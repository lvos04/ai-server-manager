# VOORTGANG - afvinkgrootboek van de regisseur

Laatst bijgewerkt: 2026-11-11 12:05 (plan afgemaakt en gecontroleerd in vier rondes; bouwen kan starten).

Regels: de regisseur werkt dit bestand zelf bij, direct na elke Agent-aanroep en direct na elke melding (AGENTEN.md 3.2).
Hier staat nooit een modelnaam; alleen het niveau (N1 tot en met N5). Een stap vink je pas af na het oordeel KLOPT van
R-EERLIJK en je eigen controles K1 tot en met K7.

## Lopend

| subagent (description) | repo | stap | rol | niveau | gestart om | zwaar | ketengegevens (basis-commit, eind-commit, herstelpoging) |
|---|---|---|---|---|---|---|---|

bouwketens open: 0 van 8, subagents: 0 van 10

## Wacht op de gebruiker

| sinds | besluit of taak (ID) | welke stap wacht erop | gevraagd op |
|---|---|---|---|
| 2026-11-11 10:44 | Z-04 attributieregels oude commits: BESLOTEN "laten staan; alleen nieuwe commits volgen de regel" (gebruiker, 10:44) | geen | nog vast te leggen via A-BOUW in ai-server-manager (kop "Ook vastleggen") |
| 2026-11-11 12:05 | Z-21 hoe het manifest van my_house de optionele Zigbee-stick vastlegt: OPEN (BESLUITEN 2.15) | S-P3-755 | nog niet gevraagd; voorleggen ruim vóór S-P3-755 |
| 2026-11-11 12:05 | Z-16 repo/app_id van mt (alleen als BG-06 een app mt oplevert), Z-18 I05-titels (zonder besluit optie 1), BG-17 (vóór S-G3-28): OPEN | S-P5-01, S-P3-440, S-G3-28 | nog niet gevraagd |
| 2026-11-11 11:50 | Swap-regel: BESLOTEN "swapregel alleen als er ook minder dan 6000 MB available is" (gebruiker, 11:50) | bezettingsregel (AGENTEN 3.3) | planregel; geen repo-vastlegging nodig |
| 2026-11-11 11:50 | Processen ronde 3 (MediaGuard-review, sim_authentik): BESLOTEN "laten staan tot hun stap" (gebruiker, 11:50) | S-P2-590, S-P2-290 ruimen ze op | - |
| 2026-11-11 11:25 | C-12 accounts Node-RED: BESLOTEN "voorziening zonder geheim in het formulier via de manifeststandaard (appstore-en-fork); profiel van home-control-hub vervalt of wordt daaraan gelijkgetrokken" (gebruiker, 11:25) | S-P2-290, -295, -310, -410; stap in appstore-en-fork | nog vast te leggen via A-BOUW in ai-server-manager (S-P2-005, kop "Ook vastleggen"; BESLUITEN 0.3) |
| 2026-11-11 11:25 | Z-17 Zigbee2MQTT: BESLOTEN "in de image van my_house, optioneel (alleen aan als in het formulier een USB-apparaat is opgegeven)" (gebruiker, 11:25) | S-P3-720, S-P3-755 | nog vast te leggen via A-BOUW in ai-server-manager (S-P2-005, kop "Ook vastleggen"; BESLUITEN 0.3) |
| 2026-11-11 11:25 | Z-19 module uit: BESLOTEN "404 zoals ADR-0030; afwijking van WP-JSON in het bewijs" (gebruiker, 11:25) | S-G2-28 e.v. | nog vast te leggen via A-BOUW in ai-server-manager (S-P2-005, kop "Ook vastleggen"; BESLUITEN 0.3) |
| 2026-11-11 11:25 | Z-20 B03-002/003/006/008/011/012: BESLOTEN "in P4 bouwen (per werkpakket eerst A-VERKEN, dan stappen in een golf)" (gebruiker, 11:25) | nieuwe stappen in P4 | nog vast te leggen via A-BOUW in ai-server-manager (S-P2-005, kop "Ook vastleggen"; BESLUITEN 0.3) |
| 2026-11-11 10:52 | C-11 Node-RED-editor: BESLOTEN "geen anonieme toegang; alleen via een beheerder; manifest/ADR-0023 in jelly-leon-platform aanpassen" (gebruiker, 10:52) | stappen in P2 (ronde 2 verwerkt het) | nog vast te leggen via A-BOUW in ai-server-manager (S-P2-005, kop "Ook vastleggen"; BESLUITEN 0.3) |
| 2026-11-11 10:44 | Z-05 tokenvormige testwaarde jelly-leon-web: BESLOTEN "ja, vervangen in een nieuwe commit" (gebruiker, 10:44) | kleine stap in baan jelly-leon-web (door PA-1 toe te voegen) | nog vast te leggen via A-BOUW in ai-server-manager (S-P2-005, kop "Ook vastleggen"; BESLUITEN 0.3) |

## Topmodel-inzet

| datum | stap | rol | reden (welk van de vijf gevallen) | leverde het iets op (ja/nee en wat) |
|---|---|---|---|---|

Terugschakelregel (AGENTEN.md 7.7): staat er bij hetzelfde soort werk (zelfde rol en zelfde geval a tot en met e) drie
keer "nee", dan gaat dat soort werk terug naar N4. Noteer het hieronder als "vanaf <datum>: <rol>, geval <letter> op N4"
en meld het de gebruiker in één regel. Weer N5 alleen als de gebruiker dat via een keuzemenu kiest.

## Plan afmaken (eerste werk; zie PLAN_AFMAKEN.md)

| klaar | taak | opdrachtbestand (in <WERKMAP>/.lokaal/plan/afmaakopdrachten/) | niveau | rapport | meldingen verwerkt |
|---|---|---|---|---|---|
| [x] | PA-1 controle STAPPEN_P2.md | controle_p2.md | N3 | afmaakrapporten/controle_p2.md (10:49) | 44 stappen; C-11 voorgelegd; meldingen voor P4a/BESLUITEN/P5 in ronde 2 |
| [x] | PA-2 controle AGENTEN.md | controle_agentmodel.md | N3 | afmaakrapporten/controle_agentmodel.md (10:40) | 2.4 geschreven; meldingen voor 00_LEES_EERST verwerkt (10:50); POORTEN in ronde 2 |
| [x] | PA-3 controle POORTEN, BESLUITEN, VALKUILEN | controle_poorten.md | N3 | afmaakrapporten/controle_poorten.md (10:33) | doorgegeven aan PA-1, PA-2, PA-5 (10:35); Z-04/Z-05 gemeld; T-03 vóór P5 |
| [x] | PA-4 dekking.py afmaken en maak_voortgang.py | samen_dekking.md | N3 | afmaakrapporten/samen_dekking.md (10:33) | doorgegeven aan PA-1, PA-6, PA-7 (10:37); eigen bestanden bijgewerkt |
| [x] | PA-5 STAPPEN_P3.md afmaken en controleren | afmaken_controle_p3.md | N3 | afmaakrapporten/afmaken_controle_p3.md (10:58) | 81 stappen; meldingen naar ronde 2 |
| [x] | PA-6 STAPPEN_P4_GOLF1_2.md afmaken en controleren | afmaken_controle_p4a.md | N3 | afmaakrapporten/afmaken_controle_p4a.md (10:58) | 58 stappen; meldingen naar ronde 2 |
| [x] | PA-7 STAPPEN_P4_GOLF3_4.md afmaken en controleren | afmaken_controle_p4b.md | N3 | afmaakrapporten/afmaken_controle_p4b.md (10:41) | 78 stappen; meldingen naar PA-6 en PA-8 (10:46) |
| [x] | PA-8 STAPPEN_P5.md afmaken en controleren | afmaken_controle_p5.md | N3 | afmaakrapporten/afmaken_controle_p5.md (10:55) | 67 stappen; meldingen naar ronde 2 |
| [x] | PA-9 STAPPEN_P6.md afmaken en controleren | afmaken_controle_p6.md | N3 | afmaakrapporten/afmaken_controle_p6.md (10:41) | Dekking K.1-K.7 toegevoegd; meldingen naar PA-1 en PA-8 (10:46) |
| [x] | PA-10 dekking.py --voortgang zonder fouten | (commando) | - | exitcode 0 om 11:00 | - |
| [x] | PA-11 droogloop | droogloop.md | N2 | afmaakrapporten/droogloop.md (11:22) | ronde 3 loopt (11:30) |

## Half werk uit ronde 3 (afgebroken op 2026-11-11; NIETS ongezien weggooien of committen)

Reservekopie per repo: `<WERKMAP>/.lokaal/halfwerk/<repo>.patch` en `<repo>-nieuw.tgz`. Volledige stand: `<WERKMAP>/.lokaal/plan/STAND_RONDE3.md`.

| repo | wat er half ligt (niet gecommit) | wat al gepusht is maar NIET gereviewd | overgenomen door stap | afgehandeld |
|---|---|---|---|---|
| ai-server-manager | policy-engine, goedkeuringen, executor (23 gewijzigd, 7 nieuw; migratie 0012, hub/actions) | - | S-P2-005 (half werk); reviews van 7d3a8ce/b309042 in S-P2-010..030 | [ ] |
| home-control-hub | afronding B11: docs, manifest, rooktest, ADR-0016 (7 gewijzigd, 2 nieuw) | B11-001 t/m 005 (12 commits, t/m 076f964); CI niet beoordeeld | S-P2-290 (half werk), S-P2-295 (review) | [ ] |
| jelly-leon-platform | review lifecycle-plannen: ADR-0022 gewijzigd, ADR-0024 nieuw | plannen, installatie, update, terugzetten + herstelcommit 35fc44d; CI niet beoordeeld | S-P2-395 (half werk + review) | [ ] |
| media-guard-ultimate | ontwerpherstel mediaserver-tabblad (10 gewijzigd, schermafdrukken nieuw) | twee mediaservers en aanmelden (t/m 1dcf318) | S-P2-590 (half werk), S-P2-600 (review) | [ ] |
| my_house | 1 testbestand (apps/web/e2e/12-grafiek-24-uur.e2e.ts) | tabel "Laatste 24 uur" (t/m dcbe73d); ontwerpreview wel gedaan | S-P2-700 (review + probe) | [ ] |
| jelly-leon | B03-018 en B03-010: 4 gewijzigd, mappen Core/Budget, Core/Planner, Core/Werker nieuw | contract 1.3, B03-017, B03-009 (t/m cc3e82b4d); CI niet beoordeeld | S-G1-15 (half werk, geparkeerd tot dan: vorm D); review: S-P2-800 (contract 1.3, e294f84ea..945eb8113) en S-G1-17 (golf 1, 945eb8113..cc3e82b4d) | [ ] |

## Fase P2 (STAPPEN_P2.md; 46 stappen)

De volgorde binnen een baan en wat tegelijk mag staat in "Volgorde en banen" van STAPPEN_P2.md; deze tabel volgt de volgorde van het bestand.
Kolommen klaar, commit, CI-run, datum en opmerking vult de regisseur in; de andere kolommen maakt maak_voortgang.py uit het stapbestand (ingekort; de stap is leidend).

