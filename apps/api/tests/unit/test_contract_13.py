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
        # RV5: bij my_house komt alleen HUB_URL (M2: de executor vult in, niet de vertaling).
        ("### 3.2", "daar komt alleen `HUB_URL`"),
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


KOP_M1 = "### 8.1 Bron- en doelbinding van appplannen (M1)"
KOP_M3 = "### 8.2 Vertrouwde plannerinvoer (M3)"
KOP_M2 = "### 8.3 Afzonderlijke geheime overdracht (M2)"


@pytest.mark.parametrize(
    ("kop", "verplicht"),
    [
        (KOP_M1, ("entry_id", "version_id", "manifest_sha256", "app_id")),
        (KOP_M1, ("source.subpath", "source.commit", "publisher_key_sha256")),
        (KOP_M1, ("target.app_id", "instance_id", "expected_version")),
        (KOP_M1, ("action_scope.parameters_sha256", "vault_refs", "readback")),
        (KOP_M1, ("onvolledig", "nieuwe preview en goedkeuring", "nul kluisopvragen en nul schrijfaanroepen")),
        (KOP_M3, ("service:hub", "catalog_request_sha256", "manifest_sha256")),
        (KOP_M3, ("plan_id", "step_id", "ETag", "instance_id")),
        (KOP_M3, ("manifest_yaml", "geen uitvoerbare stap", "geen kluisvertaling")),
        (KOP_M3, ("report_step", "eigen readback", "levende bevoegde gebruikerssessie")),
        (KOP_M2, ("uitsluitend verwijzingen en onveranderlijke revisies", "eenmalig", "Geen gedeelde database")),
        (KOP_M2, ("`appgeheim`", "`enrollment-token`", "^[A-Za-z0-9][A-Za-z0-9_-]{42}$", "^enr_[A-Za-z0-9_-]{43}$")),
        (KOP_M2, ("Geen `last4`", "Alleen de SHA-256", "Pas bij de afgifte gemaakt")),
        (KOP_M2, ("POST /api/v1/executor/secret-claims", "request_sha256", "geen gedeeltelijke afgifte")),
        (KOP_M2, ("RFC 9180", "Geen trust on first use", "policy-sleutel wordt hiervoor nooit gebruikt")),
        (KOP_M2, ("`asm-kluis-afgifte-v1:` gevolgd door de tekst van `claim_sha256`", "met `-` of `_` begint")),
        (KOP_M2, ("kluis_vorm_ongeldig", "koppeling_past_niet", "kluisplekken_recept_ontbreekt")),
        (KOP_M2, ("heft de markering niet op", "tokenplek blijft leeg", "geheimvrij")),
    ],
)
def test_appplan_contract(kop: str, verplicht: tuple[str, ...]) -> None:
    tekst = _paragraaf(kop)
    for onderdeel in verplicht:
        assert onderdeel in tekst


def test_m2_staat_in_het_wijzigingslog_en_de_koppelvelden_vult_de_executor() -> None:
    """M2 (S-P2-050e): eigen kop in het 1.3-wijzigingslog; §3.2 legt het invullen van ``HUB_*`` bij de executor."""
    log = _wijzigingslog()
    assert "### Aanvulling M2 (2026-11-21, blijft `contracts 1.3`)" in log
    assert log.index("### Aanvulling M2") > log.index("### Aanvulling M1 en M3")
    p32 = _paragraaf("### 3.2 Overzicht enrollment (eigen nieuwe diensten)")
    assert "De vertaling voegt ze nooit toe." in p32 and "de executor deze env in (§8.3)" in p32
    assert "de vertaling voegt ze bij" not in p32


