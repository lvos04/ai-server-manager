# Besluiten en blokkades

Onderdeel van het uitvoeringsplan voor TrueNAS Home Platform V2 (fasen P2 t/m P6).
Stand van dit bestand: 2026-11-11, gemeten terwijl ronde 3 nog bouwde. Ronde 3 is daarna afgebroken; wat toen half
af was staat in `<WERKMAP>/.lokaal/plan/STAND_RONDE3.md` (dat bestand gaat voor bij elke uitspraak hier over "ronde 3
bouwt ..."). Wat hier "open" heet, kan intussen genomen zijn: controleer eerst de laatste kop in de statusbron (zie
0.3) voordat je iets voorlegt.

Dit bestand heeft vier delen:

1. Genomen besluiten - niet opnieuw vragen; wel naleven.
2. Open besluiten - per besluit het moment en een kant-en-klaar keuzemenu.
3. Taken van de gebruiker - wat alleen de gebruiker kan doen.
4. Blokkades - wat technisch vastzit en waardoor.

Aan het eind: tegenstrijdigheden in de bronnen (deel 5) en wat niet vast te stellen was (deel 6).

---

## 0. Leeswijzer

### 0.1 Voor wie

- **Regisseur:** gebruikt deel 2 om besluiten op het juiste moment voor te leggen, deel 3 om de gebruiker op tijd te
  herinneren en deel 4 om geen keten te starten die toch vastloopt.
- **Subagents (A-VERKEN, A-BOUW, A-HERSTEL, reviewers, A-GATE):** lezen alleen het besluit, de taak of de blokkade waar
  hun stap naar verwijst. Een subagent vraagt de gebruiker nooit iets. Heeft een stap een open besluit nodig, dan stopt
  de subagent en meldt hij het ID uit dit bestand aan de regisseur.

### 0.2 Regels voor het voorleggen (bindend)

