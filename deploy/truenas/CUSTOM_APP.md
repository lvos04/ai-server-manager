# Installeren als standaard TrueNAS Custom App (twee formulieren, geen YAML)

De eerste installatie van het platform bestaat uit precies **twee** gewone Custom Apps die je in de TrueNAS-web-UI
aanmaakt: de **Hub** (`ai-server-manager`, alles-in-één) en de **executor** (`ai-server-manager-executor`). Daarna
installeert het platform alles via de TrueNAS-API vanuit de Hub (contract §2). Je gebruikt **nooit** *Install via YAML*,
geen compose-bestand, geen terminal en geen `install.sh`.

> **Verificatiestatus (eerlijk):** beide images zijn in een Linux/Docker-bouwomgeving gebouwd en gestart (healthcheck,
> start als root én als 568, herstart, harde kill, onbeschrijfbare map; zie `docs/platform-v2/EVIDENCE.json`). De
> web-UI in de Hub-image is daar ook getest: lege `/appdata` → setupcode in de log → beheerder aanmaken in de browser →
> herstart zonder dataverlies, en de volledige Playwright-suite tegen de image (met een gesimuleerde TrueNAS). Het
> TrueNAS-formulier zelf is **NIET GEVALIDEERD (echte NAS)**: de veldnamen volgen de TrueNAS SCALE 24.10/25.04-UI en
> kunnen per versie iets afwijken. Waarden tussen `<…>` vul je zelf in; er staan hier bewust geen voorbeeld-IP's of
> poolnamen.

> **Nog niet uitgebracht:** de tag `0.1.0` bestaat op GHCR pas nadat release `v0.1.0` is gemaakt (`release.yml`; zie
> `CHANGELOG.md`). Tot dan kan TrueNAS de image niet ophalen; vul dus geen andere tag (en zeker niet `latest`) in.

## 0. Image en tag (publiek, met digest)

De images staan op GHCR en worden **publiek** zodra de scan van besluit 3 klaar is (contract 1.3 §2.1); dan heb je
**geen** registry-login nodig. De exacte tag én digest van een release staan in de release-bijlage
`release/digests.json` (gemaakt door `release.yml`). Vul de tag in het formulier in als
**`<versie>@sha256:<64 hex>`**, bijvoorbeeld `0.1.0@sha256:<digest uit digests.json>`. Dat is geldige Docker-syntax:
TrueNAS maakt er `ghcr.io/lvos04/ai-server-manager:<versie>@sha256:…` van en haalt dan precies die image op.

> **NIET GEVALIDEERD (echte NAS):** of het TrueNAS-formulier een tag met `@` accepteert en of TrueNAS met zo'n tag nog
> updates detecteert, is niet op een echte NAS getest (contract 1.3 §2.2). Weigert het formulier de tag, vul dan
> alleen de exacte versie in (bv. `0.1.0`, nooit `latest`). De Hub leest na elke installatie of update via de
> executor de digest terug en stopt bij een afwijking.

**Terugval: registry-login (alleen als de image nog privé is).** Zolang het pakket nog niet publiek is, kan TrueNAS het
alleen ophalen met een registry-login: TrueNAS → **Apps → Configuration → Docker Registries → Add** (menunamen verschillen per versie), registry
`ghcr.io`, je GitHub-gebruikersnaam en een token dat **alleen pakketten mag lezen** (`read:packages`). Dat token is een
geheim van jou in TrueNAS: nooit in een formulierveld van de app, in een manifest, in Git of in een log. Gedrag van
TrueNAS met GHCR-tokens: **NIET GEVALIDEERD (account/echte NAS)**. Beheerder van de repo: pakket publiek maken gaat via
`https://github.com/lvos04?tab=packages` → pakket → *Package settings* → *Change visibility* → **Public** (pas na de
scan uit besluit 3).

## 1. Twee datasets maken

**Datasets** → kies je pool → **Add Dataset**, twee keer, met *Dataset Preset* **Apps**:

| Dataset | Voor |
|---|---|
| `<pool>/<apps-map>/ai-server-manager` | Hub: ingebouwde database, `secrets/`, `backups/`, `audit/` (anker van het auditspoor) |
| `<pool>/<apps-map>/ai-server-manager-executor` | executor: eigen identiteit en vault (gescheiden van de Hub) |

Rechten hoef je niet aan te passen: bij de eerste start maakt de app gebruiker `568` (apps) eigenaar van zijn eigen
submappen en verder van niets.

## 2. Formulier 1 — Hub (`ai-server-manager`)

**Apps** → **Discover Apps** → **Custom App**:

| Sectie | Veld | Waarde |
|---|---|---|
| Application Name | | `ai-server-manager` |
| Image Configuration | Repository | `ghcr.io/lvos04/ai-server-manager` |
| | Tag | `<versie>@sha256:<digest>` uit `release/digests.json` (stap 0); terugval: alleen de exacte versie, nooit `latest` |
| | Pull Policy | *Pull the image if it is not already present on host* |
| Container Configuration | Entrypoint / Command | **leeg laten** |
| | Timezone | je eigen tijdzone |
| | Environment Variables | **leeg laten** (geen wachtwoorden of geheimen in het formulier) |
| | Restart Policy | *Unless Stopped* |
| | Disable Builtin Healthcheck | **uit** (de image heeft een eigen healthcheck) |
| Security Context | Privileged | **uit** |
| | Capabilities | **geen** toevoegen |
| | Custom User | **uit** (de Hub regelt de rechten zelf en draait daarna als 568) |
| Network Configuration | Host Network | **uit** |
| | Ports → Add | Container Port `30400`, Host Port `30400` (of een andere vrije poort), Protocol TCP |
| Portal Configuration | Add | Name `Hub`, Protocol HTTP, Port `30400`, Path `/` (de web-UI) |
| Storage Configuration | Add → Type | **Host Path** |
| | Mount Path | `/appdata` |
| | Host Path | `/mnt/<pool>/<apps-map>/ai-server-manager` (dataset uit stap 1) |
| | Read Only | **uit** |
| GPU Configuration | | **geen** |
| Resources Configuration | CPUs / Memory | bv. 2 CPU / 1024 MiB (in de bouwomgeving gebruikte de Hub met web-UI in rust ±250 MiB; meet zelf) |

Wat er **niet** in staat (bewust): geen Docker-socket-mount, geen extra hostpaden, geen host network, geen
privileged-modus. Of het standaardformulier *no new privileges* kan zetten verschilt per versie (niet gecontroleerd op een
echte NAS); de image zet die vlag daarom zelf voor al zijn processen, direct nadat hij als root de eigenaar van
`/appdata` heeft geregeld (geldt ook voor de executor; de rooktest controleert `NoNewPrivs: 1` per proces).

**Install.** Open daarna **Apps → ai-server-manager → Logs**. Bij de eerste start staat daar een blok:

```
SETUPCODE (eenmalig, voor het eerste beheerdersaccount): XXXX-XXXX-XXXX
```

Open daarna de Hub in je browser: **Apps → ai-server-manager → Web UI** (of `http://<NAS-adres>:30400`, met de
hostpoort die je koos). De web-UI opent op **Eerste start** en legt daar ook uit waar de code staat:

1. Vul de setupcode uit de log in (staat hij er meer dan eens, dan geldt de onderste).
2. Kies een gebruikersnaam, eventueel een weergavenaam en een wachtwoord van minstens 12 tekens.
3. **Beheerder aanmaken** → je bent ingelogd en komt in de **onboarding** (besluiten D01–D18).

Code kwijt of verlopen (24 uur)? Herstart de app: er verschijnt een nieuwe code en de oude vervalt. Na de eerste
beheerder toont de Hub nooit meer een setupcode, ook niet na een herstart.

Alles gaat via die ene poort: de web-UI zet `/api/*`, `/connector/*`, `/healthz` en `/readyz` intern door naar de API,
die alleen binnen de container (127.0.0.1) luistert. Je hoeft dus geen tweede poort open te zetten.

