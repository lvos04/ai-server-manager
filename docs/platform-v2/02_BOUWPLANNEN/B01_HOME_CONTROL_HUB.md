# Home Control Hub — volledige bouwspecificatie

**Type/eigenaar:** Nieuw project  
**Doel:** Eén volledige responsive controle- en bedieningsinterface, niet slechts linktegels.

**Afhankelijkheden:** Back-up basis; TrueNAS JSON-RPC; Authentik voor OIDC; monitoring en connectorcapabilities.

**Bron:** https://www.truenas.com/docs/scale/api/

## 1. Concrete schermen en gebruikersreizen
Home; Applicaties; App-detail; Servers; CPU/GPU/RAM; Opslag; Netwerk; Meldingen; Automatiseringen; AI-chat; Goedkeuringen; Back-ups; Updates; Gebruikers; Kosten; Instellingen

**Per scherm minimaal:** responsief (360/390/768/1440 px), status leeg/laden/storing/offline, gedocumenteerde navigatie, zoek/filter/paginering, rolcontrole, datum van laatste update, bronherkomst, fout in het Nederlands, toegankelijk toetsenbordgebruik en zichtbaar auditspoor voor wijzigingen.

## 2. Datamodel en levensduur
host, app_instance, health_sample, metric_series, incident, notification, action_request, approval, runbook, connector, connector_capability, app_release, dashboard_layout, audit_event, cost_entry

Dwing database-migraties met forward-schema-tests af; time-series met retentie/aggregatie; primaire gegevens alleen bij bron. Entiteiten krijgen stable ID, versie, eigenaar, timestamps en provenance waar toepasselijk. Secrets alleen als vault-reference.

## 3. API en integratie-contracten
GET /api/v1/home; GET /api/v1/apps; GET /api/v1/apps/{id}; GET /api/v1/metrics/query; GET /api/v1/incidents; POST /api/v1/actions/preview; POST /api/v1/approvals/{id}; GET /api/v1/events/stream

Bij alle endpoints: authenticatie, rol, inputvalidatie, idempotency voor mutaties, paginering of cursors voor lijsten, rate limits, time-outs, versie/capability-detectie en machineleesbare foutcodes. De genoemde uitbreidingsroutes zijn ontwerpeisen, niet automatisch bestaande endpoints. API-contracten moet de bouwer in OpenAPI vastleggen en e2e verifiëren.

## 4. Bouwfasen (verplichte volgorde)

### F1 - Kern en contracten
**Fase-entry:** voorafgaande kritieke gates geslaagd; bestaande gegevens en huidige release vastgelegd; rollback plan bekend.

#### B01-001 — Onboarding en nas-inventaris
**Status bij start:** Bouwen; **impact:** Hoog.
**Gewenst gedrag en grenzen:** Automatisch detecteren van TrueNAS-versie, datasets, pools, geïnstalleerde apps, image-tags, IP/netwerk, GPU-nodes, opslag en reeds aanwezige services.
**Implementatie in code/diensten:** Build TrueNAS JSON-RPC websocket adapter met schema-caps per NAS-versie; storing en ontbrekende privilege als unknown bewaren, niet stil overslaan.
**Schermen/bediening:** Wizard toont data- en netwerkzicht, alleen-lezen default en expliciet te bevestigen ontbrekende informatie.
**Acceptatie / concrete toets:** NAS zonder API-autorisatie → gerichte fout; inventaris laat bestaande MediaGuard/MSO/my_house zien zonder installatie of mutatie.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

#### B01-002 — Centrale appcatalogus
**Status bij start:** Bouwen; **impact:** Middel.
**Gewenst gedrag en grenzen:** Alle apps tonen met status, versie, uptime, opslag, health, rechten, eigenaar, documentatie en exacte herkomst.
**Implementatie in code/diensten:** Registry met adaptertype, runtime_id, tag/digest, metadata, link en laatst getest; import bestaande apps met idempotent discovery.
**Schermen/bediening:** Zoekbare catalogus, filters, status, knoppen open/logs/herstart alleen bij privilege.
**Acceptatie / concrete toets:** Na NAS reboot blijft app identiteit gelijk; app offline krijgt stale timestamp, niet gezond.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

**Fase-exit:** alle in deze fase genoemde checks aantoonbaar geslaagd, code review, back-up-/rollback-gate, een gebruikersreis op mobiel en een negatieve test voor permissions. Bij een blocker niets forceren: status `Geblokkeerd` + reden + eigenaar.

### F2 - Functionaliteit
**Fase-entry:** voorafgaande kritieke gates geslaagd; bestaande gegevens en huidige release vastgelegd; rollback plan bekend.

