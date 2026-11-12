"""Teststack voor de web-E2E (Playwright): de echte Hub-API + worker tegen de fake TrueNAS-simulator.

Alleen voor ontwikkeling/CI (Sim-getest, geen echte NAS). Start:
- een eigen tijdelijke database ``asm_web_e2e_<id>`` op ``HUB_TEST_ADMIN_URL`` (wordt bij stoppen verwijderd);
- first-start-init met een nieuwe setupcode — die staat, net als in de image, alleen in de log (stdout) en, zodat de
  test hem kan "aflezen", in ``<state>/setupcode.txt``;
- de fake TrueNAS (wss, zelfondertekend certificaat, alleen-lezen-key);
- de Hub-API (uvicorn) op 127.0.0.1:``HUB_E2E_API_PORT`` en een worker-lus (jobs: inventaris vernieuwen);
- een kleine besturingspoort (127.0.0.1:``HUB_E2E_CONTROL_PORT``) om de fake NAS uit/aan te zetten, een app aan de
  fake NAS toe te voegen en een simulator-dienst te laten koppelen (koppelcode) en events te laten sturen;
- fakes voor Uptime Kuma, Beszel, Gotify en een OIDC-issuer (Authentik-vorm) op loopback, met hun adressen en
  testsleutels in ``state.json`` (alleen testgeheimen);
- de periodieke worker-taken (meten, bronnen, gezondheid, alerts, incidenten, meldingen) met korte intervallen;
- de echte executor (``executor.app``) op 127.0.0.1:``HUB_E2E_EXECUTOR_PORT`` met een eigen lege datamap en de fake
  TrueNAS als zijn TrueNAS, zodat de web-E2E het koppelformulier, het sleutelformulier en het beheer van de
  statuspagina echt in een browser verstuurt (contract 1.3 §3.7 punt 6 en §3.9; review N-01, R-VEILIG-5).
Er worden geen successen gesimuleerd: alle antwoorden komen van de echte API; alleen NAS, bronnen, Gotify, de OIDC-
issuer en de simulator-dienst zijn simulators.

Met ``--alleen-nas`` start alleen de fake TrueNAS + besturingspoort (voor de web-E2E tegen de alles-in-één image, die
zijn eigen API, database en setupcode heeft).
"""

from __future__ import annotations

import json
import os
import signal
import sys
import tempfile
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # tests/ → fakes

ADMIN_URL = os.environ.get("HUB_TEST_ADMIN_URL", "postgresql://postgres@127.0.0.1:5432/postgres")
API_PORT = int(os.environ.get("HUB_E2E_API_PORT", "39401"))
CONTROL_PORT = int(os.environ.get("HUB_E2E_CONTROL_PORT", "39402"))
EXECUTOR_PORT = int(os.environ.get("HUB_E2E_EXECUTOR_PORT", "39403"))
STATE_DIR = Path(os.environ.get("HUB_E2E_STATE_DIR", str(HERE / ".web-e2e-state")))
READONLY_KEY = "readonly-test-key-0123456789"
WRITE_KEY = "write-test-key-0123456789abc"
# Schrijfsleutels van de executor in de nep-TrueNAS (FULL_ADMIN, schrijven toegestaan): het sleutelformulier en het
# beheer van de executorpagina in de browser (contract 1.3 §3.7 punt 6 via §3.9; R-VEILIG-5). Alleen testwaarden.
EXECUTOR_SLEUTEL = "executor-sleutel-aaaabbbbcccc"
EXECUTOR_SLEUTEL_NIEUW = "executor-sleutel-ddddeeeeffff"
KUMA_KEY = "uk1_testkey_abcdef"
GOTIFY_TOKEN = "AppTokenHub123"
BESZEL_USER = "hub-lezer"
BESZEL_PW = "Lees-Alleen-Wachtwoord-1"
STOP = threading.Event()
# Basis van de Hub voor de besturingsroutes (simulator-dienst): de eigen API of, tegen de image, de web-UI-poort.
API_URL = os.environ.get("HUB_E2E_API_URL", f"http://127.0.0.1:{API_PORT}")


def _api(method: str, path: str, body: dict[str, Any] | None = None, token: str | None = None) -> tuple[int, Any]:
    """Aanroep van de echte Hub-API als simulator-dienst (alleen voor de testbesturing)."""
    import http.client
    from urllib.parse import urlsplit

    u = urlsplit(API_URL)
    conn = http.client.HTTPConnection(u.hostname or "127.0.0.1", u.port or 80, timeout=10)
    headers = {"Content-Type": "application/json", "Idempotency-Key": str(uuid.uuid4())}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    conn.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers)
    res = conn.getresponse()
    raw = res.read()
    conn.close()
    try:
        return res.status, json.loads(raw or b"null")
    except ValueError:
        return res.status, raw.decode(errors="replace")


