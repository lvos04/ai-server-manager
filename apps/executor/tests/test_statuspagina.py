"""Statuspagina in het Peil-sjabloon 1.1.1: versie-gepinde kopie (E08), renderer in één doorgang gelijk aan de
referentie ``design/ontwerptaal/bouw/sjabloon.py`` (E07), escapen, vaste tonen, meldingsrol, onleesbaar en koppelen
bezig zonder formulier, Gereed volgens contract 1.3 §3.7."""

from __future__ import annotations

import hashlib
import importlib.util
import re
import warnings
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

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


def test_gekoppeld_en_bevestigd_is_gereed_maar_nooit_groen() -> None:
    html = executor_page(versie="0.1.0", link=LINKED, ready_checks=READY, csrf="", now=NOW)
    assert "MEGG-8GFG-2E4Y-K2RQ" in html and 'name="csrf"' not in html and "gaat via de Hub" in html
    assert "Ja — gekoppeld en bevestigd" in html
    # Totaal = slechtste controle (schrijfsleutel onbekend): nooit groen zolang de executor niets uitvoert.
    assert 'class="pil pil-onbekend"><svg aria-hidden="true"><use href="#i-onbekend"/></svg>Onbekend' in html
    assert 'class="knop knop-secundair" href="http://hub.invalid:30400">Hub openen' in html
    # Toegestane acties: toon 'nog-niet' (zandloper), niet 'gate'.
    assert 'pil-nog-niet"><svg aria-hidden="true"><use href="#i-nog-niet"/></svg>Nog niet beschikbaar' in html
    niet_bevestigd = executor_page(
        versie="0.1.0", link={**LINKED, "confirmed_at": None}, ready_checks=READY, csrf="", now=NOW
    )
    assert "Nee — wacht op bevestiging door de Hub" in niet_bevestigd and "Niet bevestigd" in niet_bevestigd


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
