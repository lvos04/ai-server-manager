"""Statuspagina van de executor volgens het Peil-sjabloon (design/ontwerptaal/statuspagina.html, C-55).

Het sjabloon staat als versie-gepinde kopie naast deze module (O-14; een test vergelijkt het met de bron in
``design/ontwerptaal``). Plekken: ``{{x}}`` = tekst (altijd HTML-escaped), ``<!--ALS:x-->…`` / ``<!--NIET:x-->…`` /
``<!--ELK:lijst-->…``. Toonwaarden alleen uit de vaste lijst ``gezond | beperkt | storing | onbekend | gate``; meldingen
alleen uit vaste teksten (nooit weerspiegelde invoer).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import UTC, datetime
from html import escape
from importlib import resources
from typing import Any

_ELK = re.compile(r"<!--ELK:(\w+)-->(.*?)<!--/ELK:\1-->", re.S)
_ALS = re.compile(r"<!--ALS:(\w+)-->(.*?)<!--/ALS:\1-->", re.S)
_NIET = re.compile(r"<!--NIET:(\w+)-->(.*?)<!--/NIET:\1-->", re.S)
_VAR = re.compile(r"\{\{(\w+)\}\}")
TONEN = frozenset({"gezond", "beperkt", "storing", "onbekend", "gate"})


def template() -> str:
    return resources.files("executor").joinpath("statuspagina.html").read_text(encoding="utf-8")


def render(tpl: str, data: Mapping[str, Any]) -> str:
    """Dezelfde regels als de referentie-renderer ``design/ontwerptaal/bouw/sjabloon.mjs``."""

    def blokken(t: str, d: Mapping[str, Any]) -> str:
        t = _ELK.sub(lambda m: "".join(blokken(m.group(2), {**d, **item}) for item in d.get(m.group(1)) or []), t)
        t = _ALS.sub(lambda m: blokken(m.group(2), d) if d.get(m.group(1)) else "", t)
        t = _NIET.sub(lambda m: "" if d.get(m.group(1)) else blokken(m.group(2), d), t)
        return _VAR.sub(lambda m: escape(str(d.get(m.group(1)) or ""), quote=True), t)

    return blokken(tpl, data)


def _toon(t: str) -> str:
    return t if t in TONEN else "onbekend"


def _tijd(dt: datetime) -> tuple[str, str]:
    return dt.strftime("%H:%M") + " UTC", dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _datum(iso: str | None) -> str:
    if not iso:
        return "onbekend"
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%d-%m-%Y %H:%M UTC")
    except ValueError:
        return "onbekend"


def executor_page(
    *,
    versie: str,
    link: Mapping[str, Any],
    ready_checks: list[dict[str, str]],
    csrf: str,
    melding: Mapping[str, str] | None = None,
    veldfout: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> str:
    """Pagina-data voor de executor. ``melding``: {toon: fout|info, titel, tekst, code?} uit vaste teksten;
    ``veldfout``: {hub_adres|koppelcode|vingerafdruk: tekst}."""
    now = now or datetime.now(UTC)
    tijd, iso = _tijd(now)
    state = str(link.get("state") or "nooit_gekoppeld")
    linked = state == "gekoppeld"
    formulier = not link.get("first_linked_at")
    fout = dict(veldfout or {})
    checks: list[dict[str, Any]] = [{"naam": "Proces", "toon": "gezond", "label": "Gezond", "tijd": tijd, "iso": iso}]
    for c in ready_checks:
        if c.get("name") == "koppeling":
            continue
        ok = c.get("status") == "ok"
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
    if not linked:
        checks.append(
            {
                "naam": "Koppeling met de Hub",
                "toon": "onbekend",
                "label": "Niet gekoppeld",
                "tijd": tijd,
                "iso": iso,
                "reden": "Zonder koppeling weet de executor niet welke acties zijn ondertekend.",
            }
        )
    checks.append(
        {
            "naam": "TrueNAS-schrijfsleutel",
            "toon": "onbekend",
            "label": "Niet ingesteld",
            "tijd": tijd,
            "iso": iso,
            "reden": "Wordt gevraagd na het koppelen; volgt in fase P2.",
        }
    )
    storing = any(c["toon"] == "storing" for c in checks)
    spring = next((k for k in ("hub_adres", "koppelcode", "vingerafdruk") if fout.get(k)), None)
    data: dict[str, Any] = {
        "dienst_naam": "Executor",
        "dienst_omschrijving": "Voert alleen door de Hub ondertekende acties uit op TrueNAS. Enige dienst met een "
        "schrijfsleutel. Nooit shell, sudo of Docker.",
        "titel_toestand": ("gekoppeld" if linked else "niet gekoppeld")
        + (" (koppelen mislukt)" if melding and melding.get("toon") == "fout" else ""),
        "spring_doel": {"hub_adres": "hub", "koppelcode": "koppelcode", "vingerafdruk": "vingerafdruk"}.get(
            spring or "", "inhoud"
        ),
        "spring_tekst": "Naar het veld met de fout" if spring else "Naar inhoud",
        "totaal_toon": "storing" if storing else "onbekend",
        "totaal_label": "Storing" if storing else "Niet gereed",
        "totaal_toelichting": "Een eigen controle faalt."
        if storing
        else (
            "Gekoppeld; de schrijfsleutel en de toegestane acties volgen in fase P2. "
            "Tot dan voert de executor niets uit."
            if linked
            else "Deels onbekend — wacht op koppeling met de Hub."
        ),
        "checks": checks,
        "gereed": "Nee — voert in deze fase niets uit" if linked else "Nee — wacht op koppeling",
        "versie": versie,
        "bijgewerkt": now.strftime("%d-%m-%Y %H:%M UTC"),
        "bijgewerkt_iso": iso,
        "gekoppeld": linked,
        "gekoppeld_sinds": _datum(link.get("linked_at")),
        "hub_adres": link.get("hub_url") or "",
        "hub_vingerafdruk": link.get("keyset_fingerprint") or "onbekend",
        "ontkoppeld": not linked and not formulier and state in ("ontkoppeld", "nooit_gekoppeld"),
        "ingetrokken": not linked and not formulier and state not in ("ontkoppeld", "nooit_gekoppeld"),
        "koppelformulier": formulier,
        "koppelcode_geldig": "30 minuten",
        "csrf_token": csrf,
        "fout_hub_adres": fout.get("hub_adres", ""),
        "fout_koppelcode": fout.get("koppelcode", ""),
        "fout_vingerafdruk": fout.get("vingerafdruk", ""),
        "dienst_blok_titel": "Wat deze versie uitvoert",
        "dienst_blok": [
            {
                "naam": "Toegestane acties",
                "toon": "gate",
                "label": "0 · voert niets uit",
                "reden": "De lijst met toegestane acties is in deze fase leeg. Acties komen pas in fase P2, na "
                "voorstel, beleid en goedkeuring.",
            }
        ],
    }
    if melding:
        data.update(
            {
                "melding": True,
                "melding_toon": "fout" if melding.get("toon") == "fout" else "info",
                "melding_icoon": "storing" if melding.get("toon") == "fout" else "info",
                "melding_titel": melding.get("titel", ""),
                "melding_tekst": melding.get("tekst", ""),
                "melding_link": bool(spring),
                "melding_link_doel": data["spring_doel"],
                "melding_link_tekst": "Naar het veld met de fout",
                "trace_id": "",
            }
        )
    for c in [*data["checks"], *data["dienst_blok"]]:
        c["toon"] = _toon(c["toon"])
    data["totaal_toon"] = _toon(data["totaal_toon"])
    return render(template(), data)
