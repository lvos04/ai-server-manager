# ADR-0008 — Betekenis van back-updekking en de eigen database-export

Status: aangenomen · 2026-11-09 · fase P0 (B12-001/002/003)

## Besluit
- Dekking per app en dataset: lokale snapshot-taken (recursief/uitsluitingen) en leeftijd van de laatste snapshot;
  extern via cloud-sync (alleen PUSH, OneDrive-detectie op provider) en replicatie; app-consistente DB-export; laatste
  hersteltest; RPO/RTO uit D16.
- **Synchronisatie is geen herstelgarantie:** `herstelgarantie` is alleen `true` met een vastgelegde geslaagde
  hersteltest. **Een snapshot zonder app-consistente database-export telt niet als volledige app-back-up.**
- App-consistente export van andere apps loopt via hun connector-capability; zonder connector `unknown`
  (`capability_unavailable`), met ingeschreven dienst maar nog niet bevraagd `connector_not_queried` (P3).
- Snapshotbeleid is in P0 alleen een **voorstel** (schema uit RPO, ruimtewaarschuwing vanaf 80% poolgebruik);
  toepassen gebeurt pas via de executor na goedkeuring (P2).
- Eigen database: `pg_dump -Fc` naar `/appdata/backups`, status `geslaagd` alleen na: exit 0, niet-leeg bestand met
  `PGDMP`-header, `pg_restore --list` leesbaar met de verwachte tabellen (incl. data), SHA-256 na het wegschrijven
  opnieuw gelijk. Daarnaast `.sha256`- en `.json`-bestanden. Dagelijks, vóór migraties en op verzoek; nieuwste 7 blijven.
  Hersteltests registreert de beheerder als bewijs; de Hub herstelt in P0 zelf niets.
