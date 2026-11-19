# asm_policy — gedeeld risicobeleid (Hub en executor)

Eén Python-pakket dat zowel de Hub als de executor installeert, zodat beide **dezelfde code** en **dezelfde
`policy/*.yaml`** gebruiken (platformcontract 1.3 §8, ADR-0030):

| Module | Wat |
|---|---|
| `loader` | `policy/*.yaml` laden (streng schema, fail-closed) en de `policy_hash` berekenen |
| `engine` | deterministische risicoclassificatie R0–R3; `risk_claim` wordt nooit gelezen (EX18) |
| `params` | doel- en parameterschema's per `action_id`, met de harde grenzen voor `app.install` (EX47) |
| `c12` | accountcontext en variant B op aangeleverde installatiewaarden, met de gepinde eigenaarsregels |
| `execreq` | vorm, canonieke JSON en Ed25519-handtekening van het `ExecutionRequest` |
| `verify` | controles die elke uitvoerder zelf opnieuw doet: handtekening, vervaltijd, policy-hash, allowlist, schema, risicoklasse, gebonden goedkeuring |
| `etag` | `resource_etag` van een app/dataset/snapshot uit de TrueNAS-readback |
| `canonical` | canonieke JSON (gesorteerde sleutels, geen spaties, UTF-8, geen kommagetallen) |

De gedeelde `ASF_COMMIT` staat in `policy/catalogus.yaml`. Dat bestand valt onder `policy_hash` en gaat mee in
de Hub- en executor-image. Manifest-CI haalt die commit van `appstore-en-fork` op, controleert met
`python tools/sync_asf_c12.py .asf --check` de letterlijk overgenomen C-12-declaraties en valideert vervolgens de
eigen manifesten. Gebruik bij een pinwijziging hetzelfde commando zonder `--check` om de kopie te vernieuwen.

De lijst voor catalogusinstallaties is leeg. Een niet-lege configuratie wordt bij het laden van het beleid geweigerd
totdat er een schema voor gepinde releases met uitgeversbewijs is. De vaste waardenlijst voor de standaard Custom App
blijft van toepassing. Host-netwerk, `privileged`, NFS en SMB blijven gesloten. Zie ADR-0032, besluiten 5–7.

Het beleid zelf staat in [`policy/`](../../policy/README.md) en is in beide images read-only ingebakken onder
`/usr/local/share/asm/policy`. Er is geen route en geen `action_id` waarmee het beleid kan worden gewijzigd.

Tests: `pytest apps/policy/tests`.
