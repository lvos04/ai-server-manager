"""AI Server Manager (Hub) — procesbewaker van de alles-in-één image (PID 1 van de container).

Eén container met alles: PostgreSQL 16 (alleen unix-socket, geen netwerkpoort, geen wachtwoord), first-start-init,
migraties, API, worker, AI-runner (stub) en de web-UI (Next.js op poort 30400, met doorgang naar de API die dan alleen
op 127.0.0.1:8400 luistert). Daardoor installeert
de Hub als gewone TrueNAS **Custom App** met één image, één poort (30400) en één map (/appdata). Geen YAML.

Regels:
- Start als root alleen om de eigen submappen van /appdata aan 568:568 te geven; daarna draait alles als 568.
  De AI-runner draait als **aparte gebruiker 569** zonder toegang tot /appdata/secrets of de databasesocket.
  Start de container niet als root, dan draait alles als die gebruiker en start de AI-runner niet (AI staat in deze
  versie toch uit).
- Duidelijke Nederlandse fout + pauze bij een niet-beschrijfbare /appdata, i.p.v. een snelle crashloop.
- Een oude postmaster.pid na een harde stop wordt verwijderd (de container is de enige gebruiker).
- Kinderen die stoppen worden met backoff herstart; SIGTERM stopt web → worker → api → database netjes.
- Als PID 1 ruimt de bewaker ook verweesde processen (zombies) op; er draait dus geen root-init meer.
- Vóór openstaande migraties: back-up ('pre-upgrade', echte pg_dump + verificatie); mislukt die, dan start de Hub
  wel door (de oude database blijft bij een mislukte migratie onaangeroerd).
"""

from __future__ import annotations

import ctypes
import grp
import os
import pwd
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

UID = int(os.environ.get("HUB_UID", "568"))
GID = int(os.environ.get("HUB_GID", "568"))
AI_UID = int(os.environ.get("HUB_AI_UID", "569"))
AI_GID = int(os.environ.get("HUB_AI_GID", "569"))
DATA = Path(os.environ.get("HUB_DATA_DIR", "/appdata"))
PGDATA = DATA / "postgres"
SOCKET_DIR = Path("/tmp/asm-pg")  # noqa: S108 — 0700 van uid 568: de AI-runner (569) kan er niet bij
PORT = os.environ.get("HUB_PORT", "30400")
API_PORT = os.environ.get("HUB_INTERNAL_API_PORT", "8400")
WEB_SERVER = Path(os.environ.get("HUB_WEB_SERVER", "/opt/hub-web/server/hub-server.mjs"))  # aanwezig → web op PORT, API intern
DB_URL = f"postgresql+psycopg://hub@/hub?host={SOCKET_DIR}"
MANAGED = ("postgres", "secrets", "backups", "logs")
STOP = threading.Event()


def log(msg: str) -> None:
    print(f"[hub] {msg}", flush=True)


def fail(msg: str, code: int = 78) -> None:
    log("FOUT: " + msg)
    time.sleep(30)  # melding zichtbaar houden in TrueNAS → Apps → Logs i.p.v. een snelle crashloop
    sys.exit(code)


PR_SET_NO_NEW_PRIVS = 38


def set_no_new_privs() -> bool:
    """Contract §10 'no-new-privileges': het standaard Custom App-formulier kan die vlag niet zetten, dus doet de image
    het zelf na de gebruikerswissel. Erft over op alle kinderen; daarna wint geen proces nog rechten (ook niet via
    setuid-bestanden). Stil (ook bruikbaar als preexec_fn); de bewaker controleert en meldt het zelf."""
    try:
        return int(ctypes.CDLL(None, use_errno=True).prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)) == 0
    except (OSError, AttributeError):
        return False


def demote_to(uid: int, gid: int) -> None:
    if os.getuid() == 0:
        os.setgroups([])
        os.setgid(gid)
        os.setuid(uid)
    set_no_new_privs()


def demote() -> None:
    demote_to(UID, GID)


