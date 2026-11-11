"""Policybestanden laden en de ``policy_hash`` berekenen (contract 1.3 §8, ADR-0030).

- Alle ``*.yaml`` in de policymap, gesorteerd op bestandsnaam. Andere bestanden (README, de hashkopie) tellen niet mee.
- ``policy_hash`` = ``"sha256:" + sha256("asm-policy-hash-v1\\n" + per bestand naam "\\n" lengte "\\n" bytes "\\n")``
  over de **ruwe bytes**: de Hub en de executor rekenen hem uit hun eigen read-only kopie uit en vergelijken.
- Het schema is streng: een onbekend veld, een ontbrekend veld of een ongeldige waarde → :class:`PolicyError`. Een
  dienst met een ongeldig beleid voert niets uit (fail-closed).
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

SCHEMA = "asm-policy/1"
HASH_PREFIX = b"asm-policy-hash-v1\n"
RISK_CLASSES = ("R0", "R1", "R2", "R3")
RISK_RANK = {k: i for i, k in enumerate(RISK_CLASSES)}
IMAGE_POLICY_DIR = Path("/usr/local/share/asm/policy")
UITVOERDER_RE = re.compile(r"^(executor|hub:gotify|eigenaar:[a-z][a-z0-9-]{1,63})$")
ACTION_ID_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){1,4}$")
DOELEN = ("app", "app_nieuw", "dataset", "snapshot", "geen", "eigenaar")
PARAMETER_SCHEMAS = (
    "leeg",
    "app_install",
    "app_update",
    "app_rollback",
    "snapshot_create",
    "snapshot_clone",
    "notification_send",
    "eigenaar",
)


class PolicyError(ValueError):
    """Het beleid is onleesbaar of ongeldig; de dienst voert niets uit."""


@dataclass(frozen=True)
class ActieDef:
    action_id: str
    omschrijving: str
    uitvoerder: str
    truenas: tuple[str, ...]
    doel: str
    klasse: str
    klasse_kritiek: str | None
    parameters: str
    requires_backup: bool
    ai_mag_voorstellen: bool
    opslagmutatie: bool
    cooldown_seconden: int
    max_per_uur: int
    timeout_seconden: int
    verwacht: dict[str, Any]

    @property
    def via_executor(self) -> bool:
        return self.uitvoerder == "executor"

    @property
    def eigenaar(self) -> str | None:
        return self.uitvoerder.split(":", 1)[1] if self.uitvoerder.startswith("eigenaar:") else None


@dataclass(frozen=True)
class Patroon:
    id: str
    code: str
    patroon: re.Pattern[str]
    reden_nl: str


@dataclass(frozen=True)
class Regel:
    id: str
    code: str
    reden_nl: str


@dataclass(frozen=True)
class Beschermd:
    id: str
    app: str
    acties: tuple[str, ...] | None  # None = alle acties
    code: str
    reden_nl: str


@dataclass(frozen=True)
class Policy:
    hash: str
    files: tuple[str, ...]
    acties: dict[str, ActieDef]
    verboden: tuple[Patroon, ...]
    boiler_id: str
    boiler_code: str
    boiler_patronen: tuple[re.Pattern[str], ...]
    boiler_reden: str
    gereserveerd: tuple[Patroon, ...]
    dynamisch: dict[str, Regel]
    herkenning: dict[str, tuple[str, ...]]
    kritiek: frozenset[str]
    beschermd: tuple[Beschermd, ...]
    sandbox_dataset: str
    bron: Path = field(default=Path("."))

    def actie(self, action_id: str) -> ActieDef | None:
        return self.acties.get(action_id)

    def executor_allowlist(self) -> list[str]:
        return sorted(a for a, d in self.acties.items() if d.via_executor)


def default_policy_dir() -> Path:
    """De map in de image wint altijd (read-only ingebakken; een omgevingsvariabele kan het beleid in een image dus niet
    omleiden). Buiten een image: ``ASM_POLICY_DIR`` (tests), anders ``policy/`` in de repo (ontwikkeling)."""
    if IMAGE_POLICY_DIR.is_dir():
        return IMAGE_POLICY_DIR
    env = os.environ.get("ASM_POLICY_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[4] / "policy"


def policy_files(path: Path) -> list[Path]:
    return sorted((p for p in path.glob("*.yaml") if p.is_file()), key=lambda p: p.name)


def policy_hash(path: Path) -> str:
    files = policy_files(path)
    if not files:
        raise PolicyError(f"geen policybestanden in {path}")
    h = hashlib.sha256(HASH_PREFIX)
    for p in files:
        data = p.read_bytes()
        h.update(p.name.encode() + b"\n" + str(len(data)).encode() + b"\n" + data + b"\n")
    return "sha256:" + h.hexdigest()


# ------------------------------------------------------------------ strenge schemacontrole
def _keys(obj: Any, where: str, required: set[str], optional: set[str] = frozenset()) -> dict[str, Any]:  # type: ignore[assignment]
    if not isinstance(obj, dict):
        raise PolicyError(f"{where}: verwacht een object")
    missing = required - obj.keys()
    extra = obj.keys() - required - optional
    if missing:
        raise PolicyError(f"{where}: ontbrekend veld {sorted(missing)}")
    if extra:
        raise PolicyError(f"{where}: onbekend veld {sorted(extra)}")
    return obj


def _str(v: Any, where: str) -> str:
    if not isinstance(v, str) or not v.strip():
        raise PolicyError(f"{where}: verwacht tekst")
    return v


def _bool(v: Any, where: str) -> bool:
    if not isinstance(v, bool):
        raise PolicyError(f"{where}: verwacht true/false")
    return v


def _int(v: Any, where: str, lo: int, hi: int) -> int:
    if type(v) is not int or not lo <= v <= hi:
        raise PolicyError(f"{where}: verwacht een geheel getal {lo}–{hi}")
    return v


def _klasse(v: Any, where: str) -> str:
    if v not in RISK_CLASSES:
        raise PolicyError(f"{where}: risicoklasse moet R0–R3 zijn")
    return str(v)


def _regex(v: Any, where: str) -> re.Pattern[str]:
    try:
        return re.compile(_str(v, where))
    except re.error as exc:
        raise PolicyError(f"{where}: ongeldige reguliere expressie ({exc})") from exc


def _schema(doc: Any, name: str) -> dict[str, Any]:
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        raise PolicyError(f"{name}: schema moet '{SCHEMA}' zijn")
    return doc


def _actie(action_id: str, raw: Any) -> ActieDef:
    where = f"acties.yaml:{action_id}"
    if not ACTION_ID_RE.match(action_id):
        raise PolicyError(f"{where}: ongeldige action_id")
    d = _keys(
        raw,
        where,
        {
            "omschrijving",
            "uitvoerder",
            "truenas",
            "doel",
            "klasse",
            "parameters",
            "requires_backup",
            "ai_mag_voorstellen",
            "opslagmutatie",
            "cooldown_seconden",
            "max_per_uur",
            "timeout_seconden",
            "verwacht",
        },
        {"klasse_kritiek"},
    )
    uitvoerder = _str(d["uitvoerder"], f"{where}.uitvoerder")
    if not UITVOERDER_RE.match(uitvoerder):
        raise PolicyError(f"{where}.uitvoerder: onbekende uitvoerder")
    truenas = d["truenas"]
    if not isinstance(truenas, list) or not all(isinstance(m, str) and m for m in truenas):
        raise PolicyError(f"{where}.truenas: verwacht een lijst methodenamen")
    if (uitvoerder == "executor") != bool(truenas):
        raise PolicyError(f"{where}.truenas: alleen (en altijd) bij uitvoerder executor")
    doel = _str(d["doel"], f"{where}.doel")
    if doel not in DOELEN:
        raise PolicyError(f"{where}.doel: onbekend doel")
    params = _str(d["parameters"], f"{where}.parameters")
    if params not in PARAMETER_SCHEMAS:
        raise PolicyError(f"{where}.parameters: onbekend parameterschema")
    klasse = _klasse(d["klasse"], f"{where}.klasse")
    kritiek = d.get("klasse_kritiek")
    if kritiek is not None:
        kritiek = _klasse(kritiek, f"{where}.klasse_kritiek")
        if RISK_RANK[kritiek] < RISK_RANK[klasse]:
            raise PolicyError(f"{where}.klasse_kritiek: mag nooit lager zijn dan klasse")
    verwacht = d["verwacht"]
    if not isinstance(verwacht, dict) or not set(verwacht) <= {"staat", "aanwezig", "afwezig"}:
        raise PolicyError(f"{where}.verwacht: alleen staat, aanwezig of afwezig")
    return ActieDef(
        action_id=action_id,
        omschrijving=_str(d["omschrijving"], f"{where}.omschrijving"),
        uitvoerder=uitvoerder,
        truenas=tuple(truenas),
        doel=doel,
        klasse=klasse,
        klasse_kritiek=kritiek,
        parameters=params,
        requires_backup=_bool(d["requires_backup"], f"{where}.requires_backup"),
        ai_mag_voorstellen=_bool(d["ai_mag_voorstellen"], f"{where}.ai_mag_voorstellen"),
        opslagmutatie=_bool(d["opslagmutatie"], f"{where}.opslagmutatie"),
        cooldown_seconden=_int(d["cooldown_seconden"], f"{where}.cooldown_seconden", 0, 86400),
        max_per_uur=_int(d["max_per_uur"], f"{where}.max_per_uur", 1, 120),
        timeout_seconden=_int(d["timeout_seconden"], f"{where}.timeout_seconden", 10, 3600),
        verwacht=dict(verwacht),
    )


def _patroon(raw: Any, where: str) -> Patroon:
    d = _keys(raw, where, {"id", "code", "patroon", "reden_nl"})
    return Patroon(
        _str(d["id"], f"{where}.id"),
        _str(d["code"], f"{where}.code"),
        _regex(d["patroon"], f"{where}.patroon"),
        _str(d["reden_nl"], f"{where}.reden_nl"),
    )


def load_policy(path: Path | None = None) -> Policy:
    """Lees en controleer het beleid; ``PolicyError`` bij elk probleem (fail-closed)."""
    path = path or default_policy_dir()
    files = {p.name: p for p in policy_files(path)}
    for needed in ("acties.yaml", "blokkades.yaml", "apps.yaml"):
        if needed not in files:
            raise PolicyError(f"{needed} ontbreekt in {path}")
    try:
        docs = {name: yaml.safe_load(p.read_text(encoding="utf-8")) for name, p in files.items()}
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise PolicyError(f"policy onleesbaar: {type(exc).__name__}") from exc
    acties_doc = _keys(_schema(docs["acties.yaml"], "acties.yaml"), "acties.yaml", {"schema", "acties"})
    if not isinstance(acties_doc["acties"], dict) or not acties_doc["acties"]:
        raise PolicyError("acties.yaml: acties ontbreekt")
    acties = {str(k): _actie(str(k), v) for k, v in acties_doc["acties"].items()}

    blk = _keys(
        _schema(docs["blokkades.yaml"], "blokkades.yaml"),
        "blokkades.yaml",
        {"schema", "verboden_patronen", "boiler", "gereserveerd", "dynamisch"},
    )
    verboden = tuple(
        _patroon(p, f"blokkades.yaml:verboden_patronen[{i}]") for i, p in enumerate(blk["verboden_patronen"])
    )
    for a in acties:
        hit = next((v for v in verboden if v.patroon.fullmatch(a)), None)
        if hit is not None:
            raise PolicyError(f"acties.yaml:{a}: valt onder verboden patroon {hit.id}")
    boiler = _keys(blk["boiler"], "blokkades.yaml:boiler", {"id", "code", "patronen", "reden_nl"})
    if not isinstance(boiler["patronen"], list) or not boiler["patronen"]:
        raise PolicyError("blokkades.yaml:boiler.patronen: verwacht een lijst")
    boiler_patronen = tuple(re.compile(_str(p, "boiler.patronen"), re.IGNORECASE) for p in boiler["patronen"])
    gereserveerd = tuple(_patroon(p, f"blokkades.yaml:gereserveerd[{i}]") for i, p in enumerate(blk["gereserveerd"]))
    dyn_raw = _keys(
        blk["dynamisch"],
        "blokkades.yaml:dynamisch",
        {"pool", "backup", "noodstop", "cooldown", "frequentie", "checkpoint"},
    )
    dynamisch = {}
    for k, v in dyn_raw.items():
        d = _keys(v, f"blokkades.yaml:dynamisch.{k}", {"id", "code", "reden_nl"})
        dynamisch[k] = Regel(_str(d["id"], "id"), _str(d["code"], "code"), _str(d["reden_nl"], "reden_nl"))

    apps_doc = _keys(
        _schema(docs["apps.yaml"], "apps.yaml"),
        "apps.yaml",
        {"schema", "herkenning", "kritiek", "beschermd", "sandbox"},
    )
    herkenning: dict[str, tuple[str, ...]] = {}
    if not isinstance(apps_doc["herkenning"], dict):
        raise PolicyError("apps.yaml:herkenning: verwacht een object")
    for app, v in apps_doc["herkenning"].items():
        d = _keys(v, f"apps.yaml:herkenning.{app}", {"namen"})
        namen = d["namen"]
        if not isinstance(namen, list) or not namen or not all(isinstance(n, str) and n for n in namen):
            raise PolicyError(f"apps.yaml:herkenning.{app}.namen: verwacht een lijst")
        herkenning[str(app)] = tuple(n.lower() for n in namen)
    kritiek = apps_doc["kritiek"]
    if not isinstance(kritiek, list) or not all(isinstance(k, str) for k in kritiek):
        raise PolicyError("apps.yaml:kritiek: verwacht een lijst")
    beschermd: list[Beschermd] = []
    for i, raw in enumerate(apps_doc["beschermd"] or []):
        where = f"apps.yaml:beschermd[{i}]"
        d = _keys(raw, where, {"id", "app", "acties", "code", "reden_nl"})
        acties_b = d["acties"]
        if acties_b == "*":
            parsed: tuple[str, ...] | None = None
        elif isinstance(acties_b, list) and all(isinstance(a, str) for a in acties_b):
            parsed = tuple(acties_b)
        else:
            raise PolicyError(f"{where}.acties: '*' of een lijst action_id's")
        beschermd.append(
            Beschermd(
                _str(d["id"], f"{where}.id"),
                _str(d["app"], f"{where}.app"),
                parsed,
                _str(d["code"], f"{where}.code"),
                _str(d["reden_nl"], f"{where}.reden_nl"),
            )
        )
    sandbox = _keys(apps_doc["sandbox"], "apps.yaml:sandbox", {"dataset_naam"})
    sandbox_naam = _str(sandbox["dataset_naam"], "apps.yaml:sandbox.dataset_naam")
    if not re.fullmatch(r"[a-z][a-z0-9-]{2,40}", sandbox_naam):
        raise PolicyError("apps.yaml:sandbox.dataset_naam: ongeldig")
    return Policy(
        hash=policy_hash(path),
        files=tuple(sorted(files)),
        acties=acties,
        verboden=verboden,
        boiler_id=_str(boiler["id"], "boiler.id"),
        boiler_code=_str(boiler["code"], "boiler.code"),
        boiler_patronen=boiler_patronen,
        boiler_reden=_str(boiler["reden_nl"], "boiler.reden_nl"),
        gereserveerd=gereserveerd,
        dynamisch=dynamisch,
        herkenning=herkenning,
        kritiek=frozenset(kritiek),
        beschermd=tuple(beschermd),
        sandbox_dataset=sandbox_naam,
        bron=path,
    )


def is_read_only(path: Path) -> bool:
    """``True`` als het huidige proces de policymap en -bestanden niet kan wijzigen (in de image: eigenaar root,
    0555/0444, proces als 568). In ontwikkeling is de repo-map schrijfbaar; diensten tonen dat als waarschuwing en
    weigeren uitvoering als ze streng staan ingesteld."""
    if os.access(path, os.W_OK):
        return False
    return not any(os.access(p, os.W_OK) for p in policy_files(path))
