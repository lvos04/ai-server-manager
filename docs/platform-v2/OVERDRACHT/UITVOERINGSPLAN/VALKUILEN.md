# VALKUILEN — lessen uit het eerdere werk

Dit bestand hoort bij het uitvoeringsplan voor P2 tot en met P6. Het bevat alleen gevallen die in het eerdere werk echt zijn voorgekomen. Het is bedoeld voor de regisseur en voor alle subagents (A-VERKEN, A-ONTWERP, A-BOUW, A-HERSTEL, R-TECH, R-VEILIG, R-HARDE-EIS, R-MANIFEST, R-EERLIJK, R-ONTWERP, A-GATE).

## Hoe je dit bestand gebruikt

1. Zoek je repo op in de tabel onderaan ("Per repo: lees deze valkuilen voor je begint") en lees die valkuilen vóór je iets bouwt of beoordeelt.
2. Lees daarnaast altijd de groepen "Algemeen en werkwijze", "Git en CI" en "Eerlijkheid en bewijs".
3. Een reviewer gebruikt de regel "Hoe herken je het" als controlevraag.

De meeste gevallen hieronder zijn in de betreffende repo al gerepareerd. Ze staan hier omdat dezelfde fout in nieuw werk opnieuw kan ontstaan. Een valkuil is dus geen open taak, tenzij dat er uitdrukkelijk bij staat. De stand van de repos verandert nog; controleer de echte stand altijd zelf in git (zie STATUS.md, eerste regel onder de titel).

## Bronnen

| Afkorting | Bron | Verwijzing |
|---|---|---|
| R | `<WERKMAP>/.lokaal/plan/bron/RESULTATEN_ALLE_AGENTS.jsonl` | veld `agent`, waar nodig met veld `fase` |
| V | `<WERKMAP>/.lokaal/plan/bron/VERVOLGPUNTEN_RUW.md` | kop `## <repo>`, daaronder `### <agent>` |
| S | `<WERKMAP>/ai-server-manager/docs/platform-v2/OVERDRACHT/STATUS.md` | kop |
| O | `<WERKMAP>/.lokaal/workflows/ronde-3.js` | tekstblokken "OMGEVING" en "HERVATTING" |
| C | `<WERKMAP>/ai-server-manager/docs/platform-v2/PLATFORM_CONTRACTEN.md` | paragraafnummer of kop |

De agentnaam `review:hch` komt twee keer voor in R: één keer in de eerste Hub-ronde (P1) en één keer na contract 1.2. Waar het uitmaakt staat dat erbij. Hetzelfde geldt voor `controle` en `synthese`.

Nummers van bevindingen die een reviewer zelf heeft uitgedeeld, zijn hier niet overgenomen: ze staan niet in `<WERKMAP>/.lokaal/plan/uit/ALLE_IDS.txt`. Wel gebruikt zijn werkpakket- en test-ID's uit dat bestand, contractparagrafen, correctienummers uit het contract (RV1 tot en met RV13, R4 tot en met R12), conformiteitsregels (C1.3-...) en ADR's met reponaam.

## Vast sjabloon per valkuil

- **Wat ging er mis:** het concrete geval, met repo en bron.
- **Hoe herken je het:** het signaal waaraan je de fout ziet, of de controle waarmee je hem vindt.
- **Wat doe je in plaats daarvan:** de werkwijze die de fout voorkomt.

---

## 1. Algemeen en werkwijze

### V-001 — De simulator accepteert wat de echte Hub weigert
- **Wat ging er mis:** In home-control-hub hadden drie eventtypen vier segmenten in de naam. De eigen simulator nam ze aan; de echte Hub eist precies drie segmenten en verbiedt extra velden (C §7). Bij contract 1.2 bleek ook dat diensten een enroll-verzoek met extra velden stuurden; de echte Hub weigert dat en het eenmalige token is dan verbruikt. (Bron: R `review:hch` eerste Hub-ronde; R `contract-1.2`.)
- **Hoe herken je het:** Alle tests zijn groen, maar er is geen test die tegen de code van de echte Hub draait. De simulator heeft geen schemavalidatie of staat onbekende velden toe.
- **Wat doe je in plaats daarvan:** Maak de simulator even streng als de echte Hub en voeg een interop-test toe tegen de echte Hub-code. Voorbeeld: `<WERKMAP>/zoeken-en-persoonlijke-ai/tests/interop/test_real_hub.py` en het Makefile-doel `interop` in zoeken-en-persoonlijke-ai en home-control-hub. Bij het schrijven van dit bestand kwam `interop` in de CI-workflows van beide repos alleen voor in de lintstap; er is geen stap gezien die het Makefile-doel `interop` aanroept. Of de interop-test in CI echt draait is daarmee ONBEKEND - eerst vaststellen met: `grep -rn "interop" <WERKMAP>/zoeken-en-persoonlijke-ai/.github/workflows <WERKMAP>/home-control-hub/.github/workflows` en de uitvoer van de laatste CI-run (zie V-004).

### V-002 — De simulator wijkt af van de echte upstream-app
- **Wat ging er mis:** In jelly-leon-platform zijn de adapters voor Uptime Kuma, Beszel en Gotify uit de broncode van die apps afgeleid en alleen tegen eigen simulators getest. Bij review bleek dat de upstream-images nooit echt gestart waren. (Bron: R `plat:manifests-sims`, R `hub:catalogus-monitoring`, R `review:plat`.)
- **Hoe herken je het:** In het bewijs staat alleen "Sim-getest" en er is geen stap die de echte upstream-image start.
- **Wat doe je in plaats daarvan:** Start de echte image minstens één keer in een rooktest. Voorbeeld: `<WERKMAP>/jelly-leon-platform/tools/upstream_rooktest.py` (Makefile-doel `upstream-rooktest`). Houd controles die op echt gedrag berusten in stand; Gotify heeft na een verse installatie echt het standaardwachtwoord, dus de controle na installatie blijft nodig.

### V-003 — Een test die niet kan falen
- **Wat ging er mis:** Meerdere repos hadden tests die altijd slaagden. my_house: een offline-controle slaagde ook zonder worker, omdat er dan nergens "Gezond" stond. jelly-leon-platform: een regressietest gebruikte een ongeldige koppelcode en bereikte de bedoelde code nooit. media-guard-ultimate: een e2e-test sloeg zichzelf over als er niets open stond; het upgradebewijs meldde "niets verloren" terwijl er niets gemeten was. jelly-leon-clients: de vergelijking voor JLT-60 kon twee lege opnamen als gelijk tellen. (Bron: R `review:mh`, R `review-1.2:jelly-leon-platform`, R `review:mg`, R `review-1.3:media-guard-ultimate`, R `review:jelly-leon-clients`.)
- **Hoe herken je het:** De test blijft groen als je de reparatie tijdelijk terugdraait. De test heeft een vroege uitgang ("niets te doen") of vergelijkt twee lege verzamelingen.
- **Wat doe je in plaats daarvan:** Doe bij elke nieuwe test een mutatieproef: draai de reparatie tijdelijk terug (alleen in de werkmap, niet committen) en laat zien dat de test dan rood wordt. De reviewers van contract 1.3 deden dit standaard. Zet ondergrenzen op aantallen (rijen, opnamen, metingen) zodat "leeg" rood is.

### V-004 — Overgeslagen tests tellen als groen
- **Wat ging er mis:** home-control-hub: CI sloeg 12 tests stil over (708 uitgevoerd), waaronder de manifestvalidator en de byte-vergelijking met de Peil-referentie; twee beweringen van de bouwer waren daardoor niet door CI gedekt. media-source-optimizer: van 78 e2e-tests werden er 76 overgeslagen omdat `MSO_E2E_USER` en het bijbehorende wachtwoord niet gezet waren. appstore-en-fork: de autorisatietest sloeg 11 routes over (EX16). (Bron: R `review-1.3:home-control-hub`, R `controle:mso`, R `review-1.3:appstore-en-fork`.)
- **Hoe herken je het:** In de testuitvoer staat "skipped" of "overgeslagen" en niemand heeft de reden gelezen. Een test leest zijn invoer uit een omgevingsvariabele of een pad dat in CI ontbreekt.
- **Wat doe je in plaats daarvan:** Laat CI falen als een verplichte invoer ontbreekt, in plaats van over te slaan. Meld het aantal overgeslagen tests altijd met reden. Laat een autorisatietest de routes uit de echte app lezen, niet uit een eigen lijst. media-source-optimizer heeft sindsdien een ondergrens in het Makefile-doel `e2e`.

