# ADR-0033 — OIDC-clientgeheim van Authentik naar de kluis van de Hub

Status: ontwerp ter review · 2026-11-18 · S-P2-070, uitsluitend bouwpunt 4 · niveau N4.
Basis: `ai-server-manager@d38dac7ffc21a49c9b03fcca005f92d22e54bfdf`;
gelezen `home-control-hub@7defe7301153b0c1e743f92b98dd885b52c75855`.
Contract: `contracts 1.3` met aanvulling C-12, [ADR-0031](ADR-0031-contract-1-3-aanvulling-c12.md).
Dit is een ontwerp met toekomstige acceptatietests, geen gebouwde overdracht of nieuwe bevoegdheid.
Automatische overdracht blijft dicht tot de open contractmeldingen, beide implementaties en hun bewijstests
zijn afgerond. De bestaande tijdelijke handmatige contractweg krijgt hierdoor geen onbewezen veiligheidsgarantie.
Ook die tussenweg mag pas worden gebruikt nadat haar bestaande afwijkingen hieronder zijn hersteld en getoetst.
Geen code-, policy-, contract- of EVIDENCE-wijziging; geen validatie op een echte NAS of met echte accounts.

## Verkenning en bronnen

De graphify-query is vóór het gerichte bronlezen uitgevoerd. Op origin is ADR-0032 het hoogste nummer;
0033 was vrij. Voor 070 bestaat geen verkennersdossier. Het dossier en rapport van S-P2-330 noemen precies
de ontbrekende overdrachtsbeslissing en de noodzakelijke bescherming van lokale noodtoegang als blokkades.
Sinds dat dossier veranderde home-control-hub in `7defe73` de CI-validatorpin en de bijbehorende
changelog-, ADR- en evidenceaantekeningen; de gelezen SSO-code veranderde niet.

- [Contract](../platform-v2/PLATFORM_CONTRACTEN.md), §1/§1.1/§1.2, §3.1–§3.4, §3.10, §4.1–§4.7,
  §5, §8 en §9; [conformiteit](../platform-v2/CONTRACT_1.3_CONFORMITEIT.md), C1.3-ASM-18 en C1.3-HCH-15.
  §3.1 onderscheidt (a) door de Hub gemaakte appgeheimen en (b) door een dienst voor de Hub gemaakte geheimen.
  Alleen (b) is hier aan de orde. Enrollment koppelt een dienst; het verstrekt geen OIDC-geheimbevoegdheid.
- [ADR-0030](ADR-0030-policy-engine-approvals-executor.md), besluiten 10, 17 en 28 en open punten;
  [ADR-0031](ADR-0031-contract-1-3-aanvulling-c12.md), besluiten 1, 3 en 9;
  [ADR-0032](ADR-0032-vertrouwde-appplannen-en-kluisdoorgifte.md), besluiten 2, 4 en 9 en melding M2;
  [ADR-0023](ADR-0023-oidc-sso-hub.md), bestaande OIDC- en sessiegrenzen.
- `apps/api/src/hub/vault.py`, `REF_RE`, `Vault.put` en `Vault.get`: tweeledige credentialrefs,
  AES-256-GCM met de ref als gekoppelde data, en metadata met laatste vier tekens. Geen revisie-/overdrachtsbinding.
  `apps/api/src/hub/redact.py`, `redact` en `redact_log_text`: redactie als extra afscherming, geen transportgrens.
- `apps/api/src/hub/oidc/service.py`, `SECRET_REF`, `config_dict`, `finish` en `revoke_sessions`:
  de Hub gebruikt nu `vault://auth/oidc-client-secret`; `revoke_sessions` selecteert standaard alleen OIDC-sessies.
  `apps/api/src/hub/routers/oidc.py`, `put_oidc` en `enable`: bestaand handmatig schrijfveld, configuratieversie
  en testlogin. `apps/api/src/hub/deps.py`, `_idempotency`: hasht pad plus de hele gecanoniseerde verzoekbody,
  ook het geheim. Dit is geen al gebouwde eenmalige overdracht volgens besluit 3.
- `apps/api/src/hub/routers/breakglass.py`, `_new_totp`: ook het bestaande nood-TOTP staat in `auth`, onder
  `vault://auth/break-glass-totp-<id>`, met dezelfde `Vault` en hoofdsleutel. `apps/api/src/hub/logsink.py`,
  `_MatcherCache.get`: ontsleutelt iedere kluisrij kortstondig voor redactievingerafdrukken in het geheugen;
  onleesbare rijen worden stil overgeslagen. `auth` is dus geen uitsluitend OIDC-ruimte.
- `apps/api/src/hub/oidc/client.py`, `exchange_code`: gebruikt het geheim bij het token-endpoint. De huidige
  verwerking neemt een foutveld van de provider op in een fouttekst; de nieuwe keten mag geen ruwe providerfout
  doorgeven. `apps/api/src/hub/errors.py`, `install_error_handlers`, is evenmin bewijs voor alle lekvrije foutpaden.
- `apps/api/src/hub/backup/selfbackup.py`, `run_self_backup` en `verify_dump`: database-export en controles,
  geen bewezen herstelset met `vault.key`. `apps/api/src/hub/routers/breakglass.py`, `login`, en
  `apps/api/src/hub/breakglass.py`, `is_private_source`: lokale noodroute en bronadrescontrole.
- In home-control-hub: `apps/api/src/integrations/domains/sso/oidc_hub.py`, `build_hub_oidc_plan`:
  confidential provider, Authentik maakt volgens het ontwerp het geheim; er is geen uitvoerende registratie.
  `sso/proposals.py`, `create_proposal` en `_plan_sessions`: voorstellen, nog geen apply; brede sessieselectie
  is geen bewijs dat lokale noodsessies behouden blijven. `sso/authentik/reader.py`, `clean_provider`, laat
  `client_secret` door een whitelist weg: ruwe provider-lees-/lijstantwoorden kunnen dat veld wel bevatten,
  zoals de nep-Authentik in `apps/api/tests/fakes/authentik_fake.py` expliciet doet. Dit is niet met een echte
  Authentik gemeten. `sso/kit.py`, `PROCEDURE_NL`, bevat geen geheimen; `sso/recovery.py`,
  `evaluate_access`, werkt zonder Authentik. Hun LAN/VPN- en optionele CGNAT-teksten verruimen het voor deze
  opdracht geldende gebruikersbesluit **noodlogin uitsluitend via LAN** niet.
- [Overdrachtstatus](../platform-v2/OVERDRACHT/STATUS.md), gebruikersbesluiten;
  [B03-besluiten](../platform-v2/02_BOUWPLANNEN/B03_BESLUITEN.md), genomen en open besluiten;
  [risicogrenzen](../platform-v2/01_ARCHITECTUUR/03_RISICO_AUTONOMIE.md), technische handhaving.
  `EXCEL_TAKEN.json`, B01-006: een viewer kan nooit geheimen exporteren; sessie-intrekking werkt direct.

### Bestaande afwijkingen: eerst afzonderlijk herstellen

De regisseur plant de volgende bestaande afwijkingen als eigen herstelstap in ai-server-manager; dit ADR
herstelt uitsluitend het ontwerp. Zij zijn geen bewijs dat de tijdelijke contractweg veilig is. De eerste
drie invoereisen vragen **geen contractwijziging en wachten niet op O2**:

