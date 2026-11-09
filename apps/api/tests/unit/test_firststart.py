"""First-start-init (contract §3): geheimen 0600, nooit overschrijven, setupcode alleen als hash op schijf."""

from __future__ import annotations

import stat
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from hub.firststart import (
    ED25519_KEYS,
    VAULT_KEY,
    FirstStartError,
    ensure_secrets,
    log_lines,
    mark_setup_completed,
    setup_pending,
    verify_setup_code,
)


def _mode(p: Path) -> int:
    return stat.S_IMODE(p.stat().st_mode)


def test_maakt_alle_geheimen_met_strikte_rechten(tmp_path: Path) -> None:
    d = tmp_path / "secrets"
    res = ensure_secrets(d)
    assert sorted(res.created) == sorted([*ED25519_KEYS, VAULT_KEY])
    assert _mode(d) == 0o700
    for name in [*ED25519_KEYS, VAULT_KEY, "setup-code.json"]:
        assert _mode(d / name) == 0o600, name
    assert res.setup_code and len(res.setup_code) == 14
    # de code zelf staat nergens op schijf
    for f in d.iterdir():
        assert res.setup_code.encode() not in f.read_bytes()
        assert res.setup_code.replace("-", "").encode() not in f.read_bytes()


def test_overschrijft_nooit_en_scherpt_rechten_aan(tmp_path: Path) -> None:
    d = tmp_path / "secrets"
    ensure_secrets(d)
    before = {n: (d / n).read_bytes() for n in [*ED25519_KEYS, VAULT_KEY]}
    (d / VAULT_KEY).chmod(0o644)
    res = ensure_secrets(d)
    assert res.created == []
    assert VAULT_KEY in res.tightened and _mode(d / VAULT_KEY) == 0o600
    assert {n: (d / n).read_bytes() for n in before} == before


@pytest.mark.parametrize("content", [b"", b"geen-base64!!", b"AAAA\n"])
def test_ongeldige_vault_key_is_harde_fout(tmp_path: Path, content: bytes) -> None:
    d = tmp_path / "secrets"
    d.mkdir(mode=0o700)
    (d / VAULT_KEY).write_bytes(content)
    with pytest.raises(FirstStartError):
        ensure_secrets(d)
    assert (d / VAULT_KEY).read_bytes() == content  # niet overschreven


def test_ongeldige_ed25519_wordt_niet_overschreven(tmp_path: Path) -> None:
    d = tmp_path / "secrets"
    d.mkdir(mode=0o700)
    (d / "jwt-signing.ed25519").write_bytes(b"-----BEGIN PRIVATE KEY-----\nrommel\n-----END PRIVATE KEY-----\n")
    with pytest.raises(FirstStartError):
        ensure_secrets(d)


def test_setupcode_verifieren_normaliseren_en_verlopen(tmp_path: Path) -> None:
    d = tmp_path / "secrets"
    res = ensure_secrets(d, setup_code_ttl_seconds=600)
    code = res.setup_code
    assert code is not None
    assert verify_setup_code(d, code)
    assert verify_setup_code(d, code.lower().replace("-", " "))
    assert not verify_setup_code(d, "0000-0000-0000")
    assert not verify_setup_code(d, code, now=datetime.now(UTC) + timedelta(seconds=601))


def test_nieuwe_start_maakt_nieuwe_code_maar_api_hergebruikt(tmp_path: Path) -> None:
    d = tmp_path / "secrets"
    first = ensure_secrets(d).setup_code
    again = ensure_secrets(d, new_setup_code=False)
    assert again.setup_code is None and verify_setup_code(d, first or "")
    second = ensure_secrets(d, new_setup_code=True).setup_code
    assert second != first and verify_setup_code(d, second or "") and not verify_setup_code(d, first or "")


def test_na_setup_geen_code_meer(tmp_path: Path) -> None:
    d = tmp_path / "secrets"
    code = ensure_secrets(d).setup_code or ""
    mark_setup_completed(d)
    assert not setup_pending(d)
    assert not verify_setup_code(d, code)
    res = ensure_secrets(d)
    assert res.setup_code is None and res.setup_completed
    assert any("setup is afgerond" in line for line in log_lines(res))


def test_logregels_tonen_code_en_uitleg(tmp_path: Path) -> None:
    res = ensure_secrets(tmp_path / "s")
    text = "\n".join(log_lines(res))
    assert f"SETUPCODE (eenmalig, voor het eerste beheerdersaccount): {res.setup_code}" in text
    assert "Herstart de app" in text
