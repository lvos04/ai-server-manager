
Je werkt mee aan een UITVOERINGSPLAN voor het project "TrueNAS Home Platform V2": 11 repos van github.com/lvos04 in /home/transcode/truenas-v2
(ai-server-manager, home-control-hub, appstore-en-fork, jelly-leon-platform, jelly-leon, jelly-leon-web, jelly-leon-clients,
zoeken-en-persoonlijke-ai, media-guard-ultimate, media-source-optimizer, my_house), allemaal op branch ccr-c133d7a0-kuz1cv.

DOEL VAN HET PLAN: de rest van het programma (fasen P2 t/m P6) wordt straks uitgevoerd ZONDER de Workflow-tool, door een
hoofdsessie (hierna: de REGISSEUR) met beperkte denkruimte ("medium") die ZO VEEL MOGELIJK werk uitbesteedt aan subagents via
de Agent-tool: tot 10 subagents tegelijk, op elk moment, met tot 8 bouwketens (grote bouwagents) naast elkaar. Dat is een
uitdrukkelijke wens van de gebruiker ("dit houdt de focus hoog en de kwaliteit beter"; "meer grote bouwagents, 8"). Subagents
mogen op een ander denkniveau en een ander model draaien dan de regisseur (niveaus N1-N5, zie het agentmodel). De kwaliteit mag niet dalen ten opzichte van de eerdere multi-agent-workflows. Dat lukt alleen als
het plan het denkwerk al gedaan heeft: kleine stappen, exacte bestandspaden en commando's, verwijzing naar de bron (pad + kop),
verplichte tests (ook negatieve), bekende valkuilen, een vaste agentketen per stap en duidelijke stopmomenten. Schrijf nooit
iets vaags als "implementeer X netjes"; schrijf wat, waar, in welke volgorde en hoe het te controleren is.
LEZERS: (1) de regisseur: bekwaam, kent het project NIET uit het hoofd, heeft weinig denkruimte. Hij bouwt zelf niet: hij kiest
stappen, stelt opdrachten samen uit vaste bouwstenen, controleert rapporten tegen de werkelijkheid, bewaakt gates en legt
besluiten via een keuzemenu aan de gebruiker voor. (2) de subagents: kennen het project niet, weten ALLEEN wat in hun opdracht
staat en wat ze daarna zelf lezen, kunnen de gebruiker niets vragen en draaien op het niveau dat de regisseur hun meegeeft
(N1-N5; bouwers en reviewers meestal N3). Schrijf zo dat ook een subagent op een lager niveau niets hoeft te raden. Een subagent krijgt een
vaste agentprompt uit AGENTEN.md plus een verwijzing naar ZIJN stap (planbestand + stap-ID) en leest die stap zelf. Elke stap
moet dus zonder toelichting te begrijpen zijn en door EEN bouwer-subagent in een keer af te ronden zijn (richtlijn: een repo,
een samenhangend onderdeel, hooguit ongeveer 8 bouwpunten, inclusief tests). Liever meer kleine stappen dan weinig grote.

AGENTMODEL (vast; gebruik exact deze namen; de uitgeschreven prompts komen in AGENTEN.md):
- A-VERKEN   verkenner, alleen lezen: maakt het stapdossier (wat staat er al, wat ontbreekt, welke bestanden, uitkomst van "Al gedaan?").
- A-ONTWERP  ontwerp-agent (Peil), voor elke UI-bouw.
- A-BOUW     bouwer: voert precies een stap uit in een repo (bouwen, tests, poort, EVIDENCE, commits, pull --rebase, push, CI).
- A-HERSTEL  hersteller: verifieert reviewbevindingen en herstelt ze in dezelfde repo.
- R-TECH, R-VEILIG, R-HARDE-EIS, R-MANIFEST, R-EERLIJK   reviewers, alleen lezen, frisse blik: ze krijgen de diff en de bron,
  niet de conclusie van de bouwer. R-EERLIJK controleert het rapport van de bouwer tegen de werkelijkheid (commits, push, CI,
  echte testuitvoer, EVIDENCE-statussen).
