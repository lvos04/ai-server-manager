# VOORTGANG - afvinkgrootboek van de regisseur

Laatst bijgewerkt: 2026-11-11 (aangemaakt bij de overdracht; nog niets afgevinkt).

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

## Topmodel-inzet

| datum | stap | rol | reden (welk van de vijf gevallen) | leverde het iets op (ja/nee en wat) |
|---|---|---|---|---|

Terugschakelregel: zie AGENTEN.md 7.7.

## Plan afmaken (eerste werk; zie PLAN_AFMAKEN.md)

| klaar | taak | opdrachtbestand (in <WERKMAP>/.lokaal/plan/afmaakopdrachten/) | niveau | rapport | meldingen verwerkt |
|---|---|---|---|---|---|
| [ ] | PA-1 controle STAPPEN_P2.md | controle_p2.md | N3 |  |  |
| [ ] | PA-2 controle AGENTEN.md | controle_agentmodel.md | N3 |  |  |
| [ ] | PA-3 controle POORTEN, BESLUITEN, VALKUILEN | controle_poorten.md | N3 |  |  |
| [ ] | PA-4 dekking.py afmaken en maak_voortgang.py | samen_dekking.md | N3 |  |  |
| [ ] | PA-5 STAPPEN_P3.md afmaken en controleren | afmaken_controle_p3.md | N3 |  |  |
| [ ] | PA-6 STAPPEN_P4_GOLF1_2.md afmaken en controleren | afmaken_controle_p4a.md | N3 |  |  |
| [ ] | PA-7 STAPPEN_P4_GOLF3_4.md afmaken en controleren | afmaken_controle_p4b.md | N3 |  |  |
| [ ] | PA-8 STAPPEN_P5.md afmaken en controleren | afmaken_controle_p5.md | N3 |  |  |
| [ ] | PA-9 STAPPEN_P6.md afmaken en controleren | afmaken_controle_p6.md | N3 |  |  |
| [ ] | PA-10 dekking.py --voortgang zonder fouten | (commando) | - |  |  |
| [ ] | PA-11 droogloop | droogloop.md | N2 |  |  |

## Half werk uit ronde 3 (afgebroken op 2026-11-11; NIETS ongezien weggooien of committen)

Reservekopie per repo: `<WERKMAP>/.lokaal/halfwerk/<repo>.patch` en `<repo>-nieuw.tgz`. Volledige stand: `<WERKMAP>/.lokaal/plan/STAND_RONDE3.md`.

| repo | wat er half ligt (niet gecommit) | wat al gepusht is maar NIET gereviewd | overgenomen door stap | afgehandeld |
|---|---|---|---|---|
| ai-server-manager | policy-engine, goedkeuringen, executor (23 gewijzigd, 7 nieuw; migratie 0012, hub/actions) | - |  | [ ] |
| home-control-hub | afronding B11: docs, manifest, rooktest, ADR-0016 (7 gewijzigd, 2 nieuw) | B11-001 t/m 005 (12 commits, t/m 076f964); CI niet beoordeeld |  | [ ] |
| jelly-leon-platform | review lifecycle-plannen: ADR-0022 gewijzigd, ADR-0024 nieuw | plannen, installatie, update, terugzetten + herstelcommit 35fc44d; CI niet beoordeeld |  | [ ] |
| media-guard-ultimate | ontwerpherstel mediaserver-tabblad (10 gewijzigd, schermafdrukken nieuw) | twee mediaservers en aanmelden (t/m 1dcf318) |  | [ ] |
| my_house | 1 testbestand (apps/web/e2e/12-grafiek-24-uur.e2e.ts) | tabel "Laatste 24 uur" (t/m dcbe73d); ontwerpreview wel gedaan |  | [ ] |
| jelly-leon | B03-018 en B03-010: 4 gewijzigd, mappen Core/Budget, Core/Planner, Core/Werker nieuw | contract 1.3, B03-017, B03-009 (t/m cc3e82b4d); CI niet beoordeeld |  | [ ] |

## Fase P2 (STAPPEN_P2.md; 38 stappen)

De volgorde binnen een baan en wat tegelijk mag staat in "Volgorde en banen" van STAPPEN_P2.md; deze tabel volgt de volgorde van het bestand.

