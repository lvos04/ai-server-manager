# ADR-0030 — Policy-engine, goedkeuringen en executor (P2 deel 1)

Status: aangenomen · 2026-11-11 · fase P2 deel 1 · repo `ai-server-manager`
Bouwt op: ADR-0007 (gates), ADR-0010 (koppelen executor), ADR-0029 (contract 1.3 in Hub en executor).
Bron: `docs/platform-v2/PLATFORM_CONTRACTEN.md` §3.9, §4.7 en §8; B01-003, B01-007, B02-005, B02-006, B12-006;
`03_RISICO_AUTONOMIE`; testmatrix EX11, EX12, EX17–EX20, EX27, EX47. Alles is Sim-getest tegen de in-repo fake van de
TrueNAS-API; niets is op een echte NAS gevalideerd.

## Context

Tot P2 weigerde de executor alles en bestond er geen beleid. Dit deel bouwt de stroom van contract §8:
voorstel → deterministische policy → (bij R2/R3) menselijke goedkeuring per gebonden diff → ondertekend
`ExecutionRequest` → executor controleert zelf opnieuw → uitvoering → readback → audit.

## Besluiten

1. **Eén gedeeld pakket `asm_policy` (`apps/policy`).** De Hub en de executor installeren hetzelfde pakket en lezen
   dezelfde `policy/*.yaml`. Zo kan de classificatie in de Hub nooit ongemerkt afwijken van de hercontrole in de
   executor. De executor importeert nog steeds niets uit de Hub.
2. **Beleid read-only in beide images.** `/usr/local/share/asm/policy` (root, 0555/0444). In een image wint die map
   altijd; `ASM_POLICY_DIR` werkt alleen daarbuiten (tests). De `policy_hash` telt elke byte van elke `*.yaml`. Een
   ongeldig beleid laadt niet (fail-closed). Er is geen route en geen `action_id` om beleid te wijzigen.
3. **Classificatie is een pure functie.** `classify` krijgt `risk_claim` niet eens binnen (EX18). Volgorde: verboden
   patronen → boiler → gereserveerd → onbekend → basisklasse → kritieke app → beschermde app → soort actor. De
   strengste regel wint; herkenning van een app maakt alleen strenger.
4. **Verboden patronen gelden per segment.** `system.sudo`, `app.shell.exec` en `pool.dataset.delete` zijn geweigerd,
   niet alleen `shell.*`. Destructieve acties worden in deze versie niet aangeboden, ook niet met goedkeuring.
   Precies: BLK-SHELL, BLK-DESTRUCTIEF en BLK-DB-DIRECT toetsen elk segment; BLK-BEVEILIGING en BLK-NETWERK alleen
   het eerste segment (`policy.…`, `network.…`) en BLK-BETAALD een deelstring. Een `action_id` met zo'n woord verderop
   (bv. `app.network.set`) staat nooit op de allowlist en wordt als onbekend geweigerd (`403 actie_niet_toegestaan`).
   De patronen blijven zo (besluit van de regisseur, 2026-11-12; een wijziging geeft een nieuwe `policy_hash`). Elke
   verboden blokkade heeft een test met haar eigen code (`apps/policy/tests/test_policy.py`).
5. **Boiler (EX27).** Gezocht in `action_id`, doel en alle sleutels en tekstwaarden van de parameters. Uitzondering:
   de vrije tekst van `notification.send` — een melding óver de boiler schakelt niets en de bewaking moet erover
   kunnen melden. Het doel en de `action_id` van een melding tellen wel. Diepte (S-P2-010, dicht bij twijfel):
   parameters zijn hooguit 16 niveaus diep genest (`422 parameters_ongeldig`, `te_diep_genest`); de boilercontrole en
   de EX47-controle kijken tot de grens van de canonieke JSON (32 niveaus) en weigeren dieper in plaats van stil te
   stoppen (dieper telt als boiler).