- R-ONTWERP  ontwerpreview na UI-bouw (mag uiterlijk, teksten en toegankelijkheid zelf herstellen en is dan de enige schrijver in die repo).
- A-GATE     onafhankelijke gatecontrole aan het einde van een fase of golf.
Vaste regels van het agentmodel: (1) hooguit 10 subagents tegelijk, alles meegeteld; (2) nooit twee SCHRIJVENDE agents tegelijk
in dezelfde repo (een keten per repo; lezers en reviewers mogen wel tegelijk); (3) verschillende repos zijn parallelle banen;
(4) zware commando's (image-builds, Gradle/Android, emulator, grote .NET-builds, containers met echte Emby/Jellyfin) lopen
machinebreed na elkaar via de bestaande flock-locks in <WERKMAP>/.lokaal/ (lees het blok OMGEVING in
/home/transcode/truenas-v2/.lokaal/workflows/ronde-3.js voor de beproefde afspraken) en de regisseur houdt hooguit 8 BOUWKETENS tegelijk open
(een keten = een stap in een repo, van A-VERKEN tot en met R-EERLIJK; zwaar of niet). Dat is de wens van de gebruiker; ronde 3
draaide op deze machine ook 8 repos tegelijk met dezelfde locks. VANGNET (14,5 GiB RAM is de echte grens): voor het starten van
een EXTRA keten met "Zwaar: ja" draait de regisseur "free -m"; staat onder "available" minder dan 3000 (MB), dan start hij
alleen ketens met "Zwaar: nee" of wacht hij. De plekken die overblijven binnen de 10 zijn voor reviewers en verkenners;
reviewers en herstellers van lopende ketens gaan ALTIJD voor op het openen van een nieuwe keten; (5) subagents starten zelf geen subagents; (6) een subagent die een besluit nodig heeft stopt en
meldt dat - alleen de regisseur vraagt de gebruiker, via een keuzemenu; (7) de regisseur neemt geen rapport voor waar aan
zonder de goedkope controles (git log/status, push, CI-run) en R-EERLIJK; (8) valt een subagent uit: eerst git status en
niet-gepushte commits in die repo bekijken, dan pas opnieuw starten met de melding dat er half werk kan staan; (9) de
regisseur geeft ELKE subagent uitdrukkelijk een NIVEAU mee (zie hieronder) en laat dat nooit weg.

NIVEAUS - denkniveau en model per subagent. De gebruiker staat uitdrukkelijk toe dat subagents een ander denkniveau en zelfs een
ander model krijgen, "met het topmodel alleen als het echt winst gaat opleveren". Het plan gebruikt daarvoor vijf neutrale
niveaus. Welk model en welk denkniveau bij elk niveau hoort staat NIET in het plan (regel: geen modelnamen in docs) maar in
/home/transcode/truenas-v2/.lokaal/plan/MODELKEUZE.md (buiten de repos; je mag het lezen, neem er GEEN modelnaam uit over) en in de startprompt van de
gebruiker. In het plan heet het zwaarste model alleen "het topmodel".
- N1 licht: snel model, laag denkniveau. Alleen puur zoek-, tel- en statuswerk dat direct na te controleren is.
- N2 standaard: het gewone sterke model, gemiddeld denkniveau. A-VERKEN (stapdossier) en A-BOUW voor kleine mechanische stappen
  (documentatie, configuratie, EVIDENCE bijwerken).
- N3 verdiept: hetzelfde model, hoog denkniveau. Standaard voor A-BOUW, A-HERSTEL, A-ONTWERP, R-TECH, R-MANIFEST, R-EERLIJK en R-ONTWERP.
- N4 scherp: hetzelfde model, zeer hoog denkniveau. Standaard voor R-VEILIG, R-HARDE-EIS en A-GATE; A-BOUW en A-HERSTEL bij
  stappen met moeilijkheid "hoog".
