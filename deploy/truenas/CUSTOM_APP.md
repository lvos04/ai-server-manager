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

## 0. Eenmalig: images openbaar maken op GitHub

Een nieuw GHCR-pakket is standaard privé. Ga naar `https://github.com/lvos04?tab=packages` → pakket
**ai-server-manager** → *Package settings* → *Change visibility* → **Public**. Herhaal dit voor
**ai-server-manager-executor**. Controle: `https://ghcr.io/token?scope=repository:lvos04/ai-server-manager:pull` geeft
HTTP 200.

## 1. Twee datasets maken

**Datasets** → kies je pool → **Add Dataset**, twee keer, met *Dataset Preset* **Apps**:

| Dataset | Voor |
|---|---|
| `<pool>/<apps-map>/ai-server-manager` | Hub: ingebouwde database, `secrets/`, `backups/` |
| `<pool>/<apps-map>/ai-server-manager-executor` | executor: eigen identiteit en vault (gescheiden van de Hub) |

Rechten hoef je niet aan te passen: bij de eerste start maakt de app gebruiker `568` (apps) eigenaar van zijn eigen
submappen en verder van niets.

## 2. Formulier 1 — Hub (`ai-server-manager`)

**Apps** → **Discover Apps** → **Custom App**:

| Sectie | Veld | Waarde |
|---|---|---|
| Application Name | | `ai-server-manager` |
| Image Configuration | Repository | `ghcr.io/lvos04/ai-server-manager` |
| | Tag | `0.1.0` (altijd een exacte versie, nooit `latest`) |
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
| | Tag | `0.1.0` |
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

**Install.** De statuspagina `http://<NAS-adres>:30410` toont **"nog niet gekoppeld"**. In deze versie (fase P0) is
er nog geen koppelformulier en voert de executor **niets** uit (de allowlist is leeg). Voer hier dus nog geen
TrueNAS-API-key in. Koppelen (koppelcode uit de Hub + TrueNAS-key met schrijfrechten, alleen op deze pagina) volgt in
fase P2.

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

De executor (formulier 2) koppel je in deze versie nog **niet**; de onboarding legt dat uit (volgt in fase P2).

## Updaten en terugdraaien

- **Updaten:** app → **Edit** → Tag naar de nieuwe versie → **Update**. Zijn er databasewijzigingen, dan maakt de Hub bij
  de start eerst een geverifieerde back-up (`/appdata/backups`, *pre-upgrade*) en voert daarna de migraties uit. Een
  mislukte migratie laat de oude database ongemoeid. Een ZFS-snapshot vooraf blijft verstandig.
- **Terugdraaien:** alleen naar een tag met hetzelfde databaseschema, of eerst de back-up/snapshot van vóór de update
  terugzetten (tag-only rollback is niet veilig bij schemawijzigingen).

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
| Image kan niet worden opgehaald | Stap 0: het GHCR-pakket staat nog op privé. |

## Niet doen

- Geen *Install via YAML*, geen `custom_compose_config`, geen compose-bestand (compose in `deploy/dev/` is alleen voor
  ontwikkeling en CI).
- Geen `latest`-tag, geen privileged-modus, geen Docker-socket, geen wachtwoorden in Environment Variables.
