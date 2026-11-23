# Monitoring koppelen — Uptime Kuma, Beszel en Gotify

De Hub **leest** alleen: hij installeert of wijzigt niets in Uptime Kuma, Beszel of Gotify. Je koppelt een bron in de
Hub (scherm Instellingen → Monitoringbronnen/Meldingskanalen, of via de API `/api/v1/monitoring/sources` en
`/api/v1/notifications/channels`, rol **beheerder**). Geheimen (API-key, wachtwoord, token) gaan versleuteld de vault in
en komen nooit terug; je ziet alleen de laatste 4 tekens en de datum.

> **NIET GEVALIDEERD (echte installaties):** de koppelingen zijn gebouwd en getest tegen simulators die de broncode van
> Uptime Kuma 2.5.9, Beszel 0.21.1 en Gotify 3.1.1 volgen (ADR-0021). Een echte installatie kan afwijken; de Hub toont
> dan een foutreden in plaats van gegevens, nooit een gesimuleerd succes.

## Uptime Kuma (bereikbaarheid van apps)

1. In Uptime Kuma: **Instellingen → API-keys → Sleutel toevoegen** (alleen voor de Hub). Gebruik geen gebruikerswachtwoord.
2. Optioneel: een **statuspagina** met de monitors die de Hub mag zien (geeft ook de echte tijd van de laatste hartslag).
3. In de Hub: bron toevoegen met soort `uptime_kuma`, het adres (bv. `http://<NAS-adres>:<poort>`), de API-key en/of de
   slug van de statuspagina. Kies **Testen**: je ziet de Kuma-versie, het aantal monitors en hoeveel er aan een app
   gekoppeld zijn.
4. Koppeling monitor → app gaat automatisch als de monitor naar `<NAS-adres uit D03>:<hostpoort van de app>` wijst.
   Anders koppel je hem handmatig (of kies `geen`).

Statussen: UP → gezond, DOWN → down, PENDING → verminderd, MAINTENANCE → onbekend (onderhoud). Komt er 5 minuten geen
verse meting, dan wordt de monitor **onbekend** (nooit "nog gezond"). Weigert Kuma de key, dan worden alle monitors
direct onbekend en meldt de Hub dat de key vervangen moet worden.

## Monitorplan per app (C1.3-ASM-20, contract 1.3 §9)

De Hub stelt per app een monitorplan op uit het register (NAS-adres uit D03 + de gemeten hostpoort) en
`healthcheck.monitor` uit het manifest in de appstore: welke controle (HTTP), welk adres en welke drempel (verwachte
status, timeout, interval). Het manifest telt alleen als de Hub de manifesthash zelf nagerekend heeft.

**De Hub maakt geen monitors aan in Uptime Kuma en past Kuma niet aan.** Zo neem je een regel over:

1. `GET /api/v1/monitoring/monitorplan` (operator) toont per app de stand: `ontbreekt` (geen of ongeldige
   `healthcheck.monitor`, of geen manifest), `onvolledig` (NAS-adres of hostpoort niet eenduidig gemeten),
   `voorgesteld` of `handmatig bevestigd`.
2. Maak in Uptime Kuma zelf een HTTP-monitor met precies dat adres, die verwachte status, timeout en interval.
3. Bevestig de regel: `POST /api/v1/monitoring/monitorplan/{app_id}/bevestiging` (alleen admin) met de
   `plan_sha256` van de regel en `bevestigd: true`. De regel heet dan "handmatig bevestigd", nooit "gevalideerd door de
   Hub"; de bevestiging staat in de audit.

Verandert het adres of de drempel (bv. een andere hostpoort), dan is het een ander plan: de app is weer **niet
bewaakt** en een bevestiging van het oude plan wordt geweigerd (`409 plan_gewijzigd`). Een app zonder handmatig
bevestigde monitor telt nooit als gezond (`unknown`, reden `niet_bewaakt`). Bevestiging in de echte Uptime Kuma: NIET
GEVALIDEERD (echte NAS).

## Beszel (live meetwaarden van de NAS)

1. Maak in Beszel een **gebruiker met rol `readonly`** die alleen het NAS-systeem ziet (Beszel kent geen API-tokens).
2. In de Hub: bron toevoegen met soort `beszel`, het adres, de gebruikersnaam (`identiteit`) en het wachtwoord.
3. De Hub gebruikt **alleen het NAS-systeem**: het systeem dat je kiest (`nas_systeem`), of — zonder keuze — het systeem
   waarvan de host precies het NAS-adres uit D03 is. Andere systemen (zoals de mini-pc) worden getoond als
   *uitgesloten* en leveren nooit metingen.
4. GPU's worden alleen aan een GPU uit de TrueNAS-inventaris gekoppeld als de naam eenduidig past (bv. "Arc A310").
   GPU-temperatuur levert Beszel niet: die blijft **onbekend** (nooit 0 °C).

## TrueNAS zelf

Met de alleen-lezen-key uit de onboarding (rol READONLY_ADMIN, bevat REPORTING_READ) leest de Hub elke 30 s de live
meetwaarden (`reporting.realtime`): CPU, geheugen, ZFS ARC, schijf-I/O en netwerk per interface. Ontbreekt het
leesrecht of reageert de NAS niet, dan is alles **onbekend** met de reden erbij. Zie `GET /api/v1/observability/nas`
en de meetdekking in `GET /api/v1/monitoring/coverage` (welke bron wat levert en waar de hiaten zitten).

