# ADR-0029 — Contract 1.3 in de Hub en de executor (conformiteitsronde, punten NU)

Status: aangenomen · 2026-11-10 · ronde "contract 1.3 toepassen" · repo `ai-server-manager`
Bouwt op: ADR-0027 (contract 1.3), ADR-0028 (review 1.3), ADR-0013/0014 (contract 1.2 in de Hub), ADR-0015 (Peil).
Bron: `docs/platform-v2/PLATFORM_CONTRACTEN.md` (`contracts 1.3`, bron-commit 02b119c) en hoofdstuk 1 van
`docs/platform-v2/CONTRACT_1.3_CONFORMITEIT.md` (C1.3-ASM-01…23). Alles is Sim-getest; niets is op een echte NAS, met
echte accounts of op echte hardware gevalideerd.

## Context

Contract 1.3 is vastgesteld en gereviewd, maar de code van de Hub en de executor volgde nog 1.2. Deze ronde bouwt alleen
de punten die de conformiteitslijst voor deze repo als **NU** markeert. Punten voor P2, P3, P4-0, P4 en P5 (C1.3-ASM-18
t/m -22) blijven open en staan als zodanig in `EVIDENCE.json`. Waar het contract iets openlaat, staat hieronder de
gekozen (veiligste) lezing.

## Besluiten

1. **Bronrepo en kopie (C1.3-ALG-01).** Deze repo is de bron; een kopie maken is hier niet nodig. Wel pint
   `apps/api/tests/unit/test_contract_pin.py` de sha256 van beide documenten op bron-commit 02b119c: een nieuwe
   contracttekst is een bewuste stap (nieuwe pin én nieuwe kopieën via de orkestratie), nooit een stille wijziging.
2. **Healthcheck en bounding set (C1.3-ASM-01).** Eén gedeelde helper `deploy/common/rechten.py`. De bewaker (Hub) en
   het entrypoint (executor) legen de bounding set direct na de eigenaarschapsstap, vóór het eerste kindproces, zodat
   ook de AI-runner hem leeg erft; de effectieve set van het root-proces blijft tot de eigen wissel, dus `setuid` in
   `preexec_fn` werkt nog. Mislukt het legen bij een start als root, dan stopt de start met een Nederlandse melding.
   De healthchecks (exec-vorm) doen als eerste handeling bounding set leeg → 568 → no_new_privs; `--controle` meldt
   de status voor de rooktest. Een niet-root-gebruiker anders dan 568 (een eigen "Custom User") kan niets meer laten
   vallen; de healthcheck zet dan alleen no_new_privs.
3. **Herkoppelen (C1.3-ASM-02).** Een nieuw token voor een bestaande registratie krijgt een termijn van 60 min
   (`expires_at`). Bij het eerste gebruik vervalt die termijn en worden de oudere tokens ingetrokken, ook rotaties die
   de oude installatie intussen deed; een nóg nieuwere, ongebruikte herkoppeling blijft wachten op haar eigen gebruik.
   Een rotatie door de oude installatie trekt het wachtende token niet in, en "Hub-Token-Rotation: required" geldt
   alleen voor een onderbroken rotatie, niet voor een wachtende herkoppeling. `base_url` wordt alleen op type
   gecontroleerd; een ongeldige string wordt `null` met `base_url_genegeerd` (migratie 0011).
4. **Uitgaande adressen.** De canonieke vormen van §3.2 gelden ook voor elk beheerdersadres van de Hub
   (`hub/outbound.py`): `127.1`, `2130706433`, `0x7f000001` en `010.0.0.1` zijn ongeldig; `::ffff:127.0.0.1` is
   loopback.
5. **Noodlogin (C1.3-ASM-05/06).** De instelling "100.64.0.0/10 als privé" staat in een nieuwe tabel `hub_setting`
   (sleutel `noodlogin.cgnat_toestaan`), te wijzigen met `PUT /api/v1/auth/break-glass/cgnat` (admin,
   `Idempotency-Key`, audit, waarschuwing). Dat is geen `action_id` en de AI kan het niet voorstellen. Naast
   `invalid_totp` geeft ook een fout **eigen** wachtwoord binnen een geldige sessie (noodaccount instellen of roteren,
   wachtwoord wijzigen) 422: het is dezelfde situatie ("foute invoer binnen een geldige sessie") en een 401 zou de UI
   laten denken dat de sessie weg is. Inloggen zelf blijft 401.
