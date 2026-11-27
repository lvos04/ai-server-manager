# my_house — behoud, migratie en acceptatie

## Besluit
Integreren met de Hub voor het huisoverzicht en voor herstelbare temperatuurwijzigingen na goedkeuring.

## Waarom
Geen nieuw Home Assistant, apparatuur-gates; lees B06.

## Stand na P3 (simulator)

Voer in de Hub de eenmalige kijkerscode (rol `viewer`, doel `hub`) en de server-ID uit my_house in. Het scherm
Huis toont zonetemperaturen, lichtgroepen en open meldingen. Bevestig voor ondertekende voorstellen ook de publieke
Hub-sleutelset in my_house. Na vrijgave van de fysieke klimaatbediening en goedkeuring kan de Hub een herstelbare
wijziging van de insteltemperatuur laten uitvoeren. Het journaal bevestigt de uitvoering zodra de voor- en nameting
overeenkomen met de goedgekeurde wijziging.
Een nieuw zoneschema blijft een concept. Zonder herstelpad bedient de beheerder lichtgroepen en scènes in my_house
en hervat daar het zoneschema. De boiler is uitsluitend een meetpunt.

Op **Backups** leest de Hub de back-upcontrole uit de systeemstatus van my_house. Alleen een actuele `ok` met
een geldige back-upleeftijd binnen de grens en zonder automatische back-upfouten telt als gedekt. Ontbreekt de
meting of is ze verlopen, dan toont de Hub **Onbekend**. Meldt de meting een te oude back-up of een automatische
back-upfout, dan toont de Hub **Niet gedekt**.

NIET GEVALIDEERD (echte NAS).

## Verplichte inventaris voor bouwer
1. Draaiende TrueNAS image-tag/digest, container ID, owner en status (niet alleen repositoryversie).
2. Netwerkpoorten, domein, eventuele VPN/tunnel en gekoppelde app credentials (geschoond).
3. Datasets, database en restoretype; controleer OneDrive-dekking en snapshot.
4. API dependencies: welke apps praten ermee en welke acties mogen zij uitvoeren?
5. Laatste echte gebruiksdatum, hulpcode, logs en performance.

## Gefaseerde aanpak
- **A0: Meten:** documenteer bovenstaande, inclusief screenshot van huidige UI en configuratie-export.
- **A1: Niet-mutatief integreren:** koppel in Hub als catalogusitem, toon status en diep-link.
- **A2: Verbeteren of vervangen:** voer alleen functies die aantoonbaar ontbreken uit via de in B-plannen vastgelegde data-eigenaar.
- **A3: Proefstop (alleen indien kandidaat):** schakel tijdelijk uit met eigen data intact en verifieer gebruikersreizen.
- **A4: Behoud/decommission:** beslissing schriftelijk, backup restore test, veilige rollback; data verwijderen staat los van app-stop.

## Testcase en beslissing
**Acceptatie:** Boiler nooit schakelen; Gree readback.

Leg bij de praktijkproef de installatiestatus vast en controleer de teruggelezen apparaatstatus in my_house. Controleer bij een eventuele proefstop de terugkeer naar de app in één handeling. NIET GEVALIDEERD (hardware).
