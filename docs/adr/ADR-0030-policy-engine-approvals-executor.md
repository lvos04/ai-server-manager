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
13. **Schrijfsleutel op de executorpagina (§3.9).** Het vaste Peil-sjabloon van de executorpagina heeft alleen een
    veld voor de sleutel, niet voor een NAS-adres of vingerafdruk. Daarom:
    - **NAS-adres.** Uit `EXECUTOR_TRUENAS_HOST` (+ `EXECUTOR_TRUENAS_PORT`, standaard 443) als die gezet is; anders
      het IP-adres waarop de beheerder de pagina opent (de `Host`-header, al beperkt door de Host-controle). Een
      hostnaam of loopback-adres zonder instelling geeft `nas_adres_onbekend`; er wordt niets geraden.
    - **Twee stappen.** Stap 1 doet alleen een TLS-handdruk (geen login, de sleutel gaat niet over de lijn) en toont
      adres en SHA-256-vingerafdruk van het certificaat. Stap 2 (dezelfde sleutel opnieuw, binnen 15 minuten) stuurt
      de sleutel alleen over een verbinding met precies die vingerafdruk. Live test: `auth.login_with_api_key`,
      rolcontrole via `auth.me` (`FULL_ADMIN`, `APPS_WRITE` of `SNAPSHOT_WRITE`; een alleen-lezen-sleutel wordt
      geweigerd) en `core.get_methods`. Dit is vertrouwen bij eerste gebruik: de beheerder vergelijkt de vingerafdruk
      met die in TrueNAS.
    - **Opslag.** Versleuteld (AES-256-GCM met `vault.key`) in `/appdata/secrets/naslink.json` (0600); pagina en
      `/api/v1/status` tonen alleen de laatste 4 tekens. De Hub ziet de sleutel nooit.
    - **Vastgelegd.** Adres en vingerafdruk liggen na de eerste keer vast. Vervangen van de sleutel, vrijgeven na een
      afwijking en ontkoppelen van de Hub (`POST /beheer`) vragen de **huidige** sleutel, live geverifieerd tegen het
      vastgelegde adres en de vastgelegde vingerafdruk. Het formulier kent geen adres- of certificaatveld; een ander
      certificaat geeft `certificaat_gewijzigd` zonder login. Een ander adres of certificaat vraagt een nieuwe
      datamap (herinstallatie van de executor-app).
    - **Ontkoppelen.** Verwijdert alleen de Hub-koppeling; adres, vingerafdruk en sleutel blijven staan, zodat opnieuw
      koppelen met een koppelcode volstaat. `POST /api/v1/hub-link/unlink` vanuit de Hub (§3.8) blijft
      `501 capability_unavailable`: §3.9 eist bewijs met de schrijfsleutel en de Hub mag die sleutel nooit zien.
    - **Fail-closed.** Onleesbare sleutelopslag: geen formulieren, niets wordt overschreven, uitvoeren geeft
      `schrijfsleutel_onleesbaar`. Onleesbare koppelstatus met een werkende sleutel: alleen het beheerformulier, als
      herstelroute (ontkoppelen, daarna opnieuw koppelen).
    - **Restrisico.** Tussen koppelen en het instellen van de sleutel kan iemand op het LAN die de pagina bereikt de
      executor aan een ander adres binden (alleen via het IP in de `Host`-header en alleen met een sleutel die op dát
      adres schrijfrechten heeft). Dat levert geen rechten op de echte NAS op; het blokkeert de executor tot een
      herinstallatie. Mitigatie: `EXECUTOR_TRUENAS_HOST` zetten, de getoonde vingerafdruk controleren, en de
      bestaande herkomst-, formuliercode- en pogingenregels (§3.7).
