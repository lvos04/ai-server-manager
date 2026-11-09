# ADR-0022 — Incidenten-inbox, log-index, auditketting, runbooks en out-of-band (P1 deel 2)

Status: aanvaard · Datum: 2026-11-09 · Fase: P1 "Ogen en toegang", backend deel 2
Excel: B01-005, B09-004, B09-005, B09-006 (en EX16, EX17, EX22, EX23 als testgevallen)

## Context
P1 deel 1 (ADR-0021) leverde catalogus, gezondheid, tijdreeksen, alerts en Gotify. Wat ontbrak: één plek voor
problemen (05_OPERATIES: "één inbox met dedupe/correlation/snooze en readback, geen pushstorm"), geschoonde logs die aan
incidenten hangen, runbooks per storingsscenario, een eerlijk beeld van melden zonder Hub (EX22/EX23) en een auditspoor
dat je achteraf kunt vertrouwen. Het contract (1.2) regelt de details niet; hieronder de gekozen, veiligste uitleg.

## Besluiten

### 1. Incidenten zijn afgeleid, deterministisch en eenmalig per vingerafdruk
- Bron: de eigen **outbox** van de Hub en de **events-inbox** (contract §7). Elk event wordt precies één keer verwerkt
  (kolom `incident_verwerkt_op` + `FOR UPDATE SKIP LOCKED`; geen watermerk, dus geen gemiste events bij gelijktijdige
  commits; `incident_event.bron_ref` uniek). Bestaande events bij migratie 0007 tellen als verwerkt (geen golf oude
  incidenten).
- Vaste regels (`hub/incidents/rules.py`), geen AI. Rol per event: `probleem` | `herstel` | `info`, plus een
  **vingerafdruk** (soort × bron × onderwerp). Hooguit één niet-opgelost incident per vingerafdruk (partiële unieke
  index). 100 identieke crashes = één incident met `aantal = 100`.
- **Herstel sluit alleen precies hetzelfde incident**, en alleen als het herstel niet ouder is dan het laatste probleem
  (late levering). `unknown` is nooit een herstel. Correlatie op `correlation_id` hangt een verder onbekend event aan het
  bestaande incident, zonder iets te sluiten.
- Een probleem binnen `incident_reopen_window_seconds` (1 uur) na een herstel **heropent** hetzelfde incident.
- Nieuwe outbox-events om de bronnen compleet te maken: `alert.instance.fired|resolved` (met de meettijd),
  `notification.channel.failed|recovered`, `audit.chain.broken`. Alert-incidenten melden niet opnieuw (de alertregel
  meldt zelf); andere incidenten krijgen één melding per opening, één hersteldmelding als er gemeld was, escalatie
  (kritiek, niet erkend: hooguit 3 herinneringen per 30 min) en een melding als een erkenning of snooze verloopt.
- **Gezondheidswijzigingen** van apps die de Hub zelf meet (catalogus: TrueNAS-staat, Uptime Kuma, binnenkant) komen
  binnen via de standaardregel "App onbereikbaar" op de reeks `app.status` (met duur en hysterese) en dus als
  `alert.instance.*`; een apart event per statuswissel zou dubbele, flapperende incidenten geven. Diensten melden hun
  eigen gezondheid met `app.health.changed`.
- Een dienst kan zich niet als de Hub voordoen: de Hub-regels gelden alleen voor de eigen outbox; dezelfde
  `event_type` via de inbox valt onder de algemene regel.

### 2. Hypothese met zekerheid en bewijs, of eerlijk "ik weet het niet"
`hub/incidents/hypothesis.py`: vaste regels (sleutel geweigerd 0,9; app-staat uit TrueNAS 0,4–0,8; meerdere apps tegelijk
weg + inventaris faalt 0,6; …). De zekerheid is een grove inschatting van de regel, geen statistiek. Past geen regel:
`sleutel = null`, `zekerheid = null`, tekst "Ik weet het niet: er is onvoldoende bewijs voor een oorzaak." De
`oorzaak_sleutel` groepeert incidenten in de inbox. `GET …/bewijs` toont de onderliggende gebeurtenissen en de readback.

