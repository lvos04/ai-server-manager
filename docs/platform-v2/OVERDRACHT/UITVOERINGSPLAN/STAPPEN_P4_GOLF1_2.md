# STAPPEN_P4_GOLF1_2 - Fase P4 deel 1: afronding P4-0, golf 1 en golf 2 van B03 (universele mediaserver)

Dit bestand is een deel van het uitvoeringsplan. Het is geschreven voor de regisseur (hoofdsessie) die zelf niet bouwt
en elke stap uitbesteedt aan een subagent. Een subagent weet alleen wat in zijn opdracht staat: plak daarom bij elke
opdracht het blok "Opdrachtkop" (hoofdstuk 4) boven de stap. Het vervolg (golf 3 en golf 4) staat in
`<WERKMAP>/.lokaal/plan/uit/STAPPEN_P4_GOLF3_4.md`; dat bestand verwijst naar "Gate P4-0", "Gate golf 1", "B03-018",
"B03-009" en "WT-1-gate (B03-021)" uit dit bestand.

**Stand bij het schrijven (2026-11-11; een andere ronde bouwt nog, de stand verschuift):**

| Repo | Laatste commit gezien | Wat er staat | Wat ontbreekt |
|---|---|---|---|
| jelly-leon | `cc3e82b4d` (gepusht; dezelfde vastlegging heette eerder lokaal `02d6e55f3`) | fork op v12.4 (`tools/jelly-leon/baseline.json`), overnametool `tools/emby-overname`, harnas `tools/b03-harnas`, plugin met `Core/` (Api, Connector, Errors, Http, Hub, Idempotency, Media, MediaGuard, Modules, Outbox, Privacy, Secrets, Storage) en de prototypemodules `Modules/Devices` en `Modules/Quality`; de analyzer, de generator voor `config.json`, de pluginproef (`tools/jelly-leon/e2e/plugin_proef.py`), de IStartupFilter-spike (commit `cdb6dc3bf`) en de MediaGuard-viewerclient zonder vervoer (commit `cc3e82b4d`); ADR-0028 (contract 1.3) en ADR-0029 tot en met ADR-0034 vastgelegd. **HALF WERK (niet vastgelegd, ronde 3 afgebroken):** gewijzigd `Core/Api/BeheerController.cs`, `Core/Http/RouteTable.cs`, `PluginServiceRegistrator.cs` en `tests/.../Hulp/OpenApiBouwer.cs` (route `GET /media/v1/planner`); nieuw `Core/Budget/BudgetBeslisser.cs`, `Core/Planner/` (BatchPlanner.cs, CgroupMarge.cs, ISessieBron.cs, LeesfoutBreker.cs, PlannerRegels.cs) en `Core/Werker/IWerker.cs`; de code verwijst naar een "ADR-0035" die nog niet bestaat; geen tests voor planner en budget. Reservekopie: `<WERKMAP>/.lokaal/halfwerk/jelly-leon.patch` en `jelly-leon-nieuw.tgz` | Geen EVIDENCE-regel voor B03-017, B03-018, B03-009, B03-010, JLT-65, JLT-66, JLT-68; `C1.3-JL-06` tot en met `C1.3-JL-09` staan op "Niet gestart". Geen review van de vastleggingen van contract 1.3 (`e38d33f1d` tot en met `945eb8113`) en van golf 1 (`8a293727d` tot en met `cc3e82b4d`); CI van golf 1 niet beoordeeld. Let op de naam: de map heet `Core/Werker` (niet `Worker`); de analyzer-regel JL0004 staat processtarts alleen toe in de namespace `Core.Werker` (ADR-0032) |
| jelly-leon-web | `4ea95f2f0` | web-fork op v12.4, contract 1.3 verwerkt | de map `src/jelly-leon/` bestaat niet (wel gereserveerd in `tools/jelly-leon-web/fork_paths.txt`); geen haakmodule |
| jelly-leon-clients | `309b178` | compat-harnas `tools/clients/compat`, hervatproef | tablet-emulator staat op Sim-mislukt; B03-003, I24-24-05 en JLT-69 Geblokkeerd |
| media-guard-ultimate | `1dcf318` | Δ-MG-DUAL en Δ-MG-AUTH gebouwd, contracttest `tests/contract/mediaserver/` (commit `2a6dc1c`), documenten en bewijs vastgelegd (commit `1dcf318`) | de contracttest is nog niet tegen de Jelly Leon-image gedraaid; de technische review van Δ-MG-AUTH en Δ-MG-DUAL en het upgradebewijs zijn werk van `<WERKMAP>/.lokaal/plan/uit/STAPPEN_P2.md` (S-P2-600, S-P2-610); het niet-vastgelegde ontwerpherstel in `apps/web/` en `apps/android/` hoort bij S-P2-590 (niet aankomen vanuit dit bestand: zie V-016) |
| jelly-leon-platform | `35fc44d` | lifecycle en manifest (I10); controlelijsten I01 en I02 in `install/checklists/` | half werk van de P2-review (ADR-0022, ADR-0024) hoort bij STAPPEN_P2.md (S-P2-400 tot en met S-P2-420); daarna in dit bestand de controlelijsten I06, I22 en I24 (S-G2-70, S-G2-72) |

Elke stap heeft daarom een controle "Al gedaan?". Vindt die controle meer dan hier beschreven, dan bouwt de subagent
voort op wat er staat en gooit hij niets weg.

## 1. Doel

1. **P4-0 afronden.** De 12.x-basis staat (B03-014) en de overnametool vanuit Emby bestaat (B03-015), maar de gate is
   niet dicht: Δ-MG-AUTH en Δ-MG-DUAL moeten bewezen en geboekt worden, JLT-70 en JLT-73 staan op Sim-getest in plaats
   van Sim-geslaagd, de definitieve baselines (B03-016) ontbreken, en JLT-61 onderdeel (b), JLT-62 en JLT-67 zijn niet
   haalbaar of niet gestart. Ook de voormetingen van golf 0 (B03-020, B03-030, B03-060, B03-070) hebben geen bewijs.
2. **Golf 1: de gemeenschappelijke basis.** Een plugin `Jellyfin.Plugin.JellyLeon` met modules, connector, outbox,
   foutcatalogus en Hub-koppeling JL4 (B03-017); analysewerker, globale batchplanner en budgetbeslisser (B03-018);
   MediaGuard-viewerclient via de Hub (B03-009); het privacydeel van B03-010; haakmodule in de webclient; manifest.
   Dit is een afmaak- en controleplan: een deel van B03-017 staat er al.
3. **Golf 2: de eerste functiemodules.** Watch Together-kern (B03-021), aanbevelingen (B03-031 t/m B03-035),
   apparaatwaarneming en GPU-assistent (B03-061, B03-062) met de spikes F5-S2, segmenten (B03-071, B03-072, B03-073) en
   het begin van de aanvulling op B03-007.
4. **Installatie I06, I22, I24:** het manifest van Jelly Leon (I24, repo jelly-leon: S-G1-70 en S-G2-55) en de
   controlelijsten voor de gebruiker in jelly-leon-platform (I06 en I24: S-G2-70; I22 Navidrome alleen na besluit
   D18: S-G2-72). Alleen het deel dat op de ontwikkelmachine kan. Alles wat de NAS vraagt krijgt een bewijsregel
   "Geblokkeerd" en hoort in `<WERKMAP>/.lokaal/plan/uit/STAPPEN_P6.md` (N-P6-08 voor I22; de I06- en I24-rijen bij
   de cutover).
5. **Eerst opruimen wat ronde 3 heeft laten liggen:** het half werk van B03-018 in jelly-leon (S-G1-15, ketenvorm C),
   de ontbrekende review van contract 1.3 in jelly-leon (S-P2-800 in `<WERKMAP>/.lokaal/plan/uit/STAPPEN_P2.md`, ketenvorm B; niet in dit bestand) en de ontbrekende review van de
   gepushte golf-1-vastleggingen `8a293727d` tot en met `cc3e82b4d` (S-G1-17, ketenvorm B). Ketenvormen:
   `<WERKMAP>/.lokaal/plan/uit/AGENTEN.md#2.4 De vier ketenvormen`.

Niet in dit bestand: golf 3 en 4 (STAPPEN_P4_GOLF3_4.md), P5, en alle NAS-rijen (JLT-06, JLT-15, JLT-49, JLT-59,
JLT-69, JLT-74). De rest van B03-010 (authenticatie op streamroutes) is golf 3 (daar S-G3-09 en S-G3-10).

Bron: `<WERKMAP>/ai-server-manager/docs/platform-v2/02_BOUWPLANNEN/B03_FASERING.md#3. Golven en werkpakketten`.

## 2. Gates

**Ervoor:** Gate P3 volgens `<WERKMAP>/ai-server-manager/docs/platform-v2/01_ARCHITECTUUR/06_FASERING_EN_GATES.md#Gate matrix`
geldt voor Hub-kaarten, niet voor het werk in dit bestand: P4-0, golf 1 en golf 2 raken ai-server-manager alleen voor
Excel en STATUS. De stappen S-P40-xx mogen direct beginnen. Golf 1 begint na Gate P4-0 (S-P40-95), behalve de stappen
waar in hoofdstuk 6 "mag voor Gate P4-0" staat (controle- en afmaakwerk aan code die er al ligt). Golf 2 begint na
Gate golf 1 (S-G1-90).

**De drie gates van dit bestand:**

| Gate | Inhoud (letterlijk uit de bron samengevat) | Stap | Sim-haalbaar op de ontwikkelmachine? |
|---|---|---|---|
| Gate P4-0 | B03-014 en B03-015 Sim-getest; JLT-70 t/m JLT-73 Sim-geslaagd; JLT-60, JLT-61 (a en b), JLT-62, JLT-64 Sim-geslaagd; JLT-63 rooktestdeel en JLT-67 Sim-geslaagd; `JL_RUNTIME_IMAGE` op de 12.x-digest; `UPSTREAM_GEDRAG.md` met werkende CI-runner; Δ-MG-AUTH en Δ-MG-DUAL met contracttest; BG-01 vastgelegd; voorlopige manifestresources 4 CPU's en 4096 MiB; baselines opnieuw op de 12.x-digest | S-P40-95 | Ja, behalve: JLT-61 (b) en JLT-67 vragen een 12.y-tag van upstream die op 2026-11-10 niet bestond; JLT-62 geldt alleen als D07 een Jellyfin meet (de gebruiker gebruikt Emby). Zie "Drie open gate-eisen" hieronder |
| Gate golf 1 | ADR-B03-02 aanvaard en prototype met twee modules bewezen (laadt op fork en stock; elke `/connector/v1`-route een keer); JLT-68 Sim-geslaagd; JLT-64 en JLT-65 Sim-geslaagd met Core + prototype; foutcatalogus-contracttest, analyzer en UserDeleted-test groen; geheimen niet in XML, export of log; werker met smoketest en SBOM, zonder auditok, torch of ctranslate2; groei van de image binnen de ADR-grens (ADR-0017); planner: pauze binnen 5 s, hooguit 2 threads en 1 GiB batch; JLT-66 Sim-geslaagd of batchmodules blijven op de NAS uit (BG-07) | S-G1-90 | Ja. JLT-66 gebruikt de iGPU van de ontwikkelmachine (`/dev/dri/renderD128`): opmerking "Intel-iGPU-getest (ontwikkelmachine)"; A310 en UHD 770 blijven NIET GEVALIDEERD (hardware) |
| Gates golf 2 | WT-1-gate (B03-021: decorator of core-patch-besluit), G-F2-1 t/m G-F2-5 (B03-031 t/m B03-035), F5-S1 en F5-S3 (B03-061, B03-062; JLT-43), F6-S1 t/m F6-S3 (B03-071, 072, 073; JLT-56 a-f, g, i; JLT-52; JLT-53 audiodeel; JLT-51 nultolerantie); JLT-63, JLT-64, JLT-65 zonder regressie | S-G2-90 | Ja, met beperkingen: JLT-43 alleen op de iGPU (D08 open: NAS-deel in JLT-49); M1-claim van aanbevelingen alleen met D-ML (anders "functioneel aangetoond (synthetisch)"); Pioneer One-labels bevestigd of dat deel Geblokkeerd |

Bronnen: `<WERKMAP>/ai-server-manager/docs/platform-v2/02_BOUWPLANNEN/B03_FASERING.md#Gate P4-0 (vóór elk B03-modulewerk)`,
`...B03_FASERING.md#Gate golf 1 (vóór elk functiewerk in P4)`, `...B03_FASERING.md#Gates per functie` en
`<WERKMAP>/ai-server-manager/docs/platform-v2/01_ARCHITECTUUR/06_FASERING_EN_GATES.md#Fase P4-0 — Jellyfin 12.x als basis`.

**Drie open gate-eisen van Gate P4-0 (de regisseur legt ze in S-P40-95 aan de gebruiker voor; niemand past de gate zelf aan):**

1. **JLT-61 onderdeel (b)** staat op Sim-mislukt: de negatieve proef "alleen de vorige image op de gemigreerde
   database" faalt niet zichtbaar met de stock-image 10.11.11; de jelly-leon-image weigert vanaf 12.4.0-jl.0 wel
   zichtbaar. Een echte herhaling vraagt een 12.y-image. Bron: `<WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json`,
   object JLT-61.
2. **JLT-67** (upstream-sync-proef 12.x naar 12.y) is niet gestart: er was geen 12.y-tag. Stap S-P40-45 voert beide
   uit zodra die tag bestaat.
3. **JLT-62** (overname van een bestaande Jellyfin-installatie) is niet gestart: het Jellyfin-deel van B03-015 geldt
   alleen als D07 een Jellyfin meet. De gate noemt JLT-62 zonder die voorwaarde.

**No-go Gate P4-0:** een verschil in het per-gebruikerrapport zonder uitdrukkelijk akkoord van de gebruiker (HARDE
EIS); terugzetten niet bewezen; een schrijfactie naar Emby; stock-clients breken; `EnableLegacyAuthorization` weer aan
zonder besluit; B03-batch op de NAS zonder Δ-MG-AUTH.
**No-go Gate golf 1:** dubbele routes; een gedeelde singleton die per module verschilt; OOM in de belastingtest.
**No-go P4 (algemeen):** upstream-clients breken; HDR/DV-verlies; media muteren buiten MediaGuard; Jellyfin direct
verwijderen; een afspeelstart van een stock-client weigeren of verlagen; schrijven in kijkgeschiedenis buiten het
besluit BG-21 en de eenmalige overname van B03-015; Emby uitzetten of verwijderen voor de controlelijst "Emby
verwijderen"; B03-batch op de A310 terwijl MediaGuard daar encodeert; een winstclaim zonder baseline of op een
niet-bevroren testset. Bron: `<WERKMAP>/ai-server-manager/docs/platform-v2/01_ARCHITECTUUR/06_FASERING_EN_GATES.md#Fase P4-0 — Jellyfin 12.x als basis`
en `#Fase P4 — Universele mediaplatform`. Bij een no-go stopt de regisseur en meldt hij het aan de gebruiker.

**Zonder Δ-MG-AUTH** mag P4 op de ontwikkelmachine verder met een MediaGuard-simulator, maar draait er geen B03-batch
op de NAS en toont Jelly Leon `mediaguard: onbekend`. Een test tegen een simulator heet nooit een MediaGuard-validatie.

## 3. Besluiten die eerst genomen moeten zijn

Alleen de regisseur vraagt de gebruiker, via een keuzemenu. Een subagent die een besluit mist, stopt en meldt het. De
uitgeschreven keuzemenu's staan in `<WERKMAP>/.lokaal/plan/uit/BESLUITEN_EN_BLOKKADES.md` (koppen "2.1 NU", "2.2 Na
golf 1", "2.3 Start golf 2"). Bron van de besluiten:
`<WERKMAP>/ai-server-manager/docs/platform-v2/02_BOUWPLANNEN/B03_BESLUITEN.md#Overzicht`.

| Besluit | Gaat over | Stand | Nodig voor stap | Zonder besluit |
|---|---|---|---|---|
| BG-01 | MediaGuard-koppeling na de upgrade | genomen: Δ-MG-AUTH, legacy-auth blijft uit | S-P40-20, S-P40-95 | n.v.t. |
| BG-02 | Geen release op 10.11.11; P4-0 eigen fase | genomen | S-P40-95 | n.v.t. |
| BG-03 | Wat is een kinderprofiel | **open; nu voorleggen** | S-G1-18 (en later S-G2-26) | de ruimste regel: iedere gebruiker met leeftijdsgrens, geblokkeerde tags of toegangsschema telt als kind (zo staat het in `Core/Privacy/KidPolicy.cs`); de stap mag daarmee doorgaan |
| BG-04 | Waar staat de MediaGuard-sleutel | genomen: **via de Hub** (2026-11-10) | S-G1-50 | n.v.t.; zie "Spanning BG-04" |
| BG-07 | Resources van de jelly-leon-app | open; pas na JLT-66 | na S-G1-40, voor S-G1-90 | strikt na elkaar binnen 4 CPU's en 4 GiB; batchmodules op de NAS standaard uit |
| BG-22 | Bazarr-vertaler en ondertiteldownloaders van Jellyfin | **open; nu voorleggen** | S-P40-80 (tekst in de assistent) | geen ondertiteldownloaders van Jellyfin installeren; Bazarr-vertaler niet voor Nederlands |
| BG-32 | Intro Skipper en bestaande segmenten | genomen: alleen testbaseline; bestaande segmenten eenmalig als hint | S-P40-66, S-G2-40 | n.v.t. |
| BG-34 | Wie labelt echte afleveringen | genomen: de gebruiker of een aangewezen persoon | S-P40-66 | Pioneer One-deel Geblokkeerd tot de labels bevestigd zijn |
| BG-37 | Testdata met beperkende licentie | genomen: MovieLens en Pioneer One alleen lokaal | S-P40-62, S-P40-66, S-G2-22 | n.v.t. |
| BG-38 | Rechten op de ontwikkelmachine | genomen: `transcode` in de groepen render en kvm | S-P40-70 | emulator alleen in een container met `--device /dev/kvm` |
| BG-16 | Kijkgedrag van gezinsleden; fijnere kijklog | open; start golf 2 | S-G2-26 | kijkgedrag van gezinsleden telt nooit mee; fijnere kijklog uit |
| BG-27 | A310 voor live kijken terwijl MediaGuard encodeert; meten | open; start golf 2 | S-G2-32 | A310 niet voor live kijken; geen meting die MediaGuard raakt |
| BG-33 | Wie corrigeert tijdcodes; schaduwmodus | open; start golf 2 | S-G2-40 | alleen beheerders; nieuwe segmenten blijven in schaduwmodus |
| BG-35 | Hardware-decode voor de beeldanalyse | open; start golf 2 | S-G2-44 | alleen CPU |
| BG-36 | Module uit: eigen segmenten wissen of verbergen | open; start golf 2 | S-G2-40 | STOP voor dat onderdeel: het gedrag bij "module uit" wordt niet gebouwd tot het besluit er is |
| Z-19 | "Module uit": 404 of 501 | genomen (2026-11-11): **404 zoals ADR-0030**; de afwijking van WP-JSON B03-033 en B03-035 (501) staat in het bewijs | S-G2-24, S-G2-28 | n.v.t. |
| Z-20 | B03-002, B03-003, B03-006, B03-008, B03-011, B03-012 (staan in geen golf) | genomen (2026-11-11): **in P4 bouwen**; per werkpakket eerst A-VERKEN, dan stappen in een golf | geen stap in dit bestand: de stappen komen in `<WERKMAP>/.lokaal/plan/uit/STAPPEN_P4_GOLF3_4.md` (zie hoofdstuk 10.1 van dit bestand). De afhankelijkheden die WP-JSON B03-016, B03-019, B03-020 (naar B03-003), B03-032 (naar B03-006) en B03-072 (naar B03-002/B03-006) noemen, zijn zacht: geen wachtpunt; wat later aansluit staat in "Vooraf" van S-P40-40, S-P40-50, S-P40-60, S-G2-22 en S-G2-42 | n.v.t. |
| D18 | Navidrome als aparte muziekserver (I22) | open (BESLUITEN_EN_BLOKKADES.md, kop "D18 — Navidrome (optioneel)") | S-G2-72 | Navidrome wordt niet geinstalleerd; S-G2-72 start niet; de I22-rijen blijven "Niet gestart" met de reden |
| D07 | Welke mediaserver draait er echt (Emby; ook Jellyfin?) | open (NAS-meting door de gebruiker) | S-G2-70 (I06), S-P40-95 (JLT-62) | I06 beschrijft alleen de Jellyfin-weg "als D07 een Jellyfin meet"; JLT-62 blijft "Niet gestart" met die reden |

**Spanning BG-04 (melden, niet zelf oplossen):** BG-04 is genomen: de MediaGuard-sleutel van Jelly Leon loopt via de
Hub; bij voorkeur zonder sleuteloverdracht (Jelly Leon vraagt de MediaGuard-gegevens via de Hub met een dienst-JWT).
Bron: `...B03_BESLUITEN.md#Besluiten van de gebruiker na contract 1.3 (2026-11-10)`. De overzichtstabel in datzelfde
bestand en de tekst van werkpakket B03-009 spreken nog van een sleutel "in Jelly Leon zelf". Het besluit van
2026-11-10 gaat voor. Geen enkele stap in dit bestand voegt een sleutelveld voor MediaGuard toe aan een beheerpagina
of schrijft een MediaGuard-sleutel in de geheimenmap van Jelly Leon.

**Keuzes die geen BG-nummer hebben en die de regisseur toch moet voorleggen (elk met de stap waar het speelt):**

- Gate P4-0 aanvaarden met de drie open gate-eisen uit hoofdstuk 2 (S-P40-95).
- Telt de voormeting tegen stock 12.4 als definitieve baseline als de digest van de forkbasis gelijk is (S-P40-50).
- De runtime van de overname-assistent: de image heeft geen Python tot de analysewerker er is (S-P40-80).

---

## 4. Opdrachtkop (de regisseur plakt dit blok boven elke stap in de opdracht)

De stappen in hoofdstuk 8 gebruiken de afkortingen en de testlabels (T-...) uit dit blok. Een subagent krijgt dit
blok plus precies een stap. De commando's van een hele poort staan in `<WERKMAP>/.lokaal/plan/uit/POORTEN.md`
(blok P-<repo>); dit blok noemt alleen de labels waar de stappen naar verwijzen.

```
VASTE REGELS
- Taal: Nederlands. Je stelt geen vragen aan de gebruiker; heb je een besluit nodig, stop dan en meld het.
- Je start zelf geen subagents. Je werkt alleen in de repo die bij "Repo" staat. Raak ai-factory nooit aan.
- Git: altijd "git pull --rebase" voor elke push; nooit force-push; Nederlandse commitberichten; geen pull requests.
  Elke commit eindigt met de regel: Co-Authored-By: Claude <noreply@anthropic.com>
  Voeg bestanden bij naam toe, nooit "git add -A" (er kan een build lopen die tijdelijke bestanden schrijft).
- Geen geheimen, geen IP-adressen, geen NAS-gegevens en geen modelnaam of model-ID in code, docs of commits.
- HARDE EIS: kijkgeschiedenis (gezien, hervatpunten, favorieten, beoordelingen, spoorkeuzes, gebruikers) en de
  voortgang van MediaGuard blijven altijd beschikbaar; Emby blijft werken en wordt nooit onderbroken. De gebruiker
  verwijdert Emby zelf; geen stap in dit bestand schrijft in Emby of zet Emby uit.
- Installatie is altijd een standaard TrueNAS Custom App (een alles-in-een image per repo); nooit YAML of compose.
- Bewijs: schrijf nooit "Gereed" of "Geslaagd". Gebouwd en met simulator getest = status "Bezig" (validatie
  Sim-getest of Sim-geslaagd). Alles wat een echte NAS, hardware of accounts vraagt = status "Geblokkeerd" met de
  letterlijke tekst "NIET GEVALIDEERD (...)" en wat er nog nodig is. Een meting op de Arc-iGPU van de
  ontwikkelmachine krijgt in de opmerking de tekst "Intel-iGPU-getest (ontwikkelmachine)"; dat is geen NAS-bewijs.
- Zware commando's (image-build, Gradle, emulator, container met een echte Jellyfin- of Emby-server, tijdmeting)
  alleen achter het lock dat in de stap staat. Nooit "docker system prune -a", "docker builder prune -a" of
  "docker volume prune". Gebruik "nice -n 10". Volgorde bij twee locks: eerst stack.lock, dan gradle.lock.
  Emulator, Gradle en een zware transcode draaien nooit tegelijk.
- Half werk van een vorige ronde: lees eerst "Al gedaan?" in de stap. Gooi niets weg wat je niet zelf hebt gemaakt;
  meld het in je rapport.

AFKORTINGEN
- BOUWPLAN  = <WERKMAP>/ai-server-manager/docs/platform-v2/02_BOUWPLANNEN/B03_UNIVERSELE_MEDIASERVER.md
- FASERING  = <WERKMAP>/ai-server-manager/docs/platform-v2/02_BOUWPLANNEN/B03_FASERING.md
- BESLUITEN = <WERKMAP>/ai-server-manager/docs/platform-v2/02_BOUWPLANNEN/B03_BESLUITEN.md
- WP-JSON   = <WERKMAP>/ai-server-manager/docs/platform-v2/08_EXCEL/b03/werkpakketten.json
              (lijst van objecten; zoek het object met "ID"; lees Taak, Uitvoering, Acceptatie, Afhankelijkheid)
- TEST-JSON = <WERKMAP>/ai-server-manager/docs/platform-v2/08_EXCEL/b03/testen.json
              (lijst van rijen [ID, titel, opzet, verwacht])
- PLUGIN    = <WERKMAP>/jelly-leon/plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon
- PLUGINTEST= <WERKMAP>/jelly-leon/plugins/JellyLeon/tests/Jellyfin.Plugin.JellyLeon.Tests
- HARNAS    = <WERKMAP>/jelly-leon/tools/b03-harnas (python-pakket b03h, map playwright, map profielen)
- OVERNAME  = <WERKMAP>/jelly-leon/tools/emby-overname (pakket emby_overname, map e2e met proefrun.py)
- EVIDENCE  = <WERKMAP>/<repo>/docs/platform-v2/EVIDENCE.json (lijst van objecten met "id") en EXCEL_TAKEN.json
- $PY       = tools/jelly-leon/.venv/bin/python (in de repo jelly-leon)
- Koppen in "Lees eerst" en "Bron" worden met hun begin aangehaald (bijvoorbeeld "#10.6 Analysewerker").

TESTLABELS (alle paden vanuit de werkmap van de repo; de volledige poort staat in POORTEN.md)
- T-JL-PLUGIN   : flock <WERKMAP>/.lokaal/docker-build.lock <WERKMAP>/.lokaal/jl-dotnet.sh build plugins/JellyLeon.Plugins.sln -c Release
                  flock <WERKMAP>/.lokaal/docker-build.lock <WERKMAP>/.lokaal/jl-dotnet.sh test plugins/JellyLeon.Plugins.sln -c Release --no-build --verbosity minimal
                  (een deel: voeg --filter "FullyQualifiedName~<Naam>" toe)
- T-JL-REGISTER : $PY tools/jelly-leon/check_fork_consistency.py ; $PY tools/jelly-leon/patch_register_check.py ;
                  $PY tools/jelly-leon/upstream_gedrag_check.py --overzicht
- T-JL-TOOLS    : $PY -m pytest -q tools/jelly-leon/tests
- T-JL-HARNAS   : tools/jelly-leon/.venv/bin/ruff check --config tools/b03-harnas/ruff.toml tools/b03-harnas ;
                  PYTHONPATH=tools/b03-harnas $PY -m pytest -q tools/b03-harnas/tests ;
                  PYTHONPATH=tools/b03-harnas $PY -m b03h guard --git .
- T-JL-OVERNAME : tools/jelly-leon/.venv/bin/ruff check --config tools/emby-overname/ruff.toml tools/emby-overname ;
                  $PY -m pytest -q tools/emby-overname/tests ;
                  flock <WERKMAP>/.lokaal/stack.lock nice -n 10 $PY tools/emby-overname/e2e/proefrun.py --modus synthetisch
                    --ffmpeg docker --browser chromium --uitvoer <map buiten de repo>
- T-JL-IMAGE    : de image bouwen en proeven zoals P-jelly-leon "4. Volledig", job image (bouwen achter
                  docker-build.lock, proeven achter stack.lock: image_lifecycle.py, b03h guard --image,
                  rollback_sim.py, upgrade_proef.py)
- T-JL-COMPAT   : P-jelly-leon "4. Volledig", job image en job b03-harnas: compat_api.py, upstream_gedrag_runtime.py,
                  PYTHONPATH=tools/b03-harnas $PY -m b03h diffrun --uit <rapport.json> en
                  ... diffrun --negatieve-proef --uit <rapport.json> (het harnas neemt stack.lock zelf)
- T-JLW-STATISCH: python tools/jelly-leon-web/check_fork_consistency.py ; python tools/jelly-leon-web/patch_register_check.py ;
                  python tools/jelly-leon-web/upstream_gedrag_check.py --overzicht ;
                  python -m pytest -q -c tools/jelly-leon-web/pytest.ini tools/jelly-leon-web/tests
- T-JLW-NPM     : npm run lint ; npm run stylelint ; npm run build:check ; npm run test ; npm run build:production ; npm run escheck
- T-JLW-E2E     : P-jelly-leon-web "4. Volledig": tools/jelly-leon-web/e2e/web_smoke.py in modus fork en modus stock
                  (achter stack.lock)
- T-JLC-STATISCH: make test ; make check ; make lint
- T-JLC-COMPAT  : make compat-android JL_IMAGE=<image> ; make compat-desktop JL_IMAGE=<image> DESKTOP_BUILD=<map> ;
                  python3 tools/clients/client_compat.py hervatproef (lees eerst --help)
                  (compat-android en compat-desktop nemen de locks zelf: zet er GEEN flock voor)
- T-MGU-KERN    : cd apps/core && ../../.venv/bin/ruff check . && ../../.venv/bin/python -m pytest -q -p no:cacheprovider <testbestand>
- T-MGU-CONTRACT: flock <WERKMAP>/.lokaal/stack.lock nice -n 10 tests/contract/mediaserver/run.sh
                  (omgevingsvariabelen staan bovenin run.sh; lees ze voor je start)
- T-MGU-UPGRADE : P-media-guard-ultimate "4. Volledig" punt 3 (upgradebewijs; achter docker-build.lock)
```

**Niet vastgesteld en daarom door A-VERKEN eerst op te zoeken (elk met het commando):**

- Waarde van `STOCK_IMAGE` en `JL_RUNTIME_IMAGE`: ONBEKEND - eerst vaststellen met:
  `grep -n "STOCK_IMAGE:\|JL_RUNTIME_IMAGE:" <WERKMAP>/jelly-leon/.github/workflows/jelly-leon-ci.yml`
- De opties van elk hulpscript dat een stap noemt zonder opties: ONBEKEND - eerst vaststellen met:
  `$PY <script> --help` (bijvoorbeeld `PYTHONPATH=tools/b03-harnas $PY -m b03h baseline --help`).
- De inhoud van de mappen `Core/Werker`, `Core/Planner` en `Core/Budget` onder PLUGIN (bij de overdracht half werk
  van ronde 3, vastgelegd door S-G1-15) en van `Core/MediaGuard`: eerst vaststellen met:
  `ls -R <PLUGIN>/Core | head -200` en `git -C <WERKMAP>/jelly-leon status --short`
- Het eerstvolgende vrije ADR-nummer in jelly-leon (bij het schrijven was ADR-0034 het hoogste; een andere ronde
  kan intussen nummers hebben gebruikt): ONBEKEND - eerst vaststellen met:
  `ls <WERKMAP>/jelly-leon/docs/adr | sort | tail -5`
- Een simulator van de Hub voor Jelly Leon staat in `tools/jelly-leon/e2e/hub_sim.py`; een simulator van MediaGuard
  staat alleen in `tools/emby-overname/e2e/mediaguard_sim.py`. Wat ze dekken: ONBEKEND - eerst vaststellen met:
  `grep -n "def \|route\|path" tools/jelly-leon/e2e/hub_sim.py tools/emby-overname/e2e/mediaguard_sim.py | head -80`

## 5. Ketens en niveaus in dit bestand

- **Standaardketen:** A-VERKEN (N2) -> A-BOUW (N3) -> R-TECH (N3) -> A-HERSTEL (N3, alleen bij bevindingen) ->
  R-EERLIJK (N3). Bij moeilijkheid "hoog" werken A-BOUW en A-HERSTEL op N4.
- **VERPLICHT erbij (mag niet worden overgeslagen):**
  - R-VEILIG (N4) bij authenticatie, geheimen, sleutels, rechten, privacy en alles wat van buiten bereikbaar is;
  - R-HARDE-EIS (N4) bij migraties, kijkgeschiedenis, gebruikers, de Emby-koppeling en de voortgang van MediaGuard;
  - R-MANIFEST (N3) bij het manifest, `CUSTOM_APP.md`, de Dockerfile en de inhoud van de image.
- **Ontwerp:** jelly-leon-web, de pluginpagina's van Jelly Leon en de clients vallen buiten Peil. In dit bestand
  staat daarom nergens A-ONTWERP of R-ONTWERP. Waar een stap een scherm raakt, staat erbij "buiten Peil" en geldt
  de vormgeving van upstream. (De ontwerpreview van het mediaserver-tabblad van MediaGuard, wel Peil, is S-P2-590 in
  STAPPEN_P2.md.)
- **Het topmodel (N5) staat op drie plaatsen, elk met de reden in de stap zelf (drie van de 58 stappen; golf 2 heeft geen N5):**
  1. R-HARDE-EIS in S-P40-82 (startpunt van de echte overname van kijkgeschiedenis en gebruikers);
  2. R-VEILIG in S-G1-12 (de authenticatiekern van de Hub-koppeling);
  3. A-GATE in S-P40-95 (einde van de fase P4-0).
  De migratie op de database van MediaGuard (Δ-MG-AUTH, Δ-MG-DUAL) krijgt het topmodel in STAPPEN_P2.md (S-P2-610),
  niet hier. De gates van golf 1 en golf 2 (S-G1-90, S-G2-90) zijn golfgates en draaien op N4. Geen stap in dit
  bestand heeft moeilijkheid "zeer hoog". Elke andere inzet van het topmodel is een escalatie en hoort in de tabel
  "Topmodel-inzet" van de regisseur (`<WERKMAP>/.lokaal/plan/uit/AGENTEN.md#7.7 De tabel "Topmodel-inzet"`).
- **Korte keten** mag alleen waar de stap het zegt en de reden noemt (een stap die alleen leest of alleen bewijs
  boekt).
- **Vangnet geheugen:** voor een zware stap `free -m` lezen; onder 3000 MB vrij start de stap niet en meldt de
  subagent dat. Een zware stap van een andere baan wacht op het lock; dat is geen fout (V-009).
- **Uitval van een subagent:** de regisseur leest `git -C <WERKMAP>/<repo> status --short` en
  `git -C <WERKMAP>/<repo> log --oneline @{u}..` en start de stap opnieuw bij "Al gedaan?".

## 6. Volgorde en banen

Een baan is een repo: nooit twee schrijvende agents in dezelfde repo. Binnen een baan lopen de stappen in de volgorde
van de tabel. Banen lopen naast elkaar. "Zwaar: ja" betekent dat de stap een lock neemt (image-build, Gradle,
emulator, grote .NET-build of containers met een echte Emby- of Jellyfin-server); zware stappen van verschillende
banen wachten op elkaar via de locks in `<WERKMAP>/.lokaal/`.

### 6.1 Afronding P4-0

| Stap | Baan (repo) | Vooraf | Zwaar | Kan tegelijk met |
|---|---|---|---|---|
| S-P40-10 Stand P4-0 vaststellen | geen (alleen lezen in vier repos) | geen | nee | niets: eerst deze stap |
| S-P40-20 MediaGuard: aanmelden per server en twee mediaservers bewijzen met de Jelly Leon-image | media-guard-ultimate | S-P40-10; BG-01; S-P2-600 en S-P2-610 (STAPPEN_P2.md); S-G1-16 voor het deel met de Jelly Leon-image | ja | alle stappen van andere banen |
| S-G1-15 Half werk B03-018 uit ronde 3 overnemen (vorm C; EERSTE schrijver in jelly-leon) | jelly-leon | S-P40-10 | ja | S-P40-20, S-P40-72, S-G1-60; lezers van S-P2-800 en S-G1-17 |
| S-G1-17 Review van de golf-1-vastleggingen (vorm B) | jelly-leon | S-G1-15; S-P2-800 (STAPPEN_P2.md; A-HERSTEL pas daarna) | nee | reviewers van S-P2-800; andere banen |
| S-G1-16 Stand B03-017 vastzetten: werkboom schoon, poort groen, lokale image bewaren | jelly-leon | S-P40-10, S-G1-15, S-P2-800 (STAPPEN_P2.md), S-G1-17 | ja | S-P40-20, S-P40-72 |
| S-P40-40 Register upstream-gedrag en clientmatrix aanvullen | jelly-leon | S-G1-16 | ja | S-P40-20, S-P40-72 |
| S-P40-30 JLT-73 opnieuw met de echte MediaGuard-kandidaat | jelly-leon | S-P40-20, S-G1-16 | ja | S-P40-72 |
| S-P40-32 Clientdeel JLT-70 koppelen aan de proefrun | jelly-leon | S-P40-30 | ja | S-P40-72 |
| S-P40-90 Desktop-spike in het harnas bijwerken | jelly-leon | S-P40-40 | ja | S-P40-70 (locks) |
| S-P40-50 Definitieve baselines en controle-run | jelly-leon | S-P40-90; keuze "voormeting telt" | ja | niets wat stack.lock neemt (meetslot) |
| S-P40-60 Voormeting Watch Together (B03-020) | jelly-leon | S-P40-50 | ja | stappen zonder stack.lock |
| S-P40-62 Voormeting aanbevelingen (B03-030) | jelly-leon | S-P40-50; BG-37 | ja | stappen zonder stack.lock |
| S-P40-64 Voormeting apparaten en fouten (B03-060) | jelly-leon | S-P40-50 | ja | stappen zonder stack.lock |
| S-P40-66 Meetlat segmenten (B03-070) | jelly-leon | S-P40-50; BG-32, BG-34, BG-37 | ja | stappen zonder stack.lock |
| S-P40-92 Bewijs uit de andere repos overnemen in jelly-leon (JLT-60, JLT-70, clientmatrix) | jelly-leon | S-P40-70, S-P40-20, S-P40-50 | nee | alle stappen van andere banen |
| S-P40-80 Overname-assistent: ontwerp en ADR | jelly-leon | S-P40-30; BG-22; keuze runtime | nee | alle stappen van andere banen |
| S-P40-72 Compat-harnas veiliger maken | jelly-leon-clients | S-P40-10 | ja | alle stappen van de baan jelly-leon (locks) |
| S-P40-70 Tablet-emulator en emulatordeel JLT-60, JLT-63, JLT-70 | jelly-leon-clients | S-P40-72; S-P40-32 voor het JLT-70-deel; BG-38 | ja | stappen zonder stack.lock |
| S-P40-45 Sync-proef en upgradeproef met een 12.y-tag (voorwaardelijk) | jelly-leon | er bestaat een 12.y-tag van upstream; S-P40-40 | ja | stappen van andere banen |
| S-P40-95 Gate P4-0 | geen (A-GATE, alleen lezen) | alle stappen hierboven behalve S-P40-45 als de tag ontbreekt; S-P40-80 hoeft niet klaar te zijn | nee | S-G1-10, S-G1-12 |

### 6.2 Golf 1

| Stap | Baan (repo) | Vooraf | Zwaar | Kan tegelijk met |
|---|---|---|---|---|
| S-G1-15, S-G1-17 en S-G1-16 (zie 6.1; mogen voor Gate P4-0) | jelly-leon | zie 6.1 | zie 6.1 | zie 6.1 |
| S-G1-10 Kern B03-017 controleren: prototype op fork en stock, JLT-68, JLT-64 en JLT-65 (mag voor Gate P4-0) | jelly-leon | S-G1-16; de P4-0-stappen van de baan jelly-leon | ja | S-P40-95, S-G1-60 |
| S-G1-12 Hub-koppeling JL4: beveiligingsreview en herstel (mag voor Gate P4-0) | jelly-leon | S-G1-10 | nee | S-P40-95, S-G1-60 |
| S-G1-14 Foutcatalogus, 1 MiB per route, IStartupFilter-spike, health en events | jelly-leon | S-G1-12; Gate P4-0 | nee | S-G1-60 |
| S-G1-18 Privacy: persoonsgegevensregister, UserDeleted, kinderprofiel | jelly-leon | S-G1-14; BG-03 (of de terugval) | nee | S-G1-60 |
| S-G1-20 Geheimenmap, mountcontrole, wezenbreker, spoorsleutel, export en import | jelly-leon | S-G1-18 | nee | S-G1-60 |
| S-G1-30 Analysewerker in de image | jelly-leon | S-G1-20 | ja | S-G1-60 (lock) |
| S-G1-32 Werkerbewaker en socket | jelly-leon | S-G1-30 | ja | S-G1-60 (lock) |
| S-G1-34 Bestandspas en featurecache | jelly-leon | S-G1-32 | ja | S-G1-60 (lock) |
| S-G1-36 Globale batchplanner | jelly-leon | S-G1-34 | ja | S-G1-60 (lock) |
| S-G1-50 MediaGuard-viewerclient via de Hub (B03-009) | jelly-leon | S-G1-36; S-G1-12; BG-04 | ja | S-G1-60 (lock) |
| S-G1-38 Budgetbeslisser G1 t/m G10 | jelly-leon | S-G1-50 | nee | S-G1-60 |
| S-G1-40 Gecombineerde belastingtest JLT-66 | jelly-leon | S-G1-38 | ja | niets wat stack.lock neemt (meting) |
| S-P40-82 Overname-assistent bouwen | jelly-leon | S-P40-80; S-G1-30 als de keuze "interpreter van de werker" is; S-G1-20 | ja | S-G1-60 (lock) |
| S-G1-60 Haakmodule in de webclient | jelly-leon-web | S-P40-10 (mag voor Gate P4-0) | ja | alle stappen van de baan jelly-leon (locks) |
| S-G1-70 Manifest, CUSTOM_APP en web-verwijzing bijwerken | jelly-leon | S-P40-82, S-G1-60, S-G1-40 | ja | geen |
| S-G1-80 Eindrun golf 1: JLT-64, JLT-65, JLT-68 | jelly-leon | S-G1-70 | ja | geen |
| S-G1-90 Gate golf 1 | geen (A-GATE, alleen lezen) | S-G1-80; BG-07 voorgelegd | nee | geen |

### 6.3 Golf 2

| Stap | Baan (repo) | Vooraf | Zwaar | Kan tegelijk met |
|---|---|---|---|---|
| S-G2-10 Watch Together-kern WT-1 (B03-021) | jelly-leon | Gate golf 1; S-P40-60 | ja | banen web en clients |
| S-G2-20 Moduleskelet aanbevelingen (B03-031) | jelly-leon | S-G2-10; S-P40-62 | ja | banen web en clients |
| S-G2-22 Klassieke aanbevelingsengine (B03-032) | jelly-leon | S-G2-20; BG-37 | ja | banen web en clients |
| S-G2-24 Opslag en terug naar stock (B03-033) | jelly-leon | S-G2-22 | ja | banen web en clients |
| S-G2-26 Profielen en toegang (B03-034) | jelly-leon | S-G2-24; BG-16, BG-03 (of de terugval) | nee | banen web en clients |
| S-G2-28 API en OpenAPI aanbevelingen (B03-035) | jelly-leon | S-G2-26 | nee | banen web en clients |
| S-G2-30 Module Devices: waarnemen (B03-061) | jelly-leon | S-G2-28; S-P40-64 | ja | banen web en clients |
| S-G2-32 GPU-assistent (B03-062) | jelly-leon | S-G2-30; BG-27 (of de terugval) | ja | geen emulator of Gradle tegelijk |
| S-G2-34 Spikes F5-S2 server: actionfilter en fdinfo | jelly-leon | S-G2-30 | ja | banen web en clients |
| S-G2-35 Spikes F5-S2 harnas: dynamic-range en stilte-orakel | jelly-leon | S-G2-34 | ja | baan clients (lock) |
| S-G2-36 Spike F5-S2 web: stall-detectie zonder extra haak | jelly-leon-web | S-G1-60; Gate golf 1 | ja | baan jelly-leon (lock) |
| S-G2-38 Spike F5-S2 clients: rolherkenning officiele Android-app | jelly-leon-clients | Gate golf 1; S-P40-70 | ja | baan jelly-leon (locks) |
| S-G2-40 Module Segments: provider en opslag (B03-071) | jelly-leon | Gate golf 1; S-P40-66; BG-33, BG-36, BG-32 (zie de stap) | ja | banen web en clients |
| S-G2-42 Audio-engine segmenten (B03-072) | jelly-leon | S-G2-40; S-G1-34 | ja | banen web en clients |
| S-G2-44 Beeldanalyse en veiligheid (B03-073) | jelly-leon | S-G2-42; BG-35 (of de terugval) | ja | geen emulator of Gradle tegelijk |
| S-G2-46 Hoofdstuksegmenten en hervatproef op de emulators | jelly-leon-clients | S-G2-40; S-G2-38 | ja | baan jelly-leon (locks) |
| S-G2-50 Terug naar stock en begin aanvulling B03-007 (JLT-63, JLT-64, JLT-65) | jelly-leon | S-G2-44, S-G2-28, S-G2-32 | ja | geen |
| S-G2-55 Manifest en image na golf 2 | jelly-leon | S-G2-50 | ja | geen |
| S-G2-70 Controlelijsten I06 en I24 (jelly-leon-platform) | jelly-leon-platform | S-P2-420 (STAPPEN_P2.md); S-G1-70; D07 voor het Jellyfin-deel van I06 (anders de terugval uit hoofdstuk 3) | nee | alle banen |
| S-G2-72 Controlelijst I22 Navidrome (alleen na D18 "ja") | jelly-leon-platform | S-G2-70; besluit D18 | nee | alle banen |
| S-G2-90 Gate golf 2 | geen (A-GATE, alleen lezen) | S-G2-55, S-G2-46, S-G2-36, S-G2-38, S-G2-70 (S-G2-72 alleen als D18 "ja" is) | nee | geen |

**Volgorde binnen de baan jelly-leon in golf 2:** de tabel geeft een werkbare volgorde, maar alleen de regels "Vooraf"
in de stappen zelf zijn echte afhankelijkheden. Echte ketens: F1 = S-G2-10; F2 = S-G2-20 -> 22 -> 24 -> 26 -> 28;
F5 = S-G2-30 -> 32 en S-G2-30 -> 34 -> 35; F6 = S-G2-40 -> 42 -> 44 (S-G2-40 hangt alleen af van Gate golf 1,
S-P40-66 en de besluiten; S-G2-42 bovendien van de bestandspas uit S-G1-34). De regisseur mag F1, F2, F5 en F6 in een andere volgorde door de baan laten gaan, bijvoorbeeld
F6 eerst als BG-33, BG-35 en BG-36 al genomen zijn en F2 nog op BG-16 wacht. Er loopt altijd maar een schrijvende
keten in jelly-leon. S-G2-50 en S-G2-55 komen als laatste.

De spike F5-S2 (a), de lanewrapper, staat in `<WERKMAP>/.lokaal/plan/uit/STAPPEN_P4_GOLF3_4.md` als S-G4-01 en wordt
hier niet gebouwd.

## 7. Startbezetting

- **Grenzen:** hooguit 10 subagents tegelijk en hooguit 8 open bouwketens; een schrijver per repo
  (`<WERKMAP>/.lokaal/plan/uit/AGENTEN.md#3. Bezetting`).
- **Eerlijk beeld:** bijna al het werk van dit bestand zit in een repo, jelly-leon. Die baan is de flessenhals: er
  loopt daar steeds een bouwketen. In de praktijk lopen er drie of vier ketens tegelijk, niet acht.
- **Start (na S-P40-10):**
  1. baan media-guard-ultimate: S-P40-20 (keten met R-VEILIG en R-HARDE-EIS);
  2. baan jelly-leon: eerst S-G1-15 (half werk; tot die stap klaar is staat het halve werk geparkeerd, vorm D),
     daarna S-P2-800 (STAPPEN_P2.md: review contract 1.3) en S-G1-17 (hun reviewers mogen al lezen terwijl S-G1-15 loopt; hun A-HERSTEL schrijft na
     elkaar), dan S-G1-16 en de rij uit 6.1;
  3. baan jelly-leon-clients: S-P40-72;
  4. baan jelly-leon-web: S-G1-60 (mag voor Gate P4-0: nieuwe map, raakt de server niet);
  5. een A-VERKEN loopt vooruit op de eerstvolgende stap van de baan jelly-leon (S-P40-40) en schrijft alvast het
     dossier; A-VERKEN wijzigt niets.
  Dat zijn vier ketens en een verkenner: ruim binnen de grenzen. De overige ruimte blijft vrij voor reviewers die
  tegelijk lopen (R-TECH met R-VEILIG of R-HARDE-EIS).
- **Zware stappen:** bijna elke stap in de baan jelly-leon is zwaar. De locks regelen de volgorde; de regisseur
  start geen twee zware stappen bewust tegelijk als een van beide een meting is (S-P40-50, S-G1-40, S-G2-32).
- **Repos zonder werk in dit bestand:** home-control-hub, appstore-en-fork, zoeken-en-persoonlijke-ai,
  media-source-optimizer en my_house. jelly-leon-platform krijgt pas in golf 2 werk (S-G2-70, S-G2-72; mag naar
  voren zodra S-P2-420 en S-G1-70 klaar zijn, want het raakt jelly-leon niet). Die banen zijn vrij voor ander werk van de
  regisseur. ai-server-manager krijgt alleen aan het einde van een gate werk: Excel (P-EXCEL, door de regisseur),
  STATUS en het vastleggen van besluiten (via A-BOUW in ai-server-manager, zie "Fase-afsluiting").
- **Wachten op de gebruiker blokkeert niet alles:** BG-03 en BG-22 hebben een terugval (hoofdstuk 3); alleen BG-36
  stopt een onderdeel (S-G2-40).

## 8. Stappen

**Vaste afspraken voor elke stap (gelden naast de Opdrachtkop):**

- "Al gedaan?" is altijd een commando dat alleen leest. Is de verwachting al waar, dan bouwt A-BOUW niets en gaat
  de keten door met de reviewers op wat er staat.
- "Poort" verwijst naar een blok in `<WERKMAP>/.lokaal/plan/uit/POORTEN.md`. P-GIT geldt bij elke stap die iets
  vastlegt; P-EERLIJK bij elke stap die EVIDENCE raakt. Na elke push: POORTEN.md "0.5 CI-controle na elke push".
- "Bewijs" noemt EVIDENCE-ID's in `<WERKMAP>/<repo>/docs/platform-v2/EVIDENCE.json`. Bestaat een ID daar nog niet,
  dan voegt A-BOUW het toe in dezelfde vorm als de bestaande objecten en ook in `EXCEL_TAKEN.json`.
- Valkuilen (V-nnn) staan in `<WERKMAP>/.lokaal/plan/uit/VALKUILEN.md`.
- De ketenmap van een stap is `<WERKMAP>/.lokaal/ketens/<STAP-ID>/`; daar staan het dossier en de rapporten. Niets
  uit de ketenmap komt in een repo.

### 8.1 Afronding P4-0

### S-P40-10 - Stand P4-0 vaststellen (dossier voor de gate)
- **Repo:** geen wijziging; leest in jelly-leon, jelly-leon-web, jelly-leon-clients en media-guard-ultimate | **Fase:** P4-0 | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** B03-014, B03-015, B03-016, B03-019, JLT-60, JLT-61, JLT-62, JLT-63, JLT-64, JLT-67, JLT-70, JLT-71, JLT-72, JLT-73 (alleen de stand vaststellen; geen EVIDENCE-wijziging)
- **Vooraf:** geen
- **Al gedaan?** `ls <WERKMAP>/.lokaal/ketens/S-P40-10/DOSSIER.md` -> bestaat het dossier en is het van dezelfde dag als de laatste commits (`git -C <WERKMAP>/jelly-leon log -1 --format=%cd`), dan is de stap klaar. Is het ouder dan de laatste commit van een van de vier repos: opnieuw doen (de stand verschuift; een andere ronde bouwt nog).
- **Lees eerst:** `<WERKMAP>/ai-server-manager/docs/platform-v2/02_BOUWPLANNEN/B03_FASERING.md#Gate P4-0`; `<WERKMAP>/jelly-leon/docs/platform-v2/BOUWVERIFICATIE_P4-0.md#10. Wat niet gehaald`; `<WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json`; `<WERKMAP>/media-guard-ultimate/tests/contract/mediaserver/RESULTS.md`; hoofdstuk 2 van dit bestand
- **Bouw:**
  1. Lees per repo `git -C <WERKMAP>/<repo> status --short` en `git -C <WERKMAP>/<repo> log --oneline -8`. Noteer niet vastgelegd werk met bestandsnaam. Bron: `<WERKMAP>/.lokaal/plan/uit/AGENTEN.md#6. Als het misgaat`.
  2. Lees per repo de EVIDENCE-rijen met: `python3 -c "import json;[print(o['id'],'|',o['status'],'|',o['validatie']) for o in json.load(open('docs/platform-v2/EVIDENCE.json')) if o['id'].startswith(('B03','JLT','I06','I24','C1.3'))]"` (vanuit de werkmap van de repo). Zet de uitkomst in het dossier.
  3. Stel vast op welke image de CI draait: `grep -n "JL_RUNTIME_IMAGE:\|STOCK_IMAGE:" <WERKMAP>/jelly-leon/.github/workflows/jelly-leon-ci.yml <WERKMAP>/jelly-leon/.github/workflows/upstream-sync.yml`. Verwachting: beide op dezelfde 12.x-digest. Bron: B03-014 in WP-JSON, veld Acceptatie.
  4. Stel vast of upstream een nieuwere 12.x-tag heeft dan de forkbasis: `cat <WERKMAP>/jelly-leon/tools/jelly-leon/baseline.json` (veld `upstream_tag`) en `cd <WERKMAP>/jelly-leon && $PY tools/jelly-leon/upstream_sync.py kies` (leest alleen tags). Is er een nieuwere tag, dan mag S-P40-45 starten; noteer de tag.
  5. Loop de gate-eisen uit hoofdstuk 2 een voor een af en schrijf per eis: bewezen (met bestand of EVIDENCE-ID), open (met de stap uit dit bestand die het sluit) of niet haalbaar (met reden). Verzin geen stand: wat je niet kunt lezen is "ONBEKEND".
  6. Schrijf het dossier naar `<WERKMAP>/.lokaal/ketens/S-P40-10/DOSSIER.md` met een lijst "klaar", een lijst "open -> stap" en een lijst "afwijkingen van dit plan" (bijvoorbeeld een stap waarvan "Al gedaan?" al waar is).
- **Tests (verplicht):** geen build. Controle: `python3 -m json.tool <WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json > /dev/null` (leesbaar) per repo. Negatieve controle: zoek in de vier EVIDENCE-bestanden naar verboden statussen: `grep -n '"status": "Gereed"\|"status": "Geslaagd"' <WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json <WERKMAP>/jelly-leon-web/docs/platform-v2/EVIDENCE.json <WERKMAP>/jelly-leon-clients/docs/platform-v2/EVIDENCE.json <WERKMAP>/media-guard-ultimate/docs/platform-v2/EVIDENCE.json` -> verwachting: geen treffer; een treffer is een bevinding voor de regisseur.
- **Poort:** geen P-<repo> (er wordt niets gewijzigd); P-EERLIJK op het dossier
- **Valkuilen:** V-015 (half werk van een afgebroken ronde); V-017 (werk dat in een andere repo nog niet gepusht is); V-104 (verouderde tekst in bewijs)
- **Bewijs:** geen EVIDENCE-wijziging. Het dossier noemt letterlijk wat op de NAS wacht: "NIET GEVALIDEERD (echte NAS): echte overname (JLT-74), echte datamap (JLT-60), echte Emby van de gebruiker (D07)".
- **Agents:** A-VERKEN -> R-EERLIJK. Korte keten: de stap leest alleen en wijzigt geen repo.
- **Niveau:** standaard (A-VERKEN N2, R-EERLIJK N3)
- **Stop en vraag als:** een repo niet vastgelegd werk bevat dat niet bij B03-017 of bij een stap van dit bestand hoort; een EVIDENCE-rij "Gereed" of "Geslaagd" toont; de CI op een andere digest draait dan `baseline.json` aangeeft.

### S-P40-20 - MediaGuard: aanmelden per server en twee mediaservers bewijzen met de Jelly Leon-image
- **Repo:** media-guard-ultimate | **Fase:** P4-0 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (echte Emby- en Jellyfin-containers, image-build van de kandidaat)
- **Werkpakketten en tests:** B03-014, B03-015, JLT-73 (het MediaGuard-deel); contract-ID C1.3-MGU-04 en C1.3-MGU-03; deltaverzoeken Δ-MG-AUTH en Δ-MG-DUAL
- **Vooraf:** S-P40-10 klaar; BG-01 genomen; S-P2-600 en S-P2-610 uit `<WERKMAP>/.lokaal/plan/uit/STAPPEN_P2.md` klaar (daar worden de code van Δ-MG-AUTH en Δ-MG-DUAL, migratie 150 en het upgradebewijs gereviewd, met R-HARDE-EIS op het topmodel; deze stap herhaalt die review niet). Voor bouwpunt 4: een lokale Jelly Leon-image van de werkbranch (gebouwd in S-G1-16 met T-JL-IMAGE).
- **Al gedaan?** `git -C <WERKMAP>/media-guard-ultimate status --short` (verwachting: leeg) en `grep -n "jelly-leon" <WERKMAP>/media-guard-ultimate/tests/contract/mediaserver/RESULTS.md` -> staat daar een run met een jelly-leon-image als Jellyfin-server en staat in EVIDENCE bij `B03-014` niet meer "Contracttest tegen een jelly-leon:12.x-image: niet gedraaid", dan is alleen R-EERLIJK nog nodig. Half werk in `apps/web/` of `apps/android/` hoort bij S-P2-590 (STAPPEN_P2.md): niet aankomen; staat het er bij de start nog, stop en meld het (V-016).
- **Lees eerst:** `<WERKMAP>/media-guard-ultimate/docs/adr/ADR-0022-meerdere-mediaservers-en-aanmelden-per-server.md`; `<WERKMAP>/media-guard-ultimate/tests/contract/mediaserver/RESULTS.md#Wat er getest is`; `<WERKMAP>/media-guard-ultimate/docs/platform-v2/B03_DELTAVERZOEKEN.md`; BOUWPLAN `#18. Deltaverzoeken aan andere repos`; `<WERKMAP>/.lokaal/plan/uit/POORTEN.md#P-media-guard-ultimate`
- **Bouw:**
  1. Lees de code van de twee delta's zonder iets te wijzigen: `apps/core/mediaguard/mediaserver/` (api.py, clients.py, servers.py, service.py) en `apps/core/mediaguard/migrations/150_mediaserver_servers.sql`. Leg in het dossier vast: welke kop per servertype wordt gestuurd (Emby: `X-Emby-Token`; Jelly Leon 12.x: `Authorization: MediaBrowser Token=...`), en dat de bestaande Emby-koppeling "server 1" blijft zonder handeling van de beheerder. Bron: BOUWPLAN `#18. Deltaverzoeken aan andere repos`, rijen Δ-MG-AUTH en Δ-MG-DUAL.
  2. Draai T-MGU-KERN op `tests/test_mediaserver_dual.py` en op `tests/test_upgradebewijs.py` (bestanden onder `apps/core/tests/`) als controle dat de code sinds S-P2-610 niet is veranderd.
  3. Draai T-MGU-UPGRADE (upgradebewijs van de vorige release naar de kandidaat) alleen als `git -C <WERKMAP>/media-guard-ultimate log --oneline <commit van S-P2-610>..HEAD -- apps/core` iets toont; anders verwijs je naar het bewijs van S-P2-610. Verplichte uitkomst staat in POORTEN.md: exitcode 0 en in het rapport zowel "Upgrade: niets verloren" als "terugzetten: niets verloren". Bewaar de gebouwde kandidaat (`mediaguard/upgrade-kandidaat:lokaal`) voor bouwpunt 4.
  4. Draai de contracttest eerst met de stock-server (referentie) en daarna met de Jelly Leon-image als Jellyfin-server, met dezelfde kandidaat: `MGMS_KANDIDAAT=mediaguard/upgrade-kandidaat:lokaal MGMS_BEWIJS=<map buiten de repo>/stock flock <WERKMAP>/.lokaal/stack.lock nice -n 10 tests/contract/mediaserver/run.sh` en `MGMS_KANDIDAAT=mediaguard/upgrade-kandidaat:lokaal JELLYFIN_IMAGE=<jelly-leon:lokaal-... uit S-G1-16> MGMS_BEWIJS=<map buiten de repo>/jelly-leon flock <WERKMAP>/.lokaal/stack.lock nice -n 10 tests/contract/mediaserver/run.sh` (de variabelen staan in het kopcommentaar van `run.sh`). Vergelijk de twee runs per test (`test_a...` en `test_b...`); elk verschil krijgt een verklaring of is een bevinding. Stel eerst vast of de test een image met een andere startwijze aankan: ONBEKEND - eerst vaststellen met: `grep -n "JELLYFIN_IMAGE\|jellyfin" tests/contract/mediaserver/docker-compose.yml tests/contract/mediaserver/test_mediaserver_contract.py | head -40`. Past de image niet zonder wijziging, pas dan alleen de testopstelling aan (niet de productcode) en leg uit waarom.
  5. Werk `tests/contract/mediaserver/RESULTS.md` bij: datum, images op digest of lokale tag met commit, wat geslaagd is, wat niet bewezen is (sessies zijn nagebootst met de sessie-API, geen echte spelers).
  6. Werk EVIDENCE bij (zie "Bewijs") en leg vast met P-GIT.
- **Tests (verplicht):** bouwpunten 2, 3 en 4. Negatieve tests die in de contracttest moeten zitten en moeten slagen (controleer dat ze bestaan met `grep -n "def test_" tests/contract/mediaserver/test_mediaserver_contract.py`): (a) valt de Jelly Leon-server weg, dan blijft de kijkpauze voor Emby werken en blijft de Emby-koppeling staan; (b) de kandidaat stuurt Emby geen verzoek dat de vorige release niet stuurde (proxylog); (c) een Jelly Leon-server met een verkeerde sleutel geeft status "onbekend", geen "gezond". Ontbreekt een van de drie: toevoegen.
- **Poort:** P-media-guard-ultimate (Snel voor `apps/core`; Volledig punt 1, 2 en 3) + P-HARDE-EIS + P-VEILIG + P-GIT
- **Valkuilen:** V-116 (upgradebewijs meldt "niets verloren" over een lege meting); V-117 (vergelijkt met de verkeerde vorige release); V-099 (een eigen simulator is geen bewijs); V-094 (sleutel in een verzoeklog: het proxylog mag alleen een vingerafdruk bevatten); V-009
- **Bewijs:** in `<WERKMAP>/media-guard-ultimate/docs/platform-v2/EVIDENCE.json`: `C1.3-MGU-04`, `B03-014`, `B03-015` en `JLT-73` -> "Bezig", validatie "Sim-getest" (JLT-73: "Sim-geslaagd" alleen voor het MediaGuard-deel en alleen als bouwpunt 4 slaagt). Blokkade letterlijk: "NIET GEVALIDEERD (echte NAS): de echte Emby van de gebruiker, de uitgebrachte Jelly Leon-image en echte spelers; kijksessies zijn nagebootst met de sessie-API." De NAS-proef hoort in `<WERKMAP>/.lokaal/plan/uit/STAPPEN_P6.md`.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG (VERPLICHT) + R-HARDE-EIS (VERPLICHT) (tegelijk) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** R-VEILIG N4; R-HARDE-EIS N4 (geen topmodel: de migratie en het upgradepad zijn al met het topmodel gereviewd in S-P2-610; deze stap draait alleen de contracttest met een andere serverimage).
- **Stop en vraag als:** het upgradebewijs een verschil meldt; de contracttest een verzoek naar Emby toont dat de vorige release niet deed; de Jelly Leon-image alleen werkt als `EnableLegacyAuthorization` aan staat (no-go Gate P4-0); een wijziging in productcode van MediaGuard nodig blijkt die het datamodel raakt.

### S-P40-30 - JLT-73 afmaken: overnameproef tegen de Jelly Leon-image met het bewijs van de echte MediaGuard
- **Repo:** jelly-leon | **Fase:** P4-0 | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** ja (echte Emby-container en Jelly Leon-container)
- **Werkpakketten en tests:** B03-015, JLT-71, JLT-72, JLT-73; contract-ID C1.3-JL-05
- **Vooraf:** S-P40-20 klaar (contracttest met de Jelly Leon-image gedraaid); S-G1-16 klaar (schone werkboom, lokale image)
- **Al gedaan?** `python3 -c "import json;[print(o['id'],o['validatie'],'|',o['opmerking'][:200]) for o in json.load(open('<WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json')) if o['id']=='JLT-73']"` -> staat er "Sim-geslaagd" en noemt de opmerking de contracttest van media-guard-ultimate met commit, dan is de stap klaar. Staat er nog "Het MediaGuard-deel draait alleen tegen een eigen simulator", dan is de stap open.
- **Lees eerst:** TEST-JSON rij JLT-73; `<WERKMAP>/jelly-leon/docs/platform-v2/BOUWVERIFICATIE_P4-0.md#8. Overname uit Emby herhaald`; `<WERKMAP>/media-guard-ultimate/tests/contract/mediaserver/RESULTS.md`; `<WERKMAP>/jelly-leon/tools/emby-overname/README.md`; BOUWPLAN `#10.9.1 Overname vanuit Emby`
- **Bouw:**
  1. Draai T-JL-OVERNAME met `--jellyfin-image <lokale jelly-leon-image>` erbij (de optie staat in `tools/emby-overname/e2e/proefrun.py`; lees eerst `$PY tools/emby-overname/e2e/proefrun.py --help`). Bewaar het rapport buiten de repo en kopieer alleen het samenvattende JSON-bewijs naar `docs/platform-v2/test-evidence/` met een naam die de datum en de image noemt.
  2. Controleer in het rapport de vier harde punten van JLT-73: 0 verzoeken anders dan GET in de proxylog; de opzettelijke POST en DELETE (testhaak) geweigerd voor het netwerk; de Emby-sleutel in geen log, rapport of export; kijkgegevens in Emby per gebruiker voor en na gelijk. Bron: TEST-JSON rij JLT-73, kolom verwacht.
  3. Neem het MediaGuard-deel niet over van de eigen simulator: verwijs in EVIDENCE naar de contracttest van media-guard-ultimate (bestand RESULTS.md, datum, commit, gebruikte Jelly Leon-image). Staat daar geen run met een Jelly Leon-image, dan blijft JLT-73 op "Sim-getest" en meldt de stap dat.
  4. Werk `docs/platform-v2/BOUWVERIFICATIE_P4-0.md` bij onder de kop "8. Overname uit Emby herhaald": wat nu met de echte MediaGuard-kandidaat is aangetoond en wat nagebootst blijft (kijksessies via de sessie-API).
  5. Werk EVIDENCE en `EXCEL_TAKEN.json` bij en leg vast met P-GIT.
- **Tests (verplicht):** T-JL-OVERNAME (ruff, unit-tests, proefrun). Negatieve test: in het proefrun-bewijs moet de controle "verkeerd doel" aanwezig en geslaagd zijn (de tool weigert te schrijven als het doeladres Emby is; exitcode 9). Controle: `grep -n "verkeerd\|exitcode\|JLT-73" <rapport.json> | head`.
- **Poort:** P-jelly-leon (Snel voor `tools/emby-overname`; Volledig stap 8) + P-HARDE-EIS + P-VEILIG + P-EERLIJK + P-GIT
- **Valkuilen:** V-109 (de tool had per vergissing in Emby kunnen schrijven); V-110 (een leesverzoek laat Emby schrijven: geen PlaybackInfo op niet-geanalyseerde bestanden); V-111 (de proef verandert zelf de kijkgegevens); V-098; V-099; V-127
- **Bewijs:** `JLT-73` -> "Bezig", validatie "Sim-geslaagd" alleen als bouwpunt 2 en 3 beide gedekt zijn, anders "Sim-getest"; `JLT-71`, `JLT-72`, `B03-015`, `C1.3-JL-05` -> "Bezig". Blokkade letterlijk: "NIET GEVALIDEERD (echte NAS): de echte Emby van de gebruiker (D07) is niet gebruikt; echte overname in JLT-74."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-HARDE-EIS (VERPLICHT) + R-VEILIG (VERPLICHT: het bewijs dat in de repo komt mag de Emby-sleutel niet bevatten) (tegelijk) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard; R-HARDE-EIS N4, R-VEILIG N4 (geen N5: de stap wijzigt geen overnamecode, alleen proef en bewijs)
- **Stop en vraag als:** de proxylog een verzoek anders dan GET toont; de kijkgegevens in Emby voor en na verschillen; de proefrun tegen de Jelly Leon-image andere aantallen geeft dan tegen stock 12.4.

### S-P40-32 - Clientdeel JLT-70 voorbereiden: de proefrun laat een overdracht voor het clientharnas achter
- **Repo:** jelly-leon | **Fase:** P4-0 | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** ja (proefrun met echte Emby- en Jelly Leon-container)
- **Werkpakketten en tests:** B03-015, JLT-70
- **Vooraf:** S-P40-30 klaar
- **Al gedaan?** `grep -n "clientproef\|overdracht" <WERKMAP>/jelly-leon/tools/emby-overname/e2e/proefrun.py | head` -> is er een optie die na de proefrun de Jelly Leon-datamap en een overdrachtsbestand bewaart en staat die in `--help`, dan is de stap klaar. Half werk: afmaken, niet opnieuw beginnen.
- **Lees eerst:** TEST-JSON rij JLT-70; `<WERKMAP>/jelly-leon/tools/emby-overname/e2e/proefrun.py` (functie rond `--behoud`); `<WERKMAP>/jelly-leon/docs/platform-v2/OVERNAME_EMBY.md#Stappen`; `<WERKMAP>/jelly-leon-clients/tools/clients/client_compat.py` (subcommando `android`, optie `--migratie-van`); `<WERKMAP>/jelly-leon/docs/platform-v2/BOUWVERIFICATIE_B03-015.md`
- **Bouw:**
  1. Stel vast wat ontbreekt. JLT-70 eist dat na de overname "stock-web en de Android-emulator" inloggen en hervatten op het overgenomen punt. Het webdeel draait al in de proefrun (`--browser chromium`); het emulatordeel niet. Het clientharnas start zelf een server uit een image en kan nu geen bestaande datamap gebruiken (vastgesteld in `client_compat.py --help`). Bron: TEST-JSON rij JLT-70.
  2. Voeg aan `proefrun.py` een optie toe die na een geslaagde run (a) de Jelly Leon-configuratiemap en de testmedia in de uitvoermap laat staan en (b) een overdrachtsbestand schrijft (voorstel: `clientproef.json`) met: de image, het pad van de datamap en van de media, per testgebruiker de naam en een wegwerpwachtwoord dat alleen voor deze proef is gezet, en per gebruiker een item met het verwachte hervatpunt in ticks. De naam van de optie kiest A-BOUW; hij moet in `--help` staan.
  3. Het overdrachtsbestand bevat nooit de Emby-sleutel, nooit een Jelly Leon-beheerdersleutel en nooit een wachtwoord dat buiten de proef bestaat. Schrijf het met rechten 0600 en alleen in de uitvoermap buiten de repo.
  4. Voeg unit-tests toe in `tools/emby-overname/tests/` die het schema van het overdrachtsbestand vastleggen en controleren dat er geen sleutelveld in staat.
  5. Beschrijf de overdracht kort in `tools/emby-overname/README.md` en verwijs ernaar vanuit `docs/platform-v2/BOUWVERIFICATIE_B03-015.md`.
  6. Leg vast met P-GIT. De emulatorrun zelf is S-P40-70 (repo jelly-leon-clients).
- **Tests (verplicht):** T-JL-OVERNAME, de proefrun met de nieuwe optie. Negatieve test (unit): een overdracht waarin een veld met "sleutel", "token" of "api_key" in de naam staat wordt geweigerd; en: zonder de nieuwe optie laat de proefrun niets achter (bestaand gedrag ongewijzigd).
- **Poort:** P-jelly-leon (Snel voor `tools/emby-overname`; Volledig stap 8) + P-VEILIG + P-GIT
- **Valkuilen:** V-012 (schijf vol: de bewaarde datamap is groot, ruim op na S-P40-70); V-094; V-111; V-022
- **Bewijs:** `JLT-70` blijft "Bezig", validatie "Sim-getest" tot S-P40-70 het emulatordeel heeft gedraaid. Opmerking letterlijk: "Clientdeel Android-emulator: overdracht gebouwd, run in jelly-leon-clients. NIET GEVALIDEERD (echte NAS): echte Emby en echte apparaten."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG (VERPLICHT) + R-HARDE-EIS (VERPLICHT) (tegelijk) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard; R-VEILIG N4, R-HARDE-EIS N4
- **Stop en vraag als:** de overdracht alleen kan werken met een echt wachtwoord of met de Emby-sleutel; de proefrun na de wijziging andere aantallen overgenomen gegevens meldt dan ervoor.

### S-P40-40 - Register upstream-gedrag en clientmatrix aanvullen (B03-019)
- **Repo:** jelly-leon | **Fase:** P4-0 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (runtimetests tegen een servercontainer)
- **Werkpakketten en tests:** B03-019, JLT-63, JLT-64, I06-06-07
- **Vooraf:** S-G1-16 klaar (schone werkboom, lokale image). WP-JSON B03-019 (veld Afhankelijkheid) noemt B03-003: een zachte afhankelijkheid, geen wachtpunt. Wat deze stap van B03-003 nodig heeft (de clients en het compat-harnas in jelly-leon-clients) bestaat al: EVIDENCE-regel B03-003 in jelly-leon-clients, "Sim-getest" (P0, contract 1.2 en JC3 van P4-0 tegen 12.4); de acceptatie van B03-003 (echte tv's en apparaten) is P6. Later sluit aan: S-G3-32 (B03-003, golf 3) draait de matrix opnieuw op 12.x na golf 2, met stock 12.x als controlegroep, en vult gaten; dat bewijs staat in jelly-leon-clients (EVIDENCE B03-003).
- **Al gedaan?** `cd <WERKMAP>/jelly-leon && $PY tools/jelly-leon/upstream_gedrag_check.py --overzicht` -> staan de vier gedragingen uit bouwpunt 1 er als regel met een test en uitkomst "ok", en noemt `docs/platform-v2/CLIENT_COMPAT_MATRIX.md` onder kop 4 de emulator-, desktop- en derden-clientuitkomst met datum, dan is de stap klaar.
- **Lees eerst:** WP-JSON rij B03-019 (Uitvoering a-c); `<WERKMAP>/jelly-leon/docs/platform-v2/UPSTREAM_GEDRAG.md`; `<WERKMAP>/jelly-leon/docs/platform-v2/CLIENT_COMPAT_MATRIX.md#4. Rooktest tegen de jelly-leon-image 12.4`; `<WERKMAP>/jelly-leon/docs/platform-v2/BOUWVERIFICATIE_P4-0.md#7. B03-019`; `<WERKMAP>/jelly-leon/tools/jelly-leon/e2e/upstream_gedrag_runtime.py`
- **Bouw:**
  1. Voeg aan `docs/platform-v2/UPSTREAM_GEDRAG.md` de gedragingen toe die in P4-0 gemeten zijn maar nog geen regel hebben (controleer eerst met `--overzicht` welke er al staan; gebruik het volgende vrije nummer in de reeks `UG-GEM-`): (a) PlaybackInfo zonder `MediaSourceId` en zonder `AudioStreamIndex`; (b) 401 op de oude kopvormen als legacy-authenticatie uit staat; (c) `?static=true` zonder token; (d) `ApiKey=` in een `TranscodingUrl` (moet in elk log en rapport gemaskeerd worden). Bron: `<WERKMAP>/.lokaal/plan/bron/VERVOLGPUNTEN_RUW.md`, punten onder jelly-leon.
  2. Schrijf per nieuwe regel een sync-blokkerende test in `tools/jelly-leon/e2e/upstream_gedrag_runtime.py` (een nieuwe naam in `CHECKS`) of, als het zonder server kan, als unit-test in `tools/jelly-leon/tests/`. Een regel zonder test laat `upstream_gedrag_check.py` falen: dat is de bedoeling.
  3. Draai T-JL-COMPAT tegen de lokale image en tegen stock op digest. Bewaar de rapporten onder `docs/platform-v2/test-evidence/` met datum.
  4. Werk `docs/platform-v2/CLIENT_COMPAT_MATRIX.md` bij onder kop 4: per clientrol de gemeten uitkomst met datum en bron. Neem de uitkomsten van jelly-leon-clients over met verwijzing naar hun EVIDENCE (emulators telefoon, tv, desktop onder Xvfb), niet als eigen meting. Swiftfin blijft "NIET GEVALIDEERD (Mac/Xcode)". Schrijf nergens "werkt ongewijzigd" zonder meting. Bron: WP-JSON rij B03-019, veld Acceptatie.
  5. Controleer dat de CI-job die het register bewaakt bestaat en de nieuwe tests meeneemt: `grep -n "upstream_gedrag" .github/workflows/jelly-leon-ci.yml`.
  6. Werk EVIDENCE en `EXCEL_TAKEN.json` bij; leg vast met P-GIT.
- **Tests (verplicht):** T-JL-TOOLS, T-JL-REGISTER, T-JL-COMPAT. Negatieve test: voeg in een tijdelijke kopie van het register een regel `UG-GEM-<n>` zonder test toe en toon dat `upstream_gedrag_check.py --repo <kopie>` met een fout stopt (als unit-test vastleggen als die er nog niet is: `grep -n "zonder test\|ontbreekt" tools/jelly-leon/tests/test_upstream_gedrag*.py`).
- **Poort:** P-jelly-leon (Snel + Volledig, de jobs die het register, de compat-rooktest en de stock-client-rooktest draaien) + P-EERLIJK + P-GIT
- **Valkuilen:** V-003 (test die niet kan falen); V-066 (OpenAPI-drift); V-072 (upstream-botsing); V-098; V-128 (clients op echte apparaten zijn niet gemeten)
- **Bewijs:** `B03-019`, `JLT-63`, `JLT-64`, `I06-06-07` -> "Bezig". JLT-63 blijft "Sim-getest" (rooktestdeel; "alle modules aan" kan pas na golf 1). Blokkade letterlijk: "NIET GEVALIDEERD (hardware): echte tv's, telefoons en tablets; NIET GEVALIDEERD (Mac/Xcode): Swiftfin."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** een gemeten gedrag van de Jelly Leon-image afwijkt van stock op dezelfde digest (dat is een regressie en telt als Sim-mislukt); een derden-client alleen werkt met legacy-authenticatie aan (BG-02).

### S-P40-45 - Sync-proef en negatieve upgradeproef met een 12.y-tag (voorwaardelijk)
- **Repo:** jelly-leon (de webproef in bouwpunt 5 is een aparte keten in jelly-leon-web) | **Fase:** P4-0 | **Omvang:** middel | **Moeilijkheid:** hoog | **Zwaar:** ja (.NET-build op een tak, image-build, containers)
- **Werkpakketten en tests:** B03-019, B03-014, JLT-67, JLT-61
- **Vooraf:** S-P40-40 klaar; upstream heeft een 12.x-tag die nieuwer is dan `upstream_tag` in `tools/jelly-leon/baseline.json` (vastgesteld in S-P40-10). Zonder die tag start deze stap niet en blijven JLT-67 en JLT-61 onderdeel (b) open; dat is een keuze voor de gebruiker in S-P40-95.
- **Al gedaan?** `ls <WERKMAP>/jelly-leon/docs/platform-v2/test-evidence | grep -i "sync"` en de EVIDENCE-rij `JLT-67` -> staat er een syncrapport met per patch een herbasisresultaat en is JLT-67 niet meer "Niet gestart", dan is de stap klaar.
- **Lees eerst:** TEST-JSON rijen JLT-67 en JLT-61; `<WERKMAP>/jelly-leon/docs/platform-v2/FORK_STRATEGIE.md`; `<WERKMAP>/jelly-leon/docs/platform-v2/PATCHES.md`; `<WERKMAP>/jelly-leon/.github/workflows/upstream-sync.yml`; `<WERKMAP>/jelly-leon/docs/platform-v2/BOUWVERIFICATIE_P4-0.md#6. Upgradeproef`
- **Bouw:**
  1. Werk op een aparte lokale tak, nooit op de werkbranch en nooit met een push naar de standaardbranch. Lees eerst `$PY tools/jelly-leon/upstream_sync.py merge --help`. Bron: `<WERKMAP>/jelly-leon/docs/platform-v2/FORK_STRATEGIE.md`.
  2. Kies de tag met `$PY tools/jelly-leon/upstream_sync.py kies` en voer de merge uit met `merge --tag <12.y> --branch <proeftak>`. Leg per geregistreerde patch uit `PATCHES.md` vast: herbaseert los, of conflict met bestand en oplossing.
  3. Bouw de plugin en de image op de proeftak (T-JL-PLUGIN, T-JL-IMAGE) en draai `upstream_gedrag_runtime.py --image <proefimage>` en `compat_api.py --image <proefimage> --stock-image <stock 12.y op digest>`. Elke regel `UG-...` is groen of blokkeert de sync met een duidelijke melding.
  4. JLT-61 onderdeel (b): draai `$PY tools/jelly-leon/e2e/upgrade_proef.py --image <proefimage> --expected-version <12.y> --negatief-verwacht weigert --report <pad>` (lees eerst `--help`). Verwachting: de vorige image op de gemigreerde database faalt zichtbaar met een duidelijke melding en zonder stille schade. Met alleen 12.4 was dit niet te bewijzen: upstream 12.4 start gewoon op een 12.4-database.
  5. Webdeel (keten in jelly-leon-web, na bouwpunt 2): `tools/jelly-leon-web/upstream_sync.py` op een proeftak en `tools/jelly-leon-web/e2e/upgrade_proef.py --negatief-verwacht weigert` (lees eerst `--help`). Clients: `git subtree pull` per client alleen als proef op een tak; het resultaat per JLC-patch noteren.
  6. Schrijf het syncrapport naar `docs/platform-v2/test-evidence/` (datum en tag in de naam) en werk EVIDENCE bij. Verwijder de proeftak niet; meld de naam in het rapport.
- **Tests (verplicht):** bouwpunten 3 en 4. Negatieve test: `upgrade_proef.py --negatief-verwacht weigert` moet falen als de oude image toch start (controleer dat de proef dan een exitcode ongelijk aan 0 geeft; staat in de unit-tests: `grep -n "negatief" tools/jelly-leon/tests/*.py | head`).
- **Poort:** P-jelly-leon (Volledig; de proeftak wordt niet gepusht, dus de CI-controle geldt alleen voor de commit met rapport en EVIDENCE op de werkbranch) + P-GIT
- **Valkuilen:** V-126 (de workflow `upstream-sync.yml` is nooit op GitHub gedraaid: lokaal bewijs is geen bewijs dat de workflow werkt); V-072; V-117; V-012
- **Bewijs:** `JLT-67` -> "Bezig", "Sim-geslaagd" of "Sim-mislukt" naar de uitkomst; `JLT-61` -> "Bezig" met onderdeel (b) apart benoemd. Opmerking letterlijk: "Workflow upstream-sync.yml niet op GitHub gedraaid. NIET GEVALIDEERD (echte NAS): terugzetten met een ZFS-snapshot."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-HARDE-EIS (VERPLICHT) (tegelijk) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); R-HARDE-EIS N4
- **Stop en vraag als:** er geen nieuwere 12.x-tag is; een patch niet los herbaseert en de oplossing gedrag wijzigt; de negatieve proef stille schade toont (database gewijzigd door de oude image); iemand de proeftak naar de standaardbranch wil brengen (R2: alleen de gebruiker).

### S-P40-50 - Definitieve baselines en controle-run op de forkbasis (B03-016)
- **Repo:** jelly-leon | **Fase:** P4-0 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (meetslot met servercontainers, transcodes op de Arc-iGPU, Playwright)
- **Werkpakketten en tests:** B03-016, I06-06-05 (het Sim-deel)
- **Vooraf:** S-P40-90 klaar; de keuze "voormeting 12.4 telt als definitief of opnieuw meten" is voorgelegd (hoofdstuk 3, keuzes zonder BG-nummer). Zonder antwoord: opnieuw meten (dat is altijd goed). WP-JSON B03-016 (veld Afhankelijkheid) noemt B03-003: een zachte afhankelijkheid, geen wachtpunt. Wat deze stap van B03-003 nodig heeft (de clients en het compat-harnas in jelly-leon-clients) bestaat al: EVIDENCE-regel B03-003 in jelly-leon-clients, "Sim-getest" (P0, contract 1.2 en JC3 van P4-0 tegen 12.4); de acceptatie van B03-003 (echte tv's en apparaten) is P6. Later sluit aan: S-G3-32 (B03-003, golf 3) meet de matrix opnieuw tegen de jelly-leon-image na golf 2, met stock 12.x op dezelfde digest als controlegroep; de baselines van deze stap blijven daarbij gelden.
- **Al gedaan?** `grep -l '"label": "definitief-forkbasis"' <WERKMAP>/jelly-leon/docs/platform-v2/test-evidence/*.json` -> bestaat er een baselinebewijs met dit label en een image op vaste digest, en een controle-run stock tegen de Jelly Leon-image, dan is de stap klaar.
- **Lees eerst:** WP-JSON rij B03-016 (Uitvoering c, Acceptatie); `<WERKMAP>/jelly-leon/docs/platform-v2/B03-016_HARNAS.md#3. Harnas, meetprotocol en baselines (deel c)`; `<WERKMAP>/jelly-leon/tools/b03-harnas/README.md`; `<WERKMAP>/jelly-leon/tools/b03-harnas/b03h/meetslot.py`; `<WERKMAP>/jelly-leon/docs/platform-v2/BOUWVERIFICATIE_B03-016.md`
- **Bouw:**
  1. Lees `PYTHONPATH=tools/b03-harnas $PY -m b03h baseline --help` en `... diffrun --help`. Gebruik alleen opties die daar staan.
  2. Controleer het corpus voor de meting: `PYTHONPATH=tools/b03-harnas $PY -m b03h corpus bron-controle` (sha256 van `<WERKMAP>/.lokaal/media-corpus`).
  3. Meet de baselines stock-standaard en stock-best op exact de digest van de forkbasis: `PYTHONPATH=tools/b03-harnas $PY -m b03h baseline --label definitief-forkbasis --image <stock 12.x op digest> --runs 3 --uit docs/platform-v2/test-evidence/<naam met datum>.json`. Het meetslot neemt `stack.lock` zelf; start in die tijd geen docker-build, Gradle of emulator. Een run boven de lastgrens is ongeldig en wordt herhaald. Bron: WP-JSON rij B03-016, Uitvoering (c).
  4. Draai de differentiele controle-run stock tegen de Jelly Leon-image: `... -m b03h diffrun --image-a <stock op digest> --image-b <jelly-leon-image> --uit docs/platform-v2/test-evidence/<naam>.json`. Verwachting: 0 verschillen buiten de vaste uitzonderingen. De lokale image heeft geen vaste digest: stel eerst vast of het bewijsformaat dat toelaat (`grep -n "DIGEST_RE" tools/b03-harnas/b03h/bewijs.py tools/b03-harnas/b03h/diffrun.py`); zo niet, noteer de image met tag en commit in de opmerking en meld het.
  5. Draai de negatieve proef van de controle-run (`--negatieve-proef`): het harnas moet het ingebrachte verschil vinden.
  6. Maak het leesbare rapport: `... -m b03h rapport` (lees `--help`) en werk `docs/platform-v2/B03-016_HARNAS.md` bij: voormeting en definitieve meting apart gelabeld, per metriek n, interval, digest, seed en loadavg.
  7. Werk de blokkadetekst van `B03-016` in EVIDENCE bij: de zin over de desktop onder Xvfb klopt niet meer na S-P40-90. Leg vast met P-GIT.
- **Tests (verplicht):** T-JL-HARNAS; bouwpunten 3, 4 en 5. Negatieve test: bouwpunt 5 (verschil moet gevonden worden) en `b03h guard --git .` (weigert beperkt gelicentieerde testdata). Herhaalbaarheid: een tweede baseline-run valt binnen het interval van de eerste.
- **Poort:** P-jelly-leon (Snel voor `tools/b03-harnas`; Volledig stap 9) + P-EERLIJK + P-GIT
- **Valkuilen:** V-009 (stack-lock lang bezet: plan de meting als er geen andere zware stap loopt); V-005 (meting over lege invoer); V-012; V-077; V-057
- **Bewijs:** `B03-016` -> "Bezig", validatie "Sim-getest; Intel-iGPU-getest (ontwikkelmachine)"; `I06-06-05` -> "Bezig" voor het Sim-deel. Blokkade letterlijk: "NIET GEVALIDEERD (hardware): A310, UHD 770 en echte tv's; NIET GEVALIDEERD (echte NAS): baseline op de NAS; NIET GEVALIDEERD (Mac/Xcode): Swiftfin."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** de controle-run stock tegen Jelly Leon een verschil buiten de vaste uitzonderingen toont (regressie van de fork); het meetslot na drie pogingen geen geldige run oplevert door last van andere ketens; het corpus niet meer klopt met zijn sha256.

### S-P40-60 - Voormeting Watch Together (B03-020)
- **Repo:** jelly-leon | **Fase:** P4-0 (golf 0) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (meerdere browsers en servercontainers in een meetslot)
- **Werkpakketten en tests:** B03-020
- **Vooraf:** S-P40-50 klaar. WP-JSON B03-020 (veld Afhankelijkheid) noemt B03-003: een zachte afhankelijkheid, geen wachtpunt. Wat deze stap van B03-003 nodig heeft (de clients en het compat-harnas in jelly-leon-clients) bestaat al: EVIDENCE-regel B03-003 in jelly-leon-clients, "Sim-getest" (P0, contract 1.2 en JC3 van P4-0 tegen 12.4); de acceptatie van B03-003 (echte tv's en apparaten) is P6. De clientdekking in het bewijs geldt voor de clients van dat moment. Later sluit aan: S-G3-32 (B03-003, golf 3) vult gaten in de clientmatrix.
- **Al gedaan?** `ls <WERKMAP>/jelly-leon/docs/platform-v2/test-evidence | grep -i "b03-020"` en de EVIDENCE-rij `B03-020` -> bestaat er baselinebewijs met de scenario's S1, S2, S3 en S5 voor stock-standaard en stock-best, dan is de stap klaar. De rij bestond bij het schrijven van dit plan niet.
- **Lees eerst:** WP-JSON rij B03-020; BOUWPLAN `#F1.8 Bouwfasen`; `<WERKMAP>/jelly-leon/tools/b03-harnas/b03h/corpus/r_f1_framecode.py`; `<WERKMAP>/jelly-leon/tools/b03-harnas/b03h/baseline.py`; `<WERKMAP>/jelly-leon/docs/platform-v2/B03-016_HARNAS.md#3. Harnas, meetprotocol en baselines (deel c)`
- **Bouw:**
  1. Maak en bevries het framecode-recept: `PYTHONPATH=tools/b03-harnas $PY -m b03h corpus maak f1-framecode --bevries` (lees eerst `corpus maak --help`). Het manifest met sha256 komt in het bewijs; de media zelf nooit in de repo.
  2. Bouw de meting als nieuw onderdeel in het bestaande harnas `tools/b03-harnas/b03h/` (hergebruik `meetslot.py`, `bewijs.py`, `statistiek.py`, `web.py`). Meet eerst de meetonzekerheid: twee lezers van een sessie (currentTime) en het framecode-raster per opnamemethode tegen een bekende klok. Bron: WP-JSON rij B03-020, Uitvoering.
  3. Meet S1 (loopback, twee verschillende gebruikers), S2 (een transcoderende deelnemer, handmatig QSV op de Arc-iGPU), S3 (vertraging en verlies; stel eerst vast of `tc netem` in de container kan zonder extra rechten op de host: ONBEKEND - eerst vaststellen met een proefcontainer; lukt het niet, dan S3 "niet gemeten" met reden) en S5 (gesmoorde deelnemer). Elk minstens 5 runs, loadavg per run.
  4. S4 (web + desktop) alleen als S-P40-90 de desktop werkend heeft; anders "Geblokkeerd" met reden.
  5. Leg de zichtbaarheid van groepen en deelnemersnamen per rol vast via `GET /SyncPlay/List`, en maak van de genoemde open upstream-bugs regressietests voor zover ze zonder echte apparaten te reproduceren zijn; de rest staat er met "niet reproduceerbaar in de simulatie".
  6. Schrijf het bewijs als JSON met label "voormeting-12.4" of "definitief-forkbasis" (de labels uit `b03h/bewijs.py`) en voeg de rij `B03-020` toe aan EVIDENCE en `EXCEL_TAKEN.json`. Leg vast met P-GIT.
- **Tests (verplicht):** T-JL-HARNAS (met unit-tests voor de nieuwe meting en de statistiek). Negatieve test: een run boven de lastgrens wordt als ongeldig gemarkeerd en telt niet mee (unit-test met een nagebootste loadavg); en: een bewijs zonder vaste image-digest wordt door `bewijs.py` geweigerd.
- **Poort:** P-jelly-leon (Snel voor `tools/b03-harnas`; Volledig stap 9) + P-GIT
- **Valkuilen:** V-009; V-005; V-032 (wisselend falende test niet wegretryen: een ongeldige run is iets anders dan een mislukte); V-067; V-073
- **Bewijs:** `B03-020` -> "Bezig", "Sim-getest; Intel-iGPU-getest (ontwikkelmachine)". Blokkade letterlijk: "NIET GEVALIDEERD (hardware): A310, UHD 770 en echte tv's; NIET GEVALIDEERD (Mac/Xcode): Swiftfin; NIET GEVALIDEERD (echte NAS)."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** de meetonzekerheid groter is dan het verschil dat Watch Together later moet aantonen (dan is de meetmethode ongeschikt: melden, niet doorgaan); netem alleen kan met rechten op de host.

### S-P40-62 - Voormeting aanbevelingen (B03-030)
- **Repo:** jelly-leon | **Fase:** P4-0 (golf 0) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (stub-bibliotheek scannen in een servercontainer)
- **Werkpakketten en tests:** B03-030
- **Vooraf:** S-P40-50 klaar; BG-37 (genomen: beperkt gelicentieerde testdata alleen lokaal, nooit in repo of image)
- **Al gedaan?** `ls <WERKMAP>/jelly-leon/docs/platform-v2/test-evidence | grep -i "b03-030"` en de EVIDENCE-rij `B03-030` -> staan de baselinecijfers met n, interval, dataset-sha256, digest, seed en commit erin, dan is de stap klaar.
- **Lees eerst:** WP-JSON rij B03-030; BOUWPLAN `#F2.8 Bouwfasen` (rij F2-0 en gate G-F2-0); `<WERKMAP>/jelly-leon/tools/b03-harnas/b03h/corpus/r_f2_dsyn.py`; `<WERKMAP>/jelly-leon/tools/b03-harnas/b03h/statistiek.py`; `<WERKMAP>/jelly-leon/tools/b03-harnas/b03h/guard.py`
- **Bouw:**
  1. Maak en bevries D-SYN: `PYTHONPATH=tools/b03-harnas $PY -m b03h corpus maak f2-dsyn --bevries`. Laat R-TECH het recept beoordelen voordat er iets op wordt afgestemd (gate G-F2-0: "bevroren en beoordeeld").
  2. Bouw de baselinemeting voor aanbevelingen als onderdeel van het harnas (de werkpakkettekst noemt `baseline_f2.py`): stock (a) S-REC, S-REC-best, S-SIM, S-LAT, S-RND en POP als ondergrens; hetzelfde kandidatenfilter voor alle systemen. S-TMDB alleen in een wegwerpcontainer; kan dat niet zonder account of netwerk, dan "niet gemeten" met reden.
  3. Reken NDCG@10, Recall@10, coverage en ILD in het harnas en test ze tegen met de hand berekende voorbeelden. De .NET-CLI `jl-rec-eval` "op het Core-project" kan pas bestaan als dat project er is: die hoort bij S-G2-22 en moet daar op dezelfde voorbeelden dezelfde cijfers geven. Leg deze verschuiving vast in het bewijs.
  4. Bouw de lekbewaking: interacties met een tijdstip op of na T worden geweigerd; voer de lektest met geschudde holdout uit.
  5. D-ML (BG-37 is genomen: alleen lokaal): downloaden via een tijdelijk bestand, sha256 en atomaire hernoeming, nooit in repo of image (de guard weigert het). Lukt het niet: schrijf letterlijk "D-ML ontbreekt: <reden>"; dan geldt in S-G2-22 de regel voor alleen D-SYN.
  6. Meet de spreiding van stock zelf (2 runs), de scantijd en schijfruimte van de stub-bibliotheek, en ruim de stub-bibliotheek op (`corpus opruimen`).
  7. Leg de drempels en marges vast in EVIDENCE voordat er een engine bestaat (pre-registratie) en voeg de rij `B03-030` toe. Leg vast met P-GIT.
- **Tests (verplicht):** T-JL-HARNAS. Negatieve test: de lekbewaking weigert een interactie met tijdstip >= T (unit-test); `b03h guard --map <map met een MovieLens-bestand>` weigert (bestaat de test al: `grep -n "movielens\|MovieLens" tools/b03-harnas/tests/*.py | head`).
- **Poort:** P-jelly-leon (Snel voor `tools/b03-harnas`; Volledig stap 9) + P-GIT
- **Valkuilen:** V-005; V-012; V-097 (gegevens van de ontwikkelmachine in een publieke repo); V-003
- **Bewijs:** `B03-030` -> "Bezig", "Sim-getest". Blokkade letterlijk: "NIET GEVALIDEERD (echte NAS): echte bibliotheek en echte kijkgeschiedenis (JLT-15)."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** de MovieLens-download een account of het aanvaarden van voorwaarden vraagt; de stub-bibliotheek meer schijf vraagt dan vrij is (`df -h <WERKMAP>/.lokaal`); een metriek afwijkt van het handberekende voorbeeld.

### S-P40-64 - Voormeting apparaten en afspeelfouten (B03-060)
- **Repo:** jelly-leon | **Fase:** P4-0 (golf 0) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (Playwright met drie browsers, transcodes)
- **Werkpakketten en tests:** B03-060; JLT-40 (alleen het vastgelegde meetcommando, bouwpunt 6)
- **Vooraf:** S-P40-50 klaar
- **Al gedaan?** `ls <WERKMAP>/jelly-leon/docs/platform-v2/test-evidence | grep -i "b03-060"` en de EVIDENCE-rij `B03-060` -> staat er een rapport per client en per baseline met de bevroren devset en testset (sha256-manifest) en geeft `grep -n "^#.* JLT-40" <WERKMAP>/jelly-leon/tools/b03-harnas/README.md` een kop (bouwpunt 6), dan is de stap klaar; ontbreekt alleen die kop, dan alleen bouwpunt 6.
- **Lees eerst:** WP-JSON rij B03-060; BOUWPLAN `#F5.8 Bouwfasen` (rij F5-S0); `<WERKMAP>/jelly-leon/tools/b03-harnas/b03h/corpus/r_f5_fouten.py`; `<WERKMAP>/jelly-leon/tools/b03-harnas/b03h/web.py`; `<WERKMAP>/jelly-leon/tools/b03-harnas/b03h/baseline.py` (metingen `dp` en `orakel`)
- **Bouw:**
  1. Maak en bevries de gecontroleerde-foutenset: `PYTHONPATH=tools/b03-harnas $PY -m b03h corpus maak f5-fouten --bevries` en het ASS-recept (`corpus maak ass`). Devset en testset apart, met sha256-manifest in het bewijs.
  2. Breid de bestaande metingen `dp` en `orakel` uit tot het rapport K1 tot en met K9 per client en per baseline (a) en (b): Direct Play-ratio, onterechte Direct Plays, onnodige transcodes, inbrandingen, aandeel hardwaretranscodes, CPU per transcode, tijd tot spelend beeld na een mislukte Direct Play (bovengrens 60 s). De werkpakkettekst noemt `tools/jelly-leon/e2e/` als plaats; het raamwerk staat in `tools/b03-harnas`: bouw het daar en leg de afwijking vast in `docs/platform-v2/B03-016_HARNAS.md`.
  3. Afspeelorakel: binnen 10 s `currentTime` >= 2 s, `videoWidth` > 0, geen error-event, audio niet stil. Het stilte-orakel headless is een spike van golf 2 (S-G2-35); tot dan staat "audio niet stil" als "niet gemeten".
  4. De eerste run bevestigt de matrix uit de analyse (Chromium 16/25, Firefox 17/25, WebKit 21/25 Direct Play) of verklaart elk verschil schriftelijk. Bron: WP-JSON rij B03-060, Acceptatie.
  5. Emulatordelen (telefoon, tablet, tv) lopen via de clientmatrix en het clientharnas (S-P40-70); neem hun uitkomst over met verwijzing, niet als eigen meting. Desktop alleen na S-P40-90.
  6. Leg in `tools/b03-harnas/README.md` onder een eigen kop die begint met "JLT-40" (bijvoorbeeld `## JLT-40 - meetcommando winstmeting apparaatprofielen`; S-G4-47 zoekt met `grep -n "JLT-40"` op die kop) het exacte meetcommando vast waarmee later JLT-40 (winstmeting apparaatprofielen tegen stock-standaard en stock-best) wordt gedraaid: welk subcommando van `b03h`, welke opties, welke bevroren set en welke uitvoer. De winstmeting zelf is golf 4 (STAPPEN_P4_GOLF3_4.md, S-G4-47) en wacht op dit commando.
  7. Voeg de rij `B03-060` toe aan EVIDENCE en `EXCEL_TAKEN.json`; leg vast met P-GIT.
- **Tests (verplicht):** T-JL-HARNAS; minstens 3 runs met identieke beslissingen en tijden binnen 10 procent. Negatieve test: een bestand uit de foutenset met een liegende codec moet in het rapport als "onterechte Direct Play" verschijnen; verschijnt het als geslaagd, dan meet het orakel niet.
- **Poort:** P-jelly-leon (Snel voor `tools/b03-harnas`; Volledig stap 9) + P-GIT
- **Valkuilen:** V-077 (harnas keurt goed of af om de verkeerde reden); V-007; V-067; V-009
- **Bewijs:** `B03-060` -> "Bezig", "Sim-getest; Intel-iGPU-getest (ontwikkelmachine)". Blokkade letterlijk: "NIET GEVALIDEERD (hardware): echte tv's, telefoons, A310 en UHD 770; NIET GEVALIDEERD (echte NAS)."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** de matrix sterk afwijkt van de analyse en geen verklaring te vinden is; WebKit niet start (V-067).

### S-P40-66 - Meetlat segmenten: bevroren testset, harnas en baselines (B03-070)
- **Repo:** jelly-leon | **Fase:** P4-0 (golf 0) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (testset genereren tot 15 GB, servercontainers)
- **Werkpakketten en tests:** B03-070; JLT-50 (alleen het vastgelegde meetcommando, bouwpunt 6)
- **Vooraf:** S-P40-50 klaar; BG-32 (Intro Skipper alleen als testbaseline), BG-34 (labels Pioneer One) en BG-37 genomen. Zonder BG-34: het Pioneer One-deel "Geblokkeerd"; zonder BG-32: baseline (b) niet meten.
- **Al gedaan?** `ls <WERKMAP>/jelly-leon/docs/platform-v2/test-evidence | grep -i "b03-070"` en de EVIDENCE-rij `B03-070` -> staat het manifest-sha256 van de bevroren testset erin met n per type en geeft `grep -n "^#.* JLT-50" <WERKMAP>/jelly-leon/tools/b03-harnas/README.md` een kop (bouwpunt 6), dan is de stap klaar; ontbreekt alleen die kop, dan alleen bouwpunt 6.
- **Lees eerst:** WP-JSON rij B03-070; BOUWPLAN `#F6.8 Bouwfasen` (rij F6-S0); `<WERKMAP>/jelly-leon/tools/b03-harnas/b03h/corpus/r_f6_segmenten.py`; `<WERKMAP>/jelly-leon/tools/b03-harnas/b03h/statistiek.py`; BESLUITEN (afkorting uit de Opdrachtkop; zoek de koppen van BG-32 en BG-34)
- **Bouw:**
  1. Controleer vrije schijfruimte (`df -h <WERKMAP>/.lokaal`); de testset mag tot 15 GB groot zijn en wordt na de run verwijderd, manifest en seeds blijven.
  2. Maak en bevries de testset met andere seeds dan de devset: `PYTHONPATH=tools/b03-harnas $PY -m b03h corpus maak f6-segmenten --schaal vol --seed <n> --bevries`. De acht bestaande synthetische afleveringen zijn devset en komen nooit in een gate.
  3. Bouw het evaluatieharnas als onderdeel van `tools/b03-harnas/b03h/` (de werkpakkettekst noemt `tools/jelly-leon/segments-eval`; leg de afwijking vast): per type precisie, recall en F1 bij IoU >= 0,5 met Wilson-interval, grensfout mediaan en p95, onterecht overgeslagen seconden per uur, post-credit-schendingen. Onder de streef-n heet de uitkomst "smoke-gate (n = ...)".
  4. Baseline (a): stock 12.x standaard (verwachting voormeting: 0 segmenten). Baseline (b): stock + Intro Skipper ongewijzigd, alleen na BG-32 en alleen als spike S-IS een versie vindt die op deze basis laadt; anders "Geblokkeerd" met reden en vervalt elke cijferclaim tegen Intro Skipper.
  5. Het lezen van de kandidaatset via `GET /media/v1/segments/{itemId}?view=candidate` kan pas als de module bestaat (S-G2-40): bouw de lezer nu tegen een vast voorbeeldantwoord en markeer dat deel "niet gemeten".
  6. Leg in `tools/b03-harnas/README.md` onder een eigen kop die begint met "JLT-50" (bijvoorbeeld `## JLT-50 - meetcommando winstmeting segmenten`; S-G4-48 zoekt met `grep -n "JLT-50"` op die kop) het exacte meetcommando vast waarmee JLT-50 wordt gedraaid (stock standaard, stock + Intro Skipper, Jelly Leon; lezen via `?view=candidate` en `GET /MediaSegments`; bevroren testset op manifest-sha256). S-G2-42 en S-G2-44 (dit bestand) en S-G4-48 (STAPPEN_P4_GOLF3_4.md) gebruiken dat commando.
  7. Leg de drempels vast (pre-registratie) en voeg de rij `B03-070` toe aan EVIDENCE en `EXCEL_TAKEN.json`. Ruim de testset op (`corpus opruimen`). Leg vast met P-GIT.
- **Tests (verplicht):** T-JL-HARNAS; twee runs geven gelijke cijfers; `corpus controleer <set>` groen. Negatieve test: een opzettelijk verschoven label (10 s) laat de F1 dalen (het harnas kan falen); `b03h guard` weigert een Pioneer One-bestand of afgeleid label in de repo.
- **Poort:** P-jelly-leon (Snel voor `tools/b03-harnas`; Volledig stap 9) + P-GIT
- **Valkuilen:** V-012; V-003; V-005; V-097
- **Bewijs:** `B03-070` -> "Bezig", "Sim-getest". Blokkade letterlijk: "NIET GEVALIDEERD (echte NAS): winst op echte series zonder bevestigde Pioneer One-labels (BG-34) en zonder eigen bibliotheek-steekproef."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** er minder dan 20 GB vrij is; Intro Skipper alleen laadt met een aanpassing (dan is het geen ongewijzigde baseline); iemand de drempels na de eerste meting wil verschuiven.

### S-P40-70 - Tablet-emulator en het emulatordeel van JLT-60, JLT-63 en JLT-70
- **Repo:** jelly-leon-clients | **Fase:** P4-0 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (emulator in een container met /dev/kvm, Gradle)
- **Werkpakketten en tests:** B03-016, B03-019, JLT-60, JLT-63, JLT-70, I24-24-05 (het emulatordeel)
- **Vooraf:** S-P40-72 klaar; voor bouwpunt 4 en 5: S-P40-32 klaar (overdracht van de proefrun); BG-38 genomen
- **Al gedaan?** `python3 -c "import json;[print(o['id'],o['status'],o['validatie'],'|',(o.get('blokkade') or '')[:160]) for o in json.load(open('<WERKMAP>/jelly-leon-clients/docs/platform-v2/EVIDENCE.json')) if o['id'] in ('B03-016','JLT-70','I24-24-05')]"` -> noemt B03-016 de tablet niet meer als "niet stabiel (Sim-mislukt)" en bestaat er een rij `JLT-70` met het emulatordeel, dan is de stap klaar. Bij het schrijven van dit plan bestond `JLT-70` in deze repo niet.
- **Lees eerst:** `<WERKMAP>/jelly-leon-clients/docs/adr/ADR-0011-clientcompatibiliteit-12x.md`; `<WERKMAP>/jelly-leon-clients/docs/platform-v2/BOUWVERIFICATIE_P4-0.md`; `<WERKMAP>/jelly-leon-clients/tools/clients/compat/emulator.py`; `<WERKMAP>/jelly-leon-clients/tools/clients/compat/hervatproef.py`; TEST-JSON rijen JLT-70 en JLT-60
- **Bouw:**
  1. Tablet-emulator: lees het bewijs van de mislukte runs (drie keer een OOM-kill binnen 4 GiB; met 5 GiB 1 van 3 geslaagd). Zoek de oorzaak in logcat en probeer binnen 4 GiB een kleinere schermdichtheid of minder gast-geheugen in `tools/clients/compat/emulator.py`. Draai daarna `python3 tools/clients/client_compat.py android --image <jelly-leon-image> --aanvullen --soorten tablet` (lees eerst `android --help`). Bron: `<WERKMAP>/.lokaal/plan/bron/VERVOLGPUNTEN_RUW.md`, kop "review:jelly-leon-clients".
  2. Lukt de tablet niet stabiel binnen 4 GiB: laat hem op "Sim-mislukt" staan met de metingen, en meld dat 5 GiB een afwijking is van de 4 GiB-regel. Niet stil de grens verhogen.
  3. Herhaal de hervatproef met n >= 5 voor Jelly Leon en stock: `python3 tools/clients/client_compat.py hervatproef --image <jelly-leon-image> --stock-image <stock op digest> -n 5 --uit <bewijs>` (lees eerst `hervatproef --help`).
  4. JLT-70 emulatordeel: voeg aan `client_compat.py android` een optie toe die de testserver start op de datamap en met de gebruikers uit het overdrachtsbestand van S-P40-32 in plaats van een verse server. De naam van de optie kiest A-BOUW; hij staat in `--help`. De wegwerpwachtwoorden komen uit het overdrachtsbestand en gaan via de bestaande bewijscontrole (`compat/bewijs.py` weigert een document met een wachtwoord).
  5. Draai het scenario: inloggen als een overgenomen gebruiker in de telefoon-emulator en hervatten; het hervatpunt moet gelijk zijn aan het verwachte punt uit de overdracht (binnen de marge die de hervatproef al gebruikt). Draai het ook met de officiele app (`--bediend officieel`).
  6. JLT-60 emulatordeel: herhaal `android --migratie-van <oude image>` alleen als de Jelly Leon-image sinds de vorige run is veranderd; anders verwijs naar het bestaande bewijs.
  7. Werk `docs/platform-v2/BOUWVERIFICATIE_P4-0.md` en EVIDENCE bij; voeg de rij `JLT-70` toe. Ruim de overgedragen datamap op. Leg vast met P-GIT.
- **Tests (verplicht):** T-JLC-STATISCH; T-JLC-COMPAT (de onderdelen hierboven). Negatieve test: inloggen met een verkeerd wachtwoord moet in het scenario als "niet ingelogd" eindigen en de proef laten falen (unit-test of een run met een opzettelijk fout wachtwoord); en de hervatproef moet falen als het hervatpunt op 0 staat.
- **Poort:** P-jelly-leon-clients (Snel + het emulatordeel uit Volledig) + P-GIT
- **Valkuilen:** V-021 (geen KVM-toegang); V-076 (emulatorbewijs te mooi opgeschreven); V-014 (zware build door de kernel gestopt: emulator, Gradle en transcode nooit tegelijk); V-075; V-128
- **Bewijs:** `B03-016`, `B03-019`, `JLT-60`, `JLT-63` en `JLT-70` -> "Bezig"; `I24-24-05` blijft "Geblokkeerd". Blokkade letterlijk: "NIET GEVALIDEERD (hardware): echte telefoons, tablets en tv's (D15); NIET GEVALIDEERD (Mac/Xcode): Swiftfin; NIET GEVALIDEERD (echte NAS)." De echte apparaten horen in `<WERKMAP>/.lokaal/plan/uit/STAPPEN_P6.md`.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-HARDE-EIS (VERPLICHT) (tegelijk) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard; R-HARDE-EIS N4 (kijkt alleen naar het JLT-70-deel: klopt het hervatpunt met wat uit Emby kwam)
- **Stop en vraag als:** `/dev/kvm` niet bruikbaar is in de container; het hervatpunt na de overname afwijkt van het verwachte punt (dat raakt de HARDE EIS); de tablet alleen met meer dan 4 GiB werkt.

### S-P40-72 - Compat-harnas veiliger maken: eigen netwerk, willekeurige testwachtwoorden, controle op buildbestanden
- **Repo:** jelly-leon-clients | **Fase:** P4-0 | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** ja (een emulator- en een desktoprun als bewijs)
- **Werkpakketten en tests:** B03-016, B03-019
- **Vooraf:** S-P40-10 klaar
- **Al gedaan?** `grep -n '"host"' <WERKMAP>/jelly-leon-clients/tools/clients/compat/emulator.py <WERKMAP>/jelly-leon-clients/tools/clients/compat/desktop.py ; grep -n "KIJKER_WW *=\|BEHEER_WW *=" <WERKMAP>/jelly-leon-clients/tools/clients/compat/server.py ; grep -n "kotlin" <WERKMAP>/jelly-leon-clients/tools/clients/check_clients.py` -> geen `--network host` meer, geen vaste wachtwoordwaarde meer en een controle op `.kotlin` aanwezig: dan is de stap klaar.
- **Lees eerst:** `<WERKMAP>/.lokaal/plan/bron/VERVOLGPUNTEN_RUW.md` (kop "review:jelly-leon-clients"); `<WERKMAP>/jelly-leon-clients/tools/clients/compat/server.py`; `<WERKMAP>/jelly-leon-clients/tools/clients/compat/emulator.py`; `<WERKMAP>/jelly-leon-clients/tools/clients/compat/desktop.py`; `<WERKMAP>/jelly-leon-clients/tools/clients/check_clients.py`
- **Bouw:**
  1. Vervang `--network host` voor de emulator- en de desktopcontainer door een eigen Docker-netwerk per run (of een gerichte poortdoorgifte), zodat de container alleen de testserver ziet en niet de andere diensten op de ontwikkelmachine. De testserver hangt aan hetzelfde netwerk; het netwerk wordt na de run verwijderd, ook bij een fout.
  2. Maak de wachtwoorden van de testaccounts per run willekeurig (alleen letters en cijfers, omdat ze met `adb input text` worden getypt). De bewijscontrole in `compat/bewijs.py` krijgt de waarden van die run mee en blijft elk document met een wachtwoord weigeren.
  3. Voeg aan `tools/clients/check_clients.py` een controle toe die faalt als er een `.kotlin`-sessiemap of ander buildbestand in een client-subtree is getrackt (`git ls-files`). Geen `.gitignore` in de subtree zelf.
  4. Pas de unit-tests in `tools/clients/tests/` aan en voeg tests toe voor de drie punten.
  5. Draai als bewijs een telefoonrun en een desktoprun (T-JLC-COMPAT) en vergelijk de uitkomst met het vorige bewijs: geen scenario mag van geslaagd naar mislukt gaan.
  6. Werk `docs/adr/ADR-0011-clientcompatibiliteit-12x.md` bij met de netwerkkeuze (of schrijf een nieuw ADR met het eerstvolgende vrije nummer: `ls <WERKMAP>/jelly-leon-clients/docs/adr | sort | tail -3`). Leg vast met P-GIT.
- **Tests (verplicht):** T-JLC-STATISCH; T-JLC-COMPAT voor telefoon en desktop. Negatieve test: vanuit de emulatorcontainer is een poort van de host waarop een andere dienst luistert niet bereikbaar (test met een tijdelijke luisteraar op de host; verwacht: verbinding geweigerd of time-out); en `check_clients.py` faalt op een proefmap met een `.kotlin`-bestand.
- **Poort:** P-jelly-leon-clients (Snel + het emulatordeel uit Volledig) + P-VEILIG + P-GIT
- **Valkuilen:** V-008 (poorten botsen op de gedeelde machine); V-022; V-088 (testimages en testnetwerken blijven staan); V-021; V-094
- **Bewijs:** `B03-016` en `B03-019` in jelly-leon-clients blijven "Bezig", "Sim-getest"; de opmerking noemt de drie verbeteringen. "NIET GEVALIDEERD (hardware): echte apparaten."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG (VERPLICHT) (tegelijk) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard; R-VEILIG N4
- **Stop en vraag als:** de emulator de testserver alleen via het hostnetwerk kan bereiken; de verandering een scenario laat mislukken dat eerst slaagde.

### S-P40-92 - Bewijs uit de andere repos overnemen in jelly-leon (JLT-60, JLT-70, clientmatrix)
- **Repo:** jelly-leon | **Fase:** P4-0 | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** JLT-60, JLT-70, JLT-63, B03-015, B03-016
- **Vooraf:** S-P40-70 klaar; S-P40-20 klaar; S-P40-50 klaar
- **Al gedaan?** `python3 -c "import json;[print(o['id'],o['validatie'],'|',o['opmerking'][:220]) for o in json.load(open('<WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json')) if o['id'] in ('JLT-60','JLT-70')]"` -> noemen beide rijen het emulatorbewijs van jelly-leon-clients met commit en datum en staat er niet meer "clientdeel Android-emulator ontbreekt", dan is de stap klaar.
- **Lees eerst:** `<WERKMAP>/jelly-leon-clients/docs/platform-v2/EVIDENCE.json` (rijen JLT-60, JLT-63, JLT-70); `<WERKMAP>/jelly-leon-clients/docs/platform-v2/BOUWVERIFICATIE_P4-0.md`; `<WERKMAP>/jelly-leon/docs/platform-v2/CLIENT_COMPAT_MATRIX.md#2. Clients (echte apparaten)`; TEST-JSON rijen JLT-60 en JLT-70
- **Bouw:**
  1. Controleer dat het werk van S-P40-70 en S-P40-20 gepusht is (`git -C <WERKMAP>/jelly-leon-clients log origin/ccr-c133d7a0-kuz1cv --oneline -3`); verwijs alleen naar commits die op de remote staan.
  2. Werk in `docs/platform-v2/EVIDENCE.json` de rijen `JLT-60` en `JLT-70` bij: het emulatordeel met repo, commit, datum en uitkomst. Een rij gaat alleen naar "Sim-geslaagd" als elk onderdeel van de test is uitgevoerd en geslaagd; anders blijft "Sim-getest" met wat ontbreekt.
  3. Werk `docs/platform-v2/CLIENT_COMPAT_MATRIX.md` bij met de tabletuitkomst en de hervatproef (verwijzing, geen eigen meting) en `docs/platform-v2/BOUWVERIFICATIE_P4-0.md` onder kop 10 met wat nu nog open is.
  4. Werk `docs/platform-v2/EXCEL_TAKEN.json` bij en leg vast met P-GIT.
- **Tests (verplicht):** `python3 -m json.tool docs/platform-v2/EVIDENCE.json > /dev/null`; T-JL-TOOLS als er een test is die EVIDENCE controleert (`grep -ln "EVIDENCE" tools/jelly-leon/tests/*.py`). Negatieve controle: `grep -n '"Gereed"\|"Geslaagd"' docs/platform-v2/EVIDENCE.json` geeft geen treffer.
- **Poort:** P-jelly-leon (Snel) + P-EERLIJK + P-GIT
- **Valkuilen:** V-017; V-098; V-101 (EVIDENCE verwijst naar tests die niet meer bestaan); V-104
- **Bewijs:** `JLT-60`, `JLT-70` -> "Bezig" met de eerlijke validatie; blokkade letterlijk: "NIET GEVALIDEERD (echte NAS): echte datamap en echte Emby; NIET GEVALIDEERD (hardware): echte apparaten."
- **Agents:** A-BOUW -> R-EERLIJK. Korte keten: alleen documentatie en bewijsverwijzingen, geen code.
- **Niveau:** standaard
- **Stop en vraag als:** het bewijs in de andere repo niet gepusht is; een rij alleen "Sim-geslaagd" kan worden door een onderdeel weg te laten.

### S-P40-80 - Overname-assistent: ontwerp en ADR (geen terminal voor de gebruiker)
- **Repo:** jelly-leon | **Fase:** P4-0 | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** B03-015 (contractpunt C1.3-JL-05); raakt JLT-74 als voorbereiding
- **Vooraf:** S-P40-30 klaar; BG-22 genomen of de terugval uit hoofdstuk 3; de keuze "runtime van de assistent" is aan de gebruiker voorgelegd (hoofdstuk 3)
- **Al gedaan?** `ls <WERKMAP>/jelly-leon/docs/adr | grep -i "assistent"` -> een ADR over de overname-assistent bestaat en staat in `docs/adr/README.md`: dan is de stap klaar. Bij het schrijven van dit plan bestond dat ADR niet.
- **Lees eerst:** `<WERKMAP>/jelly-leon/docs/platform-v2/OVERNAME_EMBY.md#Wat nog moet gebeuren vóór de echte overname`; BOUWPLAN `#10.9.1 Overname vanuit Emby`; `<WERKMAP>/jelly-leon/tools/emby-overname/README.md` (de opdrachten en de regel "Exitcodes"); `<WERKMAP>/jelly-leon/docs/adr/ADR-0025-b03-015-eigen-overnametool-niet-jellyplex-watched.md`; `<WERKMAP>/.lokaal/plan/uit/VALKUILEN.md` (V-118, V-109, V-119)
- **Bouw:**
  1. Schrijf een nieuw ADR met het eerstvolgende vrije nummer (`ls docs/adr | sort | tail -3`) en zet het in `docs/adr/README.md`. Onderwerp: een pagina in het beheer van Jelly Leon die de bestaande overnametool start, zodat de gebruiker geen terminal nodig heeft. Bron: `<WERKMAP>/.lokaal/plan/bron/VERVOLGPUNTEN_RUW.md`, sectie jelly-leon (regels over de overname-assistent).
  2. Leg de runtime vast volgens de keuze van de gebruiker. De image bevat nu geen Python (`grep -n -i python deploy/allinone/Dockerfile` geeft niets). Beschrijf de drie mogelijkheden met hun gevolgen: (a) de interpreter van de analysewerker gebruiken (komt in S-G1-30); (b) een eigen kleine interpreter alleen voor de tool; (c) de tool herschrijven in de plugin. Kies niet zelf.
  3. Leg de stappen van het scherm vast, in de volgorde van de tool: inventaris, droge proefrun, rapport per gebruiker met afhandellijst, akkoord op elk verschil, overzetten, laatste delta, eindrapport. Het akkoord wordt op het scherm gegeven en opgeslagen in de vorm van `tools/emby-overname/schemas/emby-overname-akkoord.schema.json`.
  4. Leg de grenzen vast: alleen een beheerder; de Hub en de AI kunnen de overname niet starten; de Emby-sleutel en de Jelly Leon-sleutel staan alleen in de geheimenmap en komen nooit in een antwoord, export of log; de tool start als proces met een lijst van argumenten (geen shell); een run tegelijk; werkmap onder de eigen schrijfplek van Jelly Leon (README van de tool, alinea "Uitvoer per run").
  5. Leg de foutafhandeling vast: elke exitcode van de tool krijgt een Nederlandse melding; bij exitcode 9 (doel is geen Jellyfin of dezelfde server als de bron) stopt het scherm en schrijft niets; het adres van Jelly Leon wordt nooit uit de instellingen van Emby overgenomen.
  6. Leg vast wat het scherm niet doet: niets in Emby wijzigen, Emby niet stoppen of verwijderen (de controlelijst "Emby verwijderen" is alleen een leeslijst voor de gebruiker), geen ondertiteldownloaders van Jellyfin installeren (BG-22).
  7. Werk `docs/platform-v2/OVERNAME_EMBY.md` bij met een verwijzing naar het ADR. Leg vast met P-GIT.
- **Tests (verplicht):** T-JL-REGISTER; T-JL-TOOLS. Negatieve controle: `grep -n -i "terminal\|ssh\|docker exec\|python -m" docs/adr/<nieuw ADR>` laat geen stap zien die de gebruiker zelf moet uitvoeren; en het ADR noemt geen sleutelwaarde, adres of servernaam (P-VEILIG).
- **Poort:** P-jelly-leon (Snel) + P-VEILIG + P-HARDE-EIS + P-GIT
- **Valkuilen:** V-118; V-109 (de tool had per vergissing in Emby kunnen schrijven); V-096 (herstelweg via de terminal); V-119
- **Bewijs:** `B03-015` blijft "Bezig"; de opmerking noemt het ADR. Blokkade letterlijk: "NIET GEVALIDEERD (echte NAS): echte overname en de controlelijst Emby verwijderen (JLT-74)."
- **Agents:** A-VERKEN -> A-BOUW -> R-VEILIG (VERPLICHT) + R-HARDE-EIS (VERPLICHT) (tegelijk) -> A-HERSTEL -> R-EERLIJK. Geen R-TECH: de stap levert alleen een ontwerp en geen code; de twee verplichte reviewers lezen het ontwerp.
- **Niveau:** standaard; R-VEILIG en R-HARDE-EIS N4
- **Stop en vraag als:** de keuze voor de runtime niet genomen is; het ontwerp een schrijfactie in Emby of een route voor de Hub nodig lijkt te hebben; de gebruiker de overname toch via een andere weg wil starten.

### S-P40-82 - Overname-assistent bouwen in het beheer van Jelly Leon
- **Repo:** jelly-leon | **Fase:** P4-0 (wordt tijdens golf 1 gebouwd) | **Omvang:** groot | **Moeilijkheid:** hoog | **Zwaar:** ja (.NET-build, image-build, echte Emby- en Jellyfin-containers)
- **Werkpakketten en tests:** B03-015 (contractpunt C1.3-JL-05), JLT-70, JLT-71, JLT-72, JLT-73
- **Vooraf:** S-P40-80 klaar en de runtime gekozen; S-G1-14 klaar (pijplijn en foutcatalogus); S-G1-20 klaar (geheimenmap); S-G1-30 klaar als de keuze "interpreter van de analysewerker" is
- **Al gedaan?** `grep -rl -i "overname" <WERKMAP>/jelly-leon/plugins/JellyLeon/src --include=*.cs --include=*.html ; git -C <WERKMAP>/jelly-leon log --oneline --grep="assistent" | head -5` -> er zijn bronbestanden en commits van de assistent en `EVIDENCE` rij `B03-015` noemt de assistent als "Sim-getest": dan alleen de tests draaien. Bij half werk: lees het ADR van S-P40-80 en ga verder waar de routes ophouden.
- **Lees eerst:** het ADR uit S-P40-80; `<WERKMAP>/jelly-leon/tools/emby-overname/README.md`; PLUGIN `Core/Api/BeheerController.cs` en `Core/Http/JlPipeline.cs`; PLUGIN `Core/Secrets/SecretStore.cs`; `<WERKMAP>/jelly-leon/tools/emby-overname/e2e/proefrun.py`
- **Bouw:**
  1. Routes voor de beheerder volgens het ADR (stand lezen, inventaris, proefrun, rapport en afhandellijst lezen, akkoord opslaan, overzetten, delta). Elke route loopt via de bestaande pijplijn en de foutcatalogus (Bron: `docs/adr/ADR-0030-b03-017-foutcatalogus-pipeline-en-1-mib-per-route.md`), staat een keer in de routetabel en in het OpenAPI-bestand.
  2. Processtarter: start de tool met een lijst van argumenten (nooit via een shell), een vaste werkmap, een tijdslimiet en een slot zodat er een run tegelijk loopt. Vertaal elke exitcode naar een Nederlandse melding; exitcode 9 stopt de reeks en schrijft niets.
  3. Sleutels: de Emby-sleutel en de Jelly Leon-sleutel gaan via de geheimenmap naar een bestand met rechten 0600 dat de tool meekrijgt (`--emby-sleutel-bestand`, `--jl-sleutel-bestand`). Geen sleutel in XML, export, log, procesargumenten of antwoord.
  4. De pagina (buiten Peil; vormgeving van het Jellyfin-beheer): toont per gebruiker het rapport en de afhandellijst en vraagt akkoord op elk verschil. De knop "overzetten" werkt pas als het akkoord volledig is. Het adres van Jelly Leon is het eigen adres en komt nooit uit Emby.
  5. Zet de tool en de gekozen runtime in de image volgens het ADR (`deploy/allinone/Dockerfile`); de tool draait als de gewone gebruiker van de app, niet als root.
  6. Proef via de assistent: breid `tools/emby-overname/e2e/proefrun.py` uit (of schrijf er een script naast) dat dezelfde reeks als JLT-70 tot en met JLT-73 via de routes van de assistent draait tegen de lokale Jelly Leon-image en de echte Emby-container. De uitkomst moet gelijk zijn aan de run via de opdrachtregel.
  7. Herschrijf `docs/platform-v2/OVERNAME_EMBY.md` onder "Stappen" naar het scherm (geen opdrachten voor de gebruiker). Werk EVIDENCE en `EXCEL_TAKEN.json` bij. Leg vast met P-GIT.
- **Tests (verplicht):** T-JL-PLUGIN; T-JL-OVERNAME; T-JL-IMAGE; de proef uit bouwpunt 6 achter `stack.lock`. Negatieve tests: (1) een gewone gebruiker krijgt 403 op elke route; (2) doel is Emby of gelijk aan de bron: melding van exitcode 9 en 0 schrijfacties; (3) overzetten zonder volledig akkoord wordt geweigerd en schrijft niets; (4) de loggende proxy telt 0 verzoeken anders dan GET naar Emby; (5) de sleutelwaarde komt in geen log, antwoord of rapport voor.
- **Poort:** P-jelly-leon (Volledig) + P-VEILIG + P-HARDE-EIS + P-INSTALLATIE + P-GIT
- **Valkuilen:** V-118; V-109; V-110 (een leesverzoek laat Emby schrijven); V-111 (de proef verandert zelf de kijkgegevens); V-094; V-066 (OpenAPI loopt uit de pas)
- **Bewijs:** `B03-015`, `JLT-70`, `JLT-71`, `JLT-72`, `JLT-73` -> "Bezig" (assistent Sim-getest); `JLT-74` blijft "Geblokkeerd". Blokkade letterlijk: "NIET GEVALIDEERD (echte NAS): echte Emby van de gebruiker, D07-meting, akkoord van de gebruiker op elk verschil, controlelijst Emby verwijderen." Het NAS-deel staat in `<WERKMAP>/.lokaal/plan/uit/STAPPEN_P6.md`.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG (VERPLICHT) + R-HARDE-EIS (VERPLICHT) + R-MANIFEST (VERPLICHT) (tegelijk) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4; R-HARDE-EIS N5. Winst: dit is het startpunt van de echte overname van kijkgeschiedenis, gebruikers en rechten; een fout hier schrijft op de NAS verkeerde kijkgegevens of schrijft in Emby, en dat is niet met een nieuwe build te herstellen.
- **Stop en vraag als:** de proef via de assistent een ander rapport geeft dan de run via de opdrachtregel; een route nodig lijkt die de Hub of de AI kan aanroepen; de runtime de image groter maakt dan het ADR toestaat; er een verzoek anders dan GET naar Emby gaat.

### S-P40-90 - Desktop-spike in het meetharnas bijwerken
- **Repo:** jelly-leon | **Fase:** P4-0 | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** ja (desktop-app onder Xvfb in een container, testserver)
- **Werkpakketten en tests:** B03-016, JLT-63 (het desktopdeel)
- **Vooraf:** S-P40-40 klaar
- **Al gedaan?** `grep -n "shm" <WERKMAP>/jelly-leon/tools/b03-harnas/b03h/desktop.py ; python3 -c "import json;d=json.load(open('<WERKMAP>/jelly-leon/docs/platform-v2/test-evidence/b03-016-desktop-spike.json'));print(str(d)[:600])"` -> `--shm-size` staat in het harnas en het bewijs meldt dat de webclient laadt en de rooktest is gedraaid: dan is de stap klaar. Bij het schrijven van dit plan stond de spike in jelly-leon op "Geblokkeerd" (de webclient laadde niet na het verbinden).
- **Lees eerst:** `<WERKMAP>/jelly-leon/tools/b03-harnas/b03h/desktop.py`; `<WERKMAP>/jelly-leon/tools/b03-harnas/desktop/cdp.mjs`; `<WERKMAP>/jelly-leon-clients/tools/clients/compat/desktop.py` en `desktop_cdp.mjs` (de werkende oplossing, alleen lezen); `<WERKMAP>/jelly-leon/docs/platform-v2/B03-016_HARNAS.md`; `<WERKMAP>/.lokaal/plan/bron/VERVOLGPUNTEN_RUW.md` (sectie jelly-leon-clients, regel over het desktop-spike-harnas)
- **Bouw:**
  1. Neem de oplossing uit jelly-leon-clients over in het harnas: de container start met `--shm-size 1g` en de CDP-timers worden gewist voor het script eindigt.
  2. Lees het consolelog via CDP (`Runtime.consoleAPICalled`) en zet het in het bewijs, zodat een mislukte start een oorzaak heeft.
  3. Draai `PYTHONPATH=tools/b03-harnas $PY -m b03h desktop --stap alles --uit <bewijs.json>` (lees eerst `desktop --help`); de app komt uit de build van jelly-leon-clients (`make desktop-bouw` in die repo; niet opnieuw bouwen als de build er staat).
  4. Rooktest: inloggen, afspelen van een corpusbestand en hervatten; beantwoord de vraag of er een ChunkLoadError optreedt en leg het antwoord vast.
  5. Controleer in de stopregels van het harnas dat een voortgangsmelding met positie 0 voor het hervatpunt de proef laat falen (dezelfde regel als in het clientharnas). Bron: `<WERKMAP>/.lokaal/plan/bron/VERVOLGPUNTEN_RUW.md`, sectie jelly-leon-clients.
  6. Werk `docs/platform-v2/CLIENT_COMPAT_MATRIX.md` (kop "4. Rooktest tegen de jelly-leon-image") en `docs/platform-v2/B03-016_HARNAS.md` bij. Werk EVIDENCE bij en leg vast met P-GIT.
- **Tests (verplicht):** T-JL-HARNAS; de run uit bouwpunt 3. Negatieve test: een unit-test in `tools/b03-harnas/tests/` die bewijst dat een voortgangsmelding met positie 0 voor het hervatpunt als mislukt telt, en dat een run zonder geladen webclient "Sim-mislukt" geeft en niet "Sim-getest".
- **Poort:** P-jelly-leon (Snel + job b03-harnas uit Volledig) + P-GIT
- **Valkuilen:** V-077 (het harnas keurt goed of af om de verkeerde reden); V-073; V-008; V-088
- **Bewijs:** `B03-016` en `JLT-63` -> "Bezig"; het desktopdeel "Sim-getest" of eerlijk "Sim-mislukt" met de oorzaak uit het consolelog. "NIET GEVALIDEERD (hardware): echte apparaten; NIET GEVALIDEERD (Mac/Xcode): Swiftfin."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** de desktop-build in jelly-leon-clients ontbreekt en opnieuw gebouwd moet worden (dat is werk voor de baan jelly-leon-clients); de app met `--shm-size 1g` nog steeds de webclient niet laadt.

### S-P40-95 - Gate P4-0
- **Repo:** geen (A-GATE leest in jelly-leon, jelly-leon-web, jelly-leon-clients en media-guard-ultimate) | **Fase:** P4-0 | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** B03-014, B03-015, B03-016, B03-019, JLT-60, JLT-61, JLT-62, JLT-63, JLT-64, JLT-67, JLT-70, JLT-71, JLT-72, JLT-73
- **Vooraf:** S-P40-20, S-P40-30, S-P40-32, S-P40-40, S-P40-50, S-P40-70, S-P40-72, S-P40-90 en S-P40-92 klaar; S-P40-45 klaar of de 12.y-tag ontbreekt nog; BG-01 en BG-02 genomen. S-P40-80, S-P40-82 en de voormetingen S-P40-60 tot en met S-P40-66 hoeven niet klaar te zijn.
- **Al gedaan?** `ls <WERKMAP>/.lokaal/ketens/GATE-P4-0/RAPPORT-A-GATE.md` -> bestaat het rapport en is de uitkomst aan de gebruiker voorgelegd, dan is de stap klaar.
- **Lees eerst:** FASERING `#Gate P4-0`; `<WERKMAP>/.lokaal/ketens/S-P40-10/DOSSIER.md`; EVIDENCE van de vier repos; `<WERKMAP>/media-guard-ultimate/tests/contract/mediaserver/RESULTS.md`; hoofdstuk 2 van dit bestand (de drie open gate-eisen)
- **Bouw:**
  1. A-GATE loopt de afvinklijst van hoofdstuk 9.1 af en leest bij elk punt het bewijs zelf (bestand, commit op de remote, CI-run). Een punt zonder bewijs is "niet gehaald", niet "aangenomen".
  2. A-GATE controleert de no-go's: een verschil in het rapport per gebruiker zonder akkoord; terugzetten niet bewezen; stock-clients breken; `EnableLegacyAuthorization` weer aan zonder besluit.
  3. A-GATE schrijft `<WERKMAP>/.lokaal/ketens/GATE-P4-0/RAPPORT-A-GATE.md` met per gate-eis: gehaald, niet gehaald of open met reden.
  4. De regisseur legt de uitkomst met een keuzemenu aan de gebruiker voor. De drie open eisen staan er letterlijk in: JLT-61 onderdeel (b) en JLT-67 wachten op een 12.y-tag van upstream; JLT-62 is alleen van toepassing als de D07-meting een Jellyfin-installatie vindt. Keuzes: (1) doorgaan naar golf 1 met deze eisen open en opnieuw toetsen zodra het kan; (2) wachten; (3) iets anders.
  5. Na de keuze: de regisseur werkt de Excel bij (P-EXCEL) en laat STATUS bijwerken (hoofdstuk 9).
- **Tests (verplicht):** A-GATE draait zelf geen builds. Controle: `python3 -m json.tool <EVIDENCE> > /dev/null` voor elke repo en een telling van de rijen per status. Negatieve controle: `grep -n '"Gereed"\|"Geslaagd"' <EVIDENCE>` geeft in geen van de vier repos een treffer; een rij "Sim-geslaagd" waarvan een onderdeel niet is uitgevoerd wordt als bevinding gemeld (V-098).
- **Poort:** P-EERLIJK + P-HARDE-EIS (leeslijst) + P-EXCEL
- **Valkuilen:** V-098; V-034 ("groen" zonder echte run); V-017; V-100; V-108 (de Excel loopt achter op EVIDENCE)
- **Bewijs:** geen eigen EVIDENCE-rij; het gate-rapport is het bewijs. Elke gate-eis die de NAS vraagt blijft "Geblokkeerd" met "NIET GEVALIDEERD (echte NAS)".
- **Agents:** A-GATE (VERPLICHT) -> regisseur legt voor aan de gebruiker. Korte keten: alleen lezen en oordelen, geen wijziging in een repo.
- **Niveau:** A-GATE N5. Winst: dit is het einde van de fase P4-0; een gate die hier iets mist laat al het modulewerk van golf 1 en 2 bouwen op een basis waarvan de upgrade, de overname of de MediaGuard-koppeling niet bewezen is.
- **Stop en vraag als:** een no-go waar is; het bewijs van een andere repo niet op de remote staat; de gebruiker niet kiest (dan start golf 1 niet, behalve de stappen die in hoofdstuk 6 "mag voor Gate P4-0" hebben).


### 8.2 Golf 1

Golf 1 is een afmaak- en controleplan. Van B03-017 staat de kern er (een DLL met `Core/` en de prototypemodules
Devices en Quality, de analyzer, de generator voor `config.json`, ADR-0029 tot en met ADR-0033 en de pluginproef voor
JLT-68, JLT-64 en JLT-65 in `tools/jelly-leon/e2e/plugin_proef.py`). Tijdens het schrijven van dit plan heeft een
andere ronde ook de IStartupFilter-spike (ADR-0033) en de MediaGuard-viewerclient zonder vervoer (B03-009, ADR-0034)
vastgelegd; S-G1-14 en S-G1-50 zijn daarom controle- en afmaakstappen. Van B03-018 ligt er alleen niet-vastgelegd
half werk (planner, budgetbeslisser en de werkerinterface in `Core/Planner`, `Core/Budget` en `Core/Werker`); S-G1-15
beoordeelt en legt het vast, S-G1-36 en S-G1-38 bouwen erop verder. Van geen van deze vastleggingen is een
onafhankelijke review gezien: de reviewers in de stappen hieronder zijn dus niet over te slaan. De stappen S-G1-15,
S-G1-17, S-G1-16, S-G1-10 en S-G1-12 mogen voor Gate P4-0 lopen; de rest begint na Gate P4-0 (S-P40-95).

### S-G1-15 - Half werk van B03-018 uit ronde 3 overnemen, groen maken en vastleggen
- **Repo:** jelly-leon | **Fase:** P4 golf 1 (mag voor Gate P4-0: opruimen van ronde 3; moet de EERSTE schrijvende stap in jelly-leon zijn) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (plugin-build en unit-tests achter docker-build.lock)
- **Werkpakketten en tests:** B03-018 (alleen het halve werk: planner, budgetbeslisser en werkerinterface; de inhoud wordt afgemaakt in S-G1-32, S-G1-36 en S-G1-38); B03-010 (deel IsKid: STAND_RONDE3.md noemt het bij dit halve werk; A-VERKEN stelt vast of er iets van IsKid in de zeven bestanden staat - het werk zelf hoort bij S-G1-18)
- **Vooraf:** S-P40-10 klaar. Geen besluit nodig.
- **Al gedaan?** `git -C <WERKMAP>/jelly-leon status --short ; git -C <WERKMAP>/jelly-leon log --oneline -3 -- plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Core/Planner plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Core/Budget ; grep -rn "ADR-0035" <WERKMAP>/jelly-leon/plugins/JellyLeon/src --include=*.cs ; ls <WERKMAP>/jelly-leon/docs/adr | grep "0035"` -> werkboom leeg, er is een commit op `Core/Planner` en `Core/Budget`, en elke ADR-verwijzing in de code wijst naar een ADR die bestaat: dan is de stap klaar. Stand bij de overdracht (gecontroleerd 2026-11-11): HEAD `cc3e82b4d`; gewijzigd en niet vastgelegd `Core/Api/BeheerController.cs`, `Core/Http/RouteTable.cs`, `PluginServiceRegistrator.cs` (onder PLUGIN) en `Hulp/OpenApiBouwer.cs` (onder PLUGINTEST), samen 73 regels erbij (route `GET /media/v1/planner`); nieuw en niet gevolgd `Core/Budget/BudgetBeslisser.cs`, `Core/Planner/` (BatchPlanner.cs, CgroupMarge.cs, ISessieBron.cs, LeesfoutBreker.cs, PlannerRegels.cs) en `Core/Werker/IWerker.cs`, samen 862 regels; geen tests voor planner en budget; `PluginServiceRegistrator.cs` verwijst naar "ADR-0035", die niet bestaat (hoogste ADR: ADR-0034). Reservekopie: `<WERKMAP>/.lokaal/halfwerk/jelly-leon.patch` en `<WERKMAP>/.lokaal/halfwerk/jelly-leon-nieuw.tgz`.
- **Lees eerst:** `<WERKMAP>/.lokaal/plan/STAND_RONDE3.md` (rij "jelly-leon / golf 1: B03-018 en B03-010"); `<WERKMAP>/.lokaal/plan/uit/AGENTEN.md#2.4 De vier ketenvormen` (vorm C); `<WERKMAP>/jelly-leon/docs/adr/ADR-0018-b03-planner-en-gpu-budget.md#Besluit`; `<WERKMAP>/jelly-leon/docs/adr/ADR-0017-b03-analysewerker-en-bestandspas.md#Besluit`; WP-JSON object `B03-018`
- **Bouw:**
  1. A-VERKEN controleert eerst dat de werkboom gelijk is aan de reservekopie: `git -C <WERKMAP>/jelly-leon diff HEAD | cmp - <WERKMAP>/.lokaal/halfwerk/jelly-leon.patch` (geen uitvoer verwacht) en `diff <(tar tzf <WERKMAP>/.lokaal/halfwerk/jelly-leon-nieuw.tgz | grep -v '/$' | sort) <(git -C <WERKMAP>/jelly-leon ls-files --others --exclude-standard | sort)` (leeg verwacht). Een verschil betekent dat iemand na het afbreken nog heeft gewerkt: stop.
  2. A-VERKEN beoordeelt elk van de elf bestanden in het dossier (veld `half_werk`): hoort bij deze stap ja/nee/onduidelijk; af/half/onbruikbaar; welke regel van ADR-0017 of ADR-0018 het dekt; en draait de snelle poort (T-JL-PLUGIN). Hij gooit niets weg en commit niets.
  3. A-BOUW maakt de stand bouwbaar en groen, zonder nieuwe functies: de route `GET /media/v1/planner` staat een keer in `Core/Http/RouteTable.cs`, alleen voor een beheerder, met de foutvorm uit de catalogus en in het OpenAPI-bestand (de drifttest `Core/OpenApiDriftTests.cs` moet groen zijn).
  4. A-BOUW schrijft per publieke klasse een unit-test die het gedrag vastlegt dat er nu staat (bijvoorbeeld: de planner start zonder werker niets - de standaard is `GeenWerker`; `LeesfoutBreker` slaat aan bij de drempel die in de code staat; `BudgetBeslisser` behandelt de topologie `Onbekend` als bezet). Tests voor de regels die nog ontbreken horen bij S-G1-36 en S-G1-38.
  5. ADR-verwijzing: stel het eerstvolgende vrije nummer vast (`ls <WERKMAP>/jelly-leon/docs/adr | sort | tail -3`). Is ADR-0035 vrij, schrijf dan ADR-0035 "B03-018: uitvoering planner, budget en werkerinterface (stand na ronde 3)" met wat er staat en wat open is, en verwijs voor de besluiten naar ADR-0017 en ADR-0018; is het nummer bezet, pas de verwijzing in de code aan naar het nieuwe nummer. Zet het ADR in `docs/adr/README.md`.
  6. Analyzer: de proefassembly faalt nog steeds en de plugin geeft 0 treffers (P-jelly-leon "4. Volledig", job `plugins`; `analyzer_proef.py --log ... --exitcode ...`, niet `--bouw`). Processtarts staan alleen in de namespace `Core.Werker` (JL0004, ADR-0032).
  7. A-BOUW schrijft `<WERKMAP>/.lokaal/ketens/S-G1-15/RAPPORT-A-BOUW.md` met een lijst "nog open", per bouwpunt van S-G1-32, S-G1-36 en S-G1-38 (die stappen lezen die lijst).
  8. Leg vast met P-GIT, elk bestand bij naam (nooit `git add -A`); lees de CI-uitkomst. Vink in VOORTGANG.md (door de regisseur) het halve werk van jelly-leon af met de commit.
- **Tests (verplicht):** T-JL-PLUGIN (eerst `--filter "FullyQualifiedName~Planner"` en `--filter "FullyQualifiedName~Budget"`, daarna volledig); T-JL-REGISTER; de analyzerproef zoals hierboven. Negatieve tests: `GET /media/v1/planner` zonder beheerderssessie geeft 401 of 403 in de contractvorm; de planner zonder werker start 0 taken; een processtart buiten `Core.Werker` laat de analyzer falen (de bestaande proefassembly).
- **Poort:** P-jelly-leon (Snel + job plugins uit Volledig) + P-VEILIG (alleen de nieuwe beheerroute) + P-GIT + P-EERLIJK
- **Valkuilen:** V-015 (half werk van een afgebroken ronde); V-016; V-022; V-066 (OpenAPI-drift); V-003; V-074 (.NET alleen via `<WERKMAP>/.lokaal/jl-dotnet.sh`)
- **Bewijs:** geen statuswijziging: de EVIDENCE-rij `B03-018` ontstaat in S-G1-30. Het rapport noemt wat er is vastgelegd. Geen NAS-regel nodig (niets uitgevoerd buiten unit-tests).
- **Agents:** Ketenvorm C (half werk afmaken, `<WERKMAP>/.lokaal/plan/uit/AGENTEN.md#2.4 De vier ketenvormen`): A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG (tegelijk; R-VEILIG VERPLICHT: nieuwe beheerroute) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard (R-VEILIG N4)
- **Stop en vraag als:** de werkboom afwijkt van de reservekopie; een bestand "onduidelijk" of "onbruikbaar" is (de regisseur legt dan het keuzemenu van AGENTEN.md 2.4, vorm C punt 3 voor: meenemen en afmaken, parkeren als vorm D, of laten verwijderen met de reservekopie als vangnet); groen maken een ontwerpkeuze vraagt die bij S-G1-36 of S-G1-38 hoort.

### S-G1-17 - Review van de gepushte golf-1-vastleggingen (B03-017, B03-009; `8a293727d` tot en met `cc3e82b4d`)
- **Repo:** jelly-leon | **Fase:** P4 golf 1 (mag voor Gate P4-0: review van bestaand werk) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee (reviewers lezen; A-HERSTEL bouwt alleen de plugin en de unit-tests achter docker-build.lock)
- **Werkpakketten en tests:** B03-017, B03-009, JLT-64, JLT-65, JLT-68; contract-ID's C1.3-JL-06, C1.3-JL-07, C1.3-JL-08 (alleen lezen: de stappen S-G1-12, S-G1-14 en S-G1-50 boeken ze)
- **Vooraf:** S-G1-15 klaar (werkboom schoon); S-P2-800 in `<WERKMAP>/.lokaal/plan/uit/STAPPEN_P2.md` (review van contract 1.3, `e294f84ea..945eb8113`) klaar of in de reviewfase (de reviewers van beide stappen mogen tegelijk lezen; A-HERSTEL van deze stap schrijft pas als A-HERSTEL van S-P2-800 klaar is). Deze stap reviewt alleen wat S-P2-800 niet dekt: `945eb8113..cc3e82b4d`.
- **Al gedaan?** `ls <WERKMAP>/.lokaal/ketens/S-G1-17/RAPPORT-R-TECH.md <WERKMAP>/.lokaal/ketens/S-G1-17/RAPPORT-R-EERLIJK.md ; git -C <WERKMAP>/jelly-leon log --oneline cc3e82b4d..HEAD | head` -> beide rapporten bestaan en R-EERLIJK meldt geen open punt: dan is de stap klaar. Bij de overdracht: acht vastleggingen `8a293727d` (plugin met kern en twee prototypemodules), `a075dfd95` (ADR-0029 tot en met ADR-0031), `776d7a4dd` (analyzer), `5082f02a6` (generator `config.json`), `c09698f09` (UserDeleted in ruwe databasebestanden), `9ebdfb15d` (pluginproef JLT-68/64/65), `cdb6dc3bf` (IStartupFilter-spike), `cc3e82b4d` (MediaGuard-viewerclient); gepusht, CI-run van `cc3e82b4d`: 42989190339 (bron: `<WERKMAP>/.lokaal/ketens/S-P2-000/DOSSIER.md`); geen enkele review.
- **Lees eerst:** `<WERKMAP>/.lokaal/plan/STAND_RONDE3.md` (rij "jelly-leon / golf 1: B03-017 ... en B03-009"); `<WERKMAP>/jelly-leon/docs/adr/ADR-0029-b03-017-prototype-een-dll-eigen-ed25519-host-sqlite.md`; `<WERKMAP>/jelly-leon/docs/adr/ADR-0030-b03-017-foutcatalogus-pipeline-en-1-mib-per-route.md`; `<WERKMAP>/jelly-leon/docs/adr/ADR-0034-b03-009-mediaguard-viewerclient-via-de-hub.md`; WP-JSON objecten `B03-017` en `B03-009` (Acceptatie)
- **Bouw:**
  1. A-VERKEN schrijft het dossier met `review_basis` = `945eb8113` (de commit direct voor `8a293727d`) en `<EIND-COMMIT>` = `cc3e82b4d` (of de HEAD na S-G1-15 en S-P2-800, met hun commits uitgezonderd in de opdracht aan de reviewers). Hij leest de CI-run van `cc3e82b4d` (`gh run view 42989190339 -R lvos04/jelly-leon --json jobs`; altijd met `-R lvos04/jelly-leon`, want jelly-leon is een fork en zonder `-R` kiest `gh` de upstream jellyfin/jellyfin) en noteert per job de uitkomst.
  2. R-TECH, R-VEILIG en R-HARDE-EIS lezen tegelijk het hele bereik (`git -C <WERKMAP>/jelly-leon diff 945eb8113..cc3e82b4d -- plugins tools docs deploy .github`) naast de ADR's en de WP-JSON-acceptatie. Zij krijgen de diff en de bron, niet de conclusie van de bouwer.
  3. R-TECH: elke ADR-regel heeft een test die kan falen (V-003); geen dubbele route en geen gedeelde singleton die per module verschilt (no-go Gate golf 1); OpenAPI-drift; de pluginproef kan zelf falen (`tools/jelly-leon/tests/test_proef_lib.py`).
  4. R-VEILIG: een eerste lezing van `Core/Hub/`, `Core/Http/`, `Core/Secrets/` en `Core/MediaGuard/`. De diepe beveiligingsreview van de Hub-koppeling is S-G1-12 (op het topmodel): R-VEILIG zet daar horende bevindingen in zijn rapport onder "voor S-G1-12" en laat ze in deze stap open.
  5. R-HARDE-EIS: de analyzer verbiedt schrijven in `jellyfin.db`, kijkgegevens en de bibliotheek; de UserDeleted-afhandeling (`c09698f09`) wist alleen eigen gegevens; de pluginproef (`9ebdfb15d`) vergelijkt de beschermde tabellen echt; de viewerclient kan MediaGuard niet bedienen.
  6. A-HERSTEL herstelt de bevindingen die niet bij een latere stap horen, elk met een test; bevindingen die een latere stap van dit bestand zelf oppakt (S-G1-10, S-G1-12, S-G1-14, S-G1-16, S-G1-18, S-G1-20, S-G1-50) zet hij met de stap-ID in zijn rapport; de regisseur geeft ze aan die stap mee onder `<BESLUITEN>`.
  7. A-HERSTEL legt vast met P-GIT en leest de CI van de eigen commit.
- **Tests (verplicht):** A-HERSTEL: T-JL-PLUGIN volledig; T-JL-TOOLS; T-JL-REGISTER; de analyzerproef zoals P-jelly-leon "4. Volledig", job `plugins`. Negatieve tests: elk herstel heeft een test die zonder het herstel faalt; R-TECH toont voor minstens de routetabel (`Core/RoutetabelTests.cs`) en de pluginproef (`test_proef_lib.py`) dat de test faalt op een opzettelijk fout invoerbestand.
- **Poort:** P-jelly-leon (Snel + jobs plugins en forkregels uit Volledig) + P-VEILIG + P-HARDE-EIS (leeslijst) + P-GIT + P-EERLIJK
- **Valkuilen:** V-006 (een groene nulmeting van de bouwer is geen bewijs); V-019 (bevinding buiten het mandaat: met stap-ID doorgeven); V-003; V-098; V-099; V-034
- **Bewijs:** geen statuswijziging in deze stap (de rijen B03-017, B03-009, JLT-64, JLT-65 en JLT-68 worden in S-G1-16, S-G1-10 en S-G1-50 geboekt). Voeg in EVIDENCE de rij `REVIEW-jelly-leon-golf-1` toe ("Bezig", "Unit-getest") met het commitbereik en het aantal bevindingen per reviewer. "NIET GEVALIDEERD (echte Hub); NIET GEVALIDEERD (echte NAS)."
- **Agents:** Ketenvorm B (reviewstap, `<WERKMAP>/.lokaal/plan/uit/AGENTEN.md#2.4 De vier ketenvormen`): A-VERKEN -> R-TECH + R-VEILIG (VERPLICHT) + R-HARDE-EIS (VERPLICHT) (tegelijk) -> A-HERSTEL -> R-EERLIJK (VERPLICHT)
- **Niveau:** standaard (R-VEILIG N4, R-HARDE-EIS N4; het topmodel voor de Hub-kern zit in S-G1-12, niet hier)
- **Stop en vraag als:** de CI-run van `cc3e82b4d` rood is op een job die de lokale poort groen meldt; een bevinding een wijziging van het contract vraagt; R-HARDE-EIS vindt dat de plugin kan schrijven in een beschermde tabel (dan stoppen alle golf-1-stappen tot de gebruiker gekozen heeft).

### S-G1-16 - Stand B03-017 vastzetten: werkboom schoon, poort groen, lokale image bewaren
- **Repo:** jelly-leon | **Fase:** P4 golf 1 (mag voor Gate P4-0) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (grote .NET-build, image-build, containers met een echte Jellyfin-server)
- **Werkpakketten en tests:** B03-017 (de bewijsrij en de lokale image; JLT-64, JLT-65 en JLT-68 worden in S-G1-10 geboekt)
- **Vooraf:** S-P40-10, S-G1-15, S-P2-800 (STAPPEN_P2.md) en S-G1-17 klaar (de werkboom van jelly-leon is dan schoon; de bevindingen van S-G1-17 met "voor S-G1-16" krijgt A-BOUW mee)
- **Al gedaan?** `git -C <WERKMAP>/jelly-leon status --short ; git -C <WERKMAP>/jelly-leon log --oneline @{u}.. ; docker image ls --format '{{.Repository}}:{{.Tag}}' | grep '^jelly-leon:lokaal-' ; grep -c '"B03-017"' <WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json` -> werkboom leeg, niets ongepusht, een image `jelly-leon:lokaal-<korte commit>` van de huidige HEAD en een rij `B03-017` in EVIDENCE: dan is de stap klaar. Bij de overdracht: laatste commit `cc3e82b4d` ("B03-009: MediaGuard-viewerclient via de Hub, zonder sleutel in Jelly Leon"), half werk van B03-018 in de werkboom (dat ruimt S-G1-15 op), geen lokale jelly-leon-image, geen rij `B03-017`. Staat er bij de start van deze stap nog niet vastgelegd werk: niet zelf afmaken, maar stoppen en melden (dan is S-G1-15, S-P2-800 of S-G1-17 niet af).
- **Lees eerst:** `<WERKMAP>/jelly-leon/docs/adr/ADR-0029-b03-017-prototype-een-dll-eigen-ed25519-host-sqlite.md#Besluit`; `<WERKMAP>/jelly-leon/docs/adr/ADR-0032-b03-017-analyzer-verboden-apis-en-generator-web-config.md#Grenzen (eerlijk)`; `<WERKMAP>/.lokaal/plan/uit/POORTEN.md#P-jelly-leon`; `<WERKMAP>/jelly-leon/deploy/allinone/Dockerfile`; WP-JSON object B03-017
- **Bouw:**
  1. Lees `df -h <WERKMAP>` en `docker system df` (alleen lezen). Onder 20 GB vrij: stop en meld het; ruim niets op (V-011, V-012).
  2. Draai T-JL-PLUGIN, T-JL-TOOLS en T-JL-REGISTER. Herstel alleen wat rood is door half werk; een rode test met een oorzaak buiten B03-017 meld je.
  3. Bouw de image zoals P-jelly-leon "4. Volledig", job image (achter docker-build.lock). Geef hem direct na de bouw een tweede tag: `docker tag jelly-leon:poort jelly-leon:lokaal-<korte commit>` (de korte commit uit `git rev-parse --short HEAD`). De poort ruimt `jelly-leon:poort` zelf op; de tag `jelly-leon:lokaal-...` blijft staan voor S-P40-20, S-P40-30, S-P40-40 en S-G1-10.
  4. Draai de imageproeven van T-JL-IMAGE tegen `jelly-leon:lokaal-<korte commit>`.
  5. Schrijf de tag en de image-ID (`docker image inspect --format '{{.Id}}' <tag>`) in `<WERKMAP>/.lokaal/ketens/S-G1-16/RAPPORT-A-BOUW.md`. Bestaat er een oudere `jelly-leon:lokaal-...`-tag van jezelf, verwijder dan alleen die ene tag met `docker image rm <tag>`.
  6. Voeg in EVIDENCE de rij `B03-017` toe (status "Bezig", validatie "Sim-getest") met wat er staat en wat nog open is: IStartupFilter-spike, export en import met `preview_hash`, haakmodule in de webclient, de modules WatchTogether, Recommendations, Subtitles en Segments. Zet dezelfde rij in `EXCEL_TAKEN.json`.
  7. Leg vast met P-GIT en lees de CI-uitkomst (POORTEN.md "0.5 CI-controle na elke push"); de stappen "Pluginproef op de Jelly Leon-image (JLT-68, JLT-64, JLT-65; Hub-simulator)" en "Pluginproef op JL_RUNTIME_IMAGE (...)" in `.github/workflows/jelly-leon-ci.yml` moeten gedraaid en groen zijn. De CI van de golf-1-vastleggingen van ronde 3 (`8a293727d` tot en met `cc3e82b4d`) is nooit beoordeeld: zoek de run van `cc3e82b4d` op met de volledige hash (`gh run list -R lvos04/jelly-leon -c "$(git -C <WERKMAP>/jelly-leon rev-parse cc3e82b4d)"`; `-c` vindt niets met een korte hash, en zonder `-R` kiest `gh` de upstream van de fork; op 2026-11-11 gaf dit run 42989190339) en noteer per job de uitkomst in je rapport (`gh run view <run-ID> -R lvos04/jelly-leon --json jobs`). Een rode job uit die tijd die op jouw commit groen is, noem je; een rode job die rood blijft is een bevinding.
  8. Review (door R-TECH, met de diff `git -C <WERKMAP>/jelly-leon show 776d7a4dd 5082f02a6` en ADR-0032; de generator staat in `deploy/allinone/web-config.mjs` met test `tools/jelly-leon/tests/test_web_config.py`, de analyzer onder `plugins/JellyLeon/analyzers/` met `tools/jelly-leon/analyzer_proef.py`): de analyzer (JL0001 tot en met JL0004, JL0009) en de generator voor `config.json` zijn nooit beoordeeld. R-TECH controleert dat elke regel uit ADR-0032 (kop "Besluit") een test heeft die kan falen (V-003) en dat de witte lijst `JellyLeon.AnalyzerUitzonderingen.txt` leeg is.
- **Tests (verplicht):** T-JL-PLUGIN; T-JL-TOOLS; T-JL-REGISTER; T-JL-IMAGE. Negatieve test: de analyzerproef zoals P-jelly-leon "4. Volledig", job `plugins` (de proefassembly `plugins/JellyLeon/analyzers/Jellyfin.Plugin.JellyLeon.VerbodenProef` bouwen in de SDK-container met `jl-dotnet.sh` en de bouwlog controleren met `python3 tools/jelly-leon/analyzer_proef.py --log <bouwlog> --exitcode <exitcode>`; NIET `--bouw`, want lokaal staat er geen `dotnet` op het PATH). Verplichte uitkomst: de bouw faalt en `analyzer_proef.py` geeft exitcode 0; slaagt de bouw van de proefassembly, dan is de stap niet klaar.
- **Poort:** P-jelly-leon (Volledig: jobs forkregels, server, plugins, image) + P-GIT + P-EERLIJK
- **Valkuilen:** V-074 (.NET alleen via `<WERKMAP>/.lokaal/jl-dotnet.sh`); V-015; V-022; V-088 (alleen de eigen tag opruimen); V-034
- **Bewijs:** `B03-017` -> "Bezig" (Sim-getest). "NIET GEVALIDEERD (echte NAS): de plugin draait nog op geen NAS; NIET GEVALIDEERD (echte Hub): de koppeling is alleen tegen de Hub-simulator getest."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-HARDE-EIS (tegelijk; R-HARDE-EIS VERPLICHT: de analyzer is de bouwgrens die schrijven in kijkgegevens, `jellyfin.db` en de bibliotheek verbiedt, en hij is nooit beoordeeld) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard (R-HARDE-EIS N4)
- **Stop en vraag als:** er minder dan 20 GB vrij is; er niet vastgelegd werk staat dat je niet begrijpt of dat tests rood maakt; de CI-stap van de pluginproef rood is terwijl de lokale tests groen zijn.

### S-G1-10 - Kern B03-017 controleren: prototype op fork en stock, JLT-68, JLT-64 en JLT-65
- **Repo:** jelly-leon | **Fase:** P4 golf 1 (mag voor Gate P4-0) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (containers met een echte Jellyfin-server, .NET-build)
- **Werkpakketten en tests:** B03-017, JLT-68, JLT-64, JLT-65, I24-24-03
- **Vooraf:** S-G1-16 klaar (lokale image); de P4-0-stappen van de baan jelly-leon tot en met S-P40-40
- **Al gedaan?** `python3 -c "import json;d=json.load(open('<WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json'));print([(r['id'],r.get('status')) for r in d if r.get('id') in ('JLT-64','JLT-65','JLT-68','I24-24-03')])" ; ls <WERKMAP>/jelly-leon/docs/platform-v2/test-evidence | grep -i pluginproef` -> vier rijen "Bezig" en twee rapporten (fork en stock) van de huidige commit: dan alleen de reviewers. Bij het schrijven van dit plan stond alleen JLT-64 in EVIDENCE (met de opmerking dat de upstream-testsuite zonder plugin draait) en lag er geen rapport onder `test-evidence`. Is de vorm van EVIDENCE anders dan een lijst: lees het bestand eerst.
- **Lees eerst:** `<WERKMAP>/jelly-leon/tools/jelly-leon/e2e/plugin_proef.py` (de kop van het bestand en `--help`); TEST-JSON rijen JLT-68, JLT-64, JLT-65; FASERING `#Gate golf 1`; `<WERKMAP>/jelly-leon/docs/adr/ADR-0029-b03-017-prototype-een-dll-eigen-ed25519-host-sqlite.md#Verificatie`; WP-JSON object B03-017 (veld Acceptatie)
- **Bouw:**
  1. Bouw de plugin (T-JL-PLUGIN) en zet de DLL in een lege map buiten de repo (de DLL staat na de bouw onder `plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/bin/Release/`; het exacte pad: ONBEKEND - eerst vaststellen met: `find plugins/JellyLeon -name Jellyfin.Plugin.JellyLeon.dll -path '*Release*'`).
  2. Fork: `flock <WERKMAP>/.lokaal/stack.lock nice -n 10 $PY tools/jelly-leon/e2e/plugin_proef.py --image <tag uit S-G1-16> --stock-image <stock op digest> --werkmap <map buiten de repo, geen tmpfs, minstens 2 GiB vrij> --rapport <rapport-fork.json>`.
  3. Stock: hetzelfde commando met `--image <stock op digest> --plugin-map <map met de DLL>` en een eigen rapportnaam. Dit is het bewijs "laadt op stock" en de run waarin de plugin weer is weggehaald.
  4. Loop de acceptatie van B03-017 na tegen de twee rapporten en schrijf per punt "gemeten", "niet gemeten" of "afwijking" in je rapport: twee modules in een assembly op fork en stock; elke `/connector/v1`-route precies een keer; module uit = routes en gedrag weg; zonder pin 401 `unauthorized` met reden `not_linked`; rol kind 403; herhaalde `jti` 401 `token_replayed`; groter dan 1 MiB geeft 413 per route; UserDeleted laat 0 GUID's achter; geheimen niet in `GET /Plugins/{id}/Configuration`, export of log.
  5. Wat "niet gemeten" is en binnen B03-017 valt: voeg de controle toe aan `plugin_proef.py` of aan PLUGINTEST en draai opnieuw. Wat bij een latere stap hoort (S-G1-12, S-G1-14, S-G1-18, S-G1-20) noteer je in het rapport met de stap erbij.
  6. Bewaar beide rapporten onder `docs/platform-v2/test-evidence/` met een naam die begint met `b03-017-pluginproef-`. Controleer dat er geen wachtwoord, sleutel of adres van de machine in staat.
  7. Werk EVIDENCE en `EXCEL_TAKEN.json` bij (rijen JLT-68, JLT-65 en I24-24-03 toevoegen; JLT-64 bijwerken: de plugin-geladen variant is nu gemeten) en leg vast met P-GIT.
- **Tests (verplicht):** T-JL-PLUGIN; T-JL-TOOLS (bevat `test_hub_sim.py` en `test_proef_lib.py`); de twee runs uit bouwpunt 2 en 3 (exitcode 0). Negatieve test: de pluginproef moet zelf kunnen falen: een unit-test in `tools/jelly-leon/tests/` die bewijst dat `proef_lib` een gewijzigde rij in een servertabel en een account-ID in ruwe bytes als fout meldt; ontbreekt die test, voeg hem toe.
- **Poort:** P-jelly-leon (Snel + jobs plugins en image uit Volledig) + P-GIT + P-EERLIJK + P-HARDE-EIS (leeslijst: de plugin schrijft niets in kijkgegevens)
- **Valkuilen:** V-001 (de Hub-simulator is ruimer dan de echte Hub); V-099; V-105; V-098 (Sim-geslaagd alleen als elk acceptatiepunt gemeten is); V-005 (een vergelijking over een lege bibliotheek telt niet)
- **Bewijs:** `JLT-68`, `JLT-64`, `JLT-65`, `I24-24-03` -> "Bezig"; Sim-geslaagd alleen voor de rijen waarvan elk onderdeel is uitgevoerd, anders Sim-getest met wat ontbreekt. "NIET GEVALIDEERD (echte Hub): JLT-68 draait tegen de Hub-simulator; NIET GEVALIDEERD (echte NAS); NIET GEVALIDEERD (hardware): echte clients."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-HARDE-EIS (tegelijk; R-HARDE-EIS VERPLICHT: JLT-65 bewijst dat de server- en kijkgegevens ongewijzigd blijven) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard (R-HARDE-EIS N4)
- **Stop en vraag als:** de pluginproef een verschil in een servertabel meldt dat niet uit de ruismeting komt (mogelijk raakt de plugin kijkgegevens: HARDE EIS); de plugin op stock niet laadt; een route dubbel geregistreerd is (no-go Gate golf 1).

### S-G1-12 - Hub-koppeling JL4: beveiligingsreview en herstel
- **Repo:** jelly-leon | **Fase:** P4 golf 1 (mag voor Gate P4-0) | **Omvang:** middel | **Moeilijkheid:** hoog | **Zwaar:** nee (alleen de plugin-build en de unit-tests achter docker-build.lock)
- **Werkpakketten en tests:** B03-017, JLT-68; contract-ID C1.3-JL-06
- **Vooraf:** S-G1-10 klaar
- **Al gedaan?** `ls <WERKMAP>/.lokaal/ketens/S-G1-12/RAPPORT-R-VEILIG.md ; python3 -c "import json;d=json.load(open('<WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json'));print([(r['id'],r.get('status')) for r in d if r.get('id')=='C1.3-JL-06'])"` -> een rapport van R-VEILIG zonder open bevindingen en `C1.3-JL-06` op "Bezig": dan is de stap klaar. Bij het schrijven van dit plan stond `C1.3-JL-06` op "Niet gestart", terwijl de code er al ligt (`Core/Hub/`); de review is nog niet gedaan.
- **Lees eerst:** `<WERKMAP>/jelly-leon/docs/adr/ADR-0031-b03-017-hub-koppeling-jl4-en-connectorgrenzen.md#Besluit`; `<WERKMAP>/jelly-leon/docs/platform-v2/PLATFORM_CONTRACTEN.md#4.2 Hub-JWT met gebruikerscontext` tot en met `#4.7 Fail-closed`; `<WERKMAP>/jelly-leon/docs/platform-v2/CONTRACT_1.3_CONFORMITEIT.md#9. jelly-leon (server-fork)` (punt C1.3-JL-06); BOUWPLAN `#10.4 Hub-koppeling (JL4)`; PLUGIN `Core/Hub/` (Ed25519.cs, HubKeySet.cs, HubPin.cs, HubPrincipal.cs, HubTokenValidator.cs, JtiStore.cs)
- **Bouw:**
  1. R-VEILIG leest eerst, voor er iets gebouwd wordt, `Core/Hub/`, `Core/Http/` (JlPipeline.cs, SessionAuthenticator.cs), `Core/Api/BeheerController.cs`, `Core/Connector/` en `Core/Secrets/SecretStore.cs` en schrijft bevindingen met ernst. De punten 2 tot en met 6 zijn de minimale vragenlijst.
  2. Token: `aud` is een string (een lijst wordt geweigerd, V-047); `alg` alleen EdDSA; `kid` moet in de gepinde set staan; `exp`, `nbf` en `iat` met de speling uit het contract; `token_use` gebruiker en dienst gescheiden; dienst-JWT alleen met de gepinde `service_id`; `kind` wint van elke andere rol.
  3. Replay: `jti` wordt persistent bewaard en overleeft een herstart; twee gelijktijdige verzoeken met dezelfde `jti` leveren precies een succes (V-044).
  4. Pinnen: `POST /media/v1/hub-link/verify` bewaart niets; `PUT /media/v1/hub-link` pint alleen met dezelfde vingerafdruk over alle policy-sleutels plus `service_id`; alleen een beheerder van de server; een kinderprofiel nooit. Voor de eerste pin kan niemand zonder beheerderssessie koppelen (V-092). Rotatie en verwijderen (`DELETE`) volgen alle paden (V-043).
  5. Opslag: `hub-pin.json` staat alleen in `/config/data/jelly-leon/secrets/` (map 0700, bestand 0600); een onleesbaar of beschadigd bestand geeft "niet gekoppeld" en geen 500 (V-045); niets van de set of van een token staat in de plugin-XML, een export of een logregel (V-094).
  6. Fail-closed: elke fout in de validatie eindigt in 401 of 403 in de contractvorm; `propose`, `apply`, `rollback` geven 501 `capability_unavailable`; connectorantwoorden bevatten alleen aantallen en ondoorzichtige ID's (V-054).
  7. A-BOUW herstelt de bevindingen, elk met een test in PLUGINTEST (`Core/HubTokenTests.cs`, `Core/HubSleutelTests.cs`, `Core/BeheerTests.cs`, `Core/ConnectorTests.cs`) en waar het een looptijdeigenschap is ook in `tools/jelly-leon/e2e/plugin_proef.py`.
  8. Werk `CONTRACT_1.3_CONFORMITEIT.md` (punt C1.3-JL-06), ADR-0031 (kop "Open punten voor het contract") en EVIDENCE bij; leg vast met P-GIT.
- **Tests (verplicht):** T-JL-PLUGIN met `--filter "FullyQualifiedName~Hub"` en daarna volledig; T-JL-TOOLS. Negatieve tests (elk een eigen test): `aud` als lijst; verkeerde `alg`; onbekende `kid`; verlopen token; dienst-JWT met een andere `service_id`; herhaalde `jti` na een herstart van de opslag; twee gelijktijdige verzoeken met dezelfde `jti`; `PUT` met een afwijkende vingerafdruk; `PUT` door een niet-beheerder en door een kinderprofiel; beschadigde `hub-pin.json`.
- **Poort:** P-jelly-leon (Snel + job plugins uit Volledig) + P-VEILIG + P-CONTRACT + P-GIT + P-EERLIJK
- **Valkuilen:** V-047; V-044; V-043; V-092; V-045; V-094; V-001 (de simulator mag niet ruimer zijn dan het contract)
- **Bewijs:** `C1.3-JL-06` -> "Bezig" (Sim-getest); `JLT-68` blijft "Bezig". "NIET GEVALIDEERD (echte Hub): pinnen en tokens zijn alleen met de Hub-simulator en met testsleutels gemeten; NIET GEVALIDEERD (echte NAS)."
- **Agents:** R-VEILIG (VERPLICHT, eerst: review van de bestaande code) -> A-BOUW -> R-TECH + R-VEILIG (tegelijk; R-VEILIG VERPLICHT op het herstel) -> A-HERSTEL -> R-EERLIJK. Geen A-VERKEN: het dossier is het eerste rapport van R-VEILIG.
- **Niveau:** R-VEILIG N5; A-BOUW en A-HERSTEL N4 (moeilijkheid hoog). Winst: dit is de authenticatiekern waarlangs de Hub straks elke Jelly Leon-route bereikt; een gemiste fout in de tokencontrole, de pin of de replaycache geeft iemand op het thuisnetwerk toegang tot alle connectorgegevens, en de eigen Ed25519-controle in C# heeft geen tweede paar ogen gehad.
- **Stop en vraag als:** R-VEILIG een bevinding heeft die een wijziging van het contract vraagt (melden; het contract is van ai-server-manager); de eigen Ed25519-implementatie een afwijking van RFC 8032 blijkt te hebben die niet met een test te bewijzen is; herstel een wijziging in de server buiten de plugin zou vragen.

### S-G1-14 - Foutcatalogus, 1 MiB per route, IStartupFilter-spike, health en events
- **Repo:** jelly-leon | **Fase:** P4 golf 1 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee (plugin-build en unit-tests; de spike draait een korte container achter stack.lock)
- **Werkpakketten en tests:** B03-017, JLT-68; contract-ID C1.3-JL-07
- **Vooraf:** S-G1-12 klaar; Gate P4-0
- **Al gedaan?** `ls <WERKMAP>/jelly-leon/docs/adr/ADR-0033-b03-017-spike-istartupfilter-1-mib-voor-authenticatie.md <WERKMAP>/jelly-leon/tools/jelly-leon/e2e/startupfilter_spike.py ; git -C <WERKMAP>/jelly-leon log --oneline --grep "IStartupFilter" | head -3 ; grep -rn "item_in_playback" <WERKMAP>/jelly-leon/plugins/JellyLeon/src | head -3` -> de spike is vastgelegd, ADR-0033 noemt de uitkomst en de code 423 `item_in_playback` bestaat: dan alleen de reviewers. Stand bij het schrijven van dit plan: een andere ronde heeft de spike gedaan en vastgelegd (commit `cdb6dc3bf`, ADR-0033: technisch geslaagd op stock 12.4, de laag blijft standaard uit achter de schakelaar `JELLYLEON_SPIKE_STARTUPFILTER=1`); de code `item_in_playback` kwam in de plugin nog niet voor; de punten 1, 2 en 4 tot en met 7 hieronder zijn niet als gedaan vastgesteld. Bouwpunt 3 is daarmee een controle, geen nieuwe spike.
- **Lees eerst:** `<WERKMAP>/jelly-leon/docs/adr/ADR-0030-b03-017-foutcatalogus-pipeline-en-1-mib-per-route.md#Besluit`; `<WERKMAP>/jelly-leon/docs/adr/ADR-0033-b03-017-spike-istartupfilter-1-mib-voor-authenticatie.md#Besluit` en `#Grenzen`; BOUWPLAN `#10.3 API-regels, foutcatalogus, idempotency, 1 MiB en OpenAPI` en `#10.10 Events (contract §7)`; `<WERKMAP>/jelly-leon/docs/platform-v2/PLATFORM_CONTRACTEN.md#5. Gemeenschappelijke API-regels` en `#7. Event-envelope`; PLUGIN `Core/Errors/Fouten.cs`, `Core/Http/JlPipeline.cs` en `Core/Http/JlStartupFilterSpike.cs` (het conformiteitspunt C1.3-JL-07 staat in `<WERKMAP>/jelly-leon/docs/platform-v2/CONTRACT_1.3_CONFORMITEIT.md#9. jelly-leon (server-fork)`)
- **Bouw:**
  1. Leg de foutcatalogus naast contract §5: elke code uit het werkpakket bestaat een keer (400 `idempotency_key_required` en `idempotency_key_invalid`, 422 `idempotency_key_reused`, 409 `idempotency_in_progress`, 422 `validation_error`, 412 `precondition_failed`, 428 `precondition_required`, 413 `payload_too_large`, 429 `rate_limited`, 501 `capability_unavailable`, 503 `<afhankelijkheid>_unavailable`) plus 423 `item_in_playback` uit contract 1.3. Vul aan wat ontbreekt, met een test in `Core/FoutcatalogusTests.cs`.
  2. 1 MiB per route: controleer dat elke route in `Core/Http/RouteTable.cs` de grens heeft (limiet op de route plus controle van `Content-Length`) en dat een verzoek zonder `Content-Length` (chunked) ook op 1 MiB stopt.
  3. Spike IStartupFilter (controle; de spike is gedaan, zie "Al gedaan?"): draai `tools/jelly-leon/e2e/startupfilter_spike.py` op stock en op de lokale image (opties: zie `--help`; de CI gebruikt `--image`, `--plugin-map`, `--werkmap` en `--rapport`) en leg de uitkomst naast ADR-0033 (kop "Meting"). Zet de laag niet standaard aan: ADR-0033 (kop "Besluit", punt 2) houdt de volgorde 401 voor 413 tot het contract anders zegt; de controle per route blijft altijd staan. Meet wel wat ADR-0033 (kop "Grenzen") open laat en met de schakelaar aan te meten is: een server met een basis-URL en een verzoek zonder `Content-Length`. Meld het contractpunt uit ADR-0033 (kop "Gevolgen") aan de regisseur; het besluit is van ai-server-manager.
  4. Een 413 komt bij de client aan als een antwoord in de contractvorm, niet als een verbroken verbinding (V-040): meet het met een echte HTTP-client in `plugin_proef.py`.
  5. Health: controleer de regels uit ADR-0031 punt 8 (volgorde `healthy` < `unknown` < `degraded` < `down`; een meting ouder dan 900 s wordt `unknown`; `worker` nooit gespeeld groen) en `max_age` volgens `PLATFORM_CONTRACTEN.md#6.2 Versheid`.
  6. Events: loop de eventnamen van BOUWPLAN §10.10 na tegen contract §7 (domein `media`, precies drie segmenten, werkwoord, veld `ernst`). Een naam die niet past (het conformiteitspunt noemt als voorbeeld `media.subtitle.rejected` en `media.quality_finding.detected`) hernoem je, of je laat hem bewust staan met een regel in een ADR.
  7. Werk het OpenAPI-bestand bij via de generator (`Core/OpenApiDriftTests.cs` bewaakt de drift), en `CONTRACT_1.3_CONFORMITEIT.md`, EVIDENCE en `EXCEL_TAKEN.json`; leg vast met P-GIT.
- **Tests (verplicht):** T-JL-PLUGIN (`--filter "FullyQualifiedName~Foutcatalogus"`, daarna volledig); T-JL-TOOLS; de pluginproef uit S-G1-10 opnieuw op de lokale image. Negatieve tests: een lichaam van 1 MiB plus 1 byte geeft op elke route 413 (ook chunked en ook zonder geldige sessie); een eventnaam met twee of vier segmenten wordt bij het starten geweigerd; een health-meting van 901 s oud is `unknown` en niet `healthy`.
- **Poort:** P-jelly-leon (Snel + job plugins uit Volledig) + P-CONTRACT + P-VEILIG + P-GIT + P-EERLIJK
- **Valkuilen:** V-039; V-040; V-066; V-051; V-050 (onverwacht invoertype mag geen 500 geven)
- **Bewijs:** `C1.3-JL-07` -> "Bezig" (Sim-getest); `B03-017` blijft "Bezig" met de uitkomst van de spike in de opmerking. "NIET GEVALIDEERD (echte Hub): de Hub-inbox heeft deze events nog niet ontvangen; NIET GEVALIDEERD (echte NAS)."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG (tegelijk; R-VEILIG VERPLICHT: de grens voor authenticatie en de foutvorm zijn van buiten bereikbaar) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard (R-VEILIG N4)
- **Stop en vraag als:** iemand de laag van de spike standaard aan wil zetten zonder contractbesluit (ADR-0033 verbiedt dat); de herhaling van de spike op de lokale image een andere uitkomst geeft dan ADR-0033 (melden met beide rapporten, niets aanpassen); een eventnaam hernoemen een wijziging in een andere repo vraagt (melden als Δ-HUB-2).

### S-G1-18 - Privacy: persoonsgegevensregister, UserDeleted, kinderprofiel
- **Repo:** jelly-leon | **Fase:** P4 golf 1 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee (alleen de plugin-build en de unit-tests achter docker-build.lock)
- **Werkpakketten en tests:** B03-017, B03-010, JLT-65, JLT-68
- **Vooraf:** S-G1-14 klaar; besluit BG-03 genomen, of de terugval uit hoofdstuk 3 (de breedste regel) geldt
- **Al gedaan?** `grep -n "BG-03" <WERKMAP>/jelly-leon/plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Core/Privacy/KidPolicy.cs | head -3 ; grep -c "\[Fact\]\|\[Theory\]" <WERKMAP>/jelly-leon/plugins/JellyLeon/tests/Jellyfin.Plugin.JellyLeon.Tests/Core/PrivacyTests.cs ; python3 -c "import json;d=json.load(open('<WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json'));print([(r['id'],r.get('status')) for r in d if r.get('id') in ('B03-010','B03-017')])"` -> `KidPolicy.cs` noemt het genomen besluit (of nog de terugval), de privacytests bestaan en beide rijen staan op "Bezig": dan alleen de reviewers. Bij het schrijven van dit plan bestonden `KidPolicy.cs` en `PrivacyService.cs` al, hanteerde `KidPolicy.cs` de breedste regel "zolang BG-03 open staat", en ontbraken de EVIDENCE-rijen `B03-010` en `B03-017`. Half werk: maak af wat er staat; begin niet opnieuw.
- **Lees eerst:** BOUWPLAN `#10.9 Opslag en gegevensbescherming` (rijen Persoonsgegevens, Wezen, Kinderen, Privacy); `<WERKMAP>/jelly-leon/docs/adr/ADR-0020-b03-opslag-en-gegevensbescherming.md#Besluit`; WP-JSON objecten `B03-010` en `B03-017` (Uitvoering en Acceptatie); `<WERKMAP>/.lokaal/plan/uit/BESLUITEN_EN_BLOKKADES.md#2.1 NU` (BG-03); PLUGIN `Core/Privacy/` (KidPolicy.cs, PrivacyService.cs) en `Core/Modules/IJellyLeonModule.cs`
- **Bouw:**
  1. Register: elke module levert haar register van persoonsgegevens via `IJellyLeonModule`; `GET /media/v1/privacy/register` toont per tabel het doel, de bewaartermijn en wat er bij verwijderen gebeurt (wissen of pseudonimiseren). Een module met een tabel die een gebruikers-ID bevat maar niet in het register staat, laat een test falen. Bron: BOUWPLAN `#10.9 Opslag en gegevensbescherming`.
  2. UserDeleted: een afhandeling in `Core/Privacy/PrivacyService.cs` roept voor elke module `VerwijderGebruiker` aan. Controleer dat ook de gedeelde opslag van Core meedoet (outbox, idempotency, `jti`-opslag, audit) en dat `TelGebruiker` daarna voor elke module 0 geeft.
  3. De UserDeleted-test zoekt de GUID ook in de ruwe databasebestanden (inclusief `-wal` en `-shm`) en in de featurecache-map, in de schrijfwijzen met en zonder streepjes en in hoofd- en kleine letters. Bron: WP-JSON `B03-017` (Acceptatie).
  4. Bewaartermijnen: een opruimtaak per registerrij met een klok die in de test te sturen is. Menselijk werk (correcties, beoordelingen, bevestigde regels) wordt nooit automatisch gewist; daarvoor geldt pseudonimiseren. Het zout voor pseudonimiseren komt uit de geheimenmap (S-G1-20 controleert de map zelf).
  5. Kinderprofiel: een definitie `IsKid(user)` in `Core/Privacy/KidPolicy.cs`, gebruikt door elke module. Volg BG-03 als het genomen is; staat het open, dan blijft de breedste regel staan (kind zodra `MaxParentalRatingScore`, `BlockedTags` of `AccessSchedules` gezet is) en noemt het rapport dat. Een kind krijgt op een item dat het niet mag zien hetzelfde 404 als "bestaat niet".
  6. Hub-rol `kind`: 403 op elke `/connector/v1`-route; een test loopt de hele routetabel af (`Core/Http/RouteTable.cs`), zodat een nieuwe route er niet buiten kan vallen.
  7. Een eigenschapstest over de rollenmatrix (beheerder, gewone gebruiker, kind volgens elke regel, Hub-rollen): `IsKid` geeft voor elke module dezelfde uitkomst. Bron: WP-JSON `B03-010` (Acceptatie).
  8. Werk EVIDENCE en `EXCEL_TAKEN.json` bij (rijen `B03-010`, `B03-017`) en leg vast met P-GIT. Het deel "inlog op streamroutes" van B03-010 hoort bij golf 3 en staat in het zusterbestand `<WERKMAP>/.lokaal/plan/uit/STAPPEN_P4_GOLF3_4.md` (als dat bestand er nog niet is: melden, niet zelf bouwen).
- **Tests (verplicht):** T-JL-PLUGIN met `--filter "FullyQualifiedName~Privacy"`, daarna volledig; T-JL-TOOLS; de pluginproef uit S-G1-10 opnieuw op de lokale image (JLT-65-deel: na het verwijderen van een gebruiker 0 GUID's). Negatieve tests: een module zonder registerregel voor een tabel met een gebruikers-ID faalt; een kind dat via een module-route een geblokkeerd item opvraagt krijgt 404 en geen titel in het antwoord of in een event; de Hub-rol `kind` krijgt 403 op elke connectorroute; een verwijderde gebruiker is niet terug te vinden in een export.
- **Poort:** P-jelly-leon (Snel + job plugins uit Volledig) + P-VEILIG + P-HARDE-EIS + P-GIT + P-EERLIJK
- **Valkuilen:** V-005 (een test over een lege database telt niet: vul eerst elke module-DB met rijen van de gebruiker); V-003; V-055; V-102; V-115
- **Bewijs:** `B03-010` -> "Bezig" (Sim-getest; opmerking: alleen het deel IsKid, de streamroutes volgen in golf 3); `B03-017` blijft "Bezig"; `JLT-65` en `JLT-68` blijven "Bezig". "NIET GEVALIDEERD (echte NAS): de regels zijn alleen op een synthetische gebruikersset gemeten; de echte gebruikers en kinderprofielen van het huishouden zijn niet beoordeeld."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG + R-HARDE-EIS (tegelijk; R-VEILIG VERPLICHT: privacy en rechten; R-HARDE-EIS VERPLICHT: gebruikers en het verbod om menselijk werk automatisch te wissen) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard (R-VEILIG N4, R-HARDE-EIS N4)
- **Stop en vraag als:** BG-03 open staat en de breedste regel een profiel als kind zou aanmerken dat de gebruiker als volwassene bedoelt (dat is juist het besluit: leg het voor als keuzemenu); `IsKid` niet zonder wijziging in de server buiten de plugin te bepalen is; een bewaartermijn in het BOUWPLAN ontbreekt voor een tabel die bestaat (niet zelf een termijn kiezen).

### S-G1-20 - Geheimenmap, mountcontrole, wezenbreker, spoorsleutel, export en import
- **Repo:** jelly-leon | **Fase:** P4 golf 1 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee (plugin-build en unit-tests; de pluginproef draait een korte container achter stack.lock)
- **Werkpakketten en tests:** B03-017, JLT-65, JLT-68
- **Vooraf:** S-G1-18 klaar
- **Al gedaan?** `grep -rn "preview_hash" <WERKMAP>/jelly-leon/plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon --include=*.cs | grep -v "/obj/\|/bin/" | head -5 ; grep -n "Importeer\|Exporteer" <WERKMAP>/jelly-leon/plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Core/Modules/IJellyLeonModule.cs ; ls <WERKMAP>/jelly-leon/plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Core/Secrets <WERKMAP>/jelly-leon/plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Core/Media` -> er is een import naast `Exporteer` en `preview_hash` komt in de code voor: dan alleen de reviewers. Bij het schrijven van dit plan bestonden `SecretStore.cs`, `MountCheck.cs`, `OrphanBreaker.cs` en `StreamKey.cs`, had `IJellyLeonModule` alleen `Exporteer()` en kwam `preview_hash` nergens in de code voor: import en `preview_hash` zijn dus nog te bouwen; de andere vier onderdelen zijn controle en aanvulling.
- **Lees eerst:** BOUWPLAN `#10.9 Opslag en gegevensbescherming` (rijen Mount, Migraties, Back-up, Geheimen, Wezen) en `#10.12 Stabiele spoorsleutel`; `<WERKMAP>/jelly-leon/docs/adr/ADR-0020-b03-opslag-en-gegevensbescherming.md#Besluit`; `<WERKMAP>/jelly-leon/docs/adr/ADR-0031-b03-017-hub-koppeling-jl4-en-connectorgrenzen.md#Besluit` (punt 8, check `media_mount`); `<WERKMAP>/jelly-leon/docs/adr/ADR-0029-b03-017-prototype-een-dll-eigen-ed25519-host-sqlite.md#Besluit`; PLUGIN `Core/Storage/JlPaths.cs`
- **Bouw:**
  1. Geheimenmap (`Core/Secrets/SecretStore.cs`): `/config/data/jelly-leon/secrets` met map 0700 en bestanden 0600, eigenaar 568; bij de eerste start aangemaakt, nooit overschreven. Een map of bestand met ruimere rechten of een andere eigenaar geeft "geheim niet beschikbaar" en een health-reden, geen stille reparatie en geen 500. Er komt geen MediaGuard-sleutel in deze map: BG-04 legt de MediaGuard-gegevens via de Hub (zie S-G1-50).
  2. Lekcontrole: geen geheim in `GET /Plugins/{id}/Configuration`, in een export of in een logregel. Breid de logscan in `tools/jelly-leon/e2e/plugin_proef.py` uit met de testgeheimen die de proef zelf aanmaakt (zoek op de waarde, niet op een veldnaam).
  3. Mountcontrole (`Core/Media/MountCheck.cs`): lezen uit `/proc/self/mountinfo`, zonder proefschrijven. Een schrijfbaar gekoppelde mediamap zet de check `media_mount` en schakelt elke batchmodule uit; "onbekend" is nooit in orde. Let op het verschil in de bronnen: ADR-0031 zegt `degraded`, het werkpakket zegt "health down", het BOUWPLAN zegt "status rood". Bouw niet om: meld het verschil in het rapport (zie "Stop en vraag als").
  4. Wezenbreker (`Core/Media/OrphanBreaker.cs`): worden in een scan meer dan 5 % of meer dan 50 items wees, dan bevriest het opruimen, wordt de status `degraded` en gaat er een incident-event uit. Test beide drempels op de grens (precies 5 % en 50 items: niet bevriezen; een meer: wel).
  5. Spoorsleutel (`Core/Media/StreamKey.cs`, JSON-veld `track_key`): dezelfde sleutel voor hetzelfde spoor na een herscan, na een andere spoorvolgorde en na een rename van het bestand; een test met vaste voorbeelden bewaakt dat de sleutel niet ongemerkt verandert. Bron: BOUWPLAN `#10.12 Stabiele spoorsleutel`.
  6. Export en import per module: `Exporteer()` krijgt een `preview_hash` over de inhoud; een import (nieuw in `IJellyLeonModule` en `ModuleBasis`) werkt in twee stappen: eerst een voorbeeld met aantallen en `preview_hash`, daarna toepassen met dezelfde hash. Voor het toepassen maakt de module de back-upkopie van haar database zoals bij een migratie. Een export bevat geen geheimen en geen gegevens van een verwijderde gebruiker.
  7. Schrijfbereik: elk nieuw schrijfpad loopt via `InternalWriteScope` en `JlPaths.MagSchrijven`; de analyzer blijft 0 treffers geven en de proefassembly faalt nog steeds (analyzerproef zoals P-jelly-leon "4. Volledig", job `plugins`; niet met `--bouw`, want lokaal staat er geen `dotnet` op het PATH).
  8. Werk het OpenAPI-bestand bij als er routes bij komen (drifttest), en EVIDENCE; leg vast met P-GIT.
- **Tests (verplicht):** T-JL-PLUGIN met `--filter "FullyQualifiedName~Opslag"` en `--filter "FullyQualifiedName~Media"`, daarna volledig; T-JL-TOOLS; de analyzerproef zoals P-jelly-leon "4. Volledig", job `plugins` (bouwlog uit de SDK-container, `analyzer_proef.py --log ... --exitcode ...`); de pluginproef uit S-G1-10 opnieuw. Negatieve tests: een import met een andere `preview_hash` dan het voorbeeld wordt geweigerd (409 of 412 volgens de foutcatalogus) en wijzigt niets; een import van een export van een nieuwere schemaversie wordt geweigerd; een geheimenbestand met rechten 0644 wordt niet gebruikt; een symbolische koppeling in de geheimenmap of als exportdoel wordt geweigerd; een schrijfbare mediamap schakelt de batchmodules uit.
- **Poort:** P-jelly-leon (Snel + job plugins uit Volledig) + P-VEILIG + P-HARDE-EIS + P-GIT + P-EERLIJK
- **Valkuilen:** V-045; V-053; V-083; V-085 (een export is een back-up: niet voor iedereen leesbaar); V-094; V-095; V-084 (de proef leest bestanden van 568 vanaf de host)
- **Bewijs:** `B03-017` blijft "Bezig" (opmerking: import met `preview_hash` gebouwd en Sim-getest); `JLT-65` blijft "Bezig". "NIET GEVALIDEERD (echte NAS): eigenaar en rechten van de geheimenmap en de alleen-lezen koppeling van de mediamap zijn alleen in een wegwerpcontainer gemeten, niet op de dataset van de NAS; de dekking van de exports door de back-up (Δ-HUB-3) bestaat nog niet."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG (tegelijk; R-VEILIG VERPLICHT: geheimen, rechten en import van buiten) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard (R-VEILIG N4)
- **Stop en vraag als:** de bronnen over de schrijfbare mediamap niet met elkaar te verenigen zijn en de gate een keuze vraagt (`degraded` of `down`): de regisseur legt dat voor, de bouwer kiest niet; een import alleen kan door rechtstreeks in `jellyfin.db` te schrijven (verboden); de geheimenmap op de ontwikkelmachine niet als 568 aan te maken is zonder de container als root te starten.

### S-G1-30 - Analysewerker in de image
- **Repo:** jelly-leon | **Fase:** P4 golf 1 | **Omvang:** groot | **Moeilijkheid:** gewoon | **Zwaar:** ja (image-build achter docker-build.lock; proeven achter stack.lock)
- **Werkpakketten en tests:** B03-018
- **Vooraf:** S-G1-20 klaar; Gate P4-0
- **Al gedaan?** `grep -n "/opt/jelly-leon/python\|require-hashes" <WERKMAP>/jelly-leon/deploy/allinone/Dockerfile | head ; ls <WERKMAP>/jelly-leon/deploy/allinone ; grep -n -i "werker\|worker\|sbom\|pip-audit" <WERKMAP>/jelly-leon/.github/workflows/jelly-leon-ci.yml <WERKMAP>/jelly-leon/.github/workflows/upstream-sync.yml | head` -> de Dockerfile bevat de interpreter onder `/opt/jelly-leon/python` met `--require-hashes`, er is een SBOM-stap en een smoketest in CI: dan alleen de meting van de imagegroei controleren en de reviewers. Bij het schrijven van dit plan stond er niets van de werker in de Dockerfile en niets in CI: de stap begint bij nul.
- **Lees eerst:** `<WERKMAP>/jelly-leon/docs/adr/ADR-0017-b03-analysewerker-en-bestandspas.md#Besluit` en `#Verificatie`; BOUWPLAN `#10.6 Analysewerker en bestandspas`; WP-JSON object `B03-018` (deel (a) en Acceptatie); `<WERKMAP>/jelly-leon/deploy/allinone/Dockerfile`; `<WERKMAP>/jelly-leon/docs/adr/ADR-0023-b03-licenties.md`
- **Bouw:**
  1. Meet eerst de grootte van de lokale image uit S-G1-16 (`docker image inspect <tag> --format '{{.Size}}'`) en schrijf die in het rapport: dat is de nulmeting voor de groei. De grens zelf is: ONBEKEND - eerst vaststellen met: `grep -n -i "grens\|groei" <WERKMAP>/jelly-leon/docs/adr/ADR-0017-b03-analysewerker-en-bestandspas.md`. ADR-0017 zegt "grens vastgelegd bij de eerste meting": leg de grens in deze stap als voorstel in de ADR vast en laat de regisseur hem bevestigen.
  2. Dockerfile: een vastgezette interpreter onder `/opt/jelly-leon/python` (de basisimage heeft geen python3, zie ADR-0017 "Context"), gevuld met `pip install --no-deps --require-hashes` uit een requirements-bestand met hashes in de repo. Niet in de image: torch, transformers, ctranslate2, auditok. ffsubsync zonder auditok (`--vad webrtc`).
  3. De werker zelf als pakket onder een eigen map in de repo (naam en plaats kiest A-VERKEN aan de hand van `tools/jelly-leon/fork_paths.txt`; een nieuw pad hoort in dat register): een langlevend proces dat JSON-berichten leest en per taak een tool start met een argumentenlijst, nooit via een shell. In deze stap alleen het skelet met de taken `ping` en `versies`; socket en bewaking volgen in S-G1-32.
  4. Opdrachtbouwer: weigert `--serialize-speech` en elk uitvoerpad in een bibliotheekmap; ffmpeg alleen naar `-f null` of een pipe. Bron: ADR-0017 "Besluit" punt 5.
  5. SBOM, licentie-inventaris en `pip-audit` als CI-stap; de SBOM komt als bestand in de image en als artefact uit CI. Leg nieuwe licenties vast volgens ADR-0023 en in `deploy/allinone/NOTICE.jelly-leon`.
  6. Smoketest in de image, zonder netwerk (`--network none`): elke tool start en meldt zijn versie, en die versies zijn gelijk aan de SBOM. Neem de test op in `.github/workflows/jelly-leon-ci.yml` (job image) en als tool-smoketest in `.github/workflows/upstream-sync.yml`.
  7. Meet de image opnieuw en leg groei en grens vast in ADR-0017 (kop "Verificatie") en in EVIDENCE. Rechten: alles onder `/opt/jelly-leon` is van root en alleen-lezen voor 568; de werker draait als 568.
  8. Leg vast met P-GIT (elk bestand bij naam).
- **Tests (verplicht):** T-JL-IMAGE (bouwen achter docker-build.lock; daarna de proeven); de smoketest: `flock <WERKMAP>/.lokaal/stack.lock nice -n 10 docker run --rm --network none --user 568:568 <tag> <smoketest-commando uit deze stap>`; T-JL-TOOLS; T-JL-REGISTER. Negatieve tests: de SBOM-controle faalt op een image waarin `auditok`, `torch` of `ctranslate2` staat (bewijs het met een testbestand, niet door ze te installeren); de opdrachtbouwer weigert `--serialize-speech` en een uitvoerpad onder een bibliotheekmap; een requirements-regel zonder hash laat de build falen.
- **Poort:** P-jelly-leon (Volledig: jobs forkregels, manifest, image) + P-INSTALLATIE + P-VEILIG + P-GIT + P-EERLIJK; daarna "0.5 CI-controle na elke push"
- **Valkuilen:** V-012 (vrije schijfruimte voor de build: onder 20 GB vrij niet starten); V-014; V-011; V-088 (ruim alleen eigen testimages op, bij naam); V-035 (interpreter en pakketten op digest of hash, geen zwevende tag); V-028; V-083; V-033
- **Bewijs:** nieuwe rij `B03-018` -> "Bezig" (Sim-getest; opmerking: alleen deel (a) werker in de image; groei van de image met getal). "NIET GEVALIDEERD (echte NAS): de image met de werker is niet op TrueNAS gestart; NIET GEVALIDEERD (hardware): A310 en UHD 770."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-MANIFEST + R-VEILIG (tegelijk; R-MANIFEST VERPLICHT: Dockerfile en inhoud van de image; R-VEILIG VERPLICHT: nieuwe pakketten en een nieuw proces in de image) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard (R-VEILIG N4)
- **Stop en vraag als:** de groei van de image boven de voorgestelde grens uitkomt; een pakket een licentie heeft die ADR-0023 niet toestaat; een vastgezette interpreter alleen te krijgen is door een pakketbron toe te voegen die de build nu niet gebruikt; `pip-audit` een kwetsbaarheid meldt waarvoor geen herstelde versie bestaat.

### S-G1-32 - Werkerbewaker en socket
- **Repo:** jelly-leon | **Fase:** P4 golf 1 | **Omvang:** groot | **Moeilijkheid:** hoog | **Zwaar:** ja (image-build achter docker-build.lock; de herhaalproef achter stack.lock)
- **Werkpakketten en tests:** B03-018, JLT-68
- **Vooraf:** S-G1-30 klaar
- **Al gedaan?** `ls -R <WERKMAP>/jelly-leon/plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Core/Werker ; grep -rn "werker_niet_beschikbaar\|SO_PEERCRED\|SUBREAPER" <WERKMAP>/jelly-leon/plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon --include=*.cs | grep -v "/obj/\|/bin/" | head` -> `Core/Werker` bevat naast `IWerker.cs` een bewaker en een socketclient, en de health-check `worker` meet echt: dan alleen de herhaalproef en de reviewers. Bij de overdracht stond in `Core/Werker` alleen `IWerker.cs` (half werk van ronde 3, met de standaard `GeenWerker` in `PluginServiceRegistrator.cs`) en gaf de check `worker` vast `unknown` met reden `werker_niet_beschikbaar` (ADR-0031 punt 8). Gebruik de map `Core/Werker`, niet `Core/Worker`: de analyzer-regel JL0004 laat processtarts alleen toe in de namespace `Core.Werker` (ADR-0032, kop "Besluit").
- **Lees eerst:** `<WERKMAP>/jelly-leon/docs/adr/ADR-0017-b03-analysewerker-en-bestandspas.md#Besluit` (punten 1 en 2); BOUWPLAN `#10.6 Analysewerker en bestandspas`; WP-JSON object `B03-018` (deel (a) en Acceptatie "Werker"); `<WERKMAP>/jelly-leon/docs/adr/ADR-0031-b03-017-hub-koppeling-jl4-en-connectorgrenzen.md#Besluit` (punt 8, check `worker`); PLUGIN `Core/Storage/JlPaths.cs` (schrijfbereik `/run/jelly-leon/`)
- **Bouw:**
  1. Bewaker in `Core/Werker` (naast de bestaande `IWerker`; vervang de standaard `GeenWerker` alleen als de bewaker er is): start de werker als kindproces van de server, met herstart met backoff en een health-ping. Staat geen module aan die een jobtype levert, dan start de werker niet.
  2. Socket: een unix-socket onder `/run/jelly-leon/` (map 0700, eigenaar 568); de werker controleert de andere kant met `SO_PEERCRED` en weigert elke andere UID. Bestaat `/run/jelly-leon/` niet of is hij niet van 568, dan start de werker niet en zegt de check `worker` waarom.
  3. Berichten: JSON, hooguit 1 MiB per bericht, met een lengtekop; een groter of ongeldig bericht sluit de verbinding en geeft een foutcode uit de catalogus, geen crash van de server.
  4. Werkerkant: `PR_SET_CHILD_SUBREAPER`; elke tool in een eigen procesgroep; stoppen is de hele groep (SIGTERM, na 5 s SIGKILL). Bij het stoppen van de server stopt de werker met al zijn kinderen.
  5. Health: de check `worker` gaat van vast `unknown` naar een echte meting (laatste geslaagde ping met tijdstip); ouder dan 900 s wordt weer `unknown` (dezelfde regel als de andere checks).
  6. Herhaalproef als script in `tools/jelly-leon/e2e/` (naast `plugin_proef.py`, met `proef_lib.py`): 100 keer de werker hard stoppen terwijl een tool loopt; meet per keer de hersteltijd en scan `/proc` in de container op wees-processen en zombies. Eis: herstart binnen 10 s, 0 wezen, 0 zombies. Het rapport komt in `docs/platform-v2/test-evidence/`.
  7. Neem de herhaalproef (met een kleiner aantal herhalingen, door A-VERKEN voor te stellen) op in `.github/workflows/jelly-leon-ci.yml`; de volle 100 herhalingen draaien lokaal en het rapport noemt het aantal eerlijk.
  8. Werk EVIDENCE bij en leg vast met P-GIT.
- **Tests (verplicht):** T-JL-PLUGIN met `--filter "FullyQualifiedName~Werker"`, daarna volledig; T-JL-IMAGE; de herhaalproef: `flock <WERKMAP>/.lokaal/stack.lock nice -n 10 $PY tools/jelly-leon/e2e/<herhaalproef uit punt 6> --image <tag> --herhalingen 100 --rapport <pad>` (de opties legt A-BOUW vast en zet ze in `--help`). Negatieve tests: een verbinding van een andere UID wordt geweigerd; een bericht van 1 MiB plus 1 byte wordt geweigerd; een tool die SIGTERM negeert is na 5 s weg (SIGKILL) en laat geen kind achter; een taak met een shell-teken in een argument wordt letterlijk doorgegeven en niet uitgevoerd.
- **Poort:** P-jelly-leon (Volledig: jobs plugins en image) + P-VEILIG + P-GIT + P-EERLIJK; daarna "0.5 CI-controle na elke push"
- **Valkuilen:** V-083; V-051 (de check `worker` mag niet "gezond" zeggen zonder verse ping); V-032 (een herhaalproef die soms faalt is een bevinding, geen reden voor een retry); V-057; V-008; V-009; V-087
- **Bewijs:** `B03-018` blijft "Bezig" (opmerking: bewaker en socket; hersteltijd en aantal herhalingen met getal). "NIET GEVALIDEERD (echte NAS): `/run/jelly-leon/` en het gedrag bij een herstart van de app zijn niet op TrueNAS gemeten."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG (tegelijk; R-VEILIG VERPLICHT: een lokaal socket met rechtencontrole en het starten van processen) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4; verder standaard
- **Stop en vraag als:** `PR_SET_CHILD_SUBREAPER` of `SO_PEERCRED` in de container niet werkt zonder extra rechten (capabilities) in het manifest; `/run` in de image geen plek is waar 568 mag schrijven en de oplossing een wijziging van het manifest vraagt (dan eerst R-MANIFEST en S-G1-70); de herhaalproef niet stabiel 0 wezen haalt.

### S-G1-34 - Bestandspas en featurecache
- **Repo:** jelly-leon | **Fase:** P4 golf 1 | **Omvang:** groot | **Moeilijkheid:** gewoon | **Zwaar:** ja (image-build achter docker-build.lock; de meting met ffmpeg in een container achter stack.lock)
- **Werkpakketten en tests:** B03-018, JLT-65
- **Vooraf:** S-G1-32 klaar
- **Al gedaan?** `grep -rn -i "chromaprint\|silencedetect\|ebur128\|featurecache\|kop-hash\|kop_hash" <WERKMAP>/jelly-leon --include=*.py --include=*.cs -l | grep -v "/obj/\|/bin/\|/.venv/" | head ; ls <WERKMAP>/jelly-leon/docs/platform-v2/test-evidence | grep -i "bestandspas\|audiopas"` -> de werker kent een taak voor de bestandspas, er is een cache op bestandsvingerafdruk en er ligt een meetrapport met gelezen bytes: dan alleen de reviewers. Bij het schrijven van dit plan bestond hier niets van.
- **Lees eerst:** BOUWPLAN `#10.6 Analysewerker en bestandspas` (alinea "Een bestandspas per bestand"); `<WERKMAP>/jelly-leon/docs/adr/ADR-0017-b03-analysewerker-en-bestandspas.md#Besluit` (punten 4, 5 en 6); WP-JSON object `B03-018` (deel (b) en Acceptatie "Audiopas"); BOUWPLAN `#10.13 Echt mediacorpus`; PLUGIN `Core/Storage/JlPaths.cs`
- **Bouw:**
  1. Werkertaak "bestandspas": een leespas per bestand die de audiokenmerken maakt die F3, F4 en F6 nodig hebben (chromaprint, 16 kHz-spraakkaart met VAD, `silencedetect`, `astats`, `ebur128`, cue-extractie). De beeldsignalen in dezelfde decode horen bij F4 niveau 2 en worden hier alleen als uitbreidingspunt voorbereid, niet gebouwd.
  2. ffmpeg schrijft alleen naar `-f null` of een pipe; de spraakreeks maakt de werker zelf in `/cache`. `ffsubsync --serialize-speech` blijft verboden (de opdrachtbouwer uit S-G1-30 weigert het).
  3. Featurecache onder `/cache/jelly-leon/` op de bestandsvingerafdruk (pad, grootte, mtime, kop-hash). De cache is weggooibaar: een verwijderde of beschadigde cache geeft opnieuw rekenen, geen fout. De cache bevat geen titels en geen gebruikersgegevens.
  4. Meetpunt: gelezen bytes per item per functie uit `/proc/<pid>/io`, in het resultaat van de taak en in het meetrapport.
  5. Pluginkant: een dienst in Core waar modules de kenmerken van een item opvragen; zijn ze er niet, dan vraagt de dienst een taak aan bij de planner (S-G1-36) en geeft "nog niet beschikbaar" terug. Modules starten zelf nooit een tool.
  6. Meting op het corpus (de corpusgenerator van HARNAS; kies de kleinste set die audio in meerdere codecs heeft): voor elk bestand gelezen bytes ten opzichte van de bestandsgrootte, met alle drie de afnemers gesimuleerd. Eis: hooguit 1,1 keer de bestandsgrootte. Rapport in `docs/platform-v2/test-evidence/`.
  7. Controle "geen schrijfpad in een mediamap": het corpus is alleen-lezen gekoppeld en de sha256 van het hele corpus is voor en na gelijk.
  8. Werk EVIDENCE bij en leg vast met P-GIT.
- **Tests (verplicht):** T-JL-PLUGIN volledig; T-JL-HARNAS; T-JL-IMAGE; de meting uit punt 6 achter `flock <WERKMAP>/.lokaal/stack.lock nice -n 10` (het commando legt A-BOUW vast in het rapport en in `--help`). Negatieve tests: een beschadigd audiobestand geeft een taakfout met een code en geen hangende werker; een bestand dat tijdens de pas verandert (andere mtime) maakt de cache-invoer ongeldig; een poging om een uitvoerpad onder de mediamap mee te geven wordt geweigerd; een tweede afnemer voor hetzelfde bestand leest 0 extra bytes van de media.
- **Poort:** P-jelly-leon (Volledig: jobs plugins, image, b03-harnas) + P-HARDE-EIS (media alleen lezen) + P-GIT + P-EERLIJK
- **Valkuilen:** V-005 (een meting over een leeg corpus telt niet); V-013 (`/tmp` is gedeeld werkgeheugen: gebruik de werkmap van de proef); V-012; V-057; V-077; V-095
- **Bewijs:** `B03-018` blijft "Bezig" (opmerking: deel (b), verhouding gelezen bytes met getal en het aantal bestanden). "NIET GEVALIDEERD (echte NAS): gemeten op het synthetische corpus van de ontwikkelmachine, niet op de eigen bibliotheek en niet op de schijven van de NAS."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-HARDE-EIS (tegelijk; R-HARDE-EIS VERPLICHT: de pas leest de mediabibliotheek en mag er niets in schrijven) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard (R-HARDE-EIS N4)
- **Stop en vraag als:** een van de tools (chromaprint, VAD) niet in de image van S-G1-30 zit en toevoegen de imagegrens overschrijdt; de eis van 1,1 keer niet haalbaar is zonder de kenmerken van een functie te laten vervallen; het corpus bestanden met een beperkende licentie zou vragen (BG-37: alleen lokaal, nooit in de repo).

### S-G1-36 - Globale batchplanner
- **Repo:** jelly-leon | **Fase:** P4 golf 1 | **Omvang:** groot | **Moeilijkheid:** hoog | **Zwaar:** ja (de pauzemeting draait een container met afspelende sessies achter stack.lock)
- **Werkpakketten en tests:** B03-018, JLT-66
- **Vooraf:** S-G1-34 klaar
- **Al gedaan?** `ls -R <WERKMAP>/jelly-leon/plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Core/Planner ; grep -rn "storage.read_failed\|PlaybackStart" <WERKMAP>/jelly-leon/plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Core --include=*.cs | grep -v "/obj/\|/bin/" | head ; ls <WERKMAP>/jelly-leon/docs/platform-v2/test-evidence | grep -i planner` -> `Core/Planner` bevat de planner, het event `media.storage.read_failed` bestaat en er ligt een rapport met minstens 20 pauzemetingen: dan alleen de reviewers. Bij de overdracht stond in `Core/Planner` het half werk van ronde 3 (BatchPlanner.cs, CgroupMarge.cs, ISessieBron.cs, LeesfoutBreker.cs, PlannerRegels.cs en de route `GET /media/v1/planner`), dat S-G1-15 vastlegt. Deze stap bouwt daarop verder: lees eerst wat er staat (`git -C <WERKMAP>/jelly-leon log --oneline -- plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Core/Planner`) en het rapport `<WERKMAP>/.lokaal/ketens/S-G1-15/RAPPORT-A-BOUW.md` (wat daar als "nog open" staat), en vergelijk elk bouwpunt hieronder met de code voordat je iets nieuws schrijft. Begin niet opnieuw.
- **Lees eerst:** BOUWPLAN `#10.7 Globale batchplanner`; `<WERKMAP>/jelly-leon/docs/adr/ADR-0018-b03-planner-en-gpu-budget.md#Besluit` (punten 1 en 7) en `#Verificatie`; WP-JSON object `B03-018` (deel (c) en Acceptatie "Planner"); `<WERKMAP>/jelly-leon/docs/adr/ADR-0029-b03-017-prototype-een-dll-eigen-ed25519-host-sqlite.md#Besluit` (jobtypen per module); TEST-JSON rij `JLT-66`
- **Bouw:**
  1. Planner in `Core/Planner`: een wachtrij voor alle modules; hooguit een zware taak tegelijk. Modules leveren alleen jobtype, kostenklasse en prioriteit; geen module heeft eigen threads, vensters of budgetten. Het bestaande jobtype `quality.scan` van de prototypemodule is de eerste afnemer.
  2. Grenzen: alle batch samen hooguit 2 threads en 1 GiB; `nice 19` en `ionice idle` op de werker en zijn kinderen. De planner meet het werkelijke gebruik (threads en RSS van de procesgroep) en stopt een taak die de grens overschrijdt.
  3. Pauze: binnen 5 s na elke `PlaybackStart` (Direct Play en transcode) staat de zware taak stil; niet uit te zetten. De enige uitzondering is een uitdrukkelijk beheerdersverzoek, en alleen met minstens 1024 MiB cgroup-marge en zonder CPU-transcode.
  4. Stilstand ook bij: een lopende software-transcode; een schrijfbare mediamap (S-G1-20); MediaGuard-status `onbekend` op de NAS; een noodstop van MediaGuard. De laatste twee komen van de viewerclient (S-G1-50); bouw hier de ingang en test hem met een nagebootste bron.
  5. Stroomonderbreker: 3 of meer bestanden met een leesfout binnen 1 uur stopt alle batch en geeft het event `media.storage.read_failed` (drie segmenten, zonder pad of titel).
  6. Vensterbeleid en achterstandsschatting per module (als getal met de tekst "schatting"); de instellingen staan in de plugin-configuratie, niet per module.
  7. Pauzemeting: een script in `tools/jelly-leon/e2e/` dat in een container minstens 20 keer een sessie start terwijl een zware taak loopt en de tijd tot stilstand meet. Rapport in `docs/platform-v2/test-evidence/`.
  8. Werk ADR-0018 (kop "Verificatie"), EVIDENCE en het OpenAPI-bestand (als er een statusroute bij komt) bij; leg vast met P-GIT.
- **Tests (verplicht):** T-JL-PLUGIN met `--filter "FullyQualifiedName~Planner"`, daarna volledig; de pauzemeting achter `flock <WERKMAP>/.lokaal/stack.lock nice -n 10` met minstens 20 metingen. Negatieve tests: twee zware taken van twee modules lopen nooit tegelijk; een taak die 3 threads of meer dan 1 GiB gebruikt wordt gestopt; de pauze is niet uit te zetten via een instelling of een route; een beheerdersverzoek tijdens een CPU-transcode wordt geweigerd; bij MediaGuard-status `onbekend` met de vlag "op de NAS" start geen batch.
- **Poort:** P-jelly-leon (Volledig: jobs plugins en image) + P-VEILIG (alleen de beheerdersroute) + P-GIT + P-EERLIJK
- **Valkuilen:** V-057 (een tijdmeting hangt af van de last op de machine: `loadavg` in het rapport, en meten in een exclusief slot); V-032; V-009; V-051; V-003 (de pauzetest moet falen als de planner niet pauzeert: bewijs dat een keer met de pauze uitgeschakeld in de testopstelling)
- **Bewijs:** `B03-018` blijft "Bezig" (opmerking: deel (c), mediaan en slechtste pauzetijd met het aantal metingen); `JLT-66` nog niet boeken (dat doet S-G1-40). "NIET GEVALIDEERD (echte NAS): pauzetijd en grenzen zijn op de ontwikkelmachine gemeten; op de NAS blijven de batchmodules uit tot BG-07 en Δ-MG-AUTH."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG (tegelijk; R-VEILIG VERPLICHT voor de uitzondering "beheerdersverzoek" en de statusroute) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4; verder standaard
- **Stop en vraag als:** de pauze niet stabiel binnen 5 s komt (dat is een no-go voor Gate golf 1: melden, niet de drempel verleggen); `ionice idle` of het meten van de cgroup-marge in de container extra rechten vraagt; de planner alleen werkt met een wijziging in de server buiten de plugin.

### S-G1-50 - MediaGuard-viewerclient via de Hub (B03-009)
- **Repo:** jelly-leon | **Fase:** P4 golf 1 | **Omvang:** middel | **Moeilijkheid:** hoog | **Zwaar:** ja (plugin-build achter docker-build.lock; de pluginproef draait wegwerpcontainers achter stack.lock)
- **Werkpakketten en tests:** B03-009, B03-018, I06-06-06, I24-24-03; contract-ID C1.3-JL-08
- **Vooraf:** S-G1-36 klaar; S-G1-12 klaar; besluit BG-04 genomen (via de Hub)
- **Al gedaan?** `git -C <WERKMAP>/jelly-leon log --oneline --grep "B03-009" | head -5 ; ls <WERKMAP>/jelly-leon/plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Core/MediaGuard <WERKMAP>/jelly-leon/docs/adr/ADR-0034-b03-009-mediaguard-viewerclient-via-de-hub.md ; grep -c "B03-009" <WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json` -> de client staat er, is vastgelegd en beoordeeld, en EVIDENCE heeft een rij `B03-009`: dan alleen R-EERLIJK. Stand bij het schrijven van dit plan: een andere ronde heeft de client gebouwd en vastgelegd (commit `cc3e82b4d`: `IMediaGuardVervoer.cs`, `MediaGuardClient.cs`, `MediaGuardPoller.cs`, `MediaGuardWitteLijst.cs`, de tests in `Core/MediaGuardTests.cs` en ADR-0034). Niet gezien: een review, een EVIDENCE-rij `B03-009`, een bijgewerkte rij `C1.3-JL-08` (stond op "Niet gestart") en de aansluiting van de planner op de uitkomst. Deze stap is dus: nalopen, de gaten dichten en boeken. Begin niet opnieuw en gooi niets weg.
- **Lees eerst:** `<WERKMAP>/jelly-leon/docs/adr/ADR-0034-b03-009-mediaguard-viewerclient-via-de-hub.md#Besluit`, `#Grenzen` en `#Gevolgen`; BOUWPLAN `#10.5 MediaGuard: één viewerclient en een harde grens`; BESLUITEN `#Besluiten van de gebruiker na contract 1.3 (2026-11-10)` (BG-04); WP-JSON object `B03-009` (Acceptatie); PLUGINTEST `Core/MediaGuardTests.cs`
- **Bouw:**
  1. Leg ADR-0034 (kop "Besluit", punten 1 tot en met 9) naast de code: voor elk punt wijs je de test aan die het bewijst. Een punt zonder test krijgt een test; een test die niet kan falen (V-003) wordt aangescherpt.
  2. Geen vervoer, geen sleutel, geen adres: bevestig dat de standaardregistratie `GeenMediaGuardVervoer` is, dat `Core/MediaGuard` geen HTTP-client bevat en dat er in de configuratie, de beheerpagina's en de geheimenmap geen veld of bestand voor een MediaGuard-sleutel of -adres bestaat. Bouw geen HTTP-vervoer en geen nagebootst vervoer in de productiecode: dat wacht op een Hub-route in het contract (Δ-HUB-JL; ADR-0034 kop "Gevolgen").
  3. Rolcontrole: alleen precies `viewer` is goed; bij elke andere waarde volgt status `geweigerd` en tot de volgende rolcontrole geen enkele andere aanroep. Controleer het tijdschema (`LinkCheckMinutes` 60, `PollSeconds` 20) met een klok die in de test te sturen is.
  4. Witte lijsten: de routes buiten de lijst zijn niet aan te roepen (ook niet met een andere schrijfwijze van het pad, een querystring of een afsluitende schuine streep); van een antwoord komen alleen de genoemde velden in `MgBeeld`. De routes met een lege veldenlijst blijven onbruikbaar; vul geen velden in op een vermoeden.
  5. Ruwe antwoorden: bied in een test elk verboden veld (`sessions`, `hold.reason`, `actions`, `tests`, `last`) aan met een unieke waarde en zoek die waarde daarna in de uitkomst, in de log en in elk bestand onder de gegevensmap van de test. Eis: 0 treffers.
  6. Aansluiting: de planner (S-G1-36) laat batchwerk alleen toe bij status `ok`; `onbekend`, `geweigerd` en `onbereikbaar` betekenen geen batch (ADR-0034 punt 9). De budgetbeslisser volgt in S-G1-38. De health-controle `mediaguard` volgt ADR-0034 punt 8; controleer haar in de pluginproef.
  7. Wat uit de acceptatie van B03-009 niet uitvoerbaar is zolang er geen vervoer bestaat ("0 muterende aanroepen via een loggende proxy", "de netwerklog toont alleen routes uit de witte lijst") schrijf je letterlijk op als "niet uitgevoerd: er is geen vervoer". De verzoekroute `POST /media/v1/mediaguard/request` en de deeplink zijn golf 3 (zusterbestand `<WERKMAP>/.lokaal/plan/uit/STAPPEN_P4_GOLF3_4.md`); JLT-23, JLT-37 en JLT-45 horen daar ook.
  8. Werk `CONTRACT_1.3_CONFORMITEIT.md` (punt C1.3-JL-08), EVIDENCE en `EXCEL_TAKEN.json` bij; meld de twee contractpunten uit ADR-0034 (kop "Gevolgen") aan de regisseur voor ai-server-manager; leg vast met P-GIT.
- **Tests (verplicht):** T-JL-PLUGIN met `--filter "FullyQualifiedName~MediaGuard"`, daarna volledig; T-JL-TOOLS; de pluginproef uit S-G1-10 opnieuw op de lokale image. Negatieve tests: het nagebootste vervoer antwoordt met rol `operator`, met een lege rol en met `Viewer` in een andere schrijfwijze -> telkens `geweigerd` en geen verdere aanroep; een antwoord met een extra veld `sessions` -> het veld komt nergens voor; een route buiten de witte lijst -> geweigerd zonder dat het vervoer wordt aangeroepen; een antwoord groter dan 1 MiB of zonder geldige JSON -> `onbereikbaar`; zonder vervoer -> 0 aanroepen, status `onbekend`, reden `geen_route_via_hub`, geen 500.
- **Poort:** P-jelly-leon (Volledig: jobs plugins en image) + P-VEILIG + P-HARDE-EIS + P-CONTRACT + P-GIT + P-EERLIJK
- **Valkuilen:** V-046; V-099 (een nagebootst vervoer is geen bewijs voor een Hub-route die nog niet bestaat); V-105; V-001; V-094; V-098 (acceptatie-onderdelen die niet zijn uitgevoerd staan er letterlijk bij); V-003
- **Bewijs:** nieuwe rij `B03-009` -> "Bezig" (Unit-getest; Sim-getest; opmerking: alleen de viewerclient met nagebootst vervoer; geen vervoer, dus geen netwerkmeting; verzoekroute volgt in golf 3); `C1.3-JL-08` -> "Bezig"; `I06-06-06` en `I24-24-03` -> "Bezig" voor het deel "buiten de core en alleen lezen". "NIET GEVALIDEERD (echte Hub): er is geen Hub-route voor MediaGuard-gegevens, de koppeling staat op elke installatie op `onbekend`; NIET GEVALIDEERD (echte MediaGuard): of de echte antwoorden de genoemde velden zo bevatten is niet gemeten; NIET GEVALIDEERD (echte NAS)."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG + R-HARDE-EIS (tegelijk; R-VEILIG VERPLICHT: witte lijsten, rolcontrole en het verbod op een sleutel in Jelly Leon; R-HARDE-EIS VERPLICHT: de voortgang van MediaGuard mag door Jelly Leon nooit geraakt worden) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4; R-HARDE-EIS N4; verder standaard
- **Stop en vraag als:** het contract intussen wel een Hub-route voor MediaGuard-gegevens heeft (dan is het vervoer een nieuwe stap met een eigen keten en R-VEILIG; niet in deze stap erbij bouwen); iemand een sleutelveld of een MediaGuard-adres in Jelly Leon wil toevoegen (in strijd met BG-04 en ADR-0034 punt 1); een module een route nodig heeft die een lege veldenlijst heeft (uitbreiden is een contractpunt, geen bouwkeuze).

### S-G1-38 - Budgetbeslisser G1 t/m G10
- **Repo:** jelly-leon | **Fase:** P4 golf 1 | **Omvang:** middel | **Moeilijkheid:** hoog | **Zwaar:** nee (plugin-build en unit-tests achter docker-build.lock)
- **Werkpakketten en tests:** B03-018, JLT-66
- **Vooraf:** S-G1-50 klaar
- **Al gedaan?** `ls -R <WERKMAP>/jelly-leon/plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Core/Budget ; grep -rn "two_gpu\|a310_only\|uhd770_only\|single_other" <WERKMAP>/jelly-leon/plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon --include=*.cs | grep -v "/obj/\|/bin/" | head -5` -> `Core/Budget` bevat de beslisser met de vijf topologieen en een test per regel: dan alleen de reviewers. Bij de overdracht stond in `Core/Budget` alleen `BudgetBeslisser.cs` (half werk van ronde 3, vastgelegd door S-G1-15: een enum `GpuTopologie` met een waarde `Onbekend`, `GroupPauseLaneHoldMinutes` 30, reserveringen per sessiesleutel; geen tests en geen regels G1 tot en met G10). Bouw daarop verder; begin niet opnieuw.
- **Lees eerst:** BOUWPLAN `#10.8 GPU-budget en rolverdeling A310 / UHD 770`; `<WERKMAP>/jelly-leon/docs/adr/ADR-0018-b03-planner-en-gpu-budget.md#Besluit` (punten 2 tot en met 6); WP-JSON object `B03-018` (deel (d)); `<WERKMAP>/jelly-leon/docs/adr/ADR-0024-b03-clientrollen.md` (nooit weigeren); PLUGIN `Modules/Devices/DevicesModule.cs`
- **Bouw:**
  1. Een beslisser in `Core/Budget` als enige bron van waarheid over de bezetting van GPU en CPU. Invoer: live-transcodes (aangeleverd door module Devices via `ITranscodeManager`; staat Devices uit, dan is de live-bezetting "onbekend" en gedraagt de beslisser zich als "bezet"), de MediaGuard-lanes uit de poller van S-G1-50, en de batchvraag van de planner.
  2. De regels G1 tot en met G10 als een tabel in de code, elk met een eigen test en de regel-ID in de testnaam. De volledige tekst van de regels: ONBEKEND - eerst vaststellen met: `grep -n "G1\b\|G2\b\|G3\b\|G4\b\|G5\b\|G6\|G7\b\|G8\b\|G9\b\|G10" <WERKMAP>/ai-server-manager/docs/platform-v2/02_BOUWPLANNEN/B03_UNIVERSELE_MEDIASERVER.md | head -60` (BOUWPLAN §10.8 geeft alleen de samenvatting).
  3. Vaste uitkomsten: live gaat voor MediaGuard-AV1 en dat gaat voor B03-batch; B03-batch nooit op de node waar MediaGuard encodeert; AV1-encode nooit op een node zonder AV1-encode; nooit een aanroep van `/api/v1/app/control`; zijn alle nodes vol, dan upstreamgedrag plus het event `media.gpu_lane.saturated`, nooit een weigering.
  4. Topologie als uitdrukkelijke stand: `two_gpu`, `a310_only`, `uhd770_only`, `single_other`, `none`. Op de ontwikkelmachine is dat `single_other`; de rollen "UHD 770 live, A310 AV1" zijn hypotheses en staan nergens als vaste waarde in de code.
  5. Lane-reservering per sessiesleutel: seek, hervatten en een groepspauze houden dezelfde node (`GroupPauseLaneHoldMinutes` 30). In deze stap alleen de boekhouding en de tests; de live-lanekeuze zelf is van F5 (golf 4, zusterbestand).
  6. De uitkomst is zichtbaar in de health-check en als connector-item met alleen aantallen (geen sessie, titel of apparaatnaam).
  7. Werk ADR-0018 (kop "Verificatie") en EVIDENCE bij; leg vast met P-GIT.
- **Tests (verplicht):** T-JL-PLUGIN met `--filter "FullyQualifiedName~Budget"`, daarna volledig. Negatieve tests: de nagebootste MediaGuard meldt "A310-lane bezet" -> 0 batchtaken op die node; MediaGuard-status `onbekend` -> geen batch; alle nodes vol -> geen weigering maar upstreamgedrag plus event; een module die zelf een node kiest buiten de beslisser om laat een test falen (er is geen andere ingang); een seek tijdens een reservering houdt dezelfde node.
- **Poort:** P-jelly-leon (Snel + job plugins uit Volledig) + P-HARDE-EIS (MediaGuard alleen lezen) + P-GIT + P-EERLIJK
- **Valkuilen:** V-003; V-102 (een testtelling zegt niets: elke regel G1 tot en met G10 heeft een eigen test); V-099; V-051; V-103
- **Bewijs:** `B03-018` blijft "Bezig" (opmerking: deel (d), regels G1 tot en met G10 met tests; topologie op de ontwikkelmachine `single_other`). "NIET GEVALIDEERD (hardware): A310 en UHD 770 en het gedrag met twee kaarten zijn niet gemeten; D08 (welke render-node welke kaart is) is onbekend; NIET GEVALIDEERD (echte MediaGuard)."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-HARDE-EIS (tegelijk; R-HARDE-EIS VERPLICHT: live kijken gaat altijd voor en MediaGuard wordt nooit bediend) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); R-HARDE-EIS N4; verder standaard
- **Stop en vraag als:** een regel G1 tot en met G10 in het BOUWPLAN niet eenduidig is of twee regels elkaar tegenspreken (niet zelf uitleggen: melden); een regel alleen te bouwen is met een waarde die een meting op de NAS vraagt (dan de regel bouwen met "onbekend" als veilige stand).

### S-G1-40 - Gecombineerde belastingtest JLT-66
- **Repo:** jelly-leon | **Fase:** P4 golf 1 | **Omvang:** middel | **Moeilijkheid:** hoog | **Zwaar:** ja (exclusief meetslot: vier streams waarvan twee transcodes; niets anders zwaars tegelijk op de machine)
- **Werkpakketten en tests:** B03-018, JLT-66
- **Vooraf:** S-G1-38 klaar; de lokale image is opnieuw gebouwd op de stand na S-G1-38
- **Al gedaan?** `ls <WERKMAP>/jelly-leon/docs/platform-v2/test-evidence | grep -i "jlt-66\|belasting" ; python3 -c "import json;d=json.load(open('<WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json'));print([(r['id'],r.get('status')) for r in d if r.get('id')=='JLT-66'])"` -> er ligt een rapport met minstens 3 runs en `JLT-66` staat op "Bezig": dan alleen R-EERLIJK op het rapport. Bij het schrijven van dit plan ontbraken het rapport en de rij.
- **Lees eerst:** TEST-JSON rij `JLT-66`; WP-JSON object `B03-018` (deel (e) en Acceptatie "Belastingtest"); FASERING `#Gate golf 1`; `<WERKMAP>/jelly-leon/docs/adr/ADR-0018-b03-planner-en-gpu-budget.md#Besluit` (punt 7); `<WERKMAP>/jelly-leon/tools/b03-harnas/README.md` (meetslot)
- **Bouw:**
  1. Een testscript in `tools/jelly-leon/e2e/` of als onderdeel van HARNAS (A-VERKEN kiest aan de hand van `tools/b03-harnas/b03h/meetslot.py` en het bestaande `proef_lib.py`; niet beide). De opties van het meetslot: ONBEKEND - eerst vaststellen met: `PYTHONPATH=tools/b03-harnas $PY -m b03h --help`.
  2. Opstelling: de lokale jelly-leon-image met `--cpus 4 --memory 4g`; alle bestaande modules aan met een gevulde achterstand; 4 live streams: 2 Direct Play en 2 QSV-transcodes op `/dev/dri/renderD128`; de MediaGuard-simulator meldt een bezette A310-lane. De render-node van de ontwikkelmachine: `ls /dev/dri` gaf bij het schrijven `renderD128`. Let op: de plugin heeft standaard geen vervoer naar MediaGuard (ADR-0034 punt 2) en laat dan geen batchwerk toe (punt 9). De test heeft dus een nagebootst vervoer nodig dat alleen in de testopstelling bestaat (bijvoorbeeld een aparte test-assembly die alleen in de proefcontainer wordt gekoppeld) en dat niet in de uitgeleverde DLL of image zit. Hoe dat aansluit op `IMediaGuardVervoer` stelt A-VERKEN vast; de keuze komt in het rapport en in ADR-0018 (kop "Verificatie").
  3. Het deel "een Watch Together-groepspauze en hervatten" uit JLT-66 kan pas als de module Watch Together bestaat (golf 2). Voer het hier niet uit en schrijf dat letterlijk in het rapport; S-G2-50 herhaalt JLT-66 met dat deel.
  4. Meet per run: snelheid van elke live stream ten opzichte van realtime, buffering, pauzetijd van de batchtaak na elke `PlaybackStart`, threads en geheugen van de batch, RSS van de server, OOM-kills (uit de cgroup-teller van de container), batchtaken op de bezette node, en `loadavg` voor en na.
  5. Minstens 3 runs achter stack.lock, zonder andere zware stap op de machine (de regisseur houdt de andere banen zolang tegen).
  6. Schrijf het rapport als JSON plus een korte Nederlandse samenvatting in `docs/platform-v2/test-evidence/`; het rapport noemt de image-ID, de commit, de modules die aan stonden en wat niet is uitgevoerd.
  7. Maak van de uitkomst de meetinvoer voor BG-07 (gemeten piek van geheugen en CPU, met de waarschuwing dat de ontwikkelmachine een bovengrens is). Vul geen waarde voor de NAS in het manifest in.
  8. Werk EVIDENCE en `EXCEL_TAKEN.json` bij; leg vast met P-GIT.
- **Tests (verplicht):** de belastingtest zelf: `flock <WERKMAP>/.lokaal/stack.lock nice -n 10 $PY <script uit punt 1> --image <tag> --runs 3 --rapport <pad>` (opties legt A-BOUW vast in `--help`); T-JL-TOOLS voor de hulpfuncties. Negatieve test: dezelfde opstelling met de planner-pauze uitgeschakeld in de testopstelling moet de test laten falen op de eis "pauze binnen 5 s" (bewijs dat de test kan falen); een run met `--memory` zo laag dat de server het niet haalt moet als OOM in het rapport staan en niet als geslaagd.
- **Poort:** P-jelly-leon (Volledig: job image) + P-EERLIJK + P-GIT
- **Valkuilen:** V-057; V-009; V-014; V-003; V-098 (niet "Sim-geslaagd" als het groepspauze-deel niet is uitgevoerd: de opmerking noemt het); V-099; V-008; V-076
- **Bewijs:** nieuwe rij `JLT-66` -> "Bezig" met validatie Sim-geslaagd of Sim-mislukt en de opmerking "Intel-iGPU-getest (ontwikkelmachine); deel groepspauze niet uitgevoerd (module bestaat nog niet)"; `B03-018` blijft "Bezig". "NIET GEVALIDEERD (hardware): A310 en UHD 770; NIET GEVALIDEERD (echte NAS): de manifestresources zijn niet op de NAS gemeten; de NAS-uitvoering staat in `<WERKMAP>/.lokaal/plan/uit/STAPPEN_P6.md`."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK (VERPLICHT: de uitkomst is invoer voor een besluit van de gebruiker en mag niet mooier worden opgeschreven dan gemeten)
- **Niveau:** A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); verder standaard
- **Stop en vraag als:** het nagebootste MediaGuard-vervoer alleen te maken is door een simulator of een schakelaar in de uitgeleverde plugin te bouwen (dat is een besluit, geen bouwkeuze); er een OOM-kill optreedt (no-go voor Gate golf 1: melden met de meting); QSV op `/dev/dri/renderD128` niet werkt voor de gebruiker van de container (BG-38 regelt de groepen op de machine); de live streams de 1,0 keer realtime niet halen terwijl de batch al stil staat (dan ligt het niet aan de planner: melden).

### S-G1-60 - Haakmodule in de webclient
- **Repo:** jelly-leon-web | **Fase:** P4 golf 1 (mag voor Gate P4-0) | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** ja (npm-productiebuild en de browsertest met een echte Jellyfin-container)
- **Werkpakketten en tests:** B03-017 (het deel "Webkant: een fork-eigen haakmodule"); raakt JLT-63 en JLT-64 als controle dat de webclient gelijk blijft aan stock
- **Vooraf:** S-P40-10 klaar; geen besluit nodig. Deze stap valt buiten Peil (de webclient van Jelly Leon volgt de stijl van upstream): geen A-ONTWERP en geen R-ONTWERP.
- **Al gedaan?** `ls <WERKMAP>/jelly-leon-web/src/jelly-leon/hooks ; grep -rn "jlHook" <WERKMAP>/jelly-leon-web/src --include=*.ts --include=*.tsx --include=*.js -l | head ; grep -n "B03-017" <WERKMAP>/jelly-leon-web/docs/platform-v2/EVIDENCE.json` -> de map bestaat, `jlHook` staat alleen onder `src/jelly-leon/` en er is een rij `B03-017`: dan alleen de reviewers. Bij het schrijven van dit plan bestond `src/jelly-leon` niet en had EVIDENCE van deze repo geen rij `B03-017`. Staat `jlHook` al in een upstream-bestand zonder regel in het patchregister: niet weghalen, melden.
- **Lees eerst:** BOUWPLAN `#10.11 Register van upstream-gedrag, patches en webhaken`; `<WERKMAP>/jelly-leon-web/docs/platform-v2/PATCHES.md#Geplande haken op de 12.x-basis (nog NIET uitgevoerd — alleen planning)`; `<WERKMAP>/jelly-leon-web/tools/jelly-leon-web/fork_paths.txt`; WP-JSON object `B03-017` (zin "Webkant"); `<WERKMAP>/.lokaal/plan/uit/POORTEN.md#P-jelly-leon-web`
- **Bouw:**
  1. Maak de fork-eigen module onder `src/jelly-leon/hooks` (het pad staat al in `fork_paths.txt`). De bestandsnamen en de taal (TypeScript of JavaScript) kiest A-VERKEN aan de hand van de buurbestanden in `src/utils` en de lintregels; leg de keuze in het rapport vast.
  2. De module biedt een functie `jlHook('naam', ctx)`. Zij zoekt bij de naam een handler op, laadt die met een dynamische `import()` en roept hem aan binnen `try/catch`. Een onbekende naam, een ontbrekende handler, een mislukte import of een fout in de handler mag de aanroeper nooit breken: de functie komt dan gewoon terug en schrijft hooguit een regel naar de console zonder gegevens van de gebruiker. Bron: BOUWPLAN `#10.11 Register van upstream-gedrag, patches en webhaken`.
  3. Maak daarnaast de variant voor een plek in het scherm (een "render-slot"): een onderdeel dat de handler toont binnen een error boundary, zodat een fout in fork-code het omliggende upstream-scherm laat staan. Bron: BOUWPLAN (rij "Web: menu-items" bij Watch Together; daar staat de eis "met error boundary").
  4. De tabel met handlers is in deze stap leeg. Zet in deze stap geen enkele aanroep van `jlHook` in een upstream-bestand: elke haak komt later, per functie, als een wijziging met een eigen regel `JLW-NNNN` in `docs/platform-v2/PATCHES.md`. Gevolg dat je in het rapport noemt: zolang geen upstream-bestand de module aanroept, zit zij niet in de bundel en is de gebouwde webclient gelijk aan die van voor deze stap.
  5. Teksten horen in eigen bestanden onder `src/jelly-leon/strings/` (`nl.json` en `en-us.json`), nooit in `src/strings/*.json`. Maak de twee bestanden alleen aan als de module zelf een tekst toont; anders niet.
  6. Schrijf unit-tests naast de module (dezelfde vorm als `src/utils/events.test.ts`; ze draaien met `npm run test`).
  7. Werk `docs/platform-v2/PATCHES.md` bij: in de kop "Geplande haken ..." de zin dat de haakmodule nu bestaat en dat er nog geen haak is geplaatst. Voeg in `docs/platform-v2/EVIDENCE.json` en `EXCEL_TAKEN.json` de rij `B03-017` toe voor het webdeel.
  8. Leg vast met P-GIT en geef de volledige commit-hash door aan de regisseur: S-G1-70 zet die commit in `tools/jelly-leon/baseline.json` van jelly-leon.
- **Tests (verplicht):** T-JLW-STATISCH (de patchregistercontrole moet groen blijven zonder nieuwe registerregel: bewijs dat alles in een fork-eigen pad staat); T-JLW-NPM; T-JLW-E2E in modus fork en modus stock. Negatieve tests (unit): een handler die een fout gooit, een handler waarvan de import mislukt en een onbekende naam laten `jlHook` alle drie zonder exception terugkeren; het render-slot met een falende handler toont niets en laat de omliggende inhoud staan. Negatieve controle op het register: `git diff --name-only <basis>..HEAD` bevat geen pad buiten `fork_paths.txt` behalve documentatie die daar al onder valt.
- **Poort:** P-jelly-leon-web (Volledig) + P-GIT + P-EERLIJK
- **Valkuilen:** V-072 (alles wat buiten de fork-eigen paden komt botst bij de volgende sync); V-067; V-028; V-003; V-022; V-126
- **Bewijs:** in `<WERKMAP>/jelly-leon-web/docs/platform-v2/EVIDENCE.json`: `B03-017` -> "Bezig" (Unit-getest; opmerking: haakmodule zonder geplaatste haak). `JLT-63` blijft "Bezig". "NIET GEVALIDEERD (hardware): echte browsers en echte tv's; NIET GEVALIDEERD (echte NAS)."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** de module niet te bouwen is zonder een wijziging in een upstream-bestand of in de bouwconfiguratie (dat is een patch met registerregel en dus een besluit); `npm run build:production` door geheugen wordt afgebroken (V-014: opnieuw als er niets anders zwaars draait, daarna melden); de browsertest in modus stock anders uitvalt dan voor deze stap.

### S-G1-70 - Manifest, CUSTOM_APP en web-verwijzing bijwerken
- **Repo:** jelly-leon | **Fase:** P4 golf 1 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (image-build met de echte web-build, imageproeven)
- **Werkpakketten en tests:** B03-017, B03-018, I24-24-04; contract-ID C1.3-JL-09 (blijft "Niet gestart": het moment is P5; alleen de meting in de opmerking wordt ververst)
- **Vooraf:** S-P40-82 klaar (of uitdrukkelijk uitgesteld door de regisseur: de overname-assistent is geen eis van Gate P4-0); S-G1-60 klaar en gepusht; S-G1-40 klaar; besluit BG-07 hoeft nog niet genomen te zijn (de waarden blijven dan voorlopig)
- **Al gedaan?** `python3 -c "import json;print(json.load(open('<WERKMAP>/jelly-leon/tools/jelly-leon/baseline.json'))['web_fork_commit'])" ; git -C <WERKMAP>/jelly-leon-web rev-parse HEAD ; git -C <WERKMAP>/jelly-leon log --oneline -5 -- deploy/manifest deploy/truenas` -> de eerste twee regels zijn gelijk (of de eerste wijst naar de commit van S-G1-60 of later) en de laatste wijziging van manifest en `CUSTOM_APP.md` is van na S-G1-40: dan alleen R-MANIFEST. Bij het schrijven van dit plan wees `web_fork_commit` naar een commit van tien vastleggingen voor de HEAD van jelly-leon-web.
- **Lees eerst:** `<WERKMAP>/jelly-leon/deploy/manifest/jelly-leon.manifest.yaml`; `<WERKMAP>/jelly-leon/deploy/truenas/CUSTOM_APP.md#Formulier: Apps → Discover Apps → Custom App` en `#Beveiliging zonder formuliervelden`; `<WERKMAP>/jelly-leon/docs/adr/ADR-0013-ci-echte-web-build.md`; `<WERKMAP>/jelly-leon/docs/adr/ADR-0017-b03-analysewerker-en-bestandspas.md#Besluit`; `<WERKMAP>/.lokaal/plan/uit/POORTEN.md#P-INSTALLATIE`
- **Bouw:**
  1. Zet `web_fork_commit` in `tools/jelly-leon/baseline.json` op de volledige hash die S-G1-60 heeft doorgegeven en controleer met `$PY tools/jelly-leon/web_bron.py --controleer <checkout van jelly-leon-web op die commit>`. Bron: ADR-0013.
  2. Loop het manifest na op wat golf 1 heeft toegevoegd (werkerproces, socket, featurecache onder `/cache`, geheimenmap onder `/config`): er komt geen nieuwe opslagregel, geen nieuwe poort en geen nieuwe omgevingsvariabele bij tenzij een eerdere stap dat met een ADR heeft vastgelegd. De regel "geen `HUB_*`-namen in parameters of env" (C1.3-JL-04) blijft waar. De proefschakelaar `JELLYLEON_SPIKE_STARTUPFILTER` (ADR-0033) komt niet in het manifest en niet in het formulier.
  3. De waarden `resources: cpus: 4` en `memory_mib: 4096` blijven staan tot BG-07 genomen is. Is BG-07 genomen, zet dan de gekozen waarden erin met een verwijzing naar het besluit; is het niet genomen, zet in `CUSTOM_APP.md` de zin dat de waarden voorlopig zijn en dat de batchmodules op de NAS uit blijven tot het besluit. Vul geen waarde in die alleen op de ontwikkelmachine is gemeten als waarde voor de NAS.
  4. `image.digest` blijft `null`: de release en de digest zijn een handeling van de gebruiker. Schrijf dat zo in het rapport.
  5. Werk `deploy/truenas/CUSTOM_APP.md` bij met wat een beheerder na golf 1 in het formulier en in het dashboard ziet: de modules staan standaard uit; de Hub wordt gepind in het dashboard van Jelly Leon; de MediaGuard-status is "onbekend" zolang de Hub geen route levert (ADR-0034). Alleen formulierstappen en schermen; geen YAML, geen compose, geen terminal (P-INSTALLATIE).
  6. Bouw de image opnieuw (P-jelly-leon "4. Volledig", job image) en geef hem de tag `jelly-leon:lokaal-<korte commit>` zoals in S-G1-16; verwijder de vorige eigen tag. Meet de grootte van de image tegen de grens uit ADR-0017; staat die grens er niet als getal: ONBEKEND - eerst vaststellen met: `grep -n "MiB\|GiB\|groei" <WERKMAP>/jelly-leon/docs/adr/ADR-0017-b03-analysewerker-en-bestandspas.md`.
  7. Controleer in de gebouwde image dat `torch`, `transformers`, `ctranslate2` en `auditok` ontbreken (lees de pakketlijst van de image en de SBOM uit S-G1-30) en ververs de opmerking bij `C1.3-JL-09`.
  8. Draai `$PY tools/jelly-leon/manifest_rapport.py` (lees eerst `--help`), werk EVIDENCE en `EXCEL_TAKEN.json` bij en leg vast met P-GIT.
- **Tests (verplicht):** T-JL-TOOLS (bevat `test_manifest_1_2.py`, `test_manifest_1_3.py`, `test_manifest_rapport.py`, `test_web_bron.py` en `test_web_config.py`); T-JL-REGISTER; T-JL-IMAGE tegen de nieuwe tag. Negatieve tests: `web_bron.py --controleer` tegen een checkout op een andere commit geeft een fout (exitcode niet 0); een manifest met een `HUB_`-naam in `env` laat `test_manifest_1_3.py` falen (bestaat die test niet in die vorm, voeg hem toe); de image start met de plugin geladen en een lege `/config` zonder dat de healthcheck "healthy" meldt voordat de server antwoordt (V-068).
- **Poort:** P-jelly-leon (Volledig: jobs forkregels en image) + P-INSTALLATIE + P-CONTRACT + P-GIT + P-EERLIJK
- **Valkuilen:** V-096; V-068; V-053; V-035 (een verwijzing naar een commit die verschuift); V-017 (de web-commit moet op de remote staan voor CI hem kan ophalen); V-088; V-012
- **Bewijs:** `I24-24-04` blijft "Bezig" (Sim-getest); `B03-017` en `B03-018` blijven "Bezig"; `C1.3-JL-09` blijft "Niet gestart" met een verse meting in de opmerking. "NIET GEVALIDEERD (echte NAS): het formulier van TrueNAS is niet ingevuld en de resources zijn niet op de NAS gemeten; de installatie op de NAS staat in `<WERKMAP>/.lokaal/plan/uit/STAPPEN_P6.md`."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-MANIFEST (tegelijk; R-MANIFEST VERPLICHT: manifest, image en installatiedocument wijzigen) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** golf 1 een nieuw formulierveld, een nieuwe opslagregel, een extra capability of een andere gebruiker in de container nodig blijkt te hebben (besluit; raakt contract kop 9); de image groter is dan de grens uit ADR-0017; `torch`, `transformers`, `ctranslate2` of `auditok` in de image zit; de commit van jelly-leon-web niet op de remote staat.

### S-G1-80 - Eindrun golf 1: JLT-64, JLT-65, JLT-68
- **Repo:** jelly-leon | **Fase:** P4 golf 1 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (containers met een echte Jellyfin-server op fork en stock; de upstream-testsuite)
- **Werkpakketten en tests:** B03-017, B03-018, B03-009, B03-019, JLT-64, JLT-65, JLT-68
- **Vooraf:** S-G1-70 klaar (de image van de eindstand); S-G1-12, S-G1-14, S-G1-18, S-G1-20, S-G1-32, S-G1-34, S-G1-36, S-G1-38 en S-G1-50 klaar
- **Al gedaan?** `ls <WERKMAP>/jelly-leon/docs/platform-v2/test-evidence | grep -i "golf1\|golf-1" ; python3 -c "import json;d=json.load(open('<WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json'));print([(r['id'],r.get('validatie'),r.get('bijgewerkt')) for r in d if r.get('id') in ('JLT-64','JLT-65','JLT-68')])"` -> twee eindrapporten (fork en stock) van de commit van S-G1-70 en drie rijen die naar die rapporten wijzen: dan alleen R-HARDE-EIS en R-EERLIJK. Rapporten van een oudere commit tellen niet: opnieuw draaien.
- **Lees eerst:** TEST-JSON rijen `JLT-64`, `JLT-65`, `JLT-68`; FASERING `#Gate golf 1`; `<WERKMAP>/jelly-leon/tools/jelly-leon/e2e/plugin_proef.py` (kop en `--help`); `<WERKMAP>/.lokaal/ketens/S-G1-10/RAPPORT-A-BOUW.md` (wat toen "niet gemeten" was); `<WERKMAP>/jelly-leon/docs/platform-v2/UPSTREAM_GEDRAG.md`
- **Bouw:**
  1. Bouw de plugin van de eindstand en zet de DLL in een lege map buiten de repo (zoals S-G1-10 bouwpunt 1).
  2. Draai de pluginproef op de fork en op stock met dezelfde commando's als S-G1-10 bouwpunt 2 en 3, tegen de image-tag uit S-G1-70. Alle modules die nu bestaan staan aan (Core met Devices en Quality, met de werker, de planner en de viewerclient erin).
  3. Controleer dat de proef de onderdelen dekt die golf 1 heeft toegevoegd en breid `plugin_proef.py` uit waar dat niet zo is: de werker laat niets achter buiten `/cache` en `/config/data/jelly-leon/`; de logscan zoekt ook naar ruwe MediaGuard-antwoorden; export en back-up van elke bestaande module; de sha256 van het hele corpus is gelijk voor en na een bestandspas.
  4. JLT-64, onderdeel "aan, uit en plugin verwijderd": per module apart en voor beide samen; de antwoorden van `/Items`, `/Users/{id}/Items`, PlaybackInfo, `/MediaSegments`, `/SyncPlay/List` en `/Items/{id}/Similar` zijn met de module uit of de plugin weg gelijk aan stock (vaste veldenlijst; onstabiele lijsten als verzameling). Wat de proef hiervan al doet lees je in de kop van `plugin_proef.py`; wat ontbreekt voeg je toe.
  5. JLT-64, onderdeel "de volledige upstream-testsuite met de plugin geladen": de bestaande rij zegt dat de integratietests zonder de plugin draaien. Stel vast of het met de plugin kan: ONBEKEND - eerst vaststellen met: `grep -rn "plugin" <WERKMAP>/jelly-leon/.github/workflows/jelly-leon-ci.yml | head -20` en de testprojecten onder `<WERKMAP>/jelly-leon/tests`. Kan het niet zonder een wijziging in upstream-testcode, dan blijft dit onderdeel "niet uitgevoerd" en krijgt JLT-64 de validatie "Sim-getest" met die zin; verzin geen vervangende meting.
  6. JLT-68: routetabel uit de MVC-endpointlijst tegen het OpenAPI-bestand; de foutcatalogus per module; de Hub-simulator zonder pin, met gepinde sleutelset, met rol kind, met herhaalde `jti` en met verlopen token; schemacontrole van alle events en connector-items. Elk van deze uitkomsten staat met naam in het rapport.
  7. Bewaar de rapporten onder `docs/platform-v2/test-evidence/` met een naam die begint met `b03-017-golf1-eindrun-`; werk EVIDENCE en `EXCEL_TAKEN.json` bij met per rij wat is uitgevoerd en wat niet; leg vast met P-GIT.
- **Tests (verplicht):** T-JL-PLUGIN; T-JL-TOOLS; de twee proefruns (exitcode 0); T-JL-COMPAT. Negatieve tests: een proefrun waarin een testmodule bewust een rij in `UserData` wijzigt moet falen (bestaat als unit-test van `proef_lib`; anders toevoegen); de routetabelcontrole moet falen op een dubbel geregistreerde route (unit-test in PLUGINTEST, `RoutetabelTests`); de Hub-simulator met rol kind krijgt 403 op elke route.
- **Poort:** P-jelly-leon (Volledig) + P-HARDE-EIS + P-GIT + P-EERLIJK
- **Valkuilen:** V-098; V-005; V-099; V-105; V-112; V-032 (een wisselend falende vergelijking niet wegretryen: de ruismeting A1 tegen A2 is de enige toegestane verklaring); V-009
- **Bewijs:** `JLT-64`, `JLT-65`, `JLT-68` -> "Bezig", validatie Sim-geslaagd alleen voor rijen waarvan elk onderdeel is uitgevoerd, anders Sim-getest met het ontbrekende onderdeel bij naam; `B03-017`, `B03-018`, `B03-009`, `B03-019` blijven "Bezig". "NIET GEVALIDEERD (echte Hub): alleen de Hub-simulator; NIET GEVALIDEERD (echte MediaGuard): de viewerclient heeft geen vervoer; NIET GEVALIDEERD (echte NAS); NIET GEVALIDEERD (hardware): echte clients."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-HARDE-EIS (tegelijk; R-HARDE-EIS VERPLICHT: dit is het bewijs dat de plugin kijkgeschiedenis en servergegevens ongemoeid laat) -> A-HERSTEL -> R-EERLIJK (VERPLICHT: de uitkomst gaat de gate in)
- **Niveau:** standaard (R-HARDE-EIS N4)
- **Stop en vraag als:** een beschermde tabel (`UserData`, `BaseItems`, `Users`, `Permissions`, `Preferences`, `DisplayPreferences`, `MediaSegments`) verschilt buiten de ruis; er een byte in het corpus is gewijzigd; een route dubbel is geregistreerd; de plugin op stock niet laadt; de upstream-testsuite met de plugin alleen kan na een wijziging in upstream-code.

### S-G1-90 - Gate golf 1
- **Repo:** geen (A-GATE leest in jelly-leon en jelly-leon-web) | **Fase:** P4 golf 1 | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** B03-017, B03-018, B03-009, B03-010, JLT-64, JLT-65, JLT-66, JLT-68
- **Vooraf:** S-G1-80 klaar; Gate P4-0 voorgelegd en door de gebruiker beantwoord (S-P40-95); de meting uit S-G1-40 ligt klaar als invoer voor BG-07
- **Al gedaan?** `ls <WERKMAP>/.lokaal/ketens/GATE-GOLF-1/RAPPORT-A-GATE.md` -> bestaat het rapport en heeft de gebruiker gekozen (ook over BG-07), dan is de stap klaar.
- **Lees eerst:** FASERING `#Gate golf 1`; hoofdstuk 9.2 van dit bestand; EVIDENCE van jelly-leon en jelly-leon-web; de rapporten van S-G1-40 en S-G1-80 onder `<WERKMAP>/jelly-leon/docs/platform-v2/test-evidence/`; `<WERKMAP>/jelly-leon/docs/adr/ADR-0016-b03-een-plugin-met-modules.md`
- **Bouw:**
  1. A-GATE loopt de afvinklijst van hoofdstuk 9.2 af en leest bij elk punt het bewijs zelf (rapport, commit op de remote, CI-run). Een punt zonder bewijs is "niet gehaald".
  2. A-GATE controleert de no-go's van de gate: dubbele routes; een gedeelde singleton die per module verschilt; een OOM in de belastingtest.
  3. A-GATE controleert of van elke stap in golf 1 de verplichte reviewrapporten bestaan (`RAPPORT-R-VEILIG.md`, `RAPPORT-R-HARDE-EIS.md`, `RAPPORT-R-MANIFEST.md` waar de stap ze eist) en of open bevindingen zijn hersteld of bij naam zijn doorgeschoven.
  4. A-GATE schrijft `<WERKMAP>/.lokaal/ketens/GATE-GOLF-1/RAPPORT-A-GATE.md` met per gate-eis: gehaald, niet gehaald of open met reden; en apart de lijst van wat alleen tegen een simulator is gemeten.
  5. De regisseur legt de uitkomst en BG-07 samen aan de gebruiker voor met een keuzemenu. Voor BG-07 staan de gemeten pieken uit S-G1-40 erbij, met de zin dat de ontwikkelmachine geen NAS is. Keuzes voor de gate: (1) doorgaan naar golf 2; (2) eerst de genoemde punten herstellen; (3) iets anders. Is JLT-66 niet Sim-geslaagd of BG-07 niet genomen, dan blijven de batchmodules op de NAS uit en staat dat in STATUS.
  6. Daarna: Excel bijwerken (P-EXCEL) en STATUS laten bijwerken (hoofdstuk 9).
- **Tests (verplicht):** A-GATE draait geen builds. Controle: `python3 -m json.tool <EVIDENCE> > /dev/null` voor beide repos. Negatieve controle: `grep -n '"Gereed"\|"Geslaagd"' <EVIDENCE>` geeft geen treffer; een rij met "Sim-geslaagd" waarvan het rapport een onderdeel "niet uitgevoerd" noemt is een bevinding (V-098), ook als de bouwer hem groen meldde.
- **Poort:** P-EERLIJK + P-HARDE-EIS (leeslijst) + P-EXCEL
- **Valkuilen:** V-098; V-034; V-099; V-105; V-108; V-006
- **Bewijs:** geen eigen EVIDENCE-rij; het gate-rapport is het bewijs. Wat de NAS, de echte Hub of de echte MediaGuard vraagt blijft "Geblokkeerd" met "NIET GEVALIDEERD (echte NAS)", "NIET GEVALIDEERD (echte Hub)" of "NIET GEVALIDEERD (echte MediaGuard)".
- **Agents:** A-GATE (VERPLICHT) -> regisseur legt voor aan de gebruiker. Korte keten: alleen lezen en oordelen, geen wijziging in een repo.
- **Niveau:** A-GATE N4 (einde van een golf, niet van een fase)
- **Stop en vraag als:** een no-go waar is; een verplicht reviewrapport ontbreekt; de gebruiker niet kiest (golf 2 start dan niet; S-G2-36 en S-G2-38 ook niet).

### 8.3 Golf 2

Golf 2 bouwt de eerste functiemodules op de basis van golf 1. Bij de overdracht bestond hier niets van: geen map
`Modules/WatchTogether`, `Modules/Recommendations` of `Modules/Segments` onder PLUGIN (alleen de prototypemodules
`Modules/Devices` en `Modules/Quality`). Vaste afspraken voor alle stappen van golf 2:

- **Een DLL.** ADR-0029 (kop "Besluit", punt 1) legt vast: `Jellyfin.Plugin.JellyLeon.dll` bevat `Core/**` en
  `Modules/**`, geen tweede assembly. Een module komt onder PLUGIN `Modules/<Naam>/`. Noemt een werkpakket een tweede
  DLL of een map buiten `Modules/` (B03-031 noemt `JellyLeon.Recommendations.Core` "als tweede DLL"), dan geldt
  ADR-0029; de engine komt in een eigen namespace zonder Jellyfin-afhankelijkheid binnen dezelfde DLL. Wie toch een
  tweede DLL nodig vindt: stop en meld.
- **Module uit.** De bestaande modules geven met de module uit 404 op hun routes (ADR-0030, kop "Besluit": "module
  aan (404)"; `Core/Http/JlPipeline.cs` gooit dan `Fouten.NietGevonden()`, 404 `not_found`). WP-JSON B03-033 en
  B03-035 noemen 501 `capability_unavailable`. De gebruiker heeft gekozen (besluit Z-19, 2026-11-11; hoofdstuk 3):
  **404 zoals ADR-0030**. Elke module van golf 2 geeft met de module uit 404 `not_found` op haar routes voor een
  aangemelde gebruiker (zonder geldige authenticatie blijft het 401, ADR-0030 punt 2); de tests eisen dat. De afwijking
  van WP-JSON B03-033 en B03-035 (501) zet de bouwer letterlijk in de EVIDENCE-opmerking. Het aanpassen van de
  acceptatie in WP-JSON is een documentatiestap in ai-server-manager die de regisseur vastlegt (besluit Z-19, "Na het
  besluit"); geen stap in dit bestand wijzigt WP-JSON.
- **Schakelaar standaard uit**, eigen SQLite onder `/config/data/jelly-leon/<module>/` met migraties via
  `user_version` en een back-upkopie voor elke migratie (ADR-0029, ADR-0020), register van persoonsgegevens en
  UserDeleted via de Core-diensten van S-G1-18, routes via `Core/Http/RouteTable.cs` en de pijplijn, paden in
  `docs/openapi/jelly-leon-plugin.openapi.json` (drifttest `Core/OpenApiDriftTests.cs`), events via de ene outbox.
- **Differentiele controle-run** (gegevensbescherming) = `tools/jelly-leon/e2e/plugin_proef.py` met de module aan,
  op de lokale image en op stock met `--plugin-map`; breid de proef uit waar een module iets nieuws doet. Het harnas
  heeft daarnaast `PYTHONPATH=tools/b03-harnas $PY -m b03h diffrun --image-a <stock op digest> --image-b <jelly-leon-image>
  --toegestaan <JSON met de toegestane tabellen en kolommen> --uit <rapport>` (en `--negatieve-proef`); A-VERKEN kiest
  per stap welke van de twee het scenario uit TEST-JSON dekt en noteert de keuze in het dossier.
- **Winstclaims** alleen tegen stock-best op dezelfde 12.x-digest, met n en Wilson-interval, op een bevroren testset
  (FASERING "Gates per functie"); onder de streef-n heet de uitkomst "smoke-gate (n = ...)".
- **Pluginpagina's** van Jelly Leon vallen buiten Peil (hoofdstuk 5): geen A-ONTWERP of R-ONTWERP.

### S-G2-10 - Watch Together-kern WT-1: decorator, reconciliatie, fail-closed en API-basis (B03-021)
- **Repo:** jelly-leon | **Fase:** P4 golf 2 | **Omvang:** groot | **Moeilijkheid:** hoog (vervangt een upstream-dienst in de DI-container; gelijktijdigheid van groepen en sessies) | **Zwaar:** ja (plugin-build, image-build, containers met een echte Jellyfin-server, upstream-integratietests)
- **Werkpakketten en tests:** B03-021; WT-1-gate (BOUWPLAN #F1.8 Bouwfasen, rij WT-1); JLT-64 (deel `/SyncPlay`), JLT-65 (deel `wt_`-tabellen)
- **Vooraf:** Gate golf 1 (S-G1-90) door de gebruiker beantwoord; S-P40-60 klaar (baseline Watch Together; zonder die baseline geen vergelijking, wel bouw). BG-03 genomen of de terugval uit hoofdstuk 3.
- **Al gedaan?** `ls <WERKMAP>/jelly-leon/plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Modules ; grep -rln "watch/capabilities\|ISyncPlayManager" <WERKMAP>/jelly-leon/plugins/JellyLeon/src --include=*.cs ; python3 -c "import json;print([(o['id'],o['status']) for o in json.load(open('<WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json')) if o['id']=='B03-021'])"` -> een map `Modules/WatchTogether`, de decorator en de route bestaan en de rij `B03-021` staat op "Bezig": dan alleen de reviewers. Bij het schrijven van dit plan bestond niets hiervan.
- **Lees eerst:** WP-JSON object `B03-021` (Uitvoering en Acceptatie); BOUWPLAN `#F1.8 Bouwfasen` (rij WT-1 en de alinea "Volgorde-afhankelijkheden"); BOUWPLAN `#F1.4 Gegevens en bescherming` en `#F1.5 API-contracten`; upstream `<WERKMAP>/jelly-leon/MediaBrowser.Controller/SyncPlay/ISyncPlayManager.cs` en de registratie `grep -n "ISyncPlayManager" <WERKMAP>/jelly-leon/Emby.Server.Implementations/ApplicationHost.cs` (regel `AddSingleton<ISyncPlayManager, SyncPlayManager>`); `<WERKMAP>/jelly-leon/docs/platform-v2/UPSTREAM_GEDRAG.md`
- **Bouw:**
  1. Module `Modules/WatchTogether` met schakelaar (standaard uit), eigen SQLite met het schema `wt_` (onder andere `wt_group_meta`), registerregels voor persoonsgegevens en de UserDeleted-afhandeling via Core. Bron: WP-JSON `B03-021` (Uitvoering).
  2. Decorator om `ISyncPlayManager`: vervang de registratie vanuit `PluginServiceRegistrator.cs` en delegeer alle leden van de interface (de interface heeft er 7; tel ze na in het bestand). Geen wijziging in upstream-code. Leg de DI-vervanging vast als regel in `docs/platform-v2/UPSTREAM_GEDRAG.md` met een sync-blokkerende runtimecontrole (`decorator_active=true`) in `tools/jelly-leon/e2e/upstream_gedrag_runtime.py`.
  3. Reconciliatie in plaats van onderscheppen (upstream roept intern `LeaveGroup` aan bij `NewGroup` en bij sessie-einde): luister naar `ISessionManager.SessionEnded`, controleer na elke doorgegeven `NewGroup`, `JoinGroup` en `LeaveGroup`, controleer elke 30 s met `GetGroup`, en markeer bij het opstarten alle groepen in `wt_group_meta` als beeindigd. Event `media.watchgroup.ended`.
  4. Fail-closed: is de decorator niet actief terwijl gasten of kinderen zijn ingesteld, dan health `down`, event `media.watchgroup.degraded` en een rode melding op een eenvoudige beheerpagina van de module (W9; buiten Peil, vormgeving van het Jellyfin-dashboard; alleen de status en de melding - de rest van W9 is golf 4 in STAPPEN_P4_GOLF3_4.md).
  5. Routes `GET /media/v1/watch/capabilities`, `GET /media/v1/watch/groups`, `GET /media/v1/watch/groups/{id}/diagnostics` en `POST /media/v1/watch/admin/purge` (alleen beheerder, met Idempotency-Key) via de routetabel, de foutcatalogus en 1 MiB per route; een niet-lid krijgt 404 zonder bestaansorakel. OpenAPI bijwerken.
  6. WT-1-gate, onderdelen (a) tot en met (e) uit BOUWPLAN `#F1.8`: (a) de 22 `/SyncPlay`-routes en `GET /GetUtcTime` in de OpenAPI-export gelijk aan upstream met plugin aan, uit en verwijderd; (b) de upstream-SyncPlay-tests (`tests/Jellyfin.Server.Integration.Tests/Controllers/SyncPlayControllerTests.cs`, `tests/Jellyfin.Server.Implementations.Tests/SyncPlay/`) groen met de plugin aan - of dat kan: ONBEKEND - eerst vaststellen met `grep -rn "plugin" <WERKMAP>/jelly-leon/.github/workflows/jelly-leon-ci.yml | head -20` (dezelfde vraag als S-G1-80 bouwpunt 5; kan het niet zonder upstream-testcode te wijzigen, dan "niet uitgevoerd" en geen vervangende meting); (c) `Enabled=false` en zichtbaarheid `open` zonder gasten of kinderen: `/SyncPlay/List` en `/SyncPlay/{id}` byte-gelijk aan stock na normalisatie; (d) reconciliatie bewezen met minstens 50 herhalingen zonder wees-meta (proefscript in `tools/jelly-leon/e2e/`); (e) health `down` bij een geforceerd inactieve decorator met gasten.
  7. Gedrag bij "module uit", "plugin verwijderd" en "terug naar stock" beschrijven en testen (pluginproef). Werk EVIDENCE (nieuwe rij `B03-021`) en `EXCEL_TAKEN.json` bij; leg vast met P-GIT.
- **Tests (verplicht):** T-JL-PLUGIN (`--filter "FullyQualifiedName~WatchTogether"`, daarna volledig); T-JL-REGISTER; T-JL-IMAGE; de pluginproef op fork en stock; de herhaalproef uit bouwpunt 6 (d) achter `flock <WERKMAP>/.lokaal/stack.lock nice -n 10`. Negatieve tests: een niet-lid vraagt diagnose van een bestaande groep -> 404, gelijk aan een onbestaand ID; een geforceerd inactieve decorator met gasten -> health `down`, niet `healthy`; een tweede `NewGroup` laat geen wees-rij in `wt_group_meta`; na het verwijderen van een gebruiker staat diens GUID in geen `wt_`-tabel.
- **Poort:** P-jelly-leon (Volledig: jobs forkregels, plugins, image, stock-client-e2e) + P-VEILIG + P-CONTRACT + P-GIT + P-EERLIJK
- **Valkuilen:** V-072 (DI-vervanging botst bij een upstream-sync: de registerregel is verplicht); V-003; V-032 (reconciliatie die soms faalt is een bevinding); V-051; V-055; V-066; V-098
- **Bewijs:** `B03-021` -> "Bezig" (Sim-getest; opmerking: per WT-1-onderdeel gemeten of "niet uitgevoerd" met reden); `JLT-64` en `JLT-65` blijven "Bezig". "NIET GEVALIDEERD (echte NAS); NIET GEVALIDEERD (hardware): echte apparaten in een groep (JLT-06)."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG (tegelijk; R-VEILIG VERPLICHT: zichtbaarheid van groepen, kinderen en gasten, fail-closed) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4; verder standaard
- **Stop en vraag als:** de WT-1-gate (a) tot en met (d) niet haalbaar is met de decorator (dan is een core-patch `JL-NNNN` "SyncPlay-uitbreidingspunt" nodig; dat is een besluit met eigen review en wordt NIET in deze stap gebouwd); de decorator alleen werkt met een wijziging in upstream-code; een upstream-test met de plugin aan faalt.

### S-G2-20 - Aanbevelingen F2-1: moduleskelet en Similar-provider (B03-031)
- **Repo:** jelly-leon | **Fase:** P4 golf 2 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (container met een echte Jellyfin-server)
- **Werkpakketten en tests:** B03-031; gate G-F2-1; JLT-14 (alleen het deel "stock-clients ongewijzigd" voor `/Similar`), JLT-64 (deel `/Items/{id}/Similar`)
- **Vooraf:** Gate golf 1; S-P40-62 klaar (baseline aanbevelingen). Geen besluit.
- **Al gedaan?** `ls <WERKMAP>/jelly-leon/plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Modules | grep -i recommend ; grep -rn "ILocalSimilarItemsProvider" <WERKMAP>/jelly-leon/plugins/JellyLeon/src --include=*.cs | head -3 ; grep -n "UG-F2" <WERKMAP>/jelly-leon/docs/platform-v2/UPSTREAM_GEDRAG.md | head -3` -> module, provider en de regels UG-F2-... bestaan: dan alleen de reviewers. Bij het schrijven bestond niets.
- **Lees eerst:** WP-JSON object `B03-031`; BOUWPLAN `#F2.8 Bouwfasen` (rij F2-1); BOUWPLAN `#F2.3.1 Uitbreidingsladder`; upstream `<WERKMAP>/jelly-leon/MediaBrowser.Controller/Library/ILocalSimilarItemsProvider.cs`; `<WERKMAP>/jelly-leon/docs/adr/ADR-0029-b03-017-prototype-een-dll-eigen-ed25519-host-sqlite.md#Besluit`
- **Bouw:**
  1. Module `Modules/Recommendations` met schakelaar `Recommendations.Enabled` (standaard uit) in dezelfde DLL (ADR-0029; zie de afspraken bovenaan 8.3). De engine-namespace zonder Jellyfin-afhankelijkheid maak je nu leeg aan; S-G2-22 vult hem.
  2. Provider `ILocalSimilarItemsProvider<Movie>` en `<Series>` met vaste naam "Jelly Leon", tijdslimiet 300 ms en `ExcludeItemIds`. Implementeer GEEN `IBatchLocalSimilarItemsProvider` (dan blijft `/Movies/Recommendations` upstream). In deze stap levert de provider een eenvoudige uitkomst op metadata; de engine komt in S-G2-22.
  3. Stel in een echte 12.x-container vast en schrijf in het rapport: verschijnt de provider in de bibliotheekopties; werkt `SimilarItemProviderOrder`; wordt de provider zonder volgorde niet aangeroepen als de core genoeg levert; terugval bij exception en time-out.
  4. Leg UG-F2-1 tot en met UG-F2-8 vast in `docs/platform-v2/UPSTREAM_GEDRAG.md` met een sync-blokkerende runtimecontrole per regel (de inhoud van de acht regels: ONBEKEND - eerst vaststellen met `grep -n "UG-F2" <WERKMAP>/ai-server-manager/docs/platform-v2/02_BOUWPLANNEN/B03_UNIVERSELE_MEDIASERVER.md | head -20`); voeg de interface-drifttest toe (de interface van upstream mag niet ongemerkt veranderen).
  5. Werk EVIDENCE (nieuwe rij `B03-031`) en `EXCEL_TAKEN.json` bij; leg vast met P-GIT.
- **Tests (verplicht):** T-JL-PLUGIN (`--filter "FullyQualifiedName~Recommendations"`, daarna volledig); T-JL-REGISTER; de runtimecontroles tegen de lokale image en tegen stock met `--plugin-map`. Negatieve tests: een geforceerde exception en een time-out van de provider leveren het stock-resultaat; zonder volgorde verandert `/Items/{id}/Similar` niets ten opzichte van stock; `/Movies/Recommendations` is als verzameling gelijk met en zonder module.
- **Poort:** P-jelly-leon (Snel + jobs plugins en image uit Volledig) + P-GIT + P-EERLIJK
- **Valkuilen:** V-072; V-002; V-003; V-066
- **Bewijs:** `B03-031` -> "Bezig" (Sim-getest; opmerking met de uitkomst van de vaststellingen uit bouwpunt 3). "NIET GEVALIDEERD (echte NAS): echte bibliotheek (JLT-15)."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** de provider niet in de bibliotheekopties verschijnt en alleen met een core-patch te activeren is; een tweede DLL nodig lijkt (ADR-0029).

### S-G2-22 - Aanbevelingen F2-2: klassieke engine en offline-evaluatie (B03-032)
- **Repo:** jelly-leon | **Fase:** P4 golf 2 | **Omvang:** groot | **Moeilijkheid:** gewoon | **Zwaar:** ja (meetslot met de stub-bibliotheek; stock opnieuw meten op de forkbasisdigest)
- **Werkpakketten en tests:** B03-032; gate G-F2-2; JLT-10, JLT-11 (deel kwaliteit)
- **Vooraf:** S-G2-20 klaar; S-P40-62 klaar; BG-37 (genomen). Of D-ML beschikbaar is staat in het bewijs van S-P40-62 ("D-ML ontbreekt: ..." of een dataset-sha256). WP-JSON B03-032 (veld Afhankelijkheid) noemt "B03-006 (metadata-kwaliteit)": een zachte afhankelijkheid, geen wachtpunt. De engine leest de metadata die upstream nu levert; de acceptatie meet op D-ML of D-SYN, niet op eigen metadata (BOUWPLAN F2, risico R-2: "afhankelijkheid van B03-006 expliciet; evaluatie op schone (D-ML) én rommelige (D-ECHT) metadata"). Later sluit aan: de externe ID's en correcties van S-G3-28 (B03-006; BG-17 over online metadata) en de anime-splitsing van S-G3-30 (B03-002; de anime-vlag blijft de ene definitie uit F2, alinea 9). Een betere uitkomst daardoor is pas een claim na een nieuwe meting.
- **Al gedaan?** `grep -rln "MMR\|Mmr\|redencode\|ReasonCode" <WERKMAP>/jelly-leon/plugins/JellyLeon/src --include=*.cs | head ; ls <WERKMAP>/jelly-leon/docs/platform-v2/test-evidence | grep -i "jlt-10\|f2-eval"` -> de engine en een evaluatierapport bestaan: dan alleen de reviewers.
- **Lees eerst:** WP-JSON object `B03-032`; BOUWPLAN `#F2.3.2 Engine (klassiek, deterministisch, uitlegbaar)`; BOUWPLAN `#F2.1.3 Metrieken en drempels`; BOUWPLAN `#F2.9.4 Offline-evaluatie (JLT-10 warm, JLT-11 koud)`; het bewijs van S-P40-62 onder `<WERKMAP>/jelly-leon/docs/platform-v2/test-evidence/` (naam bevat "b03-030")
- **Bouw:**
  1. Engine in de engine-namespace van `Modules/Recommendations`: kenmerken per item, smaakprofiel uit de huidige UserData (alleen lezen; halfwaardetijd 365 dagen via een stuurbare klok), score, uitsluiten (bekeken, Next Up, niet interessant, geen toegang), herrangschikking (MMR lambda 0,7, hooguit 2 per serie of collectie, typequotum, 1 exploratieplek, tiebreak op ID), redencodes en koude start. Bron: WP-JSON `B03-032` (Uitvoering).
  2. Evaluatie-CLI `jl-rec-eval` die dezelfde engine-code gebruikt en dezelfde cijfers geeft als de harnasmetrieken van S-P40-62 op de handberekende voorbeelden (S-P40-62 bouwpunt 3). De CLI is een gereedschap en komt niet in de pluginmap of de image; de plaats kiest A-VERKEN aan de hand van `tools/jelly-leon/fork_paths.txt` (een nieuw pad hoort in dat register).
  3. Gewichten afstellen alleen op de validatiesplit (laatste 10 procent voor T), nooit op de testset; leg de gewichten en de split vast voor de meting.
  4. Meet stock opnieuw op de forkbasisdigest (gate G-F2-2) en draai JLT-10 en het kwaliteitsdeel van JLT-11 in een exclusief meetslot (het harnas neemt `stack.lock`). Twee identieke verzoeken met vaste klok geven 100 procent dezelfde top 10.
  5. Claim volgens WP-JSON `B03-032` (Acceptatie): met D-ML de drempels tegen S-BEST; alleen D-SYN -> geen rangschikkingsclaim, opmerking letterlijk "rangschikkingswinst niet aangetoond; functioneel aangetoond (synthetisch)". De lektest met geschudde holdout moet slagen.
  6. Werk EVIDENCE (`B03-032`, `JLT-10`, `JLT-11`) en `EXCEL_TAKEN.json` bij; leg vast met P-GIT.
- **Tests (verplicht):** T-JL-PLUGIN (`--filter "FullyQualifiedName~Recommendations"`); T-JL-HARNAS; de evaluatierun achter het meetslot met minstens 3 runs. Negatieve tests: de lektest met geschudde holdout (F2 mag niet significant boven POP uitkomen; doet hij dat wel, dan lekt er informatie); een interactie met tijdstip op of na T wordt geweigerd; een item buiten de toegang van de gebruiker komt nooit in de top 10.
- **Poort:** P-jelly-leon (Volledig: jobs plugins, image, b03-harnas) + P-EERLIJK + P-GIT
- **Valkuilen:** V-005; V-097 (MovieLens-gegevens nooit in de repo: `b03h guard`); V-003; V-098; V-057
- **Bewijs:** `B03-032` -> "Bezig"; `JLT-10` en `JLT-11` -> "Bezig" met Sim-geslaagd of Sim-mislukt, of met de opmerking "functioneel aangetoond (synthetisch)" als alleen D-SYN er is. "NIET GEVALIDEERD (echte NAS): echte historie (JLT-15)."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK (VERPLICHT: een winstclaim mag niet mooier zijn dan de meting)
- **Niveau:** standaard
- **Stop en vraag als:** iemand gewichten wil afstellen op de testset of drempels na de eerste meting wil verschuiven; de stock-meting op de forkbasisdigest buiten het interval van de voormeting valt (verklaren, niet doorgaan).

### S-G2-24 - Aanbevelingen F2-3: eigen opslag, back-up, vergeten en terug naar stock (B03-033)
- **Repo:** jelly-leon | **Fase:** P4 golf 2 | **Omvang:** groot | **Moeilijkheid:** hoog (migraties met back-up; de enige toegestane schrijfactie in upstream-configuratie) | **Zwaar:** ja (differentiele controle-run met echte Jellyfin-containers)
- **Werkpakketten en tests:** B03-033; gate G-F2-3; JLT-16, JLT-17
- **Vooraf:** S-G2-22 klaar.
- **Al gedaan?** `grep -rln "recommendations.db\|rec_config_backup\|IPersonalDataOwner" <WERKMAP>/jelly-leon/plugins/JellyLeon/src --include=*.cs | head ; python3 -c "import json;print([(o['id'],o['status']) for o in json.load(open('<WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json')) if o['id'] in ('JLT-16','JLT-17')])"` -> opslag en beide rijen bestaan: dan alleen de reviewers.
- **Lees eerst:** WP-JSON object `B03-033`; BOUWPLAN `#F2.4 Gegevens en bescherming` (vooral `#F2.4.1 Wat F2 nooit schrijft` en `#F2.4.4 Back-up, herstel, uitzetten en terug naar stock`); BOUWPLAN `#F2.9.8 Gegevensbescherming (JLT-16)`; TEST-JSON rijen JLT-16 en JLT-17; `<WERKMAP>/jelly-leon/docs/adr/ADR-0020-b03-opslag-en-gegevensbescherming.md#Besluit`
- **Bouw:**
  1. SQLite `recommendations.db` onder `/config/data/jelly-leon/recommendations/` (WAL), schema met versie en forward-schematests; voor elke migratie een online-back-up met sha256, migratie eerst op een kopie met `integrity_check`, dan atomair vervangen; een mislukte migratie laat het origineel intact.
  2. Bewaartermijn van pre-migratiekopieen en exports (hooguit 3 kopieen, 30 dagen) en "Alle kopieen nu wissen"; export standaard zonder `rec_interaction`; vergeten (alleen F2-gegevens van de gebruiker zelf, ook de antwoordcache); registerregels en UserDeleted via Core.
  3. Heraankoppelen van feedback na ItemRemoved/ItemAdded op provider-ID's; wezen nooit automatisch wissen; stroomonderbreker bij meer dan 5 procent of meer dan 50 wezen (status `degraded`/`orphan_surge` en event).
  4. "Verwijderen voorbereiden": de providervolgorde terug uit `rec_config_backup` plus export. De ENIGE schrijfactie buiten de eigen opslag is `CollectionFolder.UpdateLibraryOptions` voor `SimilarItemProviderOrder`, alleen na een uitdrukkelijke klik van een beheerder, met back-up en teruglezen; de analyzer staat dat alleen toe in die ene dienst (leg de uitzondering vast volgens ADR-0032, met een eigen test).
  5. Nooit schrijven in Jellyfin-tabellen, UserData, Likes, afspeellijsten, collecties, NFO's of media.
  6. Differentiele controle-run (JLT-16): breid `plugin_proef.py` uit met het gescripte scenario uit TEST-JSON JLT-16 en de tabellen daar; draai op stock en op Jelly Leon met alleen deze module aan. Storing en terugval (JLT-17): vergrendelde of beschadigde database, exception en time-out, module uit, plugin verwijderd na "Verwijderen voorbereiden", terug naar de stock-image.
  7. Werk EVIDENCE (`B03-033`, `JLT-16`, `JLT-17`) en `EXCEL_TAKEN.json` bij; leg vast met P-GIT.
- **Tests (verplicht):** T-JL-PLUGIN (`--filter "FullyQualifiedName~Recommendations"`, daarna volledig); de analyzerproef zoals P-jelly-leon "4. Volledig", job `plugins`; T-JL-IMAGE; de controle-run achter `flock <WERKMAP>/.lokaal/stack.lock nice -n 10`. Negatieve tests: een opzettelijk mislukte migratie laat het origineel byte-gelijk; vergeten laat Jellyfin-UserData ongewijzigd; een schrijfactie naar UserData vanuit de module laat de analyzer falen; met de mediamap ontkoppeld worden geen wezen gemarkeerd; `options.xml` wijkt alleen af in `SimilarItemProviderOrder` na de klik en is na terugzetten byte-gelijk in `TypeOptions`; met de module uit geven de gebruikersroutes van de module 404 `not_found` aan een aangemelde gebruiker, niet 501 (besluit Z-19).
- **Poort:** P-jelly-leon (Volledig) + P-HARDE-EIS + P-VEILIG + P-GIT + P-EERLIJK
- **Valkuilen:** V-005 (vul de database eerst met rijen van de testgebruikers); V-055; V-085 (export niet voor iedereen leesbaar); V-095; V-112; V-115
- **Bewijs:** `B03-033` -> "Bezig"; `JLT-16` en `JLT-17` -> "Bezig" met Sim-geslaagd of Sim-mislukt. Afwijking "module uit geeft 404 volgens ADR-0030 en besluit Z-19; WP-JSON B03-033 zegt 501" letterlijk in de opmerking. "NIET GEVALIDEERD (echte NAS): de B12-dekking van de exports (Δ-HUB-3) bestaat nog niet; echte bibliotheek."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-HARDE-EIS + R-VEILIG (tegelijk; R-HARDE-EIS VERPLICHT: migraties, kijkgegevens alleen lezen, de ene schrijfactie in de bibliotheekopties; R-VEILIG VERPLICHT: export en vergeten) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); R-HARDE-EIS N4; R-VEILIG N4
- **Stop en vraag als:** de controle-run een verschil in een beschermde tabel toont buiten wat stock zelf toont (HARDE EIS: alle golf-2-stappen in jelly-leon stoppen); "Verwijderen voorbereiden" alleen kan met een schrijfactie die niet in WP-JSON B03-033 staat.

### S-G2-26 - Aanbevelingen F2-4: profielen, kinderprofiel en huishoudprivacy (B03-034)
- **Repo:** jelly-leon | **Fase:** P4 golf 2 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee (plugin-build en unit-tests; de E2E met het kinderprofiel draait kort achter stack.lock)
- **Werkpakketten en tests:** B03-034; gate G-F2-4; JLT-13, JLT-11 (deel functioneel: nieuw profiel en kind)
- **Vooraf:** S-G2-24 klaar; S-G1-18 klaar (`IsKid`); BG-16 genomen of de terugval uit hoofdstuk 3 (kijkgedrag van gezinsleden telt nooit mee; fijnere kijklog uit); BG-03 genomen of de terugval.
- **Al gedaan?** `grep -rn "household_share_mine\|IsVisibleStandalone" <WERKMAP>/jelly-leon/plugins/JellyLeon/src --include=*.cs | head -3 ; python3 -c "import json;print([(o['id'],o['status']) for o in json.load(open('<WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json')) if o['id'] in ('B03-034','JLT-13')])"` -> code en rijen bestaan: dan alleen de reviewers.
- **Lees eerst:** WP-JSON object `B03-034`; BOUWPLAN `#F2.4.5 Privacy`; BOUWPLAN `#F2.9.7 Negatief en veiligheid (JLT-13, JLT-17, JLT-18)`; TEST-JSON rijen JLT-13 en JLT-11; `<WERKMAP>/.lokaal/plan/uit/BESLUITEN_EN_BLOKKADES.md#2.3 Start golf 2` (BG-16)
- **Bouw:**
  1. Kandidaten alleen via `InternalItemsQuery(user)` (MaxParentalRating, BlockUnratedItems, Blocked/AllowedTags, EnabledFolders) plus een eindcontrole `IsVisibleStandalone(user)`; een onzichtbaar item geeft dezelfde 404 als een onbestaand item.
  2. Kind = de gemeenschappelijke `IsKid(user)` uit `Core/Privacy/KidPolicy.cs` (geen eigen vlag); Hub-rol `kind` -> 403.
  3. Huishoudsignalen standaard uit op de server en per gebruiker opt-in in twee richtingen; k-anonimiteit telt alleen andere opt-in-delers dan de vrager (k >= 3); kinderen altijd uitgesloten; de beheerder kan `household_*` alleen op uit vergrendelen, nooit aanzetten. Volg BG-16 als het genomen is; anders de terugval (dan staat het huishoudsignaal hard uit en zegt het rapport dat).
  4. Uitleg en redenen verwijzen nooit naar een ander profiel; `userId` in query of body wordt genegeerd (gebruiker altijd uit het token).
  5. Draai JLT-13 en het functionele deel van JLT-11 (nieuw profiel en kind met MaxParentalRating=6 op het corpus; Sintel NL-12 blijft verborgen). Werk EVIDENCE (`B03-034`, `JLT-13`, `JLT-11`) bij; leg vast met P-GIT.
- **Tests (verplicht):** T-JL-PLUGIN (`--filter "FullyQualifiedName~Recommendations"`, daarna volledig) met een eigenschapstest over willekeurige huishoudens; de E2E uit bouwpunt 5. Negatieve tests: vrager + 2 opt-in-delers bij k=3 -> 0 `household_popular`; `PUT admin/users/{id}/settings` met `household_share_mine=true` -> 403; een IDOR-poging met een ander `userId` werkt alleen op het eigen profiel; `/why` op een verborgen item -> dezelfde 404 als een onbestaand ID; Hub-rol `kind` -> 403.
- **Poort:** P-jelly-leon (Snel + jobs plugins en image uit Volledig) + P-VEILIG + P-GIT + P-EERLIJK
- **Valkuilen:** V-055; V-050; V-003; V-102
- **Bewijs:** `B03-034` -> "Bezig" (Sim-getest); `JLT-13` -> "Bezig" met Sim-geslaagd of Sim-mislukt; `JLT-11` "Bezig". "NIET GEVALIDEERD (echte NAS): echte gebruikers en kinderprofielen van het huishouden (JLT-15)."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG (tegelijk; R-VEILIG VERPLICHT: privacy, kinderen, IDOR) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard (R-VEILIG N4)
- **Stop en vraag als:** BG-16 genomen is met een keuze die de code niet kan uitdrukken; de terugval van BG-03 een profiel als kind aanmerkt dat de testopzet als volwassene bedoelt.

### S-G2-28 - Aanbevelingen F2-5: API `/media/v1/recommendations` en events (B03-035)
- **Repo:** jelly-leon | **Fase:** P4 golf 2 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** nee (plugin-build en contracttests; de E2E kort achter stack.lock)
- **Werkpakketten en tests:** B03-035; gate G-F2-5; JLT-12
- **Vooraf:** S-G2-26 klaar; S-G1-12 en S-G1-14 klaar (Hub-JWT, foutcatalogus); S-G1-36 klaar (de rebuild gaat via de planner).
- **Al gedaan?** `grep -n "media/v1/recommendations" <WERKMAP>/jelly-leon/docs/openapi/jelly-leon-plugin.openapi.json | head -3 ; python3 -c "import json;print([(o['id'],o['status']) for o in json.load(open('<WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json')) if o['id'] in ('B03-035','JLT-12')])"` -> routes in OpenAPI en beide rijen: dan alleen de reviewers.
- **Lees eerst:** WP-JSON object `B03-035`; BOUWPLAN `#F2.5 API-contracten` (`#F2.5.1` tot en met `#F2.5.5`); `<WERKMAP>/jelly-leon/docs/adr/ADR-0030-b03-017-foutcatalogus-pipeline-en-1-mib-per-route.md#Besluit`; `<WERKMAP>/jelly-leon/docs/platform-v2/PLATFORM_CONTRACTEN.md` koppen "5. Gemeenschappelijke API-regels" en "7. Event-envelope"; TEST-JSON rij JLT-12
- **Bouw:**
  1. Routes volgens BOUWPLAN `#F2.5.3` en `#F2.5.4` (home, why, similar, feedback, settings/me met If-Match, onboarding, me/forget, status, rebuild via de planner, evaluate, exports, admin/provider-order met restore, admin/uninstall-prepare, admin/users/{id}/settings alleen vergrendelen, admin/orphans/cleanup, admin/copies/purge). Gebruiker altijd uit het token.
  2. Foutcodes uit de catalogus; Idempotency-Key op elke schrijvende route (herhaling geeft `Idempotent-Replay: true`, een ander verzoek met dezelfde sleutel 422 `idempotency_key_reused`, geen sleutel 400); `PUT` zonder If-Match 428, met verouderde ETag 412; 413 per route boven 1 MiB.
  3. A-HUB alleen met een Hub-JWT na een gepinde sleutelset (zonder pin 401 `not_linked`, rol `kind` 403).
  4. Connector-itemtypen `recommender_status`, `recommender_evaluation`, `backups`; events `media.recommender.rebuilt`, `.degraded`, `.recovered`, `.evaluated`, `.exported` via de ene outbox (drie segmenten; geen titels, gebruikers-, apparaat- of bibliotheeknamen of paden).
  5. Module uit: 404 `not_found` volgens ADR-0030 en besluit Z-19 (hoofdstuk 3; gekozen door de gebruiker op 2026-11-11). Schrijf de afwijking van WP-JSON B03-033 en B03-035 (501 `capability_unavailable`) letterlijk in de EVIDENCE-opmerking van `B03-035`. WP-JSON zelf niet wijzigen (dat is een documentatiestap in ai-server-manager).
  6. OpenAPI bijwerken; JLT-12 (feedback via de echte route) draaien; EVIDENCE (`B03-035`, `JLT-12`) en `EXCEL_TAKEN.json` bijwerken; P-GIT.
- **Tests (verplicht):** T-JL-PLUGIN (contracttests per route tegen het JSON-schema; `--filter "FullyQualifiedName~Recommendations"`, daarna volledig); T-JL-TOOLS; JLT-12 achter stack.lock. Negatieve tests: elke foutcode uit BOUWPLAN `#F2.5.2` wordt minstens een keer geraakt; de OpenAPI-diff van de bestaande Jellyfin-routes geeft 0 wijzigingen; een event met een titel of gebruikers-ID wordt door de schemacontrole geweigerd; zonder pin 401 `not_linked`; met de module uit geeft elke route onder `/media/v1/recommendations` 404 `not_found` aan een aangemelde gebruiker en nooit 501, en zonder geldige authenticatie 401 (besluit Z-19, ADR-0030 punt 2).
- **Poort:** P-jelly-leon (Snel + jobs plugins en image uit Volledig) + P-CONTRACT + P-VEILIG + P-GIT + P-EERLIJK
- **Valkuilen:** V-066; V-039; V-040; V-050; V-054; V-003
- **Bewijs:** `B03-035` -> "Bezig" (Sim-getest; gate G-F2-5 per onderdeel), in de opmerking letterlijk: "module uit geeft 404 volgens ADR-0030 en besluit Z-19; WP-JSON B03-033 en B03-035 zeggen 501 `capability_unavailable`"; `JLT-12` -> "Bezig" met Sim-geslaagd of Sim-mislukt. "NIET GEVALIDEERD (echte Hub): A-HUB alleen met de Hub-simulator; NIET GEVALIDEERD (echte NAS)."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG (tegelijk; R-VEILIG VERPLICHT: authenticatie, IDOR, van buiten bereikbare routes) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard (R-VEILIG N4)
- **Stop en vraag als:** een route alleen kan met een wijziging aan een bestaande Jellyfin-route; de 404 bij "module uit" niet via de bestaande pijplijn te halen is (`Core/Http/JlPipeline.cs` met de module in de routetabel) en dus een wijziging aan de pijplijn of aan ADR-0030 vraagt. Besluit Z-19 is genomen (404 zoals ADR-0030): niet opnieuw voorleggen en niet naar 501 bouwen.

### S-G2-30 - Apparaatprofielen F5-S1: module Devices waarneemt afspeeluitkomsten (B03-061)
- **Repo:** jelly-leon | **Fase:** P4 golf 2 | **Omvang:** groot | **Moeilijkheid:** gewoon | **Zwaar:** ja (PlaybackInfo-integratietest met echte Jellyfin-containers en drie browsers)
- **Werkpakketten en tests:** B03-061; gate F5-S1; JLT-64 (deel PlaybackInfo), JLT-65 (deel `devices.db`)
- **Vooraf:** Gate golf 1; S-P40-64 klaar (baseline B03-060: de Direct Play-ratio van het harnas is de vergelijking).
- **Al gedaan?** `ls <WERKMAP>/jelly-leon/plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Modules/Devices ; grep -rn "playback/outcomes\|GetTranscodingJob" <WERKMAP>/jelly-leon/plugins/JellyLeon/src --include=*.cs | head -3` -> de routes en de uitkomstopslag bestaan naast de prototypebestanden: dan alleen de reviewers. Bij het schrijven bevatte `Modules/Devices` alleen het prototype van golf 1 (`DevicesController.cs`, `DevicesListener.cs`, `DevicesModule.cs`: teller per methode en apparaat). Bouw daarop verder.
- **Lees eerst:** WP-JSON object `B03-061`; BOUWPLAN `#F5.8 Bouwfasen` (rij F5-S1); BOUWPLAN `#F5.4 Gegevens en bescherming`; BOUWPLAN `#F5.5.2 Endpoints`; PLUGIN `Modules/Devices/DevicesModule.cs`
- **Bouw:**
  1. `devices.db` onder `/config/data/jelly-leon/devices/` met migraties en forward-schematests; registerregels en UserDeleted (ook via `IEventConsumer<UserDeletedEventArgs>` en een dagelijkse afstemming met stroomonderbreker).
  2. Afspeeluitkomsten van alle clients via `ISessionManager.PlaybackStart`, `Progress`, `Stopped` en `ITranscodeManager.GetTranscodingJob` (PlayMethod, TranscodingInfo, TranscodeReasons, uitvoerpad, PID). Een uitkomst bewaart een combinatiesleutel en geen titel; `item_id` alleen 24 uur, ruwe rijen 30 dagen.
  3. Routes `GET /media/v1/devices/self`, `POST /media/v1/playback/outcomes`, `GET /media/v1/playback/sessions/{playSessionId}/explain`, `GET /media/v1/playback/stats`, `GET /media/v1/devices` (beheer; de Hub alleen geaggregeerd); export/import zonder ruwe uitkomsten (met `preview_hash` uit S-G1-20).
  4. Connector-itemtypen `device`, `playback_stats` en `gpu_lane`, health-checks; events `media.transcode.started`, `media.transcode.stopped`, `media.playback_attempt.failed` via de outbox. De budgetbeslisser van S-G1-38 krijgt de live-bezetting uit deze module.
  5. PlaybackInfo-integratietest: de vaste veldenlijst uit WP-JSON `B03-061` (Acceptatie) is voor 25 corpusitems x 3 browserprofielen + het MediaGuard-TV_PROFILE + het Android TV-profiel gelijk met en zonder module, bij een gelijke `encoding.xml`. De Direct Play-ratio van de module wijkt hooguit 1 sessie af van het harnas (B03-060).
  6. Differentiele controle-run (pluginproef met de module aan): buiten `devices.db`, de pluginconfiguratie en de geheimenmap geen verschil in `jellyfin.db` dat stock niet ook toont. EVIDENCE (nieuwe rij `B03-061`) en `EXCEL_TAKEN.json`; P-GIT.
- **Tests (verplicht):** T-JL-PLUGIN (`--filter "FullyQualifiedName~Devices"`, daarna volledig); T-JL-HARNAS (de vergelijking met B03-060); T-JL-IMAGE; de pluginproef op fork en stock. Negatieve tests: na het verwijderen van een testgebruiker 0 rijen met diens GUID of HMAC; na 24 uur (stuurbare klok) geen `item_id` meer in `playback_outcome`; een PlaybackInfo-antwoord met de module aan dat een veld uit de vaste lijst verandert laat de test falen; de module weigert nooit een afspeelstart.
- **Poort:** P-jelly-leon (Volledig) + P-HARDE-EIS + P-VEILIG + P-GIT + P-EERLIJK
- **Valkuilen:** V-073; V-077; V-005; V-055; V-102
- **Bewijs:** `B03-061` -> "Bezig" (Sim-getest; "Intel-iGPU-getest (ontwikkelmachine)" voor de transcodes); `JLT-64` en `JLT-65` blijven "Bezig". "NIET GEVALIDEERD (hardware): echte tv's en telefoons; NIET GEVALIDEERD (echte NAS) (JLT-49)."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-HARDE-EIS + R-VEILIG (tegelijk; R-HARDE-EIS VERPLICHT: gebruikers, migraties en de controle-run op `jellyfin.db`; R-VEILIG VERPLICHT: persoonsgegevens en de beheerroute) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard (R-HARDE-EIS N4, R-VEILIG N4)
- **Stop en vraag als:** de module een afspeelstart zou moeten weigeren of verlagen (no-go P4); de PlaybackInfo-vergelijking alleen gelijk is met een andere `encoding.xml`; het prototype van golf 1 een andere opslag heeft dan deze stap vraagt en ombouwen gegevens zou weggooien.

### S-G2-32 - Apparaatprofielen F5-S3: hardwareversnelling-assistent (B03-062)
- **Repo:** jelly-leon | **Fase:** P4 golf 2 | **Omvang:** groot | **Moeilijkheid:** hoog (schrijft in de upstream-configuratie `encoding.xml`; meting op de GPU) | **Zwaar:** ja (exclusief meetslot op de Arc-iGPU; geen emulator, Gradle of andere transcode tegelijk)
- **Werkpakketten en tests:** B03-062; gate F5-S3; JLT-43
- **Vooraf:** S-G2-30 klaar; S-G1-50 klaar (viewerclient: de MediaGuard-lanes lezen); BG-27 genomen of de terugval uit hoofdstuk 3 (de A310 niet voor live kijken; geen meting die MediaGuard raakt). D08 blijft open: op de ontwikkelmachine geldt een testbevestiging, geen D08-waarde.
- **Al gedaan?** `grep -rn "transcode/capabilities\|d08_unconfirmed" <WERKMAP>/jelly-leon/plugins/JellyLeon/src --include=*.cs | head -3 ; python3 -c "import json;print([(o['id'],o['status'],o.get('validatie')) for o in json.load(open('<WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json')) if o['id'] in ('B03-062','JLT-43')])"` -> de route en beide rijen bestaan: dan alleen de reviewers.
- **Lees eerst:** WP-JSON object `B03-062`; BOUWPLAN `#F5.3.4 GPU's: identificatie, topologie, meting per werkklasse en routering`; BOUWPLAN `#F5.4.2 Wat F5 nooit schrijft — en de ene uitzondering`; TEST-JSON rij JLT-43; `<WERKMAP>/jelly-leon/docs/adr/ADR-0018-b03-planner-en-gpu-budget.md#Besluit`
- **Bouw:**
  1. Detectie van render-nodes (sysfs PCI-slot, vendor, device, driver, renderD-pad) en de topologie (`two_gpu`, `a310_only`, `uhd770_only`, `single_other`, `none`); op de ontwikkelmachine `single_other` (`ls /dev/dri` gaf `renderD128`).
  2. Meting per node per werkklasse (decode; encode H.264, HEVC, AV1; VPP- en OpenCL-tonemapping; 1080p en 2160p): gelijktijdige streams boven 1,2 x realtime, fps en CPU; hooguit 10 s per stap; alleen zonder actieve sessies. Op een node waar MediaGuard encodeert: alleen "MediaGuard zelf pauzeren" (deeplink; de assistent wacht alleen-lezend tot de baan leeg is) of "meten met MediaGuard-last" (gelabeld). Nooit `/api/v1/app/control`.
  3. Voorstel voor `EncodingOptions` als diff met `preview_hash` (HardwareAccelerationType qsv, expliciet QsvDevice en VaapiDevice, decoding codecs, tonemapping, low-power alleen als alle nodes de LP-proef halen, AllowHevcEncoding/AllowAv1Encoding per topologie) en bij uitval van alle GPU's een voorstel "tijdelijk software-transcoding".
  4. Toepassen alleen door een Jellyfin-beheerder na een D08-bevestiging (zonder: 409 `d08_unconfirmed`), met back-up van `encoding.xml`, teruglezen en terugzetten; `EncoderAppPathDisplay` valt buiten elke vergelijking. Dit is de enige schrijfactie van F5 buiten de eigen opslag; de analyzer staat haar alleen in deze dienst toe (eigen test).
  5. `GET /media/v1/transcode/capabilities` met de meting per werkklasse en het label (gemeten, met MG-last, ongemeten).
  6. JLT-43 als A/B in een exclusief meetslot, minstens 3 runs afwisselend: stock 12.x met handmatige QSV (baseline B5b) tegen Jelly Leon met de assistent; DV-profiel-8.1- en HEVC-HDR10-transcodes in Chromium. Container met `--device /dev/dri` en de render-groep (BG-38).
  7. EVIDENCE (`B03-062`, `JLT-43`) en `EXCEL_TAKEN.json`; P-GIT.
- **Tests (verplicht):** T-JL-PLUGIN (`--filter "FullyQualifiedName~Devices"`); de A/B-meting achter het meetslot (`stack.lock`), minstens 3 runs. Negatieve tests: zonder D08-bevestiging wordt niets toegepast (409 `d08_unconfirmed`); terugzetten geeft een `encoding.xml` die byte-gelijk is aan de back-up (zonder `EncoderAppPathDisplay`); een gewone gebruiker krijgt 403 op toepassen; een nagebootste MediaGuard-lane "bezet" laat de assistent op die node niet meten; er gaat geen enkel verzoek naar `/api/v1/app/control` (verzoeklog van de MediaGuard-simulator).
- **Poort:** P-jelly-leon (Volledig) + P-VEILIG + P-HARDE-EIS + P-GIT + P-EERLIJK
- **Valkuilen:** V-057 (tijdmeting: exclusief slot en loadavg); V-009; V-014; V-099; V-103; V-098
- **Bewijs:** `B03-062` -> "Bezig"; `JLT-43` -> "Bezig" met Sim-geslaagd of Sim-mislukt, opmerking letterlijk "Intel-iGPU-getest (ontwikkelmachine)". "NIET GEVALIDEERD (hardware): A310 en UHD 770 en twee kaarten (D08 open); het NAS-deel staat in JLT-49 (STAPPEN_P6.md, N-P6-10)."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-VEILIG + R-HARDE-EIS (tegelijk; R-VEILIG VERPLICHT: beheeractie die upstream-configuratie schrijft; R-HARDE-EIS VERPLICHT: MediaGuard wordt nooit bediend en zijn encode nooit geraakt) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); R-VEILIG N4; R-HARDE-EIS N4
- **Stop en vraag als:** QSV in de container alleen werkt met extra rechten; de assistent een waarde voor de NAS zou moeten invullen (D08); een meting MediaGuard zou raken.

### S-G2-34 - Spikes F5-S2 (b) en (e) in de server: MVC-actionfilter en DRM-fdinfo
- **Repo:** jelly-leon | **Fase:** P4 golf 2 | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** ja (korte proef in een container met een echte Jellyfin-server en `/dev/dri`)
- **Werkpakketten en tests:** B03-065, B03-068 (alleen de spikes F5-S2 (b) en (e); de werkpakketten zelf zijn golf 4); voorbereiding JLT-44
- **Vooraf:** S-G2-30 klaar.
- **Al gedaan?** `ls <WERKMAP>/jelly-leon/docs/adr | grep -i "f5\|spike" ; ls <WERKMAP>/jelly-leon/docs/platform-v2/test-evidence | grep -i "f5-s2"` -> een ADR (of ADR-paragraaf) met de uitkomst van (b) en (e) en een proefrapport: klaar.
- **Lees eerst:** BOUWPLAN `#F5.8 Bouwfasen` (rij F5-S2); BOUWPLAN `#F5.3.2 Componenten en ladder-trede`; BOUWPLAN `#F5.3.4 GPU's: identificatie, topologie, meting per werkklasse en routering`; `<WERKMAP>/jelly-leon/docs/adr/ADR-0033-b03-017-spike-istartupfilter-1-mib-voor-authenticatie.md` (vorm van een eerdere spike)
- **Bouw:**
  1. Spike (b): kan een MVC-actionfilter vanuit de plugin de antwoorden van de PlaybackInfo-route waarnemen (en later aanvullen) zonder upstream-code te wijzigen? Bouw een proef achter een schakelaar die standaard uit staat (zoals ADR-0033 met `JELLYLEON_SPIKE_STARTUPFILTER`).
  2. Spike (e): leest de module het videogeheugen per proces van een Intel-GPU uit DRM-`fdinfo` (`/proc/<pid>/fdinfo`) in de container als gebruiker 568?
  3. Per spike een besluit (gelukt, mislukt, voorwaardelijk) in een nieuw ADR met het eerstvolgende vrije nummer (`ls docs/adr | sort | tail -3`) en een proefrapport onder `docs/platform-v2/test-evidence/`.
  4. P-GIT. Geen productiecode die standaard aan staat.
- **Tests (verplicht):** T-JL-PLUGIN; de proef in een container achter `flock <WERKMAP>/.lokaal/stack.lock nice -n 10`. Negatieve test: met de schakelaar uit gedraagt de server zich als stock (PlaybackInfo-veldenlijst gelijk).
- **Poort:** P-jelly-leon (Snel + job plugins) + P-GIT + P-EERLIJK
- **Valkuilen:** V-099; V-103; V-072
- **Bewijs:** geen eigen rij; de uitkomst in de opmerking van `B03-061` ("spike F5-S2 (b)/(e): ..."). "Intel-iGPU-getest (ontwikkelmachine)". De werkpakketten B03-065 en B03-068 krijgen hier geen status.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** een spike alleen werkt met een wijziging in upstream-code (dat is een core-patch: besluit); `fdinfo` alleen als root leesbaar is.

### S-G2-35 - Spikes F5-S2 (c) en (f) in het harnas: dynamic-range via CDP en een stilte-orakel
- **Repo:** jelly-leon | **Fase:** P4 golf 2 | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** ja (Playwright met een echte Jellyfin-server)
- **Werkpakketten en tests:** B03-060 (orakel "audio niet stil", dat in S-P40-64 "niet gemeten" bleef); B03-065 (spike F5-S2 (c))
- **Vooraf:** S-G2-34 klaar (alleen omdat de baan jelly-leon een schrijver tegelijk heeft; geen inhoudelijke afhankelijkheid); S-P40-64 klaar.
- **Al gedaan?** `grep -n "setEmulatedMedia\|AnalyserNode" -r <WERKMAP>/jelly-leon/tools/b03-harnas | head -3` -> beide zitten in het harnas met tests: klaar.
- **Lees eerst:** BOUWPLAN `#F5.8 Bouwfasen` (rij F5-S2, (c) en (f)); `<WERKMAP>/jelly-leon/tools/b03-harnas/b03h/web.py`; `<WERKMAP>/jelly-leon/tools/b03-harnas/b03h/baseline.py` (meting `orakel`); `<WERKMAP>/jelly-leon/tools/b03-harnas/README.md`
- **Bouw:**
  1. Spike (c): in `b03h/web.py` via CDP `Emulation.setEmulatedMedia` de media-feature `dynamic-range` zetten en vaststellen of de webclient daarop een HDR- of SDR-pad kiest.
  2. Spike (f): een stilte-orakel met een AnalyserNode in de headless browser; het afspeelorakel van B03-060 krijgt daarmee "audio niet stil" (S-P40-64 bouwpunt 3 liet het open).
  3. Unit-tests in `tools/b03-harnas/tests/`; het besluit per spike in het ADR van S-G2-34 (zelfde ADR, eigen paragraaf) of een nieuw ADR.
  4. Draai de B03-060-meting opnieuw met het orakel en werk het bewijs bij; P-GIT.
- **Tests (verplicht):** T-JL-HARNAS. Negatieve tests: een corpusbestand met een stil audiospoor laat het orakel "stil" zeggen; een bestand met geluid niet; met `dynamic-range` op `standard` kiest de client niet het HDR-pad (of het rapport zegt eerlijk dat de client het niet uitleest).
- **Poort:** P-jelly-leon (Snel voor `tools/b03-harnas`; Volledig job b03-harnas) + P-GIT + P-EERLIJK
- **Valkuilen:** V-077; V-067; V-007; V-003
- **Bewijs:** `B03-060` blijft "Bezig" (opmerking: orakel "audio niet stil" nu gemeten); de spike-uitkomst (c) in de opmerking van `B03-061`. "NIET GEVALIDEERD (hardware): echte tv's en HDR-schermen."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** het orakel alleen werkt met een browserbuild die het harnas nu niet gebruikt (V-067).

### S-G2-36 - Spike F5-S2 (d) in de webclient: stall-detectie zonder extra haak
- **Repo:** jelly-leon-web | **Fase:** P4 golf 2 | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** ja (npm-productiebuild en browsertest met een echte Jellyfin-container)
- **Werkpakketten en tests:** B03-065 (alleen spike F5-S2 (d)); JLT-63 (controle dat de webclient gelijk blijft)
- **Vooraf:** S-G1-60 klaar (haakmodule); Gate golf 1.
- **Al gedaan?** `ls <WERKMAP>/jelly-leon-web/src/jelly-leon ; grep -rn "stall\|SHOW_VIDEO_OSD" <WERKMAP>/jelly-leon-web/src/jelly-leon 2>/dev/null | head -3` -> een fork-eigen proefmodule met tests en een uitkomst in `docs/platform-v2/PATCHES.md`: klaar.
- **Lees eerst:** BOUWPLAN `#F5.8 Bouwfasen` (rij F5-S2, (d)); BOUWPLAN `#F5.2.2 Webclient 12.4`; `<WERKMAP>/jelly-leon-web/src/components/playback/playbackmanager.js`; `grep -rn "SHOW_VIDEO_OSD" <WERKMAP>/jelly-leon-web/src` (onder meer `src/constants/eventType.ts`); `<WERKMAP>/jelly-leon-web/docs/platform-v2/PATCHES.md`
- **Bouw:**
  1. Een fork-eigen module onder `src/jelly-leon/` (pad staat in `tools/jelly-leon-web/fork_paths.txt`) die stalls en hun label afleidt uit de bestaande events van `playbackManager` en `SHOW_VIDEO_OSD`, zonder nieuwe haak in een upstream-bestand.
  2. Een proefpagina of test die de module laadt zonder dat een upstream-bestand haar aanroept (dezelfde regel als S-G1-60: geen aanroep in upstream-code zonder `JLW-NNNN`-regel).
  3. Uitkomst (gelukt, mislukt, voorwaardelijk) in `docs/platform-v2/PATCHES.md` onder de geplande haken en in het rapport; P-GIT.
- **Tests (verplicht):** T-JLW-STATISCH; T-JLW-NPM; T-JLW-E2E in modus fork en stock. Negatieve test: een gesimuleerde stall in een unit-test wordt herkend, een normale pauze niet; de patchregistercontrole blijft groen zonder nieuwe registerregel.
- **Poort:** P-jelly-leon-web (Volledig) + P-GIT + P-EERLIJK
- **Valkuilen:** V-072; V-067; V-003
- **Bewijs:** geen statuswijziging; de uitkomst in de opmerking van `B03-017` in jelly-leon-web ("spike F5-S2 (d): ..."). "NIET GEVALIDEERD (hardware): echte browsers op tv's."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** stall-detectie alleen kan met een extra haak in een upstream-bestand (dat is een patch met registerregel: besluit voor golf 4).

### S-G2-38 - Spike F5-S2 (g) in de clients: rolherkenning van de officiele Android-app
- **Repo:** jelly-leon-clients | **Fase:** P4 golf 2 | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** ja (emulator in een container met /dev/kvm)
- **Werkpakketten en tests:** B03-065, B03-069 (alleen spike F5-S2 (g)); JLT-63 (rol stock-native)
- **Vooraf:** Gate golf 1; S-P40-70 klaar (emulator stabiel); BG-38.
- **Al gedaan?** `ls <WERKMAP>/jelly-leon-clients/docs/platform-v2/test-evidence | grep -i "f5-s2\|rolherkenning"` -> een proefrapport bestaat: klaar.
- **Lees eerst:** BOUWPLAN `#F5.8 Bouwfasen` (rij F5-S2, (g)); BOUWPLAN `#F5.2.3 Clients (jelly-leon-clients)`; `<WERKMAP>/jelly-leon-clients/tools/clients/compat/android.py`; `<WERKMAP>/jelly-leon-clients/docs/adr/ADR-0011-clientcompatibiliteit-12x.md`
- **Bouw:**
  1. Stel in de telefoon-emulator met de officiele app (`client_compat.py android --bediend officieel`, lees eerst `android --help`) vast wat de server van de app ziet (Client-naam, DeviceProfile, NativeShell-kenmerken) en of de rol "officiele app" daaruit eenduidig te herkennen is zonder de app te wijzigen.
  2. Leg de herkenningsregel vast als voorstel in het ADR van deze repo (eerstvolgend vrij nummer of een paragraaf in ADR-0011) en het proefrapport onder `docs/platform-v2/test-evidence/`; P-GIT.
- **Tests (verplicht):** T-JLC-STATISCH; T-JLC-COMPAT voor de telefoon (de compat-commando's nemen de locks zelf). Negatieve test: de fork-app wordt door de regel niet als "officieel" herkend.
- **Poort:** P-jelly-leon-clients (Snel + het emulatordeel uit Volledig) + P-GIT + P-EERLIJK
- **Valkuilen:** V-021; V-076; V-014; V-128
- **Bewijs:** geen statuswijziging; de uitkomst in de opmerking van `B03-019` in jelly-leon-clients. "NIET GEVALIDEERD (hardware): echte telefoons."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** herkenning alleen kan door de officiele app te wijzigen.

### S-G2-40 - Segmenten F6-S1: module Segments, provider, eigen opslag en veilige publicatie (B03-071)
- **Repo:** jelly-leon | **Fase:** P4 golf 2 | **Omvang:** groot | **Moeilijkheid:** hoog (schrijft via `IMediaSegmentManager` in de tabel MediaSegments van `jellyfin.db`; migraties met back-up) | **Zwaar:** ja (differentiele controle-run met echte Jellyfin-containers)
- **Werkpakketten en tests:** B03-071, B03-007 (aanvulling F6, deel provider en publicatie); gate F6-S1; JLT-56 (onderdelen a tot en met f, g en i)
- **Vooraf:** Gate golf 1; S-P40-66 klaar (bevroren testset); BG-32 (genomen). BG-33 genomen of de terugval uit hoofdstuk 3 (alleen beheerders corrigeren; nieuwe segmenten in schaduwmodus). BG-36 NIET genomen: het gedrag bij "module uit" (eigen segmenten wissen of verbergen) wordt niet gebouwd; de rest van de stap wel.
- **Al gedaan?** `ls <WERKMAP>/jelly-leon/plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Modules | grep -i segment ; grep -rn "IMediaSegmentProvider\|segments.db" <WERKMAP>/jelly-leon/plugins/JellyLeon/src --include=*.cs | head -3 ; python3 -c "import json;print([(o['id'],o['status']) for o in json.load(open('<WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json')) if o['id'] in ('B03-071','JLT-56')])"` -> module, provider en beide rijen: dan alleen de reviewers. (STAPPEN_P4_GOLF3_4.md en STAPPEN_P5.md zoeken naar `segments.db` om vast te stellen of deze stap klaar is: gebruik die naam.)
- **Lees eerst:** WP-JSON objecten `B03-071` en `B03-007` (Uitvoering "Aanvulling F6"); BOUWPLAN `#F6.8 Bouwfasen` (rij F6-S1); BOUWPLAN `#F6.3.6 Publicatiemodel, schaduwmodus en meting`; BOUWPLAN `#F6.4 Gegevens en bescherming`; upstream `<WERKMAP>/jelly-leon/MediaBrowser.Controller/MediaSegments/IMediaSegmentProvider.cs`
- **Bouw:**
  1. Module `Modules/Segments` met schakelaar (standaard uit). `IMediaSegmentProvider` met vaste naam "Jelly Leon Segmenten" (provider-ID = MD5 van de naam; een test bewaakt dat); `Supports` alleen video in ingeschakelde bibliotheken; `GetMediaSegments` leest alleen `segments.db` en start nooit analyse.
  2. Publicatie gericht met `IMediaSegmentManager.CreateSegmentAsync`/`DeleteSegmentAsync` onder de eigen provider-ID; nooit `RunSegmentPluginProviders`, nooit `forceOverwrite`; segmenten van andere providers blijven ongemoeid. `CleanupExtractedData` wist alleen afgeleide caches.
  3. `segments.db` onder `/config/data/jelly-leon/segments/`, caches onder `/cache/jelly-leon/segments/`; migratie alleen na back-up en `integrity_check`. Schaduwmodus en QC-steekproef: niets wordt gepubliceerd zonder afgeronde steekproef of menselijke bevestiging.
  4. Wezen nooit automatisch wissen; stroomonderbreker bij meer dan 5 procent of meer dan 50 items; opstartcontrole op een alleen-lezen mediamount (een schrijfbare mount: geen analyse en status rood; S-G1-20 levert `MountCheck`); export/import met `preview_hash`; hoofdstuknamen als eerste signaal.
  5. "Alles depubliceren" haalt alleen de eigen MediaSegments-rijen weg (`segments.db` blijft). Het gedrag van "module uit" volgt BG-36; zonder besluit: niet bouwen en in het rapport zetten.
  6. Routes 1, 9, 12, 14 tot en met 16 en 18 tot en met 20 uit BOUWPLAN `#F6.5.4 Endpoints` (alleen deze nummers; de rest is golf 4), met de foutcatalogus, OpenAPI en de analyzer per namespace `Segments`.
  7. JLT-56 onderdelen a tot en met f, g en i als differentiele controle-run (pluginproef uitbreiden met de scenario's uit TEST-JSON JLT-56); het enige toegestane verschil met stock zijn MediaSegments-rijen met de eigen provider-ID. Geef de image van T-JL-IMAGE de tag `jelly-leon:lokaal-<korte commit>` zoals in S-G1-16 (vorige eigen tag verwijderen) en noem tag en image-ID in het rapport: S-G2-46 in jelly-leon-clients gebruikt hem. EVIDENCE (`B03-071`, `JLT-56`) en `EXCEL_TAKEN.json`; P-GIT.
- **Tests (verplicht):** T-JL-PLUGIN (`--filter "FullyQualifiedName~Segments"`, daarna volledig; met eigenschapstests: geen segment langer dan de mediaduur, geen overlap, gesorteerd); de analyzerproef; T-JL-IMAGE; de controle-run achter stack.lock. Negatieve tests: een segment van een andere provider blijft na publiceren en depubliceren staan; een opzettelijk mislukte migratie laat `segments.db` intact; een schrijfbare mediamount start geen analyse; 0 schrijfpogingen op media (sha256 van het corpus voor en na); een Unknown-segment wordt nooit gepubliceerd.
- **Poort:** P-jelly-leon (Volledig) + P-HARDE-EIS + P-VEILIG + P-GIT + P-EERLIJK
- **Valkuilen:** V-005; V-055; V-095; V-112; V-003; V-072
- **Bewijs:** `B03-071` -> "Bezig" (Sim-getest); `JLT-56` -> "Bezig" (onderdelen a-f, g, i met uitkomst; h volgt in golf 4); `B03-007` -> rij toevoegen of bijwerken met "aanvulling F6 begonnen: provider en publicatie (golf 2)". Zonder BG-36 letterlijk: "module uit: gedrag niet gebouwd, wacht op BG-36". "NIET GEVALIDEERD (echte NAS): eigen bibliotheek (JLT-59)."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-HARDE-EIS + R-VEILIG (tegelijk; R-HARDE-EIS VERPLICHT: schrijven in `jellyfin.db` via de upstream-manager, migraties, correcties die niet verloren mogen gaan; R-VEILIG VERPLICHT: beheerroutes en import) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** A-BOUW en A-HERSTEL N4 (moeilijkheid hoog); R-HARDE-EIS N4; R-VEILIG N4
- **Stop en vraag als:** publiceren alleen kan met `forceOverwrite` of door rijen van andere providers te raken; BG-36 nodig is om een test groen te krijgen; de controle-run een verschil buiten MediaSegments toont.

### S-G2-42 - Segmenten F6-S2: audiofingerprint-engine (B03-072)
- **Repo:** jelly-leon | **Fase:** P4 golf 2 | **Omvang:** groot | **Moeilijkheid:** gewoon | **Zwaar:** ja (bestandspas over de bevroren testset; meetslot)
- **Werkpakketten en tests:** B03-072, B03-007 (aanvulling F6, deel audio); gate F6-S2; JLT-52, JLT-53 (audiodeel), JLT-50 (alleen de typen Intro, Recap en Preview)
- **Vooraf:** S-G2-40 klaar; S-G1-34 klaar (bestandspas en featurecache); S-P40-66 klaar. BG-34: zonder bevestigde Pioneer One-labels is dat deel van JLT-53 "Geblokkeerd". WP-JSON B03-072 (veld Afhankelijkheid) noemt "B03-002/B03-006 (seizoensindeling en absolute nummering)": een zachte afhankelijkheid, geen wachtpunt. De partnerkeuze (bouwpunt 2) gebruikt de afleveringsvolgorde en seizoensgrenzen die upstream al levert (seizoen- en afleveringsnummer; de serie-instelling `DisplayOrder` in `MediaBrowser.Controller/Entities/TV/Series.cs`), en de acceptatie meet op de bevroren testset van B03-070, niet op anime-nummering. BOUWPLAN F6 noemt B03-002/B03-006 een raakvlak ("Raakvlakken: B03-002/B03-006 (anime-seizoen/absolute nummering)"). Later sluit aan: de seizoens- en absolute-nummering met correcties van S-G3-28 (B03-006) en de anime-splitsing van S-G3-30 (B03-002); S-G3-28 zet in zijn dossier of die de volgorde veranderen waarop de partnerkeuze steunt.
- **Al gedaan?** `grep -rln "chromaprint\|Hamming" <WERKMAP>/jelly-leon/plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Modules 2>/dev/null | head -3 ; python3 -c "import json;print([(o['id'],o['status']) for o in json.load(open('<WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json')) if o['id'] in ('B03-072','JLT-52')])"` -> engine en rijen bestaan: dan alleen de reviewers.
- **Lees eerst:** WP-JSON object `B03-072`; BOUWPLAN `#F6.3.3 Detectiepijplijn`; BOUWPLAN `#F6.1.4 Metrieken en drempels`; TEST-JSON rijen JLT-52, JLT-53 en JLT-50; BOUWPLAN `#10.12 Stabiele spoorsleutel`
- **Bouw:**
  1. Chromaprint en stilte uit de gemeenschappelijke bestandspas (S-G1-34; een ffmpeg-run per bestand), over de hele aflevering; het audiospoor via de stabiele spoorsleutel uit S-G1-20 (nooit de Jellyfin-index). Taken via de planner, nooit zelf een tool starten.
  2. Uitlijning met begrensde partners (hooguit k = 8 per aflevering: plus/min 4 buren, 2 over de seizoensgrens, leden van bekende families via een inverse index); indexstemmen plus Hamming; families met varianten; consensus over partners; snelheidscompensatie 25/23,976.
  3. Recap = overeenkomst met eerdere afleveringen aan het begin; preview = overeenkomst met de volgende aflevering.
  4. Evaluatie op de bevroren testset (nooit de devset) met het harnas van S-P40-66 via `GET /media/v1/segments/{itemId}?view=candidate`; per type n en Wilson-interval; onder de streef-n "smoke-gate (n = ...)". Baseline (b) met Intro Skipper alleen als spike S-IS slaagde (bewijs van S-P40-66).
  5. Kosten per codecklasse (CPU-seconden per mediaseconde, gelezen bytes) vastleggen. EVIDENCE (`B03-072`, `JLT-52`, `JLT-53`, `JLT-50`) en `EXCEL_TAKEN.json`; P-GIT.
- **Tests (verplicht):** T-JL-PLUGIN (`--filter "FullyQualifiedName~Segments"`); T-JL-HARNAS; de evaluatie achter het meetslot, minstens 3 runs met gelijke uitkomst. Negatieve tests: het negatieve geval zonder intro geeft 0 intro; geen intro-segment in een cold open; k = 8 vindt dezelfde families als alle paren (op een kleine set).
- **Poort:** P-jelly-leon (Volledig: jobs plugins, image, b03-harnas) + P-EERLIJK + P-GIT
- **Valkuilen:** V-005; V-057; V-077; V-098; V-097 (Pioneer One-labels alleen lokaal)
- **Bewijs:** `B03-072` -> "Bezig"; `JLT-52` -> "Bezig" met Sim-geslaagd of Sim-mislukt; `JLT-53` -> "Bezig" (audiodeel; cues volgen in golf 3, S-G3-22 in STAPPEN_P4_GOLF3_4.md); `JLT-50` -> "Bezig" (alleen Intro, Recap en Preview gemeten; Outro volgt in S-G2-44). "NIET GEVALIDEERD (echte NAS): eigen bibliotheek."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK (VERPLICHT: winstclaim)
- **Niveau:** standaard
- **Stop en vraag als:** de drempels alleen gehaald worden door af te stemmen op de testset; iemand labels van echte afleveringen zelf wil invullen (BG-34: alleen de gebruiker of een aangewezen persoon).

### S-G2-44 - Segmenten F6-S3: aftiteling, post-credit-bescherming en grensverfijning (B03-073)
- **Repo:** jelly-leon | **Fase:** P4 golf 2 | **Omvang:** groot | **Moeilijkheid:** gewoon | **Zwaar:** ja (beeldanalyse in vensters; meetslot; geen emulator of Gradle tegelijk)
- **Werkpakketten en tests:** B03-073, B03-007 (aanvulling F6, deel post-credit-bescherming); gate F6-S3; JLT-51 (nultolerantie, serverdeel), JLT-50 (type Outro)
- **Vooraf:** S-G2-42 klaar; BG-35 genomen of de terugval uit hoofdstuk 3 (alleen CPU).
- **Al gedaan?** `grep -rn "PostCreditGuardSeconds" <WERKMAP>/jelly-leon/plugins/JellyLeon/src --include=*.cs | head -3 ; python3 -c "import json;print([(o['id'],o['status']) for o in json.load(open('<WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json')) if o['id'] in ('B03-073','JLT-51')])"` -> code en rijen bestaan: dan alleen de reviewers.
- **Lees eerst:** WP-JSON object `B03-073`; BOUWPLAN `#F6.3.4 Post-credit-bescherming en grensregels (kern van de veiligheid)`; BOUWPLAN `#F6.3.5 Rekenbudget op de NAS`; TEST-JSON rij JLT-51; `<WERKMAP>/jelly-leon/docs/adr/ADR-0022-b03-post-credit-bescherming.md`
- **Bouw:**
  1. Gestapte beeldanalyse: (1) staart (laatste min(15 procent, 12 min), films 15 min) eerst alleen sleutelbeelden; (2) 2 fps 32x32-hash, blackdetect en verzadiging alleen in het kandidaatblok en plus/min 15 s rond grenzen; (3) scdet op volle fps alleen plus/min 3 s rond een grens. Decode volgens BG-35 (zonder besluit alleen CPU).
  2. Aftitelingdetectie en mid-/post-credit-detectie; bij een scene na de aftiteling per blok een Outro en de scene zelf in geen segment; Outro eindigt minstens `PostCreditGuardSeconds` (2,0 s) voor de scene; bij twijfel geen Outro over het onzekere deel; EOF-marge 1,0 s; geen nieuw segmenttype; Unknown nooit publiceren.
  3. Kosten per codecklasse (1080p H.264, 4K HEVC10) meten op de ontwikkelmachine.
  4. JLT-51 serverdeel: 0,0 s beschermde inhoud binnen een gepubliceerd overslaanbaar segment op de bevroren testset (n >= 30 beschermde scenes); Wilson-bovengrens van het schendingspercentage in het rapport. Het clientdeel van JLT-51 (afspeelpositie na "Sla aftiteling over" in elke client) volgt met de knoppen in golf 4; schrijf dat letterlijk in het rapport.
  5. EVIDENCE (`B03-073`, `JLT-51`, `JLT-50`) en `EXCEL_TAKEN.json`; P-GIT.
- **Tests (verplicht):** T-JL-PLUGIN (`--filter "FullyQualifiedName~Segments"`); T-JL-HARNAS; de evaluatie achter het meetslot. Negatieve tests: een post-credit-scene na een lange zwarte pauze valt in geen segment; een mid-credit-scene tussen twee aftitelingblokken valt in geen segment; met `PostCreditGuardSeconds` op 0 faalt de test op de grens (bewijs dat de test kan falen).
- **Poort:** P-jelly-leon (Volledig: jobs plugins, image, b03-harnas) + P-EERLIJK + P-GIT
- **Valkuilen:** V-005; V-057; V-098 (nultolerantie: een enkele schending is Sim-mislukt); V-003; V-014
- **Bewijs:** `B03-073` -> "Bezig"; `JLT-51` -> "Bezig" (serverdeel Sim-geslaagd of Sim-mislukt; clientdeel "niet uitgevoerd: knoppen volgen in golf 4"); `JLT-50` -> "Bezig" (nu alle vier de typen gemeten; "aantoonbaar beter" alleen met de drempels uit TEST-JSON JLT-50 en de bootstrap tegen Intro Skipper, anders de lagere claim). "NIET GEVALIDEERD (echte NAS); NIET GEVALIDEERD (hardware): A310 en UHD 770 (kosten)."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK (VERPLICHT: nultolerantie en winstclaim)
- **Niveau:** standaard
- **Stop en vraag als:** de nultolerantie van JLT-51 niet haalbaar is zonder de Outro-recall onder de ondergrens te laten zakken (keuze voor de gebruiker, niet de bouwer); BG-35 "hardware-decode" kiest en de container daarvoor extra rechten vraagt.

### S-G2-46 - Segmenten in de clients: hoofdstuksegmenten in stock-web en de Android TV-emulator
- **Repo:** jelly-leon-clients | **Fase:** P4 golf 2 | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** ja (emulator in een container met /dev/kvm; jelly-leon-image)
- **Werkpakketten en tests:** B03-071 (gate F6-S1: "stock-web en Android TV-emulator zien hoofdstuksegmenten"); JLT-63 (regressie)
- **Vooraf:** S-G2-40 klaar en gepusht (een lokale jelly-leon-image met de module Segments, gebouwd in S-G2-40 met T-JL-IMAGE en getagd als `jelly-leon:lokaal-<korte commit>`); S-G2-38 klaar (baan jelly-leon-clients).
- **Al gedaan?** `ls <WERKMAP>/jelly-leon-clients/docs/platform-v2/test-evidence | grep -i "segment"` -> een rapport met de Android TV-emulator en stock-web: klaar.
- **Lees eerst:** BOUWPLAN `#F6.8 Bouwfasen` (rij F6-S1, kolom Gate); BOUWPLAN `#F6.6.3 Clients`; `<WERKMAP>/jelly-leon-clients/tools/clients/compat/scenario.py`; `<WERKMAP>/jelly-leon-clients/tools/clients/compat/android.py`
- **Bouw:**
  1. Voeg aan het compat-harnas een scenario toe dat op een item met hoofdstuksegmenten (gepubliceerd door de module in een testinstantie) controleert dat de Android TV-emulator (fork-app en officiele app) de segmenten ontvangt via de ongewijzigde `GET /MediaSegments` en dat afspelen gelijk blijft aan stock. Het webdeel (stock jellyfin-web) draait in het harnas van jelly-leon; neem die uitkomst over met verwijzing.
  2. Draai het tegen de jelly-leon-image en tegen stock; bewaar het rapport onder `docs/platform-v2/test-evidence/`; werk `docs/platform-v2/BOUWVERIFICATIE_P4-0.md` niet bij (dat is P4-0); P-GIT.
- **Tests (verplicht):** T-JLC-STATISCH; T-JLC-COMPAT voor de tv-emulator. Negatieve test: met de module uit zijn de antwoorden van `GET /MediaSegments` gelijk aan stock en toont de client geen extra segment.
- **Poort:** P-jelly-leon-clients (Snel + het emulatordeel uit Volledig) + P-GIT + P-EERLIJK
- **Valkuilen:** V-021; V-076; V-014; V-128
- **Bewijs:** geen eigen rij in deze repo; de uitkomst gaat met verwijzing naar `B03-071` in jelly-leon (S-G2-50 neemt haar over). "NIET GEVALIDEERD (hardware): echte tv's."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** de emulator niet stabiel draait binnen 4 GiB (zie S-P40-70).

### S-G2-50 - Terug naar stock, compat-regressie en belastingtest met alle golf-2-modules (JLT-63, JLT-64, JLT-65, JLT-66; begin B03-007)
- **Repo:** jelly-leon | **Fase:** P4 golf 2 | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (exclusief meetslot; pluginproef op fork en stock; compat-rooktest)
- **Werkpakketten en tests:** B03-013 (bijdrage per module: terug naar stock), B03-019 (compat-regressie per module-oplevering), B03-007 (aanvulling F6: stand na golf 2), JLT-63, JLT-64, JLT-65, JLT-66 (met het deel "groepspauze en hervatten" dat in S-G1-40 open bleef)
- **Vooraf:** S-G2-10, S-G2-28, S-G2-32, S-G2-44 en S-G2-46 klaar.
- **Al gedaan?** `ls <WERKMAP>/jelly-leon/docs/platform-v2/test-evidence | grep -i "golf2\|golf-2"` -> een eindrapport (fork en stock) en een JLT-66-rapport met groepspauze van de huidige commit: dan alleen R-HARDE-EIS en R-EERLIJK.
- **Lees eerst:** TEST-JSON rijen JLT-63, JLT-64, JLT-65 en JLT-66; FASERING `#Gates per functie`; `<WERKMAP>/.lokaal/ketens/S-G1-40/RAPPORT-A-BOUW.md` (wat toen "niet uitgevoerd" was); `<WERKMAP>/jelly-leon/tools/jelly-leon/e2e/plugin_proef.py` (kop en `--help`); WP-JSON object `B03-013`
- **Bouw:**
  1. Pluginproef op fork en stock (zoals S-G1-80 bouwpunt 1 tot en met 3) met alle modules aan: Core, Devices, Quality, WatchTogether, Recommendations, Segments. Elke beschermde tabel gelijk aan stock buiten de toegestane verschillen (MediaSegments-rijen met de eigen provider-ID; `SimilarItemProviderOrder` alleen na de klik).
  2. JLT-64: per module "aan, uit en plugin verwijderd" gelijk aan stock op de vaste veldenlijst; JLT-63: compat-rooktest (`compat_api.py`, `upstream_gedrag_runtime.py`) en de stock-client-rooktest; neem de emulatoruitkomst van S-G2-46 over met verwijzing.
  3. Terug naar stock (B03-013): per module "Verwijderen voorbereiden" (waar die bestaat), plugin verwijderen, stock-image op dezelfde datamap starten; alleen de gedocumenteerde restanten blijven.
  4. JLT-66 opnieuw (het script van S-G1-40) met de module WatchTogether aan en het deel "groepspauze en hervatten", minstens 3 runs in een exclusief meetslot.
  5. Rapporten onder `docs/platform-v2/test-evidence/` met een naam die begint met `b03-golf2-eindrun-`; EVIDENCE en `EXCEL_TAKEN.json` (`B03-007` met de stand van de aanvulling F6 na golf 2: provider, audio en post-credit gebouwd; cues golf 3; knoppen, correctie en Hub golf 4); P-GIT.
- **Tests (verplicht):** T-JL-PLUGIN; T-JL-TOOLS; T-JL-COMPAT; de pluginproef op fork en stock; JLT-66 achter het meetslot. Negatieve tests: de proef faalt als een testmodule bewust een rij in `UserData` wijzigt (unit-test van `proef_lib`); JLT-66 met de planner-pauze uit in de testopstelling faalt.
- **Poort:** P-jelly-leon (Volledig) + P-HARDE-EIS + P-EERLIJK + P-GIT
- **Valkuilen:** V-098; V-005; V-112; V-057; V-009; V-032
- **Bewijs:** `JLT-63`, `JLT-64`, `JLT-65`, `JLT-66` -> "Bezig", Sim-geslaagd alleen als elk onderdeel is uitgevoerd; `B03-007` -> "Bezig". "NIET GEVALIDEERD (hardware): echte clients, A310 en UHD 770; NIET GEVALIDEERD (echte NAS) (JLT-69, N-P6-10)."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-HARDE-EIS (tegelijk; R-HARDE-EIS VERPLICHT: bewijs dat geen module kijkgeschiedenis of servergegevens raakt) -> A-HERSTEL -> R-EERLIJK (VERPLICHT: de uitkomst gaat de gate in)
- **Niveau:** standaard (R-HARDE-EIS N4)
- **Stop en vraag als:** een beschermde tabel verschilt buiten de toegestane verschillen; een OOM-kill in JLT-66; een stock-client breekt.

### S-G2-55 - Manifest en image na golf 2
- **Repo:** jelly-leon | **Fase:** P4 golf 2 | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** ja (image-build, imageproeven)
- **Werkpakketten en tests:** I24-24-03, I24-24-04; B03-021, B03-031, B03-061, B03-071 (alleen manifest en installatiedocument)
- **Vooraf:** S-G2-50 klaar; BG-07 genomen of de voorlopige waarden (hoofdstuk 3).
- **Al gedaan?** `git -C <WERKMAP>/jelly-leon log --oneline -3 -- deploy/manifest deploy/truenas` -> de laatste wijziging is van na S-G2-50 en noemt golf 2: dan alleen R-MANIFEST.
- **Lees eerst:** `<WERKMAP>/jelly-leon/deploy/manifest/jelly-leon.manifest.yaml`; `<WERKMAP>/jelly-leon/deploy/truenas/CUSTOM_APP.md`; `<WERKMAP>/.lokaal/plan/uit/POORTEN.md#P-INSTALLATIE`; de rapporten van S-G1-70 (`<WERKMAP>/.lokaal/ketens/S-G1-70/RAPPORT-A-BOUW.md`)
- **Bouw:**
  1. Loop het manifest na op wat golf 2 toevoegt (vier modules, hun databases onder `/config/data/jelly-leon/`, caches onder `/cache/jelly-leon/`, `/dev/dri` voor de assistent): geen nieuwe opslagregel, poort, capability of omgevingsvariabele zonder ADR; geen `HUB_*`-naam; geen proefschakelaar van een spike in het manifest of formulier.
  2. `deploy/truenas/CUSTOM_APP.md`: de nieuwe modules staan standaard uit; hoe een beheerder ze aanzet in het dashboard van Jelly Leon; alleen formulierstappen en schermen, geen YAML, compose of terminal.
  3. Resources volgens BG-07 of de voorlopige waarden met de zin dat de batchmodules op de NAS uit blijven; `image.digest` blijft `null`.
  4. Image opnieuw bouwen, taggen als `jelly-leon:lokaal-<korte commit>` (vorige eigen tag verwijderen), grootte tegen de grens uit ADR-0017; `manifest_rapport.py`; EVIDENCE (`I24-24-03`, `I24-24-04`) en `EXCEL_TAKEN.json`; P-GIT.
- **Tests (verplicht):** T-JL-TOOLS (`test_manifest_1_2.py`, `test_manifest_1_3.py`, `test_manifest_rapport.py`); T-JL-IMAGE. Negatieve test: een manifest met een `HUB_`-naam of host-netwerk laat de controle falen; de image met lege `/config` meldt niet "healthy" voor de server antwoordt (V-068).
- **Poort:** P-jelly-leon (Volledig: jobs manifest en image) + P-INSTALLATIE + P-CONTRACT + P-GIT + P-EERLIJK
- **Valkuilen:** V-096; V-068; V-053; V-088; V-012
- **Bewijs:** `I24-24-03` en `I24-24-04` blijven "Bezig" (Sim-getest). "NIET GEVALIDEERD (echte NAS): het formulier van TrueNAS is niet ingevuld; de installatie staat in `<WERKMAP>/.lokaal/plan/uit/STAPPEN_P6.md`."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-MANIFEST (tegelijk; R-MANIFEST VERPLICHT) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** golf 2 een extra capability, apparaat of opslagregel vraagt die geen ADR heeft (besluit); de image boven de grens uit ADR-0017 komt.

### S-G2-70 - Controlelijsten I06 (Jellyfin) en I24 (Jelly Leon-release) voor de gebruiker
- **Repo:** jelly-leon-platform | **Fase:** P4 (installatiedocumenten; mag naar voren zodra de voorwaarden kloppen) | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** I06-06-01 tot en met I06-06-08; I24-24-01 tot en met I24-24-06 (alleen de controlelijst voor de gebruiker; de uitvoering op de NAS is P6)
- **Vooraf:** S-P2-420 in `<WERKMAP>/.lokaal/plan/uit/STAPPEN_P2.md` klaar (het halve werk van de P2-review in jelly-leon-platform is dan opgeruimd); S-G1-70 klaar (manifest van Jelly Leon na golf 1). D07: zonder meting beschrijft I06 het Jellyfin-deel alleen "als D07 een Jellyfin meet".
- **Al gedaan?** `ls <WERKMAP>/jelly-leon-platform/install/checklists/` -> bestaan `I06_JELLYFIN.checklist.yaml` en `I24_UNIVERSELE_MEDIASERVER.checklist.yaml` (namen volgens de bestaande vorm `I0x_<NAAM>.checklist.yaml`) en is `make manifesten` groen: klaar. Bij de overdracht stonden er alleen I01 en I02.
- **Lees eerst:** `<WERKMAP>/ai-server-manager/docs/platform-v2/03_INSTALLATIE/I06_JELLYFIN.md`; `<WERKMAP>/ai-server-manager/docs/platform-v2/03_INSTALLATIE/I24_UNIVERSELE_MEDIASERVER.md`; `<WERKMAP>/jelly-leon-platform/docs/adr/ADR-0015-controlelijsten-i01-i02.md`; `<WERKMAP>/jelly-leon-platform/schemas/checklist-v1.schema.json`; `<WERKMAP>/jelly-leon-platform/tools/checklists.py`
- **Bouw:**
  1. Maak twee controlelijsten in de vorm van `install/checklists/I01_TRUENAS_BASIS.checklist.yaml` (`kind: checklist`, `install.method: none`): een stap per Excel-ID, met wat de gebruiker in de TrueNAS-web-UI of in het dashboard doet, wat de Hub alleen-lezend meet, en de validatie per stap ("NIET GEVALIDEERD (echte NAS)" of "(hardware)"). Geen terminal, geen YAML of compose als installatieweg, geen voorbeeldwaarden.
  2. I24: de installatie zelf is de Custom App van jelly-leon (`<WERKMAP>/jelly-leon/deploy/truenas/CUSTOM_APP.md`); de controlelijst verwijst daarnaar (`wijze: verwijzing`) en dupliceert het formulier niet. I24-24-04 "Staging deployment": een nieuwe app naast Emby, media alleen-lezen, Emby blijft draaien.
  3. I06: Emby blijft de mediaserver van de gebruiker; de lijst beschrijft de inventaris, de back-upgate en het Jellyfin-deel alleen voor het geval D07 een Jellyfin meet. Geen stap zet Emby uit of wijzigt Emby (HARDE EIS).
  4. Werk `tools/checklists.py` alleen bij als het ID's hard noemt (lees de code); voeg de rijen toe aan de tests in `tests/repo/test_checklists.py`; werk `docs/platform-v2/EVIDENCE.json` en `EXCEL_TAKEN.json` bij; P-GIT.
- **Tests (verplicht):** `make manifesten` (bevat `tools/checklists.py`); `make test-repo` zoals P-jelly-leon-platform "4. Volledig" punt 8. Negatieve tests: een stap met het woord "terminal" of een shellcommando faalt in `tools/checklists.py`; een stap zonder validatie of met "Gereed" faalt.
- **Poort:** P-jelly-leon-platform (Snel: "Manifesten" en "Kopieen") + P-INSTALLATIE + P-HARDE-EIS (leeslijst) + P-GIT + P-EERLIJK
- **Valkuilen:** V-096; V-097; V-069; V-119
- **Bewijs:** de I06- en I24-rijen in jelly-leon-platform -> "Geblokkeerd" met "NIET GEVALIDEERD (echte NAS): uitvoering door de gebruiker op de NAS (STAPPEN_P6.md, S-P6-50 en N-P6-09); D07 open". Rijen die in jelly-leon of jelly-leon-clients al "Bezig" zijn blijven daar staan.
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-MANIFEST + R-HARDE-EIS (tegelijk; R-MANIFEST VERPLICHT: installatiedocumenten; R-HARDE-EIS VERPLICHT: Emby blijft, overname en terugval) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard (R-HARDE-EIS N4)
- **Stop en vraag als:** het schema of `tools/checklists.py` een I24-lijst weigert omdat I24 wel een installatie heeft (de regisseur legt dan voor: (1) alleen I06 als controlelijst, I24 blijft bij het manifest en `CUSTOM_APP.md` in jelly-leon; (2) een uitbreiding van het controlelijstformaat met een ADR; (3) iets anders); een stap alleen te beschrijven is met een terminal.

### S-G2-72 - Controlelijst I22 Navidrome (alleen na besluit D18)
- **Repo:** jelly-leon-platform | **Fase:** P4 | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** I22-22-01 tot en met I22-22-05
- **Vooraf:** S-G2-70 klaar; besluit D18 (`<WERKMAP>/.lokaal/plan/uit/BESLUITEN_EN_BLOKKADES.md`, kop "D18 — Navidrome (optioneel)") is "ja". Zonder besluit of bij "nee" start deze stap niet; de I22-rijen blijven "Niet gestart" met de reden "D18 open" of "D18: nee".
- **Al gedaan?** `ls <WERKMAP>/jelly-leon-platform/install/checklists/ | grep -i "I22"` -> de lijst bestaat en `make manifesten` is groen: klaar.
- **Lees eerst:** `<WERKMAP>/ai-server-manager/docs/platform-v2/03_INSTALLATIE/I22_NAVIDROME_OPT.md`; de controlelijsten van S-G2-70; `<WERKMAP>/jelly-leon-platform/schemas/checklist-v1.schema.json`
- **Bouw:**
  1. Controlelijst I22 in dezelfde vorm als S-G2-70; stap I22-22-01 "Value gate" is de vergelijking die de gebruiker maakt; installeren gebeurt als standaard TrueNAS-app (catalogus of Custom App) volgens de manifeststandaard, nooit met YAML of compose.
  2. Tests en EVIDENCE zoals S-G2-70; P-GIT.
- **Tests (verplicht):** `make manifesten`; `make test-repo`. Negatief: zoals S-G2-70.
- **Poort:** P-jelly-leon-platform (Snel: "Manifesten") + P-INSTALLATIE + P-GIT + P-EERLIJK
- **Valkuilen:** V-096; V-097
- **Bewijs:** I22-rijen -> "Geblokkeerd" met "NIET GEVALIDEERD (echte NAS): uitvoering door de gebruiker (STAPPEN_P6.md, N-P6-08)".
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-MANIFEST (tegelijk; R-MANIFEST VERPLICHT) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** D18 niet "ja" is.

### S-G2-90 - Gate golf 2
- **Repo:** geen (A-GATE leest in jelly-leon, jelly-leon-web, jelly-leon-clients en jelly-leon-platform) | **Fase:** P4 golf 2 | **Omvang:** klein | **Moeilijkheid:** gewoon | **Zwaar:** nee
- **Werkpakketten en tests:** B03-021, B03-031, B03-032, B03-033, B03-034, B03-035, B03-061, B03-062, B03-071, B03-072, B03-073, B03-007; JLT-10, JLT-11, JLT-12, JLT-13, JLT-16, JLT-17, JLT-43, JLT-50, JLT-51, JLT-52, JLT-53, JLT-56, JLT-63, JLT-64, JLT-65, JLT-66
- **Vooraf:** S-G2-55, S-G2-46, S-G2-36, S-G2-38 en S-G2-70 klaar; S-G2-72 klaar of D18 niet "ja".
- **Al gedaan?** `ls <WERKMAP>/.lokaal/ketens/GATE-GOLF-2/RAPPORT-A-GATE.md` -> bestaat het rapport en heeft de gebruiker gekozen: klaar.
- **Lees eerst:** FASERING `#Gates per functie` en `#3. Golven en werkpakketten` (rij Golf 2); hoofdstuk 9.3 van dit bestand; EVIDENCE van de vier repos; de rapporten van S-G2-50
- **Bouw:**
  1. A-GATE loopt de afvinklijst van hoofdstuk 9.3 af en leest bij elk punt het bewijs zelf. Een punt zonder bewijs is "niet gehaald".
  2. A-GATE controleert de no-go's van P4 (hoofdstuk 2) en of elke stap van golf 2 de verplichte reviewrapporten heeft.
  3. A-GATE schrijft `<WERKMAP>/.lokaal/ketens/GATE-GOLF-2/RAPPORT-A-GATE.md`: per functiegate gehaald, niet gehaald of open met reden; apart wat alleen in de simulator of op de iGPU is gemeten en welke winstclaims "smoke-gate" of "functioneel aangetoond (synthetisch)" zijn.
  4. De regisseur legt de uitkomst met een keuzemenu voor: (1) doorgaan naar golf 3 (STAPPEN_P4_GOLF3_4.md); (2) eerst de genoemde punten herstellen; (3) iets anders. Faalde de WT-1-gate: dan staat in het keuzemenu ook de core-patch `JL-NNNN` "SyncPlay-uitbreidingspunt" (B03-021).
  5. Daarna: Excel bijwerken en STATUS (hoofdstuk 9).
- **Tests (verplicht):** A-GATE draait geen builds. Controle: `python3 -m json.tool <EVIDENCE> > /dev/null` per repo. Negatieve controle: `grep -n '"Gereed"\|"Geslaagd"' <EVIDENCE>` zonder treffer; een rij "Sim-geslaagd" met een onderdeel "niet uitgevoerd" is een bevinding (V-098).
- **Poort:** P-EERLIJK + P-HARDE-EIS (leeslijst) + P-EXCEL
- **Valkuilen:** V-098; V-034; V-099; V-108; V-006
- **Bewijs:** geen eigen EVIDENCE-rij; het gate-rapport is het bewijs.
- **Agents:** A-GATE (VERPLICHT) -> regisseur legt voor aan de gebruiker. Korte keten: alleen lezen en oordelen.
- **Niveau:** A-GATE N4 (einde van een golf, niet van een fase)
- **Stop en vraag als:** een no-go waar is; een verplicht reviewrapport ontbreekt; de gebruiker niet kiest (golf 3 start dan niet).

---

## 9. Fase-afsluiting

Dit bestand heeft drie gates: Gate P4-0 (S-P40-95, einde van de fase P4-0), Gate golf 1 (S-G1-90) en Gate golf 2
(S-G2-90). Fase P4 zelf eindigt pas na golf 4 (STAPPEN_P4_GOLF3_4.md, S-G4-95). Na elke gate van dit bestand:
A-GATE met de lijst hieronder -> 9.4 (Excel) -> 9.5 (STATUS.md en VOORTGANG.md) -> 9.6 (melden). Niemand slaat een
onderdeel over.

Zo oordeelt A-GATE per eis (AGENTEN.md, prompt "A-GATE"):

- **VOLDAAN** alleen als hij het bewijs zelf heeft gezien (bestand, commit op de remote, CI-run op die commit, of het
  commando zelf gedraaid). Een rapport van een bouwer of een afgevinkte regel in VOORTGANG.md is geen bewijs.
- **ALLEEN OP DE ECHTE NAS TE BEWIJZEN** als het simulatordeel bewezen is, de eis daarnaast de NAS, hardware of een
  account vraagt, en de EVIDENCE-regel "NIET GEVALIDEERD (...)" met wat nog nodig is draagt.
- **NIET VOLDAAN** in elk ander geval (test ontbreekt, kan niet falen, is overgeslagen of rood; bewijs mooier dan de
  meting; blokkadetekst ontbreekt).

De nummers G0-nn, G1-nn en G2-nn zijn nummers van dit plan, geen ID's uit ALLE_IDS.txt.

### 9.1 Gatecontrole P4-0 (afvinklijst voor A-GATE in S-P40-95)

Bron: FASERING `#Gate P4-0 (vóór elk B03-modulewerk)`; `<WERKMAP>/ai-server-manager/docs/platform-v2/01_ARCHITECTUUR/06_FASERING_EN_GATES.md`,
koppen "Fase P4-0 — Jellyfin 12.x als basis" en "Gate matrix" (rijen "Voor P4 (B03-functies)").

| Nr | Eis | Geleverd door | Zo controleert A-GATE | Hoogste oordeel in P4-0 |
|---|---|---|---|---|
| G0-01 | B03-014 en B03-015 Sim-getest | S-P40-20, S-P40-30, S-P40-82 (assistent, geen gate-eis) | EVIDENCE jelly-leon en media-guard-ultimate: rijen B03-014 en B03-015 "Bezig" met "Sim-getest" en de blokkadetekst | NAS (S-P6-32, S-P6-33) |
| G0-02 | JLT-70 tot en met JLT-73 Sim-geslaagd (ook tegen jelly-leon:12.x) | S-P40-30, S-P40-32, S-P40-70, S-P40-92 | per rij de validatie en het rapport onder `test-evidence`; JLT-73 alleen Sim-geslaagd met de contracttest van media-guard-ultimate tegen de Jelly Leon-image (RESULTS.md); JLT-70 alleen met het emulatordeel | V |
| G0-03 | JLT-60 en JLT-61 (onderdelen a en b) Sim-geslaagd | S-P40-70, S-P40-92, S-P40-45 | JLT-61 (b) is bij de overdracht Sim-mislukt en vraagt een 12.y-tag: zonder S-P40-45 "NIET VOLDAAN" met de reden, ter keuze aan de gebruiker (hoofdstuk 2, "Drie open gate-eisen") | V of open |
| G0-04 | JLT-62 Sim-geslaagd | geen bouwstap zolang D07 geen Jellyfin meet | rij JLT-62 "Niet gestart" met reden "alleen als D07 een Jellyfin meet"; open gate-eis ter keuze aan de gebruiker | open |
| G0-05 | JLT-64 (met de bestaande plugin) Sim-geslaagd | S-P40-40, S-G1-10 | rij JLT-64 en het rapport van de pluginproef; het onderdeel "upstream-testsuite met de plugin" staat er eerlijk bij | V |
| G0-06 | JLT-63 rooktestdeel Sim-geslaagd | S-P40-40, S-P40-70, S-P40-90, S-P40-92 | `docs/platform-v2/CLIENT_COMPAT_MATRIX.md` kop 4 met datum; Swiftfin "NIET GEVALIDEERD (Mac/Xcode)" | NAS (N-P6-09) |
| G0-07 | JLT-67 Sim-geslaagd | S-P40-45 (voorwaardelijk) | zonder 12.y-tag "NIET VOLDAAN" met de reden; open gate-eis ter keuze | open |
| G0-08 | `JL_RUNTIME_IMAGE` op de 12.x-digest | bestond al (S-P40-10 stelt vast) | `grep -n "JL_RUNTIME_IMAGE:" <WERKMAP>/jelly-leon/.github/workflows/jelly-leon-ci.yml <WERKMAP>/jelly-leon/.github/workflows/upstream-sync.yml` gelijk aan de digest in `tools/jelly-leon/baseline.json` | V |
| G0-09 | `UPSTREAM_GEDRAG.md` met werkende CI-runner | S-P40-40 | `upstream_gedrag_check.py --overzicht` zelf draaien; de CI-job die het register draait groen op de laatste commit; V-126: `upstream-sync.yml` nooit op GitHub gedraaid, dat staat er eerlijk bij | V |
| G0-10 | Δ-MG-AUTH en Δ-MG-DUAL opgeleverd met contracttest; de Emby-koppeling onderbreekt nooit | S-P2-600, S-P2-610 (STAPPEN_P2.md), S-P40-20 | RESULTS.md met een run tegen de stock-server en tegen de Jelly Leon-image; test `test_b6_jellyfin_valt_weg_emby_blijft_gevolgd`; EVIDENCE C1.3-MGU-04 | NAS (S-P6-33) |
| G0-11 | BG-01 vastgelegd; voorlopige manifestresources (4 CPU's, 4096 MiB, batchmodules standaard uit) | bestond (S-P40-10 stelt vast) | B03_BESLUITEN.md (BG-01); `deploy/manifest/jelly-leon.manifest.yaml` (`resources`) | V |
| G0-12 | Baselines opnieuw gemeten op exact de 12.x-tag en -digest van de forkbasis | S-P40-50 | bewijs met label `definitief-forkbasis` en vaste digest; controle-run stock tegen Jelly Leon met 0 verschillen buiten de uitzonderingen | V |
| G0-13 | Gate matrix: "proefmigratie 10.11 → 12.x op een kopie geslaagd" | S-P40-70, S-P40-92 (JLT-60) | rij JLT-60 met het emulatordeel en de upgradeproef; geen verschil per gebruiker zonder akkoord | V (proef op een kopie in de simulator; echt: NAS) |
| G0-14 | No-go's: verschil in het per-gebruikerrapport zonder akkoord; terugzetten niet bewezen; een schrijfactie naar Emby; stock-clients breken; `EnableLegacyAuthorization` weer aan zonder besluit; B03-batch op de NAS zonder Δ-MG-AUTH | alle stappen | proxylog van de proefrun (0 verzoeken anders dan GET); rollback- en upgradeproef; stock-client-rooktest; `grep -rn "EnableLegacyAuthorization" <WERKMAP>/jelly-leon/deploy` | V |
| G0-15 | Review van al het werk dat P4-0 en golf 1 vooraf ging | S-P2-800 (STAPPEN_P2.md), S-G1-17 | de acht regels C1.3-JL-01..04 en C1.3-ALG-01..04 met de review in `bewijs`/`opmerking`, en de rij `REVIEW-jelly-leon-golf-1`; reviewrapporten in `<WERKMAP>/.lokaal/ketens/S-P2-800/` en `<WERKMAP>/.lokaal/ketens/S-G1-17/`; geen open bevinding zonder stap-ID | V |
| G0-16 | Bewijs eerlijk en repos schoon | elke stap | in de vier repos: `git status --short` leeg, `git rev-list --count @{u}..HEAD` 0, CI groen op de laatste commit; geen "Gereed" of "Geslaagd" in EVIDENCE | V |

### 9.2 Gatecontrole golf 1 (afvinklijst voor A-GATE in S-G1-90)

Bron: FASERING `#Gate golf 1 (vóór elk functiewerk in P4)`; 06_FASERING_EN_GATES.md, kop "Gate matrix", rij "Eén
plugin met modules + belastingtest binnen de manifestresources".

| Nr | Eis | Geleverd door | Zo controleert A-GATE | Hoogste oordeel |
|---|---|---|---|---|
| G1-01 | ADR-B03-02 aanvaard (in jelly-leon: ADR-0016) en het prototype met twee modules bewezen: laadt op fork en stock; elke `/connector/v1`-route een keer | S-G1-10, S-G1-80 | ADR-0016 kop "Status"; de twee eindrapporten `b03-017-golf1-eindrun-*` (fork en stock) | V |
| G1-02 | JLT-68 Sim-geslaagd | S-G1-10, S-G1-12, S-G1-14, S-G1-80 | rij JLT-68 en het rapport met de genoemde onderdelen (routetabel, foutcatalogus, Hub-simulator met en zonder pin, kind, `jti`, verlopen token) | NAS en echte Hub (V-105) |
| G1-03 | JLT-64 en JLT-65 Sim-geslaagd met Core + prototype | S-G1-10, S-G1-18, S-G1-20, S-G1-80 | rijen JLT-64 en JLT-65; een onderdeel "niet uitgevoerd" (bijvoorbeeld de upstream-testsuite met de plugin) maakt het Sim-getest, niet Sim-geslaagd | V |
| G1-04 | Foutcatalogus-contracttest, analyzer en UserDeleted-test groen | S-G1-14, S-G1-16, S-G1-18 | T-JL-PLUGIN zelf draaien (`--filter "FullyQualifiedName~Foutcatalogus"`, `~Privacy`); de analyzerproef faalt op de proefassembly | V |
| G1-05 | Geheimen niet in XML, export of log | S-G1-12, S-G1-20 | de logscan van de pluginproef op testgeheimen (waarde, niet veldnaam) | V |
| G1-06 | Werker: smoketest, SBOM, geen auditok, torch of ctranslate2; groei van de image binnen de ADR-grens | S-G1-30, S-G1-70 | SBOM uit CI; smoketest met `--network none`; grens als getal in ADR-0017 (kop "Verificatie") en de gemeten groei | V |
| G1-07 | Planner: pauze binnen 5 s bij elke sessie; hooguit 2 threads en 1 GiB batch | S-G1-36 | het pauzerapport (minstens 20 metingen, slechtste waarde) en de negatieve tests | V (iGPU) |
| G1-08 | JLT-66 Sim-geslaagd of batchmodules op de NAS uit tot BG-07 | S-G1-40 | rij JLT-66 en het rapport; is het niet Sim-geslaagd of BG-07 niet genomen, dan staat "batchmodules op de NAS uit" in STATUS | V (iGPU) |
| G1-09 | Werkerbewaker: herstart binnen 10 s, 0 wezen, 0 zombies | S-G1-32 | het rapport van de herhaalproef (aantal herhalingen eerlijk) | V |
| G1-10 | MediaGuard-viewerclient (B03-009) alleen met witte lijsten en rolcontrole; geen sleutel in Jelly Leon (BG-04) | S-G1-50 | `MediaGuardTests.cs`; `grep -rni "mediaguard" <WERKMAP>/jelly-leon/plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Configuration` zonder sleutelveld; rij C1.3-JL-08 | echte Hub en MediaGuard (V-105) |
| G1-11 | No-go: dubbele routes; een gedeelde singleton die per module verschilt; OOM in de belastingtest | S-G1-80, S-G1-40 | `RoutetabelTests`; het JLT-66-rapport (OOM-teller) | V |
| G1-12 | Verplichte reviews van golf 1 gedaan, open bevindingen hersteld of met stap-ID doorgeschoven | elke stap; S-G1-17 | de rapporten `RAPPORT-R-VEILIG.md`, `RAPPORT-R-HARDE-EIS.md`, `RAPPORT-R-MANIFEST.md` per stap in `<WERKMAP>/.lokaal/ketens/` | V |
| G1-13 | Repos schoon, CI groen, bewijs eerlijk (jelly-leon, jelly-leon-web) | elke stap | zoals G0-16 | V |

### 9.3 Gatecontrole golf 2 (afvinklijst voor A-GATE in S-G2-90)

Bron: FASERING `#3. Golven en werkpakketten` (rij Golf 2, kolom Gate) en `#Gates per functie`; BOUWPLAN `#F1.8`,
`#F2.8`, `#F5.8` en `#F6.8` (kolom Gate).

| Nr | Eis | Geleverd door | Zo controleert A-GATE | Hoogste oordeel |
|---|---|---|---|---|
| G2-01 | WT-1-gate (a) tot en met (e): OpenAPI `/SyncPlay/*` gelijk; upstream-SyncPlay-tests groen met plugin aan; `Enabled=false` byte-gelijk; reconciliatie bewezen (minstens 50 herhalingen); health `down` bij inactieve decorator met gasten. Faalt (a) tot en met (d): besluit core-patch | S-G2-10 | rij B03-021 per onderdeel; het herhaalrapport | V |
| G2-02 | G-F2-1: `/Similar` schema gelijk; plugin laadt op stock met alleen deze module; terugval bewezen | S-G2-20 | rij B03-031; runtimecontroles UG-F2 | V |
| G2-03 | G-F2-2: stock opnieuw op de forkbasisdigest; M1 op D-ML tegen S-BEST of eerlijk "functioneel aangetoond (synthetisch)"; lektest geslaagd | S-G2-22 | rijen B03-032, JLT-10, JLT-11 | V |
| G2-04 | G-F2-3: JLT-16 en JLT-17 Sim-geslaagd | S-G2-24 | rijen JLT-16 en JLT-17 met de controle-run | V |
| G2-05 | G-F2-4: M7 = 0/0/0 in JLT-13 inclusief de negatieve tests | S-G2-26 | rij JLT-13 | V |
| G2-06 | G-F2-5: contracttests (schema's, foutcodes, idempotency, ETag, 413, A-HUB 401 `not_linked`, module uit 404 `not_found`) Sim-geslaagd | S-G2-28 | rij B03-035; de opmerking noemt letterlijk de afwijking "module uit geeft 404 volgens ADR-0030 en besluit Z-19; WP-JSON B03-033 en B03-035 zeggen 501" | V |
| G2-07 | F5-S1: module laadt op jelly-leon:12.x en stock 12.x; PlaybackInfo identiek met en zonder module; forward-schematest; differentiele controle-run | S-G2-30 | rij B03-061 en het integratierapport | V |
| G2-08 | F5-S3: JLT-43 Sim-geslaagd als A/B tegen B5b (Intel-iGPU-getest); D08 open, NAS-deel in JLT-49 | S-G2-32 | rij JLT-43 met "Intel-iGPU-getest (ontwikkelmachine)" | V (iGPU) |
| G2-09 | F5-S2: per uitgevoerde spike een besluit in een ADR ((b), (c), (d), (e), (f), (g); (a) is golf 4) | S-G2-34, S-G2-35, S-G2-36, S-G2-38 | de ADR's en proefrapporten | V |
| G2-10 | F6-S1: ABI-test 12.x; stock-web en Android TV-emulator zien hoofdstuksegmenten; JLT-56 (a-f, g, i) groen; 0 schrijfpogingen op media; analyzer 0 treffers | S-G2-40, S-G2-46 | rij JLT-56 per onderdeel; het rapport van S-G2-46 | V |
| G2-11 | F6-S2: JLT-52 en JLT-53 (audiodeel) op de testset; Intro-ondergrenzen | S-G2-42 | rijen JLT-52 en JLT-53; Pioneer One-deel "Geblokkeerd" zonder BG-34-labels | V |
| G2-12 | F6-S3: JLT-51 nultolerantie (n >= 30); Outro-ondergrenzen; kosten vastgelegd | S-G2-44 | rij JLT-51 (serverdeel; clientdeel golf 4) | V |
| G2-13 | JLT-63, JLT-64 en JLT-65 zonder regressie met alle modules aan; terug naar stock per module | S-G2-50 | de eindrapporten `b03-golf2-eindrun-*` | V |
| G2-14 | Winstclaims alleen tegen stock-best op dezelfde digest met n en interval op een bevroren testset; anders "smoke-gate" | S-G2-22, S-G2-42, S-G2-44 | elke EVIDENCE-regel met "beter" in de opmerking | V |
| G2-15 | Manifest en installatiedocumenten na golf 2; controlelijsten I06 en I24 (en I22 als D18 "ja") | S-G2-55, S-G2-70, S-G2-72 | P-INSTALLATIE; `make manifesten` in jelly-leon-platform | NAS (S-P6-50, N-P6-09) |
| G2-16 | No-go P4 (hoofdstuk 2): geen stock-client gebroken, geen afspeelstart geweigerd, geen schrijfactie in kijkgeschiedenis, geen media gewijzigd, geen B03-batch op de A310 terwijl MediaGuard encodeert | alle stappen | de rapporten van S-G2-50 en de reviewrapporten R-HARDE-EIS | V |
| G2-17 | Repos schoon, CI groen, bewijs eerlijk (vier repos) | elke stap | zoals G0-16 | V |

Vindt A-GATE in de bronnen een gate-eis die hier ontbreekt, dan meldt hij dat als tekortkoming van het PLAN; hij
voegt niets stilzwijgend toe en laat niets weg.

### 9.4 Excel bijwerken (na elke gate van dit bestand)

De regisseur doet dit zelf, volgens `<WERKMAP>/.lokaal/plan/uit/POORTEN.md#P-EXCEL`, vanuit de map
`<WERKMAP>/ai-server-manager`, en alleen als er in ai-server-manager geen keten open is
(`git -C <WERKMAP>/ai-server-manager status --short` leeg):

- [ ] `<WERKMAP>/.lokaal/excel-venv/bin/python -m pytest -q tools/excel/tests`
- [ ] `<WERKMAP>/.lokaal/excel-venv/bin/python tools/excel/update_excel.py --xlsx docs/platform-v2/08_EXCEL/TrueNAS_V2_Uitvoering_en_Afvinken.xlsx --evidence ../*/docs/platform-v2/EVIDENCE.json --program docs/platform-v2/EVIDENCE_PROGRAMMA.json`
- [ ] Dezelfde run nog een keer: nul wijzigingen (idempotent). Elke waarschuwing lezen; exitcode 2 of een
      onverklaarde waarschuwing: stoppen; de fout wordt in de EVIDENCE van die repo hersteld, niet in de Excel.
- [ ] Commit en push volgens P-GIT (Nederlands bericht met "P4-0", "P4 golf 1" of "P4 golf 2"); CI-job `excel` groen.
- [ ] Nooit "Gereed" of "Geslaagd"; de faseregel `P4-0` staat na S-P40-95 op "Bezig" met "Sim-getest; NIET
      GEVALIDEERD (echte NAS)".

### 9.5 STATUS.md en VOORTGANG.md bijwerken

- [ ] **STATUS.md** (`<WERKMAP>/ai-server-manager/docs/platform-v2/OVERDRACHT/STATUS.md`): een korte keten A-BOUW ->
      R-EERLIJK in ai-server-manager zet onder een kop per gate ("P4-0 ...", "P4 golf 1 ...", "P4 golf 2 ...") het
      oordeel van A-GATE letterlijk, de datum, de tabel G0/G1/G2 met het oordeel per eis, de open gate-eisen met de
      keuze van de gebruiker, en wat alleen op de echte NAS te bewijzen is met het onderdeel van STAPPEN_P6.md. Na
      Gate golf 1: of de batchmodules op de NAS uit blijven (BG-07, JLT-66). Doe dit VOOR de Excel-run van 9.4.
- [ ] **CONTRACT_1.3_CONFORMITEIT.md** in ai-server-manager wordt NIET gewijzigd (V-106); de stand staat in EVIDENCE.
- [ ] **Contractpunten voor ai-server-manager** die in dit bestand zijn gemeld (ADR-0028 "gekozen interpretaties",
      ADR-0033 "Gevolgen", ADR-0034 "Gevolgen", eventnamen uit S-G1-14, besluit Z-19 "module uit geeft 404": de
      acceptatie van B03-033 en B03-035 in WP-JSON) verzamelt de regisseur in VOORTGANG.md; ze gaan naar de eigenaar
      van het contract.
- [ ] **VOORTGANG.md** (door de regisseur): de gate afgevinkt met datum en het pad van het gate-rapport; tabel
      "Topmodel-inzet" aangevuld (S-P40-82 R-HARDE-EIS, S-G1-12 R-VEILIG, S-P40-95 A-GATE, plus escalaties); deel
      "Half werk uit ronde 3" voor jelly-leon afgevinkt met de commit van S-G1-15.

### 9.6 Melden aan de gebruiker

De regisseur meldt in het Nederlands, kort, en sluit af met een keuzemenu (vorm:
`<WERKMAP>/.lokaal/plan/uit/BESLUITEN_EN_BLOKKADES.md#0.5 Sjabloon van een keuzemenu`). Nergens "gereed" of "geslaagd".

1. **Uitkomst van de gate** met het aantal eisen per oordeel.
2. **Wat er nu staat**, per repo met de laatste commit en het run-ID van de CI.
3. **De HARDE EIS:** Emby is niet aangeraakt; de overnameproef liet 0 schrijfacties naar Emby zien en geen verschil
   per gebruiker zonder akkoord (gemeten tegen een Emby-testcontainer, niet tegen de echte Emby); MediaGuard volgt Emby
   en Jelly Leon zonder onderbreking (contracttest, niet op de NAS); geen plugin schrijft in kijkgeschiedenis.
4. **Wat NIET GEVALIDEERD is**, in gewone taal, met het onderdeel van STAPPEN_P6.md (N-P6-09, N-P6-10, N-P6-11).
5. **Open besluiten:** na P4-0 de drie open gate-eisen (JLT-61 b, JLT-62, JLT-67), BG-22, D07; na golf 1 BG-07; voor
   golf 2 BG-16, BG-27, BG-33, BG-35, BG-36 en D18 (Z-19 "module uit" is genomen: 404 zoals ADR-0030; de regisseur
   noemt alleen dat de afwijking van WP-JSON in het bewijs staat); na golf 2 de WT-1-uitkomst
   (core-patch ja/nee) en de besluiten van golf 3 (BESLUITEN_EN_BLOKKADES.md, koppen "2.4 Voor golf 3" en "2.5 Start
   golf 3").
6. **Inzet van het topmodel** met wat het opleverde.
7. **Keuzemenu**, bijvoorbeeld: (1) doorgaan met de volgende golf; (2) eerst een open besluit nemen; (3) eerst
   herstellen wat niet gehaald is; (4) stoppen en de stand laten staan. Geen PR en niets naar `main` zonder vraag.

---

## 10. Dekking

Elke rij is een ID. "Stap" is de stap van dit bestand die het ID bouwt, controleert of boekt; de EERSTE stap vult de
EVIDENCE-regel, de stappen erna leveren een deel. Een ID dat niet in dit deel hoort staat er met de reden en de plek
waar het wel wordt opgepakt. ID's in deel A, B en C staan in `<WERKMAP>/.lokaal/plan/uit/ALLE_IDS.txt`; de
contractpunten (C1.3-...) komen uit CONTRACT_1.3_CONFORMITEIT.md en staan NIET in ALLE_IDS.txt; REVIEW-ID's zijn
nieuwe EVIDENCE-regels van dit plan; Δ-MG-AUTH en Δ-MG-DUAL komen uit 06_FASERING_EN_GATES.md ("Gate matrix").

### 10.1 Deel A - Werkpakketten B03

| ID | Repo met de EVIDENCE-regel | Stap of reden |
|---|---|---|
| B03-001 | jelly-leon, jelly-leon-web, jelly-leon-clients | golf 0, gebouwd (P0/P1); niet in dit deel; NAS-delen N-P6-09 (STAPPEN_P6.md) |
| B03-002 | (nog geen regel; volgt uit de bouwstap) | universele bibliotheek; stond in geen golf van FASERING#3 en heeft geen object in WP-JSON b03; besluit Z-20 (2026-11-11, hoofdstuk 3): in P4 bouwen; per werkpakket eerst A-VERKEN, dan bouwstappen in een golf. Die stappen staan NIET in dit bestand: de eigenaar van `STAPPEN_P4_GOLF3_4.md` voegt ze daar toe (stap-ID's en EVIDENCE-regel volgen daar) |
| B03-003 | jelly-leon-clients (Geblokkeerd) | beschikbaarheid van clients; besluit Z-20 (2026-11-11, hoofdstuk 3): in P4 bouwen; per werkpakket eerst A-VERKEN, dan bouwstappen in een golf. Die stappen staan NIET in dit bestand: de eigenaar van `STAPPEN_P4_GOLF3_4.md` voegt ze daar toe (stap-ID's en EVIDENCE-regel volgen daar). Het clientdeel staat nu Geblokkeerd in jelly-leon-clients; NAS-deel N-P6-09 (STAPPEN_P6.md) |
| B03-004 | (aanvulling F5) | golf 4 (STAPPEN_P4_GOLF3_4.md); in dit deel alleen de voorbereiding via S-G2-32 (topologie en meting) |
| B03-005 | (aanvulling F5) | golf 4 (STAPPEN_P4_GOLF3_4.md) |
| B03-006 | (nog geen regel; volgt uit de bouwstap) | metadata en anime-mapping; besluit Z-20 (2026-11-11, hoofdstuk 3): in P4 bouwen; per werkpakket eerst A-VERKEN, dan bouwstappen in een golf. Die stappen staan NIET in dit bestand: de eigenaar van `STAPPEN_P4_GOLF3_4.md` voegt ze daar toe (stap-ID's en EVIDENCE-regel volgen daar). Voor B03-006 volgt BG-17 (BESLUITEN_EN_BLOKKADES.md, moment "bij B03-006") |
| B03-007 | jelly-leon | aanvulling F6 begint hier: S-G2-40 (rij aanmaken), S-G2-42, S-G2-44, S-G2-50 (stand na golf 2); afronding golf 3-4 (STAPPEN_P4_GOLF3_4.md) |
| B03-008 | (nog geen regel; volgt uit de bouwstap) | semantische scenezoeker; besluit Z-20 (2026-11-11, hoofdstuk 3): in P4 bouwen; per werkpakket eerst A-VERKEN, dan bouwstappen in een golf. Die stappen staan NIET in dit bestand: de eigenaar van `STAPPEN_P4_GOLF3_4.md` voegt ze daar toe (stap-ID's en EVIDENCE-regel volgen daar). WP-JSON B03-074 noemt de cue-extractie "gedeeld met B03-008"; die cue-extractie bouwt S-G1-34 (bestandspas) in dit deel |
| B03-009 | jelly-leon | S-G1-50; S-G1-17 (review), S-G1-80, S-G1-90; verzoekroute golf 3 |
| B03-010 | jelly-leon | S-G1-18 (deel IsKid); S-G1-15 (half werk, vaststellen); streamroutes golf 3 (S-G3-09, S-G3-10) |
| B03-011 | (nog geen regel; volgt uit de bouwstap) | offline downloaden; besluit Z-20 (2026-11-11, hoofdstuk 3): in P4 bouwen; per werkpakket eerst A-VERKEN, dan bouwstappen in een golf. Die stappen staan NIET in dit bestand: de eigenaar van `STAPPEN_P4_GOLF3_4.md` voegt ze daar toe (stap-ID's en EVIDENCE-regel volgen daar) |
| B03-012 | (nog geen regel; volgt uit de bouwstap) | live-tv en DVR; besluit Z-20 (2026-11-11, hoofdstuk 3): in P4 bouwen; per werkpakket eerst A-VERKEN, dan bouwstappen in een golf. Die stappen staan NIET in dit bestand: de eigenaar van `STAPPEN_P4_GOLF3_4.md` voegt ze daar toe (stap-ID's en EVIDENCE-regel volgen daar) |
| B03-013 | jelly-leon, jelly-leon-web, jelly-leon-clients | bijdrage per module: S-G2-10, S-G2-24, S-G2-40, S-G2-50; eindproef P6 |
| B03-014 | jelly-leon (en web, clients, media-guard-ultimate) | S-P40-10 (stand), S-P40-20, S-P40-45; gate S-P40-95 |
| B03-015 | jelly-leon | S-P40-30, S-P40-32, S-P40-80, S-P40-82; gate S-P40-95; echte overname N-P6-11 |
| B03-016 | jelly-leon, jelly-leon-clients | S-P40-50 (definitieve baselines), S-P40-70, S-P40-72, S-P40-90, S-P40-92 |
| B03-017 | jelly-leon, jelly-leon-web | S-G1-16 (rij), S-G1-17 (review), S-G1-10, S-G1-12, S-G1-14, S-G1-18, S-G1-20, S-G1-60 (web), S-G1-70, S-G1-80; gate S-G1-90 |
| B03-018 | jelly-leon | S-G1-15 (half werk), S-G1-30 (rij), S-G1-32, S-G1-34, S-G1-36, S-G1-38, S-G1-40, S-G1-70, S-G1-80; gate S-G1-90 |
| B03-019 | jelly-leon, jelly-leon-web, jelly-leon-clients | S-P40-40, S-P40-45, S-P40-70, S-P40-72; per module S-G2-50 |
| B03-020 | jelly-leon | S-P40-60 |
| B03-021 | jelly-leon | S-G2-10; gate S-G2-90 |
| B03-030 | jelly-leon | S-P40-62; definitief bij S-G2-22 (G-F2-2) |
| B03-031 | jelly-leon | S-G2-20 |
| B03-032 | jelly-leon | S-G2-22 |
| B03-033 | jelly-leon | S-G2-24 |
| B03-034 | jelly-leon | S-G2-26 |
| B03-035 | jelly-leon | S-G2-28 |
| B03-060 | jelly-leon | S-P40-64; orakel "audio niet stil" S-G2-35 |
| B03-061 | jelly-leon | S-G2-30; spikes S-G2-34, S-G2-35 in de opmerking |
| B03-062 | jelly-leon | S-G2-32 |
| B03-063 | (golf 4) | spike F5-S2 (a) en de lanes: STAPPEN_P4_GOLF3_4.md (S-G4-01 e.v.) |
| B03-065, B03-068, B03-069 | (golf 4) | in dit deel alleen de spikes F5-S2 (b) tot en met (g): S-G2-34, S-G2-35, S-G2-36, S-G2-38; de werkpakketten zelf in STAPPEN_P4_GOLF3_4.md |
| B03-070 | jelly-leon | S-P40-66 |
| B03-071 | jelly-leon | S-G2-40; clientdeel S-G2-46 |
| B03-072 | jelly-leon | S-G2-42 |
| B03-073 | jelly-leon | S-G2-44 |
| B04-007 | media-guard-ultimate | niet in dit deel: STAPPEN_P3.md (S-P3-620, S-P3-675); de eventkant van Jelly Leon is S-G1-14 |

De overige B03-ID's (B03-022 tot en met B03-029, B03-036 tot en met B03-059, B03-064, B03-066, B03-067, B03-074 tot
en met B03-079) horen bij golf 3, golf 4 of P5 (STAPPEN_P4_GOLF3_4.md, STAPPEN_P5.md) en niet in dit deel.

### 10.2 Deel B - Tests (JLT)

| ID | Repo | Stap of reden |
|---|---|---|
| JLT-10 | jelly-leon | S-G2-22 |
| JLT-11 | jelly-leon | S-G2-22 (kwaliteit), S-G2-26 (functioneel) |
| JLT-12 | jelly-leon | S-G2-28 |
| JLT-13 | jelly-leon | S-G2-26 |
| JLT-14 | jelly-leon | deel `/Similar` in S-G2-20; rest golf 4 (STAPPEN_P4_GOLF3_4.md) |
| JLT-15 | jelly-leon | NAS: STAPPEN_P6.md (N-P6-10); in dit deel alleen de blokkadetekst |
| JLT-16 | jelly-leon | S-G2-24 |
| JLT-17 | jelly-leon | S-G2-24 |
| JLT-43 | jelly-leon | S-G2-32; hermeting met de wrapper in golf 4 (S-G4-03) |
| JLT-50 | jelly-leon | S-G2-42 (Intro, Recap, Preview), S-G2-44 (Outro); meetcommando in `tools/b03-harnas/README.md` via S-P40-66 |
| JLT-51 | jelly-leon | S-G2-44 (serverdeel); clientdeel golf 4 |
| JLT-52 | jelly-leon | S-G2-42 |
| JLT-53 | jelly-leon | S-G2-42 (audiodeel); cues golf 3 (S-G3-22) |
| JLT-56 | jelly-leon | S-G2-40 (a-f, g, i); h golf 4 |
| JLT-60 | jelly-leon, jelly-leon-clients, jelly-leon-web | S-P40-70, S-P40-92; gate S-P40-95 |
| JLT-61 | jelly-leon, jelly-leon-web | S-P40-45 (onderdeel b, voorwaardelijk); gate S-P40-95 (open gate-eis) |
| JLT-62 | jelly-leon | geen bouwstap: alleen als D07 een Jellyfin meet (S-P6-32 in STAPPEN_P6.md); open gate-eis in S-P40-95 |
| JLT-63 | jelly-leon, jelly-leon-web, jelly-leon-clients | S-P40-40, S-P40-70, S-P40-90, S-P40-92, S-G1-60 (controle), S-G2-50 |
| JLT-64 | jelly-leon | S-P40-40, S-G1-10, S-G1-80, S-G2-50 |
| JLT-65 | jelly-leon | S-G1-10, S-G1-18, S-G1-20, S-G1-34, S-G1-80, S-G2-50 |
| JLT-66 | jelly-leon | S-G1-40; groepspauze in S-G2-50; NAS N-P6-10 |
| JLT-67 | jelly-leon | S-P40-45 (voorwaardelijk); open gate-eis in S-P40-95 |
| JLT-68 | jelly-leon | S-G1-10, S-G1-12, S-G1-14, S-G1-80 |
| JLT-69 | jelly-leon-clients | NAS en echte apparaten: STAPPEN_P6.md |
| JLT-70 | jelly-leon (en jelly-leon-clients) | S-P40-32, S-P40-70, S-P40-92, S-P40-82 |
| JLT-71 | jelly-leon | S-P40-30, S-P40-82 |
| JLT-72 | jelly-leon | S-P40-30, S-P40-82 |
| JLT-73 | jelly-leon, media-guard-ultimate | S-P40-20, S-P40-30, S-P40-82 |
| JLT-74 | jelly-leon | NAS: STAPPEN_P6.md (N-P6-11); in dit deel alleen de voorbereiding S-P40-80 |

JLT-01 tot en met JLT-09, JLT-18 tot en met JLT-42, JLT-44 tot en met JLT-49, JLT-54, JLT-55 en JLT-57 tot en met
JLT-59 horen bij golf 3, golf 4, P5 of P6 en niet in dit deel. JLT-40 krijgt in dit deel alleen het vastgelegde
meetcommando (S-P40-64).

### 10.3 Deel C - Installatie I06, I22, I24

| ID | Repo | Stap of reden |
|---|---|---|
| I06-06-01 tot en met I06-06-04, I06-06-08 | jelly-leon-platform | S-G2-70 (controlelijst); uitvoering op de NAS: S-P6-50, N-P6-09 |
| I06-06-05 | jelly-leon, jelly-leon-platform | S-P40-50 (Sim-deel), S-G2-70 |
| I06-06-06 | jelly-leon, jelly-leon-platform | S-G1-50, S-G2-70 |
| I06-06-07 | jelly-leon, jelly-leon-web, jelly-leon-platform | S-P40-40, S-G2-70 |
| I22-22-01 tot en met I22-22-05 | jelly-leon-platform | S-G2-72 alleen na D18 "ja"; anders "Niet gestart" met reden; NAS N-P6-08 |
| I24-24-01, I24-24-02, I24-24-06 | jelly-leon-platform | S-G2-70; NAS S-P6-50, N-P6-09 |
| I24-24-03 | jelly-leon | S-G1-10, S-G1-50, S-G2-55; S-G2-70 |
| I24-24-04 | jelly-leon | S-G1-70, S-G2-55; S-G2-70 |
| I24-24-05 | jelly-leon-clients | S-P40-70 (emulatordeel); S-G2-70 |

### 10.4 Deel D - Contractpunten, review-ID's en delta's

| ID | Moment (CONTRACT_1.3_CONFORMITEIT.md) | Repo | Stap of reden |
|---|---|---|---|
| C1.3-JL-01, C1.3-JL-02, C1.3-JL-03, C1.3-JL-04 | NU | jelly-leon | niet in dit bestand: review S-P2-800 (STAPPEN_P2.md); gate-controle G0-15 |
| C1.3-ALG-01 tot en met C1.3-ALG-04 (deel jelly-leon) | NU | jelly-leon | niet in dit bestand: review S-P2-800 (STAPPEN_P2.md); gate-controle G0-15 |
| C1.3-JL-05 | P4-0 | jelly-leon | S-P40-30, S-P40-80, S-P40-82 |
| C1.3-JL-06 | P4 | jelly-leon | S-G1-12 |
| C1.3-JL-07 | P4 | jelly-leon | S-G1-14 |
| C1.3-JL-08 | P4 (na BG-04; acties na BG-05) | jelly-leon | S-G1-50; acties golf 3 |
| C1.3-JL-09 | P5 | jelly-leon | niet in dit deel; S-G1-70 ververst alleen de meting in de opmerking |
| C1.3-MGU-04 | P4-0 (exitcriterium) | media-guard-ultimate | S-P2-600, S-P2-610 (STAPPEN_P2.md); S-P40-20 |
| C1.3-MGU-03 | NU | media-guard-ultimate | STAPPEN_P2.md; in dit deel alleen genoemd in S-P40-20 |
| REVIEW-jelly-leon-golf-1 | - | jelly-leon | S-G1-17 |
| Δ-MG-AUTH, Δ-MG-DUAL | Gate P4-0 | media-guard-ultimate | S-P2-600, S-P2-610; S-P40-20; gate S-P40-95 (G0-10) |
