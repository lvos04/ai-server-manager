# Back-ups en herstel — volledige bouwspecificatie

**Type/eigenaar:** TrueNAS, ZFS en OneDrive-integratie  
**Doel:** Bevestig herstelbaarheid van foto’s/appdbs en voeg snapshots, herstelchecks en pre-change gates toe.

**Afhankelijkheden:** Bestaande OneDrive, ZFS, Authentik, alle databaseapps.

**Bron:** https://www.truenas.com/docs/

## 1. Concrete schermen en gebruikersreizen
Back-ups; Status; Datasets; Snapshotplanning; Offsite; Restoreproeven; Alerts; Sleutels; Kosten/opslag

**Per scherm minimaal:** responsief (360/390/768/1440 px), status leeg/laden/storing/offline, gedocumenteerde navigatie, zoek/filter/paginering, rolcontrole, datum van laatste update, bronherkomst, fout in het Nederlands, toegankelijk toetsenbordgebruik en zichtbaar auditspoor voor wijzigingen.

## 2. Datamodel en levensduur
backup_source, backup_set, snapshot, offsite_transfer, verification, restore_test, recovery_key, backup_policy, retention_rule

Dwing database-migraties met forward-schema-tests af; time-series met retentie/aggregatie; primaire gegevens alleen bij bron. Entiteiten krijgen stable ID, versie, eigenaar, timestamps en provenance waar toepasselijk. Secrets alleen als vault-reference.

## 3. API en integratie-contracten
TrueNAS dataset/snapshot API; bestaande OneDrive workflow audit; restic/rclone optioneel uitsluitend na bron/doel-check

Bij alle endpoints: authenticatie, rol, inputvalidatie, idempotency voor mutaties, paginering of cursors voor lijsten, rate limits, time-outs, versie/capability-detectie en machineleesbare foutcodes. De genoemde uitbreidingsroutes zijn ontwerpeisen, niet automatisch bestaande endpoints. API-contracten moet de bouwer in OpenAPI vastleggen en e2e verifiëren.

## 4. Bouwfasen (verplichte volgorde)

### F0 - Inventaris & onderzoek
**Fase-entry:** voorafgaande kritieke gates geslaagd; bestaande gegevens en huidige release vastgelegd; rollback plan bekend.

#### B12-001 — Bestaande OneDrive controle
**Status bij start:** Controleren; **impact:** Hoog.
**Gewenst gedrag en grenzen:** Check welke foto's/DB exports, hoe vaak, via welke software, versiegeschiedenis, encryptie, herstelbare sleutel en update na wijziging.
**Implementatie in code/diensten:** Inventariseer jobs, controleer logs/checksums, test download van oud punt.
**Schermen/bediening:** Dekkingsmatrix per dataset en bestandtype.
**Acceptatie / concrete toets:** Minimaal één echte foto en één appdb teruggezet naar geïsoleerde omgeving.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

**Fase-exit:** alle in deze fase genoemde checks aantoonbaar geslaagd, code review, back-up-/rollback-gate, een gebruikersreis op mobiel en een negatieve test voor permissions. Bij een blocker niets forceren: status `Geblokkeerd` + reden + eigenaar.

### F1 - Kern en contracten
**Fase-entry:** voorafgaande kritieke gates geslaagd; bestaande gegevens en huidige release vastgelegd; rollback plan bekend.

#### B12-002 — Snapshotbeleid
**Status bij start:** Bouwen; **impact:** Hoog.
**Gewenst gedrag en grenzen:** Automatische ZFS appdata snapshots plus snapshot vóór deployment/schema update, met ruimtebudget.
**Implementatie in code/diensten:** Retention per dataset, lock before app writes, warn pool usage; consistent app DB export.
**Schermen/bediening:** Snapshots met effect en laatste succesvolle ronde.
**Acceptatie / concrete toets:** Snapshot zonder DB consistentie mag niet als volledige appback-up tellen.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

#### B12-003 — App-consistent exports
**Status bij start:** Bouwen; **impact:** Hoog.
**Gewenst gedrag en grenzen:** PostgreSQL logical dump, SQLite backup API, secrets escrow en manifest; veiligheidsregels per app.
**Implementatie in code/diensten:** Owner aware backups, evidence hash, encrypt, offsite key separation.
**Schermen/bediening:** Component per app in backuprapport.
**Acceptatie / concrete toets:** MSO en my_house database kunnen onafhankelijk in teststack starten.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

**Fase-exit:** alle in deze fase genoemde checks aantoonbaar geslaagd, code review, back-up-/rollback-gate, een gebruikersreis op mobiel en een negatieve test voor permissions. Bij een blocker niets forceren: status `Geblokkeerd` + reden + eigenaar.

### F2 - Functionaliteit
**Fase-entry:** voorafgaande kritieke gates geslaagd; bestaande gegevens en huidige release vastgelegd; rollback plan bekend.