1. Alleen de regisseur vraagt de gebruiker, altijd met een keuzemenu, in het Nederlands. Niets gokken.
2. **Tot een besluit geldt de veiligste stand, nooit automatisch het advies.** Bron:
   `<WERKMAP>/ai-server-manager/docs/platform-v2/02_BOUWPLANNEN/B03_BESLUITEN.md`, inleiding ("Een open besluit wordt
   pas gevraagd als de fase of golf begint; tot dan geldt de veiligste stand ("Zonder besluit" in §3), nooit automatisch
   het advies") en `<WERKMAP>/ai-server-manager/docs/platform-v2/PLATFORM_CONTRACTEN.md`, kop "1.2 Open besluiten (tot
   het besluit geldt de veiligste stand)".
3. Een besluit wordt gevraagd op zijn MOMENT (staat bij elk besluit). Vraag niet eerder: de gebruiker wil niet alle
   vragen tegelijk. Besluiten met moment "NU" zijn al te laat of blokkeren lopend werk.
4. Staat bij "Zonder besluit geldt" de tekst "niet uitgeschreven in de bron", dan geldt PRECIES de stand die daar
   achter "afgeleid door dit plan" staat (altijd de minst ingrijpende: het gedrag van standaard Jellyfin, "uit", of
   "de stap stopt en meldt"), en de stap meldt het besluit-ID als blokkade. Het advies (de optie met "(Aanbevolen)")
   is NOOIT de stand zonder besluit, ook niet als een stappenbestand dat in een kolom "Zonder besluit" zo noemt: bij
   verschil gaat dit bestand voor (zie deel 5, punt 5-5). Beter nog: leg de besluiten van een golf voor vóór de golf
   start (de momenten in 2.0), dan speelt dit niet.
5. Een genomen besluit gaat voor het advies (zelfde bron als regel 2). Twee genomen besluiten wijken af van het advies:
   BG-04 en BG-38 (zie deel 1).
6. Geen PR's zonder te vragen; geen force-push; `ai-factory` niet aanraken. Besluiten die daar wel om vragen staan
   in deel 2.14 en worden nooit door een subagent zelf uitgevoerd.

### 0.3 Waar een nieuw besluit wordt vastgelegd

Zo is het bij de vorige besluitronde gedaan (commit `c63b32e` in ai-server-manager, "Besluiten van de gebruiker na
contract 1.3"): een nieuwe kop met datum onderaan in beide bestanden.

- `<WERKMAP>/ai-server-manager/docs/platform-v2/OVERDRACHT/STATUS.md` (laatste kop nu: "Besluiten van de gebruiker na
  contract 1.3 (2026-11-10)").
- `<WERKMAP>/ai-server-manager/docs/platform-v2/02_BOUWPLANNEN/B03_BESLUITEN.md` (zelfde kop onderaan) voor BG-besluiten.
- Raakt het besluit het contract (§1.1 of §1.2), dan past de contracteigenaar (ai-server-manager) het contract aan en
  worden de kopieen in de andere repos opnieuw byte-gelijk gemaakt. Dat is een bouwstap in ai-server-manager, geen
  handeling van de regisseur.
- Excel, blad Besluiten (D01...D18): alleen via `<WERKMAP>/ai-server-manager/tools/excel/update_excel.py`. Nooit
  "Gereed" of "Geslaagd".

Controle of een besluit intussen genomen is (alleen lezen):

```
grep -n -E '^## ' <WERKMAP>/ai-server-manager/docs/platform-v2/OVERDRACHT/STATUS.md | tail -5
grep -n -E '^## Besluiten van de gebruiker' <WERKMAP>/ai-server-manager/docs/platform-v2/02_BOUWPLANNEN/B03_BESLUITEN.md
```

Verwacht op 2026-11-11: de laatste kop is "Besluiten van de gebruiker na contract 1.3 (2026-11-10)". Staat er een
latere kop, lees die dan eerst en schrap wat daar genomen is uit de vragenlijst.

### 0.4 Soorten ID's in dit bestand

| ID | Wat | Bron |
|---|---|---|
| BG-01...BG-38 | besluiten bij bouwplan B03 | `B03_BESLUITEN.md` |
| D01...D18 | gegevens en besluiten over de echte omgeving | `08_EXCEL/decisions.json`, `00_START/BESLUITEN_EN_ONBEKENDEN.md` |
| Contractbesluit 1...9 | vaste besluiten van de gebruiker | `PLATFORM_CONTRACTEN.md`, kop "1.1 Besluiten van de gebruiker (vast)" |
| O-05, O-07, O-09, O-11 | besluiten over de ontwerptaal Peil | `<WERKMAP>/.lokaal/ontwerptaal/BESLUITEN_GEBRUIKER.md` |
| ADR-nnnn | architectuurbesluit; nummers zijn per repo, daarom altijd met reponaam | `<repo>/docs/adr/` |
| K1...K9, RV1...RV13 | keuzes en reviewcorrecties van contract 1.3 | ai-server-manager `docs/adr/ADR-0027-contract-1-3.md` en `ADR-0028-review-contract-1-3.md` |
| C1.3-<REPO>-nn | conformiteitspunt contract 1.3 | `CONTRACT_1.3_CONFORMITEIT.md` |
| APP-01...APP-20, B..-..., I..-..-.., JLT-.., EX.. | werkpakketten en testrijen (Excel) | `<WERKMAP>/.lokaal/plan/uit/ALLE_IDS.txt` |
| **Z-nn, T-nn, BLOK-nn** | **volgnummers van dit bestand** voor open besluiten zonder bron-ID (Z), taken van de gebruiker (T) en blokkades (BLOK) | dit bestand |

Z-, T- en BLOK-nummers zijn geen bron-ID's. Gebruik ze in rapporten aan de regisseur en in VOORTGANG, nooit in Excel,
EVIDENCE of commits. BLOK-nn is iets anders dan de policy-blokkades `BLK-<WOORD>` (bijvoorbeeld `BLK-CHECKPOINT`) in
`<WERKMAP>/ai-server-manager/policy/blokkades.yaml`: dat zijn weigerredenen van de Hub-policy, geen planblokkades.

Twee nummerreeksen komen ook elders voor met een andere betekenis. Schrijf daarom in een opdracht altijd erbij uit
welk bestand het nummer komt:

- **T-nn** is in dit bestand een taak van de gebruiker. In de ontwerptaal Peil is T-nn een eigenschap van een
  component (bijvoorbeeld in `<WERKMAP>/ai-server-manager/docs/platform-v2/ONTWERPTAAL.md`, kop "4.4 Versheid (T-02) en
  meetkwaliteit (T-03)").
- **K1...K9** zijn in dit bestand de keuzes van contract 1.3. In `<WERKMAP>/.lokaal/plan/uit/AGENTEN.md` zijn K1...K7
  de controles van de regisseur (kop "2.1 De goedkope controles K1 tot en met K7").

Afkortingen voor bronnen (pad + kop, geen regelnummers):

| Afkorting | Bestand |
|---|---|
| [STATUS] | `<WERKMAP>/ai-server-manager/docs/platform-v2/OVERDRACHT/STATUS.md` |
| [BG] | `<WERKMAP>/ai-server-manager/docs/platform-v2/02_BOUWPLANNEN/B03_BESLUITEN.md` |
| [CONTRACT] | `<WERKMAP>/ai-server-manager/docs/platform-v2/PLATFORM_CONTRACTEN.md` |
| [CONF] | `<WERKMAP>/ai-server-manager/docs/platform-v2/CONTRACT_1.3_CONFORMITEIT.md` |
| [B03-FASE] | `<WERKMAP>/ai-server-manager/docs/platform-v2/02_BOUWPLANNEN/B03_FASERING.md` |
| [B03-PLAN] | `<WERKMAP>/ai-server-manager/docs/platform-v2/02_BOUWPLANNEN/B03_UNIVERSELE_MEDIASERVER.md` |
| [GATES] | `<WERKMAP>/ai-server-manager/docs/platform-v2/01_ARCHITECTUUR/06_FASERING_EN_GATES.md` |
| [D] | `<WERKMAP>/ai-server-manager/docs/platform-v2/08_EXCEL/decisions.json` en `<WERKMAP>/ai-server-manager/docs/platform-v2/00_START/BESLUITEN_EN_ONBEKENDEN.md` |
| [APPS] | `<WERKMAP>/ai-server-manager/docs/platform-v2/04_BESTAANDE_APPS/APP_REGISTER.md` |
| [PROMPT] | `<WERKMAP>/ai-server-manager/docs/platform-v2/OVERDRACHT/OVERDRACHT_PROMPT.md` |
| [PEIL-B] | `<WERKMAP>/.lokaal/ontwerptaal/BESLUITEN_GEBRUIKER.md` |
| [RUW] | `<WERKMAP>/.lokaal/plan/bron/VERVOLGPUNTEN_RUW.md` (ruwe agentrapporten; alleen gebruikt waar het punt in de repo is nagekeken) |
| [EVIDENCE <repo>] | `<WERKMAP>/<repo>/docs/platform-v2/EVIDENCE.json` |

### 0.5 Sjabloon van een keuzemenu

Elk open besluit in deel 2 heeft dezelfde velden:

- **Moment** - voor welke fase, golf of stap het besluit er moet zijn.
- **Raakt** - werkpakketten, testrijen en repos.
- **Zonder besluit geldt** - de veiligste stand tot het besluit.
- **Vraag** - de tekst die de regisseur letterlijk voorlegt (aanspreekvorm "je").
- **Opties** - genummerd, met gevolg. De aanbevolen optie staat eerst en eindigt op "(Aanbevolen)".
- **Na het besluit** - wat de regisseur daarna doet.
- **Bron** - pad + kop.

Bij BG-besluiten is "(Aanbevolen)" het advies uit [BG] §3. Bij Z-besluiten bestaat geen advies in de bron; daar staat
"(Aanbevolen)" bij de veiligste optie en staat erbij "aanbeveling van dit plan". Heeft een besluit meer deelvragen, dan
legt de regisseur ze in dezelfde ronde voor als vraag a, b, c; de opties staan dan per deelvraag onder "Opties vraag a",
"Opties vraag b" enzovoort, elk met de aanbevolen optie eerst.

---

## 1. Genomen besluiten

Niet opnieuw vragen. Kolom "Gevolg voor de bouw" is wat een stap moet naleven.

### 1.1 Vaste regels van de gebruiker

| Regel | Besluit | Gevolg voor de bouw | Bron |
|---|---|---|---|
| Taal en vragen | Nederlands; vragen via een keuzemenu; niets gokken | subagent stopt bij een open besluit en meldt het ID; alleen de regisseur vraagt | vaste regel in de opdracht van dit uitvoeringsplan; zo toegepast in [STATUS] kop "Besluiten van de gebruiker (gevraagd via keuzemenu op de nieuwe machine, 2026-11-09)" |
| Git | werkbranch `ccr-c133d7a0-kuz1cv` in elke repo; geen PR's; geen force-push; `git pull --rebase` voor elke push; Nederlandse commitberichten; geen modelnaam of model-ID in code, docs of commits; commit eindigt met de attributieregel `Co-Authored-By: Claude <noreply@anthropic.com>` | geen merge naar de standaardbranch en geen PR zonder besluit Z-06; historie nooit herschrijven (zie Z-04) | [CONTRACT] kop "12. Commit- en pushregels"; [PROMPT] kop "2. Vaste keuzes en genomen besluiten (niet opnieuw vragen)" |
| ai-factory | niet aanraken | geen enkele stap leest of schrijft daar | [CONTRACT] kop "12. Commit- en pushregels" |
| Bewijs | nooit "Gereed" of "Geslaagd"; gebouwd en in de simulator getest = "Bezig"; echte NAS, hardware of accounts = "Geblokkeerd" met NIET GEVALIDEERD; na elke fase de Excel bijwerken | zie deel 4, BLOK-01 t/m BLOK-03 | [CONTRACT] kop "11. Bewijs en Excel (EVIDENCE.json)" |
| Installatie | altijd een standaard TrueNAS Custom App met een alles-in-een image per repo; nooit YAML of compose als installatieweg | my_house voldoet nog niet (C1.3-MH-03, P3); zie BLOK-13 | [PROMPT] kop "2. Vaste keuzes en genomen besluiten (niet opnieuw vragen)"; [CONTRACT] kop "2.2 Custom App-realiteit (gemeten in de bronnen, niet op een echte NAS)"; [CONF] punt C1.3-MH-03 |
| Ontwerp | eerst ontwerpstap volgens Peil, na de bouw een ontwerpreview; Jelly Leon web en clients vallen buiten Peil | A-ONTWERP voor en R-ONTWERP na elke UI-bouwstap | [CONTRACT] kop "13. Ontwerptaal" |
| Machine | 14,5 GiB RAM: nooit `docker system prune -a`, `docker builder prune -a` of `docker volume prune` terwijl er iets bouwt; zware builds na elkaar | locks in `<WERKMAP>/.lokaal/` (`docker-build.lock`, `gradle.lock`, `stack.lock`) | opdracht van dit uitvoeringsplan; lockbestanden gezien in `<WERKMAP>/.lokaal/` |

### 1.2 Besluiten uit de keuzemenu's van 2026-11-09 en 2026-11-10

| ID | Besluit | Gevolg voor de bouw | Bron |
|---|---|---|---|
| Contractbesluit 1 | Eigen app-ID's naast de officiele apps: Android `org.jellyfin.mobile.jellyleon`, Android TV `org.jellyfin.androidtv.jellyleon`, iOS/tvOS (Swiftfin) `org.jellyfin.swiftfin.jellyleon`. Bevestigd op 2026-11-10. | Nooit een ID, accounttype, authority, permissie, `app_search_suggest_*`-waarde of sharedpref-naam gelijk aan die van een officiele app; CI bewaakt dit. Na de eerste verspreiding verandert een ID niet meer. Swiftfin blijft NIET GEVALIDEERD (Mac/Xcode). | [CONTRACT] kop "1.1 Besluiten van de gebruiker (vast)" nr. 1; [STATUS] kop "Besluiten van de gebruiker na contract 1.3 (2026-11-10)" |
| Contractbesluit 2 | Swiftfin 1.6.1 blijft; de server gaat voor P4 naar de nieuwste stabiele Jellyfin 12.x (.NET 10) | Eigen fase P4-0; B03 wordt direct op 12.x gebouwd; Android-clients op 12.x controleren | [CONTRACT] kop "1.1 Besluiten van de gebruiker (vast)" nr. 2; jelly-leon `docs/adr/ADR-0011-upgrade-12x-voor-p4.md` |
| Contractbesluit 3 | Repos en GHCR-images publiek, na een scan van de volledige historie. Tien repos publiek; `media-guard-ultimate-archief` prive; nieuwe publieke `media-guard-ultimate` met schone historie. | Installatie zonder registry-login. Zichtbaarheid per GHCR-pakket nog te controleren (T-01, T-02). Tot de koppeling van het MediaGuard-pakket: geen nieuwe MediaGuard-release (BLOK-04). | [CONTRACT] kop "1.1 Besluiten van de gebruiker (vast)" nr. 3 en kop "2.1 Publieke images en registry-login" |
| Contractbesluit 4 | `JL_SYNC_PUSH_TOKEN`: de gebruiker wil dat de bouwer het regelt, maar de route staat open | Geen tokens in repos; sync-push blijft uit. Zie Z-01 en T-03. | [CONTRACT] kop "1.1 Besluiten van de gebruiker (vast)" nr. 4; [STATUS] kop "Besluiten van de gebruiker (gevraagd via keuzemenu op de nieuwe machine, 2026-11-09)" punt 4 |
| Contractbesluit 5 | my_house 0.2.0 mocht opnieuw worden uitgebracht; is gepubliceerd | geen | [CONTRACT] kop "1.1 Besluiten van de gebruiker (vast)" nr. 5 |
| Contractbesluit 6 | Release-tags `v0.1.0` voor de nieuwe repos (images naar GHCR met digests) zodra hun CI groen is | Toegestaan, maar niet in een contractronde zelf taggen. Het moment staat open: Z-07. Tot de tag blijft `digest_pending_release` in de manifesten (BLOK-06). | [CONTRACT] kop "1.1 Besluiten van de gebruiker (vast)" nr. 6 en kop "12. Commit- en pushregels" |
| Contractbesluit 7 | Een eigen ontwerptaal op Tailwind 4 + shadcn/ui + lucide (Peil), door een aparte ontwerp-agent; die beslist zelfstandig en toont het resultaat achteraf | Reikwijdte: Hub-UI, statuspagina's, uiterlijk van MediaGuard, MSO en my_house. Jelly Leon web en clients niet. | [CONTRACT] kop "1.1 Besluiten van de gebruiker (vast)" nr. 7; ai-server-manager `docs/adr/ADR-0015-ontwerptaal-peil.md` |
| Contractbesluit 8 | Licentie eigen repos GPL-3.0; forks houden hun upstream-licentie (jelly-leon en jelly-leon-web GPL-2.0, jelly-leon-clients per subtree) | `LICENSE` met volledige tekst; ook de nieuwe MediaGuard-repo. Fork-eigen bestanden in jelly-leon-clients: zie Z-11. | [CONTRACT] kop "1.1 Besluiten van de gebruiker (vast)" nr. 8 |
| Contractbesluit 9 | Emby is de huidige mediaserver en blijft de terugval tot de gebruiker hem zelf verwijdert; HARDE EIS; MediaGuard volgt Emby en Jelly Leon tegelijk | zie de rijen HARDE EIS en Emby hieronder | [CONTRACT] kop "1.1 Besluiten van de gebruiker (vast)" nr. 9 |
| D10 | De bestaande mini-pc is voor de videoapp en andere projecten; geen Home Hub-diensten | Niets van het platform wordt op de mini-pc gepland. Excel: Ingevuld. | [CONTRACT] kop "1.1 Besluiten van de gebruiker (vast)" rij D10; [D] rij D10 |
| HARDE EIS | Alle kijkgeschiedenis (gezien-status, hervatpunten, favorieten, beoordelingen, onthouden spoorkeuzes, gebruikers, rechten) en de MediaGuard-voortgang blijven altijd beschikbaar | Geen cutover zonder voor/na-rapport per gebruiker en uitdrukkelijk akkoord op elk verschil (ook verschillen door upstream-migraties); de bestaande installatie blijft ongewijzigd als terugval; elke MediaGuard-release bewijst een upgrade op een gevulde database van de vorige versie zonder gegevensverlies; UI-rondes wijzigen geen datamodel. Reikwijdte na de review: elke upgrade die de database van een mediaserver migreert (RV2; bevestiging open, Z-03). | [BG] kop "1. Genomen besluiten (2026-11-09, via keuzemenu)"; ai-server-manager `docs/adr/ADR-0020-kijkgeschiedenis-altijd-beschikbaar-en-emby-overname.md`; [B03-PLAN] kop "10.9 Opslag en gegevensbescherming (ADR-B03-08)" |
| Emby blijft | Emby blijft ongewijzigd draaien, ook als terugval. Overname per gebruiker naar Jelly Leon: alleen lezen uit Emby, herhaalbare proefrun, voor/na-rapport, akkoord op elk verschil, laatste delta bij de overstap. Wachtwoorden zijn niet over te zetten. | De Hub, de executor, de AI, Jelly Leon en de overnametool lezen alleen uit Emby (alleen `GET`); de bestaande MediaGuard-koppeling met Emby blijft; er komt geen nieuwe schrijfroute naar Emby (RV1). B03-015 en JLT-70...JLT-74 hebben prioriteit P0. Doel 100 % van gezien-status en hervatpunten; wat niet te koppelen is komt op een afhandellijst, nooit stil weglaten. | [BG] kop "Emby (gebruiker, 2026-11-09)"; [B03-PLAN] kop "10.9.1 Overname vanuit Emby (B03-015 deel A; prioriteit P0, al in golf 0)"; RV1 in ai-server-manager `docs/adr/ADR-0028-review-contract-1-3.md` |
| MediaGuard volgt beide | MediaGuard volgt Emby en Jelly Leon tegelijk; de bestaande Emby-koppeling mag op geen enkel moment onderbreken | Aanmelden per server (Emby `X-Emby-Token`, Jelly Leon 12.x `Authorization: MediaBrowser Token=...`) en meerdere mediaservers tegelijk (in de bron: delta MG-AUTH en delta MG-DUAL) | [BG] kop "Emby (gebruiker, 2026-11-09)"; media-guard-ultimate `docs/adr/ADR-0022-meerdere-mediaservers-en-aanmelden-per-server.md` |
| Emby verwijderen | Doet de gebruiker zelf, pas na de vaste controlelijst; app stoppen en data verwijderen zijn aparte stappen | Geen agent stopt of verwijdert Emby. Zie T-10. | [B03-PLAN] kop "10.9.2 Controlelijst "Emby verwijderen" (de gebruiker voert uit)" |
| Eigen overnametool | Geen hergebruik van JellyPlex-Watched; eigen overnametool (besluit van de bouwer, geen gebruikersbesluit) | B03-015 bouwt op de eigen tool | jelly-leon `docs/adr/ADR-0025-b03-015-eigen-overnametool-niet-jellyplex-watched.md` |
| BG-01 | MediaGuard naar `Authorization: MediaBrowser Token=...`; `EnableLegacyAuthorization` blijft uit; derden-apps eerst testen | Zonder deze koppeling geen B03-batch op de NAS en status `mediaguard: onbekend`. Faalt een derden-app die de gebruiker echt gebruikt (D15), dan het besluit opnieuw voorleggen. | [BG] kop "BG-01 — MediaGuard-koppeling na de upgrade naar Jellyfin 12.x" |
| BG-02 | Geen release meer op 10.11.11; eerste Jelly Leon-release op 12.x; P4-0 als eigen fase | Overnemen in de standaardbranch en een release zijn handmatige stappen van de gebruiker (zie Z-06, T-13) | [BG] kop "BG-02 — Release vóór de upgrade en P4-0 in de Excel"; jelly-leon `docs/adr/ADR-0027-p4-0-uitvoering-12x.md` |
| BG-04 | De MediaGuard-sleutel van Jelly Leon loopt **via de Hub** (wijkt af van het advies "in Jelly Leon zelf"). De Hub beheert de alleen-lezen, gescopete sleutel in de eigen vault; bij voorkeur zonder sleuteloverdracht (Jelly Leon vraagt de MediaGuard-gegevens via de Hub met een dienst-JWT). | Vraagt de Hub-koppeling van de Jelly Leon-plugin (JL4, golf 1). Tot dan `mediaguard: onbekend`. Geen sleutelveld in de beheerpagina van Jelly Leon bouwen. | [BG] kop "Besluiten van de gebruiker na contract 1.3 (2026-11-10)" |
| BG-32 | Intro Skipper alleen als ongewijzigde vergelijkingsbasis in een testcontainer; externe segmentdatabases uit; bestaande segmenten uit de huidige installatie eenmalig als hint, met voorbeeld vooraf | Geen Intro Skipper op de NAS; geen aanroepen naar AniSkip, TheIntroDB of SkipMe.db | [BG] kop "BG-32 — Intro Skipper, externe segmentdatabases en bestaande segmenten" |
| BG-34 | De gebruiker (of een aangewezen persoon) labelt de echte afleveringen; de bouwer levert een eenvoudig labelscherm | Zie T-08. Zonder labels telt alleen de synthetische testset. | [BG] kop "BG-34 — Wie labelt de echte afleveringen?" |
| BG-37 | MovieLens alleen lokaal: ja. Pioneer One alleen lokaal: ja. Eenmalige evaluatie op de echte kijkhistorie (na B03-039; samengevat rapport, afmelden kan, kinderen nooit): ja. TMDb in een wegwerpcontainer met alleen publieke MovieLens-ID's: ja. Netflix-4K/DV-masters: niet zolang de schijf vol is. | Testdata met beperkende licentie nooit in een repo of image | [BG] kop "BG-37 — Testdata met een beperkende licentie" |
| BG-38 | Tijdelijke meetdata opgeruimd; testsets on demand maken en daarna weggooien (alleen recept of manifest blijft); Android-systeemimages blijven; de ontwikkelgebruiker is toegevoegd aan de groepen render en kvm (wijkt af van het advies "geen extra groepsrechten") | Testsets niet permanent bewaren | [BG] kop "BG-38 — Ontwikkelmachine: opruimen en rechten" |
| Noodlogin (A07) | Alleen vanaf het thuisnetwerk (RFC 1918 / fc00::/7). Het bereik `100.64.0.0/10` (Tailscale/CGNAT) telt niet als prive; een beheerder kan het later in de Hub-UI uitdrukkelijk toestaan (audit + waarschuwing). | De Hub weigert de noodlogin vanaf dat bereik tot de beheerder het aanzet | [STATUS] kop "Besluiten van de gebruiker na contract 1.3 (2026-11-10)" |
| Extra's (C09) | De Android-app van MediaGuard krijgt ook en-US; my_house krijgt een tabelweergave met toetsenbordbediening bij de grafiek "Laatste 24 uur" | Beide zijn in ronde 3 gebouwd en gepusht (media-guard-ultimate commit `c5e3016`; my_house HEAD `dcbe73d`), maar de reviews zijn niet afgerond: zie `<WERKMAP>/.lokaal/plan/STAND_RONDE3.md` (my_house: technische review afgebroken; media-guard-ultimate: technische review niet gedaan, ontwerpherstel half werk). Geen nieuwe bouwstap; wel de reviewstappen | [STATUS] kop "Besluiten van de gebruiker na contract 1.3 (2026-11-10)"; my_house `docs/adr/ADR-0013-grafiek-24-uur-tabel-en-toetsenbord.md` |
| B03 2.0 | Het plan B03 2.0 met zes functies (Watch Together, aanbevelingen, NL-ondertitelvertaling, mediakwaliteitscontrole, apparaatprofielen, intro/outro/recap) is goedgekeurd | 72 werkpakketten: 66 nieuw (B03-014...B03-079) en 6 uitgebreid (B03-004, B03-005, B03-007, B03-009, B03-010, B03-013); 74 testrijen JLT-01...JLT-74; fasering P4-0 en golven 0-4 | [STATUS] kop "B03 2.0 verwerkt (2026-11-09, avond)" |
| Openbare sleutel | De openbare sideload-signingsleutel van MediaGuard blijft; risico geaccepteerd | Niet vervangen, niet als geheim behandelen | [STATUS] kop "Vervolgbesluiten van de gebruiker (2026-11-09, middag)" |

### 1.3 Besluiten over de ontwerptaal Peil

| ID | Besluit | Gevolg voor de bouw | Bron |
|---|---|---|---|
| O-07 | Productnaam "TrueNAS Home Platform" linksboven in de Hub-UI | vervangt de plaatshouder | [PEIL-B] |
| O-05 | Rol kind ziet Home, Kijken, Zoeken, Ik (geen server, apps, huis of instellingen) | navigatie per rol | [PEIL-B] |
| O-11 | Link "Terug naar de Hub" in MediaGuard, MSO en my_house; adres uit de configuratie; verborgen als onbekend | raakt Z-08 (my_house `/_shc/config.json`) | [PEIL-B] |
| O-09 | Themaknop Systeem/Licht/Donker in my_house | geen datamodelwijziging | [PEIL-B] |
| (geen ID) | Tabelweergave met toetsenbordbediening bij de grafieken van MediaGuard en MSO; ook de native Android-apps van MediaGuard en my_house in Peil-stijl | functionele toevoeging toegestaan | [PEIL-B] |
| (geen ID) | my_house fase 2: Tailwind 4 + shadcn/ui in de React 18-variant, geen React 19-upgrade | my_house `docs/adr/ADR-0009-peil-fase-2-tailwind-shadcn-react18.md` | [PEIL-B] |

### 1.4 Keuzes van de bouwer die de gebruiker nog kan terugdraaien

Deze staan vast in het contract. De ADR's zelf vragen geen bevestiging; de agentrapporten van de contractronde
([RUW]) melden dat de gebruiker K1 nog moet bevestigen en RV2 kan versoepelen. Tot dan gelden ze zoals gebouwd.

| ID | Keuze | Open deel | Bron |
|---|---|---|---|
| K1 | Host-beperking tegen DNS-rebinding: koppel- en sleutelformulieren van statuspagina's accepteren een POST alleen als de Host een IP-adres is, een naam zonder punt, of een naam onder `.local`, `.lan`, `.internal`, `.home.arpa` | bevestiging: Z-02 | ai-server-manager `docs/adr/ADR-0027-contract-1-3.md` |
| RV2 | De HARDE EIS geldt voor elke upgrade die de database van een mediaserver migreert, dus ook latere Jelly Leon-updates met upstream-migraties | bevestigen of versoepelen: Z-03 | ai-server-manager `docs/adr/ADR-0028-review-contract-1-3.md` |

---

## 2. Open besluiten

Stand 2026-11-11: 31 BG-besluiten open (BG-03, BG-05...BG-31, BG-33, BG-35, BG-36), 17 D-gegevens open (D01...D09,
D11...D18) en 15 besluiten zonder bron-ID (Z-01...Z-15). De menu's staan in de volgorde waarin ze nodig zijn.

### 2.0 Overzicht: wanneer wat

De kolom "Stap in het plan" is overgenomen uit de stapbestanden in `<WERKMAP>/.lokaal/plan/uit/` zoals ze er op
2026-11-11 stonden; die bestanden waren nog in bewerking, dus een stap-ID kan verschoven zijn. Controleer met:
`grep -n -E 'BG-[0-9]+|Z-[0-9]+' <WERKMAP>/.lokaal/plan/uit/STAPPEN_*.md`. `STAPPEN_P3.md` en `STAPPEN_P4_GOLF1_2.md`
waren op dat moment nog in opbouw: de stap-ID's in de eerste vier rijen komen uit de besluitentabel van die bestanden
(kop "3. Besluiten die eerst genomen moeten zijn" en stap S-P3-000), de stappen zelf waren nog niet allemaal
uitgeschreven. Waar geen stap gevonden is staat "ONBEKEND".

| Moment | Besluiten | Stap in het plan (gezien 2026-11-11) |
|---|---|---|
| NU (te laat of blokkeert lopend werk) | BG-03, BG-22; Z-04, Z-05, Z-06 (alleen melden, zie daar) | BG-03: S-G1-18 (later S-G2-26); BG-22: S-P40-80. Z-04...Z-06: geen stap gevonden, ONBEKEND - eerst vaststellen met: `grep -n -E 'Z-0[456]' <WERKMAP>/.lokaal/plan/uit/STAPPEN_*.md` |
| Voor P3 (contractronde en statuspagina's) | Z-02, Z-03, Z-08, Z-10 | S-P3-000 loopt ze na; Z-03: S-P3-015; Z-08: S-P3-720; Z-10: S-P3-200; Z-02: de stappen voor de statuspagina's (stap-ID ONBEKEND - eerst vaststellen met: `grep -n 'Z-02' <WERKMAP>/.lokaal/plan/uit/STAPPEN_P3.md`) |
| Na golf 1 (na de belastingtest B03-018, JLT-66) | BG-07 | na S-G1-40, voor S-G1-90 |
| Start golf 2 | BG-16, BG-27, BG-33, BG-35, BG-36 | BG-16: S-G2-26; BG-27: S-G2-32; BG-33 en BG-36: S-G2-40; BG-35: S-G2-44. BG-33 komt ook terug in S-G4-15 |
| Voor golf 3 | BG-05 | S-G3-07, S-G3-15 |
| Start golf 3 | BG-10, BG-11, BG-13, BG-14, BG-19, BG-21, BG-23, BG-24, BG-25 | S-G3-08, S-G3-11...S-G3-14, S-G3-16, S-G3-17, S-G3-19, S-G3-20, S-G3-24...S-G3-26 |
| Voor B03-027 (golf 3) | BG-09 | S-G3-23; komt terug in S-P5-01 |
| Voor golf 4 | BG-08 | S-G4-27, S-G4-28 |
| Start golf 4 | BG-12, BG-15, BG-26, BG-28, BG-29, BG-30, BG-31 | S-G4-03, S-G4-04, S-G4-06...S-G4-10, S-G4-16, S-G4-20, S-G4-22...S-G4-24, S-G4-26...S-G4-29 |
| Bij B03-006 | BG-17 | ONBEKEND - eerst vaststellen met: `grep -n 'B03-006' <WERKMAP>/.lokaal/plan/uit/STAPPEN_*.md` |
| Voor P5 | BG-06, BG-18; Z-01; D03, D08, D11 | S-P5-01 (besluitenronde), S-P5-02 |
| In P5 | BG-20 | S-P5-01 |
| Voor P6 | Z-07, Z-09, Z-11; D01...D07, D15...D17 | S-P6-01; releases in S-P6-02...S-P6-06 |
| In P6, voor de echte overname | Z-13 (met T-21) | N-P6-11 "De echte overname vanuit Emby" in `STAPPEN_P6.md` (voorwaarde 6 van dat onderdeel) |
| Na de Cutover-gate | Z-12, Z-14 | geen AI-stap: de gebruiker voert uit |
| Voor de eerste AI-functie met een echte (cloud)aanbieder | D09 | niet vragen in P2 (`STAPPEN_P2.md`, tabel met D09); AI blijft standaard uit en B02-001 houdt "NIET GEVALIDEERD (account)"; voorleggen bij de NAS-uitvoering (N-P6-08) |
| Bij de echte apparaten van my_house | D12, D13, D14 | geen bouwstap: de stappen in `STAPPEN_P3.md` bouwen in de simulator en zetten "NIET GEVALIDEERD (hardware)" met het D-nummer; voorleggen bij onderdeel N-P6-06 in `STAPPEN_P6.md` |
| Wanneer het uitkomt | Z-15; D18 | geen |

De momenten van de BG-besluiten komen uit [BG] kop "2. Open besluiten — wanneer ze gevraagd worden".

### 2.1 NU

#### BG-03 — Wat is een kinderprofiel?

- **Moment:** hoorde voor golf 1; golf 1 wordt al gebouwd. Nu voorleggen.
- **Raakt:** B03-010, B03-017, B03-023, B03-034, B03-075; repo jelly-leon.
- **Zonder besluit geldt:** de ruimste regel (a) (staat zo in de bron). Zo is het ook gebouwd: zie
  `<WERKMAP>/jelly-leon/plugins/JellyLeon/src/Jellyfin.Plugin.JellyLeon/Core/Privacy/KidPolicy.cs` (commit `8a293727d`).
- **Vraag:** "Alle zes functies hebben kinderregels (geen gemengde groepen met externen, geen verborgen titels in
  uitleg, geen correcties door kinderen). Wanneer is een gebruiker een kind?"
- **Opties:**
  1. Beide: Jelly Leon stelt automatisch voor, de beheerder bevestigt. (Aanbevolen) Gevolg: er komt een bevestigstap
     voor de beheerder. Wat geldt tussen voorstel en bevestiging is niet uitgewerkt in de bron; voorstel van dit plan:
     tot de bevestiging telt het account als kind.
  2. Iedere gebruiker met een leeftijdsgrens (`MaxParentalRating`), geblokkeerde tags of een toegangsschema.
     Gevolg: geen extra werk (huidige stand); volgens de bron kan dit volwassenen met een filter onterecht als kind
     behandelen.
  3. Alleen wie de beheerder als "kind" markeert. Gevolg volgens de bron: je vergeet makkelijk iemand.
- **Na het besluit:** vastleggen (0.3). Bij optie 1 of 3: herstelstap door A-HERSTEL op `KidPolicy.cs` en de tests in
  `<WERKMAP>/jelly-leon/plugins/JellyLeon/tests/`, daarna R-HARDE-EIS en R-VEILIG. Bij optie 2: alleen de opmerking
  "zolang BG-03 open staat" in de code bijwerken.
- **Bron:** [BG] kop "BG-03 — Wat is een kinderprofiel?".

#### BG-22 — Bazarr-vertaler en de ondertiteldownloaders van Jellyfin

- **Moment:** P4-0 (overname); P4-0 loopt al. Nu voorleggen, in elk geval voor B03-043.
- **Raakt:** B03-015, B03-043; repos jelly-leon en media-guard-ultimate (alleen documentatie en beslisregels).
- **Zonder besluit geldt:** niet uitgeschreven in de bron; afgeleid door dit plan (minst ingrijpende optie): de
  Bazarr-vertaler wordt niet voor Nederlands ingezet en er worden geen ondertiteldownloaders van Jellyfin geinstalleerd.
- **Vraag:** "a. Mag de vertaler van Bazarr Nederlandse ondertitels maken? Die gebruikt standaard Google Translate in
  de cloud en schrijft gewone `.nl.srt`-bestanden in de bibliotheek. b. Mogen de ondertiteldownloaders van Jellyfin
  geinstalleerd worden, naast MediaGuard en Bazarr?"
- **Opties vraag a:**
  1. Niet gebruiken. (Aanbevolen) Gevolg: geen cloudvertaling en geen extra `.nl.srt`-bestanden in de bibliotheek.
  2. Wel gebruiken. Gevolg: de vertaling loopt standaard via Google Translate in de cloud en komt als gewone `.nl.srt`
     in de bibliotheek.
- **Opties vraag b:**
  1. Niet installeren. (Aanbevolen) Gevolg: MediaGuard en Bazarr blijven de enige downloaders.
  2. Wel installeren. Gevolg: MediaGuard en Bazarr zijn dan niet meer de enige downloaders.
- **Na het besluit:** vastleggen (0.3). De synchronisatie in Bazarr blijft een eigen keuze van de gebruiker en hoort
  niet bij dit besluit.
- **Bron:** [BG] kop "BG-22 — Bazarr-vertaler en de ondertiteldownloaders van Jellyfin".

### 2.2 Na golf 1

#### BG-07 — Resources van de jelly-leon-app

- **Moment:** na golf 1, zodra de belastingtest (B03-018, JLT-66) een uitkomst heeft. Niet eerder: de bron vraagt
  eerst een meting.
- **Raakt:** B03-014, B03-018; JLT-66; repos jelly-leon en jelly-leon-platform (manifest).
- **Zonder besluit geldt:** optie "strikt na elkaar binnen 4 CPU's en 4 GiB", met de batchmodules op de NAS standaard
  uit (staat zo in de bron). Zie BLOK-18.
- **Vraag:** "De belastingtest gaf: <uitkomst JLT-66 invullen>. Het RAM van de NAS is: <meetwaarde invullen, of
  'nog niet gemeten'>. Hoe gaan we om met de resources van de jelly-leon-app?"
- **Opties:**
  1. Strikt na elkaar binnen 4 CPU's en 4 GiB. (Aanbevolen zolang het RAM van de NAS niet gemeten is) Gevolg: de
     batchmodules blijven op de NAS standaard uit tot de meting er is.
  2. Resources ophogen als de batchmodules aan staan. Gevolg: de app krijgt meer dan 4 CPU's en 4 GiB; pas
     verantwoord met een gemeten RAM-waarde (de bron schat het gebruik op 4,4 tot 5,5 GB, niet gemeten).
  3. Batchwerk alleen 's nachts. Gevolg: overdag geen batchwerk.
- **Na het besluit:** vastleggen (0.3). Bij optie 2 eerst A-VERKEN een onderbouwd voorstel laten maken op basis van
  de meting; de bron geeft na de meting geen vast advies maar "een onderbouwd voorstel".
- **Bron:** [BG] kop "BG-07 — Resources van de jelly-leon-app" en kop "9. Gegevens die nodig zijn (geen keuze)".

### 2.3 Start golf 2

#### BG-16 — Kijkgedrag van gezinsleden en een fijnere kijklog

- **Moment:** start golf 2, voor B03-034.
- **Raakt:** B03-034, B03-032; JLT-13; repo jelly-leon.
- **Zonder besluit geldt:** niet uitgeschreven in de bron; afgeleid door dit plan: kijkgedrag van gezinsleden telt
  nooit mee en de fijnere kijklog staat uit.
- **Vraag:** "a. Mag het kijkgedrag van andere gezinsleden meetellen in jouw aanbevelingen? b. Mag Jelly Leon een
  fijnere kijklog bijhouden (lokaal, 365 dagen)?"
- **Opties vraag a:**
  1. Opt-in per profiel, in beide richtingen, standaard uit; telt pas mee als minstens 3 andere volwassenen een
     titel keken. (Aanbevolen) Gevolg volgens de bron: in een klein huishouden werkt dit waarschijnlijk nooit.
     Kinderen tellen nooit mee.
  2. Nooit.
- **Opties vraag b:**
  1. Uit, tot gemeten is of de log iets oplevert. (Aanbevolen)
  2. Aan (365 dagen, lokaal).
- **Na het besluit:** vastleggen (0.3).
- **Bron:** [BG] kop "BG-16 — Kijkgedrag van gezinsleden en een fijnere kijklog".

#### BG-27 — De A310 voor live kijken terwijl MediaGuard AV1 encodeert; meten

- **Moment:** start golf 2, voor B03-062 en B03-064.
- **Raakt:** B03-062, B03-064; JLT-43, JLT-45; repo jelly-leon. Hangt samen met D08.
- **Zonder besluit geldt:** niet uitgeschreven in de bron; afgeleid door dit plan: de A310 wordt niet voor live kijken
  gebruikt en er wordt geen meting gedaan die MediaGuard raakt.
- **Vraag:** "a. Mag Jelly Leon de A310 gebruiken voor live kijken terwijl MediaGuard erop encodeert? b. Hoe meten we
  wat de A310 dan nog aankan?"
- **Opties vraag a:**
  1. Ja, binnen een deel van de capaciteit (voorlopig de helft, niet gemeten), met hooguit 1 Jelly Leon-stream op de
     A310 tot de meting op de NAS. (Aanbevolen)
  2. Alleen als overloop wanneer de UHD 770 vol is.
  3. Nooit.
- **Opties vraag b:**
  1. De assistent vraagt je MediaGuard zelf te pauzeren (via een link); Jelly Leon bedient MediaGuard nooit.
     (Aanbevolen) Gevolg: taak T-17.
  2. Meten terwijl MediaGuard draait, met het label "met MediaGuard-last".
- **Na het besluit:** vastleggen (0.3).
- **Bron:** [BG] kop "BG-27 — De A310 voor live kijken terwijl MediaGuard AV1 encodeert; meten".

#### BG-33 — Wie mag tijdcodes corrigeren, en eerst schaduwmodus?

- **Moment:** start golf 2, voor B03-071.
- **Raakt:** B03-071, B03-075; JLT-54; repos jelly-leon en jelly-leon-web.
- **Zonder besluit geldt:** niet uitgeschreven in de bron; afgeleid door dit plan: alleen beheerders corrigeren en
  nieuwe segmenten blijven in schaduwmodus (niet zichtbaar voor kijkers).
- **Vraag:** "a. Wie mag de tijdcodes van intro, samenvatting en aftiteling corrigeren? b. Worden nieuwe tijdcodes
  direct gebruikt of eerst in schaduwmodus?"
- **Opties vraag a:**
  1. Beheerders en door de beheerder aangewezen volwassenen; iedere volwassene mag "klopt niet" melden. (Aanbevolen)
  2. Elke volwassene. Kinderen in beide gevallen nooit.
- **Opties vraag b:**
  1. Nieuwe segmenten eerst onzichtbaar (schaduwmodus) tot jij per serie 3 afleveringen hebt bevestigd. (Aanbevolen)
  2. Direct publiceren.
- **Na het besluit:** vastleggen (0.3).
- **Bron:** [BG] kop "BG-33 — Wie mag tijdcodes corrigeren, en eerst schaduwmodus?".

#### BG-35 — Hardware-decode voor de beeldanalyse

- **Moment:** start golf 2, voor B03-073.
- **Raakt:** B03-073, B03-018; repo jelly-leon. Optie 1 vraagt een bevestigd D08.
- **Zonder besluit geldt:** niet uitgeschreven in de bron; afgeleid door dit plan: alleen CPU.
- **Vraag:** "Mag de beeldanalyse (aftiteling, grensverfijning) hardware-decode gebruiken?"
- **Opties:**
  1. Alleen de UHD 770, en pas nadat D08 bevestigd is. (Aanbevolen) Gevolg: tot D08 er is draait de analyse op de CPU.
     Meting op de ontwikkelmachine: 7,0 s met VA-API tegen 132 s zonder (Sintel 1080p); op de NAS NIET GEVALIDEERD.
  2. Alleen CPU. Gevolg: de analyse duurt veel langer. De A310 blijft in beide gevallen voor MediaGuard en live kijken.
- **Na het besluit:** vastleggen (0.3).
- **Bron:** [BG] kop "BG-35 — Hardware-decode voor de beeldanalyse".

#### BG-36 — Module uit of "schaduw": eigen segmenten wissen of verbergen?

- **Moment:** start golf 2, voor B03-071.
- **Raakt:** B03-071, B03-013; JLT-56; repo jelly-leon.
- **Zonder besluit geldt:** niet uitgeschreven in de bron; afgeleid door dit plan: het gedrag bij "module uit" wordt
  niet gebouwd tot het besluit er is; de stap meldt BG-36.
- **Vraag:** "Als je de segmentmodule uitzet of in schaduwmodus zet: wat gebeurt er met de segmenten die Jelly Leon
  zelf heeft aangemaakt?"
- **Opties:**
  1. De eigen gepubliceerde segmenten uit Jellyfin wissen; ze zijn altijd herstelbaar uit de eigen database van
     Jelly Leon. (Aanbevolen)
  2. Alleen verbergen via de bibliotheekinstelling. Gevolg: Jelly Leon schrijft dan in de bibliotheekinstellingen van
     Jellyfin.
- **Na het besluit:** vastleggen (0.3).
- **Bron:** [BG] kop "BG-36 — Module uit of "schaduw": eigen segmenten wissen of verbergen?".

### 2.4 Voor golf 3

#### BG-05 — Mag de Hub MediaGuard laten herstellen of zoeken (na jouw goedkeuring)?

- **Moment:** voor golf 3; anders bouwt golf 3 alleen links naar MediaGuard. In het plan: S-G3-07, S-G3-15.
- **Raakt:** B03-009, B03-043, B03-056, B03-058; C1.3-ASM-19, C1.3-MGU-05, C1.3-JL-08; repos ai-server-manager,
  media-guard-ultimate, jelly-leon.
- **Zonder besluit geldt:** optie "niet" (staat zo in de bron: "Tot dan geldt (b)"). De MediaGuard-acties blijven
  gereserveerd ([CONTRACT] kop "1.2 Open besluiten (tot het besluit geldt de veiligste stand)"). Zie BLOK-08.
- **Vraag:** "Jelly Leon mag nooit zelf bestanden wijzigen. Herstel (opnieuw zoeken, vrijgavecontrole, een beschadigd
  bestand opnieuw binnenhalen) en 'eerst menselijke ondertitels zoeken' zijn van MediaGuard. Het contract staat de Hub
  bij MediaGuard nu alleen 'noodstop aan' toe. Mag de Hub die acties laten uitvoeren, met jouw goedkeuring per actie?"
- **Opties:**
  1. Ja, via een contractwijziging: de Hub mag deze acties laten uitvoeren met jouw goedkeuring per actie; terugzetten
     uit quarantaine blijft altijd handmatig in MediaGuard. (Aanbevolen) Gevolg: contractronde in ai-server-manager
     (in de bron: delta CONTRACT-MG) plus twee uitbreidingen in MediaGuard (bevindingen innemen; een aanwezig bestand
     opnieuw binnenhalen). Kan pas na de Hub-policy en de MediaGuard-adapter (P2/P3, P3-02); tot dan geldt optie 2.
  2. Niet: Jelly Leon toont alleen het probleem met bewijs en een link naar MediaGuard. Gevolg: geen contractwijziging;
     herstel doe je zelf in MediaGuard.
- **Na het besluit:** vastleggen (0.3). Bij optie 1: contractstap door A-BOUW in ai-server-manager met R-VEILIG en
  R-HARDE-EIS; elke MediaGuard-release daarna vraagt het upgradebewijs (BLOK-04, BLOK-14).
- **Bron:** [BG] kop "BG-05 — Mag de Hub MediaGuard laten herstellen of zoeken (na jouw goedkeuring)?"; [CONF] punt
  C1.3-ASM-19.

### 2.5 Start golf 3

#### BG-10 — Watch Together op Android TV en Swiftfin

- **Moment:** start golf 3, voor B03-026. In het plan: S-G3-20, S-G3-26.
- **Raakt:** B03-026; JLT-07; repos jelly-leon en jelly-leon-clients.
- **Zonder besluit geldt:** niet uitgeschreven in de bron; afgeleid door dit plan: geen clientpatch; de stap voor
  B03-026 start pas na het besluit.
- **Vraag:** "Hoe doen Android TV en Swiftfin mee met Watch Together?"
- **Opties:**
  1. Volgmodus: de server stuurt de tv met de bestaande afstandsbediening (ongeveer 2 s marge, geen clientpatch).
     (Aanbevolen)
  2. Echte SyncPlay voor Android TV via een grote clientpatch op basis van een niet-gemergde community-PR. Gevolg
     volgens de bron: lastig bij upstream-updates. Swiftfin krijgt in beide gevallen geen echte SyncPlay (BG-08).
- **Na het besluit:** vastleggen (0.3).
- **Bron:** [BG] kop "BG-10 — Watch Together op Android TV en Swiftfin".

#### BG-11 — Wie ziet een nieuwe kijkgroep standaard?

- **Moment:** start golf 3, voor B03-022. In het plan: S-G3-17.
- **Raakt:** B03-022, B03-023; JLT-05; repo jelly-leon. Hangt samen met T-09 (lijst gasten en verzorgers).
- **Zonder besluit geldt:** niet uitgeschreven in de bron; afgeleid door dit plan: de stap stopt en meldt BG-11
  (zichtbaarheid is een privacykeuze; geen van de drie opties is "niets doen").
- **Vraag:** "Wie ziet een nieuwe kijkgroep standaard?"
- **Opties:**
  1. Huishouden: gasten, en kinderen van wie de maker geen verzorger is, zien niets. (Aanbevolen) Gevolg: je vult ook
     de lijst gasten en verzorgers in (T-09). Android TV, Swiftfin en derden-apps doen alleen via "tv laten volgen" mee.
  2. Prive: alleen wie is uitgenodigd. Gevolg: zelfde beperking voor Android TV, Swiftfin en derden-apps.
  3. Open: zoals standaard Jellyfin; iedereen met SyncPlay-recht ziet de groep en de namen.
- **Na het besluit:** vastleggen (0.3).
- **Bron:** [BG] kop "BG-11 — Wie ziet een nieuwe kijkgroep standaard?".

#### BG-13 — Haperende deelnemer en volle GPU's bij een groepstart

- **Moment:** start golf 3, voor B03-025. In het plan: S-G3-19, S-G4-09.
- **Raakt:** B03-025; JLT-03, JLT-04; repos jelly-leon en jelly-leon-web.
- **Zonder besluit geldt:** niet uitgeschreven in de bron; afgeleid door dit plan: het standaardgedrag van Jellyfin
  (wachten tot 30 s) en bij volle GPU's alleen waarschuwen.
- **Vraag:** "a. Wat doet een kijkgroep als een deelnemer hapert? b. Wat doet Jelly Leon als de GPU's vol zitten bij een
  groepstart?"
- **Opties vraag a:**
  1. Na 10 s doorgaan zonder de haperende deelnemer; alleen als de racetest slaagt. (Aanbevolen)
  2. Wachten zoals standaard Jellyfin (tot 30 s).
- **Opties vraag b:**
  1. Alleen waarschuwen (bijvoorbeeld "2 van 3 moeten omzetten; ruimte voor 1"). (Aanbevolen)
  2. Jelly Leon-web mag de groepstart blokkeren; officiele apps nooit.
- **Na het besluit:** vastleggen (0.3).
- **Bron:** [BG] kop "BG-13 — Haperende deelnemer en volle GPU's bij een groepstart".

#### BG-14 — Watch Together-knoppen ook in de oude weergave (Legacy)?

- **Moment:** start golf 3, voor B03-024. In het plan: S-G3-24.
- **Raakt:** B03-024; repo jelly-leon-web.
- **Zonder besluit geldt:** niet uitgeschreven in de bron; afgeleid door dit plan: alleen Modern.
- **Vraag:** "Komen de Watch Together-knoppen ook in de oude weergave (Legacy) van de webclient?"
- **Opties:**
  1. Alleen in Modern (standaard in 12.x; een kleine haak). (Aanbevolen)
  2. Ook in Legacy. Gevolg: een tweede haak die bij elke upstream-update mee moet.
- **Na het besluit:** vastleggen (0.3).
- **Bron:** [BG] kop "BG-14 — Watch Together-knoppen ook in de oude weergave (Legacy)?".

#### BG-19 — Opslag, naam en levensduur van machinevertalingen

- **Moment:** start golf 3, voor B03-047. In het plan: S-G3-08.
- **Raakt:** B03-047, B03-049; JLT-23, JLT-24, JLT-25; repo jelly-leon.
- **Zonder besluit geldt:** niet uitgeschreven in de bron; afgeleid door dit plan: de stap stopt en meldt BG-19.
  Opslag naast de media wordt nooit zonder besluit gebouwd (bestandswijziging buiten MediaGuard).
- **Vraag:** "a. Waar bewaart Jelly Leon machinevertalingen? b. Hoe heet zo'n spoor in het ondertitelmenu? c. Wat
  gebeurt er als er later een menselijke Nederlandse ondertitel verschijnt? d. Wat gebeurt er als je de module uitzet?"
- **Opties vraag a:**
  1. In Jelly Leon zelf (`/config`: interne metadatamap en eigen database). (Aanbevolen)
  2. Naast de media. Gevolg volgens de bron: een bestandswijziging buiten MediaGuard (P4-no-go), en MediaGuard en
     Bazarr stoppen met zoeken naar een menselijke vertaling.
- **Opties vraag b:** 1. "Machinevertaling". (Aanbevolen) 2. Het upstream-woord "Automatisch vertaald".
- **Opties vraag c:** 1. Verbergen (bewaard, herstelbaar). (Aanbevolen) 2. Laten staan.
- **Opties vraag d:** 1. Depubliceren; de hoofdkopieen blijven en opnieuw publiceren kan. (Aanbevolen) 2. Laten staan.
- **Na het besluit:** vastleggen (0.3). Kiest de gebruiker bij vraag a optie 2, dan eerst R-HARDE-EIS en R-VEILIG
  laten beoordelen voor er iets gebouwd wordt.
- **Bron:** [BG] kop "BG-19 — Opslag, naam en levensduur van machinevertalingen".

#### BG-21 — Onthouden audio- en ondertitelkeuzes als er een nieuw spoor bijkomt

- **Moment:** start golf 3, voor B03-047. In het plan: S-G3-08.
- **Raakt:** B03-047; JLT-24, JLT-65; repo jelly-leon. Raakt de HARDE EIS: dit is volgens de bron de enige plek waar
  een module in kijkgegevens zou schrijven.
- **Zonder besluit geldt:** optie "hold" (staat zo in de bron).
- **Vraag:** "Jellyfin nummert de sporen opnieuw zodra er een extern ondertitelspoor bijkomt; een onthouden keuze kan
  dan naar een ander spoor wijzen. Wat doet Jelly Leon dan?"
- **Opties:**
  1. Hold: niets schrijven; een publicatie die een keuze zou laten verspringen wacht op de beheerder. (Aanbevolen
     bij de start)
  2. Reset: alleen die twee keuzes wissen; de speler kiest weer op taalvoorkeur; gezien-status en positie blijven
     onaangeroerd. Volgens de bron pas na een groene JLT-24.
  3. Remap: de keuze naar hetzelfde spoor omzetten, met waarborgen. Gevolg: de Jellyfin-API schrijft daarbij het hele
     record. Volgens de bron alleen als behoud van de gekozen taal zwaarder weegt.
- **Na het besluit:** vastleggen (0.3). Optie 2 of 3 wordt alleen gebouwd met een review door R-HARDE-EIS en met
  JLT-24 en JLT-65 als bewijs.
- **Bron:** [BG] kop "BG-21 — Onthouden audio- en ondertitelkeuzes als er een nieuw spoor bijkomt".

#### BG-23 — Volledige decodecontrole voor de hele bibliotheek?

- **Moment:** start golf 3, voor B03-051...B03-053. In het plan: S-G3-11, S-G3-12.
- **Raakt:** B03-051, B03-052, B03-053; repo jelly-leon.
- **Zonder besluit geldt:** niet uitgeschreven in de bron; afgeleid door dit plan: alleen de steekproef; geen
  volledige controle van de hele bibliotheek.
- **Vraag:** "Hardware-decode verbergt beschadigingen, dus de volledige controle draait op de CPU. Voor 1000 4K-films
  kost dat naar schatting 1500 tot 2200 uur (rekensom, niet gemeten op de NAS). Hoe ver gaat de decodecontrole?"
- **Opties:**
  1. Steekproef (niveau 1,5) voor alles; volledige controle alleen voor nieuwe of door MediaGuard vervangen bestanden
     en op verzoek. (Aanbevolen) Gevolg: de beheerpagina toont een achterstandsschatting, zodat je later alsnog optie 2
     kunt kiezen.
  2. Volledige controle voor alles, binnen het dagbudget. Gevolg: zie de rekensom in de vraag.
- **Na het besluit:** vastleggen (0.3).
- **Bron:** [BG] kop "BG-23 — Volledige decodecontrole voor de hele bibliotheek?".

#### BG-24 — Bewijs-miniaturen, label, melden en home video's

- **Moment:** start golf 3, voor B03-055 en B03-057. In het plan: S-G3-14, S-G3-16, S-G3-25.
- **Raakt:** B03-055, B03-057; JLT-34, JLT-38; repos jelly-leon en jelly-leon-web.
- **Zonder besluit geldt:** niet uitgeschreven in de bron; afgeleid door dit plan: miniaturen uit, label uit, knop
  "Meld een probleem" uit, home video's en gemengde inhoud niet scannen.
- **Vraag:** "a. Mag de kwaliteitscontrole miniaturen als bewijs bewaren? b. Zien gewone gebruikers het neutrale label
  'bekend probleem met dit bestand'? c. Komt er een knop 'Meld een probleem'? d. Worden bibliotheken 'Home video's en
  foto's' en 'gemengde inhoud' gescand?"
- **Opties vraag a:** 1. Op verzoek, alleen voor beheerders, nooit naar de Hub. (Aanbevolen) 2. Uit. 3. Automatisch.
- **Opties vraag b:** 1. Uit. (Aanbevolen) 2. Aan.
- **Opties vraag c:** 1. Aan, na een eerste test. (Aanbevolen) 2. Uit.
- **Opties vraag d:** 1. Standaard niet; per bibliotheek aan te zetten, en dan nooit miniaturen of spraakherkenning.
  (Aanbevolen) 2. Ja.
- **Na het besluit:** vastleggen (0.3).
- **Bron:** [BG] kop "BG-24 — Bewijs-miniaturen, label, melden en home video's".

#### BG-25 — Gecorrigeerde ondertitelkopie bij slechte synchronisatie

- **Moment:** start golf 3, voor B03-054. In het plan: S-G3-13.
- **Raakt:** B03-054, B03-042; repo jelly-leon.
- **Zonder besluit geldt:** niet uitgeschreven in de bron; afgeleid door dit plan: alleen melden.
- **Vraag:** "Wat doet Jelly Leon bij een ondertitel die slecht gelijkloopt?"
- **Opties:**
  1. Op verzoek een gecorrigeerde kopie in de eigen opslag; nooit over het origineel en nooit als standaardspoor.
     (Aanbevolen)
  2. Alleen melden, met een hint voor de tijdverschuiving.
- **Na het besluit:** vastleggen (0.3).
- **Bron:** [BG] kop "BG-25 — Gecorrigeerde ondertitelkopie bij slechte synchronisatie".

### 2.6 Voor B03-027 (golf 3)

#### BG-09 — Mogen mensen van buiten jullie huis meekijken?

- **Moment:** voor B03-027 (golf 3). In het plan: S-G3-23; komt terug in S-P5-01 zodra Tailscale in het platform
  klaar is.
- **Raakt:** B03-027, B03-010; JLT-08, JLT-06; repos jelly-leon en jelly-leon-platform. Hangt samen met B10-005 en
  `<WERKMAP>/ai-server-manager/docs/platform-v2/03_INSTALLATIE/I21_TAILSCALE_CLOUDFLARED.md`.
- **Zonder besluit geldt:** optie "nee, alleen thuis"; B03-027 staat op Geblokkeerd (staat zo in de bron). Zie BLOK-10.
- **Vraag:** "Mogen mensen van buiten jullie huis meekijken met Watch Together?"
- **Opties:**
  1. Nee, alleen thuis. (Aanbevolen voor nu)
  2. VPN, alleen eigen apparaten (eigen tailnet, zonder delen met anderen). Volgens de bron pas zodra Tailscale in
     het platform klaar is (B10, I21).
  3. VPN met gasten via Tailscale-apparaatdeling. Gevolg volgens de bron: restrisico. Zolang Jellyfin video zonder
     inlog levert, kan een gast elke titel afspelen waarvan hij het ID kent, en zonder ACL bereikt hij ook de
     TrueNAS-UI, MediaGuard en de Hub. Daarom pas na de inlogcontrole op de streamroutes (B03-010) en een ACL die
     alleen Jelly Leon openzet.
  4. Via internet. Gevolg: vraagt eerst die inlogcontrole, HTTPS, een ADR en een besluit over poorten. Cloudflare valt
     volgens de bron af voor video.
- **Na het besluit:** vastleggen (0.3). Bij optie 2, 3 of 4 blijft B03-027 Geblokkeerd tot de genoemde voorwaarden
  gebouwd zijn; R-VEILIG beoordeelt.
- **Bron:** [BG] kop "BG-09 — Mogen mensen van buiten jullie huis meekijken?".

### 2.7 Voor golf 4

#### BG-08 — Swiftfin (iPhone, iPad, Apple TV)

- **Moment:** voor golf 4. In het plan: S-G4-27, S-G4-28.
- **Raakt:** B03-026, B03-077; JLT-06, JLT-59; repo jelly-leon-clients.
- **Zonder besluit geldt:** niet uitgeschreven in de bron; afgeleid door dit plan: geen eigen Swiftfin-patches.
- **Vraag:** "Swiftfin 1.6.1 heeft geen SyncPlay en geen skipknoppen. Eigen patches (MPL-2.0) zijn groot en hier niet
  te testen (geen Mac/Xcode). Wat doen we met Swiftfin?"
- **Opties:**
  1. In v1 accepteren: Watch Together via de volgmodus, geen skipknoppen. (Aanbevolen) Swiftfin blijft NIET
     GEVALIDEERD (Mac/Xcode).
  2. Later eigen Swiftfin-patches. Gevolg: groot, en niet te testen zonder Mac/Xcode (BLOK-02, T-14).
- **Na het besluit:** vastleggen (0.3).
- **Bron:** [BG] kop "BG-08 — Swiftfin (iPhone, iPad, Apple TV)".

### 2.8 Start golf 4

#### BG-12 — Chat en reacties tijdens samen kijken

- **Moment:** start golf 4, voor B03-028. In het plan: S-G4-10, S-G4-24.
- **Raakt:** B03-028; JLT-05; repos jelly-leon en jelly-leon-web.
- **Zonder besluit geldt:** niet uitgeschreven in de bron; afgeleid door dit plan: uit; B03-028 wordt niet gebouwd.
- **Vraag:** "Wil je chat of reacties tijdens samen kijken? Voor kinderen staat het altijd uit."
- **Opties:**
  1. Uit. (Aanbevolen; B03-028 heeft in de bron prioriteit P2)
  2. Alleen vaste reacties.
  3. Reacties en korte tekst.
- **Na het besluit:** vastleggen (0.3).
- **Bron:** [BG] kop "BG-12 — Chat en reacties tijdens samen kijken".

#### BG-26 — Afspeelprofiel aanpassen voor officiële apps en stock-tv-apps?

- **Moment:** start golf 4, voor B03-066 en B03-068. In het plan: S-G4-06, S-G4-07.
- **Raakt:** B03-066, B03-068; JLT-46; repo jelly-leon.
- **Zonder besluit geldt:** een officiele app speelt precies zoals standaard Jellyfin (staat zo in de bron).
- **Vraag:** "De officiele Android- en desktopapp laden de webclient van Jelly Leon; stock-tv-apps (Android TV, Kodi,
  Swiftfin) niet. Jelly Leon kan bij falen leren en bijsturen. Mag Jelly Leon het afspeelprofiel van die apps
  aanpassen?"
- **Opties:**
  1. Alleen als jij of de beheerder het per apparaat aanzet (standaard uit), en bij stock-tv-apps alleen beperkend.
     (Aanbevolen)
  2. Nooit.
  3. Altijd.
- **Na het besluit:** vastleggen (0.3).
- **Bron:** [BG] kop "BG-26 — Afspeelprofiel aanpassen voor officiële apps en stock-tv-apps?".

#### BG-15 — Rij "Aanbevolen voor jou" op het startscherm

- **Moment:** start golf 4, voor B03-036 en B03-037. In het plan: S-G4-20, S-G4-29.
- **Raakt:** B03-036, B03-037; JLT-14; repos jelly-leon-web en jelly-leon-clients.
- **Zonder besluit geldt:** niet uitgeschreven in de bron; afgeleid door dit plan: geen eigen rij; alleen "Meer zoals
  dit" verbetert.
- **Vraag:** "Komt er een rij 'Aanbevolen voor jou' op het startscherm?"
- **Opties:**
  1. Ja, via een kleine, geregistreerde webhaak (werkt in Modern en Legacy); Android TV niet in de eerste levering
     (wel "Meer zoals dit"). (Aanbevolen) Gevolg: een eigen rij op Android TV vraagt later een patch in de tv-app.
  2. Geen eigen rij: dan verbetert alleen "Meer zoals dit".
- **Na het besluit:** vastleggen (0.3). Een afspeellijst per gebruiker of een nieuw starttype in de server zijn in de
  bron afgevallen (schrijven in gebruikersgegevens of vragen een serverpatch); niet als optie voorleggen.
- **Bron:** [BG] kop "BG-15 — Rij "Aanbevolen voor jou" op het startscherm".

#### BG-28 — Volle of uitgevallen GPU's

- **Moment:** start golf 4, voor B03-063. In het plan: S-G4-03, S-G4-04, S-G4-08.
- **Raakt:** B03-004, B03-063; JLT-44; repos jelly-leon en jelly-leon-web.
- **Zonder besluit geldt:** niet uitgeschreven in de bron; afgeleid door dit plan: het gedrag van standaard Jellyfin en
  bij uitval alleen melden. Automatisch omschakelen gebeurt in geen enkele optie.
- **Vraag:** "a. Wat doet Jelly Leon als de GPU's vol zitten? b. Wat doet Jelly Leon als alle GPU's uitvallen?"
- **Opties vraag a:**
  1. Altijd het gedrag van standaard Jellyfin. (Aanbevolen als start)
  2. Jelly Leon-web mag bij de volgende start zelf een lagere kwaliteit kiezen, met een label en de knop "Toch
     origineel".
- **Opties vraag b:**
  1. Een voorstel "tijdelijk software-transcoding" dat een beheerder met een klik toepast en terugzet. (Aanbevolen)
  2. Alleen melden.
- **Na het besluit:** vastleggen (0.3).
- **Bron:** [BG] kop "BG-28 — Volle of uitgevallen GPU's".

#### BG-29 — Kwaliteitslabel en feedback in de speler

- **Moment:** start golf 4, voor B03-065 en B03-067. In het plan: S-G4-08, S-G4-22.
- **Raakt:** B03-067, B03-065; repos jelly-leon en jelly-leon-web.
- **Zonder besluit geldt:** niet uitgeschreven in de bron; afgeleid door dit plan: geen label en geen feedbackvraag.
- **Vraag:** "a. Wanneer toont de speler een kwaliteitslabel? b. Wanneer vraagt de speler om feedback?"
- **Opties vraag a:** 1. Alleen als beeld of geluid afwijkt van het origineel. (Aanbevolen) 2. Nooit. 3. Altijd.
- **Opties vraag b:** 1. Alleen als afspelen mislukt. (Aanbevolen) 2. Nooit. 3. Ook bij elke nieuwe combinatie van
  apparaat en formaat.
- **Na het besluit:** vastleggen (0.3).
- **Bron:** [BG] kop "BG-29 — Kwaliteitslabel en feedback in de speler".

#### BG-30 — Android TV-patch voor het automatische capabilityrapport

- **Moment:** start golf 4, voor B03-069. In het plan: S-G4-26.
- **Raakt:** B03-069; JLT-42; repo jelly-leon-clients.
- **Zonder besluit geldt:** niet uitgeschreven in de bron; afgeleid door dit plan: geen clientpatch; het rapport gaat
  alleen via de bestaande knop.
- **Vraag:** "Mag de Jelly Leon-tv-app (eigen app-ID) het bestaande capabilityrapport automatisch sturen en geleerde
  beperkende regels toepassen?"
- **Opties:**
  1. Ja, na de patches voor de eigen app-ID; prioriteit P2. (Aanbevolen)
  2. Nee: alleen via de bestaande knop.
- **Na het besluit:** vastleggen (0.3).
- **Bron:** [BG] kop "BG-30 — Android TV-patch voor het automatische capabilityrapport".

#### BG-31 — Skipknoppen: tekst en standaardgedrag

- **Moment:** start golf 4, voor B03-076 en B03-077. In het plan: S-G4-16, S-G4-23, S-G4-27, S-G4-28.
- **Raakt:** B03-007, B03-076, B03-077; JLT-55, JLT-51; repos jelly-leon, jelly-leon-web, jelly-leon-clients.
- **Zonder besluit geldt:** niet uitgeschreven in de bron; afgeleid door dit plan: de upstream-teksten (geen haak, geen
  clientpatch), overal vragen, nooit automatisch overslaan.
- **Vraag:** "a. Welke tekst staat er op de skipknoppen? b. Slaat Jelly Leon automatisch over? c. En in een Watch
  Together-groep?"
- **Opties vraag a:**
  1. Exact "Sla intro over", "Sla samenvatting over", "Sla aftiteling over" in Jelly Leon-web en de eigen apps.
     (Aanbevolen) Gevolg: een webhaak en twee clientpatches; officiele apps houden "Skip" of "Overslaan", andere talen
     de upstream-tekst.
  2. De upstream-teksten "Intro overslaan", "Terugblik overslaan", "Aftiteling overslaan" volstaan.
- **Opties vraag b:**
  1. Overal vragen (knop tonen, ook bij samenvattingen), nooit automatisch. (Aanbevolen)
  2. Intro's automatisch overslaan als standaard.
- **Opties vraag c:**
  1. Altijd vragen. (Aanbevolen)
  2. Automatisch overslaan toestaan. Gevolg: slaat dan voor iedereen over, ook voor kinderen.
- **Na het besluit:** vastleggen (0.3). Vast in de bron, geen keuze: post-credit-scenes vallen nooit binnen een
  overslaanbaar segment.
- **Bron:** [BG] kop "BG-31 — Skipknoppen: tekst en standaardgedrag".

### 2.9 Bij B03-006

#### BG-17 — Online metadata (TMDb/OMDb)

- **Moment:** bij B03-006 (metadata).
- **Raakt:** B03-006, B03-032; repo jelly-leon.
- **Zonder besluit geldt:** aan laten; dat is het standaardgedrag van Jellyfin en B03 verandert er niets aan (staat zo
  in het advies van de bron).
- **Vraag:** "Standaard Jellyfin stuurt titels naar TMDb en OMDb om metadata te halen. Aanbevelingen leunen op die
  metadata; bij de meting waren meerdere titels verkeerd gekoppeld. Blijft online metadata aan?"
- **Opties:**
  1. Aan laten: beste metadata; titels gaan naar buiten. (Aanbevolen)
  2. Uit, en metadata handmatig of lokaal verzorgen: meer privacy, meer werk.
- **Na het besluit:** vastleggen (0.3).
- **Bron:** [BG] kop "BG-17 — Online metadata (TMDb/OMDb)".

### 2.10 Voor P5

#### BG-06 — Optionele lokale modellen: welke apps, en wie maakt wat?

- **Moment:** voor P5. In het plan: S-P5-01 (besluitenronde), daarna S-P5-02 (contractdelta).
- **Raakt:** B03-038, B03-044, B03-059, B03-079; B03-008, B07-004; repos ai-server-manager (contract), jelly-leon,
  zoeken-en-persoonlijke-ai, jelly-leon-platform.
- **Zonder besluit geldt:** geen tweede producent en de app `mt` wordt niet gebouwd ([CONTRACT] kop "1.2 Open besluiten
  (tot het besluit geldt de veiligste stand)"). Zie BLOK-09.
- **Vraag:** "Het contract noemt een lokaal embeddingmodel en spraakherkenning als optionele apps, maar legt niet vast
  welke app wat levert. a. Komt de vertaling in een aparte optionele app `mt`? b. Wie maakt embeddings? c. Wie levert
  spraakherkenning?"
- **Opties vraag a:**
  1. Ja, een aparte optionele app `mt` (eventueel samen met het embeddingmodel). (Aanbevolen; de enige optie in de bron)
  2. Niet bouwen. Dit is de stand zonder besluit uit het contract, geen optie uit [BG]. Gevolg (afleiding van dit
     plan): er is dan geen vertaalmotor, dus BG-18 en BG-20 hoeven niet gevraagd te worden.
- **Opties vraag b:**
  1. Voorlopig geen embeddings. (Aanbevolen) Komen ze er later, dan adviseert de bron: Jelly Leon maakt ze, met
     hetzelfde model in beide apps.
  2. Jelly Leon maakt ze en zoeken leest.
  3. Zoeken maakt ze en Jelly Leon leest.
- **Opties vraag c:**
  1. Jelly Leon is de ene spraakproducent (eigenaar van de media-metadata). (Aanbevolen)
  2. Zoeken is de ene spraakproducent.
- **Na het besluit:** vastleggen (0.3) en de contractdelta laten bouwen (in de bron: delta CONTRACT-MODEL, delta
  CONTRACT-MT, delta ZK-2). Vast in het advies van de bron: alle model-apps standaard uit, zonder GPU of alleen op de
  UHD 770, nooit op de A310.
- **Bron:** [BG] kop "BG-06 — Optionele lokale modellen: welke apps, en wie maakt wat?".

#### BG-18 — Vertaalmotor en licentie van het vertaalmodel

- **Moment:** voor P5, samen met BG-06. In het plan: S-P5-01.
- **Raakt:** B03-044, B03-045; JLT-21, JLT-27; repos jelly-leon en jelly-leon-platform.
- **Zonder besluit geldt:** de app `mt` wordt niet gebouwd ([CONTRACT] kop "1.2 Open besluiten (tot het besluit geldt de
  veiligste stand)"); de experimentele route met een taalmodel wordt niet gebouwd.
- **Vraag:** "a. Welke vertaalmotor gebruikt Jelly Leon voor Engels naar Nederlands? b. Welke licenties mogen de
  modellen van de experimentele route met een taalmodel hebben?"
- **Opties vraag a:**
  1. Een aparte optionele app `mt`, standaard uit, met OPUS-MT (Engels naar Nederlands) via CTranslate2; het model
     wordt meegeleverd in de mt-image. (Aanbevolen) Gevolg: het model is CC-BY 4.0 (naamsvermelding); het is eenmalig
     buiten de NAS omgezet, met herkomst en sha256.
  2. Dezelfde app `mt`, maar je uploadt het model zelf.
- **Opties vraag b:**
  1. Alleen modellen met een Apache-2.0- of MIT-licentie, en alleen na een gemeten budget op de NAS; anders vervalt
     die route. (Aanbevolen)
  2. Ook gated modellen met eigen voorwaarden.
- **Na het besluit:** vastleggen (0.3). Vast in de bron, geen keuze: modellen met een NC-licentie nooit; de motor in de
  jelly-leon-image is vervallen. De lijst met modelnamen staat in de bron en wordt hier niet herhaald.
- **Bron:** [BG] kop "BG-18 — Vertaalmotor en licentie van het vertaalmodel".

### 2.11 In P5

#### BG-20 — Automatisch vertalen en automatisch publiceren

- **Moment:** in P5, voor B03-046. In het plan: S-P5-01.
- **Raakt:** B03-043, B03-046; repo jelly-leon.
- **Zonder besluit geldt:** niet uitgeschreven in de bron; afgeleid door dit plan: automatisch vertalen en automatisch
  publiceren staan beide uit.
- **Vraag:** "a. Staan automatisch vertalen en automatisch publiceren na installatie aan? b. Hoe lang wacht Jelly Leon
  tot MediaGuard of Bazarr eerst een menselijke ondertitel vindt?"
- **Opties vraag a:**
  1. Beide uit; per bibliotheek aanzetten; publiceren pas automatisch na een geslaagde kalibratie. (Aanbevolen)
  2. Direct aan.
- **Opties vraag b:**
  1. 72 uur. (Aanbevolen)
  2. Een andere wachttijd; de gebruiker noemt het aantal uren.
- **Na het besluit:** vastleggen (0.3).
- **Bron:** [BG] kop "BG-20 — Automatisch vertalen en automatisch publiceren".

### 2.12 Gegevens en besluiten over de echte omgeving (D01...D18)

Dit zijn vooral gegevens die alleen de gebruiker of een meting op de echte NAS kan leveren, geen keuzes. Ze blijven in
de Excel "Open" tot de gebruiker ze invult in de onboarding-wizard van de Hub of tot ze via de TrueNAS-API gemeten
zijn ([PROMPT] kop "2. Vaste keuzes en genomen besluiten (niet opnieuw vragen)"). Statussen: Open, Ingevuld, Getest,
Geblokkeerd, N.v.t. ([CONTRACT] kop "11. Bewijs en Excel (EVIDENCE.json)"). Een agent vult nooit zelf een D-gegeven in
en zet er nooit een op "Getest": dat vraagt de echte omgeving (BLOK-01). Geen NAS-gegevens in een repo.

De Hub houdt per D-gegeven een gate dicht tot de minimale status bereikt is. Bron van de kolom "Hub-gate":
`<WERKMAP>/ai-server-manager/apps/api/src/hub/onboarding/gates.py` (gezien op 2026-11-11). "N.v.t." opent nooit een
gate en er is geen omzeilroute.

| ID | Wat de gebruiker levert (bron) | Nodig voor (bron) | Hub-gate (minimale status) |
|---|---|---|---|
| D01 | TrueNAS-versie: exacte build en API-schema | connector en bouw | `connector_bouw`, `deployment` (Getest) |
| D02 | Poolnaam en datasetpaden: alle appdata- en mediapaden | mount en back-up | `mount_backup`, `deployment` (Getest) |
| D03 | NAS-adres en domeinen: LAN-adres, hostnamen, VPN of tunnel, poorten | deployment | `deployment` (Getest) |
| D04 | OneDrive-methode: taak of tool, encryptie, scope, retentie, herstelgegevens | backup gate | `backup_gate` (Ingevuld) |
| D05 | OneDrive-herstelbewijs: foto plus database-export, geisoleerd getest | updates van bestaande apps | `backup_gate`, `bestaande_app_updates` (Getest) |
| D06 | Gezondheid van de ZFS-pool: SMART, scrubs, vrije ruimte, fouten, snapshotcapaciteit | data-mutaties | `data_mutatie` (Getest) |
| D07 | Huidige appversies: image-tags, API, configuratieback-ups, gezondheid, actief gebruik | upgrades | `bestaande_app_updates`, `upgrades` (Getest) |
| D08 | Intel-GPU-rendernodes: welke `/dev/dri`-node de A310 is en welke de UHD 770; QSV-ondersteuning | fork en transcode | `gpu_transcode` (Getest) |
| D09 | AI-API-budget (D09): inbegrepen maandbudget, harde stop, geen betaalde overschrijding | AI-agent met cloudtool | `ai_cloud` (Getest) |
| D10 | genomen (zie deel 1) | - | - |
| D11 | Router en DNS-terugval: routermodel, huidige DNS, eigenaar van poort 53, terugvaltoegang | DNS-overstap naar AdGuard | `dns_cutover` (Getest) |
| D12 | Gree: type en firmware; lokale UDP-compatibiliteit via echte bind en readback | Gree-aansturing | `gree_aansturing` (Getest) |
| D13 | Zigbee-hardware: dongle of adapter, serial-by-id, sensortype | Zigbee-installatie | `zigbee_installatie` (Getest) |
| D14 | HomeWizard-meterkoppeling: P1, Energy Socket bij de boiler (alleen meten), meter bij de airco | exact energiedashboard | `energie_dashboard_exact` (Getest) |
| D15 | Mediaclients: tv-modellen, telefoons, Android TV of Apple TV, gewenst offline gedrag | mediaserver-cutover | `mediaserver_cutover` (Getest) |
| D16 | RPO en RTO: hoeveel historie en uitval maximaal per app | herstelbeleid | `backup_gate`, `restore_policy` (Ingevuld) |
| D17 | OIDC-bereikbaarheid: domeinnaam, HTTPS, herstelaccount, rollen | Authentik | `authentik` (Getest) |
| D18 | Navidrome (optioneel): meerwaarde boven Jellyfin na een gebruikerstest | optioneel | `navidrome` (Ingevuld) |

Samengestelde gates in hetzelfde bestand: `deployment` vraagt ook een gekoppelde executor; `backup_gate` vraagt ook een
recente geverifieerde back-up van de Hub-database; `data_mutatie` vraagt ook gezonde pools en de `backup_gate`;
`bestaande_app_updates` vraagt ook de `backup_gate`; `upgrades` vraagt ook `backup_gate`, `data_mutatie` en
`deployment`; `r2_r3_acties` vraagt de executor, `backup_gate` en `data_mutatie`. Zie BLOK-20.

Wanneer vragen:

- **Voor P5:** D03, D08, D11 (zo gevraagd in `<WERKMAP>/.lokaal/plan/uit/STAPPEN_P5.md`, kop "2.2 Besluiten en gegevens
  die vooraf nodig zijn", gezien op 2026-11-11). D08 is ook nodig voor optie 1 van BG-35 (golf 2) en voor BG-27.
- **Voor P6 (acceptatie op de echte NAS):** D01, D02, D04...D07, D15, D16, D17. D07 moet ook melden of er naast Emby een
  stock-Jellyfin draait ([BG] kop "9. Gegevens die nodig zijn (geen keuze)").
- **Bij de bouw van het betreffende onderdeel van my_house op echte hardware:** D12, D13, D14.
- **D09:** voor de eerste AI-functie met een cloudtool in productie. Vaste regel, geen keuze: alleen binnen het
  inbegrepen tegoed, met harde stop, nul betaalde overschrijding. Tot D09 er is staat AI standaard uit.

Drie D-punten zijn wel een keuze. Leg ze voor met dit menu.

#### D16 — RPO en RTO per app

- **Moment:** voor P6; de `backup_gate` en `restore_policy` blijven dicht tot D16 is ingevuld.
- **Raakt:** herstelbeleid (B12), alle acties met risico R2 of R3; repo ai-server-manager.
- **Zonder besluit geldt:** de gates blijven dicht; de policy weigert uitvoering zonder geverifieerd herstelpunt binnen
  het RPO (`BLK-CHECKPOINT` in `<WERKMAP>/ai-server-manager/policy/blokkades.yaml`).
- **Vraag:** "Hoeveel historie mag je per app maximaal kwijtraken (RPO) en hoe lang mag een app maximaal uit de lucht
  zijn (RTO)?"
- **Opties:** de bron geeft geen opties. Laat A-VERKEN eerst een voorstel per app opstellen (de catalogus heeft al een
  veld per app: klasse `AppRpoRto` in `<WERKMAP>/ai-server-manager/apps/api/src/hub/onboarding/catalog.py`) en leg dat
  voor als:
  1. Voorstel overnemen. (Aanbevolen, aanbeveling van dit plan)
  2. Per app aanpassen; de gebruiker noemt de waarden.
- **Na het besluit:** de gebruiker vult de waarden in de wizard in; Excel-status wordt Ingevuld.
- **Bron:** [D] rij D16.

#### D18 — Navidrome (optioneel)

- **Moment:** wanneer het uitkomt; de bron vraagt eerst een gebruikerstest.
- **Raakt:** `<WERKMAP>/ai-server-manager/docs/platform-v2/03_INSTALLATIE/I22_NAVIDROME_OPT.md`.
- **Zonder besluit geldt:** Navidrome wordt niet geinstalleerd (gate `navidrome` dicht).
- **Vraag:** "Wil je Navidrome als aparte muziekserver naast Jelly Leon?"
- **Opties:**
  1. Niet installeren. (Aanbevolen, aanbeveling van dit plan: het is optioneel en de meerwaarde is niet getest)
  2. Eerst zelf testen of het meerwaarde heeft boven Jellyfin, daarna beslissen.
  3. Installeren.
- **Na het besluit:** Excel-status Ingevuld of N.v.t.
- **Bron:** [D] rij D18.

#### D04 — OneDrive-methode

- **Moment:** voor P6; nodig voor de `backup_gate`.
- **Raakt:** B12-001; repo ai-server-manager. Zie T-11.
- **Zonder besluit geldt:** B12-001 blijft Geblokkeerd; de `backup_gate` blijft dicht.
- **Vraag en opties:** de bron geeft geen opties, alleen wat er geleverd moet worden (taak of tool, encryptie, scope,
  retentie, herstelgegevens). ONBEKEND - eerst vaststellen met:
  `grep -n -i 'onedrive' <WERKMAP>/ai-server-manager/docs/platform-v2/02_BOUWPLANNEN/B12_*.md`. Laat A-VERKEN daaruit
  een menu opstellen voor het wordt voorgelegd.
- **Na het besluit:** de gebruiker vult de methode in de wizard in; Excel-status wordt Ingevuld. Geen
  herstelgegevens of accountgegevens in een repo.
- **Bron:** [D] rij D04; [EVIDENCE ai-server-manager] rij B12-001.

### 2.13 Genomen besluiten die onder een voorwaarde opnieuw voorgelegd worden

| Besluit | Voorwaarde | Wat de regisseur dan doet | Bron |
|---|---|---|---|
| BG-01 (legacy-auth blijft uit) | een derden-app die de gebruiker echt gebruikt (D15) werkt niet zonder legacy-auth | het besluit opnieuw voorleggen met de naam van de app en de gemeten fout; tot dan blijft `EnableLegacyAuthorization` uit | [BG] kop "BG-01 — MediaGuard-koppeling na de upgrade naar Jellyfin 12.x" |
| Noodlogin (A07) | de gebruiker wil de noodlogin ook via Tailscale gebruiken | niets bouwen op verzoek van een agent: een beheerder zet het bereik zelf aan in de Hub-UI (audit en waarschuwing) | [STATUS] kop "Besluiten van de gebruiker na contract 1.3 (2026-11-10)" |
| BG-04 (sleutel via de Hub) | de Hub-koppeling van de Jelly Leon-plugin (JL4) blijkt zonder sleuteloverdracht niet haalbaar | melden aan de regisseur; die legt voor of sleuteloverdracht mag. De bron zegt alleen "bij voorkeur zonder" | [BG] kop "Besluiten van de gebruiker na contract 1.3 (2026-11-10)" |
| BG-37 (Netflix-masters) | er is weer schijfruimte | opnieuw vragen; nu "niet zolang de schijf vol is" | [BG] kop "BG-37 — Testdata met een beperkende licentie" |

### 2.14 Besluiten zonder bron-ID (Z-01...Z-15)

Deze vragen staan in de bronnen als open punt, maar hebben daar geen eigen ID. De opties komen uit de genoemde bron;
waar de bron geen advies geeft staat "(Aanbevolen, aanbeveling van dit plan)" bij de veiligste optie.

#### Z-01 — Hoe pusht de upstream-sync van de forks zijn resultaat?

- **Moment:** voor P5 (forkbeheer B08-005); eerder mag, het blokkeert geen bouwstap.
- **Raakt:** `<WERKMAP>/jelly-leon/.github/workflows/upstream-sync.yml` (geheim `JL_SYNC_PUSH_TOKEN`, job `push`),
  `<WERKMAP>/jelly-leon-web/.github/workflows/upstream-sync.yml` (geheim `JLW_SYNC_PUSH_TOKEN`, job `beoordeling`);
  B03-013, B08-005, EX48, JLT-67. Zie T-03 en BLOK-05.
- **Zonder besluit geldt:** sync-push staat uit; een geslaagde sync staat alleen als git-bundle in de artefacten van de
  workflow-run ([CONTRACT] kop "1.2 Open besluiten (tot het besluit geldt de veiligste stand)").
- **Vraag:** "De wekelijkse upstream-sync van de forks kan zijn resultaat pas naar GitHub pushen als er een geheim met
  schrijfrecht is. Hoe wil je dat regelen?"
- **Opties:**
  1. Ik maak zelf in de GitHub-web-UI een fine-grained token aan (inhoud schrijven plus workflows-recht) en zet het als
     repo-geheim in beide forks. (Aanbevolen, aanbeveling van dit plan: de workflows lezen dit geheim al; er hoeft niets
     omgebouwd te worden) Een agent kan dit token niet aanmaken.
  2. De bouwer mag per fork een SSH-deploysleutel met schrijfrecht aanmaken en als repo-geheim zetten. Dit is de
     uitdrukkelijke toestemming waar [STATUS] om vraagt. Gevolg: de pushjob in beide workflows moet worden omgebouwd,
     want die leest nu alleen het tokengeheim.
  3. Sync-push blijft uit. Gevolg: elke sync wordt met de hand uit de git-bundle overgenomen.
- **Na het besluit:** vastleggen (0.3). Bij optie 1: de regisseur herinnert de gebruiker aan T-03. Bij optie 2: een
  bouwstap voor A-BOUW met R-VEILIG als verplichte review. Het geheim zelf komt nooit in een repo, log of rapport.
- **Bron:** [STATUS] kop "Besluiten van de gebruiker (gevraagd via keuzemenu op de nieuwe machine, 2026-11-09)", punt 4,
  en kop "Vervolgbesluiten van de gebruiker (2026-11-09, middag)"; [CONTRACT] kop "1.1 Besluiten van de gebruiker (vast)",
  nr. 4; de toelichting bovenaan de twee workflowbestanden.

#### Z-02 — Bevestigen van de Host-beperking op statuspagina's (K1)

- **Moment:** voor P3 (de bestaande apps krijgen dan dezelfde statuspagina).
- **Raakt:** de statuspagina van elke dienst met een Hub-koppeling; [CONTRACT] kop "3.7 Koppelen via de statuspagina".
- **Zonder besluit geldt:** K1 zoals gebouwd.
- **Vraag:** "Op de statuspagina van een dienst kun je alleen koppelen als je de pagina opent via het IP-adres, een naam
  zonder punt of een naam onder .local, .lan, .internal of .home.arpa. Wie hem via een eigen domeinnaam of een
  routerdomein met een publieke extensie opent, kan daar niet koppelen; koppelen via de Hub en via de
  installatie-instellingen werkt wel, en de pagina verwijst naar het IP-adres. Dit beschermt tegen DNS-rebinding.
  Blijft dit zo?"
- **Opties:**
  1. Ja, zo laten. (Aanbevolen, aanbeveling van dit plan: het is de gebouwde en gereviewde stand)
  2. Nee, koppelen moet ook via een eigen domeinnaam kunnen. Gevolg: dit vraagt een nieuwe contractronde en een nieuwe
     veiligheidsreview in elke dienst; de bron werkt geen alternatief uit. A-VERKEN stelt eerst een voorstel op, daarna
     legt de regisseur dat opnieuw voor.
- **Na het besluit:** vastleggen (0.3).
- **Bron:** [RUW] kop "ai-server-manager" (zoek op "K1" en "Host-beperking"); ai-server-manager
  `docs/adr/ADR-0027-contract-1-3.md`.

#### Z-03 — Voor/na-rapport bij elke database-migratie van een mediaserver (RV2)

- **Moment:** voor P3 (in P3 komt de ADR over MediaGuard-updates via de Hub, zie BLOK-14).
- **Raakt:** elke update van Jelly Leon of MediaGuard die de database migreert; de HARDE EIS.
- **Zonder besluit geldt:** RV2 zoals vastgelegd: elke upgrade die de database van een mediaserver migreert vraagt een
  voor/na-rapport per gebruiker en akkoord.
- **Vraag:** "Elke update van een mediaserver die de database migreert vraagt nu een voor/na-rapport per gebruiker en
  jouw akkoord, ook latere kleine Jelly Leon-updates met een upstream-migratie. Dat is veilig maar zwaar. Blijft dit zo?"
- **Opties:**
  1. Ja, bij elke database-migratie. (Aanbevolen, aanbeveling van dit plan: dit volgt de HARDE EIS letterlijk)
  2. Versoepelen. Gevolg: de bron werkt geen versoepeling uit. A-VERKEN stelt een voorstel op, R-HARDE-EIS beoordeelt
     het, en pas daarna legt de regisseur het opnieuw voor. Tot dan geldt optie 1.
- **Na het besluit:** vastleggen (0.3).
- **Bron:** [RUW] kop "ai-server-manager" (zoek op "RV2 HARDE EIS"); ai-server-manager
  `docs/adr/ADR-0028-review-contract-1-3.md`.

#### Z-04 — Afwijkende attributieregels in oude commits

- **Moment:** NU alleen melden; een besluit is pas nodig als de gebruiker de historie schoon wil hebben.
- **Raakt:** alle repos; vaste regel 2 (commits eindigen met de vaste attributieregel; geen modelnaam in commits).
  Gemeten op 2026-11-11: de commits tot en met 2026-11-10 eindigen op een attributieregel waarin een modelnaam staat
  (in ai-server-manager 168 van de 171 commits, in my_house 76, in media-guard-ultimate 17); de commits van 2026-11-11
  volgen de vaste regel. De repos zijn publiek.
- **Zonder besluit geldt:** de historie blijft zoals ze is; nieuwe commits volgen de vaste regel.
- **Vraag:** "In de commits tot en met 10 november staat een attributieregel met een modelnaam erin. Dat botst met de
  regel 'geen modelnaam in commits'. De historie aanpassen kan alleen met een force-push, en die is verboden. Wat wil
  je?"
- **Opties:**
  1. Laten staan; alleen nieuwe commits volgen de regel. (Aanbevolen, aanbeveling van dit plan: geen force-push)
  2. Historie herschrijven. Gevolg: eenmalige, uitdrukkelijke uitzondering op "geen force-push" per repo; alle lokale
     kopieen en lopende branches moeten daarna opnieuw worden opgehaald; bij de forks raakt het ook upstream-commits en
     is het niet uitvoerbaar zonder de upstream-historie te breken.
- **Na het besluit:** vastleggen (0.3). Meten per repo (alleen lezen; bij de forks tellen ook upstream-co-auteurs mee,
  daar is de telling niet bruikbaar):
  `git -C <WERKMAP>/<repo> log --format=%B | grep -i '^Co-Authored-By:' | grep -v -c -x 'Co-Authored-By: Claude <noreply@anthropic.com>'`
- **Bron:** eigen meting van dit plan met het commando hierboven; [CONTRACT] kop "12. Commit- en pushregels".

#### Z-05 — Testwaarde met de vorm van een echt GitHub-token

- **Moment:** NU alleen melden; uitvoeren bij de eerstvolgende bouwstap in jelly-leon-web.
- **Raakt:** `<WERKMAP>/jelly-leon-web/tools/jelly-leon-web/tests/test_sync_workflow.py`.
- **Zonder besluit geldt:** de testwaarde blijft staan. Het is geen echt geheim, maar geheimscanners kunnen erop aanslaan.
- **Vraag:** "In een test van jelly-leon-web staat een nepwaarde die de vorm van een GitHub-token heeft. Mag die worden
  vervangen door een neutrale testwaarde?"
- **Opties:**
  1. Ja, vervangen in een nieuwe commit; de historie blijft ongewijzigd. (Aanbevolen, aanbeveling van dit plan)
  2. Laten staan.
- **Na het besluit:** vastleggen (0.3). Bij optie 1: kleine bouwstap voor A-BOUW; de test moet blijven aantonen wat hij
  nu aantoont. De waarde zelf wordt nergens geciteerd.
- **Bron:** [RUW] kop "jelly-leon-web".

#### Z-06 — Het werk overnemen in `main`

- **Moment:** NU alleen melden; besluit voor P6 (samen met Z-07).
- **Raakt:** alle repos. Gemeten op 2026-11-11 (GitHub-API, alleen lezen):
  - standaardbranch `main`, werkbranch loopt daar ver op voor: ai-server-manager, home-control-hub, appstore-en-fork,
    jelly-leon-platform, zoeken-en-persoonlijke-ai;
  - standaardbranch is de werkbranch, `main` bestaat ook: jelly-leon, jelly-leon-web, my_house;
  - standaardbranch is de werkbranch, er is geen `main`: jelly-leon-clients, media-guard-ultimate,
    media-source-optimizer.
- **Zonder besluit geldt:** alles blijft op de werkbranch `ccr-c133d7a0-kuz1cv`; er wordt niets in `main` overgenomen en
  er wordt geen PR geopend ([CONTRACT] kop "12. Commit- en pushregels"; vaste regel 1).
- **Vraag:** "Al het werk staat op de werkbranch. In vijf repos is `main` de standaardbranch en loopt die ver achter.
  Hoe wil je het werk in `main` krijgen?"
- **Opties:**
  1. Nog niet; eerst de Cutover-gate. (Aanbevolen, aanbeveling van dit plan: overnemen in de standaardbranch is een
     handmatige R2-stap van de gebruiker, zie T-13)
  2. Per repo een PR van de werkbranch naar `main`; ik beoordeel en voeg zelf samen.
  3. Per repo de standaardbranch op GitHub omzetten naar de werkbranch (zoals nu al bij zes repos). Gevolg: geen
     samenvoeging nodig; `main` blijft achterlopen tot je hem zelf bijwerkt.
- **Na het besluit:** vastleggen (0.3). Een agent opent alleen een PR als de gebruiker optie 2 kiest, en voegt nooit
  zelf samen.
- **Bron:** meting 2026-11-11 met `gh api repos/<eigenaar>/<repo> --jq .default_branch` en
  `git -C <WERKMAP>/<repo> ls-remote --heads origin main`; [CONTRACT] kop "12. Commit- en pushregels"; jelly-leon
  `docs/adr/ADR-0027-p4-0-uitvoering-12x.md` ("Overnemen in de standaardbranch en een release blijven handmatige
  R2-stappen").

#### Z-07 — Moment van de eerste release (v0.1.0) van de nieuwe repos

- **Moment:** voor P6.
- **Raakt:** ai-server-manager, home-control-hub, appstore-en-fork, jelly-leon-platform, zoeken-en-persoonlijke-ai;
  `<WERKMAP>/.lokaal/plan/uit/STAPPEN_P6.md` (S-P6-02...S-P6-06, gezien op 2026-11-11). Zie BLOK-06.
- **Zonder besluit geldt:** geen release-tags; de catalogus houdt `digest_pending_release` en er kan niets op de echte
  NAS worden geinstalleerd.
- **Vraag:** "De vijf nieuwe repos hebben nog geen release. Een release start met een versie-tag en publiceert het image
  op GHCR. Wanneer wil je de eerste release?"
- **Opties:**
  1. In P6, na de gates van P2...P5, in de volgorde van het stappenplan. (Aanbevolen, aanbeveling van dit plan)
  2. Eerder, per repo zodra de CI van die repo groen is. Gevolg: je kunt eerder op de NAS proefinstalleren, maar elke
     latere contractwijziging vraagt een nieuwe release.
- **Na het besluit:** vastleggen (0.3). Een release is een R2-stap: de regisseur vraagt per repo akkoord voor de tag.
  De release-workflows van deze vijf repos starten op een tag-push (gezien in elk `.github/workflows/release.yml`), dus
  samenvoegen in `main` is er technisch niet voor nodig.
- **Bron:** de vijf workflowbestanden `<WERKMAP>/<repo>/.github/workflows/release.yml`; [CONTRACT] kop "12. Commit- en
  pushregels" (release-tags pas na groene CI, contractbesluit 6) en kop "9. Manifeststandaard (B08-001, eigenaar
  `appstore-en-fork`)" (zoek op `digest_pending_release`).

#### Z-08 — my_house: het Hub-adres is zonder inloggen leesbaar

- **Moment:** voor P3 (my_house wordt dan een standaard Custom App, C1.3-MH-03).
- **Raakt:** my_house, het pad `/_shc/config.json` van de webcontainer; de link "Terug naar de Hub" (O-11).
- **Zonder besluit geldt:** zo laten: het contract noemt `HUB_URL` niet geheim.
- **Vraag:** "my_house geeft het ingestelde Hub-adres zonder inloggen. Wie my_house via een tunnel zonder extra
  toegangscontrole bereikt, ziet dus het interne adres van de Hub. Wat wil je?"
- **Opties:**
  1. Zo laten. (Aanbevolen, aanbeveling van dit plan: het adres is volgens het contract niet geheim en er verandert
     niets aan de werking)
  2. Alleen tonen na inloggen.
  3. Alleen tonen op het thuisnetwerk.
  Het gevolg van optie 2 en 3 voor de link op het inlogscherm en voor de Android-app is niet vastgesteld: ONBEKEND -
  eerst vaststellen met: `grep -rn '_shc/config' <WERKMAP>/my_house --include=*.ts --include=*.tsx --include=*.kt`.
- **Na het besluit:** vastleggen (0.3). Bij optie 2 of 3: bouwstap in P3 met R-VEILIG.
- **Bron:** [RUW] kop "my_house"; `<WERKMAP>/my_house/docs/ontwerp/PEIL_REVIEW.md` kop "10. QA-controle na de review
  (stap 6, 9 november 2026)"; my_house `docs/adr/ADR-0008-peil-omzetting-twee-fasen.md`. Het optionele veld `HUB_URL` in
  het installatieformulier zelf is al gedekt door [CONTRACT] kop "2.3 Bestaande apps (MediaGuard, MSO, my_house,
  Jellyfin/Jelly Leon, Emby)" (zoek op "Terug naar de Hub").

#### Z-09 — Eigen Jelly Leon-apps: ondertekening en verspreiding

- **Moment:** voor P6; eerder als golf 4 een installeerbare eigen app moet opleveren (BG-08).
- **Raakt:** jelly-leon-clients; D15; T-14 en T-19.
- **Zonder besluit geldt:** geen release van eigen APK's of IPA's; alleen debug-builds uit de CI, bedoeld om te testen.
- **Vraag:** "(a) Hoe wil je de eigen Jelly Leon-apps verspreiden? (b) Heb je een Apple Developer-account voor de
  iOS- en tvOS-app?"
- **Opties vraag a:**
  1. APK's als release-artefact in de repo jelly-leon-clients. (Aanbevolen, aanbeveling van dit plan: geen extra
     dienst nodig)
  2. Een downloadpagina of een eigen app-repository, geleverd door Jelly Leon of de Hub. Gevolg: extra bouwwerk dat nog
     niet ontworpen is.
  3. Alleen sideloaden; geen verspreidingskanaal.
- **Opties vraag b:**
  1. Nee. Gevolg: de iOS- en tvOS-app blijven NIET GEVALIDEERD; de gebruiker gebruikt daar de officiele app.
  2. Ja. Gevolg: de gebruiker regelt zelf het account en een Mac met Xcode (T-14).
- **Na het besluit:** vastleggen (0.3). Elke optie van vraag a vraagt eerst ondertekening: de sleutels maakt en beheert
  de gebruiker (T-19); een agent maakt nooit een ondertekeningssleutel aan.
- **Bron:** jelly-leon-clients `docs/adr/ADR-0008-geen-truenas-app-voor-clients.md` kop "Open punt voor het platform",
  `docs/adr/ADR-0004-branding-en-applicationid.md` en `README.md` kop "Open vragen voor de gebruiker".

#### Z-10 — media-source-optimizer: CI op de werkbranch

- **Moment:** voor P3 (dan wordt in deze repo gebouwd).
- **Raakt:** `<WERKMAP>/media-source-optimizer/.github/workflows/ci.yaml`.
- **Zonder besluit geldt:** de workflow `ci` start niet bij een push op de werkbranch (alleen bij `main`, tags, PR's of
  handmatig). Na elke push start de bouwer hem met de hand: `gh workflow run ci.yaml --ref ccr-c133d7a0-kuz1cv`, zonder de invoer
  `release_version` (gevuld betekent publiceren; zie POORTEN.md, P-media-source-optimizer, kop "6. CI-controle").
- **Vraag:** "De CI van Media Source Optimizer start niet vanzelf bij een push op de werkbranch. Wat wil je?"
- **Opties:**
  1. De workflow ook laten starten bij een push op de werkbranch. (Aanbevolen, aanbeveling van dit plan: kleinste
     wijziging; elke push krijgt dan vanzelf bewijs)
  2. Een branch `main` aanmaken en die de standaardbranch maken. Gevolg: hangt samen met Z-06.
  3. Handmatig blijven starten.
- **Na het besluit:** vastleggen (0.3). Bij optie 1: kleine bouwstap voor A-BOUW in P3.
- **Bron:** [RUW] kop "media-source-optimizer"; media-source-optimizer
  `docs/adr/ADR-0005-eerlijke-ci-e2e-en-logcontrole.md` kop "Besluiten". Let op: [RUW] noemt een andere standaardbranch
  dan de meting van 2026-11-11 (zie deel 5).

#### Z-11 — Licentie voor de fork-eigen code van jelly-leon-clients

- **Moment:** voor P6 (voor de eerste eigen release).
- **Raakt:** jelly-leon-clients, mappen `tools/`, de workflows en de documentatie.
- **Zonder besluit geldt:** de fork-eigen code heeft geen eigen licentie; de upstream-code houdt de upstream-licentie.
- **Vraag:** "De eigen hulpcode in jelly-leon-clients heeft nog geen licentie. Welke moet het worden?"
- **Opties:**
  1. GPL-3.0, zoals de eigen repos. (Aanbevolen, aanbeveling van dit plan: volgt contractbesluit 8)
  2. Dezelfde licentie als de upstream-client waar de code bij hoort.
  3. Geen licentie toevoegen.
- **Na het besluit:** vastleggen (0.3) en een ADR in jelly-leon-clients.
- **Bron:** jelly-leon-clients `docs/adr/ADR-0007-licenties-en-bronbeschikbaarheid.md`; [CONTRACT] kop "1.1 Besluiten van
  de gebruiker (vast)", nr. 8.

#### Z-12 — Bestaande apps uitschakelen (Plex, JellyPlex-Watched, Readarr, FlareSolverr)

- **Moment:** na de Cutover-gate, per app, pas na de inventaris op de echte NAS (B08-002) en het bewijs dat de bron
  per app noemt.
- **Raakt:** APP-01, APP-03, APP-04, APP-05; `<WERKMAP>/ai-server-manager/docs/platform-v2/03_INSTALLATIE/I26_BESTAANDE_APPS.md`.
- **Zonder besluit geldt:** alle bestaande apps blijven draaien. Een agent stopt of verwijdert nooit een bestaande app.
- **Vraag (per app, met het bewijs erbij):** "Uit de meting blijkt <bewijs>. Wil je <app> als proef stoppen?"
- **Opties:**
  1. Laten draaien. (Aanbevolen, aanbeveling van dit plan zolang het bewijs ontbreekt)
  2. Proefstop met terugzetmogelijkheid; data blijft staan. Voor Plex noemt de bron een proefstop van 72 uur.
  3. Na een geslaagde proefstop: de gebruiker verwijdert de app zelf.
- **Na het besluit:** vastleggen (0.3) en de rij in de Excel bijwerken; de status blijft "Geblokkeerd" met de tekst
  NIET GEVALIDEERD tot de proef op de echte NAS is gedaan.
- **Bron:** [APPS] kop "Bestaande apps — beslisregister"; I26_BESTAANDE_APPS.md kop "Stap 6. Decommission".

#### Z-13 — Aanmelden na de overname: nieuw wachtwoord of SSO per gebruiker

- **Moment:** in P6, voor de echte overname vanuit Emby.
- **Raakt:** B03-015; B13 (Authentik); D17; T-21.
- **Zonder besluit geldt:** geen echte overname. Wachtwoorden kunnen niet worden overgezet.
- **Vraag:** "Wachtwoorden uit Emby kunnen niet mee. Hoe melden de gebruikers zich daarna aan?"
- **Opties:**
  1. Elke gebruiker krijgt een nieuw wachtwoord dat jij uitdeelt. (Aanbevolen, aanbeveling van dit plan: werkt zonder
     Authentik)
  2. Aanmelden via SSO (Authentik). Gevolg: kan pas als B13 op de echte NAS werkt (D17, T-16, BLOK-17).
  3. Per gebruiker verschillend; de gebruiker levert de lijst.
- **Na het besluit:** vastleggen (0.3).
- **Bron:** [BG] kop "2.1 Open punten over Emby (geen BG-ID; bestaande Excel-rijen en B03-015)".

#### Z-14 — Emby stoppen en later verwijderen

- **Moment:** na de Cutover-gate; pas na JLT-74 en de controlelijst "Emby verwijderen".
- **Raakt:** APP-02, I26-26-02; de HARDE EIS.
- **Zonder besluit geldt:** Emby blijft draaien en blijft de terugval. Een agent stopt of verwijdert Emby nooit.
- **Vraag:** "De controlelijst 'Emby verwijderen' is groen: <samenvatting van het voor/na-rapport>. Wil je Emby als
  proef stoppen?"
- **Opties:**
  1. Nog niet; Emby blijft draaien. (Aanbevolen, aanbeveling van dit plan zolang JLT-74 niet op de echte NAS is gedaan)
  2. Proefstop; de data van Emby blijft staan als terugval.
  3. Na een geslaagde proefperiode: de gebruiker verwijdert de data van Emby zelf (apart besluit, T-10).
- **Na het besluit:** vastleggen (0.3).
- **Bron:** [BG] kop "2.1 Open punten over Emby (geen BG-ID; bestaande Excel-rijen en B03-015)"; [B03-PLAN] kop
  "10.9.2 Controlelijst "Emby verwijderen" (de gebruiker voert uit)".

#### Z-15 — Hulpmappen buiten de repos opruimen

- **Moment:** wanneer het uitkomt; niet terwijl er in my_house gebouwd wordt.
- **Raakt:** `<WERKMAP>/.lokaal/my_house-peil/`, `<WERKMAP>/.lokaal/my_house-review/`, `<WERKMAP>/.lokaal/my_house-qa/`.
- **Zonder besluit geldt:** de mappen blijven staan.
- **Vraag:** "Drie hulpmappen van de Peil-omzetting van my_house staan nog buiten de repo. Mogen ze weg?"
- **Opties:**
  1. Laten staan tot na P3. (Aanbevolen, aanbeveling van dit plan: in P3 wordt opnieuw aan my_house gebouwd)
  2. Nu verwijderen.
- **Na het besluit:** `<WERKMAP>/.lokaal/mso-aio-wrapper/` valt hier niet onder: die is nog in gebruik voor de
  alles-in-een-test van media-source-optimizer.
- **Bron:** [RUW] kop "my_house" (zoek op "mogen weg na akkoord").

---

## 3. Taken van de gebruiker

Dit kan geen agent doen: het vraagt de echte NAS, echte hardware, een account van de gebruiker of een uitdrukkelijk
akkoord. Regels voor de regisseur:

- Een agent voert deze taken nooit uit en bootst ze nooit na als "gedaan". De bijbehorende rij blijft "Geblokkeerd" met
  de tekst NIET GEVALIDEERD en wat er nog nodig is.
- De regisseur herinnert de gebruiker op het genoemde moment, in gewone taal, met wat het oplevert. Een herinnering
  per moment, alle taken van dat moment in een bericht.
- Meldt de gebruiker dat een taak gedaan is, dan laat de regisseur dat eerst meten (kolom "Controle") voor een status
  verandert. Wachtwoorden, tokens, sleutels en NAS-gegevens komen nooit in een repo, rapport, log of commit; de
  gebruiker voert ze zelf in op de plek waar ze horen (GitHub-geheim, TrueNAS, onboarding-wizard van de Hub).

### 3.0 Overzicht: wanneer herinneren

| Moment | Taken |
|---|---|
| NU | T-01, T-03 (na besluit Z-01) |
| Start golf 2 | T-08, T-17 |
| Start golf 3 | T-09 |
| Voor golf 4 | T-14, T-19, T-20 |
| Voor P5 | T-22 |
| Start P6 | T-02, T-04, T-05, T-11, T-13, T-15, T-16, T-18 |
| In P6, op de NAS | T-06, T-07, T-12, T-21 |
| Na de Cutover-gate | T-10 |

### 3.1 De taken

#### T-01 — GHCR-pakketten van MediaGuard koppelen aan de nieuwe repo

- **Wat precies:** op GitHub het pakket `mediaguard-core` koppelen aan de nieuwe publieke repo media-guard-ultimate en
  per pakket bevestigen dat het publiek is. [RUW] noemt ook de pakketten `-web`, `-encode` en de twee forks. Hoe dat
  op GitHub precies gaat staat niet in de bron.
- **Waarom alleen de gebruiker:** de pakketinstellingen horen bij het account; het token van de bouwomgeving mag
  pakketten niet lezen.
- **Blokkeert:** elke nieuwe MediaGuard-release (BLOK-04) en daarmee alles wat in P3 en P4 een nieuwe MediaGuard-versie
  op de NAS vraagt.
- **Herinneren:** NU, en opnieuw bij de start van P3.
- **Controle:** ONBEKEND - het token kon de koppeling niet lezen. Gemeten is alleen dat de tag `1.2.2-aio` anoniem te
  lezen is. De gebruiker bevestigt de koppeling zelf.
- **Bron:** [CONF] punt C1.3-MGU-02; [STATUS] kop "Contract 1.3 — onafhankelijke review (2026-11-10)"; [RUW] kop
  "media-guard-ultimate".

#### T-02 — Zichtbaarheid van de GHCR-pakketten van de andere repos

- **Wat precies:** na de eerste release van elke repo per pakket bevestigen dat het publiek is.
- **Waarom alleen de gebruiker:** zie T-01.
- **Blokkeert:** installatie van dat image op de echte NAS: zolang een pakket niet aantoonbaar publiek is, is die
  installatie NIET GEVALIDEERD, en bij een prive-pakket geblokkeerd.
- **Herinneren:** start P6, direct na de releases (S-P6-02...S-P6-06 in `<WERKMAP>/.lokaal/plan/uit/STAPPEN_P6.md`).
- **Controle:** de tag lezen zonder aanmelding. De releasestappen in `STAPPEN_P6.md` doen dat met
  `docker manifest inspect ghcr.io/<eigenaar>/<repo>:<versie>` (gezien op 2026-11-11). Lukt dat niet, dan meldt de stap
  het en zet de gebruiker de zichtbaarheid zelf.
- **Bron:** [CONTRACT] kop "2.1 Publieke images en registry-login".

#### T-03 — Geheim voor de sync-push van de forks

- **Wat precies:** afhankelijk van besluit Z-01. Bij optie 1: zelf een fine-grained token maken (inhoud schrijven plus
  workflows-recht) en als repo-geheim `JL_SYNC_PUSH_TOKEN` in jelly-leon en `JLW_SYNC_PUSH_TOKEN` in jelly-leon-web
  zetten.
- **Waarom alleen de gebruiker:** een fine-grained token kan alleen via de GitHub-web-UI worden gemaakt.
- **Blokkeert:** het automatisch pushen van `sync/<tag>` (BLOK-05); echt forkbeheer B08-005. Bouwen wordt er niet door
  tegengehouden.
- **Herinneren:** NU (samen met Z-01) en opnieuw voor P5.
- **Controle:** de eerstvolgende run van de workflow "Upstream-sync" meldt niet meer dat het geheim ontbreekt:
  `gh run list --repo <eigenaar>/jelly-leon --workflow upstream-sync.yml`.
- **Bron:** zie Z-01.

#### T-04 — De gegevens D01...D18 invullen

- **Wat precies:** de gegevens uit deel 2.12 invullen in de onboarding-wizard van de Hub, of ze laten meten via de
  TrueNAS-API. Daar hoort ook bij: of Jelly Leon beide GPU's ziet (de bron meldt dat de ingebouwde GPU naast een losse
  kaart vaak uit staat in het BIOS; niet op deze NAS gecontroleerd).
- **Waarom alleen de gebruiker:** het zijn feiten over de eigen NAS, het netwerk, de apparaten en de accounts.
- **Blokkeert:** de Hub-gates uit deel 2.12 (BLOK-20) en alle NAS-rijen.
- **Herinneren:** D03, D08, D11 voor P5; de rest bij de start van P6; D12...D14 bij de hardwaretest van my_house.
- **Controle:** de gate in de Hub staat op "toegestaan".
- **Bron:** [D]; [BG] kop "9. Gegevens die nodig zijn (geen keuze)".

#### T-05 — Alleen-lezen-gebruiker en API-sleutel op TrueNAS

- **Wat precies:** op de echte NAS een alleen-lezen-gebruiker (rol READONLY_ADMIN) en een API-sleutel aanmaken en die
  in de Hub invoeren. De Hub weigert een sleutel met schrijfrechten.
- **Waarom alleen de gebruiker:** het is een handeling op de echte NAS met beheerdersrechten.
- **Blokkeert:** I01-01-04 en elke meting via de TrueNAS-API (dus ook D01, D02, D06, D07).
- **Herinneren:** start P6, als eerste NAS-taak.
- **Bron:** [EVIDENCE ai-server-manager] rij I01-01-04; [EVIDENCE jelly-leon-platform] rij I01-01-04.

#### T-06 — De tests op de echte NAS uitvoeren

- **Wat precies:** het NAS-deel van P6 doorlopen en zelf afvinken. Het stappenplan noemt dat "DEEL B" met de
  onderdelen N-P6-01 en verder; op 2026-11-11 stond daarvan alleen de gatetabel in het bestand.
- **Waarom alleen de gebruiker:** er is geen echte NAS in de bouwomgeving (BLOK-01).
- **Blokkeert:** elke rij met NIET GEVALIDEERD (echte NAS); de rij P6 in de Excel.
- **Herinneren:** in P6, zodra het deel zonder NAS klaar is.
- **Bron:** `<WERKMAP>/.lokaal/plan/uit/STAPPEN_P6.md` kop "2.2 Gates tijdens de fase (start van elk onderdeel van
  DEEL B)" (gezien op 2026-11-11); [GATES].

#### T-07 — Akkoord op elk verschil in het voor/na-rapport

- **Wat precies:** bij elke proefrun en bij de echte overname het voor/na-rapport per gebruiker lezen en op elk
  verschil uitdrukkelijk akkoord geven of weigeren.
- **Waarom alleen de gebruiker:** HARDE EIS; geen agent beslist of een verschil aanvaardbaar is.
- **Blokkeert:** de echte overname vanuit Emby (B03-015, JLT-70, JLT-74) en elke upgrade die de database van een
  mediaserver migreert (RV2).
- **Herinneren:** in P6 bij elke proefrun op de NAS.
- **Bron:** [BG] kop "2.1 Open punten over Emby (geen BG-ID; bestaande Excel-rijen en B03-015)".

#### T-08 — Echte afleveringen labelen (BG-34)

- **Wat precies:** in het labelscherm dat de bouwer levert van echte afleveringen aangeven waar intro, aftiteling en
  samenvatting beginnen en eindigen. Een aangewezen persoon mag dit ook doen.
- **Waarom alleen de gebruiker:** het vraagt de eigen bibliotheek en een menselijk oordeel.
- **Blokkeert:** de nauwkeurigheidsmeting op echte data; zonder labels telt alleen de synthetische testset.
- **Herinneren:** start golf 2, zodra het labelscherm er is.
- **Bron:** [BG] kop "BG-34 — Wie labelt de echte afleveringen?".

#### T-09 — Feiten voor Watch Together en de planner

- **Wat precies:** opgeven welke gebruikers gasten zijn en wie welk kind verzorgt; of MediaGuard het nachtvenster met
  de CPU-baan gebruikt; of MediaGuard nu aan Emby of aan Jellyfin gekoppeld is; of Plex of Emby nog op een van de GPU's
  transcoderen.
- **Waarom alleen de gebruiker:** het zijn feiten over het huishouden en de eigen instellingen.
- **Blokkeert:** de standaardzichtbaarheid van kijkgroepen (BG-11) en de vensters van de planner.
- **Herinneren:** start golf 3.
- **Bron:** [BG] kop "9. Gegevens die nodig zijn (geen keuze)".

#### T-10 — Emby zelf stoppen en later verwijderen

- **Wat precies:** na een groene controlelijst "Emby verwijderen" zelf Emby stoppen (proefstop) en later, als apart
  besluit, de data van Emby verwijderen.
- **Waarom alleen de gebruiker:** HARDE EIS: geen agent stopt of verwijdert Emby.
- **Blokkeert:** niets in de bouw. APP-02 en I26-26-02 blijven "Geblokkeerd" tot de gebruiker dit gedaan heeft.
- **Herinneren:** pas na de Cutover-gate en alleen als JLT-74 op de echte NAS is uitgevoerd. Zie Z-14.
- **Bron:** [B03-PLAN] kop "10.9.2 Controlelijst "Emby verwijderen" (de gebruiker voert uit)".

#### T-11 — Herstelproef uit OneDrive

- **Wat precies:** een echte foto en een database-export van een app uit OneDrive terugzetten in een geisoleerde
  omgeving en het resultaat vastleggen.
- **Waarom alleen de gebruiker:** het vraagt de echte NAS en het OneDrive-account.
- **Blokkeert:** B12-001; D04 en D05; de `backup_gate` en daarmee alle data-mutaties, updates en R2/R3-acties.
- **Herinneren:** start P6; dit is de eerste gate na "NAS versie/pool bekend".
- **Bron:** [EVIDENCE ai-server-manager] rij B12-001.

#### T-12 — Akkoord en testbronnen voor de proeven van MediaGuard en Media Source Optimizer

- **Wat precies:** voor MediaGuard: uitdrukkelijk akkoord op de schaduwfase, een echte download en een proefperiode van
  24 tot 48 uur, met een geldige back-up. Voor Media Source Optimizer: opgeven welke testbronnen gebruikt mogen worden
  en toestemming geven voor de proef.
- **Waarom alleen de gebruiker:** echte downloads en echte bronnen; het risico ligt bij de gebruiker.
- **Blokkeert:** B04-010 en B05-007.
- **Herinneren:** in P6, na T-05 en T-11.
- **Bron:** [EVIDENCE media-guard-ultimate] rij B04-010; [EVIDENCE media-source-optimizer] rij B05-007.

#### T-13 — Overnemen in de standaardbranch en uitbrengen

- **Wat precies:** het werk overnemen in de standaardbranch (volgens besluit Z-06) en per repo akkoord geven voor een
  release-tag. De eerste Jelly Leon-release op 12.x is een stap van de gebruiker.
- **Waarom alleen de gebruiker:** het zijn handmatige R2-stappen; geen PR's en geen samenvoeging zonder vragen.
- **Blokkeert:** de eerste Jelly Leon-release; de release van my_house (BLOK-19).
- **Herinneren:** start P6.
- **Bron:** jelly-leon `docs/adr/ADR-0027-p4-0-uitvoering-12x.md`; [BG] kop "BG-02 — Release vóór de upgrade en P4-0 in
  de Excel".

#### T-14 — Apple Developer-account en een Mac met Xcode

- **Wat precies:** alleen als de gebruiker bij BG-08 of Z-09 voor een eigen iOS- of tvOS-app kiest: een Apple
  Developer-account en een Mac met Xcode beschikbaar maken.
- **Waarom alleen de gebruiker:** account en hardware van de gebruiker; de bouwomgeving heeft geen Mac (BLOK-02).
- **Blokkeert:** elke validatie van Swiftfin en Safari; die blijven NIET GEVALIDEERD (Mac/Xcode).
- **Herinneren:** voor golf 4, samen met BG-08.
- **Bron:** jelly-leon-clients `README.md` kop "Open vragen voor de gebruiker"; [BG] kop "BG-08 — Swiftfin (iPhone,
  iPad, Apple TV)".

