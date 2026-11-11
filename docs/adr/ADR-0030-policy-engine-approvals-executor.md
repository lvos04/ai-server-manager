# ADR-0030 — Policy-engine, goedkeuringen en executor (P2 deel 1)

Status: aangenomen · 2026-11-11 · fase P2 deel 1 · repo `ai-server-manager`
Bouwt op: ADR-0007 (gates), ADR-0010 (koppelen executor), ADR-0029 (contract 1.3 in Hub en executor).
Bron: `docs/platform-v2/PLATFORM_CONTRACTEN.md` §3.9, §4.7 en §8; B01-003, B01-007, B02-005, B02-006, B12-006;
`03_RISICO_AUTONOMIE`; testmatrix EX11, EX12, EX17–EX20, EX27, EX47. Alles is Sim-getest tegen de in-repo fake van de
TrueNAS-API; niets is op een echte NAS gevalideerd.

## Context

Tot P2 weigerde de executor alles en bestond er geen beleid. Dit deel bouwt de stroom van contract §8:
voorstel → deterministische policy → (bij R2/R3) menselijke goedkeuring per gebonden diff → ondertekend
`ExecutionRequest` → executor controleert zelf opnieuw → uitvoering → readback → audit.

## Besluiten

1. **Eén gedeeld pakket `asm_policy` (`apps/policy`).** De Hub en de executor installeren hetzelfde pakket en lezen
   dezelfde `policy/*.yaml`. Zo kan de classificatie in de Hub nooit ongemerkt afwijken van de hercontrole in de
   executor. De executor importeert nog steeds niets uit de Hub.
2. **Beleid read-only in beide images.** `/usr/local/share/asm/policy` (root, 0555/0444). In een image wint die map
   altijd; `ASM_POLICY_DIR` werkt alleen daarbuiten (tests). De `policy_hash` telt elke byte van elke `*.yaml`. Een
   ongeldig beleid laadt niet (fail-closed). Er is geen route en geen `action_id` om beleid te wijzigen.
3. **Classificatie is een pure functie.** `classify` krijgt `risk_claim` niet eens binnen (EX18). Volgorde: verboden
   patronen → boiler → gereserveerd → onbekend → basisklasse → kritieke app → beschermde app → soort actor. De
   strengste regel wint; herkenning van een app maakt alleen strenger.
4. **Verboden patronen gelden per segment.** `system.sudo`, `app.shell.exec` en `pool.dataset.delete` zijn geweigerd,
   niet alleen `shell.*`. Destructieve acties worden in deze versie niet aangeboden, ook niet met goedkeuring.
5. **Boiler (EX27).** Gezocht in `action_id`, doel en alle sleutels en tekstwaarden van de parameters. Uitzondering:
   de vrije tekst van `notification.send` — een melding óver de boiler schakelt niets en de bewaking moet erover
   kunnen melden. Het doel en de `action_id` van een melding tellen wel.
6. **`app.install` (B01-003, EX47).** Alleen `app.create` met `custom_app` afwezig of `false`. De standaard Custom App
   is `catalog_app: ix-app`, trein `stable`, met ix-app-waarden uit een witte lijst. Geweigerd vóór uitvoering:
   `custom_compose_config(_string)` op elke diepte, privileged, host-netwerk/-PID/-IPC, extra capabilities, devices,
   Docker-socket, hostpaden buiten `/mnt/<pool>/<dataset>`, `latest` of een tag zonder digest. Een catalogusapp vraagt
   een exacte versie en een `install_reason`.
7. **`app.uninstall` is container-only.** `app.delete` met `remove_ix_volumes: false` en `remove_images: false`;
   datasets en data blijven. Er is geen actie die data verwijdert.
8. **Terugzetten.** Custom App: `app.update` met de vorige waarden. Die waarden leest alleen de executor
   (`app.config`), en hij bewaart ze versleuteld in zijn eigen opslag bij het `request_id` van de update;
   `app.rollback` verwijst met `herstel_van` naar dat `request_id`. De Hub ziet de app-configuratie nooit.
   Catalogusapp: `app.rollback` naar een eerder geïnstalleerde versie.
9. **`resource_etag`.** Een hash over naam, staat, catalogusapp, trein, versie, `custom_app`, images en digests uit
   `app.query` + `app.image.query`. Hub en executor rekenen hem met dezelfde functie uit hun eigen readback. De
   app-configuratie telt niet mee (geheimen; de alleen-lezen-key van de Hub leest hem niet).
