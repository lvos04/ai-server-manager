# Operator-runbooks (B09-006)

Gegenereerd uit `apps/api/src/hub/runbooks/catalogus.py` (`python -m hub export-runbooks`); niet met de hand
bewerken. `runbook_hash`: `2025b189ee3df08b83296c4fe953353b9f0ad00e1fcff6652e34d3aafa797f89`.

Elke stap is getypeerd: **Hub toont** (alleen lezen), **Zelf doen** (in een bestaande UI, nooit een
terminal) of **Voorstel** (een actie uit de executor-allowlist van contract §8 met minimale risicoklasse; de
Hub voert niets zelf uit — uitvoering via policy-engine, goedkeuring en executor volgt in P2). Veilige modus:
faalt een incident telkens opnieuw, dan stelt de Hub geen herstart meer voor.

## Dienst offline of crasht (`service_offline`)

Een app of dienst is onbereikbaar, crasht of doet geen werk meer (ook: monitoringbron weg).

**Observeren**

- Hub toont: Bekijk de gezondheid per onderdeel (TrueNAS-staat, buitenkant, binnenkant) en sinds wanneer. — `/api/v1/apps/{app_id}`
- Hub toont: Bekijk de onderliggende gebeurtenissen en de readback van het incident. — `/api/v1/incidents/{incident_id}`
- Hub toont: Bekijk geschoonde logregels rond het incident (zelfde trace_id of tijdvenster). — `/api/v1/logs?incident_id={incident_id}`

**Isoleren**

- Hub toont: Kijk of meer apps tegelijk wegvallen (hypothese 'nas:onbereikbaar' of 'pool:ongezond'). — `/api/v1/incidents/samenvatting`
- Zelf doen: Open TrueNAS → Apps → de app → Logs en zoek de laatste fout vóór het stoppen. — `TrueNAS-web-UI`

**Mitigeren**

- Voorstel: Herstart de app één keer (alleen buiten de veilige modus). — `app.restart` (minimaal R1)
- Zelf doen: Is de app bewust gestopt? Erken het incident en demp de regel 'App onbereikbaar' voor deze app.

**Terugdraaien**

- Voorstel: Komt het falen na een update: zet de vorige waarden terug (terugzetrecept). — `app.rollback` (minimaal R2)

**Bewijs verzamelen**

- Hub toont: Supportbundel (geschoond) vastleggen bij het incident. — `/api/v1/incidents/{incident_id}/supportbundel`
- Hub toont: Noteer TrueNAS-staat, image-digest en tijdstippen in een notitie bij het incident.

**Oorzaak vastleggen**

- Zelf doen: Leg de oorzaak vast in een notitie (bv. geheugen, configuratie, afhankelijkheid, update).

**Test na herstel** (niet alleen 'poort open')

- Binnenkant gezond: connector-health of heartbeat vers en werk verwerkt (niet alleen 'poort open').
- Alert 'App onbereikbaar' hersteld na de herstelduur (hysterese), geen nieuwe crash binnen het heropenvenster.

Veilige modus na 2× opnieuw falen binnen 60 min.

## Databasemigratie mislukt (`db_migratie_mislukt`)

Een app start niet of meldt een mislukte schemamigratie na een update.

**Observeren**

- Hub toont: Bekijk het incident en de logregels van de app rond de update. — `/api/v1/logs?incident_id={incident_id}`
- Hub toont: Bekijk de image-historie (tag en digest) in de catalogus. — `/api/v1/apps/{app_id}`

**Isoleren**

- Zelf doen: Controleer in de app-log welke migratie faalde; verander niets aan de database met de hand.
- Hub toont: Controleer of er een verse, geverifieerde database-export van vóór de update is. — `/api/v1/backups/coverage`

**Mitigeren**

- Voorstel: Stop de app om verdere schade te voorkomen. Bij een Custom App vraagt dit een goedkeuring van een beheerder (R2), en daarna weigert het platform app.rollback en app.start op die app (doel_niet_herkenbaar): terugzetten en starten gaan dan alleen in de TrueNAS-web-UI. — `app.stop` (minimaal R1; Custom App: R2)

**Terugdraaien**

- Voorstel: Maak eerst een snapshot van de data-dataset. — `zfs.snapshot.create` (minimaal R1)
- Voorstel: Alleen bij een catalogusapp: een versie-terugzet, en alleen als de migratie niets schreef; anders is herstel van de database nodig (R3, via de eigenaar). — `app.rollback` (minimaal R2; een gestopte Custom App weigert het platform)
- Zelf doen: Een gestopte Custom App zet je zelf terug in de TrueNAS-web-UI: het platform ziet bij een gestopte Custom App niet wat erin draait en weigert app.rollback (doel_niet_herkenbaar). — `TrueNAS-web-UI`

**Bewijs verzamelen**

- Hub toont: Supportbundel en de exacte foutregel van de migratie vastleggen. — `/api/v1/incidents/{incident_id}/supportbundel`

