# Ontwerpreviews van de gebouwde P3-schermen

De kolom **Review** verwijst per stap naar de onafhankelijke beoordeling. De rapportnaam is relatief aan
`.lokaal/ketens/<stap-ID>/` in de lokale planomgeving. Bij gecombineerde reviews beschrijft de gelijknamige
opdracht met het voorvoegsel `OPDRACHT-` welke rollen en commits de reviewer beoordeelde. Alle aangewezen
afdrukken komen uit een simulator of componentproef met testgegevens.

## Hub

| Stap en scherm | Review | Schermafdrukken met testgegevens |
| --- | --- | --- |
| S-P3-060 · Gezondheid per onderdeel in de appcatalogus | `RAPPORT-R-VEILIG.md` omvat ontwerp, toegankelijkheid en bronversheid. De laatste hercontrole van de gezondheidsweergave staat in `RAPPORT-R-VEILIG-4.md`. | [Binnenkant van een ongekoppelde app](review/s-p3-060-binnenkant.png) |
| S-P3-070 · Bestaande apps koppelen in Instellingen → Diensten | `RAPPORT-R-VEILIG.md` toetste rechten, geheimen en het legen van het veld. De Peil-meting in `RAPPORT-A-BOUW.md` is door de bouwer uitgevoerd. Een onafhankelijke ontwerpreview van de bouwcommits ontbreekt. | [Leeg](review/diensten-leeg.png), [bezig](review/diensten-bezig.png), [fout](review/diensten-fout.png), [verouderd](review/diensten-verouderd.png), [gekoppeld](review/diensten-gekoppeld.png) |
| S-P3-080 · Media en de downloadketen | Voor bouwcommit `653865b` bevat de keten alleen `RAPPORT-A-BOUW.md`. De bouwer toetste de vijf toestanden. Een onafhankelijke ontwerpreview van die commit ontbreekt. | [Vijf toestanden op smal en breed scherm](../screenshots/p3/toestanden), waaronder [lege keten op mobiel](review/media-leeg-smal.png) en [bronfout op desktop](review/media-fout-breed.png) |
| S-P3-082 · MediaGuard-metingen en noodstop op Media | `RAPPORT-R-VEILIG.md` en de hercontroles tot en met `RAPPORT-R-VEILIG-3.md` toetsten onder meer de bronrechten, het aantal incidenten en het verlopen van een meting. Een afzonderlijk oordeel over het volledige ontwerp ontbreekt. | [Gemeten cijfers](review/media-gevuld-breed.png) en [verouderde meting](review/media-verouderd-smal.png). Deze opnamen zijn bij de uitbreiding van Media bijgewerkt. |
| S-P3-090 · Huis, alleen kijken | `RAPPORT-R-VEILIG.md` is de gecombineerde onafhankelijke review. Die toetste Peil-onderdelen, fout- en verbindingstoestanden, toetsenbord, axe en vier breedtes. `RAPPORT-R-VEILIG-2.md` tot en met `RAPPORT-R-VEILIG-4.md` volgen het herstel van de bronweergave. | [Gevulde woning op mobiel](../screenshots/p3/mobiel-360/huis-gevuld-donker.webp) en [op desktop](../screenshots/p3/desktop-1440/huis-gevuld-donker.webp) |
| S-P3-100 · Back-updekking van bestaande apps en het Emby-exportarchief | `RAPPORT-R-HARDE-EIS.md` en `RAPPORT-R-HARDE-EIS-r2.md` toetsten dekking en gegevensbehoud. De opdracht voor die gecombineerde review bevatte geen R-ONTWERP. | [Vier back-upmeldingen uit de simulator](review/s-p3-100-backupmeldingen.png) |
| S-P3-170 · Beeldverzameling van P3 | `RAPPORT-R-TECH.md` omvat R-ONTWERP. De reviewer herleidde 51 WebP-bestanden tot simulatoropnamen. De opdracht begrensde de review tot `a1a6736`, `40fd143` en `74594f7`. | [Mobiel 360](../screenshots/p3/mobiel-360), [mobiel 390](../screenshots/p3/mobiel-390), [tablet 768](../screenshots/p3/tablet-768), [desktop 1440](../screenshots/p3/desktop-1440) en [kaarttoestanden](../screenshots/p3/toestanden) |

S-P3-160 (Kosten) is uitgesteld tot versie 2. S-P3-170 toont de bestaande plaatshouder. S-P3-075 leverde de
leesroute voor de keten op. Het bijbehorende scherm valt onder S-P3-080. [Plaatshouder Kosten](../screenshots/p3/mobiel-390/kosten-licht.webp)

### Beeldcontrole tijdens het gateherstel

Op 25 november 2026 is `make web-review` opnieuw uitgevoerd op de Hub-werkkopie met het G-06-herstel,
op basis van `36e24f219f6e`. De 29 browserproeven gaven exitcode 0. De strenge Peil-controle telde 73
schermen en toestanden, 868 metingen, nul harde bevindingen, nul axe-overtredingen en nul meetfouten.
Alle geplande metingen zijn uitgevoerd. De schermbreedtes waren 320, 360, 390, 768, 1024 en 1440 px,
telkens in licht en donker.

