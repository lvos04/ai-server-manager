# ExecutionRequest, Approval en ActionProposal (contract 1.3 §8)

Formaat van de berichten tussen de Hub en een uitvoerder (de executor of een eigenaar-connector). De code staat in
`apps/policy/src/asm_policy` (`execreq`, `verify`, `canonical`, `etag`); de Hub en de executor gebruiken hetzelfde
pakket. Besluiten: ADR-0030.

Ontwerp voor catalogus-/plan-/doelbinding en afzonderlijke kluisdoorgifte:
[ADR-0032](adr/ADR-0032-vertrouwde-appplannen-en-kluisdoorgifte.md), besluiten 1–4 en open meldingen M1–M4.
Dit is nog geen transportcontract: het voegt geen veld aan deze envelope toe. Een geheim dat de Hub maakt
(kluisverwijzing `vault://app/<app_id>/<parameter>`) komt als waarde nooit in de ondertekende envelope,
verzoekhash, idempotentie-opslag of het journaal; het wordt niet vóór ondertekening in parameters opgelost. Dat
geldt niet voor de bestaande waarden van omgevingsvariabelen in een voorstel: die staan nu in de envelope en tellen
mee in `parameters_sha256`; preview, log en audit tonen alleen hun namen en de Hub wist ze na afloop (ADR-0030,
besluit 28). Tot het afzonderlijke transport en de binding zijn vastgesteld en gebouwd, blijft de betrokken
kluiscapability `501 capability_unavailable`.

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

Bij `app.install` toont de preview van de Hub elk gezet veld van `app_create.values` met zijn waarde (van `envs`
alleen de namen, een geheim als `***`). Een voorstel met `command` of `entrypoint` in die waarden weigert de Hub met
`501 capability_unavailable` (`details.reden` = `eigen_opdracht`) tot een installatiescherm ze veilig kan tonen
(ADR-0030 besluit 32).

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
| pre-update-gate bij `app.update`/`app.rollback` (S-P2-050f): het gebonden checkpoint is een eigen, vastgelegde snapshot, hooguit een uur oud, van na de laatste wijziging van de app, nog met dezelfde `createtxg`, en dekt alle opslag uit `app.config` | `checkpoint_ontbreekt`, `checkpoint_verlopen`, `checkpoint_afwijkend`, `checkpoint_dekt_niet` (409) |
| EX15 bij `app.rollback` (ADR-0032 besluit 8, optie 3): herkomst uit het eigen journaal; na een gemelde migratie (`parameters.upgrade`) geen terugzetten op alleen de image | `database_herstel_vereist`, `herkomst_onbekend` (409); bij `oud`/`buiten_keten` gaat het door met `herkomst` in het antwoord |

Tussen deze stappen kan de executor ook weigeren om een reden die niet in het verzoek zit. Ook dan is er niets
uitgevoerd:

| Reden | Code (HTTP) |
|---|---|
| beleid niet geladen of niet alleen-lezen in de image | `policy_niet_beschikbaar`, `policy_niet_read_only` (503) |
| er loopt al een uitvoering (de nonce is dan nog niet verbruikt) | `executor_bezet` (409) |
| gestopt na een eerdere afwijking | `executor_gestopt` (409) |
| journaal (eigen SQLite) niet beschikbaar | `journaal_niet_beschikbaar` (503) |
| schrijfsleutel niet ingesteld, vault-verwijzing in de waarden zonder `catalog_binding`, of TrueNAS kent geen van de methoden | `capability_unavailable` (501; `details.reden` = `schrijfsleutel_ontbreekt` of `vault_verwijzingen`, of `details.methoden` met de gezochte methoden) |
| schrijfsleutel of sleutelopslag onleesbaar | `schrijfsleutel_onleesbaar` (503) |
| kluisplekken (contract 1.3 §8.3): de afgifte bij de Hub mislukt, een waarde past niet bij het type van haar plek, of de Hub-koppeling in het plan is niet die van deze executor | `kluis_afgifte_mislukt` (503), `kluis_vorm_ongeldig` (422), `koppeling_past_niet` (409) |
| `app.update` met `image` of `app.rollback` met `herstel_van` op een instantie met ingevulde kluisplekken, of de lijst daarvan is onleesbaar of onvolledig hersteld (journaal ontbreekt of is leeg terwijl de geheimenmap een eerdere markering aangeeft) | `kluisplekken_recept_ontbreekt` (409) |
| TrueNAS onbereikbaar, te traag, ander certificaat, sleutel geweigerd of zonder rechten | `truenas_onbereikbaar`, `truenas_timeout`, `certificaat_gewijzigd`, `sleutel_geweigerd`, `truenas_geen_toegang` (503) |
| TrueNAS geeft een fout bij het lezen | `truenas_fout` (502) |

## Uitvoeren en teruglezen

Daarna voert de uitvoerder uit, leest terug en vergelijkt met de verwachte toestand.

