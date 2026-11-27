"""Ondertekende eigenaaracties via de bevestigde my_house-koppeling (contract §4.5 en §8)."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from asm_policy import Policy, execreq
from asm_policy.engine import Classification
from asm_policy.params import HUIS_DOELVELDEN as HUIS_DOELVELDEN
from asm_policy.params import MAX_EIGENAAR_BYTES
from jsonschema import Draft202012Validator, SchemaError
from referencing import Registry
from referencing.exceptions import Unresolvable
from sqlalchemy import select
from sqlalchemy.orm import Session

from hub import outbound
from hub.actions import blokkades
from hub.actions.doel import Doel
from hub.adapters import basis, my_house
from hub.config import Settings
from hub.errors import HubError
from hub.keys import KeyRing
from hub.models import ActionRequest, AdapterLink, CatalogApp
from hub.onboarding import gates
from hub.timeutil import utcnow
from hub.vault import Vault

CONCEPT = "zone.schedule.propose"
PREFIX = "/connector/v1/"
PIN_MELDING = "Plak eerst de Hub-sleutelset in my_house. Kopieer de publieke sleutelset bij Instellingen → Diensten."
DIENSTEN = "/instellingen/diensten#vingerafdruk-titel"


def ongeldig() -> HubError:
    return HubError(502, "bewijs_ongeldig", "my_house gaf geen passend voorstel of bewijs voor deze actie.")


def _uuid(value: Any) -> str:
    if not isinstance(value, str) or not execreq.UUID_RE.fullmatch(value):
        raise ongeldig()
    return value


def _tijd(value: Any) -> datetime:
    try:
        tijd = datetime.fromisoformat(value)
        if tijd.utcoffset() is None:
            raise ValueError
        return tijd
    except (ValueError, TypeError, OverflowError):
        raise ongeldig() from None


def _hash(value: Any) -> str:
    # Metingen mogen halve graden bevatten. De eigenaar hasht de ontvangen JSON inclusief die precisie.
    try:
        data = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True, allow_nan=False).encode()
    except (ValueError, TypeError, RecursionError):
        raise ongeldig() from None
    return "sha256:" + hashlib.sha256(data).hexdigest()


@dataclass
class Verbinding:
    adapter: my_house.Adapter
    token: str = field(repr=False)

    @property
    def binding(self) -> dict[str, str]:
        link = self.adapter.link
        return {
            "link_id": str(link.id),
            "server_id": str(link.my_house_server_id),
            "client_id": str(link.my_house_client_id),
        }

    def vraag(
        self,
        pad: str,
        *,
        body: dict[str, Any] | None = None,
        query: dict[str, str] | None = None,
        verwacht: int = 200,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.token}"}
        if body is not None:
            headers["Idempotency-Key"] = body["nonce"]
        try:
            base, beleid = self.adapter.verified_destination(self.token)
            res = outbound.request(
                base,
                "POST" if body is not None else "GET",
                PREFIX + pad,
                policy=beleid,
                headers=headers,
                json_body=body,
                query=query,
                max_bytes=basis.MAX_RESPONSE_BYTES,
            )
            data = res.json()
        except (outbound.OutboundError, OSError, ValueError, RecursionError):
            raise HubError(
                503, "my_house_unavailable", "De bevestigde my_house-koppeling is niet bereikbaar."
            ) from None
        if res.status == verwacht and isinstance(data, dict):
            return data
        code = data.get("code") if isinstance(data, dict) else None
        details = data.get("details") if isinstance(data, dict) else None
        if res.status == 501 and code == "capability_unavailable":
            ontbrekende_pin = isinstance(details, dict) and details.get("reason") == "hub_keyset_missing"
            if ontbrekende_pin or (pad == "propose" and details in (None, {})):
                raise HubError(501, code, PIN_MELDING, {"reason": "hub_keyset_missing", "href": DIENSTEN})
            raise HubError(501, code, "my_house biedt geen veilige uitvoering voor deze actie.")
        if res.status == 409 and code in ("policy_denied", "device_not_tested"):
            raise HubError(409, code, "my_house blokkeert dit doel. Controleer de bescherming en de apparaattest.")
        if 400 <= res.status < 500:
            raise HubError(res.status, "my_house_weigert", "my_house weigerde dit connectorverzoek.")
        raise ongeldig()


def verbind(db: Session, settings: Settings, vault: Vault, target: Mapping[str, Any]) -> Verbinding:
    from hub.routers.adapterkoppelingen import _house_adapter, _house_credential

    query = select(AdapterLink).where(AdapterLink.app_id == my_house.APP_ID)
    if "link_id" in target:
        query = query.where(AdapterLink.id == uuid.UUID(target["link_id"]))
    links = db.scalars(query.limit(2).with_for_update(read=True).execution_options(populate_existing=True)).all()
    if len(links) != 1:
        raise HubError(409, "doelbinding", "Selecteer één gekoppelde my_house-installatie met haar link_id.")
    link = links[0]
    catalogus = db.get(CatalogApp, link.catalog_app_id)
    if catalogus is None or link.my_house_client_id is None or link.my_house_server_id is None:
        raise HubError(409, "doelbinding", "De my_house-installatie heeft geen bevestigde Hub-koppeling.")
    try:
        credential = _house_credential(db, vault, link, utcnow())
    except outbound.OutboundError:
        raise HubError(409, "doelbinding", "De my_house-koppeling heeft geen geldig credential.") from None
    if credential.expires_at <= utcnow():
        raise HubError(409, "doelbinding", "De my_house-koppeling is verlopen.")
    return Verbinding(_house_adapter(db, settings, link, catalogus), credential.token)


def doelvelden(action_id: str, target: Mapping[str, Any]) -> dict[str, str]:
    veld = HUIS_DOELVELDEN[action_id]
    return {veld: target[veld]}


def controleer_schema(conn: Verbinding, action_id: str, target: dict[str, str], parameters: Mapping[str, Any]) -> None:
    veld, resource = next(iter(target.items()))
    data = conn.vraag("discover", query={"action_id": action_id, "target_id": resource})
    acties = data.get("actions")
    if data.get("checked_target") != target or not isinstance(acties, list) or len(acties) != 1:
        raise ongeldig()
    actie = acties[0]
    if not isinstance(actie, dict) or actie.get("action_id") != action_id or actie.get("target_field") != veld:
        raise ongeldig()
    schema = actie.get("params_schema")
    if (
        not isinstance(schema, dict)
        or schema.get("type") != "object"
        or schema.get("additionalProperties") is not False
        or schema.get("x-max-canonical-bytes") != MAX_EIGENAAR_BYTES
    ):
        raise ongeldig()
    try:
        Draft202012Validator.check_schema(schema)
        # Een lege registry laat alleen verwijzingen binnen dit ontvangen schema toe.
        geldig = Draft202012Validator(schema, registry=Registry()).is_valid(parameters)
    except (SchemaError, Unresolvable, RecursionError, ValueError, TypeError, re.error):
        raise ongeldig() from None
    if not geldig:
        raise HubError(
            422,
            "parameters_ongeldig",
            "De parameters voldoen niet aan het actieschema van my_house.",
            {"fouten": [{"veld": "parameters", "code": "schema", "fout": "voldoet niet aan discover"}]},
        )


def _toestand(state: Any) -> dict[str, Any]:
    if not isinstance(state, dict):
        raise ongeldig()
    if type(state.get("power")) is not bool or state.get("mode") not in ("auto", "cool", "dry", "fan", "heat", "off"):
        raise ongeldig()
    temperatuur = state.get("target_c")
    controls = state.get("controls")
    if (
        isinstance(temperatuur, bool)
        or not isinstance(temperatuur, int | float)
        or not 5 <= temperatuur <= 35
        or not isinstance(controls, dict)
    ):
        raise ongeldig()
    if not controls or not all(
        isinstance(k, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9]{0,23}", k) and type(v) is int
        for k, v in controls.items()
    ):
        raise ongeldig()
    return {"power": state["power"], "mode": state["mode"], "target_c": str(temperatuur), "controls": controls}


def voorstel(
    db: Session,
    settings: Settings,
    vault: Vault,
    keyring: KeyRing,
    policy: Policy,
    cls: Classification,
    target: Mapping[str, Any],
    parameters: Mapping[str, Any],
    actor: tuple[str, str],
    request_id: uuid.UUID,
    *,
    bestaand: ActionRequest | None = None,
) -> Doel:
    aid = cls.action_id
    nodig = blokkades.klimaatgates(aid)
    if nodig:
        blok = blokkades.uit_gates(policy, gates.evaluate(blokkades.gate_inputs(db, settings)), nodig)
        if blok:
            raise HubError(
                409,
                "actie_geblokkeerd",
                "Laat eerst de fysieke klimaatbediening testen en bevestigen.",
                {"blokkades": blok},
            )
    conn = verbind(db, settings, vault, target)
    native = doelvelden(aid, target)
    if bestaand is not None:
        meta = bestaand.preview["my_house"]
        if any(meta.get(k) != v for k, v in conn.binding.items()) or _tijd(meta["valid_until"]) <= utcnow():
            raise HubError(
                409, "voorstel_verlopen", "De koppeling of geldigheid van het my_house-voorstel is gewijzigd."
            )
    controleer_schema(conn, aid, native, parameters)
    if bestaand is None:
        now = utcnow()
        nonce = str(uuid.uuid4())
        body = execreq.sign(
            {
                "proposal": {
                    "action_id": aid,
                    "idempotency_key": str(request_id),
                    "actor": {"type": actor[0], "id": actor[1]},
                    "target": native,
                    "parameters": dict(parameters),
                    "expected_version": "eigenaar",
                },
                "policy_decision": {
                    "risk_class": cls.risk_class,
                    "rule_ids": list(cls.rule_ids),
                    "policy_hash": policy.hash,
                },
                "approval": None,
                "issued_at": execreq.iso(now),
                "expires_at": execreq.iso(now + timedelta(minutes=5)),
                "nonce": nonce,
            },
            keyring.policy_signing,
        )
        data = conn.vraag("propose", body=body)
        if data.get("status") == "unavailable" and data.get("reason_code") == "capability_unavailable":
            raise HubError(
                501, "capability_unavailable", "Voor deze actie biedt my_house geen veilige uitvoering met herstel."
            )
        if data.get("status") != "proposed" or data.get("concept_only") is not (aid == CONCEPT):
            raise ongeldig()
        diff, before, etag = data.get("diff"), data.get("before"), data.get("resource_etag")
        if (
            not isinstance(before, dict)
            or not isinstance(diff, dict)
            or _hash(diff.get("proposed")) != _hash(parameters)
            or _hash(diff.get("before")) != _hash(before)
        ):
            raise ongeldig()
        if (
            not isinstance(etag, str)
            or not execreq.SHA_RE.fullmatch(etag)
            or data.get("blast_radius") != [native]
            or data.get("requires_backup") is not False
        ):
            raise ongeldig()
        phash = _hash(
            {
                "direction": "apply",
                "action_id": aid,
                "diff": diff,
                "blast_radius": [native],
                "resource_etag": etag,
                "rollback_recipe": data.get("rollback_recipe"),
            }
        )
        if phash != data.get("preview_hash") or not now < _tijd(data.get("valid_until")) <= now + timedelta(minutes=5):
            raise ongeldig()
        meta = {
            **conn.binding,
            "proposal_id": _uuid(data.get("proposal_id")),
            "preview_hash": phash,
            "valid_until": data["valid_until"],
            "before_hash": _hash(before),
        }
        if aid == CONCEPT:
            if not isinstance(before.get("schedule"), list) or data.get("rollback_recipe") is not None:
                raise ongeldig()
            huidig = {"tijdsblokken": len(before["schedule"])}
        else:
            huidig = _toestand(before)
            # De huidige eigenaar kan uitsluitend een losse wijziging van de insteltemperatuur herstellen.
            if (
                aid != "zone.command"
                or set(parameters) != {"target_c"}
                or not huidig["power"]
                or data.get("rollback_recipe") != {"target_c": before["target_c"]}
            ):
                raise ongeldig()
    else:
        etag = bestaand.resource_etag
        bewijs = conn.vraag("evidence/" + _uuid(meta["proposal_id"]))
        if (
            bewijs.get("id"),
            bewijs.get("action_id"),
            bewijs.get("status"),
            bewijs.get("preview_hash"),
            bewijs.get("resource_etag"),
            bewijs.get("before_hash"),
        ) != (meta["proposal_id"], aid, "proposed", meta["preview_hash"], etag, meta["before_hash"]):
            raise ongeldig()
        huidig = bestaand.preview["huidig"]
    return Doel(
        "eigenaar",
        f"my_house/{conn.binding['link_id']}/{next(iter(native.values()))}",
        etag,
        True,
        staat=huidig,
        eigenaar={
            "preview_hash": meta["preview_hash"],
            "requires_backup": False,
            "diff": {"voorgesteld": dict(parameters)},
            "my_house": meta,
        },
    )


def gebonden_verbinding(db: Session, settings: Settings, vault: Vault, req: ActionRequest) -> Verbinding:
    meta = req.preview["my_house"]
    conn = verbind(db, settings, vault, {"link_id": meta["link_id"]})
    if any(meta.get(k) != v for k, v in conn.binding.items()):
        raise HubError(409, "doelbinding", "Deze koppeling hoort niet meer bij het goedgekeurde my_house-voorstel.")
    return conn


def lees_bewijs(conn: Verbinding, req: ActionRequest, command_id: str | None) -> tuple[str, dict[str, Any]]:
    meta = req.preview["my_house"]
    data = conn.vraag("evidence/" + _uuid(meta["proposal_id"]))
    if (
        data.get("id"),
        data.get("action_id"),
        data.get("resource_etag"),
        data.get("preview_hash"),
        data.get("before_hash"),
    ) != (meta["proposal_id"], req.action_id, req.resource_etag, meta["preview_hash"], meta["before_hash"]):
        raise ongeldig()
    identiteit = _uuid(data.get("command_id"))
    if command_id is not None and identiteit != command_id:
        raise ongeldig()
    resultaat = {"evidence_id": meta["proposal_id"], "command_id": identiteit, "before_hash": meta["before_hash"]}
    status = data.get("status")
    if status == "queued":
        return "bezig", resultaat
    if status == "failed":
        if data.get("recovery_required") is not False:
            return "onbekend", {**resultaat, "code": "uitkomst_onbekend"}
        return "mislukt", {**resultaat, "code": "readback_mislukt"}
    if status != "confirmed" or data.get("rollback_command_id") is not None:
        raise ongeldig()
    before, after = data.get("before"), data.get("after")
    if (
        not isinstance(before, dict)
        or _hash(before) != meta["before_hash"]
        or after is None
        or _hash(after) != data.get("after_hash")
    ):
        raise ongeldig()
    eerst, laatst = _tijd(data.get("before_observed_at")), _tijd(data.get("after_observed_at"))
    if not eerst <= laatst <= utcnow() or req.gestart_op is None or laatst < req.gestart_op:
        raise ongeldig()
    voor, na = _toestand(before), _toestand(after)
    if req.action_id != "zone.command" or _hash(after) != _hash({**before, "target_c": req.parameters.get("target_c")}):
        raise ongeldig()
    return "uitgevoerd", {
        **resultaat,
        "after_hash": data["after_hash"],
        "before": voor,
        "after": na,
        "before_observed_at": eerst.isoformat(),
        "after_observed_at": laatst.isoformat(),
    }
