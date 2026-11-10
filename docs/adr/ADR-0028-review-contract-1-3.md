# ADR-0028 — Onafhankelijke review van contract 1.3: twaalf correcties en een gecorrigeerde conformiteitslijst

Status: aangenomen · 2026-11-10 · ronde "contract 1.3", reviewstap · eigenaar contract: `ai-server-manager`
Bouwt op: ADR-0027 (contract 1.3 vastgesteld), ADR-0016…0020 (B03), ADR-0011/0012 (contract 1.2).
Resultaat: `docs/platform-v2/PLATFORM_CONTRACTEN.md` blijft `contracts 1.3` (nog nergens gekopieerd of gebouwd), met het
blok "Correcties uit de onafhankelijke review" (RV1–RV12) in het wijzigingslog; `CONTRACT_1.3_CONFORMITEIT.md`
gecorrigeerd en aangevuld (nu 121 punten).

## Context

De review probeerde 1.3 te weerleggen op zes vragen: is elke groep (a) uit `CONTRACT_1.3_KANDIDATEN.md` verwerkt; is
elke van de 151 meldingen traceerbaar; botst 1.3 met 1.2, `01_ARCHITECTUUR/03_RISICO_AUTONOMIE.md` of het B03-plan; zijn
enrollment, authenticatie en events eenduidig; klopt de conformiteitslijst met de code; zijn Emby, Δ-MG-DUAL, de HARDE EIS,
GPL-3.0 en de publieke repos goed verwerkt, zonder iets over de echte NAS als feit.

Wat standhield (zelf nagelopen, niet overgenomen uit het rapport van de maker):
- Alle 36 groepen (a) staan in het wijzigingslog én met hun inhoud in het contract (per groep vergeleken met het
  tekstvoorstel; waar het contract afwijkt, is het strenger of preciezer en staat het in K1–K9).
- Traceerbaarheid: een eigen script (los van `test_contract_13_kandidaten.py`) vond alle 151 meldingen precies één keer
  in §10 van de inventaris, met de juiste repo uit `CONTRACT_1.3_MELDINGEN_RONDE2.json`, een bestaande groep, de juiste
  klasse en dezelfde indeling als het overzicht in §2. De JSON is byte-gelijk aan `.lokaal/contract-issues-ronde2.json`.
- Testvectoren van §4.5 kloppen (onafhankelijk nagerekend in `test_contract_13.py`).
- Licenties: GPL-3.0 in de acht eigen repos, GPL-2.0 in jelly-leon en jelly-leon-web, per subtree in
  jelly-leon-clients. Besluiten 3, 5, 8 en 9 kloppen met `OVERDRACHT/STATUS.md`.
- Geen NAS-feiten: versies (TrueNAS 25.10.8, ix-app 1.4.8) staan er als bronwaarneming met NIET GEVALIDEERD; GPU's
  alleen als rol; Emby-versie, -poort en -installatiewijze "onbekend tot D07".
- Steekproef in de code (per repo minstens één bewering): o.a. `ENROLL_SCHEMA_VERSION = "1.2"` en
  `Field(pattern=BASE_URL)` in de Hub, `invalid_totp` met 401, `PRIVATE_NETWORKS` met `100.64.0.0/10`, `JOB_CHECKS`;
  `Referrer-Policy: no-referrer` en `Origin: null` in home-control-hub en zoeken; "laatst gepinde telt" in
  `security/pins.py` van zoeken; `service.enrollment.completed` in appstore-en-fork en jelly-leon-platform; kopieën 1.1 in
  media-guard-ultimate, media-source-optimizer en my_house; de ID's in jelly-leon-clients (ook `project.pbxproj`).

## Besluiten (de veiligste lezing; elk punt RVn staat in het contract)

1. **RV1 — Emby schrijven.** "Het platform schrijft nooit in Emby" (§2.3 regel 3) botste met bestaande code:
   MediaGuard roept bij Emby `POST /Library/Media/Updated` en `POST /Library/Refresh` aan na een vervanging en
   `POST /Items/{id}/PlaybackInfo` voor de afspeeltest (`apps/core/mediaguard/mediaserver/clients.py`, `service.py`).
   Dat is bestaande integriteit die §2.3 en Δ-MG-DUAL ("de Emby-koppeling nooit onderbreken") beschermen. Gekozen: de
   regel geldt voor de Hub, de executor, de AI, Jelly Leon en de overnametool (alleen `GET`); de bestaande
   MediaGuard-koppeling blijft; er komt geen nieuwe schrijfroute naar Emby.