| Stap | Opnieuw beoordeeld in de Hub | Metingen per genoemd scherm | Bevindingen van Peil |
| --- | --- | ---: | --- |
| 060 | Appcatalogus en appdetail met de gezondheid per onderdeel | 12 | Geen |
| 070 | Diensten als beheerder en als kijker | 12 | Geen |
| 080 en 082 | Media | 12 | Geen |
| 090 | Huis | 12 | Geen |
| 100 | Back-ups | 12 | Geen |
| 170 | De actuele schermen Media, Huis en de plaatshouder Kosten | 12 | Geen |

Het verslag van deze hercontrole staat in `.lokaal/ketens/GATE-P3-herstel-asm/RAPPORT.md`. Voor de
opgenomen bouwcommits blijft de oorspronkelijke reviewdekking gelden zoals in de tabel hierboven.
Op de serverpagina met de NAS-simulator offline was de focus bij Datasets op 390 px deels bedekt.
Dit was de enige zachte bevinding in de volledige Peil-meting.

In het appdetail was de buitenkant gezond gemeten en bleef de binnenkant van de ongekoppelde app
onbekend. Bij Back-ups bleef de dekking voor alle vier de appbronnen onbekend. De melding over
het Emby-exportarchief liet ook zien dat het archief in deze simulator nog moest worden gemaakt.
De twee opnamen bij S-P3-060 en S-P3-100 zijn pixel voor pixel vergeleken met de overeenkomstige
uitsneden van `app-status-licht.jpg` en `backups-licht.jpg` uit de Peil-review op 768 px.

De gekoppelde my_house-kaart toont de laatste vier tekens en een leeg invoerveld. Huis onderscheidt de
gemeten temperatuur van het laatst bekende doel en toont de boiler als meting. Bij een verouderde
MediaGuard-bron toont Media de laatste meettijd bij het onbekende cijfer. Op de paginavullende mobiele
opname valt de vaste ondernavigatie over een kaartkop. **VERSIE 2-voorstel** Maak ook die kop leesbaar bij de
volgende opname van dit scherm. [Koppeling](review/diensten-gekoppeld.png) · [Huis](../screenshots/p3/mobiel-360/huis-gevuld-donker.webp) · [Media](review/media-verouderd-smal.png)

## Andere P3-stappen met een ontwerpreview

| Stap en scherm | Review | Schermafdrukken met testgegevens |
| --- | --- | --- |
| S-P3-210 · MSO, buildgegevens op Systeem | `RAPPORT-R-ONTWERP.md` en `RAPPORT-R-ONTWERP-2.md` | In de stapmap, `peil-review-s-p3-210/systeem-herstel-licht-390.png`. |
| S-P3-220 · MSO, machinesleutels | `RAPPORT-R-ONTWERP.md` | In de stapmap, `r-ontwerp/beelden/contactblad-light.png` en `contactblad-dark.png` in dezelfde map. |
| S-P3-270 · MSO, Opslag en groei | Ontwerp maakte deel uit van `RAPPORT-R-HARDE-EIS.md`. De reviewer beschrijft onder meer de toestand met te weinig metingen. | [Nieuwe componentopname van de kaart met één dagmeting](review/s-p3-270-opslag-en-groei.png) |
| S-P3-280 · MSO, Peil-ronde web | `RAPPORT-R-HARDE-EIS.md` is de gecombineerde review. De hercontroles staan in `RAPPORT-R-HARDE-EIS-2.md` en `RAPPORT-R-HARDE-EIS-3.md`. | In `media-source-optimizer`, onder meer `docs/screenshots/automatisering-light-360.png` en `docs/screenshots/systeem-dark-768.png` uit beeldcommit `7aafca3`. |
| S-P3-600 · MediaGuard, rechten van API-sleutels | `RAPPORT-R-ONTWERP.md`, `RAPPORT-R-ONTWERP-2.md` en `RAPPORT-R-ONTWERP-3.md` | In de stapmap, `review2-definitief/dark-1024-forced-aan.png` en de overige toestanden in die map. |
| S-P3-680 · MediaGuard, web op tablet | `RAPPORT-R-HARDE-EIS.md` omvat ontwerp en toetsenbordbediening. De hercontrole staat in `RAPPORT-R-HARDE-EIS-2.md`. | In `media-guard-ultimate`, `docs/screenshots/peil/s-p3-680/` met de overzichtspagina in beide thema's en de opslagpagina. |
| S-P3-710b · my_house, inbedrijfstelling op web en Android | In de stapmap **S-P3-710**, `RAPPORT-R-ONTWERP-b.md` en `RAPPORT-R-ONTWERP-b2.md`. De delen a en c betroffen de beheerkern en het bewijs. | In dezelfde stapmap, `PEIL_BEWIJS-b/overzichten/` en `PEIL_BEWIJS-b2/nieuw/shots/`. |
| S-P3-730 · my_house, herstelwizard | `RAPPORT-R-HARDE-EIS.md` omvat ontwerp en toetste vijf wizardtoestanden. De reeks hercontroles loopt tot `RAPPORT-R-HARDE-EIS-6.md`. | In de stapmap, onder meer `bewijs-r-harde-eis-2/schermen/bezig-320-light.png` en `bron-gepauzeerd-1440-dark.png` in dezelfde map. |
| S-P3-745 · my_house, Hub-sleutelset op Systeem | `RAPPORT-R-VEILIG.md` omvat ontwerp, toetsenbordfocus en twaalf combinaties van breedte en thema. Twee hercontroles toetsten het herstel van sleutelvolgorde en toegang. | [Nieuwe componentopname met een leeg invoerveld](review/s-p3-745-hubkoppeling.png) |

