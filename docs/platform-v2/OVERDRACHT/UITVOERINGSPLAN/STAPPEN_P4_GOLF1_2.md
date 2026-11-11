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
| media-guard-ultimate | `1dcf318` | Δ-MG-DUAL en Δ-MG-AUTH gebouwd, contracttest `tests/contract/mediaserver/` (commit `2a6dc1c`), documenten en bewijs vastgelegd (commit `1dcf318`) | de contracttest is nog niet tegen de Jelly Leon-image gedraaid; de technische review van Δ-MG-AUTH en Δ-MG-DUAL en het upgradebewijs zijn werk van `<WERKMAP>/.lokaal/plan/uit/STAPPEN_P2.md` (S-P2-600, S-P2-610); daar hoort ook het niet-vastgelegde ontwerpherstel in `apps/web/` en `apps/android/` (niet aankomen vanuit dit bestand: zie V-016) |
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
5. **Eerst opruimen wat ronde 3 heeft laten liggen:** het half werk van B03-018 in jelly-leon (S-G1-15) en de
   ontbrekende review van contract 1.3 in jelly-leon (S-P40-12).

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
  de vormgeving van upstream. (De ontwerpreview van het mediaserver-tabblad van MediaGuard, wel Peil, is S-P2-600 in
  STAPPEN_P2.md.)
- **Het topmodel (N5) staat op drie plaatsen, elk met de reden in de stap zelf (drie van de ruim vijftig stappen):**
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
| S-P40-20 MediaGuard: aanmelden per server en twee mediaservers bewijzen met de Jelly Leon-image | media-guard-ultimate | S-P40-10; BG-01; S-G1-16 voor het deel met de Jelly Leon-image | ja | alle stappen van andere banen |
| S-G1-16 Stand B03-017 vastzetten: werkboom schoon, poort groen, lokale image bewaren | jelly-leon | S-P40-10 | ja | S-P40-20, S-P40-72 |
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
| S-G1-16 (zie 6.1; mag voor Gate P4-0) | jelly-leon | S-P40-10 | ja | zie 6.1 |
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
| S-G2-40 Module Segments: provider en opslag (B03-071) | jelly-leon | S-G2-35; S-P40-66; BG-33, BG-36, BG-32 | ja | banen web en clients |
| S-G2-42 Audio-engine segmenten (B03-072) | jelly-leon | S-G2-40; S-G1-34 | ja | banen web en clients |
| S-G2-44 Beeldanalyse en veiligheid (B03-073) | jelly-leon | S-G2-42; BG-35 (of de terugval) | ja | geen emulator of Gradle tegelijk |
| S-G2-46 Hoofdstuksegmenten en hervatproef op de emulators | jelly-leon-clients | S-G2-40; S-G2-38 | ja | baan jelly-leon (locks) |
| S-G2-50 Terug naar stock en begin aanvulling B03-007 (JLT-63, JLT-64, JLT-65) | jelly-leon | S-G2-44, S-G2-28, S-G2-32 | ja | geen |
| S-G2-55 Manifest en image na golf 2 | jelly-leon | S-G2-50 | ja | geen |
| S-G2-90 Gate golf 2 | geen (A-GATE, alleen lezen) | S-G2-55, S-G2-46, S-G2-36 | nee | geen |

De spike F5-S2 (a), de lanewrapper, staat in `<WERKMAP>/.lokaal/plan/uit/STAPPEN_P4_GOLF3_4.md` als S-G4-01 en wordt
hier niet gebouwd.

## 7. Startbezetting

- **Grenzen:** hooguit 10 subagents tegelijk en hooguit 8 open bouwketens; een schrijver per repo
  (`<WERKMAP>/.lokaal/plan/uit/AGENTEN.md#3. Bezetting`).
- **Eerlijk beeld:** bijna al het werk van dit bestand zit in een repo, jelly-leon. Die baan is de flessenhals: er
  loopt daar steeds een bouwketen. In de praktijk lopen er drie of vier ketens tegelijk, niet acht.
