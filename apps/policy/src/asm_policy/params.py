"""Parameterschema's, doelschema's en harde grenzen per action_id (contract 1.3 §8 en §9 EX47, B01-003, ADR-0030).

Elke functie geeft een lijst :class:`Fout` terug; leeg = geldig. De Hub controleert bij het voorstel, de executor
opnieuw vóór uitvoering (zelfde code, eigen kopie van het beleid). Invoer wordt als geheel gecontroleerd en nooit
afgekapt. Onbekende velden zijn een fout (strikt).

``app.install`` (standaard Custom App = catalogusapp ``ix-app``) weigert vóór uitvoering (EX47): compose/YAML
(``custom_app: true``, ``custom_compose_config(_string)``), ``privileged``, extra capabilities, apparaten, een
Docker-socket, hostpaden buiten ``/mnt/<pool>/<dataset>`` (dus ook ``/``, ``/etc``, ``/var/run``, ``/root``), host
network zonder reden, een gedeeld Docker-netwerk, ``latest`` of een tag zonder digest, ``HUB_*``-variabelen en root
als "custom user". Ook de eigen waarden van een catalogusapp krijgen op elke diepte geen compose, privileged, extra
capabilities, apparaten, host-PID/-IPC, host network zonder reden, gedeeld netwerk, GPU zonder ``gpu: intel_render``,
Docker-socket of hostpad buiten een dataset (:func:`_deep_forbidden`; S-P2-010, R-VEILIG-3). Dat geldt ook voor een
losse tekst in een lijst (S-P2-010, herstelronde 2): een Docker-socket, een hostpad in bind- of volumevorm
(``"/:/host"``, ``"--mount=type=bind,source=/,..."``), een ongeldige kluisverwijzing en een verboden sleutel als vlag
(``"--privileged"``, ``"pid=host"``, ``"--cap-add=SYS_ADMIN"``) worden geweigerd (:func:`_losse_tekst`).

Eén tabel (S-P2-010, herstelronde 3): :data:`VERBODEN_SLEUTELS` geldt gelijk voor een sleutel in een object, een
losse tekst in een lijst en de vlagvorm. Sleutels worden eerst genormaliseerd (:func:`_nk`: kleine letters, alleen
letters en cijfers, zoals de manifestregels van appstore-en-fork), dus ``Privileged``, ``hostNetwork`` en
``host-network`` zijn dezelfde sleutel. ``privileged`` en ``host_network`` zijn verboden met elke waarde behalve
afwezig, ``None`` of ``False``; de Docker-/compose-namen (``network_mode``, ``security_opt``, ``sysctls``, ...) met
een niet-lege waarde; "compose" in een sleutel en ``services`` altijd; "unconfined" in elke tekst. In de waarden van
een catalogusapp krijgt ook een tekstwaarde in een object de controle van een losse tekst, behalve vrije tekst
(de waarde naast ``name`` of ``key`` in een paar, ``notes`` en ``description``), en tellen ``source``, ``src``,
``hostpath`` en ``path`` met een waarde die met "/" begint als hostpad. Bij de standaard Custom App zijn ``command``
en ``entrypoint`` de opdracht van het proces ín de container (ix-app-sjabloon: alleen ``set_command`` en
``set_entrypoint``): daar geldt de vlag- en bindcontrole niet, de Docker-socket- en kluisregels wel.

Opslag (KLEIN-76; KLEIN-75 A5 en A1): ``ix_volume_config.properties`` (ZFS-eigenschappen van het dataset dat TrueNAS
aanmaakt) is bij elke app en met elke waarde verboden (``zfs_eigenschappen_verboden``), en ``mountpoint`` met een
waarde die met "/" begint is overal een hostpad, ook bij de standaard Custom App. Bij de standaard Custom App is een
aanwezig ``host_path_config.acl`` ook met ``acl_enable: false`` een ACL (``acl_verboden``) en gaat ``acl.path`` door
de hostpadregel, in een opslagregel van elk type (R-VEILIG-1: TrueNAS normaliseert ``host_path_config`` ook in een
regel van type ix_volume of tmpfs); ``host_path_config.path`` gaat dan ook door de hostpadregel. Een config van een
ander type dan de regel (bv. ``host_path_config`` of ``tmpfs_config`` bij ix_volume) die niet leeg is (afwezig,
``null`` of ``{}``), is ``opslag_verboden``. Het gedrag van TrueNAS in deze alinea is afgeleid uit de bron
(truenas/apps f142a16, middleware ece9d19); NIET GEVALIDEERD (echte NAS).

Opslag (KLEIN-78; KLEIN-75 A3 en A6): ``ix_volume_config.dataset_name`` (ook een ``ix_volume_config`` die een tekst
is) moet bij elke app een veilige ZFS-naam zijn (:data:`IX_VOLUME_NAAM_RE`; anders ``patroon``, of ``type`` als het
geen tekst is). In de waarden van een catalogusapp is SMB-opslag geweigerd (``opslag_verboden``): elke opslagregel
van type cifs en elke niet-lege ``cifs_config``, ook in een andere schrijfwijze en in een lijst, tot de executor
kluisverwijzingen invult (herstel R-VEILIG-1; ADR-0030 besluit 6 en 28). Afgeleid uit de bron; NIET GEVALIDEERD
(echte NAS).

Opslag (KLEIN-80; KLEIN-75 A2): bij de standaard Custom App geldt een witte lijst per opslagregel en per type-config,
precies het formulier van ix-app 1.4.8 (:data:`IX_OPSLAGREGEL_VELDEN`, :data:`IX_OPSLAG_CONFIG_VELDEN`); elke andere
sleutel, ook ``create_host_path``, ``propagation``, ``auto_permissions`` en tmpfs ``exec``/``mode``/``uid``/``gid``,
geeft ``onbekend_veld``. ``read_only`` is true of false, ``tmpfs_config.size`` een geheel getal van minstens 1. Een
nieuw veld in een latere ix-app-versie wordt geweigerd tot de lijst is bijgewerkt. Catalogusapps vallen hier niet
onder (S-P2-050). Afgeleid uit de bron; NIET GEVALIDEERD (echte NAS).

Opslag (KLEIN-80, herstel R-VEILIG-1 en R-VEILIG-2; KLEIN-75 A4 optie a): bij de standaard Custom App is
``mount_path`` alleen een strikt containerpad (:data:`CONTAINERPAD_RE`, geen "."- of ".."-deel, genormaliseerd geen
verboden containerpad; anders ``mount_verboden``), zodat de tmpfs-opties niet via ":" of "," in ``mount_path`` te zetten
zijn. In ``ix_volume_config`` geeft een niet-lege ``acl_entries`` of een ``acl_enable`` anders dan false
``acl_verboden`` en staat elke ``dataset_name`` hooguit één keer in een installatie (anders ``dubbel``). Afgeleid uit
de bron; NIET GEVALIDEERD (echte NAS).

Diepte (S-P2-010, R-VEILIG-1; dicht bij twijfel): parameters zijn hooguit :data:`MAX_PARAMETER_DIEPTE` niveaus diep
genest, anders ``te_diep_genest``. De doorzoekers (:func:`_walk`, en de boilercontrole in de engine) kijken tot
:data:`asm_policy.canonical.MAX_DIEPTE` (minstens zo diep) en weigeren dieper in plaats van stil te stoppen.
"""

from __future__ import annotations

import ipaddress
import posixpath
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from asm_policy.canonical import MAX_DIEPTE, CanonicalError, TeDiepGenest, canonical_json
from asm_policy.loader import ActieDef, Policy

