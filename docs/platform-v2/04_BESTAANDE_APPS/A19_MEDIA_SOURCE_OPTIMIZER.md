# Media Source Optimizer — behoud, migratie en acceptatie

## Besluit
Behouden, bronoptimalisatie.

## Waarom
Head 1.6.0, release/VERSION 1.5.0 bij inspectie; lees B05.

## Stand na P3 (simulator)

De Hub leest zonder sleutel de bereikbaarheid, versie en inrichtingsstatus van MSO. MSO biedt voor beschermde
gegevens een machinesleutel met het recht `read`. De Hub kan dit recht nog niet bevestigen en toont open
wijzigingen en kosten daarom als onbekend. De beheerder bekijkt het wijzigingsvoorstel en keurt het in MSO goed.
MSO voert de wijziging uit en controleert het resultaat.

Op **Backups** blijft de dekking van MSO **Onbekend**. De Hub heeft geen toegestane leesroute voor een
back-upmeting. De openbare bereikbaarheidscontrole laat alleen zien of MSO reageert.

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
**Acceptatie:** Echte service mocks/live parity en geen owner writes.

Leg bij de praktijkproef de installatiestatus vast en vergelijk de resultaten van de brondiensten met die uit de simulator. Controleer bij een eventuele proefstop de terugkeer naar MSO in één handeling.
