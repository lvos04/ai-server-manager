"""Contract 1.3 (``docs/platform-v2/PLATFORM_CONTRACTEN.md``) en de conformiteitslijst: volledig en kopieerbaar.

- De kop zegt ``contracts 1.3``; het wijzigingslog 1.2 → 1.3 noemt elke contractgroep (a) uit de inventaris.
- Elke contractgroep staat ook in ``CONTRACT_1.3_CONFORMITEIT.md``; die lijst heeft een hoofdstuk per repo (alle 11),
  unieke ID's ``C1.3-<REPO>-<nn>`` en per regel een geldig moment (NU of een fase).
- Geen relatieve links: in een byte-gelijke kopie in een andere repo zouden ze kapot zijn (contract, kop; A35).
- De testvectoren van §4.5 staan letterlijk in het contract en kloppen met de formule (hier onafhankelijk nagerekend,
  zonder de implementatie van de Hub), ook de nieuwe vector met twee policy-sleutels.
- §11 kent de nieuwe validatiewaarden.
"""

from __future__ import annotations

import base64
import hashlib
import re
from pathlib import Path

import pytest

DOCS = Path(__file__).resolve().parents[4] / "docs" / "platform-v2"
CONTRACT = DOCS / "PLATFORM_CONTRACTEN.md"
CONFORMITEIT = DOCS / "CONTRACT_1.3_CONFORMITEIT.md"
KANDIDATEN = DOCS / "CONTRACT_1.3_KANDIDATEN.md"

REPOS = [
    "ai-server-manager",
    "home-control-hub",
    "appstore-en-fork",
    "jelly-leon-platform",
    "zoeken-en-persoonlijke-ai",
    "media-guard-ultimate",
    "media-source-optimizer",
    "my_house",
    "jelly-leon",
    "jelly-leon-web",
    "jelly-leon-clients",
]
AFKORTINGEN = {"ALG", "ASM", "HCH", "ASF", "JLP", "ZPA", "MGU", "MSO", "MH", "JL", "JLW", "JLC"}
MOMENT = re.compile(r"^(NU|P2|P3|P4-0|P4|P5|na )")
RIJ = re.compile(r"^\| (C1\.3-([A-Z]+)-(\d\d)) \| (.+) \| ([^|]+) \|$")
CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _tekst(pad: Path) -> str:
    return pad.read_text(encoding="utf-8")


def _contractgroepen() -> list[str]:
    groepen = re.findall(r"^\| \[(A\d\d)\]\(#a\d\d\) \| \(a\) \|", _tekst(KANDIDATEN), flags=re.M)
    assert len(groepen) == 36, f"verwacht 36 contractgroepen (a) in de inventaris, gevonden {len(groepen)}"
    return groepen


def _wijzigingslog() -> str:
    tekst = _tekst(CONTRACT)
    begin = tekst.index("## Wijzigingslog 1.2 → 1.3")
    eind = tekst.index("## Eerdere wijzigingen")
    return tekst[begin:eind]


def test_kop_zegt_contracts_13() -> None:
    eerste = _tekst(CONTRACT).splitlines()[:5]
    assert any(r.startswith("Versie: `contracts 1.3`") for r in eerste), eerste


def test_wijzigingslog_noemt_elke_contractgroep() -> None:
    log = _wijzigingslog()
    ontbreekt = [g for g in _contractgroepen() if f"({g})" not in log and f"({g}," not in log]
    assert not ontbreekt, f"contractgroepen zonder punt in het wijzigingslog: {ontbreekt}"


def test_conformiteit_noemt_elke_contractgroep() -> None:
    tekst = _tekst(CONFORMITEIT)
    ontbreekt = [g for g in _contractgroepen() if not re.search(rf"\b{g}\b", tekst)]
    assert not ontbreekt, f"contractgroepen die in de conformiteitslijst ontbreken: {ontbreekt}"


