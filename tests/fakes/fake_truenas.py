"""In-repo fake TrueNAS: JSON-RPC 2.0 over WebSocket (wss) op ``/api/current``.

Alleen voor tests (simulator). Gedrag dat de echte TrueNAS-middleware nabootst:
- ``auth.login_with_api_key`` → ``true``/``false``; zonder aanmelding geeft elke methode ``ENOTAUTHENTICATED``;
- onbekende methode → ``-32601``; geweigerde methode → ``-32001`` met ``errname: EACCES``;
- versieprofielen: ``25.04`` (``pool.snapshot.query``) en ``24.10`` (``zfs.snapshot.query``);
- notificaties (``collection_update``) tussen antwoorden door;
- TLS met een eigen test-CA (zelfondertekend vanuit het perspectief van de Hub).
Elke aanroep wordt gelogd; aanroepen van niet-leesmethoden komen in ``mutations`` (tests eisen dat die leeg blijft).
"""

from __future__ import annotations

import asyncio
import datetime as dt
import hashlib
import ipaddress
import json
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
}
WRITE_METHODS = {
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
    compose-app (Install via YAML) — zo leest de Hub het in de broncode van TrueNAS (NIET GEVALIDEERD op een NAS)."""
    return {
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
        "active_workloads": {
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
        },
    }


@dataclass
class KeyProfile:
    roles: list[str] = field(default_factory=lambda: ["READONLY_ADMIN"])
    deny: set[str] = field(default_factory=set)


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
        m = set(READ_METHODS) | set(WRITE_METHODS)
        if major_minor >= (25, 4):
            m.discard("zfs.snapshot.query")
            m.discard("zfs.snapshot.create")
        else:
            m.discard("pool.snapshot.query")
            m.discard("pool.snapshot.create")
        return m

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
            self._handler, "127.0.0.1", self.port, ssl=ctx, process_request=self._process_request
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
                if method in profile.deny or method in WRITE_METHODS:
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
            return [{k: v for k, v in a.items() if k != "config"} for a in value]
        return value
