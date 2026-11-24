# Hub-ontwerp voor P2

## 0. Leeswijzer

Dit is het schermontwerp voor S-P2-170 t/m S-P2-200. Een operator kan een wijziging voorbereiden, een beheerder kan de precieze wijziging goedkeuren en beiden kunnen de uitkomst teruglezen. Dezelfde preview bedient apps, incidenten en voorstellen van andere diensten. Een app bijwerken begint bijvoorbeeld bij **Versies**, loopt via **Actie-preview** en **Goedkeuring** en eindigt bij **Uitvoering**. Bij een dichtstaande back-upgate leidt de uitleg naar **Back-ups**.

| Bouwstap | Onderdeel van de Hub |
| --- | --- |
| S-P2-170 | Actie-preview, goedkeuringen, uitvoering en risicobeleid |
| S-P2-180 | Versies, acties, catalogus, installatiewizard en verwijderen |
| S-P2-190 | Back-ups, herstelpunten, hersteltests en de status van automatiseringen |
| S-P2-200 | AI, beheerstatus in Apps en het monitorplan in Instellingen → Monitoring |

De bron voor methoden en paden is `docs/openapi/hub-api.openapi.json`. Waar een antwoord als vrij object is beschreven, bepaalt de Hub-router welke velden de browser kan gebruiken. De paragraaf **Wat de backendbouwer nog mist** noemt de ontbrekende gegevens en de bijbehorende bouwstap. In de schermteksten staat ‹tijd› voor de oorspronkelijke meettijd en ‹doel› voor het gecontroleerde doel van dit voorstel.

## 1. Schil, componenten en bediening

De schermen gebruiken de bestaande AppSchil, PageHeader, rolmelding, focusring en thematokens van de Hub. De basis is Peil op Tailwind 4, shadcn/ui en lucide. `apps/web/src/components` levert onder meer `ResponsiveList`, `Freshness`, `ErrorPanel`, `NotYetAvailable`, `KopieerVeld` en `Aftellen`. Voor de overige Peil-componenten geldt `design/ontwerptaal/COMPONENTEN.md`, met name ‘15. ActiePreview’ en ‘16. GoedkeuringsPagina’. De schermen volgen de patronen in `docs/platform-v2/ONTWERPTAAL.md`, ‘8. Componentenbibliotheek’, ‘9. Patronen per schermtype’ en ‘11. Nederlandse microcopy’.

| Patroon in de schermparagrafen | 320 px | 768 px | 1440 px |
| --- | --- | --- | --- |
| Lijst of matrix | Eén kaart per rij, kop gevolgd door benoemde waarden. Filters in een sheet. | Tabel met kolom- en rijkoppen. Een rijlink heeft een herkenbare naam. | Zelfde tabel. Bij lijst/detail kan het geselecteerde detail ernaast, met `aria-current` op de rij. |
| Detail of infopaneel | Eén kolom. Kop, feiten, bewijs, daarna de vervolghandeling. Codes en labels lopen om. | Feiten in een `dl`. Dezelfde lees- en tabvolgorde. | Verwante details naast elkaar. Een melding over een ontbrekende functie blijft één kort paneel. |
| Preview of goedkeuring | Eigen pagina. Was en Wordt onder elkaar per veld. Knoppen over de volle breedte. | Diff als tabel. Veiligheid en herstel direct onder de diff. | Veiligheid naast de diff. R2 en R3 houden een eigen goedkeuringspagina. |
| Wizard | Eén stap per pagina met stapnummer, velden en actiebalk boven de ondernavigatie. | Dezelfde stap en een compacte stapindicator. | Stapnamen zichtbaar, actiebalk in de leesvolgorde na de velden. |

In licht en donker gelden dezelfde betekenissen en dezelfde inhoud. Gebruik `card` en `foreground` voor inhoud, `muted` voor toelichting, `unknown` en `stale-ink` voor onzekere of oude gegevens, `gate` voor voorwaarden en `risk-0` t/m `risk-3` voor risico. Icoon, woord en vorm dragen steeds de betekenis. Iedere pagina begint met de skiplink. Bij navigatie krijgt de h1 focus, bij een veldfout de foutsamenvatting met links naar de velden. Tab volgt de leesvolgorde, echte tabs reageren op pijltjes, Home en End. De focus blijft zichtbaar boven vaste balken. Alle interactieve doelen zijn minstens 44 px.

## 2. Toestanden en zichtbaarheid op ieder scherm

| Toestand | Wat verschijnt en wat de gebruiker kan doen |
| --- | --- |
| Laden | C-18 toont bij de eerste lezing een skelet en een voorleesbare taak zoals ‘Herstelpunten ophalen…’. Bij verversen blijft de vorige stand leesbaar met bron en tijd (C-06). |
| Leeg | C-17 benoemt wat ontbreekt na een verse, volledige en toegestane lezing. Een deelpagina, filter of weggevallen bron rechtvaardigt uitsluitend een uitspraak over dat deel. |
| Storing | C-14 benoemt het getroffen onderdeel, een bekende foutcode in Nederlandse woorden en ‘Opnieuw proberen’ voor de lezing. Een onbekende code krijgt een vaste tekst. Een geldig trace-ID mag worden gekopieerd. |
| Offline | C-16 meldt ‘Je bent offline. Je kunt de laatst bekende stand bekijken.’ Alleen eerder toegestane gegevens blijven leesbaar. Schrijfacties en verversen wachten op een nieuwe, geslaagde lezing. Er komt geen opdracht in een wachtrij. Uitval van één bron raakt alleen haar onderdeel. |
| Onbekend of verouderd | Zonder meting ‘Onbekend — nog nooit gemeten’. Bij E15 krijgen kaart of rij een gestippelde rand, een gearceerd vak ‘Laatst bekend · ‹tijd›’ en de badge **Verouderd · stand van ‹tijd›**. Een eerdere storing of beperking houdt het eigen woord met ‘stand van ‹tijd›’. Oude positieve status, vinkjes en groene waarden verdwijnen. Bron, **Bijgewerkt** en **Geprobeerd** blijven onderscheiden. Een verversing van de pagina verjongt de bron niet. |
| Geblokkeerd of geen recht | Een voorwaarde krijgt C-11 met slot, zichtbare reden en een bruikbare vervolgstap. Een geblokkeerde knop krijgt `aria-disabled` en `aria-describedby` naar de reden en doet ook met Enter of Spatie niets. Bij ontbrekend schrijfrecht verschijnt de rolmelding C-49 zonder de mutatieknoppen. Bij 403 op een lezing verdwijnen ook eerder getoonde gegevens van dat onderdeel. |
| Verlopen | Bij 401 verdwijnen private gegevens en invoer uit beeld. ‘Je sessie is verlopen. Meld je opnieuw aan.’ Een verstreken voorstel, goedkeuring, plan of bewijs heeft daarnaast de eigen vervaltekst bij het scherm. Een nieuwe sessie hervat geen wijziging. |
| Nog niet beschikbaar | Ontbreekt de leesroute, dan toont C-12 onmiddellijk ‘Nog niet beschikbaar’, met de betreffende functie en de bron die die functie moet leveren. Geen laadlus, nulstand, demonstratierecords of bedienbaar formulier. Ontbreekt één veld, dan krijgt alleen dat onderdeel deze melding. Bij `capability_unavailable` noemt C-12 de bron en de aangeroepen route. |