| klaar | stap-ID | titel | baan (repo) | zwaar | moeilijkheid | vooraf (ingekort; de stap is leidend) | commit | CI-run | datum | opmerking |
|---|---|---|---|---|---|---|---|---|---|---|
| [ ] | S-P2-000 | Stand opnemen en half werk van ronde 3 veiligstellen | alle elf repos, alleen lezen (uit… | nee | gewoon | ronde 3 is gestopt (afgebroken op 2026-11-11 om 09:52; <WER… |  |  |  |  |
| [ ] | S-P2-010 | Policy-pakket en risicoclassificatie controleren en vastleggen | ai-server-manager | nee | gewoon | S-P2-000 |  |  |  |  |
| [ ] | S-P2-020 | Executor: TrueNAS-schrijfsleutel, NAS-verbinding en executorpagina | ai-server-manager | nee | hoog | S-P2-010 |  |  |  |  |
| [ ] | S-P2-030 | Executor: ExecutionRequest verifiëren, uitvoeren en teruglezen | ai-server-manager | nee | zeer hoog | S-P2-020 |  |  |  |  |
| [ ] | S-P2-040 | Hub: voorstel, preview, goedkeuring en ondertekening | ai-server-manager | ja (volledi… | zeer hoog | S-P2-030 |  |  |  |  |
| [ ] | S-P2-050 | Hub: apps installeren, bijwerken, terugzetten en verwijderen | ai-server-manager | nee | hoog | S-P2-040; S-P2-400 gepusht (de planner van jelly-leon-platf… |  |  |  |  |
| [ ] | S-P2-060 | Hub: dynamische blokkades en gates (pool, back-up, boiler) | ai-server-manager | nee | hoog | S-P2-050 |  |  |  |  |
| [ ] | S-P2-070 | Geheimen van catalogusapps via de vault | ai-server-manager | nee | hoog | S-P2-060; S-P2-500 gepusht (appstore-en-fork levert de vaul… |  |  |  |  |
| [ ] | S-P2-080 | Hub: acties via de eigenaar-connector, catalogusroute en ontkoppelen | ai-server-manager | nee | hoog | S-P2-070 |  |  |  |  |
| [ ] | S-P2-090 | Back-up: OneDrive-verificatie, herstelpunten per app en pre-update-ga… | ai-server-manager | nee | hoog | S-P2-080 |  |  |  |  |
| [ ] | S-P2-100 | Back-up: hersteltest-robot en rampenscenario | ai-server-manager | nee | hoog | S-P2-090 |  |  |  |  |
| [ ] | S-P2-110 | AI deel A: rechten en kosten, kennisinstrumenten, triage en plan-engi… | ai-server-manager | nee | hoog | S-P2-100 |  |  |  |  |
| [ ] | S-P2-120 | AI deel B: zelfreparatie, updates, automatiserings-AI en feedback | ai-server-manager | nee | hoog | S-P2-110 |  |  |  |  |
| [ ] | S-P2-130 | AI-chat-backend en veiligheidstests als releasepoort | ai-server-manager | nee | hoog | S-P2-120 |  |  |  |  |
| [ ] | S-P2-140 | Automatiseringen zonder code, Hub-kant | ai-server-manager | nee | hoog | S-P2-130; S-P2-310 gepusht (home-control-hub levert flow.ac… |  |  |  |  |
| [ ] | S-P2-150 | Monitorplan per app | ai-server-manager | nee | gewoon | S-P2-140 |  |  |  |  |
| [ ] | S-P2-160 | Ontwerpstap voor de P2-schermen van de Hub | ai-server-manager | nee | hoog | S-P2-150 (de routes van de backend staan dan in docs/openap… |  |  |  |  |
| [ ] | S-P2-170 | UI: goedkeuringen, actie-preview en uitvoering | ai-server-manager | ja (make we… | hoog | S-P2-160 |  |  |  |  |
| [ ] | S-P2-180 | UI: apps installeren, bijwerken, terugzetten en verwijderen | ai-server-manager | ja (make we… | hoog | S-P2-170 |  |  |  |  |
| [ ] | S-P2-190 | UI: back-ups en automatiseringen | ai-server-manager | ja (make we… | gewoon | S-P2-180 |  |  |  |  |
| [ ] | S-P2-200 | UI: AI-chat, monitorplan, "Geïmporteerd" en E15 | ai-server-manager | ja (make we… | gewoon | S-P2-190 |  |  |  |  |
| [ ] | S-P2-210 | Beveiligingsreview van P2 als geheel | ai-server-manager | nee | zeer hoog | S-P2-200 |  |  |  |  |
| [ ] | S-P2-220 | Images, rooktest, OpenAPI en schermafdrukken | ai-server-manager | ja (image-b… | gewoon | S-P2-210 |  |  |  |  |
| [ ] | S-P2-300 | B11: eventcatalogus, inname, wachtrij en proefrun | home-control-hub | nee | hoog | S-P2-000 |  |  |  |  |
| [ ] | S-P2-310 | B11: veilige acties, flow-tokens en isolatie van Node-RED | home-control-hub | nee | hoog | S-P2-300 |  |  |  |  |
| [ ] | S-P2-320 | B11: momentopnamen, versies en herstel van flows | home-control-hub | nee | hoog | S-P2-310 |  |  |  |  |
| [ ] | S-P2-330 | Connector: Authentik-acties toepassen met een ondertekend verzoek, en… | home-control-hub | nee | hoog | S-P2-320; S-P2-040 gepusht (de Hub ondertekent). Voor de ca… |  |  |  |  |
| [ ] | S-P2-340 | home-control-hub: image, rooktest en proef tegen de echte Hub | home-control-hub | ja (image-b… | gewoon | S-P2-330; S-P2-080 gepusht en S-P2-140 gepusht (de Hub kent… |  |  |  |  |
| [ ] | S-P2-400 | Lifecycle-planner controleren en het bewijs bijwerken | jelly-leon-platform | nee (de vol… | gewoon | S-P2-000 |  |  |  |  |
| [ ] | S-P2-410 | Node-RED: installatiemanifest, flowbundels en controles na installati… | jelly-leon-platform | ja (de rook… | hoog | S-P2-400 |  |  |  |  |
| [ ] | S-P2-420 | jelly-leon-platform: rooktest en conformiteit tegen de echte Hub-code | jelly-leon-platform | ja (image-b… | hoog | S-P2-410; S-P2-050 en S-P2-080 gepusht (de Hub neemt planne… |  |  |  |  |
| [ ] | S-P2-500 | Geheime waarden van catalogusapps: alleen een verwijzing naar de vault | appstore-en-fork | nee | hoog | S-P2-000. Deze stap loopt vóór S-P2-070 (de Hub-kant, C1.3-… |  |  |  |  |
| [ ] | S-P2-600 | MediaGuard: twee mediaservers, aanmelden per server, web en contractt… | media-guard-ultimate | ja (contrac… | hoog | S-P2-000 |  |  |  |  |
| [ ] | S-P2-610 | MediaGuard: upgradebewijs vanaf de vorige release (1.2.2) | media-guard-ultimate | ja (image-b… | hoog | S-P2-600 (de mediaservercode is dan definitief voor P2) |  |  |  |  |
| [ ] | S-P2-620 | MediaGuard: Android-app in en-US controleren | media-guard-ultimate | ja (Gradle … | gewoon | S-P2-610 (één schrijver per repo) |  |  |  |  |
| [ ] | S-P2-700 | my_house: tabel en grafiek "Laatste 24 uur" controleren en afronden | my_house | ja (de brow… | gewoon | S-P2-000 |  |  |  |  |
| [ ] | S-P2-900 | Bewijs samenvoegen: programmabewijs, Excel en STATUS | ai-server-manager | nee | gewoon | S-P2-010 t/m S-P2-700 zijn in <WERKMAP>/.lokaal/plan/uit/VO… |  |  |  |  |
| [ ] | S-P2-910 | Gate P2: onafhankelijke controle | ai-server-manager, home-control-h… | ja (A-GATE … | zeer hoog | S-P2-900 afgevinkt; er is in geen van de zes repos een kete… |  |  |  |  |

## Fase P3 (STAPPEN_P3.md; 47 stappen)

De volgorde binnen een baan en wat tegelijk mag staat in "Volgorde en banen" van STAPPEN_P3.md; deze tabel volgt de volgorde van het bestand.

| klaar | stap-ID | titel | baan (repo) | zwaar | moeilijkheid | vooraf (ingekort; de stap is leidend) | commit | CI-run | datum | opmerking |
|---|---|---|---|---|---|---|---|---|---|---|
| [ ] | S-P3-000 | Stand opnemen, half werk veiligstellen en open besluiten nalopen | de zeven repos van P3 (alleen lez… | nee | gewoon | geen |  |  |  |  |
| [ ] | S-P3-010 | ADR: adapters voor de bestaande apps | ai-server-manager | nee | gewoon | S-P3-000 klaar; in deze repo werkt geen schrijver van P2 |  |  |  |  |
| [ ] | S-P3-015 | ADR: MediaGuard-upgradebewijs in de Hub en rotatie bij een geplakte s… | ai-server-manager | nee | gewoon | S-P3-010 klaar; antwoord op Z-03 of de regel "zonder beslui… |  |  |  |  |
| [ ] | S-P3-020 | Hub: basis voor koppelingen met bestaande apps (opslag, geheim, uitga… | ai-server-manager | nee | hoog | S-P3-010 klaar (het ADR bepaalt map en opslag) |  |  |  |  |
| [ ] | S-P3-030 | Hub: adapter MediaGuard (alleen lezen) | ai-server-manager | nee | hoog | S-P3-020 klaar. S-P2-600 klaar of de terugval uit bouwpunt … |  |  |  |  |
| [ ] | S-P3-040 | Hub: adapter Media Source Optimizer (alleen lezen) | ai-server-manager | nee | gewoon | S-P3-020 klaar |  |  |  |  |
| [ ] | S-P3-050 | Hub: adapter my_house (alleen lezen, koppelcode) | ai-server-manager | nee | hoog | S-P3-020 klaar |  |  |  |  |
| [ ] | S-P3-060 | Hub: gezondheid van de binnenkant via de adapters | ai-server-manager | nee | gewoon | S-P3-030, S-P3-040 en S-P3-050 klaar |  |  |  |  |
| [ ] | S-P3-070 | Hub-UI: bestaande apps koppelen (sleutel of koppelcode invoeren) | ai-server-manager | nee | gewoon | S-P3-060 klaar |  |  |  |  |
| [ ] | S-P3-075 | Hub: incident- en downloadketen over MediaGuard en MSO (backend) | ai-server-manager | nee | gewoon | S-P3-030 en S-P3-040 klaar |  |  |  |  |
| [ ] | S-P3-080 | Hub-UI: scherm Media (MediaGuard en MSO) | ai-server-manager | nee | gewoon | S-P3-075 klaar |  |  |  |  |
| [ ] | S-P3-090 | Hub-UI: scherm Huis (my_house, alleen kijken) | ai-server-manager | nee | gewoon | S-P3-050 klaar |  |  |  |  |
| [ ] | S-P3-100 | Hub: back-updekking van de bestaande apps en het Emby-exportarchief | ai-server-manager | nee | hoog | S-P3-030, S-P3-040 en S-P3-050 klaar; S-P2-090 klaar |  |  |  |  |
| [ ] | S-P3-110 | Hub: noodstop AAN in MediaGuard via het goedkeuringspad | ai-server-manager | nee | hoog | Gate P2 afgevinkt; S-P3-600 gepusht (scope emergency_stop:o… |  |  |  |  |
| [ ] | S-P3-120 | Hub: een MSO-wijziging goedkeuren via de Hub | ai-server-manager | nee | hoog | Gate P2 afgevinkt; S-P3-240 gepusht (MSO kent expected_prev… |  |  |  |  |
| [ ] | S-P3-130 | Hub: bewaakt schrijfpad naar my_house (ondertekend verzoek) | ai-server-manager | nee | hoog | Gate P2 afgevinkt; S-P3-742 gepusht; S-P3-050 klaar; S-P3-0… |  |  |  |  |
| [ ] | S-P3-150 | Hub: energie en kosten met herkomst (backend) | ai-server-manager | nee | gewoon | S-P3-040 klaar; S-P3-310 gepusht (of het ADR van S-P3-010 w… |  |  |  |  |
| [ ] | S-P3-160 | Hub-UI: scherm Kosten | ai-server-manager | nee | gewoon | S-P3-150 klaar |  |  |  |  |
| [ ] | S-P3-170 | Hub: images, rooktest, OpenAPI en schermafdrukken van P3 | ai-server-manager | ja (image-b… | gewoon | alle eerdere stappen van deze baan klaar, behalve stappen d… |  |  |  |  |
| [ ] | S-P3-180 | A-documenten: vastleggen wat het platform nu dekt (A09...A14, A17...A… | ai-server-manager | nee | gewoon | S-P3-170 klaar |  |  |  |  |
| [ ] | S-P3-200 | MSO: opruimen en CI op de werkbranch | media-source-optimizer | nee | gewoon | S-P3-000 klaar; besluit Z-10 genomen of de regel "zonder be… |  |  |  |  |
| [ ] | S-P3-205 | MSO: weiger een database van een nieuwere versie | media-source-optimizer | nee | hoog | S-P3-200 klaar |  |  |  |  |
| [ ] | S-P3-210 | MSO: build-gegevens op de Systeem-kaart | media-source-optimizer | ja (stackpr… | gewoon | S-P3-200 klaar |  |  |  |  |
| [ ] | S-P3-215 | MSO: terugkeerpad na inloggen volgens het contract | media-source-optimizer | nee | gewoon | S-P3-200 klaar |  |  |  |  |
| [ ] | S-P3-220 | MSO: machine-sleutel met scopes | media-source-optimizer | nee | hoog | S-P3-200 klaar |  |  |  |  |
| [ ] | S-P3-230 | MSO: connector, leesdeel | media-source-optimizer | nee | gewoon | S-P3-220 klaar |  |  |  |  |
| [ ] | S-P3-240 | MSO: wijzigingen via de connector, gebonden aan preview_hash | media-source-optimizer | nee | hoog | S-P3-230 klaar |  |  |  |  |
| [ ] | S-P3-250 | MSO: healthcheck die eerst naar 568 wisselt | media-source-optimizer | ja (image-b… | hoog | S-P3-200 klaar |  |  |  |  |
| [ ] | S-P3-255 | MSO: vaste digests, SBOM en afhankelijkheidscontrole | media-source-optimizer | ja (image-b… | gewoon | S-P3-250 klaar |  |  |  |  |
| [ ] | S-P3-260 | MSO: upgradetest vanaf de vorige image | media-source-optimizer | ja (image-b… | hoog | S-P3-205 en S-P3-255 klaar |  |  |  |  |
| [ ] | S-P3-265 | MSO: contracttest tegen de echte MediaGuard-image | media-source-optimizer | ja (stackpr… | gewoon | S-P3-200 klaar |  |  |  |  |
| [ ] | S-P3-270 | MSO: opslag en groei met herkomst | media-source-optimizer | ja (stackpr… | gewoon | S-P3-210 klaar |  |  |  |  |
| [ ] | S-P3-280 | MSO: Peil-ronde en schermbreedtes | media-source-optimizer | ja (stackpr… | gewoon | S-P3-270 klaar |  |  |  |  |
| [ ] | S-P3-290 | MSO: manifest en installatiedocument (standaard Custom App) | media-source-optimizer | nee | gewoon | S-P3-250 en S-P3-255 klaar |  |  |  |  |
| [ ] | S-P3-300 | Energie: bron my_house en de dekkingsmatrix | home-control-hub | nee | gewoon | S-P3-010 klaar (het ADR wijst aan wie de energiecijfers van… |  |  |  |  |
| [ ] | S-P3-310 | Energie: tijdreeks met zomertijd, tellerreset en metervervanging | home-control-hub | nee | hoog | S-P3-300 klaar |  |  |  |  |
| [ ] | S-P3-320 | Energie: werklast en reserveringen (alleen plannen en voorstellen) | home-control-hub | nee | gewoon | S-P3-310 klaar |  |  |  |  |
| [ ] | S-P3-330 | Energie: advies over kosten met aannames en bandbreedte | home-control-hub | nee | gewoon | S-P3-310 en S-P3-320 klaar |  |  |  |  |
| [ ] | S-P3-340 | Energie: meldingen bij afwijkingen | home-control-hub | nee | gewoon | S-P3-310 klaar |  |  |  |  |
| [ ] | S-P3-350 | Energie op de statuspagina van de dienst | home-control-hub | nee | gewoon | S-P3-340 klaar |  |  |  |  |
| [ ] | S-P3-400 | Platform: ADR en gereedschap voor de controlelijsten I03...I20 | jelly-leon-platform | nee | gewoon | S-P3-000 klaar; geen keten van P2 actief in deze repo |  |  |  |  |
| [ ] | S-P3-410 | Platform: controlelijsten I03 (MediaGuard) en I04 (Media Source Optim… | jelly-leon-platform | nee | gewoon | S-P3-400 klaar |  |  |  |  |
| [ ] | S-P3-420 | Platform: controlelijsten I15 (Immich), I16 (Prowlarr) en I17 (SABnzb… | jelly-leon-platform | nee | gewoon | S-P3-400 klaar |  |  |  |  |
| [ ] | S-P3-430 | Platform: controlelijsten I18 (qBittorrent), I19 (Seerr) en I20 (Baza… | jelly-leon-platform | nee | gewoon | S-P3-400 klaar |  |  |  |  |
| [ ] | S-P3-440 | Platform: controlelijst I05 (my_house) met de standaard Custom App al… | jelly-leon-platform | nee | gewoon | S-P3-400 klaar; keuze van de gebruiker over de I05-titels (… |  |  |  |  |
| [ ] | S-P3-450 | Platform: manifestkopieen van MediaGuard, MSO en my_house | jelly-leon-platform | nee | gewoon | S-P3-290, S-P3-660 en S-P3-755 gepusht (de drie manifesten … |  |  |  |  |
| [ ] | S-P3-500 | Appstore: register van de bestaande apps laten meebewegen met de A-do… | appstore-en-fork | nee | gewoon | S-P3-180 gepusht (de A-documenten zijn bijgewerkt in ai-ser… |  |  |  |  |

## Fase P4: P4-0, golf 1 en golf 2 (STAPPEN_P4_GOLF1_2.md; 35 stappen)

De volgorde binnen een baan en wat tegelijk mag staat in "Volgorde en banen" van STAPPEN_P4_GOLF1_2.md; deze tabel volgt de volgorde van het bestand.

| klaar | stap-ID | titel | baan (repo) | zwaar | moeilijkheid | vooraf (ingekort; de stap is leidend) | commit | CI-run | datum | opmerking |
|---|---|---|---|---|---|---|---|---|---|---|
| [ ] | S-P40-10 | Stand P4-0 vaststellen (dossier voor de gate) | geen wijziging; leest in jelly-le… | nee | gewoon | geen |  |  |  |  |
| [ ] | S-P40-20 | MediaGuard: aanmelden per server en twee mediaservers bewijzen met de… | media-guard-ultimate | ja (echte E… | gewoon | S-P40-10 klaar; BG-01 genomen; S-P2-600 en S-P2-610 uit <WE… |  |  |  |  |
| [ ] | S-P40-30 | JLT-73 afmaken: overnameproef tegen de Jelly Leon-image met het bewij… | jelly-leon | ja (echte E… | gewoon | S-P40-20 klaar (contracttest met de Jelly Leon-image gedraa… |  |  |  |  |
| [ ] | S-P40-32 | Clientdeel JLT-70 voorbereiden: de proefrun laat een overdracht voor … | jelly-leon | ja (proefru… | gewoon | S-P40-30 klaar |  |  |  |  |
| [ ] | S-P40-40 | Register upstream-gedrag en clientmatrix aanvullen (B03-019) | jelly-leon | ja (runtime… | gewoon | S-G1-16 klaar (schone werkboom, lokale image) |  |  |  |  |
| [ ] | S-P40-45 | Sync-proef en negatieve upgradeproef met een 12.y-tag (voorwaardelijk) | jelly-leon (de webproef in bouwpu… | ja (.NET-bu… | hoog | S-P40-40 klaar; upstream heeft een 12.x-tag die nieuwer is … |  |  |  |  |
| [ ] | S-P40-50 | Definitieve baselines en controle-run op de forkbasis (B03-016) | jelly-leon | ja (meetslo… | gewoon | S-P40-90 klaar; de keuze "voormeting 12.4 telt als definiti… |  |  |  |  |
| [ ] | S-P40-60 | Voormeting Watch Together (B03-020) | jelly-leon | ja (meerder… | gewoon | S-P40-50 klaar |  |  |  |  |
| [ ] | S-P40-62 | Voormeting aanbevelingen (B03-030) | jelly-leon | ja (stub-bi… | gewoon | S-P40-50 klaar; BG-37 (genomen: beperkt gelicentieerde test… |  |  |  |  |
| [ ] | S-P40-64 | Voormeting apparaten en afspeelfouten (B03-060) | jelly-leon | ja (Playwri… | gewoon | S-P40-50 klaar |  |  |  |  |
| [ ] | S-P40-66 | Meetlat segmenten: bevroren testset, harnas en baselines (B03-070) | jelly-leon | ja (testset… | gewoon | S-P40-50 klaar; BG-32 (Intro Skipper alleen als testbaselin… |  |  |  |  |
| [ ] | S-P40-70 | Tablet-emulator en het emulatordeel van JLT-60, JLT-63 en JLT-70 | jelly-leon-clients | ja (emulato… | gewoon | S-P40-72 klaar; voor bouwpunt 4 en 5: S-P40-32 klaar (overd… |  |  |  |  |
| [ ] | S-P40-72 | Compat-harnas veiliger maken: eigen netwerk, willekeurige testwachtwo… | jelly-leon-clients | ja (een emu… | gewoon | S-P40-10 klaar |  |  |  |  |
| [ ] | S-P40-92 | Bewijs uit de andere repos overnemen in jelly-leon (JLT-60, JLT-70, c… | jelly-leon | nee | gewoon | S-P40-70 klaar; S-P40-20 klaar; S-P40-50 klaar |  |  |  |  |
| [ ] | S-P40-80 | Overname-assistent: ontwerp en ADR (geen terminal voor de gebruiker) | jelly-leon | nee | gewoon | S-P40-30 klaar; BG-22 genomen of de terugval uit hoofdstuk … |  |  |  |  |
| [ ] | S-P40-82 | Overname-assistent bouwen in het beheer van Jelly Leon | jelly-leon | ja (.NET-bu… | hoog | S-P40-80 klaar en de runtime gekozen; S-G1-14 klaar (pijpli… |  |  |  |  |
| [ ] | S-P40-90 | Desktop-spike in het meetharnas bijwerken | jelly-leon | ja (desktop… | gewoon | S-P40-40 klaar |  |  |  |  |
| [ ] | S-P40-95 | Gate P4-0 | geen (A-GATE leest in jelly-leon,… | nee | gewoon | S-P40-20, S-P40-30, S-P40-32, S-P40-40, S-P40-50, S-P40-70,… |  |  |  |  |
| [ ] | S-G1-16 | Stand B03-017 vastzetten: werkboom schoon, poort groen, lokale image … | jelly-leon | ja (grote .… | gewoon | S-P40-10, S-G1-15 en S-P40-12 klaar (de werkboom van jelly-… |  |  |  |  |
| [ ] | S-G1-10 | Kern B03-017 controleren: prototype op fork en stock, JLT-68, JLT-64 … | jelly-leon | ja (contain… | gewoon | S-G1-16 klaar (lokale image); de P4-0-stappen van de baan j… |  |  |  |  |
| [ ] | S-G1-12 | Hub-koppeling JL4: beveiligingsreview en herstel | jelly-leon | nee (alleen… | hoog | S-G1-10 klaar |  |  |  |  |
| [ ] | S-G1-14 | Foutcatalogus, 1 MiB per route, IStartupFilter-spike, health en events | jelly-leon | nee (plugin… | gewoon | S-G1-12 klaar; Gate P4-0 |  |  |  |  |
| [ ] | S-G1-18 | Privacy: persoonsgegevensregister, UserDeleted, kinderprofiel | jelly-leon | nee (alleen… | gewoon | S-G1-14 klaar; besluit BG-03 genomen, of de terugval uit ho… |  |  |  |  |
| [ ] | S-G1-20 | Geheimenmap, mountcontrole, wezenbreker, spoorsleutel, export en impo… | jelly-leon | nee (plugin… | gewoon | S-G1-18 klaar |  |  |  |  |
| [ ] | S-G1-30 | Analysewerker in de image | jelly-leon | ja (image-b… | gewoon | S-G1-20 klaar; Gate P4-0 |  |  |  |  |
| [ ] | S-G1-32 | Werkerbewaker en socket | jelly-leon | ja (image-b… | hoog | S-G1-30 klaar |  |  |  |  |
| [ ] | S-G1-34 | Bestandspas en featurecache | jelly-leon | ja (image-b… | gewoon | S-G1-32 klaar |  |  |  |  |
| [ ] | S-G1-36 | Globale batchplanner | jelly-leon | ja (de pauz… | hoog | S-G1-34 klaar |  |  |  |  |
| [ ] | S-G1-50 | MediaGuard-viewerclient via de Hub (B03-009) | jelly-leon | ja (plugin-… | hoog | S-G1-36 klaar; S-G1-12 klaar; besluit BG-04 genomen (via de… |  |  |  |  |
| [ ] | S-G1-38 | Budgetbeslisser G1 t/m G10 | jelly-leon | nee (plugin… | hoog | S-G1-50 klaar |  |  |  |  |
| [ ] | S-G1-40 | Gecombineerde belastingtest JLT-66 | jelly-leon | ja (exclusi… | hoog | S-G1-38 klaar; de lokale image is opnieuw gebouwd op de sta… |  |  |  |  |
| [ ] | S-G1-60 | Haakmodule in de webclient | jelly-leon-web | ja (npm-pro… | gewoon | S-P40-10 klaar; geen besluit nodig. Deze stap valt buiten P… |  |  |  |  |
| [ ] | S-G1-70 | Manifest, CUSTOM_APP en web-verwijzing bijwerken | jelly-leon | ja (image-b… | gewoon | S-P40-82 klaar (of uitdrukkelijk uitgesteld door de regisse… |  |  |  |  |
| [ ] | S-G1-80 | Eindrun golf 1: JLT-64, JLT-65, JLT-68 | jelly-leon | ja (contain… | gewoon | S-G1-70 klaar (de image van de eindstand); S-G1-12, S-G1-14… |  |  |  |  |
| [ ] | S-G1-90 | Gate golf 1 | geen (A-GATE leest in jelly-leon … | nee | gewoon | S-G1-80 klaar; Gate P4-0 voorgelegd en door de gebruiker be… |  |  |  |  |

## Fase P4: golf 3 en golf 4 (STAPPEN_P4_GOLF3_4.md; 73 stappen)

De volgorde binnen een baan en wat tegelijk mag staat in "Volgorde en banen" van STAPPEN_P4_GOLF3_4.md; deze tabel volgt de volgorde van het bestand.

| klaar | stap-ID | titel | baan (repo) | zwaar | moeilijkheid | vooraf (ingekort; de stap is leidend) | commit | CI-run | datum | opmerking |
|---|---|---|---|---|---|---|---|---|---|---|
| [ ] | S-G3-01 | Module Quality: fundament, eigen opslag en alleen-lezen-garanties | jelly-leon | nee (plugin… | gewoon | Gate P4-0 en Gate golf 1 aantoonbaar (B03-001, B03-013, B03… |  |  |  |  |
| [ ] | S-G3-02 | Jobtypes quality.* en kostenmodel in de globale batchplanner | jelly-leon | nee | gewoon | S-G3-01; planner en werker van B03-018 aanwezig (Gate golf … |  |  |  |  |
| [ ] | S-G3-03 | Module Subtitles: fundament, stabiele spoorsleutels en NL-dekking (al… | jelly-leon | nee | gewoon | Gate golf 1 (B03-017; spoorsleutel volgens bouwsteen 10.12)… |  |  |  |  |
| [ ] | S-G3-04 | Watch Together: telemetrieroute en diagnose (serverdeel van B03-024) | jelly-leon | nee | gewoon | WT-1-gate geslaagd (B03-021: decorator of core-patch); B03-… |  |  |  |  |
| [ ] | S-G3-05 | Ondertiteltoolkit in de analysewerker (subtitle.inventory, subtitle.q… | jelly-leon | ja (image-b… | gewoon | S-G3-03; analysewerker B03-018 met een vastgepinde Python-o… |  |  |  |  |
| [ ] | S-G3-06 | Ondertitelsync met veiligheidstoetsen (subtitle.sync) | jelly-leon | ja (image-b… | hoog | S-G3-05. Geen besluit nodig (BG-25 gaat over een gecorrigee… |  |  |  |  |
| [ ] | S-G3-07 | Beslisregels ondertitels en MediaGuard-leesroutes | jelly-leon | nee | gewoon | S-G3-03; viewerclient B03-009 (golf 1). BG-04 is genomen (v… |  |  |  |  |
| [ ] | S-G3-08 | Publicatie van gesynchroniseerde kopieen en beleid voor onthouden spo… | jelly-leon | ja (differe… | hoog | S-G3-06; BG-19 genomen (zonder besluit stopt deze stap en m… |  |  |  |  |
| [ ] | S-G3-09 | Streamroutes zonder inlog: meting per client, spike en ADR | jelly-leon | ja (server … | gewoon | Gate golf 1 (deel IsKid van B03-010 en de IStartupFilter-sp… |  |  |  |  |
| [ ] | S-G3-10 | Streamroutes: authenticatiefilter bouwen en met clients bewijzen | jelly-leon | ja (clientt… | hoog | S-G3-09 met een ADR die een route kiest. |  |  |  |  |
| [ ] | S-G3-11 | Kwaliteitscontrole niveau 0, 1 en 1,5 met triggers | jelly-leon | nee (de met… | gewoon | S-G3-02. BG-23: zonder besluit steekproef voor alles en vol… |  |  |  |  |
| [ ] | S-G3-12 | Kwaliteitscontrole niveau 2 (volledige decode) en de meting op het co… | jelly-leon | ja (decode … | hoog | S-G3-11. BG-23 (hele bibliotheek alleen na dat besluit). |  |  |  |  |
| [ ] | S-G3-13 | Kwaliteitscontrole niveau 3: teksttaal en ondertitelsync via de F3-to… | jelly-leon | nee | gewoon | S-G3-12 en S-G3-06 (toolkit en syncmeter). BG-25: zonder be… |  |  |  |  |
| [ ] | S-G3-14 | Bewijs per bevinding, verificatierun, feedback en onderdrukkingen | jelly-leon | nee | gewoon | S-G3-13. BG-24: zonder besluit miniaturen uit (Q5b geeft 50… |  |  |  |  |
| [ ] | S-G3-15 | Quality en MediaGuard: alleen lezen, geen dubbel werk, herstel als de… | jelly-leon | nee | gewoon | S-G3-14; viewerclient B03-009. BG-04 genomen (via de Hub). … |  |  |  |  |
| [ ] | S-G3-16 | Pluginpagina "Mediakwaliteit" voor beheerders | jelly-leon | ja (image e… | gewoon | S-G3-15. BG-24 (label en "Meld een probleem" standaard uit). |  |  |  |  |
| [ ] | S-G3-17 | Watch Together: zichtbaarheid, uitnodigingen en deelnemersbeheer | jelly-leon | nee (plugin… | hoog | WT-1-gate geslaagd (B03-021). BG-11 genomen: zonder besluit… |  |  |  |  |
| [ ] | S-G3-18 | Watch Together: kinderprofiel en ouderlijk toezicht | jelly-leon | nee | gewoon | S-G3-17. BG-03 (definitie van een kinderprofiel) hoort voor… |  |  |  |  |
| [ ] | S-G3-19 | Watch Together: haperbeleid zonder IgnoreWait, met racetest | jelly-leon | ja (haperme… | hoog | S-G3-17; planner B03-018 (golf 1). BG-13: zonder besluit is… |  |  |  |  |
| [ ] | S-G3-20 | Watch Together: volgmodus voor clients zonder SyncPlay (serverdeel) | jelly-leon | nee | gewoon | S-G3-17. BG-10 genomen: zonder besluit start deze stap NIET… |  |  |  |  |
| [ ] | S-G3-21 | Volgmodus bewijzen in de Android TV-emulator | jelly-leon | ja (emulato… | gewoon | S-G3-20 (en dus BG-10 genomen); een lokale image met S-G3-2… |  |  |  |  |
| [ ] | S-G3-22 | Segmenten: ondertitel- en hoofdstuksignalen en families | jelly-leon | nee (signal… | gewoon | B03-071 en B03-072 (golf 2: module met segments.db); de ged… |  |  |  |  |
| [ ] | S-G3-23 | Watch Together: externe deelnemers via VPN (alleen na BG-09) | jelly-leon | ja (netwerk… | hoog | BG-09 genomen en "aan". Zonder dat besluit wordt deze stap … |  |  |  |  |
| [ ] | S-G3-24 | Webplugin Watch Together: gezaaide driftcorrectie, telemetrie en menu | jelly-leon-web | ja (npm-bui… | hoog | S-G3-04; de webhaakmodule en de config.json-generator van B… |  |  |  |  |
| [ ] | S-G3-25 | Kwaliteitslabel op de itempagina (webdeel van B03-057) | jelly-leon-web | ja (npm-bui… | gewoon | S-G3-14 (route Q2 bestaat); S-G3-24 is klaar (zelfde baan).… |  |  |  |  |
| [ ] | S-G3-26 | Native SyncPlay op Android TV (alleen als BG-10 "clientpatch" zegt) | jelly-leon-clients | ja (Gradle … | hoog | BG-10 genomen met de keuze "clientpatch". Zonder die keuze … |  |  |  |  |
| [ ] | S-G3-27 | Compat-regressie en differentiele run per module-oplevering (herhaals… | jelly-leon | ja (image-b… | gewoon | deze stap draait vier keer: na S-G3-08 (Subtitles), na S-G3… |  |  |  |  |
| [ ] | S-G4-01 | Spike lanewrapper (NativeAOT met execv) en ADR | jelly-leon | ja (tijdmet… | hoog | gate golf 3; B03-062 (GPU-assistent, golf 2). |  |  |  |  |
| [ ] | S-G4-02 | Lanewrapper en socketdienst bouwen | jelly-leon | nee (build … | hoog | S-G4-01 met een ADR die optie A of A' kiest. Bij optie B ve… |  |  |  |  |
| [ ] | S-G4-03 | Wrapper in de image en laneplanner | jelly-leon | ja (image-b… | hoog | S-G4-02. BG-28 (rolverdeling van de GPU's, D08): zonder bev… |  |  |  |  |
| [ ] | S-G4-04 | Gedeeld GPU-budget met MediaGuard (alleen lezen) | jelly-leon | nee (contra… | hoog | S-G4-03; de MediaGuard-viewerclient van golf 1 (B03-009). B… |  |  |  |  |
| [ ] | S-G4-05 | Apparaten: probe-, advies- en uitkomstroutes (serverdeel) | jelly-leon | nee | gewoon | B03-061 (golf 2: module Devices met devices.db). Deze stap … |  |  |  |  |
| [ ] | S-G4-06 | Geleerde profielen per apparaat met bevestiging | jelly-leon | nee | gewoon | S-G4-05; de testset met gecontroleerde fouten van B03-060 (… |  |  |  |  |
| [ ] | S-G4-07 | Bescherming van stock-clients en de MediaGuard-afspeeltest | jelly-leon | ja (Playbac… | hoog | S-G4-06. BG-26 (opt-in voor officiele apps en stock-clients… |  |  |  |  |
| [ ] | S-G4-08 | HDR/DV-, audio- en ondertitelregels en de uitleg "Waarom?" (serverdee… | jelly-leon | nee | gewoon | S-G4-06. BG-28 (GPU-rollen) en BG-29 (kwaliteitslabel en fe… |  |  |  |  |
| [ ] | S-G4-09 | Watch Together: diagnose per deelnemer en capaciteitsadvies voor de s… | jelly-leon | ja (voorspe… | gewoon | S-G4-04 (capaciteit van de laneplanner) en S-G3-19 (haperbe… |  |  |  |  |
| [ ] | S-G4-10 | Watch Together: chat en reacties, serverdeel (alleen na BG-12) | jelly-leon | nee | gewoon | S-G3-18 (kinderregels). BG-12: zegt het besluit "niet bouwe… |  |  |  |  |
| [ ] | S-G4-11 | Watch Together: connector-items en events voor de Hub | jelly-leon | nee | gewoon | S-G3-17 tot en met S-G3-20. De Hub-pin JL4 van golf 1 besta… |  |  |  |  |
| [ ] | S-G4-12 | Aanbevelingen: connector-items, gedragsregister en prestatiemeting | jelly-leon | ja (meting … | gewoon | B03-035 (golf 2; gate G-F2-5). Gate G-F2-9 is de uitkomst v… |  |  |  |  |
| [ ] | S-G4-13 | Ondertitels: de gesynchroniseerde kopie als gemarkeerd spoor, nooit s… | jelly-leon | nee | gewoon | S-G3-08 (publicatie en spoorkeuzes). BG-19 en BG-21 zijn da… |  |  |  |  |
| [ ] | S-G4-14 | Quality: connector-items, bewijsroute en health-checks voor de Hub | jelly-leon | nee | gewoon | S-G3-15. Subfase QC-6. De Hub-pin JL4 bestaat. |  |  |  |  |
| [ ] | S-G4-15 | Segmenten: correctieroutes, review, meldingen en voorkeur per gebruik… | jelly-leon | nee | hoog | B03-071, B03-072 en B03-073 (golf 2: segmentprovider met se… |  |  |  |  |
| [ ] | S-G4-40 | Segmenten: leren van bevestigde correcties, heranalyse en kwaliteitsm… | jelly-leon | ja (holdout… | hoog | S-G4-15 en S-G3-22 (families en varianten). Subfase F6-S5. … |  |  |  |  |
| [ ] | S-G4-16 | Beheerpagina "Intro's en aftiteling" en afronding van B03-007 | jelly-leon | ja (image e… | gewoon | S-G4-15 en S-G4-40. BG-31 (standaardgedrag van de knoppen):… |  |  |  |  |
| [ ] | S-G4-17 | Segmenten: taaktypen voor de planner, MediaGuard alleen lezen en conn… | jelly-leon | ja (meting … | hoog | de planner en de analysewerker (B03-018) en de MediaGuard-v… |  |  |  |  |
| [ ] | S-G4-18 | Apparaten: connector-items voor de Hub en het clientrapport alleen le… | jelly-leon | nee | gewoon | S-G4-06 (geleerde profielen) en S-G4-03 (lanes voor gpu_lan… |  |  |  |  |
| [ ] | S-G4-19 | Contractcontrole: eventnamen, foutcatalogus, verzoekgrootte en Hub-pin | jelly-leon | nee | gewoon | S-G4-11, S-G4-13, S-G4-14, S-G4-17 en S-G4-18 (alle connect… |  |  |  |  |
| [ ] | S-G4-42 | Pluginpagina "Apparaten" voor beheerders (regels beslissen, correctie… | jelly-leon | ja (image e… | gewoon | S-G4-07 en S-G4-18. BG-26 (wie een verruimende regel mag be… |  |  |  |  |
| [ ] | S-G4-44 | Pluginpagina "Watch Together" voor beheerders afmaken | jelly-leon | ja (image e… | gewoon | S-G4-11. De pagina zelf is in golf 2 begonnen (WP-JSON B03-… |  |  |  |  |
| [ ] | S-G4-20 | Rij "Aanbevolen voor jou" op het startscherm (haak en rij) | jelly-leon-web | ja (npm-bui… | hoog | B03-035 (routes van de module Recommendations, golf 2); de … |  |  |  |  |
| [ ] | S-G4-45 | Aanbevelingen: dialogen "Waarom aanbevolen?", "Wat kijk je graag?" en… | jelly-leon-web | ja (npm-bui… | gewoon | S-G4-20. |  |  |  |  |
| [ ] | S-G4-21 | Web: rolbepaling, capability-probe en advies samenvoegen in het appar… | jelly-leon-web | ja (npm-bui… | hoog | S-G4-05 (routes E1 en E2 in de plugin). S-G4-25 levert de m… |  |  |  |  |
| [ ] | S-G4-22 | Web: stall-detectie met terugval, kwaliteitslabel en "Waarom?" in Pla… | jelly-leon-web | ja (npm-bui… | hoog | S-G4-21; S-G4-08 (uitlegroute E5 in de plugin). BG-29: zond… |  |  |  |  |
| [ ] | S-G4-41 | Web: scherm "Dit apparaat" en de bevestigingsproef | jelly-leon-web | ja (npm-bui… | gewoon | S-G4-21 en S-G4-22; S-G4-06 (routes E6, E7, E8 en E8b in de… |  |  |  |  |
| [ ] | S-G4-23 | Web: skipknoppen per type, standaardactie en groepsregel (drie haken) | jelly-leon-web | ja (npm-bui… | hoog | S-G4-16 (serverdeel, marge aan het einde); S-G4-15 (route v… |  |  |  |  |
| [ ] | S-G4-46 | Web: hint na de aftiteling, "Klopt niet", correctiepaneel en voorkeur… | jelly-leon-web | ja (npm-bui… | gewoon | S-G4-23; S-G4-15 (correctie-, meld- en voorkeurroutes in de… |  |  |  |  |
| [ ] | S-G4-43 | Web: capaciteitsadvies voor de start van een groep (dialoog) | jelly-leon-web | ja (npm-bui… | gewoon | S-G4-09 (route E19 in de plugin); S-G3-24 (webplugin Watch … |  |  |  |  |
| [ ] | S-G4-24 | Web: strook voor reacties en chat (alleen als BG-12 "aan" is) | jelly-leon-web | ja (npm-bui… | gewoon | BG-12 moet "aan" zijn; S-G4-10 (routes E14 en E15 in de plu… |  |  |  |  |
| [ ] | S-G4-25 | Clients: marker jellyLeonBuild in de Android- en desktop-build | jelly-leon-clients | ja (Gradle-… | gewoon | geen stap van dit bestand; mag starten voor de gate van gol… |  |  |  |  |
| [ ] | S-G4-26 | Android TV: capabilityrapport automatisch sturen en beperkende regels… | jelly-leon-clients | ja (Gradle-… | hoog | S-G4-05 (route E2) en S-G4-06 (regels). BG-30 (mag de Jelly… |  |  |  |  |
| [ ] | S-G4-27 | Android TV: overlay-tekst per segmenttype en Recap standaard "vragen" | jelly-leon-clients | ja (Gradle-… | gewoon | S-G4-16. BG-31 met optie a1 (eigen knopteksten en daarmee c… |  |  |  |  |
| [ ] | S-G4-28 | Android: knoptekst per type in de native speler; desktop: marge aan h… | jelly-leon-clients | ja (Gradle-… | gewoon | S-G4-27. BG-31 (optie a1) en BG-08; zonder een van beide st… |  |  |  |  |
| [ ] | S-G4-29 | Clientmatrix aanbevelingen in de emulators (met loggende proxy) | jelly-leon-clients | ja (emulato… | gewoon | S-G4-20 en S-G4-45 (rij en dialogen in web); S-G4-12 (provi… |  |  |  |  |
| [ ] | S-G4-30 | Clientmatrix golf 4: ondertitels, kwaliteit, apparaten en skipknoppen… | jelly-leon-clients | ja (emulato… | gewoon | S-G4-13, S-G4-14, S-G4-07, S-G4-23, S-G4-46, S-G4-26, S-G4-… |  |  |  |  |
| [ ] | S-G4-31 | Hub: adapter voor Jelly Leon en de stap "Hub-sleutelset kopieren" | ai-server-manager | nee (alleen… | hoog | S-P3-010, S-P3-020 en S-P3-070 (STAPPEN_P3.md: ADR, adapter… |  |  |  |  |
| [ ] | S-G4-32 | Hub: kaartbasis voor Jelly Leon op het scherm Media en de eventtypes … | ai-server-manager | ja (make we… | gewoon | S-G4-31; S-P3-080 (scherm Media) en S-P3-075 (incidentketen… |  |  |  |  |
| [ ] | S-G4-33 | Hub-kaart "Watch Together" | ai-server-manager | ja (make we… | gewoon | S-G4-32; S-G4-11 (itemtype watch_together_stats en de event… |  |  |  |  |
| [ ] | S-G4-34 | Hub-kaart "Aanbevelingen · Jelly Leon" en het detailscherm | ai-server-manager | ja (make we… | gewoon | S-G4-32; S-G4-12 (itemtypen recommender_status en recommend… |  |  |  |  |
| [ ] | S-G4-36 | Hub-kaart "Mediakwaliteit" met problemen-inbox en bewijs | ai-server-manager | ja (make we… | gewoon | S-G4-32; S-G4-14 (itemtypen quality_summary en quality_find… |  |  |  |  |
| [ ] | S-G4-37 | Hub-kaarten "Jelly Leon · Afspelen" en "GPU-banen" en het scherm "App… | ai-server-manager | ja (make we… | gewoon | S-G4-32; S-G4-18 (itemtypen device, playback_stats, gpu_lan… |  |  |  |  |
| [ ] | S-G4-38 | Hub-kaart "Intro en aftiteling (Jelly Leon)" | ai-server-manager | ja (make we… | gewoon | S-G4-32; S-G4-17 (itemtypen segment_coverage en segment_rev… |  |  |  |  |
| [ ] | S-G4-35 | Hub: alle Jelly Leon-kaarten samen, kinderschil en afsluitende ontwer… | ai-server-manager | ja (make we… | gewoon | S-G4-33, S-G4-34, S-G4-36, S-G4-37, S-G4-38. De Hub-kaart v… |  |  |  |  |
| [ ] | S-G4-39 | Compat-regressie per oplevering en het clientmatrixdocument (herhaals… | jelly-leon | ja (image-b… | gewoon | de stap waarna de run is gepland; een lokale image van de a… |  |  |  |  |

## Fase P5 (STAPPEN_P5.md; 65 stappen)

De volgorde binnen een baan en wat tegelijk mag staat in "Volgorde en banen" van STAPPEN_P5.md; deze tabel volgt de volgorde van het bestand.

| klaar | stap-ID | titel | baan (repo) | zwaar | moeilijkheid | vooraf (ingekort; de stap is leidend) | commit | CI-run | datum | opmerking |
|---|---|---|---|---|---|---|---|---|---|---|
| [ ] | S-P5-01 | Startcontrole van fase P5 en besluitenronde | ai-server-manager (alleen docs/pl… | nee | gewoon | de fase-afsluiting van P4 (STAPPEN_P4*.md) is door A-GATE g… |  |  |  |  |
| [ ] | S-P5-02 | Contractdelta voor de optionele model-apps | ai-server-manager (contractbron) … | nee | hoog (een… | S-P5-01 met BG-06 en BG-18 genomen. Zonder die besluiten: s… |  |  |  |  |
| [ ] | S-P5-10 | Ingest-raamwerk en bestandenadapter | zoeken-en-persoonlijke-ai | nee | hoog (lee… | S-P5-01. Geen besluit nodig. |  |  |  |  |
| [ ] | S-P5-11 | Adapters voor Immich en logbestanden | zoeken-en-persoonlijke-ai | nee | gewoon | S-P5-10 gepusht. |  |  |  |  |
| [ ] | S-P5-12 | Adapter voor Jellyfin en Jelly Leon, met kinderfilter | zoeken-en-persoonlijke-ai | nee | gewoon | S-P5-10 gepusht. Mag na of vóór S-P5-11 (zelfde baan, dus n… |  |  |  |  |
| [ ] | S-P5-13 | Zoeken afronden: paginering over een momentopname en filters | zoeken-en-persoonlijke-ai | nee | gewoon | S-P5-10 gepusht (er moet echte indexdata zijn om op te test… |  |  |  |  |
| [ ] | S-P5-14 | Optionele embeddingbron en hybride zoeken | zoeken-en-persoonlijke-ai | nee | hoog (adr… | S-P5-13 gepusht; S-P5-02 gedaan; BG-06 staat embeddings toe… |  |  |  |  |
| [ ] | S-P5-15 | Rijbeveiliging in de database met een aparte querierol | zoeken-en-persoonlijke-ai | nee | hoog (mig… | S-P5-10 gepusht. Mag vóór S-P5-14 als de regisseur dat hand… |  |  |  |  |
| [ ] | S-P5-16 | Mediascènes, ondertitels en de herkomst "machinevertaling" | zoeken-en-persoonlijke-ai | nee | gewoon | S-P5-12 gepusht. Het deel spraakherkenning (bouwpunt 5) all… |  |  |  |  |
| [ ] | S-P5-17 | Canonieke itemtekst en gedeelde vectoren voor Jelly Leon | zoeken-en-persoonlijke-ai | nee | gewoon | S-P5-14 gepusht; BG-06 bevestigt dat zoeken-en-persoonlijke… |  |  |  |  |
| [ ] | S-P5-18 | Vraag-en-antwoord met citaten en afweer tegen ingesloten opdrachten | zoeken-en-persoonlijke-ai | nee | hoog (bev… | S-P5-13 gepusht. Voor het genereren van een antwoord: BG-06… |  |  |  |  |
| [ ] | S-P5-19 | Portabiliteit, privacyrapport en herindexeren na herstel | zoeken-en-persoonlijke-ai | nee | gewoon | S-P5-10 gepusht; S-P5-14 als de modelwissel (bouwpunt 4) me… |  |  |  |  |
| [ ] | S-P5-20 | Chat- en spraaksessies met optionele spraakherkenning | zoeken-en-persoonlijke-ai | nee | gewoon | S-P5-01 gedaan. Getypte sessies kunnen direct. Het deel spr… |  |  |  |  |
| [ ] | S-P5-21 | Intentrouter, context en probleemvragen | zoeken-en-persoonlijke-ai | nee | hoog (bev… | S-P5-20 gepusht; gate P2 gehaald (voorstellen lopen via het… |  |  |  |  |
| [ ] | S-P5-22 | Uitspraak van antwoorden (TTS) | zoeken-en-persoonlijke-ai | nee | gewoon | S-P5-20 gepusht; S-P5-02 en BG-06 (de tts-app is in het con… |  |  |  |  |
| [ ] | S-P5-23 | Manifest, OpenAPI, image en rooktest van zoeken-en-persoonlijke-ai | zoeken-en-persoonlijke-ai | ja (image-b… | gewoon | S-P5-10 t/m S-P5-22 gepusht of uitdrukkelijk overgeslagen w… |  |  |  |  |
| [ ] | S-P5-30 | Upstream-API's vaststellen en simulators voor NetAlertX en AdGuard Ho… | home-control-hub | nee | gewoon | S-P5-01 gedaan; werkmap schoon (zie de inleiding van deze b… |  |  |  |  |
| [ ] | S-P5-31 | NetAlertX-ingest: apparaten, adreshistorie en nieuwe-apparaatsignalen | home-control-hub | nee | gewoon | S-P5-30 gepusht. |  |  |  |  |
| [ ] | S-P5-32 | DNS-samenvatting, uitzonderingen als voorstel en fail-safe | home-control-hub | nee | hoog (een… | S-P5-30 gepusht. Voor het voorsteldeel (bouwpunt 4 t/m 6): … |  |  |  |  |
| [ ] | S-P5-33 | Verkeersdiagnose met eerlijke labels | home-control-hub | nee | gewoon | S-P5-32 gepusht. |  |  |  |  |
| [ ] | S-P5-34 | VPN- en tunnelbewaking | home-control-hub | nee | gewoon | S-P5-31 gepusht (zelfde worker-stap). |  |  |  |  |
| [ ] | S-P5-35 | Beveiligingsbevindingen met bewijs en goedkeuringsstroom | home-control-hub | nee | hoog (bev… | S-P5-31 en S-P5-32 gepusht; gate P2 gehaald (voorstellen lo… |  |  |  |  |
| [ ] | S-P5-37 | Connector, events, OpenAPI, image en rooktest van het netwerkdomein | home-control-hub | ja (image-b… | gewoon | S-P5-31 t/m S-P5-35 gepusht of uitdrukkelijk overgeslagen. … |  |  |  |  |
| [ ] | S-P5-50 | Voorspellend onderhoud: API | ai-server-manager | nee | gewoon | S-P5-01 gedaan; S-P5-02 klaar of nog niet gestart (zelfde r… |  |  |  |  |
| [ ] | S-P5-51 | Voorspellend onderhoud: scherm | ai-server-manager | ja (make we… | gewoon | S-P5-50 gepusht. |  |  |  |  |
| [ ] | S-P5-52 | Update- en rollbackcentrum: API | ai-server-manager | nee | hoog (ter… | gate P2 gehaald (voorstel, goedkeuring, executor, pre-updat… |  |  |  |  |
| [ ] | S-P5-53 | Update- en rollbackcentrum: scherm | ai-server-manager | ja (make we… | gewoon | S-P5-52 gepusht. |  |  |  |  |
| [ ] | S-P5-54 | Draagbare export en herstel van de Hub: API | ai-server-manager | nee | hoog (mig… | S-P5-52 gepusht (zelfde repo); de eigen database-export van… |  |  |  |  |
| [ ] | S-P5-55 | Herstelwizard: scherm | ai-server-manager | ja (make we… | gewoon | S-P5-54 gepusht. |  |  |  |  |
| [ ] | S-P5-56 | Scherm Netwerk | ai-server-manager | ja (make we… | gewoon | S-P5-31, S-P5-32, S-P5-34 en S-P5-35 gepusht (wat niet gebo… |  |  |  |  |
| [ ] | S-P5-57 | Scherm Zoeken en antwoordkaart | ai-server-manager | ja (make we… | gewoon | S-P5-13 gepusht; voor de antwoordkaart ook S-P5-18. |  |  |  |  |
| [ ] | S-P5-58 | Schermen Bronnen en rechten, indexstatus en privacy | ai-server-manager | ja (make we… | gewoon | S-P5-10 en S-P5-19 gepusht. |  |  |  |  |
| [ ] | S-P5-59 | Spraak in de chat | ai-server-manager | ja (make we… | gewoon | S-P5-20 en S-P5-22 gepusht; de AI-chat uit P2 bestaat (apps… |  |  |  |  |
| [ ] | S-P5-60 | Fork-dashboard | ai-server-manager | ja (make we… | gewoon | S-P5-71 gepusht. |  |  |  |  |
| [ ] | S-P5-61 | Verwijderen en verhuizen: scherm | ai-server-manager | ja (make we… | gewoon | S-P5-81 gepusht; het scherm Apps met de verwijderstap uit P… |  |  |  |  |
| [ ] | S-P5-62 | Hub-kaart "Nederlandse ondertitels" en events | ai-server-manager | ja (make we… | gewoon | S-P5-107 gepusht; B03-gate JL4 gehaald; de eventtypen voor … |  |  |  |  |
| [ ] | S-P5-63 | Optionele model-apps in catalogus en scherm | ai-server-manager | ja (make we… | gewoon | S-P5-02, S-P5-72 en S-P5-86 gepusht (voor mt: BG-06 en BG-1… |  |  |  |  |
| [ ] | S-P5-64 | Hub: images, rooktest en volledige ontwerpreview | ai-server-manager | ja (image-b… | gewoon | S-P5-50 t/m S-P5-63 gepusht of uitdrukkelijk overgeslagen. … |  |  |  |  |
| [ ] | S-P5-70 | Forkregister en upstream volgen | appstore-en-fork | nee | hoog (mig… | S-P5-01 gedaan (besluit Z-01 bekend of uitdrukkelijk open g… |  |  |  |  |
| [ ] | S-P5-71 | Samenvoegvoorstellen en de poort vóór productie | appstore-en-fork | nee | hoog (bep… | S-P5-70 gepusht. |  |  |  |  |
| [ ] | S-P5-72 | Catalogus- en validatorregels voor optionele model-apps | appstore-en-fork | nee | hoog (val… | S-P5-02 gepusht (contractdelta); BG-06 genomen. Voor mt ook… |  |  |  |  |
| [ ] | S-P5-73 | Image, rooktest en statuspagina van appstore-en-fork | appstore-en-fork | ja (image-b… | gewoon | S-P5-70 t/m S-P5-72 gepusht of uitdrukkelijk overgeslagen. … |  |  |  |  |
| [ ] | S-P5-80 | Verwijderplan zonder dataverlies | jelly-leon-platform | nee | hoog (ver… | gate P2 gehaald (installatie-, update- en terugzetplannen w… |  |  |  |  |
| [ ] | S-P5-81 | Verhuisplan via export | jelly-leon-platform | nee | gewoon | S-P5-80 gepusht. |  |  |  |  |
| [ ] | S-P5-82 | Manifest en controlelijst I11 NetAlertX | jelly-leon-platform | ja (alleen … | gewoon | S-P5-01 gedaan (D03 en D11 bekend of open gelaten). |  |  |  |  |
| [ ] | S-P5-83 | Manifest en controlelijst I12 AdGuard Home | jelly-leon-platform | nee | gewoon | S-P5-01 gedaan (D11 bekend of open gelaten). |  |  |  |  |
| [ ] | S-P5-84 | Controlelijsten I21 (Tailscale en Cloudflared) en I26 (bestaande apps) | jelly-leon-platform | nee | gewoon | S-P5-01 gedaan (D03 bekend of open gelaten). |  |  |  |  |
| [ ] | S-P5-85 | Controlelijsten I14 en I25 en manifestcontrole van zoeken | jelly-leon-platform | nee | gewoon | S-P5-23 gepusht (manifest en image van zoeken-en-persoonlij… |  |  |  |  |
| [ ] | S-P5-86 | Manifesten voor de optionele model-apps | jelly-leon-platform | ja (alleen … | gewoon | S-P5-72 gepusht en de validator-pin van deze repo verzet (m… |  |  |  |  |
| [ ] | S-P5-100 | Imagebewaking en één adrescontrole voor model-apps | jelly-leon | ja (plugin-… | hoog (afw… | fase-afsluiting P4 (kern B03-017 en werker B03-018 aanwezig… |  |  |  |  |
| [ ] | S-P5-101 | Optionele embeddings voor aanbevelingen | jelly-leon | ja (plugin-… | hoog (men… | S-P5-100; S-P5-17 gepusht (canonieke itemtekst en leesroute… |  |  |  |  |
| [ ] | S-P5-102 | Koppeling met de vertaalmotor en bewaring van het geheim | jelly-leon | ja (plugin-… | hoog (geh… | S-P5-100; S-P5-02 (Δ-CONTRACT-MT) en BG-18; de ondertitelto… |  |  |  |  |
| [ ] | S-P5-103 | Image van de vertaalmotor mt | de repo die S-P5-02 in de contrac… | ja (image-b… | hoog (her… | S-P5-02 met BG-06 en BG-18: repo, app_id, image-naam en poo… |  |  |  |  |
| [ ] | S-P5-104 | Vertaalpijplijn in de werker (taaktype subtitle.translate) | jelly-leon | ja (plugin-… | hoog (tek… | S-P5-102; voor de meting ook S-P5-103 (echte motor in een l… |  |  |  |  |
| [ ] | S-P5-105 | Kwaliteitsscore, publicatiedrempel en kalibratie | jelly-leon | ja (image-b… | hoog (sta… | S-P5-104 (bevroren pijplijn). AutoPublish blijft in deze st… |  |  |  |  |
| [ ] | S-P5-106 | Correctieroutes, beoordeling, vertaalgeheugen en woordenlijst | jelly-leon | ja (plugin-… | hoog (gel… | S-P5-105; de publicatietransactie B03-047 (P4, S-G3-08) en … |  |  |  |  |
| [ ] | S-P5-107 | Events, connector-itemtypen en Hub-toegang voor ondertitels | jelly-leon | ja (plugin-… | hoog (wat… | S-P5-106. De outbox, de connector en de Hub-koppeling uit d… |  |  |  |  |
| [ ] | S-P5-108 | Audiotaal- en dialoogcontrole met lokale spraakherkenning (standaard … | jelly-leon | ja (plugin-… | gewoon | S-P5-100; S-P5-02 (Δ-CONTRACT-MODEL) en BG-06; S-P5-20 gepu… |  |  |  |  |
| [ ] | S-P5-109 | Optionele lokale AI voor segmentdetectie (standaard uit) | jelly-leon | ja (plugin-… | gewoon | S-P5-100; S-P5-101 (bron van vectoren) en S-P5-108 (koppeli… |  |  |  |  |
| [ ] | S-P5-111 | Pluginpagina "Ondertitels" voor beheerders (W4) | jelly-leon | ja (plugin-… | gewoon | S-P5-107 (beheerroutes); S-P5-105 (kalibratiestatus); S-P5-… |  |  |  |  |
| [ ] | S-P5-115 | Meetslot JLT-28, web-pin, image en rooktest (sluit de baan jelly-leon… | jelly-leon | ja (image-b… | gewoon | S-P5-100 tot en met S-P5-111 voor zover gebouwd; S-P5-120 e… |  |  |  |  |
| [ ] | S-P5-120 | Dialoog "Ondertitels (Jelly Leon)" op de itempagina (W2) | jelly-leon-web | ja (npm-bui… | gewoon | S-P5-106 gepusht (routes 1 tot en met 5, 8 en 9 bestaan, sa… |  |  |  |  |
| [ ] | S-P5-121 | Correctie-editor in de webfork (W3) | jelly-leon-web | ja (npm-bui… | hoog (bew… | S-P5-120; S-P5-106 gepusht (routes 6, 7 en 10). |  |  |  |  |
| [ ] | S-P5-900 | Bewijs samenvoegen: programmabewijs, Excel en STATUS | ai-server-manager | nee | gewoon | S-P5-01 tot en met S-P5-121 zijn in <WERKMAP>/.lokaal/plan/… |  |  |  |  |
| [ ] | S-P5-910 | Gate P5: onafhankelijke controle | zoeken-en-persoonlijke-ai, home-c… | ja (A-GATE … | zeer hoog | S-P5-900 afgevinkt; er is in geen van de zeven repos een ke… |  |  |  |  |

## Fase P6 (STAPPEN_P6.md; 29 stappen)

De volgorde binnen een baan en wat tegelijk mag staat in "Volgorde en banen" van STAPPEN_P6.md; deze tabel volgt de volgorde van het bestand.

| klaar | stap-ID | titel | baan (repo) | zwaar | moeilijkheid | vooraf (ingekort; de stap is leidend) | commit | CI-run | datum | opmerking |
|---|---|---|---|---|---|---|---|---|---|---|
| [ ] | S-P6-01 | Stand en voorwaarden van P6 vaststellen | geen (alleen lezen in alle 11 rep… | nee | gewoon | fasegate P5 gesloten |  |  |  |  |
| [ ] | S-P6-02 | Release v0.1.0 van de Hub en de executor | ai-server-manager | nee (de ima… | gewoon | S-P6-01; CI groen op de laatste commit; besluit 6 van de ge… |  |  |  |  |
| [ ] | S-P6-03 | Release v0.1.0 van home-control-hub | home-control-hub | nee (de ima… | gewoon | S-P6-01; CI groen; besluit 6 van de gebruiker genomen |  |  |  |  |
| [ ] | S-P6-04 | Release v0.1.0 van appstore-en-fork | appstore-en-fork | nee (de ima… | gewoon | S-P6-01; CI groen; besluit 6 van de gebruiker genomen |  |  |  |  |
| [ ] | S-P6-05 | Release v0.1.0 van jelly-leon-platform en digests in de installatiema… | jelly-leon-platform | nee (de ima… | gewoon | S-P6-01; CI groen; voor bouwpunt 5: S-P6-02 klaar (digests … |  |  |  |  |
| [ ] | S-P6-06 | Release v0.1.0 van zoeken-en-persoonlijke-ai | zoeken-en-persoonlijke-ai | nee (de ima… | gewoon | S-P6-01; CI groen; besluit 6 van de gebruiker genomen |  |  |  |  |
| [ ] | S-P6-10 | Simulators voor de downloadketen (arr, sabnzbd, qbittorrent) | jelly-leon-platform | nee | gewoon | S-P6-05 klaar (baan jelly-leon-platform vrij) |  |  |  |  |
| [ ] | S-P6-11 | Simulators voor huis en energie (gree, homewizard, zigbee) | jelly-leon-platform | nee | gewoon | S-P6-10 klaar |  |  |  |  |
| [ ] | S-P6-12 | Simulators overig (immich, onedrive, credits, stt, upstream-git) | jelly-leon-platform | nee | gewoon | S-P6-11 klaar |  |  |  |  |
| [ ] | S-P6-13 | Integrale omgeving: compose, runner en eerste rookronde | jelly-leon-platform | ja (image-b… | hoog (elf… | S-P6-12 klaar; S-P6-02...06 klaar (de vijf releases bestaan… |  |  |  |  |
| [ ] | S-P6-14 | Scenario's uitval en noodstop (EX01, EX02, EX06, EX07) | jelly-leon-platform | ja (integra… | gewoon | S-P6-13 klaar (runner en compose bestaan); S-P6-10 klaar |  |  |  |  |
| [ ] | S-P6-15 | Scenario's MediaGuard-inhoud (EX03, EX04, EX05, EX09, EX37) | jelly-leon-platform | ja (integra… | gewoon | S-P6-13 klaar; S-P6-10 klaar (simulator arr) |  |  |  |  |
| [ ] | S-P6-16 | Scenario's Media Source Optimizer (EX39, EX40, EX41, EX42) | jelly-leon-platform | ja (integra… | gewoon | S-P6-13 klaar; S-P6-10 klaar (simulators sabnzbd, qbittorre… |  |  |  |  |
| [ ] | S-P6-17 | Scenario's zoeken, spraak en LiveTV (EX36, EX43, EX44, EX49, EX38) | jelly-leon-platform | ja (integra… | gewoon | S-P6-13 klaar; S-P6-12 klaar (simulators immich, stt); voor… |  |  |  |  |
| [ ] | S-P6-18 | Scenario's Hub-veiligheid (EX16...EX21) | jelly-leon-platform | ja (integra… | hoog (bev… | S-P6-13 klaar; S-P6-12 klaar (credits-simulator) |  |  |  |  |
| [ ] | S-P6-19 | Scenario's Node-RED en meldingen buiten de Hub om (EX45, EX46, EX22) | jelly-leon-platform | ja (integra… | gewoon | S-P6-13 klaar |  |  |  |  |
| [ ] | S-P6-20 | Scenario's back-up, levenscyclus en appstore (EX11, EX12, EX14, EX15,… | jelly-leon-platform | ja (integra… | hoog (ter… | S-P6-13 klaar; S-P6-12 klaar (simulators onedrive, upstream… |  |  |  |  |
| [ ] | S-P6-21 | Scenario's huis en energie (EX24...EX30) | jelly-leon-platform | ja (integra… | gewoon | S-P6-13 klaar; S-P6-11 klaar (simulators gree, homewizard, … |  |  |  |  |
| [ ] | S-P6-22 | Netwerkscenario's, de "Echt"-rijen, volledige run en rapport | jelly-leon-platform | ja (volledi… | gewoon | S-P6-14...21 klaar |  |  |  |  |
| [ ] | S-P6-30 | Eindproef terug naar stock en gegevensbescherming (B03-013; JLT-60, J… | jelly-leon | ja (image-b… | hoog (bew… | S-P6-01 klaar; fasegate P5 gesloten (alle B03-modules die h… |  |  |  |  |
| [ ] | S-P6-31 | Releasegate compatibiliteit (B03-019; JLT-63, JLT-64, JLT-66, JLT-67) | jelly-leon | ja (contain… | gewoon | S-P6-30 klaar (image jelly-leon:p6 bestaat: docker image in… |  |  |  |  |
| [ ] | S-P6-32 | Generale repetitie van de Emby-overname met de eindimage (B03-015; JL… | jelly-leon | ja (contain… | hoog (laa… | S-P6-31 klaar (zelfde baan); image jelly-leon:p6 bestaat; h… |  |  |  |  |
| [ ] | S-P6-33 | MediaGuard: contracttest met de Jelly Leon-image en upgradebewijs (B0… | media-guard-ultimate | ja (image-b… | gewoon | S-P6-30 heeft jelly-leon:p6 gebouwd (docker image inspect j… |  |  |  |  |
| [ ] | S-P6-40 | Regressieronde over alle repos op de eindstand (releasegate; JLT-68) | één repo per run; de regisseur st… | ja (de voll… | gewoon | S-P6-22, S-P6-32 en S-P6-33 klaar. In de gekozen repo loopt… |  |  |  |  |
| [ ] | S-P6-50 | NAS-acceptatiedraaiboek voor de gebruiker (document) | ai-server-manager | nee | gewoon | S-P6-02 klaar (de tag en digest van Hub en executor zijn be… |  |  |  |  |
| [ ] | S-P6-51 | Overnamedraaiboek en controlelijst "Emby verwijderen" bijwerken | jelly-leon | nee | gewoon | S-P6-32 klaar (uitkomsten van de generale repetitie); S-P6-… |  |  |  |  |
| [ ] | S-P6-52 | Excel-gereedschap: wat de gebruiker zelf afvinkt blijft staan | ai-server-manager | nee | gewoon | besluit van de gebruiker via een keuzemenu van de regisseur… |  |  |  |  |
| [ ] | S-P6-60 | EVIDENCE-programma en Excel bijwerken na DEEL A | ai-server-manager | nee | gewoon | S-P6-40 voor alle elf repos "groen" in VOORTGANG.md; S-P6-5… |  |  |  |  |
| [ ] | S-P6-70 | Terugmelding van een NAS-onderdeel verwerken (herhaalbaar, één keer p… | de repo waarvan de rijen zijn (éé… | nee | gewoon | de terugmelding van de gebruiker is compleet (elk punt onde… |  |  |  |  |

## NAS-onderdelen van P6 (alleen met de gebruiker op de echte NAS; tot dan NIET GEVALIDEERD)

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
