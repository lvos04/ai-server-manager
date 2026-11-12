# executor — AI Server Manager executor

Eigen image en eigen standaard TrueNAS Custom App `ai-server-manager-executor` (poort 30410). Dit is de **enige**
component met een TrueNAS-API-sleutel met schrijfrechten. Hij voert uitsluitend door de Hub ondertekende acties van een
vaste allowlist uit en controleert elk verzoek zelf opnieuw (contract 1.3 §8, ADR-0030). Zonder koppeling met de Hub of
zonder schrijfsleutel voert hij niets uit.

Status: **Sim-getest** tegen de in-repo nep-TrueNAS (`tests/fakes/fake_truenas.py`). Tegen een echte TrueNAS is niets
gevalideerd (NIET GEVALIDEERD (hardware)).

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
  gaat met de TrueNAS-schrijfsleutel op de statuspagina (zie hieronder); is er nog geen sleutel ingesteld, of is de
  opgeslagen TrueNAS-koppeling zelf onleesbaar (`sleutelopslag_onleesbaar`), kijk dan in
  `deploy/truenas/CUSTOM_APP.md`, kop "Herstel".
- `GET /connector/v1/hub-link` controleert inkomende Hub-JWT's in de volgorde en met de redenen van §4.7 (`aud` precies
  één string; geen header, ander schema of lege waarde → `invalid_token`; header zonder `kid` → `unknown_key`).
- Elke POST/PUT/PATCH/DELETE met een Hub-JWT verbruikt de `jti` in een persistente replaycache
  (`/appdata/executor.sqlite3`), ook zonder `Idempotency-Key`; daarna pas rol (403), `Idempotency-Key` (400) en body
  (422). Een hergebruikte `jti` → `401 token_replayed`, ook na een herstart; is de cache onbruikbaar, dan `503`.
- `POST /connector/v1/hub-link/unlink`: een gebruikers-JWT moet de rol `admin` hebben (de rol `kind` wint altijd); de
  route antwoordt eerlijk `501 capability_unavailable`: ontkoppelen vraagt een live geverifieerde TrueNAS-schrijfsleutel
  en kan daarom alleen op de executorpagina (§3.9), niet via de Hub.
- `POST /api/v1/execute` vraagt een dienst-JWT van de Hub en een `Idempotency-Key`, en daarna een ondertekend
  `ExecutionRequest` (zie hieronder). Zonder aanmelding: `401`. `GET /api/v1/executions/{request_id}` geeft de Hub het
  journaal van één verzoek.
- Verzoeken groter dan 1 MiB krijgen `413`, ook chunked, vóór routering en aanmelding (§5).
- Er is geen shell-, sudo- of Docker-endpoint en geen Docker-socket.
- Bij de eerste start maakt de executor zijn eigen Ed25519-identiteit en `vault.key` in `/appdata/secrets` (0600; nooit
  overschreven).

## TrueNAS-schrijfsleutel (contract 1.3 §3.9)

Zodra de executor gekoppeld is, vraagt de statuspagina de TrueNAS-API-sleutel met schrijfrechten. De Hub ziet deze
sleutel nooit.

1. **Stap 1 — vingerafdruk.** Na het versturen haalt de executor alleen het TLS-certificaat van TrueNAS op en toont de
   SHA-256-vingerafdruk. De sleutel is dan nog niet verstuurd en niet bewaard.
2. **Stap 2 — bevestigen.** Vul de sleutel nogmaals in (binnen 15 minuten). De executor verbindt met precies dat
   certificaat, meldt aan met `auth.login_with_api_key`, controleert de rollen (`auth.me`) en roept `core.get_methods`
   aan, en slaat de sleutel versleuteld op (AES-256-GCM met `vault.key`) in `/appdata/secrets/naslink.json` (0600).
   Daarna zie je alleen de laatste 4 tekens.

