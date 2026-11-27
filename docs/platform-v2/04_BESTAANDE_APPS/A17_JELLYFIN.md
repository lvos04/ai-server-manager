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
- **A3: Proefstop (alleen indien kandidaat):** schakel tijdelijk uit met eigen data intact en verifieer gebruikersreizen.
- **A4: Behoud/decommission:** beslissing schriftelijk, backup restore test, veilige rollback; data verwijderen staat los van app-stop.

## Testcase en beslissing
**Acceptatie:** No library/watch state regression.

NIET GEVALIDEERD (echte NAS). Leg vast of Jellyfin aanwezig is. Controleer bij een overstap de bibliotheek en vergelijk per gebruiker de kijkgeschiedenis en hervatpunten vóór en na de overstap. Elk verschil vraagt uitdrukkelijk akkoord van de gebruiker. Controleer of gebruikers in één handeling naar de bestaande installatie kunnen terugkeren.