De twee aanvullende componentopnamen tonen de echte kaart uit respectievelijk MSO-commit `6722169` en
my_house-commit `fbaebb3`, op 768 px met het gebouwde appstijlblad. De MSO-kaart kreeg één synthetische
dagmeting. De sleutelkaart kreeg het testantwoord voor een lege koppeling. Beide opnamen zijn achteraf
gemaakt voor deze inventaris. S-P3-350, S-P3-685 en S-P3-765 staan in het faseplan op versie 2.

## Schermwijzigingen bij functionele stappen

| Stap en scherm | Onafhankelijke beoordeling van de stap | Nieuwe opname van het gewijzigde onderdeel |
| --- | --- | --- |
| S-P3-265 · MSO, compatibiliteitstabel | `RAPPORT-R-VEILIG-2.md` toetste de tekst ‘Alleen voor beheerder’ voor OpenAPI. Een volledige ontwerpreview van dit herstel ontbreekt. | [Rechten bij de OpenAPI-route](review/s-p3-265-compatibiliteit.png) |
| S-P3-625 · MediaGuard, herstelweergave bij een nieuwere database | `RAPPORT-R-TECH.md` en `RAPPORT-R-HARDE-EIS-9.md` toetsten het technische herstel en het behoud van de gegevens. Het bouwrapport van de derde ronde vermeldt een browserproef op 320 px. Een onafhankelijke ontwerpreview ontbreekt. | [Uitleg en twee herstelmogelijkheden](review/s-p3-625-herstelweergave.png) |
| S-P3-640 · MediaGuard, gedeeltelijk herstelde downloadmap | `RAPPORT-R-HARDE-EIS-6.md` toetste het behoud van bestanden. Een onafhankelijke ontwerpreview van de gewijzigde melding ontbreekt. | [Deels bewaarde map in de prullenbak](review/s-p3-640-opruimer.png) |
| S-P3-676 · MediaGuard, bevestiging bij het verwijderen van originelen | `RAPPORT-R-HARDE-EIS-3.md` liet bij de onderzochte stand een blokkade op het behoud van originelen open. Een onafhankelijke ontwerpreview van de dialoog ontbreekt. | [Voorvertoning met één te bewaren origineel](review/s-p3-676-origineel.png) |
| S-P3-700 · my_house, startkaart bij een nieuwere database | De herstelling in `RAPPORT-A-HERSTEL.md` voegde de serveruitleg aan de bestaande kaart toe. `RAPPORT-R-EERLIJK.md` controleerde het herstel. Een onafhankelijke ontwerpreview van de kaart ontbreekt. | [De reactie op een nieuwere schemaversie](review/s-p3-700-startkaart.png) |
| S-P3-742 · my_house, terugvalinstructie in de herstelwizard | `RAPPORT-R-HARDE-EIS-7.md` hield de vrijgave van `102984c` tegen. De latere aanpassing van de instructies staat in `RAPPORT-A-HERSTEL-8.md`. Een onafhankelijke ontwerpreview van die tekstwijziging ontbreekt. | [Bronregistratie afgesloten en kopie voorbereiden](review/s-p3-742-terugval.png) |

De onderdelen in deze zes opnamen komen op volgorde uit de stapcommits `c6f21d3`, `114c05e`, `52810fa`,
`9f6dfb3`, `57b7018` en `7ee5781`, met het lokaal gebouwde stijlblad van de betreffende app.
In de browser zijn de gewijzigde teksten bij 390 px in het lichte thema en 768 px in het donkere thema
gelezen. De onderdelen vielen binnen de schermbreedte en axe meldde binnen die onderdelen geen
WCAG A- of AA-overtredingen uit 2.0 of 2.1. De quarantaineproef opende alleen de voorvertoning.
Bij nul verwijderbare bestanden staat boven ‘Blijft bewaard’ nog de algemene uitleg dat het origineel wordt
verwijderd. **VERSIE 2-voorstel** Geef bij nul verwijderbare bestanden een uitleg die de telling volgt.