| Bestaande bron en afwijking | Vereist vóór gebruik van de tussenweg | Bewijs bij de bouw |
|---|---|---|
| `routers/oidc.py::put_oidc` accepteert geheime invoer over HTTP; `ToegangScreen.tsx::Sso` vraagt met `autoComplete="new-password"` om opslaan/genereren; `deps.py::Admin` toetst geen sessiebron. | Server weigert schrijven én wissen over HTTP vóór opslag; UI biedt daar geen geheimveld. Alleen een levende lokale sessie met de hoogste rol `admin` mag schrijven/wissen, ook niet een OIDC-`admin`. Het veld vraagt niet om opslaan/genereren en gebruikt de beschikbare uitsluitingen voor wachtwoordmanagers; geen eigen browseropslag of formulierherstel. | T2: HTTP → 4xx en nul kluiswijzigingen; OIDC-`admin` → 403, lokale `admin` via HTTPS positief; browser-/veldcontrole. |
| `deps.py::_session_principal` toetst SSO-stand en configuratie niet; `routers/oidc.py::oidc_login` zet automatisch uit zonder intrekking; `put_oidc`/`enable` trekken alleen bij eerder ingeschakelde SSO in. Een oude `web_session`-back-up laat intrekking herleven. | Sessiecontrole en herstelbestendige intrekkingsgrens volgens besluiten 4/5, ook als SSO al uit stond; lokale/noodsessies blijven buiten de selectie. | T4/T5: oude OIDC-cookie geeft 401 na uitzetten/vervangen/intrekken en na herstel, ook na opnieuw inschakelen. |
| `oidc/service.py::finish` geeft zonder ref `None` aan `oidc/client.py::exchange_code`; die kiest dan een publieke client. `put_oidc` wist alleen de ref; `enable` eist geen actieve geheime revisie. | Ontbrekend, gewist of ingetrokken geheim sluit testlogin, callback en inschakelen vóór een tokenaanroep; oude ciphertext blijft geblokkeerd of wordt verwijderd. | T5: wissen en opnieuw proberen geeft een vaste fout, nul tokenaanroepen zonder geheim en geen hergebruik van de oude rij. |
| `deps.py::_idempotency` bewaart een hash van pad plus body met geheim; `oidc/service.py::config_dict` levert laatste vier tekens ook aan opgeslagen antwoorden. | Geen geheime invoer of afgeleide vorm in idempotentieopslag, ook geen hash of laatste vier in `response_body`. De nieuwe eenmalige claim blijft dicht tot O2; geen ongeautoriseerde uitzondering op §5. | T3/T7: structurele opslagcontrole, raadorakelcontrole en controles van discover-/inschakelantwoorden. |
| `routers/breakglass.py::put_cgnat` laat een SSO-beheerder de noodlogin verruimen zonder eigen herbevestiging. | Eigen herstelstap van de noodlogineigenaar; valt buiten dit OIDC-ontwerp. Het ontwerp mag niet op die verruiming steunen of haar activeren. O3 blijft open tegenover het gebruikersbesluit alleen LAN. | T5 bewijst dat alle OIDC-stappen de bestaande netwerksetting ongewijzigd laten; dit bewijst geen herstel van deze beheerroute. |

Zolang deze toepasselijke herstelvoorwaarden niet zijn bewezen, geeft de tussenweg geen vrijgave voor geheime
invoer. App-attributen kunnen browser-/wachtwoordmanagersynchronisatie niet afdwingen; dat restrisico blijft
uitdrukkelijk staan en wordt niet met een Playwright-profiel zonder wachtwoordmanager als opgelost aangemerkt.

## Genummerde besluiten

### 1. Authentik maakt het geheim; home-control-hub beheert alleen de gebonden registratie

**Keuze.** Het `client_secret` ontstaat in Authentik bij het maken of expliciet roteren van precies de
confidential OIDC-provider van de Hub. De Hub, planner, AI en beheerder verzinnen daarvoor geen waarde.
home-control-hub laat Authentik genereren en verwerkt een eventueel geheimhoudend aanmaakantwoord uitsluitend
in de afgeschermde uitvoeradapter. Ook ruwe provider-GET-/lijstantwoorden kunnen het geheim bevatten:
readback, status en detectie gaan verplicht door de whitelist van `clean_provider`, zonder ruwe antwoordlogging,
ook in de toekomstige uitvoeradapter. De alleen-lezen reader krijgt geen bevoegdheid tot geheime afgifte.
Het Authentik-beheercredential waarmee de dienst uitvoert is een ander geheim en wordt nooit mee overgedragen.

Die adapter in home-control-hub (S-P2-330) controleert vóór ophalen of schrijven de eerste verbinding,
**Authentik → home-control-hub**: verplicht HTTPS met geverifieerde certificaatketen en servernaam én binding
aan de vooraf bevestigde Authentik-instantie en provider/client. Geen HTTP-terugval, redirect of omwisseling
naar een ander Authentik-doel; de huidige generieke clientfactory is daarvoor onvoldoende. Ongeldig schema
of doel wordt geweigerd vóór het beheercredential wordt opgehaald; bij een ongeldig certificaat faalt de
TLS-handshake vóór een HTTP-verzoek, een geheimhoudend leesantwoord of een upstreamschrijfactie.

Een registratie via `sso.oidc.hub.register` blijft R2, met menselijke goedkeuring van de precieze niet-geheime
diff en een ondertekend `ExecutionRequest`. De dienst controleert zelf opnieuw handtekening, gepinde sleutel,
geldigheid, nonce, allowlist, schema, policy-hash, eigen risicoklasse, doel en precondities. Een geldig
dienst-JWT, een rolclaim of een AI-voorstel vervangt die controles niet. Het geheim staat ook niet in de
handtekeninginvoer of in een hash van de uitvoerparameters. Inrichten van de Hub-OIDC-instellingen blijft
beheerdersbediening volgens ADR-0023, geen algemene AI-actie of nieuwe action_id.

De beoogde herkomst is vastgesteld uit de huidige planbron, niet op een echte Authentik gemeten.
Vóór bouwen moet de gepinde Authentik-versie aantonen dat weglaten van `client_secret` veilig laat genereren
en hoe intrekking/rotatie werkt. Geen ondersteund generator-/versiebewijs betekent `capability_unavailable`.
De adapter controleert het aanmaakantwoord vóór verdere verwerking; geen onbeperkte tekst, stuurtekens of
stil afkappen. De precieze generatorvorm wordt gepind bij de bouw, met voldoende willekeur (minstens 256 bit).
Het patroon van een door de Hub gemaakt appgeheim of een enrollment-token wordt hier niet op toegepast.

**Alternatieven en reden.** Een door de Hub gegenereerd geheim terugschrijven naar Authentik is verworpen:
dat wisselt de eigenaar en maakt van §3.1(b) ten onrechte §3.1(a). Een geheim in een manifest, accountveld,
omgevingsvariabele of gewone parameter valt niet onder C-12; C-12 is geen automatische accountvoorziening.

**Bewijstest T1.** De echte registratieadapter, aangestuurd door de echte dienstverificatie en een
nagebootste Authentik, maakt precies één goedgekeurde provider. De aanmaakbody bevat geen clientgeheim;
het willekeurige antwoordgeheim bereikt alleen het toegelaten invoerpad van besluit 2. Ongetekend, verlopen,
andere client, gewijzigde diff en onondersteunde Authentik-versie geven nul schrijf- en overdrachtsaanroepen.
Voor juist de eerste verbinding geven HTTP, een ongeldig certificaat en een verkeerd Authentik-doel elk
weigering vóór ophalen/schrijven: nul geheime HTTP-aanvragen/-antwoorden, nul providerwijzigingen en nul
Hub-kluisschrijvingen. De geldige HTTPS-/doelvariant bewijst positief ontvangst; T2 herhaalt deze grens in de keten.
**Mutatie M-T1.** Laat de adapter een clientgeheim uit parameters nemen of sla één verificatie over:
de betreffende positieve herkomstcontrole of negatieve autorisatietest moet rood worden.
Schakel afzonderlijk HTTPS-, certificaat-/servernaam- of Authentik-doelcontrole op de eerste verbinding uit:
de overeenkomstige negatieve proef moet rood worden, zonder een echt account te benaderen.

### 2. Alleen een afzonderlijke geheime verbinding; tijdelijk handmatig via twee UI's

**Keuze.** De automatische richting is **Authentik → home-control-hub → Hub-kluis**. De eerste pijl voldoet
verplicht aan de HTTPS-, server- en doelbinding uit besluit 1, ook voor ruwe leesantwoorden. De tweede pijl gebruikt
een afzonderlijke inkomende overdrachtsverbinding met TLS 1.3, wederzijdse certificaatcontrole en vooraf door
een beheerder via de UI bevestigde transportpinnen. Alleen de ingeschreven instantie van home-control-hub
mag naar de bedoelde Hub-instantie leveren. De certificaatidentiteit is aan haar registratie gebonden;
een service-token, enrollment-token of policy-handtekening alleen geeft geen toegang. Geen TOFU, redirects,
proxy-omgevingsvariabelen, HTTP-terugval, TLS-early-data of doorgifte door de gewone connector-/webproxy.
Elke partij maakt haar eigen transportsleutel lokaal; alleen publieke certificaten/pinnen worden bevestigd.
Ontkoppelen, intrekken en een pinwijziging sluiten oude overdrachten; een nieuwe pin vraagt eigen bevestiging.
Dit vereist eerst contractmelding O1; er is nog geen route, scope of werkende transportkoppeling voor.

