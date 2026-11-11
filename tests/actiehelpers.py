"""Gedeelde opzet voor de actietests: de **echte** Hub-API, de **echte** executor-app en de fake TrueNAS (Sim-getest).

De Hub leest de NAS met de alleen-lezen-sleutel; de executor schrijft met zijn eigen schrijfsleutel. De executor wordt
gekoppeld via zijn statuspagina (koppelcode + vingerafdruk) en draait als echte HTTP-server, zodat de Hub hem aanroept
met een dienst-JWT en een ondertekend ``ExecutionRequest``. Alleen testwaarden; nooit echte NAS-gegevens.

De gates rekenen met de echte beoordeling (:func:`hub.onboarding.gates.evaluate`); een test zet alleen de *invoer*
(besluiten en de eigen back-up) via :class:`Toestand`, nooit de uitkomst.
"""

from __future__ import annotations

import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any

import uvicorn
from conftest import idem
from executorhelpers import NAS_HOST, WRITE_KEY
from fakes.fake_truenas import FakeTrueNAS
from nashelpers import connect, refresh

HOST = "nas-primary"
EX_BASE = "http://executor.local"
ALLE_BESLUITEN = {f"D{n:02d}": ("Getest", None) for n in range(1, 19)}


class Served:
    """Een ASGI-app als echte HTTP-server op 127.0.0.1 (willekeurige vrije poort)."""

    def __init__(self, app: Any) -> None:
        self.server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        deadline = time.monotonic() + 15
        while not self.server.started:
            if time.monotonic() > deadline:
                raise RuntimeError("server start niet")
            time.sleep(0.05)
        port = self.server.servers[0].sockets[0].getsockname()[1]
        self.url = f"http://127.0.0.1:{port}"

    def stop(self) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=10)


@dataclass
class Toestand:
    """Invoer voor de gates die een test zet. ``besluiten=None`` laat de echte besluiten staan (alles Open)."""

    besluiten: dict[str, tuple[str, Any]] | None = field(default_factory=lambda: dict(ALLE_BESLUITEN))
    backup: str = "vers"  # vers | geen | oud | echt


@dataclass
class Stack:
    admin: Any
    app: Any
    nas: FakeTrueNAS
    worker_once: Any
    toestand: Toestand
    ex_settings: Any = None
    ex_url: str = ""
    servers: list[Served] = field(default_factory=list)

    def vernieuw(self) -> None:
        """Inventaris opnieuw meten (de pool- en appstaat waar de gates en previews op rekenen)."""
        refresh(self.admin, self.worker_once)

    def stop(self) -> None:
        for s in self.servers:
            s.stop()
        self.servers.clear()


def zet_gate_invoer(monkeypatch: Any, toestand: Toestand) -> None:
    """Besluiten en eigen back-up als *gemeten invoer* zetten; pool en executor blijven echt gemeten."""
    from hub.actions import blokkades
    from hub.routers.onboarding import gate_inputs as echte
    from hub.timeutil import utcnow

    def invoer(db: Any, settings: Any) -> Any:
        inp = echte(db, settings)
        if toestand.besluiten is not None:
            inp.decisions = dict(toestand.besluiten)
        if toestand.backup == "vers":
            inp.eigen_backup = {"finished_at": utcnow(), "sha256": "sha256:" + "c" * 64, "id": str(uuid.uuid4())}
        elif toestand.backup == "oud":
            oud = utcnow() - timedelta(seconds=inp.eigen_backup_max_age_seconds + 60)
            inp.eigen_backup = {"finished_at": oud, "sha256": "sha256:" + "c" * 64, "id": str(uuid.uuid4())}
        elif toestand.backup == "geen":
            inp.eigen_backup = None
        return inp

    monkeypatch.setattr(blokkades, "gate_inputs", invoer)


def koppel_executor(admin: Any, hub_url: str, ex_app: Any) -> None:
    """Koppelen zoals een beheerder het doet: koppelcode uit de Hub, invullen op de statuspagina van de executor."""
    from fastapi.testclient import TestClient

    r = admin.post("/api/v1/services/pairing-codes", json={"app_id": "ai-server-manager-executor"})
    assert r.status_code == 201, r.text
    grant = r.json()
    c = TestClient(ex_app, base_url=EX_BASE)
    m = re.search(r'name="csrf" value="([^"]+)"', c.get("/").text)
    r = c.post(
        "/koppelen",
        data={
            "csrf": m.group(1) if m else "",
            "hub_adres": hub_url,
            "koppelcode": grant["koppelcode"],
            "hub_vingerafdruk": grant["keyset_fingerprint"],
        },
        headers={"Origin": EX_BASE},
    )
    assert r.status_code == 200 and "Gekoppeld met de Hub" in r.text, r.text