def _service_jwk() -> dict[str, str]:
    import base64

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    from hub.keys import jwk_thumbprint

    raw = (
        Ed25519PrivateKey.generate()
        .public_key()
        .public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    )
    jwk = {"kty": "OKP", "crv": "Ed25519", "x": base64.urlsafe_b64encode(raw).rstrip(b"=").decode()}
    jwk["kid"] = jwk_thumbprint(jwk)
    return jwk


def log(msg: str) -> None:
    print(f"[web-e2e-stack] {msg}", flush=True)


class _Control(BaseHTTPRequestHandler):
    nas: Any = None
    tokens: ClassVar[dict[str, str]] = {}  # app_id → service-token van de simulator-dienst

    def _reply(self, body: dict[str, Any], status: int = 200) -> None:
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def _body(self) -> dict[str, Any]:
        n = int(self.headers.get("content-length") or 0)
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def do_POST(self) -> None:
        if self.path == "/nas/offline":
            self.nas.offline()
        elif self.path == "/nas/online":
            self.nas.online()
        elif self.path == "/nas/app":
            # Extra app op de fake NAS (bv. een eigen dienst met een hostpoort waar niets luistert).
            from fakes.fake_truenas import _app

            b = self._body()
            name = str(b["naam"])
            self.nas.data["app.query"] = [a for a in self.nas.data["app.query"] if a.get("name") != name]
            app = _app(
                name,
                b.get("staat", "RUNNING"),
                str(b["image"]),
                int(b["poort"]),
                int(b.get("container_poort", 30420)),
                f"/mnt/testpool/apps/{name}",
                "/appdata",
            )
            self.nas.data["app.query"].append(app)
        elif self.path == "/dienst/koppel":
            # Simulator-dienst koppelt met een koppelcode via de echte API (contract 1.2 §3.3).
            b = self._body()
            status, res = _api(
                "POST",
                "/api/v1/services/enroll",
                {
                    "app_id": b["app_id"],
                    "pairing_code": b["code"],
                    "version": "0.1.0",
                    "base_url": None,
                    "public_key_jwk": _service_jwk(),
                },
            )
            if status == 200 and isinstance(res, dict):
                self.tokens[str(b["app_id"])] = str(res["service_token"])
            self._reply(
                {
                    "status": status,
                    "antwoord": {k: v for k, v in (res or {}).items() if k != "service_token"}
                    if isinstance(res, dict)
                    else res,
                },
                200 if status == 200 else 409,
            )
            return
        elif self.path == "/dienst/events":
            # Events van de simulator-dienst naar de events-inbox (contract §7), bv. 100 identieke crashes.
            b = self._body()
            token = self.tokens.get(str(b["app_id"]))
            if token is None:
                self._reply({"fout": "dienst niet gekoppeld"}, 409)
                return
            ok = 0
            for _ in range(int(b.get("aantal", 1))):
                eid = str(uuid.uuid4())
                ev = {
                    "schema_version": "1.0",
                    "event_id": eid,
                    "source_app": b["app_id"],
                    "source_event_id": eid,
                    # Contract 1.3 §7: app.* alleen als app.health.changed over de eigen app van de bron.
                    "event_type": b.get("event_type", "app.health.changed"),
                    "entity": {"type": "app", "id": b.get("entity", b["app_id"])},
                    "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "trace_id": str(uuid.uuid4()),
                    "correlation_id": None,
                    "actor": {"type": "system", "id": b["app_id"]},
                    "classification": "internal",
                    "payload": b.get("payload", {"status": "down", "naam": "Node-RED", "reden": "exit_code_137"}),
                }
                status, _res = _api("POST", "/api/v1/events/inbox", ev, token)
                ok += status in (200, 202)
            self._reply({"verstuurd": ok})
            return
        else:
            self._reply({"fout": "onbekend pad"}, 404)
            return
        self._reply({"ok": True, "mutaties_op_nas": list(self.nas.mutations)})

    def do_GET(self) -> None:
        self._reply({"mutaties_op_nas": list(self.nas.mutations), "aanroepen": len(self.nas.calls)})

    def log_message(self, *_args: Any) -> None:
        return


