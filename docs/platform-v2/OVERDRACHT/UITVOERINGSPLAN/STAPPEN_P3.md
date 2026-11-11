# STAPPEN_P3 - Fase P3: eigen apps koppelen (MediaGuard, Media Source Optimizer, my_house), energie en kosten

Dit bestand is het uitvoeringsplan voor fase P3. De regisseur kiest hieruit stappen en geeft elke subagent het
stap-ID mee; de subagent leest zijn stap zelf. Elke stap is door een bouwer in een keer af te ronden.
Stand van dit plan: geschreven op 2026-11-11, terwijl ronde 3 nog in de repos bouwde. Daarom heeft elke stap een
regel "Al gedaan?".

## 0. Afkortingen en vaste verwijzingen

| Afkorting | Betekenis |
|---|---|
| `<WERKMAP>` | de map waarin de 11 repos staan (branch `ccr-c133d7a0-kuz1cv` in elke repo) |
| `<DOCS>` | `<WERKMAP>/ai-server-manager/docs/platform-v2` |
| [CONTRACT] | `<DOCS>/PLATFORM_CONTRACTEN.md` (versie 1.3) |
| [CONF] | `<DOCS>/CONTRACT_1.3_CONFORMITEIT.md` |
| [GATES] | `<DOCS>/01_ARCHITECTUUR/06_FASERING_EN_GATES.md` |
| [B03-FASE] | `<DOCS>/02_BOUWPLANNEN/B03_FASERING.md` |
| [B01], [B04], [B05], [B06], [B14] | `<DOCS>/02_BOUWPLANNEN/B01_HOME_CONTROL_HUB.md`, `B04_MEDIAGUARD_DELTA.md`, `B05_MSO_DELTA.md`, `B06_MY_HOUSE_DELTA.md`, `B14_ENERGIE_RESOURCE_MANAGER.md` |
| [I-nn] | `<DOCS>/03_INSTALLATIE/` (bijvoorbeeld `I03_MEDIAGUARD.md`) |
| [A-nn] | `<DOCS>/04_BESTAANDE_APPS/` (bijvoorbeeld `A18_MEDIAGUARD.md`) |
| [PEIL] | `<DOCS>/ONTWERPTAAL.md` en `<WERKMAP>/ai-server-manager/design/ontwerptaal/` |
| [RUW] | `<WERKMAP>/.lokaal/plan/bron/VERVOLGPUNTEN_RUW.md` (koppen per ronde en repo; geen punt-ID's) |
| [DM-MG], [DM-MSO], [DM-MH] | `docs/platform-v2/DELTA_MATRIX.md` in `media-guard-ultimate`, `media-source-optimizer`, `my_house` |
| POORTEN, VALKUILEN, BESLUITEN | `<WERKMAP>/.lokaal/plan/uit/POORTEN.md`, `VALKUILEN.md`, `BESLUITEN_EN_BLOKKADES.md` |
| STAND `<repo>` `<ID ...>` | het alleen-lezen commando van regel 4 in hoofdstuk 3 |

Paden in een stap die niet met `<WERKMAP>` of `<DOCS>` beginnen zijn relatief aan de repo van die stap.
Een pad met "(nieuw)" erachter bestond op 2026-11-11 niet en wordt in die stap gemaakt.

**Let op, drie nummerreeksen die op elkaar lijken.** De app-repos hebben een eigen "bouwlijst P3" met nummers
P3-01...P3-14. Die nummers verschillen per repo. In dit plan staat er daarom altijd bij welke lijst het is:
"MG-bouwlijst P3-02" ([DM-MG], kop "I. Geprioriteerde bouwlijst fase P3 (alleen hiaten)" met correcties onder kop
"K.5 Correcties en aanscherpingen op de bouwlijst (§I)"), "MSO-bouwlijst P3-07" ([DM-MSO], kop "9. Geprioriteerde
bouwlijst fase P3 (alleen hiaten)" met correcties onder "11.5 Gecorrigeerde bouwlijst P3 (alleen wijzigingen t.o.v.
§9)" en "12. Contract 1.3 (conformiteitsronde 2026-11-10)") en "my_house-bouwlijst P3-05" ([DM-MH], kop "9.
Geprioriteerde bouwlijst fase P3 (alleen hiaten)" met correcties onder "11.6 Bijgestelde bouwlijst (vervangt de
genoemde regels van §9)" en "12. Contract 1.3 (2026-11-10)"). Stap-ID's van dit plan beginnen met `S-P3-`.
Bouwlijstnummers komen nooit in Excel, EVIDENCE of commits als ID.

---

## 1. Doel van de fase

Bron: [GATES], kop "Fase P3 — Eigen apps koppelen"; `<DOCS>/OVERDRACHT/OVERDRACHT_PROMPT.md`, hoofdstuk 4.

Na P3 geldt, gebouwd en in de simulator getest:

1. De Hub leest MediaGuard, Media Source Optimizer (MSO) en my_house via adapters in de Hub, op de bestaande routes
   van die apps. De gebruiker voert de sleutel of koppelcode in de Hub-UI in; er is geen enrollment voor bestaande
   apps ([CONTRACT], kop "2.3 Bestaande apps (MediaGuard, MSO, my_house, Jellyfin/Jelly Leon, Emby)", regel 2).
2. De Hub toont een incident- en downloadketen (MediaGuard plus MSO), een paneel voor het huis (my_house) en energie
   en kosten met herkomst (B14, B01-011).
3. De drie apps hebben hun P3-hiaten dicht: connectorroutes waar het contract ze vraagt, sleutels met scopes,
   bescherming tegen een nieuwer databaseschema, een healthcheck als gebruiker 568, een manifest en een
   installatiedocument voor de standaard TrueNAS Custom App.
4. my_house heeft een alles-in-een image en is zonder terminal en zonder YAML te installeren en te herstellen.
5. Voor I03, I04, I05 en I15...I20 bestaan controlelijsten of manifestkopieen in `jelly-leon-platform`.
6. De bestaande databases van de eigen apps blijven behouden. De MediaGuard-voortgang en de kijkgeschiedenis worden
   door geen enkele stap gewijzigd of onbereikbaar (HARDE EIS).

Wat P3 uitdrukkelijk NIET doet (no-go uit [GATES], zelfde kop): Prowlarr of SABnzbd wijzigen vanuit twee eigenaren,
de boiler schakelen, Gree aansturen zonder test op echte hardware. Verder niet in P3: herstel of zoeken in MediaGuard
via de Hub (wacht op BG-05), de alleen-lezen Emby-client (P4-0), de Jelly Leon-plugin en de Hub-koppeling daarvan (P4),
releases en tags, en alles wat een echte NAS, echte apparaten of accounts vraagt (STAPPEN_P6.md).

---

## 2. Gates

### 2.1 Gate ervoor (P2 naar P3)

Bron: [GATES], kop "Gate matrix" en kop "Fase P2 — Veilig automatiseren"; STAPPEN_P2.md, hoofdstuk "Fase-afsluiting".

- [ ] Gate P2 is afgevinkt door A-GATE (STAPPEN_P2.md, stap S-P2-910) en staat in `<DOCS>/OVERDRACHT/STATUS.md`.
- [ ] "Risk policy + privileged executor tested" is in de simulator aangetoond. Zonder deze regel mogen S-P3-110,
      S-P3-120 en S-P3-130 (schrijven via de Hub) niet starten. Alle andere stappen zijn alleen-lezen of raken alleen
      de eigen app en mogen wel starten zodra de regisseur dat vastlegt in STATUS.md.
- [ ] S-P2-600 (MediaGuard volgt twee mediaservers, `servers[]`) is klaar of S-P3-030 bouwt de terugval op de velden
      van het hoogste niveau.
- [ ] Contract staat op 1.3 en verandert niet tijdens de fase (V-018). Een contractwijziging is nooit een losse stap
      van A-BOUW.

Stappen die niet op Gate P2 wachten (geen schrijven via de Hub, geen executor): alle stappen in
`media-source-optimizer`, `media-guard-ultimate`, `my_house`, `home-control-hub` en `jelly-leon-platform`, en in
`ai-server-manager` alle stappen behalve S-P3-110, S-P3-120 en S-P3-130. De regisseur mag deze banen dus al laten lopen terwijl
P2 in `ai-server-manager` nog bezig is, MITS in die repo nooit twee schrijvers tegelijk werken: de baan
`ai-server-manager` van P3 start pas als de baan `ai-server-manager` van P2 stilligt.

### 2.2 Gate erna (P3 naar P4 en verder)

Bron: [GATES], kop "Gate matrix". [B03-FASE], kop "4. Gates", heeft geen eigen gate voor P3 (alleen "Gate P4-0 (vóór
elk B03-modulewerk)"); zie voor die gate het stappenbestand van P4-0.

| Gate (letterlijk uit de matrix) | Nodig voor | Wat P3 levert | Wat open blijft |
|---|---|---|---|
| MediaGuard/MSO API contract live verified | downloadgerelateerde acties | contracttests tegen de echte images in de simulator: S-P3-265, S-P3-645; adapters S-P3-030, S-P3-040 | "live" op de NAS: Geblokkeerd, STAPPEN_P6.md |
| my_house fysieke apparaten gevalideerd | climate actuation | inbedrijfstellingsgate S-P3-710; bewaakt schrijfpad S-P3-740 | echte apparaten: Geblokkeerd (D12, D13, D14), STAPPEN_P6.md onderdeel N-P6-06 |
| Δ-CONTRACT-MG | herstel/zoeken in MediaGuard via de Hub | alleen de voorwaarde: scopes S-P3-600 | besluit BG-05; daarna een contractronde (niet in dit bestand) |
| ZFS snapshots en pre-change database-export | schema- en infrastructuurwijzigingen | herstelrapporten van de apps: S-P3-100, S-P3-635 | echte pool: Geblokkeerd |

De afvinklijst van de gate staat in hoofdstuk 7 (stap S-P3-910).

---

## 3. Vaste regels voor elke stap (de regisseur geeft dit blok mee aan elke subagent)

1. **Taal en vragen.** Alles in het Nederlands, zakelijk, geen emoji. Een subagent vraagt de gebruiker niets. Alleen
   de regisseur legt een vraag voor, via een keuzemenu. Niets gokken: wat niet in een bestand staat is ONBEKEND.
   Geen pull requests zonder vraag aan de gebruiker.
2. **Git.** Werk op branch `ccr-c133d7a0-kuz1cv`. Voor elke push `git pull --rebase`. Nooit force-push. Nooit
   `git add -A` (V-022): voeg bestanden bij naam toe. Commitbericht in het Nederlands, zonder modelnaam, eindigend met
   de regel `Co-Authored-By: Claude <noreply@anthropic.com>`. Geen modelnaam in code, docs of commits. Geen tags, geen
   releases, geen `release`-workflow starten.
3. **Bewijs.** In `docs/platform-v2/EVIDENCE.json` van de repo en in Excel staat nooit "Gereed" of "Geslaagd".
   Gebouwd en in de simulator getest = status "Bezig" met validatie "Unit-getest" of "Sim-getest". Wat een echte NAS,
   echte hardware of een account vraagt = "Geblokkeerd" met de tekst "NIET GEVALIDEERD (echte NAS)", "NIET GEVALIDEERD
   (hardware)" of "NIET GEVALIDEERD (account)" plus wat er nodig is. Alleen ID's uit
   `<WERKMAP>/.lokaal/plan/uit/ALLE_IDS.txt` en contractpunten (C1.3-...) komen in EVIDENCE.
4. **Stand lezen** (alleen-lezen; afgekort als STAND `<repo>` `<ID ...>`):
   `python3 -c "import json,sys;[print(r['id'],r['status'],r['validatie'],sep=' | ') for r in json.load(open(sys.argv[1])) if r['id'] in sys.argv[2:]]" <WERKMAP>/<repo>/docs/platform-v2/EVIDENCE.json <ID> [<ID> ...]`
   Een ID zonder regel drukt niets af. Begin elke stap met `git -C <WERKMAP>/<repo> status --short` en
   `git -C <WERKMAP>/<repo> log --oneline -5`: staat er half werk van een ander, stop en meld het (V-015, V-016).
5. **HARDE EIS.** Kijkgeschiedenis, gebruikers, favorieten, hervatpunten en de MediaGuard-voortgang blijven altijd
   beschikbaar. Emby blijft werken en wordt nooit onderbroken of gewijzigd; de bestaande Emby-koppeling van
   MediaGuard blijft werken. Geen platformactie schrijft rechtstreeks in de database van Emby, Jelly Leon of
   MediaGuard ([CONTRACT], kop "2.3 ...", regel 7). Elke stap in `media-guard-ultimate` eindigt met het upgradebewijs
   op de bestaande fixture (POORTEN, P-media-guard-ultimate, kop "4. Volledig (CI-volgorde)", punt 3) met als
   verplichte uitkomst exitcode 0 en de regels "Upgrade: niets verloren" en "terugzetten: niets verloren". Het
   uitzonderingenbestand `tests/fixtures/aio/upgradebewijs-uitzonderingen.json` krijgt nooit een tabel van de
   voortgang erbij.
6. **Installatie.** De enige installatieweg is de standaard TrueNAS Custom App met een alles-in-een image per repo.
   Compose, YAML en `install.sh` zijn alleen voor ontwikkeling en CI en staan zo gemarkeerd. Documentatie beschrijft
   nooit een installatie- of herstelweg via een terminal (V-096).
7. **UI.** Elke stap met een scherm begint met A-ONTWERP in Peil (Tailwind 4, shadcn/ui, lucide; [PEIL]) en eindigt
   met R-ONTWERP. Schermafdrukken bevatten alleen testgegevens (V-063).
8. **Machine.** 14,5 GiB werkgeheugen. Zware commando's lopen na elkaar via de locks
   `<WERKMAP>/.lokaal/docker-build.lock`, `<WERKMAP>/.lokaal/gradle.lock` en `<WERKMAP>/.lokaal/stack.lock`, met
   `nice -n 10`. Is `free -m` "available" lager dan 3000 MB, start dan geen zwaar commando. Nooit
   `docker system prune -a`, `docker builder prune -a` of `docker volume prune` terwijl iets bouwt (V-011). Grote
   tijdelijke bestanden niet in `/tmp` (V-013): gebruik `TMPDIR` op schijf.
9. **Publieke repos.** Geen geheimen, geen IP-adressen, geen poolnamen, geen gegevens van de NAS of van de
   ontwikkelmachine in code, tests, docs of schermafdrukken (V-097). Voorbeelden gebruiken plaatshouders.
10. **Agents.** Subagents starten geen subagents. Nooit twee schrijvers in dezelfde repo. De regisseur geeft elke
    subagent een niveau mee (N1...N5). "standaard" betekent: A-VERKEN N2; A-BOUW, A-HERSTEL, A-ONTWERP, R-TECH,
    R-MANIFEST, R-EERLIJK, R-ONTWERP N3; R-VEILIG, R-HARDE-EIS, A-GATE N4. Bij moeilijkheid "hoog" werken A-BOUW en
    A-HERSTEL op N4. Het topmodel (N5) alleen waar de stap het noemt, of als escalatie nadat een stap op N3/N4 twee
    keer is vastgelopen (dan een poging van A-HERSTEL op N5, daarna een keuzemenu). Elke inzet van het topmodel komt in
    `<WERKMAP>/.lokaal/plan/uit/VOORTGANG.md`, tabel "Topmodel-inzet".
11. **Stap klaar** betekent alle vier: lokale poorten groen (POORTEN: P-<repo> plus de algemene poorten die de stap
    noemt), commit gepusht, de CI-run op precies die commit groen (POORTEN, kop "0.5 CI-controle na elke push (geldt
    voor alle repos)"), en EVIDENCE klopt met wat echt gemeten is (P-EERLIJK). Een overgeslagen test telt niet als
    groen (V-004).
12. **Namen die nog niet bestaan.** Een bestand, route of kolom met "(nieuw)" is een voorstel. Bestaat er in de repo
    al iets met dezelfde functie, dan gebruikt de bouwer dat en meldt hij de afwijking. Een migratienummer wordt altijd
    eerst vastgesteld met het commando in de stap.

### 3.1 Stand bij het schrijven van dit plan (gemeten op 2026-11-11; ronde 3 liep nog)

| Repo | Wat er voor P3 al is | Wat er nog niet is |
|---|---|---|
| ai-server-manager | catalogusprofielen met `BINNENKANT_P3 = "adapter_p3"` in `apps/api/src/hub/catalog/profiles.py`; plaatshouders voor Media, Huis en Kosten in `apps/web/src/app/`; vault, uitgaande verzoeken, monitorbronnen | adapters voor MediaGuard, MSO en my_house; schermen; EVIDENCE-regel B01-011; C1.3-ASM-19 en C1.3-ASM-21 "Niet gestart" |
| media-guard-ultimate | 1.2.2-basis, upgradebewijs, `system.hub_url` (B04-001 en B04-009 "Bezig") | map `apps/core/mediaguard/connector/`, `deploy/manifest/`, `tests/contract/mso/`; B04-002...B04-008 "Niet gestart"; C1.3-MGU-05, -06, -07, -09 "Niet gestart"; C1.3-MGU-08 "Bezig" (terugkeerpad open) |
| media-source-optimizer | alles-in-een image met proef van 10 scenario's; `systeem.hub_url`; B05-001...B05-006, B05-008, B05-010 "Bezig" | `apps/core/mso/connector_api/`, `deploy/manifest/`, `.env.example`, `tests/stack/mediaguard_contract.py`; B05-009 en C1.3-MSO-03...06 "Niet gestart" |
| my_house | 0.2.0 met compose-route; `HUB_URL`; B06-001...B06-006 en B06-008 "Bezig" | map `deploy/` (geen alles-in-een image, geen manifest); B06-007 en C1.3-MH-03...06 "Niet gestart" |
| home-control-hub | energiedomein met schema en routes die `501 capability_unavailable` geven (`apps/api/src/integrations/domains/energy/`); B14-001 "Bezig" | B14-002...B14-005 "Niet gestart" |
| jelly-leon-platform | controlelijsten I01 en I02; manifesten van de platformdiensten | regels en bestanden voor I03, I04, I05, I15...I20 |
| appstore-en-fork | register van bestaande apps en adoptiemanifest (B08-002, APP-01...APP-20: "Geblokkeerd", Sim-getest) | alleen meebewegen met gewijzigde A-documenten |

Deze stand veroudert. De regel "Al gedaan?" in elke stap is leidend, niet deze tabel.

---

## 4. Volgorde en banen

Een baan is een repo. Binnen een baan lopen de stappen in de volgorde van de tabel, een tegelijk (nooit twee
schrijvers in dezelfde repo). Banen lopen naast elkaar. "Zwaar: ja" betekent dat de stap een commando heeft dat een
lock uit regel 8 van hoofdstuk 3 vraagt; de stap zelf mag gewoon starten, alleen dat ene commando wacht op de lock.
"gepusht" in de kolom Vooraf betekent: de genoemde stap in een andere repo is klaar volgens regel 11 (V-017).

| Stap | Baan (repo) | Vooraf | Zwaar | Kan tegelijk met |
|---|---|---|---|---|
| S-P3-000 Stand opnemen | alle (alleen lezen) | geen | nee | niets (eerst) |
| S-P3-010 ADR adapters bestaande apps | ai-server-manager | S-P3-000; baan ai-server-manager van P2 ligt stil | nee | alle andere banen |
| S-P3-015 ADR upgradebewijs en sleutelrotatie | ai-server-manager | S-P3-010 | nee | alle andere banen |
| S-P3-020 Basis koppeling bestaande apps | ai-server-manager | S-P3-010 | nee | alle andere banen |
| S-P3-030 Adapter MediaGuard (lezen) | ai-server-manager | S-P3-020 | nee | alle andere banen |
| S-P3-040 Adapter MSO (lezen) | ai-server-manager | S-P3-020 | nee | alle andere banen |
| S-P3-050 Adapter my_house (lezen) | ai-server-manager | S-P3-020 | nee | alle andere banen |
| S-P3-060 Gezondheid binnenkant via adapters | ai-server-manager | S-P3-030, S-P3-040, S-P3-050 | nee | alle andere banen |
| S-P3-070 UI koppeling bestaande apps | ai-server-manager | S-P3-060 | nee | alle andere banen |
| S-P3-075 Incident- en downloadketen (backend) | ai-server-manager | S-P3-030, S-P3-040 | nee | alle andere banen |
| S-P3-080 UI scherm Media | ai-server-manager | S-P3-075 | nee | alle andere banen |
| S-P3-090 UI scherm Huis | ai-server-manager | S-P3-050 | nee | alle andere banen |
| S-P3-100 Back-updekking bestaande apps | ai-server-manager | S-P3-030, S-P3-040, S-P3-050; S-P2-090 | nee | alle andere banen |
| S-P3-110 Noodstop aan in MediaGuard via de Hub | ai-server-manager | Gate P2; S-P3-600 gepusht; S-P3-030 | nee | alle andere banen |
| S-P3-120 MSO-wijziging goedkeuren via de Hub | ai-server-manager | Gate P2; S-P3-240 gepusht; S-P3-040 | nee | alle andere banen |
| S-P3-130 Bewaakt schrijfpad naar my_house | ai-server-manager | Gate P2; S-P3-742 gepusht; S-P3-050; S-P3-015 | nee | alle andere banen |
| S-P3-150 Energie en kosten (backend) | ai-server-manager | S-P3-040; S-P3-310 gepusht | nee | alle andere banen |
| S-P3-160 UI scherm Kosten | ai-server-manager | S-P3-150 | nee | alle andere banen |
| S-P3-170 Hub: images, rooktest, OpenAPI, schermafdrukken | ai-server-manager | alle stappen van deze baan hierboven | ja (image-build) | geen andere image-build |
| S-P3-180 A-documenten: dekking vastleggen | ai-server-manager | S-P3-170 | nee | alle andere banen |
| S-P3-200 Opruimen en CI-start | media-source-optimizer | S-P3-000; besluit Z-10 | nee | alle andere banen |
| S-P3-205 Weiger nieuwer schema | media-source-optimizer | S-P3-200 | nee | alle andere banen |
| S-P3-210 Build-gegevens op de Systeem-kaart | media-source-optimizer | S-P3-200 | ja (stackproef voor de browsertest) | geen andere stackproef |
| S-P3-215 Terugkeerpad na inloggen | media-source-optimizer | S-P3-200 | nee | alle andere banen |
| S-P3-220 Machine-sleutel met scopes | media-source-optimizer | S-P3-200 | nee | alle andere banen |
| S-P3-230 Connector: lezen | media-source-optimizer | S-P3-220 | nee | alle andere banen |
| S-P3-240 Connector: wijzigingen met preview_hash | media-source-optimizer | S-P3-230 | nee | alle andere banen |
| S-P3-250 Healthcheck als 568 | media-source-optimizer | S-P3-200 | ja (image-build) | geen andere image-build |
| S-P3-255 Vaste digests en SBOM | media-source-optimizer | S-P3-250 | ja (image-build) | geen andere image-build |
| S-P3-260 Upgradetest vanaf de vorige image | media-source-optimizer | S-P3-205, S-P3-255 | ja (image-build, stackproef) | geen andere image-build of stackproef |
| S-P3-265 Contracttest tegen de echte MediaGuard-image | media-source-optimizer | S-P3-200 | ja (stackproef) | geen andere stackproef |
| S-P3-270 Opslag en groei | media-source-optimizer | S-P3-210 | ja (stackproef voor de browsertest) | geen andere stackproef |
| S-P3-280 Peil-ronde en schermbreedtes | media-source-optimizer | S-P3-270 | ja (stackproef voor de browsertest) | geen andere stackproef |
| S-P3-290 Manifest en installatiedocument | media-source-optimizer | S-P3-250, S-P3-255 | nee | alle andere banen |
| S-P3-300 Energiebron en dekkingsmatrix | home-control-hub | S-P3-010; baan home-control-hub van P2 ligt stil | nee | alle andere banen |
| S-P3-310 Energietijdreeks | home-control-hub | S-P3-300 | nee | alle andere banen |
| S-P3-320 Werklast-reserveringen | home-control-hub | S-P3-310 | nee | alle andere banen |
| S-P3-330 Advies over kosten | home-control-hub | S-P3-310, S-P3-320 | nee | alle andere banen |
| S-P3-340 Meldingen bij afwijkingen | home-control-hub | S-P3-310 | nee | alle andere banen |
| S-P3-350 Statuspagina energie | home-control-hub | S-P3-340 | nee | alle andere banen |
| S-P3-400 ADR en gereedschap voor I03...I20 | jelly-leon-platform | S-P3-000 | nee | alle andere banen |
| S-P3-410 Controlelijsten I03 en I04 | jelly-leon-platform | S-P3-400 | nee | alle andere banen |
| S-P3-420 Controlelijsten I15, I16, I17 | jelly-leon-platform | S-P3-400 | nee | alle andere banen |
| S-P3-430 Controlelijsten I18, I19, I20 | jelly-leon-platform | S-P3-400 | nee | alle andere banen |
| S-P3-440 I05: controlelijst en installatietekst | jelly-leon-platform | S-P3-400; keuze van de gebruiker over de I05-titels | nee | alle andere banen |
| S-P3-450 Manifestkopieen van de drie apps | jelly-leon-platform | S-P3-290, S-P3-660, S-P3-755 gepusht | nee | alle andere banen |
| S-P3-500 Register bestaande apps laten meebewegen | appstore-en-fork | S-P3-180 gepusht | nee | alle andere banen |
| S-P3-600 Scopes op API-sleutels | media-guard-ultimate | S-P3-000; S-P2-610 klaar | ja (image-build upgradebewijs) | geen andere image-build |
| S-P3-610 Connector deel 1: discover, health, healthz, readyz | media-guard-ultimate | S-P3-600 | ja (upgradebewijs) | geen andere image-build |
| S-P3-615 Connector deel 2: items, evidence, vijf datasets | media-guard-ultimate | S-P3-610 | ja (upgradebewijs) | geen andere image-build |
| S-P3-620 Events met cursor | media-guard-ultimate | S-P3-610 | ja (upgradebewijs) | geen andere image-build |
| S-P3-625 Bescherming tegen nieuwer schema | media-guard-ultimate | S-P3-600 | ja (upgradebewijs) | geen andere image-build |
| S-P3-630 Correlatie-ID | media-guard-ultimate | S-P3-610 | ja (upgradebewijs) | geen andere image-build |
| S-P3-635 Herstelrapport | media-guard-ultimate | S-P3-615 | ja (upgradebewijs) | geen andere image-build |
| S-P3-640 Opruimer bij een zieke pool | media-guard-ultimate | S-P3-600 | ja (upgradebewijs) | geen andere image-build |
| S-P3-645 Contracttest MSO-routes | media-guard-ultimate | S-P3-600 | ja (upgradebewijs) | geen andere image-build |
| S-P3-650 Healthcheck als 568 | media-guard-ultimate | S-P3-610 | ja (image-build) | geen andere image-build |
| S-P3-655 Terugkeerpad na inloggen | media-guard-ultimate | S-P3-600 | ja (upgradebewijs) | geen andere image-build |
| S-P3-660 Manifest en installatiedocument | media-guard-ultimate | S-P3-650 | ja (upgradebewijs) | geen andere image-build |
| S-P3-665 Vaste digests en SBOM | media-guard-ultimate | S-P3-650 | ja (image-build) | geen andere image-build |
| S-P3-670 Begrensde platformpauze | media-guard-ultimate | S-P3-600 | ja (upgradebewijs) | geen andere image-build |
| S-P3-675 Jellyfin: pad behouden en verversen | media-guard-ultimate | S-P3-620 | ja (upgradebewijs) | geen andere image-build |
| S-P3-680 Peil-ronde web en kernteksten | media-guard-ultimate | S-P3-615 | ja (upgradebewijs) | geen andere image-build |
| S-P3-685 Peil-ronde Android | media-guard-ultimate | S-P3-680 | ja (Gradle) | geen andere Gradle-build |
| S-P3-690 Poolstatus van de Hub | media-guard-ultimate | S-P3-640 | ja (upgradebewijs) | geen andere image-build |
| S-P3-700 Weiger nieuwer schema | my_house | S-P3-000; S-P2-700 klaar | nee | alle andere banen |
| S-P3-705 Boiler: regressietests | my_house | S-P3-700 | nee | alle andere banen |
| S-P3-710 Inbedrijfstellingsgate | my_house | S-P3-705 | nee | alle andere banen |
| S-P3-715 Tests sensor, TTL en herstart | my_house | S-P3-700 | nee | alle andere banen |
| S-P3-720 Alles-in-een image deel 1 | my_house | S-P3-700; besluit Z-08 | ja (image-build) | geen andere image-build |
| S-P3-725 Alles-in-een image deel 2: CI en rooktest | my_house | S-P3-720 | ja (image-build) | geen andere image-build |
| S-P3-730 Herstel en overstap zonder terminal | my_house | S-P3-725 | nee | alle andere banen |
| S-P3-735 Proef back-up A naar herstel B | my_house | S-P3-730 | ja (image-build, twee containers) | geen andere image-build of stackproef |
| S-P3-740 Verificatiekern ondertekend verzoek | my_house | S-P3-700; S-P3-015 gepusht | nee | alle andere banen |
| S-P3-742 Routes propose, apply en evidence | my_house | S-P3-740, S-P3-705, S-P3-710 | nee | alle andere banen |
| S-P3-745 UI Hub-sleutelset plakken | my_house | S-P3-740 | nee | alle andere banen |
| S-P3-750 Terugkeerpad na inloggen | my_house | S-P3-700 | nee | alle andere banen |
| S-P3-755 Manifest en installatiedocument | my_house | S-P3-725 | nee | alle andere banen |
| S-P3-765 Schermbreedtes en huishouding | my_house | S-P3-755 | nee | alle andere banen |
| S-P3-900 Bewijs samenvoegen: Excel en STATUS | ai-server-manager | alle stappen hierboven | nee | niets |
| S-P3-910 Gate P3 | alle (alleen lezen, behalve het gate-rapport) | S-P3-900 | ja (volledige poorten) | niets |

Kritiek pad: de baan `ai-server-manager` (20 stappen na elkaar) en de baan `media-guard-ultimate` (18 stappen, elk met
een upgradebewijs). Deze twee banen mogen nooit wachten op een vrije plek.

---

## 5. Startbezetting

Grenzen: hooguit 10 subagents tegelijk, hooguit 8 bouwketens, een schrijver per repo, zware commando's na elkaar.

**Bij het begin** (na S-P3-000, die alleen leest en door een A-VERKEN wordt gedaan):

| Plek | Keten | Start mits | Lock nodig bij start |
|---|---|---|---|
| 1 | S-P3-600 (media-guard-ultimate) | S-P2-610 en S-P2-620 klaar | `docker-build.lock` aan het einde (upgradebewijs) |
| 2 | S-P3-010 (ai-server-manager) | de baan van P2 in deze repo ligt stil | nee |
| 3 | S-P3-200 (media-source-optimizer) | besluit Z-10 genomen of "zonder besluit geldt" toegepast | nee |
| 4 | S-P3-700 (my_house) | S-P2-700 klaar | nee |
| 5 | S-P3-400 (jelly-leon-platform) | geen P2-keten actief in deze repo | nee |
| 6 | S-P3-300 (home-control-hub) | S-P3-010 klaar en de B11-baan van P2 ligt stil | nee |

Dat zijn vijf ketens direct en een zesde (plek 6) zodra S-P3-010 klaar is. Een keten gebruikt meestal een subagent
tegelijk en twee tijdens de review (R-TECH en R-VEILIG tegelijk). Met zes ketens blijft de bezetting dus binnen 10
subagents zolang hooguit vier ketens tegelijk in een dubbele review zitten; de regisseur laat een vijfde dubbele review
wachten.

**Daarna vrijkomend:**

- `jelly-leon-platform` is na S-P3-440 klaar tot S-P3-450 kan (die wacht op de drie manifesten). De plek komt vrij.
- `home-control-hub` is na S-P3-350 klaar. De plek komt vrij.
- `appstore-en-fork` heeft alleen S-P3-500, helemaal aan het einde.
- De eerste zware golf is in `media-guard-ultimate` (elke stap). De tweede zware golf begint als
  `media-source-optimizer` bij S-P3-250 komt en `my_house` bij S-P3-720. Dan staan drie banen voor
  `docker-build.lock`. De regisseur laat ze lopen (de lock regelt de volgorde) maar start er geen vierde zware keten
  bij, en kijkt voor elk zwaar commando naar `free -m`.
- Laat in een baan die wacht op een lock de volgende niet-zware stap niet voorgaan: de schrijver in die repo is nog
  bezig.

**Repos zonder werk in P3:** `jelly-leon`, `jelly-leon-web`, `jelly-leon-clients` en `zoeken-en-persoonlijke-ai`.
`appstore-en-fork` heeft tot S-P3-500 geen werk. In deze repos mag de regisseur een keten uit een andere fase of golf
laten lopen als de gate-matrix ([GATES], kop "Gate matrix") dat toestaat: werk van P4-0 of P4 in de drie
Jelly Leon-repos alleen na "Gate P4-0" ([B03-FASE], kop "4. Gates"); werk van P5 in `zoeken-en-persoonlijke-ai` alleen
volgens het stappenbestand van P5. Zo'n keten telt mee voor de grens van 8 ketens en voor de locks.

---

## 6. Stappen

**Niveaus.** "standaard" staat in regel 10 van hoofdstuk 3. Het topmodel (N5) wordt in P3 vijf keer ingezet:
S-P3-220 (R-VEILIG, kern van de authenticatie van MSO), S-P3-600 en S-P3-625 (R-HARDE-EIS, migratiecode van de
MediaGuard-database), S-P3-740 (R-VEILIG, kern van de verificatie van ondertekende verzoeken) en S-P3-910 (A-GATE aan
het einde van de fase). Dat is 5 op 81 stappen.

**Keten.** De standaardketen is A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL (alleen bij bevindingen) -> R-EERLIJK. Wat een
stap daarbovenop noemt met het woord VERPLICHT mag niet worden overgeslagen.

### S-P3-000 - Stand opnemen, half werk veiligstellen en open besluiten nalopen
- **Repo:** de zeven repos van P3 (alleen lezen) | **Fase:** P3 | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** geen eigen ID (controlestap); leest de stand van alle ID's uit hoofdstuk 8
- **Vooraf:** geen
- **Al gedaan?** `grep -n 'S-P3-000' <WERKMAP>/.lokaal/plan/uit/VOORTGANG.md` -> staat er een regel van vandaag, sla over. Is de regel ouder, doe de stap opnieuw.
- **Lees eerst:** dit bestand, hoofdstuk 3.1 en hoofdstuk 8; BESLUITEN, koppen "Z-02", "Z-03", "Z-08", "Z-10" en "BG-05"; STAPPEN_P2.md, hoofdstuk 4
- **Bouw:** (er wordt niets gebouwd en niets gecommit)
  1. Per repo (`ai-server-manager`, `media-guard-ultimate`, `media-source-optimizer`, `my_house`, `home-control-hub`, `jelly-leon-platform`, `appstore-en-fork`): `git -C <WERKMAP>/<repo> rev-parse --abbrev-ref HEAD`, `git -C <WERKMAP>/<repo> status --short` en `git -C <WERKMAP>/<repo> log --oneline -5`. Noteer ongecommit werk en bij welke stap het hoort.
  2. Draai STAND voor alle ID's uit hoofdstuk 8 en leg de uitkomst naast de tabel in hoofdstuk 3.1. Elk verschil betekent dat een stap (deels) al gedaan is: noteer het stap-ID.
  3. Draai de regel "Al gedaan?" van de eerste twee stappen van elke baan.
  4. Lees per open besluit de regel "Zonder besluit geldt": `grep -n -E '^#### (Z-02|Z-03|Z-08|Z-10|BG-05)' <WERKMAP>/.lokaal/plan/uit/BESLUITEN_EN_BLOKKADES.md`. Meld welke vragen nu in een keuzemenu moeten: Z-10 voor S-P3-200, Z-08 voor S-P3-720, Z-03 voor S-P3-015, Z-02 voor de statuspagina's, en de keuze over de I05-titels voor S-P3-440.
  5. Meet `df -h <WERKMAP>` en `free -m` en vergelijk met POORTEN, kop "0.3 Vaste omgeving en machineregels".
  6. Lever een rapport per repo: commit, half werk, stappen die al klaar zijn, open vragen. De regisseur zet het in `<WERKMAP>/.lokaal/plan/uit/VOORTGANG.md` onder "P3 - nulmeting" met de datum.
- **Tests (verplicht):** geen bouwtests. Negatieve controle: neem een ID dat volgens hoofdstuk 3.1 "Niet gestart" is en bevestig met STAND dat het niet zonder bewijsverwijzing op "Bezig" staat.
- **Poort:** P-EERLIJK op het rapport. Geen commit, dus geen P-GIT en geen CI.
- **Valkuilen:** V-015, V-016, V-017, V-034
- **Bewijs:** geen wijziging in EVIDENCE
- **Agents:** A-VERKEN -> R-EERLIJK. Korter omdat dit een zuivere controlestap is.
- **Niveau:** standaard
- **Stop en vraag als:** een repo niet op branch `ccr-c133d7a0-kuz1cv` staat; er ongecommit werk is dat bij geen stap hoort; de schijf- of geheugenregel uit POORTEN 0.3 niet gehaald wordt.

## Baan ai-server-manager (Hub: adapters, schermen, energie en kosten)

Werkmap `<WERKMAP>/ai-server-manager`. Poort: P-ai-server-manager. Een testbestand draaien:
`.venv/bin/python -m pytest -q <pad naar testbestand>`. Tests met database:
`PATH=/usr/lib/postgresql/16/bin:$PATH HUB_TEST_ADMIN_URL=postgresql://postgres@127.0.0.1:5432/postgres make test-integration`
(niet naast een andere volledige testsuite). Nieuwe migratie: het volgende vrije nummer in `apps/api/alembic/versions/`
(vaststellen met `ls apps/api/alembic/versions | tail -3`; op 2026-11-11 was `0012_acties_goedkeuringen.py` de laatste
en nog niet gecommit). Nieuw ADR: volgend vrij nummer (`ls docs/adr | tail -3`; op 2026-11-11 was ADR-0030 de laatste).
`make web-e2e` en `make web-review` hebben geen lock maar zijn volgens POORTEN (P-ai-server-manager, kop "4. Volledig
(CI-volgorde)", punt 8) wel zwaar: draai ze niet naast een andere volledige testsuite en alleen als `free -m`
"available" 3000 MB of meer is. De kolom "Zwaar" van de UI-stappen staat op "nee" omdat er geen lock nodig is.

### S-P3-010 - ADR: adapters voor de bestaande apps
- **Repo:** ai-server-manager | **Fase:** P3 | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** C1.3-ASM-21; raakt B04-002, B05-009, B06-006, B01-011 (alleen het besluit)
- **Vooraf:** S-P3-000 klaar; in deze repo werkt geen schrijver van P2
- **Al gedaan?** `ls <WERKMAP>/ai-server-manager/docs/adr | grep -i 'adapter'` -> een ADR over adapters voor bestaande apps betekent klaar; controleer dan alleen of de zes punten onder Bouw erin staan.
- **Lees eerst:** [CONTRACT], kop "2.3 Bestaande apps (MediaGuard, MSO, my_house, Jellyfin/Jelly Leon, Emby)" regels 1, 2, 3 en 5; [CONTRACT], koppen "3.10 Credentials van andere apps" en "6.2 Versheid (`observed_at` en `max_age`)"; [CONF], kop "1. ai-server-manager (Hub + executor; contracteigenaar)" punt C1.3-ASM-21; [DM-MG], kop "D. Hub-adapter: bestaande routes vs connectorcontract (§6) en enrollment (§3)"; [DM-MSO] en [DM-MH], kop "6. Hub-adapter: welke bestaande routes de Hub kan gebruiken (connectorcontract §6, enrollment §3)"
- **Bouw:**
  1. Schrijf `docs/adr/ADR-<nummer>-adapters-bestaande-apps.md` (nieuw). Alleen dit bestand en `CHANGELOG.md`.
  2. Leg per app vast welke routes de adapter leest. Uitgangspunt: de bestaande routes van vandaag, zodat de Hub-baan niet op de app-banen wacht. Leg vast of de adapter overstapt op `/connector/v1/*` zodra de app die levert (MediaGuard: S-P3-610 en S-P3-615; MSO: S-P3-230). my_house bouwt geen leesconnector (my_house-bouwlijst P3-03 vervalt; C1.3-MH-05 zegt: alleen als dit ADR erom vraagt).
  3. Plaats: modules onder `apps/api/src/hub/` (eis van C1.3-ASM-21). Voorstel `apps/api/src/hub/adapters/` (nieuw), een module per app. Opslag van een koppeling: kies tussen hergebruik van het patroon van `MonitorSource` (`apps/api/src/hub/models.py`, `apps/api/src/hub/monitoring/sources.py`) en een eigen tabel; motiveer.
  4. Geheimen: de gebruiker voert sleutel of koppelcode in de Hub-UI in; opslag versleuteld met alleen een vault-verwijzing; de UI toont nooit de waarde terug, alleen de laatste 4 tekens en de datum. Bron: [CONTRACT], kop "3.10 ...".
  5. Per app: de veldenwitte lijst (MediaGuard: `sessions`, `hold.reason`, `actions`, `tests` en `last` worden nooit opgeslagen, gelogd of getoond), `max_age` (standaard 900 s; strenger mag, soepeler nooit), de vertaling naar health (MSO: `offline` wordt `down`, `auth_failed` wordt `degraded`) en het gedrag bij onbereikbaar: `unknown`, oude gegevens gemarkeerd als verouderd.
  6. Energie: kies een eigenaar voor het lezen van de energiecijfers van my_house: de Hub-adapter of `home-control-hub` (energiedomein, B14). Leg vast welke bron B01-011 gebruikt zodat niets dubbel wordt geteld. Dit besluit stuurt S-P3-300 en S-P3-150.
- **Tests (verplicht):** `make lint && make test-unit` (bewijst dat er buiten `docs/` niets is geraakt). Negatief, door R-VEILIG: in de leeslijst van het ADR staat geen schrijvende route en geen bedienroute van my_house.
- **Poort:** P-ai-server-manager (snel) + P-GIT + P-EERLIJK + P-CONTRACT (het ADR mag het contract niet tegenspreken)
- **Valkuilen:** V-018, V-054; een ADR is geen contractwijziging: staat iets niet in het contract, meld het als contractpunt
- **Bewijs:** C1.3-ASM-21 naar "Bezig" met validatie "Niet getest" en de opmerking "besluit vastgelegd, bouw volgt"
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG (tegelijk; R-VEILIG VERPLICHT) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** het contract en een delta-matrix elkaar tegenspreken over een route of rol; het besluit over energie een wijziging in het contract zou vragen.

### S-P3-015 - ADR: MediaGuard-upgradebewijs in de Hub en rotatie bij een geplakte sleutelset
- **Repo:** ai-server-manager | **Fase:** P3 | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** C1.3-ASM-19 (alleen het deel "ADR in P3"); raakt C1.3-MH-04 (voorwaarde), B04-009
- **Vooraf:** S-P3-010 klaar; antwoord op Z-03 of de regel "zonder besluit geldt" (RV2 blijft zoals vastgelegd)
- **Al gedaan?** `grep -l -i 'upgradebewijs' <WERKMAP>/ai-server-manager/docs/adr/*.md` -> een ADR van na ADR-0030 dat beide onderwerpen behandelt betekent klaar.
- **Lees eerst:** [CONTRACT], kop "2.3 ..." regel 3 (geplakte sleutelset, vingerafdruk, pin) en regel 7 (HARDE EIS, onderdeel b); [CONTRACT], kop "4.5 Sleutelpinning, vingerafdruk en rotatie"; [CONF], kop "1. ai-server-manager ..." punt C1.3-ASM-19 en kop "8. my_house (bestaande app; P3)" punt C1.3-MH-04; [RUW], kop "1.3:my_house (Conformiteit)"; `<WERKMAP>/media-guard-ultimate/deploy/upgradebewijs/vorige-release.json`
- **Bouw:**
  1. Schrijf `docs/adr/ADR-<nummer>-mediaguard-upgradebewijs-en-sleutelrotatie.md` (nieuw).
  2. Deel A: hoe de Hub het upgradebewijs van een MediaGuard-release ziet (welk gegeven, van welke bron, hoe oud het mag zijn) en dat de Hub tot dat er is geen MediaGuard-update uitvoert. Het bewijs zelf blijft van MediaGuard (script `scripts/upgradebewijs.py` in die repo).
  3. Deel B: hoe een app met een geplakte Hub-sleutelset (my_house) een rotatie bevestigt, en dat de Hub niet roteert zolang die app de oude set gepind heeft (RV8).
  4. Leg vast wat de gebruiker ziet bij een geweigerde update (de reden, in gewone taal) en welke EVIDENCE-regel dit dekt.
  5. Noem wat NIET in P3 gebouwd wordt: het uitvoeren van een MediaGuard-update via de Hub.
- **Tests (verplicht):** `make lint && make test-unit`. Negatief, door R-HARDE-EIS: het ADR laat geen weg open waarlangs de Hub een MediaGuard-update start zonder bewijs.
- **Poort:** P-ai-server-manager (snel) + P-GIT + P-EERLIJK + P-CONTRACT + P-HARDE-EIS (leescontrole)
- **Valkuilen:** V-018, V-043, V-070
- **Bewijs:** C1.3-ASM-19 blijft de status houden die het had; voeg aan de opmerking toe "ADR upgradebewijs vastgelegd". Geen "Bezig" op grond van dit ADR alleen als de regel nu "Niet gestart" is: dan "Bezig", validatie "Niet getest".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG + R-HARDE-EIS (tegelijk; R-VEILIG en R-HARDE-EIS VERPLICHT) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** het ADR een nieuwe route in MediaGuard of my_house nodig heeft die niet in dit plan staat; het antwoord op Z-03 RV2 versoepelt (dan eerst de contractronde, niet deze stap).

### S-P3-020 - Hub: basis voor koppelingen met bestaande apps (opslag, geheim, uitgaand verkeer)
- **Repo:** ai-server-manager | **Fase:** P3 | **Omvang:** middel | **Moeilijkheid:** hoog | **Zwaar:** nee
- **Werkpakketten en tests:** C1.3-ASM-21; raakt B04-002, B05-009, B06-006
- **Vooraf:** S-P3-010 klaar (het ADR bepaalt map en opslag)
- **Al gedaan?** `ls <WERKMAP>/ai-server-manager/apps/api/src/hub/adapters 2>/dev/null; grep -rn 'adapter' <WERKMAP>/ai-server-manager/apps/api/alembic/versions/*.py | head -5` -> een basismodule plus een migratie betekent klaar. Bij een map zonder migratie of zonder tests: maak af wat er ligt, begin niet opnieuw.
- **Lees eerst:** het ADR van S-P3-010; [CONTRACT], koppen "3.10 Credentials van andere apps", "6.2 Versheid (`observed_at` en `max_age`)" en "5. Gemeenschappelijke API-regels"; `apps/api/src/hub/monitoring/sources.py` (bestaand patroon voor een bron met vault-geheim); `apps/api/src/hub/outbound.py`; `apps/api/src/hub/vault.py`
- **Bouw:**
  1. Opslag van een koppeling volgens het ADR: app, basisadres, vault-verwijzing, laatste 4 tekens, datum van invoer, laatste meting met `observed_at`. Migratie met het volgende vrije nummer, met een werkende downgrade.
  2. Basismodule in de map uit het ADR (voorstel `apps/api/src/hub/adapters/basis.py`, nieuw): een leesinterface (ontdekken, gezondheid, items) en een gedeelde functie voor uitgaande verzoeken. Elk verzoek loopt via `validate_base_url` en `request` uit `apps/api/src/hub/outbound.py`; redirects naar een andere host worden niet gevolgd.
  3. Routes (nieuw bestand onder `apps/api/src/hub/routers/`): koppeling maken, wijzigen, testen en verwijderen alleen voor een beheerder; lezen voor een ingelogde gebruiker. Het geheim is alleen-schrijven: geen enkel antwoord geeft het terug, alleen de laatste 4 tekens en de datum.
  4. Versheid: een meting ouder dan `max_age` (standaard 900 s, of strenger als de app dat opgeeft) wordt `unknown` met `reason_code: meting_verouderd`. Onbereikbaar wordt `unknown` of `down` volgens het ADR, nooit "gezond".
  5. Het geheim komt niet in logs, audit, foutmeldingen of het verzoeklog. Gebruik `apps/api/src/hub/redact.py`.
  6. Ontkoppelen verwijdert de vault-waarde en de opgeslagen metingen. De Hub schrijft daarbij niets in de app.
  7. `make openapi`, daarna `make openapi-check`.
- **Tests (verplicht):** nieuwe unit- en integratietests. Negatief: (a) een basisadres naar loopback of een metadata-adres wordt geweigerd; (b) de exacte testsleutel komt niet voor in het antwoord, in de logregels van de test of in de audit; (c) een gewone gebruiker krijgt 403 op maken en verwijderen; (d) een meting van 901 s oud geeft `unknown`. Commando's: `make lint && make test-unit`, daarna `PATH=/usr/lib/postgresql/16/bin:$PATH HUB_TEST_ADMIN_URL=postgresql://postgres@127.0.0.1:5432/postgres make test-integration`, daarna `make openapi-check`.
- **Poort:** P-ai-server-manager (snel en volledig) + P-VEILIG + P-CONTRACT + P-GIT + P-EERLIJK
- **Valkuilen:** V-003, V-043, V-048, V-051, V-066, V-094
- **Bewijs:** C1.3-ASM-21 blijft "Bezig", validatie "Unit-getest"
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG (tegelijk; R-VEILIG VERPLICHT) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4, A-HERSTEL N4 (moeilijkheid hoog); verder standaard
- **Stop en vraag als:** het ongecommitte P2-werk in `apps/api/src/hub/models.py` nog niet gepusht is (dan eerst de P2-baan afmaken); het ADR een keuze openlaat; de migratie een bestaande tabel van P2 moet wijzigen.

### S-P3-030 - Hub: adapter MediaGuard (alleen lezen)
- **Repo:** ai-server-manager | **Fase:** P3 | **Omvang:** middel | **Moeilijkheid:** hoog | **Zwaar:** nee
- **Werkpakketten en tests:** C1.3-ASM-21; Hub-deel van B04-002 en B04-003; I03-03-08 (bouwdeel)
- **Vooraf:** S-P3-020 klaar. S-P2-600 klaar of de terugval uit bouwpunt 3.
- **Al gedaan?** `ls <WERKMAP>/ai-server-manager/apps/api/src/hub/adapters | grep -i mediaguard` en `grep -rn 'hold.reason\|"sessions"' <WERKMAP>/ai-server-manager/apps/api/tests | head` -> module plus een test op de veldenwitte lijst betekent klaar.
- **Lees eerst:** [CONTRACT], kop "2.3 Bestaande apps (MediaGuard, MSO, my_house, Jellyfin/Jelly Leon, Emby)" regel 2 (MediaGuard) en regel 7; [DM-MG], kop "D. Hub-adapter: bestaande routes vs connectorcontract (§6) en enrollment (§3)"; `<WERKMAP>/media-guard-ultimate/docs/openapi/mediaguard.openapi.json`; het ADR van S-P3-010; [DM-MG], kop "B04-002 — Hub read-model adapter (F1)"
- **Bouw:**
  1. Module `mediaguard` in de adaptermap. Aanmelden met de kop `X-Api-Key`; de sleutel heet in MediaGuard `hub` en heeft rol viewer. De adapter controleert de rol met `GET /api/v1/auth/me` en weigert een sleutel met een hogere rol dan viewer voor het lezen (melding in gewone taal: "gebruik een sleutel met alleen leesrechten").
  2. Lees: `GET /api/v1/health`, `/api/v1/status`, `/api/v1/mediaserver/status`, `/api/v1/attention`, `/api/v1/wanted`, `/api/v1/downloads/health`, `/api/v1/encoding/jobs`, `/api/v1/storage/forecast`, `/api/v1/backups`. Controleer elk pad eerst in het OpenAPI-bestand; een pad dat daar niet staat wordt niet gebruikt maar gemeld.
  3. `/api/v1/mediaserver/status`: gebruik `servers[]` (`server_id`, `kind`, `label`, `connected`, `hold.active`). Ontbreekt `servers`, val terug op de velden van het hoogste niveau. Veldenwitte lijst: `sessions`, `hold.reason`, `actions`, `tests` en `last` worden nooit opgeslagen, gelogd of doorgegeven; de adapter bouwt een nieuw object uit de toegestane velden en kopieert niet het hele antwoord.
  4. Vijf datasets voor de vergelijking van B04-002: wanted, status, downloads, AV1, incidenten. De Hub bewaart alleen aantallen, toestanden, tijdstempels en verwijzingen (`wanted_id`), geen kopie van de inhoud.
  5. Noodstop: lees `emergency_stop` uit `/api/v1/status` (`active`, `since`). Is MediaGuard onbereikbaar, dan is de toestand `unknown`, niet "geen noodstop".
  6. Nagebootste MediaGuard voor de tests, in de vorm van het OpenAPI-bestand, zoals `apps/api/tests/unit/test_bronnen.py` dat doet voor andere bronnen.
- **Tests (verplicht):** unit- en integratietests. Negatief: (a) een antwoord met `sessions`, `hold.reason`, `actions`, `tests` en `last` erin: geen van die waarden staat daarna in de database, het log of het API-antwoord van de Hub; (b) sleutel ingetrokken (401) geeft een incident "sleutel ongeldig" en `unknown`; (c) time-out geeft `unknown` en de oude cijfers met het label verouderd; (d) antwoord zonder `servers` gebruikt de terugval. Commando: `.venv/bin/python -m pytest -q <pad naar het nieuwe testbestand>`, daarna `make lint && make test-unit`.
- **Poort:** P-ai-server-manager + P-VEILIG + P-CONTRACT + P-HARDE-EIS (de adapter doet alleen GET; zoek met `grep -n -i 'post\|put\|delete\|patch' <modulebestand>`) + P-GIT + P-EERLIJK
- **Valkuilen:** V-001, V-046, V-051, V-094. De simulator mag niet meer accepteren dan de echte MediaGuard: bouw hem uit het OpenAPI-bestand, niet uit de adapter.
- **Bewijs:** C1.3-ASM-21 "Bezig", validatie "Sim-getest". B04-002 en B04-003 zijn regels van `media-guard-ultimate` en worden hier niet gewijzigd. Tegen de echte MediaGuard op de NAS: "NIET GEVALIDEERD (echte NAS)", STAPPEN_P6.md onderdeel N-P6-05.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG + R-HARDE-EIS (tegelijk; R-VEILIG en R-HARDE-EIS VERPLICHT) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4, A-HERSTEL N4; verder standaard
- **Stop en vraag als:** een pad uit bouwpunt 2 niet in het OpenAPI-bestand staat; de vorm van `servers[]` afwijkt van het contract; voor een cijfer een hogere rol dan viewer nodig blijkt.

### S-P3-040 - Hub: adapter Media Source Optimizer (alleen lezen)
- **Repo:** ai-server-manager | **Fase:** P3 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** C1.3-ASM-21; Hub-deel van B05-009; I04-04-08 (bouwdeel)
- **Vooraf:** S-P3-020 klaar
- **Al gedaan?** `ls <WERKMAP>/ai-server-manager/apps/api/src/hub/adapters | grep -i -E 'mso|optimizer'` -> module met tests betekent klaar.
- **Lees eerst:** [CONTRACT], kop "2.3 ..." regel 2 (MSO: machine-sleutel met scope `read`) en regel 3; [DM-MSO], kop "6. Hub-adapter: welke bestaande routes de Hub kan gebruiken (connectorcontract §6, enrollment §3)" en kop "12. Contract 1.3 (conformiteitsronde 2026-11-10)"; `<WERKMAP>/media-source-optimizer/docs/openapi/media-source-optimizer.openapi.json`; het ADR van S-P3-010
- **Bouw:**
  1. Module `mso` in de adaptermap. Aanmelden met een machine-sleutel met scope `read`. Die sleutel bestaat pas na S-P3-220 in MSO; hoe de sleutel wordt meegestuurd (naam van de kop) is ONBEKEND - eerst vaststellen met: `grep -n -i 'machine\|x-api-key\|authorization' <WERKMAP>/media-source-optimizer/apps/core/mso/auth.py | head -30`. Tot S-P3-220 gepusht is test de adapter alleen tegen de nagebootste MSO.
  2. Zonder sleutel leesbaar: `GET /healthz`, `GET /api/v1/setup/status`. Met sleutel: `GET /api/v1/system/info`, `/api/v1/system/health`, `/api/v1/overview`, `/api/v1/usenet/failure-reasons`, `/api/v1/usenet/categories/diagnosis`, `/api/v1/mediaguard/compat`, `/api/v1/costs/summary`, `/api/v1/system/maintenance`, `/api/v1/changes?status=preview`. Controleer elk pad in het OpenAPI-bestand.
  3. Vertaling naar de health van het contract: `offline` wordt `down`, `auth_failed` wordt `degraded` met een `reason_code`, geen gegevens wordt `unknown`. De slechtste check bepaalt de toestand van de app.
  4. Foutformaat van MSO is `{detail, code, correlation_id}`: neem `correlation_id` over in het incident van de Hub.
  5. De Hub gebruikt nooit een gebruikerswachtwoord of een sessie met CSRF van MSO. Een poging om zo te koppelen wordt in de koppelroute geweigerd.
  6. Open wijzigingen (`/api/v1/changes?status=preview`) worden alleen getoond met een link naar MSO. Goedkeuren komt in S-P3-120.
- **Tests (verplicht):** unit- en integratietests tegen een nagebootste MSO. Negatief: (a) sleutel zonder scope `read` (403) geeft een incident en `unknown`; (b) `auth_failed` van een koppeling in MSO wordt `degraded`, niet `healthy`; (c) een koppeling met gebruikersnaam en wachtwoord wordt geweigerd. Commando: `.venv/bin/python -m pytest -q <pad naar het nieuwe testbestand>`, daarna `make lint && make test-unit`.
- **Poort:** P-ai-server-manager + P-VEILIG + P-CONTRACT + P-GIT + P-EERLIJK
- **Valkuilen:** V-001, V-017, V-051, V-094
- **Bewijs:** C1.3-ASM-21 "Bezig", "Sim-getest". B05-009 is een regel van `media-source-optimizer` (S-P3-230). Echte MSO op de NAS: "NIET GEVALIDEERD (echte NAS)", STAPPEN_P6.md onderdeel N-P6-05.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG (tegelijk; R-VEILIG VERPLICHT) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** de kop voor de machine-sleutel na S-P3-220 anders blijkt dan de adapter aanneemt (dan de adapter aanpassen, niet MSO); een pad uit bouwpunt 2 ontbreekt.

### S-P3-050 - Hub: adapter my_house (alleen lezen, koppelcode)
- **Repo:** ai-server-manager | **Fase:** P3 | **Omvang:** middel | **Moeilijkheid:** hoog | **Zwaar:** nee
- **Werkpakketten en tests:** C1.3-ASM-21; Hub-deel van B06-006; raakt B06-003 (boiler: alleen meten)
- **Vooraf:** S-P3-020 klaar
- **Al gedaan?** `ls <WERKMAP>/ai-server-manager/apps/api/src/hub/adapters | grep -i -E 'my_house|myhouse|huis'` -> module met tests betekent klaar.
- **Lees eerst:** [CONTRACT], kop "2.3 ..." regel 2 (my_house: koppelcode, rol viewer) en regel 3; [DM-MH], kop "6. Hub-adapter: welke bestaande routes de Hub kan gebruiken (connectorcontract §6, enrollment §3)"; `<WERKMAP>/my_house/docs/openapi/my_house.openapi.json`; het ADR van S-P3-010; [B06], kop "5. Niet-regressie, randgevallen en verbodsbepalingen"
- **Bouw:**
  1. Module `my_house` in de adaptermap. Koppelen: de gebruiker maakt in my_house een koppelcode met rol viewer en voert die in de Hub in. De Hub wisselt in met `POST /api/v1/pairing/redeem` (velden `code`, `device_name`) en bewaart het token in de vault. De koppelcode zelf wordt na het inwisselen niet bewaard.
  2. Vernieuwen: `POST /api/v1/clients/self/refresh` ruim voor het verlopen (180 dagen). Mislukt het, dan een incident en `unknown`, geen stille uitval.
  3. Lees: `GET /api/v1/health`, `/api/v1/system/status`, `/api/v1/homes`, `/api/v1/homes/{id}/overview`, `/api/v1/homes/{id}/zones`, `/api/v1/homes/{id}/lights`, `/api/v1/homes/{id}/alerts`, `/api/v1/homes/{id}/devices`, `/api/v1/system/settings`. Energie alleen als het ADR van S-P3-010 de Hub als lezer aanwijst.
  4. Verboden in deze module: elke bedienroute (`POST /zones/{id}/command`, `/zones/{id}/resume`, `/lights/groups/{id}`, `/alerts/{id}/ack`) en de routes voor audit, diagnose, back-up en gebruikers. De module bevat alleen GET plus de twee POST-routes uit bouwpunt 1 en 2.
  5. Foutformaat van my_house is `{"detail":{"code","message"}}`: vertaal `code` naar een `reason_code` van de Hub.
  6. De link naar my_house komt uit `lan_url` of `remote_url` van `/api/v1/system/settings`. Valideer het adres met `validate_base_url` voor het wordt getoond; een ongeldig adres geeft geen link.
- **Tests (verplicht):** unit- en integratietests tegen een nagebootste my_house. Negatief: (a) een token met een hogere rol dan viewer wordt geweigerd bij het koppelen; (b) een verlopen token (401) geeft een incident en `unknown`; (c) een test die de module doorzoekt en faalt als er een bedienroute in staat; (d) een `lan_url` met een ander schema dan http of https geeft geen link. Commando: `.venv/bin/python -m pytest -q <pad naar het nieuwe testbestand>`, daarna `make lint && make test-unit`.
- **Poort:** P-ai-server-manager + P-VEILIG + P-CONTRACT + P-GIT + P-EERLIJK
- **Valkuilen:** V-001, V-043, V-051, V-064, V-094
- **Bewijs:** C1.3-ASM-21 "Bezig", "Sim-getest". B06-006 is een regel van `my_house`. Echte my_house op de NAS: "NIET GEVALIDEERD (echte NAS)", STAPPEN_P6.md onderdeel N-P6-06.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG (tegelijk; R-VEILIG VERPLICHT) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4, A-HERSTEL N4; verder standaard
- **Stop en vraag als:** `POST /api/v1/pairing/redeem` een thuisadres of een ander veld eist dat de Hub niet heeft; het token meer kan dan lezen.

### S-P3-060 - Hub: gezondheid van de binnenkant via de adapters
- **Repo:** ai-server-manager | **Fase:** P3 | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** C1.3-ASM-21; raakt B04-002, B05-009, B06-006
- **Vooraf:** S-P3-030, S-P3-040 en S-P3-050 klaar
- **Al gedaan?** `grep -n 'adapter_p3' <WERKMAP>/ai-server-manager/apps/api/src/hub/monitoring/health.py` -> staat daar nog de tak die "volgt in P3" teruggeeft, dan is de stap open. Leest de tak een adaptermeting, dan klaar.
- **Lees eerst:** `apps/api/src/hub/monitoring/health.py` (de tak voor `adapter_p3`); `apps/api/src/hub/catalog/profiles.py` (`BINNENKANT_P3`); [CONTRACT], kop "6.2 Versheid (`observed_at` en `max_age`)"; `apps/api/tests/unit/test_catalogus.py`
- **Bouw:**
  1. Laat de tak voor `adapter_p3` in `apps/api/src/hub/monitoring/health.py` de laatste adaptermeting gebruiken: toestand, `observed_at`, `reason_code`.
  2. Geen koppeling ingesteld: toestand `unknown` met een reden in gewone taal ("nog niet gekoppeld") en een verwijzing naar het koppelscherm. Nooit "gezond".
  3. Het commentaar bij `BINNENKANT_P3` in `apps/api/src/hub/catalog/profiles.py` aanpassen: het is nu gebouwd. De waarde `adapter_p3` blijft (anders breekt `apps/web/src/app/apps/[id]/AppDetail.tsx`).
  4. `apps/web/src/app/apps/[id]/AppDetail.tsx`: de tekst voor `adapter_p3` toont de echte toestand in plaats van "volgt in P3". Alleen tekst en bestaande Peil-onderdelen; geen nieuw scherm.
  5. Incidentregel: adapter drie metingen achter elkaar `unknown` of `down` geeft een incident (regels in `apps/api/src/hub/incidents/rules.py`).
- **Tests (verplicht):** `apps/api/tests/unit/test_catalogus.py` en `apps/api/tests/unit/test_incident_regels.py` uitbreiden. Negatief: geen koppeling geeft `unknown`; een meting ouder dan `max_age` geeft `unknown` met `meting_verouderd`. Commando: `make lint && make test-unit && make web-lint && make web-test`.
- **Poort:** P-ai-server-manager + P-CONTRACT + P-PEIL (alleen tekst gewijzigd) + P-GIT + P-EERLIJK
- **Valkuilen:** V-051, V-052
- **Bewijs:** C1.3-ASM-21 "Bezig", "Sim-getest"
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK. Geen A-ONTWERP: er komt geen nieuw scherm of onderdeel bij; R-TECH controleert dat.
- **Niveau:** standaard
- **Stop en vraag als:** de wijziging in `AppDetail.tsx` meer wordt dan een tekst (dan hoort het bij S-P3-070).

### S-P3-070 - Hub-UI: bestaande apps koppelen (sleutel of koppelcode invoeren)
- **Repo:** ai-server-manager | **Fase:** P3 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** C1.3-ASM-21; I03-03-08 en I04-04-08 (bouwdeel); Hub-deel van B06-006
- **Vooraf:** S-P3-060 klaar
- **Al gedaan?** `grep -rln -i 'koppelcode\|laatste 4' <WERKMAP>/ai-server-manager/apps/web/src/app/instellingen/diensten` -> een scherm met invoer voor de drie apps betekent klaar.
- **Lees eerst:** [CONTRACT], kop "3.10 Credentials van andere apps"; [PEIL] (`<DOCS>/ONTWERPTAAL.md`); de bestaande schermen in `apps/web/src/app/instellingen/diensten`; het ADR van S-P3-010; POORTEN, kop "P-PEIL"
- **Bouw:**
  1. A-ONTWERP eerst: ontwerp in Peil voor het onderdeel "Bestaande apps" in `apps/web/src/app/instellingen/diensten`: per app een kaart met toestand, laatste meting, invoer, knop "Testen" en "Ontkoppelen". Met de toestanden leeg, bezig, fout, verouderd en gekoppeld.
  2. Invoer: MediaGuard en MSO een sleutel, my_house een koppelcode. Het veld is van het type wachtwoord, wordt nooit vooraf gevuld en na opslaan geleegd. Getoond worden alleen de laatste 4 tekens en de datum.
  3. Uitleg per app in gewone taal waar de gebruiker de sleutel of code maakt (in de app zelf, met welke rol). Geen terminalopdrachten.
  4. Fouten in gewone taal met wat de gebruiker kan doen: sleutel ongeldig, te hoge rol, app onbereikbaar, adres geweigerd.
  5. Ontkoppelen vraagt een bevestiging en zegt wat er gebeurt: de Hub vergeet de sleutel; in de app zelf trekt de gebruiker de sleutel in.
  6. Toetsenbord en schermlezer: alle knoppen bereikbaar, foutmelding gekoppeld aan het veld.
- **Tests (verplicht):** componenttests en een browsertest in `apps/web/e2e/` (nieuw bestand, genummerd tussen `10-schermen.spec.ts` en `90-afsluiting.spec.ts`). Negatief: (a) na opslaan staat de sleutel nergens in de pagina (zoek de testwaarde in de DOM); (b) een gewone gebruiker ziet de invoer niet; (c) fouttoestand toont de reden, geen lege kaart. Commando's: `make web-lint && make web-test`, `make web-e2e`, `make web-review`.
- **Poort:** P-ai-server-manager + P-PEIL + P-VEILIG + P-GIT + P-EERLIJK
- **Valkuilen:** V-058, V-061, V-063, V-094
- **Bewijs:** C1.3-ASM-21 "Bezig", "Sim-getest". I03-03-08 en I04-04-08 zijn regels van `jelly-leon-platform` (S-P3-410).
- **Agents:** A-VERKEN -> A-ONTWERP -> A-BOUW -> R-TECH + R-VEILIG (tegelijk; R-VEILIG VERPLICHT) -> A-HERSTEL -> R-ONTWERP (VERPLICHT) -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** het ontwerp een onderdeel nodig heeft dat niet in Peil bestaat (dan eerst een Peil-wijziging via ADR-0015, niet lokaal oplossen).

### S-P3-075 - Hub: incident- en downloadketen over MediaGuard en MSO (backend)
- **Repo:** ai-server-manager | **Fase:** P3 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** Hub-deel van B04-004 en B04-008; raakt B05-002, B05-003, B05-006
- **Vooraf:** S-P3-030 en S-P3-040 klaar
- **Al gedaan?** `grep -rn -i 'keten\|chain' <WERKMAP>/ai-server-manager/apps/api/src/hub/incidents/*.py | head` en `grep -rn 'wanted_id' <WERKMAP>/ai-server-manager/apps/api/src/hub | head -3` -> een ketenfunctie met tests betekent klaar.
- **Lees eerst:** [DM-MG], kop "B04-004 — Diagnoseketen met MSO (F2)"; [B04], kop "3. API en integratie-contracten"; [B05], kop "3. API en integratie-contracten"; `apps/api/src/hub/incidents/engine.py` en `view.py`; [CONTRACT], kop "5. Gemeenschappelijke API-regels" (correlatie)
- **Bouw:**
  1. Een ketenfunctie in `apps/api/src/hub/incidents/` die voor een ontbrekende aflevering de stappen naast elkaar zet: MediaGuard (`GET /api/v1/wanted/{id}/diagnosis?cached=true`, `/api/v1/downloads/failures`), MSO (`/api/v1/usenet/failure-reasons`, `/api/v1/usenet/categories/diagnosis`, `/api/v1/mediaguard/compat`). Alleen de gecachte diagnose: de interactieve vraagt een hogere rol en wordt niet gebruikt.
  2. Per schakel: eigenaar (`mediaguard` of `media-source-optimizer`), oorzaakcode van de eigenaar, `observed_at`, en een link naar het scherm van de eigenaar. De Hub verzint geen oorzaak: ontbreekt een schakel, dan staat er "onbekend" met de reden.
  3. De Hub bewaart alleen verwijzingen (`wanted_id`, wijzigings-ID van MSO), geen kopie van bronstatistieken.
  4. Elk verzoek in een keten krijgt dezelfde kop `X-Correlation-Id` (een UUID). MediaGuard neemt die over na S-P3-630; tot dan is de kop onschadelijk.
  5. Route om de keten te lezen (ingelogde gebruiker), in het bestaande incidentenrouterbestand `apps/api/src/hub/routers/incidents.py`. OpenAPI bijwerken.
  6. De keten biedt geen actie aan: geen herzoek, geen verwijderen, geen opruimen. Alleen links.
- **Tests (verplicht):** unit- en integratietests met de nagebootste apps uit S-P3-030 en S-P3-040. Negatief: (a) MSO onbereikbaar: de keten toont de MediaGuard-schakels en "onbekend" voor MSO, geen fout 500; (b) een keten bevat geen veld uit de verboden lijst van S-P3-030; (c) twee verzoeken van dezelfde keten dragen dezelfde correlatiewaarde. Commando: `make lint && make test-unit`, daarna de integratietests (commando in de kop van deze baan), daarna `make openapi-check`.
- **Poort:** P-ai-server-manager + P-CONTRACT + P-GIT + P-EERLIJK
- **Valkuilen:** V-046, V-051, V-066
- **Bewijs:** C1.3-ASM-21 "Bezig", "Sim-getest". De integrale scenario's (EX39...EX42) horen bij STAPPEN_P6.md, stap S-P6-16.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** voor een schakel een schrijvende of interactieve route nodig lijkt.

### S-P3-080 - Hub-UI: scherm Media (MediaGuard en MSO)
- **Repo:** ai-server-manager | **Fase:** P3 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** Hub-deel van B04-002, B04-003, B04-004, B04-005, B04-008 en B05-009
- **Vooraf:** S-P3-075 klaar
- **Al gedaan?** `grep -n 'media' <WERKMAP>/ai-server-manager/apps/web/src/lib/nav.ts` en `ls <WERKMAP>/ai-server-manager/apps/web/src/app/media` -> staat `media` nog in `PLANNED` en is er alleen `page.tsx` met de plaatshouder, dan is de stap open.
- **Lees eerst:** [B04], kop "1. Concrete schermen en gebruikersreizen"; [B05], kop "1. Concrete schermen en gebruikersreizen"; [PEIL]; `apps/web/src/app/media/page.tsx` en `apps/web/src/lib/nav.ts`; [DM-MG], koppen "B04-003 — Noodstop en risicocoördinatie (F1)" en "B04-005 — Globale resource-scheduler-hooks (F2)"
- **Bouw:**
  1. A-ONTWERP eerst: ontwerp in Peil voor het scherm Media met de toestanden leeg (niet gekoppeld), bezig, fout, verouderd en gevuld, op smal en breed scherm.
  2. Blok MediaGuard: per mediaserver het label, verbonden ja/nee en of een kijkpauze actief is (alleen ja/nee). De vijf cijfers (wanted, status, downloads, AV1, incidenten) met tijdstip van meting. Een balk "gepauzeerd" als de noodstop aan staat, met sinds wanneer.
  3. Blok MSO: gezondheid, open wijzigingen (aantal, met link naar MSO), kostenregel met herkomst.
  4. "Waarom ontbreekt dit?": de keten uit S-P3-075, per schakel de eigenaar en een link naar diens scherm.
  5. Zekerheid eerlijk tonen: elk cijfer heeft het label gemeten, geschat of onbekend (Peil-onderdeel ZekerheidLabel). Verouderd of onbereikbaar toont het oude cijfer grijs met "laatst gemeten ...", nooit als actueel.
  6. Geen actieknoppen voor MediaGuard of MSO op dit scherm in deze stap. `media` uit `PLANNED` in `apps/web/src/lib/nav.ts` halen; het deel voor Jelly Leon blijft gepland (P4) en staat zo op het scherm.
- **Tests (verplicht):** componenttests en browsertest. Negatief: (a) adapter `unknown`: het scherm toont "onbekend", niet nul problemen; (b) noodstop aan: de balk staat er en er is geen knop om hem uit te zetten; (c) geen koppeling: het scherm verwijst naar het koppelscherm. Commando's: `make web-lint && make web-test`, `make web-e2e`, `make web-review`.
- **Poort:** P-ai-server-manager + P-PEIL + P-GIT + P-EERLIJK
- **Valkuilen:** V-051, V-058, V-061, V-063
- **Bewijs:** C1.3-ASM-21 "Bezig", "Sim-getest"
- **Agents:** A-VERKEN -> A-ONTWERP -> A-BOUW -> R-TECH -> A-HERSTEL -> R-ONTWERP (VERPLICHT) -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** het ontwerp een actieknop voor MediaGuard nodig lijkt te hebben (wacht op BG-05).

### S-P3-090 - Hub-UI: scherm Huis (my_house, alleen kijken)
- **Repo:** ai-server-manager | **Fase:** P3 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** Hub-deel van B06-006; raakt B06-003, B06-004, B06-005
- **Vooraf:** S-P3-050 klaar
- **Al gedaan?** `grep -n 'huis' <WERKMAP>/ai-server-manager/apps/web/src/lib/nav.ts` en `ls <WERKMAP>/ai-server-manager/apps/web/src/app/huis` -> staat `huis` nog in `PLANNED`, dan is de stap open.
- **Lees eerst:** [B06], koppen "1. Concrete schermen en gebruikersreizen" en "5. Niet-regressie, randgevallen en verbodsbepalingen"; [PEIL]; `apps/web/src/app/huis/page.tsx`; [DM-MH], kop "B06-006 — Hub-integratie (F3, P1)"
- **Bouw:**
  1. A-ONTWERP eerst: ontwerp in Peil met de toestanden leeg, bezig, fout, verouderd en gevuld.
  2. Toon per woning: zones met gemeten temperatuur en doel, lichtgroepen aan of uit, open meldingen, veilige modus, laatste back-up volgens `GET /api/v1/system/status`.
  3. Alleen kijken. Er is geen knop die iets schakelt. Wie wil bedienen krijgt een link "Open in my_house".
  4. De boiler staat er alleen als meting. Er is geen schakelaar en geen tekst die suggereert dat schakelen kan.
  5. Sensorwaarden ouder dan de grens van my_house krijgen het label verouderd.
  6. `huis` uit `PLANNED` in `apps/web/src/lib/nav.ts` halen.
- **Tests (verplicht):** componenttests en browsertest. Negatief: (a) de pagina bevat geen knop of formulier dat een POST naar de adapter doet; (b) verlopen token: het scherm toont "koppeling verlopen" met een verwijzing naar het koppelscherm; (c) een verouderde sensor wordt niet als actueel getoond. Commando's: `make web-lint && make web-test`, `make web-e2e`, `make web-review`.
- **Poort:** P-ai-server-manager + P-PEIL + P-GIT + P-EERLIJK
- **Valkuilen:** V-051, V-058, V-061, V-063, V-064
- **Bewijs:** C1.3-ASM-21 "Bezig", "Sim-getest". Echte apparaten: "NIET GEVALIDEERD (hardware)", STAPPEN_P6.md onderdeel N-P6-06.
- **Agents:** A-VERKEN -> A-ONTWERP -> A-BOUW -> R-TECH -> A-HERSTEL -> R-ONTWERP (VERPLICHT) -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** de gebruiker om een bedienknop in de Hub vraagt (dat is S-P3-130 en vraagt Gate P2).

### S-P3-100 - Hub: back-updekking van de bestaande apps en het Emby-exportarchief
- **Repo:** ai-server-manager | **Fase:** P3 | **Omvang:** middel | **Moeilijkheid:** hoog | **Zwaar:** nee
- **Werkpakketten en tests:** B12-003 (dekking); C1.3-ASM-21 (deel Δ-HUB-3); Hub-deel van B04-006, B05-010 en B06-008
- **Vooraf:** S-P3-030, S-P3-040 en S-P3-050 klaar; S-P2-090 klaar
- **Al gedaan?** `grep -n -i 'mediaguard\|emby\|exportarchief' <WERKMAP>/ai-server-manager/apps/api/src/hub/backup/coverage.py | head` -> dekkingsitems voor de drie apps en het Emby-exportarchief betekent klaar.
- **Lees eerst:** [CONTRACT], kop "2.3 ..." regel 7 en regel 8; `<DOCS>/02_BOUWPLANNEN/B12_BACKUP_HERSTEL.md`, kop "3. API en integratie-contracten"; `apps/api/src/hub/backup/coverage.py` (`CoverageInputs`, `compute`); [DM-MG], kop "B04-006 — Back-up en rollback-integratie (F3)"; `apps/api/tests/unit/test_coverage.py`
- **Bouw:**
  1. Breid `CoverageInputs` en `compute` in `apps/api/src/hub/backup/coverage.py` uit met een eigen back-upmelding per bestaande app, gelezen door de adapter.
  2. MediaGuard: `GET /api/v1/backups` (en na S-P3-635 het herstelrapport). Een ontbrekende of ongeverifieerde back-up van een onderdeel maakt de dekking `degraded`, nooit groen.
  3. MSO: `GET /api/v1/system/maintenance` (back-upruimte, veroudering). my_house: het onderdeel back-up in `GET /api/v1/system/status`.
  4. Emby-exportarchief als dekkingsitem (contract, kop "2.3 ...", regel 8): aanwezig, leeftijd, plaats in de back-up. Het archief zelf wordt in P3 niet gemaakt; ontbreekt het, dan staat het item op "onbekend" met de reden "nog niet gemaakt (overname, P4-0)".
  5. De Hub leest alleen. Hij start geen back-up of herstel in een bestaande app en schrijft niet in een database van een app.
  6. Toon de nieuwe items in het bestaande scherm `apps/web/src/app/backups/BackupsScreen.tsx` met de bestaande onderdelen (geen nieuw schermontwerp; alleen extra rijen).
- **Tests (verplicht):** `apps/api/tests/unit/test_coverage.py` uitbreiden. Negatief: (a) MediaGuard-back-up ouder dan de grens geeft `degraded`; (b) adapter onbereikbaar geeft "onbekend", niet "gedekt"; (c) Emby-archief ontbreekt geeft "onbekend" en telt niet als gedekt. Commando: `.venv/bin/python -m pytest -q apps/api/tests/unit/test_coverage.py`, daarna `make lint && make test-unit && make web-lint && make web-test`.
- **Poort:** P-ai-server-manager + P-HARDE-EIS + P-CONTRACT + P-GIT + P-EERLIJK
- **Valkuilen:** V-051, V-085; een dekking die groen wordt zonder verse meting is de fout die deze stap moet voorkomen
- **Bewijs:** B12-003 blijft "Bezig" ("Sim-getest"); C1.3-ASM-21 "Bezig". Echte pool en echte back-ups: "NIET GEVALIDEERD (echte NAS)", STAPPEN_P6.md onderdeel N-P6-02.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-HARDE-EIS (tegelijk; R-HARDE-EIS VERPLICHT) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4, A-HERSTEL N4; verder standaard
- **Stop en vraag als:** de dekking alleen te bepalen is door in een database van een app te lezen; het back-upwerk van P2 (S-P2-090) nog niet gepusht is.

### S-P3-110 - Hub: noodstop AAN in MediaGuard via het goedkeuringspad
- **Repo:** ai-server-manager | **Fase:** P3 | **Omvang:** middel | **Moeilijkheid:** hoog | **Zwaar:** nee
- **Werkpakketten en tests:** Hub-deel van B04-003; C1.3-ASM-19 (deel MediaGuard); raakt C1.3-MGU-05, EX18, EX19, EX20
- **Vooraf:** Gate P2 afgevinkt; S-P3-600 gepusht (scope `emergency_stop:on` bestaat in MediaGuard); S-P3-030 klaar
- **Al gedaan?** `grep -n -i 'mediaguard\|emergency' <WERKMAP>/ai-server-manager/policy/acties.yaml` en `grep -rn 'emergency-stop' <WERKMAP>/ai-server-manager/apps/api/src/hub | head -3` -> een actie in het beleid plus een aanroep met tests betekent klaar.
- **Lees eerst:** [CONTRACT], kop "2.3 Bestaande apps (MediaGuard, MSO, my_house, Jellyfin/Jelly Leon, Emby)" regel 2 (MediaGuard) en regel 3; [CONTRACT], kop "8. Risicobeleid, voorstel, goedkeuring en executor"; [DM-MG], kop "B04-003 — Noodstop en risicocoördinatie (F1)"; `policy/acties.yaml` en `apps/api/src/hub/actions/service.py`; BESLUITEN, koppen "BG-05" en "BLOK-08"
- **Bouw:**
  1. Stel eerst de actienaam vast. De naam voor "noodstop aan in MediaGuard" is ONBEKEND - eerst vaststellen met: `grep -n -i 'noodstop' <DOCS>/PLATFORM_CONTRACTEN.md` en `grep -n '^  [a-z_.]*:' <WERKMAP>/ai-server-manager/policy/acties.yaml`. Op 2026-11-11 stond er in de tabel "Acties via de eigenaar-connector" van het contract en in `policy/acties.yaml` geen naam voor. Ontbreekt hij nog: zie "Stop en vraag als".
  2. Voeg de actie toe aan `policy/acties.yaml` in het bestaande patroon: alleen de richting AAN, met de risicoklasse en goedkeuringsregel die het contract of het besluit noemt. Er komt geen actie voor "noodstop uit" en geen van de gereserveerde `mediaguard.*`-acties.
  3. Uitvoering: via de bestaande stroom in `apps/api/src/hub/actions/service.py` (`stel_voor`, `keur_goed`, `voer_uit`). De Hub roept `POST /api/v1/system/emergency-stop` van MediaGuard aan met `active: true` en een reden, met een aparte sleutel die alleen de scope `emergency_stop:on` heeft. Die sleutel is een andere dan de viewer-sleutel van S-P3-030 en wordt op dezelfde manier ingevoerd en bewaard (S-P3-020).
  4. Voor en na: lees `GET /api/v1/status` voor de aanroep (toestand en tijdstip binden aan het voorstel) en erna (readback). Is de readback niet "actief", dan is de uitkomst mislukt, nooit geslaagd.
  5. Staat de noodstop al aan, dan doet de Hub niets en meldt dat (idempotent). De Hub zet de noodstop nooit uit en biedt daar geen knop of route voor; uitzetten doet de gebruiker in MediaGuard (link).
  6. Audit en journaal volgens het bestaande patroon (`_journaal` in `service.py`). De reden komt in de audit; de sleutel niet.
  7. Op het scherm Media (S-P3-080) een knop "Noodstop aan" die naar het bestaande goedkeuringspad leidt. Het goedkeuringsscherm zelf is van P2: ONBEKEND - eerst vaststellen met: `grep -rln -i 'goedkeur' <WERKMAP>/ai-server-manager/apps/web/src/app`. Bestaat het niet, dan alleen de API en de tests in deze stap en de knop melden als open punt.
- **Tests (verplicht):** unit- en integratietests tegen de nagebootste MediaGuard. Negatief: (a) een voorstel met `active: false` of een andere MediaGuard-actie wordt door de policy geweigerd; (b) een `risk_claim` in het voorstel verandert de klasse niet (EX18); (c) een goedkeuring waarvan een gebonden veld is gewijzigd vervalt (EX19) en een nonce werkt een keer (EX20); (d) MediaGuard antwoordt 403 (sleutel zonder scope): uitkomst mislukt met reden, geen herhaalpoging met de viewer-sleutel; (e) readback zegt "niet actief": uitkomst mislukt. Commando: `make lint && make test-unit`, daarna de integratietests (commando in de kop van deze baan), daarna `(cd apps/policy && ../../.venv/bin/python -m pytest -q tests/test_policy.py)`; klopt dat laatste pad niet, gebruik het commando uit POORTEN, P-ai-server-manager, kop "3. Snel".
- **Poort:** P-ai-server-manager (snel en volledig) + P-VEILIG + P-CONTRACT + P-HARDE-EIS + P-GIT + P-EERLIJK
- **Valkuilen:** V-001, V-018, V-043, V-055, V-094. Een Hub-vlag die de noodstop van MediaGuard "onthoudt" is verboden: de waarheid staat in MediaGuard.
- **Bewijs:** C1.3-ASM-19 "Bezig", "Sim-getest" (opmerking: alleen noodstop aan). B04-003 is een regel van `media-guard-ultimate`. Echte MediaGuard: "NIET GEVALIDEERD (echte NAS)", STAPPEN_P6.md stap S-P6-14 en onderdeel N-P6-05.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG + R-HARDE-EIS (tegelijk; R-VEILIG en R-HARDE-EIS VERPLICHT) -> A-HERSTEL -> R-EERLIJK. Met knop: A-ONTWERP voor A-BOUW en R-ONTWERP (VERPLICHT) na herstel.
- **Niveau:** A-BOUW N4, A-HERSTEL N4 (moeilijkheid hoog); verder standaard. Geen topmodel: dit is een afnemer van de policy, niet de kern.
- **Stop en vraag als:** de actienaam in contract en beleid ontbreekt (de regisseur legt een keuzemenu voor: een contractronde die de naam toevoegt, of deze stap uitstellen; een naam zelf verzinnen mag niet); BG-05 anders is beantwoord dan "niet" en de stap daardoor groter wordt; MediaGuard de scope niet afdwingt.

### S-P3-120 - Hub: een MSO-wijziging goedkeuren via de Hub
- **Repo:** ai-server-manager | **Fase:** P3 | **Omvang:** middel | **Moeilijkheid:** hoog | **Zwaar:** nee
- **Werkpakketten en tests:** Hub-deel van B05-009 en B05-005; C1.3-ASM-19; raakt C1.3-MSO-04, EX16, EX19, EX20
- **Vooraf:** Gate P2 afgevinkt; S-P3-240 gepusht (MSO kent `expected_preview_hash` en de scope `changes:approve`); S-P3-040 klaar
- **Al gedaan?** `grep -rn 'expected_preview_hash' <WERKMAP>/ai-server-manager/apps/api/src/hub | head -3` -> een aanroep met tests betekent klaar.
- **Lees eerst:** [CONTRACT], kop "8. Risicobeleid, voorstel, goedkeuring en executor" (tabel "Acties via de eigenaar-connector", regel over MSO change sets); [CONTRACT], kop "2.3 ..." regel 2 (MSO) en regel 3; [DM-MSO], koppen "B05-009 — Integratie met Hub (F4, P0, risico hoog)" en "11.5 Gecorrigeerde bouwlijst P3 (alleen wijzigingen t.o.v. §9)"; `<WERKMAP>/media-source-optimizer/docs/openapi/media-source-optimizer.openapi.json`; `apps/api/src/hub/actions/service.py`
- **Bouw:**
  1. Stel de actielijst vast. Het contract verwijst voor MSO naar "eigen lijst in hun `DELTA_MATRIX.md`". Die lijst is ONBEKEND - eerst vaststellen met: `grep -n -i 'action_id\|actielijst' <WERKMAP>/media-source-optimizer/docs/platform-v2/DELTA_MATRIX.md`. S-P3-240 legt hem vast; staat hij er niet, dan stopt deze stap.
  2. Voeg de acties toe aan `policy/acties.yaml` (klasse minimaal R1, goedkeuring per actie, zoals de contracttabel zegt). De klasse bepaalt de Hub; een klasse die MSO meestuurt is alleen ter informatie.
  3. Voorstel: de Hub leest de wijziging uit MSO (`GET /api/v1/changes?status=preview` en de wijziging zelf) en bindt `preview_hash` aan het voorstel en aan de goedkeuring.
  4. Uitvoering na menselijke goedkeuring in de Hub: `POST /api/v1/changes/{id}/approve` en daarna `/apply` in MSO, met `expected_preview_hash`, een `Idempotency-Key` en de machine-sleutel met scope `changes:approve`. Antwoord 409 `preview_changed`: de goedkeuring in de Hub vervalt en de gebruiker ziet dat de wijziging is veranderd.
  5. De Hub gebruikt nooit `force`, nooit een gebruikerswachtwoord van MSO en schrijft nooit rechtstreeks naar SABnzbd, qBittorrent of Prowlarr ([DM-MSO], kop "10. Wat in P3 nooit mag (samengevat)").
  6. Readback: lees de wijziging na `apply`; alleen de toestand `applied` telt als uitgevoerd. Terugdraaien blijft in MSO (link); de Hub toont de terugdraaimogelijkheid, voert hem in P3 niet uit.
  7. Audit en journaal volgens het bestaande patroon; `correlation_id` van MSO erin.
- **Tests (verplicht):** unit- en integratietests tegen de nagebootste MSO. Negatief: (a) `preview_hash` gewijzigd tussen voorstel en uitvoering geeft 409 en een vervallen goedkeuring (EX19); (b) dezelfde `Idempotency-Key` twee keer geeft een uitvoering en een auditregel (EX20); (c) sleutel met alleen scope `read` geeft mislukt met reden; (d) een voorstel van de AI zonder menselijke goedkeuring wordt niet uitgevoerd (EX16); (e) een poging met `force` wordt in de Hub geweigerd voor er een verzoek uitgaat. Commando: `make lint && make test-unit`, daarna de integratietests (commando in de kop van deze baan).
- **Poort:** P-ai-server-manager (snel en volledig) + P-VEILIG + P-CONTRACT + P-GIT + P-EERLIJK
- **Valkuilen:** V-001, V-017, V-043, V-055, V-094
- **Bewijs:** C1.3-ASM-19 "Bezig", "Sim-getest". B05-009 is een regel van `media-source-optimizer`. Echte MSO en echte downloaders: "NIET GEVALIDEERD (echte NAS)" en "NIET GEVALIDEERD (account)", STAPPEN_P6.md stappen S-P6-16 en S-P6-18.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG (tegelijk; R-VEILIG VERPLICHT) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4, A-HERSTEL N4; verder standaard
- **Stop en vraag als:** de actielijst van MSO ontbreekt; MSO voor `approve` een beheerdersrol eist die een machine-sleutel niet kan krijgen (dan beslist de gebruiker via een keuzemenu, niet de bouwer).

### S-P3-130 - Hub: bewaakt schrijfpad naar my_house (ondertekend verzoek)
- **Repo:** ai-server-manager | **Fase:** P3 | **Omvang:** middel | **Moeilijkheid:** hoog | **Zwaar:** nee
- **Werkpakketten en tests:** Hub-deel van B06-006 en B06-007; C1.3-ASM-19; raakt C1.3-MH-04, EX17, EX18, EX20, EX27, EX45
- **Vooraf:** Gate P2 afgevinkt; S-P3-742 gepusht; S-P3-050 klaar; S-P3-015 klaar (rotatie bij een geplakte sleutelset)
- **Al gedaan?** `grep -n 'light.group.set\|zone.command' <WERKMAP>/ai-server-manager/policy/acties.yaml` en `grep -rn 'connector/v1/apply' <WERKMAP>/ai-server-manager/apps/api/src/hub | head -3` -> acties in het beleid plus een aanroep met tests betekent klaar.
- **Lees eerst:** [CONTRACT], kop "8. Risicobeleid, voorstel, goedkeuring en executor"; [CONTRACT], kop "4.5 Sleutelpinning, vingerafdruk en rotatie"; [DM-MH], kop "11.6 Bijgestelde bouwlijst (vervangt de genoemde regels van §9)" regel P3-05; het ADR van S-P3-015; `policy/blokkades.yaml` (blok `boiler`) en `apps/api/src/hub/actions/blokkades.py`
- **Bouw:**
  1. Acties in `policy/acties.yaml`: `light.group.set`, `light.scene.recall`, `zone.command`, `zone.resume` en `zone.schedule.propose` (de laatste alleen als concept). Klassen volgens [DM-MH]: licht R1, klimaat R2. Neem het parameterschema over uit `discover` van my_house, niet uit eigen aannames.
  2. De Hub ondertekent het `ExecutionRequest` met de policy-sleutel (bestaande code in `apps/policy/src/asm_policy/execreq.py`) en stuurt het naar `POST /connector/v1/propose` en daarna `/apply` van my_house, met `Idempotency-Key`, vervaltijd en eenmalige nonce.
  3. Boiler: elke actie met een beschermd doel wordt al in de Hub geweigerd door het blok `boiler` in `policy/blokkades.yaml`, voor er iets ondertekend wordt. Voeg tests toe; verander het blok niet.
  4. Klimaat: `zone.command` en `zone.resume` blijven in de Hub geblokkeerd met een reden in gewone taal zolang de gate "my_house fysieke apparaten gevalideerd" niet is afgevinkt. Gebruik het bestaande mechanisme voor dynamische blokkades (`dynamisch` in `apps/api/src/hub/actions/blokkades.py`); verzin geen tweede.
  5. Readback en bewijs: lees na `apply` het bewijsrecord van my_house (`GET /connector/v1/evidence/{id}`) en leg voor en na vast in het journaal.
  6. my_house antwoordt `501 capability_unavailable` (geen gepinde sleutel): de Hub toont "plak eerst de Hub-sleutelset in my_house" met een verwijzing naar het scherm waar de sleutelset te kopieren is (`apps/web/src/app/instellingen/diensten/DienstenScreen.tsx`).
  7. Rotatie: de Hub weigert de policy-sleutel te roteren zolang my_house de oude set gepind heeft, volgens het ADR van S-P3-015.
- **Tests (verplicht):** unit- en integratietests tegen een nagebootste my_house-connector die de handtekening echt controleert. Negatief: (a) een voorstel voor de boiler (elk beschermd doel, ook met `actor.type=ai` en met goedkeuring) wordt geweigerd met `policy_denied` en er gaat geen verzoek uit (EX27); (b) een actie buiten de lijst wordt geweigerd (EX17, EX45); (c) `risk_claim` wordt genegeerd (EX18); (d) hetzelfde verzoek twee keer geeft een uitvoering (EX20); (e) `zone.command` zonder afgevinkte apparatengate wordt geweigerd; (f) rotatie met een gepinde oude set wordt geweigerd. Commando: `make lint && make test-unit`, daarna de integratietests (commando in de kop van deze baan).
- **Poort:** P-ai-server-manager (snel en volledig) + P-VEILIG + P-CONTRACT + P-GIT + P-EERLIJK
- **Valkuilen:** V-001, V-018, V-043, V-055. De nagebootste connector moet een ongeldige handtekening weigeren, anders bewijst de test niets (V-003).
- **Bewijs:** C1.3-ASM-19 "Bezig", "Sim-getest". B06-006 en B06-007 zijn regels van `my_house`. Echte lampen en airco: "NIET GEVALIDEERD (hardware)", STAPPEN_P6.md stap S-P6-21 en onderdeel N-P6-06.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG (tegelijk; R-VEILIG VERPLICHT) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4, A-HERSTEL N4; verder standaard. Geen topmodel: de kern van de ondertekening is in P2 beoordeeld; de kern van de verificatie in S-P3-740.
- **Stop en vraag als:** het parameterschema van my_house iets toelaat dat het beleid van de Hub niet kent; voor de klimaatblokkade een nieuw soort gate nodig is; het ondertekenen een wijziging in `apps/policy` vraagt.

### S-P3-150 - Hub: energie en kosten met herkomst (backend)
- **Repo:** ai-server-manager | **Fase:** P3 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** B01-011; Hub-deel van B14-001, B14-002 en B05-008; raakt EX28, EX30
- **Vooraf:** S-P3-040 klaar; S-P3-310 gepusht (of het ADR van S-P3-010 wijst de Hub-adapter aan als lezer)
- **Al gedaan?** STAND ai-server-manager B01-011 en `grep -rn -i 'measurement_quality\|meetdekking' <WERKMAP>/ai-server-manager/apps/api/src/hub | head -3` -> een regel B01-011 op "Bezig" plus een module met tests betekent klaar.
- **Lees eerst:** [B01], kop "F5 - Hardening & UX" (taak B01-011); [B14], koppen "3. API en integratie-contracten" en "5. Niet-regressie, randgevallen en verbodsbepalingen"; het ADR van S-P3-010 (bouwpunt 6: wie leest de energie); `<WERKMAP>/home-control-hub/apps/api/src/integrations/domains/energy/router.py`; [DM-MSO], kop "B05-008 — Kostenoptimalisatie (F4, P1)"
- **Bouw:**
  1. Een module voor energie en kosten onder `apps/api/src/hub/` (naam volgens het ADR; voorstel `kosten/`, nieuw) met een leesroute voor dag, week en maand.
  2. Bronnen: stroom uit de bron die het ADR aanwijst (energiedomein van `home-control-hub` of de my_house-adapter, nooit beide); kosten van externe diensten uit MSO (`GET /api/v1/costs/summary`); cloudbudget alleen als er al een bron in de Hub bestaat (ONBEKEND - eerst vaststellen met: `grep -rn -i 'budget' <WERKMAP>/ai-server-manager/apps/api/src/hub | head`). Ontbreekt een bron, dan is het cijfer "onbekend".
  3. Elk cijfer draagt `measurement_quality` met een van `measured`, `estimated`, `unknown`, plus de bron en het tijdvak. Een schatting noemt de aanname.
  4. Geen dubbeltelling: een kostenpost heeft precies een bron; komt dezelfde post uit twee bronnen, dan wint de bron die het ADR aanwijst en wordt de andere genegeerd met een logregel.
  5. Verboden afleidingen: geen wattage uit CPU-percentage zonder kalibratie; de gemeten airco-energie is van de gedeelde buitenunit en wordt nooit als verbruik van een binnenunit getoond; de energie van de NAS wordt niet per app verdeeld zonder meting.
  6. Budgetwaarschuwing: een grens die de gebruiker instelt; overschrijding geeft een melding via het bestaande meldingspad. Geen actie die iets schakelt.
  7. `make openapi`, daarna `make openapi-check`. Voeg in `docs/platform-v2/EVIDENCE.json` de regel B01-011 toe in dezelfde vorm als de andere B01-regels.
- **Tests (verplicht):** unit- en integratietests. Negatief: (a) geen meter: het antwoord bevat geen bedrag en geen besparing, alleen "onbekend"; (b) dezelfde post uit twee bronnen wordt een keer geteld; (c) een binnenunit krijgt geen eigen kWh; (d) een meting ouder dan `max_age` wordt "onbekend"; (e) een dag van 23 of 25 uur (zomertijd) telt goed op. Commando: `make lint && make test-unit`, daarna de integratietests (commando in de kop van deze baan), daarna `make openapi-check`.
- **Poort:** P-ai-server-manager + P-CONTRACT + P-GIT + P-EERLIJK
- **Valkuilen:** V-051, V-056, V-066; een nul tonen waar "onbekend" hoort is de fout die deze stap moet voorkomen
- **Bewijs:** B01-011 nieuw op "Bezig", "Sim-getest". Echte meters: "NIET GEVALIDEERD (hardware)" (D14), STAPPEN_P6.md stap S-P6-21 en onderdeel N-P6-06.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** het ADR van S-P3-010 geen eigenaar voor de energiecijfers noemt; een cijfer alleen te maken is met een afleiding uit bouwpunt 5.

### S-P3-160 - Hub-UI: scherm Kosten
- **Repo:** ai-server-manager | **Fase:** P3 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** B01-011; Hub-deel van B14-001 en B14-004
- **Vooraf:** S-P3-150 klaar
- **Al gedaan?** `grep -n 'kosten' <WERKMAP>/ai-server-manager/apps/web/src/lib/nav.ts` en `ls <WERKMAP>/ai-server-manager/apps/web/src/app/kosten` -> staat `kosten` nog in `PLANNED` (met fase "P5"), dan is de stap open.
- **Lees eerst:** [B01], kop "F5 - Hardening & UX" (taak B01-011: "Dag/week/maand grafiek; duidelijk bron en meetdekking; budgetwaarschuwing"); [B14], kop "1. Concrete schermen en gebruikersreizen"; [PEIL]; `apps/web/src/app/kosten/page.tsx`; POORTEN, kop "P-PEIL"
- **Bouw:**
  1. A-ONTWERP eerst: ontwerp in Peil met de toestanden leeg (geen meter), bezig, fout, verouderd en gevuld, op 360, 390, 768 en 1440 px.
  2. Grafiek per dag, week en maand. Een grafiekonderdeel in Peil is ONBEKEND - eerst vaststellen met: `grep -rn -i 'grafiek\|chart' <WERKMAP>/ai-server-manager/design/ontwerptaal | head`. Bestaat het niet, dan een tabel met balken uit bestaande Peil-onderdelen; een nieuw onderdeel vraagt een Peil-wijziging en hoort niet in deze stap.
  3. Elk cijfer met het label gemeten, geschat of onbekend, de bron en de meetdekking (welk deel van het tijdvak is gemeten).
  4. De airco staat er als een post "buitenunit (gedeeld)". Er is geen regel per binnenunit.
  5. Budgetwaarschuwing instellen en zien. Geen knop die een apparaat of een taak schakelt.
  6. De grafiek is ook als tabel te lezen (toetsenbord en schermlezer). `kosten` uit `PLANNED` in `apps/web/src/lib/nav.ts` halen.
- **Tests (verplicht):** componenttests en browsertest. Negatief: (a) geen meter: het scherm toont geen euroteken met een getal, alleen "onbekend" en waarom; (b) een geschat cijfer heeft zichtbaar het label geschat; (c) er staat geen regel per binnenunit; (d) verouderde gegevens zijn zichtbaar verouderd. Commando's: `make web-lint && make web-test`, `make web-e2e`, `make web-review`.
- **Poort:** P-ai-server-manager + P-PEIL + P-GIT + P-EERLIJK
- **Valkuilen:** V-051, V-058, V-061, V-063
- **Bewijs:** B01-011 "Bezig", "Sim-getest"
- **Agents:** A-VERKEN -> A-ONTWERP -> A-BOUW -> R-TECH -> A-HERSTEL -> R-ONTWERP (VERPLICHT) -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** Peil geen onderdeel heeft waarmee een tijdreeks toegankelijk te tonen is; de regisseur B01-011 in een andere fase wil houden (de plaatshouder noemt "P5"; zie hoofdstuk 8, opmerking bij B01-011).

### S-P3-170 - Hub: images, rooktest, OpenAPI en schermafdrukken van P3
- **Repo:** ai-server-manager | **Fase:** P3 | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** ja (image-build)
- **Werkpakketten en tests:** C1.3-ASM-21; B01-011; raakt C1.3-ALG-04 (de Hub-images blijven voldoen)
- **Vooraf:** alle eerdere stappen van deze baan klaar, behalve stappen die op een besluit of op Gate P2 wachten en die de regisseur uitdrukkelijk heeft uitgesteld
- **Al gedaan?** `ls <WERKMAP>/ai-server-manager/docs/screenshots/p3 2>/dev/null | head` en `git -C <WERKMAP>/ai-server-manager log --oneline -5` -> een map `p3` met schermafdrukken van na de laatste UI-commit betekent klaar.
- **Lees eerst:** POORTEN, kop "P-ai-server-manager", onderdeel "4. Volledig (CI-volgorde)" punten 8, 9 en 11; POORTEN, kop "P-PEIL"; `apps/web/review/README.md`; `docs/screenshots/p1` (vorm van de vorige ronde)
- **Bouw:**
  1. `make openapi` en `make openapi-check`: het OpenAPI-bestand klopt met alle nieuwe routes van P3.
  2. `flock <WERKMAP>/.lokaal/docker-build.lock nice -n 10 make images`, daarna `bash deploy/smoke.sh ai-server-manager:dev ai-server-manager-executor:dev`.
  3. `make web-e2e`, daarna `make web-review`. Los elke bevinding van de review op of leg hem met reden vast volgens `apps/web/review/README.md`.
  4. Schermafdrukken van de nieuwe schermen (koppelen, Media, Huis, Kosten) in `docs/screenshots/p3` (nieuw), in de vorm van `docs/screenshots/p1`. Alleen testgegevens.
  5. De twee manifesten valideren (commando's in POORTEN, punt 9). In deze stap wijzigt er niets aan de manifesten; wijkt de validatie af, meld het.
  6. `CHANGELOG.md` en `README.md`: wat P3 toevoegt, in gewone taal.
- **Tests (verplicht):** de commando's uit bouwpunt 1, 2 en 3. Negatief: de rooktest controleert de healthcheck als gebruiker 568 en faalt als de image als root blijft draaien; bevestig dat die controle in `deploy/smoke.sh` staat met `grep -n -i 'CapPrm\|568' deploy/smoke.sh`.
- **Poort:** P-ai-server-manager (volledig) + P-INSTALLATIE + P-PEIL + P-GIT + P-EERLIJK
- **Valkuilen:** V-011, V-013, V-063, V-066, V-088
- **Bewijs:** C1.3-ASM-21 en B01-011 "Bezig", "Sim-getest", met de verwijzing naar de CI-run. Installatie op de NAS: "NIET GEVALIDEERD (echte NAS)", STAPPEN_P6.md onderdeel N-P6-03.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-MANIFEST (tegelijk; R-MANIFEST VERPLICHT) -> A-HERSTEL -> R-ONTWERP (VERPLICHT, op de schermafdrukken) -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** `free -m` "available" onder 3000 MB blijft; de review een bevinding geeft die een Peil-wijziging vraagt.

### S-P3-180 - A-documenten: vastleggen wat het platform nu dekt (A09...A14, A17...A20)
- **Repo:** ai-server-manager | **Fase:** P3 | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** APP-09, APP-10, APP-11, APP-12, APP-13, APP-14, APP-17, APP-18, APP-19, APP-20 (alleen de documenten; geen statuswijziging)
- **Vooraf:** S-P3-170 klaar
- **Al gedaan?** `git -C <WERKMAP>/ai-server-manager log --oneline -3 -- docs/platform-v2/04_BESTAANDE_APPS` -> een commit van P3 die de tien documenten raakt betekent klaar.
- **Lees eerst:** `<DOCS>/04_BESTAANDE_APPS/APP_REGISTER.md`; `<DOCS>/04_BESTAANDE_APPS/A18_MEDIAGUARD.md`, `A19_MEDIA_SOURCE_OPTIMIZER.md` en `A20_MY_HOUSE.md`; [DM-MG], kop "E. Installatie- en app-stappen (I-/A-documenten)"; [DM-MSO] en [DM-MH], kop "3. Installatie- en bestaande-app-stappen (MSO-kant)" respectievelijk "3. Installatie- en bestaande-app-stappen (my_house-kant)"; [CONTRACT], kop "2.3 ..." regels 1 tot en met 9
- **Bouw:**
  1. A18, A19 en A20: voeg per document een korte alinea toe "Stand na P3 (simulator)": wat de Hub leest, via welke sleutel of koppelcode, wat de Hub mag doen (alleen wat S-P3-110, S-P3-120 en S-P3-130 hebben gebouwd) en wat handmatig in de app blijft. Elk met de tekst "NIET GEVALIDEERD (echte NAS)".
  2. A09 (Bazarr), A10 (Immich), A11 (Prowlarr), A12 (Seerr), A13 (SABnzbd), A14 (qBittorrent) en A17 (Jellyfin): controleer dat het document geen installatie- of beheerweg via een terminal of YAML beschrijft en dat de eigenaar klopt met [CONTRACT], kop "2.3 ...". Pas alleen aan wat aantoonbaar verouderd is; verzin geen nieuwe eisen.
  3. Prowlarr en SABnzbd: bevestig in A11 en A13 de regel "een eigenaar" (no-go van P3: niet wijzigen vanuit twee eigenaren).
  4. `APP_REGISTER.md` bijwerken als een document van naam of strekking verandert.
  5. Draai daarna de drifttests van de repos die een kopie van deze documenten houden; die repos worden bijgewerkt in S-P3-500 (appstore-en-fork). Meld welke andere repos een kopie hebben: `grep -rln 'A18_MEDIAGUARD' <WERKMAP>/*/docs/platform-v2 2>/dev/null`.
- **Tests (verplicht):** `make lint && make test-unit` (documenttests van de repo). Negatief, door R-EERLIJK: in geen van de tien documenten staat "Gereed", "Geslaagd" of een bewering over de echte NAS zonder "NIET GEVALIDEERD".
- **Poort:** P-ai-server-manager (snel) + P-EERLIJK + P-INSTALLATIE (leescontrole: geen terminalweg) + P-GIT
- **Valkuilen:** V-096, V-097, V-017
- **Bewijs:** geen statuswijziging. APP-09...APP-20 blijven "Geblokkeerd" (regels van `appstore-en-fork`): "NIET GEVALIDEERD (echte NAS)", STAPPEN_P6.md onderdeel N-P6-05.
- **Agents:** A-VERKEN -> A-BOUW -> R-EERLIJK. Korter omdat dit zuivere documentatie is; R-TECH vervalt.
- **Niveau:** standaard
- **Stop en vraag als:** een A-document een eis bevat die het contract tegenspreekt; een wijziging de Excel-titel van een taak zou veranderen.

## Baan media-source-optimizer (MSO: connector, machine-sleutel, image, manifest)

Werkmap `<WERKMAP>/media-source-optimizer`. Poort: P-media-source-optimizer. De tests van de kern vragen PostgreSQL 16
en lopen een testbestand tegelijk. Nieuwe migratie: het volgende vrije nummer in `apps/core/mso/migrations/`
(vaststellen met `ls apps/core/mso/migrations | tail -3`; op 2026-11-11 was `0607_footprint.sql` de laatste; de
MSO-bouwlijst noemt `0608` en `0609` als voorstel, het echte nummer hangt af van de volgorde van uitvoering). Nieuw
ADR: volgend vrij nummer (`ls docs/adr | tail -3`; op 2026-11-11 was ADR-0009 de laatste). Na een bewuste wijziging
van de API wordt `docs/openapi/media-source-optimizer.openapi.json` bijgewerkt met het commando dat in de stap staat
en meegecommit. Het getal `E2E_MIN_TESTS` in `Makefile` wordt nooit verlaagd. Deze repo maakt zelf geen tag en wijzigt
`release/VERSION` niet (een wijziging van dat bestand start `release.yaml`).

### S-P3-200 - MSO: opruimen en CI op de werkbranch
- **Repo:** media-source-optimizer | **Fase:** P3 | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** B05-001 (deel: CI-bewijs op de werkbranch); MSO-bouwlijst P3-14 en het CI-deel van P3-04
- **Vooraf:** S-P3-000 klaar; besluit Z-10 genomen of de regel "zonder besluit geldt" toegepast
- **Al gedaan?** `git -C <WERKMAP>/media-source-optimizer ls-files apps/core/mso_core.egg-info | head -1` en `grep -n -A3 '^  push:' <WERKMAP>/media-source-optimizer/.github/workflows/ci.yaml` -> geen uitvoer bij het eerste commando en (bij Z-10 optie 1) `ccr-` in de lijst met branches betekent klaar.
- **Lees eerst:** BESLUITEN, kop "Z-10 — media-source-optimizer: CI op de werkbranch"; [DM-MSO], kop "9. Geprioriteerde bouwlijst fase P3 (alleen hiaten)" regels P3-04 en P3-14; `.github/workflows/ci.yaml` (blok `on:`); `docs/adr/ADR-0005-eerlijke-ci-e2e-en-logcontrole.md`, kop "Besluiten"; POORTEN, kop "P-media-source-optimizer", onderdeel "6. CI-controle"
- **Bouw:**
  1. Z-10 optie 1 (CI ook bij een push op de werkbranch): voeg in `.github/workflows/ci.yaml` onder `on: push: branches:` het patroon voor de werkbranch toe (de MSO-bouwlijst noemt `ccr-*`). Verander niets aan `tags`, aan `workflow_dispatch` of aan de invoer `release_version`.
  2. Z-10 zonder besluit of optie 3: wijzig de workflow niet. Elke stap in deze baan start de CI dan met de hand: `gh workflow run ci.yaml --ref ccr-c133d7a0-kuz1cv` en leest de uitkomst met `gh run list --workflow ci.yaml --branch ccr-c133d7a0-kuz1cv --limit 3`. Geef nooit de invoer `release_version` mee.
  3. Haal de gevolgde map `apps/core/mso_core.egg-info` uit git (`git rm -r --cached apps/core/mso_core.egg-info`) en zet `*.egg-info/` in `.gitignore`.
  4. Controleer of `apps/core/pyproject.toml` nog naar een niet-bestaand `THIRD_PARTY.md` verwijst: `grep -n 'THIRD_PARTY' apps/core/pyproject.toml`. Geen treffer betekent dat dit deel al is hersteld (zie `CHANGELOG.md`); wel een treffer: laat de verwijzing wijzen naar een bestaand bestand of haal hem weg.
  5. Leg in `README.md` (ontwikkeldeel) vast hoe de CI op de werkbranch start, in een regel.
- **Tests (verplicht):** `make lint` en `actionlint .github/workflows/ci.yaml .github/workflows/release.yaml`. Negatief: (a) `git ls-files | grep -c 'egg-info'` geeft 0; (b) `grep -n -A3 '^on:' .github/workflows/release.yaml` laat zien dat `release.yaml` alleen start bij een wijziging van `release/VERSION` of met de hand, dus niet door deze push; (c) na de push staat er precies een nieuwe run van `ci.yaml` op deze commit en geen run van `release.yaml`.
- **Poort:** P-media-source-optimizer (snel) + P-GIT + P-EERLIJK
- **Valkuilen:** V-004, V-022; een run starten met `release_version` publiceert images en is verboden
- **Bewijs:** B05-001 blijft "Bezig"; voeg de CI-run op de werkbranch toe aan het bewijs
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N2 (kleine mechanische stap); verder standaard
- **Stop en vraag als:** Z-10 met optie 2 is beantwoord (een branch `main` als standaardbranch: dat hangt samen met Z-06 en is geen werk voor deze stap); de CI na de push niet start en ook met de hand niet te starten is.

### S-P3-205 - MSO: weiger een database van een nieuwere versie
- **Repo:** media-source-optimizer | **Fase:** P3 | **Omvang:** klein | **Moeilijkheid:** hoog | **Zwaar:** nee
- **Werkpakketten en tests:** B05-001, B05-010; EX15; MSO-bouwlijst P3-01
- **Vooraf:** S-P3-200 klaar
- **Al gedaan?** `grep -n -i 'nieuwere MSO-versie\|newer' <WERKMAP>/media-source-optimizer/apps/core/mso/db.py <WERKMAP>/media-source-optimizer/apps/core/mso/__main__.py` -> een weigering in `migrate_up` plus een test betekent klaar.
- **Lees eerst:** [DM-MSO], kop "9. Geprioriteerde bouwlijst fase P3 (alleen hiaten)" regel P3-01 en kop "B05-010 — Back-up en migratie (F5, P0, risico hoog)"; `apps/core/mso/db.py` (functies `load_migrations`, `applied_migrations`, `migrate_up`, `schema_version`); `apps/core/mso/__main__.py`; `apps/core/tests/test_foundation.py` (test `test_migrations_down_and_up`); `apps/core/tests/test_maintenance.py` (test `test_restore_of_a_newer_dump_is_refused`)
- **Bouw:**
  1. In `migrate_up` in `apps/core/mso/db.py`: is de hoogste toegepaste migratie in de database hoger dan de hoogste migratie die deze code kent, dan wordt er niets gemigreerd en volgt een eigen fout met de Nederlandse melding uit de bouwlijst: "database is van een nieuwere MSO-versie; zet de bijpassende snapshot/back-up terug".
  2. Dezelfde controle in de opdrachtregel-ingang `apps/core/mso/__main__.py`, met een eigen exitcode die de bewaker van het alles-in-een image (`deploy/allinone/supervisor.py`) als duidelijke regel in het containerlog zet.
  3. Er wordt bij een weigering niets geschreven: geen rij in de migratietabel, geen wijziging van gegevens, geen automatische terugzetting.
  4. De controle vergelijkt nummers, niet een letterlijke versietekst (V-086).
  5. Documenteer het gedrag in `docs/OPERATIONS.md` in een alinea: wat de gebruiker ziet en dat de oplossing de bijpassende image of de snapshot van voor de update is. Geen terminalstappen.
- **Tests (verplicht):** nieuwe tests in `apps/core/tests/test_foundation.py`. Negatief: (a) database met een migratienummer hoger dan bekend: `migrate_up` geeft de fout en de inhoud van de migratietabel is daarna byte-gelijk aan ervoor; (b) een database op het huidige schema migreert niet en start gewoon; (c) een database op een ouder schema migreert omhoog zoals nu. Commando: `cd apps/core && PATH=/usr/lib/postgresql/16/bin:$PATH MSO_PG_BIN=/usr/lib/postgresql/16/bin MSO_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:5432/postgres ../../.venv/bin/python -m pytest -q -p no:warnings -rs tests/test_foundation.py tests/test_maintenance.py`, daarna `make lint`.
- **Poort:** P-media-source-optimizer (snel; de alles-in-een-proef volgt in S-P3-260) + P-HARDE-EIS (bestaande gegevens blijven onaangeroerd) + P-GIT + P-EERLIJK
- **Valkuilen:** V-070, V-086, V-003
- **Bewijs:** B05-001 en B05-010 blijven "Bezig", "Unit-getest" voor dit onderdeel; EX15 is een regel van het programma en blijft "Geblokkeerd": "NIET GEVALIDEERD (echte NAS)", STAPPEN_P6.md stap S-P6-20.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-HARDE-EIS (tegelijk; R-HARDE-EIS VERPLICHT) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4, A-HERSTEL N4 (moeilijkheid hoog: migratiecode); verder standaard. Geen topmodel: de database van MSO bevat geen kijkgeschiedenis en geen MediaGuard-voortgang.
- **Stop en vraag als:** de weigering alleen te bouwen is door de migratietabel van vorm te veranderen; het herstelpad (`apps/core/mso/backups.py`) door de controle anders gaat werken.

### S-P3-210 - MSO: build-gegevens op de Systeem-kaart
- **Repo:** media-source-optimizer | **Fase:** P3 | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** ja (stackproef voor de browsertest)
- **Werkpakketten en tests:** I04-04-01 (bouwdeel: versie en herkomst zichtbaar); B05-001; MSO-bouwlijst P3-02
- **Vooraf:** S-P3-200 klaar
- **Al gedaan?** `grep -n 'git_sha\|build_time' <WERKMAP>/media-source-optimizer/apps/core/mso/config.py <WERKMAP>/media-source-optimizer/apps/core/mso/api/foundation.py | head` -> velden in de configuratie en in `/api/v1/system/info` betekent klaar.
- **Lees eerst:** [DM-MSO], kop "9. Geprioriteerde bouwlijst fase P3 (alleen hiaten)" regel P3-02; `apps/core/mso/config.py`; `apps/core/mso/api/foundation.py` (route voor `/system/info`); `apps/web/app/(app)/systeem/page.tsx`; `deploy/allinone/Dockerfile`
- **Bouw:**
  1. A-ONTWERP eerst: de bestaande Systeem-kaart krijgt vier regels (versie, commit, bouwtijd, kanaal). Geen nieuw scherm.
  2. Build-argumenten in `deploy/allinone/Dockerfile` en in de Dockerfiles van kern en web voor `version`, `git_sha`, `build_time` en `channel`; doorgeven in `scripts/build-images.sh` en in `.github/workflows/release.yaml` en `ci.yaml`.
  3. `apps/core/mso/config.py` leest de vier waarden; ontbreekt er een, dan is de waarde "onbekend" (geen verzonnen waarde).
  4. `GET /api/v1/system/info` geeft de vier velden; werk de OpenAPI-export bij.
  5. `apps/web/app/(app)/systeem/page.tsx`: toon de vier regels op de bestaande kaart; "onbekend" in de onbekend-vorm van Peil.
- **Tests (verplicht):** kerntest plus browsertest. Negatief: zonder build-argumenten toont de kaart "onbekend" en geen lege regel. Commando's: `cd apps/core && PATH=/usr/lib/postgresql/16/bin:$PATH MSO_PG_BIN=/usr/lib/postgresql/16/bin MSO_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:5432/postgres MSO_OPENAPI_BIJWERKEN=1 ../../.venv/bin/python -m pytest -q -p no:warnings -rs tests/test_openapi_export.py tests/test_foundation.py`; `cd apps/web && npm run check:peil && npm run typecheck && npm run lint && npm run test:unit`; daarna de browsertest: `flock <WERKMAP>/.lokaal/stack.lock env MSO_STACK_NO_BUILD=1 nice -n 10 make e2e` en `make down` (de images eerst bouwen volgens POORTEN, P-media-source-optimizer, kop "4. Volledig (CI-volgorde)").
- **Poort:** P-media-source-optimizer + P-PEIL + P-GIT + P-EERLIJK
- **Valkuilen:** V-058, V-061, V-066, V-011
- **Bewijs:** B05-001 blijft "Bezig", "Sim-getest". I04-04-01 is een regel van `jelly-leon-platform` (S-P3-410).
- **Agents:** A-VERKEN -> A-ONTWERP -> A-BOUW -> R-TECH -> A-HERSTEL -> R-ONTWERP (VERPLICHT) -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** de build-argumenten een wijziging vragen die `release.yaml` anders laat publiceren; `free -m` "available" onder 3000 MB blijft.

### S-P3-215 - MSO: terugkeerpad na inloggen volgens het contract
- **Repo:** media-source-optimizer | **Fase:** P3 | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** C1.3-MSO-05
- **Vooraf:** S-P3-200 klaar
- **Al gedaan?** STAND media-source-optimizer C1.3-MSO-05 en `grep -n '256\|://' "<WERKMAP>/media-source-optimizer/apps/web/app/login/page.tsx"` -> status "Bezig" met een test en een lengtegrens in `safeNext` betekent klaar.
- **Lees eerst:** [CONTRACT], kop "4.1 Gebruikers, noodlogin (break-glass) en SSO" (zoek op "terugkeerpad"); [CONF], kop "7. media-source-optimizer (MSO, bestaande app; P3)" punt C1.3-MSO-05; `apps/web/app/login/page.tsx` (functie `safeNext`); `apps/web/tests/unit/hub.test.ts` (vorm van een bestaande test)
- **Bouw:**
  1. Verplaats `safeNext` naar een eigen bestand onder `apps/web/lib/` (nieuw; naam vrij) zodat hij los te testen is, en gebruik hem in `apps/web/app/login/page.tsx`.
  2. De regel uit het contract, letterlijk: alleen een pad dat voldoet aan `^/(?![/\\])[!-~]*$`, hooguit 256 tekens, zonder `://` en zonder backslash; anders `/`. Nooit een volledige URL.
  3. Behoud de bestaande extra regel dat een pad naar `/login` niet wordt gevolgd.
  4. Controleer of er meer plekken zijn die na het inloggen doorsturen: `grep -rn 'router.replace\|router.push\|location.href' apps/web/app/login apps/web/app/setup`. Elke plek gebruikt dezelfde functie.
- **Tests (verplicht):** nieuw testbestand onder `apps/web/tests/unit/`. Negatief, elk geval geeft `/`: `//evil.example`, `/\evil`, `https://evil.example`, `/a://b`, een pad met een spatie, een pad met een teken buiten `!` tot `~`, een pad van 257 tekens, een lege waarde. Positief: `/kosten?x=1` blijft staan; een pad van precies 256 tekens blijft staan. Commando: `cd apps/web && npm run typecheck && npm run lint && npm run test:unit`.
- **Poort:** P-media-source-optimizer (web) + P-VEILIG + P-CONTRACT + P-GIT + P-EERLIJK
- **Valkuilen:** V-064, V-003
- **Bewijs:** C1.3-MSO-05 naar "Bezig", "Unit-getest"
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG (tegelijk; R-VEILIG VERPLICHT) -> A-HERSTEL -> R-EERLIJK. Geen A-ONTWERP: het scherm verandert niet.
- **Niveau:** A-BOUW N2 (kleine mechanische stap); verder standaard
- **Stop en vraag als:** de kern zelf ook een terugkeerpad verwerkt (dan moet dezelfde regel daar komen en wordt de stap groter).

### S-P3-220 - MSO: machine-sleutel met scopes
- **Repo:** media-source-optimizer | **Fase:** P3 | **Omvang:** middel | **Moeilijkheid:** hoog | **Zwaar:** nee
- **Werkpakketten en tests:** B05-009; EX16; C1.3-MSO-04 (voorwaarde); MSO-bouwlijst P3-06 (gecorrigeerd)
- **Vooraf:** S-P3-200 klaar
- **Al gedaan?** `grep -n 'machine=True\|machine = True' <WERKMAP>/media-source-optimizer/apps/core/mso/auth.py` en `ls <WERKMAP>/media-source-optimizer/apps/core/mso/migrations | tail -3` -> `Principal.machine` wordt ergens gezet en er is een migratie voor machine-sleutels: klaar.
- **Lees eerst:** [CONTRACT], kop "2.3 Bestaande apps (MediaGuard, MSO, my_house, Jellyfin/Jelly Leon, Emby)" regel 2 (MSO) en regel 3; [DM-MSO], kop "11.5 Gecorrigeerde bouwlijst P3 (alleen wijzigingen t.o.v. §9)" regel P3-06 en kop "12. Contract 1.3 (conformiteitsronde 2026-11-10)"; `apps/core/mso/auth.py` (klasse `Principal`, veld `machine`; de bestaande begrenzing van inlogpogingen); `apps/core/mso/security.py`; `docs/adr/ADR-0009-contract-1-3-en-peil-1-1-1.md`
- **Bouw:**
  1. Er komt GEEN enrollment, geen Hub-JWT en geen JWKS in MSO: dat is vervallen (contract 1.3). Wat er wel komt is een machine-sleutel die de beheerder in MSO maakt en in de Hub-UI invoert.
  2. Migratie met het volgende vrije nummer: een tabel voor machine-sleutels met naam, een hash van de sleutel (nooit de sleutel zelf), scopes, aanmaakdatum, laatst gebruikt en ingetrokken. Met een werkende terugweg (`migrate_down`).
  3. `apps/core/mso/auth.py`: herken een machine-sleutel in een verzoekkop (naam van de kop: voorstel `X-Api-Key`, nieuw; leg de keuze vast in de OpenAPI-export en in `docs/USER_GUIDE.md`), vergelijk in constante tijd en zet `Principal.machine`. Een machine-sleutel krijgt nooit een rol; hij kan alleen wat zijn scopes noemen.
  4. Scopes: `read` (alleen de GET-routes die een ingelogde lezer ook mag) en, voor S-P3-240, `changes:approve`. Een onbekende scope wordt bij het aanmaken geweigerd. Een machine-sleutel kan nooit: gebruikers of sleutels beheren, de kluis lezen, instellingen wijzigen, een back-up terugzetten, of een route met `force` gebruiken.
  5. Routes voor de beheerder: sleutel maken (de waarde wordt een keer getoond), lijst (alleen naam, scopes, data en de laatste 4 tekens), intrekken. Elke handeling komt in het auditlog, zonder de sleutel.
  6. A-ONTWERP en daarna een sectie "Machine-sleutels" in het bestaande scherm Instellingen (`apps/web/app/(app)/instellingen/page.tsx`), met Peil-onderdelen en de toestanden leeg, bezig en fout.
  7. Mislukte pogingen met een machine-sleutel vallen onder dezelfde begrenzing als inlogpogingen. MSO blijft zonder Hub volledig werken.
  8. Werk de OpenAPI-export bij.
- **Tests (verplicht):** nieuw testbestand `apps/core/tests/test_machine_keys.py` (nieuw). Negatief: (a) sleutel zonder scope `read` op een GET-route geeft 403; (b) sleutel met alleen `read` op elke schrijvende route geeft 403 (de test loopt alle POST-, PUT-, PATCH- en DELETE-routes uit de OpenAPI-export af); (c) ingetrokken sleutel geeft 401; (d) een machine-sleutel kan geen sleutel maken en geen gebruiker wijzigen; (e) de sleutel staat niet in de database, het auditlog of de logregels van de test; (f) een onbekende scope wordt geweigerd; (g) de bestaande sessie-inlog werkt ongewijzigd. Commando: `cd apps/core && PATH=/usr/lib/postgresql/16/bin:$PATH MSO_PG_BIN=/usr/lib/postgresql/16/bin MSO_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:5432/postgres MSO_OPENAPI_BIJWERKEN=1 ../../.venv/bin/python -m pytest -q -p no:warnings -rs tests/test_machine_keys.py tests/test_openapi_export.py tests/test_foundation.py`, daarna `make lint` en `cd apps/web && npm run check:peil && npm run typecheck && npm run lint && npm run test:unit`.
- **Poort:** P-media-source-optimizer (snel en volledig) + P-VEILIG + P-CONTRACT + P-HARDE-EIS (migratie: bestaande gebruikers en sessies blijven werken) + P-PEIL + P-GIT + P-EERLIJK
- **Valkuilen:** V-043, V-055, V-094, V-046, V-066
- **Bewijs:** B05-009 naar "Bezig", "Unit-getest" (opmerking: machine-sleutel met scope `read`). Invoeren in de echte Hub: "NIET GEVALIDEERD (echte NAS)", STAPPEN_P6.md onderdeel N-P6-05.
- **Agents:** A-VERKEN -> A-ONTWERP -> A-BOUW -> R-TECH + R-VEILIG + R-HARDE-EIS (tegelijk; R-VEILIG en R-HARDE-EIS VERPLICHT) -> A-HERSTEL -> R-ONTWERP (VERPLICHT) -> R-EERLIJK
- **Niveau:** A-BOUW N4, A-HERSTEL N4; R-VEILIG N5 - Winst: dit is de kern van de authenticatie van MSO; een fout hier geeft elke latere afnemer (de Hub-adapter en het goedkeuren van wijzigingen) te veel rechten, en dat is met tests op afnemers niet meer te vinden. Verder standaard. Leg de inzet vast in `<WERKMAP>/.lokaal/plan/uit/VOORTGANG.md`, tabel "Topmodel-inzet".
- **Stop en vraag als:** een bestaande route alleen met een rol te beschermen is en niet met een scope; de MediaGuard-koppeling van MSO (`apps/core/mso/connectors/`) door de wijziging in `auth.py` anders gaat werken.

### S-P3-230 - MSO: connector, leesdeel
- **Repo:** media-source-optimizer | **Fase:** P3 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** B05-009; I04-04-08 (bouwdeel); C1.3-MSO-04; MSO-bouwlijst P3-07 (leesdeel)
- **Vooraf:** S-P3-220 klaar
- **Al gedaan?** `ls <WERKMAP>/media-source-optimizer/apps/core/mso/connector_api 2>/dev/null` en `grep -c '/connector/v1/' <WERKMAP>/media-source-optimizer/docs/openapi/media-source-optimizer.openapi.json` -> een map met tests en de leesroutes in de export betekent klaar.
- **Lees eerst:** [CONTRACT], kop "6. Connectorcontract (elke dienst én elke adapter voor bestaande apps)" en kop "6.2 Versheid (`observed_at` en `max_age`)"; [CONTRACT], kop "5. Gemeenschappelijke API-regels" (foutcatalogus); [DM-MSO], kop "9. Geprioriteerde bouwlijst fase P3 (alleen hiaten)" regel P3-07 en kop "12. Contract 1.3 (conformiteitsronde 2026-11-10)"; [CONF], kop "7. media-source-optimizer (MSO, bestaande app; P3)" punt C1.3-MSO-04; `apps/core/mso/audit.py`
- **Bouw:**
  1. Nieuwe map `apps/core/mso/connector_api/` (nieuw) met een router onder `/connector/v1`: `discover`, `health`, `items`, `events`, `evidence/{id}`. Plus `/readyz` naast het bestaande `/healthz`.
  2. Het foutformaat van het contract geldt alleen voor de routes onder `/connector/v1`. De bestaande routes onder `/api/v1` houden hun eigen formaat (`{detail, code, correlation_id}`); verander daar niets aan.
  3. `health`: de slechtste check bepaalt de toestand; elke check heeft `observed_at`; een meting ouder dan `max_age` is `unknown`. Een verouderde back-up telt mee als check.
  4. `items`: een `deep_link` per item naar het scherm in MSO. `events`: uit het auditlog en het automatiseringslog, met een oplopende cursor en stabiele ID's; een cursor die te oud is geeft de fout uit het contract, geen lege lijst.
  5. Toegang: alleen een machine-sleutel met scope `read` (S-P3-220) of een ingelogde lezer. Zonder sleutel: 401.
  6. `propose` geeft `501 capability_unavailable`. `apply` en `rollback` komen in S-P3-240; tot dan geven ze ook 501.
  7. Geen geheimen in `items`, `events` of `evidence`: gebruik de bestaande redactie; test op de exacte testsleutel.
  8. Werk de OpenAPI-export bij.
- **Tests (verplicht):** nieuw testbestand `apps/core/tests/test_connector_api.py` (nieuw). Negatief: (a) zonder sleutel 401, sleutel zonder `read` 403; (b) een check ouder dan `max_age` maakt `health` `unknown`, nooit gezond; (c) een verlopen cursor geeft de contractfout; (d) dezelfde gebeurtenis komt bij herhaald ophalen met hetzelfde ID terug; (e) `propose`, `apply` en `rollback` geven 501; (f) de waarde van een opgeslagen wachtwoord of sleutel komt in geen enkel antwoord voor. Commando: `cd apps/core && PATH=/usr/lib/postgresql/16/bin:$PATH MSO_PG_BIN=/usr/lib/postgresql/16/bin MSO_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:5432/postgres MSO_OPENAPI_BIJWERKEN=1 ../../.venv/bin/python -m pytest -q -p no:warnings -rs tests/test_connector_api.py tests/test_openapi_export.py`, daarna `make lint`.
- **Poort:** P-media-source-optimizer (snel en volledig) + P-CONTRACT + P-VEILIG + P-GIT + P-EERLIJK
- **Valkuilen:** V-001, V-046, V-051, V-052, V-066
- **Bewijs:** B05-009 blijft "Bezig", nu "Sim-getest" voor het leesdeel; C1.3-MSO-04 naar "Bezig", "Unit-getest". I04-04-08 is een regel van `jelly-leon-platform` (S-P3-410). Echte Hub tegen echte MSO: "NIET GEVALIDEERD (echte NAS)", STAPPEN_P6.md onderdeel N-P6-05.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG (tegelijk; R-VEILIG VERPLICHT) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** het contract een veld in `discover` of `health` eist dat MSO niet kan leveren zonder een bestaande route te veranderen; het auditlog geen stabiel ID per regel heeft.

### S-P3-240 - MSO: wijzigingen via de connector, gebonden aan preview_hash
- **Repo:** media-source-optimizer | **Fase:** P3 | **Omvang:** middel | **Moeilijkheid:** hoog | **Zwaar:** nee
- **Werkpakketten en tests:** B05-009, B05-005; EX19, EX20; C1.3-MSO-04; MSO-bouwlijst P3-07 (schrijfdeel) en P3-08
- **Vooraf:** S-P3-230 klaar
- **Al gedaan?** `grep -n 'expected_preview_hash\|preview_hash' <WERKMAP>/media-source-optimizer/apps/core/mso/changes.py | head -5` -> het veld in `changes.py` plus een paralleltest betekent klaar.
- **Lees eerst:** [DM-MSO], kop "9. Geprioriteerde bouwlijst fase P3 (alleen hiaten)" regels P3-07 en P3-08 en kop "10. Wat in P3 nooit mag (samengevat)"; [CONTRACT], kop "8. Risicobeleid, voorstel, goedkeuring en executor" (velden van `Approval`; tabel "Acties via de eigenaar-connector"); `apps/core/mso/changes.py`; `apps/core/tests/test_change_safety.py` (hulpmiddelen `_Holder` en `_hold_lock`); `apps/core/mso/migrations/0605_v160_change_safety.sql`
- **Bouw:**
  1. `preview_hash`: sha256 over de canonieke vorm van `target`, `risk` en `ops` van een wijziging. `impact` telt NIET mee (dat is een schatting die kan verschuiven). Opslaan in een kolom; migratie met het volgende vrije nummer, samen met de tabel `connector_idempotency`. Bestaande wijzigingen krijgen de hash bij de migratie of bij eerste lezing; kies een en test het.
  2. `POST /api/v1/changes/{id}/approve` en `/apply` accepteren `expected_preview_hash`. Wijkt hij af: 409 met code `preview_changed`, en er wordt niets uitgevoerd. Zonder het veld blijft het gedrag voor ingelogde gebruikers zoals nu.
  3. Een machine-sleutel met scope `changes:approve` mag `approve` en `apply` alleen MET `expected_preview_hash` en MET `Idempotency-Key`. De rol-eis van de bestaande routes voor mensen (`approve`: beheerder; `apply`: operator) verandert niet.
  4. `Idempotency-Key`: dezelfde sleutel met hetzelfde verzoek geeft hetzelfde antwoord terug zonder tweede uitvoering; dezelfde sleutel met een ander verzoek geeft de fout uit het contract. Een goedkeuring heeft een vervaltermijn; daarna 409.
  5. `/connector/v1/apply` en `/connector/v1/rollback` roepen het bestaande mechanisme voor wijzigingen aan. Er komt geen tweede mechanisme en `force` is via de connector niet mogelijk.
  6. Leg de actielijst voor de Hub vast in `docs/platform-v2/DELTA_MATRIX.md` (nieuwe paragraaf): per soort wijziging een `action_id`, wat hij raakt en of terugdraaien kan. Het contract verwijst naar deze lijst; op 2026-11-11 bestond hij niet. S-P3-120 leest hem.
  7. `discover` noemt de acties uit bouwpunt 6. Werk de OpenAPI-export bij.
- **Tests (verplicht):** uitbreiding van `apps/core/tests/test_change_safety.py` en `tests/test_connector_api.py`. Negatief: (a) twee HTTP-clients die tegelijk `apply` doen: precies een schrijfactie en een auditregel (echte race, met `_Holder` en `_hold_lock`); (b) herhaling na `applied` voert niets meer uit; (c) gewijzigde wijziging geeft 409 `preview_changed`; (d) verlopen goedkeuring geeft 409; (e) machine-sleutel zonder `expected_preview_hash` of zonder `Idempotency-Key` wordt geweigerd; (f) `force` via de connector wordt geweigerd; (g) sleutel met alleen `read` geeft 403. Commando: `cd apps/core && PATH=/usr/lib/postgresql/16/bin:$PATH MSO_PG_BIN=/usr/lib/postgresql/16/bin MSO_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:5432/postgres MSO_OPENAPI_BIJWERKEN=1 ../../.venv/bin/python -m pytest -q -p no:warnings -rs tests/test_change_safety.py tests/test_connector_api.py tests/test_openapi_export.py`, daarna `make lint`.
- **Poort:** P-media-source-optimizer (snel en volledig) + P-VEILIG + P-CONTRACT + P-HARDE-EIS (migratie: open wijzigingen blijven bruikbaar) + P-GIT + P-EERLIJK
- **Valkuilen:** V-003, V-043, V-055, V-066; een paralleltest die na elkaar loopt bewijst niets
- **Bewijs:** B05-009 en C1.3-MSO-04 "Bezig", "Sim-getest". EX19 en EX20 blijven "Geblokkeerd" (programma): "NIET GEVALIDEERD (echte NAS)", STAPPEN_P6.md stap S-P6-18.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG + R-HARDE-EIS (tegelijk; R-VEILIG en R-HARDE-EIS VERPLICHT) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4, A-HERSTEL N4 (moeilijkheid hoog: gelijktijdigheid); verder standaard. Geen topmodel: dit is een afnemer van de sleutelkern uit S-P3-220.
- **Stop en vraag als:** een machine-sleutel volgens het contract niet mag goedkeuren wat nu een beheerder goedkeurt (dan beslist de gebruiker via een keuzemenu); de actielijst een wijziging van het contract vraagt.

### S-P3-250 - MSO: healthcheck die eerst naar 568 wisselt
- **Repo:** media-source-optimizer | **Fase:** P3 | **Omvang:** klein | **Moeilijkheid:** hoog | **Zwaar:** ja (image-build)
- **Werkpakketten en tests:** C1.3-MSO-03; C1.3-ALG-04 (deel MSO); B05-001
- **Vooraf:** S-P3-200 klaar
- **Al gedaan?** `grep -n 'NO_NEW_PRIVS\|setuid\|setgroups' <WERKMAP>/media-source-optimizer/deploy/allinone/healthcheck.py` -> een wissel naar 568 voor de eerste controle plus een scenario in `tests/stack/allinone_test.py` betekent klaar. Op 2026-11-11 had `healthcheck.py` alleen de functie `ok(url)` en geen wissel.
- **Lees eerst:** [CONTRACT], kop "2.2 Custom App-realiteit (gemeten in de bronnen, niet op een echte NAS)" (alinea's "Healthcheck en `docker exec`" en "Rooktest"); [CONF], kop "7. media-source-optimizer (MSO, bestaande app; P3)" punt C1.3-MSO-03; `deploy/allinone/healthcheck.py`; `deploy/allinone/supervisor.py` (functie `demote`); `tests/stack/allinone_test.py` (scenario 1 en 7)
- **Bouw:**
  1. `deploy/allinone/healthcheck.py`: als eerste handeling, voor elke controle: is het proces root, dan eerst de bounding set legen, daarna `setgroups([])`, `setgid(568)`, `setuid(568)` en `prctl(PR_SET_NO_NEW_PRIVS, 1)`; is het proces al 568, dan alleen no_new_privs. Mislukt de wissel: exit 1. Gebruik de waarden `MSO_UID` en `MSO_GID` zoals `supervisor.py` dat doet.
  2. Een controlevlag (naam vrij, bijvoorbeeld `--controle`) die na de wissel `Uid`, `CapEff`, `CapPrm` en `NoNewPrivs` van het eigen proces meldt en stopt. De rooktest gebruikt die vlag.
  3. `HEALTHCHECK` in `deploy/allinone/Dockerfile` blijft in exec-vorm (dat is hij al); geen `sh -c`.
  4. `deploy/allinone/supervisor.py`: bij een start als root legt de bewaker de bounding set leeg voordat hij naar 568 wisselt, zodat elk proces in de boom `CapBnd 0` heeft.
  5. PID 1: op 2026-11-11 stond in de Dockerfile `ENTRYPOINT ["/usr/local/bin/dumb-init", "--"]`. Het contract zegt dat een init die als root blijft draaien niet voldoet. Meet eerst (`docker exec <container> cat /proc/1/status`); blijft PID 1 root, dan wordt de bewaker zelf PID 1 (en ruimt zelf zombies op) of start de init pas na de wissel. Kies de kleinste ingreep en leg hem vast in `docs/test-evidence/allinone-report.md`.
  6. Breid `tests/stack/allinone_test.py` uit met een scenario: de container draait zonder `--security-opt no-new-privileges` en zonder `--cap-drop`; voor elk proces in de boom van PID 1 (ook PID 1) geldt `Uid 568`, `CapEff`, `CapPrm` en `CapAmb` nul, `NoNewPrivs 1` en bij een start als root `CapBnd` nul; de healthcheck met de controlevlag meldt hetzelfde. Bij `--user 568` mag `CapBnd` de standaardset zijn.
- **Tests (verplicht):** het nieuwe scenario plus alle bestaande. Negatief: (a) de healthcheck gestart als root in een container waar de wissel niet kan (bijvoorbeeld zonder de capability daarvoor) eindigt met exit 1 en niet met "gezond"; (b) het scenario faalt aantoonbaar als de wissel uit de healthcheck wordt gehaald (een keer proberen, uitkomst in het rapport, wijziging terugdraaien). Commando's: `flock <WERKMAP>/.lokaal/docker-build.lock env MSO_IMAGE_TAG=local nice -n 10 scripts/build-images.sh allinone`, daarna `TMPDIR=<map op schijf> flock <WERKMAP>/.lokaal/stack.lock .venv/bin/python <WERKMAP>/.lokaal/mso-aio-wrapper/run.py tests/stack/allinone_test.py media-source-optimizer:local` (alle scenario's geslaagd, geen overgeslagen).
- **Poort:** P-media-source-optimizer (volledig: image en alles-in-een-proef) + P-INSTALLATIE + P-VEILIG + P-GIT + P-EERLIJK
- **Valkuilen:** V-053, V-052, V-083, V-084, V-011, V-013, V-088
- **Bewijs:** C1.3-MSO-03 naar "Bezig", "Sim-getest"; werk `docs/test-evidence/allinone-report.md` bij met de nieuwe uitkomst. Op een echte NAS: "NIET GEVALIDEERD (echte NAS)", STAPPEN_P6.md onderdeel N-P6-05.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG + R-MANIFEST (tegelijk; R-VEILIG en R-MANIFEST VERPLICHT) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4, A-HERSTEL N4 (moeilijkheid hoog: rechten en procesboom); verder standaard
- **Stop en vraag als:** de wissel van PID 1 alleen kan door PostgreSQL anders te starten dan nu; een bestaand scenario (1 tot en met 10) na de wijziging faalt en niet binnen deze stap te herstellen is.

### S-P3-255 - MSO: vaste digests, SBOM en afhankelijkheidscontrole
- **Repo:** media-source-optimizer | **Fase:** P3 | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** ja (image-build)
- **Werkpakketten en tests:** B05-001; MSO-bouwlijst P3-04 (deel digests en SBOM)
- **Vooraf:** S-P3-250 klaar
- **Al gedaan?** `grep -n '_IMAGE=' <WERKMAP>/media-source-optimizer/deploy/allinone/Dockerfile` en `ls <WERKMAP>/media-source-optimizer/release` -> elke regel eindigt op `@sha256:...` en er is een `digests.json`: klaar. Op 2026-11-11 stonden er versies zonder digest en was `node:22-bookworm-slim` zwevend.
- **Lees eerst:** [DM-MSO], kop "9. Geprioriteerde bouwlijst fase P3 (alleen hiaten)" regel P3-04 en kop "8. Releasegate v1.6.0 — wat ontbreekt voor een echte release (zonder zelf te taggen of te publiceren)"; `deploy/allinone/Dockerfile` (regels `ARG PYTHON_IMAGE`, `ARG POSTGRES_IMAGE`, `ARG NODE_IMAGE`); `.github/workflows/release.yaml`; BESLUITEN, kop "BLOK-06" (zoek op "BLOK-06")
- **Bouw:**
  1. Zet elke basis-image in `deploy/allinone/Dockerfile` en in de Dockerfiles van `apps/core`, `apps/web` en `apps/mocks` op een exacte versie plus `@sha256:<digest>`. De digest komt uit het register (`docker buildx imagetools inspect <image>:<tag>`), nooit uit het hoofd. `node` krijgt een exacte versie.
  2. Een controle in `ci.yaml` (job `python` of een eigen stap) die faalt als een `FROM` of een `ARG ..._IMAGE` zonder `@sha256:` in een Dockerfile staat.
  3. `release.yaml`: schrijf na het bouwen `release/digests.json` (nieuw) met per image de digest, maak een SBOM en draai `pip-audit`. De workflow publiceert alleen wat hij nu al publiceert; deze stap start hem niet.
  4. Geen tag, geen wijziging van `release/VERSION`.
- **Tests (verplicht):** Negatief: de controle uit bouwpunt 2 faalt op een Dockerfile met een regel zonder digest (unittest op het controlescript met een proefbestand). Commando's: `actionlint .github/workflows/ci.yaml .github/workflows/release.yaml`; `make lint`; `flock <WERKMAP>/.lokaal/docker-build.lock env MSO_IMAGE_TAG=local nice -n 10 scripts/build-images.sh allinone`; daarna de alles-in-een-proef zoals in S-P3-250 (alle scenario's geslaagd).
- **Poort:** P-media-source-optimizer (volledig) + P-INSTALLATIE + P-GIT + P-EERLIJK
- **Valkuilen:** V-011, V-088, V-004; een digest overtypen in plaats van opvragen
- **Bewijs:** B05-001 blijft "Bezig". Er is geen release, dus geen digest van de eigen image: BLOK-06 blijft staan; het manifest gebruikt tot de eerste release `digest_pending_release` (S-P3-290).
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-MANIFEST (tegelijk; R-MANIFEST VERPLICHT) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N2 (kleine mechanische stap); verder standaard
- **Stop en vraag als:** een basis-image met de vaste digest niet meer bouwt; de SBOM-stap een nieuw geheim of een nieuwe dienst vraagt.

### S-P3-260 - MSO: upgradetest vanaf de vorige image
- **Repo:** media-source-optimizer | **Fase:** P3 | **Omvang:** middel | **Moeilijkheid:** hoog | **Zwaar:** ja (image-build, stackproef)
- **Werkpakketten en tests:** B05-001, B05-010; I04-04-07 (bouwdeel); EX15; MSO-bouwlijst P3-03
- **Vooraf:** S-P3-205 en S-P3-255 klaar
- **Al gedaan?** `sed -n 1,25p <WERKMAP>/media-source-optimizer/tests/stack/allinone_test.py` -> scenario's 11 en 12 (of hoger) over een upgrade vanaf de vorige image en een geweigerde terugweg betekent klaar. Op 2026-11-11 eindigde de lijst bij scenario 10.
- **Lees eerst:** [DM-MSO], kop "9. Geprioriteerde bouwlijst fase P3 (alleen hiaten)" regel P3-03 (daar staat de digest van de 1.5.0-image); `tests/stack/allinone_test.py` (scenario 3 en 10); `apps/core/mso/backups.py`; `docs/MIGRATION.md`; [I-04], kop van stap 7 (zoek op "I04-04-07")
- **Bouw:**
  1. Nieuw scenario in `tests/stack/allinone_test.py`: start de 1.5.0-image (op de digest uit de bouwlijst, niet op een tag) op een lege map, maak gegevens (gebruiker, een koppeling, een wijziging), stop hem en start de nieuwe image op dezelfde map. Verwacht: er wordt eerst een `pre-upgrade`-back-up gemaakt, alle migraties lopen, de gegevens en de inlog zijn intact.
  2. Nieuw scenario: herstel van die `pre-upgrade`-back-up in een wegwerpcontainer met de oude image; de gegevens zijn terug.
  3. Nieuw scenario (negatief): de oude image starten op de map die al gemigreerd is (alleen de tag terugzetten) wordt geweigerd met de melding uit S-P3-205, en de map is daarna ongewijzigd.
  4. Is de 1.5.0-image niet op te halen, dan worden de scenario's overgeslagen met een luide melding en telt de stap als niet klaar (V-004); verzin geen vervanger.
  5. Neem de scenario's op in de job `allinone` van `ci.yaml`.
  6. Schrijf in `docs/MIGRATION.md` wat de gebruiker ziet bij een update en hoe hij teruggaat: de snapshot van voor de update terugzetten in de TrueNAS-webinterface en de vorige image-versie in het formulier kiezen. Geen terminalstappen als hoofdroute.
- **Tests (verplicht):** de drie nieuwe scenario's plus alle bestaande; het derde is de negatieve test. Commando's: `flock <WERKMAP>/.lokaal/docker-build.lock env MSO_IMAGE_TAG=local nice -n 10 scripts/build-images.sh allinone`, daarna `TMPDIR=<map op schijf> flock <WERKMAP>/.lokaal/stack.lock .venv/bin/python <WERKMAP>/.lokaal/mso-aio-wrapper/run.py tests/stack/allinone_test.py media-source-optimizer:local`.
- **Poort:** P-media-source-optimizer (volledig) + P-HARDE-EIS (niets verloren bij upgrade; terugweg bewezen) + P-INSTALLATIE + P-GIT + P-EERLIJK
- **Valkuilen:** V-070, V-004, V-013, V-088, V-011
- **Bewijs:** B05-010 en B05-001 blijven "Bezig", "Sim-getest"; werk `docs/test-evidence/allinone-report.md` bij. I04-04-07 is een regel van `jelly-leon-platform` (S-P3-410). EX15: "NIET GEVALIDEERD (echte NAS)", STAPPEN_P6.md stap S-P6-20.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-HARDE-EIS (tegelijk; R-HARDE-EIS VERPLICHT) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4, A-HERSTEL N4; verder standaard. Geen topmodel: dit is een proef, geen migratiecode, en de database van MSO bevat geen kijkgeschiedenis of MediaGuard-voortgang.
- **Stop en vraag als:** de upgrade vanaf 1.5.0 gegevens verliest (dan is dat een fout in een bestaande migratie: stoppen en melden, niet de test aanpassen); de oude image alleen te halen is met een inlog op het register.

### S-P3-265 - MSO: contracttest tegen de echte MediaGuard-image
- **Repo:** media-source-optimizer | **Fase:** P3 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (stackproef)
- **Werkpakketten en tests:** B05-006; I04-04-03 (bouwdeel); MSO-bouwlijst P3-09
- **Vooraf:** S-P3-200 klaar
- **Al gedaan?** `ls <WERKMAP>/media-source-optimizer/tests/stack/mediaguard_contract.py 2>/dev/null` en `grep -n 'mediaguard_contract' <WERKMAP>/media-source-optimizer/.github/workflows/ci.yaml` -> het bestand en een CI-job betekent klaar.
- **Lees eerst:** [DM-MSO], kop "9. Geprioriteerde bouwlijst fase P3 (alleen hiaten)" regel P3-09; `apps/core/tests/test_mediaguard_integration.py`; `apps/core/tests/mg_support.py`; `docs/MEDIAGUARD_API_KEYS.md`; [DM-MG], kop "D. Hub-adapter: bestaande routes vs connectorcontract (§6) en enrollment (§3)"
- **Bouw:**
  1. Nieuw `tests/stack/mediaguard_contract.py`: start de echte MediaGuard-core-image (versie en digest uit de bouwlijst, regel P3-09) met een nep-arr uit `tests/stack/gen_mocks.py`, maak in MediaGuard een sleutel zoals `docs/MEDIAGUARD_API_KEYS.md` beschrijft en laat MSO de routes aanroepen die het in het echt gebruikt.
  2. Controleer per route: statuscode, de velden die MSO leest, en dat MSO alleen leest wat het mag (de lijst `ALLOWED_WRITES` wordt niet groter).
  3. De test meldt welke MediaGuard-versie is getest. Is de image niet op te halen (de GHCR-pakketten zijn nog niet aan de nieuwe repo gekoppeld, T-01), dan wordt de test overgeslagen met een luide melding en is de stap niet klaar.
  4. Een eigen CI-job in `ci.yaml` die de test draait, met dezelfde regel voor overslaan.
  5. De test schrijft niets in een echte MediaGuard: alleen in de wegwerpcontainer, met een lege database.
- **Tests (verplicht):** de contracttest zelf. Negatief: (a) een sleutel met een te lage rol geeft de weigering die MSO verwacht en MSO toont de Nederlandse melding; (b) MediaGuard onbereikbaar: MSO meldt "onbereikbaar", geen lege lijst. Commando: `flock <WERKMAP>/.lokaal/stack.lock nice -n 10 .venv/bin/python tests/stack/mediaguard_contract.py` (exact commando vastleggen in `README.md` zodra het bestand bestaat), daarna `make lint` en `actionlint .github/workflows/ci.yaml .github/workflows/release.yaml`.
- **Poort:** P-media-source-optimizer + P-HARDE-EIS (MediaGuard wordt alleen gelezen; de voortgangsdatabase van een echte installatie wordt nooit geraakt) + P-GIT + P-EERLIJK
- **Valkuilen:** V-001, V-004, V-088, V-013
- **Bewijs:** B05-006 blijft "Bezig", "Sim-getest" (opmerking: tegen welke MediaGuard-versie). I04-04-03 is een regel van `jelly-leon-platform` (S-P3-410). Tegen de MediaGuard op de NAS: "NIET GEVALIDEERD (echte NAS)", STAPPEN_P6.md onderdeel N-P6-05.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-HARDE-EIS (tegelijk; R-HARDE-EIS VERPLICHT) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard (R-HARDE-EIS N4)
- **Stop en vraag als:** de MediaGuard-image niet op te halen is (T-01 open): meld het en ga door met de volgende stap; de echte MediaGuard een route anders beantwoordt dan MSO verwacht (dat is een bevinding voor beide repos, geen reden om de test te versoepelen).

### S-P3-270 - MSO: opslag en groei met herkomst
- **Repo:** media-source-optimizer | **Fase:** P3 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (stackproef voor de browsertest)
- **Werkpakketten en tests:** B05-004; MSO-bouwlijst P3-10
- **Vooraf:** S-P3-210 klaar
- **Al gedaan?** `grep -rn 'resource_samples' <WERKMAP>/media-source-optimizer/apps/core/mso/migrations <WERKMAP>/media-source-optimizer/apps/core/mso/retention.py | head -3` -> een migratie en gebruik in `retention.py` betekent klaar.
- **Lees eerst:** [DM-MSO], kop "9. Geprioriteerde bouwlijst fase P3 (alleen hiaten)" regel P3-10 en kop "11.5 Gecorrigeerde bouwlijst P3 (alleen wijzigingen t.o.v. §9)" regel P3-10; `apps/core/mso/retention.py`; `apps/core/mso/migrations/0607_footprint.sql`; `apps/web/components/mso/system/maintenance-card.tsx`; `apps/core/tests/test_maintenance.py`
- **Bouw:**
  1. A-ONTWERP eerst: een sectie "Opslag en groei" op de bestaande Systeem-pagina; de toestanden leeg (nog geen metingen), bezig, storing en "te weinig metingen voor een trend".
  2. Migratie met het volgende vrije nummer: tabel `resource_samples` met een dagelijkse meting van databasegrootte, tabellen, back-ups, vrije ruimte in `/appdata` en databaseverbindingen. Met terugweg.
  3. Hergebruik wat er al is (bouwlijst 11.5): `usage()` van de header-index, schijfruimte uit `/system/health`, `backups.space_status()` en het opslagrapport van de torrentclient. Bouw geen tweede meting.
  4. `growth` en `provenance` in het antwoord van `/api/v1/system/maintenance`: groei per dag over de gemeten periode, en per getal of het gemeten of geschat is. Met minder dan twee metingen is de groei "onbekend", nooit 0.
  5. Leg voor elke groeiende tabel een bewaartermijn vast in het bestaande `retention.py`; er komt geen tweede opruimmechanisme en er wordt niets automatisch verwijderd dat nu ook niet verwijderd wordt.
  6. Toon de sectie in `apps/web/app/(app)/systeem/page.tsx`; werk de OpenAPI-export bij.
- **Tests (verplicht):** kerntest met 30 gesimuleerde dagen plus browsertest. Negatief: (a) een dag zonder meting geeft een gat, geen nul; (b) een meting kan in de tijd niet achteruit geschreven worden (de tijd komt van de database, V-056); (c) zonder metingen toont de sectie de lege toestand. Commando's: `cd apps/core && PATH=/usr/lib/postgresql/16/bin:$PATH MSO_PG_BIN=/usr/lib/postgresql/16/bin MSO_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:5432/postgres MSO_OPENAPI_BIJWERKEN=1 ../../.venv/bin/python -m pytest -q -p no:warnings -rs tests/test_maintenance.py tests/test_openapi_export.py`; `cd apps/web && npm run check:peil && npm run typecheck && npm run lint && npm run test:unit`; `flock <WERKMAP>/.lokaal/stack.lock env MSO_STACK_NO_BUILD=1 nice -n 10 make e2e` en `make down`.
- **Poort:** P-media-source-optimizer + P-PEIL + P-HARDE-EIS (migratie met terugweg) + P-GIT + P-EERLIJK
- **Valkuilen:** V-056, V-051, V-061, V-066, V-058
- **Bewijs:** B05-004 blijft "Bezig", "Sim-getest". Groei op de echte NAS over echte dagen: "NIET GEVALIDEERD (echte NAS)", STAPPEN_P6.md onderdeel N-P6-05.
- **Agents:** A-VERKEN -> A-ONTWERP -> A-BOUW -> R-TECH + R-HARDE-EIS (tegelijk; R-HARDE-EIS VERPLICHT) -> A-HERSTEL -> R-ONTWERP (VERPLICHT) -> R-EERLIJK
- **Niveau:** standaard (R-HARDE-EIS N4)
- **Stop en vraag als:** een bewaartermijn gegevens zou weggooien die nu bewaard blijven (dan beslist de gebruiker via een keuzemenu); de meting een recht vraagt dat de container nu niet heeft.

### S-P3-280 - MSO: Peil-ronde en schermbreedtes
- **Repo:** media-source-optimizer | **Fase:** P3 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (stackproef voor de browsertest)
- **Werkpakketten en tests:** B05-002, B05-003, B05-008 (schermdeel); C1.3-ALG-05 (deel MSO); MSO-bouwlijst P3-11
- **Vooraf:** S-P3-270 klaar
- **Al gedaan?** `grep -n 'width' <WERKMAP>/media-source-optimizer/apps/web/playwright.config.ts` -> projecten of specs voor 360 en 768 naast 390 en 1440 betekent dat het breedtedeel klaar is. Op 2026-11-11 waren er de projecten `desktop-1440` en `mobile-390`.
- **Lees eerst:** [DM-MSO], kop "9. Geprioriteerde bouwlijst fase P3 (alleen hiaten)" regel P3-11; `docs/adr/ADR-0009-contract-1-3-en-peil-1-1-1.md`, kop "Besluiten" (het punt over E11, E13 en E15); `docs/ontwerp/PEIL_REVIEW.md`; [PEIL]; `apps/web/e2e/screens.spec.ts`
- **Bouw:**
  1. A-ONTWERP eerst: loop de schermen van MSO na op 360, 390, 768 en 1440 breed en op de toestanden leeg, bezig, storing en offline. Lever een lijst van afwijkingen van Peil; alleen die worden gebouwd.
  2. Browsertests voor 360 en 768 in `apps/web/e2e/` (uitbreiding van `screens.spec.ts` of `peil.spec.ts`), en per scherm een test voor offline, storing en leeg.
  3. Herstel de afwijkingen uit bouwpunt 1 met Peil-onderdelen. Peil wordt nooit lokaal omzeild; een verbeterpunt uit de Peil-inventaris (E11, E13, E15) wordt alleen overgenomen via de Peil-versie die het bevat, na `python3 scripts/bronkopie.py controleer`. Wat ADR-0009 met reden niet overneemt, blijft zo.
  4. Het getal `E2E_MIN_TESTS` in `Makefile` gaat omhoog naar het nieuwe aantal tests, nooit omlaag.
  5. Nieuwe schermafdrukken in `docs/screenshots` met alleen fixture-gegevens.
- **Tests (verplicht):** Negatief: (a) op 360 breed is er op geen scherm horizontaal schuiven van de pagina; (b) de offline-toestand toont geen oude gegevens als actueel; (c) de strikte reporter (`apps/web/e2e/strict-reporter.ts`) keurt een overgeslagen test af. Commando's: `cd apps/web && npm run check:peil && npm run typecheck && npm run lint && npm run test:unit`; `flock <WERKMAP>/.lokaal/stack.lock env MSO_STACK_NO_BUILD=1 nice -n 10 make e2e` en `make down`.
- **Poort:** P-media-source-optimizer (volledig) + P-PEIL + P-GIT + P-EERLIJK
- **Valkuilen:** V-058, V-061, V-063, V-004
- **Bewijs:** B05-002, B05-003 en B05-008 blijven "Bezig", "Sim-getest"; C1.3-ALG-05 blijft open voor de punten die op een volgende Peil-versie wachten (noem ze in de opmerking).
- **Agents:** A-VERKEN -> A-ONTWERP -> A-BOUW -> R-TECH -> A-HERSTEL -> R-ONTWERP (VERPLICHT) -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** een afwijking alleen op te lossen is door een Peil-onderdeel lokaal aan te passen; een scherm op 360 breed een andere indeling vraagt dan Peil kent.

### S-P3-290 - MSO: manifest en installatiedocument (standaard Custom App)
- **Repo:** media-source-optimizer | **Fase:** P3 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** C1.3-MSO-06; B05-010 (deel terugdraaien zonder terminal); I04-04-01, I04-04-02, I04-04-07 (documentdeel); MSO-bouwlijst P3-05 en P3-13
- **Vooraf:** S-P3-250 en S-P3-255 klaar
- **Al gedaan?** `ls <WERKMAP>/media-source-optimizer/deploy/manifest <WERKMAP>/media-source-optimizer/deploy/truenas/CUSTOM_APP.md <WERKMAP>/media-source-optimizer/.env.example 2>&1` -> alle drie aanwezig en het manifest slaagt in de strikte validatie: klaar. Op 2026-11-11 bestonden ze niet.
- **Lees eerst:** [CONTRACT], kop "9. Manifeststandaard (B08-001, eigenaar `appstore-en-fork`)" (velden; "Wijzigingen in 1.3"); [DM-MSO], kop "9. Geprioriteerde bouwlijst fase P3 (alleen hiaten)" regels P3-05 en P3-13 en kop "7. Custom App-controle (alles-in-één)"; `docs/TRUENAS_CUSTOM_APP.md`; `<WERKMAP>/ai-server-manager/deploy/manifest/ai-server-manager.manifest.yaml` (voorbeeld van een geldig manifest); [I-04]
- **Bouw:**
  1. Nieuw `deploy/manifest/media-source-optimizer.manifest.yaml`: `install.method: custom_app`, `upgrade.tag_only_rollback_safe: false`, `decisions_required: [D01, D02, D03, D07]` (uit de bouwlijst), `healthcheck.monitor` met pad, verwachte status, timeout en interval, het blok `backup` (export, datasets, `rpo`, `rto`), `network.ports` als enige bron voor poorten, geen `compose`-veld, geen parameter of omgevingsvariabele die met `HUB_` begint. Elke waarde komt uit de image of uit de bestaande documentatie; wat niet gemeten is krijgt geen waarde.
  2. Zolang er geen release is: `accepted_findings` met `digest_pending_release` en een Nederlandse reden (BLOK-06). Geen andere geaccepteerde bevinding zonder dat de validator hem meldt.
  3. Nieuw `deploy/truenas/CUSTOM_APP.md`: de velden van het formulier van de standaard Custom App in de volgorde van het formulier, met `<POOL>` als plaatshouder. Geen echte paden, adressen of namen van de NAS.
  4. Nieuw `.env.example` in de root, alleen voor ontwikkeling, zonder echte waarden.
  5. Werk de gebruikersdocumentatie bij zodat de standaard Custom App de enige installatieweg is: `docs/TRUENAS_CUSTOM_APP.md`, `docs/OPERATIONS.md`, `docs/MIGRATION.md`; `docs/TRUENAS_INSTALL.md` krijgt bovenaan "alleen voor ontwikkeling"; `docs/HARDWARE_ACCEPTANCE.md` wordt herschreven naar de Custom App. De bestanden `deploy/truenas/compose*.yaml` blijven voor ontwikkeling en worden nergens als installatieweg genoemd.
  6. Terugdraaien zonder terminal (bouwlijst P3-13): beschrijf in `docs/TRUENAS_CUSTOM_APP.md` en `docs/MIGRATION.md` de hoofdroute (snapshot terugzetten in de TrueNAS-webinterface plus de vorige image-versie in het formulier); `docker exec` staat er alleen als weg voor experts.
  7. Nieuw runbook "MSO provider outage" in het zesstappenformaat (bouwlijst 11.5) onder `docs/runbooks/` (nieuw).
  8. Een CI-stap die het manifest valideert zodra de validator in de CI beschikbaar is; tot dan staat het lokale commando in `README.md`.
- **Tests (verplicht):** `<WERKMAP>/appstore-en-fork/.venv/bin/jl-manifest validate --strict deploy/manifest/media-source-optimizer.manifest.yaml` (exitcode 0). Negatief: (a) een proefkopie buiten de repo met een parameter `HUB_URL` geeft de fout `reserved_env`; (b) een proefkopie met een `compose`-veld wordt geweigerd; (c) `grep -rn -i 'install via yaml\|docker compose up' docs/TRUENAS_CUSTOM_APP.md docs/OPERATIONS.md docs/MIGRATION.md` geeft geen installatie-instructie meer; (d) `grep -rn '/mnt/' deploy/manifest deploy/truenas/CUSTOM_APP.md` geeft alleen regels met `<POOL>`.
- **Poort:** P-media-source-optimizer (snel) + P-INSTALLATIE + P-CONTRACT + P-GIT + P-EERLIJK
- **Valkuilen:** V-089, V-096, V-097, V-085
- **Bewijs:** C1.3-MSO-06 naar "Bezig", "Sim-getest" (alleen gevalideerd met de validator). Installeren op de NAS via het formulier: "NIET GEVALIDEERD (echte NAS)", STAPPEN_P6.md onderdeel N-P6-05. De I04-regels zijn van `jelly-leon-platform` (S-P3-410).
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-MANIFEST (tegelijk; R-MANIFEST VERPLICHT) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** de validator een veld eist dat alleen op de NAS te meten is (laat het dan open volgens het contract en meld het); de "terugdraaiknop" uit de bouwlijst als bouwwerk wordt gevraagd (dat staat open en is een keuze van de gebruiker, zie hoofdstuk 8).

## Baan home-control-hub (energie en werklast, B14)

Werkmap `<WERKMAP>/home-control-hub`. Poort: P-home-control-hub. Het energiedomein staat in
`apps/api/src/integrations/domains/energy/` (`catalog.py`, `models.py`, `router.py`). De tabellen bestaan al sinds
migratie `apps/api/alembic/versions/0001_basisschema.py` (onder andere `energy_meter`, `energy_meter_role`,
`energy_usage_interval`, `energy_tariff`, `energy_cost_model`, `energy_workload`, `energy_workload_reservation`,
`energy_estimate_provenance`), met vaste regels in de database: een meter is altijd alleen-lezen, een schatting heeft
altijd een herkomst, "onbekend" heeft nooit een waarde. Op 2026-11-11 gaven de routes `/meters`, `/usage`,
`/workloads` en `/advice` nog `501 capability_unavailable` en bestond alleen `/coverage`. Een nieuwe migratie krijgt
het volgende vrije nummer (`ls apps/api/alembic/versions | tail -3`; op 2026-11-11 was `0005_b11_automatisering.py` de
laatste; de baan van P2 in deze repo kan er een hebben toegevoegd). Een testbestand draaien:
`cd apps/api && PATH=/usr/lib/postgresql/16/bin:$PATH HCH_TEST_ADMIN_URL=postgresql+psycopg://postgres@127.0.0.1:5432/postgres ../../.venv/bin/python -m pytest -q -p no:cacheprovider <pad onder tests/>`.
Na elke wijziging van een route: `make openapi && git diff --exit-code docs/openapi/` (de tweede helft faalt als de
export niet is meegecommit). Deze baan bouwt geen enkele route die iets schakelt: de boiler wordt in alle gevallen
alleen gemeten.

### S-P3-300 - Energie: bron my_house en de dekkingsmatrix
- **Repo:** home-control-hub | **Fase:** P3 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** B14-001
- **Vooraf:** S-P3-010 klaar (het ADR wijst aan wie de energiecijfers van my_house leest); in deze repo werkt geen schrijver van P2
- **Al gedaan?** STAND home-control-hub B14-001 en `grep -n '"/meters"' <WERKMAP>/home-control-hub/apps/api/src/integrations/domains/energy/router.py` -> staat `/meters` niet meer in de lijst met 501-routes en is er een test met een nagebootste my_house: klaar.
- **Lees eerst:** [B14], kop "B14-001 — Dekkingsmatrix" en kop "5. Niet-regressie, randgevallen en verbodsbepalingen"; het ADR van S-P3-010 (punt over energie); `apps/api/src/integrations/domains/energy/catalog.py` (bron `my_house`, `EXPECTED_METER_ROLES`); `apps/api/src/integrations/sources.py` (`SourceConfig`, `probe_http`); [DM-MH], kop "6. Hub-adapter: welke bestaande routes de Hub kan gebruiken (connectorcontract §6, enrollment §3)" (regel Energie)
- **Bouw:**
  1. Wijst het ADR de Hub-adapter aan als lezer van my_house, dan leest deze dienst de cijfers bij de Hub en niet bij my_house; wijst het ADR deze dienst aan, dan leest hij rechtstreeks. Bouw precies een van de twee. De rest van deze stap is voor beide gelijk.
  2. Een leesclient (nieuw bestand in `apps/api/src/integrations/domains/energy/`) die alleen GET doet. Voor my_house zijn dat volgens [DM-MH]: `GET /api/v1/homes/{id}/energy/summary`, `.../energy/live`, `.../energy/export?format=json`, `.../tariffs` en `GET /api/v1/energy/limits`. Adres en geheim komen uit de bestaande bronconfiguratie (`PUT /sources/{source_id}`); het geheim staat in de kluis en komt in geen antwoord of logregel.
  3. Vul `energy_meter` en `energy_meter_role` uit wat de bron meldt. Een rol is pas "gemeten" als de bron een meter met die rol levert; anders blijft hij "onbekend" met de reden. Niets wordt uit een naam geraden.
  4. `GET .../energy/meters` geeft de meters met rol, eenheid, bron en laatste meting; `GET .../energy/coverage` toont per verwachte rol: gemeten, geschat of onbekend, met `last_updated` en de reden.
  5. Regels uit het bouwplan, afgedwongen in code en test: geen wattage uit CPU-percentage zonder kalibratie; de airco-meter is van de gedeelde buitenunit en krijgt nooit een binnenunit als rol; de energie van de NAS is alleen "gemeten" met een losse meter.
  6. Versheid: een bron die langer dan `max_age` niet antwoordt maakt de rollen "onbekend" (niet de laatste waarde als actueel).
  7. OpenAPI bijwerken.
- **Tests (verplicht):** nieuw `apps/api/tests/integration/test_b14_001_dekkingsmatrix.py` (nieuw) met een nagebootste bron onder `apps/api/tests/fakes/`. Negatief: (a) bron onbereikbaar: alle rollen "onbekend", geen oude waarde als actueel; (b) de client kan geen ander werkwoord dan GET versturen (test op de client zelf); (c) een meter zonder rol wordt niet aan een rol gekoppeld; (d) een lezer zonder rechten krijgt 401 of 403 voordat er iets wordt gelezen; (e) het geheim van de bron staat in geen antwoord. Commando: het testcommando uit de kop van deze baan met `tests/integration/test_b14_001_dekkingsmatrix.py`, daarna `make lint` en `make openapi && git diff --exit-code docs/openapi/`.
- **Poort:** P-home-control-hub (snel en volledig) + P-CONTRACT + P-VEILIG + P-GIT + P-EERLIJK
- **Valkuilen:** V-001, V-048, V-051, V-094, V-066
- **Bewijs:** B14-001 blijft "Bezig", nu "Sim-getest". Echte meters: "NIET GEVALIDEERD (hardware)"; nodig: besluit D14 en de meters in huis; STAPPEN_P6.md onderdeel N-P6-06.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG (tegelijk; R-VEILIG VERPLICHT: uitgaand verkeer en een geheim) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** het ADR van S-P3-010 geen lezer aanwijst; my_house de energieroutes alleen met een gebruikerssessie vrijgeeft en niet met de koppeling uit S-P3-050.

### S-P3-310 - Energie: tijdreeks met zomertijd, tellerreset en metervervanging
- **Repo:** home-control-hub | **Fase:** P3 | **Omvang:** middel | **Moeilijkheid:** hoog | **Zwaar:** nee
- **Werkpakketten en tests:** B14-002; EX28
- **Vooraf:** S-P3-300 klaar
- **Al gedaan?** STAND home-control-hub B14-002 en `ls <WERKMAP>/home-control-hub/apps/api/tests/integration | grep b14_002` -> status "Bezig" en een test voor een dag van 23 en van 25 uur: klaar.
- **Lees eerst:** [B14], kop "B14-002 — Energietijdreeks"; `apps/api/src/integrations/domains/energy/models.py` (klassen `EnergyUsageInterval`, `EnergyTariff`, `EnergyMeter`); [DM-MH], kop "1. B06-taken (Excel) — per eis" (regels over cumulatieve tellers, zomertijd en metervervanging); `apps/api/src/integrations/timeutil.py`; `apps/api/src/integrations/worker.py` (hoe een stap van de worker is opgebouwd)
- **Bouw:**
  1. Een stap in de worker die de uurcijfers van de bron ophaalt en als intervallen in `energy_usage_interval` zet, in UTC, met `source_ref`. Geen ruwe meetpunten overnemen: alleen de uurtotalen die de bron al maakt, met het kwaliteitslabel van de bron.
  2. Idempotent: hetzelfde interval twee keer ophalen geeft een rij. Een gat in de bron wordt een interval "onbekend" zonder waarde, nooit een nul.
  3. Tellerreset: neem het kenmerk van de bron over in `counter_reset`; reken nooit zelf een negatief verschil om.
  4. Metervervanging: de nieuwe meter verwijst met `replaced_meter_id` naar de oude; een rapport over een periode telt beide na elkaar en nooit dubbel.
  5. `GET .../energy/usage` met een periode (dag, week, maand) en de tijdzone van het huis: de dagen worden in lokale tijd gesneden. Een dag met de overgang naar zomertijd heeft 23 uur, terug 25 uur; het dagtotaal klopt in beide gevallen.
  6. Kosten: alleen met een tarief uit de bron (`energy_tariff`, vast of dynamisch). Zonder tarief voor het tijdvak is het bedrag "onbekend"; het verbruik blijft zichtbaar. Invoer en teruglevering apart (`direction`).
  7. Elk getal in het antwoord draagt kwaliteit (gemeten, geschat, onbekend) en bron. OpenAPI bijwerken.
- **Tests (verplicht):** nieuw `apps/api/tests/integration/test_b14_002_tijdreeks.py` (nieuw). Negatief: (a) dag van 23 uur en dag van 25 uur: het dagtotaal is de som van de uren van die lokale dag; (b) tellerreset midden op de dag: geen negatieve of dubbele waarde, label zichtbaar; (c) metervervanging: de maand telt niet dubbel; (d) een gat blijft "onbekend" en maakt het dagtotaal "onvolledig"; (e) twee keer ophalen geeft geen dubbele rijen; (f) zonder tarief geen bedrag. Commando: het testcommando uit de kop van deze baan met `tests/integration/test_b14_002_tijdreeks.py`, daarna `make lint` en `make openapi && git diff --exit-code docs/openapi/`.
- **Poort:** P-home-control-hub (snel en volledig) + P-CONTRACT + P-GIT + P-EERLIJK
- **Valkuilen:** V-056, V-051, V-003, V-066
- **Bewijs:** B14-002 naar "Bezig", "Sim-getest". EX28 is een regel van het programma en blijft "Geblokkeerd": "NIET GEVALIDEERD (hardware)", STAPPEN_P6.md stap S-P6-21.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N4, A-HERSTEL N4 (moeilijkheid hoog: tijdrekenen en idempotentie); verder standaard
- **Stop en vraag als:** de bron geen uurtotalen met kwaliteitslabel levert; de tijdzone van het huis nergens is vastgelegd (dan niet aannemen maar vragen).

### S-P3-320 - Energie: werklast en reserveringen (alleen plannen en voorstellen)
- **Repo:** home-control-hub | **Fase:** P3 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** B14-003
- **Vooraf:** S-P3-310 klaar
- **Al gedaan?** STAND home-control-hub B14-003 en `ls <WERKMAP>/home-control-hub/apps/api/tests/integration | grep b14_003` -> status "Bezig" en een test: klaar.
- **Lees eerst:** [B14], kop "B14-003 — Workload reservations"; `apps/api/src/integrations/domains/energy/models.py` (klassen `EnergyWorkload`, `EnergyWorkloadReservation`); `apps/api/src/integrations/domains/energy/catalog.py` (bronnen `truenas_metrics` en `mediaguard_encoding`); [DM-MG], kop "B04-005 — Globale resource-scheduler-hooks (F2)" en kop "H. Wat NIET mag (eigenaarschap en invarianten)"; het ADR van S-P3-010
- **Bouw:**
  1. Bron van de werklastgegevens: volgens `catalog.py` krijgt deze dienst de belasting van de NAS en de encodeerstatus van MediaGuard via de Hub. Welke route dat is: ONBEKEND - eerst vaststellen met: `grep -rn 'truenas_metrics\|mediaguard_encoding' <WERKMAP>/home-control-hub/apps/api/src | head` en het ADR van S-P3-010. Bestaat de route niet, dan toont de planner "onbekend" voor die bron en bouw je alleen het model en de regels.
  2. `GET .../energy/workloads`: de bekende werklasten met prioriteitsklasse (`interactief`, `hoog`, `normaal`, `achtergrond`), of ze onderbreekbaar zijn en of ze een veilig stoppunt nodig hebben.
  3. Reserveringen: tijdvensters per werklast met status (`voorstel`, `gepland`, `actief`, `wacht`, `klaar`, `geannuleerd`) en bij "wacht" een reden uit een vaste lijst van deze dienst. Vrije tekst van MediaGuard (bijvoorbeeld de reden van een kijkpauze) wordt niet overgenomen, opgeslagen of getoond.
  4. Deze dienst pauzeert, start of versnelt zelf niets. Een reservering is een plan. Het wachten van AV1 bij een lopende stream is en blijft werk van MediaGuard zelf (kijkpauze); deze stap toont alleen dat het zo is.
  5. Een voorstel dat wel iets zou veranderen (capability `energy.reservations.propose`, R1) wordt alleen als voorstel vastgelegd; uitvoeren loopt via het goedkeuringspad van de Hub en de eigen route van de eigenaar-app, niet via deze dienst. In P3 is er geen uitvoering.
  6. Antwoord voor de dagplanner: per uur wat er loopt, wat wacht en waarom. OpenAPI bijwerken.
- **Tests (verplicht):** nieuw `apps/api/tests/integration/test_b14_003_werklast.py` (nieuw). Negatief: (a) een werklast `achtergrond` wacht als er een `interactief` loopt, en de wachtreden komt uit de vaste lijst; (b) er bestaat in deze dienst geen route die MediaGuard of TrueNAS iets laat doen (de test loopt de OpenAPI-export af: onder `/energy` alleen GET, plus hooguit het vastleggen van een voorstel); (c) een bron die niet antwoordt geeft "onbekend", geen lege planning die op "niets te doen" lijkt; (d) overlappende vensters voor dezelfde werklast worden geweigerd. Commando: het testcommando uit de kop van deze baan met `tests/integration/test_b14_003_werklast.py`, daarna `make lint` en `make openapi && git diff --exit-code docs/openapi/`.
- **Poort:** P-home-control-hub (snel en volledig) + P-CONTRACT + P-HARDE-EIS (MediaGuard wordt alleen gelezen; geen ingreep in encodering of voortgang) + P-GIT + P-EERLIJK
- **Valkuilen:** V-046, V-051, V-001
- **Bewijs:** B14-003 naar "Bezig", "Sim-getest". De acceptatie "een live stream laat AV1 wachten zonder bestandsverlies" is een proef op de NAS: "NIET GEVALIDEERD (echte NAS)", STAPPEN_P6.md onderdeel N-P6-05.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-HARDE-EIS (tegelijk; R-HARDE-EIS VERPLICHT: raakt de MediaGuard-koppeling) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard (R-HARDE-EIS N4)
- **Stop en vraag als:** het bouwplan zo gelezen wordt dat deze dienst zelf moet pauzeren of onderbreken (dat botst met het eigenaarschap van MediaGuard en met BG-05); de Hub geen route heeft waar de gegevens vandaan kunnen komen.

### S-P3-330 - Energie: advies over kosten met aannames en bandbreedte
- **Repo:** home-control-hub | **Fase:** P3 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** B14-004
- **Vooraf:** S-P3-310 en S-P3-320 klaar
- **Al gedaan?** STAND home-control-hub B14-004 en `ls <WERKMAP>/home-control-hub/apps/api/tests/integration | grep b14_004` -> status "Bezig" en een test voor "zonder meter geen bedrag": klaar.
- **Lees eerst:** [B14], kop "B14-004 — AI advies voor kosten"; `apps/api/src/integrations/domains/energy/models.py` (klassen `EnergyCostModel`, `EnergyEstimateProvenance`); `docs/platform-v2/EVIDENCE.json` (regel B14-004: de kolom `requires_meter` is nu alleen een vlag); [B14], kop "5. Niet-regressie, randgevallen en verbodsbepalingen"
- **Bouw:**
  1. In deze stap komt geen taalmodel. Het advies is rekenwerk: vergelijk gelijkwaardige dagen (zelfde weekdag-soort en vergelijkbare werklast) en leg het verband tussen verbruik en werklast met een zekerheid tussen 0 en 1. Een toelichting door AI hoort bij fase P5.
  2. `GET .../energy/advice`: per advies de aannames, de gebruikte dagen, de zekerheid en een besparing als bandbreedte (laag tot hoog), met de vaste tekst dat de besparing niet gegarandeerd is.
  3. Harde regel: zonder gemeten reeks voor de betrokken meter is er geen bedrag en geen besparing; het advies meldt dan "geen meter, geen bedrag". Maak van de vlag `requires_meter` een echte controle op het bestaan van gemeten intervallen in het tijdvak.
  4. Een schatting heeft altijd een herkomst (`energy_estimate_provenance`) en een methode; een schatting uit CPU-percentage mag alleen met een kalibratie tegen een echte meter.
  5. Een advies schakelt niets en stelt geen schakelactie voor een apparaat voor zonder dat erbij staat dat goedkeuring nodig is. De boiler komt in geen enkel advies voor als iets dat te schakelen is.
  6. Te weinig vergelijkbare dagen: geen advies, met de reden. OpenAPI bijwerken.
- **Tests (verplicht):** nieuw `apps/api/tests/integration/test_b14_004_advies.py` (nieuw). Negatief: (a) zonder gemeten reeks bevat het antwoord geen bedrag en geen besparing; (b) een schatting zonder herkomst wordt door de database geweigerd en door de route niet getoond; (c) minder dan het minimum aan vergelijkbare dagen geeft geen advies; (d) geen enkel advies noemt de boiler als schakelbaar; (e) de bandbreedte heeft altijd laag kleiner dan of gelijk aan hoog en nooit een enkel "gegarandeerd" getal. Commando: het testcommando uit de kop van deze baan met `tests/integration/test_b14_004_advies.py`, daarna `make lint` en `make openapi && git diff --exit-code docs/openapi/`.
- **Poort:** P-home-control-hub (snel en volledig) + P-CONTRACT + P-GIT + P-EERLIJK
- **Valkuilen:** V-003, V-051, V-066; een bedrag tonen zonder meter is de fout die deze stap moet voorkomen
- **Bewijs:** B14-004 naar "Bezig", "Sim-getest". Met echte meters en echte dagen: "NIET GEVALIDEERD (hardware)", STAPPEN_P6.md onderdeel N-P6-06.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** de gebruiker in P3 al een AI-toelichting verwacht (dat is werk van P5); "gelijkwaardige dagen" niet te bepalen is zonder buitentemperatuur of een andere bron die er niet is.

### S-P3-340 - Energie: meldingen bij afwijkingen
- **Repo:** home-control-hub | **Fase:** P3 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** B14-005; raakt EX27
- **Vooraf:** S-P3-310 klaar
- **Al gedaan?** STAND home-control-hub B14-005 en `ls <WERKMAP>/home-control-hub/apps/api/tests/integration | grep b14_005` -> status "Bezig" en een test: klaar.
- **Lees eerst:** [B14], kop "B14-005 — Alert bij afwijkingen"; [CONTRACT], kop "7. Event-envelope"; `apps/api/src/integrations/events.py`; `apps/api/src/integrations/domains/energy/catalog.py` (`forbidden_nl` bij de bron `my_house`); `apps/api/tests/integration/test_contract_1_3_events.py` (vorm van een eventtest)
- **Bouw:**
  1. Vier regels, elk met een drempel die de beheerder instelt en een basislijn uit de eigen tijdreeks: meter offline (geen meting binnen de ingestelde tijd), ongebruikelijk boilerverbruik, groeiende belasting van de NAS, overschreden budget.
  2. Een regel werkt alleen op verse gegevens: is de reeks verouderd, dan is de uitkomst "onbekend" en volgt hooguit de melding "meter offline", nooit een melding over verbruik.
  3. Een afwijking wordt een gebeurtenis in de bestaande uitgaande rij (`events.py`), in de envelope van het contract, met ernst en zonder persoonsgegevens. Dezelfde afwijking geeft een gebeurtenis en bij herstel een tweede; geen stroom van herhalingen.
  4. Geen enkele regel en geen enkele route in het energiedomein schakelt iets. De boiler wordt alleen gemeten; er komt geen route, knop of voorstel om hem te schakelen. Leg dat vast in een test op de OpenAPI-export.
  5. Instellingen van de drempels: een route voor de beheerder met validatie (geen negatieve of onzinnige drempels) en `Idempotency-Key` volgens de bestaande aanpak (`idempotency.py`).
  6. OpenAPI bijwerken.
- **Tests (verplicht):** nieuw `apps/api/tests/integration/test_b14_005_meldingen.py` (nieuw). Negatief: (a) verouderde reeks geeft geen verbruiksmelding; (b) dezelfde afwijking geeft precies een gebeurtenis; (c) onder `/energy` bestaat geen route met een schrijvend werkwoord behalve de drempelinstelling, en geen route met "boiler" en een schrijvend werkwoord; (d) een lezer kan de drempels niet wijzigen (403); (e) de gebeurtenis bevat geen adres, naam of geheim. Commando: het testcommando uit de kop van deze baan met `tests/integration/test_b14_005_meldingen.py`, daarna `make lint` en `make openapi && git diff --exit-code docs/openapi/`.
- **Poort:** P-home-control-hub (snel en volledig) + P-CONTRACT + P-VEILIG (boiler: alleen meten) + P-GIT + P-EERLIJK
- **Valkuilen:** V-051, V-046, V-003, V-066
- **Bewijs:** B14-005 naar "Bezig", "Sim-getest". Echte meters en de echte boiler: "NIET GEVALIDEERD (hardware)", STAPPEN_P6.md stap S-P6-21 (EX27) en onderdeel N-P6-06.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG (tegelijk; R-VEILIG VERPLICHT: risicoklasse en het boilerverbod) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** een melding alleen zin heeft met een actie erachter (dan is het een voorstel voor het goedkeuringspad van de Hub en geen werk van deze stap); het contract geen passend domein of werkwoord voor een energiegebeurtenis kent.

### S-P3-350 - Energie op de statuspagina van de dienst
- **Repo:** home-control-hub | **Fase:** P3 | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** B14-001, B14-005 (schermdeel van de dienst zelf)
- **Vooraf:** S-P3-340 klaar
- **Al gedaan?** `grep -n -i 'dekking\|meter' <WERKMAP>/home-control-hub/apps/api/src/integrations/status_page.py | head -5` -> een blok over energie met eigen toestanden en schermafdrukken onder `docs/screenshots`: klaar.
- **Lees eerst:** [PEIL]; [CONTRACT], koppen "13. Ontwerptaal" en "3.7 Koppelen via de statuspagina"; `apps/api/src/integrations/status_page.py`; `apps/api/src/integrations/peil.py`; `docs/adr/ADR-0012-ontwerpreview-statuspagina.md`
- **Bouw:**
  1. A-ONTWERP eerst: een blok "Energie" op de bestaande statuspagina: per verwachte meterrol gemeten, geschat of onbekend, de laatste meting en openstaande afwijkingen. Toestanden: leeg (geen bron ingesteld), bezig, storing, verouderd. Breedtes 360, 390, 768 en 1440.
  2. Bouw het blok met de bestaande Peil-kopie van deze repo; geen eigen kleuren of onderdelen. `python3 tools/peil_kopie.py controleer` blijft groen.
  3. Het blok toont geen bedragen en geen grafieken; de schermen Energie en Kosten zijn van de Hub (S-P3-160). Het blok linkt naar de Hub als het Hub-adres geldig is, anders geen link.
  4. Geen knop die iets schakelt of een bron wijzigt.
  5. Voeg de nieuwe toestanden toe aan wat `make toestanden` opbouwt en maak schermafdrukken met `make schermafdrukken` (alleen fixture-gegevens).
- **Tests (verplicht):** `python3 tools/peil_kopie.py controleer && make test-ui`; `make toestanden`; `make schermafdrukken`; `make ontwerpreview`. Negatief: (a) verouderde meting toont "verouderd" en niet de oude waarde als actueel; (b) zonder bron staat er de lege toestand met uitleg, geen foutpagina; (c) een ongeldig Hub-adres geeft geen link.
- **Poort:** P-home-control-hub (snel, UI-deel) + P-PEIL + P-GIT + P-EERLIJK
- **Valkuilen:** V-058, V-061, V-063, V-064
- **Bewijs:** B14-001 en B14-005 blijven "Bezig", "Sim-getest" (opmerking: schermafdrukken van de statuspagina). De schermen uit het bouwplan (Energie, Kosten, Verbruiksbronnen, GPU/CPU, Werkloadplanning, Vergelijk, Prognoses) zijn van de Hub; in P3 is daarvan alleen Kosten gebouwd (S-P3-160), zie hoofdstuk 8.
- **Agents:** A-VERKEN -> A-ONTWERP -> A-BOUW -> R-TECH -> A-HERSTEL -> R-ONTWERP (VERPLICHT) -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** het blok een onderdeel vraagt dat Peil niet heeft; de statuspagina door het blok trager wordt dan de bestaande test toelaat.

## Baan jelly-leon-platform (controlelijsten I03, I04, I05, I15...I20 en manifestkopieen)

Werkmap `<WERKMAP>/jelly-leon-platform`. Poort: P-jelly-leon-platform. Deze baan bouwt geen dienst en geen route: zij
legt de installatiedocumenten I03, I04, I05 en I15 tot en met I20 vast als controlelijst (`kind: checklist`,
`install.method: none`) in het formaat dat I01 en I02 al hebben, en neemt de manifesten van de drie eigen apps over
als kopie. Vaste gegevens (gemeten op 2026-11-11):

- Bestaande controlelijsten: `install/checklists/I01_TRUENAS_BASIS.checklist.yaml` en
  `install/checklists/I02_BACKUP_EN_RESTORE.checklist.yaml`. Schema: `schemas/checklist-v1.schema.json`. Controle:
  `tools/checklists.py`. Test: `tests/repo/test_checklists.py`. Besluit: `docs/adr/ADR-0015-controlelijsten-i01-i02.md`.
- De regels die `tools/checklists.py` afdwingt: de stappen dekken precies de Excel-taken van het document, in
  volgorde (bron `docs/platform-v2/EXCEL_TAKEN.json`); `titel_nl`, `acceptatie_nl` en `risico` zijn letterlijk gelijk
  aan de Excel-kolommen `Taak`, `Acceptatie` en `Risico`; alleen alleen-lezen TrueNAS-methoden (lijst `LEZEND`); geen
  terminalopdrachten en geen voorbeeldwaarden (adres, poolnaam) in `uitvoeren_nl`, `acceptatie_nl`, `bij_fout_nl` en
  `handmatig_ui_pad_nl`; "Sim-getest" alleen bij een stap met een TrueNAS-methode; elke stap noemt minstens een van
  `NIET GEVALIDEERD (echte NAS)`, `NIET GEVALIDEERD (hardware)`, `NIET GEVALIDEERD (account)`; een stap met een
  account (OneDrive) noemt `NIET GEVALIDEERD (account)`; besluiten van een stap staan ook in de lijst `besluiten` van
  de controlelijst.
- Waar de tekst van het document niet kan (terminal, YAML als installatieweg), wijkt `uitvoeren_nl` af en zegt het
  veld `afwijking_van_document_nl` waarom. De titel blijft de Excel-titel.
- Commando's: `make lint`; `make test-repo` (alle tests onder `tests/repo`); een testbestand:
  `.venv/bin/python -m pytest -q tests/repo/<bestand>`; `make manifesten` (draait `tools/manifesten.py`,
  `tools/manifest_kopie.py controleer`, `tools/validator_kopie.py controleer` en `tools/checklists.py`).
- Nieuw ADR: volgend vrij nummer (`ls docs/adr | tail -3`; op 2026-11-11 was ADR-0023 de laatste).
- EVIDENCE: op 2026-11-11 had `docs/platform-v2/EVIDENCE.json` geen regels voor I03, I04, I05 en I15 tot en met I20.
  Nieuwe regels krijgen de vorm van de bestaande I01- en I02-regels (bekijk er een met STAND `jelly-leon-platform`
  `I02-02-01`): status "Geblokkeerd", validatie met de letterlijke tekst "NIET GEVALIDEERD (...)" en een
  blokkadetekst die zegt wat nodig is. Geen van deze regels wordt in P3 "Bezig" op grond van een document alleen.
- Deze baan installeert en wijzigt niets op een NAS en beschrijft nergens een terminalweg.

### S-P3-400 - Platform: ADR en gereedschap voor de controlelijsten I03...I20
- **Repo:** jelly-leon-platform | **Fase:** P3 | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** voorwaarde voor I03-03-01...I03-03-08, I04-04-01...I04-04-08, I05-05-01...I05-05-08, I15-15-01...I15-15-06, I16-16-01...I16-16-06, I17-17-01...I17-17-06, I18-18-01...I18-18-06, I19-19-01...I19-19-06, I20-20-01...I20-20-05 (geen statuswijziging in deze stap)
- **Vooraf:** S-P3-000 klaar; geen keten van P2 actief in deze repo
- **Al gedaan?** `ls <WERKMAP>/jelly-leon-platform/docs/adr | tail -3` en `grep -n 'I01_TRUENAS_BASIS\|== 8' <WERKMAP>/jelly-leon-platform/tests/repo/test_checklists.py` -> een ADR over de controlelijsten van de bestaande apps en een test die niet meer vastzit aan twee bestandsnamen en acht stappen betekent klaar. Op 2026-11-11 eiste de test precies de twee bestanden I01 en I02 en `len(stappen) == 8`.
- **Lees eerst:** `docs/adr/ADR-0015-controlelijsten-i01-i02.md` (koppen "Besluit" en "Gevolgen"); `tools/checklists.py` (functies `excel_taken`, `lijsten`, `controleer_lijst`, `controleer_alle`); `tests/repo/test_checklists.py`; `schemas/checklist-v1.schema.json`; [CONTRACT], kop "9. Manifeststandaard (B08-001, eigenaar `appstore-en-fork`)" (deel "Wijzigingen in 1.3": `kind: checklist`)
- **Bouw:**
  1. Nieuw ADR `docs/adr/ADR-<nummer>-controlelijsten-bestaande-apps.md` (nieuw): de documenten I03, I04, I05 en I15 tot en met I20 krijgen een controlelijst in hetzelfde formaat `checklist v1`; `aanpak` is `behouden_en_valideren` voor apps die al draaien en `inrichten_en_testen` alleen waar het document een nieuwe inrichting beschrijft; de lijsten installeren niets; waar een document een terminal of YAML als weg noemt, beschrijft de lijst de weg via de TrueNAS-webinterface of het formulier van de standaard Custom App en legt de afwijking vast.
  2. `tests/repo/test_checklists.py`, functie `test_checklists_are_valid_and_cover_the_excel_tasks`: vervang de vaste verzameling van twee bestandsnamen door "elke lijst in `install/checklists/` hoort bij precies een document onder `03_INSTALLATIE/` en geen document heeft twee lijsten", en vervang `len(stappen) == 8` door "het aantal stappen is gelijk aan het aantal Excel-taken van dat document". De bestaande negatieve tests (`_mutate`) blijven en gelden voor elke lijst.
  3. Loop `tools/checklists.py` na op alles wat alleen voor I01 en I02 geldt (vaste namen, vaste aantallen): `grep -n 'I01\|I02\|== 8' tools/checklists.py`. Maak het algemeen zonder een regel te verzwakken.
  4. Stel vast of het schema iets tegenhoudt: `id` heeft het patroon `^I[0-9]{2}$` (I03 tot en met I20 passen). Wijzig het schema alleen als een verplicht veld voor een bestaande app geen zinnige waarde kan hebben; leg dat dan vast in het ADR.
  5. Werk `install/manifests/README.md` of het document dat de controlelijsten noemt bij met een regel per nieuwe lijst (naam en document), zonder NAS-gegevens. Welk document dat is: ONBEKEND - eerst vaststellen met: `grep -rln 'checklists' <WERKMAP>/jelly-leon-platform/docs <WERKMAP>/jelly-leon-platform/install --include=*.md`.
- **Tests (verplicht):** `make lint && .venv/bin/python -m pytest -q tests/repo/test_checklists.py && .venv/bin/python tools/checklists.py`. Negatief: (a) een proefkopie van een lijst met een stap minder dan de Excel-taken faalt; (b) een tweede lijst voor hetzelfde document faalt; (c) een lijst met een terminalopdracht in `uitvoeren_nl` faalt nog steeds (bestaande negatieve test blijft groen). Doe (a) en (b) als test in het testbestand, niet met de hand.
- **Poort:** P-jelly-leon-platform (snel) + P-INSTALLATIE (leescontrole: geen terminalweg) + P-GIT + P-EERLIJK
- **Valkuilen:** V-003, V-096, V-022
- **Bewijs:** geen statuswijziging. Geen nieuwe EVIDENCE-regels in deze stap.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-MANIFEST (tegelijk; R-MANIFEST VERPLICHT) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** het algemeen maken van de test een bestaande regel uit ADR-0015 zou verzwakken; het schema voor de bestaande apps een nieuw verplicht veld nodig heeft (dat is een formaatwijziging en vraagt een besluit).

### S-P3-410 - Platform: controlelijsten I03 (MediaGuard) en I04 (Media Source Optimizer)
- **Repo:** jelly-leon-platform | **Fase:** P3 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** I03-03-01, I03-03-02, I03-03-03, I03-03-04, I03-03-05, I03-03-06, I03-03-07, I03-03-08; I04-04-01, I04-04-02, I04-04-03, I04-04-04, I04-04-05, I04-04-06, I04-04-07, I04-04-08
- **Vooraf:** S-P3-400 klaar
- **Al gedaan?** `ls <WERKMAP>/jelly-leon-platform/install/checklists | grep -E '^I0[34]_'` en STAND `jelly-leon-platform` `I03-03-01` `I04-04-01` -> twee lijsten en EVIDENCE-regels voor alle zestien ID's betekent klaar.
- **Lees eerst:** [I-03] en [I-04] (koppen "2. Stappen in uitvoeringsvolgorde", "4. Terugdraaien / verwijderen" en "5. Let op"); `install/checklists/I02_BACKUP_EN_RESTORE.checklist.yaml` (voorbeeld van alle velden); [DM-MG], kop "E. Installatie- en app-stappen (I-/A-documenten)"; [DM-MSO], kop "3. Installatie- en bestaande-app-stappen (MSO-kant)"; [CONTRACT], kop "2.3 Bestaande apps (MediaGuard, MSO, my_house, Jellyfin/Jelly Leon, Emby)" regel 7 (HARDE EIS)
- **Bouw:**
  1. Nieuw `install/checklists/I03_MEDIAGUARD.checklist.yaml` (nieuw) met acht stappen. Titel, acceptatie en risico letterlijk uit `docs/platform-v2/EXCEL_TAKEN.json` (haal ze op met `python3 -c "import json,sys;[print(t['ID'],t['Taak'],t['Acceptatie'],t['Risico'],sep=' | ') for t in json.load(open('docs/platform-v2/EXCEL_TAKEN.json')) if t['ID'].startswith(sys.argv[1])]" I03-`; controleer eerst de vorm van het bestand met `head -c 400`). `document: 03_INSTALLATIE/I03_MEDIAGUARD.md`, `aanpak: behouden_en_valideren`, `installatie: geen`, `mutaties_door_platform: false`.
  2. I03, HARDE EIS in de tekst van de stappen: stap 3 (back-up inclusief forks) is voorwaarde voor stap 4; stap 4 (update) noemt in `uitvoeren_nl` dat een update alleen mag met het upgradebewijs van die release en met de vorige image-versie als terugval, en dat de gebruiker de update zelf doet in het formulier van de Custom App. De versie "1.2.2" staat in de Excel-titel en blijft daar letterlijk staan; `uitvoeren_nl` noemt geen andere versie.
  3. I03 stap 8 (Hub-API integratie): `uitvoeren_nl` beschrijft het invoeren van de viewer-sleutel in de Hub-UI (S-P3-070) en de controle dat de Hub dezelfde status toont als MediaGuard; `wijze: handmatig_bewijs`.
  4. Nieuw `install/checklists/I04_MEDIA_SOURCE_OPTIMIZER.checklist.yaml` (nieuw) met acht stappen, zelfde opzet. Stap 6 (1.6.0 veranderingen accepteren) en stap 4 (Prowlarr en clients live) vragen echte diensten en een akkoord: `validatie_nu` noemt `NIET GEVALIDEERD (echte NAS)` en de blokkadetekst verwijst naar T-12. Stap 8 (Hub koppelen) beschrijft de machine-sleutel uit S-P3-220.
  5. Geen stap krijgt een TrueNAS-methode die niet in de lijst `LEZEND` van `tools/checklists.py` staat. Een stap zonder methode krijgt `wijze: handmatig_bewijs` of `handmatig_in_truenas_ui` met een `handmatig_ui_pad_nl` in woorden (menu's, geen opdrachten).
  6. Waar het document een terminalopdracht noemt: `uitvoeren_nl` beschrijft de weg via de webinterface en `afwijking_van_document_nl` zegt waarom.
  7. EVIDENCE: voeg zestien regels toe in de vorm van de bestaande I-regels, status "Geblokkeerd", met per regel de juiste soort (NAS, hardware voor I03-03-06 en I03-03-07, account waar een account nodig is).
- **Tests (verplicht):** `make lint && .venv/bin/python -m pytest -q tests/repo/test_checklists.py && make manifesten`, daarna de EVIDENCE-test van deze repo (`make test-repo`). Negatief: (a) verander in een proefkopie buiten de repo een `acceptatie_nl` met een teken: `tools/checklists.py` moet falen; (b) `grep -n -i 'ssh\|sudo\|docker \|midclt\|zfs \|/mnt/' install/checklists/I03_MEDIAGUARD.checklist.yaml install/checklists/I04_MEDIA_SOURCE_OPTIMIZER.checklist.yaml` geeft niets.
- **Poort:** P-jelly-leon-platform (snel) + P-INSTALLATIE + P-HARDE-EIS (leescontrole op I03 stap 3 en 4) + P-GIT + P-EERLIJK
- **Valkuilen:** V-096, V-097, V-089, V-070
- **Bewijs:** I03-03-01...I03-03-08 en I04-04-01...I04-04-08 nieuw als "Geblokkeerd" met "NIET GEVALIDEERD (echte NAS): controlelijst geschreven en gecontroleerd tegen de Excel-taken; uitvoeren op de NAS door de gebruiker (STAPPEN_P6.md onderdeel N-P6-05)". I03-03-06: "NIET GEVALIDEERD (hardware)" erbij (echte GPU). I03-03-07: "NIET GEVALIDEERD (hardware)" (echte telefoon).
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-MANIFEST + R-HARDE-EIS (tegelijk; R-MANIFEST en R-HARDE-EIS VERPLICHT) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard (R-HARDE-EIS N4; dit is tekst, geen migratiecode, dus geen topmodel)
- **Stop en vraag als:** een Excel-titel of acceptatie iets vraagt dat tegen de HARDE EIS of tegen de installatieregel ingaat en niet met `afwijking_van_document_nl` op te lossen is; de EVIDENCE-test van deze repo een regel "Geblokkeerd" zonder commit weigert.

### S-P3-420 - Platform: controlelijsten I15 (Immich), I16 (Prowlarr) en I17 (SABnzbd)
- **Repo:** jelly-leon-platform | **Fase:** P3 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** I15-15-01, I15-15-02, I15-15-03, I15-15-04, I15-15-05, I15-15-06; I16-16-01, I16-16-02, I16-16-03, I16-16-04, I16-16-05, I16-16-06; I17-17-01, I17-17-02, I17-17-03, I17-17-04, I17-17-05, I17-17-06
- **Vooraf:** S-P3-400 klaar
- **Al gedaan?** `ls <WERKMAP>/jelly-leon-platform/install/checklists | grep -E '^I1[567]_'` en STAND `jelly-leon-platform` `I15-15-01` `I16-16-01` `I17-17-01` -> drie lijsten en achttien EVIDENCE-regels betekent klaar.
- **Lees eerst:** `<DOCS>/03_INSTALLATIE/I15_IMMICH.md`, `I16_PROWLARR.md` en `I17_SABNZBD.md` (kop "2. Stappen in uitvoeringsvolgorde"); `install/checklists/I02_BACKUP_EN_RESTORE.checklist.yaml` (de stap met OneDrive als voorbeeld van `NIET GEVALIDEERD (account)`); [DM-MG], kop "E. Installatie- en app-stappen (I-/A-documenten)" (regels I16); [CONTRACT], kop "2.3 Bestaande apps (MediaGuard, MSO, my_house, Jellyfin/Jelly Leon, Emby)" regels 1 en 9; `<DOCS>/04_BESTAANDE_APPS/APP_REGISTER.md`
- **Bouw:**
  1. Drie nieuwe lijsten (nieuw): `install/checklists/I15_IMMICH.checklist.yaml`, `I16_PROWLARR.checklist.yaml`, `I17_SABNZBD.checklist.yaml`, elk met zes stappen, `aanpak: behouden_en_valideren`, `installatie: geen`, `mutaties_door_platform: false`. Titels, acceptatie en risico letterlijk uit `docs/platform-v2/EXCEL_TAKEN.json`.
  2. Deze apps zijn van derden en draaien al. Geen stap laat het platform iets wijzigen in de app; elke stap is een meting (alleen-lezen TrueNAS-methode) of een handeling van de gebruiker in de eigen webinterface van de app.
  3. I15 stap 2 (OneDrive restore): `validatie_nu` noemt `NIET GEVALIDEERD (account)`; de stap verwijst met `wijze: verwijzing` naar de bijbehorende stap van I02 als die daar staat. I15 stap 4 (Hub connector opt-in) en stap 5 (SSO evaluatie): beschrijf alleen wat het document zegt; er is in P3 geen Immich-adapter gebouwd, dus `uitvoeren_nl` zegt dat de stap wacht tot die er is.
  4. I16: eigenaarschap volgens [DM-MG] (MediaGuard wijzigt alleen de eigen tags; geen tweede reconciler). Stap 4 (MSO integration, lusdetectie) verwijst naar MSO; de lijst belooft niets wat MSO niet doet.
  5. I17: stap 5 (Backup config) en stap 6 (Health en update) beschrijven de weg via de webinterface van SABnzbd en de TrueNAS-webinterface; geen bestandspaden met een echte poolnaam.
  6. EVIDENCE: achttien regels, status "Geblokkeerd", met de juiste soort per regel.
- **Tests (verplicht):** `make lint && .venv/bin/python -m pytest -q tests/repo/test_checklists.py && make manifesten && make test-repo`. Negatief: (a) een proefkopie met een schrijvende TrueNAS-methode (een naam die past op de regel `SCHRIJVEND` in `tools/checklists.py`) faalt; (b) een proefkopie van I15 waarin stap 2 geen `NIET GEVALIDEERD (account)` noemt faalt.
- **Poort:** P-jelly-leon-platform (snel) + P-INSTALLATIE + P-GIT + P-EERLIJK
- **Valkuilen:** V-096, V-097, V-089, V-003
- **Bewijs:** I15-15-01...I15-15-06, I16-16-01...I16-16-06 en I17-17-01...I17-17-06 nieuw als "Geblokkeerd" met "NIET GEVALIDEERD (echte NAS): controlelijst geschreven; uitvoeren door de gebruiker (STAPPEN_P6.md onderdeel N-P6-05)". I15-15-02: "NIET GEVALIDEERD (account)" en onderdeel N-P6-02.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-MANIFEST (tegelijk; R-MANIFEST VERPLICHT) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** een stap alleen uitvoerbaar is met een opdracht in een terminal en er geen weg via een webinterface bestaat (dan wordt de stap "handmatig_bewijs" met de reden, en de regisseur meldt het aan de gebruiker).

### S-P3-430 - Platform: controlelijsten I18 (qBittorrent), I19 (Seerr) en I20 (Bazarr)
- **Repo:** jelly-leon-platform | **Fase:** P3 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** I18-18-01, I18-18-02, I18-18-03, I18-18-04, I18-18-05, I18-18-06; I19-19-01, I19-19-02, I19-19-03, I19-19-04, I19-19-05, I19-19-06; I20-20-01, I20-20-02, I20-20-03, I20-20-04, I20-20-05
- **Vooraf:** S-P3-400 klaar
- **Al gedaan?** `ls <WERKMAP>/jelly-leon-platform/install/checklists | grep -E '^(I18|I19|I20)_'` en STAND `jelly-leon-platform` `I18-18-01` `I19-19-01` `I20-20-01` -> drie lijsten en zeventien EVIDENCE-regels betekent klaar.
- **Lees eerst:** `<DOCS>/03_INSTALLATIE/I18_QBITTORRENT.md`, `I19_SEERR.md` en `I20_BAZARR.md` (kop "2. Stappen in uitvoeringsvolgorde"); [DM-MG], kop "E. Installatie- en app-stappen (I-/A-documenten)" (regels I19 en I20); [DM-MSO], kop "3. Installatie- en bestaande-app-stappen (MSO-kant)"; `<DOCS>/04_BESTAANDE_APPS/A09_BAZARR.md`; `install/checklists/I01_TRUENAS_BASIS.checklist.yaml`
- **Bouw:**
  1. Drie nieuwe lijsten (nieuw): `install/checklists/I18_QBITTORRENT.checklist.yaml` (zes stappen), `I19_SEERR.checklist.yaml` (zes stappen) en `I20_BAZARR.checklist.yaml` (vijf stappen), `aanpak: behouden_en_valideren`. Titels, acceptatie en risico letterlijk uit `docs/platform-v2/EXCEL_TAKEN.json`.
  2. I18: stap 2 (MSO policies) en stap 5 (Seeding en AV1 overlap) raken het beleid van MSO en MediaGuard; de lijst beschrijft alleen de controle (geen torrent verplaatst of verwijderd) en waar de gebruiker die ziet. Stap 4 (Netwerk/VPN binding) noemt geen interface- of adreswaarden.
  3. I19: Seerr blijft via MediaGuard lopen ([DM-MG], regels I19-19-01 tot en met I19-19-06). Stap 5 (Hub/Jellyfin links): geen tweede aanvraagmotor; de lijst zegt dat de Hub aanvragen alleen toont.
  4. I20: stap 5 (Decommission gate) is een besluit van de gebruiker. `uitvoeren_nl` zegt dat Bazarr blijft tot pariteit is aangetoond ([A-09]) en dat het platform Bazarr nooit zelf verwijdert. Stap 3 (Retentietest) vraagt echte media en spelers: `NIET GEVALIDEERD (hardware)`.
  5. EVIDENCE: zeventien regels, status "Geblokkeerd", met de juiste soort per regel.
- **Tests (verplicht):** `make lint && .venv/bin/python -m pytest -q tests/repo/test_checklists.py && make manifesten && make test-repo`. Negatief: (a) een proefkopie van I20 met zes stappen faalt (het document heeft er vijf); (b) `grep -n -i 'verwijder' install/checklists/I20_BAZARR.checklist.yaml` toont geen stap waarin het platform zelf iets verwijdert.
- **Poort:** P-jelly-leon-platform (snel) + P-INSTALLATIE + P-GIT + P-EERLIJK
- **Valkuilen:** V-096, V-097, V-089
- **Bewijs:** I18-18-01...I18-18-06, I19-19-01...I19-19-06 en I20-20-01...I20-20-05 nieuw als "Geblokkeerd" met "NIET GEVALIDEERD (echte NAS): controlelijst geschreven; uitvoeren door de gebruiker (STAPPEN_P6.md onderdeel N-P6-05)". I20-20-03: "NIET GEVALIDEERD (hardware)" erbij.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-MANIFEST (tegelijk; R-MANIFEST VERPLICHT) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** een document een handeling vraagt die tegen een besluit ingaat (bijvoorbeeld Bazarr verwijderen voor pariteit is aangetoond).

### S-P3-440 - Platform: controlelijst I05 (my_house) met de standaard Custom App als weg
- **Repo:** jelly-leon-platform | **Fase:** P3 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** I05-05-01, I05-05-02, I05-05-03, I05-05-04, I05-05-05, I05-05-06, I05-05-07, I05-05-08; raakt B06-009, D12, D13, D14
- **Vooraf:** S-P3-400 klaar; keuze van de gebruiker over de I05-titels (zie bouwpunt 1; geen besluit-ID, de regisseur legt het keuzemenu voor en noteert het antwoord in `<WERKMAP>/.lokaal/plan/uit/VOORTGANG.md`)
- **Al gedaan?** `ls <WERKMAP>/jelly-leon-platform/install/checklists | grep '^I05_'` en STAND `jelly-leon-platform` `I05-05-01` `I05-05-03` -> de lijst en acht EVIDENCE-regels betekent klaar.
- **Lees eerst:** [I-05] (koppen "2. Stappen in uitvoeringsvolgorde" met "Stap 2. Eerste YAML zonder Zigbee/tunnel" en "Stap 3. TrueNAS Install via YAML", en "5. Let op"); `<WERKMAP>/my_house/docs/adr/ADR-0004-alles-in-een-custom-app.md`; [DM-MH], kop "3. Installatie- en bestaande-app-stappen (my_house-kant)"; BESLUITEN, kop "BLOK-13"; STAPPEN_P6.md, kop "N-P6-06 - my_house en echte apparaten"
- **Bouw:**
  1. De keuze. De Excel-taken I05-05-02 ("Eerste YAML zonder Zigbee/tunnel") en I05-05-03 ("TrueNAS Install via YAML") noemen YAML, en de vaste regel verbiedt YAML als installatieweg. Het gereedschap eist de Excel-titel letterlijk. Keuzemenu van de regisseur: (1) titels letterlijk laten staan en in `uitvoeren_nl` de weg via het formulier van de standaard Custom App beschrijven, met `afwijking_van_document_nl` (geen wijziging in het Excel-bestand); (2) de twee Excel-taken en het I05-document laten hernoemen in `ai-server-manager` (een programmawijziging: Excel, `EXCEL_TAKEN.json` in alle kopieen en het document). Zonder antwoord geldt (1): dat verandert niets aan de bron en sluit aan bij wat STAPPEN_P6.md voor N-P6-06 al zegt.
  2. Nieuw `install/checklists/I05_MY_HOUSE.checklist.yaml` (nieuw) met acht stappen, `aanpak: inrichten_en_testen` (my_house draait nog niet als standaard Custom App) of `behouden_en_valideren` als de gebruiker dat bij de keuze zo wil; leg de keuze vast in `toelichting_nl`.
  3. Stap 2 en 3: `uitvoeren_nl` beschrijft het invullen van het formulier van de standaard Custom App volgens het document van my_house (`deploy/truenas/CUSTOM_APP.md` in die repo, gemaakt in S-P3-755) en het wachten op "gezond". `afwijking_van_document_nl`: "Het document noemt YAML. De vaste installatieweg is de standaard Custom App met een alles-in-een image; YAML wordt niet gebruikt." Bestaat het document van S-P3-755 nog niet, dan verwijst de tekst naar de naam van het bestand zonder de inhoud te herhalen.
  4. Stap 5 (HomeWizard rollen): de boiler wordt alleen gemeten; `acceptatie_nl` (letterlijk uit Excel) zegt dat al, `uitvoeren_nl` herhaalt dat er geen schakelhandeling is. Stap 6 (Gree): eerst alleen uitlezen; bedienen alleen bij een unit die in my_house als getest te boek staat (D12). Stap 7 (Zigbee): alleen als D13 dat zegt.
  5. Stap 8 (Android en restore): herstelproef naar een aparte plek, via de webinterface van my_house (S-P3-730); geen opdracht in een terminal.
  6. EVIDENCE: acht regels, status "Geblokkeerd"; I05-05-04 tot en met I05-05-08 met "NIET GEVALIDEERD (hardware)".
- **Tests (verplicht):** `make lint && .venv/bin/python -m pytest -q tests/repo/test_checklists.py && make manifesten && make test-repo`. Negatief: (a) `grep -n -i 'compose\|yaml' install/checklists/I05_MY_HOUSE.checklist.yaml` toont alleen de twee letterlijke Excel-titels en de regels `afwijking_van_document_nl`, geen aanwijzing om YAML te gebruiken; (b) een proefkopie waarin `titel_nl` van stap 2 is "verbeterd" faalt in `tools/checklists.py` (bij keuze 1).
- **Poort:** P-jelly-leon-platform (snel) + P-INSTALLATIE + P-GIT + P-EERLIJK
- **Valkuilen:** V-096, V-097, V-089
- **Bewijs:** I05-05-01...I05-05-08 nieuw als "Geblokkeerd": I05-05-01, -02, -03 met "NIET GEVALIDEERD (echte NAS): controlelijst geschreven; installeren via het formulier door de gebruiker (STAPPEN_P6.md onderdeel N-P6-06)"; I05-05-04...-08 met "NIET GEVALIDEERD (hardware): echte Hue, HomeWizard, Gree, Zigbee en telefoon (N-P6-06)".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-MANIFEST (tegelijk; R-MANIFEST VERPLICHT) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** de gebruiker keuze (2) maakt (dan is het werk in `ai-server-manager` en wacht deze stap tot de nieuwe `EXCEL_TAKEN.json` is overgenomen); het gereedschap de woorden "YAML" in een letterlijke titel als verboden waarde ziet.

### S-P3-450 - Platform: manifestkopieen van MediaGuard, MSO en my_house
- **Repo:** jelly-leon-platform | **Fase:** P3 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** I03-03-04, I04-04-01, I05-05-03 (manifestdeel); raakt C1.3-MGU-09, C1.3-MSO-06, C1.3-MH-06
- **Vooraf:** S-P3-290, S-P3-660 en S-P3-755 gepusht (de drie manifesten bestaan in hun eigen repo)
- **Al gedaan?** `ls <WERKMAP>/jelly-leon-platform/install/manifests | grep -i -E 'mediaguard|media-source|my_house'` -> drie kopieen met een herkomstkop en een groene `make manifesten` betekent klaar. Op 2026-11-11 stonden er alleen kopieen van de Hub en de executor.
- **Lees eerst:** `tools/manifest_kopie.py` (constanten `KOPIE_DIR`, `BRON_REPO`, `BRON_DIR`, `BESTANDEN`, `KOP_RE`; functies `maak_kop`, `controleer_kopie`, `bijwerken`); `tests/repo/test_manifest_kopie.py`; `install/manifests/overgang-1.3.yaml` (secties `kopieen:` en `hiaten:`); `docs/adr/ADR-0021-manifeststandaard-als-kopie.md`; `tools/manifesten.py`
- **Bouw:**
  1. `tools/manifest_kopie.py` kent nu een bronrepo (`lvos04/ai-server-manager`) en twee bestanden. Breid het uit naar een lijst van bronnen: per bron de repo, de map `deploy/manifest` en de bestandsnamen. Voeg toe: `media-guard-ultimate` met `mediaguard.manifest.yaml`, `my_house` met `my_house.manifest.yaml` en `media-source-optimizer` met de naam die S-P3-290 heeft gekozen (vaststellen met `ls <WERKMAP>/media-source-optimizer/deploy/manifest`).
  2. De herkomstkop houdt dezelfde vorm (bron `<repo>@<commit>:<pad>` en sha256). De tekst "I23-manifest" in de kop past niet bij deze drie; maak het woord afhankelijk van de bron of algemeen, en pas `KOP_RE` en de test daarop aan zonder de bestaande twee kopieen te breken.
  3. Haal de drie kopieen op met het uitgebreide gereedschap, uit de gepushte commit van elke bronrepo (`python tools/manifest_kopie.py bijwerken --bron ../<repo> --ref <commit>`; de precieze vlaggen na de uitbreiding: zie `python tools/manifest_kopie.py --help`). Nooit met de hand kopieren.
  4. `install/manifests/overgang-1.3.yaml`, sectie `kopieen:`: neem voor elke kopie precies de waarschuwingen op die de validator nu geeft en die de bronrepo zelf als `accepted_findings` heeft (verwacht: `digest_pending_release`). `tools/manifesten.py` faalt bij elke andere waarschuwing en bij een vermelding die niet optreedt.
  5. Stel vast of `tests/repo/test_installeerbare_manifesten.py` een vaste lijst manifesten kent: `grep -n 'manifest.yaml' tests/repo/test_installeerbare_manifesten.py`. Breid de lijst uit als dat zo is.
  6. Laat de controlelijsten I03, I04 en I05 naar de kopie verwijzen waar een stap "installeren of bijwerken via het formulier" beschrijft (veld `verwijzing`), zonder de inhoud van het manifest te herhalen.
  7. Werk `install/manifests/README.md` bij: drie regels, elk met bron en doel.
- **Tests (verplicht):** `make lint && .venv/bin/python -m pytest -q tests/repo/test_manifest_kopie.py tests/repo/test_installeerbare_manifesten.py && make manifesten && make test-repo`. Negatief: (a) wijzig in een proefkopie een teken in een overgenomen manifest: `python tools/manifest_kopie.py controleer` faalt op de sha256; (b) een kopie zonder herkomstkop faalt; (c) een vermelding in `overgang-1.3.yaml` die de validator niet meer geeft laat `tools/manifesten.py` falen.
- **Poort:** P-jelly-leon-platform (snel) + P-INSTALLATIE + P-CONTRACT + P-GIT + P-EERLIJK
- **Valkuilen:** V-017, V-018, V-016, V-097
- **Bewijs:** geen statuswijziging van de I-regels (blijven "Geblokkeerd"); voeg aan de opmerking van I03-03-04, I04-04-01 en I05-05-03 toe "manifestkopie aanwezig en gevalideerd met de validator (Sim-getest); NIET GEVALIDEERD (echte NAS)".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-MANIFEST (tegelijk; R-MANIFEST VERPLICHT) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** een van de drie manifesten in de eigen repo niet strikt valideert (dan is het werk van die repo, niet van deze stap); de validatorkopie in deze repo ouder is dan de standaard die de manifesten gebruiken (`python tools/validator_kopie.py controleer` faalt).

## Baan appstore-en-fork (register van de bestaande apps)

Werkmap `<WERKMAP>/appstore-en-fork`. Poort: P-appstore-en-fork. Deze baan heeft in P3 een stap. Het register
`apps/api/src/appstore/bestaande_apps/register.yaml` haalt elke tekst letterlijk uit de kopie van de A-documenten in
`docs/platform-v2/04_BESTAANDE_APPS/` van deze repo; de test `apps/api/tests/unit/test_bestaande_apps_register.py`
bewaakt dat. Het register zegt niets over de NAS (geen versies, poorten of paden).

### S-P3-500 - Appstore: register van de bestaande apps laten meebewegen met de A-documenten
- **Repo:** appstore-en-fork | **Fase:** P3 | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** APP-09, APP-10, APP-11, APP-12, APP-13, APP-14, APP-17, APP-18, APP-19, APP-20 (registerdeel; geen statuswijziging); B08-002 (blijft geblokkeerd)
- **Vooraf:** S-P3-180 gepusht (de A-documenten zijn bijgewerkt in `ai-server-manager`)
- **Al gedaan?** `cd <WERKMAP>/appstore-en-fork && python3 tools/contract_kopie.py controleer` en `git -C <WERKMAP>/appstore-en-fork log --oneline -3 -- docs/platform-v2/04_BESTAANDE_APPS` -> de kopie is gelijk aan de commit van S-P3-180 en de registertest is groen: klaar.
- **Lees eerst:** `docs/BESTAANDE_APPS.md`; `docs/adr/ADR-0010-bestaande-apps-import.md`; `apps/api/src/appstore/bestaande_apps/register.yaml` (de items met `excel_id` APP-09 tot en met APP-14 en APP-17 tot en met APP-20); `apps/api/tests/unit/test_bestaande_apps_register.py`; `tools/contract_kopie.py`
- **Bouw:**
  1. Neem de bijgewerkte documenten over met het eigen gereedschap. Het precieze bijwerkcommando: ONBEKEND - eerst vaststellen met: `python3 tools/contract_kopie.py --help` (bekend zijn `controleer` en `vergelijk --online ... --bron ../ai-server-manager`). Nooit met de hand kopieren; `docs/platform-v2/CONTRACT_HERKOMST.json` wordt door het gereedschap bijgewerkt.
  2. Draai de registertest. Faalt een tekst omdat het A-document is aangepast, pas dan het veld in `register.yaml` aan zodat het weer letterlijk gelijk is aan het document. Verzin geen nieuwe tekst en wijzig geen `voorgenomen_besluit.code`.
  3. Verhoog `register_versie` volgens het patroon in het bestand (datum en volgnummer).
  4. Controleer dat het register nog steeds niets over de NAS zegt en dat het item MediaGuard geen versie belooft die er niet is.
  5. Zijn de A-documenten in S-P3-180 niet veranderd op een plek die het register aanhaalt, dan is deze stap alleen de kopie plus een groene test.
- **Tests (verplicht):** `make lint && make typecheck`, daarna `cd apps/api && PATH=/usr/lib/postgresql/16/bin:$PATH nice -n 10 ../../.venv/bin/python -m pytest -q -n 4 tests/unit`, daarna `python3 tools/contract_kopie.py controleer`. Negatief: wijzig in een proefkopie buiten de repo een woord in een registertekst en bevestig dat de registertest faalt (de test moet kunnen falen).
- **Poort:** P-appstore-en-fork (snel) + P-CONTRACT + P-GIT + P-EERLIJK
- **Valkuilen:** V-003, V-017, V-018
- **Bewijs:** APP-09...APP-14 en APP-17...APP-20 blijven "Geblokkeerd" met hun bestaande tekst ("NIET GEVALIDEERD (echte NAS)": inventaris en besluit van de gebruiker, STAPPEN_P6.md onderdeel N-P6-05). B08-002 blijft "Geblokkeerd".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW N2 (kleine mechanische stap); verder standaard
- **Stop en vraag als:** de kopie meer bestanden wijzigt dan de A-documenten (dan is de bron verder veranderd dan S-P3-180; eerst nagaan wat); de contractversie in de bron niet meer 1.3 is.
