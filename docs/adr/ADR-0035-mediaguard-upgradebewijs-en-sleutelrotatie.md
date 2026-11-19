# ADR-0035 — MediaGuard-upgradebewijs en rotatie van geplakte Hub-sleutels

Status: ontwerp ter review · 2026-11-19 · S-P3-015 · niveau N3.

Dit besluit werkt contract 1.3 §2.3 regels 3 en 7, §4.5, RV2 en RV8 uit. De uitvoering van
een MediaGuard-update via de Hub of de executor valt buiten P3. Voor my_house gebruiken
S-P3-740, S-P3-745 en S-P3-130 de afspraken hieronder over geplakte sleutelsets.

## A. MediaGuard levert het bewijs voor de exacte upgrade

De Hub leest in een latere bouwstap het releasebewijs van de eigenaar, `lvos04/media-guard-ultimate`,
via de GitHub Actions-metadata en het bijbehorende releaseartefact. Het bestaande
`scripts/upgradebewijs.py poort` meet de upgrade op de gevulde fixture van de direct vorige release,
vergelijkt de voortgang en doet een API-terugleesproef. Daarna controleert het script terugzetten
met de vorige image én de snapshot van vóór de upgrade. `deploy/upgradebewijs/vorige-release.json`
op de releasecommit beschrijft bronversie, brondigest en fixture. In `.github/workflows/release.yml`
bewaart de job `upgradebewijs` het rapport als `upgradebewijs-<versie>` gedurende 90 dagen.
Publicatie hangt van die job af en neemt de geteste kandidaat over zonder herbouw.

De Hub gebruikt uitsluitend het vaste repository en de workflow `release.yml` van de eigenaar.
Voor een bruikbaar bewijs moeten alle volgende controles slagen:

1. De vrijgegeven versie in `deploy/release-manifest.json` op de releasecommit, de releasecommit
   van de run en de versie in het rapport horen bij dezelfde release. De run, de job `upgradebewijs`
   en de publicatiejob zijn succesvol afgerond. De Hub koppelt run-ID, poging, jobs en artefact
   eenduidig aan elkaar. Het rapport uit die poging bevat zowel `Upgrade: niets verloren` als
   `terugzetten: niets verloren`. Een rapport kan ook bij een mislukte job worden bewaard, dus
   de tekst alleen voldoet niet.
2. Versie én digest van de werkelijk draaiende installatie komen overeen met de bronversie en
   brondigest die in die job zijn beproefd. Een overgeslagen tussenrelease vereist eigen bewijs
   voor die bron-doelcombinatie. Een onbekende installatie levert geen bruikbare bronversie op.
3. De Hub kan uit onveranderlijk bewijs van de uitgevoerde proef vaststellen welke OCI-digest
   daadwerkelijk getest is. De digest moet gelijk zijn aan die van het vrijgegeven alles-in-één-image
   in GHCR en aan de vastgepinde doeldigest van het voorstel. Een kandidaat-tag, release-tag,
   OCI-label of een build van dezelfde commit op zichzelf bewijst die gelijkheid niet. Als
   de huidige jobgegevens alleen een kandidaat-tag aan de proef binden, blijft de update dicht.
4. Het bewijs is beschikbaar, niet ingetrokken en hooguit 90 dagen oud, gerekend vanaf de
   voltooiingstijd van de geslaagde bewijsjob in UTC. De effectieve grens is de vroegste van
   die termijn en het verval van het artefact. Opnieuw ophalen of opnieuw publiceren in de
   Hub verjongt het bewijs niet. Een ontbrekende of toekomstige voltooiingstijd wordt geweigerd.

De Hub bewaart de bron- en doelversie met hun digests, de releasecommit, het run-ID en de poging,
het artefact-ID, de voltooiingstijd en de uitkomst van de controles. Een gebruiker kan geen bewijs
uploaden of als geldig markeren. De geplande leescontrole gebruikt GitHub en GHCR, zonder nieuwe
MediaGuard-route. Het leesmodel van de adapter, een groene algemene CI-run, de rooktest en een
gepubliceerde tag zijn geen vervanging. Als de releasegegevens onvoldoende binding leveren,
moet de eigenaar bij een toekomstige bouwstap de geteste digest vastleggen in het releasebewijs.

### Weigering in de Hub