- **Start (na S-P40-10):**
  1. baan media-guard-ultimate: S-P40-20 (keten met R-VEILIG en R-HARDE-EIS);
  2. baan jelly-leon: S-G1-16, daarna de rij uit 6.1;
  3. baan jelly-leon-clients: S-P40-72;
  4. baan jelly-leon-web: S-G1-60 (mag voor Gate P4-0: nieuwe map, raakt de server niet);
  5. een A-VERKEN loopt vooruit op de eerstvolgende stap van de baan jelly-leon (S-P40-40) en schrijft alvast het
     dossier; A-VERKEN wijzigt niets.
  Dat zijn vier ketens en een verkenner: ruim binnen de grenzen. De overige ruimte blijft vrij voor reviewers die
  tegelijk lopen (R-TECH met R-VEILIG of R-HARDE-EIS).
- **Zware stappen:** bijna elke stap in de baan jelly-leon is zwaar. De locks regelen de volgorde; de regisseur
  start geen twee zware stappen bewust tegelijk als een van beide een meting is (S-P40-50, S-G1-40, S-G2-32).
- **Repos zonder werk in dit bestand:** jelly-leon-platform, home-control-hub, appstore-en-fork,
  zoeken-en-persoonlijke-ai, media-source-optimizer en my_house. Die banen zijn vrij voor ander werk van de
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
- **Al gedaan?** `git -C <WERKMAP>/media-guard-ultimate status --short` (verwachting: leeg) en `grep -n "jelly-leon" <WERKMAP>/media-guard-ultimate/tests/contract/mediaserver/RESULTS.md` -> staat daar een run met een jelly-leon-image als Jellyfin-server en staat in EVIDENCE bij `B03-014` niet meer "Contracttest tegen een jelly-leon:12.x-image: niet gedraaid", dan is alleen R-EERLIJK nog nodig. Half werk in `apps/web/` of `apps/android/` hoort bij S-P2-600 (STAPPEN_P2.md): niet aankomen; staat het er bij de start nog, stop en meld het (V-016).
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
- **Poort:** P-jelly-leon (Snel voor `tools/emby-overname`; Volledig stap 8) + P-HARDE-EIS + P-EERLIJK + P-GIT
- **Valkuilen:** V-109 (de tool had per vergissing in Emby kunnen schrijven); V-110 (een leesverzoek laat Emby schrijven: geen PlaybackInfo op niet-geanalyseerde bestanden); V-111 (de proef verandert zelf de kijkgegevens); V-098; V-099; V-127
- **Bewijs:** `JLT-73` -> "Bezig", validatie "Sim-geslaagd" alleen als bouwpunt 2 en 3 beide gedekt zijn, anders "Sim-getest"; `JLT-71`, `JLT-72`, `B03-015`, `C1.3-JL-05` -> "Bezig". Blokkade letterlijk: "NIET GEVALIDEERD (echte NAS): de echte Emby van de gebruiker (D07) is niet gebruikt; echte overname in JLT-74."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH + R-HARDE-EIS (VERPLICHT) (tegelijk) -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard; R-HARDE-EIS N4 (geen N5: de stap wijzigt geen overnamecode, alleen proef en bewijs)
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
- **Vooraf:** S-G1-16 klaar (schone werkboom, lokale image)
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
- **Vooraf:** S-P40-90 klaar; de keuze "voormeting 12.4 telt als definitief of opnieuw meten" is voorgelegd (hoofdstuk 3, keuzes zonder BG-nummer). Zonder antwoord: opnieuw meten (dat is altijd goed).
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
- **Vooraf:** S-P40-50 klaar
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
- **Werkpakketten en tests:** B03-060
- **Vooraf:** S-P40-50 klaar
- **Al gedaan?** `ls <WERKMAP>/jelly-leon/docs/platform-v2/test-evidence | grep -i "b03-060"` en de EVIDENCE-rij `B03-060` -> staat er een rapport per client en per baseline met de bevroren devset en testset (sha256-manifest), dan is de stap klaar.
- **Lees eerst:** WP-JSON rij B03-060; BOUWPLAN `#F5.8 Bouwfasen` (rij F5-S0); `<WERKMAP>/jelly-leon/tools/b03-harnas/b03h/corpus/r_f5_fouten.py`; `<WERKMAP>/jelly-leon/tools/b03-harnas/b03h/web.py`; `<WERKMAP>/jelly-leon/tools/b03-harnas/b03h/baseline.py` (metingen `dp` en `orakel`)
- **Bouw:**
  1. Maak en bevries de gecontroleerde-foutenset: `PYTHONPATH=tools/b03-harnas $PY -m b03h corpus maak f5-fouten --bevries` en het ASS-recept (`corpus maak ass`). Devset en testset apart, met sha256-manifest in het bewijs.
  2. Breid de bestaande metingen `dp` en `orakel` uit tot het rapport K1 tot en met K9 per client en per baseline (a) en (b): Direct Play-ratio, onterechte Direct Plays, onnodige transcodes, inbrandingen, aandeel hardwaretranscodes, CPU per transcode, tijd tot spelend beeld na een mislukte Direct Play (bovengrens 60 s). De werkpakkettekst noemt `tools/jelly-leon/e2e/` als plaats; het raamwerk staat in `tools/b03-harnas`: bouw het daar en leg de afwijking vast in `docs/platform-v2/B03-016_HARNAS.md`.
  3. Afspeelorakel: binnen 10 s `currentTime` >= 2 s, `videoWidth` > 0, geen error-event, audio niet stil. Het stilte-orakel headless is een spike van golf 2 (S-G2-35); tot dan staat "audio niet stil" als "niet gemeten".
  4. De eerste run bevestigt de matrix uit de analyse (Chromium 16/25, Firefox 17/25, WebKit 21/25 Direct Play) of verklaart elk verschil schriftelijk. Bron: WP-JSON rij B03-060, Acceptatie.
  5. Emulatordelen (telefoon, tablet, tv) lopen via de clientmatrix en het clientharnas (S-P40-70); neem hun uitkomst over met verwijzing, niet als eigen meting. Desktop alleen na S-P40-90.
  6. Voeg de rij `B03-060` toe aan EVIDENCE en `EXCEL_TAKEN.json`; leg vast met P-GIT.