#### B01-003 — Apps installeren en verwijderen
**Status bij start:** Bouwen; **impact:** Hoog.
**Gewenst gedrag en grenzen:** Installatie vanuit goedgekeurde manifests; installatie vereist preview van images, mounts, netwerken, secrets, CPU/GPU en dataretentie.
**Implementatie in code/diensten:** Manifest schema, signature/digest check, conflictanalyse, deploy via privileged executor; uninstall standaard container-only, data alleen apart expliciet.
**Schermen/bediening:** Installatiewizard met diff, preflight, approvals en rollback-knop.
**Acceptatie / concrete toets:** Een manifest met host network/privileged zonder reden faalt; geen datasetdelete bij uninstallen.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

#### B01-004 — Observability in één scherm
**Status bij start:** Bouwen; **impact:** Middel.
**Gewenst gedrag en grenzen:** CPU/i7 threads, RAM/ZFS ARC, A310/UHD 770, disks/pool health, netwerk, app health, taken en trendgrafieken.
**Implementatie in code/diensten:** Read-only adapters Beszel/Uptime Kuma/TrueNAS; tijdreeks in beperkte retention, units normalized; capability flags voor ontbrekende GPU-stat.
**Schermen/bediening:** Live dashboard met historische periode, freshness en per-metric provenance.
**Acceptatie / concrete toets:** Stale bron >TTL wordt unknown; GPU wisseling van render node verwisselt A310 en iGPU niet.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

#### B01-005 — Incidenten-inbox
**Status bij start:** Bouwen; **impact:** Middel.
**Gewenst gedrag en grenzen:** Alle relevante alerts op één plaats, groepering op root cause, deduplicatie, severity, acknowledged/snoozed/resolved.
**Implementatie in code/diensten:** Events via poll/webhook/outbox, correlation by host/service/entity/trace; retry en DLQ; systeemalerts missen geen herstelmelding.
**Schermen/bediening:** Inbox per prioriteit met bewijs, laatste verandering, bron en aan te vragen remedie.
**Acceptatie / concrete toets:** 100 identieke app-crashes → één doorlopend incident; herstel sluit niet onterecht gerelateerd incident.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

**Fase-exit:** alle in deze fase genoemde checks aantoonbaar geslaagd, code review, back-up-/rollback-gate, een gebruikersreis op mobiel en een negatieve test voor permissions. Bij een blocker niets forceren: status `Geblokkeerd` + reden + eigenaar.

### F3 - Integraties en veiligheid
**Fase-entry:** voorafgaande kritieke gates geslaagd; bestaande gegevens en huidige release vastgelegd; rollback plan bekend.

#### B01-006 — Gebruikers en SSO
**Status bij start:** Bouwen; **impact:** Hoog.
**Gewenst gedrag en grenzen:** OIDC login voor Hub; bestaande apps met ondersteunde SSO koppelen; niet-ondersteunde apps via eigen veilige login.
**Implementatie in code/diensten:** Authentik OIDC code + PKCE, rollen admin/operator/viewer, korte websessies, secure cookies/CSRF, permission adapter.
**Schermen/bediening:** Eén login naar Hub, per app status SSO wel/niet, sessies en intrekken.
**Acceptatie / concrete toets:** Een viewer kan nooit update/stop of export secrets; logout/sessie-intrekking werkt na revocation.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

#### B01-007 — Beheers-API en approvals
**Status bij start:** Bouwen; **impact:** Hoog.
**Gewenst gedrag en grenzen:** Acties verschijnen nooit rechtstreeks vanuit frontend bij TrueNAS of Docker; elke wijziging via voorstel/permission gate.
**Implementatie in code/diensten:** Action request met preview hash + target resource ETag + time-bound approval; dispatch to isolated executor.
**Schermen/bediening:** Goedkeuringsscherm met diffs, back-upstatus, impact, rollback en automatische expiry.
**Acceptatie / concrete toets:** Bij gewijzigde appversie tussen preview/approval opnieuw goedkeuren.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

**Fase-exit:** alle in deze fase genoemde checks aantoonbaar geslaagd, code review, back-up-/rollback-gate, een gebruikersreis op mobiel en een negatieve test voor permissions. Bij een blocker niets forceren: status `Geblokkeerd` + reden + eigenaar.

### F4 - Automatisering
**Fase-entry:** voorafgaande kritieke gates geslaagd; bestaande gegevens en huidige release vastgelegd; rollback plan bekend.

#### B01-008 — Automatiseringen zonder code
**Status bij start:** Bouwen; **impact:** Middel.
**Gewenst gedrag en grenzen:** Visuele flows voor app-/media-/smart-home-gebeurtenissen, met testmodus en veiligheidsgrenzen.
**Implementatie in code/diensten:** Node-RED beheert canvas; Hub verwelkomt read-only event nodes, policy-bound action nodes, scopes, loop-detectie.
**Schermen/bediening:** Flow-editor, testconsole, geschiedenis, pause, templates, triggervoorwaarden.
**Acceptatie / concrete toets:** Flow kan geen ongeautoriseerde shellcode of boilercommando uitvoeren.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

