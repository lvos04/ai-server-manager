"""Statuspagina in het Peil-sjabloon 1.1.1: versie-gepinde kopie (E08), renderer in één doorgang gelijk aan de
referentie ``design/ontwerptaal/bouw/sjabloon.py`` (E07), escapen, vaste tonen, meldingsrol, onleesbaar en koppelen
bezig zonder formulier, Gereed volgens contract 1.3 §3.7."""

from __future__ import annotations

import hashlib
import importlib.util
import re
import warnings
from datetime import UTC, datetime
from html import unescape
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from executor.app import FORM_MESSAGES
from executor.hublink import public_status
from executor.statuspagina import TONEN, executor_page, onleesbaar_melding, render, template

DESIGN = Path(__file__).resolve().parents[3] / "design" / "ontwerptaal"
BRON = DESIGN / "statuspagina.html"
# Pin (ONTWERPTAAL §14, Peil 1.1.1 E08): versie + sha256 van de kopie, gelijk aan de bron op commit 3e559e7.
PIN_VERSIE = (1, 1, 1)
PIN_SHA256 = "d352028f798934d5efb96610c42a61712e3948b8c9eec8a87f34035b89f8c80b"
NOW = datetime(2026, 11, 10, 11, 56, tzinfo=UTC)
LINKED = {
    "state": "gekoppeld",
    "first_linked_at": "2026-11-09T10:00:00Z",
    "linked_at": "2026-11-09T10:00:00Z",
    "confirmed_at": "2026-11-09T10:00:01Z",
    "hub_url": "http://hub.invalid:30400",
    "pins": {"keyset_fingerprint": "MEGG-8GFG-2E4Y-K2RQ"},
}
READY = [{"name": "geheimen", "status": "ok"}, {"name": "datamap", "status": "ok"}]


def _versie(tekst: str) -> tuple[int, ...]:
    m = re.search(r"Peil statuspagina-sjabloon (\d+)\.(\d+)\.(\d+)", tekst)
    assert m, "sjabloon zonder Peil-versie in de kopcommentaar"
    return tuple(int(x) for x in m.groups())


