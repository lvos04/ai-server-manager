"""Afzonderlijke geheime overdracht, kant van de executor (contract 1.3 §8.3, M2; S-P2-050e).

Na alle eigen controles en vlak vóór ``app.create`` claimt de executor de waarden één keer bij de Hub: ondertekend met
zijn eigen identiteit, over zijn bestaande koppeling, met een X25519-sleutel die alleen in het geheugen leeft. Het
antwoord is een Hub-dienst-JWT (gepinde sleutels, §4.7) met de waarden HPKE-versleuteld naar die sleutel. Daarna toetst
hij elke waarde aan het type dat zijn eigen witte lijst aan de plek geeft en vult hij een tijdelijke kopie in.

Nooit een waarde in log, journaal, antwoord of fout: een :class:`KluisFout` draagt alleen een vaste code.
"""

from __future__ import annotations

import base64
import copy
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from asm_policy.canonical import canonical_json, canonical_sha256
from asm_policy.catalogbinding import APPGEHEIM, TOKEN, TOKEN_ENV, VORM, koppelbaar, regels_voor_record
from asm_policy.loader import Policy
from cryptography.hazmat.primitives import hpke, serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from executor import APP_ID
from executor.firststart import IDENTITY
from executor.hublink import HubLinkStore, HubResponse, hub_request, verify_hub_jwt

PAD = "/api/v1/executor/secret-claims"
INFO = b"asm-kluis-afgifte-v1"
SUITE = hpke.Suite(hpke.KEM.X25519, hpke.KDF.HKDF_SHA256, hpke.AEAD.AES_256_GCM)
AFGIFTE_KEYS = {"request_sha256", "claim_sha256", "enc", "ct"}


class KluisFout(Exception):
    """Weigering zonder schrijfaanroep; alleen een vaste code, nooit een waarde."""

    def __init__(self, status: int, code: str, melding: str) -> None:
        super().__init__(code)
        self.status, self.code, self.melding = status, code, melding


def _mislukt() -> KluisFout:
    melding = "De geheimen konden niet bij de Hub worden opgehaald; er is niets geïnstalleerd. Keur opnieuw goed."
    return KluisFout(503, "kluis_afgifte_mislukt", melding)


def _vorm() -> KluisFout:
    return KluisFout(422, "kluis_vorm_ongeldig", "Een geheim past niet bij zijn plek; er is niets geïnstalleerd.")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def regel_van(policy: Policy, params: Mapping[str, Any]) -> dict[str, Any] | None:
    """De eigen witte-lijstregel met kluisplekken, of ``None`` (geen binding of geen plekken: niets in te vullen)."""
    b = params.get("catalog_binding")
    if not isinstance(b, Mapping):
        return None
    regels = regels_voor_record(policy.catalogus, b["provenance"]["record"])
    return regels[0] if len(regels) == 1 and regels[0]["kluisplekken"] else None


def markering(regel: Mapping[str, Any], binding: Mapping[str, Any]) -> list[dict[str, str]]:
    """Per plek ``env`` en type, bij een appgeheim ook ref en revisie; nooit een waarde of hash (§8.3)."""
    per_ref = {r["parameter"]: r for r in binding["vault_refs"]}
    uit: list[dict[str, str]] = []
    for p in regel["kluisplekken"]:
        rij = {"env": p["env"], "type": p["type"]}
        if p["type"] == APPGEHEIM:
            r = per_ref[p["env"].lower()]
            rij.update(ref=r["ref"], revision=r["revision"])
        uit.append(rij)
    return uit


def vingerafdruk(link: Mapping[str, Any]) -> Any:
    """De gepinde Hub-vingerafdruk van de eigen koppeling (§3.9), zoals ``public_status`` die toont."""
    return (link.get("pins") or {}).get("keyset_fingerprint")


def vul_in(
    regel: Mapping[str, Any],
    binding: Mapping[str, Any],
    values: Mapping[str, Any],
    afgifte: Any,
    link: Mapping[str, Any],
) -> dict[str, Any]:
    """Een tijdelijke kopie van ``values`` met precies de gevraagde plekken ingevuld; elke afwijking weigert alles."""
    if not isinstance(afgifte, Mapping) or set(afgifte) != {"waarden", "token"}:
        raise _vorm()
    waarden, token = afgifte["waarden"], afgifte["token"]
    paden = {r["path"]: r for r in binding["vault_refs"]}
    if not isinstance(waarden, Mapping) or set(waarden) != set(paden):
        raise _vorm()
    typen = {p["env"]: p["type"] for p in regel["kluisplekken"]}
    envs = copy.deepcopy(list(values.get("envs") or []))
    for pad, waarde in waarden.items():
        i = int(pad[len("values.envs[") : -len("].value")])
        naam = envs[i].get("name")
        # Het type komt uitsluitend uit de eigen regel; de plek moet nog precies de gebonden verwijzing dragen.
        if typen.get(naam) != APPGEHEIM or envs[i].get("value") != paden[pad]["ref"]:
            raise _vorm()
        if not isinstance(waarde, str) or VORM[APPGEHEIM].fullmatch(waarde) is None:
            raise _vorm()
        envs[i] = {"name": naam, "value": waarde}
    if koppelbaar(regel):
        if not isinstance(token, str) or VORM[TOKEN].fullmatch(token) is None:
            raise _vorm()
        envs += [
            {"name": "HUB_URL", "value": str(link["hub_url"])},
            {"name": "HUB_KEY_FINGERPRINT", "value": str(vingerafdruk(link))},
            {"name": TOKEN_ENV, "value": token},
        ]
    elif token is not None:
        raise _vorm()
    return {**values, "envs": envs}


