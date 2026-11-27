# NAS-acceptatiedraaiboek

## Begin hier

Leg je privé-invulblad, TrueNAS-webtoegang, OneDrive-back-up, lege herstelplek, telefoon en spelers klaar. Plan de proef als niemand kijkt. Gebruik de openbare images op `ghcr.io/lvos04/<image>` met de volledige pin (versietag met digest) uit de tabel in het draaiboek onder **Een app installeren en terugzetten**. Zet vooraf op GitHub de vijf pakketten op openbaar: ai-server-manager, ai-server-manager-executor, home-control-hub, appstore-en-fork en jelly-leon-platform. Vraagt de NAS om een registerinlog, stop dan en meld het. Lees bij elk onderdeel eerst **Voor je begint** en **Stop als**.

### Vier gouden regels

1. Gebruik alleen de webinterface van TrueNAS, Hub en apps, zonder terminal of YAML.
2. Houd Emby aan en gekoppeld buiten je proefstop. **Delete** van Emby en wissen van Emby-opslag zijn verboden. Uitfasering vraagt een aparte opdracht.
3. Maak vóór elke stap een ZFS-snapshot. Controleer of die alle betrokken gegevens dekt.
4. Alleen jij zet een Excel-rij op **Gereed** of **Geslaagd**.

### Je drie besluiten van 25 november 2026

1. **Je stopt Emby zelf minstens 72 uur (keuze B).** Lees vóór overstap en proefstop de kijkgegevens per gebruiker en soort. Noteer bij elk verschilakkoord de geteste vindplaats. Beproef één keer uitval direct na een nieuw Jelly Leon-hervatpunt, vóór de gewone kopieverversing. Lees die positie via de afgeschermde route zonder het gewone doel. Lukt dit niet of ontbreekt een waarde, dan wachten overstap én proefstop.
    - Pauzeer vóór ontkoppelen de MediaGuard-taken die de voortgang wijzigen. Laat lopend werk afronden en controleer de wachtrij. Zonder stabiele pauze wacht de proef. Stop pas na vijf gedateerde ja’s en opnieuw nul actieve sessies in Emby zelf. De taken blijven de hele proefstop gepauzeerd, ook bij voldoende ruimte. Ververs de kopie minstens dagelijks en direct vóór een geplande terugkeer.
    - Keer bij afloop, uitstel of gemis direct terug. Zodra Emby draait en gekoppeld is en gewoon aanmelden, afspelen en de Emby-kijkpauze werken, mag iedereen weer kijken. Hervat taken pas na de gecontroleerde terugkeer. Bij afwijkende Jelly Leon- of MediaGuard-gegevens blijven de proef open en de taken gepauzeerd.
2. **Bewaar mediasnapshots tot 30 dagen na de laatste geslaagde stap**, langer zolang nodig voor herstel. Bescherm altijd de nieuwste snapshot per dataset, ook na afbreken, de laatste Emby-snapshot, het exportarchief en elk nodig herstelpunt. Onder **20% vrije poolruimte** pauzeer je nieuwe MediaGuard-taken. Alleen dan mag je eerder vrijgeven. Controleer vóór wissen de exacte snapshot, bescherming en herstelafhankelijkheden. Wis alleen de oudste door jou vrijgegeven, onbeschermde mediasnapshot. Meet na elke verwijdering opnieuw. Stop bij minstens 20% of zonder vrijgegeven kandidaat. Stel alleen een bewaartermijn in als elk beschermd of nog niet vrijgegeven herstelpunt aantoonbaar behouden blijft.
3. **Geen proef-VM.** MediaGuard blijft op de huidige versie met Emby werken. De upgrade wacht. Authentik, AdGuard Home en Navidrome mogen via de community-trein op hun vaste manifestversie. Navidrome vraagt ook een **ja** bij muziekbesluit D18.

<div style="break-before: page; page-break-before: always;"></div>

### De veertien onderdelen

Begin met **01 → 02 deel a → 03 → 02 deel b**. Doe 05 na heel 02 en 07 na 04. Volg voor de overstap **05 → 09 → 10 → 11 → 12 → 13**. Begin 14 na terugkeer van Emby.

| Onderdeel | Wat je doet | Reken op | Wat het oplevert |
|---|---|---|---|
| N-P6-01 | NAS en bestaande apps bekijken | 30–60 min | Privé-invulblad en leesaccount |
| N-P6-02 | Back-up in twee delen testen | 1–2 uur + kopieertijd | Foto en database hersteld op een lege proefplek |
| N-P6-03 | Hub en executor installeren | 1–2 uur | Koppeling en rechten getest |
| N-P6-04 | Bewaking en aanmelding op Hub en aangewezen proefroutes | 1–2 uur | Gewoon Emby-aanmelden en afspelen vóór en na getest |
| N-P6-05 | Apps, MediaGuard en Media Source Optimizer uitlezen | 45–90 min | Versies en voortgang. Wijzigende proeven wachten |
| N-P6-06 | my_house op apparaten testen | 1–2 uur + 1 dag | Bediening en daggrafiek getest |
| N-P6-07 | DNS op één apparaat testen | 45–90 min | Terugweg naar de oude DNS |
| N-P6-08 | Zoeken, persoonlijke AI en eventueel muziek testen | 1–2 uur + indexering | Zichtbare resultaten per gebruiker |
| N-P6-09 | Jelly Leon naast Emby installeren | 2–4 uur | Afspelen per speler en grafische kaart getest |
| N-P6-10 | Modules onder belasting testen | 2–4 uur | Afspelen tijdens ander werk getest |
| N-P6-11 | Kijkgegevens overnemen, eerst op een kopie | 2–4 uur + kopieertijd | Rapport en geteste vindplaats per verschil |
| N-P6-12 | Speler heen en terug met beide servers aan | 1–2 uur + proefperiode | Nieuw hervatpunt bij uitval teruggelezen |
| N-P6-13 | Omkeerbare Emby-proefstop volgens de zes proefpunten | 30–60 min + minstens 72 uur uit | Emby weer gekoppeld, kijkpauze werkt. Je vinkt alleen de proefstop af |
| N-P6-14 | Duurproef en zo mogelijk herstel op een tweede omgeving | 1–2 uur + minstens 72 uur aan | Meetwaarden voor jouw acceptatiebesluit |

Vóór ontkoppelen heb je apart, gedateerd bewijs op dezelfde versies nodig voor **Start**, **Weer koppelen**, gewoon aanmelden, afspelen, kijkpauze en intacte kijkgegevens en rechten. Lees op een geïsoleerd doel uit één actuele MediaGuard-herstelset de open en afgeronde taken, werkgegevens, het journaal en de bijbehorende originelen terug. Ontbreekt één van beide bewijzen, dan wacht de proefstop. Bij betaald gebruik in 08 meet je ook een week het verbruik.

**Emby blijft draaien en gekoppeld, behalve tijdens je eigen omkeerbare proefstop in N-P6-13.** Het besluit van 25 november 2026 past de beschikbaarheidseis alleen voor die proef aan. Ook tijdens de proef en bij terugval moet je de kijkgegevens van iedere gebruiker en de actuele MediaGuard-voortgang kunnen teruglezen. Maak vóór elke stap een verse ZFS-snapshot van de betrokken gegevens en zoek die terug. In versie 1 zijn **Delete** van Emby en het wissen van de Emby-opslag verboden.

- **Apps.** Kies in TrueNAS op de appkaart van Emby, een bestaande Jellyfin en MediaGuard nooit **Roll Back** of **Update**. Dit geldt ook bij een storing of als er een verse snapshot is. Bij ixVolume-opslag kan **Roll Back** ook de opgeslagen gegevens terugzetten. **Update** kan de app herstarten en het afspelen onderbreken.
- **Datasets.** Kies nooit **Rollback** op een dataset van Emby, MediaGuard of de media, ook niet op een bovenliggende dataset. Wijzig op geen van die datasets de eigenaar, rechten of ACL, ook niet recursief.

Je doorloopt dit draaiboek zelf in de webinterface van TrueNAS, de Hub en de apps, zonder terminal, YAML of compose. Eigen gegevens vul je uitsluitend op je eigen systeem in. De regisseur vult de tag en digest na elke release in. Een installatie wacht tot de release, de digest en een bruikbare terugweg vaststaan. De overname wacht op een werkende webassistent. Alleen jij kiest in Excel **Gereed** of **Geslaagd**.

## Werken met het draaiboek

- **Begin bij de gegevens die er al zijn.** Maak vóór de eerste stap een ZFS-snapshot van de bestaande appdata. Noteer bij iedere volgende stap lokaal tijdstip, dekking en versies van de nieuwe snapshot. Neem bij wijzigingen aan een database ook een consistente export op. Controleer of je de bijpassende versie én gegevens op een aparte plek kunt herstellen. Lukt het maken of identificeren van het herstelpunt niet, houd dan op vóór die stap.
- **Controleer het doel vóór herstel.** Herstel een snapshot voor een proef uitsluitend naar een afzonderlijke kloon of een lege proefdataset. **Rollback** zet de gekozen dataset terug in de tijd. Daarbij kunnen recente kijkgegevens, voortgang, mediabestanden en nieuwere snapshots verloren gaan. De harde eis geldt ook voor de eigen `/config` van MediaGuard. Verschijnt een beschermd doel, een verzoek om nieuwere snapshots te verwijderen of een voorstel om rechten te verruimen, sluit het scherm zonder te bevestigen.
- **Bescherm de herstelpunten.** Bewaar altijd de nieuwste snapshot per dataset, ook als de bijbehorende stap is afgebroken of mislukt. Bescherm ook de laatste Emby-snapshot, het blijvende exportarchief en alle snapshots die nog nodig zijn voor een leesroute, herstelproef of terugweg. Bewaar elke mediasnapshot normaal tot **30 dagen na de laatste geslaagde stap** en langer zolang herstel ervan afhangt. Werk na elke geslaagde stap de vrijgavedatums bij. Controleer vóór **elke** verwijdering de exacte dataset, snapshot en tijdstip, de bescherming, alle herstelafhankelijkheden en jouw uitdrukkelijke vrijgave. Een datum geeft op zichzelf geen toestemming om te wissen. [N-P6-02, punt 3][snapshotbescherming]
- **Bij minder dan 20% vrije poolruimte** pauzeer je nieuwe MediaGuard-taken. Controleer dat ze wachten, laat lopend werk veilig afronden en meld de afwijking. Alleen dan mag jij een onbeschermde mediasnapshot vervroegd vrijgeven. Kies de oudste vrijgegeven mediasnapshot en verwijder die zelf na de controle hierboven. Meet na elke verwijdering opnieuw. Stop bij minstens 20% of zodra er geen vrijgegeven mediasnapshot meer is. Zijn alleen beschermde snapshots over, laat ze staan en houd de taken gepauzeerd zolang de ruimte onder de grens ligt. Tijdens de hele Emby-proefstop blijft de taakpauze bij elke ruimtestand gelden. [N-P6-02, punt 3][snapshotbescherming]
- **Bij de kijkgeschiedenis gelden vier voorwaarden samen.** Vóór een overdracht zijn er een ZFS-snapshot, een blijvend exportarchief met SHA-256, een droge proefrun met rapport en jouw uitdrukkelijke akkoord op elk verschil. Leg bij elk akkoord vast waar het gegeven met de juiste rechten terug te lezen is. De eerste overdracht gaat naar een kopie van het doel. Emby levert uitsluitend leesgegevens. Dezelfde bescherming geldt voor de laatste delta.
- **Volgorde.** Doe 01 → 02 deel a → 03 → 02 deel b. Daarna kan 04 beginnen. Voor 05 moet 02 helemaal af zijn. Voor 07 moet ook 04 werken. Voor 08 heb je 05 nodig als je foto's uit Immich wilt doorzoeken. De media-overstap loopt via 05 → 09 → 10 → 11 → 12 → 13. Bij 10 staat welk deel ná 11 terugkomt. Huis, DNS en zoeken staan los van de overstap. In 14 bepaal je zelf wat je accepteert.
- **Bij een ontbrekend scherm.** De menunamen komen uit de installatiehandleidingen en de appcode. De bediening op jouw installatie is **NIET GEVALIDEERD op de NAS**. Waar de precieze bediening ontbreekt, staat **ONBEKEND - eerst vaststellen op de NAS**. Noteer de afwijkende schermtekst zonder privégegevens. Wacht als een handeling niet vanuit een beschreven webinterface kan. Een ontbrekende functie wordt als open punt teruggegeven.
- **Wat je deelt.** Houd het [installatie-invulblad][invulblad] en onbewerkte rapporten bij jezelf. Deel per stap de uitkomst, aantallen, datum en gevraagde hashes. Gebruik voor personen “gebruiker 1”, “gebruiker 2” enzovoort. Houd adressen, domeinen, pool- en datasetnamen, persoonsnamen, mailadressen, sleutels, codes en wachtwoorden buiten het gesprek. Een schermafdruk is optioneel en alleen bruikbaar als al die gegevens onleesbaar zijn.
- **Een checksum vergelijken.** Lees de SHA-256 van het oorspronkelijke archief of rapport af. Laat bij herstel de webassistent of herstelvoorziening de checksum opnieuw bepalen uit de teruggehaalde kopie. Vergelijk alle 64 tekens. Als de UI alleen de oude waarde toont, blijft de inhoudscontrole open.
- **Bewijs per installatiestap.** De verwijzingen naar §2 van I01 t/m I26 helpen je de bewijsrijen te vinden. Volg voor de uitvoering de stappen van dit draaiboek. De regel **Bewijs** luidt voor elke stap “noteer NAS-versie, appimage digest, datum, gemaskeerde output, eventuele screenshot en status in Excel” bij de eigen rij-ID. Bij I03 stap 5 is dat bijvoorbeeld I03-03-05. Vul de regel *Bewijs per I-stap* in de terugmeldtabel voor **elke** uitgevoerde stap afzonderlijk in. Noteer “n.v.t.” met reden bij een stap zonder image. Bij een deels uitgevoerde stap vermeld je wat ontbreekt.
- **Wat er met je terugmelding gebeurt.** De regisseur vergelijkt die met de bron, de release en het onderliggende bewijs. Alleen een volledig uitgevoerde rij zonder afwijking komt vanuit Geblokkeerd in aanmerking voor **Bezig**. Een gedeeltelijke proef, stilte of een simulatie levert geen NAS-bevestiging op. Bij een besluit deel je alleen wat de Hub als status toont. De status **Getest** vraagt een meting of vastgelegd bewijs. Bij 11, 12 en 13 krijgt elk verschil een afzonderlijke beoordeling op behoud van gegevens.

## Een app installeren en terugzetten

1. De eigen release-images zijn openbaar op GHCR onder `ghcr.io/lvos04/<image>`, zonder registerinlog. In de tabel staan per app de **Repository** en de volledige **Tag** met digest. Voor de andere apps staat er “nog geen release in versie 1: wacht”; de bestaande MediaGuard blijft op de huidige versie draaien. Wacht bij zo’n rij, en ook als de release afwijkt van het geteste manifest of de image om een registerinlog vraagt. Het digestdeel na `sha256:` telt 64 hexadecimale tekens.
2. Maak voor een nieuwe app een eigen dataset via **Datasets → Add Dataset**, kies **Dataset Preset → Apps** en **Save**. Kies de dataset via de mapkiezer. Leg de bestaande formulierwaarden, vrije hostpoort, mountrechten en het herstelpunt vast. Beperk de inrichting van rechten tot nieuwe, lege, exclusieve appdatasets. Wijzig nooit eigenaar, rechten of ACL op bestaande gedeelde opslag of beschermde datasets, ook niet via een bovenliggende map.
3. De eerste twee apps vul je in via **Apps → Discover Apps → Custom App**. Voor volgende apps beschrijft de [installatiehandleiding][installatie] **Apps → Toevoegen**. In de gelezen Hub-versie vind je **Apps → Appstore → Installatiewizard bekijken**. De wizard kan een bestaand plan hervatten. Een nieuwe app kiezen uit de catalogus is daar nog niet beschikbaar. Is er een plan, controleer dan in **Preview** de image met digest, poorten, datasets, rechten, limieten, back-up en risico vóór goedkeuring. Zonder bruikbaar plan volg je het gedocumenteerde standaardformulier van de app. Gebruik voor een catalogusapp de trein en de vaste catalogusversie uit het manifest. Op 25 november 2026 heb je de community-trein goedgekeurd voor Authentik, AdGuard Home en Navidrome (risico R2). Voor Navidrome is daarnaast een **ja** bij muziekbesluit D18 nodig. Staat de trein uit, schakel hem voor de goedgekeurde installatie via de webinterface in. Het precieze menu is **ONBEKEND - eerst vaststellen op de NAS**. Wacht met de betreffende app zolang de trein, de webbediening, het geteste manifest of de daarin vastgezette versie ontbreekt. [Catalogus en risico][contract] · [Manifestoverzicht][monitoren]
4. Neem voor een eigen app de **Repository** onder `ghcr.io/lvos04/` uit de tabel over en overschrijf **Tag** met de volledige pin. **Privileged** blijft uit. Voeg geen capabilities toe. De eigen images verlagen zelf de rechten van de dienstprocessen en hun gezondheidstest. Als dat mislukt, wacht dan op een herstelde image. Neem de gebruikersinstelling, netwerk-, opslag- en resourcevelden over uit de bijbehorende formulierhandleiding. Houd blijvende geheimen uit het formulier. Maak de eerste beheerder direct in de app.
    - Voor eigen diensten die Hub-koppeling via omgevingsvariabelen ondersteunen, zoals platformbeheer, home-control-hub en appstore-en-fork, verzorgt het goedgekeurde Hub-plan de eerste koppeling. Bij handmatige installatie is de aanbevolen weg om vóór de eerste start onder **Environment Variables** de drie waarden uit de Hub over te nemen. Gebruik `HUB_URL`, `HUB_KEY_FINGERPRINT` en `HUB_ENROLLMENT_TOKEN`. Het token werkt één keer en vervalt uiterlijk na 60 minuten. Houd het privé. Controleer de vingerafdruk en de bevestiging in de Hub.
    - De tweede weg voor een nog nooit gekoppelde dienst is haar lokale statuspagina. Vul daar het Hub-adres, de eenmalige koppelcode en de vingerafdruk uit de Hub in. Voor de executor geldt de eigen procedure in 03. Jelly Leon gebruikt de adapter uit het serverformulier en laat de omgevingsvariabelen leeg. [TrueNAS, stap 5–6][installatie] · [Jelly Leon, openen en koppelen][jelly]
