"""Terugval met twee lokale Hub-images. Geef de image van schema 0014, de upgrade en retentie 1 of 7."""

import argparse
import json
import secrets
import shutil
import subprocess
import sys
import time
import uuid
from contextlib import ExitStack, contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request, urlopen


def stap_in_image(stap, argument):
    # In beide images gebruiken we de instellingen en PostgreSQL van die versie.
    sys.path.insert(0, "/usr/local/lib/hub")
    import supervisor
    from sqlalchemy import create_engine, text

    from hub.backup import selfbackup
    from hub.config import Settings
    from hub.db import make_sessionmaker
    from hub.firststart import ensure_secrets

    settings = Settings(database_url=supervisor.DB_URL)
    engine = create_engine(settings.database_url)
    if stap == "vullen":
        with make_sessionmaker(engine)() as db:
            for i in range(settings.self_backup_keep):
                toekomst = datetime.now(UTC) + timedelta(minutes=2, seconds=i)
                with patch.object(selfbackup, "utcnow", return_value=toekomst):
                    rij = selfbackup.run_self_backup(db, settings, trigger="manual")
                    assert rij.status == "geslaagd" and rij.deleted_at is None, rij.reason_code
    elif stap in {"setup/admin", "auth/login"}:
        with engine.connect() as db:
            assert db.scalar(text("SELECT version_num FROM alembic_version")) == argument
        data = {"username": "terugvalproef", "password": sys.stdin.read()}
        if stap == "setup/admin":
            data["setup_code"] = ensure_secrets(settings.secrets_dir, new_setup_code=True).setup_code
        request = Request(
            f"http://localhost:{supervisor.PORT}/api/v1/{stap}",
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=8) as response:  # noqa: S310 — eigen Hub zonder extern netwerk
            assert json.load(response)["user"]["username"] == "terugvalproef"
    elif stap == "archief":
        with engine.connect() as db:
            archief = db.execute(
                text(
                    "SELECT file_name, sha256 FROM self_backup WHERE trigger='pre-upgrade' "
                    "AND status='geslaagd' AND deleted_at IS NULL"
                )
            ).one_or_none()
        if archief is None:
            return
        naam, digest = archief
        map_backups = settings.backups_dir
        assert len(list(map_backups.glob("*.dump"))) == settings.self_backup_keep + 1
        assert selfbackup.sha256_file(map_backups / naam) == digest
        assert (map_backups / (naam + ".sha256")).read_text().split() == [digest, naam]
        assert json.loads((map_backups / (naam + ".json")).read_text())["schema_revisie"] == "0014"
        print(naam)
    elif stap == "herstel":
        shutil.copytree("/bron/secrets", settings.secrets_dir)
        supervisor.prepare_dirs()
        supervisor.demote()
        supervisor.init_database()
        pg = supervisor.postgres_child()
        pg.start()
        try:
            supervisor.wait_for_db(pg)
            subprocess.run(
                [
                    "pg_restore",
                    "--exit-on-error",
                    "--single-transaction",
                    "--no-owner",
                    "-d",
                    settings.libpq_url,
                    Path("/bron/backups") / argument,
                ],
                check=True,
            )
        finally:
            pg.stop()
    else:
        raise ValueError("Onbekende proefstap.")


def docker(*args, invoer=None):
    return subprocess.run(["docker", *args], input=invoer, stdout=subprocess.PIPE, text=True, check=True).stdout.strip()


@contextmanager
def hub_image(image, volume, bewaren):
    container = docker(
        "run",
        "-d",
        "--name",
        volume + "-hub",
        "--pull=never",
        "--network=none",
        "--health-interval=2s",
        "--health-start-period=5s",
        "-v",
        f"{Path(__file__).resolve()}:/proef.py:ro",
        "-v",
        volume + ":/appdata",
        "-e",
        f"HUB_SELF_BACKUP_KEEP={bewaren}",
        image,
    )
    try:
        for _ in range(45):
            if docker("inspect", "-f", "{{.State.Health.Status}}", container) == "healthy":
                break
            time.sleep(2)
        else:
            raise RuntimeError("De lokale proefimage werd niet gezond.")
        yield container
    finally:
        try:
            docker("stop", container)
        finally:
            docker("rm", "-v", container)


def in_hub(container, stap, argument="", invoer=None):
    return docker(
        "exec", "-i", "-u", "568", container, "python", "/proef.py", "in-image", stap, argument, invoer=invoer
    )


def proef(vorig, nieuw, bewaren):
    naam = "asm-terugval-" + uuid.uuid4().hex
    wachtwoord = secrets.token_urlsafe(32)
    with ExitStack() as resources:
        bron, terug = naam + "-bron", naam + "-terug"
        for volume in (bron, terug):
            docker("volume", "create", volume)
            resources.callback(docker, "volume", "rm", volume)
        with hub_image(vorig, bron, bewaren) as container:
            in_hub(container, "vullen")
            in_hub(container, "setup/admin", "0014", wachtwoord)
        with hub_image(nieuw, bron, bewaren) as container:
            in_hub(container, "auth/login", "0015", wachtwoord)
            bestand = in_hub(container, "archief")
            if not bestand:
                raise SystemExit(f"Retentie {bewaren}: schema 0015 bereikt zonder bewaard pre-upgradearchief.")
        docker(
            "run",
            "--rm",
            "--name",
            terug + "-laden",
            "--pull=never",
            "--network=none",
            "-v",
            f"{Path(__file__).resolve()}:/proef.py:ro",
            "-v",
            bron + ":/bron:ro",
            "-v",
            terug + ":/appdata",
            vorig,
            "python",
            "/proef.py",
            "in-image",
            "herstel",
            bestand,
        )
        with hub_image(vorig, terug, bewaren) as container:
            in_hub(container, "auth/login", "0014", wachtwoord)
    print(f"Retentie {bewaren}: upgrade 0015, eigen export hersteld op 0014, laatste testgebruiker aangemeld.")


if __name__ == "__main__":
    if sys.argv[1:2] == ["in-image"]:
        stap_in_image(*sys.argv[2:])
    else:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("vorig")
        parser.add_argument("nieuw")
        parser.add_argument("bewaren", type=int, choices=(1, 7))
        args = parser.parse_args()
        proef(args.vorig, args.nieuw, args.bewaren)