class Kluis:
    """De opvraag bij de Hub over de bestaande koppeling (§3.2-adresregels, nooit een redirect)."""

    def __init__(self, store: HubLinkStore, secrets_dir: Path, *, allow_loopback: bool = False) -> None:
        self.store, self.secrets_dir, self.allow_loopback = store, secrets_dir, allow_loopback

    def _identiteit(self) -> Ed25519PrivateKey:
        key = serialization.load_pem_private_key((self.secrets_dir / IDENTITY).read_bytes(), password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise ValueError("identiteit")
        return key

    def vul(self, regel: Mapping[str, Any], request: Mapping[str, Any]) -> dict[str, Any]:
        """Koppeling toetsen, eenmalig claimen, ontsleutelen, vorm toetsen en invullen (in die volgorde)."""
        params = request["proposal"]["parameters"]
        binding = params["catalog_binding"]
        link = self.store.read()
        if link.get("state") != "gekoppeld" or link.get("_onleesbaar") or not link.get("service_token"):
            raise _mislukt()
        if binding["koppeling"] is not None and binding["koppeling"] != {
            "soort": "volledig",
            "hub_url": link.get("hub_url"),
            "hub_key_fingerprint": vingerafdruk(link),
        }:
            melding = "De Hub-koppeling in het plan is niet die van deze executor; er is niets geïnstalleerd."
            raise KluisFout(409, "koppeling_past_niet", melding)
        afgifte = self._vraag_op(link, request, binding)
        return vul_in(regel, binding, params["app_create"]["values"], afgifte, link)

    def opvraag(
        self, request: Mapping[str, Any], binding: Mapping[str, Any], ontvanger: X25519PrivateKey
    ) -> dict[str, Any]:
        """De velden van de opvraag zonder handtekening (§8.3)."""
        approval = request.get("approval") or {}
        return {
            "request_id": str(approval.get("request_id")),
            "request_sha256": canonical_sha256(request),
            "nonce": str(request["nonce"]),
            "approval_id": str(approval.get("approval_id")),
            "instance_id": str(binding["instance"]["instance_id"]),
            "refs": [{k: r[k] for k in ("path", "ref", "revision")} for r in binding["vault_refs"]],
            "token": binding["koppeling"] is not None,
            "ontvanger": _b64(ontvanger.public_key().public_bytes_raw()),
            "issued_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    def stuur(self, link: Mapping[str, Any], rest: Mapping[str, Any]) -> HubResponse:
        """Onderteken met de eigen identiteit en stuur over de bestaande koppeling (service-token, geen redirect)."""
        body = {**rest, "handtekening": _b64(self._identiteit().sign(canonical_json(dict(rest))))}
        return hub_request(
            str(link["hub_url"]),
            "POST",
            PAD,
            body=body,
            bearer=str(link["service_token"]),
            allow_loopback=self.allow_loopback,
        )

    def _vraag_op(self, link: Mapping[str, Any], request: Mapping[str, Any], binding: Mapping[str, Any]) -> Any:
        ontvanger = X25519PrivateKey.generate()  # alleen voor deze opvraag, alleen in het geheugen
        rest = self.opvraag(request, binding, ontvanger)
        try:
            res = self.stuur(link, rest)
            jwt = res.body.get("afgifte") if res.status == 200 and isinstance(res.body, dict) else None
            claims = verify_hub_jwt(str(jwt), link, audience=APP_ID)
            ka = claims.get("kluis_afgifte")
            claim_sha = canonical_sha256(rest)
            if not (
                isinstance(ka, dict)
                and set(ka) == AFGIFTE_KEYS
                and ka["request_sha256"] == rest["request_sha256"]
                and ka["claim_sha256"] == claim_sha
            ):
                raise ValueError("afgifte")
            klaar = SUITE.decrypt(
                _unb64(str(ka["enc"])) + _unb64(str(ka["ct"])), ontvanger, info=INFO + b":" + claim_sha.encode()
            )
            return json.loads(klaar)
        except Exception:  # transport, JWT, hashes of HPKE: nooit details, nooit de waarde
            raise _mislukt() from None
