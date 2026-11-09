# AI Server Manager — volledige bouwspecificatie

**Type/eigenaar:** Nieuw subsysteem in Hub  
**Doel:** Veilige autonome beheeragent met echte diagnose, detectie, uitvoerbare runbooks en bewijsgestuurde terugval.

**Afhankelijkheden:** Home Control Hub, monitoring, back-ups, risk policy.

**Bron:** https://platform.claude.com/docs/en/about-claude/api-credits-for-subscribers

## 1. Concrete schermen en gebruikersreizen
AI-overzicht; Chat; Actievoorstellen; Risicoprofielen; Runbooks; Taken; Kosten en tokens; Audit; Evaluatie; Noodstop

**Per scherm minimaal:** responsief (360/390/768/1440 px), status leeg/laden/storing/offline, gedocumenteerde navigatie, zoek/filter/paginering, rolcontrole, datum van laatste update, bronherkomst, fout in het Nederlands, toegankelijk toetsenbordgebruik en zichtbaar auditspoor voor wijzigingen.

## 2. Datamodel en levensduur
model_provider, model_policy, credential_ref, budget_cap, tool_capability, context_record, diagnosis, evidence, action_plan, action_step, risk_rating, approval, execution, rollback, evaluation, incident

Dwing database-migraties met forward-schema-tests af; time-series met retentie/aggregatie; primaire gegevens alleen bij bron. Entiteiten krijgen stable ID, versie, eigenaar, timestamps en provenance waar toepasselijk. Secrets alleen als vault-reference.

## 3. API en integratie-contracten
POST /api/v1/ai/diagnose; POST /api/v1/ai/plan; GET /api/v1/ai/providers; POST /api/v1/action-requests; POST /api/v1/actions/{id}/approve; GET /api/v1/ai/audit

Bij alle endpoints: authenticatie, rol, inputvalidatie, idempotency voor mutaties, paginering of cursors voor lijsten, rate limits, time-outs, versie/capability-detectie en machineleesbare foutcodes. De genoemde uitbreidingsroutes zijn ontwerpeisen, niet automatisch bestaande endpoints. API-contracten moet de bouwer in OpenAPI vastleggen en e2e verifiëren.

## 4. Bouwfasen (verplichte volgorde)

### F0 - Inventaris & onderzoek
**Fase-entry:** voorafgaande kritieke gates geslaagd; bestaande gegevens en huidige release vastgelegd; rollback plan bekend.

#### B02-001 — Modelrechten en kosten
**Status bij start:** Bouwen; **impact:** Hoog.
**Gewenst gedrag en grenzen:** Claude Max bestaande inbegrepen maandelijkse API-credits, indien gekoppeld/claimbaar; ChatGPT Plus niet misbruiken als gratis API; geen overage.
**Implementatie in code/diensten:** Config gated account connection; balance/spend tracking, max_cost_per_job, monthly hard stop, offline fallback; no stealth fallback to paid API.
**Schermen/bediening:** Providerkaart met beschikbare credits, herkomst, gekozen model, kosten per taak, uitgeschakeld bij limiet.
**Acceptatie / concrete toets:** 0 credits → geen externe LLM-aanroepen maar deterministic alerts; bewijs zonder billing overschrijding.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

**Fase-exit:** alle in deze fase genoemde checks aantoonbaar geslaagd, code review, back-up-/rollback-gate, een gebruikersreis op mobiel en een negatieve test voor permissions. Bij een blocker niets forceren: status `Geblokkeerd` + reden + eigenaar.

### F1 - Kern en contracten
**Fase-entry:** voorafgaande kritieke gates geslaagd; bestaande gegevens en huidige release vastgelegd; rollback plan bekend.

#### B02-002 — Read-only kennisinstrumenten
**Status bij start:** Bouwen; **impact:** Hoog.
**Gewenst gedrag en grenzen:** Toegang tot TrueNAS, incidenten, Beszel, Uptime Kuma, MediaGuard/MSO/my_house, netwerkevents volgens rol.
**Implementatie in code/diensten:** Tool schemas met permissions, data classification en output length bounds; retrieval freshness + source evidence.
**Schermen/bediening:** Diagnose met citaten naar lokale logs/metrics, timestamps en twijfel.
**Acceptatie / concrete toets:** Misleidende logregels als prompts worden niet uitgevoerd.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

#### B02-003 — Deterministische triage
**Status bij start:** Bouwen; **impact:** Middel.
**Gewenst gedrag en grenzen:** Automatische incidentclassificatie zonder LLM waar mogelijk: crashed container, disk nearly full, bad backup, AV1 stall, authentication failures.
**Implementatie in code/diensten:** Rules engine met alert correlation, rolling windows, severity; LLM pas bij complexiteit/onzekerheid.
**Schermen/bediening:** Incident met drempelwaarden, historiek en oorzaakhypothesen.
**Acceptatie / concrete toets:** 100 events → één ticket; een bewuste AV1-pauze geeft geen crashalarm.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

