# Monitoring & incidentrespons — volledige bouwspecificatie

**Type/eigenaar:** Integratie: Beszel + Uptime Kuma + TrueNAS  
**Doel:** Een betrouwbare meetlaag en alert-/herstelpijplijn die werkt ook als de Hub of AI down is.

**Afhankelijkheden:** Hub, Beszel, Uptime Kuma, Gotify.

**Bron:** https://github.com/henrygd/beszel

## 1. Concrete schermen en gebruikersreizen
Metrieken; Services; Incidenten; SLO; Logs; Sensoren; Backups; GPU; ZFS; Traces

**Per scherm minimaal:** responsief (360/390/768/1440 px), status leeg/laden/storing/offline, gedocumenteerde navigatie, zoek/filter/paginering, rolcontrole, datum van laatste update, bronherkomst, fout in het Nederlands, toegankelijk toetsenbordgebruik en zichtbaar auditspoor voor wijzigingen.

## 2. Datamodel en levensduur
metric, metric_source, health_probe, probe_result, alert_rule, incident, incident_event, acknowledgement, maintenance_window, alert_channel

Dwing database-migraties met forward-schema-tests af; time-series met retentie/aggregatie; primaire gegevens alleen bij bron. Entiteiten krijgen stable ID, versie, eigenaar, timestamps en provenance waar toepasselijk. Secrets alleen als vault-reference.

## 3. API en integratie-contracten
Beszel Hub API/agent; Uptime Kuma event/status read where supported; TrueNAS JSON-RPC; Hub event endpoint

Bij alle endpoints: authenticatie, rol, inputvalidatie, idempotency voor mutaties, paginering of cursors voor lijsten, rate limits, time-outs, versie/capability-detectie en machineleesbare foutcodes. De genoemde uitbreidingsroutes zijn ontwerpeisen, niet automatisch bestaande endpoints. API-contracten moet de bouwer in OpenAPI vastleggen en e2e verifiëren.

## 4. Bouwfasen (verplichte volgorde)

### F0 - Inventaris & onderzoek
**Fase-entry:** voorafgaande kritieke gates geslaagd; bestaande gegevens en huidige release vastgelegd; rollback plan bekend.

#### B09-001 — Metrics coverage
**Status bij start:** Bouwen; **impact:** Middel.
**Gewenst gedrag en grenzen:** Inventariseer wat TrueNAS API en Beszel daadwerkelijk leveren voor i7, ZFS ARC, disks, GPU, Docker en netwerk.
**Implementatie in code/diensten:** Adapter capability flag; alternative collector voor ontbrekende intel_gpu_top; niet onnodig privileged.
**Schermen/bediening:** Meetdekking met onbekende velden.
**Acceptatie / concrete toets:** A310 en UHD 770 juist onderscheiden; missing GPU temp niet 0C tonen.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

**Fase-exit:** alle in deze fase genoemde checks aantoonbaar geslaagd, code review, back-up-/rollback-gate, een gebruikersreis op mobiel en een negatieve test voor permissions. Bij een blocker niets forceren: status `Geblokkeerd` + reden + eigenaar.

### F1 - Kern en contracten
**Fase-entry:** voorafgaande kritieke gates geslaagd; bestaande gegevens en huidige release vastgelegd; rollback plan bekend.

#### B09-002 — App healthchecks
**Status bij start:** Bouwen; **impact:** Middel.
**Gewenst gedrag en grenzen:** Monitor zowel buitenkant URL als binnenkant health en worker heartbeat.
**Implementatie in code/diensten:** Uptime Kuma probes and app-specific health contract with grace thresholds.
**Schermen/bediening:** Up/down, latency, last 24h, method, link logs.
**Acceptatie / concrete toets:** App die 200 teruggeeft maar geen jobs uitvoert is degraded.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

**Fase-exit:** alle in deze fase genoemde checks aantoonbaar geslaagd, code review, back-up-/rollback-gate, een gebruikersreis op mobiel en een negatieve test voor permissions. Bij een blocker niets forceren: status `Geblokkeerd` + reden + eigenaar.

### F2 - Functionaliteit
**Fase-entry:** voorafgaande kritieke gates geslaagd; bestaande gegevens en huidige release vastgelegd; rollback plan bekend.

#### B09-003 — Time-series en alerts
**Status bij start:** Bouwen; **impact:** Middel.
**Gewenst gedrag en grenzen:** Beszel metrics naar Hub, burn rate/disk pressure, ZFS pool degraded en inactive jobs.
**Implementatie in code/diensten:** Store bounded normalized samples, retention per metric, aggregated history, threshold + debounce.
**Schermen/bediening:** Grafieken en incidenttrends.
**Acceptatie / concrete toets:** Prometheusachtige testload veroorzaakt geen alert storm.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

