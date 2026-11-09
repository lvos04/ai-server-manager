# ADR-0024 — Hub-UI in Peil en de P1-schermen (H5, H6, H12)

Status: aanvaard · Datum: 2026-11-09 · Fase: P1 "Ogen en toegang", webstap
Excel: B01-002, B01-004, B01-005, B01-006, B09-001…B09-006 (UI-kant) · Contract 1.2: H5, H6, H12
Bouwt op: ADR-0009 (web-UI), ADR-0015 (ontwerptaal Peil), ADR-0021…0023 (P1-backend) en
`docs/ontwerp/HUB_PEIL_ONTWERP.md` (ontwerpstap, besluiten OB-01 t/m OB-14).

## Context

De ontwerpstap leverde Peil-prototypes en een migratieplan voor `apps/web`, maar geen gebouwde UI. De besluiten OB-01 t/m
OB-14 stonden in `HUB_PEIL_ONTWERP.md` §8 met de opdracht ze als volgend vrij ADR-nummer over te nemen. Deze ADR legt ze
vast én de keuzes die bij het bouwen nodig waren (afwijkingen van het ontwerp staan er expliciet bij).

## Besluiten

### Overgenomen uit de ontwerpstap (OB-01 t/m OB-14)

| # | Besluit | Gebouwd als |
|---|---|---|
| OB-01 | Merk "TrueNAS Home Platform"; "Hub" blijft de naam van de centrale app | merk links in zijbalk/kop (ook kindschil), titel "<pagina> — TrueNAS Home Platform", PWA `short_name` "Home Platform", nieuwe iconen (`server`-glyph op `--foreground`) |
| OB-02 | Kindschil Home · Kijken · Zoeken · Ik | eigen schil zonder zijbalk/tellers/systeemstatus; andere routes → kindvriendelijke 403 met "Details voor een volwassene"; Kijken/Zoeken "komt later"; de API weigert kind al (getest) |
| OB-03 | Niet-gezondheidstoestanden neutraal | `StatusBadge` tonen `neutral`/`info`/`gate`; Gekoppeld, Ingesteld, Aan, Draait, Geslaagd, Ingetrokken nooit groen |
| OB-04 | Zekerheid als woord | ≥ 0,85 Zeker · ≥ 0,6 Waarschijnlijk · lager Onzeker · leeg "Ik weet het niet"; het getal alleen in "Toon bewijs" |
| OB-05 | Ernst (3 API-niveaus) | kritiek → Kritiek, waarschuwing → Middel, info → Info |
| OB-06 | Totaalstatus | Storing > Beperkt > Deels onbekend > Alles gezond; gate, neutraal, info en nog-niet tellen niet mee |
| OB-07 | TOTP zonder QR | geheim (groepen van 4) + otpauth-URI als KopieerVeld; geen QR-generator |
| OB-08 | Volgorde Apps | `limit=200`, slechtste status eerst in de UI; met `next_cursor` op naam + melding |
| OB-09 | Versheid-label | "Bijgewerkt" (tests volgen) |
| OB-10 | Acties in P1 | zichtbaar, `aria-disabled`, "Volgt in fase P2", **geen** RisicoBadge ("risico bepaalt het beleid") |
| OB-11 | Intrekken van een dienst | getypte app-id in de pagina; knop uit tot de tekst klopt |
| OB-12 | Instellingen | index + 8 subpagina's, ≥ 1024 vaste subnavigatie; oude ankers (`#gebruikers`, `#sessies`, `#audit`, `#over`, `#weergave`) sturen door |
| OB-13 | Iconen | lucide-react 1.66.0 (zelfde paden als de prototypes), vaste koppeling per betekenis |
| OB-14 | Skiplink | "Naar de inhoud" (bestaande test) |

### Keuzes bij het bouwen

1. **Tailwind 4 + shadcn/ui-componenten + lucide (H12).** Exact gepind: `tailwindcss`/`@tailwindcss/postcss` 4.3.5
   (dev), `class-variance-authority` 0.7.1, `clsx` 2.1.1, `tailwind-merge` 3.7.0, `lucide-react` 1.66.0, Radix
   (`react-slot`, `react-dialog`, `react-alert-dialog`, `react-tabs`, `react-dropdown-menu`) en `recharts` 3.10.1.
   De shadcn-componenten (Button, Tabs, AlertDialog, Sheet, DropdownMenu) zijn met de hand in `src/components/ui`
   geschreven volgens shadcn new-york **met de verplichte Peil-codemod al toegepast** (44 px, geen `text-xs`,
   Peil-focusring, `aria-disabled` met gestippelde rand, geen opacity-vlakken, `z-overlay`/`z-nav`). Er is geen
   `npx shadcn add` gedraaid: dat zou de codemod per component opnieuw vragen en `globals.css` overschrijven.
2. **Tokens als versie-gepinde kopie (O-14).** `src/app/peil/ontwerptaal.css` = exacte kopie van
   `design/ontwerptaal/ontwerptaal.css` met herkomstkop (Peil 1.1.0 · sha256); `scripts/peil-kopie.mjs` maakt hem
   opnieuw, `tests/unit/peil-tokens.test.ts` faalt bij drift en bij hex-kleuren of eigen kleurblokken in `globals.css`.