| klaar | stap-ID | titel | baan (repo) | vooraf (ingekort; de stap is leidend) | zwaar | moeilijkheid | niveau (afwijkingen) | verplichte reviewers | commit | CI-run | datum | opmerking |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [x] | S-P2-000 | Stand opnemen en half werk van ronde 3 veiligstellen | alle elf repos, alleen lezen (uitzonder… | ronde 3 is gestopt (afgebroken op 2026-11-11 om 09:52; <WER… | nee | gewoon | A-VERKEN N2 (één subagent voor het tellen en de vergelijking met [CON… | R-EERLIJK | geen (alleen lezen) | n.v.t. (HEAD-runs per repo in dossier) | 2026-11-11 | Nulmeting: alle 11 repos gelijk aan remote; half werk = reservekopie; 92 NU-punten plus C1.3-ALG-05 (93 regels in deel C) staan op Bezig; 41 ID/repo-combinaties zonder EVIDENCE (dossier). R-EERLIJK: eerst KLOPT NIET (2x klein), na verwerking KLOPT (RAPPORT-R-EERLIJK-2.md). Stopvoorwaarde "half werk zonder stap" opgelost door het plan (S-P2-005/290/295/395/590/800, S-G1-15). |
| [ ] | S-P2-005 | Half werk van ronde 3 afmaken: acties, goedkeuringen en de wijziginge… | ai-server-manager | S-P2-000 (de werkmap is daar gelijk bevonden aan de reserve… | ja | hoog | A-BOUW en A-HERSTEL N4 (half werk van een ander in de veiligheidskern… | R-TECH, R-VEILIG, R-HARDE-EIS, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-010 | Policy-pakket en risicoclassificatie controleren en vastleggen | ai-server-manager | S-P2-005 | nee | gewoon | standaard. R-VEILIG hier N4; de N5-review van de policy-kern gebeurt… | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-020 | Executor: TrueNAS-schrijfsleutel, NAS-verbinding en executorpagina | ai-server-manager | S-P2-010 | nee | hoog | A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); verder standaard. | R-TECH, R-VEILIG, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-030 | Executor: ExecutionRequest verifiëren, uitvoeren en teruglezen | ai-server-manager | S-P2-020 | nee | zeer hoog | A-BOUW N5 alleen als er nog kerncode van de punten 1 t/m 5 gebouwd mo… | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-040 | Hub: voorstel, preview, goedkeuring en ondertekening | ai-server-manager | S-P2-030 | ja | zeer hoog | A-BOUW N5 alleen als na S-P2-005 nog kerncode van de punten 2 t/m 6 g… | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-050 | Hub: apps installeren, bijwerken, terugzetten en verwijderen | ai-server-manager | S-P2-040; S-P2-400 gepusht (de planner van jelly-leon-platf… | nee | hoog | A-BOUW en A-HERSTEL N4; verder standaard. | R-TECH, R-VEILIG, R-HARDE-EIS, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-060 | Hub: dynamische blokkades en gates (pool, back-up, boiler) | ai-server-manager | S-P2-050 | nee | hoog | A-BOUW en A-HERSTEL N4; verder standaard. | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-070 | Geheimen van catalogusapps via de vault | ai-server-manager | S-P2-060; S-P2-500 gepusht (appstore-en-fork levert de vaul… | nee | hoog | A-BOUW en A-HERSTEL N4; verder standaard. | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-080 | Hub: acties via de eigenaar-connector, catalogusroute en ontkoppelen | ai-server-manager | S-P2-070 | nee | hoog | A-BOUW en A-HERSTEL N4; verder standaard. | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-090 | Back-up: OneDrive-verificatie, herstelpunten per app en pre-update-ga… | ai-server-manager | S-P2-080 | nee | hoog | A-BOUW en A-HERSTEL N4; verder standaard. | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-100 | Back-up: hersteltest-robot en rampenscenario | ai-server-manager | S-P2-090 | nee | hoog | A-BOUW en A-HERSTEL N4; verder standaard. | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-110 | AI deel A: rechten en kosten, kennisinstrumenten, triage en plan-engi… | ai-server-manager | S-P2-100 | nee | hoog | A-BOUW en A-HERSTEL N4; verder standaard. | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-120 | AI deel B: zelfreparatie, updates, automatiserings-AI en feedback | ai-server-manager | S-P2-110 | nee | hoog | A-BOUW en A-HERSTEL N4; verder standaard. | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-130 | AI-chat-backend en veiligheidstests als releasepoort | ai-server-manager | S-P2-120 | nee | hoog | A-BOUW en A-HERSTEL N4; verder standaard. | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-140 | Automatiseringen zonder code, Hub-kant | ai-server-manager | S-P2-130; S-P2-310 gepusht (home-control-hub levert flow.ac… | nee | hoog | A-BOUW en A-HERSTEL N4; verder standaard. | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-150 | Monitorplan per app | ai-server-manager | S-P2-140 | nee | gewoon | standaard | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-160 | Ontwerpstap voor de P2-schermen van de Hub | ai-server-manager | S-P2-150 (de routes van de backend staan dan in docs/openap… | nee | hoog | A-ONTWERP N4 (22 schermen die bij elkaar moeten passen); A-HERSTEL N4… | R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-170 | UI: goedkeuringen, actie-preview en uitvoering | ai-server-manager | S-P2-160 | ja | hoog | A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); verder standaard. | R-TECH, R-VEILIG, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-180 | UI: apps installeren, bijwerken, terugzetten en verwijderen | ai-server-manager | S-P2-170 | ja | hoog | A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); verder standaard. | R-TECH, R-HARDE-EIS, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-190 | UI: back-ups en automatiseringen | ai-server-manager | S-P2-180 | ja | gewoon | standaard | R-TECH, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-200 | UI: AI-chat, monitorplan, "Geïmporteerd" en E15 | ai-server-manager | S-P2-190 | ja | gewoon | standaard | R-TECH, R-VEILIG, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-210 | Beveiligingsreview van P2 als geheel | ai-server-manager | S-P2-200 | nee | zeer hoog | R-VEILIG N5 (beide keren). Winst: dit is de enige plek waar policy, o… | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-220 | Images, rooktest, OpenAPI en schermafdrukken | ai-server-manager | S-P2-210 | ja | gewoon | standaard | R-TECH, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-290 | Half werk van ronde 3 afmaken: B11-afronding (documentatie, manifest,… | home-control-hub | S-P2-000 (werkmap gelijk aan de reservekopie) | ja | gewoon | standaard | R-TECH, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-295 | Review van de twaalf B11-commits (f07a546..076f964) en hun CI | home-control-hub | S-P2-290 gepusht (werkmap schoon) | nee | hoog | R-VEILIG N4, R-HARDE-EIS N4, A-HERSTEL N4 (beveiligingsherstel); verd… | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-300 | B11: eventcatalogus, inname, wachtrij en proefrun | home-control-hub | S-P2-295 | nee | gewoon | standaard (het halve werk is in S-P2-290 en S-P2-295 al vastgelegd en… | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-310 | B11: veilige acties, flow-tokens en isolatie van Node-RED | home-control-hub | S-P2-300 | nee | hoog | A-BOUW en A-HERSTEL N4; verder standaard. | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-320 | B11: momentopnamen, versies en herstel van flows | home-control-hub | S-P2-310 | nee | hoog | A-BOUW en A-HERSTEL N4; verder standaard. | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-330 | Connector: Authentik-acties toepassen met een ondertekend verzoek, en… | home-control-hub | S-P2-320; S-P2-040 gepusht (de Hub ondertekent). Voor de ca… | nee | hoog | A-BOUW en A-HERSTEL N4; verder standaard. | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-340 | home-control-hub: image, rooktest en proef tegen de echte Hub | home-control-hub | S-P2-330; S-P2-080 gepusht en S-P2-140 gepusht (de Hub kent… | ja | gewoon | standaard | R-TECH, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-395 | Review P2 opnieuw en volledig (2f5fa76..HEAD), met het halve werk ADR… | jelly-leon-platform | S-P2-000 (werkmap gelijk aan de reservekopie) | nee | hoog | A-BOUW en A-HERSTEL N4 (moeilijkheid hoog; ook A-BOUW, al legt hij al… | R-TECH, R-VEILIG, R-HARDE-EIS, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-400 | Lifecycle-planner controleren en het bewijs bijwerken | jelly-leon-platform | S-P2-395 | nee | gewoon | standaard | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-410 | Node-RED: installatiemanifest (met besluit C-11), flowbundels en cont… | jelly-leon-platform | S-P2-400 | ja | hoog | A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); verder standaard. | R-TECH, R-VEILIG, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-420 | jelly-leon-platform: rooktest en conformiteit tegen de echte Hub-code | jelly-leon-platform | S-P2-410; S-P2-050 en S-P2-080 gepusht (de Hub neemt planne… | ja | hoog | A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); verder standaard. | R-TECH, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-500 | Geheime waarden van catalogusapps: alleen een verwijzing naar de vault | appstore-en-fork | S-P2-000. Deze stap loopt vóór S-P2-070 (de Hub-kant, C1.3-… | nee | hoog | A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); verder standaard. | R-TECH, R-VEILIG, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-510 | Manifeststandaard: ontwerp van een voorziening voor een beheerder en… | appstore-en-fork | S-P2-500 (zelfde repo, één schrijver per repo); besluit C-1… | nee | hoog | A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); verder standaard (R-VEILI… | R-VEILIG, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-590 | MediaGuard: ontwerpreview van het mediaserver-tabblad afmaken (half w… | media-guard-ultimate | S-P2-000 (werkmap gelijk aan de reservekopie) | ja | gewoon | standaard | R-TECH, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-600 | MediaGuard: technische review van twee mediaservers, aanmelden per se… | media-guard-ultimate | S-P2-590 gepusht (werkmap schoon; de ontwerpreview van het… | ja | hoog | R-HARDE-EIS N5 (geval a van AGENTEN 7.3: echte migratiecode op de dat… | R-TECH, R-VEILIG, R-HARDE-EIS, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-610 | MediaGuard: upgradebewijs vanaf de vorige release (1.2.2) | media-guard-ultimate | S-P2-600 (de mediaservercode is dan definitief voor P2) | ja | hoog | R-HARDE-EIS N4 (geen N5: het commitbereik van deze stap bevat alleen… | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-620 | MediaGuard: Android-app in en-US controleren | media-guard-ultimate | S-P2-610 (één schrijver per repo) | ja | gewoon | standaard | R-TECH, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-700 | my_house: technische review van de tabel en grafiek "Laatste 24 uur"… | my_house | S-P2-000 | ja | gewoon | standaard | R-TECH, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-800 | jelly-leon: review van contract 1.3 (e294f84ea..945eb8113) | jelly-leon | S-P2-000. A-HERSTEL mag alleen schrijven als het halve werk… | nee | gewoon | standaard | R-TECH, R-HARDE-EIS, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-850 | jelly-leon-web: neutrale testwaarde in plaats van een nep-GitHub-toke… | jelly-leon-web | S-P2-000; besluit Z-05 genomen (ja, 2026-11-11) | nee | gewoon | A-BOUW N2 (kleine mechanische stap, besluit van de regisseur); verder… | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-P2-900 | Bewijs samenvoegen: programmabewijs, Excel en STATUS | ai-server-manager | S-P2-005 t/m S-P2-850 zijn in <WERKMAP>/.lokaal/plan/uit/VO… | nee | gewoon | standaard | R-EERLIJK |  |  |  |  |
| [ ] | S-P2-910 | Gate P2: onafhankelijke controle | ai-server-manager, home-control-hub, je… | S-P2-900 afgevinkt; er is in geen van de zes repos een kete… | ja | zeer hoog | A-GATE N5. Winst: dit is de enige plek waar iemand zonder voorkennis… | R-EERLIJK |  |  |  |  |

## Fase P3 (STAPPEN_P3.md; 84 stappen)

De volgorde binnen een baan en wat tegelijk mag staat in "Volgorde en banen" van STAPPEN_P3.md; deze tabel volgt de volgorde van het bestand.
Kolommen klaar, commit, CI-run, datum en opmerking vult de regisseur in; de andere kolommen maakt maak_voortgang.py uit het stapbestand (ingekort; de stap is leidend).

| klaar | stap-ID | titel | baan (repo) | vooraf (ingekort; de stap is leidend) | zwaar | moeilijkheid | niveau (afwijkingen) | verplichte reviewers | commit | CI-run | datum | opmerking |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [ ] | S-P3-000 | Stand opnemen, half werk veiligstellen en open besluiten nalopen | de zeven repos van P3 (alleen lezen) | geen | nee | gewoon | standaard | R-EERLIJK |  |  |  |  |
| [ ] | S-P3-010 | ADR: adapters voor de bestaande apps | ai-server-manager | S-P3-000 klaar; in deze repo werkt geen schrijver van P2 | nee | gewoon | standaard | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-015 | ADR: MediaGuard-upgradebewijs in de Hub en rotatie bij een geplakte s… | ai-server-manager | S-P3-010 klaar; antwoord op Z-03 of de regel "zonder beslui… | nee | gewoon | standaard | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-020 | Hub: basis voor koppelingen met bestaande apps (opslag, geheim, uitga… | ai-server-manager | S-P3-010 klaar (het ADR bepaalt map en opslag) | nee | hoog | A-BOUW N4, A-HERSTEL N4 (moeilijkheid hoog); verder standaard | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-030 | Hub: adapter MediaGuard (alleen lezen) | ai-server-manager | S-P3-020 klaar. S-P2-600 klaar of de terugval uit bouwpunt… | nee | hoog | A-BOUW N4, A-HERSTEL N4; verder standaard | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-040 | Hub: adapter Media Source Optimizer (alleen lezen) | ai-server-manager | S-P3-020 klaar | nee | gewoon | standaard | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-050 | Hub: adapter my_house (alleen lezen, koppelcode) | ai-server-manager | S-P3-020 klaar | nee | hoog | A-BOUW N4, A-HERSTEL N4; verder standaard | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-060 | Hub: gezondheid van de binnenkant via de adapters | ai-server-manager | S-P3-030, S-P3-040 en S-P3-050 klaar | nee | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-070 | Hub-UI: bestaande apps koppelen (sleutel of koppelcode invoeren) | ai-server-manager | S-P3-060 klaar | nee | gewoon | standaard | R-TECH, R-VEILIG, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-075 | Hub: incident- en downloadketen over MediaGuard en MSO (backend) | ai-server-manager | S-P3-030 en S-P3-040 klaar | nee | gewoon | standaard | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-080 | Hub-UI: scherm Media (MediaGuard en MSO) | ai-server-manager | S-P3-075 klaar | nee | gewoon | standaard | R-TECH, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-090 | Hub-UI: scherm Huis (my_house, alleen kijken) | ai-server-manager | S-P3-050 klaar | nee | gewoon | standaard | R-TECH, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-100 | Hub: back-updekking van de bestaande apps en het Emby-exportarchief | ai-server-manager | S-P3-030, S-P3-040 en S-P3-050 klaar; S-P2-090 klaar | nee | hoog | A-BOUW N4, A-HERSTEL N4; verder standaard | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-110 | Hub: noodstop AAN in MediaGuard via het goedkeuringspad | ai-server-manager | Gate P2 afgevinkt; S-P3-600 gepusht (scope emergency_stop:o… | nee | hoog | A-BOUW N4, A-HERSTEL N4 (moeilijkheid hoog); verder standaard. Geen t… | R-TECH, R-VEILIG, R-HARDE-EIS, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-120 | Hub: een MSO-wijziging goedkeuren via de Hub | ai-server-manager | Gate P2 afgevinkt; S-P3-240 gepusht (MSO kent expected_prev… | nee | hoog | A-BOUW N4, A-HERSTEL N4; verder standaard | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-130 | Hub: bewaakt schrijfpad naar my_house (ondertekend verzoek) | ai-server-manager | Gate P2 afgevinkt; S-P3-742 gepusht; S-P3-050 klaar; S-P3-0… | nee | hoog | A-BOUW N4, A-HERSTEL N4; verder standaard. Geen topmodel: de kern van… | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-150 | Hub: energie en kosten met herkomst (backend) | ai-server-manager | S-P3-040 klaar; S-P3-310 gepusht (of het ADR van S-P3-010 w… | nee | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-160 | Hub-UI: scherm Kosten | ai-server-manager | S-P3-150 klaar | nee | gewoon | standaard | R-TECH, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-170 | Hub: images, rooktest, OpenAPI en schermafdrukken van P3 | ai-server-manager | alle eerdere stappen van deze baan klaar, behalve stappen d… | ja | gewoon | standaard | R-TECH, R-MANIFEST, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-180 | A-documenten: vastleggen wat het platform nu dekt (A09...A14, A17...A… | ai-server-manager | S-P3-170 klaar | nee | gewoon | standaard | R-EERLIJK |  |  |  |  |
| [ ] | S-P3-200 | MSO: opruimen en CI op de werkbranch | media-source-optimizer | S-P3-000 klaar; besluit Z-10 genomen of de regel "zonder be… | nee | gewoon | A-BOUW N2 (kleine mechanische stap); verder standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-205 | MSO: weiger een database van een nieuwere versie | media-source-optimizer | S-P3-200 klaar | nee | hoog | A-BOUW N4, A-HERSTEL N4 (moeilijkheid hoog: migratiecode); verder sta… | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-210 | MSO: build-gegevens op de Systeem-kaart | media-source-optimizer | S-P3-200 klaar | ja | gewoon | standaard | R-TECH, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-215 | MSO: terugkeerpad na inloggen volgens het contract | media-source-optimizer | S-P3-200 klaar | nee | gewoon | A-BOUW N2 (kleine mechanische stap); verder standaard | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-220 | MSO: machine-sleutel met scopes | media-source-optimizer | S-P3-200 klaar | nee | hoog | A-BOUW N4, A-HERSTEL N4; R-VEILIG N5 - Winst: dit is de kern van de a… | R-TECH, R-VEILIG, R-HARDE-EIS, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-230 | MSO: connector, leesdeel | media-source-optimizer | S-P3-220 klaar | nee | gewoon | standaard | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-240 | MSO: wijzigingen via de connector, gebonden aan preview_hash | media-source-optimizer | S-P3-230 klaar | nee | hoog | A-BOUW N4, A-HERSTEL N4 (moeilijkheid hoog: gelijktijdigheid); verder… | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-250 | MSO: healthcheck die eerst naar 568 wisselt | media-source-optimizer | S-P3-200 klaar | ja | hoog | A-BOUW N4, A-HERSTEL N4 (moeilijkheid hoog: rechten en procesboom); v… | R-TECH, R-VEILIG, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-255 | MSO: vaste digests, SBOM en afhankelijkheidscontrole | media-source-optimizer | S-P3-250 klaar | ja | gewoon | A-BOUW N2 (kleine mechanische stap); verder standaard | R-TECH, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-260 | MSO: upgradetest vanaf de vorige image | media-source-optimizer | S-P3-205 en S-P3-255 klaar | ja | hoog | A-BOUW N4, A-HERSTEL N4; verder standaard. Geen topmodel: dit is een… | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-265 | MSO: contracttest tegen de echte MediaGuard-image | media-source-optimizer | S-P3-200 klaar | ja | gewoon | standaard (R-HARDE-EIS N4) | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-270 | MSO: opslag en groei met herkomst | media-source-optimizer | S-P3-210 klaar | ja | gewoon | standaard (R-HARDE-EIS N4) | R-TECH, R-HARDE-EIS, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-280 | MSO: Peil-ronde en schermbreedtes | media-source-optimizer | S-P3-270 klaar | ja | gewoon | standaard | R-TECH, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-290 | MSO: manifest en installatiedocument (standaard Custom App) | media-source-optimizer | S-P3-250 en S-P3-255 klaar | nee | gewoon | standaard | R-TECH, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-300 | Energie: bron my_house en de dekkingsmatrix | home-control-hub | S-P3-010 klaar (het ADR wijst aan wie de energiecijfers van… | nee | gewoon | standaard | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-310 | Energie: tijdreeks met zomertijd, tellerreset en metervervanging | home-control-hub | S-P3-300 klaar | nee | hoog | A-BOUW N4, A-HERSTEL N4 (moeilijkheid hoog: tijdrekenen en idempotent… | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-320 | Energie: werklast en reserveringen (alleen plannen en voorstellen) | home-control-hub | S-P3-310 klaar | nee | gewoon | standaard (R-HARDE-EIS N4) | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-330 | Energie: advies over kosten met aannames en bandbreedte | home-control-hub | S-P3-310 en S-P3-320 klaar | nee | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-340 | Energie: meldingen bij afwijkingen | home-control-hub | S-P3-310 klaar | nee | gewoon | standaard | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-350 | Energie op de statuspagina van de dienst | home-control-hub | S-P3-340 klaar | nee | gewoon | standaard | R-TECH, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-360 | home-control-hub: Node-RED-beveiligingsprofiel uitfaseren of gelijktr… | home-control-hub | S-P3-350 klaar (een schrijver per repo); S-P3-490 gepusht (… | nee | hoog | standaard (moeilijkheid hoog: A-BOUW en A-HERSTEL N4) | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-400 | Platform: ADR en gereedschap voor de controlelijsten I03...I20 | jelly-leon-platform | S-P3-000 klaar; geen keten van P2 actief in deze repo | nee | gewoon | standaard | R-TECH, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-410 | Platform: controlelijsten I03 (MediaGuard) en I04 (Media Source Optim… | jelly-leon-platform | S-P3-400 klaar | nee | gewoon | standaard (R-HARDE-EIS N4; dit is tekst, geen migratiecode, dus geen… | R-TECH, R-HARDE-EIS, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-420 | Platform: controlelijsten I15 (Immich), I16 (Prowlarr) en I17 (SABnzb… | jelly-leon-platform | S-P3-400 klaar | nee | gewoon | standaard | R-TECH, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-430 | Platform: controlelijsten I18 (qBittorrent), I19 (Seerr) en I20 (Baza… | jelly-leon-platform | S-P3-400 klaar | nee | gewoon | standaard | R-TECH, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-440 | Platform: controlelijst I05 (my_house) met de standaard Custom App al… | jelly-leon-platform | S-P3-400 klaar; besluit Z-18 (BESLUITEN, deel 2.15, kop "Z-… | nee | gewoon | standaard | R-TECH, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-445 | Platform: Node-RED-manifest op de voorziening voor beheerder en diens… | jelly-leon-platform | S-P3-440 klaar (een schrijver per repo; deze stap hangt nie… | ja | hoog | standaard (moeilijkheid hoog: A-BOUW en A-HERSTEL N4) | R-TECH, R-VEILIG, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-450 | Platform: manifestkopieen van MediaGuard, MSO en my_house | jelly-leon-platform | S-P3-290, S-P3-660 en S-P3-755 gepusht (de drie manifesten… | nee | gewoon | standaard | R-TECH, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-490 | Appstore: voorziening voor een beheerder en een dienstaccount zonder… | appstore-en-fork | S-P3-000 klaar; S-P2-510 (de ontwerpstap van C-12 in de baa… | nee | hoog | standaard (moeilijkheid hoog: A-BOUW en A-HERSTEL N4) | R-TECH, R-VEILIG, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-500 | Appstore: register van de bestaande apps laten meebewegen met de A-do… | appstore-en-fork | S-P3-180 gepusht (de A-documenten zijn bijgewerkt in ai-ser… | nee | gewoon | A-BOUW N2 (kleine mechanische stap); verder standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-600 | MediaGuard: scopes op API-sleutels | media-guard-ultimate | S-P3-000 klaar; S-P2-610 en S-P2-620 klaar (een schrijver p… | ja | hoog | A-BOUW N4, A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N5 - Winst: dit… | R-TECH, R-VEILIG, R-HARDE-EIS, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-610 | MediaGuard: connector deel 1 (discover, health, healthz, readyz) | media-guard-ultimate | S-P3-600 klaar | ja | gewoon | standaard | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-615 | MediaGuard: connector deel 2 (items, evidence en de vijf datasets) | media-guard-ultimate | S-P3-610 klaar | ja | gewoon | standaard | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-620 | MediaGuard: events met cursor | media-guard-ultimate | S-P3-610 klaar | ja | gewoon | standaard | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-625 | MediaGuard: bescherming tegen een database van een nieuwere versie | media-guard-ultimate | S-P3-600 klaar (de nieuwe migratie 005_api_key_scopes.sql i… | ja | hoog | [N5] A-BOUW N4, A-HERSTEL N4 (moeilijkheid hoog: migratiecode); R-HA… | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-630 | MediaGuard: correlatie-ID op externe verzoeken | media-guard-ultimate | S-P3-610 klaar | ja | gewoon | A-BOUW N2 (kleine mechanische stap); verder standaard | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-635 | MediaGuard: herstelrapport voor de Hub | media-guard-ultimate | S-P3-615 klaar | ja | gewoon | standaard | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-640 | MediaGuard: download-opruimer volgt een gemeten zieke pool | media-guard-ultimate | S-P3-600 klaar | ja | gewoon | standaard | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-645 | MediaGuard: contracttest met de routes die MSO gebruikt | media-guard-ultimate | S-P3-600 klaar | ja | gewoon | standaard | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-650 | MediaGuard: healthcheck die eerst naar 568 wisselt | media-guard-ultimate | S-P3-610 klaar (de healthcheck gebruikt /readyz) | ja | hoog | A-BOUW N4, A-HERSTEL N4 (moeilijkheid hoog: rechten en procesboom); v… | R-TECH, R-VEILIG, R-HARDE-EIS, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-655 | MediaGuard: terugkeerpad na inloggen volgens het contract | media-guard-ultimate | S-P3-600 klaar | ja | gewoon | A-BOUW N2 (kleine mechanische stap); verder standaard | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-660 | MediaGuard: manifest en installatiedocument (standaard Custom App) | media-guard-ultimate | S-P3-650 klaar (het manifest noemt de nieuwe healthcheck) | ja | gewoon | standaard | R-TECH, R-HARDE-EIS, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-665 | MediaGuard: vaste digests, SBOM en release/digests.json | media-guard-ultimate | S-P3-650 klaar | ja | gewoon | A-BOUW N2 (kleine mechanische stap); verder standaard | R-TECH, R-HARDE-EIS, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-670 | MediaGuard: begrensde platformpauze voor AV1 | media-guard-ultimate | S-P3-600 klaar | ja | hoog | A-BOUW N4, A-HERSTEL N4 (moeilijkheid hoog: gelijktijdigheid van twee… | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-675 | MediaGuard: Jellyfin-pad behouden en verversen melden | media-guard-ultimate | S-P3-620 klaar (events met cursor) | ja | hoog | A-BOUW N4, A-HERSTEL N4 (moeilijkheid hoog: raakt de mediaservercode… | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-680 | MediaGuard: Peil-ronde web (768 breed, toetsenbord) en kernteksten | media-guard-ultimate | S-P3-615 klaar | ja | gewoon | standaard | R-TECH, R-HARDE-EIS, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-685 | MediaGuard: Peil-ronde Android | media-guard-ultimate | S-P3-680 klaar (zelfde teksten en ontwerp) | ja | gewoon | standaard | R-TECH, R-HARDE-EIS, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-690 | MediaGuard: poolstatus van de Hub als extra invoer (ADR eerst) | media-guard-ultimate | S-P3-640 klaar (of de Hub de poolstatus al aanbiedt, stelt… | ja | gewoon | standaard | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-700 | my_house: weiger een database van een nieuwere versie | my_house | S-P3-000 klaar; S-P2-700 klaar (een schrijver per repo) | nee | hoog | A-BOUW N4, A-HERSTEL N4 (moeilijkheid hoog: migratiecode); verder sta… | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-705 | my_house: boilerblokkade als regressietest op elke weg | my_house | S-P3-700 klaar | nee | gewoon | standaard | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-710 | my_house: inbedrijfstellingsgate (geen bediening van ongeteste appara… | my_house | S-P3-705 klaar | nee | gewoon | standaard | R-TECH, R-VEILIG, R-HARDE-EIS, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-715 | my_house: tests voor verouderde sensoren, commando-TTL en herstart, e… | my_house | S-P3-700 klaar | nee | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-720 | my_house: alles-in-een image deel 1 (image, bewaker, healthcheck, eer… | my_house | S-P3-700 klaar (de herstelmodus bij een nieuwer schema hoor… | ja | hoog | A-BOUW N4, A-HERSTEL N4 (moeilijkheid hoog: procesboom, rechten, gehe… | R-TECH, R-VEILIG, R-HARDE-EIS, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-725 | my_house: alles-in-een image deel 2 (CI, rooktest, digests) | my_house | S-P3-720 klaar | ja | gewoon | standaard | R-TECH, R-VEILIG, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-730 | my_house: herstel en overstap zonder terminal | my_house | S-P3-725 klaar | nee | hoog | A-BOUW N4, A-HERSTEL N4 (moeilijkheid hoog); verder standaard | R-TECH, R-VEILIG, R-HARDE-EIS, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-735 | my_house: proef back-up A naar herstel B met twee alles-in-een contai… | my_house | S-P3-730 klaar | ja | gewoon | standaard | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-740 | my_house: verificatiekern voor ondertekende verzoeken en de geplakte… | my_house | S-P3-700 klaar; S-P3-015 gepusht (ADR over rotatie bij een… | nee | hoog | A-BOUW N4, A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N5 - Winst: dit… | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-742 | my_house: routes propose, apply, rollback en evidence | my_house | S-P3-740, S-P3-705 en S-P3-710 klaar | nee | hoog | A-BOUW N4, A-HERSTEL N4 (moeilijkheid hoog); verder standaard. Geen t… | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-745 | my_house: scherm om de Hub-sleutelset te plakken en te controleren | my_house | S-P3-740 klaar | nee | gewoon | standaard | R-TECH, R-VEILIG, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-750 | my_house: terugkeerpad na inloggen volgens het contract | my_house | S-P3-700 klaar | nee | gewoon | A-BOUW N2 (kleine mechanische stap); verder standaard | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-755 | my_house: manifest en installatiedocument (standaard Custom App) | my_house | S-P3-725 klaar | nee | gewoon | standaard | R-TECH, R-VEILIG, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-765 | my_house: schermbreedtes, schermafdrukken en huishouding | my_house | S-P3-755 klaar | nee | gewoon | standaard | R-TECH, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P3-900 | Bewijs samenvoegen: programmabewijs, Excel en STATUS | ai-server-manager | alle stappen S-P3-000 tot en met S-P3-765 zijn in <WERKMAP>… | nee | gewoon | standaard | R-EERLIJK |  |  |  |  |
| [ ] | S-P3-910 | Gate P3: onafhankelijke controle | ai-server-manager, media-guard-ultimate… | S-P3-900 afgevinkt; in geen van de zeven repos is een keten… | ja | hoog | A-GATE N5 - Winst: dit is de enige plek waar iemand zonder voorkennis… | R-EERLIJK |  |  |  |  |

## Fase P4: P4-0, golf 1 en golf 2 (STAPPEN_P4_GOLF1_2.md; 58 stappen)

De volgorde binnen een baan en wat tegelijk mag staat in "Volgorde en banen" van STAPPEN_P4_GOLF1_2.md; deze tabel volgt de volgorde van het bestand.
Kolommen klaar, commit, CI-run, datum en opmerking vult de regisseur in; de andere kolommen maakt maak_voortgang.py uit het stapbestand (ingekort; de stap is leidend).

| klaar | stap-ID | titel | baan (repo) | vooraf (ingekort; de stap is leidend) | zwaar | moeilijkheid | niveau (afwijkingen) | verplichte reviewers | commit | CI-run | datum | opmerking |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [ ] | S-P40-10 | Stand P4-0 vaststellen (dossier voor de gate) | geen wijziging; leest in jelly-leon, je… | geen | nee | gewoon | standaard (A-VERKEN N2, R-EERLIJK N3) | R-EERLIJK |  |  |  |  |
| [ ] | S-P40-20 | MediaGuard: aanmelden per server en twee mediaservers bewijzen met de… | media-guard-ultimate | S-P40-10 klaar; BG-01 genomen; S-P2-600 en S-P2-610 uit <WE… | ja | gewoon | R-VEILIG N4; R-HARDE-EIS N4 (geen topmodel: de migratie en het upgrad… | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P40-30 | JLT-73 afmaken: overnameproef tegen de Jelly Leon-image met het bewij… | jelly-leon | S-P40-20 klaar (contracttest met de Jelly Leon-image gedraa… | ja | gewoon | standaard; R-HARDE-EIS N4, R-VEILIG N4 (geen N5: de stap wijzigt geen… | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P40-32 | Clientdeel JLT-70 voorbereiden: de proefrun laat een overdracht voor… | jelly-leon | S-P40-30 klaar | ja | gewoon | standaard; R-VEILIG N4, R-HARDE-EIS N4 | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P40-40 | Register upstream-gedrag en clientmatrix aanvullen (B03-019) | jelly-leon | S-G1-16 klaar (schone werkboom, lokale image). WP-JSON B03-… | ja | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-P40-45 | Sync-proef en negatieve upgradeproef met een 12.y-tag (voorwaardelijk) | jelly-leon (de webproef in bouwpunt 5 i… | S-P40-40 klaar; upstream heeft een 12.x-tag die nieuwer is… | ja | hoog | A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); R-HARDE-EIS N4 | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P40-50 | Definitieve baselines en controle-run op de forkbasis (B03-016) | jelly-leon | S-P40-90 klaar; de keuze "voormeting 12.4 telt als definiti… | ja | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-P40-60 | Voormeting Watch Together (B03-020) | jelly-leon | S-P40-50 klaar. WP-JSON B03-020 (veld Afhankelijkheid) noem… | ja | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-P40-62 | Voormeting aanbevelingen (B03-030) | jelly-leon | S-P40-50 klaar; BG-37 (genomen: beperkt gelicentieerde test… | ja | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-P40-64 | Voormeting apparaten en afspeelfouten (B03-060) | jelly-leon | S-P40-50 klaar | ja | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-P40-66 | Meetlat segmenten: bevroren testset, harnas en baselines (B03-070) | jelly-leon | S-P40-50 klaar; BG-32 (Intro Skipper alleen als testbaselin… | ja | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-P40-70 | Tablet-emulator en het emulatordeel van JLT-60, JLT-63 en JLT-70 | jelly-leon-clients | S-P40-72 klaar; voor bouwpunt 4 en 5: S-P40-32 klaar (overd… | ja | gewoon | standaard; R-HARDE-EIS N4 (kijkt alleen naar het JLT-70-deel: klopt h… | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P40-72 | Compat-harnas veiliger maken: eigen netwerk, willekeurige testwachtwo… | jelly-leon-clients | S-P40-10 klaar | ja | gewoon | standaard; R-VEILIG N4 | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P40-92 | Bewijs uit de andere repos overnemen in jelly-leon (JLT-60, JLT-70, c… | jelly-leon | S-P40-70 klaar; S-P40-20 klaar; S-P40-50 klaar | nee | gewoon | standaard | R-EERLIJK |  |  |  |  |
| [ ] | S-P40-80 | Overname-assistent: ontwerp en ADR (geen terminal voor de gebruiker) | jelly-leon | S-P40-30 klaar; BG-22 genomen of de terugval uit hoofdstuk… | nee | gewoon | standaard; R-VEILIG en R-HARDE-EIS N4 | R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P40-82 | Overname-assistent bouwen in het beheer van Jelly Leon | jelly-leon | S-P40-80 klaar en de runtime gekozen; S-G1-14 klaar (pijpli… | ja | hoog | [N5] A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4; R-HARD… | R-TECH, R-VEILIG, R-HARDE-EIS, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P40-90 | Desktop-spike in het meetharnas bijwerken | jelly-leon | S-P40-40 klaar | ja | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-P40-95 | Gate P4-0 | geen (A-GATE leest in jelly-leon, jelly… | S-P40-20, S-P40-30, S-P40-32, S-P40-40, S-P40-50, S-P40-70,… | nee | gewoon | A-GATE N5. Winst: dit is het einde van de fase P4-0; een gate die hie… | - |  |  |  |  |
| [ ] | S-G1-15 | Half werk van B03-018 uit ronde 3 overnemen, groen maken en vastleggen | jelly-leon | S-P40-10 klaar. Geen besluit nodig. | ja | gewoon | standaard (R-VEILIG N4) | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-G1-17 | Review van de gepushte golf-1-vastleggingen (B03-017, B03-009; 8a2937… | jelly-leon | S-G1-15 klaar (werkboom schoon); S-P2-800 in <WERKMAP>/.lok… | nee | gewoon | standaard (R-VEILIG N4, R-HARDE-EIS N4; het topmodel voor de Hub-kern… | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G1-16 | Stand B03-017 vastzetten: werkboom schoon, poort groen, lokale image… | jelly-leon | S-P40-10, S-G1-15, S-P2-800 (STAPPEN_P2.md) en S-G1-17 klaa… | ja | gewoon | standaard (R-HARDE-EIS N4) | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G1-10 | Kern B03-017 controleren: prototype op fork en stock, JLT-68, JLT-64… | jelly-leon | S-G1-16 klaar (lokale image); de P4-0-stappen van de baan j… | ja | gewoon | standaard (R-HARDE-EIS N4) | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G1-12 | Hub-koppeling JL4: beveiligingsreview en herstel | jelly-leon | S-G1-10 klaar | nee | hoog | R-VEILIG N5; A-BOUW en A-HERSTEL N4 (moeilijkheid hoog). Winst: dit i… | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-G1-14 | Foutcatalogus, 1 MiB per route, IStartupFilter-spike, health en events | jelly-leon | S-G1-12 klaar; Gate P4-0 | nee | gewoon | standaard (R-VEILIG N4) | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-G1-18 | Privacy: persoonsgegevensregister, UserDeleted, kinderprofiel | jelly-leon | S-G1-14 klaar; besluit BG-03 genomen, of de terugval uit ho… | nee | gewoon | standaard (R-VEILIG N4, R-HARDE-EIS N4) | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G1-20 | Geheimenmap, mountcontrole, wezenbreker, spoorsleutel, export en impo… | jelly-leon | S-G1-18 klaar | nee | gewoon | standaard (R-VEILIG N4) | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-G1-30 | Analysewerker in de image | jelly-leon | S-G1-20 klaar; Gate P4-0 | ja | gewoon | standaard (R-VEILIG N4) | R-TECH, R-VEILIG, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-G1-32 | Werkerbewaker en socket | jelly-leon | S-G1-30 klaar | ja | hoog | A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4; verder stand… | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-G1-34 | Bestandspas en featurecache | jelly-leon | S-G1-32 klaar | ja | gewoon | standaard (R-HARDE-EIS N4) | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G1-36 | Globale batchplanner | jelly-leon | S-G1-34 klaar | ja | hoog | A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4; verder stand… | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-G1-50 | MediaGuard-viewerclient via de Hub (B03-009) | jelly-leon | S-G1-36 klaar; S-G1-12 klaar; besluit BG-04 genomen (via de… | ja | hoog | A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4; R-HARDE-EIS… | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G1-38 | Budgetbeslisser G1 t/m G10 | jelly-leon | S-G1-50 klaar | nee | hoog | A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); R-HARDE-EIS N4; verder st… | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G1-40 | Gecombineerde belastingtest JLT-66 | jelly-leon | S-G1-38 klaar; de lokale image is opnieuw gebouwd op de sta… | ja | hoog | A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); verder standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G1-60 | Haakmodule in de webclient | jelly-leon-web | S-P40-10 klaar; geen besluit nodig. Deze stap valt buiten P… | ja | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G1-70 | Manifest, CUSTOM_APP en web-verwijzing bijwerken | jelly-leon | S-P40-82 klaar (of uitdrukkelijk uitgesteld door de regisse… | ja | gewoon | standaard | R-TECH, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-G1-80 | Eindrun golf 1: JLT-64, JLT-65, JLT-68 | jelly-leon | S-G1-70 klaar (de image van de eindstand); S-G1-12, S-G1-14… | ja | gewoon | standaard (R-HARDE-EIS N4) | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G1-90 | Gate golf 1 | geen (A-GATE leest in jelly-leon en jel… | S-G1-80 klaar; Gate P4-0 voorgelegd en door de gebruiker be… | nee | gewoon | A-GATE N4 (einde van een golf, niet van een fase) | - |  |  |  |  |
| [ ] | S-G2-10 | Watch Together-kern WT-1: decorator, reconciliatie, fail-closed en AP… | jelly-leon | Gate golf 1 (S-G1-90) door de gebruiker beantwoord; S-P40-6… | ja | hoog | A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4; verder stand… | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-G2-20 | Aanbevelingen F2-1: moduleskelet en Similar-provider (B03-031) | jelly-leon | Gate golf 1; S-P40-62 klaar (baseline aanbevelingen). Geen… | ja | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G2-22 | Aanbevelingen F2-2: klassieke engine en offline-evaluatie (B03-032) | jelly-leon | S-G2-20 klaar; S-P40-62 klaar; BG-37 (genomen). Of D-ML bes… | ja | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G2-24 | Aanbevelingen F2-3: eigen opslag, back-up, vergeten en terug naar sto… | jelly-leon | S-G2-22 klaar. | ja | hoog | A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); R-HARDE-EIS N4; R-VEILIG… | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G2-26 | Aanbevelingen F2-4: profielen, kinderprofiel en huishoudprivacy (B03-… | jelly-leon | S-G2-24 klaar; S-G1-18 klaar (IsKid); BG-16 genomen of de t… | nee | gewoon | standaard (R-VEILIG N4) | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-G2-28 | Aanbevelingen F2-5: API /media/v1/recommendations en events (B03-035) | jelly-leon | S-G2-26 klaar; S-G1-12 en S-G1-14 klaar (Hub-JWT, foutcatal… | nee | gewoon | standaard (R-VEILIG N4) | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-G2-30 | Apparaatprofielen F5-S1: module Devices waarneemt afspeeluitkomsten (… | jelly-leon | Gate golf 1; S-P40-64 klaar (baseline B03-060: de Direct Pl… | ja | gewoon | standaard (R-HARDE-EIS N4, R-VEILIG N4) | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G2-32 | Apparaatprofielen F5-S3: hardwareversnelling-assistent (B03-062) | jelly-leon | S-G2-30 klaar; S-G1-50 klaar (viewerclient: de MediaGuard-l… | ja | hoog | A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4; R-HARDE-EIS… | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G2-34 | Spikes F5-S2 (b) en (e) in de server: MVC-actionfilter en DRM-fdinfo | jelly-leon | S-G2-30 klaar. | ja | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G2-35 | Spikes F5-S2 (c) en (f) in het harnas: dynamic-range via CDP en een s… | jelly-leon | S-G2-34 klaar (alleen omdat de baan jelly-leon een schrijve… | ja | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G2-36 | Spike F5-S2 (d) in de webclient: stall-detectie zonder extra haak | jelly-leon-web | S-G1-60 klaar (haakmodule); Gate golf 1. | ja | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G2-38 | Spike F5-S2 (g) in de clients: rolherkenning van de officiele Android… | jelly-leon-clients | Gate golf 1; S-P40-70 klaar (emulator stabiel); BG-38. | ja | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G2-40 | Segmenten F6-S1: module Segments, provider, eigen opslag en veilige p… | jelly-leon | Gate golf 1; S-P40-66 klaar (bevroren testset); BG-32 (geno… | ja | hoog | A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); R-HARDE-EIS N4; R-VEILIG… | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G2-42 | Segmenten F6-S2: audiofingerprint-engine (B03-072) | jelly-leon | S-G2-40 klaar; S-G1-34 klaar (bestandspas en featurecache);… | ja | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G2-44 | Segmenten F6-S3: aftiteling, post-credit-bescherming en grensverfijni… | jelly-leon | S-G2-42 klaar; BG-35 genomen of de terugval uit hoofdstuk 3… | ja | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G2-46 | Segmenten in de clients: hoofdstuksegmenten in stock-web en de Androi… | jelly-leon-clients | S-G2-40 klaar en gepusht (een lokale jelly-leon-image met d… | ja | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G2-50 | Terug naar stock, compat-regressie en belastingtest met alle golf-2-m… | jelly-leon | S-G2-10, S-G2-28, S-G2-32, S-G2-44 en S-G2-46 klaar. | ja | gewoon | standaard (R-HARDE-EIS N4) | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G2-55 | Manifest en image na golf 2 | jelly-leon | S-G2-50 klaar; BG-07 genomen of de voorlopige waarden (hoof… | ja | gewoon | standaard | R-TECH, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-G2-70 | Controlelijsten I06 (Jellyfin) en I24 (Jelly Leon-release) voor de ge… | jelly-leon-platform | S-P2-420 in <WERKMAP>/.lokaal/plan/uit/STAPPEN_P2.md klaar… | nee | gewoon | standaard (R-HARDE-EIS N4) | R-TECH, R-HARDE-EIS, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-G2-72 | Controlelijst I22 Navidrome (alleen na besluit D18) | jelly-leon-platform | S-G2-70 klaar; besluit D18 (<WERKMAP>/.lokaal/plan/uit/BESL… | nee | gewoon | standaard | R-TECH, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-G2-90 | Gate golf 2 | geen (A-GATE leest in jelly-leon, jelly… | S-G2-55, S-G2-46, S-G2-36, S-G2-38 en S-G2-70 klaar; S-G2-7… | nee | gewoon | A-GATE N4 (einde van een golf, niet van een fase) | - |  |  |  |  |

## Fase P4: golf 3 en golf 4 (STAPPEN_P4_GOLF3_4.md; 89 stappen)

De volgorde binnen een baan en wat tegelijk mag staat in "Volgorde en banen" van STAPPEN_P4_GOLF3_4.md; deze tabel volgt de volgorde van het bestand.
Kolommen klaar, commit, CI-run, datum en opmerking vult de regisseur in; de andere kolommen maakt maak_voortgang.py uit het stapbestand (ingekort; de stap is leidend).

| klaar | stap-ID | titel | baan (repo) | vooraf (ingekort; de stap is leidend) | zwaar | moeilijkheid | niveau (afwijkingen) | verplichte reviewers | commit | CI-run | datum | opmerking |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [ ] | S-G3-01 | Module Quality: fundament, eigen opslag en alleen-lezen-garanties | jelly-leon | S-G2-90 gehaald (gate golf 2; rapport <WERKMAP>/.lokaal/ket… | nee | gewoon | standaard; R-HARDE-EIS N4 | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G3-02 | Jobtypes quality.* en kostenmodel in de globale batchplanner | jelly-leon | S-G3-01; planner en werker van B03-018 aanwezig (Gate golf… | nee | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G3-03 | Module Subtitles: fundament, stabiele spoorsleutels en NL-dekking (al… | jelly-leon | S-G2-90 gehaald (gate golf 2; daarin Gate golf 1 met B03-01… | nee | gewoon | standaard; R-HARDE-EIS N4 | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G3-04 | Watch Together: telemetrieroute en diagnose (serverdeel van B03-024) | jelly-leon | WT-1-gate geslaagd volgens het rapport van S-G2-90 (<WERKMA… | nee | gewoon | standaard; A-BOUW N2 mag als A-VERKEN bevestigt dat de routes alleen… | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G3-28 | Metadata en anime-mapping: externe ID's met versie, zekerheid en eige… | jelly-leon | S-G2-90 gehaald (gate golf 2). Besluit Z-20 genomen (in P4… | nee | hoog | A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); R-HARDE-EIS N4; overig… | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G3-29 | Pluginpagina "Metadata-suggesties" voor beheerders (B03-006, schermde… | jelly-leon | S-G3-28 (routes voor beheerders). | ja | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G3-30 | Universele bibliotheek: anime apart van films en series, met externe… | jelly-leon | S-G3-28 (externe ID's van B03-006; TASKS-JSON B03-002 Uitvo… | nee | hoog | A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); R-HARDE-EIS N4; overig… | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G3-05 | Ondertiteltoolkit in de analysewerker (subtitle.inventory, subtitle.q… | jelly-leon | S-G3-03; analysewerker B03-018 met een vastgepinde Python-o… | ja | gewoon | standaard | R-TECH, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-G3-06 | Ondertitelsync met veiligheidstoetsen (subtitle.sync) | jelly-leon | S-G3-05. Geen besluit nodig (BG-25 gaat over een gecorrigee… | ja | hoog | A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); overige standaard | R-TECH, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-G3-07 | Beslisregels ondertitels en MediaGuard-leesroutes | jelly-leon | S-G3-03; viewerclient B03-009 (golf 1). BG-04 is genomen (v… | nee | gewoon | standaard; R-VEILIG N4 | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-G3-08 | Publicatie van gesynchroniseerde kopieen en beleid voor onthouden spo… | jelly-leon | S-G3-06; BG-19 genomen (zonder besluit stopt deze stap en m… | ja | hoog | [N5] A-BOUW N4 en A-HERSTEL N4; R-HARDE-EIS N4. Alleen als BG-21 res… | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G3-09 | Streamroutes zonder inlog: meting per client, spike en ADR | jelly-leon | S-G2-90 gehaald (gate golf 2; daarin Gate golf 1 met het de… | ja | gewoon | standaard; R-VEILIG N4 | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-G3-10 | Streamroutes: authenticatiefilter bouwen en met clients bewijzen | jelly-leon | S-G3-09 met een ADR die een route kiest. | ja | hoog | A-BOUW N4 en A-HERSTEL N4; R-VEILIG N5. Winst: dit is de inlogcontrol… | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-G3-11 | Kwaliteitscontrole niveau 0, 1 en 1,5 met triggers | jelly-leon | S-G3-02. BG-23: zonder besluit steekproef voor alles en vol… | nee | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G3-12 | Kwaliteitscontrole niveau 2 (volledige decode) en de meting op het co… | jelly-leon | S-G3-11. BG-23 (hele bibliotheek alleen na dat besluit). | ja | hoog | A-BOUW N4 en A-HERSTEL N4; overige standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G3-13 | Kwaliteitscontrole niveau 3: teksttaal en ondertitelsync via de F3-to… | jelly-leon | S-G3-12 en S-G3-06 (toolkit en syncmeter). BG-25: zonder be… | nee | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G3-14 | Bewijs per bevinding, verificatierun, feedback en onderdrukkingen | jelly-leon | S-G3-13. BG-24: zonder besluit miniaturen uit (Q5b geeft 50… | nee | gewoon | standaard; R-VEILIG N4 | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-G3-15 | Quality en MediaGuard: alleen lezen, geen dubbel werk, herstel als de… | jelly-leon | S-G3-14; viewerclient B03-009. BG-04 genomen (via de Hub).… | nee | gewoon | standaard; R-VEILIG N4; R-HARDE-EIS N4 | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G3-16 | Pluginpagina "Mediakwaliteit" voor beheerders | jelly-leon | S-G3-15. BG-24 (label en "Meld een probleem" standaard uit). | ja | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G3-17 | Watch Together: zichtbaarheid, uitnodigingen en deelnemersbeheer | jelly-leon | WT-1-gate geslaagd volgens het rapport van S-G2-90 (B03-021… | nee | hoog | A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4; R-HARDE-E… | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G3-18 | Watch Together: kinderprofiel en ouderlijk toezicht | jelly-leon | S-G3-17. BG-03 (definitie van een kinderprofiel) hoort voor… | nee | gewoon | standaard; R-VEILIG N4 | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-G3-19 | Watch Together: haperbeleid zonder IgnoreWait, met racetest | jelly-leon | S-G3-17; planner B03-018 (golf 1). BG-13: zonder besluit is… | ja | hoog | A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); overige standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G3-20 | Watch Together: volgmodus voor clients zonder SyncPlay (serverdeel) | jelly-leon | S-G3-17; S-G3-32 (WP-JSON B03-026 noemt B03-003 als afhanke… | nee | gewoon | standaard; R-VEILIG N4 | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-G3-21 | Volgmodus bewijzen in de Android TV-emulator | jelly-leon | S-G3-20 (en dus BG-10 genomen); een lokale image met S-G3-2… | ja | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G3-22 | Segmenten: ondertitel- en hoofdstuksignalen en families | jelly-leon | S-G2-90 gehaald, met B03-071 en B03-072 (S-G2-40, S-G2-42:… | nee | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G3-23 | Watch Together: externe deelnemers via VPN (alleen na BG-09) | jelly-leon | BG-09 genomen en "aan". Zonder dat besluit wordt deze stap… | ja | hoog | A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4 | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-G3-24 | Webplugin Watch Together: gezaaide driftcorrectie, telemetrie en menu | jelly-leon-web | S-G3-04; de webhaakmodule en de config.json-generator van B… | ja | hoog | A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); overige standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G3-25 | Kwaliteitslabel op de itempagina (webdeel van B03-057) | jelly-leon-web | S-G3-14 (route Q2 bestaat); S-G3-24 is klaar (zelfde baan).… | ja | hoog | A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog: de haak H-ITEMDETAILS i… | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G3-31 | Universele bibliotheek: webdeel (B03-002; alleen als het dossier van… | jelly-leon-web | S-G3-30, en zijn dossier (<WERKMAP>/.lokaal/ketens/S-G3-30/… | ja | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G3-32 | Beschikbaarheid van clients: wat op de ontwikkelmachine nog ontbreekt… | jelly-leon-clients | S-G2-90 gehaald (gate golf 2). Besluit Z-20 genomen. BG-08… | ja | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G3-26 | Native SyncPlay op Android TV (alleen als BG-10 "clientpatch" zegt) | jelly-leon-clients | BG-10 genomen met de keuze "clientpatch". Zonder die keuze… | ja | hoog | A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); overige standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G3-27 | Compat-regressie en differentiele run per module-oplevering (herhaals… | jelly-leon | deze stap draait vijf keer: na S-G3-08 (Subtitles), na S-G3… | ja | gewoon | standaard; R-HARDE-EIS N4; A-BOUW N2 mag bij de tweede en latere run… | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G3-90 | Gatecontrole golf 3 (A-GATE, alleen lezen) | jelly-leon, jelly-leon-web en jelly-leo… | S-G3-01 tot en met S-G3-25, S-G3-28 tot en met S-G3-32 en d… | ja | gewoon | A-GATE N4 (einde van een golf, niet van een fase) | R-EERLIJK |  |  |  |  |
| [ ] | S-G4-01 | Spike lanewrapper (NativeAOT met execv) en ADR | jelly-leon | gate golf 3; B03-062 (GPU-assistent, golf 2). | ja | hoog | A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); overige standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-02 | Lanewrapper en socketdienst bouwen | jelly-leon | S-G4-01 met een ADR die optie A of A' kiest. Bij optie B ve… | nee | hoog | A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4 | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-03 | Wrapper in de image en laneplanner | jelly-leon | S-G4-02. BG-28 (rolverdeling van de GPU's, D08): zonder bev… | ja | hoog | A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4; R-MANIFES… | R-TECH, R-VEILIG, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-04 | Gedeeld GPU-budget met MediaGuard (alleen lezen) | jelly-leon | S-G4-03; de MediaGuard-viewerclient van golf 1 (B03-009). B… | nee | hoog | A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4; R-HARDE-E… | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-05 | Apparaten: probe-, advies- en uitkomstroutes (serverdeel) | jelly-leon | B03-061 (golf 2: module Devices met devices.db). Deze stap… | nee | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-06 | Geleerde profielen per apparaat met bevestiging | jelly-leon | S-G4-05; de testset met gecontroleerde fouten van B03-060 (… | nee | gewoon | standaard; R-VEILIG N4 | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-07 | Bescherming van stock-clients en de MediaGuard-afspeeltest | jelly-leon | S-G4-06. BG-26 (opt-in voor officiele apps en stock-clients… | ja | hoog | A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4; R-HARDE-E… | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-08 | HDR/DV-, audio- en ondertitelregels en de uitleg "Waarom?" (serverdee… | jelly-leon | S-G4-06. BG-28 (GPU-rollen) en BG-29 (kwaliteitslabel en fe… | nee | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-09 | Watch Together: diagnose per deelnemer en capaciteitsadvies voor de s… | jelly-leon | S-G4-04 (capaciteit van de laneplanner) en S-G3-19 (haperbe… | ja | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-10 | Watch Together: chat en reacties, serverdeel (alleen na BG-12) | jelly-leon | S-G3-18 (kinderregels). BG-12 genomen met "aan". Zegt het b… | nee | gewoon | standaard; R-VEILIG N4 | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-11 | Watch Together: connector-items en events voor de Hub | jelly-leon | S-G3-17 tot en met S-G3-20. De Hub-pin JL4 van golf 1 besta… | nee | gewoon | standaard; R-VEILIG N4 | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-12 | Aanbevelingen: connector-items, gedragsregister en prestatiemeting | jelly-leon | B03-035 (golf 2; gate G-F2-5). Gate G-F2-9 is de uitkomst v… | ja | gewoon | standaard; R-VEILIG N4 | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-13 | Ondertitels: de gesynchroniseerde kopie als gemarkeerd spoor, nooit s… | jelly-leon | S-G3-08 (publicatie en spoorkeuzes). BG-19 en BG-21 zijn da… | nee | gewoon | standaard; A-BOUW N2 mag (klein en mechanisch); R-HARDE-EIS N4 | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-14 | Quality: connector-items, bewijsroute en health-checks voor de Hub | jelly-leon | S-G3-15. Subfase QC-6. De Hub-pin JL4 bestaat. | nee | gewoon | standaard; R-VEILIG N4 | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-15 | Segmenten: correctieroutes, review, meldingen en voorkeur per gebruik… | jelly-leon | B03-071, B03-072 en B03-073 (golf 2: segmentprovider met se… | nee | hoog | A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4; R-HARDE-E… | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-40 | Segmenten: leren van bevestigde correcties, heranalyse en kwaliteitsm… | jelly-leon | S-G4-15 en S-G3-22 (families en varianten). Subfase F6-S5.… | ja | hoog | A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); R-HARDE-EIS N4; overig… | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-16 | Beheerpagina "Intro's en aftiteling" en afronding van B03-007 | jelly-leon | S-G4-15 en S-G4-40. BG-31 (standaardgedrag van de knoppen):… | ja | gewoon | standaard; R-HARDE-EIS N4 | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-17 | Segmenten: taaktypen voor de planner, MediaGuard alleen lezen en conn… | jelly-leon | de planner en de analysewerker (B03-018) en de MediaGuard-v… | ja | hoog | A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4; R-HARDE-E… | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-18 | Apparaten: connector-items voor de Hub en het clientrapport alleen le… | jelly-leon | S-G4-06 (geleerde profielen) en S-G4-03 (lanes voor gpu_lan… | nee | gewoon | standaard; R-VEILIG N4 | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-19 | Contractcontrole: eventnamen, foutcatalogus, verzoekgrootte en Hub-pin | jelly-leon | S-G4-11, S-G4-13, S-G4-14, S-G4-17 en S-G4-18 (alle connect… | nee | gewoon | [N5] standaard; R-VEILIG N4 (er wordt nagelopen en aangevuld; wordt… | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-42 | Pluginpagina "Apparaten" voor beheerders (regels beslissen, correctie… | jelly-leon | S-G4-07 en S-G4-18. BG-26 (wie een verruimende regel mag be… | ja | gewoon | standaard; R-VEILIG N4 | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-44 | Pluginpagina "Watch Together" voor beheerders afmaken | jelly-leon | S-G4-11. De pagina zelf is in golf 2 begonnen (WP-JSON B03-… | ja | gewoon | standaard; R-VEILIG N4; R-HARDE-EIS N4 | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-49 | Scènezoeker: zoeken in ondertitelcues met tijdcode en rechten per geb… | jelly-leon | S-G3-22 (cues en families; WP-JSON B03-074: cue-extractie "… | nee | hoog | A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4; overige s… | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-51 | Offline downloaden: downloadrechten, verlopen en uitgezet account (B0… | jelly-leon | S-G3-10 (authenticatiefilter op streamroutes; B03-010 Accep… | nee | gewoon | standaard; R-VEILIG N4; R-HARDE-EIS N4 als hij loopt | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-53 | Live-tv en DVR: overlapmelding, opnamestatus, bewaartermijn en gids (… | jelly-leon | S-G4-04 (gedeeld GPU-budget: opnames die transcoderen lopen… | ja | hoog | A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4; overige s… | R-TECH, R-VEILIG, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-20 | Rij "Aanbevolen voor jou" op het startscherm (haak en rij) | jelly-leon-web | B03-035 (routes van de module Recommendations, golf 2); de… | ja | hoog | A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); overige standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-45 | Aanbevelingen: dialogen "Waarom aanbevolen?", "Wat kijk je graag?" en… | jelly-leon-web | S-G4-20. | ja | gewoon | standaard; R-HARDE-EIS N4 | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-21 | Web: rolbepaling, capability-probe en advies samenvoegen in het appar… | jelly-leon-web | S-G4-05 (routes E1 en E2 in de plugin). S-G4-25 levert de m… | ja | hoog | A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); overige standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-22 | Web: stall-detectie met terugval, kwaliteitslabel en "Waarom?" in Pla… | jelly-leon-web | S-G4-21; S-G4-08 (uitlegroute E5 in de plugin). BG-29: zond… | ja | hoog | A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); overige standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-41 | Web: scherm "Dit apparaat" en de bevestigingsproef | jelly-leon-web | S-G4-21 en S-G4-22; S-G4-06 (routes E6, E7, E8 en E8b in de… | ja | hoog | A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog: routehaak H-ROUTE in tw… | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-23 | Web: skipknoppen per type, standaardactie en groepsregel (drie haken) | jelly-leon-web | S-G4-16 (serverdeel, marge aan het einde); S-G4-15 (route v… | ja | hoog | A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog: drie haken in upstream-… | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-46 | Web: hint na de aftiteling, "Klopt niet", correctiepaneel en voorkeur… | jelly-leon-web | S-G4-23; S-G4-15 (correctie-, meld- en voorkeurroutes in de… | ja | gewoon | standaard; R-VEILIG N4 | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-43 | Web: capaciteitsadvies voor de start van een groep (dialoog) | jelly-leon-web | S-G4-09 (route E19 in de plugin); S-G3-24 (webplugin Watch… | ja | gewoon | standaard; A-BOUW N2 is toegestaan als A-VERKEN meldt dat de plugin v… | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-24 | Web: strook voor reacties en chat (alleen als BG-12 "aan" is) | jelly-leon-web | BG-12 moet "aan" zijn; S-G4-10 (routes E14 en E15 in de plu… | ja | gewoon | standaard; R-VEILIG N4 | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-50 | Scènezoeker web: zoekscherm met tijdcode en "afspelen vanaf hier" (B0… | jelly-leon-web | S-G4-49 (routes /media/v1/search en /media/v1/scenes); de w… | ja | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-54 | Live-tv web: overlapwaarschuwing vóór het plannen en opnamestatus (B0… | jelly-leon-web | S-G4-53; de webhaakmodule van B03-017 (golf 1). | ja | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-25 | Clients: marker jellyLeonBuild in de Android- en desktop-build | jelly-leon-clients | geen stap van dit bestand; mag starten voor de gate van gol… | ja | hoog | A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog: patch in upstream-appco… | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-26 | Android TV: capabilityrapport automatisch sturen en beperkende regels… | jelly-leon-clients | S-G4-05 (route E2) en S-G4-06 (regels). BG-30 (mag de Jelly… | ja | hoog | A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog: eerste gedragspatch in… | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-27 | Android TV: overlay-tekst per segmenttype en Recap standaard "vragen" | jelly-leon-clients | S-G4-16. BG-31 met optie a1 (eigen knopteksten en daarmee c… | ja | hoog | A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog: patch in upstream-appco… | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-28 | Android: knoptekst per type in de native speler; desktop: marge aan h… | jelly-leon-clients | S-G4-27. BG-31 (optie a1) en BG-08; zonder een van beide st… | ja | hoog | A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog: patch in upstream-appco… | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-29 | Clientmatrix aanbevelingen in de emulators (met loggende proxy) | jelly-leon-clients | S-G4-20 en S-G4-45 (rij en dialogen in web); S-G4-12 (provi… | ja | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-30 | Clientmatrix golf 4: ondertitels, kwaliteit, apparaten en skipknoppen… | jelly-leon-clients | S-G4-13, S-G4-14, S-G4-07, S-G4-23, S-G4-46, S-G4-26, S-G4-… | ja | gewoon | standaard; R-HARDE-EIS N4 | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-52 | Offline downloaden in de Android-app: rechten, verlopen, hervatten en… | jelly-leon-clients | S-G4-51 (rechten aan de serverkant); S-G4-30 (de vorige emu… | ja | gewoon | standaard; R-VEILIG N4; R-HARDE-EIS N4 als hij loopt | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-31 | Hub: adapter voor Jelly Leon en de stap "Hub-sleutelset kopieren" | ai-server-manager | S-P3-010, S-P3-020 en S-P3-070 (STAPPEN_P3.md: ADR, adapter… | nee | hoog | [N5] A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4 (de… | R-TECH, R-VEILIG, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-32 | Hub: kaartbasis voor Jelly Leon op het scherm Media en de eventtypes… | ai-server-manager | S-G4-31; S-P3-080 (scherm Media) en S-P3-075 (incidentketen… | ja | gewoon | standaard; R-VEILIG N4 | R-TECH, R-VEILIG, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-33 | Hub-kaart "Watch Together" | ai-server-manager | S-G4-32; S-G4-11 (itemtype watch_together_stats en de event… | ja | gewoon | standaard | R-TECH, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-34 | Hub-kaart "Aanbevelingen · Jelly Leon" en het detailscherm | ai-server-manager | S-G4-32; S-G4-12 (itemtypen recommender_status en recommend… | ja | gewoon | standaard | R-TECH, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-36 | Hub-kaart "Mediakwaliteit" met problemen-inbox en bewijs | ai-server-manager | S-G4-32; S-G4-14 (itemtypen quality_summary en quality_find… | ja | gewoon | standaard | R-TECH, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-37 | Hub-kaarten "Jelly Leon · Afspelen" en "GPU-banen" en het scherm "App… | ai-server-manager | S-G4-32; S-G4-18 (itemtypen device, playback_stats, gpu_lan… | ja | gewoon | standaard | R-TECH, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-38 | Hub-kaart "Intro en aftiteling (Jelly Leon)" | ai-server-manager | S-G4-32; S-G4-17 (itemtypen segment_coverage en segment_rev… | ja | gewoon | standaard | R-TECH, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-35 | Hub: alle Jelly Leon-kaarten samen, kinderschil en afsluitende ontwer… | ai-server-manager | S-G4-33, S-G4-34, S-G4-36, S-G4-37, S-G4-38. De Hub-kaart v… | ja | gewoon | standaard | R-TECH, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-39 | Compat-regressie per oplevering en het clientmatrixdocument (herhaals… | jelly-leon | de stap waarna de run is gepland; een lokale image van de a… | ja | gewoon | standaard; R-HARDE-EIS N4; A-BOUW N2 mag bij de tweede en latere run… | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-47 | Winstmeting apparaatprofielen tegen standaard Jellyfin (JLT-40) | jelly-leon | S-G4-07, S-G4-22 en S-G4-41 klaar; S-P40-64 klaar (STAPPEN_… | ja | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-48 | Winstmeting segmenten tegen standaard Jellyfin en Intro Skipper (JLT-… | jelly-leon | S-G4-16 en S-G4-40 klaar; de bevroren testset, het evaluati… | ja | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-G4-90 | Bewijs samenvoegen voor P4: programmabewijs, Excel en STATUS | ai-server-manager | elke stap van golf 3 en golf 4 is in <WERKMAP>/.lokaal/plan… | nee | gewoon | A-BOUW N2 (mechanisch: meten en twee documenten bijwerken); R-EERLIJK… | R-EERLIJK |  |  |  |  |
| [ ] | S-G4-95 | Gate einde P4: onafhankelijke controle | jelly-leon, jelly-leon-web, jelly-leon-… | S-G4-90 afgevinkt; in geen van de vier repos is een keten o… | ja | hoog | A-GATE N5. Winst: dit is de enige plek waar iemand zonder voorkennis… | - |  |  |  |  |

## Fase P5 (STAPPEN_P5.md; 67 stappen)

De volgorde binnen een baan en wat tegelijk mag staat in "Volgorde en banen" van STAPPEN_P5.md; deze tabel volgt de volgorde van het bestand.
Kolommen klaar, commit, CI-run, datum en opmerking vult de regisseur in; de andere kolommen maakt maak_voortgang.py uit het stapbestand (ingekort; de stap is leidend).

| klaar | stap-ID | titel | baan (repo) | vooraf (ingekort; de stap is leidend) | zwaar | moeilijkheid | niveau (afwijkingen) | verplichte reviewers | commit | CI-run | datum | opmerking |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [ ] | S-P5-01 | Startcontrole van fase P5 en besluitenronde | ai-server-manager (alleen docs/platform… | de fase-afsluiting van P4 is door A-GATE gedaan (S-G4-95 in… | nee | gewoon | A-VERKEN N1; A-BOUW N2; R-EERLIJK N3. | R-EERLIJK |  |  |  |  |
| [ ] | S-P5-02 | Contractdelta voor de optionele model-apps | ai-server-manager (contractbron) en daa… | S-P5-01 met BG-06 en BG-18 genomen. Zonder die besluiten: s… | nee | hoog | A-BOUW N4 (moeilijkheid hoog); verder standaard. | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-10 | Ingest-raamwerk en bestandenadapter | zoeken-en-persoonlijke-ai | S-P5-01. Geen besluit nodig. | nee | hoog | A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); verder standaard. | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-11 | Adapters voor Immich en logbestanden | zoeken-en-persoonlijke-ai | S-P5-10 gepusht. | nee | gewoon | standaard | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-12 | Adapter voor Jellyfin en Jelly Leon, met kinderfilter | zoeken-en-persoonlijke-ai | S-P5-10 gepusht. Mag na of vóór S-P5-11 (zelfde baan, dus n… | nee | gewoon | standaard | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-13 | Zoeken afronden: paginering over een momentopname en filters | zoeken-en-persoonlijke-ai | S-P5-10 gepusht (er moet echte indexdata zijn om op te test… | nee | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-14 | Optionele embeddingbron en hybride zoeken | zoeken-en-persoonlijke-ai | S-P5-13 gepusht; S-P5-02 gedaan; BG-06 staat embeddings toe… | nee | hoog | A-BOUW en A-HERSTEL N4; verder standaard. | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-15 | Rijbeveiliging in de database met een aparte querierol | zoeken-en-persoonlijke-ai | S-P5-10 gepusht. Mag vóór S-P5-14 als de regisseur dat hand… | nee | hoog | A-BOUW en A-HERSTEL N4; verder standaard. | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-16 | Mediascènes, ondertitels en de herkomst "machinevertaling" | zoeken-en-persoonlijke-ai | S-P5-12 gepusht. Het deel spraakherkenning (bouwpunt 5) all… | nee | gewoon | standaard | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-17 | Canonieke itemtekst en gedeelde vectoren voor Jelly Leon | zoeken-en-persoonlijke-ai | S-P5-14 gepusht; BG-06 bevestigt dat zoeken-en-persoonlijke… | nee | gewoon | standaard | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-18 | Vraag-en-antwoord met citaten en afweer tegen ingesloten opdrachten | zoeken-en-persoonlijke-ai | S-P5-13 gepusht. Voor het genereren van een antwoord: BG-06… | nee | hoog | A-BOUW en A-HERSTEL N4; verder standaard. | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-19 | Portabiliteit, privacyrapport en herindexeren na herstel | zoeken-en-persoonlijke-ai | S-P5-10 gepusht; S-P5-14 als de modelwissel (bouwpunt 4) me… | nee | gewoon | standaard | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-20 | Chat- en spraaksessies met optionele spraakherkenning | zoeken-en-persoonlijke-ai | S-P5-01 gedaan. Getypte sessies kunnen direct. Het deel spr… | nee | gewoon | standaard | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-21 | Intentrouter, context en probleemvragen | zoeken-en-persoonlijke-ai | S-P5-20 gepusht; gate P2 gehaald (voorstellen lopen via het… | nee | hoog | A-BOUW en A-HERSTEL N4; verder standaard. | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-22 | Uitspraak van antwoorden (TTS) | zoeken-en-persoonlijke-ai | S-P5-20 gepusht; S-P5-02 en BG-06 (de tts-app is in het con… | nee | gewoon | standaard | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-24 | Discover, gezondheid en statuspagina voor de P5-functies van zoeken | zoeken-en-persoonlijke-ai | S-P5-10 t/m S-P5-22 gepusht of uitdrukkelijk overgeslagen w… | nee | gewoon | standaard | R-TECH, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-23 | Manifest, OpenAPI, image en rooktest van zoeken-en-persoonlijke-ai | zoeken-en-persoonlijke-ai | S-P5-10 t/m S-P5-22 gepusht of uitdrukkelijk overgeslagen w… | ja | gewoon | standaard | R-TECH, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-30 | Upstream-API's vaststellen en simulators voor NetAlertX en AdGuard Ho… | home-control-hub | S-P5-01 gedaan; werkmap schoon (zie de inleiding van deze b… | nee | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-31 | NetAlertX-ingest: apparaten, adreshistorie en nieuwe-apparaatsignalen | home-control-hub | S-P5-30 gepusht. | nee | gewoon | standaard | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-32 | DNS-samenvatting, uitzonderingen als voorstel en fail-safe | home-control-hub | S-P5-30 gepusht. Voor het voorsteldeel (bouwpunt 4 t/m 6):… | nee | hoog | A-BOUW en A-HERSTEL N4; verder standaard. | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-33 | Verkeersdiagnose met eerlijke labels | home-control-hub | S-P5-32 gepusht. | nee | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-34 | VPN- en tunnelbewaking | home-control-hub | S-P5-31 gepusht (zelfde worker-stap). | nee | gewoon | standaard | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-35 | Beveiligingsbevindingen met bewijs en goedkeuringsstroom | home-control-hub | S-P5-31 en S-P5-32 gepusht; gate P2 gehaald (voorstellen lo… | nee | hoog | A-BOUW en A-HERSTEL N4; verder standaard. | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-37 | Connector, events, OpenAPI, image en rooktest van het netwerkdomein | home-control-hub | S-P5-31 t/m S-P5-35 gepusht of uitdrukkelijk overgeslagen.… | ja | gewoon | standaard | R-TECH, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-50 | Voorspellend onderhoud: API | ai-server-manager | S-P5-01 gedaan; S-P5-02 klaar of nog niet gestart (zelfde r… | nee | gewoon | standaard | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-51 | Voorspellend onderhoud: scherm | ai-server-manager | S-P5-50 gepusht. | ja | gewoon | standaard | R-TECH, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-52 | Update- en rollbackcentrum: API | ai-server-manager | gate P2 gehaald (voorstel, goedkeuring, executor, pre-updat… | nee | hoog | A-BOUW en A-HERSTEL N4; verder standaard. | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-53 | Update- en rollbackcentrum: scherm | ai-server-manager | S-P5-52 gepusht. | ja | gewoon | standaard | R-TECH, R-HARDE-EIS, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-54 | Draagbare export en herstel van de Hub: API | ai-server-manager | S-P5-52 gepusht (zelfde repo); de eigen database-export van… | nee | hoog | [N5] A-BOUW en A-HERSTEL N4; R-HARDE-EIS N4 (de Hub-gebruikers en he… | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-55 | Herstelwizard: scherm | ai-server-manager | S-P5-54 gepusht. | ja | gewoon | standaard | R-TECH, R-VEILIG, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-56 | Scherm Netwerk | ai-server-manager | S-P5-31, S-P5-32, S-P5-34 en S-P5-35 gepusht (wat niet gebo… | ja | gewoon | A-ONTWERP N4 (acht onderdelen die bij elkaar moeten passen); verder s… | R-TECH, R-VEILIG, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-57 | Scherm Zoeken en antwoordkaart | ai-server-manager | S-P5-13 gepusht; voor de antwoordkaart ook S-P5-18. | ja | gewoon | standaard | R-TECH, R-VEILIG, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-58 | Schermen Bronnen en rechten, indexstatus en privacy | ai-server-manager | S-P5-10 en S-P5-19 gepusht. | ja | gewoon | standaard | R-TECH, R-VEILIG, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-59 | Spraak in de chat | ai-server-manager | S-P5-20 en S-P5-22 gepusht; de AI-chat uit P2 bestaat (apps… | ja | gewoon | standaard | R-TECH, R-VEILIG, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-60 | Fork-dashboard | ai-server-manager | S-P5-71 gepusht. | ja | gewoon | standaard | R-TECH, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-61 | Verwijderen en verhuizen: scherm | ai-server-manager | S-P5-81 gepusht; het scherm Apps met de verwijderstap uit P… | ja | gewoon | standaard | R-TECH, R-HARDE-EIS, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-62 | Hub-kaart "Nederlandse ondertitels" en events | ai-server-manager | S-P5-107 gepusht; B03-gate JL4 gehaald; de eventtypen voor… | ja | gewoon | standaard | R-TECH, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-63 | Optionele model-apps in catalogus en scherm | ai-server-manager | S-P5-02, S-P5-72 en S-P5-86 gepusht (voor mt: BG-06 en BG-1… | ja | gewoon | standaard | R-TECH, R-MANIFEST, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-64 | Hub: images, rooktest en volledige ontwerpreview | ai-server-manager | S-P5-50 t/m S-P5-63 gepusht of uitdrukkelijk overgeslagen.… | ja | gewoon | standaard | R-TECH, R-MANIFEST, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-70 | Forkregister en upstream volgen | appstore-en-fork | S-P5-01 gedaan (besluit Z-01 bekend of uitdrukkelijk open g… | nee | hoog | A-BOUW en A-HERSTEL N4; verder standaard. | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-71 | Samenvoegvoorstellen en de poort vóór productie | appstore-en-fork | S-P5-70 gepusht. | nee | hoog | A-BOUW en A-HERSTEL N4; verder standaard. | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-72 | Catalogus- en validatorregels voor optionele model-apps | appstore-en-fork | S-P5-02 gepusht (contractdelta); BG-06 genomen. Voor mt ook… | nee | hoog | A-BOUW en A-HERSTEL N4; verder standaard. | R-TECH, R-VEILIG, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-73 | Image, rooktest en statuspagina van appstore-en-fork | appstore-en-fork | S-P5-70 t/m S-P5-72 gepusht of uitdrukkelijk overgeslagen.… | ja | gewoon | standaard | R-TECH, R-MANIFEST, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-80 | Verwijderplan zonder dataverlies | jelly-leon-platform | gate P2 gehaald (installatie-, update- en terugzetplannen w… | nee | hoog | A-BOUW en A-HERSTEL N4; R-HARDE-EIS N4 (VERPLICHT). Geen N5: een verw… | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-81 | Verhuisplan via export | jelly-leon-platform | S-P5-80 gepusht. | nee | gewoon | standaard | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-82 | Manifest en controlelijst I11 NetAlertX | jelly-leon-platform | S-P5-01 gedaan (D03 en D11 bekend of open gelaten). | ja | gewoon | standaard | R-TECH, R-VEILIG, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-83 | Manifest en controlelijst I12 AdGuard Home | jelly-leon-platform | S-P5-01 gedaan (D11 bekend of open gelaten). | nee | gewoon | standaard | R-TECH, R-VEILIG, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-84 | Controlelijsten I21 (Tailscale en Cloudflared) en I26 (bestaande apps) | jelly-leon-platform | S-P5-01 gedaan (D03 bekend of open gelaten). | nee | gewoon | standaard | R-TECH, R-HARDE-EIS, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-85 | Controlelijsten I14 en I25 en manifestcontrole van zoeken | jelly-leon-platform | S-P5-23 gepusht (manifest en image van zoeken-en-persoonlij… | nee | gewoon | A-BOUW N2 (klein en mechanisch); verder standaard. | R-TECH, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-86 | Manifesten voor de optionele model-apps | jelly-leon-platform | S-P5-72 gepusht en de validator-pin van deze repo verzet (m… | ja | gewoon | standaard | R-TECH, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-100 | Imagebewaking en één adrescontrole voor model-apps | jelly-leon | fase-afsluiting P4 (S-G4-95 in STAPPEN_P4_GOLF3_4.md, oorde… | ja | hoog | A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); verder standaard. Geen N5… | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-101 | Optionele embeddings voor aanbevelingen | jelly-leon | S-P5-100; S-P5-17 gepusht (canonieke itemtekst en leesroute… | ja | hoog | A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); verder standaard. | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-102 | Koppeling met de vertaalmotor en bewaring van het geheim | jelly-leon | S-P5-100; S-P5-02 (Δ-CONTRACT-MT) en BG-18; de ondertitelto… | ja | hoog | A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); verder standaard. | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-103 | Image van de vertaalmotor mt | de repo die S-P5-02 in de contractrij v… | S-P5-02 met BG-06, BG-18 en Z-16: repo, app_id, image-naam… | ja | hoog | A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); verder standaard. | R-TECH, R-VEILIG, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-104 | Vertaalpijplijn in de werker (taaktype subtitle.translate) | jelly-leon | S-P5-102; voor de meting ook S-P5-103 (echte motor in een l… | ja | hoog | A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); verder standaard. | R-TECH, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-105 | Kwaliteitsscore, publicatiedrempel en kalibratie | jelly-leon | S-P5-104 (bevroren pijplijn). AutoPublish blijft in deze st… | ja | hoog | A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); R-EERLIJK N4 (controle va… | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-106 | Correctieroutes, beoordeling, vertaalgeheugen en woordenlijst | jelly-leon | S-P5-105; de publicatietransactie B03-047 (P4, S-G3-08) en… | ja | hoog | A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); verder standaard. Geen N5… | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-107 | Events, connector-itemtypen en Hub-toegang voor ondertitels | jelly-leon | S-P5-106. De outbox, de connector en de Hub-koppeling uit d… | ja | hoog | A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG en R-HARDE-EIS N… | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-108 | Audiotaal- en dialoogcontrole met lokale spraakherkenning (standaard… | jelly-leon | S-P5-100; S-P5-02 (Δ-CONTRACT-MODEL) en BG-06; S-P5-20 gepu… | ja | gewoon | standaard | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-109 | Optionele lokale AI voor segmentdetectie (standaard uit) | jelly-leon | S-P5-100; de segmentmodule uit P4 (S-G2-40, S-G2-42, S-G3-2… | ja | gewoon | standaard | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-111 | Pluginpagina "Ondertitels" voor beheerders (W4) | jelly-leon | S-P5-107 (beheerroutes); S-P5-105 (kalibratiestatus); S-P5-… | ja | gewoon | standaard | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-115 | Meetslot JLT-28, web-pin, image en rooktest (sluit de baan jelly-leon… | jelly-leon | S-P5-100 tot en met S-P5-111 voor zover gebouwd; S-P5-120 e… | ja | gewoon | standaard (R-HARDE-EIS op N4). Geen N5: er wordt geen overname- of mi… | R-TECH, R-HARDE-EIS, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-120 | Dialoog "Ondertitels (Jelly Leon)" op de itempagina (W2) | jelly-leon-web | S-P5-106 gepusht (routes 1 tot en met 5, 8 en 9 bestaan, sa… | ja | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-121 | Correctie-editor in de webfork (W3) | jelly-leon-web | S-P5-120; S-P5-106 gepusht (routes 6, 7 en 10). | ja | hoog | A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); verder standaard. | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-P5-130 | Clientmatrix van de machinevertaling in de emulators (B03-049, JLT-25) | jelly-leon-clients | S-P5-115 gepusht en de image jelly-leon:poort van die commi… | ja | gewoon | standaard | R-EERLIJK |  |  |  |  |
| [ ] | S-P5-900 | Bewijs samenvoegen: programmabewijs, Excel en STATUS | ai-server-manager | S-P5-01 tot en met S-P5-130 zijn in <WERKMAP>/.lokaal/plan/… | nee | gewoon | standaard | R-EERLIJK |  |  |  |  |
| [ ] | S-P5-910 | Gate P5: onafhankelijke controle | zoeken-en-persoonlijke-ai, home-control… | S-P5-900 afgevinkt; er is in geen van de acht repos een ket… | ja | hoog | A-GATE N5 (geval d: gatecontrole aan het einde van een hele fase). Wi… | R-EERLIJK |  |  |  |  |

## Fase P6 (STAPPEN_P6.md; 29 stappen)

De volgorde binnen een baan en wat tegelijk mag staat in "Volgorde en banen" van STAPPEN_P6.md; deze tabel volgt de volgorde van het bestand.
Kolommen klaar, commit, CI-run, datum en opmerking vult de regisseur in; de andere kolommen maakt maak_voortgang.py uit het stapbestand (ingekort; de stap is leidend).

| klaar | stap-ID | titel | baan (repo) | vooraf (ingekort; de stap is leidend) | zwaar | moeilijkheid | niveau (afwijkingen) | verplichte reviewers | commit | CI-run | datum | opmerking |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [ ] | S-P6-01 | Stand en voorwaarden van P6 vaststellen | geen (alleen lezen in alle 11 repos) | fasegate P5 gesloten (S-P5-910 met oordeel "GATE GEHAALD";… | nee | gewoon | A-VERKEN N2; R-EERLIJK N3 | R-EERLIJK |  |  |  |  |
| [ ] | S-P6-02 | Release v0.1.0 van de Hub en de executor | ai-server-manager | S-P6-01; CI groen op de laatste commit; besluit 6 van de ge… | nee | gewoon | A-BOUW N2 (kleine mechanische stap); overige standaard | R-TECH, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P6-03 | Release v0.1.0 van home-control-hub | home-control-hub | S-P6-01; CI groen; besluit 6 van de gebruiker genomen | nee | gewoon | A-BOUW N2; overige standaard | R-TECH, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P6-04 | Release v0.1.0 van appstore-en-fork | appstore-en-fork | S-P6-01; CI groen; besluit 6 van de gebruiker genomen | nee | gewoon | A-BOUW N2; overige standaard | R-TECH, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P6-05 | Release v0.1.0 van jelly-leon-platform en digests in de installatiema… | jelly-leon-platform | S-P6-01; CI groen; voor bouwpunt 5: S-P6-02 klaar (digests… | nee | gewoon | standaard | R-TECH, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P6-06 | Release v0.1.0 van zoeken-en-persoonlijke-ai | zoeken-en-persoonlijke-ai | S-P6-01; CI groen; besluit 6 van de gebruiker genomen | nee | gewoon | A-BOUW N2; overige standaard | R-TECH, R-MANIFEST, R-EERLIJK |  |  |  |  |
| [ ] | S-P6-10 | Simulators voor de downloadketen (arr, sabnzbd, qbittorrent) | jelly-leon-platform | S-P6-05 klaar (baan jelly-leon-platform vrij) | nee | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-P6-11 | Simulators voor huis en energie (gree, homewizard, zigbee) | jelly-leon-platform | S-P6-10 klaar | nee | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-P6-12 | Simulators overig (immich, onedrive, credits, stt, upstream-git) | jelly-leon-platform | S-P6-11 klaar | nee | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-P6-13 | Integrale omgeving: compose, runner en eerste rookronde | jelly-leon-platform | S-P6-12 klaar; S-P6-02...06 klaar (de vijf releases bestaan… | ja | hoog | A-BOUW N4 (moeilijkheid hoog); overige standaard | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P6-14 | Scenario's uitval en noodstop (EX01, EX02, EX06, EX07) | jelly-leon-platform | S-P6-13 klaar (runner en compose bestaan); S-P6-10 klaar | ja | gewoon | standaard | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P6-15 | Scenario's MediaGuard-inhoud (EX03, EX04, EX05, EX09, EX37) | jelly-leon-platform | S-P6-13 klaar; S-P6-10 klaar (simulator arr) | ja | gewoon | standaard | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P6-16 | Scenario's Media Source Optimizer (EX39, EX40, EX41, EX42) | jelly-leon-platform | S-P6-13 klaar; S-P6-10 klaar (simulators sabnzbd, qbittorre… | ja | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-P6-17 | Scenario's zoeken, spraak en LiveTV (EX36, EX43, EX44, EX49, EX38) | jelly-leon-platform | S-P6-13 klaar; S-P6-12 klaar (simulators immich, stt); voor… | ja | gewoon | standaard | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P6-18 | Scenario's Hub-veiligheid (EX16...EX21) | jelly-leon-platform | S-P6-13 klaar; S-P6-12 klaar (credits-simulator) | ja | hoog | A-BOUW N4 (moeilijkheid hoog); R-VEILIG N4 (standaard voor deze rol);… | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P6-19 | Scenario's Node-RED en meldingen buiten de Hub om (EX45, EX46, EX22) | jelly-leon-platform | S-P6-13 klaar | ja | gewoon | standaard | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P6-20 | Scenario's back-up, levenscyclus en appstore (EX11, EX12, EX14, EX15,… | jelly-leon-platform | S-P6-13 klaar; S-P6-12 klaar (simulators onedrive, upstream… | ja | hoog | A-BOUW N4 (moeilijkheid hoog); overige standaard | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P6-21 | Scenario's huis en energie (EX24...EX30) | jelly-leon-platform | S-P6-13 klaar; S-P6-11 klaar (simulators gree, homewizard,… | ja | gewoon | standaard | R-TECH, R-VEILIG, R-EERLIJK |  |  |  |  |
| [ ] | S-P6-22 | Netwerkscenario's, de "Echt"-rijen, volledige run en rapport | jelly-leon-platform | S-P6-14...21 klaar | ja | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-P6-30 | Eindproef terug naar stock en gegevensbescherming (B03-013; JLT-60, J… | jelly-leon | S-P6-01 klaar; fasegate P5 gesloten (alle B03-modules die h… | ja | hoog | A-BOUW N4 (moeilijkheid hoog); overige standaard | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P6-31 | Releasegate compatibiliteit (B03-019; JLT-63, JLT-64, JLT-66, JLT-67) | jelly-leon | S-P6-30 klaar (image jelly-leon:p6 bestaat: docker image in… | ja | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-P6-32 | Generale repetitie van de Emby-overname met de eindimage (B03-015; JL… | jelly-leon | S-P6-31 klaar (zelfde baan); image jelly-leon:p6 bestaat; h… | ja | hoog | A-BOUW N4 (moeilijkheid hoog); R-HARDE-EIS N5. Winst: dit is de laats… | R-TECH, R-VEILIG, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P6-33 | MediaGuard: contracttest met de Jelly Leon-image en upgradebewijs (B0… | media-guard-ultimate | S-P6-30 heeft jelly-leon:p6 gebouwd (docker image inspect j… | ja | gewoon | standaard | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P6-40 | Regressieronde over alle repos op de eindstand (releasegate; JLT-68) | één repo per run; de regisseur start de… | S-P6-22, S-P6-32 en S-P6-33 klaar. In de gekozen repo loopt… | ja | gewoon | standaard. Geen topmodel: regressie is routinewerk. | R-TECH, R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P6-50 | NAS-acceptatiedraaiboek voor de gebruiker (document) | ai-server-manager | S-P6-02 klaar (de tag en digest van Hub en executor zijn be… | nee | gewoon | R-HARDE-EIS N4; overige standaard. Geen topmodel: documentatie. | R-TECH, R-HARDE-EIS, R-ONTWERP, R-EERLIJK |  |  |  |  |
| [ ] | S-P6-51 | Overnamedraaiboek en controlelijst "Emby verwijderen" bijwerken | jelly-leon | S-P6-32 klaar (uitkomsten van de generale repetitie); S-P6-… | nee | gewoon | R-HARDE-EIS N4; overige standaard. Geen topmodel: documentatie (de ov… | R-HARDE-EIS, R-EERLIJK |  |  |  |  |
| [ ] | S-P6-52 | Excel-gereedschap: wat de gebruiker zelf afvinkt blijft staan | ai-server-manager | besluit van de gebruiker via een keuzemenu van de regisseur… | nee | gewoon | standaard | R-TECH, R-EERLIJK |  |  |  |  |
| [ ] | S-P6-60 | EVIDENCE-programma en Excel bijwerken na DEEL A | ai-server-manager | S-P6-40 voor alle elf repos "groen" in VOORTGANG.md; S-P6-5… | nee | gewoon | A-BOUW N2 (mechanisch); R-EERLIJK N3. Geen topmodel: Excel. | R-EERLIJK |  |  |  |  |
| [ ] | S-P6-70 | Terugmelding van een NAS-onderdeel verwerken (herhaalbaar, één keer p… | de repo waarvan de rijen zijn (één repo… | de terugmelding van de gebruiker is compleet (elk punt onde… | nee | gewoon | A-BOUW N2; R-EERLIJK N3. R-HARDE-EIS N5 bij N-P6-11 en N-P6-12. Winst… | R-HARDE-EIS, R-EERLIJK |  |  |  |  |

## NAS-onderdelen van P6 (STAPPEN_P6.md; 14 onderdelen; alleen met de gebruiker op de echte NAS; tot dan NIET GEVALIDEERD)

Deze onderdelen voert de regisseur niet zelf uit: de gebruiker doet ze op de echte NAS met het draaiboek uit STAPPEN_P6.md.
Afvinken alleen met het bewijs dat het onderdeel noemt.

| klaar | stap-ID | titel | bewijs | datum | opmerking |
|---|---|---|---|---|---|
| [ ] | N-P6-01 | NAS-basis, invulblad en alleen-lezen-gebruiker |  |  |  |
| [ ] | N-P6-02 | Back-up en herstelproef |  |  |  |
| [ ] | N-P6-03 | De Hub en de executor installeren, bijwerken en terugzetten |  |  |  |
| [ ] | N-P6-04 | Bewaking, meldingen en aanmelden |  |  |  |
| [ ] | N-P6-05 | Bestaande apps, MediaGuard en Media Source Optimizer |  |  |  |
| [ ] | N-P6-06 | my_house en echte apparaten |  |  |  |
| [ ] | N-P6-07 | Netwerk en DNS |  |  |  |
| [ ] | N-P6-08 | Zoeken, persoonlijke AI en optioneel Navidrome |  |  |  |
| [ ] | N-P6-09 | Jelly Leon naast Emby: installatie, clients en GPU |  |  |  |
| [ ] | N-P6-10 | De Jelly Leon-modules en de belastingtest op de NAS |  |  |  |
| [ ] | N-P6-11 | De echte overname vanuit Emby |  |  |  |
| [ ] | N-P6-12 | De overstap (Cutover-gate) |  |  |  |
| [ ] | N-P6-13 | Controlelijst "Emby verwijderen" |  |  |  |
| [ ] | N-P6-14 | Duurproef, herstel op een tweede omgeving en productieacceptatie |  |  |  |

## Gates

Per gate een regel; de eisen staan in het deel "Gates" en in de fase-afsluiting van het stapbestand. Afvinken alleen met het
rapport van A-GATE in de ketenmap.

| klaar | gate | stapbestand | rapport A-GATE | datum |
|---|---|---|---|---|
| [ ] | P2 naar P3 | STAPPEN_P2.md |  |  |
| [ ] | P3 naar P4 | STAPPEN_P3.md |  |  |
| [ ] | P4-0, golf 1, golf 2 (per golf een regel toevoegen bij de start van die golf) | STAPPEN_P4_GOLF1_2.md |  |  |
| [ ] | golf 3, golf 4 en P4 naar P5 (per golf een regel toevoegen) | STAPPEN_P4_GOLF3_4.md |  |  |
| [ ] | P5 naar P6 | STAPPEN_P5.md |  |  |
| [ ] | P6: acceptatie en cutover (de gebruiker beslist) | STAPPEN_P6.md |  |  |

## Fase-afsluitingen

| fase | dekking.py --voortgang schoon | A-GATE | Excel bijgewerkt (commit) | STATUS.md bijgewerkt | gemeld aan de gebruiker |
|---|---|---|---|---|---|
| P2 |  |  |  |  |  |
| P3 |  |  |  |  |  |
| P4 |  |  |  |  |  |
| P5 |  |  |  |  |  |
| P6 |  |  |  |  |  |
