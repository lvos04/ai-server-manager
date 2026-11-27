# MediaGuard — behoud, migratie en acceptatie

## Besluit
Behouden, bibliotheek- en AV1-eigenaar.

## Waarom
Release 1.2.2; niet dupliceren; lees B04.

## Stand na P3 (simulator)

Maak in MediaGuard onder **Instellingen → API-sleutels** de sleutel `hub` aan met de rol Kijker (`viewer`) zonder extra rechten en voer hem in de Hub in.
Het scherm Media toont de aantallen openstaande zoekitems, mislukte taken, lopende AV1-encodes en open incidenten,
plus de stand van de noodstop. Voor een aflevering leest de Hub de opgeslagen diagnose. De downloadwachtrij en de
mediaserverstatus blijven onbekend. De noodstop bedienen, herstellen en opnieuw zoeken doet de beheerder in MediaGuard.
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
**Acceptatie:** Geteste noodstop, HDR/VMAF failclosed.

Leg bij de praktijkproef de installatiestatus en de werking van de noodstop vast. Controleer dat gebruikers in één handeling naar MediaGuard kunnen terugkeren en hun voortgang kunnen zien.