6. **`app.install` (B01-003, EX47).** Alleen `app.create` met `custom_app` afwezig of `false`. De standaard Custom App
   is `catalog_app: ix-app`, trein `stable`, met ix-app-waarden uit een witte lijst. Geweigerd vóór uitvoering:
   `custom_compose_config(_string)` op elke diepte, privileged, host-netwerk/-PID/-IPC, extra capabilities, devices,
   Docker-socket, hostpaden buiten `/mnt/<pool>/<dataset>`, `latest` of een tag zonder digest. Een catalogusapp vraagt
   een exacte versie en een `install_reason`. Ook de eigen waarden van een catalogusapp krijgen op elke diepte geen
   compose, privileged, host-netwerk zonder reden, host-PID/-IPC, extra capabilities, devices, gedeeld netwerk, GPU
   zonder `gpu: intel_render` in het manifest of Docker-socket (S-P2-010). Dat geldt ook voor een losse tekst in een
   lijst (S-P2-010, herstelronde 2; dicht bij twijfel): een Docker-socket, een hostpad buiten een dataset in bind- of
   volumevorm (`"/:/host"`, `"--volume=/etc:/etc"`, `"type=bind,source=/,..."`), een ongeldige kluisverwijzing en een
   verboden sleutel als vlag (`"--privileged"`, `"pid=host"`, `"--cap-add=SYS_ADMIN"`; een vlag zonder waarde telt
   als aan, ook `"--pid"`). Een geldige kluisverwijzing in een lijst wordt gevonden en geeft
   `501 capability_unavailable`, net als in een object. Een hostpad weigert ook elk teken uit de Unicode-categorieën
   Cc, Cf, Zl en Zp en een spatie aan het begin of eind van een mapnaam. Een tekst die geen
   geldige UTF-8 is (een losse surrogaat) is niet canoniek: `422 parameters_ongeldig` (`niet_canoniek`).
   **Eén tabel van verboden sleutels (S-P2-010, herstelronde 3).** Een sleutel in een object, een losse tekst in een
   lijst en de vlagvorm gaan door dezelfde tabel (`asm_policy.params`, `VERBODEN_SLEUTELS`). Sleutels worden eerst
   genormaliseerd: kleine letters, alleen letters en cijfers (zoals de manifestregels van appstore-en-fork), dus
   `Privileged`, `hostNetwork` en `host-network` zijn dezelfde sleutel als `privileged` en `host_network`. De tabel
   geldt in de waarden van een catalogusapp en in elk onderdeel van de standaard Custom App:
   - `privileged`, `host_network` (zonder reden), `host_pid`, `host_ipc` en `use_all_gpus` (zonder
     `gpu: intel_render`): verboden met elke waarde behalve afwezig, `null` of `false` (dus ook `1`, `0`, `"true"`
     en `"false"`);
   - "compose" ergens in de sleutel, of de sleutel `services`: altijd verboden;
   - `network_mode`, `net` en `network`: verboden met de waarde `host` of de namespace van een andere container
     (`container:…`, `service:…`); dezelfde waarden bij `pid` en `ipc`;
   - de Docker-/compose-namen `pid_mode`, `ipc_mode`, `uts`, `userns(_mode)`, `cgroup(ns)`, `cgroup_parent`,
     `security_opt`, `seccomp`, `apparmor`, `sysctl(s)`, `volumes_from`, `runtime`, `device(s)`,
     `device_cgroup_rules`, `cap_add` en `allowPrivilegeEscalation`: verboden met een niet-lege waarde, als vlag
     ook zonder waarde (`"--device"`, `"--security-opt=…"`, `"--userns=host"`); `command` en `entrypoint` alleen bij
     een catalogusapp (bij de standaard Custom App zijn het gewone velden);
   - "unconfined" in een tekst: altijd verboden.

   De nieuwe namen geven de code `catalogus_waarde_verboden`; de bestaande sleutels houden hun eigen code. In de
   tekstvorm (`"sleutel=waarde"`, `"--sleutel waarde"`) is de waarde altijd een tekst: daar telt een vlag zonder
   waarde als aan en tellen `false`, `0`, `no`, `off`, `none` en `null` als uit (`"--privileged=false"` mag).
   In de waarden van een catalogusapp krijgt ook een tekstwaarde in een object de controle van een losse tekst
   (`{"extra_args": "--privileged"}`, `{"volume": "/:/host"}`), en tellen `source`, `src`, `hostpath` en `path`
   (genormaliseerd) met een waarde die met "/" begint als hostpad. Vrije tekst is daarvan uitgezonderd: de waarde
   naast `name` of `key` in een paar (`envs[].value`, `additional_envs[].value`, `labels[].value`), `notes` en
   `description`. De Docker-socket, een ongeldige kluisverwijzing en "unconfined" blijven ook daar geweigerd.
   Een losse tekst met een onzichtbaar opmaakteken (Unicode-categorie Cf) wordt geweigerd (`stuurteken`), en
   `"-v/:/host"` en `"--volume/:/host"` (de waarde direct achter de optie) worden als bindvorm herkend.
   Bij de standaard Custom App zijn `command` en `entrypoint` de opdracht van het proces ín de container: het
   ix-app-sjabloon (truenas/apps, `ix-dev/stable/ix-app/templates/docker-compose.yaml`, ix-app 1.4.8) geeft ze
   alleen door aan `set_command` en `set_entrypoint` van de container. Voor de teksten direct in die twee lijsten
   geldt de vlag- en bindcontrole daarom niet (`["java", "-cp", "/app/lib/*:/app/classes", …]` mag); de
   Docker-socket, een ongeldige kluisverwijzing en "unconfined" blijven geweigerd en een geldige kluisverwijzing
   geeft `501`. Een controle op vrije tekst blijft onvolledig (bijvoorbeeld JSON als tekst of een ander streepje
   dan "-"); voor catalogusapps blijft de echte grens het schema van TrueNAS en het manifest
   (NIET GEVALIDEERD (echte NAS)).
   **Opslag: ZFS-eigenschappen, mountpoint en ACL (aanvulling 2026-11-14, KLEIN-76; besluit van de gebruiker "Nu
   herstellen", dicht bij twijfel).** De middleware van TrueNAS laat onbekende sleutels door en neemt
   `ix_volume_config.properties` mee bij het aanmaken van het dataset van een ixVolume (ook `mountpoint`); een
   `host_path_config.acl` wordt ook bij `acl_enable: false` verwerkt (afgeleid uit de bron, KLEIN-75 A5 en A1).
   Daarom: `ix_volume_config.properties` is bij elke app (standaard Custom App en catalogusapp) en met elke waarde
   geweigerd, ook `{}` en `null`, met de nieuwe code `zfs_eigenschappen_verboden`; `mountpoint` (genormaliseerd) met
   een waarde die met "/" begint is overal een hostpad (`hostpad_verboden` buiten `/mnt/<pool>/<dataset>`), ook bij de
   standaard Custom App. Bij de standaard Custom App is een aanwezig `host_path_config.acl` (ook leeg of `null`)
   dezelfde weigering als `acl_enable: true` (`acl_verboden`), en `acl.path` gaat ook door de hostpadregel. Dat geldt
   in een opslagregel van elk type (R-VEILIG-1, 2026-11-14: TrueNAS normaliseert een meegestuurde `host_path_config`
   ook in een regel van type `ix_volume` of `tmpfs`); `host_path_config.path` gaat dan ook door de hostpadregel.
   Daarnaast (besluit van de regisseur, dicht bij twijfel): een config van een ander type dan de regel
   (`host_path_config`, `ix_volume_config`, `tmpfs_config`, `nfs_config`, `cifs_config`, `volume_config`, ook in een
   andere schrijfwijze) die niet leeg is (alleen afwezig, `null` of `{}` is leeg) geeft `opslag_verboden`. Geen
   geldige payload stuurt zo'n config mee (appstore-en-fork vertaalt per regel alleen de config van het eigen type).
   Een witte lijst binnen een opslagregel, `dataset_name`, ACL op een ixVolume en cifs/nfs bij catalogusapps
   (KLEIN-75 A2, A3, A4, A6, A7) zijn hier niet besloten; A3 en A6 besluit de latere aanvulling KLEIN-78 hieronder,
   A2 de latere aanvulling KLEIN-80, A4 het herstel van KLEIN-80, A7 (NFS) de latere aanvulling KLEIN-83.
   `policy/*.yaml` en de `policy_hash` veranderen hierdoor niet. NIET GEVALIDEERD (echte NAS).
   **Opslag: datasetnaam van een ixVolume en SMB-wachtwoord (aanvulling 2026-11-14, KLEIN-78; KLEIN-75 A3 en A6;
   besluit van de regisseur, dicht bij twijfel).** TrueNAS maakt het dataset van een ixVolume aan als
   `<docker-dataset>/app_mounts/<app>/<dataset_name>` en controleert de naam nergens als pad (middleware ece9d19,
   `update_volumes` en `normalize_ix_volume`). Daarom moet `ix_volume_config.dataset_name` (genormaliseerde sleutel;
   ook een `ix_volume_config` die zelf een tekst is) bij elke app een veilige naam zijn: alleen de tekens die ZFS in
   een datasetnaam toestaat (middleware `validate_dataset_name` -> `truenas_pylibzfs.name_is_valid`; OpenZFS
   `zfs_namecheck.c`: letters, cijfers, `-`, `_`, `.`, `:` en spatie), in delen gescheiden door `/`, zonder `/` aan het
   begin of eind, zonder leeg deel, zonder `.` als deel, nergens `..`, hooguit 200 tekens. Anders de bestaande code
   `patroon` (of `type` als het geen tekst is). Van de 194 standaardnamen in de catalogusapps van TrueNAS
   (truenas/apps f142a16) valt alleen `data#` hierbuiten; die weigert ZFS zelf ook (`#` is het teken van een
   bladwijzer). In de waarden van een catalogusapp was `cifs_config.password` (genormaliseerde sleutels) eerst alleen
   als geldige kluisverwijzing `vault://app/<app_id>/<parameter>` toegestaan (besluit 28; die geeft eerlijk `501`);
   elke andere waarde gaf de code `geheim_in_klare_tekst`. Die wachtwoordregel is op dezelfde dag vervangen door de
   herstelregel hieronder. Een ongeldige `vault://`-tekst houdt `vault_ref_ongeldig`. Andere wachtwoordvelden van
   catalogusapps vallen hier niet onder (KLEIN-75 A6 optie a is niet gekozen). Witte lijst per opslagregel, ACL op een
   ixVolume en NFS/SMB-paden (KLEIN-75 A2, A4, A7) blijven open (A2 besluit de latere aanvulling KLEIN-80 hieronder,
   A4 het herstel van KLEIN-80, A7 voor NFS de aanvulling KLEIN-83).
   `policy/*.yaml` en de `policy_hash` veranderen niet.
   NIET GEVALIDEERD (echte NAS).
   **Opslag: SMB bij catalogusapps geweigerd (aanvulling 2026-11-14, KLEIN-78 herstel R-VEILIG-1; KLEIN-75 A6 optie
   b, besluit van de regisseur, dicht bij twijfel).** De wachtwoordregel hierboven was te omzeilen: TrueNAS bouwt de
   mountopties van een SMB-volume uit `cifs_config` (`user=`, `password=`, `domain=` en elke tekst uit `options`, met
   komma's aan elkaar; truenas/apps f142a16, library 2.3.18, `CifsVolume`), dus het wachtwoord ging ook via `options`
   (`pass=`, `password=`, `password2=`, `credentials=`) of via een komma in `username` of `domain` in klare tekst mee.
   Daarom geeft in de waarden van een catalogusapp elke opslagregel van type `cifs` en elke niet-lege `cifs_config`
   (genormaliseerde sleutel en typewaarde, ook in een lijst en op elke diepte; leeg is alleen afwezig, `null` of `{}`)
   de bestaande code `opslag_verboden`, met of zonder wachtwoord en ook met een kluisverwijzing. Eén code: dezelfde
   als voor cifs bij de standaard Custom App, en juist voor elke vorm (ook zonder wachtwoord of met een
   kluisverwijzing, waar `geheim_in_klare_tekst` niet zou kloppen). De code `geheim_in_klare_tekst` vervalt. Geen
   geldige payload gebruikt cifs (appstore-en-fork kent alleen `host_path`, `ix_volume` en `tmpfs`). Deze weigering
   moet weer open bij S-P2-050/S-P2-070, als de executor kluisverwijzingen invult; daar horen ook bij: (1) de
   `<app_id>` in een kluisverwijzing binden aan `target.app_id` en `.` en `..` als `<parameter>` weigeren (anders kan
   het SMB-wachtwoordveld het geheim van een andere app naar een zelfgekozen SMB-server sturen), en (2) komma-injectie
   in de CIFS-mountopties ook buiten wachtwoorden (bv. `username: "gast,uid=0"`) dichtzetten met een witte lijst per
   catalogusapp. `policy/*.yaml` en de `policy_hash` veranderen niet. NIET GEVALIDEERD (echte NAS).
   **Opslag: witte lijst per opslagregel van de standaard Custom App (aanvulling 2026-11-14, KLEIN-80; KLEIN-75 A2;
   besluit van de regisseur, dicht bij twijfel).** De middleware van TrueNAS laat onbekende sleutels door
   (`extra='allow'`) en de bibliotheek (library 2.3.18) gebruikt er een aantal die het formulier niet toont. Daarom
   geldt bij de standaard Custom App (ix-app) een witte lijst, precies de velden van het formulier van ix-app 1.4.8
   (truenas/apps f142a16, `ix-dev/stable/ix-app/questions.yaml`): een opslagregel kent alleen `type`, `read_only`,
   `mount_path`, `host_path_config`, `ix_volume_config`, `cifs_config`, `nfs_config` en `tmpfs_config`;
   `host_path_config` alleen `acl_enable`, `acl` en `path`; `ix_volume_config` alleen `acl_enable`, `dataset_name` en
   `acl_entries`; `tmpfs_config` alleen `size`. Elke andere sleutel (exacte naam), ook in een lege config van een ander
   type, geeft de bestaande code `onbekend_veld`. Apart beoordeeld en geweigerd, omdat de policy ze niet beoordeelt en
   geen geldige payload ze gebruikt (appstore-en-fork, `IxStorage`): `create_host_path` (maakt een hostpad aan),
   `propagation` (mount-propagatie), `auto_permissions` (rechten zetten) en `exec`, `mode`, `uid` en `gid` van tmpfs, met
   elke waarde (als sleutel; via `mount_path` waren die tmpfs-opties tot het herstel hieronder nog wel te zetten, nu
   niet meer). `properties` houdt daarnaast `zfs_eigenschappen_verboden`. Velden op de lijst houden hun eigen regel:
   `acl` blijft `acl_verboden`, een niet-lege `cifs_config`/`nfs_config` blijft `opslag_verboden`; `acl_enable` en
   `acl_entries` van een ixVolume staan op de lijst omdat het formulier ze toont, ACL op een ixVolume (KLEIN-75 A4) is
   hiermee niet besloten (A4 besluit het herstel hieronder). De config van het eigen type is een object (anders
   `type`), `read_only` is true of false (anders `type`) en `tmpfs_config.size` is een geheel getal van minstens 1 MiB
   (anders `bereik`; een bovengrens is niet besloten; zie de aanvulling KLEIN-85 hieronder). Gevolg (bewust): een nieuw veld in een latere ix-app-versie
   wordt geweigerd tot de lijst is bijgewerkt. Catalogusapps vallen hier niet onder (S-P2-050). `policy/*.yaml` en de
   `policy_hash` veranderen niet;
   restrisico executor-image: zie "Engine-regels buiten de `policy_hash`". NIET GEVALIDEERD (echte NAS).
   **Opslag: strikt koppelpad en geen ACL op een ixVolume (aanvulling 2026-11-14, KLEIN-80 herstel R-VEILIG-1 en
   R-VEILIG-2; KLEIN-75 A4 optie a; besluit van de regisseur, dicht bij twijfel).** Twee velden op de witte lijst
   droegen de gevaarlijke inhoud alsnog. (1) De bibliotheek geeft een tmpfs weer als tekst `"<mount_path>:<opties>"`
   (truenas/apps f142a16, library 2.3.18, `Tmpfs.render`) en niemand controleerde `mount_path` op `:` of `,`; met
   bijvoorbeeld `/cache:exec,suid,dev,mode=4777,uid=0,gid=0,=` waren zo de tmpfs-opties toch te zetten, en een `.`-deel
   (`/proc/.`, `/./proc`) ontliep de lijst van verboden containerpaden (de middleware maakt er met `normpath` `/proc`
   van). Daarom is `mount_path` bij de standaard Custom App alleen een strikt containerpad: `/` gevolgd door delen van
   ASCII-letters, cijfers en `.`, `_`, `@`, `+`, `-`, gescheiden door één `/`, zonder `.`- of `..`-deel en zonder `/`
   aan het eind; het genormaliseerde pad is geen verboden containerpad (`/`, `/proc`, `/sys`, `/dev`, de
   Docker-socket). Anders de bestaande code `mount_verboden`. Alle koppelpaden uit de manifesten van de elf repos
   (`/app/data`, `/appdata`, `/beszel_data`, `/cache`, `/certs`, `/config`, `/data`, `/media`, `/templates`,
   `/var/lib/beszel-agent`, `/var/lib/postgresql`) blijven geldig. (2) TrueNAS zet een ACL op een ixVolume zodra
   `ix_volume_config.acl_entries` niet leeg is, ook met `acl_enable: false` (middleware ece9d19,
   `normalize_ix_volume`: `if acl_dict:`), en bij een `dataset_name` die eerder in dezelfde installatie staat stopt
   `normalize_ix_volume` vóórdat het pad door het eigen ixVolume wordt vervangen: dan houdt `acl_entries` zijn eigen
   `path`, slaat `validate_acl_entries` bij `options.force` de controle over en zet `filesystem.add_to_acl` een
   recursieve ACL op elk pad onder `/mnt`, ook de data van andere apps. Het uitgangspunt van KLEIN-75 A4 ("pad door de
   middleware bepaald") klopt dan niet. Daarom geeft bij de standaard Custom App een niet-lege `acl_entries` (leeg is
   alleen afwezig, `null` of `{}`) of een `acl_enable` anders dan false in `ix_volume_config` `acl_verboden`, zoals bij
   `host_path_config`, en mag elke `dataset_name` hooguit één keer per installatie voorkomen (anders de bestaande code
   `dubbel`, die `_ix_values` al gebruikt voor een dubbele variabele: dezelfde betekenis; `opslag_verboden` of
   `patroon` zou een verboden opslagsoort of een ongeldige naam suggereren). Gevolg (bewust): via het platform komt er
   geen ACL op een ixVolume. Geen geldige payload gebruikt dat: appstore-en-fork kent in `IxVolumeConfig` alleen
   `acl_enable: false` en `dataset_name`, en de 9 opnieuw vertaalde payloads van de manifesten bevatten geen
   `acl_entries` en geen dubbele `dataset_name`. Catalogusapps vallen hier niet onder (S-P2-050). `policy/*.yaml` en
   de `policy_hash` veranderen niet; restrisico executor-image: zie "Engine-regels buiten de `policy_hash`". Afgeleid
   uit de bron; NIET GEVALIDEERD (echte NAS).
   **Opslag: ook onder een verboden containerpad (aanvulling 2026-11-14, KLEIN-81; vervolgpunt van de herreview van
   KLEIN-80; besluit van de regisseur, dicht bij twijfel).** De vergelijking met de verboden containerpaden (`/`,
   `/proc`, `/sys`, `/dev`, `/var/run/docker.sock`, `/run/docker.sock`) was exact: `/proc/sys`, `/dev/shm` en
   `/sys/fs/cgroup` gaven geen fout. Nu geldt een verboden containerpad ook voor alles eronder, per padsegment, op het
   genormaliseerde pad: `/proc/sys`, `/dev/shm` en `/sys/fs/cgroup` geven `mount_verboden`; `/process`, `/devices` en
   `/procfs/sys` niet (geen eigen segment). `/` telt alleen exact, want elk pad ligt eronder. Hoofdletters tellen mee:
   Linux is hoofdlettergevoelig, dus `/PROC` en `/PROC/sys` zijn andere paden dan `/proc` en blijven geldig. Geldt
   waar de lijst al gold: alleen `mount_path` van de standaard Custom App (catalogusapps: S-P2-050). Geen geldig
   koppelpad ligt onder een verboden containerpad: de 11 koppelpaden uit de manifesten van de elf repos en de
   koppelpaden van de 9 opnieuw vertaalde payloads van appstore-en-fork blijven geldig. `policy/*.yaml` en de
   `policy_hash` veranderen niet; restrisico executor-image: zie "Engine-regels buiten de `policy_hash`". NIET
   GEVALIDEERD (echte NAS).
   **Opslag: door Docker beheerde bestanden en `/run/secrets` (aanvulling 2026-11-14, KLEIN-88; vervolgpunt van
   R-VEILIG bij KLEIN-81; besluit van de regisseur, dicht bij twijfel).** De lijst van verboden containerpaden is
   aangevuld met `/etc/hosts`, `/etc/hostname` en `/etc/resolv.conf` (bestanden die Docker zelf in elke container
   beheert) en `/run/secrets`; alleen deze vier. De vergelijking per padsegment van KLEIN-81 geldt ook hier:
   `/run/secrets/x` en `/etc/hosts/x` geven `mount_verboden`; `/etc`, `/run`, `/etc/hostsx`, `/run/secretsx` en
   `/ETC/hosts` blijven geldig (`/etc` en `/run` waren en blijven geldig). Er was geen gat naar de host aangetoond;
   doel is dat een koppeling deze door Docker beheerde bestanden en de geheimenmap in de container niet vervangt.
   `/var/run/secrets` staat er niet in (besluit: alleen deze vier paden); de policy toetst de padtekst, niet
   symlinks in de image (zoals `/var/run` naar `/run`). Geldt waar de lijst al gold: alleen
   `mount_path` van de standaard Custom App (catalogusapps: S-P2-050). Geen geldig koppelpad ligt op of onder deze
   paden: de 11 koppelpaden uit de manifesten van de elf repos en de koppelpaden in de tests blijven geldig.
   `policy/*.yaml` en de `policy_hash` veranderen niet; restrisico executor-image: zie "Engine-regels buiten de
   `policy_hash`". NIET GEVALIDEERD (echte NAS).
   **Opslag: `/var/run/secrets` (aanvulling 2026-11-14, KLEIN-90; vervolgpunt van R-VEILIG bij KLEIN-88; besluit van
   de regisseur, zelfde lijn als de Docker-socket, waar `/var/run/docker.sock` en `/run/docker.sock` allebei in de
   lijst staan).** De lijst van verboden containerpaden is aangevuld met `/var/run/secrets`; verder niets. Dit
   vervangt de zin "`/var/run/secrets` staat er niet in" van KLEIN-88 hierboven. In gangbare images is `/var/run` een
   symlink naar `/run`, zodat een koppeling op `/var/run/secrets` op `/run/secrets` uitkwam. De vergelijking per
   padsegment van KLEIN-81 geldt ook hier: `/var/run/secrets/x` geeft `mount_verboden`; `/var/run`,
   `/var/run/secretsx` en `/VAR/run/secrets` blijven geldig. Andere symlinks in een image blijven buiten beeld (de
   policy toetst de padtekst). Geldt alleen voor `mount_path` van de standaard Custom App. Geen geldig koppelpad ligt
   op of onder dit pad: de 11 koppelpaden uit de manifesten, de koppelpaden van appstore-en-fork en die in de tests
   blijven geldig. `policy/*.yaml` en de `policy_hash` veranderen niet; restrisico executor-image: zie
   "Engine-regels buiten de `policy_hash`". NIET GEVALIDEERD (echte NAS).
   **Opslag: NFS bij catalogusapps geweigerd (aanvulling 2026-11-14, KLEIN-83; KLEIN-75 A7; besluit van de
   regisseur, dicht bij twijfel, zelfde lijn als SMB).** NFS bij een catalogusapp werd alleen toevallig geweigerd: een
   exportpad met `/` gaf `hostpad_verboden` (misleidend: het is een pad op de NFS-server, niet op de NAS), en een
   exportpad zonder `/`, een `nfs_config` zonder pad, type `nfs` zonder config, een andere schrijfwijze of een
   `nfs_config` in een regel van een ander type ging erdoor tot TrueNAS. TrueNAS bouwt de mountopties uit `nfs_config`
   (`addr=<server>` en elke tekst uit `options`; truenas/apps f142a16, library 2.3.18, `NfsVolume`), en welke
   NFS-server en -opties een catalogusapp mag gebruiken is niet besloten. Daarom geeft in de waarden van een
   catalogusapp elke opslagregel van type `nfs` en elke niet-lege `nfs_config` (genormaliseerde sleutel en typewaarde,
   ook in een lijst en op elke diepte; leeg is alleen afwezig, `null` of `{}`) bewust de bestaande code
   `opslag_verboden`. Het exportpad (`path` direct in zo'n `nfs_config`) krijgt niet meer ook `hostpad_verboden`; dat
   is geen verzwakking, want die uitzondering geldt alleen naast `opslag_verboden` op die `nfs_config`, en elk ander
   pad houdt de hostpadregel. `cifs_config.path` is niet geraakt. Bij de standaard Custom App was nfs al
   `opslag_verboden` (alleen `host_path`, `ix_volume` en `tmpfs`; een niet-lege `nfs_config` is een config van een
   ander type); dat blijft zo en is niet tegenstrijdig met de witte lijst van KLEIN-80 (`nfs_config` staat daar als
   sleutel op, alleen leeg). Geen geldige payload gebruikt nfs: appstore-en-fork kent alleen `host_path`, `ix_volume`
   en `tmpfs`, de 9 opnieuw vertaalde payloads van de manifesten bevatten geen nfs, en in de catalogus van TrueNAS
   (truenas/apps f142a16, 500 `questions.yaml`) is nfs alleen een keuze van de variabele `type` (493 keer) en nergens
   de standaardwaarde. Deze weigering moet weer open bij S-P2-050, met een witte lijst per catalogusapp (welke
   NFS-servers, exportpaden en mountopties; ook komma-injectie in `server` en `options`, zoals bij SMB). `policy/*.yaml`
   en de `policy_hash` veranderen niet; restrisico executor-image: zie "Engine-regels buiten de `policy_hash`".
   Afgeleid uit de bron; NIET GEVALIDEERD (echte NAS).
   Verduidelijking 2026-11-14 (KLEIN-84; bevinding R-EERLIJK-1 van de controle van KLEIN-83): de zin "elk ander pad
   houdt de hostpadregel" hierboven is te sterk. De uitzondering wordt vastgelegd op de padtekst van het exportpad
   (de keten van sleutels, met punten aan elkaar gezet), niet op het object zelf. Heeft een sleutel een punt in de
   naam (bijvoorbeeld een sleutel `m.nfs_config` naast een sleutel `m` met daarin een `nfs_config`), dan kan een ander
   pad dezelfde padtekst krijgen als een exportpad; afhankelijk van de volgorde van de sleutels valt de melding
   `hostpad_verboden` voor dat andere pad dan weg. Het verzoek wordt in dat geval altijd ook geweigerd met
   `opslag_verboden` op die padtekst, dus wat geweigerd wordt verandert niet (geen veiligheidsgevolg); alleen de
   lijst met meldingen kan korter zijn. Juist is daarom: elk ander pad met een andere padtekst houdt de hostpadregel.
   Code, tests, `policy/*.yaml` en de `policy_hash` veranderen hierdoor niet.
   **Opslag: geen bovengrens voor `tmpfs_config.size` (aanvulling 2026-11-14, KLEIN-85; besluit van de gebruiker
   2026-11-14).** Dat `tmpfs_config.size` bij de standaard Custom App alleen een ondergrens heeft (een geheel getal van
   minstens 1 MiB, anders `bereik`) en geen bovengrens, is een bewuste keuze, geen open punt. Code, tests,
   `policy/*.yaml` en de `policy_hash` veranderen hierdoor niet.
7. **`app.uninstall` is container-only.** `app.delete` met `remove_ix_volumes: false` en `remove_images: false`;
   datasets en data blijven. Er is geen actie die data verwijdert.
8. **Terugzetten.** Custom App: `app.update` met de vorige waarden. Die waarden leest alleen de executor
   (`app.config`), en hij bewaart ze versleuteld in zijn eigen opslag bij het `request_id` van de update;
   `app.rollback` verwijst met `herstel_van` naar dat `request_id`. De Hub ziet de app-configuratie nooit.
   Catalogusapp: `app.rollback` naar een eerder geïnstalleerde versie.
   **Hercontrole bij terugzetten, alleen melden (aanvulling 2026-11-14, KLEIN-85; vervolgpunt van R-VEILIG bij
   KLEIN-80; besluit van de gebruiker 2026-11-14).** De bewaarde vorige waarden gingen zonder nieuwe parametercontrole
   naar `app.update`. Nu haalt de executor ze vóór het terugzetten door dezelfde `validate_parameters` als een
   installatie van de standaard Custom App (`app.install`, schema `app_install`); alleen de fouten in de waarden zelf
   tellen (en grootte of diepte). Het install-manifest kent de executor niet, dus de uitzonderingen daaruit (digest
   buiten de tag, `host_network_reason`, GPU) tellen hier niet mee en kunnen een melding geven. Een overtreding wordt
   alleen vastgelegd: één logregel (logger `executor.uitvoeren`, met `request_id`, `herstel_van`, aantal en codes),
   de waarschuwing `herstelwaarden_buiten_beleid` en het veld `hercontrole` (`overtredingen`, `codes`) in het antwoord
   (de Hub bewaart `waarschuwingen` in het resultaat van het verzoek), en de codes in `detail` van het journaal; nooit
   een waarde of geheim. Het terugzetten gaat altijd door met precies dezelfde waarden en dezelfde aanroep naar TrueNAS,
   ook als de hercontrole zelf faalt (code `hercontrole_niet_mogelijk`): bestaande apps blijven altijd terug te zetten.
   Zonder overtreding verandert er niets (geen waarschuwing, geen veld, geen logregel). De Hub doet geen hercontrole:
   hij ziet de bewaarde waarden nooit. `policy/*.yaml` en de `policy_hash` veranderen niet. Sim-getest (nep-TrueNAS);
   of de waarden die een echte TrueNAS in `app.config` teruggeeft vanzelf meldingen geven, is NIET GEVALIDEERD (echte
   NAS). Aanvulling 2026-11-14 (KLEIN-86; bevinding R-EERLIJK-2 van de controle van KLEIN-85): de hercontrole zit in de
   executor en werkt op de NAS pas na een nieuw gebouwd en uitgerold executor-image (zoals bij KLEIN-80, KLEIN-81 en
   KLEIN-83; zie "Engine-regels buiten de `policy_hash`"); een oude executor zet terug zonder hercontrole en meldt
   niets. Code, tests, `policy/*.yaml` en de `policy_hash` veranderen hierdoor niet.
9. **`resource_etag`.** Een hash over naam, staat, catalogusapp, trein, versie, `custom_app`, images en digests uit
   `app.query` + `app.image.query`. Hub en executor rekenen hem met dezelfde functie uit hun eigen readback. De
   app-configuratie telt niet mee (geheimen; de alleen-lezen-key van de Hub leest hem niet).
10. **Goedkeuring (B01-007, EX19, EX20).** Gebonden aan `preview_hash`, `resource_etag`, `policy_hash`,
    `action_scope` en risicoklasse; hooguit 15 minuten; `one_time_nonce` eenmalig. De beheerder stuurt bij goedkeuren
    de drie hashes mee die hij zag; wijkt er één af, dan `409` en een nieuwe preview. Vlak vóór uitvoering rekent de
    Hub alles opnieuw uit; een gewijzigd gebonden veld laat de goedkeuring vervallen. De nonce wordt atomair in de
    database verbruikt vóór er iets naar de executor gaat; de executor houdt in zijn eigen SQLite bij welke nonces hij
    zag. Goedkeuren kan alleen een beheerder (rol `admin`); een AI-, flow- of dienst-actor nooit.
11. **Dynamische blokkades (EX11, EX12).** De Hub leidt ze af van de bestaande gates (ADR-0007), zonder die te
    dupliceren: R2/R3 vraagt gate `r2_r3_acties`; een `opslagmutatie` vraagt `data_mutatie`; `app.install` vraagt
    `deployment`; `app.update`/`app.rollback` vragen `bestaande_app_updates`. Pool niet `ONLINE`/onbekend →
    `pool_niet_gezond`; back-upgate niet groen → `backup_gate_rood`. Onbekend telt nooit als groen en er is geen
    override. De executor controleert de pools bij een opslagmutatie zelf opnieuw via `pool.query`.
12. **Herstelpunt (B12-006).** Acties met `requires_backup` vragen een `backup_checkpoint_id` van een geverifieerd
    herstelpunt van de app. Die herstelpunten per app bestaan nog niet (B12, later deel): tot dan is zo'n actie
    geblokkeerd met `backup_checkpoint_ontbreekt`. Veiligste lezing; nooit een verzonnen herstelpunt.
13. **Schrijfsleutel op de executorpagina (§3.9).** Het vaste Peil-sjabloon van de executorpagina heeft alleen een
    veld voor de sleutel, niet voor een NAS-adres of vingerafdruk. Daarom:
    - **NAS-adres.** Uit `EXECUTOR_TRUENAS_HOST` (+ `EXECUTOR_TRUENAS_PORT`, standaard 443) als die gezet is; anders
      het IP-adres waarop de beheerder de pagina opent (de `Host`-header, al beperkt door de Host-controle). Een
      hostnaam of loopback-adres zonder instelling geeft `nas_adres_onbekend`; er wordt niets geraden.
    - **Twee stappen.** Stap 1 doet alleen een TLS-handdruk (geen login, de sleutel gaat niet over de lijn) en toont
      adres en SHA-256-vingerafdruk van het certificaat. Stap 2 (dezelfde sleutel opnieuw, binnen 15 minuten) stuurt
      de sleutel alleen over een verbinding met precies die vingerafdruk. Live test: `auth.login_with_api_key`,
      rolcontrole via `auth.me` en `core.get_methods`. Dit is vertrouwen bij eerste gebruik: de beheerder vergelijkt
      de vingerafdruk met die in TrueNAS. Na een ontkoppeling (zie **Ontkoppelen**) is er geen stap 1 meer: adres en
      vingerafdruk liggen al vast, en de nieuwe sleutel wordt in één stap live getest tegen precies dat adres en die
      vingerafdruk, nooit tegen het adres van de pagina of een gewijzigde `EXECUTOR_TRUENAS_HOST`.
    - **Rollen (S-P2-020, R-TECH-1).** Een sleutel telt alleen als schrijfsleutel als zijn rollen de app- **én**
      snapshotacties van de allowlist dekken: `FULL_ADMIN`, of `APPS_WRITE` samen met `SNAPSHOT_WRITE`. Een
      alleen-lezen-sleutel geeft `schrijfrechten_ontbreken`; alleen `APPS_WRITE` of alleen `SNAPSHOT_WRITE` geeft
      `schrijfrechten_onvolledig` (vaste melding, niets opgeslagen, nooit "Gezond"). De rolnamen en welke rol welke
      methode mag, komen uit de publieke API-beschrijving: **NIET GEVALIDEERD (echte NAS)**. De nep-TrueNAS dwingt
      dezelfde indeling per methode af.
    - **`core.get_methods` bij het instellen (S-P2-020, R-TECH-7)** is alleen een controle dat de sleutel die methode
      mag aanroepen: faalt de aanroep, dan wordt de sleutel geweigerd. De lijst zelf wordt hier niet gebruikt; bij elke
      uitvoering vraagt de executor de methoden opnieuw op (besluit 15).
    - **Opslag.** Versleuteld (AES-256-GCM met `vault.key`) in `/appdata/secrets/naslink.json` (0600); pagina en
      `/api/v1/status` tonen alleen de laatste 4 tekens. De Hub ziet de sleutel nooit.
    - **Vastgelegd.** Adres en vingerafdruk liggen na de eerste keer vast. Vervangen van de sleutel, vrijgeven na een
      afwijking en ontkoppelen van de Hub (`POST /beheer`) vragen de **huidige** sleutel, live geverifieerd tegen het
      vastgelegde adres en de vastgelegde vingerafdruk. Het formulier kent geen adres- of certificaatveld; een ander
      certificaat geeft `certificaat_gewijzigd` zonder login. Een ander adres of certificaat vraagt een nieuwe
      datamap (herinstallatie van de executor-app).
    - **Bewijs = alleen de huidige sleutel (S-P2-020, BN-2 a).** De executor ontsleutelt de opgeslagen sleutel en
      vergelijkt het bewijs daarmee in constante tijd, vóór er iets naar TrueNAS gaat. Een andere sleutel, ook een
      geldige schrijfsleutel of een sleutel met alleen `SNAPSHOT_WRITE`, geeft `sleutel_niet_huidig` (400); een
      onleesbare opslag of een `vault.key` die de sleutel niet opent geeft `sleutelopslag_onleesbaar` (409). In beide
      gevallen verandert er niets. Pas daarna volgt de live test. Is de huidige sleutel in TrueNAS ingetrokken (of zijn
      zijn rechten weg), dan weigert TrueNAS hem en kan vervangen, vrijgeven of ontkoppelen niet meer op de pagina:
      dan is herinstallatie met een nieuwe datamap nodig.
    - **Ontkoppelen (S-P2-020, R-VEILIG-1, BN-1 a; tussenstap).** Na het bewijs met de huidige sleutel wist de
      executor eerst de schrijfsleutel en daarna de Hub-koppeling. Adres en vingerafdruk van TrueNAS blijven vast.
      `hub-link.json` gaat naar `state: ontkoppeld`: service-token weg, pins naar `previous_pins` (alleen audit),
      `first_linked_at` blijft altijd staan (§3.5, §3.8). Een onleesbaar `hub-link.json` wordt eerst bewaard als
      `hub-link.json.onleesbaar-<UTC-tijd>` (0600) met `unreadable_replaced_at`; `first_linked_at` is dan het moment
      van vervangen (de echte waarde is niet te lezen). In `ontkoppeld` komt het bestaande koppelformulier terug,
      maar alleen zolang er geen sleutel ligt; daarna stelt de beheerder de sleutel opnieuw in met het bestaande
      sleutelformulier, tegen het vastgelegde adres en de vastgelegde vingerafdruk. Tot dan voert de executor niets
      uit (`capability_unavailable`, reden `schrijfsleutel_ontbreekt`), ook niet voor een nieuw gekoppelde Hub.
      **Afwijking van §3.9 letterlijk:** opnieuw koppelen na een ontkoppeling gaat zonder sleutelbewijs. Wie op het
      LAN de pagina bereikt, kan in dat venster de executor aan een eigen Hub koppelen, maar die Hub krijgt geen
      rechten: er is geen schrijfsleutel, en een nieuwe sleutel werkt alleen als hij op het vastgelegde NAS-adres en
      certificaat schrijfrechten heeft (zoals het restrisico van §3.7: "de dienst heeft dan nog geen data of
      rechten"). De pagina toont adres en vingerafdruk van de gekoppelde Hub, met een vaste melding: vul de sleutel
      alleen in als dat jouw Hub is. Is het een andere Hub, dan is er zonder sleutel geen beheerformulier: herstel
      is een nieuwe datamap (of de sleutel instellen en direct ontkoppelen; in dat korte venster kan die Hub wel
      acties aanbieden, dus dat raden de docs niet aan). De volledige
      vorm (opnieuw koppelen mét sleutelbewijs in het koppelformulier, plus een eigen vrijgeefknop) vraagt een nieuwe
      Peil-versie van de statuspagina en is een eigen latere stap (zie Open punten). `POST /api/v1/hub-link/unlink`
      vanuit de Hub (§3.8) blijft `501 capability_unavailable`: §3.9 eist bewijs met de schrijfsleutel en de Hub mag
      die sleutel nooit zien.
    - **Fail-closed.** Onleesbare sleutelopslag: geen formulieren, niets wordt overschreven, uitvoeren geeft
      `schrijfsleutel_onleesbaar` (503). Onleesbaar is ook een `vault.key` die de opgeslagen sleutel niet opent (bv.
      verloren en bij de start opnieuw gemaakt): status en pagina openen de sleutel echt en tonen dan
      `sleutelopslag_onleesbaar`, nooit "Gezond" of "uitvoeren mogelijk" (S-P2-020, R-TECH-2). Onleesbare koppelstatus
      met een werkende sleutel: alleen het beheerformulier, als herstelroute (ontkoppelen, daarna opnieuw koppelen).
      Een schijf- of rechtenfout bij opslaan of ontkoppelen geeft `sleutelopslag_niet_schrijfbaar` (503) met een vaste
      melding, nooit een kale 500; is de sleutel net in een ander tabblad ingesteld, dan `sleutel_al_ingesteld` (409)
      (S-P2-020, R-TECH-4 en R-TECH-9).
    - **Log (S-P2-020, R-VEILIG-3 en R-VEILIG-4).** Elke afgehandelde poging op de pagina geeft één regel met code en
      trace-ID: `python -m executor api` geeft de logger `executor` een eigen handler op INFO (stdout), los van root.
      De websocket-verbinding met TrueNAS logt via een eigen logger die vast op INFO staat; websockets logt op DEBUG
      elk frame (ook de aanmelding met de sleutel), en dat komt zo nooit in een log, ook niet met root op DEBUG.
    - **Restrisico.** Tussen koppelen en het instellen van de sleutel kan iemand op het LAN die de pagina bereikt de
      executor aan een ander adres binden (alleen via het IP in de `Host`-header en alleen met een sleutel die op dát
      adres schrijfrechten heeft). Dat levert geen rechten op de echte NAS op; het blokkeert de executor tot een
      herinstallatie. Mitigatie: `EXECUTOR_TRUENAS_HOST` zetten, de getoonde vingerafdruk controleren, en de
      bestaande herkomst-, formuliercode- en pogingenregels (§3.7).
14. **Afwijking → stop + incident.** Wijkt de readback af van de verwachting (staat, aanwezigheid, digest) of is de
    uitkomst onbekend (time-out of verbroken verbinding ná de aanroep), dan zet de executor zichzelf op "gestopt" en
    weigert hij elke volgende uitvoering (`executor_gestopt`) tot een beheerder hem op de executorpagina vrijgeeft.
    Het sjabloon heeft geen aparte vrijgaveknop: vrijgeven is "Sleutel vervangen" met de huidige sleutel en een leeg
    veld voor de nieuwe sleutel. "Sleutel vervangen" met een nieuwe sleutel geeft nooit vrij; de executor blijft dan
    gestopt (S-P2-020, R-TECH-5). Ontkoppelen laat een stop ook staan. Het antwoord aan de Hub is `afwijking`; de Hub legt een incident vast en zet de
    actie op `afwijking`. Geen automatische herhaling. Weigert TrueNAS de aanroep en is het doel aantoonbaar
    onveranderd, dan is het `uitvoering_mislukt` zonder stop. Een onleesbaar journaal telt als gestopt: vóór de
    aanroep `journaal_niet_beschikbaar` (er is niets uitgevoerd), erna `afwijking`.
    Aanvulling 2026-11-15 (S-P2-030, herstel R-TECH-1, R-VEILIG-1 en R-VEILIG-2): "TrueNAS weigert de aanroep" betekent
    alleen een foutantwoord op de schrijfaanroep zelf (geen job) of een job die `FAILED`/`ABORTED` meldt. Heeft TrueNAS
    de aanroep aangenomen (er is een job-id) en faalt daarna het opvragen van de jobstatus, dan is de uitkomst
    onbekend (`job_status_onbekend` → `afwijking`, stop); ook elke andere onverwachte fout of elk onverwacht antwoord
    ná de schrijfaanroep is een onbekende uitkomst. De stop is duurzaam: de stop en het einde van de journaalrij staan
    in één transactie (de stop eerst); lukt vastleggen niet, dan houdt de executor de stop in het geheugen tot het
    journaal weer werkt (en voert tot dan niets uit); viel het journaal ná de aanroep weg, dan staat de stop daarna
    vast als `uitkomst_onbekend` (het antwoord noemt `journaal_niet_beschikbaar`). Bij het starten en vóór elke uitvoering telt een journaalrij
    `gestart` zonder einde (het proces viel weg ná de aanroep) als onbekende uitkomst (de rij krijgt `afwijking` met
    `uitkomst_onbekend`, de executor stopt), en een `afwijking` van na de laatste vrijgave zonder vastgelegde stop
    geeft alsnog de stop. De vrijgave (bestaande weg, zie hierboven) legt vast tot welke journaalrij is vrijgegeven
    (`vrijgegeven_tot`). Gevolg bij de eerste start met deze versie: een `afwijking` uit een eerder journaal die al
    was vrijgegeven, heeft nog geen grens en geeft één keer opnieuw een stop; vrijgeven heft die op. Een stop raakt
    nooit een app: alleen de executor weigert verdere acties. Eén proces per datamap: een rij `gestart` die niet van
    een lopende uitvoering in dit proces is, telt als onafgemaakt. Het journaal (`detail`) bewaart van een fout van
    TrueNAS alleen de stabiele code en de foutnaam of jobstatus, nooit de vrije fouttekst (R-VEILIG-4); te diep
    geneste JSON geeft `422 validation_error` (R-VEILIG-3).
    Aanvulling 2026-11-15 (S-P2-030, herstelronde 2, R-VEILIG-H1 en R-VEILIG-H2): de lopende uitvoeringen worden binnen
    de schrijftransactie gelezen die een onafgemaakte rij als stop vastlegt (na `BEGIN IMMEDIATE`); een uitvoering die
    net begint, telt zo nooit als weggevallen. Die vaststelling gebeurt alleen bij het starten, vóór een uitvoering en
    bij het vrijgeven. De statusopvragen (`GET /api/v1/status`, `GET /`, `GET /api/v1/executions/{request_id}`) lezen
    alleen (geen schrijftransactie): een onaangemelde opvraag kan de executor dus niet stilleggen. Valt het journaal
    weg vóór de schrijfaanroep, dan is er aantoonbaar niets naar TrueNAS gestuurd: de rij krijgt het einde `mislukt`
    zodra het journaal weer werkt, zonder stop (zolang het proces blijft draaien; na een herstart in die tussentijd telt
    de rij als onafgemaakt en volgt een stop, dicht bij twijfel).
15. **Methoden per TrueNAS-versie.** De executor vraagt `core.get_methods` op en kiest de eerste methode uit
    `acties.yaml` die bestaat (bv. `pool.snapshot.create`, anders `zfs.snapshot.create`). Bestaat er geen, dan
    `capability_unavailable`; nooit gesimuleerd succes. Welke versie welke naam kent is niet op een echte NAS
    vastgesteld: de fake kent beide varianten, de lijst in het beleid is een aanname uit de publieke API-beschrijving
    (**NIET GEVALIDEERD (echte NAS)**).
16. **Noodstop.** Een instelling van de Hub (`acties.noodstop`) die elke nieuwe uitvoering blokkeert. Alleen een
    beheerder zet hem; het is geen `action_id`.
17. **Uitvoerders buiten de executor.** `notification.send` (R0) loopt via de Gotify-adapter van de Hub.
    `sso.*` hoort bij de eigenaar-connector van `home-control-hub`; zolang die geen `/connector/v1/apply` aanbiedt,
    geeft de Hub `capability_unavailable`.
18. **Hub-routes voor voorstellen en goedkeuringen (B01-007).** Contract §8 legt de objecten vast, niet de routes.
    Gekozen, alles onder `/api/v1` en alleen voor gebruikerssessies:

    | Route | Rol | Doet |
    |---|---|---|
    | `GET /policy` | kijker | beleid, klassen, blokkades en `policy_hash` (alleen-lezen) |
    | `POST /actions` | operator | voorstel → classificatie, preview en drie hashes; er wordt niets uitgevoerd |
    | `GET /actions`, `GET /actions/{request_id}` | kijker | voorstellen met preview, blokkades, goedkeuring, uitkomst |
    | `POST /actions/{request_id}/approve` | beheerder | R2/R3 goedkeuren voor precies de getoonde hashes |
    | `POST /actions/{request_id}/reject` | beheerder | afwijzen met reden |
    | `POST /actions/{request_id}/execute` | operator (R2/R3: beheerder) | opnieuw controleren, ondertekenen, uitvoeren |
    | `POST /actions/{request_id}/reconcile` | operator | onbekende uitkomst ophelderen (alleen lezen) |
    | `GET`/`PUT /actions/noodstop` | kijker / beheerder | noodstop lezen / zetten |

    De rol kind heeft geen toegang. `request_id` = de `Idempotency-Key` van het voorstel (het `idempotency_key` van
    contract §8); staat hij ook in de body, dan moet hij gelijk zijn. Voorstellen door diensten, flows of de AI
    krijgen later een eigen ingang met een eigen dienstscope; tot dan bestaat die weg niet (dus ook geen AI-actor die
    iets kan goedkeuren of uitvoeren).
19. **Statussen.** `klaar` (R0/R1, direct uitvoerbaar), `wacht_op_goedkeuring`, `goedgekeurd`, `afgewezen`,
    `geweigerd` (beleid), `bezig`, `uitgevoerd`, `mislukt` (toestand aantoonbaar onveranderd), `afwijking`, `onbekend`
    en `verlopen`. Een geweigerd voorstel wordt wél vastgelegd (wie, wat, welke regel), maar zonder parameterwaarden:
    alleen hun hash. Een voorstel dat het schema niet haalt (422) of waarvan het doel niet te lezen is, wordt niet
    opgeslagen.
20. **Twee keer classificeren.** Eerst zonder de NAS (verboden, boiler, gereserveerd, onbekend, schema), daarna met de
    eigen readback van het doel (kritieke of beschermde app). Kan de Hub het doel niet lezen, dan `409 doel_onbekend`:
    onbekend telt nooit als ongewijzigd, en zonder readback is er geen preview en geen `resource_etag`.
21. **Herkenning op naam, catalogusapp én image; dicht bij twijfel.** Wijzen de appnaam, de catalogusapp
    (`metadata.name`, behalve `ix-app`) en de image naar verschillende bekende apps, dan gelden de regels van allemaal
    (`recognize_all`); de strengste wint. Zo verliest een app met de naam `emby` de Emby-bescherming niet door een
    andere image, en wordt een kritieke app niet R1 doordat zijn image op een gewone app lijkt. TrueNAS toont bij een
    gestopte app geen image (lege `active_workloads`; middleware `plugins/apps/ix_apps/query.py`, `list_apps`, gelezen
    in release/25.04.2 en release/25.10.0, NIET GEVALIDEERD op een echte NAS). Een catalogusapp blijft herkenbaar aan
    zijn catalogusnaam: de catalogus legt zijn images vast en het formulier laat hooguit kiezen uit die images, nooit
    een eigen repository (gelezen in `truenas/apps`, o.a. emby, plex en jellyfin). Is van een bestaande app niet vast
    te stellen wat erin draait (geen image te zien en geen catalogusapp, zoals een gestopte Custom App), dan weigert
    het beleid elke actie op die app (`DOEL-ONHERKENBAAR`, `doel_niet_herkenbaar`), ook met goedkeuring: het kan Emby,
    MediaGuard of de mediaserver onder een andere naam zijn. Gevolg: een gestopte Custom App start, wijzigt of
    verwijdert het platform niet. Hub en executor gebruiken dezelfde functie (`herken_app`) op hun eigen readback; de
    nagebootste TrueNAS in de tests geeft bij een gestopte app dezelfde lege `active_workloads`.
    **Stoppen van een Custom App is daarom eenrichtingsverkeer** (besluit van de gebruiker, 2026-11-11: "stoppen met
    goedkeuring"). Elke app die het platform zelf installeert, is een Custom App; na `app.stop` kan het platform zo'n
    app niet meer starten. Daarom is `app.stop` op een app die na het stoppen niet meer herkenbaar is (geen
    catalogusapp: ix-app of compose) altijd R2 (`STOP-EENRICHTING`, in de engine; `policy/*.yaml` en de
    `policy_hash` zijn ongewijzigd): een goedkeuring van een beheerder is verplicht en de stop gebeurt nooit
    automatisch, ook niet op voorstel van de AI, een flow of een runbook. Hub en executor rekenen dit allebei zelf
    uit; een verzoek met R1 weigert de executor (`risicoklasse_te_laag`). De preview zegt bij "terugdraaien" eerlijk
    dat weer starten daarna alleen in de TrueNAS-web-UI kan, en de runbooks (`schijf_vol`, `db_migratie_mislukt`)
    zeggen dat ook. `app.stop` op een catalogusapp blijft R1: die blijft gestopt herkenbaar en start gewoon weer.
    Aan de beschermde regels (Emby nooit; MediaGuard en de mediaserver geen update, terugzet of verwijdering zonder
    bewijs) verandert niets.
    `GET /api/v1/policy` toont naast de yaml-klasse ook de klasse voor een Custom App (`risk_class_custom_app`) en de
    vaste engine-regels (`engine_regels`), uitgerekend met de engine zelf; de runbooks noemen bij `app.stop`
    "Custom App: R2" (S-P2-010). `Herkenning.na_stop_herkenbaar` heeft geen standaardwaarde (dicht bij twijfel). Bij
    `app.install` telt ook de catalogusapp uit het voorstel (`app_create.catalog_app`, behalve `ix-app`) mee voor de
    herkenning, in Hub en executor: een tweede Emby onder een andere naam is ook Emby. Bij een bestaande app telt ook
    de image ná de actie mee: de nieuwe image bij `app.update`; bij `app.rollback` met `herstel_van` in de executor de
    bewaarde vorige image en in de Hub de images van vóór die wijziging uit de preview van dat verzoek. Een bestaande
    app omzetten naar een Emby-image is dus ook een tweede Emby; volledig is de herkenning alleen op wat er nu te zien
    is (S-P2-010). Zonder `Herkenning` (bv. een aanroep zonder readback) is `app.stop` op een app ook R2: niet bekend
    is dat de app gestopt herkenbaar blijft (dicht bij twijfel).
22. **Fout mét of zonder vastlegging.** Een weigering die de toestand van het verzoek verandert (goedkeuring vervallen,
    voorstel verlopen, uitvoering mislukt, afwijking, uitkomst onbekend) wordt samen met die wijziging vastgelegd en
    is daarna het idempotente antwoord op dezelfde sleutel. Elke andere fout laat de database ongemoeid.
23. **Welke goedkeuring telt.** Per verzoek is er hooguit één open goedkeuring; opnieuw goedkeuren laat de vorige
    vervallen (`vervangen`). De keuze van "de huidige" is volledig bepaald (open eerst, dan de laatst afgesloten),
    ook als twee goedkeuringen in dezelfde seconde vallen — anders zou een geldige goedkeuring bij toeval als
    vervallen gelden. Goedkeuren, afwijzen, uitvoeren en ophelderen vergrendelen de rij van het verzoek
    (`SELECT … FOR UPDATE`) tot het einde van hun transactie: twee gelijktijdige aanroepen op hetzelfde verzoek lopen
    na elkaar en de tweede krijgt `409 status_past_niet`. Bij uitvoeren blijven daarnaast de atomaire voorwaardelijke
    updates staan (nonce van de goedkeuring en status), zodat precies één uitvoering de executor bereikt. Het bijwerken
    van verlopen goedkeuringen en voorstellen (ook vanuit de leesroutes) raakt alleen verzoeken waarvan het de rij zelf
    kan vergrendelen (`FOR UPDATE SKIP LOCKED`) en controleert de voorwaarden daarna opnieuw: een gebruikte goedkeuring
    wordt nooit ook "verlopen", en een verzoek dat `bezig` is gaat nooit terug.
24. **Anti-flap voor iedereen.** Afkoeltijd en maximum per uur per (actie, doel) gelden ook voor een beheerder. Het
    contract zegt niet of ze alleen voor de AI gelden; dit is de veiligste lezing. Uitvoeren houdt per (actie, doel) een
    vergrendeling (`pg_advisory_xact_lock`) vast vanaf vlak vóór de controle van de blokkades tot het voorstel op
    `bezig` staat; zo zien twee voorstellen voor hetzelfde doel elkaars start ook als ze tegelijk worden uitgevoerd.
25. **Synchroon uitvoeren, nooit herhalen.** `execute` wacht op het antwoord van de executor (time-out van de actie
    plus marge). Komt er geen bruikbaar antwoord, dan is de status `onbekend`: de Hub herhaalt niets, want de nonce
    is verbruikt. `reconcile` leest het journaal van de executor (`GET /api/v1/executions/{request_id}`) en zet de
    status alleen op wat daar staat; zegt het journaal "nooit gezien" en is het `ExecutionRequest` verlopen, dan is
    er aantoonbaar niets uitgevoerd (`mislukt`).
26. **Incidenten.** Afwijking → kritiek incident per doel (`actie.afwijking`, vingerafdruk
    `ai-server-manager:actie_afwijking:<doel>`, elke keer een melding); sluit bij een latere geslaagde en gecontroleerde
    actie op hetzelfde doel. Onbekende uitkomst → waarschuwing per verzoek (`actie.uitkomst_onbekend`); sluit als de
    uitkomst is opgehelderd. Een nette weigering of een mislukte aanroep staat alleen in het auditspoor.
    Aanvulling 2026-11-15 (S-P2-040): het event `action.run.failed` neemt `reden` en `gestopt` over uit het antwoord
    van de executor (`409 afwijking`, `502 uitvoering_mislukt`) of, bij ophelderen, uit het journaal (`detail` en de
    stopstand van `GET /api/v1/executions/{request_id}`). Zo staat in het incident `actie.afwijking` ook waarom
    (bv. `journaal_niet_beschikbaar`, `uitkomst_onbekend`, `staat_verschilt`) en dat de executor gestopt is. `gestopt`
    komt alleen mee als de executor het zelf als ja/nee meldt; de Hub leidt het nooit af. Een onbekende jobstatus na de
    schrijfaanroep (`job_status_onbekend` in de executor) komt bij de Hub binnen als `reden` `uitkomst_onbekend`: de
    executor geeft die code door (S-P2-030), de Hub neemt over wat de executor zegt.
27. **Adres van de executor.** Uit de eigen inventaris (`app.query` + het NAS-adres van D03), met controle van de
    image-repository; nooit uit de `base_url` die een dienst zelf opgeeft. Niet gekoppeld of adres onbekend → er wordt
    niets ondertekend.
28. **Geheimen in installatiewaarden.** Waarden van omgevingsvariabelen staan nooit in een preview, log of audit
    (alleen de namen). Zolang een voorstel open is, bewaart de Hub ze in zijn database (nodig voor het uitvoeren); na
    afloop (uitgevoerd, mislukt, afwijking, onbekend, afgewezen, geweigerd of verlopen) wist hij ze daar, zodat ze
    niet voor altijd in klare tekst in de database en de back-up staan. Hetzelfde geldt voor de vrije tekst in
    `command`, `entrypoint`, `labels` en `notes` (`vrije_tekst_gewist` noemt de gewiste velden; S-P2-010). De namen
    en `parameters_sha256` blijven. Eigen waarden van een catalogusapp (buiten de ix-app-velden) wist de Hub nog
    niet; zie de open punten. Een
    verwijzing `vault://app/<app_id>/<parameter>` is het enige toegestane formaat; het invullen ervan door de executor
    bestaat nog niet, dus een installatie met zo'n verwijzing geeft eerlijk `501 capability_unavailable`.
29. **Testnaden.** Tests zetten alleen de *invoer* van de gates (`blokkades.gate_inputs`: besluiten, eigen back-up) en
    — voor `app.update`/`app.rollback` — een gesimuleerd herstelpunt (`blokkades.verified_checkpoint`); de
    beoordeling, de policy, de handtekening en de executor zijn de echte code.

30. **Vervaltijd: de goedkeuring, niet de preview (S-P2-040, besluit regisseur BN-040-A optie A).** De stap
    S-P2-040 noemt "preview hooguit 15 minuten geldig". Zo gelezen en zo gebouwd: de 15 minuten gelden voor de
    goedkeuring (`execreq.MAX_APPROVAL_SECONDS`, `Approval.expires_at`; besluit 10). Een voorstel blijft geldig tot
    `geldig_tot` (`expires_in_seconds`, standaard 3600, 60 tot 86400 seconden), maar de preview heeft geen eigen
    vervaltijd nodig: bij goedkeuren en vlak vóór uitvoeren rekent de Hub de preview opnieuw uit uit een verse
    readback, en elke afwijking geeft `409 preview_gewijzigd` (bij goedkeuren) of laat de goedkeuring vervallen (bij
    uitvoeren). Er wordt dus nooit uitgevoerd op een preview die ouder is dan de goedkeuring van hooguit 15 minuten.
    Geen gedragswijziging.
31. **Onbekend `action_id` geeft `403`, niet `422` (S-P2-040).** De staptekst van S-P2-040 noemt `422` voor een
    onbekend `action_id` of een doel buiten bereik. Gebouwd en gereviewd in S-P2-005 en S-P2-010: een onbekend
    `action_id` geeft `403 actie_niet_toegestaan`, een verboden patroon `403 actie_geweigerd`, een gereserveerde actie
    `501`; alleen een parameter of doel buiten het schema geeft `422 parameters_ongeldig`. Contract §8 zegt alleen
    "geweigerd". Dat blijft zo (besluit regisseur, S-P2-040); in alle gevallen wordt er niets uitgevoerd.
32. **Herstel na de review van S-P2-040 (aanvulling 2026-11-15; besluiten regisseur).** Alles Sim-getest; NIET
    GEVALIDEERD (echte NAS).
    - *Preview van een installatie toont elk gezet veld (R-VEILIG-1).* `wijziging.waarden` toont elk veld van
      `app_create.values` mét zijn waarde, volgens een vaste regel per veld van de standaard Custom App
      (`IX_PREVIEWREGELS` in `apps/api/src/hub/actions/preview.py`; een bewakingstest eist een regel voor elk veld
      van `IX_VALUES_KEYS`). Van `envs` alleen de namen (besluit 28). Een geheim (een waarde onder een
      geheim-achtige sleutel, of de `value` naast een geheim-achtige `name` of `key`) staat er als `***`, zoals
      overal in de API-uitvoer (`hub.redact`). Ook de eigen waarden van een catalogusapp staan er zo in. `labels` en
      `notes` staan er met waarde in zolang het voorstel open is; na afloop wist de Hub ze ook uit de bewaarde
      preview (`{"waarde_gewist": true}`), zoals uit de parameters (besluit 28); de `preview_hash` blijft de hash
      van wat is voorgesteld en goedgekeurd. Restpunt: een antwoord met die waarden bewaart de idempotentie-opslag
      hooguit een dag (de worker ruimt het daarna op).
    - *Eigen opdracht: optie C.* Een voorstel met `command` of `entrypoint` in de waarden van een installatie weigert
      de Hub met `501 capability_unavailable` (`details.reden` = `eigen_opdracht`, `details.velden`); er wordt niets
      voorgesteld of bewaard. Een open voorstel van vóór dit herstel met zo'n opdracht wordt bij goedkeuren of
      uitvoeren geweigerd (status `geweigerd`, vrije tekst gewist). Het beleid (`asm_policy`, `policy_hash`) is niet
      gewijzigd. Vervolgpunt: zie de open punten.
    - *"Uitgevoerd" alleen met bewijs (R-VEILIG-2).* De Hub legt `uitgevoerd` alleen vast als het antwoord
      `methode`, `before_hash`, `after_hash`, `uitgevoerd_op` en `policy_hash` (gelijk aan het eigen beleid) in de
      juiste vorm heeft. Anders is het een onduidelijk antwoord: `502 uitkomst_onbekend` (`reden`
      `executor_bewijs_onvolledig`), status `onbekend`, een incident `actie.uitkomst_onbekend`, en een open incident
      `actie.afwijking` blijft open. Bij ophelderen telt een journaalrij `uitgevoerd` alleen als hij van dit verzoek
      en deze actie is en `methode`, `before_hash`, `after_hash` en een einde in de juiste vorm heeft; anders blijft
      de uitkomst onbekend. Het journaal heeft geen `policy_hash`: de executor controleert die zelf vóór hij iets
      uitvoert.
    - *Witte lijst voor het antwoord van de executor (R-VEILIG-3).* Resultaat, audit, event en foutantwoord nemen van
      de executor alleen velden uit een vaste lijst over, elk met een vaste vorm en grootte (`_van_executor` in
      `service.py`): `reden`, `afwijkingen`, `methode`, `before_hash`, `after_hash` en `gestopt`, bij een weigering
      `reden`, `fouten`, `blokkades`, `gewijzigd`, `eigen_risk_class`, `methoden`, `sinds` en `request_id` (genest
      onder `executor`). De eigen velden van de Hub (`code`, `request_id`, `doel`, `uitkomst`, `action_id`,
      `risk_class`) zet de Hub zelf; ze zijn niet te overschrijven. `reden` is altijd een code met een vast
      tekenpatroon (zoals `staat_verschilt` of `job_mislukt [FAILED]`), anders `onbekende_reden`; `gestopt` gaat
      alleen mee als echte ja/nee. Een object of lijst mag hooguit 8192 tekens JSON zijn en geen stuurtekens bevatten
      (anders `null`); de melding hooguit 500 tekens (anders `null`). Een weigering met een code buiten het vaste patroon is
      geen bruikbaar antwoord: uitkomst onbekend. Zo komen vrije tekst, een NUL-teken (eerder HTTP 500) en een
      reusachtig antwoord nergens meer terecht.
    - *Noodstop (R-VEILIG-4).* `PUT /api/v1/actions/noodstop` zet de stand altijd echt, ook bij een herhaling met
      dezelfde `Idempotency-Key`, en geeft de werkelijke stand terug (geen bewaard antwoord van toen). Dezelfde
      sleutel voor een ander verzoek blijft `422 idempotency_key_reused`.
    - *Incident (R-TECH).* De titel van `actie.afwijking` zegt "executor gestopt" alleen als het event `gestopt` echt
      `true` heeft; bij `false` of zonder `gestopt` zegt de samenvatting dat ook.
    - *Aanvulling 2026-11-16 (herstelronde 2; R-VEILIG-5, -6 en -7; besluiten regisseur).* (a) Ook een geheim-achtige
      sleutel direct onder `values` van een catalogusapp staat er als `***`, niet alleen een geneste. (b) Van elk paar
      `name` + `value` in de waarden (zoals `additional_envs` van een catalogusapp) staat alleen de naam erin; de
      waarde is altijd `***`, ook bij een naam die niet op een geheim lijkt (besluit 28). Een paar `key` + `value`
      (zoals `labels`) houdt de regel hierboven. Er blijft dan ook na afloop niets van achter in de bewaarde preview.
      (c) Noodstop: een herhaling met dezelfde `Idempotency-Key` zet alleen de veilige kant opnieuw. Een herhaald
      aan-verzoek zet de noodstop echt aan; een herhaald uit-verzoek wijzigt niets (geen audit) en geeft de werkelijke
      stand terug, zodat het een noodstop die een ander daarna zette niet opheft. Beleid en `policy_hash` ongewijzigd.
    - *Aanvulling 2026-11-16 (herstelronde 3; R-VEILIG-8 en besluit regisseur).* Bij een catalogusapp staan van een
      omgevingsvariabele ook in andere vormen alleen de namen in de preview: onder een sleutel `environment`, `env` of
      `envs` (ook met hoofdletters) een object met elke waarde als `***` en in een lijst een tekst `NAAM=waarde` als
      `NAAM`; een paar `name` + `value` ook met hoofdletters (`Name`/`Value`) en direct onder `values`. Leeg en ja/nee
      blijven zichtbaar. Tests eisen nu ook `***` voor een label met een geheim-achtige `key` en voor een geheim dat
      een getal, lijst of object is. Beleid en `policy_hash` ongewijzigd.
    - *Aanvulling 2026-11-17 (herstelronde 4; R-VEILIG-9 t/m 13; besluit regisseur): één principe in plaats van een
      opsomming.* De Hub stuurt de hele `wijziging` van elke actie door één toonfunctie (`_toon` in
      `apps/api/src/hub/actions/preview.py`); er staat geen rauw veld meer in, ook niet `resources`, het
      herstartbeleid, poorten, opslag of de redenen en controles uit het manifest. Een bewakingstest
      (`apps/api/tests/unit/test_preview_toon.py`) plant per actie een geheim in elke bron van `wijziging` en is rood
      als er een veld bijkomt dat niet door de toonfunctie gaat. De regel: (1) de waarde onder een geheim-achtige
      sleutel is `***`; (2) een paar is een object met een naam (`name` of `key`) én een `value`, herkend in elke
      schrijfwijze en genormaliseerd zoals `_nk` in het beleid; bij een `name` (of een geheim-achtige `key`) is de
      `value` `***`; (3) onder elke sleutel met een omgevingsbetekenis (genormaliseerd bevat hij `env`, zoals
      `additional_envs`, `env_vars` en `environment_variables`, of het Nederlandse `omgeving`) staan alleen namen: een
      object met zijn sleutels en `***`, een paar met alleen zijn naam, een tekst per regel als de naam vóór `=` of
      `:` (zonder scheiding de hele regel) als die op een variabelenaam lijkt (`^[A-Za-z_][A-Za-z0-9_]*`), anders
      `***`; (4) elke andere tekst, ook een sleutel, gaat door `redact_text` (URL met wachtwoord, `Bearer`); (5) leeg
      en ja/nee blijven zichtbaar, net als poorten, opslag, labels zonder geheim, `run_as` en `dns_config`. Een losse
      naam zonder scheiding (zoals `env: production`) blijft dus zichtbaar. De vorm van de preview verandert alleen
      waar een geheim stond; een open voorstel met zo'n vorm krijgt bij goedkeuren een nieuwe `preview_hash` (409 en
      een nieuwe diff, besluit 9). Beleid en `policy_hash` ongewijzigd.
    - *Aanvulling 2026-11-17 (herstelronde 5; R-VEILIG-14 t/m 17 en W3; besluit regisseur): hetzelfde principe,
      scherper.* (1) Een sleutelnaam is ook geheim-achtig als `hub.redact` hem genormaliseerd herkent (`api.key` wordt
      `apikey`), als hij genormaliseerd op `key` eindigt (`encryption_key`, `license.key`, `access-key`), als hij `pwd`
      bevat of als `auth` een los deel is; de kale `key` (de naam van een labelpaar) niet. (2) `redact_text` herkent
      ook een URL met een lege gebruikersnaam (`redis://:wachtwoord@host`); dat geldt ook voor audit en events. (3) Een
      omgevingscontext is er alleen als een heel deel van de sleutel (gescheiden door `_ . -` of een
      hoofdletterovergang) `env`, `envs`, `environment(s)` of `omgeving` is, of een samenstelling daarvan met
      `vars`/`variables`/`variabelen` (`envvars`, `omgevingsvariabelen`); onder `openvpn`, `envoy` of `venv` blijven
      poort, server en hostpad zichtbaar. (4) In een omgevingscontext staat per regel een naam (vóór `=` of `:`, of de
      hele regel) alleen als hij op een variabelenaam lijkt, hooguit 64 tekens is en niet willekeurig: willekeurig is
      een woord met een cijfer én hoofd- en kleine letters, of met een cijfer en een entropie van minstens 4,0 (de
      drempel van `_maybe_secret`), of een hexreeks van minstens 16 tekens; anders `***`. Een '='-staart (base64) helpt
      dus niet, en een regel zonder naam is `***`. De sleutels van een omgevingsobject volgen dezelfde regel
      (`NAAM=geheim` als sleutel wordt `NAAM`). (5) Ook `huidig` (de readback van de NAS) gaat door de toonfunctie;
      alleen `target` en `resource_etag` blijven bewust rauw (met de reden in de bewakingstest, die nu de hele preview
      doorzoekt en rood wordt bij een nieuw veld). **Restvorm die bewust blijft:** onder een omgevingssleutel een geheim
      dat op een naam lijkt: zonder cijfer (`geheimwoord`, `GeheimWoord`), of met een cijfer maar in één kast en met
      lage entropie (`wachtwoord2024`); een sleutel die `env` zonder scheiding in een ander woord plakt
      (`additionalenvs`, `dotenv`) is geen omgevingscontext (een paar `name`/`value` blijft daar wel verborgen); een
      geheim in de vrije tekst van een gewoon veld (`notes`, een labelwaarde) zonder URL-wachtwoord of `Bearer`; de
      vrije tekst `target.resource` van een eigenaarsactie. Beleid en `policy_hash` ongewijzigd.

## Open punten

- **Eigen opdracht bij een installatie (S-P2-040, besluit regisseur optie C; besluit 32).** De Hub weigert `command`
  en `entrypoint` tot er een installatiescherm is dat ze veilig kan tonen (UI-stappen S-P2-170 en S-P2-180). Daar
  opnieuw besluiten hoe: de inhoud tonen (en na afloop wissen) of alleen "gezet", lengte en SHA-256. Tot dan kan een
  installatie met een eigen opdracht niet via de Hub.

- **Hub stuurt op `ready_for_install` en `conflicts.status` van de appstore-preview (R-VEILIG-11 uit S-P2-520).**
  De Hub roept de preview van appstore-en-fork nu nergens aan. Doorgeschoven naar de stappen waarin die aanroep
  ontstaat (S-P2-050 en S-P2-080; besluit regisseur BN-040-B optie B, S-P2-040): daar stuurt de Hub op
  `ready_for_install` en `conflicts.status`, niet op `preview_hash` alleen.

- **Schermen in de Hub-UI.** De API is er; het goedkeuringsscherm (preview, hashes, goedkeuren/afwijzen, uitvoeren,
  noodstop) is nog niet gebouwd. Tot dan is het voor een gebruiker niet te bedienen: elke wijzigende aanroep vraagt
  de header `X-CSRF-Token` bij de sessie, en de API-documentatie (`/api/docs`) stuurt die niet mee.
- **Herstelpunten per app (B12).** Zolang die niet bestaan, zijn `app.update` en `app.rollback` via de Hub altijd
  geblokkeerd (`backup_checkpoint_ontbreekt`); de keten zelf is Sim-getest met een gesimuleerd herstelpunt.
- **Gate `r2_r3_acties`** hangt af van `data_mutatie` (ADR-0007). Daardoor is élke R2-actie geblokkeerd bij een
  ongezonde pool of een rode back-upgate, ook een die geen opslag raakt (bv. een kritieke app herstarten). Veilig, maar
  mogelijk strenger dan bedoeld; aanpassen is een besluit over de gates, niet over dit beleid.
- **Engine-regels buiten de `policy_hash`.** `STOP-EENRICHTING` en `DOEL-ONHERKENBAAR` staan in de code van de
  engine, niet in de yaml. Een Hub en een executor met verschillende engineversies maar dezelfde yaml zien dat
  verschil niet. Een engineversie naast de `policy_hash` vraagt een veld in `ExecutionRequest.policy_decision`
  (contract §8: precies `risk_class`, `rule_ids`, `policy_hash`) of bij het koppelen: contractvraag, niet gebouwd
  (S-P2-010, bouwpunt 6d; open voor S-P2-030). Aanvulling 2026-11-14 (KLEIN-77): ook de opslagregels van KLEIN-76
  in `apps/policy/src/asm_policy/params.py` (`zfs_eigenschappen_verboden`, `acl_verboden` en de hostpadregel voor
  `host_path_config` in elke opslagregel, `opslag_verboden` voor een config van een ander type) vallen buiten de
  `policy_hash` en werken in de executor pas na een nieuw gebouwd en uitgerold executor-image; een oude executor merkt
  geen verschil. Aanvulling 2026-11-14 (KLEIN-78): hetzelfde restrisico geldt voor de naamregel van
  `ix_volume_config.dataset_name` (`patroon`) en, na het herstel van R-VEILIG-1, voor `opslag_verboden` voor SMB-opslag
  (type cifs, `cifs_config`) bij een catalogusapp (in plaats van `geheim_in_klare_tekst` voor `cifs_config.password`).
  Aanvulling 2026-11-14 (KLEIN-80): ook de witte lijst per opslagregel van de standaard Custom App (`onbekend_veld`,
  `type` en `bereik` in een opslagregel) werkt in de executor pas na een nieuw gebouwd en uitgerold executor-image.
  Aanvulling 2026-11-14 (KLEIN-80 herstel R-VEILIG-1 en R-VEILIG-2): hetzelfde geldt voor `mount_verboden` voor een
  koppelpad dat geen strikt containerpad is, `acl_verboden` voor een ACL op een ixVolume en `dubbel` voor een
  herhaalde `dataset_name`. Aanvulling 2026-11-14 (KLEIN-81): hetzelfde geldt voor `mount_verboden` voor een
  koppelpad onder een verboden containerpad (`/proc/sys`, `/dev/shm`, `/sys/fs/cgroup`); een oude executor laat die
  nog door. Aanvulling 2026-11-14 (KLEIN-88): hetzelfde geldt voor `mount_verboden` voor een koppelpad op of onder
  `/etc/hosts`, `/etc/hostname`, `/etc/resolv.conf` of `/run/secrets`; een oude executor laat die nog door.
  Aanvulling 2026-11-14 (KLEIN-90): hetzelfde geldt voor `mount_verboden` voor een koppelpad op of onder
  `/var/run/secrets`; een oude executor laat dat nog door.
  Aanvulling 2026-11-14 (KLEIN-83): hetzelfde geldt voor `opslag_verboden` voor NFS-opslag (type nfs,
  `nfs_config`) bij een catalogusapp; een oude executor laat een exportpad zonder `/` nog door.
  Besluit 2026-11-15 (S-P2-030, bouwpunt 6d, optie A): geen engineversie en geen nieuw contractveld; dit open punt
  blijft staan. Tot een contractronde is de maatregel: het executor-image wordt op een digest vastgezet (manifest
  `deploy/manifest/ai-server-manager-executor.manifest.yaml`: `digest_pending_release`, de release-CI vult de digest
  in) en bij de uitrol op de NAS (P6) vervangen. Een executor met een ouder image ziet nieuwe engine-regels tot die
  vervanging niet.
- **Open punten uit de ruwe lijst, stand na S-P2-030 (bouwpunt 7).** Gebouwd: de eenmalige nonce van een
  `ExecutionRequest` staat in dezelfde `executor.sqlite3` in de eigen datamap als de `jti`-replaycache (tabel
  `request_nonces` in `apps/executor/src/executor/journal.py`; `ReplayCache` in `apps/executor/src/executor/replay.py`,
  contract §4.6); `notification.send` wordt door de executor geweigerd (`actie_niet_toegestaan`) en loopt via de
  Gotify-adapter van de Hub (besluit 17). Open: **sleutelrotatie van de policy-sleutel in de executor.**
  `KeyRotationPoller.poll` in `apps/executor/src/executor/hublink.py` past een gemelde rotatie niet toe en zet
  `sleutelrotatie_niet_toegepast` (test `apps/executor/tests/test_hublink.py::test_sleutelrotaties_pollen_lege_lijst_en_niet_lege_lijst`);
  de executor blijft dan bij de gepinde sleutels en weigert verzoeken met een nieuwe sleutel. Geen stap in het
  uitvoeringsplan bouwt het toepassen in de executor nog uitdrukkelijk; S-P2-210 (beveiligingsreview van P2) toetst "sleutelrotatie niet toegepast" als
  aanvalsweg. Niet gebouwd in S-P2-030.
- **Eigen waarden van een catalogusapp.** Bij een catalogusapp (geen ix-app) kunnen de waarden andere vrije tekst
  bevatten dan de vier ix-app-velden; die wist de Hub na afloop nog niet (S-P2-050/S-P2-070, kluisverwijzingen).
- **Geen sleutel-ID in `ExecutionRequest`.** De executor probeert elke sleutel uit de gepinde set; bij sleutelrotatie
  (contract §4.5) is een `kid` in het verzoek duidelijker. Contractvraag.
- **Opnieuw koppelen mét sleutelbewijs en een eigen vrijgeefknop (S-P2-020, vervolg op R-VEILIG-1 en R-TECH-5).**
  De tussenstap van besluit 13 (ontkoppelen wist de sleutel) en besluit 14 (vervangen met een nieuwe sleutel geeft
  nooit vrij) staan; de volledige vorm van §3.9 (sleutelveld in het koppelformulier na een ontkoppeling) en een eigen
  knop "Vrijgeven" (alleen zichtbaar als de executor gestopt is) vragen een nieuwe Peil-versie van
  `design/ontwerptaal/statuspagina.html` (nu 1.1.1, byte-gelijk gepind). Ook de vaste teksten van het koppelformulier
  ("Niet gekoppeld", "nog niet met de Hub gekoppeld") en het sjablooncommentaar ("koppelformulier: nog NOOIT
  gekoppeld") passen niet bij `ontkoppeld`; tot die stap legt een vaste melding op de pagina uit wat er aan de hand
  is. Eigen latere stap.

## Gevolgen

- Een wijziging van het beleid vraagt een nieuwe image van Hub én executor met dezelfde `policy_hash`; anders weigert
  de executor alles (`policy_hash_verschilt`). De rooktest (`deploy/smoke.sh`) vergelijkt de `policy_hash` van beide
  images met elkaar en met `policy/` in de repo, en een unittest bewaakt dat beide Dockerfiles precies alle
  `policy/*.yaml` kopiëren (S-P2-010).
- De JSON-RPC-methoden en hun parameters (`app.create`, `app.update`, `app.delete`, `app.config`, `core.get_jobs`)
  zijn gebouwd naar de publieke API-beschrijving en alleen tegen de fake getest: **NIET GEVALIDEERD (echte NAS)**.
