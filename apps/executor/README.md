# executor — AI Server Manager executor (fase P0/P1)

Eigen image en eigen standaard TrueNAS Custom App `ai-server-manager-executor` (poort 30410). Later is dit de **enige**
component met een TrueNAS-API-key met schrijfrechten. Zonder die key doet hij bewust nog niets:

- `GET /healthz`, `GET /readyz`, `GET /api/v1/status` en `GET /`, de Nederlandse statuspagina. Daarop staat het
  koppelformulier (koppelcode van 30 minuten plus Hub-vingerafdruk) **alleen zolang de executor nog nooit gekoppeld is**
  (contract 1.2 §3.7, §3.9).
- Koppelt met de Hub en pint daarbij de Hub-sleutels in `/appdata/secrets/hub-link.json` (0600, atomair).
- `GET /connector/v1/hub-link` controleert inkomende Hub-JWT's in de volgorde en met de redenen van §4.7.
- `POST /connector/v1/hub-link/unlink` is de enige mutatie met een Hub-JWT. Voor die route geldt:
  - een `Idempotency-Key` is verplicht;
  - een gebruikers-JWT moet de rol `admin` hebben (de rol `kind` wint altijd);
  - een persistente `jti`-replaycache in `/appdata/executor.sqlite3` weigert een hergebruikte `jti` met
    `401 token_replayed`, ook na een herstart; is de cache onbruikbaar, dan `503`;
  - de route antwoordt daarna eerlijk `501 capability_unavailable`: ontkoppelen vraagt een live geverifieerde
    TrueNAS-schrijfkey (P2).
- `POST /api/v1/execute` weigert **alles** (`403 action_not_allowed`), want de allowlist is leeg.
- Verzoeken groter dan 1 MiB krijgen `413`, ook chunked, vóór routering en aanmelding (§5).
- Er is geen shell-, sudo- of Docker-endpoint en geen Docker-socket.
- Bij de eerste start maakt de executor zijn eigen Ed25519-identiteit en `vault.key` in `/appdata/secrets` (0600; nooit
  overschreven).

De TrueNAS-schrijfkey op de statuspagina volgt in fase P2 (contract §3.9 en §8), samen met:
- de handtekeningcontrole van `ExecutionRequest`;
- de nonce-opslag (in dezelfde SQLite-database);
- de echte allowlist.