10. **Goedkeuring (B01-007, EX19, EX20).** Gebonden aan `preview_hash`, `resource_etag`, `policy_hash`,
    `action_scope` en risicoklasse; hooguit 15 minuten; `one_time_nonce` eenmalig. De beheerder stuurt bij goedkeuren
    de drie hashes mee die hij zag; wijkt er één af, dan `409` en een nieuwe preview. Vlak vóór uitvoering rekent de
    Hub alles opnieuw uit; een gewijzigd gebonden veld laat de goedkeuring vervallen. De nonce wordt atomair in de
    database verbruikt vóór er iets naar de executor gaat; de executor houdt in zijn eigen SQLite bij welke nonces hij
    zag. Goedkeuren kan alleen een beheerder (rol `admin`); een AI-, flow- of dienst-actor nooit.
11. **Dynamische blokkades (EX11, EX12).** De Hub leidt ze af van de bestaande gates (ADR-0007), zonder die te
    dupliceren: R2/R3 vraagt gate `r2_r3_acties`; een `opslagmutatie` vraagt `data_mutatie`; `app.install` vraagt
    `deployment`; `app.update`/`app.rollback` vragen `bestaande_app_updates`. Pool niet `ONLINE`/onbekend →
    `pool_niet_gezond`; back-upgate niet groen → `backup_gate_rood`. Onbekend telt nooit als groen en er is geen
    override. De executor controleert de pools bij een opslagmutatie zelf opnieuw via `pool.query`.
12. **Herstelpunt (B12-006).** Acties met `requires_backup` vragen een `backup_checkpoint_id` van een geverifieerd
    herstelpunt van de app. Die herstelpunten per app bestaan nog niet (B12, later deel): tot dan is zo'n actie
    geblokkeerd met `backup_checkpoint_ontbreekt`. Veiligste lezing; nooit een verzonnen herstelpunt.
13. **Schrijfsleutel op de executorpagina (§3.9).** NAS-adres, poort en schrijfsleutel worden op de statuspagina van
    de executor ingevuld, met dezelfde herkomst-, Host-, token-, pogingen- en veldregels als het koppelformulier. De
    executor toont eerst de TLS-vingerafdruk; pas na bevestiging gaat de sleutel over de lijn, en alleen naar een
    verbinding met precies die vingerafdruk. Live test: `auth.login_with_api_key`, rolcontrole (`FULL_ADMIN` of
    `APPS_WRITE`-achtig via `auth.me`) en `core.get_methods`. De sleutel staat versleuteld (AES-256-GCM met
    `vault.key`) in `/appdata/secrets`; de pagina toont alleen de laatste 4 tekens. De Hub ziet de sleutel nooit.
    Roteren, ontkoppelen en opnieuw koppelen vragen opnieuw de sleutel, live geverifieerd tegen het **vastgelegde**
    adres en de vastgelegde vingerafdruk; een ander adres of certificaat telt niet als bewijs.
14. **Afwijking → stop + incident.** Wijkt de readback af van de verwachting (staat, aanwezigheid, digest), dan zet
    de executor zichzelf op "gestopt" en weigert hij elke volgende uitvoering (`executor_gestopt`) tot een beheerder
    hem op de executorpagina vrijgeeft met de schrijfsleutel. Het antwoord aan de Hub is `afwijking`; de Hub legt een
    incident vast en zet de actie op `afwijking`. Geen automatische herhaling.
15. **Methoden per TrueNAS-versie.** De executor vraagt `core.get_methods` op en kiest de eerste methode uit
    `acties.yaml` die bestaat (`pool.snapshot.create` op 25.10, `zfs.snapshot.create` op 25.04). Bestaat er geen,
    dan `capability_unavailable`; nooit gesimuleerd succes.
16. **Noodstop.** Een instelling van de Hub (`acties.noodstop`) die elke nieuwe uitvoering blokkeert. Alleen een
    beheerder zet hem; het is geen `action_id`.
17. **Uitvoerders buiten de executor.** `notification.send` (R0) loopt via de Gotify-adapter van de Hub.
    `sso.*` hoort bij de eigenaar-connector van `home-control-hub`; zolang die geen `/connector/v1/apply` aanbiedt,
    geeft de Hub `capability_unavailable`.

## Gevolgen

- Een wijziging van het beleid vraagt een nieuwe image van Hub én executor met dezelfde `policy_hash`; anders weigert
  de executor alles (`policy_hash_verschilt`). De rooktest vergelijkt de hash van beide images.
- De JSON-RPC-methoden en hun parameters (`app.create`, `app.update`, `app.delete`, `app.config`, `core.get_jobs`)
  zijn gebouwd naar de publieke API-beschrijving en alleen tegen de fake getest: **NIET GEVALIDEERD (echte NAS)**.