def test_aanvulling_c12_staat_in_het_wijzigingslog_en_in_de_kop() -> None:
    log = _wijzigingslog()
    assert KOP_C12 in log
    # Na de reviewcorrecties, binnen het 1.3-wijzigingslog.
    assert log.index(KOP_C12) > log.index("### Correcties uit de onafhankelijke review (2026-11-10")
    for n in range(1, 8):
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
        # C12-5, eigen zin (R-TECH-1, mutatie M13): het eigen manifest van een dienst maakt geen installatie.
        "Het eigen manifest van een dienst (`deploy/manifest/`), dat een I-document alleen als verwijzing in"
        " `docs` noemt, maakt dat document geen installatie.",
        # R-VEILIG-3: de 32 tekens gelden ook voor het wachtwoord in `gebruiker:wachtwoord` (ADR-0016 besluit 3).
        "de afnemer weigert korter. Ook in de vorm `gebruiker:wachtwoord` telt dat voor het wachtwoord.",
        # R-VEILIG-2: een kluisverwijzing of geheim van de Hub onder een accountnaam is een fout, geen waarschuwing.
        "Een kluisverwijzing of een geheim van de Hub onder een accountnaam is een fout"
        " (`account_gegevens_verboden`, een weigering), nooit een waarschuwing.",
        # R-VEILIG-2: de woordenlijst van de standaard, aangevuld (besluit regisseur).
        "Een accountnaam is een geheimnaam met een woord uit de vaste woordenlijst van de standaard (ADR-0016 W2),"
        " aangevuld met `INIT`, `LOGIN` en `BASIC_AUTH`, en met namen die de aanmelding bij de app zelf zijn, zoals"
        " `*_INIT_PASSWORD`, `*_BASIC_AUTH_PASSWORD`, `JUPYTER_TOKEN` en de kale naam `PASSWORD`.",
        # R-VEILIG-2: wie de lijst en de validator bouwt, en dat de Hub opnieuw toetst.
        "De woordenlijst en de validator bouwt `appstore-en-fork` (vervolg op ADR-0016 W2); de Hub en de executor"
        " toetsen dezelfde lijst opnieuw vóór het invullen (`ai-server-manager`, S-P2-050).",
        # R-VEILIG-2: `secret_in_form` is nooit te accepteren onder een accountnaam.
        "`secret_in_form` (alleen bij een parameter met `source: generated` en `secret: true`, nooit onder een"
        " accountnaam)",
        # R-MANIFEST-1: de regel voor geheime parameters noemt ook de tweede uitzondering.
        "**Geheime parameters die de Hub maakt** (§3.1 a en de tweede uitzondering van §3.1)",
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
    assert "nooit voor de aanmelding van een beheerder of dienstaccount (`account_gegevens_verboden`, §9)" in p31
    # §3.2 noemt het enrollment-token niet meer "de enige" uitzondering.
    assert "(de enige, kortlevende uitzondering" not in _paragraaf("### 3.2 Overzicht enrollment")


#: De kernzinnen van de tweede uitzondering (C12-3), elk met een eigen test: een afzwakking van één zin maakt precies
#: die test rood, los van de sha256-pin (R-TECH-1 en R-VEILIG-1 van de review van S-P2-C12; V-003).
KERNZINNEN_3_1 = {
    # Alleen een geheim dat de Hub maakt, en alleen via value_from (niet "elk geheim").
    "alleen_geheim_van_de_hub": "een geheim dat de Hub maakt (`source: generated` + `secret: true`, punt (a) hieronder)"
    " mag via `custom_app.env[].value_from` als omgevingsvariabele in het formulier van een Custom App komen.",
    # R-VEILIG-1: een manifest bevat nooit een kluisverwijzing; alleen de vertaling zet haar (ADR-0015 besluit 5).
    "manifest_nooit_een_kluisverwijzing": "Een manifest bevat nooit een kluisverwijzing: het noemt alleen de parameter;"
    " een kluisverwijzing in een manifest wordt geweigerd (`vault_ref_not_allowed`; de verwijzing zet alleen de"
    " vertaling, ADR-0015 besluit 5).",
    # R-VEILIG-1: alleen de Hub en de executor vullen in, alleen voor het doel, nooit onder een accountnaam.
    "alleen_hub_en_executor_vullen_in": "Alleen de Hub en, bij het uitvoeren, de executor vullen een kluisverwijzing"
    " `vault://app/<app_id>/<parameter>` in,",
    "alleen_voor_het_doel": "alleen voor de `app_id` van het doel van de ondertekende actie: nooit voor een andere app"
    " en nooit onder een accountnaam (§9); anders weigeren ze de actie.",
    # De kerngarantie: nooit de waarde (ook niet in verzoekhash en idempotentie-opslag).
    "nooit_de_waarde": "Vertaling, preview, goedkeuring, verzoekhash, idempotentie-opslag, audit, log en evidence"
    " bevatten nooit de waarde, hooguit de verwijzing;",
    # Nooit een geheim van de gebruiker, nooit letterlijk of via een gewone parameter, nooit een aanmelding.
    "nooit_gebruiker_letterlijk_of_account": "Dit geldt alleen voor zo'n geheim van de Hub: nooit voor een geheim van"
    " de gebruiker, nooit als letterlijke waarde of via een gewone parameter, en nooit voor de aanmelding van een"
    " beheerder of dienstaccount (`account_gegevens_verboden`, §9).",
}


@pytest.mark.parametrize("sleutel", sorted(KERNZINNEN_3_1))
def test_paragraaf_3_1_kernzin_van_de_tweede_uitzondering(sleutel: str) -> None:
    p31 = _paragraaf("### 3.1 Uitgangspunten")
    zin = " ".join(KERNZINNEN_3_1[sleutel].split())
    assert zin in p31, f"§3.1, kernzin {sleutel!r} ontbreekt of is veranderd: {zin!r}"


def test_paragraaf_3_1_laat_de_app_id_niet_uit_het_manifest_komen() -> None:
    """R-VEILIG-1: de oude tekst liet het manifest een verwijzing dragen, met de app_id 'uit het manifest'."""
    p31 = _paragraaf("### 3.1 Uitgangspunten")
    assert "met de vaste `app_id` uit het manifest" not in p31
    assert "Manifest, vertaling, preview" not in p31