def demote_ai() -> None:
    demote_to(AI_UID, AI_GID)
    # Na het wisselen van gebruiker: SIGTERM als de bewaker stopt (de bewaker mag 569 zelf geen signaal sturen).
    try:
        ctypes.CDLL(None, use_errno=True).prctl(1, int(signal.SIGTERM))  # PR_SET_PDEATHSIG
    except (OSError, AttributeError):
        pass


def reap_orphans(known: set[int]) -> None:
    """PID 1: verweesde kindprocessen opruimen zonder de exitstatus van eigen kinderen weg te nemen."""
    if os.getpid() != 1:
        return
    while True:
        try:
            info = os.waitid(os.P_ALL, 0, os.WEXITED | os.WNOHANG | os.WNOWAIT)
        except ChildProcessError:
            return
        if info is None or info.si_pid in known:
            return
        try:
            os.waitpid(info.si_pid, os.WNOHANG)
        except ChildProcessError:
            return


def prepare_dirs() -> None:
    if not DATA.exists():
        fail(f"{DATA} bestaat niet. Koppel een dataset (Host Path) aan {DATA} in de app-instellingen.")
    root = os.getuid() == 0
    if root:
        for path in [DATA, *[DATA / n for n in MANAGED if (DATA / n).exists()]]:
            st = path.stat()
            if (st.st_uid, st.st_gid) != (UID, GID):
                log(f"eigenaar van {path} wordt {UID}:{GID} (alleen eigen mappen van de Hub)")
                if path == DATA:
                    os.chown(path, UID, GID)
                    continue
                for dirpath, dirnames, filenames in os.walk(path):
                    for name in [dirpath, *[os.path.join(dirpath, n) for n in dirnames + filenames]]:
                        try:
                            os.lchown(name, UID, GID)
                        except OSError:
                            pass
    for sub in (PGDATA, DATA / "secrets", DATA / "backups", DATA / "logs"):
        try:
            sub.mkdir(parents=True, exist_ok=True)
            if root:
                os.chown(sub, UID, GID)
        except PermissionError:
            fail(f"geen schrijfrechten op {sub}. Laat 'Custom User' uit (de Hub regelt de rechten) of geef gebruiker "
                 f"{UID} (apps) schrijfrechten op de dataset.")
    try:
        os.chmod(PGDATA, 0o700)
        os.chmod(DATA / "secrets", 0o700)
    except PermissionError:
        fail(f"{PGDATA} of secrets is niet van gebruiker {UID}; start de app als root of maak {UID} eigenaar.")
    SOCKET_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(SOCKET_DIR, 0o700)
    if root:
        os.chown(SOCKET_DIR, UID, GID)
    probe = subprocess.run(
        [sys.executable, "-c", f"open('{DATA}/.hub-write-test','w').close();import os;os.remove('{DATA}/.hub-write-test')"],
        preexec_fn=demote, capture_output=True, check=False,
    )
    if probe.returncode != 0:
        fail(f"gebruiker {UID} kan niet schrijven in {DATA}. Pas de rechten van de dataset aan (Apps-gebruiker).")


