# POORTEN - kwaliteitspoorten per stap

Dit bestand hoort bij het uitvoeringsplan van TrueNAS Home Platform V2. Het beschrijft wat A-BOUW na ELKE stap zelf
draait, en wat R-EERLIJK en A-GATE daarna onafhankelijk kunnen herhalen. Alle commando's in dit bestand zijn
teruggevonden in de repos (CI-bestanden, Makefiles, package.json, scripts) of in de vastgelegde testruns van eerdere
rondes (`<WERKMAP>/.lokaal/plan/bron/RESULTATEN_ALLE_AGENTS.jsonl`). Wat niet vast te stellen was staat er als
"ONBEKEND - eerst vaststellen met: <commando>".

`<WERKMAP>` is de map waarin de elf repos naast elkaar staan. De werkbranch is in alle repos
`ccr-c133d7a0-kuz1cv`.

Inhoud:

- 0. Gebruik van dit bestand (wie, wanneer, omgeving, CI-controle, rapportvorm)
- 1. Poorten per repo: P-ai-server-manager, P-home-control-hub, P-appstore-en-fork, P-jelly-leon-platform,
  P-zoeken-en-persoonlijke-ai, P-media-guard-ultimate, P-media-source-optimizer, P-my_house, P-jelly-leon,
  P-jelly-leon-web, P-jelly-leon-clients
- 2. Algemene poorten: P-GIT, P-CONTRACT, P-VEILIG, P-EERLIJK, P-PEIL, P-HARDE-EIS, P-INSTALLATIE, P-EXCEL
- 3. Als een poort faalt (vaste beslisboom)
- 4. Open punten (ONBEKEND) en bronnen

---

## 0. Gebruik van dit bestand

### 0.1 Wie draait wat, en wanneer

| Wie | Wat | Wanneer |
|---|---|---|
| A-BOUW | De snelle variant van P-<repo> tijdens het werk; vóór de commit de volledige variant van P-<repo> voor elk geraakt deel; daarna P-GIT en elke algemene poort die volgens 0.4 bij de wijziging hoort; na de push de CI-controle (0.5). | Na elke stap, vóór de melding "stap klaar". |
| A-HERSTEL | Dezelfde poorten als A-BOUW, alleen voor het herstelde deel plus de poort die faalde. | Na elke herstelpoging (zie hoofdstuk 3). |
| R-EERLIJK | Herhaalt zelf: `git status`, `git log origin/ccr-c133d7a0-kuz1cv..HEAD`, de CI-run op de gemelde commit, P-EERLIJK en een steekproef uit de snelle variant. Vergelijkt de uitkomst met het rapport van A-BOUW. | Na elke stap die A-BOUW klaar meldt. |
| A-GATE | Herhaalt de volledige variant van P-<repo> voor alle repos van de fase, plus alle algemene poorten. | Aan het eind van een fase, vóór de fase-overgang. |
| R-TECH, R-VEILIG, R-HARDE-EIS, R-MANIFEST, R-ONTWERP | Gebruiken de bijbehorende poort als controlelijst: P-<repo> (R-TECH), P-VEILIG (R-VEILIG), P-HARDE-EIS (R-HARDE-EIS), P-INSTALLATIE (R-MANIFEST), P-PEIL (R-ONTWERP). | Bij hun review. Het agentmodel in het hoofdplan is leidend voor wanneer welke reviewer wordt ingezet. |

Een stap is pas klaar als: (1) de lokale poorten groen zijn, (2) de commit gepusht is, (3) de CI-run op precies die
commit groen is, (4) EVIDENCE.json klopt met wat echt gemeten is (P-EERLIJK). Ontbreekt een van de vier, dan is de
stap niet klaar en heet hij in het rapport "Bezig" of "Geblokkeerd", nooit "klaar".

### 0.2 Vaste begrippen

- **Snelle variant**: alleen de controles voor het geraakte deel. Bedoeld om tijdens het werk vaak te draaien.
  Elk commando draait LOS, met een eigen exitcode in het rapport (zoals regel O1 in de prompts van `AGENTEN.md`). In de
  tabellen "Snel" staan ze daarom als "`a`; los daarna `b`". Staat er toch ergens (ook in "Volledig" of in een
  algemene poort) een keten als `make lint && make test`, draai dan elk deel los: anders slaat een rode lint de tests
  over en ziet de reviewer niet alle uitkomsten. Uitzonderingen die WEL aan elkaar vast blijven: `cd <map> && ...`
  (het tweede deel hoort in die map) en "eerst maken, dan vergelijken" (bv. `make openapi && git diff --exit-code
  docs/openapi/`).
- **Volledige variant**: dezelfde controles als de CI van de repo, in dezelfde volgorde. Verplicht vóór de commit
  die een stap afsluit.
- **Zwaar: ja**: het commando bouwt een image, draait Gradle, start containers of draait een testsuite die
  minuten duurt en veel geheugen vraagt. Zware commando's draaien machinebreed NA elkaar, via de lock die erbij
  staat. **Zwaar: nee**: mag naast ander werk draaien.
- **Lock**: drie lockbestanden in `<WERKMAP>/.lokaal/`:
  - `<WERKMAP>/.lokaal/docker-build.lock` voor elke `docker build`/`docker buildx build` en voor dotnet in de
    SDK-container;
  - `<WERKMAP>/.lokaal/gradle.lock` voor elk Gradle-commando;
  - `<WERKMAP>/.lokaal/stack.lock` voor proeven die containers met een echte mediaserver of een hele stack starten.
  Gebruik: `flock <lockbestand> <commando>`. Het commando wacht dan tot een ander klaar is.
- **Databaselock**: twee extra lockbestanden, los van de drie hierboven (ze tellen niet mee bij het geheugen-wachten
  van 0.3 regel 2): `<WERKMAP>/.lokaal/hch-db.lock` (home-control-hub) en `<WERKMAP>/.lokaal/zoek-db.lock`
  (zoeken-en-persoonlijke-ai). De tests van die twee repos gebruiken vaste databasenamen en gooien die vooraf weg met
  `DROP DATABASE IF EXISTS ... WITH (FORCE)`; twee runs tegelijk breken elkaar dan af. Zie 0.3 regel 5. `flock` maakt
  het bestand zelf aan als het nog niet bestaat.
- **Richtgetal**: een aantal tests of een duur uit een eerdere meting. Het aantal tests mag stijgen. Daalt het,
  dan hoort daar een uitleg bij in het rapport (welke test is verdwenen en waarom).

### 0.3 Vaste omgeving en machineregels

De machine heeft 22 CPU's en 14,5 GiB werkgeheugen. Daarom gelden deze regels voor elk commando in dit bestand:

1. Zet `nice -n 10` voor elk zwaar commando.
2. Vóór een zwaar commando: `free -m` en `df -h /` (regel 3). Geheugen te laag = kolom "available" onder 3000 (MB),
   of "available" onder 6000 met swap meer dan 90 % gebruikt (regel "Swap": "used" meer dan 90 % van "total"). Met
   "available" 6000 of meer telt de swap niet (besluit van de gebruiker, 2026-11-11). Geheugen te laag: niet starten. Doe
   eerst ander werk van je stap en meet opnieuw. Is er niets anders te doen: wacht tot het zware commando van een
   ander klaar is (`flock <WERKMAP>/.lokaal/<lock> true` wacht vanzelf tot die lock vrij is; doe dat voor elk van de
   drie locks `docker-build.lock`, `gradle.lock` en `stack.lock`) en meet opnieuw. Blijft het geheugen te laag
   terwijl alle drie de locks vrij zijn: stop en meld onder blokkades ("geheugen te laag", met de uitvoer van
   `free -m`). Bron: `AGENTEN.md`, regel O3 in de prompts van deel 5 en kop "3.3 Weinig geheugen of
   schijf".
3. Vóór een image-build of een stackproef: `df -h /`. Is er minder dan 15 GB vrij, stop en meld. Ruim alleen eigen,
   bij naam genoemde images en containers op.
4. VERBODEN terwijl er iets bouwt: `docker system prune -a`, `docker builder prune -a`, `docker volume prune`.
   Ook `make opruimen` in jelly-leon-clients en `make clean` in ai-server-manager vallen hieronder (beide bevatten
   `docker image prune -f`, dat ook images van andere ketens weggooit). Draai die twee doelen nooit; ruim alleen
   eigen, bij naam genoemde mappen op.
5. PostgreSQL 16 draait gedeeld op `127.0.0.1:5432` (gebruiker `postgres`, geen wachtwoord). Tests maken eigen
   databases aan en ruimen die zelf op. Maak nooit met de hand een database aan zonder repo-voorvoegsel in de
   naam, en verwijder nooit een database die je niet zelf hebt aangemaakt.
   Reviewers van één keten draaien tegelijk in dezelfde repo (bv. R-TECH met de volledige variant en R-HARDE-EIS met
   "migraties heen en terug"). Daarom:
   - **Een database die je met de hand aanmaakt** (de migratieproef van P-ai-server-manager, P-home-control-hub,
     P-appstore-en-fork en P-zoeken-en-persoonlijke-ai) krijgt een eigen achtervoegsel: `<ACHTERVOEGSEL>` = je rol
     plus het stap-ID, in kleine letters met `_` (bv. `r_harde_eis_s_p2_005`, `r_tech_s_p2_005`, `a_bouw_s_p2_005`,
     `a_gate_p2`). Zo heeft elke subagent een eigen naam (regel RV6 van de reviewprompts in `AGENTEN.md`). Draai zo'n
     blok als één bash-aanroep: een `export` geldt alleen binnen dezelfde shell.
   - **Vaste namen in de testcode** van home-control-hub en zoeken-en-persoonlijke-ai (de namen staan in het P-blok,
     Omgeving): draai elk commando van die repo dat PostgreSQL gebruikt achter de databaselock van de repo (0.2). Het
     P-blok geeft de commando's zo. Dat geldt ook voor de commando's van die twee repos in P-PEIL en voor een losse
     test die niet in het P-blok staat. In de andere repos maakt de testcode zelf unieke namen (willekeurig of met het
     proces-ID; gezien op 2026-11-11 in de `conftest.py`-bestanden); daar is geen lock nodig.
6. Zet vóór Python-tests die een database back-uppen of herstellen altijd
   `PATH=/usr/lib/postgresql/16/bin:$PATH`. Zonder deze regel pakt de test een nieuwere `pg_dump` naast een
   oudere `pg_restore` en faalt hij op de omgeving, niet op de code.
7. pytest met hooguit `-n 4`; dotnet met `-m:4`; Gradle altijd met
   `--no-daemon --max-workers=4 -Dorg.gradle.jvmargs=-Xmx2g`.
8. Android: `ANDROID_HOME=$HOME/android-sdk`. Voor media-guard-ultimate en my_house ook
   `JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64` (de CI van die repos gebruikt Java 17).
9. Playwright-browsers staan in `~/.cache/ms-playwright`. Ontbreekt de browser: `npx playwright install chromium`
   (zonder `--with-deps`).
10. Een virtuele Python-omgeving (`.venv`) en `node_modules` worden nooit gecommit. Controle:
    `git status --short` toont ze niet.
11. Subagents starten zelf geen subagents. Twee schrijvende agents werken nooit tegelijk in dezelfde repo.
12. Raak de map `ai-factory` nooit aan.

### 0.4 Welke poort bij welke wijziging

Zoek de regel die past bij wat de stap heeft veranderd. Past er meer dan één regel, draai dan alle genoemde poorten.

| De stap raakt | Verplichte poorten |
|---|---|
| Elke stap, altijd | P-<repo> (volledig voor het geraakte deel), P-GIT, P-EERLIJK, CI-controle (0.5) |
| API, events, koppelen, authenticatie, connector, manifestvelden, EVIDENCE-vorm | + P-CONTRACT |
| Executor, policy, sleutels, goedkeuringen, acties op de NAS, app-installatie | + P-VEILIG |
| Een scherm, statuspagina, app-UI of ontwerptokens (niet Jelly Leon web/clients) | + P-PEIL |
| Kijkgeschiedenis, gebruikers, favorieten, hervatpunten, MediaGuard-voortgang, databaseschema of migratie van een dienst met gebruikersgegevens, Emby-overname, upgradepad van een image | + P-HARDE-EIS |
| Dockerfile, entrypoint, healthcheck, manifest, installatiedocument | + P-INSTALLATIE |
| Het einde van een fase | + P-EXCEL, als EIGEN stap die de regisseur plant (schrijft in ai-server-manager en pullt in alle repos). A-BOUW draait P-EXCEL nooit binnen een bouwstap, ook niet na een statuswijziging in EVIDENCE.json; die wijziging valt onder P-EERLIJK |
| Een bestand onder `.github/workflows/` | + `actionlint` op de gewijzigde bestanden (commando staat in het P-<repo>-blok) |

### 0.5 CI-controle na elke push (geldt voor alle repos)

`gh` staat in `~/.local/bin`. Alle commando's draaien vanuit de werkmap van de repo, en elk `gh run`- en
`gh workflow`-commando krijgt `-R lvos04/<repo>` (zoals in `AGENTEN.md`, controle K5). Zonder `-R` kiest `gh` zelf een
remote, en in de forks met een remote `upstream` is dat de upstream-repo: `gh repo view --json nameWithOwner` gaf op
2026-11-11 in `<WERKMAP>/jelly-leon` `jellyfin/jellyfin` (in `<WERKMAP>/my_house`, zonder `upstream`, wel
`lvos04/my_house`). Zonder `-R` lees of start je dan runs van een andere repo.

```bash
SHA=$(git rev-parse HEAD)
gh run list -R lvos04/<repo> --branch ccr-c133d7a0-kuz1cv --commit "$SHA" --limit 10 \
  --json databaseId,workflowName,status,conclusion,headSha
gh run watch <run-id> -R lvos04/<repo> --exit-status   # wacht tot de run klaar is; exitcode 0 = groen
gh run view <run-id> -R lvos04/<repo> --log-failed     # alleen bij rood: de falende stappen
```

`--commit` (kort `-c`) werkt alleen met de VOLLEDIGE commit-hash van 40 tekens. Met een korte hash geeft
`gh run list` een lege lijst `[]`, ook als er een run is: op 2026-11-11 gaf
`gh run list -R lvos04/home-control-hub -b ccr-c133d7a0-kuz1cv -c 076f964` `[]` en met de volle hash van dezelfde
commit run 42990957447 "success". Noemt een stap, rapport of VOORTGANG.md een korte hash, maak hem dan eerst vol:
`SHA=$(git rev-parse <korte-hash>)`. Gebruik nooit een korte hash bij `--commit`/`-c`; een lege lijst met een korte
hash bewijst niet dat er "geen run" is.

Afvinklijst:

- [ ] Er is voor `$SHA` minstens één run van elke workflow die volgens het P-<repo>-blok op deze push hoort te
      starten. Ontbreekt een run omdat de workflow een padfilter heeft of niet op de werkbranch start, dan staat in
      het P-<repo>-blok hoe je hem met de hand start.
- [ ] Elke run heeft `status: completed` en `conclusion: success`.
- [ ] Het rapport noemt per run: het run-ID, de workflownaam en de uitkomst.
- [ ] Bij rood: eerst `gh run view <run-id> -R lvos04/<repo> --log-failed` lezen, dan hoofdstuk 3 volgen. Een rode run wordt nooit
      "bekend probleem" genoemd zonder dat de oorzaak in het rapport staat.

Lokaal groen en CI rood betekent: de stap is NIET klaar.

Afgebroken runs (`conclusion: cancelled`): bijna elke workflow in deze repos heeft `concurrency` met
`cancel-in-progress: true` per branch (vaststellen: `grep -n -A2 'concurrency' .github/workflows/*.y*ml`). Een nieuwe
push of een met de hand gestarte run (`gh workflow run -R lvos04/<repo> ...`) van DEZELFDE workflow op dezelfde branch breekt de lopende run
af. Gevolgen: (1) een afgebroken run is geen groene run; controleer altijd de run op de commit die je meldt; (2) start
een workflow pas met de hand (`gh workflow run -R lvos04/<repo> ...`) nadat de run van de push voor die workflow
`completed` is (`gh run watch <run-id> -R lvos04/<repo> --exit-status`), anders breek je die run zelf af.

### 0.6 Rapportvorm van een poortresultaat

A-BOUW levert per gedraaide poort precies deze regels. R-EERLIJK en A-GATE gebruiken dezelfde vorm, zodat de
regisseur ze naast elkaar kan leggen.

```
Poort:      P-<naam> (snel | volledig)
Repo:       <repo>, commit <korte sha>
Commando:   <letterlijk commando, met werkmap>
Uitkomst:   exitcode <n>; <aantal> geslaagd, <aantal> mislukt, <aantal> overgeslagen; duur <tijd>
Overgeslagen: <welke tests en de reden die de test zelf geeft>, of "geen"
CI:         run <run-id> (<workflownaam>): <success | failure | niet gestart: reden>
Afwijking:  <wat anders is dan dit bestand voorschrijft en waarom>, of "geen"
```

Een poort zonder letterlijk commando en zonder exitcode telt als niet gedraaid.

### 0.7 Sjabloon van een P-<repo>-blok

Elk blok in hoofdstuk 1 heeft dezelfde koppen, in deze volgorde:

1. **Werkmap en CI-bron** - waar je staat, welke workflowbestanden de waarheid zijn, wanneer ze starten.
2. **Omgeving** - wat er eenmalig klaar moet staan en hoe je controleert dat het er al is.
3. **Snel** - tabel: geraakt deel, commando, Zwaar ja/nee.
4. **Volledig** - genummerde lijst in CI-volgorde, met Zwaar ja/nee en de lock.
5. **Contract-, EVIDENCE- en drifttests** - de tests die P-CONTRACT, P-EERLIJK en P-PEIL voor deze repo invullen.
6. **CI-controle** - welke workflows op de push horen te starten en wat met de hand moet.
7. **Valkuilen** - omgevingsfouten die eerder zijn gezien, met de oplossing.

---

## 1. Poorten per repo

## P-ai-server-manager

### 1. Werkmap en CI-bron

- Werkmap: `<WERKMAP>/ai-server-manager`
- CI: `.github/workflows/ci.yml` (jobs `python`, `web`, `excel`, `manifest`, `images`). Start bij elke push op elke
  branch.
- Lokale ingang: `Makefile` (doelen `venv`, `lint`, `type`, `test`, `test-unit`, `test-integration`, `test-e2e`,
  `openapi-check`, `audit`, `images`, `smoke`, `web-install`, `web-lint`, `web-test`, `web-build`, `web-e2e`,
  `web-review`, `web-audit`). `pytest.ini` zet de testpaden op `apps/policy/tests`, `apps/api/tests`,
  `apps/executor/tests` en `tests/e2e`.

### 2. Omgeving

- Python: `make venv` maakt `.venv` (python3.12; installeert uit `apps/api/requirements.lock` en
  `apps/api/requirements-dev.lock`, daarna `apps/policy`, `apps/api` en `apps/executor` als bewerkbare pakketten).
  Al klaar? `ls .venv/bin/pytest`.
- Web: `make web-install` (= `cd apps/web && npm ci --no-audit --no-fund`). Al klaar? `ls apps/web/node_modules`.
- Database: `HUB_TEST_ADMIN_URL=postgresql://postgres@127.0.0.1:5432/postgres`.
- Manifestvalidator: de job `manifest` installeert de validator van appstore-en-fork op de commit die in
  `ci.yml` als `ASF_COMMIT` staat. Lokaal: gebruik `<WERKMAP>/appstore-en-fork/.venv/bin/python` (zie
  P-appstore-en-fork, Omgeving).

### 3. Snel

