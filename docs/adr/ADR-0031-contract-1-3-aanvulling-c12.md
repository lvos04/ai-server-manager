# ADR-0031 — Contract 1.3, aanvulling C-12: accounts in de manifeststandaard en vier open contractmeldingen

Status: aangenomen · 2026-11-17 · stap S-P2-C12 (deel A: de bron) · eigenaar contract: `ai-server-manager`
Bouwt op: ADR-0027 (contract 1.3), ADR-0028 (review 1.3, vorm van een aanvulling die 1.3 blijft), ADR-0030 besluit 32
(preview); `appstore-en-fork:docs/adr/ADR-0016-beheerder-en-dienstaccount-zonder-geheim-in-het-formulier.md` (besluit
C-12, uitgewerkt), `appstore-en-fork:docs/adr/ADR-0015-vault-verwijzing-geheimen-in-de-vertaling.md` (vault-verwijzing
voor Custom Apps), `jelly-leon-platform:docs/adr/ADR-0027-controlelijsten-bestaande-apps.md` (één weg per document).
Resultaat: `docs/platform-v2/PLATFORM_CONTRACTEN.md` blijft `contracts 1.3`, met het blok "Aanvulling C-12" (C12-1 tot
en met C12-6) in het wijzigingslog; `CONTRACT_1.3_CONFORMITEIT.md` krijgt C1.3-ASF-15, C1.3-JLP-15 en C1.3-HCH-16.
Niets hiervan is op een echte NAS, met echte accounts of op echte hardware gevalideerd.

## Context

De gebruiker koos op 2026-11-11 bij vraag C-12 optie 1: een beheerder of dienstaccount van een app komt er zonder geheim
in het Custom App-formulier. Het ontwerp staat in ADR-0016 van appstore-en-fork (stap S-P2-510); de regels W2 en W3
(geheimen en accountgegevens weigeren, opnieuw toetsen na het invullen) zijn daar gebouwd in S-P2-520, het veld
`accounts` (W1) volgt in S-P3-490. ADR-0016 besluit 9 vraagt de eigenaar van het contract om kop 9 aan te vullen, vóór
de gate van P2 en vóór de schrijvers van P3 die het veld gebruiken (S-P3-490, S-P3-445, S-P3-360; V-018).

Daarnaast stonden vier contractmeldingen open die dezelfde ronde kunnen meenemen, zodat de tien kopieën maar één keer
opnieuw worden overgenomen:
- ADR-0015 van appstore-en-fork (besluit van de gebruiker 2026-11-11 bij S-P2-500): vault-verwijzingen ook voor een
  omgevingsvariabele van een Custom App. Dat botst met §3.1 ("nooit geheimen in het Custom App-formulier").
- R-VEILIG bij S-P2-040: §8 ("menselijke goedkeuring per gebonden diff") zegt niet welke velden een preview minimaal
  toont.
- S-P3-400 (R-MANIFEST en A-HERSTEL): §9 zegt niet of een controlelijst (`kind: checklist`) naast een installeerbaar
  manifest mag staan.
- jelly-leon S-G1-17: het plan schrijft de validatiewaarde `NIET GEVALIDEERD (echte Hub)` voor, maar §11 kent haar niet.

## Besluiten

1. **De versie blijft `contracts 1.3`, met een gedateerde aanvulling (besluit regisseur BN-C12-1, optie A).** De
   versieregel ("Versie: `contracts 1.3` · Peildatum 2026-11-10 · …") blijft letterlijk staan; de aanvulling draagt haar
   eigen datum. Redenen, gemeten bij de verkenning van S-P2-C12 en nagelopen in de code:
   - "1.3" staat in code, niet alleen in tests: de `schema_version` van het koppelbestand (§3.5) in appstore-en-fork,
     home-control-hub, jelly-leon-platform en zoeken-en-persoonlijke-ai. Een 1.4 dwingt codewerk in die repos.
   - Vier versieparsers lezen alleen `x.y` (`^Versie: \`contracts (\d+\.\d+)\``: my_house en jelly-leon-platform
     `tools/contract_kopie.py`, media-guard-ultimate `scripts/kopie-herkomst.py`, media-source-optimizer
     `scripts/bronkopie.py`); een "1.3.1" breekt ze.
   - De driftregel van jelly-leon-platform vervangt letterlijk de peildatum in zijn kopie; een andere peildatum laat die
     test vallen.
   - Nadeel, bewust aanvaard: van de push van deze bron tot de kopie in jelly-leon-platform is de CI daar rood
     (`tests/repo/test_contract_kopie.py::test_geen_drift_met_de_huidige_bron`: andere tekst onder dezelfde versie).
     De regisseur sluit dat venster direct met de kopiestap in jelly-leon-platform.
