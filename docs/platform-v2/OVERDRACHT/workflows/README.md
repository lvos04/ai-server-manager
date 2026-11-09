# Workflow-scripts (orkestratie van de bouw)

- `p0.js` — P0 per groep: `delta` (MediaGuard/MSO/my_house + tweede controle), `hub` (backend → PWA → review),
  `svc` (appstore, home-control-hub, zoeken; elk + review), `plat` (jelly-leon-platform, jelly-leon, -web, -clients; elk + review).
- `p1.js` — P1 per groep: `hub` (catalogus+monitoring → incidenten+SSO → PWA → review), `svc` (home-control-hub B13-002…005,
  appstore B08-002 + APP-01…20), `plat` (manifests I07/I08/I09/I13/I23, simulators, installatie-rooktest).

Gebruik (Workflow-tool): `Workflow({scriptPath: ".../p1.js", args: {"groups": ["hub"]}})`, één workflow per groep zodat
ze parallel lopen. Het blok `OMGEVING:` in de `COMMON`-tekst is aangepast aan de Ubuntu-machine (geen proxy/CA, 22 CPU's / 14,5 GiB,
werkmap `/home/transcode/truenas-v2`). Filter op één repo met `args.keys` (bv. `{"keys":["hch"]}`). P0 is grotendeels uitgevoerd; draai alleen wat nog ontbreekt
(zie `../STATUS.md` en de git-historie per repo), bijvoorbeeld de ontbrekende reviews.