2. **RV2 — reikwijdte van de HARDE EIS.** Het contract zei alleen "geen overstap van mediaserver"; B03 §10.9 punt 1
   noemt ook "niet van 10.11 naar 12.x". Gekozen: elke upgrade die de database van een mediaserver migreert, valt eronder
   (ook latere Jelly Leon-updates met upstream-migraties), met terugzetten als vorige image én snapshot. Bij (b): zonder
   upgradebewijs ook geen MediaGuard-update via de Hub of de executor; hoe de Hub het bewijs ziet, legt een ADR in P3 vast.
3. **RV3 — kijkgedrag via MediaGuard.** Met Δ-MG-DUAL bevat `sessions` in `GET /api/v1/mediaserver/status` ook wie wat
   kijkt in Jelly Leon. Regel 9 (ADR-0017) en B03 §10.9 ("geen kijkgedrag naar de Hub") zouden via de MediaGuard-adapter
   omzeild worden. Gekozen: de Hub-adapter volgt dezelfde veldenwitte lijst als de viewerclient van Jelly Leon.
4. **RV4 — `service_id` voor de Jelly Leon-plugin.** §2.3 regel 9 zei "daarna gelden §4.2–§4.7", maar §4.3 eist dat
   `service_id` in een dienst-JWT gelijk is aan de eigen opgeslagen `service_id`; zonder enrollment heeft de plugin er
   geen. Gekozen (strengste, zonder §4.3 los te laten): de stap "Hub-sleutelset kopiëren" (Δ-HUB-JL) levert ook een
   `service_id` uit het register, die de plugin mee pint.
5. **RV5 — `HUB_URL` bij my_house.** §3.2/§9 verbieden `HUB_*` als manifestparameter en laten de vertaling ze alleen
   toevoegen "als de Hub koppelt"; my_house leest `HUB_URL` voor de link "Terug naar de Hub" zonder koppeling. Gekozen:
   bij my_house zet de vertaling alleen `HUB_URL`, nooit een token of vingerafdruk.
6. **RV6 — onleesbaar koppelbestand.** Niet vastgelegd was wanneer het bestand vervangen wordt. Vervangt een dienst pas
   na een geslaagde koppeling (zoals jelly-leon-platform nu doet), dan kan hij `pending` en de hash van een geweigerd
   token niet vastleggen en probeert hij na elke herstart opnieuw (en telt hij mee voor de 401-limiet van de Hub per
   bron-IP). Gekozen, zoals home-control-hub al doet: vervangen bij de eerste schrijfactie van de poging, vóór het
   verzoek; `/readyz` blijft 200; de HTTP-uitkomst per vaste code staat erbij.
7. **RV7 — al gekoppeld.** "Elke formulier-POST telt mee" noemde de al gekoppelde dienst niet; drie diensten tellen hem
   nu niet. Gekozen: ook die telt (409 `al_gekoppeld`, geen verzoek naar de Hub); één regel zonder uitzondering is
   eenvoudiger te testen en kost niets.
8. **RV8 — sleutelrotatie en geplakte sleutelsets.** "De Hub ondertekent pas met een nieuwe sleutel als elke actieve
   dienst ... meldt" dekte my_house en de Jelly Leon-plugin niet (geen `GET /connector/v1/hub-link`). Gekozen: zij tellen
   mee; hoe de Hub dat weet, legt een ADR vast vóór de rotatie gebouwd wordt.
9. **RV9 — controlevolgorde.** Rol en `Idempotency-Key` komen ná de authenticatie (zo bouwen de executor en
   home-control-hub het al): zonder geldige authenticatie altijd 401.
10. **RV10 — `Idempotency-Key` en formulieren.** De uitzonderingenlijst van §5 leek gesloten, maar een browserformulier
    (koppelen, sleutelformulieren van de executor) kan geen header meesturen; elke repo moest dat zelf verzinnen.
    Gekozen: expliciete uitzondering met reden; andere uitzonderingen alleen met ADR.
11. **RV11 — log-sink.** `op` en `trace_id` hadden geen type; vastgelegd zoals de Hub ze afdwingt.
12. **RV12 — events.** (a) Na ontkoppelen of intrekken heeft een dienst geen token; `unlinked`/`revoked` kunnen dan
    niet aankomen. Vastgelegd wat alle vier diensten al doen: niet gekoppeld = niet pushen en geen pogingen tellen.
    (b) Het domein `media` had twee eigenaren (Jelly Leon en MediaGuard); de eigenaar is nu het paar
    (`source_app`, domein).

