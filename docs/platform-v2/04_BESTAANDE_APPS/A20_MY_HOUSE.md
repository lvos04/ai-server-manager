# my_house — behoud, migratie en acceptatie

## Besluit
Bouwen/testen en integreren (release v0.1.0).

## Waarom
Geen nieuw Home Assistant, apparatuur-gates; lees B06.

## Stand na P3 (simulator)

Maak in my_house een eenmalige koppelcode met rol Kijker (`viewer`) en doel `hub`. Voer de code en de
bijbehorende server-ID in de Hub in. Het scherm Huis toont per woning de zonetemperaturen, de stand van de
lichtgroepen en de open meldingen. De koppeling geeft alleen leesrecht. Voor bediening opent de beheerder
my_house. De boiler is uitsluitend een meetpunt. NIET GEVALIDEERD (echte NAS).

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