5. Kies **Install**. Controleer **Running**, de gezondheid en de teruggelezen digest van dezelfde repository. De executor vergelijkt de lokaal opgehaalde digest met het manifest, ook na elke update. Weigert **Tag** het teken `@`, stop en meld dit. Alleen na jouw afzonderlijke besluit over de exacte versietag én een uitvoerbare digestcontrole is die terugvalroute beschikbaar. Ontbreekt de teruglezing of wijkt die af, gebruik de app dan niet en meld het incident. Bij `version_unavailable` wacht je op een getest manifest voor de beschikbare catalogus- of formulierversie.
6. **Terugzetten.** Bewaar ook de gegevens die sinds het herstelpunt zijn bijgekomen. Controleer in **Apps** eerst welke app je hebt geselecteerd.
    - Kies op Emby, een bestaande Jellyfin en MediaGuard nooit **Roll Back** of **Update**. **Roll Back** kan bij een eerder geïnstalleerde catalogusversie ook de bijbehorende ixVolume-snapshot terugzetten. Staat de database daar, dan kun je recentere kijkgeschiedenis of MediaGuard-voortgang verliezen. **Update** kan een draaiende app herstarten. Het venster, de aangeboden opties en het effect op jouw installatie zijn **NIET GEVALIDEERD op de NAS**. Sluit het venster zonder te bevestigen. [TrueNAS, app-acties §4][appacties] · [Contract §2.2][contract]
    - Oefen op een afzonderlijke proefapp met de volledige vorige formulierwaarden en bijpassende gegevens. Controleer bij **Edit** de tag met digest, het schema en de proefopslag. Voor Jelly Leon horen de vorige image en de eigen configuratiesnapshot bij elkaar. De bestaande MediaGuard blijft op de huidige versie draaien. De upgrade en bijbehorende terugzetproef in 05 zijn uitgesteld wegens het ontbreken van een proef-VM. [TrueNAS, handmatig terugzetten][installatie] · [Jelly Leon, updaten en terugdraaien][jelly]
    - Voor datasets noemen de handleidingen **Datasets → Data Protection → Create Snapshot**, **Datasets → Data Protection → Manage Snapshots** en bij Jelly Leon **Datasets → Snapshots**. I02 noemt **Data Protection → Periodic Snapshot Tasks**. Dit zijn bronpaden, **niet op de NAS gezien**. De bediening voor klonen of herstel naar een lege proefdataset is **ONBEKEND - eerst vaststellen op de NAS**. Controleer bron, apart doel en tijdstip vóór bevestigen. [MediaGuard][mg] · [Jelly Leon][jelly] · [Bescherming en bewaring in N-P6-02, punt 3][snapshotbescherming]

| App | Repository | Tag na publicatie | Formulierwaarden |
|---|---|---|---|
| Hub | `ghcr.io/lvos04/ai-server-manager` | `0.1.0@sha256:4accffc49b8d4180a302c974f4acf6e2c0d36b2a4fe458e80741b8ffc94546fa` | [Hub, formulier 1][hub] |
| Executor | `ghcr.io/lvos04/ai-server-manager-executor` | `0.1.1@sha256:eb98c8fab8121f819582325dbd9582256e3dd9c77912b2c8a67c7d5619aee27e` | [Executor, formulier 2][hub] |
| jelly-leon-platform | `ghcr.io/lvos04/jelly-leon-platform` | `0.1.0@sha256:210a3d1a2059e0ff92979f5612e0f0b82ef512afdceeb84b6871e98d1db045ca` | [Platformbeheer][platform] |
| home-control-hub | `ghcr.io/lvos04/home-control-hub` | `0.1.0@sha256:b691683455cb38f7eebceead98544946f9d741288449f85739a5339cd7aa681b` | [Bewaking en koppelingen][hch] |
| appstore-en-fork | `ghcr.io/lvos04/appstore-en-fork` | `0.1.0@sha256:2b3109bd599ec35a4460183eca91f27199c5d62c69fd874f51ea797028cf9faf` | [Appstore][winkel] |
| MediaGuard | `ghcr.io/lvos04/mediaguard-core` | nog geen release in versie 1: wacht | [MediaGuard][mg] |
| Media Source Optimizer | `ghcr.io/lvos04/media-source-optimizer` | nog geen release in versie 1: wacht | [Media Source Optimizer][mso] |
| my_house | `ghcr.io/lvos04/my_house` | nog geen release in versie 1: wacht | [Alles-in-één-image][huis] |
| Zoeken en persoonlijke AI | `ghcr.io/lvos04/zoeken-en-persoonlijke-ai` | nog geen release in versie 1: wacht | [Zoeken][zoeken] |
| Jelly Leon inclusief webclient | `ghcr.io/lvos04/jelly-leon` | nog geen release in versie 1: wacht | [Mediaserver][jelly] |

## N-P6-01 - NAS-basis, invulblad en alleen-lezen-gebruiker

### Voor je begint

Maak een ZFS-snapshot van de bestaande appdata en zoek hem terug. Houd het lege invulblad en het [register met twintig bestaande apps][register] bij de hand. De Hub is hier nog niet nodig. [TrueNAS, stap 0 en 2][installatie]

### Wat je doet

1. Open **System → General**. Noteer je TrueNAS-versie op het invulblad (D01). Open **Apps** en controleer of er een app-pool gekozen is. Alleen als TrueNAS er een vraagt, kies je **Configuration → Choose Pool**. Noteer de pool en datasetpaden privé (D02). Controleer de gezondheid en vrije poolruimte (D06) tegen de ondergrens van 20%. [I01 §2, stap 1][I01]
2. Maak een lijst van actieve apps, versies, bezette poorten en bestaande toegangsroutes. Noteer per app de zichtbare installatiewijze (catalogusapp, standaard Custom App, anders of onbekend) en de werkelijk draaiende versie (D07). Het manifest noemt Jellyfin in de community-catalogus. Controleer bij een aanwezige Jellyfin hoe die daadwerkelijk is geïnstalleerd. Ook voor Emby moet je dit zelf aflezen. Noteer de bereikbaarheid binnen je netwerk (D03) en het afgesproken doel van de bestaande mini-pc (D10). [I01 §2, stap 1, 5 en 6][I01] · [Manifestoverzicht, I06][monitoren] · [Platformcontract, bestaande apps][bestaandeapps]
    - Heeft de bestaande app een formulier, open dan **Apps → kies de app → Edit → Storage**. Kijk alleen en sluit zonder op te slaan. Noteer privé per koppeling het opslagtype (**Host Path** of **ixVolume**) en alle gebruikte datasets, ook onderliggende datasets. Loop bij Emby onder meer configuratie, database, metadata en transcodeopslag langs en bij MediaGuard `/config`, `/work` en `/data`. Noteer “onbekend” voor wat je niet kunt aflezen. Controleer dat beheer alleen via de bestaande privéroute bereikbaar is. [TrueNAS, opslag][installatie] · [Jelly Leon, Edit en Storage][jelly] · [MediaGuard, herstelset][mg]
3. Maak via **Datasets → Add Dataset** twee afzonderlijke appdatasets, één voor de Hub en één voor de executor. Kies bij beide de preset **Apps**. Controleer in de lijst of ze onder de bedoelde pool staan en alleen de nieuwe appdata gaan bevatten. [I01 §2, stap 7][I01]
4. Open **Credentials → Users → Add**. Zet **TrueNAS Access** aan met de rol **Read-Only Admin**. Laat SMB, SSH/Shell uit en kies **Save**. De sleutel maak je in 03 wanneer je hem meteen kunt invoeren. De GPU-meting volgt ook in 03, de basismeting van de hardware in 04. [TrueNAS, stap 4][installatie] · [I01 §2, voorbereiding op stap 4][I01]

### Wat je terugmeldt

| Gegeven | Jouw terugmelding |
|---|---|
| Bewijs per I-stap (1, 5, 6, 7) | |
| TrueNAS-versie, pool gekozen en gezond, vrije poolruimte minstens 20% of eronder | |
| Productnaam, versie en installatiewijze per app (catalogusapp, standaard Custom App, anders of onbekend), afwijkingen t.o.v. het register, draaiende Emby-versie | |
| Per app opslagtype, aantal gebruikte datasets en eventuele onbekende koppelingen, zonder paden of datasetnamen | |
| Twee aparte datasets, gebruiker met alleen leesrechten, privéroute gecontroleerd, afwijkende menunaam | |

### Wat daarna gecontroleerd wordt

De regisseur vergelijkt je versie met 25.04 of 25.10, de apps met het register en de Emby-versie met de repetitie voor 11. Een afwijkende app gaat mee naar 05. Bij een andere Emby-versie is eerst een nieuwe repetitie op de juiste vaste digest nodig.

### Welke rijen daarna van Geblokkeerd af mogen

I01-01-01, I01-01-05, I01-01-06 en I01-01-07. I01-01-02 wacht op 02, I01-01-03 en I01-01-04 op 03 en I01-01-08 op 04. De D-rijen volgen pas na invullen of meten in de Hub.

### Stop als

De versie buiten de ondersteunde reeks valt, de pool ongezond is, je een bestaande dataset zou moeten wijzigen of de webinterface niet volstaat. Laat bestaande apps op hun eigen opslag draaien. Is de nieuwe accountrol verkeerd, herstel die via **Credentials → Users** voordat je een sleutel maakt.

## N-P6-02 - Back-up en herstelproef

### Voor je begint

Doe deel a na 01, vóór je de Hub installeert. Doe deel b zodra 03 werkt. Kies een lege, afzonderlijke herstelplek. Houd bron en proefdoel naast elkaar op het invulblad. Werk met de bestaande OneDrive-back-up. Volg voor de bewaring de beschermingsregels vooraan en in punt 3 hieronder. De bewaarinstructie van I02 dient uitsluitend als achtergrond en bewijsbron. [I02 §2, stap 4, herkomst van de bewijsrij][I02]

### Wat je doet

1. **Deel a.** Leg de bestaande OneDrive-methode en dekking per app vast (D04). Bekijk van één bestand de grootte, datum en minstens twee herstelpunten in de versiehistorie. [I02 §2, stap 1–2][I02]
2. Haal één echte foto en één consistente database-export op uit de back-up. Zet beide op de lege proefplek. Open de foto, controleer inhoud en integriteit van de export en herstel de database op de proefplek. Noteer duur en ouderdom van de herstelde data. [I02 §2, stap 3][I02] · [I15 §2, stap 2][I15]
3. <a id="snapshotbescherming"></a>Leg de lijst uit 01 naast **Datasets**. Maak ZFS-snapshots van de betrokken appdatasets. Neem voor Emby en MediaGuard elke gebruikte opslagplaats en alle onderliggende datasets met gegevens mee. Noteer privé per opslagplaats de snapshotnaam en het tijdstip en zoek elke snapshot terug. Controleer de dekking van elke onderliggende dataset afzonderlijk. De MediaGuard-handleiding noemt **Datasets → Data Protection → Create Snapshot** en **Datasets → Data Protection → Manage Snapshots**. Jelly Leon noemt **Datasets → Snapshots** voor het terugvinden. I02 noemt **Data Protection → Periodic Snapshot Tasks** als vindplaats van periodieke taken. Deze paden zijn **niet op de NAS gezien**. Voor een ixVolume is de menuroute naar een aantoonbaar volledige snapshot **ONBEKEND - eerst vaststellen op de NAS**. [I02 §2, stap 4, bron van de menunaam][I02] · [I01 §2, stap 2][I01] · [MediaGuard, back-up en upgrade][mg] · [Jelly Leon, Problemen][jelly]
    - Houd privé per mediasnapshot de dataset, naam, tijdstip, **Used** (gebruikte ruimte), vrije poolruimte vóór en na, laatste geslaagde stap, vrijgavedatum en herstelafhankelijkheden bij. De gewone termijn is 30 dagen na de laatste geslaagde stap en schuift mee. Markeer de nieuwste snapshot van elke dataset ongeacht de stapstatus, de laatste Emby-snapshot, het exportarchief en alle herstelpunten die nog nodig zijn. Meet zelf zolang de melding uit 04 niet werkt. Geldt de uitzondering onder 20%, volg dan de ruimteregel vooraan. Noteer per verwijdering je vrijgave, de gecontroleerde snapshot en de nieuwe meting. [I02 §2, bewijsrijen bij stap 4 en 7][I02]
    - Controleer ook bestaande periodieke taken en taken die de executor aanvraagt. Een taak mag geen beschermd herstelpunt of nog niet door jou vrijgegeven mediasnapshot wissen, ook als een latere geslaagde stap de vrijgavedatum opschuift. Stel alleen een bewaartermijn in als je dit voor alle betrokken datasets hebt aangetoond. Anders blijft de taak zonder bewaartermijn. Voorkom dat een bestaande onveilige taak verder wist. Als de webinterface geen veilige instelling biedt, gebruik de taak niet en maak de vereiste snapshots zelf. De bediening voor deze bescherming is **ONBEKEND - eerst vaststellen op de NAS**.
    - Zet één appconfiguratie op een afzonderlijke, lege proefdataset terug en open die kopie. Controleer bron, kloondoel en tijdstip en of de bron blijft werken (EX14). De exacte bediening voor deze kloon of dit aparte herstel is **ONBEKEND - eerst vaststellen op de NAS**. [I02 §2, bewijsrijen bij stap 3–4][I02]
4. **Deel b.** Open **Onboarding**, vul D04, D05 en D16 in. Leg bij D05 onder **Bewijs vastleggen** de herstelproef vast. Noteer het aanvaardbare gegevensverlies (RPO), de toegestane hersteltijd (RTO) en je werkelijke meting. Controleer **Wat mag nu? (gates)** en **Backups → Back-upgate**. De toestemming voor een wijziging mag pas verschijnen na bewijs. [I02 §2, stap 3 en 8][I02]
5. Regel via de betreffende app en **Backups** consistente database-exports, een versieerbare externe kopie, onafhankelijke bewaring van de herstelsleutel, een melding bij veroudering en een periodieke herstelproef. Controleer in TrueNAS of de door de executor aangevraagde snapshottaak bestaat en aan de bescherming uit punt 3 voldoet vóór je haar laat werken. Bekijk **Externe back-up**. Een geslaagde upload bewijst alleen de overdracht. [I02 §2, stap 5–8][I02]
6. Herhaal het herstel van foto en database uit OneDrive naar een apart doel (EX13). Voor een snapshotproef toont **Backups → Hersteltests** de knoppen **Nieuwe hersteltest** en **Hersteltest in zandbak starten**. Controleer het kloondoel in de preview en lees de uitkomst voor kloon, database en productie direct af. Een lokale snapshotproef vervangt de OneDrive-proef niet. Ontbreekt de bediening voor een externe herstelstap, meld die stap als open. [I02 §2, stap 3 en 8][I02]

### Wat je terugmeldt

| Gegeven | Jouw terugmelding |
|---|---|
| Bewijs per I-stap, gesplitst naar deel a en deel b | |
| Foto opent, database leest en werkt, afzonderlijk leeg doel, inhoud gelijk, herstelduur en ouderdom | |
| Per app aantal opslagplaatsen uit 01 en aantal met teruggevonden snapshot, ixVolume gedekt of open, configuratie op leeg proefdoel geopend | |
| Per mediasnapshot ruimte tegenover 20%, Used, gewone vrijgavedatum en bescherming. Per verwijdering vrijgave, afhankelijkheden en nameting. Periodieke taak veilig bij verschuivende vrijgave of zonder bewaartermijn | |
| D04, D05, D16, stand van beide gates, snapshottaak zichtbaar, externe herstelproef en telefoonmelding | |

### Wat daarna gecontroleerd wordt

De regisseur vergelijkt de gedateerde proeven met de RPO/RTO, controleert of foto én database van buiten de NAS terugkwamen en of de gate pas daarna openging. Hij vergelijkt per app de inventaris uit 01 met de teruggevonden snapshots. Elke gebruikte opslagplaats van Emby en MediaGuard moet gedekt zijn vóór een onderdeel aan hun gegevens komt.

Voor N-P6-13 is apart bewijs nodig dat de actuele MediaGuard-voortgang, het hersteljournaal en de bijbehorende werkgegevens samen terug te lezen zijn op een geïsoleerd doel. Leg dat bewijs bij punt 3 van 13. De algemene herstelproef van foto, database en appconfiguratie dekt alleen de gegevens die je hier zelf hebt teruggelezen.

### Welke rijen daarna van Geblokkeerd af mogen

Na deel a komen I02-02-01 t/m I02-02-04, I01-01-02 en EX14 in aanmerking. Na deel b volgen I02-02-05 t/m I02-02-08, I15-15-02, B12-001 en EX13. B12-002 vereist een in TrueNAS zichtbare taak van de executor. B12-003 t/m B12-006 en de echte delen van EX11 en EX12 vragen elk hun eigen bewijs. D04, D05 en D16 volgen de Hub. Herstel op andere hardware (B12-007) hoort bij 14.

### Stop als

Een opslagplaats van Emby of MediaGuard onbekend is of je de bijbehorende snapshot niet kunt maken, terugvinden of volledig kunt verifiëren. Dan wacht elk onderdeel dat hun gegevens raakt. Stop ook bij een gevuld hersteldoel, een ontbrekende foto of export, mislukt herstel of een gate zonder bewijs. Kies in **Apps** op Emby, een bestaande Jellyfin en MediaGuard nooit **Roll Back** of **Update**. Kies nooit **Rollback** en wijzig nooit rechten op een Emby-, MediaGuard- of mediadataset of hun bovenliggende datasets. Bij minder dan 20% vrije poolruimte pauzeer je nieuwe MediaGuard-taken en meld je dit. Bewaar de snapshots en het exportarchief. Voor hervatting zijn minstens 20% vrije poolruimte en een bruikbare herstelproef nodig. Bij de Emby-proefstop gelden ook de voorwaarden van N-P6-13, punt 6.

## N-P6-03 - De Hub en de executor installeren, bijwerken en terugzetten

### Voor je begint

Rond 01 en 02 deel a af. Voor Hub, executor en platformbeheer moeten de eigen releasepins beschikbaar zijn. Controleer eerst de releaseproef en publieke beschikbaarheid (I23-23-01). Bewaar de twee afzonderlijke datasets en kies vrije poorten. [I23 §2, stap 1–2][I23] · [TrueNAS, stap 1–5][installatie]

### Wat je doet

1. Open **Apps → Discover Apps → Custom App** voor `ai-server-manager`. Vul bij **Repository** `ghcr.io/lvos04/ai-server-manager` in en bij **Tag** de pin uit de ingevulde releasetabel. Kies TCP-containerpoort **30400**, een vrije hostpoort en de Hub-dataset als **Host Path → /appdata**. Laat opdracht en omgevingsvariabelen leeg, zet **Restart Policy** op **Unless Stopped**, laat **Disable Builtin Healthcheck**, **Host Network**, **Privileged** en **Custom User** uit. Geen extra capabilities of GPU. Kies **Install** en controleer **Running** en **Healthy**. [Hub, formulier 1][hub] · [I23 §2, stap 2–3][I23]
2. Open **Apps → ai-server-manager → Workloads → View Logs**. Lees de eenmalige setupcode privé en voer die direct in bij de Hub-wizard. Maak de beheerder en het noodaccount. Maak in **Credentials → Users → User API Keys → Add** de sleutel van de alleen-lezen-gebruiker. Voer hem direct in bij **Onboarding → TrueNAS koppelen (alleen-lezen)**. Controleer vóór bevestigen de vingerafdruk van het TrueNAS-certificaat en laat de leesverbinding testen. [I01 §2, stap 4][I01] · [I23 §2, stap 3][I23]
3. Maak het tweede formulier voor `ai-server-manager-executor`. Gebruik `ghcr.io/lvos04/ai-server-manager-executor`, dezelfde releaseversie met de **eigen** digest, TCP-containerpoort **30410** en de afzonderlijke executor-dataset op `/appdata`. Neem de overige velden uit formulier 2 over. [Executor, formulier 2][hub] · [I23 §2, stap 5][I23]
    - Maak een eigen groep en kies volgens de handleiding **Credentials → Groups → Privileges → Add**. Selecteer bij **Local Groups** die groep en geef uitsluitend `READONLY_ADMIN`, `APPS_WRITE`, `SNAPSHOT_WRITE` en `DATASET_WRITE`. Laat `POOL_WRITE` uit. Dat is het extra recht dat de handleiding noemt voor het terugzetten van snapshots via de executor. Kies geen **Full Admin**. Maak een aparte gebruiker in die groep en voor die gebruiker een sleutel via **Credentials → Users → User API Keys → Add**. De precieze schermen en werking van deze rollen zijn niet op de NAS gezien. [TrueNAS, stap 5][installatie]
    - Gebruik in de Hub **Onboarding → Executor installeren en koppelen**. Vul op de lokale executorpagina het Hub-adres, de koppelcode en de gecontroleerde vingerafdruk in. De verbinding van de executor met TrueNAS moet `wss://` gebruiken. Controleer het certificaat vóór je uitsluitend op die pagina de schrijfsleutel invoert. TrueNAS trekt een sleutel op een onversleutelde verbinding in. Controleer de koppeling, beide digests en bij elk plan de doelapp en dataset. [TrueNAS, stap 5][installatie]
