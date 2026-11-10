"""Statuspagina in het Peil-sjabloon: versie-gepinde kopie (O-14), escapen, vaste toonwaarden, koppelen niet groen."""

from __future__ import annotations

import hashlib
import re
import warnings
from datetime import UTC, datetime
from pathlib import Path

from executor.statuspagina import executor_page, render, template

BRON = Path(__file__).resolve().parents[3] / "design" / "ontwerptaal" / "statuspagina.html"
# Pin (ONTWERPTAAL §14, Peil 1.1.1 E08): versie + sha256 van de kopie,
# gelijk aan de bron op commit 172ee87 (Peil 1.1.0).
PIN_VERSIE = (1, 1, 0)
PIN_SHA256 = "be766cc4bf6962772a8dfc77996da34040fa94698403a9625e33545fa9ee62c8"


def _versie(tekst: str) -> tuple[int, ...]:
    m = re.search(r"Peil statuspagina-sjabloon (\d+)\.(\d+)\.(\d+)", tekst)
    assert m, "sjabloon zonder Peil-versie in de kopcommentaar"
    return tuple(int(x) for x in m.groups())


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


def test_render_escapet_en_kent_als_niet_elk() -> None:
    tpl = "<!--ALS:a-->[{{x}}]<!--/ALS:a--><!--NIET:a-->leeg<!--/NIET:a--><!--ELK:l-->({{n}})<!--/ELK:l-->"
    assert render(tpl, {"a": True, "x": "<script>", "l": [{"n": 1}, {"n": "&"}]}) == "[&lt;script&gt;](1)(&amp;)"
    assert render(tpl, {"a": False}) == "leeg"


def test_gekoppeld_is_neutraal_en_toon_alleen_uit_vaste_lijst() -> None:
    now = datetime(2026, 11, 9, 11, 56, tzinfo=UTC)
    link = {"state": "gekoppeld", "first_linked_at": "2026-11-09T10:00:00Z", "linked_at": "2026-11-09T10:00:00Z",
            "hub_url": "http://hub.invalid:30400", "keyset_fingerprint": "MEGG-8GFG-2E4Y-K2RQ"}  # fmt: skip
    html = executor_page(
        versie="0.1.0", link=link, ready_checks=[{"name": "geheimen", "status": "ok"}], csrf="", now=now
    )
    assert 'class="pil pil-neutraal"' in html and "Gekoppeld" in html and "MEGG-8GFG-2E4Y-K2RQ" in html
    assert 'name="csrf"' not in html and "gaat via de Hub" in html  # formulier weg na de eerste koppeling
    assert 'pil-gezond"><svg aria-hidden="true"><use href="#i-gezond"/></svg>Niet' not in html
    # Totaal nooit groen zolang de executor niets uitvoert (schrijfsleutel en acties volgen in P2).
    assert 'class="pil pil-onbekend"><svg aria-hidden="true"><use href="#i-onbekend"/></svg>Niet gereed' in html


def test_veldfout_springt_naar_het_veld_en_toont_geen_invoer() -> None:
    html = executor_page(
        versie="0.1.0",
        link={"state": "nooit_gekoppeld"},
        ready_checks=[],
        csrf="abc",
        melding={"toon": "fout", "titel": "Koppelen is mislukt", "tekst": "vaste tekst"},
        veldfout={"koppelcode": "Koppelcode: 12 tekens."},
    )
    assert 'href="#koppelcode">Naar het veld met de fout' in html
    assert 'aria-invalid="true"' in html and "Koppelcode: 12 tekens." in html
    assert "<title>Executor — niet gekoppeld (koppelen mislukt)</title>" in html
