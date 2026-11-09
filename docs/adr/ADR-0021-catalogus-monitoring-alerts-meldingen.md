# ADR-0021 — Appcatalogus, gezondheidsmodel, monitoringbronnen, tijdreeksen, alerts en meldingen (P1, deel 1)

Status: aangenomen · Datum: 2026-11-09 · Fase: P1 "Ogen en toegang" (backend deel 1)
Betreft: B01-002, B01-004, B09-001, B09-002, B09-003 en de Gotify-adapter (`notification.send`, R0).

## Context

De Hub moet alle apps op de NAS tonen met herkomst en gezondheid, de NAS zelf live laten zien en zonder pushstorm
alarmeren. Harde eisen: alleen lezen ten opzichte van de NAS en bestaande apps; nooit voorbeeldwaarden als echte waarden;
onbekend is `unknown`, nooit groen; bestaande apps via hun bestaande routes (contract 1.2 §2.3); geen privileged
collector; alles in de eigen PostgreSQL van de alles-in-één image. Er is geen echte NAS, Uptime Kuma, Beszel of Gotify
beschikbaar: alle protocolkennis is **bronwaarneming** (broncode op een vaste tag/commit) en **NIET GEVALIDEERD**.

Bronnen (alleen gelezen, sparse checkout):
- TrueNAS-middleware `TS-25.10.8` (`29ed02b8`): `plugins/reporting/events.py`, `realtime_reporting/*`,
  `api/v25_10_0/{reporting,app,app_image,core}.py`, `service/core_service.py`, `api/base/server/ws_handler/rpc.py`.
- Uptime Kuma `2.5.9`: `server/prometheus.js`, `server/auth.js` (`apiAuth`), `server/routers/status-page-router.js`.
- Beszel `v0.21.1`: `internal/entities/system/system.go`, `internal/hub/api.go`, migratie-snapshot `0_20_0`.
- Gotify `v3.1.1`: `router/router.go`, `auth/authentication.go`, `model/{message,version,health}.go`.

## Besluiten

### 1. Catalogus (B01-002)
- **Identiteit = TrueNAS-app-id (`runtime_id`).** Die wijzigt niet bij een herstart van NAS of app; de Hub-UUID hoort
  er vast bij. Discovery is idempotent (upsert op `runtime_id`), draait alleen op een **verse, geslaagde** `apps`-meting
  en verwijdert nooit: ontbreekt een app in een verse meting, dan `aanwezig=false` + `verdwenen_sinds`.
- **Installatiewijze** uit `app.query`: `custom_app: true` = compose-app (Install via YAML, buiten platformbeleid →
  `custom_compose`); `custom_app: false` met catalogus-app `ix-app` = het standaard Custom App-formulier
  (`custom_app`); andere catalogus-app → `catalog_app`; anders `onbekend`.
- **Digest:** uit het tagveld (`versie@sha256:…`) en als readback uit `app.image.query` (`repo_digests` met dezelfde
  repository). Afwijking → `readback.status = afwijking` (de executor stopt hierop in P2). Geen digest gemeten →
  `null`, nooit verzonnen.
- **Resourcegrenzen** staan in de app-configuratie; die leest de Hub nooit (kan geheimen bevatten) → `unknown`
  (`config_niet_gelezen`). Voor door de Hub geïnstalleerde apps komen ze in P2 uit het manifest.
- **Deep-link** op leestijd: NAS-adres uit D03 + portal-poort/-pad of de hostpoort van de UI-poort uit het profiel.
  Zonder D03 geen link.
- **Appstore-koppeling** alleen via het dienstenregister: `appstore-en-fork` ingeschreven, adres gemeten, dan
  `GET /catalog/v1/entries` met een dienst-JWT; koppelen op `app_id`. Anders/storing → `unknown` met reden en
  `laatst_bekend`.
- **Herkenning gerepareerd:** exacte naam wint, daarna het langste voorvoegsel (de executor werd als Hub herkend,
  `jelly-leon-platform` als `jelly-leon`); eigen diensten staan in de herkenningslijst.

