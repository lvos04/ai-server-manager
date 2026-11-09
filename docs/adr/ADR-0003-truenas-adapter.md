# ADR-0003 — TrueNAS-adapter: alleen-lezen, wss, TLS-vertrouwen per vingerafdruk, capability-map

Status: aangenomen · 2026-11-09 · fase P0 (B01-001)

## Besluit
- **Transport:** uitsluitend `wss://<D03-adres>[:poort]/api/current` (JSON-RPC 2.0). Onversleuteld `ws://` wordt
  geweigerd: de key zou leesbaar over het LAN gaan en TrueNAS trekt keys die zo gebruikt worden zelf in. Geen proxy.
- **TLS:** standaard verifiëren (systeem-CA's, optioneel `HUB_TRUENAS_EXTRA_CA_FILE`). Bij een zelfondertekend
  certificaat geeft de test `tls_untrusted` met de SHA-256-vingerafdruk. Een beheerder bevestigt die expliciet
  (`POST /api/v1/truenas/tls/trust`); de Hub vergelijkt de bevestiging met wat de NAS op dat moment aanbiedt. Het
  vertrouwen geldt alleen voor exact die URL. Bij elke verbinding wordt de vingerafdruk na de TLS-handdruk en **vóór**
  het versturen van de key vergeleken; afwijking → `tls_untrusted`.
- **Alleen lezen:** de client kan alleen methoden uit `READ_ONLY_METHODS` aanroepen (anders `PermissionError`);
  `app.query` wordt nooit met `retrieve_config` aangeroepen (de configuratie kan geheimen bevatten); normalisatie werkt
  met een whitelist, zodat bv. cloud-sync-credentials nooit in de database komen.
- **Rechten van de key:** via `auth.me`. Heeft de key schrijfrechten (bv. `FULL_ADMIN`), dan weigert de Hub
  (`key_too_privileged`) en leest verder niets; de schrijfkey hoort alleen bij de executor.
- **Capability-map:** per versie uit `core.get_methods` (eerste kandidaat die de NAS aanbiedt, bv.
  `pool.snapshot.query` ≥ 25.04 en `zfs.snapshot.query` daarvoor); lukt ontdekking niet, dan een versietabel
  (`capability_source = versietabel`).
- **Fouten:** elke fout → `unknown` met `reason_code`: `auth_failed`, `permission_denied`, `method_unavailable`,
  `unreachable`, `timeout`, `tls_untrusted`, plus `key_too_privileged`, `not_configured` (geen D03/key),
  `protocol_error` (onverwacht antwoord) en `stale` (meting ouder dan de TTL). Een onderdeel zonder leesrecht blijft
  `unknown`, de rest wordt wel gelezen (`partial`). Tijdlimieten 5 s connect / 15 s read (contract §5).

## Gevolgen
Getest tegen een in-repo fake (`tests/fakes/fake_truenas.py`) met versieprofielen 24.10/25.04, eigen test-CA,
notificaties tussendoor, geweigerde methoden en offline-gedrag. **NIET GEVALIDEERD (echte NAS):** methodenamen en
antwoordvormen moeten bij de eerste echte koppeling tegen de officiële API-documentatie van de gemeten versie worden
gecontroleerd.