#### T-15 — Echte apparaten voor my_house

- **Wat precies:** de echte Zigbee-adapter, Hue, Gree, HomeWizard en een Android-toestel beschikbaar hebben en de
  hardwaretest doorlopen; een echt Cloudflare-account voor de tunneltest.
- **Waarom alleen de gebruiker:** echte hardware en een echt account.
- **Blokkeert:** B06-009; D12, D13, D14.
- **Herinneren:** start P6, na de installatie van my_house als standaard Custom App (BLOK-13).
- **Bron:** [EVIDENCE my_house] rij B06-009.

#### T-16 — Domeinnaam, HTTPS en herstelaccount voor Authentik

- **Wat precies:** een domeinnaam met HTTPS voor de aanmelddienst regelen, een herstelaccount aanmaken en de rollen
  bevestigen (D17).
- **Waarom alleen de gebruiker:** eigen domein en eigen accounts.
- **Blokkeert:** B13-002 en SSO (BLOK-17); optie 2 van Z-13.
- **Herinneren:** start P6.
- **Bron:** [EVIDENCE home-control-hub] rij B13-002.

#### T-17 — MediaGuard pauzeren voor de GPU-meting (BG-27)

- **Wat precies:** alleen bij de aanbevolen optie van BG-27: MediaGuard zelf pauzeren zolang de meting loopt en daarna
  weer aanzetten.
