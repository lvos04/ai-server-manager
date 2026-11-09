# ADR-0017 — Hub-koppeling volgens JL4 en geen titels naar de Hub (B03)

Status: aangenomen · 2026-11-09 · overgenomen uit ADR-B03-06 van het goedgekeurde B03 2.0-plan (`docs/platform-v2/02_BOUWPLANNEN/B03_UNIVERSELE_MEDIASERVER.md` §10.4) · Hub-kant (Δ-HUB-JL, Δ-HUB-2) in deze repo; plugin-kant in jelly-leon (B03-017).
Contractwijzigingen die hieruit volgen (Δ-…, hoofdstuk 18 van het bouwplan) zijn nog niet in `PLATFORM_CONTRACTEN.md`
doorgevoerd; dat gebeurt als eigen stap met review.
Herkomst: Jurypunten J-BESCH A1/A2/A14, J-COMPAT (Hub-auth).

- **Werkpakketten:** B03-017; Hub-kaarten B03-029, 039, 049, 058, 069, 078; test JLT-68.

## Context

- Contract 1.2 §2.3 regel 2: geen enrollment voor Jellyfin/Jelly Leon in v1. JL4 (`CONTRACT_1.2_CONFORMITEIT.md:256`): de
  B03-plugin verifieert Hub-JWT's pas als er een pinmechanisme is (pluginconfiguratie in het Jellyfin-dashboard,
  vingerafdruk §4.5).
- In v1.0 van de plandelen bestonden vier Hub-modellen (401, 501, gescopete sleutel, "en/of").
- Een Hub-gebruiker is niet gekoppeld aan een Jellyfin-gebruiker, dus de bibliotheekrechten van Jellyfin gelden niet in de
  Hub. Een item-ID geeft samen met de anonieme streamroutes (ADR-0009) toegang tot de inhoud.
- De Hub-inbox eist een service-token (`routers/events.py:37-43`), dat Jelly Leon in v1 niet heeft.

## Besluit

1. **Eén model:** Hub-JWT's worden alleen geaccepteerd na een in het Jellyfin-dashboard gepinde sleutelset (vingerafdruk
   vergeleken met de Hub-UI); persistente `jti`-cache (§4.6); rol `kind` wint altijd (403); zonder pin
   `401 {code:"unauthorized", details:{reason:"not_linked"}}`. Geen gescopete sleutel, geen ander model.
2. De Hub **pollt** de ene outbox (`GET /connector/v1/events`); geen push.
3. **Wat de Hub krijgt:** alleen aantallen en ondoorzichtige ID's (connector-items en events). Nooit titels,
   bestandsnamen, paden, logregels, beelden, item-ID's, gebruikers- of apparaatnamen of IP-adressen. `entity` in events is
   een ondoorzichtig ID (bijv. `quality_finding`), nooit een item-ID.
4. `propose`/`apply`/`rollback` geven in v1 `501 capability_unavailable`; Hub-kaarten tonen `onbekend` (grijs) zonder pin.
5. Hub-kaarten worden gebouwd in ai-server-manager (Δ-HUB-2) met een ontwerpstap en een ontwerpreview (contract §13); de
   Hub-adapter en de stap "sleutelset kopiëren" zijn Δ-HUB-JL.

## Alternatieven

- *Gescopete API-sleutel van Jellyfin:* Jellyfin kent geen gescopete sleutels; een admin-sleutel is te ruim. Verworpen.
- *Titels naar de Hub met een eigen ACL-laag:* vraagt een koppeling Hub-gebruiker ↔ Jellyfin-gebruiker (eigen ADR); niet in
  v1.

## Gevolgen

- De Hub toont gezondheid en aantallen, en verwijst voor details met een deeplink naar Jelly Leon (waar de Jellyfin-rechten
  gelden).

## Verificatie

JLT-68 (401 not_linked, 403 kind, 401 token_replayed; schemacontrole events/items zonder titels, namen, paden, IP's).