De wachtlijst en de overige leeslijsten gebruiken het tijdstip van de bron. Na vijftien minuten vervalt de leegmelding. Een ontbrekend, ongeldig of toekomstig tijdstip geeft een onbekende stand. Bij meerdere pagina’s bepaalt de oudste lezing de versheid van de selectie. Kortere geldigheidsgrenzen per meting blijven gelden.

**Zichtbare gegevens.** Elk scherm gebruikt een positieve veldlijst. Vertaal bekende typen, status- en redencodes naar vaste Nederlandse zinnen. Geef alleen gevalideerde identificaties, tijden, eenheden en getypeerde meetwaarden door aan de weergave. Vrije redenen uit voorstellen, upstreamfouten, logregels, prompts, notities, flowinhoud, willekeurige URL's en ongestructureerde JSON blijven buiten DOM, toegankelijke naam en klembord. Een citaat kan bestaan uit een vast gebeurtenistype, bron en meettijd. Geheimen krijgen alleen hun veldnaam. Een verplichte diff-regel waarvan de inhoud niet veilig en volledig kan worden uitgelegd, blokkeert de goedkeuring met ‘Deze wijziging kan nog niet veilig worden weergegeven.’

**Rechten.** `GET /api/v1/auth/me` levert de sessierol. De server beslist bij elke afzonderlijke handeling. Een kijker leest de toegestane overzichten, een operator stelt getypeerde acties voor en alleen een beheerder keurt R2/R3 goed. De kindschil houdt Home, Kijken, Zoeken en Ik. Een administratieve deep link verleent geen recht. Een mutatie gebruikt de bestaande sessie- en CSRF-afhandeling en dezelfde `Idempotency-Key` bij herhaling van hetzelfde verzoek. Bij een onzekere uitkomst leest de Hub eerst de stand terug.

## S-061 · Actie-preview

**Bediening.** Vanuit de aanroepende app of het incident controleert de gebruiker één voorstel. Volg `design/ontwerptaal/prototypes/appdetail.html`, onderdeel ‘Waarom R2?’. C-19 toont doel, aanvragertype, uitvoerder, reikwijdte, verwachte onderbreking, vereiste back-up en terugval. C-20 toont Was/Wordt en de tekens voor gewijzigd, toegevoegd en verwijderd. C-08 legt de klasse van het beleid uit met `rule_ids`. Een afwijkende, geldige `risk_claim` staat apart. C-22 toont de vervaltijd.

**Bron.** `POST /api/v1/actions` maakt het voorstel en de gebonden preview. `GET /api/v1/actions/{request_id}` levert onder meer `preview.huidig`, `preview.wijziging`, `risk_class`, `blokkades`, `uitvoerder`, `geldig_tot` en de drie bindingsvelden. Toon geplande stappen als verwachtingen. Ontbrekende impact of downtime krijgt ‘Onbekend’. R1 ‘Uitvoeren’ vraagt een bevestiging met focus op Annuleren. Bij R2/R3 leidt ‘Goedkeuring aanvragen’ naar het al aangemaakte verzoek in S-062/S-063.

**Toestanden en toets.** Zonder selectie ‘Kies een voorstel’. Tijdens laden ‘Voorstel ophalen…’. Bij 422 voor een onbekende actie ‘Deze actie staat niet in de lijst met toegestane acties’. Zonder droogtestroute krijgt ‘Simuleren’ C-12 met reden. Offline of verouderd geldt E15 voor de diff en vervalt de bediening. Een dichte gate toont de ontbrekende voorwaarde. Na `geldig_tot` volgt ‘Voorstel verlopen. Vraag een nieuw voorstel aan.’ Toets dat een geblokkeerd voorstel met het toetsenbord leesbaar blijft en geen uitvoering start.

## S-062 · Goedkeuringen

**Bediening.** De teller in kopbalk en AI-navigatie opent dezelfde lijst. C-34/C-35 tonen doel, aanvragertype, C-08, status en C-22. Tab loopt van filter via één link per verzoek naar ‘Meer laden’. De detailpagina is op smal scherm een aparte bestemming.

**Bron.** `GET /api/v1/actions?status=wacht_op_goedkeuring` met `items`, `next_cursor` en `bijgewerkt_op`. `status=open` omvat ook al goedgekeurde en direct uitvoerbare voorstellen. De teller gebruikt uitsluitend de wachtlijst. Zolang er een vervolgcursor is, toon ‘Ten minste ‹aantal›’ of laat de exacte teller weg. Een detail opent `GET /api/v1/actions/{request_id}`.

**Toestanden en toets.** ‘Goedkeuringen ophalen…’, daarna alleen bij een verse lege wachtlijst ‘Geen openstaande goedkeuringen’. Bij storing ‘Goedkeuringen ophalen mislukt’. Offline of verouderd krijgen lijst én teller E15. Een verlopen rij verwijst naar het vervallen detail. Toon een weigering of blokkade met reden als de gebruiker de historie bekijkt. Toets dat een reeds goedgekeurd verzoek nergens als wachtend wordt meegeteld.

## S-063 · Goedkeuring beoordelen

**Bediening.** Volg `design/ontwerptaal/prototypes/goedkeuring-r3.html`, ‘Stap 2 van 2’. C-21 toont de volledige preview, het herstelpunt en met C-15 de gebonden `preview_hash`, `resource_etag` en `policy_hash`. R2 heeft één beslisstap. Bij R3 volgt een tweede pagina/stap met gevolgen en ‘Typ ‹doel› om te bevestigen’. Annuleren staat vóór de gevaarknop. Bij een onjuiste naam blijft die `aria-disabled` met ‘Typ eerst de exacte naam van het doel’. Bij weigeren kiest de beheerder een vaste reden.

**Bron.** `GET /api/v1/actions/{request_id}`, `POST /api/v1/actions/{request_id}/approve` met precies de drie getoonde bindingsvelden, of `POST /api/v1/actions/{request_id}/reject` met `reden`. Gebruik `goedkeuring.backup_checkpoint_id` zodra die er is. Een lijst met mogelijke herstelpunten bewijst nog geen binding vóór goedkeuring. Bij vereiste back-up zonder aantoonbaar gebonden herstelpunt blijft de goedkeuring geblokkeerd. De looptijd van de aanvraag (`geldig_tot`) en die van de eenmalige goedkeuring (`goedkeuring.expires_at`, maximaal 15 minuten) zijn apart zichtbaar.