2. **§9 krijgt het blok "Aanvulling C-12" (C12-1, C12-2).** De tekst is letterlijk het voorstel van ADR-0016 ("Voorstel
   voor de aanvulling van contract kop 9"): het optionele veld `accounts`, de twee aanmaakwijzen (`eerste_gebruik` voor
   de beheerder, `door_beheerder` voor een dienstaccount), de weigering `account_gegevens_verboden`, en dat een geheim
   dat de Hub maakt nooit de aanmelding van een beheerder of dienstaccount is. Op besluit van de regisseur (BN-C12-3)
   staat ook de eis van ADR-0016 besluit 3 in de contracttekst: het wachtwoord of token van een dienstaccount is
   minstens 32 willekeurige tekens uit een generator; de afnemer weigert korter. De regel "Weigeren vóór uitvoering
   (EX47)" noemt nu ook de accountgegevens.
3. **§3.1 krijgt een tweede uitzondering: een geheim van de Hub als vault-verwijzing in een omgevingsvariabele van een
   Custom App (C12-3; besluit regisseur BN-C12-2, op het besluit van de gebruiker 2026-11-11 bij S-P2-500).** Alleen
   voor een parameter met `source: generated` + `secret: true`, via `custom_app.env[].value_from`; manifest, vertaling,
   preview, goedkeuring, audit, log en evidence bevatten nooit de waarde, hooguit de verwijzing
   `vault://app/<app_id>/<parameter>`; alleen de executor vult de waarde in. Nooit voor een geheim van de gebruiker,
   nooit letterlijk of via een gewone parameter, en nooit voor de aanmelding van een beheerder of dienstaccount
   (`account_gegevens_verboden`). Dat laatste is de grens van C-12: ADR-0016 eis 1 ("er komt geen tweede uitzondering
   (C-12)") gaat over accounts, en ADR-0016 besluit 9 laat de melding van ADR-0015 uitdrukkelijk apart. C-12 zelf
   verandert §3.1 dus niet; deze uitzondering komt uit S-P2-500 en gaat alleen mee in dezelfde ronde. §3.2 noemt het
   enrollment-token daarom niet meer "de enige" uitzondering, en §8 noemt het meegeven van dit geheim als deel van de
   R2-actie. Of de executor dit al kan: nee; tot C1.3-ASM-18 gebouwd is, weigert de Hub een installatie met een
   vault-verwijzing eerlijk met `501 capability_unavailable` (ADR-0030 besluit 28).
4. **§8 zegt wat een preview minimaal toont (C12-4; besluit regisseur).** Elk gezet veld van de voorgestelde wijziging,
   ook de eigen waarden van een catalogusapp, door één maskeerregel (geheim als `***`, van een omgevingsvariabele alleen
   de naam); een gezet veld weglaten mag niet. Een installatie met `command` of `entrypoint` weigert de Hub met
   `501 capability_unavailable` tot er een installatiescherm is dat ze veilig toont. De precieze regel blijft in ADR-0030
   besluit 32 (één toonfunctie met een bewakingstest); het contract legt alleen de ondergrens vast.
5. **§9: één weg per document (C12-5; besluit regisseur: een controlelijst naast een installeerbaar manifest mag
   niet).** Een I-document is óf een installatie met een manifest (`install.method` `custom_app` of `catalog_app`), óf een
   controlelijst. Het eigen manifest van een dienst (`deploy/manifest/`), dat een I-document alleen als verwijzing in
   `docs` noemt, maakt dat document geen installatie; zo dwingt jelly-leon-platform het al af (ADR-0027 besluit 5).
   Of een controlelijst naast een adoptie (`kind: adoption`) mag staan, is hiermee niet besloten.
6. **§11: nieuwe validatiewaarde `NIET GEVALIDEERD (echte Hub)` (C12-6; besluit regisseur).** Voor bewijs dat alleen met
   de Hub-simulator of met testsleutels is beproefd. De EVIDENCE-test van deze repo leest haar vaste lijst nu uit de
   tabel van §11 (`test_vaste_lijst_is_de_tabel_van_paragraaf_11`), zodat lijst en contract niet uit elkaar lopen.
7. **Conformiteitslijst: drie punten voor P3, bestaande ID's niet hernummerd.** C1.3-ASF-15 (het veld `accounts` in de
   validator, S-P3-490, eerst), C1.3-JLP-15 (Node-RED-manifest, S-P3-445; geen `accounts` zolang de gebruiker voor
   Node-RED "Wachten" houdt, ADR-0016 besluit 7) en C1.3-HCH-16 (het profiel van home-control-hub vervalt, met de
   32-tekens-eis, S-P3-360). Hun EVIDENCE-regels komen in die stappen, niet hier.
