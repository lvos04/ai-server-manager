"""Afzonderlijke geheime overdracht, kant van de Hub (contract 1.3 §8.3, M2; S-P2-050e).

Het ondertekende verzoek draagt alleen verwijzingen en revisies. Bij het voorstel maakt de Hub per appgeheim-plek een
revisie en een willekeurige waarde (versleuteld met de eigen ``vault.key``, zonder ``last4``). Vlak vóór verzending legt
hij de afgifte vast. Na zijn eigen controles claimt de executor de waarden één keer: de opvraag is ondertekend met zijn
gepinde identiteit, het antwoord is een Hub-dienst-JWT met de waarden HPKE-versleuteld naar een sleutel die de executor
alleen voor deze opvraag maakte. Pas bij de claim maakt de Hub het enrollment-token (alleen de SHA-256 blijft).

Geen waarde in antwoorden buiten de afgifte, logs, audit of foutpaden; alleen refs, revisies en aantallen.
"""

from __future__ import annotations

import base64
import secrets
import uuid
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any

from asm_policy.canonical import canonical_json, canonical_sha256
from asm_policy.catalogbinding import APPGEHEIM, VORM, kluisrefs
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hpke
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from hub import audit, servicecalls
from hub.config import Settings
from hub.deps import Principal
from hub.errors import HubError
from hub.keys import KeyRing
from hub.models import ActionRequest, AppGeheim, Approval, CatalogPlan, EnrollmentGrant, KluisAfgifte, Service
from hub.registry import EXECUTOR_APP_ID
from hub.security import new_token, sha256_hex
from hub.timeutil import utcnow
from hub.vault import Vault

INFO = b"asm-kluis-afgifte-v1"
SUITE = hpke.Suite(hpke.KEM.X25519, hpke.KDF.HKDF_SHA256, hpke.AEAD.AES_256_GCM)
AFGIFTE_MAX = timedelta(seconds=60)
ENC_LEN = 32  # DHKEM(X25519): de ingekapselde sleutel staat vóór de versleutelde tekst


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _aad(instance_id: str, ref: str, revision: str) -> str:
    return f"{ref}|{instance_id}|{revision}"


def nieuw_appgeheim() -> str:
    """32 willekeurige bytes als base64url; een waarde die niet in de vorm past (begint met ``-`` of ``_``) opnieuw."""
    while True:
        waarde = secrets.token_urlsafe(32)
        if VORM[APPGEHEIM].fullmatch(waarde):
            return waarde


# ------------------------------------------------------------------ bij plan en voorstel
def koppeling(db: Session, settings: Settings, keyring: KeyRing) -> dict[str, str]:
    """Adres en vingerafdruk voor ``HUB_URL``/``HUB_KEY_FINGERPRINT``: het Hub-adres zoals de gekoppelde executor het
    zelf gebruikt (live gelezen, §3.5) en de eigen vingerafdruk, die de executor ook gepind moet hebben."""
    from hub.actions.service import _executor  # hier: service importeert dit bestand

    svc, base = _executor(db, settings)
    bearer, _ = keyring.issue_hub_service_jwt(audience=svc.app_id, service_id=str(svc.id))
    eigen = keyring.keyset_fingerprint()
    try:
        res = servicecalls.call(
            base,
            "GET",
            "/connector/v1/hub-link",
            bearer=bearer,
            connect_timeout=settings.service_call_connect_timeout,
            read_timeout=settings.service_call_read_timeout,
        )
    except servicecalls.ServiceCallError:
        raise HubError(503, "dienst_onbereikbaar", "De executor is niet bereikbaar; er is geen plan gemaakt.") from None
    body = res.body if res.status == 200 and isinstance(res.body, dict) else {}
    hub_url = body.get("hub_url")
    if body.get("keyset_fingerprint") != eigen or not isinstance(hub_url, str) or not hub_url:
        raise HubError(
            409,
            "koppeling_past_niet",
            "De executor is niet met deze Hub-sleutels gekoppeld; een koppelbare eigen dienst kan nu niet worden "
            "geïnstalleerd.",
        )
    return {"soort": "volledig", "hub_url": hub_url, "hub_key_fingerprint": eigen}


