# ADR-0002 — Alles-in-één Hub-image, aparte executor-image, bewaker als PID 1 zonder root

Status: aangenomen · 2026-11-09 · fase P0

## Context
Installatie uitsluitend als standaard TrueNAS Custom App: één image, één poort, één map `/appdata`, geen YAML en geen
geheimen in het formulier (contract §1/§2). De executor is de enige component die later een TrueNAS-key met
schrijfrechten krijgt en moet daarom een eigen app zijn.

## Besluit
- Hub-image (`deploy/allinone`): ingebouwde PostgreSQL 16 op een unix-socket in `/tmp/asm-pg` (map 0700 van 568,
  `listen_addresses=''`, `--auth-host=reject`), first-start-init, migraties met vooraf een geverifieerde pg_dump,
  `api`, `worker`, `ai-runner` en later de web-UI onder `supervisor.py`.
- De bewaker is **zelf PID 1** (signalen + opruimen van verweesde processen) en wisselt na het rechtzetten van
  `/appdata` naar 568. Daardoor draait na de init **geen enkel proces als root** — strenger dan het MSO-voorbeeld, waar
  `dumb-init` als root blijft draaien. Gemeten: `uid's in de Hub-container: 568 569` (rooktest).
- Web-UI (sinds ADR-0009 `/opt/hub-web/server/hub-server.mjs`): zodra die in de image staat, start de bewaker de web-UI op 30400 en luistert de
  API alleen op `127.0.0.1:8400`; de healthcheck controleert dan beide.
- Executor-image (`deploy/executor`): één proces (`entrypoint.py` geeft `/appdata` aan 568 en vervangt zichzelf door
  de API), eigen dataset, eigen Ed25519-identiteit en `vault.key`. Fase P0: allowlist leeg, alles geweigerd.
- `deploy/dev/compose.yaml` is uitsluitend voor ontwikkeling/CI (getest met `no-new-privileges` en alleen
  CHOWN/DAC_OVERRIDE/FOWNER/SETUID/SETGID).

## Gevolgen
Eén datamap per app; back-up van de Hub = dataset-snapshot + geverifieerde pg_dump in `/appdata/backups`. Start de
gebruiker de container als niet-root (*Custom User*), dan draait alles als die gebruiker en start de AI-runner niet
(zie ADR-0005).