- **Tests (verplicht):** T-JL-HARNAS; minstens 3 runs met identieke beslissingen en tijden binnen 10 procent. Negatieve test: een bestand uit de foutenset met een liegende codec moet in het rapport als "onterechte Direct Play" verschijnen; verschijnt het als geslaagd, dan meet het orakel niet.
- **Poort:** P-jelly-leon (Snel voor `tools/b03-harnas`; Volledig stap 9) + P-GIT
- **Valkuilen:** V-077 (harnas keurt goed of af om de verkeerde reden); V-007; V-067; V-009
- **Bewijs:** `B03-060` -> "Bezig", "Sim-getest; Intel-iGPU-getest (ontwikkelmachine)". Blokkade letterlijk: "NIET GEVALIDEERD (hardware): echte tv's, telefoons, A310 en UHD 770; NIET GEVALIDEERD (echte NAS)."
- **Agents:** A-VERKEN -> A-BOUW -> R-TECH -> A-HERSTEL -> R-EERLIJK
- **Niveau:** standaard
- **Stop en vraag als:** de matrix sterk afwijkt van de analyse en geen verklaring te vinden is; WebKit niet start (V-067).

### S-P40-66 - Meetlat segmenten: bevroren testset, harnas en baselines (B03-070)
- **Repo:** jelly-leon | **Fase:** P4-0 (golf 0) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (testset genereren tot 15 GB, servercontainers)
- **Werkpakketten en tests:** B03-070
- **Vooraf:** S-P40-50 klaar; BG-32 (Intro Skipper alleen als testbaseline), BG-34 (labels Pioneer One) en BG-37 genomen. Zonder BG-34: het Pioneer One-deel "Geblokkeerd"; zonder BG-32: baseline (b) niet meten.
- **Al gedaan?** `ls <WERKMAP>/jelly-leon/docs/platform-v2/test-evidence | grep -i "b03-070"` en de EVIDENCE-rij `B03-070` -> staat het manifest-sha256 van de bevroren testset erin met n per type, dan is de stap klaar.
- **Lees eerst:** WP-JSON rij B03-070; BOUWPLAN `#F6.8 Bouwfasen` (rij F6-S0); `<WERKMAP>/jelly-leon/tools/b03-harnas/b03h/corpus/r_f6_segmenten.py`; `<WERKMAP>/jelly-leon/tools/b03-harnas/b03h/statistiek.py`; `<BESLUITEN>` (zoek BG-32 en BG-34)
- **Bouw:**
  1. Controleer vrije schijfruimte (`df -h <WERKMAP>/.lokaal`); de testset mag tot 15 GB groot zijn en wordt na de run verwijderd, manifest en seeds blijven.
  2. Maak en bevries de testset met andere seeds dan de devset: `PYTHONPATH=tools/b03-harnas $PY -m b03h corpus maak f6-segmenten --schaal vol --seed <n> --bevries`. De acht bestaande synthetische afleveringen zijn devset en komen nooit in een gate.
  3. Bouw het evaluatieharnas als onderdeel van `tools/b03-harnas/b03h/` (de werkpakkettekst noemt `tools/jelly-leon/segments-eval`; leg de afwijking vast): per type precisie, recall en F1 bij IoU >= 0,5 met Wilson-interval, grensfout mediaan en p95, onterecht overgeslagen seconden per uur, post-credit-schendingen. Onder de streef-n heet de uitkomst "smoke-gate (n = ...)".
  4. Baseline (a): stock 12.x standaard (verwachting voormeting: 0 segmenten). Baseline (b): stock + Intro Skipper ongewijzigd, alleen na BG-32 en alleen als spike S-IS een versie vindt die op deze basis laadt; anders "Geblokkeerd" met reden en vervalt elke cijferclaim tegen Intro Skipper.
  5. Het lezen van de kandidaatset via `GET /media/v1/segments/{itemId}?view=candidate` kan pas als de module bestaat (S-G2-40): bouw de lezer nu tegen een vast voorbeeldantwoord en markeer dat deel "niet gemeten".
  6. Leg de drempels vast (pre-registratie) en voeg de rij `B03-070` toe aan EVIDENCE en `EXCEL_TAKEN.json`. Ruim de testset op (`corpus opruimen`). Leg vast met P-GIT.
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
S-G1-16, S-G1-10 en S-G1-12 mogen voor Gate P4-0 lopen; de rest begint na Gate P4-0 (S-P40-95).

