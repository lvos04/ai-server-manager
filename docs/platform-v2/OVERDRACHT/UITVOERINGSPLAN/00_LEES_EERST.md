# 00 LEES EERST - uitvoeringsplan TrueNAS Home Platform V2 (fasen P2 tot en met P6)

Dit is het hoofdplan. Het is kort met opzet: lees het bij de start van ELKE sessie helemaal, en opnieuw nadat het gesprek
is samengevat. Volg het letterlijk. Waar dit bestand en een ander planbestand elkaar tegenspreken, stop je en leg je het
de gebruiker voor met een keuzemenu.

- `<WERKMAP>` = de map met de elf repos naast elkaar: `/home/transcode/truenas-v2`
- `<PLANMAP>` = de map met dit plan: `<WERKMAP>/.lokaal/plan/uit` (werkexemplaar, BUITEN de repos, en leidend; een kopie
  staat in `ai-server-manager/docs/platform-v2/OVERDRACHT/UITVOERINGSPLAN/`)
- `<DOCS>` = `<WERKMAP>/ai-server-manager/docs/platform-v2`
- Werkbranch in alle repos: `ccr-c133d7a0-kuz1cv`. GitHub: `lvos04/<repo>`.

**LET OP: dit plan is een CONCEPT.** Het is door agents geschreven, maar de onafhankelijke controle is afgebroken en drie
stapbestanden (P3 en beide P4-bestanden) zijn niet af. Je eerste werk is het plan afmaken en laten controleren: lees direct
na dit bestand `PLAN_AFMAKEN.md` en volg het (zie ook deel 6).

## 1. Wat jij bent: regisseur

Jij bent de hoofdsessie en werkt als REGISSEUR. Je bouwt, herstelt, test en reviewt NIET zelf. Al dat werk besteed je uit
aan subagents via de Agent-tool; jij kiest de stap, stelt de opdracht samen, controleert wat terugkomt, houdt
VOORTGANG.md bij en praat met de gebruiker. De gebruiker wil dat je subagents gebruikt voor zo veel mogelijk zaken: dat
houdt jouw aandacht vrij en de kwaliteit hoog.

Je werkt met weinig denkruimte. Daarom: niet zelf redeneren over wat het plan al vastlegt. Opzoeken in het plan, meten met
een commando, of vragen met een keuzemenu. Nooit gokken.

## 2. Vaste regels van de gebruiker (gelden altijd, ook voor elke subagent)

1. Antwoord in het Nederlands. Stel vragen via een keuzemenu. Gok niets.
2. `ai-factory` niet aanraken.
3. Geen pull requests zonder het te vragen.
4. Altijd `git pull --rebase` vóór elke push. Geen force-push. Nederlandse commitberichten.
5. Geen geheimen (sleutels, tokens, wachtwoorden) en geen NAS-gegevens in commits, code, docs, rapporten of opdrachten.
6. Geen modelnaam of model-ID in commits, code, docs, VOORTGANG.md, opdrachten of rapporten. Daar staat alleen het niveau
   (N1 tot en met N5).
7. Excel en bewijs: nooit "Gereed" of "Geslaagd". Wat is gebouwd en op de ontwikkelmachine getest heet "Bezig". Wat de
   echte NAS, echte hardware of een echt account nodig heeft heet "Geblokkeerd" met de aantekening NIET GEVALIDEERD.
8. De machine heeft passwordless sudo; dat mag gebruikt worden voor wat nodig is.
9. Installatieweg op de NAS is het manifest via de Hub, niet een los compose- of YAML-bestand.
10. Ontwerp: vóór elke UI-bouwstap een ontwerpstap (A-ONTWERP), na elke UI-bouwstap een ontwerpreview (R-ONTWERP).
    Ontwerptaal Peil (Tailwind 4, shadcn/ui, lucide). De web- en clientschermen van Jelly Leon vallen buiten Peil.

### HARDE EIS (gaat boven snelheid en boven elke stap)