def bind_geheimen(
    db: Session, vault: Vault, plan: CatalogPlan, regel: Mapping[str, Any], values: Any
) -> list[dict[str, str]]:
    """Bij het voorstel: per appgeheim-plek een nieuwe revisie en waarde (alleen versleuteld bewaard). Geeft
    ``vault_refs`` voor de binding; ``None``-plekken weigert de gewone controle daarna (``kluisplek_past_niet``)."""
    refs = kluisrefs(regel, values, plan.app_id)
    if refs is None:
        raise HubError(409, "plan_stap_onverwacht", "De installatiestap noemt de kluisplekken van de regel niet.")
    uit: list[dict[str, str]] = []
    for r in refs:
        revision = str(uuid.uuid4())
        nonce, ct = vault.encrypt(_aad(str(plan.instance_id), r["ref"], revision), nieuw_appgeheim())
        db.add(
            AppGeheim(
                instance_id=plan.instance_id,
                ref=r["ref"],
                revision=uuid.UUID(revision),
                nonce=nonce,
                ciphertext=ct,
                created_at=utcnow(),
            )
        )
        uit.append({**r, "revision": revision})
    return uit


def heeft_kluis(binding: Any) -> bool:
    return isinstance(binding, Mapping) and bool(binding.get("vault_refs") or binding.get("koppeling"))


def leg_afgifte_vast(db: Session, req: ActionRequest, ap: Approval | None, verzoek: Mapping[str, Any]) -> None:
    """Vlak vóór verzending: de hash van precies dit ondertekende verzoek en de eerst aflopende tijd (hooguit 60 s)."""
    if not heeft_kluis((req.parameters or {}).get("catalog_binding")):
        return
    now = utcnow()
    eind = min(
        [now + AFGIFTE_MAX, req.geldig_tot, datetime.fromisoformat(str(verzoek["expires_at"]).replace("Z", "+00:00"))]
        + ([ap.expires_at] if ap is not None else [])
    )
    db.add(KluisAfgifte(request_id=req.id, request_sha256=canonical_sha256(verzoek), expires_at=eind, created_at=now))
    db.commit()


def gemarkeerd(db: Session, app_name: str) -> bool:
    """Register van de Hub (§8.3): een instantie waarin de executor plekken heeft (of kan hebben) ingevuld."""
    plannen = db.scalars(
        select(CatalogPlan).where(CatalogPlan.app_name == app_name, CatalogPlan.request_id.is_not(None))
    )
    return any(heeft_kluis(p.binding) for p in plannen)


# ------------------------------------------------------------------ de claim
def _weiger(status: int, code: str, melding: str) -> HubError:
    return HubError(status, code, melding)