- N5 top: het topmodel. ALLEEN waar het aantoonbaar winst oplevert, en dat is uitsluitend in deze gevallen: (a) HARDE EIS met
  onomkeerbaar risico: de review (R-HARDE-EIS) van echte overname- of migratiecode voor kijkgeschiedenis, gebruikers of de
  MediaGuard-database; (b) de veiligheidskern: de review (R-VEILIG) van de kern van executor, policy, ondertekening of
  authenticatie zelf - niet van elke afnemer daarvan; (c) een stap met moeilijkheid "zeer hoog": een ingreep door meerdere
  subsystemen waar een fout pas laat zichtbaar wordt (A-BOUW op N5); (d) A-GATE aan het einde van een hele FASE (niet van een
  golf); (e) escalatie: een stap is op N3/N4 twee keer vastgelopen (tests niet groen te krijgen, of dezelfde bevinding blijft
  na herstel en herreview open) - dan EEN poging van A-HERSTEL op N5 voordat de regisseur de gebruiker een keuzemenu voorlegt.
  NOOIT N5 voor verkennen, routinebouw, UI, documentatie, manifesten, de eerlijkheidscontrole of Excel. Richtlijn voor
  schaarste: hooguit ongeveer een op de acht stappen heeft ergens N5 (escalaties niet meegeteld). Elke N5-inzet noteert de
  regisseur in VOORTGANG.md, tabel "Topmodel-inzet" (datum, stap, rol, reden, leverde het iets op: ja/nee en wat); leverde N5
  bij hetzelfde soort werk drie keer niets extra op, dan gaat dat soort werk terug naar N4.

ALLEEN LEZEN in de repos: geen builds, geen tests, geen docker, geen pakketinstallaties, geen git-commando's die iets wijzigen
(git log/show/status/diff/ls-files mag). Op dit moment draait een andere workflow ("ronde 3") die in de repos bouwt en commit; de
stand verandert dus terwijl je leest. Schrijf UITSLUITEND in /home/transcode/truenas-v2/.lokaal/plan/uit (map bestaat of maak hem met mkdir -p). Raak ai-factory nooit aan.

