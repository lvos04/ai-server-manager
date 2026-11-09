"""Teststack voor de web-E2E (Playwright): de echte Hub-API + worker tegen de fake TrueNAS-simulator.

Alleen voor ontwikkeling/CI (Sim-getest, geen echte NAS). Start:
- een eigen tijdelijke database ``asm_web_e2e_<id>`` op ``HUB_TEST_ADMIN_URL`` (wordt bij stoppen verwijderd);
- first-start-init met een nieuwe setupcode — die staat, net als in de image, alleen in de log (stdout) en, zodat de
  test hem kan "aflezen", in ``<state>/setupcode.txt``;
- de fake TrueNAS (wss, zelfondertekend certificaat, alleen-lezen-key);
- de Hub-API (uvicorn) op 127.0.0.1:``HUB_E2E_API_PORT`` en een worker-lus (jobs: inventaris vernieuwen);
- een kleine besturingspoort (127.0.0.1:``HUB_E2E_CONTROL_PORT``) om de fake NAS uit/aan te zetten.
Er worden geen successen gesimuleerd: alle antwoorden komen van de echte API; alleen de NAS is een simulator.

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
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # tests/ → fakes

ADMIN_URL = os.environ.get("HUB_TEST_ADMIN_URL", "postgresql://postgres@127.0.0.1:5432/postgres")
API_PORT = int(os.environ.get("HUB_E2E_API_PORT", "39401"))
CONTROL_PORT = int(os.environ.get("HUB_E2E_CONTROL_PORT", "39402"))
STATE_DIR = Path(os.environ.get("HUB_E2E_STATE_DIR", str(HERE / ".web-e2e-state")))
READONLY_KEY = "readonly-test-key-0123456789"
WRITE_KEY = "write-test-key-0123456789abc"
STOP = threading.Event()


def log(msg: str) -> None:
    print(f"[web-e2e-stack] {msg}", flush=True)


class _Control(BaseHTTPRequestHandler):
    nas: Any = None

    def _reply(self, body: dict[str, Any], status: int = 200) -> None:
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:
        if self.path == "/nas/offline":
            self.nas.offline()
        elif self.path == "/nas/online":
            self.nas.online()
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

    nas = FakeTrueNAS(keys={READONLY_KEY: KeyProfile(), WRITE_KEY: KeyProfile(roles=["FULL_ADMIN"])}).start()
    log(f"fake TrueNAS op wss://127.0.0.1:{nas.port}/api/current (simulator)")
    _Control.nas = nas
    control = ThreadingHTTPServer(("127.0.0.1", CONTROL_PORT), _Control)
    threading.Thread(target=control.serve_forever, daemon=True).start()
    return nas, control


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
    try:
        _write_state(
            {
                "control_url": f"http://127.0.0.1:{CONTROL_PORT}",
                "fake_nas_port": nas.port,
                "readonly_key": READONLY_KEY,
                "write_key": WRITE_KEY,
            }
        )
        _wait_for_stop()
    finally:
        control.shutdown()
        nas.stop()
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
        )
        res = ensure_secrets(settings.secrets_dir, new_setup_code=True)
        assert res.setup_code
        log(f"SETUPCODE (eenmalig, voor het eerste beheerdersaccount): {res.setup_code}")

        nas, control = _start_nas()
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
            vault = app.state.vault()
            while not STOP.is_set():
                try:
                    worker.run_once(app.state.sessionmaker, settings, vault, schedule=False)
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
        if control is not None:
            control.shutdown()
        if nas is not None:
            nas.stop()
        with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
            conn.execute(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE)')
        tmp.cleanup()
        log("gestopt; testdatabase verwijderd")
    return 0


if __name__ == "__main__":
    sys.exit(main_nas_only() if "--alleen-nas" in sys.argv else main())
