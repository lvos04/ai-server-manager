"""De AI-runner controleert zijn eigen toegang tot sleutels en database bij de start."""

from __future__ import annotations

import errno
import os
import subprocess
import sys
from pathlib import Path
from typing import Never

import pytest

from hub import airunner, config
from hub.firststart import ensure_secrets


def _leesfout(*args: object, **kwargs: object) -> Never:
    raise OSError(errno.EIO, "interne proefmarkering")


def test_weigert_bij_leesbare_geheimen(tmp_path: Path) -> None:
    ensure_secrets(tmp_path / "secrets")  # eigenaar = huidige gebruiker → leesbaar → weigeren
    assert airunner.main(tmp_path, ai_enabled=False, once=True) == 78


def test_start_zonder_toegang(tmp_path: Path) -> None:
    (tmp_path / "secrets").mkdir()
    assert airunner.can_read_secrets(tmp_path / "secrets") == []
    assert airunner.main(tmp_path, ai_enabled=False, once=True) == 0


@pytest.mark.parametrize("ingeschakeld", [False, True])
@pytest.mark.parametrize("doel", ["postgres", "standaardsocket", "ingestelde_socket"])
@pytest.mark.parametrize("rechten", [0o100, 0o400])
def test_weigert_bij_toegankelijke_databasemap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ingeschakeld: bool, doel: str, rechten: int
) -> None:
    mapnaam = tmp_path / doel
    mapnaam.mkdir()
    if doel == "postgres":
        gegevens = mapnaam / "base" / "1" / "210"
        gegevens.parent.mkdir(parents=True)
        gegevens.write_bytes(b"210")
    elif doel == "standaardsocket":
        monkeypatch.setattr(config, "DEFAULT_SOCKET_DIR", str(mapnaam))
    else:
        monkeypatch.setenv("PGHOST", str(mapnaam))
    # Er luistert nog geen database. Leesrecht en doorgangsrecht zijn elk afzonderlijk voldoende om te weigeren.
    mapnaam.chmod(rechten)
    try:
        assert airunner.main(tmp_path, ai_enabled=ingeschakeld, once=True) == 78
    finally:
        mapnaam.chmod(0o700)


@pytest.mark.parametrize("storing", [False, True], ids=["leesbare-sleutel", "leesfout"])
def test_vaste_weigering_bij_sleutelcontrole(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, storing: bool
) -> None:
    sleutel = tmp_path / "secrets" / airunner.FORBIDDEN[0]
    sleutel.parent.mkdir()
    sleutel.write_bytes(b"210")
    if storing:
        monkeypatch.setattr(Path, "open", _leesfout)
    assert airunner.main(tmp_path, ai_enabled=False, once=True) == 78
    assert caplog.messages == [
        "De AI-runner weigert te starten omdat de isolatie van sleutels en database niet vaststaat."
    ]


def test_weigert_bij_onbesliste_databasecontrole(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os, "scandir", _leesfout)
    assert airunner.main(tmp_path, ai_enabled=False, once=True) == 78


@pytest.mark.parametrize("url", ["ongeldige-instelling", "postgresql://proef.invalid/hub"])
def test_weigert_bij_een_database_die_niet_lokaal_te_toetsen_is(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, url: str
) -> None:
    monkeypatch.setattr(config, "get_settings", lambda: config.Settings(database_url=url))
    assert airunner.main(tmp_path, ai_enabled=False, once=True) == 78


def test_cli_toetst_de_socket_uit_de_database_url_voor_postgres_luistert(tmp_path: Path) -> None:
    socketmap = tmp_path / "socket"
    env = dict(os.environ, HUB_DATA_DIR=str(tmp_path), HUB_DATABASE_URL=f"postgresql://hub@/hub?host={socketmap}")
    opdracht = [sys.executable, "-m", "hub", "ai-runner", "--once"]
    assert subprocess.run(opdracht, env=env, check=False).returncode == 0
    socketmap.mkdir()
    assert subprocess.run(opdracht, env=env, check=False).returncode == 78