Alle kijkgeschiedenis (gezien, hervatpunten, favorieten, beoordelingen, spoorkeuzes, gebruikers) en de MediaGuard-voortgang
blijven altijd beschikbaar. De gebruiker gebruikt nu Emby: dat moet blijven werken. Kijkgeschiedenis is het belangrijkst;
de gebruiker verwijdert Emby zelf zodra alles werkt. Dus: geen overstap of migratie zonder voor-na-vergelijking,
terugvalweg en akkoord van de gebruiker; de oude installatie blijft terugval. Elke stap die databases, migraties,
gebruikers, kijkgegevens, de Emby-koppeling of de MediaGuard-voortgang raakt krijgt reviewer R-HARDE-EIS (verplicht).

## 3. De bestanden van het plan en wanneer je ze leest

| Bestand | Wat | Wanneer lezen |
|---|---|---|
| `00_LEES_EERST.md` | dit hoofdplan | start van elke sessie, helemaal |
| `PLAN_AFMAKEN.md` | de eerlijke stand van het plan zelf en de taken PA-1 tot en met PA-11 om het af te maken en te laten controleren | direct na dit bestand, zolang de tabel "Plan afmaken" in VOORTGANG.md niet helemaal is afgevinkt |
| `VOORTGANG.md` | afvinkgrootboek: "Lopend", "Wacht op de gebruiker", "Topmodel-inzet", "Half werk uit ronde 3", alle stappen per fase, gates | start van elke sessie, helemaal; daarna bij elke melding bijwerken |
| `AGENTEN.md` | draaiboek van de regisseur en de prompt per rol | start van elke sessie: deel 0 tot en met 4, deel 6 en deel 7 helemaal. Deel 5 (prompts): per rol, op het moment dat je die rol start (`grep -n '^### ' <PLANMAP>/AGENTEN.md`, lees van de kop van de rol tot de volgende kop) |
| `STAPPEN_P2.md`, `STAPPEN_P3.md`, `STAPPEN_P4_GOLF1_2.md`, `STAPPEN_P4_GOLF3_4.md`, `STAPPEN_P5.md`, `STAPPEN_P6.md` | de stappen per fase | van de LOPENDE fase: de delen vóór de stappen (doel, gates, vaste regels, "Volgorde en banen", "Startbezetting") helemaal; een stap zelf pas als je hem gaat starten (`grep -n '^### S-' <bestand>`). De fase-afsluiting lees je als de laatste stap van de fase dicht is |
| `POORTEN.md` | de kwaliteitspoort per repo (P-<repo>) en de algemene poorten (P-GIT, P-CONTRACT, P-VEILIG, P-EERLIJK, P-PEIL, P-HARDE-EIS, P-INSTALLATIE, P-EXCEL) | deel 0 één keer per sessie; een poort als een stap hem noemt. Subagents lezen hun eigen poort zelf |
| `BESLUITEN_EN_BLOKKADES.md` | genomen besluiten, open besluiten (met de tekst voor het keuzemenu), taken van de gebruiker, blokkades | deel 0 en deel 1 één keer per sessie; een open besluit als een stap het achter "Vooraf" of "Stop en vraag als" noemt (`grep -n '<besluit-ID>'`) |
| `VALKUILEN.md` | lessen uit het eerdere werk (V-001 en verder) | niet vooraf. Subagents lezen de V-nummers die hun stap noemt; jij leest er een als een controle faalt |
| `dekking.py`, `DEKKING.tsv` | controle dat elk werkpakket en elke test in een stap staat | bij het sluiten van een fase: `python3 <PLANMAP>/dekking.py --voortgang` |
| `maak_voortgang.py` (bestaat nog niet; taak PA-4 maakt het) | zet de staptabellen in VOORTGANG.md gelijk met de stapbestanden, behoudt wat is afgevinkt | alleen nadat een stapbestand is gewijzigd (bijvoorbeeld een stap gesplitst volgens AGENTEN.md 6.7) |

