# ADR-0004 — Eenmalige setupcode in de app-log

Status: aangenomen · 2026-11-09 · fase P0

## Besluit
- `hub init` (bij elke containerstart) maakt zolang er geen beheerder is een nieuwe code van 12 tekens
  (Crockford-base32, ~60 bit) en schrijft die alleen naar de log (TrueNAS → Apps → Logs). Op schijf staat alleen een
  gezouten SHA-256 met vervaltijd (24 uur). De vorige code vervalt, zodat de laatste code in de log altijd geldig is.
- Andere processen (bv. de API in ontwikkeling) maken alleen een code als er nog geen geldige is.
- Na het aanmaken van de eerste admin verdwijnt de hash en verschijnt er geen code meer.
- Pogingen zijn per IP begrensd (5 per 15 minuten) en worden geaudit.

## Gevolgen
Wie toegang heeft tot de app-logs in TrueNAS kan de eerste beheerder aanmaken; dat is bewust (de NAS-beheerder).