**Toestanden en toets.** ‘Goedkeuring ophalen…’, 404 ‘Dit verzoek is niet gevonden’. Zonder recht ‘Alleen een beheerder kan dit goedkeuren.’ Bij verlopen tijd of drift vervallen beide beslisknoppen, bijvoorbeeld ‘Goedkeuring vervallen: de appversie is gewijzigd na de preview. Vraag een nieuw voorstel aan.’ Offline of verouderd krijgt juist de te beoordelen diff E15. C-22 kondigt 5 minuten, 1 minuut en verlopen aan. Toets een typefout, dubbel drukken en wijziging van een gebonden veld. Elk vraagt respectievelijk de juiste naam, idempotente verwerking of een nieuwe preview.

## S-064 · Uitvoering

**Bediening.** C-23 toont een geordende tijdlijn met tijd, voor/na-controle en uitkomst. Een operator mag R1 uitvoeren. Voor R2/R3 voert alleen de beheerder uit na een geldige goedkeuring. De bevestiging stuurt `POST /api/v1/actions/{request_id}/execute`. Volg `GET /api/v1/actions/{request_id}` met `status`, `gestart_op`, `uitgevoerd_op` en de getypeerde velden in `resultaat`. Toon duur alleen bij twee tijdstippen, de voor/na-hash en een incidentlink alleen waar bewijs voor is.

**Toestanden en toets.** Voor de start ‘Nog niet uitgevoerd’. Bij laden of een lopende opdracht ‘Uitkomst ophalen…’ of ‘Uitvoering bezig’. Bij teruggelezen succes ‘Uitgevoerd en gecontroleerd’, bij `afwijking` ‘Gestopt: afwijking na uitvoering’. Na een verbroken verbinding geldt E15 op de laatste stap. ‘Uitkomst onbekend’ biedt de operator `POST /api/v1/actions/{request_id}/reconcile` om het journaal te lezen. Een nieuwe uitvoering blijft uit. Een verlopen goedkeuring verwijst naar S-063. Afbreken per verzoek ontbreekt en krijgt C-12 met reden. Toets dat een time-out nooit een successtap of een tweede uitvoering oplevert.

## S-066 · Risicobeleid

**Bediening en bron.** De gebruiker zoekt een actie op in `GET /api/v1/policy`. C-34 toont actie, uitvoerder, basisklasse, klasse voor kritieke of Custom Apps, back-upvereiste en wachttijd. C-08 licht de risicoklasse toe. C-13 toont verboden en beschermde acties met vaste uitleg. De revisie is `policy_hash` in C-15. ‘Het beleid kan niet door de AI worden gewijzigd.’ Er is uitsluitend leesbediening.

**Toestanden en toets.** ‘Beleid ophalen…’ of bij een leeg zoekresultaat ‘Geen regel gevonden voor dit filter’. Bij een onleesbare of lege beleidsbron ‘Risicobeleid onbekend’. Offline of verouderd krijgt het hele regeloverzicht inclusief hash E15 en vormt het geen basis voor een nieuwe actie. Een verboden actie toont ‘Wordt nooit uitgevoerd’. Verloopt de sessie, dan verdwijnt de lijst. Toets dat ook de beheerder uitsluitend kan zoeken, lezen en de openbare hash kopiëren.

## S-044 · Appdetail, tab Versies

**Bediening en bron.** De tab **Versies** in het bestaande appdetail toont via `GET /api/v1/apps/{app_uuid}` de huidige `versie`, `image.digest`, `image_historie` en eventueel `appstore.laatste_versie` met eigen meettijd. C-15 maakt de digest leesbaar en kopieerbaar, C-34 toont de geschiedenis. ‘Bijwerken’ of ‘Terugzetten’ opent S-061 voor `app.update` of `app.rollback` via `POST /api/v1/actions`. Volg de serverblokkades voor app, herstelpunt en versie. Een eerder waargenomen image bewijst op zichzelf geen veilig terugzetpad.

**Toestanden en toets.** ‘Versies ophalen…’, ‘Nog geen versiehistorie’ of bij bronuitval ‘Beschikbare versie onbekend’. Offline of verouderd krijgt iedere getroffen versieregel E15. Een verdwenen cataloguspin, een onverenigbaar databaseschema of ontbrekend herstelpunt krijgt C-11 met reden en link naar Back-ups. Zonder bevestigd terugzetpad voor gegevens én database blijft terugzetten geblokkeerd. Voor een verlopen voorstel is een nieuwe preview nodig. Toets dat ontbrekend migratiebewijs, changelog of clientcompatibiliteit nergens als ‘veilig’ verschijnt.

## S-045 · Appdetail, tab Acties

**Bediening en bron.** C-34 toont per toepasselijke actie het werkwoord, klasse, onderbreking indien bekend, back-up en wie mag goedkeuren. Gebruik `GET /api/v1/apps/{app_uuid}` voor de identiteit, `GET /api/v1/policy` voor acties, `beschermd` en voorwaarden, en `POST /api/v1/actions` voor de werkelijke classificatie en doelcontrole van S-061. De oudere P1-lijst `acties` in het appdetail verleent geen schrijfrecht. Een operator kiest ‘Bekijk voorstel’. Een kijker krijgt C-49.

**Toestanden en toets.** ‘Acties ophalen…’, na een vastgestelde lege selectie ‘Geen acties voor deze app’. Zonder betrouwbare herkenning of beleid ‘Toegestane acties onbekend’. Offline of verouderd geldt E15 voor app én regels. Gewone gate dicht of een verlopen herstelpunt toont het slot, de reden en ‘Bekijk herstelpunten’. Bij beschermde apps biedt de Hub geen knop om te stoppen, bij te werken of te verwijderen. Aanvullende verboden, zoals terugzetten, volgen uit de beschermingsregel voor die app. Voor Emby staat ‘Emby blijft beschikbaar. Alleen jij kunt Emby verwijderen.’ Toets de tab en een rechtstreeks geopend detail op dezelfde bescherming.

## S-046 · Appstore-catalogus

**Bediening en bron.** De hoofdtaak is een goedgekeurd, installeerbaar manifest kiezen. De bestaande bronnen `GET /api/v1/apps` en `GET /api/v1/apps/{app_uuid}` geven inventaris en de appstorekoppeling van een ontdekte app. Ze bevatten geen volledige winkel of selecteerbare versielijst. `GET /api/v1/catalog/availability` controleert precies één pin met dienstscope en is geen browserroute. Tot er een gebruikerslijst is, toont de winkel C-12 ‘Nog niet beschikbaar — de Hub kan de installeerbare manifests nog niet ophalen’. De gebruiker kan wel naar de bestaande Apps-lijst.

**Weergave bij een leesbron.** C-35 laat zoeken op app en filteren op categorie. C-34 toont per versie validatie, image en digest, poorten, mounts, GPU, netwerk en privileges met hun reden, SSO, back-updoelen en installatierisico. Afhankelijkheden of een weigering komen vóór ‘Installeren’. De beheerstatus in de bestaande lijst (S-040) gebruikt ‘Beheerd’ bij expliciet platformbeheer, ‘Geïmporteerd’ bij `adopted` en ‘Niet beheerd’ bij bevestigde afwezigheid van beheer. Een herkenning of appstorekoppeling bewijst geen adoptie. Bij ontbrekende bron ‘Beheerstatus onbekend’.