#### B12-004 — OneDrive-verificatie
**Status bij start:** Bouwen; **impact:** Middel.
**Gewenst gedrag en grenzen:** Bevestig bestaande schedule en herstel zonder een nieuwe OneDrive-opslagdienst aan te maken.
**Implementatie in code/diensten:** If rclone/restic already used, manage config by API or CLI with least permission; store encrypted independent key.
**Schermen/bediening:** Offsite timestamp, count, source map, errors.
**Acceptatie / concrete toets:** Stale upload/expired auth → high-priority alert.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

**Fase-exit:** alle in deze fase genoemde checks aantoonbaar geslaagd, code review, back-up-/rollback-gate, een gebruikersreis op mobiel en een negatieve test voor permissions. Bij een blocker niets forceren: status `Geblokkeerd` + reden + eigenaar.

### F3 - Integraties en veiligheid
**Fase-entry:** voorafgaande kritieke gates geslaagd; bestaande gegevens en huidige release vastgelegd; rollback plan bekend.

#### B12-005 — Restore-test robot
**Status bij start:** Bouwen; **impact:** Hoog.
**Gewenst gedrag en grenzen:** Op geïsoleerde testdataset/stack routine DB import en check critical data; nooit productie overschrijven.
**Implementatie in code/diensten:** Create temp dataset with timebound ACL, checksum scan, boot app in isolated network, results then wipe test data with approval.
**Schermen/bediening:** Testresultaat geslaagd/partial/mislukt met bewijs.
**Acceptatie / concrete toets:** Failing checksum mark unhealthy; geen productie database gewijzigd.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

**Fase-exit:** alle in deze fase genoemde checks aantoonbaar geslaagd, code review, back-up-/rollback-gate, een gebruikersreis op mobiel en een negatieve test voor permissions. Bij een blocker niets forceren: status `Geblokkeerd` + reden + eigenaar.

### F4 - Automatisering
**Fase-entry:** voorafgaande kritieke gates geslaagd; bestaande gegevens en huidige release vastgelegd; rollback plan bekend.

#### B12-006 — Pre-update gate
**Status bij start:** Bouwen; **impact:** Hoog.
**Gewenst gedrag en grenzen:** Elke R2/R3 change heeft vers back-up/restore evidence en plan.
**Implementatie in code/diensten:** Policy engine queries backup controller and enforces freshness thresholds.
**Schermen/bediening:** Approval pane toont concrete recovery point IDs.
**Acceptatie / concrete toets:** Zonder herstelpunt niet deployen; operator kan gate niet wegklikken.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

**Fase-exit:** alle in deze fase genoemde checks aantoonbaar geslaagd, code review, back-up-/rollback-gate, een gebruikersreis op mobiel en een negatieve test voor permissions. Bij een blocker niets forceren: status `Geblokkeerd` + reden + eigenaar.

### F5 - Hardening & UX
**Fase-entry:** voorafgaande kritieke gates geslaagd; bestaande gegevens en huidige release vastgelegd; rollback plan bekend.

#### B12-007 — Rampenscenario
**Status bij start:** Bouwen; **impact:** Middel.
**Gewenst gedrag en grenzen:** Scenario poolverlies, credential leak, foutieve appmigratie, rollback van MediaGuard en home move.
**Implementatie in code/diensten:** Write step-by-step runbooks + quarterly rehearsal and RPO/RTO measured.
**Schermen/bediening:** Herstelstappen per app en na-test.
**Acceptatie / concrete toets:** Rehearsal op andere hardware/teststack zonder originele NAS.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

**Fase-exit:** alle in deze fase genoemde checks aantoonbaar geslaagd, code review, back-up-/rollback-gate, een gebruikersreis op mobiel en een negatieve test voor permissions. Bij een blocker niets forceren: status `Geblokkeerd` + reden + eigenaar.

## 5. Niet-regressie, randgevallen en verbodsbepalingen
ZFS-snapshot is geen offsite back-up. OneDrive huidige fotos en appdbs zijn niet hetzelfde als volledige recovery van NAS, credentials of apps.

## 6. Oplevering door bouwer
Opleveren: (1) broncode en tests, (2) migration scripts en versiecompatibiliteit, (3) Compose/TrueNAS app manifest met gepinde images, (4) .env.example zonder geheimen, (5) OpenAPI/connector schemas, (6) test- en auditrapport, (7) restore bewijs, (8) release notes, (9) gebruikershandleiding, (10) screenshots web/mobiel. Markeer niet-geteste hardware/echte accounts als `NIET GEVALIDEERD`.

## 7. Proof of Done
Alle acceptatiecriteria in Excel zijn gekoppeld aan testbewijs en codecommit; bij stroomonderbreking, uitval van afhankelijke app, NAS-herstart, gewijzigde credentials en incompatibele versie degradeert de service aantoonbaar veilig. Geen directe writes aan de database van een andere app.
