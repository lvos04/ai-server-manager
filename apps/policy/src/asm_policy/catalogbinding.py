"""Bron- en doelbinding van een uitvoerbare planstap (contract 1.3 §8.1, M1; ADR-0032 besluiten 1, 2 en 6).

Eén gedeelde controle voor Hub én executor: ``parameters.catalog_binding`` van ``app.install`` moet precies één regel
uit de witte lijst ``catalogus.yaml`` (onder de ``policy_hash`` in beide images) raken, en de werkelijke payload moet
bij die regel passen. De executor kent geen appstore of planner; deze regel is zijn eigen anker. De Hub controleert
daarnaast zelf de handtekening van de appstore (``hub.catalog.plannen``); dat kan de executor niet.

Fail-closed: een onbekend, ontbrekend of afwijkend veld, een lege witte lijst of meer dan één passende regel geeft een
:class:`~asm_policy.params.Fout`, nooit een stilzwijgende vrijgave. Kluisplekken (§8.3, M2): alleen wat de eigen regel
als ``kluisplekken`` noemt, met precies de verwijzingen en revisies uit ``vault_refs`` en de ``koppeling`` die bij een
koppelbare eigen dienst hoort. Het type van een plek volgt alleen uit de regel.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from asm_policy._asf_c12 import has_account_word, is_login_name, is_secret_name
from asm_policy.params import (
    APP_NAME_RE,
    CATALOG_APP_RE,
    ENV_NAME_RE,
    IX_APP,
    SHA_RE,
    TRAIN_RE,
    UUID_RE,
    VERSION_RE,
    Fout,
    _f,
    _only,
    _text,
    expected_image,
    vault_refs,
)

COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
KEY_ID_RE = re.compile(r"^[0-9a-f]{16}$")
B64_RE = re.compile(r"^[A-Za-z0-9+/]{40,200}={0,2}$")
REVISION_RE = re.compile(r"^[A-Za-z0-9:._@-]{1,128}$")
STEP_RE = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
ETAG_RE = re.compile(r'^"?[A-Za-z0-9:._-]{1,120}"?$')
VALIDATOR_RE = re.compile(r"^[0-9A-Za-z][0-9A-Za-z.+_-]{0,63}$")
PAD_RE = re.compile(r"^[A-Za-z0-9_.-]+(/[A-Za-z0-9_.-]+)*$")
URL_RE = re.compile(r"^(https|ssh)://[A-Za-z0-9.-]+(:[0-9]{1,5})?(/[A-Za-z0-9._~%-]+)+$")

BINDING_KEYS = {
    "appstore_service_id",
    "source_approval_revision",
    "provenance",
    "release",
    "plan_id",
    "step_id",
    "plan_etag",
    "instance",
    "vault_refs",
    "koppeling",
}
# Het getekende record: de bestaande velden van ``SignedProvenance.record`` plus de aanvullingen van §8.1.
RECORD_KEYS = {
    "app_id",
    "version",
    "entry_id",
    "version_id",
    "manifest_sha256",
    "schema_sha256",
    "validator_version",
    "source",
    "fetched_at",
    "publisher_signature",
    "publisher_key_id",
    "publisher_key_sha256",
    "valid",
    "errors",
    "warnings",
}
RECORD_SOURCE_KEYS = {"source_id", "kind", "url", "ref", "commit", "path", "subpath"}
INSTANCE_KEYS = {"host_id", "instance_id", "registry_revision", "app_name", "expected_version"}
REGEL_KEYS = {
    "app_id",
    "version",
    "catalog",
    "manifest_sha256",
    "image_digests",
    "schema_sha256",
    "validator_version",
    "source",
    "publisher_key_sha256",
    "formuliervelden",
    "kluisplekken",
}
# De vooraf toegelaten bron-ID hoort bij de bron: item, versie en record moeten dezelfde noemen (R-VEILIG-3).
REGEL_SOURCE_KEYS = {"source_id", "url", "subpath", "path", "commit"}
VELD_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
CATALOG_KEYS = {"train", "app", "version"}
# §8.3: precies twee gebonden typen; het enrollment-token heeft één vaste plek.
APPGEHEIM, TOKEN = "appgeheim", "enrollment-token"
TOKEN_ENV = "HUB_ENROLLMENT_TOKEN"  # noqa: S105 - de naam van de plek, geen waarde
VORM = {APPGEHEIM: re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{42}$"), TOKEN: re.compile(r"^enr_[A-Za-z0-9_-]{43}$")}
VAULT_REF_KEYS = {"path", "parameter", "ref", "revision"}
KOPPELING_KEYS = {"soort", "hub_url", "hub_key_fingerprint"}
HUB_URL_RE = re.compile(r"^https?://[A-Za-z0-9.:\[\]-]{1,253}$")
FINGERPRINT_RE = re.compile(r"^[0-9A-Z]{4}(-[0-9A-Z]{4}){3}$")


class RegelFout(ValueError):
    """Een regel in ``catalogus.yaml`` voldoet niet aan het schema; het beleid is dan ongeldig (fail-closed)."""


# ------------------------------------------------------------------ de witte lijst laden
def _regel_tekst(v: Any, where: str, pattern: re.Pattern[str], max_len: int = 255) -> str:
    if not isinstance(v, str) or not v or len(v) > max_len or not pattern.fullmatch(v):
        raise RegelFout(f"{where}: ongeldige waarde")
    return v


def _catalog(raw: Any, where: str) -> dict[str, str]:
    if not isinstance(raw, Mapping) or set(raw) != CATALOG_KEYS:
        raise RegelFout(f"{where}: verwacht precies train, app en version")
    return {
        "train": _regel_tekst(raw["train"], f"{where}.train", TRAIN_RE, 32),
        "app": _regel_tekst(raw["app"], f"{where}.app", CATALOG_APP_RE, 64),
        "version": _regel_tekst(raw["version"], f"{where}.version", VERSION_RE, 32),
    }


def laad_regels(raw: Any) -> tuple[dict[str, Any], ...]:
    """Valideer ``catalogus.yaml: installaties`` streng; elk probleem geeft :class:`RegelFout`."""
    if not isinstance(raw, list):
        raise RegelFout("installaties: verwacht een lijst")
    out: list[dict[str, Any]] = []
    for i, r in enumerate(raw):
        w = f"installaties[{i}]"
        if not isinstance(r, Mapping) or set(r) != REGEL_KEYS:
            raise RegelFout(f"{w}: verwacht precies de velden {sorted(REGEL_KEYS)}")
        src = r["source"]
        if not isinstance(src, Mapping) or set(src) != REGEL_SOURCE_KEYS:
            raise RegelFout(f"{w}.source: verwacht precies source_id, url, subpath, path en commit")
        velden = r["formuliervelden"]
        if not isinstance(velden, list) or len(set(map(str, velden))) != len(velden):
            raise RegelFout(f"{w}.formuliervelden: verwacht een lijst zonder dubbelen")
        digests = r["image_digests"]
        if not isinstance(digests, list) or not digests or len(set(digests)) != len(digests):
            raise RegelFout(f"{w}.image_digests: verwacht een niet-lege lijst zonder dubbelen")
        regel: dict[str, Any] = {
            "app_id": _regel_tekst(r["app_id"], f"{w}.app_id", APP_NAME_RE, 64),
            "version": _regel_tekst(r["version"], f"{w}.version", VERSION_RE, 32),
            "catalog": _catalog(r["catalog"], f"{w}.catalog"),
            "manifest_sha256": _regel_tekst(r["manifest_sha256"], f"{w}.manifest_sha256", SHA_RE),
            "image_digests": sorted(_regel_tekst(d, f"{w}.image_digests", SHA_RE) for d in digests),
            "schema_sha256": _regel_tekst(r["schema_sha256"], f"{w}.schema_sha256", SHA_RE),
            "validator_version": _regel_tekst(r["validator_version"], f"{w}.validator_version", VALIDATOR_RE, 64),
            "source": {
                "source_id": _regel_tekst(src["source_id"], f"{w}.source.source_id", UUID_RE, 36),
                "url": _regel_tekst(src["url"], f"{w}.source.url", URL_RE),
                "subpath": None
                if src["subpath"] is None
                else _regel_tekst(src["subpath"], f"{w}.source.subpath", PAD_RE),
                "path": _regel_tekst(src["path"], f"{w}.source.path", PAD_RE),
                "commit": _regel_tekst(src["commit"], f"{w}.source.commit", COMMIT_RE, 40),
            },
            "publisher_key_sha256": _regel_tekst(r["publisher_key_sha256"], f"{w}.publisher_key_sha256", SHA_RE),
            # Het veldschema van deze versie: de toegestane velden onder ``app_create.values`` (R-VEILIG-4).
            "formuliervelden": sorted(_regel_tekst(v, f"{w}.formuliervelden", VELD_RE, 64) for v in velden),
            "kluisplekken": _kluisplekken(r["kluisplekken"], f"{w}.kluisplekken"),
        }
        if any(".." in (p or "").split("/") for p in (regel["source"]["subpath"], regel["source"]["path"])):
            raise RegelFout(f"{w}.source: '..' is geen geldig paddeel")
        out.append(regel)
    return tuple(out)


def _kluisplekken(raw: Any, w: str) -> list[dict[str, str]]:
    """``[{env, type}]`` (§8.3): een appgeheim op een geheimnaam buiten ``HUB_*``; het token op zijn vaste plek."""
    if not isinstance(raw, list):
        raise RegelFout(f"{w}: verwacht een lijst")
    out: dict[str, dict[str, str]] = {}
    for j, p in enumerate(raw):
        if not isinstance(p, Mapping) or set(p) != {"env", "type"}:
            raise RegelFout(f"{w}[{j}]: verwacht precies env en type")
        env = _regel_tekst(p["env"], f"{w}[{j}].env", ENV_NAME_RE, 128)
        if p["type"] == TOKEN:
            if env != TOKEN_ENV:
                raise RegelFout(f"{w}[{j}]: het enrollment-token staat alleen op {TOKEN_ENV}")
        elif p["type"] == APPGEHEIM:
            if env.upper().startswith("HUB_") or not is_secret_name(env) or has_account_word(env) or is_login_name(env):
                raise RegelFout(f"{w}[{j}]: een appgeheim staat op een geheimnaam buiten HUB_* en nooit op een account")
        else:
            raise RegelFout(f"{w}[{j}].type: alleen {APPGEHEIM} of {TOKEN}")
        if env in out:
            raise RegelFout(f"{w}[{j}]: plek {env} staat er dubbel in")
        out[env] = {"env": env, "type": p["type"]}
    return [out[k] for k in sorted(out)]


def koppelbaar(regel: Mapping[str, Any]) -> bool:
    """Een regel met een tokenplek is een koppelbare eigen dienst (§8.3)."""
    return any(p["type"] == TOKEN for p in regel["kluisplekken"])


def kluisrefs(regel: Mapping[str, Any], values: Any, app_id: str) -> list[dict[str, str]] | None:
    """Per appgeheim-plek ``{path, parameter, ref}`` uit de payload, in de volgorde van de regel. ``None`` als een
    plek ontbreekt, dubbel staat of niet precies de verwijzing ``vault://app/<app_id>/<parameter>`` draagt."""
    envs = values.get("envs") if isinstance(values, Mapping) else None
    envs = envs if isinstance(envs, list) else []
    out: list[dict[str, str]] = []
    for plek in regel["kluisplekken"]:
        if plek["type"] != APPGEHEIM:
            continue
        parameter = plek["env"].lower()
        ref = f"vault://app/{app_id}/{parameter}"
        idx = [i for i, e in enumerate(envs) if isinstance(e, Mapping) and e.get("name") == plek["env"]]
        if len(idx) != 1 or envs[idx[0]].get("value") != ref:
            return None
        out.append({"path": f"values.envs[{idx[0]}].value", "parameter": parameter, "ref": ref})
    return out