### 3. Readback bepaalt of handmatig oplossen mag
`readback.state()` leest de bron terug waar de Hub dat zelf kan (alert, monitoringbron, meldingskanaal, eigen back-up,
inventaris, noodaccount). Meldt de bron het probleem nog (`actief`), dan weigert `oplossen` met `409 nog_actief`:
erkennen of snoozen kan wel. Een **autoritatieve** readback (`hersteld` op een bron die de Hub meet) sluit het incident
zelf (bv. noodlogin pas na rotatie + bevestiging). `onbekend` sluit nooit iets.

### 4. Log-index: alleen geschoond, begrensd en zonder gevolgen
- Bronnen: eigen processen (`hub-api`, `hub-worker`, vanaf WARNING, met `trace_id` uit de request-context) en eigen
  diensten via `POST /api/v1/logs` (service-token). TrueNAS-containerlogs: `capability_unavailable` (welke methode de
  alleen-lezen-sleutel daarvoor mag gebruiken is NIET GEVALIDEERD); bestaande apps: `unknown` tot P3.
- Schonen **vóór opslag** (`redact_log_text`): `sleutel=waarde` (ook NL: wachtwoord, geheim, sleutel), query-parameters
  (`code`, `state`, `token`, …), Bearer/Basic, JWT, PEM, tokens met bekende voorvoegsels, lange hex (behalve
  `sha256:`-digests), hoog-entropische base64, e-mail en **IP-adressen** (alleen de soort blijft: privé/publiek/lokaal),
  plus de **exacte waarde** van elk vault-geheim en elk door de Hub uitgegeven token. Voor dat laatste houdt de Hub
  alleen SHA-256-vingerafdrukken in het geheugen (60 s cache), nooit de waarden.
- Grenzen: bericht ≤ 2000 tekens, velden ≤ 4 KiB, ≤ 200 regels per verzoek (en 1 MiB), per dienst ≤ 1000 regels per
  minuut (429 + `Retry-After`), retentie 14 dagen en hooguit 50 000 regels.
- De supportbundel (operator) wordt daarna nog een keer volledig geschoond; gevoelige details (`classification:
  sensitive`) gaan er nooit in. Logregels zijn gegevens: de sink voert nooit iets uit (EX17).
- **AI-telemetrie:** de AI-runner staat uit en heeft geen toegang tot de database (ADR-0005). Elke toekomstige AI-lezing
  gebruikt alleen deze geschoonde views (incidenten, log-index, supportbundel); er komt geen tweede, ongeschoonde route.

### 5. Auditspoor: append-only met hash-ketting en anker buiten de database
- Elke auditrij krijgt bij de commit een doorlopend `ketting_nr`, `prev_hash` en `hash = SHA-256(prev_hash + "\n" +
  canonieke JSON v1)`. Het verzegelen gebeurt in `before_commit` onder een transactie-advisory-lock: kort (geen
  netwerk), gatloos, en één ketting over API en worker heen. Welke rijen verzegeld worden, bepaalt de database
  (`hash IS NULL`, partiële index, migratie 0009): elke vastgelegde rij is verzegeld en onverzegelde rijen van andere
  transacties zijn onzichtbaar, dus dat zijn precies de eigen rijen — ook als een savepoint ertussen terugdraaide. De
  hash rekent met de rij zoals de database hem bewaart (JSONB), zodat verificatie exact dezelfde vorm gebruikt. Bestaande rijen zijn in migratie 0006 verzegeld (bevroren
  kopie van het algoritme).
- Een trigger weigert `DELETE` en elke `UPDATE` behalve het eenmalig verzegelen. De database-eigenaar kan de trigger
  omzeilen; daarom ook: `GET /api/v1/audit/verify` (nummering, koppeling, inhoud) en een **anker** in
  `/appdata/audit/anker.jsonl` (0600; kop per 15 min) dat een afgeknipte staart zichtbaar maakt. Dagelijkse controle →
  `audit.chain.broken` → kritiek incident.
- Details blijven geschoond (`redact`). IP-adressen staan bewust wél in het audit (alleen admin): forensisch nodig bij
  bv. een noodlogin; in logs en supportbundels worden ze gemaskeerd.
- Een statische test controleert dat elke muterende route een auditrecord schrijft of met reden is uitgezonderd.