### S-G1-16 - Stand B03-017 vastzetten: werkboom schoon, poort groen, lokale image bewaren
- **Repo:** jelly-leon | **Fase:** P4 golf 1 (mag voor Gate P4-0) | **Omvang:** middel | **Moeilijkheid:** gewoon | **Zwaar:** ja (grote .NET-build, image-build, containers met een echte Jellyfin-server)
- **Werkpakketten en tests:** B03-017 (de bewijsrij en de lokale image; JLT-64, JLT-65 en JLT-68 worden in S-G1-10 geboekt)
- **Vooraf:** S-P40-10, S-G1-15 en S-P40-12 klaar (de werkboom van jelly-leon is dan schoon)
- **Al gedaan?** `git -C <WERKMAP>/jelly-leon status --short ; git -C <WERKMAP>/jelly-leon log --oneline @{u}.. ; docker image ls --format '{{.Repository}}:{{.Tag}}' | grep '^jelly-leon:lokaal-' ; grep -c '"B03-017"' <WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json` -> werkboom leeg, niets ongepusht, een image `jelly-leon:lokaal-<korte commit>` van de huidige HEAD en een rij `B03-017` in EVIDENCE: dan is de stap klaar. Bij de overdracht: laatste commit `cc3e82b4d` ("B03-009: MediaGuard-viewerclient via de Hub, zonder sleutel in Jelly Leon"), half werk van B03-018 in de werkboom (dat ruimt S-G1-15 op), geen lokale jelly-leon-image, geen rij `B03-017`. Staat er bij de start van deze stap nog niet vastgelegd werk: niet zelf afmaken, maar stoppen en melden (dan is S-G1-15 of S-P40-12 niet af).
- **Lees eerst:** `<WERKMAP>/jelly-leon/docs/adr/ADR-0029-b03-017-prototype-een-dll-eigen-ed25519-host-sqlite.md#Besluit`; `<WERKMAP>/jelly-leon/docs/adr/ADR-0032-b03-017-analyzer-verboden-apis-en-generator-web-config.md#Grenzen (eerlijk)`; `<WERKMAP>/.lokaal/plan/uit/POORTEN.md#P-jelly-leon`; `<WERKMAP>/jelly-leon/deploy/allinone/Dockerfile`; WP-JSON object B03-017
- **Bouw:**
  1. Lees `df -h <WERKMAP>` en `docker system df` (alleen lezen). Onder 20 GB vrij: stop en meld het; ruim niets op (V-011, V-012).
  2. Draai T-JL-PLUGIN, T-JL-TOOLS en T-JL-REGISTER. Herstel alleen wat rood is door half werk; een rode test met een oorzaak buiten B03-017 meld je.
  3. Bouw de image zoals P-jelly-leon "4. Volledig", job image (achter docker-build.lock). Geef hem direct na de bouw een tweede tag: `docker tag jelly-leon:poort jelly-leon:lokaal-<korte commit>` (de korte commit uit `git rev-parse --short HEAD`). De poort ruimt `jelly-leon:poort` zelf op; de tag `jelly-leon:lokaal-...` blijft staan voor S-P40-20, S-P40-30, S-P40-40 en S-G1-10.
  4. Draai de imageproeven van T-JL-IMAGE tegen `jelly-leon:lokaal-<korte commit>`.
  5. Schrijf de tag en de image-ID (`docker image inspect --format '{{.Id}}' <tag>`) in `<WERKMAP>/.lokaal/ketens/S-G1-16/RAPPORT-A-BOUW.md`. Bestaat er een oudere `jelly-leon:lokaal-...`-tag van jezelf, verwijder dan alleen die ene tag met `docker image rm <tag>`.
  6. Voeg in EVIDENCE de rij `B03-017` toe (status "Bezig", validatie "Sim-getest") met wat er staat en wat nog open is: IStartupFilter-spike, export en import met `preview_hash`, haakmodule in de webclient, de modules WatchTogether, Recommendations, Subtitles en Segments. Zet dezelfde rij in `EXCEL_TAKEN.json`.
  7. Leg vast met P-GIT en lees de CI-uitkomst (POORTEN.md "0.5 CI-controle na elke push"); de stappen "Pluginproef op de Jelly Leon-image (JLT-68, JLT-64, JLT-65; Hub-simulator)" en "Pluginproef op JL_RUNTIME_IMAGE (...)" in `.github/workflows/jelly-leon-ci.yml` moeten gedraaid en groen zijn. De CI van de golf-1-vastleggingen van ronde 3 (`8a293727d` tot en met `cc3e82b4d`) is nooit beoordeeld: zoek de run van `cc3e82b4d` op (`gh run list --repo lvos04/jelly-leon --branch ccr-c133d7a0-kuz1cv --limit 10`) en noteer per job de uitkomst in je rapport. Een rode job uit die tijd die op jouw commit groen is, noem je; een rode job die rood blijft is een bevinding.
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
  4. De tabel met handlers is in deze stap leeg. Zet in deze stap geen enkele aanroep van `jlHook` in een upstream-bestand: elke haak komt later, per functie, als een regel van een regel met een eigen `JLW-NNNN`-nummer in `docs/platform-v2/PATCHES.md`. Gevolg dat je in het rapport noemt: zolang geen upstream-bestand de module aanroept, zit zij niet in de bundel en is de gebouwde webclient gelijk aan die van voor deze stap.
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