def _kluis(regel: Mapping[str, Any], b: Mapping[str, Any], params: Mapping[str, Any], app_id: str) -> list[Fout]:
    """``vault_refs`` en ``koppeling`` precies zoals de eigen regel en de payload ze vragen (§8.3)."""
    w = "parameters.catalog_binding"
    ac = params.get("app_create") if isinstance(params.get("app_create"), Mapping) else {}
    assert isinstance(ac, Mapping)
    out: list[Fout] = []
    verwacht = kluisrefs(regel, ac.get("values"), app_id)
    refs = b["vault_refs"]
    goed = isinstance(refs, list) and all(
        isinstance(r, Mapping)
        and set(r) == VAULT_REF_KEYS
        and isinstance(r["revision"], str)
        and UUID_RE.fullmatch(r["revision"]) is not None
        for r in refs
    )
    if verwacht is None or not goed or [{k: r[k] for k in ("path", "parameter", "ref")} for r in refs] != verwacht:
        out.append(_f(f"{w}.vault_refs", "kluisplek_past_niet", "de kluisplekken passen niet bij de toegelaten regel"))
    elif vault_refs(params) != sorted(r["ref"] for r in verwacht):
        out.append(_f(f"{w}.vault_refs", "kluisplek_past_niet", "een andere kluisverwijzing in de payload"))
    k = b["koppeling"]
    if koppelbaar(regel):
        if not (
            isinstance(k, Mapping)
            and set(k) == KOPPELING_KEYS
            and k["soort"] == "volledig"
            and isinstance(k["hub_url"], str)
            and HUB_URL_RE.fullmatch(k["hub_url"]) is not None
            and isinstance(k["hub_key_fingerprint"], str)
            and FINGERPRINT_RE.fullmatch(k["hub_key_fingerprint"]) is not None
        ):
            out.append(_f(f"{w}.koppeling", "koppeling_past_niet", "een koppelbare eigen dienst vraagt de koppeling"))
    elif k is not None:
        out.append(_f(f"{w}.koppeling", "koppeling_past_niet", "deze regel koppelt niet met de Hub"))
    return out