In P3 blijft `APP-MEDIAGUARD` in `policy/apps.yaml` van kracht, ook als een bruikbaar rapport wordt
gevonden. Er is geen weg via het algemene appbeheer, een handmatig goedgekeurd voorstel of een
direct `ExecutionRequest` om toch een MediaGuard-update te starten. Herken MediaGuard aan de
huidige installatie én aan het beoogde image. Wanneer identiteit onduidelijk is, blijft de actie
geweigerd. Dit geldt voor alle uitvoeringspaden, inclusief catalogus-upgrades, achtergronduitvoering
en retry. Pas in een expliciete latere bouwstap mag een updatepad beschikbaar komen. Dan controleert
de Hub vóór goedkeuring en opnieuw vóór het versturen, en weigert de executor vóór elke mutatie
zelfstandig bij ontbrekend, ongeldig of verlopen bewijs voor de dan geldende bron en doel.
Goedkeuring, het risicobeleid, back-upbevestiging, terugval, compatibiliteitscontroles en controles
na de update blijven afzonderlijke voorwaarden. Ook via dat pad wordt nooit rechtstreeks in een
database van Emby, Jelly Leon of MediaGuard geschreven.

Bij een ontbrekend of oncontroleerbaar rapport toont de Hub bijvoorbeeld **‘MediaGuard is niet
bijgewerkt. Voor deze update ontbreekt een geldig bewijs dat de voortgang behouden blijft.’**
Bij een verlopen rapport toont de Hub **‘MediaGuard is niet bijgewerkt. Het upgradebewijs is
verlopen.’** Bij een afwijkende versie of digest meldt de Hub **‘Het upgradebewijs hoort bij
een andere versie van MediaGuard.’** Met geldig bewijs in P3 toont de Hub **‘Bijwerken van
MediaGuard via de Hub is nog niet beschikbaar.’** De Hub toont versies en, indien bekend, een
verwijzing naar de gecontroleerde release-run. De bewijsregel voor dit besluit is `C1.3-ASM-19`
in `docs/platform-v2/EVIDENCE.json`. B04-009 omvat daarnaast de MSO-compatibiliteitscontrole.

Z-03, optie 1, geldt bij elke upgrade die de database van een mediaserver migreert. Vereist
zijn een vóór/na-rapport per gebruiker en uitdrukkelijk akkoord op elk verschil. Terugzetten
betekent de vorige image én de snapshot samen. Het releasebewijs op een fixture vervangt dat
rapport en akkoord niet. Emby blijft beschikbaar en de bestaande MediaGuard-koppeling blijft werken.

## B. Bevestiging per app met geplakte sleutels

De Hub telt elke actieve koppeling met een geplakte sleutelset mee, ook als my_house offline is.
Een koppeling is gebonden aan de bevestigde Hub en de specifieke doelinstantie. Voor iedere
R2-rotatie legt de Hub per doel (`jwt` of `policy`) de volgorde uit §4.5 en de verwachte
vingerafdruk van de volledige resulterende publieke sleutelset vast. Alleen een beheerder kan
een rotatie starten of een bevestiging registreren. Het ophalen van JWKS geeft geen vertrouwen.

1. **Voorbereiden.** De Hub houdt de bestaande sleutel en publiceert de ondertekende
   rotatieverklaring op `GET /api/v1/auth/key-rotations` wanneer dat pad is gebouwd. De app
   verifieert de verklaring met een al gepinde sleutel voor hetzelfde doel. De app controleert
   de aaneengesloten globale `sequence` over beide doelen en weigert een ongeldige verklaring,
   een sprong in de volgorde of het intrekken van de laatste sleutel voor een doel. Zolang
   ondertekende rotatie niet beschikbaar is, kan een beheerder expliciet opnieuw koppelen via
   het bestaande proces met de geplakte publieke sleutelset van de bevestigde Hub. In dat geval
   levert de Hub de bijbehorende actuele volgorde en vingerafdruk bij de herbevestiging.
2. **Bevestigen in my_house.** De beheerder vergelijkt op het geplande Systeem-scherm de oude en
   nieuwe vingerafdruk en bevestigt de nieuwe, zoals voorzien in S-P3-745. De app berekent de
   vingerafdruk over alle JWT- en policy-sleutels volgens §4.5, inclusief beide policy-sleutels
   tijdens de overlap. De testvector voor twee policy-sleutels is `HN69-2PHK-XV2D-X85W`.
   Alleen een geldige, bevestigde set wordt atomair gepind met de volgorde en vingerafdruk.
   my_house toont de actuele waarden pas nadat de set duurzaam is opgeslagen. Zonder gepinde
   policy-sleutel weigert my_house het schrijfpad met `501 capability_unavailable`.
