# Stand van ronde 3 (bouwronde vóór de overdracht) - DEFINITIEF

Ronde 3 is op 2026-11-11 om 09:52 AFGEBROKEN op verzoek van de gebruiker (het duurde te lang). Er draait niets meer. Wat
toen liep is NIET afgemaakt: het staat als half werk (niet gecommit) in de werkmap van de repo, met een reservekopie in
`<WERKMAP>/.lokaal/halfwerk/<repo>.patch` (git diff HEAD) en `<repo>-nieuw.tgz` (nieuwe bestanden).

Regel voor de regisseur: half werk NOOIT ongezien weggooien en NOOIT ongezien committen. Per repo met half werk is de eerste
stap: A-VERKEN beoordeelt wat er staat (git status, git diff, tests draaien), A-BOUW maakt het af, daarna de gewone keten
(reviewers, A-HERSTEL, R-EERLIJK). Vertrouw voor "is het er al?" altijd op `git log` en `git status` in de repo zelf.

Alle 11 repos staan op branch `ccr-c133d7a0-kuz1cv`; er zijn geen niet-gepushte commits meer (stand 2026-11-11 10:05).

| Repo | Onderdeel (werkpakketten) | Stand | Gevolg voor het plan |
|---|---|---|---|
| jelly-leon-web | contract 1.3 (NU-punten) | gebouwd, gepusht EN gereviewd (HEAD 4ea95f2f0); werkmap schoon | geen stap nodig |
| jelly-leon-clients | contract 1.3 (NU-punten) | gebouwd, gepusht EN gereviewd (HEAD 309b178); werkmap schoon | geen stap nodig |
| jelly-leon | contract 1.3 (NU-punten) | gebouwd en gepusht; review NIET gedaan | reviewstap |
| jelly-leon | golf 1: B03-017 (analyzer JL0001-JL0004, web-config-generator, UserDeleted, pluginproef JLT-68/64/65, IStartupFilter-spike) en B03-009 (MediaGuard-viewerclient via de Hub) | gecommit en gepusht (HEAD cc3e82b4d); review NIET gedaan; CI niet beoordeeld | reviewstap |
| jelly-leon | golf 1: B03-018 en B03-010 (deel IsKid) | HALF WERK in de werkmap, niet gecommit: 4 gewijzigde bestanden (BeheerController.cs, RouteTable.cs, PluginServiceRegistrator.cs, OpenApiBouwer.cs) en 3 nieuwe mappen (Core/Budget, Core/Planner, Core/Werker) | bouwstap "half werk afmaken" (A-VERKEN eerst) + review |
| media-guard-ultimate | Δ-MG-AUTH + Δ-MG-DUAL (Emby en Jelly Leon tegelijk; HARDE EIS) | gebouwd en gepusht (HEAD 1dcf318); technische review NIET gedaan | reviewstap (met R-HARDE-EIS en R-VEILIG) |
| media-guard-ultimate | ontwerpreview van het mediaserver-tabblad | HALF WERK in de werkmap, niet gecommit: 10 gewijzigde bestanden (web: mediaserver-tab.tsx, primitives.tsx, badge.tsx, peil-mg.css, i18n, tests; android: OverviewScreen.kt, TaalTest.kt) en nieuwe map docs/screenshots/peil/review-mediaserver | stap "ontwerpherstel afmaken" (A-VERKEN eerst, daarna R-ONTWERP) |
| my_house | tabelweergave bij 'Laatste 24 uur' | gebouwd en gepusht (HEAD dcbe73d); ontwerpreview gedaan; technische review AFGEBROKEN: 1 gewijzigd bestand niet gecommit (apps/web/e2e/12-grafiek-24-uur.e2e.ts) | reviewstap (beoordeel eerst de ene wijziging) |
| home-control-hub | B11-001...005 (Node-RED-automatisering): datamodel/migratie 0005, client, events, veilige acties, proefrun, versiebeheer, routes/worker, tests, E2E, OpenAPI | 12 commits gecommit en gepusht (HEAD 076f964); CI NIET beoordeeld; review NIET gedaan | reviewstap; eerst CI bekijken |
| home-control-hub | B11: afronding (documentatie, manifest, image-smoketest, ADR-0016) | HALF WERK in de werkmap, niet gecommit: 7 gewijzigde bestanden (.env.example, CHANGELOG.md, README.md, deploy/allinone/smoke-test.sh, het manifest, CUSTOM_APP.md, DELTA_MATRIX.md) en 2 nieuwe (NODE_RED_CUSTOM_APP.md, ADR-0016); afgebroken tijdens de image-smoketest; EVIDENCE.json NIET bijgewerkt | bouwstap "half werk afmaken" (R-MANIFEST verplicht) |
| jelly-leon-platform | B08-003, B08-004, I10-10-01...06 (plannen, installatie, update, terugzetten) | gebouwd en gepusht | reviewstap afmaken (zie volgende rij) |
| jelly-leon-platform | review van het bovenstaande | AFGEBROKEN halverwege: 1 herstelcommit gepusht (35fc44d "Review P2: geen plan op een oude meting, terugzetten bewezen met de digest"); HALF WERK: ADR-0022 gewijzigd en ADR-0024-review-p2.md nieuw, niet gecommit; CI niet beoordeeld | reviewstap opnieuw (volledig), half werk eerst beoordelen |
| ai-server-manager | P2 deel 1: B02-005, B01-007, B02-006 (policy-engine, approvals, executor) | HALF WERK in de werkmap, NIETS gecommit (HEAD 0001116): 23 gewijzigde bestanden (api: app.py, models.py, registry.py, routers, tests; executor: truenas.py, uitvoeren.py; policy: engine.py, verify.py; web: 2 schermen; ADR-0030; OpenAPI) en 7 nieuwe (migratie 0012_acties_goedkeuringen.py, hub/actions/, routers/actions.py, tests). Afgebroken tijdens formatter/linter/typecheck; tests niet aantoonbaar groen; EVIDENCE.json NIET bijgewerkt | bouwstap "half werk afmaken" (A-VERKEN eerst; R-VEILIG verplicht) |
| ai-server-manager | P2 deel 2: AI-beheer (B02-001, -002, -003, -004, -007, -008, -010, -011 e.v.) | NIET begonnen | bouwstappen |
| ai-server-manager | P2 deel 3: back-up/herstel en automatiseringen (B12-004...007, B01-008) | NIET begonnen | bouwstappen (HARDE EIS: back-up dekt Emby-kijkgegevens en MediaGuard-database) |
| ai-server-manager | onafhankelijke beveiligingsreview P2 (docs/security/P2_REVIEW.md) | NIET begonnen | stap met R-VEILIG op de kern van executor/policy/ondertekening |
| ai-server-manager | ontwerpstap P2-schermen (docs/ontwerp/HUB_P2_ONTWERP.md) | NIET begonnen | stap met A-ONTWERP |
| ai-server-manager | P2-UI in Peil (apps/web) en de ontwerpreview ervan | NIET begonnen | bouwstappen + R-ONTWERP |

Schoon en ongewijzigd in ronde 3: appstore-en-fork (7b3159d), zoeken-en-persoonlijke-ai (7a0148b), media-source-optimizer
(97ca519).

Let op voor de regisseur: in ai-server-manager staat het halve werk van de executor in dezelfde werkmap als waarin het plan
en de Excel worden bijgewerkt. Voeg bij een commit alleen de eigen paden toe (`git add <pad>`), nooit `git add -A`.