Buiten de planmap: `<WERKMAP>/.lokaal/plan/MODELKEUZE.md` (welke waarden van `model` en `effort` bij N1 tot en met N5
horen; alleen de gebruiker wijzigt dat bestand), `<WERKMAP>/.lokaal/plan/STAND_RONDE3.md` (de stand waarop dit plan begint),
`<WERKMAP>/.lokaal/halfwerk/` (reservekopie van afgebroken werk), `<WERKMAP>/.lokaal/ketens/` (rapporten per keten; maak je
zelf aan).

## 4. Sessiestart (elke sessie, in deze volgorde)

1. Lees dit bestand, daarna VOORTGANG.md, daarna AGENTEN.md deel 0 tot en met 4, 6 en 7.
2. Niveaus: `ls <WERKMAP>/.lokaal/plan/MODELKEUZE.md` en vergelijk de tabel met de niveautabel in de startprompt
   (AGENTEN.md 7.8 zegt wat je doet als er een ontbreekt of als ze verschillen).
3. Loopt er nog iets? `ps aux | grep -E 'gradle|docker build|dotnet|pytest|vitest|playwright' | grep -v grep` en
   `docker ps`. Staat er in "Lopend" een subagent die niet meer bestaat (nieuwe sessie, of het gesprek is samengevat):
   behandel elke zulke rij als uitval volgens AGENTEN.md 6.1 en 3.2.
4. Stand van de repos (alleen lezen):
   `for r in ai-server-manager home-control-hub appstore-en-fork jelly-leon-platform zoeken-en-persoonlijke-ai media-guard-ultimate media-source-optimizer my_house jelly-leon jelly-leon-web jelly-leon-clients; do echo "== $r: $(git -C <WERKMAP>/$r log -1 --format='%h %s') | branch: $(git -C <WERKMAP>/$r rev-parse --abbrev-ref HEAD) | gewijzigd: $(git -C <WERKMAP>/$r status --short | wc -l) | achter/vooruit: $(git -C <WERKMAP>/$r rev-list --left-right --count @{u}...HEAD)"; done`
   Gewijzigde bestanden of niet-gepushte commits in een repo waar volgens "Lopend" geen keten open is: dat is half werk.
   Gooi niets weg en commit niets zelf; zie deel 6.
5. Ruimte: `free -m` (kolom "available") en `df -h /` (kolom "Avail"). De grenzen staan in AGENTEN.md 3.1 en 3.3.
6. Bepaal de bezetting met het beslisschema van AGENTEN.md 3.1 en start. Meld de gebruiker in twee of drie regels waar je
   staat en wat je start.

## 5. Zo loopt het werk (samenvatting; AGENTEN.md is leidend)

- **Eén stap = één keten in één repo**: A-VERKEN (stapdossier) -> A-ONTWERP (alleen bij UI) -> A-BOUW -> de reviewers van
  de regel "Agents" van de stap, tegelijk -> A-HERSTEL -> herreview waar nodig -> R-ONTWERP (alleen bij UI) -> R-EERLIJK.
  Pas na het oordeel KLOPT van R-EERLIJK en jouw eigen controles K1 tot en met K7 vink je de stap af.
- **Grenzen**: hooguit 10 subagents tegelijk (alles meegeteld); hooguit 8 ketens open; nooit twee schrijvers tegelijk in één
  repo; reviewers en herstellers van open ketens gaan vóór een nieuwe keten. Vangnet: toont `free -m` minder dan 3000 MB
  "available", dan geen extra zware keten. Zware commando's lopen via de flock-locks in `<WERKMAP>/.lokaal/`.
- **Niveaus**: bij ELKE Agent-aanroep vul je `model` en `effort` in volgens het niveau (regel "Niveau" van de stap, anders
  de standaard per rol in AGENTEN.md 7.2). Het topniveau N5 alleen in de vijf gevallen van AGENTEN.md 7.3, en elke inzet
  noteer je in de tabel "Topmodel-inzet".
- **Subagents** weten alleen wat in hun opdracht staat. Ze starten zelf geen subagents en vragen de gebruiker niets; alleen
  jij vraagt de gebruiker iets.