> **HTTPS en offline:** de Hub werkt gewoon via `http://<NAS-adres>:30400`. Browsers staan een offline-schil en
> "installeren als app" (PWA) alleen toe via HTTPS (of op `localhost`); via HTTP staat onder **Instellingen → Over de
> Hub** daarom eerlijk "Offline-schil: niet actief". HTTPS volgt met besluit D17.

## 3. Formulier 2 — executor (`ai-server-manager-executor`)

| Sectie | Veld | Waarde |
|---|---|---|
| Application Name | | `ai-server-manager-executor` |
| Image Configuration | Repository | `ghcr.io/lvos04/ai-server-manager-executor` |
| | Tag | `<versie>@sha256:<digest>` van de executor uit `release/digests.json` (stap 0); terugval: alleen de exacte versie |
| | Pull Policy | *Pull the image if it is not already present on host* |
| Container Configuration | Entrypoint / Command / Environment Variables | **leeg laten** |
| | Timezone | je eigen tijdzone |
| | Restart Policy | *Unless Stopped* |
| Security Context | Privileged | **uit** · Capabilities: **geen** · Custom User: **uit** |
| Network Configuration | Host Network | **uit** |
| | Ports → Add | Container Port `30410`, Host Port `30410`, Protocol TCP |
| Portal Configuration | Add | Name `Executor`, Protocol HTTP, Port `30410`, Path `/` |
| Storage Configuration | Add → Type | **Host Path** |
| | Mount Path | `/appdata` |
| | Host Path | `/mnt/<pool>/<apps-map>/ai-server-manager-executor` (eigen dataset, **niet** die van de Hub) |

**Install.** De statuspagina `http://<NAS-adres>:30410` toont **"nog niet gekoppeld"**. De executor voert **niets**
uit zolang hij niet gekoppeld is en geen TrueNAS-sleutel met schrijfrechten heeft. Er zijn geen omgevingsvariabelen
nodig: de executor koppelt nooit met een `HUB_ENROLLMENT_TOKEN`, alleen met een koppelcode op zijn eigen statuspagina
(contract 1.3 §3.9).

**Koppelen met de Hub (eenmalig):**

1. Maak in de Hub een **koppelcode voor `ai-server-manager-executor`** (30 minuten geldig). De Hub toont daarbij de
   **Hub-vingerafdruk** (`XXXX-XXXX-XXXX-XXXX`). Zolang het scherm "Diensten" in de Hub-UI er nog niet is (dat wacht
   op de ontwerpstap, contract §13), maak je de code via de API-documentatie van de Hub (`/api/docs`,
   `POST /api/v1/services/pairing-codes` met `{"app_id": "ai-server-manager-executor"}`) terwijl je als beheerder bent
   ingelogd.
2. Open de statuspagina van de executor en vul **Hub-adres** (`http://<NAS-adres>:<hostpoort van de Hub>`),
   **koppelcode** en **Hub-vingerafdruk** in → **Koppelen**. De executor controleert de vingerafdruk zelf; klopt die
   niet, dan slaat hij niets op.
3. Daarna toont de statuspagina "gekoppeld", het Hub-adres en dezelfde vingerafdruk. Het koppelformulier verdwijnt.

**TrueNAS-sleutel met schrijfrechten (eenmalig, op dezelfde pagina):**

1. Maak in TrueNAS een **aparte gebruiker voor de executor** met een rol die apps en snapshots mag wijzigen, en
   daarvoor een **API-key** (Credentials → API Keys; menunamen verschillen per versie). Gebruik **niet** de
   alleen-lezen-key van de Hub: die weigert de executor (`schrijfrechten_ontbreken`).
2. Open de statuspagina via het **IP-adres van de NAS** en plak de sleutel. De executor toont eerst alleen het
   **NAS-adres** en de **SHA-256-vingerafdruk van het TrueNAS-certificaat**; de sleutel is dan nog niet verstuurd.
   Vergelijk de vingerafdruk teken voor teken met wat je browser toont bij het slotje van de TrueNAS-web-UI.