- **Waarom alleen de gebruiker:** een agent schakelt bestaande bewaking of verwerking nooit uit.
- **Blokkeert:** de meting per werkklasse zonder MediaGuard-last.
- **Herinneren:** start golf 2 (besluit) en in P6 op de NAS (uitvoering).
- **Bron:** [BG] kop "BG-27 — De A310 voor live kijken terwijl MediaGuard AV1 encodeert; meten".

#### T-18 — Monitors bevestigen in Uptime Kuma

- **Wat precies:** het monitorplan per app in de echte Uptime Kuma overnemen en per monitor bevestigen.
- **Waarom alleen de gebruiker:** de bron beschrijft dit als een handeling van de beheerder in de UI van Uptime Kuma.
- **Blokkeert:** I08-08-03.
- **Herinneren:** start P6, na de installatie van Uptime Kuma.
- **Bron:** [EVIDENCE jelly-leon-platform] rij I08-08-03; [CONF] punt C1.3-ASM-20.

#### T-19 — Ondertekeningsgeheimen voor de Android-apps

- **Wat precies:** de ondertekeningssleutels van de Android-apps beheren en als repo-geheim zetten. De workflows
  `<WERKMAP>/media-guard-ultimate/.github/workflows/android.yml` en `<WERKMAP>/my_house/.github/workflows/release.yml`
  lezen zulke geheimen. Voor de eigen Jelly Leon-apps bestaat nog geen ondertekening (Z-09).