@pytest.mark.parametrize("pad", [CONTRACT, CONFORMITEIT], ids=lambda p: p.name)
def test_geen_relatieve_links(pad: Path) -> None:
    # Inline code (bv. regexen als `^[a-z]([-a-z0-9]*…`) is geen link; alleen de rest van de tekst telt.
    zonder_code = re.sub(r"`[^`\n]*`", "", _tekst(pad))
    links = re.findall(r"\]\(([^)\s]+)\)", zonder_code)
    relatief = [link for link in links if not link.startswith("https://")]
    assert not relatief, f"{pad.name}: relatieve links breken in een kopie: {relatief}"


def test_conformiteit_heeft_een_hoofdstuk_per_repo() -> None:
    koppen = re.findall(r"^## \d+\. ([a-z_-]+)", _tekst(CONFORMITEIT), flags=re.M)
    assert koppen[: len(REPOS)] == REPOS, koppen


def test_conformiteitsregels_hebben_unieke_id_en_geldig_moment() -> None:
    gezien: set[str] = set()
    per_afkorting: dict[str, int] = {}
    for regel in _tekst(CONFORMITEIT).splitlines():
        if not regel.startswith("| C1.3-"):
            continue
        m = RIJ.match(regel)
        assert m, f"regel past niet in de tabelvorm: {regel[:80]}"
        rid, afk, moment = m.group(1), m.group(2), m.group(5).strip()
        assert afk in AFKORTINGEN, rid
        assert rid not in gezien, f"ID dubbel: {rid}"
        assert MOMENT.match(moment), f"{rid}: onbekend moment {moment!r}"
        gezien.add(rid)
        per_afkorting[afk] = per_afkorting.get(afk, 0) + 1
    assert set(per_afkorting) == AFKORTINGEN, f"repos zonder regels: {AFKORTINGEN - set(per_afkorting)}"


def _thumbprint(x: str) -> str:
    tekst = '{"crv":"Ed25519","kty":"OKP","x":"' + x + '"}'
    return base64.urlsafe_b64encode(hashlib.sha256(tekst.encode()).digest()).rstrip(b"=").decode()


def _vingerafdruk(jwt: list[str], policy: list[str]) -> str:
    """Formule van §4.5 (1.3), los van de implementatie: beide lijsten gesorteerd op bytewaarde."""
    tekst = (
        "jl-hub-keyset-v1\njwt:"
        + ",".join(sorted(_thumbprint(x) for x in jwt))
        + "\npolicy:"
        + ",".join(sorted(_thumbprint(x) for x in policy))
    )
    bits = int.from_bytes(hashlib.sha256(tekst.encode("utf-8")).digest()[:10], "big")
    code = "".join(CROCKFORD[(bits >> (75 - 5 * i)) & 31] for i in range(16))
    return "-".join(code[i : i + 4] for i in range(0, 16, 4))


J1 = "11qYAYKxCrfVS_7TyWQHOg7hcvPapiMlrwIaaPcHURo"
P1 = "A6EHv_POEL4dcN0Y50vAmWfk1jCbpQ1fHdyGZBJVMbg"
K2 = "Kay64UG8yvCyLhqU000LxzYeUm0L_hLIl5S8kyKWbdc"


@pytest.mark.parametrize(
    ("jwt", "policy", "verwacht"),
    [
        ([J1], [P1], "MEGG-8GFG-2E4Y-K2RQ"),
        ([J1, K2], [P1], "CYRC-JS8C-14AN-JR17"),
        ([J1], [P1, K2], "HN69-2PHK-XV2D-X85W"),
        ([J1], [K2, P1], "HN69-2PHK-XV2D-X85W"),
    ],
)
def test_testvectoren_kloppen_en_staan_in_het_contract(jwt: list[str], policy: list[str], verwacht: str) -> None:
    assert _vingerafdruk(jwt, policy) == verwacht
    assert f"**`{verwacht}`**" in _tekst(CONTRACT)


def test_thumbprints_van_de_testsleutels_staan_in_het_contract() -> None:
    tekst = _tekst(CONTRACT)
    for x in (J1, P1, K2):
        assert x in tekst
        assert _thumbprint(x) in tekst