def bouw_stack(
    *,
    admin: Any,
    app: Any,
    nas: FakeTrueNAS,
    worker_once: Any,
    tmp_path: Path,
    monkeypatch: Any,
    met_executor: bool = True,
    schrijfsleutel: bool = True,
) -> Stack:
    from executor.app import create_app
    from executor.config import Settings
    from executor.firststart import ensure_secrets
    from executor.naslink import NasLinkStore
    from executor.truenas import fetch_fingerprint

    toestand = Toestand()
    stack = Stack(admin=admin, app=app, nas=nas, worker_once=worker_once, toestand=toestand)
    connect(admin, nas)
    refresh(admin, worker_once)
    zet_gate_invoer(monkeypatch, toestand)
    if not met_executor:
        return stack
    hub_srv = Served(app)
    stack.servers.append(hub_srv)
    settings = Settings(
        data_dir=tmp_path / "executor",
        allow_loopback_hub=True,
        truenas_host=NAS_HOST,
        truenas_port=nas.port,
        truenas_timeout_seconds=5,
        readback_wait_seconds=0.6,
        readback_poll_seconds=0.05,
        allow_writable_policy=True,
    )
    ensure_secrets(settings.secrets_dir)
    ex_app = create_app(settings)
    koppel_executor(admin, hub_srv.url, ex_app)
    if schrijfsleutel:
        fingerprint = fetch_fingerprint(NAS_HOST, nas.port)
        NasLinkStore(settings.secrets_dir).save_key(NAS_HOST, nas.port, fingerprint, WRITE_KEY, ["FULL_ADMIN"])
    ex_srv = Served(ex_app)
    stack.servers.append(ex_srv)
    stack.ex_settings, stack.ex_url = settings, ex_srv.url
    # Het adres van de executor komt in productie uit de inventaris (app.query + D03); hier is het de testserver.
    monkeypatch.setattr("hub.actions.service.service_base_url", lambda db, s, svc: (stack.ex_url, None))
    return stack


# ---------------------------------------------------------------------- aanroepen
def app_target(name: str) -> dict[str, Any]:
    return {"host_id": HOST, "app_id": name}


def stel_voor(
    c: Any, action_id: str, target: dict[str, Any], parameters: dict[str, Any] | None = None, **meer: Any
) -> Any:
    body: dict[str, Any] = {"action_id": action_id, "target": target, "parameters": parameters or {}, "reason": "test"}
    body.update(meer)
    return c.post("/api/v1/actions", json=body, headers=idem())


def hashes(voorstel: dict[str, Any]) -> dict[str, str]:
    return {k: voorstel[k] for k in ("preview_hash", "resource_etag", "policy_hash")}


def keur_goed(c: Any, voorstel: dict[str, Any], **wijzig: str) -> Any:
    return c.post(
        f"/api/v1/actions/{voorstel['request_id']}/approve", json={**hashes(voorstel), **wijzig}, headers=idem()
    )


def voer_uit(c: Any, voorstel: dict[str, Any] | str) -> Any:
    rid = voorstel if isinstance(voorstel, str) else voorstel["request_id"]
    return c.post(f"/api/v1/actions/{rid}/execute", headers=idem())


def haal(c: Any, voorstel: dict[str, Any] | str) -> dict[str, Any]:
    rid = voorstel if isinstance(voorstel, str) else voorstel["request_id"]
    r = c.get(f"/api/v1/actions/{rid}")
    assert r.status_code == 200, r.text
    return dict(r.json())


def schrijfaanroepen(nas: FakeTrueNAS) -> list[str]:
    """Schrijfaanroepen die TrueNAS kreeg (zonder het lezen van de app-configuratie door de executor)."""
    return [m for m in nas.mutations if m != "app.config"]


def audit_acties(app: Any) -> list[str]:
    from sqlalchemy import select

    from hub.models import AuditEvent

    with app.state.sessionmaker() as db:
        return [str(a) for a in db.scalars(select(AuditEvent.action).order_by(AuditEvent.id))]