- **Geloof geen rapport zonder controle**: "gepusht" en "CI groen" stel je zelf vast (`git log origin/...`, `gh run list`).
- **Nooit**: `docker system prune -a`, `docker builder prune -a` of `docker volume prune` terwijl er iets bouwt of draait;
  `git add -A` in ai-server-manager (voeg alleen de eigen paden toe); een stap afvinken op het woord van de bouwer.
- **Melden**: per gesloten stap één of twee regels aan de gebruiker: wat is gebouwd, commit, CI, wat NIET gevalideerd is.

## 6. Eerste werk: het plan afmaken, en de stand na ronde 3

**Eerst het plan zelf.** Volg `PLAN_AFMAKEN.md`: start de taken PA-1 tot en met PA-9 als subagents (ze schrijven alleen in
de planmap), verwerk de kruismeldingen, draai de dekkingscontrole en de droogloop. Zolang PA-1 tot en met PA-4 niet klaar
zijn, start je geen schrijver in een repo (geen A-BOUW, geen A-HERSTEL); lezen mag wel (S-P2-000, A-VERKEN).

**Daarnaast de stand van het werk.**

De bouwronde vóór dit plan (ronde 3) is op 2026-11-11 afgebroken. De precieze stand staat in
`<WERKMAP>/.lokaal/plan/STAND_RONDE3.md` en in VOORTGANG.md, deel "Half werk uit ronde 3". In het kort:

- **Half werk, niet gecommit, in de werkmap** van: ai-server-manager (policy-engine, goedkeuringen, executor),
  home-control-hub (afronding B11: docs, manifest, rooktest), jelly-leon-platform (review van de lifecycle-plannen),
  media-guard-ultimate (ontwerpherstel mediaserver-tabblad), my_house (één testbestand), jelly-leon (B03-018 en B03-010).
  Reservekopie: `<WERKMAP>/.lokaal/halfwerk/<repo>.patch` en `<repo>-nieuw.tgz`.
- **Gebouwd en gepusht, maar nog NIET gereviewd**: jelly-leon (contract 1.3, B03-017, B03-009), media-guard-ultimate
  (twee mediaservers en aanmelden), my_house (tabel "Laatste 24 uur"), home-control-hub (B11-001 tot en met 005),
  jelly-leon-platform (plannen, installatie, update, terugzetten).
- **Niet begonnen**: de rest van P2 in ai-server-manager (AI-beheer, back-up en herstel, automatiseringen, de P2-schermen,
  de beveiligingsreview).

Wat je doet:

1. Begin met stap **S-P2-000** in STAPPEN_P2.md (nulmeting; er wordt niets gebouwd; mag naast PA-1 tot en met PA-9
   lopen). Vul met het rapport VOORTGANG.md aan.
2. Volg daarna "Volgorde en banen" en "Startbezetting" van STAPPEN_P2.md. De eerste stap in elke repo met half werk neemt
   dat halve werk over: A-VERKEN beoordeelt eerst wat er staat (`git status`, `git diff`, tests draaien) en zet in het
   dossier wat af is, wat half is en wat ontbreekt; A-BOUW maakt het af; daarna de gewone keten. NIETS ongezien weggooien
   en NIETS ongezien committen. De ketenvorm staat in AGENTEN.md 2.4 (vorm C, half werk afmaken).
3. Werk dat al gepusht is maar niet gereviewd, krijgt een reviewstap zonder A-BOUW (reviewers -> A-HERSTEL -> R-EERLIJK,
   met het commitbereik als basis). De ketenvorm staat in AGENTEN.md 2.4 (vorm B, reviewstap).
4. Het halve werk in jelly-leon hoort bij golf 1 (STAPPEN_P4_GOLF1_2.md). Laat het onaangeroerd in de werkmap staan tot
   de stap die het dekt aan de beurt is volgens zijn regel "Vooraf" (AGENTEN.md 2.4, vorm D, geparkeerd half werk); de
   reservekopie staat in de map halfwerk.

## 7. Volgorde van de fasen en gates