def claim(
    db: Session, settings: Settings, vault: Vault, keyring: KeyRing, principal: Principal, body: dict[str, Any]
) -> dict[str, Any]:
    if principal.service_app_id != EXECUTOR_APP_ID:
        raise _weiger(403, "afgifte_geweigerd", "Alleen de gekoppelde executor haalt kluiswaarden op.")
    svc = db.get(Service, uuid.UUID(principal.id))
    rest = {k: v for k, v in body.items() if k != "handtekening"}
    try:
        assert svc is not None and isinstance(svc.public_key_jwk, Mapping)
        sleutel = Ed25519PublicKey.from_public_bytes(_unb64(str(svc.public_key_jwk["x"])))
        sleutel.verify(_unb64(body["handtekening"]), canonical_json(rest))
    except (AssertionError, KeyError, ValueError, InvalidSignature):
        raise _weiger(403, "afgifte_geweigerd", "De opvraag is niet door de gepinde executor ondertekend.") from None
    req_id = uuid.UUID(body["request_id"])
    afgifte = db.scalars(select(KluisAfgifte).where(KluisAfgifte.request_id == req_id).with_for_update()).first()
    req = db.get(ActionRequest, req_id)
    binding = (req.parameters or {}).get("catalog_binding") if req is not None else None
    ap = (
        db.scalars(select(Approval).where(Approval.request_id == req_id).order_by(Approval.approved_at.desc())).first()
        if req is not None
        else None
    )
    now = utcnow()
    gebonden = (
        afgifte is not None
        and req is not None
        and isinstance(binding, Mapping)
        and req.status == "bezig"
        and str(req.execution_nonce) == body["nonce"]
        and ap is not None
        and str(ap.id) == body["approval_id"]
        and ap.used_at is not None
        and ap.vervallen_op is None
        and afgifte.request_sha256 == body["request_sha256"]
        and binding["instance"]["instance_id"] == body["instance_id"]
        and [{k: r[k] for k in ("path", "ref", "revision")} for r in binding["vault_refs"]] == body["refs"]
        and (binding.get("koppeling") is not None) == body["token"]
    )
    if not gebonden:
        raise _weiger(409, "afgifte_past_niet", "De opvraag past niet bij een lopende uitvoering; niets afgegeven.")
    assert afgifte is not None and req is not None and ap is not None and isinstance(binding, Mapping)
    if afgifte.claimed_at is not None:
        raise _weiger(409, "afgifte_al_geclaimd", "Deze afgifte is al opgehaald; er komt geen tweede.")
    eind = min(afgifte.expires_at, ap.expires_at)
    if eind <= now:
        raise _weiger(410, "afgifte_verlopen", "De afgifte is verlopen; keur opnieuw goed.")
    geclaimd = db.execute(
        update(KluisAfgifte)
        .where(KluisAfgifte.request_id == req_id, KluisAfgifte.claimed_at.is_(None))
        .values(claimed_at=now)
    )
    if geclaimd.rowcount != 1:  # type: ignore[attr-defined]
        raise _weiger(409, "afgifte_al_geclaimd", "Deze afgifte is al opgehaald; er komt geen tweede.")
    db.commit()  # de claim staat vast vóór er iets wordt ontsleuteld: geen tweede afgifte, ook niet na een fout
    instance = str(binding["instance"]["instance_id"])
    waarden: dict[str, str] = {}
    try:
        for r in binding["vault_refs"]:
            row = db.scalars(select(AppGeheim).where(AppGeheim.revision == uuid.UUID(r["revision"]))).first()
            if row is None or row.ref != r["ref"] or str(row.instance_id) != instance:
                raise ValueError("revisie")
            waarden[r["path"]] = vault.decrypt(_aad(instance, r["ref"], r["revision"]), row.nonce, row.ciphertext)
    except Exception:
        raise _weiger(503, "kluis_niet_beschikbaar", "De appgeheimen zijn niet te lezen; niets afgegeven.") from None
    token: str | None = None
    if binding.get("koppeling") is not None:
        token = new_token("enr")
        db.add(
            EnrollmentGrant(
                kind="token",
                purpose="service",
                app_id=str(binding["provenance"]["record"]["app_id"]),
                secret_hash=sha256_hex(token),
                created_by="hub:kluisafgifte",
                expires_at=now + timedelta(seconds=settings.enrollment_token_ttl_seconds),
            )
        )
    klaar = _klare_tekst(waarden, token)
    uit = SUITE.encrypt(klaar, X25519PublicKey.from_public_bytes(_unb64(body["ontvanger"])), info=_info(rest))
    ttl = max(1, min(120, int((eind - now).total_seconds())))
    jwt, _ = keyring.issue_hub_service_jwt(
        audience=EXECUTOR_APP_ID,
        service_id=str(svc.id),
        ttl_seconds=ttl,
        kluis_afgifte={
            "request_sha256": body["request_sha256"],
            "claim_sha256": canonical_sha256(rest),
            "enc": _b64(uit[:ENC_LEN]),
            "ct": _b64(uit[ENC_LEN:]),
        },
    )
    audit.record(
        db,
        actor_type="service",
        actor_id=EXECUTOR_APP_ID,
        action="kluis.afgifte",
        target_type="action_request",
        target_id=str(req_id),
        details={"refs": [r["ref"] for r in binding["vault_refs"]], "token": token is not None},
    )
    db.commit()
    return {"afgifte": jwt}


def _klare_tekst(waarden: Mapping[str, str], token: str | None) -> bytes:
    """De klare tekst van §8.3, zonder typen: de executor kent het type alleen uit zijn eigen regel."""
    return canonical_json({"waarden": dict(waarden), "token": token})


def _info(rest: Mapping[str, Any]) -> bytes:
    """HPKE-info: de vaste tekst plus de claimhash; zo hoort de versleutelde tekst alleen bij deze opvraag."""
    return INFO + b":" + canonical_sha256(rest).encode()
