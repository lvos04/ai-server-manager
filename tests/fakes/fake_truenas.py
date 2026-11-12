"""In-repo fake TrueNAS: JSON-RPC 2.0 over WebSocket (wss) op ``/api/current``.

Alleen voor tests (simulator). Gedrag dat de echte TrueNAS-middleware nabootst:
- ``auth.login_with_api_key`` → ``true``/``false``; zonder aanmelding geeft elke methode ``ENOTAUTHENTICATED``;
- onbekende methode → ``-32601``; geweigerde methode → ``-32001`` met ``errname: EACCES``;
- versieprofielen: ``25.04`` (``pool.snapshot.query``) en ``24.10`` (``zfs.snapshot.query``);
- notificaties (``collection_update``) tussen antwoorden door;
- TLS met een eigen test-CA (zelfondertekend vanuit het perspectief van de Hub).
Elke aanroep wordt gelogd; aanroepen van niet-leesmethoden komen in ``mutations`` (tests van de Hub eisen dat die leeg
blijft).

Schrijven (voor de executor, fase P2): alleen een sleutel met ``KeyProfile(write=True)`` mag schrijfmethoden aanroepen;
elke andere sleutel krijgt ``EACCES``. Ook dan gelden rechten per methode volgens de rollen (R-TECH-1, S-P2-020):
``FULL_ADMIN`` mag alles, ``APPS_WRITE`` de app-methoden (en ``app.config``), ``SNAPSHOT_WRITE`` de snapshotmethoden
(maken en klonen); de rest alleen ``FULL_ADMIN``. Die indeling is een aanname uit de publieke rolnamen: NIET
GEVALIDEERD (echte NAS). De websocket-server logt via een eigen logger vast op INFO, zodat een test met de root-logger
op DEBUG geen frames met de sleutel van de fake in de log krijgt (R-VEILIG-4). App-methoden zijn jobs (een job-id als
antwoord, uitkomst via
``core.get_jobs``); de wijziging staat direct in de testdata. Testknoppen: ``fail`` (methode → foutmelding),
``silent_noop`` (job "geslaagd" zonder wijziging), ``digest_override`` (repository → andere digest dan gevraagd),
``hidden`` (methoden die deze "versie" niet aanbiedt) en ``job_polls`` (aantal keer RUNNING vóór de eindstaat).

Een gestopte app (``STOPPED``) heeft lege ``active_workloads``: geen images, containers, poorten of volumes, net als in
de broncode van TrueNAS (middleware ``plugins/apps/ix_apps/query.py``, ``list_apps`` en
``get_default_workload_values``; gelezen in release/25.04.2 en release/25.10.0, NIET GEVALIDEERD op een echte NAS).
De werklast van daarvoor bewaart de fake apart (``_werklast``) en zet hij terug bij het starten.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import hashlib
import ipaddress
import json
import logging
import ssl
import tempfile
import threading
from dataclasses import dataclass, field
from http import HTTPStatus
from pathlib import Path
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from websockets.asyncio.server import Server, ServerConnection, serve
from websockets.exceptions import ConnectionClosed
from websockets.http11 import Request, Response

READ_METHODS = {
    "auth.login_with_api_key",
    "auth.me",
    "core.get_methods",
    "system.version",
    "system.info",
    "pool.query",
    "pool.dataset.query",
    "app.query",
    "app.image.query",
    "app.gpu_choices",
    "device.get_info",
    "disk.query",
    "smart.test.results",
    "pool.snapshottask.query",
    "pool.snapshot.query",
    "zfs.snapshot.query",
    "cloudsync.query",
    "replication.query",
    "alert.list",
    "network.general.summary",
    "interface.query",
    "core.subscribe",
    "core.unsubscribe",
    "core.get_jobs",
}
WRITE_METHODS = {
    "app.upgrade",
    "app.rollback",
    "pool.snapshot.clone",
    "zfs.snapshot.clone",
    "app.create",
    "app.update",
    "app.delete",
    "app.redeploy",
    "app.stop",
    "app.start",
    "pool.snapshot.create",
    "zfs.snapshot.create",
    "pool.dataset.delete",
    "pool.snapshottask.create",
}
# Gevoelig lezen: de volledige app-configuratie (kan geheimen bevatten). Alleen met een schrijfprofiel; de Hub
# (alleen-lezen) mag dit nooit aanroepen — een poging komt in ``mutations``.
CONFIG_METHODS = {"app.config"}
JOB_METHODS = {
    "app.create",
    "app.update",
    "app.delete",
    "app.redeploy",
    "app.stop",
    "app.start",
    "app.upgrade",
    "app.rollback",
}
# Rechten per methode voor een schrijfprofiel (aanname uit de rolnamen; NIET GEVALIDEERD (echte NAS)).
APP_WRITE_METHODS = JOB_METHODS | CONFIG_METHODS
SNAPSHOT_WRITE_METHODS = {"pool.snapshot.create", "zfs.snapshot.create", "pool.snapshot.clone", "zfs.snapshot.clone"}
# Eigen logger van de websocket-server, vast op INFO (nooit DEBUG-frames met de sleutel).
WS_LOGGER = logging.getLogger("fakes.fake_truenas.websockets")
WS_LOGGER.setLevel(logging.INFO)


def mag_schrijven(profile: KeyProfile, method: str) -> bool:
    """Of dit profiel deze schrijf- of configuratiemethode mag aanroepen (rollen per methode, R-TECH-1)."""
    if not profile.write:
        return False
    roles = set(profile.roles)
    if "FULL_ADMIN" in roles:
        return True
    if method in APP_WRITE_METHODS:
        return "APPS_WRITE" in roles
    if method in SNAPSHOT_WRITE_METHODS:
        return "SNAPSHOT_WRITE" in roles
    return False


class FakeCallError(Exception):
    """Fout van een schrijfmethode in de fake (wordt een ``-32001`` met ``errname``)."""

    def __init__(self, errname: str, reason: str) -> None:
        super().__init__(reason)
        self.errname = errname
        self.reason = reason


def _ms(days_ago: float = 0, hours_ago: float = 0) -> dict[str, int]:
    t = dt.datetime.now(dt.UTC) - dt.timedelta(days=days_ago, hours=hours_ago)
    return {"$date": int(t.timestamp() * 1000)}


def _make_tls(tmp: Path) -> tuple[Path, Path, Path]:
    """Test-CA + servercertificaat voor 127.0.0.1/localhost. Geeft (ca.pem, cert.pem, key.pem)."""
    now = dt.datetime.now(dt.UTC)
    ca_key = ec.generate_private_key(ec.SECP256R1())
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Fake TrueNAS test-CA")])
    ca = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(days=1))
        .not_valid_after(now + dt.timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_cert_sign=True,
                crl_sign=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    key = ec.generate_private_key(ec.SECP256R1())
    cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "truenas.test")]))
        .issuer_name(ca_name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(days=1))
        .not_valid_after(now + dt.timedelta(days=30))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
            critical=False,
        )
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    ca_p, cert_p, key_p = tmp / "ca.pem", tmp / "cert.pem", tmp / "key.pem"
    ca_p.write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    cert_p.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_p.write_bytes(
        key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    )
    return ca_p, cert_p, key_p


def default_data() -> dict[str, Any]:
    """Testdata (geen echte NAS-waarden): pool ``testpool`` met MediaGuard, MSO, my_house en een gestopte app."""
    mnt = "/mnt/testpool"
    return {
        "system.info": {
            "version": "TrueNAS-25.04.2",
            "hostname": "fake-truenas",
            "model": "Fake CPU",
            "cores": 8,
            "physmem": 32 * 1024**3,
            "uptime_seconds": 3600,
            "timezone": "UTC",
        },
        "pool.query": [
            {
                "id": 1,
                "name": "testpool",
                "status": "ONLINE",
                "healthy": True,
                "warning": False,
                "size": 4_000_000_000_000,
                "allocated": 1_000_000_000_000,
                "free": 3_000_000_000_000,
                "scan": {"function": "SCRUB", "state": "FINISHED", "end_time": _ms(days_ago=3), "errors": 0},
            }
        ],
        "pool.dataset.query": [
            {
                "id": "testpool",
                "name": "testpool",
                "pool": "testpool",
                "type": "FILESYSTEM",
                "mountpoint": mnt,
                "used": {"parsed": 10},
                "available": {"parsed": 20},
                "encrypted": False,
                "children": [
                    {
                        "id": "testpool/apps",
                        "name": "testpool/apps",
                        "pool": "testpool",
                        "type": "FILESYSTEM",
                        "mountpoint": f"{mnt}/apps",
                        "children": [
                            {
                                "id": f"testpool/apps/{n}",
                                "name": f"testpool/apps/{n}",
                                "pool": "testpool",
                                "type": "FILESYSTEM",
                                "mountpoint": f"{mnt}/apps/{n}",
                                "children": [],
                            }
                            for n in ("mediaguard", "mso", "my_house", "jellyfin")
                        ],
                    },
                    {
                        "id": "testpool/photos",
                        "name": "testpool/photos",
                        "pool": "testpool",
                        "type": "FILESYSTEM",
                        "mountpoint": f"{mnt}/photos",
                        "children": [],
                    },
                    {
                        "id": "testpool/media",
                        "name": "testpool/media",
                        "pool": "testpool",
                        "type": "FILESYSTEM",
                        "mountpoint": f"{mnt}/media",
                        "children": [],
                    },
                ],
            }
        ],
        "app.query": [
            _app(
                "mediaguard",
                "RUNNING",
                "ghcr.io/lvos04/mediaguard:1.2.2",
                30101,
                8080,
                f"{mnt}/apps/mediaguard",
                "/data",
            ),
            _app(
                "media-source-optimizer",
                "RUNNING",
                "ghcr.io/lvos04/media-source-optimizer:1.6.0",
                38081,
                38081,
                f"{mnt}/apps/mso",
                "/appdata",
            ),
            _app("my-house", "RUNNING", "ghcr.io/lvos04/my_house:0.1.0", 30102, 8000, f"{mnt}/apps/my_house", "/data"),
            _app(
                "jellyfin",
                "STOPPED",
                "jellyfin/jellyfin:10.11.0",
                30013,
                8096,
                f"{mnt}/apps/jellyfin",
                "/config",
                catalog_app="jellyfin",
            ),
        ],
        "app.image.query": [
            _image("ghcr.io/lvos04/mediaguard:1.2.2"),
            _image("ghcr.io/lvos04/media-source-optimizer:1.6.0"),
            _image("ghcr.io/lvos04/my_house:0.1.0"),
            _image("jellyfin/jellyfin:10.11.0"),
        ],
        "disk.query": [
            {
                "name": "sda",
                "serial": "SERIAL0001",
                "model": "Fake HDD",
                "size": 4_000_000_000_000,
                "type": "HDD",
                "pool": "testpool",
            }
        ],
        "smart.test.results": [
            {
                "disk": "sda",
                "tests": [
                    {
                        "description": "Short offline",
                        "status": "SUCCESS",
                        "status_verbose": "Completed without error",
                        "lifetime": 100,
                    }
                ],
            }
        ],
        "app.gpu_choices": {
            "0000:03:00.0": {
                "vendor": "INTEL",
                "description": "Intel Corporation DG2 [Arc A310]",
                "pci_slot": "0000:03:00.0",
                "vendor_specific_config": {},
                "error": None,
            },
            "0000:00:02.0": {
                "vendor": "INTEL",
                "description": "Intel Corporation Raptor Lake-S GT1 [UHD Graphics 770]",
                "pci_slot": "0000:00:02.0",
                "vendor_specific_config": {},
                "error": None,
            },
        },
        "pool.snapshottask.query": [
            {
                "id": 1,
                "dataset": "testpool/apps",
                "recursive": True,
                "exclude": [],
                "lifetime_value": 2,
                "lifetime_unit": "WEEK",
                "enabled": True,
                "naming_schema": "auto-%Y-%m-%d_%H-%M",
                "schedule": {"minute": "0", "hour": "*", "dom": "*", "month": "*", "dow": "*"},
                "state": {"state": "FINISHED", "datetime": _ms(hours_ago=1)},
            }
        ],
        "snapshots": {
            "testpool/apps": [
                {
                    "name": "testpool/apps@auto-latest",
                    "dataset": "testpool/apps",
                    "createtxg": "1000",
                    "properties": {"creation": {"parsed": _ms(hours_ago=1)}},
                }
            ]
        },
        "cloudsync.query": [
            {
                "id": 1,
                "description": "Foto's naar OneDrive",
                "path": f"{mnt}/photos",
                "direction": "PUSH",
                "transfer_mode": "COPY",
                "enabled": True,
                "encryption": False,
                "credentials": {
                    "id": 1,
                    "name": "OneDrive",
                    "provider": {
                        "type": "ONEDRIVE",
                        "client_secret": "GEHEIM-NIET-OPSLAAN",
                        "token": '{"access_token":"GEHEIM"}',
                    },
                },
                "job": {
                    "state": "SUCCESS",
                    "time_started": _ms(hours_ago=5),
                    "time_finished": _ms(hours_ago=4),
                    "error": None,
                },
            },
        ],
        "replication.query": [],
        "alert.list": [
            {
                "uuid": "a1",
                "level": "WARNING",
                "klass": "ScrubPaused",
                "formatted": "Testmelding",
                "datetime": _ms(hours_ago=2),
                "dismissed": False,
            }
        ],
        # Event source reporting.realtime (vorm volgens middleware TS-25.10.8, realtime_reporting/*).
        "reporting.realtime": {
            "cpu": {
                "cpu": {"usage": 23.5, "temp": 51.0},
                **{f"cpu{i}": {"usage": 20.0 + i, "temp": 50.0 + i} for i in range(4)},
            },
            "memory": {
                "arc_size": 6 * 1024**3,
                "arc_free_memory": 1024**3,
                "arc_available_memory": 2 * 1024**3,
                "physical_memory_total": 32 * 1024**3,
                "physical_memory_available": 24 * 1024**3,
            },
            "disks": {"busy": 3.5, "read_bytes": 4096.0, "write_bytes": 8192.0, "read_ops": 1.0, "write_ops": 2.0},
            "interfaces": {
                "eth0": {
                    "link_state": "LINK_STATE_UP",
                    "speed": 1000,
                    "received_bytes_rate": 1250.0,
                    "sent_bytes_rate": 250.0,
                },
                "eth1": {"link_state": "LINK_STATE_DOWN", "speed": 0, "received_bytes_rate": 0, "sent_bytes_rate": 0},
            },
            "zfs": {"demand_data_hit_percentage": 97},
            "pools": {},
        },
        "network.general.summary": {
            "ips": {"eth0": {"IPV4": ["127.0.0.1/8"]}},
            "default_routes": [],
            "nameservers": [],
        },
    }


def _image(ref: str) -> dict[str, Any]:
    """Image zoals ``app.image.query`` hem teruggeeft; de digest is een vaste testwaarde (geen echte image)."""
    repo = ref.rsplit(":", 1)[0]
    digest = "sha256:" + hashlib.sha256(ref.encode()).hexdigest()
    return {
        "id": "sha256:" + hashlib.sha256(("id" + ref).encode()).hexdigest(),
        "repo_tags": [ref],
        "repo_digests": [f"{repo}@{digest}"],
        "size": 1000,
        "dangling": False,
        "update_available": False,
        "created": "2026-11-01T00:00:00",
        "author": "",
        "comment": "",
    }


def _app(
    name: str,
    state: str,
    image: str,
    host_port: int,
    container_port: int,
    src: str,
    dst: str,
    *,
    catalog_app: str = "ix-app",
    custom_app: bool = False,
) -> dict[str, Any]:
    """Standaard Custom App = catalogus-app ``ix-app`` (``custom_app: false``); ``custom_app: true`` is een
    compose-app (Install via YAML) — zo leest de Hub het in de broncode van TrueNAS (NIET GEVALIDEERD op een NAS).
    Gestopt: lege ``active_workloads`` (zie de kop van dit bestand)."""
    app: dict[str, Any] = {
        "name": name,
        "id": name,
        "state": state,
        "version": "1.4.8" if catalog_app == "ix-app" else "1.0.0",
        "human_version": image.rsplit(":", 1)[-1],
        "custom_app": custom_app,
        "upgrade_available": False,
        "latest_version": None,
        "image_updates_available": False,
        "metadata": {"app_version": image.rsplit(":", 1)[-1], "name": catalog_app, "train": "stable"},
        "portals": {"Web UI": f"http://0.0.0.0:{host_port}/"},
        "config": {"env": {"SECRET_TOKEN": "mag-nooit-opgehaald-worden"}},
    }
    werklast = {
        "containers": 1 if state == "RUNNING" else 0,
        "used_ports": [
            {
                "container_port": container_port,
                "protocol": "tcp",
                "host_ports": [{"host_port": host_port, "host_ip": "0.0.0.0"}],
            }
        ],
        "container_details": [{"service_name": name, "image": image, "state": state.lower()}],
        "volumes": [{"source": src, "destination": dst, "mode": "rw", "type": "bind"}],
        "images": [image],
    }
    if state == "STOPPED":
        app["active_workloads"], app["_werklast"] = lege_werklast(), werklast
    else:
        app["active_workloads"] = werklast
    return app


def lege_werklast() -> dict[str, Any]:
    """``active_workloads`` van een gestopte app zoals TrueNAS hem geeft (``get_default_workload_values``)."""
    return {"containers": 0, "used_ports": [], "container_details": [], "volumes": [], "images": [], "networks": []}


@dataclass
class KeyProfile:
    roles: list[str] = field(default_factory=lambda: ["READONLY_ADMIN"])
    deny: set[str] = field(default_factory=set)
    write: bool = False  # True: schrijfmethoden toegestaan (de schrijfsleutel van de executor)


class FakeTrueNAS:
    def __init__(
        self,
        *,
        version: str = "25.04.2",
        keys: dict[str, KeyProfile] | None = None,
        data: dict[str, Any] | None = None,
        noise: bool = True,
    ) -> None:
        self.version = version
        self.keys = keys if keys is not None else {"readonly-test-key-0123456789": KeyProfile()}
        self.data = data or default_data()
        self.noise = noise
        self.delays: dict[str, float] = {}
        self.subscriptions: list[str] = []
        self.unsubscribed: list[str] = []
        self.realtime_silent = False  # True: abonnement aangenomen maar nooit gegevens (time-out-test)
        self.calls: list[tuple[str, Any]] = []
        self.mutations: list[str] = []
        self.paths: list[str] = []
        # Schrijven (executor): testknoppen en wat er is ontvangen.
        self.fail: dict[str, str] = {}
        self.silent_noop: set[str] = set()
        self.digest_override: dict[str, str] = {}
        self.hidden: set[str] = set()
        self.job_polls = 1
        self.jobs: dict[int, dict[str, Any]] = {}
        self.created: list[dict[str, Any]] = []
        self.updated: list[tuple[str, dict[str, Any]]] = []
        self.deleted: list[tuple[str, dict[str, Any]]] = []
        self.logins = 0
        self._tmp = tempfile.TemporaryDirectory(prefix="fake-truenas-")
        self.ca_file, self._cert, self._key = _make_tls(Path(self._tmp.name))
        self.port = 0
        self._loop: asyncio.AbstractEventLoop | None = None
        self._server: Server | None = None
        self._thread: threading.Thread | None = None

    # ---------------------------------------------------------------- versie en methoden
    @property
    def methods(self) -> set[str]:
        major_minor = tuple(int(x) for x in self.version.split(".")[:2])
        m = set(READ_METHODS) | set(WRITE_METHODS) | set(CONFIG_METHODS)
        old = "zfs" if major_minor >= (25, 4) else "pool"
        for verb in ("query", "create", "clone"):
            m.discard(f"{old}.snapshot.{verb}")
        return m - self.hidden

    @property
    def url(self) -> str:
        return f"wss://127.0.0.1:{self.port}/api/current"

    # ---------------------------------------------------------------- lifecycle
    def start(self) -> FakeTrueNAS:
        ready = threading.Event()

        def run() -> None:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._start_server())
            ready.set()
            self._loop.run_forever()

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()
        if not ready.wait(10):
            raise RuntimeError("fake TrueNAS start niet")
        return self

    async def _start_server(self) -> None:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(str(self._cert), str(self._key))
        self._server = await serve(
            self._handler,
            "127.0.0.1",
            self.port,
            ssl=ctx,
            process_request=self._process_request,
            logger=WS_LOGGER,
        )
        self.port = self._server.sockets[0].getsockname()[1] if self._server.sockets else self.port

    def offline(self) -> None:
        """NAS 'uit': de server stopt (verbinden faalt met unreachable)."""
        assert self._loop is not None
        fut = asyncio.run_coroutine_threadsafe(self._close_server(), self._loop)
        fut.result(10)

    def online(self) -> None:
        assert self._loop is not None
        asyncio.run_coroutine_threadsafe(self._start_server(), self._loop).result(10)

    async def _close_server(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    def stop(self) -> None:
        if self._loop is not None:
            asyncio.run_coroutine_threadsafe(self._close_server(), self._loop).result(10)
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread is not None:
            self._thread.join(5)
        self._tmp.cleanup()

    # ---------------------------------------------------------------- protocol
    def _process_request(self, connection: ServerConnection, request: Request) -> Response | None:
        self.paths.append(request.path)
        if request.path != "/api/current":
            return connection.respond(HTTPStatus.NOT_FOUND, "Not Found\n")
        return None

    async def _handler(self, ws: ServerConnection) -> None:
        profile: KeyProfile | None = None
        try:
            async for raw in ws:
                msg = json.loads(raw)
                method, params, mid = msg.get("method"), msg.get("params") or [], msg.get("id")
                self.calls.append((method, params if method != "auth.login_with_api_key" else ["***"]))
                if self.noise:
                    await ws.send(
                        json.dumps(
                            {
                                "jsonrpc": "2.0",
                                "method": "collection_update",
                                "params": {"msg": "changed", "collection": "app.query"},
                            }
                        )
                    )
                if method in self.delays:
                    await asyncio.sleep(self.delays[method])
                if method in WRITE_METHODS or (method not in READ_METHODS and method in self.methods):
                    self.mutations.append(method)
                if method == "auth.login_with_api_key":
                    self.logins += 1
                    profile = self.keys.get(str(params[0]) if params else "")
                    await self._reply(ws, mid, result=profile is not None)
                    continue
                if profile is None:
                    await self._reply(
                        ws,
                        mid,
                        error={
                            "code": -32001,
                            "message": "Method call error",
                            "data": {"error": 13, "errname": "ENOTAUTHENTICATED", "reason": "Not authenticated"},
                        },
                    )
                    continue
                if method not in self.methods:
                    await self._reply(ws, mid, error={"code": -32601, "message": "Method not found"})
                    continue
                if method == "core.subscribe":
                    event = str(params[0]) if params else ""
                    if event != "reporting.realtime" or "reporting.realtime" in profile.deny:
                        await self._reply(
                            ws,
                            mid,
                            error={
                                "code": -32001,
                                "message": "Method call error",
                                "data": {"error": 13, "errname": "EACCES", "reason": "Not authorized"},
                            },
                        )
                        continue
                    ident = f"sub-{len(self.subscriptions) + 1}"
                    self.subscriptions.append(ident)
                    await self._reply(ws, mid, result=ident)
                    if self.realtime_silent:
                        continue
                    await asyncio.sleep(0.05)
                    await ws.send(
                        json.dumps(
                            {
                                "jsonrpc": "2.0",
                                "method": "collection_update",
                                "params": {
                                    "msg": "added",
                                    "collection": "reporting.realtime",
                                    "fields": self.data["reporting.realtime"],
                                },
                            }
                        )
                    )
                    continue
                if method == "core.unsubscribe":
                    self.unsubscribed.append(str(params[0]) if params else "")
                    await self._reply(ws, mid, result=None)
                    continue
                if method in CONFIG_METHODS and not profile.write:
                    self.mutations.append("app.config(geheimen)")
                if method in profile.deny or (
                    method in WRITE_METHODS | CONFIG_METHODS and not mag_schrijven(profile, method)
                ):
                    await self._reply(
                        ws,
                        mid,
                        error={
                            "code": -32001,
                            "message": "Method call error",
                            "data": {"error": 13, "errname": "EACCES", "reason": "Not authorized"},
                        },
                    )
                    continue
                if method in WRITE_METHODS | CONFIG_METHODS:
                    try:
                        await self._reply(ws, mid, result=self._write(method, params))
                    except FakeCallError as exc:
                        await self._reply(
                            ws,
                            mid,
                            error={
                                "code": -32001,
                                "message": "Method call error",
                                "data": {"error": 22, "errname": exc.errname, "reason": exc.reason},
                            },
                        )
                    continue
                await self._reply(ws, mid, result=self._result(method, params, profile))
        except ConnectionClosed:
            return

    async def _reply(self, ws: ServerConnection, mid: Any, *, result: Any = None, error: Any = None) -> None:
        body: dict[str, Any] = {"jsonrpc": "2.0", "id": mid}
        if error is not None:
            body["error"] = error
        else:
            body["result"] = result
        await ws.send(json.dumps(body))

    def _result(self, method: str, params: list[Any], profile: KeyProfile) -> Any:
        if method == "system.version":
            return f"TrueNAS-{self.version}"
        if method == "system.info":
            return {**self.data["system.info"], "version": f"TrueNAS-{self.version}"}
        if method == "core.get_methods":
            return {m: {"description": None} for m in sorted(self.methods)}
        if method == "auth.me":
            return {"pw_name": "hub-lezer", "privilege": {"roles": {"$set": list(profile.roles)}, "web_shell": False}}
        if method == "core.get_jobs":
            return self._jobs(params)
        if (
            method == "app.query"
            and len(params) > 1
            and isinstance(params[1], dict)
            and (params[1].get("extra") or {}).get("retrieve_config")
        ):
            self.mutations.append("app.query(retrieve_config)")  # de Hub mag de app-config (geheimen) nooit ophalen
        if method in ("pool.snapshot.query", "zfs.snapshot.query"):
            ds = None
            if params and isinstance(params[0], list) and params[0] and isinstance(params[0][0], list):
                ds = params[0][0][2]
            return list(self.data["snapshots"].get(ds, []))
        if method == "device.get_info":
            return list(self.data["app.gpu_choices"].values())
        if method == "interface.query":
            return []
        value = self.data.get(method)
        if method == "app.query" and isinstance(value, list):
            return [{k: v for k, v in a.items() if k != "config" and not k.startswith("_")} for a in value]
        return value

    # ---------------------------------------------------------------- schrijven (executor, fase P2)
    def _jobs(self, params: list[Any]) -> list[dict[str, Any]]:
        wanted = None
        if params and isinstance(params[0], list) and params[0] and isinstance(params[0][0], list):
            wanted = params[0][0][2]
        out = []
        for job in self.jobs.values():
            if wanted is not None and job["id"] != wanted:
                continue
            if job["polls_left"] > 0:
                job["polls_left"] -= 1
                out.append({"id": job["id"], "method": job["method"], "state": "RUNNING", "error": None})
            else:
                out.append({k: v for k, v in job.items() if k != "polls_left"})
        return out

    def app(self, name: str) -> dict[str, Any] | None:
        return next((a for a in self.data["app.query"] if a["name"] == name), None)

    def datasets(self) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}

        def walk(nodes: list[dict[str, Any]]) -> None:
            for n in nodes:
                out[n["id"]] = n
                walk(n.get("children") or [])

        walk(self.data["pool.dataset.query"])
        return out

    def add_dataset(self, name: str) -> None:
        parent = self.datasets()[name.rsplit("/", 1)[0]]
        parent["children"].append(
            {
                "id": name,
                "name": name,
                "pool": name.split("/", 1)[0],
                "type": "FILESYSTEM",
                "mountpoint": f"/mnt/{name}",
                "children": [],
            }
        )

    def _set_image(self, app: dict[str, Any], image: dict[str, Any]) -> None:
        """Image van een Custom App bijwerken. De tag mag ``<versie>@sha256:<digest>`` zijn; de digest in
        ``app.image.query`` is die uit de tag, tenzij ``digest_override`` (registry levert iets anders)."""
        repo, tag = str(image["repository"]), str(image["tag"])
        ref = f"{repo}:{tag}"
        version, _sep, pinned = tag.partition("@")
        digest = self.digest_override.get(repo) or pinned or "sha256:" + hashlib.sha256(ref.encode()).hexdigest()
        wl = app.get("_werklast") or app["active_workloads"]  # gestopt: de bewaarde werklast
        wl["images"] = [ref]
        for c in wl["container_details"]:
            c["image"] = ref
        app["human_version"] = version
        app["metadata"]["app_version"] = version
        entry = _image(f"{repo}:{version}")
        entry["repo_digests"] = [f"{repo}@{digest}"]
        self.data["app.image.query"] = [
            i for i in self.data["app.image.query"] if f"{repo}:{version}" not in i["repo_tags"]
        ] + [entry]

    def _set_state(self, app: dict[str, Any], state: str) -> None:
        """Staat wijzigen zoals TrueNAS: gestopt = lege ``active_workloads`` (de werklast blijft bewaard voor het
        starten)."""
        app["state"] = state
        if state == "STOPPED":
            if "_werklast" not in app:
                app["_werklast"] = app["active_workloads"]
            app["active_workloads"] = lege_werklast()
            return
        if "_werklast" in app:
            app["active_workloads"] = app.pop("_werklast")
        app["active_workloads"]["containers"] = 1 if state == "RUNNING" else 0
        for c in app["active_workloads"]["container_details"]:
            c["state"] = state.lower()

    def _write(self, method: str, params: list[Any]) -> Any:
        if method == "app.config":
            app = self.app(str(params[0]) if params else "")
            if app is None:
                raise FakeCallError("ENOENT", "App does not exist")
            return json.loads(json.dumps(app.get("config") or {}))
        if method in JOB_METHODS:
            job_id = len(self.jobs) + 1
            job: dict[str, Any] = {
                "id": job_id,
                "method": method,
                "state": "SUCCESS",
                "error": None,
                "result": None,
                "polls_left": self.job_polls,
            }
            if method in self.fail:
                job.update(state="FAILED", error=self.fail[method])
            elif method not in self.silent_noop:
                try:
                    self._apply(method, params)
                except FakeCallError as exc:
                    job.update(state="FAILED", error=f"[{exc.errname}] {exc.reason}")
            self.jobs[job_id] = job
            return job_id
        if method in self.fail:
            raise FakeCallError("EFAULT", self.fail[method])
        if method in self.silent_noop:
            return True
        return self._apply(method, params)

    def _apply(self, method: str, params: list[Any]) -> Any:
        if method == "app.create":
            data = params[0] if params and isinstance(params[0], dict) else {}
            self.created.append(json.loads(json.dumps(data)))
            name = str(data.get("app_name") or "")
            if self.app(name) is not None:
                raise FakeCallError("EEXIST", "Application with this name already exists")
            if "custom_compose_config" in data or "custom_compose_config_string" in data or data.get("custom_app"):
                self.mutations.append("app.create(custom_compose)")  # nooit: Install via YAML
            values = data.get("values") or {}
            ports = values.get("ports") or [{}]
            storage = values.get("storage") or [{}]
            app = _app(
                name,
                "RUNNING",
                "onbekend/onbekend:0",
                int(ports[0].get("port_number") or 0),
                int(ports[0].get("container_port") or 0),
                str((storage[0].get("host_path_config") or {}).get("path") or ""),
                str(storage[0].get("mount_path") or ""),
                catalog_app=str(data.get("catalog_app") or "ix-app"),
            )
            app["version"] = str(data.get("version") or app["version"])
            app["metadata"]["train"] = str(data.get("train") or "stable")
            app["config"] = json.loads(json.dumps(values))
            if isinstance(values.get("image"), dict):
                self._set_image(app, values["image"])
            self.data["app.query"].append(app)
            return None
        if method in ("pool.snapshot.create", "zfs.snapshot.create"):
            data = params[0] if params and isinstance(params[0], dict) else {}
            ds, name = str(data.get("dataset") or ""), str(data.get("name") or "")
            if ds not in self.datasets():
                raise FakeCallError("ENOENT", "Dataset does not exist")
            snaps = self.data["snapshots"].setdefault(ds, [])
            full = f"{ds}@{name}"
            if any(x["name"] == full for x in snaps):
                raise FakeCallError("EEXIST", "Snapshot already exists")
            snap = {
                "name": full,
                "dataset": ds,
                "createtxg": str(1000 + len(snaps) + 1),
                "properties": {"creation": {"parsed": _ms()}},
            }
            snaps.append(snap)
            return snap
        if method in ("pool.snapshot.clone", "zfs.snapshot.clone"):
            data = params[0] if params and isinstance(params[0], dict) else {}
            snap, dst = str(data.get("snapshot") or ""), str(data.get("dataset_dst") or "")
            ds = snap.split("@", 1)[0]
            if not any(x["name"] == snap for x in self.data["snapshots"].get(ds, [])):
                raise FakeCallError("ENOENT", "Snapshot does not exist")
            if dst.rsplit("/", 1)[0] not in self.datasets():
                raise FakeCallError("ENOENT", "Parent dataset does not exist")
            if dst in self.datasets():
                raise FakeCallError("EEXIST", "Dataset already exists")
            self.add_dataset(dst)
            return True
        if method in ("pool.dataset.delete", "pool.snapshottask.create"):
            raise FakeCallError("EPERM", "Niet ondersteund in de fake")
        app = self.app(str(params[0]) if params else "")
        if app is None:
            raise FakeCallError("ENOENT", "App does not exist")
        options = params[1] if len(params) > 1 and isinstance(params[1], dict) else {}
        if method == "app.update":
            self.updated.append((app["name"], json.loads(json.dumps(options))))
            if "custom_compose_config" in options or "custom_compose_config_string" in options:
                self.mutations.append("app.update(custom_compose)")
            values = options.get("values") or {}
            app["config"] = {**(app.get("config") or {}), **json.loads(json.dumps(values))}
            if isinstance(values.get("image"), dict):
                self._set_image(app, values["image"])
        elif method == "app.delete":
            self.deleted.append((app["name"], dict(options)))
            self.data["app.query"] = [a for a in self.data["app.query"] if a["name"] != app["name"]]
        elif method in ("app.redeploy", "app.start"):
            self._set_state(app, "RUNNING")
        elif method == "app.stop":
            self._set_state(app, "STOPPED")
        elif method in ("app.upgrade", "app.rollback"):
            app["version"] = str(options.get("app_version") or app["version"])
        return None