def env_for(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    env.update({"HOME": "/tmp", "HUB_DATA_DIR": str(DATA), "HUB_DATABASE_URL": DB_URL, "PYTHONUNBUFFERED": "1"})  # noqa: S108
    env.update(extra or {})
    return env


def run_once(name: str, cmd: list[str], extra_env: dict[str, str] | None = None) -> int:
    log(f"{name}: {' '.join(cmd)}")
    return subprocess.run(cmd, env=env_for(extra_env), preexec_fn=demote, check=False).returncode


class Child:
    def __init__(self, name: str, cmd: list[str], extra_env: dict[str, str] | None = None,
                 stop_signal: int = signal.SIGTERM, ai: bool = False) -> None:
        self.name, self.cmd, self.extra_env, self.stop_signal, self.ai = name, cmd, extra_env, stop_signal, ai
        self.proc: subprocess.Popen[bytes] | None = None

    def start(self) -> None:
        log(f"start {self.name}")
        if self.ai:
            env = {"HOME": "/tmp", "PATH": os.environ.get("PATH", ""), "HUB_DATA_DIR": str(DATA), "PYTHONUNBUFFERED": "1",  # noqa: S108
                   "HUB_AI_ENABLED": os.environ.get("HUB_AI_ENABLED", "false")}
            self.proc = subprocess.Popen(self.cmd, env=env, preexec_fn=demote_ai, cwd="/tmp", start_new_session=True)  # noqa: S108
        else:
            self.proc = subprocess.Popen(self.cmd, env=env_for(self.extra_env), preexec_fn=demote, start_new_session=True)

    def alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def stop(self, timeout: float = 25) -> None:
        if not self.alive():
            return
        assert self.proc is not None
        try:
            self.proc.send_signal(self.stop_signal)
            self.proc.wait(timeout)
        except PermissionError:
            log(f"{self.name}: draait als andere gebruiker; stopt zodra de bewaker stopt (parent-death-signaal)")
        except subprocess.TimeoutExpired:
            log(f"{self.name} reageert niet; geforceerd stoppen")
            self.proc.kill()
            self.proc.wait(5)


def init_database() -> None:
    if (PGDATA / "PG_VERSION").exists():
        major = (PGDATA / "PG_VERSION").read_text().strip()
        if major != "16":
            fail(f"database in {PGDATA} is PostgreSQL {major}; deze image gebruikt 16.")
        pid = PGDATA / "postmaster.pid"
        if pid.exists():
            log("oude postmaster.pid van een onderbroken stop verwijderd")
            pid.unlink()
        return
    log("eerste start: database aanmaken")
    rc = run_once("initdb", ["initdb", "-D", str(PGDATA), "-U", "hub", "--auth-local=trust", "--auth-host=reject",
                             "--encoding=UTF8", "--locale=C.UTF-8", "--no-instructions"])
    if rc != 0:
        fail("initdb mislukt (zie log hierboven)")


def postgres_child() -> Child:
    return Child("database", ["postgres", "-D", str(PGDATA), "-c", "listen_addresses=", "-c",
                              f"unix_socket_directories={SOCKET_DIR}", "-c", "unix_socket_permissions=0700",
                              "-c", "max_connections=40", "-c", "shared_buffers=64MB", "-c", "jit=off",
                              "-c", "logging_collector=off", "-c", "log_min_messages=warning"],
                 stop_signal=signal.SIGINT)


def wait_for_db(pg: Child, timeout: float = 90) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not pg.alive():
            fail("database stopte tijdens het opstarten (zie log hierboven)")
        rc = subprocess.run(["pg_isready", "-h", str(SOCKET_DIR), "-U", "hub", "-d", "postgres", "-q"],
                            env=env_for(), preexec_fn=demote, check=False).returncode
        if rc == 0:
            break
        time.sleep(1)
    else:
        fail("database niet klaar binnen 90 s")
    exists = subprocess.run(["psql", "-h", str(SOCKET_DIR), "-U", "hub", "-d", "postgres", "-tAc",
                             "SELECT 1 FROM pg_database WHERE datname='hub'"],
                            env=env_for(), preexec_fn=demote, capture_output=True, text=True, check=False)
    if exists.stdout.strip() != "1" and run_once(
        "createdb", ["psql", "-h", str(SOCKET_DIR), "-U", "hub", "-d", "postgres", "-qc", "CREATE DATABASE hub"]
    ) != 0:
        fail("database 'hub' aanmaken mislukt")


def has_schema() -> bool:
    out = subprocess.run(["psql", "-h", str(SOCKET_DIR), "-U", "hub", "-d", "hub", "-tAc",
                          "SELECT to_regclass('public.alembic_version') IS NOT NULL"],
                         env=env_for(), preexec_fn=demote, capture_output=True, text=True, check=False)
    return out.stdout.strip() == "t"


def main() -> None:
    log(f"AI Server Manager — Hub (alles-in-één) · data {DATA} · poort {PORT}")
    started_as_root = os.getuid() == 0
    prepare_dirs()
    py = sys.executable
    if run_once("first-start-init", [py, "-m", "hub", "init"]) != 0:
        fail("first-start-init mislukt (zie de melding hierboven); geheimen worden nooit overschreven")

    ai_runner: Child | None = None
    if started_as_root:
        ai_runner = Child("ai-runner", [py, "-m", "hub", "ai-runner"], ai=True)
        ai_runner.start()
    else:
        log("AI-runner niet gestart: de container draait niet als root, dus een aparte gebruiker is niet mogelijk")

    demote()  # vanaf hier draait niets meer als root
    if not set_no_new_privs():
        log("WAARSCHUWING: no-new-privileges kon niet worden gezet (prctl); de processen draaien wel als 568")
    init_database()
    pg = postgres_child()
    pg.start()
    wait_for_db(pg)
    if has_schema() and run_once("migratiecontrole", [py, "-m", "hub", "migrate", "--check"]) != 0:
        if shutil.disk_usage(DATA).free < 200 * 1024 * 1024 or \
                run_once("back-up vóór upgrade", [py, "-m", "hub", "backup-now", "--trigger", "pre-upgrade"]) != 0:
            log("back-up vóór upgrade niet gelukt (zie log); de Hub start door, de oude database blijft bij een "
                "mislukte migratie onaangeroerd")
    if run_once("migraties", [py, "-m", "hub", "migrate"]) != 0:
        pg.stop()
        fail("databasemigratie mislukt; de vorige versie van de database is ongewijzigd.")

    web = WEB_SERVER.exists()
    api_host, api_port = ("127.0.0.1", API_PORT) if web else ("0.0.0.0", PORT)  # noqa: S104
    children = [Child("api", [py, "-m", "hub", "api", "--host", api_host, "--port", api_port]),
                Child("worker", [py, "-m", "hub", "worker"])]
    if web:
        children.append(Child("web", ["node", str(WEB_SERVER)],
                              {"PORT": PORT, "HOSTNAME": "0.0.0.0", "HUB_API_URL": f"http://127.0.0.1:{API_PORT}",  # noqa: S104
                               "NODE_ENV": "production", "NEXT_TELEMETRY_DISABLED": "1"}))
    for c in children:
        c.start()

    def shutdown(signum: int, _frame: object) -> None:
        log(f"signaal {signum}: netjes stoppen")
        STOP.set()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    backoff: dict[str, float] = {}
    warned_ai = False
    while not STOP.is_set():
        if not pg.alive():
            log("database gestopt; opnieuw starten")
            for c in children:
                c.stop()
            init_database()
            pg.start()
            wait_for_db(pg)
            for c in children:
                c.start()
        for c in children:
            if not c.alive() and not STOP.is_set():
                wait = min(60.0, backoff.get(c.name, 1.0))
                log(f"{c.name} gestopt (code {c.proc.returncode if c.proc else '?'}); herstart over {wait:.0f} s")
                STOP.wait(wait)
                backoff[c.name] = wait * 2
                if not STOP.is_set():
                    c.start()
            elif c.alive():
                backoff[c.name] = max(1.0, backoff.get(c.name, 1.0) * 0.9)
        reap_orphans({c.proc.pid for c in [pg, *children, *([ai_runner] if ai_runner else [])] if c.proc})
        if ai_runner is not None and not ai_runner.alive() and not warned_ai:
            log("AI-runner gestopt; hij start weer bij de volgende herstart van de app (AI staat uit)")
            warned_ai = True
        STOP.wait(2)

    for c in reversed(children):
        c.stop()
    pg.stop(60)
    log("gestopt")


if __name__ == "__main__":
    for uid, gid in ((UID, GID), (AI_UID, AI_GID)):
        try:
            pwd.getpwuid(uid)
            grp.getgrgid(gid)
        except KeyError:
            fail(f"gebruiker {uid}:{gid} bestaat niet in de image")
    if shutil.which("postgres") is None:
        fail("postgres ontbreekt in de image")
    main()