| Geraakt | Commando (vanuit de werkmap) | Zwaar |
|---|---|---|
| `apps/policy`, `apps/executor`, `apps/api` (zonder database) | `make lint`; los daarna `make test-unit` | nee |
| `apps/api` met database | `PATH=/usr/lib/postgresql/16/bin:$PATH HUB_TEST_ADMIN_URL=postgresql://postgres@127.0.0.1:5432/postgres make test-integration` | ja (geen lock; niet naast een andere volledige testsuite) |
| Eén testbestand | `.venv/bin/python -m pytest -q <pad naar testbestand>` | nee |
| API-vorm (routes, schema's) | `make openapi-check` | nee |
| `apps/web` (code) | `make web-lint`; los daarna `make web-test` | nee |
| `tools/excel` | `.venv/bin/python -m pytest -q tools/excel/tests` (vraagt eerst `.venv/bin/python -m pip install -r tools/excel/requirements-test.txt`), of dezelfde test met `<WERKMAP>/.lokaal/excel-venv/bin/python` | nee |
| `deploy/manifest/*.manifest.yaml` | zie Volledig, stap 9 | nee |
| `.github/workflows/*.yml` | `actionlint .github/workflows/*.yml` | nee |

### 4. Volledig (CI-volgorde)

1. `make lint` - Zwaar: nee.
2. `make type` - Zwaar: nee (mypy op api, executor en policy).
3. `PATH=/usr/lib/postgresql/16/bin:$PATH HUB_TEST_ADMIN_URL=postgresql://postgres@127.0.0.1:5432/postgres nice -n 10 .venv/bin/python -m pytest -q`
   - Zwaar: ja (geen lock). Richtgetal: ruim 800 tests, ongeveer 9 minuten.
4. Migraties heen en terug, op een eigen database (vul `<ACHTERVOEGSEL>` in volgens 0.3 regel 5; draai het blok
   als één bash-aanroep):
   ```bash
   DB=asm_ci_migrate_<ACHTERVOEGSEL>     # bv. asm_ci_migrate_r_harde_eis_s_p2_005
   psql -h 127.0.0.1 -U postgres -c "DROP DATABASE IF EXISTS $DB"   # alleen je eigen naam: resten van een afgebroken eigen run
   psql -h 127.0.0.1 -U postgres -c "CREATE DATABASE $DB"
   export HUB_DATABASE_URL=postgresql+psycopg://postgres@127.0.0.1:5432/$DB
   .venv/bin/python -m hub migrate
   .venv/bin/python -m hub migrate --check
   .venv/bin/python -m hub migrate --down base
   .venv/bin/python -m hub migrate --check    # MOET nu falen (exitcode ongelijk aan 0)
   .venv/bin/python -m hub migrate
   (cd apps/api && ../../.venv/bin/alembic -c alembic.ini check)
   unset HUB_DATABASE_URL
   psql -h 127.0.0.1 -U postgres -c "DROP DATABASE $DB"
   ```
   Zwaar: nee. De database `asm_ci_migrate_<ACHTERVOEGSEL>` is van jou; ruim hem na afloop op. Een vaste naam zonder
   achtervoegsel botst als R-TECH (volledige variant) en R-HARDE-EIS (P-HARDE-EIS) tegelijk lopen: de een gooit de
   database weg terwijl de ander migreert.
5. `make openapi-check` - Zwaar: nee.
6. `make audit` - Zwaar: nee (`pip-audit --strict` op de twee lockbestanden; vraagt netwerk).
7. Web: `make web-lint && make web-test && make web-audit` - Zwaar: nee.
8. Web, zwaar deel: `make web-e2e` (bouwt eerst met `next build`, draait dan Playwright tegen de echte API met een
   nagebootste TrueNAS) en daarna `make web-review` (Peil-ontwerpreview, zie P-PEIL). De CI draait de review als
   `PEIL_REVIEW_WORKERS=2 npx playwright test -c playwright.review.config.ts` gevolgd door
   `node review/samenvat.mjs --json review/uit/samenvatting.json --streng` (werkmap `apps/web`). Zwaar: ja (geen
   lock; niet naast een andere volledige testsuite).
9. Manifesten (werkmap blijft de repo):
   ```bash
   <WERKMAP>/appstore-en-fork/.venv/bin/python -I -m appstore.manifest.cli validate --strict \
     deploy/manifest/ai-server-manager.manifest.yaml
   <WERKMAP>/appstore-en-fork/.venv/bin/python -I -m appstore.manifest.cli validate --strict \
     deploy/manifest/ai-server-manager-executor.manifest.yaml
   ```
   Zwaar: nee. Exitcode 0 is verplicht.
10. Excel-gereedschap: `<WERKMAP>/.lokaal/excel-venv/bin/python -m pytest -q tools/excel/tests` - Zwaar: nee. Vraagt
    `pytest` en `openpyxl` in die venv (zie P-EXCEL, Omgeving; op 2026-11-11 ontbraken ze nog).
11. Images en rooktest:
    ```bash
    flock <WERKMAP>/.lokaal/docker-build.lock nice -n 10 make images
    bash deploy/smoke.sh ai-server-manager:dev ai-server-manager-executor:dev
    ```
    Zwaar: ja, lock `docker-build.lock`. `make images` bouwt `deploy/allinone/Dockerfile` en
    `deploy/executor/Dockerfile`; `make smoke` is hetzelfde als de tweede regel.
12. `actionlint .github/workflows/*.yml` - Zwaar: nee.

### 5. Contract-, EVIDENCE- en drifttests

- Contract 1.3 (bron staat in deze repo): `apps/api/tests/unit/test_contract_13.py`,
  `apps/api/tests/unit/test_contract_13_kandidaten.py`, `apps/api/tests/unit/test_contract_pin.py`,
  `apps/api/tests/unit/test_contract_1_2.py`.
- Eigen manifesten: `apps/api/tests/unit/test_eigen_manifesten.py`.
- EVIDENCE-vorm: `apps/api/tests/unit/test_evidence_contract.py`.
- Veiligheid: alle tests onder `apps/policy/tests` en `apps/executor/tests`, plus `tests/e2e`.
- Snel alles hierboven: `.venv/bin/python -m pytest -q apps/api/tests/unit/test_contract_13.py apps/api/tests/unit/test_contract_13_kandidaten.py apps/api/tests/unit/test_contract_pin.py apps/api/tests/unit/test_contract_1_2.py apps/api/tests/unit/test_eigen_manifesten.py apps/api/tests/unit/test_evidence_contract.py`

### 6. CI-controle

Eén workflow (`ci.yml`) hoort op elke push te starten. Volg 0.5. De job `images` bouwt beide images en draait de
rooktest; die job is de onafhankelijke herhaling van stap 11.

### 7. Valkuilen

- Deze repo is de BRON van het contract en van Peil. Een wijziging in
  `docs/platform-v2/PLATFORM_CONTRACTEN.md`, `docs/platform-v2/CONTRACT_1.3_CONFORMITEIT.md` of
  `design/ontwerptaal/` maakt de drifttests in de andere tien repos rood tot hun kopie is bijgewerkt. Zo'n
  wijziging is nooit een losse stap van A-BOUW: stop en meld aan de regisseur (zie P-CONTRACT).
- `ASF_COMMIT` in `ci.yml` wijst naar een vaste commit van appstore-en-fork. Verandert de manifestvalidator daar,
  dan valideert de CI hier nog met de oude tot de pin is verzet. Vaststellen: `grep -n 'ASF_COMMIT' .github/workflows/ci.yml`.
- `make web-e2e` en `make web-review` vragen een verse `next build`; `web-e2e` doet dat zelf, `web-review` niet.

---

## P-home-control-hub

### 1. Werkmap en CI-bron

- Werkmap: `<WERKMAP>/home-control-hub`
- CI: `.github/workflows/ci.yml` (jobs `python`, `statuspagina-ui`, `image`). Start bij elke push op elke branch.
- Lokale ingang: `Makefile` (doelen `lint`, `test`, `e2e`, `toestanden`, `test-ui`, `schermafdrukken`,
  `ontwerpreview`, `contract-drift`, `peil-drift`, `interop`, `openapi`, `image`, `smoke`).

### 2. Omgeving

- Python: er is geen doel `venv`. De CI doet:
  `python3.12 -m venv .venv`, `.venv/bin/pip install -r apps/api/requirements.lock`,
  `.venv/bin/pip install -e 'apps/api[dev]'`. Al klaar? `ls .venv/bin/pytest`.
- Database: `HCH_TEST_ADMIN_URL=postgresql+psycopg://postgres@127.0.0.1:5432/postgres`.
- Databaselock `<WERKMAP>/.lokaal/hch-db.lock` (0.2 en 0.3 regel 5): de testcode gebruikt vaste databasenamen en gooit die vooraf weg
  met `DROP DATABASE IF EXISTS ... WITH (FORCE)`: `hch_test_api` (`apps/api/tests/conftest.py`, tenzij
  `HCH_TEST_DB_NAME` gezet is), `hch_test_migrations`, `hch_test_backup`, `hch_test_newer_db` (tests onder
  `apps/api/tests/integration/`), `hch_test_e2e` (`tests/e2e/conftest.py`), `hch_ui_toestanden`
  (`tests/ui/genereer_toestanden.py`, via `make toestanden`, `make test-ui` en `make schermafdrukken`),
  `hch_review_<n>` (`tests/ui/ontwerpreview.py`) en `hch_interop_hub`, `hch_interop_dienst`
  (`tests/interop/test_real_hub.py`). Gezien op 2026-11-11. Elk commando hieronder dat PostgreSQL gebruikt staat
  daarom achter deze lock; doe dat ook bij een commando dat hier niet staat.
- Manifestvalidator: de test `apps/api/tests/unit/test_deploy_artifacts.py` zoekt `jl-manifest` in de variabele
  `HCH_JL_MANIFEST` en anders in `<WERKMAP>/appstore-en-fork/.venv/bin/jl-manifest`. Met
  `HCH_MANIFEST_VALIDATOR_VERPLICHT=1` faalt de test als de validator ontbreekt (zo draait de CI).
- UI-tests: `cd tests/ui && npm ci --no-audit --no-fund`. Al klaar? `ls tests/ui/node_modules`.

### 3. Snel

| Geraakt | Commando (vanuit de werkmap) | Zwaar |
|---|---|---|
| `apps/api` (code) | `make lint` | nee |
| `apps/api` (één testbestand) | `cd apps/api && PATH=/usr/lib/postgresql/16/bin:$PATH HCH_TEST_ADMIN_URL=postgresql+psycopg://postgres@127.0.0.1:5432/postgres flock <WERKMAP>/.lokaal/hch-db.lock ../../.venv/bin/python -m pytest -q -p no:cacheprovider <pad onder tests/>` | nee |
| API-vorm | `make openapi && git diff --exit-code docs/openapi/` | nee |
| Contractkopie | `python3 tools/contract_kopie.py controleer` | nee |
| Peil-kopie of statuspagina | `python3 tools/peil_kopie.py controleer`; los daarna `flock <WERKMAP>/.lokaal/hch-db.lock make test-ui` | nee |
| `deploy/manifest/home-control-hub.manifest.yaml` | `<WERKMAP>/appstore-en-fork/.venv/bin/jl-manifest validate --strict deploy/manifest/home-control-hub.manifest.yaml` | nee |

### 4. Volledig (CI-volgorde)

1. `make lint` - Zwaar: nee (ruff, ruff format en mypy op `apps/api`).
2. `.venv/bin/python -m ruff check tests/e2e tests/interop tests/ui deploy/allinone tools && .venv/bin/python -m ruff format --check tests/e2e tests/interop tests/ui deploy/allinone tools`
   - Zwaar: nee (dit deel zit niet in `make lint`, wel in de CI).
3. `make contract-drift` en `make peil-drift` - Zwaar: nee (vraagt netwerk: `vergelijk --online` haalt de bron op).
   Zonder netwerk: `python3 tools/contract_kopie.py vergelijk --bron ../ai-server-manager`.
4. `cd apps/api && PATH=/usr/lib/postgresql/16/bin:$PATH HCH_TEST_ADMIN_URL=postgresql+psycopg://postgres@127.0.0.1:5432/postgres HCH_MANIFEST_VALIDATOR_VERPLICHT=1 flock <WERKMAP>/.lokaal/hch-db.lock nice -n 10 ../../.venv/bin/python -m pytest -q -p no:cacheprovider`
   - Zwaar: ja (alleen de databaselock; geen machinelock).
5. Migraties heen en terug, op een eigen database (zoals de CI-stap "Migraties op en neer"; vul `<ACHTERVOEGSEL>`
   in volgens 0.3 regel 5; draai het blok als één bash-aanroep):
   ```bash
   DB=hch_ci_mig_<ACHTERVOEGSEL>     # bv. hch_ci_mig_r_harde_eis_s_p2_290
   psql -h 127.0.0.1 -U postgres -c "DROP DATABASE IF EXISTS $DB"   # alleen je eigen naam
   psql -h 127.0.0.1 -U postgres -c "CREATE DATABASE $DB"
   export HCH_DATA_DIR=$(mktemp -d) HCH_DATABASE_URL=postgresql+psycopg://postgres@127.0.0.1:5432/$DB
   .venv/bin/python -m integrations migrate && .venv/bin/python -m integrations migrate --down base && .venv/bin/python -m integrations migrate
   unset HCH_DATA_DIR HCH_DATABASE_URL
   psql -h 127.0.0.1 -U postgres -c "DROP DATABASE $DB"
   ```
   Zwaar: nee. Geen databaselock nodig: de naam is van jou alleen.
6. `make openapi && git diff --exit-code docs/openapi/` - Zwaar: nee.
7. `PATH=/usr/lib/postgresql/16/bin:$PATH HCH_TEST_ADMIN_URL=postgresql+psycopg://postgres@127.0.0.1:5432/postgres flock <WERKMAP>/.lokaal/hch-db.lock make e2e`
   - Zwaar: ja (alleen de databaselock; geen machinelock).
8. `.venv/bin/pip-audit -r apps/api/requirements.lock --progress-spinner off` - Zwaar: nee.
9. Manifest: `<WERKMAP>/appstore-en-fork/.venv/bin/jl-manifest validate --strict deploy/manifest/home-control-hub.manifest.yaml`
   - Zwaar: nee.
10. Statuspagina (job `statuspagina-ui`): `flock <WERKMAP>/.lokaal/hch-db.lock make schermafdrukken` en daarna
    `flock <WERKMAP>/.lokaal/hch-db.lock .venv/bin/python tests/ui/ontwerpreview.py --uit tests/ui/review-uit` - Zwaar: nee.
11. Image en rooktest:
    ```bash
    flock <WERKMAP>/.lokaal/docker-build.lock make image
    make smoke
    ```
    Zwaar: ja, lock `docker-build.lock`. `make smoke` draait `deploy/allinone/smoke-test.sh home-control-hub:dev`.

Alleen als de koppeling met de Hub is geraakt: `flock <WERKMAP>/.lokaal/hch-db.lock make interop HUB_PY=<WERKMAP>/ai-server-manager/.venv/bin/python`
(draait `tests/interop` tegen de echte Hub-code). Zwaar: ja (alleen de databaselock).

### 5. Contract-, EVIDENCE- en drifttests

- Contract 1.3: `apps/api/tests/integration/test_contract_1_3_auth.py`, `test_contract_1_3_connector.py`,
  `test_contract_1_3_events.py`, `test_contract_1_3_koppeling.py`, `test_contract_1_3_sso.py`,
  `test_contract_1_3_statuspagina.py` (alle in dezelfde map), plus `apps/api/tests/integration/test_contract_1_2_link.py`.
- EVIDENCE en documenten: `apps/api/tests/unit/test_contract_docs.py`.
- Drift: `tools/contract_kopie.py`, `tools/peil_kopie.py`.

### 6. CI-controle

Eén workflow (`ci.yml`) hoort op elke push te starten. Volg 0.5.

### 7. Valkuilen

- De CI valideert het manifest met de validator op de commit die in `ci.yml` als `VALIDATOR_COMMIT` staat; lokaal
  gebruik je de validator van de naburige appstore-en-fork. Verschil tussen lokaal groen en CI rood op het
  manifest betekent meestal dat de pin achterloopt. Vaststellen: `grep -n 'VALIDATOR_COMMIT' .github/workflows/ci.yml`.
- De CI zet ook `HCH_PEIL_REFERENTIE` (het bestand `bouw/sjabloon.py` van de gepinde Peil-bron) en
  `HCH_PEIL_REFERENTIE_VERPLICHT=1`. Lokaal slaat `apps/api/tests/unit/test_statuspagina_peil.py` die vergelijking
  over als de referentie ontbreekt. Meld die overgeslagen test in het rapport.

---

## P-appstore-en-fork

### 1. Werkmap en CI-bron

- Werkmap: `<WERKMAP>/appstore-en-fork`
- CI: `.github/workflows/ci.yml` (jobs `python`, `statuspagina-ui`, `image`). Start bij elke push op elke branch.
- Lokale ingang: `Makefile` (doelen `venv`, `lint`, `typecheck`, `test-unit`, `test-integration`, `test-e2e`, `test`,
  `test-ui`, `schermafdrukken`, `peil-drift`, `contract-drift`, `openapi`, `manifest`, `image`, `image-e2e`).
- Deze repo is eigenaar van de manifeststandaard (B08-001) en van de validator `jl-manifest` die alle andere repos
  gebruiken.

### 2. Omgeving

- Python: `make venv` maakt `.venv` en installeert `apps/api[dev]`. De CI installeert strenger:
  `pip install --require-hashes -r apps/api/requirements.lock` gevolgd door `pip install --no-deps -e apps/api`.
  Al klaar? `ls .venv/bin/jl-manifest`.
- Database: lokaal NIETS zetten. De tests gebruiken dan de standaard
  `postgresql+psycopg://postgres@127.0.0.1:5432/postgres`. De CI zet `APPSTORE_TEST_DATABASE_URL` met een eigen
  wachtwoord; neem die waarde niet over. Met `APPSTORE_REQUIRE_DB=1` is een ontbrekende database een fout in plaats
  van een overgeslagen test.
- UI-tests: `cd tests/ui && npm ci --no-audit --no-fund`. Al klaar? `ls tests/ui/node_modules`.

### 3. Snel

| Geraakt | Commando (vanuit de werkmap) | Zwaar |
|---|---|---|
| `apps/api` (code) | `make lint`; los daarna `make typecheck` | nee |
| Manifestschema of -regels | `cd apps/api && ../../.venv/bin/python -m pytest -q tests/unit/test_manifest_schema.py tests/unit/test_manifest_rules.py tests/unit/test_manifest_contract_13.py` | nee |
| Unit-tests | `cd apps/api && PATH=/usr/lib/postgresql/16/bin:$PATH nice -n 10 ../../.venv/bin/python -m pytest -q -n 4 tests/unit` | nee |
| Eigen manifest | `make manifest` | nee |
| API-vorm | `.venv/bin/appstore openapi --out /tmp/openapi.json && diff -u docs/openapi/appstore-en-fork.openapi.json /tmp/openapi.json` | nee |
| Statuspagina | `make test-ui` | nee |

### 4. Volledig (CI-volgorde)

1. `make lint && make typecheck` - Zwaar: nee.
2. `cd apps/api && PATH=/usr/lib/postgresql/16/bin:$PATH nice -n 10 ../../.venv/bin/python -m pytest -q -n 4 tests/unit`
   - Zwaar: nee.
3. `cd apps/api && PATH=/usr/lib/postgresql/16/bin:$PATH APPSTORE_REQUIRE_DB=1 nice -n 10 ../../.venv/bin/python -m pytest -q tests/integration`
   - Zwaar: ja (geen lock).
4. `.venv/bin/python -m pytest -q tests/e2e/test_service_e2e.py` - Zwaar: ja (geen lock).
5. Migraties heen en terug, op een eigen database (vul `<ACHTERVOEGSEL>` in volgens 0.3 regel 5; draai het blok
   als één bash-aanroep):
   ```bash
   DB=appstore_ci_mig_<ACHTERVOEGSEL>     # bv. appstore_ci_mig_r_tech_s_p2_500
   psql -h 127.0.0.1 -U postgres -c "DROP DATABASE IF EXISTS $DB"   # alleen je eigen naam
   psql -h 127.0.0.1 -U postgres -c "CREATE DATABASE $DB"
   export APPSTORE_DATABASE_URL=postgresql+psycopg://postgres@127.0.0.1:5432/$DB
   .venv/bin/appstore migrate && .venv/bin/appstore migrate --down base && .venv/bin/appstore migrate
   .venv/bin/appstore db-pending; echo "exitcode db-pending: $?"    # MOET 1 zijn (1 = schema actueel)
   unset APPSTORE_DATABASE_URL
   psql -h 127.0.0.1 -U postgres -c "DROP DATABASE $DB"
   ```
   Zwaar: nee. De testcode van deze repo maakt zelf unieke namen (`appstore_test_<pid>`, `appstore_e2e_<pid>`,
   `appstore_ui_<pid>`, `appstore_review_a_<pid>`; gezien op 2026-11-11), dus de andere commando's hebben geen
   databaselock nodig. `appstore db-pending` geeft exitcode 0 als er nog migraties wachten en 1 als het schema actueel is
   (`apps/api/src/appstore/__main__.py`); exitcode 0 na de laatste `migrate` is dus een fout. De CI gebruikt voor
   deze stap de database van de CI-container met een eigen wachtwoord; neem dat wachtwoord nergens over.
6. OpenAPI: zie de regel "API-vorm" bij Snel. Zwaar: nee.
7. `.venv/bin/jl-manifest validate --strict --format json deploy/manifest/appstore-en-fork.manifest.yaml` - Zwaar: nee.
8. `python3 tools/contract_kopie.py controleer && python3 tools/contract_kopie.py vergelijk --online` en
   `python3 tools/peil_kopie.py controleer && python3 tools/peil_kopie.py vergelijk --online` - Zwaar: nee (netwerk).
   `make contract-drift` en `make peil-drift` doen de vergelijking ook tegen de naburige `../ai-server-manager`.
9. `.venv/bin/pip-audit -r apps/api/requirements.lock --require-hashes --disable-pip --progress-spinner off` - Zwaar: nee.
10. Statuspagina (job `statuspagina-ui`): `make schermafdrukken` en daarna de ontwerpreview tegen de draaiende dienst:
    `PATH=/usr/lib/postgresql/16/bin:$PATH .venv/bin/python tests/ui/review_live.py --meting <map buiten de repo>`
    - Zwaar: nee. `make schermafdrukken` schrijft afdrukken naar `docs/screenshots/peil/statuspagina`; controleer
    daarna `git status --short` (zie P-PEIL).
11. Image en proef op de image:
    ```bash
    flock <WERKMAP>/.lokaal/docker-build.lock make image
    make image-e2e
    ```
    Zwaar: ja, lock `docker-build.lock`. `make image-e2e` draait `tests/e2e/test_allinone_image.py` tegen
    `appstore-en-fork:dev`.

### 5. Contract-, EVIDENCE- en drifttests

- Manifeststandaard: `apps/api/tests/unit/test_manifest_contract_13.py`, `apps/api/tests/unit/test_manifest_rules.py`,
  `apps/api/tests/unit/test_manifest_schema.py`.
- Bewijs dat verboden installatievormen geweigerd worden (EX47 en de compose-regel):
  `apps/api/tests/fixtures/manifests/compose-forbidden.manifest.yaml` en
  `apps/api/tests/fixtures/manifests/ex47-privileged-hostmount.manifest.yaml`. Deze fixtures mogen nooit worden
  verwijderd of versoepeld.
- EVIDENCE-vorm: `apps/api/tests/unit/test_evidence_contract.py`.
- Peil-kopie: `apps/api/tests/unit/test_peil_kopie.py`.

### 6. CI-controle

Eén workflow (`ci.yml`) hoort op elke push te starten. Volg 0.5.

### 7. Valkuilen

- Andere repos pinnen een commit van deze repo voor hun validator (`ASF_COMMIT` in ai-server-manager,
  `VALIDATOR_COMMIT` in home-control-hub en zoeken-en-persoonlijke-ai, `APPSTORE_COMMIT` in jelly-leon). Een
  wijziging aan het manifestschema of aan de regels hier is pas overal van kracht als die pins zijn verzet. Meld
  elke wijziging aan `apps/api/src` onder de manifestcode aan de regisseur, met de nieuwe commit.
- jelly-leon-platform pint NIET: de CI daar kloont de validator van appstore-en-fork op de werkbranch
  `ccr-c133d7a0-kuz1cv` (vaststellen: `grep -n 'appstore-en-fork.git' <WERKMAP>/jelly-leon-platform/.github/workflows/ci.yml`).
  Elke push hier verandert dus direct de validator voor de volgende CI-run van jelly-leon-platform. Een
  manifestwijziging hier is pas klaar als ook de CI van jelly-leon-platform op zijn laatste commit groen is
  (met de hand starten: `gh workflow run ci.yml -R lvos04/jelly-leon-platform --ref ccr-c133d7a0-kuz1cv` in `<WERKMAP>/jelly-leon-platform`); rood
  daar is tak H (hoofdstuk 3).
- Een nieuwe regel die bestaande manifesten van andere repos afkeurt is een contractwijziging: stop en meld
  (P-CONTRACT).

---

## P-jelly-leon-platform

### 1. Werkmap en CI-bron

- Werkmap: `<WERKMAP>/jelly-leon-platform`
- CI: `.github/workflows/ci.yml` (jobs `test`, `statuspagina`, `image`, `rooktest`). Start bij elke push en met de
  hand (`workflow_dispatch`).
- Lokale ingang: `Makefile` (doelen `venv`, `lint`, `typecheck`, `test`, `test-sim`, `test-repo`, `test-conformance`,
  `test-conformance-hub`, `test-e2e`, `openapi`, `image`, `sim-image`, `audit`, `peil-kopie`, `test-ui`,
  `test-ui-live`, `statuspagina-shots`, `ontwerpreview`, `validator-venv`, `manifesten`, `rooktest`,
  `upstream-rooktest`, `nodered`, `nodered-rooktest`). Let op: `make test` draait alleen `apps/api`; de CI-job
  `test` draait daarnaast de simulatortests (`make test-sim`) en `tests/conformance` (`make test-conformance`).

### 2. Omgeving

- Python: `make venv` maakt `.venv` (installeert `apps/api[test]` en de simulatoren onder `e2e/simulators`).
  Al klaar? `ls .venv/bin/pytest`.
- Validator: `make validator-venv` maakt `.venv-validator` uit de HEAD van de naburige `../appstore-en-fork`.
  Al klaar? `ls .venv-validator/bin/jl-manifest`. Draai dit doel opnieuw als appstore-en-fork is veranderd.
- Database: `LIFECYCLE_TEST_PG=postgresql+psycopg://postgres@127.0.0.1:5432/postgres`.
- Naburige bronnen: de tests onder `tests/repo` lezen standaard `../ai-server-manager` en `../appstore-en-fork`.

### 3. Snel

| Geraakt | Commando (vanuit de werkmap) | Zwaar |
|---|---|---|
| Code onder `apps/api` | `make lint`; los daarna `cd apps/api && PATH=/usr/lib/postgresql/16/bin:$PATH LIFECYCLE_TEST_PG=postgresql+psycopg://postgres@127.0.0.1:5432/postgres ../../.venv/bin/python -m pytest -q <pad onder tests/>` | nee |
| Simulatoren | `make test-sim` | nee |
| Koppeling met de Hub (contract 1.3) | `make test-conformance` | nee |
| Manifesten onder `install/manifests/` of `deploy/manifest/` | `make manifesten` | nee |
| Kopieën (contract, Peil, manifest, validator) | `make test-repo` | nee |
| Statuspagina | `make test-ui` | nee |
| API-vorm | `.venv/bin/python -m lifecycle export-openapi /tmp/openapi.json && diff -u docs/openapi/jelly-leon-platform.openapi.json /tmp/openapi.json` | nee |

### 4. Volledig (CI-volgorde)

1. `make lint` - Zwaar: nee.
2. `actionlint .github/workflows/ci.yml .github/workflows/release.yml` - Zwaar: nee.
3. `nice -n 10 make typecheck` - Zwaar: nee (mypy, deels `--strict`).
4. `PATH=/usr/lib/postgresql/16/bin:$PATH LIFECYCLE_TEST_PG=postgresql+psycopg://postgres@127.0.0.1:5432/postgres nice -n 10 make test`
   - Zwaar: ja (geen lock).
5. `make test-sim` - Zwaar: nee.
6. `make test-conformance` - Zwaar: nee (conformiteit contract 1.3 tegen de Hub-simulator).
7. `make validator-venv && make manifesten` - Zwaar: nee.
8. `JL_MANIFEST=$PWD/.venv-validator/bin/jl-manifest PEIL_BRON_VERPLICHT=1 MANIFEST_VALIDATOR_VERPLICHT=1 VALIDATOR_BRON_VERPLICHT=1 make test-repo`
   - Zwaar: nee. `JL_MANIFEST` is verplicht: `tests/repo/test_checklists.py` zoekt de validator ALLEEN via die
   variabele en faalt met `MANIFEST_VALIDATOR_VERPLICHT=1` als hij ontbreekt (de map `.venv-validator` komt uit
   stap 7).
9. OpenAPI: zie de regel "API-vorm" bij Snel. Zwaar: nee.
10. `make audit` - Zwaar: nee (netwerk).
11. Statuspagina (job `statuspagina`): `make test-ui` en `make test-ui-live` - Zwaar: nee.
12. Image en proef op de image:
    ```bash
    flock <WERKMAP>/.lokaal/docker-build.lock make image
    LIFECYCLE_IMAGE=jelly-leon-platform:dev nice -n 10 .venv/bin/python -m pytest -q tests/e2e
    ```
    Zwaar: ja, lock `docker-build.lock`. Gebruik NIET `make test-e2e` zonder lock: dat doel bouwt de image zelf
    zonder `flock`.
13. `make rooktest` - Zwaar: ja. Het doel neemt zelf de lock `<WERKMAP>/.lokaal/docker-build.lock` (variabele
    `LOCK`). Het bouwt de Hub-image en de executor-image uit `../ai-server-manager` en de eigen image, en draait
    `tools/rooktest.py`. Verplicht als de stap de installatie-, koppel- of manifestcode raakt.
14. De CI-job `rooktest` draait na `tools/rooktest.py` nog twee proeven; lokaal:
    ```bash
    flock <WERKMAP>/.lokaal/stack.lock make upstream-rooktest     # Beszel, Gotify, Uptime Kuma als 568 met lege map
    flock <WERKMAP>/.lokaal/stack.lock make nodered-rooktest      # Node-RED volgens het manifest tegen de Hub-simulator
    ```
    Zwaar: ja, lock `stack.lock` (starten containers). Verplicht als de stap `install/manifests/`, `install/node-red/`
    of `tools/upstream_rooktest.py`/`tools/nodered_rooktest.py` raakt.
15. Node-RED-flows (raakt de stap `install/node-red/` of `tools/nodered_flows.py`): `make nodered` (render-, lint- en
    lockcontrole, zonder Docker) - Zwaar: nee.

Alleen als de koppeling met de Hub is geraakt: `make test-conformance-hub` (draait `e2e/conformance/echte_hub.py`
tegen de echte Hub-code uit `../ai-server-manager`). Zwaar: ja (geen lock).

### 5. Contract-, EVIDENCE- en drifttests

- Conformiteit contract 1.3: `tests/conformance/test_hub_conformance.py`, `tests/conformance/test_service_link.py`,
  `apps/api/tests/integration/test_contract_13_api.py`, `apps/api/tests/unit/test_enroll_contract.py`.
- Kopieën en regels: `tests/repo/test_contract_kopie.py`, `tests/repo/test_peil_kopie.py`,
  `tests/repo/test_manifest_kopie.py`, `tests/repo/test_validator_kopie.py`,
  `tests/repo/test_installeerbare_manifesten.py`, `tests/repo/test_repo_rules.py` (leest ook EVIDENCE.json).

### 6. CI-controle

Eén workflow (`ci.yml`) hoort op elke push te starten. Volg 0.5. De job `rooktest` gebruikt de Hub op de commit die
in `ci.yml` als `ASM_COMMIT` staat.

### 7. Valkuilen

- `make statuspagina-shots` en `make ontwerpreview` VERVANGEN bestanden die in de repo staan
  (`docs/screenshots/peil/statuspagina` en `docs/ontwerp`). Draai ze alleen als de stap de statuspagina wijzigt,
  en controleer daarna met `git status --short` welke bestanden zijn veranderd.
- Lokaal test `make rooktest` tegen de HEAD van `../ai-server-manager`; de CI tegen `ASM_COMMIT`. Lokaal groen en
  CI rood (of omgekeerd) op de rooktest wijst op een verschil tussen die twee commits. Vaststellen:
  `grep -n 'ASM_COMMIT' .github/workflows/ci.yml` en `git -C ../ai-server-manager rev-parse HEAD`.

---

## P-zoeken-en-persoonlijke-ai

### 1. Werkmap en CI-bron

- Werkmap: `<WERKMAP>/zoeken-en-persoonlijke-ai`
- CI: `.github/workflows/ci.yml` (jobs `python`, `statuspagina-ui`, `image`). Start bij elke push op elke branch.
- Lokale ingang: `Makefile` (doelen `venv`, `lint`, `test`, `e2e`, `ui`, `ui-echt`, `interop`, `openapi`, `image`,
  `smoke`).

### 2. Omgeving

- Python: `make venv` maakt `.venv` (uit `apps/api/requirements.lock`, daarna `apps/api[dev]`).
  Al klaar? `ls .venv/bin/pytest`.
- Database: `SEARCH_AI_TEST_ADMIN_URL=postgresql+psycopg://postgres@127.0.0.1:5432/postgres`.
- Databaselock `<WERKMAP>/.lokaal/zoek-db.lock` (0.2 en 0.3 regel 5): de testcode gebruikt vaste databasenamen en gooit die vooraf weg
  met `DROP DATABASE IF EXISTS ... WITH (FORCE)`: `zoek_test_api` (`apps/api/tests/conftest.py`, tenzij
  `SEARCH_AI_TEST_DB_NAME` gezet is), `zoek_test_backup`, `zoek_test_mig0002` (tests onder
  `apps/api/tests/integration/`), `zoek_test_e2e` (`tests/e2e/conftest.py`), `zoek_ui_echt_a`, `_b`, `_d`, `_f` en
  `zoek_ui_echt_ontbreekt` (`tests/ui/echte_dienst.py`, ook via `make ui-echt`) en `zoek_interop_hub`,
  `zoek_interop_dienst` (`tests/interop/test_real_hub.py`). Gezien op 2026-11-11. Elk commando hieronder dat
  PostgreSQL gebruikt staat daarom achter deze lock; doe dat ook bij een commando dat hier niet staat. `make ui`
  gebruikt geen database (`Makefile`: toestanden uit de renderer) en hoeft de lock niet.
- Validator: `JL_MANIFEST=<WERKMAP>/appstore-en-fork/.venv/bin/jl-manifest`.
- UI-tests: `make ui` installeert zelf `tests/ui/node_modules`.

### 3. Snel

| Geraakt | Commando (vanuit de werkmap) | Zwaar |
|---|---|---|
| Code | `make lint` | nee |
| Eén testbestand | `cd apps/api && PATH=/usr/lib/postgresql/16/bin:$PATH SEARCH_AI_TEST_ADMIN_URL=postgresql+psycopg://postgres@127.0.0.1:5432/postgres flock <WERKMAP>/.lokaal/zoek-db.lock ../../.venv/bin/python -m pytest -q -p no:cacheprovider <pad onder tests/>` | nee |
| Contract- of Peil-kopie | `cd apps/api && ../../.venv/bin/python -m pytest -q tests/unit/test_contract_kopie.py tests/unit/test_peil_kopie.py -p no:cacheprovider` | nee |
| Manifest | `<WERKMAP>/appstore-en-fork/.venv/bin/jl-manifest validate --strict deploy/manifest/zoeken-en-persoonlijke-ai.manifest.yaml` | nee |
| API-vorm | `make openapi && git diff --exit-code docs/openapi/` | nee |
| Statuspagina | `make ui` | nee |

### 4. Volledig (CI-volgorde)

1. `make lint` - Zwaar: nee (ruff, ruff format, mypy).
2. Drift van de Peil-kopie en de contractkopie: zie de regel "Contract- of Peil-kopie" bij Snel. Zwaar: nee.
3. Manifest: zie de regel "Manifest" bij Snel. Zwaar: nee.
4. `PATH=/usr/lib/postgresql/16/bin:$PATH SEARCH_AI_TEST_ADMIN_URL=postgresql+psycopg://postgres@127.0.0.1:5432/postgres JL_MANIFEST=<WERKMAP>/appstore-en-fork/.venv/bin/jl-manifest MANIFEST_VALIDATOR_VERPLICHT=1 flock <WERKMAP>/.lokaal/zoek-db.lock nice -n 10 make test`
   - Zwaar: ja (alleen de databaselock; geen machinelock).
5. Migraties heen en terug, op een eigen database (zoals de CI-stap "Migraties op en neer"; vul `<ACHTERVOEGSEL>`
   in volgens 0.3 regel 5; draai het blok als één bash-aanroep):
   ```bash
   DB=zoek_ci_mig_<ACHTERVOEGSEL>     # bv. zoek_ci_mig_r_tech_s_p5_10
   psql -h 127.0.0.1 -U postgres -c "DROP DATABASE IF EXISTS $DB"   # alleen je eigen naam
   psql -h 127.0.0.1 -U postgres -c "CREATE DATABASE $DB"
   export SEARCH_AI_DATA_DIR=$(mktemp -d) SEARCH_AI_DATABASE_URL=postgresql+psycopg://postgres@127.0.0.1:5432/$DB
   .venv/bin/python -m search_ai migrate && .venv/bin/python -m search_ai migrate --down base && .venv/bin/python -m search_ai migrate
   unset SEARCH_AI_DATA_DIR SEARCH_AI_DATABASE_URL
   psql -h 127.0.0.1 -U postgres -c "DROP DATABASE $DB"
   ```
   Zwaar: nee. Geen databaselock nodig: de naam is van jou alleen. De CI-database is een pgvector-image; lokaal staat de extensie `vector` bij PostgreSQL 16.
6. `make openapi && git diff --exit-code docs/openapi/` - Zwaar: nee.
7. `PATH=/usr/lib/postgresql/16/bin:$PATH SEARCH_AI_TEST_ADMIN_URL=postgresql+psycopg://postgres@127.0.0.1:5432/postgres flock <WERKMAP>/.lokaal/zoek-db.lock make e2e`
   - Zwaar: ja (alleen de databaselock; geen machinelock).
8. `.venv/bin/pip-audit -r apps/api/requirements.lock --progress-spinner off` - Zwaar: nee.
9. Statuspagina (job `statuspagina-ui`): `make ui` en daarna de ontwerpreview tegen de echte dienst zoals de CI hem
   draait, met uitvoer BUITEN de repo:
   `PATH=/usr/lib/postgresql/16/bin:$PATH SEARCH_AI_TEST_ADMIN_URL=postgresql+psycopg://postgres@127.0.0.1:5432/postgres flock <WERKMAP>/.lokaal/zoek-db.lock .venv/bin/python tests/ui/echte_dienst.py --out /tmp/zoek-echte-dienst --rapport /tmp/zoek-echte-dienst/CONTROLE.json`
   - Zwaar: nee. Gebruik hiervoor niet `make ui-echt` (dat overschrijft de afdrukken in de repo, zie Valkuilen).
10. Image en rooktest:
    ```bash
    flock <WERKMAP>/.lokaal/docker-build.lock make image
    make smoke
    ```
    Zwaar: ja, lock `docker-build.lock`. `make smoke` draait
    `deploy/allinone/smoke-test.sh zoeken-en-persoonlijke-ai:dev`.

Alleen als de koppeling met de Hub is geraakt: `flock <WERKMAP>/.lokaal/zoek-db.lock make interop HUB_PY=<WERKMAP>/ai-server-manager/.venv/bin/python`.
Zwaar: ja (geen lock).

### 5. Contract-, EVIDENCE- en drifttests

- Contract 1.3: `apps/api/tests/integration/test_qa_contract_1_3.py`; contract 1.2 (blijft gelden):
  `apps/api/tests/integration/test_contract_1_2.py`, `apps/api/tests/integration/test_qa_contract_1_2.py`.
- EVIDENCE-vorm: `apps/api/tests/unit/test_evidence_contract.py`.
- Drift: `apps/api/tests/unit/test_contract_kopie.py`, `apps/api/tests/unit/test_peil_kopie.py`.

### 6. CI-controle

Eén workflow (`ci.yml`) hoort op elke push te starten. Volg 0.5.

### 7. Valkuilen

- De drifttests vergelijken lokaal alleen als de bron bereikbaar is; anders slaan ze de bronvergelijking over met
  de melding dat de CI dit controleert. De CI haalt de bron op de gepinde commit op en zet `PEIL_BRON_VERPLICHT=1`
  en `CONTRACT_BRON_VERPLICHT=1`. Een overgeslagen drifttest lokaal is dus geen bewijs: de CI-run is het bewijs.
- `make ui-echt` VERWIJDERT en hermaakt de schermafdrukken in `docs/screenshots/peil/statuspagina`. Alleen draaien
  als de stap de statuspagina wijzigt.
- De validatorpin `VALIDATOR_COMMIT` staat in `ci.yml`; zie de valkuil bij P-home-control-hub.

---

## P-media-guard-ultimate

### 1. Werkmap en CI-bron

- Werkmap: `<WERKMAP>/media-guard-ultimate`
- CI:
  - `.github/workflows/ci.yml`: start bij elke push op elke branch. Jobs voor de kern (`apps/core`, Python 3.12 en
    3.14), de kopieën, het upgradebewijs, de encoder-unittests (`services/encoder`, Python 3.14), de web-UI
    (`apps/web`). Zware jobs (encoder-image, forks, upstream-sync) draaien alleen 's nachts of met de hand.
  - `.github/workflows/android.yml`: start ALLEEN als de push een bestand raakt onder `apps/android/`, of
    `design/ontwerptaal/tokens.json`, of `deploy/release-manifest.json`, of `.github/workflows/android.yml` zelf.
    Met de hand: `gh workflow run android.yml -R lvos04/media-guard-ultimate --ref ccr-c133d7a0-kuz1cv`.
  - `.github/workflows/release.yml`: alleen bij een release (tests, images, `scripts/aio-smoke.py`, upgradebewijs,
    publiceren). Wordt in P2 t/m P6 niet door A-BOUW gestart.
- Lokale ingang: geen Makefile. Verzamelscript `scripts/test-all.sh` (opties `--only a,b`, `--skip a,b`, `--fast`;
  suites `core`, `encoder`, `web`, `web-e2e`, `forks`, `stack`, `faults`, `seerr`).

### 2. Omgeving

- Kern: `.venv` in de werkmap (Python 3.12), gevuld met `pip install -e "apps/core[test]"`.
  Al klaar? `ls .venv/bin/pytest`.
- Encoder: eigen omgeving `services/encoder/.venv` (Python 3.14, gemaakt met `~/.local/bin/python3.14`), gevuld met
  `pip install -e "services/encoder[test]"`. Al klaar? `services/encoder/.venv/bin/python --version` geeft 3.14.
- Web: `cd apps/web && npm ci --no-audit --no-fund`. Al klaar? `ls apps/web/node_modules`.
- Android: `ANDROID_HOME=$HOME/android-sdk`, `JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64`, lock `gradle.lock`.

### 3. Snel

| Geraakt | Commando (vanuit de werkmap) | Zwaar |
|---|---|---|
| `apps/core` (één testbestand) | `cd apps/core && ../../.venv/bin/ruff check .`; los daarna `cd apps/core && ../../.venv/bin/python -m pytest -q -p no:cacheprovider <pad onder tests/>` | nee |
| Upgradepad, release, AIO, instellingen | `cd apps/core && ../../.venv/bin/python -m pytest -q tests/test_upgradebewijs.py tests/test_hub_url_setting.py tests/test_evidence_contract.py tests/test_kopie_herkomst.py tests/test_stack_regressions.py tests/test_zero_config.py tests/test_aio.py tests/test_release_pipeline.py tests/test_openapi_export.py` | nee |
| Contract- of Peil-kopie | `python3 scripts/kopie-herkomst.py controleer` | nee |
| `services/encoder` | `cd services/encoder && .venv/bin/ruff check app tests`; los daarna `cd services/encoder && .venv/bin/mypy app` | nee |
| `apps/web` (code) | `cd apps/web && npm run check:peil`; los daarna `cd apps/web && npm run lint`; los daarna `cd apps/web && npm run typecheck`; los daarna `cd apps/web && npm run test:unit` | nee |
| `apps/android` | `cd apps/android && python3 tools/peil_tokens.py --check` | nee |
| `.github/workflows/*.yml` | `actionlint .github/workflows/*.yml` | nee |

### 4. Volledig (CI-volgorde)

1. Kern: `cd apps/core && ../../.venv/bin/ruff check . && nice -n 10 ../../.venv/bin/python -m pytest -q -rfEs -p no:cacheprovider`
   - Zwaar: ja (geen lock). Richtgetal: ruim 1200 tests, ongeveer 4 minuten. De CI draait dit ook op Python 3.14;
     lokaal is 3.12 voldoende, de CI-run dekt 3.14.
2. Kopieën: `python3 scripts/kopie-herkomst.py controleer && python3 scripts/kopie-herkomst.py vergelijk --online`
   - Zwaar: nee (netwerk). Zonder netwerk: `python3 scripts/kopie-herkomst.py vergelijk --bron ../ai-server-manager`.
3. Upgradebewijs (P-HARDE-EIS, C1.3-MGU-03) - Zwaar: ja, lock `docker-build.lock`:
   ```bash
   python3 scripts/upgradebewijs.py volgorde
   VORIGE="$(python3 -c 'import json;d=json.load(open("deploy/upgradebewijs/vorige-release.json"));print(d["image"]+"@"+d["digest"])')"
   VORIGE_VERSIE="$(python3 -c 'import json;print(json.load(open("deploy/upgradebewijs/vorige-release.json"))["versie"])')"
   VERSIE="$(python3 -c 'import json;print(json.load(open("deploy/release-manifest.json"))["version"])')"
   docker pull -q "$VORIGE"
   flock <WERKMAP>/.lokaal/docker-build.lock nice -n 10 docker buildx build --load \
     -f deploy/upgradebewijs/Dockerfile.kandidaat --build-context core=apps/core --build-context release=deploy \
     --build-arg "VORIGE=$VORIGE" -t mediaguard/upgrade-kandidaat:lokaal deploy/upgradebewijs
   python3 scripts/upgradebewijs.py poort --vorige "$VORIGE" --vorige-versie "$VORIGE_VERSIE" \
     --nieuw mediaguard/upgrade-kandidaat:lokaal --versie "$VERSIE" \
     --werkmap <lege map buiten de repo> --rapport <bestand buiten de repo>.md
   ```
   Verplichte uitkomst: exitcode 0 en in het rapport zowel "Upgrade: niets verloren" als "terugzetten: niets
   verloren". Elk verschil is een stopreden (hoofdstuk 3, tak HARDE EIS).
4. Encoder: `cd services/encoder && .venv/bin/ruff check app tests && .venv/bin/mypy app && .venv/bin/python -m pytest -q -rfEs -p no:cacheprovider tests/test_mediaguard_policy.py tests/test_beslissen.py tests/test_bestandsfilter.py tests/test_db.py tests/test_opslag.py tests/test_onderhoud.py tests/test_mediaguard_storage_guard.py tests/test_scanscheduler.py tests/test_smb_helper.py tests/test_ai_controller.py tests/test_integraties.py tests/test_verificatie.py tests/test_systeem.py`
   - Zwaar: nee. Richtgetal: 124 geslaagd, 1 overgeslagen. Dit is precies de deelverzameling die `ci.yml` draait.
5. Web: `cd apps/web && npm run check:peil && npm run lint && npm run typecheck && npm run test:unit` - Zwaar: nee.
6. Web, zwaar deel: `cd apps/web && nice -n 10 npm run build && MG_E2E_PYTHON=<WERKMAP>/media-guard-ultimate/.venv/bin/python nice -n 10 npm run e2e`
   - Zwaar: ja (geen lock). Richtgetal: ruim 200 Playwright-tests, ongeveer 12 minuten.
7. Android (alleen als `apps/android`, `design/ontwerptaal/tokens.json` of `deploy/release-manifest.json` is geraakt):
   ```bash
   cd apps/android && python3 tools/peil_tokens.py --check
   ANDROID_HOME=$HOME/android-sdk JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
     flock <WERKMAP>/.lokaal/gradle.lock nice -n 10 ./gradlew --no-daemon --max-workers=4 \
     -Dorg.gradle.jvmargs=-Xmx2g :app:verifyPaparazziDebug :app:assembleDebug
   ```
   Zwaar: ja, lock `gradle.lock`. De CI bouwt daarnaast `:app:assembleRelease`. Richtgetal: 278 tests, 0 fouten,
   138 bewust overgeslagen (documentatie-afdrukken, alleen met `PEIL_AFDRUKKEN=1`).
8. `actionlint .github/workflows/*.yml` - Zwaar: nee.
9. Contracttest mediaservers (echte Emby en echte Jellyfin 12.x op digest; deel A de clients, deel B de vorige
   release met een Emby-koppeling en daarna de kandidaat op dezelfde datamap). VERPLICHT als de stap de
   mediaserverkoppeling raakt (Δ-MG-AUTH, Δ-MG-DUAL, `app.integraties`, aanmelden/sessies bij Emby of Jelly Leon):
   ```bash
   free -m        # geheugen te laag (0.3 regel 2): niet starten
   MGMS_BEWIJS=<lege map buiten de repo> MG_CORE_PYTHON=<WERKMAP>/media-guard-ultimate/.venv/bin/python \
     flock <WERKMAP>/.lokaal/stack.lock nice -n 10 tests/contract/mediaserver/run.sh
   ```
   Zwaar: ja, lock `stack.lock` (start containers met een echte mediaserver; zonder `MGMS_KANDIDAAT` bouwt het
   script ook een kandidaat-image). Dit zijn testcontainers op eigen poorten, NIET de Emby van de gebruiker.
   Deze job draait in `ci.yml` NIET op een push (alleen 's nachts of met de hand); het CI-bewijs start je zelf:
   `gh workflow run ci.yml -R lvos04/media-guard-ultimate --ref ccr-c133d7a0-kuz1cv -f heavy=true` en volg dan 0.5 voor de job
   `contracttest mediaservers`. Start dit pas als de run van de push `completed` is: `ci.yml` heeft
   `cancel-in-progress: true` per branch, dus de handmatige run breekt anders de push-run af (0.5).

### 5. Contract-, EVIDENCE- en drifttests

- Mediaservercontract (Δ-MG-AUTH, Δ-MG-DUAL): `tests/contract/mediaserver/run.sh` (zie Volledig, stap 9).
- EVIDENCE-vorm: `apps/core/tests/test_evidence_contract.py`.
- Kopieën (contract en Peil): `apps/core/tests/test_kopie_herkomst.py` en `scripts/kopie-herkomst.py`.
- Upgradebewijs: `apps/core/tests/test_upgradebewijs.py`, `scripts/upgradebewijs.py`,
  `deploy/upgradebewijs/vorige-release.json`, `deploy/upgradebewijs/Dockerfile.kandidaat`.
- Seerr-contract: `tests/contract/seerr/test_seerr_contract.py`.

### 6. CI-controle

- `ci.yml` hoort op elke push te starten. Volg 0.5.
- `android.yml` start alleen bij de paden uit punt 1. Is een van die paden geraakt en ontbreekt de run, meld dat.
  Is geen van die paden geraakt, dan hoort er geen run te zijn en is dat geen fout.

### 7. Valkuilen

- Zes encodertests rekenen met de vrije ruimte van de tijdelijke map. Op een volle of gedeelde tmpfs falen ze op
  de omgeving. Controleer eerst `df -h /tmp`; zet zo nodig `TMPDIR` op een map op schijf.
- `:app:recordPaparazziDebug` OVERSCHRIJFT de referentiebeelden. Dat commando hoort alleen bij een ontwerpstap
  (P-PEIL), nooit om een falende `verifyPaparazziDebug` groen te krijgen.
- Deze repo heeft nog geen manifest en geen `deploy/truenas/CUSTOM_APP.md` (zie P-INSTALLATIE, open punt). Er is
  wel `docs/INSTALL_TRUENAS.md`. De map `deploy/truenas` bevat een compose-bestand; dat is geen installatieweg.

---

## P-media-source-optimizer

### 1. Werkmap en CI-bron

- Werkmap: `<WERKMAP>/media-source-optimizer`
- CI: `.github/workflows/ci.yaml` (jobs `python`, `web`, drie image-jobs, `allinone`, `stack`, `e2e`).
  **Start NIET vanzelf op de werkbranch**: alleen bij een push naar `main`, bij tags `v*`, bij een pull request en
  met de hand. Na elke push dus zelf starten:
  ```bash
  gh workflow run ci.yaml -R lvos04/media-source-optimizer --ref ccr-c133d7a0-kuz1cv
  ```
  Geef NOOIT de invoer `release_version` mee: leeg betekent alleen bouwen en testen, gevuld betekent publiceren.
- `.github/workflows/release.yaml`: alleen bij een release. Wordt niet door A-BOUW gestart.
- Lokale ingang: `Makefile` (doelen `lint`, `test`, `images`, `stack`, `e2e`, `down`).

### 2. Omgeving

- Python: `.venv` in de werkmap, gevuld met `pip install -e "apps/core[test]"` (de CI gebruikt Python 3.13; de
  lokale `.venv` is 3.12). Al klaar? `ls .venv/bin/pytest`.
- Web: `cd apps/web && npm ci --no-audit --no-fund`. Al klaar? `ls apps/web/node_modules`.
- Tijdelijke map: de back-uptests vragen 2 GB vrije ruimte. Zet `TMPDIR` en `--basetemp` op een map OP SCHIJF,
  niet op `/tmp`.

### 3. Snel

| Geraakt | Commando (vanuit de werkmap) | Zwaar |
|---|---|---|
| `apps/core`, `apps/mocks`, `scripts` (code) | `make lint` | nee |
| `apps/core` (één testbestand) | `cd apps/core && PATH=/usr/lib/postgresql/16/bin:$PATH MSO_PG_BIN=/usr/lib/postgresql/16/bin MSO_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:5432/postgres ../../.venv/bin/python -m pytest -q -p no:warnings -rs <pad onder tests/>` | nee |
| Contract- of Peil-kopie | `python3 scripts/bronkopie.py controleer` | nee |
| `apps/web` (code) | `cd apps/web && npm run check:peil`; los daarna `cd apps/web && npm run typecheck`; los daarna `cd apps/web && npm run lint`; los daarna `cd apps/web && npm run test:unit` | nee |
| `.github/workflows/*.yaml` | `actionlint .github/workflows/ci.yaml .github/workflows/release.yaml` | nee |

### 4. Volledig (CI-volgorde)

1. `make lint` - Zwaar: nee (ruff op `apps/core apps/mocks tests/stack scripts` en `scripts/bronkopie.py controleer`).
2. `python3 scripts/bronkopie.py vergelijk --online` - Zwaar: nee (netwerk). Zonder netwerk:
   `python3 scripts/bronkopie.py vergelijk --bron ../ai-server-manager`.
3. `cd apps/core && PATH=/usr/lib/postgresql/16/bin:$PATH MSO_PG_BIN=/usr/lib/postgresql/16/bin MSO_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:5432/postgres TMPDIR=<map op schijf> nice -n 10 ../../.venv/bin/python -m pytest -q -p no:warnings -rs --basetemp=<map op schijf>`
   - Zwaar: ja (geen lock). Richtgetal: ruim 900 tests, ongeveer 28 minuten.
4. Web: `cd apps/web && npm run check:peil && npm run typecheck && npm run lint && npm run test:unit && nice -n 10 npm run build`
   - Zwaar: ja voor de build (geen lock).
5. Images - Zwaar: ja, lock `docker-build.lock`:
   ```bash
   flock <WERKMAP>/.lokaal/docker-build.lock env MSO_IMAGE_TAG=stack nice -n 10 scripts/build-images.sh core
   flock <WERKMAP>/.lokaal/docker-build.lock env MSO_IMAGE_TAG=stack nice -n 10 scripts/build-images.sh mocks
   flock <WERKMAP>/.lokaal/docker-build.lock env MSO_IMAGE_TAG=stack nice -n 10 scripts/build-images.sh web
   flock <WERKMAP>/.lokaal/docker-build.lock env MSO_IMAGE_TAG=local nice -n 10 scripts/build-images.sh allinone
   ```
6. Alles-in-één-proef (dekt ook de upgrade vanaf het 1.5.0-schema; P-HARDE-EIS voor deze repo) - Zwaar: ja, lock
   `stack.lock`:
   ```bash
   TMPDIR=<map op schijf> flock <WERKMAP>/.lokaal/stack.lock .venv/bin/python \
     <WERKMAP>/.lokaal/mso-aio-wrapper/run.py tests/stack/allinone_test.py media-source-optimizer:local
   ```
   De CI draait `tests/stack/allinone_test.py` met rootrechten. Het hulpscript
   `<WERKMAP>/.lokaal/mso-aio-wrapper/run.py` draait hetzelfde, ongewijzigde testbestand zonder rootrechten.
   Richtgetal: 10 van 10.
7. Stackproef - Zwaar: ja, lock `stack.lock`:
   ```bash
   flock <WERKMAP>/.lokaal/stack.lock env MSO_STACK_NO_BUILD=1 nice -n 10 tests/stack/run.sh
   .venv/bin/python tests/stack/test_smoke_logcheck.py
   ```
   Richtgetal: 19 van 19 en 12 van 12.
8. E2E - Zwaar: ja, lock `stack.lock`:
   ```bash
   flock <WERKMAP>/.lokaal/stack.lock env MSO_STACK_NO_BUILD=1 nice -n 10 make e2e
   make down
   ```
   `make e2e` is strikt: minder tests dan `E2E_MIN_TESTS` (staat in de `Makefile`) of een overgeslagen test is een
   fout. `make down` ruimt de stack `msostack` en de testgegevens op.

### 5. Contract-, EVIDENCE- en drifttests

- EVIDENCE-vorm: `apps/core/tests/test_evidence_contract.py`.
- Kopieën: `apps/core/tests/test_contract_kopie.py`, `apps/core/tests/test_bronkopie.py`, `scripts/bronkopie.py`.

### 6. CI-controle

1. Na de push: `gh workflow run ci.yaml -R lvos04/media-source-optimizer --ref ccr-c133d7a0-kuz1cv` (zonder invoer).
2. Wacht enkele seconden en zoek de run: `gh run list -R lvos04/media-source-optimizer --workflow ci.yaml --branch ccr-c133d7a0-kuz1cv --limit 3`.
3. Controleer dat `headSha` van die run gelijk is aan `git rev-parse HEAD`, en volg verder 0.5.

Zonder deze handmatige start is er GEEN CI-bewijs voor de stap.

### 7. Valkuilen

- Stackpoorten: de standaardpoorten van `tests/stack/run.sh` liggen in het bereik dat het systeem ook voor
  uitgaande verbindingen gebruikt. Faalt `compose up` met "address already in use", draai dan opnieuw met
  `MSO_STACK_API_PORT=28200 MSO_STACK_WEB_PORT=28081`. Dat is een omgevingsfout, geen codefout.
- `tests/stack/test_smoke_logcheck.py` faalt met de systeem-Python op een ontbrekende module; gebruik
  `.venv/bin/python`.
- `make e2e` kan schermafdrukken in de repo opnieuw renderen. Controleer daarna `git status --short` en zet
  onbedoeld gewijzigde afdrukken terug met `git checkout -- <pad>`.
- `E2E_MIN_TESTS` verlagen is verboden (hoofdstuk 3).
- Deze repo heeft nog geen manifest en geen `deploy/truenas/CUSTOM_APP.md` (zie P-INSTALLATIE, open punt). Het
  bestaande installatiedocument voor de Custom App staat op `docs/TRUENAS_CUSTOM_APP.md`. De map `deploy/truenas`
  bevat compose-bestanden; dat is geen installatieweg.

---

## P-my_house

### 1. Werkmap en CI-bron

- Werkmap: `<WERKMAP>/my_house`
- CI:
  - `.github/workflows/ci.yml` (jobs `backend`, `web`, `e2e`, `compose`, `stack`): start bij elke push op elke
    branch behalve `main`.
  - `.github/workflows/android.yml`: start ALLEEN als de push een bestand raakt onder `apps/android/`, of
    `design/ontwerptaal/tokens.json`, of `.github/workflows/android.yml`. Kan ook met de hand:
    `gh workflow run android.yml -R lvos04/my_house --ref ccr-c133d7a0-kuz1cv`.
  - `.github/workflows/audit.yml`: alleen gepland of met de hand. `.github/workflows/edge.yml`: alleen op `main`.
- Lokale ingang: geen Makefile; de commando's staan in `ci.yml`.

### 2. Omgeving

- Python: `.venv` in de werkmap (Python 3.12). De CI vult hem zo:
  ```bash
  grep -vE '^[./]' apps/api/requirements.txt > /tmp/mh-lock.txt
  .venv/bin/pip install --require-hashes --only-binary=:all: -r /tmp/mh-lock.txt
  .venv/bin/pip freeze > /tmp/mh-locked.txt
  .venv/bin/pip install -c /tmp/mh-locked.txt -e "integrations[test]" -e "apps/api[dev]"
  .venv/bin/pip check
  ```
  Al klaar? `ls .venv/bin/pytest`.
- Database: `SHC_TEST_PG=postgresql://postgres@127.0.0.1:5432` (zonder databasenaam).
- Web: `cd apps/web && npm ci`. Al klaar? `ls apps/web/node_modules`.
- Android: `ANDROID_HOME=$HOME/android-sdk`, `JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64`, lock `gradle.lock`.

### 3. Snel

| Geraakt | Commando (vanuit de werkmap) | Zwaar |
|---|---|---|
| `apps/api` (code) | `.venv/bin/ruff check apps/api/src apps/api/tests` | nee |
| Platformkoppeling (contract, EVIDENCE, Peil-kopie, Hub-adres) | `cd apps/api && ../../.venv/bin/python -m pytest -q tests/platform_v2` | nee |
| `integrations` | `pipx run ruff==0.17.4 check integrations`; los daarna `nice -n 10 .venv/bin/python -m pytest -q integrations/tests` | nee |
| `apps/web` (code) | `cd apps/web && npx tsc --noEmit`; los daarna `cd apps/web && npm test` | nee |
| `infra/scripts`, `infra/compose` | `shellcheck infra/scripts/*.sh apps/web/docker/*.sh apps/web/e2e/*.sh`; los daarna `python3 -m unittest discover -s infra/tests -v`; los daarna `bash infra/scripts/validate_compose.sh` | nee |
| `apps/android` | `python3 apps/android/tools/peil_tokens.py --check` | nee |
| `.github/workflows/*.yml` | `actionlint .github/workflows/*.yml` | nee |

### 4. Volledig (CI-volgorde)

1. Lint: `.venv/bin/ruff check apps/api/src apps/api/tests && .venv/bin/ruff check --config apps/api/pyproject.toml infra/scripts infra/e2e infra/tests tools && pipx run ruff==0.17.4 check integrations`
   - Zwaar: nee.
2. Kopieën: `python3 tools/contract_kopie.py controleer && python3 tools/contract_kopie.py vergelijk --online` en
   `python3 tools/peil_kopie.py controleer && python3 tools/peil_kopie.py vergelijk --online` - Zwaar: nee
   (netwerk). Zonder netwerk: `python3 tools/contract_kopie.py vergelijk --bron ../ai-server-manager`.
3. `nice -n 10 .venv/bin/python -m pytest -q integrations/tests` - Zwaar: nee. Richtgetal: 188.
4. `cd apps/api && PATH=/usr/lib/postgresql/16/bin:$PATH SHC_TEST_PG=postgresql://postgres@127.0.0.1:5432 nice -n 10 ../../.venv/bin/python -m pytest -q tests`
   - Zwaar: ja (geen lock). Richtgetal: ruim 370 tests, ongeveer 6 minuten.
5. Kwetsbaarheden: `.venv/bin/pip freeze --exclude-editable > /tmp/mh-req.txt && pipx run pip-audit==2.10.1 --no-deps --disable-pip --progress-spinner off -r /tmp/mh-req.txt`
   - Zwaar: nee (netwerk).
6. Web: `cd apps/web && npx tsc --noEmit && npm test && npm run build && npm audit --omit=dev --audit-level=high`
   - Zwaar: nee.
7. E2E:
   ```bash
   (cd apps/web && npx tsc -p e2e/tsconfig.json)
   PATH=/usr/lib/postgresql/16/bin:$PATH SHC_E2E_PYTHON=.venv/bin/python \
     SHC_E2E_PG=postgresql://postgres@127.0.0.1:5432 nice -n 10 apps/web/e2e/run-stack.sh
   ```
   Zwaar: ja (geen lock). Richtgetal: 26 geslaagd.
8. Job `compose`: zie de regel "`infra/scripts`, `infra/compose`" bij Snel. Zwaar: nee.
9. Job `stack` - Zwaar: ja, locks `docker-build.lock` en `stack.lock`:
   ```bash
   V=$(tr -d '[:space:]' < VERSION)
   flock <WERKMAP>/.lokaal/docker-build.lock nice -n 10 docker buildx build --load --provenance=false \
     --build-arg APP_VERSION="$V" -f apps/api/Dockerfile -t shc-api:ci .
   flock <WERKMAP>/.lokaal/docker-build.lock nice -n 10 docker buildx build --load --provenance=false \
     --build-arg APP_VERSION="$V" -t shc-web:ci apps/web
   docker run --rm --entrypoint sh shc-api:ci -c 'pg_dump --version && cat /app/VERSION'
   trivy image --severity CRITICAL --ignore-unfixed --exit-code 1 shc-api:ci
   trivy image --severity CRITICAL --ignore-unfixed --exit-code 1 shc-web:ci
   ```
   De `docker run`-regel moet "PostgreSQL) 16." tonen en als laatste regel exact de inhoud van `VERSION`. De
   CI doet de twee scans met de Trivy-action (zelfde instellingen: alleen CRITICAL met een beschikbare
   oplossing laat de job falen).
   De rest van deze job (installatiescript, `docker compose up -d --wait`, `infra/scripts/smoke_test.py`,
   `infra/scripts/e2e_compose.sh`) draait in de CI met rootrechten. Lokaal is dit eerder herhaald met het
   hulpscript `<WERKMAP>/.lokaal/my_house-ci/stack-job.sh` onder `flock <WERKMAP>/.lokaal/stack.lock`. Dat script
   gebruikt `sudo` en hoort NIET bij de standaardpoort van A-BOUW: de CI-run van de job `stack` is hier het bewijs.
   Wil A-GATE het toch lokaal herhalen: ONBEKEND of het script nog bij de huidige `ci.yml` past - eerst vaststellen
   met: `sed -n '/^  stack:/,$p' .github/workflows/ci.yml` naast `cat <WERKMAP>/.lokaal/my_house-ci/stack-job.sh`.
10. Android (alleen als `apps/android` of `design/ontwerptaal/tokens.json` is geraakt):
    ```bash
    python3 apps/android/tools/peil_tokens.py --check
    cd apps/android && ANDROID_HOME=$HOME/android-sdk JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
      flock <WERKMAP>/.lokaal/gradle.lock nice -n 10 ./gradlew --no-daemon --max-workers=4 \
      -Dorg.gradle.jvmargs=-Xmx2g :core:test :app:verifyPaparazziDebug :app:assembleDebug :app:assembleRelease
    ```
    Zwaar: ja, lock `gradle.lock`. Richtgetal: core 82 en app 109 tests, 0 fouten.
11. `actionlint .github/workflows/*.yml` - Zwaar: nee.

### 5. Contract-, EVIDENCE- en drifttests

- Map `apps/api/tests/platform_v2`: `test_evidence_contract.py`, `test_contract_kopie.py`, `test_peil_kopie.py`,
  `test_hub_url_zonder_koppeling.py`.
- Connectorcontracten: `integrations/tests/test_contract_gree.py`, `integrations/tests/test_contract_homewizard.py`,
  `integrations/tests/test_contract_hue.py`, `integrations/tests/test_contract_zigbee.py`.
- Drift: `tools/contract_kopie.py`, `tools/peil_kopie.py`.

### 6. CI-controle

- `ci.yml` hoort op elke push te starten. Volg 0.5. Let op de job `stack`: die is het enige volledige bewijs van de
  installatieproef.
- `android.yml` start alleen bij de paden uit punt 1; anders met de hand starten als de stap Android raakt.

### 7. Valkuilen

- De CI gebruikt een oudere `shellcheck` dan deze machine en geeft soms een melding die lokaal niet verschijnt.
  Lokaal schoon en CI rood op shellcheck is dus mogelijk: lees de CI-log en los de melding op, schakel hem niet uit.
- Lettertypen verschillen tussen deze machine en de CI. Een schermbreedtetest (overloop op 320 px) kan lokaal
  slagen en in de CI falen. De CI-run is leidend.
- `:app:recordPaparazziDebug` overschrijft referentiebeelden; alleen in een ontwerpstap (P-PEIL).
- Deze repo heeft nog geen alles-in-één image en geen manifest (C1.3-MH-03 en C1.3-MH-06 in
  `docs/platform-v2/CONTRACT_1.3_CONFORMITEIT.md`, kop "8. my_house (bestaande app; P3)"). Zie P-INSTALLATIE.

---

## P-jelly-leon

### 1. Werkmap en CI-bron

- Werkmap: `<WERKMAP>/jelly-leon`
- CI: `.github/workflows/jelly-leon-ci.yml` (jobs `forkregels`, `manifest`, `server`, `plugins`, `image`,
  `stock-client-e2e`, `emby-overname`, `b03-harnas`). Start bij elke push op de werkbranch (patroon `ccr-**`), op
  `main`, `sync/**` en `release/**`, en met de hand (`workflow_dispatch`).
- De workflows die van upstream komen, draaien niet op de werkbranch; zie
  `docs/adr/ADR-0007-upstream-workflows-in-fork.md`. Alleen `jelly-leon-ci.yml` telt als poort.
- Er is geen `Makefile`. Alle commando's hieronder komen uit `jelly-leon-ci.yml`.
- Vaste waarden: `tools/jelly-leon/baseline.json` (`upstream_version`, `fork_version`, `web_fork_commit`,
  `dotnet_sdk_major`) en `jelly-leon-ci.yml` (`JL_RUNTIME_IMAGE`, `APPSTORE_COMMIT`, `STOCK_IMAGE`).

### 2. Omgeving

- Python: `tools/jelly-leon/.venv` (python3.12, uit `tools/jelly-leon/requirements-dev.txt`; de map staat in
  `tools/jelly-leon/.gitignore`). Al klaar? `ls tools/jelly-leon/.venv/bin/pytest`. Anders:
  `python3.12 -m venv tools/jelly-leon/.venv && tools/jelly-leon/.venv/bin/pip install --disable-pip-version-check -r tools/jelly-leon/requirements-dev.txt`.
  Hieronder: `PY=tools/jelly-leon/.venv/bin/python`.
- .NET: er staat geen `dotnet` op de machine. Gebruik `<WERKMAP>/.lokaal/jl-dotnet.sh <dotnet-argumenten>`. Dat
  script draait dotnet in de vastgezette SDK-container als de eigen gebruiker, met de repo op `/src` en
  `<WERKMAP>/.lokaal/jl-home` op `/h`, begrensd op 5 GiB en 6 CPU's. Altijd onder
  `flock <WERKMAP>/.lokaal/docker-build.lock`. `global.json` vraagt SDK 10.0 (`rollForward: latestMinor`).
- Vaste waarden in de shell (eenmalig per sessie, vanuit de werkmap):
  ```bash
  export JL_RUNTIME_IMAGE=$(awk '/^  JL_RUNTIME_IMAGE:/{print $2}' .github/workflows/jelly-leon-ci.yml)
  VERSIE=$(python3 -c "import json;print(json.load(open('tools/jelly-leon/baseline.json'))['upstream_version'])")
  FORK_VERSION=$(python3 -c "import json;print(json.load(open('tools/jelly-leon/baseline.json'))['fork_version'])")
  WEB_REF=$(python3 tools/jelly-leon/web_bron.py --commit)
  WERK=$(mktemp -d -p <WERKMAP>/.lokaal poort-jelly-leon.XXXXXX)   # rapporten en exports, buiten de repo
  ```
- Manifestvalidator: `<WERKMAP>/appstore-en-fork/.venv/bin/python` (de CI gebruikt de commit `APPSTORE_COMMIT`).
- Web-bron voor de image: de lokale kloon `<WERKMAP>/jelly-leon-web`.
- Playwright van het harnas: `ls tools/b03-harnas/playwright/node_modules`. Ontbreekt de map:
  `cd tools/b03-harnas/playwright && npm ci --no-audit --no-fund` (Node 22, de systeem-Node). Browsers: zie 0.3
  regel 9; het harnas gebruikt Chromium, Firefox en WebKit.
- `ffmpeg` staat op de machine (`/usr/bin/ffmpeg`); de recepttests van het harnas gebruiken het.

### 3. Snel

| Geraakt | Commando (vanuit de werkmap) | Zwaar |
|---|---|---|
| `tools/jelly-leon`, `docs/platform-v2/PATCHES.md`, `docs/platform-v2/EVIDENCE.json` | `$PY tools/jelly-leon/check_fork_consistency.py`; los daarna `$PY tools/jelly-leon/patch_register_check.py`; los daarna `$PY -m pytest -q tools/jelly-leon/tests`; los daarna `tools/jelly-leon/.venv/bin/ruff check --config tools/jelly-leon/ruff.toml tools/jelly-leon` | nee |
| Kopie van contract of conformiteitslijst | `$PY tools/jelly-leon/contract_drift.py --bron-map ../ai-server-manager` | nee |
| `deploy/allinone/entrypoint.sh`, `deploy/allinone/healthcheck.sh` | `shellcheck -s sh deploy/allinone/entrypoint.sh deploy/allinone/healthcheck.sh` | nee |
| `deploy/manifest/jelly-leon.manifest.yaml` | Volledig, stap 2 | nee |
| `plugins/` | Volledig, stap 4 | ja, `docker-build.lock` |
| C#-code buiten `plugins/` (core-patch) | Volledig, stap 1 (patchregister) en stap 3. Er is geen snelle variant: de hele solution moet bouwen en testen. | ja, `docker-build.lock` |
| `tools/emby-overname` | `tools/jelly-leon/.venv/bin/ruff check --config tools/emby-overname/ruff.toml tools/emby-overname`; los daarna `$PY -m pytest -q tools/emby-overname/tests` | nee |
| `tools/b03-harnas` | `tools/jelly-leon/.venv/bin/ruff check --config tools/b03-harnas/ruff.toml tools/b03-harnas`; los daarna `PYTHONPATH=tools/b03-harnas $PY -m pytest -q tools/b03-harnas/tests`; los daarna `PYTHONPATH=tools/b03-harnas $PY -m b03h guard --git .` | nee |
| `.github/workflows/*.yml` | `actionlint .github/workflows/jelly-leon-ci.yml .github/workflows/upstream-sync.yml` | nee |

### 4. Volledig (CI-volgorde)

1. Job `forkregels` - Zwaar: nee. Richtgetal: 199 tests in `tools/jelly-leon/tests`.
   ```bash
   $PY tools/jelly-leon/check_fork_consistency.py
   $PY tools/jelly-leon/patch_register_check.py
   $PY tools/jelly-leon/upstream_gedrag_check.py --overzicht
   $PY tools/jelly-leon/contract_drift.py --online --github
   $PY -m pytest -q tools/jelly-leon/tests
   tools/jelly-leon/.venv/bin/ruff check --config tools/jelly-leon/ruff.toml tools/jelly-leon
   shellcheck -s sh deploy/allinone/entrypoint.sh deploy/allinone/healthcheck.sh
   actionlint .github/workflows/jelly-leon-ci.yml .github/workflows/upstream-sync.yml
   ```
   `contract_drift.py --online` vergelijkt met de gepushte bron op GitHub; zonder netwerk:
   `--bron-map ../ai-server-manager`.
2. Job `manifest` - Zwaar: nee. Beide exitcodes moeten 0 zijn.
   ```bash
   <WERKMAP>/appstore-en-fork/.venv/bin/python -I -m appstore.manifest.cli validate --strict --format json \
     deploy/manifest/jelly-leon.manifest.yaml > "$WERK/manifest-rapport.json"; echo "exitcode validator: $?"
   $PY tools/jelly-leon/manifest_rapport.py --rapport "$WERK/manifest-rapport.json"
   ```
3. Job `server` - Zwaar: ja, lock `docker-build.lock`. Richtgetal: 4206 tests, 4190 geslaagd, 16 overgeslagen
   (overgeslagen door upstream), 0 mislukt; build 0 waarschuwingen en 0 fouten.
   ```bash
   flock <WERKMAP>/.lokaal/docker-build.lock <WERKMAP>/.lokaal/jl-dotnet.sh restore Jellyfin.sln
   flock <WERKMAP>/.lokaal/docker-build.lock <WERKMAP>/.lokaal/jl-dotnet.sh build Jellyfin.sln -c Release --no-restore -m:4
   flock <WERKMAP>/.lokaal/docker-build.lock <WERKMAP>/.lokaal/jl-dotnet.sh test Jellyfin.sln -c Release --no-build -m:4 \
     --verbosity minimal --logger "trx;LogFilePrefix=jelly-leon" --results-directory testresults
   GEN=$(find tests/Jellyfin.Server.Integration.Tests/bin/Release -name openapi.json | head -1)
   python3 tools/jelly-leon/openapi_drift.py --verwacht docs/openapi/jelly-leon.openapi.json \
     --gegenereerd "${GEN:-ontbreekt/openapi.json}"
   ```
   Zie Valkuilen voor de 131 omgevingsfouten zonder `libfontconfig1`.
4. Job `plugins` - Zwaar: ja, lock `docker-build.lock`. Richtgetal: 16 tests.
   ```bash
   flock <WERKMAP>/.lokaal/docker-build.lock <WERKMAP>/.lokaal/jl-dotnet.sh build plugins/JellyLeon.Plugins.sln -c Release -m:4
   flock <WERKMAP>/.lokaal/docker-build.lock <WERKMAP>/.lokaal/jl-dotnet.sh test plugins/JellyLeon.Plugins.sln -c Release --no-build --verbosity minimal
   ```
   Daarna de analyzerproef (B03-017, ADR-0032; CI-stap "Analyzer verboden API's"): de proefassembly MOET de build
   laten falen met precies JL0001-JL0004. `analyzer_proef.py --bouw` vraagt een `dotnet` op het PATH en die is er
   lokaal niet; gebruik daarom de bouwlog uit de SDK-container:
   ```bash
   flock <WERKMAP>/.lokaal/docker-build.lock <WERKMAP>/.lokaal/jl-dotnet.sh build \
     plugins/JellyLeon/analyzers/Jellyfin.Plugin.JellyLeon.VerbodenProef/Jellyfin.Plugin.JellyLeon.VerbodenProef.csproj \
     -c Release --nologo > "$WERK/analyzer-bouw.log" 2>&1; echo "exitcode build: $?"
   python3 tools/jelly-leon/analyzer_proef.py --log "$WERK/analyzer-bouw.log" --exitcode <exitcode build hierboven>
   ```
   Verplichte uitkomst: de build faalt (exitcode ongelijk aan 0) en `analyzer_proef.py` geeft exitcode 0. Exitcode 3
   is een omgevingsfout (hoofdstuk 3). Verplicht als de stap `plugins/` raakt.
5. Job `image`, deel bouwen - Zwaar: ja, lock `docker-build.lock`.
   ```bash
   mkdir -p "$WERK/jelly-leon-web"
   git -C <WERKMAP>/jelly-leon-web archive --format=tar "$WEB_REF" | tar -x -C "$WERK/jelly-leon-web"
   test -f "$WERK/jelly-leon-web/package-lock.json"
   flock <WERKMAP>/.lokaal/docker-build.lock nice -n 10 docker buildx build -f deploy/allinone/Dockerfile \
     --build-context jelly-leon-web="$WERK/jelly-leon-web" \
     --build-arg FORK_VERSION="$FORK_VERSION" --build-arg VCS_REF="$(git rev-parse HEAD)" \
     --build-arg WEB_REF="$WEB_REF" --build-arg BUILD_JOBS=4 --load -t jelly-leon:poort .
   ```
   De CI controleert de web-bron ook met `python3 tools/jelly-leon/web_bron.py --controleer <kloon>`. Die controle
   slaagt alleen als `HEAD` van de kloon gelijk is aan `$WEB_REF`. Vergelijk eerst:
   `git -C <WERKMAP>/jelly-leon-web rev-parse HEAD`. Is dat een andere commit, wissel dan NIET van commit in de
   kloon (er kan een andere agent in werken); de CI-job `image` is dan het bewijs voor deze ene controle. Meld
   het onder "Afwijking".
6. Job `image`, deel proeven - Zwaar: ja, elk commando onder `flock <WERKMAP>/.lokaal/stack.lock nice -n 10`.
   Richtgetallen: levenscyclus 31 controles, terugzetproef 10 van 10, upgradeproef 18 van 18.
   ```bash
   S="flock <WERKMAP>/.lokaal/stack.lock nice -n 10"
   $S python3 tools/jelly-leon/e2e/image_lifecycle.py --image jelly-leon:poort --expected-version "$VERSIE" \
     --werkmap "$WERK" --report "$WERK/image-lifecycle.json" --verwacht-web-ref "$WEB_REF"
   PYTHONPATH=tools/b03-harnas python3 -m b03h guard --image jelly-leon:poort
   $S python3 tools/jelly-leon/e2e/rollback_sim.py --image jelly-leon:poort --upstream-image "$JL_RUNTIME_IMAGE" \
     --expected-version "$VERSIE" --werkmap "$WERK" --report "$WERK/rollback-sim.json"
   $S python3 tools/jelly-leon/e2e/upgrade_proef.py --image jelly-leon:poort --expected-version "$VERSIE" \
     --stock-image "$JL_RUNTIME_IMAGE" --werkmap "$WERK" --report "$WERK/upgrade-proef.json"
   $S python3 tools/jelly-leon/e2e/compat_api.py --image jelly-leon:poort --stock-image "$JL_RUNTIME_IMAGE" \
     --werkmap "$WERK" --report "$WERK/compat-api.json"
   $S python3 tools/jelly-leon/e2e/upstream_gedrag_runtime.py --image jelly-leon:poort --werkmap "$WERK" \
     --rapport "$WERK/upstream-gedrag-runtime-jelly-leon.json"
   # B03-017 (gate golf 1): pluginproef JLT-68/64/65 en de IStartupFilter-spike (ADR-0033)
   $S python3 tools/jelly-leon/e2e/plugin_proef.py --image jelly-leon:poort --stock-image "$JL_RUNTIME_IMAGE" \
     --werkmap "$WERK" --rapport "$WERK/pluginproef-jelly-leon.json"
   $S python3 tools/jelly-leon/e2e/startupfilter_spike.py --image jelly-leon:poort \
     --werkmap "$WERK" --rapport "$WERK/startupfilter-spike-jelly-leon.json"
   ```
   De CI draait `plugin_proef.py` en `startupfilter_spike.py` ook in de job `stock-client-e2e` op
   `$JL_RUNTIME_IMAGE` met `--plugin-map <map met de gebouwde plugin-DLL>`; voor A-BOUW is die CI-job daar het bewijs.
   `rollback_sim.py` is de terugzetproef van B03-013; `upgrade_proef.py` dekt JLT-60 en JLT-61. Beide horen bij
   P-HARDE-EIS. Ruim na afloop alleen de eigen image op: `docker image rm jelly-leon:poort`.
7. Job `stock-client-e2e` - Zwaar: ja.
   ```bash
   flock <WERKMAP>/.lokaal/stack.lock nice -n 10 python3 tools/jelly-leon/e2e/upstream_gedrag_runtime.py \
     --image "$JL_RUNTIME_IMAGE" --werkmap "$WERK" --rapport "$WERK/upstream-gedrag-runtime.json"
   flock <WERKMAP>/.lokaal/stack.lock nice -n 10 python3 tools/jelly-leon/e2e/healthcheck_proef.py \
     --image "$JL_RUNTIME_IMAGE" --rapport "$WERK/healthcheck-proef.json"
   ```
   De rest van deze job publiceert de server (`dotnet publish Jellyfin.Server/Jellyfin.Server.csproj -c Release
   --runtime linux-x64 --self-contained ...`), start hem als gebruiker 568 op de upstream-runtime en draait
   `tools/jelly-leon/e2e/stock_client_smoke.py`. Dat is lokaal eerder herhaald, maar het exacte lokale commando is
   niet vastgelegd. Voor A-BOUW is de CI-job `stock-client-e2e` hier het bewijs. A-GATE die het lokaal wil
   herhalen: volg de stappen "Server publiceren" tot en met "Stock-client-smoketest" uit `jelly-leon-ci.yml`.
   Let op: `jl-dotnet.sh` koppelt alleen de repo (`/src`) en `<WERKMAP>/.lokaal/jl-home` (`/h`); de uitvoermap van
   `dotnet publish` moet dus onder `/h/` liggen en nooit in de repo.
8. Job `emby-overname` (B03-015; JLT-70, JLT-71, JLT-72, JLT-73) - hoort bij P-HARDE-EIS.
   ```bash
   tools/jelly-leon/.venv/bin/ruff check --config tools/emby-overname/ruff.toml tools/emby-overname
   $PY -m pytest -q tools/emby-overname/tests
   flock <WERKMAP>/.lokaal/stack.lock nice -n 10 $PY tools/emby-overname/e2e/proefrun.py --modus synthetisch \
     --ffmpeg docker --browser chromium --uitvoer "$WERK/emby-overname"
   ```
   Eerste twee regels: Zwaar: nee, richtgetal 77 tests. Derde regel: Zwaar: ja, lock `stack.lock`; start een echte
   Emby-container en een stock-server. Zwaardere lokale variant met het mediacorpus in
   `<WERKMAP>/.lokaal/media-corpus`: dezelfde regel met `--modus corpus` (zonder `--ffmpeg` en `--browser`);
   richtgetal 57 van 57 controles.
9. Job `b03-harnas` (B03-016).
   ```bash
   tools/jelly-leon/.venv/bin/ruff check --config tools/b03-harnas/ruff.toml tools/b03-harnas
   PYTHONPATH=tools/b03-harnas $PY -m pytest -q tools/b03-harnas/tests
   PYTHONPATH=tools/b03-harnas $PY -m b03h guard --git .
   PYTHONPATH=tools/b03-harnas $PY -m b03h guard --bereik . origin/ccr-c133d7a0-kuz1cv..HEAD
   PYTHONPATH=tools/b03-harnas nice -n 10 $PY -m b03h clientmatrix --onderdelen web,ua,legacy,webdir \
     --uit "$WERK/b03-clientmatrix.json"
   PYTHONPATH=tools/b03-harnas nice -n 10 $PY -m b03h diffrun --uit "$WERK/b03-diffrun.json"
   PYTHONPATH=tools/b03-harnas nice -n 10 $PY -m b03h diffrun --negatieve-proef --uit "$WERK/b03-diffrun-negatief.json"
   ```
   Eerste vier regels: Zwaar: nee. `clientmatrix` en `diffrun`: Zwaar: ja, maar ZONDER `flock` ervoor: het harnas
   neemt `stack.lock` zelf (zie Valkuilen). De laatste regel (negatieve proef) MOET falen met een exitcode
   ongelijk aan 0; slaagt hij, dan is de vergelijking stuk en is de poort rood. De CI maakt voor deze job een
   klein synthetisch corpus met `tools/b03-harnas/ci_mini_corpus.py`; lokaal gebruikt het harnas standaard
   `<WERKMAP>/.lokaal/media-corpus`.

### 5. Contract-, EVIDENCE- en drifttests

- EVIDENCE-vorm: `tools/jelly-leon/tests/test_evidence_contract.py`.
- Contractkopie: `tools/jelly-leon/tests/test_contract_drift.py` en het script `tools/jelly-leon/contract_drift.py`.
- Manifest volgens contract 1.3: `tools/jelly-leon/tests/test_manifest_1_3.py`.
- Snel alles hierboven: `$PY -m pytest -q tools/jelly-leon/tests/test_evidence_contract.py tools/jelly-leon/tests/test_contract_drift.py tools/jelly-leon/tests/test_manifest_1_3.py`
- Conformiteitslijst voor deze repo: `docs/platform-v2/CONTRACT_1.3_CONFORMITEIT.md`, kop
  "9. jelly-leon (server-fork)".
- Peil geldt niet voor deze repo (er is geen map `design/ontwerptaal`); zie P-PEIL.

### 6. CI-controle

Eén workflow (`jelly-leon-ci.yml`, acht jobs) hoort op elke push te starten. Volg 0.5. Alle acht jobs moeten
groen zijn. De jobs `image`, `stock-client-e2e` en `emby-overname` zijn de onafhankelijke herhaling van de
stappen 5 tot en met 8.

### 7. Valkuilen

- `python -m b03h clientmatrix`, `python -m b03h diffrun` en `python -m b03h baseline` nemen `stack.lock` (en waar
  nodig `gradle.lock` en `docker-build.lock`) ZELF, in `<WERKMAP>/.lokaal`. Zet er dus nooit
  `flock <WERKMAP>/.lokaal/stack.lock` voor: het commando wacht dan op een slot dat zijn eigen ouder vasthoudt en
  komt niet verder. Bron: `tools/b03-harnas/b03h/meetslot.py`.
- Hetzelfde meetprotocol verklaart een run ONGELDIG (niet mislukt) als de machinebelasting te hoog is (grens 4,
  instelbaar met `B03_LASTGRENS`). Draai deze metingen niet terwijl een andere keten bouwt. Verhoog de grens niet
  om een geldige run te krijgen.
- Volledige upstream-testsuite: zonder de bibliotheek `libfontconfig1` in de SDK-container faalden 131 tests
  (SkiaSharp). Dat is een omgevingsfout. Hoe de bibliotheek in de container is gezet, is niet vastgelegd:
  ONBEKEND - eerst vaststellen met: `grep -rn 'fontconfig' <WERKMAP>/.lokaal --include='*.sh'` (gaf bij het
  schrijven van dit bestand geen treffer voor de SDK-container; `jl-dotnet.sh` draait niet als root en kan dus
  zelf niets installeren). Tot er een vastgelegde werkwijze is, is de CI-job `server` het bewijs voor de volledige
  suite en meldt A-BOUW de lokale omgevingsfouten met naam en aantal onder "Afwijking".
- `jl-dotnet.sh` begrenst de container op 5 GiB. De eerdere volledige testrun is met 7 GiB gedraaid. Stopt de
  container met exitcode 137, dan is het geheugen op: omgevingsfout, volg hoofdstuk 3. Pas het script niet aan
  zonder dat te melden.
- OpenAPI: vergelijk altijd met `tools/jelly-leon/openapi_drift.py` (vergelijkt de structuur). Een byte-vergelijking
  kan verschillen in beschrijvingsteksten tonen die van de omgeving komen.
- Vaste poorten: de proeven gebruiken vaste poorten op 127.0.0.1 (onder andere 38096). Daarom altijd `stack.lock`.
- `APPSTORE_COMMIT` in `jelly-leon-ci.yml` wijst naar een vaste commit van appstore-en-fork. Vaststellen:
  `grep -n 'APPSTORE_COMMIT' .github/workflows/jelly-leon-ci.yml`. Verandert de validator, dan moet deze pin in een
  eigen stap mee.
- `web_fork_commit` in `tools/jelly-leon/baseline.json` bepaalt welke web-client in de image komt. Een wijziging in
  jelly-leon-web komt pas in de image nadat deze waarde is verzet; dat is een eigen stap.
- Zet nooit een map `_extern` of een uitvoermap in de repo; `git status --short` moet na de poort alleen de
  bedoelde wijzigingen tonen.
- Elke core-patch (C#-code buiten `plugins/`) moet in het patchregister staan
  (`docs/platform-v2/PATCHES.md`); `patch_register_check.py` faalt anders. Voeg de regel toe, schakel de controle
  niet uit.

---

## P-jelly-leon-web

### 1. Werkmap en CI-bron

- Werkmap: `<WERKMAP>/jelly-leon-web`
- CI: `.github/workflows/jelly-leon-web-ci.yml` (jobs `forkregels`, `kwaliteit` met de vier onderdelen `lint`,
  `stylelint`, `build:check` en `test`, `build`, `web-e2e`, `upgrade-e2e`). Start bij elke push op de werkbranch
  (patroon `ccr-**`), op `main`, `sync/**` en `release/**`, en met de hand (`workflow_dispatch`).
- De workflows die van upstream komen, tellen niet als poort; zie
  `docs/adr/ADR-0007-upstream-workflows-in-fork.md`.
- Er is geen `Makefile`. De commando's komen uit `jelly-leon-web-ci.yml` en uit `package.json` (scripts `lint`,
  `stylelint`, `build:check`, `test`, `build:production`, `escheck`).
- Vaste waarden: `tools/jelly-leon-web/baseline.json` (onder `toolchain`: `node`, `npm`, `node_image`,
  `server_image`) en `jelly-leon-web-ci.yml` (`JLW_SERVER_IMAGE`, `JLW_OUDE_SERVER_IMAGE`). Eén bron voor de
  toolchain: `docs/adr/ADR-0011-upgrade-12x-webclient.md`.

### 2. Omgeving

- Node: de repo vraagt Node 24 en npm 11 (`engines` in `package.json`; exact: `toolchain` in
  `tools/jelly-leon-web/baseline.json`). De systeem-Node is 22 en is dus FOUT voor deze repo. Zet vóór elk
  npm-commando:
  ```bash
  export PATH=<WERKMAP>/.lokaal/jelly-leon-web/node24/bin:$PATH
  node --version && npm --version     # verwacht: v24.22.2 en 11.19.1
  ```
- Afhankelijkheden: `npm ci --no-audit --no-fund` (Zwaar: ja, geen lock; niet naast een image-build). Al klaar?
  `ls node_modules/.bin/webpack`. `node_modules` en `dist` staan in `.gitignore`.
- Python (forktools en browserproeven): `<WERKMAP>/.lokaal/jlw-venv` (uit
  `tools/jelly-leon-web/requirements-dev.txt`; bevat pytest, playwright, actionlint en shellcheck). Al klaar?
  `ls <WERKMAP>/.lokaal/jlw-venv/bin/pytest`. Hieronder: `PY=<WERKMAP>/.lokaal/jlw-venv/bin/python`.
- Vaste waarden in de shell (eenmalig per sessie, vanuit de werkmap):
  ```bash
  export JLW_SERVER_IMAGE=$(awk '/^  JLW_SERVER_IMAGE:/{print $2}' .github/workflows/jelly-leon-web-ci.yml)
  export JLW_OUDE_SERVER_IMAGE=$(awk '/^  JLW_OUDE_SERVER_IMAGE:/{print $2}' .github/workflows/jelly-leon-web-ci.yml)
  WERK=$(mktemp -d -p <WERKMAP>/.lokaal poort-jelly-leon-web.XXXXXX)   # rapporten, buiten de repo
  ```

### 3. Snel

| Geraakt | Commando (vanuit de werkmap) | Zwaar |
|---|---|---|
| `tools/jelly-leon-web`, `docs/platform-v2/PATCHES.md`, `docs/platform-v2/EVIDENCE.json` | `$PY tools/jelly-leon-web/check_fork_consistency.py`; los daarna `$PY tools/jelly-leon-web/patch_register_check.py`; los daarna `$PY -m pytest -q -c tools/jelly-leon-web/pytest.ini tools/jelly-leon-web/tests` | nee |
| Kopie van contract of conformiteitslijst | `$PY tools/jelly-leon-web/contract_drift.py --online --github` | nee |
| Broncode onder `src/` (TypeScript, JavaScript) | `nice -n 10 npm run lint`; los daarna `npm run build:check` | nee |
| Stijlbestanden onder `src/` | `npm run stylelint` | nee |
| Eén testbestand | `npm test -- <pad naar testbestand>` | nee |
| `.github/workflows/*.yml` | `$PY tools/jelly-leon-web/workflow_check.py --overzicht`; los daarna `PATH=<WERKMAP>/.lokaal/jlw-venv/bin:$PATH actionlint .github/workflows/jelly-leon-web-ci.yml .github/workflows/upstream-sync.yml` | nee |

Elke wijziging aan een bestand dat van upstream komt, moet in het patchregister staan; daarom hoort
`patch_register_check.py` bij elke snelle ronde.

### 4. Volledig (CI-volgorde)

1. Job `forkregels` - Zwaar: nee. Richtgetal: 171 tests.
   ```bash
   $PY tools/jelly-leon-web/check_fork_consistency.py
   $PY tools/jelly-leon-web/patch_register_check.py
   $PY tools/jelly-leon-web/contract_drift.py --online --github
   $PY tools/jelly-leon-web/workflow_check.py --overzicht
   $PY tools/jelly-leon-web/upstream_gedrag_check.py --overzicht
   $PY -m pytest -q -c tools/jelly-leon-web/pytest.ini tools/jelly-leon-web/tests
   PATH=<WERKMAP>/.lokaal/jlw-venv/bin:$PATH actionlint .github/workflows/jelly-leon-web-ci.yml .github/workflows/upstream-sync.yml
   ```
2. Job `kwaliteit` - Zwaar: nee voor de losse commando's (wel na `npm ci`). Richtgetallen: lint 0 fouten (rond 98
   waarschuwingen die van upstream komen), stylelint 0, `build:check` 0, vitest 164 van 164.
   ```bash
   npm ci --no-audit --no-fund
   nice -n 10 npm run lint
   npm run stylelint
   npm run build:check
   npm test -- --maxWorkers=4
   ```
3. Job `build` - Zwaar: ja (geen lock; niet naast een image-build of een andere volledige testsuite).
   ```bash
   JELLYFIN_VERSION=$(git rev-parse HEAD) nice -n 10 taskset -c 0-3 npm run build:production && npm run escheck
   test -f dist/index.html
   ```
   `taskset -c 0-3` is VERPLICHT op deze machine: zonder begrenzing is de build eerder door het systeem gestopt.
   De CI draait deze job in de Node-image uit `toolchain.node_image`; lokaal is dat eerder herhaald met
   `docker run --cpuset-cpus 0-3 --memory 6g <node_image> ...` gevolgd door
   `npm ci && npm run build:production && npm run escheck`. De koppelingen (`-v`) van dat commando zijn niet
   vastgelegd: ONBEKEND - eerst vaststellen met: `ls <WERKMAP>/.lokaal/jelly-leon-web/logs`. De regel hierboven
   (zonder container) is de lokale poort; de CI-job `build` is de herhaling in de vaste image.
4. Job `web-e2e` - Zwaar: ja, lock `stack.lock`. Vraagt de `dist` uit stap 3.
   ```bash
   flock <WERKMAP>/.lokaal/stack.lock nice -n 10 $PY tools/jelly-leon-web/e2e/web_smoke.py --modus fork --dist dist \
     --image "$JLW_SERVER_IMAGE" --layouts modern,legacy --uitvoer "$WERK/e2e"
   flock <WERKMAP>/.lokaal/stack.lock nice -n 10 $PY tools/jelly-leon-web/e2e/web_smoke.py --modus stock \
     --image "$JLW_SERVER_IMAGE" --layouts modern,legacy --uitvoer "$WERK/e2e"
   ```
5. Job `upgrade-e2e` - Zwaar: ja, lock `stack.lock`. Hoort bij P-HARDE-EIS. Richtgetal: 50 van 50 controles;
   de kijkgegevens per gebruiker zijn vóór en na de upgrade gelijk.
   ```bash
   flock <WERKMAP>/.lokaal/stack.lock nice -n 10 $PY tools/jelly-leon-web/e2e/upgrade_proef.py --dist dist \
     --oude-image "$JLW_OUDE_SERVER_IMAGE" --image "$JLW_SERVER_IMAGE" --layouts modern,legacy \
     --negatief-verwacht start --uitvoer "$WERK/upgrade"
   ```

### 5. Contract-, EVIDENCE- en drifttests

- EVIDENCE-vorm: `tools/jelly-leon-web/tests/test_evidence_contract_1_3.py`.
- Contractkopie: `tools/jelly-leon-web/tests/test_contract_drift.py` en het script
  `tools/jelly-leon-web/contract_drift.py`.
- Snel alles hierboven: `$PY -m pytest -q -c tools/jelly-leon-web/pytest.ini tools/jelly-leon-web/tests/test_evidence_contract_1_3.py tools/jelly-leon-web/tests/test_contract_drift.py`
- Conformiteitslijst voor deze repo: `docs/platform-v2/CONTRACT_1.3_CONFORMITEIT.md`, kop
  "10. jelly-leon-web (web-fork)".
- Peil geldt NIET voor deze repo (contract, kop "13. Ontwerptaal"). P-PEIL wordt hier niet gedraaid.

### 6. CI-controle

Eén workflow (`jelly-leon-web-ci.yml`) hoort op elke push te starten. Volg 0.5. De jobs `web-e2e` en
`upgrade-e2e` wachten op de job `build`; is `build` rood, dan starten ze niet en is de run rood.

### 7. Valkuilen

- Met de systeem-Node (22) weigert `npm ci` met de melding `EBADENGINE`. Dat is terecht: zet het pad naar Node 24
  (Omgeving). Pas `engines` in `package.json` niet aan om dit te omzeilen.
- De build zonder `taskset -c 0-3` kan door het systeem worden gestopt (geheugen). Dat is een omgevingsfout.
- De browserproeven gebruiken vaste poorten op 127.0.0.1 (38097 en 38098). Daarom altijd `stack.lock`.
- Deze repo levert geen eigen image en geen manifest. De web-client komt in de image van jelly-leon via
  `web_fork_commit` in `<WERKMAP>/jelly-leon/tools/jelly-leon/baseline.json`. Een wijziging hier is voor de
  gebruiker pas zichtbaar nadat die waarde in jelly-leon is verzet (eigen stap, P-jelly-leon stap 5 en 6).
  Installatiedocument van deze repo: `deploy/truenas/CUSTOM_APP.md`.
- `lint` geeft waarschuwingen die van upstream komen. Het aantal fouten moet 0 zijn; los upstream-waarschuwingen
  niet op in een stap die daar niet over gaat (elke wijziging is een patch die in het register moet).

---

## P-jelly-leon-clients

### 1. Werkmap en CI-bron

- Werkmap: `<WERKMAP>/jelly-leon-clients` (mappen `android`, `androidtv`, `desktop`, `swiftfin`, `tools/clients`).
- CI, zes workflows die als poort tellen:

  | Workflow | Start bij een push | Job |
  |---|---|---|
  | `.github/workflows/clients-forkregels.yml` | altijd | `forkregels` |
  | `.github/workflows/clients-android.yml` | alleen bij `android/**`, het workflowbestand zelf of `tools/clients/app_identiteit.*` | `bouwen-en-testen` |
  | `.github/workflows/clients-androidtv.yml` | alleen bij `androidtv/**`, het workflowbestand zelf of `tools/clients/app_identiteit.*` | `bouwen-en-testen` |
  | `.github/workflows/clients-desktop.yml` | alleen bij `desktop/**` of het workflowbestand zelf | `linux` |
  | `.github/workflows/clients-swiftfin.yml` | alleen bij `swiftfin/**`, het workflowbestand zelf of `tools/clients/app_identiteit.*` | `simulator` (macOS-runner) |
  | `.github/workflows/clients-compat.yml` | alleen bij de paden die in het bestand onder `paths:` staan (onder andere `android/app/src/**`, `androidtv/app/src/**`, `swiftfin/**`, `tools/clients/server_api_compat.py`) | `routes` |

  Alle zes hebben `workflow_dispatch` en zijn dus met de hand te starten (zie punt 6).
- `.github/workflows/clients-upstream-sync.yml` en `.github/workflows/clients-upstream-sync-een.yml` zijn geen
  poort (upstream-sync).
- Lokale ingang: `Makefile` (doelen `venv`, `test`, `lint`, `check`, `actionlint`, `sync-status`, `android-bouw`,
  `androidtv-bouw`, `desktop-image`, `desktop-bouw`, `release-apks`, `emulator-image`, `desktop-test-image`,
  `compat-android`, `compat-desktop`, `compat-swiftfin`, `opruimen`).

### 2. Omgeving

- Python: `make venv` maakt `.venv` (python3.12, uit `tools/clients/requirements-dev.txt`; bevat pytest, ruff,
  actionlint en shellcheck). Al klaar? `ls .venv/bin/pytest`.
- Android en Android TV: `ANDROID_HOME=$HOME/android-sdk` (zonder deze variabele stoppen de make-doelen met
  exitcode 2). Java 21: dat is de standaard-Java van deze machine (`java -version`); zet hier GEEN
  `JAVA_HOME` naar Java 17.
- De make-doelen zetten zelf `nice -n 10`, `--no-daemon`, `--max-workers=4` en `-Xmx2g`. Geef de locks mee als
  variabele: `GRADLE_LOCK=<WERKMAP>/.lokaal/gradle.lock` en `DOCKER_LOCK=<WERKMAP>/.lokaal/docker-build.lock`.
- `make android-bouw` en `make androidtv-bouw` vergelijken de eigen build met de officiële upstream-APK's in
  `.bouw/officiele-apks` (worden hergebruikt of gedownload; vraagt netwerk). `.bouw` staat in `.gitignore`.
- Swiftfin (iOS en tvOS) bouwt alleen op een macOS-runner. Lokaal is dat niet mogelijk; zie punt 6 en Valkuilen.

### 3. Snel

| Geraakt | Commando (vanuit de werkmap) | Zwaar |
|---|---|---|
| `tools/clients`, `docs/platform-v2/PATCHES.md`, `docs/platform-v2/EVIDENCE.json` | `make lint`; los daarna `make test`; los daarna `make check` | nee |
| Elke wijziging in `android`, `androidtv`, `desktop` of `swiftfin` (patchregister en app-identiteit) | `make check` | nee |
| `android/` | `ANDROID_HOME=$HOME/android-sdk make android-bouw GRADLE_LOCK=<WERKMAP>/.lokaal/gradle.lock` | ja, `gradle.lock` |
| `androidtv/` | `ANDROID_HOME=$HOME/android-sdk make androidtv-bouw GRADLE_LOCK=<WERKMAP>/.lokaal/gradle.lock` | ja, `gradle.lock` |
| `desktop/` | `make desktop-bouw DOCKER_LOCK=<WERKMAP>/.lokaal/docker-build.lock` | ja, `docker-build.lock` |
| `.github/workflows/*.yml` | `make actionlint` | nee |

### 4. Volledig (CI-volgorde)

1. Workflow `clients-forkregels.yml` - Zwaar: nee. Richtgetal: 249 tests.
   ```bash
   test -x "$(git --exec-path)/git-subtree"
   make lint          # ruff check --config tools/clients/ruff.toml tools/clients
   make test          # .venv/bin/python -m pytest -q tools/clients/tests
   make check         # tools/clients/check_clients.py en tools/clients/app_identiteit.py bron
   make actionlint
   ```
2. Workflow `clients-android.yml` (alleen als `android/` of `tools/clients/app_identiteit.*` is geraakt) -
   Zwaar: ja, lock `gradle.lock`.
   ```bash
   ANDROID_HOME=$HOME/android-sdk make android-bouw GRADLE_LOCK=<WERKMAP>/.lokaal/gradle.lock
   ```
   Het doel draait in `android/`: `./gradlew ... assembleDebug test processLibreReleaseResources
   processProprietaryReleaseResources`, daarna `python3 tools/clients/app_identiteit.py bouwmap android
   android/app/build --verwacht debug,release` en `python3 tools/clients/app_identiteit.py vergelijk android
   android/app/build --officieel-map .bouw/officiele-apks`. Upstream heeft hier geen unit-tests met broncode; de
   taak `test` meldt dan dat er niets te testen is. Dat is geen fout.
3. Workflow `clients-androidtv.yml` (alleen als `androidtv/` of `tools/clients/app_identiteit.*` is geraakt) -
   Zwaar: ja, lock `gradle.lock`. Richtgetal: 13 tests in de app en 2 in `preference`.
   ```bash
   ANDROID_HOME=$HOME/android-sdk make androidtv-bouw GRADLE_LOCK=<WERKMAP>/.lokaal/gradle.lock
   ```
4. Workflow `clients-desktop.yml` (alleen als `desktop/` is geraakt) - Zwaar: ja, lock `docker-build.lock`.
   ```bash
   make desktop-bouw DOCKER_LOCK=<WERKMAP>/.lokaal/docker-build.lock
   ```
   Het doel bouwt eerst de bouwimage (`tools/clients/bouwverificatie/desktop.Dockerfile`) en draait daarna
   `tools/clients/bouwverificatie/desktop_bouw.sh`. De CI doet hetzelfde zonder container:
   `cmake -S desktop -B build/desktop -G Ninja -DCMAKE_BUILD_TYPE=Debug -DUSE_STATIC_MPVQT=ON`,
   `cmake --build build/desktop -j 2`, `ctest --test-dir build/desktop --output-on-failure`.
5. Workflow `clients-compat.yml` (statische routevergelijking) - Zwaar: nee. Eerste stap lokaal:
   ```bash
   python3 tools/clients/client_compat.py bronnen
   ```
   De rest van de job haalt met `git` vier upstream-bronnen op en draait twee keer
   `python3 tools/clients/server_api_compat.py` (Kotlin-SDK en `--sdk-taal swift`). De volledige argumenten staan
   in `clients-compat.yml`, stap met `server_api_compat.py`. Voor A-BOUW is de CI-run van deze workflow het bewijs;
   start hem met de hand als de stap een clientmap raakt en de workflow niet vanzelf startte (punt 6).
6. Workflow `clients-swiftfin.yml` - lokaal NIET uitvoerbaar (macOS met Xcode). Alleen de CI-run telt. Zolang die
   niet groen is op de commit van de stap: status "Geblokkeerd", validatie `NIET GEVALIDEERD (Mac/Xcode)`.
7. Alleen A-GATE, of A-BOUW als de stap er uitdrukkelijk om vraagt: emulator- en desktopproeven tegen een echte
   Jelly Leon-image. Zwaar: ja.
   ```bash
   ANDROID_HOME=$HOME/android-sdk make release-apks GRADLE_LOCK=<WERKMAP>/.lokaal/gradle.lock
   make emulator-image DOCKER_LOCK=<WERKMAP>/.lokaal/docker-build.lock
   make desktop-test-image DOCKER_LOCK=<WERKMAP>/.lokaal/docker-build.lock
   make compat-android JL_IMAGE=<jelly-leon-image>
   make compat-desktop JL_IMAGE=<jelly-leon-image> DESKTOP_BUILD=<map met de desktop-build>
   flock <WERKMAP>/.lokaal/stack.lock make compat-swiftfin JL_IMAGE=<jelly-leon-image>
   ```
   `<jelly-leon-image>` is een lokaal gebouwde image uit P-jelly-leon, stap 5. `compat-android` neemt `stack.lock`
   en `gradle.lock` ZELF en `compat-desktop` neemt `stack.lock` ZELF: zet er geen `flock` voor (zie Valkuilen).
   `compat-swiftfin` neemt geen slot en krijgt daarom wel `flock` ervoor. `compat-android` vraagt KVM
   (`ls /dev/kvm`). Exitcode 0 betekent bij deze drie doelen alleen dat het bewijsbestand is geschreven: lees de
   regel `validatie` in de uitvoer (`Sim-geslaagd` of `Sim-mislukt`).

### 5. Contract-, EVIDENCE- en drifttests

- Contractkopie: `tools/clients/tests/test_contract_kopie.py`. De vergelijking met de bron draait alleen als
  `<WERKMAP>/ai-server-manager` als git-checkout naast deze repo staat of als `JLC_CONTRACT_BRON` ernaar wijst;
  anders slaat de test dat deel over en controleert hij alleen de hash. Draai hem met `-rs` en lees de
  overgeslagen regels: `.venv/bin/python -m pytest -q -rs tools/clients/tests/test_contract_kopie.py`.
- EVIDENCE-vorm: `tools/clients/tests/test_evidence.py`.
- App-identiteit (eigen pakketnaam, niet gelijk aan de officiële app): `python3 tools/clients/app_identiteit.py bron`
  en de stappen `bouwmap` en `vergelijk` in de make-doelen; hoort bij C1.3-JLC-02.
- Conformiteitslijst voor deze repo: `docs/platform-v2/CONTRACT_1.3_CONFORMITEIT.md`, kop
  "11. jelly-leon-clients".
- Peil geldt NIET voor deze repo (contract, kop "13. Ontwerptaal"). P-PEIL wordt hier niet gedraaid.

### 6. CI-controle

- `clients-forkregels.yml` hoort op elke push te starten. Volg 0.5.
- De andere vijf starten alleen bij hun padfilter. Raakt de stap een client en is er geen run voor de commit, start
  dan de workflow met de hand en volg hem daarna volgens 0.5:
  ```bash
  gh workflow run -R lvos04/jelly-leon-clients clients-android.yml --ref ccr-c133d7a0-kuz1cv
  gh workflow run -R lvos04/jelly-leon-clients clients-androidtv.yml --ref ccr-c133d7a0-kuz1cv
  gh workflow run -R lvos04/jelly-leon-clients clients-desktop.yml --ref ccr-c133d7a0-kuz1cv
  gh workflow run -R lvos04/jelly-leon-clients clients-swiftfin.yml --ref ccr-c133d7a0-kuz1cv
  gh workflow run -R lvos04/jelly-leon-clients clients-compat.yml --ref ccr-c133d7a0-kuz1cv
  ```
  Start alleen de workflow van de client die de stap raakt. Een met de hand gestarte run draait op de laatste
  commit van de branch: controleer in `gh run list` dat `headSha` gelijk is aan de commit van de stap.

### 7. Valkuilen

- `make opruimen` verwijdert bouwmappen en images en eindigt met `docker image prune -f`. Draai dit doel NIET
  terwijl er ergens iets bouwt (0.3 regel 4), en nooit als onderdeel van een poort.
- `make compat-android` en `make compat-desktop` nemen de machinebrede locks zelf
  (`tools/clients/compat/bewijs.py`, functie `slot`; aanroepen in `tools/clients/compat/cli.py` en
  `tools/clients/compat/desktop.py`). Met `flock <WERKMAP>/.lokaal/stack.lock` ervoor wacht het commando op een
  slot dat zijn eigen ouder vasthoudt en komt het niet verder. `make compat-swiftfin` neemt geen slot
  (`swiftfin_cmd` in `tools/clients/compat/cli.py`) en moet dus wel achter `flock` staan.
- Deze repo gebruikt Java 21. De regel "Java 17" uit 0.3 regel 8 geldt alleen voor media-guard-ultimate en my_house.
- De clients zijn forks met `git subtree`. Elke wijziging in een clientmap is een patch die in het patchregister
  moet staan (`docs/platform-v2/PATCHES.md`); `make check` faalt anders. Voeg de regel toe, schakel de controle
  niet uit.
- Er is geen manifest en geen Custom App voor deze repo (clients draaien niet op de NAS). P-INSTALLATIE geldt
  hier niet.
- Echte telefoons, tablets, tv's, Chromecast en DLNA zijn niet te testen op deze machine: altijd
  `NIET GEVALIDEERD (hardware)`. Swiftfin zonder groene macOS-run: `NIET GEVALIDEERD (Mac/Xcode)`.

---

## 2. Algemene poorten

Elke algemene poort heeft dezelfde vorm: wanneer verplicht, bron, afvinklijst met de exacte commando's, en de
stopredenen. Welke algemene poort bij welke wijziging hoort staat in 0.4. Rapporteer elke poort in de vorm van 0.6.

### P-GIT

**Wanneer:** bij elke commit en elke push, in elke repo. A-BOUW en A-HERSTEL voeren de hele lijst uit; R-EERLIJK
herhaalt de punten 1, 2, 11 en 12.
**Bron:** contract (`<WERKMAP>/ai-server-manager/docs/platform-v2/PLATFORM_CONTRACTEN.md`), kop
"12. Commit- en pushregels"; eerdere scan: `<WERKMAP>/.lokaal/scan/OPENBAARHEIDSSCAN.md`, koppen
"1.1 Gitleaks (volledige historie)" en "1.2 Privacyscan (wat gitleaks mist)".

Alle commando's draaien vanuit de werkmap van de repo.

Vóór de commit:

- [ ] 1. `git branch --show-current` geeft `ccr-c133d7a0-kuz1cv`.
- [ ] 2. `git status --short` toont alleen bestanden die bij deze stap horen. Geen `.venv`, `node_modules`,
      bouwmappen, `*.bak`, logbestanden of uitvoer van proeven. Staat er iets dat niet van deze stap is: niet
      meenemen, niet weggooien, wel melden.
- [ ] 3. Bestanden bij naam klaarzetten: `git add <pad> [<pad> ...]`. Niet `git add -A` en niet `git add .`.
- [ ] 4. Geheimenscan op wat klaarstaat:
      ```bash
      gitleaks git --staged --redact --no-banner .
      ```
      Exitcode 0 = geen treffer. Exitcode 1 = treffer: niet committen, zie "Stop en meld" hieronder.
- [ ] 5. Lees `git diff --cached` na op wat gitleaks niet ziet. In de wijziging staat GEEN: IP-adres van een echt
      apparaat, hostnaam, NAS-naam of poolnaam, e-mailadres, naam van een persoon, pad onder `/home/`,
      wachtwoord of token (ook niet als voorbeeld dat echt lijkt), schermafdruk of rapport van de echte NAS,
      modelnaam of model-ID. Toegestaan: `127.0.0.1`, plaatshouders tussen punthaken (zoals `<WERKMAP>`) en waarden
      die al letterlijk in het contract staan. Hulpmiddel om kandidaten te vinden (vervangt het nalezen niet):
      ```bash
      git diff --cached -U0 | grep -E '^\+' | grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}'
      ```
      Voor deze privacycontrole bestaat in de repos geen vast commando; alleen jelly-leon-platform test een deel
      geautomatiseerd (`tests/repo/test_repo_rules.py`, onder andere `test_no_model_identifiers_in_own_files` en
      `test_install_docs_no_example_nas_values`).
- [ ] 6. Commitbericht: Nederlands, één logische wijziging per commit, laatste regel exact
      `Co-Authored-By: Claude <noreply@anthropic.com>`. Geen modelnaam, geen model-ID, geen sessielink.
      Controle: `git log -1 --format=%B`.

Vóór de push:

- [ ] 7. Vóór ELKE push, ook als je denkt dat er niets is veranderd:
      ```bash
      VOOR=$(git rev-parse origin/ccr-c133d7a0-kuz1cv)
      git pull --rebase origin ccr-c133d7a0-kuz1cv
      git log --oneline "$VOOR"..origin/ccr-c133d7a0-kuz1cv
      ```
      De laatste regel toont de commits van anderen die zijn binnengehaald.
- [ ] 8. Toonde punt 7 commits van anderen? Draai dan de snelle variant van P-<repo> opnieuw voor het geraakte deel,
      vóór de push.
- [ ] 9. Geheimenscan op alles wat gepusht gaat worden:
      ```bash
      gitleaks git --log-opts="origin/ccr-c133d7a0-kuz1cv..HEAD" --redact --no-banner .
      ```
      Exitcode 0 is verplicht.
- [ ] 10. `git push -u origin ccr-c133d7a0-kuz1cv`. Alleen bij een netwerkfout: hooguit vier keer opnieuw, met 2,
      4, 8 en 16 seconden wachttijd. Weigert de server de push omdat de branch is bijgewerkt: terug naar punt 7.

Na de push:

- [ ] 11. `git log origin/ccr-c133d7a0-kuz1cv..HEAD --oneline` is leeg en `git status --short` is leeg.
- [ ] 12. CI-controle volgens 0.5 op `git rev-parse HEAD`.

Nooit:

- `git push --force`, `--force-with-lease`, `git commit --no-verify`, `git reset --hard` op werk van een ander,
  `git rebase` van al gepushte commits, een commit rechtstreeks op een andere branch.
- Een pull request openen (`gh pr create`) of een tag of release maken, tenzij de stap dat letterlijk voorschrijft
  en het besluit erbij staat.
- Een bestand `.gitleaks.toml` of `.gitleaksignore` toevoegen om een treffer te laten verdwijnen (geen repo heeft
  zo'n bestand; toevoegen is een besluit van de regisseur).
- Een bestaande treffer in de historie "oplossen" door historie te herschrijven. Dat beslist alleen de gebruiker.

Stop en meld (hoofdstuk 3) als:

- gitleaks een treffer geeft in je eigen wijziging. Is het een echt geheim: niet committen, waarde uit het bestand
  halen, melden dat het geheim als gelekt moet worden behandeld als het al gecommit of gepusht was. Is het een
  testwaarde: melden met regel-ID en bestand; de regisseur beslist.
- de rebase een conflict geeft in een bestand dat niet van deze stap is: `git rebase --abort`, niets forceren,
  melden.
- er na de push nog lokale commits of gewijzigde bestanden zijn die je niet kunt verklaren.

### P-CONTRACT

**Wanneer:** de stap raakt een API-route, een event, koppelen of ontkoppelen, authenticatie, een connector, een
manifestveld, de vorm van EVIDENCE.json of een van de contractkopieën.
**Bron:** `<WERKMAP>/ai-server-manager/docs/platform-v2/PLATFORM_CONTRACTEN.md` (contract 1.3) en
`<WERKMAP>/ai-server-manager/docs/platform-v2/CONTRACT_1.3_CONFORMITEIT.md` (de afvinklijst per repo). Besluiten:
ADR-0027, ADR-0028 en ADR-0029 in `<WERKMAP>/ai-server-manager/docs/adr/`. Elke repo heeft een kopie van beide
documenten in `docs/platform-v2/`; een drifttest bewaakt dat de kopie gelijk is aan de bron.

Stap 1 - zoek het contractonderdeel bij de wijziging:

| De stap wijzigt | Lees in het contract de kop | Ook draaien |
|---|---|---|
| Image, poort, Custom App-waarden | "2. Apps, images en poorten" | P-INSTALLATIE |
| Iets aan MediaGuard, MSO, my_house, Jelly Leon of Emby | "2.3 Bestaande apps (MediaGuard, MSO, my_house, Jellyfin/Jelly Leon, Emby)" | P-HARDE-EIS |
| Koppelen, enrollment, opslag van geheimen, koppelen via de statuspagina | "3. Geheimen en koppelen" | P-VEILIG |
| Login, SSO, tokens, sleutelpin, replay, fail-closed | "4. Authenticatie en rollen" | P-VEILIG |
| Een API-route (vorm, fouten, grenzen) | "5. Gemeenschappelijke API-regels" | OpenAPI-controle uit het P-<repo>-blok |
| Een connectorroute | "6. Connectorcontract (elke dienst én elke adapter voor bestaande apps)" | - |
| Een event | "7. Event-envelope" | - |
| Voorstel, goedkeuring, executor, een actie | "8. Risicobeleid, voorstel, goedkeuring en executor" | P-VEILIG |
| Een manifest of de manifestregels | "9. Manifeststandaard (B08-001, eigenaar `appstore-en-fork`)" | P-INSTALLATIE |
| De indeling van een nieuwe Python-dienst | "10. Repo-indeling nieuwe Python-diensten" | - |
| EVIDENCE.json | "11. Bewijs en Excel (EVIDENCE.json)" | P-EERLIJK, P-EXCEL |
| Een scherm of statuspagina | "13. Ontwerptaal" | P-PEIL |

Stap 2 - zoek het conformiteitspunt en de test van de repo:

| Repo | Kop in `CONTRACT_1.3_CONFORMITEIT.md` | ID-vorm | Conformiteits- en drifttests |
|---|---|---|---|
| alle repos | "0. Voor alle repos (ALG)" | `C1.3-ALG-<nn>` | de EVIDENCE-test en de drifttest van de repo |
| ai-server-manager | "1. ai-server-manager (Hub + executor; contracteigenaar)" | `C1.3-ASM-<nn>` | P-ai-server-manager, punt 5 |
| home-control-hub | "2. home-control-hub" | `C1.3-HCH-<nn>` | P-home-control-hub, punt 5 |
| appstore-en-fork | "3. appstore-en-fork" | `C1.3-ASF-<nn>` | P-appstore-en-fork, punt 5 |
| jelly-leon-platform | "4. jelly-leon-platform" | `C1.3-JLP-<nn>` | P-jelly-leon-platform, punt 5 |
| zoeken-en-persoonlijke-ai | "5. zoeken-en-persoonlijke-ai" | `C1.3-ZPA-<nn>` | P-zoeken-en-persoonlijke-ai, punt 5 |
| media-guard-ultimate | "6. media-guard-ultimate (MediaGuard, bestaande app; P3 en P4-0)" | `C1.3-MGU-<nn>` | P-media-guard-ultimate, punt 5 |
| media-source-optimizer | "7. media-source-optimizer (MSO, bestaande app; P3)" | `C1.3-MSO-<nn>` | P-media-source-optimizer, punt 5 |
| my_house | "8. my_house (bestaande app; P3)" | `C1.3-MH-<nn>` | P-my_house, punt 5 |
| jelly-leon | "9. jelly-leon (server-fork)" | `C1.3-JL-<nn>` | P-jelly-leon, punt 5 |
| jelly-leon-web | "10. jelly-leon-web (web-fork)" | `C1.3-JLW-<nn>` | P-jelly-leon-web, punt 5 |
| jelly-leon-clients | "11. jelly-leon-clients" | `C1.3-JLC-<nn>` | P-jelly-leon-clients, punt 5 |

De `C1.3-`ID's zijn contract-ID's. Ze staan niet in `<WERKMAP>/.lokaal/plan/bron/ALLE_IDS.txt`; zoek ze in
`CONTRACT_1.3_CONFORMITEIT.md`: `grep -n 'C1.3-<CODE>-' docs/platform-v2/CONTRACT_1.3_CONFORMITEIT.md`.
De volgorde tussen repos staat in dezelfde lijst onder de kop "Volgorde (kruisafhankelijkheden)".

Afvinklijst:

- [ ] 1. Het contractonderdeel uit stap 1 is gelezen in de kopie van de repo (`docs/platform-v2/PLATFORM_CONTRACTEN.md`).
- [ ] 2. De wijziging volgt het contract letterlijk: veldnamen, statuscodes en volgorde komen uit de tekst, niet uit
      het geheugen en niet uit een andere repo.
- [ ] 3. De conformiteits- en drifttests uit punt 5 van het P-<repo>-blok zijn groen. Draai ze met `-rs` en lees elke
      overgeslagen test: een drifttest die de bronvergelijking overslaat (geen netwerk, geen bron-checkout, geen
      CI-variabele) telt lokaal niet als bewijs; dan is de CI-run het bewijs.
- [ ] 4. Voor een nieuw of gewijzigd gedrag is er een test die het contractpunt aantoont, positief en negatief (wat
      geweigerd moet worden, wordt geweigerd).
- [ ] 5. EVIDENCE.json heeft voor het contractpunt een regel `C1.3-<CODE>-<nn>` met de status en validatie volgens
      P-EERLIJK.
- [ ] 6. De contractkopie in de repo is NIET met de hand gewijzigd.

Stop en meld (hoofdstuk 3) als:

- het contract het gewenste gedrag niet beschrijft, zichzelf tegenspreekt of iets anders zegt dan de stap vraagt.
  Los dit niet op in de code. Een wijziging van de bron in ai-server-manager is een besluit (contract 1.3 zelf is
  vastgelegd in ADR-0027, ADR-0028 en ADR-0029), gevolgd door het bijwerken van de kopieën in de tien andere repos;
  dat is nooit een losse stap van A-BOUW.
- een drifttest rood wordt zonder dat de stap de kopie raakte. Dan is de bron veranderd of de pin verouderd; de
  kopie bijwerken is een eigen stap met de hulpscripts uit het P-<repo>-blok (bijvoorbeeld `tools/contract_kopie.py`).
- de stap vraagt om een conformiteitstest uit te zetten, te versoepelen of over te slaan.

### P-VEILIG

**Wanneer:** de stap raakt de executor, het risicobeleid, goedkeuringen, sleutels of tokens, de AI-runner, een actie
die iets op de NAS verandert, een route `POST /connector/v1/apply` in een dienst, of het installeren, bijwerken of
verwijderen van een app.
**Bron:** contract, kop "8. Risicobeleid, voorstel, goedkeuring en executor" en kop "4. Authenticatie en rollen";
`<WERKMAP>/ai-server-manager/docs/platform-v2/01_ARCHITECTUUR/03_RISICO_AUTONOMIE.md` (koppen "Klassen",
"Technische handhaving", "Speciale blokkades", "Faalproeven"); `<WERKMAP>/ai-server-manager/policy/README.md`;
`<WERKMAP>/ai-server-manager/docs/EXECUTION_REQUEST.md`; ADR-0030 in `<WERKMAP>/ai-server-manager/docs/adr/`.

Risicoklassen (bron: `03_RISICO_AUTONOMIE.md`, kop "Klassen"):

| Klasse | Betekenis | Uitvoering |
|---|---|---|
| R0 | alleen lezen | automatisch |
| R1 | omkeerbaar en beperkt | automatisch, alleen met allowlist, cooldown, anti-flap en rollback |
| R2 | infrastructureel of impactvol | uitdrukkelijke goedkeuring |
| R3 | destructief, onomkeerbaar of privilege | altijd menselijk akkoord per gebonden diff; sommige acties worden bewust niet aangeboden |

Commando's (werkmap `<WERKMAP>/ai-server-manager`):

```bash
.venv/bin/python -m pytest -q apps/policy/tests apps/executor/tests
.venv/bin/python -m pytest -q apps/api/tests/unit/test_airunner.py apps/api/tests/unit/test_keyset_fingerprint.py \
  apps/api/tests/unit/test_contract_pin.py apps/api/tests/unit/test_catalog_gates.py
PATH=/usr/lib/postgresql/16/bin:$PATH HUB_TEST_ADMIN_URL=postgresql://postgres@127.0.0.1:5432/postgres \
  .venv/bin/python -m pytest -q tests/e2e/test_executor_koppelen.py
```

In appstore-en-fork (werkmap `<WERKMAP>/appstore-en-fork`), als de stap installeren of manifestregels raakt:

```bash
cd apps/api && PATH=/usr/lib/postgresql/16/bin:$PATH ../../.venv/bin/python -m pytest -q tests/unit/test_ex47.py \
  tests/unit/test_manifest_rules.py
cd apps/api && PATH=/usr/lib/postgresql/16/bin:$PATH APPSTORE_REQUIRE_DB=1 ../../.venv/bin/python -m pytest -q \
  tests/integration/test_hardening.py
```

Welke test welk punt aantoont (bron: de kopregels van de testbestanden):

| Punt | Test-ID | Testbestand in ai-server-manager |
|---|---|---|
| `risk_claim` van AI of flow wordt nooit gelezen; de policy bepaalt de klasse | EX18 | `apps/policy/tests/test_policy.py`, `apps/executor/tests/test_uitvoeren.py` |
| Alleen acties op de allowlist; geen shell, sudo, exec, Docker, cron of vrije tekst | EX17 | `apps/executor/tests/test_executor.py`, `apps/executor/tests/test_uitvoeren.py` |
| Goedkeuring is gebonden aan actie, doel, parameters, ETag, beleid en geldigheid | EX19 | `apps/executor/tests/test_uitvoeren.py` |
| Nonce en goedkeuring zijn eenmalig | EX20 | `apps/executor/tests/test_uitvoeren.py` |
| Pool niet gezond: geen mutatie | EX11 | `apps/executor/tests/test_uitvoeren.py`, `apps/api/tests/unit/test_catalog_gates.py` |
| De boiler wordt nooit geschakeld | EX27 | `apps/policy/tests/test_policy.py`, `apps/executor/tests/test_executor.py` |
| Nooit custom compose, geen privileged of host-mount buiten de regels | EX47 | `apps/policy/tests/test_policy.py`, `apps/executor/tests/test_uitvoeren.py`; in appstore-en-fork `apps/api/tests/unit/test_ex47.py` |
| Back-up verouderd: geen mutatie | EX12 | nog geen test (stand in `<WERKMAP>/.lokaal/plan/bron/STAND_PER_ID.tsv`: niet gestart). De stap die de back-upgate bouwt, voegt de test toe. |

Afvinklijst:

- [ ] 1. Er is geen nieuwe `action_id` zonder regel in `policy/acties.yaml` met minimale klasse, parameterschema en
      back-upeis. Er bestaat geen shell-, sudo-, exec-, Docker-, cron- of vrije-tekstactie en geen actie die data,
      datasets, snapshots of media verwijdert (`policy/README.md`, de lijst onder "Regels:").
- [ ] 2. Een wijziging in `policy/acties.yaml`, `policy/apps.yaml` of `policy/blokkades.yaml` verandert de
      `policy_hash`. Dan zijn de Hub-image EN de executor-image opnieuw gebouwd en getest (P-ai-server-manager,
      Volledig stap 11) en heeft R-VEILIG de wijziging beoordeeld vóór de commit.
- [ ] 3. De executor controleert alles zelf opnieuw: handtekening tegen de gepinde sleutel, vervaltijd, nonce,
      allowlist, parameterschema, policy-hash, risicoklasse en de toestand via teruglezen. Geen van deze controles
      is verwijderd, omzeild of achter een instelling gezet.
- [ ] 4. R2 en R3 worden nooit automatisch uitgevoerd. `app.uninstall_data` wordt niet aangeboden. `app.install`
      gebruikt nooit custom compose.
- [ ] 5. Geen platformactie schrijft rechtstreeks in de database van Emby, Jelly Leon of MediaGuard (contract,
      kop "2.3 Bestaande apps (MediaGuard, MSO, my_house, Jellyfin/Jelly Leon, Emby)", regel 7).
- [ ] 6. Sleutels en tokens: geen privésleutel, token of wachtwoord in code, tests met echte waarden, logregels,
      foutmeldingen, EVIDENCE.json of schermafdrukken. Testsleutels worden in de test gegenereerd. P-GIT punt 4 en
      9 zijn groen.
- [ ] 7. De AI-runner draait als eigen gebruiker zonder toegang tot geheimen, signing keys en de database, en
      weigert te starten als hij er wel bij kan (`apps/api/tests/unit/test_airunner.py`). AI staat standaard uit;
      geen externe of betaalde aanroep zonder besluit D09.
- [ ] 8. Bij twijfel faalt de code dicht: onbekende actie, onleesbaar beleid, verlopen of gewijzigde goedkeuring en
      onbekende toestand leiden tot weigeren, nooit tot uitvoeren.
- [ ] 9. Elke negatieve test (een test die bewijst dat iets geweigerd wordt) bestaat nog en is niet afgezwakt.
      Controle: `git diff origin/ccr-c133d7a0-kuz1cv -- apps/policy/tests apps/executor/tests` toont geen
      verwijderde of versoepelde weigertest.
- [ ] 10. Biedt een dienst buiten ai-server-manager `POST /connector/v1/apply` aan, dan controleert die dienst het
      ondertekende verzoek zelf opnieuw, net als de executor. ONBEKEND welke tests dat per dienst dekken - eerst
      vaststellen met: `grep -rIlE 'ExecutionRequest|execution_request' apps/api/tests` in de werkmap van die dienst.

Voorstel- en goedkeuringsroutes van de Hub-API (B02-005, B01-007): de code (`apps/api/src/hub/actions/`,
`apps/api/src/hub/routers/actions.py`, migratie `apps/api/alembic/versions/0012_acties_goedkeuringen.py`) en de
bijbehorende tests (`apps/api/tests/integration/test_acties.py`, `apps/api/tests/unit/test_actie_blokkades.py`,
`tests/e2e/test_acties.py`) stonden op 2026-11-11 als HALF WERK, niet gecommit, in de werkmap (zie
`<WERKMAP>/.lokaal/plan/STAND_RONDE3.md`). Zodra de stap "half werk afmaken" ze heeft gecommit, horen deze drie
testbestanden bij de commando's van P-VEILIG hierboven. Al gecommit? `git ls-files apps/api/src/hub/actions
apps/api/tests/integration/test_acties.py tests/e2e/test_acties.py` (lege uitvoer = nog niet gecommit).

Stop en meld (hoofdstuk 3) als:

- de stap alleen kan slagen door een controle van de executor of de policy te verwijderen of te versoepelen;
- een actie in een hogere of lagere klasse terecht moet komen dan het beleid nu zegt (dat is een besluit);
- een echte sleutel, een echt token of een echt wachtwoord in de werkboom, in een log of in de historie staat;
- een test alleen groen wordt met een echte NAS, een echt account of echte hardware: dat is geen fout maar een
  blokkade, zie P-EERLIJK.

### P-EERLIJK

**Wanneer:** bij elke stap. A-BOUW vult in; R-EERLIJK controleert onafhankelijk.
**Bron:** contract, kop "11. Bewijs en Excel (EVIDENCE.json)". Bestand per repo: `docs/platform-v2/EVIDENCE.json`.

Elke regel heeft de velden `id`, `status`, `validatie`, `bewijs`, `blokkade`, `opmerking`, `repo`, `bijgewerkt`.

Statuswoorden - welke mag je zetten:

| Situatie | `status` | `validatie` |
|---|---|---|
| Nog niet begonnen | `Niet gestart` | `Niet getest` |
| Gebouwd, tests en CI groen, in de simulator getest (werkpakket, installatiestap, contractpunt, review) | `Bezig` | `Sim-getest` of `Unit-getest` |
| Testregel (`EX..`, `JLT-..`) in de simulator geslaagd | `Bezig` | `Sim-geslaagd` |
| Testregel in de simulator mislukt | `Bezig` (de stap is niet klaar: hoofdstuk 3) | `Sim-mislukt` |
| Het vervolg vraagt de echte NAS | `Geblokkeerd` | de simulatorwaarde, dan `; NIET GEVALIDEERD (echte NAS)` |
| Het vervolg vraagt echte hardware (bijvoorbeeld de GPU's van de NAS) | `Geblokkeerd` | idem met `NIET GEVALIDEERD (hardware)` |
| Het vervolg vraagt een echt account | `Geblokkeerd` | idem met `NIET GEVALIDEERD (account)` |
| Het vervolg vraagt een Mac met Xcode | `Geblokkeerd` | idem met `NIET GEVALIDEERD (Mac/Xcode)` |
| Gemeten op de grafische kaart van de ontwikkelmachine | `Bezig` of `Geblokkeerd` | `Intel-iGPU-getest (ontwikkelmachine)`, plus `NIET GEVALIDEERD (hardware)` voor de NAS |
| Besluitregel (`D..`) | `Open`, `Ingevuld`, `Getest`, `Geblokkeerd` of `N.v.t.` | een waarde uit de vaste lijst; nooit leeg |

`Gereed` en `Geslaagd` worden NOOIT gezet. Die woorden horen bij acceptatie op de echte NAS en die kan in deze
bouwomgeving niet plaatsvinden.

Afvinklijst:

- [ ] 1. Elke ID die de stap raakt heeft een regel in `docs/platform-v2/EVIDENCE.json` van de repo. De ID staat
      letterlijk in `<WERKMAP>/.lokaal/plan/bron/ALLE_IDS.txt`
      (`grep -x '<ID>' <WERKMAP>/.lokaal/plan/bron/ALLE_IDS.txt`), of is een contractpunt `C1.3-<CODE>-<nn>` of
      `C1.2-<code>`, of een review `REVIEW-<repo>-<onderwerp>`.
- [ ] 2. `status` komt uit de tabel hierboven. Nergens `Gereed` of `Geslaagd`:
      `grep -nE '"status": *"(Gereed|Geslaagd)"' docs/platform-v2/EVIDENCE.json` geeft niets.
- [ ] 3. `validatie` is niet leeg, bevat alleen waarden uit de vaste lijst en scheidt meerdere waarden met `"; "`.
- [ ] 4. Staat er `NIET GEVALIDEERD (...)` in `blokkade`, dan staat dezelfde waarde ook in `validatie`. `blokkade`
      zegt wat nog nodig is en van wie (welk apparaat, welk account, welke handeling van de gebruiker).
- [ ] 5. `bewijs` noemt wat echt gedraaid is: de commit, het testbestand of het bewijsbestand, en de CI-run. Geen
      bewijs van een andere commit, geen "zou moeten werken".
- [ ] 6. `bijgewerkt` is de datum van vandaag; `repo` is de naam van de repo.
- [ ] 7. De EVIDENCE-test van de repo is groen (punt 5 van het P-<repo>-blok).
- [ ] 8. Het rapport van de stap noemt elke overgeslagen test met de reden die de test zelf geeft. Een overgeslagen
      test is geen geslaagde test.
- [ ] 9. Getallen in het rapport (aantal tests, duur) komen uit de uitvoer van deze run, niet uit een richtgetal in
      dit bestand.

R-EERLIJK herhaalt zelf, zonder het rapport van A-BOUW te vertrouwen:

```bash
git status --short
git log origin/ccr-c133d7a0-kuz1cv..HEAD --oneline
git log -1 --format='%H %s'
git show --stat HEAD
gh run list -R lvos04/<repo> --branch ccr-c133d7a0-kuz1cv --commit "$(git rev-parse HEAD)" --limit 10 \
  --json databaseId,workflowName,status,conclusion,headSha
grep -nE '"status": *"(Gereed|Geslaagd)"' docs/platform-v2/EVIDENCE.json
```

en daarna de EVIDENCE-test van de repo en minstens één commando uit de snelle variant dat het geraakte deel dekt.
Wijkt een uitkomst af van het rapport van A-BOUW, dan is de stap niet klaar en gaat hij terug (hoofdstuk 3).

Stop en meld (hoofdstuk 3) als:

- het rapport iets "klaar", "gereed", "geslaagd" of "werkt op de NAS" noemt zonder dat het gemeten is;
- een test is overgeslagen, uitgezet of verwijderd zonder dat het rapport het zegt;
- de CI-run hoort bij een andere commit dan de gemelde;
- EVIDENCE.json een status of validatie bevat die niet in de tabel staat.

### P-PEIL

**Wanneer:** de stap raakt een scherm van de Hub-UI, een statuspagina (home-control-hub, appstore-en-fork,
jelly-leon-platform, zoeken-en-persoonlijke-ai, executor), het uiterlijk van MediaGuard, MSO of my_house (web of
Android), of de ontwerptokens.
**Geldt NIET voor:** jelly-leon, jelly-leon-web en jelly-leon-clients. Die houden de Jellyfin-vormgeving met alleen
de zichtbare naam "Jelly Leon" (contract, kop "13. Ontwerptaal"). Deze drie repos hebben geen map
`design/ontwerptaal`.
**Bron (de Peil-bron staat in ai-server-manager):**

- `<WERKMAP>/ai-server-manager/docs/platform-v2/ONTWERPTAAL.md` - lees minstens de koppen "4. Kleursemantiek",
  "11. Nederlandse microcopy", "12. Toegankelijkheid en tests", "13. Per oppervlak" (met een eigen subkop per
  oppervlak) en "14. Verspreiding, versies en drift".
- `<WERKMAP>/ai-server-manager/design/ontwerptaal/` - `tokens.json`, `ontwerptaal.css`, `statuspagina.css`,
  `statuspagina.html`, `COMPONENTEN.md`, `components.json`, `contrast.json`, `REVIEW.md`, en de mappen `bouw`,
  `controle`, `prototypes`, `shots`, `aliaslagen`.
- Besluiten: ADR-0015, ADR-0024 en ADR-0025 in `<WERKMAP>/ai-server-manager/docs/adr/`; contract, kop
  "13. Ontwerptaal".
- De zeven andere Peil-repos (home-control-hub, appstore-en-fork, jelly-leon-platform, zoeken-en-persoonlijke-ai,
  media-guard-ultimate, media-source-optimizer, my_house) hebben een versie-gepinde kopie in hun eigen
  `design/ontwerptaal`. Die kopie wordt nooit met de hand gewijzigd; een verbetering van Peil gaat via een nieuwe Peil-versie in ai-server-manager en is een besluit
  (zie P-CONTRACT, "Stop en meld").

Volgorde (contract, kop "13. Ontwerptaal", "Werkwijze"):

1. **Ontwerpstap vooraf - A-ONTWERP.** Schermontwerp en componentkeuze binnen Peil, vastgelegd in `docs/ontwerp/`
   van de repo, vóór A-BOUW begint. Bestaande ontwerpdocumenten: `docs/ontwerp/HUB_PEIL_ONTWERP.md`
   (ai-server-manager) en `docs/ontwerp/PEIL_MIGRATIE.md` (media-guard-ultimate, media-source-optimizer, my_house).
   De stap noemt het bestand; noemt de stap er geen, dan vult A-ONTWERP het bestaande document van de repo aan.
2. **Bouw - A-BOUW.** Bouwt precies het ontwerp en draait de kolom "Controle tijdens de bouw" uit de tabel.
3. **Ontwerpreview achteraf - R-ONTWERP.** Meet de gebouwde UI met de kolom "Ontwerpreview" en legt de uitkomst
   vast in `docs/ontwerp/PEIL_REVIEW.md` van de repo (elke Peil-repo heeft dat bestand al; vul het aan met datum
   en commit). R-ONTWERP beslist zelfstandig over afwijkingen van Peil; het resultaat wordt de gebruiker achteraf
   getoond.

| Repo | Oppervlak | Controle tijdens de bouw | Ontwerpreview | Zo is het eerder gedaan: `docs/ontwerp/PEIL_REVIEW.md`, kop |
|---|---|---|---|---|
| ai-server-manager | Hub-UI (`apps/web`) en statuspagina van de executor | `make web-lint && make web-test`, `make web-e2e`; executor: `.venv/bin/python -m pytest -q apps/executor/tests/test_statuspagina.py` | `make web-build` en daarna `make web-review` (uitleg: `apps/web/review/README.md`) | "Werkwijze" en "Bewijs" |
| home-control-hub | statuspagina | `make test-ui` | `make schermafdrukken` en `.venv/bin/python tests/ui/ontwerpreview.py --uit tests/ui/review-uit` | "2. Werkwijze" |
| appstore-en-fork | statuspagina | `make test-ui` | `make schermafdrukken` en `PATH=/usr/lib/postgresql/16/bin:$PATH .venv/bin/python tests/ui/review_live.py --meting <map buiten de repo>` | "9. Opnieuw uitvoeren" |
| jelly-leon-platform | statuspagina | `make test-ui` | `make test-ui-live`; alleen in de reviewstap: `make statuspagina-shots` en `make ontwerpreview` | "6. Schermafdrukken en reproduceren" |
| zoeken-en-persoonlijke-ai | statuspagina | `make ui` | alleen in de reviewstap: `make ui-echt` | "10. Reproduceren" |
| media-guard-ultimate | web en Android | P-media-guard-ultimate, Volledig stap 5, 6 en 7 (`npm run check:peil`, de e2e-suite met `apps/web/e2e/peil.spec.ts`, `tools/peil_tokens.py --check`, `:app:verifyPaparazziDebug`) | dezelfde stappen, plus de commando's onder de genoemde kop | "9. Uitgevoerde controles (exacte commando's)" |
| media-source-optimizer | web | P-media-source-optimizer, Volledig stap 4 en 8 (`npm run check:peil`, `make e2e` met `apps/web/e2e/peil.spec.ts`) | dezelfde stappen, plus de commando's onder de genoemde kop | "10. Opnieuw draaien" |
| my_house | web en Android | P-my_house, Volledig stap 7 en 10 (`apps/web/e2e/run-stack.sh` met `apps/web/e2e/peil-metingen.ts`, `apps/android/tools/peil_tokens.py --check`, `:app:verifyPaparazziDebug`) | dezelfde stappen, plus de commando's onder de genoemde kop | "9. Bestanden en opnieuw meten" |

home-control-hub en zoeken-en-persoonlijke-ai: draai elk commando uit deze tabel dat PostgreSQL gebruikt (home-control-hub:
`make test-ui`, `make schermafdrukken`, `tests/ui/ontwerpreview.py`; zoeken-en-persoonlijke-ai: `make ui-echt`) achter de
databaselock van de repo, bv. `flock <WERKMAP>/.lokaal/hch-db.lock make schermafdrukken` (0.3 regel 5).

Driftcontrole van de Peil-kopie (elke Peil-repo behalve de bron): zie punt 5 van het P-<repo>-blok. Kort:
`make peil-drift` (home-control-hub, appstore-en-fork), `make test-repo` (jelly-leon-platform),
`python3 scripts/kopie-herkomst.py controleer` (media-guard-ultimate), `python3 scripts/bronkopie.py controleer`
(media-source-optimizer), `python3 tools/peil_kopie.py controleer` (my_house), en de test
`apps/api/tests/unit/test_peil_kopie.py` (zoeken-en-persoonlijke-ai, appstore-en-fork).

Afvinklijst (normen uit het contract, kop "13. Ontwerptaal", en `ONTWERPTAAL.md`, kop "12. Toegankelijkheid en tests"):

- [ ] 1. Er is een ontwerpstap van A-ONTWERP voor dit scherm, vastgelegd in `docs/ontwerp/` vóór de bouw.
- [ ] 2. Alleen tokens en componenten uit Peil; geen losse kleurwaarden, geen eigen lettertype, geen extern CDN.
      Statuspagina's werken zonder JavaScript en gebruiken framework-vrije CSS uit dezelfde tokens.
- [ ] 3. Gemeten op de breedtes 320, 360, 390, 768, 1024 en 1440 px, in licht en donker.
- [ ] 4. WCAG 2.2 AA: axe met de tags `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, `wcag22aa` geeft 0 bevindingen.
- [ ] 5. Focus is zichtbaar en nooit bedekt; alles is met het toetsenbord te bereiken.
- [ ] 6. Tekstafstand kan worden vergroot zonder overloop; op 320 px is er geen horizontaal schuiven.
- [ ] 7. Aanraakdoelen zijn minstens 44 px.
- [ ] 8. Teksten zijn Nederlands en gebruiken de vaste woorden uit `ONTWERPTAAL.md`, kop "11.1 Vaste woorden
      (overal gelijk, ook in statuspagina's en de bestaande apps)".
- [ ] 9. Een waarde heeft eenheid, bron en "laatst bijgewerkt". Onbekend (`unknown`) of verouderd is nooit groen.
      Status wordt nooit met alleen kleur getoond.
- [ ] 10. Bij MediaGuard, MSO en my_house verandert alleen het uiterlijk: functies, routes, gebruikersreizen, API's
      en het datamodel blijven gelijk (contract, kop "2.3 Bestaande apps (MediaGuard, MSO, my_house,
      Jellyfin/Jelly Leon, Emby)"). Raakt de stap toch gegevens: P-HARDE-EIS.
- [ ] 11. De driftcontrole van de Peil-kopie is groen.
- [ ] 12. R-ONTWERP heeft de ontwerpreview gedaan op de gepushte commit en `docs/ontwerp/PEIL_REVIEW.md` bijgewerkt.
      Elke harde bevinding is gerepareerd of staat als open punt in het rapport van de stap.

Commando's die bestanden IN de repo vervangen (referentiebeelden, schermafdrukken, reviewuitvoer):

| Repo | Commando | Vervangt |
|---|---|---|
| home-control-hub, appstore-en-fork | `make schermafdrukken` | `docs/screenshots/peil/statuspagina` |
| jelly-leon-platform | `make statuspagina-shots`, `make ontwerpreview` | `docs/screenshots/peil/statuspagina`, en in `docs/ontwerp`: `live.json`, `rapport-live.json`, `shots` |
| zoeken-en-persoonlijke-ai | `make ui-echt` | `docs/screenshots/peil/statuspagina` |
| media-guard-ultimate, my_house (Android) | `./gradlew :app:recordPaparazziDebug` | de referentiebeelden van de schermtests |
| media-source-optimizer | `make e2e` | kan afdrukken in de repo opnieuw renderen |

Regel: draai zo'n commando alleen als de stap het uiterlijk bewust wijzigt en het ontwerp dat voorschrijft. Bekijk
daarna `git status --short` en `git diff --stat`. Gewijzigde beelden die niet bij de stap horen zet je terug met
`git checkout -- <pad>`; je commit ze niet mee.

Stop en meld (hoofdstuk 3) als:

- een schermtest (`verifyPaparazziDebug`, een Playwright-vergelijking) faalt en de enige weg naar groen het opnieuw
  opnemen van de referentiebeelden is, terwijl het ontwerp geen wijziging van dat scherm voorschrijft;
- het ontwerp iets vraagt dat Peil niet heeft (een nieuw token, een nieuw component, een ander woord);
- een norm alleen gehaald wordt door de meting te versoepelen (minder breedtes, een axe-regel uit, een lagere
  contrastgrens);
- de driftcontrole rood is: dan is de bron of de pin veranderd, zie P-CONTRACT.

### P-HARDE-EIS

**De eis (van de gebruiker; niet onderhandelbaar):** alle kijkgeschiedenis (gezien, hervatpunten, favorieten,
beoordelingen, spoorkeuzes, gebruikers) en de MediaGuard-voortgang blijven altijd beschikbaar. Emby blijft werken en
wordt nooit onderbroken. Er is geen overstap zonder vóór/na-rapport per gebruiker en uitdrukkelijk akkoord van de
gebruiker. De oude installatie blijft de terugval. De gebruiker verwijdert Emby zelf.
**Bron:** contract, kop "2.3 Bestaande apps (MediaGuard, MSO, my_house, Jellyfin/Jelly Leon, Emby)", regels 7 en 8;
ADR-0020 in `<WERKMAP>/ai-server-manager/docs/adr/`;
`<WERKMAP>/ai-server-manager/docs/platform-v2/01_ARCHITECTUUR/06_FASERING_EN_GATES.md`, kop "Gate matrix";
`<WERKMAP>/jelly-leon/docs/platform-v2/OVERNAME_EMBY.md` en `B03-016_HARNAS.md` in dezelfde map.
**Wanneer:** de stap raakt een databaseschema of migratie, het upgradepad of de versie van een image, het
entrypoint of de opslagindeling van een app met gebruikersgegevens, de Emby-overname, de spelerkoppelingen van
MediaGuard, of iets dat Emby of de bestaande mediaserver kan stoppen, herstarten of wijzigen. Bij twijfel: draaien.

Welk bewijs bestaat en wanneer het verplicht is:

| Repo | Wat het bewijst | Waar het commando staat | ID | Verplicht |
|---|---|---|---|---|
| media-guard-ultimate | Upgrade van een gevulde database van de vorige release naar de nieuwe image, en terugzetten: niets verloren. Vorige release: `deploy/upgradebewijs/vorige-release.json`; kandidaat: `deploy/upgradebewijs/Dockerfile.kandidaat`; test van het gereedschap: `apps/core/tests/test_upgradebewijs.py` | P-media-guard-ultimate, Volledig stap 3 (`scripts/upgradebewijs.py`) | C1.3-MGU-03 | Bij elke wijziging aan `apps/core`, het schema, `deploy/` of de release; altijd vóór een release |
| media-guard-ultimate | Migratiewizard: de oude instanties krijgen vóór de cutover geen enkel muterend verzoek en staan na cutover of rollback exact in hun vorige staat: `apps/core/tests/test_migration.py` (hulpmodule: `apps/core/tests/test_migration_fakes.py`) | P-media-guard-ultimate, Volledig stap 1 | - | Bij elke wijziging aan `apps/core` |
| media-source-optimizer | Upgrade vanaf het 1.5.0-schema in de alles-in-één image: `tests/stack/allinone_test.py` | P-media-source-optimizer, Volledig stap 6 | - | Bij elke wijziging aan schema, entrypoint of image |
| jelly-leon | Terugzetproef: terug naar de upstream-image zonder verlies (`tools/jelly-leon/e2e/rollback_sim.py`) | P-jelly-leon, Volledig stap 6 | B03-013 | Bij elke wijziging aan server, plugins of image |
| jelly-leon | Upgradeproef op een gevulde installatie (`tools/jelly-leon/e2e/upgrade_proef.py`) | P-jelly-leon, Volledig stap 6 | JLT-60, JLT-61 | Bij elke wijziging aan server, plugins of image |
| jelly-leon | Emby-overname: proefrun met een echte Emby-container en een stock-server (`tools/emby-overname/e2e/proefrun.py`) en de tests in `tools/emby-overname/tests` | P-jelly-leon, Volledig stap 8 | B03-015; JLT-70, JLT-71, JLT-72, JLT-73 | Bij elke wijziging onder `tools/emby-overname` en vóór elke stap die naar de overname toewerkt |
| jelly-leon | Vergelijkingsharnas stock tegenover fork (`tools/b03-harnas`), met een negatieve proef die moet falen | P-jelly-leon, Volledig stap 9 | B03-016 | Bij elke wijziging aan server, plugins of image |
| jelly-leon-web | Upgradeproef: kijkgegevens per gebruiker vóór en na gelijk (`tools/jelly-leon-web/e2e/upgrade_proef.py`) | P-jelly-leon-web, Volledig stap 5 | - | Bij elke wijziging aan de web-fork die in de image komt |
| ai-server-manager, home-control-hub, appstore-en-fork, zoeken-en-persoonlijke-ai | Migraties heen en terug op een eigen database | P-ai-server-manager stap 4; P-home-control-hub stap 5; P-appstore-en-fork stap 5; P-zoeken-en-persoonlijke-ai stap 5 | - | Bij elke nieuwe of gewijzigde migratie |
| my_house | Back-up en terugzetten: `apps/api/tests/test_ws_backup_api.py`, `apps/api/tests/test_ws_backup_format.py`, `apps/api/tests/test_ws_backup_restore.py` | P-my_house, Volledig stap 4 | - | Bij elke wijziging aan schema of back-up |

ONBEKEND of jelly-leon-platform en jelly-leon-clients eigen proeven hebben die kijkgegevens bewaken - eerst
vaststellen met: `grep -rIlE 'kijkgeschiedenis|hervat|favoriet|UserData' --exclude-dir=node_modules --exclude-dir=.venv apps tests tools`
in de werkmap van die repo. Vindt de stap in zo'n repo een pad dat kijkgegevens kan wijzigen en is er geen proef:
stop en meld.

Afvinklijst:

- [ ] 1. De proeven uit de tabel voor de geraakte repo zijn gedraaid en groen, op de commit die gepusht wordt.
- [ ] 2. De uitkomst is letterlijk "niets verloren": de vergelijking vóór/na per gebruiker toont geen enkel verschil
      in gezien, hervatpunt, favoriet, beoordeling, spoorkeuze en gebruiker. Voor MediaGuard: het rapport bevat
      zowel "Upgrade: niets verloren" als "terugzetten: niets verloren".
- [ ] 3. De proef draaide op een GEVULDE database van de vorige versie, niet op een lege.
- [ ] 4. De negatieve proef van het vergelijkingsharnas faalt zoals bedoeld (P-jelly-leon, Volledig stap 9, laatste
      regel). Slaagt die proef, dan meet de vergelijking niets: rood. In P-jelly-leon-web, Volledig stap 5, hoort het
      negatieve deel (JLT-61) bij de proef zelf: `--negatief-verwacht start` legt het gemeten gedrag van de oude
      upstream-image vast. Die waarde wordt niet gewijzigd om de proef groen te krijgen.
- [ ] 5. Terugzetten is bewezen als "vorige image en snapshot samen" (contract, kop 2.3, regel 7), niet alleen als
      "oude image starten".
- [ ] 6. Geen code in de stap schrijft rechtstreeks in de database van Emby, Jelly Leon of MediaGuard, en geen
      platformactie doet dat. Een UI-ronde wijzigt geen datamodel.
- [ ] 7. Niets in de stap stopt, herstart, wijzigt of verwijdert Emby of de bestaande mediaserver, ook niet in een
      script, een manifest, een installatiedocument of een "opruimstap". Proeven gebruiken eigen containers.
- [ ] 8. De overnametools lezen Emby alleen: alleen GET, de databasebestanden van Emby worden nooit geopend (bron:
      `<WERKMAP>/jelly-leon/docs/platform-v2/OVERNAME_EMBY.md`, koppen "Wat er overgaat — en wat niet" en "Stappen").
- [ ] 9. EVIDENCE.json: status hooguit `Bezig`, of `Geblokkeerd` met `NIET GEVALIDEERD (echte NAS)`. Een proef in
      de simulator is geen overstap.
- [ ] 10. R-HARDE-EIS heeft de uitvoer van de proeven zelf gelezen (niet het rapport van A-BOUW) en de punten 2, 3
      en 4 bevestigd.

Wat geen agent ooit doet (ook niet als een stap het lijkt te vragen):

- een overstap, cutover of migratie van de echte mediaserverdatabase uitvoeren;
- Emby stoppen, bijwerken of verwijderen, of een tekst schrijven die de gebruiker opdraagt dat te doen zonder de
  controlelijst (rij Controlelijst "Emby verwijderen" in de "Gate matrix"; uitgewerkt in
  `<WERKMAP>/jelly-leon/docs/platform-v2/OVERNAME_EMBY.md`, kop "Controlelijst "Emby verwijderen" (u voert dit
  zelf uit — geen enkele agent verwijdert Emby)"): de gebruiker beslist en voert uit;
- een verschil in het vóór/na-rapport "klein" of "verwacht" noemen en doorgaan;
- een fixture met gevulde gegevens kleiner of leger maken, of een vergelijkingsveld uit de proef halen;
- de vorige release in `deploy/upgradebewijs/vorige-release.json` verzetten om een rode upgradeproef te omzeilen.

Stop en meld DIRECT, zonder herstelpoging (hoofdstuk 3, tak HARDE EIS), als:

- een proef één verschil toont in kijkgegevens, gebruikers of MediaGuard-voortgang;
- een upgrade- of terugzetproef rood is;
- de stap alleen kan slagen met een schrijfactie in de database van Emby, Jelly Leon of MediaGuard;
- de stap de echte NAS, de echte Emby of echte gebruikersgegevens nodig heeft: dat is `Geblokkeerd` met
  `NIET GEVALIDEERD (echte NAS)` en een beschrijving van wat de gebruiker moet doen en goedkeuren.

### P-INSTALLATIE

**De regel (van de gebruiker):** installeren gaat altijd als standaard TrueNAS Custom App, met één alles-in-één
image per repo. YAML of compose is nooit een installatieweg.
**Bron:** contract, koppen "1. Vaste keuzes (van de gebruiker)", "2.2 Custom App-realiteit (gemeten in de bronnen,
niet op een echte NAS)", "9. Manifeststandaard (B08-001, eigenaar `appstore-en-fork`)";
`<WERKMAP>/appstore-en-fork/docs/MANIFESTSTANDAARD.md`.
**Wanneer:** de stap raakt een Dockerfile, een entrypoint, een healthcheck, een manifest, poorten, opslagpaden,
omgevingsvariabelen van de image, of een installatiedocument.
**Geldt niet voor:** jelly-leon-clients (geen image). jelly-leon-web heeft geen eigen image en geen manifest: de
web-fork komt in de image van jelly-leon; alleen `deploy/truenas/CUSTOM_APP.md` hoort hier bij deze poort.

Manifestvalidatie per repo (exitcode 0 is verplicht; `--strict` faalt op elke waarschuwing die niet in
`accepted_findings` van het manifest staat):

| Repo | Manifest | Validatie (vanuit de werkmap van de repo) | Test die de installatieregels afdwingt |
|---|---|---|---|
| ai-server-manager | `deploy/manifest/ai-server-manager.manifest.yaml`, `deploy/manifest/ai-server-manager-executor.manifest.yaml` | P-ai-server-manager, Volledig stap 9 | `apps/api/tests/unit/test_eigen_manifesten.py` |
| home-control-hub | `deploy/manifest/home-control-hub.manifest.yaml` | `<WERKMAP>/appstore-en-fork/.venv/bin/jl-manifest validate --strict deploy/manifest/home-control-hub.manifest.yaml` | `apps/api/tests/unit/test_deploy_artifacts.py` |
| appstore-en-fork | `deploy/manifest/appstore-en-fork.manifest.yaml` | `make manifest` | `apps/api/tests/unit/test_manifest_rules.py`, `apps/api/tests/unit/test_manifest_bypass.py`, `apps/api/tests/unit/test_ex47.py` |
| jelly-leon-platform | `deploy/manifest/jelly-leon-platform.manifest.yaml` en de manifesten onder `install/manifests/` | `make validator-venv && make manifesten` | `tests/repo/test_repo_rules.py`, `tests/repo/test_installeerbare_manifesten.py` |
| zoeken-en-persoonlijke-ai | `deploy/manifest/zoeken-en-persoonlijke-ai.manifest.yaml` | `<WERKMAP>/appstore-en-fork/.venv/bin/jl-manifest validate --strict deploy/manifest/zoeken-en-persoonlijke-ai.manifest.yaml` | `apps/api/tests/unit/test_deploy_artifacts.py` |
| jelly-leon | `deploy/manifest/jelly-leon.manifest.yaml` | P-jelly-leon, Volledig stap 2 | `tools/jelly-leon/tests/test_manifest_1_3.py` |
| media-guard-ultimate | nog geen manifest; image uit `deploy/aio/Dockerfile` | open punt, zie onder | - |
| media-source-optimizer | nog geen manifest; image uit `deploy/allinone/Dockerfile` | open punt, zie onder | - |
| my_house | nog geen manifest en nog geen alles-in-één image | open punt, zie onder | - |

Afvinklijst:

- [ ] 1. Het manifest valideert met `--strict` en exitcode 0, met de validator van de naburige appstore-en-fork.
      Controleer ook de pin: de CI van de repo gebruikt de validator op een vaste commit (`ASF_COMMIT`,
      `VALIDATOR_COMMIT` of `APPSTORE_COMMIT` in de workflow). Lokaal groen en CI rood op het manifest betekent
      meestal dat de pin achterloopt; de pin verzetten is een eigen, gemelde wijziging.
- [ ] 2. `install.method` is `custom_app` (of `catalog_app` met `install.reason`). Er is geen `compose`-veld. Er is
      precies één image; de tag is niet `latest`.
- [ ] 3. Poorten staan alleen in `network.ports`. `host_network` is `false` en `privileged` is `false`, tenzij het
      manifest de reden noemt en het besluit erbij staat. De app draait als 568 (de AI-runner van de Hub als 569).
- [ ] 4. Geen wachtwoord, token of sleutel in het manifest of in het formulier. Geen voorbeeldwaarde die op een
      echte NAS lijkt (pad, pool, adres) in manifest of installatiedocument.
- [ ] 5. De image is gebouwd en de proef op de image is groen (de stap met de image in het P-<repo>-blok, onder
      "Volledig").
- [ ] 6. `deploy/truenas/CUSTOM_APP.md` beschrijft de installatie via het formulier van de Custom App en is
      bijgewerkt als een poort, pad, variabele of versie is veranderd. Het document noemt YAML of compose nergens als
      installatieweg.
- [ ] 7. Een compose-bestand in de repo dient alleen ontwikkeling of een test (bijvoorbeeld
      `<WERKMAP>/ai-server-manager/deploy/dev/compose.yaml`) en geen enkel document verwijst ernaar als manier om te
      installeren.
- [ ] 8. De tests uit de laatste kolom zijn groen; de weigerfixtures in appstore-en-fork
      (`apps/api/tests/fixtures/manifests/compose-forbidden.manifest.yaml`,
      `apps/api/tests/fixtures/manifests/ex47-privileged-hostmount.manifest.yaml`) bestaan nog en worden nog
      geweigerd.
- [ ] 9. R-MANIFEST heeft het manifest en het installatiedocument naast elkaar gelezen: elke poort, elk pad en elke
      variabele komt in beide overeen.
- [ ] 10. EVIDENCE.json: installeren is in deze bouwomgeving nooit gevalideerd op de NAS. Status hooguit `Bezig`, of
      `Geblokkeerd` met `NIET GEVALIDEERD (echte NAS)`.

Open punt - media-guard-ultimate, media-source-optimizer en my_house hebben nog geen manifest en geen
`deploy/truenas/CUSTOM_APP.md`. Dat is werk voor de fase van de bestaande apps (zie
`CONTRACT_1.3_CONFORMITEIT.md`, koppen "6. media-guard-ultimate (MediaGuard, bestaande app; P3 en P4-0)",
"7. media-source-optimizer (MSO, bestaande app; P3)" en "8. my_house (bestaande app; P3)"; voor my_house onder
andere C1.3-MH-03 en C1.3-MH-06). Er bestaan wel oudere installatiedocumenten op een andere plek:
`media-source-optimizer/docs/TRUENAS_CUSTOM_APP.md` en `media-guard-ultimate/docs/INSTALL_TRUENAS.md`; een stap die
`deploy/truenas/CUSTOM_APP.md` maakt, neemt die inhoud mee en laat geen twee tegenstrijdige documenten achter.
my_house installeert nu nog met een compose-YAML; de stand en de richting
staan in `<WERKMAP>/my_house/docs/adr/ADR-0004-alles-in-een-custom-app.md`, kop "Context". Tot die
stappen gebouwd zijn geldt voor deze drie repos: punten 2 tot en met 9 kunnen niet groen zijn; EVIDENCE.json zegt
dat eerlijk (`Niet gestart` of `Bezig`), en een stap die een installatiedocument voor deze repos schrijft noemt
compose nergens als de weg voor de gebruiker. Stand vaststellen:
`ls deploy/manifest deploy/truenas 2>/dev/null` in de werkmap van de repo.

Stop en meld (hoofdstuk 3) als:

- de app niet in één image past, host-netwerk, `privileged` of een extra apparaat nodig heeft, of als root moet
  draaien: dat is een besluit, geen bouwkeuze;
- de validator een regel afdwingt die de stap niet kan halen: de regel wordt niet versoepeld (eigenaar:
  appstore-en-fork, zie P-CONTRACT);
- een waarschuwing alleen weg kan door hem in `accepted_findings` te zetten: dat mag alleen voor de codes die het
  contract daarvoor noemt (kop "9. Manifeststandaard (B08-001, eigenaar `appstore-en-fork`)") en wordt gemeld.

### P-EXCEL

**Wanneer:** na elke fase, en na elke stap die een status of validatie in een EVIDENCE.json heeft gewijzigd en waar
de regisseur om vraagt. Excel bijwerken is SCHRIJVEN in ai-server-manager: één agent tegelijk in die repo, dus de
regisseur plant deze poort als eigen stap en nooit naast een bouwketen in ai-server-manager.
**Bron:** `<WERKMAP>/ai-server-manager/tools/excel/README.md`; contract, kop "11. Bewijs en Excel (EVIDENCE.json)".
**Werkmap:** `<WERKMAP>/ai-server-manager`. **Omgeving:** de lokale venv `<WERKMAP>/.lokaal/excel-venv`. Het script
zelf heeft alleen de standaardbibliotheek nodig, maar de tests van het gereedschap vragen `pytest` en `openpyxl`;
die stonden op 2026-11-11 NIET in deze venv (alleen `lxml`). Al klaar?
`<WERKMAP>/.lokaal/excel-venv/bin/python -c "import pytest, openpyxl"` (exitcode 0). Anders eenmalig:
`<WERKMAP>/.lokaal/excel-venv/bin/python -m pip install -r tools/excel/requirements-test.txt` (vaste versies; de venv
staat buiten de repo).

Afvinklijst:

- [ ] 1. Het script leest de EVIDENCE.json uit de WERKMAP van alle repos naast ai-server-manager. Die moet dus de
      gepushte stand zijn. De regisseur start P-EXCEL alleen als in GEEN enkele repo een schrijvende keten open is
      (een `git pull` in een repo is schrijven). Per repo, vanuit `<WERKMAP>/<repo>`:
      ```bash
      git fetch origin ccr-c133d7a0-kuz1cv
      git status --short -- docs/platform-v2/EVIDENCE.json      # moet leeg zijn
      git log --oneline HEAD..origin/ccr-c133d7a0-kuz1cv        # leeg = al bij
      git log --oneline origin/ccr-c133d7a0-kuz1cv..HEAD        # moet leeg zijn (niets ongepusht)
      ```
      Loopt de repo achter en is `git status --short` helemaal leeg: `git pull --rebase origin ccr-c133d7a0-kuz1cv`.
      Staat er ander werk (bijvoorbeeld half werk uit ronde 3, zie `<WERKMAP>/.lokaal/plan/STAND_RONDE3.md`): NIET
      pullen, niets weggooien of wegzetten; melden aan de regisseur en wachten tot de keten van die repo klaar is.
- [ ] 2. Het gereedschap zelf is groen:
      ```bash
      <WERKMAP>/.lokaal/excel-venv/bin/python -m pytest -q tools/excel/tests
      ```
- [ ] 3. Proefrun naar een bestand BUITEN de repo (er wordt niets in de repo gewijzigd):
      ```bash
      <WERKMAP>/.lokaal/excel-venv/bin/python tools/excel/update_excel.py \
        --xlsx docs/platform-v2/08_EXCEL/TrueNAS_V2_Uitvoering_en_Afvinken.xlsx \
        --evidence ../*/docs/platform-v2/EVIDENCE.json --program docs/platform-v2/EVIDENCE_PROGRAMMA.json \
        --out <bestand buiten de repo>.xlsx
      ```
      Lees de JSON-uitvoer: `bijgewerkt_per_blad`, `gewijzigde_onderdelen`, `contractpunten_en_reviews` en
      `waarschuwingen`. Exitcode 2 met "FOUT: ... er is niets geschreven" betekent dat het script weigert. Lees de
      foutregel; mogelijke oorzaken (bron: `raise ExcelFout` in `tools/excel/update_excel.py`): een status `Gereed`
      of `Geslaagd`, een onbekende status, een onleesbaar EVIDENCE-bestand, een ontbrekend blad. Herstel een
      EVIDENCE-regel in de repo van herkomst (P-EERLIJK), nooit in het script; een ontbrekend blad of een andere
      oorzaak: stop en meld.
- [ ] 4. Elke waarschuwing is gelezen en verklaard. Een waarschuwing dat bewijs met `Gereed` of `Geslaagd` is
      teruggezet naar `Bezig` betekent: de EVIDENCE.json van die repo is fout en wordt daar hersteld.
- [ ] 5. De echte run (het exacte commando; schrijft het Excel-bestand in de repo en maakt een `.xlsx.bak`):
      ```bash
      <WERKMAP>/.lokaal/excel-venv/bin/python tools/excel/update_excel.py \
        --xlsx docs/platform-v2/08_EXCEL/TrueNAS_V2_Uitvoering_en_Afvinken.xlsx \
        --evidence ../*/docs/platform-v2/EVIDENCE.json --program docs/platform-v2/EVIDENCE_PROGRAMMA.json
      ```
- [ ] 6. Het script is idempotent: een tweede run direct erna meldt geen gewijzigde onderdelen meer.
- [ ] 7. Verwijder het reservebestand na controle: `rm docs/platform-v2/08_EXCEL/TrueNAS_V2_Uitvoering_en_Afvinken.xlsx.bak`.
      `git status --short -- docs/platform-v2/` toont daarna alleen het `.xlsx`-bestand (en, als die is bijgewerkt,
      `docs/platform-v2/EVIDENCE_PROGRAMMA.json`). Zet alleen die paden klaar met `git add <pad>`, nooit `git add -A`:
      in ai-server-manager kan ander (half) werk in de werkmap staan dat niet bij deze poort hoort. Het
      `.bak`-bestand wordt nooit gecommit.
- [ ] 8. P-GIT in ai-server-manager, met een Nederlands commitbericht dat de fase noemt. Daarna CI-controle (0.5);
      de job `excel` van `ci.yml` draait de tests van het gereedschap.
- [ ] 9. Het rapport noemt: het aantal bijgewerkte rijen per blad, alle waarschuwingen, en dat er nergens `Gereed`
      of `Geslaagd` staat.

Regels:

- Het script kiest bij meerdere bewijsregels voor één ID de voorzichtigste status. Dat is bedoeld; "los" het niet op
  door bewijs weg te halen.
- De Excel wordt nooit met de hand of met een ander gereedschap bewerkt.
- De glob `../*/docs/platform-v2/EVIDENCE.json` raakt alleen de repos in `<WERKMAP>`. De map `ai-factory` staat
  daar niet en wordt nooit aangeraakt.

Stop en meld (hoofdstuk 3) als:

- `waarschuwingen` een regel bevat die je niet kunt verklaren, bijvoorbeeld "onbekende status ... genegeerd" of
  "<ID>: geen rij gevonden in blad <blad>" (het ID uit een EVIDENCE.json heeft dan geen rij in de Excel; een rij
  toevoegen is een eigen stap met de opties uit `tools/excel/README.md`, geen handwerk);
- een status in de Excel na de run "beter" is dan in de EVIDENCE.json van de repo;
- de tests van het gereedschap rood zijn: dan wordt de Excel niet bijgewerkt.

---

## 3. Als een poort faalt

Dit hoofdstuk is een vaste beslisboom. Hij geldt voor elke poort in dit bestand en voor elke agent (A-BOUW,
A-HERSTEL, R-EERLIJK, A-GATE en de reviewers). "Faalt" betekent: een commando geeft een andere exitcode dan 0, een
afvinkpunt kan niet worden aangevinkt, een test is overgeslagen zonder dat het P-<repo>-blok dat verwacht, een
richtgetal is gedaald zonder uitleg, of de CI-run op de gepushte commit is rood.

### 3.1 Vier regels die altijd gelden

1. **Eerst de oorzaak, dan pas een wijziging.** Niemand wijzigt code, een test of een instelling voordat de oorzaak
   in één of twee zinnen is opgeschreven. "Opnieuw proberen tot het groen is" is geen herstel.
2. **Maximaal twee herstelpogingen** per stap. Daarna stoppen en melden (3.6).
3. **Nooit groen maken door de meting te veranderen.** Geen test uitzetten, geen drempel verlagen, geen controle
   overslaan (de volledige lijst staat in 3.7).
4. **Een subagent vraagt de gebruiker niets en beslist niets dat een besluit is.** Hij stopt en meldt aan de
   regisseur. De regisseur legt een keuze met een keuzemenu voor aan de gebruiker.

### 3.2 Stap 1 - Stop en leg vast

Doe dit direct na de fout, vóór elke andere handeling:

- [ ] 1. Start geen volgend commando van de poort. Laat lopende zware commando's van jezelf eerst eindigen of stop
      ze netjes. Ruim alleen op wat je zelf hebt gestart; wat je niet kunt opruimen noem je in de melding onder
      "Achtergelaten" (3.6).
- [ ] 2. Bewaar de uitvoer: het letterlijke commando, de werkmap, de exitcode en de eerste foutregel. Bij een rode
      CI-run: `gh run view <run-id> -R lvos04/<repo> --log-failed`.
- [ ] 3. Leg de stand van de repo vast: `git status --short` en `git log origin/ccr-c133d7a0-kuz1cv..HEAD --oneline`.
- [ ] 4. Gooi niets weg: geen `git reset --hard`, geen `git checkout -- .`, geen `git clean`, geen `git stash drop`.
      (Het terugzetten van opnieuw gerenderde beelden die niet bij de stap horen, zoals P-PEIL beschrijft, blijft
      toegestaan: dat gaat per bestand, met het pad erbij.)
- [ ] 5. Push geen commit waarvan je weet dat hij een poort rood maakt.

### 3.3 Stap 2 - Deel de oorzaak in

Loop de tabel van boven naar beneden af en neem de EERSTE tak die past. De takken F, G en H gaan altijd voor.

| Tak | Herken je aan | Herstelpoging toegestaan? | Verder in |
|---|---|---|---|
| F - HARDE EIS | Een proef uit P-HARDE-EIS is rood; één verschil in kijkgegevens, gebruikers of MediaGuard-voortgang; iets raakt Emby of de bestaande mediaserver | NEE - direct stoppen en melden | 3.4 F |
| G - Veiligheid of geheim | gitleaks-treffer; een weigertest uit P-VEILIG laat iets door; een sleutel, token of wachtwoord staat in een bestand, log of rapport; een policy- of risicoregel moet wijken om groen te worden | NEE - direct stoppen en melden | 3.4 G |
| H - Besluit nodig | De poort kan alleen groen worden door een contractpunt, een Peil-regel, een manifestregel, een pin of de opdracht van de stap te wijzigen; of de stap vraagt een echte NAS, hardware of een account | NEE - direct stoppen en melden | 3.4 H |
| A - Omgeving | De fout zit in de machine en niet in de wijziging: geheugen op (exitcode 137), schijf vol, poort bezet, lock wacht, netwerk of registry onbereikbaar, verkeerde versie van een hulpprogramma, ontbrekende browser | Omgeving herstellen en opnieuw draaien; hooguit twee keer | 3.4 A |
| D - Was al rood | Dezelfde fout bestaat ook zonder jouw wijziging (de CI-run van de vorige commit was al rood, of de falende test raakt geen bestand van deze stap) | NEE voor A-BOUW - melden | 3.4 D |
| E - Alleen in de CI rood | Lokaal groen op dezelfde commit, CI rood | Ja, telt mee in de twee pogingen | 3.4 E |
| B - Eigen wijziging | De fout wijst naar een bestand dat deze stap heeft gewijzigd of toegevoegd | Ja, telt mee in de twee pogingen | 3.4 B |
| C - De test klopt niet meer | De code doet wat de stap voorschrijft, en de test legt het OUDE gedrag vast dat de stap volgens zijn opdracht wijzigt | Alleen onder de voorwaarden van 3.4 C; telt mee | 3.4 C |

Past geen enkele tak, of twijfel je tussen twee takken: behandel het als tak H (stoppen en melden, oorzaak "niet
gevonden"). Een oorzaak gokken is verboden; "niet gevonden" melden is toegestaan.

### 3.4 Tak voor tak

**Tak F - HARDE EIS.** Geen herstelpoging, ook geen "kleine". Doe alleen 3.2 en meld volgens 3.6. Noem in de melding
letterlijk welk gegeven verschilt (gebruiker, soort gegeven, waarde vóór en na) of welke proef rood is. De regisseur
zet R-HARDE-EIS in en legt het voor aan de gebruiker. Wat in geen geval gebeurt staat in P-HARDE-EIS onder "Wat geen
agent ooit doet".

**Tak G - Veiligheid of geheim.** Geen herstelpoging aan regels, tests of policy. Wel direct doen:

- een echt geheim in een nog NIET gecommit bestand: de waarde uit het bestand halen, niet committen, melden;
- een geheim dat al gecommit of gepusht is: NIET proberen de historie te herschrijven, niet force-pushen; melden
  dat de waarde als gelekt moet worden behandeld. De gebruiker beslist over vervangen en over de historie;
- een weigertest die iets doorlaat: de wijziging die dat veroorzaakt niet pushen; melden met de naam van de test.

De regisseur zet R-VEILIG in. Neem een gevonden geheim nooit over in de melding; noem alleen bestand, regel-ID van
gitleaks en soort.

**Tak H - Besluit nodig.** Niets wijzigen. Meld volgens 3.6 en geef onder "Nodig" de keuzes die je ziet, elk met het
gevolg. Voorbeelden uit dit bestand: een pin verzetten (`ASF_COMMIT`, `VALIDATOR_COMMIT`, `ASM_COMMIT`,
`APPSTORE_COMMIT`, `web_fork_commit`), een contractkopie of Peil-kopie bijwerken, een code in `accepted_findings`
zetten, een proef die alleen op de echte NAS kan. Kan de stap niet verder zonder echte NAS, hardware of account, dan
is dat geen fout van de poort: de status wordt `Geblokkeerd` met `NIET GEVALIDEERD` en wat er nodig is (P-EERLIJK).

**Tak A - Omgeving.** Herstel de omgeving, niet de code. Vaste oorzaken en wat je doet:

| Verschijnsel | Eerst controleren | Dan |
|---|---|---|
| Exitcode 137, of een proces dat zonder foutmelding stopt | `free -m` | Volg 0.3 regel 2 (eerst ander werk, dan wachten op de drie locks met `flock <lock> true`, opnieuw meten; blijft het geheugen te laag (0.3 regel 2: "available" onder 3000 MB, of onder 6000 MB met swap meer dan 90 % gebruikt): melden onder blokkades); draaien onder de lock en met de begrenzing uit het P-<repo>-blok (bijvoorbeeld `taskset -c 0-3` bij jelly-leon-web). Niet de begrenzing uit het script halen |
| "No space left on device" | `df -h /` en `df -h /tmp` | Alleen eigen, bij naam genoemde images, containers en uitvoermappen verwijderen. Geen van de drie verboden prune-commando's uit 0.3 regel 4. Lukt het niet: melden |
| Poort bezet | `ss -ltnp` | Draaien onder de lock (`stack.lock`) en wachten; geen proces van een ander stoppen. Voor media-source-optimizer: zie "Stackpoorten" in de Valkuilen van P-media-source-optimizer |
| Het commando wacht lang op `flock` | `ls -l <WERKMAP>/.lokaal/*.lock` | Wachten. Een lock nooit weghalen of omzeilen. Wacht je langer dan het P-<repo>-blok aannemelijk maakt: melden |
| Netwerk, registry of pakketbron onbereikbaar | Hetzelfde commando één keer opnieuw na een korte wachttijd | Blijft het rood: melden. Geen andere bron, spiegel of versie kiezen |
| Back-up- of hersteltest faalt op een versieverschil | `which pg_dump pg_restore` | `PATH=/usr/lib/postgresql/16/bin:$PATH` (0.3 regel 6) |
| `EBADENGINE` bij `npm ci` | `node --version` | De Node-versie uit het P-<repo>-blok gebruiken. `engines` niet aanpassen |
| Playwright vindt geen browser | `ls ~/.cache/ms-playwright` | `npx playwright install chromium` (0.3 regel 9) |
| Een meting is "ongeldig" door machinebelasting (vergelijkingsharnas jelly-leon) | `uptime` | Wachten tot de andere ketens klaar zijn en opnieuw meten. `B03_LASTGRENS` niet verhogen |

Een omgevingsherstel gevolgd door opnieuw draaien mag hooguit twee keer. Is de poort daarna nog rood, dan is het
geen omgevingsfout meer: ga terug naar 3.3 en deel opnieuw in, of meld. Staat het verschijnsel niet in deze tabel en
niet in de Valkuilen van het P-<repo>-blok: melden, niet zelf iets installeren of aan het systeem veranderen.

**Tak D - Was al rood.** Vaststellen (alleen lezen):

```bash
gh run list -R lvos04/<repo> --branch ccr-c133d7a0-kuz1cv --limit 10 --json databaseId,workflowName,conclusion,headSha
git log --oneline -5 -- <pad van het falende bestand of de falende test>
```

Was de run van de commit vóór de jouwe al rood, of is het falende bestand het laatst gewijzigd door een commit die
niet van deze stap is, dan herstelt A-BOUW dit NIET stil in zijn eigen stap. Meld het met het run-ID en de commit
van herkomst. De regisseur beslist wie het herstelt (het kan werk van een andere keten zijn). Jouw stap is intussen
niet klaar: zonder groene CI op jouw commit geldt 0.1.

**Tak E - Alleen in de CI rood.** Lees eerst `gh run view <run-id> -R lvos04/<repo> --log-failed`. Vaste oorzaken:

- De CI gebruikt een gepinde commit van een andere repo en lokaal draai je tegen de map ernaast (Valkuilen van
  P-ai-server-manager, P-home-control-hub, P-jelly-leon-platform, P-zoeken-en-persoonlijke-ai, P-jelly-leon). De pin
  verzetten is tak H.
- De CI zet variabelen waardoor een test die lokaal wordt overgeslagen daar wel draait (Valkuilen van
  P-home-control-hub en P-zoeken-en-persoonlijke-ai; contractkopie in P-jelly-leon-clients). Draai de test lokaal
  met `-rs`, lees de reden van het overslaan en zet de variabele zoals het P-<repo>-blok beschrijft.
- Een verschil in hulpprogramma of lettertype tussen deze machine en de CI (Valkuilen van P-my_house). Herstel de
  oorzaak in de code of het script; een schermtest wordt niet verruimd.
- De runner zelf faalde (afgebroken, geen schijfruimte, netwerk), zonder een foutregel uit de eigen code of tests.
  Dan één keer: `gh run rerun <run-id> -R lvos04/<repo> --failed`, daarna `gh run watch <run-id> -R lvos04/<repo> --exit-status`. Een tweede keer
  opnieuw starten zonder wijziging is niet toegestaan: melden.

Elke wijziging om de CI groen te krijgen is een herstelpoging en telt mee (3.5). Een workflowbestand wijzig je
alleen als de stap dat voorschrijft; dan geldt de regel uit 0.4 (`actionlint`).

**Tak B - Eigen wijziging.** Dit is de gewone herstelweg: 3.5.

**Tak C - De test klopt niet meer.** Een test wijzigen mag alleen als ALLE vier de punten waar zijn:

- [ ] 1. De opdracht van de stap schrijft het nieuwe gedrag letterlijk voor (verwijs naar de zin in de stap).
- [ ] 2. De test legt het oude gedrag vast en niets anders; de wijziging in de test is even streng of strenger.
- [ ] 3. De test is geen weigertest uit P-VEILIG, geen proef uit P-HARDE-EIS, geen contract-, drift- of
      EVIDENCE-test en geen test met een vaste ondergrens (zoals `E2E_MIN_TESTS`).
- [ ] 4. De wijziging staat in het rapport onder "Afwijking", met de naam van de test en de reden.

Is één punt niet waar: tak H (stoppen en melden). Een test verwijderen is nooit herstel.

### 3.5 Herstelpogingen: maximaal twee

Een herstelpoging is: één wijziging aan code, een test of een instelling, gevolgd door het opnieuw draaien van de
poort. De telling geldt per subagent-opdracht (A-BOUW binnen zijn eigen stap, of één opdracht aan A-HERSTEL), ongeacht
welke poort rood is: maakt een herstelpoging een andere poort rood, dan valt het herstel daarvan binnen dezelfde twee
pogingen. Een subagent stopt en meldt (3.6) uiterlijk na zijn tweede mislukte poging.

Wat de regisseur daarna doet staat in `AGENTEN.md`, kop "7.5 Escalatieladder bij vastlopen": een nieuwe opdracht aan
A-HERSTEL (poging 1 op het niveau van de stap, poging 2 één niveau hoger, poging 3 eenmalig op N5, genoteerd in
VOORTGANG.md, tabel "Topmodel-inzet"), en pas daarna het keuzemenu aan de gebruiker. Die ladder geldt ALLEEN voor de
takken A, B, C en E. Tak F, G en H krijgen nooit een herstelpoging en ook geen escalatie (3.8).

Per poging, in deze volgorde:

- [ ] 1. Schrijf de oorzaak op in één of twee zinnen, met het bestand en de regel uit de foutmelding.
- [ ] 2. Maak de kleinste wijziging die de oorzaak wegneemt. Geen opruimwerk, geen extra verbeteringen.
- [ ] 3. Draai eerst het commando dat faalde. Groen? Draai dan de volledige variant van P-<repo> voor het geraakte
      deel, en elke algemene poort die volgens 0.4 bij de wijziging hoort.
- [ ] 4. P-GIT (commit met een Nederlands bericht dat het herstel noemt, pull --rebase, scan, push) en de CI-controle
      van 0.5. Een poging is pas geslaagd bij groene CI op de nieuwe commit.
- [ ] 5. Noteer de poging voor het rapport: nummer, oorzaak, gewijzigde bestanden, commit, uitkomst.

Een commando opnieuw draaien ZONDER wijziging mag één keer, alleen om een omgevingsoorzaak uit te sluiten. Slaagt
het de tweede keer zonder wijziging, dan is de test wisselvallig: de poort telt als groen voor deze stap, en de
wisselvallige test wordt in het rapport gemeld onder "Afwijking" met naam en beide uitkomsten. Een wisselvallige
test wordt niet uitgezet en niet van een herhaalinstelling voorzien. Dit geldt NIET voor proeven uit P-HARDE-EIS
en weigertests uit P-VEILIG: daar is één rode uitkomst al tak F of G.

Na de tweede mislukte poging: stoppen en melden (3.6). Een derde poging met dezelfde aanpak is verboden, ook als het
"bijna werkt".

### 3.6 Stoppen en melden

Wie stopt, levert precies dit blok aan de regisseur (aanvulling op de rapportvorm van 0.6):

```
POORT GEFAALD - GESTOPT
Stap:        <stap-ID uit het plan>
Repo:        <repo>, commit <korte sha> (gepusht: ja | nee)
Poort:       P-<naam> (snel | volledig), stap of punt <nr>
Commando:    <letterlijk commando, met werkmap>
Uitkomst:    exitcode <n>; <aantal> mislukt; eerste foutregel letterlijk
CI:          run <run-id> (<workflownaam>): <uitkomst>, of "niet gepusht"
Tak:         <A | B | C | D | E | F | G | H> - <naam van de tak>
Oorzaak:     <één of twee zinnen>, of "niet gevonden" met wat is uitgesloten
Pogingen:    <0 | 1 | 2>; per poging: oorzaak, gewijzigde bestanden, commit, uitkomst
Stand repo:  git status --short: <leeg | lijst>; niet-gepushte commits: <aantal en korte sha's>
Achtergelaten: <containers, databases, mappen van proeven die nog bestaan>, of "niets"
Niet gedaan: <wat uit de stap nog open staat>
Nodig:       <besluit, omgeving of informatie; bij een keuze: de opties, elk met het gevolg>
EVIDENCE:    <ID>: <status> - <validatie> (in het bestand bijgewerkt: ja | nee)
```

Regels bij het melden:

- De status in EVIDENCE.json is op dat moment `Bezig` of `Geblokkeerd` (met `NIET GEVALIDEERD` en wat er nodig is),
  nooit iets gunstigers (P-EERLIJK).
- In de melding staat geen geheim, geen adres van een echt apparaat en geen gegeven van een echte gebruiker.
- Na de melding doet de subagent niets meer aan de stap. Hij start geen ander werk in dezelfde repo.

### 3.7 Wat nooit mag om een poort groen te krijgen

Deze lijst geldt voor elke agent en elke tak. Ziet een reviewer een van deze handelingen in een commit, dan is de
stap rood, ook als alle poorten groen zijn.

Tests en metingen:

- een test verwijderen, uitzetten, overslaan of als "verwacht falend" markeren; een test uit de verzameling halen
  met een filter of een padwijziging;
- een bewering in een test afzwakken, een vergelijkingsveld weghalen, een fixture kleiner of leger maken;
- een drempel of ondergrens verlagen of een grens verruimen: `E2E_MIN_TESTS` (media-source-optimizer),
  `B03_LASTGRENS` (jelly-leon), en elke andere grens in een test, Makefile of workflow;
- referentiebeelden of schermafdrukken opnieuw opnemen om een schermtest groen te krijgen
  (`:app:recordPaparazziDebug`, `make schermafdrukken`, `make statuspagina-shots`, `make ui-echt`); dat mag alleen
  in een ontwerpstap volgens P-PEIL;
- een negatieve proef zo wijzigen dat hij niet meer faalt, of de verwachte uitkomst omdraaien
  (`--negatief-verwacht`);
- een herhaalinstelling of langere wachttijd toevoegen om een wisselvallige test te verbergen.

Regels en bronnen:

- een contractkopie, Peil-kopie of token met de hand wijzigen om een drifttest groen te krijgen;
- een pin verzetten of terugzetten zonder melding (`ASF_COMMIT`, `VALIDATOR_COMMIT`, `ASM_COMMIT`,
  `APPSTORE_COMMIT`, `web_fork_commit`, de vorige release in `deploy/upgradebewijs/vorige-release.json`);
- een waarschuwing van de manifestvalidator wegnemen via `accepted_findings` buiten de codes die het contract
  daarvoor noemt, of `--strict` weglaten;
- een policybestand, risicoklasse of weigerregel versoepelen (P-VEILIG);
- `engines` in `package.json`, een toolchainversie of een begrenzing in een hulpscript aanpassen om een
  omgevingsfout te omzeilen.

Git en CI:

- `git commit --no-verify`, `git push --force` of `--force-with-lease`, historie herschrijven;
- een workflow, job of stap uitzetten, voorwaardelijk maken of op "mag falen" zetten; een padfilter verruimen
  zodat een workflow niet meer start;
- een `.gitleaks.toml` of `.gitleaksignore` toevoegen (P-GIT);
- een rode CI-run "bekend probleem" noemen zonder oorzaak in het rapport, of de stap klaar melden bij een rode of
  ontbrekende run.

Eerlijkheid:

- een status gunstiger schrijven dan gemeten; `Gereed` of `Geslaagd` gebruiken; een simulatorproef een validatie op
  de echte NAS noemen (P-EERLIJK);
- een poort als gedraaid melden zonder letterlijk commando en exitcode (0.6);
- overgeslagen tests weglaten uit het rapport.

Machine:

- `docker system prune -a`, `docker builder prune -a` of `docker volume prune` terwijl er iets bouwt; `make opruimen`
  in jelly-leon-clients of `make clean` in ai-server-manager (beide `docker image prune -f`);
- een lock weghalen of een zwaar commando zonder de lock starten;
- een proces, container of database van een andere agent stoppen of verwijderen;
- de map `ai-factory` aanraken.

### 3.8 Wat de regisseur met een melding doet

- [ ] 1. Lees het blok van 3.6 volledig. Ontbreekt het commando, de exitcode of de tak: stuur de melding terug.
- [ ] 2. Laat R-EERLIJK de stand herhalen (`git status`, `git log origin/ccr-c133d7a0-kuz1cv..HEAD`, de CI-run) als
      de melding zegt dat er iets gepusht is of dat er lokaal werk staat.
- [ ] 3. Kies precies één vervolg:
      - tak A, B, C of E: A-HERSTEL met een opdracht die de melding letterlijk bevat, op het niveau uit de
        escalatieladder (`AGENTEN.md`, kop "7.5 Escalatieladder bij vastlopen");
      - tak D: de keten die de fout veroorzaakte herstelt hem; de gemelde stap wacht;
      - tak F: R-HARDE-EIS, daarna de gebruiker (keuzemenu). Geen bouwwerk in die repo tot er een besluit is;
      - tak G: R-VEILIG, daarna de gebruiker als er een geheim gelekt kan zijn of een regel moet wijken;
      - tak H: de gebruiker (keuzemenu) met de opties uit "Nodig", of de status `Geblokkeerd` met
        `NIET GEVALIDEERD` als het om de echte NAS, hardware of een account gaat;
      - de subagent heeft zijn twee pogingen gebruikt en het is nog rood (tak A, B, C of E): volg de escalatieladder
        in `AGENTEN.md`, kop "7.5 Escalatieladder bij vastlopen" (nieuwe A-HERSTEL, één niveau hoger; daarna
        eenmalig N5); is de ladder op, dan het keuzemenu aan de gebruiker met de opties uit die kop. Nooit een derde
        poging door dezelfde subagent met dezelfde aanpak.
- [ ] 4. Start geen andere schrijvende agent in dezelfde repo zolang er niet-gepusht werk van de gestopte stap staat.
      Ketens in andere repos lopen door, tenzij ze afhangen van de gestopte stap.
- [ ] 5. Leg het besluit vast op de plek die het hoofdplan daarvoor aanwijst, met het stap-ID en de tak.

---

## 4. Open punten (ONBEKEND) en bronnen

### 4.1 Wat niet vast te stellen was

Elk punt hieronder staat ook op de plek in dit bestand waar het speelt. De regel "tot dan geldt" is bindend: een
agent die het punt tegenkomt, stelt het eerst vast met het genoemde commando (alleen lezen) en meldt de uitkomst in
zijn rapport onder "Afwijking". Hij vult het antwoord niet zelf in.

| Nr | Waar | Wat niet vaststaat | Eerst vaststellen met | Tot dan geldt |
|---|---|---|---|---|
| O-1 | P-jelly-leon, Valkuilen | Hoe `libfontconfig1` in de SDK-container komt voor de volledige upstream-testsuite | `grep -rn 'fontconfig' <WERKMAP>/.lokaal --include='*.sh'` | De CI-job `server` is het bewijs voor de volledige suite; lokale omgevingsfouten worden met naam en aantal gemeld |
| O-2 | P-my_house, Volledig stap 9 | Of `<WERKMAP>/.lokaal/my_house-ci/stack-job.sh` nog past bij de huidige `ci.yml` | `sed -n '/^  stack:/,$p' .github/workflows/ci.yml` naast `cat <WERKMAP>/.lokaal/my_house-ci/stack-job.sh` | De CI-job `stack` is het bewijs; het script gebruikt `sudo` en hoort niet bij de poort van A-BOUW |
| O-3 | P-jelly-leon-web, Volledig stap 3 | De koppelingen (`-v`) van de build in de Node 24-container | `ls <WERKMAP>/.lokaal/jelly-leon-web/logs` | De build zonder container (met `taskset -c 0-3`) is de lokale poort; de CI-job `build` is de herhaling in de vaste image |
| O-4 | P-jelly-leon, Volledig stap 7 | Het exacte lokale commando voor de stock-client-smoketest (server publiceren, starten als 568, `tools/jelly-leon/e2e/stock_client_smoke.py`) | `sed -n '/^  stock-client-e2e:/,/^  emby-overname:/p' .github/workflows/jelly-leon-ci.yml` | De CI-job `stock-client-e2e` is het bewijs |
| O-5 | P-jelly-leon, Volledig stap 5 | Of de kloon van jelly-leon-web op de commit uit `web_fork_commit` staat (nodig voor `web_bron.py --controleer`) | `python3 tools/jelly-leon/web_bron.py --commit` naast `git -C <WERKMAP>/jelly-leon-web rev-parse HEAD` | Bij verschil: niet van commit wisselen in de kloon; de CI-job `image` is het bewijs voor deze controle |
| O-6 | P-jelly-leon-clients, Volledig stap 5 | De volledige lokale herhaling van `tools/clients/server_api_compat.py` (vraagt vier upstream-bronnen die de CI zelf ophaalt) | `grep -n 'server_api_compat' -B3 -A12 .github/workflows/clients-compat.yml` | De CI-run van `clients-compat.yml` is het bewijs; met de hand starten als hij niet vanzelf startte |
| O-7 | P-VEILIG, punt 10 | Welke tests per dienst het opnieuw controleren van het ondertekende verzoek bij `POST /connector/v1/apply` dekken | `grep -rIlE 'ExecutionRequest|execution_request' apps/api/tests` in de werkmap van de dienst | Geen test gevonden: de stap die de route raakt voegt hem toe, of stopt en meldt |
| O-8 | P-VEILIG | Of de voorstel- en goedkeuringsroutes van de Hub-API (`apps/api/src/hub/actions`, half werk uit ronde 3) en hun tests al gecommit zijn | `git ls-files apps/api/src/hub/actions apps/api/tests/integration/test_acties.py tests/e2e/test_acties.py` in `<WERKMAP>/ai-server-manager` | Niet gecommit: eerst de stap "half werk afmaken" (STAND_RONDE3.md); daarna horen die tests bij P-VEILIG |
| O-9 | P-HARDE-EIS | Of jelly-leon-platform en jelly-leon-clients eigen proeven hebben die kijkgegevens bewaken | `grep -rIlE 'kijkgeschiedenis|hervat|favoriet|UserData' --exclude-dir=node_modules --exclude-dir=.venv apps tests tools` in de werkmap van de repo | Raakt een stap in zo'n repo een pad dat kijkgegevens kan wijzigen en is er geen proef: stop en meld |
| O-10 | P-home-control-hub, P-zoeken-en-persoonlijke-ai, P-jelly-leon-clients (kop 5 en Valkuilen) | Of een drifttest lokaal de bron echt heeft vergeleken of dat deel heeft overgeslagen | De test draaien met `-rs` en de overgeslagen regels lezen | Een overgeslagen bronvergelijking staat in het rapport; de CI-run is dan het bewijs voor de vergelijking |

### 4.2 Bekende gaten (vastgesteld, nog niet gebouwd)

Dit zijn geen onzekerheden maar open werk. Een poort die erop stuit, meldt het gat en doet niet alsof het dicht is.

| Gat | Vastgesteld in | Gevolg voor de poort |
|---|---|---|
| EX12 (back-upgate: geen mutatie bij verouderde back-up) heeft nog geen test | P-VEILIG, tabel; `<WERKMAP>/.lokaal/plan/bron/STAND_PER_ID.tsv` | De stap die de back-upgate bouwt voegt de test toe; tot dan is dit punt van P-VEILIG niet groen |
| media-guard-ultimate, media-source-optimizer en my_house hebben geen manifest en geen `deploy/truenas/CUSTOM_APP.md`; my_house heeft nog geen alles-in-één image en installeert nu met een compose-YAML | P-INSTALLATIE, open punt; `CONTRACT_1.3_CONFORMITEIT.md`, koppen 6, 7 en 8; `<WERKMAP>/my_house/docs/adr/ADR-0004-alles-in-een-custom-app.md`, kop "Context" | P-INSTALLATIE punten 2 tot en met 9 kunnen voor deze repos niet groen zijn tot die stappen gebouwd zijn |
| Voor de privacycontrole (adressen, namen, paden, modelnamen) bestaat geen vast commando; alleen jelly-leon-platform test een deel (`tests/repo/test_repo_rules.py`) | P-GIT, punt 5 | Nalezen van `git diff --cached` blijft handwerk en is verplicht |
| Swiftfin (iOS en tvOS) bouwt alleen op een macOS-runner | P-jelly-leon-clients, Volledig stap 6 | Alleen de CI-run telt; zonder groene run: `Geblokkeerd`, `NIET GEVALIDEERD (Mac/Xcode)` |
| De C1.3-ID's (zoals C1.3-MGU-03, C1.3-MH-03, C1.3-MH-06) staan niet in `<WERKMAP>/.lokaal/plan/bron/ALLE_IDS.txt` | `CONTRACT_1.3_CONFORMITEIT.md` | Het zijn contract-ID's; de Excel toont ze in een eigen overzicht (`contractpunten_en_reviews`), niet als rij in Werkpakketten |

### 4.3 Bronnen

Alle paden zijn relatief aan `<WERKMAP>`. Koppen staan tussen aanhalingstekens.

Contract, besluiten en fasering (ai-server-manager):

- `ai-server-manager/docs/platform-v2/PLATFORM_CONTRACTEN.md` - "1. Vaste keuzes (van de gebruiker)",
  "2.2 Custom App-realiteit (gemeten in de bronnen, niet op een echte NAS)",
  "2.3 Bestaande apps (MediaGuard, MSO, my_house, Jellyfin/Jelly Leon, Emby)", "3. Geheimen en koppelen",
  "4. Authenticatie en rollen", "5. Gemeenschappelijke API-regels",
  "6. Connectorcontract (elke dienst én elke adapter voor bestaande apps)", "7. Event-envelope",
  "8. Risicobeleid, voorstel, goedkeuring en executor", "9. Manifeststandaard (B08-001, eigenaar `appstore-en-fork`)",
  "11. Bewijs en Excel (EVIDENCE.json)", "12. Commit- en pushregels", "13. Ontwerptaal".
- `ai-server-manager/docs/platform-v2/CONTRACT_1.3_CONFORMITEIT.md` - "0. Voor alle repos (ALG)" en de kop per repo
  ("1. ai-server-manager (Hub + executor; contracteigenaar)" tot en met "11. jelly-leon-clients").
- `ai-server-manager/docs/platform-v2/01_ARCHITECTUUR/06_FASERING_EN_GATES.md` - "Gate matrix".
- `ai-server-manager/docs/adr/` - ADR-0015, ADR-0020, ADR-0024, ADR-0025, ADR-0027, ADR-0028, ADR-0029, ADR-0030.
- `ai-server-manager/policy/README.md` - het hele bestand (de lijst onder "Regels:").
- `ai-server-manager/docs/platform-v2/ONTWERPTAAL.md` - "4. Kleursemantiek", "11. Nederlandse microcopy",
  "12. Toegankelijkheid en tests", "13. Per oppervlak", "14. Verspreiding, versies en drift".
- `ai-server-manager/design/ontwerptaal/` - de Peil-bron (tokens, stijlbladen, componenten, controles).
- `ai-server-manager/tools/excel/README.md` - "Excel-bijwerker"; `ai-server-manager/tools/excel/update_excel.py`.

Poorten per repo (de CI-bestanden zijn de waarheid; daarnaast de Makefile of `package.json` van de repo):

- `ai-server-manager/.github/workflows/ci.yml`, `ai-server-manager/Makefile`.
- `home-control-hub/.github/workflows/ci.yml`, `home-control-hub/Makefile`.
- `appstore-en-fork/.github/workflows/ci.yml`, `appstore-en-fork/Makefile`,
  `appstore-en-fork/docs/MANIFESTSTANDAARD.md` - "Valideren", "Weigerregels in detail (aangescherpt na de review
  van fase P0, ADR-0007)", "Alle meldingscodes".
- `jelly-leon-platform/.github/workflows/ci.yml`, `jelly-leon-platform/Makefile`.
- `zoeken-en-persoonlijke-ai/.github/workflows/ci.yml`, `zoeken-en-persoonlijke-ai/Makefile`.
- `media-guard-ultimate/.github/workflows/ci.yml`, `media-guard-ultimate/.github/workflows/android.yml`.
- `media-source-optimizer/.github/workflows/ci.yaml`, `media-source-optimizer/Makefile`.
- `my_house/.github/workflows/ci.yml`, `my_house/.github/workflows/android.yml`,
  `my_house/.github/workflows/audit.yml`, `my_house/.github/workflows/edge.yml`.
- `jelly-leon/.github/workflows/jelly-leon-ci.yml`; `jelly-leon/docs/platform-v2/OVERNAME_EMBY.md` - "Wat er
  overgaat — en wat niet", "Stappen", "Controlelijst "Emby verwijderen" (u voert dit zelf uit — geen enkele agent
  verwijdert Emby)"; `jelly-leon/docs/platform-v2/B03-016_HARNAS.md` - "3. Harnas, meetprotocol en baselines
  (deel c)", "4. Wat hier NIET gevalideerd kan worden".
- `jelly-leon-web/.github/workflows/jelly-leon-web-ci.yml`.
- `jelly-leon-clients/.github/workflows/clients-forkregels.yml`, `clients-android.yml`, `clients-androidtv.yml`,
  `clients-desktop.yml`, `clients-swiftfin.yml`, `clients-compat.yml` in dezelfde map; `jelly-leon-clients/Makefile`.

Ontwerpreview per Peil-repo: `docs/ontwerp/PEIL_REVIEW.md` in de repo; de kop met de commando's om de review te
herhalen staat per repo in de tabel van P-PEIL.

Lokale hulpbestanden (niet in git):

- `.lokaal/plan/bron/ALLE_IDS.txt` en `.lokaal/plan/bron/STAND_PER_ID.tsv` - alle ID's en hun stand.
- `.lokaal/plan/bron/RESULTATEN_ALLE_AGENTS.jsonl` - vastgelegde testruns van eerdere rondes (herkomst van de
  richtgetallen).
- `.lokaal/scan/OPENBAARHEIDSSCAN.md` - "1.1 Gitleaks (volledige historie)", "1.2 Privacyscan (wat gitleaks mist)".
  Neem uit dit bestand geen gevonden waarden over in een rapport of commit.
- `.lokaal/docker-build.lock`, `.lokaal/gradle.lock`, `.lokaal/stack.lock` - de machinebrede locks.
- `.lokaal/excel-venv` - de venv voor P-EXCEL.
