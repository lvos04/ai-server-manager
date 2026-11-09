# ADR-0020 — Kijkgeschiedenis altijd beschikbaar; overname vanuit Emby

Status: aangenomen · 2026-11-09 · besluit van de gebruiker (keuzemenu, `02_BOUWPLANNEN/B03_BESLUITEN.md` §1) · raakt de
programmagates (`01_ARCHITECTUUR/06_FASERING_EN_GATES.md`), de Excel, de Hub (B12-dekking) en de deltaverzoeken aan
media-guard-ultimate. De uitvoering staat in het bouwplan B03 (B03-015, §10.9.1, §10.9.2) en in jelly-leon.

## Context

- De gebruiker gebruikt nu **Emby** als mediaserver; de kijkgeschiedenis van het hele huishouden staat daar. Versie,
  plugins, gebruikers en bibliotheken zijn nog niet gemeten (D07 blijft Open tot de wizard of de TrueNAS-API het meet).
- De gebruiker: "Het belangrijkste is mijn kijkgeschiedenis; als alles werkt verwijder ik Emby."
- Jellyfin 12.x draait bij de upgrade migraties die gebruikersgegevens kunnen veranderen (`HarmonizeConflictingUserData`,
  `MergeDuplicatePeople`, `RemoveOrphanedUserPermissionsAndPreferences`); een 10.11-back-up is in 12.x niet terug te zetten.
- MediaGuard volgt nu Emby met `X-Emby-Token`; Jelly Leon 12.x weigert die header (legacy-auth uit, BG-01).
- De bestaande rijen APP-02 (Emby) en I26-26-02 ("Plex/Emby slechts kandidaat stop na client/library parity";
  "Gebruikers/kijkstatus behouden") gelden al.

## Besluit

1. **HARDE EIS (letterlijk):** alle kijkgeschiedenis (gezien-status, hervatpunten, favorieten, beoordelingen, onthouden
   spoorkeuzes, gebruikers, rechten) en de MediaGuard-voortgang blijven altijd beschikbaar.
2. **Geen cutover** zonder vóór/na-rapport per gebruiker en uitdrukkelijk akkoord van de gebruiker op elk verschil, ook op
   verschillen door upstream-migraties. Dit is een harde gate in `06_FASERING_EN_GATES.md` (Gate matrix) en in de no-go
   van P4-0 en P4. De bestaande installatie blijft ongewijzigd als terugval.
3. **Overname vanuit Emby (B03-015 deel A), prioriteit P0 en al in golf 0:** alleen lezen uit Emby (API-sleutel, alleen
   GET); koppelen op provider-ID's en daarna pad; wat niet te koppelen is, op een afhandellijst; per gebruiker gezien-status,
   hervatpunten, favorieten en waar mogelijk beoordelingen en spoorkeuzes; herhaalbare proefrun; laatste delta bij de
   overstap; wachtwoorden niet (nieuw wachtwoord of SSO). Eerst JellyPlex-Watched (GPL-3.0) beoordelen op hergebruik. Doel:
   100 % van gezien-status en hervatpunten. Testen JLT-70…74 (P0; JLT-74 *Geblokkeerd* tot de echte NAS).
4. **MediaGuard volgt Emby én Jelly Leon tegelijk** (Δ-MG-DUAL, met Δ-MG-AUTH per server); de Emby-koppeling onderbreekt
   nooit. Elke MediaGuard-release, ook de eerste uit de nieuwe publieke repo, bewijst een upgrade op een gevulde database van
   de vorige versie zonder gegevensverlies; UI-rondes wijzigen geen datamodel.
5. **Emby verwijderen doet de gebruiker zelf**, pas na de controlelijst van bouwplan §10.9.2: laatste delta, eindrapport per
   gebruiker met akkoord, ZFS-snapshot van de Emby-dataset, een blijvend JSON-exportarchief van alle Emby-kijkgegevens met
   sha256 op de NAS én in de back-updekking (B12; Hub-kaart Back-ups via Δ-HUB-3) zodat herimport later kan, en MediaGuard
   laat Emby netjes los. App stoppen en data verwijderen blijven aparte stappen (APP-02/A4).
6. **Excel:** B03-015 en JLT-70…74 staan op P0; geen van deze rijen krijgt hier een eindstatus.

## Alternatieven

- *Kijkgeschiedenis opnieuw opbouwen in Jelly Leon:* verworpen door de gebruiker (belangrijkste gegevens).
- *Emby direct uitzetten bij de overstap:* verworpen; Emby blijft de terugval tot de controlelijst is afgewerkt.
- *Rechtstreeks in de databases van Emby of Jelly Leon lezen/schrijven:* verworpen (geen garantie op schema, risico op stille
  schade; regel "geen directe DB-writes").
- *MediaGuard in één keer omzetten van Emby naar Jelly Leon:* verworpen; dan valt de kijkpauze voor Emby-kijkers weg zolang
  Emby nog in gebruik is.

## Gevolgen

- Hub: het Emby-exportarchief wordt een B12-dekkingsitem (Δ-HUB-3); de wizard meet D07 (Emby) zodra de NAS bereikbaar is.
- Gates: "vóór/na-rapport per gebruiker + akkoord" vóór elke cutover; "controlelijst Emby verwijderen" vóór Emby uit.
- Werk in golf 0 krijgt voorrang voor de Emby-overname bij een conflict om de ontwikkelmachine.

## Verificatie

JLT-70 (proefrun met een echte Emby-container `emby/embyserver` op vaste versie en digest, corpus en synthetische
gebruikers), JLT-71 (idempotent, laatste delta), JLT-72 (afhandellijst, 0 stil weggelaten), JLT-73 (0 schrijfacties naar
Emby via een loggende proxy; MediaGuard volgt beide), JLT-74 (echte NAS en de controlelijst; *Geblokkeerd*, NIET
GEVALIDEERD (echte NAS)).