- **Waarom alleen de gebruiker:** een agent maakt of ziet nooit een ondertekeningssleutel.
- **Blokkeert:** een ondertekende release van de Android-apps.
- **Herinneren:** voor golf 4 en bij Z-09.
- **Controle:** of de geheimen nu zijn ingesteld is ONBEKEND - eerst vaststellen met:
  `gh secret list --repo <eigenaar>/<repo>` (toont alleen namen, geen waarden).
- **Bron:** de twee workflowbestanden; jelly-leon-clients `docs/adr/ADR-0004-branding-en-applicationid.md`.

#### T-20 — Derden-apps testen zonder de oude aanmeldmethode

- **Wat precies:** opgeven welke derden-apps echt gebruikt worden (D15) en daarvan minstens een app testen tegen Jelly
  Leon met de oude aanmeldmethode uit.
- **Waarom alleen de gebruiker:** eigen apparaten en apps.
- **Blokkeert:** niets in de bouw. Faalt een app die echt gebruikt wordt, dan legt de regisseur BG-01 opnieuw voor
  (deel 2.13).
- **Herinneren:** voor golf 4 en in P6.
- **Bron:** [BG] kop "BG-01 — MediaGuard-koppeling na de upgrade naar Jellyfin 12.x".

#### T-21 — Nieuwe wachtwoorden uitdelen of SSO instellen

