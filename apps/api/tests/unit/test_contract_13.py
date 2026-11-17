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
    """De onafhankelijke review van 1.3 (ADR-0028) blijft `contracts 1.3`: RV1–RV13 staan in het 1.3-wijzigingslog."""
    log = _wijzigingslog()
    assert "### Correcties uit de onafhankelijke review (2026-11-10, blijft `contracts 1.3`; ADR-0028)" in log
    for n in range(1, 14):
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


# --- Aanvulling C-12 (2026-11-17, blijft `contracts 1.3`; ADR-0031) -------------------------------------------------

ADR_C12 = Path(__file__).resolve().parents[4] / "docs" / "adr" / "ADR-0031-contract-1-3-aanvulling-c12.md"
KOP_C12 = "### Aanvulling C-12 (2026-11-17, blijft `contracts 1.3`; ADR-0031)"


def _paragraaf(kop: str) -> str:
    """De tekst van een kop tot de volgende kop van niveau 2 of 3, met regelafbrekingen als één spatie."""
    tekst = _tekst(CONTRACT)
    begin = tekst.index(f"\n{kop}")
    volgende = re.search(r"\n#{2,3} ", tekst[begin + 1 :])
    eind = begin + 1 + volgende.start() if volgende else len(tekst)
    return " ".join(tekst[begin:eind].split())


def test_versieregel_blijft_letterlijk_staan() -> None:
    """De aanvulling blijft 1.3: de versieregel (met de peildatum) is gelijk, want de versieparsers en de driftregel
    van de kopieën lezen haar letterlijk (ADR-0031)."""
    eerste = _tekst(CONTRACT).splitlines()[2]
    assert eerste == (
        "Versie: `contracts 1.3` · Peildatum 2026-11-10 · Eigenaar: `lvos04/ai-server-manager` (bron van waarheid)."
    )


def test_aanvulling_c12_staat_in_het_wijzigingslog_en_in_de_kop() -> None:
    log = _wijzigingslog()
    assert KOP_C12 in log
    # Na de reviewcorrecties, binnen het 1.3-wijzigingslog.
    assert log.index(KOP_C12) > log.index("### Correcties uit de onafhankelijke review (2026-11-10")
    for n in range(1, 7):
        assert f"- C12-{n}. " in log, f"C12-{n} ontbreekt"
    assert ADR_C12.is_file()
    kop = _tekst(CONTRACT).split("## Wijzigingslog")[0]
    assert "`ai-server-manager:docs/adr/ADR-0031-contract-1-3-aanvulling-c12.md`" in kop
    assert "ADR-0016-beheerder-en-dienstaccount-zonder-geheim-in-het-formulier.md" in kop


@pytest.mark.parametrize(
    "zin",
    [
        # C12-1: het veld `accounts` met precies twee aanmaakwijzen, zonder waarde.
        "**`accounts: [{id, rol: beheerder|dienst, aanmaak: eerste_gebruik|door_beheerder, afnemer, rechten, controle,"
        " beschrijving_nl}]`** (optioneel)",
        "het manifest verklaart alleen wat er moet bestaan, nooit een waarde",
        # C12-2: accountgegevens weigeren; een geheim van de Hub is nooit een aanmelding.
        "wordt geweigerd (`account_gegevens_verboden`)",
        "is nooit de aanmelding van een beheerder of dienstaccount (`account_gegevens_verboden`; niet te accepteren)",
        # BN-C12-3: de 32-tekens-eis van ADR-0016 besluit 3.
        "Het wachtwoord of token van een dienstaccount is minstens 32 willekeurige tekens uit een generator; de afnemer"
        " weigert korter.",
        # EX47 noemt de accountgegevens.
        "een geheime waarde of accountgegevens (`account_gegevens_verboden`) in een manifest.",
        # C12-5: één weg per document.
        "Een controlelijst (`kind: checklist`) staat nooit naast een installeerbaar manifest",
    ],
)
def test_paragraaf_9_heeft_de_aanvulling_c12(zin: str) -> None:
    p9 = _paragraaf("## 9. Manifeststandaard")
    assert " ".join(zin.split()) in p9, zin
    for term in ("`accounts", "eerste_gebruik", "door_beheerder", "`account_gegevens_verboden`"):
        assert term in p9, term


