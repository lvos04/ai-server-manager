export const meta = {
  name: 'p1-ogen-en-toegang',
  description: 'P1 (per groep): appcatalogus, monitoring, incidenten, SSO, import bestaande apps, manifests en simulators, met review',
  phases: [
    { title: 'Bouwen', detail: 'per repo het P1-werk' },
    { title: 'Web', detail: 'Hub-PWA P1-schermen' },
    { title: 'Review', detail: 'onafhankelijke controle en reparatie per repo' },
  ],
}

const COMMON = `Je werkt mee aan het programma "TrueNAS Home Platform V2". Taal voor alle documenten, UI-teksten, foutmeldingen en commitberichten: Nederlands (code-identifiers mogen Engels).

WERKMAP: /home/transcode/truenas-v2 bevat 11 git-repos naast elkaar (geen repo zelf): ai-server-manager, home-control-hub, appstore-en-fork, jelly-leon-platform, jelly-leon, jelly-leon-web, jelly-leon-clients, zoeken-en-persoonlijke-ai, media-guard-ultimate, media-source-optimizer, my_house. Er kunnen andere bouwers tegelijk werken, elk in een eigen repo. Wijzig en commit UITSLUITEND in jouw eigen repo (andere repos alleen lezen). ai-factory nooit aanraken.

LEES EERST (bindend): <repo>/docs/platform-v2/PLATFORM_CONTRACTEN.md (versie 1.1!), <repo>/docs/platform-v2/README.md, je eigen B-/I-/A-/promptdocs in <repo>/docs/platform-v2/, en <repo>/docs/platform-v2/EXCEL_TAKEN.json (jouw Excel-taken met acceptatiecriteria). Gedeelde architectuur: docs/platform-v2/01_ARCHITECTUUR (vooral 02_DATA_EIGENAARSCHAP, 03_RISICO_AUTONOMIE, 07_API_EN_EVENTSCHEMA, 08_UI_EN_INTERACTIES) en 05_TESTS. Het volledige pakket staat in /home/transcode/truenas-v2/ai-server-manager/docs/platform-v2/.

VASTE KEUZES GEBRUIKER: Python 3.12 FastAPI + PostgreSQL + Next.js/React PWA (alle schermen centraal in de Hub-UI van ai-server-manager; andere nieuwe apps zijn API-diensten met alleen een kleine statuspagina). INSTALLATIE: uitsluitend als STANDAARD TrueNAS Custom App (formulier: image+tag, poort, opslag) — NOOIT YAML, 'Install via YAML', custom_compose_config of docker compose als installatiemethode (compose alleen voor ontwikkeling/CI/E2E). Eén alles-in-één image per repo (ingebouwde PostgreSQL via unix-socket, API, worker; zie het werkende voorbeeld /home/transcode/truenas-v2/media-source-optimizer/deploy/allinone en docs/TRUENAS_CUSTOM_APP.md). Eerste installatie = twee handmatige Custom Apps (Hub + executor) via de TrueNAS-web-UI, daarna alles via de platform-UI/TrueNAS-API; derden-apps met meerdere containers via de officiële TrueNAS-catalogusapp. Geen terminal of install.sh voor de gebruiker. NAS-gegevens D01–D18 zijn onbekend: nooit voorbeeldwaarden (IP, poolnaam zoals "tank", versies) als echte waarden gebruiken; die komen uit de onboarding-wizard of uit gemeten TrueNAS-API-readback. Bestaande repos: alleen hiaten bouwen, nooit bestaande integriteit/rollback/monitoring dubbel bouwen of uitschakelen. Veiligheid volgens 03_RISICO_AUTONOMIE: geen shell/root voor AI, geen sh -c/sudo-endpoint, geen Docker-socket in containers, geen latest-tags (base images op @sha256-digest), boiler nooit schakelen, geen betaalde API-overage. Lokale AI-modellen optioneel en standaard uit. Jellyfin-fork: technische identiteit/API blijft 'Jellyfin', alleen de zichtbare naam wordt 'Jelly Leon'.

EERLIJKHEID (cruciaal): claim nooit dat iets geslaagd of gereed is wat je niet echt hebt uitgevoerd. Echte NAS-, hardware- en accounttests zijn hier onmogelijk → markeer als NIET GEVALIDEERD / Geblokkeerd. Simulatoren/fakes → "Sim-getest". Een ontbrekende functie geeft capability_unavailable/unknown, nooit gesimuleerd succes. Werk docs/platform-v2/EVIDENCE.json bij volgens §11 van de contracten (Excel-statussen; 'Gereed' en 'Geslaagd' NOOIT zetten).

OMGEVING: eigen Ubuntu 26.04-machine van de gebruiker (passwordless sudo; sudo alleen voor systeeminstallaties, nooit in repo-scripts) met 22 CPU's maar slechts 14,5 GiB RAM + 4 GiB swap, gedeeld met andere agents — geheugen is de echte grens. Beperk daarom parallelisme: per agent hooguit één zware build tegelijk, 'nice -n 10' voor zware builds, pytest -n 4 (of zonder -n), npm/next build één tegelijk, Gradle --max-workers=4 met org.gradle.jvmargs=-Xmx2g, dotnet -m:4, docker build hooguit één per agent. Zware stappen machinebreed serialiseren met flock (wacht netjes op elkaar): Gradle als 'flock /home/transcode/truenas-v2/.lokaal/gradle.lock ./gradlew --no-daemon ...' en image-builds als 'flock /home/transcode/truenas-v2/.lokaal/docker-build.lock docker buildx build ...'. Systeempakketten (sudo apt-get) alleen met -o DPkg::Lock::Timeout=600 en alleen als echt nodig; ffmpeg, mediainfo, acl, shellcheck, actionlint, jq, redis-server staan er al. Docker Engine (systeemdaemon, context 'default'; docker, buildx, compose) draait; de gebruiker zit in groep docker. python3.12 (/usr/bin/python3.12, deadsnakes), Node 22 + npm, pnpm 10 (corepack), Java 21, cmake/ninja; .NET 9 alleen via image mcr.microsoft.com/dotnet/sdk:9.0. Android SDK in ~/android-sdk (ANDROID_HOME; platform-tools, platforms;android-36, build-tools;36.0.0; extra pakketten met sdkmanager mogen). Gedeelde PostgreSQL 16 + pgvector op 127.0.0.1:5432 (user postgres, geen wachtwoord, alleen localhost): maak eigen databases met je repo-prefix. Redis op 127.0.0.1:6379. Playwright-browsers staan in ~/.cache/ms-playwright; 'npx playwright install chromium' (zonder --with-deps) voor de door de repo vastgezette versie mag. Internet is direct bereikbaar (géén proxy en géén eigen CA meer): GHCR, dl.google.com, Gradle, NuGet, npm en PyPI werken; containers hebben gewoon internet. De Dockerfiles houden hun optionele BuildKit-secret ca_bundle (RUN --mount=type=secret,id=ca_bundle,required=false ...), die is hier gewoon leeg — voeg nooit een CA of proxy toe. Wat in de oude sandbox geblokkeerd was (GHCR-blobs, Android SDK/Gradle, invent.kde.org, classList.js-archief, officiële TrueNAS-docs) opnieuw proberen en EVIDENCE.json bijwerken naar wat nu echt lukt. Gebruik een venv per repo (niet committen). Digests: docker buildx imagetools inspect <image>:<tag>; actuele stabiele versies via git ls-remote --tags (alleen lezen). Ruim build-artefacten en ongebruikte images op (docker image prune -f), commit nooit node_modules/.venv/bin/obj. Er kunnen onafgemaakte, niet-gecommitte bestanden van een afgebroken eerdere poging in je repo staan: beoordeel, hergebruik of verwijder ze.

GIT: branch ccr-c133d7a0-kuz1cv (staat al uitgecheckt). Kleine logische commits met NL-berichten; elke commit eindigt met precies deze regel:
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Doe vóór ELKE push eerst git pull --rebase origin ccr-c133d7a0-kuz1cv en push daarna met git push -u origin ccr-c133d7a0-kuz1cv (bij netwerkfout tot 4× opnieuw na 2/4/8/16 s). Geen PR's, geen force-push, geen geheimen committen, nooit een modelnaam of model-ID in commits, code of docs.

KWALITEIT: per onderdeel code + unit-, integratie- en E2E-tests (met simulators/fakes), OpenAPI-export, CI-workflow (.github/workflows), alles-in-één image + deploy/truenas/CUSTOM_APP.md (formuliervelden) + manifest met gepinde images en .env.example, ADR bij keuzes. Draai je tests echt en rapporteer exacte commando's en uitkomsten. Als het contract iets mist of tegenstrijdig is: kies de veiligste interpretatie, leg het vast in docs/adr en meld het onder contract_issues.

EINDRAPPORT: lever het gestructureerde eindrapport (repo, samenvatting NL, commits, tests_run, evidence_ids, blockers, contract_issues, followups).`

