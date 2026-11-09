# Workflow-scripts (orkestratie van de bouw)

- `p0.js` — P0 per groep: `delta` (MediaGuard/MSO/my_house + tweede controle), `hub` (backend → PWA → review),
  `svc` (appstore, home-control-hub, zoeken; elk + review), `plat` (jelly-leon-platform, jelly-leon, -web, -clients; elk + review).
- `p1.js` — P1 per groep: `hub` (catalogus+monitoring → incidenten+SSO → PWA → review), `svc` (home-control-hub B13-002…005,
  appstore B08-002 + APP-01…20), `plat` (manifests I07/I08/I09/I13/I23, simulators, installatie-rooktest).

Gebruik (Workflow-tool): `Workflow({scriptPath: ".../p1.js", args: {"groups": ["hub"]}})`, één workflow per groep zodat
ze parallel lopen. **Pas eerst het blok `OMGEVING:` in de `COMMON`-tekst aan** (geen proxy/CA meer, echte CPU-telling) en
vervang `/home/user` door de werkmap met de 11 repos. P0 is grotendeels uitgevoerd; draai alleen wat nog ontbreekt
(zie `../STATUS.md` en de git-historie per repo), bijvoorbeeld de ontbrekende reviews.
