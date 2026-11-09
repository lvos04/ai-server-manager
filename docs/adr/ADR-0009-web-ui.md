# ADR-0009 — Web-UI: Next.js-PWA met eigen webserver en strikte API-doorgang

> **Bijgewerkt 2026-11-09:** het deel "geen CSS-framework, geen iconenbibliotheek" van punt 1 is vervangen door
> [ADR-0015](ADR-0015-ontwerptaal-peil.md) (ontwerptaal Peil op Tailwind 4 + shadcn/ui + lucide, besluit van de gebruiker).


Status: aangenomen · 2026-11-09 · fase P0 (deel 2)

## Context
Alle schermen van het platform staan in één Nederlandstalige Hub-UI (contract §1). In de alles-in-één image moet de
web-UI op de ene poort 30400 luisteren en `/api/*` doorzetten naar de interne API (127.0.0.1). De Hub draait in P0 via
`http://<NAS-adres>:30400` (HTTPS volgt met D17). Navigatie, kaarten en toegankelijkheid volgen
`01_ARCHITECTUUR/08_UI_EN_INTERACTIES.md`; er mag nooit nepdata of "alles groen" bij onbekend getoond worden.

## Besluit
1. **Stack:** Next.js 16.4.5 (App Router, Turbopack-build, `output: "standalone"`), React 19.3.1, TypeScript 5.9.3,
   Node 22.23.4 (`node:22.23.4-bookworm-slim` op `@sha256`-digest). Geen CSS-framework, geen iconenbibliotheek, geen
   externe lettertypen of CDN's: alles werkt op een offline LAN. TypeScript 7 (native port) is bewust niet gekozen:
   Next.js gebruikt voor zijn typecontrole de JavaScript-API van TypeScript 5.x.
2. **Eigen webserver** `server/hub-server.mjs`: Next.js-requesthandler + doorgang voor precies `/api/*`, `/connector/*`,
   `/healthz` en `/readyz` naar `HUB_API_URL` (alleen loopback toegestaan). Niet de ingebouwde rewrites van Next.js,
   omdat (a) die bij de build worden vastgelegd en (b) de externe proxy van Next.js alleen `x-forwarded-host` zet
   (gecontroleerd in `next/dist/server/lib/router-utils/proxy-request.js`): een door de client verzonnen
   `X-Forwarded-For` zou dan via uvicorn (`forwarded_allow_ips=127.0.0.1`) als client-IP gelden en zo de rate-limit
   van inloggen/setup omzeilen. Onze server negeert alle `Forwarded`/`X-Forwarded-*`/`X-Real-IP` van de client en zet
   zelf het socketadres; alleen een expliciet vertrouwde reverse proxy (`HUB_WEB_TRUSTED_PROXIES`, standaard leeg) mag
   de keten en `https` doorgeven. API onbereikbaar → `502 {code:"api_unavailable", message:<NL>}`.
3. **Gegevens alleen client-side** uit de API (pagina's zijn statische schillen). Bij een fout wordt oude data gewist
   in plaats van als actueel te blijven staan; Home vernieuwt elke 60 s. Statussen hebben altijd symbool + tekst;
   `unknown`/verouderd is grijs, nooit groen; de totaalstatus is nooit beter dan het slechtste onderdeel (in P0 is
   app-gezondheid onbekend, dus nooit "in orde").
4. **Wizard uit het schema:** het formulier per besluit wordt opgebouwd uit het JSON-schema van de API (pydantic),
   met Nederlandse labels in de UI, lege beginwaarden, keuzerondjes zonder standaard voor verplichte ja/nee en een
   verplichte bevestiging voor `const: true` (bv. harde stop). Pydantic-meldingen worden per veld naar het
   Nederlands vertaald. Een kopie van de schema's (`tests/unit/fixtures`) wordt door een pytest bewaakt op drift.
5. **PWA:** webmanifest + service worker die alleen de app-schil (HTML-schil, `/_next/static`, iconen,
   `offline.html`) bewaart en **nooit** `/api`, `/connector`, `/healthz`, `/readyz`. Offline: duidelijke banner, gegevens
   onbekend. Browsers staan service workers alleen toe in een *secure context* (HTTPS of localhost); via
   `http://<NAS-adres>` registreert de UI daarom niets en toont Instellingen eerlijk "Offline-schil: niet actief".
   Om dezelfde reden wordt de `Idempotency-Key` met `crypto.getRandomValues` gemaakt als `crypto.randomUUID` ontbreekt.
6. **Navigatie** exact volgens 08_UI. Breekpunt 1024 px: daaronder (360/390/768) de ondernavigatie Home, Apps,
   Problemen, AI, Meer; vanaf 1024 de zijbalk met de negen items. Schermen buiten de zijbalk zijn op desktop bereikbaar
   via Home-kaarten/links (Apps onder Server, onboarding onder Instellingen). Latere fasen tonen
   "Nog niet beschikbaar (volgt in fase Px)" volgens `06_FASERING_EN_GATES`.
7. **Beveiliging:** CSP (`default-src 'self'`, `frame-ancestors 'none'`, geen externe bronnen; `'unsafe-inline'` voor
   scripts is nodig voor de inline-hydratie van Next.js), `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`,
   `Permissions-Policy`. Alleen interne terugsprong na inloggen (geen open redirect). De web-UI draait als 568, de code
   in `/opt/hub-web` is van root en alleen-lezen. `sharp`/libvips (±47 MB) wordt niet meegeleverd
   (`images.unoptimized`).
8. **Tests:** vitest (pure logica + server-render van componenten) en Playwright 1.63.0 (zelfde Chromium-revisie als
   de voorgeïnstalleerde browser; `playwright-core` via `overrides` gelijkgetrokken voor `@axe-core/playwright`) op
   360/390/768/1440 px met axe (WCAG 2.2 A/AA), aanraakdoelen ≥ 44 px en geen horizontaal scrollen, tegen de echte
   API met de fake TrueNAS — en dezelfde suite tegen de alles-in-één image. Schermafbeeldingen als JPEG (kwaliteit 70)
   om de repo klein te houden.

## Gevolgen
- Eén proces extra in de image (Node, ±250 MiB voor de hele Hub in rust gemeten in Docker); de API luistert alleen op
  127.0.0.1:8400. Rooktest: luisterende sockets precies `0.0.0.0:30400` en `127.0.0.1:8400`.
- Achter een latere HTTPS-reverse-proxy (D17) moet het adres van die proxy in `HUB_WEB_TRUSTED_PROXIES` staan, anders
  ziet de Hub die proxy als client.
- Offline-schil en installeren als app werken pas met HTTPS; tot die tijd is de UI gewoon online bruikbaar.
- Niet gevalideerd: echte NAS, Android-telefoon en tv/speler (08_UI vraagt die vóór afmelding).
