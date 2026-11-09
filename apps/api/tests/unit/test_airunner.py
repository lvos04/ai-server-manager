"""AI-runner weigert te starten als hij geheimen kan lezen."""

from __future__ import annotations

from pathlib import Path

from hub import airunner
from hub.firststart import ensure_secrets


def test_weigert_bij_leesbare_geheimen(tmp_path: Path) -> None:
    ensure_secrets(tmp_path / "secrets")  # eigenaar = huidige gebruiker → leesbaar → weigeren
    assert airunner.main(tmp_path, ai_enabled=False, once=True) == 78


def test_start_zonder_toegang(tmp_path: Path) -> None:
    (tmp_path / "secrets").mkdir()
    assert airunner.can_read_secrets(tmp_path / "secrets") == []
    assert airunner.main(tmp_path, ai_enabled=False, once=True) == 0