4. Installeer `jelly-leon-platform` via het goedgekeurde plan of het platformformulier. Gebruik de eigen dataset op `/appdata` en TCP-containerpoort **30440**. Bij handmatige installatie gebruik je bij voorkeur de drie Hub-variabelen uit “Een app installeren en terugzetten”, punt 4. De lokale statuspagina met koppelcode en vingerafdruk is de tweede weg voor een nog nooit gekoppelde app. Controleer de koppeling. Open **Onboarding**. Kies per besluit **Meten via TrueNAS (alleen-lezen)** of **Invullen**. Doe nu D01, D02, D03, D06, D07, D08 en D10. Noteer bij **Wat mag nu? (gates)** welke toestemming bij welke gemeten besluiten hoort. [Platformformulier][platform] · [I01 §2, stap 3–4][I01]
5. Gebruik voor de rechtenproef een intrekbare testsleutel. Controleer dat intrekken tot een onbekende of verbroken testkoppeling leidt. Open een onschuldig proefplan en geef eenmaal akkoord. Controleer in de UI dat hetzelfde akkoord geen tweede uitvoering oplevert. Herstel de testkoppeling via de wizard. Houd de werkende beheer- en terugvaltoegang beschikbaar. [I23 §2, stap 3 en 5][I23]
6. Is er een tweede vrijgegeven versie, oefen dan bijwerken en terugzetten met de vorige formulierwaarden, digest en passende databasekopie. Vergelijk aanmelding, data en gezondheid na beide versies. Zonder tweede versie blijft de rij open. Open op je telefoon ook de hoofdschermen. Noteer onleesbare tekst of onbereikbare knoppen, en welke systeemtaal en lichtomstandigheden je hebt geprobeerd. [I23 §2, stap 7–8][I23]

### Wat je terugmeldt

| Gegeven | Jouw terugmelding |
|---|---|
| Bewijs per I-stap, acceptatie van `@`, release- en teruggelezen digest per app | |
| Beide apps Running en Healthy, alleen-lezen-rol toereikend, schrijfsleutel in Hub geweigerd indien beproefd | |
| Executorprivilege (alleen de toegekende rolnamen), wss en certificaat gecontroleerd, koppelweg platformbeheer | |
| D01 t/m D18 elk met schermstatus, toegestane gates, aantal onderscheiden GPU's | |
| Ingetrokken testkoppeling, eenmalig akkoord, uitkomst van update én terugzetten, behoud van gegevens, telefoon | |

### Wat daarna gecontroleerd wordt

De regisseur vergelijkt elke teruggelezen digest met release en manifest, elke open gate met de bijbehorende besluiten, en de gemelde rechten met hun bestemming. Een ongeteste rechtenproef krijgt geen bewijs.

### Welke rijen daarna van Geblokkeerd af mogen

I23-23-02, I23-23-03, I23-23-05, I23-23-08 en I01-01-04. I01-01-03 alleen bij D08 **Getest**, I23-23-07 alleen na update én terugzetproef. EX15 t/m EX21 en EX47 tellen alleen voor de werkelijk uitgevoerde, toepasselijke proef. I23-23-04 wacht op 04 en I23-23-06 op 05.

Vergelijk voor Hub, beleid en executor ook B01-001 t/m B01-005, B01-007, B01-010, B02-005, B02-006 en B02-009 met hun eigen blokkade. Voor B08-003, B08-004 en B08-006 is de afzonderlijke levenscyclusproef op een onschuldige proefapp nodig. Installatie van de Hub alleen is daarvoor onvoldoende.

### Stop als

De genoemde rollen ontbreken of niet volstaan, het formulier ruimere rechten vraagt, of `wss://` en het certificaat niet zijn bevestigd. Laat de executor dan ongekoppeld en meld de afwijking. Stop ook als het tagveld de digest weigert, de teruglezing afwijkt, een schrijfsleutel in de Hub wordt geaccepteerd, de setupcode buiten de logs verschijnt of een gate zonder bewijs opengaat. Trek een verkeerd gebruikte sleutel in. Gebruik de vorige formulierwaarden en bijpassende data als een update mislukt. Rond hierna 02 deel b af.

## N-P6-04 - Bewaking, meldingen en aanmelden

### Voor je begint

De Hub en executor werken. De release van home-control-hub en de pins voor de bewakingsapps zijn beschikbaar. Voor Authentik heb je werkende HTTPS-toegang, een eigen domeinnaam en een lokaal herstelaccount nodig. Controleer vooraf de rechten, goedkeuring en back-upeis van ieder plan. [Manifesten en verplichte controles na installatie][monitoren]

### Wat je doet

1. Installeer eerst home-control-hub met een eigen dataset op `/appdata` en TCP-containerpoort **30420**. Bij handmatige installatie hebben de drie Hub-variabelen uit het algemene punt 4 de voorkeur. Als tweede weg gebruik je bij eerste koppeling de lokale statuspagina met koppelcode, Hub-adres en vingerafdruk. Controleer de koppeling. Installeer daarna Gotify als standaard Custom App. Wijzig direct het standaardwachtwoord, maak per meldbron een aparte toepassing aan en ontvang een testbericht op je telefoon. Stel prioriteiten in en probeer herstel van de meldconfiguratie op een kopie. [Formulier home-control-hub][hch] · [I13 §2, stap 1–5][I13]
2. Installeer Uptime Kuma op eigen opslag, maak de eerste beheerder en bevestig de voorgestelde monitors met hun verwachte uitkomst en wachttijd. Koppel Gotify rechtstreeks. Stop voor EX22 kort **alleen de Hub-app**, laat de bewaking en Emby draaien, noteer de aankomsttijd van de melding en start de Hub weer. Controleer de herstelmelding, onderdrukking van herhaalde meldingen en herstel van de monitorlijst. [I08 §2, stap 1–6][I08]
3. Installeer Beszel-hub en Beszel-agent met hun afzonderlijke manifesten. Maak direct het eerste account en koppel de agent met de publieke hubsleutel. Noteer welke metingen aanwezig zijn voor CPU, RAM inclusief ARC, schijven, pool, netwerk en GPU. Stel de ruimtemelding in op **20% vrije poolruimte** en controleer met een proefmelding of die je telefoon bereikt. Bij minder dan 20% pauzeer je nieuwe MediaGuard-taken en controleer je dat ze wachten. Gebruik voor elke mediasnapshot de termijn uit 02 van 30 dagen na de laatste geslaagde stap, langer zolang nodig voor herstel. De bediening per versie is **ONBEKEND - eerst vaststellen op de NAS**. Vergelijk de tijdstippen met TrueNAS en controleer de historie op een aparte herstelkopie. Bewaar dit als nulmeting voor 14. [I07 §2, stap 1–6][I07] · [I01 §2, stap 8][I01] · [Bescherming en bewaring in N-P6-02, punt 3][snapshotbescherming]
4. Meld je vóór de aanmeldproef via de gewone route aan op een bestaande Emby-client en speel een titel af. Noteer de uitkomst. Laat de Emby-aanmeldroute, accounts en clients ongemoeid. Leg privé vast welke proefroutes je naast de Hub aanwijst. Is er geen extra proefroute aangewezen, test dan alleen de Hub. [I09 §2, stap 4–6][I09]
    - Installeer Authentik via het TrueNAS-catalogusformulier met de goedgekeurde **community-trein** (R2), de vaste catalogusversie en de vier datasets uit het geteste manifest. Het installatiedeel van I09 dient uitsluitend als achtergrond en bewijsbron. Het menu voor de trein is **ONBEKEND - eerst vaststellen op de NAS**. Wacht met installeren als de bediening, de vastgezette versie of de trein ontbreekt. Controleer de database, MFA en het lokale herstelaccount. Test OIDC, rollen en sessie-intrekking uitsluitend op de Hub en de vooraf aangewezen proefroutes. Trek daar een testsessie in en controleer dat die toegang vervalt. Oefen upgrade en herstel op een aparte kopie. Meld je na de proef via de gewone route aan op dezelfde Emby-client en speel dezelfde titel af. Noteer beide uitkomsten bij D17. [Catalogusformulier en manifest][monitoren] · [I09 §2, bewijsrijen][I09] · [I23 §2, stap 4][I23]
5. **Node-RED wacht.** Het huidige besluit laat de editor dicht, ook voor lezen. De officiële image heeft langs de vastgelegde route nog geen beheerder of dienstaccount. Sla de hele I10-proef nu over. Pas na een nieuw besluit en een werkende, geteste voorziening maakt de beheerder zijn account in de app en geeft hij het dienstaccount éénmaal op bij home-control-hub. Het formulier vraagt geen accountgegevens. Controleer dan in een privévenster dat je alleen de aanmelding ziet. De isolatiecontrole `anoniem_geweigerd` moet op alle drie de controles voor flows, nodes en instellingen 401 melden. Het bedieningsscherm voor deze meting is **ONBEKEND - eerst vaststellen op de NAS**. Alleen na beide controles mag je als beheerder proefflows importeren, de weigering van een ongeoorloofde proefactie en één verwerking van vijf gelijke gebeurtenissen controleren, een flowversie herstellen en de bewaking testen. [I10 §2, stap 1–6][I10] · [Node-RED en de accountvoorziening][nodered]

### Wat je terugmeldt

| Gegeven | Jouw terugmelding |
|---|---|
| Bewijs per I-stap, installatieweg en overeenkomst tussen plan, digest en draaiende app | |
| Bewaakte meetpunten en onbekende waarden, bericht buiten de Hub ontvangen na … minuten, herstelmelding | |
| Proefmelding voor 20% vrije poolruimte ontvangen, bewaring per mediasnapshot tot 30 dagen na de laatste geslaagde stap en langer zolang nodig voor herstel, koppelweg home-control-hub en beschikbaarheid van de goedgekeurde community-trein en vaste Authentik-versie | |
| MFA en herstelaccount, OIDC, rollen en ingetrokken testsessie op Hub en aangewezen proefroutes, upgrade/herstel, D17. Gewone Emby-aanmelding én afspelen op dezelfde client vóór en na | |
| Node-RED overgeslagen of accountaanmaak, formulier zonder geheim, anonieme weergave, drie weigeringen, flowproeven | |

### Wat daarna gecontroleerd wordt

De regisseur vergelijkt de digests en back-upeisen met de manifesten en volgt de meldweg van Uptime Kuma naar Gotify en de telefoon. Voor Node-RED zijn zowel de anonieme weergave als de onafhankelijke isolatiecontrole nodig. Een onbekende isolatiestatus blijft open.

### Welke rijen daarna van Geblokkeerd af mogen

De uitgevoerde I07-, I08-, I09- en I13-stappen, I01-01-08 en EX22. I23-23-04 en B13-002 t/m B13-005 vragen de aanmeld-, upgrade- en herstelproeven. D17 volgt de Hub. B09-001 t/m B09-006 en B11-001 t/m B11-005 vereisen per rij echt bewijs. B09-006 vraagt een goedgekeurd voorstel dat de executor uitvoerde. I10, B11-001, EX45 en EX46 wachten op de Node-RED-voorwaarden. EX23 blijft open zolang NAS-uitval Emby zou onderbreken.

Voor B13-001, B01-006 en B01-008 telt alleen het hier beproefde deel van lokaal aanmelden, bewaken of melden.

### Stop als

De draaiende instellingen afwijken van het plan, de melding alleen via de Hub werkt of Authentik de enige toegang wordt. Wacht met de aanmeldproef als de Emby-voormeting faalt of de proef een gewone Emby-route, account of client zou wijzigen. Faalt de nameting, breek de proef af, draai de wijziging op de proefroute terug en controleer de gewone Emby-aanmelding en het afspelen opnieuw. Houd D17 open bij een afwijking. Gebruik voor de Hub het geteste herstelaccount. Start de Hub weer na de meldproef. Stop alleen de betrokken proefapp bij zichtbare flows zonder aanmelding of een uitgevoerde verboden actie. Vraagt het Node-RED-formulier om een geheim, laat het leeg en sluit het formulier.

## N-P6-05 - Bestaande apps, MediaGuard en Media Source Optimizer

### Voor je begint

**Besluit van 25 november 2026. Er is geen proef-VM. De MediaGuard-upgrade wacht. MediaGuard blijft op de huidige versie werken, met Emby.** Na heel 02 en na 03 kun je met de vrijgegeven appstore de inventaris uit punt 1 maken. Je kunt versies, koppelingen, wachtrijen, voortgang en hersteljournaal aflezen. Ook de bestaande appschermen kun je bekijken. Noteer wat je daadwerkelijk ziet. Laat de koppelingen en de draaiende apps ongemoeid.

### Wat je doet

1. Installeer appstore-en-fork op een eigen dataset (`/appdata`, TCP-containerpoort **30430**). Laat de Hub de bestaande apps alleen lezen. Vergelijk alle twintig posities met het register. Noteer per app de versie, installatiewijze uit 01, eigenaar en je besluit over later onderhoud. Kies tijdens deze inventaris geen onderhoudsactie. Gebruik op Emby, een bestaande Jellyfin en MediaGuard nooit de app-acties **Roll Back** of **Update**. Plex, Emby, JellyPlex Watched en een bestaande Jellyfin blijven hierbij draaien. Bekijk voor Readarr en FlareSolverr de gebruikshistorie en afhankelijkheden, en voor de eigen losse apps aanmelding en herstel. [Appstoreformulier][winkel] · [I26 §2, stap 1, 3–5][I26] · [Appregister][register]
    - Noteer de huidige versies van MediaGuard en Media Source Optimizer, de zichtbare koppeling met Emby, de open en afgeronde taken en welke herstelpunten je uit 02 terugvindt. Leg privé vast welke werkgegevens en herstelbare originelen het journaal aanwijst. Noteer onbekende waarden als onbekend. Dit is de uitgangsstand. Vóór de proefstop in 13 moet je de dan actuele taken en het journaal ook uit één samenhangende herstelset kunnen teruglezen. [I03 §2, stap 1–3][I03] · [I04 §2, stap 1][I04] · [MediaGuard, back-up en upgrade][mg]

**Punten 2–9 zijn de werkwijze voor later. Sla ze deze ronde over.** Zonder afgeschermde proef-VM vervallen de nette stop van MediaGuard voor de upgrade, de proefkopieën, de upgrade en alle wijzigende appproeven in 6–9. Dit omvat ook de testdownload en de VPN-wijziging. Ga na de inventaris naar **Wat je terugmeldt**.