### 6. Runbooks zijn getypeerde code, geen vrije tekst
Acht runbooks uit 05_OPERATIES met vaste fasen observeren → isoleren → mitigeren → terugdraaien → bewijs → oorzaak en een
test na herstel die meer vraagt dan "poort open". Stappen: `lezen` (R0, Hub-route), `handmatig` (bestaande UI, nooit een
terminal) of `voorstel` (alleen een `action_id` uit de executor-allowlist van §8, met minimaal die risicoklasse).
`validate()` en unit-tests bewaken dit; `runbook_hash` maakt wijzigingen zichtbaar. De policy-engine bestaat nog niet
(P2): de catalogus staat daarom in het Hub-pakket (read-only in de image), niet in `policy/*.yaml`; P2 verwijst ernaar.
"Herstel voorstellen" geeft alleen een `ActionProposal` met `uitvoerbaar: false` en een vaste reden, nooit uitvoering.

**Veilige modus** (B09-006): heropent een incident 2× binnen een uur (per runbook instelbaar), dan één melding en geen
herstart- of herhaalvoorstel meer — ook niet als TrueNAS of een mens tussendoor herstartte. Opheffen alleen door een
operator met reden + audit.

### 7. Out-of-band: de Hub zit niet in het meldpad en claimt geen dekking die hij niet kan zien
- Uptime Kuma controleert en meldt zelf (Kuma → Gotify → telefoon). De Hub leest Kuma alleen (GET) en heeft **geen**
  route die Kuma-meldingen ontvangt of doorstuurt. Valt de Hub uit, dan blijft Kuma melden (EX22) — mits Kuma de Hub en
  de diensten zelf bewaakt en zijn Gotify-melding werkt.
- `GET /api/v1/monitoring/out-of-band` laat zien: of Kuma de Hub/executor met een verse monitor bewaakt, welke apps geen
  Kuma-monitor hebben, en of Kuma en de Gotify-kanalen op het NAS-adres (D03) staan. Of Kuma zelf via Gotify meldt staat
  niet in `/metrics`: `onbekend` tot een beheerder het in Kuma test en vastlegt (`…/bevestiging`, auditrecord, "handmatig
  bevestigd" — nooit "gevalideerd door de Hub").
- EX23: volledige NAS-uitval is **nooit** `gedekt`. Staan Kuma of Gotify op de NAS, dan zegt de Hub dat er dan niets
  meldt; een ander adres geeft hooguit `extern_onbevestigd` (onafhankelijkheid van stroom/netwerk is niet te meten);
  hostnaam tegenover IP is `onbekend` (geen DNS-aanname).

## Gevolgen
- Nieuwe routes: `/api/v1/incidents…`, `/api/v1/runbooks…`, `/api/v1/logs…`, `/api/v1/audit/verify`,
  `/api/v1/monitoring/out-of-band…`; migraties 0006, 0007 en 0009; worker-taken `incidenten_bijwerken`, `logs_onderhoud`,
  `audit_verankeren`, `audit_controleren`.
- De UI (inbox, bewijs, runbook-knoppen, logs zoeken, out-of-band-kaart) volgt in de P1-webstap met ontwerpstap (§13).
- Alles is Sim-getest; echte Kuma/Gotify/telefoon en een echte NAS-uitval zijn NIET GEVALIDEERD.

## Open punten voor het contract (gemeld als contract_issues)
1. §7 kent geen vaste vorm voor "app-crash" of "herstel": de Hub leest het laatste segment (`failed/crashed/…` vs.
   `succeeded/recovered/…`) en `app.health.changed` met `payload.status`. Voorstel 1.3: vaste werkwoorden en een stabiele
   `entity` (bv. de taak, niet de run) zodat herstel en probleem dezelfde vingerafdruk krijgen.
2. §7 noemt geen `severity` in de payload; de Hub leest `payload.ernst|severity` als hint. Voorstel: optioneel veld.
3. Een log-sink voor diensten (`POST /api/v1/logs`) staat niet in het contract; het is een optionele Hub-uitbreiding met
   service-token, net als de heartbeat (ADR-0021). §5 `Idempotency-Key` past niet (logregels zijn geen beheerhandeling;
   dubbele levering is acceptabel). Voorstel 1.3: opnemen met deze grenzen.
4. `sso.access.revoked` (home-control-hub) noemt de Authentik-gebruikersnaam als `entity.id`; de Hub koppelt op
   `preferred_username` en trekt alleen in. Voorstel: ook de OIDC-`sub` meesturen.