6. **Scopes (C1.3-ASM-07).** Vast in code (`hub/scopes.py`), niet in de database: dan kan niemand ze wijzigen, ook
   geen beheerder; de Hub-UI toont ze per dienst. Naast `items` zijn ook de outbox (`/connector/v1/events`) en het bewijs
   (`/connector/v1/evidence`) van de Hub alleen voor gebruikers: daar zit beheerinformatie in (o.a. besluiten via
   `onboarding.decision.changed`) waarvoor geen dienstscope bestaat. Gemeten: geen dienst leest die routes.
7. **Momentopname (C1.3-ASM-08).** De `snapshot_id` is een vingerafdruk van de meting (`observed_at`), de filters en per
   app id, versie en gezondheid. Verandert een van die drie, dan geeft een oude cursor 409 `snapshot_changed`; de
   gezondheid hoort erbij omdat het totaal per pagina anders niet gelijk blijft. Sorteren op status (C01) zit in
   dezelfde momentopname.
8. **Domeinen en ernst (C1.3-ASM-09).** De regels van een eigenaar gelden alleen voor (`source_app`, domein) uit §7;
   `app.*` alleen `app.health.changed` over de eigen app, `service.*` alleen de vaste lijst (oude namen: informatie).
   Daarbuiten maakt een event geen incident (het blijft zichtbaar in de inbox). De werkwoorden van §7 zijn een gesloten
   lijst: woorden die de Hub vroeger als probleem las (`error`, `timeout`, `offline`, `expired`, …) zijn nu informatie.
   Ernst: `payload.ernst` met de vijf Peil-woorden; `payload.severity` geldt nog **deze** release (0.1.x) als overgang
   en vervalt in de volgende. De bronwaarde staat in `incident.ernst_bron` (migratie 0011) zodat de UI hem toont.
9. **sso.access.\* (C1.3-ASM-10).** Koppelen op (`issuer`, `sub`); ontbreekt `issuer`, dan alleen op `sub`. Alleen
   zonder `sub` (overgang) op de gebruikersnaam. Ook `sso.access.changed` trekt alleen sessies in; nieuwe rechten
   volgen pas bij de volgende OIDC-login via groep → rol.
10. **Connector-health en versheid (C1.3-ASM-11/12).** Het totaal is het slechtste van de gemelde status en alle checks
    (een worker die `down` is, maakt de dienst `down`, niet meer alleen `degraded`). De Hub leest `discover` voor
    `limits.max_age_s` en gebruikt min(bron, 900 s), dus nooit soepeler. `inventory_ttl_seconds` blijft instelbaar tot
    24 uur, maar de effectieve geldigheid is hooguit 900 s (`inventory_max_age_seconds`). Een verouderde meting heeft
    `reason_code: meting_verouderd`; de oude code `verouderd` blijft leesbaar voor opgeslagen waarnemingen. De
    oude jobs-checknamen (`job`, `queue`, `wachtrij`, `taken`) gelden nog deze release.
11. **Log-sink (C1.3-ASM-13).** Eerst de hele (al gecontroleerde) invoer schonen, dan voor opslag inkorten tot 2000
    tekens met de zichtbare markering " … [ingekort]" en `velden._bericht_ingekort`; de zoek-API geeft
    `bericht_ingekort` en `velden_ingekort`.
12. **Koppelstatus van een dienst in de Hub-UI (C1.3-ASM-16).** Nieuwe route `GET /api/v1/services/{id}/koppelstatus`
    (operator): live gelezen bij de dienst (`GET /connector/v1/hub-link`), alleen de witte lijst van §3.5 en de
    NL-melding van de dienst zelf, nooit opgeslagen. Weigert de dienst de Hub (401), dan zoekt de Hub in de openbare
    `/readyz` naar `koppelstatus_onleesbaar` (storing); anders "dienst weigerde". Onbereikbaar = onbekend.
