# policy/ — risicobeleid (contract 1.3 §8, 03_RISICO_AUTONOMIE, ADR-0030)

De drie bestanden hier zijn het **volledige** beleid van de deterministische policy-engine. Ze worden read-only
ingebakken in de Hub-image én de executor-image (`/usr/local/share/asm/policy`, eigenaar root, map 0555, bestanden
0444; de diensten draaien als 568). Beide rekenen dezelfde `policy_hash` uit; de executor weigert elk
`ExecutionRequest` met een andere hash.

| Bestand | Inhoud |
|---|---|
| `acties.yaml` | allowlist van `action_id`'s: uitvoerder, TrueNAS-methoden, minimale risicoklasse R0–R3, parameterschema, back-upeis, anti-flap |
| `apps.yaml` | herkenning van apps, kritieke apps (herstart wordt R2) en beschermde apps (Emby nooit; Hub/executor niet stoppen; MediaGuard en de mediaserver geen update zonder bewijs) |
| `blokkades.yaml` | wat altijd geweigerd wordt (shell, destructief, beveiligingsbeleid, betaald, database, netwerk, boiler), gereserveerde acties en de dynamische blokkades (pool, back-upgate, noodstop, cooldown, herstelpunt) |

Regels:

- **`policy_hash`** = `sha256` over `asm-policy-hash-v1\n` en per `*.yaml` (op naam gesorteerd) naam, lengte en
  inhoud. Elke byte telt; dit README-bestand telt niet mee.
- Een ongeldig of onleesbaar bestand → de dienst laadt geen beleid en voert niets uit (fail-closed).
- `risk_claim` van AI of flow wordt nooit gelezen (EX18). Een onbekende `action_id` → `422`.
- Er bestaat nooit een shell-, sudo-, exec-, Docker-, cron- of vrije-tekstactie, en geen actie die data, datasets,
  snapshots of media verwijdert.
- De boiler wordt nooit geschakeld (EX27): een `action_id`, doel of parameter die naar de boiler verwijst, wordt
  geweigerd. Alleen de vrije tekst van een melding (`notification.send`) mag het woord bevatten.
- Wijzigen van het beleid is een handmatige beheerdershandeling met review en een nieuwe image van Hub **en**
  executor. Er is geen route en geen `action_id` waarmee het beleid, rollen of privileges gewijzigd kunnen worden; de
  AI-runner heeft geen schrijfrecht op de map en geen toegang tot signing keys of de vault.

De code staat in [`apps/policy`](../apps/policy/README.md); het formaat van het uitvoeringsverzoek in
[`docs/EXECUTION_REQUEST.md`](../docs/EXECUTION_REQUEST.md).