### V-005 — Een meting over lege invoer telt als schoon
- **Wat ging er mis:** home-control-hub: de ontwerpreview in CI las door een relatief uitvoerpad een lege map en meldde "0 metingen, 0 overtredingen". media-source-optimizer: de eerste meetronde gaf 0 van 128 afdrukken door een ontbrekende basis-URL in het script. (Bron: R `review:hch` na contract 1.2; R `ontwerp:mso`.)
- **Hoe herken je het:** Het meetrapport noemt nul metingen of veel minder dan de matrix voorschrijft, en eindigt toch zonder fout.
- **Wat doe je in plaats daarvan:** "0 metingen" is een fout. Leg per meetscript het verwachte aantal vast (toestanden x breedtes x thema's) en laat het script falen als het aantal lager is.

### V-006 — Een groene nulmeting van de bouwer is geen bewijs dat het goed is
- **Wat ging er mis:** Na de bouw van contract 1.3 meldden alle bouwers groene tests. De onafhankelijke reviewers vonden daarna in elke repo echte fouten, onder meer genegeerde Retry-After, een kale 500, een veld buiten de witte lijst en stil overgeslagen tests. (Bron: R, alle agents `review-1.3:<repo>`.)
- **Hoe herken je het:** Het rapport van de bouwer bevat alleen aantallen geslaagde tests en geen tegenproef.
- **Wat doe je in plaats daarvan:** Sla de onafhankelijke review nooit over omdat de bouwer groen meldt. De reviewer probeert de contractregels zelf te breken (te grote body, dubbele aanvraag, verkeerde rechten, verlopen meting) en leest de CI-uitvoer zelf.

### V-007 — De test stuurt zelf headers mee die een browser anders stuurt
- **Wat ging er mis:** Het koppelformulier op de statuspagina (C §3.7) werkte in de tests, maar niet in een echte browser. Met `Referrer-Policy: no-referrer` stuurt de browser `Origin: null`, en de Origin-controle weigerde dat. Dit trof de executor-statuspagina in ai-server-manager en de statuspagina's van de diensten. In zoeken-en-persoonlijke-ai was het omgekeerde een gat; daar wordt nu elke `Sec-Fetch-Site` anders dan `same-origin` geweigerd. (Bron: R `1.2:jelly-leon-platform`, R `hub:ontwerpreview`, R `review:zoek`.)
- **Hoe herken je het:** Formuliertests zetten zelf een `Origin`-header. Er is geen test die het formulier in Chromium verstuurt.
- **Wat doe je in plaats daarvan:** Verstuur elk formulier minstens één keer met Playwright in een echte browser. Stem `Referrer-Policy` en de Origin-controle op elkaar af en test beide kanten: de echte browser komt erdoor, een vreemde herkomst niet.

### V-008 — Poorten botsen op de gedeelde machine
- **Wat ging er mis:** In ai-server-manager startten twee Playwright-runs niet omdat de webserver "adres in gebruik" meldde; een andere agent draaide op dat moment Playwright in media-guard-ultimate. (Bron: R `review-1.2:ai-server-manager`.)
- **Hoe herken je het:** `EADDRINUSE` of wisselende netwerkfouten in e2e-uitvoer, terwijl de code niet veranderd is.
- **Wat doe je in plaats daarvan:** Kies per agent eigen vrije poorten en geef ze expliciet mee. Gebruik geen standaardpoorten van de repo als er meer agents tegelijk werken.

### V-009 — De stack-lock is lang bezet
- **Wat ging er mis:** In jelly-leon-web kon de upgradeproef lokaal niet draaien omdat `<WERKMAP>/.lokaal/stack.lock` meer dan een uur bezet was door een andere bouwer; de proef is toen alleen op de GitHub-runner gedaan. In media-source-optimizer bestond een gemeten doorlooptijd voor ongeveer zes minuten uit wachten op die lock. (Bron: R `p4-0:web`, R `controle:mso`.)
- **Hoe herken je het:** Een commando met `flock` lijkt te hangen, of een tijdmeting is veel hoger dan de echte looptijd.
- **Wat doe je in plaats daarvan:** Houd de lock zo kort mogelijk vast en nooit rond een hele reviewronde. Meet tijden zonder de wachttijd op de lock. Meld in je rapport als een proef daardoor alleen in CI is gedraaid. Een maximale houdtijd is nergens vastgelegd. Lijkt een lock veel langer bezet dan de richtgetallen in POORTEN.md aannemelijk maken, meld dat dan aan de regisseur met de uitvoer van `ls -l <WERKMAP>/.lokaal/*.lock` en `ps -ef | grep '[f]lock'`. Een lock wordt nooit weggehaald (POORTEN.md, hoofdstuk 3, tak A).

### V-010 — Een commando draait in de verkeerde repo
- **Wat ging er mis:** Een agent die aan media-source-optimizer werkte, draaide per ongeluk `npm ci` in `ai-server-manager/apps/web`. De oorzaak was een `cd` die in een achtergrondsubshell terechtkwam. (Bron: R `web:mso`.)
- **Hoe herken je het:** `git status` in een andere repo toont onverwachte wijzigingen, of `node_modules` daar is opnieuw opgebouwd.
- **Wat doe je in plaats daarvan:** Gebruik absolute paden en opties als `--prefix` of `-C`. Zet geen `cd` in een samengesteld commando dat op de achtergrond draait. Controleer na afloop `git status` in je eigen repo en meld het als je buiten je repo iets hebt geraakt.

### V-011 — Opruimen van Docker breekt de build van een ander
- **Wat ging er mis:** Een `docker image prune` van één agent brak een gelijktijdige build van een andere agent. Dit is één keer gebeurd. (Bron: V `## jelly-leon-platform`, `### 1.2:jelly-leon-platform`.)
- **Hoe herken je het:** Een build faalt halverwege op een ontbrekende laag, terwijl de Dockerfile niet veranderd is.
- **Wat doe je in plaats daarvan:** Verwijder alleen je eigen images op naam (`docker rmi <naam>`). Breed opruimen is een stap van de regisseur, op een moment dat niets bouwt. De vaste regel van de gebruiker verbiedt `docker system prune -a`, `docker builder prune -a` en `docker volume prune` zolang er iets bouwt.

### V-012 — De schijf loopt vol
- **Wat ging er mis:** Tijdens het werk aan jelly-leon-clients stond de schijf op 97 procent; de gedeelde Docker-buildcache was 47,6 GB. De agent heeft alleen eigen images en werkmappen verwijderd, omdat opruimen van de gedeelde cache alle agents raakt. (Bron: V `## jelly-leon-clients`, `### p4-0:clients`.)
- **Hoe herken je het:** Builds of tests falen met "no space left on device", of databasetests die reserve eisen worden rood.
- **Wat doe je in plaats daarvan:** De regisseur controleert tussen rondes de ruimte. Bij het schrijven van dit bestand was 51 procent van de schijf in gebruik. De stand verandert met elke build; stel hem telkens opnieuw vast met `df -h /` en `docker system df`. Opruimen van de gedeelde cache gebeurt alleen door de regisseur en alleen als niets bouwt.

### V-013 — /tmp is werkgeheugen en wordt gedeeld
- **Wat ging er mis:** Op deze machine is `/tmp` een tmpfs en telt dus mee als RAM. Toen `/tmp` bijna vol stond door het werk van alle agents, werden tests rood die vrije ruimte eisen: zestien back-uptests van media-source-optimizer (de app weigert terecht een back-up zonder 2 GB reserve) en zes encodertests van media-guard-ultimate. (Bron: R `test:mh`, R `1.3:media-source-optimizer`, R `review-1.3:media-guard-ultimate`; V `## media-source-optimizer`.)
- **Hoe herken je het:** Tests falen op vrije ruimte of geheugen, alleen lokaal en alleen als er meer agents werken.
- **Wat doe je in plaats daarvan:** Zet `TMPDIR` en bij pytest `--basetemp` op een map op schijf onder `<WERKMAP>/.lokaal/`. Zet geen virtuele omgevingen of grote testdata in `/tmp`. In media-guard-ultimate staan daarvoor hulpmiddelen in `<WERKMAP>/media-guard-ultimate/services/encoder/tests/conftest.py`.

### V-014 — Een zware build wordt door de kernel gestopt
- **Wat ging er mis:** De productiebuild van jelly-leon-web werd bij de eerste poging zonder begrenzing door de kernel gestopt (exit 137, geheugen). Een emulator met een groot scherm kreeg binnen 4 GiB een OOM-kill. (Bron: R `p4-0:web`, R `golf0:corpus`.)
- **Hoe herken je het:** Exit 137, of "Killed" zonder foutmelding van het programma zelf.
- **Wat doe je in plaats daarvan:** Volg het OMGEVING-blok (O): per agent één zware build tegelijk, `nice -n 10`, begrensde werkers, en de locks `<WERKMAP>/.lokaal/docker-build.lock` en `<WERKMAP>/.lokaal/gradle.lock`. Gebruik voor de emulator een kleiner scherm. Leg bij een OOM beide pogingen vast in het bewijs (zie jelly-leon `docs/adr/ADR-0026-b03-016-harnas-corpus-clientmatrix-baseline.md`).

### V-015 — Een afgebroken ronde laat half werk achter
- **Wat ging er mis:** Een ronde brak af door de gebruikslimiet, niet door een inhoudelijke fout. In de repos kon daardoor half werk staan: niet-gecommitte of nieuwe bestanden en commits die nog niet gepusht waren. (Bron: O, blok "HERVATTING".)
- **Hoe herken je het:** Een subagent levert geen resultaat op, of `git status` toont bij de start al wijzigingen.
- **Wat doe je in plaats daarvan:** Begin elke taak met `git status` en een vergelijking van de lokale branch met de remote. Beoordeel gevonden half werk eerst (afmaken of terugdraaien) en bouw er niet blind op voort. De regisseur behandelt een leeg resultaat als "onbekende stand", niet als "niets gedaan".

### V-016 — Twee agents wijzigen hetzelfde bestand
- **Wat ging er mis:** Bij het verwerken van het B03-plan nam een andere verwerker de gepushte JSON-bestanden van een agent over in een gedeelde bronmap en maakte daar een lockbestand aan. Bij het samenvoegen van EVIDENCE.json veranderden 31 werkpakketrijen en 5 EX-rijen buiten de eigen opdracht. (Bron: R `int:asm`; R `controle`, de tweede rij (controle na het verwerken).)
- **Hoe herken je het:** De diff van je commit raakt rijen of bestanden die niet in je opdracht staan.
- **Wat doe je in plaats daarvan:** Eén eigenaar per gedeeld bestand per ronde. Doe `git pull --rebase` vóór je begint en vóór elke push. Lees de diff van EVIDENCE.json regel voor regel voordat je commit; een wijziging buiten je opdracht meld je, je voert hem niet stil door.

### V-017 — Wachten op werk dat in een andere repo nog niet gepusht is
- **Wat ging er mis:** De manifesten van home-control-hub, ai-server-manager, zoeken-en-persoonlijke-ai en my_house wachtten op de 1.3-validator van appstore-en-fork (C1.3-ASF-08). Die stond lokaal klaar maar was nog niet gepusht. Gevolg: open regels C1.3-HCH-13, C1.3-ASM-17, C1.3-ZPA-13 en C1.3-MH-06. (Bron: R `1.3:home-control-hub`, R `1.3:ai-server-manager`, R `1.3:zoeken-en-persoonlijke-ai`, R `1.3:my_house`.)
- **Hoe herken je het:** Een blokkade in EVIDENCE verwijst naar een andere repo. De genoemde commit staat niet op de remote.
- **Wat doe je in plaats daarvan:** De regisseur plant gedeelde bouwstenen (validator, contractkopie, Peil-sjabloon) vóór de afnemers en laat ze eerst pushen. Haal een blokkade uit EVIDENCE zodra de oorzaak weg is. Of de genoemde regels nu nog open staan is ONBEKEND - eerst vaststellen met: `grep -n "C1.3-ASF-08" <WERKMAP>/*/docs/platform-v2/EVIDENCE.json`.

### V-018 — De contractversie verandert tijdens een ronde
- **Wat ging er mis:** Elke repo heeft een byte-gelijke kopie van het contract met een drifttest. In media-guard-ultimate en my_house moest gekozen worden wat er gebeurt als de bron na het pinnen wijzigt: een fout alleen bij afwijking van de gepinde commit, een latere wijziging in de bron is een waarschuwing. Contract en Peil stellen hier niet dezelfde eis. (Bron: V `## media-guard-ultimate`, `### 1.3:media-guard-ultimate`; V `## my_house`, `### 1.3:my_house`.)
- **Hoe herken je het:** De drifttest wordt rood zonder dat de eigen repo veranderd is.
- **Wat doe je in plaats daarvan:** Pin kopieën op een bron-commit. Het overnemen van een nieuwe versie is een aparte stap van de regisseur voor alle repos tegelijk; een bouwer past de kopie nooit lokaal aan. Wijzigingsvoorstellen voor contract of Peil gaan naar ai-server-manager.

### V-019 — Een review vindt een fout buiten zijn mandaat en niemand pakt hem op
- **Wat ging er mis:** De ontwerpreview van de Hub vond een blokkerende functionele fout (koppelen via de executor-statuspagina mislukte in elke echte browser, zie V-007) en repareerde die niet, omdat het buiten het mandaat van een ontwerpreview viel. (Bron: R `hub:ontwerpreview`.)
- **Hoe herken je het:** In een reviewrapport staat "gevonden, niet gerepareerd" zonder vervolgstap.
- **Wat doe je in plaats daarvan:** De regisseur zet elke niet-gerepareerde bevinding direct door naar A-HERSTEL en sluit de stap pas als er een commit of een uitdrukkelijk besluit tegenover staat.

### V-020 — Iets proberen wat toestemming van de gebruiker vraagt
- **Wat ging er mis:** Het sync-token `JL_SYNC_PUSH_TOKEN` voor de forks staat open. Een fijnmazig token kan alleen via de webinterface van GitHub; het alternatief met deploysleutels vraagt uitdrukkelijke toestemming in de sessie. (Bron: S, kop "Besluiten van de gebruiker", besluit 4, en de lijst met open punten.)
- **Hoe herken je het:** Een stap vraagt om het aanmaken van sleutels, tokens of rechten op GitHub of op de NAS.
- **Wat doe je in plaats daarvan:** Niet proberen en niet omzeilen. Meld het als blokkade met wat de gebruiker moet doen, en ga door met werk dat er niet van afhangt.

### V-021 — De emulatortest kan niet door ontbrekende KVM-toegang
- **Wat ging er mis:** In een eerdere ronde had de gebruiker van de sessie geen toegang tot `/dev/kvm`; een emulatortest kon alleen in een container met dat apparaat. In media-guard-ultimate bleef de emulator-rooktest daardoor liggen tot na een nieuwe aanmelding. (Bron: R `analyse:testomgeving`; V `## jelly-leon-clients`, `### review:jlc`; V `## media-guard-ultimate`, `### android:mg`.)
- **Hoe herken je het:** De emulator start niet of meldt dat hardwareversnelling ontbreekt.
- **Wat doe je in plaats daarvan:** In de sessie waarin dit bestand is geschreven had de sessiegebruiker geen lees- of schrijfrecht op `/dev/kvm` (geen lid van de groep `kvm`). Of dat in jouw sessie ook zo is, is ONBEKEND - eerst vaststellen met: `test -w /dev/kvm && echo schrijfbaar; id -nG`. Werkt het niet, dan is de emulatortest "Geblokkeerd" met de reden; schermafdruktests zonder emulator zijn dan hooguit "Sim-getest". Gebruik geen sudo in repo-scripts om dit te omzeilen.

---

## 2. Git en CI

### V-022 — `git add -A` neemt buildbestanden mee
- **Wat ging er mis:** jelly-leon-clients: een `git add -A` tijdens een Gradle-build nam een Kotlin-sessiebestand mee; dit is vóór de push ontdekt. my_house: een eerste Android-build liet een JVM-crashlog in de repo achter, en er is een keer een Python-wheel in de repo-root gecommit dat later weer verwijderd is. (Bron: R `review:jelly-leon-clients`, R `test:mh`; my_house `git log`, commit met "Opruimen: wheel".)
- **Hoe herken je het:** `git status` toont bestanden die je niet zelf hebt gemaakt, of de diff bevat binaire bestanden.
- **Wat doe je in plaats daarvan:** Stage gericht per pad en lees `git diff --cached --stat` vóór elke commit. Commit niet terwijl een build in dezelfde werkmap loopt.

### V-023 — Testrun-mappen en testresultaten staan in de repo
- **Wat ging er mis:** In het oude media-guard-ultimate stond een gecommitte testrun-map met databases, sleutelbestanden en logs. In media-source-optimizer stond onder `tests/stack/` een complete databasemap van 67 MB met dumps en een sleutelbestand. (Bron: R `openbaarheidsscan`.)
- **Hoe herken je het:** `git ls-files` toont mappen die met een punt beginnen onder `tests/`, of bestanden met de extensies van databases en dumps.
- **Wat doe je in plaats daarvan:** Schrijf testuitvoer naar een map buiten de repo of naar een pad dat in `.gitignore` staat. Controleer dat vóór de eerste run. De repos zijn publiek.

### V-024 — Oude commits met een verboden regel zijn niet te repareren
- **Wat ging er mis:** In ongeveer 590 oude commitberichten staat een sessietrailer. Verwijderen kan alleen door de historie te herschrijven en te force-pushen, en dat is verboden. (Bron: R `openbaarheidsscan`.)
- **Hoe herken je het:** `git log` toont oude commits die niet aan de huidige commitregels voldoen.
- **Wat doe je in plaats daarvan:** Laat oude commits staan en meld het. Nieuwe commits volgen C §12: Nederlands bericht, geen modelnaam of model-ID, en als laatste regel `Co-Authored-By: Claude <noreply@anthropic.com>`. Nooit `git push --force`, nooit `git filter-repo`.

### V-025 — Een CI-stap kan door de schrijfwijze nooit falen
- **Wat ging er mis:** ai-server-manager: een stap begon met `! python -m hub migrate --check`. Het uitroepteken schakelt het afbreken bij een fout uit voor dat commando, dus de controle na de downgrade kon nooit rood worden. (Bron: R `review-1.2:ai-server-manager`.)
- **Hoe herken je het:** Een shellregel in een workflow begint met `!`, of eindigt op `|| true`.
- **Wat doe je in plaats daarvan:** Schrijf de controle uit als `if <commando>; then echo "<reden>"; exit 1; fi`. Laat shellcheck over de workflowscripts lopen en doe een mutatieproef op de CI-stap zelf.

### V-026 — De release-workflow publiceert vanaf een branch
- **Wat ging er mis:** jelly-leon-platform: `release.yml` pushte bij handmatig starten op een branch de versie-tag naar GHCR. (Bron: R `review:jelly-leon-platform`.)
- **Hoe herken je het:** De release-workflow heeft `workflow_dispatch` en geen controle op het soort ref.
- **Wat doe je in plaats daarvan:** Publiceer een versie-tag alleen als de workflow door een git-tag is gestart. Test de workflow op een branch en controleer dat er niets gepusht wordt.

### V-027 — De bewijscontrole slaagt als het bewijs ontbreekt
- **Wat ging er mis:** jelly-leon-web: `check_fork_consistency.py` was fail-open; bij een ontbrekend of leeg bewijsbestand slaagde de controle. (Bron: R `review:jlw`.)
- **Hoe herken je het:** Verwijder of leeg het invoerbestand in een proefmap; de controle blijft groen.
- **Wat doe je in plaats daarvan:** Elke bewaker faalt bij ontbrekende, lege of onleesbare invoer. Zie `<WERKMAP>/jelly-leon-web/tools/jelly-leon-web/check_fork_consistency.py` en als voorbeeld van een bewaker-test `<WERKMAP>/ai-server-manager/apps/api/tests/unit/test_evidence_contract.py`.

### V-028 — Lokaal en in CI draaien verschillende versies van hetzelfde gereedschap
- **Wat ging er mis:** my_house: een CI-run werd rood omdat shellcheck op de runner (0.9) een melding onder een ander nummer geeft dan de lokale versie (0.11). Op deze machine is `python3` versie 3.14, terwijl CI 3.12 gebruikt. In home-control-hub koos de systeemwrapper van PostgreSQL een dump-programma van versie 18 naast een herstelprogramma van versie 16. (Bron: R `review-1.3:my_house`, R `test:mh`, R `hch:sso`.)
- **Hoe herken je het:** Lokaal groen en in CI rood (of omgekeerd) zonder codeverschil.
- **Wat doe je in plaats daarvan:** Maak de virtuele omgeving met `/usr/bin/python3.12 -m venv`. Zet voor PostgreSQL-gereedschap `PATH=/usr/lib/postgresql/16/bin:$PATH` (media-source-optimizer: `MSO_PG_BIN=/usr/lib/postgresql/16/bin`). Onderdruk een lintermelding onder beide nummers als de versies verschillen. (Bron voor de instellingen: O.)

### V-029 — Bewijs van mislukte browsertests wordt niet bewaard
- **Wat ging er mis:** my_house: rapporten en traces van mislukte browsertests werden nooit bewaard, omdat de uploadstap een verborgen map overslaat. Een wisselend falende test bij de eerste start was daardoor moeilijk te onderzoeken. (Bron: R `review-1.3:my_house`.)
- **Hoe herken je het:** Een rode e2e-run heeft geen artefact, of het artefact is leeg.
- **Wat doe je in plaats daarvan:** Zet `include-hidden-files: true` bij de uploadstap als de uitvoermap met een punt begint. Controleer bij de eerste rode run dat het artefact er echt is. Ruim de uitvoermap niet op in het script dat de stack stopt.

### V-030 — Een storing bij GitHub wordt voor een eigen fout aangezien
- **Wat ging er mis:** home-control-hub: een run mislukte omdat GitHub tijdens een storing een job niet aanmaakte. media-source-optimizer: een run stond op "failure" zonder mislukte job. jelly-leon-platform: een commitbericht noemde ten onrechte een lange stapnaam als oorzaak. (Bron: R `hch:ontwerpreview`, R `web:mso`, R `plat:ontwerpreview`.)
- **Hoe herken je het:** De run is rood, maar geen enkele job heeft een mislukte stap, of een job ontbreekt.
- **Wat doe je in plaats daarvan:** Lees eerst de jobs en stappen van de run (`gh run view <run-id>`). Schrijf geen oorzaak in een commitbericht die je niet hebt vastgesteld. Start de run opnieuw en noem beide run-ID's in het bewijs.

### V-031 — Een hangende run en een push eroverheen
- **Wat ging er mis:** ai-server-manager: een run werd geannuleerd omdat de stap die Chromium voor Playwright installeert meer dan 35 minuten hing (normaal anderhalve minuut). De herstart werd daarna afgebroken door de volgende push. (Bron: R `review:contract-1.3`.)
- **Hoe herken je het:** Een stap duurt een veelvoud van de vorige run. Na een nieuwe push staat de vorige run op "cancelled".
- **Wat doe je in plaats daarvan:** Volg na elke push de run tot het einde (C §12). Push niet opnieuw zolang je de lopende run nodig hebt als bewijs: bijna alle workflows hebben `cancel-in-progress: true` per branch, dus ook een met de hand gestarte run van dezelfde workflow breekt de lopende af (POORTEN.md, 0.5). Annuleer een hangende stap en start opnieuw; noem dat in het bewijs.

### V-032 — Een wisselend falende test wordt weggeretryd
- **Wat ging er mis:** media-guard-ultimate: een tijdgevoelige test (`test_hooks`) faalde in CI op een tijdsgrens; de run faalde tegelijk op e2e-tests door UI-werk van een andere agent. my_house: de test voor de eerste start faalde wisselend. (Bron: R `controle` fase Controle na het verwerken; R `review-1.3:my_house`.)
- **Hoe herken je het:** Dezelfde commit is de ene keer rood en de andere keer groen.
- **Wat doe je in plaats daarvan:** Noteer bij elke herhaling de run-ID en de oorzaak die je hebt vastgesteld. Is de oorzaak een tijdsgrens, maak de test dan onafhankelijk van de belasting. Meld een wisselende test als open punt; "tweede poging groen" is geen afronding.

### V-033 — Padfilters: de workflow draait niet op je commit
- **Wat ging er mis:** jelly-leon-clients: de workflows voor Android, tv, desktop en Swiftfin draaiden niet op commits die geen clientcode raakten, omdat hun padfilter alleen clientcode dekt. (Bron: R `int:forks`.)
- **Hoe herken je het:** Er is voor je laatste commit geen run van de workflow die je als bewijs wilt noemen.
- **Wat doe je in plaats daarvan:** Noem in het bewijs de commit waarop de laatste groene run echt draaide, en zeg erbij dat latere commits de workflow niet raakten. Claim geen groene run voor een commit zonder run.

### V-034 — "Groen" zonder echte run
- **Wat ging er mis:** media-source-optimizer: de branch had geen enkele Actions-run en `ci.yaml` was op GitHub nooit gedraaid, terwijl een eerder rapport van groen uitging. Ook bouwde `ci.yaml` de alles-in-één-image niet; er is later een job `allinone` toegevoegd. (Bron: R `controle:mso`, R `review-1.3:media-source-optimizer`.)
- **Hoe herken je het:** In het rapport staat "CI groen" zonder run-ID en commit.
- **Wat doe je in plaats daarvan:** R-EERLIJK controleert elke CI-claim met `gh run list --branch <branch>` en `gh run view <run-id>`. Zonder run-ID en commit geen claim. Controleer ook dat de workflow het onderdeel dat je claimt echt bouwt of test.

### V-035 — Verschuivende verwijzingen in build en CI
- **Wat ging er mis:** jelly-leon-clients: de Dockerfile begon met `# syntax=docker/dockerfile:1.7`, een verschuivende tag zonder digest. jelly-leon: CI was rood omdat de SDK-versie uit `global.json` niet te downloaden was; die versie stond er alleen als ondergrens. (Bron: R `review:jelly-leon-clients` fase P0-hiaten, R `p0:jelly-leon`.)
- **Hoe herken je het:** Een build die gisteren werkte, faalt vandaag zonder wijziging; in de workflow staan tags zonder digest of acties zonder commit-SHA.
- **Wat doe je in plaats daarvan:** Pin images op digest en acties op commit-SHA. Leg vast hoe de SDK-versie in CI gekozen wordt (jelly-leon `docs/adr/ADR-0010-ci-sdk-kanaal-en-openapi-drift.md`).

### V-036 — sudo in CI of in testscripts
- **Wat ging er mis:** jelly-leon: een CI-job gebruikte `sudo chown`. media-source-optimizer: de stacktest van de alles-in-één-image werd lokaal met sudo gestart. (Bron: R `review:jl`, R `test:mso`.)
- **Hoe herken je het:** `grep -rn "sudo" .github scripts tests` geeft treffers.
- **Wat doe je in plaats daarvan:** Gebruik een wegwerpcontainer voor het aanpassen of uitlezen van eigenaar en rechten. Op deze machine is sudo alleen voor systeeminstallaties en nooit in repo-scripts (O).

### V-037 — De rooktest in CI test tegen de vorige contractversie
- **Wat ging er mis:** jelly-leon-platform: de rooktest in CI draaide tegen de Hub van contract 1.2, terwijl 1.3 gold. (Bron: R `review-1.3:jelly-leon-platform`.)
- **Hoe herken je het:** De workflow haalt de Hub of de simulator op een vaste oude commit binnen.
- **Wat doe je in plaats daarvan:** Werk bij elke contractwijziging de gepinde commit van de tegenpartij in CI bij, en laat de rooktest de contractversie controleren die hij aantreft.

### V-038 — CI was bij de overname al rood
- **Wat ging er mis:** Bij de overname van de machine stond CI rood in jelly-leon (SDK-versie), in jelly-leon-platform (vier lintfouten) en in zoeken-en-persoonlijke-ai (rooktest). (Bron: S, kop "Nieuwe machine".)
- **Hoe herken je het:** De laatste run op de branch is rood vóór je eerste wijziging.
- **Wat doe je in plaats daarvan:** Doe een nulmeting vóór je begint: laatste run-ID, commit en uitkomst. Draai lint en opmaakcontrole lokaal vóór elke push. Een fout die er al was, meld je apart van je eigen werk.

---

## 3. Python, FastAPI en PostgreSQL

### V-039 — De grens van 1 MiB wordt pas na routering of authenticatie gecontroleerd
- **Wat ging er mis:** C §5 eist een maximale verzoekgrootte van 1 MiB met antwoord 413. In jelly-leon-platform gaf een te grote body in stukken (chunked) 401, 404 of 405 in plaats van 413. In de executor van ai-server-manager werd alleen `Content-Length` gecontroleerd en miste de 413 het veld `details.max_bytes`. Via de webpoort van ai-server-manager (doorgang in Node) werd een upload van 3 MB in 18 van de 25 gevallen een 502. In appstore-en-fork gaf een te groot chunked verzoek op een route zonder body-model 401. (Bron: R `review-1.2:jelly-leon-platform`, R `review-1.2:ai-server-manager`, R `1.2:appstore-en-fork`.)
- **Hoe herken je het:** Stuur een chunked body van meer dan 1 MiB naar een bestaande route, een niet-bestaande route en een route zonder body, met en zonder geldige aanmelding. Alles behalve 413 is fout.
- **Wat doe je in plaats daarvan:** Tel de body in een ASGI-laag vóór routering en authenticatie, ook zonder `Content-Length`. Test elke ingang apart: de API, de statuspagina en elke doorgang ervoor.

### V-040 — Een 413 komt bij de client aan als een verbroken verbinding
- **Wat ging er mis:** zoeken-en-persoonlijke-ai: de 413 kwam bij de client vaak aan als verbindingsreset, omdat de rest van de body ongelezen bleef. (Bron: R `review-1.2:zoeken-en-persoonlijke-ai`.)
- **Hoe herken je het:** De test voor te grote verzoeken slaagt wisselend, of de client meldt een netwerkfout in plaats van een statuscode.
- **Wat doe je in plaats daarvan:** Lees of sluit de verbinding zo af dat het antwoord de client bereikt, en test met een echte HTTP-client over een socket, niet alleen met de testclient van het framework.

### V-041 — Een formulier geeft een kale 500
- **Wat ging er mis:** ai-server-manager: een formulier-POST op de koppelpagina van de executor met meer dan acht velden gaf "Internal Server Error" zonder vaste Nederlandse melding. (Bron: R `review-1.3:ai-server-manager`.)
- **Hoe herken je het:** Stuur te veel velden, te lange velden en dubbele velden; een 500 of een Engelse standaardtekst is fout.
- **Wat doe je in plaats daarvan:** Vang grenzen van de formulierverwerking af en geef een vaste foutcode met Nederlandse melding volgens C §5.

### V-042 — Retry-After wordt genegeerd of ingekort
- **Wat ging er mis:** jelly-leon-platform: na een 429 of 503 met Retry-After stuurde de worker in dezelfde ronde de andere events nog; een mislukte tokenrotatie werd elke vijf seconden opnieuw geprobeerd; enrollment kortte een lange Retry-After in. zoeken-en-persoonlijke-ai: na een 429 of 503 volgde binnen enkele seconden een nieuwe poging. (Bron: R `review-1.3:jelly-leon-platform`, R `review-1.3:zoeken-en-persoonlijke-ai`.)
- **Hoe herken je het:** Laat de simulator 429 met `Retry-After: 120` geven en tel de aanroepen in de volgende twee minuten. Meer dan nul is fout.
- **Wat doe je in plaats daarvan:** Stop de hele ronde bij 429 of 503 en plan de volgende poging op zijn vroegst na Retry-After. Dit geldt voor elk pad naar de Hub: outbox, rotatie, enrollment en bevestiging.

### V-043 — Rotatie en intrekking volgen niet alle paden
- **Wat ging er mis:** zoeken-en-persoonlijke-ai: een 401 die een intrekking bleek, telde toch als poging (in strijd met RV12). Paste de achtergrondpoll een sleutelrotatie als eerste toe, dan kwam er geen event `service.key_rotation.applied` en geen auditregel; een geblokkeerde rotatie gaf elke tien minuten een nieuw `rejected`. (Bron: R `review-1.3:zoeken-en-persoonlijke-ai`.)
- **Hoe herken je het:** Er zijn twee codepaden die hetzelfde kunnen toepassen (aanvraag en achtergrondpoll) en maar één heeft tests op events en audit.
- **Wat doe je in plaats daarvan:** Test elke toestandsovergang via elk pad dat hem kan uitvoeren, en controleer events en auditregels op precies één keer.

### V-044 — Twee gelijktijdige koppelpogingen slagen allebei
- **Wat ging er mis:** jelly-leon-platform: iemand op het LAN kon een koppelpoging naar een eigen "Hub" starten en pas antwoorden nadat de echte koppeling was opgeslagen; de controle "nog nooit gekoppeld" gebeurde alleen vóór het verzoek. appstore-en-fork had hetzelfde bij gelijktijdige pogingen en bij koppelen na een eerdere koppeling. (Bron: R `review-1.2:jelly-leon-platform`, R `review-1.2:appstore-en-fork`.)
- **Hoe herken je het:** De toestandscontrole en het opslaan staan niet onder dezelfde vergrendeling. Er is geen test met twee gelijktijdige pogingen.
- **Wat doe je in plaats daarvan:** Beslis en schrijf onder één bestandsvergrendeling van `hub-link.json` en controleer de toestand opnieuw vlak voor het opslaan. Een koppelcode overschrijft nooit een bestaande koppeling (C §3.7).

### V-045 — Het koppelbestand is onleesbaar door eigenaar of rechten
- **Wat ging er mis:** appstore-en-fork: herstel van een kapot `hub-link.json` liep vast als het bestand van een andere eigenaar was, bijvoorbeeld van root met 0600 na een herstel als root (C1.3-ASF-04). home-control-hub: het bestand geldt als onleesbaar zodra de rechten ruimer zijn dan 0600; de dienst moet de rechten daarom zelf zetten. Of dit op een echte dataset met overgeërfde rechten goed gaat is NIET GEVALIDEERD (echte NAS). (Bron: R `review-1.3:appstore-en-fork`, R `1.3:appstore-en-fork`, R `review-1.3:home-control-hub`.)
- **Hoe herken je het:** Maak het bestand in een proefmap aan met een andere eigenaar of met 0644 en start de dienst. Een stille terugval naar "nooit gekoppeld" is fout.
- **Wat doe je in plaats daarvan:** Bewaar het origineel, toon de vaste foutcode `koppelstatus_onleesbaar` en bied geen koppelformulier aan. Schrijf het bestand altijd zelf met 0600 en test dat met een tegenproef. Zie `<WERKMAP>/appstore-en-fork/apps/api/src/appstore/hublink_store.py`.

### V-046 — Een antwoord bevat een veld buiten de witte lijst
- **Wat ging er mis:** appstore-en-fork: `GET /connector/v1/hub-link` gaf ook `confirmed_at` mee. Dat veld staat niet in de witte lijst van C §3.5 en die lijst is een maximum. (Bron: R `review-1.3:appstore-en-fork`.)
- **Hoe herken je het:** De test controleert alleen of verplichte velden aanwezig zijn.
- **Wat doe je in plaats daarvan:** Test op de exacte veldenset: geen veld te weinig en geen veld te veel.

### V-047 — Een JWT met `aud` als lijst wordt geaccepteerd
- **Wat ging er mis:** home-control-hub accepteerde een JWT waarin `aud` een lijst met twee diensten was. Zo'n token is dan bij meer diensten bruikbaar, terwijl elke dienst een eigen replaycache heeft. De reviewer meldde dat appstore-en-fork, zoeken-en-persoonlijke-ai en ai-server-manager dezelfde aanroep zonder strikte controle gebruikten. (Bron: R `review:hch` na contract 1.2; V `## home-control-hub`, `### review:hch`.)
- **Hoe herken je het:** `grep -rn "jwt.decode" <repo>` toont een aanroep met `audience=` zonder strikte controle op één waarde.
- **Wat doe je in plaats daarvan:** Accepteer precies één `aud` als tekst (C §4). Voeg een negatieve test toe met een lijst. Bij het schrijven van dit bestand kwam de naam `strict_aud` alleen in home-control-hub voor. Of de andere drie repos een eigen strikte controle hebben is ONBEKEND - eerst vaststellen met: `grep -rn "strict_aud\|jwt.decode" <WERKMAP>/appstore-en-fork <WERKMAP>/zoeken-en-persoonlijke-ai <WERKMAP>/ai-server-manager --include=*.py`.

### V-048 — Adrescontrole is te omzeilen met afwijkende schrijfwijzen
- **Wat ging er mis:** my_house: het startscript liet voor het Hub-adres verkorte en afwijkende schrijfwijzen van het loopback-adres door (octaal, decimaal, hexadecimaal, verkorte en gemapte IPv6-vormen). media-source-optimizer: `lower()` in Python en `toLowerCase()` in JavaScript maken van het Kelvin-teken een gewone "k", zodat een vergelijking na omzetting iets anders controleert dan wat is ingevoerd (C1.3-MSO-02). (Bron: R `review:mh`, R `review-1.3:media-source-optimizer`.)
- **Hoe herken je het:** De validatie gebruikt een eigen reguliere expressie of zet eerst om naar kleine letters. Er is geen lijst met afwijkende vormen in de tests.
- **Wat doe je in plaats daarvan:** Weiger niet-ASCII vóór elke omzetting. Accepteer een IPv4-adres alleen in de vorm van vier decimale getallen. Test dezelfde lijst afwijkende vormen in elke laag die het adres controleert (API en web).

### V-049 — De snelheidslimiet vertrouwt een header van de aanvrager
- **Wat ging er mis:** jelly-leon-platform: met een startoptie kon de webserver `X-Forwarded-For` vertrouwen, terwijl de limiet per bron-adres van de TCP-verbinding moet tellen. (Bron: R `review-1.2:jelly-leon-platform`.)
- **Hoe herken je het:** De startregel van de server bevat een optie voor vertrouwde doorstuuradressen, of de code leest `X-Forwarded-For`.
- **Wat doe je in plaats daarvan:** Zet het vertrouwen van proxyheaders uit. Het werkelijke bron-adres achter de netwerklaag van de NAS blijft NIET GEVALIDEERD (echte NAS).

### V-050 — Onverwachte invoertypen geven een 500 of een verkeerde waarde
- **Wat ging er mis:** zoeken-en-persoonlijke-ai: een tijdstip zonder tijdzone gaf een 500, en een cursor met `true` of `false` telde als getal. appstore-en-fork: `sequence: true` telde als volgnummer 1 en een volgnummer dat geen geheel getal was liet het toepassen crashen. ai-server-manager: gelijktijdig dezelfde gebruikersnaam aanmaken gaf 500 in plaats van 409. jelly-leon-platform: een lege variabele voor de datamap maakte de werkmap tot datamap. (Bron: R `review:zoeken-en-persoonlijke-ai`, R `review-1.2:appstore-en-fork`, R `review:hub`, R `review-1.2:jelly-leon-platform`.)
- **Hoe herken je het:** Velden voor getallen hebben geen strikte typecontrole (in Python is `True` ook een getal). Unieke waarden worden alleen vooraf gecontroleerd, niet bij het schrijven. Instellingen worden niet op "leeg" gecontroleerd.
- **Wat doe je in plaats daarvan:** Gebruik strikte typen in de invoermodellen. Vang de unieke-sleutelfout van de database af en geef 409. Weiger lege verplichte instellingen bij de start met een duidelijke melding.

### V-051 — De gezondheidsstatus zegt "gezond" zonder verse meting
- **Wat ging er mis:** home-control-hub: een meting van drie dagen oud stond als "Gezond"; na reparatie is dat `unknown` met de reden `meting_verouderd`. ai-server-manager kreeg dezelfde regel in contract 1.3. (Bron: R `hch:ontwerpreview`, R `review:hch` na contract 1.2, R `review:contract-1.3`.)
- **Hoe herken je het:** De status wordt afgeleid uit de laatst bekende waarde zonder naar de leeftijd te kijken. `observed_at` is het moment van de aanvraag in plaats van het moment van meten.
- **Wat doe je in plaats daarvan:** De slechtste controle bepaalt de totaalstatus (C §6). Een verouderde meting is "onbekend", nooit "gezond". `observed_at` is het moment van de oudste meting waarop de uitspraak rust.

### V-052 — De healthcheck gedraagt zich anders dan het echte verkeer
- **Wat ging er mis:** appstore-en-fork: de healthcheck volgde de proxy uit de omgeving, ook naar het eigen loopback-adres; wie in het formulier een proxy zet, kreeg een container die onterecht "unhealthy" werd (C1.3-ASF-01). jelly-leon-platform: elke healthcheck schreef migratieregels in de log. zoeken-en-persoonlijke-ai: een nieuwe controle in de rooktest gebruikte HEAD en kreeg 405. (Bron: R `review-1.3:appstore-en-fork`, R `review:jelly-leon-platform`, R `1.3:zoeken-en-persoonlijke-ai`.)
- **Hoe herken je het:** Start de container met proxyvariabelen gezet en kijk naar de gezondheidsstatus en de log.
- **Wat doe je in plaats daarvan:** De healthcheck negeert proxyvariabelen, schrijft niets en gebruikt de methode die de route ondersteunt. Zie `<WERKMAP>/appstore-en-fork/deploy/allinone/healthcheck.py`.

### V-053 — Met UID of GID 0 blijft alles als root draaien
- **Wat ging er mis:** zoeken-en-persoonlijke-ai: met de variabele voor UID of GID op 0 bleef de hele dienst als root draaien. (Bron: R `review-1.3:zoeken-en-persoonlijke-ai`.)
- **Hoe herken je het:** Het startscript neemt de doelgebruiker uit een variabele over zonder de waarde 0 te weigeren.
- **Wat doe je in plaats daarvan:** Weiger 0 bij de start met een Nederlandse melding. Test dit in de rooktest van de image (C §2.2).

### V-054 — Een dienst stuurt te veel of te weinig naar de Hub
- **Wat ging er mis:** appstore-en-fork: elke importronde (elke 15 minuten) zette een event in de outbox, ook zonder verandering; dat zijn 96 events per dag van dezelfde soort. (Bron: R `review:app`.)
- **Hoe herken je het:** Tel de events in de outbox na een uur stilstand.
- **Wat doe je in plaats daarvan:** Stuur een event alleen bij een verandering van toestand en ontdubbel op inhoud.

### V-055 — Een beveiliging in de database of in de omleiding dekt niet alle wegen
- **Wat ging er mis:** ai-server-manager: de auditketting weigerde `TRUNCATE` niet, omdat een trigger per rij daar niet op afgaat. Het terugkeerpad na aanmelden liet een open omleiding toe via een tabteken of een regeleinde. (Bron: R `review:hub`.)
- **Hoe herken je het:** De bescherming is geschreven voor de gewone weg (UPDATE, DELETE, een nette URL) en er is geen test voor de afwijkende weg.
- **Wat doe je in plaats daarvan:** Zet naast de rij-trigger een trigger op opdrachtniveau. Weiger stuurtekens in elk pad dat als omleiding dient. Test beide met een negatieve proef.

### V-056 — De database op de ontwikkelmachine staat niet in UTC
- **Wat ging er mis:** my_house: een migratietest (`test_migration_0004_limits_legacy_phone_tokens`) faalde lokaal en niet in CI. De lokale PostgreSQL draait in de lokale tijdzone, CI in UTC. Een herhaling met de omgevingsvariabele voor de tijdzone gaf geen verschil, omdat de gebruikte databasebibliotheek die variabele niet leest. (Bron: R `test:mh`, R `controle:mh`; V `## my_house`, `### fix:mh`.)
- **Hoe herken je het:** Een test met datums of tijdsgrenzen faalt alleen lokaal en deterministisch.
- **Wat doe je in plaats daarvan:** Schrijf migraties onafhankelijk van de tijdzone (my_house `docs/adr/ADR-0007-tijdzone-onafhankelijke-migraties.md`). Test tegen een database die als CI is ingesteld, of zet de tijdzone op de eigen databaserol. Wijzig de instellingen van de gedeelde PostgreSQL niet.

### V-057 — Tests hangen af van het geheugen of de schijf van de machine
- **Wat ging er mis:** media-guard-ultimate: encodertests lazen de geheugengrens van de eigen procesgroep en faalden daardoor lokaal; zes andere tests gingen uit van meer dan 2 GB vrij in de gedeelde tijdelijke map. media-source-optimizer: de logcontrole van de stack was te streng en struikelde over een regel die de database schrijft bij het eigen afsluiten. (Bron: R `test:mg`, R `review-1.3:media-guard-ultimate`, R `test:mso`.)
- **Hoe herken je het:** Een test faalt op de ene machine en niet op de andere, zonder codeverschil.
- **Wat doe je in plaats daarvan:** Vervang metingen van de machine in tests door vaste waarden (fixtures `ruim_werkgeheugen` en `ruime_cache` in `<WERKMAP>/media-guard-ultimate/services/encoder/tests/conftest.py`). Laat een logcontrole alleen regels afkeuren die niet bij een verwachte handeling horen.

---

## 4. Web, Next.js en Peil

### V-058 — Het lettertype verschilt tussen CI en de ontwikkelmachine
- **Wat ging er mis:** my_house: een CI-run faalde op 5 px overloop bij 320 px breedte, alleen met de lettertypes van de CI-runner. appstore-en-fork: een CI-run vond tekst die op 320 px buiten de melding stak met het lettertype van de runner. media-guard-ultimate: het bedoelde lettertype werd nooit geladen, omdat de variabele alleen op `body` stond; daar gaf juist de ontwikkelmachine overloop en de lettertypes van CI niet. (Bron: R `web:mh`, R `app:ontwerpreview`, R `controle:mg`.)
- **Hoe herken je het:** Een overlooptest is lokaal groen en in CI rood, of omgekeerd.
- **Wat doe je in plaats daarvan:** Controleer in de browser welk lettertype echt gebruikt wordt. Meet overloop ook met de lettertypes die de CI-runner heeft (media-source-optimizer en zoeken-en-persoonlijke-ai deden dat met geforceerde lettertypes in de meting). Installeer of wijzig geen lettertypes op de gedeelde machine.

### V-059 — Een handeling start voordat de sessie klaar is
- **Wat ging er mis:** media-guard-ultimate: in een e2e-test ging een upload de deur uit zonder CSRF-token, omdat de pagina de sessie nog niet had opgehaald; de eerste pogingen faalden telkens met 403. my_house: een momentopname van enkele seconden oud met een nog lege lijst gold na herladen als vers. (Bron: R `test:mg`, R `controle:mg`, R `review-1.3:my_house`.)
- **Hoe herken je het:** Een e2e-test slaagt pas bij de tweede poging. Na herladen is een scherm kort leeg zonder laadtoestand.
- **Wat doe je in plaats daarvan:** Schakel knoppen pas in als de sessie geladen is. Laat de test wachten op een zichtbare toestand, niet op tijd. Behandel "nog niet geladen" als aparte toestand, niet als lege lijst.

### V-060 — De pagina vraagt eindeloos opnieuw gegevens op
- **Wat ging er mis:** ai-server-manager: in de Hub-grafieken veranderde de sleutel van de aanvraag bij elke weergave; de app deed 1357 aanvragen in zes seconden. Na reparatie zijn het er drie. (Bron: R `hub:ontwerpreview`.)
- **Hoe herken je het:** Tel de netwerkaanvragen van een stilstaande pagina in Playwright.
- **Wat doe je in plaats daarvan:** Houd de sleutel van een aanvraag stabiel (geen tijdstip van "nu" erin). Voeg een e2e-test toe met een bovengrens op het aantal aanvragen per pagina.

### V-061 — axe meldt nul fouten, maar de pagina breekt Peil
- **Wat ging er mis:** De geautomatiseerde toegankelijkheidscontrole gaf nul overtredingen, terwijl de ontwerpreviews wel fouten vonden. home-control-hub: een verouderde meting stond groen als "Gezond". zoeken-en-persoonlijke-ai: interne taak-ID's stonden op de pagina en de standaardzin gebruikte een verboden woord, waardoor de eigen woordcontrole op elke toestand faalde. my_house: vóór de omzetting 58 doelen kleiner dan 44 px en tekst kleiner dan de ondergrens. (Bron: R `hch:ontwerpreview`, R `zoek:ontwerpreview`, R `1.3:zoeken-en-persoonlijke-ai`, R `web:mh`.)
- **Hoe herken je het:** Het bewijs voor de UI bestaat alleen uit "axe 0".
- **Wat doe je in plaats daarvan:** R-ONTWERP meet naast axe zelf: de vaste woordenlijst van Peil, één uiterlijk per status, onbekend en verouderd nooit groen, doelgrootte, overloop en tekstafstand, en een doorloop met Tab. De matrix is alle voorgeschreven breedtes in licht en donker. Zie `<WERKMAP>/ai-server-manager/docs/platform-v2/ONTWERPTAAL.md` en het meetvoorbeeld `<WERKMAP>/jelly-leon-platform/tests/ui/controle.mjs`.

### V-062 — De ontwerptaal zelf bevatte fouten
- **Wat ging er mis:** Bij de review van Peil in ai-server-manager bleek dat voorgeschreven klassen voor de lagenvolgorde niet bestonden, en dat kleurvariabelen naar zichzelf verwezen waardoor vlakken voor "Onbekend" en "Info" in Chromium doorzichtig werden. (Bron: R `review:ontwerp`.)
- **Hoe herken je het:** Een onderdeel uit de componentenlijst heeft geen stijl in de gebouwde CSS, of een vlak heeft geen achtergrond.
- **Wat doe je in plaats daarvan:** Bouw de CSS met het bouwscript in `<WERKMAP>/ai-server-manager/design/ontwerptaal/bouw/` en draai de controles daar. Neem het sjabloon byte-gelijk over; een afwijking is een wijzigingsvoorstel voor ai-server-manager, geen lokale aanpassing.

### V-063 — Schermafdrukken bevatten echte gegevens
- **Wat ging er mis:** Bij de voorbereiding op het openbaar maken zijn de afbeeldingen van media-guard-ultimate, media-source-optimizer en my_house met tekstherkenning doorzocht, ook oudere versies uit de historie. In het oude media-guard-ultimate stonden rapporten met echte gegevens van de NAS; die repo is daarom vervangen door een nieuwe publieke repo met schone historie. (Bron: R `privacy`, R `openbaarheidsscan`.)
- **Hoe herken je het:** Afdrukken zijn gemaakt tegen een echte installatie, of tonen het pad van de werkmap of een adres in de adresbalk.
- **Wat doe je in plaats daarvan:** Maak afdrukken alleen met testgegevens en fictieve namen. Maak ze opnieuw na elke opschoning van de code. Meetscripts die je commit bevatten geen absolute paden van deze machine.

### V-064 — Een instelling die de gebruiker ergens heen stuurt is door te veel rollen te wijzigen
- **Wat ging er mis:** media-guard-ultimate: het Hub-adres voor de knop "Terug naar de Hub" kon door een operator gewijzigd worden; dat maakt misleiding via die knop mogelijk. Nu mag alleen een beheerder het wijzigen. (Bron: R `review:mg`.)
- **Hoe herken je het:** Een instelling met een URL staat niet in de lijst van instellingen die alleen de beheerder mag wijzigen.
- **Wat doe je in plaats daarvan:** Behandel elke instelling die een link of omleiding bepaalt als beheerdersinstelling en valideer het adres volgens C §3.2.

### V-065 — Een uitgeschakelde knop doet toch iets
- **Wat ging er mis:** media-source-optimizer: de bevestigknop in de dialoog voor gevaarlijke handelingen ging van `disabled` naar `aria-disabled`, zonder test die bewijst dat hij dan niets doet. (Bron: R `review:mso`.)
- **Hoe herken je het:** Een knop heeft `aria-disabled` en de klikafhandeling controleert de toestand niet zelf.
- **Wat doe je in plaats daarvan:** Voeg bij elke wissel naar `aria-disabled` een test toe die klikt en met Enter en spatie activeert, en aantoont dat er geen aanvraag vertrekt.

### V-066 — De OpenAPI-beschrijving loopt uit de pas
- **Wat ging er mis:** In de UI-ronde voor media-guard-ultimate, media-source-optimizer en my_house gold de afspraak dat de API niet verandert; dat is alleen te bewijzen met een driftcontrole. In media-guard-ultimate verschilde de export na een opschoning in één docstring. (Bron: R `prep:mg`; media-source-optimizer `apps/core/tests/test_openapi_export.py`.)
- **Hoe herken je het:** De repo heeft geen test die de geëxporteerde OpenAPI met de vastgelegde versie vergelijkt.
- **Wat doe je in plaats daarvan:** Voeg een driftcontrole toe en draai die in CI. Een UI-taak die de export verandert, stopt en meldt dat.

### V-067 — De browser voor Playwright ontbreekt of is de verkeerde build
- **Wat ging er mis:** media-guard-ultimate: de gebruikte Playwright-versie vroeg een Chromium-build die niet in de cache stond; er stonden alleen andere builds. (Bron: R `test:mg`.)
- **Hoe herken je het:** Playwright meldt dat het uitvoerbare bestand van de browser ontbreekt.
- **Wat doe je in plaats daarvan:** Draai `npx playwright install chromium` zonder `--with-deps` in de repo waar je test (O). Verander de vastgelegde Playwright-versie niet om een aanwezige build te kunnen gebruiken.

---

## 5. .NET en de Jellyfin-fork

### V-068 — De container is "healthy" met een lege instellingenmap
- **Wat ging er mis:** jelly-leon: met `/config` als tmpfs (het formulier van de Custom App biedt die keuze) werd de container toch gezond, met een lege database. De startwizard stond na elke herstart weer voor iedereen open. (Bron: R `review:jelly-leon` fase P0-hiaten; V `## jelly-leon`.)
- **Hoe herken je het:** Start de image met de datamap op tmpfs of op een anoniem volume. Wordt hij gezond, dan is het fout.
- **Wat doe je in plaats daarvan:** De entrypoint weigert een data- of instellingenmap op tmpfs, op een anoniem volume, in de container zelf en op een netwerkschijf, ook bij start als niet-root (jelly-leon `docs/adr/ADR-0008-alles-in-een-image.md`, `<WERKMAP>/jelly-leon/deploy/allinone/entrypoint.sh`). De weigering op een netwerkschijf is niet getest: er was geen NFS- of SMB-server. Dezelfde regel geldt voor elke platformapp met `/appdata`.

### V-069 — De README spreekt een besluit van de gebruiker tegen
- **Wat ging er mis:** jelly-leon: de README noemde een release op de oude basisversie als eerste release, terwijl besluit 2 zegt dat eerst naar 12.x wordt gegaan. (Bron: R `review:jelly-leon` fase P0-hiaten; S, kop "Besluiten van de gebruiker".)
- **Hoe herken je het:** Versienummers of volgordes in README en ADR's komen niet overeen met de besluitenlijst in STATUS.md.
- **Wat doe je in plaats daarvan:** Lees de besluiten in STATUS.md vóór je documentatie schrijft en verwijs naar het besluit in plaats van het over te typen.

### V-070 — Terugvallen op de vorige image lijkt te werken
- **Wat ging er mis:** jelly-leon en jelly-leon-web: de oude stock-image start op de door 12.4 gemigreerde gegevens, meldt zich gezond, maar aanmelden geeft HTTP 500. JLT-61 eist dat de vorige image op gemigreerde gegevens zichtbaar faalt; dat onderdeel staat daarom op "Sim-mislukt". (Bron: R `p4-0:web`, R `review:jelly-leon-web`.)
- **Hoe herken je het:** Een terugvalproef controleert alleen "container is healthy".
- **Wat doe je in plaats daarvan:** Een terugvalproef meldt zich aan en leest kijkgegevens terug. Terugval betekent: de bewaarde kopie van vóór de upgrade terugzetten, niet de oude image op nieuwe gegevens starten. Zie `<WERKMAP>/jelly-leon/tools/jelly-leon/e2e/rollback_sim.py` en `upgrade_proef.py` in dezelfde map. JLT-74 (echte NAS) is "Geblokkeerd".

### V-071 — Een poort eist tests die nog niet kunnen sluiten
- **Wat ging er mis:** jelly-leon: JLT-62 en JLT-67 staan op "Niet gestart" met reden; JLT-67 (bijwerken van 12.x naar een volgende 12-versie) kan pas als upstream zo'n versie uitbrengt. Bij de controle van het B03-plan bleek ook dat de volgorde van poorten en tests niet klopte. (Bron: R `p4-0:server`, R `p4-0:web`, R `controle` fase Controle van het B03-plan.)
- **Hoe herken je het:** Een poort noemt een test die afhangt van iets buiten de eigen invloed (een upstream-release, een echte NAS, een besluit).
- **Wat doe je in plaats daarvan:** A-GATE meldt zo'n test als open met reden en vraagt de regisseur om een besluit. De poort wordt niet stil verlaagd en de test wordt niet als gehaald geteld.

### V-072 — Bijwerken vanaf upstream botst met eigen wijzigingen
- **Wat ging er mis:** jelly-leon-clients: de proef met bijwerken vanaf upstream eindigde voor de tv-app met exit 2, omdat een beschermd bestand upstream verdwenen was, en voor Swiftfin met een conflict in het projectbestand. Dat is het bedoelde gedrag: de branch bleef ongewijzigd. (Bron: R `review:jlc`.)
- **Hoe herken je het:** `<WERKMAP>/jelly-leon-clients/tools/clients/upstream_sync.py` stopt met een foutcode.
- **Wat doe je in plaats daarvan:** Los het conflict niet automatisch op. Meld het, laat de eigen wijziging opnieuw toepassen en draai daarna `<WERKMAP>/jelly-leon-clients/tools/clients/check_clients.py`.

### V-073 — Een nagebootste client krijgt een ander antwoord dan de echte
- **Wat ging er mis:** jelly-leon: bij de analyse van de testomgeving gaf WebKit op Linux een onterechte "Direct Play" die niet afspeelde; het is geen Safari. Een meting met een nagebootste client zegt dus niets over de echte. (Bron: R `analyse:testomgeving`.)
- **Hoe herken je het:** De afspeelbeslissing is gemeten met een andere browser of een kale API-aanroep dan de client die de gebruiker heeft.
- **Wat doe je in plaats daarvan:** Laat het harnas vragen zoals de echte client vraagt, met diens apparaatprofiel. Claim voor Safari en Apple-apparaten alleen "NIET GEVALIDEERD (hardware)" of "(Mac/Xcode)".

### V-074 — .NET is niet op de machine geïnstalleerd
- **Wat ging er mis:** Geen fout, wel een randvoorwaarde die tijd kost als je hem mist: .NET draait op deze machine alleen via een image. (Bron: O.)
- **Hoe herken je het:** `dotnet` ontbreekt op het pad.
- **Wat doe je in plaats daarvan:** Bouw en test de server in de SDK-image, met de docker-buildlock en begrensde parallelliteit volgens O. Installeer geen SDK op de machine.

---

## 6. Android en clients

### V-075 — De Gradle-daemon crasht één keer
- **Wat ging er mis:** my_house: de eerste Android-releasebuild crashte in de geheugenopruiming van de JVM, terwijl er ruim geheugen vrij was. Een herhaling slaagde. De crash liet een logbestand in de repo achter. (Bron: R `test:mh`.)
- **Hoe herken je het:** De build stopt zonder compileerfout en er staat een nieuw crashlogbestand in de modulemap.
- **Wat doe je in plaats daarvan:** Herhaal één keer, meld beide pogingen en verwijder het crashlog uit de werkmap (niet committen, zie V-022). Bouw met de JDK die de CI van de repo gebruikt (my_house en media-guard-ultimate: JDK 17; jelly-leon-clients: JDK 21, zie POORTEN.md, P-jelly-leon-clients), `--no-daemon`, begrensde werkers en onder `<WERKMAP>/.lokaal/gradle.lock` (O).

### V-076 — Het bewijs van een emulatorproef wordt te mooi opgeschreven
- **Wat ging er mis:** jelly-leon-clients: de tabletproef raakte de sessie kwijt en staat op "Sim-mislukt"; de documentatie noemde de tablet eerst als goed. Dat is rechtgezet met een telling van de pogingen uit het bewijs. Bij het opbouwen van het corpus was de emulator met een groot scherm al eens door de kernel gestopt wegens geheugen (zie V-014). (Bron: R `p4-0:clients`, R `review:jelly-leon-clients` fase Review, R `golf0:corpus`.)
- **Hoe herken je het:** De tekst in de documentatie noemt meer apparaten als gehaald dan de bewijsbestanden.
- **Wat doe je in plaats daarvan:** Schrijf per apparaat het aantal pogingen en de uitkomst op zoals het bewijs die geeft. Draai een emulatorproef niet tegelijk met een zware build van een andere agent.

### V-077 — Het harnas keurt goed of af om de verkeerde reden
- **Wat ging er mis:** jelly-leon-clients: de tv-app meldt soms eerst positie 0 en een seconde later de echte positie; het harnas stopte dan te vroeg en keurde de poging af. Een stap die op Jelly Leon ontbrak, telde niet als regressie. Zonder leesbare geheugenmeting werd de geheugenstap weggelaten in plaats van afgekeurd. (Bron: R `review:jelly-leon-clients` fase Review.)
- **Hoe herken je het:** Uitkomsten wisselen tussen runs, of het rapport heeft minder stappen dan het draaiboek.
- **Wat doe je in plaats daarvan:** Een ontbrekende stap of meting is "mislukt", nooit "weggelaten". Wacht op een stabiele waarde in plaats van de eerste. Zie `<WERKMAP>/jelly-leon-clients/tools/clients/client_compat.py`.

### V-078 — "Unit-getest" zonder unit-tests
- **Wat ging er mis:** jelly-leon-clients: de forkstrategie noemde de Android-app "Unit-getest", terwijl upstream geen unit-tests heeft; er is alleen gecompileerd en verpakt. (Bron: R `review:jelly-leon-clients` fase P0-hiaten, R `p0:jelly-leon-clients`.)
- **Hoe herken je het:** De testtaak van Gradle meldt dat er geen bronnen zijn.
- **Wat doe je in plaats daarvan:** Gebruik de validatiewaarde die past bij wat er echt gedraaid is (C §11). Compileren is geen test.

### V-079 — Schermafdruktests worden grotendeels overgeslagen
- **Wat ging er mis:** media-guard-ultimate: de schermafdruktaak gaf 278 tests waarvan 138 overgeslagen; dat zijn documentatie-afdrukken die alleen met `PEIL_AFDRUKKEN=1` draaien. my_house: een schermtest faalde eerst omdat de testopzet een onderdeel miste dat het scherm nodig heeft. (Bron: R `ontwerpreview:mg`, R `android:mg`, R `ontwerp:mh`.)
- **Hoe herken je het:** Het aantal overgeslagen tests is groot en de reden staat niet in het rapport.
- **Wat doe je in plaats daarvan:** Noem het aantal overgeslagen tests met de reden. Schermafdruktests zonder emulator zijn "Sim-getest", geen apparaattest.

### V-080 — Een build wijzigt de gedeelde Android-SDK
- **Wat ging er mis:** jelly-leon-clients: de bouwplugin zette tijdens een proef zelf een extra platform in de gedeelde SDK. (Bron: R `review:jlc`.)
- **Hoe herken je het:** De map van de SDK is na een build groter of bevat een nieuw platform.
- **Wat doe je in plaats daarvan:** Meld het en laat het staan; verwijder niets uit de gedeelde SDK terwijl anderen bouwen.

### V-081 — Het foutmodel van de app kan de contractvelden niet dragen
- **Wat ging er mis:** media-guard-ultimate (Android): het foutmodel van de app draagt alleen een tekst en geen foutcode of trace-ID, terwijl Peil die bij een foutmelding wil tonen. (Bron: R `android:mg`; media-guard-ultimate `docs/adr/ADR-0018-peil-android-bouwkeuzes.md`.)
- **Hoe herken je het:** Een foutscherm toont alleen een zin.
- **Wat doe je in plaats daarvan:** Stel bij A-ONTWERP vast welke velden een foutmelding moet tonen en of het bestaande model die doorgeeft. Is dat niet zo, leg de keuze vast in een ADR in plaats van de velden te verzinnen.

### V-082 — Een ondertekeningssleutel staat bewust in de repo
- **Wat ging er mis:** media-guard-ultimate: zonder sleutelvariabelen ondertekent de build de app met een sleutel uit de repo. De gebruiker heeft besloten die openbare sideload-sleutel bewust te houden. Een echt niet-ondertekende app is niet gebouwd. (Bron: R `test:mg`, R `openbaarheidsscan`.)
- **Hoe herken je het:** Een scan op geheimen meldt een sleutelbestand in de Android-module.
- **Wat doe je in plaats daarvan:** Verwijder of vervang de sleutel niet zonder besluit van de gebruiker. Voeg geen nieuwe sleutels of wachtwoorden aan een repo toe.

---

## 7. Docker, images en schijf

### V-083 — "Alles als 568" gold niet voor het eerste proces
- **Wat ging er mis:** In meerdere alles-in-één-images bleef het eerste proces (PID 1) als root draaien; contractcorrectie R11 zegt dat ook PID 1 als 568 draait. In home-control-hub wisselt de bewaker nu naar 568 en zet zelf de beperking op nieuwe rechten, omdat het formulier van de Custom App die niet kan zetten. In media-source-optimizer draait PID 1 nog als root; dat hoort bij P3 (C1.3-MSO-03 tot en met C1.3-MSO-06). (Bron: R `review:contract`, R `hch:contract-1.2`, R `review-1.3:media-source-optimizer`; C, kop "Wijzigingslog 1.1 → 1.2".)
- **Hoe herken je het:** De rooktest controleert alleen de gebruiker van de hoofddienst en niet van elk proces in de container.
- **Wat doe je in plaats daarvan:** De rooktest leest de gebruiker van elk proces, inclusief PID 1 en de healthcheck, en start de container zoals het formulier dat doet (C §2.2).

### V-084 — De rooktest leest bestanden van 568 vanaf de host
- **Wat ging er mis:** home-control-hub: het testscript las bestanden van gebruiker 568 vanaf de host; dat kan alleen als root en faalde ook in twee GitHub-runs. (Bron: R `hch:sso`.)
- **Hoe herken je het:** "Permission denied" in een rooktest op een controle van rechten of eigenaar.
- **Wat doe je in plaats daarvan:** Controleer rechten en inhoud vanuit de container of via een wegwerpcontainer op hetzelfde volume. Ruim testmappen op dezelfde manier op.

### V-085 — Back-ups zijn voor iedereen leesbaar
- **Wat ging er mis:** jelly-leon-platform: de back-upmap stond op 0755 met dumps op 0644, terwijl de dumps de hele database bevatten. (Bron: R `review:jelly-leon-platform`.)
- **Hoe herken je het:** `stat` op de back-upmap en de dumps toont leesrechten voor anderen.
- **Wat doe je in plaats daarvan:** Zet `umask 077` vóór het schrijven; map 0700, bestanden 0600. Test dit in de rooktest.

### V-086 — Een versiecontrole weigert alleen de letterlijke waarde
- **Wat ging er mis:** jelly-leon-platform: het veld voor de doelversie weigerde alleen precies `latest`, niet een waarde die daarop eindigt of willekeurige tekst. (Bron: R `review:jelly-leon-platform`.)
- **Hoe herken je het:** De validatie vergelijkt met één verboden waarde.
- **Wat doe je in plaats daarvan:** Valideer op de toegestane vorm (versie of digest) in plaats van op een verboden waarde.

### V-087 — De poort is open voordat de dienst luistert
- **Wat ging er mis:** jelly-leon-platform: een CI-stap faalde omdat de doorstuurlaag van Docker de verbinding op de hostpoort al aannam voordat de dienst in de container luisterde. Een andere stap had een te krap tijdsbudget voor herverbinden (150 s, verhoogd naar 300 s). (Bron: R `review:plat`.)
- **Hoe herken je het:** "Poort is open" slaagt, de eerste echte aanroep faalt.
- **Wat doe je in plaats daarvan:** Wacht op een inhoudelijk antwoord van de dienst (een begroeting of een geslaagde gezondheidsroute), niet op een open poort.

### V-088 — Testimages blijven staan
- **Wat ging er mis:** media-guard-ultimate: na de tests stonden er images van samen ongeveer 7 GB; die zijn door de agent zelf verwijderd. (Bron: R `test:mg`.)
- **Hoe herken je het:** `docker images` toont images met een testnaam van een afgeronde taak.
- **Wat doe je in plaats daarvan:** Geef testimages een herkenbare naam per agent en verwijder ze op naam aan het eind van de taak (zie V-011). Bouw met een builder met geheugengrens en onder de docker-buildlock (O).

### V-089 — Een vast poolpad als standaard in ontwikkelbestanden
- **Wat ging er mis:** media-guard-ultimate: de compose voor ontwikkeling en CI gebruikte een vast pad op een pool als standaard. (Bron: R `review-1.3:media-guard-ultimate`.)
- **Hoe herken je het:** `grep -rn "/mnt/" deploy docker compose*` geeft treffers buiten documentatie met een plaatshouder.
- **Wat doe je in plaats daarvan:** Maak het pad een verplichte variabele zonder standaardwaarde en schrijf in documentatie `<pool>`. Compose is alleen voor ontwikkeling en CI, nooit een installatieweg (C §2.3 regel 4).

### V-090 — Zichtbaarheid van images en repos loopt uiteen
- **Wat ging er mis:** Bij de openbaarheidsscan waren zes images zonder aanmelden te downloaden terwijl alle repos privé waren; voor twee forks onder een copyleft-licentie stond de verplichte broncode daardoor nergens publiek. Omgekeerd gaf een vrijgegeven image van my_house anoniem "unauthorized". Voor de nieuwe repo van media-guard-ultimate staan de pakketrechten nog open bij de gebruiker. (Bron: R `openbaarheidsscan`, R `test:mh`; S, kop "Besluiten van de gebruiker na contract 1.3".)
- **Hoe herken je het:** Een anonieme `docker pull` geeft een andere uitkomst dan je verwacht.
- **Wat doe je in plaats daarvan:** Controleer per image of anoniem ophalen werkt voordat je het als installatiebewijs noemt. Publiceer geen release van media-guard-ultimate zolang de pakketrechten open staan (RV13). Pakketrechten wijzigen is een handeling van de gebruiker.

---

## 8. Beveiliging en executor

### V-091 — De executor had geen replaycache en geen grens voor chunked verzoeken
- **Wat ging er mis:** ai-server-manager: bij de onafhankelijke review van contract 1.2 ontbraken in de executor een blijvende replaycache op `jti`, een verplichte `Idempotency-Key`, de rol `admin` op ontkoppelen en een grens voor chunked verzoeken; een `iat` in de toekomst werd geaccepteerd. Alles is gerepareerd. (Bron: S, kop "Contract 1.2 — verwerkt in `PLATFORM_CONTRACTEN.md`"; R `review-1.2:ai-server-manager`.)
- **Hoe herken je het:** Een nieuwe muterende route op de executor heeft geen test met een herhaald token, een token uit de toekomst en een aanvraag zonder `Idempotency-Key`.
- **Wat doe je in plaats daarvan:** Elke nieuwe muterende route in P2 krijgt deze negatieve tests vóór de positieve (C §4.6, §4.7, §5, §8). R-VEILIG gaat ervan uit dat er een gat zit en probeert het aan te tonen.

### V-092 — Vóór de eerste koppeling kan iemand op het LAN de dienst aan een eigen "Hub" koppelen
- **Wat ging er mis:** Dit is een bekend restrisico van het koppelen via de statuspagina, en in jelly-leon-platform was het ook na de eerste koppeling nog mogelijk door een wedloop (zie V-044). Het contract beperkt het met een verplichte vingerafdruk, alleen vóór de eerste koppeling en een limiet van vijf pogingen per kwartier per bron. (Bron: R `review-1.2:jelly-leon-platform`, R `contract-1.2`; C §3.7.)
- **Hoe herken je het:** Een dienst is geïnstalleerd en nog niet gekoppeld, en de statuspagina is op het LAN bereikbaar.
- **Wat doe je in plaats daarvan:** Bouw geen extra koppelweg. Houd de beperkingen van C §3.7 in stand en test ze. Koppelen en roteren zijn geen acties met een `action_id` (contractcorrectie R7).

### V-093 — Een foutmelding op de statuspagina komt uit de URL
- **Wat ging er mis:** zoeken-en-persoonlijke-ai: een foutmelding kwam uit een queryparameter zonder dat er een poging was gedaan; invoer werd afgekapt vóór de controle. De reviewer meldde dat dezelfde reparaties nodig waren in de statuspagina's van home-control-hub, appstore-en-fork, jelly-leon-platform en de executor. (Bron: R `review:zoek`.)
- **Hoe herken je het:** Open de statuspagina met een zelfgekozen queryparameter; verschijnt er een melding, dan is het fout.
- **Wat doe je in plaats daarvan:** Toon een melding alleen bij een echte, door de server bijgehouden poging. Controleer invoer vóór enige bewerking. Een bevinding in één statuspagina loop je in alle statuspagina's na. Of dat in de vier andere overal is gebeurd is ONBEKEND - eerst vaststellen met: de negatieve proef hierboven per dienst.

### V-094 — Een geheim staat in een verzoeklog
- **Wat ging er mis:** jelly-leon-platform: de simulator van de monitor bewaarde het pad van een push-aanroep letterlijk in zijn verzoeklog, inclusief het token in dat pad. (Bron: R `review:plat`.)
- **Hoe herken je het:** Een token of sleutel staat in een URL-pad of queryparameter, en er is een log of testrapport dat URL's bewaart.
- **Wat doe je in plaats daarvan:** Maskeer geheimen in elk log, ook in simulators en testuitvoer. De rooktest zoekt in de log naar de gebruikte testgeheimen.

### V-095 — Een bronpad ontsnapt via een symbolische koppeling
- **Wat ging er mis:** zoeken-en-persoonlijke-ai: een bronpad onder de leeswortel dat via een symbolische koppeling in een bovenliggende map liep, werd geaccepteerd; de voorvertoning las dan een share die niet geselecteerd was (werkpakket B07-001). De controle keek alleen naar het opgeloste bronpad zelf. (Bron: R `review:zoeken-en-persoonlijke-ai`.)
- **Hoe herken je het:** De padcontrole kijkt alleen naar het eindpunt en niet naar elk onderdeel van het pad.
- **Wat doe je in plaats daarvan:** Weiger een pad waarin enig onderdeel een symbolische koppeling is, bij het kiezen én opnieuw bij het lezen (de map kan na het kiezen vervangen zijn). Test met een koppeling in een bovenliggende map.

### V-096 — Documentatie beschrijft een installatie- of herstelweg via de terminal
- **Wat ging er mis:** media-source-optimizer: de installatiedocumentatie adviseerde "Install via YAML" en een terminal voor terugdraaien, tegen de vaste keuze van de gebruiker en C §2.3 regel 4 in; de conformiteitslijst noemde de repo op dat punt toch conform. my_house wordt nu nog als compose-app geïnstalleerd, met een installatiescript dat root eist; de alles-in-één Custom App is C1.3-MH-03 en hoort bij P3. (Bron: V `## media-source-optimizer`, `### review-1.3:media-source-optimizer`; R `1.3:my_house`; `<WERKMAP>/my_house/README.md`.)
- **Hoe herken je het:** `grep -rn -i "install via yaml\|docker exec\|docker compose up" README* docs deploy` geeft treffers in installatie- of herstelstappen.
- **Wat doe je in plaats daarvan:** Beschrijf uitsluitend het standaardformulier van de Custom App. Herstel en terugdraaien lopen via het formulier of via de eigen app, niet via een terminal op de NAS.

### V-097 — Gegevens van de ontwikkelmachine staan in een publieke repo
- **Wat ging er mis:** ai-server-manager: overdrachtsdocumenten vermeldden het pad van de werkmap en eigenschappen van de ontwikkelmachine. In my_house en media-source-optimizer stonden hulpscripts voor schermafdrukken en review met absolute paden van de ontwikkelmachine in de repo. (Bron: R `openbaarheidsscan`, R `prep:mh`, R `prep:mso`.)
- **Hoe herken je het:** `grep -rn "/home/" docs tools tests` geeft treffers.
- **Wat doe je in plaats daarvan:** Schrijf `<WERKMAP>` en relatieve paden. Machine-eigen notities horen onder `<WERKMAP>/.lokaal/`, niet in een repo. De scan staat in `<WERKMAP>/.lokaal/scan/OPENBAARHEIDSSCAN.md`.

---

## 9. Eerlijkheid en bewijs

### V-098 — "Sim-geslaagd" terwijl een deel van de acceptatie niet is uitgevoerd
- **Wat ging er mis:** jelly-leon: de testrijen JLT-60, JLT-63 en JLT-70 eisen uitvoering met een echte client (emulator, stock-web). De bouwers hadden dat niet gedaan en toch stonden de rijen op "Sim-geslaagd". Het contract kent geen waarde voor "deels geslaagd"; de reviewer zette ze op "Sim-getest" met uitleg. (Bron: R `review:jelly-leon` fase Review.)
- **Hoe herken je het:** Leg de acceptatietekst van de rij naast het bewijs: elk onderdeel van de acceptatie moet een eigen bewijsregel hebben.
- **Wat doe je in plaats daarvan:** Is een deel niet uitgevoerd, dan krijgt de hele rij de lagere waarde en noemt de opmerking wat ontbreekt (C §11). R-EERLIJK controleert dit per rij, niet per repo.

### V-099 — Een eigen simulator als bewijs voor iets dat nog niet bestaat
- **Wat ging er mis:** jelly-leon: bij JLT-73 hangt het MediaGuard-deel van de acceptatie af van twee leveringen van media-guard-ultimate (Δ-MG-DUAL en Δ-MG-AUTH) die nog niet bestaan. Een eigen MediaGuard-simulator als bewijs zou gesimuleerd succes zijn; de reviewer heeft dat geweigerd. Beide leveringen zijn exitcriterium van P4-0 (C1.3-MGU-04). (Bron: R `review:jelly-leon` fase Review; V `## jelly-leon`, `### golf0:emby`; V `## ai-server-manager`, `### contract-1.3`.)
- **Hoe herken je het:** De simulator is geschreven door dezelfde agent die het bewijs levert, en de echte tegenpartij heeft de functie nog niet.
- **Wat doe je in plaats daarvan:** Laat de rij open met de reden en de naam van de ontbrekende levering. Plan de levering in de andere repo eerst, met een contracttest die beide kanten draaien.

### V-100 — De aanduiding "NIET GEVALIDEERD" ontbreekt
- **Wat ging er mis:** jelly-leon-web: I24-24-01 miste "NIET GEVALIDEERD (hardware)" en I06-06-07 miste "NIET GEVALIDEERD (echte NAS)"; de waarden beloofden daardoor meer dan er gemeten was. (Bron: R `review:jlw`.)
- **Hoe herken je het:** Een rij die volgens haar tekst een echte NAS, hardware, account of Mac vraagt, heeft een validatiewaarde zonder die aanduiding.
- **Wat doe je in plaats daarvan:** Bepaal per rij eerst wat de acceptatie echt vraagt en zet de aanduiding erbij, ook als alle simulatortests slagen. De bewijscontrole van de repo moet dit afdwingen en mag niet stil slagen (zie V-027).

### V-101 — EVIDENCE verwijst naar tests die niet meer bestaan
- **Wat ging er mis:** home-control-hub: EVIDENCE wees naar zeven tests die niet meer bestonden en bevatte een niet-ingevulde sjabloonplek, onder meer bij EX16 en B13-002. (Bron: R `review:hch` fase Review, na contract 1.2.)
- **Hoe herken je het:** Zoek elke testnaam en elk pad uit EVIDENCE op in de repo; een verwijzing zonder treffer is fout.
- **Wat doe je in plaats daarvan:** Een test in de repo bewaakt dat elke verwijzing in EVIDENCE bestaat. Wie een test hernoemt of verwijdert, werkt EVIDENCE in dezelfde commit bij. Voorbeeld van zo'n bewaking: `<WERKMAP>/ai-server-manager/apps/api/tests/unit/test_evidence_contract.py`.

### V-102 — Een testtelling als bewijs voor iets dat geen test controleert
- **Wat ging er mis:** media-source-optimizer: EVIDENCE noemde bij B05-008 "e2e 109/109" als bewijs voor een gedrag dat geen enkele test controleerde. De reviewer schreef de ontbrekende test; B05-001 en B05-008 blijven "Bezig". (Bron: R `review:mso`.)
- **Hoe herken je het:** Het bewijs is een totaaltelling zonder de naam van de test die juist dit gedrag aantoont.
- **Wat doe je in plaats daarvan:** Noem per bewering de test die haar aantoont. Een totaaltelling is alleen bewijs dat de suite draait.

### V-103 — Bewijs voor een onderdeel dat niet bestaat
- **Wat ging er mis:** jelly-leon-platform: I08-08-03 stond op "Sim-getest", maar er bestond geen monitorplan met verwachte status en time-out per endpoint. De rij is teruggezet naar "NIET GEVALIDEERD (echte NAS)" met reden. (Bron: R `review:plat`; jelly-leon-platform `docs/adr/ADR-0018-review-p1.md`.)
- **Hoe herken je het:** De rij noemt een product (een plan, een rapport, een route) dat je in de repo niet kunt aanwijzen.
- **Wat doe je in plaats daarvan:** Wijs bij elke rij het bestand of de route aan die het gevraagde levert. Kan dat niet, dan is de rij niet getest.

### V-104 — Verouderde tekst in bewijs en documentatie
- **Wat ging er mis:** appstore-en-fork: bij EX16 stond een blokkade die al was opgelost. ai-server-manager: documentatie en rooktestmeldingen verwezen nog naar contract 1.2 nadat 1.3 was toegepast. my_house: EVIDENCE zei bij B06-001 "niet gepubliceerd", terwijl de release bestond. (Bron: R `review-1.2:appstore-en-fork`, R `review-1.3:ai-server-manager`, R `1.3:my_house`.)
- **Hoe herken je het:** `grep -rn "contract 1\.[0-9]" README* docs deploy` toont een oudere versie dan `contracts` in het contract; een blokkade noemt iets dat inmiddels gepusht is.
- **Wat doe je in plaats daarvan:** Meet de stand opnieuw (bijvoorbeeld de lijst van releases) voordat je een blokkade of status overneemt uit een eerdere ronde. R-EERLIJK leest blokkades na op actualiteit.

### V-105 — Alleen tegen de simulator, omdat de echte Hub het nog niet kan
- **Wat ging er mis:** appstore-en-fork: de import van de inventaris (C1.3-ASF-09) is alleen tegen de simulator uitgevoerd. De echte Hub had de benodigde scope en de paginering over een momentopname toen nog niet (C1.3-ASM-07 en C1.3-ASM-08); tegen de echte Hub meldt de import eerlijk `capability_unavailable`. De vorm van die paginering lag bovendien niet vast en is aangenomen. (Bron: R `1.3:appstore-en-fork`; V `## appstore-en-fork`, `### 1.3:appstore-en-fork` en `### review-1.3:appstore-en-fork`.)
- **Hoe herken je het:** De afnemer en de aanbieder van een route zijn in verschillende rondes gebouwd, en geen test draait ze samen.
- **Wat doe je in plaats daarvan:** Zodra beide kanten bestaan, draait een interop-test ze samen (zie V-001). Tot dan staat in EVIDENCE dat het alleen tegen de simulator is getest en welke aanname is gedaan. Bij het schrijven van dit bestand kwam `snapshot_changed` in beide repos voor; de twee vormen zijn niet met elkaar vergeleken. Of de Hub de aangenomen vorm volgt is ONBEKEND - eerst vaststellen met: `grep -rn "snapshot_changed" <WERKMAP>/ai-server-manager/apps <WERKMAP>/appstore-en-fork/apps`.

### V-106 — De conformiteitslijst zegt "conform" en mist open punten
- **Wat ging er mis:** media-source-optimizer: de conformiteitslijst van contract 1.3 noemde de alles-in-één image conform, maar miste een nog open punt uit contract 1.2 en de vaste keuze voor basisimages op een digest: de Dockerfiles gebruikten nog tags, waaronder een zwevende. (Bron: V `## media-source-optimizer`, `### review-1.3:media-source-optimizer` en `### review:mso`.)
- **Hoe herken je het:** `grep -n "_IMAGE=" <WERKMAP>/media-source-optimizer/deploy/allinone/Dockerfile <WERKMAP>/media-source-optimizer/apps/*/Dockerfile` toont waarden zonder `@sha256:`.
- **Wat doe je in plaats daarvan:** Lees `<WERKMAP>/ai-server-manager/docs/platform-v2/CONTRACT_1.3_CONFORMITEIT.md` als startpunt, niet als bewijs. Controleer de vaste keuzes van C §1 zelf in de repo voordat je "conform" overneemt.

### V-107 — Werk zonder ID in de Excel
- **Wat ging er mis:** zoeken-en-persoonlijke-ai: voor de statuspagina en de bijbehorende reviewronde bestond geen eigen Excel-ID. De reviewer heeft geen ID verzonnen en het bewijs bij EX16 gezet. In ai-server-manager kenden het samenvoegscript en de bewijstest de contract-ID's (C1.3-…) eerst niet (C1.3-ASM-15). (Bron: R `review:zoek`; V `## ai-server-manager`, `### contract-1.3`.)
- **Hoe herken je het:** Je wilt bewijs vastleggen en vindt geen passend ID in de lijst van ID's.
- **Wat doe je in plaats daarvan:** Verzin geen ID. Hang het bewijs aan het best passende bestaande ID en meld het ontbreken aan de regisseur. Contract- en reviewregels gebruiken de vorm die C §11 toestaat.

### V-108 — De Excel loopt achter op EVIDENCE
- **Wat ging er mis:** In vrijwel elke ronde meldden agents dat de Excel-afvinklijst niet opnieuw was samengevoegd; dat moet voor alle repos samen, vanuit ai-server-manager. Losse repos kunnen dat niet zelf. (Bron: V `## zoeken-en-persoonlijke-ai`, `### 1.3:zoeken-en-persoonlijke-ai`; V `## home-control-hub`, `### review-1.3:home-control-hub`; V `## ai-server-manager`, `### review:contract-1.3`.)
- **Hoe herken je het:** EVIDENCE.json in een repo is nieuwer dan de Excel.
- **Wat doe je in plaats daarvan:** Samenvoegen is een taak van de regisseur aan het eind van een golf, met `<WERKMAP>/ai-server-manager/tools/excel/update_excel.py`. Subagents wijzigen de Excel niet zelf (zie V-016).

---

## 10. HARDE EIS en migraties

De HARDE EIS staat in C §2.3 regel 7 en in contractcorrectie RV2. Lees die eerst.

### V-109 — De overnametool had per vergissing in Emby kunnen schrijven
- **Wat ging er mis:** jelly-leon: Emby accepteert ook de aanmeldheader van Jellyfin (gemeten met een wegwerp-Emby). Wees het doeladres per vergissing naar Emby, dan hield alleen toeval (verschillen in de API) schrijfacties zoals het aanmaken van gebruikers tegen. (Bron: R `review:jelly-leon` fase Review.)
- **Hoe herken je het:** Een tool met een bron en een doel controleert het doel niet voordat hij schrijft.
- **Wat doe je in plaats daarvan:** De tool leest eerst, zonder sleutel, de openbare systeeminformatie van het doel en gaat alleen door als het doel zich als Jellyfin-server meldt. Bij hetzelfde adres of dezelfde server-ID als de bron stopt hij. Zie `<WERKMAP>/jelly-leon/tools/emby-overname/` en `<WERKMAP>/jelly-leon/docs/platform-v2/OVERNAME_EMBY.md`. Houd deze controle bij elke wijziging in stand en test hem met het doel op Emby gericht.

### V-110 — Een leesverzoek laat Emby schrijven
- **Wat ging er mis:** jelly-leon: de eerste opvraging van afspeelinformatie voor een bestand dat Emby nog niet had geanalyseerd, liet Emby dat bestand analyseren en het resultaat opslaan. De proef "export vóór en na identiek" haalde daardoor 61 van 62 controles. (Bron: R `review:jelly-leon` fase Review.)
- **Hoe herken je het:** De vergelijking vóór en na de proef verschilt terwijl de tool alleen leesverzoeken deed.
- **Wat doe je in plaats daarvan:** Neem "alleen lezen" niet aan op grond van de HTTP-methode. Meet met een export vóór en na en met een loggende proxy (`<WERKMAP>/jelly-leon/tools/emby-overname/e2e/loggende_proxy.py`). De tool vraagt geen afspeelinformatie op voor een bestand dat nog niet is geanalyseerd.

### V-111 — De proef verandert zelf de kijkgegevens
- **Wat ging er mis:** jelly-leon-web: afspelen in de browser tijdens de upgradeproef kon de kijkgegevens zelf veranderen (aantal keren gezien, laatst gezien). De negatieve proef meldde dan onterecht schade, afhankelijk van timing. (Bron: R `review:jelly-leon-web`.)
- **Hoe herken je het:** Een voor/na-vergelijking faalt soms, en het verschil zit in velden die de testclient zelf bijwerkt.
- **Wat doe je in plaats daarvan:** Onderschep in zo'n proef de afspeelmeldingen van de testclient, of meet vóór de client iets afspeelt. Een proef die kijkgegevens vergelijkt, mag ze zelf niet aanraken.

### V-112 — Een onderdeel van de HARDE EIS wordt niet echt gemeten
- **Wat ging er mis:** jelly-leon-web: "onthouden spoorkeuzes" was niet gedekt: het testbestand had één spoor en alleen de taalvoorkeur werd vergeleken. "Hervatten op het juiste punt" werd alleen gemeten als "de knop Hervatten is zichtbaar". (Bron: R `review:jelly-leon-web`.)
- **Hoe herken je het:** Zet de onderdelen van de HARDE EIS (gezien, hervatpunten, favorieten, beoordelingen, spoorkeuzes, gebruikers, MediaGuard-voortgang) onder elkaar en zoek per onderdeel de meting. Een onderdeel zonder eigen meting, of met testgegevens waarin het niet kan verschillen, is niet gedekt.
- **Wat doe je in plaats daarvan:** Testgegevens moeten per onderdeel een verschil kunnen tonen (meer sporen, meer gebruikers, een hervatpunt met een waarde). Meet de waarde zelf, niet de aanwezigheid van een knop. R-HARDE-EIS loopt deze lijst af.

### V-113 — Spoorkeuzes kunnen niet via een officiële route worden overgezet
- **Wat ging er mis:** jelly-leon: Jellyfin 12.4 heeft geen officiële route om onthouden spoorkeuzes te zetten; het kan alleen via afspeelrapportage en die wijzigt ook de kijkgegevens. Dat onderdeel van B03-015 is met de toegestane routes niet uitvoerbaar. Gekozen: elk verschil komt op de afhandellijst. (Bron: R `golf0:emby`; V `## jelly-leon`, `### golf0:emby`.)
- **Hoe herken je het:** Een onderdeel van de overname vraagt een schrijfactie waarvoor de server geen eigen route heeft.
- **Wat doe je in plaats daarvan:** Bouw geen omweg die andere kijkgegevens wijzigt. Meld het verschil in het voor/na-rapport en laat de gebruiker akkoord geven. Een eigen pluginroute vraagt eerst een besluit van de gebruiker.

### V-114 — Emby gedraagt zich anders dan aangenomen
- **Wat ging er mis:** jelly-leon: in echte containers bleek dat Emby "aantal keren gezien" en "laatst gezien" in lijsten alleen teruggeeft als die velden uitdrukkelijk worden gevraagd, films met hetzelfde externe ID bundelt tot één item met versies, en na een "vind ik leuk" geen beoordeling teruggeeft. (Bron: R `golf0:emby`.)
- **Hoe herken je het:** Een export bevat minder velden of minder items dan de bibliotheek.
- **Wat doe je in plaats daarvan:** Neem geen gedrag van Emby aan uit de documentatie van Jellyfin. Meet tegen een wegwerp-Emby op een vaste digest en leg vast wat gemeten is. De echte Emby van de gebruiker wordt nooit als testdoel gebruikt.

### V-115 — De acceptatie van een werkpakket mist delen van de HARDE EIS
- **Wat ging er mis:** ai-server-manager (plan voor B03): in de acceptatie van B03-015 ontbraken het akkoord van de gebruiker op elk verschil (ook door upstream-migraties), "de bestaande installatie blijft ongewijzigd als terugval" en het upgradebewijs per MediaGuard-release. (Bron: R `controle`, de rij na het verwerken van het B03-plan.)
- **Hoe herken je het:** De acceptatietekst van een werkpakket dat mediaserver of MediaGuard raakt, begint niet met de HARDE EIS.
- **Wat doe je in plaats daarvan:** Elk werkpakket dat een mediaserver, een migratie of MediaGuard raakt, neemt de HARDE EIS letterlijk op in de acceptatie. R-HARDE-EIS keurt af als een deel ontbreekt.

### V-116 — Het upgradebewijs meldt "niets verloren" over een lege meting
- **Wat ging er mis:** media-guard-ultimate: een lege of halve meting vóór de upgrade gaf "niets verloren", omdat er dan niets werd vergeleken. (Bron: R `review-1.3:media-guard-ultimate`.)
- **Hoe herken je het:** Het rapport noemt geen aantallen per tabel, of de aantallen zijn nul.
- **Wat doe je in plaats daarvan:** De poort is rood als een database ontbreekt, als een tabel minder rijen heeft dan de testgegevens, of als een verwachte database leeg is. Bewijs dat de poort kan falen met een migratie die opzettelijk een rij wist (zie V-003). Zie `<WERKMAP>/media-guard-ultimate/scripts/upgradebewijs.py` en `<WERKMAP>/media-guard-ultimate/apps/core/tests/test_upgradebewijs.py`.

### V-117 — Het upgradebewijs vergelijkt met de verkeerde vorige release
- **Wat ging er mis:** media-guard-ultimate: niets controleerde of het bestand met de vorige release echt de direct vorige gepubliceerde release noemt. Er is een stap toegevoegd die dat tegen de registry controleert. (Bron: R `review-1.3:media-guard-ultimate`.)
- **Hoe herken je het:** `<WERKMAP>/media-guard-ultimate/deploy/upgradebewijs/vorige-release.json` noemt een andere versie dan de laatst gepubliceerde.
- **Wat doe je in plaats daarvan:** Werk dat bestand na elke release bij naar de nieuwe versie en digest. Zonder upgradebewijs geen release en geen update via de Hub of de executor (RV2).

### V-118 — Het plan veronderstelt een terminal bij de overname
- **Wat ging er mis:** jelly-leon: het plan noemde de overname een losse tool, maar zei niet wie die op de NAS start, terwijl de gebruiker geen terminal gebruikt. De overname-assistent in het beheer van Jelly Leon die de tool start en rapport, afhandellijst en akkoord toont, bestaat nog niet. (Bron: V `## jelly-leon`, `### golf0:emby`.)
- **Hoe herken je het:** Een stap in een overstap- of herstelbeschrijving begint met een commando.
- **Wat doe je in plaats daarvan:** Tot de assistent er is, draait de tool alleen als proef in test en CI. Het akkoord van de gebruiker loopt via een scherm, niet via een bestand of een commando.

### V-119 — "Nooit schrijven in Emby" te breed of te smal gelezen
- **Wat ging er mis:** Het contract sprak zichzelf tegen: MediaGuard heeft een bestaande koppeling met Emby die schrijft (bibliotheek bijwerken, afspeeltest, sessies). De onafhankelijke review legde vast dat het verbod geldt voor de Hub, de executor, de AI, Jelly Leon en de overnametool, dat de bestaande koppeling van MediaGuard blijft werken en dat er geen nieuwe schrijfroute bij komt (RV1). Ook mag er via de Hub-adapter van MediaGuard geen kijkgedrag in de Hub komen (RV3). (Bron: C, kop "Correcties uit de onafhankelijke review".)
- **Hoe herken je het:** Een wijziging "repareert" de Emby-koppeling van MediaGuard, of voegt een veld met sessies of kijkgedrag toe aan wat de Hub leest.
- **Wat doe je in plaats daarvan:** Laat de bestaande koppeling van MediaGuard ongemoeid. Nieuwe onderdelen lezen alleen. De Hub-adapter volgt de witte lijst van velden uit RV3.

---

## 11. Per repo

Deze groep bevat alleen wat niet al in een eerdere groep staat. De tabel aan het eind verwijst per repo naar alle valkuilen die daar hebben gespeeld. Voor media-guard-ultimate staat alles in de groepen 1 tot en met 10; die repo heeft hier geen eigen valkuil.

### V-120 — ai-server-manager: de Hub-UI toont bij een verouderde meting alles als "Verouderd"
- **Wat ging er mis:** ai-server-manager: bij een verouderde meting moeten de toestanden "Beperkt" en "Storing" blijven staan met de tijd van de laatste meting. De Hub-UI toonde alles als "Verouderd". Dit staat open onder C1.3-ALG-05. Het tonen van een geadopteerde app als "Geïmporteerd" in de catalogus (rest van C1.3-ASM-16) wacht eveneens op de ontwerpstap. (Bron: V `## ai-server-manager`, `### 1.3:ai-server-manager` en `### review-1.3:ai-server-manager`.)
- **Hoe herken je het:** Zet in de teststack een dienst op "Storing" en laat de meting verlopen; verdwijnt "Storing" uit beeld, dan is het fout.
- **Wat doe je in plaats daarvan:** Dit is UI-werk: eerst A-ONTWERP volgens Peil, dan bouwen, dan R-ONTWERP opnieuw. De backend levert de laatste bekende toestand al mee (`extra.laatste_status`); verzin geen eigen veld. Zie ook V-051.

### V-121 — ai-server-manager en home-control-hub: hernoemde vaste namen blijven bij een afnemer staan
- **Wat ging er mis:** home-control-hub heeft de vaste namen van de gezondheidscontroles gewijzigd naar `hub_link` en `jobs`; de oude namen `hub_koppeling` en `outbox` bestaan niet meer. De Hub moest daarop worden aangepast. In ai-server-manager gelden daarnaast overgangsnamen die in de release na 0.1.x vervallen. (Bron: V `## home-control-hub`, `### 1.3:home-control-hub`; V `## ai-server-manager`, `### 1.3:ai-server-manager`.)
- **Hoe herken je het:** `grep -rn "hub_koppeling" <WERKMAP>/*/apps` geeft treffers buiten migraties en wijzigingslogs.
- **Wat doe je in plaats daarvan:** Een vaste naam uit C §6 of §7 wijzig je nooit in één repo. Zoek bij elke naamswijziging in alle repos naar de oude naam en neem de afnemers mee in dezelfde golf.

### V-122 — home-control-hub: noodtoegang vanaf een CGNAT-adres vervalt bij de update
- **Wat ging er mis:** home-control-hub: de gebruiker heeft besloten dat de noodlogin alleen vanaf het thuisnetwerk werkt en dat het CGNAT-bereik niet als privé telt. Een bestaande noodtoegang met dat bereik geeft na de update geen toegang meer, totdat een beheerder het bewust opnieuw toestaat. De herstelstatus meldt dit. (Bron: V `## home-control-hub`, `### 1.3:home-control-hub`; S, kop "Besluiten van de gebruiker na contract 1.3 (2026-11-10)".)
- **Hoe herken je het:** Een test of een handleiding gaat ervan uit dat noodtoegang via een VPN-adres vanzelf werkt.
- **Wat doe je in plaats daarvan:** Behandel dit als bedoeld gedrag en repareer het niet weg. Zie `<WERKMAP>/home-control-hub/apps/api/alembic/versions/0004_contract_1_3_cgnat.py`. Beschrijf in documentatie voor de gebruiker dat opnieuw toestaan een bewuste handeling is.

### V-123 — appstore-en-fork: een geheime waarde van een catalogusapp kan nog nergens heen
- **Wat ging er mis:** appstore-en-fork: de verwijzing naar de kluis voor geheime waarden van catalogusapps (C1.3-ASF-14, samen met C1.3-ASM-18) hoort bij P2 en is niet gebouwd. Tot dan weigert de vertaling een geheime waarde, zodat er nooit een geheim in een payload staat. (Bron: V `## appstore-en-fork`, `### 1.3:appstore-en-fork` en `### review-1.3:appstore-en-fork`.)
- **Hoe herken je het:** Een catalogusapp met een geheime instelling kan niet worden geïnstalleerd en de vertaling geeft een weigering.
- **Wat doe je in plaats daarvan:** Omzeil de weigering niet door de waarde als gewone instelling door te geven. Bouw eerst de verwijzing naar de kluis aan beide kanten.

### V-124 — jelly-leon-platform: planroutes gaven 501 en twee acceptatiecriteria waren niet aangetoond
- **Wat ging er mis:** jelly-leon-platform: na contract 1.2 gaven de planroutes van de lifecycle nog 501 en waren de acceptatiecriteria van B08-003 (een poortconflict of ontbrekende afhankelijkheid blokkeert de uitrol) en B08-006 niet aangetoond. De conformiteitstests tegen de echte Hub draaien alleen lokaal, niet in CI. (Bron: V `## jelly-leon-platform`, `### 1.2:jelly-leon-platform` en `### review-1.2:jelly-leon-platform`.) Stand op 2026-11-11 (gezien in de repo, niet gereviewd): ronde 3 heeft B08-003 en B08-004 gebouwd en gepusht, met de negatieve tests `test_poortconflict_blokkeert_de_installatie` en `test_ontbrekende_vereiste_afhankelijkheid_blokkeert_de_installatie` in `<WERKMAP>/jelly-leon-platform/apps/api/tests/unit/test_planner.py`; de review daarvan is afgebroken (`<WERKMAP>/.lokaal/plan/STAND_RONDE3.md`). Nog 501: alleen `/plans/uninstall/preview` en `/plans/move/preview` (B08-006; `_P2` in `apps/api/src/lifecycle/api_lifecycle.py`).
- **Hoe herken je het:** EVIDENCE noemt B08-003 of B08-006 met een validatiewaarde, maar er is geen test die een poortconflict of een ontbrekende afhankelijkheid aanbiedt; of een route geeft nog 501 terwijl EVIDENCE het werkpakket als gebouwd noemt.
- **Wat doe je in plaats daarvan:** Bouw B08-003 niet opnieuw: controleer eerst met `git -C <WERKMAP>/jelly-leon-platform log --oneline -10` en de twee tests hierboven wat er al staat. B08-006 bouwt voort op `<WERKMAP>/jelly-leon-platform/apps/api/src/lifecycle/custom_app.py`, met eerst de negatieve tests. Draai `<WERKMAP>/jelly-leon-platform/e2e/conformance/echte_hub.py` (`make test-conformance-hub`) na elke wijziging aan de Hub.

### V-125 — zoeken-en-persoonlijke-ai: bladeren door zoekresultaten volgt de momentopname-regel nog niet
- **Wat ging er mis:** zoeken-en-persoonlijke-ai: de regel voor bladeren over een momentopname (C §5) geldt ook voor zoekresultaten, maar de conformiteitslijst noemde dat niet en de zoekroute gebruikt een cursor op basis van een verschuiving, zonder `snapshot_id`. Het is bewust niet gebouwd: zonder de ingest (B07-002) is de index in productie leeg en kan hij tussen twee pagina's niet veranderen. Het hoort bij P5, samen met B07-002 en B07-003. C1.3-ZPA-14 hoort ook bij P5, na besluit BG-06. (Bron: V `## zoeken-en-persoonlijke-ai`, `### review-1.3:zoeken-en-persoonlijke-ai` en `### 1.3:zoeken-en-persoonlijke-ai`; zoeken-en-persoonlijke-ai `docs/adr/ADR-0017-qa-contract-1-3.md`.)
- **Hoe herken je het:** De ingest wordt gebouwd en de zoekroute blijft ongewijzigd.
- **Wat doe je in plaats daarvan:** Neem de momentopname mee in hetzelfde werkpakket als de ingest. Begin niet aan C1.3-ZPA-14 voordat BG-06 genomen is.

### V-126 — jelly-leon en jelly-leon-web: de workflow voor bijwerken vanaf upstream heeft nog nooit op GitHub gedraaid
- **Wat ging er mis:** jelly-leon en jelly-leon-web: geplande en handmatige runs starten alleen vanaf de standaardbranch, en het pushen van een sync-branch vraagt een token waarover het besluit nog open staat (zie V-020). De standaardbranch van beide repos bevatte bij de openbaarheidsscan alleen de eerste commit, zonder licentie en zonder vermelding van upstream. (Bron: V `## jelly-leon`, `### p0:jelly-leon`; V `## jelly-leon-web`, `### jlw:contract-1.2`; R `openbaarheidsscan`.)
- **Hoe herken je het:** De workflow staat in de repo en heeft geen enkele run.
- **Wat doe je in plaats daarvan:** Noem deze workflow niet als bewijs. Het bijwerken is alleen lokaal beproefd. Samenvoegen naar de standaardbranch is een besluit van de gebruiker (geen PR's zonder te vragen).

### V-127 — jelly-leon: de overnameproef draaide tegen een andere versie dan de gebruiker heeft
- **Wat ging er mis:** jelly-leon: JLT-70 tot en met JLT-73 moeten worden herhaald tegen de 12-versie van Jelly Leon en daarna met de Emby-versie die D07 op de NAS meet, op een vaste digest. Het clientdeel van JLT-70 is alleen op protocolniveau nagebootst. (Bron: V `## jelly-leon`, `### golf0:emby`.)
- **Hoe herken je het:** Het proefrapport noemt een andere bron- of doelversie dan de inventaris van de NAS.
- **Wat doe je in plaats daarvan:** Leg in elk proefrapport de versies en digests van bron en doel vast. Herhaal de proef zodra D07 de echte versie heeft gemeten; tot dan blijft de rij "NIET GEVALIDEERD (echte NAS)".

### V-128 — jelly-leon-clients: wat alleen op echte apparaten kan, blijft open
- **Wat ging er mis:** jelly-leon-clients: installeren naast de officiële app, accounts, zoeksuggesties, back-up en casten met de eigen pakketnaam zijn niet op een emulator of echt apparaat getest (welke apparaten er zijn is onbekend tot D15). Swiftfin is NIET GEVALIDEERD: bouwen en testen vraagt een Mac met Xcode. (Bron: V `## jelly-leon-clients`, `### review:jlc` en `### jlc:contract-1.2`; S, kop "Besluiten van de gebruiker na contract 1.3 (2026-11-10)".)
- **Hoe herken je het:** Een rij over naast elkaar installeren, casten of Apple-apparaten heeft een andere waarde dan "NIET GEVALIDEERD (hardware)" of "NIET GEVALIDEERD (Mac/Xcode)".
- **Wat doe je in plaats daarvan:** Laat deze rijen op "Geblokkeerd" met wat nodig is. Een emulatorproef vraagt toegang tot hardwareversnelling (zie V-021).

### V-129 — media-source-optimizer: een route die niet bestaat antwoordt met HTTP 200
- **Wat ging er mis:** media-source-optimizer: `/readyz` geeft een nette "niet gevonden"-pagina met HTTP 200, omdat de route in deze versie niet bestaat. Een bewaking die alleen naar de statuscode kijkt, ziet de dienst dan als gereed. (Bron: R `review:mso`; media-source-optimizer `docs/platform-v2/DELTA_MATRIX.md`.)
- **Hoe herken je het:** Vraag een verzonnen pad op; komt er HTTP 200 terug, dan zegt de statuscode van geen enkele route iets.
- **Wat doe je in plaats daarvan:** Controleer in een gezondheidsproef de inhoud van het antwoord en niet alleen de statuscode (C §6), tot de connectorlaag van P3 de echte route levert.

### V-130 — my_house: de link "Terug naar de Hub" werkt pas met de alles-in-één image
- **Wat ging er mis:** my_house: de app kent het Hub-adres niet. Er is een optionele variabele `HUB_URL` toegevoegd, maar het veld in het formulier van de Custom App kan pas komen met de alles-in-één image (P3); de bestaande installatie is bewust niet aangepast. Het contract legt vast dat hier alleen `HUB_URL` wordt gezet, nooit een token of vingerafdruk, en dat het geen manifestparameter is (RV5). (Bron: V `## my_house`, `### ontwerp:mh` en `### web:mh`; C, kop "Correcties uit de onafhankelijke review".)
- **Hoe herken je het:** De link ontbreekt in de UI terwijl de Hub draait.
- **Wat doe je in plaats daarvan:** Dat is bedoeld gedrag zolang er geen geldig adres is. Voeg voor my_house geen koppelgegevens toe. De regel wordt bewaakt door `<WERKMAP>/my_house/apps/api/tests/platform_v2/test_hub_url_zonder_koppeling.py`.

---

## Per repo: lees deze valkuilen voor je begint

Voor iedereen, ongeacht de repo: groep 1 (V-001 tot en met V-021), groep 2 (V-022 tot en met V-038) en groep 9 (V-098 tot en met V-108). Wie iets doet aan de mediaserver, de overname uit Emby of MediaGuard leest ook groep 10 (V-109 tot en met V-119).

De kolom "Hier gebeurd of hier van toepassing" noemt de valkuilen waarin de repo zelf voorkomt, ook die uit de groepen voor iedereen. De kolom "Lees ook de hele groep" noemt de groepen die bij de techniek van de repo horen, ook als het geval in een andere repo speelde.

| Groep | Onderwerp | Valkuilen |
|---|---|---|
| 1 | Algemeen en werkwijze | V-001 tot en met V-021 |
| 2 | Git en CI | V-022 tot en met V-038 |
| 3 | Python, FastAPI en PostgreSQL | V-039 tot en met V-057 |
| 4 | Web, Next.js en Peil | V-058 tot en met V-067 |
| 5 | .NET en de Jellyfin-fork | V-068 tot en met V-074 |
| 6 | Android en clients | V-075 tot en met V-082 |
| 7 | Docker, images en schijf | V-083 tot en met V-090 |
| 8 | Beveiliging en executor | V-091 tot en met V-097 |
| 9 | Eerlijkheid en bewijs | V-098 tot en met V-108 |
| 10 | HARDE EIS en migraties | V-109 tot en met V-119 |
| 11 | Per repo | V-120 tot en met V-130 |

| Repo | Hier gebeurd of hier van toepassing | Lees ook de hele groep |
|---|---|---|
| ai-server-manager | V-007, V-008, V-010, V-017, V-018, V-019, V-025, V-027, V-031, V-039, V-041, V-047, V-050, V-051, V-055, V-060, V-061, V-062, V-091, V-097, V-099, V-101, V-104, V-105, V-106, V-107, V-108, V-115, V-119, V-120, V-121 | 3, 4, 7 en 8 |
| home-control-hub | V-001, V-004, V-005, V-017, V-028, V-030, V-045, V-047, V-051, V-061, V-083, V-084, V-093, V-101, V-108, V-121, V-122 | 3, 7 en 8; groep 4 voor de statuspagina |
| appstore-en-fork | V-004, V-017, V-039, V-044, V-045, V-046, V-047, V-050, V-052, V-054, V-058, V-093, V-104, V-105, V-123 | 3, 7 en 8; groep 4 voor de statuspagina |
| jelly-leon-platform | V-002, V-003, V-007, V-011, V-026, V-030, V-037, V-038, V-039, V-042, V-044, V-049, V-050, V-052, V-061, V-085, V-086, V-087, V-092, V-093, V-094, V-103, V-124 | 3, 7 en 8; groep 4 voor de statuspagina |
| jelly-leon | V-014, V-020, V-035, V-036, V-038, V-068, V-069, V-070, V-071, V-073, V-074, V-098, V-099, V-109, V-110, V-113, V-114, V-118, V-119, V-126, V-127 | 5, 7 en 10 |
| jelly-leon-web | V-009, V-014, V-020, V-027, V-070, V-100, V-111, V-112, V-126 | 5 en 10 (deze repo valt buiten Peil) |
| jelly-leon-clients | V-003, V-012, V-020, V-021, V-022, V-033, V-035, V-072, V-076, V-077, V-078, V-080, V-128 | 6 (deze repo valt buiten Peil) |
| zoeken-en-persoonlijke-ai | V-001, V-007, V-017, V-038, V-040, V-042, V-043, V-047, V-050, V-052, V-053, V-058, V-061, V-093, V-095, V-107, V-108, V-125 | 3, 7 en 8; groep 4 voor de statuspagina |
| media-guard-ultimate | V-003, V-008, V-013, V-018, V-021, V-023, V-032, V-057, V-058, V-059, V-063, V-064, V-066, V-067, V-079, V-081, V-082, V-088, V-089, V-090, V-099, V-116, V-117, V-119 | 3, 4, 6, 7, 8 en 10 |
| media-source-optimizer | V-004, V-005, V-009, V-010, V-013, V-023, V-028, V-030, V-034, V-036, V-048, V-057, V-058, V-063, V-065, V-066, V-083, V-096, V-097, V-102, V-106, V-129 | 3, 4, 7 en 8 |
| my_house | V-003, V-017, V-018, V-022, V-028, V-029, V-032, V-048, V-056, V-058, V-059, V-061, V-063, V-066, V-075, V-079, V-090, V-096, V-097, V-104, V-130 | 3, 4, 6 en 7 |
