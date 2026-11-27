"""De overstapvoorwaarden uit contract §2.3 regel 7a horen ook in A17."""

from pathlib import Path

A17 = Path(__file__).resolve().parents[4] / "docs/platform-v2/04_BESTAANDE_APPS/A17_JELLYFIN.md"


def test_rapport_terugval_en_akkoord_gaan_voor_de_overstap() -> None:
    beslissing = A17.read_text(encoding="utf-8").partition("## Testcase en beslissing")[2]
    tekst = " ".join(beslissing.casefold().split())
    voorbereiding, overstap, voorwaarden = tekst.partition("schakel pas over na")
    assert overstap, "A17 mist het beslismoment voor de overstap"
    assert "het vastgelegde akkoord van de gebruiker" in voorwaarden
    proef, akkoord, beoordeling = voorbereiding.partition("vraag de gebruiker om uitdrukkelijk akkoord")
    assert akkoord, "Het akkoord van de gebruiker moet vóór de overstap staan"
    assert "op het rapport en op elk verschil afzonderlijk" in beoordeling
    assert "één onbeoordeelde afwijking blokkeert de overstap" in beoordeling

    assert "op een kopie" in proef
    assert "beschikbaar als terugval" in proef
    assert "vóór/na-rapport per gebruiker" in proef
    for gegeven in (
        "gezien-status",
        "hervatpositie",
        "favorieten",
        "beoordelingen",
        "spoorkeuzes",
        "gebruikers",
        "rechten",
    ):
        assert gegeven in proef
    assert "vorige image samen met de bijbehorende snapshot" in proef


def test_a17_verwijst_naar_het_contract_en_het_besluit() -> None:
    tekst = A17.read_text(encoding="utf-8")
    for naam, doel in (
        (
            "contract §2.3 regel 7a",
            "../PLATFORM_CONTRACTEN.md#23-bestaande-apps-mediaguard-mso-my_house-jellyfinjelly-leon-emby",
        ),
        ("ADR-0020", "../../adr/ADR-0020-kijkgeschiedenis-altijd-beschikbaar-en-emby-overname.md"),
    ):
        assert f"[{naam}]({doel})" in tekst
        assert (A17.parent / doel.split("#")[0]).is_file()
