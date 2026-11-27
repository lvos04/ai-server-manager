# hub — Hub-API van AI Server Manager

`python -m hub <commando>` (in de image ook `hub <commando>`):

| Commando | Doel |
|---|---|
| `init` | first-start-init: ontbrekende geheimen (nooit overschrijven) + setupcode in de log |
| `api` | HTTP-API (`/api/v1/…`, `/connector/v1/…`, `/healthz`, `/readyz`) |
| `worker` | hartslag, geplande inventaris en eigen back-up, jobs |
| `ai-runner` | optionele diagnose als uid 569, met een gecontroleerde kredietreservering per taak |
| `migrate [--check] [--down REV]` | Alembic-migraties |
| `backup-now` | eigen database-export maken en verifiëren |
| `export-openapi [--check]` | `docs/openapi/hub-api.openapi.json` schrijven of op drift controleren |

Installatie: standaard TrueNAS Custom App, zie `deploy/truenas/CUSTOM_APP.md` (geen YAML).

## Incidentdiagnose

Een operator stuurt het incident-ID naar `POST /api/v1/ai/diagnose`. De Hub beoordeelt eerst het gecorreleerde incident.
Via `GET /api/v1/ai/kennis/{incident_id}` zijn de lokale bronmeting, logverwijzingen en het runbook terug te vinden.
Een kijker ziet de openbare incidentgegevens. Logregels vragen operatorrechten en gevoelige incidenten vragen beheerrechten.
`POST /api/v1/ai/plan` maakt op verzoek van een operator een voorstel voor de app uit het incident.
De actie, het doel en de parameters gaan door dezelfde controles als bij `POST /api/v1/actions`.
De beheerder kan de preview via de bestaande actieroute beoordelen.

Externe analyse staat standaard uit. Voor inschakeling zijn `HUB_AI_ENABLED`, het HTTPS-basisadres
`HUB_AI_PROVIDER_URL` en een getest besluit D09 nodig. De beheerder bevestigt in D09 het gekoppelde account,
de aanbieder, de modelkeuze, het toegewezen inbegrepen krediet voor de UTC-maand en het taakmaximum in dezelfde eenheden.
Ontbrekende of verlopen kredietgegevens houden de koppeling dicht. De lokale regels blijven beschikbaar.

De kredietdienst ontvangt `POST /diagnose` met de taaksleutel als `Idempotency-Key`, de keuzes uit D09,
`maand`, `max_eenheden`, `alleen_inbegrepen=true` en een samenvatting van vier velden uit de triage.
De dienst moet het inbegrepen tegoed en het taakmaximum zelf afdwingen. HTTP 200 met uitsluitend
het tekstveld `analyse` levert advies. HTTP 402 sluit de maand. Bij een verbindingsfout blijft de volledige
reservering staan. De Hub reserveert vóór verzending en probeert een gereserveerde taak nooit opnieuw.
`GET /api/v1/ai/providers` toont de grens en de reserveringen. Beheerders kunnen de afzonderlijke
reserveringen, uitkomsten en voorstellen terugvinden via `GET /api/v1/ai/audit`.
