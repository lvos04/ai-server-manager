# STAPPEN_P4_GOLF3_4 - Fase P4 deel 2: golf 3 en golf 4 van B03 (universele mediaserver)

Dit bestand is een deel van het uitvoeringsplan. Het is geschreven voor de regisseur (hoofdsessie) die zelf niet bouwt
en elke stap uitbesteedt aan een subagent. Een subagent weet alleen wat in zijn opdracht staat: plak daarom bij elke
opdracht het blok "Opdrachtkop" (hoofdstuk 4) boven de stap.

Stand van de verkenning waarop dit bestand steunt: alle ID's van dit deel staan in
`<WERKMAP>/.lokaal/plan/bron/STAND_PER_ID.tsv` op "GEEN BEWIJS (Niet gestart)". Stand van `<WERKMAP>/jelly-leon`
na het afbreken van ronde 3 (2026-11-11, zie `<WERKMAP>/.lokaal/plan/STAND_RONDE3.md`): B03-017 en B03-009
(MediaGuard-viewerclient via de Hub, map `Core/MediaGuard`) zijn gecommit en gepusht maar niet gereviewd; B03-018 en
het IsKid-deel van B03-010 staan als HALF WERK niet-gecommit in de werkmap (nieuwe mappen `Core/Budget`, `Core/Planner`,
`Core/Werker`; let op: de werker heet `Werker`, niet `Worker`). Dat werk hoort bij STAPPEN_P4_GOLF1_2.md. Tel voor "is
het er al?" daarom alleen wat in git staat: `git -C <WERKMAP>/jelly-leon ls-files <pad>` (een map die alleen in de
werkmap staat, is half werk van een andere stap). Daarom heeft elke stap een controle "Al gedaan?".

## 1. Doel

Golf 3 en golf 4 maken de zes functies van Jelly Leon af op de ontwikkelmachine, als modules van de ene plugin
`Jellyfin.Plugin.JellyLeon` (plugins voor patches), met webhaken, clientpatches en Hub-kaarten:

- **Golf 3:** Watch Together compleet behalve chat en Hub (B03-022 t/m B03-027), ondertitelinventaris, -sync en
  -publicatie zonder model (B03-040, 041, 042, 043, 047), kwaliteitscontrole niveau 0/1/1,5/2/3 (B03-050 t/m B03-057),
  cues en families voor segmenten (B03-074) en de spike authenticatie op streamroutes (B03-010).
- **Golf 4:** chat (alleen na BG-12) en Hub voor Watch Together (B03-028, 029), webrij en clientmatrix aanbevelingen
  (B03-036, 037, 039), het P4-deel van B03-049, Hub voor kwaliteit (B03-058), lanewrapper, gedeeld GPU-budget, probe,
  geleerde profielen en bescherming van stock-clients (B03-004/005 aanvullingen, B03-063 t/m B03-069),
  correctie-editor, skipknoppen en koppelingen voor segmenten (B03-075 t/m B03-078) en de afronding van B03-007.
- **Besluit Z-20 (genomen 2026-11-11: "in P4 bouwen; per werkpakket eerst A-VERKEN, dan stappen in een golf"):** de
  zes werkpakketten zonder golf in FASERING#3 worden hier gebouwd, zo ver als de ontwikkelmachine toelaat. Golf 3:
  metadata en anime-mapping (B03-006: S-G3-28, S-G3-29), universele bibliotheek (B03-002: S-G3-30, S-G3-31) en
  beschikbaarheid van clients (B03-003: S-G3-32). Golf 4: scènezoeker (B03-008: S-G4-49, S-G4-50), offline downloaden
  (B03-011: S-G4-51, S-G4-52) en live-tv en DVR (B03-012: S-G4-53, S-G4-54). Echte apparaten, tuners en de NAS:
  STAPPEN_P6.md, N-P6-09.

Niet in dit bestand (fase P5): B03-038, B03-044, B03-045, B03-046, B03-048, de rest van B03-049, B03-059, B03-079.
Niet in dit bestand (fase P6, echte NAS of echte apparaten): de testrijen JLT-06, JLT-15, JLT-26, JLT-39, JLT-49,
JLT-59, JLT-69, JLT-74. Die krijgen hier alleen een bewijsregel "Geblokkeerd" en horen in STAPPEN_P6.md.

Bron: `<WERKMAP>/ai-server-manager/docs/platform-v2/02_BOUWPLANNEN/B03_FASERING.md#3. Golven en werkpakketten`.

## 2. Gates

**Ervoor (allemaal aantoonbaar, anders begint golf 3 niet):**

| Gate | Inhoud in het kort | Bron |
|---|---|---|
| Gate P4-0 | jelly-leon en jelly-leon-web op 12.x; JLT-60 t/m JLT-64, JLT-67, JLT-70 t/m JLT-73 Sim-geslaagd; baselines opnieuw gemeten op de digest van de forkbasis | B03_FASERING.md#Gate P4-0 (vóór elk B03-modulewerk); stap S-P40-95 (STAPPEN_P4_GOLF1_2.md) |
| Gate golf 1 | een plugin met modules bewezen; JLT-68, JLT-64, JLT-65 Sim-geslaagd; foutcatalogus, analyzer, UserDeleted groen; werker met SBOM; planner (pauze binnen 5 s, hooguit 2 threads en 1 GiB batch); JLT-66 Sim-geslaagd of batchmodules blijven op de NAS uit (BG-07) | B03_FASERING.md#Gate golf 1 (vóór elk functiewerk in P4); stap S-G1-90 (STAPPEN_P4_GOLF1_2.md) |
| Gates golf 2 | WT-1-gate (decorator of core-patch, B03-021), G-F2-1 t/m G-F2-5 (B03-031 t/m B03-035), F5-S1 en F5-S3 (B03-061, B03-062), F6-S1 t/m F6-S3 (B03-071, 072, 073; JLT-51 nultolerantie) | B03_FASERING.md#3. Golven en werkpakketten, rij Golf 2; stap S-G2-90 (STAPPEN_P4_GOLF1_2.md), rapport `<WERKMAP>/.lokaal/ketens/GATE-GOLF-2/RAPPORT-A-GATE.md` |
| Contractregel | "Een plugin met modules + belastingtest binnen de manifestresources" voor B03-batch op de NAS; "Hub-sleutelpin in Jelly Leon (JL4)" voor Hub-kaarten van B03 | `<WERKMAP>/ai-server-manager/docs/platform-v2/01_ARCHITECTUUR/06_FASERING_EN_GATES.md#Fase P4 — Universele mediaplatform` |

Golf 3 begint pas als de gate van golf 2 (S-G2-90) gehaald is en de gebruiker daar in het keuzemenu "doorgaan naar
golf 3" koos (STAPPEN_P4_GOLF1_2.md, S-G2-90 bouwpunt 4 en "Stop en vraag als"). Die gate veronderstelt de gates van
P4-0 en golf 1. Ook S-G4-25 en S-G4-31, die al tijdens golf 3 mogen lopen (hoofdstuk 7), starten dus niet eerder.

Let op: Δ-MG-AUTH en Δ-MG-DUAL (eigenaar: media-guard-ultimate) zijn exitcriteria van P4-0. Volgens de vervolgpunten
zijn ze niet opgeleverd. P4 mag dan op de ontwikkelmachine verder met een MediaGuard-simulator, maar er draait geen
B03-batch op de NAS en Jelly Leon toont `mediaguard: onbekend`. Alle MediaGuard-tests in dit bestand zijn dus
"Sim-getest" tegen een simulator; nooit als echte MediaGuard-validatie melden.

**Erna:**

| Gate | Testrijen die Sim-geslaagd moeten zijn | Wie controleert |
|---|---|---|
| Gate golf 3 | JLT-03, JLT-05, JLT-07, JLT-08 (alleen na BG-09; anders Geblokkeerd), JLT-20, JLT-22, JLT-23, JLT-24, JLT-30 t/m JLT-37, JLT-53, JLT-57 | A-GATE op N4 (hoofdstuk 8) |
| Gate golf 4 = einde P4 op de ontwikkelmachine | JLT-09, JLT-14, JLT-38, JLT-41 t/m JLT-48, JLT-54, JLT-55, JLT-56, JLT-58; compat JLT-63 en JLT-64 per oplevering, JLT-65 bij elke module-oplevering | A-GATE op N5 (hoofdstuk 10, einde van de fase) |
| Cutover-gate (P6) | NAS-rijen en echte apparaten; hoort niet in dit bestand | STAPPEN_P6.md |

Per functie gelden daarnaast de subfase-gates uit het bouwplan (Fx.8): WT-2 t/m WT-8, 3A en 3B, QC-0 t/m QC-6,
F5-S2 en F5-S4 t/m F5-S8, F6-S4 t/m F6-S7, G-F2-6, G-F2-7 en G-F2-9. Ze staan bij de stappen.

**No-go voor P4 (de regisseur stopt en meldt dit aan de gebruiker):** upstream-clients breken; HDR/DV-verlies; media
muteren buiten MediaGuard; de afspeelstart van een stock-client weigeren of verlagen; schrijven in kijkgeschiedenis
buiten BG-21 en de eenmalige overname B03-015; Emby uitzetten voor de controlelijst; B03-batch op de A310 terwijl
MediaGuard encodeert; een winstclaim zonder baseline of met een niet-bevroren testset.

**Regel "aantoonbaar beter":** een functie mag dat pas claimen als haar Fx.1-drempels tegen stock-best gehaald zijn op
dezelfde 12.x-digest, met n en Wilson-interval (anders heet het een smoke-gate), terwijl JLT-63, JLT-64 en JLT-65 geen
regressie tonen. Bron: B03_FASERING.md#Gates per functie.

## 3. Besluiten die eerst genomen moeten zijn

Alleen de regisseur vraagt de gebruiker, via een keuzemenu. Een subagent die een besluit mist, stopt en meldt het.
Bij verschil tussen deze tabel en `<WERKMAP>/.lokaal/plan/uit/BESLUITEN_EN_BLOKKADES.md` (koppen "#### BG-nn", regel
"Zonder besluit geldt") gaat BESLUITEN_EN_BLOKKADES.md voor; de stap stopt en meldt het verschil.
Bron: `<WERKMAP>/ai-server-manager/docs/platform-v2/02_BOUWPLANNEN/B03_BESLUITEN.md#Overzicht`. De kolom "Zonder
besluit" is de veiligste stand; daarmee mag een stap doorgaan als dat er staat.

| Besluit | Gaat over | Nodig voor stap | Zonder besluit |
|---|---|---|---|
| BG-05 | Mag de Hub MediaGuard laten herstellen of zoeken | S-G3-07, S-G3-15 (voor golf 3); S-G4-04, S-G4-14, S-G4-36 | alleen deeplinks `handmatig_in_mediaguard`; route "eerst menselijk zoeken" en QC-H blijven Geblokkeerd (contract) |
| BG-04 | Waar staat de MediaGuard-sleutel (genomen: via de Hub) | S-G3-07, S-G3-15, S-G4-04, S-G4-17 | n.v.t. (genomen); zie "Spanning BG-04" hieronder |
| BG-09 | Watch Together met mensen buiten huis | S-G3-23; S-G4-44 (tabblad "Externe deelnemers") | `ExternalMode=uit`; B03-027 en JLT-08 Geblokkeerd |
| BG-10 | Watch Together op Android TV en Swiftfin | S-G3-20, S-G3-21, S-G3-26 | STOP: geen clientpatch, en de stappen voor B03-026 (S-G3-20, S-G3-21) starten pas na het besluit; S-G3-26 alleen bij de keuze "clientpatch" |
| BG-11 | Wie ziet een nieuwe kijkgroep | S-G3-17 (en daardoor S-G3-18 t/m S-G3-23) | STOP: S-G3-17 start niet (privacykeuze; geen optie is "niets doen"). Met het besluit wordt de gekozen stand de standaard |
| BG-13 | Haperende deelnemer en volle GPU's | S-G3-19, S-G4-09, S-G4-43 | standaardgedrag van Jellyfin (wachten tot 30 s) is de standaard; `doorgaan_na_wachttijd` mag gebouwd en getest worden maar is niet de standaard; bij volle GPU's alleen waarschuwen |
| BG-14 | Watch Together-knoppen in de oude weergave | S-G3-24 | alleen Modern |
| BG-19 | Opslag, naam en levensduur van machinevertalingen; WP B03-047 noemt het ook als afhankelijkheid voor de publicatie | S-G3-08 (werkt door in S-G4-13) | STOP: S-G3-08 stopt en meldt BG-19; opslag naast de media wordt nooit zonder besluit gebouwd |
| BG-21 | Onthouden spoorkeuzes bij een nieuw spoor | S-G3-08 (werkt door in S-G4-13) | `hold` (niets schrijven) |
| BG-23 | Volledige decodecontrole voor de hele bibliotheek | S-G3-11, S-G3-12 | alleen de steekproef (niveau 1,5) voor de bibliotheek; geen volledige controle van de hele bibliotheek. De volledige decode alleen voor nieuw of door MediaGuard vervangen en op verzoek (standaard van WP B03-052) |
| BG-24 | Bewijs-miniaturen, label, "Meld een probleem", home video's | S-G3-11, S-G3-14, S-G3-16, S-G3-25 | miniaturen uit (Q5b geeft 501); label uit; melden uit; bibliotheken home video's en gemengde inhoud niet scannen |
| BG-25 | Gecorrigeerde ondertitelkopie bij slechte sync | S-G3-13 | alleen melden: geen gecorrigeerde kopie, ook niet op verzoek |
| BG-03 | Wat is een kinderprofiel (hoort voor golf 1) | S-G3-18 | STOP als `IsKid(user)` in de code nog geen vastgelegde definitie heeft |
| BG-08 | Swiftfin | S-G4-27, S-G4-28 (voor golf 4) | geen eigen patches |
| BG-12 | Chat en reacties | S-G4-10, S-G4-24; S-G4-44 (tabblad "Chat en reacties") | uit; B03-028 wordt niet gebouwd: S-G4-10 en S-G4-24 vervallen, B03-028 staat op "Geblokkeerd (besluit BG-12)" |
| BG-15 | Rij "Aanbevolen voor jou" | S-G4-20, S-G4-45, S-G4-29 | STOP: zonder besluit geen webhaak H-HOME |
| BG-26 | Afspeelprofiel aanpassen voor officiele apps en stock-tv-apps | S-G4-06, S-G4-07, S-G4-41, S-G4-42 | alleen opt-in per apparaat, alleen beperkend |
| BG-28 | Volle of uitgevallen GPU's | S-G4-03, S-G4-04, S-G4-08 | standaardgedrag van upstream; nooit weigeren |
| BG-29 | Kwaliteitslabel en feedbackvraag | S-G4-08, S-G4-22 | geen label en geen feedbackvraag: de server bewaart de reden wel, de webclient toont label en feedbackvraag niet |
| BG-30 | Android TV-patch capabilityrapport | S-G4-26 (en het Android TV-deel van S-G4-30) | STOP: zonder besluit geen clientpatch |
| BG-31 | Skipknoppen: tekst en standaardgedrag | S-G4-16, S-G4-23, S-G4-27, S-G4-28 | de upstream-teksten (geen haak, geen clientpatch), overal vragen, nooit automatisch overslaan: S-G4-23, S-G4-27 en S-G4-28 starten niet; S-G4-16 wel |
| BG-33 | Wie mag tijdcodes corrigeren (hoort bij golf 2) | S-G4-15, S-G4-46 | alleen beheerders corrigeren; nieuwe segmenten blijven in schaduwmodus |
| BG-07 | Resources van de jelly-leon-app (hoort na golf 1) | S-G3-02 | bouwen mag; batch op de NAS blijft uit tot het gemeten budget er is |
| BG-34 | Wie labelt de echte afleveringen (genomen: de gebruiker of een aangewezen persoon) | S-G3-22, S-G4-40 | alleen de synthetische testset telt; het deel met echte afleveringen blijft Geblokkeerd |
| BG-36 | Module uit: eigen segmenten wissen of verbergen (hoort bij golf 2) | S-G4-16 | STOP als de code van golf 2 dit gedrag nog niet heeft vastgelegd; S-G4-16 kiest het niet zelf |
| BG-37 | Testdata met een beperkende licentie (genomen) | S-G4-12, S-G4-34 | testdata met een beperkende licentie alleen lokaal, nooit in een repo of image; evaluatie op echte kijkgeschiedenis is JLT-15 en hoort in STAPPEN_P6.md |
| BG-17 | Online metadata (TMDb/OMDb); moment "bij B03-006" | S-G3-28 (de regisseur legt het voor vóór die stap) | aan laten (standaardgedrag van Jellyfin); S-G3-28 verandert niets aan de online metadata-instellingen |
| BG-06 | Optionele lokale modellen (embeddings, spraakherkenning); hoort bij P5 | S-G4-49 | geen tweede producent: in P4 geen spraakherkenning en geen embeddings; de scènezoeker zoekt alleen in tekst van bestaande ondertitelsporen |
| Z-19 | "Module uit": 404 of 501 (genomen 2026-11-11) | elke route van een module in golf 3 en golf 4; gatecontrole golf 4 | n.v.t. (genomen): 404 zoals jelly-leon ADR-0030; de afwijking van WP-JSON (B03-033 en B03-035 vragen 501) staat letterlijk in het bewijs van die twee ID's (golf 2). Niet aangemeld blijft 401. 501 `capability_unavailable` blijft alleen waar een functie BINNEN een aangezette module uit staat (bv. chat bij BG-12, miniaturen bij BG-24) en voor `propose`/`apply`/`rollback` van de connector |
| Z-20 | Zes B03-werkpakketten zonder golf (genomen 2026-11-11) | S-G3-28 t/m S-G3-32; S-G4-49 t/m S-G4-54 | n.v.t. (genomen): in P4 bouwen, per werkpakket eerst A-VERKEN, dan stappen in een golf; vastleggen in FASERING en WP-JSON is een documentatiestap in ai-server-manager (BESLUITEN_EN_BLOKKADES.md 0.3), niet in dit bestand |

**Spanning BG-04 (melden, niet zelf oplossen):** BG-04 is genomen: de MediaGuard-sleutel van Jelly Leon loopt via de
Hub (Hub-vault; bij voorkeur zonder sleuteloverdracht, Jelly Leon vraagt de MediaGuard-gegevens via de Hub met een
dienst-JWT). Zie `<WERKMAP>/.lokaal/plan/uit/BESLUITEN_EN_BLOKKADES.md#1.2 Besluiten uit de keuzemenu's`. De
overzichtstabel in B03_BESLUITEN.md toont BG-04 nog als open met advies "in Jelly Leon zelf", en de werkpakketteksten
B03-043, B03-056 en B03-064 spreken van een sleutel in de geheimenmap van Jelly Leon. Het besluit gaat voor. Op
2026-11-11 staat in jelly-leon commit `cc3e82b4d` ("B03-009: MediaGuard-viewerclient via de Hub, zonder sleutel in
Jelly Leon") met `docs/adr/ADR-0034-b03-009-mediaguard-viewerclient-via-de-hub.md`; die is nog niet gereviewd (STAND_RONDE3.md).
A-VERKEN stelt bij de eerste MediaGuard-stap vast wat de code van golf 1 (B03-009, viewerclient) na de review doet; bouwt
die toch op een sleutel in Jelly Leon zelf, dan stopt de stap en vraagt de regisseur de gebruiker. Geen enkele stap in dit bestand voegt een
sleutelveld voor MediaGuard toe aan een beheerpagina.

## 4. Opdrachtkop (de regisseur plakt dit blok boven elke stap in de opdracht)

```
VASTE REGELS
- Taal: Nederlands. Je stelt geen vragen aan de gebruiker; heb je een besluit nodig, stop dan en meld het.
- Je start zelf geen subagents. Je werkt alleen in de repo die bij "Repo" staat. Raak ai-factory nooit aan.
- Git: altijd "git pull --rebase" voor elke push; nooit force-push; Nederlandse commitberichten; geen pull requests.
  Elke commit eindigt met de regel: Co-Authored-By: Claude <noreply@anthropic.com>
  Voeg bestanden bij naam toe, nooit "git add -A" (er kan een build lopen die tijdelijke bestanden schrijft).
- Geen geheimen, geen IP-adressen, geen NAS-gegevens en geen modelnaam of model-ID in code, docs of commits.
- HARDE EIS: kijkgeschiedenis (gezien, hervatpunten, favorieten, beoordelingen, spoorkeuzes, gebruikers) en de
  voortgang van MediaGuard blijven altijd beschikbaar; Emby blijft werken en wordt nooit onderbroken.
- Installatie is altijd een standaard TrueNAS Custom App (een alles-in-een image per repo); nooit YAML of compose.
- Bewijs: schrijf nooit "Gereed" of "Geslaagd". Gebouwd en met simulator getest = status "Bezig" (validatie
  Sim-getest of Sim-geslaagd). Alles wat een echte NAS, hardware of accounts vraagt = status "Geblokkeerd" met de
  letterlijke tekst "NIET GEVALIDEERD (...)" en wat er nog nodig is.
- Zware commando's (image-build, Gradle, emulator, container met een echte Jellyfin- of Emby-server, tijdmeting)
  alleen achter het lock dat in de stap staat. Nooit "docker system prune -a", "docker builder prune -a" of
  "docker volume prune". Gebruik "nice -n 10". Volgorde bij twee locks: eerst stack.lock, dan gradle.lock.

AFKORTINGEN
- BOUWPLAN  = <WERKMAP>/ai-server-manager/docs/platform-v2/02_BOUWPLANNEN/B03_UNIVERSELE_MEDIASERVER.md
- FASERING  = <WERKMAP>/ai-server-manager/docs/platform-v2/02_BOUWPLANNEN/B03_FASERING.md
- BESLUITEN = <WERKMAP>/ai-server-manager/docs/platform-v2/02_BOUWPLANNEN/B03_BESLUITEN.md
- WP-JSON   = <WERKMAP>/ai-server-manager/docs/platform-v2/08_EXCEL/b03/werkpakketten.json
              (lijst van objecten; zoek het object met "ID"; lees Taak, Uitvoering, Acceptatie, Afhankelijkheid)
- TEST-JSON = <WERKMAP>/ai-server-manager/docs/platform-v2/08_EXCEL/b03/testen.json
              (lijst van rijen [ID, titel, opzet, verwacht])
- TASKS-JSON= <WERKMAP>/ai-server-manager/docs/platform-v2/08_EXCEL/tasks.json
              (lijst van objecten; zoek het object met "ID"; lees Taak, Uitvoering, Acceptatie, Afhankelijkheid).
              Voor B03-002, B03-003, B03-006, B03-008, B03-011 en B03-012 bestaat GEEN object in WP-JSON; daar
              zijn TASKS-JSON en BOUWPLAN#4. Bouwfasen (verplichte volgorde) (kop "#### B03-0nn — ...") de bron.
- E2E-JSON  = <WERKMAP>/ai-server-manager/docs/platform-v2/08_EXCEL/e2e_cases.json
              (lijst van rijen [ID, titel, opzet, verwacht]; de EX-rijen)
- PLUGIN    = <WERKMAP>/jelly-leon/plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon
- PLUGINTEST= <WERKMAP>/jelly-leon/plugins/JellyLeon/tests/Jellyfin.Plugin.JellyLeon.Tests
- EVIDENCE  = <WERKMAP>/<repo>/docs/platform-v2/EVIDENCE.json (lijst van objecten met "id") en EXCEL_TAKEN.json
- Koppen in "Lees eerst" en "Bron" worden met hun begin aangehaald (bijvoorbeeld "#F4.5 API-contracten").

TESTCOMMANDO'S (uit de werkstromen en Makefiles van de repos overgenomen; draai ze vanuit de repo-map)
- T-JL-PLUGIN   : <WERKMAP>/.lokaal/jl-dotnet.sh build plugins/JellyLeon.Plugins.sln -c Release
                  <WERKMAP>/.lokaal/jl-dotnet.sh test plugins/JellyLeon.Plugins.sln -c Release --no-build --verbosity minimal
                  (een testklasse: voeg --filter "FullyQualifiedName~<Naam>" toe; de container gebruikt tot 5 GiB:
                  zet er daarom altijd "flock <WERKMAP>/.lokaal/docker-build.lock" voor)
- T-JL-REGISTER : python tools/jelly-leon/check_fork_consistency.py
                  python tools/jelly-leon/patch_register_check.py
                  python tools/jelly-leon/upstream_gedrag_check.py --overzicht
- T-JL-TOOLS    : python -m pytest -q tools/jelly-leon/tests
- T-JL-HARNAS   : PYTHONPATH=tools/b03-harnas python -m pytest -q tools/b03-harnas/tests
- T-JL-IMAGE    : flock <WERKMAP>/.lokaal/docker-build.lock docker buildx build -f deploy/allinone/Dockerfile \
                    --build-context jelly-leon-web=<map-met-export-van-jelly-leon-web> \
                    --build-arg FORK_VERSION=<forkversie> --build-arg VCS_REF=<commit> \
                    --build-arg WEB_REF=<commit-jelly-leon-web> --build-arg BUILD_JOBS=4 --load -t <lokale-tag> .
                  python3 tools/jelly-leon/e2e/image_lifecycle.py --image <lokale-tag> --expected-version <versie> \
                    --werkmap <tijdelijke-map> --report <rapport.json>
                  PYTHONPATH=tools/b03-harnas python3 -m b03h guard --image <lokale-tag>
                  (<forkversie> en <versie> staan in tools/jelly-leon/baseline.json: fork_version, upstream_version)
- T-JL-COMPAT   : python3 tools/jelly-leon/e2e/compat_api.py --image <lokale-tag> --stock-image <stock-12.x-image> \
                    --werkmap <tijdelijke-map> --report <rapport.json>
                  python3 tools/jelly-leon/e2e/upstream_gedrag_runtime.py --image <lokale-tag> \
                    --werkmap <tijdelijke-map> --rapport <rapport.json>
                  PYTHONPATH=tools/b03-harnas python -m b03h diffrun --uit <rapport.json>
                  PYTHONPATH=tools/b03-harnas python -m b03h diffrun --negatieve-proef --uit <rapport.json>
                  (alles achter: flock <WERKMAP>/.lokaal/stack.lock ...)
- T-JLW-STATISCH: python tools/jelly-leon-web/check_fork_consistency.py
                  python tools/jelly-leon-web/patch_register_check.py
                  python tools/jelly-leon-web/upstream_gedrag_check.py --overzicht
                  python -m pytest -q -c tools/jelly-leon-web/pytest.ini tools/jelly-leon-web/tests
- T-JLW-NPM     : npm run lint ; npm run stylelint ; npm run build:check ; npm run test ;
                  npm run build:production ; npm run escheck   (een npm-build tegelijk op de machine)
- T-JLW-E2E     : python tools/jelly-leon-web/e2e/web_smoke.py --modus fork --dist dist --image <server-image> \
                    --layouts modern,legacy --uitvoer <map>
                  python tools/jelly-leon-web/e2e/web_smoke.py --modus stock --image <server-image> \
                    --layouts modern,legacy --uitvoer <map>      (achter stack.lock)
- T-JLC-STATISCH: make test ; make check ; make lint
- T-JLC-BOUW    : make androidtv-bouw | make android-bouw | make desktop-bouw
                  (Gradle achter gradle.lock: geef GRADLE_LOCK=<WERKMAP>/.lokaal/gradle.lock en
                  DOCKER_LOCK=<WERKMAP>/.lokaal/docker-build.lock mee aan make)
- T-JLC-COMPAT  : make compat-android JL_IMAGE=<jelly-leon-image>
                  make compat-desktop JL_IMAGE=<jelly-leon-image> DESKTOP_BUILD=<map>
                  python3 tools/clients/client_compat.py hervatproef   (opties: eerst --help lezen)
- T-HUB-WEB     : make web-lint ; make web-test ; make web-build ; make web-e2e ; make web-review
- T-HUB-API     : make test-unit ; make test-integration ; make openapi-check
```

Niet vastgesteld en daarom door A-VERKEN eerst op te zoeken:

- De lokale Python-omgeving voor `tools/jelly-leon` en `tools/b03-harnas`: tijdens de verkenning bestond
  `<WERKMAP>/jelly-leon/tools/jelly-leon/.venv` (controle: `ls <WERKMAP>/jelly-leon/tools/jelly-leon/.venv/bin/pytest`).
  Aanmaken en gebruiken: zie `<WERKMAP>/.lokaal/plan/uit/POORTEN.md`, blok "P-jelly-leon", kop "2. Omgeving". Waar in
  de testcommando's hierboven `python` staat, is dat de Python uit die omgeving.
- De naam van de stock-12.x-image (`<stock-12.x-image>`): staat als `STOCK_IMAGE` in
  `<WERKMAP>/jelly-leon/.github/workflows/jelly-leon-ci.yml`; uitlezen met:
  `grep -n "STOCK_IMAGE:" <WERKMAP>/jelly-leon/.github/workflows/jelly-leon-ci.yml`.
- De plek van de analysewerker, de planner en de MediaGuard-viewerclient van golf 1: vaststellen met
  `git -C <WERKMAP>/jelly-leon ls-files plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Core/Werker plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Core/Planner plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Core/Budget plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Core/MediaGuard`
  (op 2026-11-11: `Core/MediaGuard` gecommit met `MediaGuardClient.cs`, `MediaGuardPoller.cs`,
  `MediaGuardWitteLijst.cs` en `IMediaGuardVervoer.cs`; `Core/Werker`, `Core/Planner` en `Core/Budget` alleen als
  niet-gecommit half werk in de werkmap = golf 1 nog niet klaar). Geeft `ls-files` voor een van die mappen niets, dan
  stopt elke stap die erop bouwt.
- De MediaGuard-simulator voor plugintests: gezien is alleen
  `<WERKMAP>/jelly-leon/tools/emby-overname/e2e/mediaguard_sim.py`; of golf 1 een eigen simulator levert: ONBEKEND -
  eerst vaststellen met: `grep -rli "mediaguard" <WERKMAP>/jelly-leon/plugins/JellyLeon/tests <WERKMAP>/jelly-leon/tools --include=*.cs --include=*.py`.
- De poorten per repo (P-jelly-leon, P-jelly-leon-web, P-jelly-leon-clients, P-ai-server-manager) en de algemene
  poorten (P-GIT, P-CONTRACT, P-VEILIG, P-EERLIJK, P-PEIL, P-HARDE-EIS, P-INSTALLATIE, P-EXCEL) staan in
  `<WERKMAP>/.lokaal/plan/uit/POORTEN.md`. Ontbreekt daar een blok voor een repo, dan gelden de testcommando's uit de
  Opdrachtkop als poort. De valkuilen V-nnn staan in `<WERKMAP>/.lokaal/plan/uit/VALKUILEN.md`.

## 5. Ketens en niveaus in dit bestand

- **Standaardketen:** A-VERKEN (N2) -> A-BOUW (N3) -> R-TECH (N3) -> A-HERSTEL (N3, alleen bij bevindingen) ->
  R-EERLIJK (N3). Staat bij een stap "Niveau: standaard", dan gelden precies deze niveaus.
- **VERPLICHT erbij** (mag niet worden overgeslagen) waar de stap dat zegt: R-VEILIG (N4) bij authenticatie, rechten,
  geheimen, MediaGuard-sleutel, sockets en netwerkklassen; R-HARDE-EIS (N4) bij migraties en alles wat
  kijkgeschiedenis, gebruikers, spoorkeuzes of MediaGuard raakt; R-MANIFEST (N3) bij wijzigingen aan de image of het
  installatiemanifest; A-ONTWERP (N3) voor en R-ONTWERP (N3) na elke Hub-kaart in ai-server-manager.
- **Jelly Leon-web, de pluginpagina's en de clients vallen buiten Peil:** daar geen A-ONTWERP en geen R-ONTWERP; de
  vormgeving volgt upstream Jellyfin.
- **Topmodel (N5)** staat in dit bestand op drie plaatsen: R-VEILIG van S-G3-10 (authenticatie op streamroutes zelf),
  R-HARDE-EIS van S-G3-08 alleen als BG-21 `reset` of `remap` toestaat en die schrijvende code wordt gebouwd, en A-GATE
  aan het einde van de fase (S-G4-95 in hoofdstuk 10). De gate van golf 3 (S-G3-90) is het einde van een golf en loopt
  op N4. Daarnaast alleen als escalatie: na twee keer vastlopen op N3/N4 een
  enkele poging A-HERSTEL op N5. Elke N5-inzet komt in VOORTGANG.md, tabel "Topmodel-inzet".
- **Vangnet geheugen:** voor een extra keten met "Zwaar: ja" draait de regisseur `free -m`; bij minder dan 3000 MB
  beschikbaar start hij alleen stappen met "Zwaar: nee" of wacht hij. Reviewers en herstellers van lopende ketens
  gaan voor nieuwe ketens.
- **Bij uitval van een subagent:** eerst `git -C <WERKMAP>/<repo> status --short` en
  `git -C <WERKMAP>/<repo> log --oneline @{u}..` (niet-gepushte commits) bekijken, dan pas opnieuw uitzetten.

## 6. Volgorde en banen

Een baan is een repo: nooit twee schrijvende agents in dezelfde repo. Binnen een baan lopen de stappen in de volgorde
van de tabel. Banen lopen naast elkaar.

### 6.1 Golf 3

Elke stap van golf 3 wacht op S-G2-90 (gate golf 2, STAPPEN_P4_GOLF1_2.md; hoofdstuk 2). "Vooraf" hieronder noemt
daarnaast wat een stap binnen golf 3 nodig heeft.

| Stap | Baan (repo) | Vooraf | Zwaar | Kan tegelijk met |
|---|---|---|---|---|
| S-G3-01 Quality fundament (B03-050) | jelly-leon | S-G2-90 (gate golf 2) | nee | S-G3-24 zodra S-G3-04 klaar is; alle andere banen |
| S-G3-02 Jobtypes quality in planner (B03-053) | jelly-leon | S-G3-01; B03-018 | nee | andere banen |
| S-G3-03 Subtitles fundament en inventaris (B03-040) | jelly-leon | S-G2-90 (gate golf 2) | nee | andere banen |
| S-G3-04 Telemetrieroute Watch Together (B03-024 serverdeel) | jelly-leon | S-G2-90 met de WT-1-gate (B03-021) | nee | andere banen |
| S-G3-28 Metadata en anime-mapping, serverdeel (B03-006; besluit Z-20) | jelly-leon | S-G2-90 (gate golf 2); BG-17 voorgelegd (zonder besluit: aan laten) | nee | andere banen |
| S-G3-29 Pluginpagina "Metadata-suggesties" (B03-006 schermdeel) | jelly-leon | S-G3-28 | ja (image, browsertest achter stack.lock) | banen zonder stack.lock |
| S-G3-30 Universele bibliotheek: anime apart, serverdeel (B03-002; besluit Z-20) | jelly-leon | S-G3-28 | nee | andere banen |
| S-G3-05 Ondertiteltoolkit in de werker (B03-041) | jelly-leon | S-G3-03; B03-018 | ja (image) | banen zonder image-build |
| S-G3-06 Ondertitelsync (B03-042) | jelly-leon | S-G3-05 | ja (image, meting) | banen zonder image-build |
| S-G3-07 Beslisregels en MediaGuard-leesroutes (B03-043) | jelly-leon | S-G3-03; B03-009; BG-05 | nee | andere banen |
| S-G3-08 Publicatie en spoorkeuzes (B03-047) | jelly-leon | S-G3-06; BG-19; BG-21 | ja (differentiele run) | banen zonder stack.lock |
| S-G3-09 Streamroutes: meting en ADR (B03-010) | jelly-leon | S-G2-90 (gate golf 2) | ja (server + clients) | banen zonder stack.lock |
| S-G3-10 Streamroutes: authenticatiefilter (B03-010) | jelly-leon | S-G3-09 | ja (clienttest) | banen zonder stack.lock |
| S-G3-11 Quality niveau 0/1/1,5 (B03-051) | jelly-leon | S-G3-02; BG-23 | nee | andere banen |
| S-G3-12 Quality niveau 2 (B03-052) | jelly-leon | S-G3-11 | ja (meting in image) | banen zonder stack.lock |
| S-G3-13 Quality niveau 3 taal en sync (B03-054) | jelly-leon | S-G3-12; S-G3-06; BG-25 | nee | andere banen |
| S-G3-14 Bewijs, verificatie, feedback (B03-055) | jelly-leon | S-G3-13; BG-24 | nee | andere banen |
| S-G3-15 Quality en MediaGuard (B03-056) | jelly-leon | S-G3-14; B03-009; BG-05 | nee | andere banen |
| S-G3-16 Pluginpagina Mediakwaliteit (B03-057 serverdeel) | jelly-leon | S-G3-15 | ja (image, browsertest) | banen zonder stack.lock |
| S-G3-17 Zichtbaarheid en uitnodigingen (B03-022) | jelly-leon | S-G2-90 met de WT-1-gate; BG-11 | nee | andere banen |
| S-G3-18 Kinderregels Watch Together (B03-023) | jelly-leon | S-G3-17; BG-03 | nee | andere banen |
| S-G3-19 Haperbeleid (B03-025 deel beleid) | jelly-leon | S-G3-17; B03-018; BG-13 | ja (hapermeting achter stack.lock) | banen zonder stack.lock |
| S-G3-20 Volgmodus server (B03-026) | jelly-leon | S-G3-17; S-G3-32 (WP-JSON B03-026 noemt B03-003 als afhankelijkheid); BG-10 | nee | andere banen |
| S-G3-21 Volgmodus in de Android TV-emulator (JLT-07) | jelly-leon | S-G3-20 | ja (emulator) | geen andere emulator- of Gradle-stap |
| S-G3-22 Cues, hoofdstuksignalen en families (B03-074) | jelly-leon | S-G2-90 (B03-071, B03-072); cue-extractie uit de bestandspas S-G1-34 | nee | andere banen |
| S-G3-23 Extern via VPN (B03-027) | jelly-leon | BG-09; S-G3-17; voor gasten S-G3-10 | ja (netwerkproef) | banen zonder stack.lock |
| S-G3-24 Webplugin Watch Together (B03-024 webdeel) | jelly-leon-web | S-G3-04; haakmodule B03-017; BG-14 | ja (npm-build, e2e) | jelly-leon-stappen zonder stack.lock |
| S-G3-25 Kwaliteitslabel op de itempagina (B03-057 webdeel) | jelly-leon-web | S-G3-14; S-G3-24 klaar; BG-24 | ja (npm-build, e2e) | jelly-leon-stappen zonder stack.lock |
| S-G3-31 Universele bibliotheek, webdeel (B03-002; alleen als het dossier van S-G3-30 een webdeel noemt) | jelly-leon-web | S-G3-30; haakmodule B03-017 | ja (npm-build, e2e) | jelly-leon-stappen zonder stack.lock |
| S-G3-32 Beschikbaarheid van clients: gaten op de ontwikkelmachine (B03-003; besluit Z-20) | jelly-leon-clients | S-G2-90 (gate golf 2) | ja (Gradle, emulator) | geen andere emulator- of Gradle-stap |
| S-G3-26 Native SyncPlay Android TV (alleen na BG-10 "clientpatch") | jelly-leon-clients | BG-10; S-G3-20 | ja (Gradle, emulator) | geen andere emulator- of Gradle-stap |
| S-G3-27 Compat-regressie per module-oplevering (herhaalstap) | jelly-leon | na S-G3-08, S-G3-16, S-G3-22, S-G3-30 en S-G3-23 (of S-G3-20 als BG-09 "uit" is) | ja (stack.lock) | niets met stack.lock |
| S-G3-90 Gatecontrole golf 3 (A-GATE, alleen lezen) | geen (leest jelly-leon en jelly-leon-web; jelly-leon-clients als S-G3-26 liep) | alle stappen van golf 3 die niet door een besluit of door hun dossier (S-G3-31) zijn vervallen, en de vijf runs van S-G3-27 | nee | S-G4-25 en S-G4-31 (andere repos); in jelly-leon en jelly-leon-web wordt tijdens de gate niet geschreven |

### 6.2 Golf 4

De rijen staan in de volgorde waarin de stappen in hoofdstuk 9 staan. De nummers S-G4-40 tot en met S-G4-46 zijn later
toegevoegd, S-G4-47 en S-G4-48 bij de controle van 2026-11-11, S-G4-49 tot en met S-G4-54 na besluit Z-20
(2026-11-11); ze staan in deze tabel en in hoofdstuk 9 op hun plaats in de volgorde en niet op nummer.

| Stap | Baan (repo) | Vooraf | Zwaar | Kan tegelijk met |
|---|---|---|---|---|
| S-G4-01 Spike lanewrapper en ADR (B03-063) | jelly-leon | Gate golf 3; B03-062 | ja (tijdmeting achter stack.lock) | banen zonder stack.lock |
| S-G4-02 Lanewrapper bouwen (B03-063) | jelly-leon | S-G4-01 | nee | andere banen |
| S-G4-03 Wrapper in de image en laneplanner (B03-063, B03-004) | jelly-leon | S-G4-02; BG-28 | ja (image, meting) | banen zonder image-build |
| S-G4-04 Gedeeld GPU-budget (B03-064, B03-004) | jelly-leon | S-G4-03; B03-009; BG-04; BG-05 | nee (contracttest achter stack.lock) | andere banen |
| S-G4-05 Probe-, advies- en uitkomstroutes (B03-065 serverdeel, B03-005) | jelly-leon | B03-061 (golf 2) | nee | andere banen |
| S-G4-06 Geleerde profielen (B03-066) | jelly-leon | S-G4-05; BG-26 | nee | andere banen |
| S-G4-07 Bescherming stock-clients en MediaGuard-afspeeltest (B03-068) | jelly-leon | S-G4-06; BG-26 | ja (compat achter stack.lock) | banen zonder stack.lock |
| S-G4-08 HDR/DV/audio/ondertitelregels en "Waarom?" (B03-067, B03-005) | jelly-leon | S-G4-06; BG-28; BG-29 | nee | andere banen |
| S-G4-09 Capaciteitsadvies Watch Together (B03-025 rest) | jelly-leon | S-G4-04; S-G3-19; BG-13 | ja (voorspellingsproef achter stack.lock) | banen zonder stack.lock |
| S-G4-10 Chat en reacties serverdeel (B03-028) | jelly-leon | BG-12; S-G3-18 | nee | andere banen |
| S-G4-11 Connector en events Watch Together (B03-029 serverdeel) | jelly-leon | S-G3-17 t/m S-G3-20 | nee | andere banen |
| S-G4-12 Aanbevelingen: prestatie, register en connector (B03-039 serverdeel) | jelly-leon | B03-035 (golf 2) | ja (meetslot) | niets met stack.lock |
| S-G4-13 Ondertitels: gesynchroniseerde kopie als gemarkeerd spoor (B03-049 P4-deel) | jelly-leon | S-G3-08 | nee | andere banen |
| S-G4-14 Quality: connector en bewijsroute (B03-058 serverdeel) | jelly-leon | S-G3-15 | nee | andere banen |
| S-G4-15 Segmenten: correctie, review, meldingen, voorkeur (B03-075) | jelly-leon | B03-071, 072, 073; S-G3-22; BG-33 | nee | andere banen |
| S-G4-40 Segmenten: leren, heranalyse en kwaliteitsmeting (B03-075) | jelly-leon | S-G4-15; S-G3-22 | ja (holdout-meting achter stack.lock) | banen zonder stack.lock |
| S-G4-16 Segmenten: beheerpagina en afronding B03-007 (B03-076 serverdeel) | jelly-leon | S-G4-15; S-G4-40; BG-31 | ja (image, browsertest achter stack.lock) | banen zonder stack.lock |
| S-G4-17 Segmenten: taaktypen, MediaGuard-leesadapter, connector (B03-078 serverdeel) | jelly-leon | B03-009; B03-018; BG-04 | ja (meetslot) | niets met stack.lock |
| S-G4-18 Apparaten: connector en clientrapport (B03-069 serverdeel) | jelly-leon | S-G4-06; S-G4-03 | nee | andere banen |
| S-G4-19 Contractcontrole events, foutcatalogus en pin (C1.3-JL-06, -07, -08) | jelly-leon | S-G4-11, -13, -14, -17, -18 | nee | andere banen |
| S-G4-42 Pluginpagina "Apparaten" voor beheerders (B03-066, B03-068) | jelly-leon | S-G4-07; S-G4-18; BG-26 | ja (image, browsertest achter stack.lock) | banen zonder stack.lock |
| S-G4-44 Pluginpagina "Watch Together" afmaken (B03-029, B03-022, B03-023) | jelly-leon | S-G4-11 | ja (image, browsertest achter stack.lock) | banen zonder stack.lock |
| S-G4-49 Scènezoeker: zoeken in ondertitelcues met tijdcode en rechten (B03-008 serverdeel; besluit Z-20) | jelly-leon | S-G3-22; S-G3-06; S-G3-10; cue-extractie S-G1-34; BG-06 (zonder besluit: geen spraakherkenning, geen embeddings) | nee (ONBEKEND of de indexbouw een werkertaak in de image vraagt; A-VERKEN stelt vast) | andere banen |
| S-G4-51 Offline downloaden: rechten, verlopen en uitgezet account (B03-011 serverdeel; besluit Z-20) | jelly-leon | S-G3-10 | nee | andere banen |
| S-G4-53 Live-tv en DVR: overlap, opnamestatus, bewaren, gids (B03-012 serverdeel; besluit Z-20) | jelly-leon | S-G4-04 | ja (server met nagebootste tuner achter stack.lock; ONBEKEND, A-VERKEN stelt vast) | banen zonder stack.lock |
| S-G4-20 Rij "Aanbevolen voor jou" (B03-036 deel rij) | jelly-leon-web | B03-035; BG-15; haakmodule; S-G3-30 (en S-G3-31 als die niet vervalt): WP-JSON B03-036 noemt B03-002 (startscherm) als afhankelijkheid | ja (npm-build, e2e) | jelly-leon-stappen zonder stack.lock |
| S-G4-45 Aanbevelingen: drie dialogen (B03-036 deel dialogen) | jelly-leon-web | S-G4-20 | ja (npm-build, e2e) | idem |
| S-G4-21 Capability-probe en rolbepaling (B03-065 webdeel 1) | jelly-leon-web | S-G4-05; S-G4-25 voor de marker | ja (npm-build, e2e) | idem |
| S-G4-22 Stall-detectie, label en "Waarom?" (B03-065 webdeel 2, B03-067 webdeel) | jelly-leon-web | S-G4-21; S-G4-08; BG-29 | ja (npm-build, e2e) | idem |
| S-G4-41 Scherm "Dit apparaat" en bevestigingsproef (B03-065, B03-066 webdeel) | jelly-leon-web | S-G4-21; S-G4-22; S-G4-06; BG-26 | ja (npm-build, e2e) | idem |
| S-G4-23 Skipknoppen web (B03-076 webdeel) | jelly-leon-web | S-G4-16; S-G4-15; BG-31 | ja (npm-build, e2e) | idem |
| S-G4-46 Hint na aftiteling, "Klopt niet", correctiepaneel (B03-075, B03-076 webdeel) | jelly-leon-web | S-G4-23; S-G4-15 | ja (npm-build, e2e) | idem |
| S-G4-43 Dialoog capaciteitsadvies (B03-025 webdeel) | jelly-leon-web | S-G4-09; S-G3-24; BG-13 | ja (npm-build, e2e) | idem |
| S-G4-24 Chat-strook web (B03-028 webdeel; alleen na BG-12 "aan") | jelly-leon-web | BG-12; S-G4-10; S-G3-24 | ja (npm-build, e2e) | idem |
| S-G4-50 Scènezoeker web: zoekscherm met tijdcode (B03-008 webdeel) | jelly-leon-web | S-G4-49; haak H-ROUTE | ja (npm-build, e2e) | idem |
| S-G4-54 Live-tv web: overlapwaarschuwing en opnamestatus (B03-012 webdeel) | jelly-leon-web | S-G4-53 | ja (npm-build, e2e) | idem |
| S-G4-25 Marker `jellyLeonBuild` in android en desktop (B03-069) | jelly-leon-clients | geen; mag voor de gate van golf 3 starten | ja (Gradle) | geen andere Gradle- of emulatorstap |
| S-G4-26 Android TV: capabilityrapport (B03-069) | jelly-leon-clients | S-G4-05; S-G4-06; BG-30 | ja (Gradle, emulator) | idem |
| S-G4-27 Skipknoppen Android TV (B03-077) | jelly-leon-clients | S-G4-16; BG-31; BG-08 | ja (Gradle, emulator) | idem |
| S-G4-28 Skipknop Android en desktop-marge (B03-077) | jelly-leon-clients | S-G4-27; BG-31; BG-08; S-P40-90 voor het desktopdeel | ja (Gradle, emulator) | idem |
| S-G4-29 Clientmatrix aanbevelingen (B03-037) | jelly-leon-clients | S-G4-20; S-G4-45; S-G4-12; S-G3-32 (WP-JSON B03-037 noemt B03-003); BG-15 | ja (emulator, stack.lock) | niets met stack.lock of emulator |
| S-G4-30 Clientmatrix golf 4 (JLT-25, -38, -42, -46, -55) | jelly-leon-clients | S-G4-07, -13, -14, -23, -26, -27, -28, -29, -46; S-G3-25 | ja (emulator, stack.lock) | niets met stack.lock of emulator |
| S-G4-52 Offline downloaden in de Android-app (B03-011 clientdeel) | jelly-leon-clients | S-G4-51; S-G4-30; BG-08 | ja (Gradle, emulator) | geen andere Gradle- of emulatorstap |
| S-G4-31 Hub-adapter Jelly Leon en "Hub-sleutelset kopieren" (C1.3-ASM-21) | ai-server-manager | S-P3-010, S-P3-020, S-P3-070 (STAPPEN_P3.md); JL4-pin in de plugin (golf 1); mag voor de gate van golf 3 starten | nee | alle Jelly Leon-banen |
| S-G4-32 Hub: kaartbasis B03 op het scherm Media | ai-server-manager | S-G4-31; S-P3-075 en S-P3-080 (STAPPEN_P3.md) | ja (next build, review) | Jelly Leon-banen zonder npm-build |
| S-G4-33 Hub-kaart Watch Together (B03-029) | ai-server-manager | S-G4-32; S-G4-11 | ja (next build, review) | idem |
| S-G4-34 Hub-kaart Aanbevelingen (B03-039) | ai-server-manager | S-G4-32; S-G4-12 | ja (next build, review) | idem |
| S-G4-36 Hub-kaart Mediakwaliteit met incidenten en bewijs (B03-058) | ai-server-manager | S-G4-32; S-G4-14 | ja (next build, review) | idem |
| S-G4-37 Hub-kaarten Afspelen en GPU-banen (B03-069) | ai-server-manager | S-G4-32; S-G4-18 | ja (next build, review) | idem |
| S-G4-38 Hub-kaart Intro en aftiteling (B03-078) | ai-server-manager | S-G4-32; S-G4-17 | ja (next build, review) | idem |
| S-G4-35 Hub: alle B03-kaarten samen, kinderschil en ontwerpreview (sluit de Hub-baan af) | ai-server-manager | S-G4-33, -34, -36, -37, -38 | ja (next build, review) | idem |
| S-G4-47 Winstmeting apparaatprofielen (JLT-40) | jelly-leon | S-G4-07; S-G4-22; S-G4-41; harnas B03-060 (S-P40-64) | ja (meetslot achter stack.lock) | niets met stack.lock |
| S-G4-48 Winstmeting segmenten (JLT-50) | jelly-leon | S-G4-16; S-G4-40; harnas B03-070 (S-P40-66) | ja (meetslot achter stack.lock) | niets met stack.lock |
| S-G4-39 Compat-regressie per oplevering en clientmatrixdocument (herhaalstap) | jelly-leon | na S-G4-07, S-G4-09, S-G4-14, S-G4-19, na S-G4-42 en S-G4-44, na S-G4-49, S-G4-51 en S-G4-53, en na de laatste web- en clientstap | ja (stack.lock) | niets met stack.lock |
| S-G4-90 Bewijs samenvoegen: programmabewijs, Excel en STATUS (hoofdstuk 10) | ai-server-manager | alle stappen van golf 4 afgevinkt of met reden geblokkeerd; laatste run van S-G4-39; geen keten open in een van de vier repos | nee | niets (leest de EVIDENCE.json van alle repos) |
| S-G4-95 Gate einde P4 (A-GATE, alleen lezen; hoofdstuk 10) | geen (leest jelly-leon, jelly-leon-web, jelly-leon-clients, ai-server-manager) | S-G4-90 | ja (volledige poort per repo, na elkaar) | niets in deze vier repos |

## 7. Startbezetting

**Bij de start van golf 3** (na S-G2-90 en de keuze "doorgaan naar golf 3") lopen hooguit vier ketens van dit bestand tegelijk, omdat bijna al het werk in een repo
ligt:

1. Baan jelly-leon: begin met S-G3-04 (klein; na S-G2-90 alleen de WT-1-gate vooraf), zodat de web-baan zo vroeg mogelijk kan starten;
   daarna S-G3-01 en verder in tabelvolgorde. Dit is het kritieke pad (27 stappen na elkaar, plus de vijf runs van
   S-G3-27). S-G3-28 en S-G3-30 (B03-006 en B03-002) staan vroeg in de tabel omdat werkpakketten van golf 2 en golf 4
   ze als afhankelijkheid noemen (zie de rij Z-20 in hoofdstuk 3). Voor golf 2 (B03-032 in S-G2-22, B03-072 in S-G2-42)
   en P4-0 (B03-016, B03-019, B03-020 naar B03-003) is die afhankelijkheid zacht: die stappen wachten er niet op; wat
   hier later aansluit staat in hun "Vooraf" in STAPPEN_P4_GOLF1_2.md.
2. Baan jelly-leon-web: start pas als S-G3-04 klaar is (S-G3-24). Tot dan ligt hier geen werk van golf 3.
3. Baan jelly-leon-clients: eerst S-G3-32 (B03-003; S-G3-20 wacht erop). S-G3-26 alleen als BG-10 een clientpatch
   toestaat. Daarnaast mag S-G4-25 (marker `jellyLeonBuild`) hier al tijdens golf 3 lopen (hangt niet aan de gate van
   golf 3; niet tegelijk met S-G3-26 of S-G3-32).
4. Baan ai-server-manager: S-G4-31 (Hub-adapter) mag al tijdens golf 3 lopen zodra S-P3-010, S-P3-020 en S-P3-070
   (STAPPEN_P3.md) klaar zijn; S-G4-32 volgt als ook S-P3-075 en S-P3-080 klaar zijn.

**Geen werk van golf 3 (en vóór de gate ook geen golf 4-werk) in:** jelly-leon-platform. De regisseur kan daar en in
de banen die stilliggen ketens van een andere fase of golf laten lopen (binnen de gate-matrix) om de 8 banen te vullen.
Let op in ai-server-manager: na ronde 3 staat daar niet-vastgelegd half werk aan de executor
(`<WERKMAP>/.lokaal/plan/STAND_RONDE3.md`); eerst `git -C <WERKMAP>/ai-server-manager status --short` bekijken en
geen Hub-stap starten zolang dat half werk er staat.

**Bij de start van golf 4** kunnen vier ketens tegelijk lopen: jelly-leon (S-G4-01), jelly-leon-web (S-G4-20, als
BG-15 genomen is), jelly-leon-clients (S-G4-25) en ai-server-manager (S-G4-31). Daarna komt per baan de volgende stap
uit de tabel vrij. De Hub-kaarten S-G4-33, -34, -36, -37 en -38 wachten elk op hun connectorstap in jelly-leon; de
regisseur haalt daarom S-G4-11, -12, -14, -17 en -18 in de jelly-leon-baan naar voren als de Hub-baan stilvalt en de
afhankelijkheden in de tabel dat toelaten. De Hub-kaart "Nederlandse ondertitels" hoort bij P5 (S-P5-62 in
STAPPEN_P5.md) en staat daarom niet in dit bestand; S-G4-35 is de gezamenlijke afsluiting van de Hub-baan.

**Later toegevoegde nummers:** S-G4-40 tot en met S-G4-46 staan in tabel 6.2 en in hoofdstuk 9 op hun plaats in de
volgorde (S-G4-40 na S-G4-15; S-G4-42 en S-G4-44 na S-G4-19; S-G4-45 na S-G4-20; S-G4-41 na S-G4-22; S-G4-46 en
S-G4-43 na S-G4-23; S-G4-47 en S-G4-48 voor de laatste run van S-G4-39). Na besluit Z-20 kwamen erbij: in golf 3
S-G3-28 tot en met S-G3-30 (na S-G3-04), S-G3-31 (na S-G3-25) en S-G3-32 (voor S-G3-26); in golf 4 S-G4-49, S-G4-51
en S-G4-53 (na S-G4-44), S-G4-50 en S-G4-54 (na S-G4-24) en S-G4-52 (na S-G4-30). De regisseur volgt de tabel, niet de
nummering.

**Excel en fase-afsluiting:** het bijwerken van de Excel (POORTEN.md, blok P-EXCEL) schrijft in ai-server-manager.
Die stap (S-G4-90) loopt daarom nooit naast een stap van de Hub-baan (S-G4-31 tot en met S-G4-38) en pas als die baan
stilligt. S-G4-95 (A-GATE) loopt pas als S-G4-90 klaar is en in geen van de vier repos een keten open is.

**Geen werk van golf 4 in:** jelly-leon-platform. Er is in dit deel van het plan geen enkele stap voor die repo.

**Zware stappen:** emulator, Gradle en zware transcodes of tijdmetingen nooit tegelijk (BOUWPLAN#F5.8 Bouwfasen,
geheugenregel). Een stap met een tijdmeting vraagt het exclusieve meetslot (`stack.lock`); loopt er een andere keten met
een npm-build of image-build, dan wacht de meting. De `stack.lock` is in eerdere rondes uren bezet geweest; de
regisseur plant metingen daarom aan het eind van een blok en niet tussendoor.

## 8. Stappen golf 3

**Vaste afspraken voor elke stap hieronder (staan niet steeds opnieuw in de stap):**

- **Half werk:** vindt de controle "Al gedaan?" een deel van het werk, dan eerst
  `git -C <WERKMAP>/<repo> status --short` en `git -C <WERKMAP>/<repo> log --oneline @{u}..` lezen. Bouw verder op wat
  er staat; gooi niets weg. Staat er niet-vastgelegd werk dat niet bij deze stap hoort, stop dan en meld het (V-015,
  V-016).
- **Poort:** naast de genoemde poort gelden altijd P-GIT, P-EERLIJK en de CI-controle uit POORTEN.md (kop "0.5
  CI-controle na elke push"). Lokaal groen en CI rood = stap niet klaar.
- **Bewijs:** de bouwer schrijft de regels in EVIDENCE (en EXCEL_TAKEN.json als de repo dat bestand bijhoudt) van de
  eigen repo. Status alleen "Bezig" of "Geblokkeerd". Bij "Bezig" hoort het validatielabel (Unit-getest, Sim-getest of
  Sim-geslaagd) en het pad naar het testrapport onder `docs/platform-v2/test-evidence/`.
- **Testbestanden:** nieuwe plugintests komen onder PLUGINTEST in een map per module (bijvoorbeeld
  `Modules/Quality/`); de bestaande hulpklassen staan in `Hulp/Harnas.cs` en `Hulp/OpenApiBouwer.cs`.
- **Media:** het corpus `<WERKMAP>/.lokaal/media-corpus` wordt altijd alleen-lezen gekoppeld. Een test die in een
  mediamap schrijft is fout.
- **OpenAPI:** elke nieuwe route komt in de OpenAPI van de plugin; drift mag alleen additief zijn (bestaande tests
  `OpenApiDriftTests` en `OpenApiContractTests` in PLUGINTEST blijven groen).
- **Stappen uit besluit Z-20** (S-G3-28 tot en met S-G3-32 en S-G4-49 tot en met S-G4-54; geldt ook in hoofdstuk 9):
  - Bron: er is GEEN object in WP-JSON. De bron is TASKS-JSON (object met het B03-ID) plus BOUWPLAN#4. Bouwfasen
    (verplichte volgorde), kop "#### B03-0nn — ...", en de raakvlakken die de stap noemt. Wat daar niet staat, is
    ONBEKEND en wordt niet verzonnen.
  - "Waar haalbaar" (06_FASERING_EN_GATES.md, Fase P4: "scene search, live-tv/DVR, offline apps waar haalbaar")
    betekent in dit plan: bouwen en testen zo ver als de ontwikkelmachine toelaat, met simulator, emulator of
    wegwerpcontainer (00_LEES_EERST.md deel 7). Wat een echte NAS, echte apparaten, een echte tuner of een account
    vraagt, wordt niet nagebootst als bewijs (V-099) maar staat op "Geblokkeerd" met NIET GEVALIDEERD; de handeling
    hoort bij STAPPEN_P6.md, N-P6-09.
  - A-VERKEN legt de scope vast: bouwpunt 1 van zo'n stap is altijd "Scope". A-VERKEN zet per onderdeel van de bron in
    het dossier (veld per_punt): "doet upstream Jellyfin 12.x in de fork al" (dan niet opnieuw bouwen; S7 van de
    prompt) | "ontbreekt en haalbaar" | "alleen met echte NAS, apparaten of account". A-BOUW bouwt alleen wat het
    dossier "ontbreekt en haalbaar" noemt. Noemt het dossier meer werk dan één subagent in één keer afrondt: AGENTEN.md
    6.7 (splitsen). Valt een onderdeel van de bron af of schuift het naar een andere fase: dat is een besluit, keuzemenu
    (AGENTEN.md 6.8); A-VERKEN zet het onder besluit_nodig.
  - Een nieuwe route krijgt een schema in de OpenAPI van de plugin (additief). Noemt BOUWPLAN geen schema, dan legt
    A-BOUW het vast in een ADR in `docs/adr/` van de repo; de reviewers toetsen het.

### S-G3-01 - Module Quality: fundament, eigen opslag en alleen-lezen-garanties
- **Repo:** jelly-leon | **Fase:** P4 (golf 3) | **Omvang:** groot | **Moeilijkheid:** gewoon | **Zwaar:** nee (plugin-build en -test achter docker-build.lock)
- **Werkpakketten en tests:** B03-050; JLT-35 (deel fundament); JLT-39 (alleen bewijsregel)
- **Vooraf:** S-G2-90 gehaald (gate golf 2; rapport `<WERKMAP>/.lokaal/ketens/GATE-GOLF-2/RAPPORT-A-GATE.md`; die gate veronderstelt Gate P4-0 en Gate golf 1: B03-001, B03-013, B03-017 in EVIDENCE van jelly-leon). Geen besluit nodig.
- **Al gedaan?** `grep -c '"id": "B03-050"' <WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json` -> 0 = niet gestart. `grep -rln "quality.db" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = opslag nog niet gebouwd. `ls <WERKMAP>/jelly-leon/plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Modules/Quality` -> tijdens de verkenning alleen `QualityController.cs` en `QualityModule.cs` (skelet uit golf 1): daarop voortbouwen.
- **Lees eerst:** WP-JSON object B03-050; BOUWPLAN#F4.4 Gegevens en bescherming; BOUWPLAN#F4.5.3 Endpoints in Jelly Leon; BOUWPLAN#F4.8 Bouwfasen (regel QC-0); BOUWPLAN#10.9 Opslag en gegevensbescherming
- **Bouw:**
  1. Schakelaar `Quality.Enabled` en eigen SQLite `quality.db` onder de gegevensmap van Jelly Leon (map 0700), met versietabel en forward-only migraties. Bron: WP-JSON B03-050, veld Uitvoering.
  2. Back-up voor elke migratie met `VACUUM INTO` (laatste 3, hooguit 90 dagen); mislukte migratie = status `degraded` en geen scan. Bron: BOUWPLAN#F4.4.3 Migraties en back-up.
  3. Opstartcontrole alleen-lezen-media via de mountvlag (`statvfs` ST_RDONLY of `/proc/self/mountinfo`), nooit met een schrijfpoging; schrijfbare mediamount = status `down` en geen enkele scan; waarschuwing als Jellyfin zelf in mediamappen schrijft. Bron: WP-JSON B03-050.
  4. Analyzer-regels en een read-only-architectuurtest voor de namespace `Jellyfin.Plugin.JellyLeon.Quality` (geen schrijvende API's op bibliotheek, kijkgeschiedenis of gebruikers). Bron: BOUWPLAN#F4.4.2 Wat F4 nooit doet.
  5. Routes Q1 `GET /media/v1/quality/status`, Q13 `GET/PUT /media/v1/quality/config` (If-Match, Idempotency-Key) en Q14 `POST /media/v1/quality/data/purge?dry_run=true|false` (vraagt een export van hooguit 24 uur oud). Bron: BOUWPLAN#F4.5.3.
  6. Export en import van de eigen gegevens; uitzetten en verwijderen laat de server als stock achter. Bron: BOUWPLAN#F4.4.6 Uitzetten, verwijderen en terug naar stock.
  7. Tests (zie hieronder) en EVIDENCE-regels.
- **Tests (verplicht):** xUnit onder `PLUGINTEST/Modules/Quality/`: migratie heen, back-up aanwezig voor migratie, Q1/Q13/Q14 contract. Negatief: (a) nagebootste schrijfbare mediamount -> status `down`, 0 scans; (b) mislukte migratie -> `degraded`; (c) Q13 PUT zonder If-Match en Q14 zonder verse export -> geweigerd met de code uit de foutcatalogus; (d) niet-beheerder -> 403. Commando: T-JL-PLUGIN met `--filter "FullyQualifiedName~Quality"`, daarna T-JL-PLUGIN volledig.
- **Poort:** P-jelly-leon (plugin, volledig) + P-CONTRACT + P-HARDE-EIS. Extra: de plugin laadt nog in de stock-image (bestaande plugin-laadtest uit golf 1; A-VERKEN zoekt de naam op met `grep -rn "stock" <WERKMAP>/jelly-leon/tools/jelly-leon/e2e --include=*.py -l`).
- **Valkuilen:** V-003, V-005, V-066, V-071. Eigen: de mountcontrole mag nooit zelf een bestand proberen te schrijven.
- **Bewijs:** B03-050 -> Bezig (Unit-getest). JLT-35 -> Bezig, met de tekst "deel fundament; differentiele run volgt in S-G3-27". JLT-39 -> Geblokkeerd: "NIET GEVALIDEERD: echte NAS nodig (QC-8, kwaliteitscontrole op de echte bibliotheek); zie STAPPEN_P6.md".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-HARDE-EIS (VERPLICHT: eigen database met migratie en verwijderroute) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard; R-HARDE-EIS N4
- **Stop en vraag als:** de bouwstenen opslag, foutcatalogus of analyzer uit golf 1 ontbreken in `PLUGIN/Core`; het Quality-skelet nog niet-vastgelegd werk van een andere agent is; de plugin met de module niet meer in stock laadt.

### S-G3-02 - Jobtypes quality.* en kostenmodel in de globale batchplanner
- **Repo:** jelly-leon | **Fase:** P4 (golf 3) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** B03-053; JLT-36 (deel regels; meting volgt in S-G3-12)
- **Vooraf:** S-G3-01; planner en werker van B03-018 aanwezig (Gate golf 1). BG-07 bepaalt alleen of batch op de NAS aan mag, niet deze bouw.
- **Al gedaan?** `grep -rn "quality.full_pass" <WERKMAP>/jelly-leon/plugins/JellyLeon/src | head -3` -> geen uitvoer = niet gestart. `git -C <WERKMAP>/jelly-leon ls-files plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Core/Planner` -> geen uitvoer = planner van golf 1 is niet gecommit (op 2026-11-11 alleen half werk in de werkmap): STOP.
- **Lees eerst:** WP-JSON object B03-053; BOUWPLAN#F4.3.4 Jobtypes in de globale batchplanner; BOUWPLAN#F4.3.5 GPU-, CPU-, RAM- en I/O-budget op de NAS; BOUWPLAN#10.7 Globale batchplanner
- **Bouw:**
  1. Registreer de jobtypes `quality.inventory`, `quality.structure`, `quality.sample`, `quality.full_pass`, `quality.dialogue_contrast`, `quality.verify` en `quality.readback` bij de planner, elk met een kostenklasse per codec en resolutie. Geen eigen planner of werker. Bron: WP-JSON B03-053.
  2. Regels: live gaat voor MediaGuard-AV1 gaat voor B03-batch; alleen zonder actieve Jelly Leon-sessie; stoppen binnen 5 s na PlaybackStart (hele procesgroep); hervatten na 10 min rust. Bron: BOUWPLAN#F4.3.4.
  3. Niet starten terwijl de CPU-baan van MediaGuard draait (uitkomst van de gemeenschappelijke poller, veldenwitte lijst `encoder.lanes[].lane/running/slots/paused`); wel bij alleen een bezette GPU-baan, met hooguit 2 threads. Bron: WP-JSON B03-053.
  4. Noodstop van MediaGuard en de stroomonderbrekers uit het werkpakket: geen nieuwe zware taak. Bron: WP-JSON B03-053.
  5. Tests en EVIDENCE.
- **Tests (verplicht):** xUnit met een nepklok en de nagebootste MediaGuard-status: stop binnen 5 s, hervat na 10 min, volgorde van voorrang. Negatief: (a) bezette MG-CPU-baan -> 0 nieuwe zware taken; (b) noodstop -> 0 nieuwe zware taken; (c) MediaGuard onbekend -> veilige stand (geen batch). Commando: T-JL-PLUGIN met `--filter "FullyQualifiedName~Quality"`.
- **Poort:** P-jelly-leon (plugin, volledig).
- **Valkuilen:** V-003, V-057. Eigen: een test met echte wachttijden van minuten is geen unit-test; gebruik de klok van de planner.
- **Bewijs:** B03-053 -> Bezig (Unit-getest). JLT-36 -> Bezig met "regels getest; meting met exclusief meetslot volgt in S-G3-12".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** de planner van golf 1 geen manier heeft om jobtypes of kostenklassen te registreren (dan hoort de uitbreiding eerst in golf 1, B03-018).

### S-G3-03 - Module Subtitles: fundament, stabiele spoorsleutels en NL-dekking (alleen lezen)
- **Repo:** jelly-leon | **Fase:** P4 (golf 3) | **Omvang:** groot | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** B03-040; JLT-20 (baselinedeel); JLT-24 (deel: geen schrijfacties); JLT-26 (alleen bewijsregel)
- **Vooraf:** S-G2-90 gehaald (gate golf 2; daarin Gate golf 1 met B03-017; spoorsleutel volgens bouwsteen 10.12). Geen besluit nodig.
- **Al gedaan?** `grep -c '"id": "B03-040"' <WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json` -> 0 = niet gestart. `ls <WERKMAP>/jelly-leon/plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Modules` -> tijdens de verkenning alleen `Devices` en `Quality`; een map voor ondertitels ontbreekt. `grep -rln "subtitles/coverage" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = niet gestart.
- **Lees eerst:** WP-JSON object B03-040; BOUWPLAN#F3.4.1 Eigen opslag; BOUWPLAN#F3.5.2 Clientroutes en beheerroutes; BOUWPLAN#10.12 Stabiele spoorsleutel; BOUWPLAN#F3.8 Bouwfasen (regel 3A)
- **Bouw:**
  1. Module Subtitles (namespace `Jellyfin.Plugin.JellyLeon.Subtitles`) met eigen schakelaar en eigen `subtitles.db` (migraties en back-up zoals de opslagbouwsteen van golf 1). Bron: WP-JSON B03-040.
  2. Inventaris per item van alle ondertitelsporen via `ILibraryManager`/MediaStreams: tekst of beeld, tagtaal, vlaggen forced/SDH/standaard/commentaar, herkomst ingebed/extern/Jelly Leon. Alleen lezen. Bron: WP-JSON B03-040.
  3. `track_key` per spoor in plaats van de verschuivende Jellyfin-index (extern: sha256 van het echte pad plus grootte en mtime; ingebed: index binnen het bestand plus codec, taal, kanalen en titelhash). Bron: BOUWPLAN#10.12.
  4. Dekkingsstatus per item (onder meer `menselijk_aanwezig`, `in_wachtrij`, `wacht_op_mediaguard`) en de route `GET /media/v1/subtitles/coverage`. Bron: BOUWPLAN#F3.5.2.
  5. Opstartcontrole en analyzer-regels: de module schrijft nooit buiten de eigen gegevensmap. Bron: BOUWPLAN#F3.4.2 Wat F3 nooit doet.
  6. Tests en EVIDENCE. De taal uit de tekst (py3langid) is een werkertaak en hoort bij S-G3-05.
- **Tests (verplicht):** xUnit onder `PLUGINTEST/Modules/Subtitles/`: `track_key` blijft gelijk nadat een extern spoor is toegevoegd of verwijderd terwijl de Jellyfin-indexen verschuiven; Sintel met ingebed NL -> `menselijk_aanwezig`; item zonder NL -> `in_wachtrij` of `wacht_op_mediaguard`. Negatief: (a) gebruiker zonder bibliotheekrecht -> 404 op het item; (b) na een volledige inventaris 0 nieuwe of gewijzigde bestanden buiten de gegevensmap (vergelijk bestandslijst voor en na). Commando: T-JL-PLUGIN met `--filter "FullyQualifiedName~Subtitles"`.
- **Poort:** P-jelly-leon (plugin, volledig) + P-CONTRACT + P-HARDE-EIS.
- **Valkuilen:** V-005, V-066. Eigen: gebruik nooit de Jellyfin-ondertitelindex als sleutel; die verschuift zodra er een extern spoor bij komt.
- **Bewijs:** B03-040 -> Bezig (Unit-getest; "taal uit tekst volgt in S-G3-05"). JLT-20 -> Bezig met "baselinedeel". JLT-24 -> Bezig met "deel inventaris: geen schrijfacties". JLT-26 -> Geblokkeerd: "NIET GEVALIDEERD: echte NAS en echte bibliotheek nodig; zie STAPPEN_P6.md".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-HARDE-EIS (VERPLICHT: leest spoorgegevens waar onthouden spoorkeuzes van afhangen) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard; R-HARDE-EIS N4
- **Stop en vraag als:** de stock-baseline van golf 0 (RemoteSearch voor NL leeg, 0 nieuwe NL-sporen) niet in het bewijs van jelly-leon terug te vinden is; de bouwsteen spoorsleutel uit golf 1 een andere vorm heeft dan het bouwplan.

### S-G3-04 - Watch Together: telemetrieroute en diagnose (serverdeel van B03-024)
- **Repo:** jelly-leon | **Fase:** P4 (golf 3) | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** B03-024 (serverdeel); JLT-01 en JLT-02 (voorwaarde; meting in S-G3-24)
- **Vooraf:** WT-1-gate geslaagd volgens het rapport van S-G2-90 (`<WERKMAP>/.lokaal/ketens/GATE-GOLF-2/RAPPORT-A-GATE.md`; B03-021: decorator of core-patch); B03-020 (baseline) in EVIDENCE.
- **Al gedaan?** `grep -rln "watch/telemetry" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = niet gestart. `grep -rln "watch/capabilities" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = de module Watch Together van golf 2 ontbreekt: STOP.
- **Lees eerst:** WP-JSON object B03-024; BOUWPLAN#F1.5.2 Endpoints (E1, E9, E10); BOUWPLAN#F1.5.3 Schema's; BOUWPLAN#F1.7 Configuratieopties
- **Bouw:**
  1. Route E10 `POST /media/v1/watch/telemetry`: Idempotency-Key = `window_id`; herhaling geeft 204; meer dan 1 per 10 s per sessie geeft `RATE_LIMITED`. Bron: BOUWPLAN#F1.5.2.
  2. Route E9 `GET /media/v1/watch/groups/{groupId}/diagnostics` voor leden en beheerders. Bron: BOUWPLAN#F1.5.2.
  3. Instelling `SyncSeed.Enabled` en het veld in E1 `GET /media/v1/watch/capabilities` waaraan de webplugin ziet of hij mag zaaien. Bron: WP-JSON B03-024.
  4. Telemetrie alleen als aantallen en tijden, zonder titels, namen of adressen; bewaartermijn volgens BOUWPLAN#F1.4.1 Eigen opslag en persoonsgegevens.
  5. Tests en EVIDENCE.
- **Tests (verplicht):** xUnit: herhaalde `window_id` -> 204 zonder tweede rij; schema-geldig antwoord op E9. Negatief: (a) tweede melding binnen 10 s -> `RATE_LIMITED`; (b) niet-lid vraagt E9 -> zelfde antwoord als bij een niet-bestaande groep; (c) lichaam groter dan 1 MiB -> geweigerd voor verwerking. Commando: T-JL-PLUGIN met `--filter "FullyQualifiedName~Watch"`.
- **Poort:** P-jelly-leon (plugin, volledig) + P-CONTRACT.
- **Valkuilen:** V-039, V-046. Eigen: de limiet per sessie mag niet op een header van de aanvrager steunen (V-049).
- **Bewijs:** B03-024 -> Bezig (Unit-getest; "serverdeel; webdeel in S-G3-24").
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard; A-BOUW N2 mag als A-VERKEN bevestigt dat de routes alleen de bestaande bouwstenen gebruiken
- **Stop en vraag als:** de WT-1-gate niet aantoonbaar is of B03-021 op de core-patch-route zit zonder geregistreerde patch in `<WERKMAP>/jelly-leon/docs/platform-v2/PATCHES.md`.

### S-G3-28 - Metadata en anime-mapping: externe ID's met versie, zekerheid en eigen correcties (B03-006, serverdeel)
- **Repo:** jelly-leon | **Fase:** P4 (golf 3) | **Omvang:** middel | **Moeilijkheid:** hoog | **Zwaar:** nee (plugin-build en -test achter docker-build.lock)
- **Werkpakketten en tests:** B03-006 (serverdeel)
- **Vooraf:** S-G2-90 gehaald (gate golf 2). Besluit Z-20 genomen (in P4 bouwen). BG-17 (online metadata, moment "bij B03-006"): de regisseur legt het voor vóór deze stap; zonder besluit geldt "aan laten" (standaardgedrag van Jellyfin) en deze stap verandert niets aan de instellingen voor online metadata.
- **Al gedaan?** `grep -c '"id": "B03-006"' <WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json` -> 0 = niet gestart (op 2026-11-11: 0). `git -C <WERKMAP>/jelly-leon ls-files plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Modules | cut -d/ -f6 | sort -u` -> op 2026-11-11 alleen `Devices` en `Quality`: er is geen module of opslag voor metadata.
- **Lees eerst:** TASKS-JSON object B03-006; BOUWPLAN#B03-006 — Metadata en anime mapping; BOUWPLAN#2. Datamodel en levensduur (entiteiten `external_id` en `episode_map`, en het blok "Aanvulling 2.0": eigen SQLite per module, nooit schrijven in `jellyfin.db`); BOUWPLAN#10.1 Uitbreidingsladder en pluginverpakking; `<WERKMAP>/.lokaal/plan/uit/BESLUITEN_EN_BLOKKADES.md`, kop "BG-17"; E2E-JSON rij EX37 (het eindscenario zelf is S-P6-15 in STAPPEN_P6.md); TEST-JSON rij JLT-72 (absolute anime-nummering bij de overname, raakvlak); WP-JSON objecten B03-032 en B03-072 (die noemen B03-006 als afhankelijkheid)
- **Bouw:**
  1. Scope (A-VERKEN, volgens de afspraak "Stappen uit besluit Z-20" in hoofdstuk 8): wat de fork (upstream Jellyfin 12.x) al doet voor provider-ID's per item en voor afleveringsnummering (de serie-instelling met de opties airdate, dvd en absolute in `MediaBrowser.Controller/Entities/TV/Series.cs`), en wat ontbreekt voor de bron: externe ID's met versie en zekerheid, correcties door de beheerder die een metadataverversing overleven, conflictreview. ONBEKEND of de koppeling aflevering-bestand bij absolute nummering upstream al stabiel blijft - A-VERKEN stelt vast met `grep -rln -i "absolute" <WERKMAP>/jelly-leon/MediaBrowser.Controller/Entities/TV <WERKMAP>/jelly-leon/MediaBrowser.Providers --include=*.cs` en de bijbehorende tests. A-VERKEN zet ook in het dossier of de correcties van deze stap de afleveringsvolgorde of seizoensgrenzen veranderen waarop de segmentenmodule (S-G2-42, B03-072) haar partners kiest; zo ja, welke herberekening dat vraagt (wordt geen eigen bouwwerk in deze stap: keuzemenu).
  2. Externe ID's met versie, zekerheid en correcties van de beheerder in eigen opslag van de plugin (welke opslagbouwsteen van golf 1: A-VERKEN noemt hem), nooit rechtstreeks in `jellyfin.db`; schrijven in Jellyfin-metadata alleen via de officiële API van de server. Bron: TASKS-JSON B03-006 (Uitvoering), BOUWPLAN#2 (Aanvulling 2.0).
  3. Correcties van de beheerder blijven staan na een metadataverversing ("behoud eigen wijzigingen"). Bron: BOUWPLAN#B03-006 (Schermen/bediening).
  4. Achtergrondscans vertraagd ("delayed background scans") via de planner van golf 1 (B03-018); geen eigen planner. Bron: TASKS-JSON B03-006.
  5. Nooit de wanted-stand van MediaGuard wijzigen; MediaGuard alleen lezen via de viewerclient van B03-009, en alleen als het dossier dat nodig vindt. Bron: TASKS-JSON B03-006.
  6. Routes voor beheerders (lezen, corrigeren, conflict afhandelen), additief in de OpenAPI; schema volgens de afspraak in hoofdstuk 8. Module uit: 404 (besluit Z-19).
  7. Tests en EVIDENCE.
- **Tests (verplicht):** xUnit onder PLUGINTEST (map volgens de module of bouwsteen die A-VERKEN noemt): de acceptatie uit TASKS-JSON B03-006 "S01E01 versus absolute E13 blijft correct gelinkt na metadata refresh" op een synthetische testserie. ONBEKEND welk corpusrecept absolute nummering heeft - A-VERKEN stelt vast met `grep -rln -i "absolute\|anime" <WERKMAP>/jelly-leon/tools/b03-harnas/b03h/corpus`. Negatief: (a) een correctie van de beheerder overleeft een verversing; (b) gezien-status en hervatpunt van een testgebruiker op de betrokken afleveringen zijn voor en na de verversing gelijk; (c) 0 aanroepen naar schrijvende MediaGuard-routes; (d) een niet-beheerder krijgt 403 op elke corrigerende route; (e) module uit -> 404. Commando: T-JL-PLUGIN met het filter van de module of bouwsteen, daarna T-JL-PLUGIN volledig.
- **Poort:** P-jelly-leon (plugin, volledig) + P-CONTRACT + P-HARDE-EIS.
- **Valkuilen:** V-003, V-005, V-066. Eigen: een verkeerde koppeling van aflevering en bestand verplaatst kijkgeschiedenis naar een ander item; een test die alleen het nieuwe gedrag bekijkt en niet de kijkgegevens ervoor en erna, bewijst dat niet.
- **Bewijs:** B03-006 -> Bezig (Unit-getest). Blokkadetekst voor de echte bibliotheek: "NIET GEVALIDEERD (echte NAS): echte anime-bibliotheek en metadatabronnen; zie STAPPEN_P6.md, N-P6-09." EX37 blijft bij S-P6-15.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-HARDE-EIS (tegelijk; R-HARDE-EIS VERPLICHT: de koppeling van afleveringen bepaalt bij welk item gezien-status en hervatpunten horen) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); R-HARDE-EIS N4; overige standaard
- **Stop en vraag als:** BG-17 nog niet is voorgelegd (de regisseur legt het eerst voor; zonder antwoord geldt "aan laten"); de bouw een schrijfactie in `jellyfin.db` of op de wanted-stand van MediaGuard zou vragen; een correctie kijkgegevens naar een ander item zou verplaatsen; er geen testserie met absolute nummering in het corpus is (geen eigen media toevoegen zonder licentie, BG-37).

### S-G3-29 - Pluginpagina "Metadata-suggesties" voor beheerders (B03-006, schermdeel)
- **Repo:** jelly-leon | **Fase:** P4 (golf 3) | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** ja (image en browsertest achter stack.lock)
- **Werkpakketten en tests:** B03-006 (schermdeel)
- **Vooraf:** S-G3-28 (routes voor beheerders).
- **Al gedaan?** `python3 -c "import json,sys;[print(r.get('opmerking','')) for r in json.load(open(sys.argv[1])) if r['id']=='B03-006']" <WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json` -> noemt de opmerking een pluginpagina met rapportpad, dan is deze stap gedaan; geen regel of geen pagina = niet gestart.
- **Lees eerst:** BOUWPLAN#B03-006 — Metadata en anime mapping (Schermen/bediening: "Metadata-suggesties met bron en behoud eigen wijzigingen"); stap S-G3-16 in dit bestand (zelfde vorm voor een pluginpagina: browsertest en toestanden); het dossier en de rapporten van S-G3-28 in `<WERKMAP>/.lokaal/ketens/S-G3-28/`
- **Bouw:**
  1. Scope (A-VERKEN): welke routes S-G3-28 opleverde en wat de pagina daarmee kan tonen; de pagina toont niets wat geen route levert.
  2. Pluginpagina voor beheerders: per suggestie de bron en de zekerheid; aannemen of afwijzen; eigen wijzigingen blijven zichtbaar als "eigen". Vormgeving volgt upstream Jellyfin (buiten Peil).
  3. Elke toestand zichtbaar: laden, leeg, fout, geen rechten, module uit.
  4. Tests en EVIDENCE.
- **Tests (verplicht):** Playwright in Chromium, Firefox en WebKit (de opzet van S-G3-16): de pagina laadt met een gevulde testdatabase; aannemen en afwijzen werken. Negatief: (a) een niet-beheerder krijgt 403 op pagina en routes; (b) een afgewezen suggestie verandert niets aan het item; (c) module uit -> de pagina toont "module uit" en doet geen verzoek dat een fout geeft. Commando's: T-JL-PLUGIN; T-JL-IMAGE; de browsertest achter `flock <WERKMAP>/.lokaal/stack.lock nice -n 10`.
- **Poort:** P-jelly-leon (plugin, image bouwen en proeven).
- **Valkuilen:** V-003, V-005.
- **Bewijs:** B03-006 -> Bezig bijwerken met "schermdeel: pluginpagina" en het rapportpad.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK (geen A-ONTWERP en geen R-ONTWERP: pluginpagina's vallen buiten Peil)
- **Niveau:** standaard
- **Stop en vraag als:** S-G3-28 geen routes heeft opgeleverd waar een pagina op kan bouwen.

### S-G3-30 - Universele bibliotheek: anime apart van films en series, met externe ID's (B03-002, serverdeel)
- **Repo:** jelly-leon | **Fase:** P4 (golf 3) | **Omvang:** middel | **Moeilijkheid:** hoog | **Zwaar:** nee (plugin-build en -test achter docker-build.lock)
- **Werkpakketten en tests:** B03-002 (serverdeel)
- **Vooraf:** S-G3-28 (externe ID's van B03-006; TASKS-JSON B03-002 Uitvoering: "add overlay for anime metadata + external IDs"). Besluit Z-20 genomen.
- **Al gedaan?** `grep -c '"id": "B03-002"' <WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json` -> 0 = niet gestart (op 2026-11-11: 0). `grep -rln "Anime.LibraryIds\|GenreNames" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> uitvoer = de anime-herkenning van F2 (golf 2, B03-035) bestaat; daarop voortbouwen, geen tweede definitie van "anime".
- **Lees eerst:** TASKS-JSON object B03-002; BOUWPLAN#B03-002 — Universele bibliotheek; BOUWPLAN, hoofdstuk F2, alinea "9. Anime-herkenning" (eerste regel die past; "Later volgt de anime-splitsing van B03-002"); WP-JSON objecten B03-036 en B03-072 (die noemen B03-002 als afhankelijkheid); het dossier en de rapporten van S-G3-28
- **Bouw:**
  1. Scope (A-VERKEN): wat upstream al levert voor "film, series, anime, muziek in één ervaring met filters, collecties, tags, genres, persoon en talen" (BOUWPLAN#B03-002) en wat ontbreekt. A-VERKEN zet ook in het dossier of de schermen uit de bron ("Unified homepage, watchlist, anime-splits, details en muziek") iets vragen wat upstream jellyfin-web niet heeft: dat bepaalt of S-G3-31 loopt.
  2. Anime-overlay op basis van de externe ID's van S-G3-28 en de ene definitie van "anime" uit F2 (alinea 9); geen tweede definitie.
  3. Anime met absolute afleveringen en een film met dezelfde titel blijven aparte items; nooit items samenvoegen of splitsen via de database. Bron: TASKS-JSON B03-002 (Acceptatie, Uitvoering "no DB direct edits").
  4. Routes alleen als het dossier ze nodig vindt (afspraak in hoofdstuk 8). Module uit: 404 (besluit Z-19).
  5. Tests en EVIDENCE.
- **Tests (verplicht):** xUnit: de acceptatie uit TASKS-JSON B03-002 "Anime met absolute episodes en film met zelfde titel blijven aparte items" met synthetische items. Negatief: (a) een film en een anime met dezelfde titel: twee items, en de kijkgegevens van een testgebruiker staan elk op het eigen item; (b) UserData van de testgebruikers is voor en na een volledige bibliotheekscan gelijk; (c) een item dat volgens F2 geen anime is, verandert niet van soort. Commando: T-JL-PLUGIN met het filter van de module of bouwsteen, daarna volledig. De differentiele run met alle modules aan volgt in S-G3-27 (run na S-G3-30).
- **Poort:** P-jelly-leon (plugin, volledig) + P-CONTRACT + P-HARDE-EIS.
- **Valkuilen:** V-003, V-005, V-066.
- **Bewijs:** B03-002 -> Bezig (Unit-getest; "webdeel: S-G3-31" of "webdeel niet nodig: <reden uit het dossier>"). "NIET GEVALIDEERD (echte NAS): echte bibliotheek; zie STAPPEN_P6.md, N-P6-09."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-HARDE-EIS (tegelijk; R-HARDE-EIS VERPLICHT: items samenvoegen of splitsen verplaatst kijkgeschiedenis) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); R-HARDE-EIS N4; overige standaard
- **Stop en vraag als:** de overlay alleen met een wijziging in upstream-code kan (dan eerst melden: een corepatch hoort in het patchregister); de anime-herkenning van F2 ontbreekt of anders werkt dan BOUWPLAN F2 alinea 9; een scan items samenvoegt of splitst.

### S-G3-05 - Ondertiteltoolkit in de analysewerker (subtitle.inventory, subtitle.qc)
- **Repo:** jelly-leon | **Fase:** P4 (golf 3) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (image-build; docker-build.lock)
- **Werkpakketten en tests:** B03-041; B03-040 (rest: taal uit tekst); JLT-20 (deel taalherkenning)
- **Vooraf:** S-G3-03; analysewerker B03-018 met een vastgepinde Python-omgeving en SBOM (Gate golf 1).
- **Al gedaan?** `grep -rn "subtitle.qc" <WERKMAP>/jelly-leon --include=*.py --include=*.cs -l | head` -> geen uitvoer = niet gestart. `grep -rn "py3langid\|pysubs2" <WERKMAP>/jelly-leon/deploy <WERKMAP>/jelly-leon/tools -l | head` -> geen uitvoer = pakketten nog niet vastgepind.
- **Lees eerst:** WP-JSON object B03-041; BOUWPLAN#10.6 Analysewerker en bestandspas; BOUWPLAN#F3.3.5 Vertaalpijplijn; BOUWPLAN#F3.9.1 Testomgeving en corpus; BOUWPLAN#10.16 Lokale verwerking en optionele modellen
- **Bouw:**
  1. Voeg pysubs2, srt, chardet, charset-normalizer en py3langid toe aan de ene vastgepinde Python-omgeving van de werker (`pip --no-deps --require-hashes`), met SBOM en licentie-inventaris. Niet in de image: auditok, ctranslate2, sentencepiece, torch. Bron: WP-JSON B03-041.
  2. Taaktype `subtitle.inventory`: coulant inlezen (ook misvormde SRT), taal per venster van 10 cues; het origineel wordt nooit gerepareerd of herschreven. Bron: WP-JSON B03-041.
  3. Taaktype `subtitle.qc`: zachte, instelbare leesregels (42 tekens per regel, 2 regels, leessnelheid, minimale en maximale duur, gat) en harde blokkades (structuur, taal per venster onder 90 % NL, opschoning van tags tot i/b/u/font). Bron: WP-JSON B03-041.
  4. Koppel `subtitle.inventory` aan de module Subtitles: verkeerd getagde NL-tekst wordt als NL herkend en als signaal voor F4 bewaard. Bron: WP-JSON B03-040, veld Acceptatie.
  5. Tests in de image en EVIDENCE.
- **Tests (verplicht):** in de gebouwde image (T-JL-IMAGE): `sintel_nl.srt` volledig ingelezen (26 cues) en byte-gelijk gebleven; regelafbreking geeft hooguit 2 regels van 42 tekens of markeert `te_lang` zonder tekstverlies; taalvensters 100 % NL op de NL-referenties van het corpus; alles werkt met `TranslationEnabled = false`. Negatief: (a) injectietekst (`<script>`, `onerror`) komt als platte tekst terug; (b) `pip check` en de licentie-inventaris tonen geen GPL-3.0- of AGPL-pakket en geen torch; (c) `PYTHONPATH=tools/b03-harnas python3 -m b03h guard --image <lokale-tag>` blijft groen. Exact commando voor de werkertests: ONBEKEND - eerst vaststellen met: `grep -rn "pytest" <WERKMAP>/jelly-leon/.github/workflows/jelly-leon-ci.yml`.
- **Poort:** P-jelly-leon (plugin en image) + P-INSTALLATIE.
- **Valkuilen:** V-012, V-014, V-088. Eigen: een pakket met een eigen afhankelijkheid op auditok of torch sluipt binnen zodra `--no-deps` vergeten wordt.
- **Bewijs:** B03-041 -> Bezig (Sim-getest in de image). B03-040 -> Bezig bijwerken ("taal uit tekst aanwezig"). Imagegroei in MiB in het bewijs noemen (gate 3A).
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-MANIFEST (VERPLICHT: image en SBOM wijzigen) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** de werker van golf 1 geen vastgepinde omgeving met hashes heeft; een nodig pakket alleen onder GPL-3.0 of AGPL beschikbaar is; de image door deze stap niet meer binnen de manifestresources past.

### S-G3-06 - Ondertitelsync met veiligheidstoetsen (subtitle.sync)
- **Repo:** jelly-leon | **Fase:** P4 (golf 3) | **Omvang:** groot | **Moeilijkheid:** hoog | **Zwaar:** ja (image-build achter docker-build.lock; meting achter stack.lock)
- **Werkpakketten en tests:** B03-042; JLT-22
- **Vooraf:** S-G3-05. Geen besluit nodig (BG-25 gaat over een gecorrigeerde kopie bij slechte sync en raakt alleen S-G3-13).
- **Al gedaan?** `grep -rln "subtitle.sync" <WERKMAP>/jelly-leon/plugins <WERKMAP>/jelly-leon/tools <WERKMAP>/jelly-leon/deploy` -> geen uitvoer = niet gestart. `grep -rln "ffsubsync" <WERKMAP>/jelly-leon/deploy <WERKMAP>/jelly-leon/tools` -> geen uitvoer = pakket nog niet vastgepind.
- **Lees eerst:** WP-JSON object B03-042; BOUWPLAN#F3.3.6 Synchronisatie met veiligheidstoetsen; BOUWPLAN#F3.5.3 Interne werkertaak; BOUWPLAN#F3.1.5 Gate-sets (bevroren voor het afstemmen); BOUWPLAN#F3.9.1 Testomgeving en corpus
- **Bouw:**
  1. Voeg ffsubsync 0.5.1 toe aan de werkeromgeving met `--no-deps` en hashes; altijd met `--vad webrtc`. Nooit `--serialize-speech` of `--make-test-case` op een mediapad (die schrijven naast de media). Bron: WP-JSON B03-042.
  2. Taaktype `subtitle.sync`: de spraakreeks wordt als `.npz` in de cachemap van Jelly Leon bewaard en hergebruikt; het resultaat is een nieuwe kopie in de eigen opslag, het origineel blijft byte-gelijk. Bron: BOUWPLAN#F3.5.3.
  3. Veiligheidstoetsen voor de start: nooit op een spoor zonder spraak (zxx, M&E, commentaar); minstens 20 cues en 60 s spraak; een framerate-factor alleen bij een bekend paar. Bron: BOUWPLAN#F3.3.6.
  4. Veiligheidstoetsen na afloop: score kleiner dan of gelijk aan 0 is altijd afgekeurd; kruiscontrole volgens het werkpakket; uitkomsten `andere_versie` en `niet_te_synchroniseren` worden nooit gepubliceerd. Bron: WP-JSON B03-042.
  5. Uitkomst en reden per spoor in `subtitles.db`, opvraagbaar via de dekkingsroute van S-G3-03.
  6. Meting op de bevroren testset en EVIDENCE met n, mediaan en p95.
- **Tests (verplicht):** in de image: op de testset mediaan van de restfout hooguit 100 ms en p95 hooguit 250 ms (n noemen). Negatief: (a) REFIX/VODO.C -> `andere_versie` of `niet_te_synchroniseren`, niet gepubliceerd; (b) fragment met 4 cues -> `niet_te_synchroniseren`; (c) M&E- of zxx-spoor -> geweigerd voor de start; (d) sha256 van het mediacorpus voor en na gelijk en geen nieuw bestand in een mediamap. Commando's: T-JL-IMAGE; de werkertests met het commando dat S-G3-05 heeft vastgesteld; de meting achter `flock <WERKMAP>/.lokaal/stack.lock nice -n 10`.
- **Poort:** P-jelly-leon (plugin, image bouwen en proeven) + P-INSTALLATIE.
- **Valkuilen:** V-005, V-006, V-012, V-032. Eigen: de drempels staan vast; haalt de meting ze niet, dan meldt de bouwer de gemeten waarden en past hij de testset of de drempel niet aan.
- **Bewijs:** B03-042 -> Bezig (Sim-getest, met n, mediaan, p95). JLT-22 -> Bezig. Haalt de meting de drempel niet: status Bezig met de tekst "drempel niet gehaald: <waarden>", publicatie in S-G3-08 blijft uit.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-MANIFEST (VERPLICHT: image en SBOM wijzigen) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); overige standaard
- **Stop en vraag als:** de bevroren testset of een genoemd corpusbestand ontbreekt in `<WERKMAP>/.lokaal/media-corpus`; ffsubsync alleen met extra pakketten werkt die het werkpakket verbiedt.

### S-G3-07 - Beslisregels ondertitels en MediaGuard-leesroutes
- **Repo:** jelly-leon | **Fase:** P4 (golf 3) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** B03-043; JLT-23
- **Vooraf:** S-G3-03; viewerclient B03-009 (golf 1). BG-04 is genomen (via de Hub). BG-05: zonder besluit alleen deeplinks.
- **Al gedaan?** `grep -rln "HumanSearchGraceHours" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = niet gestart. `git -C <WERKMAP>/jelly-leon ls-files plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Core/MediaGuard` -> geen uitvoer = viewerclient van golf 1 ontbreekt: STOP (op 2026-11-11 gecommit, review nog open).
- **Lees eerst:** WP-JSON object B03-043; BOUWPLAN#F3.3.7 Beslisregels: wanneer vertalen; BOUWPLAN#F3.10 MediaGuard-integratie; BOUWPLAN#10.5 MediaGuard: een viewerclient en een harde grens; `<WERKMAP>/.lokaal/plan/uit/BESLUITEN_EN_BLOKKADES.md#1.2 Besluiten uit de keuzemenu's` (BG-04)
- **Bouw:**
  1. Beslisregel per item, deterministisch en met reden: er is geen menselijke NL; NL is gewenst volgens MediaGuard (`GET /api/v1/policy/effective`, veld `audio.nl_subtitles_wanted`); de menselijke zoekroute had haar kans (`searched_at` uit `GET /api/v1/mediaserver/subtitles/missing` is minstens `HumanSearchGraceHours` oud, standaard 72); er is geen actieve sessie. Bron: BOUWPLAN#F3.3.7.
  2. In P4 start deze regel geen vertaling (`TranslationEnabled = false`); hij levert alleen de status (`wacht_op_mediaguard`, `in_wachtrij`) en de reden.
  3. Alle MediaGuard-aanroepen via de viewerclient: routewitte lijst met alleen GET; veldenwitte lijst op `/mediaserver/status`. Geen eigen HTTP-client in de module. Bron: BOUWPLAN#10.5.
  4. Fail-closed: MediaGuard onbereikbaar, 401 of 429 -> `MediaGuard: onbekend` plus een incident; afspelen en de rest van de module blijven werken; `Retry-After` wordt gevolgd. Bron: WP-JSON B03-043, veld Acceptatie.
  5. Een sleutel of token met de rol operator of admin wordt geweigerd en nergens bewaard. Geen sleutelveld op een beheerpagina (BG-04).
  6. Tests en EVIDENCE.
- **Tests (verplicht):** xUnit tegen de nagebootste MediaGuard: 71 uur oud -> niet aan de beurt, 72 uur -> wel; menselijke NL aanwezig -> nooit aan de beurt. Negatief: (a) rol operator -> geweigerd en niet opgeslagen (zoek de waarde in database en log); (b) 401, 429 en time-out -> `onbekend` plus incident, geen nieuwe poging voor `Retry-After` voorbij is; (c) het verzoeklog van de simulator bevat alleen routes van de witte lijst en geen andere hosts. Commando: T-JL-PLUGIN met `--filter "FullyQualifiedName~Subtitles"`.
- **Poort:** P-jelly-leon (plugin, volledig) + P-CONTRACT + P-VEILIG.
- **Valkuilen:** V-042, V-046, V-094.
- **Bewijs:** B03-043 -> Bezig (Sim-getest) met "NIET GEVALIDEERD: echte MediaGuard met viewerrol (delta-verzoek MG-AUTH) nodig; getest tegen simulator". JLT-23 -> Bezig.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-VEILIG (VERPLICHT: toegang tot MediaGuard en sleutelroute) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard; R-VEILIG N4
- **Stop en vraag als:** de viewerclient van golf 1 op een sleutel in Jelly Leon zelf bouwt (botst met BG-04, zie hoofdstuk 3); een benodigde MediaGuard-route niet in de witte lijst van de viewerclient staat.

### S-G3-08 - Publicatie van gesynchroniseerde kopieen en beleid voor onthouden spoorkeuzes
- **Repo:** jelly-leon | **Fase:** P4 (golf 3) | **Omvang:** groot | **Moeilijkheid:** hoog | **Zwaar:** ja (differentiele run achter stack.lock)
- **Werkpakketten en tests:** B03-047; JLT-24
- **Vooraf:** S-G3-06; BG-19 genomen (zonder besluit stopt deze stap en meldt BG-19; WP B03-047 noemt BG-19 als afhankelijkheid voor opslag en uitzetten); BG-21 (zonder besluit: `hold`).
- **Al gedaan?** `grep -rln "RememberedSelectionPolicy" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = niet gestart. `grep -rln "storage_blocked" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = padbewaking nog niet gebouwd.
- **Lees eerst:** WP-JSON object B03-047; BOUWPLAN#F3.4.1 Eigen opslag; BOUWPLAN#F3.4.4 Onthouden spoorkeuzes; BOUWPLAN#F3.4.6 Uitzetten, verwijderen en terug naar stock; BOUWPLAN#F3.9.4 Differentiele controle-run
- **Bouw:**
  1. Eerst het prototype: stel vast in welke refreshmodus Jellyfin een nieuw extern spoor oppikt zonder online metadata of ondertiteldownloads (kandidaat `MetadataRefreshMode.ValidationOnly`). Leg de uitkomst vast in `<WERKMAP>/jelly-leon/docs/platform-v2/UPSTREAM_GEDRAG.md`. Zonder veilige modus: geen publicatie bouwen, STOP. Bron: WP-JSON B03-047.
  2. Hoofdkopieen en revisies in de eigen opslag (SQLite in WAL-modus plus bestanden met sha256). Bron: BOUWPLAN#F3.4.1.
  3. Publicatie als extern spoor in het interne metadatapad van het item (`item.GetInternalMetadataPath()`), met de naam `<videonaam>.Gesynchroniseerd.<taal>.srt`: atomair schrijven, nooit overschrijven, padbewaking, nooit als standaardspoor. De naam met `Machinevertaling` hoort bij P5. Bron: WP-JSON B03-047.
  4. Ligt het metadatapad in een mediamap, dan `storage_blocked` en geen publicatie; ook met `SaveSubtitlesWithMedia = true` komen er 0 bestanden in mediamappen.
  5. `RememberedSelectionPolicy` met `hold` als standaard (geen enkele schrijfactie in gebruikersgegevens). `reset` en `remap` alleen bouwen als BG-21 dat toestaat; anders weigert de configuratieroute die waarden. Bron: BOUWPLAN#F3.4.4.
  6. Depubliceren, uitzetten en terug naar stock volgens BOUWPLAN#F3.4.6; komt er later menselijke NL, dan gelden de regels van BOUWPLAN#F3.4.3 Menselijke NL komt later. Verwijderen van een gepubliceerd bestand alleen na controle van pad, markeringstoken in de naam en sha256 tegen de hoofdkopie; anders niet verwijderen en een incident. Bij `hold`: een publicatie die een onthouden spoorkeuze naar een ander geldig spoor zou laten wijzen, gaat niet door en wacht op de beheerder (WP-JSON B03-047, veld Uitvoering). Verder uit hetzelfde veld: de beheeractie "Alles depubliceren" en `OnUninstalling` ruimen gepubliceerde kopieen op, met readback; opnieuw koppelen na een vervanging door MediaGuard, met een stroomonderbreker bij massale wezen (meer dan 5 % of meer dan 50 items: stoppen en een incident); back-up van `subtitles.db` voor elke schemamigratie.
  7. Lijst met toegestane verschillen voor de differentiele run van deze module (alleen `MediaStreamInfos` en de refreshkolommen van `BaseItems`).
  8. Tests en EVIDENCE.
- **Tests (verplicht):** xUnit: tweede publicatie overschrijft niets; naam en plaats kloppen. Negatief: (a) videonaam of symlink die buiten het metadatapad wijst -> geweigerd; (b) metadatapad in mediamap -> `storage_blocked`; (c) bij `hold` is na publiceren en depubliceren geen enkele UserData-rij veranderd; (d) differentiele run: `PYTHONPATH=tools/b03-harnas python -m b03h diffrun --image-a <stock-12.x-image> --image-b <lokale-tag> --toegestaan <lijst-van-deze-module.json> --uit <rapport.json>` toont alleen toegestane verschillen en 0 verschillen in MediaSegments, TrickplayInfos, KeyframeData en Chapters, en dezelfde run met `--negatieve-proef` vindt een opzettelijk aangebrachte wijziging wel; (e) HARDE EIS: een voortgangsmelding die tijdens de publicatie binnenkomt blijft volledig behouden (positie, gezien-status, aantal keer afgespeeld; vergelijk de UserData-rij voor en na); (f) bij `hold` en een publicatie die een onthouden keuze naar een ander spoor zou laten wijzen: geen publicatie, status "wacht op beheerder", 0 gewijzigde UserData-rijen; (g) een gepubliceerd bestand zonder markeringstoken of met een afwijkende sha256 wordt niet verwijderd en geeft een incident; (h) terugzetproef: back-up van `subtitles.db` terugzetten geeft dezelfde inhoud (aantal rijen en sha256 van de hoofdkopieen gelijk); (i) een nagebootste MediaGuard-vervanging die meer dan 5 % van de gepubliceerde items tot wees maakt, laat de stroomonderbreker afgaan: 0 verwijderde bestanden en een incident; (j) na "Alles depubliceren" staat er geen gepubliceerde kopie meer en is de readback leeg. De diffrun draait achter `flock <WERKMAP>/.lokaal/stack.lock`.
- **Poort:** P-jelly-leon (plugin, image bouwen en proeven) + P-HARDE-EIS + P-CONTRACT.
- **Valkuilen:** V-027, V-077, V-095, V-111, V-112, V-113. Eigen: een differentiele run die niets vindt bewijst pas iets als de negatieve proef wel iets vindt.
- **Bewijs:** B03-047 -> Bezig (Sim-getest; gekozen refreshmodus en beleid `hold` noemen). JLT-24 -> Bezig. JLT-26 blijft Geblokkeerd (zie S-G3-03).
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-HARDE-EIS (VERPLICHT: spoorkeuzes en gebruikersgegevens) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4 en A-HERSTEL N4; R-HARDE-EIS N4. Alleen als BG-21 `reset` of `remap` toestaat en die code in deze stap wordt gebouwd: R-HARDE-EIS N5. Winst: dit is dan de enige code in golf 3 die in gebruikersgegevens schrijft (onthouden spoorkeuzes van alle gebruikers); een fout is zonder back-up niet terug te draaien.
- **Stop en vraag als:** er geen veilige refreshmodus bestaat; de differentiele run een verschil buiten de lijst toont; iemand `reset` of `remap` wil zonder BG-21.

### S-G3-09 - Streamroutes zonder inlog: meting per client, spike en ADR
- **Repo:** jelly-leon | **Fase:** P4 (golf 3) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (server met clients achter stack.lock; emulator achter gradle.lock)
- **Werkpakketten en tests:** B03-010 (golf 3-deel: meting en keuze); JLT-63 (meetdeel)
- **Vooraf:** S-G2-90 gehaald (gate golf 2; daarin Gate golf 1 met het deel IsKid van B03-010 en de IStartupFilter-spike). Geen besluit van de gebruiker nodig voor de meting.
- **Al gedaan?** `ls <WERKMAP>/jelly-leon/docs/adr | grep -i "stream"` -> geen uitvoer = nog geen ADR. `grep -c '"id": "B03-010"' <WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json` -> lees de bestaande regel (het deel IsKid van golf 1 kan er al staan).
- **Lees eerst:** WP-JSON object B03-010; `<WERKMAP>/jelly-leon/docs/adr/ADR-0009-upstream-risicos-niet-patchen-in-p0.md`; BOUWPLAN#F1.4.5 Fail-closed; BOUWPLAN#10.14 Clientmatrix; `<WERKMAP>/jelly-leon/docs/platform-v2/CLIENT_COMPAT_MATRIX.md#1. Protocol`
- **Bouw:**
  1. Stel in de broncode vast welke stream-, ondertitel- en afbeeldingsroutes zonder inlog werken (`<WERKMAP>/jelly-leon/Jellyfin.Api/Controllers/VideosController.cs`, `AudioController.cs`, `SubtitleController.cs`; afbeeldingen: ONBEKEND - eerst vaststellen met: `grep -rln "AllowAnonymous" <WERKMAP>/jelly-leon/Jellyfin.Api/Controllers`). Bron: WP-JSON B03-010.
  2. Meet per client uit de clientmatrix welke van die URL's zonder `Authorization`-header en zonder sleutel in de URL worden opgevraagd (loggende proxy van het harnas). Bron: BOUWPLAN#10.14.
  3. Spike: een actionfilter in de plugin dat op die routes inlog eist, achter een schakelaar die standaard uit staat. Leg vast of het filter deze routes werkelijk raakt.
  4. Schrijf de ADR (nummer: het eerstvolgende vrije in `<WERKMAP>/jelly-leon/docs/adr`): pluginfilter of een kleine geregistreerde core-patch met kans op een upstream-PR; per client: blijft afspelen of breekt.
  5. Werk `UPSTREAM_GEDRAG.md` bij met het gemeten gedrag en EVIDENCE met het meetrapport.
- **Tests (verplicht):** integratie in de image met de schakelaar aan: anoniem -> 401 op `/Videos/{id}/stream`, `/Audio/{id}/stream` en `/Videos/{id}/{ms}/Subtitles/{i}/Stream.{fmt}`. Negatief: schakelaar uit -> antwoorden gelijk aan stock (T-JL-COMPAT blijft groen). Clientmeting: `PYTHONPATH=tools/b03-harnas python -m b03h clientmatrix` (opties eerst met `--help` lezen; onderdelen `web,legacy,telefoon,tv`).
- **Poort:** P-jelly-leon (plugin, image proeven, `stock-client-e2e`) + P-VEILIG.
- **Valkuilen:** V-007, V-073, V-021. Eigen: een nagebootste client die wel een header stuurt, zegt niets over de echte app.
- **Bewijs:** B03-010 -> Bezig ("meting en ADR klaar; filter volgt in S-G3-10"), met per client het resultaat. Clients die niet gemeten konden worden: "NIET GEVALIDEERD: <client> niet in de emulator te meten".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-VEILIG (VERPLICHT: authenticatie) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard; R-VEILIG N4
- **Stop en vraag als:** geen van beide routes (filter of core-patch) alle gemeten stock-clients laat afspelen: dan beslist de gebruiker (keuzemenu via de regisseur) en blijft de wijziging uit.

### S-G3-10 - Streamroutes: authenticatiefilter bouwen en met clients bewijzen
- **Repo:** jelly-leon | **Fase:** P4 (golf 3) | **Omvang:** middel | **Moeilijkheid:** hoog | **Zwaar:** ja (clienttest achter stack.lock en gradle.lock)
- **Werkpakketten en tests:** B03-010 (golf 3-deel: bouw); JLT-63; JLT-64
- **Vooraf:** S-G3-09 met een ADR die een route kiest.
- **Al gedaan?** Lees de ADR van S-G3-09 en zoek de daar genoemde klasse of patch: `grep -n "B03-010" <WERKMAP>/jelly-leon/docs/platform-v2/PATCHES.md <WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json`. Staat er alleen de spike, dan is deze stap niet gestart.
- **Lees eerst:** de ADR van S-G3-09; WP-JSON object B03-010; BOUWPLAN#10.11 Register van upstream-gedrag, patches en webhaken; BOUWPLAN#F1.5.2 Endpoints (E16)
- **Bouw:**
  1. Maak van de spike de definitieve oplossing volgens de ADR. Bij een core-patch: registreren in `PATCHES.md` met een nieuw JL-nummer en een regel in `UPSTREAM_GEDRAG.md`. Bron: BOUWPLAN#10.11.
  2. De schakelaar blijft standaard uit en kan pas aan nadat de clienttest van deze stap is geslaagd; het resultaat van die test staat in de status.
  3. Zelftest als dienst in de plugin die meldt of anonieme stream-, ondertitel- en afbeeldingsroutes worden geweigerd. S-G3-17 toont de uitkomst in E16 `GET /media/v1/watch/admin/rights-check`; S-G3-23 gebruikt haar voor `vpn_gasten`. Bron: WP-JSON B03-027.
  4. Tests en EVIDENCE.
- **Tests (verplicht):** integratie: anoniem -> 401 op de drie routes uit S-G3-09; met geldige inlog -> ongewijzigd antwoord. Negatief: (a) verlopen of ingetrokken token -> 401; (b) een token van gebruiker A op een item buiten zijn bibliotheekrechten -> geweigerd zoals upstream dat doet; (c) schakelaar uit -> T-JL-COMPAT zonder verschil. Clienttest: alle clients uit de matrix blijven afspelen met de schakelaar aan (`b03h clientmatrix`, zelfde onderdelen als S-G3-09) en `python3 tools/clients/client_compat.py hervatproef --image <lokale-tag> --soort tv --bediend fork -n 3 --uit <rapport.json>` vanuit `<WERKMAP>/jelly-leon-clients` (alleen draaien, niets wijzigen; `--image` is verplicht; het rapport buiten die repo schrijven, bijvoorbeeld in `<WERKMAP>/jelly-leon/docs/platform-v2/test-evidence/`).
- **Poort:** P-jelly-leon (plugin of server, image proeven, `stock-client-e2e`) + P-VEILIG + P-CONTRACT.
- **Valkuilen:** V-007, V-072, V-073.
- **Bewijs:** B03-010 -> Bezig (Sim-getest; per client "speelt af met filter aan"). JLT-63 en JLT-64 -> Bezig bijwerken. Slaagt de clienttest niet: schakelaar blijft uit, bewijs "wijziging uit: <client> breekt".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-VEILIG (VERPLICHT: authenticatie zelf) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4 en A-HERSTEL N4; R-VEILIG N5. Winst: dit is de inlogcontrole op de afspeelroutes zelf; een gat geeft iedereen op het netwerk alle media, een te strenge regel breekt alle stock-clients tegelijk, en beide fouten zijn in een gewone test moeilijk te zien.
- **Stop en vraag als:** de ADR een core-patch kiest die meer dan de routes uit het werkpakket raakt; een stock-client met het filter aan niet meer afspeelt.

### S-G3-11 - Kwaliteitscontrole niveau 0, 1 en 1,5 met triggers
- **Repo:** jelly-leon | **Fase:** P4 (golf 3) | **Omvang:** groot | **Moeilijkheid:** gewoon | **Zwaar:** nee (de meting op het corpus volgt in S-G3-12)
- **Werkpakketten en tests:** B03-051; JLT-30 (deel structuur); JLT-32 (deel ontbrekend spoor)
- **Vooraf:** S-G3-02. BG-23: zonder besluit steekproef voor alles en volledig alleen voor nieuw of vervangen.
- **Al gedaan?** `grep -rln "no_audio_track" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = niet gestart.
- **Lees eerst:** WP-JSON object B03-051; BOUWPLAN#F4.3.3 Detectieniveaus, ernstmodel en verificatie; BOUWPLAN#F4.5.3 Endpoints in Jelly Leon (Q2, Q3, Q4, Q7); BOUWPLAN#F4.1.5 Datasets, metrieken en drempels
- **Bouw:**
  1. Niveau 0 uit de bestaande MediaStreams, zonder het bestand te openen: geen video, geen audiospoor, alle audio 'und', ondertitel zonder taal. Bron: WP-JSON B03-051.
  2. Niveau 1: vingerafdruk (grootte plus sha256 van de eerste en laatste 4 MiB), staartcontrole met ffprobe `-read_intervals`, headerfouten. Bron: BOUWPLAN#F4.3.3.
  3. Niveau 1,5: steekproef van 3 vensters van 10 s op 10, 50 en 90 procent, altijd met het label 'steekproef, geen volledige controle'.
  4. Triggers: ItemAdded, ItemUpdated, ItemRemoved, een `ILibraryPostScanTask` en MediaGuard-events via `GET /api/v1/events/recent` (viewerclient). Alles loopt als taak via de planner van S-G3-02. Bibliotheken van het type home video's en foto's en gemengde inhoud worden zonder BG-24 niet gescand (BESLUITEN_EN_BLOKKADES.md, kop BG-24).
  5. Bevindingen met ernst en status in `quality.db`; routes Q2, Q3, Q4 en Q7. Bron: BOUWPLAN#F4.5.3.
  6. Tests en EVIDENCE.
- **Tests (verplicht):** xUnit met opgenomen ffprobe-uitvoer van de corpusbestanden: `sintel-60s-afgekapt-70pct.mkv` -> `truncated`; `sintel-60s-zonder-audio.mkv` -> `no_audio_track`; afgekapte mp4 -> `container_error`. Negatief: (a) een gezond bestand -> 0 bevindingen hoog of middel; (b) een bestand dat tijdens de controle verdwijnt -> geen crash, status onbekend; (c) Q7 door een niet-beheerder -> 403; (d) een steekproef levert nooit de uitspraak "volledig gecontroleerd"; (e) een item in een bibliotheek home video's of gemengde inhoud krijgt zonder BG-24 geen taak. Commando: T-JL-PLUGIN met `--filter "FullyQualifiedName~Quality"`.
- **Poort:** P-jelly-leon (plugin, volledig) + P-CONTRACT.
- **Valkuilen:** V-003, V-005, V-051.
- **Bewijs:** B03-051 -> Bezig (Unit-getest; "recall op T-QC volgt in S-G3-12"). JLT-30 en JLT-32 -> Bezig met "deel".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** een genoemd corpusbestand ontbreekt; een controle alleen kan door het mediabestand te openen voor schrijven.

### S-G3-12 - Kwaliteitscontrole niveau 2 (volledige decode) en de meting op het corpus
- **Repo:** jelly-leon | **Fase:** P4 (golf 3) | **Omvang:** groot | **Moeilijkheid:** hoog | **Zwaar:** ja (decode en meting in de image achter stack.lock; exclusief meetslot)
- **Werkpakketten en tests:** B03-052; JLT-30; JLT-31; JLT-36 (meting)
- **Vooraf:** S-G3-11. BG-23 (hele bibliotheek alleen na dat besluit).
- **Al gedaan?** `grep -rln "decode_error" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = niet gestart.
- **Lees eerst:** WP-JSON object B03-052; BOUWPLAN#F4.3.3 Detectieniveaus; BOUWPLAN#F4.9.5 Prestaties (meetprotocol); BOUWPLAN#F4.1.5 Datasets, metrieken en drempels; BOUWPLAN#10.15 Baselinemeting standaard Jellyfin en meetprotocol
- **Bouw:**
  1. Bereik: standaard 'nieuw en op verzoek' (hooguit 24 uur nieuw, of door MediaGuard vervangen); de hele bibliotheek alleen als BG-23 dat toestaat. Bron: WP-JSON B03-052.
  2. Overslaan als de vrijgavecontrole van MediaGuard al geslaagd is (`GET /api/v1/quarantine/{id}`, `/api/v1/recovery/transactions`, via de viewerclient).
  3. CPU-decode in brokken van 10 minuten met checkpoint; stoppen en hervatten volgens de planner.
  4. Audiocontroles (silencedetect, astats, ebur128) en beeldcontroles (blackdetect, freezedetect op 320 px breed). Bron: BOUWPLAN#F4.3.3.
  5. Bevindingen met tijdcode; `decode_error` met tijdcode binnen 1 s.
  6. Meting op T-QC en de negatieve sets en op het budget (JLT-36) met het meetprotocol: exclusief meetslot, minstens 3 runs, A/B.
  7. EVIDENCE met n, recall, Wilson-ondergrens per klasse.
- **Tests (verplicht):** in de image: recall per codecklasse met Wilson-95 %-ondergrens minstens 0,80 bij n van minstens 30 (anders noemt het bewijs het een smoke-gate); audioklassen n minstens 20 en ondergrens minstens 0,70. Negatief: (a) 0 bevindingen hoog of middel op N-QC en N-QC-rommelig; (b) transcode-fps van een live stream wijkt met de controle aan hooguit 5 % af; (c) PlaybackStart tijdens een decode -> gestopt binnen 5 s, geen achtergebleven ffmpeg-proces; (d) sha256 van het corpus voor en na gelijk. Commando's: T-JL-IMAGE, daarna de meting achter `flock <WERKMAP>/.lokaal/stack.lock nice -n 10`; voor het transcode-deel vanuit `<WERKMAP>/jelly-leon`: `PYTHONPATH=tools/b03-harnas python -m b03h baseline --metingen transcode --runs 3 --image <lokale-tag> --label definitief-forkbasis --uit <rapport.json>` (opties staan in `tools/b03-harnas/b03h/baseline.py`; controleer ze daar voor gebruik). De recall-meting per klasse heeft nog geen harnasonderdeel: de bouwer voegt die toe en schrijft het commando in het README van het harnas.
- **Poort:** P-jelly-leon (plugin, image bouwen en proeven).
- **Valkuilen:** V-005, V-006, V-009, V-014, V-032. Eigen: een run is ongeldig (telt niet mee, en is niet "mislukt") als de 1-minuut-loadavg vóór de run boven 4 ligt, als andere processen meer dan 4 kernen gebruiken of als een ander zwaar slot actief is: de lastgrens `LASTGRENS` (standaard 4.0) van het harnas `tools/b03-harnas/b03h/meetslot.py`, functie `beoordeel`, zoals ook `<WERKMAP>/jelly-leon/tools/b03-harnas/README.md` en BOUWPLAN#F1.1.3, #F5.1.3 en #F6.1.3 zeggen ("loadavg(1 min) > 4"). Gebruik de functies van het harnas en zet `B03_LASTGRENS` niet hoger. BOUWPLAN#F4.9.5 zegt "loadavg > aantal toegewezen CPU's + 1"; de bouwer noemt in het bewijs welke grens gold en hoeveel CPU's de container had.
- **Bewijs:** B03-052 -> Bezig (Sim-getest, met n en ondergrens per klasse). B03-051 -> bijwerken met de gemeten recall. JLT-30, JLT-31, JLT-36 -> Bezig. Klassen met te weinig n: "smoke-gate, n=<n>".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4 en A-HERSTEL N4; overige standaard
- **Stop en vraag als:** de testsets T-QC, N-QC of N-QC-rommelig niet in het corpus staan; de machine het meetslot niet vrij krijgt (dan wachten, niet meten onder belasting).

### S-G3-13 - Kwaliteitscontrole niveau 3: teksttaal en ondertitelsync via de F3-toolkit
- **Repo:** jelly-leon | **Fase:** P4 (golf 3) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** B03-054; JLT-32; JLT-33
- **Vooraf:** S-G3-12 en S-G3-06 (toolkit en syncmeter). BG-25: zonder besluit alleen melden; deze stap bouwt geen gecorrigeerde kopie (ook niet op verzoek). Een gecorrigeerde kopie is pas een vervolgstap na het besluit.
- **Al gedaan?** `grep -rln "toolkit_unavailable" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = niet gestart.
- **Lees eerst:** WP-JSON object B03-054; BOUWPLAN#F4.3.3 Detectieniveaus; BOUWPLAN#F4.3.6 Optionele lokale modellen (standaard uit) en terugval; BOUWPLAN#F3.5.3 Interne werkertaak
- **Bouw:**
  1. Niveau 3 als afnemer van de toolkit van F3: geen eigen Python-omgeving, geen tweede syncmeter. Ontbreekt de toolkit: uitkomst 'onbekend' met reden `toolkit_unavailable`. Bron: WP-JSON B03-054.
  2. Jobtype `quality.dialogue_contrast` via de planner.
  3. Teksttaal tegen tagtaal: alleen bij minstens 100 tekens en zekerheid van minstens 0,9 -> `subtitle_language_mismatch`.
  4. Sync: |offset| van minstens 0,5 s of factor buiten 1 plus of min 0,005 = ernst middel (`subtitle_offset`, `subtitle_framerate_drift`); meer dan 30 s = `subtitle_wrong_version`.
  5. Audiotaal zonder spraakherkenning: uitkomst 'onbekend' met reden `stt_disabled` (spraakherkenning hoort bij P5).
  6. Tests en EVIDENCE.
- **Tests (verplicht):** met het corpus: `tos-120s-verkeerde-taaltags` -> `subtitle_language_mismatch`; offsetfout hooguit 0,10 s; framerate-factor 0,959 binnen 0,005. Negatief: (a) Engelse audio met tag nld -> 'onbekend' (`stt_disabled`), geen bevinding; (b) toolkit uitgeschakeld -> `toolkit_unavailable`, geen crash; (c) tekst korter dan 100 tekens -> geen taaluitspraak. Commando: T-JL-PLUGIN met `--filter "FullyQualifiedName~Quality"`; de werkerdelen met het commando van S-G3-05.
- **Poort:** P-jelly-leon (plugin, volledig).
- **Valkuilen:** V-003, V-005.
- **Bewijs:** B03-054 -> Bezig (Sim-getest). JLT-32 -> Bezig met "STT-deel volgt in P5". JLT-33 -> Bezig.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** de toolkit van S-G3-05 en S-G3-06 geen aanroep biedt die de module kan gebruiken zonder een tweede omgeving.

### S-G3-14 - Bewijs per bevinding, verificatierun, feedback en onderdrukkingen
- **Repo:** jelly-leon | **Fase:** P4 (golf 3) | **Omvang:** groot | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** B03-055; JLT-34
- **Vooraf:** S-G3-13. BG-24: zonder besluit miniaturen uit (Q5b geeft 501 volgens de foutcatalogus), label uit, "Meld een probleem" uit, home video's en gemengde inhoud niet gescand.
- **Al gedaan?** `grep -rln "not_reproducible" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = niet gestart.
- **Lees eerst:** WP-JSON object B03-055; BOUWPLAN#F4.3.3 Detectieniveaus, ernstmodel en verificatie; BOUWPLAN#F4.5.3 Endpoints in Jelly Leon (Q5, Q5b, Q6, Q8, Q9, Q12); BOUWPLAN#F4.4.5 Privacy en zichtbaarheid
- **Bouw:**
  1. Bewijs per bevinding: tijdvensters, meetwaarden, logfragment zonder paden, versies, drempels, probe-hash, vingerafdruk en spoorsleutel. Route Q5. Bron: WP-JSON B03-055.
  2. Miniaturen standaard uit. Alleen als BG-24 "op verzoek" kiest: via Q5b, alleen voor een beheerder na een klik, hooguit 3, 320 px, 90 dagen, weg bij "opgelost"; nooit voor home video's; nooit naar de Hub. Zonder dat besluit geeft Q5b 501.
  3. Verificatierun: venster van plus en min 10 s met `-threads 1`; uitkomsten `not_reproducible` en `storage_read_error`. Bron: BOUWPLAN#F4.3.3.
  4. Feedback Q6 ('bevestigd' of 'onterecht', met bereik bestand, serie of bibliotheek; Idempotency-Key en If-Match) en onderdrukkingen Q9.
  5. Automatisch verlagen van de ernst bij lage precisie van een detector (regel uit het werkpakket).
  6. Q8 "Meld een probleem" alleen als `Quality.UserReports` aan staat (BG-24); anders 501 volgens de foutcatalogus. Export en import Q12.
  7. Tests en EVIDENCE.
- **Tests (verplicht):** xUnit: herhaalde Idempotency-Key op Q6 -> zelfde antwoord, een rij; onderdrukking verbergt de bevinding en is terug te draaien. Negatief: (a) bewijs en log bevatten geen pad en geen titel; (b) miniatuur voor een home video -> geweigerd; (c) Q6 zonder If-Match -> geweigerd; (d) valse positieven op N-QC blijven 0 na feedback; (e) Q5 door een gewone gebruiker -> 403. Commando: T-JL-PLUGIN met `--filter "FullyQualifiedName~Quality"`.
- **Poort:** P-jelly-leon (plugin, volledig) + P-CONTRACT.
- **Valkuilen:** V-046, V-063, V-094.
- **Bewijs:** B03-055 -> Bezig (Unit-getest). JLT-34 -> Bezig.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-VEILIG (VERPLICHT: rechten en wat een gewone gebruiker of de Hub van bewijs mag zien) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard; R-VEILIG N4
- **Stop en vraag als:** het bewijs alleen bruikbaar is met een pad of titel erin (dan beslist de gebruiker; standaard blijft het eruit).

### S-G3-15 - Quality en MediaGuard: alleen lezen, geen dubbel werk, herstel als deeplink
- **Repo:** jelly-leon | **Fase:** P4 (golf 3) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** B03-056; JLT-37; EX06; EX16
- **Vooraf:** S-G3-14; viewerclient B03-009. BG-04 genomen (via de Hub). BG-05: zonder besluit alleen de deeplink `handmatig_in_mediaguard`.
- **Al gedaan?** `grep -rln "handmatig_in_mediaguard" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = niet gestart. `grep -rln "ambiguous_mg_item" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> idem.
- **Lees eerst:** WP-JSON object B03-056; BOUWPLAN#F4.10 MediaGuard-integratie (F4.10.1 tot en met F4.10.3); BOUWPLAN#F4.5.4 Gedeelde uitbreiding van B03-009: herstelverzoek; BOUWPLAN#10.5 MediaGuard: een viewerclient en een harde grens
- **Bouw:**
  1. Gebruik de viewerclient: rol viewer, rolcontrole bij de start en elk uur, fail-closed. Toegestane routes: alleen GET plus `POST /api/v1/audio/inspect`. Bron: WP-JSON B03-056.
  2. Het MediaGuard-adres mag alleen een prive-, ULA- of loopback-adres zijn; redirects worden niet gevolgd.
  3. Koppeling van een Jelly Leon-item aan een MediaGuard-item; bij twijfel `ambiguous_mg_item` en geen actie.
  4. Herstelverzoek: in v1 altijd de status `handmatig_in_mediaguard` met een deeplink; route Q11 voor de lijst. Bron: BOUWPLAN#F4.10.2.
  5. Foutgedrag: MediaGuard 401 -> connectorstatus unknown plus incident (EX16); noodstop -> 409 `emergency_stop_active` (EX06); 429 -> `Retry-After` volgen.
  6. De velden sessions, hold.reason, actions, tests en encoder.running komen niet in log of database.
  7. Tests en EVIDENCE.
- **Tests (verplicht):** tegen de simulator met een loggende proxy: 0 muterende aanroepen naar MediaGuard over de hele testreeks. Negatief: (a) sleutel met rol operator -> geweigerd en niet opgeslagen; (b) 401 -> unknown plus incident; (c) noodstop -> 409 `emergency_stop_active`; (d) 429 -> geen aanroep voor `Retry-After` voorbij is; (e) een adres buiten de toegestane bereiken of een redirect -> geweigerd; (f) de verboden velden staan nergens in log of database (zoek op de waarden uit de simulator). Commando: T-JL-PLUGIN met `--filter "FullyQualifiedName~Quality"`.
- **Poort:** P-jelly-leon (plugin, volledig) + P-CONTRACT + P-VEILIG + P-HARDE-EIS.
- **Valkuilen:** V-042, V-046, V-094. Eigen: een test die alleen de eigen client naspeelt, bewijst niet dat er niets muteert; tel de verzoeken aan de kant van de simulator.
- **Bewijs:** B03-056 -> Bezig (Sim-getest) met "NIET GEVALIDEERD: echte MediaGuard met viewerrol nodig (delta-verzoek MG-AUTH); getest tegen simulator". JLT-37, EX06, EX16 -> Bezig (alleen het Jelly Leon-deel; noem dat in de regel).
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-VEILIG (VERPLICHT: sleutelroute en adrescontrole) -> R-HARDE-EIS (VERPLICHT: MediaGuard-voortgang mag nooit veranderen) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard; R-VEILIG N4; R-HARDE-EIS N4
- **Stop en vraag als:** het werkpakket een sleutel in de geheimenmap van Jelly Leon vraagt terwijl BG-04 "via de Hub" zegt en de viewerclient van golf 1 dat nog niet doet (zie hoofdstuk 3, "Spanning BG-04"); EX06 of EX16 volgens `<WERKMAP>/ai-server-manager/docs/platform-v2/EVIDENCE.json` een andere eigenaar heeft dan jelly-leon.

### S-G3-16 - Pluginpagina "Mediakwaliteit" voor beheerders
- **Repo:** jelly-leon | **Fase:** P4 (golf 3) | **Omvang:** groot | **Moeilijkheid:** gewoon | **Zwaar:** ja (image en browsertest achter stack.lock)
- **Werkpakketten en tests:** B03-057 (serverdeel: pluginpagina); EX36 (serverdeel); JLT-38 (deel pluginpagina)
- **Vooraf:** S-G3-15. BG-24 (label en "Meld een probleem" standaard uit).
- **Al gedaan?** `grep -rln "IHasWebPages" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> lees welke pagina's al geregistreerd zijn. `grep -rli "Mediakwaliteit" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = niet gestart.
- **Lees eerst:** WP-JSON object B03-057; BOUWPLAN#F4.6.1 jelly-leon-web (upstream-Jellyfin-stijl, geen platform-ontwerptaal); BOUWPLAN#F4.5.3 Endpoints in Jelly Leon; BOUWPLAN#F4.9.4 Clientmatrix (alleen UI)
- **Bouw:**
  1. Pluginpagina via `IHasWebPages`, alleen voor beheerders, bruikbaar in Modern en Legacy, zonder web-patch. Vormgeving volgt upstream Jellyfin (buiten Peil). Bron: WP-JSON B03-057.
  2. Tabbladen Overzicht, Bevindingen, Wachtrij, Onderdrukkingen, Instellingen en Over, gevoed door Q1, Q3, Q4, Q9, Q10 en Q13.
  3. Elke toestand zichtbaar: laden, leeg, fout, module uit, MediaGuard onbekend, steekproef-label.
  4. Nederlandse teksten; geen paden of titels in foutmeldingen.
  5. Browsertest in het harnas (`<WERKMAP>/jelly-leon/tools/b03-harnas/playwright`) en EVIDENCE.
- **Tests (verplicht):** Playwright in Chromium, Firefox en WebKit, Modern en Legacy, op 360 en 1440 px breed: elk tabblad laadt en toont gegevens uit een gevulde testdatabase. Negatief: (a) niet-beheerder -> 403 op de pagina en op de routes; (b) een item dat de gebruiker niet mag zien -> 404 en geen label (EX36); (c) module uit -> de pagina zegt dat en doet geen verzoeken in een lus. Commando: het harnas heeft nog geen onderdeel voor pluginpagina's; de bouwer voegt de test toe aan `<WERKMAP>/jelly-leon/tools/b03-harnas/playwright/harnas.mjs` (lees eerst dat bestand en `package.json` ernaast; het onderdeel `web` van `b03h clientmatrix` is het voorbeeld) en schrijft het exacte commando in het README van het harnas. Let op: het harnasonderdeel `legacy` is de proef met een derden-client, niet de weergave Legacy. Draaien achter `flock <WERKMAP>/.lokaal/stack.lock`.
- **Poort:** P-jelly-leon (plugin, image bouwen en proeven, job `b03-harnas`) + P-CONTRACT.
- **Valkuilen:** V-058, V-060, V-063, V-065, V-067.
- **Bewijs:** B03-057 -> Bezig (Sim-getest; "webdeel label volgt in S-G3-25"). EX36 -> Bezig (deel Jelly Leon). JLT-38 -> Bezig met "deel pluginpagina; clientmatrix en Hub-kaart volgen in golf 4".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK (geen A-ONTWERP en geen R-ONTWERP: pluginpagina's vallen buiten Peil)
- **Niveau:** standaard
- **Stop en vraag als:** de pagina alleen werkt met een wijziging in jelly-leon-web (dan hoort dat deel in de web-baan, S-G3-25).

### S-G3-17 - Watch Together: zichtbaarheid, uitnodigingen en deelnemersbeheer
- **Repo:** jelly-leon | **Fase:** P4 (golf 3) | **Omvang:** groot | **Moeilijkheid:** hoog | **Zwaar:** nee (plugin-build en -test achter docker-build.lock)
- **Werkpakketten en tests:** B03-022; JLT-05 (deel privacy en uitnodigingen); JLT-09 (deel: geen gewijzigde UserPolicy)
- **Vooraf:** WT-1-gate geslaagd volgens het rapport van S-G2-90 (B03-021). BG-11 genomen: zonder besluit start deze stap NIET (privacykeuze; zie hoofdstuk 3). De standaardzichtbaarheid is de stand die de gebruiker koos.
- **Al gedaan?** `grep -rln "InviteNotifier" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = niet gestart. `grep -rln "wt_audit" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = audit nog niet gebouwd. `grep -rln "watch/capabilities" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = module van golf 2 ontbreekt: STOP.
- **Lees eerst:** WP-JSON object B03-022; BOUWPLAN#F1.5.2 Endpoints (E2 tot en met E8, E16); BOUWPLAN#F1.5.3 Schema's; BOUWPLAN#F1.4.4 Privacy; BOUWPLAN#F1.8 Bouwfasen (regel WT-2)
- **Bouw:**
  1. Zichtbaarheid per groep `open`, `huishouden` of `privé` (standaard = de keuze uit BG-11; kies nooit zelf) als filter in ListGroups, GetGroup en JoinGroup. Niet zichtbaar = hetzelfde antwoord als niet bestaand. Bron: WP-JSON B03-022.
  2. Route E3 `PUT /media/v1/watch/groups/{groupId}/meta` voor eigenaar of beheerder, met Idempotency-Key en If-Match. Bron: BOUWPLAN#F1.5.2.
  3. Uitnodigingen E4 tot en met E7: alleen bestaande, niet-verborgen huishoudgebruikers; levensduur 120 minuten; een enkele generieke reden `niet_uitnodigbaar`. Een openstaande uitnodiging maakt de groep zichtbaar in de gewone SyncPlay-lijst van de genodigde; joinen via upstream `POST /SyncPlay/Join` geldt als accepteren.
  4. Melding aan de genodigde via DisplayMessage met lege controllingSessionId, uitsluitend vanuit de klasse `InviteNotifier`; een analyzer-regel weigert dit op elke andere plek.
  5. Route E8: deelnemer verwijderen via upstream LeaveGroup. Audit in `wt_audit`, gepseudonimiseerd bij UserDeleted.
  6. Route E16 `GET /media/v1/watch/admin/rights-check`: een alleen-lezen rechtencontrole. De module wijzigt nooit UserPolicy; gastaccounts maakt de beheerder zelf.
  7. Lijst met toegestane verschillen voor de differentiele run van deze module (geen enkele wijziging in UserPolicy).
  8. Tests en EVIDENCE.
- **Tests (verplicht):** xUnit en integratie over de volledige rollenmatrix (eigenaar, lid, genodigde, niet-genodigde huishoudgebruiker, gast, verborgen gebruiker, beheerder): 0 lekken van groep of deelnemersnamen via `GET /SyncPlay/List` en `GET /SyncPlay/{id}`, ook bij een lege wachtrij. Negatief: (a) JoinGroup op een niet-zichtbare groep geeft hetzelfde antwoord als op een niet-bestaande groep; (b) verlopen of ingetrokken uitnodiging geeft geen toegang; (c) een verborgen of niet-bestaande gebruiker uitnodigen geeft dezelfde `niet_uitnodigbaar`; (d) analyzer: een Send-commando met lege controllingSessionId buiten `InviteNotifier` breekt de build; (e) E3 zonder If-Match wordt geweigerd. Commando: T-JL-PLUGIN met `--filter "FullyQualifiedName~Watch"`, daarna volledig.
- **Poort:** P-jelly-leon (plugin, volledig) + P-CONTRACT + P-VEILIG + P-HARDE-EIS.
- **Valkuilen:** V-003, V-046, V-055, V-111. Eigen: een filter op alleen de eigen routes laat de upstream-routes `/SyncPlay/*` lekken; test daarom altijd via de upstream-routes.
- **Bewijs:** B03-022 -> Bezig (Unit-getest; "stock-web en officiele apps volgen in S-G3-27 en S-G4-30"). JLT-05 -> Bezig met "deel". JLT-06 -> Geblokkeerd: "NIET GEVALIDEERD (echte NAS): echte apparaten en echte Tailscale nodig; zie STAPPEN_P6.md".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-VEILIG (VERPLICHT: zichtbaarheid en rechten) + R-HARDE-EIS (tegelijk; VERPLICHT: de stap raakt gebruikers, UserPolicy en de pseudonimisering bij UserDeleted; de lijst met toegestane verschillen moet UserPolicy uitsluiten) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4; R-HARDE-EIS N4; overige standaard
- **Stop en vraag als:** WT-1 de core-patch-route koos en het filter niet in de decorator kan; een upstream-route de groep toch toont en dat alleen met een nieuwe core-patch te dichten is.

### S-G3-18 - Watch Together: kinderprofiel en ouderlijk toezicht
- **Repo:** jelly-leon | **Fase:** P4 (golf 3) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** B03-023; JLT-05 (deel kinderprofiel)
- **Vooraf:** S-G3-17. BG-03 (definitie van een kinderprofiel) hoort voor golf 1 genomen te zijn.
- **Al gedaan?** `grep -rn "IsKid" <WERKMAP>/jelly-leon/plugins/JellyLeon/src | head` -> geen treffer in `Core/` = de bouwsteen van golf 1 ontbreekt: STOP. `grep -rln "AccessSchedules" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = niet gestart.
- **Lees eerst:** WP-JSON object B03-023; WP-JSON object B03-010 (deel IsKid); BOUWPLAN#F1.4.5 Fail-closed; BOUWPLAN#F1.9.5 Negatief en veiligheid; BOUWPLAN#F1.7 Configuratieopties
- **Bouw:**
  1. Gebruik alleen de gemeenschappelijke `IsKid(user)`; geen eigen definitie in de module. Bron: WP-JSON B03-023.
  2. Hergebruik de upstream UserPolicy (MaxParentalRating, BlockedTags, SyncPlayAccess, AccessSchedules, IsHidden) en de wachtrijcontrole van upstream; de module schrijft er nooit in.
  3. Aanvullend: een kind ziet en joint alleen groepen en uitnodigingen van ingestelde verzorgers of beheerders, kan niet uitnodigen, heeft chat standaard uit en doet nooit mee in een groep met een VPN- of externe deelnemer.
  4. Toegangstijden elke 60 s bewaken tijdens een groep; buiten het schema: upstream LeaveGroup plus een melding.
  5. Een weigering toont het kind nooit de titel.
  6. E16 waarschuwt bij een kind met het recht groepen te maken en adviseert `SyncPlayAccess=None` voor kinderen zolang de decorator niet actief is.
  7. De Hub-rol kind krijgt 403 op alle connectorroutes van Watch Together.
  8. Tests en EVIDENCE.
- **Tests (verplicht):** xUnit met een nepklok. Negatief (allemaal verplicht): (a) in geen scenario krijgt het kind via een groep een titel boven zijn leeftijdsgrens of met een geblokkeerde tag; (b) een wachtrij met zo'n titel wordt geweigerd en het antwoord bevat de titel niet; (c) kind in een groep met een VPN- of externe deelnemer -> geweigerd; (d) E4 door een kind -> geweigerd; (e) buiten de toegangstijden verlaat het kind de groep binnen 90 s; (f) het kind ziet geen groepen of namen van niet-verzorgers; (g) met een geforceerd inactieve decorator meldt E16 het advies. Commando: T-JL-PLUGIN met `--filter "FullyQualifiedName~Watch"`.
- **Poort:** P-jelly-leon (plugin, volledig) + P-CONTRACT + P-VEILIG.
- **Valkuilen:** V-046, V-050, V-055.
- **Bewijs:** B03-023 -> Bezig (Unit-getest). JLT-05 -> Bezig ("chat-deel voorwaardelijk, zie S-G4-10").
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-VEILIG (VERPLICHT: rechten van kinderprofielen) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard; R-VEILIG N4
- **Stop en vraag als:** `IsKid(user)` geen vastgelegde definitie heeft (BG-03); de instelling "verzorgers" niet in BOUWPLAN#F1.7 staat en dus zou moeten worden bedacht.

### S-G3-19 - Watch Together: haperbeleid zonder IgnoreWait, met racetest
- **Repo:** jelly-leon | **Fase:** P4 (golf 3) | **Omvang:** middel | **Moeilijkheid:** hoog | **Zwaar:** ja (hapermeting met server en browsers achter stack.lock)
- **Werkpakketten en tests:** B03-025 (deel haperbeleid); JLT-03
- **Vooraf:** S-G3-17; planner B03-018 (golf 1). BG-13: zonder besluit is `wachten` (upstream, 30 s) de standaard per groep; `doorgaan_na_wachttijd` wordt gebouwd en getest maar staat dan niet standaard aan (BESLUITEN_EN_BLOKKADES.md, kop BG-13).
- **Al gedaan?** `grep -rln "LaggardGraceSeconds" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = niet gestart.
- **Lees eerst:** WP-JSON object B03-025; BOUWPLAN#F1.8 Bouwfasen (regel WT-4); BOUWPLAN#F1.9.1 Unit; BOUWPLAN#F1.9.3 E2E met het echte corpus; `<WERKMAP>/jelly-leon/docs/platform-v2/UPSTREAM_GEDRAG.md`
- **Bouw:**
  1. Haperbeleid per groep (in E3): `wachten` (gedrag van upstream, 30 s) of `doorgaan_na_wachttijd` (wachttijd standaard 10 s, bereik 3 tot 25 s; instelling `LaggardGraceSeconds`). Welk beleid een nieuwe groep krijgt volgt BG-13; zonder besluit `wachten`. Bron: WP-JSON B03-025.
  2. De module stuurt nooit een `IgnoreWaitGroupRequest`.
  3. Route 1: na de wachttijd stuurt de decorator namens een deelnemer die klaar is een `UnpauseGroupRequest` via `ISyncPlayManager.HandleRequest`, en alleen als alle vier gelden: de groep staat in Waiting; de bedoeling "spelen" is positief afgeleid (geen Pause of Stop sindsdien); onder een groepsslot dat ook de doorgegeven clientverzoeken van die groep serialiseert; na een hercontrole vlak ervoor. Bij twijfel niets doen (upstream wacht 30 s).
  4. Racetest als xUnit: minstens 200 gerandomiseerde reeksen met Pause, Seek, NextItem, Leave en de 30 s-timer van upstream tijdens de wachttijd; de seed staat in het rapport.
  5. Regel in `UPSTREAM_GEDRAG.md` voor het upstream-gedrag waarop route 1 steunt.
  6. Hapermeting en EVIDENCE.
- **Tests (verplicht):** racetest: 0 keer hervatten tegen een waargenomen Pause in. Negatief: (a) het verzoeklog bevat 0 IgnoreWait-verzoeken van de module; (b) beleid `wachten` gedraagt zich als upstream; (c) deelnemer verlaat de groep tijdens de wachttijd -> geen fout, geen hervatting namens hem. Meting in de image (achter `flock <WERKMAP>/.lokaal/stack.lock nice -n 10`): deelnemer gesmoord op 1,5 Mbit/s bij Sintel 1080p -> de groep staat ten hoogste `LaggardGraceSeconds` + 2 s stil en de deelnemer speelt binnen 20 s na herstel weer binnen 500 ms van de groep, over minstens 10 haperingen per beleid. Het meetharnas is dat van B03-020 (golf 2): ONBEKEND - eerst vaststellen met: `grep -n '"id": "B03-020"' -A 12 <WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json`.
- **Poort:** P-jelly-leon (plugin, volledig; image proeven).
- **Valkuilen:** V-003, V-009, V-032, V-057. Eigen: een racetest zonder vastgelegde seed is niet te herhalen en telt niet.
- **Bewijs:** B03-025 -> Bezig (Sim-getest; "deel haperbeleid; capaciteitsadvies volgt in S-G4-09"; "A310/UHD 770 NIET GEVALIDEERD (hardware)"). JLT-03 -> Bezig met aantal reeksen, seed en gemeten stilstand.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); overige standaard
- **Stop en vraag als:** route 1 de racetest niet haalt. Dan beslist de gebruiker (keuzemenu via de regisseur): route 2 (een kleine geregistreerde core-patch voor de wachttijd, serverbreed) of het beleid niet aanbieden. De bouwer kiest dat niet zelf.

### S-G3-20 - Watch Together: volgmodus voor clients zonder SyncPlay (serverdeel)
- **Repo:** jelly-leon | **Fase:** P4 (golf 3) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** B03-026 (serverdeel); JLT-07 (unitdeel)
- **Vooraf:** S-G3-17; S-G3-32 (WP-JSON B03-026 noemt B03-003 als afhankelijkheid). BG-10 genomen: zonder besluit start deze stap NIET (BESLUITEN_EN_BLOKKADES.md, kop BG-10). Beide opties bevatten geen clientpatch voor de volgmodus zelf; de clientpatch is S-G3-26.
- **Al gedaan?** `grep -rln "FollowController" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = niet gestart.
- **Lees eerst:** WP-JSON object B03-026; BOUWPLAN#F1.5.2 Endpoints (E11, E12, E13); BOUWPLAN#F1.6.2 Andere clients; BOUWPLAN#F1.9.5 Negatief en veiligheid
- **Bouw:**
  1. Routes E11 `GET /media/v1/watch/sessions/followable`, E12 `POST .../groups/{groupId}/followers` en E13 `DELETE .../followers/{sessionId}`; alleen een eigen sessie van dezelfde gebruiker met SupportsMediaControl. Bron: BOUWPLAN#F1.5.2.
  2. Alleen de klasse `FollowController` spiegelt Play, Pause, Unpause, Seek en volgende aflevering via `ISessionManager.SendPlayCommand` en `SendPlaystateCommand`, met de eigen sessie van de aanvrager als controllingSessionId. Nooit `EnableRemoteControlOfOtherUsers`. Bron: WP-JSON B03-026.
  3. Eindigt de controlerende sessie, dan stopt het volgen (status gestopt); nooit terugvallen op een lege controllingSessionId (analyzer-regel).
  4. Positie uit de voortgangsmeldingen; correctie met een seek boven de tolerantie (standaard 2 s), hooguit 1 keer per 15 s.
  5. Wisselgevaar op Android TV (Pause en Unpause wisselen beide): toestandscontrole, een herhaling, daarna status `niet_synchroon` en stoppen.
  6. Label "Volgen (±2 s)" in de diagnose (E9).
  7. Tests en EVIDENCE.
- **Tests (verplicht):** xUnit met een nagebootste sessiebeheerder: de vijf acties worden gespiegeld; hooguit 1 correctie per 15 s. Negatief: (a) een sessie van een andere gebruiker koppelen -> 403; (b) controlerende sessie weg -> status gestopt en geen enkel commando met lege controllingSessionId; (c) wisselgeval -> na een herhaling `niet_synchroon`, geen lus (tel de commando's); (d) een sessie zonder SupportsMediaControl staat niet in E11; (e) de kinderregels van S-G3-18 gelden ook via de volgmodus. Commando: T-JL-PLUGIN met `--filter "FullyQualifiedName~Watch"`.
- **Poort:** P-jelly-leon (plugin, volledig) + P-CONTRACT + P-VEILIG.
- **Valkuilen:** V-003, V-055.
- **Bewijs:** B03-026 -> Bezig (Unit-getest; "emulatorbewijs volgt in S-G3-21"; "Swiftfin NIET GEVALIDEERD (Mac/Xcode); echte tv's NIET GEVALIDEERD (hardware)").
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-VEILIG (VERPLICHT: besturen van andermans sessie moet onmogelijk zijn) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard; R-VEILIG N4
- **Stop en vraag als:** het spiegelen alleen lukt met `EnableRemoteControlOfOtherUsers` of met een lege controllingSessionId.

### S-G3-21 - Volgmodus bewijzen in de Android TV-emulator
- **Repo:** jelly-leon | **Fase:** P4 (golf 3) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (emulator in een container met 4 GiB, een tegelijk; eerst stack.lock, dan gradle.lock)
- **Werkpakketten en tests:** B03-026 (emulatorbewijs); JLT-07
- **Vooraf:** S-G3-20 (en dus BG-10 genomen); een lokale image met S-G3-20 erin (T-JL-IMAGE).
- **Al gedaan?** `ls <WERKMAP>/jelly-leon/docs/platform-v2/test-evidence | grep -i "jlt-07\|volg"` -> geen uitvoer = geen bewijs. `grep -rn "followers" <WERKMAP>/jelly-leon/tools/b03-harnas --include=*.py -l` -> geen uitvoer = harnasonderdeel niet gestart.
- **Lees eerst:** `<WERKMAP>/jelly-leon/tools/b03-harnas/README.md`; `<WERKMAP>/jelly-leon/tools/b03-harnas/b03h/android.py` (de regels voor de emulator staan bovenaan het bestand); WP-JSON object B03-026, veld Acceptatie; TEST-JSON rij JLT-07; `<WERKMAP>/jelly-leon/docs/platform-v2/CLIENT_COMPAT_MATRIX.md#3. Clientmatrix-rooktest`
- **Bouw:**
  1. Een harnasonderdeel dat een webgroep start en een Android TV-sessie koppelt via E12; hergebruik de emulatorklasse uit `b03h/android.py` (container met toegang tot KVM, 4 GiB, een emulator tegelijk).
  2. Eerst de stock-app androidtv 0.19.x (versie en sha256 van het pakket in het bewijs), daarna de Jelly Leon-build uit jelly-leon-clients (alleen gebruiken, daar niets wijzigen).
  3. Positieverschil meten met het framecode-raster uit het corpus; de meetonzekerheid uit B03-020 erbij optellen.
  4. Minstens 30 acties: pauze, hervatten, spoelen en volgende aflevering.
  5. De controlerende websessie stoppen en de stoptijd van het volgen meten.
  6. Bewijs-JSON via `b03h/bewijs.py` (validatie "Sim-getest") en unit-tests voor de rekendelen.
- **Tests (verplicht):** p95-positieverschil hooguit 2 s na correctie over minstens 30 acties (n noemen). Negatief: (a) geen pauze/hervat-lus (tel de commando's naar de tv); (b) na het stoppen van de websessie stopt het volgen binnen 15 s en gaat er geen commando met lege controllingSessionId meer naar de tv; (c) de diagnose toont "Volgen (±2 s)". Commando's: T-JL-HARNAS voor de unit-tests; de proef zelf achter `flock <WERKMAP>/.lokaal/stack.lock flock <WERKMAP>/.lokaal/gradle.lock nice -n 10 ...`; het exacte proefcommando schrijft de bouwer in het README van het harnas.
- **Poort:** P-jelly-leon (job `b03-harnas`).
- **Valkuilen:** V-014, V-021, V-076, V-098.
- **Bewijs:** JLT-07 -> Bezig (Sim-getest in de emulator; versie, sha256, n en p95 noemen). B03-026 -> bijwerken. Mislukt de emulator: validatie "Sim-mislukt" met de oorzaak, niet mooier opschrijven. Altijd erbij: "Swiftfin NIET GEVALIDEERD (Mac/Xcode); echte tv's NIET GEVALIDEERD (hardware)".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** KVM in de container niet beschikbaar is; de emulator niet binnen 4 GiB blijft (een herhaling met 5 GiB is toegestaan, beide uitkomsten in het bewijs; daarna stoppen en melden).

### S-G3-22 - Segmenten: ondertitel- en hoofdstuksignalen en families
- **Repo:** jelly-leon | **Fase:** P4 (golf 3) | **Omvang:** groot | **Moeilijkheid:** gewoon | **Zwaar:** nee (signalen zonder videodecode)
- **Werkpakketten en tests:** B03-074; JLT-53; JLT-57
- **Vooraf:** S-G2-90 gehaald, met B03-071 en B03-072 (S-G2-40, S-G2-42: module met `segments.db`); de cue-extractie uit de bestandspas en featurecache van S-G1-34 (B03-018 deel b, "Eén audiopas per bestand ... cue-extractie"; STAPPEN_P4_GOLF1_2.md). WP-JSON B03-074 noemt die cue-extractie "gedeeld met B03-008" (de semantische scenezoeker). B03-008 wordt na besluit Z-20 in golf 4 gebouwd (S-G4-49) en bouwt op deze stap voort; deze stap hangt niet van B03-008 af en bouwt er niets van. BG-34: zonder bevestigde labels van echte afleveringen telt alleen de synthetische set.
- **Al gedaan?** `grep -rln "Previously on" <WERKMAP>/jelly-leon/plugins <WERKMAP>/jelly-leon/tools` -> geen uitvoer = niet gestart. `grep -rln "segments.db" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = module van golf 2 ontbreekt: STOP.
- **Lees eerst:** WP-JSON object B03-074; BOUWPLAN#F6.3.3 Detectiepijplijn; BOUWPLAN#F6.3.4 Post-credit-bescherming en grensregels; BOUWPLAN#F6.5.4 Endpoints (7 en 8); BOUWPLAN#F6.9.4 Negatieve, veiligheids- en gegevensbeschermingstests
- **Bouw:**
  1. Hoofdstuknamen als signaal (patronen NL, EN en Japans in Latijns schrift); dummy- en genummerde hoofdstukken negeren. Bron: WP-JSON B03-074.
  2. Ondertitelcues uit de cue-extractie van de bestandspas (S-G1-34; via de Core-dienst voor kenmerken, nooit zelf een tool starten; stabiele spoorsleutel; externe bestanden via een pad-hash; alleen lezen): "Previously on", "Eerder in", "Wat voorafging", dichtheid van muzieknoten, ASS-stijlnamen OP en ED, aftitelingcues.
  3. Machinevertalingen van F3 (herkenbaar aan het titeltoken) tellen nooit als bewijs.
  4. Fusie met audio en beeld via een gekalibreerde score; ondertitels zijn alleen zwak bewijs (ze kunnen verschoven zijn).
  5. Families: zonder classificatie blijft een familie intern "terugkerend fragment" tot een editor een type kiest; routes 7 `GET /media/v1/segments/families` en 8 `PUT /media/v1/segments/families/{familyId}`. Bron: BOUWPLAN#F6.5.4.
  6. Tests en EVIDENCE.
- **Tests (verplicht):** op de synthetische set: de samenvatting wordt gevonden. Negatief: (a) een terugkerend fragment aan het begin (0 tot 31 s) wordt zonder bevestiging niet als intro gepubliceerd; (b) een misvormde `sintel_nl.srt` geeft geen crash; (c) ondertitels die 2,5 s naar voren of achteren zijn verschoven geven geen verschoven segment; (d) een extra extern ondertitelspoor verandert de gekozen cuebron niet; (e) route 8 door een gewone gebruiker -> 403. Alleen met bevestigde labels (BG-34): Pioneer One E02 tot en met E06, start binnen 1 s van het label, E01 geen samenvatting. Commando: T-JL-PLUGIN met `--filter "FullyQualifiedName~Segment"` (controleer de naam van de modulemap met `ls <WERKMAP>/jelly-leon/plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Modules`).
- **Poort:** P-jelly-leon (plugin, volledig) + P-CONTRACT.
- **Valkuilen:** V-003, V-005, V-099.
- **Bewijs:** B03-074 -> Bezig (Sim-getest op de synthetische set). JLT-53 en JLT-57 -> Bezig. Zonder labels: het deel Pioneer One apart als Geblokkeerd met "NIET GEVALIDEERD (echte NAS): bevestigde labels van echte afleveringen nodig (BG-34)".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** de segmentmodule van golf 2 (S-G2-40) of de cue-extractie van de bestandspas (S-G1-34, golf 1) ontbreekt; iemand labels van echte afleveringen zelf wil invullen (labels komen alleen van de gebruiker).

### S-G3-23 - Watch Together: externe deelnemers via VPN (alleen na BG-09)
- **Repo:** jelly-leon | **Fase:** P4 (golf 3) | **Omvang:** groot | **Moeilijkheid:** hoog | **Zwaar:** ja (netwerkproef met vertraging achter stack.lock)
- **Werkpakketten en tests:** B03-027; JLT-08; EX34
- **Vooraf:** BG-09 genomen en "aan". Zonder dat besluit wordt deze stap NIET gebouwd; alleen de bewijsregel hieronder. Verder S-G3-17 en S-G3-18; voor de stand `vpn_gasten` ook S-G3-10 met een geslaagde clienttest.
- **Al gedaan?** `grep -rln "ExternalMode" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = niet gestart.
- **Lees eerst:** WP-JSON object B03-027 (daar staan het VPN-adresbereik en de ACL-voorwaarde); BOUWPLAN#F1.4.5 Fail-closed; BOUWPLAN#F1.5.2 Endpoints (E16); BOUWPLAN#F1.8 Bouwfasen (regel WT-6); BOUWPLAN#F1.9.5 Negatief en veiligheid
- **Bouw:**
  1. Netwerkklasse per sessie: lan, vpn, extern of onbekend. Het VPN-bereik is standaard het Tailscale-/CGNAT-bereik (zie WP-JSON B03-027). VPN telt nooit als LAN of huishouden. Een Docker-gatewayadres telt als onbekend en dus als extern, met een Nederlandse melding.
  2. `ExternalMode`: `uit` (standaard), `vpn_huishouden` of `vpn_gasten`. Bron: WP-JSON B03-027.
  3. `vpn_gasten` is alleen te kiezen als de zelftest van S-G3-10 aantoont dat anonieme stream-, ondertitel- en afbeeldingsroutes worden geweigerd en de beheerder de ACL-voorwaarde uit de installatiegids bevestigt; anders 422 met uitleg. De ACL-voorwaarde toont E16 altijd als "niet te verifieren", nooit als groen.
  4. E16 uitbreiden met: externe toegang van de server, adresfilters, lokale subnetten (waarschuwing als het VPN-bereik daarin staat), per gast externe toegang en bitratelimiet, de uitkomst van de zelftest en het gemeten bronadres.
  5. Jelly Leon opent geen poorten en wijzigt geen router, tunnel of firewall. Er komt geen internetmodus.
  6. Installatiegids voor apparaatdeling via de VPN, zonder echte adressen of namen van de gebruiker.
  7. Tests en EVIDENCE.
- **Tests (verplicht):** `uit`: een sessie met klasse vpn, extern of onbekend ziet en joint niets. `vpn_huishouden`: een huishoudaccount met een bronadres uit het VPN-bereik (nagebootst met 80 ms vertraging, 20 ms spreiding) doet mee met p95-drift hooguit 250 ms; een gastaccount niet. Negatief: (a) `vpn_gasten` -> 422 zolang de zelftest anonieme streamroutes vindt; (b) na het intrekken van de VPN-deling verliest de deelnemer de toegang en blijft LAN werken (EX34); (c) Docker-gatewayadres -> onbekend met melding; (d) een door de aanvrager meegestuurde doorstuurheader verandert de klasse niet; (e) afwijkende schrijfwijzen van hetzelfde adres geven dezelfde klasse; (f) een kind met een VPN-deelnemer -> geweigerd. Commando: T-JL-PLUGIN met `--filter "FullyQualifiedName~Watch"`; de netwerkproef achter `flock <WERKMAP>/.lokaal/stack.lock`.
- **Poort:** P-jelly-leon (plugin, volledig; image proeven) + P-CONTRACT + P-VEILIG.
- **Valkuilen:** V-048, V-049, V-097.
- **Bewijs:** met BG-09: B03-027 -> Bezig (Sim-getest, gesimuleerd) met "NIET GEVALIDEERD (echte NAS): echte Tailscale, het bronadres achter de Docker-NAT van TrueNAS en een poortscan van buiten"; JLT-08 -> Bezig; EX34 -> Bezig (deel Jelly Leon). Zonder BG-09: B03-027 en JLT-08 -> Geblokkeerd met "wacht op besluit BG-09; ExternalMode blijft uit".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-VEILIG (VERPLICHT: toegang van buiten het huis en netwerkklassen) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4
- **Stop en vraag als:** BG-09 niet genomen is; een test, log of document een echt adres of een echte naam van de gebruiker zou bevatten; iemand een internetmodus of een open poort wil toevoegen.

### S-G3-24 - Webplugin Watch Together: gezaaide driftcorrectie, telemetrie en menu
- **Repo:** jelly-leon-web | **Fase:** P4 (golf 3) | **Omvang:** groot | **Moeilijkheid:** hoog | **Zwaar:** ja (npm-build; e2e en driftmeting achter stack.lock)
- **Werkpakketten en tests:** B03-024 (webdeel); JLT-01 en JLT-02 (hermeting met de plugin aan)
- **Vooraf:** S-G3-04; de webhaakmodule en de config.json-generator van B03-017 (golf 1). BG-14: zonder besluit alleen de weergave Modern.
- **Al gedaan?** `ls <WERKMAP>/jelly-leon-web/src/plugins/jellyLeon/watchTogether` -> bestaat niet = niet gestart. `ls <WERKMAP>/jelly-leon-web/src/jelly-leon` -> bestaat niet = de haakmodule van golf 1 ontbreekt: STOP. `grep -rn "jellyLeon-wt-seed" <WERKMAP>/jelly-leon-web/src -l` -> geen uitvoer = zaaien nog niet gebouwd.
- **Lees eerst:** WP-JSON object B03-024; BOUWPLAN#F1.6.1 Jelly Leon-webclient; `<WERKMAP>/jelly-leon-web/docs/platform-v2/PATCHES.md` (haaktabel, rij H-SYNCPLAY-MENU); BOUWPLAN#10.11 Register van upstream-gedrag, patches en webhaken; BOUWPLAN#F1.8 Bouwfasen (regel WT-3)
- **Bouw:**
  1. Fork-eigen webplugin in `src/plugins/jellyLeon/watchTogether`, geladen via de gegenereerde config.json van de image. Bron: WP-JSON B03-024.
  2. De plugin bereikt de SyncPlay-kern via de plugin-instance (geen haak) en luistert op het upstream-event `playback-diff`.
  3. Zaaien: per apparaat gemeten waarden voor `enableSyncCorrection`, `minDelaySpeedToSync`, `maxDelaySpeedToSync`, `speedToSyncDuration` en `minDelaySkipToSync`, alleen als de gebruiker ze op dat apparaat nooit zelf zette. De markeersleutel `jellyLeon-wt-seed` bewaart de versie en de gezaaide waarden.
  4. Terugdraaien: bij `SyncSeed.Enabled=false`, module uit of capabilities 404 of 501 gaat elke nog ongewijzigde gezaaide waarde terug.
  5. Telemetrie elke 10 s naar E10; meldingen bij haperen.
  6. Menu-items via een render-slot `jlHook('syncplay.menu', ctx)` in `src/apps/modern/components/AppToolbar/menus/SyncPlayMenu.tsx`: een import en een aanroep, met foutgrens; registreren als haak met het eerstvolgende vrije JLW-nummer in PATCHES.md. De weergave Legacy alleen als BG-14 dat zegt.
  7. Teksten in een eigen stringbestand; geen wijziging in `src/strings`.
  8. Driftmeting (JLT-01, JLT-02), de standaard van `enableSyncCorrection` vastzetten op basis van de meting, en EVIDENCE.
- **Tests (verplicht):** unit (in T-JLW-NPM): zaaien en terugdraaien. Negatief: (a) een door de gebruiker gezette instelling wordt nooit overschreven; (b) na "uit" staan alleen door de gebruiker gezette `syncPlay`-waarden in localStorage; (c) capabilities 404 of 501 -> gedrag als upstream; (d) een geforceerde fout in de fork-code laat het upstream-menu werken; (e) de afspeelsnelheid komt nooit boven 1,3 keer. Meting: S2 en S3 p95 hooguit 200 ms; S1 p95 hooguit de tweegebruikersbaseline van B03-020 plus 20 ms en maximaal 100 ms; minstens 5 runs per systeem. "Verbetering" mag alleen in het bewijs staan als de bovengrens van het 95 %-interval van het p95-verschil onder 0 ligt tegenover stock-standaard en stock-best; anders heet het "betere standaardinstellingen". Commando's: T-JLW-STATISCH, T-JLW-NPM, T-JLW-E2E.
- **Poort:** P-jelly-leon-web (volledig) + P-CONTRACT.
- **Valkuilen:** V-005, V-032, V-067, V-072.
- **Bewijs:** B03-024 -> Bezig (Sim-getest; aantal runs, p95 per scenario, gekozen standaard). JLT-01 en JLT-02 -> Bezig bijwerken met de hermeting. Haalt de meting de drempel niet: de gemeten waarden melden, niets claimen.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK (geen A-ONTWERP en geen R-ONTWERP: Jelly Leon-web valt buiten Peil)
- **Niveau:** A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); overige standaard
- **Stop en vraag als:** de config.json-generator in jelly-leon moet worden aangepast om de plugin te laden (dat is werk voor de jelly-leon-baan; melden aan de regisseur); de haak meer dan een import en een aanroep in het upstream-bestand vraagt.

### S-G3-25 - Kwaliteitslabel op de itempagina (webdeel van B03-057)
- **Repo:** jelly-leon-web | **Fase:** P4 (golf 3) | **Omvang:** klein | **Moeilijkheid:** hoog (haak in een upstream-bestand van de fork) | **Zwaar:** ja (npm-build; e2e achter stack.lock)
- **Werkpakketten en tests:** B03-057 (webdeel); EX36 (webdeel); JLT-38 (deel web)
- **Vooraf:** S-G3-14 (route Q2 bestaat); S-G3-24 is klaar (zelfde baan). BG-24: zonder besluit staat het label uit (`Quality.ShowLabelToUsers`).
- **Al gedaan?** `grep -rn "media/v1/quality" <WERKMAP>/jelly-leon-web/src -l` -> geen uitvoer = niet gestart.
- **Lees eerst:** WP-JSON object B03-057; BOUWPLAN#F4.6.1 jelly-leon-web; `<WERKMAP>/jelly-leon-web/docs/platform-v2/PATCHES.md` (haaktabel, rij H-ITEMDETAILS); BOUWPLAN#F4.5.3 Endpoints in Jelly Leon (Q2); BOUWPLAN#F4.9.4 Clientmatrix (alleen UI)
- **Bouw:**
  1. Gebruik de haak H-ITEMDETAILS in `src/apps/legacy/controllers/itemDetails/index.js` (functie `reloadFromItem`; Modern en Legacy laden dezelfde controller). Bestaat de haak al, dan komt er geen tweede patch: alleen een nieuwe afnemer in de fork-eigen code. Bron: PATCHES.md, haaktabel.
  2. Het label verschijnt alleen als Q2 voor deze gebruiker een label teruggeeft.
  3. 404, 501 of een fout: geen label, geen foutmelding, de pagina werkt als upstream.
  4. Nederlandse teksten in het eigen stringbestand.
  5. Tests en EVIDENCE.
- **Tests (verplicht):** e2e in Modern en Legacy: label zichtbaar bij een item met een bevinding als de instelling aan staat. Negatief: (a) een item waar de gebruiker niet bij mag -> 404 en geen label (EX36); (b) instelling uit -> geen label; (c) een geforceerde fout in de fork-code -> de itempagina werkt als upstream; (d) tegen een stock-server zonder plugin -> geen fout in de console. Commando's: T-JLW-STATISCH, T-JLW-NPM, T-JLW-E2E.
- **Poort:** P-jelly-leon-web (volledig).
- **Valkuilen:** V-060, V-067, V-072, V-126.
- **Bewijs:** B03-057 -> Bezig (Sim-getest; webdeel). EX36 -> Bezig (deel web). JLT-38 -> Bezig met "deel web; clientmatrix en Hub-kaart volgen in golf 4".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK (geen A-ONTWERP en geen R-ONTWERP: Jelly Leon-web valt buiten Peil)
- **Niveau:** A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog: de haak H-ITEMDETAILS is een ingreep in een upstream-bestand); overige standaard
- **Stop en vraag als:** de haak nog niet bestaat en meer dan een regel in het upstream-bestand vraagt; het label alleen kan met een titel of pad in het verzoek.

### S-G3-31 - Universele bibliotheek: webdeel (B03-002; alleen als het dossier van S-G3-30 een webdeel noemt)
- **Repo:** jelly-leon-web | **Fase:** P4 (golf 3) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (npm-build; e2e achter stack.lock)
- **Werkpakketten en tests:** B03-002 (webdeel)
- **Vooraf:** S-G3-30, en zijn dossier (`<WERKMAP>/.lokaal/ketens/S-G3-30/DOSSIER.md`) noemt een scherm uit BOUWPLAN#B03-002 dat upstream jellyfin-web niet heeft. Noemt het dossier geen webdeel, dan vervalt deze stap: de regisseur zet hem in VOORTGANG.md op "vervallen" met de reden uit het dossier. De webhaakmodule van B03-017 (golf 1).
- **Al gedaan?** `ls <WERKMAP>/jelly-leon-web/src/jelly-leon` -> bestaat niet = de haakmodule van golf 1 ontbreekt: STOP. `grep -n '"B03-002"' <WERKMAP>/jelly-leon-web/docs/platform-v2/EVIDENCE.json` -> geen uitvoer = niet gestart.
- **Lees eerst:** BOUWPLAN#B03-002 — Universele bibliotheek (Schermen/bediening); het dossier van S-G3-30; `<WERKMAP>/jelly-leon-web/docs/platform-v2/PATCHES.md` (kop "Geplande haken op de 12.x-basis")
- **Bouw:**
  1. Scope (A-VERKEN): alleen de schermdelen die het dossier van S-G3-30 noemt; per deel de haak uit PATCHES.md waarlangs het komt. Een haak die daar niet staat, is een nieuwe patch met een nummer in het register.
  2. Bouw die delen in de vormgeving van upstream (buiten Peil), via de haakmodule.
  3. Module uit (404), een stock-server of een fout in de fork-code: het scherm is gelijk aan upstream.
  4. Tests en EVIDENCE.
- **Tests (verplicht):** T-JLW-STATISCH; T-JLW-NPM; T-JLW-E2E (achter stack.lock). Negatief: (a) module uit of stock-server: de DOM van de betrokken schermen is gelijk aan stock; (b) een geforceerde fout in de fork-code laat het upstream-scherm werken; (c) T-JLW-STATISCH faalt als de nieuwe haak niet in het register staat.
- **Poort:** P-jelly-leon-web.
- **Valkuilen:** V-003, V-005.
- **Bewijs:** B03-002 (jelly-leon-web) -> Bezig (Sim-getest), webdeel. "NIET GEVALIDEERD (hardware): echte tv's en browsers op apparaten; zie N-P6-09."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK (geen A-ONTWERP en geen R-ONTWERP: Jelly Leon-web valt buiten Peil)
- **Niveau:** standaard
- **Stop en vraag als:** het dossier van S-G3-30 een webdeel noemt dat een wijziging buiten een haak vraagt; de haakmodule ontbreekt.

### S-G3-32 - Beschikbaarheid van clients: wat op de ontwikkelmachine nog ontbreekt (B03-003)
- **Repo:** jelly-leon-clients | **Fase:** P4 (golf 3) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (Gradle en emulator achter gradle.lock; server achter stack.lock; volgorde: eerst stack.lock, dan gradle.lock)
- **Werkpakketten en tests:** B03-003
- **Vooraf:** S-G2-90 gehaald (gate golf 2). Besluit Z-20 genomen. BG-08 (Swiftfin: zonder besluit geen eigen patches) en ADR-0008 van jelly-leon-clients (eigen builds niet verspreiden) blijven gelden.
- **Al gedaan?** `python3 -c "import json,sys;[print(r['status'],'|',r['validatie'],'|',r.get('blokkade','')) for r in json.load(open(sys.argv[1])) if r['id']=='B03-003']" <WERKMAP>/jelly-leon-clients/docs/platform-v2/EVIDENCE.json` -> op 2026-11-11: "Geblokkeerd | Sim-getest; NIET GEVALIDEERD (hardware); NIET GEVALIDEERD (Mac/Xcode); NIET GEVALIDEERD (account)". Gedaan (P0, contract 1.2 en JC3 van P4-0, tegen 12.4): telefoon, Android TV en desktop 2.0.0 onder Xvfb Sim-getest (inloggen, hervatten, Direct Play, transcode, ondertitels); tablet-emulator Sim-mislukt; smart-tv, Chromecast en AirPlay onbekend tot D15. Deze stap herhaalt dat niet zonder reden en bouwt alleen wat het dossier als gat noemt.
- **Lees eerst:** TASKS-JSON object B03-003; BOUWPLAN#B03-003 — Beschikbaarheid van clients; de EVIDENCE-regel B03-003 in jelly-leon-clients (velden bewijs, blokkade, opmerking); `<WERKMAP>/jelly-leon-clients/docs/platform-v2/INVENTARIS.md`; `<WERKMAP>/jelly-leon-clients/docs/adr/ADR-0011-clientcompatibiliteit-12x.md`; `<WERKMAP>/jelly-leon-clients/docs/adr/ADR-0008-geen-truenas-app-voor-clients.md`; WP-JSON objecten B03-026 en B03-037 (die noemen B03-003 als afhankelijkheid)
- **Bouw:**
  1. Scope (A-VERKEN): per onderdeel van de bron (web, Android, iOS, Android TV, tv-browser, Chromecast/AirPlay waar de client het ondersteunt; toegankelijkheid; responsieve speler, afstandsbediening, keuze van ondertitel- en audiospoor; "PWA shell"): al Sim-getest | ontbreekt en haalbaar | alleen met echte apparaten, Mac of account. Een webdeel (PWA-schil) hoort in jelly-leon-web: noemt het dossier dat als gat, dan keuzemenu (AGENTEN.md 6.8: aparte stap in jelly-leon-web of niet in P4); het hoort niet in deze stap.
  2. De matrix voor ondertitels, hervatten en afspelen opnieuw tegen de jelly-leon-image van de actuele stand (na golf 2, op 12.x), met stock 12.x op dezelfde digest als controlegroep: T-JLC-COMPAT.
  3. Alleen de gaten uit het dossier die op de ontwikkelmachine te bouwen en te testen zijn, als geregistreerde JLC-patch met test (T-JLC-STATISCH controleert het register). De tablet-emulator: ONBEKEND of die stabiel kan binnen de grenzen van de Opdrachtkop - A-VERKEN leest de rapporten `docs/platform-v2/test-evidence/p4-0-jc3-android-tablet-herhaling-1.json` en `-2.json`; blijft hij Sim-mislukt, dan staat dat zo in het bewijs.
  4. EVIDENCE bijwerken.
- **Tests (verplicht):** T-JLC-STATISCH; T-JLC-BOUW voor de clients die het dossier noemt; T-JLC-COMPAT (achter stack.lock en gradle.lock, in die volgorde). Negatief: (a) stock 12.x met dezelfde scenario's als controlegroep, 0 regressies; (b) de hervatproef telt elke poging (`python3 tools/clients/client_compat.py hervatproef`, opties eerst met `--help`); (c) T-JLC-STATISCH faalt bij een JLC-patch zonder registerregel.
- **Poort:** P-jelly-leon-clients.
- **Valkuilen:** V-011, V-012, V-057.
- **Bewijs:** B03-003 (jelly-leon-clients) blijft "Geblokkeerd" (de acceptatie vraagt echte tv's en apparaten) met "Sim-getest" en de nieuwe rapportpaden. "NIET GEVALIDEERD (hardware): echte tv's en apparaten (D15); NIET GEVALIDEERD (Mac/Xcode): Swiftfin; zie STAPPEN_P6.md, N-P6-09."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK (geen A-ONTWERP en geen R-ONTWERP: de clients vallen buiten Peil)
- **Niveau:** standaard
- **Stop en vraag als:** het dossier een gat noemt dat een eigen build op een echt apparaat of verspreiding vraagt (ADR-0008); een emulator het geheugen van de machine overschrijdt (AGENTEN.md 3.3); een regressie tegen stock optreedt.

### S-G3-26 - Native SyncPlay op Android TV (alleen als BG-10 "clientpatch" zegt)
- **Repo:** jelly-leon-clients | **Fase:** P4 (golf 3) | **Omvang:** ONBEKEND tot na de verkenning (zie bouwpunt 1) | **Moeilijkheid:** hoog | **Zwaar:** ja (Gradle achter gradle.lock; emulator)
- **Werkpakketten en tests:** B03-026 (optioneel deel, subfase WT-10); JLT-07 (deel native)
- **Vooraf:** BG-10 genomen met de keuze "clientpatch". Zonder die keuze VERVALT deze stap. S-G3-20.
- **Al gedaan?** `grep -n "SyncPlay" <WERKMAP>/jelly-leon-clients/docs/platform-v2/PATCHES.md` -> geen treffer = niet gestart.
- **Lees eerst:** WP-JSON object B03-026 (laatste zin); BOUWPLAN#F1.8 Bouwfasen (regel WT-10); `<WERKMAP>/jelly-leon-clients/docs/platform-v2/PATCHES.md`; `<WERKMAP>/jelly-leon-clients/docs/platform-v2/FORK_STRATEGIE.md`; BOUWPLAN#F1.6.2 Andere clients
- **Bouw:**
  1. A-VERKEN zoekt de beoordeelde community-wijziging waarop het bouwplan doelt en meet de omvang (bestanden, regels, raakvlak met upstream). Is het meer dan een bouwer in een keer kan afronden, dan stopt de stap hier en splitst de regisseur hem.
  2. ADR in jelly-leon-clients met de keuze, de bron en het sync-risico.
  3. Patch met het eerstvolgende vrije JLC-nummer (JLC-0001 tot en met JLC-0004 bestaan) in PATCHES.md.
  4. Sync-proef: de patch overleeft het bijwerken vanaf upstream.
  5. Emulatortest en EVIDENCE.
- **Tests (verplicht):** T-JLC-STATISCH; T-JLC-BOUW (`make androidtv-bouw`); emulatortest: de tv-app doet als gewoon groepslid mee. Negatief: (a) tegen een stock-server zonder plugin gedraagt de app zich als upstream; (b) een kinderprofiel krijgt via de app niets wat S-G3-18 verbiedt.
- **Poort:** P-jelly-leon-clients (volledig; emulatorproef).
- **Valkuilen:** V-021, V-072, V-075, V-076, V-080.
- **Bewijs:** B03-026 -> bijwerken ("native deel", Sim-getest in de emulator). Vervalt de stap: geen bewijsregel, wel de zin "native SyncPlay niet gekozen (BG-10)" bij B03-026.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); overige standaard
- **Stop en vraag als:** BG-10 niet "clientpatch" is; er geen beoordeelde community-wijziging te vinden is; de patch beschermde bestanden van de fork raakt.

### S-G3-27 - Compat-regressie en differentiele run per module-oplevering (herhaalstap)
- **Repo:** jelly-leon | **Fase:** P4 (golf 3) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (image-build achter docker-build.lock; proeven achter stack.lock)
- **Werkpakketten en tests:** JLT-63; JLT-64; JLT-65; JLT-24 (differentieel deel); JLT-35; JLT-05 (deel stock-web)
- **Vooraf:** deze stap draait vijf keer: na S-G3-08 (Subtitles), na S-G3-16 (Quality), na S-G3-22 (Segments), na S-G3-30 (metadata en universele bibliotheek, S-G3-28 tot en met S-G3-30) en na S-G3-23 of S-G3-20 (Watch Together). Elke keer met een verse image van de actuele main.
- **Al gedaan?** `ls <WERKMAP>/jelly-leon/docs/platform-v2/test-evidence | grep -i "diffrun\|compat"` -> vergelijk de datum en de commit in het rapport met `git -C <WERKMAP>/jelly-leon log -1 --format=%H`; een rapport van een oudere commit telt niet.
- **Lees eerst:** FASERING#Gates per functie; BOUWPLAN#F4.9.7 Gegevensbescherming; BOUWPLAN#F3.9.4 Differentiele controle-run; BOUWPLAN#F1.9.6 Gegevensbescherming; `<WERKMAP>/jelly-leon/tools/b03-harnas/README.md`
- **Bouw:**
  1. Bouw de image (T-JL-IMAGE) van de actuele main.
  2. Draai T-JL-COMPAT: API-vergelijking met stock, het gedragsregister en de differentiele run met alle modules aan (`--image-a <stock-12.x-image> --image-b <lokale-tag>`, met `--toegestaan` de samengevoegde lijsten van de opgeleverde modules).
  3. Draai dezelfde differentiele run met `--negatieve-proef`.
  4. Controleer in de rapporten: geen verschil in kijkgegevens, gebruikers, UserPolicy of mediabestanden buiten de lijsten.
  5. Rooktest met stock-web tegen de image: een genodigde ziet de groep in de gewone SyncPlay-lijst en kan joinen (aanvulling op S-G3-17).
  6. EVIDENCE bijwerken met het rapportpad en de commit; opruimen van de eigen testimages (alleen de eigen tags, nooit `prune`).
- **Tests (verplicht):** T-JL-IMAGE; T-JL-COMPAT. Negatief: de negatieve proef van de differentiele run moet een verschil vinden; een run zonder die proef telt niet. Stock-web: `PYTHONPATH=tools/b03-harnas python -m b03h clientmatrix --onderdelen web --image <lokale-tag> --uit <rapport.json>`.
- **Poort:** P-jelly-leon (volledig, CI-volgorde) + P-HARDE-EIS.
- **Valkuilen:** V-009, V-011, V-027, V-077, V-088, V-111.
- **Bewijs:** JLT-63, JLT-64, JLT-65 -> Bezig met per run de commit en "modules aan: <lijst>". JLT-24 en JLT-35 -> Bezig bijwerken. Nooit een oudere run als bewijs voor een nieuwere module gebruiken.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-HARDE-EIS (VERPLICHT: de run is het bewijs dat kijkgegevens ongemoeid blijven) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard; R-HARDE-EIS N4; A-BOUW N2 mag bij de tweede en latere run als er geen code verandert
- **Stop en vraag als:** de differentiele run een verschil buiten de lijsten toont (no-go: schrijven in kijkgeschiedenis); een stock-client niet meer afspeelt.

### S-G3-90 - Gatecontrole golf 3 (A-GATE, alleen lezen)
- **Repo:** jelly-leon, jelly-leon-web en jelly-leon-clients (S-G3-32; en S-G3-26 als die liep), alleen lezen. Uitzondering op "een stap = een repo": dit is de gatecontrole; A-GATE schrijft alleen `<WERKMAP>/.lokaal/ketens/GATE-GOLF-3/RAPPORT-A-GATE.md` | **Fase:** P4 (golf 3) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (A-GATE draait per repo de volledige poort opnieuw, de repos na elkaar, achter de locks)
- **Werkpakketten en tests:** geen eigen ID's; beoordeelt de gate van golf 3 (B03_FASERING.md#3. Golven en werkpakketten, rij Golf 3: JLT-03, 05, 07, 08, 20, 22, 23, 24, 30 tot en met 37, 53, 57) met de afvinklijst hieronder
- **Vooraf:** S-G3-01 tot en met S-G3-25, S-G3-28 tot en met S-G3-32 en de vijf runs van S-G3-27 klaar of met reden vervallen (S-G3-31 vervalt als het dossier van S-G3-30 geen webdeel noemt; S-G3-26 alleen als BG-10 een clientpatch koos; S-G3-23 alleen als BG-09 "aan" is; S-G3-17 tot en met S-G3-21 alleen na BG-11 en BG-10); in jelly-leon, jelly-leon-web en jelly-leon-clients is geen keten open
- **Al gedaan?** `ls <WERKMAP>/.lokaal/ketens/GATE-GOLF-3/RAPPORT-A-GATE.md && grep -n "gate golf 3" <WERKMAP>/.lokaal/ketens/GATE-GOLF-3/RAPPORT-A-GATE.md` -> klaar als het rapport bestaat, de uitkomst "gate golf 3 gehaald" is EN `git -C <WERKMAP>/jelly-leon rev-parse --short HEAD` (en idem voor jelly-leon-web) nog gelijk is aan de HEAD die het rapport noemt. Is er sindsdien gecommit, dan loopt de gate opnieuw voor wat die commits raken.
- **Lees eerst:** hoofdstuk 2 (Gates) en de afvinklijst hieronder; FASERING#Gates per functie; `<WERKMAP>/.lokaal/plan/uit/AGENTEN.md` (prompt "A-GATE" en kop "2.2 Het protocol"); POORTEN.md, blokken P-jelly-leon en P-jelly-leon-web (kop "4. Volledig (CI-volgorde)"); `<WERKMAP>/.lokaal/plan/uit/VOORTGANG.md`
- **Bouw:** er wordt niets gebouwd. A-GATE loopt de afvinklijst hieronder af, draait per repo de volledige poort (eerst jelly-leon-clients, dan jelly-leon-web, dan jelly-leon; tussen twee repos `free -m` en `df -h /`) en schrijft per punt "ja", "nee" of "niet vast te stellen" met het commando of bestand waarop het oordeel rust.
- **Tests (verplicht):** de volledige poort per repo (POORTEN.md, kop "4. Volledig (CI-volgorde)"), elk commando met exitcode en slotregel in het rapport. Negatief (door A-GATE zelf opnieuw gedraaid, niet overgenomen uit een rapport): de negatieve proef van de laatste differentiele run van S-G3-27 vindt een verschil; T-JL-REGISTER faalt als een haak of patch uit het register wordt weggelaten (alleen lezen van de test, niets wijzigen).
- **Poort:** P-jelly-leon, P-jelly-leon-web en P-jelly-leon-clients (volledig) + P-GIT + P-EERLIJK + P-HARDE-EIS + P-VEILIG, alle als controle.
- **Valkuilen:** V-098, V-005, V-027, V-034, V-112. Eigen: een gate-rij die alleen op de NAS te bewijzen is telt niet als gehaald en niet als fout; zij staat apart in het rapport.
- **Bewijs:** geen wijziging in een EVIDENCE.json; de uitkomst staat in het gate-rapport en in VOORTGANG.md.
- **Agents:** A-GATE. Kortere keten met reden: zuivere controlestap; A-GATE is zelf de onafhankelijke controle en herstelt niets. Bij tekortkomingen: A-HERSTEL -> R-EERLIJK in de betreffende repo, daarna A-GATE opnieuw alleen voor de open punten.
- **Niveau:** A-GATE N4 (einde van een golf, niet van een fase)
- **Stop en vraag als:** tijdens de controle in een van de repos wordt geschreven; een gate-rij volgens TEST-JSON of FASERING bij golf 3 hoort maar niet in de afvinklijst staat (tekortkoming van het plan: melden); de gate een tweede keer niet gehaald wordt (keuzemenu aan de gebruiker).

Afvinklijst gate golf 3 (A-GATE bouwt niets en leest alleen):

- [ ] Elke stap van golf 3 heeft in EVIDENCE van de repo een regel met status "Bezig" of "Geblokkeerd"; nergens
      "Gereed" of "Geslaagd". Controle: `grep -n '"status"' <WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json | grep -ci "gereed\|geslaagd"` -> 0
      (validatielabels "Sim-geslaagd" staan in een ander veld; lees bij een treffer de regel na).
- [ ] Gate-rijen golf 3 hebben elk een bewijsregel met rapportpad: JLT-03, JLT-05, JLT-07, JLT-08, JLT-20, JLT-22,
      JLT-23, JLT-24, JLT-30 tot en met JLT-37, JLT-53, JLT-57. Een rij die op een besluit wacht (JLT-08 zonder BG-09)
      staat op "Geblokkeerd" met het besluit erbij.
- [ ] Elk rapportpad in die regels bestaat (`ls`), en het rapport noemt de commit waarop het is gemaakt.
- [ ] Subfase-gates: WT-2 (S-G3-17, S-G3-18), WT-3 (S-G3-24), WT-4 (S-G3-19), WT-5 (S-G3-20, S-G3-21), WT-6
      (S-G3-23 of "wacht op BG-09"), 3A en 3B (S-G3-03 tot en met S-G3-08), QC-0 tot en met QC-5 (S-G3-01, S-G3-02,
      S-G3-11 tot en met S-G3-16), F6-S4 (S-G3-22).
- [ ] Besluit Z-20, golf 3: B03-006 (S-G3-28, S-G3-29), B03-002 (S-G3-30, en S-G3-31 of de reden dat hij verviel) en
      B03-003 (S-G3-32) hebben elk een EVIDENCE-regel in de repo van de stap met "Bezig" of "Geblokkeerd" en
      NIET GEVALIDEERD voor wat echte apparaten of de NAS vraagt; de dossiers noemen per onderdeel van de bron de scope
      (afspraak "Stappen uit besluit Z-20" in hoofdstuk 8). Deze werkpakketten hebben geen gate-rij in FASERING; hun
      ontbreken is een tekortkoming van de stap, niet van de gate.
- [ ] Module uit (besluit Z-19): de routes van de modules van golf 3 geven 404 als de module uit staat (niet
      aangemeld: 401), elk met een test.
- [ ] No-go-lijst uit hoofdstuk 2: geen schrijven in kijkgeschiedenis, gebruikers, UserPolicy of mediabestanden
      (laatste run van S-G3-27, met de negatieve proef erbij); geen MediaGuard-mutatie; geen weigering van een
      stock-client.
- [ ] De NAS-rijen JLT-06, JLT-26 en JLT-39 staan op "Geblokkeerd" met "NIET GEVALIDEERD (...)" en wat nog nodig is.
- [ ] Patchregisters kloppen: T-JL-REGISTER en T-JLW-STATISCH groen; elke nieuwe haak of patch heeft een nummer.
- [ ] CI van de laatste commit op de branch is groen in jelly-leon, jelly-leon-web en jelly-leon-clients (POORTEN.md, kop "0.5
      CI-controle na elke push").
- [ ] Geen modelnaam, geen geheim, geen adres van de gebruiker in de commits van deze golf (P-VEILIG).
- [ ] VOORTGANG.md noemt elke stap van golf 3 met zijn stand; vervallen stappen staan er met het besluit (BG-09,
      BG-10, BG-11) of met de reden uit het dossier (S-G3-31). De Excel en `docs/platform-v2/OVERDRACHT/STATUS.md` worden niet bij deze golfgate bijgewerkt maar
      een keer bij de fase-afsluiting (S-G4-90 in hoofdstuk 10); dat is geen tekortkoming van golf 3.

Uitkomst van A-GATE: "gate golf 3 gehaald" of een lijst met wat ontbreekt per stap. Bij een gat gaat de stap terug
naar A-HERSTEL; de regisseur start golf 4 in de jelly-leon-baan pas na een gehaalde gate. De banen jelly-leon-clients
(S-G4-25) en ai-server-manager (S-G4-31) hangen niet aan deze gate en mogen eerder starten.

## 9. Stappen golf 4

De vaste afspraken uit hoofdstuk 8 (half werk, poort, bewijs, testbestanden, media, OpenAPI, stappen uit besluit Z-20)
gelden hier ook. Extra
voor golf 4:

- **Module-namen:** de module voor apparaten en afspelen heet in de code `Devices`
  (`PLUGIN/Modules/Devices`); de namen van de andere modulemappen: `ls <WERKMAP>/jelly-leon/plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Modules`.
  Het testfilter is steeds `--filter "FullyQualifiedName~<naam van de modulemap>"`.
- **Hub-stappen (ai-server-manager):** altijd A-ONTWERP voor de bouw en R-ONTWERP erna; de kaart toont alleen aantallen
  en ondoorzichtige ID's, nooit titels of namen uit Jelly Leon; zonder koppeling toont de kaart de toestand "onbekend"
  of "nog niet beschikbaar" en nooit een groene status.
- **Geheugenregel:** emulator, Gradle en zware transcodes of tijdmetingen nooit tegelijk.

### S-G4-01 - Spike lanewrapper (NativeAOT met execv) en ADR
- **Repo:** jelly-leon | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** hoog | **Zwaar:** ja (tijdmeting en serverproef achter stack.lock)
- **Werkpakketten en tests:** B03-063 (spike F5-S2(a)); JLT-44 (deel spikegate)
- **Vooraf:** gate golf 3; B03-062 (GPU-assistent, golf 2).
- **Al gedaan?** `ls <WERKMAP>/jelly-leon/docs/adr | grep -i "lane"` -> geen uitvoer = geen ADR. `grep -rln "jl-ffmpeg-lane" <WERKMAP>/jelly-leon --include=*.cs --include=*.csproj --include=Dockerfile` -> geen uitvoer = niet gestart.
- **Lees eerst:** WP-JSON object B03-063; BOUWPLAN#F5.8 Bouwfasen (regel F5-S2); BOUWPLAN#F5.5.3 Interne IPC: lanewrapper; BOUWPLAN#F5.3.6 Upstream-sync, patchhygiëne; `<WERKMAP>/.lokaal/jl-dotnet.sh`
- **Bouw:**
  1. Proefversie van de wrapper `jl-ffmpeg-lane` als NativeAOT-programma dat alleen het nodepad herschrijft en ffmpeg start met `execv` zonder shell. Of de bouwcontainer NativeAOT kan bouwen: ONBEKEND - eerst vaststellen met: `cat <WERKMAP>/.lokaal/jl-dotnet.sh` en een proefbuild. Bron: WP-JSON B03-063.
  2. Meting: extra starttijd over 200 starts tegenover ffmpeg rechtstreeks.
  3. Serverproef: de PID van de transcode in de server is de PID van ffmpeg; na stoppen met `q` en na Kill() blijft geen ffmpeg-proces achter.
  4. Golden files: echte ffmpeg-regels per nodeklasse (vaapi, drm, qsv via va, opencl via va, `-hwaccel_device`, `-filter_hw_device`, leeg apparaat) door de wrapper halen.
  5. ADR "lanewrapper of core-patch" met de meetwaarden en de keuze: optie A (NativeAOT), optie A' (klein statisch C-programma als A de gate niet haalt) of optie B (geregistreerde core-patch, alleen als A en A' falen). Nummer: het eerstvolgende vrije (`ls <WERKMAP>/jelly-leon/docs/adr | tail -3`).
  6. EVIDENCE.
- **Tests (verplicht):** spikegate: mediaan extra starttijd hooguit 50 ms over 200 starts (n en mediaan in het rapport); zelfde PID; geen achtergebleven proces. Negatief: (a) een regel zonder nodepad gaat ongewijzigd door; (b) een onbereikbare socket geeft na de time-out de ongewijzigde regel, geen fout. Meting achter `flock <WERKMAP>/.lokaal/stack.lock nice -n 10`.
- **Poort:** P-jelly-leon (plugin, snel) + T-JL-REGISTER.
- **Valkuilen:** V-005, V-057, V-074.
- **Bewijs:** B03-063 -> Bezig ("spike; ADR <nummer>; keuze optie ..."). JLT-44 -> Bezig met "deel spikegate". "Echte twee-GPU-opstelling NIET GEVALIDEERD (hardware)".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); overige standaard
- **Stop en vraag als:** A en A' de gate niet halen: optie B is een core-patch en vraagt een besluit van de gebruiker (keuzemenu via de regisseur).

### S-G4-02 - Lanewrapper en socketdienst bouwen
- **Repo:** jelly-leon | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** hoog | **Zwaar:** nee (build achter docker-build.lock)
- **Werkpakketten en tests:** B03-063; JLT-44 (deel wrapper en socket); JLT-48 (deel socketrechten)
- **Vooraf:** S-G4-01 met een ADR die optie A of A' kiest. Bij optie B vervalt deze stap en maakt de regisseur een aparte patchstap.
- **Al gedaan?** `grep -rln "lane.sock" <WERKMAP>/jelly-leon/plugins <WERKMAP>/jelly-leon/deploy` -> geen uitvoer = niet gestart.
- **Lees eerst:** de ADR van S-G4-01; BOUWPLAN#F5.5.3 Interne IPC: lanewrapper; BOUWPLAN#F5.4.5 Beveiliging; BOUWPLAN#F5.9.1 Unit; WP-JSON object B03-063
- **Bouw:**
  1. De wrapper als eigen project in de fork (de map legt de ADR vast): herschrijft uitsluitend het nodepad in `-init_hw_device vaapi=...`, `drm=...` en `-hwaccel_device`. Bron: WP-JSON B03-063.
  2. Sessiesleutel `job_key` = de stam van het uitvoerpad, zodat spoelen en hervatten dezelfde node houden.
  3. Socketdienst in de module Devices op `/run/jelly-leon/lane.sock`: controle van de aanroeper met SO_PEERCRED; alleen de gebruiker van de server mag verbinden. Bron: BOUWPLAN#F5.5.3.
  4. Time-out van 150 ms in de wrapper: daarna de regel ongewijzigd doorgeven.
  5. Argumenten zonder nodepad (probes van de server, leeg apparaat) gaan zonder socket direct door.
  6. Golden files als vaste testbestanden bij de tests.
  7. Tests en EVIDENCE.
- **Tests (verplicht):** golden files groen per nodeklasse. Negatief: (a) een proces met een andere uid krijgt geen antwoord van de socket; (b) socket weg -> ongewijzigde regel; (c) misvormd socketantwoord -> ongewijzigde regel; (d) een argument dat op een nodepad lijkt maar op een andere plek staat wordt niet herschreven; (e) een shell-teken in een argument wordt niet uitgevoerd. Commando: T-JL-PLUGIN met `--filter "FullyQualifiedName~Devices"`; de wrappertests: het commando legt de bouwer vast in het README naast het project.
- **Poort:** P-jelly-leon (plugin, volledig) + P-VEILIG.
- **Valkuilen:** V-003, V-050, V-055.
- **Bewijs:** B03-063 -> Bezig (Unit-getest). JLT-44 -> Bezig met "deel".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-VEILIG (VERPLICHT: socket en het starten van een proces) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4
- **Stop en vraag als:** de wrapper meer moet herschrijven dan het nodepad; de socket alleen werkt met ruimere rechten.

### S-G4-03 - Wrapper in de image en laneplanner
- **Repo:** jelly-leon | **Fase:** P4 (golf 4) | **Omvang:** groot | **Moeilijkheid:** hoog | **Zwaar:** ja (image-build achter docker-build.lock; simulatie en meting achter stack.lock)
- **Werkpakketten en tests:** B03-063; B03-004 (aanvulling F5, delen 1, 3 en 4); JLT-44; JLT-43 (hermeting met de wrapper)
- **Vooraf:** S-G4-02. BG-28 (rolverdeling van de GPU's, D08): zonder bevestiging blijft de rolverdeling een hypothese en geldt alleen de simulatie.
- **Al gedaan?** `grep -n "JELLYFIN_FFMPEG\|jelly-leon/lane" <WERKMAP>/jelly-leon/deploy/allinone/Dockerfile` -> geen treffer = wrapper niet in de image.
- **Lees eerst:** WP-JSON objecten B03-063 en B03-004 (alleen "Aanvulling F5"); BOUWPLAN#F5.3.4 GPU's: identificatie, topologie; BOUWPLAN#F5.9.2 Integratie; `<WERKMAP>/jelly-leon/deploy/allinone/Dockerfile`; BOUWPLAN#F5.9.10 Middelen en locks
- **Bouw:**
  1. Image: wrapper in `/usr/lib/jelly-leon/lane/ffmpeg`, eigendom van root, niet schrijfbaar voor de gebruiker van de server; `ffprobe` als symlink naar de echte ffprobe; `JELLYFIN_FFMPEG` wijst naar de wrapper. Bron: WP-JSON B03-063.
  2. Planner: routeren op gemeten capaciteit per werkklasse; AV1-encode nooit op een node zonder AV1-encode; VPP-tonemapping nooit voor DV-profiel 5.
  3. Bezetting uit `ITranscodeManager` plus afstemming met `/proc` elke 5 s.
  4. Geen geschikte node met ruimte: geen keuze teruggeven (gedrag van upstream) plus event `media.gpu_lane.saturated`; nooit weigeren.
  5. Gezondheid per node: een defecte node krijgt geen nieuwe sessies; batchwerk van de server (trickplay, keyframes) nooit naar de node waarop MediaGuard encodeert.
  6. Route `GET /media/v1/transcode/capabilities` toont node en werkklasse; event `media.transcode.started`.
  7. Simulatie van alle topologieen (`two_gpu` met een echte en een afwezige of defecte node, `a310_only`, `uhd770_only`, `none`) en EVIDENCE.
- **Tests (verplicht):** imagetest: wrapper, map en symlink van root en niet schrijfbaar voor de servergebruiker. Simulatie: spoelen houdt de node. Negatief: (a) node weg -> de volgende sessie start binnen 15 s op een andere geschikte node, zonder herstartlus; (b) alle nodes vol -> gedrag van upstream en 0 geweigerde starts; (c) planner of socket weg -> afspelen werkt als upstream; (d) AV1-uitvoer wordt nooit op een node zonder AV1-encode gezet. Commando's: T-JL-PLUGIN, T-JL-IMAGE; simulatie achter `flock <WERKMAP>/.lokaal/stack.lock nice -n 10`.
- **Poort:** P-jelly-leon (volledig, CI-volgorde) + P-INSTALLATIE + P-VEILIG.
- **Valkuilen:** V-009, V-014, V-053, V-068, V-070.
- **Bewijs:** B03-063 en B03-004 -> Bezig (Sim-getest; opmerking "Intel-iGPU-getest (ontwikkelmachine)"). JLT-44 -> Bezig. JLT-43 -> Bezig bijwerken. Altijd: "NIET GEVALIDEERD (hardware): echte twee-GPU-opstelling, A310 en UHD 770 (JLT-49, STAPPEN_P6.md)".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-MANIFEST (VERPLICHT: image) -> R-VEILIG (VERPLICHT: rechten op de wrapper) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4; R-MANIFEST N3
- **Stop en vraag als:** de image alleen werkt met een extra apparaat, poort of recht in het installatiemanifest; de servergebruiker in de image een andere uid heeft dan het bouwplan aanneemt.

### S-G4-04 - Gedeeld GPU-budget met MediaGuard (alleen lezen)
- **Repo:** jelly-leon | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** hoog | **Zwaar:** nee (contracttest tegen de MediaGuard-image achter stack.lock)
- **Werkpakketten en tests:** B03-064; B03-004 (aanvulling F5, deel 2); JLT-45; EX08 (deels)
- **Vooraf:** S-G4-03; de MediaGuard-viewerclient van golf 1 (B03-009). BG-04 (sleutel via de Hub) en BG-05.
- **Al gedaan?** `grep -rln "CapacityWhenMgActive" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = niet gestart.
- **Lees eerst:** WP-JSON object B03-064; BOUWPLAN#F5.10 MediaGuard-integratie; BOUWPLAN#F5.3.4 GPU's: identificatie, topologie (regels G1 tot en met G10); BOUWPLAN#F5.3.8 Budget op de NAS; BOUWPLAN#F5.4.4 Privacy
- **Bouw:**
  1. De module leest de uitkomst van de ene poller van de gemeenschappelijke viewerclient (`GET /api/v1/app/status` elke 20 s); geen tweede poller. Bron: WP-JSON B03-064.
  2. Witte lijst van velden: alleen bereikbaarheid en per baan naam, lopend, plaatsen en gepauzeerd. Nooit redenen, lopende titels of sessies bewaren of loggen.
  3. Overige leesroutes met hun ritme: bronnen elke 5 minuten, mogelijkheden bij de start, koppelstatus hooguit 1 keer per uur met alleen de vier toegestane velden.
  4. Regels G1 tot en met G10: live gaat voor MediaGuard-AV1, dat gaat voor batchwerk; het aandeel van MediaGuard op zijn node via `CapacityWhenMgActive`; conflict als MediaGuard een andere node gebruikt dan bevestigd.
  5. Events `media.gpu_lane.saturated` en `media.gpu_budget.conflict`. Geen enkele schrijvende aanroep naar MediaGuard, geen weigering.
  6. De live-kant doorgeven aan de globale batchplanner: zolang een software-transcode loopt staat de batch stil.
  7. Tests en EVIDENCE.
- **Tests (verplicht):** met de MediaGuard-simulator (vol, leeg, gepauzeerd, onbereikbaar, andere node; antwoorden met titels en namen erin): nooit een sessie naar een node boven zijn capaciteit zolang een geschikte node ruimte heeft. Negatief: (a) alle nodes vol -> gedrag van upstream, event, 0 geweigerde starts; (b) MediaGuard onbereikbaar -> "bezetting onbekend" en afspelen werkt; (c) andere node -> degraded plus event; (d) logscan: geen titel of gebruikersnaam uit MediaGuard in logs, database of events; (e) een sleutel met een hogere rol dan viewer wordt geweigerd en niet opgeslagen; (f) de koppelstatus wordt hooguit 1 keer per uur gevraagd. Contracttest tegen de echte MediaGuard-image (401, 403 en 429): hoe die image lokaal te krijgen: POORTEN.md, blok "P-media-guard-ultimate" (alleen gebruiken, in die repo niets wijzigen). Commando: T-JL-PLUGIN met `--filter "FullyQualifiedName~Devices"`.
- **Poort:** P-jelly-leon (plugin, volledig) + P-CONTRACT + P-VEILIG + P-HARDE-EIS.
- **Valkuilen:** V-042, V-046, V-094, V-099, V-105.
- **Bewijs:** B03-064 -> Bezig (Sim-getest). JLT-45 -> Bezig. EX08 -> Bezig met "alleen deels: het MediaGuard-deel wacht op de wijziging aan MediaGuard-kant". "Echte A310: NIET GEVALIDEERD (hardware)".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-VEILIG (VERPLICHT: MediaGuard-sleutel en witte lijst) -> R-HARDE-EIS (VERPLICHT: MediaGuard mag nooit worden gestuurd of gehinderd) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4; R-HARDE-EIS N4
- **Stop en vraag als:** het budget alleen werkt met een schrijvende MediaGuard-route of met een rol boven viewer; de viewerclient van golf 1 ontbreekt.

### S-G4-05 - Apparaten: probe-, advies- en uitkomstroutes (serverdeel)
- **Repo:** jelly-leon | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** B03-065 (serverdeel); B03-005 (aanvulling F5); JLT-42 (deel proberapport); JLT-48 (deel invoergrenzen)
- **Vooraf:** B03-061 (golf 2: module Devices met `devices.db`). Deze stap hangt niet aan de lanewrapper en mag in de baan naar voren.
- **Al gedaan?** `grep -rn "devices/self/probe" <WERKMAP>/jelly-leon/plugins/JellyLeon/src -l` -> geen uitvoer = niet gestart.
- **Lees eerst:** WP-JSON object B03-065; BOUWPLAN#F5.5.2 Endpoints; BOUWPLAN#F5.5.1 Gedeelde schema's; BOUWPLAN#F5.3.3 Beslisvolgorde, clientrollen en invarianten; BOUWPLAN#F5.9.6 Negatief en veiligheid
- **Bouw:**
  1. Route `PUT /media/v1/devices/self/probe`: proberapport van het eigen apparaat, met schemacontrole en een grens van 64 KiB voor het rapport. Bron: WP-JSON B03-065; JLT-48.
  2. Route `GET /media/v1/devices/self/advice` met ETag.
  3. Route `POST /media/v1/playback/outcomes` voor afspeeluitkomsten van de webmodule.
  4. Route `PUT /media/v1/devices/self/correction`: de opt-in-schakelaar voor het eigen apparaat.
  5. Rolbepaling aan de serverkant volgens de ene definitie van clientrollen; een onbekende rol telt als stock (geen advies).
  6. Tests en EVIDENCE.
- **Tests (verplicht):** xUnit: schema-geldig rapport wordt opgeslagen; advies met ETag geeft 304 bij ongewijzigd. Negatief: (a) zonder token -> 401; (b) rapport voor een ander apparaat -> 403; (c) rapport groter dan 64 KiB en groter dan 1 MiB -> 413 met de contractfoutvorm; (d) ongeldige JSON -> 422; (e) een kind kan de opt-in niet zetten; (f) ontbrekende of hergebruikte Idempotency-Key en een verkeerde If-Match geven de fouten uit de foutcatalogus. Commando: T-JL-PLUGIN met `--filter "FullyQualifiedName~Devices"`.
- **Poort:** P-jelly-leon (plugin, volledig) + P-CONTRACT.
- **Valkuilen:** V-039, V-046, V-050, V-066.
- **Bewijs:** B03-065 -> Bezig (Unit-getest; "serverdeel; webdeel in S-G4-21 en S-G4-22"). JLT-42 en JLT-48 -> Bezig met "deel".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** een route uit het bouwplan al bestaat met een ander schema (golf 2); de module Devices van golf 2 ontbreekt.

### S-G4-06 - Geleerde profielen per apparaat met bevestiging
- **Repo:** jelly-leon | **Fase:** P4 (golf 4) | **Omvang:** groot | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** B03-066; JLT-41 (serverdeel); JLT-42 (deel regels)
- **Vooraf:** S-G4-05; de testset met gecontroleerde fouten van B03-060 (golf 2). BG-26: zonder besluit krijgen officiele apps en stock-clients geen advies.
- **Al gedaan?** `grep -rln "RestrictThreshold" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = niet gestart.
- **Lees eerst:** WP-JSON object B03-066; BOUWPLAN#F5.3.3 Beslisvolgorde, clientrollen en invarianten (I1 tot en met I8); BOUWPLAN#F5.4.1 Eigen opslag; BOUWPLAN#F5.4.3 Back-up, migratie, uitzetten; BOUWPLAN#F5.9.1 Unit
- **Bouw:**
  1. Regelmotor in de module Devices. Beperkende regels worden actief na `RestrictThreshold` (standaard 2) consistente mislukkingen per apparaat en combinatie, en alleen waar het profieladvies aan staat. Bron: WP-JSON B03-066.
  2. Verruimende regels worden alleen actief na probe, een gelukte bevestigingsproef en bevestiging door de gebruiker (eigen apparaat, geen kind) of de beheerder.
  3. Staten: waargenomen, voorgesteld, bevestigd, actief, ingetrokken, te herbevestigen (bij een nieuwe hoofdversie van de client).
  4. Import zet verruimende regels terug naar voorgesteld.
  5. Audit per beslissing met een gepseudonimiseerde beslisser; bevestigde of afgewezen regels worden nooit automatisch gewist.
  6. Actie "vergeet dit apparaat" per apparaat; UserDeleted ruimt de gegevens van die gebruiker op.
  7. Eigenschapstest voor invariant I1 (regels zijn alleen beperkend zonder bevestiging).
  8. Tests en EVIDENCE.
- **Tests (verplicht):** xUnit over de staten. Negatief: (a) een verruimende regel wordt nooit actief zonder bevestiging, ook niet via import; (b) afwijzen of intrekken herstelt bij de volgende start het eerdere profiel; (c) een officiele app zonder opt-in krijgt geen enkele regel; (d) een kind kan niet bevestigen; (e) na UserDeleted staan er 0 rijen met de sleutel van die gebruiker. Commando: T-JL-PLUGIN met `--filter "FullyQualifiedName~Devices"`.
- **Poort:** P-jelly-leon (plugin, volledig) + P-CONTRACT + P-VEILIG.
- **Valkuilen:** V-003, V-005, V-050.
- **Bewijs:** B03-066 -> Bezig (Unit-getest; "meting op de testset volgt in S-G4-22 en S-G4-30"). JLT-41 -> Bezig met "serverdeel"; bij n kleiner dan 20 heet het een smoke-gate.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-VEILIG (VERPLICHT: wie mag een verruimende regel bevestigen) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard; R-VEILIG N4
- **Stop en vraag als:** de testset van B03-060 ontbreekt of niet bevroren is; een regel een profiel ruimer zou maken zonder bevestiging.

### S-G4-07 - Bescherming van stock-clients en de MediaGuard-afspeeltest
- **Repo:** jelly-leon | **Fase:** P4 (golf 4) | **Omvang:** groot | **Moeilijkheid:** hoog | **Zwaar:** ja (PlaybackInfo-vergelijking en meting achter stack.lock)
- **Werkpakketten en tests:** B03-068; JLT-46 (serverdeel); JLT-48
- **Vooraf:** S-G4-06. BG-26 (opt-in voor officiele apps en stock-clients).
- **Al gedaan?** `grep -n "UG-F5-" <WERKMAP>/jelly-leon/docs/platform-v2/UPSTREAM_GEDRAG.md | head -3` -> geen treffer = register nog niet aangevuld. `grep -rln "server_correction" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = niet gestart.
- **Lees eerst:** WP-JSON object B03-068; BOUWPLAN#F5.5.6 Compatibiliteitsgaranties; BOUWPLAN#F5.4.2 Wat F5 nooit schrijft; BOUWPLAN#F5.9.7 Gegevensbescherming; `<WERKMAP>/jelly-leon/docs/platform-v2/UPSTREAM_GEDRAG.md`
- **Bouw:**
  1. Standaard wijzigt de module nooit een meegestuurd apparaatprofiel van een stock-client of van een officiele app zonder opt-in, en weigert of verlaagt nooit een start. Bron: WP-JSON B03-068.
  2. Opt-in per apparaat: `client_advice` (officiele app; gebruiker op het eigen apparaat of beheerder) en `server_correction` (stock-client; alleen beheerder, alleen beperkend).
  3. `server_correction` via een filter vanuit de plugin als de spike F5-S2(b) dat toelaat; anders is het een core-patch en geldt "Stop en vraag als".
  4. Vaste uitsluiting: de MediaGuard-afspeeltest (profielnaam "MediaGuard afspeeltest" en aanroepen met een API-sleutel) wordt nooit aangepast.
  5. Regels UG-F5-1 tot en met UG-F5-13 in UPSTREAM_GEDRAG.md, elk met een contracttest die het bijwerken vanaf upstream blokkeert.
  6. Contracttests: PlaybackInfo met de vaste veldenlijst; eigenschapstest I1 over de upstream-testbestanden (19 apparaatprofielen keer 33 mediabronnen); OpenAPI-verschil alleen additief.
  7. Uitzetten, verwijderen en terug naar de stock-image met de gedocumenteerde restanten; beheeractie "alles van F5 verwijderen".
  8. Meting van de PlaybackInfo-vertraging met en zonder plugin, en EVIDENCE.
- **Tests (verplicht):** in de drie standen (plugin uit, aan, aan met opt-in voor een ander apparaat): 100 % identieke PlaybackInfo voor de niet-gekozen rollen en voor het profiel van de MediaGuard-afspeeltest. Negatief: (a) met opt-in krijgt alleen het gekozen apparaat minder Direct Play, nooit meer; (b) 0 geweigerde of verlaagde starts zonder opt-in; (c) een route of DTO buiten `/media/v1` en `/connector/v1` wijzigen laat de test falen; (d) na plugin uit, plugin verwijderd en terug naar de stock-image speelt Direct Play en transcode, en staan er alleen de gedocumenteerde restanten; (e) de negatieve gevallen van TEST-JSON rij JLT-48. Meting: p95-overhead van PlaybackInfo hooguit 20 ms, in het exclusieve meetslot. Commando's: T-JL-PLUGIN, T-JL-REGISTER, T-JL-COMPAT.
- **Poort:** P-jelly-leon (volledig, CI-volgorde) + P-CONTRACT + P-VEILIG + P-HARDE-EIS.
- **Valkuilen:** V-007, V-073, V-077, V-111.
- **Bewijs:** B03-068 -> Bezig (Sim-getest; "officiele apps in de emulator volgen in S-G4-30"). JLT-46 -> Bezig met "serverdeel". JLT-48 -> Bezig. "Derden-clients met legacy-headers: niet beweerd."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-VEILIG (VERPLICHT: profielcorrectie en opt-in-rechten) -> R-HARDE-EIS (VERPLICHT: stock-clients en de MediaGuard-afspeeltest blijven ongewijzigd) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4; R-HARDE-EIS N4
- **Stop en vraag als:** `server_correction` alleen met een core-patch kan (besluit van de gebruiker); een niet-gekozen client een andere PlaybackInfo krijgt en de oorzaak niet in de eigen code ligt.

### S-G4-08 - HDR/DV-, audio- en ondertitelregels en de uitleg "Waarom?" (serverdeel)
- **Repo:** jelly-leon | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** B03-067 (serverdeel); B03-005 (aanvulling F5); JLT-47 (serverdeel)
- **Vooraf:** S-G4-06. BG-28 (GPU-rollen) en BG-29 (kwaliteitslabel en feedback): zonder BG-29 levert de server de reden wel (route en opslag), maar markeert hij geen label voor de speler (veld leeg of `label: null`; de webstap S-G4-22 toont dan niets).
- **Al gedaan?** `grep -rln "why-transcode\|WhyTranscode" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = niet gestart.
- **Lees eerst:** WP-JSON object B03-067; BOUWPLAN#F5.3.5 HDR/DV, audio en ondertitels; BOUWPLAN#F5.5.2 Endpoints; BOUWPLAN#F5.9.3 E2E; BOUWPLAN#F5.7 Configuratieopties
- **Bouw:**
  1. Beslisregels, alleen waar het profieladvies aan staat: tonemapping alleen als het scherm SDR is en de client niet zelf tonemapt. Bron: WP-JSON B03-067.
  2. Dolby Vision per profiel: profiel 5 naar een DV-client of OpenCL-tonemapping (nooit VPP); 8.1 naar de HDR10-basislaag waar HDR10 bevestigd is; 8.4 naar HLG of tonemapping; AV1 met profiel 10 naar HDR10-basis of tonemapping.
  3. Audio: passthrough alleen na bevestiging; anders kanalen behouden tot het gemeten maximum; downmix met het algoritme van upstream.
  4. Ondertitels: tekst extern; ASS en PGS door de client waar dat kan; inbranden alleen als laatste stap en altijd met een reden.
  5. Per afspeelbeslissing een Nederlandse reden die de webmodule als label en in "Waarom?" kan tonen; debuggegevens per client (bandbreedte, reden van transcoderen, node, werkklasse).
  6. Tests op het corpus en EVIDENCE.
- **Tests (verplicht):** op het corpus (DV-profielen, HDR10, verkeerd HLG-label, Sintel met 10 SRT-sporen, ToS met NL en EN): elk afwijkend afspeelpad heeft een reden. Negatief: (a) DV-profiel 5 krijgt nooit VPP; (b) geen HDR-stroom zonder tonemapping naar een bevestigd SDR-scherm zonder client-tonemapping; (c) tekstondertitels 0 keer ingebrand; (d) een stock-client en een officiele app zonder opt-in krijgen dezelfde afspeelbeslissing als op stock. Commando: T-JL-PLUGIN met `--filter "FullyQualifiedName~Devices"`.
- **Poort:** P-jelly-leon (plugin, volledig) + P-CONTRACT.
- **Valkuilen:** V-003, V-073, V-099.
- **Bewijs:** B03-067 -> Bezig (Sim-getest; serverdeel). JLT-47 -> Bezig met "PGS/VobSub, TrueHD/DTS/Atmos en DV-profiel 7: Geblokkeerd tot er een testbestand met licentie is". B03-005 -> Bezig met "echte DV-apparaten en tv's: NIET GEVALIDEERD (hardware) tot JLT-49".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** een regel alleen te testen is met een bestand zonder licentie in het corpus; een regel het gedrag voor een niet-gekozen client zou veranderen.

### S-G4-09 - Watch Together: diagnose per deelnemer en capaciteitsadvies voor de start
- **Repo:** jelly-leon | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (voorspellingsproef met een echte server en drie browsers achter stack.lock)
- **Werkpakketten en tests:** B03-025 (rest: diagnose, voorspelling, advies, lane bij groepspauze); JLT-04
- **Vooraf:** S-G4-04 (capaciteit van de laneplanner) en S-G3-19 (haperbeleid). BG-13: zonder besluit bij groepstart alleen waarschuwen.
- **Al gedaan?** `grep -rln "GroupPauseLaneHoldMinutes" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = niet gestart. `grep -rn "admission" <WERKMAP>/jelly-leon/plugins/JellyLeon/src --include=*.cs -il` -> geen uitvoer = route E19 ontbreekt.
- **Lees eerst:** WP-JSON object B03-025; TEST-JSON rij JLT-04; BOUWPLAN#F1.5.2 Endpoints (E19); BOUWPLAN#F1.3.5 GPU/CPU/RAM-budget op de NAS; BOUWPLAN#F1.7 Configuratieopties
- **Bouw:**
  1. Diagnose per deelnemer, alleen lezen: afspeelmethode, reden van transcoderen, hardwareversnelling. Bron: WP-JSON B03-025.
  2. Voorspelling voor de start met de StreamBuilder van upstream en het laatst gemelde apparaatprofiel. De voorspelling start geen transcode en schrijft niets.
  3. Advies met de capaciteit van de planner erbij, in de vorm "2 van 3 moeten omzetten; capaciteit 1", met een reden.
  4. Route E19 `GET .../groups/{groupId}/admission`; het volledige pad en het schema staan in BOUWPLAN#F1.5.2 en #F1.5.3.
  5. Instelling `Admission`: alleen de opt-in-stand `blokkeren` mag een groepstart vanuit Jelly Leon-web tegenhouden. De module weigert nooit een stock-client en start zelf geen transcode.
  6. Bij groepspauze de lane vasthouden gedurende `GroupPauseLaneHoldMinutes` (standaard 30); `MaxParticipants` standaard 8.
  7. Voorspellingsproef op de 25 corpusitems en EVIDENCE.
- **Tests (verplicht):** xUnit: diagnose en advies met een nagebootste planner op de grens (vol, leeg) en met de MediaGuard-simulator vol, leeg en onbereikbaar. Negatief: (a) boven de grens wordt een stock-client door de module niet geweigerd; (b) zonder de opt-in `blokkeren` wordt geen enkele groepstart tegengehouden; (c) MediaGuard onbereikbaar geeft het advies "onbekend" en geen weigering; (d) de voorspelling start 0 transcodes (aantal ffmpeg-processen voor en na gelijk); (e) hervatten binnen de houdtijd houdt dezelfde lane, na de houdtijd is de lane vrij. Proef (achter stack.lock): voorspelling tegenover de werkelijke PlaybackInfo voor alle 25 corpusitems in Chromium, Firefox en WebKit; eis: minstens 95 % gelijk. De proef komt in het harnas (voorbeeld voor een browserproef: `tools/b03-harnas/playwright/harnas.mjs`, onderdeel `web` van `b03h clientmatrix`). Commando's: T-JL-PLUGIN met `--filter "FullyQualifiedName~Watch"`, T-JL-HARNAS, daarna de proef met `flock <WERKMAP>/.lokaal/stack.lock`.
- **Poort:** P-jelly-leon (plugin, volledig) + P-CONTRACT.
- **Valkuilen:** V-003, V-009, V-073, V-098. Eigen: een voorspelling die de echte PlaybackInfo-route aanroept kan een transcode starten; gebruik alleen de alleen-lezen weg.
- **Bewijs:** B03-025 -> Bezig (Sim-getest; met het gemeten percentage en n = 25 per browser). JLT-04 -> Bezig met "desktop: Geblokkeerd als de desktopspike faalde" en "A310 en UHD 770: NIET GEVALIDEERD (hardware): meting op de echte NAS nodig; zie STAPPEN_P6.md".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** het advies alleen te geven is door een start te weigeren of te verlagen (no-go); de voorspelling onder 95 % blijft en de oorzaak in upstream ligt (melden met de afwijkende items, niet de drempel verlagen).

### S-G4-10 - Watch Together: chat en reacties, serverdeel (alleen na BG-12)
- **Repo:** jelly-leon | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** B03-028 (serverdeel); JLT-05 (voorwaardelijk deel chat); JLT-09 (deel: alleen in het geheugen)
- **Vooraf:** S-G3-18 (kinderregels). BG-12 genomen met "aan". Zegt het besluit "uit" of ontbreekt het, dan VERVALT deze stap (BESLUITEN_EN_BLOKKADES.md, kop BG-12: "B03-028 wordt niet gebouwd"); de regisseur zet dan alleen de bewijsregel B03-028 -> "Geblokkeerd (besluit BG-12)" via de eerstvolgende stap in jelly-leon.
- **Al gedaan?** `grep -rn "groups/{[a-zA-Z]*}/messages" <WERKMAP>/jelly-leon/plugins/JellyLeon/src --include=*.cs -l` -> geen uitvoer = niet gestart.
- **Lees eerst:** WP-JSON object B03-028; BOUWPLAN#F1.5.2 Endpoints (E14, E15); BOUWPLAN#F1.4.4 Privacy; BOUWPLAN#F1.9.5 Negatief en veiligheid; BOUWPLAN#F1.8 Bouwfasen (regel WT-7)
- **Bouw:**
  1. Routes E14 `POST /media/v1/watch/groups/{id}/messages` en E15 `GET .../messages` (long-poll met `after` en `wait` van hooguit 25 s). Met de instelling uit (de standaard na installatie) geven beide 501 `capability_unavailable`. Bron: WP-JSON B03-028.
  2. Aan: vaste reacties (duim, lach, verbaasd, hart, applaus) en korte tekst van hooguit 200 tekens, zonder HTML en zonder links.
  3. Opslag alleen in het geheugen: nooit in een database, logboek, event of antwoord aan de Hub. Na het einde van de groep of een herstart van de server is alles weg.
  4. Snelheidslimiet 5 berichten per 10 s per gebruiker, op de aangemelde gebruiker en niet op een header van de aanvrager.
  5. Kinderen standaard uit: een kind zonder toestemming kan niet sturen en niet lezen (via `IsKid(user)` uit `PLUGIN/Core/Privacy/KidPolicy.cs`).
  6. Alleen leden van de groep kunnen sturen en lezen; native stock-clients krijgen niets toegestuurd.
  7. Tests en EVIDENCE.
- **Tests (verplicht):** standaard uit geeft 501 op E14 en E15. Aan: een lid stuurt en een ander lid leest. Negatief: (a) een niet-lid krijgt hetzelfde antwoord als bij een niet-bestaande groep; (b) meer dan 5 berichten in 10 s geeft 429 met Retry-After; (c) tekst met HTML of script komt als platte tekst terug, een link en een tekst van 201 tekens worden geweigerd; (d) een kind zonder toestemming krijgt 403 op sturen en lezen; (e) na de test bevat geen enkel bestand in de datamap, geen logregel en geen outbox-rij de unieke testtekst (zoek op een unieke tekenreeks); (f) na het einde van de groep geeft E15 niets meer terug. Commando: T-JL-PLUGIN met `--filter "FullyQualifiedName~Watch"`, daarna volledig.
- **Poort:** P-jelly-leon (plugin, volledig) + P-CONTRACT + P-VEILIG.
- **Valkuilen:** V-042, V-049, V-050, V-094. Eigen: een logregel op debugniveau met de berichttekst breekt de regel "alleen in het geheugen".
- **Bewijs:** B03-028 -> Bezig (Unit-getest; "webdeel volgt in S-G4-24"). JLT-05 en JLT-09 -> Bezig met "deel chat". (Vervalt de stap door BG-12: B03-028 -> "Geblokkeerd (besluit BG-12)".)
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-VEILIG (VERPLICHT: invoer van gebruikers, snelheidslimiet, kinderregel, niets op schijf) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard; R-VEILIG N4
- **Stop en vraag als:** BG-12 niet "aan" is (de stap had dan niet mogen starten); de long-poll alleen werkt met opslag buiten het geheugen.

### S-G4-11 - Watch Together: connector-items en events voor de Hub
- **Repo:** jelly-leon | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** B03-029 (serverdeel); JLT-09 (deel connector en events)
- **Vooraf:** S-G3-17 tot en met S-G3-20. De Hub-pin JL4 van golf 1 bestaat (`ls <WERKMAP>/jelly-leon/plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Core/Hub/HubPin.cs`).
- **Al gedaan?** `grep -rln "watch_together_stats" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = niet gestart. `grep -rln "media.watchgroup" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = events ontbreken.
- **Lees eerst:** WP-JSON object B03-029; BOUWPLAN#F1.5.4 Connectorcontract (§6) voor de Hub; BOUWPLAN#F1.5.5 Events; BOUWPLAN#10.4 Hub-koppeling (JL4) en wat de Hub te zien krijgt; `PLUGIN/Core/Connector/ConnectorService.cs`
- **Bouw:**
  1. Connector-itemtype `watch_together_stats` op `GET /connector/v1/items?type=watch_together_stats`: actieve groepen, deelnemers, volgers, VPN/extern, transcoderend, p95-drift over 24 uur, status van de decorator. Alleen aantallen. Bron: WP-JSON B03-029.
  2. Events `media.watchgroup.started`, `.ended`, `.degraded`, `.blocked` via de ene outbox (`PLUGIN/Core/Outbox/Outbox.cs`), classification internal.
  3. Nooit namen, titels, paden, IP-adressen of chattekst in items of events; de inhoudsbewaker van de outbox (`PLUGIN/Core/Outbox/InhoudsBewaker.cs`) weigert ze.
  4. Toegang voor de Hub alleen met een Hub-JWT na een gepinde sleutelset; zonder pin 401 `not_linked`; rol kind 403. Hergebruik de bestaande controle; bouw geen tweede.
  5. De uurlijkse controle via de MediaGuard-viewerclient die de WP-tekst "G8" noemt: lees de inhoud in WP-JSON B03-029 en BOUWPLAN#F1.10 MediaGuard-integratie; alleen GET.
  6. Schema's in de OpenAPI van de plugin; tests en EVIDENCE.
- **Tests (verplicht):** schematest op items en events: geen veld met naam, titel, pad, IP-adres of chattekst. Negatief: (a) zonder pin 401 `not_linked`; (b) een Hub-JWT met rol kind geeft 403; (c) een event met een verboden veld wordt door de outbox geweigerd en de test ziet de weigering; (d) is de decorator-status onbekend, dan staat er `unknown` en nooit een goede status; (e) een eventnaam heeft precies drie segmenten. Commando: T-JL-PLUGIN met `--filter "FullyQualifiedName~Watch"`, daarna volledig (de kerntests `ConnectorTests`, `OutboxTests`, `HubTokenTests` blijven groen).
- **Poort:** P-jelly-leon (plugin, volledig) + P-CONTRACT + P-VEILIG.
- **Valkuilen:** V-001, V-046, V-047, V-054, V-105.
- **Bewijs:** B03-029 -> Bezig (Unit-getest; "Hub-kaart volgt in S-G4-33; clientmatrix volgt in S-G4-39"). JLT-09 -> Bezig met "deel". "Tegen de echte Hub: NIET GEVALIDEERD tot S-G4-33 de items uitleest."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-VEILIG (VERPLICHT: Hub-toegang en wat de Hub te zien krijgt) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard; R-VEILIG N4
- **Stop en vraag als:** de pin van golf 1 ontbreekt of anders werkt dan BOUWPLAN#10.4 beschrijft; een eventnaam botst met de werkwoordenlijst van het contract (dan eerst S-G4-19 of een besluit).

### S-G4-12 - Aanbevelingen: connector-items, gedragsregister en prestatiemeting
- **Repo:** jelly-leon | **Fase:** P4 (golf 4) | **Omvang:** groot | **Moeilijkheid:** gewoon | **Zwaar:** ja (meting in het exclusieve meetslot achter stack.lock; image-build)
- **Werkpakketten en tests:** B03-039 (serverdeel); JLT-19
- **Vooraf:** B03-035 (golf 2; gate G-F2-5). Gate G-F2-9 is de uitkomst van deze stap samen met S-G4-34.
- **Al gedaan?** `grep -n "UG-F2-" <WERKMAP>/jelly-leon/docs/platform-v2/UPSTREAM_GEDRAG.md | head -3` -> geen treffer = register nog niet aangevuld. `ls <WERKMAP>/jelly-leon/docs/platform-v2/test-evidence | grep -i "jlt-19\|prestatie"` -> geen uitvoer = meting nog niet gedaan.
- **Lees eerst:** WP-JSON object B03-039; TEST-JSON rij JLT-19; BOUWPLAN#F2.9.6 Prestatie (JLT-19); BOUWPLAN#F2.5.4 Beheer- en Hub-routes; BOUWPLAN#F2.3.1a Register van upstream-gedrag
- **Bouw:**
  1. Status- en connector-items voor de Hub-kaart H-1 en het detail H-2: alleen aantallen, dekking en de evaluatieclaim met haar validatielabel; geen gegevens per gebruiker, geen titels, geen bibliotheeknamen. Bron: WP-JSON B03-039; BOUWPLAN#F2.5.4.
  2. Toegang als in S-G4-11: Hub-JWT na pin, zonder pin 401 `not_linked`, rol kind 403.
  3. Regels UG-F2-1 tot en met UG-F2-8 in `docs/platform-v2/UPSTREAM_GEDRAG.md`, elk met een contracttest; F2 opnemen in de proef voor bijwerken vanaf upstream (`tools/jelly-leon/upstream_sync.py`; opties in het bestand lezen).
  4. Een bibliotheek van 10 000 nagebootste items voor de meting. Of het harnas die al kan maken: ONBEKEND - eerst vaststellen met: `grep -rln "10000\|10_000" <WERKMAP>/jelly-leon/tools/b03-harnas/b03h <WERKMAP>/jelly-leon/tools/jelly-leon`. Bestaat het niet, dan bouwt deze stap het in het harnas, met een pytest erbij.
  5. Meting in het exclusieve meetslot (`tools/b03-harnas/b03h/meetslot.py`): minstens 3 runs, stock en Jelly Leon afwisselend; een run met een 1-minuut-belasting boven 2,0 is ongeldig en telt niet als mislukt (BOUWPLAN#F2.9.6 en WP-JSON B03-039 noemen 2,0; dat is strenger dan de standaard van het harnas, `LASTGRENS` 4.0: draai deze meting daarom met `B03_LASTGRENS=2.0` en zet dat in het rapport).
  6. Gemeten worden: startschermrij p95 koud en warm, Similar p95 tegenover stock, extra geheugen (PSS), volledige herberekening op 1 thread, plannerpauze bij Direct Play en bij transcode, en gelezen bytes op de mediamap.
  7. Rapport onder `docs/platform-v2/test-evidence/` en EVIDENCE.
- **Tests (verplicht):** grenzen uit de acceptatie: startschermrij p95 hooguit 250 ms koud en 50 ms warm; Similar p95 hooguit 1,5 keer stock; extra PSS hooguit 200 MiB; herberekening hooguit 120 s op 1 thread bij 10 000 items; gelezen bytes op media = 0. Negatief: (a) een ongeldige run (belasting boven 2,0) wordt in het rapport als ongeldig geteld en niet stil weggelaten; (b) de herberekening pauzeert bij een actieve sessie van beide soorten; (c) zonder pin 401; (d) de syncproef is groen of faalt terecht met exitcode 2 en een leesbare reden. Commando's: T-JL-PLUGIN met `--filter "FullyQualifiedName~Recommend"` (controleer de naam van de modulemap), T-JL-REGISTER, T-JL-HARNAS, T-JL-IMAGE, daarna de meting achter stack.lock.
- **Poort:** P-jelly-leon (volledig, CI-volgorde) + P-CONTRACT.
- **Valkuilen:** V-005, V-009, V-032, V-057, V-098. Eigen: een meting terwijl een andere keten bouwt is ongeldig; plan haar aan het eind van een blok.
- **Bewijs:** B03-039 -> Bezig (Sim-geslaagd of Sim-mislukt, met de gemeten waarden en het aantal geldige runs). JLT-19 -> Bezig met "ontwikkelmachine; gedrag op de NAS: NIET GEVALIDEERD (echte NAS)". JLT-15 -> Geblokkeerd: "NIET GEVALIDEERD (echte NAS): echte bibliotheek en echte huishoudhistorie nodig (BG-37); zie STAPPEN_P6.md".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-VEILIG (VERPLICHT: Hub-toegang en geen gegevens per gebruiker naar de Hub) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard; R-VEILIG N4
- **Stop en vraag als:** een grens niet gehaald wordt (melden als Sim-mislukt met de waarde; de grens niet aanpassen); de meting drie keer achter elkaar ongeldig is door belasting van andere ketens (regisseur plant een rustig moment).

### S-G4-13 - Ondertitels: de gesynchroniseerde kopie als gemarkeerd spoor, nooit standaard
- **Repo:** jelly-leon | **Fase:** P4 (golf 4) | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** B03-049 (P4-deel: gesynchroniseerde kopieen); JLT-25 (serverdeel)
- **Vooraf:** S-G3-08 (publicatie en spoorkeuzes). BG-19 en BG-21 zijn daar al toegepast.
- **Al gedaan?** `grep -rn "JLT-25" <WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json | head -2` en lees de status; staat er alleen "Niet gestart", dan is de stap niet gedaan.
- **Lees eerst:** WP-JSON object B03-049 (alleen het deel "gesynchroniseerde kopieen"); TEST-JSON rij JLT-25; BOUWPLAN#F3.4.4 Onthouden spoorkeuzes; BOUWPLAN#F3.8 (regel 3B); WP-JSON object B03-047
- **Bouw:**
  1. Geen client- en geen core-patch: de gepubliceerde gesynchroniseerde kopie verschijnt als een gewoon extern spoor met de markering in de naam die S-G3-08 heeft vastgelegd. Kies geen nieuwe naam. Bron: WP-JSON B03-049.
  2. Test dat de gesynchroniseerde kopie nooit de standaardkeuze wordt (vlaggen `IsDefault` en `IsForced` niet gezet; de keuzeregels van upstream kiezen haar niet boven een menselijk spoor in dezelfde taal).
  3. Test dat PlayMethod en TranscodeReasons met en zonder het spoor gelijk zijn.
  4. De standaardkeuze per clientrol vastleggen in `docs/platform-v2/CLIENT_COMPAT_MATRIX.md` voor zover dat op de server meetbaar is; de clients zelf volgen in S-G4-30.
  5. EVIDENCE.
- **Tests (verplicht):** integratietest op een corpusitem met een menselijk NL-spoor en een gesynchroniseerde kopie. Negatief: (a) verwijder je het menselijke spoor uit de test, dan mag de kopie nog steeds niet als `IsDefault` verschijnen; (b) PlaybackInfo met en zonder het spoor geeft dezelfde PlayMethod en dezelfde TranscodeReasons; (c) na depubliceren is het spoor weg en is de antwoordinhoud gelijk aan stock. Commando: T-JL-PLUGIN met `--filter "FullyQualifiedName~Subtitles"`.
- **Poort:** P-jelly-leon (plugin, volledig) + P-HARDE-EIS.
- **Valkuilen:** V-003, V-111, V-113.
- **Bewijs:** B03-049 -> Bezig met "P4-deel; machinevertaling, events, connector-items en Hub-kaart horen bij P5 (S-P5-107, S-P5-62 in STAPPEN_P5.md)". JLT-25 -> Bezig met "serverdeel; clients volgen in S-G4-30; machinevertaling volgt in P5". JLT-26 -> Geblokkeerd: "NIET GEVALIDEERD (echte NAS); zie STAPPEN_P6.md".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-HARDE-EIS (VERPLICHT: spoorkeuzes van gebruikers blijven ongemoeid) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard; A-BOUW N2 mag (klein en mechanisch); R-HARDE-EIS N4
- **Stop en vraag als:** de kopie alleen uit de standaardkeuze te houden is door een opgeslagen spoorkeuze van een gebruiker te wijzigen (no-go buiten BG-21).

### S-G4-14 - Quality: connector-items, bewijsroute en health-checks voor de Hub
- **Repo:** jelly-leon | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** B03-058 (serverdeel); JLT-38 (deel connector)
- **Vooraf:** S-G3-15. Subfase QC-6. De Hub-pin JL4 bestaat.
- **Al gedaan?** `grep -rln "quality_summary\|quality_finding" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = niet gestart.
- **Lees eerst:** WP-JSON object B03-058; BOUWPLAN#F4.5.5 Connectorcontract (§6) waar de Hub F4 gebruikt; BOUWPLAN#F4.5.6 Events; BOUWPLAN#F4.8 (regel QC-6); `PLUGIN/Core/Connector/ConnectorService.cs`
- **Bouw:**
  1. Connector-itemtypen `quality_summary` en `quality_finding` op `/connector/v1/items`. De entiteit is `quality_finding` met een willekeurige `finding_id`; nooit item_id, titel, bestandsnaam, pad, gebruikers- of apparaatnaam. Bron: WP-JSON B03-058.
  2. Route `/connector/v1/evidence/{id}`: alleen meetwaarden, tijdvensters en de naam van de detector; geen beeld en geen logfragment.
  3. Events van de module via de ene outbox op `/connector/v1/events` (de Hub pollt); drie segmenten, hooguit 16 KiB, ontdubbeling op `source_event_id`.
  4. Health-checks `quality_worker`, `quality_media_mount` en `quality_mediaguard` in de bestaande health-uitvoer, met een leeftijd van de meting.
  5. `propose`, `apply` en `rollback` geven 501 `capability_unavailable`. Herstel loopt alleen als deeplink (zie S-G3-15).
  6. OpenAPI, tests en EVIDENCE.
- **Tests (verplicht):** schematest: geen van de verboden velden in items, bewijs of events. Negatief: (a) zonder pin 401 `not_linked`; (b) rol kind 403; (c) `propose`, `apply`, `rollback` geven 501; (d) een bewijs-ID van een onderdrukte of niet-bestaande bevinding geeft 404 zonder inhoud; (e) een event groter dan 16 KiB wordt geweigerd; (f) een health-check zonder verse meting meldt niet "gezond". Commando: T-JL-PLUGIN met `--filter "FullyQualifiedName~Quality"`, daarna volledig.
- **Poort:** P-jelly-leon (plugin, volledig) + P-CONTRACT + P-VEILIG.
- **Valkuilen:** V-046, V-051, V-054, V-105.
- **Bewijs:** B03-058 -> Bezig (Unit-getest; "Hub-kaart en incidenten volgen in S-G4-36"). JLT-38 -> Bezig met "deel connector". "Hub-uitvoering van herstel via de MediaGuard-adapter: Geblokkeerd (contract; BG-05)."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-VEILIG (VERPLICHT: wat de Hub te zien krijgt; geen titels, paden of beelden) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard; R-VEILIG N4
- **Stop en vraag als:** de Hub voor een incident meer nodig lijkt te hebben dan een ondoorzichtig ID (niet toevoegen; melden).

### S-G4-15 - Segmenten: correctieroutes, review, meldingen en voorkeur per gebruiker
- **Repo:** jelly-leon | **Fase:** P4 (golf 4) | **Omvang:** groot | **Moeilijkheid:** hoog | **Zwaar:** nee
- **Werkpakketten en tests:** B03-075 (deel routes, rechten, correctielog en voorkeur); JLT-54 (deel correctie, rechten en voorkeur); JLT-56 (onderdeel h: gebruiker verwijderd)
- **Vooraf:** B03-071, B03-072 en B03-073 (golf 2: segmentprovider met `segments.db`, audio-engine, aftiteling en post-credit-bescherming) en S-G3-22. BG-33 (wie mag corrigeren): zonder besluit alleen beheerders, en nieuwe segmenten blijven in schaduwmodus. Subfase F6-S5.
- **Al gedaan?** `ls <WERKMAP>/jelly-leon/plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Modules` -> staat er geen map voor de segmentmodule, dan is golf 2 niet klaar (STOP). `grep -rln "later_correction_exists\|not_editor" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = niet gestart.
- **Lees eerst:** WP-JSON object B03-075; BOUWPLAN#F6.5.4 Endpoints (routes 2 tot en met 8 en 17); BOUWPLAN#F6.4.5 Persoonsgegevens, privacy en rechten; BOUWPLAN#F6.5.2 Foutcodes; BOUWPLAN#F6.7 Configuratieopties
- **Bouw:**
  1. Routes 2, 3 en 4 (corrigeren, ongedaan maken, geschiedenis) onder `/media/v1/segments/{itemId}/...`, met `If-Match` en `Idempotency-Key`: een verouderde ETag geeft 412, ongedaan maken van een correctie waar een latere op voortbouwt geeft 409 `later_correction_exists`. Bewerkingen: bevestigen, afwijzen, grens aanpassen, toevoegen, verwijderen, type wijzigen, scene markeren als beschermd. Bron: WP-JSON B03-075; BOUWPLAN#F6.5.4 Endpoints.
  2. Alleen-toevoegen-tabel `corrections` in `segments.db` (nooit bijwerken of wissen); de auteur is alleen voor beheerders zichtbaar. Publicatie na een correctie loopt via de bestaande gerichte publicatie onder de eigen provider-ID (B03-071); deze stap schrijft zelf geen andere MediaSegments-rijen.
  3. Rechten: beheerders, en (alleen als BG-33 dat toestaat) de gebruikers in `SegmentEditorUserIds`; zonder besluit telt de lijst niet. Een gebruiker met `IsKid` is nooit editor, ook niet als hij in de lijst staat. Niet-editor -> 403 `not_editor`; een item buiten de bibliotheekrechten van de gebruiker -> 404 (zichtbaarheid via `GetItemById(itemId, userId)`). Bron: BOUWPLAN#F6.4.5.
  4. Route 5 ("Klopt niet"): alleen volwassen kijkers; `IsKid` -> 403 `kid_profile`; meer dan `ReportRateLimitPerUserPerDay` meldingen -> 429 met `Retry-After`; antwoord 202. Een melding maakt alleen een reviewitem en verandert nooit een segment. Bewaartermijn: tot afhandeling plus `ReportRetentionDaysAfterHandled`.
  5. Routes 6, 7 en 8 (reviewlijst, families lezen, familie labelen); de reviewlijst toont alleen items die de gebruiker mag zien.
  6. Route 17 (voorkeur per gebruiker) in de tabel `preferences` van `segments.db`: alleen de gebruiker uit het token; `IsKid` mag alleen `ask`, `none` of `default`. Schrijf nooit DisplayPreferences of een andere upstream-instelling. Bron: WP-JSON B03-075 ("geen DisplayPreferences").
  7. Gebruiker verwijderd: meld de tabellen aan bij de gemeenschappelijke privacylaag (`PLUGIN/Core/Privacy/PrivacyService.cs`): auteur in `corrections` wordt een pseudoniem, `reports` en `preferences` van die gebruiker worden gewist.
  8. Events `media.segment.corrected` en `media.segment.review_requested` (hooguit 1 per serie per uur) via de ene outbox, zonder titels en namen; alle routes in de OpenAPI; EVIDENCE.
- **Tests (verplicht):** per route een geslaagd pad en: ongedaan maken herstelt exact de vorige versie. Negatief: (a) niet-editor -> 403; (b) `IsKid` in de editorlijst -> toch 403; (c) item buiten de bibliotheekrechten -> 404; (d) verouderde ETag -> 412 en niets gewijzigd; (e) dezelfde `Idempotency-Key` twee keer -> hetzelfde antwoord en een enkele correctie; (f) de 21e melding op een dag (standaard 20) -> 429; (g) melding door `IsKid` -> 403 `kid_profile`; (h) voorkeur van een andere gebruiker lezen of zetten lukt niet; (i) na het verwijderen van een gebruiker 0 rijen met diens GUID in `segments.db`; (j) na het zetten van een voorkeur is DisplayPreferences in de testdatabase ongewijzigd. Commando: T-JL-PLUGIN met `--filter "FullyQualifiedName~Segment"`, daarna volledig.
- **Poort:** P-jelly-leon (plugin, volledig) + P-CONTRACT + P-VEILIG + P-HARDE-EIS.
- **Valkuilen:** V-003, V-042, V-049, V-055, V-066, V-112.
- **Bewijs:** B03-075 -> Bezig (Unit-getest; "leren volgt in S-G4-40"). JLT-54 -> Bezig met "deel correctie en voorkeur". JLT-56 -> Bezig met "onderdeel h". JLT-59 -> Geblokkeerd: "NIET GEVALIDEERD (echte NAS); NIET GEVALIDEERD (hardware); zie STAPPEN_P6.md".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-VEILIG (VERPLICHT: rechten per route, kinderprofiel, zichtbaarheid van items) -> R-HARDE-EIS (VERPLICHT: voorkeuren en correcties raken gebruikersgegevens; geen upstream-instelling geschreven) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4; R-HARDE-EIS N4; overig standaard
- **Stop en vraag als:** de segmentmodule van golf 2 ontbreekt; BG-33 een andere editorgroep kiest dan de standaard en de code dat niet kan uitdrukken; de voorkeur alleen werkt door een upstream-instelling te schrijven.

### S-G4-40 - Segmenten: leren van bevestigde correcties, heranalyse en kwaliteitsmeting
- **Repo:** jelly-leon | **Fase:** P4 (golf 4) | **Omvang:** groot | **Moeilijkheid:** hoog | **Zwaar:** ja (holdout-meting op het corpus achter stack.lock)
- **Werkpakketten en tests:** B03-075 (deel leren; routes 10, 11 en 13); JLT-54 (rest: doorgeven en grensfout)
- **Vooraf:** S-G4-15 en S-G3-22 (families en varianten). Subfase F6-S5. Dit nummer is later toegevoegd en hoort in de volgorde direct na S-G4-15.
- **Al gedaan?** `grep -rln "AutoPropagateConfirmed" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = niet gestart. Alleen een treffer in `Configuration/PluginConfiguration.cs` = optie bestaat, gedrag nog niet.
- **Lees eerst:** WP-JSON object B03-075; BOUWPLAN#F6.3.7 Leren van bevestigde correcties; BOUWPLAN#F6.3.4 Post-credit-bescherming en grensregels; BOUWPLAN#F6.1.3 Testopzet, n en statistiek; TEST-JSON rij JLT-54
- **Bouw:**
  1. Doorgeven per variant: een bevestigde grens gaat via de uitlijning naar de andere afleveringen van dezelfde variant. Standaard als voorstel (`AutoPropagateConfirmed=propose`); bij `apply_high_confidence` alleen toepassen bij een zekerheid van 0,9 of hoger; bij `off` niets. Bron van zo'n segment: `propagated`. Bron: BOUWPLAN#F6.3.7.
  2. Gezag: handmatig en bevestigd gaan voor doorgegeven, en doorgegeven gaat voor gedetecteerd, hoofdstuk en hint. Een menselijk segment wordt nooit automatisch overschreven; een botsing wordt een reviewitem.
  3. Voorkennis per serie en lokale kalibratie per bibliotheek, in de plugin zelf, met versienummer, holdout en terugrol. Een nieuwe kalibratie wordt alleen actief als de holdout niet verslechtert en er 0 post-credit-schendingen zijn.
  4. Onderdrukking: een afgewezen fragment komt na heranalyse niet terug.
  5. Alleen correcties van editors leren het systeem; een kijkersmelding niet. Met `LearningEnabled=false` wordt er niets doorgegeven of gekalibreerd.
  6. Elke doorgerekende grens gaat opnieuw door de post-credit-regels (`PostCreditGuardSeconds`) voordat hij voorstel of segment wordt.
  7. Routes 10 en 11 (heranalyse aanvragen en taakstatus; `rederive` herberekent afgeleide gegevens en nooit menselijke; 409 `already_queued`; 503 `worker_unavailable`) en route 13 (doorlopende kwaliteitscijfers per type). De planner van golf 1 bepaalt wanneer een taak draait.
  8. Holdout-meting in het harnas, rapport onder `docs/platform-v2/test-evidence/`, EVIDENCE.
- **Tests (verplicht):** holdout met minstens 5 varianten van elk minstens 4 afleveringen: na 1 bevestigde correctie per variant daalt de p95-grensfout op de overige afleveringen met minstens 50 % (alleen te beoordelen als die fout vooraf groter dan 1 s was; anders eerlijk "niet van toepassing" melden) en blijven de post-credit-schendingen 0. Negatief: (a) een kalibratie die de holdout verslechtert wordt niet geactiveerd; (b) een menselijk segment wordt bij doorgeven niet overschreven; (c) een afgewezen fragment komt na heranalyse niet terug; (d) een kijkersmelding verandert geen label en geen grens; (e) bij `propose` wordt niets gepubliceerd; (f) een meting over een lege holdout faalt en meldt geen 100 % (V-005). Commando's: T-JL-PLUGIN met `--filter "FullyQualifiedName~Segment"`; het meetcommando voor de holdout is ONBEKEND - eerst vaststellen met: `ls <WERKMAP>/jelly-leon/tools/b03-harnas/b03h/corpus/r_f6_segmenten.py` en `grep -n "segment" <WERKMAP>/jelly-leon/tools/b03-harnas/README.md`; de bouwer schrijft het exacte commando in dat README. Meting achter `flock <WERKMAP>/.lokaal/stack.lock`.
- **Poort:** P-jelly-leon (plugin, volledig; job `b03-harnas`) + P-CONTRACT + P-HARDE-EIS.
- **Valkuilen:** V-005, V-042, V-058, V-066, V-098, V-112.
- **Bewijs:** B03-075 -> Bezig (Sim-getest; rapport met n, varianten en grensfout voor en na). JLT-54 -> Bezig. Het deel met echte afleveringen: Geblokkeerd met "NIET GEVALIDEERD (echte NAS): bevestigde labels nodig (BG-34)".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-HARDE-EIS (VERPLICHT: menselijk werk wordt nooit automatisch overschreven of gewist) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); R-HARDE-EIS N4; overig standaard
- **Stop en vraag als:** de drempel van 50 % niet wordt gehaald (meld de gemeten waarde; niet de testset aanpassen); de holdout minder dan 5 varianten heeft; doorgeven alleen werkt door de testset na het afstemmen te wijzigen.

### S-G4-16 - Beheerpagina "Intro's en aftiteling" en afronding van B03-007
- **Repo:** jelly-leon | **Fase:** P4 (golf 4) | **Omvang:** groot | **Moeilijkheid:** gewoon | **Zwaar:** ja (image en browsertest achter stack.lock)
- **Werkpakketten en tests:** B03-076 (serverdeel: beheerpagina); B03-007 (afronding, serverdeel); JLT-56 (eindrun); JLT-55 (serverdeel: marge aan het einde van het bestand)
- **Vooraf:** S-G4-15 en S-G4-40. BG-31 (standaardgedrag van de knoppen): zonder besluit overal vragen en nooit automatisch overslaan. Het gedrag van "module uit" volgt het besluit BG-36 dat bij golf 2 hoort.
- **Al gedaan?** `grep -rln "IHasWebPages" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> lees welke pagina's al geregistreerd zijn (S-G3-16 voegde de pagina "Mediakwaliteit" toe). `grep -rli "aftiteling" <WERKMAP>/jelly-leon/plugins/JellyLeon/src --include=*.html --include=*.js` -> geen uitvoer = pagina nog niet gebouwd.
- **Lees eerst:** WP-JSON objecten B03-076 en B03-007; BOUWPLAN#F6.6.2 jelly-leon-web — beheer; BOUWPLAN#F6.5.4 Endpoints; BOUWPLAN#F6.4.6 Uitzetten, verwijderen en terug naar stock; TEST-JSON rij JLT-56
- **Bouw:**
  1. Plugin-configuratiepagina voor beheerders en editors, op dezelfde manier geregistreerd als de pagina van S-G3-16 (bestaand voorbeeld: `PLUGIN/Configuration/configPage.html`), bruikbaar in Modern en Legacy, zonder web-patch. Vormgeving volgt upstream Jellyfin (buiten Peil). Bron: BOUWPLAN#F6.6.2.
  2. Tabbladen Overzicht, Beoordelen (tijdlijn met trickplay-miniaturen), Families, Publicatie, Kwaliteit, Wezen, Taken en instellingen, Export / import; gevoed door de routes 6 tot en met 16 en 18 tot en met 20. Een editor die geen beheerder is ziet alleen Beoordelen en Families.
  3. Elke toestand zichtbaar: laden, leeg, fout, onbekend, geen rechten, module uit. Achterstand altijd met het woord "schatting".
  4. Publiceren en wezen opruimen altijd eerst als proefrun met `preview_hash`; de pagina toont wat er zou gebeuren en vraagt dan pas bevestiging.
  5. Instelling `OutroEofGuardSeconds` (0 tot 5, standaard 1,0) zichtbaar op het tabblad Taken en instellingen; de marge zelf is in golf 2 gebouwd (B03-073): hier alleen aantonen met een test "marge 0 tegen 1,0 s".
  6. Afronding B03-007, punt voor punt met bewijs aanwijzen: (a) 0 s beschermde scene binnen een overslaanbaar segment op de bevroren testset (JLT-51) na de stappen S-G4-15 en S-G4-40 opnieuw gemeten; (b) geen segment gepubliceerd zonder afgeronde steekproef of menselijke bevestiging, en nergens automatisch overslaan als standaard; (d) module uit geeft hetzelfde gedrag als stock (JLT-56). Punt (c), de clients, volgt in S-G4-23, -27, -28 en -30.
  7. Browsertest in het harnas en EVIDENCE.
- **Tests (verplicht):** Playwright in Chromium, Firefox en WebKit, Modern en Legacy: elk tabblad laadt met een gevulde testdatabase. Negatief: (a) een gewone kijker krijgt 403 op de pagina en de routes; (b) publiceren zonder afgeronde steekproef geeft 409 `qc_sample_incomplete`; (c) opruimen van wezen zonder export van hooguit 24 uur geeft 409 `export_required`; (d) module uit: de pagina zegt dat en doet geen verzoeken in een lus; (e) met marge 0 eindigt het segment op het einde van het bestand, met 1,0 s ervoor. Opnieuw meten van JLT-51: met het commando van S-G2-44 (STAPPEN_P4_GOLF1_2.md; evaluatieharnas van S-P40-66); vaststellen met: `grep -rn "JLT-51" <WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json <WERKMAP>/jelly-leon/tools/b03-harnas/README.md`. Browsertest: toevoegen aan `<WERKMAP>/jelly-leon/tools/b03-harnas/playwright/harnas.mjs` naast de test van S-G3-16; het exacte commando in het README van het harnas. Draaien achter `flock <WERKMAP>/.lokaal/stack.lock`.
- **Poort:** P-jelly-leon (plugin, image bouwen en proeven, job `b03-harnas`) + P-CONTRACT + P-HARDE-EIS.
- **Valkuilen:** V-058, V-060, V-063, V-065, V-067, V-112.
- **Bewijs:** B03-076 -> Bezig (Sim-getest; "webdeel knoppen volgt in S-G4-23"). B03-007 -> Bezig (Sim-getest; per acceptatiepunt het rapportpad; "clients volgen"). JLT-56 -> Bezig. JLT-55 -> Bezig met "serverdeel".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-HARDE-EIS (VERPLICHT: publiceren, wezen opruimen en module uit mogen alleen eigen rijen raken; menselijk werk blijft) -> A-HERSTEL -> R-EERLIJK (geen A-ONTWERP en geen R-ONTWERP: pluginpagina's vallen buiten Peil)
- **Niveau:** standaard; R-HARDE-EIS N4
- **Stop en vraag als:** de hermeting van JLT-51 een schending toont (no-go: niet publiceren; melden); de pagina alleen werkt met een wijziging in jelly-leon-web (dat deel hoort in S-G4-23).

### S-G4-17 - Segmenten: taaktypen voor de planner, MediaGuard alleen lezen en connector voor de Hub
- **Repo:** jelly-leon | **Fase:** P4 (golf 4) | **Omvang:** groot | **Moeilijkheid:** hoog | **Zwaar:** ja (meting in het exclusieve meetslot achter stack.lock)
- **Werkpakketten en tests:** B03-078 (serverdeel); JLT-58 (deel Jelly Leon)
- **Vooraf:** de planner en de analysewerker (B03-018) en de MediaGuard-viewerclient (B03-009) van golf 1. BG-04 (sleutel via de Hub). Subfase F6-S7. Deze stap hangt niet aan S-G4-15 en mag in de baan naar voren.
- **Al gedaan?** `grep -rln "segments.tail_keyframes\|segment_coverage" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = niet gestart.
- **Lees eerst:** WP-JSON object B03-078; BOUWPLAN#F6.10 MediaGuard-integratie; BOUWPLAN#F6.5.6 Connectorcontract; BOUWPLAN#10.5 MediaGuard; TEST-JSON rij JLT-58
- **Bouw:**
  1. Taaktypen `segments.tail_keyframes`, `segments.window_video`, `segments.align` en `segments.classify` aanmelden bij de planner van golf 1, met een kostenschatting per codecklasse (hooguit 2 threads; geheugenklasse 1080p tot 200 MiB, 4K tot 768 MiB) en prioriteit laag. Geen eigen planner, werker of budget. Bron: WP-JSON B03-078.
  2. De planner pauzeert bij elke actieve kijksessie; pauzereden `mg_auth_missing` zolang de dubbele MediaGuard-koppeling (Δ-MG-AUTH) niet klaar is: dan geen batch op de NAS.
  3. MediaGuard alleen via de ene viewerclient van golf 1: rolcontrole op `/api/v1/auth/me` (elke andere rol dan viewer = sleutel niet gebruiken, status `wrong_role`), routelijst en veldenlijst, nooit ruwe antwoorden bewaren of loggen. Gelezen: `/api/v1/status` (noodstop), `/api/v1/app/status` (baanbezetting), `/api/v1/encoding/jobs` (bestanden in encode of verificatie), de eventroutes en `/api/v1/recovery/transactions/{id}`. Nooit `/api/v1/mediaserver/status` en nooit een schrijvende route. Bron: BOUWPLAN#F6.10.
  4. Gedrag: een bestand dat MediaGuard encodeert wordt niet geanalyseerd; bij noodstop geen nieuwe analyse; na `recovery.committed` heruitlijning rond de grenzen; MediaGuard onbereikbaar of 401 -> status `unknown` en de voorzichtige regels.
  5. Connector: `items?type=segment_coverage` (aantallen per bibliotheek) en `items?type=segment_review` (aantallen en ondoorzichtige ID's), health-check `segments` met de redencodes uit BOUWPLAN#F6.5.6, events via de ene outbox. `propose`, `apply` en `rollback` geven 501 `capability_unavailable`.
  6. Achterstandsschatting (dagen, met het woord "schatting") voor de beheerpagina en de Hub-kaart.
  7. Meting volgens JLT-58 en EVIDENCE.
- **Tests (verplicht):** contracttest: 0 aangeroepen MediaGuard-mutatieroutes. Meting in het meetslot, minstens 3 runs, loadavg in het bewijs: taken binnen het budget; gelezen bytes per item en CPU-seconden per mediaseconde per codecklasse; pauze binnen 5 s na de start van een kijksessie; uitlijning van een synthetisch seizoen van 200 afleveringen met gemeten bovengrens. Negatief: (a) sleutel met rol operator -> niet gebruikt, status `wrong_role`; (b) MediaGuard 401 of onbereikbaar -> `unknown`, geen crash; (c) noodstop -> geen nieuwe analyse; (d) bestand in encode -> overgeslagen; (e) zonder pin 401 `not_linked`; (f) een event met een titel of pad wordt door de schematest geweigerd. Commando's: T-JL-PLUGIN met `--filter "FullyQualifiedName~Segment"`; de MediaGuard-simulator: zie "Niet vastgesteld" in hoofdstuk 4; het meetcommando is ONBEKEND - eerst vaststellen met: `grep -n "meetslot\|stack.lock" <WERKMAP>/jelly-leon/tools/b03-harnas/README.md`. Meting achter `flock <WERKMAP>/.lokaal/stack.lock`.
- **Poort:** P-jelly-leon (plugin, volledig) + P-CONTRACT + P-VEILIG + P-HARDE-EIS.
- **Valkuilen:** V-014, V-043, V-046, V-051, V-054, V-099, V-105.
- **Bewijs:** B03-078 -> Bezig (Sim-getest; opmerking "Intel-iGPU-getest op de ontwikkelmachine"; "Hub-kaart volgt in S-G4-38"). JLT-58 -> Bezig met "deel Jelly Leon; cijfers zijn een bovengrens". "A310 en UHD 770: NIET GEVALIDEERD (hardware); D08 open." JLT-59 -> Geblokkeerd.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-VEILIG (VERPLICHT: MediaGuard-sleutel, rolcontrole, wat de Hub te zien krijgt) -> R-HARDE-EIS (VERPLICHT: geen enkele schrijvende aanroep naar MediaGuard; voortgang van MediaGuard blijft ongemoeid) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4; R-HARDE-EIS N4; overig standaard
- **Stop en vraag als:** `git -C <WERKMAP>/jelly-leon ls-files` voor `PLUGIN/Core/Planner`, `PLUGIN/Core/Werker` of `PLUGIN/Core/MediaGuard` niets geeft (golf 1 niet klaar); de viewerclient op een MediaGuard-sleutel in Jelly Leon zelf bouwt (zie "Spanning BG-04"); een gevraagd gegeven alleen via `/api/v1/mediaserver/status` te krijgen is.

### S-G4-18 - Apparaten: connector-items voor de Hub en het clientrapport alleen lezen
- **Repo:** jelly-leon | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** B03-069 (serverdeel); JLT-48 (deel Hub-negatieven)
- **Vooraf:** S-G4-06 (geleerde profielen) en S-G4-03 (lanes voor `gpu_lane`). De Hub-pin JL4 bestaat.
- **Al gedaan?** `grep -rln "playback_stats\|gpu_lane" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = niet gestart.
- **Lees eerst:** WP-JSON object B03-069; BOUWPLAN#F5.5.5 Connectorcontract (§6), bijdrage van F5; BOUWPLAN#F5.5.2 Endpoints; BOUWPLAN#F5.9.7 Gegevensbescherming; `PLUGIN/Core/Connector/ConnectorService.cs`
- **Bouw:**
  1. Connector-itemtypen `device`, `playback_stats` en `gpu_lane` op `/connector/v1/items`: per apparaatklasse en rol, met ondoorzichtige ID's; geen apparaatnaam, gebruikersnaam of titel. Bron: WP-JSON B03-069.
  2. Geen uitsplitsing per apparaat met een tijdvenster voor de Hub: `group_by=device` geeft de Hub 403.
  3. Stock Android TV: het rapport dat de app via de bestaande knop naar de server stuurt (`POST /ClientLog/Document`) leest de module alleen-lezend, binnen het opruimvenster van de logmap (`LogFileRetentionDays`). De module schrijft of wist daar niets.
  4. Health-check `clientlog.reports`: `unavailable` als `AllowClientLogUpload=false` of als het rapport is opgeruimd; de apparaatpagina toont dan "rapport niet beschikbaar".
  5. `propose`, `apply` en `rollback` geven 501; OpenAPI, tests en EVIDENCE.
- **Tests (verplicht):** schematest op de drie itemtypen (alleen aantallen, klassen en ondoorzichtige ID's). Negatief: (a) zonder pin 401 `not_linked`; (b) rol kind 403; (c) `group_by=device` 403; (d) met `AllowClientLogUpload=false` is de health-check `unavailable` en nooit gezond; (e) een rapport buiten het opruimvenster wordt niet gelezen en geeft geen fout; (f) de logmap is na de test byte-gelijk. Commando: T-JL-PLUGIN met `--filter "FullyQualifiedName~Devices"`, daarna volledig.
- **Poort:** P-jelly-leon (plugin, volledig) + P-CONTRACT + P-VEILIG.
- **Valkuilen:** V-046, V-051, V-054, V-105.
- **Bewijs:** B03-069 -> Bezig (Unit-getest; "clientpatches volgen in S-G4-25 en S-G4-26; Hub-kaarten in S-G4-37"). JLT-48 -> Bezig met "deel Hub". "Swiftfin: alleen waarneming aan de serverkant; NIET GEVALIDEERD (Mac/Xcode)."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-VEILIG (VERPLICHT: wat de Hub over apparaten te zien krijgt; geen spoor per apparaat in de tijd) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard; R-VEILIG N4
- **Stop en vraag als:** de Hub-kaart meer nodig lijkt te hebben dan klassen en aantallen (niet toevoegen; melden); het rapport alleen te lezen is door een upstream-bestand te wijzigen.

### S-G4-19 - Contractcontrole: eventnamen, foutcatalogus, verzoekgrootte en Hub-pin
- **Repo:** jelly-leon | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** contractpunten C1.3-JL-06, C1.3-JL-07 en C1.3-JL-08 (bron: `<WERKMAP>/jelly-leon/docs/platform-v2/CONTRACT_1.3_CONFORMITEIT.md`, kop "9. jelly-leon (server-fork)"); JLT-64 (deel: alleen additief)
- **Vooraf:** S-G4-11, S-G4-13, S-G4-14, S-G4-17 en S-G4-18 (alle connectorbijdragen van de modules staan er).
- **Al gedaan?** `grep -n "C1.3-JL-06\|C1.3-JL-07\|C1.3-JL-08" <WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json` -> geen uitvoer = nog geen bewijsregel. `ls <WERKMAP>/jelly-leon/docs/adr` -> zoek een ADR over eventnamen; ontbreekt die, dan is punt 3 hieronder niet gedaan.
- **Lees eerst:** `<WERKMAP>/jelly-leon/docs/platform-v2/CONTRACT_1.3_CONFORMITEIT.md` (de drie rijen); `<WERKMAP>/jelly-leon/docs/platform-v2/PLATFORM_CONTRACTEN.md` (§4, §5, §6 en §7); BOUWPLAN#10.4 Hub-koppeling (JL4); `PLUGIN/Core/Errors`; `PLUGIN/Core/Hub`
- **Bouw:**
  1. C1.3-JL-06: loop de Hub-koppeling na tegen het contract: pin met vingerafdruk over alle policy-sleutels plus de meegekopieerde `service_id`; `aud` als tekst; persistente `jti`; rol kind wint; zonder pin 401 `not_linked`; events alleen via poll; alleen aantallen en ondoorzichtige ID's; `propose`, `apply` en `rollback` 501. Wat ontbreekt: bouwen met test.
  2. C1.3-JL-07, deel grootte en fouten: elke route van `/media/v1` en `/connector/v1` heeft de grens van 1 MiB (of de eigen, kleinere of in een ADR vastgelegde grotere grens) en gebruikt de foutcatalogus, inclusief 423 `item_in_playback`.
  3. C1.3-JL-07, deel events: zet alle eventnamen van de modules in een tabel naast de werkwoorden van contract §7 en beslis per naam: hernoemen of bewust zo laten. Leg dat vast in een ADR in `<WERKMAP>/jelly-leon/docs/adr` (nummer pas kiezen na `git pull --rebase`). Een hernoeming is een contractwijziging voor de Hub: meld de lijst aan de regisseur voor de Hub-baan.
  4. C1.3-JL-08: de MediaGuard-viewerclient heeft rolcontrole, routelijst en veldenlijst en bewaart geen ruwe antwoorden; acties bestaan alleen als deeplink `handmatig_in_mediaguard`.
  5. Een test die alle geregistreerde routes en eventnamen opsomt en tegen de regels houdt, zodat een latere module niet ongemerkt afwijkt; EVIDENCE.
- **Tests (verplicht):** de opsommende test uit punt 5. Negatief: (a) een verzoek groter dan de grens geeft 413 en wordt niet verwerkt; (b) een eventnaam die niet in de tabel van de ADR staat laat de test falen; (c) een dienst-JWT met een verkeerde `service_id` wordt geweigerd; (d) een hergebruikte `jti` wordt geweigerd, ook na een herstart. Commando: T-JL-PLUGIN volledig; `python -m pytest -q tools/jelly-leon/tests` voor de drifttest van het contract.
- **Poort:** P-jelly-leon (plugin, volledig) + P-CONTRACT + P-VEILIG.
- **Valkuilen:** V-001, V-046, V-047, V-054, V-092, V-094.
- **Bewijs:** per contractpunt een regel in EVIDENCE -> Bezig (Unit-getest) met het testrapport; "tegen de echte Hub: NIET GEVALIDEERD tot S-G4-31 de koppeling legt".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-VEILIG (VERPLICHT: controle van dienst-JWT's, pin, `jti`) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard; R-VEILIG N4 (er wordt nagelopen en aangevuld; wordt de kern van de JWT-controle herschreven, dan stopt de stap en zet de regisseur een aparte stap uit met R-VEILIG op N5. Winst: een fout in die controle laat een vreemde dienst als de Hub optreden)
- **Stop en vraag als:** een eventnaam hernoemd moet worden terwijl de Hub hem al gebruikt (eerst afstemmen); de kern van de JWT-controle herschreven moet worden.

### S-G4-42 - Pluginpagina "Apparaten" voor beheerders (regels beslissen, correctie per apparaat)
Dit nummer is later toegevoegd; in de volgorde hoort de stap na S-G4-18 (zie de tabel in 6.2).
- **Repo:** jelly-leon | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (image en browsertest achter stack.lock)
- **Werkpakketten en tests:** B03-066 (deel beheer: regels beslissen); B03-068 (deel beheer: profieladvies en serverzijdige correctie per apparaat); JLT-42 (deel beheer); JLT-46 (deel: correctie staat standaard uit)
- **Vooraf:** S-G4-07 en S-G4-18. BG-26 (wie een verruimende regel mag bevestigen): zonder besluit alleen de beheerder.
- **Al gedaan?** `grep -rln "IHasWebPages" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> lees welke pagina's al geregistreerd zijn. `grep -rli "apparaten" <WERKMAP>/jelly-leon/plugins/JellyLeon/src --include=*.html --include=*.js` -> geen uitvoer = pagina nog niet gebouwd. `grep -rn "rules/{ruleId}/decision" <WERKMAP>/jelly-leon/plugins/JellyLeon/src -l` -> geen uitvoer = de routes van S-G4-06 ontbreken: STOP.
- **Lees eerst:** BOUWPLAN#F5.6.1 jelly-leon-web (upstream-stijl) (rij W6); BOUWPLAN#F5.5.2 Endpoints (E9 tot en met E12); WP-JSON objecten B03-066 en B03-068; `PLUGIN/Modules/Devices/DevicesController.cs`; BOUWPLAN#F5.9.7 Gegevensbescherming
- **Bouw:**
  1. Plugin-configuratiepagina "Apparaten", alleen voor beheerders, geregistreerd zoals de pagina van S-G3-16 (voorbeeld: `PLUGIN/Configuration/configPage.html`), bruikbaar in Modern en Legacy, zonder web-patch. Bron: BOUWPLAN#F5.6.1 (W6).
  2. Apparatenlijst uit E9 en detail uit E10: rol, apparaatklasse, gemeten mogelijkheden, uitkomsten en regels met hun staat.
  3. Regels beslissen via E11 (`confirm`, `reject`, `revoke`), elk met een bevestigingsvraag die zegt wat er verandert.
  4. Per apparaat de schakelaars "Profieladvies" en "Serverzijdige correctie" via E12; na installatie staan beide uit; bij een officiele app staat erbij dat de app zelf niet wordt gewijzigd.
  5. DV-bevestigingen van MediaGuard naast die van Jelly Leon: alleen gelezen via de viewerclient, met de markering "verschilt" en een deeplink naar MediaGuard. MediaGuard niet bereikbaar: "MediaGuard: onbekend", nooit "gelijk".
  6. Het clientrapport van S-G4-18: is de health-check `clientlog.reports` niet beschikbaar, dan toont de pagina "rapport niet beschikbaar".
  7. Elke toestand zichtbaar: laden, leeg, fout, onbekend, geen rechten, module uit.
  8. Browsertest in het harnas en EVIDENCE.
- **Tests (verplicht):** Playwright in Chromium, Firefox en WebKit, Modern en Legacy: lijst, detail en elke beslissing met een gevulde testdatabase. Negatief: (a) een gewone gebruiker krijgt 403 op de pagina en op E9 tot en met E12; (b) elke weigering die BOUWPLAN#F5.5.2 bij E11 en E12 noemt heeft een eigen test; (c) MediaGuard onbereikbaar geeft "onbekend" en geen fout op de rest van de pagina; (d) de pagina doet geen enkel schrijvend verzoek naar MediaGuard (teller in de testdubbel is 0); (e) module uit: de pagina zegt dat en vraagt niet in een lus op. Browsertest: toevoegen aan `<WERKMAP>/jelly-leon/tools/b03-harnas/playwright/harnas.mjs` naast de test van S-G3-16; het exacte commando in het README van het harnas bijwerken. Daarnaast T-JL-PLUGIN met `--filter "FullyQualifiedName~Devices"`, T-JL-IMAGE.
- **Poort:** P-jelly-leon (plugin, image bouwen en proeven, job `b03-harnas`) + P-CONTRACT + P-VEILIG.
- **Valkuilen:** V-058, V-060, V-063, V-065, V-067. Eigen: het harnasonderdeel `legacy` is de proef met een derden-client, niet de weergave Legacy.
- **Bewijs:** B03-066 en B03-068 -> Bezig (Sim-getest; "beheerpagina; webscherm Dit apparaat volgt in S-G4-41"). JLT-42 en JLT-46 -> Bezig met "deel beheer".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-VEILIG (VERPLICHT: wie een regel mag bevestigen en wie de correctie mag aanzetten) -> A-HERSTEL -> R-EERLIJK (geen A-ONTWERP en geen R-ONTWERP: pluginpagina's vallen buiten Peil)
- **Niveau:** standaard; R-VEILIG N4
- **Stop en vraag als:** de pagina alleen werkt met een wijziging in jelly-leon-web; een beslissing een schrijvende aanroep naar MediaGuard zou vragen (niet bouwen; melden).

### S-G4-44 - Pluginpagina "Watch Together" voor beheerders afmaken
Dit nummer is later toegevoegd; in de volgorde hoort de stap na S-G4-11 (zie de tabel in 6.2).
- **Repo:** jelly-leon | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (image en browsertest achter stack.lock)
- **Werkpakketten en tests:** B03-029 (afronding: beheerpagina); B03-022 en B03-023 (zichtbaar maken van de rechtencontrole en de kinderregels); JLT-05 (deel beheer); JLT-09 (deel: de pagina wijzigt geen UserPolicy)
- **Vooraf:** S-G4-11. De pagina zelf is in golf 2 begonnen (WP-JSON B03-021 noemt de rode melding op deze pagina). Het tabblad "Externe deelnemers" toont alleen instellingen als BG-09 "aan" is; het tabblad "Chat en reacties" alleen als BG-12 "aan" is en S-G4-10 klaar is.
- **Al gedaan?** `grep -rli "watch together" <WERKMAP>/jelly-leon/plugins/JellyLeon/src --include=*.html --include=*.js` -> geen uitvoer = de pagina van golf 2 ontbreekt: deze stap bouwt haar dan helemaal en de omvang wordt "groot" (melden aan de regisseur). `grep -rn "admin/overview\|admin/purge\|admin/rights-check" <WERKMAP>/jelly-leon/plugins/JellyLeon/src -l` -> lees welke beheerroutes er al zijn.
- **Lees eerst:** BOUWPLAN#F1.6.1 Jelly Leon-webclient (rij W9); BOUWPLAN#F1.5.2 Endpoints (E16, E17, E18); BOUWPLAN#F1.7 Configuratieopties; WP-JSON object B03-021 (wat de pagina al moest tonen); BOUWPLAN#F1.9.6 Gegevensbescherming
- **Bouw:**
  1. De tabbladen van de pagina compleet maken in de volgorde van het bouwplan: Algemeen, Privacy en uitnodigingen, Kinderprofielen, Synchronisatie, Externe deelnemers, Chat en reacties, Rechtencontrole, Overzicht, Gegevens. Bron: BOUWPLAN#F1.6.1 (W9).
  2. Elke instelling op de pagina komt uit BOUWPLAN#F1.7; geen instelling bedenken die daar niet staat.
  3. Rechtencontrole toont de uitkomst van E16 in gewone taal, met de rode melding als de decorator niet actief is terwijl gasten of kinderen zijn ingesteld (advies `SyncPlayAccess=None`).
  4. Overzicht toont E17 (alleen aantallen en toestanden). Ontbreekt E17 in de plugin: de route bouwen volgens BOUWPLAN#F1.5.2, met test.
  5. Gegevens: opruimen via E18 met een bevestigingsvraag; de pagina zegt erbij dat een verwijderde gebruiker in oudere back-ups nog kan voorkomen. E18 raakt uitsluitend de eigen tabellen van de module.
  6. Een tabblad waarvan het besluit ontbreekt toont "uit (wacht op besluit BG-09)" of "uit (wacht op besluit BG-12)" en geen instellingen.
  7. Elke toestand zichtbaar: laden, leeg, fout, onbekend, geen rechten, module uit.
  8. Browsertest in het harnas en EVIDENCE.
- **Tests (verplicht):** Playwright in Chromium, Firefox en WebKit, Modern en Legacy: elk tabblad laadt. Negatief: (a) een gewone gebruiker krijgt 403 op de pagina en op E16, E17 en E18; (b) met een geforceerd inactieve decorator en een ingesteld kind staat de rode melding er en is niets groen; (c) E18 zonder bevestiging doet niets; (d) na E18 is de bibliotheekdatabase van Jellyfin byte-gelijk voor kijkgegevens en gebruikers (vergelijk met de differentiele run van S-G4-39) en staat er geen gebruikers-GUID meer in de eigen tabellen; (e) opslaan op de pagina wijzigt geen UserPolicy. Browsertest: toevoegen aan `<WERKMAP>/jelly-leon/tools/b03-harnas/playwright/harnas.mjs`. Daarnaast T-JL-PLUGIN met `--filter "FullyQualifiedName~Watch"`, T-JL-IMAGE.
- **Poort:** P-jelly-leon (plugin, image bouwen en proeven, job `b03-harnas`) + P-CONTRACT + P-VEILIG + P-HARDE-EIS.
- **Valkuilen:** V-046, V-055, V-058, V-060, V-063, V-065, V-067.
- **Bewijs:** B03-029 -> Bezig (Sim-getest; "beheerpagina; Hub-kaart volgt in S-G4-33"). JLT-05 -> Bezig met "deel beheer". Tabbladen zonder besluit: "Geblokkeerd (besluit BG-09)" of "Geblokkeerd (besluit BG-12)" in de bewijsregel.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-VEILIG (VERPLICHT: beheerroutes en opruimen) -> R-HARDE-EIS (VERPLICHT: opruimen raakt alleen eigen tabellen; gebruikers en kijkgegevens blijven) -> A-HERSTEL -> R-EERLIJK (geen A-ONTWERP en geen R-ONTWERP: pluginpagina's vallen buiten Peil)
- **Niveau:** standaard; R-VEILIG N4; R-HARDE-EIS N4
- **Stop en vraag als:** een tabblad een instelling vraagt die niet in BOUWPLAN#F1.7 staat; E18 meer zou wissen dan de eigen tabellen van de module.

### S-G4-49 - Scènezoeker: zoeken in ondertitelcues met tijdcode en rechten per gebruiker (B03-008, serverdeel)
- **Repo:** jelly-leon | **Fase:** P4 (golf 4) | **Omvang:** groot | **Moeilijkheid:** hoog | **Zwaar:** nee (plugin-build en -test achter docker-build.lock; ONBEKEND of de indexbouw een werkertaak in de image vraagt - A-VERKEN stelt vast; dan image-build achter docker-build.lock)
- **Werkpakketten en tests:** B03-008 (serverdeel)
- **Vooraf:** S-G3-22 (cues en families; WP-JSON B03-074: cue-extractie "gedeeld met B03-008"); de cue-extractie van de bestandspas S-G1-34 (STAPPEN_P4_GOLF1_2.md); S-G3-06 (de ene syncmeter B03-042; BOUWPLAN noemt B03-008 als afnemer); S-G3-10 (rechten op streamroutes, B03-010: een kinderaccount krijgt geen volwassen media "via zoeken"). Besluit Z-20 genomen. BG-06 (P5): zonder besluit geen tweede producent, dus in P4 geen spraakherkenning en geen embeddings.
- **Al gedaan?** `grep -c '"id": "B03-008"' <WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json` -> 0 = niet gestart (op 2026-11-11: 0). `grep -rln "media/v1/scenes\|media/v1/search" <WERKMAP>/jelly-leon/plugins/JellyLeon/src` -> geen uitvoer = routes nog niet gebouwd.
- **Lees eerst:** TASKS-JSON object B03-008; BOUWPLAN#B03-008 — Semantische scènezoeker; BOUWPLAN#3. API en integratie-contracten (blok "Aanvulling 2.0 — API": "`GET /media/v1/search` en `GET /media/v1/scenes` blijven B03-008"); in BOUWPLAN de tabelrij "F4/F6/B03-008 spraak (P5)" (zoek op "faster-whisper"); WP-JSON objecten B03-042 en B03-074; `<WERKMAP>/.lokaal/plan/uit/BESLUITEN_EN_BLOKKADES.md`, kop "BG-06"; E2E-JSON rij EX36; de ADR van S-G3-10 over streamroutes
- **Bouw:**
  1. Scope (A-VERKEN, afspraak "Stappen uit besluit Z-20" in hoofdstuk 8): per onderdeel van de bron (zoeken op omschrijving of op uitgesproken dialoog; scènedetectie; ondertitelsync; vectorindex met rechten per gebruiker; batch alleen bij rust) wat zonder spraakherkenning en zonder embeddings haalbaar is. Zoeken op omschrijving en een vectorindex vragen embeddings (BG-06, P5) en horen niet in deze stap. Scènedetectie (beeld): ONBEKEND - A-VERKEN stelt vast of de bestandspas (S-G1-34) of kwaliteitscontrole niveau 2 (S-G3-12) al scènegrenzen levert; zo niet, dan niet bouwen en onder besluit_nodig zetten.
  2. Een index van de tekst van bestaande ondertitelsporen met tijdcode per item (cues uit de bestandspas, stabiele spoorsleutel), in eigen opslag van de plugin; bouwen via de planner van golf 1 en alleen bij rust (B03-018); de module start zelf nooit een tool.
  3. Routes `GET /media/v1/search` en `GET /media/v1/scenes`, additief in de OpenAPI; schema volgens de afspraak in hoofdstuk 8 (BOUWPLAN noemt alleen de paden). Module uit: 404 (besluit Z-19).
  4. Rechten: een resultaat alleen voor items die de gebruiker mag zien (bibliotheekrechten, ouderlijk toezicht, kind volgens de ene definitie van B03-010); een verborgen item geeft hetzelfde antwoord als een niet-bestaand item.
  5. Zonder tekstspoor of zonder recht: geen resultaat en geen verzonnen tekst. Bron: TASKS-JSON B03-008 (Acceptatie).
  6. Tests en EVIDENCE.
- **Tests (verplicht):** xUnit: een zin uit een ondertitelspoor van het corpus geeft het item met de tijdcode van die cue. Negatief (acceptatie TASKS-JSON B03-008: "Zonder transcript of permissie geen hallucinaties of lek van verborgen media"): (a) een item zonder ondertitelspoor geeft geen resultaat; (b) een kind of een gebruiker zonder bibliotheekrecht ziet het item niet, ook niet via `/scenes` of via aantallen (EX36); (c) een zoekterm die alleen in een verborgen item staat geeft hetzelfde antwoord als een zoekterm zonder treffer; (d) module uit -> 404; (e) een PlaybackStart pauzeert de indexbouw (planner). Commando: T-JL-PLUGIN met het filter van de module, daarna volledig.
- **Poort:** P-jelly-leon (plugin, volledig) + P-CONTRACT + P-VEILIG.
- **Valkuilen:** V-003, V-005, V-066, V-099.
- **Bewijs:** B03-008 -> Bezig (Unit-getest) met de opmerking "alleen tekst uit bestaande ondertitelsporen; zoeken op omschrijving en spraak wachten op BG-06 (P5)". "NIET GEVALIDEERD (echte NAS): echte bibliotheek; zie STAPPEN_P6.md, N-P6-09."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG (tegelijk; R-VEILIG VERPLICHT: rechten per gebruiker en geen lek van verborgen media) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4; overige standaard
- **Stop en vraag als:** de cue-extractie van S-G1-34 geen tekst met tijdcode levert; de stap spraakherkenning of embeddings zou vragen (BG-06); scènedetectie nodig blijkt waar geen bouwsteen voor is.

### S-G4-51 - Offline downloaden: downloadrechten, verlopen en uitgezet account (B03-011, serverdeel)
- **Repo:** jelly-leon | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee (plugin-build en -test achter docker-build.lock)
- **Werkpakketten en tests:** B03-011 (serverdeel)
- **Vooraf:** S-G3-10 (authenticatiefilter op streamroutes; B03-010 Acceptatie: een kinderaccount krijgt geen volwassen media "via ... download API"). Besluit Z-20 genomen.
- **Al gedaan?** `grep -c '"id": "B03-011"' <WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json` -> 0 = niet gestart (op 2026-11-11: 0).
- **Lees eerst:** TASKS-JSON object B03-011; BOUWPLAN#B03-011 — Offline downloaden; BOUWPLAN#B03-010 — Accounts en parental control (Acceptatie); E2E-JSON rij EX35 (het eindscenario zelf is S-P6-13 in STAPPEN_P6.md); de ADR van S-G3-10 over streamroutes
- **Bouw:**
  1. Scope (A-VERKEN): welke upstream-routes en welk gebruikersbeleid het downloaden regelen en wat ze al afdwingen. ONBEKEND - A-VERKEN stelt vast met `grep -rln "Download" <WERKMAP>/jelly-leon/Jellyfin.Api/Controllers --include=*.cs` en de upstream-tests. Wat ontbreekt voor de bron: een uitgezet account start geen nieuwe download; verlopen rechten; een kind krijgt geen volwassen media via de download-API. Versleutelde opslag, opslagquota en het downloadoverzicht zitten in de client (S-G4-52).
  2. Alleen wat ontbreekt, in de plugin. Kan het alleen met een wijziging in upstream-code: niet bouwen, melden (een corepatch hoort in het patchregister).
  3. Tests en EVIDENCE.
- **Tests (verplicht):** xUnit en, als het dossier dat nodig vindt, een proef tegen een container met de server. Negatief: (a) een uitgezet account start geen nieuwe download; (b) een kind kan een item boven zijn grens niet downloaden en krijgt hetzelfde antwoord als bij een niet-bestaand item; (c) een ingetrokken token geeft geen download; (d) een stock-client die mag downloaden kan dat nog (zelfde antwoord als stock 12.x). Commando: T-JL-PLUGIN.
- **Poort:** P-jelly-leon (plugin, volledig) + P-VEILIG.
- **Valkuilen:** V-003, V-005.
- **Bewijs:** B03-011 (jelly-leon) -> Bezig (Unit-getest of Sim-getest). "NIET GEVALIDEERD (hardware): echte telefoons; zie STAPPEN_P6.md, N-P6-09."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG (tegelijk; R-VEILIG VERPLICHT: tokens en rechten) -> A-HERSTEL -> R-EERLIJK. R-HARDE-EIS erbij (VERPLICHT) als de bouw gebruikersbeleid of gebruikers schrijft of wijzigt.
- **Niveau:** standaard; R-VEILIG N4; R-HARDE-EIS N4 als hij loopt
- **Stop en vraag als:** afdwingen alleen kan met een wijziging in upstream-code of in het beleid van bestaande gebruikers; een stock-client anders zou beslissen dan met de plugin uit.

### S-G4-53 - Live-tv en DVR: overlapmelding, opnamestatus, bewaartermijn en gids (B03-012, serverdeel)
- **Repo:** jelly-leon | **Fase:** P4 (golf 4) | **Omvang:** groot | **Moeilijkheid:** hoog | **Zwaar:** ja (proef met een server en een nagebootste tuner in een container achter stack.lock; ONBEKEND welke tuner na te bootsen is - A-VERKEN stelt vast)
- **Werkpakketten en tests:** B03-012 (serverdeel)
- **Vooraf:** S-G4-04 (gedeeld GPU-budget: opnames die transcoderen lopen over dezelfde lanes; TASKS-JSON B03-012 noemt "GPU capability tests" als afhankelijkheid). Besluit Z-20 genomen.
- **Al gedaan?** `grep -c '"id": "B03-012"' <WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json` -> 0 = niet gestart (op 2026-11-11: 0). `git -C <WERKMAP>/jelly-leon ls-files src/Jellyfin.LiveTv | wc -l` -> upstream-live-tv is aanwezig (op 2026-11-11 onder meer `TunerHosts/HdHomerun/`, `Listings/SchedulesDirect.cs`, `IO/EncodedRecorder.cs`).
- **Lees eerst:** TASKS-JSON object B03-012; BOUWPLAN#B03-012 — Live-tv en DVR; E2E-JSON rij EX38 (het eindscenario zelf is S-P6-17 in STAPPEN_P6.md); hoofdstuk 2 van dit bestand (no-go "media muteren buiten MediaGuard"); stap S-G3-01 bouwpunt 3 (media alleen-lezen gekoppeld)
- **Bouw:**
  1. Scope (A-VERKEN): wat upstream `src/Jellyfin.LiveTv` al doet (tuners, gids, opnameplanner) tegen de bron (EPG, tuner, opnameplanner, overlapdetectie, opslagquota, opnamestatus, bewaartermijn, gidssync, veilig hervatten na herstart). Welke tuner op de ontwikkelmachine na te bootsen is zonder echte tuner of gidsprovider met account: ONBEKEND - A-VERKEN stelt vast met `git -C <WERKMAP>/jelly-leon ls-files src/Jellyfin.LiveTv/TunerHosts src/Jellyfin.LiveTv/Listings`. Waar opnames worden weggeschreven: nooit in een mediamap van de bibliotheek (die is alleen-lezen gekoppeld).
  2. Overlap vooraf herkennen en de beperking melden ("Overlappende opname meldt beperkingen"; EX38 "Conflict wordt vooraf getoond"). Bron: TASKS-JSON B03-012.
  3. Status per opname; na een herstart hervat de planner veilig (geen dubbele en geen verloren opname). Bron: TASKS-JSON B03-012 (Acceptatie).
  4. Bewaartermijn en opslagquota voor een opnamemap die geen mediamap is.
  5. Routes additief in de OpenAPI (afspraak in hoofdstuk 8). Module uit: 404 (besluit Z-19); upstream-live-tv blijft dan werken zoals stock.
  6. Tests en EVIDENCE.
- **Tests (verplicht):** acceptatie met de nagebootste tuner: twee overlappende opnames op één tuner -> melding vooraf; een herstart van de server tijdens een geplande opname -> de planner hervat zonder dubbele of verloren opname. Negatief: (a) een opnamepad in een alleen-lezen mediamap -> geweigerd met een code uit de foutcatalogus, niets geschreven; (b) quota vol -> geen nieuwe opname en een melding; (c) een niet-beheerder krijgt 403 op beheerroutes; (d) met de module uit is het gedrag gelijk aan stock 12.x. Commando's: T-JL-PLUGIN; de containerproef achter `flock <WERKMAP>/.lokaal/stack.lock nice -n 10` (commando legt A-BOUW vast in het rapport).
- **Poort:** P-jelly-leon (plugin, volledig; image als het dossier een containerproef nodig vindt) + P-VEILIG; P-INSTALLATIE als het installatiemanifest wijzigt.
- **Valkuilen:** V-003, V-005, V-099. Eigen: een nagebootste tuner bewijst geen echte ontvangst.
- **Bewijs:** B03-012 -> Bezig (Sim-getest). "NIET GEVALIDEERD (hardware): echte tuner en antenne of kabel; NIET GEVALIDEERD (account): gidsprovider met account als de gebruiker die wil; zie STAPPEN_P6.md, N-P6-09." EX38 blijft bij S-P6-17.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG (tegelijk; R-VEILIG VERPLICHT: tuners in het netwerk, ontdekking en verbinding, en gidsbronnen) -> A-HERSTEL -> R-EERLIJK. R-MANIFEST erbij (VERPLICHT) als er iets aan de image of het installatiemanifest wijzigt (bijvoorbeeld een opnamemap).
- **Niveau:** A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4; overige standaard
- **Stop en vraag als:** opnames in een mediamap zouden komen (no-go); het installatieformulier geen schrijfbare opnamemap heeft en er een nodig is (wijziging aan de Custom App: eerst de gebruiker via een keuzemenu); geen tuner na te bootsen is (dan alleen unit-tests, de rest "Geblokkeerd", en melden).

### S-G4-20 - Rij "Aanbevolen voor jou" op het startscherm (haak en rij)
- **Repo:** jelly-leon-web | **Fase:** P4 (golf 4) | **Omvang:** groot | **Moeilijkheid:** hoog | **Zwaar:** ja (npm-build; e2e achter stack.lock)
- **Werkpakketten en tests:** B03-036 (deel rij en kaartmenu); JLT-14 (deel web, Chromium)
- **Vooraf:** B03-035 (routes van de module Recommendations, golf 2); de webhaakmodule van B03-017 (golf 1); S-G3-30 en S-G3-31 (of de reden dat S-G3-31 verviel): WP-JSON B03-036 noemt B03-002 (startscherm) als afhankelijkheid. BG-15 (plaats van de rij en gedrag op officiele apps): zonder besluit start deze stap niet.
- **Al gedaan?** `ls <WERKMAP>/jelly-leon-web/src/jelly-leon` -> bestaat niet = de haakmodule van golf 1 ontbreekt: STOP. `ls <WERKMAP>/jelly-leon-web/src/jelly-leon/recommendations` -> bestaat niet = niet gestart. `grep -n "home.sections" <WERKMAP>/jelly-leon-web/src/components/homesections/homesections.js` -> geen uitvoer = haak nog niet geplaatst.
- **Lees eerst:** WP-JSON object B03-036; BOUWPLAN#F2.6.1 jelly-leon-web; BOUWPLAN#F2.5.3 Routes voor gebruikers; `<WERKMAP>/jelly-leon-web/docs/platform-v2/PATCHES.md` (kop "Geplande haken op de 12.x-basis", rij H-HOME); BOUWPLAN#F2.9.5 Clientmatrix
- **Bouw:**
  1. Haak H-HOME: een import en een aanroep `jlHook('home.sections', ctx)` in `src/components/homesections/homesections.js`, in `export function loadSections`, met foutgrens. Dit bestand is gedeeld door Modern en Legacy. Registreren als haak met het eerstvolgende vrije JLW-nummer in PATCHES.md. Bron: PATCHES.md, rij H-HOME.
  2. Fork-code in `src/jelly-leon/recommendations`: de rij "Aanbevolen voor jou" en hooguit twee extra rijen ("Omdat je X keek", "Anime voor jou"), gevoed door `GET /media/v1/recommendations/home`. Plaats volgens de instelling `home_row_position` (BG-15).
  3. Kaartmenu met "Waarom aanbevolen?", "Niet interessant", "Meer zoals dit", "Minder zoals dit" en "Niets meer uit deze serie/collectie" via `POST /media/v1/recommendations/feedback`; ongedaan maken via `DELETE .../feedback/{feedbackId}`.
  4. Tv-weergave: dezelfde rij bedienbaar met de pijltjestoetsen als `layoutManager.tv` waar is.
  5. Toestanden uit de tabel van BOUWPLAN#F2.6.1, elk met de daar genoemde tekst: laden met time-out van 3 s; leeg bij een koude start (kaart "Vertel ons wat je leuk vindt"); leeg gefilterd; `not_computed` ("Aanbevelingen worden voorbereid."); gepauzeerd met de knop "Hervatten"; uitgeschakeld (geen rij); fout 503 of time-out (rij weg met de regel "Aanbevelingen zijn nu niet beschikbaar."); 404 of 501 (rij weg zonder regel); 401 (geen rij).
  6. Knop "Aanbevelingen aanpassen" in de rijkop; hij opent de dialoog van S-G4-45 (tot die stap klaar is: knop verborgen).
  7. Teksten in een eigen stringbestand; geen wijziging in `src/strings`.
  8. Unit-tests, uitbreiding van de e2e-rooktest en EVIDENCE.
- **Tests (verplicht):** unit (in T-JLW-NPM): elke toestand uit punt 5. Negatief: (a) 503, 404, 501 en time-out: alleen de eigen rij verdwijnt, de overige secties van het startscherm blijven; (b) module uit of een stock-server: de DOM van de startschermsecties is gelijk aan stock; (c) een geforceerde fout in de fork-code laat het upstream-startscherm werken (foutgrens); (d) "Niet interessant" haalt de kaart binnen 2 s weg en is ongedaan te maken; (e) er wordt niets in persistente browseropslag geschreven. Commando's: T-JLW-STATISCH, T-JLW-NPM, T-JLW-E2E. Firefox, WebKit, UA-simulatie en stock-web lopen in S-G4-39.
- **Poort:** P-jelly-leon-web (volledig) + P-CONTRACT.
- **Valkuilen:** V-005, V-032, V-067, V-072.
- **Bewijs:** B03-036 -> Bezig (Sim-getest; "rij in Chromium; dialogen W-2 tot en met W-4 volgen in S-G4-45; drie browsers in S-G4-39"). JLT-14 -> Bezig met "deel web". JLT-15 -> Geblokkeerd: "NIET GEVALIDEERD (echte apparaten en echte kijkers nodig; zie STAPPEN_P6.md)".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK (geen A-ONTWERP en geen R-ONTWERP: Jelly Leon-web valt buiten Peil)
- **Niveau:** A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); overige standaard
- **Stop en vraag als:** BG-15 niet genomen is; de haak meer dan een import en een aanroep in het upstream-bestand vraagt; de route `/media/v1/recommendations/home` in de lokale image ontbreekt (werk van golf 2; melden).

### S-G4-45 - Aanbevelingen: dialogen "Waarom aanbevolen?", "Wat kijk je graag?" en "Aanbevelingen aanpassen"
Dit nummer is later toegevoegd; in de volgorde hoort de stap direct na S-G4-20 (zie de tabel in 6.2).
- **Repo:** jelly-leon-web | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (npm-build; e2e achter stack.lock)
- **Werkpakketten en tests:** B03-036 (deel dialogen W-2, W-3, W-4); JLT-14 (deel web)
- **Vooraf:** S-G4-20.
- **Al gedaan?** `grep -rln "onboarding/candidates\|settings/me" <WERKMAP>/jelly-leon-web/src/jelly-leon` -> geen uitvoer = niet gestart (bestaat de map niet: S-G4-20 is niet klaar, STOP).
- **Lees eerst:** BOUWPLAN#F2.6.1 jelly-leon-web (rijen W-2, W-3, W-4 en W-5); BOUWPLAN#F2.5.3 Routes voor gebruikers; WP-JSON object B03-036, veld Acceptatie; BOUWPLAN#F2.9.7 Negatief en veiligheid; BOUWPLAN#F2.9.8 Gegevensbescherming
- **Bouw:**
  1. Dialoog "Waarom aanbevolen?" gevoed door `GET /media/v1/recommendations/items/{itemId}/why`: een tot drie redenen in gewone taal, met de knoppen "Niet interessant" en "Meer zoals dit"; nooit iets over een ander profiel; bij `show_reasons=false` bestaat de dialoog niet. Bron: BOUWPLAN#F2.6.1 (W-2).
  2. Dialoog "Wat kijk je graag?" (koude start): genrechips en een raster van 12 tot 24 titels uit `GET /media/v1/recommendations/onboarding/candidates`, knoppen "Opslaan" en "Overslaan", opslaan via `PUT /media/v1/recommendations/onboarding/me`. Bron: W-3.
  3. Dialoog "Aanbevelingen aanpassen": de schakelaars uit het bouwplan, lezen en schrijven via `GET|PUT /media/v1/recommendations/settings/me`; de lijst "Niet interessant" (`GET .../feedback`) met "Ongedaan maken" per regel; door de beheerder vergrendelde velden grijs met "Ingesteld door de beheerder". Bron: W-4.
  4. Knop "Wis mijn aanbevelingsgegevens" via `POST /media/v1/recommendations/me/forget`, alleen na het intypen van "WIS", met de tekst uit het bouwplan dat de kijkgeschiedenis bewaard blijft.
  5. Antwoord 412 bij opslaan: de melding "De instellingen zijn intussen gewijzigd. Opnieuw laden?" en geen stil overschrijven.
  6. De dialogen openen vanuit de eigen rij van S-G4-20 (kaartmenu, kaart "Vertel ons wat je leuk vindt" en de knop "Aanbevelingen aanpassen"); er komt geen nieuwe haak en geen nieuwe route bij. De knop uit S-G4-20 punt 6 wordt hier zichtbaar gemaakt.
  7. "Meer zoals dit" (W-5) blijft de ongewijzigde upstream-weergave: hier niets bouwen, alleen in de e2e-test vastleggen dat de rij er staat.
  8. Unit-tests, e2e-uitbreiding en EVIDENCE.
- **Tests (verplicht):** unit (in T-JLW-NPM) per scherm. Negatief: (a) wissen zonder "WIS" doet geen verzoek; (b) 412 overschrijft niets; (c) een kinderprofiel ziet in "Wat kijk je graag?" uitsluitend de titels die `/onboarding/candidates` teruggeeft: de client vult zelf niets aan; (d) 404 of 501 op een route: de dialoog toont "niet beschikbaar" en het startscherm blijft werken; (e) wissen raakt alleen de aanbevelingsgegevens: de test controleert dat er geen verzoek naar een upstream-route voor kijkgegevens gaat. Commando's: T-JLW-STATISCH, T-JLW-NPM, T-JLW-E2E.
- **Poort:** P-jelly-leon-web (volledig) + P-CONTRACT.
- **Valkuilen:** V-005, V-032, V-067, V-072.
- **Bewijs:** B03-036 -> Bezig (Sim-getest; "W-1 tot en met W-4 in Chromium; drie browsers in S-G4-39"). JLT-14 -> Bezig met "deel web".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-HARDE-EIS (VERPLICHT: "wissen" mag nooit kijkgeschiedenis, favorieten of hervatpunten raken) -> A-HERSTEL -> R-EERLIJK (geen A-ONTWERP en geen R-ONTWERP: Jelly Leon-web valt buiten Peil)
- **Niveau:** standaard; R-HARDE-EIS N4
- **Stop en vraag als:** een dialoog een route nodig heeft die niet in BOUWPLAN#F2.5.3 staat; een dialoog alleen te openen is met een nieuwe haak in een upstream-bestand.

### S-G4-21 - Web: rolbepaling, capability-probe en advies samenvoegen in het apparaatprofiel
- **Repo:** jelly-leon-web | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** hoog | **Zwaar:** ja (npm-build; e2e achter stack.lock)
- **Werkpakketten en tests:** B03-065 (webdeel 1); JLT-42 (deel web); JLT-48 (deel: module uit geeft het stock-profiel)
- **Vooraf:** S-G4-05 (routes E1 en E2 in de plugin). S-G4-25 levert de marker `jellyLeonBuild`; zonder die stap test deze stap de rol "Jelly Leon-app" met een nagebootste NativeShell en meldt dat in het bewijs.
- **Al gedaan?** `ls <WERKMAP>/jelly-leon-web/src/jelly-leon` -> bestaat niet = de haakmodule van golf 1 ontbreekt: STOP. `ls <WERKMAP>/jelly-leon-web/src/jelly-leon/deviceProfile` -> bestaat niet = niet gestart. `grep -n "jlHook" <WERKMAP>/jelly-leon-web/src/components/apphost.js` -> geen uitvoer = haak nog niet geplaatst.
- **Lees eerst:** WP-JSON object B03-065; BOUWPLAN#F5.6.1 jelly-leon-web (upstream-stijl); BOUWPLAN#F5.5.2 Endpoints (E1, E2, E8b); BOUWPLAN#F5.3.3 Beslisvolgorde, clientrollen en invarianten; `<WERKMAP>/jelly-leon-web/docs/platform-v2/PATCHES.md` (rij H-DEVICEPROFILE)
- **Bouw:**
  1. Haak H-DEVICEPROFILE: een import en een aanroep `jlHook('deviceProfile', ctx)` in `src/components/apphost.js`, in `function getDeviceProfile`, met foutgrens; de haak dekt het browserpad en het pad via NativeShell. Registreren met het eerstvolgende vrije JLW-nummer in PATCHES.md. Bron: PATCHES.md, rij H-DEVICEPROFILE.
  2. Fork-code in `src/jelly-leon/deviceProfile`: de rol van deze client bepalen volgens BOUWPLAN#F5.3.3 (Jelly Leon-web in de browser; Jelly Leon-app met de marker `jellyLeonBuild`; officiele app zonder marker).
  3. Probe: de mogelijkheden van het apparaat meten binnen 2 s, eenmaal per clientversie, en insturen via E2 (`PUT /media/v1/devices/self/probe`, hooguit 64 KiB).
  4. Advies ophalen via E1 (`GET /media/v1/devices/self/advice`) en samenvoegen met het upstream-profiel. Het advies mag alleen beperken; een verruiming wordt alleen toegepast als de regel bevestigd is.
  5. Officiele app zonder opt-in (E8b staat uit): exact het resultaat van de upstream `profileBuilder()`; de fork-code doet dan niets, ook geen probe.
  6. Module uit, 404, 501, time-out of een fout in de fork-code: het upstream-profiel, ongewijzigd.
  7. Geen persistente browseropslag voor meetwaarden behalve wat BOUWPLAN#F5.6.1 noemt; teksten in een eigen stringbestand.
  8. Unit-tests, e2e-uitbreiding en EVIDENCE.
- **Tests (verplicht):** unit (in T-JLW-NPM): rolbepaling per geval, samenvoegen, probe eenmaal per versie. Negatief: (a) module uit: het profiel is byte-gelijk aan dat van stock (vergelijk de JSON); (b) nagebootste NativeShell zonder marker en zonder opt-in: exact het upstream-profiel en geen verzoek naar E1 of E2; (c) een verruimend advies zonder bevestigde regel wordt genegeerd; (d) E1 geeft 404, 501 of time-out: afspelen start met het upstream-profiel; (e) een probe van meer dan 64 KiB wordt niet verstuurd; (f) een geforceerde fout in de fork-code breekt het afspelen niet. Commando's: T-JLW-STATISCH, T-JLW-NPM, T-JLW-E2E.
- **Poort:** P-jelly-leon-web (volledig) + P-CONTRACT.
- **Valkuilen:** V-005, V-032, V-067, V-072. Eigen: `getDeviceProfile` wordt ook door de officiele apps via hun webweergave gebruikt; een wijziging die daar het profiel verandert is een no-go van FASERING#Gates per functie.
- **Bewijs:** B03-065 -> Bezig (Sim-getest; "rol en probe in Chromium; stall-detectie volgt in S-G4-22; officiele apps in S-G4-30"). JLT-42 -> Bezig met "deel web". JLT-48 -> Bezig met "deel webprofiel". JLT-49 -> Geblokkeerd: "NIET GEVALIDEERD (echte apparaten en echte GPU's nodig; zie STAPPEN_P6.md)".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK (geen A-ONTWERP en geen R-ONTWERP: Jelly Leon-web valt buiten Peil)
- **Niveau:** A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); overige standaard
- **Stop en vraag als:** de haak meer dan een import en een aanroep vraagt; het profiel van een officiele app zonder opt-in ook maar een veld verschilt van upstream (no-go; niet opleveren).

### S-G4-22 - Web: stall-detectie met terugval, kwaliteitslabel en "Waarom?" in Playback Info
- **Repo:** jelly-leon-web | **Fase:** P4 (golf 4) | **Omvang:** groot | **Moeilijkheid:** hoog | **Zwaar:** ja (npm-build; e2e en tijdmeting achter stack.lock)
- **Werkpakketten en tests:** B03-065 (webdeel 2); B03-067 (webdeel); B03-005 (webdeel van de uitleg); JLT-41; JLT-47 (webdeel)
- **Vooraf:** S-G4-21; S-G4-08 (uitlegroute E5 in de plugin). BG-29: zonder besluit GEEN kwaliteitslabel in de OSD en GEEN feedbackvraag ("Dit klopt niet" in de melding van bouwpunt 3); bouw beide achter een instelling die standaard uit staat en test beide standen. Of het blok "Jelly Leon" in Playback Info onder BG-29 valt: ONBEKEND; zonder besluit staat ook dat blok achter dezelfde uit-instelling. Stall-detectie en terugval (bouwpunt 2) hangen niet aan BG-29.
- **Al gedaan?** `ls <WERKMAP>/jelly-leon-web/src/plugins/jellyLeon/playback` -> bestaat niet = niet gestart (de mapnaam `playback` is een voorstel; kijk met `ls <WERKMAP>/jelly-leon-web/src/plugins/jellyLeon` wat er al staat en volg het patroon van S-G3-24). `grep -n "jlHook" <WERKMAP>/jelly-leon-web/src/components/playerstats/playerstats.js` -> geen uitvoer = haak nog niet geplaatst.
- **Lees eerst:** WP-JSON objecten B03-065 en B03-067; BOUWPLAN#F5.6.1 jelly-leon-web (upstream-stijl) (rijen W1, W2, W3); BOUWPLAN#F5.5.2 Endpoints (E3, E4, E5); `<WERKMAP>/jelly-leon-web/docs/platform-v2/PATCHES.md` (rij H-PLAYBACKINFO); TEST-JSON rijen JLT-41 en JLT-47
- **Bouw:**
  1. Fork-eigen webplugin, geladen via de gegenereerde config.json van de image, die uitkomsten van het afspelen meldt via E3 (`POST /media/v1/playback/outcomes`). Bron: WP-JSON B03-065.
  2. Stall-detectie: start het beeld binnen 8 s niet of blijft het hangen, dan valt de speler terug naar de volgende methode; de hele terugval duurt hooguit 12 s. De server onthoudt de uitkomst (S-G4-06).
  3. Melding bij een echte terugval (toast): "Direct afspelen lukte niet op dit apparaat. Jelly Leon zet het nu om en onthoudt dit voor dit soort bestanden." met "Details" en "Dit klopt niet" (E4). Niet tonen bij deelnemers van Watch Together die niets kunnen kiezen (alleen het label).
  4. Kwaliteitslabel in de OSD: de plugin hangt zich via het event `SHOW_VIDEO_OSD` aan `document.body`, zoals `src/components/playback/skipsegment.ts` dat doet; werkt in Modern en Legacy zonder haak in de videoroute. De labelteksten letterlijk uit BOUWPLAN#F5.6.1, rij W1.
  5. Haak H-PLAYBACKINFO: een import en een aanroep in `src/components/playerstats/playerstats.js`, in `getTranscodingStats`, na het blok met `TranscodingInfo.TranscodeReasons`; registreren met het eerstvolgende vrije JLW-nummer. Het extra blok "Jelly Leon" toont wat E5 (`GET /media/v1/playback/sessions/{playSessionId}/explain`) teruggeeft.
  6. Het label en de uitleg veranderen de afspeelbeslissing nooit; ze tonen alleen wat de server besloot.
  7. Teksten in een eigen stringbestand; geen wijziging in `src/strings`.
  8. Unit-tests, e2e-uitbreiding met een tijdmeting van de terugval, en EVIDENCE.
- **Tests (verplicht):** unit (in T-JLW-NPM): stall-detectie met een nepklok, labelkeuze per geval uit rij W1, het blok "Jelly Leon" per antwoord van E5. Meting (JLT-41): terugval binnen 12 s op de testset, n en p95 noemen. Negatief: (a) module uit of een stock-server: geen label, geen blok, geen verzoek naar E3, E4 of E5; (b) E5 geeft 404, 501 of time-out: Playback Info toont het upstream-blok ongewijzigd; (c) een geforceerde fout in de fork-code laat de speler en de OSD werken; (d) er wordt geen terugval gemeld als de gebruiker zelf pauzeert of spoelt; (e) "Dit klopt niet" stuurt geen titel of bestandsnaam mee die de server niet al kent. Commando's: T-JLW-STATISCH, T-JLW-NPM, T-JLW-E2E.
- **Poort:** P-jelly-leon-web (volledig) + P-CONTRACT.
- **Valkuilen:** V-005, V-014, V-032, V-067, V-072.
- **Bewijs:** B03-065 en B03-067 -> Bezig (Sim-getest; "web in Chromium; drie browsers in S-G4-39; echte tv's en HDR-schermen NIET GEVALIDEERD (hardware)"). JLT-41 -> Bezig met n en p95. JLT-47 -> Bezig met "webdeel; beoordeling van beeld op een echt HDR-scherm NIET GEVALIDEERD (hardware)".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK (geen A-ONTWERP en geen R-ONTWERP: Jelly Leon-web valt buiten Peil)
- **Niveau:** A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); overige standaard
- **Stop en vraag als:** de config.json-generator in jelly-leon moet worden aangepast om de plugin te laden (werk voor de jelly-leon-baan; melden); de terugval alleen werkt met een wijziging in de upstream-afspeelbeheerder (niet doen; melden); de haak meer dan een import en een aanroep vraagt.

### S-G4-41 - Web: scherm "Dit apparaat" en de bevestigingsproef
Dit nummer is later toegevoegd; in de volgorde hoort de stap na S-G4-22 (zie de tabel in 6.2).
- **Repo:** jelly-leon-web | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** hoog (routehaak in twee upstream-bestanden) | **Zwaar:** ja (npm-build; e2e achter stack.lock)
- **Werkpakketten en tests:** B03-066 (webdeel: regels bekijken, bevestigen en afwijzen); B03-065 (webdeel: opt-in op een officiele app); JLT-42 (deel: een verruimende regel blijft voorgesteld tot bevestiging)
- **Vooraf:** S-G4-21 en S-G4-22; S-G4-06 (routes E6, E7, E8 en E8b in de plugin). BG-26.
- **Al gedaan?** `grep -rn "devices/self" <WERKMAP>/jelly-leon/plugins/JellyLeon/src -l` -> geen uitvoer = de serverroutes ontbreken: STOP en melden (werk voor de jelly-leon-baan). `grep -rn "ASYNC_USER_ROUTES" <WERKMAP>/jelly-leon-web/src/apps/modern/routes/asyncRoutes/user.ts <WERKMAP>/jelly-leon-web/src/apps/legacy/routes/asyncRoutes/user.ts` -> lees of er al een `jlHook`-aanroep bij staat (routehaak van een eerdere stap).
- **Lees eerst:** BOUWPLAN#F5.6.1 jelly-leon-web (upstream-stijl) (rijen W4 en W5); BOUWPLAN#F5.5.2 Endpoints (E6, E7, E8, E8b); WP-JSON object B03-066; `<WERKMAP>/jelly-leon-web/docs/platform-v2/PATCHES.md` (rij H-ROUTE); BOUWPLAN#F5.9.6 Negatief en veiligheid
- **Bouw:**
  1. Routehaak H-ROUTE in `src/apps/modern/routes/asyncRoutes/user.ts` en `src/apps/legacy/routes/asyncRoutes/user.ts` (bij `ASYNC_USER_ROUTES`): per bestand een import en een aanroep. Bestaat de haak al, dan alleen een route toevoegen in de fork-code. Registreren met het eerstvolgende vrije JLW-nummer. Bron: PATCHES.md, rij H-ROUTE.
  2. Scherm "Instellingen -> Afspelen -> Dit apparaat": rol, gemeten mogelijkheden (tabel met ja, nee of onbekend, bron en datum) en de regels met hun staat, uit E6.
  3. Knoppen "Opnieuw testen" (probe opnieuw, E2), "Regel afwijzen" (E7) en "Vergeet dit apparaat" (E8, met bevestigingsvraag).
  4. Bevestigingsproef (dialoog): speelt 8 s van een door de gebruiker gekozen eigen titel met de kandidaat-instelling en stelt de drie vragen uit het bouwplan; bevestigen of afwijzen via E7.
  5. Op een officiele app de schakelaar "Jelly Leon-advies gebruiken op dit apparaat" (E8b), standaard uit, met de uitleg uit het bouwplan.
  6. Toestanden: laden, leeg ("nog niets gemeten"), fout, onbekend, geen rechten (kind), module uit (het menupunt bestaat dan niet).
  7. Teksten in een eigen stringbestand.
  8. Unit-tests, e2e-uitbreiding en EVIDENCE.
- **Tests (verplicht):** unit (in T-JLW-NPM) per knop en per toestand. Negatief: (a) een kind kan niet bevestigen (de knop ontbreekt en E7 weigert); (b) bevestigen zonder gelukte proefsessie geeft 409 `test_session_required` en de regel blijft "voorgesteld"; (c) een tweede beslissing op dezelfde regel geeft 409 `decision_exists`; (d) een fout bij het afspelen in de proef geeft "afgewezen (technisch)"; (e) geen geschikte titel: "Geen titel met dit formaat gevonden" en geen proef; (f) E8b op een uitgesloten apparaat geeft 409 `device_excluded`; (g) module uit of een stock-server: het menupunt bestaat niet en de upstream-instellingen werken. Commando's: T-JLW-STATISCH, T-JLW-NPM, T-JLW-E2E.
- **Poort:** P-jelly-leon-web (volledig) + P-CONTRACT.
- **Valkuilen:** V-005, V-032, V-067, V-072.
- **Bewijs:** B03-066 -> Bezig (Sim-getest; "web in Chromium; echte beoordeling van beeld en geluid door een mens op echte apparaten NIET GEVALIDEERD (hardware)"). JLT-42 -> Bezig met "deel web".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-VEILIG (VERPLICHT: wie een regel mag bevestigen; het kind mag dat nooit) -> A-HERSTEL -> R-EERLIJK (geen A-ONTWERP en geen R-ONTWERP: Jelly Leon-web valt buiten Peil)
- **Niveau:** A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog: routehaak H-ROUTE in twee upstream-bestanden); R-VEILIG N4; overige standaard
- **Stop en vraag als:** de routehaak per bestand meer vraagt dan een import en een aanroep; BG-26 anders uitvalt dan "de gebruiker bevestigt zelf, de beheerder mag ook".

### S-G4-23 - Web: skipknoppen per type, standaardactie en groepsregel (drie haken)
- **Repo:** jelly-leon-web | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** hoog | **Zwaar:** ja (npm-build; e2e achter stack.lock)
- **Werkpakketten en tests:** B03-076 (webdeel: knoppen); B03-007 (afronding, punt clients: web); JLT-55 (deel web)
- **Vooraf:** S-G4-16 (serverdeel, marge aan het einde); S-G4-15 (route voor de voorkeur per gebruiker). BG-31 genomen met optie a1 (eigen knopteksten): zonder besluit, of bij a2 (upstream-teksten), komt er geen haak en start deze stap NIET; bewijs dan "Geblokkeerd (besluit BG-31)" bij B03-076 (webdeel) en JLT-55 (deel web).
- **Al gedaan?** `grep -n "jlHook" <WERKMAP>/jelly-leon-web/src/components/playback/skipsegment.ts <WERKMAP>/jelly-leon-web/src/apps/legacy/features/playback/utils/mediaSegmentSettings.ts <WERKMAP>/jelly-leon-web/src/apps/legacy/features/playback/utils/mediaSegmentManager.ts` -> geen uitvoer = geen van de drie haken geplaatst.
- **Lees eerst:** WP-JSON object B03-076; BOUWPLAN#F6.6.1 jelly-leon-web — speler; BOUWPLAN#F6.3.9 Upstream-sync, gedragsregister en compatibiliteit; `<WERKMAP>/jelly-leon-web/docs/platform-v2/PATCHES.md` (rijen H-SKIPTEXT, H-SEGACTION, H-SYNCPLAY-SKIP); BOUWPLAN#F6.9.3 Clientmatrix
- **Bouw:**
  1. Haak H-SKIPTEXT in `src/components/playback/skipsegment.ts`, in `setButtonText`: de knoptekst per segmenttype: "Sla intro over", "Sla samenvatting over", "Sla aftiteling over", "Sla vooruitblik over" en "Sla reclame over"; Engels "Skip intro", "Skip recap", "Skip credits"; andere talen houden de upstream-tekst (`MediaSegmentSkipPrompt`). Bron: BOUWPLAN#F6.6.1 en PATCHES.md, rij H-SKIPTEXT.
  2. Haak H-SEGACTION in `src/apps/legacy/features/playback/utils/mediaSegmentSettings.ts` (bij `DEFAULT_ACTIONS` en `getMediaSegmentAction`): de standaardactie voor Intro, Recap en Outro is "Vragen om over te slaan" (BG-31), en de voorkeur per gebruiker uit route 17 (`GET /media/v1/segments/preferences/me`, gebouwd in S-G4-15; het menu om haar te zetten volgt pas in S-G4-46) telt alleen als standaard wanneer op dit apparaat geen uitdrukkelijke upstream-instelling bestaat. De haak leest alleen; hij schrijft nooit een `segmentTypeAction`-sleutel en gebruikt geen persistente browseropslag.
  3. Haak H-SYNCPLAY-SKIP in `src/apps/legacy/features/playback/utils/mediaSegmentManager.ts`, in `skipSegment`: in een SyncPlay-groep gedraagt "Overslaan" zich als "Vragen" (ook voor kinderen); een klik wordt een enkele groeps-seek naar `EndTicks`; tooltip "In een groep vraagt Jelly Leon eerst".
  4. Elke haak: een import en een aanroep met foutgrens; elk een eigen eerstvolgend vrij JLW-nummer in PATCHES.md.
  5. De eigen keuze van de gebruiker in de upstream-instellingen wint altijd van de standaard uit punt 2.
  6. Herbasisproef: `python3 tools/jelly-leon-web/upstream_sync.py` in de stand die PATCHES.md voor een nieuwe haak voorschrijft (ONBEKEND welk subcommando - eerst vaststellen met: `sed -n 1,80p <WERKMAP>/jelly-leon-web/tools/jelly-leon-web/upstream_sync.py`).
  7. Unit-tests, e2e-uitbreiding en EVIDENCE.
- **Tests (verplicht):** unit (in T-JLW-NPM): tekst per type, standaardactie per type, groepsregel. e2e in Chromium, Modern en Legacy: de knop springt naar `EndTicks`; een scene na de aftiteling speelt gewoon af. Negatief: (a) na een hele sessie staat er geen nieuwe sleutel `segmentTypeAction__*` in localStorage; (b) een door de gebruiker gekozen actie wordt nooit overschreven; (c) module uit of een stock-server: tekst en gedrag zijn gelijk aan upstream; (d) een geforceerde fout in de fork-code laat de upstream-knop werken; (e) twee websessies in een groep: een enkele groeps-seek, bij beide binnen 500 ms, en geen sprong zonder bevestiging. Commando's: T-JLW-STATISCH, T-JLW-NPM, T-JLW-E2E.
- **Poort:** P-jelly-leon-web (volledig) + P-CONTRACT.
- **Valkuilen:** V-005, V-032, V-067, V-072. Eigen: `DEFAULT_ACTIONS` staat onder `src/apps/legacy` maar wordt door beide weergaven gebruikt; test dus altijd Modern en Legacy.
- **Bewijs:** B03-076 -> Bezig (Sim-getest; "knoppen in Chromium; hint en correctiepaneel in S-G4-46; drie browsers in S-G4-39"). JLT-55 -> Bezig met "deel web". B03-007 -> bijwerken met "punt clients: web".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK (geen A-ONTWERP en geen R-ONTWERP: Jelly Leon-web valt buiten Peil)
- **Niveau:** A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog: drie haken in upstream-bestanden); overige standaard
- **Stop en vraag als:** BG-31 "automatisch overslaan als standaard" zou vragen (vraag b, optie 2; dat botst met de afronding van B03-007; melden); BG-31 vraag c met optie 2 (automatisch overslaan in een groep) is gekozen: bouwpunt 3 dan niet zelf aanpassen, melden; een haak meer dan een import en een aanroep vraagt; de herbasisproef een conflict geeft.

### S-G4-46 - Web: hint na de aftiteling, "Klopt niet", correctiepaneel en voorkeur per gebruiker
Dit nummer is later toegevoegd; in de volgorde hoort de stap direct na S-G4-23 (zie de tabel in 6.2).
- **Repo:** jelly-leon-web | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (npm-build; e2e achter stack.lock)
- **Werkpakketten en tests:** B03-076 (webdeel: plugin in de speler); B03-075 (webdeel: melden en corrigeren); JLT-54 (deel speler); JLT-55 (deel web)
- **Vooraf:** S-G4-23; S-G4-15 (correctie-, meld- en voorkeurroutes in de plugin).
- **Al gedaan?** `ls <WERKMAP>/jelly-leon-web/src/plugins/jellyLeon/segments` -> bestaat niet = niet gestart (kijk met `ls <WERKMAP>/jelly-leon-web/src/plugins/jellyLeon` welke plugins er al staan).
- **Lees eerst:** BOUWPLAN#F6.6.1 jelly-leon-web — speler; BOUWPLAN#F6.5.4 Endpoints; WP-JSON objecten B03-075 en B03-076; BOUWPLAN#F6.9.3 Clientmatrix; BOUWPLAN#F6.9.4 Negatieve, veiligheids- en gegevensbeschermingstests
- **Bouw:**
  1. Fork-eigen webplugin in `src/plugins/jellyLeon/segments`, geladen via de gegenereerde config.json, die zich net als `skipsegment.ts` via `SHOW_VIDEO_OSD` aan de speler hangt. Bron: BOUWPLAN#F6.6.1.
  2. Hint "Na de aftiteling volgt nog een scène" (5 s, sluitbaar, `aria-live`), alleen als `GET /media/v1/segments/{itemId}` een `protected`-interval geeft; bij een fout of onbekend geen hint. De hint slaat nooit zelf iets over.
  3. "Klopt niet" voor kijkers in het OSD-menu: de kijker kiest een soort (begint te vroeg of te laat, geen intro, intro gemist, inhoud overgeslagen); verzenden via `POST /media/v1/segments/{itemId}/reports`; niet zichtbaar voor kinderprofielen; bij 429 de tekst "Je hebt vandaag al veel meldingen gedaan".
  4. Correctiepaneel voor editors, via een knop "Segmenten" in de OSD: "Begin hier", "Einde hier", type kiezen, "Klopt", "Klopt niet", "Ongedaan maken" en "Post-credit-scène hier", met bron en zekerheid; opslaan via `POST /media/v1/segments/{itemId}/corrections` en `.../corrections/{correctionId}/undo` met `If-Match` en `Idempotency-Key`. In schaduwmodus staat erbij "Nog niet zichtbaar voor kijkers".
  5. "Mijn overslaan-voorkeur" per type (vragen, overslaan, niets, standaard) in het OSD-menu, via `GET|PUT /media/v1/segments/preferences/me` (BOUWPLAN#F6.5.4, route 17); nooit via de upstream-sleutels `segmentTypeAction`. Bij een fout geldt de upstream-standaard met de melding "Voorkeur niet opgeslagen".
  6. Toestanden: laden, leeg (geen segmenten), fout, geen rechten, module uit (plugin doet niets).
  7. Teksten in een eigen stringbestand.
  8. Unit-tests, e2e-uitbreiding en EVIDENCE.
- **Tests (verplicht):** unit (in T-JLW-NPM) per onderdeel. Negatief: (a) een gewone kijker krijgt het correctiepaneel niet en `view=candidate` geeft 403 `not_editor`; (b) 412 bij opslaan geeft "Iemand anders wijzigde dit; opnieuw laden" en overschrijft niets; (c) een door de server afgewezen correctie geeft "Opslaan mislukt — niets gewijzigd" met de `trace_id`; (d) een kinderprofiel ziet "Klopt niet" niet en de meldroute weigert; (e) module uit of 404 of 501: geen hint, geen knop, upstream-gedrag; (f) de plugin schrijft niets in persistente browseropslag. Commando's: T-JLW-STATISCH, T-JLW-NPM, T-JLW-E2E.
- **Poort:** P-jelly-leon-web (volledig) + P-CONTRACT.
- **Valkuilen:** V-005, V-032, V-067, V-072.
- **Bewijs:** B03-076 -> Bezig (Sim-getest; "web in Chromium; drie browsers in S-G4-39"). B03-075 -> bijwerken met "webdeel". JLT-54 -> Bezig met "deel speler". JLT-59 -> Geblokkeerd: "NIET GEVALIDEERD (echte bibliotheek en echte kijkers nodig; zie STAPPEN_P6.md)".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-VEILIG (VERPLICHT: wie mag corrigeren) -> A-HERSTEL -> R-EERLIJK (geen A-ONTWERP en geen R-ONTWERP: Jelly Leon-web valt buiten Peil)
- **Niveau:** standaard; R-VEILIG N4
- **Stop en vraag als:** een van de genoemde routes in de lokale image ontbreekt (werk voor de jelly-leon-baan; melden); de config.json-generator moet worden aangepast.

### S-G4-43 - Web: capaciteitsadvies voor de start van een groep (dialoog)
Dit nummer is later toegevoegd; in de volgorde hoort de stap na S-G4-46 (zie de tabel in 6.2).
- **Repo:** jelly-leon-web | **Fase:** P4 (golf 4) | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** ja (npm-build; e2e achter stack.lock)
- **Werkpakketten en tests:** B03-025 (webdeel: capaciteitsadvies); JLT-04 (deel web)
- **Vooraf:** S-G4-09 (route E19 in de plugin); S-G3-24 (webplugin Watch Together). BG-13.
- **Al gedaan?** `ls <WERKMAP>/jelly-leon-web/src/plugins/jellyLeon/watchTogether` -> bestaat niet = S-G3-24 is niet klaar: STOP. `grep -rn "admission" <WERKMAP>/jelly-leon-web/src/plugins/jellyLeon/watchTogether -l` -> geen uitvoer = niet gestart.
- **Lees eerst:** BOUWPLAN#F1.6.1 Jelly Leon-webclient (rij W10); BOUWPLAN#F1.5.2 Endpoints (E19); WP-JSON object B03-025; TEST-JSON rij JLT-04; BOUWPLAN#F1.9.5 Negatief en veiligheid
- **Bouw:**
  1. In de bestaande webplugin `src/plugins/jellyLeon/watchTogether`: bij "Groep starten" en "Afspelen in groep" het advies ophalen via E19 (`GET /media/v1/watch/groups/{groupId}/admission`). Bron: BOUWPLAN#F1.6.1 (W10).
  2. Dialoog met de samenvatting uit het antwoord (voorbeeld uit het bouwplan: "2 van 3 deelnemers spelen direct af; 1 moet omzetten; capaciteit nu 1") en de knoppen "Toch starten" en "Annuleren".
  3. Toestand onbekend: "Capaciteit onbekend (planner niet bereikbaar)" met "Toch starten".
  4. Toestand blokkeren (alleen als de beheerder dat heeft aangezet): "Toch starten" uit, met de reden.
  5. Geen advies nodig (iedereen speelt direct af): geen dialoog.
  6. Teksten in het stringbestand van de plugin; unit-tests, e2e-uitbreiding en EVIDENCE.
- **Tests (verplicht):** unit (in T-JLW-NPM) per toestand. Negatief: (a) E19 geeft 404, 501 of time-out: geen dialoog en de groep start zoals upstream; (b) zonder de instelling "blokkeren" is "Toch starten" altijd bruikbaar: het advies weigert nooit; (c) een stock-client of stock-web die via upstream `Join` binnenkomt wordt nooit tegengehouden (test tegen de plugin met een rechtstreeks upstream-verzoek); (d) een geforceerde fout in de fork-code laat het upstream-menu werken. Commando's: T-JLW-STATISCH, T-JLW-NPM, T-JLW-E2E.
- **Poort:** P-jelly-leon-web (volledig) + P-CONTRACT.
- **Valkuilen:** V-005, V-032, V-067, V-072.
- **Bewijs:** B03-025 -> Bezig (Sim-getest; "webdeel; capaciteit met echte GPU's NIET GEVALIDEERD (hardware)"). JLT-04 -> Bezig met "deel web".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK (geen A-ONTWERP en geen R-ONTWERP: Jelly Leon-web valt buiten Peil)
- **Niveau:** standaard; A-BOUW N2 is toegestaan als A-VERKEN meldt dat de plugin van S-G3-24 al een dialoogpatroon heeft
- **Stop en vraag als:** E19 in de lokale image ontbreekt (werk voor de jelly-leon-baan; melden); de dialoog alleen kan met een tweede haak in een upstream-bestand.

### S-G4-24 - Web: strook voor reacties en chat (alleen als BG-12 "aan" is)
- **Repo:** jelly-leon-web | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (npm-build; e2e achter stack.lock)
- **Werkpakketten en tests:** B03-028 (webdeel); JLT-05 (chat-deel, web)
- **Vooraf:** BG-12 moet "aan" zijn; S-G4-10 (routes E14 en E15 in de plugin); S-G3-24. Is BG-12 "uit" of niet genomen: de stap vervalt en de bewijsregel wordt "Geblokkeerd (besluit BG-12)".
- **Al gedaan?** `grep -rn "messages" <WERKMAP>/jelly-leon-web/src/plugins/jellyLeon/watchTogether -l` -> geen uitvoer = niet gestart. `grep -rn "groups/{groupId}/messages" <WERKMAP>/jelly-leon/plugins/JellyLeon/src -l` -> geen uitvoer = het serverdeel ontbreekt: STOP.
- **Lees eerst:** WP-JSON object B03-028; BOUWPLAN#F1.6.1 Jelly Leon-webclient (rij W8); BOUWPLAN#F1.5.2 Endpoints (E14, E15); BOUWPLAN#F1.9.5 Negatief en veiligheid; BOUWPLAN#F1.4.4 Privacy
- **Bouw:**
  1. Strook boven de spelerbalk als fork-eigen overlay in de webplugin `src/plugins/jellyLeon/watchTogether`: vaste reacties en, als de beheerder tekst toestaat, een tekstveld. Bron: BOUWPLAN#F1.6.1 (W8).
  2. Versturen via E14 (`POST /media/v1/watch/groups/{groupId}/messages`); ophalen via E15 met een long-poll van hooguit 25 s.
  3. Ontvangen tekst altijd als tekst tonen, nooit als HTML.
  4. Antwoord 429: het veld kort uitschakelen met een melding; geen herhaalde pogingen in een lus.
  5. Uit, of een kind zonder toestemming: niets zichtbaar en geen verzoek naar E14 of E15.
  6. Berichten worden niet in de browser bewaard; na het verlaten van de groep is de strook leeg.
  7. Menupunt "Reacties" in het SyncPlay-menu alleen als de functie aan staat (bestaande haak van S-G3-24; geen nieuwe haak).
  8. Unit-tests, e2e-uitbreiding en EVIDENCE.
- **Tests (verplicht):** unit (in T-JLW-NPM). Negatief: (a) een bericht met `<script>` of een afbeeldingstag verschijnt als letterlijke tekst en voert niets uit; (b) 429 stopt het versturen en herhaalt niet; (c) een kind zonder toestemming ziet niets en doet geen verzoek; (d) functie uit: geen strook, geen menupunt, geen verzoek; (e) na het verlaten van de groep staat er niets van de berichten in localStorage of sessionStorage; (f) een geforceerde fout in de fork-code laat de speler werken. Commando's: T-JLW-STATISCH, T-JLW-NPM, T-JLW-E2E.
- **Poort:** P-jelly-leon-web (volledig) + P-CONTRACT + P-VEILIG.
- **Valkuilen:** V-005, V-032, V-067, V-072.
- **Bewijs:** B03-028 -> Bezig (Sim-getest; "web in Chromium") of Geblokkeerd (besluit BG-12). JLT-05 -> bijwerken met "chat-deel web".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-VEILIG (VERPLICHT: invoer van andere gebruikers wordt getoond; kinderregel) -> A-HERSTEL -> R-EERLIJK (geen A-ONTWERP en geen R-ONTWERP: Jelly Leon-web valt buiten Peil)
- **Niveau:** standaard; R-VEILIG N4
- **Stop en vraag als:** BG-12 niet "aan" is; de strook alleen kan met een nieuwe haak in de videoroute.

### S-G4-50 - Scènezoeker web: zoekscherm met tijdcode en "afspelen vanaf hier" (B03-008, webdeel)
- **Repo:** jelly-leon-web | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (npm-build; e2e achter stack.lock)
- **Werkpakketten en tests:** B03-008 (webdeel)
- **Vooraf:** S-G4-49 (routes `/media/v1/search` en `/media/v1/scenes`); de webhaakmodule van B03-017 (golf 1); haak H-ROUTE (BOUWPLAN: "H-ROUTE (JLW-0002 + F5-routehaak samengevoegd)", gebruikt door de scènezoeker en F5 "Dit apparaat").
- **Al gedaan?** `grep -n "H-ROUTE" <WERKMAP>/jelly-leon-web/docs/platform-v2/PATCHES.md` -> op 2026-11-11 alleen een rij onder "Geplande haken op de 12.x-basis (nog NIET uitgevoerd)"; staat H-ROUTE daar met een nummer (bijvoorbeeld door S-G4-41), dan bouwt deze stap erop voort. `grep -n '"B03-008"' <WERKMAP>/jelly-leon-web/docs/platform-v2/EVIDENCE.json` -> geen uitvoer = niet gestart.
- **Lees eerst:** BOUWPLAN#B03-008 — Semantische scènezoeker (Schermen/bediening: "Zoekresultaat met tijdcode, titel, reden, open stream at timestamp"); `<WERKMAP>/jelly-leon-web/docs/platform-v2/PATCHES.md` (kop "Geplande haken op de 12.x-basis", rij H-ROUTE); de rapporten van S-G4-49
- **Bouw:**
  1. Scope (A-VERKEN): wat S-G4-49 aan routes en velden opleverde; of H-ROUTE al bestaat (S-G4-41) of in deze stap komt.
  2. Zoekscherm via H-ROUTE: per resultaat titel, tijdcode en de cue als reden; "afspelen vanaf de tijdcode" via de upstream-speler. Vormgeving volgt upstream (buiten Peil).
  3. Toestanden: laden, leeg ("geen treffer"), fout, module uit (404: het menupunt bestaat dan niet), stock-server.
  4. Tests en EVIDENCE.
- **Tests (verplicht):** T-JLW-STATISCH; T-JLW-NPM; T-JLW-E2E (achter stack.lock): een zoekterm uit de testset geeft een resultaat en "afspelen" start op de tijdcode. Negatief: (a) module uit of stock-server: geen menupunt en de DOM van de upstream-zoekpagina is gelijk aan stock; (b) een geforceerde fout in de fork-code laat de upstream-zoekpagina werken; (c) de client toont alleen wat de server teruggeeft en vult niets aan (kinderprofiel).
- **Poort:** P-jelly-leon-web.
- **Valkuilen:** V-003, V-005.
- **Bewijs:** B03-008 (jelly-leon-web) -> Bezig (Sim-getest), webdeel. "NIET GEVALIDEERD (hardware): echte tv's en apparaten; zie N-P6-09."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK (geen A-ONTWERP en geen R-ONTWERP: Jelly Leon-web valt buiten Peil)
- **Niveau:** standaard
- **Stop en vraag als:** H-ROUTE niet als geregistreerde haak te plaatsen is; S-G4-49 geen tijdcode per resultaat levert.

### S-G4-54 - Live-tv web: overlapwaarschuwing vóór het plannen en opnamestatus (B03-012, webdeel)
- **Repo:** jelly-leon-web | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (npm-build; e2e achter stack.lock)
- **Werkpakketten en tests:** B03-012 (webdeel)
- **Vooraf:** S-G4-53; de webhaakmodule van B03-017 (golf 1).
- **Al gedaan?** `grep -n '"B03-012"' <WERKMAP>/jelly-leon-web/docs/platform-v2/EVIDENCE.json` -> geen uitvoer = niet gestart. `git -C <WERKMAP>/jelly-leon-web ls-files | grep -i livetv | head` -> de upstream-schermen voor live-tv (op 2026-11-11 onder meer `src/apps/dashboard/controllers/livetvtuner.js` en `livetvguideprovider.js`).
- **Lees eerst:** BOUWPLAN#B03-012 — Live-tv en DVR (Schermen/bediening: "Gids, live player, geplande opnames, overlapwaarschuwing"); E2E-JSON rij EX38; de rapporten van S-G4-53; `<WERKMAP>/jelly-leon-web/docs/platform-v2/PATCHES.md`
- **Bouw:**
  1. Scope (A-VERKEN): welke schermen upstream al heeft (gids, live player, geplande opnames) en wat ontbreekt: de overlapwaarschuwing vóór het opslaan van een opname en de opnamestatus uit S-G4-53. Per deel de haak; een haak die niet in PATCHES.md staat is een nieuwe patch met een nummer.
  2. Bouw alleen die delen, via de haakmodule, in de vormgeving van upstream.
  3. Module uit (404), stock-server of een fout: het scherm is gelijk aan upstream.
  4. Tests en EVIDENCE.
- **Tests (verplicht):** T-JLW-STATISCH; T-JLW-NPM; T-JLW-E2E (achter stack.lock, tegen de server met de nagebootste tuner van S-G4-53): twee overlappende opnames plannen -> de waarschuwing staat er vóór het opslaan (EX38). Negatief: (a) module uit of stock-server: de DOM is gelijk aan stock; (b) een geforceerde fout in de fork-code laat de upstream-schermen werken.
- **Poort:** P-jelly-leon-web.
- **Valkuilen:** V-003, V-099.
- **Bewijs:** B03-012 (jelly-leon-web) -> Bezig (Sim-getest), webdeel. "NIET GEVALIDEERD (hardware): echte tuner; zie N-P6-09."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK (geen A-ONTWERP en geen R-ONTWERP: Jelly Leon-web valt buiten Peil)
- **Niveau:** standaard
- **Stop en vraag als:** een deel een wijziging buiten een haak vraagt; S-G4-53 geen overlapmelding of status levert.

### S-G4-25 - Clients: marker `jellyLeonBuild` in de Android- en desktop-build
- **Repo:** jelly-leon-clients | **Fase:** P4 (golf 4) | **Omvang:** klein | **Moeilijkheid:** hoog (eerste patches in upstream-appcode van de fork) | **Zwaar:** ja (Gradle-build achter gradle.lock; desktop-build achter docker-build.lock)
- **Werkpakketten en tests:** B03-069 (deel marker); JLT-42 (deel: de rol "Jelly Leon-app" wordt herkend)
- **Vooraf:** geen stap van dit bestand; mag starten voor de gate van golf 3. Contractpunt C1.3-JLC-02: de eigen applicationId's wachten op bevestiging van de gebruiker; builds van deze stap niet verspreiden.
- **Al gedaan?** `grep -rn "jellyLeonBuild" <WERKMAP>/jelly-leon-clients/android <WERKMAP>/jelly-leon-clients/desktop/native` -> geen uitvoer = niet gestart. `grep -n "^| JLC-" <WERKMAP>/jelly-leon-clients/docs/platform-v2/PATCHES.md` -> het hoogste nummer is het laatst gebruikte (bij de verkenning JLC-0004).
- **Lees eerst:** WP-JSON object B03-069; BOUWPLAN#F5.3.3 Beslisvolgorde, clientrollen en invarianten; `<WERKMAP>/jelly-leon-clients/docs/platform-v2/PATCHES.md` (hoe een patch wordt geregistreerd); `<WERKMAP>/jelly-leon-clients/android/app/src/main/java/org/jellyfin/mobile/bridge/NativeInterface.kt` (`getDeviceInformation`); `<WERKMAP>/jelly-leon-clients/desktop/native/nativeshell.js`
- **Bouw:**
  1. Android: `fun getDeviceInformation()` in `NativeInterface.kt` geeft een extra veld `jellyLeonBuild` mee; `android/app/src/main/assets/native/nativeshell.js` geeft het veld door aan de webclient. Bron: WP-JSON B03-069.
  2. Desktop: `desktop/native/nativeshell.js` geeft hetzelfde veld mee op de plek waar `deviceName`, `appName` en `appVersion` worden gezet.
  3. De zichtbare naam en de technische identiteit (`appName`) blijven ongewijzigd; alleen het extra veld komt erbij (upstream negeert onbekende velden).
  4. Dit zijn de eerste patches in appcode van deze repo: registreer per app een JLC-patch met het eerstvolgende vrije nummer (kies het nummer pas na `git pull --rebase`), met bestand, reden en de test die hem bewaakt.
  5. Test die faalt als het veld na een upstream-sync verdwijnt (naast de bestaande tests in `tools/clients/tests`).
  6. Bouwen en EVIDENCE.
- **Tests (verplicht):** T-JLC-STATISCH. T-JLC-BOUW voor android en desktop. Negatief: (a) de test uit punt 5 faalt als het veld uit een van de drie bestanden wordt gehaald (eenmaal aantonen door het veld tijdelijk weg te halen; daarna terugzetten); (b) `appName` is na de patch gelijk aan upstream; (c) de registercontrole (`make check`) faalt als de patch niet in PATCHES.md staat.
- **Poort:** P-jelly-leon-clients.
- **Valkuilen:** V-021, V-075, V-076, V-080, V-128.
- **Bewijs:** B03-069 -> Bezig (Unit-getest; "marker gebouwd; herkenning in de webclient volgt in S-G4-21 en S-G4-30"). "Swiftfin: geen marker; NIET GEVALIDEERD (Mac/Xcode)."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog: patch in upstream-appcode, moet een upstream-sync overleven); overige standaard
- **Stop en vraag als:** de desktop-build niet lokaal te bouwen is zonder de desktopspike van S-P40-90 (dan alleen android opleveren en desktop als "Geblokkeerd (desktopspike)" melden); het veld alleen door te geven is met een wijziging in jelly-leon-web.

### S-G4-26 - Android TV: capabilityrapport automatisch sturen en beperkende regels samenvoegen
- **Repo:** jelly-leon-clients | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** hoog | **Zwaar:** ja (Gradle-build achter gradle.lock; emulator een tegelijk)
- **Werkpakketten en tests:** B03-069 (deel Android TV); JLT-42 (deel Android TV, voorwaardelijk op de emulator)
- **Vooraf:** S-G4-05 (route E2) en S-G4-06 (regels). BG-30 (mag de Jelly Leon-app het rapport automatisch sturen): zonder besluit start deze stap niet.
- **Al gedaan?** `grep -rn "devices/self/probe" <WERKMAP>/jelly-leon-clients/androidtv -l` -> geen uitvoer = niet gestart.
- **Lees eerst:** WP-JSON object B03-069; `<WERKMAP>/jelly-leon-clients/androidtv/app/src/main/java/org/jellyfin/androidtv/util/profile/deviceProfileReport.kt` (`createDeviceProfileReport`); `<WERKMAP>/jelly-leon-clients/androidtv/app/src/main/java/org/jellyfin/androidtv/util/profile/deviceProfile.kt` (`createDeviceProfile`); BOUWPLAN#F5.6.2 Gedrag per client; BOUWPLAN#F5.5.2 Endpoints (E1, E2)
- **Bouw:**
  1. Het bestaande rapport (`createDeviceProfileReport`, type `media_capabilities_report`) automatisch sturen naar `PUT /media/v1/devices/self/probe`: bij de eerste start en na een update van de app. Bron: WP-JSON B03-069.
  2. Opt-out als instelling in de app, standaard volgens BG-30.
  3. Advies ophalen (E1) en alleen beperkende regels samenvoegen in `createDeviceProfile`; een verruiming wordt nooit toegepast.
  4. Server zonder de module (404 of 501), geen netwerk of een time-out: de app werkt exact als upstream en probeert het niet in een lus opnieuw.
  5. Het rapport bevat wat upstream er al in zet; geen extra persoonsgegevens toevoegen.
  6. JLC-patch registreren met het eerstvolgende vrije nummer; test die de patch bewaakt.
  7. Bouwen, proef in de emulator en EVIDENCE.
- **Tests (verplicht):** unit-tests voor het samenvoegen (alleen beperkend) en voor "eenmaal per versie". T-JLC-STATISCH; T-JLC-BOUW (`make androidtv-bouw`). Emulatorproef: de Jelly Leon-build stuurt na de eerste start een rapport en de server toont het apparaat. Negatief: (a) tegen een stock-server stuurt de app niets en speelt gewoon af; (b) met de opt-out aan gaat er geen verzoek naar E2; (c) een verruimend advies verandert het profiel niet; (d) de officiele Android TV-app (ongewijzigd pakket, versie en sha256 in het bewijs) stuurt niets automatisch en speelt gewoon af. Proefcommando: `python3 tools/clients/client_compat.py android --image <jelly-leon-image> --soorten tv --bediend fork --uit <rapport.json>` achter `flock <WERKMAP>/.lokaal/stack.lock flock <WERKMAP>/.lokaal/gradle.lock nice -n 10 ...`.
- **Poort:** P-jelly-leon-clients + P-CONTRACT.
- **Valkuilen:** V-021, V-075, V-076, V-080, V-128.
- **Bewijs:** B03-069 -> Bezig (Sim-getest in de emulator; "de emulator heeft geen echte decoder: de inhoud van het rapport is NIET GEVALIDEERD (hardware)"). JLT-42 -> Bezig met "deel Android TV, emulator". Mislukt de emulator: validatie "Sim-mislukt" met de oorzaak.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-VEILIG (VERPLICHT: de app stuurt zelfstandig apparaatgegevens; opt-out en inhoud controleren) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog: eerste gedragspatch in Kotlin-appcode); R-VEILIG N4; overige standaard
- **Stop en vraag als:** BG-30 niet genomen is; KVM in de container niet beschikbaar is; de emulator niet binnen 4 GiB blijft (een herhaling met 5 GiB is toegestaan, beide uitkomsten in het bewijs; daarna stoppen en melden).

### S-G4-27 - Android TV: overlay-tekst per segmenttype en Recap standaard "vragen"
- **Repo:** jelly-leon-clients | **Fase:** P4 (golf 4) | **Omvang:** klein | **Moeilijkheid:** hoog (patch in upstream-appcode) | **Zwaar:** ja (Gradle-build achter gradle.lock; emulator een tegelijk)
- **Werkpakketten en tests:** B03-077 (deel Android TV); B03-007 (afronding, punt clients: Android TV); JLT-55 (deel Android TV, fork-app)
- **Vooraf:** S-G4-16. BG-31 met optie a1 (eigen knopteksten en daarmee clientpatches) en BG-08 (welke clients een eigen patch krijgen): zonder een van beide start deze stap niet; bewijs "Geblokkeerd (besluit BG-31)" of "(besluit BG-08)".
- **Al gedaan?** `grep -n "segment_action_skip" <WERKMAP>/jelly-leon-clients/androidtv/app/src/main/java/org/jellyfin/androidtv/ui/playback/overlay/SkipOverlayView.kt` -> staat er alleen de ene upstream-tekst = niet gestart. `grep -n "RECAP" <WERKMAP>/jelly-leon-clients/androidtv/app/src/main/java/org/jellyfin/androidtv/preference/UserPreferences.kt` -> geen uitvoer = Recap heeft nog geen standaard.
- **Lees eerst:** WP-JSON object B03-077; BOUWPLAN#F6.6.3 Clients; de twee bestanden uit "Al gedaan?"; `<WERKMAP>/jelly-leon-clients/docs/platform-v2/PATCHES.md`; TEST-JSON rij JLT-55
- **Bouw:**
  1. `SkipOverlayView.kt`: de tekst van de overlay per segmenttype ("Sla intro over" en de andere teksten uit BOUWPLAN#F6.6.1) in plaats van de ene tekst `R.string.segment_action_skip`; nieuwe tekstsleutels in een eigen bronbestand, de upstream-sleutel blijft bestaan. Bron: WP-JSON B03-077.
  2. `UserPreferences.kt`, voorkeur `mediaSegmentActions`: naast Intro en Outro ook `MediaSegmentType.RECAP to MediaSegmentAction.ASK_TO_SKIP` als standaard.
  3. Een door de gebruiker gekozen actie blijft altijd gelden; de patch verandert alleen de standaard.
  4. JLC-patch registreren met het eerstvolgende vrije nummer; test die de patch bewaakt.
  5. Bouwen, proef in de emulator en EVIDENCE.
- **Tests (verplicht):** unit-test voor de tekst per type en voor de standaard. T-JLC-STATISCH; T-JLC-BOUW (`make androidtv-bouw`). Emulatorproef met `beoordeel_segmenten` uit `tools/clients/compat/scenario.py`: de overlay toont de tekst per type en de sprong komt uit op het einde van het segment. Negatief: (a) tegen een stock-server zonder segmenten verschijnt geen overlay; (b) een bestaande eigen keuze van de gebruiker wordt niet overschreven: unit-test op de voorkeur (een opgeslagen waarde wint van de standaard); de proef "vorige build installeren, keuze zetten, nieuwe build eroverheen installeren" alleen als het harnas dat kan (ONBEKEND - eerst vaststellen met: `grep -n "installeer" <WERKMAP>/jelly-leon-clients/tools/clients/compat/*.py`); kan het niet, dan staat in het bewijs "app-update niet in de emulator beproefd"; (c) de officiele Android TV-app toont "Overslaan" en heeft Recap standaard uit: dat is het bekende stock-gedrag en geen fout. Proefcommando: `python3 tools/clients/client_compat.py android --image <jelly-leon-image> --soorten tv --bediend fork --uit <rapport.json>` achter stack.lock en gradle.lock.
- **Poort:** P-jelly-leon-clients.
- **Valkuilen:** V-021, V-075, V-076, V-080, V-128.
- **Bewijs:** B03-077 -> Bezig (Sim-getest in de emulator). JLT-55 -> Bezig met "deel Android TV". "Echte tv's NIET GEVALIDEERD (hardware); Swiftfin heeft geen skipknoppen en is NIET GEVALIDEERD (Mac/Xcode)."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog: patch in upstream-appcode); overige standaard
- **Stop en vraag als:** BG-08 geen clientpatch toestaat (dan vervalt de stap: "Geblokkeerd (besluit BG-08)"); de overlay in de emulator niet verschijnt terwijl de server segmenten levert (eerst met de officiele app vergelijken en de uitkomst melden). Let op: de optie `--migratie-van` van het harnas migreert de gegevens van de server (JLT-60) en installeert geen oudere app; gebruik hem niet voor deze stap.

### S-G4-28 - Android: knoptekst per type in de native speler; desktop: marge aan het einde meten
- **Repo:** jelly-leon-clients | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** hoog (patch in upstream-appcode) | **Zwaar:** ja (Gradle-build achter gradle.lock; emulator een tegelijk)
- **Werkpakketten en tests:** B03-077 (deel Android en desktop); B03-007 (afronding, punt clients: Android en desktop); JLT-55 (deel Android fork-app en officiele app; deel desktop voorwaardelijk)
- **Vooraf:** S-G4-27. BG-31 (optie a1) en BG-08; zonder een van beide start deze stap niet. Het desktop-deel alleen als de desktopspike van S-P40-90 (STAPPEN_P4_GOLF1_2.md) is geslaagd.
- **Al gedaan?** `grep -n "skip_media_segment" <WERKMAP>/jelly-leon-clients/android/app/src/main/java/org/jellyfin/mobile/player/ui/playermenuhelper/SkipMediaSegmentButton.kt` -> staat er alleen de ene upstream-tekst = niet gestart.
- **Lees eerst:** WP-JSON object B03-077; BOUWPLAN#F6.6.3 Clients; het bestand uit "Al gedaan?"; BOUWPLAN#F6.9.3 Clientmatrix; `<WERKMAP>/jelly-leon-clients/tools/clients/compat/scenario.py` (`beoordeel_segmenten`)
- **Bouw:**
  1. `SkipMediaSegmentButton.kt`: de knoptekst per segmenttype in plaats van de ene tekst `skip_media_segment`; nieuwe tekstsleutels in een eigen bronbestand. Recap standaard "vragen" in de native speler van de fork-app. Bron: WP-JSON B03-077.
  2. JLC-patch registreren met het eerstvolgende vrije nummer; test die de patch bewaakt.
  3. Meting officiele Android-app (ongewijzigd pakket; versie en sha256 in het bewijs), native speler: gedrag bij Intro, Outro en Recap voor en na het opslaan van "Acties voor mediasegmenten" in de webinstellingen. De module schrijft zelf niets; de meting legt vast wat upstream doet.
  4. Desktop (voorwaardelijk): de sprong aan het einde van het bestand met marge 0 en met 1,0 s; hergebruik het desktop-onderdeel van het harnas (`make compat-desktop JL_IMAGE=<jelly-leon-image> DESKTOP_BUILD=<map>`).
  5. Bouwen, proeven en EVIDENCE.
- **Tests (verplicht):** unit-test voor de tekst per type. T-JLC-STATISCH; T-JLC-BOUW (`make android-bouw`). Emulatorproef telefoon: `python3 tools/clients/client_compat.py android --image <jelly-leon-image> --soorten telefoon --bediend fork --uit <rapport.json>` en daarna dezelfde proef met `--bediend officieel --aanvullen`. Negatief: (a) de officiele app toont na de proef nog steeds "Skip" (de patch zit alleen in de fork-app); (b) een eigen keuze van de gebruiker blijft na een update staan; (c) desktop met marge 0 mag vastlopen aan het einde (bekend upstream-gedrag): leg vast wat er gebeurt, en met 1,0 s mag het niet vastlopen.
- **Poort:** P-jelly-leon-clients.
- **Valkuilen:** V-021, V-075, V-076, V-080, V-128.
- **Bewijs:** B03-077 -> Bezig (Sim-getest; per client de versie en sha256). JLT-55 -> Bezig met "deel Android"; het desktop-deel "Sim-getest" of "Geblokkeerd (desktopspike S-P40-90 niet geslaagd)". "Tablet volgt in S-G4-30." B03-007 -> bijwerken met "punt clients: Android (en desktop als de desktopspike slaagde)".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog: patch in upstream-appcode); overige standaard
- **Stop en vraag als:** de native speler van de fork-app in de emulator niet te kiezen is (dan alleen de webspeler meten en dat melden); de desktop-build ontbreekt.

### S-G4-29 - Clientmatrix aanbevelingen in de emulators (met loggende proxy)
- **Repo:** jelly-leon-clients | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (emulator een tegelijk; stack.lock en gradle.lock)
- **Werkpakketten en tests:** B03-037 (deel emulators en desktop); JLT-14 (deel Android, Android TV, desktop)
- **Vooraf:** S-G4-20 en S-G4-45 (rij en dialogen in web); S-G4-12 (providervolgorde); S-G3-32 (WP-JSON B03-037 noemt B03-003 als afhankelijkheid). BG-15 (Android TV-rij als clientpatch ja of nee): het besluit wordt in de matrix vastgelegd; zonder besluit staat er "open besluit BG-15".
- **Al gedaan?** `grep -il proxy <WERKMAP>/jelly-leon-clients/tools/clients/compat/*.py` -> geen uitvoer = de loggende proxy ontbreekt (bij de verkenning ontbrak hij). `grep -n "recommendations" <WERKMAP>/jelly-leon-clients/tools/clients/compat/scenario.py` -> geen uitvoer = het scenario ontbreekt.
- **Lees eerst:** WP-JSON object B03-037; BOUWPLAN#F2.9.5 Clientmatrix; TEST-JSON rij JLT-14; `<WERKMAP>/jelly-leon-clients/tools/clients/compat/scenario.py`; `<WERKMAP>/jelly-leon-clients/tools/clients/compat/emulator.py`
- **Bouw:**
  1. Loggende proxy als klein onderdeel van het harnas (nieuwe module in `tools/clients/compat`, met unit-test in `tools/clients/tests`): staat tussen emulator en server en legt per verzoek alleen de methode, het pad zonder querywaarden en de statuscode vast. Geen headers, geen tokens, geen inhoud. Bron: WP-JSON B03-037.
  2. Scenario "aanbevelingen" in `scenario.py`. Telefoon, officiele app en Jelly Leon-app (beide tonen de webclient van de server): de rij "Aanbevolen voor jou" is zichtbaar en "Aanbevelingen aanpassen" is bruikbaar; de proxy ziet `/media/v1/recommendations/home`.
  3. Tablet-AVD: de rij in tabletbreedte en "Aanbevelingen aanpassen" bruikbaar.
  4. Android TV, officiele app (native, stock-client): de detailpagina toont in "Meer zoals dit" de uitvoer van de Jelly Leon-provider; de proxy ziet `/Items/{id}/Similar` en de UI-dump (`uiautomator dump`, bestaande functie in `emulator.py`) bevat de titels.
  5. Drie standen per client: plugin aan met gezette providervolgorde, plugin aan zonder volgorde, plugin uit. Stock wordt twee keer gemeten voor de spreiding.
  6. Desktop: alleen na een geslaagde desktopspike (S-P40-90): rij zichtbaar en "Waarom aanbevolen?" opent; anders "Geblokkeerd" met de reden.
  7. Matrix in het rapport: per client de versie en sha256 van het pakket, de rol (stock-client of Jelly Leon-web-client) en de uitkomst. Swiftfin, derden-clients en echte apparaten staan erin als NIET GEVALIDEERD.
  8. EVIDENCE bijwerken.
- **Tests (verplicht):** unit-test van de proxy (in `make test`). T-JLC-STATISCH. Proef: `python3 tools/clients/client_compat.py android --image <jelly-leon-image> --stock-image <stock-12.x-image> --soorten telefoon,tablet,tv --vergelijk-soorten tv --bediend officieel --uit <rapport.json>` en daarna dezelfde proef met `--bediend fork --aanvullen`, achter `flock <WERKMAP>/.lokaal/stack.lock flock <WERKMAP>/.lokaal/gradle.lock nice -n 10 ...`. Negatief: (a) plugin uit of geen volgorde gezet: "Meer zoals dit" op Android TV is als verzameling gelijk aan stock; (b) tegen de stock-server is er geen rij en werken inloggen, startscherm, detailpagina en afspelen van de testfilm gewoon; (c) het proxylog bevat geen token: zoek in het log naar het testtoken en naar `api_key=` met een waarde en verwacht nul treffers; (d) een emulator die niet start geeft "Sim-mislukt", geen geslaagde rij.
- **Poort:** P-jelly-leon-clients.
- **Valkuilen:** V-021, V-075, V-076, V-080, V-128.
- **Bewijs:** B03-037 -> Bezig (Sim-getest; matrix met versies). JLT-14 -> Bezig met "deel emulators". "Swiftfin NIET GEVALIDEERD (Mac/Xcode); derden-clients en echte tv's, telefoons en tablets NIET GEVALIDEERD (hardware)." De webrijen van de matrix (drie browsers, UA-simulatie, stock-web) komen uit S-G4-39.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** de soort `tablet` door het onderdeel `android` van het harnas wordt geweigerd (ONBEKEND - eerst vaststellen met: `grep -n "tablet" <WERKMAP>/jelly-leon-clients/tools/clients/compat/*.py`); KVM in de container niet beschikbaar is; de emulator niet binnen 4 GiB blijft (een herhaling met 5 GiB is toegestaan, beide uitkomsten in het bewijs; daarna stoppen en melden).

### S-G4-30 - Clientmatrix golf 4: ondertitels, kwaliteit, apparaten en skipknoppen in de emulators
- **Repo:** jelly-leon-clients | **Fase:** P4 (golf 4) | **Omvang:** groot | **Moeilijkheid:** gewoon | **Zwaar:** ja (emulator een tegelijk; stack.lock en gradle.lock)
- **Werkpakketten en tests:** B03-049 (P4-deel: matrix gemarkeerd spoor), B03-058 (deel clients), B03-068 (deel officiele apps), B03-077 (deel matrix); JLT-25, JLT-38, JLT-42, JLT-46, JLT-55 (telkens het deel emulators)
- **Vooraf:** S-G4-13, S-G4-14, S-G4-07, S-G4-23, S-G4-46, S-G4-26, S-G4-27, S-G4-28, S-G4-29 (proxy), S-G3-25. Is S-G4-26 vervallen door BG-30, dan is het Android TV-deel van JLT-42 "Geblokkeerd (besluit BG-30)".
- **Al gedaan?** `ls <WERKMAP>/jelly-leon-clients/docs/platform-v2/` en `grep -c "JLT-55" <WERKMAP>/jelly-leon-clients/docs/platform-v2/EVIDENCE.json` -> 0 = nog geen bewijs van deze matrix.
- **Lees eerst:** TEST-JSON rijen JLT-25, JLT-38, JLT-46 en JLT-55; BOUWPLAN#F6.9.3 Clientmatrix; BOUWPLAN#F5.9.4 Clientmatrix; `<WERKMAP>/jelly-leon-clients/tools/clients/compat/scenario.py`; het rapport van S-G4-29
- **Bouw:** de stap wordt in vier runs gedaan, een per onderwerp; elke run vult hetzelfde rapport aan (`--aanvullen`). Een run die niet af komt is geen reden om de andere over te slaan.
  1. Ondertitels (JLT-25): in elke client is het gemarkeerde spoor te kiezen en draagt het de markering "Gesynchroniseerd" in de naam (vastgelegd in S-G3-08; het spoor "Machinevertaling" bestaat pas in P5, S-P5-115); afspeelmethode en omzetredenen zijn met en zonder het spoor gelijk; de standaardkeuze per client wordt vastgelegd; de gesynchroniseerde kopie is nooit de standaard.
  2. Kwaliteit (JLT-38): Android TV en de officiele apps werken ongewijzigd (inloggen en afspelen); geen kwaliteitslabel in stock-clients.
  3. Apparaten (JLT-46, JLT-42): officiele Android TV-app en de officiele Android-app (native speler en webspeler) krijgen in de standen plugin uit, aan en aan met opt-in voor een ander apparaat dezelfde afspeelbeslissing; de Jelly Leon-app met marker wordt als Jelly Leon-app herkend; de Android TV-build van S-G4-26 stuurt het rapport.
  4. Skipknoppen (JLT-55): telefoon en tablet-AVD, fork-app en officiele app, webweergave en native speler, voor en na het opslaan van de webinstellingen; Android TV fork-app en officiele app; teksten per type, juiste moment, nooit automatisch overslaan als standaard.
  5. Per run de versie en sha256 van elk pakket in het rapport; de rol per client (stock-client of Jelly Leon-web-client).
  6. Desktop per onderwerp alleen na de geslaagde desktopspike; anders "Geblokkeerd" met de reden.
  7. Samenvatting per JLT-rij in EVIDENCE, met het rapportpad.
- **Tests (verplicht):** T-JLC-STATISCH. Proef per run: `python3 tools/clients/client_compat.py android --image <jelly-leon-image> --stock-image <stock-12.x-image> --soorten telefoon,tablet,tv --vergelijk-soorten telefoon,tv --bediend fork --uit <rapport.json>` en dezelfde run met `--bediend officieel --aanvullen`, achter stack.lock en gradle.lock. Negatief: (a) tegen de stock-server gedragen fork-app en officiele app zich als upstream: geen gemarkeerd spoor ("Gesynchroniseerd" of "Machinevertaling"), geen label, geen eigen skiptekst door de server; (b) de afspeelbeslissing van een niet-gekozen apparaat verandert in geen van de drie standen; (c) de officiele native speler crasht niet op een Recap-segment (gedrag vastleggen, niet "verbeteren"); (d) een run met een gefaalde emulator krijgt "Sim-mislukt" en telt niet als gehaald.
- **Poort:** P-jelly-leon-clients + P-HARDE-EIS (spoorkeuzes en hervatpunten van de testgebruiker zijn na de runs gelijk aan ervoor: `python3 tools/clients/client_compat.py hervatproef --image <jelly-leon-image> --soort tv --bediend fork -n 3 --uit <rapport.json>`; `--image` is verplicht).
- **Valkuilen:** V-021, V-075, V-076, V-080, V-128.
- **Bewijs:** JLT-25, JLT-38, JLT-42, JLT-46, JLT-55 -> Bezig (Sim-getest, "deel emulators"; per rij het rapportpad). "De emulator heeft geen echte decoder; Swiftfin, Safari en tvOS NIET GEVALIDEERD (Mac/Xcode); derden-clients, Chromecast, DLNA en echte apparaten NIET GEVALIDEERD (hardware)."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-HARDE-EIS (VERPLICHT: spoorkeuzes en hervatpunten blijven gelijk; stock-clients ongewijzigd) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard; R-HARDE-EIS N4
- **Stop en vraag als:** een stock-client met de plugin aan anders beslist dan met de plugin uit (dat is een fout in de plugin: stoppen, melden, de jelly-leon-baan herstelt); de vier runs samen niet binnen een werksessie passen (dan na elke run committen en de rest als vervolg melden).

### S-G4-52 - Offline downloaden in de Android-app: rechten, verlopen, hervatten en offline kijken (B03-011, clientdeel)
- **Repo:** jelly-leon-clients | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (Gradle en emulator; eerst stack.lock, dan gradle.lock)
- **Werkpakketten en tests:** B03-011 (clientdeel)
- **Vooraf:** S-G4-51 (rechten aan de serverkant); S-G4-30 (de vorige emulatorstap in deze baan). BG-08: zonder besluit geen eigen patches voor Swiftfin. ADR-0008 van jelly-leon-clients (eigen builds niet verspreiden) blijft gelden.
- **Al gedaan?** `git -C <WERKMAP>/jelly-leon-clients ls-files android/app/src/main/java/org/jellyfin/mobile/downloads` -> upstream-downloadbeheer aanwezig (op 2026-11-11 onder meer `DownloadManager.kt`, `DownloadWorker.kt`, `DownloadsFragment.kt`). `grep -n '"B03-011"' <WERKMAP>/jelly-leon-clients/docs/platform-v2/EVIDENCE.json` -> geen uitvoer = niet gestart.
- **Lees eerst:** TASKS-JSON object B03-011; BOUWPLAN#B03-011 — Offline downloaden; `<WERKMAP>/jelly-leon-clients/docs/platform-v2/INVENTARIS.md`; `<WERKMAP>/jelly-leon-clients/docs/platform-v2/PATCHES.md`; `<WERKMAP>/jelly-leon-clients/docs/adr/ADR-0008-geen-truenas-app-voor-clients.md`; de rapporten van S-G4-51
- **Bouw:**
  1. Scope (A-VERKEN): wat upstream jellyfin-android al doet (downloadbeheer, hervatten en opnieuw proberen, kwaliteit van de download) tegen de bron ("geautoriseerde media versleuteld lokaal opslaan in de client waar mogelijk, verlopen rechten en opslagquota"; overzicht met voortgang, opslag, kwaliteit en opruimen). Android TV en desktop: ONBEKEND of upstream daar downloaden heeft - A-VERKEN stelt vast met `git -C <WERKMAP>/jelly-leon-clients ls-files androidtv desktop | grep -i download`. Of offline kijken voortgang of gezien-status naar de server terugschrijft: ONBEKEND - A-VERKEN stelt het vast (dat bepaalt R-HARDE-EIS).
  2. Alleen wat ontbreekt en op de emulator te testen is, als geregistreerde JLC-patch met test.
  3. Emulatorproef: downloaden, netwerk weg, offline kijken; daarna een uitgezet account (S-G4-51) en een nieuwe download. Bron: TASKS-JSON B03-011 (Acceptatie).
  4. EVIDENCE bijwerken.
- **Tests (verplicht):** T-JLC-STATISCH; T-JLC-BOUW (`make android-bouw`); de emulatorproef uit punt 3 met `make compat-android JL_IMAGE=<jelly-leon-image>` of het commando dat A-VERKEN in `tools/clients/compat` vindt (eerst `--help`). Negatief: (a) een uitgezet account start geen nieuwe download; (b) een download met ingetrokken rechten speelt niet meer af als de bron dat vraagt (ONBEKEND of upstream dit kent; A-VERKEN); (c) T-JLC-STATISCH faalt bij een JLC-patch zonder registerregel.
- **Poort:** P-jelly-leon-clients.
- **Valkuilen:** V-011, V-012, V-057.
- **Bewijs:** B03-011 (jelly-leon-clients) -> Bezig (Sim-getest). "NIET GEVALIDEERD (hardware): echte telefoons; NIET GEVALIDEERD (Mac/Xcode): Swiftfin; zie STAPPEN_P6.md, N-P6-09." EX35 blijft bij S-P6-13.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG (tegelijk; R-VEILIG VERPLICHT: tokens en versleutelde opslag op het toestel) -> A-HERSTEL -> R-EERLIJK. R-HARDE-EIS erbij (VERPLICHT) als offline kijken hervatpunten of gezien-status naar de server terugschrijft.
- **Niveau:** standaard; R-VEILIG N4; R-HARDE-EIS N4 als hij loopt
- **Stop en vraag als:** het gat alleen met een eigen build op een echt toestel of met verspreiding te testen is (ADR-0008); een emulator het geheugen van de machine overschrijdt (AGENTEN.md 3.3).

### S-G4-31 - Hub: adapter voor Jelly Leon en de stap "Hub-sleutelset kopieren"
- **Repo:** ai-server-manager | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** hoog | **Zwaar:** nee (alleen de afsluitende `make web-build` en `make web-e2e` zijn zwaar: na elkaar, niet naast een andere npm-build)
- **Werkpakketten en tests:** contractpunt C1.3-ASM-21 (deel Jelly Leon, Moment P4); voorwaarde voor B03-029, B03-039, B03-058, B03-069, B03-078 (Hub-kaarten)
- **Vooraf:** S-P3-010, S-P3-020 en S-P3-070 (STAPPEN_P3.md: ADR, adapterbasis en koppelscherm); het pinmechanisme JL4 in de plugin (golf 1, B03-017). Mag starten voor de gate van golf 3.
- **Al gedaan?** Lees eerst in het ADR van S-P3-010 welke adaptermap is gekozen (voorstel in STAPPEN_P3.md: `apps/api/src/hub/adapters`). `ls <WERKMAP>/ai-server-manager/<adaptermap>` -> map ontbreekt = S-P3-020 is niet klaar: STOP. `grep -rni "jelly" <WERKMAP>/ai-server-manager/<adaptermap> -l` -> geen uitvoer = niet gestart. `grep -n "Jelly Leon-plugin" <WERKMAP>/ai-server-manager/apps/web/src/app/instellingen/diensten/DienstenScreen.tsx` -> geen uitvoer = de kopieerstap voor de plugin ontbreekt (let op: de regel "Jelly Leon-platform (jelly-leon-platform)" in `EIGEN_DIENSTEN` is een andere dienst en telt niet).
- **Lees eerst:** `<WERKMAP>/ai-server-manager/docs/platform-v2/CONTRACT_1.3_CONFORMITEIT.md` (rij C1.3-ASM-21); BOUWPLAN#10.4 Hub-koppeling (JL4); het ADR van S-P3-010 (vinden met `ls <WERKMAP>/ai-server-manager/docs/adr | grep -i adapter`); `<WERKMAP>/ai-server-manager/apps/api/src/hub/servicecalls.py` en `keys.py`; de basismodule van S-P3-020 in de adaptermap
- **Bouw:**
  1. Adaptermodule voor Jelly Leon in de map uit het ADR, op de basis van S-P3-020. Twee leeswegen: (a) de gewone Jellyfin-API met een eigen niet-beheerder-gebruiker (het token is een geheim in de vault, alleen-schrijven); (b) `/connector/v1/items?type=...` en `/connector/v1/evidence/{id}` met een dienst-JWT van de Hub (bestaande functie `call` in `servicecalls.py`). Bron: CONTRACT_1.3_CONFORMITEIT.md rij C1.3-ASM-21; BOUWPLAN#10.4.
  2. Events: de Hub haalt ze op met `GET /connector/v1/events` (pollen; er is geen enrollment voor Jelly Leon). De cursor wordt bewaard; een dubbel event wordt eenmaal verwerkt.
  3. Antwoord 401 met `reason: not_linked` wordt de toestand "niet gekoppeld" (onbekend, nooit gezond); 403 voor de rol kind wordt doorgegeven; 501 `capability_unavailable` wordt "niet beschikbaar". De adapter roept nooit `propose`, `apply` of `rollback` aan.
  4. Witte lijst op itemtypen (`watch_together_stats`, `recommender_status`, `recommender_evaluation`, `subtitle_coverage`, `subtitle_translation`, `quality_summary`, `quality_finding`, `device`, `playback_stats`, `gpu_lane`, `segment_coverage`, `segment_review`, `backups`) en op velden: een onbekend veld wordt weggelaten; een veld dat op een titel, pad, naam of adres lijkt wordt geweigerd en als fout gemeld.
  5. Scherm Diensten (`DienstenScreen.tsx`): de bestaande blokken voor vingerafdruk en publieke sleutelset (functie met commentaar "C-57") uitbreiden met een stap met de titel "Jelly Leon-plugin": sleutelset kopieren, vingerafdruk tonen en het `service_id` uit het register. Bestaand onderdeel `KopieerVeld.tsx` gebruiken. A-ONTWERP levert eerst het ontwerp van dit blok.
  6. Versheid volgens de basis van S-P3-020 (verouderd wordt onbekend).
  7. `make openapi`, daarna `make openapi-check`; unit- en integratietests; e2e-test in `apps/web/e2e` (nieuw bestand met een nummer tussen 10 en 90).
  8. EVIDENCE en de statusregel van C1.3-ASM-21.
- **Tests (verplicht):** T-HUB-API en T-HUB-WEB. De plugin wordt in de tests nagebootst met een nepserver in de testmap (geen echte Jelly Leon nodig). Negatief: (a) nepserver geeft 401 `not_linked`: toestand "niet gekoppeld", niet gezond; (b) een item met een veld `title` of `path` wordt geweigerd en komt niet in de database of het antwoord; (c) het token van de niet-beheerder-gebruiker komt in geen antwoord, logregel of auditregel voor (zoek op de exacte testwaarde); (d) een gewone gebruiker krijgt 403 op koppelen en ontkoppelen; (e) de adapter doet geen enkel verzoek met een andere methode dan GET (de nepserver telt de methoden); (f) een basisadres dat de uitgaande controle van `outbound.py` weigert wordt niet aangeroepen.
- **Poort:** P-ai-server-manager (snel en volledig) + P-VEILIG + P-CONTRACT + P-PEIL (alleen voor het blok op het scherm Diensten).
- **Valkuilen:** V-001, V-003, V-043, V-047, V-048, V-051, V-054, V-061, V-066, V-092, V-094, V-120.
- **Bewijs:** C1.3-ASM-21 blijft "Bezig" (validatie "Unit-getest" of "Sim-getest"; "tegen een echte Jelly Leon op de NAS NIET GEVALIDEERD (NAS)").
- **Agents:** A-VERKEN -> A-ONTWERP (alleen het blok op het scherm Diensten) -> A-BOUW -> R-TECH + R-VEILIG (tegelijk; R-VEILIG VERPLICHT: geheim van de Jellyfin-gebruiker, dienst-JWT, veldenwitte lijst) -> A-HERSTEL -> R-ONTWERP (VERPLICHT) -> R-EERLIJK
- **Niveau:** A-BOUW N4 en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4 (de kern van ondertekening en sleutels verandert niet: de stap gebruikt de bestaande functies; wordt `keys.py` of `servicecalls.py` toch gewijzigd, dan stopt de stap en beslist de regisseur over R-VEILIG N5, met "Winst: ..."); overige standaard
- **Stop en vraag als:** het ADR van S-P3-010 de vorm van de adapter openlaat; de plugin een andere vorm van de sleutelset verwacht dan het scherm Diensten levert (dan eerst vaststellen met de pluginpagina van golf 1 en melden); `keys.py` of `servicecalls.py` gewijzigd moet worden.

### S-G4-32 - Hub: kaartbasis voor Jelly Leon op het scherm Media en de eventtypes in de incidenten
- **Repo:** ai-server-manager | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (`make web-build`, `make web-e2e`, `make web-review`: na elkaar)
- **Werkpakketten en tests:** repowerk Δ-HUB-2 (CONTRACT_1.3_CONFORMITEIT.md, vervolgpunten ai-server-manager; Moment P4); basis voor B03-029, B03-039, B03-058, B03-069, B03-078
- **Vooraf:** S-G4-31; S-P3-080 (scherm Media) en S-P3-075 (incidentketen).
- **Al gedaan?** `grep -n "media" <WERKMAP>/ai-server-manager/apps/web/src/lib/nav.ts` -> staat `media` nog in `PLANNED` = S-P3-080 is niet klaar: STOP. `grep -rn "watchgroup\|media.storage.read_failed" <WERKMAP>/ai-server-manager/apps/api/src/hub/incidents -l` -> geen uitvoer = de eventtypes ontbreken.
- **Lees eerst:** BOUWPLAN#10.10 Events; BOUWPLAN#10.4 Hub-koppeling (JL4); `<WERKMAP>/ai-server-manager/design/ontwerptaal/COMPONENTEN.md` (StatKaart C-05, StatusBadge C-03, Versheid C-06, Validatielabel C-09, CapabilityUnavailable C-12); `<WERKMAP>/ai-server-manager/docs/ontwerp/HUB_PEIL_ONTWERP.md`; `<WERKMAP>/ai-server-manager/apps/web/src/app/media/page.tsx`
- **Bouw:**
  1. A-ONTWERP eerst: een sectie "Jelly Leon" op het scherm Media met plaats voor vijf kaarten, in de toestanden niet gekoppeld, onbekend, laden, fout, verouderd en gevuld, op 360, 390, 768 en 1440 px, licht en donker.
  2. Een gedeeld kaartonderdeel voor Jelly Leon-kaarten op basis van de bestaande onderdelen (`StatCard.tsx`, `StatusBadge.tsx`, `Freshness.tsx`, `NotYetAvailable.tsx`, `ErrorPanel.tsx`, `Loading.tsx`): waarde, eenheid, bron, laatst bijgewerkt en het validatielabel. Onbekend is grijs en nooit groen.
  3. Leesroute(s) in de Hub-API die de items van de adapter per itemtype teruggeven (in het routerbestand van de adapterbasis); `make openapi` en `make openapi-check`.
  4. Eventtypes uit BOUWPLAN#10.10 opnemen in de incidentregels (`apps/api/src/hub/incidents/rules.py`) met de ernst uit het bouwplan (de definitie per functie staat in de hoofdstukken Fx.5, bijvoorbeeld BOUWPLAN#F6.5.5 Events); een onbekend type wordt bewaard als "onbekend type" en maakt geen incident.
  5. De sectie is verborgen in de kinderschil (bestaande onderdelen `KindScreens.tsx` en `KindSection.tsx` volgen).
  6. Het deel "Jelly Leon" van het scherm Media is niet langer "gepland"; zonder koppeling verwijst het naar het scherm Diensten.
  7. Componenttests, e2e-test (nieuw bestand met een nummer tussen 10 en 90) en de Peil-review (`make web-review`).
- **Tests (verplicht):** T-HUB-API en T-HUB-WEB. Negatief: (a) adapter "niet gekoppeld" of onbekend: de sectie toont "Onbekend" en geen groene status; (b) een kind ziet de sectie niet en de leesroute geeft 403; (c) een event met een onbekend type maakt geen incident; (d) een event met een veld dat niet in het schema staat wordt geweigerd; (e) een meting ouder dan de grens is "verouderd", niet actueel.
- **Poort:** P-ai-server-manager (snel en volledig) + P-PEIL + P-CONTRACT + P-VEILIG.
- **Valkuilen:** V-051, V-058, V-061, V-062, V-063, V-079.
- **Bewijs:** de voortgang van Δ-HUB-2 in de statusregel van C1.3-ASM-21 ("Bezig", Sim-getest). Geen B03-rij wordt door deze stap alleen bijgewerkt.
- **Agents:** A-VERKEN -> A-ONTWERP -> A-BOUW -> R-TECH + R-VEILIG (tegelijk; R-VEILIG VERPLICHT: nieuwe leesroute in de Hub-API met rolcontrole voor de kinderschil, en eventinvoer van een andere dienst in de incidentregels) -> A-HERSTEL -> R-ONTWERP (VERPLICHT) -> R-EERLIJK
- **Niveau:** standaard; R-VEILIG N4
- **Stop en vraag als:** de ernst van een eventtype niet in het bouwplan staat (niet zelf kiezen: melden); het ontwerp een actieknop richting Jelly Leon of MediaGuard nodig lijkt te hebben (in deze golf zijn er alleen deeplinks).

### S-G4-33 - Hub-kaart "Watch Together"
- **Repo:** ai-server-manager | **Fase:** P4 (golf 4) | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** ja (`make web-build`, `make web-e2e`, `make web-review`: na elkaar)
- **Werkpakketten en tests:** B03-029 (deel Hub-kaart); geen JLT-rij noemt deze kaart apart: het bewijs komt bij B03-029
- **Vooraf:** S-G4-32; S-G4-11 (itemtype `watch_together_stats` en de events in de plugin).
- **Al gedaan?** `grep -rn "Watch Together" <WERKMAP>/ai-server-manager/apps/web/src -l` -> geen uitvoer = niet gestart.
- **Lees eerst:** BOUWPLAN#F1.6.3 Hub; WP-JSON object B03-029; het ontwerp en het kaartonderdeel van S-G4-32; `<WERKMAP>/ai-server-manager/design/ontwerptaal/COMPONENTEN.md` (StatKaart C-05, Versheid C-06); `<WERKMAP>/ai-server-manager/apps/web/src/app/media/page.tsx`
- **Bouw:**
  1. A-ONTWERP eerst: de kaart in alle toestanden (vers, onbekend, niet beschikbaar, leeg, fout, laden) op 360, 390, 768 en 1440 px, licht en donker.
  2. Kaart "Watch Together" in de sectie Jelly Leon: actieve groepen, deelnemers (waarvan volgers), via VPN of van buiten, transcoderend, synchronisatie p95 over 24 uur; bij elke waarde eenheid, bron "Jelly Leon-plugin" en laatst bijgewerkt. Bron: BOUWPLAN#F1.6.3.
  3. Leeg: "Nu geen Watch Together-groepen". Onbekend en niet gekoppeld: grijs, nooit groen.
  4. Link "Openen in Jelly Leon" (deeplink; geen actie in de Hub).
  5. Het event `media.watchgroup.degraded` verschijnt in de incidentinbox (regel van S-G4-32); de kaart verwijst ernaar.
  6. Componenttest, e2e-test en Peil-review.
- **Tests (verplicht):** T-HUB-WEB (en T-HUB-API als de leesroute wijzigt). Negatief: (a) onbekend of niet gekoppeld is nooit groen; (b) een kind ziet de kaart niet; (c) een antwoord met een naam, titel of adres in een veld toont dat veld niet (de adapter weigert het; de kaart toont "fout"); (d) een verouderde meting toont "verouderd" met het tijdstip.
- **Poort:** P-ai-server-manager + P-PEIL.
- **Valkuilen:** V-051, V-058, V-061, V-062, V-063.
- **Bewijs:** B03-029 -> Bezig (Sim-getest; "kaart met nagebootste plugin; tegen de echte NAS NIET GEVALIDEERD (NAS)").
- **Agents:** A-VERKEN -> A-ONTWERP -> A-BOUW -> R-TECH -> A-HERSTEL -> R-ONTWERP (VERPLICHT) -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** het itemtype in de plugin andere velden levert dan het bouwplan noemt (verschil melden; niet zelf velden verzinnen).

### S-G4-34 - Hub-kaart "Aanbevelingen · Jelly Leon" en het detailscherm
- **Repo:** ai-server-manager | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (`make web-build`, `make web-e2e`, `make web-review`: na elkaar)
- **Werkpakketten en tests:** B03-039 (deel Hub-kaart H-1 en detail H-2); geen JLT-rij noemt deze kaart apart
- **Vooraf:** S-G4-32; S-G4-12 (itemtypen `recommender_status` en `recommender_evaluation`).
- **Al gedaan?** `grep -rn "Aanbevelingen" <WERKMAP>/ai-server-manager/apps/web/src/app/media -l` -> geen uitvoer = niet gestart.
- **Lees eerst:** BOUWPLAN#F2.6.4 Hub; WP-JSON object B03-039; het ontwerp en het kaartonderdeel van S-G4-32; `<WERKMAP>/ai-server-manager/design/ontwerptaal/COMPONENTEN.md` (Validatielabel C-09, CapabilityUnavailable C-12, Grafiek C-32, DekkingsMatrix C-33); `<WERKMAP>/ai-server-manager/apps/web/src/components/LineChart.tsx`
- **Bouw:**
  1. A-ONTWERP eerst: kaart H-1 en detail H-2 in alle toestanden en op de vier breedtes, licht en donker.
  2. Kaart H-1: items in het model, laatste herberekening, bibliotheken zonder volgorde, embeddings "Uit" of "Aan" met de bron, laatste offline-evaluatie (NDCG@10) met het validatielabel. Bron: BOUWPLAN#F2.6.4.
  3. Antwoord 401 `not_linked`: toestand "niet gekoppeld" (StatusBadge), nooit groen. Een niet-gepinde sleutel: CapabilityUnavailable.
  4. Detail H-2 "Media → Aanbevelingen": evaluatiehistorie als grafiek, redencodes, back-updekking als dekkingsmatrix, deeplink naar Jelly Leon. Geen acties.
  5. Geen gegevens per gebruiker, geen titels en geen bibliotheeknamen op kaart of detail.
  6. Verborgen in de kinderschil.
  7. Componenttests, e2e-test en Peil-review.
- **Tests (verplicht):** T-HUB-WEB (en T-HUB-API als de leesroute wijzigt). Negatief: (a) geen evaluatie beschikbaar: "onbekend", geen nul en geen groen; (b) een kind ziet kaart en detail niet (de route geeft 403); (c) een bibliotheeknaam in het antwoord wordt niet getoond; (d) de evaluatiewaarde draagt altijd het validatielabel, nooit een kale waarde.
- **Poort:** P-ai-server-manager + P-PEIL.
- **Valkuilen:** V-051, V-058, V-061, V-062, V-063.
- **Bewijs:** B03-039 -> Bezig (Sim-getest; "kaart met nagebootste plugin; de evaluatie op echte kijkgeschiedenis valt onder BG-37 en JLT-15 en is NIET GEVALIDEERD").
- **Agents:** A-VERKEN -> A-ONTWERP -> A-BOUW -> R-TECH -> A-HERSTEL -> R-ONTWERP (VERPLICHT) -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** de grafiek een nieuw Peil-onderdeel vraagt dat niet in COMPONENTEN.md staat (dan beslist A-ONTWERP binnen Peil; een nieuw onderdeel buiten Peil is een vraag voor de regisseur).

### S-G4-36 - Hub-kaart "Mediakwaliteit" met problemen-inbox en bewijs
- **Repo:** ai-server-manager | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (`make web-build`, `make web-e2e`, `make web-review`: na elkaar)
- **Werkpakketten en tests:** B03-058 (deel Hub: kaart, incidenten, bewijs); JLT-38 (deel Hub-UI)
- **Vooraf:** S-G4-32; S-G4-14 (itemtypen `quality_summary` en `quality_finding`, bewijsroute, health-checks).
- **Al gedaan?** `grep -rn "Mediakwaliteit" <WERKMAP>/ai-server-manager/apps/web/src -l` -> geen uitvoer = niet gestart.
- **Lees eerst:** BOUWPLAN#F4.6.3 Hub-UI; WP-JSON object B03-058; TEST-JSON rij JLT-38; `<WERKMAP>/ai-server-manager/design/ontwerptaal/COMPONENTEN.md` (IncidentRij C-25, BewijsPaneel C-28, CapabilityUnavailable C-12); `<WERKMAP>/ai-server-manager/apps/web/src/lib/incidents.ts`
- **Bouw:**
  1. A-ONTWERP eerst: H1 (kaart), H2 (problemen-inbox) en H3 (herstel) in alle toestanden en op de vier breedtes, licht en donker.
  2. H1, kaart "Mediakwaliteit": aantal open problemen met het aantal "hoog", bron "Jelly Leon · kwaliteitscontrole", laatst bijgewerkt, dekking en validatielabel; knop "Bekijk problemen". Bron: BOUWPLAN#F4.6.3.
  3. Toestand Onbekend met de tekst "Hub-toegang tot Jelly Leon nog niet ingesteld (pin ontbreekt)"; toestand Verouderd; toestand Leeg.
  4. H2, problemen-inbox: rijen voor ernst "hoog" en voor `media.storage.read_failed`, met ernst- en zekerheidslabel en een bewijspaneel (alleen meetwaarden, tijdvensters en detector; geen beeld, geen logfragment); link "Open in Jelly Leon".
  5. Een fout toont het trace-id.
  6. H3, herstel: CapabilityUnavailable met de tekst "Herstel via de Hub is nog niet toegestaan door het platformcontract. Doe het in MediaGuard." en een deeplink. Geen knop die iets uitvoert.
  7. Verborgen voor een kind; componenttests, e2e-test en Peil-review.
- **Tests (verplicht):** T-HUB-WEB (en T-HUB-API als de leesroute wijzigt). Negatief: (a) zonder pin: "Onbekend", nooit groen en nooit "0 problemen"; (b) een kind ziet niets (403 op de route); (c) het bewijspaneel toont geen titel, bestandsnaam, pad of beeld, ook niet als de nepserver die meestuurt; (d) er bestaat geen verzoek vanuit H3 naar MediaGuard of naar een schrijvende route (de e2e-test telt de verzoeken).
- **Poort:** P-ai-server-manager + P-PEIL + P-CONTRACT.
- **Valkuilen:** V-051, V-058, V-061, V-062, V-063, V-079.
- **Bewijs:** B03-058 -> Bezig (Sim-getest; "Hub-uitvoering via MediaGuard: Geblokkeerd (contract) tot Δ-CONTRACT-MG"). JLT-38 -> Bezig met "deel Hub-UI".
- **Agents:** A-VERKEN -> A-ONTWERP -> A-BOUW -> R-TECH -> A-HERSTEL -> R-ONTWERP (VERPLICHT) -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** het ontwerp een herstelknop lijkt te vragen (wacht op BG-05 en Δ-CONTRACT-MG; niet bouwen).

### S-G4-37 - Hub-kaarten "Jelly Leon · Afspelen" en "GPU-banen" en het scherm "Apparaten (Jelly Leon)"
- **Repo:** ai-server-manager | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (`make web-build`, `make web-e2e`, `make web-review`: na elkaar)
- **Werkpakketten en tests:** B03-069 (deel Hub-weergave); JLT-48 (deel Hub: geen uitsplitsing per apparaat)
- **Vooraf:** S-G4-32; S-G4-18 (itemtypen `device`, `playback_stats`, `gpu_lane`).
- **Al gedaan?** `grep -rn "GPU-banen" <WERKMAP>/ai-server-manager/apps/web/src -l` -> geen uitvoer = niet gestart.
- **Lees eerst:** BOUWPLAN#F5.6.3 Hub; WP-JSON object B03-069; het ontwerp en het kaartonderdeel van S-G4-32; `<WERKMAP>/ai-server-manager/design/ontwerptaal/COMPONENTEN.md` (StatKaart C-05, Leeg/Onbekend/Laden/Offline C-16 tot en met C-18); `<WERKMAP>/ai-server-manager/apps/web/src/components/ResponsiveList.tsx`
- **Bouw:**
  1. A-ONTWERP eerst: H1, H2 en H3 in alle toestanden en op de vier breedtes, licht en donker.
  2. H1, kaart "Jelly Leon · Afspelen": Direct Play-ratio over 7 dagen, mislukte starts over 7 dagen, actieve transcodes, aandeel hardware, momenten "GPU's vol" over 7 dagen. Leeg: "Nog geen afspeelgegevens". Onbekend: "Jelly Leon nog niet gekoppeld". Bron: BOUWPLAN#F5.6.3.
  3. H2, kaart "GPU-banen (Jelly Leon)": per nodeklasse de bezetting met het label gemeten of ongemeten; de bezetting door MediaGuard als gelezen waarde, of "MediaGuard: onbekend".
  4. H3, scherm "Apparaten (Jelly Leon)": alleen lezen, per apparaatklasse en rol; ondoorzichtige ID's; de deeplink naar Jelly Leon alleen voor beheerders.
  5. Aanraakdoelen minstens 44 px; geen apparaatnaam en geen gebruikersnaam op enig scherm.
  6. Verborgen voor een kind; componenttests, e2e-test en Peil-review.
- **Tests (verplicht):** T-HUB-WEB (en T-HUB-API als de leesroute wijzigt). Negatief: (a) niet gekoppeld of onbekend is nooit groen; (b) een kind ziet niets; (c) de adapter vraagt nooit een uitsplitsing per apparaat aan en een nepantwoord 403 daarop toont "fout", niet leeg; (d) een ongemeten baan wordt niet als gemeten getoond; (e) een gewone gebruiker ziet geen deeplink op H3.
- **Poort:** P-ai-server-manager + P-PEIL.
- **Valkuilen:** V-051, V-058, V-061, V-062, V-063.
- **Bewijs:** B03-069 -> Bezig (Sim-getest; "GPU-waarden met echte hardware NIET GEVALIDEERD (hardware)"). JLT-48 -> bijwerken met "deel Hub".
- **Agents:** A-VERKEN -> A-ONTWERP -> A-BOUW -> R-TECH -> A-HERSTEL -> R-ONTWERP (VERPLICHT) -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** het scherm Apparaten een eigen navigatiepunt nodig heeft (dat is een keuze in `apps/web/src/lib/nav.ts` voor de regisseur).

### S-G4-38 - Hub-kaart "Intro en aftiteling (Jelly Leon)"
- **Repo:** ai-server-manager | **Fase:** P4 (golf 4) | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** ja (`make web-build`, `make web-e2e`, `make web-review`: na elkaar)
- **Werkpakketten en tests:** B03-078 (deel Hub-kaart); JLT-58 (deel Hub: items en health zonder pin)
- **Vooraf:** S-G4-32; S-G4-17 (itemtypen `segment_coverage` en `segment_review`, health-check `segments`).
- **Al gedaan?** `grep -rn "Intro en aftiteling" <WERKMAP>/ai-server-manager/apps/web/src -l` -> geen uitvoer = niet gestart.
- **Lees eerst:** BOUWPLAN#F6.6.4 Hub-kaart; WP-JSON object B03-078; TEST-JSON rij JLT-58; het ontwerp en het kaartonderdeel van S-G4-32; `<WERKMAP>/ai-server-manager/design/ontwerptaal/COMPONENTEN.md` (StatKaart C-05)
- **Bouw:**
  1. A-ONTWERP eerst: de kaart in de toestanden leeg (module uit), laden, fout, onbekend en geen rechten (kind), op de vier breedtes, licht en donker.
  2. Kaart "Intro en aftiteling (Jelly Leon)": dekking in procenten, open reviewitems, achterstand met de schatting, laatste analyse en de status; bron "Jelly Leon connector" en laatst bijgewerkt. Bron: BOUWPLAN#F6.6.4.
  3. Knop "Beoordelen in Jelly Leon" (deeplink; geen actie in de Hub).
  4. Alleen aantallen: geen titels, geen afleveringsnamen.
  5. De schatting van de achterstand draagt het label "geschat".
  6. Componenttest, e2e-test en Peil-review.
- **Tests (verplicht):** T-HUB-WEB (en T-HUB-API als de leesroute wijzigt). Negatief: (a) module uit: "leeg (module uit)", niet "0 % dekking" als meting; (b) zonder pin: onbekend, nooit groen; (c) een kind ziet de kaart niet; (d) de schatting wordt nooit als gemeten getoond.
- **Poort:** P-ai-server-manager + P-PEIL.
- **Valkuilen:** V-051, V-058, V-061, V-062, V-063.
- **Bewijs:** B03-078 -> Bezig (Sim-getest; "kaart met nagebootste plugin"). JLT-58 -> bijwerken met "deel Hub".
- **Agents:** A-VERKEN -> A-ONTWERP -> A-BOUW -> R-TECH -> A-HERSTEL -> R-ONTWERP (VERPLICHT) -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** de plugin de achterstand zonder schatting levert (dan het veld weglaten en dat melden; niet zelf schatten).

### S-G4-35 - Hub: alle Jelly Leon-kaarten samen, kinderschil en afsluitende ontwerpreview
- **Repo:** ai-server-manager | **Fase:** P4 (golf 4) | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** ja (`make web-build`, `make web-e2e`, `make web-review`: na elkaar)
- **Werkpakketten en tests:** afronding Hub-deel van B03-029, B03-039, B03-058, B03-069, B03-078; Δ-HUB-2; JLT-38 (deel Hub-UI, alle breedtes)
- **Vooraf:** S-G4-33, S-G4-34, S-G4-36, S-G4-37, S-G4-38. De Hub-kaart voor ondertitels hoort bij P5 (STAPPEN_P5.md) en ontbreekt hier met opzet.
- **Al gedaan?** `ls <WERKMAP>/ai-server-manager/apps/web/e2e` -> staat er geen test die alle Jelly Leon-kaarten samen opent = niet gestart (de naam van die test kiest de bouwer; zoek met `grep -ln "Jelly Leon" <WERKMAP>/ai-server-manager/apps/web/e2e/*.spec.ts`).
- **Lees eerst:** de ontwerpen van S-G4-32 tot en met S-G4-38; `<WERKMAP>/ai-server-manager/docs/ontwerp/HUB_PEIL_ONTWERP.md`; `<WERKMAP>/ai-server-manager/apps/web/review/README.md`; `<WERKMAP>/ai-server-manager/apps/web/src/app/KindScreens.tsx`; POORTEN.md blok P-PEIL
- **Bouw:**
  1. A-ONTWERP eerst: de sectie Jelly Leon met alle kaarten samen beoordelen op volgorde, dichtheid en lege ruimte op 360, 390, 768 en 1440 px, licht en donker; alleen bijsturen, geen nieuwe kaarten.
  2. Een e2e-test die het scherm Media met alle kaarten opent in drie standen van de nepserver: gekoppeld en gevuld, niet gekoppeld, en plugin onbereikbaar.
  3. Kinderschil: een test die als kind inlogt en vaststelt dat geen enkele Jelly Leon-kaart, link of route bereikbaar is.
  4. Een schemacontrole over alle antwoorden van de leesroutes: geen titel, bestandsnaam, pad, gebruikers- of apparaatnaam, adres of beeld.
  5. De Peil-review (`make web-review`) over het hele scherm; bevindingen herstellen.
  6. De statusregel van Δ-HUB-2 en C1.3-ASM-21 bijwerken; EVIDENCE.
- **Tests (verplicht):** T-HUB-WEB en T-HUB-API. Negatief: (a) plugin onbereikbaar: alle kaarten "onbekend" of "fout", geen enkele groen; (b) een kind bereikt geen route (403) en ziet geen sectie; (c) de schemacontrole faalt als de nepserver een veld `title` meestuurt en de adapter het zou doorlaten (eenmaal aantonen met een opzettelijk fout nepantwoord); (d) toetsenbord: elke kaart en link is met Tab bereikbaar en heeft een zichtbare focus.
- **Poort:** P-ai-server-manager (volledig) + P-PEIL + P-CONTRACT + P-VEILIG.
- **Valkuilen:** V-051, V-058, V-061, V-062, V-063, V-079.
- **Bewijs:** de Hub-delen van B03-029, B03-039, B03-058, B03-069 en B03-078 blijven "Bezig" (Sim-getest; "Hub tegen de echte NAS NIET GEVALIDEERD (NAS)"). JLT-38 -> "deel Hub-UI, vier breedtes, licht en donker".
- **Agents:** A-VERKEN -> A-ONTWERP -> A-BOUW -> R-TECH -> A-HERSTEL -> R-ONTWERP (VERPLICHT) -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** de ontwerpreview een wijziging aan Peil zelf vraagt (tokens of onderdelen in `design/ontwerptaal`): dat is een besluit voor de regisseur en de gebruiker.

### S-G4-39 - Compat-regressie per oplevering en het clientmatrixdocument (herhaalstap golf 4)
Deze stap draait meer dan eens: na S-G4-07, na S-G4-09, na S-G4-14, na S-G4-19, na S-G4-42 en S-G4-44, na S-G4-49, S-G4-51 en S-G4-53, en na de laatste web- en clientstap. Elke run krijgt een eigen rapport.
- **Repo:** jelly-leon | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (image-build achter docker-build.lock; proeven achter stack.lock)
- **Werkpakketten en tests:** B03-029 (deel clientmatrixdocument), B03-037 (webrijen), B03-068 (deel regressie); JLT-63, JLT-64, JLT-65 (per oplevering); JLT-09, JLT-48 (deel terug naar stock); JLT-14, JLT-25, JLT-38, JLT-55 (webrijen: drie browsers, UA-simulatie, stock-web)
- **Vooraf:** de stap waarna de run is gepland; een lokale image van de actuele stand. De werkwijze is die van S-G3-27.
- **Al gedaan?** `grep -ci "volgmodus" <WERKMAP>/jelly-leon/docs/platform-v2/CLIENT_COMPAT_MATRIX.md` -> 0 = de kolommen van Watch Together ontbreken nog in het bestaande document. `git -C <WERKMAP>/jelly-leon log --oneline -5 -- docs/platform-v2/EVIDENCE.json` -> staat de run van deze oplevering er al = deze run is gedaan.
- **Lees eerst:** stap S-G3-27 in dit bestand (zelfde werkwijze); TEST-JSON rijen JLT-63, JLT-64 en JLT-65; BOUWPLAN#F1.9.5 Negatief en veiligheid; BOUWPLAN#F5.9.4 Clientmatrix; `<WERKMAP>/jelly-leon/tools/b03-harnas/README.md`
- **Bouw:**
  1. Lokale image bouwen (T-JL-IMAGE) en de compat-proef draaien (T-JL-COMPAT) met de toegestane-verschillenlijst van de opgeleverde module en de negatieve proef, precies zoals in S-G3-27.
  2. Webrijen van de clientmatrix: `PYTHONPATH=tools/b03-harnas python -m b03h clientmatrix --onderdelen web,ua,webdir --image <lokale-tag> --uit <rapport.json>` (drie browsers, UA-simulatie voor tv's, stock-web uit de stock-image tegen de Jelly Leon-server).
  3. Terug naar stock: plugin aan, uitgeschakeld, verwijderd en daarna de stock-image op dezelfde gegevens; de kijkgegevens van de testgebruikers zijn voor en na gelijk.
  4. `docs/platform-v2/CLIENT_COMPAT_MATRIX.md` bijwerken: per client en per rol de kolommen SyncPlay, volgmodus en uitnodigingsmelding, en per functie van golf 4 de uitkomst met het label (Sim-getest, NIET GEVALIDEERD (Mac/Xcode), NIET GEVALIDEERD (hardware)). De emulatorrijen komen uit de rapporten van S-G4-29 en S-G4-30.
  5. EVIDENCE bijwerken: per run een regel met het rapportpad.
- **Tests (verplicht):** T-JL-IMAGE; T-JL-COMPAT (met `--image-a <stock-12.x-image> --image-b <lokale-tag>`, `--toegestaan` en `--negatieve-proef`); het clientmatrixcommando uit punt 2. Negatief: (a) de negatieve proef van het harnas moet een opzettelijk verschil vinden; vindt hij niets, dan is de run ongeldig; (b) een verschil buiten de toegestane lijst laat de run falen en wordt niet aan de lijst toegevoegd zonder bron in het bouwplan; (c) na "terug naar stock" is er geen enkel verschil in gezien, hervatpunten, favorieten en spoorkeuzes.
- **Poort:** P-jelly-leon (volledig, CI-volgorde) + P-HARDE-EIS.
- **Valkuilen:** V-009, V-011, V-027, V-077, V-088, V-111.
- **Bewijs:** JLT-63, JLT-64, JLT-65 -> Bezig (Sim-getest; per oplevering het rapportpad). JLT-09 en JLT-48 -> bijwerken met "deel terug naar stock". "Safari NIET GEVALIDEERD (Mac/Xcode); echte tv's NIET GEVALIDEERD (hardware); upgrade op de echte NAS NIET GEVALIDEERD (NAS)."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> R-HARDE-EIS (VERPLICHT: kijkgegevens voor en na gelijk; terug naar stock) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard; R-HARDE-EIS N4; A-BOUW N2 mag bij de tweede en latere run als er geen code verandert
- **Stop en vraag als:** een kijkgegeven na een run verschilt (alles stilleggen in jelly-leon en melden); de toegestane lijst moet groeien zonder dat het bouwplan het verschil noemt.

### S-G4-47 - Winstmeting apparaatprofielen tegen standaard Jellyfin (JLT-40)
Dit nummer is later toegevoegd (bij de controle van 2026-11-11); in de volgorde hoort de stap na S-G4-22, S-G4-41 en S-G4-07 en voor de laatste run van S-G4-39 (zie de tabel in 6.2).
- **Repo:** jelly-leon | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (meting in het exclusieve meetslot achter stack.lock; image-build achter docker-build.lock)
- **Werkpakketten en tests:** JLT-40 (winstmeting F5; webdeel volgens BOUWPLAN#F5.8 Bouwfasen, regel F5-S5); B03-065, B03-066 (bewijs bijwerken)
- **Vooraf:** S-G4-07, S-G4-22 en S-G4-41 klaar; S-P40-64 klaar (STAPPEN_P4_GOLF1_2.md): het meetharnas van B03-060 met de bevroren gecontroleerde-foutenset en, uit bouwpunt 6, het meetcommando voor JLT-40 onder een eigen kop in `tools/b03-harnas/README.md`. Geen besluit nodig; BG-26 bepaalt alleen welke rollen advies krijgen.
- **Al gedaan?** `grep -n '"id": "JLT-40"' <WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json` -> geen uitvoer = niet gestart; staat er een regel, lees dan of het rapportpad een commit noemt die gelijk is aan `git -C <WERKMAP>/jelly-leon log -1 --format=%h -- plugins` (anders opnieuw meten). `grep -n "JLT-40" <WERKMAP>/jelly-leon/tools/b03-harnas/README.md` -> geen uitvoer = bouwpunt 6 van S-P40-64 is niet gedaan: STOP (het recept `b03h/corpus/r_f5_fouten.py` bestond al op 2026-11-11 en bewijst dus niets).
- **Lees eerst:** TEST-JSON rij JLT-40; BOUWPLAN#F5.8 Bouwfasen (regels F5-S5 en F5-S6); de metriektabel K1 tot en met K9 in BOUWPLAN hoofdstuk F5 (zoek met `grep -n "Onterechte Direct Play" <WERKMAP>/ai-server-manager/docs/platform-v2/02_BOUWPLANNEN/B03_UNIVERSELE_MEDIASERVER.md`); FASERING#Gates per functie; `<WERKMAP>/jelly-leon/tools/b03-harnas/README.md`
- **Bouw:**
  1. Bouw de image van de actuele stand (T-JL-IMAGE) met de modules Devices aan.
  2. Draai de meting van TEST-JSON rij JLT-40 (opzet en verwacht letterlijk uit die rij) in het exclusieve meetslot: minstens 3 runs, stock en Jelly Leon afwisselend, loadavg per run; drie browsers en de Tizen- en webOS-UA-simulatie. Het commando: precies het commando onder de kop voor JLT-40 in `<WERKMAP>/jelly-leon/tools/b03-harnas/README.md` (vastgelegd door S-P40-64, bouwpunt 6: subcommando van `b03h`, opties, bevroren set en uitvoer); niet zelf samenstellen. Op 2026-11-11 stond het er nog niet (alleen de algemene regel `b03h baseline --metingen dp,orakel,transcode,functies --runs 3`); ontbreekt het, dan STOP.
  3. Vergelijk per client met baseline (a) stock-standaard en (b) stock-best op dezelfde 12.x-digest; noem n en het Wilson-interval. De drempels en de testset worden niet aangepast.
  4. Emulator- en desktopdelen niet zelf meten: neem de uitkomst van S-G4-30 over met verwijzing.
  5. Rapport onder `docs/platform-v2/test-evidence/` en EVIDENCE.
- **Tests (verplicht):** T-JL-HARNAS; de meting uit bouwpunt 2. Negatief: (a) een bestand uit de foutenset met een liegende codec verschijnt als "onterechte Direct Play" bij de eerste start en NIET bij de tweede; verschijnt het nooit, dan meet het orakel niet en is de run ongeldig; (b) officiele apps zonder opt-in geven dezelfde beslissingen als stock; (c) een run boven de lastgrens van het meetslot (loadavg(1 min) > 4 of andere processen > 4 kernen; BOUWPLAN#F5.1.3 Metrieken en drempels en `LASTGRENS` in `tools/b03-harnas/b03h/meetslot.py`) telt als ongeldig en wordt in het rapport genoemd.
- **Poort:** P-jelly-leon (job `b03-harnas`; image proeven).
- **Valkuilen:** V-005, V-006, V-009, V-032, V-098.
- **Bewijs:** JLT-40 -> Bezig (Sim-geslaagd of Sim-mislukt met de gemeten waarden, n en het aantal geldige runs; "aantoonbaar beter" alleen als alle drempels tegen stock-best gehaald zijn, anders "smoke-gate"). "Echte tv's en echte GPU's: NIET GEVALIDEERD (hardware); zie STAPPEN_P6.md."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK (R-EERLIJK VERPLICHT: controleert dat geen winst wordt geclaimd die de meting niet draagt)
- **Niveau:** standaard
- **Stop en vraag als:** het meetharnas van B03-060, de bevroren foutenset of het vastgelegde JLT-40-commando in het README ontbreekt; een drempel niet gehaald wordt (melden met de waarden; niets aanpassen); het meetslot drie keer achter elkaar ongeldig is door belasting.

### S-G4-48 - Winstmeting segmenten tegen standaard Jellyfin en Intro Skipper (JLT-50)
Dit nummer is later toegevoegd (bij de controle van 2026-11-11); in de volgorde hoort de stap na S-G4-16 en S-G4-40 en voor de laatste run van S-G4-39 (zie de tabel in 6.2).
- **Repo:** jelly-leon | **Fase:** P4 (golf 4) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (meting op de bevroren testset achter stack.lock; image-build achter docker-build.lock)
- **Werkpakketten en tests:** JLT-50 (winstmeting F6, herhaling na golf 4; de eerste meting is van golf 2: S-G2-42 voor Intro, Recap en Preview, S-G2-44 voor Outro); B03-007 (acceptatie, deel winst); B03-070 (alleen het bewijs bijwerken)
- **Vooraf:** S-G4-16 en S-G4-40 klaar; de bevroren testset, het evaluatieharnas en het meetcommando voor JLT-50 in `tools/b03-harnas/README.md` (STAPPEN_P4_GOLF1_2.md, S-P40-66 bouwpunt 6); de golf-2-meting van JLT-50 uit S-G2-42 en S-G2-44 (rapportpaden in EVIDENCE) als vergelijkingspunt. Baseline (b) met Intro Skipper alleen als BG-32 en de spike S-IS dat toelaten (zie S-P40-66); anders is dat deel "Geblokkeerd" met reden. BG-34: echte afleveringen alleen met bevestigde labels.
- **Al gedaan?** `grep -n '"id": "JLT-50"' <WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json` -> geen uitvoer = golf 2 heeft JLT-50 niet gemeten (S-G2-42, S-G2-44): STOP en melden; staat er een regel, vergelijk de commit in het nieuwste rapport met `git -C <WERKMAP>/jelly-leon log -1 --format=%h -- plugins` (gelijk en het rapport is van na S-G4-40 = klaar; anders meten). `grep -n "JLT-50" <WERKMAP>/jelly-leon/tools/b03-harnas/README.md` -> geen uitvoer = bouwpunt 6 van S-P40-66 is niet gedaan: STOP (het recept `b03h/corpus/r_f6_segmenten.py` bestond al op 2026-11-11 en bewijst dus niets).
- **Lees eerst:** TEST-JSON rij JLT-50; BOUWPLAN#F6.8 Bouwfasen (regel F6-S0: herhaling bij elke gate); BOUWPLAN#F6.1.3 Testopzet, n en statistiek; FASERING#Gates per functie; `<WERKMAP>/jelly-leon/tools/b03-harnas/README.md`
- **Bouw:**
  1. Bouw de image van de actuele stand (T-JL-IMAGE).
  2. Draai de evaluatie van TEST-JSON rij JLT-50 op de bevroren testset (nooit de devset): drie instanties op dezelfde 12.x-tag en -digest (stock standaard, stock met Intro Skipper als dat mag, Jelly Leon), per type n, precisie, recall en grensfout met Wilson-95 %-interval. Het commando: precies het commando onder de kop voor JLT-50 in `<WERKMAP>/jelly-leon/tools/b03-harnas/README.md` (vastgelegd door S-P40-66, bouwpunt 6; hetzelfde dat S-G2-42 en S-G2-44 gebruikten), met dezelfde bevroren testset (zelfde manifest-sha256 als in hun rapporten); niet zelf samenstellen. Op 2026-11-11 stond het er nog niet; ontbreekt het, dan STOP.
  3. Controleer tegelijk dat er 0 s beschermde scene binnen een gepubliceerd overslaanbaar segment valt (JLT-51 nultolerantie); een schending is een no-go.
  4. Zet de uitkomst per type naast die van golf 2 (S-G2-42, S-G2-44) en noem elke verandering; de drempels zijn die van de pre-registratie in S-P40-66 (bouwpunt 7) en worden niet verschoven.
  5. Rapport onder `docs/platform-v2/test-evidence/` en EVIDENCE.
- **Tests (verplicht):** T-JL-HARNAS; de evaluatie uit bouwpunt 2, twee runs met gelijke cijfers. Negatief: (a) een opzettelijk 10 s verschoven label laat de F1 dalen (het harnas kan falen); (b) een testset waarvan de sha256 niet overeenkomt met het manifest wordt geweigerd; (c) onder de streef-n heet de uitkomst "smoke-gate" en niet "beter".
- **Poort:** P-jelly-leon (job `b03-harnas`) + P-HARDE-EIS (geen publicatie in de gegevens van de testserver buiten de eigen provider).
- **Valkuilen:** V-005, V-006, V-032, V-098, V-112.
- **Bewijs:** JLT-50 -> Bezig (Sim-geslaagd of Sim-mislukt, met n en intervallen per type; deel Intro Skipper "Geblokkeerd (BG-32 of spike S-IS)" als dat niet mocht). Het deel met echte series: "Geblokkeerd" met "NIET GEVALIDEERD (echte NAS): bevestigde labels van echte afleveringen nodig (BG-34)". B03-007 -> bijwerken met het rapportpad.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK (R-EERLIJK VERPLICHT: controleert dat geen winst wordt geclaimd die de meting niet draagt)
- **Niveau:** standaard
- **Stop en vraag als:** de testset of het evaluatieharnas ontbreekt of niet bevroren is; een beschermde scene binnen een overslaanbaar segment valt (no-go; melden); iemand de testset na het afstemmen wil wijzigen.

### Gatecontrole golf 4 (afvinklijst voor A-GATE; wordt uitgevoerd in S-G4-95 in hoofdstuk 10, niveau N5)

Gate golf 4 is het einde van P4 op de ontwikkelmachine. Daarom loopt deze lijst niet als losse controle maar als deel van de ene A-GATE-run van hoofdstuk 10. A-GATE leest en controleert; hij bouwt en herstelt niet. Elk punt krijgt "ja", "nee" of "niet vast te stellen" met het commando of het bestand waarop het oordeel rust.

- [ ] Geen enkele regel in een EVIDENCE.json van jelly-leon, jelly-leon-web, jelly-leon-clients of ai-server-manager heeft de status "Gereed" of "Geslaagd" (`grep -n '"Gereed"\|"Geslaagd"' <WERKMAP>/<repo>/docs/platform-v2/EVIDENCE.json` geeft per repo geen uitvoer).
- [ ] De gate-rijen JLT-09, JLT-14, JLT-38, JLT-41, JLT-42, JLT-43, JLT-44, JLT-45, JLT-46, JLT-47, JLT-48, JLT-54, JLT-55, JLT-56 en JLT-58 hebben elk een bewijsregel met rapportpad en een eerlijke validatie (Sim-getest, Sim-mislukt of Geblokkeerd met reden).
- [ ] JLT-63 en JLT-64 hebben per oplevering een run van S-G4-39; JLT-65 per module-oplevering. De laatste run is gedaan na de laatste codewijziging in jelly-leon.
- [ ] Elk genoemd rapportpad bestaat.
- [ ] Subfase-gates van golf 4 zijn per functie nagelopen: WT-7 en WT-8, G-F2-6, G-F2-7 en G-F2-9, QC-6, F5-S2 en F5-S4 tot en met F5-S8, F6-S5 tot en met F6-S7 (de definities staan in het bouwplan in de hoofdstukken Fx.8, bijvoorbeeld BOUWPLAN#F5.8 Bouwfasen); wat niet gehaald is staat met reden in de melding.
- [ ] De no-go-lijst van het bouwplan is nagelopen: geen schrijfactie naar MediaGuard, geen schrijfactie op de mediamap, geen wijziging aan Emby, geen stock-client die anders beslist dan met de plugin uit.
- [ ] De NAS-rijen JLT-06, JLT-15, JLT-26, JLT-39, JLT-49 en JLT-59 staan op "Geblokkeerd" met NIET GEVALIDEERD en wat nog nodig is; niemand heeft ze als gehaald gemeld.
- [ ] Stappen die door een besluit zijn vervallen (onder meer BG-12, BG-15, BG-30, BG-31, BG-08) staan als "Geblokkeerd (besluit ...)" in het bewijs en niet als gehaald.
- [ ] Patchregisters kloppen: T-JL-REGISTER, T-JLW-STATISCH en T-JLC-STATISCH zijn groen; elke nieuwe haak en elke nieuwe JLC-patch staat in het register met een test.
- [ ] Hub: P-PEIL is voor elke kaartstap gehaald (rapport van R-ONTWERP aanwezig); geen kaart is groen bij onbekend; een kind ziet niets.
- [ ] De CI is groen in alle vier de repos (POORTEN.md, kop "0.5 CI-controle na elke push").
- [ ] Geen modelnaam, geen geheim en geen adres in commits, code of documenten van deze golf (P-VEILIG).
- [ ] De winstmetingen JLT-40 (S-G4-47) en JLT-50 (S-G4-48) hebben een bewijsregel met rapportpad, n en interval
      (Sim-geslaagd, Sim-mislukt of Geblokkeerd met reden).
- [ ] Geen winstclaim zonder meting: een EVIDENCE-regel of document dat een functie "aantoonbaar beter" noemt, steunt
      op de Fx.1-drempels tegen stock-best op dezelfde 12.x-digest, met n en Wilson-interval; anders staat er
      "smoke-gate" (FASERING#Gates per functie; hoofdstuk 2, regel "aantoonbaar beter").
- [ ] Doel van fase P4 volgens `<WERKMAP>/ai-server-manager/docs/platform-v2/01_ARCHITECTUUR/06_FASERING_EN_GATES.md`,
      kop "Fase P4 — Universele mediaplatform": naast de zes functies noemt die kop ook scene search, live-tv/DVR en
      offline apps "waar haalbaar". Besluit Z-20 (genomen 2026-11-11): de zes werkpakketten zonder golf worden in P4
      gebouwd. A-GATE toetst per ID: B03-006 (S-G3-28, S-G3-29), B03-002 (S-G3-30, S-G3-31 of de reden dat die
      verviel), B03-003 (S-G3-32), B03-008 (S-G4-49, S-G4-50), B03-011 (S-G4-51, S-G4-52) en B03-012 (S-G4-53,
      S-G4-54) hebben in elke repo van hun stappen een EVIDENCE-regel met "Bezig" of "Geblokkeerd" en NIET GEVALIDEERD
      voor wat echte apparaten, een echte tuner, een account of de NAS vraagt; elk dossier noemt per onderdeel van de
      bron de scope ("doet upstream al", "ontbreekt en haalbaar", "alleen met echte NAS, apparaten of account"), en
      wat "ontbreekt en haalbaar" heette, is gebouwd en getest. Een onderdeel dat volgens een dossier afviel of naar
      een andere fase schoof, heeft een keuze van de gebruiker (VOORTGANG.md, "Wacht op de gebruiker"); zonder die
      keuze is het "nee". Deze werkpakketten hebben geen gate-rij in FASERING.
- [ ] Module uit (besluit Z-19, genomen 2026-11-11: 404 zoals jelly-leon ADR-0030): de routes van elke module van
      golf 3 en golf 4 geven 404 als de module uit staat (niet aangemeld: 401), elk met een test; de afwijking van
      WP-JSON (B03-033 en B03-035 vragen 501) staat letterlijk in het bewijs van die twee ID's. 501
      `capability_unavailable` komt alleen voor bij een functie die binnen een aangezette module uit staat (bv. chat
      bij BG-12, miniaturen en melden bij BG-24) en bij `propose`/`apply`/`rollback` van de connector. De web- en
      clientstappen behandelen 404 en 501 beide als "niet beschikbaar" (upstream-gedrag); dat is geen afwijking.
- [ ] Excel is bijgewerkt volgens P-EXCEL, de faseregel `P4` staat in `EVIDENCE_PROGRAMMA.json` op "Bezig" met
      "NIET GEVALIDEERD (echte NAS)", STATUS.md heeft een kop voor P4 en de tabel "Topmodel-inzet" in VOORTGANG.md
      heeft een regel per inzet van het topmodel in dit bestand (S-G3-10, S-G3-08 als BG-21 dat vroeg, S-G4-95)
      (S-G4-90).

Uitkomst van A-GATE: "gate golf 4 gehaald" of een lijst met wat ontbreekt. Bij een lijst zet de regisseur per punt een A-HERSTEL uit in de juiste repo; daarna controleert een A-GATE op N4 alleen de open punten opnieuw (geen tweede run op N5).

Let op: deze afvinklijst dekt alleen golf 3 en golf 4. De gates van P4-0, golf 1 en golf 2 staan in
STAPPEN_P4_GOLF1_2.md (S-P40-95, S-G1-90, S-G2-90); S-G4-95 controleert alleen dat hun gate-rapporten bestaan en
"gehaald" zeggen, en draait ze niet opnieuw.

## 10. Fase-afsluiting

Gate golf 4 is het einde van fase P4 op de ontwikkelmachine. Volgorde: S-G4-90 (bewijs samenvoegen, Excel eerste
keer) -> S-G4-95 (A-GATE met de afvinklijst "Gatecontrole golf 4" aan het einde van hoofdstuk 9) -> 10.1 (Excel nog
een keer) -> 10.2 (STATUS.md en VOORTGANG.md) -> 10.3 (melden aan de gebruiker). Niemand slaat een onderdeel over.
De vorm volgt STAPPEN_P2.md, hoofdstuk 9 (S-P2-900 en S-P2-910). `<DOCS>` hieronder is
`<WERKMAP>/ai-server-manager/docs/platform-v2`.

### S-G4-90 - Bewijs samenvoegen voor P4: programmabewijs, Excel en STATUS
- **Repo:** ai-server-manager | **Fase:** P4 (afsluiting) | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** geen eigen ID's; schrijft de faseregel `P4` in `<DOCS>/EVIDENCE_PROGRAMMA.json` en controleert dat elk ID uit hoofdstuk 11 (delen A, C en D) een eerlijke EVIDENCE-regel heeft
- **Vooraf:** elke stap van golf 3 en golf 4 is in `<WERKMAP>/.lokaal/plan/uit/VOORTGANG.md` afgevinkt of staat er met reden als vervallen of geblokkeerd; S-G3-90 gehaald; de laatste run van S-G4-39 is gedaan na de laatste codewijziging in jelly-leon; in geen enkele repo is een schrijvende keten open (P-EXCEL punt 1); de gates van P4-0, golf 1 en golf 2 (STAPPEN_P4_GOLF1_2.md: S-P40-95, S-G1-90, S-G2-90) zijn gehaald
- **Al gedaan?** `python3 -c "import json;[print(f['id'],f['status'],f['validatie'],sep=' | ') for f in json.load(open('<DOCS>/EVIDENCE_PROGRAMMA.json'))['fasen']]"` -> klaar als er een regel "P4 | Bezig | ..." staat met "NIET GEVALIDEERD (echte NAS)" in de validatie (op 2026-11-11 stonden er alleen P0 en P1); `grep -n '^## P4' <DOCS>/OVERDRACHT/STATUS.md` -> klaar als er een kop voor P4 staat; `git -C <WERKMAP>/ai-server-manager log --oneline -5 -- docs/platform-v2/08_EXCEL docs/platform-v2/EVIDENCE_PROGRAMMA.json docs/platform-v2/OVERDRACHT/STATUS.md` -> klaar als de laatste commit op deze paden na de laatste P4-commit van de vier repos ligt. Half werk (alleen een deel van deze drie): verder bouwen op wat er staat.
- **Lees eerst:** POORTEN.md, blok P-EXCEL (de afvinklijst en de regels eronder); `<WERKMAP>/ai-server-manager/tools/excel/README.md`; hoofdstuk 11 van dit bestand; `<DOCS>/OVERDRACHT/STATUS.md` (vorm van een bestaande kop, bijvoorbeeld "Contract 1.3 — toegepast in de Hub en de executor (2026-11-10)"); STAPPEN_P2.md, stap S-P2-900 (zelfde werkwijze)
- **Bouw:**
  1. Controleer de vier repos van dit bestand en de andere zeven: `for r in ai-server-manager home-control-hub appstore-en-fork jelly-leon-platform zoeken-en-persoonlijke-ai media-guard-ultimate media-source-optimizer my_house jelly-leon jelly-leon-web jelly-leon-clients; do echo "$r: $(git -C <WERKMAP>/$r status --short | wc -l) gewijzigd; $(git -C <WERKMAP>/$r rev-list --count @{u}..HEAD) niet gepusht"; done`. Voor jelly-leon, jelly-leon-web, jelly-leon-clients en ai-server-manager moet dat "0 gewijzigd; 0 niet gepusht" zijn. Staat er in ai-server-manager ander werk in de werkmap (bijvoorbeeld het halve werk van ronde 3): stoppen en melden; nooit `git add -A`.
  2. Meet per ID uit hoofdstuk 11 (delen A, C en D) de EVIDENCE-regel in de repo uit de kolom "Repos met een regel": `python3 -c "import json,sys;d={r['id']:r for r in json.load(open(sys.argv[1]))};r=d.get(sys.argv[2]);print(sys.argv[2], r['status'] if r else 'GEEN REGEL', (r or {}).get('validatie',''))" <WERKMAP>/<repo>/docs/platform-v2/EVIDENCE.json <ID>`. Maak een tabel ID | repo | status | validatie | blokkadetekst aanwezig ja/nee. Een bevinding is: een ID zonder regel terwijl de stap is afgevinkt; een regel "Niet gestart" na een afgevinkte stap; een regel "Bezig" zonder "NIET GEVALIDEERD (...)" waar de echte NAS, hardware of een account nodig is; "Gereed" of "Geslaagd" ergens. Herstel dat NIET in een andere repo: de regisseur start daar A-HERSTEL -> R-EERLIJK en deze stap wacht.
  3. Voeg in `<DOCS>/EVIDENCE_PROGRAMMA.json`, lijst `fasen`, een regel toe met precies de velden van de bestaande regels (lees ze eerst): `id` "P4"; `status` "Bezig"; `validatie` "Sim-getest; NIET GEVALIDEERD (echte NAS)"; `bewijs` een zin per repo met de laatste commit en het run-ID van de CI (uit VOORTGANG.md, zelf nagekeken met `gh run list -R lvos04/<repo> -b ccr-c133d7a0-kuz1cv -c <volle hash>` of `gh run view <run-ID> -R lvos04/<repo>`; de volle hash uit `git -C <WERKMAP>/<repo> rev-parse <hash>`: met een korte hash geeft `-c` geen run); `blokkade` wat de cutover-gate (P6) nog vraagt (de NAS-rijen JLT-06, -15, -26, -39, -49, -59, -69, -74 en de echte apparaten); `bijgewerkt` de datum van vandaag. Bestaande regels blijven ongewijzigd. Staat er al een regel "P4" (bijvoorbeeld van P4-0), dan die bijwerken en niet een tweede toevoegen.
  4. Voeg aan het einde van `<DOCS>/OVERDRACHT/STATUS.md` een kop "## P4 — universele mediaserver, golf 3 en golf 4: gebouwd en in de simulator getest (<datum>)" toe met vier korte delen: wat er per repo staat (een regel per repo met de stap-ID's), wat NIET GEVALIDEERD is (uitgeschreven, niet alleen een verwijzing), de open besluiten (hoofdstuk 3 met hun stand) en de uitkomst van de gate ("volgt"; de regisseur laat dit na S-G4-95 invullen, zie 10.2). `CONTRACT_1.3_CONFORMITEIT.md` wordt NIET gewijzigd (V-106).
  5. Doe de punten 2, 3 en 4 van P-EXCEL: de tests van het gereedschap, een proefrun met `--out <bestand buiten de repo>.xlsx`, en elke waarschuwing lezen en verklaren. Exitcode 2 of een onverklaarde waarschuwing: stoppen en melden.
  6. Commit en push `docs/platform-v2/EVIDENCE_PROGRAMMA.json` en `docs/platform-v2/OVERDRACHT/STATUS.md` volgens P-GIT (eerst `git pull --rebase`, bestanden bij naam toevoegen) en wacht op de CI.
  7. De REGISSEUR doet daarna zelf de punten 5 tot en met 8 van P-EXCEL (AGENTEN.md, kop "1.1 Wat de regisseur zelf doet", punt 7): de echte run, een tweede run zonder gewijzigde onderdelen, het `.xlsx.bak`-bestand verwijderen, commit en push met een Nederlands bericht dat "P4" noemt, en de CI-job `excel` controleren. Hij noteert het aantal bijgewerkte rijen per blad en alle waarschuwingen in VOORTGANG.md.
  8. R-EERLIJK vergelijkt twintig rijen van de Excel met de EVIDENCE.json van de repo van herkomst (minstens drie per repo, en alle rijen die in deze run van status wisselden): geen enkele rij is "beter" dan het bewijs.
- **Tests (verplicht):** `<WERKMAP>/.lokaal/excel-venv/bin/python -m pytest -q tools/excel/tests` (vanuit `<WERKMAP>/ai-server-manager`); de proefrun en de echte run uit P-EXCEL, punten 3 en 5; `python3 -c "import json,glob,sys;b=[(p,r['id'],r['status']) for p in glob.glob(sys.argv[1]) for r in json.load(open(p)) if r['status'] in ('Gereed','Geslaagd')];print(b);sys.exit(1 if b else 0)" '<WERKMAP>/*/docs/platform-v2/EVIDENCE.json'` (verwachting: lege lijst, exitcode 0). Negatief: een tweede run van het Excel-script meldt nul gewijzigde onderdelen; een ID uit hoofdstuk 11 zonder regel komt in de tabel van bouwpunt 2 als "GEEN REGEL" terug en niet als leeg (V-005).
- **Poort:** P-EXCEL (alle punten) + P-ai-server-manager (snel, regel `tools/excel`) + P-EERLIJK + P-GIT. Extra: de CI-jobs `python` en `excel` zijn groen op precies de laatste commit.
- **Valkuilen:** V-108, V-107, V-106, V-104, V-100, V-022.
- **Bewijs:** faseregel `P4` in `<DOCS>/EVIDENCE_PROGRAMMA.json` -> "Bezig" met "Sim-getest; NIET GEVALIDEERD (echte NAS)". Blokkade: "NIET GEVALIDEERD (echte NAS): Jelly Leon draait niet als Custom App op de NAS, geen echte apparaten, geen A310 en UHD 770, geen echte MediaGuard met viewerrol, geen echte Hub-koppeling; zie STAPPEN_P6.md." Geen enkele rij wordt "Gereed" of "Geslaagd".
- **Agents:** A-BOUW -> R-EERLIJK, met tussendoor de regisseur voor bouwpunt 7. Kortere keten met reden: zuivere documentatie- en controlestap; er verandert geen code. Geen A-VERKEN (de stand komt uit VOORTGANG.md en wordt in bouwpunt 1 en 2 opnieuw gemeten).
- **Niveau:** A-BOUW N2 (mechanisch: meten en twee documenten bijwerken); R-EERLIJK N3
- **Stop en vraag als:** een repo niet schoon of niet gepusht is; een waarschuwing van het script niet te verklaren is; een ID uit hoofdstuk 11 geen rij in de Excel heeft (een rij toevoegen is een eigen stap volgens `tools/excel/README.md`, geen handwerk); een status in de Excel na de run beter is dan in EVIDENCE.

### S-G4-95 - Gate einde P4: onafhankelijke controle
- **Repo:** jelly-leon, jelly-leon-web, jelly-leon-clients en ai-server-manager, alle alleen lezen (uitzondering op "een stap = een repo": dit is de gatecontrole; A-GATE schrijft alleen `<WERKMAP>/.lokaal/ketens/GATE-P4/RAPPORT-A-GATE.md`) | **Fase:** P4 (afsluiting) | **Omvang:** groot | **Moeilijkheid:** hoog | **Zwaar:** ja (A-GATE draait per repo de volledige poort opnieuw, de repos na elkaar, achter de locks)
- **Werkpakketten en tests:** geen eigen ID's; beoordeelt de afvinklijst "Gatecontrole golf 4" (einde van hoofdstuk 9) en de gate-rijen van golf 4 uit B03_FASERING.md#3. Golven en werkpakketten (JLT-09, 14, 38, 41 tot en met 48, 54, 55, 56, 58; JLT-63 en 64 per oplevering, JLT-65 per module-oplevering)
- **Vooraf:** S-G4-90 afgevinkt; in geen van de vier repos is een keten open; de gate-rapporten `<WERKMAP>/.lokaal/ketens/GATE-P4-0/RAPPORT-A-GATE.md`, `GATE-GOLF-1/RAPPORT-A-GATE.md`, `GATE-GOLF-2/RAPPORT-A-GATE.md` (S-G2-90, STAPPEN_P4_GOLF1_2.md) en `GATE-GOLF-3/RAPPORT-A-GATE.md` (S-G3-90) bestaan
- **Al gedaan?** `ls <WERKMAP>/.lokaal/ketens/GATE-P4/RAPPORT-A-GATE.md && grep -n "gate golf 4" <WERKMAP>/.lokaal/ketens/GATE-P4/RAPPORT-A-GATE.md` -> klaar als het rapport bestaat, de uitkomst "gate golf 4 gehaald" is EN de HEAD van elk van de vier repos (`git -C <WERKMAP>/<repo> rev-parse --short HEAD`) nog gelijk is aan wat het rapport noemt. Op 2026-11-11 bestond de map `<WERKMAP>/.lokaal/ketens/` nog niet.
- **Lees eerst:** hoofdstuk 2 (Gates) en de afvinklijst "Gatecontrole golf 4" van dit bestand; `<WERKMAP>/ai-server-manager/docs/platform-v2/01_ARCHITECTUUR/06_FASERING_EN_GATES.md`, koppen "Fase P4 — Universele mediaplatform" en "Gate matrix"; FASERING#4. Gates; AGENTEN.md, prompt "A-GATE" en kop "2.2 Het protocol"; POORTEN.md, de vier blokken P-<repo> (kop "4. Volledig (CI-volgorde)")
- **Bouw:** (er wordt niets gebouwd; A-GATE levert een rapport)
  1. De regisseur vult de prompt A-GATE: Gate "P4 (golf 4, einde van de fase)"; Repos de vier hierboven; Gate-eisen: de afvinklijst "Gatecontrole golf 4" in dit bestand; onder "Besluiten en bijzonderheden" alleen feiten: de besluiten die de gebruiker tijdens golf 3 en golf 4 nam (met ID), de stappen die door een besluit vervielen, en de genomen besluiten Z-20 ("in P4 bouwen; per werkpakket eerst A-VERKEN, dan stappen in een golf", voor B03-002, B03-003, B03-006, B03-008, B03-011 en B03-012) en Z-19 ("module uit: 404 zoals ADR-0030; afwijking van WP-JSON in het bewijs"), letterlijk met datum; per Z-20-stap of hij liep, verviel (met reden) of gesplitst is; en elke keuze van de gebruiker over een onderdeel dat volgens een dossier afviel. De regisseur en A-GATE kiezen hier zelf niets.
  2. A-GATE volgt de werkwijze uit zijn prompt: per repo schoon, gepusht en CI groen op HEAD; VOORTGANG.md tegen de werkelijkheid; per repo de volledige poort, de repos na elkaar (volgorde: jelly-leon-clients, jelly-leon-web, ai-server-manager, jelly-leon; tussen twee repos `free -m` en `df -h /`); de algemene poorten; daarna per punt van de afvinklijst "ja", "nee" of "niet vast te stellen", met het bewijs dat hij zelf zag.
  3. A-GATE draait zelf opnieuw (niet overnemen uit een rapport): de negatieve proef van de laatste differentiele run (T-JL-COMPAT met `--negatieve-proef`), de opsommende contracttest van S-G4-19 en een schemacontrole op de Hub-leesroutes van S-G4-35.
  4. De regisseur doet na de melding de controles K1, K3 en K7 (AGENTEN.md, kop "2.1 De goedkope controles K1 tot en met K7") voor elke repo.
  5. Uitkomst "gate golf 4 gehaald": de regisseur vinkt de gate af in VOORTGANG.md en volgt 10.1 tot en met 10.3. Anders: per tekortkoming een herstelketen in de betreffende repo (A-HERSTEL met het gate-rapport, daarna R-EERLIJK), daarna S-G4-90 bouwpunt 7 opnieuw als er bewijs is gewijzigd, en dan A-GATE op N4 alleen voor de open punten (rapport `RAPPORT-A-GATE-2.md`). Tweede keer niet gehaald: keuzemenu aan de gebruiker. P5-stappen in de banen jelly-leon en jelly-leon-web starten nooit zonder gehaalde gate (STAPPEN_P5.md, tabel met startvoorwaarden).
- **Tests (verplicht):** per repo de volledige variant uit POORTEN.md (P-jelly-leon, P-jelly-leon-web, P-jelly-leon-clients en P-ai-server-manager, kop "4. Volledig (CI-volgorde)"), elk commando met exitcode en slotregel in het rapport; overgeslagen tests zijn niet groen. Negatief (verplicht, door A-GATE zelf gedraaid): de drie controles uit bouwpunt 3; `grep -n '"Gereed"\|"Geslaagd"'` over de vier EVIDENCE.json-bestanden geeft geen uitvoer.
- **Poort:** de vier blokken P-<repo> (volledig) + P-GIT + P-CONTRACT + P-EERLIJK + P-VEILIG + P-HARDE-EIS + P-INSTALLATIE + P-PEIL, alle als controle (A-GATE wijzigt niets). P-EXCEL alleen als lezer: de Excel-commit van S-G4-90 bestaat en de CI-job `excel` is groen.
- **Valkuilen:** V-098, V-002, V-005, V-027, V-034, V-112, V-033.
- **Bewijs:** geen wijziging in een EVIDENCE.json door A-GATE. De uitkomst komt in `<WERKMAP>/.lokaal/ketens/GATE-P4/RAPPORT-A-GATE.md`, in VOORTGANG.md en (via 10.2) in `<DOCS>/OVERDRACHT/STATUS.md`. De faseregel `P4` blijft "Bezig" met "NIET GEVALIDEERD (echte NAS)", ook bij "gate golf 4 gehaald".
- **Agents:** A-GATE. Kortere keten met reden: zuivere controlestap; A-GATE is zelf de onafhankelijke controle en herstelt niets.
- **Niveau:** A-GATE N5. Winst: dit is de enige plek waar iemand zonder voorkennis vier repos en zes functies tegelijk naast de gate van P4 legt; een gemist verschil in kijkgegevens, een gat in de Hub-toegang of een stock-client die anders beslist, wordt na P4 de basis van de cutover in P6, waar zo'n fout pas met echte gebruikers zichtbaar wordt (geval d: A-GATE aan het einde van een hele fase). Een herhaling voor alleen de open punten loopt op N4.
- **Stop en vraag als:** er tijdens de controle in een van de vier repos wordt geschreven; er te weinig geheugen of schijf is voor een volledige poort (wat niet gedraaid kon worden is "niet vast te stellen" tot het gedraaid is); A-GATE een eis vindt die volgens 06_FASERING_EN_GATES.md of B03_FASERING.md bij P4 hoort maar niet in de afvinklijst staat (tekortkoming van het plan: melden, niet stilzwijgend toevoegen of weglaten); de gate een tweede keer niet gehaald wordt.

### 10.1 Excel bijwerken

De eerste, volledige run is S-G4-90 (bouwpunten 5 en 7). Na "gate golf 4 gehaald" doet de REGISSEUR zelf (AGENTEN.md,
kop "1.1 Wat de regisseur zelf doet", punt 7):

- [ ] Controleer dat in ai-server-manager geen keten open is en de werkboom schoon is:
      `git -C <WERKMAP>/ai-server-manager status --short` (verwachting: geen uitvoer).
- [ ] Is er sinds S-G4-90 bewijs gewijzigd (een herstelketen na de gate)? Dan eerst P-EXCEL punten 2 en 3 (tests en
      proefrun), daarna de echte run (P-EXCEL punt 5) en een tweede run die nul gewijzigde onderdelen meldt. Is er
      niets gewijzigd, dan meldt de run nul wijzigingen en is er niets te committen.
- [ ] Lees elke waarschuwing; exitcode 2 of een onverklaarde waarschuwing: stoppen; de fout wordt in de EVIDENCE.json
      van de repo van herkomst hersteld, niet in het script en niet in de Excel.
- [ ] Verwijder het `.xlsx.bak`-bestand na controle; commit en push volgens P-GIT (Nederlands bericht met "P4",
      eerst `git pull --rebase`, bestanden bij naam toevoegen); controleer de CI-job `excel` op precies die commit.
- [ ] Noteer in VOORTGANG.md het aantal bijgewerkte rijen per blad, alle waarschuwingen en het run-ID van de CI.

Geen enkele rij wordt "Gereed" of "Geslaagd", ook niet na "gate golf 4 gehaald".

### 10.2 STATUS.md en VOORTGANG.md bijwerken

- [ ] **STATUS.md** (`<DOCS>/OVERDRACHT/STATUS.md`): de kop voor P4 bestaat sinds S-G4-90 met de uitkomst "volgt".
      De regisseur start een korte keten A-BOUW (N2) -> R-EERLIJK in ai-server-manager die onder die kop invult: de
      uitkomst van A-GATE (letterlijk), de datum, per punt van de afvinklijst het oordeel in een tabel, en de lijst van
      wat alleen op de echte NAS te bewijzen is met het onderdeel van STAPPEN_P6.md dat het oppakt. Geen woord
      "klaar", "gereed" of "geslaagd" voor iets dat alleen in de simulator is gemeten. Commit en push volgens P-GIT;
      de CI moet groen zijn. Doe dit VOOR de laatste Excel-run van 10.1.
- [ ] **VOORTGANG.md** (door de regisseur zelf): de gate van P4 afgevinkt met datum en de verwijzing naar
      `<WERKMAP>/.lokaal/ketens/GATE-P4/RAPPORT-A-GATE.md`; de tabel "Topmodel-inzet" aangevuld met S-G4-95 (en
      S-G3-10, en S-G3-08 als daar N5 is ingezet); de lijst "Geblokkeerd" bijgewerkt; de besluiten van hoofdstuk 3
      met hun stand.
- [ ] **Per repo** blijft EVIDENCE.json de waarheid. De regisseur wijzigt zelf geen EVIDENCE.json.

### 10.3 Melden aan de gebruiker

De regisseur meldt in het Nederlands, kort en zonder vakjargon, en sluit af met een keuzemenu
(BESLUITEN_EN_BLOKKADES.md, kop "0.5 Sjabloon van een keuzemenu"). Hij schrijft nergens dat iets "gereed" of
"geslaagd" is. Onderdelen, in deze volgorde:

1. **Uitkomst van de gate:** "gate golf 4 gehaald" of niet, met het aantal punten per oordeel.
2. **Wat er nu staat, per repo:** jelly-leon (Watch Together, ondertitelsync en publicatie zonder vertaling,
   kwaliteitscontrole, apparaten en GPU-banen, segmenten met correctie en leren, connector voor de Hub,
   metadata en anime-mapping, universele bibliotheek, scènezoeker op ondertitels, downloadrechten, live-tv en DVR),
   jelly-leon-web (webplugins en haken), jelly-leon-clients (marker, Android TV-patches, emulatormatrix, offline
   downloaden, beschikbaarheid van clients),
   ai-server-manager (adapter en vijf Jelly Leon-kaarten op het scherm Media). Per repo de laatste commit en het
   run-ID van de CI.
3. **Wat NIET GEVALIDEERD is:** niets is op de echte NAS, met echte apparaten (tv's, telefoons, Swiftfin) of met de
   A310 en UHD 770 geprobeerd; MediaGuard en de Hub zijn alleen als simulator of nagebootste plugin gebruikt. Per punt
   welk onderdeel van STAPPEN_P6.md het oppakt (NAS-rijen JLT-06, -15, -26, -39, -49, -59).
4. **De HARDE EIS:** kijkgeschiedenis, spoorkeuzes en gebruikers zijn in de differentiele runs ongewijzigd gebleven
   (rapportpaden van S-G3-27 en S-G4-39); Emby is niet aangeraakt; MediaGuard is alleen gelezen.
5. **Besluiten:** welke van hoofdstuk 3 genomen zijn en welke stappen daardoor vervielen of "Geblokkeerd (besluit
   ...)" staan; welke nog open zijn.
6. **Wat het plan niet wist:** de punten "ONBEKEND" die tijdens de bouw zijn vastgesteld, en per werkpakket uit
   besluit Z-20 (B03-002, B03-003, B03-006, B03-008, B03-011, B03-012) de scope uit het dossier: wat upstream al deed,
   wat gebouwd is en wat alleen op de echte NAS of met echte apparaten, een tuner of een account kan. Zoeken op
   omschrijving en spraak in de scènezoeker wachten op BG-06 (P5). "Module uit" geeft 404 (besluit Z-19). Staat er
   nog een keuze open over een onderdeel dat volgens een dossier afviel, dan komt die in het keuzemenu.
7. **Inzet van het topmodel:** de regels uit de tabel "Topmodel-inzet" met per regel wat het opleverde.
8. **Keuzemenu**, bijvoorbeeld:
   1. Doorgaan met P5 (alleen bij "gate golf 4 gehaald"). Gevolg: de open besluiten voor P5 (BG-06, BG-18) komen
      eerst langs (S-P5-01).
   2. Eerst een open besluit van hoofdstuk 3 nemen, zodat een vervallen stap alsnog kan worden gebouwd.
   3. Eerst zelf op de echte NAS proberen wat P6 vraagt.
   4. Stoppen en de stand laten staan.

Er wordt geen PR gemaakt en niets naar `main` overgenomen zonder dat de gebruiker daar uitdrukkelijk om vraagt.

---

## 11. Dekking

Elke rij is een ID. "Stappen" noemt de stappen van dit bestand die het ID bouwen, meten of bijwerken; de EERSTE stap
in de rij zet de EVIDENCE-regel op "Bezig" (of "Geblokkeerd" met reden), de stappen erna leveren een deel. In S-G4-90
moet elk ID uit de delen A, C en D een eerlijke EVIDENCE-regel hebben. Deel B noemt de ID's die NIET in dit bestand
horen, met de plek waar ze wel staan. Herkomst: de B03-, JLT- en EX-ID's staan in
`<WERKMAP>/.lokaal/plan/bron/ALLE_IDS.txt`; de contractpunten (C1.3-...) en Δ-HUB-2 komen uit
`<WERKMAP>/ai-server-manager/docs/platform-v2/CONTRACT_1.3_CONFORMITEIT.md` (kolom "Moment" = P4) en staan niet in
ALLE_IDS.txt. Bij elke rij met echte NAS, hardware of accounts hoort naast "Bezig" de tekst "NIET GEVALIDEERD (...)";
de echte uitvoering staat in STAPPEN_P6.md.

### 11.1 Deel A - Werkpakketten van golf 3 en golf 4

| ID | Repos met een regel | Stappen of reden |
|---|---|---|
| B03-002 | jelly-leon, jelly-leon-web | besluit Z-20: S-G3-30 (serverdeel), S-G3-31 (webdeel, alleen als het dossier van S-G3-30 een webdeel noemt); echte bibliotheek -> STAPPEN_P6.md (N-P6-09) |
| B03-003 | jelly-leon-clients | besluit Z-20: S-G3-32 (gaten op de ontwikkelmachine); de regel blijft "Geblokkeerd" (acceptatie op echte tv's en apparaten) -> STAPPEN_P6.md (N-P6-09) |
| B03-004 | jelly-leon | aanvulling F5: S-G4-03 (delen 1, 3, 4), S-G4-04 (deel 2); echte GPU's -> STAPPEN_P6.md |
| B03-005 | jelly-leon | aanvulling F5: S-G4-05, S-G4-08, S-G4-22 (webdeel uitleg); echte DV-apparaten -> STAPPEN_P6.md |
| B03-006 | jelly-leon | besluit Z-20: S-G3-28 (serverdeel; BG-17 vooraf), S-G3-29 (pluginpagina); eindscenario EX37 in STAPPEN_P6.md (S-P6-15) |
| B03-007 | jelly-leon | afronding: S-G4-16 (serverdeel, punten a, b, d), S-G4-23 (web), S-G4-27 (Android TV), S-G4-28 (Android, desktop), S-G4-30 (matrix), S-G4-48 (winstmeting JLT-50); begin van de aanvulling in golf 2 (STAPPEN_P4_GOLF1_2.md, S-G2-50) |
| B03-008 | jelly-leon, jelly-leon-web | besluit Z-20: S-G4-49 (serverdeel, alleen tekst uit ondertitelsporen), S-G4-50 (webdeel); spraak en zoeken op omschrijving wachten op BG-06 (P5) |
| B03-010 | jelly-leon | golf 3-deel streamroutes: S-G3-09 (meting, ADR), S-G3-10 (filter); deel IsKid in golf 1 (STAPPEN_P4_GOLF1_2.md, S-G1-18) |
| B03-011 | jelly-leon, jelly-leon-clients | besluit Z-20: S-G4-51 (serverdeel), S-G4-52 (Android); echte telefoons en EX35 -> STAPPEN_P6.md (N-P6-09, S-P6-13) |
| B03-012 | jelly-leon, jelly-leon-web | besluit Z-20: S-G4-53 (serverdeel), S-G4-54 (webdeel); echte tuner en EX38 -> STAPPEN_P6.md (N-P6-09, S-P6-17) |
| B03-022 | jelly-leon | S-G3-17; S-G4-44 (beheerpagina) |
| B03-023 | jelly-leon | S-G3-18; S-G4-44 (beheerpagina) |
| B03-024 | jelly-leon, jelly-leon-web | S-G3-04 (serverdeel), S-G3-24 (webdeel) |
| B03-025 | jelly-leon, jelly-leon-web | S-G3-19 (haperbeleid), S-G4-09 (diagnose, advies), S-G4-43 (webdialoog) |
| B03-026 | jelly-leon, jelly-leon-clients | alleen na BG-10: S-G3-20, S-G3-21; S-G3-26 alleen bij de keuze "clientpatch"; zonder besluit "Geblokkeerd (besluit BG-10)" |
| B03-027 | jelly-leon | alleen na BG-09 "aan": S-G3-23; anders "Geblokkeerd (besluit BG-09)" (bewijsregel in S-G3-23) |
| B03-028 | jelly-leon, jelly-leon-web | alleen na BG-12 "aan": S-G4-10, S-G4-24; anders "Geblokkeerd (besluit BG-12)" |
| B03-029 | jelly-leon, ai-server-manager | S-G4-11 (connector, events), S-G4-44 (beheerpagina), S-G4-33 (Hub-kaart), S-G4-35 (Hub samen), S-G4-39 (clientmatrixdocument); voorwaarde S-G4-31, S-G4-32 |
| B03-036 | jelly-leon-web | alleen na BG-15: S-G4-20 (rij), S-G4-45 (dialogen) |
| B03-037 | jelly-leon-clients, jelly-leon | S-G4-29 (emulators, desktop), S-G4-39 (webrijen) |
| B03-039 | jelly-leon, ai-server-manager | S-G4-12 (connector, register, meting), S-G4-34 (Hub-kaart), S-G4-35 |
| B03-040 | jelly-leon | S-G3-03; S-G3-05 (taal uit tekst) |
| B03-041 | jelly-leon | S-G3-05 |
| B03-042 | jelly-leon | S-G3-06 |
| B03-043 | jelly-leon | S-G3-07 |
| B03-047 | jelly-leon | S-G3-08 (alleen na BG-19; anders stopt de stap en blijft het ID "Niet gestart" met de reden "wacht op besluit BG-19") |
| B03-049 | jelly-leon, jelly-leon-clients | alleen het P4-deel: S-G4-13, S-G4-30; de rest hoort bij P5 (STAPPEN_P5.md: S-P5-107, S-P5-62, S-P5-111, S-P5-115, S-P5-120) |
| B03-050 | jelly-leon | S-G3-01 |
| B03-051 | jelly-leon | S-G3-11; S-G3-12 (recall bijwerken) |
| B03-052 | jelly-leon | S-G3-12 |
| B03-053 | jelly-leon | S-G3-02 |
| B03-054 | jelly-leon | S-G3-13 |
| B03-055 | jelly-leon | S-G3-14 |
| B03-056 | jelly-leon | S-G3-15 |
| B03-057 | jelly-leon, jelly-leon-web | S-G3-16 (pluginpagina), S-G3-25 (label op de itempagina) |
| B03-058 | jelly-leon, ai-server-manager, jelly-leon-clients | S-G4-14 (connector), S-G4-36 (Hub-kaart), S-G4-30 (clients), S-G4-35 |
| B03-063 | jelly-leon | S-G4-01 (spike, ADR), S-G4-02 (wrapper, socket), S-G4-03 (image, planner) |
| B03-064 | jelly-leon | S-G4-04 |
| B03-065 | jelly-leon, jelly-leon-web | S-G4-05 (server), S-G4-21, S-G4-22, S-G4-41 (web) |
| B03-066 | jelly-leon, jelly-leon-web | S-G4-06; S-G4-42 (beheerpagina), S-G4-41 (web) |
| B03-067 | jelly-leon, jelly-leon-web | S-G4-08 (server), S-G4-22 (web) |
| B03-068 | jelly-leon, jelly-leon-clients | S-G4-07; S-G4-42 (beheerpagina), S-G4-30 (officiele apps), S-G4-39 (regressie) |
| B03-069 | jelly-leon, jelly-leon-clients, ai-server-manager | S-G4-18 (connector), S-G4-25 (marker), S-G4-26 (Android TV, alleen na BG-30), S-G4-37 (Hub-kaarten), S-G4-35 |
| B03-074 | jelly-leon | S-G3-22 |
| B03-075 | jelly-leon, jelly-leon-web | S-G4-15 (routes, rechten), S-G4-40 (leren), S-G4-46 (web) |
| B03-076 | jelly-leon, jelly-leon-web | S-G4-16 (beheerpagina), S-G4-23 (knoppen, alleen na BG-31 a1), S-G4-46 (hint, correctiepaneel) |
| B03-077 | jelly-leon-clients | alleen na BG-31 a1 en BG-08: S-G4-27, S-G4-28; S-G4-30 (matrix); anders "Geblokkeerd (besluit BG-31)" of "(besluit BG-08)" |
| B03-078 | jelly-leon, ai-server-manager | S-G4-17 (planner, MediaGuard, connector), S-G4-38 (Hub-kaart), S-G4-35 |

### 11.2 Deel B - B03-werkpakketten die NIET in dit bestand horen

| ID | Waar wel | Reden |
|---|---|---|
| B03-038, B03-044, B03-045, B03-046, B03-048, B03-059, B03-079 en de rest van B03-049 | STAPPEN_P5.md | rij "P5" in FASERING#3. Golven en werkpakketten |
| B03-020, B03-030, B03-060, B03-070 | STAPPEN_P4_GOLF1_2.md (S-P40-60, S-P40-62, S-P40-64, S-P40-66) | golf 0 en P4-0 |
| B03-014, B03-015, B03-016, B03-019 | STAPPEN_P4_GOLF1_2.md en STAPPEN_P6.md | P4-0 en doorlopend; B03-019 komt hier alleen terug als de compat-runs S-G3-27 en S-G4-39 |
| B03-009, B03-017, B03-018 | STAPPEN_P4_GOLF1_2.md (golf 1) | golf 1; de stappen hier gebruiken ze alleen |
| B03-021, B03-031 tot en met B03-035, B03-061, B03-062, B03-071, B03-072, B03-073 | STAPPEN_P4_GOLF1_2.md (golf 2, S-G2-10 tot en met S-G2-44) | golf 2 |
| B03-001, B03-013 | STAPPEN_P6.md (B03-013 eindproef) | forkstrategie (P0, regel al "Bezig") en terugkeer naar upstream (doorlopend; eindproef in P6 volgens FASERING#3, rij P6) |

B03-002, B03-003, B03-006, B03-008, B03-011 en B03-012 stonden hier tot 2026-11-11 als "geen bouwstap". Na besluit
Z-20 (in P4 bouwen) staan ze in deel A met hun stappen. De cue-extractie die WP-JSON B03-074 "gedeeld met B03-008"
noemt, komt uit S-G1-34 (B03-018, STAPPEN_P4_GOLF1_2.md).

### 11.3 Deel C - Testrijen

| ID | Repos met een regel | Stappen of reden |
|---|---|---|
| JLT-01, JLT-02 | jelly-leon, jelly-leon-web | hermeting met de plugin aan: S-G3-24; voorwaarde S-G3-04; de voormeting hoort bij B03-020 (STAPPEN_P4_GOLF1_2.md, S-P40-60) |
| JLT-03 | jelly-leon | S-G3-19 (gate golf 3) |
| JLT-04 | jelly-leon, jelly-leon-web | S-G4-09, S-G4-43; A310 en UHD 770 -> STAPPEN_P6.md |
| JLT-05 | jelly-leon, jelly-leon-web | S-G3-17, S-G3-18, S-G3-27 (stock-web), S-G4-44, S-G4-10 en S-G4-24 (chat-deel alleen na BG-12) (gate golf 3) |
| JLT-06 | jelly-leon | NAS-rij: alleen bewijsregel "Geblokkeerd" (S-G3-17); uitvoering in STAPPEN_P6.md |
| JLT-07 | jelly-leon, jelly-leon-clients | S-G3-20, S-G3-21; S-G3-26 (native deel); zonder BG-10 "Geblokkeerd (besluit BG-10)" (gate golf 3) |
| JLT-08 | jelly-leon | S-G3-23 alleen na BG-09; anders "Geblokkeerd (besluit BG-09)" (gate golf 3) |
| JLT-09 | jelly-leon | S-G3-17, S-G4-10, S-G4-11, S-G4-44, S-G4-39 (gate golf 4) |
| JLT-14 | jelly-leon-web, jelly-leon-clients, jelly-leon | S-G4-20, S-G4-45, S-G4-29, S-G4-39 (gate golf 4) |
| JLT-15 | jelly-leon | NAS-rij: bewijsregel "Geblokkeerd" (S-G4-12, S-G4-20); uitvoering in STAPPEN_P6.md |
| JLT-19 | jelly-leon | S-G4-12 |
| JLT-20 | jelly-leon | S-G3-03, S-G3-05 (gate golf 3) |
| JLT-22 | jelly-leon | S-G3-06 (gate golf 3) |
| JLT-23 | jelly-leon | S-G3-07 (gate golf 3) |
| JLT-24 | jelly-leon | S-G3-03, S-G3-08, S-G3-27 (gate golf 3) |
| JLT-25 | jelly-leon, jelly-leon-clients | P4-deel: S-G4-13, S-G4-30, S-G4-39; machinevertaling in P5 (S-P5-111, S-P5-115) |
| JLT-26 | jelly-leon | NAS-rij: bewijsregel "Geblokkeerd" (S-G3-03, S-G4-13); uitvoering in STAPPEN_P6.md |
| JLT-30 | jelly-leon | S-G3-11, S-G3-12 (gate golf 3) |
| JLT-31 | jelly-leon | S-G3-12 (gate golf 3) |
| JLT-32 | jelly-leon | S-G3-11, S-G3-13 (gate golf 3); het deel spraakherkenning in P5 (S-P5-108) |
| JLT-33 | jelly-leon | S-G3-13 (gate golf 3) |
| JLT-34 | jelly-leon | S-G3-14 (gate golf 3) |
| JLT-35 | jelly-leon | S-G3-01, S-G3-27 (gate golf 3) |
| JLT-36 | jelly-leon | S-G3-02, S-G3-12 (gate golf 3) |
| JLT-37 | jelly-leon | S-G3-15 (gate golf 3) |
| JLT-38 | jelly-leon, jelly-leon-web, jelly-leon-clients, ai-server-manager | S-G3-16, S-G3-25, S-G4-14, S-G4-36, S-G4-30, S-G4-35, S-G4-39 (gate golf 4) |
| JLT-39 | jelly-leon | NAS-rij: bewijsregel "Geblokkeerd" (S-G3-01); uitvoering in STAPPEN_P6.md |
| JLT-41 | jelly-leon, jelly-leon-web | S-G4-06 (serverdeel), S-G4-22 (meting) (gate golf 4) |
| JLT-42 | jelly-leon, jelly-leon-web, jelly-leon-clients | S-G4-05, S-G4-06, S-G4-42, S-G4-21, S-G4-41, S-G4-25, S-G4-26, S-G4-30 (gate golf 4) |
| JLT-43 | jelly-leon | hermeting met de wrapper: S-G4-03; de eerste meting hoort bij B03-062 (golf 2, STAPPEN_P4_GOLF1_2.md, S-G2-32) (gate golf 4) |
| JLT-44 | jelly-leon | S-G4-01, S-G4-02, S-G4-03 (gate golf 4) |
| JLT-45 | jelly-leon | S-G4-04 (gate golf 4) |
| JLT-46 | jelly-leon, jelly-leon-clients | S-G4-07, S-G4-42, S-G4-30 (gate golf 4) |
| JLT-47 | jelly-leon, jelly-leon-web | S-G4-08, S-G4-22 (gate golf 4) |
| JLT-48 | jelly-leon, jelly-leon-web, ai-server-manager | S-G4-02, S-G4-05, S-G4-07, S-G4-18, S-G4-21, S-G4-37, S-G4-39 (gate golf 4) |
| JLT-40 | jelly-leon | S-G4-47 (winstmeting F5; emulator- en desktopdelen uit S-G4-30; meetcommando uit S-P40-64 bouwpunt 6, STAPPEN_P4_GOLF1_2.md); geen gate-rij in FASERING, wel nodig voor de regel "aantoonbaar beter" |
| JLT-49 | jelly-leon | NAS-rij: bewijsregel "Geblokkeerd" (S-G4-03, S-G4-21); uitvoering in STAPPEN_P6.md |
| JLT-51 | jelly-leon | hoort bij golf 2 (B03-073; STAPPEN_P4_GOLF1_2.md); hier alleen de hermeting in S-G4-16 |
| JLT-50 | jelly-leon | eerste meting in golf 2 (STAPPEN_P4_GOLF1_2.md: S-G2-42 Intro, Recap en Preview; S-G2-44 Outro; meetcommando uit S-P40-66 bouwpunt 6; nagelopen in S-G2-90); hier de herhaling na golf 4 in S-G4-48 (winstmeting F6); geen gate-rij in FASERING, wel nodig voor de regel "aantoonbaar beter"; echte series -> STAPPEN_P6.md |
| JLT-53 | jelly-leon | audiodeel golf 2 (S-G2-42, STAPPEN_P4_GOLF1_2.md); cues en hoofdstuksignalen S-G3-22 (gate golf 3) |
| JLT-54 | jelly-leon, jelly-leon-web | S-G4-15, S-G4-40, S-G4-46 (gate golf 4) |
| JLT-55 | jelly-leon, jelly-leon-web, jelly-leon-clients | S-G4-16, S-G4-23, S-G4-46, S-G4-27, S-G4-28, S-G4-30, S-G4-39 (gate golf 4) |
| JLT-56 | jelly-leon | S-G4-16 (eindrun), S-G4-15 (onderdeel h) (gate golf 4) |
| JLT-57 | jelly-leon | S-G3-22 (gate golf 3) |
| JLT-58 | jelly-leon, ai-server-manager | S-G4-17, S-G4-38 (gate golf 4) |
| JLT-59 | jelly-leon | NAS-rij: bewijsregel "Geblokkeerd" (S-G4-15, S-G4-17, S-G4-46); uitvoering in STAPPEN_P6.md |
| JLT-63 | jelly-leon | per oplevering: S-G3-27, S-G4-39; daarnaast S-G3-09, S-G3-10; eerdere delen in STAPPEN_P4_GOLF1_2.md |
| JLT-64 | jelly-leon | per oplevering: S-G3-27, S-G4-39; daarnaast S-G3-10, S-G4-19; eerdere delen in STAPPEN_P4_GOLF1_2.md |
| JLT-65 | jelly-leon | per module-oplevering: S-G3-27, S-G4-39; eerdere delen in STAPPEN_P4_GOLF1_2.md |
| JLT-69, JLT-74 | - | alleen genoemd in hoofdstuk 1; NAS-rijen van P6 (STAPPEN_P6.md) |

Niet in dit bestand: JLT-10, JLT-11, JLT-12, JLT-13, JLT-16, JLT-17 en JLT-52 (golf 2, STAPPEN_P4_GOLF1_2.md;
JLT-10 hoort volgens TEST-JSON bij B03-030 en B03-032); JLT-18, JLT-21, JLT-27, JLT-28 en JLT-29 (P5, STAPPEN_P5.md); JLT-60, JLT-61, JLT-62,
JLT-66, JLT-67, JLT-68 en JLT-70 tot en met JLT-73 (P4-0 en golf 1, STAPPEN_P4_GOLF1_2.md).

### 11.4 Deel D - Excel-testrijen, contractpunten en repowerk

| ID | Repos met een regel | Stappen of reden |
|---|---|---|
| EX06 | jelly-leon (alleen het Jelly Leon-deel; eigenaar volgens ai-server-manager controleren, zie S-G3-15) | S-G3-15; de rest in STAPPEN_P6.md |
| EX08 | jelly-leon (deels) | S-G4-04; het MediaGuard-deel wacht op MediaGuard; rest in STAPPEN_P6.md |
| EX16 | jelly-leon (alleen het Jelly Leon-deel) | S-G3-15; andere delen in STAPPEN_P2.md, STAPPEN_P3.md en STAPPEN_P6.md |
| EX34 | jelly-leon (alleen het Jelly Leon-deel) | S-G3-23 alleen na BG-09; anders "Geblokkeerd (besluit BG-09)"; rest in STAPPEN_P5.md en STAPPEN_P6.md |
| EX36 | jelly-leon, jelly-leon-web | S-G3-16 (serverdeel), S-G3-25 (webdeel), S-G4-49 (scènezoeker, negatieve test b); rest in STAPPEN_P5.md en STAPPEN_P6.md |
| C1.3-JL-06 | jelly-leon | S-G4-19 (Moment P4) |
| C1.3-JL-07 | jelly-leon | S-G4-19 (Moment P4) |
| C1.3-JL-08 | jelly-leon | S-G4-19 (Moment "P4 (na BG-04; acties na BG-05)") |
| C1.3-ASM-21 | ai-server-manager | deel Jelly Leon-plugin (Moment P4): S-G4-31, S-G4-35; de delen P3 en P4-0 in STAPPEN_P3.md en STAPPEN_P4_GOLF1_2.md |
| Δ-HUB-2 | ai-server-manager (geen eigen regel; voortgang in de statusregel van C1.3-ASM-21) | S-G4-32, S-G4-35 |
| C1.3-JLC-02 | jelly-leon-clients | niet in dit bestand (Moment NU); S-G4-25 houdt zich alleen aan de regel "builds niet verspreiden" |