def _referentie() -> ModuleType:
    spec = importlib.util.spec_from_file_location("peil_sjabloon_referentie", DESIGN / "bouw" / "sjabloon.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_sjabloon_is_de_gepinde_kopie_van_de_ontwerptaal() -> None:
    """Falen bij een met de hand gewijzigde kopie of bij dezelfde bronversie met andere inhoud; een nieuwere
    bronversie in design/ontwerptaal is alleen een waarschuwing (overstappen = kopie + renderer + tests bijwerken)."""
    kopie = template()
    assert hashlib.sha256(kopie.encode("utf-8")).hexdigest() == PIN_SHA256, "statuspagina.html met de hand gewijzigd"
    assert _versie(kopie) == PIN_VERSIE
    bron = BRON.read_text(encoding="utf-8")
    assert _versie(bron) >= PIN_VERSIE, "bron is ouder dan de gepinde kopie"
    if _versie(bron) == PIN_VERSIE:
        assert kopie == bron, "zelfde Peil-versie met andere inhoud in design/ontwerptaal"
    else:
        warnings.warn(f"Peil {_versie(bron)} staat in design/ontwerptaal; de executor pint {PIN_VERSIE}", stacklevel=1)


def test_render_escapet_en_kent_als_niet_elk_ook_genest() -> None:
    tpl = "<!--ALS:a-->[{{x}}]<!--/ALS:a--><!--NIET:a-->leeg<!--/NIET:a--><!--ELK:l-->({{n}})<!--/ELK:l-->"
    assert render(tpl, {"a": True, "x": "<script>", "l": [{"n": 1}, {"n": "&"}]}) == "[&lt;script&gt;](1)(&amp;)"
    assert render(tpl, {"a": False}) == "leeg"
    assert render("<!--ALS:a--><!--NIET:b-->ja<!--/NIET:b--><!--/ALS:a-->", {"a": 1, "b": ""}) == "ja"
    with pytest.raises(ValueError):
        render("<!--ALS:a-->open", {})


def test_een_doorgang_een_waarde_wordt_nooit_opnieuw_als_sjabloon_gelezen() -> None:
    """E07: in 1.1.0 vulde een tweede doorgang '{{csrf_token}}' als waarde opnieuw in."""
    tpl = '<input value="{{a}}"><!--ALS:b-->{{b}}<!--/ALS:b-->'
    out = render(tpl, {"a": "{{csrf_token}}", "b": "<!--ALS:x-->", "csrf_token": "GEHEIM"})
    assert "GEHEIM" not in out and "{{csrf_token}}" in out and "&lt;!--ALS:x--&gt;" in out


@pytest.mark.parametrize(
    "link",
    [
        {"state": "nooit_gekoppeld"},
        LINKED,
        {**LINKED, "confirmed_at": None},
        {"state": "nooit_gekoppeld", "pending": {"started_at": "2026-11-10T11:54:00Z"}},
        {"state": None, "_onleesbaar": True},
        {**LINKED, "state": "ingetrokken"},
    ],
)
def test_uitvoer_byte_gelijk_aan_de_referentie_renderer(link: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    """De eigen renderer geeft voor elke toestand precies dezelfde HTML als ``bouw/sjabloon.py`` (Peil 1.1.1)."""
    import executor.statuspagina as sp

    ref = _referentie()
    captured: dict[str, Any] = {}

    def spy(tpl: str, data: dict[str, Any]) -> str:
        captured["data"] = data
        return render(tpl, data)

    monkeypatch.setattr(sp, "render", spy)
    html = executor_page(versie="0.1.0", link=link, ready_checks=READY, csrf="abc", now=NOW)
    assert html == ref.render(template(), captured["data"])
    for c in [*captured["data"]["checks"], *captured["data"]["dienst_blok"]]:
        assert c["toon"] in TONEN


ACTIES = ["app.restart", "app.stop", "zfs.snapshot.create"]
BELEID = {"geladen": True, "hash": "sha256:" + "ab" * 32, "read_only": True, "toegestaan": True}
NAS = {
    "ingesteld": True,
    "onleesbaar": False,
    "nas_adres": "192.0.2.10",
    "nas_poort": 443,
    "tls_vingerafdruk": "0f" * 32,
    "laatste4": "wxyz",
    "ingesteld_op": "2026-11-10T09:00:00Z",
    "rollen": ["FULL_ADMIN"],
}


def test_gekoppeld_en_bevestigd_is_gereed_maar_nooit_groen_zonder_schrijfsleutel() -> None:
    html = executor_page(
        versie="0.1.0", link=LINKED, ready_checks=READY, csrf="tok", now=NOW, allowlist=ACTIES, policy=BELEID
    )
    assert "MEGG-8GFG-2E4Y-K2RQ" in html and "gaat via de Hub" in html
    assert "Ja — gekoppeld en bevestigd; voert niets uit zonder schrijfsleutel" in html
    # Totaal = slechtste controle (schrijfsleutel onbekend): nooit groen zolang de executor niets uitvoert.
    assert 'class="pil pil-onbekend"><svg aria-hidden="true"><use href="#i-onbekend"/></svg>Onbekend' in html
    assert 'class="knop knop-secundair" href="http://hub.invalid:30400">Hub openen' in html
    # §3.9: zodra gekoppeld vraagt de pagina de schrijfsleutel; geen koppel- en geen beheerformulier.
    assert 'action="/schrijfsleutel"' in html and 'name="csrf" value="tok"' in html
    assert 'action="/koppelen"' not in html and 'action="/beheer"' not in html
    assert 'pil-nog-niet"><svg aria-hidden="true"><use href="#i-nog-niet"/></svg>Niet ingesteld' in html
    assert "zonder sleutel voert de executor niets uit" in html
    # Toegestane acties: een feit uit het beleid in het image (toon 'beleid'), geen gezondheidsoordeel.
    assert 'pil-beleid"><svg aria-hidden="true"><use href="#i-beleid"/></svg>3 acties' in html
    assert "app.restart, app.stop, zfs.snapshot.create." in html and "Alleen-lezen" in html
    assert "policy_hash sha256:" + "ab" * 32 in html
    niet_bevestigd = executor_page(
        versie="0.1.0", link={**LINKED, "confirmed_at": None}, ready_checks=READY, csrf="", now=NOW
    )
    assert "Nee — wacht op bevestiging door de Hub" in niet_bevestigd and "Niet bevestigd" in niet_bevestigd


def test_met_schrijfsleutel_gezond_en_beheerformulier_zonder_de_sleutel() -> None:
    html = executor_page(
        versie="0.1.0", link=LINKED, ready_checks=READY, csrf="tok", now=NOW, nas=NAS, allowlist=ACTIES, policy=BELEID
    )
    assert 'class="pil pil-gezond"><svg aria-hidden="true"><use href="#i-gezond"/></svg>Gezond</span>' in html
    assert "Ja — gekoppeld en bevestigd</dd>" in html
    assert 'action="/beheer"' in html and 'action="/schrijfsleutel"' not in html and 'action="/koppelen"' not in html
    # Alleen de laatste 4 tekens; eerlijk over wat getest is.
    assert "Eindigt op wxyz. Live getest bij het instellen op 10-11-2026 09:00 UTC; daarna niet opnieuw getest." in html
    assert "<code>wxyz</code>" in html
    # Het vastgelegde NAS-adres en certificaat als feit.
    assert 'pil-feit"><svg aria-hidden="true"><use href="#i-feit"/></svg>Vastgelegd' in html
    assert "192.0.2.10, poort 443; TLS-vingerafdruk (SHA-256) 0F:0F:" in html
    assert "Een ander adres of certificaat wordt geweigerd." in html


def test_wacht_op_bevestiging_van_de_vingerafdruk() -> None:
    html = executor_page(
        versie="0.1.0",
        link=LINKED,
        ready_checks=READY,
        csrf="tok",
        now=NOW,
        nas={"ingesteld": False, "onleesbaar": False, "wacht_op_bevestiging": True},
        allowlist=ACTIES,
        policy=BELEID,
    )
    assert "Wacht op je bevestiging van de vingerafdruk van TrueNAS" in html and 'action="/schrijfsleutel"' in html


def test_gestopt_na_een_afwijking_is_storing_met_herstelstap() -> None:
    html = executor_page(
        versie="0.1.0",
        link=LINKED,
        ready_checks=READY,
        csrf="tok",
        now=NOW,
        nas=NAS,
        gestopt={"code": "staat_verschilt", "at": "2026-11-10T11:00:00Z"},
        allowlist=ACTIES,
        policy=BELEID,
    )
    assert 'class="pil pil-storing"><svg aria-hidden="true"><use href="#i-storing"/></svg>Storing' in html
    assert "Gestopt" in html and "(code <code>executor_gestopt</code>)" in html
    assert "Ja — gekoppeld en bevestigd; gestopt, voert niets uit" in html
    assert "laat &#39;Nieuwe sleutel&#39; leeg en kies &#39;Sleutel vervangen&#39;" in html
    journaal = executor_page(
        versie="0.1.0",
        link=LINKED,
        ready_checks=READY,
        csrf="tok",
        now=NOW,
        nas=NAS,
        gestopt={"code": "journaal_niet_beschikbaar"},
        allowlist=ACTIES,
        policy=BELEID,
    )
    assert (
        "(code <code>journaal_niet_beschikbaar</code>)" in journaal and "Controleer de opslag van /appdata." in journaal
    )


def test_onleesbare_sleutelopslag_geen_formulieren() -> None:
    html = executor_page(
        versie="0.1.0",
        link=LINKED,
        ready_checks=READY,
        csrf="tok",
        now=NOW,
        nas={"ingesteld": False, "onleesbaar": True},
        allowlist=ACTIES,
        policy=BELEID,
    )
    assert (
        "(code <code>sleutelopslag_onleesbaar</code>)" in html and "Storing — de opgeslagen TrueNAS-koppeling" in html
    )
    assert 'action="/schrijfsleutel"' not in html and 'action="/beheer"' not in html


def test_beleid_onleesbaar_of_beschrijfbaar_is_nooit_groen() -> None:
    kwargs: dict[str, Any] = {"versie": "0.1.0", "link": LINKED, "ready_checks": READY, "csrf": "tok", "now": NOW}
    geen = executor_page(**kwargs, nas=NAS, allowlist=None, policy={"geladen": False})
    assert "(code <code>policy_niet_beschikbaar</code>)" in geen and "Niet beschikbaar" in geen
    assert (
        'class="pil pil-gezond"><svg aria-hidden="true"><use href="#i-gezond"/></svg>Gezond</span><span class="sr">: '
        not in geen
    )
    schrijfbaar = executor_page(
        **kwargs, nas=NAS, allowlist=ACTIES, policy={**BELEID, "read_only": False, "toegestaan": False}
    )
    assert "(code <code>policy_niet_read_only</code>)" in schrijfbaar and "Beschrijfbaar" in schrijfbaar
    assert "Gereed, maar het risicobeleid is niet bruikbaar" in schrijfbaar
    ontwikkel = executor_page(
        **kwargs, nas=NAS, allowlist=ACTIES, policy={**BELEID, "read_only": False, "toegestaan": True}
    )
    assert "Alleen voor ontwikkeling toegestaan (EXECUTOR_ALLOW_WRITABLE_POLICY)" in ontwikkel
    assert "policy_niet_read_only" not in ontwikkel


def test_onleesbaar_koppelbestand_met_sleutel_biedt_beheer_als_herstel() -> None:
    html = executor_page(
        versie="0.1.0",
        link={"state": None, "_onleesbaar": True},
        ready_checks=READY,
        csrf="tok",
        melding=onleesbaar_melding(sleutel_ingesteld=True),
        now=NOW,
        nas=NAS,
        allowlist=ACTIES,
        policy=BELEID,
    )
    assert 'action="/beheer"' in html and 'action="/koppelen"' not in html and 'role="alert"' not in html
    assert "daarna kun je opnieuw koppelen met een koppelcode" in html
    zonder = onleesbaar_melding()
    assert "geen bruikbare TrueNAS-schrijfsleutel" in zonder["tekst"] and "CUSTOM_APP.md" in zonder["tekst"]


def test_onleesbaar_zonder_bruikbare_sleutel_zegt_niet_dat_er_geen_sleutel_is() -> None:
    """Ontwerpreview S-P2-005 (herreview): de melding zonder bruikbare sleutel geldt ook als de sleutelopslag zelf
    onleesbaar is (app.py geeft dan sleutel_ingesteld=False). Ze mag dan niet beweren dat er nog geen sleutel is
    ingesteld, want de rij 'TrueNAS-schrijfsleutel' op dezelfde pagina zegt 'Onleesbaar'."""
    beide = executor_page(
        versie="0.1.0",
        link={"state": None, "_onleesbaar": True},
        ready_checks=READY,
        csrf="",
        melding=onleesbaar_melding(sleutel_ingesteld=False),
        now=NOW,
        nas={"ingesteld": False, "onleesbaar": True},
        allowlist=ACTIES,
        policy=BELEID,
    )
    tekst = unescape(beide)
    assert "sleutelopslag_onleesbaar" in tekst and "koppelstatus_onleesbaar" in tekst
    assert "nog geen TrueNAS-schrijfsleutel ingesteld" not in tekst
    assert "geen bruikbare TrueNAS-schrijfsleutel (niet ingesteld of onleesbaar)" in tekst


REPO = Path(__file__).resolve().parents[3]
HERSTELDOC = REPO / "deploy" / "truenas" / "CUSTOM_APP.md"
# Verwijzing naar een kop: "deploy/truenas/CUSTOM_APP.md, kop 'Herstel'" (in de README met backticks om het pad).
KOPVERWIJZING = re.compile(r"deploy/truenas/CUSTOM_APP\.md`?, kop ['\"]([^'\"]+)['\"]")


def _sectie(doc: str, kop: str) -> str:
    """De tekst onder ``## <kop>`` tot de volgende kop van hetzelfde niveau; de kop moet precies één keer bestaan."""
    regels = doc.splitlines()
    begin = [i for i, r in enumerate(regels) if r == f"## {kop}"]
    assert len(begin) == 1, f"CUSTOM_APP.md heeft {len(begin)} keer de kop '## {kop}' (verwacht: precies 1)"
    eind = next((i for i in range(begin[0] + 1, len(regels)) if regels[i].startswith("## ")), len(regels))
    return "\n".join(regels[begin[0] + 1 : eind])


def test_herstelverwijzing_wijst_naar_een_bestaande_kop_met_beide_toestanden() -> None:
    """R-ONTWERP-1: bij een onleesbaar koppelbestand zonder schrijfsleutel en bij een onleesbare sleutelopslag
    verwijzen de statuspagina en de README naar een kop in CUSTOM_APP.md. Die kop bestaat en beschrijft beide codes,
    het herstel met een schrijfsleutel op de statuspagina en de weg zonder (een nieuwe datamap via Host Path).
    R-ONTWERP-4: hetzelfde voor de melding bij ``koppelstatus_onleesbaar`` in ``last_error`` en in het
    formulierantwoord als niet bekend is dat er een bruikbare sleutel is (de standaard)."""
    onleesbaar = {"state": None, "_onleesbaar": True, "last_error": {"code": "koppelstatus_onleesbaar"}}
    sleutelopslag = executor_page(
        versie="0.1.0",
        link=LINKED,
        ready_checks=READY,
        csrf="",
        now=NOW,
        nas={"ingesteld": False, "onleesbaar": True},
        allowlist=ACTIES,
        policy=BELEID,
    )
    teksten = {
        "statuspagina, rij sleutelopslag_onleesbaar": unescape(sleutelopslag),
        "statuspagina, koppelstatus onleesbaar zonder sleutel": onleesbaar_melding()["tekst"],
        "hublink.py, last_error koppelstatus_onleesbaar": public_status(onleesbaar)["last_error"]["melding"],
        "app.py, FORM_MESSAGES koppelstatus_onleesbaar": FORM_MESSAGES["koppelstatus_onleesbaar"][2],
        "apps/executor/README.md": (REPO / "apps" / "executor" / "README.md").read_text(encoding="utf-8"),
    }
    doc = HERSTELDOC.read_text(encoding="utf-8")
    for waar, tekst in teksten.items():
        assert "(herstel)" not in tekst, f"{waar}: verwijst nog naar '(herstel)' zonder bestaande kop"
        koppen = KOPVERWIJZING.findall(tekst)
        assert koppen, f"{waar}: geen verwijzing naar een kop in deploy/truenas/CUSTOM_APP.md"
        for kop in koppen:
            sectie = _sectie(doc, kop)
            for woord in ("koppelstatus_onleesbaar", "sleutelopslag_onleesbaar", "Ontkoppelen van de Hub", "Host Path"):
                assert woord in sectie, f"{waar}: kop '{kop}' in CUSTOM_APP.md noemt '{woord}' niet"


ONBOARDING = REPO / "apps" / "web" / "src" / "app" / "onboarding"


def test_installatiedocument_verwijst_voor_de_koppelcode_naar_het_hub_scherm() -> None:
    """R-ONTWERP-5: stap 3 van CUSTOM_APP.md ("Koppelen met de Hub") stuurt de beheerder voor de koppelcode naar de
    bestaande Hub-pagina, net als de kop 'Herstel', en niet naar /api/docs (die stuurt geen X-CSRF-Token mee, kop 5).
    De genoemde knop, pagina en link bestaan in de Hub-UI."""
    stap3 = _sectie(HERSTELDOC.read_text(encoding="utf-8"), "3. Formulier 2 — executor (`ai-server-manager-executor`)")
    vlak = " ".join(stap3.split())
    assert "/api/docs" not in vlak, "stap 3 verwijst voor de koppelcode nog naar /api/docs"
    for tekst, bestand in (
        ("Koppelcode voor de executor maken", ONBOARDING / "executor" / "ExecutorKoppelen.tsx"),
        ("Executor installeren en koppelen", ONBOARDING / "executor" / "page.tsx"),
        ("Uitleg executor", ONBOARDING / "OnboardingScreen.tsx"),
    ):
        assert tekst in vlak, f"stap 3 noemt '{tekst}' niet"
        assert tekst in bestand.read_text(encoding="utf-8"), f"'{tekst}' staat niet in {bestand.name}"


def test_niet_gekoppeld_heeft_eigen_toon_en_formulier_met_verplichte_velden() -> None:
    html = executor_page(versie="0.1.0", link={"state": "nooit_gekoppeld"}, ready_checks=READY, csrf="abc", now=NOW)
    assert 'pil-niet-gekoppeld"><svg aria-hidden="true"><use href="#i-niet-gekoppeld"/></svg>Niet gekoppeld' in html
    assert "novalidate" in html and html.count('<span class="verplicht">(verplicht)</span>') >= 3
    assert 'name="csrf" value="abc"' in html and "Nee — wacht op koppeling" in html
    assert "Gereed betekent" in html  # uitleg Gereed ↔ /readyz (E10)


def test_koppelen_bezig_verbergt_het_formulier() -> None:
    link = {"state": "nooit_gekoppeld", "pending": {"started_at": "2026-11-10T11:54:00Z"}}
    html = executor_page(versie="0.1.0", link=link, ready_checks=READY, csrf="abc", now=NOW)
    assert 'name="koppelcode"' not in html and "Koppelen bezig" in html and "11:54 UTC" in html
    assert "Executor — niet gereed, koppelen bezig" in html


def test_onleesbaar_storing_zonder_formulier_en_zonder_live_rol() -> None:
    html = executor_page(
        versie="0.1.0",
        link={"state": None, "_onleesbaar": True},
        ready_checks=READY,
        csrf="",
        melding=onleesbaar_melding(),
        now=NOW,
    )
    assert 'name="koppelcode"' not in html and 'role="alert"' not in html and 'role="status"' not in html
    assert "<code>/appdata/secrets/hub-link.json</code>" in html and "Code <code>koppelstatus_onleesbaar</code>" in html
    assert 'class="pil pil-storing"><svg aria-hidden="true"><use href="#i-storing"/></svg>Niet gereed' in html
    assert "Nee — koppelstatus onleesbaar" in html and "Trace-ID" not in html


def test_melding_van_dit_verzoek_heeft_rol_alert_of_status() -> None:
    fout = executor_page(
        versie="0.1.0",
        link={"state": "nooit_gekoppeld"},
        ready_checks=READY,
        csrf="abc",
        melding={
            "toon": "fout",
            "rol": "alert",
            "titel": "Koppelen is mislukt",
            "tekst": "vaste tekst",
            "code": "hub_weigerde",
            "trace_id": "3d8a1f4e-6b2c-4e95-a7d0-91c5b8e2f364",
        },
        veldfout={"koppelcode": "Koppelcode: 12 tekens."},
        now=NOW,
    )
    assert 'role="alert" aria-labelledby="melding-titel"' in fout and "Code <code>hub_weigerde</code>" in fout
    assert 'href="#koppelcode">Naar het veld met de fout' in fout and 'aria-invalid="true"' in fout
    assert "<title>Executor — niet gekoppeld (koppelen mislukt)</title>" in fout
    info = executor_page(
        versie="0.1.0",
        link=LINKED,
        ready_checks=READY,
        csrf="",
        melding={"toon": "info", "rol": "status", "titel": "Gekoppeld met de Hub.", "tekst": "Controleer."},
        now=NOW,
    )
    assert 'role="status"' in info and 'role="alert"' not in info
    # Een onbekende rol valt terug op geen live-regio.
    leeg = executor_page(
        versie="0.1.0",
        link=LINKED,
        ready_checks=READY,
        csrf="",
        melding={"toon": "info", "rol": "<script>", "titel": "x", "tekst": "y"},
        now=NOW,
    )
    assert 'class="melding melding-info" style=' in leeg and "&lt;script&gt;" not in leeg