Dit kanaal is **geen derde type op het ophaalkanaal van ADR-0032**. Dat kanaal gaat van Hub naar executor,
voor precies appgeheim en enrollment-token, met eigen vormcontrole. Het OIDC-geheim is een inkomend credential
voor de Hub zelf en wordt nooit aan de executor aangeboden. Alleen de OIDC-client in de Hub mag het daarna
intern uit de kluis gebruiken voor authenticatie bij het gebonden Authentik-token-endpoint over HTTPS.
De eigen issuer-/endpointcontrole, PKCE, asymmetrische tokens en redirectweigering van ADR-0023 blijven gelden.

Uitdrukkelijk verboden, ook als versleutelde blob, base64 of kluisref bedoeld voor latere ontsluiting:
Hub-connector (`propose`, `apply`, `rollback`, items, logs), events/inbox/outbox, gewone dienst-leesroutes,
enrollment-/rotatieantwoorden, manifesten en TrueNAS-`values`. Nooit de waarde in preview, diff, goedkeuring,
audit, verzoekhash, idempotentieopslag, journaal, terugzetrecept, foutmelding, log, AI-context, supportbundel,
schermafdruk, trace, testartefact of EVIDENCE. Een connectorverzoek dat het geheim probeert aan te leveren
wordt geweigerd, zonder opslag, doorsturen of ontsluiting. Redactie achteraf vervangt deze grens niet.

**Tijdelijke handmatige bediening, zonder terminal.** Zolang automatische overdracht niet gezamenlijk is
vrijgegeven, blijft contract §3.1(b) de enige toegelaten overdrachtsweg:

1. De beheerder opent zelf de Authentik-beheer-UI over HTTPS en controleert de bedoelde instantie,
   provider/applicatie, `client_id` en strikte redirect-URI van de Hub. Bij twijfel niets kopiëren of wijzigen.
2. In de Hub opent de beheerder **Instellingen → Toegang → Inloggen via SSO**, controleert dezelfde issuer, client en
   callback en kiest het alleen-schrijvenveld voor het clientgeheim. Dit is functionele bediening; het
   bestaande scherm staat in `apps/web/src/app/instellingen/toegang/ToegangScreen.tsx`.
3. De beheerder kopieert de door Authentik gemaakte waarde rechtstreeks uit die UI en plakt haar één keer
   in het afgeschermde veld van de Hub; alleen over een vertrouwde HTTPS-verbinding. Geen tussenbestand,
   chat, e-mail, terminal, URL, browseropslag of schermafdruk. Het klembord en het bronvenster kunnen de
   waarde tijdelijk bevatten: geen claim van wissen op het besturingssysteem of synchronisatiebeheer.
   De beheerder ruimt het klembord zelf op; de Hub mag het nooit automatisch terug vullen.
4. Opslaan bewaart versleuteld en toont alleen ingesteld, datum en hooguit laatste vier tekens (§3.10).
   Daarna doet de beheerder discovery, een testlogin met de actuele configuratie en pas dan inschakelen.
   Bij fout blijft SSO uit. De UI toont nooit een knop om de opgeslagen volledige waarde te bekijken/exporteren.

De bestaande route `PUT /api/v1/auth/oidc` ondersteunt handmatige invoer, maar de bestaande afwijkingen
hierboven moeten vóór elk gebruik van de tussenweg zijn hersteld en getoetst. HTTPS-weigering, lokaal-`admin`-
controle en browserveldbeveiliging zijn zelfstandig bouwwerk, geen onderdeel van O2. De server bepaalt HTTPS
uit de daadwerkelijke verbinding of uitsluitend een expliciet vertrouwde TLS-proxy; een zelf aangeleverde
schemaheader geeft geen toegang. Schrijven én wissen vragen `auth_bron=lokaal` en rol `admin`; een lokale
noodsessie mag dit binnen haar eigen geldigheidsduur. OIDC-beheerders worden geweigerd.
Het veld gebruikt geen `new-password`, vraagt geen opslag/generatie en sluit wachtwoordmanagers uit voor zover
de app dat kan sturen; de app bewaart niets in localStorage, sessionStorage, serviceworkercache of formulierherstel.
Na verzending, fout of verlaten wordt de invoer leeggemaakt. Het resterende externe browserrisico blijft vermeld.
De nieuwe gebonden eenmalige invoer uit besluit 3 blijft dicht tot O2 en haar bouw-/UI-review. Bestaande code
wordt niet als conform aangemerkt. Zonder bewezen veilige invoer geen onversleutelde noodomweg.
Publicatie van dit ADR beëindigt handmatig kopiëren niet. Dat gebeurt voor een instantie pas na de
contractronde, beide gepinde implementaties, gezamenlijke positieve/negatieve proeven, de transportkoppeling
en een door de beheerder bevestigde testlogin. Tot dan geen automatische claim dat overdracht voltooid is.
Na omschakeling geen automatische handmatige terugval; herstel vraagt een nieuwe, expliciete gebonden
beheerdershandeling. De precieze herstelbediening hoort bij O1/O2 en blijft tot vastlegging dicht.

**Alternatieven en reden.** Connectortransport blijft verboden, ongeacht encryptie. Een gedeelde kluis,
generieke `get_secret`, NAS-configuratie teruglezen of een bestand downloaden/uploaden vergroot de bevoegdheid
en opslag van geheimen. Automatisch een nieuwe geheime route bouwen zonder contract is eveneens verworpen.

**Bewijstest T2.** Na de contractronde: echte Hub en echte home-control-hub op gepinde commits, alleen
Authentik nagebootst. Controleer automatische levering over het gekozen transport en handmatige invoer
in een echte browser zonder gefingeerde herkomstheaders. Test verkeerd certificaat/pin, ingetrokken dienst,
HTTP, redirects en connectorlevering: weigering, nul kluisschrijvingen. Geen schermopname/video/trace zolang
het veld of de bron het geheim bevat. De bronnen die T7 doorzoekt zijn aantoonbaar gevuld.
Toets beide verbindingen afzonderlijk: op **Authentik → home-control-hub** moeten HTTP, onjuist certificaat
en verkeerd Authentik-doel vóór ophalen of schrijven weigeren, met dezelfde nultellingen als T1. Een veilige
tweede pijl compenseert geen onveilige eerste. Op de bestaande handmatige route: HTTP-PUT met schrijf-/wisveld
geeft 4xx, vervalste schemaheaders helpen niet, alle kluisrijen blijven gelijk; een OIDC-`admin` krijgt 403 en een
lokale `admin` via vertrouwde HTTPS slaagt. De UI verbergt het veld over HTTP, vraagt geen wachtwoordopslag en
laat na opslaan/fout/navigatie geen invoer in app-opslag of formulierherstel achter. Meet beschikbare
browser-/wachtwoordmanagersturing in isolatie; rapporteer onbeheersbaar gedrag eerlijk als restrisico.
**Mutatie M-T2.** Laat een connector-body doorsturen, accepteer alleen een service-token, schakel TLS-/pincontrole
uit of sla het veld op in browseropslag: elk maakt de betreffende negatieve proef rood.
Zet afzonderlijk de eerste-pijlcontroles voor HTTP, certificaat/servernaam en Authentik-doel uit, laat HTTP-PUT
of een OIDC-beheerder schrijven/wissen, of herstel `new-password`/app-formulieropslag: elk maakt zijn eigen proef rood.

### 3. Iedere overdracht is eenmalig en aan dienst, client, instantie en configuratie gebonden

**Keuze.** De Hub start een overdracht alleen vanuit een levende lokale beheerderssessie (eventueel de
lokale noodsessie), met CSRF-/herkomstcontrole en expliciete bevestiging van het niet-geheime doel.
Een SSO-sessie die door vervanging wordt ingetrokken is geen noodzakelijke voorwaarde voor voltooiing.
Een operator, viewer, kind, AI of dienst-token kan geen overdracht autoriseren.

