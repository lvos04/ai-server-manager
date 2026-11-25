# Prowlarr — behoud, migratie en acceptatie

## Besluit
Prowlarr is de enige eigenaar van de indexercatalogus. De beheerder wijzigt indexers, tags en de native
synchronisatie in Prowlarr. De gekoppelde MediaGuard-forks ontvangen de synchronisatie. MSO mag een
zoekendpoint aanbieden. In versie 1 blijven de Hub en zijn executor alleen-lezen voor Prowlarr, ook na
goedkeuring door een beheerder. Dit geldt ook voor algemene appacties. [Gedeeld appbeleid](../../../policy/apps.yaml)

## Waarom
Eén synchronisatie houdt indexers en tags in de gekoppelde apps consistent.

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
**Acceptatie:** Geen cyclische zoeklus of tag drift.

**Praktijkproef:** NIET GEVALIDEERD (echte NAS). Controleer daar de installatiestatus, de synchronisatie en of gebruikers bij stoppen in één handeling kunnen terugkeren naar de bestaande app.