**Toestanden en toets.** Bij een beschikbare bron zijn laden en een vers leeg filter respectievelijk ‘Catalogus ophalen…’ en ‘Geen manifests voor dit filter’. Bij storing of verlopen bewijs blijft kiezen geblokkeerd met reden. Offline of verouderd krijgt de laatste catalogusmeting E15. Toets dat een geïnventariseerde app, adoptiemanifest of losse pin nooit als installeerbaar product in de winkel belandt.

## S-047 · Installatiewizard

**Bediening.** Volg `design/ontwerptaal/prototypes/wizardstap.html` en ‘20. Wizard / Wizardstap’ in de componentspecificatie. C-36 t/m C-39 begeleiden zeven stappen. **Kies app → Parameters → Controle vooraf → Preview → Goedkeuring → Uitvoering → Controle na uitvoering.** Elk veld noemt de bron (wizard, datasetkiezer, geheim, gegenereerd of standaard). Maak keuzes uit het manifest. Alleen niet-geheime wizard- en datasetvelden zijn invulbaar voor het catalogusplan. Voor een gegenereerd of door de kluis geleverd geheim toont C-39 de naam en ‘De Hub vult dit in’. Invoer, preview, samenvatting en hervatten bevatten geen geheime waarde. Bewaar uitsluitend het bestaande plan-ID voor hervatten.

**Bron.** Voor een vastgestelde selectie maakt de operator via `POST /api/v1/catalog/plans/install` een plan voor `app_id`, `version_id` en doelversies. `GET /api/v1/catalog/plans/{plan_id}` levert stap, status, vervaltijd en open controles. `POST /api/v1/catalog/plans/{plan_id}/steps/{step_id}/propose` maakt uitsluitend voor de vrijgegeven stap het voorstel. Volg de `request_id` naar S-061, S-063 en S-064. Installatie gebeurt als standaard TrueNAS Custom App of als officiële catalogusapp. De installatiepreview benoemt alle hostpaden, mounts, netwerk en poorten, GPU, privileges en reden, image met digest, resources, back-up en dataretentie.

**Toestanden en toets.** Zolang selectie, parameterschema of volledige preflight ontbreekt, krijgt die stap C-12 met de ontbrekende bron. Bij een echte lege keuze ‘Kies eerst een app’. ‘Plan ophalen…’ gaat bij storing over in C-14. Bij poortconflict of ontbrekende afhankelijkheid staat naast ‘Volgende’ de specifieke reden. Offline of verouderd geldt E15 voor plan én preflight. Na `expires_at` ‘Installatieplan verlopen. Maak een nieuw plan.’ Toets dat Enter bij geblokkeerde preflight geen voorstel maakt, de focus de veldfout bereikt en een open controle na installatie zichtbaar open blijft.

## S-048 · App verwijderen

**Bediening en bron.** Vanuit Acties volgt eerst **Controleer wat blijft** met app, opslag, herstelwijze en ‘Alleen de container wordt verwijderd. Je gegevens blijven bewaard.’ Daarna volgt de afzonderlijke bevestiging **Verwijderen goedkeuren** op S-063 voor het voorstel `app.uninstall`. `GET /api/v1/apps/{app_uuid}` en `GET /api/v1/policy` leveren doel en beschermingsregels. `POST /api/v1/actions` geeft de gebonden preview. De gewone R2-goedkeuring en uitvoering blijven aparte handelingen. De ontwerpeis voor data wissen beschrijft een afzonderlijke R3-procedure met getypte doelnaam en eigen goedkeuring. Het huidige beleid blokkeert `uninstall_data`. In P2 ontbreken daarom zowel de wisknop als een selectievak of AI-aanbod daarvoor.

**Toestanden en toets.** ‘Verwijdering controleren…’, ‘Geen app geselecteerd’ of ‘Doel kan niet worden gecontroleerd’. Offline of verouderd wordt het doel met E15 getoond. Bij verlopen binding terug naar de controle van het doel. Bescherming uit `policy/apps.yaml`, onderdeel `beschermd`, vervangt bijbehorende acties door uitleg. Een gesloten gate bij een verder toegestane actie heeft C-11 met reden. Toets beide bevestigingsstappen, focus op Annuleren, ontbreken van datawissen en ontbreken van verwijderen bij Emby en andere daarvoor beschermde apps.

## S-120 · Back-ups

**Bediening.** Boven de matrix staat C-11 met de uitkomst van `GET /api/v1/gates/{gate_id}` voor `backup_gate`. ‘Toegestaan’, ‘Gate dicht’ en ‘Onbekend’ volgen de serverstatus. Een afgewezen of onbekende voorwaarde krijgt eigen uitleg en een link naar het betrokken besluit, de meting of het herstelpunt. Daaronder levert `GET /api/v1/backups/coverage` de C-33-matrix per app en dataset. Cellen tonen woord én symbool voor lokale snapshot, externe kopie, consistente database-export en laatste hersteltest. De Hub-export komt uit `GET /api/v1/backups/self`. ‘Een gesynchroniseerde kopie geeft nog geen herstelgarantie.’

**Appdekking (S-P3-100).** Behoud de vier afzonderlijke bronmeldingen in `app_backups` voor MediaGuard-voortgang, Media Source Optimizer, my_house en Emby-exportarchief. `gedekt` telt alleen binnen `geldig_tot` en met geldig bronbewijs. `degraded` is ‘Beperkt’ met reden, `unknown` is ‘Onbekend’ met reden en `niet_gedekt` in de datasetmatrix is expliciet ‘Niet gedekt’. `vereist` geeft aan of de gate dit onderdeel vereist. Een niet-vereiste of onbekende meting levert geen groen vinkje. Een snapshot zonder vereiste DB-export krijgt ‘Geen volledige appback-up’.

**Toestanden en toets.** ‘Back-updekking ophalen…’, bij verse lege selectie ‘Geen datasets voor deze selectie’. Bij uitval van één bron blijft de rest leesbaar. Offline, verouderde bron of verlopen `geldig_tot` past E15 toe per cel en op een daarvan afhankelijke gate. Gebruik `observed_at` van elke vermelde bron en `app_backups`-meettijden, ook als `afgeleid_op` recent is. Toets dat een niet-gedekte of onbekende voorwaarde zichtbaar blijft en een bijwerking in Versies bij een dichte gate geblokkeerd blijft.

## S-121 · Herstelpunten per app

**Bediening en bron.** C-34 toont de punten uit `GET /api/v1/backups/herstelpunten` met queryparameter `app`, datum, leeftijd, soort, `checkpoint_id` en opgeslagen status. Toon van `snapshot` en `db_export` alleen getypeerde bewijzen van aanwezigheid en consistentie. `GET /api/v1/backups/coverage` levert de D16-doelen en de laatste hersteltest. Label RPO als maximale leeftijd en RTO als beoogde hersteltijd, beide met eenheid. C-15 maakt de ID kopieerbaar.

