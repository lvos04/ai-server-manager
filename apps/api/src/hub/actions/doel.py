"""Eigen alleen-lezen readback van het doel van een actie (contract 1.3 §8: "precondities via readback").

De Hub leest het doel met zijn alleen-lezen TrueNAS-sleutel en rekent de ``resource_etag`` met dezelfde functie als de
executor (:mod:`asm_policy.etag`). Kan de Hub het doel niet lezen, dan is de toestand onbekend en komt er geen preview
en geen goedkeuring (fail-closed) — onbekend telt nooit als "ongewijzigd". De herkenning van een app (naam,
catalogusapp en images) komt uit :func:`asm_policy.engine.herken_app`, net als in de executor; is niet vast te stellen
wat er in een bestaande app draait (gestopt, geen catalogusapp), dan weigert het beleid elke actie erop. Ook de image
ná de actie telt mee: de nieuwe image bij ``app.update``, en bij ``app.rollback`` met ``herstel_van`` de images van
vóór die wijziging zoals de Hub ze toen zag (de preview van dat verzoek; de bewaarde waarden zelf kent alleen de
executor, die herkent er zelf op). Een herkenning maakt alleen strenger (S-P2-010, R-VEILIG-2).
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from asm_policy import Policy
from asm_policy import etag as etags
from asm_policy.engine import Herkenning, herken_app
from asm_policy.loader import ActieDef
from asm_policy.params import expected_image, verwachte_catalogus
from sqlalchemy.orm import Session

from hub.config import Settings
from hub.models import ActionRequest
from hub.truenas.client import TrueNASClient, TrueNASError
from hub.truenas.connection import API_KEY_REF, connection_row, current_target, tls_for
from hub.vault import Vault


class DoelOnbekend(Exception):
    """Het doel is nu niet leesbaar (NAS niet ingesteld, niet bereikbaar, geen leesrecht)."""

    def __init__(self, reason_code: str, detail: str = "") -> None:
        super().__init__(reason_code)
        self.reason_code, self.detail = reason_code, detail


@dataclass
class Doel:
    soort: str
    naam: str
    etag: str
    bestaat: bool
    staat: dict[str, Any] = field(default_factory=dict)
    # Alle herkenningen (naam, catalogusapp en image; de regels van allemaal gelden) en of die volledig is. De standaard
    # (doelen zonder app) zegt "na een stop niet herkenbaar": dicht bij twijfel (S-P2-010).
    herkend_als: Herkenning = field(default_factory=lambda: Herkenning((), True, False))
    extra_bestaat: bool = False  # snapshot of sandbox-dataset bestaat al

    @property
    def sleutel(self) -> str:
        return f"{self.soort.replace('app_nieuw', 'app')}:{self.naam}"[:300]


def _dataset_exists(tree: Any, name: str) -> bool:
    for node in tree if isinstance(tree, list) else []:
        if not isinstance(node, dict):
            continue
        if node.get("id") == name or node.get("name") == name:
            return True
        if _dataset_exists(node.get("children"), name):
            return True
    return False


async def _snapshots(client: TrueNASClient, dataset: str) -> list[str]:
    got = await client.call("core.get_methods")
    methods = {str(m) for m in got} if isinstance(got, dict | list) else set()
    method = next((m for m in ("pool.snapshot.query", "zfs.snapshot.query") if m in methods), None)
    if method is None:
        raise DoelOnbekend("capability_unavailable", "deze TrueNAS-versie kent geen leesmethode voor snapshots")
    rows = await client.call(method, [[["dataset", "=", dataset]]])
    names = [str(r.get("name")) for r in rows or [] if isinstance(r, dict)]
    return sorted(n for n in names if n.split("@", 1)[0] == dataset)


def vorige_images(db: Session, actie: ActieDef, target: Mapping[str, Any], parameters: Mapping[str, Any]) -> list[str]:
    """Bij ``app.rollback`` met ``herstel_van``: de images van het doel vóór die wijziging, uit de preview van dat
    verzoek (``huidig.images``). Leeg als het verzoek er niet is of bij een ander doel hoort; de executor herkent dan
    zelf op de waarden die hij bewaarde."""
    if actie.action_id != "app.rollback" or not isinstance(parameters, Mapping) or "herstel_van" not in parameters:
        return []
    try:
        request_id = uuid.UUID(str(parameters["herstel_van"]))
    except ValueError:
        return []
    vorig = db.get(ActionRequest, request_id)
    if vorig is None or not isinstance(vorig.target, dict) or vorig.target.get("app_id") != target.get("app_id"):
        return []
    huidig = (vorig.preview or {}).get("huidig") if isinstance(vorig.preview, dict) else None
    images = huidig.get("images") if isinstance(huidig, dict) else None
    return [str(i) for i in images if i] if isinstance(images, list) else []


async def _lees(
    client: TrueNASClient,
    policy: Policy,
    actie: ActieDef,
    target: Mapping[str, Any],
    parameters: Mapping[str, Any],
    na_actie: list[str] | None = None,
) -> Doel:
    if actie.doel in ("app", "app_nieuw"):
        name = str(target["app_id"])
        apps = await client.call("app.query")
        images = [i for i in (await client.call("app.image.query") or []) if isinstance(i, dict)]
        app = next((a for a in apps or [] if isinstance(a, dict) and a.get("name") == name), None)
        verwacht = expected_image(parameters)
        return Doel(
            actie.doel,
            name,
            etags.app_etag(app, images),
            app is not None,
            etags.app_state(app, images) if app is not None else {"naam": name, "afwezig": True},
            herken_app(
                policy,
                name,
                app,
                [str((verwacht or {}).get("repository") or ""), *(na_actie or [])],
                catalogus=verwachte_catalogus(parameters),
            ),
        )
    tree = await client.call("pool.dataset.query")
    if actie.doel == "dataset":
        ds = str(target["dataset"])
        snaps = await _snapshots(client, ds)
        full = f"{ds}@{parameters.get('naam')}"
        return Doel(
            "dataset",
            ds,
            etags.dataset_etag(ds),
            _dataset_exists(tree, ds),
            {"dataset": ds, "snapshot": full, "snapshot_bestaat_al": full in snaps},
            extra_bestaat=full in snaps,
        )
    snap = str(target["snapshot"])
    ds = snap.split("@", 1)[0]
    dst = str(parameters.get("doel_dataset"))
    dst_exists = _dataset_exists(tree, dst)
    return Doel(
        "snapshot",
        snap,
        etags.snapshot_etag(snap),
        snap in await _snapshots(client, ds),
        {"snapshot": snap, "doel_dataset": dst, "doel_dataset_bestaat_al": dst_exists},
        extra_bestaat=dst_exists,
    )


def lees_doel(
    db: Session,
    vault: Vault,
    settings: Settings,
    policy: Policy,
    actie: ActieDef,
    target: Mapping[str, Any],
    parameters: Mapping[str, Any],
) -> Doel:
    """Lees het doel nu uit TrueNAS. ``DoelOnbekend`` als dat niet kan; nooit een aanname."""
    if actie.doel == "geen":
        return Doel("geen", "", "geen", True)
    if actie.doel == "eigenaar":
        return Doel("eigenaar", str(target.get("app_id") or ""), "eigenaar", True)
    nas = current_target(db)
    if nas is None:
        raise DoelOnbekend("not_configured", "Besluit D03 (NAS-adres) is nog niet ingevuld.")
    api_key = vault.get(db, API_KEY_REF)
    if not api_key:
        raise DoelOnbekend("not_configured", "Er is nog geen alleen-lezen-API-key ingesteld.")
    tls = tls_for(connection_row(db), nas, settings)
    na_actie = vorige_images(db, actie, target, parameters)

    async def run() -> Doel:
        async with TrueNASClient(
            nas.url,
            api_key,
            tls=tls,
            connect_timeout=settings.truenas_connect_timeout,
            read_timeout=settings.truenas_read_timeout,
        ) as client:
            return await _lees(client, policy, actie, target, parameters, na_actie)

    try:
        return asyncio.run(run())
    except TrueNASError as exc:
        raise DoelOnbekend(exc.reason_code, exc.detail) from None
