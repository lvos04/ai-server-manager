# ADR-0026 — Onafhankelijke QA-review van P1 en de contract 1.2-schermen

Status: aanvaard · Datum: 2026-11-10 · Rol: onafhankelijke reviewer/QA (geen bouwer van P1)
Bouwt op: ADR-0006 (geheimen), ADR-0014 (review contract 1.2), ADR-0022 (auditketting), ADR-0023 (OIDC),
ADR-0025 (Peil-ontwerpreview, N-01/N-06)

## Context

Na P1 (backend deel 1 en 2, de Peil-webstap en de ontwerpreview) zijn alle tests opnieuw gedraaid zoals de CI ze draait
en is de code nagelopen op contract 1.2 §1–§13, veiligheid (03_RISICO_AUTONOMIE), eerlijkheid (EVIDENCE) en de
acceptatiecriteria van B01-002/004/005/006 en B09-001…006. Alles blijft **Sim-getest**: er is geen echte NAS,
Authentik, Uptime Kuma, Beszel, Gotify, telefoon of schermlezer gebruikt.

## Besluiten

1. **Executor-statuspagina: `Referrer-Policy: same-origin` en de exacte `Origin`-controle blijft (N-01).**
   Met `no-referrer` stuurt elke browser bij het koppelformulier `Origin: null`; koppelen via de statuspagina (§3.9)
   werkte daardoor in geen enkele echte browser. Gekozen is **niet** om `Origin: null` te accepteren (zoals enkele
   andere diensten doen), maar om de pagina `same-origin` te geven: een POST van de eigen pagina draagt dan de echte
   oorsprong, en `null` of een vreemde oorsprong blijft 403 (nooit open bij twijfel). Het CSRF-cookie
   (`SameSite=Strict`, HttpOnly) met formuliertoken blijft daarnaast gelden. `same-origin` lekt geen adres naar andere
   sites: naar een andere oorsprong gaat geen `Referer`. Bewijs: de web-E2E start nu de **echte executor** en verstuurt
   het formulier in Chromium (eerst een foute vingerafdruk → veldfout, daarna koppelen met dezelfde code als toegestane
   herhaling, formulier weg, beide POST's met de echte `Origin`).
2. **Terugkeerpad na inloggen: alleen zichtbare ASCII zonder spatie of backslash.** `/<tab>/ander.domein` passeerde
   de oude controle (`/`, niet `//`); browsers halen tab, CR en LF uit een URL, waarna de meta-refresh na een
   SSO-aanmelding (en `router.replace` na lokaal inloggen) naar `//ander.domein` ging: een open redirect. De Hub
   (`hub.oidc.service.safe_return`) en de web-UI (`safeReturnPath`) gebruiken nu dezelfde regel
   `^/(?![/\\])[!-~]*$`, maximaal 256 tekens, geen `://`; anders `/`.
3. **Auditspoor weigert ook `TRUNCATE` (migratie 0010).** De rij-trigger uit 0006 weigert `UPDATE` en `DELETE`, maar
   `TRUNCATE` vuurt geen rij-triggers af. Een statement-trigger `BEFORE TRUNCATE` weigert dat nu met
   `insufficient_privilege`. Een database-eigenaar kan triggers nog steeds uitzetten; dat blijft zichtbaar via de
   hash-ketting en het anker in `/appdata/audit` (ADR-0022). Alleen de testfixture die tussen tests alle tabellen
   leegmaakt, zet daarvoor als superuser `session_replication_role = replica` voor die ene opdracht.
4. **Gelijktijdig dezelfde gebruikersnaam → 409 `username_taken`, geen 500 (N-06).** De unieke index blijft de echte
   bewaker; een `IntegrityError` bij het wegschrijven wordt vertaald, zonder halve rij. Een integratietest bootst de
   wedloop deterministisch na (een tweede transactie precies tussen voorcontrole en wegschrijven).
5. **Kleine eerlijkheidsreparaties:** de executor meldt bij de start de echte koppelstatus in plaats van altijd "nog
   niet gekoppeld"; image- en pakketbeschrijving van de executor zeggen niet meer "fase P0: nog niet gekoppeld". De
   overlays van Sheet en AlertDialog gebruiken `bg-black/50`, zoals ONTWERPTAAL §1 voorschrijft (was `/60`).

## Niet veranderd (bewust)

- **N-07 (databasepool):** API-pool 5 + 5 en `max_connections=40` in de ingebouwde PostgreSQL. Het verband met de trage
  aanmelding in de CI-review is een vermoeden, niet bewezen; een grotere pool vraagt eerst een meting op de echte NAS.
- De interne API-statuspagina (`GET /` op 127.0.0.1:8400, alleen binnen de container) heet nog "AI Server Manager —
  Hub"; de gebruiker ziet altijd de web-UI met "TrueNAS Home Platform" (ADR-0015 O-07).

## Gevolgen

- De web-E2E-teststack (`tests/e2e/web_stack.py`) start de executor als echte dienst (`HUB_E2E_EXECUTOR_PORT`,
  standaard 39403); de CI-webjob installeert daarom ook `apps/executor` (zelfde vastgezette versies).
- Contractvoorstel 1.3 (§3.7): de statuspagina's zetten `Referrer-Policy: same-origin` en eisen een exacte `Origin`
  (fail-closed), in plaats van `Origin: null` te accepteren; plus een browsertest op elk koppelformulier.
