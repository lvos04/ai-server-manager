# Jellyfin — behoud, migratie en acceptatie

## Besluit
Een bestaande Jellyfin-installatie behouden als mediaserver. Jellyfin is de basis voor Jelly Leon.

## Waarom
Client compat met huidige media testen.

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
- **A3** Beproef de migratie en de terugval op een kopie terwijl de bestaande installatie in gebruik blijft.
- **A4** Leg de beslissing over de overstap schriftelijk vast. Het verwijderen van gegevens vraagt een apart besluit.

## Testcase en beslissing
**Acceptatie:** No library/watch state regression.

NIET GEVALIDEERD (echte NAS). Leg vast of Jellyfin aanwezig is. Volg deze stappen bij een overstap van mediaserver
of een upgrade die de database migreert. De bestaande installatie blijft tijdens de proef en na de overstap
ongewijzigd beschikbaar als terugval. Zie [contract §2.3 regel 7a](../PLATFORM_CONTRACTEN.md#23-bestaande-apps-mediaguard-mso-my_house-jellyfinjelly-leon-emby)
en [ADR-0020](../../adr/ADR-0020-kijkgeschiedenis-altijd-beschikbaar-en-emby-overname.md).

1. Voer de migratie op een kopie uit. Vergelijk de bibliotheek, alle gebruikers en hun rechten vóór en na de
   proefmigratie. Vergelijk voor iedere gebruiker ook de gezien-status, hervatpositie, favorieten, beoordelingen
   en onthouden spoorkeuzes per titel. Leg de uitkomst en elk verschil vast in een vóór/na-rapport per gebruiker.
2. Test de terugval op een kopie door de vorige image samen met de bijbehorende snapshot terug te zetten.
   Controleer of de kijkgegevens en de rechten weer kloppen en of gebruikers in één handeling naar de
   bestaande installatie kunnen terugkeren.
3. Vraag de gebruiker om uitdrukkelijk akkoord op het rapport en op elk verschil afzonderlijk, ook als dat door
   een upgrade van Jellyfin is ontstaan. Zelfs één onbeoordeelde afwijking blokkeert de overstap.
4. Schakel pas over na een werkende terugvalproef en het vastgelegde akkoord van de gebruiker.
