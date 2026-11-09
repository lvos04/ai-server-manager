"""Opdrachtregel van de Hub: ``python -m hub <commando>`` (in de image ook ``hub <commando>``)."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from hub.config import get_settings


def _logging(level: str) -> None:
    logging.getLogger("alembic").setLevel(logging.WARNING)
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )


def cmd_init(args: argparse.Namespace) -> int:
    from hub.firststart import FirstStartError, ensure_secrets, log_lines

    s = get_settings()
    try:
        result = ensure_secrets(s.secrets_dir, setup_code_ttl_seconds=s.setup_code_ttl_seconds, new_setup_code=True)
    except FirstStartError as exc:
        print(f"[hub] FOUT: {exc}", flush=True)
        return 78
    for line in log_lines(result):
        print(f"[hub] {line}", flush=True)
    return 0


def cmd_api(args: argparse.Namespace) -> int:
    import uvicorn

    s = get_settings()
    uvicorn.run(
        "hub.app:create_app",
        factory=True,
        host=args.host or s.host,
        port=args.port or s.port,
        proxy_headers=True,
        forwarded_allow_ips=s.forwarded_allow_ips,
        log_level=s.log_level,
        access_log=False,
        server_header=False,
    )
    return 0


def cmd_worker(args: argparse.Namespace) -> int:
    from hub import worker

    s = get_settings()
    if args.once:
        from hub.db import make_engine, make_sessionmaker
        from hub.vault import Vault

        engine = make_engine(s.database_url)
        done = worker.run_once(make_sessionmaker(engine), s, Vault.from_file(s.secrets_dir / "vault.key"))
        print(json.dumps(done, indent=2, default=str))
        engine.dispose()
        return 0
    return worker.main(s)


def cmd_ai_runner(args: argparse.Namespace) -> int:
    from hub import airunner

    s = get_settings()
    return airunner.main(s.data_dir, s.ai_enabled, once=args.once)


def cmd_migrate(args: argparse.Namespace) -> int:
    from hub import migrations

    s = get_settings()
    if args.check:
        pending = migrations.pending_migrations(s.database_url)
        print("migraties wachten" if pending else "database op head")
        return 1 if pending else 0
    if args.down:
        migrations.downgrade(s.database_url, args.down)
    else:
        migrations.upgrade(s.database_url, args.revision)
    return 0


def cmd_backup_now(args: argparse.Namespace) -> int:
    from hub.backup.selfbackup import run_self_backup, to_dict
    from hub.db import make_engine, make_sessionmaker

    s = get_settings()
    engine = make_engine(s.database_url)
    with make_sessionmaker(engine)() as db:
        row = run_self_backup(db, s, trigger=args.trigger)
        print(json.dumps(to_dict(row), indent=2))
        ok = row.status == "geslaagd"
    engine.dispose()
    return 0 if ok else 1


def cmd_export_openapi(args: argparse.Namespace) -> int:
    from hub.openapi_export import export

    return export(Path(args.out), check=args.check)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="hub", description="AI Server Manager — Hub")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="first-start-init: geheimen aanmaken (nooit overschrijven) + setupcode in de log")
    a = sub.add_parser("api", help="HTTP-API starten")
    a.add_argument("--host")
    a.add_argument("--port", type=int)
    w = sub.add_parser("worker", help="achtergrondtaken")
    w.add_argument("--once", action="store_true")
    r = sub.add_parser("ai-runner", help="AI-runner (stub; aparte gebruiker zonder geheimen)")
    r.add_argument("--once", action="store_true")
    m = sub.add_parser("migrate", help="databasemigraties")
    m.add_argument("--revision", default="head")
    m.add_argument("--down")
    m.add_argument("--check", action="store_true")
    b = sub.add_parser("backup-now", help="eigen database-export maken en verifiëren")
    b.add_argument("--trigger", default="manual", choices=["manual", "pre-upgrade", "schedule"])
    e = sub.add_parser("export-openapi", help="OpenAPI exporteren of op drift controleren")
    e.add_argument("--out", default="docs/openapi/hub-api.openapi.json")
    e.add_argument("--check", action="store_true")
    args = p.parse_args(argv)
    _logging(get_settings().log_level)
    handlers = {
        "init": cmd_init,
        "api": cmd_api,
        "worker": cmd_worker,
        "ai-runner": cmd_ai_runner,
        "migrate": cmd_migrate,
        "backup-now": cmd_backup_now,
        "export-openapi": cmd_export_openapi,
    }
    return handlers[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
