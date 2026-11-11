"""Statuspagina van de executor volgens het Peil-sjabloon 1.1.1 (design/ontwerptaal/statuspagina.html, C-55, COMPONENTEN
§29).

Het sjabloon staat als versie-gepinde kopie naast deze module (pin- en driftregel E08; een test vergelijkt het met de
bron in ``design/ontwerptaal``). Plekken: ``{{x}}`` = tekst (altijd HTML-escaped), ``<!--ALS:x-->…`` /
``<!--NIET:x-->…`` / ``<!--ELK:lijst-->…``, ook genest. De renderer vult in **één doorgang** in (E07, gelijk aan de
referentie ``design/ontwerptaal/bouw/sjabloon.py``): een ingevulde waarde wordt nooit opnieuw als sjabloon gelezen.
Toonwaarden alleen uit de vaste lijst; meldingen alleen uit vaste teksten (nooit weerspiegelde invoer).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import UTC, datetime
from importlib import resources
from typing import Any

_TOKEN = re.compile(r"<!--(/?)(ELK|ALS|NIET):(\w+)-->|\{\{(\w+)\}\}")
# Peil 1.1.1: tonen per rij (ook de naam van het symbool #i-<toon>); het totaal kent alleen de eerste vier.
TONEN = frozenset(
    {
        "gezond",
        "beperkt",
        "storing",
        "onbekend",
        "verouderd",
        "niet-beschikbaar",
        "nog-niet",
        "niet-gekoppeld",
        "gate",
        "beleid",
        "feit",
    }
)
TOTAAL_TONEN = frozenset({"gezond", "beperkt", "storing", "onbekend"})
MELDING_ROLLEN = frozenset({"alert", "status", ""})
KOPPELBESTAND = "/appdata/secrets/hub-link.json"
SLEUTELBESTAND = "/appdata/secrets/naslink.json"
# Herstel zonder bruikbare schrijfsleutel staat in het installatiedocument; een test controleert dat de kop bestaat.
HERSTEL = "Zie deploy/truenas/CUSTOM_APP.md, kop 'Herstel'."


def template() -> str:
    return resources.files("executor").joinpath("statuspagina.html").read_text(encoding="utf-8")


def _esc(waarde: Any) -> str:
    if waarde is None:
        tekst = ""
    elif isinstance(waarde, bool):
        tekst = "true" if waarde else "false"
    else:
        tekst = str(waarde)
    return (
        tekst.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _lees(sjabloon: str) -> list[Any]:
    """Sjabloon → boom; ``ValueError`` bij een niet-gesloten of verkeerd genest blok."""
    wortel: dict[str, Any] = {"kids": []}
    stapel = [wortel]
    pos = 0
    for m in _TOKEN.finditer(sjabloon):
        top = stapel[-1]
        if m.start() > pos:
            top["kids"].append(sjabloon[pos : m.start()])
        pos = m.end()
        if m.group(4):
            top["kids"].append({"plek": m.group(4)})
        elif not m.group(1):
            blok: dict[str, Any] = {"soort": m.group(2), "naam": m.group(3), "kids": []}
            top["kids"].append(blok)
            stapel.append(blok)
        else:
            if len(stapel) == 1 or top["soort"] != m.group(2) or top["naam"] != m.group(3):
                raise ValueError(f"sjabloon: onverwachte sluiting {m.group(0)}")
            stapel.pop()
    if len(stapel) != 1:
        raise ValueError(f"sjabloon: blok niet gesloten: {stapel[-1]['soort']}:{stapel[-1]['naam']}")
    if pos < len(sjabloon):
        wortel["kids"].append(sjabloon[pos:])
    return list(wortel["kids"])


def _schrijf(knopen: list[Any], gegevens: Mapping[str, Any]) -> str:
    uit: list[str] = []
    for k in knopen:
        if isinstance(k, str):
            uit.append(k)
        elif "plek" in k:
            uit.append(_esc(gegevens.get(k["plek"])))
        elif k["soort"] == "ELK":
            for item in gegevens.get(k["naam"]) or []:
                uit.append(_schrijf(k["kids"], {**gegevens, **item}))
        elif k["soort"] == "ALS":
            if gegevens.get(k["naam"]):
                uit.append(_schrijf(k["kids"], gegevens))
        elif not gegevens.get(k["naam"]):  # NIET
            uit.append(_schrijf(k["kids"], gegevens))
    return "".join(uit)


def render(tpl: str, data: Mapping[str, Any]) -> str:
    """Eén doorgang (Peil 1.1.1 E07); uitvoer byte-gelijk aan ``design/ontwerptaal/bouw/sjabloon.py``."""
    return _schrijf(_lees(tpl), data)


def _toon(t: str) -> str:
    return t if t in TONEN else "onbekend"


def _tijd(dt: datetime) -> tuple[str, str]:
    return dt.strftime("%H:%M") + " UTC", dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse(iso: str | None) -> datetime | None:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None


def _datum(iso: str | None) -> str:
    dt = _parse(iso)
    return dt.strftime("%d-%m-%Y %H:%M UTC") if dt else "onbekend"


def gereed(link: Mapping[str, Any], ready_ok: bool) -> bool:
    """Contract 1.3 §3.7: Gereed = ``/readyz`` in orde **én** ``state: gekoppeld`` met ``confirmed_at``."""
    return ready_ok and link.get("state") == "gekoppeld" and bool(link.get("confirmed_at"))


def executor_page(
    *,
    versie: str,
    link: Mapping[str, Any],
    ready_checks: list[dict[str, str]],
    csrf: str,
    melding: Mapping[str, str] | None = None,
    veldfout: Mapping[str, str] | None = None,
    now: datetime | None = None,
    nas: Mapping[str, Any] | None = None,
    gestopt: Mapping[str, Any] | None = None,
    allowlist: list[str] | None = None,
    policy: Mapping[str, Any] | None = None,
) -> str:
    """Pagina-data voor de executor.

    ``link``: de (interne) koppelstatus, met ``_onleesbaar`` bij een onleesbaar koppelbestand. ``melding``: {toon:
    fout|info, titel, tekst, rol: alert|status|"" , code?, trace_id?, pad?} uit vaste teksten; ``veldfout``:
    {hub_adres|koppelcode|vingerafdruk|sleutel: tekst}. ``nas``: wat :meth:`NasLinkStore.public` geeft (nooit de
    sleutel), plus ``wacht_op_bevestiging``. ``gestopt``: de toestand na een afwijking (of ``None``). ``allowlist``:
    de acties uit het ingebakken beleid (``None`` = beleid niet leesbaar). ``policy``: {geladen, hash, read_only}."""
    now = now or datetime.now(UTC)
    tijd, iso = _tijd(now)
    onleesbaar = bool(link.get("_onleesbaar"))
    state = link.get("state")
    linked = state == "gekoppeld" and not onleesbaar
    bevestigd = linked and bool(link.get("confirmed_at"))
    formulier = not onleesbaar and not link.get("first_linked_at")
    bezig = not onleesbaar and link.get("pending") is not None
    fout = dict(veldfout or {})
    nas = dict(nas or {})
    policy = dict(policy or {})
    sleutel = bool(nas.get("ingesteld"))
    sleutel_onleesbaar = bool(nas.get("onleesbaar"))
    sleutelformulier = linked and not sleutel and not sleutel_onleesbaar
    checks: list[dict[str, Any]] = [{"naam": "Proces", "toon": "gezond", "label": "Gezond", "tijd": tijd, "iso": iso}]
    ready_ok = True
    for c in ready_checks:
        if c.get("name") == "koppeling":
            continue
        ok = c.get("status") == "ok"
        ready_ok = ready_ok and ok
        checks.append(
            {
                "naam": {"geheimen": "Eigen sleutels", "datamap": "Datamap (/appdata)"}.get(
                    c.get("name", ""), c.get("name")
                ),
                "toon": "gezond" if ok else "storing",
                "label": "Gezond" if ok else "Storing",
                "tijd": tijd,
                "iso": iso,
                "reden": "" if ok else "Herstart de executor; controleer de opslag van /appdata.",
            }
        )
    if onleesbaar:
        checks.append(
            {
                "naam": "Koppeling met de Hub",
                "toon": "storing",
                "label": "Onleesbaar",
                "tijd": tijd,
                "iso": iso,
                "reden": "Het koppelbestand is geen geldig bestand van de executor; hij vertrouwt de Hub niet.",
                "reden_code": "koppelstatus_onleesbaar",
            }
        )
    elif not linked:
        sinds = _parse((link.get("pending") or {}).get("started_at")) if bezig else None
        checks.append(
            {
                "naam": "Koppeling met de Hub",
                "toon": "niet-gekoppeld",
                "label": "Niet gekoppeld",
                "tijd": tijd,
                "iso": iso,
                "reden": f"Er loopt een koppelpoging sinds {sinds.strftime('%H:%M')} UTC."
                if sinds
                else "Zonder koppeling weet de executor niet welke acties zijn ondertekend.",
            }
        )
    elif not bevestigd:
        checks.append(
            {
                "naam": "Koppeling met de Hub",
                "toon": "onbekend",
                "label": "Niet bevestigd",
                "tijd": tijd,
                "iso": iso,
                "reden": "Gekoppeld, maar de Hub heeft de koppeling nog niet bevestigd.",
            }
        )
    if sleutel_onleesbaar:
        checks.append(
            {
                "naam": "TrueNAS-schrijfsleutel",
                "toon": "storing",
                "label": "Onleesbaar",
                "tijd": tijd,
                "iso": iso,
                "reden": f"De opgeslagen TrueNAS-koppeling is onleesbaar; de executor voert niets uit. {HERSTEL}",
                "reden_code": "sleutelopslag_onleesbaar",
            }
        )
    elif sleutel:
        checks.append(
            {
                "naam": "TrueNAS-schrijfsleutel",
                "toon": "gezond",
                "label": "Ingesteld",
                "tijd": tijd,
                "iso": iso,
                # Eerlijk over wat bekend is: de sleutel is bij het instellen live getest, daarna niet opnieuw.
                "reden": f"Eindigt op {nas.get('laatste4') or '????'}. Live getest bij het instellen op "
                f"{_datum(nas.get('ingesteld_op'))}; daarna niet opnieuw getest.",
            }
        )
    else:
        checks.append(
            {
                "naam": "TrueNAS-schrijfsleutel",
                "toon": "nog-niet",
                "label": "Niet ingesteld",
                "tijd": tijd,
                "iso": iso,
                "reden": (
                    "Wacht op je bevestiging van de vingerafdruk van TrueNAS; vul de sleutel hieronder nogmaals in."
                    if nas.get("wacht_op_bevestiging")
                    else "Vul de sleutel hieronder in; zonder sleutel voert de executor niets uit."
                )
                if sleutelformulier
                else "Wordt gevraagd zodra de executor gekoppeld is.",
            }
        )
    if gestopt is not None:
        checks.append(
            {
                "naam": "Uitvoering",
                "toon": "storing",
                "label": "Gestopt",
                "tijd": tijd,
                "iso": iso,
                "reden": (
                    "Het journaal van de executor is niet leesbaar; hij voert niets uit. Controleer de opslag van "
                    "/appdata."
                    if gestopt.get("code") == "journaal_niet_beschikbaar"
                    else "Na een actie week de teruggelezen toestand af van wat was goedgekeurd. De executor voert "
                    "niets meer uit tot je hem vrijgeeft: vul onder 'Ontkoppelen of sleutel vervangen' de huidige "
                    "sleutel in, laat 'Nieuwe sleutel' leeg en kies 'Sleutel vervangen'."
                ),
                "reden_code": "journaal_niet_beschikbaar"
                if gestopt.get("code") == "journaal_niet_beschikbaar"
                else "executor_gestopt",
            }
        )
    is_gereed = gereed(link, ready_ok) and not onleesbaar
    storing = any(c["toon"] == "storing" for c in checks)
    if storing:
        totaal = ("storing", "Niet gereed" if not is_gereed else "Storing")
        toelichting = (
            "Storing — de koppelstatus is onleesbaar."
            if onleesbaar
            else "Storing — de opgeslagen TrueNAS-koppeling is onleesbaar."
            if sleutel_onleesbaar
            else "Storing — de executor is gestopt en voert niets uit."
            if gestopt is not None
            else "Een eigen controle faalt."
        )
    elif not is_gereed:
        totaal = ("onbekend", "Niet gereed")
        toelichting = (
            "Deels onbekend — er loopt een koppelpoging."
            if bezig
            else "Deels onbekend — wacht op bevestiging door de Hub."
            if linked
            else "Deels onbekend — wacht op koppeling met de Hub."
        )
    elif not sleutel:
        # Gereed (§3.7), maar zonder schrijfsleutel voert de executor niets uit: het totaal is nooit groen.
        totaal = ("onbekend", "Onbekend")
        toelichting = "Gereed, maar zonder TrueNAS-schrijfsleutel voert de executor niets uit."
    elif allowlist is None or not (policy.get("read_only") or policy.get("toegestaan")):
        totaal = ("beperkt", "Beperkt")
        toelichting = "Gereed, maar het risicobeleid is niet bruikbaar; de executor voert niets uit."
    else:
        totaal = ("gezond", "Gezond")
        toelichting = "Gereed. Voert alleen door de Hub ondertekende acties van de allowlist uit."
    if onleesbaar:
        gereed_tekst = "Nee — koppelstatus onleesbaar"
    elif is_gereed and gestopt is not None:
        gereed_tekst = "Ja — gekoppeld en bevestigd; gestopt, voert niets uit"
    elif is_gereed and not sleutel:
        gereed_tekst = "Ja — gekoppeld en bevestigd; voert niets uit zonder schrijfsleutel"
    elif is_gereed:
        gereed_tekst = "Ja — gekoppeld en bevestigd"
    elif linked:
        gereed_tekst = "Nee — wacht op bevestiging door de Hub"
    elif state == "ingetrokken":
        gereed_tekst = "Nee — ingetrokken door de Hub"
    elif state == "ontkoppeld":
        gereed_tekst = "Nee — ontkoppeld"
    else:
        gereed_tekst = "Nee — wacht op koppeling"
    spring = next((k for k in ("hub_adres", "koppelcode", "vingerafdruk", "sleutel") if fout.get(k)), None)
    doel = {"hub_adres": "hub", "koppelcode": "koppelcode", "vingerafdruk": "vingerafdruk", "sleutel": "sleutel"}.get(
        spring or "", "inhoud"
    )
    if onleesbaar:
        titel_toestand = "niet gereed, koppelstatus onleesbaar"
    elif bezig and not linked:
        titel_toestand = "niet gereed, koppelen bezig"
    else:
        mislukt = bool(melding and melding.get("toon") == "fout")
        titel_toestand = ("gekoppeld" if linked else "niet gekoppeld") + (
            (" (niet gelukt)" if linked else " (koppelen mislukt)") if mislukt else ""
        )
    sinds_dt = _parse((link.get("pending") or {}).get("started_at")) if bezig else None
    data: dict[str, Any] = {
        "dienst_naam": "Executor",
        "dienst_omschrijving": "Voert alleen door de Hub ondertekende acties uit op TrueNAS. Enige dienst met een "
        "schrijfsleutel. Nooit shell, sudo of Docker.",
        "titel_toestand": titel_toestand,
        "spring_doel": doel,
        "spring_tekst": "Naar het veld met de fout" if spring else "Naar inhoud",
        "totaal_toon": totaal[0] if totaal[0] in TOTAAL_TONEN else "onbekend",
        "totaal_label": totaal[1],
        "totaal_toelichting": toelichting,
        "checks": checks,
        "gereed": gereed_tekst,
        "bron": "Eigen controles (/readyz, /healthz) en het koppelbestand van de executor.",
        "versie": versie,
        "bijgewerkt": now.strftime("%d-%m-%Y %H:%M UTC"),
        "bijgewerkt_iso": iso,
        "gekoppeld": linked,
        "gekoppeld_sinds": _datum(link.get("linked_at")),
        "hub_adres": (link.get("hub_url") or "") if linked else "",
        "hub_vingerafdruk": (link.get("pins") or {}).get("keyset_fingerprint")
        or link.get("keyset_fingerprint")
        or "onbekend",
        "ontkoppeld": not onleesbaar and not linked and not formulier and state in ("ontkoppeld", "nooit_gekoppeld"),
        "ingetrokken": not onleesbaar and not linked and not formulier and state == "ingetrokken",
        "koppelstatus_onleesbaar": onleesbaar,
        "koppelformulier": formulier,
        "koppelen_bezig": bezig,
        "koppelen_bezig_sinds": sinds_dt.strftime("%H:%M") + " UTC" if sinds_dt else "",
        "koppelen_bezig_iso": sinds_dt.strftime("%Y-%m-%dT%H:%M:%SZ") if sinds_dt else "",
        "koppelcode_geldig": "30 minuten",
        "csrf_token": csrf,
        "fout_hub_adres": fout.get("hub_adres", ""),
        "fout_koppelcode": fout.get("koppelcode", ""),
        "fout_vingerafdruk": fout.get("vingerafdruk", ""),
        # §3.9: de schrijfsleutel wordt gevraagd zodra de executor gekoppeld is; beheer zodra er een sleutel ligt (ook
        # bij een onleesbaar of ontkoppeld koppelbestand, want de sleutel is daar juist het herstelmiddel).
        "schrijfsleutel_formulier": sleutelformulier,
        "fout_sleutel": fout.get("sleutel", "") if sleutelformulier else "",
        "executor_beheer": sleutel,
        "sleutel_laatste4": nas.get("laatste4") or "????",
        "sleutel_datum": "ingesteld op " + _datum(nas.get("ingesteld_op")),
        "dienst_blok_titel": "Wat deze versie uitvoert",
        "dienst_blok": _dienst_blok(allowlist, policy, nas if sleutel else {}),
    }
    if melding:
        rol = str(melding.get("rol") or "")
        data.update(
            {
                "melding": True,
                "melding_rol": rol if rol in MELDING_ROLLEN else "",
                "melding_toon": "fout" if melding.get("toon") == "fout" else "info",
                "melding_icoon": "storing" if melding.get("toon") == "fout" else "info",
                "melding_titel": melding.get("titel", ""),
                "melding_tekst": melding.get("tekst", ""),
                "melding_pad": melding.get("pad", ""),
                "melding_code": melding.get("code", ""),
                "melding_link": bool(spring),
                "melding_link_doel": doel,
                "melding_link_tekst": "Naar het veld met de fout",
                "trace_id": melding.get("trace_id", ""),
            }
        )
    for c in [*data["checks"], *data["dienst_blok"]]:
        c["toon"] = _toon(c["toon"])
    return render(template(), data)


def _dienst_blok(
    allowlist: list[str] | None, policy: Mapping[str, Any], nas: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Het blok "Wat deze versie uitvoert": allowlist en beleid (feiten uit het image), plus het vastgelegde NAS."""
    if allowlist is None:
        rijen: list[dict[str, Any]] = [
            {
                "naam": "Toegestane acties",
                "toon": "storing",
                "label": "Niet beschikbaar",
                "reden": "Het risicobeleid in het image is niet leesbaar; de executor voert niets uit.",
                "reden_code": "policy_niet_beschikbaar",
            }
        ]
    else:
        rijen = [
            {
                "naam": "Toegestane acties",
                "toon": "beleid",
                "label": f"{len(allowlist)} acties",
                "reden": ", ".join(allowlist)
                + ". Alleen met een geldige handtekening van de Hub; al het andere wordt geweigerd.",
            }
        ]
        kort = str(policy.get("hash") or "")
        if policy.get("read_only"):
            rijen.append(
                {
                    "naam": "Risicobeleid",
                    "toon": "beleid",
                    "label": "Alleen-lezen",
                    "reden": f"Ingebakken in het image; policy_hash {kort}.",
                }
            )
        else:
            toegestaan = bool(policy.get("toegestaan"))
            rijen.append(
                {
                    "naam": "Risicobeleid",
                    "toon": "beperkt" if toegestaan else "storing",
                    "label": "Beschrijfbaar",
                    "reden": (
                        "Alleen voor ontwikkeling toegestaan (EXECUTOR_ALLOW_WRITABLE_POLICY); "
                        if toegestaan
                        else "Het beleid hoort alleen-lezen in het image te staan; de executor voert niets uit. "
                    )
                    + f"policy_hash {kort}.",
                    "reden_code": "" if toegestaan else "policy_niet_read_only",
                }
            )
    if nas.get("nas_adres"):
        vinger = str(nas.get("tls_vingerafdruk") or "")
        rijen.append(
            {
                "naam": "TrueNAS",
                "toon": "feit",
                "label": "Vastgelegd",
                "reden": f"{nas.get('nas_adres')}, poort {nas.get('nas_poort')}; TLS-vingerafdruk (SHA-256) "
                + ":".join(vinger[i : i + 2] for i in range(0, len(vinger), 2)).upper()
                + ". Een ander adres of certificaat wordt geweigerd.",
            }
        )
    return rijen