def test_paragraaf_9_ex47_noemt_geen_kale_geheime_waarde_meer() -> None:
    p9 = _paragraaf("## 9. Manifeststandaard")
    ex47 = p9[p9.index("Weigeren vóór uitvoering (EX47):") :]
    assert not ex47.rstrip().endswith("een geheime waarde in een manifest.")


def test_paragraaf_3_1_kent_de_vault_uitzondering_maar_nooit_voor_een_account() -> None:
    """C12-3 (BN-C12-2; besluit van de gebruiker 2026-11-11 bij S-P2-500; ADR-0015 van appstore-en-fork)."""
    p31 = _paragraaf("### 3.1 Uitgangspunten")
    assert "`HUB_ENROLLMENT_TOKEN`" in p31
    assert "Tweede uitzondering (aanvulling C-12; besluit van de gebruiker 2026-11-11, S-P2-500;" in p31
    assert "`custom_app.env[].value_from`" in p31 and "`vault://app/<app_id>/<parameter>`" in p31
    assert "alleen de executor vult de waarde in" in p31
    assert "nooit voor de aanmelding van een beheerder of dienstaccount (`account_gegevens_verboden`, §9)" in p31
    # §3.2 noemt het enrollment-token niet meer "de enige" uitzondering.
    assert "(de enige, kortlevende uitzondering" not in _paragraaf("### 3.2 Overzicht enrollment")


def test_paragraaf_8_zegt_wat_een_preview_minimaal_toont() -> None:
    """C12-4 (melding R-VEILIG bij S-P2-040): elk gezet veld door de maskeerregel; eigen opdracht 501."""
    p8 = _paragraaf("## 8. Risicobeleid")
    assert "**Preview (gebonden diff; aanvulling C-12):**" in p8
    assert "elk gezet veld" in p8
    assert "De hele wijziging gaat door die regel; een gezet veld weglaten mag niet." in p8
    assert "`***`" in p8
    assert "`command` of `entrypoint`" in p8 and "`501 capability_unavailable`" in p8
    assert "ADR-0030-policy-engine-approvals-executor.md` besluit 32" in p8


def test_paragraaf_11_kent_de_waarde_echte_hub() -> None:
    """C12-6 (melding uit jelly-leon S-G1-17): `NIET GEVALIDEERD (echte Hub)` is een vaste validatiewaarde."""
    tekst = _tekst(CONTRACT)
    begin = tekst.index("## 11. Bewijs en Excel")
    p11 = tekst[begin : tekst.index("## 12.", begin)]
    assert "| `NIET GEVALIDEERD (echte Hub)` |" in p11


@pytest.mark.parametrize(
    ("rid", "afkorting", "moment", "woorden"),
    [
        ("C1.3-ASF-15", "ASF", "P3 (S-P3-490)", ("`accounts`", "`account_ongeldig`", "`docs/MANIFESTSTANDAARD.md`")),
        ("C1.3-JLP-15", "JLP", "P3 (S-P3-445)", ("`credentialSecret`", "`tools/validator_kopie.py`", "besluit 7")),
        ("C1.3-HCH-16", "HCH", "P3 (S-P3-360)", ("`credentialSecret`", "32 tekens", "integrations/sources.py`")),
    ],
)
def test_conformiteit_heeft_de_regels_van_c12(rid: str, afkorting: str, moment: str, woorden: tuple[str, ...]) -> None:
    regels = [r for r in _tekst(CONFORMITEIT).splitlines() if r.startswith(f"| {rid} |")]
    assert len(regels) == 1, rid
    m = RIJ.match(regels[0])
    assert m and m.group(2) == afkorting and m.group(5).strip() == moment, regels[0][:80]
    assert "C-12" in m.group(4)
    for woord in woorden:
        assert woord in regels[0], (rid, woord)