#### B01-009 — Globale AI-chat
**Status bij start:** Bouwen; **impact:** Hoog.
**Gewenst gedrag en grenzen:** Natuurlijke taal voor uitlezen en plannen; schrijft alleen via action request, never tool call direct.
**Implementatie in code/diensten:** Toolregistry met schema, read model, role check, context redaction, citation/evidence and preview.
**Schermen/bediening:** Chat toont bronnen, exact plan en status per actie plus buttons goedkeuren/weigeren.
**Acceptatie / concrete toets:** Prompt injection in logline kan geen privileged action veroorzaken.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

**Fase-exit:** alle in deze fase genoemde checks aantoonbaar geslaagd, code review, back-up-/rollback-gate, een gebruikersreis op mobiel en een negatieve test voor permissions. Bij een blocker niets forceren: status `Geblokkeerd` + reden + eigenaar.

### F5 - Hardening & UX
**Fase-entry:** voorafgaande kritieke gates geslaagd; bestaande gegevens en huidige release vastgelegd; rollback plan bekend.

#### B01-010 — App update en rollback-centrum
**Status bij start:** Bouwen; **impact:** Hoog.
**Gewenst gedrag en grenzen:** Versies uit upstream/eigen GitHub monitoren, changelog tonen, migrations-risk bepalen, testdeployment en rollback.
**Implementatie in code/diensten:** Release watcher met pins, content digest, canary copy, DB backup lock, post-deploy health window.
**Schermen/bediening:** Versieverschil, nieuwe functies, risico, down-time, bevestiging en provenance.
**Acceptatie / concrete toets:** DB schema incompatibility blokkeert tag-only rollback; volledig herstelplan toont dataset+DB.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

#### B01-011 — Energie en kosten
**Status bij start:** Bouwen; **impact:** Middel.
**Gewenst gedrag en grenzen:** Stroominschattingen per NAS/app uitsluitend waar daadwerkelijk gemeten of verantwoord afgeleid; externe dienstkosten zonder dubbeltelling.
**Implementatie in code/diensten:** Ingest my_house stroommeter, metrics van host, MSO diensten en cloudbudget; measurement quality measured/estimated/unknown.
**Schermen/bediening:** Dag/week/maand grafiek; duidelijk bron en meetdekking; budgetwaarschuwing.
**Acceptatie / concrete toets:** Geen gemeten airco energie presenteren als specifiek binnenunit-verbruik.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

**Fase-exit:** alle in deze fase genoemde checks aantoonbaar geslaagd, code review, back-up-/rollback-gate, een gebruikersreis op mobiel en een negatieve test voor permissions. Bij een blocker niets forceren: status `Geblokkeerd` + reden + eigenaar.

### F6 - Release en nazorg
**Fase-entry:** voorafgaande kritieke gates geslaagd; bestaande gegevens en huidige release vastgelegd; rollback plan bekend.

#### B01-012 — Portable export en recovery
**Status bij start:** Bouwen; **impact:** Hoog.
**Gewenst gedrag en grenzen:** Beheerdashboard kan naar andere NAS verhuizen met config, audit, gebruikers, appcatalogus en connectorrelaties.
**Implementatie in code/diensten:** Encrypt export + versioned schema + restore in isolated environment; reconnect wizard; no hardcoded IP.
**Schermen/bediening:** Herstelwizard met dry-run of alles aanwezig is en geen credentials onbeveiligd delen.
**Acceptatie / concrete toets:** Herstel op lege testinstance creëert geen dubbele apps en behoudt auditgeschiedenis.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

**Fase-exit:** alle in deze fase genoemde checks aantoonbaar geslaagd, code review, back-up-/rollback-gate, een gebruikersreis op mobiel en een negatieve test voor permissions. Bij een blocker niets forceren: status `Geblokkeerd` + reden + eigenaar.

## 5. Niet-regressie, randgevallen en verbodsbepalingen
UI moet voortbouwen op rustig, mobielvriendelijk ontwerp van eigen MediaGuard/MSO/my_house, zonder hun UI-techniek blind te kopiëren. Publieke interface nooit direct met Docker socket delen. Eén nieuwe Hub projectrepository, eigen DB en geen verplichte eigen chatbot om basisfuncties te laten werken.

## 6. Oplevering door bouwer
Opleveren: (1) broncode en tests, (2) migration scripts en versiecompatibiliteit, (3) Compose/TrueNAS app manifest met gepinde images, (4) .env.example zonder geheimen, (5) OpenAPI/connector schemas, (6) test- en auditrapport, (7) restore bewijs, (8) release notes, (9) gebruikershandleiding, (10) screenshots web/mobiel. Markeer niet-geteste hardware/echte accounts als `NIET GEVALIDEERD`.

## 7. Proof of Done
Alle acceptatiecriteria in Excel zijn gekoppeld aan testbewijs en codecommit; bij stroomonderbreking, uitval van afhankelijke app, NAS-herstart, gewijzigde credentials en incompatibele versie degradeert de service aantoonbaar veilig. Geen directe writes aan de database van een andere app.