8. **Pin en kopieën.** `apps/api/tests/unit/test_contract_pin.py` pint de nieuwe sha256 van beide bestanden. De tien
   andere repos nemen de nieuwe tekst over in een eigen kopiestap per repo (deel B van S-P2-C12), byte-gelijk vanaf de
   gepushte eind-commit van deze stap; de volle hash staat in hun pins.

## Wat niet verandert

- De versieregel, de naam `CONTRACT_1.3_CONFORMITEIT.md` en de ID-vorm `C1.3-…`; de `schema_version` `"1.3"` van het
  koppelbestand (§3.5).
- `CONTRACT_1.3_KANDIDATEN.md` (de 36 groepen van 1.3 blijven de invoer van 1.3).
- Het beleid van de Hub: `accounts` komt niet in `validate_manifest_meta` en niet in de catalogus-API (ADR-0016, keuze
  (a)); `policy_hash` blijft gelijk.
- Wat §3.1 zegt over accounts: een beheerder of dienstaccount komt nooit door het formulier, het manifest of Git.

## Alternatieven

- *`contracts 1.4`:* verworpen (BN-C12-1, optie B). Het is een conformiteitsronde met codewijzigingen in alle repos
  (`schema_version`, versie-asserts, de naam van de conformiteitslijst in pins, tools en CI, de C1.3-ID's), voor een
  aanvulling die geen bestaande regel verandert. Voordeel dat vervalt: met 1.4 geeft jelly-leon-platform alleen een
  waarschuwing in plaats van een rood venster.
- *`contracts 1.3.1`:* verworpen; vier versieparsers kennen alleen `x.y`.
- *De uitzondering van ADR-0015 apart laten:* verworpen (BN-C12-2); dan volgt een tweede ronde met opnieuw tien kopieën,
  of de afwijking van appstore-en-fork blijft staan.
- *De 32-tekens-eis alleen in ADR-0016 en S-P3-360:* verworpen (BN-C12-3); de eis bindt de afnemer, en dat is een
  contractzaak.

## Gevolgen

- Per repo een kopiestap (deel B): jelly-leon-platform eerst (sluit het rode CI-venster), dan appstore-en-fork (vóór
  S-P3-490) en home-control-hub (vóór S-P3-360), daarna de rest zodra de repo vrij is.
- EVIDENCE-tests die de vaste validatielijst zelf bijhouden (zoals in jelly-leon), kennen `NIET GEVALIDEERD (echte Hub)`
  nog niet; een repo die de waarde gebruikt, past zijn test aan in een eigen stap.
- `docs/platform-v2/03_INSTALLATIE/I10_NODE_RED.md` en `docs/platform-v2/02_BOUWPLANNEN/B12_BACKUP_HERSTEL.md` volgen in
  dezelfde stap ADR-0016 (besluit 6 en 7, eis 9); hun kopieën in de andere repos hebben geen drifttest (V-132).
- POORTEN P-CONTRACT (plan) noemt als besluiten ADR-0027, -0028 en -0029; ADR-0031 hoort erbij.

## Verificatie

- `apps/api/tests/unit/test_contract_13.py`: de versieregel letterlijk, het blok "Aanvulling C-12" met C12-1 tot en met
  C12-6, de kernzinnen in §3.1, §8, §9 en §11, en de drie conformiteitsregels (rood zonder de aanvulling).
- `apps/api/tests/unit/test_evidence_contract.py`: de vaste lijst is precies de tabel van §11.
- `apps/api/tests/unit/test_contract_pin.py`: de nieuwe sha256 van beide bestanden (rood met de oude).
