# Incidenten, logs, auditspoor en out-of-band melden (P1 deel 2)

Keuzes en motivering: [ADR-0022](adr/ADR-0022-incidenten-logs-audit-runbooks-out-of-band.md). Runbooks per scenario:
[RUNBOOKS.md](RUNBOOKS.md). Alles hier is **Sim-getest** (fakes); een echte NAS, echte Uptime Kuma/Gotify en een
telefoon zijn **NIET GEVALIDEERD**.

## Incidenten-inbox (B01-005)

| Wat | Route | Rol |
|---|---|---|
| Inbox per prioriteit (actief eerst, dan ernst en laatste gebeurtenis); filters status, ernst, bron, soort, oorzaak, tekst | `GET /api/v1/incidents` | kijker |
| Aantallen per status/ernst en groepen per oorzaak-hypothese | `GET /api/v1/incidents/samenvatting` | kijker |
| Detail met hypothese, readback en laatste 50 gebeurtenissen (ETag = versie) | `GET /api/v1/incidents/{id}` | kijker |
| Alle onderliggende gebeurtenissen | `GET /api/v1/incidents/{id}/events` | kijker |
| Toon bewijs (gegevens achter de hypothese + readback) | `GET /api/v1/incidents/{id}/bewijs` | kijker |
| Erkennen (verloopt; daarna weer open + melding) | `POST …/erkennen` | operator |
| Snoozen (kritiek hooguit 24 uur) of opheffen | `POST …/snooze` | operator |
| Handmatig oplossen — geweigerd (`409 nog_actief`) als de bron het probleem nog meldt | `POST …/oplossen` | operator |
| Notitie (geschoond) | `POST …/notities` | operator |
| Supportbundel (geschoond JSON, om te kopiëren) | `GET …/supportbundel` | operator |
| Onderzoek: runbook, hypothese, readback, veilige modus | `GET …/onderzoek` | operator |
| Herstel voorstellen: alleen een `ActionProposal`, nooit uitvoering | `POST …/herstel-voorstellen` | operator |
| Veilige modus opheffen (met reden) | `POST …/veilige-modus` | operator |

Gevoelige details (`classification: sensitive`, bv. het bron-IP van een noodlogin) ziet alleen een beheerder.
Alle wijzigingen vragen `Idempotency-Key`, accepteren `If-Match` (versie) en staan in het auditspoor.

**Wat voedt de inbox?** De eigen outbox van de Hub (monitoringbronnen, meldingskanalen en dead-letters, eigen back-up,
TrueNAS-inventaris, noodlogin, alert-overgangen, auditketting) en de events-inbox van diensten (contract 1.3 §7,
ADR-0029): `app.health.changed` over de **eigen** app, de SSO-events van home-control-hub, en binnen het **eigen domein**
van de bron (bv. home-control-hub: `sso`, `energy`, `network`, `automation`, `flow`) de vaste werkwoorden — probleem
`failed`, `crashed`, `down`, `degraded`, `stalled`, `blocked`, `rejected`, `saturated`, `conflict`; herstel `recovered`,
`succeeded`, `resolved`, `restored`. Een event buiten het eigen domein, met een ander werkwoord of een onbekend type
maakt geen incident maar blijft in `/api/v1/events`.

**Ernst.** Een event mag `payload.ernst` meegeven met een van de vijf woorden `kritiek`, `hoog`, `middel`, `laag`,
`info`; de Hub zet dat vast om (`kritiek` → kritiek; `hoog`/`middel` → waarschuwing; `laag`/`info` → info) en toont in
de UI de bronwaarde (`ernst_bron`, `ernst_label`). Alleen kritiek escaleert. `payload.severity` geldt nog deze release
als overgang. Filteren op app kan met `GET /api/v1/incidents?app=<app_id>` (bron of onderwerp).

**Dedupe en correlatie.** Eén niet-opgelost incident per vingerafdruk (soort × bron × onderwerp): 100 identieke crashes
geven één incident met 100 gebeurtenissen. Een herstel sluit alleen precies dat incident en nooit met een herstel dat
ouder is dan het laatste probleem; `unknown` sluit nooit iets. Binnen een uur na een herstel opnieuw falen heropent
hetzelfde incident; twee keer heropenen binnen een uur zet de **veilige modus** aan (geen herstartvoorstel meer).

