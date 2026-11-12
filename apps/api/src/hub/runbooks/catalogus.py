"""Getypeerde operator-runbooks (B09-006, 05_OPERATIES_EN_UPDATES "Incident & herstel").

Elk runbook volgt vast **observeren → isoleren → mitigeren → terugdraaien → bewijs verzamelen → oorzaak vastleggen**,
met een **test na herstel** die meer vraagt dan "de poort is open". Stappen zijn getypeerd:
- ``lezen`` (R0): wat de Hub zelf toont (met de route als bron);
- ``handmatig``: wat een mens doet in een bestaande UI (TrueNAS-web-UI, de app zelf) — nooit een terminal;
- ``voorstel``: een actievoorstel met een ``action_id`` uit de executor-allowlist (contract §8) en een minimale
  risicoklasse. De Hub voert een voorstel nooit zelf uit: dat loopt (vanaf P2) via policy-engine, goedkeuring en
  executor. Er bestaat geen stap met shell, sudo, Docker-socket of vrije opdrachttekst.

De catalogus is code (read-only in de image) met een ``runbook_hash``; de AI kan hem niet wijzigen. Veilige modus: na
``max_herhalingen`` keer opnieuw falen binnen ``venster_s`` stelt de Hub geen herstart of herhaling meer voor.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Soort = Literal["lezen", "handmatig", "voorstel"]
Risico = Literal["R0", "R1", "R2", "R3"]
FASEN = ("observeren", "isoleren", "mitigeren", "terugdraaien", "bewijs", "oorzaak")
RISICO_RANK = {"R0": 0, "R1": 1, "R2": 2, "R3": 3}
# Executor-allowlist v1 (contract §8) met de minimale risicoklasse.
ALLOWLIST: dict[str, Risico] = {
    "app.restart": "R1",
    "app.stop": "R1",
    "app.start": "R1",
    "app.install": "R2",
    "app.update": "R2",
    "app.rollback": "R2",
    "app.uninstall": "R2",
    "zfs.snapshot.create": "R1",
    "zfs.snapshot.clone_to_sandbox": "R1",
    "notification.send": "R0",
}
# Wat de engine voor een Custom App strenger maakt (STOP-EENRICHTING, ADR-0030 besluit 21): stoppen is daar R2.
ALLOWLIST_CUSTOM_APP: dict[str, Risico] = {"app.stop": "R2"}
# Na een stop ziet het platform niet meer wat er in een Custom App draait (doel_niet_herkenbaar) en weigert het elke
# actie op die app. Een runbookstap na ``app.stop`` met een van deze acties zegt dat (``custom_app``).
NA_STOP_GEWEIGERD = "gestopt_geweigerd"
NA_STOP_ACTIES = ("app.start", "app.restart", "app.update", "app.rollback", "app.uninstall")
VERBODEN_WOORDEN = ("sudo", "ssh ", "shell", "terminal", "docker exec", "docker.sock", "rm -rf", "sh -c", "chmod 777")


@dataclass(frozen=True)
class Stap:
    tekst: str
    soort: Soort
    bron: str | None = None  # Hub-route of UI-plek
    action_id: str | None = None
    risico: Risico | None = None
    # Wat er anders is voor een Custom App: een hogere klasse ("R2") of ``NA_STOP_GEWEIGERD``; ``None`` = hetzelfde.
    custom_app: str | None = None


@dataclass(frozen=True)
class VeiligeModus:
    max_herhalingen: int = 2
    venster_s: int = 3600


@dataclass(frozen=True)
class Runbook:
    id: str
    titel: str
    scenario: str
    observeren: tuple[Stap, ...]
    isoleren: tuple[Stap, ...]
    mitigeren: tuple[Stap, ...]
    terugdraaien: tuple[Stap, ...]
    bewijs: tuple[Stap, ...]
    oorzaak: tuple[Stap, ...]
    test_na_herstel: tuple[str, ...]
    veilige_modus: VeiligeModus = field(default_factory=VeiligeModus)
    herstart_voorstel: str | None = None  # action_id voor 'Herstel voorstellen' (buiten veilige modus)

    def stappen(self) -> dict[str, tuple[Stap, ...]]:
        return {f: getattr(self, f) for f in FASEN}


def L(tekst: str, bron: str | None = None) -> Stap:
    return Stap(tekst, "lezen", bron)


def H(tekst: str, bron: str | None = None) -> Stap:
    return Stap(tekst, "handmatig", bron)


def V(tekst: str, action_id: str, risico: Risico, *, custom_app: str | None = None) -> Stap:
    return Stap(tekst, "voorstel", None, action_id, risico, custom_app)


INCIDENT = "/api/v1/incidents/{incident_id}"
LOGS = "/api/v1/logs?incident_id={incident_id}"

RUNBOOKS: tuple[Runbook, ...] = (
    Runbook(
        "service_offline",
        "Dienst offline of crasht",
        "Een app of dienst is onbereikbaar, crasht of doet geen werk meer (ook: monitoringbron weg).",
        observeren=(
            L(
                "Bekijk de gezondheid per onderdeel (TrueNAS-staat, buitenkant, binnenkant) en sinds wanneer.",
                "/api/v1/apps/{app_id}",
            ),
            L("Bekijk de onderliggende gebeurtenissen en de readback van het incident.", INCIDENT),
            L("Bekijk geschoonde logregels rond het incident (zelfde trace_id of tijdvenster).", LOGS),
        ),
        isoleren=(
            L(
                "Kijk of meer apps tegelijk wegvallen (hypothese 'nas:onbereikbaar' of 'pool:ongezond').",
                "/api/v1/incidents/samenvatting",
            ),
            H("Open TrueNAS → Apps → de app → Logs en zoek de laatste fout vóór het stoppen.", "TrueNAS-web-UI"),
        ),
        mitigeren=(
            V("Herstart de app één keer (alleen buiten de veilige modus).", "app.restart", "R1"),
            H("Is de app bewust gestopt? Erken het incident en demp de regel 'App onbereikbaar' voor deze app."),
        ),
        terugdraaien=(
            V("Komt het falen na een update: zet de vorige waarden terug (terugzetrecept).", "app.rollback", "R2"),
        ),
        bewijs=(
            L("Supportbundel (geschoond) vastleggen bij het incident.", INCIDENT + "/supportbundel"),
            L("Noteer TrueNAS-staat, image-digest en tijdstippen in een notitie bij het incident."),
        ),
        oorzaak=(H("Leg de oorzaak vast in een notitie (bv. geheugen, configuratie, afhankelijkheid, update)."),),
        test_na_herstel=(
            "Binnenkant gezond: connector-health of heartbeat vers en werk verwerkt (niet alleen 'poort open').",
            "Alert 'App onbereikbaar' hersteld na de herstelduur (hysterese), geen nieuwe crash binnen het "
            "heropenvenster.",
        ),
        herstart_voorstel="app.restart",
    ),
    Runbook(
        "db_migratie_mislukt",
        "Databasemigratie mislukt",
        "Een app start niet of meldt een mislukte schemamigratie na een update.",
        observeren=(
            L("Bekijk het incident en de logregels van de app rond de update.", LOGS),
            L("Bekijk de image-historie (tag en digest) in de catalogus.", "/api/v1/apps/{app_id}"),
        ),
        isoleren=(
            H("Controleer in de app-log welke migratie faalde; verander niets aan de database met de hand."),
            L(
                "Controleer of er een verse, geverifieerde database-export van vóór de update is.",
                "/api/v1/backups/coverage",
            ),
        ),
        mitigeren=(
            V(
                "Stop de app om verdere schade te voorkomen. Bij een Custom App vraagt dit goedkeuring van een "
                "beheerder (R2), en daarna weigert het platform elke actie op die app, ook app.rollback en app.start "
                "(doel_niet_herkenbaar): terugzetten en starten gaan dan alleen in de TrueNAS-web-UI.",
                "app.stop",
                "R1",
                custom_app="R2",
            ),
        ),
        terugdraaien=(
            V("Maak eerst een snapshot van de data-dataset.", "zfs.snapshot.create", "R1"),
            V(
                "Alleen bij een catalogusapp: een versie-terugzet, en alleen als de migratie niets schreef; anders is "
                "herstel van de database nodig (R3, via de eigenaar).",
                "app.rollback",
                "R2",
                custom_app=NA_STOP_GEWEIGERD,
            ),
            H(
                "Een gestopte Custom App zet je zelf terug in de TrueNAS-web-UI: het platform ziet bij een gestopte "
                "Custom App niet wat erin draait en weigert app.rollback (doel_niet_herkenbaar).",
                "TrueNAS-web-UI",
            ),
        ),
        bewijs=(L("Supportbundel en de exacte foutregel van de migratie vastleggen.", INCIDENT + "/supportbundel"),),
        oorzaak=(H("Leg vast welke migratie faalde en waarom (versie, schema, data)."),),
        test_na_herstel=(
            "App start, migratiestand gelijk aan de verwachte versie, connector-health gezond.",
            "Een testrestore van de export in een sandbox lukt (B12) voordat opnieuw wordt geüpdatet.",
        ),
    ),
    Runbook(
        "schijf_vol",
        "Quota of schijf vol (opslag)",
        "Een pool of dataset raakt vol, een quota is bereikt, of een pool is niet gezond.",
        observeren=(
            L("Bekijk poolgebruik en -gezondheid met bron en laatst bijgewerkt.", "/api/v1/observability/nas"),
            L("Bekijk de trend van pool.gebruik.", "/api/v1/metrics/query?metriek=pool.gebruik"),
        ),
        isoleren=(
            H("Zoek in TrueNAS → Storage welke dataset groeit (snapshots, downloads, transcodes)."),
            L(
                "Controleer de gate 'data_mutatie': bij een ongezonde pool zijn opslagmutaties geblokkeerd.",
                "/api/v1/gates/data_mutatie",
            ),
        ),
        mitigeren=(
            H("Ruim op via de eigenaar van de data (MediaGuard/MSO); de Hub verwijdert nooit zelf media of datasets."),
            V(
                "Pauzeer een niet-kritieke, schrijvende app. Bij een Custom App vraagt dit goedkeuring van een "
                "beheerder (R2), en daarna kun je de app alleen in de TrueNAS-web-UI weer starten.",
                "app.stop",
                "R1",
                custom_app="R2",
            ),
        ),
        terugdraaien=(
            V(
                "Start een gepauzeerde catalogusapp weer met app.start als er genoeg ruimte is.",
                "app.start",
                "R1",
                custom_app=NA_STOP_GEWEIGERD,
            ),
            H(
                "Een gepauzeerde Custom App start je zelf in de TrueNAS-web-UI: het platform ziet bij een gestopte "
                "Custom App niet wat erin draait en weigert app.start (doel_niet_herkenbaar).",
                "TrueNAS-web-UI",
            ),
        ),
        bewijs=(L("Leg pool.gebruik vóór en na vast (grafiek of waarden).", "/api/v1/metrics/query"),),
        oorzaak=(H("Leg vast wat de ruimte opat en welke grens of retentie moet veranderen."),),
        test_na_herstel=(
            "pool.gebruik onder de herstelgrens gedurende de herstelduur; pool gezond (TrueNAS-meting, niet "
            "verouderd).",
        ),
    ),
    Runbook(
        "slechte_deployment",
        "Slechte deployment of update",
        "Na een installatie of update werkt een app slechter, crasht, of wijkt de digest af.",
        observeren=(
            L("Bekijk image, tag en digest-historie (readback na de update).", "/api/v1/apps/{app_id}"),
            L("Bekijk het incident en de logregels sinds de update.", LOGS),
        ),
        isoleren=(H("Vergelijk de release-notes van de nieuwe versie met het gedrag; verander niets met de hand."),),
        mitigeren=(V("Zet de vorige waarden terug (terugzetrecept met tag + digest).", "app.rollback", "R2"),),
        terugdraaien=(
            V(
                "Bij een schemawijziging: eerst snapshot, daarna herstel via de eigenaar (R3).",
                "zfs.snapshot.create",
                "R1",
            ),
        ),
        bewijs=(L("Supportbundel en de digest vóór en na vastleggen.", INCIDENT + "/supportbundel"),),
        oorzaak=(H("Leg vast welke wijziging de fout veroorzaakte en blokkeer die versie in het manifest."),),
        test_na_herstel=(
            "Digest-readback gelijk aan het terugzetrecept; binnenkant gezond; geen nieuwe fout binnen het "
            "heropenvenster.",
        ),
        herstart_voorstel="app.rollback",
    ),
    Runbook(
        "toegang_kwijt",
        "Toegang kwijt: Tailscale/Cloudflare-lockout (ook SSO)",
        "Toegang van buiten (Tailscale, Cloudflare Tunnel) of via SSO werkt niet meer.",
        observeren=(
            L("Bekijk de gezondheid van Tailscale/cloudflared en Authentik in de catalogus.", "/api/v1/apps"),
            L("Bekijk of de noodlogin werkt (zelftest, zonder in te loggen).", "/api/v1/auth/break-glass/selftest"),
        ),
        isoleren=(
            H("Test vanaf het thuisnetwerk én vanaf een onafhankelijke verbinding (telefoon zonder wifi)."),
            H(
                "Controleer in de app zelf (Tailscale-beheer, Cloudflare-dashboard) of de sleutel/het token verlopen "
                "is."
            ),
        ),
        mitigeren=(
            H("Gebruik op het thuisnetwerk de noodlogin van de Hub (wachtwoord + TOTP); nooit via internet."),
            V("Herstart de tunnel-app één keer.", "app.restart", "R2"),
        ),
        terugdraaien=(V("Zet de vorige waarden van de tunnel-app terug.", "app.rollback", "R2"),),
        bewijs=(L("Leg tijdstippen en de testresultaten van beide verbindingen vast als notitie.", INCIDENT),),
        oorzaak=(H("Leg vast wat de toegang brak (verlopen sleutel, update, DNS) en roteer het noodaccount daarna."),),
        test_na_herstel=(
            "Toegang werkt vanaf een onafhankelijke verbinding én van binnen; noodaccount geroteerd en bevestigd.",
        ),
        veilige_modus=VeiligeModus(max_herhalingen=1),
    ),
    Runbook(
        "jellyfin_client",
        "Jellyfin/Jelly Leon-clientprobleem",
        "Een client speelt niet af, logt niet in of is incompatibel na een update.",
        observeren=(
            L("Bekijk de gezondheid van Jelly Leon (openbare routes) en het incident.", "/api/v1/apps"),
            H("Noteer client, versie, apparaat en het afspeelpad (direct play of transcode)."),
        ),
        isoleren=(H("Test dezelfde titel met een andere client en met de stock-webclient."),),
        mitigeren=(H("Gebruik tijdelijk een andere client of de webclient; wijzig niets aan de database."),),
        terugdraaien=(V("Komt het door een serverupdate: zet de vorige waarden terug.", "app.rollback", "R2"),),
        bewijs=(L("Supportbundel en de clientmatrix-regel vastleggen.", INCIDENT + "/supportbundel"),),
        oorzaak=(H("Leg vast welke client/versie faalt en meld het bij de clientmatrix (B03)."),),
        test_na_herstel=("De titel speelt af op de getroffen client; de clientmatrix-test voor die client slaagt.",),
    ),
    Runbook(
        "gree_onbekend",
        "Gree-airco onbekend of offline",
        "my_house meldt een Gree-apparaat als onbekend, offline of met verouderde status.",
        observeren=(
            L("Bekijk de status van my_house in de catalogus (alleen lezen).", "/api/v1/apps"),
            H("Open my_house en bekijk de laatste bijgewerkte status van het apparaat."),
        ),
        isoleren=(H("Controleer of het apparaat stroom en wifi heeft en of de afstandsbediening het heeft uitgezet."),),
        mitigeren=(
            H(
                "Laat my_house het apparaat niet aansturen zolang de status onbekend is (veilige terugval); de Hub "
                "stuurt nooit zelf aan."
            ),
        ),
        terugdraaien=(H("Hervat schema's in my_house pas na een verse, bevestigde status."),),
        bewijs=(L("Leg tijdstippen van de laatste verse status vast als notitie.", INCIDENT),),
        oorzaak=(H("Leg vast waarom het apparaat onbereikbaar was (netwerk, firmware, stroom)."),),
        test_na_herstel=("my_house toont een verse status en een testcommando in my_house wordt bevestigd.",),
    ),
    Runbook(
        "mso_provider_uitval",
        "MSO: providers of indexers vallen uit",
        "Media Source Optimizer meldt dat Usenet-providers of indexers niet werken.",
        observeren=(
            L("Bekijk de MSO-status in de catalogus en het incident.", "/api/v1/apps"),
            H("Open MSO en bekijk providerhealth en foutcodes."),
        ),
        isoleren=(H("Controleer in MSO of één provider of alle providers falen (account, quota, netwerk)."),),
        mitigeren=(
            H(
                "Laat MSO zelf uitwijken naar andere providers; keur alleen MSO-change-sets goed, nooit iets "
                "verwijderen vanuit de Hub."
            ),
        ),
        terugdraaien=(H("Draai een eerder goedgekeurde MSO-change-set terug in MSO als die de oorzaak was."),),
        bewijs=(L("Leg de MSO-foutcodes en tijdstippen vast als notitie.", INCIDENT),),
        oorzaak=(H("Leg vast welke provider faalde en waarom (account verlopen, storing bij de provider)."),),
        test_na_herstel=("MSO meldt de provider weer gezond en een testzoekopdracht in MSO slaagt.",),
    ),
)
BY_ID = {r.id: r for r in RUNBOOKS}


def runbook_hash() -> str:
    data = [asdict(r) for r in RUNBOOKS]
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def validate(runbooks: tuple[Runbook, ...] = RUNBOOKS) -> list[str]:
    """Fouten in de catalogus (lege fase, verboden woord, onbekende action_id, te lage risicoklasse, ``app.stop`` zonder
    de klasse voor een Custom App, of een actie op de app na een stop zonder de vermelding dat het platform een
    gestopte Custom App weigert)."""
    errors: list[str] = []
    for r in runbooks:
        gestopt = False
        for fase, stappen in r.stappen().items():
            if not stappen:
                errors.append(f"{r.id}: fase {fase} is leeg")
            for s in stappen:
                low = s.tekst.lower()
                errors.extend(f"{r.id}: verboden woord '{w}'" for w in VERBODEN_WOORDEN if w in low)
                if s.soort == "voorstel":
                    if s.action_id not in ALLOWLIST or s.risico is None:
                        errors.append(f"{r.id}: onbekende action_id {s.action_id}")
                    elif RISICO_RANK[s.risico] < RISICO_RANK[ALLOWLIST[s.action_id]]:
                        errors.append(f"{r.id}: {s.action_id} onder de minimale klasse")
                    errors.extend(_custom_app_fouten(r.id, s, gestopt))
                    gestopt = gestopt or s.action_id == "app.stop"
                elif s.action_id is not None:
                    errors.append(f"{r.id}: action_id alleen bij een voorstel")
        if not r.test_na_herstel:
            errors.append(f"{r.id}: geen test na herstel")
        if all("poort" in t.lower() and "niet alleen" not in t.lower() for t in r.test_na_herstel):
            errors.append(f"{r.id}: test na herstel mag niet alleen 'poort open' zijn")
        if r.herstart_voorstel is not None and r.herstart_voorstel not in ALLOWLIST:
            errors.append(f"{r.id}: onbekend herstartvoorstel")
    return errors


def _custom_app_fouten(rid: str, s: Stap, gestopt: bool) -> list[str]:
    errors: list[str] = []
    if s.custom_app is not None and s.custom_app != NA_STOP_GEWEIGERD and s.custom_app not in RISICO_RANK:
        errors.append(f"{rid}: onbekende waarde custom_app '{s.custom_app}' bij {s.action_id}")
    minimum = ALLOWLIST_CUSTOM_APP.get(str(s.action_id))
    if minimum is not None and (
        s.custom_app not in RISICO_RANK or RISICO_RANK[str(s.custom_app)] < RISICO_RANK[minimum]
    ):
        errors.append(f"{rid}: {s.action_id} zonder de klasse voor een Custom App ({minimum})")
    if gestopt and s.action_id in NA_STOP_ACTIES and s.custom_app != NA_STOP_GEWEIGERD:
        errors.append(
            f"{rid}: {s.action_id} na app.stop zonder de vermelding dat het platform een gestopte Custom App weigert"
        )
    return errors


def to_dict(r: Runbook) -> dict[str, Any]:
    return {
        "id": r.id,
        "titel": r.titel,
        "scenario": r.scenario,
        "fasen": {f: [asdict(s) for s in st] for f, st in r.stappen().items()},
        "test_na_herstel": list(r.test_na_herstel),
        "veilige_modus": asdict(r.veilige_modus),
        "herstel_voorstel": r.herstart_voorstel,
    }