BRONNEN (lees wat je voor jouw deel nodig hebt; grote bestanden gericht met grep + Read met offset):
- /home/transcode/truenas-v2/ai-server-manager/docs/platform-v2/OVERDRACHT/OVERDRACHT_PROMPT.md (opdracht, regels, fasering §4) en /home/transcode/truenas-v2/ai-server-manager/docs/platform-v2/OVERDRACHT/STATUS.md (alle besluiten, stand).
- /home/transcode/truenas-v2/ai-server-manager/docs/platform-v2/PLATFORM_CONTRACTEN.md (bindend contract 1.3) en /home/transcode/truenas-v2/ai-server-manager/docs/platform-v2/CONTRACT_1.3_CONFORMITEIT.md (punten C1.3-<REPO>-nn met Moment NU/P2/P3/P4-0/P4/P5).
- /home/transcode/truenas-v2/ai-server-manager/docs/platform-v2/01_ARCHITECTUUR/ (o.a. 06_FASERING_EN_GATES.md met de gate-matrix), /home/transcode/truenas-v2/ai-server-manager/docs/platform-v2/02_BOUWPLANNEN/B01...B15,
  B03_FASERING.md, B03_BESLUITEN.md, B03_UNIVERSELE_MEDIASERVER.md (10.000+ regels: par.4 bouwfasen, par.8 12.x-basis, par.10
  gemeenschappelijke bouwstenen, F1...F6, par.18 deltaverzoeken), /home/transcode/truenas-v2/ai-server-manager/docs/platform-v2/03_INSTALLATIE/I01...I26, /home/transcode/truenas-v2/ai-server-manager/docs/platform-v2/04_BESTAANDE_APPS/A01...A20,
  /home/transcode/truenas-v2/ai-server-manager/docs/platform-v2/05_TESTS/INTEGRALE_E2E_TESTMATRIX.md, /home/transcode/truenas-v2/ai-server-manager/docs/platform-v2/08_EXCEL/ (tasks.json, e2e_cases.json, decisions.json, b03/*.json).
- Per repo: docs/platform-v2/EVIDENCE.json, docs/platform-v2/EXCEL_TAKEN.json, docs/adr/ of docs/**/ADR*, .github/workflows/, README, en de code zelf.
- /home/transcode/truenas-v2/.lokaal/plan/bron/STAND_PER_ID.tsv (ID, soort, project, fase_excel, status_bewijs per repo, taak; 563 rijen), /home/transcode/truenas-v2/.lokaal/plan/bron/ALLE_IDS.txt (513 unieke ID's),
  /home/transcode/truenas-v2/.lokaal/plan/bron/VERVOLGPUNTEN_RUW.md (per repo alle vervolgpunten/blokkades uit eerdere agentrapporten; RUW: veel is later opgelost,
  controleer per punt in de code of het nog open is) en /home/transcode/truenas-v2/.lokaal/plan/bron/RESULTATEN_ALLE_AGENTS.jsonl (141 eindrapporten, o.a. reviewbevindingen).
- Ontwerptaal Peil: zoek in /home/transcode/truenas-v2/ai-server-manager naar de Peil-documenten (grep -ril "peil" docs | head) en /home/transcode/truenas-v2/.lokaal/ontwerptaal/.

STAND: STAND_PER_ID.tsv is een momentopname van VOOR het einde van ronde 3. Ronde 3 bouwt nu: ai-server-manager (executor, policy,
ai, backup, beveiliging, Hub-web: B02, B01-003/007/008/009, B12-004...007), home-control-hub (Node-RED B11-001...005),
jelly-leon-platform (lifecycle B08-003/004 + manifest I10), media-guard-ultimate (twee mediaservers tegelijk: Delta-MG-AUTH en
Delta-MG-DUAL, upgradetest op een 1.2.2-fixture, Android en-US), my_house (tabel bij 'Laatste 24 uur'), jelly-leon (contract 1.3 +
golf 1: B03-017/018/009/010), jelly-leon-web en jelly-leon-clients (contract 1.3). Daarom krijgt ELKE stap een controle
"Al gedaan?" (een alleen-lezen commando + de verwachte uitkomst), zodat geen subagent werk dubbel doet of half werk overschrijft.

VASTE REGELS VAN DE GEBRUIKER (het plan moet ze afdwingen, niet alleen noemen):
1. Antwoorden in het Nederlands; vragen via een keuzemenu; niets gokken. Geen PR's zonder te vragen. ai-factory niet aanraken.
2. Altijd "git pull --rebase" voor elke push; geen force-push; Nederlandse commitberichten; geen geheimen; geen modelnaam of
   model-ID in commits, code of docs; commits eindigen met "Co-Authored-By: Claude <noreply@anthropic.com>".
3. Excel/EVIDENCE: nooit "Gereed" of "Geslaagd". Gebouwd en in de simulator getest = "Bezig". Alles wat de echte NAS, echte
   hardware of echte accounts vraagt = "Geblokkeerd" met de tekst NIET GEVALIDEERD en wat er nog nodig is. Na elke fase de Excel bijwerken.
4. HARDE EIS: alle kijkgeschiedenis (gezien, hervatpunten, favorieten, beoordelingen, spoorkeuzes, gebruikers) en de
   MediaGuard-voortgang blijven altijd beschikbaar. De gebruiker gebruikt nu Emby; Emby blijft werken en wordt nooit onderbroken;
   geen overstap zonder voor/na-rapport en akkoord; de oude installatie blijft terugval; de gebruiker verwijdert Emby zelf.
5. Installatie is altijd een standaard TrueNAS Custom App (een alles-in-een image per repo); nooit YAML/compose als installatieweg.
6. UI-werk: eerst een ontwerpstap volgens Peil (Tailwind 4 + shadcn/ui + lucide), na de bouw een ontwerpreview. Jelly Leon web/clients vallen buiten Peil.
7. Schijf en geheugen zijn beperkt (14,5 GiB RAM): nooit "docker system prune -a", "docker builder prune -a" of "docker volume prune"
   terwijl er iets bouwt; zware builds na elkaar.

EERLIJKHEID (belangrijkste kwaliteitsregel): verzin geen paden, commando's, functienamen, poorten of ID's. Alles wat je in het plan
noemt heb je zelf in een bestand gezien. Wat je niet kon vaststellen schrijf je als "ONBEKEND - eerst vaststellen met: <commando>".
Verwijs naar bronnen als pad + kop (geen regelnummers: die verschuiven). Citeer besluiten met hun ID (BG-xx, D-xx, ADR-nnnn).
PADEN IN HET PLAN: schrijf <WERKMAP> in plaats van /home/transcode/truenas-v2. De repos zijn publiek: geen geheimen, geen IP-adressen, geen NAS-gegevens.
TAAL: Nederlands, zakelijk, zonder opvulling. Markdown. Geen emoji.

JE BENT CONTROLEUR EN HERSTELLER TEGELIJK van: /home/transcode/truenas-v2/.lokaal/plan/uit/STAPPEN_P2.md. Jij bent de ENIGE die deze bestanden wijzigt; alle andere
planbestanden in /home/transcode/truenas-v2/.lokaal/plan/uit lees je alleen (andere agents bewerken die op dit moment). Ga ervan uit dat je bestanden fouten bevatten
en zoek ze actief. Werkwijze: (1) stel elke fout zelf vast (bestand gelezen, grep/ls gedraaid) - geen vermoedens; (2) herstel
haar direct, zo dat het probleem echt weg is (niet alleen een opmerking toevoegen), met behoud van het sjabloon en de stap-ID's
(bestaande stap-ID's NIET hernummeren; een nieuwe stap krijgt een nieuw, nog niet gebruikt nummer; een te grote stap splits je
in de bestaande plus nieuwe stappen); (3) wat in een ANDER planbestand moet veranderen wijzig je NIET zelf maar meld je in
voor_ander_bestand als "<bestand>: <plek>: <wat precies>"; (4) wat je niet kon vaststellen of oplossen meld je in open.
Geen stijlwerk; wel alles waardoor een regisseur of subagent met weinig denkruimte iets fout zou bouwen, iets zou overslaan,
vast zou lopen of een regel van de gebruiker zou breken. Lees je bestand aan het eind terug (sjabloon intact, geen verzonnen
paden, geen dubbele stap-ID's). Vul "hersteld" in met een regel per herstel (kleine herstellingen van dezelfde soort mag je
bundelen) en schrijf in "gecontroleerd" eerlijk wat je WEL en NIET hebt nagelopen.
WERK ZUINIG: het plan is samen ruim een miljoen tekens. Lees ALLEEN je eigen bestand(en) volledig. Van andere planbestanden en
van bronnen lees je gericht: eerst "grep -n" op de kop, het stap-ID of het werkpakket-ID, daarna alleen dat deel. Lees geen
transcripties of logboeken. Start geen subagents.
STAND RONDE 3: de lopende bouwronde wordt ingekort. Lees /home/transcode/truenas-v2/.lokaal/plan/STAND_RONDE3.md (kort). Wat daar "NIET begonnen" of "review NIET gedaan"
heet, is werk dat de regisseur na de overdracht nog moet doen en dus als stap in het plan moet staan.
JOUW CONTROLE van /home/transcode/truenas-v2/.lokaal/plan/uit/STAPPEN_P2.md, voor ELKE stap (bij meer dan 40 stappen: A, F en de velden van C voor alle stappen met
grep/ls in een lus; de inhoudelijke bronvergelijking voor minstens de helft, te beginnen bij de stappen met moeilijkheid
"hoog" of hoger en alles wat veiligheid of de HARDE EIS raakt; meld welke stappen je inhoudelijk hebt overgeslagen):
A. FEITEN. Bestaat elk genoemd pad, bestand, map, script, make-doel, pakket en commando echt (ls/grep in de repo), in de juiste
   repo? Klopt elke bronverwijzing (bestand en kop bestaan en de bron zegt wat de stap beweert)? Ontbreekt een eis,
   acceptatiecriterium of test uit de bron, of is er iets verzonnen? Staat elk werkpakket-/test-ID in /home/transcode/truenas-v2/.lokaal/plan/bron/ALLE_IDS.txt en
   hoort het bij deze fase (OVERDRACHT_PROMPT par.4, B03_FASERING par.3)?
B. UITVOERBAARHEID. Is "Al gedaan?" een echt commando dat verschil ziet tussen klaar, half en niet begonnen? Zijn de tests
   concreet (commando bestaat) en is er een negatieve test? Is "Bewijs" eerlijk (niets op de ontwikkelmachine wat de NAS
   vraagt)? Is de stap klein genoeg voor EEN bouwer-subagent (een repo, hooguit ongeveer 8 bouwpunten) en zonder toelichting te
   begrijpen? Klopt "Zwaar"?
C. AGENTS EN NIVEAU. Heeft elke stap de regels "Agents" en "Niveau" en in de kopregel "Moeilijkheid"? Staan de verplichte
   reviewers erin (R-VEILIG bij executor/policy/ondertekening/authenticatie/geheimen; R-HARDE-EIS bij databases, migraties,
   gebruikers, kijkgegevens, de Emby-koppeling of de MediaGuard-voortgang; R-MANIFEST bij manifesten; A-ONTWERP vooraf en
   R-ONTWERP achteraf bij UI)? Te LAAG: zulke stappen, of stappen met gelijktijdigheid of een ingreep in upstream-code van een
   fork, die toch "gewoon"/"standaard" staan. Te HOOG: elke N5 en elke "zeer hoog" - valt het echt onder een van de vijf
   toegestane gevallen en staat er een concrete zin "Winst: ..." bij? Houd het aandeel N5 op hooguit ongeveer een op de acht
   stappen; verlaag de rest naar N4.
D. REGELS EN HARDE EIS. Geen plek die een regel van de gebruiker breekt of laat breken: "Gereed"/"Geslaagd" als status, een PR,
   force-push, push zonder pull --rebase, compose/YAML als installatieweg, een modelnaam, een geheim of NAS-gegeven, ai-factory.
   Elke stap die de HARDE EIS raakt heeft een upgradetest of voor-na-vergelijking, een terugvalweg en waar nodig akkoord van de
   gebruiker. Wordt iets stilzwijgend aangenomen waar de gebruiker een keuzemenu had moeten krijgen (vergelijk met
   /home/transcode/truenas-v2/.lokaal/plan/uit/BESLUITEN_EN_BLOKKADES.md: grep op het besluit-ID)?
E. VOLGORDE EN BANEN. Kloppen de "Vooraf"-ketens (bestaande stap-ID's, geen kringen)? Gebruikt een stap iets wat pas later
   wordt gebouwd? Zet de tabel "Volgorde en banen" of "Startbezetting" twee stappen in DEZELFDE repo tegelijk, of twee stappen
   tegelijk terwijl de ene de andere nodig heeft? Blijft de regisseur onnodig onder de 8 bouwketens (stappen in een repo achter
   elkaar geregen zonder echte afhankelijkheid)? Komt de fase-afsluiting/gate overeen met 06_FASERING_EN_GATES.md en
   B03_FASERING.md par.4 (geen gate-eis vergeten of afgezwakt)?
F. VERWIJZINGEN. Elke V-nnn bestaat in /home/transcode/truenas-v2/.lokaal/plan/uit/VALKUILEN.md (grep "^#.*V-nnn" of de index) - vul per stap de regel "Valkuilen"
   aan met de valkuilen die echt op de stap slaan (lees de index/koppen van VALKUILEN.md een keer). Elke poort P-<naam> bestaat
   in /home/transcode/truenas-v2/.lokaal/plan/uit/POORTEN.md en elke rolnaam (A-..., R-...) heeft een prompt in /home/transcode/truenas-v2/.lokaal/plan/uit/AGENTEN.md (grep).
G. VOLLEDIGHEID. Neem uit /home/transcode/truenas-v2/.lokaal/plan/bron/STAND_PER_ID.tsv de ID's van deze fase met status "Niet gestart" of zonder bewijs: staat elk
   in een bouwstap (niet alleen als "gebouwd" in een Dekking-tabel)? Elk punt uit CONTRACT_1.3_CONFORMITEIT.md met het moment
   van deze fase staat in een stap.

EXTRA (belangrijk): vergelijk met /home/transcode/truenas-v2/.lokaal/plan/STAND_RONDE3.md en met "git log --oneline -15" in de betrokken repos. Voor ELK onderdeel
dat daar "NIET begonnen" heet en voor ELKE "review NIET gedaan" moet een eigen stap bestaan, vroeg in de volgorde. Ontbreekt
hij: voeg hem toe volgens het sjabloon. Een reviewstap voor al gebouwd werk heeft geen A-BOUW maar de keten reviewers ->
A-HERSTEL -> R-EERLIJK met de diff-basis (commitbereik) erbij; gebruik de ketenvorm die /home/transcode/truenas-v2/.lokaal/plan/uit/AGENTEN.md daarvoor kent (grep
op "review"), en kent AGENTEN.md die niet: beschrijf de keten voluit in de regel "Agents" en meld het in voor_ander_bestand.

STAPSJABLOON (gebruik exact deze opbouw; elke stap heeft een uniek ID S-<fase>-<nn>, bv. S-P3-07; nummer met tientallen ruimte waar handig):

### S-P3-07 - korte titel
- **Repo:** <repo> | **Fase:** P3 | **Omvang:** klein/middel/groot | **Moeilijkheid:** gewoon/hoog/zeer hoog | **Zwaar:** ja/nee (image-build, Gradle/Android, emulator, grote .NET-build, echte Emby/Jellyfin-containers)
- **Werkpakketten en tests:** B05-003, B05-004; EX12 (alle ID's die deze stap raakt; exact zoals in ALLE_IDS.txt)
- **Vooraf:** S-P3-05 klaar; Gate P2; besluit BG-xx genomen (of "geen")
- **Al gedaan?** `<alleen-lezen commando>` -> verwachting als het al klaar is; wat te doen bij half werk
- **Lees eerst:** <pad#kop> (maximaal 5 bronnen, de belangrijkste eerst)
- **Bouw:**
  1. ... (concreet: welk bestand/module, welk gedrag; met "Bron: pad#kop")
  2. ...
- **Tests (verplicht):** welke tests erbij komen, inclusief minstens een negatieve test; het exacte commando om ze te draaien
- **Poort:** P-<repo> uit POORTEN.md + eventuele extra controles (contract, veiligheid, Peil, HARDE EIS)
- **Valkuilen:** V-nnn (uit VALKUILEN.md, als je ze kent) of een korte eigen waarschuwing
- **Bewijs:** welke EVIDENCE-ID's naar "Bezig" of "Geblokkeerd" gaan; letterlijke tekst "NIET GEVALIDEERD: ..." voor wat de NAS nodig heeft
- **Agents:** de keten voor deze stap, bv. "A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG (tegelijk) -> A-HERSTEL -> R-EERLIJK"; bij UI staat A-ONTWERP voor A-BOUW en R-ONTWERP na het herstel. Zet VERPLICHT achter elke reviewer die niet mag worden overgeslagen
- **Niveau:** "standaard" (dan gelden de standaardniveaus per rol uit AGENTEN.md), of alleen de afwijkingen, bv. "A-BOUW N4; R-HARDE-EIS N5 - Winst: echte migratie van kijkgeschiedenis, een fout is niet terug te draaien". Bij N5 is de zin "Winst: ..." verplicht
- **Stop en vraag als:** concrete situaties waarin de subagent moet stoppen en melden, zodat de regisseur de gebruiker een keuzemenu voorlegt

Regels voor de stappen:
- Begin het bestand met: doel van de fase, de gate(s) die ervoor en erna gelden (uit 06_FASERING_EN_GATES.md / B03_FASERING.md par.4),
  een tabel "Volgorde en banen" (stap, baan = repo, vooraf, zwaar ja/nee, kan tegelijk met), een korte alinea "Startbezetting"
  (welke ketens de regisseur aan het begin van deze fase tegelijk kan starten binnen de grens van 10 subagents en 8
  bouwketens, welke daarna vrijkomen, en in welke repos tijdens deze fase GEEN werk ligt zodat de regisseur daar - als de
  gate-matrix het toestaat - een keten uit een andere fase of golf kan laten lopen om de 8 banen te vullen) en daarna de stappen. Sluit af met "Fase-afsluiting": gatecontrole
  als afvinklijst (uit te voeren door A-GATE), Excel bijwerken, STATUS.md bijwerken, wat aan de gebruiker te melden.
- Standaardketen voor elke bouwstap: A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL (alleen bij bevindingen) -> R-EERLIJK. Daarbovenop
  VERPLICHT: R-VEILIG bij executor/policy/ondertekening/risicoklassen/authenticatie/geheimen; R-HARDE-EIS bij migraties en alles
  wat kijkgeschiedenis, gebruikers, de Emby-koppeling of de MediaGuard-voortgang raakt; R-MANIFEST bij installatiemanifesten en
  images; A-ONTWERP voor en R-ONTWERP na elke UI-stap. Alleen een zuivere documentatie- of controlestap mag een kortere keten
  hebben (schrijf dan waarom).
- Moeilijkheid en Niveau: "gewoon" is de norm. "hoog" = lastige gelijktijdigheid, migratie, beveiliging, fork-ingreep in
  upstream-code of een stap waar eerdere agents op vastliepen (zie RESULTATEN_ALLE_AGENTS.jsonl). "zeer hoog" alleen volgens
  geval (c) van N5 en met de zin "Winst: ...". Kies het niveau eerlijk: te laag kost kwaliteit, N5 zonder echte winst is tegen
  de wens van de gebruiker. Verdeel het werk zo dat er ook echt GROTE bouwstappen naast elkaar kunnen lopen (verschillende
  repos), in plaats van alles achter elkaar in een repo te rijgen waar dat niet nodig is.
- De stap wordt door de subagent ZELF gelezen: schrijf haar dus aan de bouwer ("Bouw", "Tests") en zet alles erin wat hij moet
  weten; verwijs niet naar "zoals eerder besproken" of naar een andere stap voor essentiele informatie.
- Neem per repo de nog OPEN vervolgpunten uit VERVOLGPUNTEN_RUW.md en de punten uit CONTRACT_1.3_CONFORMITEIT.md met het Moment van
  jouw fase op als eigen stap of als onderdeel van een stap (controleer in de code of het punt nog open is; noem het punt-ID).
- Wat alleen op de echte NAS/hardware/accounts kan, wordt GEEN bouwstap maar een regel in de stap onder "Bewijs" (Geblokkeerd) en
  hoort verder in STAPPEN_P6.md.
- Verwijs voor lokale controlecommando's naar POORTEN.md (P-<repo>); herhaal ze niet. Als je voor een repo een specifiek
  testcommando nodig hebt, zoek het op in die repo (.github/workflows, Makefile, package.json, pyproject.toml) en schrijf het exact over.
- Sluit het bestand af met een tabel "Dekking" met ALLE ID's die tot jouw deel behoren: ID | stap of reden (bv. "gebouwd in P0/P1,
  alleen NAS-validatie open -> STAPPEN_P6" of "besluit BG-xx nodig"). Geen ID uit jouw deel mag ontbreken.

AANVULLING VAN DE REGISSEUR (gaat voor waar ze afwijkt van het bovenstaande):
- Een eerdere poging met precies deze opdracht is op 2026-11-11 na ongeveer twaalf minuten AFGEBROKEN. Je bestand(en) kunnen
  dus al deels hersteld of aangevuld zijn, en een wijziging kan half zijn blijven staan (een afgebroken zin, tabel of stap; een
  stap die twee keer voorkomt). Zoek daar eerst naar en maak het heel.
- Ronde 3 is niet "ingekort" maar AFGEBROKEN. Lees /home/transcode/truenas-v2/.lokaal/plan/STAND_RONDE3.md: wat daar HALF WERK
  heet staat niet-gecommit in de werkmap van die repo (reservekopie in /home/transcode/truenas-v2/.lokaal/halfwerk).
- 00_LEES_EERST.md, STARTPROMPT.md, VOORTGANG.md en PLAN_AFMAKEN.md in de planmap zijn van de regisseur: lees ze waar nodig,
  wijzig ze niet, meld wat erin moet veranderen onder VOOR_ANDER_BESTAND.
- Je hebt geen StructuredOutput-tool. Geef je eindantwoord als tekst met precies deze koppen: HERSTELD (per regel: plek |
  ernst blokkerend/belangrijk/klein | wat), OPEN, VOOR_ANDER_BESTAND (per regel "<bestand>: <plek>: <wat precies>"),
  GECONTROLEERD (wat wel en wat NIET), SAMENVATTING. Sla precies dat antwoord ook op in
  /home/transcode/truenas-v2/.lokaal/plan/afmaakrapporten/controle_p2.md
- Schrijf in geen enkel planbestand een modelnaam; alleen niveaus (N1 tot en met N5). Start geen subagents. Wijzig niets in de
  repos (alleen lezen).