- **Wat precies:** na besluit Z-13 elke gebruiker een nieuw wachtwoord geven of SSO voor die gebruiker instellen.
- **Waarom alleen de gebruiker:** wachtwoorden zijn niet over te zetten en een agent maakt of ziet ze niet.
- **Blokkeert:** de echte overname.
- **Herinneren:** in P6, voor de echte overname.
- **Bron:** [BG] kop "2.1 Open punten over Emby (geen BG-ID; bestaande Excel-rijen en B03-015)".

#### T-22 — Accounts en sleutels voor de onderdelen van P5

- **Wat precies:** een Tailscale-account en het tunnelgeheim van Cloudflare (I21); beheerdersgegevens van AdGuard Home
  en NetAlertX (I11, I12); API-sleutels van Immich en Jellyfin voor de zoekadapters (B07-002); een echt apparaat met
  microfoon en luidspreker voor spraak (B15).
- **Waarom alleen de gebruiker:** eigen accounts en apparaten.
- **Blokkeert:** geen bouwstap; wel de NAS-rijen van deze onderdelen, en B03-027 (BLOK-10).
- **Herinneren:** voor P5 melden, uitvoeren in P6.
- **Bron:** `<WERKMAP>/.lokaal/plan/uit/STAPPEN_P5.md` kop "2.2 Besluiten en gegevens die vooraf nodig zijn" (gezien op
  2026-11-11).

