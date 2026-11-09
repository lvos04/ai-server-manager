# policy/ — risicobeleid (fase P2)

Hier komen de policybestanden (`*.yaml`) van de deterministische policy-engine (contract §8, 03_RISICO_AUTONOMIE):
allowlist van `action_id`'s met minimale risicoklasse R0–R3, parameterschema's en harde grenzen, cooldown/anti-flap,
blokkades (pool `DEGRADED`/onbekend, back-upgate rood, boiler, auto-delete, betaalde acties) en de `policy_hash`.

Regels die nu al vastliggen:
- De bestanden worden **read-only** in zowel de Hub- als de executor-image ingebakken; de AI-runner kan ze niet wijzigen
  en heeft geen toegang tot signing keys of de vault.
- Wijzigen van policy, rollen of privileges door AI is altijd verboden; een policywijziging is een handmatige
  beheerdershandeling met review.
- Er bestaat nooit een `shell.exec`, `sudo`, `docker.*` of vrije-tekstcommando.
- In fase P0 is er nog **geen** policy: de executor-allowlist is leeg en weigert alles (`apps/executor`), en de gates
  (`GET /api/v1/gates`) houden R2/R3-acties dicht zolang de executor niet gekoppeld is.