const RESULT = {
  type: 'object',
  properties: {
    repo: { type: 'string' },
    summary: { type: 'string' },
    commits: { type: 'array', items: { type: 'string' } },
    tests_run: { type: 'array', items: { type: 'object', properties: { command: { type: 'string' }, result: { type: 'string' } }, required: ['command', 'result'] } },
    evidence_ids: { type: 'array', items: { type: 'string' } },
    blockers: { type: 'array', items: { type: 'string' } },
    contract_issues: { type: 'array', items: { type: 'string' } },
    followups: { type: 'array', items: { type: 'string' } },
  },
  required: ['repo', 'summary', 'commits', 'tests_run', 'blockers', 'contract_issues', 'followups'],
}

const SVC = (pkg, port, alias) => `Scaffold volgens §10 (pakket '${pkg}', containerpoort/hostpoort-voorstel ${port}, Custom App-naam '${alias}'): FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL, connectorcontract §6 (niet-gebouwde functies geven eerlijk capability_unavailable), auth §4 (service-token + Hub-JWT via JWKS van HUB_URL, met caching en fail-closed), enrollment-client §3 (eenmalig token uit env → POST {HUB_URL}/api/v1/services/enroll; zonder Hub eerlijk 'niet gekoppeld' tonen; ook koppelen met koppelcode via de statuspagina), foutformaat, Idempotency-Key, healthz/readyz, kleine NL-statuspagina op GET /, alles-in-één image deploy/allinone (ingebouwde PostgreSQL 16 via unix-socket, procesbewaker, first-start-init van /appdata/secrets, root → 568, healthcheck; voorbeeld: MSO deploy/allinone), deploy/truenas/CUSTOM_APP.md (exacte velden van het standaard Custom App-formulier, NL, geen YAML), deploy/dev/compose.yaml (alleen ontwikkeling), deploy/manifest/${alias}.manifest.yaml (install.method custom_app), .env.example, CI (incl. image bouwen + starten + healthcheck) en release.yml, OpenAPI-export, ADR's.`