> Voor een latere ronde heb je een bruikbare, afgeschermde proef-VM nodig, upgradebewijs voor precies de gekozen versies, je eigen toegestane testbronnen en de volledige herstelset. Bewaar de vorige installatie en alle formulierwaarden. De actuele voortgang moet ook bij een nette stop van uitsluitend MediaGuard in te zien zijn.
>
> 2. **Bereid de proef voor terwijl de bestaande installatie draait.** Start de proefkopie nooit in de echte NAS-appomgeving of op het thuisnetwerk. Volg deze vier voorwaarden voor de eerste start. [MediaGuard, Afgeschermde proefkopie][mg] · [I03 §2, stap 1–4][I03]
>     1. Gebruik een **aparte TrueNAS-proef-VM**. Vóór de proef moeten zowel de formuliercatalogus als de oude en nieuwe image op de verwachte digest lokaal beschikbaar zijn. De webroute om de VM te maken en beide images en de catalogus er zonder uplink in te krijgen is **ONBEKEND - eerst vaststellen op de NAS**. Deelt de VM hardware met Emby, controleer dan vooraf vrije CPU en RAM en tijdens de proef het afspelen van een bestaande titel op Emby. Bij te weinig ruimte voor Emby sla je de proef over.
>     2. Controleer **vóór import van enige datasetkopie én vóór de eerste start** dat de VM uitsluitend een **intern virtueel netwerk zonder uplink** heeft. Sluit router, productienetwerk, productie-DNS en internet uit. Gebruik geen bridge of NAT naar buiten. Controleer de netwerkadapters in de hypervisor. Controleer met een lokale testdienst aan de andere kant van de scheiding dat die vanaf haar eigen testnet werkt en vanuit de VM onbereikbaar is. Bedien de VM vanuit een proefbrowser op het interne netwerk. Koppel uitsluitend proefdatasets. De webroute om een datasetkopie uit de herstelset van punt 3 in te voeren zonder netwerkpad naar de NAS is **ONBEKEND - eerst vaststellen op de NAS**. Open voor de overdracht ook geen tijdelijke uplink en koppel geen productieopslag.
>     3. Kies in het formulier van de proefapp **Pull Policy → Never pull an image**. Controleer dat oude en nieuwe digest lokaal beschikbaar zijn. Een ontbrekende image of catalogus is een stopreden.
>     4. Controleer vooraf of de webinterface een **gestopte kopie** kan inrichten. Na import moeten **alle** koppelingen van MediaGuard, de forks en de encoder vóór de eerste start uitstaan of naar lokale testdiensten met testgegevens wijzen. Loop ook mediaservers (inclusief Emby), Sonarr/Radarr, Seerr, indexers, downloadclients, meldingen en webhooks na. Controleer elke ingestelde bestemming. Houd de afscherming de hele proef in stand en herhaal de controle na herstel van een oudere kopie, vóór die weer start. De handleiding beschrijft het aanpassen in een al gestarte, geïsoleerde proefapp. Dit draaiboek vereist het vooraf. De webroute daarvoor is **ONBEKEND - eerst vaststellen op de NAS**.
>
>     **Stop hier bij een ontbrekende voorwaarde.** Zolang je de offline overdracht of de inrichting vóór de eerste start niet kunt aantonen, sla je de proefkopie en de MediaGuard-upgrade deze ronde over. Laat de bestaande MediaGuard draaien en noteer de reden. Zonder bruikbare proef-VM kun je in 6–9 alleen de inventaris en alleen-lezencontroles doen. Ook op een toekomstige bruikbare proef-VM vraagt elke wijzigende proef in 6–9 een eigen geverifieerd herstel volgens punt 6.
>
> 3. **Leg de uitgangsstand en herstelset vast.** Controleer vóór enige wijziging op Emby met een testprofiel dat een bestaande titel via het gebruikelijke pad speelt. Gebruik dit profiel ook voor de afspeelcontrole achteraf. Bewaar de draaiende digest, mounts en formulierwaarden. Lees in MediaGuard open en afgeronde overdrachten, wachtrijen, hersteljournaal en herstelbare originelen af. [I03 §2, stap 1–3][I03] · [MediaGuard, back-up en upgrade][mg]
>     - Gebruik voor kijkgegevens een ondersteunde export als die beschikbaar is. Vergelijk per gebruiker gezien-status, hervatpunten, favorieten, beoordelingen, spoorkeuzes en rechten, en de lijst gebruikers. Een volledige telling zonder export via de webinterface is **ONBEKEND - eerst vaststellen op de NAS**. Als vervangende meting bekijk je in de Emby-interface van elke gebruiker vijf vaste titels. Noteer privé per titel gezien-status, hervatpositie en favoriet. Kijk ná de upgrade in hetzelfde profiel naar dezelfde vijf, zonder hun status te wijzigen. Meld alleen het gebruikersnummer, de meetmethode en de uitkomst. Overige niet meetbare gegevens blijven open. Een steekproef levert geen bewijs voor een volledige telling of voor de overname in 11. [MediaGuard, kijkgegevens vóór en na][mg] · [Overname, voorwaarden voor de assistent][overname]
>     - Maak vóór de eerste wijziging per schrijfbaar gekoppelde dienst een eigen appdatasnapshot of back-up in die app. Noteer privé naam en tijdstip en leg per dienst de versie, vóór-waarden en herstelhandeling vast. Verifieer het terugzetten per dienst op een afgeschermde kopie in de proef-VM van punt 2. Ontbreekt een herstelpunt of lukt het herstel niet, dan wacht de wijziging. [MediaGuard, back-up en upgrade][mg] · [I02 §2, bewijsrijen bij stap 4–5][I02]
>     - Pauzeer nieuwe MediaGuard-taken, laat lopende encodes, imports en hersteltransacties afronden en stem de overige schrijvers af. Volg de nette stop van uitsluitend MediaGuard en verifieer de afsluiting. Maak één samenhangende herstelset van `/config`, `/work` en `/data`, de database-export, forks, quarantaine, journaal en alle gebruikte onderliggende datasets. Noteer voor iedere mediasnapshot de vrije poolruimte tegenover 20%, **Used** en de vroegste vrijgavedatum volgens 02. Bewaar hem tot 30 dagen na de laatste geslaagde stap en langer zolang nodig voor herstel. Houd eigenaar, rechten en ACL van Emby, MediaGuard en de media intact. Breng de bestaande MediaGuard na het veiligstellen van de set met de bestaande versie en gegevens weer in bedrijf. Controleer de tellers. [MediaGuard, back-up en upgrade][mg] · [I03 §2, stap 1–3][I03]
> 4. **Oefen de upgrade én de terugweg op de afgeschermde kopie.** Controleer de isolatie vóór import van de kopie uit punt 3. Controleer na import alle vier voorwaarden uit punt 2, terwijl de proefapp nog uit staat. Pas dan start je de kopie. Vergelijk op de vorige image de voortgang en het journaal met het herstelpunt. Controleer per herstelbaar origineel het quarantainepad, de grootte en de SHA-256. Ontbreekt een geregistreerde checksum, bepaal die vóór de migratie en vergelijk met de snapshotkopie. Oefen gericht herstel alleen op de kopie. Kies via **Edit** op de proefapp de vrijgegeven image en behoud de proefmounts en **Never pull an image**. Controleer digest, aanmelding, gezondheid van core, web, encoder en forks, de koppelingen met testdiensten en alle tellers. Oefen ook terugkeer met de vorige image en bijpassende gegevens op afzonderlijke proefopslag. [I03 §2, stap 3–4][I03] · [MediaGuard, afgeschermde proefkopie][mg]
> 5. **Beslis pas daarna over de bestaande MediaGuard.** Kies op deze app nooit **Roll Back** of **Update**. Kies ook op de dataset voor de eigen `/config` van MediaGuard nooit **Rollback**. De paragraaf *Terugzetten na een mislukte upgrade* dient hier alleen als achtergrond. **Volg stap 2 (Rollback) van die paragraaf niet.** [MediaGuard, terugzetten na een mislukte upgrade][mgterug] · [I03 §2, stap 4][I03]
>     - Begin alleen als je zowel de upgrade als de terugweg op de kopie hebt aangetoond en de bestaande standaard Custom App dezelfde veilige webroute biedt. Voor de terugweg heb je de vorige digest, vorige formulierwaarden en een aparte passende gegevenskopie nodig. Vereist een van beide routes **Roll Back**, **Update**, het terugdraaien van beschermde opslag of een rechtenwijziging, of is behoud van de voortgang onzeker, laat de bestaande installatie dan op de huidige versie draaien.
>     - Maak direct vóór een toegestane upgrade opnieuw de vóórmeting en een verse stabiele herstelset volgens punt 3. Controleer in **Edit** de vrijgegeven image, bestaande mounts, poorten en koppelingen. Ga alleen door langs de vooraf beproefde webroute. Controleer vóór hervatting digest, gezondheid, aanmelding, voortgang, journaal en de kijkgegevens volgens dezelfde meetmethode. Speel dezelfde bestaande Emby-titel via hetzelfde pad af en controleer de MediaGuard-kijkpauze. Bij een afwijking geldt de stopregel hieronder. [I03 §2, stap 3–5][I03] · [MediaGuard, back-up en upgrade][mg]
> 6. **Vóór elke wijzigende appproef in punten 6–9** maak je per betrokken app én elke dienst waarnaar die proef kan schrijven een eigen appdatasnapshot of consistente back-up in de app. Noteer naam en tijdstip privé, versie, vóór-waarden en de herstelhandeling. Verifieer het herstel per dienst op een afgeschermde kopie in de proef-VM van punt 2. Ontbreekt die VM, een herstelpunt of een geslaagde herstelproef, sla de wijzigende proef over. Dit geldt ook voor de eerste testdownload en een wijziging van de VPN-binding. [MediaGuard, herstelpunten per dienst][mg] · [I02 §2, bewijsrijen bij stap 4–5][I02]
>     - Koppel Seerr, Prowlarr en de downloadclients via de app. Controleer de AV1-noodstop, behoud van het origineel, telefoonmeldingen en de alleen-lezenstatus in de Hub. Laat eerst in de schaduw meelezen. Doe daarna met je toestemming één download uit een toegestane testbron. Beoordeel na **24 tot 48 uur** de uitkomst en geef zelf akkoord of weigering. [I03 §2, stap 5–8][I03] · [I23 §2, stap 6][I23]
> 7. **Media Source Optimizer (MSO).** Noteer de huidige en beoogde versie. Controleer de eigen dataset op `/appdata`, de vaste image en TCP-containerpoort **38081**. Beproef de nieuwe versie en het herstel uitsluitend op een **afgeschermde MSO-kopie volgens alle vier voorwaarden van punt 2**. Gebruik in de proef-VM beide lokale MSO-images op digest, **Never pull an image** en uitsluitend proefopslag. Met een oude koppeling kan de kopie een nieuwe zoekopdracht bij de echte MediaGuard aanvragen. Zet vóór de eerste start alle koppelingen uit of vervang ze door lokale testdiensten met testgegevens en testsleutels. Controleer MediaGuard, Prowlarr, SABnzbd en qBittorrent elk afzonderlijk. De kopie mag geen productiedienst of mediadataset van het huishouden kunnen bereiken. Herhaal deze controle na elk herstel, vóór de kopie weer start. [MSO-formulier][mso] · [I04 §2, stap 1–5][I04]
>     - Controleer op de kopie het databaseherstel zonder dubbele taken. Beproef met de aangesloten testdiensten de categoriegrenzen, een providerstoring, een privé-torrent en een herhaalde zoekopdracht. Controleer behoud van bestanden, de categorie en het uitblijven van een zoeklus. Leg vast welke app eigenaar blijft van elke wijziging. De latere acceptatie met de bestaande diensten vraagt apart jouw toestemming en de herstelpunten uit punt 6. Houd dat deel open zolang alleen de proefkopie is getest. [I04 §2, stap 3–8][I04]
> 8. Loop de overige koppelingen één voor één door. Bij Immich controleer je behoud van foto's, albums, rechten en toegestane metadata. Bij Prowlarr toets je eigenaarschap van tags, lusbewaking en herstel. Bij SABnzbd controleer je categorieën, padtoewijzing, uitval van één provider en behoud van de serverlijst. Bij qBittorrent controleer je VPN-binding en behoud van seedgegevens. Gebruik uitsluitend de eigen back-up en de goedgekeurde versie per app. [I15 §2, stap 1 en 3–6][I15] · [I16 §2, stap 1–6][I16] · [I17 §2, stap 1–6][I17] · [I18 §2, stap 1–6][I18]
> 9. Controleer bij Seerr de vier gekoppelde diensten, anime-routering, status van een proefaanvraag en herstel. Controleer bij Bazarr Nederlandse ondertitels in de speler, behoud na vervanging en afwezigheid van dubbele downloads. Laat Bazarr actief tot gelijkwaardige werking en een apart besluit. Leg vast welke echte koppelingen de Hub kon lezen. Je kunt de drie webinterfaces en MediaGuard op Android ook op telefoon, met schermlezer, fel licht en Engelse systeemtaal beproeven. [I19 §2, stap 1–6][I19] · [I20 §2, stap 1–5][I20] · [I23 §2, stap 6][I23]

### Wat je terugmeldt

| Gegeven | Jouw terugmelding |
|---|---|
| Bewijs per I-stap, per app versie, huidige installatieweg en besluit, afwijkingen van het register | |
| Huidige versies, Emby-koppeling, MediaGuard-tellers en hersteljournaal alleen afgelezen | |
| Upgrade en alle wijzigende proeven uit 6–9 | Uitgesteld wegens ontbreken van een proef-VM. |
| Bij een latere VM-proef beschikbaarheid van de offline catalogus en beide images, isolatie vóór import, overdracht zonder uplink, onbereikbare testdienst, Never pull en alle koppelingen vóór start en bij herstel | |
| Bij die latere proef de voortgang vóór / op kopie / na, journaal en herstelset, terugweg op kopie, kijkgegevens per gebruiker (export of vijf titels), verschillen, ontbrekende metingen en dezelfde Emby-titel vóór/na | |
| Per mediasnapshot vrije poolruimte tegenover 20%, Used, gewone vrijgavedatum en bescherming volgens 02. Bij een latere proef ook CPU, RAM en Emby-afspelen | |
| Bij een latere proef de schaduwfase, ene testdownload, uren proefgebruik, jouw akkoord of weigering | |
| Bij een latere proef de MSO-kopie vóór start en na herstel afgeschermd, per koppeling uit of lokale testdienst, uitkomst op de kopie en afzonderlijk resultaat met bestaande diensten of reden van overslaan | |
| Waarnemingen bij het bekijken van bestaande Hub-koppelingen, telefoon of schermlezer. Bij een latere proef ook downloadclients, noodstop en behoud van originelen | |

Vermeld voor elke uitgestelde proef ‘overgeslagen, geen proef-VM’. Vul meetwaarden pas in wanneer de proef werkelijk is uitgevoerd. Noteer de namen van herstelpunten alleen privé.

| App | Versie, type herstelpunt en tijdstip vóór de proef | Herstel op afgeschermde kopie, vóór/na of reden van overslaan |
|---|---|---|
| Seerr | | |
| Prowlarr | | |
| SABnzbd | | |
| qBittorrent | | |
| Immich | | |
| Bazarr | | |
| Media Source Optimizer | | |
| Overige schrijfbaar gekoppelde dienst (één regel per dienst en proef) | | |

### Wat daarna gecontroleerd wordt

Deze ronde vergelijkt de regisseur de inventaris en afgelezen waarden met de terugmelding per app. Alle wijzigende proeven en het bewijs voor de upgrade blijven open. Bij een latere proef vergelijkt hij de VM-isolatie, versies en herstelpunten per dienst, de MediaGuard-tellers met het journaal en de kijkgegevens per gebruiker met dezelfde vóórmeting. Elk verschil vraagt een afzonderlijke beoordeling. Een steekproef telt uitsluitend voor de gecontroleerde titels en velden.

### Welke rijen daarna van Geblokkeerd af mogen

APP-01 t/m APP-20 per geïnventariseerde app mét besluit, behalve APP-02. Voor APP-17 en APP-20 blijven aanvullende proeven in 09 respectievelijk 06 open. B08-002, I26-26-01, I26-26-03 t/m I26-26-05, I23-23-06 en de uitgevoerde I03-, I04- en I15- t/m I20-stappen volgen hun bewijs. B04-010 en B05-007 vragen jouw akkoord. Voor B05-007 is ook de afzonderlijke proef met de bestaande diensten nodig. EX01 t/m EX06, EX09, EX37 en EX39 t/m EX42 tellen alleen voor hun eigen gecontroleerde proef. De MediaGuard-acceptatie, de uitgestelde upgrade en de wijzigende appproeven in 6–9 blijven Geblokkeerd. Alleen het werkelijk uitgevoerde inventaris- of leesdeel kan bewijs krijgen.

Bij de overige NAS-delen van B04-001 t/m B04-010, B05-001 t/m B05-010 en B08-001 vergelijkt de regisseur de appversie, koppeling en proef met de betreffende rij. De pakketcontrole voor MediaGuard blijft open tot de desbetreffende release onder `ghcr.io/lvos04/` openbaar op de opgegeven digest te verkrijgen is.

### Stop als

Een voorwaarde uit punt 2 ontbreekt, een proefbestemming buiten de VM bereikbaar is of Emby door de belasting hapert. Sla de proefkopie dan over of breek de lopende proef af. Deze ronde is er geen proef-VM. Daarom wachten de MediaGuard-upgrade en alle wijzigende appproeven in 6–9. Inventaris en alleen-lezencontroles kunnen doorgaan. Kies in **Apps** op Emby, een bestaande Jellyfin en MediaGuard nooit **Roll Back** of **Update**. Stop ook bij een onvolledige snapshot of dienstback-up, ontbrekend upgradebewijs, onduidelijke terugweg, gewijzigde kijkgegevens, een afwijkende teller of ontoegankelijke voortgang. Bij minder dan 20% vrije poolruimte pauzeer je nieuwe MediaGuard-taken en meld je dit. Stop bij een vereiste wijziging van de bestaande installatieweg, eigenaar, rechten of ACL. [MediaGuard, afgeschermde proefkopie en back-up][mg]

Bij een afwijking na een latere upgrade pauzeer je nieuwe taken en bewaar je de actuele stand van appdata, werk, media en gekoppelde diensten apart. Gebruik uitsluitend de vooraf beproefde terugweg met vorige image en bijpassende kopie. Vergelijk journaal en originelen op de aparte kopie en bewaar ook nieuwere bestanden. **Nooit Rollback of een rechtenwijziging op Emby-, MediaGuard- of mediadatasets, ook niet op een bovenliggende dataset.** Hervat pas wanneer alle voortgang beschikbaar is, Emby dezelfde titel afspeelt en de kijkgegevens kloppen. Lees de paragraaf *Terugzetten na een mislukte upgrade* alleen als achtergrond. **Volg stap 2 (Rollback) van die paragraaf niet.** [MediaGuard, terugzetten na een mislukte upgrade][mgterug]

Ontbreekt bij een latere proef met MSO één van de vier voorwaarden uit punt 2 of kan de kopie nog een echte dienst of mediadataset bereiken, start de kopie dan niet. Breek een lopende proef bij verlies van de afscherming direct af. Pauzeer bij een MSO-afwijking de automatisering en bewaar de actuele gegevens apart. Oefen herstel van de volledige MSO-appdata met bijbehorende kluis en vorige image op digest uitsluitend op de afgeschermde kopie. Controleer na elk herstel de bestemmingen en sleutels vóór de volgende start. Op de kopie hervat je uitsluitend lokale testkoppelingen. Voor een afwijking op de bestaande MSO gebruik je de bij punt 6 beproefde terugweg. Controleer op die installatie taken en audit. Trek sleutels die sinds het herstelpunt zijn ingetrokken opnieuw in vóór je de koppelingen hervat. [MSO, terugdraaien via TrueNAS][msoherstel]

## N-P6-06 - my_house en echte apparaten

### Voor je begint

03 werkt. Wacht op een publiek beschikbare alles-in-één-image met eigen vaste tag en digest. Losse web- en API-images voldoen hier niet. Houd het herstelpunt, de uitgeschakelde automatiseringen en de apparaten die je zelf kunt waarnemen bij de hand. [Formulier voor my_house][huis]

### Wat je doet

1. Maak een eigen, lege dataset. De oude I05-stappen 2 en 3 “Eerste YAML zonder Zigbee/tunnel” en “TrueNAS Install via YAML” worden **NIET gevolgd**. Onder de bijgewerkte titels van I05 staan nog oude uitvoerinstructies. Gebruik voor stap 1–3 uitsluitend de formulierhandleiding van my_house. Kies na de release in dat formulier de alles-in-één-image, `/appdata`, TCP-containerpoort **8080** en een vrije hostpoort (voorstel **8088**). Laat Zigbee aanvankelijk uit. [I05 §2, stap 1–3 (rijen en bewijs)][I05] · [my_house, naam, image en container][huis]
2. Neem voor de eerste start het startprogramma en de drie afzonderlijke argumenten uit het formulierdocument over. Kies eerst **Restart Policy → No**. Lees via **Workloads → View Logs** de door deze image opgegeven startmodule. Gebruik **Edit**, neem die naam als laatste argument over en kies **Unless Stopped**. Controleer digest en gezondheid. Maak direct de eerste beheerder en woning aan, open **Systeem → Installatiewizard** en stel onder **Systeem → Back-ups en bewaren** de versleutelde back-up in. [my_house, opslaan en controleren][huis] · [I05 §2, vervangende uitvoering van stap 2–3][I05]
3. Vul D12 (Gree), D13 (Zigbee) en D14 (meters) in de Hub in. Koppel Hue en bedien één lamp terwijl je erbij staat. Koppel de HomeWizard-meters, wijs de rollen toe en vergelijk de uitlezing met de meter. De boiler heeft uitsluitend een meetfunctie. Controleer bij my_house, Hub en assistent met de beschikbare weigeringsproef dat een schakelverzoek wordt afgewezen zonder het naar het apparaat te sturen (EX27). [I05 §2, stap 4–5][I05]
4. Lees Gree eerst uit. Bedien alleen één als getest aangemerkte unit, terwijl je in dezelfde kamer bent. Vergelijk de fysieke stand met het scherm. Zet tijdens een testschema de unit met de afstandsbediening uit. De unit hoort uit te blijven tot je zelf hervat (EX26). Bij een niet-ondersteunde unit verwacht je een melding van die beperking (EX30). [I05 §2, stap 6][I05]
5. Alleen bij een positief D13-besluit kies je in het formulier **Devices** en de eigen USB-stick, met `/dev/serial/by-id/<STICK>` naar `/dev/zigbee`. Controleer of Zigbee2MQTT de stick ziet. Koppel één apparaat en controleer ter plekke de reactie. Een groene algemene gezondheidstest is onvoldoende bewijs voor de stick. [I05 §2, stap 7][I05] · [my_house, Zigbee-stick][huis]
6. Test de Android-app en de 24-uursgrafiek na een volle dag. Probeer herstel naar een aparte, schrijfbare kloon. Gebruik bij terugval de procedure voor de Custom App op de kloon met beide workers gestopt en apparaten los. Controleer vóór starten het terugval-ID, het alleen-lezen startbestand en de bijpassende oude versie en startmodule. [I05 §2, stap 8][I05] · [Offline terugvalkopie][huisherstel]

### Wat je terugmeldt

| Gegeven | Jouw terugmelding |
|---|---|
| Bewijs per I05-stap, standaard Custom App geïnstalleerd, digest en startmodule gecontroleerd | |
| D12, D13 en D14, per soort het aantal apparaten, drie boilerweigeringen, fysieke Gree-stand en scherm | |
| USB-doorgifte, Zigbee2MQTT, reactie proefapparaat, grafiek na 24 uur, metervergelijking en herstelkopie | |

### Wat daarna gecontroleerd wordt

De regisseur vergelijkt type/firmware met de ondersteunde apparatuur, kijkt of Gree-bediening pas na D12 beschikbaar was en controleert of de boiler langs alle drie de wegen alleen meetbaar bleef.

### Welke rijen daarna van Geblokkeerd af mogen

