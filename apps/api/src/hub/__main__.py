"""Opdrachtregel van de Hub: ``python -m hub <commando>`` (in de image ook ``hub <commando>``)."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import uuid
from pathlib import Path

from hub.config import get_settings
from hub.logfilter import install_log_filter, uvicorn_log_config


def _logging(level: str) -> None:
    logging.getLogger("alembic").setLevel(logging.WARNING)
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )
    install_log_filter()  # KLEIN-33: vangnet tegen de DETAIL-regel van PostgreSQL


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
        log_config=uvicorn_log_config(),
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
        if ok and args.id_bestand:
            try:
                with args.id_bestand.open("x", encoding="ascii") as receipt:
                    receipt.write(f"{row.id}\n")
            except OSError:
                print("De identiteit van de nieuwe export kon niet worden vastgelegd.", file=sys.stderr)
                ok = False
    engine.dispose()
    return 0 if ok else 1


def cmd_backup_controle(args: argparse.Namespace) -> int:
    from hub.backup.selfbackup import verify_pre_upgrade
    from hub.db import make_engine, make_sessionmaker

    s = get_settings()
    engine = make_engine(s.database_url)
    with make_sessionmaker(engine)() as db:
        ver = verify_pre_upgrade(db, s, args.id)
    engine.dispose()
    print(json.dumps({"ok": ver.ok, "reason_code": ver.reason_code, "melding": ver.message}))
    return 0 if ver.ok else 1


def cmd_herstel_lokale_beheerder(args: argparse.Namespace) -> int:
    import re
    import warnings
    from getpass import GetPassWarning, getpass

    from sqlalchemy import select
    from sqlalchemy.exc import SQLAlchemyError

    from hub import audit, breakglass
    from hub.db import make_engine, make_sessionmaker
    from hub.errors import HubError
    from hub.models import User
    from hub.routers.auth import USERNAME_PATTERN, _check_password_policy
    from hub.security import Role, hash_password
    from hub.vault import Vault, VaultError

    settings = get_settings()
    naam = args.gebruikersnaam
    if not re.fullmatch(USERNAME_PATTERN, naam):
        print("Kies een geldige lokale gebruikersnaam.", file=sys.stderr)
        return 1
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", GetPassWarning)
            wachtwoord = getpass("Nieuw wachtwoord: ")
            bevestiging = getpass("Herhaal het nieuwe wachtwoord: ")
    except (EOFError, GetPassWarning, KeyboardInterrupt):
        print("Herstel vereist een interactieve terminal met afgeschermde invoer.", file=sys.stderr)
        return 1
    if wachtwoord != bevestiging or len(wachtwoord) > 256:
        print("De ingevoerde wachtwoorden komen niet overeen of zijn te lang.", file=sys.stderr)
        return 1
    try:
        _check_password_policy(wachtwoord, settings.password_min_length, naam)
    except HubError as exc:
        print(exc.message, file=sys.stderr)
        return 1
    try:
        vault = Vault.from_file(settings.secrets_dir / "vault.key")
    except (OSError, ValueError, VaultError):
        print("De Hub-kluissleutel kan niet worden gelezen.", file=sys.stderr)
        return 1

    engine = make_engine(settings.database_url)
    try:
        with make_sessionmaker(engine).begin() as db:
            breakglass.lock_local_recovery(db)
            nood = breakglass.account(db, lock=True)
            _, reden = breakglass.working_status(db, vault, nood)
            herstelredenen = (breakglass.TOTP_UNAVAILABLE, breakglass.VERIFIER_UNUSABLE)
            if reden not in herstelredenen or breakglass.has_local_admin(db):
                print(
                    "Herstel vereist een onbruikbare wachtwoordhash of onleesbare TOTP van het noodaccount "
                    "en geen bruikbare gewone lokale beheerder.",
                    file=sys.stderr,
                )
                return 1
            if db.scalar(select(User.id).where(User.username == naam)) is not None:
                print("Deze gebruikersnaam bestaat al.", file=sys.stderr)
                return 1
            gebruiker = User(username=naam, role=Role.admin.value, password_hash=hash_password(wachtwoord))
            db.add(gebruiker)
            db.flush()
            audit.record(
                db,
                actor_type="system",
                actor_id="hub-console",
                action="auth.lokale_beheerder_hersteld",
                target_type="user",
                target_id=str(gebruiker.id),
                details={"reden": reden},
            )
    except SQLAlchemyError:
        print("Het lokale beheerdersaccount kon niet worden opgeslagen.", file=sys.stderr)
        return 1
    finally:
        engine.dispose()
    print("Lokaal beheerdersaccount aangemaakt. Meld je aan en herstel het noodaccount.")
    return 0


def cmd_export_openapi(args: argparse.Namespace) -> int:
    from hub.openapi_export import export

    return export(Path(args.out), check=args.check)


def cmd_export_runbooks(args: argparse.Namespace) -> int:
    from hub.runbooks.export import export

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
    b.add_argument("--id-bestand", type=Path, help="schrijf de UUID van de geverifieerde export in een nieuw bestand")
    controle = sub.add_parser("backup-controle", help="controleer een specifieke pre-upgrade-export vóór de migratie")
    controle.add_argument("--id", type=uuid.UUID, required=True, help="export-UUID uit deze upgradebeurt")
    h = sub.add_parser(
        "herstel-lokale-beheerder", help="lokaal beheer herstellen bij storing van noodwachtwoord of TOTP"
    )
    h.add_argument("gebruikersnaam")
    e = sub.add_parser("export-openapi", help="OpenAPI exporteren of op drift controleren")
    e.add_argument("--out", default="docs/openapi/hub-api.openapi.json")
    e.add_argument("--check", action="store_true")
    rb = sub.add_parser("export-runbooks", help="runbooks als Markdown exporteren of op drift controleren")
    rb.add_argument("--out", default="docs/RUNBOOKS.md")
    rb.add_argument("--check", action="store_true")
    args = p.parse_args(argv)
    _logging(get_settings().log_level)
    handlers = {
        "init": cmd_init,
        "api": cmd_api,
        "worker": cmd_worker,
        "ai-runner": cmd_ai_runner,
        "migrate": cmd_migrate,
        "backup-now": cmd_backup_now,
        "backup-controle": cmd_backup_controle,
        "herstel-lokale-beheerder": cmd_herstel_lokale_beheerder,
        "export-openapi": cmd_export_openapi,
        "export-runbooks": cmd_export_runbooks,
    }
    return handlers[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
