# qBittorrent — behoud, migratie en acceptatie

## Besluit
qBittorrent is eigenaar van zijn torrentwachtrij en configuratie. De beheerder gebruikt qBittorrent voor handmatig
wachtrijbeheer. Voor de snelheidslimieten die MSO beheert, lopen wijzigingen uitsluitend via de bestaande
torrentregels van MSO. MediaGuard gebruikt de client voor zijn eigen downloads en import.
In versie 1 blijven de Hub en zijn executor alleen-lezen voor qBittorrent, ook bij algemene appacties en na
goedkeuring door een beheerder. [Gedeeld appbeleid](../../../policy/apps.yaml)

## Waarom
MSO tuning, hardlink en private trackers veilig.

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
**Acceptatie:** Geen automatische bestanden verwijderen.

**Praktijkproef:** NIET GEVALIDEERD (echte NAS). Controleer daar de installatiestatus, het behoud van bestanden en of gebruikers bij stoppen in één handeling kunnen terugkeren naar de bestaande app.