def test_paragraaf_8_zegt_wat_een_preview_minimaal_toont() -> None:
    """C12-4 (melding R-VEILIG bij S-P2-040): elk gezet veld door de maskeerregel; eigen opdracht 501."""
    p8 = _paragraaf("## 8. Risicobeleid")
    assert "**Preview (gebonden diff; aanvulling C-12):**" in p8
    assert "elk gezet veld" in p8
    assert "De hele wijziging gaat door die regel; een gezet veld weglaten mag niet." in p8
    assert "`***`" in p8
    assert "`command` of `entrypoint`" in p8 and "`501 capability_unavailable`" in p8
    assert "ADR-0030-policy-engine-approvals-executor.md` besluit 32" in p8


def test_paragraaf_8_preview_toont_van_een_omgevingsvariabele_alleen_de_naam() -> None:
    """C12-4, eigen test (R-TECH-1): de maskeerregel voor geheimen en omgevingsvariabelen staat er volledig."""
    p8 = _paragraaf("## 8. Risicobeleid")
    zin = "elk door dezelfde maskeerregel: een geheim staat er als `***` en van een omgevingsvariabele staat alleen de"
    zin += " naam erin."
    assert zin in p8


def test_paragraaf_11_kent_de_waarde_echte_hub() -> None:
    """C12-6 (melding uit jelly-leon S-G1-17): `NIET GEVALIDEERD (echte Hub)` is een vaste validatiewaarde."""
    tekst = _tekst(CONTRACT)
    begin = tekst.index("## 11. Bewijs en Excel")
    p11 = tekst[begin : tekst.index("## 12.", begin)]
    assert "| `NIET GEVALIDEERD (echte Hub)` |" in p11


def _paragraaf_11() -> str:
    tekst = _tekst(CONTRACT)
    begin = tekst.index("## 11. Bewijs en Excel")
    return " ".join(tekst[begin : tekst.index("## 12.", begin)].split())


@pytest.mark.parametrize(
    "zin",
    [
        "code + CI + simulator-E2E geslaagd ⇒ `status: Bezig`.",
        "Rest alleen nog de test op de echte NAS, op echte hardware of met een echt account, dan blijft het `Bezig`,"
        " met in `opmerking` de aantekening `alleen NAS-test nodig` en in `validatie` de passende"
        " `NIET GEVALIDEERD (…)` (besluit van de gebruiker 2026-11-11).",
        "`Geblokkeerd` (met `NIET GEVALIDEERD (…)`) alleen voor werk dat zonder de echte NAS, hardware of het account"
        " niet verder kan worden gebouwd.",
        "In beide gevallen staat in `blokkade` wat er nog nodig is.",
    ],
)
def test_paragraaf_11_statusregel_volgt_het_besluit_van_de_gebruiker(zin: str) -> None:
    """C12-7: de statusregel van §11 volgt het statusbesluit van de gebruiker van 2026-11-11 (R3)."""
    assert " ".join(zin.split()) in _paragraaf_11(), zin


def test_paragraaf_11_zet_alleen_nas_test_nooit_op_geblokkeerd() -> None:
    """De oude regel zette werk waarvoor alleen de NAS-test rest op `Geblokkeerd`; dat strijdt met R3."""
    assert "(of `Geblokkeerd` als echte NAS/hardware/account nodig is)" not in _paragraaf_11()


@pytest.mark.parametrize(
    ("rid", "afkorting", "moment", "woorden"),
    [
        (
            "C1.3-ASF-15",
            "ASF",
            "P3 (S-P3-490)",
            # R-VEILIG-1 en -2: de validator weigert een kluisverwijzing in een manifest en kent de aangevulde lijst.
            (
                "`accounts`",
                "`account_ongeldig`",
                "`docs/MANIFESTSTANDAARD.md`",
                "`vault_ref_not_allowed`",
                "`INIT`",
                "`LOGIN`",
                "`BASIC_AUTH`",
            ),
        ),
        ("C1.3-JLP-15", "JLP", "P3 (S-P3-445)", ("`credentialSecret`", "`tools/validator_kopie.py`", "besluit 7")),
        (
            "C1.3-HCH-16",
            "HCH",
            "P3 (S-P3-360)",
            ("`credentialSecret`", "32 tekens", "integrations/sources.py`", "`gebruiker:wachtwoord`"),
        ),
        # R-MANIFEST-1: de Hub- en executorkant van de tweede uitzondering van §3.1 (C12-3).
        (
            "C1.3-ASM-24",
            "ASM",
            "P2 (S-P2-050, met C1.3-ASM-18)",
            (
                "tweede uitzondering",
                "`values.envs`",
                "vullen een kluisverwijzing `vault://app/<app_id>/<parameter>` in `values.envs` van een Custom App"
                " alleen in als `<app_id>` de `app_id` van het doel van de ondertekende actie is",
                "nooit onder een accountnaam",
                "`501 capability_unavailable`",
                "apps/policy/src/asm_policy/params.py`",
                "apps/executor/src/executor/uitvoeren.py`",
            ),
        ),
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