**Fase-exit:** alle in deze fase genoemde checks aantoonbaar geslaagd, code review, back-up-/rollback-gate, een gebruikersreis op mobiel en een negatieve test voor permissions. Bij een blocker niets forceren: status `Geblokkeerd` + reden + eigenaar.

### F2 - Functionaliteit
**Fase-entry:** voorafgaande kritieke gates geslaagd; bestaande gegevens en huidige release vastgelegd; rollback plan bekend.

#### B02-004 — Plan-engine en analyse
**Status bij start:** Bouwen; **impact:** Hoog.
**Gewenst gedrag en grenzen:** AI formuleert stappen, gevolgen, preconditions, alternatieven en rollback; plannen vereisen schema-validatie.
**Implementatie in code/diensten:** Structured JSON to typed plan, evidence_refs, capabilities, uncertainty; disallow free shell and unregistered actions.
**Schermen/bediening:** Preview met risico en exacte bestemming, knop simuleren en goedkeuren.
**Acceptatie / concrete toets:** Onbekend action_id of buiten-scope target → 422 en geen uitvoering.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

#### B02-005 — Risicoclassificatie
**Status bij start:** Bouwen; **impact:** Hoog.
**Gewenst gedrag en grenzen:** R0 lezen; R1 kleine omkeerbare reparatie; R2 infrastrucuur en downtime; R3 destructief/privilege/financieel.
**Implementatie in code/diensten:** Hard policy separate process with allowlist + max frequency, dataset protection, canary, TTL; policy edits require manual admin.
**Schermen/bediening:** Risicobadge niet decoratief maar onderbouwde categorie, blokkadereden.
**Acceptatie / concrete toets:** LLM kiest R0 voor dataset destroy → server classificeert R3 en weigert.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

**Fase-exit:** alle in deze fase genoemde checks aantoonbaar geslaagd, code review, back-up-/rollback-gate, een gebruikersreis op mobiel en een negatieve test voor permissions. Bij een blocker niets forceren: status `Geblokkeerd` + reden + eigenaar.

### F3 - Integraties en veiligheid
**Fase-entry:** voorafgaande kritieke gates geslaagd; bestaande gegevens en huidige release vastgelegd; rollback plan bekend.

#### B02-006 — Privileged executor
**Status bij start:** Bouwen; **impact:** Hoog.
**Gewenst gedrag en grenzen:** Specifieke acties zoals app.restart, app.healthcheck, zfs.snapshot.create, backup.verify; nooit generieke remote-root shell.
**Implementatie in code/diensten:** Small service with Unix socket/API, per-action identity, user-link NAS key over HTTPS, dry run, timeouts and audit.
**Schermen/bediening:** Uitvoerverloop inclusief voor/na-state en reden.
**Acceptatie / concrete toets:** Front-end of toolprompt kan niet rechtstreeks naar docker.sock/sudo; executor weigert onbekende acties.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

#### B02-007 — Veilige zelfreparatie
**Status bij start:** Bouwen; **impact:** Middel.
**Gewenst gedrag en grenzen:** Na bewezen crash mag één beperkte containerherstart met cooldown, verify en rollback/incident-escalatie.
**Implementatie in code/diensten:** Retry budget and circuit breaker; expected app identity/digest; preserve no restart for storage, DB migration, WAN.
**Schermen/bediening:** Herstelreeks met aantal pogingen, definitieve status en melding.
**Acceptatie / concrete toets:** Crashloop na 2 pogingen stopt; operator krijgt oorzaak en geen eindeloze loop.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

**Fase-exit:** alle in deze fase genoemde checks aantoonbaar geslaagd, code review, back-up-/rollback-gate, een gebruikersreis op mobiel en een negatieve test voor permissions. Bij een blocker niets forceren: status `Geblokkeerd` + reden + eigenaar.

### F4 - Automatisering
**Fase-entry:** voorafgaande kritieke gates geslaagd; bestaande gegevens en huidige release vastgelegd; rollback plan bekend.

#### B02-008 — Updates en config verbeteringen
**Status bij start:** Bouwen; **impact:** Hoog.
**Gewenst gedrag en grenzen:** AI mag code/configchanges voorstellen via aparte PR en testomgeving, niet direct live productie configuratie aanpassen.
**Implementatie in code/diensten:** Worktree isolated runner, GitHub PR, CI logs, review, artifact diff, rollout after approval, backup and canary.
**Schermen/bediening:** Vergelijkingsscherm van PR-tests en veiligheidsimpact.
**Acceptatie / concrete toets:** Falende tests kunnen niet gemerged of gedeployed worden via AI bypass.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