De uitgevoerde I05-stappen, EX26 en EX30 en de volledig aangetoonde apparaatdelen van B06 en B14. Voor I05-05-02 en I05-05-03 geldt als bewijs “geïnstalleerd als standaard Custom App”. B06-009 vraagt ook alle apparaatsoorten en een NAS-herstart. Die herstart blijft open zolang Emby hierdoor zou worden onderbroken. B06-008 hoort bij 14. Bij D13 **nee** noteer je voor Zigbee “niet van toepassing volgens D13”.

Voor B01-011, B14-001, B14-002, B14-004 en B14-005 telt de bijbehorende waarneming op het apparaat. Voor EX24, EX25 en EX27 t/m EX29 telt alleen de herhaalde proef die je daadwerkelijk hebt gedaan.

### Stop als

De image of terugvalkopie ontbreekt, bediening onvoorspelbaar is, een ketelverzoek kan worden uitgevoerd of de UI een andere toestand dan het apparaat meldt. Schakel de nieuwe automatisering uit, houd de fysieke bediening beschikbaar en sluit het betrokken testapparaat uit tot de oorzaak bekend is.

## N-P6-07 - Netwerk en DNS

### Voor je begint

03 en 04 werken, inclusief een melding buiten de Hub om. NetAlertX gebruikt een standaard Custom App. AdGuard Home is een **catalogusapp uit de community-trein** met een vaste versie uit het manifest. Je hebt de community-trein voor AdGuard Home goedgekeurd (R2). Het menu is **ONBEKEND - eerst vaststellen op de NAS**. Wacht bij een ontbrekend getest manifest, een onbeschikbare vaste versie of een ontbrekende community-trein. Bewaar de bestaande routerinstelling privé, maak een back-up van de configuratie en houd een werkende lokale beheerroute bij de hand. Gebruik eerst één testapparaat waarmee niemand naar Emby kijkt. [Manifestoverzicht][monitoren] · [Catalogustreinen][contract]

### Wat je doet

1. Leg de bestaande DNS-route, beheerroute en terugweg vast (D03 en D11). Controleer dat het testapparaat nu namen kan opzoeken. Richt AdGuard Home geïsoleerd in volgens het vastgezette manifest, met beheer alleen via LAN/VPN. De productierouter blijft op de huidige instelling. [I12 §2, stap 1–2][I12]
2. Laat uitsluitend het testapparaat de nieuwe DNS gebruiken. Controleer gewone websites, apps en toegestane apparaten. Zet het apparaat terug op de oude DNS en controleer opnieuw (EX31). Herhaal de proef met de nieuwe DNS en onderbreek uitsluitend de testdienst AdGuard. Het apparaat moet blijven werken via de terugvalroute en de melding moet aankomen (EX32). Start de testdienst weer. [I12 §2, stap 3 en 6][I12]
3. Probeer filters en uitzonderingen op dat ene apparaat. Controleer toegang voor de gebruikte apps, de huisapparaten en de privéroute. Alleen jij kunt daarna besluiten de router om te zetten. Doe dit als laatste DNS-wijziging, thuis, met een geteste terugweg en alleen wanneer Emby en alle kijkapparaten bereikbaar blijven. De pilot mag de eindstand zijn. [I12 §2, stap 4–6][I12]
4. Richt NetAlertX alleen voor passieve waarneming op het eigen netwerk in, met het goedgekeurde manifest. Leg de bekende apparaten vast en sluit één eigen testapparaat aan (EX33). Controleer één melding “nieuw apparaat”, herkenning in de Hub, bewaartermijn en herstel op een kopie. [I11 §2, stap 1–6][I11]
5. Controleer de bestaande Tailscale- en cloudflared-routes per app, inclusief MFA, certificaatmelding en terugweg. Trek één afzonderlijke testsleutel in. Controleer via die testroute dat beheer van buiten is afgesloten en lokaal nog werkt (EX34). Deel geen adressen. [I21 §2, stap 1–6][I21]

### Wat je terugmeldt

| Gegeven | Jouw terugmelding |
|---|---|
| Bewijs per I-stap, community-trein en vaste AdGuard Home-versie bevestigd, D03 en D11, oorspronkelijke instelling bewaard | |
| Eén testapparaat terug op oude DNS, verbinding bij uitval, melding ontvangen buiten de Hub | |
| Router gewijzigd ja/nee, terugweg en Emby bereikbaar, nieuw apparaat herkend, externe testsleutel ingetrokken | |

### Wat daarna gecontroleerd wordt

De regisseur controleert de volgorde van pilot, uitvalproef en eventuele routerwijziging. De DNS-gate mag pas opengaan na het bewijs bij D11. Een geslaagde pilot bewijst uitsluitend het geteste apparaat.

### Welke rijen daarna van Geblokkeerd af mogen

De uitgevoerde I11-, I12- en I21-stappen, de bewezen proeven EX31 t/m EX34 en de bijbehorende delen van B10-001 t/m B10-006. I12-12-05 blijft open wanneer de router op de oorspronkelijke instelling staat. Een nog te bouwen voorziening houdt de eigen status.

### Stop als

Het testapparaat zijn verbinding verliest, de terugweg ontbreekt, beheer publiek bereikbaar wordt of Emby gevaar loopt. Zet het apparaat en, indien al gewijzigd, de router terug op de genoteerde DNS. Controleer lokaal beheer en afspelen voordat je de storing verder onderzoekt.

## N-P6-08 - Zoeken, persoonlijke AI en optioneel Navidrome

### Voor je begint

03 werkt en de release van de zoekapp heeft een bevestigde pin. Voor foto's uit Immich moet 05 zijn uitgevoerd. Leg bronkeuzes, toestemming en back-up vast. Betaalde functies wachten op D09 met harde bestedingsgrens en werkende verbruiksbewaking.

### Wat je doet

1. Installeer de standaard Custom App met eigen dataset op `/appdata`, TCP-containerpoort **30450** en publicatie op een vrije hostpoort. PostgreSQL met pgvector zit in dezelfde image. Kies per toegestane share een afzonderlijke **Host Path** op `/bronnen/<BRON>` met **Read Only** aan. Verifieer de digest en de koppeling aan de Hub. [Zoekformulier][zoeken] · [I14 §2, stap 1–2][I14]
2. Kies in de Hub per bron expliciet toestemming, toegangsgroepen en bewaartermijn. Bouw de index en zoek naar enkele bekende items. Controleer dat de herkomst zichtbaar is en een herhaling geen dubbele resultaten geeft. [I25 §2, stap 1–3][I25] · [I14 §2, stap 3][I14]
3. Zoek met een beperkt testaccount naar iets waartoe alleen een ander account toegang heeft. Controleer ook titels, voorbeeldplaatjes en foto's uit privé-albums (EX36 en EX43). Trek de toestemming van één proefbron in. Alle treffers daarvan horen te verdwijnen (EX44). [I25 §2, stap 1 en 5][I25]
4. Bouw de index opnieuw op en herstel op een afzonderlijke proefplek. Controleer dezelfde zoekvraag en behoud van de originelen. Probeer betekeniszoeken of spraak alleen na eigen keuze. Controleer bij een onduidelijke spraakopdracht dat eerst een wedervraag komt en geen actie volgt (EX49). Noteer processorbelasting en of afspelen vlot blijft. [I14 §2, stap 4–5][I14] · [I25 §2, stap 4 en 6][I25]
5. Voor betaald gebruik vul je eerst D09 in. Controleer de harde grens en de melding, en vergelijk na een week werkelijk verbruik met het toegestane budget. Voor muziek vul je D18 in. Alleen bij **ja** installeer je Navidrome als **catalogusapp uit de community-trein**, op de beschikbare vaste versie uit het geteste manifest. Je hebt de trein al goedgekeurd (R2). Wacht met deze app als de trein, het geteste manifest of de vaste versie ontbreekt. Het menu is **ONBEKEND - eerst vaststellen op de NAS**. Koppel de muziek alleen-lezen en gebruik een eigen dataset voor de app. Controleer afspelen, illustraties en afspeellijsten op een gebruikt apparaat en herstel de lijsten op een kopie. [I22 §2, stap 1–5][I22] · [Manifestoverzicht][monitoren]

### Wat je terugmeldt

| Gegeven | Jouw terugmelding |
|---|---|
| Bewijs per I-stap, soorten bronnen, alleen-lezen bevestigd, zoeken, herbouwen en geïsoleerd herstel | |
| Beperkt account zonder verboden titel of afbeelding, ingetrokken bron verdwenen | |
| D09 en D18, optionele functies aan/uit, wedervraag, weekverbruik binnen/buiten budget en werking melding | |
| Navidrome bij D18 ja op de vaste manifestversie via de community-trein getest, of reden van overslaan, apparaatsoort en herstel van lijsten | |

### Wat daarna gecontroleerd wordt

De regisseur controleert toestemming, negatieve zoekproeven, de weekmeting en of de gate voor betaald gebruik gesloten bleef toen D09 nog openstond. Alleen daadwerkelijk ingeschakelde en beproefde opties krijgen bewijs.

### Welke rijen daarna van Geblokkeerd af mogen

Uitgevoerde I14- en I25-stappen, EX36, EX43 en EX44, en EX49 bij een uitgevoerde spraakproef. Gebouwde B07- en B15-rijen volgen hun eigen bewijs. De aanbiederrijen van B02 en B01-009 vragen een gebruikte aanbieder, D09 en budgetbewijs. I22 alleen bij uitvoering. Bij **nee** luidt de notitie “niet van toepassing volgens D18”. Schermlezer-, telefoon- en tv-proeven blijven open tot je ze hebt gedaan.

De betrokken aanbiederrijen zijn B02-001 t/m B02-004, B02-007, B02-008 en B02-010 t/m B02-012. D09 en D18 volgen de status in de Hub.

### Stop als

Een beperkt account iets verbodens ziet, een bron beschrijfbaar is of er zonder D09 kosten ontstaan. Trek de toestemming van de betrokken bron in, schakel de betaalde of optionele functie uit en controleer opnieuw met het beperkte account. Herstel alleen de afgeleide index op een aparte plek.

## N-P6-09 - Jelly Leon naast Emby: installatie, clients en GPU

### Voor je begint

02, 03 en 05 zijn voorwaarden voor 09. Controleer de terugmeldingen. Zolang vereist bewijs uit 05 ontbreekt, wacht 09. De inventaris geldt uitsluitend voor de uitgevoerde leescontroles. Er is een vrijgegeven Jelly Leon-image op 12.x met bevestigde digest. Emby bedient het huishouden. Reserveer een andere appnaam, vrije hostpoort, eigen configuratie en eigen cache voor Jelly Leon. Een eventueel al aanwezige Jellyfin blijft draaien. [Formulier Jelly Leon][jelly]

### Wat je doet

1. Noteer in D15 welke soorten spelers je gebruikt, welke direct afspelen en welke via een receiver lopen. Leg op Emby per type de uitgangssituatie voor afspelen, ondertitels, HDR, Dolby Vision en hervatten vast. Speel met een testprofiel een bestaande titel af en controleer de kijkpauze in MediaGuard. Inventariseer een bestaande Jellyfin (APP-17) en maak een back-up. Maak en verifieer ZFS-snapshots van de media en alle Emby-opslag uit 01. Controleer de dekking van MediaGuard uit 02. Noteer bij elke mediasnapshot vrije poolruimte, **Used** en de vroegste vrijgavedatum. Bewaar hem tot 30 dagen na de laatste geslaagde stap en langer zolang hij nodig is voor herstel. Controleer de ruimtemelding voor 20% uit 02 en 04. [I24 §2, stap 1][I24] · [I06 §2, stap 1–2][I06] · [Bescherming en bewaring in N-P6-02, punt 3][snapshotbescherming]
2. Geef Jelly Leon in **Apps → Discover Apps → Custom App** een eigen appnaam. Zet **Host Network** en **Privileged** uit, laat **Environment Variables** leeg en voeg geen capabilities toe. Houd GPU-doorgifte uit tot de meting van D08 en je eigen keuze. Kies TCP-containerpoort **8096** met een vrije, unieke hostpoort (voorstel **30460**). Kies nooit de hostpoort van Emby of een bestaande Jellyfin. De webclient zit in deze image. Apparaatclients installeer je op het apparaat zelf. [I24 §2, stap 3–4][I24] · [Serverformulier][jelly] · [Webclient][webclient] · [Apparaatclients][clients]
    - Kies voor `/config` en `/cache` elk een nieuwe, lege dataset die alleen deze app gebruikt. Deel ook hun submappen niet. Zet alleen eigen snapshots of back-ups van deze configuratie terug. Gebruik nooit een gedeelde cache of een hostmap in het werkgeheugen van de NAS. Koppel de bestaande mediadataset aan `/media` met **Read Only** aan. [Jelly Leon, drie verplichte regels][jelly]
    - Laat **Custom User** uit zoals de handleiding aanbeveelt. Bij de eerste start maakt de container de appgebruiker (568) eigenaar van de eigen config en cache. Geef groep, anderen en andere apps geen schrijfrecht, ook niet via een overerfbare ACL die nieuwe mappen beschrijfbaar maakt. Bij onveilige rechten weigert de container te starten. Controleer bij een startweigering de eigen datasets aan de hand van **Problemen** in de formulierhandleiding. Kan Jelly Leon de media niet lezen, stop en meld het. Wijzig nooit eigenaar, rechten of ACL van Emby-, MediaGuard- of mediadatasets, ook niet recursief of via een bovenliggende dataset. [Jelly Leon, Datasets en Problemen][jelly] · [MediaGuard, bestaande groepstoegang][mg]
3. Rond de startwizard direct af en maak de eerste beheerder aan. Voeg de bibliotheken toe. Houd modules uit. Controleer met een testgebruiker de bibliotheek, serieherkenning en het afspelen. Speel op Emby dezelfde bestaande titel via hetzelfde pad als vóór de installatie. Controleer dat bij de bron geen ondertitel-, afbeelding- of metadatabestand is bijgekomen. Pas opruim- en verversproeven van I06 alleen op proefgegevens toe. [I06 §2, stap 4–7][I06] · [I24 §2, stap 3–4][I24]
4. **Voeg Jelly Leon als tweede mediaserver toe aan MediaGuard.** Controleer eerst op de bestaande Emby-kaart de koppeling en het laatste contact. Laat die kaart staan en kies daarop nooit **Wijzigen** om Jelly Leon in te voeren. Maak in het Jelly Leon-dashboard via **Dashboard → API-sleutels → +** een aparte sleutel voor MediaGuard. Kies in MediaGuard **Inrichten → Mediaservers & ondertitels → Mediaserver toevoegen**. Kies **Jellyfin (Jelly Leon)**, vul bij **Adres** het adres en de eigen hostpoort van Jelly Leon in en bij **API-sleutel** diens sleutel. Kies **Toevoegen en testen**. Controleer beide kaarten op **Gekoppeld** en een geslaagd, recent contact. Speel daarna met een testprofiel eerst op Emby en vervolgens afzonderlijk op Jelly Leon. Controleer per sessie dat MediaGuard nieuwe encodes laat wachten en na afloop veilig hervat. Blijft één kaart of kijkpauze onbevestigd, wacht met EX08 en de overname. [MediaGuard, serverkaarten][mgscherm] · [Schermteksten en hulp voor de sleutel][mgtekst] · [I24 §2, stap 4–5][I24]
5. Laat D08 in **Onboarding** meten. Onderscheid de losse Intel-kaart en de geïntegreerde GPU. Geef Intel-render pas door na die meting. Het standaardformulier kan alle beschikbare niet-NVIDIA-GPU's tegelijk doorgeven. Meet per kaart en soort werk direct afspelen, transcoderen en verwerking. Pauzeer alleen nieuwe MediaGuard-taken op een veilige taakgrens voor de nulmeting en hervat ze daarna voor de belaste meting. Leg voortgang vóór en na vast. Een bevestiging na een NAS-herstart blijft open als Emby daarbij niet kan doorlopen. [I24 §2, stap 2][I24] · [I06 §2, stap 3][I06]
6. Probeer op elk D15-apparaat de gewone Jellyfin-app en, indien beschikbaar, de Jelly Leon-client. Controleer aanmelding, direct afspelen, transcoderen, ondertitels, hervatten, HDR/Dolby Vision en audio via een receiver. Probeer een offlineprofiel op de telefoon. Neem gebruikte apps van derden mee. Noteer expliciet welke apparaatproef je hebt overgeslagen. [I24 §2, stap 5][I24] · [Clientmatrix][matrix]
7. Start twee afzonderlijke proeven met testmedia. Speel op Jelly Leon een film af terwijl MediaGuard omzet. Controleer kijkvoorrang, het wachten van nieuwe encodes, veilige hervatting en behoud van voortgang (EX08). Controleer bij een vastgelopen proeftaak de melding en het uitblijven van een herstartlus (EX07). Heb je een tv-ontvanger, plan dan twee overlappende proefopnames. Het conflict hoort vóór de opname zichtbaar te zijn (EX38). [I24 §2, stap 2 en 5][I24]
8. Oefen uitsluitend op de aparte Jelly Leon-proefinstallatie een update en terugkeer met de vorige tag **én bijpassende configuratiesnapshot**. Gebruik alleen eigen snapshots. Controleer daarna het opnieuw aanmelden en de kijkgegevens van de testgebruiker. Laat zonder tweede geteste versie het versieonderdeel open. [I24 §2, stap 6][I24] · [I06 §2, stap 8][I06]

### Wat je terugmeldt

| Gegeven | Jouw terugmelding |
|---|---|
| Bewijs per I-stap, Emby onafgebroken beschikbaar, media ongewijzigd, rechten op config/cache/media gecontroleerd | |
| Dezelfde Emby-titel vóór/na afgespeeld. Per mediasnapshot ruimte tegenover 20%, Used, gewone vrijgavedatum 30 dagen na de laatste geslaagde stap en bescherming volgens 02 | |
| Aparte Emby- en Jelly Leon-kaart gekoppeld en gezond, per server een sessie met kijkpauze en veilige hervatting | |
| D08 en D15, werkklasse per kaart, meting met en zonder MediaGuard, herstartcontrole gedaan of open | |
| Voorrang, voortgang, storingsmelding, eventuele opname-overlap, versie teruggezet en testhistorie intact, ontbrekende apparaten | |

Vul voor elke geteste combinatie één regel in. Noteer “open” bij een ontbrekende proef.

| Apparaatsoort en client | Login, direct/transcode | Hervatten en ondertitels | HDR/Dolby Vision, audio via receiver | Offlineprofiel |
|---|---|---|---|---|
| | | | | |

### Wat daarna gecontroleerd wordt

De regisseur vergelijkt elke apparaatregel met de clientmatrix en de GPU-metingen met het manifest. De GPU-toestemming mag pas na D08 open zijn. Voor EX08 controleert hij de twee aparte serverkaarten en de kijkpauze per server. Mediamutatie buiten MediaGuard of verlies van beeldfunctionaliteit blokkeert de overstap.

### Welke rijen daarna van Geblokkeerd af mogen

De bewezen I06- en I24-stappen, EX07, EX08, EX10, EX35 en EX38 met echte ontvanger. D08 en D15 volgen de Hub. JLT-49, JLT-63, JLT-64 en de toepasselijke apparaatdelen van B03 vereisen dekking van hun volledige proef. JLT-69 wacht ook op overname, belasting en terugzetten in 12. Swiftfin en Safari blijven open zonder de vereiste Apple-proef. Voor distributie van de Android-apps is de ondertekeningskeuze nodig.

Controleer voor B03-001 t/m B03-012, B03-016 t/m B03-019 en JLT-40 t/m JLT-48 de terugmelding per werkklasse en speler. EX48 en B08-005 gaan over een incompatibele upstream-versie. Laat die rijen open zonder een eigen compatibiliteitsrapport voor de gebruikte release.

