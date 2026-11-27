# SABnzbd — behoud, migratie en acceptatie

## Besluit
Behouden als eigenaar van de Usenet-wachtrij en de algemene configuratie. De beheerder wijzigt de wachtrij in
SABnzbd. Voor de nieuwsserverinstellingen die MSO beheert, zoals de serverprioriteit, is MSO de enige schrijver.
MSO volgt zijn eigen goedkeuringsregels en leest het resultaat terug.
MediaGuard levert downloadopdrachten voor zijn eigen categorieën en importeert de resultaten.
De Hub en zijn executor hebben alleen leesrecht voor SABnzbd, ook bij algemene appacties en na
goedkeuring door een beheerder. [Gedeeld appbeleid](../../../policy/apps.yaml)

## Waarom
MSO diagnostiek en MediaGuard import horen via API.

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
**Acceptatie:** Geen wildcard category misrouting.

**Praktijkproef:** NIET GEVALIDEERD (echte NAS). Controleer daar de installatiestatus, de routering per categorie en of gebruikers bij stoppen in één handeling kunnen terugkeren naar de bestaande app.