14. **Afwijking → stop + incident.** Wijkt de readback af van de verwachting (staat, aanwezigheid, digest) of is de
    uitkomst onbekend (time-out of verbroken verbinding ná de aanroep), dan zet de executor zichzelf op "gestopt" en
    weigert hij elke volgende uitvoering (`executor_gestopt`) tot een beheerder hem op de executorpagina vrijgeeft.
    Het sjabloon heeft geen aparte vrijgaveknop: vrijgeven is "Sleutel vervangen" met de huidige sleutel en een leeg
    veld voor de nieuwe sleutel. Het antwoord aan de Hub is `afwijking`; de Hub legt een incident vast en zet de
    actie op `afwijking`. Geen automatische herhaling. Weigert TrueNAS de aanroep en is het doel aantoonbaar
    onveranderd, dan is het `uitvoering_mislukt` zonder stop. Een onleesbaar journaal telt als gestopt: vóór de
    aanroep `journaal_niet_beschikbaar` (er is niets uitgevoerd), erna `afwijking`.
15. **Methoden per TrueNAS-versie.** De executor vraagt `core.get_methods` op en kiest de eerste methode uit
    `acties.yaml` die bestaat (bv. `pool.snapshot.create`, anders `zfs.snapshot.create`). Bestaat er geen, dan
    `capability_unavailable`; nooit gesimuleerd succes. Welke versie welke naam kent is niet op een echte NAS
    vastgesteld: de fake kent beide varianten, de lijst in het beleid is een aanname uit de publieke API-beschrijving
    (**NIET GEVALIDEERD (echte NAS)**).
16. **Noodstop.** Een instelling van de Hub (`acties.noodstop`) die elke nieuwe uitvoering blokkeert. Alleen een
    beheerder zet hem; het is geen `action_id`.
17. **Uitvoerders buiten de executor.** `notification.send` (R0) loopt via de Gotify-adapter van de Hub.
    `sso.*` hoort bij de eigenaar-connector van `home-control-hub`; zolang die geen `/connector/v1/apply` aanbiedt,
    geeft de Hub `capability_unavailable`.
18. **Hub-routes voor voorstellen en goedkeuringen (B01-007).** Contract §8 legt de objecten vast, niet de routes.
    Gekozen, alles onder `/api/v1` en alleen voor gebruikerssessies:

    | Route | Rol | Doet |
    |---|---|---|
    | `GET /policy` | kijker | beleid, klassen, blokkades en `policy_hash` (alleen-lezen) |
    | `POST /actions` | operator | voorstel → classificatie, preview en drie hashes; er wordt niets uitgevoerd |
    | `GET /actions`, `GET /actions/{request_id}` | kijker | voorstellen met preview, blokkades, goedkeuring, uitkomst |
    | `POST /actions/{request_id}/approve` | beheerder | R2/R3 goedkeuren voor precies de getoonde hashes |
    | `POST /actions/{request_id}/reject` | beheerder | afwijzen met reden |
    | `POST /actions/{request_id}/execute` | operator (R2/R3: beheerder) | opnieuw controleren, ondertekenen, uitvoeren |
    | `POST /actions/{request_id}/reconcile` | operator | onbekende uitkomst ophelderen (alleen lezen) |
    | `GET`/`PUT /actions/noodstop` | kijker / beheerder | noodstop lezen / zetten |

    De rol kind heeft geen toegang. `request_id` = de `Idempotency-Key` van het voorstel (het `idempotency_key` van
    contract §8); staat hij ook in de body, dan moet hij gelijk zijn. Voorstellen door diensten, flows of de AI
    krijgen later een eigen ingang met een eigen dienstscope; tot dan bestaat die weg niet (dus ook geen AI-actor die
    iets kan goedkeuren of uitvoeren).
19. **Statussen.** `klaar` (R0/R1, direct uitvoerbaar), `wacht_op_goedkeuring`, `goedgekeurd`, `afgewezen`,
    `geweigerd` (beleid), `bezig`, `uitgevoerd`, `mislukt` (toestand aantoonbaar onveranderd), `afwijking`, `onbekend`
    en `verlopen`. Een geweigerd voorstel wordt wél vastgelegd (wie, wat, welke regel), maar zonder parameterwaarden:
    alleen hun hash. Een voorstel dat het schema niet haalt (422) of waarvan het doel niet te lezen is, wordt niet
    opgeslagen.