### Stop als

Emby hapert, poorten botsen, de Emby-kaart ontbreekt of is gewijzigd, een kaart geen gezond contact heeft, of op een van beide servers de kijkpauze uitblijft. Pauzeer dan nieuwe MediaGuard-taken tot de werkende Emby-koppeling en kijkpauze bevestigd zijn. Stop ook bij onvolledige snapshots, minder dan 20% vrije poolruimte (pauzeer nieuwe MediaGuard-taken), onleesbare media, voorgestelde rechtenwijzigingen, veranderde mediabestanden, een defecte client of verlies van HDR/Dolby Vision. Breek de Jelly Leon-proef af. Laat eigenaar, rechten en ACL staan, zet de testspeler terug op de beschermde Emby en controleer de afspeelpositie.

## N-P6-10 - De Jelly Leon-modules en de belastingtest op de NAS

### Voor je begint

09 is uitgevoerd. Controleer welke modules in de gepinde release zijn gebouwd. Houd twee proefaccounts, twee apparaten uit D15, een eigen gelabelde steekproef afleveringen en de resourcegrenzen van het manifest bij de hand. Leg vooraf je keuze voor JLT-06 vast. Je kunt naast Emby vóór de overstap testen, of JLT-06 uitstellen met een uitdrukkelijke uitzondering op punt 4 van de overstaptoets. Zonder keuze blijft de volgorde open. [Clientproef, I24 §2, stap 5][I24] · [Overstaptoets][cutover]

### Wat je doet

1. Open in het pluginbeheer **Jelly Leon → Modules**. Zet één beschikbare module aan en speel een titel met een testaccount. Herhaal dit per module. Houd de kijkgegevens van het proefaccount en de mediamappen als vergelijkingspunt. [Pluginscherm][modules] · [I06 §2, stap 6–7][I06]
2. Start bij JLT-06 één gezamenlijke Watch Together-sessie op twee apparaten. Pauzeer, spoel en hervat. Controleer synchronisatie en de kijkpauze van MediaGuard. Een deelnemer van buiten komt alleen in aanmerking als je dat vooraf hebt toegestaan. [I24 §2, stap 5][I24] · [Testrij JLT-06][jltesten]
3. Laat voor JLT-59 de gelabelde steekproef analyseren. Tel op tv en telefoon de goed en fout getimede knoppen voor intro, samenvatting en aftiteling. Controleer ook de scène ná de aftiteling en dat de analyse de losse GPU die voor ander werk gereserveerd is vrijlaat. [I24 §2, stap 5][I24] · [Testrij JLT-59][jltesten]
4. Beproef aanbevelingen (JLT-15) vóór 11 uitsluitend met testgebruikers. Kom na 11 hier terug voor de eenmalige evaluatie op echte kijkhistorie. Maak eerst een verse ZFS-snapshot van de Jelly Leon-configuratie. Gebruik alleen geaggregeerde uitkomsten van deelnemende volwassenen, met afmeldmogelijkheid per gebruiker. Stuur geen persoonlijke kijktitels of kijkprofielen mee. [I24 §2, stap 1 en 5][I24] · [Testrij JLT-15][jltesten]
5. Gebruik voor JLT-26 echte ondertitelparen, met Engels en menselijk Nederlands. Laat voor JLT-39 kwaliteitscontrole tegelijk met MediaGuard-AV1 en een live-transcode lopen. De bibliotheek blijft alleen-lezen. Alleen MediaGuard en Bazarr halen ondertitels op. Meet haperingen en tel gewijzigde mediabestanden (verwacht nul). Voor de startbediening van deze afzonderlijke proeven geldt **ONBEKEND - eerst vaststellen op de NAS**. [I06 §2, stap 3 en 6][I06] · [Testrijen JLT-26 en JLT-39][jltesten]
6. Start voor JLT-66 twee proefstreams, één analyse en een MediaGuard-taak tegelijk. Lees in de Hub CPU, geheugen en kijkvoorrang af. Vergelijk met de limieten van de geïnstalleerde release en de nulmeting uit 04. Is de belastingproef niet vanuit de webinterface te starten of te meten, laat dan de rij open. [I24 §2, stap 2 en 5][I24]
7. Heeft je Hub een lokale dienst voor vertaling, betekeniszoeken of spraak geïnstalleerd, schakel dan alleen de bijbehorende module in. Controleer dat deze binnen het thuisnetwerk werkt en dat de UI de netwerkcontrole toont. Is die meting niet beschikbaar, noteer dat. Meld alleen soort dienst en uitkomst. [I06 §2, stap 6][I06] · [Pluginscherm][modules]

### Wat je terugmeldt

| Gegeven | Jouw terugmelding |
|---|---|
| Per module aan/uit, gewoon afspelen, kijkgegevens en media gelijk, bijbehorend I-bewijs indien van toepassing | |
| Watch Together met twee apparaten, MediaGuard-pauze, knoppen goed/fout per apparaatsoort | |
| JLT-15 voor of na 11, alleen geaggregeerde uitkomst, uitsluiting kinderen en mogelijkheid tot afmelden | |
| Ondertitels, kwaliteitscontrole, twee streams onder belasting, haperingen, CPU/geheugen versus manifest, optionele netwerkmeting | |

### Wat daarna gecontroleerd wordt

De regisseur vergelijkt de gemeten belasting met de releasegrenzen en controleert of de media en kijkgegevens gelijk bleven. Voor een lokale verwerkingsdienst vergelijkt hij de draaiende serverdigest ook met de release waarvoor de controle van de inhoud van de image is uitgevoerd.

### Welke rijen daarna van Geblokkeerd af mogen

JLT-06, JLT-26, JLT-39, JLT-59 en JLT-66 en de bijbehorende B03-modulerijen per volledige proef. JLT-15 vraagt de echte, geaggregeerde evaluatie na 11. De netwerkcontrole vraagt zowel een werkende optionele dienst als een gemeten uitkomst. Uitgeschakelde of ontbrekende modules en ontbrekende Apple-apparaatproeven blijven open.

### Stop als

Een module afspelen breekt, kijkgegevens of media verandert, buiten de resourcegrens komt of een verwerkingsdienst buiten het thuisnetwerk vereist. Zet de laatst ingeschakelde module uit. Controleer dat gewoon afspelen weer als in de standaardclient werkt. Bewaar recentere kijkgegevens afzonderlijk voordat je de eigen Jelly Leon-configuratie uit het bijbehorende herstelpunt herstelt. Emby blijft beschikbaar.

## N-P6-11 - De echte overname vanuit Emby

### Voor je begint

**Start pas als alle voorwaarden aantoonbaar zijn vervuld.** 02 is volledig uitgevoerd. Uit 09 blijkt dat Jelly Leon met afgeronde startwizard naast Emby draait. D07 is gemeten en de generale repetitie gebruikte precies die Emby-versie op vaste digest en de beoogde Jelly Leon-image. De bijgewerkte overnamehandleiding en een werkende **webassistent in het beheer van Jelly Leon** zijn beschikbaar. De gelezen handleiding noemt die assistent nog als open punt. Leg vooraf per gebruiker vast of die een nieuw wachtwoord of Authentik krijgt. [Overname, stappen en voorwaarden][overname]

### Wat je doet

1. Maak verse ZFS-snapshots van alle gebruikte Emby-datasets uit 01 en van de Jelly Leon-configuratie. Zoek ze terug en verifieer de volledige dekking. Controleer de dekking van de MediaGuard-database en de voortgang uit 05. Bewaar naam en tijdstip lokaal. Laat JellyPlex Watched los van Jelly Leon zolang de overname loopt. [I01 §2, stap 2][I01] · [I26 §2, stap 3][I26]
2. Maak zelf in Emby een API-sleutel en voer die uitsluitend op de bedoelde pagina van de assistent in. De assistent leest Emby alleen via zijn leesinterface. De databasebestanden van Emby blijven dicht. Laat de assistent controleren dat het doel een **andere** server is met productnaam **Jellyfin Server**. Het pad naar de assistent is **ONBEKEND - eerst vaststellen op de NAS**. [Overname, doelcontrole en stap 1][overname] · [I06 §2, stap 6 (import via de app)][I06]
3. Laat de inventaris van versie, gebruikers, bibliotheken en plugins uitlezen. Controleer de aantallen. Maak het blijvende **JSON-exportarchief met SHA-256** van de kijkgegevens die Emby per gebruiker levert. Vergelijk met wat in Emby zelf zichtbaar is en leg ontbrekende waarden bij de verschillen vast. Controleer de checksum van de bewaarde kopie en houd het archief ook na de overstap onder back-updekking. [Overname, stap 1–2][overname] · [I26 §2, stap 2 (behoud kijkstatus)][I26]
4. Start de **droge proefrun**. Er wordt nog niets naar Jelly Leon geschreven. Lees voor elke gebruiker wat in Emby staat, wat het plan verwacht en de reden van ieder niet-gekoppeld of afwijkend item. Leg bij **elk verschilakkoord** privé vast om welk gegeven het gaat, waar het terug te lezen is, met welke rechten en wanneer je de waarde daar hebt gezien. Doe dit bij elk volgend akkoord, ook bij de laatste delta. Ontbreekt een werkende leesroute of weiger je een verschil, wacht dan. Bij een wijziging sinds de proefrun maak je een nieuw plan en beoordeel je de verschillen opnieuw. [Overname, soorten gegevens en stap 3–4][overname] · [I24 §2, stap 1 (uitgangsstand)][I24]
5. Selecteer eerst een geïsoleerde, schrijfbare **kopie van de Jelly Leon-datamap** als doel. Controleer bron, doel en tijdstip op het scherm. Zet uitsluitend op die kopie over. Vergelijk per gebruiker alle tellingen met het plan. Lees per gebruiker en soort de waarden met de juiste rechten terug, ook bij afzonderlijke verschillen. Noteer de vindplaats, datum en uitkomst in de tabel en beslis opnieuw per verschil. Houd een ontbrekend rapport, een ongekend verschil of een onleesbare waarde open. [Overname, stap 5–6][overname] · [I24 §2, stap 4 (proefinstallatie)][I24]
6. Pas na akkoord op de kopie maak je een vers herstelpunt van de echte **Jelly Leon**-configuratie. Controleer de doelidentiteit opnieuw. Herhaal de goedgekeurde overdracht op Jelly Leon en vergelijk het nieuwe vóór/na-rapport per gebruiker en soort gegeven. Bewaar het JSON-eindrapport met eigen SHA-256 en leg elk afzonderlijk akkoord of elke weigering vast. [Overname, stap 5–6][overname] · [I26 §2, stap 2 (gebruikers en kijkstatus)][I26]
7. Vergelijk op beide servers vijf titels per gebruiker, met in ieder geval een bekeken film, een half bekeken aflevering en een favoriet. Herhaal de overname zonder bronwijziging. Verwacht nul nieuwe wijzigingen (JLT-71). Controleer Emby-afspelen en de MediaGuard-tellers uit 05. Open in MediaGuard **Inrichten → Mediaservers & ondertitels**. De oorspronkelijke Emby-kaart en de tweede kaart voor Jelly Leon uit 09 moeten elk gekoppeld en gezond zijn. Herhaal de kijkpauze afzonderlijk met een sessie op elk van beide servers. Stel uitsluitend voor Jelly Leon per gebruiker het gekozen nieuwe wachtwoord of Authentik in. Behoud de gewone Emby-aanmelding uit 04. [Overname, vóór/na-rapport][overname] · [MediaGuard-koppeling][mgscherm] · [I24 §2, stap 5–6][I24]

### Wat je terugmeldt

Kopieer de eerste gegevensregel voor **iedere gebruiker en iedere soort**. Rapporteer gezien (ook aantal en datum), hervatpunten, favorieten, beoordelingen, voorkeuren en rechten. Neem de afhandeling van onthouden spoorkeuzes afzonderlijk mee. Bewaar bestandsnamen, titels en de rapporten met persoonsinformatie privé.

| Gebruikersnummer en soort | In Emby | In plan | Na op kopie | Na op Jelly Leon | Verschil, reden en jouw akkoord/weigering | Geteste leesroute, rol en datum |
|---|---:|---:|---:|---:|---|---|
| | | | | | | |

| Bewijs | Jouw terugmelding |
|---|---|
| Bewijs per betrokken I-stap, D07 gemeten, repetitie op dezelfde versie, snapshots vóór de overdracht | |
| Aantal afhandelregels per reden, ontbrekende koppelingen, per regel aanvaard/geweigerd | |
| SHA-256 exportarchief, SHA-256 eindrapport, back-updekking, uitkomst “overstap toegestaan” | |
| Steekproef vijf per gebruiker, herhaling met nul wijzigingen, Emby beschikbaar, MediaGuard-tellers gelijk en kijkpauze op beide servers | |

### Wat daarna gecontroleerd wordt

Controleer per gebruiker en soort zowel de telling als de toegang. Dit omvat beoordelingen die de bron soms niet levert, strenger overgenomen rechten en spoorkeuzes die het doel niet kan vastleggen. Geeft de export een nul terwijl de gebruiker in Emby wél een waarde ziet, zoek die waarde op in een afgeschermde leesbare kopie met passende rechten. Noteer bij ieder afwijkend gegeven waar je het tijdens de Emby-stop kunt terugvinden. Blijft de draaiende Emby de enige vindplaats, dan wachten de overstap en de proefstop. [Overname, soorten gegevens en beperkingen][overname]

### Welke rijen daarna van Geblokkeerd af mogen

B03-015, JLT-70 t/m JLT-73 en het bijbehorende contractpunt over bronbescherming, uitsluitend met de juiste Emby-versie en de volledige bewijsvoering. D07 volgt de Hub. De overstap wacht op de laatste delta en de overstaptoets in N-P6-12. JLT-74 vraagt ook de zes proefpunten van N-P6-13.

### Stop als

Een vereiste snapshot ontbreekt of de dekking onzeker is, de webassistent ontbreekt, bron en doel naar dezelfde server wijzen, het doel geen Jellyfin-server is, er een rapport ontbreekt, een verschil onverklaard is of jij het weigert, Emby anders gaat werken of er één aanwijzing is dat de overname in Emby schreef. Stop ook bij een onbereikbaar kijkgegeven of een weggevallen serverkaart, kijkpauze of voortgang. Breek de overdracht af. Bewaar de rapporten en de mislukte doelkopie. Herstel uitsluitend Jelly Leon op een eigen kopie met bijpassende image en snapshot. Kies in **Apps** op Emby, een bestaande Jellyfin en MediaGuard nooit **Roll Back** of **Update**. Kies nooit **Rollback** en wijzig nooit de rechten op Emby-, MediaGuard- of mediadatasets of een bovenliggende dataset. Blijf kijken via de beschermde Emby en verifieer de MediaGuard-voortgang.

## N-P6-12 - De overstap (Cutover-gate)

### Voor je begint

09, 10 (met je vastgelegde keuze over de moduleproef) en 11 zijn doorlopen. Houd het goedgekeurde NA-rapport uit 11, het permanente exportarchief met SHA-256, hun back-ups en de gemeten client- en GPU-resultaten bij de hand. Kies samen een rustig moment waarop niemand kijkt. Emby blijft draaien. [Overstaptoets, vijf voorwaarden][cutover]

### Wat je doet

1. Controleer dat niemand kijkt. Maak opnieuw ZFS-snapshots van alle Emby-datasets uit 01 en de Jelly Leon-configuratie. Controleer dat je ze terugvindt, met naam en tijdstip op je privéblad. Leg ook de bijbehorende imagewaarden vast. Bescherm de op dit moment actuele kijkgegevens. [I01 §2, stap 2][I01] · [I24 §2, stap 6][I24]
2. Maak een **aparte Jelly Leon-proefapp** met een eigen appnaam en vrije, unieke hostpoort op TCP-containerpoort **8096**. Sluit de poorten van Emby, een bestaande Jellyfin én de gewone Jelly Leon uit. Zet **Host Network**, **Privileged** en **Custom User** uit, laat **Environment Variables** leeg, voeg geen capabilities toe en laat GPU-doorgifte uit voor deze herstelproef. Koppel aan `/config` uitsluitend een afzonderlijke schrijfbare kloon van een **eigen** configuratiesnapshot. Geef de proefapp een eigen lege `/cache` en koppel de media aan `/media` met **Read Only** aan. Gebruik de drie verplichte regels uit 09 ook voor de kloon. Deel geen config, submap of cache met andere apps. Controleer vooraf exclusief schrijfrecht zonder overerfbare schrijf-ACL voor anderen en na de eerste start eigenaar 568 op de proefopslag. Houd de proefapp buiten de koppelingen van het huishouden. [Jelly Leon, formulier en drie verplichte regels][jelly] · [I06 §2, stap 8][I06]
    - Oefen op de kloon met de vorige Jelly Leon-tag **met digest, vorige formulierwaarden en de bijbehorende config-snapshot van vóór de update**. Behoud bij het overnemen van de formulierwaarden de appnaam, poort en opslag van de proefapp. Zonder vorige vrijgegeven versie doe je alleen de snapshotproef op een aparte kopie en meld je de versieproef als open. Zet ook weer vooruit op een kopie van de bewaarde juiste configuratie met de juiste image. Vergelijk per gebruiker gezien, hervatpunten en favorieten met het NA-rapport uit 11. Bij een verschil houd je de spelers op Emby. [I06 §2, stap 8][I06] · [Jelly Leon, updaten en terugdraaien][jelly]
3. Laat de assistent de **laatste delta** uit Emby bepalen. Bewaar het bijgewerkte exportarchief met SHA-256. Herhaal voor uitsluitend de veranderingen sinds 11 de droge proefrun, akkoord op elk verschil, proef op de kopie, vóór/na-vergelijking en akkoord. Pas daarna voer je de delta op het echte Jelly Leon-doel uit, met een nieuw rapport en akkoord op elk verschil. Bewaar ook daarvan de SHA-256. Heeft iemand intussen weer op Emby gekeken, dan herhaal je de delta op een nieuw rustig moment. [Overname, stap 7][overname] · [I24 §2, stap 6][I24]
4. Beproef **vóór de overstap** per gebruiker en soort twee leesroutes met de juiste toegangsrechten. Lees voor de Emby-stop de gegevens terug in Jelly Leon of op een afgeschermde, leesbare kopie zonder de draaiende Emby te gebruiken. Zoek elk afwijkend gegeven uit 11 op en zet de vindplaats bij het verschilakkoord. Beproef voor de terugval ook de omgekeerde richting zoals hieronder. Wacht zodra één gegeven onbereikbaar zou worden. Controleer daarna **overstap toegestaan** en de vijf voorwaarden in de tabel. [Overstaptoets][cutover] · [Overname, soorten kijkgegevens][overname]
    - **Eenmalige uitvalproef vóór overstap én proefstop.** De webbediening voor de aparte kloon en voor het afschermen van het gewone doel is **ONBEKEND - eerst vaststellen op de NAS**. Wacht zolang die bediening onbekend is. Noteer met het proefprofiel privé waar de proeftitel op de laatste gewone kopie hervat. Sla op Jelly Leon een duidelijk ander hervatpunt op en noteer de bevestigde positie. Boots direct daarna, vóór de gewone verversing van de kopie, uitval na. Het gewone Jelly Leon-doel moet voor zowel de proefspeler als de afgeschermde leesroute onbereikbaar zijn. Laat Emby en de spelers van het huishouden draaien. Open de titel met de rechten van het proefprofiel via de afgeschermde leesroute en lees de opgeslagen positie terug terwijl de gewone kopie nog onververst is.
    - Vergelijk de teruggelezen positie met het nieuwe hervatpunt. Noteer beide posities en de tijdstippen van de laatste verversing, opslag, uitval en teruglezing. Gebruik dit ene bewijs ook in N-P6-13, punt 2. Was het gewone doel toch bereikbaar, is de kopie te vroeg ververst, ontbreekt het hervatpunt of wijkt de positie af, dan wachten de overstap én de proefstop.
    - **Ververs de kopie** tijdens de proefperiode en de proefstop minstens dagelijks en direct vóór een geplande terugkeer. Gebruik een consistente eigen configuratiesnapshot en de bijpassende image op de aparte kopie van punt 2. Vergelijk per gebruiker en soort de laatste waarden en rechten. Noteer het tijdstip en de teruggelezen stand. Houd de afgeschermde leesroute ook tussen verversingen beschikbaar. [Jelly Leon, eigen configuratiesnapshot en bijpassende image][jelly]