**Toestanden en toets.** ‘Herstelpunten ophalen…’ of ‘Geen herstelpunten gevonden voor deze app’. Een bronfout geeft ‘Herstelpunten onbekend’. Offline of verouderd krijgt het laatst bekende bewijs E15. Een verlopen RPO, ongezonde hersteltest of ontbrekende vereiste database blokkeert toepassing met de desbetreffende reden, ook als ooit ‘Geverifieerd’ is vastgelegd. Toets dat een eerdere snapshot zonder vereiste DB-export nooit toegang tot bijwerken of terugzetten geeft.

## S-123 · Externe back-up

**Bediening en bron.** C-34/C-06 tonen per taak uit `GET /api/v1/backups/extern` de vaste taak-ID, bron, stand en eindtijd `beeindigd`. Dit zijn de D04-uploadtaken. Gebruik `max_leeftijd_s` als grens. Toon apart het aantal gerapporteerde taken. Aantal bestanden, inhoud en versleuteling blijven onbekend bij gebrek aan meetgegevens. Een verlopen aanmelding of verouderde upload krijgt hoge prioriteit. ‘Bekijk incident’ opent het gekoppelde kritieke incident. Als alleen de bronstatus bekend is, verwijst ‘Bekijk problemen’ naar de inbox.

**Toestanden en toets.** ‘Externe back-up ophalen…’. Een ontbrekend D04-besluit of onbereikbare bron levert ‘Externe back-up onbekend’. Een vastgestelde ontbrekende taak krijgt ‘Geen passende uploadtaak’. `aanmelding_verlopen` toont ‘Aanmelding verlopen. Controleer de externe back-up.’ Een te oude upload toont ‘Laatste upload te oud’ en de tijd, met de dichte gate. Offline of verouderd krijgt de laatst bekende upload E15. Toets dat een nieuwe ophaalpoging de oude upload niet ververst en dat fouttekst, account en bestemmingsadres buiten beeld blijven.

## S-124 · Hersteltests

**Bediening en bron.** C-34 en C-28 tonen uit `GET /api/v1/backups/restore-tests` doel, soort, uitkomst, duur en `uitgevoerd_op`. Alleen de beheerder krijgt ‘Nieuwe hersteltest’. De knop begint op S-061 met de R1-preview van `zfs.snapshot.clone_to_sandbox`. Na bevestigde uitvoering voor elke dataset start `POST /api/v1/backups/herstelpunten/{herstelpunt_id}/hersteltest` de robot met de uitgevoerde voorstel-ID's in `klonen`. De robot beproeft de kloon en proefdatabase. Het directe antwoord bevat het oordeel over kloon, database en ongewijzigde productie. `POST /api/v1/backups/restore-tests` registreert uitsluitend bewijs en is geen startknop.

**Toestanden en toets.** ‘Hersteltests ophalen…’, ‘Nog geen hersteltests’ of ‘Resultaat onbekend’. Toon geslaagd, mislukt en onbekend volgens het bronrecord. Deelbewijs blijft herkenbaar als deelbewijs. Bij een afwijkende checksum verschijnt ‘Hersteltest mislukt’ en is het herstelpunt ongezond. Zonder passende kloon ‘Start geblokkeerd — er ontbreekt een bevestigde zandbakkloon’. Bij uitval na starten eerst de resultaten herlezen. Offline, verouderde resultaten of een verlopen preview geven E15 respectievelijk een nieuwe preview. Toets dat een kijker geen startknop ziet en een losse registratie geen bewijs van een geslaagde robotproef wordt.

## S-127 · Rampenscenario’s

**Bediening en bron.** Per vaste scenario-ID uit `GET /api/v1/backups/rampenscenario` toont een detailpagina de benoemde stappen in een geordende lijst. Gebruik lokaal gecontroleerde instructies bij de vaste stappenlijst voor poolverlies, gelekte toegang, foutieve appmigratie, MediaGuard terugzetten en verhuizing. Het beheer verloopt via de Hub of de TrueNAS-webinterface. C-28 toont de afzonderlijke recente hersteltests. `laatste_hersteltests` is appgebonden. Een datum van een oefening per scenario ontbreekt en krijgt ‘Laatste oefening onbekend’.

**Toestanden en toets.** ‘Scenario’s ophalen…’, bij een ontbrekende of onbekende definitie ‘Stappen voor dit scenario niet beschikbaar’. Bij storing biedt C-14 een nieuwe lezing. Offline of verouderd geldt E15 voor de laatst opgehaalde lijst en oefenbewijzen. Bij verlopen sessie verdwijnt het detail. Het scherm biedt alleen leeshulp. Bij ontbrekend bewijs voor het terugvalpad blijft de ingrijpende stap geblokkeerd met ‘Stop en verifieer eerst de back-up en het afzonderlijke hersteldoel.’ Toets dat een recente hersteltest geen oefendatum bij een ander scenario oplevert.

## S-110 · Flows

**Bediening en bron.** Het overzicht is bedoeld om per flow status, trigger, laatste uitvoering, aantal acties en goedkeuringsvereiste te lezen (C-34, C-53). De Hub-OpenAPI heeft geen flow-inventaris. `GET /api/v1/registry/services` levert alleen dienstbestemmingen uit de inventaris. `GET /api/v1/events` levert ontvangen gebeurtenissen. Beide zijn ongeschikt om een lijst actieve flows samen te stellen. Toon C-12 ‘Nog niet beschikbaar — de Hub ontvangt geen flowlijst.’

**Openen in Node-RED.** Dit is de enige bediening buiten lezen in S-110 t/m S-115. C-42 mag alleen verschijnen voor een beheerder met een vers, eenduidig, voor de editor bevestigd doel achter aanmelding. Een algemene basis-URL of open TCP-poort bewijst dat niet. Bij ontbrekend doel krijgt de beheerder ‘Editoradres niet bevestigd’. Andere rollen krijgen ‘Alleen een beheerder kan de editor openen.’ De bestemming opent in een aangekondigd nieuw tabblad.

**Toestanden en toets.** Bij een toekomstige leesbron ‘Flows ophalen…’ en uitsluitend na een verse, volledige lege lijst ‘Geen flows’. Bij storing van home-control-hub of Node-RED ‘Flowstatus onbekend’. Offline, verlopen of verouderd krijgt de laatst bekende flowstatus E15 en vervalt de editorlink. Toets dat een lege eventpagina of een weggevallen bron nooit ‘Geen flows’ oplevert.

## S-111 · Flowdetail