3. **Fase 1–3 in één stap, met één bewuste rest.** De drie eigen kleurblokken, `.btn*`, `.badge`, `.tone-*`,
   `.notice`, `.choice`, `Icon.tsx` en de tekstsymbolen zijn weg. Een kleine set opmaakhulpen (`stack`, `row`, `card`,
   `meta`, `kv`, `field`, …) blijft als Tailwind-recept op Peil-tokens in `globals.css`, zodat de grote P0-schermen
   (onboarding, besluit, TrueNAS, back-ups) niet regel voor regel herschreven hoefden te worden. Nieuwe schermen
   gebruiken utilities en componenten. `TableWrap` (scrollkader) blijft alleen voor 2D-tabellen (datasets, schijven,
   audit); kerninformatie (apps, diensten, gebruikers, incidenten) gebruikt `ResponsiveList` (C-34).
4. **Peil O-03 (vervangt ADR-0009 punt 3).** `useApi` bewaart bij een fout de laatst bekende gegevens en meldt ze als
   `stale` (met `lastOk`); gegevens horen bij één pad (na een padwissel nooit "laatst bekend" van een ander pad).
   StatKaart en inventarissecties tonen ze gedempt in een gearceerd vak "Laatst bekend · 10:12" met status
   Onbekend/Verouderd — nooit als actueel en nooit groen. De Home-samenvatting krijgt verouderde invoer niet als vers.
5. **401 is niet altijd "afgemeld".** Alleen code `unauthorized` (sessie weg) meldt de gebruiker af; een 401 met een
   inhoudelijke code (`invalid_totp` bij het bevestigen van het noodaccount) is een veldfout.
6. **Thema.** Het themascript zet altijd het opgeloste thema (`data-theme` + `.dark`), ook bij Systeem, en volgt
   `matchMedia` live. Keuze Systeem/Licht/Donker als knoppengroep (C-50) onder Instellingen → Account (en Ik voor kind).
7. **Grafieken (O-13).** recharts met een eigen `LineChart`-component in shadcn-stijl: alleen `var(--chart-N)`, lijn
   2 px, `connectNulls` uit, gaten als expliciete `null` (tabel: "Geen meting"), verouderd = arcering vanaf het laatste
   punt, animatie uit bij reduced motion. **Afwijking:** geen toetsenbord-draadkruis; de grafiek is `role="img"` met een
   beschrijving en elke grafiek heeft "Toon als tabel" als toegankelijk alternatief (followup).
8. **Kopbalk P1.** Problemen (inktteller uit `/incidents/samenvatting`, "99+" met exact getal in sr-tekst), AI en het
   gebruikersmenu (account, uitloggen). **Niet gebouwd:** Zoeken (C-51) en de Live-indicator — er is in P1 geen
   zoekindex en geen live-stroom (alleen verversen per 30–60 s). Ze staan als followup; er is geen schijnknop.
9. **"Meer" blijft een pagina** (`/meer`) in plaats van een Sheet: de route bestaat al, is deep-linkbaar en getest. De
   Sheet-component is er (Radix Dialog) voor later.
10. **Executor-statuspagina in het Peil-sjabloon (C-55).** `apps/executor/src/executor/statuspagina.html` is een exacte
    kopie van `design/ontwerptaal/statuspagina.html` (test op drift); een renderer van ±20 regels doet `{{x}}` (altijd
    escaped), `ALS`/`NIET`/`ELK`. Velden heten nu `hub_adres`/`koppelcode`/`hub_vingerafdruk` (de oude namen blijven
    werken); fouten per veld met `aria-invalid` en skiplink naar het veld; "Gekoppeld" is een neutrale pil; het totaal is
    nooit groen zolang de executor niets uitvoert.
11. **Productnaam in de authenticator-app.** `otpauth`-issuer van het noodaccount is "TrueNAS Home Platform" (was "AI
    Server Manager").
12. **Web-E2E-teststack.** `tests/e2e/web_stack.py` start naast de fake TrueNAS ook fakes voor Uptime Kuma, Beszel,
    Gotify en een OIDC-issuer (met een browser-autorisatieroute in de fake), draait de periodieke worker-taken met korte
    intervallen en heeft besturingsroutes om een app aan de fake NAS toe te voegen en een simulator-dienst te laten
    koppelen (koppelcode) en events te laten sturen. Alles op loopback, alleen testsleutels; alleen ontwikkeling/CI.
13. **Peil-matrix in Playwright.** Elk scherm op 360/390/768/1440 in licht én donker met axe (WCAG 2.2 A/AA), geen
    horizontaal scrollen en doelen ≥ 44 px. **Afwijking:** 320 en 1024 zitten niet in de Playwright-matrix (wel in de
    prototypecontrole); dat zou de suite verdubbelen. Followup.

## Gevolgen

- De UI zegt overal eerlijk wat er niet is: P2-acties zichtbaar maar uit, `capability_unavailable` bij CPU/geheugen per
  app en containerlogs, GPU-temperatuur altijd Onbekend, "Geen open problemen" alleen met verse monitoring.
- ADR-0009 punt 1 ("geen CSS-framework, geen iconenbibliotheek") en punt 3 ("oude data wissen") zijn vervangen.
- Alles is **Sim-getest**; niets is gevalideerd op een echte NAS, telefoon, schermlezer, Authentik, Uptime Kuma,
  Beszel of Gotify (NIET GEVALIDEERD).