## Eigen diensten (connector-health en heartbeat, contract 1.3 §6 en §6.2)

- De Hub leest per eigen dienst `GET /connector/v1/discover` (voor `limits.max_age_s`) en `GET /connector/v1/health`.
  Het totaal is de **slechtste** van de gemelde status en alle checks (gezond < onbekend < beperkt < storing): een dienst
  die "healthy" zegt met een worker die `down` is, staat op storing (`jobs_staan_stil`).
- Een meting of check zonder verse `observed_at` (ouder dan `max_age`, standaard 900 s; een bron mag strenger zijn,
  de Hub is nooit soepeler) is **onbekend** met `meting_verouderd`; de laatste waarde blijft alleen "laatst bekend".
  Ook de instelbare inventaris-TTL geldt hooguit 900 s.
- De Hub zelf meldt `database`, `worker`, `jobs` (wachtrij, bezig, laatste klaar) en `eigen_backup`.

## Externe back-up (OneDrive, B12-004)

- De Hub leest de uploadtaken uit besluit D04 (methode `truenas_cloud_sync`) via `cloudsync.query` van TrueNAS,
  alleen-lezen en zonder credential-attributen. Hij maakt of wijzigt geen opslagdienst. Uitkomst:
  `GET /api/v1/backups/extern`.
- Alleen een ingeschakelde PUSH-taak naar OneDrive met een laatste job `SUCCESS` van hooguit
  `HUB_OFFSITE_MAX_AGE_SECONDS` (standaard 26 uur) geleden is `ok`. Een verouderde of nooit gelopen upload
  (`verouderd`), een verlopen aanmelding (`aanmelding_verlopen`), een mislukte job (`mislukt`) of een ontbrekende of
  uitgeschakelde taak (`ontbreekt`) geeft het incident `backup.extern` met ernst kritiek. De back-upgate is dan dicht
  (`backup_gate_rood`, dus ook R2/R3 en opslagmutaties).
- `unknown` geeft geen incident maar houdt de gate wel dicht. Dat geldt bij een andere methode in D04
  (`capability_unavailable`), een niet-leesbare TrueNAS of een job die nog loopt. Een open incident sluit alleen bij
  positief bewijs: een verse, geslaagde upload van elke taak.
- Fail-closed bij twijfel: alleen `enabled` als boolean `true` telt als ingeschakeld; een job `SUCCESS` mét foutmelding
  is `mislukt` (`tegenstrijdige_jobstatus`). Een D04-naam moet op precies één taak passen (taak-ID of omschrijving);
  past hij op meer taken, dan is de taak `ontbreekt` (`taak_niet_eenduidig`).
- Per taak bewaart de Hub de laatste bevestigde storing (instelling `backup.extern.storingen`). Alleen een upload die
  ná die storing klaar is, heft haar op; een oudere upload blijft `mislukt` (`geen_upload_na_storing`). Een
  herstelbericht sluit het incident alleen als de actuele meting bij het afsluiten nog `ok` is.
- De uitkomst bevat geen vrije taaktekst (omschrijving), alleen taak-ID, staat, tijd en reden.
- Een geslaagde upload is geen herstelgarantie; alleen een vastgelegde hersteltest is dat.

## Gotify (meldingen op je telefoon)

1. In Gotify: **Apps → Applicatie maken** (bv. "Hub") en kopieer het **applicatietoken**. Gebruik nooit een
   client-token of het beheerdersaccount.
2. In de Hub: meldingskanaal toevoegen met het adres en het token, eventueel minimale ernst en stille uren
   (bv. 22:00–07:00, tijdzone `Europe/Amsterdam`). Kies **Testmelding**: de Hub verstuurt echt een bericht en toont
   het echte resultaat.
3. Geen meldingenstorm: per kanaal standaard hooguit 10 berichten per 15 minuten; wat erboven komt wordt onderdrukt en
   samengevat in één bericht. Kritieke meldingen gaan altijd door, ook in de stille uren.

## Wat de Hub (nog) niet doet

- Geen eigen GPU-collector (vraagt render-node-/root-toegang; bewust niet gebouwd).
- MediaGuard, MSO en my_house: alleen bereikbaarheid via Uptime Kuma; hun binnenkant (jobs) volgt in fase P3 via hun
  bestaande routes met een gescopete sleutel. Tot dan zijn ze **onbekend**, nooit groen.
- Out-of-band: Uptime Kuma en Gotify alarmeren ook als de Hub zelf uit staat; bij volledige NAS-uitval meldt niets op
  de NAS zelf (daarvoor is een externe host nodig). Inrichten en de eerlijke status (EX22/EX23):
  [`INCIDENTEN.md`](INCIDENTEN.md#out-of-band-melden-b09-005-ex22-ex23).
- Incidenten-inbox, log-index, auditketting en runbooks (P1 deel 2): [`INCIDENTEN.md`](INCIDENTEN.md),
  [`RUNBOOKS.md`](RUNBOOKS.md); SSO-login: [`SSO.md`](SSO.md).
