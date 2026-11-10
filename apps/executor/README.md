# executor — AI Server Manager executor (fase P0/P1)

Eigen image en eigen standaard TrueNAS Custom App `ai-server-manager-executor` (poort 30410). Later is dit de **enige**
component met een TrueNAS-API-key met schrijfrechten. Zonder die key doet hij bewust nog niets:

- `GET /healthz`, `GET /readyz`, `GET /api/v1/status` en `GET /`, de Nederlandse statuspagina (Peil-sjabloon 1.1.1,
  gepinde kopie met sha256 en drifttest). Daarop staat het koppelformulier (koppelcode van 30 minuten plus
  Hub-vingerafdruk) **alleen zolang de executor nog nooit gekoppeld is en het koppelbestand leesbaar is** (contract 1.3
  §3.7, §3.9). "Gereed" = `/readyz` in orde én gekoppeld en bevestigd; `/readyz` hangt niet van de koppeling af.
- Elke formulier-POST doorloopt eerst de herkomstcontrole van §3.7: exacte `Origin` (`<schema>://<Host>` van het
  verzoek; ontbreekt of `null` → 403), `Sec-Fetch-Site` alleen `same-origin`/`none`, de `Host`-beperking tegen
  DNS-rebinding (IP-adres, naam zonder punt of onder `.local`/`.lan`/`.internal`/`.home.arpa`; anders 403
  `host_niet_toegestaan`) en de formuliercode. Daarna telt elke POST als poging (5 per bron-IP en 20 in totaal per
  15 min), ook bij ongeldige invoer, `409 al_gekoppeld`, `409 koppelen_bezig` of `409 koppelstatus_onleesbaar`.
  Invoer wordt als geheel gecontroleerd (Hub-adres ≤ 512, koppelcode ≤ 32, vingerafdruk ≤ 64) en nooit afgekapt;
  één logregel per poging met code en trace-ID.
- Adresregels van §3.2: alleen canonieke IPv4 (`a.b.c.d`), IPv6 tussen `[]`, en de verboden bereiken (loopback,
  link-local, `0.0.0.0`/`::`) ook voor het opgeloste adres, bij elke verbinding.
- Koppelt met de Hub en pint daarbij de Hub-sleutels en `rotation_sequence` in `/appdata/secrets/hub-link.json` (0600,
  atomair, `schema_version` `"1.3"`; lezers accepteren elke `1.x`). Een onleesbaar bestand (geen JSON, andere major,
  ontbrekende velden, verkeerde eigenaar of rechten, symlink) is fail-closed: geen vertrouwen, geen formulier,
  `koppelstatus_onleesbaar`, en het bestand wordt nooit stil teruggezet. De executor kent geen env-token (§3.9): herstel
  volgt in P2 met de TrueNAS-schrijfsleutel.
- `GET /connector/v1/hub-link` controleert inkomende Hub-JWT's in de volgorde en met de redenen van §4.7 (`aud` precies
  één string; geen header, ander schema of lege waarde → `invalid_token`; header zonder `kid` → `unknown_key`).
- Elke POST/PUT/PATCH/DELETE met een Hub-JWT verbruikt de `jti` in een persistente replaycache
  (`/appdata/executor.sqlite3`), ook zonder `Idempotency-Key`; daarna pas rol (403), `Idempotency-Key` (400) en body
  (422). Een hergebruikte `jti` → `401 token_replayed`, ook na een herstart; is de cache onbruikbaar, dan `503`.
- `POST /connector/v1/hub-link/unlink`: een gebruikers-JWT moet de rol `admin` hebben (de rol `kind` wint altijd); de
  route antwoordt eerlijk `501 capability_unavailable`: ontkoppelen vraagt een live geverifieerde TrueNAS-schrijfkey
  (P2).
- `POST /api/v1/execute` vraagt eerst een dienst-JWT van de Hub en weigert daarna **alles** (`403
  action_not_allowed`), want de allowlist is leeg. Zonder aanmelding: `401`.
- Verzoeken groter dan 1 MiB krijgen `413`, ook chunked, vóór routering en aanmelding (§5).
- Er is geen shell-, sudo- of Docker-endpoint en geen Docker-socket.
- Bij de eerste start maakt de executor zijn eigen Ed25519-identiteit en `vault.key` in `/appdata/secrets` (0600; nooit
  overschreven).

De TrueNAS-schrijfkey op de statuspagina volgt in fase P2 (contract §3.9 en §8), samen met:
- de handtekeningcontrole van `ExecutionRequest`;
- de nonce-opslag (in dezelfde SQLite-database);
- de echte allowlist.
