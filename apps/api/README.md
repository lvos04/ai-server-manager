# hub — Hub-API van AI Server Manager

`python -m hub <commando>` (in de image ook `hub <commando>`):

| Commando | Doel |
|---|---|
| `init` | first-start-init: ontbrekende geheimen (nooit overschrijven) + setupcode in de log |
| `api` | HTTP-API (`/api/v1/…`, `/connector/v1/…`, `/healthz`, `/readyz`) |
| `worker` | hartslag, geplande inventaris en eigen back-up, jobs |
| `ai-runner` | stub; draait als aparte gebruiker zonder toegang tot geheimen (AI staat uit) |
| `migrate [--check] [--down REV]` | Alembic-migraties |
| `backup-now` | eigen database-export maken en verifiëren |
| `export-openapi [--check]` | `docs/openapi/hub-api.openapi.json` schrijven of op drift controleren |

Installatie: standaard TrueNAS Custom App, zie `deploy/truenas/CUSTOM_APP.md` (geen YAML).