De Hub legt vooraf een willekeurig overdrachts-ID en een onveranderlijke context vast: eigen Hub-identiteit,
de ingeschreven home-control-hub-`service_id` en transportpin, Authentik-instantie/issuer, provideridentiteit,
`client_id`, strikte redirect-URI, configuratieversie, verwachte huidige kluisrevisie, doel nieuwe registratie
of vervanging, bevestigende beheerder/sessie en vervaltijd. Bij automatische registratie hoort daar ook het
geverifieerde request-ID met approval/diff-binding bij. Het overdrachts-ID is geen bearercredential.
Een nieuwe overdracht vervangt nooit ongemerkt een nog geldige binding.

De overdracht vervalt na **maximaal vijf minuten**, eerder bij sessie-intrekking, verlopen goedkeuring,
gewijzigde registratie/configuratie, ontkoppeling of pin-/clientwissel. Verlengen of een ruimere klokspeling
kan haar niet geldig houden. Onbetrouwbare klok of onleesbare claimopslag betekent weigering.
Een atomaire claim laat hooguit één bevoegde leverancier toe; andere of extra contextvelden geven weigering
zonder kluiswijziging. Vóór ontsluiting worden bevoegdheid en binding opnieuw gecontroleerd.

De levering bevat alleen de vooraf vastgelegde context en precies één geheim van de gebonden provider;
geen door de leverancier gekozen kluisref, ander credential of uitvoercommando. Bij handmatige invoer is
dezelfde beheerder en browser gebonden. Dat bewijst wie invoert, niet cryptografisch dat de waarde uit
de juiste Authentik komt; pas de gebonden volledige testlogin controleert de bruikbaarheid voor die client.
Zonder bewijs blijft de status aangeleverd/ongetest en SSO uit. Een testlogin is geen bewijs van een echte
dienst zolang alleen de simulator is gebruikt.

De duurzame toestanden zijn aangevraagd, geclaimd, opgeslagen/ongetest, bevestigd, mislukt, vervallen of
onbekend. Claim en opslaan worden tegen concurrentie afgeschermd; ciphertext, revisiebinding en overgang
naar opgeslagen/ongetest worden atomair vastgelegd. Er is geen duurzame geheime wachtrij in home-control-hub
en geen caching van een afgifteantwoord. Het antwoord op levering bevat alleen vaste statusmetadata.
Na een commit mag een afzonderlijke statusopvraag bevestigen dát opgeslagen is; zij levert nooit de waarde.
Een tweede levering op hetzelfde ID wordt altijd geweigerd; geen tweede kluisschrijving.

Bij fout vóór claim kan alleen een nog geldige, niet geclaimde overdracht opnieuw worden aangeboden.
Na claim, timeout, herstart of een half antwoord nooit blind herhalen: eerst niet-geheime status lezen.
Een geclaimde overdracht zonder aantoonbare opslag wordt mislukt/onbekend en is onbruikbaar; nieuwe
beheerdersbevestiging en nieuw ID zijn nodig. Geen automatische tweede provider of rotatie om een verloren
antwoord te repareren. Als Authentik al schreef, wordt die deeluitkomst eerlijk gemeld en via readback van
uitsluitend niet-geheime identiteit vastgesteld; geen automatische verwijdering van mogelijk gebruikte clients.
Verdere geheime levering gebeurt daarna handmatig uit Authentik of via een nieuwe expliciete rotatie.
Uitval van overdracht wijzigt nooit het lokale noodaccount en meldt registratie niet als SSO voltooid.

De geheime invoer gebruikt geen generieke bodyhash/idempotentiecache: een hash van het geheim blijft ook
verboden, inclusief de hash van pad plus body die een geraden geheim offline bevestigbaar maakt. Geen enkele
opgeslagen idempotentierespons bevat laatste vier tekens; ook discover en inschakelen bewaren die metadata niet.
Eigen eenmaligheid is een **voorgestelde uitzondering** op contract §5, melding O2; geen zelfstandig
ingevoerde uitzondering. Niet-geheime voorbereidingsmutaties behouden de bestaande Idempotency-Key-regels.
Het exacte strikte schema, routepad, status-/foutcodes en herstelprotocol worden eerst gezamenlijk als O1/O2
vastgelegd; bestaande routes of scopes worden daarvoor niet hergebruikt of uitgebreid bij aanname.

**Alternatieven en reden.** De levensduur van een enrollment-token overnemen is verworpen: koppelen is een
andere bevoegdheid. Levering vrijgeven op alleen `app_id` of opnieuw leveren na een timeout mist de
instantie-/clientbinding en kan tweemaal schrijven. Alleen een verzoekhash geeft geen eenmalige overdracht.

**Bewijstest T3.** Echte claim-/opslagcode met gelijktijdige leveringen: precies één schrijft. Test andere
dienst, Hub, provider, issuer, client, redirect, sessie, revisie, configuratieversie en verstreken vijf minuten.
Test crash vóór claim, na claim, vóór/na opslagcommit en vóór antwoord; herstart levert nooit opnieuw.
Een onzekere registratie veroorzaakt nul tweede Authentik-aanmaakaanroepen; een statusopvraag blijft geheimvrij.
Na O2 heeft het geheime invoerpad structureel geen generieke `Idempotency`-afhankelijkheid en ontstaan voor
die invoer nul `idempotency_record`-rijen. Controleer daarnaast alle blijvende hash-/antwoordvelden: geen
waarde is uit pad plus bekende bodyvelden met de canary te herberekenen; een fout kandidaatgeheim mag geen
vergelijkbaar raadorakel opleveren. De niet-geheime idempotente routes blijven gevuld maar bewaren geen laatste vier.
**Mutatie M-T3.** Verwijder een contextvergelijking, de atomaire claim of de vervaltijdcontrole, zet automatische
herhaling aan of gebruik de generieke bodyhash: de betreffende negatieve proef moet rood worden.
Injecteer afzonderlijk een hash van pad plus geheime body of laatste vier in een opgeslagen antwoord:
de structurele opslag-/orakelcontrole en T7 moeten beide rood worden, ook als zoeken naar alleen SHA-256 van de waarde niets vindt.

### 4. Een eigen credentialruimte in de Hub-kluis; herstel omvat ook de kluissleutel

**Keuze.** Het OIDC-clientgeheim krijgt een **eigen uitsluitend voor OIDC bestemde credentialruimte en
binding**, via een eigen codepad/opslagstructuur. De bestaande `vault://auth/oidc-client-secret` is een
legacybron voor gecontroleerde migratie, geen bewijs van die scheiding: `auth` bevat ook bestaand nood-TOTP.
De concrete nieuwe ref en het schema worden bij de bouw vastgesteld, zonder gedeelde `auth`-rijen te herinterpreteren.
Alleen de Hub-OIDC-component kiest de vaste bestemming; de aanvrager kiest geen scope, naam, ref of afnemer.
Er is één actieve Hub-OIDC-configuratie; meerdere clients/instanties delen deze bestemming niet.
Onbekende of tegenstrijdige eigenaar geeft weigering.

De bouw voegt onveranderlijke interne revisies met de context uit besluit 3 toe: een kandidaat is nog niet
actief; de actieve verwijzing kiest alleen een aan die configuratie gebonden revisie. Een nieuwe revisie is
een willekeurige identificatie, nooit een hash van de waarde. Geen stil overschrijven via `Vault.put` zonder
verwachte oude revisie. Migratie van de bestaande singleton vereist eerst bevestiging van de eigenaar;
onbekende bestaande binding wordt niet automatisch vertrouwd. Tabellen/schema en migratie worden bij bouw
vastgesteld, niet als bestaande voorziening verondersteld.