const reviewTask = (repo, fase, focus) => `Je bent onafhankelijke reviewer/QA voor REPO ${repo}, fase ${fase}. Bouwer(s) hebben net gewerkt (zie melding hieronder). Controleer en REPAREER zelf wat niet klopt (commit + push):
1. Draai alle tests opnieuw zoals de CI ze draait (lint, typecheck, unit, integratie, E2E). Faalt iets: oplossen.
2. Naleving PLATFORM_CONTRACTEN.md 1.1 §1–§12 (alles-in-één image als standaard Custom App, geen YAML-installatie, poort, auth/enrollment, foutformaat, Idempotency-Key, healthz/readyz, connectorcontract, events, geheimen in /appdata/secrets, 568, geen latest, digests).
3. Veiligheid: geen shell/sudo/Docker-socket, geen geheimen in repo/formulier/logs, invoervalidatie, autorisatie op elke route, nooit 'open bij fout', geen stale data als gezond.
4. Eerlijkheid: geen gesimuleerd succes; EVIDENCE.json klopt met wat echt getest is (nooit Gereed/Geslaagd).
5. Acceptatiecriteria van de ${fase}-taken in EXCEL_TAKEN.json: echt met tests afgedekt (inclusief negatieve scenario's)? Voeg ontbrekende tests toe.
6. CI-workflows geldig (actionlint); de alles-in-één image bouwt, start met lege /appdata, wordt healthy en herstart zonder dataverlies; OpenAPI-export actueel.
7. Docs in het Nederlands, geen voorbeeldwaarden als echte NAS-waarden, installatie zonder terminal en zonder YAML.
8. Controleer aan het eind dat 'git status' schoon is en alles gepusht is.
${focus}
Rapporteer de gevonden problemen en wat je repareerde.`