3. Klopt hij, plak dan dezelfde sleutel opnieuw en bevestig (binnen 15 minuten). De executor test de sleutel live,
   bewaart hem versleuteld in `/appdata/secrets` en toont daarna alleen de laatste 4 tekens. De Hub ziet deze sleutel
   nooit.
4. Luistert de TrueNAS-API op een ander adres dan de executorpagina, zet dan bij **Environment Variables**
   `EXECUTOR_TRUENAS_HOST` (en zo nodig `EXECUTOR_TRUENAS_PORT`). Alleen dan; standaard is er geen variabele nodig.

Adres en certificaat liggen daarna vast. **Sleutel vervangen**, **Ontkoppelen van de Hub** en het **vrijgeven** van een
gestopte executor (na een afwijking) doe je op dezelfde pagina onder "Ontkoppelen of sleutel vervangen", telkens met de
huidige sleutel. Vrijgeven = de huidige sleutel invullen, "Nieuwe sleutel" leeg laten en "Sleutel vervangen" kiezen.

Vanaf dat moment voert de executor alleen uit wat de Hub ondertekend aanlevert en wat op de vaste lijst in de image
staat (apps starten/stoppen/herstarten, installeren, bijwerken, terugzetten, verwijderen zonder data, snapshots). Hij
controleert alles zelf opnieuw en leest na elke wijziging terug of het klopt. Sim-getest tegen de echte Hub-API en een
nagebouwde TrueNAS-API in de bouwomgeving; op een echte NAS **NIET GEVALIDEERD**.

## 4. Alleen-lezen-koppeling met TrueNAS (in de Hub-web-UI)

**Onboarding → TrueNAS koppelen (alleen-lezen)**. De pagina loopt de stappen met je door:

1. **NAS-adres (besluit D03):** het adres waarmee jij de TrueNAS-web-UI opent, zonder `https://` en zonder pad, en
   alleen als het afwijkt de HTTPS-poort. De Hub neemt nooit zelf een adres aan.
2. **Alleen-lezen-gebruiker en API-key:** maak in TrueNAS een aparte gebruiker met alleen de rol **Read-only
   Administrator** (`READONLY_ADMIN`) en daarvoor een **API-key** (Credentials → API Keys; menunamen verschillen per
   versie). Plak de key in de Hub. Hij wordt versleuteld bewaard; de Hub toont daarna alleen de laatste 4 tekens.
3. **Verbinding testen.** Gebruikt TrueNAS een zelfondertekend certificaat, dan toont de Hub de **SHA-256-vingerafdruk**.
   Vergelijk die teken voor teken met wat je browser toont bij het slotje van de TrueNAS-web-UI (of Credentials →
   Certificates) en bevestig alleen als hij exact gelijk is. Pas daarna verstuurt de Hub de key.
4. Een key met schrijfrechten wordt geweigerd (`key_too_privileged`); een onbekende of ingetrokken key geeft een
   gerichte melding met advies (`auth_failed`).
5. **Inventaris ophalen en meten:** daarna haal je de inventaris op (Server) en laat je D01, D03, D06 en D07 alleen-lezen
   meten. D02 kies je zelf uit de gemeten pools en datasets.

De executor (formulier 2) koppel je met een koppelcode zoals in stap 3; daar vul je ook zijn eigen TrueNAS-sleutel
met schrijfrechten in. De Hub houdt alleen de alleen-lezen-key.

## 5. Wijzigingen laten uitvoeren (voorstel → goedkeuring → uitvoering)

Elke wijziging op de NAS loopt via één weg: een **voorstel** in de Hub, een vaste **risicoklasse** uit het beleid in de
image (R0–R3; niemand kan die klasse zelf kiezen), bij R2/R3 een **goedkeuring door een beheerder** voor precies de
getoonde wijziging (15 minuten geldig, één keer bruikbaar), en dan de **executor**. Verandert de app tussen bekijken en
uitvoeren, dan vervalt de goedkeuring en volgt een nieuwe preview.