3. **Bevestigen in de Hub.** De beheerder leest de waarden af in de beheer-UI van de bevestigde
   doelinstantie, selecteert de betrokken koppeling in de Hub en verklaart dat de app de set
   heeft vastgelegd. De beheerder voert daarbij de volgorde en vingerafdruk in die de app na
   het vastleggen toont. De Hub accepteert alleen de
   verwachte volgorde en, na normalisatie volgens §4.5, de exacte verwachte vingerafdruk voor
   de betrokken koppeling, instantie, rotatie en doel. De Hub legt vast welke beheerder de
   bevestiging gaf en wanneer. Een preview, een bereikbaarheidsmeting, een kopieeractie in de
   Hub of een bevestiging van een andere instantie voldoet niet. Deze handmatige bevestiging
   heeft geen nieuwe my_house-route of `/connector/v1/hub-link` op my_house nodig.
4. **Activeren en intrekken.** De Hub blijft met de bestaande sleutel ondertekenen zolang één
   actieve ontvanger de oude set heeft gepind of zijn bevestiging ontbreekt. Gekoppelde diensten
   waarvoor het contract `GET /connector/v1/hub-link` voorschrijft, bevestigen daar zoals in §4.5.
   Vóór de wissel controleert de Hub onder dezelfde vergrendeling de actuele ontvangers en hun
   bevestigingen. Een nieuwe of opnieuw gekoppelde instantie telt meteen mee. Een offline app,
   mislukte invoer of onbereikbare controle opent de gate niet. Eerst volgt de bevestigde
   toevoeging van de nieuwe sleutel, daarna de wissel van ondertekenaar. Intrekken is een
   volgende bevestigde wijziging, nadat eerder ondertekende verzoeken en tokens van die sleutel
   zijn verlopen. Elke wijziging wordt per doel en volgorde behandeld en geaudit. Een app die
   aantoonbaar ontkoppeld en ingetrokken is, verlaat de actieve ontvangerslijst. Alleen
   onbereikbaarheid of het verbergen van de koppeling doet dat niet. Herstel of vervanging van
   een instantie mag een oude pin niet opnieuw activeren onder een bestaande bevestiging.
   Behoud bij herstel de laatst bevestigde pin of trek de oude koppeling in en bevestig opnieuw
   vóór het schrijfpad beschikbaar komt.

Bij een ontbrekende bevestiging ziet de beheerder per app **‘Sleutelrotatie wacht op bevestiging
in de app.’** Een foutieve vingerafdruk of een mislukte opslag laat de oude pin staan. Zolang de
Hub nog geen sleutelrotatie ondersteunt, blijft zijn rotatie-endpoint leeg en is opnieuw koppelen
de beschikbare sleutelwissel volgens §4.5. De Hub mag dat proces niet gebruiken om actieve
ontvangers van de oude set stilzwijgend te passeren.

## Acceptatie bij de vervolgbouw

- Een lokaal gesimuleerde release met volledig, passend bewijs krijgt de bewijsstatus geldig.
  P3 weigert ook dan de update. Ontbrekend, verlopen, teruggetrokken of niet aan de geteste
  digest gebonden bewijs mag nooit leiden tot een muterend verzoek. Test ook een rapport uit
  een mislukte of andere poging, een gewijzigd voorstel en een herhaling na het verstrijken
  van de geldigheid. De proef controleert afwezigheid van elk muterend verzoek, ook bij een
  direct verzoek aan de executor.
- Bevestiging van alle actieve ontvangers maakt in de latere rotatiebouw de juiste nieuwe
  sleutel activeerbaar. Beproef ook één offline app, een andere instantie, een oude volgorde,
  ontbrekende tweede policy-sleutel, ongeldige handtekening, mislukte opslag en een nieuwe
  koppeling tijdens de wissel. In die gevallen blijft de bestaande ondertekenaar actief en
  zorgt een herhaalde bevestiging voor hoogstens één overgang.

Bronnen: [Platformcontract §2.3, §4.5, §8 en §11](../platform-v2/PLATFORM_CONTRACTEN.md),
[conformiteit C1.3-ASM-19 en C1.3-MH-04](../platform-v2/CONTRACT_1.3_CONFORMITEIT.md),
[ADR-0020 over kijkgeschiedenis](ADR-0020-kijkgeschiedenis-altijd-beschikbaar-en-emby-overname.md),
[ADR-0034 over leesadapters](ADR-0034-adapters-bestaande-apps.md) en
[de releaseworkflow van MediaGuard](https://github.com/lvos04/media-guard-ultimate/blob/4610591778fa4bec720aa34fdb382918d9baa8ee/.github/workflows/release.yml).