**Bediening en bron.** C-53 toont bij een toegestane leesbron trigger, eventtype en schema, per actie C-08 met goedkeuringsvereiste en C-13 bij een verboden actie. Er is geen Hub-route voor de flowdefinitie. Een reeds ontvangen afzonderlijk voorstel heeft wel `GET /api/v1/actions/{request_id}` met actor, doel en beleidsklasse. Toon het als link naar S-061 bij vastgestelde flow-identiteit. De definitie zelf krijgt C-12 ‘Flowdetails nog niet beschikbaar’. De editorlink volgt S-110.

**Toestanden en toets.** ‘Voorstel ophalen…’, zonder gekoppeld voorstel ‘Geen voorstel geselecteerd’. Bij uitval ‘Flowdetail onbekend’. Een verouderde of offline geraadpleegde klasse draagt E15. Een verlopen voorstel blijft alleen leesbaar. Toets dat het detail een verboden actie uitlegt en dat vrije nodenamen, configuratie en geheimen buiten beeld blijven.

## S-112 · Testmodus

**Bediening en bron.** De Hub heeft geen gebruikersroute voor het starten of uitlezen van een flow-droogtest. Het infopaneel C-12 zegt ‘Nog niet beschikbaar — testresultaten komen uit Node-RED.’ Een bevoegde beheerder kan vanuit hier de geverifieerde editorbestemming van S-110 openen. Een latere C-54 toont uitsluitend vaste uitkomsten van bevestigde testevents en de bron die de zandbak bevestigt.

**Toestanden en toets.** Zonder leesroute blijft het paneel direct zichtbaar. Een laadindicator of ‘Nog geen tests’ vereist een werkelijke leesbron. Bij uitval of ontbrekend testbewijs ‘Testuitkomst onbekend’. Een historische test krijgt offline of verouderd E15. Een verlopen sessie sluit de editorlink af. Toets dat ‘Er zijn geen echte apparaten gewijzigd’ uitsluitend bij bewezen droogtest verschijnt en dat de Hub geen afspeel- of startknop biedt.

## S-113 · Eventtypen

**Bediening en bron.** De beoogde C-34-lijst laat eventtype, bron en schemaversie lezen. `GET /api/v1/events?source_app=home-control-hub` kan als apart gelabelde lijst **Ontvangen gebeurtenissen** contractbekende typen en tijdstippen tonen. Een voorbeeldschema of de complete catalogus van ondersteunde typen wordt nergens geleverd. Dat gedeelte krijgt C-12 ‘Catalogus van eventtypen nog niet beschikbaar’. Toon uitsluitend toegestane metadata.

**Toestanden en toets.** ‘Ontvangen gebeurtenissen ophalen…’ of bij een verse lege selectie ‘Geen gebeurtenissen ontvangen voor dit filter’. Bij storing ‘Gebeurtenissen onbekend’. Offline of verouderd krijgt de waarnemingslijst E15. Een onbekende schemaversie blijft als zodanig benoemd, zonder payload. Een verlopen sessie wist de lijst. Toets dat een ontvangen, onbekend type nergens als ondersteund of uitvoerbaar verschijnt.

## S-114 · Uitvoeringshistorie van flows

**Bediening en bron.** C-34 en C-23 tonen als deelhistorie alleen **Actieverzoeken van flows**. Lees `GET /api/v1/actions`, selecteer op `actor.type = flow` en volg de cursor. `GET /api/v1/actions/{request_id}` levert de status per verzoek. Koppel gebeurtenissen alleen met servergeleverde identificaties. Een aanvraag is nog geen uitgevoerde actie. Voor het volledige runlog van de eigenaar ontbreekt een Hub-leesroute. C-12 benoemt dit naast de deelhistorie.

**Toestanden en toets.** ‘Actieverzoeken ophalen…’. Meld een lege pagina als ‘Op deze pagina geen flowverzoeken’. Alleen na een volledige verse lezing is ‘Geen actieverzoeken van flows’ juist. Bij storing ‘Uitvoeringshistorie onbekend’. Offline of verouderd draagt de tijdlijn E15. ‘Verlopen’, ‘Geweigerd’ en ‘Uitgevoerd en gecontroleerd’ volgen het individuele verzoek. Toets dat herlevering bij dezelfde `request_id` één regel houdt en dat doorklikken naar het volledige verloop geen tweede uitvoering start.

## S-115 · Flowversies en herstel

**Bediening en bron.** C-34/C-20 zijn bedoeld voor de momentopnamen en hun geschoonde verschil. De lijst met momenten en versies is niet via de Hub opvraagbaar en krijgt C-12. S-P2-140b levert wél de beleidsactie `automation.flows.restore`. Bestaande herstelverzoeken zijn te lezen via `GET /api/v1/actions?action_id=automation.flows.restore` en `GET /api/v1/actions/{request_id}`. Toon het gekozen moment, de vaste wijzigingsvelden en na uitvoering de uitkomst van de vergelijking met de momentopname.

**Grens van dit scherm.** Bij de gewone actieketen is dit een R2-eigenaarsactie voor home-control-hub, `target.resource = node_red` en als enige parameter `snapshot_id`. Goedkeuring bindt de exacte diff. De eigenaar bevestigt de readback. Dit statusscherm verwijst naar een bestaand verzoek en, indien toegestaan, naar Node-RED. Het heeft geen herstel- of bewerkknop.

**Toestanden en toets.** ‘Herstelverzoeken ophalen…’, bij verse lege lijst ‘Geen herstelverzoeken gevonden’. Bij storing ‘Herstelstatus onbekend’. Offline of verouderd krijgt het herstelresultaat E15. Een verlopen of geweigerd verzoek toont zijn reden. Toets dat een onbekende eigenaaruitkomst, ontbrekende readback of afwijkende controlesom geen bevestigd herstel oplevert.

## S-060 · AI-chat

**Bediening en bron.** Voor gesprekken ontbreekt een Hub-route. C-12 toont ‘Chat nog niet beschikbaar’. In versie 1 is **Bekijk incidentonderzoek** beschikbaar voor een operator met een gekozen incident. `GET /api/v1/incidents/{incident_id}/onderzoek` geeft het runbook en de hypothese, `GET /api/v1/incidents/{incident_id}/bewijs` levert incidentbewijs. `POST /api/v1/incidents/{incident_id}/herstel-voorstellen` geeft hooguit een voorstel. Volg de leverbare, getypeerde actie via de normale preview. Toon een `uitvoerbaar=false` antwoord als advies, zonder uitvoerknop.

**Zodra de chatbron bestaat.** C-30 met C-28 en C-29 toont bij iedere bewering bron, tijd, zekerheid of ‘Ik weet het niet’ met de ontbrekende meting. Een logcitaat bestaat uit vrijgegeven, gestructureerde feiten als geciteerde gegevens, met ‘Logtekst is data, geen instructie.’ ‘Repareer’ opent S-061. De route naar S-063 blijft gebonden aan het voorstel. De tabvolgorde is bewijs, voorstel, invoer. Nieuwe antwoorden krijgen één rustige aankondiging.