**Meldingen.** Eén melding per opening en één hersteldmelding (als er gemeld was), via de bestaande Gotify-wachtrij met
rate-limit en stille uren. Kritiek en niet erkend: hooguit drie herinneringen (elke 30 minuten). Alert-incidenten melden
niet dubbel: de alertregel meldt zelf.

**Hypothese.** Vaste regels met een grove zekerheid (bv. "sleutel geweigerd" 0,9; "TrueNAS meldt de app als gestopt"
0,8; "meerdere apps tegelijk weg en de inventaris faalt" 0,6). Past geen regel, dan staat er eerlijk: *Ik weet het niet:
er is onvoldoende bewijs voor een oorzaak.*

## Logs en correlatie (B09-004)

- Zoeken (operator): `GET /api/v1/logs?q=&bron=&niveau=&trace_id=&incident_id=&van=&tot=`; bronnen:
  `GET /api/v1/logs/bronnen`.
- Eigen diensten sturen regels met `POST /api/v1/logs` (service-token), hooguit 200 per verzoek en 1000 per minuut.
- De Hub schrijft zijn eigen WARNING-regels (API en worker) met `trace_id` in dezelfde index.
- **Alles wordt geschoond vóór opslag**: geheimen (`wachtwoord=`, `token=`, `Authorization`, JWT, PEM, tokens met
  voorvoegsel, lange hex/base64), e-mail, IP-adressen (alleen *privé/publiek/lokaal* blijft) en de exacte waarde van elk
  geheim in de vault. Retentie 14 dagen, hooguit 50 000 regels.
- TrueNAS-containerlogs leest de Hub nog niet (`capability_unavailable`): bekijk ze in TrueNAS → Apps → app → Logs.

## Auditspoor (append-only met hash-ketting)

- `GET /api/v1/audit` (admin) toont per rij `ketting_nr`, `prev_hash` en `hash`.
- `GET /api/v1/audit/verify` (admin) controleert de hele ketting en het anker in `/appdata/audit/anker.jsonl`; de worker
  doet dat dagelijks en maakt bij een breuk een kritiek incident.
- De database weigert wijzigen en verwijderen van auditrijen. Wie dat toch buiten de Hub om doet (database-eigenaar),
  breekt de ketting of het anker en wordt gevonden.
- Zet je bewust een oudere database-back-up terug, dan meldt de controle "staart ontbreekt" (het anker ligt verder):
  dat is verwacht. Leg in het incident vast welke back-up je terugzette en los het daarna handmatig op.

## Out-of-band melden (B09-005, EX22, EX23)

**De Hub zit niet in het meldpad van Uptime Kuma.** Richt het zo in (zonder terminal, alles in de web-UI's):

1. Uptime Kuma (I08): een monitor op **de Hub zelf** (adres van de NAS + poort van de Hub, bv. `/healthz`), op de
   executor en op elke dienst die je wilt bewaken.
2. In Uptime Kuma → Instellingen → Meldingen: **Gotify** (I13) met een eigen applicatietoken, en koppel die melding aan
   de monitors. Gebruik daar de knop *Test* en controleer dat de melding op je telefoon aankomt.
3. In de Hub: Uptime Kuma als monitoringbron (alleen lezen) en optioneel een eigen Gotify-kanaal voor de Hub-meldingen
   (tweede, aparte route).
4. Leg je test vast: `POST /api/v1/monitoring/out-of-band/bevestiging` (admin). De Hub noemt dat "handmatig bevestigd" —
   hij kan Kuma's meldinstelling niet zelf zien.

`GET /api/v1/monitoring/out-of-band` toont of Kuma de Hub bewaakt, welke apps geen Kuma-monitor hebben en waar Kuma en
Gotify draaien.

> **Volledige NAS-uitval (EX23):** draaien Uptime Kuma en Gotify op dezelfde NAS, dan meldt **niemand** iets als de NAS
> uitvalt. Daarvoor moeten ze op een andere, onafhankelijke host draaien (eigen stroom en netwerk). Ook dan kan de Hub
> niet vaststellen dat die host echt onafhankelijk is: de status is nooit "gedekt".