| Uitkomst | Antwoord |
|---|---|
| toestand is zoals verwacht | `200` met `status: "uitgevoerd"`, `methode`, `before_hash`, `after_hash`, `resource_etag`, `readback`, `waarschuwingen`, `policy_hash`; bij `app.rollback` met `herstel_van` en bewaarde waarden buiten het huidige beleid ook de waarschuwing `herstelwaarden_buiten_beleid` en `hercontrole` (`overtredingen`, `codes`; alleen gemeld, het terugzetten gaat door; KLEIN-85) |
| TrueNAS weigert de aanroep zelf (foutantwoord op de aanroep, geen job) of meldt de job als `FAILED`/`ABORTED`, en het doel is onveranderd | `502 uitvoering_mislukt` (`details.reden`); de executor blijft werken |
| toestand wijkt af, of de uitkomst is onbekend: time-out, verbroken verbinding, de jobstatus is niet op te vragen nadat TrueNAS de aanroep aannam (`job_status_onbekend`; de job kan nog slagen), een onverwachte fout of een onverwacht antwoord ná de aanroep, journaal weg na de aanroep | `409 afwijking` (`details.reden`, `details.afwijkingen`, `details.gestopt`); de executor stopt |

Na een afwijking weigert de executor alles met `executor_gestopt` tot een beheerder hem op de executorpagina
vrijgeeft met de TrueNAS-schrijfsleutel. De Hub legt een incident vast; er is geen automatische herhaling.

De stop is duurzaam (S-P2-030, herstel R-VEILIG-1 en R-VEILIG-2):

- de stop en het einde van de journaalrij (`afwijking`) worden in één transactie vastgelegd, de stop eerst;
- lukt dat vastleggen niet (bv. een volle schijf), dan houdt de executor de stop in het geheugen en legt hem vast
  zodra het journaal weer werkt; tot dan voert hij niets uit;
- bij het starten en vóór elke uitvoering telt een journaalrij `gestart` zonder einde (het proces viel weg ná de
  aanroep) als onbekende uitkomst: de rij krijgt `afwijking` met `uitkomst_onbekend` en de executor stopt. Ook een
  `afwijking` van na de laatste vrijgave zonder vastgelegde stop geeft alsnog de stop. Een uitvoering die op dat
  moment in dit proces loopt, telt nooit als weggevallen (de lopende uitvoeringen worden binnen dezelfde
  schrijftransactie gelezen);
- de statusopvragen (`GET /api/v1/status`, de executorpagina `GET /` en `GET /api/v1/executions/{request_id}`) lezen
  alleen: ze tonen de vastgelegde stop of de stop in het geheugen en leggen zelf nooit een stop vast;
- valt het journaal weg vóór de schrijfaanroep (er is aantoonbaar niets naar TrueNAS gestuurd; antwoord `503
  journaal_niet_beschikbaar`), dan krijgt de rij het einde `mislukt` zodra het journaal weer werkt; dat geeft geen
  stop;
- een stop raakt nooit een app: alleen de executor weigert verdere acties. Vrijgeven blijft de bestaande weg ("Sleutel
  vervangen" met de huidige sleutel en een leeg veld "Nieuwe sleutel"); daarmee tellen de rijen tot dat moment niet
  meer als stop.

Te diep geneste JSON in de body geeft `422 validation_error`, net als andere ongeldige JSON.

Wat de Hub van dit antwoord overneemt (ADR-0030 besluit 32): `uitgevoerd` alleen met `methode`, `before_hash`,
`after_hash`, `uitgevoerd_op` en een `policy_hash` gelijk aan die van de Hub, in de juiste vorm; anders is de uitkomst
voor de Hub onbekend (`502 uitkomst_onbekend`, `reden` `executor_bewijs_onvolledig`). Verder alleen velden uit een vaste
lijst, elk met een vaste vorm en grootte; `details.reden` alleen als code (`[A-Za-z][A-Za-z0-9_]*`, eventueel met
` [FOUTNAAM]`), anders `onbekende_reden`; `details.gestopt` alleen als ja/nee. Een weigering met een code buiten
`[a-z][a-z0-9_]*` telt als een onbruikbaar antwoord.

`GET /api/v1/executions/{request_id}` (dienst-JWT van de Hub) geeft `{request_id, uitvoeringen, gestopt}` uit het
journaal. Elke uitvoering heeft `action_id`, `target`, `methode`, `status` (`gestart`, `uitgevoerd`, `mislukt` of
`afwijking`), `before_hash`, `after_hash` en `detail`. `detail` bevat alleen een stabiele code met de foutnaam van
TrueNAS of de jobstatus (bv. `truenas_geen_toegang [EACCES]`, `job_mislukt [FAILED]`, `uitkomst_onbekend`), nooit de
vrije fouttekst van TrueNAS: die kan waarden uit de aanroep bevatten. Een onbekend verzoek geeft een lege lijst.