**Oorzaak vastleggen**

- Zelf doen: Leg vast welke migratie faalde en waarom (versie, schema, data).

**Test na herstel** (niet alleen 'poort open')

- App start, migratiestand gelijk aan de verwachte versie, connector-health gezond.
- Een testrestore van de export in een sandbox lukt (B12) voordat opnieuw wordt geüpdatet.

Veilige modus na 2× opnieuw falen binnen 60 min.

## Quota of schijf vol (opslag) (`schijf_vol`)

Een pool of dataset raakt vol, een quota is bereikt, of een pool is niet gezond.

**Observeren**

- Hub toont: Bekijk poolgebruik en -gezondheid met bron en laatst bijgewerkt. — `/api/v1/observability/nas`
- Hub toont: Bekijk de trend van pool.gebruik. — `/api/v1/metrics/query?metriek=pool.gebruik`

**Isoleren**

- Zelf doen: Zoek in TrueNAS → Storage welke dataset groeit (snapshots, downloads, transcodes).
- Hub toont: Controleer de gate 'data_mutatie': bij een ongezonde pool zijn opslagmutaties geblokkeerd. — `/api/v1/gates/data_mutatie`

**Mitigeren**

- Zelf doen: Ruim op via de eigenaar van de data (MediaGuard/MSO); de Hub verwijdert nooit zelf media of datasets.
- Voorstel: Pauzeer een niet-kritieke, schrijvende app. Bij een Custom App vraagt dit een goedkeuring van een beheerder (R2) en start de app daarna alleen weer in de TrueNAS-web-UI. — `app.stop` (minimaal R1; Custom App: R2)

**Terugdraaien**

- Voorstel: Start een gepauzeerde catalogusapp weer met app.start als er genoeg ruimte is. — `app.start` (minimaal R1; een gestopte Custom App weigert het platform)
- Zelf doen: Een gepauzeerde Custom App start je zelf in de TrueNAS-web-UI: het platform ziet bij een gestopte Custom App niet wat erin draait en weigert app.start (doel_niet_herkenbaar). — `TrueNAS-web-UI`

**Bewijs verzamelen**

- Hub toont: Leg pool.gebruik vóór en na vast (grafiek of waarden). — `/api/v1/metrics/query`

**Oorzaak vastleggen**

- Zelf doen: Leg vast wat de ruimte opat en welke grens of retentie moet veranderen.

**Test na herstel** (niet alleen 'poort open')

- pool.gebruik onder de herstelgrens gedurende de herstelduur; pool gezond (TrueNAS-meting, niet verouderd).

Veilige modus na 2× opnieuw falen binnen 60 min.

## Slechte deployment of update (`slechte_deployment`)

Na een installatie of update werkt een app slechter, crasht, of wijkt de digest af.

**Observeren**

- Hub toont: Bekijk image, tag en digest-historie (readback na de update). — `/api/v1/apps/{app_id}`
- Hub toont: Bekijk het incident en de logregels sinds de update. — `/api/v1/logs?incident_id={incident_id}`

**Isoleren**

- Zelf doen: Vergelijk de release-notes van de nieuwe versie met het gedrag; verander niets met de hand.

**Mitigeren**

- Voorstel: Zet de vorige waarden terug (terugzetrecept met tag + digest). — `app.rollback` (minimaal R2)

**Terugdraaien**

- Voorstel: Bij een schemawijziging: eerst snapshot, daarna herstel via de eigenaar (R3). — `zfs.snapshot.create` (minimaal R1)

**Bewijs verzamelen**

- Hub toont: Supportbundel en de digest vóór en na vastleggen. — `/api/v1/incidents/{incident_id}/supportbundel`

**Oorzaak vastleggen**

- Zelf doen: Leg vast welke wijziging de fout veroorzaakte en blokkeer die versie in het manifest.

**Test na herstel** (niet alleen 'poort open')

- Digest-readback gelijk aan het terugzetrecept; binnenkant gezond; geen nieuwe fout binnen het heropenvenster.

Veilige modus na 2× opnieuw falen binnen 60 min.

## Toegang kwijt: Tailscale/Cloudflare-lockout (ook SSO) (`toegang_kwijt`)

Toegang van buiten (Tailscale, Cloudflare Tunnel) of via SSO werkt niet meer.

**Observeren**

- Hub toont: Bekijk de gezondheid van Tailscale/cloudflared en Authentik in de catalogus. — `/api/v1/apps`
- Hub toont: Bekijk of de noodlogin werkt (zelftest, zonder in te loggen). — `/api/v1/auth/break-glass/selftest`

**Isoleren**

- Zelf doen: Test vanaf het thuisnetwerk én vanaf een onafhankelijke verbinding (telefoon zonder wifi).
- Zelf doen: Controleer in de app zelf (Tailscale-beheer, Cloudflare-dashboard) of de sleutel/het token verlopen is.

