# ExecutionRequest, Approval en ActionProposal (contract 1.3 §8)

Formaat van de berichten tussen de Hub en een uitvoerder (de executor of een eigenaar-connector). De code staat in
`apps/policy/src/asm_policy` (`execreq`, `verify`, `canonical`, `etag`); de Hub en de executor gebruiken hetzelfde
pakket. Besluiten: ADR-0030.

## ActionProposal

```json
{
  "idempotency_key": "<uuid>",
  "action_id": "app.restart",
  "target": {"host_id": "nas-primary", "app_id": "<app>"},
  "parameters": {},
  "reason": "…",
  "actor": {"type": "user|ai|flow|voice|service|system", "id": "…"},
  "expected_version": "<resource_etag>",
  "risk_claim": "R0",
  "evidence_ids": [],
  "expires_in_seconds": 900
}
```

`risk_claim` wordt alleen in de audit bewaard en nooit gelezen. `expected_version` is de `resource_etag` van het doel
op het moment van de preview:

| Doel | `resource_etag` |
|---|---|
| app | `sha256:<hex>` over naam, staat, catalogusapp, trein, versie, `custom_app`, images en digests (`etag.app_etag`) |
| nieuwe app | `absent` |
| dataset | `dataset:<naam>` |
| snapshot | `snapshot:<dataset>@<naam>` |
| geen / eigenaar | `geen` / `eigenaar` |

De app-configuratie telt bewust niet mee: die kan geheimen bevatten en de Hub leest hem nooit.

## Approval

```json
{
  "approval_id": "<uuid>", "request_id": "<uuid>",
  "preview_hash": "sha256:…", "resource_etag": "…", "policy_hash": "sha256:…",
  "risk_class": "R2", "approved_by": "<gebruiker>",
  "approved_at": "2026-01-01T00:00:00Z", "expires_at": "2026-01-01T00:15:00Z",
  "one_time_nonce": "<uuid>", "backup_checkpoint_id": null,
  "action_scope": {"action_id": "…", "target": {…}, "parameters_sha256": "sha256:…"}
}
```

Hooguit 15 minuten geldig. Vervalt bij elke wijziging van een gebonden veld (`preview_hash`, `resource_etag`,
`policy_hash`, `action_scope`, een hogere risicoklasse) en na één gebruik van `one_time_nonce`.

## ExecutionRequest

```json
{
  "proposal": {…}, "approval": {…} ,
  "policy_decision": {"risk_class": "R2", "rule_ids": ["ACT:app.update"], "policy_hash": "sha256:…"},
  "issued_at": "2026-01-01T00:00:00Z", "expires_at": "2026-01-01T00:05:00Z",
  "nonce": "<uuid>", "signature": "<base64url>"
}
```

- `approval` is `null` bij R0/R1.
- Tijden altijd `YYYY-MM-DDTHH:MM:SSZ` (UTC, hele seconden); een verzoek is hooguit 15 minuten geldig.
- **Handtekening:** Ed25519 met de policy-sleutel van de Hub over de canonieke JSON van het verzoek zonder
  `signature`; base64url zonder opvulling. Canonieke JSON = gesorteerde sleutels, scheidingstekens `,` en `:`, UTF-8
  zonder escapes, alleen tekst/gehele getallen/booleans/`null`/lijsten/objecten (geen kommagetallen).
- De ontvanger probeert elke bij het koppelen gepinde policy-sleutel (`pins.policy`).

## Wat de uitvoerder zelf opnieuw controleert

In deze volgorde; elke weigering heeft een stabiele code en er wordt niets uitgevoerd.