const ALL = [
  { group: 'hub', key: 'hub', repo: 'ai-server-manager', chain: [
    { label: 'catalogus-monitoring', phase: 'Bouwen', prompt: `REPO: ai-server-manager — FASE P1 "Ogen en toegang", backend deel 1. De P0-basis staat er (lees code, docs/adr, CHANGELOG, EVIDENCE.json en de P0-meldingen in git log). Lees B01, B09, I07, I08, I13, I23 en 01_ARCHITECTUUR/05_OPERATIES_EN_UPDATES.
1. B01-002 Centrale appcatalogus: register met adaptertype, runtime_id (stabiel over NAS-reboot), image/tag/digest, installatiewijze (custom_app/catalog_app), metadata, deep-link, datasets, resourcegrenzen, eigenaar, laatst getest; idempotente discovery uit de TrueNAS-inventaris (bestaande apps als MediaGuard/MSO/my_house verschijnen zonder installatie of mutatie); offline app → stale/unknown met timestamp, nooit gezond. Koppeling met appstore-entries via het dienstenregister waar beschikbaar (anders unknown).
2. B09-001 Metrics coverage: dekkingsmatrix welke bron welke metriek levert (TrueNAS reporting/realtime, Beszel, Uptime Kuma, eigen heartbeats), hiaten zichtbaar.
3. B09-002 App healthchecks: adapters Uptime Kuma (versie-detectie; /metrics met API-key en/of status-page-API), Beszel (hub-API), eigen heartbeat-endpoint voor eigen apps; healthy/degraded/down/unknown met observed_at; stale → unknown.
4. B09-003 Time-series en alerts: opslag in PostgreSQL met retentie/aggregatie (ruw → 5 min → 1 u), alertregels met drempel/duur/hysterese, geen pushstorm (dedupe, rate-limit, snooze).
5. B01-004 Observability: API voor live CPU/RAM/GPU/disk/netwerk van de NAS (alleen TrueNAS; mini-pc uitgesloten), met bron en laatst bijgewerkt.
6. Gotify-adapter (notification.send R0) en meldingskanalen.
Tests: unit + integratie + E2E tegen in-repo fakes (Uptime Kuma, Beszel, Gotify, TrueNAS); de simulators in /home/transcode/truenas-v2/jelly-leon-platform/e2e/simulators mag je lezen/gebruiken maar niet wijzigen. OpenAPI bijwerken. EVIDENCE.json voor B01-002, B01-004, B09-001…003 naar waarheid. Commit per onderdeel en push.` },
    { label: 'incidenten-sso', phase: 'Bouwen', prompt: `REPO: ai-server-manager — FASE P1 "Ogen en toegang", backend deel 2. Deel 1 (catalogus, monitoring) is net gebouwd (zie melding). Lees B01, B09, B13 (Hub-kant) en 05_OPERATIES_EN_UPDATES.
1. B01-005 + B09-004 Incidenten-inbox en logcorrelatie: incidenten met severity, bron, eerste/laatste gebeurtenis, onderliggende events, root-cause-hypothese met zekerheid + 'toon bewijs', dedupe/correlatie/snooze, readback; logs alleen geschoond (secrets/tokens/IP-redactie) en beperkt; 'ik weet het niet' is een geldige uitkomst. Events (§7) en healthwijzigingen voeden incidenten.
2. B09-005 Out-of-band: Uptime Kuma + Gotify blijven ook zonder Hub melden (EX22) — documenteer en test dat de Hub niet in dat pad zit; EX23: geen claim van out-of-band bij volledige NAS-uitval zonder externe host (eerlijke UI-tekst + docs).
3. B09-006 Operator-runbooks: per scenario uit 05_OPERATIES (service offline, DB-migratie mislukt, quota/disk vol, slechte deployment, Tailscale/Cloudflare-lockout, Jellyfin-clientprobleem, Gree unknown, MSO-provideruitval): observeren → isoleren → mitigeren → rollback → bewijs → oorzaak, gekoppeld aan incidenttypen.
4. B01-006 Gebruikers en SSO (Hub-kant): OIDC-login (Authorization Code + PKCE) tegen een configureerbare issuer (Authentik), groep→rol-mapping, lokaal break-glass-admin blijft werken als OIDC faalt, sessie-intrekking; tests met een in-repo OIDC-fake. Authentik zelf configureren is van home-control-hub (B13).
5. Audit-log: append-only met hash-ketting en geschoonde details voor alle beheerhandelingen.
EVIDENCE.json voor B01-005, B01-006, B09-004…006. Commit per onderdeel en push.` },
    { label: 'web', phase: 'Web', prompt: `REPO: ai-server-manager — FASE P1, Hub-PWA. De P1-backend is net gebouwd (zie meldingen); lees de bijgewerkte OpenAPI. Lees 08_UI_EN_INTERACTIES.
Schermen: Apps (lijst + detail met tabs Status, Metrieken, Logs (geschoond), Versies, Acties — acties nog uitgeschakeld met uitleg 'volgt in P2'), Problemen-inbox + incidentdetail (tijdlijn, bewijs, hypothese met zekerheid, runbook), Home-kaarten met echte data + bron + laatst bijgewerkt, Server-metrieken (toegankelijke grafieken, licht/donker), Instellingen: gebruikers/rollen, SSO (OIDC-config + test), meldingskanalen, monitoringbronnen (Uptime Kuma/Beszel/Gotify koppelen met verbindingstest). Geen nepdata; onbekend blijft onbekend. Playwright op 360/390/768/1440 tegen de echte API + fakes, screenshots naar docs/screenshots/p1/. Alles-in-één image opnieuw bouwen en de schermen daarin controleren. EVIDENCE.json aanvullen. Commit en push.` },
  ], review: reviewTask('ai-server-manager', 'P1', 'Extra focus: stale → unknown overal; geen pushstorm; logs geschoond; OIDC-fout laat break-glass werken en geeft nooit open toegang; audit-keten niet te wijzigen.') },

  { group: 'svc', key: 'hch', repo: 'home-control-hub', chain: [
    { label: 'sso', phase: 'Bouwen', prompt: `REPO: home-control-hub — FASE P1: B13-002…B13-005 (Authentik/SSO). Lees B13, PROMPT_B13, I09, EXCEL_TAKEN.json en de P0-code.
0. NULMETING eerst, vóór je iets wijzigt: draai de volledige bestaande CI-suite zoals .github/workflows/ci.yml (ruff check + format --check, mypy, pytest, alembic up/down op een eigen DB, OpenAPI-drift, tests/e2e, pip-audit, en de image-rooktest deploy/allinone/smoke-test.sh) en rapporteer elk commando met uitkomst in tests_run met prefix 'NULMETING:'. Faalt er al iets vóór jouw werk: onderzoek of het een omgevingsprobleem van deze machine is of een echte fout, en meld dat apart.
Let op: contract 1.2 is nog niet vastgesteld (zie /home/transcode/truenas-v2/ai-server-manager/docs/platform-v2/OVERDRACHT/STATUS.md, sectie 'Contract 1.2', alleen lezen). Bouw volgens 1.1, maar maak keuzes die verenigbaar zijn met de 1.2-punten (env HUB_ENROLLMENT_TOKEN, verzoeken > 1 MiB → 413, JWT-replaycache op jti, JWKS-pinning bij enrollment, koppelen via statuspagina alleen vóór eerste koppeling met rate-limit, break-glass/noodlogin in de Hub) en meld afwijkingen onder contract_issues. De andere repos (behalve home-control-hub) zijn op dit moment ALLEEN-LEZEN: daar nooit iets wijzigen, committen of pushen.
1. Authentik-integratie via de officiële Authentik-API (versie-detectie, token via de vault): voor de Hub een OAuth2/OIDC-provider + application aanmaken als R2-voorstel (preview/diff/preview_hash; toepassen alleen met een door de Hub ondertekend ExecutionRequest volgens §8 — tot de executor in P2 bestaat: alleen preview en eerlijk 'nog niet toepasbaar').
2. B13-003 SSO-mapping per app: per catalogus-app vastleggen of OIDC echt ondersteund wordt (bron: officiële docs-URL + verificatiestatus), anders native login houden; groepen → rollen.
3. B13-004 Audit en rechten: logins/rolwijzigingen uit Authentik-events lezen, afwijkingen als events (§7) naar de Hub.
4. B13-005 Back-up en upgrade van Authentik: configuratie-export via API/blueprints, pre-upgrade-gate, herstelcheck. Authentik zelf wordt via de TrueNAS-catalogusapp geïnstalleerd (niet door deze repo).
5. In-repo Authentik-fake voor tests. Alles wat een echte Authentik of domeinnaam (D17) vraagt: Geblokkeerd.
EVIDENCE.json voor B13-002…005. Commit en push.` },
  ], review: reviewTask('home-control-hub', 'P1', 'Extra focus: Authentik-token nooit in logs; geen wijziging zonder ondertekend verzoek; SSO-claims per app alleen met bronvermelding.') },
  { group: 'svc', key: 'app', repo: 'appstore-en-fork', chain: [
    { label: 'import', phase: 'Bouwen', prompt: `REPO: appstore-en-fork — FASE P1: B08-002 Import bestaande apps + APP-01…APP-20. Lees B08, I26, A01–A20, APP_REGISTER, EXCEL_TAKEN.json en de P0-code.
1. Haal de app-inventaris via de Hub-API (service-token na enrollment; endpoints uit /home/transcode/truenas-v2/ai-server-manager/docs/openapi) — de appstore krijgt zelf geen TrueNAS-key. Koppel aan catalogus-entries (bekende apps uit A01–A20 en APP_REGISTER), idempotent; status 'adopted' met eigenaar, huidige tag/digest, installatiewijze, datasets, poorten, afhankelijkheden. Onbekende apps blijven 'onbekend', nooit gegokt.
2. Beslisregister per app: voorgenomen besluit + controlelijst uit het A-document als afvinkbare checks met bewijs; decommission-procedure uit I26 als plan (uitvoering is R2/R3 via lifecycle/executor; hier alleen voorbereiden; nooit data verwijderen).
3. Manifests voor bestaande apps alleen voor adoptie/inventaris (install.method catalog_app of custom_app volgens wat de app nu is), geen herinstallatie.
4. Tests met een Hub-fake. EVIDENCE.json voor B08-002 en APP-01…20 (Geblokkeerd: echte NAS-inventaris/gebruikerstest nodig).
Commit en push.` },
  ], review: reviewTask('appstore-en-fork', 'P1', 'Extra focus: import is idempotent, raakt niets aan, en verzint geen versies of eigenaren.') },

  { group: 'plat', key: 'plat', repo: 'jelly-leon-platform', chain: [
    { label: 'manifests-sims', phase: 'Bouwen', prompt: `REPO: jelly-leon-platform — FASE P1. Lees I01, I02, I07, I08, I09, I13, I23, B08, EXCEL_TAKEN.json, de P0-code, docs/platform-v2/TRUENAS_APP_API.md en het manifestschema in /home/transcode/truenas-v2/appstore-en-fork/schemas.
1. Installeerbare manifests (manifeststandaard §9, gevalideerd met de appstore-validator) voor I07 Beszel, I08 Uptime Kuma, I13 Gotify (standaard Custom App met één gepinde image, of catalogusapp als TrueNAS die aanbiedt — controleer de actuele TrueNAS-catalogus via github.com/truenas/apps), I09 Authentik (TrueNAS-catalogusapp, vaste versie), I23 Hub + executor (de twee handmatige Custom Apps, verwijzing naar INSTALLATIE.md). Actuele stabiele versies + @sha256-digests; parameters uit wizard/datasetkiezer/geheimen, geen voorbeeldwaarden.
2. I01/I02 als checklist-manifests (of eigen formaat als de standaard dat niet kent — meld dan onder contract_issues).
3. Simulators in e2e/simulators/: beszel, uptime-kuma (alleen API-delen die de Hub gebruikt), gotify, authentik (OIDC discovery/token/userinfo/JWKS + de beheer-API-delen die home-control-hub gebruikt) — protocol gedocumenteerd, met foutinjectie.
4. Installatie-rooktest zonder YAML: bouw lokaal de alles-in-één images uit ../ai-server-manager (Hub + executor) zonder in die repo te committen; start ze zoals de twee Custom Apps (docker run met één volume en één poort elk), haal de setupcode uit de logs, maak een admin aan via de API, doorloop de wizard tegen de TrueNAS-simulator, en installeer daarna via de lifecycle (alleen voor zover P2-uitvoering al bestaat; anders alleen plan/preview) een app in de simulator als standaard Custom App. Rapporteer eerlijk wat werkt en wat nog niet.
5. EVIDENCE.json voor de I01/I02/I07/I08/I09/I13/I23-stappen (installatie op echte NAS: Geblokkeerd).
Commit en push.` },
  ], review: reviewTask('jelly-leon-platform', 'P1', 'Extra focus: geen enkel manifest gebruikt compose of latest; digests kloppen (controleer er minstens drie met imagetools); simulators gedragen zich als de gedocumenteerde API en foutinjectie werkt.') },
]

const ITEMS = ALL.filter((i) => (args && args.groups ? args.groups.includes(i.group) : true) && (args && args.keys ? args.keys.includes(i.key) : true))
log(`Groep(en): ${(args && args.groups) ? args.groups.join(', ') : 'alle'} — ${ITEMS.length} repo('s)`)

const results = await pipeline(
  ITEMS,
  async (item) => {
    const out = []
    for (const step of item.chain) {
      const prev = out.length ? `\n\nMELDING VORIGE AGENT(S):\n${JSON.stringify(out)}` : ''
      const r = await agent(`${COMMON}\n\n${step.prompt}${prev}`, { label: `${item.key}:${step.label}`, phase: step.phase, schema: RESULT })
      if (!r) break
      out.push(r)
    }
    return out.length ? out : null
  },
  async (prev, item) => {
    if (!prev) return null
    const r = await agent(`${COMMON}\n\n${item.review}\n\nMELDING VORIGE AGENT(S):\n${JSON.stringify(prev)}`, { label: `review:${item.key}`, phase: 'Review', schema: RESULT })
    return { item: item.key, build: prev, review: r }
  },
)
return results