# ------------------------------------------------------------------ zoeken
def regels_voor_record(regels: tuple[dict[str, Any], ...], record: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Alle regels die bij het getekende record passen (bron, uitgever, app, versie, hash en schema)."""
    src = record.get("source") if isinstance(record.get("source"), Mapping) else {}
    assert isinstance(src, Mapping)
    eigen_bron = {k: src.get(k) for k in REGEL_SOURCE_KEYS}
    return [
        r
        for r in regels
        if r["app_id"] == record.get("app_id")
        and r["version"] == record.get("version")
        and r["manifest_sha256"] == record.get("manifest_sha256")
        and r["schema_sha256"] == record.get("schema_sha256")
        and r["validator_version"] == record.get("validator_version")
        and r["publisher_key_sha256"] == record.get("publisher_key_sha256")
        and r["source"] == eigen_bron
    ]


# ------------------------------------------------------------------ controle van de binding
def _record(rec: Any, w: str) -> list[Fout]:
    out = _only(rec, w, RECORD_KEYS, RECORD_KEYS)
    if not isinstance(rec, Mapping) or out:
        return out
    out += _text(rec["app_id"], f"{w}.app_id", max_len=64, pattern=APP_NAME_RE)
    out += _text(rec["version"], f"{w}.version", max_len=32, pattern=VERSION_RE)
    out += _text(rec["entry_id"], f"{w}.entry_id", max_len=36, pattern=UUID_RE)
    out += _text(rec["version_id"], f"{w}.version_id", max_len=36, pattern=UUID_RE)
    for k in ("manifest_sha256", "schema_sha256", "publisher_key_sha256"):
        out += _text(rec[k], f"{w}.{k}", max_len=71, pattern=SHA_RE)
    out += _text(rec["validator_version"], f"{w}.validator_version", max_len=64, pattern=VALIDATOR_RE)
    if rec["publisher_signature"] != "verified":
        out.append(_f(f"{w}.publisher_signature", "uitgever_niet_geverifieerd", "verwacht verified"))
    if rec["valid"] is not True:
        out.append(_f(f"{w}.valid", "manifest_ongeldig", "het record verklaart het manifest niet geldig"))
    src = rec["source"]
    out += _only(src, f"{w}.source", RECORD_SOURCE_KEYS, RECORD_SOURCE_KEYS)
    if isinstance(src, Mapping) and src.get("kind") != "git":
        out.append(_f(f"{w}.source.kind", "bron_niet_toegelaten", "alleen een gepinde Git-bron"))
    if isinstance(src, Mapping) and not (isinstance(src.get("commit"), str) and COMMIT_RE.fullmatch(src["commit"])):
        out.append(_f(f"{w}.source.commit", "bron_niet_gepind", "verwacht een volledige commit (40 hex)"))
    return out


def _instance(inst: Any, w: str, target: Mapping[str, Any], app_name: Any) -> list[Fout]:
    out = _only(inst, w, INSTANCE_KEYS, INSTANCE_KEYS)
    if not isinstance(inst, Mapping) or out:
        return out
    out += _text(inst["host_id"], f"{w}.host_id", max_len=64)
    out += _text(inst["instance_id"], f"{w}.instance_id", max_len=36, pattern=UUID_RE)
    out += _text(inst["registry_revision"], f"{w}.registry_revision", max_len=128, pattern=REVISION_RE)
    out += _text(inst["app_name"], f"{w}.app_name", max_len=40, pattern=APP_NAME_RE)
    if inst["app_name"] != target.get("app_id") or inst["app_name"] != app_name:
        out.append(_f(f"{w}.app_name", "doel_verschilt", "de instantie hoort bij een ander doel"))
    if inst["host_id"] != target.get("host_id"):
        out.append(_f(f"{w}.host_id", "doel_verschilt", "de instantie hoort bij een andere host"))
    # Deze versie kent alleen installeren: de naam moet nog vrij zijn (ADR-0032 besluit 2).
    if inst["expected_version"] != "absent":
        out.append(_f(f"{w}.expected_version", "doel_verschilt", "bij installeren verwacht: absent"))
    return out


def controleer(regels: tuple[dict[str, Any], ...], params: Mapping[str, Any], target: Mapping[str, Any]) -> list[Fout]:
    """Controleer ``parameters.catalog_binding`` van ``app.install`` tegen de witte lijst en de payload."""
    w = "parameters.catalog_binding"
    b = params.get("catalog_binding")
    out = _only(b, w, BINDING_KEYS, BINDING_KEYS)
    if not isinstance(b, Mapping) or out:
        return out
    ac = params.get("app_create") if isinstance(params.get("app_create"), Mapping) else {}
    assert isinstance(ac, Mapping)
    out += _text(b["appstore_service_id"], f"{w}.appstore_service_id", max_len=36, pattern=UUID_RE)
    out += _text(b["source_approval_revision"], f"{w}.source_approval_revision", max_len=128, pattern=REVISION_RE)
    out += _text(b["plan_id"], f"{w}.plan_id", max_len=36, pattern=UUID_RE)
    out += _text(b["step_id"], f"{w}.step_id", max_len=64, pattern=STEP_RE)
    out += _text(b["plan_etag"], f"{w}.plan_etag", max_len=122, pattern=ETAG_RE)
    out += _instance(b["instance"], f"{w}.instance", target, ac.get("app_name"))
    prov = b["provenance"]
    out += _only(prov, f"{w}.provenance", {"record", "signature", "key_id", "alg"}, {"record", "signature", "key_id"})
    if not isinstance(prov, Mapping) or out:
        return out
    out += _text(prov["signature"], f"{w}.provenance.signature", max_len=200, pattern=B64_RE)
    out += _text(prov["key_id"], f"{w}.provenance.key_id", max_len=16, pattern=KEY_ID_RE)
    if prov.get("alg", "EdDSA") != "EdDSA":
        out.append(_f(f"{w}.provenance.alg", "waarde", "alleen EdDSA"))
    out += _record(prov["record"], f"{w}.provenance.record")
    rel = b["release"]
    out += _only(rel, f"{w}.release", {"catalog", "image_digests"}, {"catalog", "image_digests"})
    if out:
        return out
    assert isinstance(rel, Mapping)
    record = prov["record"]
    passend = regels_voor_record(regels, record)
    if len(passend) != 1:
        code = "catalogusversie_niet_toegelaten" if not passend else "catalogusregel_dubbelzinnig"
        return [_f(f"{w}.provenance.record", code, "Geen eenduidige geverifieerde catalogusregel.")]
    regel = passend[0]
    out += _kluis(regel, b, params, str(record.get("app_id")))
    if rel.get("catalog") != regel["catalog"] or rel.get("image_digests") != regel["image_digests"]:
        out.append(_f(f"{w}.release", "release_verschilt", "de release past niet bij de toegelaten regel"))
    # De payload moet precies de toegelaten catalogusversie installeren.
    if {"train": ac.get("train"), "app": ac.get("catalog_app"), "version": ac.get("version")} != regel["catalog"]:
        out.append(_f("parameters.app_create", "release_verschilt", "de installatie past niet bij de release"))
    values = ac.get("values") if isinstance(ac.get("values"), Mapping) else {}
    assert isinstance(values, Mapping)
    # shortcut: alleen velden op het eerste niveau; diepere toetsen EX47/C-12. Verfijnen als een regel dat vraagt.
    for naam in sorted(set(map(str, values)) - set(regel["formuliervelden"])):
        out.append(_f(f"parameters.app_create.values.{naam}", "veld_niet_in_schema", "veld buiten het veldschema"))
    manifest = params.get("manifest") if isinstance(params.get("manifest"), Mapping) else {}
    assert isinstance(manifest, Mapping)
    # De vertaalde stap moet zelf de hash van het gevalideerde manifest noemen; ontbreken is geen vrijgave (R-VEILIG-4).
    if manifest.get("manifest_sha256") != record.get("manifest_sha256"):
        out.append(
            _f("parameters.manifest.manifest_sha256", "manifest_verschilt", "manifesthash ontbreekt of wijkt af")
        )
    if ac.get("catalog_app") == IX_APP:
        img = expected_image(params) or {}
        if img.get("digest") not in regel["image_digests"] or manifest.get("image_digest") != img.get("digest"):
            out.append(_f("parameters.app_create.values.image", "digest_verschilt", "image niet in de release"))
        if manifest.get("app_id") != record.get("app_id") or manifest.get("version") != record.get("version"):
            out.append(_f("parameters.manifest", "release_verschilt", "app_id of versie wijkt af van het record"))
    return out


# ------------------------------------------------------------------ readback na uitvoering (executor)
def readback_digest_afwijking(
    params: Mapping[str, Any], refs: Sequence[str], images: Sequence[Mapping[str, Any]]
) -> dict[str, Any] | None:
    """Na ``app.install`` met binding: elke image van de app moet volgens ``app.image.query`` (``repo_digests``, niet de
    tag) een digest uit de release hebben. Ontbreekt dat bewijs of is het niet eenduidig (meer images of digests voor
    één actieve referentie), dan is het een afwijking (onbekend is geen succes).

    Toestandstabel per actieve referentie (rijen = imagerijen uit ``app.image.query`` met die tag):

    ==========================================================  ========================
    meting                                                      uitkomst
    ==========================================================  ========================
    geen referentie, geen rij of een rij zonder digest          digest_niet_bevestigd
    een digest buiten de release, of de referentie zelf noemt   digest_verschilt
    een digest buiten release of meting
    twee of meer rijen (image-ID's), ook met toegelaten digests digest_niet_bevestigd
    één rij met twee of meer verschillende digests              digest_niet_bevestigd
    precies één rij met precies één toegelaten digest           in orde (None)
    twee afzonderlijke referenties, elk precies zo bewezen      in orde (None)
    ==========================================================  ========================
    """
    b = params.get("catalog_binding")
    if not isinstance(b, Mapping):
        return None
    toegelaten = set((b.get("release") or {}).get("image_digests") or [])
    if not refs:
        return {"code": "digest_niet_bevestigd", "verwacht": sorted(toegelaten), "gevonden": []}
    gevonden: list[str] = []
    for ref in refs:
        naam, _, eigen = ref.partition("@")  # ``repo:tag@digest`` staat in app.image.query als ``repo:tag``
        rijen = [i for i in images if {ref, naam} & {str(t) for t in i.get("repo_tags") or []}]
        per_rij = [{str(d).split("@", 1)[-1] for d in i.get("repo_digests") or [] if d} for i in rijen]
        digests = set().union(*per_rij)
        gevonden += sorted(digests)
        # Elke rij voor deze tag moet een digest hebben; een rij zonder is geen eenduidig bewijs (R-VEILIG-7).
        if not per_rij or not all(per_rij):
            return {"code": "digest_niet_bevestigd", "verwacht": sorted(toegelaten), "gevonden": sorted(digests)}
        # Elke rij telt, en ook de digest in de actieve imagereferentie zelf: die moet in de release en in de meting.
        if digests - toegelaten or (eigen and (eigen not in toegelaten or eigen not in digests)):
            return {
                "code": "digest_verschilt",
                "verwacht": sorted(toegelaten),
                "gevonden": sorted(digests | {eigen} - {""}),
            }
        # Alleen precies één image (rij) met precies één digest is eenduidig: anders is niet vast te stellen welke
        # image draait, ook als alle digests in de release staan (R-VEILIG-7).
        if len(rijen) != 1 or len(digests) != 1:
            return {"code": "digest_niet_bevestigd", "verwacht": sorted(toegelaten), "gevonden": sorted(digests)}
    return None