#### B02-009 — Predictive maintenance
**Status bij start:** Bouwen; **impact:** Middel.
**Gewenst gedrag en grenzen:** Voorspel opslagtrend, poolcapaciteit, foutgolf, backup expiry en abnormal resource usage uit echte trends.
**Implementatie in code/diensten:** Baseline week/maand with confidence and false-positive feedback; simpler thresholds when little data.
**Schermen/bediening:** Proactieve melding met model en onderliggende meetwaarden.
**Acceptatie / concrete toets:** <24h historie → geen precieze voorspelling verzinnen.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

**Fase-exit:** alle in deze fase genoemde checks aantoonbaar geslaagd, code review, back-up-/rollback-gate, een gebruikersreis op mobiel en een negatieve test voor permissions. Bij een blocker niets forceren: status `Geblokkeerd` + reden + eigenaar.

### F5 - Hardening & UX
**Fase-entry:** voorafgaande kritieke gates geslaagd; bestaande gegevens en huidige release vastgelegd; rollback plan bekend.

#### B02-010 — Automatiserings-AI
**Status bij start:** Bouwen; **impact:** Hoog.
**Gewenst gedrag en grenzen:** Stelt nieuwe Node-RED flows voor, test in sandbox en activeert alleen via permissions/approval.
**Implementatie in code/diensten:** Generate declarative workflows, static validation for forbidden nodes, mock and dry-run, update diff.
**Schermen/bediening:** Voorstel ‘wanneer X dan Y’ met testevents en overrideknoppen.
**Acceptatie / concrete toets:** Flow met exfiltratie of destructieve actie wordt geweigerd.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

#### B02-011 — Veiligheidsreview en modeltests
**Status bij start:** Bouwen; **impact:** Hoog.
**Gewenst gedrag en grenzen:** Adversarial prompts, secrets-leakage, tool confusion, replay, action drift, cost race, unauthorized human spoofing.
**Implementatie in code/diensten:** Automated red-team fixtures + e2e policy tests; run on every release, deny by default.
**Schermen/bediening:** Veiligheidsdashboard met evidence en laatste tests.
**Acceptatie / concrete toets:** Test suite blokkeert release bij één kritieke policy failure.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

**Fase-exit:** alle in deze fase genoemde checks aantoonbaar geslaagd, code review, back-up-/rollback-gate, een gebruikersreis op mobiel en een negatieve test voor permissions. Bij een blocker niets forceren: status `Geblokkeerd` + reden + eigenaar.

### F6 - Release en nazorg
**Fase-entry:** voorafgaande kritieke gates geslaagd; bestaande gegevens en huidige release vastgelegd; rollback plan bekend.

#### B02-012 — Zelflerend zonder auto-policy drift
**Status bij start:** Bouwen; **impact:** Middel.
**Gewenst gedrag en grenzen:** AI gebruikt incident feedback voor better advice; mag veiligheidsgrenzen nooit zelfstandig verlagen.
**Implementatie in code/diensten:** Feedback signals on resolved incidents + approved runbook success; annotated examples with retention/opt-out.
**Schermen/bediening:** Lijst aanbevelingen en gemeten effecten.
**Acceptatie / concrete toets:** Verwijder feedbackdata zonder productie logs te beschadigen.
**Foutafhandeling en bewijs:** een externe storing mag niet als succes worden gelogd; leg testscenario, gebruikte app/image-versie, screenshots, redacted request/response, timestamps, audit/rollback en incidentlink vast.

**Fase-exit:** alle in deze fase genoemde checks aantoonbaar geslaagd, code review, back-up-/rollback-gate, een gebruikersreis op mobiel en een negatieve test voor permissions. Bij een blocker niets forceren: status `Geblokkeerd` + reden + eigenaar.

## 5. Niet-regressie, randgevallen en verbodsbepalingen
Niet dupliceren met ai-factory. ai-factory is een apart codebouwproduct dat zo nodig PR- en testprocessen kan uitvoeren, maar krijgt geen onbeperkte toegang tot TrueNAS; zijn host blijft onafhankelijk. Specifieke modelvarianten/prijsverhoudingen opnieuw meten bij installatie.

## 6. Oplevering door bouwer
Opleveren: (1) broncode en tests, (2) migration scripts en versiecompatibiliteit, (3) Compose/TrueNAS app manifest met gepinde images, (4) .env.example zonder geheimen, (5) OpenAPI/connector schemas, (6) test- en auditrapport, (7) restore bewijs, (8) release notes, (9) gebruikershandleiding, (10) screenshots web/mobiel. Markeer niet-geteste hardware/echte accounts als `NIET GEVALIDEERD`.

## 7. Proof of Done
Alle acceptatiecriteria in Excel zijn gekoppeld aan testbewijs en codecommit; bij stroomonderbreking, uitval van afhankelijke app, NAS-herstart, gewijzigde credentials en incompatibele versie degradeert de service aantoonbaar veilig. Geen directe writes aan de database van een andere app.