Dit is afzonderlijk van de eigen app-opslag in ADR-0032 besluit 2. Geen afbeelding naar of fallback vanuit
`vault://app/<app_id>/<parameter>`, ook niet voor `app_id` gelijk aan `auth`. De executor, planner, connector,
AI en andere diensten kunnen deze credentialruimte niet ontsluiten. Zij krijgen geen bestand, database,
hoofdsleutel of algemene leesroute. Alleen de kluis/OIDC-component verwerkt plaintext kortstondig voor de
gebonden tokenaanroep. De enige aanvullende interne afnemer is de bestaande logsink: die krijgt via het
OIDC-codepad uitsluitend kortstondig toegang voor redactievingerafdrukken in het geheugen, nooit voor opslag
of afgifte van geheimen/vingerafdrukken. Geen export- of volledige terugleesfunctie buiten die grens.
De integratie behoudt aantoonbaar de bestaande logsink en zijn vingerafdrukken; onleesbare OIDC-rijen stil
overslaan telt niet als afscherming. Deze vluchtige redactievoorziening staat los van verboden duurzame hashes.

Opslag is AES-256-GCM; gekoppelde data bindt ref én de onveranderlijke eigenaar-/revisiecontext, zodat
verwisselde ciphertext niet opent. **Die nieuwe binding geldt uitsluitend voor de eigen OIDC-opslag.**
De gedeelde `Vault.encrypt/decrypt` en de AAD-vorm van bestaande nood-TOTP-, TrueNAS-, monitoring- en
notificatierijen blijven compatibel en ongewijzigd. Geen migratie of rotatie van nood-TOTP als OIDC-bijwerking;
de noodlogin mag door geen enkele ontwerpstap stukgaan. Sleutel in `/appdata/secrets/vault.key`, geheimenmap 0700, bestanden
0600, eigenaar 568:568, buiten bereik van de AI-runner. Bestaande andere kluisgeheimen en sleutels worden
niet geroteerd of gewist voor een OIDC-wijziging. UI-metadata is uitsluitend ingesteld, datum en hooguit
laatste vier tekens volgens §3.10; alleen voor bevoegde beheerders, nooit in connector, audit of events.
Die uitzondering geldt niet voor de appgeheimen van ADR-0032, die ook geen laatste vier bewaren.

De eigen versleutelde herstelset van de Hub omvat ciphertext, revisie-/eigenaarbindingen, noodzakelijke
configuratie en de bijpassende kluissleutel, met aparte versleuteling van de hele set en beheerdersbeveiliging
van het ontsluitmateriaal. Sleutel en database naast elkaar in een leesbaar archief is geen veilige back-up.
Map 0700, bestanden 0600 en toegang tot alleen de herstelbediening; geen download voor viewers of AI.
Herstel van de kluis is een afzonderlijke geautoriseerde herstelhandeling, geen los key-exportendpoint.
Een database-dump met een controlelijst alleen bewijst geen herstel van de kluis (V-085).

Na herstel blijven open/geclaimde overdrachten ongeldig; een oud snapshot mag geen replay opnieuw mogelijk
maken. SSO start uitgeschakeld en vraagt herbevestiging van de huidige Authentik-/clientbinding en een nieuwe
testlogin; ingetrokken oude revisies worden nooit vanzelf actief. Zonder herstelde intrekkingszekerheid
blijft SSO dicht; een nieuwe gebonden overdracht/rotatie heropent nooit een oude sessie.

Iedere OIDC-sessie draagt de configuratie-, geheime revisie- en intrekkingsgeneratie van haar uitgifte.
Bij **ieder verzoek** geldt zij alleen als SSO aan staat, haar binding nog actueel is en haar generatie boven
de actuele intrekkingsondergrens ligt. Uitzetten (ook automatisch bij discovery), vervangen, wissen en
intrekken maken oude OIDC-sessies direct ongeldig, óók als SSO al uit stond. Opnieuw inschakelen laat ze niet
herleven. Lokale sessies en noodsessies worden nooit aan deze OIDC-ondergrens getoetst of mee ingetrokken.

De intrekkingsondergrens/generatie wordt beschermd in een afzonderlijk actueel kluis-/instellingenanker
**buiten `web_session` én buiten de terug te zetten set/dataset**. Herstel mag dit anker nooit verlagen;
ontbrekend, oud of oncontroleerbaar anker betekent weigeren van OIDC-sessies. De bouw legt opslag en
herstelprotocol eerst vast met O1, inclusief oude volledige herstelsets en opnieuw inschakelen. Alleen een
generatie in dezelfde teruggerolde database is onvoldoende. Een ruwe dataset-/snapshotterugrol buiten de
herstelbediening blijft een operationeel restrisico: vooraf SSO uit, via de lokale beheer-/herstelbediening
het onafhankelijke anker vernieuwen, daarna oude sessies/transacties blokkeren en pas na nieuwe binding en
testlogin heropenen. Zonder aantoonbaar actueel anker geen SSO, ook na zo'n terugrol; geen terminalomweg.
Verlies van de kluissleutel kan ook het lokale TOTP-geheim raken:
dit ADR claimt daarvoor geen onafhankelijkheid van de kluis. Volledige herstelproeven horen bij de Hub-back-up,
terwijl de gewone OIDC-overdracht die sleutel en het nood-TOTP juist nooit verandert.

**Alternatieven en reden.** Opslag als appgeheim geeft de verkeerde eigenaar en toegangspaden. Alleen
`vault.key` bewaren mist de data; alleen de dump bewaren mist de sleutel. Een gedeelde sleutel of een
onversleutelde key-export maakt de scheiding ongedaan. Alle zijn verworpen.

**Bewijstest T4.** Schrijf en ontsluit uitsluitend via de echte kluis/OIDC-component met juiste context.
Wissel ciphertext/revisie/clientbinding: weigering. Vul een appgeheim met dezelfde namen en controleer nul
toegang tot de OIDC-ruimte en gedeelde `auth`-geheimen; directe executor-/dienst-/viewer-/AI-pogingen leveren
niets. Maak een niet-lege eigen herstelset, controleer rechten en herstel in isolatie; verwijder sleutel,
binding of setonderdeel: weigering.
Maak vóór de migratie met de bestaande code een werkend noodaccount, bevestigd TOTP, andere kluisrijen,
lokale/noodsessies en een niet-lege logsink. Bewijs een echte LAN-noodlogin in deze geïsoleerde fixture vóór
én na migratie, overdracht en herstel, met hetzelfde bestaande TOTP; niet opnieuw instellen of roteren om
de proef te laten slagen. Alle bestaande niet-OIDC-rijen blijven ontsleutelbaar; hun ciphertext en TOTP blijven
byte-gelijk buiten de bewust geïsoleerde herstelactie. De logsink herkent vóór migratie de bestaande
OIDC-canary en daarna de gemigreerde/nieuwe canary via de verwachte vingerafdruk voor elke aanwezige rij;
tel positieve redactietreffers vóór/na, geen stil wegvallen. Controleer lokale sessies en accountbeleid naast
de normale bijwerkingen van een echte proefnoodlogin.
Herstel eerst `web_session`, daarna een volledige set van vóór intrekking: oude OIDC-cookies geven 401,
open/geclaimde overdrachten blijven ongeldig, óók na nieuwe testlogin en opnieuw inschakelen. Het actuele
anker blijft gelden; een ontbrekend/teruggezet anker houdt OIDC dicht. Lokale/noodsessies blijven geldig
binnen hun eigen grenzen. Dit bewijst meer dan alleen de stand 'SSO uit'.
**Mutatie M-T4.** Voeg namespacefallback toe, laat revisiecontext uit gekoppelde data weg, maak de back-up
leesbaar voor anderen of activeer automatisch een herstelde oude revisie: telkens moet de betreffende proef rood.
Pas de nieuwe AAD naïef in de gedeelde `Vault` toe of laat de logsink OIDC-rijen stil overslaan: de
bestaande-TOTP-/vingerafdrukproef moet rood worden. Herstel `web_session` zonder actuele generatiecontrole,
toets alleen 'SSO uit' of verlaag het anker met de oude set: de sessieherstelproef moet rood worden.

### 5. Rotatie en intrekken sluiten SSO; de lokale noodlogin blijft uitsluitend via LAN werken

**Keuze.** Overdracht is geen bewijs dat Authentik het oude geheim heeft ingetrokken. Vervangen/verwijderen
in de Hub-kluis evenmin. Rotatie/intrekken in Authentik gebeurt pas met een expliciete, precies gebonden
beheerdersgoedkeuring en ondersteunde eigenaarsactie; een nieuwe action_id of policyregel valt buiten dit
ontwerp. Ontbreekt die uitvoercapability, dan doet de beheerder dit in de Authentik-UI. Geen verborgen rotatie
als bijwerking van een herhaling of overdrachtsfout, en geen claim dat een onbekende externe uitkomst voltooid is.

