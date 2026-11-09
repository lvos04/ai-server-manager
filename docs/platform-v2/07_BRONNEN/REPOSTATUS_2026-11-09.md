# Repo- en versiecontrole — 9 november 2026

Deze waarnemingen kwamen uit de eigen GitHub-repositories via de GitHub-connector. **Code/README/CI zijn géén bewijs dat jouw TrueNAS de release daadwerkelijk draait.**

## MediaGuard Ultimate
- Repository: https://github.com/lvos04/media-guard-ultimate (privé; gebruiker met toegang nodig).
- GitHub release **v1.2.2**, gepubliceerd 2026-11-09 03:42 UTC; commit `de710c7f26` beschrijft de 40 verbeteringen. Daarna commits `a420ee8db6` en `30f7415a99` voor CI/E2E herhalingen en traces.
- `README.md` noemt image `ghcr.io/lvos04/mediaguard-core:1.2.2-aio`, poort 30080, drie data mounts `/config`, `/work`, `/data`.
- Changelog 1.2.2: zelfstandige achtergrondcontrole en push, wachtrijen per CPU/GPU-lane, betere Seerr-levenscyclus, AV1/VMAF fail-closed, robuustere backup, betere mobiele app, strengere auth.
- Onderzoekstatus: repository en release bekeken, geen directe remote toegang tot productie TrueNAS. Niet opnieuw implementeren zonder vergelijking.

## Media Source Optimizer
- Repository: https://github.com/lvos04/media-source-optimizer (privé).
- HEAD commit `422b5106` 2026-11-09 04:40 UTC; batch `1.6.0` met diagnose server/provider, categorie `*`, wijzigingen in audit, doelenkaart, footprint, categorie-outcomes, backup vóór upgrade, redactie en driftgedrag.
- `release/VERSION` was **1.5.0** op het moment van lezen; README en changelog beschrijven 1.5.0 als releasebasis. De 1.6.0 commits bewijzen nieuwe code, maar nog geen gevalideerde geactiveerde productie-release.
- `INTEGRATION_MEDIAGUARD.md`: 1.6.0 extra MediaGuard **leesroutes**; geen extra schrijfroutes, eigen eigenaar-API blijft leidend. Categorie `*` corrigeren in SABnzbd vraagt toestemming, geen MediaGuard fork-config aanpassen.
- `TEST_RESULTS.md`: eerdere testresultaten in mock/Docker-omgeving, live echte accounts/hardware hebben aparte acceptatiechecklist. Plan vereist nieuwe tests met v1.2.2.

## my_house
- Repository: https://github.com/lvos04/my_house (privé).
- Release **v0.1.0** gepubliceerd 2026-11-08 18:10 UTC; commit `4ed22bca9b` bevat release-workflow.
- Corestack FastAPI+worker+PostgreSQL+MQTT en web/Android; Hue/Gree/HomeWizard/Zigbee adapters; energy (P1, socket boiler alleen meten, airco totaal meter); tijdzones, klimaatregels, backup en verhuisfunctie.
- `docs/testlog.md`: Unit/integratie op mocks/fixtures, hardware/lokale Gree en TrueNAS installatie moeten nog op echte apparaten worden getest.
- Documentatie voor installatie noemt TrueNAS 25.10. Werkelijke NAS-versie is **onbekend**.

## Belangrijke externe officiële referenties
- TrueNAS JSON-RPC API: https://www.truenas.com/docs/scale/25.10/api/ — versiegebonden WebSocket API, oud REST niet gebruiken.
- Claude Max API-credits: https://platform.claude.com/docs/en/about-claude/api-credits-for-subscribers — claimen via Claude Console, gescheiden van abonnementlimieten en Claude Code; saldo/claim en overage checken.
- Jellyfin server en licentie: https://github.com/jellyfin/jellyfin en https://jellyfin.org/docs/
- Beszel https://beszel.dev/guide/installation ; Uptime Kuma https://github.com/louislam/uptime-kuma ; Authentik https://docs.goauthentik.io/install-config/install/docker-compose/
- Node-RED https://nodered.org/docs/getting-started/docker ; NetAlertX https://github.com/netalertx/NetAlertX ; AdGuard Home https://github.com/AdguardTeam/AdGuardHome ; Gotify https://gotify.net/docs/install ; pgvector https://github.com/pgvector/pgvector .

**Installatiebeleid:** vóór uitvoering alle releaseversies en de huidige official docs opnieuw controleren; geen garantie dat voorbeeld UI-velden of containeropties hetzelfde blijven.