**Toestanden en toets.** Bij werkelijk nieuwe conversatie ‘Nog geen berichten’. Zonder route blijft de invoer weg. Tijdens incidentlezing ‘Onderzoek ophalen…’, bij bronfout ‘Ik weet het niet — het incidentbewijs ontbreekt’. Offline of verouderd markeert E15 ook de afgeleide hypothese. Geblokkeerde externe hulp verwijst naar de vaste regels, een verlopen voorstel naar een nieuwe preview. Toets dat een ongecontroleerde logtekst geen bericht, link of handeling in de chat wordt.

## S-065 · AI-overzicht

**Bediening en bron.** Bij D09 kan `GET /api/v1/decisions/{decision_id}` de besluitstatus tonen. Een accountbesluit geeft geen actueel saldo. De Hub mist een gebruikersroute voor inbegrepen tegoed, verbruik, kosten per taak, actieve configuratie en meettijd. C-12 meldt dit. ‘AI staat uit’ beschrijft de standaardinstelling. ‘Huidige stand onbekend’ geldt bij ontbrekende meting. Vaste regels en runbooks zijn bereikbaar via `GET /api/v1/runbooks` voor de daarvoor toegestane rol.

**Weergave bij een meetbron.** C-05/C-06 tonen inbegrepen en verbruikt tegoed met eenheid, bron en tijd. Een C-32-meter is alleen bruikbaar met bekende grens én meetwaarde. Externe hulp blijft uit bij nul, ontbrekend of verlopen tegoed. ‘Tegoed op. Externe hulp staat uit. De vaste regels blijven werken.’ Lokale AI is optioneel en standaard uit.

**Toestanden en toets.** ‘Besluit ophalen…’ of ‘Nog geen keuze vastgelegd’. Bij storing ‘Tegoed onbekend’. Offline of verouderd toont E15 het eerdere bedrag zonder beschikbare bestedingsruimte. Een geblokkeerde rekening opent geen betaalde terugval. Toets dat een besluit, ontbrekend bedrag en gemeten nul drie herkenbaar verschillende toestanden opleveren.

## S-069 · Veiligheidsoverzicht

**Bediening en bron.** De hoofdtaak is de laatste veiligheidstoets en de releasebeslissing kunnen herleiden tot een testrun. De Hub-OpenAPI publiceert geen gebruikersroute voor het rapport van S-P2-130 of de releasepoort. C-12 toont ‘Nog niet beschikbaar — er is geen testrapport voor deze versie.’ Bij een toekomstige leesbron geeft C-28 vaste testcategorie, uitkomst, commit, meettijd en bewijsreferentie. Een kritieke fout toont C-11 ‘Vrijgave geblokkeerd’ met de categorie.

**Toestanden en toets.** Zonder rapport geen spinner, testteller of vinkje. Bij een bestaande maar falende leesbron ‘Testrapport ophalen mislukt’. Offline of verouderd krijgt de oude beoordeling E15. Bij verlopen bewijs of een andere commit ‘Geen geldig bewijs voor deze versie’. Toets dat een oude groene run nooit de huidige release vrijgeeft en dat voorbeelden uit testpayloads buiten beeld blijven.

## S-071 · Aanbevelingen en feedback

**Bediening en bron.** De Hub heeft geen gebruikersroute voor aanbevelingen, effectmetingen of het verwijderen van feedbackdata. C-12 toont ‘Aanbevelingen nog niet beschikbaar’. Na levering laat C-34 per aanbeveling het bronincident, gemeten effect met eenheid en meetperiode, en de bewijsdatum zien. C-28 opent alleen vrijgegeven feiten. ‘Verwijder feedbackdata’ krijgt daarna een afzonderlijke bevestiging met de precieze reikwijdte. Productielogs en beleid vallen daarbuiten.

**Toestanden en toets.** ‘Nog geen aanbevelingen’ vereist een vers, bevoegd leeg antwoord. Bij storing ‘Aanbevelingen onbekend’. Offline of verouderd geldt E15 ook voor het gemeten effect. Zonder verwijderroute, bevoegdheid of bij verlopen sessie kan niets worden gewist. Toets dat de Hub geen lokale succesmelding toont voor een ontbrekende verwijderhandeling en geen beleidsgrens uit feedback overneemt.

## S-073 · Automatiseringsvoorstel van de AI

**Bediening en bron.** De gebruiker wil trigger, voorwaarde, actie en doel van één voorstel kunnen beoordelen. Een Hub-route voor een gestructureerd automatiseringsvoorstel met zandbakresultaat ontbreekt. C-12 toont ‘Automatiseringsvoorstellen nog niet beschikbaar’. Later volgt een detail met C-19, C-08, C-28 en een link naar de gewone beoordeling. ‘Wanneer ‹gebeurtenis›, dan ‹actie›’ wordt uit toegestane velden samengesteld. De Hub toont of bewerkt geen flowdefinitie.

**Toestanden en toets.** Zolang de bron ontbreekt heeft dit scherm alleen het infopaneel. Bij een bestaande bron ‘Voorstel ophalen…’, ‘Geen voorstel geselecteerd’ of ‘Testbewijs onbekend’. Offline of verouderd behandelt E15 de test en het daarvan afgeleide voorstel samen. Een verlopen voorstel of geblokkeerde beleidsactie toont de reden. Toets dat noch AI-tekst noch een testevent een echte flow, herstelactie of apparaatbediening kan starten.

## Monitorplan · Instellingen → Monitoring

**Bediening en bron.** Voeg de sectie **Monitorplan per app** toe aan `apps/web/src/app/instellingen/monitoring/MonitoringScreen.tsx`. `GET /api/v1/monitoring/monitorplan` is voor operator en beheerder. C-34/C-06 tonen per app de controle uit `healthcheck.monitor`, het gevalideerde controleadres als tekst, verwachte HTTP-status, time-out en interval in seconden. De stand van een regel is `ontbreekt`, `onvolledig`, `voorgesteld` of `handmatig bevestigd`. Toon bij de eerste drie **Niet bewaakt** met reden. Een ontbrekende bronlezing krijgt ‘Bewaking onbekend’.

De beheerder neemt de regel zelf over in Uptime Kuma en kiest **Handmatig bevestigen**. `POST /api/v1/monitoring/monitorplan/{app_id}/bevestiging` bindt `bevestigd=true` aan de getoonde `plan_sha256`. Lees het plan daarna opnieuw. Alleen een actuele, overeenkomende bevestiging draagt ‘Handmatig bevestigd’. Dit is een verklaring van de beheerder. De gezondheid van de app staat afzonderlijk bij haar eigen meting. Een operator kan alleen lezen. Een kijker krijgt geen planregels of bevestigknop.

**Toestanden en toets.** ‘Monitorplan ophalen…’ en na verse lege lijst ‘Geen apps voor dit monitorplan’. Bij leesfout C-14 ‘Monitorplan ophalen mislukt’. Een onvolledige regel heeft naast de uitgeschakelde knop een concrete reden, bijvoorbeeld ‘De hostpoort ontbreekt’. Bij 409 `plan_gewijzigd` of `bevestiging_verouderd` vervalt de oude bevestiging en verschijnt ‘Plan gewijzigd. Neem de nieuwe regel over.’ Offline of verouderd geldt E15 ook op ‘Handmatig bevestigd’. Bij verlopen sessie verdwijnt het plan. Toets een gewijzigde regel, een ontbrekend monitorblok en een kijker.