### 2. Gezondheidsmodel (B09-002)
Per app componenten `truenas` (staat), `buitenkant` (Uptime Kuma) en `binnenkant` (heartbeat, connector-health §6,
worker van de Hub), elk met `observed_at` en TTL. Regels: verouderd → `unknown` (de laatste status blijft zichtbaar,
nooit herhaald als actueel); `down` wint, dan `degraded`; `RUNNING` alleen is **nooit** gezond; `healthy` vraagt een
verse gezonde buiten- óf binnenkant, en bij apps met eigen taken (`binnenkant_vereist`: Hub, eigen diensten,
MediaGuard, MSO, my_house) bovendien een verse gezonde binnenkant. Zo wordt een app die 200 geeft maar geen jobs
uitvoert `degraded` (als de binnenkant dat meldt) of `unknown` (als er geen binnenkant is) — nooit groen. Voor
MediaGuard/MSO/my_house volgt de binnenkant (read-model met gescopete sleutel, §2.3) in P3; tot dan `unknown`
(`binnenkant_niet_gebouwd`). Grace: één mislukte connector-controle = `unknown` (`eerste_fout_grace`), de tweede
= `down`. Een geweigerde credential (Kuma-key, 401 van een dienst) maakt direct `unknown` (fail-closed, EX16).

### 3. Bronnen
- **Uptime Kuma:** `/metrics` alleen met een **API-key** (Basic, wachtwoord = key; nooit een gebruikerswachtwoord) en/of
  de status-page-API (zonder aanmelding, echte hartslagtijd). Versie uit `app_version`. Statussen 1/0/2/3 →
  healthy/down/degraded/unknown (`onderhoud`). Koppeling monitor → app automatisch op (NAS-adres, hostpoort) of
  handmatig (`koppelingen`, ook expliciet `geen`).
- **Beszel:** PocketBase `auth-with-password` met een gebruiker met rol `readonly` (geen API-tokens in Beszel); het
  wachtwoord staat in de vault. **Alleen het NAS-systeem** telt (handmatig gekozen of `host` = D03); alle andere
  systemen (mini-pc, D10) zijn `uitgesloten` en leveren nooit metingen.
- **Eigen diensten:** pull van `GET /connector/v1/health` (contract §6) met dienst-JWT, plus de Hub-uitbreiding
  `POST /api/v1/monitoring/heartbeat` (service-token). De heartbeat staat **niet** in contract 1.2: diensten hoeven
  hem niet te sturen; zonder heartbeat geldt de connector-health. De heartbeat gebruikt geen `Idempotency-Key`
  (dedupe op `observed_at`, zoals de inbox op `event_id`) en heeft een rate-limit van 5 s.

### 4. GPU's en temperatuur (B09-001, B01-004)
GPU-identiteit = **PCI-slot** uit `app.gpu_choices` (stabiel), nooit de render-node. Beszel-GPU's worden alleen aan
een PCI-slot gekoppeld als een modelnummer in de naam **eenduidig** past (A310 ↔ DG2 [Arc A310], 770 ↔ UHD Graphics
770); anders geen meting en een melding `gpu_niet_toegewezen`. GPU-temperatuur levert geen bron (TrueNAS niet, Beszel
stuurt `GPUData.Temperature` niet mee) → altijd `unknown` (`niet_geleverd`), nooit 0 °C. Temperaturen ≤ 0 °C of
> 150 °C zijn ongeldig. Een eigen collector (intel_gpu_top) vraagt render-node-/root-toegang en wordt **niet** gebouwd.

