# executor — AI Server Manager executor (fase P0)

Eigen image en eigen standaard TrueNAS Custom App `ai-server-manager-executor` (poort 30410). Dit is later de **enige**
component met een TrueNAS-API-key met schrijfrechten. In fase P0 is hij bewust nog leeg:

- `GET /healthz`, `GET /readyz`, `GET /` (Nederlandse statuspagina: *nog niet gekoppeld*), `GET /api/v1/status`;
- `POST /api/v1/execute` weigert **alles** (`403 action_not_allowed`): de allowlist is leeg;
- geen shell-, sudo- of Docker-endpoint, geen Docker-socket;
- maakt bij de eerste start zijn eigen Ed25519-identiteit en `vault.key` in `/appdata/secrets` (0600, nooit overschreven).

Koppelen met de Hub (koppelcode + schrijfkey op de statuspagina), handtekeningcontrole van `ExecutionRequest`, nonce-opslag
en de echte allowlist volgen in fase P2 (contract §8).