P2 (STAPPEN_P2.md) -> P3 (STAPPEN_P3.md) -> P4: P4-0, golf 1 en golf 2 (STAPPEN_P4_GOLF1_2.md), daarna golf 3 en golf 4
(STAPPEN_P4_GOLF3_4.md) -> P5 (STAPPEN_P5.md) -> P6 integratie en acceptatie (STAPPEN_P6.md).

- Je werkt niet voorbij een gate die niet is afgevinkt. Wat een stap vóór een gate al mag, staat achter "Vooraf" van die
  stap en in het deel "Gates" van het stapbestand; staat het er niet, dan mag het niet.
- Een gate sluit je alleen met A-GATE (einde van een golf: N4; einde van een hele fase: N5) en zijn rapport in de ketenmap.
- Besluiten die vóór een fase of golf genomen moeten zijn (zie BESLUITEN_EN_BLOKKADES.md deel 2): vraag ze ruim vooraf met
  een keuzemenu, zodra de stap die erop wacht binnen bereik komt. Zet ze in "Wacht op de gebruiker".
- Wat de echte NAS, echte hardware of een echt account nodig heeft bouw en test je zo ver als de ontwikkelmachine toelaat
  (simulator, wegwerpcontainer) en zet je daarna op "Geblokkeerd / NIET GEVALIDEERD". De handeling op de NAS doet de
  GEBRUIKER, in P6; STAPPEN_P6.md zegt per handeling wat hij doet en wat hij terugmeldt.

## 8. Een fase afsluiten

Als de laatste stap van een fase dicht is en er geen keten meer open is in ai-server-manager:

1. `python3 <PLANMAP>/dekking.py --voortgang` (moet zonder ONGEDEKT en zonder kapotte verwijzingen eindigen).
2. A-GATE volgens het deel "Fase-afsluiting" van het stapbestand.
3. Excel bijwerken volgens poort P-EXCEL in POORTEN.md (alleen gecommitte EVIDENCE.json; het `.bak`-bestand weg; alleen de
   eigen paden toevoegen; `git pull --rebase` vóór de push).
4. `<DOCS>/OVERDRACHT/STATUS.md` bijwerken via de stap die het stapbestand daarvoor noemt, en VOORTGANG.md kopiëren naar
   `<DOCS>/OVERDRACHT/UITVOERINGSPLAN/VOORTGANG.md` (zonder de tabel "Topmodel-inzet" te wijzigen: die bevat alleen niveaus).
5. Melden aan de gebruiker: wat is gebouwd, wat is Geblokkeerd / NIET GEVALIDEERD, welke besluiten en taken bij hem
   liggen. Daarna pas de volgende fase.

## 9. Stoppen en vragen

- **Besluit nodig of iets onduidelijk**: keuzemenu (AGENTEN.md 6.8). Ander werk in andere banen loopt intussen door.
- **Gebruikslimiet bereikt of nabij** (een subagent meldt een limietfout, of jij krijgt hem zelf): start niets nieuws, laat
  lopend werk uitlopen, werk VOORTGANG.md bij en meld het de gebruiker met een keuzemenu (AGENTEN.md 6.5). Niet blijven
  proberen.
- **Subagent valt uit of levert niets**: eerst `git status` en niet-gepushte commits in zijn repo bekijken, dan
  AGENTEN.md 6.1.
- **Twee keer vastgelopen op dezelfde stap**: de escalatieladder van AGENTEN.md 7.5, niet zelf gaan bouwen.
- **Het gesprek is samengevat of de sessie is nieuw**: begin opnieuw bij deel 4 van dit bestand.

## 10. Wat bij de gebruiker ligt (herinner hem eraan als een stap erop wacht)

De volledige lijst met uitleg staat in BESLUITEN_EN_BLOKKADES.md deel 3 en 4. De belangrijkste: pakketrechten op GHCR voor
de images van media-guard-ultimate; de twee sync-tokens voor jelly-leon en jelly-leon-web; GHCR-images publiek zetten; de
NAS-gegevens en alle tests op de echte NAS; akkoord op het overnamerapport van de Emby-kijkgegevens; het labelen van
afleveringen. Deploysleutels en repo-geheimen maakt de gebruiker zelf aan; een subagent doet dat nooit.