**Fase-exit:** alle in deze fase genoemde checks aantoonbaar geslaagd, code review, back-up-/rollback-gate, een gebruikersreis op mobiel en een negatieve test voor permissions. Bij een blocker niets forceren: status `Geblokkeerd` + reden + eigenaar.

### F3 - Integraties en veiligheid
**Fase-entry:** voorafgaande kritieke gates geslaagd; bestaande gegevens en huidige release vastgelegd; rollback plan bekend.

#### B09-004 — Logs en correlatie
**Status bij start:** Bouwen; **impact:** Middel.
**Gewenst gedrag en grenzen:** Systeem en app logs geredigeerd, gestructureerd en gekoppeld aan incident.
**Implementatie in code/diensten:** Read-only log sink and trace IDs; secret/IP masking by policy, size and retention bounds.
**Schermen/bediening:** Zoeken op incident/app/time en kopiëren van gemaskeerde supportbundle.
**Acceptatie / concrete toets:** Geheimen niet in index of AI-telemetrie.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

**Fase-exit:** alle in deze fase genoemde checks aantoonbaar geslaagd, code review, back-up-/rollback-gate, een gebruikersreis op mobiel en een negatieve test voor permissions. Bij een blocker niets forceren: status `Geblokkeerd` + reden + eigenaar.

### F4 - Automatisering
**Fase-entry:** voorafgaande kritieke gates geslaagd; bestaande gegevens en huidige release vastgelegd; rollback plan bekend.

#### B09-005 — Out-of-band melding
**Status bij start:** Bouwen; **impact:** Middel.
**Gewenst gedrag en grenzen:** Gotify/Uptime Kuma alarmeert los van Hub zodat Hub-falen zichtbaar blijft.
**Implementatie in code/diensten:** Independent service checks + phone push, escalation with acknowledgement expiry.
**Schermen/bediening:** Prioriteitsregels en testmelding.
**Acceptatie / concrete toets:** Stop Hub → Uptime Kuma alert werkt nog steeds.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

**Fase-exit:** alle in deze fase genoemde checks aantoonbaar geslaagd, code review, back-up-/rollback-gate, een gebruikersreis op mobiel en een negatieve test voor permissions. Bij een blocker niets forceren: status `Geblokkeerd` + reden + eigenaar.

### F5 - Hardening & UX
**Fase-entry:** voorafgaande kritieke gates geslaagd; bestaande gegevens en huidige release vastgelegd; rollback plan bekend.

#### B09-006 — Operator runbooks
**Status bij start:** Bouwen; **impact:** Middel.
**Gewenst gedrag en grenzen:** Elke storing heeft mitigatie en test na herstel, niet automatisch permanent opgelost op open TCP.
**Implementatie in code/diensten:** Typed runbook templates in policy engine.
**Schermen/bediening:** Incidentknop ‘Onderzoek’ en ‘Herstel voorstellen’.
**Acceptatie / concrete toets:** Herhaald app-falen → safe mode en geen endless restart.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

**Fase-exit:** alle in deze fase genoemde checks aantoonbaar geslaagd, code review, back-up-/rollback-gate, een gebruikersreis op mobiel en een negatieve test voor permissions. Bij een blocker niets forceren: status `Geblokkeerd` + reden + eigenaar.

## 5. Niet-regressie, randgevallen en verbodsbepalingen
Beszel GPU/support afhankelijk van kernel drivers; verzamel indien nodig aparte, rechtenbeperkte exporter. Geen volledige logging van cloud- of privésleutels.

## 6. Oplevering door bouwer
Opleveren: (1) broncode en tests, (2) migration scripts en versiecompatibiliteit, (3) Compose/TrueNAS app manifest met gepinde images, (4) .env.example zonder geheimen, (5) OpenAPI/connector schemas, (6) test- en auditrapport, (7) restore bewijs, (8) release notes, (9) gebruikershandleiding, (10) screenshots web/mobiel. Markeer niet-geteste hardware/echte accounts als `NIET GEVALIDEERD`.

## 7. Proof of Done
Alle acceptatiecriteria in Excel zijn gekoppeld aan testbewijs en codecommit; bij stroomonderbreking, uitval van afhankelijke app, NAS-herstart, gewijzigde credentials en incompatibele versie degradeert de service aantoonbaar veilig. Geen directe writes aan de database van een andere app.