**Mitigeren**

- Zelf doen: Gebruik op het thuisnetwerk de noodlogin van de Hub (wachtwoord + TOTP); nooit via internet.
- Voorstel: Herstart de tunnel-app één keer. — `app.restart` (minimaal R2)

**Terugdraaien**

- Voorstel: Zet de vorige waarden van de tunnel-app terug. — `app.rollback` (minimaal R2)

**Bewijs verzamelen**

- Hub toont: Leg tijdstippen en de testresultaten van beide verbindingen vast als notitie. — `/api/v1/incidents/{incident_id}`

**Oorzaak vastleggen**

- Zelf doen: Leg vast wat de toegang brak (verlopen sleutel, update, DNS) en roteer het noodaccount daarna.

**Test na herstel** (niet alleen 'poort open')

- Toegang werkt vanaf een onafhankelijke verbinding én van binnen; noodaccount geroteerd en bevestigd.

Veilige modus na 1× opnieuw falen binnen 60 min.

## Jellyfin/Jelly Leon-clientprobleem (`jellyfin_client`)

Een client speelt niet af, logt niet in of is incompatibel na een update.

**Observeren**

- Hub toont: Bekijk de gezondheid van Jelly Leon (openbare routes) en het incident. — `/api/v1/apps`
- Zelf doen: Noteer client, versie, apparaat en het afspeelpad (direct play of transcode).

**Isoleren**

- Zelf doen: Test dezelfde titel met een andere client en met de stock-webclient.

**Mitigeren**

- Zelf doen: Gebruik tijdelijk een andere client of de webclient; wijzig niets aan de database.

**Terugdraaien**

- Voorstel: Komt het door een serverupdate: zet de vorige waarden terug. — `app.rollback` (minimaal R2)

**Bewijs verzamelen**

- Hub toont: Supportbundel en de clientmatrix-regel vastleggen. — `/api/v1/incidents/{incident_id}/supportbundel`

**Oorzaak vastleggen**

- Zelf doen: Leg vast welke client/versie faalt en meld het bij de clientmatrix (B03).

**Test na herstel** (niet alleen 'poort open')

- De titel speelt af op de getroffen client; de clientmatrix-test voor die client slaagt.

Veilige modus na 2× opnieuw falen binnen 60 min.

## Gree-airco onbekend of offline (`gree_onbekend`)

my_house meldt een Gree-apparaat als onbekend, offline of met verouderde status.

**Observeren**

- Hub toont: Bekijk de status van my_house in de catalogus (alleen lezen). — `/api/v1/apps`
- Zelf doen: Open my_house en bekijk de laatste bijgewerkte status van het apparaat.

**Isoleren**

- Zelf doen: Controleer of het apparaat stroom en wifi heeft en of de afstandsbediening het heeft uitgezet.

**Mitigeren**

- Zelf doen: Laat my_house het apparaat niet aansturen zolang de status onbekend is (veilige terugval); de Hub stuurt nooit zelf aan.

**Terugdraaien**

- Zelf doen: Hervat schema's in my_house pas na een verse, bevestigde status.

**Bewijs verzamelen**

- Hub toont: Leg tijdstippen van de laatste verse status vast als notitie. — `/api/v1/incidents/{incident_id}`

**Oorzaak vastleggen**

- Zelf doen: Leg vast waarom het apparaat onbereikbaar was (netwerk, firmware, stroom).

**Test na herstel** (niet alleen 'poort open')

- my_house toont een verse status en een testcommando in my_house wordt bevestigd.

Veilige modus na 2× opnieuw falen binnen 60 min.

## MSO: providers of indexers vallen uit (`mso_provider_uitval`)

Media Source Optimizer meldt dat Usenet-providers of indexers niet werken.

**Observeren**

- Hub toont: Bekijk de MSO-status in de catalogus en het incident. — `/api/v1/apps`
- Zelf doen: Open MSO en bekijk providerhealth en foutcodes.

**Isoleren**

- Zelf doen: Controleer in MSO of één provider of alle providers falen (account, quota, netwerk).

**Mitigeren**

- Zelf doen: Laat MSO zelf uitwijken naar andere providers; keur alleen MSO-change-sets goed, nooit iets verwijderen vanuit de Hub.

**Terugdraaien**

- Zelf doen: Draai een eerder goedgekeurde MSO-change-set terug in MSO als die de oorzaak was.

**Bewijs verzamelen**

- Hub toont: Leg de MSO-foutcodes en tijdstippen vast als notitie. — `/api/v1/incidents/{incident_id}`

**Oorzaak vastleggen**

- Zelf doen: Leg vast welke provider faalde en waarom (account verlopen, storing bij de provider).

**Test na herstel** (niet alleen 'poort open')

- MSO meldt de provider weer gezond en een testzoekopdracht in MSO slaagt.

Veilige modus na 2× opnieuw falen binnen 60 min.
