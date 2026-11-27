"""First-start-init (contract §3): geheimen 0600, nooit overschrijven, setupcode alleen als hash op schijf."""

from __future__ import annotations

import stat
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from hub.firststart import (
    ED25519_KEYS,
    VAULT_KEY,
    WEB_KEY,
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
    assert sorted(res.created) == sorted([*ED25519_KEYS, VAULT_KEY, WEB_KEY])
    assert _mode(d) == 0o700
    for name in [*ED25519_KEYS, VAULT_KEY, WEB_KEY, "setup-code.json"]:
        assert _mode(d / name) == 0o600, name
    assert res.setup_code and len(res.setup_code) == 14
    # de code zelf staat nergens op schijf
    for f in d.iterdir():
        assert res.setup_code.encode() not in f.read_bytes()
        assert res.setup_code.replace("-", "").encode() not in f.read_bytes()


def test_overschrijft_nooit_en_scherpt_rechten_aan(tmp_path: Path) -> None:
    d = tmp_path / "secrets"
    ensure_secrets(d)
    before = {n: (d / n).read_bytes() for n in [*ED25519_KEYS, VAULT_KEY, WEB_KEY]}
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


@pytest.mark.parametrize("attribuut", ["system.nfs4_acl_xdr", "system.nfs4_acl"])
def test_beperkte_acl_eerste_start_en_herstart(tmp_path, monkeypatch, attribuut):
    import os

    d = tmp_path / "secrets"
    d.mkdir(mode=0o750)

    def geweigerd(*args):
        raise PermissionError("chmod geweigerd")

    def lees_acl(fd, naam):
        assert isinstance(fd, int)
        if naam == attribuut:
            return b"acl"
        raise OSError("onbekend attribuut")

    with monkeypatch.context() as proef:
        proef.setattr(os, "getxattr", lees_acl)
        proef.setattr(os, "chmod", geweigerd)
        proef.setattr(os, "fchmod", geweigerd)
        eerste = ensure_secrets(d)
        assert verify_setup_code(d, eerste.setup_code or "")
    bestand = d / VAULT_KEY
    inhoud = bestand.read_bytes()
    bestand.chmod(0o640)
    monkeypatch.setattr(os, "getxattr", lees_acl)
    monkeypatch.setattr(os, "chmod", geweigerd)
    monkeypatch.setattr(os, "fchmod", geweigerd)
    tweede = ensure_secrets(d)
    assert bestand.read_bytes() == inhoud
    assert VAULT_KEY not in tweede.tightened
    assert verify_setup_code(d, tweede.setup_code or "")


def test_zonder_nfs4_acl_blijft_geweigerde_chmod_een_fout(tmp_path, monkeypatch):
    import os

    d = tmp_path / "secrets"
    d.mkdir(mode=0o750)

    def geweigerd(*args):
        raise PermissionError("geen NFSv4-ACL")

    for naam in ("chmod", "fchmod", "getxattr"):
        monkeypatch.setattr(os, naam, geweigerd)
    with pytest.raises(PermissionError):
        ensure_secrets(d)
    assert not list(d.iterdir())


@pytest.mark.parametrize("onveilig", ["symlink", "wereldschrijfbaar"])
def test_acl_versoepelt_type_en_wereldschrijfrechten_niet(tmp_path, monkeypatch, onveilig):
    import os

    d = tmp_path / "secrets"
    ensure_secrets(d)
    bestand = d / VAULT_KEY
    if onveilig == "symlink":
        bestand.rename(tmp_path / "origineel")
        bestand.symlink_to(tmp_path / "origineel")
    else:
        bestand.chmod(0o666)
    monkeypatch.setattr(os, "getxattr", lambda *_: b"acl")
    with pytest.raises(OSError):
        ensure_secrets(d)


def test_acl_vervangt_eigenaar_of_postgresrechten_niet(tmp_path, monkeypatch):
    import os

    from hub.bestandsrechten import prive_map

    tmp_path.chmod(0o770)
    monkeypatch.setattr(os, "getxattr", lambda *_: b"acl")

    def geweigerd(*args):
        raise PermissionError("beperkte ACL")

    monkeypatch.setattr(os, "fchmod", geweigerd)
    with pytest.raises(PermissionError, match="eigenaar"):
        prive_map(tmp_path, os.geteuid() + 1)
    with pytest.raises(PermissionError, match="PostgreSQL"):
        prive_map(tmp_path, os.geteuid(), postgres=True)
    tmp_path.chmod(0o750)
    prive_map(tmp_path, os.geteuid(), postgres=True)


def test_supervisor_bereidt_dataset_met_beperkte_acl_voor(tmp_path, monkeypatch):
    import importlib.util
    import os

    deploy = Path(__file__).resolve().parents[4] / "deploy"
    monkeypatch.syspath_prepend(str(deploy / "common"))
    spec = importlib.util.spec_from_file_location("hub_supervisor_proef", deploy / "allinone/supervisor.py")
    assert spec is not None and spec.loader is not None
    supervisor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(supervisor)
    data = tmp_path / "data"
    data.mkdir()
    for naam, mode in (("postgres", 0o750), ("secrets", 0o770), ("backups", 0o770)):
        (data / naam).mkdir()
        (data / naam).chmod(mode)
    chmod = os.chmod

    def geweigerd(*args):
        raise PermissionError("beperkte ACL")

    def chmod_op_pad(pad, mode):
        if Path(pad).parent == data:
            geweigerd()
        chmod(pad, mode)

    for naam, waarde in {
        "DATA": data,
        "PGDATA": data / "postgres",
        "SOCKET_DIR": tmp_path / "socket",
        "WEB_SERVER": deploy / "allinone/supervisor.py",
        "WEB_RUNTIME_DIR": tmp_path / "web",
        "UID": os.getuid(),
        "GID": os.getgid(),
        "fail": geweigerd,
    }.items():
        monkeypatch.setattr(supervisor, naam, waarde)
    monkeypatch.setattr(os, "getxattr", lambda *_: b"acl")
    monkeypatch.setattr(os, "fchmod", geweigerd)
    monkeypatch.setattr(os, "chmod", chmod_op_pad)
    supervisor.prepare_dirs()
    assert _mode(data / "secrets") == 0o770
    assert _mode(supervisor.SOCKET_DIR) == 0o700
    assert _mode(supervisor.WEB_RUNTIME_DIR) == 0o700


def test_ingerichte_hub_vervangt_ontbrekende_gepinde_policysleutel_niet(tmp_path: Path) -> None:
    ensure_secrets(tmp_path)
    mark_setup_completed(tmp_path)
    sleutel = tmp_path / "policy-signing.ed25519"
    sleutel.unlink()
    with pytest.raises(FirstStartError, match="Herstel de bestaande sleutel"):
        ensure_secrets(tmp_path)
    assert not sleutel.exists()