**Rollen.** De sleutel moet de app- én snapshotacties van de allowlist dekken: `FULL_ADMIN`, of `APPS_WRITE` samen met
`SNAPSHOT_WRITE`. Een alleen-lezen-sleutel geeft `schrijfrechten_ontbreken`; alleen `APPS_WRITE` of alleen
`SNAPSHOT_WRITE` geeft `schrijfrechten_onvolledig`. De rolnamen zijn NIET GEVALIDEERD (echte NAS). `core.get_methods` is
hier alleen een controle dat de sleutel die methode mag aanroepen; de lijst wordt niet gebruikt (bij elke uitvoering
vraagt de executor de methoden opnieuw op, zie "Uitvoeren").

Het **NAS-adres** is `EXECUTOR_TRUENAS_HOST` (optioneel) of, als dat leeg is, het IP-adres waarop je de executorpagina
opent (de executor draait op de NAS zelf); poort `EXECUTOR_TRUENAS_PORT` (standaard 443). Open je de pagina via een naam
of via loopback, dan is het adres onbekend (`nas_adres_onbekend`). Adres en certificaat liggen na stap 2 vast: een ander
adres of certificaat wordt geweigerd en de sleutel wordt er dan niet naartoe gestuurd.

**Beheer** (blok "Ontkoppelen of sleutel vervangen", zodra er een sleutel ligt) vraagt altijd de huidige sleutel als
bewijs. De executor vergelijkt het bewijs eerst in constante tijd met de opgeslagen (ontsleutelde) sleutel; een andere
sleutel, ook een andere geldige schrijfsleutel, geeft `sleutel_niet_huidig` en gaat nergens heen. Daarna test hij de
sleutel live tegen het vastgelegde adres en certificaat, en pas dan verandert er iets. Is de huidige sleutel in TrueNAS
ingetrokken, dan kan beheer niet meer op deze pagina: installeer de executor opnieuw met een nieuwe datamap
(`deploy/truenas/CUSTOM_APP.md`, kop "Herstel").

- *Sleutel vervangen*: nieuwe sleutel invullen; ook die wordt eerst live getest. Een nieuwe sleutel geeft een gestopte
  executor nooit vrij.
- *Vrijgeven na een afwijking*: huidige sleutel invullen, "Nieuwe sleutel" leeg laten en "Sleutel vervangen" kiezen.
- *Ontkoppelen van de Hub*: de Hub wordt niet meer vertrouwd en de schrijfsleutel wordt gewist; NAS-adres en
  certificaat blijven vast, `first_linked_at` blijft staan (toestand `ontkoppeld`) en het koppelformulier komt terug.
  Na opnieuw koppelen vul je de sleutel opnieuw in; dat gaat in één stap tegen het vastgelegde adres en certificaat.
  Tot dan voert de executor niets uit, ook niet voor een nieuw gekoppelde Hub. Opnieuw koppelen vraagt (nog) geen
  sleutelbewijs; zie ADR-0030 besluit 13. Dit is ook het herstel bij een onleesbaar koppelbestand; dat bestand blijft
  bewaard als `hub-link.json.onleesbaar-<UTC-tijd>`.

Voor alle drie de formulieren gelden de regels van §3.7 (herkomst, `Host`, formuliercode, pogingenlimiet). Een schijf-
of rechtenfout in `/appdata/secrets` geeft `sleutelopslag_niet_schrijfbaar` (503) met een vaste melding; een sleutel die
net in een ander tabblad is ingesteld geeft `sleutel_al_ingesteld` (409). Kan `vault.key` de opgeslagen sleutel niet
openen (bijvoorbeeld na verlies), dan tonen status en pagina `sleutelopslag_onleesbaar` en voert de executor niets uit.

**Log.** `python -m executor api` geeft de logger `executor` een eigen handler op INFO (stdout, de app-log): elke
afgehandelde poging geeft één regel met code en trace-ID, zonder geheimen. De verbinding met TrueNAS logt via een eigen
logger die vast op INFO staat, zodat de frames van websockets (op DEBUG staat daar de sleutel in) nooit in een log
komen.

## Uitvoeren (contract 1.3 §8)