---

## 4. Blokkades

Een blokkade is iets wat technisch vastzit: een stap kan het niet oplossen door harder te bouwen. Regels:

- De regisseur start geen keten waarvan het doel onder een blokkade valt. Wat er wel kan, staat bij "Wat wel kan".
- Een stap die op een blokkade stuit, bouwt het deel dat wel kan, zet de rij op "Geblokkeerd" met de tekst
  NIET GEVALIDEERD en wat er nog nodig is, en meldt het BLOK-nummer aan de regisseur. Nooit een blokkade omzeilen met
  een nagebootst resultaat, een voorbeeldwaarde of een uitgeschakelde controle.
- Drie soorten: **omgeving** (lost alleen de echte NAS, echte hardware of een echt account op), **gebruiker** (wacht
  op een taak uit deel 3 of een besluit uit deel 2) en **volgorde** (wacht op ander werk in het plan).

### 4.0 Overzicht

| ID | Wat zit vast | Soort | Opgeheven door |
|---|---|---|---|
| BLOK-01 | alles wat de echte NAS vraagt | omgeving | T-05, T-06 (P6, door de gebruiker) |
| BLOK-02 | alles wat echte hardware of een Mac met Xcode vraagt | omgeving | T-14, T-15 |
| BLOK-03 | alles wat een echt account vraagt | omgeving | T-11, T-14, T-15, T-16, T-22 |
| BLOK-04 | elke nieuwe MediaGuard-release | gebruiker | T-01, plus het upgradebewijs per release |
| BLOK-05 | automatisch pushen van de upstream-sync | gebruiker | Z-01, T-03 |
| BLOK-06 | installeren van de nieuwe apps op digest | volgorde, gebruiker | Z-07, S-P6-02...S-P6-06 |
| BLOK-07 | Hub-kaarten en Hub-toegang van B03 | volgorde | Hub-sleutelpin in Jelly Leon (JL4) en de Hub-adapter |
| BLOK-08 | MediaGuard-acties via de Hub of Jelly Leon | gebruiker, volgorde | BG-05, daarna de contractdelta en de sleutelscopes |
| BLOK-09 | de app `mt` en een tweede producent van modellen | gebruiker | BG-06, BG-18, daarna S-P5-02 |
| BLOK-10 | meekijken van buiten huis (B03-027) | gebruiker, omgeving | BG-09 en een gevalideerde Tailscale op de NAS |
| BLOK-11 | de echte overname vanuit Emby (JLT-74) | omgeving, volgorde | zie de lijst bij BLOK-11 |
| BLOK-12 | delen van de upgradetests JLT-61, JLT-62, JLT-67 | volgorde, extern | zie BLOK-12 |
| BLOK-13 | my_house installeren als standaard Custom App | volgorde | C1.3-MH-03 in P3 |
| BLOK-14 | MediaGuard-update via de Hub; sleutelrotatie | volgorde | twee ADR's in ai-server-manager |
| BLOK-15 | inventaris van bestaande apps voor appstore-en-fork | volgorde, omgeving | Hub opent twee leesroutes voor diensten; daarna de echte NAS |
| BLOK-16 | zekerheid over het gedrag van TrueNAS Custom Apps | omgeving | meting op de echte NAS (D01) |
| BLOK-17 | SSO met Authentik (B13-002) | omgeving, volgorde | T-16, Authentik op de NAS, ondertekend uitvoerverzoek |
| BLOK-18 | batchmodules van Jelly Leon aan op de NAS | volgorde, gebruiker | belastingtest JLT-66, daarna BG-07 |
| BLOK-19 | werk staat niet in de standaardbranch `main`; release van my_house | gebruiker | Z-06, T-13 |
| BLOK-20 | de Hub-gates (uitrol, back-up, data, updates, GPU, DNS, huis) | gebruiker, omgeving | T-04, T-11 |

### 4.1 De blokkades

#### BLOK-01 — Geen echte NAS

- **Wat zit vast:** elke rij met het label NIET GEVALIDEERD (echte NAS). Geteld op 2026-11-11 komt dat label ruim 300 keer
  voor in de elf EVIDENCE-bestanden (307 bij het schrijven, 315 aan het eind van die dag), in elke repo.
- **Waardoor:** de bouwomgeving is een ontwikkelmachine met simulators; er is geen TrueNAS.
- **Wat wel kan:** bouwen en in de simulator testen. Status dan "Bezig" met "Sim-getest", nooit meer.
- **Opgeheven door:** de gebruiker in P6 (T-05, T-06). Geen agent zet zo'n rij op iets anders dan "Geblokkeerd" of
  "Bezig".
- **Opnieuw tellen:**
  `cat <WERKMAP>/*/docs/platform-v2/EVIDENCE.json | grep -o -E 'NIET GEVALIDEERD \([^)]*\)' | sort | uniq -c | sort -rn`
- **Bron:** [CONTRACT] kop "11. Bewijs en Excel (EVIDENCE.json)"; [EVIDENCE <repo>] van alle elf repos.

#### BLOK-02 — Geen echte hardware, geen Mac met Xcode

- **Wat zit vast:** rijen met NIET GEVALIDEERD (hardware), 111 keer geteld, en NIET GEVALIDEERD (Mac/Xcode), 31 keer
  geteld, de laatste in jelly-leon-clients, jelly-leon-web en jelly-leon. Voorbeelden: Swiftfin en Safari; de twee
  GPU's van de NAS; Zigbee, Hue, Gree, HomeWizard en een Android-toestel voor my_house.
- **Waardoor:** die apparaten staan bij de gebruiker.
- **Wat wel kan:** simulators en bouwen van de Android-apps; voor Swiftfin alleen wat zonder Mac te controleren is.
- **Opgeheven door:** T-14 (alleen na BG-08 of Z-09), T-15, T-04 (D08, D12...D15).
- **Bron:** jelly-leon-clients `README.md` kop "Open vragen voor de gebruiker"; [EVIDENCE my_house] rij B06-009; [BG]
  kop "9. Gegevens die nodig zijn (geen keuze)".

#### BLOK-03 — Geen echte accounts

- **Wat zit vast:** rijen met NIET GEVALIDEERD (account), 35 keer geteld. Het gaat om OneDrive (B12-001), Cloudflare
  en Tailscale (I21; tunneltest van B06-009), het Apple-account (Swiftfin) en de aanmelddienst Authentik (B13-002).
- **Waardoor:** accounts en geheimen van de gebruiker; die komen nooit in de bouwomgeving of in een repo.
- **Wat wel kan:** de simulator van de dienst; de rij blijft "Geblokkeerd".
- **Opgeheven door:** T-11, T-14, T-15, T-16, T-22.
- **Bron:** [EVIDENCE ai-server-manager] rij B12-001; [EVIDENCE home-control-hub] rij B13-002; [EVIDENCE my_house] rij
  B06-009; `<WERKMAP>/.lokaal/plan/uit/STAPPEN_P5.md` kop "2.2 Besluiten en gegevens die vooraf nodig zijn".

#### BLOK-04 — Geen nieuwe MediaGuard-release

- **Wat zit vast:** elke release van media-guard-ultimate, en dus elke nieuwe MediaGuard-versie op de NAS.
- **Waardoor:** twee dingen. (1) Het GHCR-pakket `mediaguard-core` is nog niet aan de nieuwe publieke repo gekoppeld;
  tot dan geldt "geen nieuwe release". (2) Elke MediaGuard-release moet een upgrade bewijzen op een gevulde database
  van de vorige versie; zonder dat bewijs geen release en geen update op de NAS.
- **Wat wel kan:** bouwen, testen en committen op de werkbranch; CI volgen.
- **Opgeheven door:** T-01 voor (1); een bouwstap met upgradetest per release voor (2).
- **Bron:** [CONF] punt C1.3-MGU-02; [CONTRACT] kop "2.3 Bestaande apps (MediaGuard, MSO, my_house, Jellyfin/Jelly
  Leon, Emby)" regel 7; kop "12. Commit- en pushregels".

#### BLOK-05 — De upstream-sync pusht niet

- **Wat zit vast:** het automatisch pushen van een synchronisatiebranch in jelly-leon en jelly-leon-web; echt
  forkbeheer (B08-005 staat op "Niet gestart").
- **Waardoor:** de workflows lezen een repo-geheim (`JL_SYNC_PUSH_TOKEN`, `JLW_SYNC_PUSH_TOKEN`) dat de gebruiker moet
  zetten. Zonder geheim levert de workflow van jelly-leon een git-bundle als artefact. Op 2026-11-11 had de geplande
  sync nog geen enkele run; waarom is niet vastgesteld (deel 6).
- **Wat wel kan:** de sync handmatig beoordelen op de ontwikkelmachine; alle bouwstappen.
- **Opgeheven door:** Z-01 en T-03.
- **Bron:** `<WERKMAP>/jelly-leon/.github/workflows/upstream-sync.yml`;
  `<WERKMAP>/jelly-leon-web/.github/workflows/upstream-sync.yml`; [EVIDENCE appstore-en-fork] rij B08-005.

#### BLOK-06 — Geen release, dus geen digest

- **Wat zit vast:** installeren van de vijf nieuwe apps (en van Jelly Leon) op een vaste digest. Alle eigen
  manifesten dragen op 2026-11-11 de markering `digest_pending_release`: de zeven bestanden
  `deploy/manifest/*.manifest.yaml` in ai-server-manager (twee), home-control-hub, appstore-en-fork,
  jelly-leon-platform, zoeken-en-persoonlijke-ai en jelly-leon (controle:
  `grep -l digest_pending_release <WERKMAP>/*/deploy/manifest/*.yaml`). De markering is alleen toegestaan voor de
  eerste release van een eigen image. Voor jelly-leon is de eerste release een stap van de gebruiker (BG-02, T-13).
- **Waardoor:** de vijf nieuwe repos (ai-server-manager, home-control-hub, appstore-en-fork, jelly-leon-platform,
  zoeken-en-persoonlijke-ai) hadden op 2026-11-11 geen tag `v0.1.0`. Een release start bij een versie-tag.
- **Wat wel kan:** alles in de simulator; lokaal gebouwde images.
- **Opgeheven door:** Z-07 en de releasestappen S-P6-02...S-P6-06; daarna T-02.
- **Controle:** `gh api "repos/<eigenaar>/<repo>/tags?per_page=100" --jq '.[].name'`
- **Bron:** [CONTRACT] kop "9. Manifeststandaard (B08-001, eigenaar `appstore-en-fork`)" en kop "12. Commit- en
  pushregels"; `<WERKMAP>/.lokaal/plan/uit/STAPPEN_P6.md` (gezien op 2026-11-11).

#### BLOK-07 — Hub-kaarten van B03 wachten op de sleutelpin

- **Wat zit vast:** de Hub-kaart en de Hub-toegang van de B03-functies.
- **Waardoor:** de gate "Hub-sleutelpin in Jelly Leon (JL4)" is voorwaarde "Voor Hub-kaarten van B03". Die pin hoort
  bij de B03-plugin (C1.3-JL-06, moment P4) en de Hub-adapter voor Jelly Leon (C1.3-ASM-21).
- **Wat wel kan:** de modules zelf; zonder pin antwoordt de plugin 401 `not_linked`.
- **Opgeheven door:** de bouwstappen voor C1.3-JL-06 en C1.3-ASM-21. In `STAPPEN_P5.md` wachten S-P5-62 en S-P5-107
  hierop.
- **Bron:** [GATES] kop "Gate matrix"; [CONF] punten C1.3-JL-06 en C1.3-ASM-21.

#### BLOK-08 — Geen MediaGuard-acties via de Hub of Jelly Leon

- **Wat zit vast:** herstellen, opnieuw zoeken en ondertitels zoeken in MediaGuard op verzoek van de Hub of Jelly Leon.
  Jelly Leon toont alleen een link (`handmatig_in_mediaguard`).
- **Waardoor:** besluit BG-05 is open en het contract staat deze acties nog niet toe. Daarna zijn nog nodig: de
  contractdelta (in de bron "Δ-CONTRACT-MG"), de sleutelscopes in MediaGuard (C1.3-MGU-05) en de policy in de Hub
  (C1.3-ASM-19).
- **Wat wel kan:** alleen-lezen-status van MediaGuard tonen; de link naar MediaGuard.
- **Opgeheven door:** BG-05 (optie 1), daarna de genoemde bouwstappen. Bij optie 2 blijft dit zo; dat is dan geen
  blokkade meer maar het besluit.
- **Bron:** [GATES] kop "Gate matrix"; [CONF] punten C1.3-ASM-19, C1.3-MGU-05, C1.3-JL-08; [CONTRACT] kop "1.2 Open
  besluiten (tot het besluit geldt de veiligste stand)".

#### BLOK-09 — De app `mt` en de model-apps

- **Wat zit vast:** de aparte vertaal-app `mt` en een tweede producent van embeddings of spraakherkenning.
- **Waardoor:** BG-06 en BG-18 zijn open; het contract legt nog niet vast welke app wat levert.
- **Wat wel kan:** alles wat zonder model werkt; modellen blijven standaard uit met terugval.
- **Opgeheven door:** BG-06 en BG-18, daarna de contractdelta S-P5-02.
- **Bron:** [CONTRACT] kop "1.2 Open besluiten (tot het besluit geldt de veiligste stand)";
  `<WERKMAP>/.lokaal/plan/uit/STAPPEN_P5.md` kop "2.2 Besluiten en gegevens die vooraf nodig zijn".

#### BLOK-10 — Meekijken van buiten huis (B03-027)

- **Wat zit vast:** B03-027.
- **Waardoor:** BG-09 is open, en ook na een "ja" blijft het geblokkeerd tot Tailscale (I21, B10-005) op de echte NAS
  is gevalideerd. B10-005 staat op "Niet gestart".
- **Wat wel kan:** Watch Together binnen huis.
- **Opgeheven door:** BG-09, de bouw van B10-005, daarna T-22 en T-06.
- **Bron:** [BG] kop "BG-09 — Mogen mensen van buiten jullie huis meekijken?"; [EVIDENCE home-control-hub] rij B10-005.

#### BLOK-11 — De echte overname vanuit Emby (JLT-74)

- **Wat zit vast:** JLT-74 en daarmee APP-02 en I26-26-02.
- **Waardoor:** de rij vraagt alles tegelijk: de echte NAS met de echte Emby (D07 gemeten), een ZFS-snapshot, de
  overname-assistent in het beheer van Jelly Leon (P4-0; de gebruiker heeft geen terminal), back-updekking van het
  exportarchief (in de bron "Δ-HUB-3") en de dubbele koppeling van MediaGuard (in de bron "Δ-MG-DUAL").
- **Wat wel kan:** de proefovername tegen echte containers op de ontwikkelmachine (B03-015 en JLT-70 staan op "Bezig").
- **Opgeheven door:** de bouw van de drie genoemde onderdelen, daarna T-04 (D07), T-06, T-07. Emby blijft al die tijd
  draaien; T-10 komt pas daarna.
- **Bron:** [EVIDENCE jelly-leon] rijen JLT-74, B03-015, JLT-70; [B03-PLAN] kop "10.9.1 Overname vanuit Emby (B03-015
  deel A; prioriteit P0, al in golf 0)".

#### BLOK-12 — Delen van de upgradetests

