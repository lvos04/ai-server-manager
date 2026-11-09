# Installeren als standaard TrueNAS Custom App (twee formulieren, geen YAML)

De eerste installatie van het platform bestaat uit precies **twee** gewone Custom Apps die je in de TrueNAS-web-UI
aanmaakt: de **Hub** (`ai-server-manager`, alles-in-één) en de **executor** (`ai-server-manager-executor`). Daarna
installeert het platform alles via de TrueNAS-API vanuit de Hub (contract §2). Je gebruikt **nooit** *Install via YAML*,
geen compose-bestand, geen terminal en geen `install.sh`.

> **Verificatiestatus (eerlijk):** beide images zijn in een Linux/Docker-bouwomgeving gebouwd en gestart (healthcheck,
> start als root én als 568, herstart, harde kill, onbeschrijfbare map; zie `docs/platform-v2/EVIDENCE.json`). Het
> TrueNAS-formulier zelf is **NIET GEVALIDEERD (echte NAS)**: de veldnamen volgen de TrueNAS SCALE 24.10/25.04-UI en
> kunnen per versie iets afwijken. Waarden tussen `<…>` vul je zelf in; er staan hier bewust geen voorbeeld-IP's of
> poolnamen.

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
| Portal Configuration | Add | Name `Hub`, Protocol HTTP, Port `30400`, Path `/` |
| Storage Configuration | Add → Type | **Host Path** |
| | Mount Path | `/appdata` |
| | Host Path | `/mnt/<pool>/<apps-map>/ai-server-manager` (dataset uit stap 1) |
| | Read Only | **uit** |
| GPU Configuration | | **geen** |
| Resources Configuration | CPUs / Memory | bv. 2 CPU / 1024 MiB (meet zelf; in rust gebruikt de Hub weinig) |

Wat er **niet** in staat (bewust): geen Docker-socket-mount, geen extra hostpaden, geen host network, geen
privileged-modus.

**Install.** Open daarna **Apps → ai-server-manager → Logs**. Bij de eerste start staat daar een blok:

```
SETUPCODE (eenmalig, voor het eerste beheerdersaccount): XXXX-XXXX-XXXX
```

Open `http://<NAS-adres>:30400` en vul de setupcode in bij het eerste beheerdersaccount (in deze versie via de API
`POST /api/v1/setup/admin`; de web-UI met wizard volgt in de volgende versie). Code kwijt of verlopen (24 uur)? Herstart de
app: er verschijnt een nieuwe code en de oude vervalt.

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

## 4. Alleen-lezen-koppeling met TrueNAS (in de Hub)

1. Maak in TrueNAS een aparte gebruiker met alleen de rol **READONLY_ADMIN** en daarvoor een **API-key**
   (Credentials → API Keys). De Hub weigert een key met schrijfrechten (`key_too_privileged`).
2. Vul in de Hub besluit **D03** in (NAS-adres zoals jij het gebruikt, plus HTTPS-poort als die afwijkt).
3. Stel de key in (`PUT /api/v1/truenas/api-key`) en test (`POST /api/v1/truenas/test`). Gebruikt TrueNAS een
   zelfondertekend certificaat, dan toont de Hub de **SHA-256-vingerafdruk**: vergelijk die met System → Certificates en
   bevestig hem alleen als hij exact gelijk is. Pas daarna verstuurt de Hub de key.

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
| `oude postmaster.pid ... verwijderd` | Geen fout: de vorige stop was onverwacht (stroom/kill). |
| Poort bezet bij opslaan | Kies een andere vrije **Host Port**; de Container Port blijft `30400` / `30410`. |
| Image kan niet worden opgehaald | Stap 0: het GHCR-pakket staat nog op privé. |

## Niet doen

- Geen *Install via YAML*, geen `custom_compose_config`, geen compose-bestand (compose in `deploy/dev/` is alleen voor
  ontwikkeling en CI).
- Geen `latest`-tag, geen privileged-modus, geen Docker-socket, geen wachtwoorden in Environment Variables.