De executor vertrouwt de Hub niet blind. Per verzoek, in deze volgorde:

1. Vorm van het `ExecutionRequest`, handtekening (Ed25519 over canonieke JSON, alleen met de bij het koppelen gepinde
   policy-sleutel van de Hub), geldigheid (hooguit 15 minuten) en `policy_hash` (gelijk aan het eigen, in het image
   ingebakken beleid; anders `409 policy_hash_verschilt`).
2. Eenmalige nonce van het verzoek (eigen SQLite, overleeft een herstart) en of de executor niet gestopt is.
3. Eigen beslissing met hetzelfde beleid: allowlist, parameterschema, blokkades (o.a. Emby, het platform zelf, shell,
   boiler), eigen risicoklasse (een lagere klasse in het verzoek → `403 risicoklasse_te_laag`) en bij R2/R3 de
   goedkeuring: gebonden aan `preview_hash`-velden (`action_scope`), `resource_etag`, `policy_hash`, `risk_class`,
   hooguit 15 minuten geldig, eenmalig (`goedkeuring_al_gebruikt`), en waar het beleid dat eist een
   `backup_checkpoint_id`.
4. Live lezen van TrueNAS: bestaat het doel, is de `resource_etag` nog gelijk (`doel_gewijzigd`), zijn alle pools
   `ONLINE` en gezond voor opslagmutaties (`pool_niet_gezond`), en bestaan de benodigde methoden volgens
   `core.get_methods` (anders `501 capability_unavailable`).
5. Uitvoeren met alleen de methoden uit het beleid, teruglezen, before/after-hash in het journaal. Wijkt de teruggelezen
   toestand af van wat was goedgekeurd, dan `409 afwijking`: de executor **stopt** en voert niets meer uit tot je hem op
   de statuspagina vrijgeeft.

Allowlist v1: `app.install`, `app.update`, `app.rollback`, `app.uninstall`, `app.start`, `app.stop`, `app.restart`,
`zfs.snapshot.create`, `zfs.snapshot.clone_to_sandbox`.

- Installeren gaat **alleen** als standaard Custom App (`app.create` met `custom_app: false`, `catalog_app: "ix-app"`
  en waarden); `custom_compose_config` wordt nooit gestuurd en geweigerd als het in de parameters staat (EX47). Images
  alleen met tag én `@sha256`-digest; geen `latest`, geen privileged, geen Docker-socket, geen hostpaden buiten `/mnt`.
- Verwijderen is container-only: `remove_images: false`, `remove_ix_volumes: false`; datasets en snapshots blijven.
- Bijwerken bewaart eerst de vorige waarden (versleuteld, in het journaal); terugzetten is `app.update` met die waarden.
- Een kloon gaat alleen naar `<pool>/asm-sandbox/<naam>`; de ouderdataset moet al bestaan.
- Er is geen shell-, sudo- of Docker-endpoint en geen Docker-socket; `NasClient` weigert elke methode buiten de vaste
  lees- en schrijflijst.

## Instellingen

Alle optioneel (prefix `EXECUTOR_`); de Custom App heeft geen verplichte variabelen.

| Variabele | Standaard | Betekenis |
|---|---|---|
| `EXECUTOR_TRUENAS_HOST` | leeg | NAS-adres als de TrueNAS-API op een ander adres luistert dan de executorpagina. |
| `EXECUTOR_TRUENAS_PORT` | `443` | HTTPS-poort van de TrueNAS-API. |
| `EXECUTOR_TRUENAS_TIMEOUT_SECONDS` | `15` | Time-out per TrueNAS-aanroep. |
| `EXECUTOR_READBACK_WAIT_SECONDS` | `120` | Zo lang wachten op de verwachte eindtoestand; daarna is het een afwijking. |
| `EXECUTOR_ALLOW_WRITABLE_POLICY` | `false` | Alleen ontwikkeling/CI. In het image is het beleid alleen-lezen. |
| `EXECUTOR_ALLOW_LOOPBACK_HUB` | `false` | Alleen ontwikkeling/CI. |