### 5. Live NAS-metingen (B01-004)
`reporting.realtime` is in TrueNAS 25.10 alleen een **event source** (rol `REPORTING_READ`): de Hub opent per poll
(30 s) de WebSocket, doet `core.subscribe`, neemt het eerste `collection_update` met `fields` en zegt het abonnement
op (ook na een time-out). `core.subscribe`/`core.unsubscribe` staan op de alleen-lezen-lijst, beperkt tot een vaste
lijst events. Netwerktotaal alleen bij precies één actieve interface (bridges/VLAN's zouden dubbel tellen).
Bronvoorkeur per metriek: TrueNAS vóór Beszel; ouder dan `nas_metrics_ttl_seconds` → `unknown` met `laatst_bekend`.

### 6. Tijdreeksen (B09-003)
Tabellen `metric_series`/`metric_sample`/`metric_rollup` in de eigen PostgreSQL 16; aggregatie ruw → 5 min → 1 uur
met `date_bin` (idempotent, `ON CONFLICT DO UPDATE`); retentie per reeks (standaard 48 u / 30 d / 400 d; `app.status`
7 d ruw). Begrensd: maximaal `metrics_max_series` reeksen, alleen eindige waarden met tijdzone, niet verder dan 5 min
in de toekomst; wat buiten de grenzen valt wordt geweigerd en geteld. **Geen TimescaleDB**: de alles-in-één image
houdt de standaard PostgreSQL zonder extensie; de hoeveelheden van één NAS passen ruim.

### 7. Alerts zonder pushstorm (B09-003)
Regel = metriek + (optioneel) onderwerp/bron + operator + drempel + duur + **herstelgrens + herstelduur**
(hysterese, gevalideerd aan de veilige kant). Per onderwerp één bron (TrueNAS > Hub > Beszel > Kuma). Verouderde data
geeft **geen** overgang: een actief alert wordt nooit door ontbrekende data "hersteld". Meldingen: één rij per
overgang per kanaal (`dedupe_sleutel` uniek); dempen per alert of per regel legt de melding vast als `onderdrukt`;
herhaling alleen met `herhaal_na_s` (≥ 15 min). Standaardregels (pool vol/bijna vol/ongezond, app onbereikbaar, CPU,
CPU-temperatuur, geheugen) zijn beleid, geen NAS-gegevens, en door een beheerder aan te passen of uit te zetten.

### 8. Meldingen (Gotify, `notification.send` R0)
Alleen een **applicatietoken** (kan alleen berichten sturen) in de vault. Per kanaal rate-limit (standaard 10 per
15 min); daarboven `onderdrukt` en één samenvatting zodra er ruimte is; kritiek gaat in de wachtrij voor. Stille uren
(IANA-tijdzone) stellen niet-kritieke meldingen uit; kritiek gaat altijd door; een uitgestelde "actief"-melding van
een intussen hersteld alert vervalt (`achterhaald`). Fouten: backoff 30 s … 1 uur, na `notify_max_attempts` `mislukt`
+ outbox-event; 401/403 → kanaal `fout` en stil tot een nieuw token (geen herhaalde pogingen met een ingetrokken
token). `notification.send` is een getypte route (titel ≤ 120, bericht ≤ 2000, ernst) voor operators, met audit en
`Idempotency-Key`; de policy-engine (P2) gebruikt dezelfde adapter.

### 9. Uitgaand verkeer
`http`/`https` naar een door een beheerder ingesteld adres, nooit redirects of proxy-variabelen, 5/15 s, groottegrens
(2 MiB, `/metrics` 8 MiB), geen inloggegevens/query in het adres; loopback, link-local en `0.0.0.0`/`::` geweigerd
(ook na DNS-resolutie), behalve met de ontwikkelvlag `HUB_OUTBOUND_ALLOW_LOOPBACK` (tests). Restrisico: HTTP op het
LAN laat tokens leesbaar (zoals contract §4.7); HTTPS kan met systeem-CA's of `HUB_OUTBOUND_EXTRA_CA_FILE`.

## Gevolgen
- Nieuwe tabellen (migraties 0003–0005), nieuwe routes (OpenAPI), periodieke taken in de worker (`periodic_task`).
- De web-UI (P1-stap "web") kan alle schermen vullen uit deze API; geen nepdata nodig.
- Open/contractpunten (gemeld): heartbeat-route en `Idempotency-Key`-uitzondering niet in contract 1.2; vaste namen
  voor worker/jobs-controles in `/connector/v1/health` ontbreken (nu herkend op naam: worker, jobs, queue, wachtrij);
  resourcegrenzen niet leesbaar zonder app-configuratie; `custom_app` in `app.query` betekent compose, niet "Custom
  App-formulier".
- Alles Sim-getest; niets op een echte NAS of echte Uptime Kuma/Beszel/Gotify gevalideerd.
