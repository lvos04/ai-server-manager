"""Catalogusinstallatie via een eigen plannerplan (contract 1.3 §8.1 M1 en §8.2 M3; ADR-0032 deel D; S-P2-050d).

1. **Bewijs (M1).** De Hub haalt zelf bij de ingeschreven appstore de versie, het item en de bron op en verifieert de
   ``SignedProvenance``-handtekening met de gepinde appstoresleutel (``Service.public_key_jwk``). De manifesthash
   rekent hij zelf na. De witte lijst ``catalogus.yaml`` (onder de ``policy_hash``) is de toelating door de beheerder;
   zonder precies één passende regel geen plan.
2. **Plan (M3).** De Hub maakt zelf de preview bij de planner, met ``catalog_binding`` in de body en de extra claim
   ``catalog_request_sha256`` in zijn dienst-JWT. Hij registreert plan-ID, ETag, binding en vervaltijd uit zijn eigen
   aanmaakantwoord. Alleen zo'n eigen plan levert een voorstel op.
3. **Voorstel, goedkeuring, uitvoering.** De gewone actieweg (gebruikerssessie, preview, goedkeuring, executor). Vóór
   voorstel, goedkeuring en uitvoering controleert de Hub plan en bewijs opnieuw; elke afwijking blokkeert.
4. **Na uitvoering.** De Hub meldt het stapresultaat met zijn eigen readback aan de planner en registreert naam en
   digest. De controles na installatie blijven open: de app is daarmee nooit 'gezond'.

Onbekend is niet goed: elke ontbrekende, onbereikbare of afwijkende bron geeft een weigering, nooit een vrijgave.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import uuid
from collections.abc import Mapping
from datetime import datetime
from typing import Any

import yaml
from asm_policy._asf_c12 import is_secret_name, secret_text_reasons
from asm_policy.canonical import CanonicalError, canonical_json, canonical_sha256
from asm_policy.catalogbinding import regels_voor_record
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from sqlalchemy import select
from sqlalchemy.orm import Session

from hub.actions import service
from hub.actions.beleid import get_policy
from hub.catalog.appstore import APPSTORE_APP_ID
from hub.catalog.asf.manifest.model import Parameter
from hub.catalog.asf.manifest.translate import _check_value, is_secret
from hub.catalog.asf.manifest.validator import schema_sha256, validate_data
from hub.config import Settings
from hub.deps import Principal
from hub.errors import HubError
from hub.inventory.store import latest_run
from hub.keys import KeyRing
from hub.models import ActionRequest, CatalogPlan, Service
from hub.registry import measured_apps, service_base_url
from hub.servicecalls import CallResult, ServiceCallError, call
from hub.timeutil import iso, utcnow
from hub.vault import Vault

PLANNER_APP_ID = "jelly-leon-platform"
PREVIEW_PATH = "/lifecycle/v1/plans/install/preview"
HOST_ID = "nas-primary"
STAP_ACTIE = "app.install"
OPEN = ("klaar_voor_voorstel", "voorgesteld")
NS = uuid.UUID("8f1d3c52-5b0e-4f7a-9d61-2c4b7e0a9f13")  # vaste naamruimte voor de idempotente stapmelding
# ``schema_sha256`` van de gepinde validator (kopie in ``hub.catalog.asf`` van appstore-en-fork op ASF_COMMIT).
SCHEMA_SHA256 = "sha256:f2f1201a12e28ec88db1ea7e49af2bb7f10b8970dc8b68fae30ec7b33b243ce1"
INVULBAAR = ("wizard", "dataset_picker")  # bronnen die de aanvrager mag invullen; geheimen openen pas in deel E
CONTROLE_KEYS = ("id", "soort", "beschrijving_nl")


def _fout(status: int, code: str, message: str, details: dict[str, Any] | None = None) -> HubError:
    return HubError(status, code, message, details or {})


def _dienst(db: Session, settings: Settings, app_id: str) -> tuple[Service, str]:
    svc = db.scalars(select(Service).where(Service.app_id == app_id, Service.status == "active")).first()
    if svc is None:
        raise _fout(409, "dienst_niet_gekoppeld", f"{app_id} is niet ingeschreven bij de Hub.", {"app_id": app_id})
    base, reden = service_base_url(db, settings, svc)
    if base is None:
        raise _fout(503, "dienst_adres_onbekend", f"Het adres van {app_id} is niet gemeten.", {"reden": reden})
    return svc, base


def _vraag(
    settings: Settings,
    keyring: KeyRing,
    svc: Service,
    base: str,
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
    key: str | None = None,
    claim: str | None = None,
) -> CallResult:
    bearer, _jti = keyring.issue_hub_service_jwt(
        audience=svc.app_id, service_id=str(svc.id), catalog_request_sha256=claim
    )
    try:
        return call(
            base,
            method,
            path,
            bearer=bearer,
            idempotency_key=key,
            body=body,
            connect_timeout=settings.service_call_connect_timeout,
            read_timeout=settings.service_call_read_timeout,
        )
    except ServiceCallError as exc:
        raise _fout(
            503, "dienst_onbereikbaar", f"{svc.app_id} gaf geen bruikbaar antwoord.", {"reden": exc.reason}
        ) from None


def _json(res: CallResult, svc: Service, path: str) -> dict[str, Any]:
    if (res.status != 200 and res.status != 201) or not isinstance(res.body, dict):
        raise _fout(
            503,
            "dienst_antwoord_ongeldig",
            f"{svc.app_id} gaf geen bruikbaar antwoord.",
            {"pad": path, "http": res.status},
        )
    return res.body


# ------------------------------------------------------------------ M1: catalogusbewijs
def _sleutel(svc: Service) -> Ed25519PublicKey:
    jwk = svc.public_key_jwk or {}
    try:
        raw = base64.urlsafe_b64decode(str(jwk.get("x", "")) + "==")
        return Ed25519PublicKey.from_public_bytes(raw)
    except ValueError:
        raise _fout(409, "bewijs_ongeldig", "De gepinde appstoresleutel is ongeldig.") from None


def _key_id(pub: Ed25519PublicKey) -> str:
    """Zelfde sleutel-ID als de appstore: eerste 16 hex van SHA-256 over de ruwe publieke sleutel."""
    return hashlib.sha256(pub.public_bytes(Encoding.Raw, PublicFormat.Raw)).hexdigest()[:16]


def _weiger(reden: str) -> HubError:
    return _fout(409, "bewijs_ongeldig", "Het catalogusbewijs klopt niet; er wordt niets gepland.", {"reden": reden})


def manifest_fouten(regel: Mapping[str, Any], manifest: Any) -> int:
    """Aantal fouten van de gepinde validator (schema én regels) voor het oorspronkelijke manifest (§8.1, R-VEILIG-2).

    Een ander schema dan de pin telt als fout (fail-closed)."""
    if regel.get("schema_sha256") != SCHEMA_SHA256 or schema_sha256() != SCHEMA_SHA256:
        return 1
    if not isinstance(manifest, Mapping):
        return 1
    rapport, model = validate_data(copy.deepcopy(dict(manifest)))
    return rapport.errors if model is not None else max(rapport.errors, 1)


def parameters_fouten(manifest: Mapping[str, Any], parameters: Mapping[str, Any]) -> list[str]:
    """Codes voor ingevulde parameters die niet gedeclareerd, niet invulbaar, ongeldig of geheim zijn (§8.1).

    De waarde zelf toetst de parametercontrole van de gepinde validator (type, pad, dataset, adres, ...)."""
    decl = {p.get("name"): p for p in manifest.get("parameters") or [] if isinstance(p, Mapping)}
    codes: set[str] = set()
    for naam, waarde in parameters.items():
        try:
            p = Parameter.model_validate(decl[naam]) if naam in decl else None
        except ValueError:
            p = None
        if p is None:
            codes.add("niet_gedeclareerd")
        elif p.source not in INVULBAAR or is_secret(p) or p.type == "secret_ref" or is_secret_name(naam):
            codes.add("niet_invulbaar")
        elif _check_value(p, waarde) is not None:
            codes.add("type")
        elif isinstance(waarde, str) and secret_text_reasons(waarde, settings=True):
            codes.add("geheim_in_waarde")
    return sorted(codes)


def bewijs(db: Session, settings: Settings, keyring: KeyRing, *, app_id: str, version_id: str) -> dict[str, Any]:
    """Verifieer de gekozen versie bij de appstore zelf (§8.1). Geeft ``{service, provenance, manifest, regel}``."""
    svc, base = _dienst(db, settings, APPSTORE_APP_ID)
    try:
        vid = str(uuid.UUID(version_id))
    except ValueError:
        raise _fout(422, "version_id_ongeldig", "version_id moet een UUID zijn.") from None
    res = _vraag(settings, keyring, svc, base, "GET", f"/catalog/v1/versions/{vid}")
    if res.status == 404:
        # Alleen een aangetoond verdwenen versie (§8.1).
        raise _fout(409, "version_unavailable", "Deze catalogusversie bestaat niet meer bij de appstore.")
    versie = _json(res, svc, "versions")
    entry = _json(_vraag(settings, keyring, svc, base, "GET", f"/catalog/v1/entries/{app_id}"), svc, "entries")
    prov = versie.get("provenance")
    if not isinstance(prov, Mapping) or not isinstance(prov.get("record"), Mapping):
        raise _weiger("provenance_ontbreekt")
    record = prov["record"]
    src = record.get("source") if isinstance(record.get("source"), Mapping) else {}
    assert isinstance(src, Mapping)
    bron_id = str(src.get("source_id") or "")
    bron = _json(_vraag(settings, keyring, svc, base, "GET", f"/catalog/v1/sources/{bron_id}"), svc, "sources")

    pub = _sleutel(svc)
    try:
        sig = base64.b64decode(str(prov.get("signature", "")), validate=True)
        if prov.get("key_id") != _key_id(pub) or prov.get("alg", "EdDSA") != "EdDSA":
            raise _weiger("sleutel_past_niet")
        pub.verify(sig, canonical_json(dict(record)))
    except (InvalidSignature, ValueError, CanonicalError):
        raise _weiger("handtekening_ongeldig") from None

    manifest = versie.get("manifest")
    try:
        herberekend = canonical_sha256(manifest) if isinstance(manifest, Mapping) else None
    except CanonicalError:
        herberekend = None
    checks = {
        "entry_id": record.get("entry_id") == entry.get("entry_id") == versie.get("entry_id"),
        "version_id": record.get("version_id") == versie.get("id") == vid,
        "app_id": record.get("app_id") == entry.get("app_id") == versie.get("app_id") == app_id,
        "version": record.get("version") == versie.get("version"),
        "source_id": bron_id == str(versie.get("source_id")) == str(bron.get("id")) == str(_bron_van(entry)),
        # De actieve bron noemt dezelfde uitgeverssleutel als het record (R-VEILIG-3); de volledige vingerafdruk
        # vergelijkt de witte lijst.
        "uitgeverssleutel": isinstance(record.get("publisher_key_sha256"), str)
        and record.get("publisher_key_id") == record["publisher_key_sha256"][7:23] == bron.get("trusted_key_id"),
        "bron": bron.get("kind") == "git"
        and bron.get("enabled") is True
        and bron.get("require_signature") is True
        and bron.get("url") == src.get("url")
        and bron.get("subpath") == src.get("subpath")
        and bron.get("pinned_commit") == src.get("commit"),
        "manifest_sha256": herberekend is not None and herberekend == record.get("manifest_sha256"),
        "valid": record.get("valid") is True and record.get("publisher_signature") == "verified",
    }
    anders = sorted(k for k, ok in checks.items() if not ok)
    if anders:
        raise _fout(
            409, "bewijs_ongeldig", "Het catalogusbewijs klopt niet; er wordt niets gepland.", {"velden": anders}
        )
    regels = regels_voor_record(get_policy().catalogus, record)
    if len(regels) != 1:
        code = "catalogusversie_niet_toegelaten" if not regels else "catalogusregel_dubbelzinnig"
        raise _fout(409, code, "Deze versie staat niet (eenduidig) in de witte lijst van de beheerder.")
    if manifest_fouten(regels[0], manifest):
        raise _weiger("manifest_schema")
    return {"service": svc, "provenance": dict(prov), "manifest": dict(manifest), "regel": regels[0]}  # type: ignore[arg-type]


def _bron_van(entry: Mapping[str, Any]) -> Any:
    src = entry.get("source")
    return src.get("id") if isinstance(src, Mapping) else None


# ------------------------------------------------------------------ M3: eigen plan bij de planner
def _naam_vrij(db: Session, settings: Settings, app_name: str) -> str:
    st = measured_apps(db, settings)
    if st.get("status") != "ok":
        raise _fout(409, "inventaris_niet_actueel", "Zonder verse meting wordt er niets gepland.")
    if any(isinstance(a, dict) and a.get("naam") == app_name for a in st.get("data") or []):
        raise _fout(409, "naam_bezet", "Deze appnaam bestaat al op de NAS.", {"app_name": app_name})
    bezet = db.scalars(select(CatalogPlan).where(CatalogPlan.app_name == app_name, CatalogPlan.status.in_(OPEN)))
    if bezet.first() is not None:
        raise _fout(409, "naam_gereserveerd", "Voor deze appnaam loopt al een plan.", {"app_name": app_name})
    run = latest_run(db)
    return f"inventaris:{run.id}" if run is not None else "inventaris:onbekend"


def _actiestap(view: Mapping[str, Any]) -> dict[str, Any] | None:
    stappen = (view.get("plan") or {}).get("stappen") if isinstance(view.get("plan"), Mapping) else None
    acties = [s for s in stappen or [] if isinstance(s, Mapping) and (s.get("voorstel") or {}).get("action_id")]
    return dict(acties[0]) if len(acties) == 1 else None


def maak_plan(
    db: Session,
    settings: Settings,
    keyring: KeyRing,
    principal: Principal,
    *,
    app_id: str,
    version_id: str,
    app_name: str,
    parameters: dict[str, Any],
    doel: dict[str, Any],
) -> dict[str, Any]:
    m1 = bewijs(db, settings, keyring, app_id=app_id, version_id=version_id)
    codes = parameters_fouten(m1["manifest"], parameters)
    if codes:
        # Geen namen of waarden terug: die kunnen van de aanvrager komen.
        raise _fout(
            422, "parameters_ongeldig", "De ingevulde parameters passen niet bij het manifest.", {"codes": codes}
        )
    revisie = _naam_vrij(db, settings, app_name)
    regel = m1["regel"]
    vijf = {
        "appstore_service_id": str(m1["service"].id),
        "source_approval_revision": get_policy().hash,
        "provenance": m1["provenance"],
        "release": {"catalog": regel["catalog"], "image_digests": regel["image_digests"]},
        "instance": {
            "host_id": HOST_ID,
            "instance_id": str(uuid.uuid4()),
            "registry_revision": revisie,
            "app_name": app_name,
            "expected_version": "absent",
        },
    }
    body = {
        "manifest_yaml": yaml.safe_dump(m1["manifest"], sort_keys=False, allow_unicode=True),
        "parameters": parameters,
        "app_name": app_name,
        "doel": doel,
        "catalog_binding": vijf,
    }
    key = str(uuid.uuid4())
    try:
        claim = canonical_sha256(["POST", PREVIEW_PATH, key, body])
    except CanonicalError as exc:
        raise _fout(422, "parameters_ongeldig", f"Parameters niet canoniek: {exc}") from None
    svc, base = _dienst(db, settings, PLANNER_APP_ID)
    res = _vraag(settings, keyring, svc, base, "POST", PREVIEW_PATH, body=body, key=key, claim=claim)
    view = _json(res, svc, "preview")
    stap = _actiestap(view)
    try:
        plan_id = uuid.UUID(str(view.get("id")))
        verloopt = datetime.fromisoformat(str(view.get("expires_at")).replace("Z", "+00:00"))
    except ValueError:
        raise _fout(503, "dienst_antwoord_ongeldig", "De planner gaf geen geldig plan terug.") from None
    if view.get("catalog_binding") != vijf or not isinstance(view.get("etag"), str):
        # De planner moet precies de binding van de Hub bewaren en teruggeven (§8.2).
        raise _fout(409, "plan_binding_verschilt", "De planner gaf een andere of geen catalogusbinding terug.")
    if stap is None or not _stap_past(stap["voorstel"], app_name):
        raise _fout(409, "plan_stap_onverwacht", "Het plan bevat niet precies één passende installatiestap.")
    controles = (view.get("plan") or {}).get("controles_na_installatie") or []
    if controles != (m1["manifest"].get("post_install_checks") or []):
        # Alleen de openbare controles uit het geverifieerde manifest komen in opslag en antwoord (R-VEILIG-1).
        raise _fout(409, "plan_controles_verschillen", "De controles na installatie wijken af van het manifest.")
    if stap.get("hangt_af_van"):
        status, reden = "geblokkeerd", "voorganger_onbevestigd"  # geen eigen bevestiging in deze versie
    elif view.get("status") == "klaar_voor_voorstel":
        status, reden = "klaar_voor_voorstel", None
    else:
        status, reden = "geblokkeerd", "planner_niet_klaar"
    now = utcnow()
    plan = CatalogPlan(
        id=plan_id,
        soort="install",
        app_id=app_id,
        app_name=app_name,
        instance_id=uuid.UUID(vijf["instance"]["instance_id"]),
        planner_service_id=svc.id,
        binding={**vijf, "plan_id": str(plan_id), "step_id": stap["id"], "plan_etag": view["etag"], "vault_refs": []},
        plan_etag=view["etag"],
        step_id=stap["id"],
        stap_sha256=_stap_sha(stap),
        controles_na_installatie=openbare_controles(controles),
        expires_at=verloopt,
        status=status,
        reden=reden,
        created_by=principal.name,
        created_at=now,
        updated_at=now,
    )
    db.add(plan)
    db.flush()
    return plan_dict(plan)


def _stap_sha(stap: Mapping[str, Any]) -> str:
    try:
        return canonical_sha256(stap.get("voorstel"))
    except CanonicalError:
        raise _fout(503, "dienst_antwoord_ongeldig", "De planner gaf een niet-canonieke stap terug.") from None


def _tijd(waarde: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(waarde).replace("Z", "+00:00"))
    except ValueError:
        return None


def _stap_past(voorstel: Any, app_name: str) -> bool:
    return (
        isinstance(voorstel, Mapping)
        and voorstel.get("action_id") == STAP_ACTIE
        and voorstel.get("target") in ({"app_id": app_name}, {"host_id": HOST_ID, "app_id": app_name})
        and voorstel.get("expected_version") == "absent"
        and isinstance(voorstel.get("parameters"), Mapping)
    )


def plan_dict(plan: CatalogPlan) -> dict[str, Any]:
    return {
        "plan_id": str(plan.id),
        "app_id": plan.app_id,
        "app_name": plan.app_name,
        "step_id": plan.step_id,
        "status": plan.status,
        "reden": plan.reden,
        "plan_etag": plan.plan_etag,
        "expires_at": iso(plan.expires_at),
        "request_id": str(plan.request_id) if plan.request_id else None,
        "release": plan.binding.get("release"),
        "registratie": plan.registratie,
        "melding": plan.melding,
        "controles_na_installatie": openbare_controles(plan.controles_na_installatie),
    }


def openbare_controles(controles: Any) -> list[dict[str, Any]]:
    """Alleen de openbare velden, ook uit rijen en antwoorden van vóór het herstel (R-VEILIG-1)."""
    return [{k: c.get(k) for k in CONTROLE_KEYS} for c in controles or [] if isinstance(c, Mapping)]


def idempotency_response(body: Any) -> Any:
    """Filter voor herhaalde antwoorden van de planroutes: een bewaard oud antwoord lekt geen extra controleveld."""
    if isinstance(body, dict) and "controles_na_installatie" in body:
        return {**body, "controles_na_installatie": openbare_controles(body["controles_na_installatie"])}
    return body


def _plan_nu(db: Session, settings: Settings, keyring: KeyRing, plan: CatalogPlan) -> dict[str, Any]:
    """Haal alleen het eigen plan op en vergelijk het met de eigen registratie (ETag, binding, stap, vervaltijd)."""
    if plan.expires_at <= utcnow():
        raise _fout(409, "plan_vervallen", "Dit plan is verlopen; maak een nieuw plan.")
    svc = db.get(Service, plan.planner_service_id)
    if svc is None or svc.status != "active":
        raise _fout(409, "plan_bewijs_gewijzigd", "De planner van dit plan is niet meer ingeschreven.")
    _, base = _dienst(db, settings, PLANNER_APP_ID)
    view = _json(_vraag(settings, keyring, svc, base, "GET", f"/lifecycle/v1/plans/{plan.id}"), svc, "plan")
    vijf = {
        k: plan.binding[k]
        for k in ("appstore_service_id", "source_approval_revision", "provenance", "release", "instance")
    }
    stap = _actiestap(view)
    checks = {
        "plan_id": view.get("id") == str(plan.id),
        "etag": view.get("etag") == plan.plan_etag,
        "binding": view.get("catalog_binding") == vijf,
        "vervallen": view.get("vervallen") is False,
        "stap": stap is not None and stap.get("id") == plan.step_id and _stap_past(stap.get("voorstel"), plan.app_name),
        "vrijgegeven": plan.step_id in (view.get("vrijgegeven_stappen") or []),
        # Bij gelijke ETag toch zelf vergelijken: stapinhoud, vervaltijd, planstatus en voorgangers (R-VEILIG-5/-6).
        "stapinhoud": stap is not None and _stap_sha(stap) == plan.stap_sha256,
        "vervaltijd": _tijd(view.get("expires_at")) == plan.expires_at,
        "planstatus": view.get("status") == "klaar_voor_voorstel",
        "voorganger": stap is not None and not stap.get("hangt_af_van"),
    }
    anders = sorted(k for k, ok in checks.items() if not ok)
    if anders:
        raise _fout(
            409, "plan_bewijs_gewijzigd", "Het plan bij de planner wijkt af; maak een nieuw plan.", {"velden": anders}
        )
    rec = plan.binding["provenance"]["record"]
    m1 = bewijs(db, settings, keyring, app_id=rec["app_id"], version_id=rec["version_id"])
    if m1["provenance"] != plan.binding["provenance"] or str(m1["service"].id) != plan.binding["appstore_service_id"]:
        raise _fout(409, "plan_bewijs_gewijzigd", "Het catalogusbewijs is gewijzigd; maak een nieuw plan.")
    if plan.binding["source_approval_revision"] != get_policy().hash:
        raise _fout(409, "plan_bewijs_gewijzigd", "De witte lijst is gewijzigd; maak een nieuw plan.")
    assert stap is not None
    return dict(stap["voorstel"])


def haal_plan(db: Session, plan_id: uuid.UUID, *, vergrendel: bool = False) -> CatalogPlan:
    q = select(CatalogPlan).where(CatalogPlan.id == plan_id)
    plan = db.scalars(q.with_for_update() if vergrendel else q).first()
    if plan is None:
        # Een plan dat de Hub niet zelf aanmaakte, bestaat voor de Hub niet.
        raise _fout(404, "not_found", "Geen eigen plan met dit ID.")
    return plan


def stel_stap_voor(
    db: Session,
    settings: Settings,
    vault: Vault,
    keyring: KeyRing,
    principal: Principal,
    plan: CatalogPlan,
    *,
    step_id: str,
    request_id: uuid.UUID,
    trace_id: str,
) -> dict[str, Any]:
    if step_id != plan.step_id:
        raise _fout(409, "stap_onbekend", "Deze stap hoort niet bij dit plan.")
    if plan.status != "klaar_voor_voorstel":
        raise _fout(
            409,
            "plan_status_past_niet",
            "Voor dit plan kan geen voorstel meer worden gemaakt.",
            {"status": plan.status},
        )
    voorstel = _plan_nu(db, settings, keyring, plan)
    parameters = {**dict(voorstel["parameters"]), "catalog_binding": plan.binding}
    rec = plan.binding["provenance"]["record"]
    uit = service.stel_voor(
        db,
        settings,
        vault,
        principal,
        request_id=request_id,
        action_id=STAP_ACTIE,
        target={"host_id": HOST_ID, "app_id": plan.app_name},
        parameters=parameters,
        reason=f"Catalogusinstallatie {rec['app_id']} {rec['version']} (plan {plan.id})",
        risk_claim=None,
        evidence_ids=[],
        expected_version="absent",
        expires_in_seconds=3600,
        trace_id=trace_id,
    )
    plan.request_id, plan.status, plan.updated_at = request_id, "voorgesteld", utcnow()
    db.flush()
    return uit


def plan_van(db: Session, req: ActionRequest) -> CatalogPlan | None:
    if not isinstance((req.parameters or {}).get("catalog_binding"), Mapping):
        return None
    plan = db.scalars(select(CatalogPlan).where(CatalogPlan.request_id == req.id)).first()
    if plan is None:
        raise _fout(409, "plan_bewijs_gewijzigd", "Dit voorstel hoort niet bij een eigen plan van de Hub.")
    return plan


def hercontroleer(db: Session, settings: Settings, keyring: KeyRing, req: ActionRequest) -> None:
    """Vlak vóór goedkeuring en uitvoering: plan en bewijs opnieuw, en de binding in het voorstel ongewijzigd."""
    plan = plan_van(db, req)
    if plan is None:
        return
    if req.parameters.get("catalog_binding") != plan.binding:
        raise _fout(409, "plan_bewijs_gewijzigd", "De binding in het voorstel wijkt af van het eigen plan.")
    _plan_nu(db, settings, keyring, plan)


def na_uitvoering(db: Session, settings: Settings, keyring: KeyRing, req: ActionRequest) -> None:
    """Meld het stapresultaat met de eigen readback en registreer de instantie. Faalt nooit hard: een melding die niet
    aankomt, staat als ``niet_gemeld`` bij het plan en blokkeert elk vervolg (het plan heeft dan een andere ETag)."""
    plan = db.scalars(select(CatalogPlan).where(CatalogPlan.request_id == req.id)).first()
    if plan is None or plan.status != "voorgesteld" or req.status not in ("uitgevoerd", "mislukt", "afwijking"):
        return
    res = req.resultaat or {}
    rb = res.get("readback") if isinstance(res.get("readback"), Mapping) else {}
    assert isinstance(rb, Mapping)
    readback = {
        "staat": str(rb.get("staat") or "onbekend")[:32],
        "versie": rb.get("versie"),
        "digests": [str(d) for d in rb.get("digests") or []][:20],
        "images": [str(i) for i in rb.get("images") or []][:20],
        "etag": res.get("resource_etag"),
    }
    ok = req.status == "uitgevoerd"
    body = {
        "status": "voltooid" if ok else "mislukt",
        "execution_id": str(req.id),
        "readback": readback,
        "reden": None if ok else str(res.get("reden") or res.get("code") or req.status)[:500],
    }
    now = utcnow()
    try:
        svc = db.get(Service, plan.planner_service_id)
        if svc is None:
            raise _fout(409, "dienst_niet_gekoppeld", "planner")
        _, base = _dienst(db, settings, PLANNER_APP_ID)
        path = f"/lifecycle/v1/plans/{plan.id}/steps/{plan.step_id}/result"
        r = _vraag(
            settings, keyring, svc, base, "POST", path, body=body, key=str(uuid.uuid5(NS, f"{plan.id}/{plan.step_id}"))
        )
        plan.melding = {"status": "gemeld" if r.status == 200 else "geweigerd", "http": r.status, "op": iso(now)}
    except HubError as exc:
        plan.melding = {"status": "niet_gemeld", "reden": exc.code, "op": iso(now)}
    if ok:
        # Pas een passende readback bevestigt naam en digest; de hostpoort volgt uit de volgende inventaris.
        plan.registratie = {
            "app_name": plan.app_name,
            "instance_id": str(plan.instance_id),
            "digests": readback["digests"],
            "host_poort": None,
            "host_poort_reden": "wacht_op_inventaris",
            "bevestigd_op": iso(now),
        }
        plan.status = "geinstalleerd_controles_open"
    else:
        plan.status = req.status
    plan.updated_at = now
    db.flush()