Gekozen is een korte onderbreking van SSO, zonder overlappende automatisch geldige geheimen:

1. De beheerder gebruikt eerst de bestaande **zelftest zonder mutatie**
   (`POST /api/v1/auth/break-glass/selftest`) en houdt een geldige lokale beheerderssessie open.
   De zelftest toetst inrichting/netwerkstatus, geen volledige TOTP-aanmelding. Een echte noodlogin is alleen
   een bewuste oefening met eigen incident en rotatieplicht, geen verplichte voorbereiding op OIDC-rotatie.
   De Hub zet SSO uit, verhoogt de configuratieversie en trekt alle Hub-sessies met `auth_bron=oidc` in,
   ongeacht of SSO eerder al uit stond. Open OIDC-aanmeldtransacties/testresultaten worden onbruikbaar.
2. De beheerder laat het oude clientgeheim bij precies de gebonden Authentik-provider intrekken/vervangen;
   de ondersteunde adapter doet dit alleen onder de eigen geverifieerde autorisatie. Bij onbekende uitkomst
   blijft de Hub dicht; geen terugval naar het mogelijk gelekte oude geheim.
3. Het nieuwe Authentik-geheim gaat als nieuwe kandidaat/revisie via besluit 2–4 naar de kluis. Na een
   volledige nieuwe testlogin met de huidige configuratie en de bestaande Authentik-gate wordt die revisie
   actief; de beheerder schakelt SSO expliciet weer in. Fout, timeout of halve overdracht houdt SSO uit.
   Een geldige oude testlogin opent geen nieuwe revisie. Zonder geheim geen stille omschakeling naar publieke client.
   Testlogin, callback en inschakelen weigeren een ontbrekende, gewiste of ingetrokken geheime revisie vóór
   enige tokenaanroep; wissen blokkeert/verwijdert ook de oude kluisrij en laat haar niet via een oude ref herleven.

Bij een lek: SSO onmiddellijk lokaal uitschakelen, OIDC-sessies en transacties intrekken, de actieve
revisie blokkeren en uit de normale ontsluiting halen; externe intrekking afzonderlijk uitvoeren en bevestigen.
Andere Authentik-/app-/enrollment-/transport-/policy-sleutels blijven gescheiden. Een versleutelde historische
back-up kan een oud geheim bevatten; daarom is externe intrekking nodig en blijft herstel gesloten tot
herbevestiging. Alleen een kluisrij wissen maakt historische kopieën niet onbruikbaar.

Authentik-sessies zijn iets anders dan de lokale Hub-sessiecookie. Een clientgeheim roteren beëindigt niet
vanzelf bestaande gebruikerssessies of al uitgegeven tokens. De Hub controleert zijn eigen intrekking per
verzoek; zo eindigt hun toegang direct. Eventuele externe `sso.sessions.revoke` wordt apart ondertekend,
op de bedoelde Authentik-sessies gericht en bewijst geen intrekking van tokens bij andere afnemers.
Geen brede afmeld-/accountuitschakelactie als vervanging voor clientrotatie.

**Waarom noodtoegang behouden moet blijven.** Het noodaccount is lokaal, met eigen argon2id-wachtwoord;
zijn bestaande TOTP deelt nu `auth`, `Vault` en de hoofdsleutel met OIDC. Alleen de eigen OIDC-ruimte en de
beperkte migratie uit besluit 4 maken de nieuwe binding veilig voor die bestaande rijen; een andere ref
alleen bewijst dat niet. De noodroute roept Authentik en home-control-hub niet aan. De ingreep selecteert alleen
OIDC-transacties en `auth_bron=oidc`-sessies en verandert geen lokale gebruikers, noodbeleid, TOTP, wachtwoord,
kluis-hoofdsleutel, rotatieplicht van de noodlogin of lokale sessies. Naam/e-mail/een gedeelde Authentik-gebruiker
zijn nooit een sessieselectiecriterium. Ook de actieve lokale noodsessie blijft tot haar eigen afloop geldig.
Een interne fout mag geen algemene sessie-intrekking starten.

Het gebruikersbesluit is **alleen LAN**. Het overdrachts-/rotatiepad verruimt de bestaande bronadrescontrole
nooit naar VPN/CGNAT/internet en vertrouwt geen aangeleverde doorstuurheaders.
Privé-adresherkenning alleen bewijst achter portpublicatie niet het echte LAN; dat blijft een afzonderlijke
NAS-netwerkproef. Bestaande ruimere beschrijvingen/settings in recovery/kit worden gemeld in O3, hier niet
gewijzigd. De Hub heeft ook al een optionele CGNAT-schakelaar, standaard uit, die een SSO-beheerder nu zonder
herbevestiging kan aanzetten: de eigen herstelstap hierboven moet dit behandelen. Dit ontwerp steunt er
niet op en geeft geen huidige absolute LAN-garantie. T5 bewaakt dat de setting niet verandert.
Een reguliere succesvolle noodlogin heeft haar eigen audit/incident en rotatieplicht; die normale
bijwerkingen zijn geen OIDC-rotatie en blijven bestaan.

**Alternatieven en reden.** Alleen het secret veranderen laat Hub-sessies leven. Alle gebruikers afmelden,
noodaccount uitschakelen of de hoofdsleutel roteren raakt noodtoegang. Een stil venster met twee geldige
geheimen vergroot het lekvenster. Deze varianten zijn verworpen.

**Bewijstest T5.** Gebruik echte lokale Hub-login-/sessiecode met een werkend noodaccount en TOTP, een actieve
noodsessie, een gewone lokale sessie en OIDC-sessies, allemaal vóór de OIDC-migratie met de bestaande code
ingericht. Behoud precies dat bestaande TOTP en de logsink-vingerafdrukken uit T4 vóór/na iedere overgang.
Draai overdracht, rotatie, intrekking, timeouts en provideruitval: oude OIDC-sessies/callbacks verliezen
toegang; lokale sessies, account, TOTP en beleid blijven
intact. Test ook automatisch uitzetten door discovery, vervangen/intrekken terwijl SSO al uit staat en
opnieuw inschakelen: oude OIDC-cookies telkens 401, geen invloed op lokale/noodsessies. De zelftest van stap 1
veroorzaakt geen noodlogin-incident, TOTP-wijziging of nieuwe rotatieplicht. Een bewuste LAN-proefnoodlogin
met het bestaande TOTP blijft vóór/na werken met nul externe aanroepen en alleen haar gewone bijwerkingen.
Netwerkinstellingen, inclusief de CGNAT-schakelaar, blijven gelijk. Met LAN-beleid actief blijven niet-LAN en
vervalste bronheaders geweigerd. De echte home-control-hub-intrekking raakt alleen het exact goedgekeurde Authentik-doel;
een brede/all_users-variant mag zonder bewezen lokale scheiding niet open. Nieuwe SSO werkt uitsluitend
met de nieuwe revisie plus nieuwe testlogin; extern oud geheim wordt door de nagebootste provider geweigerd.
Wis het geheim en probeer testlogin, callback en inschakelen: vaste fout en nul publieke-client-/tokenaanroepen;
de oude ciphertext is niet meer ontsluitbaar via de actieve of een oude binding.
**Mutatie M-T5.** Laat de OIDC-filter weg, gebruik algemene afmelding, hergebruik het oude testresultaat,
maak noodlogin afhankelijk van de issuer of verruim LAN naar VPN/CGNAT: elke variant maakt de proef rood.
Wijzig de gedeelde AAD, richt het nood-TOTP pas ná migratie opnieuw in, verlies de logsink-vingerafdruk,
vervang de zelftest door een echte noodlogin, sla intrekking over als SSO al uit staat of laat zonder geheim
een publieke tokenaanroep toe: elke eigen proef moet rood worden. T4 vangt ook herleven na herstel.

### 6. De repo-eigenaren leveren afzonderlijk; geen afronding van ongebouwd werk

**Keuze.** De grens voor vervolgopdrachten is:

| Eigenaar/stap | Te bouwen en te bewijzen | Grens |
|---|---|---|
| home-control-hub, S-P2-330 | Echte uitvoering van registratie en sessie-intrekking met alle eigen ExecutionRequest-controles; Authentik-adapter met geverifieerde HTTPS/server-/doelbinding vóór ophalen/schrijven op de eerste verbinding, whitelist op ruwe lees-/aanmaakantwoorden en crashafhandeling. Later de verzendkant van O1; in de handmatige fase nooit een geheim in connectorantwoord. | Geen toegang tot de Hub-kluis, geen lokaal Hub-accountbeheer. Registratie voltooid en geheimoverdracht/SSO voltooid zijn verschillende uitkomsten; ontbrekende overdracht eerlijk onbekend/niet beschikbaar. |
| ai-server-manager, resterend S-P2-070 | Ontvangst en beheerdersbediening, context/claim/revisies, lek-/idempotentiebescherming, herstelbestendige OIDC-sessie-intrekking en eigen OIDC-kluismigratie met bestaand nood-TOTP en logsink intact. De regisseur plant de bestaande afwijkingen als eigen herstelstap vóór gebruik van de tussenweg; haar drie invoereisen wachten niet op O2. UI eerst ontwerp in Peil en daarna ontwerpreview. | Geen Authentik-beheercredential of generieke geheimexport; geen nieuwe actiebevoegdheid. Het vervolg over SSO-beheer van noodnetwerkverruiming krijgt een eigen herstelstap bij de noodlogineigenaar en valt buiten dit ontwerp. |
| ai-server-manager, S-P2-050 deel e | Appgeheimen en enrollment-token, hun eigen opslag, vorm-/doelcontrole en Hub→executor-transport volgens ADR-0032, na diens M2. | Geen OIDC-clientgeheim, geen derde transporttype, geen accountvoorziening via C-12. |
| Contracteigenaar, afzonderlijke contractronde | O1/O2 en de bestaande ADR-0032 M2/M3 afstemmen, exacte vormen en bijbehorende kopieën/pins; O3 bij de bevoegde eigenaarsbeoordeling. | Deze ontwerpcommit verandert het contract en andere repos niet. |

De ontbrekende ADR als leesvoorwaarde van S-P2-330 wordt met dit ontwerp concreet invulbaar na de
onafhankelijke reviews; dit is geen toestemming om andere stopvoorwaarden te negeren. Een zelfstandige,
geheimvrije registratie met tijdelijke handmatige overdracht kan pas na haar eigen volledige acceptatie
worden vrijgegeven. Automatische levering wacht op O1/O2 en beide implementaties. Een placeholder/fake
tegenpartij ontsluit geen capability. Catalogusroute M3 en upgradegate uit S-P2-330 blijven eigen werk.
Geen EVIDENCE-verhoging, Excel-afvinking of claim dat uitsluitend de NAS-test resteert door dit ontwerp.

**Alternatieven en reden.** Alles in 050 deel e onderbrengen verwart inkomende credentials met appdistributie.
Een simulator als ontbrekende tegenpartij of een kleinere acceptatie geeft onbewezen succes. Beide zijn verworpen.

**Bewijstest T6.** Reviews vergelijken repo-diffs, gepinde tegenpartijen en werkende ketens met de tabel;
directe pogingen van planner/executor tot OIDC-ontsluiting weigeren en bestaande 050-appgeheimtests blijven
ongewijzigd. S-P2-330 meldt bij ontbrekende ontvangst geen voltooide SSO en geen geheim in zijn antwoord.
**Mutatie M-T6.** Voeg OIDC toe aan de executor-typen of meld volledige overdracht terwijl de ontvanger
ontbreekt: de grens-/capabilityproef moet rood worden.

### 7. Bewijs zoekt in gevulde uitkomsten en toont voor elk besluit een rode tegenproef

**Keuze.** T1–T7 en M-T1–M-T7 zijn nog te bouwen/draaien, geen bestaande testfuncties of evidence-ID's.
De bouwer legt per besluit echte testnamen, tegenpartijcommits, rode mutatie, herstelde groene uitkomst
en CI vast. Integrale proeven laden de echte Hub- en home-control-hub-code; alleen Authentik/netwerkfouten
worden nagebootst. Volledige NAS/accountvalidatie volgt afzonderlijk en blijft NIET GEVALIDEERD.

T7 maakt per proef een willekeurige, nooit afgedrukte canary en voert daadwerkelijk registratie,
overdracht/invoer, testlogin, rotatie, intrekking en de fout-/crashvarianten uit. De bedoelde geheime
transportbody en de ontsluiting binnen kluis/OIDC zijn uitsluitend vluchtig beschikbaar voor de asserties,
geen persistent testlog of artefact. Zij bewijzen positief dat de juiste waarde de bedoelde ontvanger
bereikte; nul verboden treffers zonder die ontvangst en zonder gevulde opvang is geen bewijs.

Onderzoek daarna niet-lege previews/diffs, signatures/hashinvoer, antwoorden van alle betrokken routes,
audit, events/inbox/outbox, logs van beide diensten/proxies/adapter/nep-Authentik, databasevelden buiten
ciphertext, idempotentie, eventuele recepten, support-/AI-uitvoer en testartefacten. Zoek op de volledige
waarde, URL-/procent-/JSON-/hexvorm en SHA-256, en decodeer samengestelde transportcoderingen. Test expliciet
**Basic = base64(client_id:geheim)** én de in `exchange_code` gebruikte variant met procentcodering van
client-ID en geheim vóór base64. Alleen base64 van het losse geheim zoeken mist dit; kalibreer alle drie
base64-uitlijningen of decodeer elk passend token. **Elke Authorization-kop/credential is verboden in alle
log-, fout- en artefactopvang**, ongeacht of de losse canary wordt gevonden. Inspecteer headers én bodies,
ook na foutafhandeling/redactie en bij de nep-Authentik.

Zoek ook structureel naar afgeleide opslag: de generieke hash van **pad plus gecanoniseerde body met geheim**
is een verboden offline raadorakel, ook als hij niet gelijk is aan SHA-256 van de canary. Herbereken binnen
de vluchtige testgrens met bekende bodyvelden plus juiste en onjuiste kandidaten; geen opgeslagen hash
mag zo een kandidaat bevestigen. De geheime route maakt na O2 nul generieke idempotentierijen (T3).
Niet-geheime idempotente routes hebben wel aantoonbare rijen; geen daarvan bewaart laatste vier in zijn
antwoord, inclusief discover en inschakelen. De laatste-vier-uitzondering van besluit 4 geldt alleen voor
beveiligde kluismetadata en de rechtstreekse bevoegde beheerweergave, nooit voor opgeslagen routeantwoorden.
Vluchtige logsink-vingerafdrukken voor redactie zijn uitsluitend de interne uitzondering uit besluit 4.
Inspecteer een versleuteld resultaat na toegestane ontsleuteling in de testgrens: zoeken in alleen ciphertext telt niet.
In de bedoelde kluis/herstelset wordt correcte encryptie plus eigenaarbinding bewezen; in een journaal,
recept, connectorblob of andere verboden opslag is ook versleutelde geheimopslag een fout.

Ook foutmeldingen mogen geen via Authentik of ongeldige invoer teruggekaatste canary bevatten; vaste
Nederlandse codes met veldnamen komen vóór ruwe exception-/SQL-/providerteksten. Schermopnamen, video's,
HAR en traces met geheime velden zijn uit; bewijsopnamen pas na leegmaken en met alleen veilige status.
Testuitvoer noemt aantallen en codes, nooit waarden, vergelijkingsdiffs of locals met de canary.

**Alternatieven en reden.** Alleen een zoekactie na het normale succespad of in lege tabellen bewijst geen
afscherming. Alleen redactieregexen zien nieuwe fout-/logpaden niet. Testnamen opschrijven zonder draaien
is geen testbewijs. Deze alternatieven zijn verworpen.

