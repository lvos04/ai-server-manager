# Programma-fasering en harde doorgangsgates

## Fase P0 — Inspecteren en herstellen
**Doel:** documenteer bestaande productie, gebruik, datasetindeling, actuele image-tags, NAS-versie, hardware rendernodes, auth, bestaande OneDrive kopie en afhankelijke apps. Maak eerste ZFS-snapshots plus geslaagde restore-test van foto en een appdatabase.
**Opgeleverd:** inventaris, opslagplattegrond, data-eigenaarschap, source/version register, RPO/RTO-doelen en testbackup.
**No-go:** onduidelijke datamap, onherstelbare belangrijke data of storage in degraded state.

## Fase P1 — Ogen en toegang
**Doel:** installeer Beszel, Uptime Kuma en Gotify; maak onafhankelijke app-heartbeats en kritieke meldingen. Zet basis Hub read-only aan; Authentik OIDC zodra loginroute voorbereid is.
**Opgeleverd:** appcatalogus, NAS CPU/RAM/GPU/disk, uptime, alert bij app offline, secure mobile access.
**No-go:** GUI toont oude data als gezond, management staat op publiek internet, eigen agents op mini-pc.

## Fase P2 — Veilig automatiseren
**Doel:** risk policy, acties met diff/TTL, limited executor, dry-run, staged updates, Node-RED integration.
**Opgeleverd:** goedgekeurde R1-restart, audit, rollback en blokkade van R3 zonder toestemming.
**No-go:** AI kan rechtstreeks shell/sudo, policy overruled door model, DB backup onbekend.

## Fase P3 — Eigen apps koppelen
**Doel:** MediaGuard v1.2.2, MSO 1.5.0/1.6 kandidaat en my_house v0.1.0 live API contracten; actual hardware/live accounts testen. Integratie met Hub.
**Opgeleverd:** één incident en downloadketen, één smart-home paneel, energy provenance; bestaande eigen app DB behouden.
**No-go:** wijzigingen aan Prowlarr/SABnzbd vanuit twee eigenaren, boiler schakelen, ongeteste Gree aansturing.

## Fase P4-0 — Jellyfin 12.x als basis
**Doel:** server en web van de fork naar de nieuwste stabiele Jellyfin 12.x (.NET 10) vóór er B03-functies gebouwd worden; de kijkgeschiedenis uit de bestaande mediaserver (Emby; ook Jellyfin als D07 dat meet) veilig overnemen; eerlijke baselines van standaard Jellyfin op dezelfde versie.
**Opgeleverd:** jelly-leon en jelly-leon-web op 12.x met groene CI, plugin op 12.x, terugzetproef (vorige image + DB-snapshot), Emby-overname (alleen-lezen) en proefmigratie op een kopie met een per-gebruikerrapport en akkoord, baselines (stock-standaard en stock-best), register van upstream-gedrag, MediaGuard volgt Emby én Jelly Leon zonder legacy-auth (Δ-MG-AUTH per server, Δ-MG-DUAL).
**No-go:** een verschil in kijkgeschiedenis of rechten zonder uitdrukkelijk akkoord van de gebruiker (HARDE EIS, ADR-0020), terugzetten niet bewezen, een schrijfactie naar Emby, stock-clients breken, legacy-auth weer aan zonder besluit, B03-batch op de NAS zonder Δ-MG-AUTH.

## Fase P4 — Universele mediaplatform
**Doel:** Jellyfin plugin/adapter eerst, daarna minimaal onderhouden fork, streaming matrix, A310 scheduling, scene search, live-tv/DVR, offline apps waar haalbaar. Daarbij de zes uitbreidingen Watch Together, aanbevelingen, ondertitels (klassiek), kwaliteitscontrole, apparaatprofielen en intro/outro/recap als modules van één plugin, in golven (gemeenschappelijke basis eerst).
**Opgeleverd:** echte playbacktests, TV/client compat, intacte watch history, MediaGuard request links. Per functie een meetbare winst tegen stock-standaard én stock-best op dezelfde 12.x-digest; compat-regressie per clientrol; differentiële gegevensbeschermingsrun.
**No-go:** upstream clients breken, HDR/DV verlies, media mutatie buiten MediaGuard, Jellyfin direct verwijderen. Ook: een afspeelstart van een stock-client weigeren of verlagen; schrijven in kijkgeschiedenis buiten het besluit BG-21 en de eenmalige overname van B03-015; Emby uitzetten of verwijderen vóór de controlelijst "Emby verwijderen"; B03-batch op de A310 terwijl MediaGuard daar encodeert; een winstclaim zonder baseline of op een niet-bevroren testset.

## Fase P5 — Netwerk, persoonlijke AI, kosten en uitbreiding
**Doel:** AdGuard pilot, NetAlertX discovery, zoekindex, spraak (opt-in), energie- en kostenanalyse, nieuwe appcatalogus en uitbreidbare connectors, plus de optionele lokale AI van B03 (vertaling, embeddings, spraakherkenning voor taal en segmenten).
**Opgeleverd:** veilige DNS fallback, per-bron indexrechten, opt-in lokale STT/TTS, geen overage, met één producent per modelsoort en een aangetoonde klassieke terugval.
**No-go:** router lockout, AI leaks via RAG, automatische credentials naar internet, een model in de jelly-leon-image, een model-app op de A310, een NC-gelicentieerd model.

## Fase P6 — Oplevering en beheer
Regressies, releasegates, herstelproef, mobiele E2E, 72h soak, update/rollback, documentatie, metrics vergelijking en alleen dan productieacceptatie.

## Gate matrix
| Voorwaarde | Verplichting voor volgende fase |
|---|---|
| NAS versie/pool bekend | Altijd |
| OneDrive foto en DB restore getest | Voor mutaties aan bestaande data en upgrades |
| ZFS snapshots en pre-change database-export | Voor schema- en infrastructuurwijzigingen |
| Risk policy + privileged executor tested | Voor autonome writes |
| MediaGuard/MSO API contract live verified | Voor downloadgerelateerde acties |
| my_house fysieke apparaten gevalideerd | Voor climate actuation |
| Jellyfin client/GPU testmatrix geslaagd | Voor universele mediaserver cutover |
| Δ-MG-AUTH per server + Δ-MG-DUAL + proefmigratie 10.11 → 12.x op een kopie geslaagd | Voor P4 (B03-functies) |
| Emby-overname JLT-70…73 Sim-geslaagd (golf 0, herhaald in P4-0) | Voor P4 (B03-functies) |
| Vóór/na-rapport per gebruiker + uitdrukkelijk akkoord op elk verschil (HARDE EIS, ADR-0020) | Voor elke cutover |
| Controlelijst "Emby verwijderen" (laatste delta, eindrapport + akkoord, ZFS-snapshot, exportarchief, MediaGuard los) | Voor Emby uit (de gebruiker beslist en voert uit) |
| Eén plugin met modules + belastingtest binnen de manifestresources | Voor B03-batch op de NAS |
| Hub-sleutelpin in Jelly Leon (JL4) | Voor Hub-kaarten van B03 |
| Δ-CONTRACT-MG | Voor herstel/zoeken in MediaGuard via de Hub |
| DNS rollback route getest | Voor routerwijzigingen |
| 0 paid API overage en monitor | Voor AI in productie |