APP_NAME_RE = re.compile(r"^[a-z]([-a-z0-9]*[a-z0-9])?$")
DATASET_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*(/[A-Za-z0-9_.:-]+)*$")
SNAP_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$")
SANDBOX_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,63}$")
CATALOG_APP_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
TRAIN_RE = re.compile(r"^[a-z][a-z0-9_-]{1,31}$")
VERSION_RE = re.compile(r"^\d{1,6}(\.\d{1,6}){1,3}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
REPO_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*(:[0-9]{1,5})?(/[a-z0-9][a-z0-9._-]*){1,6}$")
TAG_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$")
ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
VAULT_REF_RE = re.compile(r"^vault://app/[a-z0-9][a-z0-9_-]{0,63}/[a-z0-9_.-]{1,128}$")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
# Een hostpad is strenger dan vrije tekst: ook tab en regeleinde zijn daar geen gewone tekens (S-P2-010, 6f), en ook
# geen Unicode-teken uit Cc (C1, NEL), Cf (bidi-omkering, zero-width, BOM), Zl of Zp (S-P2-010, R-VEILIG-5).
HOSTPAD_STUURTEKEN_RE = re.compile(r"[\x00-\x1f\x7f]")
HOSTPAD_VERBODEN_CATEGORIEEN = frozenset({"Cc", "Cf", "Zl", "Zp"})
# Hooguit zoveel objecten of lijsten diep (``parameters`` zelf is diepte 0; een gewone catalogusapp met opslag en
# ACL-regels zit rond de 10). Dieper: ``te_diep_genest`` (S-P2-010, R-VEILIG-1). De doorzoekers kijken tot
# MAX_DIEPTE (32), dus minstens zo diep.
MAX_PARAMETER_DIEPTE = 16
# Losse teksten in een lijst (S-P2-010, herstelronde 2; dicht bij twijfel). Zo'n tekst heeft geen sleutel; een sleutel
# die in een object verboden is, wordt herkend in de vormen "sleutel", "sleutel=waarde", "sleutel: waarde",
# "--sleutel waarde" en "--sleutel" (streepjes tellen als "_", hoofdletters tellen niet).
LOSSE_SLEUTEL_RE = re.compile(r"-{0,2}([A-Za-z_][A-Za-z0-9_-]*)")
NIET_ALFANUM_RE = re.compile(r"[^a-z0-9]")
# Waarden die "uit" betekenen; al het andere (ook een vlag zonder waarde) telt als "aan".
LOSSE_WAARDE_UIT = frozenset({"", "false", "0", "no", "off", "none", "null", "[]", "{}"})
# Docker-bindvorm BRON:DOEL[:OPTIES] (bv. "/:/host", "/etc:/etc:ro"): begint een tekst met "/", "." of "~" en staat er
# een ":" in, dan is alles vóór de eerste ":" een hostpad (dicht bij twijfel: ook "/usr/bin:/bin" telt zo). Een andere
# bron ("data:/data") is een benoemd volume. Lange vorm: "type=bind,source=/,target=/host" (ook "src=").
BIND_BRON_RE = re.compile(r"(?:^|[\s,=])(?:source|src)\s*=\s*([^,]*)", re.IGNORECASE)
URL_RE = re.compile(r"\s*[A-Za-z][A-Za-z0-9+.-]*://")
HOSTPAD_BEGIN = ("/", ".", "~")
# De korte en de lange Docker-optie voor een volume met de waarde er direct achter ("-v/:/host", "--volume/:/host").
VOLUME_AANEEN_RE = re.compile(r"\s*(?:-v|--volume)(?=[/.~])")
# Genormaliseerde sleutels (zie _nk) waarvan een tekstwaarde die met "/" begint in de waarden van een catalogusapp
# een hostpad is (S-P2-010, herstelronde 3). ``mountpoint`` (KLEIN-76) geldt ook bij de standaard Custom App
# (HOSTPAD_SLEUTELS_OVERAL): bij TrueNAS is dat het mountpunt van een ZFS-dataset.
HOSTPAD_SLEUTELS = frozenset({"source", "src", "hostpath", "path", "mountpoint"})
HOSTPAD_SLEUTELS_OVERAL = frozenset({"mountpoint"})
# Vrije tekst in de waarden van een catalogusapp (genormaliseerde sleutels): geen vlag- of bindcontrole. Daarnaast is
# de waarde naast "name" of "key" in een paar vrije tekst (zie _walk).
VRIJE_TEKST_SLEUTELS = frozenset({"notes", "description"})
# "host", of de namespace van een andere container (Docker: "container:<naam>", compose: "service:<naam>").
NAAMRUIMTE_VAN_ANDER = ("container:", "service:")
HOST_IDS = ("nas-primary",)
IX_APP = "ix-app"
RESTART_POLICIES = ("no", "unless-stopped", "on-failure", "always")
MAX_VALUES_BYTES = 64 * 1024
MAX_EIGENAAR_BYTES = 16 * 1024
# Bekende velden van het formulier van de standaard Custom App (ix-app 1.4.8, questions.yaml; via appstore-en-fork).
IX_VALUES_KEYS = frozenset(
    {
        "notes",
        "image",
        "hostname",
        "entrypoint",
        "command",
        "TZ",
        "envs",
        "restart_policy",
        "max_retry_count",
        "disable_builtin_healthcheck",
        "tty",
        "stdin",
        "devices",
        "privileged",
        "capabilities",
        "run_as_custom_user",
        "run_as",
        "host_network",
        "ports",
        "networks",
        "dns_config",
        "portals",
        "storage",
        "labels",
        "resources",
    }
)
CONTAINER_FORBIDDEN_MOUNTS = ("/", "/proc", "/sys", "/dev", "/var/run/docker.sock", "/run/docker.sock")


@dataclass(frozen=True)
class Fout:
    veld: str
    code: str
    fout: str

    def as_dict(self) -> dict[str, str]:
        return {"veld": self.veld, "code": self.code, "fout": self.fout}


def _f(veld: str, code: str, fout: str) -> Fout:
    return Fout(veld, code, fout)


def _only(obj: Any, where: str, allowed: set[str], required: set[str] = frozenset()) -> list[Fout]:  # type: ignore[assignment]
    if not isinstance(obj, Mapping):
        return [_f(where, "type", "verwacht een object")]
    out = [_f(f"{where}.{k}" if where else k, "onbekend_veld", "onbekend veld") for k in obj if k not in allowed]
    out += [
        _f(f"{where}.{k}" if where else k, "verplicht", "verplicht veld ontbreekt") for k in required if k not in obj
    ]
    return out


def _text(
    v: Any, where: str, *, min_len: int = 1, max_len: int = 256, pattern: re.Pattern[str] | None = None
) -> list[Fout]:
    if not isinstance(v, str):
        return [_f(where, "type", "verwacht tekst")]
    if len(v) < min_len or len(v) > max_len:
        return [_f(where, "lengte", f"lengte {min_len}–{max_len} tekens")]
    if CONTROL_RE.search(v):
        return [_f(where, "stuurteken", "stuurtekens zijn niet toegestaan")]
    if pattern is not None and not pattern.fullmatch(v):
        return [_f(where, "patroon", "ongeldige vorm")]
    return []


def _bool(v: Any, where: str) -> list[Fout]:
    return [] if isinstance(v, bool) else [_f(where, "type", "verwacht true of false")]


def _intr(v: Any, where: str, lo: int, hi: int) -> list[Fout]:
    if type(v) is not int or not lo <= v <= hi:
        return [_f(where, "bereik", f"geheel getal {lo}–{hi}")]
    return []


def te_diep(value: Any, grens: int, depth: int = 0) -> bool:
    """Waar als ergens in ``value`` een waarde op een diepte groter dan ``grens`` staat (``value`` zelf is diepte 0)."""
    if depth > grens:
        return True
    if isinstance(value, Mapping):
        return any(te_diep(v, grens, depth + 1) for v in value.values())
    if isinstance(value, list | tuple):
        return any(te_diep(v, grens, depth + 1) for v in value)
    return False


def _size(obj: Any, where: str, limit: int) -> list[Fout]:
    try:
        n = len(canonical_json(obj))
    except CanonicalError as exc:
        return [_f(where, "niet_canoniek", str(exc))]
    return [_f(where, "te_groot", f"hooguit {limit} bytes")] if n > limit else []


# ------------------------------------------------------------------ doel
def validate_target(actie: ActieDef, target: Any) -> list[Fout]:
    if not isinstance(target, Mapping):
        return [_f("target", "type", "verwacht een object")]
    out: list[Fout] = []
    host = target.get("host_id")
    if host is not None and host not in HOST_IDS:
        out.append(_f("target.host_id", "buiten_scope", "alleen 'nas-primary' (één NAS in v1)"))
    doel = actie.doel
    if doel in ("app", "app_nieuw"):
        out += _only(target, "target", {"host_id", "app_id"}, {"app_id"})
        if "app_id" in target:
            out += _text(target["app_id"], "target.app_id", max_len=40, pattern=APP_NAME_RE)
    elif doel == "dataset":
        out += _only(target, "target", {"host_id", "dataset"}, {"dataset"})
        if "dataset" in target:
            out += _dataset(target["dataset"], "target.dataset")
    elif doel == "snapshot":
        out += _only(target, "target", {"host_id", "snapshot"}, {"snapshot"})
        snap = target.get("snapshot")
        if isinstance(snap, str) and snap.count("@") == 1:
            ds, name = snap.split("@")
            out += _dataset(ds, "target.snapshot")
            out += _text(name, "target.snapshot", max_len=64, pattern=SNAP_NAME_RE)
        elif "snapshot" in target:
            out.append(_f("target.snapshot", "patroon", "verwacht <dataset>@<naam>"))
    elif doel == "geen":
        out += _only(target, "target", {"host_id"})
    else:  # eigenaar
        out += _only(target, "target", {"host_id", "app_id", "resource"}, {"app_id"})
        if target.get("app_id") != actie.eigenaar:
            out.append(_f("target.app_id", "buiten_scope", f"deze actie hoort bij {actie.eigenaar}"))
        if "resource" in target:
            out += _text(target["resource"], "target.resource", max_len=200)
    return out


def _dataset(v: Any, where: str) -> list[Fout]:
    errs = _text(v, where, max_len=200, pattern=DATASET_RE)
    if not errs and ("/../" in f"/{v}/" or "/./" in f"/{v}/"):
        errs.append(_f(where, "patroon", "ongeldige datasetnaam"))
    return errs


# ------------------------------------------------------------------ parameters
def validate_parameters(policy: Policy, actie: ActieDef, target: Mapping[str, Any], params: Any) -> list[Fout]:
    if not isinstance(params, Mapping):
        return [_f("parameters", "type", "verwacht een object")]
    out = _size(params, "parameters", MAX_VALUES_BYTES + 8 * 1024)
    if out:
        return out
    if te_diep(params, MAX_PARAMETER_DIEPTE):
        return [_f("parameters", "te_diep_genest", f"hooguit {MAX_PARAMETER_DIEPTE} niveaus diep genest")]
    schema = actie.parameters
    if schema == "leeg":
        return _only(params, "parameters", set())
    if schema == "snapshot_create":
        out = _only(params, "parameters", {"naam", "recursief"}, {"naam"})
        if "naam" in params:
            out += _text(params["naam"], "parameters.naam", max_len=64, pattern=SNAP_NAME_RE)
        if "recursief" in params:
            out += _bool(params["recursief"], "parameters.recursief")
        return out
    if schema == "snapshot_clone":
        out = _only(params, "parameters", {"doel_dataset"}, {"doel_dataset"})
        dest = params.get("doel_dataset")
        snap = str(target.get("snapshot") or "")
        pool = snap.split("/", 1)[0].split("@", 1)[0]
        if isinstance(dest, str):
            parts = dest.split("/")
            ok = (
                len(parts) == 3
                and parts[0] == pool
                and parts[1] == policy.sandbox_dataset
                and bool(SANDBOX_NAME_RE.fullmatch(parts[2]))
            )
            if not ok:
                out.append(
                    _f(
                        "parameters.doel_dataset",
                        "buiten_sandbox",
                        f"alleen <pool van de snapshot>/{policy.sandbox_dataset}/<naam>",
                    )
                )
        elif "doel_dataset" in params:
            out.append(_f("parameters.doel_dataset", "type", "verwacht tekst"))
        return out
    if schema == "notification_send":
        out = _only(params, "parameters", {"titel", "tekst", "prioriteit"}, {"titel", "tekst"})
        out += _text(params.get("titel"), "parameters.titel", max_len=120) if "titel" in params else []
        out += _text(params.get("tekst"), "parameters.tekst", max_len=2000) if "tekst" in params else []
        if "prioriteit" in params:
            out += _intr(params["prioriteit"], "parameters.prioriteit", 0, 10)
        return out
    if schema == "eigenaar":
        return _size(params, "parameters", MAX_EIGENAAR_BYTES)
    if schema == "app_update":
        return _app_update(params)
    if schema == "app_rollback":
        return _app_rollback(params)
    if schema == "app_install":
        return validate_install(params, target)
    return [_f("parameters", "schema_onbekend", "onbekend parameterschema")]  # pragma: no cover


def _image_ref(img: Any, where: str, digest: Any = None) -> list[Fout]:
    out = _only(img, where, {"repository", "tag", "pull_policy"}, {"repository", "tag"})
    if not isinstance(img, Mapping):
        return out
    out += _text(img.get("repository"), f"{where}.repository", max_len=255, pattern=REPO_RE)
    tag = img.get("tag")
    if not isinstance(tag, str) or not tag:
        out.append(_f(f"{where}.tag", "verplicht", "exacte tag verplicht"))
        return out
    version, sep, dig = tag.partition("@")
    if version.lower() == "latest" or not TAG_RE.fullmatch(version):
        out.append(_f(f"{where}.tag", "latest_of_ongeldig", "geen latest: een exacte versie is verplicht"))
    if sep and not DIGEST_RE.fullmatch(dig):
        out.append(_f(f"{where}.tag", "digest_ongeldig", "digest moet sha256:<64 hex> zijn"))
    if not sep and not (isinstance(digest, str) and DIGEST_RE.fullmatch(digest)):
        out.append(_f(f"{where}.tag", "digest_ontbreekt", "tag <versie>@sha256:<digest> of een digest in het manifest"))
    if "pull_policy" in img and img["pull_policy"] not in ("missing", "always", "never"):
        out.append(_f(f"{where}.pull_policy", "waarde", "missing, always of never"))
    return out


def _app_update(params: Mapping[str, Any]) -> list[Fout]:
    out = _only(params, "parameters", {"image", "catalog_version", "image_digest", "manifest_sha256"})
    has_img, has_cat = "image" in params, "catalog_version" in params
    if has_img == has_cat:
        out.append(_f("parameters", "precies_een", "precies één van image (Custom App) of catalog_version"))
    if has_img:
        out += _image_ref(params["image"], "parameters.image", params.get("image_digest"))
    if has_cat:
        out += _text(params["catalog_version"], "parameters.catalog_version", max_len=32, pattern=VERSION_RE)
    if "image_digest" in params:
        out += _text(params["image_digest"], "parameters.image_digest", max_len=71, pattern=DIGEST_RE)
    if "manifest_sha256" in params:
        out += _text(params["manifest_sha256"], "parameters.manifest_sha256", max_len=71, pattern=SHA_RE)
    return out


def _app_rollback(params: Mapping[str, Any]) -> list[Fout]:
    out = _only(params, "parameters", {"herstel_van", "catalog_version"})
    has_exec, has_cat = "herstel_van" in params, "catalog_version" in params
    if has_exec == has_cat:
        out.append(_f("parameters", "precies_een", "precies één van herstel_van (Custom App) of catalog_version"))
    if has_exec:
        out += _text(params["herstel_van"], "parameters.herstel_van", max_len=36, pattern=UUID_RE)
    if has_cat:
        out += _text(params["catalog_version"], "parameters.catalog_version", max_len=32, pattern=VERSION_RE)
    return out


# ------------------------------------------------------------------ app.install (EX47, B01-003)
def host_path_problem(path: Any) -> str | None:
    """``None`` als het hostpad een dataset onder ``/mnt/<pool>/<dataset>`` is; anders de reden (NL)."""
    if not isinstance(path, str) or not path.startswith("/"):
        return "het hostpad moet absoluut zijn: begin met /, bijvoorbeeld /mnt/<pool>/<dataset>"
    if HOSTPAD_STUURTEKEN_RE.search(path) or any(unicodedata.category(t) in HOSTPAD_VERBODEN_CATEGORIEEN for t in path):
        return "ongeldig hostpad: tabs, regeleinden en andere onzichtbare tekens zijn niet toegestaan"
    if "//" in path or path != path.rstrip("/"):
        return "ongeldig hostpad: geen dubbele / en geen / aan het eind"
    if len(path) > 512:
        return "ongeldig hostpad: hooguit 512 tekens"
    parts = path.split("/")[1:]
    if any(p != p.strip() for p in parts):
        return "ongeldig hostpad: een spatie aan het begin of eind van een mapnaam"
    if any(p in ("", ".", "..") for p in parts):
        return "geen . of .. in een hostpad"
    if "docker.sock" in path:
        return "een Docker-socket mag nooit in een container"
    if parts[0] != "mnt":
        return "alleen datasets onder /mnt/<pool>/<dataset> (nooit /, /etc, /var/run, /root of andere systeempaden)"
    if len(parts) < 3:
        return "/mnt zonder dataset is niet toegestaan; kies een dataset onder /mnt/<pool>/<dataset>"
    if parts[1].startswith(".") or parts[2].startswith("."):
        return "verborgen of interne mappen (bv. /mnt/.ix-apps) zijn niet toegestaan"
    return None


def _walk(value: Any, path: str = "", depth: int = 0) -> list[tuple[str, Any, Any, bool]]:
    """(pad, sleutel, waarde, paarwaarde) voor elke sleutel in geneste objecten, en (pad, ``None``, element, False)
    voor elk element van een lijst: ook een losse tekst in een lijst wordt zo bekeken (S-P2-010, herstelronde 2).
    ``paarwaarde`` is waar voor ``value`` in een naam/waarde-paar (een object met ``value`` naast ``name`` of ``key``,
    zoals ``envs[].value`` en ``labels[].value``): vrije tekst (herstelronde 3). Dieper dan
    :data:`asm_policy.canonical.MAX_DIEPTE`: :class:`TeDiepGenest` (nooit stil stoppen; S-P2-010, R-VEILIG-1)."""
    out: list[tuple[str, Any, Any, bool]] = []
    if depth > MAX_DIEPTE:
        raise TeDiepGenest(f"dieper genest dan {MAX_DIEPTE} niveaus")
    if isinstance(value, Mapping):
        paar = "value" in value and ("name" in value or "key" in value)
        for k, v in value.items():
            p = f"{path}.{k}" if path else str(k)
            out.append((p, k, v, paar and k == "value"))
            out += _walk(v, p, depth + 1)
    elif isinstance(value, list | tuple):
        for i, v in enumerate(value):
            p = f"{path}[{i}]"
            out.append((p, None, v, False))
            out += _walk(v, p, depth + 1)
    return out


def _nk(sleutel: Any) -> str:
    """Een sleutel genormaliseerd voor vergelijking: kleine letters, alleen letters en cijfers (``Host-Network``,
    ``hostNetwork`` en ``host_network`` worden ``hostnetwork``). Zelfde normalisatie als de manifestregels van
    appstore-en-fork."""
    return NIET_ALFANUM_RE.sub("", str(sleutel).lower())


def _sleutel_en_waarde(tekst: str) -> tuple[str, str | None] | None:
    """``("privileged", "true")`` voor ``"--privileged=true"``, ``("privileged", None)`` voor ``"--privileged"``;
    ``None`` als de tekst niet met een sleutel begint. De sleutel is genormaliseerd (:func:`_nk`): ``"--cap-add"``
    geeft ``capadd``. Lineair (geen regex met terugzoeken over de waarde)."""
    t = tekst.strip()
    m = LOSSE_SLEUTEL_RE.match(t)
    if not m:
        return None
    sleutel, rest = _nk(m[1]), t[m.end() :]
    if not rest:
        return sleutel, None
    na = rest.lstrip()
    if na[:1] in ("=", ":"):
        return sleutel, na[1:].strip()
    if rest[:1].isspace():
        return sleutel, na.strip()
    return None


def _aan(waarde: str | None) -> bool:
    """Een vlag zonder waarde, of een waarde die niet "uit" betekent (dicht bij twijfel)."""
    return waarde is None or waarde.strip().lower() not in LOSSE_WAARDE_UIT


def _bind_bronnen(tekst: str) -> list[str]:
    """Hostpaden die een tekst in bind- of volumevorm als bron noemt: de korte en de lange Docker-vorm, ook na een
    optie (``--volume=/:/host``, ``-v /:/host``) en met de waarde er direct achter (``-v/:/host``,
    ``--volume/:/host``). Een URL (``tcp://localhost:8080``) is geen bindvorm."""
    kandidaten = [tekst]
    sw = _sleutel_en_waarde(tekst)
    if sw and sw[1] and not URL_RE.match(tekst):
        kandidaten.append(sw[1])
    aaneen = VOLUME_AANEEN_RE.match(tekst)
    if aaneen:
        kandidaten.append(tekst[aaneen.end() :])
    bronnen: list[str] = []
    for t in (k.lstrip() for k in kandidaten):
        if ":" in t and t.startswith(HOSTPAD_BEGIN):
            bronnen.append(t.split(":", 1)[0])
        bronnen += [b for b in BIND_BRON_RE.findall(t) if b.startswith(HOSTPAD_BEGIN)]
    return bronnen


def _losse_tekst(tekst: str, p: str, manifest: Mapping[str, Any], ix_app: bool = False) -> list[Fout]:
    """Een losse tekst (een element van een lijst, of bij een catalogusapp een tekstwaarde in een object): dezelfde
    weigeringen als een sleutel in een object, uit dezelfde tabel (:func:`_sleutel_fout`; S-P2-010, herstelronde 2 en
    3). Een vlag zonder waarde telt als "aan" (dicht bij twijfel). ``pid`` en ``ipc`` zijn in een object alleen met
    de waarde ``host`` of de namespace van een andere container verboden; zonder waarde is die niet te zien, dus ook
    ``["--pid", "host"]`` (en daarmee ook ``["--pid", "/run/x.pid"]``) wordt geweigerd. ``"--pid=/run/x.pid"`` mag.
    Een tekst met een onzichtbaar opmaakteken (Unicode-categorie Cf: zero-width, bidi, BOM) wordt geweigerd: zo'n
    teken verbergt een vlag of bindvorm voor deze controle (net als bij een hostpad)."""
    if any(unicodedata.category(t) == "Cf" for t in tekst):
        return [_f(p, "stuurteken", "onzichtbare opmaaktekens (Unicode Cf) zijn in deze tekst niet toegestaan")]
    out: list[Fout] = []
    sw = _sleutel_en_waarde(tekst)
    if sw:
        fout = _sleutel_fout(sw[0], sw[1], tekstvorm=True, manifest=manifest, ix_app=ix_app)
        if fout:
            out.append(_f(p, *fout))
    for bron in _bind_bronnen(tekst):
        problem = host_path_problem(bron)
        if problem:
            out.append(_f(p, "hostpad_verboden", problem))
            break
    return out


def _extra_capabilities(v: Any) -> bool:
    """Zelfde regel als bij de ix-app: alleen leeg of ``{"add": []}`` mag (dicht bij twijfel)."""
    if not v:
        return False
    return not isinstance(v, Mapping) or bool(set(v) - {"add"}) or bool(v.get("add"))


def _inhoud(v: Any) -> bool:
    """Een niet-lege waarde: alles behalve ``None``, ``False``, ``""`` en een leeg object of een lege lijst (dicht
    bij twijfel: ook ``0`` en ``"false"`` tellen als inhoud)."""
    if isinstance(v, Mapping | list | tuple):
        return len(v) > 0
    return v is not None and v is not False and v != ""


def _naamruimte(v: Any) -> bool:
    """De namespace van de host of van een andere container: de tekst ``host``, ``container:…`` of ``service:…``
    (ook als element van een lijst). Een object (``network`` bij catalogusapps) en elke andere tekst niet."""
    if isinstance(v, str):
        t = v.strip().lower()
        return t == "host" or t.startswith(NAAMRUIMTE_VAN_ANDER)
    if isinstance(v, list | tuple):
        return any(isinstance(e, str) and _naamruimte(e) for e in v)
    return False


# Wanneer een sleutel uit de tabel verboden is. Voor een sleutel in een object telt de waarde zelf; voor de tekstvorm
# ("sleutel=waarde", "--sleutel waarde", "--sleutel") is de waarde een tekst of ontbreekt ze: zonder waarde telt de
# vlag als "aan", en een waarde uit LOSSE_WAARDE_UIT ("false", "0", "none", ...) als "uit".
AAN = "aan"  # object: elke waarde behalve afwezig, None of False
INHOUD = "inhoud"  # object: een niet-lege waarde (_inhoud)
NAAMRUIMTE = "naamruimte"  # object en tekst: "host", "container:…" of "service:…" (_naamruimte)
CAPABILITIES = "capabilities"  # object: alles behalve leeg of {"add": []} (_extra_capabilities)


@dataclass(frozen=True)
class Sleutelregel:
    wanneer: str
    code: str
    fout: str


_PRIVILEGED = "privileged (volledige toegang tot de host) is nooit toegestaan"
_HOST_NETWORK = (
    "het netwerk van de host (host network) alleen met een reden van minstens 10 tekens in het manifest "
    "(host_network_reason)"
)
_COMPOSE = "compose en YAML zijn nooit een installatieweg; een sleutel met compose of services wordt daarom geweigerd"
_PID = "de PID-namespace van de host of van een andere container is nooit toegestaan"
_IPC = "de IPC-namespace van de host of van een andere container is nooit toegestaan"
_CAPS = "geen extra capabilities: laat dit leeg"
_APPARAAT = (
    "apparaten (devices) zijn in deze versie niet toegestaan; de render-node voor de GPU volgt met besluit D08 (B03)"
)
_DOCKER = (
    "deze Docker- of compose-optie is in de waarden van een app nooit toegestaan (netwerk of namespace van de host "
    "of van een andere container, beveiligings- en rechtenopties, cgroups, sysctls, runtime, volumes van een andere "
    "container of een eigen opdracht)"
)
# Docker-/compose-namen die met een niet-lege waarde nooit mogen (genormaliseerd; de namen van FORBIDDEN_VALUE_KEYS in
# appstore-en-fork, plus de vlagnamen ``--device``, ``--sysctl``). ``command`` en ``entrypoint`` staan apart: die
# gelden alleen bij een catalogusapp (ALLEEN_CATALOGUS).
DOCKER_NAMEN = (
    "pidmode", "ipcmode", "uts", "utsmode", "userns", "usernsmode", "cgroup", "cgroupns", "cgroupnsmode",
    "cgroupparent", "securityopt", "securityopts", "securityoptions", "securitycontext", "apparmor",
    "apparmorprofile", "seccomp", "seccompprofile", "sysctl", "sysctls", "devicecgrouprules", "volumesfrom",
    "runtime", "allowprivilegeescalation", "command", "entrypoint",
)  # fmt: skip
ALLEEN_CATALOGUS = frozenset({"command", "entrypoint"})
# De ene tabel van verboden sleutels (S-P2-010, herstelronde 3): genormaliseerde sleutel -> regel. Compose staat er
# niet in: "compose" ergens in de genormaliseerde sleutel, of de sleutel "services", is altijd verboden.
VERBODEN_SLEUTELS: dict[str, Sleutelregel] = {
    "privileged": Sleutelregel(AAN, "privileged_verboden", _PRIVILEGED),
    "hostnetwork": Sleutelregel(AAN, "host_network_zonder_reden", _HOST_NETWORK),
    "capabilities": Sleutelregel(CAPABILITIES, "capabilities_verboden", _CAPS),
    "capadd": Sleutelregel(INHOUD, "capabilities_verboden", _CAPS),
    "devices": Sleutelregel(INHOUD, "devices_verboden", _APPARAAT),
    "device": Sleutelregel(INHOUD, "devices_verboden", _APPARAAT),
    "hostpid": Sleutelregel(AAN, "host_pid_verboden", _PID),
    "pid": Sleutelregel(NAAMRUIMTE, "host_pid_verboden", _PID),
    "hostipc": Sleutelregel(AAN, "host_ipc_verboden", _IPC),
    "ipc": Sleutelregel(NAAMRUIMTE, "host_ipc_verboden", _IPC),
    "networks": Sleutelregel(INHOUD, "netwerk_verboden", "apps delen nooit een Docker-netwerk (contract §2)"),
    "useallgpus": Sleutelregel(AAN, "gpu_zonder_d08", "GPU alleen met manifest gpu=intel_render en D08"),
    "nvidiagpuselection": Sleutelregel(INHOUD, "gpu_verboden", "NVIDIA-selectie wordt niet aangeboden"),
    # ``network`` is bij catalogusapps een gewoon object en ``--network <naam>`` kan een eigen optie van de app zijn:
    # alleen de waarde "host" of de namespace van een andere container is verboden.
    "network": Sleutelregel(NAAMRUIMTE, "catalogus_waarde_verboden", _DOCKER),
    "net": Sleutelregel(NAAMRUIMTE, "catalogus_waarde_verboden", _DOCKER),
    "networkmode": Sleutelregel(NAAMRUIMTE, "catalogus_waarde_verboden", _DOCKER),
    **{naam: Sleutelregel(INHOUD, "catalogus_waarde_verboden", _DOCKER) for naam in DOCKER_NAMEN},
}
# De fout van deze sleutels staat op het bovenliggende veld (zoals bij de ix-app: ``resources.gpus``).
OP_OUDER = frozenset({"useallgpus", "nvidiagpuselection"})
# ZFS-eigenschappen van een ixVolume (KLEIN-76; KLEIN-75 A5): de middleware van TrueNAS neemt
# ``ix_volume_config.properties`` mee bij het aanmaken van het dataset, ook ``mountpoint``. Elke aanwezigheid is
# verboden, bij de standaard Custom App en in de waarden van een catalogusapp (genormaliseerde sleutels).
# Gedrag van TrueNAS: afgeleid uit de bron (truenas/apps f142a16, middleware ece9d19); NIET GEVALIDEERD (echte NAS).
IX_VOLUME_CONFIG = "ixvolumeconfig"
ZFS_EIGENSCHAPPEN = "properties"
_ZFS_EIGENSCHAPPEN = (
    "ZFS-eigenschappen (properties) van een ixVolume zet het platform niet: TrueNAS maakt het dataset met de "
    "standaardinstellingen aan; laat properties weg"
)
# Opslagregels van de standaard Custom App (KLEIN-76, R-VEILIG-1): per type hoort er één config bij. De genormaliseerde
# namen van alle type-configs van de ix-app-bibliotheek (ook van de types die de policy niet toelaat).
HOST_PATH_CONFIG = "hostpathconfig"
OPSLAG_CONFIGS = frozenset(
    {HOST_PATH_CONFIG, IX_VOLUME_CONFIG, "tmpfsconfig", "nfsconfig", "cifsconfig", "volumeconfig"}
)
EIGEN_OPSLAG_CONFIG = {"host_path": "host_path_config", "ix_volume": "ix_volume_config", "tmpfs": "tmpfs_config"}
_VREEMDE_CONFIG = (
    "deze config hoort niet bij het type van de opslagregel (host_path_config bij host_path, ix_volume_config bij "
    "ix_volume, tmpfs_config bij tmpfs): laat haar weg"
)
# Naam van het dataset van een ixVolume (KLEIN-78; KLEIN-75 A3). TrueNAS maakt het dataset aan als
# ``<docker-dataset>/app_mounts/<app>/<dataset_name>`` (middleware ece9d19, ``plugins/apps/schema_action_context.py``,
# ``update_volumes``: ``os.path.join``) en controleert de naam nergens als pad (``normalize_ix_volume``): met "/" aan
# het begin of met ".." komt het buiten de eigen boom van de app. Toegestaan zijn alleen de tekens die ZFS in een
# datasetnaam toestaat (middleware ``plugins/zfs_/validation_utils.py``, ``validate_dataset_name`` ->
# ``truenas_pylibzfs.name_is_valid``; OpenZFS zfs-2.3.9 ``module/zcommon/zfs_namecheck.c``, ``valid_char`` en
# ``entity_namecheck``: letters, cijfers, - _ . : en spatie; "%" weigert ``zfs_validate_name`` bij het aanmaken),
# in delen gescheiden door "/": geen "/" aan het begin of eind, geen leeg deel, geen "." als deel en nergens "..".
# Hooguit 200 tekens (middleware ``ZFS_MAX_DATASET_NAME_LEN``). Geldt bij elke app, ook voor een ``ix_volume_config``
# die een tekst is (die neemt de middleware als naam). Afgeleid uit de bron; NIET GEVALIDEERD (echte NAS).
DATASETNAAM = "datasetname"
IX_VOLUME_NAAM_RE = re.compile(r"^[A-Za-z0-9_.: -]+(/[A-Za-z0-9_.: -]+)*$")
MAX_IX_VOLUME_NAAM = 200
_IX_VOLUME_NAAM = (
    "ongeldige datasetnaam: alleen letters, cijfers, - _ . : en spatie, in delen gescheiden door /; geen / aan het "
    "begin of eind, geen leeg deel, geen . als deel en nergens .. (hooguit 200 tekens)"
)
# SMB-opslag in de waarden van een catalogusapp (KLEIN-78, herstel R-VEILIG-1; KLEIN-75 A6 optie b, besluit van de
# regisseur, dicht bij twijfel). TrueNAS bouwt de mountopties van het volume uit ``cifs_config``: ``user=``,
# ``password=``, ``domain=`` en elke tekst uit ``options``, met komma's aan elkaar (truenas/apps f142a16, library
# 2.3.18, ``CifsVolume``). Een wachtwoord kan zo ook via ``options`` (``pass=``, ``password2=``, ``credentials=``) of
# een komma in ``username``/``domain`` in klare tekst mee, en eigen waarden van een catalogusapp wist de Hub nog niet
# (ADR-0030 besluit 28). Daarom is elke opslagregel van type cifs en elke niet-lege ``cifs_config`` (genormaliseerde
# sleutel en typewaarde; leeg is alleen afwezig, ``null`` of ``{}``, zoals bij de standaard Custom App) geweigerd met
# ``opslag_verboden``, tot de executor kluisverwijzingen invult (S-P2-050/070; dan moet deze weigering weer open).
# Bij de standaard Custom App was cifs al ``opslag_verboden`` (:func:`_ix_values`).
CIFS_CONFIG = "cifsconfig"
OPSLAGTYPE = "type"
CIFS = "cifs"
_SMB_VERBODEN = (
    "SMB-opslag (type cifs of cifs_config) is bij een catalogusapp nog niet toegestaan: het wachtwoord kan nog niet "
    "als kluisverwijzing worden ingevuld en zou in klare tekst in de mountopties en de opgeslagen waarden komen"
)
# Witte lijst per opslagregel en per type-config van de standaard Custom App (KLEIN-80; KLEIN-75 A2, besluit van de
# regisseur, dicht bij twijfel): precies de velden die het formulier van ix-app 1.4.8 toont (truenas/apps f142a16,
# ``ix-dev/stable/ix-app/questions.yaml``, ``storage[]``). De middleware van TrueNAS laat onbekende sleutels door
# (``extra='allow'``) en de bibliotheek (library 2.3.18) gebruikt er een aantal die het formulier niet toont:
# ``create_host_path`` (maakt een hostpad aan), ``propagation`` (mount-propagatie), ``auto_permissions`` (rechten
# zetten) en ``exec``/``mode``/``uid``/``gid`` van tmpfs. De policy beoordeelt die niet en geen geldige payload gebruikt
# ze (appstore-en-fork, ``IxStorage``), dus ze vallen buiten de lijst. Elke andere sleutel (exacte naam, zoals TrueNAS
# hem leest) geeft ``onbekend_veld``. Velden op de lijst houden hun eigen regel: ``acl`` geeft ``acl_verboden``,
# ``path`` gaat door de hostpadregel, ``dataset_name`` door de naamregel, en een niet-lege ``cifs_config`` of
# ``nfs_config`` (type cifs/nfs is verboden) is ``opslag_verboden``. Gevolg (bewust): een nieuw veld in een latere
# ix-app-versie wordt geweigerd tot deze lijst is bijgewerkt. Gedrag van TrueNAS: afgeleid uit de bron (truenas/apps
# f142a16, middleware ece9d19); NIET GEVALIDEERD (echte NAS).
IX_OPSLAGREGEL_VELDEN = frozenset(
    {"type", "read_only", "mount_path", "host_path_config", "ix_volume_config", "cifs_config", "nfs_config",
     "tmpfs_config"}
)  # fmt: skip
IX_OPSLAG_CONFIG_VELDEN = {
    "host_path_config": frozenset({"acl_enable", "acl", "path"}),
    "ix_volume_config": frozenset({"acl_enable", "dataset_name", "acl_entries"}),
    "tmpfs_config": frozenset({"size"}),
}


def _ix_opslag_witte_lijst(st: Mapping[str, Any], sw: str, eigen: str | None) -> list[Fout]:
    """De witte lijst van één opslagregel van de standaard Custom App (KLEIN-80; zie :data:`IX_OPSLAGREGEL_VELDEN`):
    onbekende sleutels op de regel en in elke type-config die een object is (``onbekend_veld``); de config van het
    eigen type is een object (``type``); ``read_only`` is true of false (``type``); ``tmpfs_config.size`` is een
    geheel getal van minstens 1 MiB (``bereik``; bibliotheek en appstore-en-fork weigeren minder)."""
    out = _only(st, sw, set(IX_OPSLAGREGEL_VELDEN))
    if "read_only" in st:
        out += _bool(st["read_only"], f"{sw}.read_only")
    for k, velden in IX_OPSLAG_CONFIG_VELDEN.items():
        cfg = st.get(k)
        if isinstance(cfg, Mapping):
            out += _only(cfg, f"{sw}.{k}", set(velden))
        elif k == eigen and cfg is not None:
            out.append(_f(f"{sw}.{k}", "type", "verwacht een object"))
    tmpfs = st.get("tmpfs_config")
    if isinstance(tmpfs, Mapping) and "size" in tmpfs:
        size = tmpfs["size"]
        if type(size) is not int or size < 1:
            out.append(_f(f"{sw}.tmpfs_config.size", "bereik", "geheel getal van minstens 1 (MiB)"))
    return out


# Koppelpad in de container van de standaard Custom App (KLEIN-80, herstel R-VEILIG-1; besluit van de regisseur, dicht
# bij twijfel). De bibliotheek geeft een tmpfs weer als tekst ``"<mount_path>:<opties>"`` (truenas/apps f142a16,
# library 2.3.18, ``Tmpfs.render``) en niemand controleert ``mount_path`` op ":" of ",": zo waren de tmpfs-opties
# (``exec``, ``suid``, ``dev``, ``mode``, ``uid``, ``gid``) toch te zetten. De middleware normaliseert het pad
# (``pydantic_utils._validate_absolute_path``: ``os.path.normpath``), dus ``/proc/.`` werd ``/proc``. Daarom alleen
# een strikt containerpad: "/" gevolgd door delen van letters, cijfers en ``. _ @ + -`` (ASCII), gescheiden door één
# "/", geen "."- of ".."-deel, geen "/" aan het eind; het genormaliseerde pad is geen verboden containerpad
# (:data:`CONTAINER_FORBIDDEN_MOUNTS`). Anders ``mount_verboden``. NIET GEVALIDEERD (echte NAS).
CONTAINERPAD_RE = re.compile(r"/[A-Za-z0-9._@+-]+(/[A-Za-z0-9._@+-]+)*")
_MOUNT_VERBODEN = (
    "absoluut pad in de container: / gevolgd door delen van letters, cijfers en . _ @ + -, gescheiden door één /; "
    "geen . of .. als deel, geen / aan het eind, niet / of een systeempad"
)
# ACL op een ixVolume van de standaard Custom App (KLEIN-80, herstel R-VEILIG-2; KLEIN-75 A4 optie a, besluit van de
# regisseur, dicht bij twijfel). TrueNAS zet een ACL zodra ``acl_entries`` niet leeg is, ook met ``acl_enable: false``
# (middleware ece9d19, ``normalize_ix_volume``: ``if acl_dict:``). Bij een ``dataset_name`` die eerder in dezelfde
# installatie staat, stopt ``normalize_ix_volume`` vóórdat het pad door het eigen ixVolume wordt vervangen; dan houdt
# ``acl_entries`` zijn eigen ``path``, slaat ``validate_acl_entries`` bij ``options.force`` de controle over en zet
# ``filesystem.add_to_acl`` een recursieve ACL op elk pad onder /mnt. Daarom: een niet-lege ``acl_entries`` (leeg is
# alleen afwezig, ``null`` of ``{}``) of een ``acl_enable`` anders dan false is ``acl_verboden``, en elke
# ``dataset_name`` staat hooguit één keer in een installatie (anders de bestaande code ``dubbel``). Gevolg (bewust):
# via het platform geen ACL op een ixVolume; geen geldige payload gebruikt dat (appstore-en-fork, ``IxVolumeConfig``:
# alleen ``acl_enable: false`` en ``dataset_name``). Afgeleid uit de bron; NIET GEVALIDEERD (echte NAS).
_DATASET_DUBBEL = "deze dataset_name staat er dubbel in: elk ixVolume hooguit één keer per installatie"


def _mount_path_problem(mount: Any) -> bool:
    """Waar als ``mount`` geen strikt containerpad is of genormaliseerd een verboden containerpad (zie
    :data:`CONTAINERPAD_RE`)."""
    if not isinstance(mount, str) or not CONTAINERPAD_RE.fullmatch(mount):
        return True
    if any(deel in (".", "..") for deel in mount.split("/")[1:]):
        return True
    return posixpath.normpath(mount) in CONTAINER_FORBIDDEN_MOUNTS


def _ix_volume_acl(cfg: Mapping[str, Any], where: str) -> list[Fout]:
    """``acl_verboden`` voor een niet-lege ``acl_entries`` of een ``acl_enable`` anders dan false in een
    ``ix_volume_config`` van de standaard Custom App (KLEIN-80, herstel R-VEILIG-2)."""
    acl_enable = cfg.get("acl_enable")
    acl_entries = cfg.get("acl_entries")
    if not (acl_enable is None or acl_enable is False) or not (acl_entries is None or acl_entries == {}):
        return [_f(where, "acl_verboden", "ACL's zet het platform niet, ook niet op een ixVolume")]
    return []


def _ix_volume_naam(v: Any, where: str) -> list[Fout]:
    """Een veilige naam voor het dataset van een ixVolume (KLEIN-78; zie :data:`IX_VOLUME_NAAM_RE`)."""
    if not isinstance(v, str):
        return [_f(where, "type", "verwacht tekst")]
    if len(v) > MAX_IX_VOLUME_NAAM or not IX_VOLUME_NAAM_RE.fullmatch(v) or ".." in v or "." in v.split("/"):
        return [_f(where, "patroon", _IX_VOLUME_NAAM)]
    return []


def _sleutel_fout(
    nk: str, waarde: Any, *, tekstvorm: bool, manifest: Mapping[str, Any], ix_app: bool
) -> tuple[str, str] | None:
    """(code, melding) als de genormaliseerde sleutel ``nk`` met deze waarde verboden is, anders ``None``. Eén regel
    voor een sleutel in een object (``tekstvorm=False``: ``waarde`` is de waarde zelf) en voor een losse tekst of
    vlag (``tekstvorm=True``: ``waarde`` is de tekst achter de sleutel, of ``None`` bij een vlag zonder waarde)."""
    if "compose" in nk or nk == "services":
        return "compose_verboden", _COMPOSE
    regel = VERBODEN_SLEUTELS.get(nk)
    if regel is None or (ix_app and nk in ALLEEN_CATALOGUS):
        return None
    if tekstvorm:
        geraakt = waarde is None or (_naamruimte(waarde) if regel.wanneer == NAAMRUIMTE else _aan(waarde))
    elif regel.wanneer == AAN:
        geraakt = waarde is not None and waarde is not False
    elif regel.wanneer == INHOUD:
        geraakt = _inhoud(waarde)
    elif regel.wanneer == NAAMRUIMTE:
        geraakt = _naamruimte(waarde)
    else:
        geraakt = _extra_capabilities(waarde)
    if not geraakt:
        return None
    if nk == "hostnetwork":
        reason = manifest.get("host_network_reason")
        if isinstance(reason, str) and len(reason.strip()) >= 10:
            return None
    if nk == "useallgpus" and manifest.get("gpu") == "intel_render":
        return None
    return regel.code, regel.fout


def _ouder(p: str) -> str:
    return p.rsplit(".", 1)[0] if "." in p else p


def _deep_forbidden(values: Any, where: str, manifest: Mapping[str, Any], ix_app: bool = False) -> list[Fout]:
    """Controles op elk niveau (ook voor catalogusapps met eigen waarden; ADR-0030 besluit 6). Dieper genest dan de
    scangrens: ``te_diep_genest`` (dicht bij twijfel).

    Sleutels gaan door de ene tabel (:func:`_sleutel_fout`), gelijk voor een object, een losse tekst in een lijst en
    de vlagvorm. De Docker-socket, een ongeldige kluisverwijzing en "unconfined" worden in elke tekst geweigerd, ook
    in vrije tekst. ``where`` is ``app_create``: de controle van een tekstwaarde in een object en de hostpad-sleutels
    gelden voor wat onder ``values`` staat (``app_name``, ``catalog_app``, ``train`` en ``version`` hebben een eigen
    patroon). ``ix_app``: de waarden zijn van de standaard Custom App. Daar is het schema vast (:func:`_ix_values`):
    een tekstwaarde in een object wordt geen Docker-optie en krijgt de controle van een losse tekst niet, en de
    teksten direct in ``values.command`` en ``values.entrypoint`` zijn de opdracht van het proces in de container
    (geen vlag- of bindcontrole)."""
    out: list[Fout] = []
    try:
        alles = _walk(values, where)
    except TeDiepGenest:
        return [_f(where, "te_diep_genest", f"hooguit {MAX_DIEPTE} niveaus diep genest")]
    opdracht = re.compile(re.escape(where) + r"\.values\.(?:command|entrypoint)\[\d+\]") if ix_app else None
    waarden = (f"{where}.values.", f"{where}.values[")
    for p, k, v, paarwaarde in alles:
        nk = None if k is None else _nk(k)
        in_waarden = p.startswith(waarden)
        catalogus_waarde = not ix_app and in_waarden
        if nk is not None:
            fout = _sleutel_fout(nk, v, tekstvorm=False, manifest=manifest, ix_app=ix_app)
            if fout:
                out.append(_f(_ouder(p) if nk in OP_OUDER else p, *fout))
            if nk == IX_VOLUME_CONFIG and isinstance(v, Mapping):
                out += [
                    _f(f"{p}.{e}", "zfs_eigenschappen_verboden", _ZFS_EIGENSCHAPPEN)
                    for e in v
                    if _nk(e) == ZFS_EIGENSCHAPPEN
                ]
                for e, naam in v.items():
                    if _nk(e) == DATASETNAAM:
                        out += _ix_volume_naam(naam, f"{p}.{e}")
            elif nk == IX_VOLUME_CONFIG and isinstance(v, str):
                out += _ix_volume_naam(v, p)
            if catalogus_waarde and (
                (nk == CIFS_CONFIG and v is not None and v != {})
                or (nk == OPSLAGTYPE and isinstance(v, str) and _nk(v) == CIFS)
            ):
                out.append(_f(p, "opslag_verboden", _SMB_VERBODEN))
            vast_veld = k in ("host_path", "path") and p.endswith(("host_path_config.path", ".host_path"))
            pad_sleutel = (nk in HOSTPAD_SLEUTELS_OVERAL and in_waarden) or (
                catalogus_waarde and nk in HOSTPAD_SLEUTELS
            )
            hostpad_waarde = pad_sleutel and isinstance(v, str) and v.startswith("/")
            if vast_veld or hostpad_waarde:
                problem = host_path_problem(v)
                if problem:
                    out.append(_f(p, "hostpad_verboden", problem))
        if not isinstance(v, str):
            continue
        if "docker.sock" in v:
            out.append(_f(p, "docker_socket_verboden", "een Docker-socket mag nooit in een container"))
        if "unconfined" in v.lower():
            out.append(
                _f(p, "catalogus_waarde_verboden", "een beveiligingsprofiel uitzetten ('unconfined') is verboden")
            )
        if v.startswith("vault://") and not VAULT_REF_RE.fullmatch(v):
            out.append(_f(p, "vault_ref_ongeldig", "alleen vault://app/<app_id>/<parameter>"))
        if nk is None:
            if opdracht is None or not opdracht.fullmatch(p):
                out += _losse_tekst(v, p, manifest, ix_app)
        elif catalogus_waarde and not paarwaarde and nk not in VRIJE_TEKST_SLEUTELS:
            out += _losse_tekst(v, p, manifest, ix_app)
    return out


def _host_path_config(waarde: Any, where: str, *, pad_verplicht: bool) -> list[Fout]:
    """``host_path_config`` van een opslagregel van de standaard Custom App, bij elk type (KLEIN-76, R-VEILIG-1): een
    aanwezig ``acl``-blok of ``acl_enable`` anders dan false is een ACL (``acl_verboden``; TrueNAS normaliseert het
    ``acl``-blok ook bij ``acl_enable: false`` en in een regel van een ander type), en elk pad (``path`` en
    ``acl.path``) gaat door :func:`host_path_problem`. ``pad_verplicht``: bij type host_path moet ``path`` er zijn.
    Gedrag van TrueNAS: afgeleid uit de bron (truenas/apps f142a16, middleware ece9d19); NIET GEVALIDEERD
    (echte NAS)."""
    out: list[Fout] = []
    cfg = waarde or {}
    is_object = isinstance(cfg, Mapping)
    if not is_object or cfg.get("acl_enable") not in (None, False) or "acl" in cfg:
        out.append(_f(where, "acl_verboden", "ACL's zet het platform niet"))
    if pad_verplicht or (is_object and "path" in cfg):
        problem = host_path_problem(cfg.get("path") if is_object else None)
        if problem:
            out.append(_f(f"{where}.path", "hostpad_verboden", problem))
    acl = cfg.get("acl") if is_object else None
    if isinstance(acl, Mapping) and "path" in acl:
        problem = host_path_problem(acl["path"])
        if problem:
            out.append(_f(f"{where}.acl.path", "hostpad_verboden", problem))
    return out


def _ix_values(values: Mapping[str, Any], manifest: Mapping[str, Any]) -> list[Fout]:
    w = "parameters.app_create.values"
    out = _only(values, w, set(IX_VALUES_KEYS), {"image", "restart_policy", "TZ"})
    out += _image_ref(values.get("image"), f"{w}.image", manifest.get("image_digest"))
    if values.get("restart_policy") not in RESTART_POLICIES:
        out.append(_f(f"{w}.restart_policy", "waarde", "expliciet: no, unless-stopped, on-failure of always"))
    out += _text(values.get("TZ"), f"{w}.TZ", max_len=64) if "TZ" in values else []
    if values.get("privileged") not in (None, False):
        out.append(_f(f"{w}.privileged", "privileged_verboden", _PRIVILEGED))
    caps = values.get("capabilities") or {}
    if not isinstance(caps, Mapping) or set(caps) - {"add"} or (caps.get("add") or []):
        out.append(_f(f"{w}.capabilities", "capabilities_verboden", _CAPS))
    if values.get("devices"):
        out.append(_f(f"{w}.devices", "devices_verboden", _APPARAAT))
    if values.get("networks"):
        out.append(_f(f"{w}.networks", "netwerk_verboden", "apps delen nooit een Docker-netwerk (contract §2)"))
    if values.get("run_as_custom_user") is True:
        run_as = values.get("run_as")
        if not isinstance(run_as, Mapping) or any(
            type(run_as.get(k)) is not int or run_as[k] < 1 for k in ("user", "group")
        ):
            out.append(_f(f"{w}.run_as", "root_verboden", "custom user moet een gewone uid/gid (≥ 1) zijn"))
    envs = values.get("envs") or []
    if not isinstance(envs, list) or len(envs) > 100:
        out.append(_f(f"{w}.envs", "lijst", "hooguit 100 variabelen"))
    else:
        seen: set[str] = set()
        for i, e in enumerate(envs):
            ew = f"{w}.envs[{i}]"
            out += _only(e, ew, {"name", "value"}, {"name", "value"})
            if not isinstance(e, Mapping):
                continue
            name = e.get("name")
            out += _text(name, f"{ew}.name", max_len=128, pattern=ENV_NAME_RE)
            if isinstance(name, str):
                if name.upper().startswith("HUB_"):
                    out.append(_f(f"{ew}.name", "reserved_env", "HUB_* zet alleen de Hub zelf (contract §3.2)"))
                if name in seen:
                    out.append(_f(f"{ew}.name", "dubbel", "variabele staat er dubbel in"))
                seen.add(name)
            out += _text(e.get("value"), f"{ew}.value", min_len=0, max_len=4096)
    storage = values.get("storage") or []
    if not isinstance(storage, list) or len(storage) > 20:
        out.append(_f(f"{w}.storage", "lijst", "hooguit 20 opslagregels"))
    else:
        datasets: set[str] = set()
        for i, st in enumerate(storage):
            sw = f"{w}.storage[{i}]"
            if not isinstance(st, Mapping):
                out.append(_f(sw, "type", "verwacht een object"))
                continue
            typ = st.get("type")
            if typ not in ("host_path", "ix_volume", "tmpfs"):
                out.append(_f(f"{sw}.type", "opslag_verboden", "alleen host_path, ix_volume of tmpfs"))
            if _mount_path_problem(st.get("mount_path")):
                out.append(_f(f"{sw}.mount_path", "mount_verboden", _MOUNT_VERBODEN))
            eigen = EIGEN_OPSLAG_CONFIG.get(typ) if isinstance(typ, str) else None
            out += _ix_opslag_witte_lijst(st, sw, eigen)
            ixcfg = st.get("ix_volume_config")
            if isinstance(ixcfg, Mapping):
                out += _ix_volume_acl(ixcfg, f"{sw}.ix_volume_config")
                naam = ixcfg.get("dataset_name")
                if isinstance(naam, str):
                    if naam in datasets:
                        out.append(_f(f"{sw}.ix_volume_config.dataset_name", "dubbel", _DATASET_DUBBEL))
                    datasets.add(naam)
            # Een config van een ander type, met inhoud, wordt geweigerd (KLEIN-76, R-VEILIG-1; dicht bij twijfel):
            # TrueNAS laat hem door en normaliseert een aanwezige ix_volume_config (dataset) of host_path_config.acl
            # (ACL) ook bij een ander type. Leeg is alleen afwezig, null of {}. Gedrag van TrueNAS: afgeleid uit de
            # bron (truenas/apps f142a16, middleware ece9d19); NIET GEVALIDEERD (echte NAS).
            out += [
                _f(f"{sw}.{k}", "opslag_verboden", _VREEMDE_CONFIG)
                for k, v in st.items()
                if _nk(k) in OPSLAG_CONFIGS and k != eigen and v is not None and v != {}
            ]
            # host_path_config bij elk type, ook in een andere schrijfwijze (KLEIN-76, R-VEILIG-1).
            hostpad_cfgs = [k for k in st if _nk(k) == HOST_PATH_CONFIG]
            if typ == "host_path" and "host_path_config" not in st:
                hostpad_cfgs.append("host_path_config")
            for k in hostpad_cfgs:
                verplicht = typ == "host_path" and k == "host_path_config"
                out += _host_path_config(st.get(k), f"{sw}.{k}", pad_verplicht=verplicht)
    ports = values.get("ports") or []
    if not isinstance(ports, list) or len(ports) > 20:
        out.append(_f(f"{w}.ports", "lijst", "hooguit 20 poorten"))
    else:
        for i, pt in enumerate(ports):
            pw = f"{w}.ports[{i}]"
            out += _only(pt, pw, {"bind_mode", "port_number", "container_port", "protocol", "host_ips"},
                         {"port_number", "container_port", "protocol"})  # fmt: skip
            if not isinstance(pt, Mapping):
                continue
            out += _intr(pt.get("port_number"), f"{pw}.port_number", 1, 65535)
            out += _intr(pt.get("container_port"), f"{pw}.container_port", 1, 65535)
            if pt.get("protocol") not in ("tcp", "udp"):
                out.append(_f(f"{pw}.protocol", "waarde", "tcp of udp"))
            if pt.get("bind_mode", "published") not in ("published", "exposed"):
                out.append(_f(f"{pw}.bind_mode", "waarde", "published of exposed"))
            for j, ip in enumerate(pt.get("host_ips") or []):
                try:
                    ipaddress.ip_address(str(ip))
                except ValueError:
                    out.append(_f(f"{pw}.host_ips[{j}]", "ip", "geen IP-adres"))
    resources = values.get("resources")
    if not isinstance(resources, Mapping):
        out.append(_f(f"{w}.resources", "verplicht", "resources (limieten) zijn verplicht"))
    else:
        gpus = resources.get("gpus") or {}
        if isinstance(gpus, Mapping) and gpus.get("use_all_gpus") is True and manifest.get("gpu") != "intel_render":
            out.append(_f(f"{w}.resources.gpus", "gpu_zonder_d08", "GPU alleen met manifest gpu=intel_render en D08"))
        if isinstance(gpus, Mapping) and gpus.get("nvidia_gpu_selection"):
            out.append(_f(f"{w}.resources.gpus", "gpu_verboden", "NVIDIA-selectie wordt niet aangeboden"))
    for key in ("entrypoint", "command"):
        seq = values.get(key) or []
        if not isinstance(seq, list) or len(seq) > 32 or not all(isinstance(s, str) and len(s) <= 1024 for s in seq):
            out.append(_f(f"{w}.{key}", "lijst", "lijst van hooguit 32 teksten (≤ 1024 tekens)"))
    return out


def validate_manifest_meta(manifest: Any) -> list[Fout]:
    w = "parameters.manifest"
    allowed = {
        "app_id",
        "manifest_sha256",
        "version",
        "image_digest",
        "host_network_reason",
        "install_reason",
        "gpu",
        "post_install_checks",
        "rpo_uren",
    }
    out = _only(manifest, w, allowed, {"app_id"})
    if not isinstance(manifest, Mapping):
        return out
    out += _text(manifest.get("app_id"), f"{w}.app_id", max_len=64, pattern=re.compile(r"^[a-z][a-z0-9_-]{0,63}$"))
    if "manifest_sha256" in manifest:
        out += _text(manifest["manifest_sha256"], f"{w}.manifest_sha256", max_len=71, pattern=SHA_RE)
    if "image_digest" in manifest:
        out += _text(manifest["image_digest"], f"{w}.image_digest", max_len=71, pattern=DIGEST_RE)
    for k in ("host_network_reason", "install_reason"):
        if manifest.get(k) is not None:
            out += _text(manifest[k], f"{w}.{k}", max_len=500)
    if "gpu" in manifest and manifest["gpu"] not in ("none", "intel_render"):
        out.append(_f(f"{w}.gpu", "waarde", "none of intel_render"))
    if "rpo_uren" in manifest:
        out += _intr(manifest["rpo_uren"], f"{w}.rpo_uren", 1, 24 * 365)
    checks = manifest.get("post_install_checks") or []
    if not isinstance(checks, list) or len(checks) > 20:
        out.append(_f(f"{w}.post_install_checks", "lijst", "hooguit 20 controles"))
    else:
        for i, c in enumerate(checks):
            cw = f"{w}.post_install_checks[{i}]"
            out += _only(c, cw, {"id", "soort", "beschrijving_nl"}, {"id", "soort", "beschrijving_nl"})
            if isinstance(c, Mapping):
                out += _text(c.get("id"), f"{cw}.id", max_len=64)
                if c.get("soort") not in ("http", "handmatig"):
                    out.append(_f(f"{cw}.soort", "waarde", "http of handmatig"))
                out += _text(c.get("beschrijving_nl"), f"{cw}.beschrijving_nl", max_len=500)
    return out


def validate_install(params: Mapping[str, Any], target: Mapping[str, Any]) -> list[Fout]:
    out = _only(params, "parameters", {"app_create", "manifest", "appstore_preview_hash"}, {"app_create", "manifest"})
    manifest = params.get("manifest")
    out += validate_manifest_meta(manifest)
    manifest = manifest if isinstance(manifest, Mapping) else {}
    if "appstore_preview_hash" in params:
        out += _text(params["appstore_preview_hash"], "parameters.appstore_preview_hash", max_len=71, pattern=SHA_RE)
    ac = params.get("app_create")
    w = "parameters.app_create"
    out += _only(ac, w, {"app_name", "custom_app", "catalog_app", "train", "version", "values"},
                 {"app_name", "catalog_app", "train", "version", "values"})  # fmt: skip
    if not isinstance(ac, Mapping):
        return out
    out += _deep_forbidden(ac, w, manifest, ix_app=ac.get("catalog_app") == IX_APP)
    if ac.get("custom_app") not in (None, False):
        out.append(
            _f(
                f"{w}.custom_app",
                "compose_verboden",
                "custom_app=true is een compose-app (Install via YAML) en is nooit toegestaan; installeer als "
                "standaard Custom App (ix-app)",
            )
        )
    out += _text(ac.get("app_name"), f"{w}.app_name", max_len=40, pattern=APP_NAME_RE)
    if ac.get("app_name") != target.get("app_id"):
        out.append(_f(f"{w}.app_name", "doel_verschilt", "app_name moet gelijk zijn aan target.app_id"))
    out += _text(ac.get("catalog_app"), f"{w}.catalog_app", max_len=64, pattern=CATALOG_APP_RE)
    out += _text(ac.get("train"), f"{w}.train", max_len=32, pattern=TRAIN_RE)
    version = ac.get("version")
    if not isinstance(version, str) or not VERSION_RE.fullmatch(version):
        out.append(_f(f"{w}.version", "versie_exact", "een exacte versie (nooit latest)"))
    values = ac.get("values")
    if not isinstance(values, Mapping):
        out.append(_f(f"{w}.values", "type", "verwacht een object"))
        return out
    out += _size(values, f"{w}.values", MAX_VALUES_BYTES)
    if ac.get("catalog_app") == IX_APP:
        if ac.get("train") != "stable":
            out.append(_f(f"{w}.train", "waarde", "de standaard Custom App (ix-app) staat in de trein stable"))
        out += _ix_values(values, manifest)
    else:
        reason = manifest.get("install_reason")
        if not (isinstance(reason, str) and reason.strip()):
            out.append(
                _f("parameters.manifest.install_reason", "install_reason_ontbreekt", "catalogusapp vraagt een reden")
            )
    # Dubbele meldingen (zelfde veld en code) één keer tonen.
    uniq: dict[tuple[str, str], Fout] = {}
    for f in out:
        uniq.setdefault((f.veld, f.code), f)
    return list(uniq.values())


def expected_image(params: Mapping[str, Any]) -> dict[str, str | None] | None:
    """Verwachte image na ``app.install``/``app.update`` (voor de digest-readback); ``None`` bij een catalogusapp."""
    img: Any = None
    digest: Any = None
    if "app_create" in params:
        ac = params.get("app_create") or {}
        if not isinstance(ac, Mapping) or ac.get("catalog_app") != IX_APP:
            return None
        img = (ac.get("values") or {}).get("image")
        digest = (params.get("manifest") or {}).get("image_digest")
    elif "image" in params:
        img, digest = params.get("image"), params.get("image_digest")
    if not isinstance(img, Mapping):
        return None
    tag = str(img.get("tag") or "")
    version, _sep, in_tag = tag.partition("@")
    return {"repository": str(img.get("repository") or ""), "tag": tag, "versie": version, "digest": in_tag or digest}


def verwachte_catalogus(params: Mapping[str, Any]) -> str | None:
    """De catalogusapp die ``app.install`` gaat installeren (``app_create.catalog_app``), voor de herkenning van het
    doel; ``None`` bij de standaard Custom App (``ix-app`` zegt niets over de inhoud) of zonder ``app_create``."""
    ac = params.get("app_create") if isinstance(params, Mapping) else None
    cat = ac.get("catalog_app") if isinstance(ac, Mapping) else None
    if not isinstance(cat, str) or not cat.strip() or cat.strip().lower() == IX_APP:
        return None
    return cat.strip().lower()


def vault_refs(value: Any) -> list[str]:
    """Alle ``vault://app/...``-verwijzingen (geheimen die de Hub pas bij verzenden invult, contract §3.1 a)."""
    return sorted({v for _p, _k, v, _paar in _walk(value) if isinstance(v, str) and VAULT_REF_RE.fullmatch(v)})
