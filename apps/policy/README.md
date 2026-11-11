# asm_policy — gedeeld risicobeleid (Hub en executor)

Eén Python-pakket dat zowel de Hub als de executor installeert, zodat beide **dezelfde code** en **dezelfde
`policy/*.yaml`** gebruiken (platformcontract 1.3 §8, ADR-0030):

| Module | Wat |
|---|---|
| `loader` | `policy/*.yaml` laden (streng schema, fail-closed) en de `policy_hash` berekenen |
| `engine` | deterministische risicoclassificatie R0–R3; `risk_claim` wordt nooit gelezen (EX18) |
| `params` | doel- en parameterschema's per `action_id`, met de harde grenzen voor `app.install` (EX47) |
| `execreq` | vorm, canonieke JSON en Ed25519-handtekening van het `ExecutionRequest` |
| `verify` | controles die elke uitvoerder zelf opnieuw doet: handtekening, vervaltijd, policy-hash, allowlist, schema, risicoklasse, gebonden goedkeuring |
| `etag` | `resource_etag` van een app/dataset/snapshot uit de TrueNAS-readback |
| `canonical` | canonieke JSON (gesorteerde sleutels, geen spaties, UTF-8, geen kommagetallen) |

Het beleid zelf staat in [`policy/`](../../policy/README.md) en is in beide images read-only ingebakken onder
`/usr/local/share/asm/policy`. Er is geen route en geen `action_id` waarmee het beleid kan worden gewijzigd.

Tests: `pytest apps/policy/tests`.