5. Kies pas bij vijf onderbouwde antwoorden “ja” op de apparaten in huis de Jelly Leon-server. **Spelerproef.** Schakel op één speler terug naar Emby en weer naar Jelly Leon. Beide servers draaien en blijven aan MediaGuard gekoppeld. Controleer afspelen, de juiste kijkgegevens en de kijkpauze met één sessie per server. Leg dit apart vast. Voor **Start** en **Weer koppelen** geldt de afzonderlijke proef in 13. [I24 §2, stap 5–6][I24]
6. Controleer na een dag gewoon gebruik per gebruiker gezien-status, hervatpunten en favorieten. Leg de proefduur vast en lees ook de sindsdien gewijzigde waarden via de terugvalroute van punt 4. De overname leest Emby alleen. Nieuwe Jelly Leon-kijkgegevens vind je bij terugkeer naar Emby via die aparte route. Bewaar de herstelpunten en laat de leesbare kopie beschikbaar zolang een gebruiker, proef of terugweg ervan afhangt. Alleen een overbodige proefapp mag je na controle van de proefnaam met **Delete** opruimen, met **Remove iXVolumes** uit. Controleer dat Emby en de gewone Jelly Leon nog spelen. [I24 §2, stap 6][I24] · [TrueNAS, opslag behouden][installatie]

### Wat je terugmeldt

| Voorwaarde voor de overstap | Ja/nee, datum en onderliggend bewijs |
|---|---|
| 1. Overname en delta met vóór/na-rapport, elk verschil aanvaard met beproefde vindplaats. Per gebruiker en soort leesbaar tijdens Emby-stop én bij terugval. Bij de uitvalproef gaf de afgeschermde route het nieuwe hervatpunt terug vóór de gewone kopieverversing. Verse snapshot en geteste terugweg | |
| 2. Emby draait en blijft gekoppeld tijdens de overstap. Alleen jij voert de proefstop in 13 na vijf gedateerde controles uit. Die eindigt met draaiende, gekoppelde Emby | |
| 3. D07, D08 en D15 ingevuld, beide GPU's onderscheiden en per kaart en werkklasse gemeten | |
| 4. Vereiste NAS- en apparaatproeven uitgevoerd, keuze over JLT-06 verantwoord. Swiftfin en Safari blijven herkenbaar open zonder Apple-bewijs | |
| 5. Gewone Jellyfin-clients werken, HDR en Dolby Vision behouden, nul mediamutaties buiten MediaGuard en de oorspronkelijke Jellyfin beschikbaar | |

| Uitvoering | Jouw terugmelding |
|---|---|
| Bewijs per I-stap, snapshots en terugzetproef. Per gebruikersnummer drie tellingen na de terugzetproef versus het NA-rapport uit 11 | |
| Proefapp op afzonderlijke poort, config en cache exclusief, media Read Only. Leesroute behouden bij opruimen | |
| Delta per gebruiker en soort (tabel uit 11), reden, akkoord en vindplaats per verschil, hashes van export en rapport | |
| Uitvalproef uit punt 4. Tijdstippen van de laatste gewone verversing, het nieuwe hervatpunt, de uitval en de teruglezing. Gewoon doel onbereikbaar, oude en nieuwe positie vergeleken, uitkomst met de juiste profielrechten | |
| Toestemming van de assistent, kijkpauze op beide servers, spelerproef met twee draaiende servers, steekproef na één dag en gekozen proefduur | |

### Wat daarna gecontroleerd wordt

De regisseur vergelijkt de delta per gebruiker en per soort met 11, de herstelde aantallen met het NA-rapport en elk “ja” met de onderliggende terugmelding. Een nog open no-go blijft zichtbaar. Alleen jij besluit over de overstap.

### Welke rijen daarna van Geblokkeerd af mogen

B03-013 en JLT-61 vragen een passende terugzetproef. B03-014 vraagt Jelly Leon 12.x op de NAS. JLT-65 vraagt aangetoonde gegevensbescherming. JLT-69 vraagt overname, belasting, apparaatproef én terugzetproef. JLT-60 en JLT-62 tellen alleen bij overname van een bestaande Jellyfin-datamap na een proef op een kopie. Anders noteer je “niet van toepassing, geen bestaande Jellyfin-datamap overgenomen”. JLT-74 wacht op 13. JLT-67 wacht op een volgende upstream-versie.

### Stop als

Eén van de vijf voorwaarden ontbreekt, een leesroute of verschilakkoord ontbreekt, de kloon geen eigen poort of opslag heeft, de herstelde waarden afwijken of Emby als terugval hapert. Laat de spelers op Emby zolang de overstap wacht. Bij onverwachte uitval keer je direct terug. Zodra Emby draait en gekoppeld is en de gewone aanmelding, het afspelen en de Emby-kijkpauze werken, kan het huishouden weer kijken. Lees de laatste Jelly Leon-wijziging met de juiste rechten via de afgeschermde route uit punt 4, ook als de dagelijkse kopie ouder is. Bij een afwijking bewaar je de actuele Jelly Leon-opslag en alle herstelpunten en blijven de overstap en de proefstop open. Kies in **Apps** op Emby, een bestaande Jellyfin en MediaGuard nooit **Roll Back** of **Update**. Kies nooit **Rollback** en wijzig nooit rechten op Emby-, MediaGuard- of mediadatasets of een bovenliggende dataset.

## N-P6-13 - Omkeerbare Emby-proefstop

### Voor je begint

**Keuze B van 25 november 2026 geldt uitsluitend voor de omkeerbare proefstop.** Alleen jij mag na 12 en de afgesproken proefperiode de zes proefpunten hieronder uitvoeren. N-P6-13 eindigt met draaiende, aan MediaGuard gekoppelde Emby. **Delete** van Emby en het wissen van Emby-opslag zijn in versie 1 verboden. De kijkgegevens per gebruiker en de MediaGuard-voortgang moeten ook tijdens de stop toegankelijk zijn. Plex valt buiten dit besluit. De oude controlelijst dient uitsluitend als achtergrond en bewijsbron. De afgeschermde herimport staat in punt 4 en de stop en terugkeer staan in punt 6. [Oude controlelijst, alleen achtergrond][controlelijst] · [I26, bewijsrijen bij de proefstop][I26]

- **Bewijs van de terugweg, vóór de eerste ontkoppeling.** Bewaar de spelerproef uit 12 afzonderlijk. Leg daarnaast een gedateerd proefverslag klaar van dezelfde TrueNAS-, Emby- en MediaGuard-versies, installatiewijze, opslag en kaartinstellingen als de beoogde proef. Dat mag bestaand passend bewijs zijn of een afgeschermde lokale proef met dezelfde inrichting en uitsluitend testgegevens. Gebruik hiervoor geen stop van de Emby van het huishouden. [TrueNAS, app-acties §4][appacties] · [MediaGuard, app starten][mg]
- Controleer wat dat verslag aantoont. De bewaarde Emby-app ging met één **Start** van **Stopped** naar **Running**. Na **Weer koppelen** op de oorspronkelijke kaart waren het contact en de ingestelde verversing hersteld. De gewone client kon aanmelden en afspelen. Bij alleen een Emby-testsessie zag MediaGuard de sessie en de kijkpauze als reden dat nieuwe encodes wachtten. De kijkgegevens en rechten per gebruiker en soort waren intact. Ontbreekt een van deze uitkomsten of past het bewijs niet bij de installatie, laat Emby draaien en gekoppeld en houd de proefstop open. [MediaGuard, serverkaarten][mgscherm] · [Schermteksten][mgtekst]
- Spreek een rustig moment af. Maak vóór punt 1 een verse ZFS-snapshot van de betrokken gegevens en controleer de dekking. Stel vooraf een actuele sessiemeting **in Emby zelf** vast die je ook na ontkoppeling kunt lezen. Controleer met één proefafspeling en na het beëindigen daarvan of je de overgang naar nul ziet. Het precieze scherm is **ONBEKEND - eerst vaststellen op de NAS**. Wacht met de proef zolang deze onafhankelijke controle ontbreekt. Voer de laatste delta ná die afspeling uit. Vul bij punten 1–5 elk ‘ja’ of ‘nee’ en de uitvoerdatum in. Punt 6 krijgt zijn uitkomst pas na de terugkeer.

### Wat je doet

1. <a id="proefpunten-emby"></a>Controleer het vóór/na-rapport van de **laatste delta** na droge proef, akkoord per verschil en beproeving op een kopie. Controleer in MediaGuard dat er nul actieve Emby-sessies zijn. Is sinds die delta op Emby gekeken, herhaal dan op een rustig moment de delta volgens 12 punt 3 met alle bijbehorende controles en een vers herstelpunt. Beoordeel daarna opnieuw de proefpunten van dit onderdeel.
2. Open het JSON-eindrapport. Controleer de SHA-256 en **overstap toegestaan**. Lees met de juiste rechten per gebruiker en soort de laatste waarden terug zonder de draaiende Emby te raadplegen. Zoek **ieder** afwijkend gegeven op de bij het verschilakkoord vastgelegde vindplaats op. Neem het gedateerde bewijs uit N-P6-12, punt 4, erbij. Daar moet het nieuwe hervatpunt bij uitval vóór de gewone kopieverversing zijn teruggelezen. Controleer dat dezelfde afgeschermde route beschikbaar is en de recente Jelly Leon-waarden teruggeeft. Houd beide leesroutes tijdens de proef beschikbaar. Ontbreekt het bewijs of een waarde, laat Emby draaien en gekoppeld.
3. Maak verse ZFS-snapshots van de configuratie en alle gebruikte Emby-datasets uit 01. Zoek ze terug. Controleer tijdstip, dekking, **Used**, ruimte tegenover 20%, vrijgavedatums en bescherming volgens 02. Bewaar de laatste Emby-snapshot en het exportarchief. [Bescherming en bewaring in N-P6-02, punt 3][snapshotbescherming]
    - **Pauzeer vóór het ontkoppelen alle nieuwe MediaGuard-taken die de voortgang kunnen wijzigen.** Controleer in de wachtrij dat ze wachten en laat lopende encodes, imports en hersteltransacties veilig afronden. Controleer met Emby nog gekoppeld en zonder kijksessie dat de pauze blijft gelden. De webbediening voor deze taakpauze is **ONBEKEND - eerst vaststellen op de NAS**. Kan de pauze niet stabiel worden aangehouden, dan wacht de proef en blijft Emby gekoppeld. Houd de pauze de hele proefstop aan, tot na de gecontroleerde terugkeer in punt 6. [MediaGuard, back-up en upgrade][mg]
    - **Apart herstelbewijs voor MediaGuard.** Leg de actuele, stabiele stand vast. Noteer privé de versie en welke bij elkaar horende snapshots de voortgang, het hersteljournaal, werkgegevens en de huidige én eerder gebruikte quarantaine dekken. Neem ook originelen mee waarnaar het journaal verwijst. Vergelijk op een geïsoleerd doel vanuit díe set de open én afgeronde taken, hun status en bijbehorende werkgegevens met de vastgelegde stand. Lees het journaal terug, volg elke verwijzing naar een herstelbaar origineel en vergelijk bestand, grootte en checksum met de bron. Bewaar het bewijs met het tijdstip van de set. [MediaGuard, afgeschermde proefkopie en back-up][mg]
    - Gebruik hiervoor een beproefde alleen-lezenroute op een geïsoleerd doel of een al gedateerde herstelproef op zo'n doel van **dezelfde actuele set en versie**. Houd de gewone MediaGuard in bedrijf. De upgrade uit 05 wacht. Zonder veilige leesbediening, aantoonbaar samenhangende set of passend herstelbewijs blijft de proefstop open. De algemene back-upgate en de inventaris uit 05 leveren dit bewijs niet. De bediening voor het afzonderlijk teruglezen is **ONBEKEND - eerst vaststellen op de NAS**. Wijzigt de stand, leg dan de nieuwe set vast en controleer die opnieuw vóór je ontkoppelt.
4. Controleer het blijvende exportarchief met SHA-256 op de NAS en in de back-up. Vergelijk in de Hub **Backups → Back-upmeldingen → Emby-exportarchief** met de werkelijke externe kopie. Controleer in de webassistent de bron en het doel. Lees het archief uit de externe back-up uitsluitend in op een **lege, afgeschermde kopie** en vergelijk checksum, inhoud en tellingen. De webbediening voor deze herimport is **ONBEKEND - eerst vaststellen op de NAS**. Zonder veilige doelkeuze en aangetoonde herimport wacht de proefstop. [I02 §2, bewijsrijen bij stap 3 en 6][I02]
5. Controleer op het afgesproken moment de vier gedateerde ‘ja’-antwoorden, het aparte terugwegbewijs, het MediaGuard-herstelbewijs en de gezondheid van beide serverkaarten. Controleer opnieuw dat nieuwe taken wachten, lopend werk is afgerond en Emby nul sessies heeft. De Emby-kijkpauze is vóór de laatste delta aangetoond. Is er sindsdien op Emby afgespeeld, ook als proef, herhaal de delta en punten 1–4. Ontbreekt iets, laat de kaart gekoppeld. [MediaGuard, back-up en upgrade][mg]
    - Kies pas nu op de Emby-kaart **Inrichten → Mediaservers & ondertitels → Ontkoppelen…**. Behoud de kaart voor **Weer koppelen**. MediaGuard volgt Emby vanaf dat moment niet meer voor verversen, afspeeltests of kijkpauze. Speel uitsluitend op Jelly Leon een proeftitel af. Controleer dat MediaGuard alleen Jelly Leon volgt en diens sessie als wachtreden toont, terwijl de handmatige taakpauze blijft gelden. Lees de recente kijkstand van die proef terug via de afgeschermde route uit 12. Controleer de voortgang en dateer punt 5. Bij uitstel of afbreken houd je taken gepauzeerd en herstel je direct de Emby-koppeling volgens punt 6. [MediaGuard-koppeling][mgscherm] · [Schermteksten bij ontkoppelen][mgtekst]
6. **Proefstop van minstens 72 uur.** Vergelijk de laatste Emby-kijkstand met de delta. Controleer direct vóór **Stop** opnieuw in Emby zelf of er nul actieve sessies zijn. Een lege of oude meting van de ontkoppelde kaart telt niet. Alleen bij een ongewijzigde kijkstand, een actuele nulmeting en vijf gedateerde ‘ja’-antwoorden stop jij de bewaarde Emby-app in de TrueNAS-webinterface. Bij een nieuwe sessie, onbekende stand of uitstel blijft Emby aan. Houd de taken gepauzeerd en volg direct de terugweg hieronder.
    - **Tijdens de proefstop.** Controleer **Stopped**, de leesroutes uit punt 2 en de Jelly Leon-kijkpauze. Alle voortgangswijzigende MediaGuard-taken blijven de hele proefstop gepauzeerd, ook met Emby gestopt en minstens 20% vrije poolruimte. Ververs de Jelly Leon-kopie minstens dagelijks en direct vóór een geplande terugkeer. Lees telkens de nieuwste stand terug en noteer het tijdstip. Controleer dan ook de wachtrij en vergelijk de voortgang en het journaal met de herstelset uit punt 3. Noteer begin en einde van de proef. Mislukt de verversing, valt de pauze weg, mist iemand iets of treedt een andere stopreden op, keer dan direct terug, ook binnen 72 uur. Gebruik bij onverwachte uitval de beproefde leesroute uit 12 zonder op een verversing te wachten.
    - **Terugkeer bij afloop, uitstel of afbreken.** Houd de taakpauze aan. Is de pauze weggevallen, houd dan onmiddellijk nieuwe taken tegen en bewaar de actuele voortgang. Breng tegelijk Emby terug. Is de app gestopt, kies dan direct **Start** en controleer **Running**. Kies zo nodig **Weer koppelen** op de oorspronkelijke kaart. Controleer recent gezond contact en de ingestelde verversing. Meld je op de gewone Emby-client aan en speel als enige testsessie een titel af. Controleer dat MediaGuard juist die sessie als reden voor de kijkpauze toont en nieuwe encodes wachten. **Zodra Emby draait en gekoppeld is en de gewone aanmelding, het afspelen en de Emby-kijkpauze werken, mag het huishouden direct weer gewoon kijken.** Noteer het tijdstip van vrijgave. [MediaGuard-koppeling][mgscherm] · [Schermteksten][mgtekst]
    - **Proefstatus en hervatting van taken.** Vergelijk na de Emby-vrijgave de Emby-kijkgegevens en rechten per gebruiker en soort met de stand vóór de stop. Houd rekening met de terugkeerproef en het kijkgebruik sinds de vrijgave. Lees de laatste Jelly Leon-standen via de afgeschermde route terug en vergelijk ze met de verwachte waarden. Vergelijk de open en afgeronde MediaGuard-taken, werkgegevens en het journaal met de herstelset uit punt 3. Bij ontbrekende of afwijkende Jelly Leon- of MediaGuard-gegevens blijft de proef open en blijven de voortgangswijzigende taken gepauzeerd. Gewoon Emby-gebruik blijft vrij. Hervat de taken pas na de gecontroleerde terugkeer, met overeenkomende gegevens, werkende kijkpauze en minstens 20% vrije poolruimte. Laat nieuwe encodes bij een actieve kijksessie wachten.

**Uitfasering van Emby is een afzonderlijke, latere opdracht (niet in versie 1).** Die vraagt een eigen besluit over beschikbaarheid en bewijs dat de volledige app met haar gegevens kan worden hersteld. Met deze proef vink je uitsluitend de proefstop af. Bewaar de app, haar opslag, de laatste Emby-snapshot en het exportarchief.

### Wat je terugmeldt

| Controlepunt | Ja/nee/open en datum | Bewijs zonder privégegevens |
|---|---|---|
| 1. Laatste delta ná de laatste Emby-afspeling, nul Emby-sessies | | |
| 2. Eindrapport, SHA-256, overstap toegestaan. Per gebruiker en soort leesroute tijdens stop en bij terugval, geteste vindplaats bij ieder verschilakkoord. Gedateerde uitvalproef uit 12 punt 4 en laatste Jelly Leon-stand via dezelfde route teruggelezen | | |
| 3. Verse snapshots en tijdstip, bescherming uit 02 en ruimte tegenover 20%. Stabiele taakpauze en afgerond lopend werk. Datum, versie en dekking van de actuele MediaGuard-herstelset, open/afgeronde taken, werkgegevens, journaal en teruggevonden originelen op geïsoleerd doel | | |
| 4. Archief lokaal én in back-up, hash klopt, inleesproef op een lege kopie | | |
| 5. Vier gedateerde controles, afzonderlijk passend bewijs voor Start en Weer koppelen, nieuwe taken wachten, lopend werk afgerond, nul sessies vóór ontkoppelen. Daarna alleen Jelly Leon gevolgd, sessiegebonden kijkpauze en voortgang gecontroleerd | | |
| 6. Proefstop en gecontroleerde terugkeer | | Verse Emby-nulmeting direct vóór de stop, begin, einde, duur en eventueel gemis. Taakpauze gedurende de hele proef. Tijdstippen van kopieverversingen en teruggelezen standen. Tijdstip Emby-vrijgave na controle van draaien, koppeling, gewone aanmelding, afspelen en kijkpauze. Uitkomst gegevensvergelijking, open afwijkingen en eventuele hervatting van MediaGuard na de proef. |