20. **Twee keer classificeren.** Eerst zonder de NAS (verboden, boiler, gereserveerd, onbekend, schema), daarna met de
    eigen readback van het doel (kritieke of beschermde app). Kan de Hub het doel niet lezen, dan `409 doel_onbekend`:
    onbekend telt nooit als ongewijzigd, en zonder readback is er geen preview en geen `resource_etag`.
21. **Herkenning op naam, catalogusapp én image; dicht bij twijfel.** Wijzen de appnaam, de catalogusapp
    (`metadata.name`, behalve `ix-app`) en de image naar verschillende bekende apps, dan gelden de regels van allemaal
    (`recognize_all`); de strengste wint. Zo verliest een app met de naam `emby` de Emby-bescherming niet door een
    andere image, en wordt een kritieke app niet R1 doordat zijn image op een gewone app lijkt. TrueNAS toont bij een
    gestopte app geen image (lege `active_workloads`; middleware `plugins/apps/ix_apps/query.py`, `list_apps`, gelezen
    in release/25.04.2 en release/25.10.0, NIET GEVALIDEERD op een echte NAS). Een catalogusapp blijft herkenbaar aan
    zijn catalogusnaam: de catalogus legt zijn images vast en het formulier laat hooguit kiezen uit die images, nooit
    een eigen repository (gelezen in `truenas/apps`, o.a. emby, plex en jellyfin). Is van een bestaande app niet vast
    te stellen wat erin draait (geen image te zien en geen catalogusapp, zoals een gestopte Custom App), dan weigert
    het beleid elke actie op die app (`DOEL-ONHERKENBAAR`, `doel_niet_herkenbaar`), ook met goedkeuring: het kan Emby,
    MediaGuard of de mediaserver onder een andere naam zijn. Gevolg: een gestopte Custom App start, wijzigt of
    verwijdert het platform niet. Hub en executor gebruiken dezelfde functie (`herken_app`) op hun eigen readback; de
    nagebootste TrueNAS in de tests geeft bij een gestopte app dezelfde lege `active_workloads`.
22. **Fout mét of zonder vastlegging.** Een weigering die de toestand van het verzoek verandert (goedkeuring vervallen,
    voorstel verlopen, uitvoering mislukt, afwijking, uitkomst onbekend) wordt samen met die wijziging vastgelegd en
    is daarna het idempotente antwoord op dezelfde sleutel. Elke andere fout laat de database ongemoeid.
23. **Welke goedkeuring telt.** Per verzoek is er hooguit één open goedkeuring; opnieuw goedkeuren laat de vorige
    vervallen (`vervangen`). De keuze van "de huidige" is volledig bepaald (open eerst, dan de laatst afgesloten),
    ook als twee goedkeuringen in dezelfde seconde vallen — anders zou een geldige goedkeuring bij toeval als
    vervallen gelden. Goedkeuren, afwijzen, uitvoeren en ophelderen vergrendelen de rij van het verzoek
    (`SELECT … FOR UPDATE`) tot het einde van hun transactie: twee gelijktijdige aanroepen op hetzelfde verzoek lopen
    na elkaar en de tweede krijgt `409 status_past_niet`. Bij uitvoeren blijven daarnaast de atomaire voorwaardelijke
    updates staan (nonce van de goedkeuring en status), zodat precies één uitvoering de executor bereikt. Het bijwerken
    van verlopen goedkeuringen en voorstellen (ook vanuit de leesroutes) raakt alleen verzoeken waarvan het de rij zelf
    kan vergrendelen (`FOR UPDATE SKIP LOCKED`) en controleert de voorwaarden daarna opnieuw: een gebruikte goedkeuring
    wordt nooit ook "verlopen", en een verzoek dat `bezig` is gaat nooit terug.
24. **Anti-flap voor iedereen.** Afkoeltijd en maximum per uur per (actie, doel) gelden ook voor een beheerder. Het
    contract zegt niet of ze alleen voor de AI gelden; dit is de veiligste lezing. Uitvoeren houdt per (actie, doel) een
    vergrendeling (`pg_advisory_xact_lock`) vast vanaf vlak vóór de controle van de blokkades tot het voorstel op
    `bezig` staat; zo zien twee voorstellen voor hetzelfde doel elkaars start ook als ze tegelijk worden uitgevoerd.
