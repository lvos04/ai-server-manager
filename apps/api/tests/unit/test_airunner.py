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


def test_actief_kanaal_weigert_buiten_de_runner_uid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os, "getuid", lambda: 568)
    assert airunner.main(tmp_path, ai_enabled=True, once=True) == 78


def test_runner_beperkt_antwoord_en_weigert_betaalde_uitwijk() -> None:
    from uuid import uuid4

    from fakes.fake_kredietdienst import FakeKredietdienst

    from hub.ai.runner import Aanvraag, Triage, raadpleeg
    from hub.timeutil import utcnow

    fake = FakeKredietdienst(2)
    fake.start()
    try:
        instellingen = config.Settings(ai_provider_url=f"http://localhost:{fake.port}", outbound_allow_loopback=True)
        taak = Aanvraag(
            taak_id=uuid4(),
            aanbieder=uuid4().hex,
            modelkeuze=uuid4().hex,
            maand=utcnow().strftime("%Y-%m"),
            max_eenheden=1,
            triage=Triage(ernst="waarschuwing", gebeurtenissen=1, inventaris="unknown", logregels=0),
        )
        assert raadpleeg(taak, instellingen).status == "dienst_onbeschikbaar"
        assert fake.requests == []
        instellingen.ai_enabled = True
        assert raadpleeg(taak, instellingen).status == "advies"
        fake.advies["action_id"] = "app.restart"
        assert raadpleeg(taak.model_copy(update={"taak_id": uuid4()}), instellingen).status == "dienst_onbeschikbaar"
        assert raadpleeg(taak.model_copy(update={"taak_id": uuid4()}), instellingen).status == "tegoed_op"
        assert fake.paths() == ["/diagnose"] * 3
        assert fake.eenheden == 0
    finally:
        fake.stop()


@pytest.mark.parametrize(
    ("werkwoord", "reden", "probleem"),
    [
        ("paused", "manual", False),
        ("stalled", "manual", False),
        ("stalled", "playback_active", False),
        ("stalled", None, True),
        ("crashed", "manual", True),
    ],
)
def test_av1_pauze_en_crash_blijven_onderscheidbaar(werkwoord: str, reden: str | None, probleem: bool) -> None:
    from hub.incidents.rules import EventIn, classify
    from hub.timeutil import utcnow

    ev = EventIn(
        "inbox",
        "proef",
        "mediaguard",
        f"media.av1.{werkwoord}",
        "taak",
        "proef",
        {"pause_reason": reden},
        "internal",
        utcnow(),
    )
    signaal = classify(ev)
    assert (signaal is not None and signaal.rol == "probleem") == probleem


def test_gevoelige_kennis_vraagt_ook_met_een_bekend_incident_id_beheer() -> None:
    from unittest.mock import Mock
    from uuid import uuid4

    from sqlalchemy.orm import Session

    from hub.ai import kennis
    from hub.deps import Principal
    from hub.errors import HubError
    from hub.models import Incident
    from hub.security import Role

    db = Mock(spec=Session)
    bron = Incident(id=uuid4(), classificatie="sensitive")
    db.get.return_value = bron
    for rol in (Role.viewer, Role.operator):
        with pytest.raises(HubError) as fout:
            kennis.incident(db, bron.id, Principal("user", "proef", "lezer", role=rol))
        assert fout.value.status == 403
    assert kennis.incident(db, bron.id, Principal("user", "proef", "beheerder", role=Role.admin)) is bron


@pytest.mark.parametrize(("status", "veilige_modus"), [("gesnoozed", False), ("opgelost", False), ("open", True)])
def test_plan_weigert_vóór_readback_bij_pauze_herstel_of_veilige_modus(status: str, veilige_modus: bool) -> None:
    from unittest.mock import Mock
    from uuid import uuid4

    from sqlalchemy.orm import Session

    from hub.ai import plan
    from hub.errors import HubError
    from hub.models import Incident
    from hub.vault import Vault

    db, vault = Mock(spec=Session), Mock(spec=Vault)
    inc = Incident(soort="app.gezondheid", bron="hub:alerts", status=status, veilige_modus=veilige_modus)
    with pytest.raises(HubError) as fout:
        plan.voorstel(
            db,
            config.Settings(),
            vault,
            inc,
            request_id=uuid4(),
            action_id=None,
            target=None,
            parameters={},
            expected_version=None,
            trace_id="",
        )
    assert (fout.value.status, fout.value.code) == (422, "geen_runbookvoorstel")
    assert db.mock_calls == vault.mock_calls == []