Vul ook de regel Bewijs per werkelijk uitgevoerde I-stap in. Een datum op een voornemen geldt niet als uitvoerdatum.

### Wat daarna gecontroleerd wordt

De regisseur vergelijkt de vijf vooraf gedateerde ‘ja’-antwoorden met de nulmeting op het stopmoment, de uitvalproef uit 12, het leesbewijs per gebruiker, de herimport en het afzonderlijke herstelbewijs voor MediaGuard. Voor het zesde ‘ja’ controleert hij minstens 72 aaneengesloten uren tussen stop en herstart, de ononderbroken taakpauze, de kopieverversingen en de teruggelezen standen. Hij controleert de onderbouwing van de Emby-vrijgave en daarna de uitkomst van de gegevensvergelijking. Vergelijk ook de gedateerde spelerproef met het afzonderlijke verslag van herstart en herkoppeling.

### Welke rijen daarna van Geblokkeerd af mogen

Bij **APP-02, I26-26-02, I26-26-06 en JLT-74** mag je uitsluitend het proefstopdeel afvinken na zes onderbouwde punten, inclusief de terugkeer. Houd de proef bij een ontbrekende controle of voortijdig afbreken open. Aanvullende eisen per rij houden hun eigen bewijs en status. De afzonderlijke duurproef in 14 meet minstens 72 uur mét draaiende Emby en levert uitsluitend bewijs voor 14.

### Stop als

Iemand kijkt op het stopmoment nog op Emby of mist tijdens de proef iets, een vereist ‘ja’ ontbreekt, een leesroute onbereikbaar is of bewijs ontbreekt voor de uitvalproef, herstart, herkoppeling, herimport of de actuele MediaGuard-herstelset. Stop ook bij een onbekende sessiestand, een onveilige taakpauze, onvolledig afgerond werk, een weggevallen kijkpauze of een afwijking in kijkgegevens of voortgang. Laat Emby draaien en gekoppeld of herstel dat onmiddellijk via punt 6. Geef gewoon kijken vrij zodra de Emby-controles van punt 6 kloppen. Bij afwijkende gegevens in Jelly Leon of MediaGuard blijft de proef open en houd je de voortgangswijzigende taken gepauzeerd. Bewaar de actuele gegevens en de herstelpunten. Kies in **Apps** op Emby, een bestaande Jellyfin en MediaGuard nooit **Roll Back** of **Update**. Kies nooit **Rollback** en wijzig nooit rechten op Emby-, MediaGuard- of mediadatasets of een bovenliggende dataset.

## N-P6-14 - Duurproef, herstel op een tweede omgeving en productieacceptatie

### Voor je begint

Leg vast welke onderdelen je accepteert en welke bewust openblijven. Kies je meetpunten en grenzen vóór de proef. Gebruik 04 als nulmeting. Leg bijvoorbeeld het aantal onverwachte appherstarts, kritieke meldingen, CPU/geheugen versus manifest en onderbrekingen bij afspelen vast. Bewaar de huidige herstelpunten. [Fasering en gates][fasering]

### Wat je doet

1. Laat het platform **minstens 72 uur** bij normaal gebruik draaien, inclusief Emby. Verander in die periode geen instellingen. Noteer begin, einde en bijzonderheden. Dit is een aparte duurproef. Na 13 begint deze meting pas wanneer Emby weer draait, gekoppeld is en de kijkpauze is gecontroleerd. [I07 §2, stap 4–5][I07] · [I08 §2, stap 3–5][I08]
2. Lees na afloop in de Hub en de bewaking je meetpunten af. Vergelijk met de nulmeting, de gekozen grenzen en de gebruikerservaring bij afspelen. De uitvalproef van de hele NAS (EX23) blijft open zolang deze Emby zou onderbreken. [I01 §2, stap 8][I01] · [I07 §2, stap 4–5][I07]
3. Heb je een tweede, afgeschermde omgeving, herstel dan de Hub, my_house en de aanmelding uit back-up naar de lege doelen daar (EX50). Houd de oude installatie actief. Gebruik op de tweede omgeving een ander adres en test uitsluitend met geïsoleerde koppelingen, zonder tweede actieve worker voor huisapparaten. Controleer data, autorisaties en of de juiste koppelingen na de adreswijziging werken. Vergelijk duur en gegevensverlies met D16. Zonder tweede omgeving laat je dit deel open. [I02 §2, stap 3, 5 en 8][I02] · [I05 §2, stap 8][I05] · [I09 §2, stap 6][I09]
4. Loop je eigen Excel na. Bepaal per simulatorrij of je het onderliggende simulatierapport aanvaardt of eerst zelf een proef nodig hebt. Leg je persoonlijke keuze bij het juiste bewijs vast. Besluit zelf over productieacceptatie, met datum en een lijst van bewust openstaande zaken. [Werkboek][excel] · [Fasering en acceptatie][fasering]

### Wat je terugmeldt

| Gegeven | Jouw terugmelding |
|---|---|
| Bewijs per betrokken I-stap, begin, einde en aantal uren | |
| Per meetpunt nulmeting, grens, eindmeting en gehaald/niet gehaald | |
| Tweede omgeving, per dienst gegevens/aanmelding/koppeling, herstelduur en afwijkingen | |
| Aantal zelf afgevinkte rijen per blad, bewust open rijen met reden, jouw acceptatiebesluit en datum | |

### Wat daarna gecontroleerd wordt

De regisseur controleert de 72 uur, de vergelijking per meetpunt en de hersteltellingen. Hij vergelijkt de handmatige keuzes met de lijst `handmatig_afgevinkt` en controleert dat de registraties in EVIDENCE bij hun bewijs passen. Elke open rij houdt een concrete reden en het bijbehorende onderdeel.

### Welke rijen daarna van Geblokkeerd af mogen

EX50, B01-012, B06-008 en B12-007 alleen bij passend werkelijk herstel op een tweede omgeving. EX23 vraagt een werkelijk, apart gepland uitvalmoment dat verenigbaar is met de beschikbaarheidseis. De faseregel P6 kan op **Bezig** met de lijst van uitgevoerde onderdelen. Ontbrekende Apple-proeven en andere open punten houden hun reden.

### Stop als

De 72 uur niet zijn gehaald, een meetpunt buiten de afgesproken grens ligt of op de andere omgeving gegevens, rechten of koppelingen ontbreken. Houd de oude installatie in gebruik. Isoleer het herstelde proefdoel, bewaar de bevindingen en stel acceptatie uit tot je het resultaat opnieuw hebt beoordeeld.

## Zo vink je zelf af

1. Open in de repo **ai-server-manager** het bestand `docs/platform-v2/08_EXCEL/TrueNAS_V2_Uitvoering_en_Afvinken.xlsx`. Zoek op de rij-ID uit je terugmelding en vergelijk het bewijs met de uitkomst. [Excel-werkboek][excel]
2. Alleen jij kiest **Gereed** bij een werkpakket of **Geslaagd** bij een test. Zet die waarde rechtstreeks in de statuscel van de betreffende rij. Met een ontbrekende of afwijkende proef houd je de reden bij de rij. Een besluit zoals D07 volgt de status in **Onboarding**.
3. De volgende bijwerkronde bewaart de letterlijke, handmatig gekozen eindstatus en vermeldt rij en blad onder `handmatig_afgevinkt`. Staat het bewijs op **Geblokkeerd** of **Mislukt**, dan verschijnt een waarschuwing en blijft jouw keuze staan. Controleer die rij zelf. Een formule in de statuscel telt niet als handmatige keuze. De eindstatus die jij in Excel kiest komt niet in EVIDENCE. [Werking van het Excel-gereedschap][exceltool]

## Bronnen per project

De installatiebladen I01 t/m I26 staan in de repo ai-server-manager onder `docs/platform-v2/03_INSTALLATIE/`. Voor bronnen uit andere repo’s kom je bij het juiste bestand in deze tabel. Open in de webweergave de genoemde repo en zoek op het bestandspad. Gebruik **Open lokaal** als de projectrepo’s naast elkaar staan en je het draaiboek vanuit de overdrachtsmap leest.

| Repo | Bestand en eventuele paragraaf | Lokale projectmap |
|---|---|---|
| <a name="bron-winkel"></a>`appstore-en-fork` | `deploy/truenas/CUSTOM_APP.md` | [Open lokaal](../../../../appstore-en-fork/deploy/truenas/CUSTOM_APP.md) |
| <a name="bron-hch"></a>`home-control-hub` | `deploy/truenas/CUSTOM_APP.md` | [Open lokaal](../../../../home-control-hub/deploy/truenas/CUSTOM_APP.md) |
| <a name="bron-nodered"></a>`home-control-hub` | `deploy/truenas/NODE_RED_CUSTOM_APP.md` | [Open lokaal](../../../../home-control-hub/deploy/truenas/NODE_RED_CUSTOM_APP.md) |
| <a name="bron-jelly"></a>`jelly-leon` | `deploy/truenas/CUSTOM_APP.md` | [Open lokaal](../../../../jelly-leon/deploy/truenas/CUSTOM_APP.md) |
| <a name="bron-matrix"></a>`jelly-leon` | `docs/platform-v2/CLIENT_COMPAT_MATRIX.md` | [Open lokaal](../../../../jelly-leon/docs/platform-v2/CLIENT_COMPAT_MATRIX.md) |
| <a name="bron-overname"></a>`jelly-leon` | `docs/platform-v2/OVERNAME_EMBY.md` | [Open lokaal](../../../../jelly-leon/docs/platform-v2/OVERNAME_EMBY.md) |
| <a name="bron-controlelijst"></a>`jelly-leon` | `docs/platform-v2/OVERNAME_EMBY.md` — Oude controlelijst “Emby verwijderen”, uitsluitend achtergrond en bewijsbron | [Oude bewijsbron](../../../../jelly-leon/docs/platform-v2/OVERNAME_EMBY.md#controlelijst-emby-verwijderen-u-voert-dit-zelf-uit--geen-enkele-agent-verwijdert-emby) · [Uitvoering in N-P6-13, punten 1–6][proefpunten-emby] |
| <a name="bron-modules"></a>`jelly-leon` | `plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Configuration/configPage.html` | [Open lokaal](../../../../jelly-leon/plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Configuration/configPage.html) |
| <a name="bron-clients"></a>`jelly-leon-clients` | `README.md` | [Open lokaal](../../../../jelly-leon-clients/README.md) |
| <a name="bron-platform"></a>`jelly-leon-platform` | `deploy/truenas/CUSTOM_APP.md` | [Open lokaal](../../../../jelly-leon-platform/deploy/truenas/CUSTOM_APP.md) |
| <a name="bron-appacties"></a>`jelly-leon-platform` | `docs/platform-v2/TRUENAS_APP_API.md` — §4, Bijwerken, terugzetten, upgraden, verwijderen | [Open lokaal](../../../../jelly-leon-platform/docs/platform-v2/TRUENAS_APP_API.md#4-bijwerken-terugzetten-upgraden-verwijderen) |
| <a name="bron-monitoren"></a>`jelly-leon-platform` | `install/manifests/README.md` | [Open lokaal](../../../../jelly-leon-platform/install/manifests/README.md) |
| <a name="bron-installatie"></a>`jelly-leon-platform` | `install/truenas/INSTALLATIE.md` | [Open lokaal](../../../../jelly-leon-platform/install/truenas/INSTALLATIE.md) |
| <a name="bron-webclient"></a>`jelly-leon-web` | `deploy/truenas/CUSTOM_APP.md` | [Open lokaal](../../../../jelly-leon-web/deploy/truenas/CUSTOM_APP.md) |
| <a name="bron-mgscherm"></a>`media-guard-ultimate` | `apps/web/components/mediaserver/mediaserver-tab.tsx` | [Open lokaal](../../../../media-guard-ultimate/apps/web/components/mediaserver/mediaserver-tab.tsx) |
| <a name="bron-mgtekst"></a>`media-guard-ultimate` | `apps/web/lib/i18n/messages/mediaserver.ts` | [Open lokaal](../../../../media-guard-ultimate/apps/web/lib/i18n/messages/mediaserver.ts) |
| <a name="bron-mg"></a>`media-guard-ultimate` | `deploy/truenas/CUSTOM_APP.md` | [Open lokaal](../../../../media-guard-ultimate/deploy/truenas/CUSTOM_APP.md) |
| <a name="bron-mgterug"></a>`media-guard-ultimate` | `deploy/truenas/CUSTOM_APP.md` — Terugzetten na een mislukte upgrade (alleen als achtergrond, sla stap 2 over) | [Open lokaal](../../../../media-guard-ultimate/deploy/truenas/CUSTOM_APP.md#terugzetten-na-een-mislukte-upgrade) |
| <a name="bron-mso"></a>`media-source-optimizer` | `deploy/truenas/CUSTOM_APP.md` | [Open lokaal](../../../../media-source-optimizer/deploy/truenas/CUSTOM_APP.md) |
| <a name="bron-msoherstel"></a>`media-source-optimizer` | `docs/TRUENAS_CUSTOM_APP.md` — Terugdraaien via TrueNAS | [Open lokaal](../../../../media-source-optimizer/docs/TRUENAS_CUSTOM_APP.md#terugdraaien-via-truenas) |
| <a name="bron-huis"></a>`my_house` | `deploy/truenas/CUSTOM_APP.md` | [Open lokaal](../../../../my_house/deploy/truenas/CUSTOM_APP.md) |
| <a name="bron-huisherstel"></a>`my_house` | `docs/onderhoud.md` — Offline terugvalkopie voorbereiden | [Open lokaal](../../../../my_house/docs/onderhoud.md#offline-terugvalkopie-voorbereiden) |
| <a name="bron-zoeken"></a>`zoeken-en-persoonlijke-ai` | `deploy/truenas/CUSTOM_APP.md` | [Open lokaal](../../../../zoeken-en-persoonlijke-ai/deploy/truenas/CUSTOM_APP.md) |

[invulblad]: ../06_TEMPLATES/INSTALLATIE_INVULBLAD.md
[register]: ../04_BESTAANDE_APPS/APP_REGISTER.md
[contract]: ../PLATFORM_CONTRACTEN.md#22-custom-app-realiteit-gemeten-in-de-bronnen-niet-op-een-echte-nas
[installatie]: #bron-installatie
[hub]: ../../../deploy/truenas/CUSTOM_APP.md
[platform]: #bron-platform
[hch]: #bron-hch
[winkel]: #bron-winkel
[mg]: #bron-mg
[mso]: #bron-mso
[huis]: #bron-huis
[huisherstel]: #bron-huisherstel
[zoeken]: #bron-zoeken
[jelly]: #bron-jelly
[monitoren]: #bron-monitoren
[nodered]: #bron-nodered
[webclient]: #bron-webclient
[clients]: #bron-clients
[matrix]: #bron-matrix
[overname]: #bron-overname
[cutover]: ../02_BOUWPLANNEN/B03_FASERING.md
[modules]: #bron-modules
[mgscherm]: #bron-mgscherm
[mgtekst]: #bron-mgtekst
[fasering]: ../01_ARCHITECTUUR/06_FASERING_EN_GATES.md
[excel]: ../08_EXCEL/TrueNAS_V2_Uitvoering_en_Afvinken.xlsx
[exceltool]: ../../../tools/excel/update_excel.py
[I01]: ../03_INSTALLATIE/I01_TRUENAS_BASIS.md#2-stappen-in-uitvoeringsvolgorde
[I02]: ../03_INSTALLATIE/I02_BACKUP_EN_RESTORE.md#2-stappen-in-uitvoeringsvolgorde
[snapshotbescherming]: #snapshotbescherming
[I03]: ../03_INSTALLATIE/I03_MEDIAGUARD.md#2-stappen-in-uitvoeringsvolgorde
[I04]: ../03_INSTALLATIE/I04_MEDIA_SOURCE_OPTIMIZER.md#2-stappen-in-uitvoeringsvolgorde
[I05]: ../03_INSTALLATIE/I05_MY_HOUSE.md#2-stappen-in-uitvoeringsvolgorde
[I06]: ../03_INSTALLATIE/I06_JELLYFIN.md#2-stappen-in-uitvoeringsvolgorde
[I07]: ../03_INSTALLATIE/I07_BESZEL.md#2-stappen-in-uitvoeringsvolgorde
[I08]: ../03_INSTALLATIE/I08_UPTIME_KUMA.md#2-stappen-in-uitvoeringsvolgorde
[I09]: ../03_INSTALLATIE/I09_AUTHENTIK.md#2-stappen-in-uitvoeringsvolgorde
[I10]: ../03_INSTALLATIE/I10_NODE_RED.md#2-stappen-in-uitvoeringsvolgorde
[I11]: ../03_INSTALLATIE/I11_NETALERTX.md#2-stappen-in-uitvoeringsvolgorde
[I12]: ../03_INSTALLATIE/I12_ADGUARD_HOME.md#2-stappen-in-uitvoeringsvolgorde
[I13]: ../03_INSTALLATIE/I13_GOTIFY.md#2-stappen-in-uitvoeringsvolgorde
[I14]: ../03_INSTALLATIE/I14_PGVECTOR.md#2-stappen-in-uitvoeringsvolgorde
[I15]: ../03_INSTALLATIE/I15_IMMICH.md#2-stappen-in-uitvoeringsvolgorde
[I16]: ../03_INSTALLATIE/I16_PROWLARR.md#2-stappen-in-uitvoeringsvolgorde
[I17]: ../03_INSTALLATIE/I17_SABNZBD.md#2-stappen-in-uitvoeringsvolgorde
[I18]: ../03_INSTALLATIE/I18_QBITTORRENT.md#2-stappen-in-uitvoeringsvolgorde
[I19]: ../03_INSTALLATIE/I19_SEERR.md#2-stappen-in-uitvoeringsvolgorde
[I20]: ../03_INSTALLATIE/I20_BAZARR.md#2-stappen-in-uitvoeringsvolgorde
[I21]: ../03_INSTALLATIE/I21_TAILSCALE_CLOUDFLARED.md#2-stappen-in-uitvoeringsvolgorde
[I22]: ../03_INSTALLATIE/I22_NAVIDROME_OPT.md#2-stappen-in-uitvoeringsvolgorde
[I23]: ../03_INSTALLATIE/I23_HOME_CONTROL_HUB.md#2-stappen-in-uitvoeringsvolgorde
[I24]: ../03_INSTALLATIE/I24_UNIVERSELE_MEDIASERVER.md#2-stappen-in-uitvoeringsvolgorde
[I25]: ../03_INSTALLATIE/I25_SEARCH.md#2-stappen-in-uitvoeringsvolgorde
[I26]: ../03_INSTALLATIE/I26_BESTAANDE_APPS.md#2-stappen-in-uitvoeringsvolgorde
[jltesten]: ../08_EXCEL/b03/testen.json
[msoherstel]: #bron-msoherstel
[bestaandeapps]: ../PLATFORM_CONTRACTEN.md#23-bestaande-apps-mediaguard-mso-my_house-jellyfinjelly-leon-emby
[appacties]: #bron-appacties
[mgterug]: #bron-mgterug
[controlelijst]: #bron-controlelijst
[proefpunten-emby]: #proefpunten-emby
