# Workflow-scripts (orkestratie van de bouw)

- `p0.js` — P0 per groep: `delta` (MediaGuard/MSO/my_house + tweede controle), `hub` (backend → PWA → review),
  `svc` (appstore, home-control-hub, zoeken; elk + review), `plat` (jelly-leon-platform, jelly-leon, -web, -clients; elk + review).
- `p1.js` — P1 per groep: `hub` (catalogus+monitoring → incidenten+SSO → PWA → review), `svc` (home-control-hub B13-002…005,
  appstore B08-002 + APP-01…20), `plat` (manifests I07/I08/I09/I13/I23, simulators, installatie-rooktest).

Gebruik (Workflow-tool): `Workflow({scriptPath: ".../p1.js", args: {"groups": ["hub"]}})`, één workflow per groep zodat
ze parallel lopen. Het blok `OMGEVING:` in de `COMMON`-tekst is aangepast aan de Ubuntu-machine (geen proxy/CA, echte CPU-/RAM-telling,
werkmap `<WERKMAP>`). Filter op één repo met `args.keys` (bv. `{"keys":["hch"]}`). P0 is grotendeels uitgevoerd; draai alleen wat nog ontbreekt
(zie `../STATUS.md` en de git-historie per repo), bijvoorbeeld de ontbrekende reviews.


**Let op:** in deze repo staat `<WERKMAP>` in plaats van het echte pad van de ontwikkelmachine (publieke repo). Vervang
`<WERKMAP>` vóór gebruik door de werkmap met de 11 repos (bv. `$HOME/truenas-v2`, als absoluut pad).

**Contract 1.3 (C1.3-ASM-23):** de `COMMON`-tekst noemt nu contract 1.3 en `CONTRACT_1.3_CONFORMITEIT.md` als bindende
leesstof. De KWALITEIT-eisen voor nieuwe Python-diensten (OpenAPI, alles-in-één image, `CUSTOM_APP.md`, manifest)
gelden niet meer voor jelly-leon-web en jelly-leon-clients: die krijgen `KWALITEIT_FORK` (bouwen en testen met de
upstream-toolchain, geen eigen image of Custom App; contract 1.3 §10, inventaris B03). `commonFor(repo)` kiest de tekst.