- **Altijd geweigerd:** shell- of root-opdrachten, verwijderen van datasets, pools of media, alles met de boiler, en
  elke wijziging aan Emby. Emby wordt herkend aan de appnaam, de catalogusapp en de image. Van een gestopte Custom App
  toont TrueNAS geen image; dan is niet uit te sluiten dat het Emby, MediaGuard of de mediaserver is, en weigert het
  platform elke actie op die app (`doel_niet_herkenbaar`), ook met goedkeuring.
- **Geblokkeerd tot het is opgelost:** pool niet gezond of onbekend, back-up niet groen, executor niet gekoppeld,
  noodstop aan. Zo'n blokkade is niet weg te klikken, ook niet door een beheerder.
- **Verwijderen van een app** haalt alleen de containers weg; datasets en data blijven staan.
- **Bijwerken en terugzetten** vragen een geverifieerd herstelpunt van de app. Die herstelpunten bestaan in deze
  versie nog niet; tot dan weigert de Hub die twee acties eerlijk (`backup_checkpoint_ontbreekt`).
- **Noodstop:** een beheerder legt alle uitvoering in één keer stil.

De schermen hiervoor in de Hub-UI zijn nog niet gebouwd; tot dan loopt dit via de API-documentatie van de Hub
(`/api/docs`, onderdeel "acties en goedkeuringen"), ingelogd als beheerder.

## Updaten en terugdraaien

- **Updaten:** app → **Edit** → Tag naar de nieuwe `<versie>@sha256:<digest>` (of alleen de versie, zie stap 0) →
  **Update**. Zijn er databasewijzigingen, dan maakt de Hub bij
  de start eerst een geverifieerde back-up (`/appdata/backups`, *pre-upgrade*) en voert daarna de migraties uit. Een
  mislukte migratie laat de oude database ongemoeid. Een ZFS-snapshot vooraf blijft verstandig.
- **Terugdraaien:** een Custom App heeft geen catalogusversies: TrueNAS' *Roll Back* werkt hier niet voor een andere
  image-tag (contract 1.3 §2.2, NIET GEVALIDEERD op een echte NAS). Terugdraaien = **Edit** → de vorige tag (met
  digest) weer invullen → **Update**, alleen naar een tag met hetzelfde databaseschema; anders eerst de
  back-up/snapshot van vóór de update terugzetten (tag-only rollback is niet veilig bij schemawijzigingen).

## Problemen

| Melding in de app-log | Oplossing |
|---|---|
| `FOUT: /appdata bestaat niet` | De Storage-regel ontbreekt of Mount Path is niet exact `/appdata`. |
| `FOUT: geen schrijfrechten op /appdata/...` | *Custom User* staat aan met een andere gebruiker: zet het uit, of geef 568 schrijfrechten. |
| `AI-runner niet gestart` | De container draait niet als root (Custom User aan). Geen probleem in deze versie: AI staat uit. |
| Browser toont "De Hub-API is (nog) niet bereikbaar" | De app start nog op (database/migraties); wacht tot de app *Running/healthy* is. Blijft het, kijk in de Logs. |
| Web-UI meldt "Offline-schil: niet actief" | Verwacht via `http://`: offline gebruik en installeren als app vereisen HTTPS (volgt met D17). |
| `oude postmaster.pid ... verwijderd` | Geen fout: de vorige stop was onverwacht (stroom/kill). |
| Poort bezet bij opslaan | Kies een andere vrije **Host Port**; de Container Port blijft `30400` / `30410`. |
| Image kan niet worden opgehaald | Stap 0: het GHCR-pakket staat nog op privé (registry-login als terugval), of de digest hoort niet bij deze versie. |
| Formulier weigert de tag met `@sha256:` | Vul alleen de exacte versie in (stap 0); de digest-readback blijft de controle. |

## Niet doen

- Geen *Install via YAML*, geen `custom_compose_config`, geen compose-bestand (compose in `deploy/dev/` is alleen voor
  ontwikkeling en CI).
- Geen `latest`-tag, geen privileged-modus, geen Docker-socket, geen wachtwoorden in Environment Variables.