13. **Executor (C1.3-ASM-03/04/14).** Een onleesbaar koppelbestand (geen JSON, andere major, ontbrekende velden,
    verkeerde eigenaar of rechten, symlink, of een toestand na een koppeling zonder `first_linked_at`) is fail-closed.
    De executor kent geen env-token (§3.9): herstel volgt in P2 met de TrueNAS-schrijfsleutel; de statuspagina zegt dat
    in de melding naast het vaste Peil-blok. `POST /api/v1/execute` vraagt nu eerst een dienst-JWT van de Hub (dan
    `Idempotency-Key`, dan de body) en weigert daarna nog steeds alles; een gebruikers-JWT kan geen acties aanbieden.
    De formulier-POST staat met reden in de statische uitzonderingslijst (RV10). Uvicorn vertrouwt geen
    `X-Forwarded-*` (`proxy_headers=False`).
14. **Peil 1.1.1.** Executor: gepinde sjabloonkopie 1.1.1 en een renderer in één doorgang die byte-gelijk getest is
    tegen `design/ontwerptaal/bouw/sjabloon.py`. Hub: tokenkopie 1.1.1 via `scripts/peil-kopie.mjs`; ondernavigatie op
    labelbreedte zonder vet actief item, statuspil met radius = halve regelhoogte, "verzonden" in plaats van
    "verstuurd". De Hub heeft geen domeinknoppen (huis): de regel "rand = -ink" is hier niet van toepassing.
15. **Eigen manifesten (C1.3-ASM-17).** Kop "platformcontract 1.3" en geen `HUB_*`. Bij de conformiteitsronde wachtten
    `healthcheck.monitor` en `accepted_findings` nog op de validator (appstore-en-fork 4e4e305 weigerde beide). Sinds
    C1.3-ASF-08 gecommit is (appstore-en-fork 1090fc9; gecontroleerd op 7b3159d) staan ze erin (onafhankelijke review,
    2026-11-10):
    - **Monitorplan op `/readyz`**, niet `/healthz` (zoals eerst gepland): `/healthz` blijft groen als de database of
      de geheimen weg zijn, `/readyz` niet; de koppeling telt daar niet mee (§5). 200, timeout 10 s, interval 60 s.
      Gelijk aan het eigen manifest van appstore-en-fork. De beheerder neemt het plan over in Uptime Kuma ("handmatig
      bevestigd", §9); het monitorplan zelf bouwen is C1.3-ASM-20 (P2).
    - **`accepted_findings`: alleen `digest_pending_release`** (eigen image vóór de eerste release), zodat `--strict`
      slaagt. De release-CI vult de digest; daarna moet deze regel weg (anders faalt `--strict`: geaccepteerde code die
      niet meer optreedt).
    - `provenance.license: GPL-3.0` (§1.1 besluit 8, gelijk aan `LICENSE`).
    - Bewaakt door `apps/api/tests/unit/test_eigen_manifesten.py` (tekstregels, met negatieve gevallen) en de CI-job
      `manifest`: de validator van appstore-en-fork op een vaste commit in `--strict`. Een nieuwe validatorversie is
      een bewuste stap (commit in `ci.yml` bijwerken).

## Gevolgen

- Diensten die de Hub-connector lazen (gemeten: geen) krijgen 403 `scope_ontbreekt` op `items`, `events` en
  `evidence`; `discover` en `health` blijven open voor elke dienst.
- Incidenten van diensten die buiten hun domein of met andere werkwoorden meldden, ontstaan niet meer. De diensten
  moeten de vaste namen van §7 volgen (conformiteitslijst, hoofdstukken 2–5).
- `hoog` escaleert niet meer (was kritiek): alleen `kritiek` escaleert.
- Open (later): P2-punten (C1.3-ASM-18/19/20), P3/P4-adapters (C1.3-ASM-21), P5 (C1.3-ASM-22), de catalogusroute voor
  `catalogus.lezen` (P2), `accepted_findings: digest_pending_release` weghalen na de eerste release, en het
  verwijderen van de overgangen (`payload.severity`, oude jobs-checknamen) in de release na 0.1.x.