- **Wat zit vast:**
  - JLT-61 onderdeel (b): staat op "Sim-mislukt". De bron noemt het voor de stap van 10.11.11 naar 12.4 niet haalbaar
    met de stock-image; een echte latere 12.x-image om de weigering met een echte migratie te bewijzen bestaat nog niet.
  - JLT-62: "Niet gestart". Geldt alleen als D07 een Jellyfin meet; de overnamewizard is niet gebouwd.
  - JLT-67: "Niet gestart". Er is geen nieuwere upstream-tag dan v12.4 (stand 2026-11-10 volgens de bron).
- **Waardoor:** JLT-61 (b) en JLT-67 wachten op een nieuwe upstream-versie; JLT-62 wacht op D07.
- **Wat wel kan:** niets forceren. Een stap mag JLT-61 (b) niet als gehaald melden.
- **Opgeheven door:** een nieuwe upstream-tag (controle: de workflow "Upstream-sync", of handmatig de tags van
  upstream bekijken); T-04 (D07).
- **Bron:** [EVIDENCE jelly-leon] rijen JLT-61, JLT-62, JLT-67.

#### BLOK-13 — my_house is nog geen standaard Custom App

- **Wat zit vast:** installatie van my_house op de NAS volgens de vaste regel "een alles-in-een image", en daarmee de
  hardwaretest B06-009.
- **Waardoor:** my_house vraagt nu een installatiescript en installatie via YAML/compose. Het alles-in-een image is
  conformiteitspunt C1.3-MH-03 (moment P3; nieuw `deploy/allinone/*`). De map `<WERKMAP>/my_house/deploy` bestond op
  2026-11-11 nog niet.
- **Wat wel kan:** al het andere werk aan my_house.
- **Opgeheven door:** de bouwstap voor C1.3-MH-03 in P3.
- **Controle:** `ls <WERKMAP>/my_house/deploy/allinone`
- **Bron:** [CONF] punt C1.3-MH-03; [EVIDENCE my_house] rij B06-009.

#### BLOK-14 — Twee ADR's die eerst geschreven moeten worden

- **Wat zit vast:** (1) een MediaGuard-update via de Hub of de executor; (2) de bouw van de sleutelrotatie.
- **Waardoor:** (1) "hoe de Hub het bewijs ziet, legt een ADR in P3 vast; tot dan voert de Hub geen MediaGuard-update
  uit" (RV2). (2) Bij sleutelrotatie tellen de geplakte sleutelsets in my_house en de Jelly Leon-plugin mee; hoe de Hub
  dat weet, legt een ADR vast voor de rotatie gebouwd wordt (RV8).
- **Wat wel kan:** al het andere P2- en P3-werk.
- **Opgeheven door:** twee ADR-stappen in ai-server-manager (A-ONTWERP of A-BOUW, met R-VEILIG en R-HARDE-EIS). Of ze
  er al zijn: `ls <WERKMAP>/ai-server-manager/docs/adr/` (op 2026-11-11 was ADR-0030 het hoogste nummer; een ADR met
  dit onderwerp is niet gezien).
- **Bron:** ai-server-manager `docs/adr/ADR-0028-review-contract-1-3.md` (RV2, RV8); [CONTRACT] kop "2.3 Bestaande
  apps (MediaGuard, MSO, my_house, Jellyfin/Jelly Leon, Emby)" regel 7 en kop "4.5 Sleutelpinning, vingerafdruk en
  rotatie".

#### BLOK-15 — Inventaris van bestaande apps voor appstore-en-fork

- **Wat zit vast:** B08-002 en de APP-rijen die een inventaris van de echte NAS vragen (onder andere APP-02).
- **Waardoor:** de Hub geeft `GET /api/v1/apps` en `GET /api/v1/apps/{id}` alleen aan gebruikerssessies; een dienst
  krijgt 403 en meldt dan `capability_unavailable`. Daarnaast moet de inventaris van de echte NAS komen.
- **Wat wel kan:** de simulator-inventaris.
- **Opgeheven door:** een bouwstap in ai-server-manager die de twee leesroutes voor de dienst openstelt (eigenaar
  ai-server-manager; contractregels volgen); daarna BLOK-01.
- **Bron:** [EVIDENCE appstore-en-fork] rijen B08-002 en APP-02.

#### BLOK-16 — Gedrag van TrueNAS Custom Apps is niet gemeten

- **Wat zit vast:** zekerheid over onder meer: of het formulier een tag met digest accepteert, of TrueNAS daarmee
  updates herkent, en welke versie van TrueNAS en van het Custom App-sjabloon op de NAS staat.
- **Waardoor:** alles in die contractparagraaf is gelezen in broncode en documentatie, niet gemeten op een echte NAS.
- **Wat wel kan:** bouwen volgens de regels van die paragraaf; ze zijn zo gekozen dat ze ook gelden als de NAS zich
  anders gedraagt. Na elke installatie leest de executor de digest terug.
- **Opgeheven door:** T-04 (D01) en T-06.
- **Bron:** [CONTRACT] kop "2.2 Custom App-realiteit (gemeten in de bronnen, niet op een echte NAS)".

#### BLOK-17 — SSO met Authentik (B13-002)

- **Wat zit vast:** B13-002 en aanmelden via SSO.
- **Waardoor:** de echte Authentik (catalogusapp, I09) en een domeinnaam met HTTPS (D17) ontbreken; toepassen vraagt
  een door de Hub ondertekend uitvoerverzoek (fase P2); de aanmelding zelf hoort in de Hub.
- **Wat wel kan:** B13-001 (staat op "Bezig") en alles in de simulator.
- **Opgeheven door:** P2 (executor), T-16, installatie van Authentik op de NAS (T-06).
- **Bron:** [EVIDENCE home-control-hub] rij B13-002.

#### BLOK-18 — Batchmodules van Jelly Leon staan op de NAS uit

- **Wat zit vast:** de batchmodules (ondertitels, kwaliteit, segmenten) aanzetten op de NAS.
- **Waardoor:** de gate "Eén plugin met modules + belastingtest binnen de manifestresources" is voorwaarde "Voor
  B03-batch op de NAS"; de belastingtest (B03-018, JLT-66) heeft nog geen bewijs en BG-07 is open.
- **Wat wel kan:** de modules bouwen en in de simulator testen, strikt na elkaar binnen 4 CPU's en 4 GiB.
- **Opgeheven door:** JLT-66, daarna BG-07.
- **Bron:** [GATES] kop "Gate matrix"; [BG] kop "BG-07 — Resources van de jelly-leon-app".

#### BLOK-19 — Het werk staat niet in `main`

- **Wat zit vast:** (1) in ai-server-manager, home-control-hub, appstore-en-fork, jelly-leon-platform en
  zoeken-en-persoonlijke-ai is `main` de standaardbranch en staat al het werk op de werkbranch. (2) De release van
  my_house start op een push naar `main` (pad `VERSION`) of handmatig. (3) Geplande workflows draaien alleen vanaf de
  standaardbranch.
- **Waardoor:** vaste regel: geen PR's en geen samenvoeging zonder de gebruiker te vragen.
- **Wat wel kan:** bouwen, committen en pushen op de werkbranch; CI op de werkbranch volgen.
- **Opgeheven door:** Z-06 en T-13.
- **Controle:** `gh api repos/<eigenaar>/<repo> --jq .default_branch`
- **Bron:** eigen meting op 2026-11-11 met het commando hierboven; `<WERKMAP>/my_house/.github/workflows/release.yml`;
  [CONTRACT] kop "12. Commit- en pushregels".

#### BLOK-20 — De Hub-gates staan dicht

- **Wat zit vast:** uitrol, back-upgate, data-mutaties, updates van bestaande apps, upgrades, GPU-transcode, AI met
  cloudtools, DNS-omschakeling, aansturing van Gree en Zigbee, de overstap van mediaserver, Authentik, Navidrome en
  R2/R3-acties. Welke gate welk gegeven vraagt staat in deel 2.12.
- **Waardoor:** de gates vragen gegevens D01...D18 met status "Ingevuld" of "Getest". Zeventien daarvan staan open.
  De status "Getest" vraagt de echte omgeving. Daarbovenop: B12-001 (herstelproef uit OneDrive) is "Geblokkeerd", en
  zonder geverifieerd herstelpunt binnen het RPO weigert de policy met `BLK-CHECKPOINT`.
- **Wat wel kan:** de gates en de wizard bouwen en testen met simulatorwaarden. Voorbeeldwaarden worden nooit als echte
  waarden opgeslagen.
- **Opgeheven door:** T-04, T-05, T-11.
- **Bron:** `<WERKMAP>/ai-server-manager/apps/api/src/hub/onboarding/gates.py`;
  `<WERKMAP>/ai-server-manager/policy/blokkades.yaml`; [EVIDENCE ai-server-manager] rij B12-001.

### 4.2 De gatematrix naast de blokkades

De programmagates staan in [GATES] kop "Gate matrix". Deze tabel zegt per gate wat hem nu tegenhoudt. De gate zelf
wordt alleen door A-GATE beoordeeld. Welk onderdeel van het NAS-draaiboek bij welke gate hoort staat in
`<WERKMAP>/.lokaal/plan/uit/STAPPEN_P6.md`, kop "2.2 Gates tijdens de fase (start van elk onderdeel van DEEL B)".

| Gate (tekst uit de bron) | Verplicht voor | Nu tegengehouden door |
|---|---|---|
| NAS versie/pool bekend | altijd | BLOK-01; T-04 (D01, D06), T-05 |
| OneDrive foto en DB restore getest | mutaties aan bestaande data en upgrades | BLOK-03, BLOK-20; T-11 |
| ZFS snapshots en pre-change database-export | schema- en infrastructuurwijzigingen | BLOK-01 |
| Risk policy + privileged executor tested | autonome writes | bouwwerk van P2; op de NAS: BLOK-01 |
| MediaGuard/MSO API contract live verified | downloadgerelateerde acties | BLOK-01; T-12 |
| my_house fysieke apparaten gevalideerd | climate actuation | BLOK-02, BLOK-13; T-15 |
| Jellyfin client/GPU testmatrix geslaagd | universele mediaserver cutover | BLOK-01, BLOK-02; T-04 (D08, D15) |
| Vóór/na-rapport per gebruiker + uitdrukkelijk akkoord op elk verschil | elke cutover | BLOK-11; T-07 |
| Controlelijst "Emby verwijderen" | Emby uit (de gebruiker beslist en voert uit) | BLOK-11; Z-14, T-10 |
| Eén plugin met modules + belastingtest binnen de manifestresources | B03-batch op de NAS | BLOK-18 |
| Hub-sleutelpin in Jelly Leon (JL4) | Hub-kaarten van B03 | BLOK-07 |
| Δ-CONTRACT-MG | herstel/zoeken in MediaGuard via de Hub | BLOK-08 |
| DNS rollback route getest | routerwijzigingen | BLOK-01; T-04 (D11) |
| 0 paid API overage en monitor | AI in productie | D09 (AI-API-budget); AI blijft standaard uit |

Niet in deze tabel: de twee gates "Voor P4 (B03-functies)" (de koppeling van MediaGuard per server met de
proefmigratie naar 12.x, en de Emby-overname JLT-70...JLT-73 in de simulator). Dat is bouwwerk van golf 0 en P4-0; de
stand staat in [EVIDENCE jelly-leon] en [EVIDENCE media-guard-ultimate]. ONBEKEND of beide op 2026-11-11 gehaald
zijn - eerst vaststellen met:
`grep -n -E 'JLT-7[0-3]|MG-AUTH|MG-DUAL' <WERKMAP>/jelly-leon/docs/platform-v2/EVIDENCE.json`.

---

## 5. Tegenstrijdigheden in de bronnen

Gevonden bij het controleren. Een subagent lost geen tegenstrijdigheid zelf op: hij volgt de kolom "Wat geldt" en
meldt het nummer. Het bijwerken van een bron is een bouwstap in de repo die eigenaar is.

| Nr | Wat botst | Wat geldt | Wie werkt de bron bij |
|---|---|---|---|
| 5-1 | [BG] toont BG-04 op drie plekken nog als open (kop "2. Open besluiten — wanneer ze gevraagd worden", de regel "Open: 32 besluiten", en de tabel onder kop "Overzicht"), terwijl de slotkop "Besluiten van de gebruiker na contract 1.3 (2026-11-10)" het als genomen meldt: via de Hub. | Genomen; er staan 31 BG-besluiten open. Een genomen besluit gaat voor het advies. | documentatiestap in ai-server-manager |
| 5-2 | [CONTRACT] kop "1.2 Open besluiten (tot het besluit geldt de veiligste stand)" noemt nog als open: BG-04, het adresbereik voor de noodlogin en de bevestiging van de app-ID's. [STATUS] slotkop meldt alle drie als genomen op 2026-11-10. | [STATUS]. Het contract loopt achter. | contractstap in ai-server-manager, daarna de kopieen in alle repos byte-gelijk maken |
| 5-3 | BG-04 is genomen als "via de Hub", maar teksten van voor het besluit gaan uit van een sleutel in Jelly Leon zelf: [CONF] punten C1.3-JL-08 en C1.3-MGU-05, en volgens `STAPPEN_P4_GOLF3_4.md` (alinea "Spanning BG-04") ook de werkpakketteksten B03-043, B03-056 en B03-064. | Het besluit. Geen stap voegt een sleutelveld voor MediaGuard toe aan een beheerpagina; blijkt het zonder sleuteloverdracht niet haalbaar, dan deel 2.13. | documentatiestap in ai-server-manager; code: eerst A-VERKEN op B03-009 |
| 5-4 | BG-03 hoort "vóór golf 1" en BG-22 bij "P4-0 (overname)", maar beide staan open terwijl dat werk al gebouwd wordt. BG-03 is gebouwd volgens de regel "zonder besluit". | Nu voorleggen (deel 2.1). | regisseur |
| 5-5 | [BG] zegt: tot een besluit geldt de veiligste stand, "nooit automatisch het advies". Een uitgeschreven stand zonder besluit staat er alleen bij BG-01, BG-02, BG-03, BG-09 en BG-21 (regel "Zonder besluit"), en in de regel "Advies" bij BG-05 ("Tot dan geldt (b)"), BG-07 ("tot dan (b)") en BG-26 ("Zonder keuze speelt een officiële app precies zoals standaard Jellyfin"). `STAPPEN_P4_GOLF3_4.md` (kop "3. Besluiten die eerst genomen moeten zijn") vult de kolom "Zonder besluit" bij andere besluiten met de tekst van het advies, bijvoorbeeld BG-11 ("huishouden") en BG-13 ("na 10 s doorgaan"); bij BG-33 staat er een ruimere stand ("beheerders en aangewezen volwassenen") dan in `STAPPEN_P4_GOLF1_2.md` ("alleen beheerders"). Dit bestand zegt daar "niet uitgeschreven in de bron" en laat de stap stoppen of de minst ingrijpende stand kiezen. | Regel 0.2-4 van dit bestand, tot het hoofdplan anders beslist. De eenvoudigste oplossing: de besluiten van een golf voorleggen voor de golf start, dan speelt het niet. | hoofdplan |
| 5-6 | Vaste regel: geen modelnaam in commits en geen force-push. In de commits tot en met 2026-11-10 staat een attributieregel met een modelnaam; dat is alleen met een force-push te herstellen. [CONTRACT] kop "12. Commit- en pushregels" spreekt bovendien van "de attributieregel(s) die de lopende sessie voorschrijft". | Historie blijft staan; nieuwe commits volgen de vaste regel (Z-04). | gebruiker beslist |
| 5-7 | [CONTRACT] kop "12. Commit- en pushregels": al het werk op de werkbranch, geen PR's. In vijf repos is `main` de standaardbranch; die bevat het werk niet. De release van my_house start op een push naar `main`. | Werkbranch; niets samenvoegen zonder de gebruiker (Z-06, BLOK-19). | gebruiker beslist |
| 5-8 | [RUW] noemt onder de koppen "media-guard-ultimate" en "media-source-optimizer" andere standaardbranches dan nu gemeten. Op 2026-11-11 is in beide repos de werkbranch de standaardbranch. | De meting. Opnieuw meten: `gh api repos/<eigenaar>/<repo> --jq .default_branch`. | geen (agentrapporten zijn momentopnamen) |
| 5-9 | `<WERKMAP>/.lokaal/plan/bron/STAND_PER_ID.tsv` meldt B03-017 als "GEEN BEWIJS (Niet gestart)", terwijl in jelly-leon op 2026-11-11 een commit met dat ID staat (`8a293727d`). In [EVIDENCE jelly-leon] stond op dat moment nog geen rij B03-017. | De stand in de repo. `STAND_PER_ID.tsv` is een momentopname; A-VERKEN meet opnieuw voor elke stap. | de bouwer van B03-017 (bewijsregel toevoegen) |
| 5-10 | Vaste regel "nooit Geslaagd" naast de waarde `Sim-geslaagd` in EVIDENCE (op 2026-11-11 24 keer in het veld `validatie`; geen enkele `status` "Gereed" of "Geslaagd"). | Geen echte tegenstrijdigheid: `Sim-geslaagd` is een toegestane waarde van het veld `validatie` voor testrijen; het veld `status` blijft "Bezig" of "Geblokkeerd". Een reviewer keurt `Sim-geslaagd` dus niet af, wel elke `status` "Gereed" of "Geslaagd". | geen |
| 5-11 | De ADR's over contract 1.3 leggen K1 en RV2 vast zonder voorbehoud. Dat de gebruiker K1 nog moet bevestigen en RV2 kan versoepelen staat alleen in de agentrapporten ([RUW] kop "ai-server-manager"). | Zoals gebouwd, tot de gebruiker anders beslist (Z-02, Z-03). | regisseur legt voor |

Bronnen bij 5-10: [CONTRACT] kop "11. Bewijs en Excel (EVIDENCE.json)".

---

## 6. Wat niet vast te stellen was

Elk punt is ONBEKEND tot het met het genoemde commando is vastgesteld. Alle commando's lezen alleen.

| Nr | Wat is onbekend | Eerst vaststellen met |
|---|---|---|
| 6-1 | Of de GHCR-pakketten van MediaGuard aan de nieuwe repo gekoppeld en publiek zijn. Het token van de bouwomgeving mag pakketten niet lezen. | de gebruiker bevestigt het zelf (T-01); zonder aanmelding lezen kan met de controle bij T-02 |
| 6-2 | Of de repo-geheimen (sync, Android-ondertekening) op GitHub zijn ingesteld. | `gh secret list --repo <eigenaar>/<repo>` (toont alleen namen) |
| 6-3 | Waarom de geplande upstream-sync op 2026-11-11 nog geen run had. | `gh run list --repo <eigenaar>/jelly-leon --workflow upstream-sync.yml` en `gh workflow list --repo <eigenaar>/jelly-leon --all` |
| 6-4 | Wat er functioneel breekt als `/_shc/config.json` van my_house wordt afgeschermd (Z-08). | `grep -rn '_shc/config' <WERKMAP>/my_house --include=*.ts --include=*.tsx --include=*.kt` (zelfde commando als bij Z-08; op 2026-11-11 gaf het alleen treffers in `apps/web/src/hub.ts` en twee testbestanden) |
| 6-5 | Welke methoden voor OneDrive het bouwplan als opties noemt (D04). | `grep -n -i 'onedrive' <WERKMAP>/ai-server-manager/docs/platform-v2/02_BOUWPLANNEN/B12_*.md` |
| 6-6 | De veiligste stand bij de 22 besluiten waar in deel 2 "niet uitgeschreven in de bron" staat. Wat daar staat is afgeleid door dit plan en door geen bron bevestigd. | de gebruiker beslist (het besluit zelf voorleggen) |
| 6-7 | Of de stap-ID's uit de andere planbestanden nog kloppen. Die bestanden werden op 2026-11-11 nog geschreven: `STAPPEN_P3.md` en `STAPPEN_P4_GOLF1_2.md` waren in opbouw (in het tweede stonden nog geen stappen, alleen de besluitentabel), en van DEEL B van `STAPPEN_P6.md` stond alleen de gatetabel. | `ls <WERKMAP>/.lokaal/plan/uit/` en `grep -n -E '^#{2,3} S-' <WERKMAP>/.lokaal/plan/uit/STAPPEN_*.md` |
| 6-8 | Of ronde 3 intussen punten uit dit bestand heeft opgelost (bijvoorbeeld het alles-in-een image van my_house, de ADR's van BLOK-14, de leesroutes van BLOK-15). | per punt het commando bij "Controle"; anders `git -C <WERKMAP>/<repo> log --oneline -20` |
| 6-9 | Of de twee gates "Voor P4 (B03-functies)" gehaald zijn. | zie het slot van deel 4.2 |
| 6-10 | Of een besluit na 2026-11-10 is genomen buiten de twee statusbronnen om. | de twee commando's in deel 0.3; bij twijfel vraagt de regisseur het de gebruiker |
| 6-11 | Hoe de koppeling van een GHCR-pakket aan een repo precies gaat. Staat in geen bron. | geen commando; de gebruiker doet dit in de pakketinstellingen op GitHub |