**Conformiteitslijst:** C1.3-JLP-02 en C1.3-JLP-03 beschreven een stand die niet in de code staat (de teller per bron-IP
en voor de dienst bestaat al; de code voor een onleesbaar bestand is `hub_link_onleesbaar`, niet `koppeling_onbekend`)
en zijn gecorrigeerd. Aangevuld met de gevolgen van RV1–RV12 per repo, met regelnummers waar de code nu afwijkt (o.a.
`hub_adres[:500]`/`koppelcode[:64]` vóór de controle in home-control-hub, `http`/`https`-Origin in de executor),
Δ-HUB-2 als repowerk van ai-server-manager (groep C12 ontbrak daar) en het nieuwe punt C1.3-MH-07 (de delta-matrix van
my_house noemt nog "enrollment via `HUB_URL`").

**EVIDENCE (C1.3-ASM-15, in deze repo):** de maker kon voor de contractstap geen EVIDENCE-regel schrijven, omdat
`test_evidence_contract.py` en `tools/excel/update_excel.py` de 1.3-waarden en -ID's nog niet kenden. De review bouwt
dat punt (het is NU-werk van deze repo en blokkeerde het bewijs): de test kent de nieuwe waarden, de regel "`Niet getest`
alleen bij `Niet gestart`", de consistentie `blokkade` → `validatie` en de vorm van `C1.x-…`/`REVIEW-…`; de Excel-bijwerker
zet zulke regels in het overzicht `contractpunten_en_reviews` van zijn uitvoer in plaats van ze als "geen rij gevonden"
te melden. Twee bestaande rijen (B01-001, I23-23-08) noemden in `blokkade` een NIET GEVALIDEERD die niet in `validatie`
stond (één met de niet-bestaande waarde "hardware/echte NAS"); die zijn rechtgezet. Daarna kreeg `EVIDENCE.json` de regels
`REVIEW-ai-server-manager-contract-1.3` en `C1.3-ASM-15` (status `Bezig`, validatie `Unit-getest`).

## Alternatieven

- *Een versie 1.3.1 uitbrengen:* verworpen; 1.3 is nog nergens gekopieerd (C1.3-ALG-01 is de volgende stap), dus de
  correcties horen bij 1.3 zelf, zoals de review van 1.2 (ADR-0012).
- *RV1: MediaGuard ook verbieden in Emby te schrijven:* verworpen; dat schakelt bestaande integriteit uit (bibliotheek
  bijwerken na een vervanging) en breekt Δ-MG-DUAL.
- *RV4: dienst-JWT's voor de plugin zonder `service_id`-controle:* verworpen; dan zou een dienst-JWT voor een andere
  registratie met dezelfde sleutel ook bij de plugin werken.
- *RV7: al gekoppeld uitdrukkelijk niet laten tellen (zoals drie diensten nu doen):* verworpen; "elke POST telt" zonder
  uitzondering is eenduidiger, en na de koppeling gebruikt niemand het formulier nog.

## Gevolgen

- Geen enkele repo is gebroken: de correcties raken punten die nog niet gebouwd zijn (P3/P4) of leggen vast wat de
  referentie-implementatie (home-control-hub) al doet. Het werk staat per repo in de conformiteitslijst.
- `test_contract_13.py` bewaakt het blok met de reviewcorrecties en de kernzinnen ervan.
- ADR-0027 punt 12 ("tot dat gebouwd is, schrijft deze repo zulke regels nog niet") is hiermee ingehaald.
- Niets hiervan is op een echte NAS, met echte accounts of op echte hardware gevalideerd; de codemetingen zijn gelezen
  (grep en bestandsinhoud), niet uitgevoerd in de andere repos.

## Verificatie

- `apps/api/tests/unit/test_contract_13.py`, `test_contract_13_kandidaten.py`, `test_keyset_fingerprint.py`.
- `apps/api/tests/unit/test_evidence_contract.py` en `tools/excel/tests/test_update_excel.py`
  (`test_contractpunten_en_reviews_in_eigen_overzicht`).
- Eigen traceerbaarheidsscript (alle 151 meldingen, repo, groep, klasse) en een padcontrole van de conformiteitslijst
  (alle genoemde bestanden bestaan, behalve de als "nieuw" gemarkeerde).