def test_paragraaf_11_kent_de_nieuwe_validatiewaarden() -> None:
    tekst = _tekst(CONTRACT)
    begin = tekst.index("## 11. Bewijs en Excel")
    p11 = tekst[begin : tekst.index("## 12.", begin)]
    waarden = ("Intel-iGPU-getest (ontwikkelmachine)", "Niet getest", "Sim-geslaagd", "NIET GEVALIDEERD (Mac/Xcode)")
    for waarde in waarden:
        assert f"`{waarde}`" in p11, waarde
    assert "C1.3-" in p11 and "REVIEW-" in p11


ADR_REVIEW = Path(__file__).resolve().parents[4] / "docs" / "adr" / "ADR-0028-review-contract-1-3.md"


def test_reviewcorrecties_staan_in_het_wijzigingslog() -> None:
    """De onafhankelijke review van 1.3 (ADR-0028) blijft `contracts 1.3`: RV1–RV12 staan in het 1.3-wijzigingslog."""
    log = _wijzigingslog()
    assert "### Correcties uit de onafhankelijke review (2026-11-10, blijft `contracts 1.3`; ADR-0028)" in log
    for n in range(1, 13):
        assert f"- RV{n}. " in log, f"RV{n} ontbreekt"
    assert ADR_REVIEW.is_file()
    assert "ADR-0028-review-contract-1-3.md" in _tekst(CONTRACT).split("## Wijzigingslog")[0]


@pytest.mark.parametrize(
    ("paragraaf", "zin"),
    [
        # RV1: de bestaande Emby-koppeling van MediaGuard blijft; de rest van het platform schrijft nooit in Emby.
        ("### 2.3", "De **bestaande** koppeling van MediaGuard"),
        # RV2: de HARDE EIS dekt ook een upgrade die de database van een mediaserver migreert.
        ("### 2.3", "geen upgrade die de database van een mediaserver migreert"),
        # RV3: geen kijkgedrag via de MediaGuard-adapter in de Hub.
        ("### 2.3", "de Hub-adapter volgt op deze route dezelfde veldenwitte lijst"),
        # RV4: de Jelly Leon-plugin pint een service_id voor §4.3.
        ("### 2.3", "ook een `service_id`"),
        # RV5: bij my_house zet de vertaling alleen HUB_URL.
        ("### 3.2", "voegt de vertaling alleen `HUB_URL` toe"),
        # RV6: vervangen bij de eerste schrijfactie van de poging, vóór het verzoek.
        ("### 3.5", "Dat gebeurt bij de eerste schrijfactie van die poging"),
        # RV7: ook een al gekoppelde dienst telt als poging.
        ("### 3.7", "409 `al_gekoppeld`"),
        # RV8: apps met een geplakte sleutelset tellen mee bij een rotatie.
        ("### 4.5", "Apps met een **geplakte** sleutelset"),
        # RV9: rol en Idempotency-Key na de authenticatie.
        ("### 4.7", "Rol (403) en `Idempotency-Key`"),
        # RV10: formulier-POST's van statuspagina's zijn met reden uitgezonderd.
        ("## 5.", "formulier-POST's van een statuspagina"),
        # RV11: types in de log-sink.
        ("### 6.1", "`op` (tijd met tijdzone)"),
        # RV12: niet gekoppeld = niet pushen; eigenaar = (source_app, domein).
        ("## 7.", "pusht hij niet en telt hij geen pogingen"),
        ("## 7.", "het paar (`source_app`, domein)"),
    ],
)
def test_reviewcorrectie_staat_in_de_juiste_paragraaf(paragraaf: str, zin: str) -> None:
    tekst = _tekst(CONTRACT)
    begin = tekst.index(f"\n{paragraaf}")
    volgende = re.search(r"\n#{2,3} ", tekst[begin + 1 :])
    eind = begin + 1 + volgende.start() if volgende else len(tekst)
    # Regelafbrekingen en inspringing tellen als één spatie (de tekst is op 120 tekens afgebroken).
    assert " ".join(zin.split()) in " ".join(tekst[begin:eind].split()), f"{zin!r} ontbreekt in {paragraaf}"