def _start_nas() -> Any:
    from fakes.fake_truenas import FakeTrueNAS, KeyProfile

    nas = FakeTrueNAS(
        keys={
            READONLY_KEY: KeyProfile(),
            WRITE_KEY: KeyProfile(roles=["FULL_ADMIN"]),
            EXECUTOR_SLEUTEL: KeyProfile(roles=["FULL_ADMIN"], write=True),
            EXECUTOR_SLEUTEL_NIEUW: KeyProfile(roles=["FULL_ADMIN"], write=True),
        }
    ).start()
    log(f"fake TrueNAS op wss://127.0.0.1:{nas.port}/api/current (simulator)")
    _Control.nas = nas
    control = ThreadingHTTPServer(("127.0.0.1", CONTROL_PORT), _Control)
    threading.Thread(target=control.serve_forever, daemon=True).start()
    return nas, control


def _start_fakes() -> dict[str, Any]:
    """Simulators voor monitoring, meldingen en SSO (alleen loopback, alleen testsleutels)."""
    from fakes.fake_gotify import FakeGotify
    from fakes.fake_monitoring import FakeBeszel, FakeUptimeKuma
    from fakes.fake_oidc import FakeOidc

    kuma = FakeUptimeKuma(api_keys={KUMA_KEY}).start()
    kuma.add(1, "MediaGuard", url="http://127.0.0.1:30101/api/v1/health", ping=18.0)
    kuma.add(2, "Jellyfin", url="http://127.0.0.1:30013/health", status=0)
    kuma.add(3, "Externe site", url="https://example.org/", ping=40.0)
    beszel = FakeBeszel(users={BESZEL_USER: BESZEL_PW}).start()
    gotify = FakeGotify(tokens={GOTIFY_TOKEN}).start()
    oidc = FakeOidc().start()
    log(f"fakes: Uptime Kuma {kuma.url}, Beszel {beszel.url}, Gotify {gotify.url}, OIDC {oidc.issuer}")
    return {"kuma": kuma, "beszel": beszel, "gotify": gotify, "oidc": oidc}


def _fake_state(f: dict[str, Any]) -> dict[str, Any]:
    return {
        "kuma_url": f["kuma"].url,
        "kuma_key": KUMA_KEY,
        "beszel_url": f["beszel"].url,
        "beszel_user": BESZEL_USER,
        "beszel_pw": BESZEL_PW,
        "gotify_url": f["gotify"].url,
        "gotify_token": GOTIFY_TOKEN,
        "oidc_issuer": f["oidc"].issuer,
        "oidc_client_id": f["oidc"].client_id,
        "oidc_client_secret": f["oidc"].client_secret,
    }


def _start_executor(data_dir: Path, nas_port: int) -> Any:
    """De echte executor-app (statuspagina, koppelen, schrijfsleutel en beheer) met een lege datamap; loopback-Hub
    alleen met de testvlag. Zijn TrueNAS is de nep-TrueNAS (adres via de instelling, zoals
    ``EXECUTOR_TRUENAS_HOST``)."""
    import uvicorn
    from executor.app import create_app as create_executor
    from executor.config import Settings as ExecutorSettings
    from executor.firststart import ensure_secrets as ensure_executor_secrets

    ex_settings = ExecutorSettings(
        data_dir=data_dir,
        allow_loopback_hub=True,
        truenas_host="127.0.0.1",
        truenas_port=nas_port,
        truenas_timeout_seconds=5,
    )
    ensure_executor_secrets(ex_settings.secrets_dir)
    server = uvicorn.Server(
        uvicorn.Config(
            create_executor(ex_settings),
            host="127.0.0.1",
            port=EXECUTOR_PORT,
            log_level="warning",
            access_log=False,
            server_header=False,
        )
    )
    threading.Thread(target=server.run, daemon=True).start()
    deadline = time.monotonic() + 15
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError("executor start niet")
        time.sleep(0.05)
    log(f"executor op http://127.0.0.1:{EXECUTOR_PORT} (lege datamap, nog nooit gekoppeld)")
    return server