| Stap | Code (HTTP) |
|---|---|
| dienst-JWT van de Hub (§4.7), `jti` eenmalig | `unauthorized` (401), `forbidden` (403) |
| vorm van het verzoek | `execution_request_ongeldig` (422) |
| handtekening | `handtekening_ongeldig` (403) |
| tijden | `verzoek_nog_niet_geldig`, `verzoek_verlopen`, `verzoek_geldigheid_ongeldig` (403) |
| policy-hash gelijk aan het eigen beleid | `policy_hash_verschilt` (409) |
| nonce van het verzoek nog niet gebruikt | `nonce_al_gebruikt` (409) |
| allowlist en uitvoerder | `actie_niet_toegestaan` (403), `capability_unavailable` (501) |
| blokkades (shell, destructief, boiler, beschermde app) | `actie_geweigerd` (403) |
| doel- en parameterschema met harde grenzen | `parameters_ongeldig` (422) |
| risicoklasse ≥ eigen herberekening | `risicoklasse_te_laag` (403) |
| goedkeuring aanwezig, geldig en gebonden | `goedkeuring_ontbreekt`, `goedkeuring_verlopen`, `goedkeuring_ongeldig` (403), `goedkeuring_past_niet` (409), `backup_checkpoint_ontbreekt` (409) |
| nonce van de goedkeuring nog niet gebruikt | `goedkeuring_al_gebruikt` (409) |
| precondities uit eigen readback (ETag van het doel, pools gezond) | `doel_gewijzigd`, `doel_bestaat_niet`, `doel_bestaat_al`, `pool_niet_gezond`, `herstelpunt_onbekend` (409) |

Tussen deze stappen kan de executor ook weigeren om een reden die niet in het verzoek zit. Ook dan is er niets
uitgevoerd:

| Reden | Code (HTTP) |
|---|---|
| beleid niet geladen of niet alleen-lezen in de image | `policy_niet_beschikbaar`, `policy_niet_read_only` (503) |
| er loopt al een uitvoering (de nonce is dan nog niet verbruikt) | `executor_bezet` (409) |
| gestopt na een eerdere afwijking | `executor_gestopt` (409) |
| journaal (eigen SQLite) niet beschikbaar | `journaal_niet_beschikbaar` (503) |
| schrijfsleutel niet ingesteld, vault-verwijzing in de waarden, of TrueNAS kent geen van de methoden | `capability_unavailable` (501; `details.reden` = `schrijfsleutel_ontbreekt` of `vault_verwijzingen`, of `details.methoden` met de gezochte methoden) |
| schrijfsleutel of sleutelopslag onleesbaar | `schrijfsleutel_onleesbaar` (503) |
| TrueNAS onbereikbaar, te traag, ander certificaat, sleutel geweigerd of zonder rechten | `truenas_onbereikbaar`, `truenas_timeout`, `certificaat_gewijzigd`, `sleutel_geweigerd`, `truenas_geen_toegang` (503) |
| TrueNAS geeft een fout bij het lezen | `truenas_fout` (502) |

## Uitvoeren en teruglezen

Daarna voert de uitvoerder uit, leest terug en vergelijkt met de verwachte toestand.

| Uitkomst | Antwoord |
|---|---|
| toestand is zoals verwacht | `200` met `status: "uitgevoerd"`, `methode`, `before_hash`, `after_hash`, `resource_etag`, `readback`, `waarschuwingen`, `policy_hash` |
| TrueNAS weigert de aanroep en het doel is onveranderd | `502 uitvoering_mislukt` (`details.reden`); de executor blijft werken |
| toestand wijkt af, of de uitkomst is onbekend (time-out, verbroken verbinding, journaal weg na de aanroep) | `409 afwijking` (`details.reden`, `details.afwijkingen`, `details.gestopt`); de executor stopt |

Na een afwijking weigert de executor alles met `executor_gestopt` tot een beheerder hem op de executorpagina
vrijgeeft met de TrueNAS-schrijfsleutel. De Hub legt een incident vast; er is geen automatische herhaling.

`GET /api/v1/executions/{request_id}` (dienst-JWT van de Hub) geeft `{request_id, uitvoeringen, gestopt}` uit het
journaal. Elke uitvoering heeft `action_id`, `target`, `methode`, `status` (`gestart`, `uitgevoerd`, `mislukt` of
`afwijking`), `before_hash` en `after_hash`. Een onbekend verzoek geeft een lege lijst.