def onleesbaar_melding(*, sleutel_ingesteld: bool = False) -> dict[str, str]:
    """Bestaande toestand bij het laden (geen live-rol, geen trace-ID; code + pad, Peil 1.1.1 §29.1). De executor
    koppelt niet met een koppeltoken (§3.9): herstel gaat met de TrueNAS-schrijfsleutel op deze pagina."""
    return {
        "toon": "fout",
        "rol": "",
        "titel": "De koppelstatus is onleesbaar",
        "tekst": (
            "De executor kon zijn koppelbestand niet lezen en voert daarom niets uit. De executor koppelt niet met "
            "een koppeltoken. Herstel: vul onder 'Ontkoppelen of sleutel vervangen' de TrueNAS-schrijfsleutel in en "
            "kies 'Ontkoppelen van de Hub'; daarna kun je opnieuw koppelen met een koppelcode. Het bestand:"
            if sleutel_ingesteld
            else "De executor kon zijn koppelbestand niet lezen en voert daarom niets uit. De executor koppelt niet "
            "met een koppeltoken, en er is geen bruikbare TrueNAS-schrijfsleutel (niet ingesteld of onleesbaar) "
            f"waarmee je dit hier kunt herstellen. {HERSTEL} Het bestand:"
        ),
        "pad": KOPPELBESTAND,
        "code": "koppelstatus_onleesbaar",
    }


def vingerafdruk_melding(vingerafdruk: str, *, rol: str) -> dict[str, str]:
    """Stap 1 van het sleutelformulier: de TLS-vingerafdruk van TrueNAS, opgehaald uit de TLS-handdruk (geen
    weerspiegelde invoer). ``rol`` = ``status`` direct na het versturen, ``""`` als bestaande toestand bij het laden."""
    return {
        "toon": "info",
        "rol": rol,
        "titel": "Controleer de vingerafdruk van TrueNAS",
        "tekst": "De sleutel is nog niet verstuurd en niet bewaard. Vergelijk de SHA-256-vingerafdruk hieronder met "
        "het certificaat in TrueNAS (Systeem → Certificaten). Klopt hij, vul de sleutel dan nogmaals in om te "
        "bevestigen (binnen 15 minuten). Daarna liggen het NAS-adres en dit certificaat vast.",
        "pad": vingerafdruk,
    }