def _write_state(extra: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    (STATE_DIR / "state.json").write_text(json.dumps(extra, indent=2))


def _wait_for_stop() -> None:
    def stop(_signum: int, _frame: object) -> None:
        STOP.set()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    while not STOP.is_set():
        time.sleep(0.5)


def main_nas_only() -> int:
    nas, control = _start_nas()
    fakes = _start_fakes()
    try:
        _write_state(
            {
                "control_url": f"http://127.0.0.1:{CONTROL_PORT}",
                "fake_nas_port": nas.port,
                "readonly_key": READONLY_KEY,
                "write_key": WRITE_KEY,
                **_fake_state(fakes),
            }
        )
        _wait_for_stop()
    finally:
        control.shutdown()
        nas.stop()
        for f in fakes.values():
            f.stop()
        log("gestopt")
    return 0


def main() -> int:
    import psycopg
    import uvicorn

    from hub import migrations, worker
    from hub.app import create_app
    from hub.config import Settings
    from hub.firststart import ensure_secrets

    db_name = f"asm_web_e2e_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(ADMIN_URL, autocommit=True, connect_timeout=5) as conn:
        # Restanten van afgebroken runs opruimen: alleen eigen testdatabases zonder open verbindingen.
        stale = conn.execute(
            "SELECT d.datname FROM pg_database d WHERE d.datname LIKE 'asm\\_web\\_e2e\\_%' "
            "AND NOT EXISTS (SELECT 1 FROM pg_stat_activity a WHERE a.datname = d.datname)"
        ).fetchall()
        for (name,) in stale:
            conn.execute(f'DROP DATABASE IF EXISTS "{name}"')
            log(f"oude testdatabase {name} opgeruimd")
        conn.execute(f'CREATE DATABASE "{db_name}"')
    base = ADMIN_URL.rsplit("/", 1)[0]
    db_url = f"{base}/{db_name}".replace("postgresql://", "postgresql+psycopg://", 1)
    tmp = tempfile.TemporaryDirectory(prefix="asm-web-e2e-")
    nas: Any = None
    control: Any = None
    executor: Any = None
    try:
        migrations.upgrade(db_url)
        settings = Settings(
            data_dir=Path(tmp.name) / "appdata",
            database_url=db_url,
            inventory_ttl_seconds=int(os.environ.get("HUB_E2E_INVENTORY_TTL", "900")),
            inventory_interval_seconds=3600,
            truenas_connect_timeout=3,
            truenas_read_timeout=5,
            login_max_failures=20,
            cookie_secure="false",
            # Alleen in de teststack: bronnen, Gotify en de OIDC-issuer draaien als simulator op loopback.
            outbound_allow_loopback=True,
            nas_metrics_interval_seconds=10,
            monitoring_interval_seconds=10,
            health_record_interval_seconds=10,
            alert_interval_seconds=5,
            incident_interval_seconds=5,
        )
        res = ensure_secrets(settings.secrets_dir, new_setup_code=True)
        assert res.setup_code
        log(f"SETUPCODE (eenmalig, voor het eerste beheerdersaccount): {res.setup_code}")

        nas, control = _start_nas()
        fakes = _start_fakes()
        executor = _start_executor(Path(tmp.name) / "executor", nas.port)
        (STATE_DIR / "setupcode.txt").parent.mkdir(parents=True, exist_ok=True)
        (STATE_DIR / "setupcode.txt").write_text(res.setup_code)
        _write_state(
            {
                "api_url": f"http://127.0.0.1:{API_PORT}",
                "control_url": f"http://127.0.0.1:{CONTROL_PORT}",
                "fake_nas_port": nas.port,
                "readonly_key": READONLY_KEY,
                "write_key": WRITE_KEY,
                "database": db_name,
                "executor_url": f"http://127.0.0.1:{EXECUTOR_PORT}",
                "executor_sleutel": EXECUTOR_SLEUTEL,
                "executor_sleutel_nieuw": EXECUTOR_SLEUTEL_NIEUW,
                **_fake_state(fakes),
            }
        )

        app = create_app(settings)
        server = uvicorn.Server(
            uvicorn.Config(
                app,
                host="127.0.0.1",
                port=API_PORT,
                log_level="warning",
                proxy_headers=True,
                forwarded_allow_ips="127.0.0.1",
                access_log=False,
            )
        )
        api_thread = threading.Thread(target=server.run, daemon=True)
        api_thread.start()

        def worker_loop() -> None:
            from hub.monitoring import periodic

            vault = app.state.vault()
            while not STOP.is_set():
                try:
                    worker.run_once(app.state.sessionmaker, settings, vault, schedule=False)
                    # Periodieke taken (meten, bronnen, alerts, incidenten, meldingen) volgens hun interval.
                    periodic.run_due(app.state.sessionmaker, settings, vault, app.state.keyring())
                except Exception as exc:  # de lus mag de teststack niet stoppen
                    log(f"worker-ronde mislukt: {type(exc).__name__}: {exc}")
                STOP.wait(1)

        threading.Thread(target=worker_loop, daemon=True).start()

        log(f"Hub-API op http://127.0.0.1:{API_PORT} (database {db_name})")
        _wait_for_stop()
        server.should_exit = True
        api_thread.join(10)
        app.state.engine.dispose()
    finally:
        if executor is not None:
            executor.should_exit = True
        if control is not None:
            control.shutdown()
        if nas is not None:
            nas.stop()
        for f in (locals().get("fakes") or {}).values():
            f.stop()
        with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
            conn.execute(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE)')
        tmp.cleanup()
        log("gestopt; testdatabase verwijderd")
    return 0


if __name__ == "__main__":
    sys.exit(main_nas_only() if "--alleen-nas" in sys.argv else main())
