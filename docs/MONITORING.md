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