## Wat de backendbouwer nog mist

De regisseur kan onderstaande hiaten vóór S-P2-170 aan de betreffende eigenaar toewijzen. Tot de bron beschikbaar is, geldt op het betreffende scherm de beschreven blokkade of C-12. De monitorplanroutes, de vier bronnen van appback-updekking en de R2-eigenaarsactie voor flowherstel zijn al aanwezig.

| Scherm en eigenaar | Benodigde aanvulling | Herkomst van de eis |
| --- | --- | --- |
| S-061/S-063 · Hub-acties | Lever het door de server geselecteerde checkpoint en de binding al bij de preview van een actie die een back-up vereist. Nu verschijnt de ID pas in de goedkeuring. Lever ontbrekende impact, onderbreking en veilige veldbeschrijvingen indien bekend. | `apps/api/src/hub/actions/service.py`, `weergave` en `keur_goed`. `docs/platform-v2/PLATFORM_CONTRACTEN.md`, ‘8. Risicobeleid, voorstel, goedkeuring en executor’. |
| S-044 t/m S-047 · Hub en appstore | Een voor gebruikers leesbare lijst goedgekeurde installeerbare versies, met versie-ID, schema, manifesteisen, terugzetcompatibiliteit en preflight per conflict of afhankelijkheid. Voeg de bevestigde beheer-/adoptiestatus per app toe. Een plan kunnen aanmaken dekt de voorafgaande keuze niet af. | `apps/api/src/hub/routers/catalog_plans.py`, `InstallPlanIn`. Contract, ‘9. Manifeststandaard’. `docs/platform-v2/02_BOUWPLANNEN/B08_APPSTORE_LIFECYCLE.md`, ‘B08-003’ en ‘B08-004’. |
| S-110 t/m S-115 · home-control-hub en Hub | Een voor de browser geautoriseerde leesweergave van flows, trigger en actieklasse, testresultaten, typen, runs en momentopnamen met versheid. Lever een geverifieerde, beheerdersgebonden editorbestemming. Actiehistorie, events en het algemene dienstenregister kunnen deze gegevens niet vervangen. | Contract, ‘7. Event-envelope’ en ‘8. Risicobeleid, voorstel, goedkeuring en executor’. `docs/platform-v2/02_BOUWPLANNEN/B11_AUTOMATISERING.md`, ‘1. Concrete schermen en gebruikersreizen’. `docs/platform-v2/OVERDRACHT/STATUS.md`, besluit C-11. |
| S-060/S-065/S-069/S-071/S-073 · Hub-AI | Gebruikersroutes voor gestructureerde chat met bronverwijzingen, vers tegoed en harde stop, testbewijs per release, aanbevelingen met gemeten effect en afgebakend wissen, en automatiseringsvoorstellen met zandbakbewijs. | `docs/platform-v2/02_BOUWPLANNEN/B02_AI_SERVER_MANAGER.md`, ‘3. API en integratie-contracten’ en werkpakketten B02-001, B02-002, B02-010, B02-011 en B02-012. |

**Vervolgpunten.** Voor S-062 is een exact servertotaal voor de wachtlijst wenselijk. Voor S-061/S-064 ontbreken een afzonderlijke droogtest en het afbreken van één verzoek. De algemene noodstop heeft een ander bereik. Een leesbaar versienummer naast de beleidshash is een uitbreiding voor S-066. Voor S-123 ontbreken bestandsaantal en versleutelingsbewijs. Voor S-124 ontbreekt een blijvend opvraagbaar, gestructureerd robotrapport per test-ID. Voor S-127 ontbreekt de koppeling van oefendatum en bewijs aan een scenario. Deze wensen komen uit de gelijknamige schermrijen in `design/ontwerptaal/onderzoek/EISEN_EN_SCHERMEN.md` en de werkpakketten B12-004, B12-005 en B12-007. Het ontwerp vraagt geen uitbreiding van Peil of van de lijst toegestane destructieve acties.

## Controle en overdracht

De schermnamen en de vier groepen volgen `design/ontwerptaal/onderzoek/EISEN_EN_SCHERMEN.md`, ‘5.5 Apps en appstore’, ‘5.7 AI, acties en goedkeuring’, ‘5.11 Automatisering’ en ‘5.12 Backups en herstel’. De prototypekeuze volgt `docs/ontwerp/HUB_PEIL_ONTWERP.md`, ‘10. Hiaten en vervolg’. Contract §13 en `docs/platform-v2/ONTWERPTAAL.md`, ‘4.4 Versheid’, ‘4.5 Risico R0–R3’ en ‘12. Toegankelijkheid en tests’ geven de toetsnorm.

| Proef bij de onafhankelijke review | Waarop letten |
| --- | --- |
| Volg ‘Bijwerken’ van appdetail tot uitvoering. Laat het herstelpunt ontbreken, verander daarna het doel en laat een goedkeuring verlopen. | Iedere uitgeschakelde gevaarknop heeft een zichtbare en voorleesbare reden. Een gewijzigde binding vereist een nieuw voorstel. De toetsenbordroute bereikt eerst uitleg en Annuleren. |
| Loop een installatiepreview, flowdiff, mislukt robotrapport en logcitaat na met synthetische gevoelige broninhoud. | Alleen de bedoelde veldnamen, vaste zinnen en gevalideerde feiten mogen zichtbaar, voorleesbaar of kopieerbaar zijn. Bij onvolledig toonbare wijzigingen blijft goedkeuring geblokkeerd. |
| Wissel van beheerder naar kijker, laat de verbinding wegvallen en herstel haar. | Eerder toegestane gegevens verdwijnen bij geweigerd leesrecht. Offline markeert brongebonden oude waarden en zet bediening uit. Een herstelde verbinding vraagt eerst nieuwe gegevens op. |
| Laat de flowbron wegvallen, een upload verlopen en een monitorregel wijzigen. | ‘Onbekend’, ‘Niet gedekt’ en ‘Niet bewaakt’ hebben elk eigen tekst en bron. Een vorige bevestiging, recente paginalezing of lege eventpagina kan geen groen opleveren. |

Bij de UI-bouw volgt per scherm de beschreven toets met lokale testgegevens. Controleer 320, 360, 390, 768, 1024 en 1440 px in licht en donker, reflow bij verruimde tekstafstand, aanraakdoelen, focus bij de vaste balk en de volledige Tab-doorloop. Meet WCAG 2.2 AA met de Peil-axe-tags. Controleer de scherminhoud ook met de schermlezer en in gedwongen kleuren. In S-P2-170 t/m S-P2-200 verwijst de EVIDENCE-opmerking van het betreffende UI-werkpakket naar dit ontwerp.