**Bewijstest T7.** Alle genoemde opvang heeft een ondergrens en wordt bij succes én fout onderzocht.
Een afzonderlijke controle op ontbrekende opvang faalt. Connectorlevering (plaintext én gecodeerd/versleuteld)
wordt geweigerd, zonder opslag/kluisopvraag; audit/log/antwoord van de weigering blijft geheimvrij.
De canary staat ook in ruwe provider-GET-/lijstantwoorden van de nep-Authentik; detectie, toestand,
voorstel en readback bevatten hem niet na `clean_provider`/adapterfiltering. Kalibreer per opvang de
daadwerkelijke ontvangst met veilige markers en aantallen en kalibreer de detector in een afgeschermde
testbuffer met zowel een ruwe canary als een terugwinbare Basic-/Authorization-kop: elk lek wordt gevonden.
Een opvang die alleen door zo'n injectie gevuld raakt is onvoldoende; leegte is rood. Koppel de T3-opslag-/
raadorakelcontrole aan dezelfde eindcontrole; nul letterlijke treffers alleen is geen goedkeuring.
**Mutatie M-T7.** Laat de uitvoeradapter een body loggen, providerfout of validatiefout de waarde echoën,
audit een geheim opnemen, een geheim in een event/antwoord zetten of een opname bewaren: iedere
afzonderlijke lekmutatie maakt T7 rood. Laat apart een Basic-kop, een andere Authorization-kop, de hash van
pad plus geheime body of laatste vier in idempotentieopslag terechtkomen; omzeil apart de whitelist voor
ruwe provider-leesantwoorden: **elke lekmutatie afzonderlijk rood** in de betreffende log-/fout-/artefact-
of opslagcontrole. Leeg één opvang, verwijder de kalibratie of sla de positieve ontvangst over: eveneens rood.
De gecontroleerde lekwaarden blijven binnen de testgrens en worden nooit naar CI-uitvoer gepubliceerd.

## Open contractmeldingen en tekstvoorstellen

Dit zijn **open voorstellen**, geen wijziging of nieuwe uitzondering in contract 1.3. De betrokken nieuwe
mogelijkheden blijven dicht tot vastlegging, bouw en onafhankelijke acceptatie. Een ontwerp kan worden
gereviewd en gepusht terwijl zijn toekomstige uitvoerpad gesloten blijft.

| Melding | Bron/eigenaar | Tekstvoorstel en sluitvoorwaarde | Blijft dicht |
|---|---|---|---|
| O1 inkomende OIDC-overdracht | Contract §3.1(b), §3.10 en §4.4; ai-server-manager en home-control-hub. | “De eerste verbinding, Authentik → home-control-hub, gebruikt verplicht geverifieerde HTTPS met certificaat-/servernaam- én vooraf bevestigde Authentik-doelbinding; geen HTTP-terugval, weigering vóór ophalen of schrijven. Dit is verantwoordelijkheid van de uitvoeradapter in S-P2-330. De clientcredential gaat daarna uitsluitend via afzonderlijk wederzijds geauthenticeerd, versleuteld en vooraf gepind transport naar de eigen Hub-OIDC-ruimte. Binding omvat Hub, dienst, Authentik/provider/client/redirect, configuratie-/kluisrevisie, beheerder en maximaal vijf minuten. Eén claim, alleen status terug; nooit connector/items/events/leesroutes.” Leg route, strikt schema, codes, beide transportgrenzen/-rotatie, claim/crash/herstel, het onafhankelijke intrekkingsanker en beëindiging van de tussenweg gezamenlijk vast. Beide echte implementaties bewijzen T1/T2/T4/T7 inclusief de eerste verbinding. | Automatische levering en haar herstelbediening; geen extra service-tokenscope. |
| O2 eigen eenmaligheid van geheime invoer | Contract §5; `hub/deps.py::_idempotency`, `hub/routers/oidc.py::put_oidc`; ai-server-manager. | “De eenmalige geheime OIDC-invoer gebruikt de gebonden claim en bewaart geen geheime invoer of afgeleide vorm: geen hash van pad plus body, geen afgifteantwoord of laatste vier in idempotentieopslag. Tweede levering weigeren, statusnavraag geheimvrij; niet-geheime voorbereidingsmutaties behouden Idempotency-Key zonder geheime responsmetadata.” Leg de gemotiveerde uitzondering en route-/replaymatrix eerst vast; tot dan geen afwijkende idempotentielaag of nieuwe claimroute. De bestaande tijdelijke contractweg is pas bruikbaar na haar eigen herstelvoorwaarden. Haar HTTPS-weigering, browserveldbeveiliging en lokale hoogste beheerdersrol zijn bestaande afwijkingen die geen contractwijziging vragen en geen deel van O2 zijn. | Nieuwe eenmalige handmatige/automatische claimroute; geen heimelijke uitzondering op §5. O2 stelt de drie zelfstandige invoerherstellingen niet uit. |
| O3 noodlogin alleen LAN | Contract §4.1/§1.2; home-control-hub `sso/kit.py::PROCEDURE_NL`, `sso/recovery.py::validate_scopes`; Hub `breakglass.py::cgnat_setting` en `routers/breakglass.py::put_cgnat`. | “Voor deze installatie blijft noodlogin uitsluitend LAN; overdracht/rotatie wijzigt noch verruimt netwerkbeleid en raakt geen lokale noodsessies, accounts of bestaand TOTP.” Laat eigenaren de ruimere instructies/settings en de bestaande SSO-beheerdersverruiming zonder herbevestiging in een eigen herstelstap afstemmen op het gebruikersbesluit. De optionele Hub-schakelaar bestaat al en staat standaard uit; dit ontwerp steunt er niet op, verandert haar niet en bewijst dat met T5. Bronadres op de NAS afzonderlijk vaststellen vóór een netwerkclaim. | Elke netwerkverruiming door dit ontwerp en een onbewezen absolute LAN-garantie; niet het schrijven van dit ontwerp. |

ADR-0032 **M2 blijft open en afzonderlijk**: Hub→executor, twee gebonden typen, onveranderlijke revisies,
tokenuitgifte en ref-only recepten. O1/O2 sluiten M2 niet; M2 geeft evenmin toestemming voor OIDC-inname.
Afstemming in dezelfde contractronde mag transportprincipes delen, nooit endpoints, privésleutels,
opslagbevoegdheden of typen stil samenvoegen. De eigen app-opslag uit besluit 2 daar blijft onbereikbaar
vanuit de OIDC-ruimte en de gedeelde `auth`-ruimte en omgekeerd. C-12-accounts blijven uitsluitend beschrijvend en geheimvrij in het manifest.

Overige nog vast te stellen bouwdetails: exact gepinde Authentik-generator/rotatie-API en grenzen,
revisieschema/migratie, UI-bediening, transportcertificaten en geverifieerde kluisherstelset. Dat zijn geen
gemeten productievoorzieningen. Eerst vaststellen met `rg -n 'client_secret|rotate|revoke|oauth2'` in
home-control-hub `apps/api/src/integrations/domains/sso` en de daar gepinde upstreamschema's, en
`rg -n 'OidcConfig|VaultSecret|run_self_backup|Idempotency' apps/api/src/hub` in de Hub; daarna de gerichte
bron-/versieproef en hierboven vereiste bouwtests. Geen echte NAS-/accountgegevens invullen of benaderen.

## Verificatie van deze ontwerpstap

De oorspronkelijke ontwerpcommit voegde dit ADR en een verwijzing in ADR-0032 toe. Deze herstelronde wijzigt
uitsluitend dit ADR: de bestaande besluiten/T1–T7/M-T1–M-T7, bestaande afwijkingen en open O1/O2/O3 worden
aangescherpt; de verwijzing blijft geldig. Mutaties worden hier alleen ontworpen, niet gedraaid. Controleer relatieve
documentlinks, besluiten 1–7 met alternatief/reden en bewijstest/mutatie, de harde connectorweigering,
de afzonderlijke richting/namespace en de open vrijgavegrenzen. Draai de bestaande contract-, manifest-
en evidencecontroles van P-ai-server-manager voor het geraakte documentatiedeel, plus P-GIT en P-EERLIJK.
P-VEILIG en de lokale-noodtoegangsgrens worden als ontwerpchecklijst beoordeeld; uitvoercode en tests
worden hier niet gewijzigd. Volledige code-/migratie-/UI-/imagepoorten lopen via de ongewijzigde CI op
deze ontwerpcommit. Lokale documentcontroles en groene bestaande CI zijn geen uitvoering van T1–T7.
Daarna volgen R-TECH en R-VEILIG, herstel/herreview waar nodig en R-EERLIJK via de regisseur.