25. **Synchroon uitvoeren, nooit herhalen.** `execute` wacht op het antwoord van de executor (time-out van de actie
    plus marge). Komt er geen bruikbaar antwoord, dan is de status `onbekend`: de Hub herhaalt niets, want de nonce
    is verbruikt. `reconcile` leest het journaal van de executor (`GET /api/v1/executions/{request_id}`) en zet de
    status alleen op wat daar staat; zegt het journaal "nooit gezien" en is het `ExecutionRequest` verlopen, dan is
    er aantoonbaar niets uitgevoerd (`mislukt`).
26. **Incidenten.** Afwijking → kritiek incident per doel (`actie.afwijking`, vingerafdruk
    `ai-server-manager:actie_afwijking:<doel>`, elke keer een melding); sluit bij een latere geslaagde en gecontroleerde
    actie op hetzelfde doel. Onbekende uitkomst → waarschuwing per verzoek (`actie.uitkomst_onbekend`); sluit als de
    uitkomst is opgehelderd. Een nette weigering of een mislukte aanroep staat alleen in het auditspoor.
27. **Adres van de executor.** Uit de eigen inventaris (`app.query` + het NAS-adres van D03), met controle van de
    image-repository; nooit uit de `base_url` die een dienst zelf opgeeft. Niet gekoppeld of adres onbekend → er wordt
    niets ondertekend.
28. **Geheimen in installatiewaarden.** Waarden van omgevingsvariabelen staan nooit in een preview, log of audit
    (alleen de namen). Een verwijzing `vault://app/<app_id>/<parameter>` is het enige toegestane formaat; het invullen
    ervan door de executor bestaat nog niet, dus een installatie met zo'n verwijzing geeft eerlijk
    `501 capability_unavailable`.
29. **Testnaden.** Tests zetten alleen de *invoer* van de gates (`blokkades.gate_inputs`: besluiten, eigen back-up) en
    — voor `app.update`/`app.rollback` — een gesimuleerd herstelpunt (`blokkades.verified_checkpoint`); de
    beoordeling, de policy, de handtekening en de executor zijn de echte code.

## Open punten

- **Schermen in de Hub-UI.** De API is er; het goedkeuringsscherm (preview, hashes, goedkeuren/afwijzen, uitvoeren,
  noodstop) is nog niet gebouwd. Tot dan loopt het via de API-documentatie (`/api/docs`).
- **Herstelpunten per app (B12).** Zolang die niet bestaan, zijn `app.update` en `app.rollback` via de Hub altijd
  geblokkeerd (`backup_checkpoint_ontbreekt`); de keten zelf is Sim-getest met een gesimuleerd herstelpunt.
- **Gate `r2_r3_acties`** hangt af van `data_mutatie` (ADR-0007). Daardoor is élke R2-actie geblokkeerd bij een
  ongezonde pool of een rode back-upgate, ook een die geen opslag raakt (bv. een kritieke app herstarten). Veilig, maar
  mogelijk strenger dan bedoeld; aanpassen is een besluit over de gates, niet over dit beleid.
- **Geen sleutel-ID in `ExecutionRequest`.** De executor probeert elke sleutel uit de gepinde set; bij sleutelrotatie
  (contract §4.5) is een `kid` in het verzoek duidelijker. Contractvraag.

## Gevolgen

- Een wijziging van het beleid vraagt een nieuwe image van Hub én executor met dezelfde `policy_hash`; anders weigert
  de executor alles (`policy_hash_verschilt`). De rooktest vergelijkt de hash van beide images.
- De JSON-RPC-methoden en hun parameters (`app.create`, `app.update`, `app.delete`, `app.config`, `core.get_jobs`)
  zijn gebouwd naar de publieke API-beschrijving en alleen tegen de fake getest: **NIET GEVALIDEERD (echte NAS)**.
