# Node-RED — installatie, update, test en herstel

**Rol:** Visuele automatiseringen.  
**Aanpak:** Nieuw installeren.  
**Bron:** https://nodered.org/docs/getting-started/docker.  
**Versiebeleid:** Actuele officiële image gepind.

## 1. Vooraf controleren
Hub action-policy actief voordat muterende flows ingeschakeld worden.

**Toegang / netwerk:** Editor alleen LAN/SSO, geen externe admin-port.

**Data / mounts:** /data persistent. Node-RED maakt de sleutel voor zijn credentials zelf (`flowEncryptionType: "system"`, in `/data/.config.runtime.json`); er komt geen aparte sleutel en geen `credentialSecret` via het formulier, het manifest of de vault van de Hub (contract §3.1 en §9, aanvulling C-12; `appstore-en-fork:docs/adr/ADR-0016-beheerder-en-dienstaccount-zonder-geheim-in-het-formulier.md` besluit 6). Omdat de sleutel naast de versleutelde credentials staat, beschermen de eigenaar (568) en de toegang tot de dataset en haar kopieën (snapshots, back-ups) de credentials, niet de versleuteling: een kopie van `/data` geldt als geheim (ADR-0016 eis 9; `02_BOUWPLANNEN/B12_BACKUP_HERSTEL.md`, B12-003).

**Preflight-regels (niet overslaan):** TrueNAS-release en Docker-appconfig controleren; data-eigenaar bepalen; bestaande install herkennen; bezette ports en container netwerken vergelijken; herstelbare backup + exacte image pin eisen; secrets nooit in logs of screenshots; test op stille omgeving vóór productie.

## 2. Stappen in uitvoeringsvolgorde

### Stap 1. Container en beveiliging
**Uitvoeren:** Installeer Node-RED als standaard Custom App volgens het manifest `jelly-leon-platform:install/manifests/node-red.manifest.yaml`: non-root met /data, `adminAuth` zonder gebruikers (zonder beheerder is de editor helemaal dicht, ook voor lezen; besluit C-11), geen privileged, geen Docker-socket. Geen `credentialSecret`, wachtwoord, wachtwoordhash of gebruiker in het formulier of het manifest (contract §9, `account_gegevens_verboden`). Een beheerder en een dienstaccount komen er voorlopig niet: besluit van de gebruiker 2026-11-11 bij ADR-0016 besluit 7 ("Wachten"); deze stap blijft daarom Geblokkeerd tot de gebruiker een weg kiest.
**Verifiëren:** De controles na installatie uit het manifest (`beveiliging_actief`, `anoniem_geweigerd`) en de monitor tonen een beveiligde Node-RED: anoniem geeft de editor en de Admin-API 401. Een editor die zonder aanmelding opengaat, is een fout: Node-RED direct stoppen.
**Bewijs:** noteer NAS-versie, appimage digest, datum, gemaskeerde output, eventuele screenshot en status in Excel (ID `I10-10-01`).
**Als dit mislukt:** stop hier; maak oorzaak en rollbackpad inzichtelijk. Geen volgende stap starten zolang deze test of de back-upgate rood is.

### Stap 2. Netwerk beperken
**Uitvoeren:** Maak alleen uitgaande verbindingen naar Hub/event endpoints, geen directe TrueNAS root.
**Verifiëren:** Onbekend tool node mag niet script uitvoeren.
**Bewijs:** noteer NAS-versie, appimage digest, datum, gemaskeerde output, eventuele screenshot en status in Excel (ID `I10-10-02`).
**Als dit mislukt:** stop hier; maak oorzaak en rollbackpad inzichtelijk. Geen volgende stap starten zolang deze test of de back-upgate rood is.

### Stap 3. Flows importeren
**Uitvoeren:** Maak eerste read-only flow MediaGuard offline→incident en my_house sensor stale→melding.
**Verifiëren:** Flowhistorie en event schema zichtbaar.
**Bewijs:** noteer NAS-versie, appimage digest, datum, gemaskeerde output, eventuele screenshot en status in Excel (ID `I10-10-03`).
**Als dit mislukt:** stop hier; maak oorzaak en rollbackpad inzichtelijk. Geen volgende stap starten zolang deze test of de back-upgate rood is.

### Stap 4. Policy-bound actions
**Uitvoeren:** Gebruik Hub action request connector, geen directe app mutations.
**Verifiëren:** Een test flow restart vraagt goedkeuring volgens R-class.
**Bewijs:** noteer NAS-versie, appimage digest, datum, gemaskeerde output, eventuele screenshot en status in Excel (ID `I10-10-04`).
**Als dit mislukt:** stop hier; maak oorzaak en rollbackpad inzichtelijk. Geen volgende stap starten zolang deze test of de back-upgate rood is.

### Stap 5. Replay/versies
**Uitvoeren:** Testevents, Git export, checksum/backup flows.
**Verifiëren:** Herstel van oude flowversie slaagt.
**Bewijs:** noteer NAS-versie, appimage digest, datum, gemaskeerde output, eventuele screenshot en status in Excel (ID `I10-10-05`).
**Als dit mislukt:** stop hier; maak oorzaak en rollbackpad inzichtelijk. Geen volgende stap starten zolang deze test of de back-upgate rood is.

### Stap 6. Monitoring
**Uitvoeren:** Health en queue lag naar Hub/Uptime Kuma.
**Verifiëren:** Stop Node-RED → zichtbaar incident.
**Bewijs:** noteer NAS-versie, appimage digest, datum, gemaskeerde output, eventuele screenshot en status in Excel (ID `I10-10-06`).
**Als dit mislukt:** stop hier; maak oorzaak en rollbackpad inzichtelijk. Geen volgende stap starten zolang deze test of de back-upgate rood is.

## 3. Acceptatie en oplevering
Echte TrueNAS-app start, authenticatie, persistente data na herstart, firewall/poort, metrics, backup+restore en rolrechten controleren.

- **GO:** elke stap heeft bewijs en geen kritisch defect; health na herstart, functionaliteit in eigen UI en Hub, DB persistent, documenten geactualiseerd.
- **NO-GO:** geen restorepoint, onbekend secret ownership, ongeteste dataset/poort, falende health, incomplete migratie, onveilige WAN-exposure of datawijziging buiten eigenaar.

## 4. Terugdraaien / verwijderen
1. Schakel nieuwe automation/ingest uit. 2. Bewaar audit en logs. 3. Stop nieuwe container/route, herstel oude version-pinned image én passend databestand/snapshot waar schema is veranderd. 4. Controleer credentials, clients en content integrity. 5. Maak incidentrapport met wat wel/niet is teruggezet. 6. Bij decommission: data alleen na eigen, afzonderlijke bevestiging verwijderen.

## 5. Let op
Veiligheid: sandbox testflows, exec node disallow en geen onbeheerde contrib packages.

## 6. Upstream documentatie en broncontrole
https://nodered.org/docs/getting-started/docker

Re-run broncheck vlak vóór uitvoering: deze installatiebeschrijving is een plan en geen claim dat er reeds een live installatie is gevalideerd.