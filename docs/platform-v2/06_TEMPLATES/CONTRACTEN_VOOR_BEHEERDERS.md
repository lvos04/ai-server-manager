# Bouwverantwoordelijkheden en deliverables per rol

- **Architect:** event-ownership, diagrammen, API-schema's, threat model, migratie-/rollback-Gates, privacy en resourcebeleid.
- **Backendbouwer:** typed schema, connector retries/dedupe, auth, scoped executor, audit, service health, DB migrations, tests tegen echte API waar mogelijk.
- **Frontendbouwer:** telefoon/tablet/desktop, loading/error/unknown, toegankelijkheid, incident drilldowns, approvals en geschoonde provenance.
- **Infra/TrueNAS-bouwer:** datasets, ACL, port inventory, pinned images, container least privilege, DNS/TLS, volume persistency, restore tests en stapsgewijze rollout.
- **Media-bouwer:** Jellyfin upstream compat, playback clients, hardware transcoding, anime/subtitles, media owner boundary, TV/canary tests.
- **QA/security reviewer:** malicious prompt/flow, R0/R1/R2/R3 policy, secret leak, auth and SSO, Prowlarr loops, boiler physical command denial, ZFS safety and external backup recoverability.

### Milestone definition
Geen milestone op '100% gebouwd' zonder: testmatrix geslaagd, CI release immutability, NAS real hardware test waar mogelijk, rollback evidence en nul onverklaarde kritieke bugs. Ontbrekende apparaten of API tokens moeten als expliciete blokkade in Excel staan.
