"""Duurzame stop en onbekende uitkomst ná de schrijfaanroep (S-P2-030, herstel van R-TECH-1 en R-VEILIG-1 t/m -4;
ADR-0030 besluit 14; ``docs/EXECUTION_REQUEST.md#Uitvoeren en teruglezen``). Sim-getest tegen de nagebootste TrueNAS.

- R-TECH-1: faalt het opvragen van de jobstatus nadat TrueNAS de schrijfaanroep heeft aangenomen, dan is de uitkomst
  onbekend (409 ``afwijking``, stop), nooit 502 "TrueNAS heeft de actie niet uitgevoerd".
- R-VEILIG-1: een journaalfout op het moment van stoppen laat de executor niet doorwerken (stop en einde van de rij in
  één transactie, anders in het geheugen); een ``afwijking`` zonder vrijgave telt als stop.
- R-VEILIG-2: een proces dat wegvalt na de schrijfaanroep (rij ``gestart`` zonder einde) of een onverwachte fout ná
  de schrijfaanroep geeft een stop, bij het starten en vóór de volgende uitvoering.
- R-VEILIG-3: te diep geneste JSON geeft 422, geen 500.
- R-VEILIG-4: het journaal bewaart alleen de code en de foutnaam, nooit de vrije fouttekst van TrueNAS.

Een stop raakt nooit een app: alleen de executor weigert (``executor_gestopt``) tot de vrijgave op de executorpagina
("Sleutel vervangen" met de huidige sleutel en een leeg veld "Nieuwe sleutel").
"""

from __future__ import annotations

import contextlib
import re
import sqlite3
import threading
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from asm_policy.etag import ABSENT, app_etag
from executorhelpers import (
    BASE,
    POLICY,
    WRITE_KEY,
    Hub,
    approved,
    auth,
    execute,
    nas_hub,
    set_write_key,
    write_nas,
)
from executorhelpers import client as hub_client
from fakes.fake_truenas import FakeTrueNAS
from fastapi.testclient import TestClient
from policyhelpers import DIGEST_B, HOST, install_params, proposal

from executor.app import create_app
from executor.journal import Journal, JournalUnavailable
from executor.naslink import NasLinkStore
from executor.truenas import NasClient, NasFout
from executor.uitvoeren import Uitvoerder

REPO = "ghcr.io/voorbeeld/demo-app"
NIET_UITGEVOERD = "niet uitgevoerd"
Stack = tuple[Hub, TestClient, FakeTrueNAS]


@pytest.fixture
def nas() -> Iterator[FakeTrueNAS]:
    fake = write_nas().start()
    yield fake
    fake.stop()


@pytest.fixture
def stack(tmp_path: Path, nas: FakeTrueNAS) -> Stack:
    hub = nas_hub(tmp_path / "appdata", nas)
    set_write_key(hub, nas)
    return hub, hub_client(hub), nas


def app_prop(nas: FakeTrueNAS, action: str, name: str, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
    etag = app_etag(nas.app(name), nas.data["app.image.query"])
    return proposal(action, {"host_id": HOST, "app_id": name}, parameters, expected_version=etag)


def install_prop(name: str = "demo-app", **values: Any) -> dict[str, Any]:
    return proposal(
        "app.install", {"host_id": HOST, "app_id": name}, install_params(name, **values), expected_version=ABSENT
    )


def herstart(hub: Hub, nas: FakeTrueNAS) -> dict[str, Any]:
    return approved(hub, app_prop(nas, "app.restart", "my-house"), risk_class="R1")


def writes(nas: FakeTrueNAS) -> list[str]:
    return [m for m in nas.mutations if m != "app.config"]


def journaal(hub: Hub) -> Journal:
    return Journal(hub.settings.replay_db, hub.settings.secrets_dir)


def rijen(hub: Hub) -> list[tuple[str, str]]:
    # Zonder de snapshotactie achter het checkpoint van approved() (executorhelpers.checkpoint).
    return [
        (str(e["status"]), str(e["detail"] or ""))
        for e in journaal(hub).entries()
        if e["action_id"] != "zfs.snapshot.create"
    ]


def uitvoerder(hub: Hub) -> Uitvoerder:
    return Uitvoerder(
        policy=POLICY,
        journal=journaal(hub),
        naslink=NasLinkStore(hub.settings.secrets_dir),
        settle_seconds=0.5,
        poll_seconds=0.05,
        timeout=5,
    )


def vrijgeven(c: TestClient) -> Any:
    """De bestaande weg: "Sleutel vervangen" met de huidige sleutel en een leeg veld "Nieuwe sleutel"."""
    m = re.search(r'name="csrf" value="([^"]+)"', c.get("/").text)
    token = m.group(1) if m else ""
    return c.post(
        "/beheer",
        data={"csrf": token, "truenas_sleutel": WRITE_KEY, "actie": "vervangen"},
        headers={"Origin": str(c.base_url).rstrip("/")},
    )


def gestopt_gemeld(r: Any) -> bool:
    return bool(r.status_code == 409 and r.json()["code"] == "executor_gestopt")


# ------------------------------------------------------------------ R-TECH-1: jobstatus niet op te vragen
@pytest.mark.parametrize("code", ["truenas_fout", "truenas_geen_toegang", "truenas_timeout", "truenas_onbereikbaar"])
def test_fout_bij_het_opvragen_van_de_jobstatus_is_een_onbekende_uitkomst(
    stack: Stack, monkeypatch: pytest.MonkeyPatch, code: str
) -> None:
    """TrueNAS neemt ``app.stop`` aan (er is een job-id; de job loopt nog), daarna faalt ``core.get_jobs``. De job kan
    nog slagen: 409 ``afwijking`` met ``uitkomst_onbekend`` en een stop, nooit 502 "niet uitgevoerd" (R-TECH-1)."""
    hub, c, nas = stack
    nas.job_polls = 50  # de job staat nog op RUNNING
    nas.silent_noop.add("app.stop")  # en er is nog niets zichtbaar
    echte_call = NasClient.call

    def call(self: NasClient, method: str, *params: Any, timeout: float | None = None) -> Any:
        if method == "core.get_jobs":
            raise NasFout(code, "core.get_jobs: [EFAULT] peilen mislukt")
        return echte_call(self, method, *params, timeout=timeout)

    monkeypatch.setattr(NasClient, "call", call)
    req = approved(hub, app_prop(nas, "app.stop", "my-house"), risk_class="R2")
    r = execute(c, hub, req)
    assert r.status_code == 409 and r.json()["code"] == "afwijking", r.text
    assert NIET_UITGEVOERD not in r.json()["message"] and "niets uitgevoerd" not in r.json()["message"]
    d = r.json()["details"]
    assert d["reden"] == "uitkomst_onbekend" and d["gestopt"] is True and d["methode"] == "app.stop"
    assert writes(nas) == ["app.stop"] and len(nas.jobs) == 1
    assert rijen(hub) == [("afwijking", "uitkomst_onbekend")]
    monkeypatch.undo()
    assert gestopt_gemeld(execute(c, hub, herstart(hub, nas)))
    assert writes(nas) == ["app.stop"]


def test_geweigerde_aanroep_en_mislukte_job_blijven_502_zonder_stop(stack: Stack) -> None:
    """De andere kant van R-TECH-1: weigert TrueNAS de aanroep zelf (geen job-id) of meldt de job FAILED, en is het
    doel onveranderd, dan blijft het 502 ``uitvoering_mislukt`` en werkt de executor door."""
    hub, c, nas = stack
    nas.keys[WRITE_KEY].deny.add("app.redeploy")
    r = execute(c, hub, herstart(hub, nas))
    assert r.status_code == 502 and r.json()["details"]["reden"] == "truenas_geen_toegang", r.text
    nas.keys[WRITE_KEY].deny.clear()
    nas.fail["app.redeploy"] = "proef"
    r = execute(c, hub, herstart(hub, nas))
    assert r.status_code == 502 and r.json()["details"]["reden"] == "job_mislukt", r.text
    del nas.fail["app.redeploy"]
    assert execute(c, hub, herstart(hub, nas)).status_code == 200
    assert [s for s, _d in rijen(hub)] == ["mislukt", "mislukt", "uitgevoerd"]


# ------------------------------------------------------------------ R-VEILIG-1: journaalfout bij het stoppen
@pytest.mark.parametrize("welke", ["finish", "stop"])
def test_journaalfout_bij_het_stoppen_houdt_de_executor_gestopt(
    stack: Stack, monkeypatch: pytest.MonkeyPatch, welke: str
) -> None:
    """Proef B van R-VEILIG: een andere digest dan goedgekeurd (afwijking), en precies op dat moment faalt het journaal
    één keer (``finish`` of ``stop``). De volgende actie moet ``executor_gestopt`` geven, ook na een herstart, tot de
    vrijgave; de rij staat daarna op ``afwijking``."""
    hub, c, nas = stack
    nas.digest_override[REPO] = DIGEST_B
    echt = getattr(Journal, welke)
    teller = {"n": 0}

    def eenmaal_kapot(self: Journal, *a: Any, **k: Any) -> Any:
        teller["n"] += 1
        if teller["n"] == 1:
            raise JournalUnavailable("OperationalError")  # schijf vol of I/O-fout op dit moment
        return echt(self, *a, **k)

    monkeypatch.setattr(Journal, welke, eenmaal_kapot)
    r = execute(c, hub, approved(hub, install_prop()))
    assert r.status_code == 409 and r.json()["code"] == "afwijking", r.text
    assert r.json()["details"]["gestopt"] is True and r.json()["details"]["reden"] == "digest_verschilt"
    assert gestopt_gemeld(execute(c, hub, herstart(hub, nas)))
    monkeypatch.undo()
    # Vastgelegd: een nieuwe instantie op dezelfde datamap (herstart) ziet de stop ook.
    assert journaal(hub).stopped() is not None
    assert rijen(hub) == [("afwijking", "digest_verschilt")]
    assert hub_client(hub).get("/api/v1/status").json()["gestopt"]["reden"] == "digest_verschilt"
    assert gestopt_gemeld(execute(hub_client(hub), hub, herstart(hub, nas)))
    assert writes(nas) == ["app.create"]
    # Vrijgeven via de bestaande weg; daarna loopt de volgende actie weer.
    assert "De executor is vrijgegeven." in vrijgeven(c).text
    assert execute(c, hub, herstart(hub, nas)).status_code == 200


def test_stop_in_het_geheugen_zolang_het_journaal_niet_werkt(stack: Stack, monkeypatch: pytest.MonkeyPatch) -> None:
    """Werkt het journaal na de afwijking helemaal niet meer, dan blijft de stop in het geheugen: niets wordt
    uitgevoerd en de status toont gestopt. Zodra het journaal weer werkt, wordt de stop vastgelegd."""
    hub, c, nas = stack
    nas.silent_noop.add("app.stop")
    kapot = {"aan": False}
    echte_stop = Journal.stop

    def stop(self: Journal, *a: Any, **k: Any) -> Any:
        kapot["aan"] = True  # vanaf de stop werkt het journaal niet meer
        raise JournalUnavailable("OperationalError")

    echt_connect = Journal._connect

    def connect(self: Journal) -> Any:
        if kapot["aan"]:
            raise JournalUnavailable("OperationalError")
        return echt_connect(self)

    monkeypatch.setattr(Journal, "stop", stop)
    monkeypatch.setattr(Journal, "_connect", connect)
    r = execute(c, hub, approved(hub, app_prop(nas, "app.stop", "my-house"), risk_class="R2"))
    assert r.status_code == 409 and r.json()["details"]["gestopt"] is True, r.text
    nas.silent_noop.clear()
    r = execute(c, hub, herstart(hub, nas))
    assert r.status_code == 503 and r.json()["code"] == "journaal_niet_beschikbaar", r.text
    st = c.get("/api/v1/status").json()
    assert st["gestopt"] is not None and st["uitvoeren"]["mogelijk"] is False
    # Het journaal werkt weer: de stop uit het geheugen wordt vastgelegd (met het einde van de rij).
    monkeypatch.setattr(Journal, "stop", echte_stop)
    kapot["aan"] = False
    assert gestopt_gemeld(execute(c, hub, herstart(hub, nas)))
    assert journaal(hub).stopped() is not None and rijen(hub) == [("afwijking", "staat_verschilt")]
    assert writes(nas) == ["app.stop"]


def test_journaal_weg_na_de_aanroep_geeft_een_stop_met_vrijgave_uitleg(
    stack: Stack, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Faalt het vastleggen van een geslaagde uitvoering (``finish``), dan is de uitkomst niet vastgelegd: 409
    ``afwijking`` met ``journaal_niet_beschikbaar`` en een stop. Zodra het journaal weer werkt, staat de stop vast als
    ``uitkomst_onbekend`` (niet als "journaal onleesbaar"), zodat de pagina uitlegt hoe je vrijgeeft."""
    hub, c, nas = stack

    def finish(self: Journal, *a: Any, **k: Any) -> None:
        raise JournalUnavailable("OperationalError")

    echte_stop = Journal.stop

    def stop(self: Journal, *a: Any, **k: Any) -> None:
        raise JournalUnavailable("OperationalError")

    monkeypatch.setattr(Journal, "finish", finish)
    monkeypatch.setattr(Journal, "stop", stop)
    r = execute(c, hub, herstart(hub, nas))
    assert r.status_code == 409 and r.json()["details"]["reden"] == "journaal_niet_beschikbaar", r.text
    assert r.json()["details"]["gestopt"] is True and "niets uitgevoerd" not in r.json()["message"]
    monkeypatch.setattr(Journal, "stop", echte_stop)
    monkeypatch.undo()
    assert gestopt_gemeld(execute(c, hub, herstart(hub, nas)))
    assert c.get("/api/v1/status").json()["gestopt"]["reden"] == "uitkomst_onbekend"
    assert rijen(hub) == [("afwijking", "journaal_niet_beschikbaar")]
    assert "Sleutel vervangen" in c.get("/").text and "De executor is vrijgegeven." in vrijgeven(c).text
    assert execute(c, hub, herstart(hub, nas)).status_code == 200


def test_afwijking_zonder_vrijgave_telt_als_stop(stack: Stack) -> None:
    """Een rij ``afwijking`` van na de laatste vrijgave zonder vastgelegde stop (zoals na een journaalfout vóór dit
    herstel) geeft bij de volgende actie alsnog de stop. Na de vrijgave telt die rij niet meer."""
    hub, c, nas = stack
    nas.silent_noop.add("app.stop")
    r = execute(c, hub, approved(hub, app_prop(nas, "app.stop", "my-house"), risk_class="R2"))
    assert r.status_code == 409 and r.json()["code"] == "afwijking", r.text
    nas.silent_noop.clear()
    with contextlib.closing(sqlite3.connect(hub.settings.replay_db)) as db, db:
        db.execute("DELETE FROM state WHERE key = 'gestopt'")  # de stop ontbreekt, de rij "afwijking" staat er
    assert gestopt_gemeld(execute(c, hub, herstart(hub, nas)))
    assert c.get("/api/v1/status").json()["gestopt"]["reden"] == "staat_verschilt"
    assert "De executor is vrijgegeven." in vrijgeven(c).text
    assert execute(c, hub, herstart(hub, nas)).status_code == 200
    assert c.get("/api/v1/status").json()["gestopt"] is None


def test_stop_en_einde_van_de_rij_staan_in_een_transactie(tmp_path: Path) -> None:
    """Faalt het einde van de rij, dan wordt ook de stop teruggedraaid (geen halve vastlegging); de aanroeper houdt
    de stop dan in het geheugen. Lukt het, dan staan beide er."""
    j = Journal(tmp_path / "executor.sqlite3", tmp_path)
    j.begin(request_id="r", nonce="n", action_id="app.stop", target={}, methode="app.stop", before_hash="h")
    with contextlib.closing(sqlite3.connect(j.path)) as db, db:
        db.execute("CREATE TRIGGER kapot BEFORE UPDATE ON journal BEGIN SELECT RAISE(ABORT, 'schijf'); END")
    with pytest.raises(JournalUnavailable):
        j.stop({"code": "staat_verschilt"}, nonce="n", detail="staat_verschilt")
    with contextlib.closing(sqlite3.connect(j.path)) as db, db:
        assert db.execute("SELECT count(*) FROM state WHERE key = 'gestopt'").fetchone()[0] == 0
        db.execute("DROP TRIGGER kapot")
    j.stop({"code": "staat_verschilt"}, nonce="n", detail="staat_verschilt")
    with contextlib.closing(sqlite3.connect(j.path)) as db:
        assert db.execute("SELECT status, detail FROM journal").fetchall() == [("afwijking", "staat_verschilt")]
    assert j.stopped() == {"code": "staat_verschilt"}


# ------------------------------------------------------------------ R-VEILIG-2: proces weg of onverwachte fout
class ProcesWeg(BaseException):
    """Nabootsing: het proces of de container stopt na de schrijfaanroep, vóór het teruglezen."""


def test_proces_weg_na_de_schrijfaanroep_stopt_bij_het_starten(
    tmp_path: Path, nas: FakeTrueNAS, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Proef A van R-VEILIG: installatie met een andere digest dan goedgekeurd; het proces valt weg na
    ``app.create``. Na de herstart (nieuwe instanties op dezelfde datamap) is de executor gestopt: bij het starten
    (lifespan) en vóór de volgende uitvoering; de rij staat niet meer op ``gestart``."""
    hub = nas_hub(tmp_path / "appdata", nas)
    set_write_key(hub, nas)
    nas.digest_override[REPO] = DIGEST_B
    keys = [hub.policy_key.public_key()]

    def weg(self: Uitvoerder, *a: Any, **k: Any) -> Any:
        raise ProcesWeg()

    monkeypatch.setattr(Uitvoerder, "_teruglezen", weg)
    with pytest.raises(ProcesWeg):
        uitvoerder(hub).run(approved(hub, install_prop()), keys)
    monkeypatch.undo()
    assert writes(nas) == ["app.create"] and rijen(hub) == [("gestart", "")]
    # Herstart: de app start (lifespan) en ziet de onafgemaakte uitvoering.
    with TestClient(create_app(hub.settings), base_url=BASE) as c:
        st = c.get("/api/v1/status").json()
        assert st["gestopt"]["reden"] == "uitkomst_onbekend", st
        assert st["uitvoeren"] == {"mogelijk": False, "reden": "executor_gestopt"}
        assert rijen(hub) == [("afwijking", "uitkomst_onbekend")]
        assert gestopt_gemeld(execute(c, hub, herstart(hub, nas)))
        r = c.get(f"/api/v1/executions/{journaal(hub).entries()[0]['request_id']}", headers=auth(hub.jwt()))
        assert r.json()["gestopt"] is True and r.json()["uitvoeringen"][0]["status"] == "afwijking"
    assert writes(nas) == ["app.create"]


def test_onafgemaakte_rij_telt_ook_zonder_herstart_van_de_app(
    tmp_path: Path, nas: FakeTrueNAS, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Zelfde proef, nu met een tweede instantie van de uitvoerder (zonder lifespan): vóór de uitvoering stopt hij."""
    hub = nas_hub(tmp_path / "appdata", nas)
    set_write_key(hub, nas)
    keys = [hub.policy_key.public_key()]

    def weg(self: Uitvoerder, *a: Any, **k: Any) -> Any:
        raise ProcesWeg()

    monkeypatch.setattr(Uitvoerder, "_teruglezen", weg)
    with pytest.raises(ProcesWeg):
        uitvoerder(hub).run(herstart(hub, nas), keys)
    monkeypatch.undo()
    uit = uitvoerder(hub).run(herstart(hub, nas), keys)
    assert uit.status == 409 and uit.body["code"] == "executor_gestopt", uit.body
    assert uit.body["details"]["reden"] == "uitkomst_onbekend"
    assert writes(nas) == ["app.redeploy"]


def test_onverwacht_antwoord_op_de_jobstatus_na_de_schrijfaanroep(
    stack: Stack, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Proef A2 van R-VEILIG: TrueNAS antwoordt op ``core.get_jobs`` met een getal in plaats van een lijst, nadat
    ``app.redeploy`` is verstuurd. Nooit een 500 met een rij die op ``gestart`` blijft: 409 ``afwijking``, stop."""
    hub, c, nas = stack
    monkeypatch.setattr(nas, "_jobs", lambda params: 7)
    r = execute(c, hub, herstart(hub, nas))
    assert r.status_code == 409 and r.json()["code"] == "afwijking", r.text
    assert r.json()["details"]["reden"] == "uitkomst_onbekend" and r.json()["details"]["gestopt"] is True
    assert writes(nas) == ["app.redeploy"] and rijen(hub) == [("afwijking", "uitkomst_onbekend")]
    monkeypatch.undo()
    assert gestopt_gemeld(execute(c, hub, herstart(hub, nas)))


@pytest.mark.parametrize("waar", ["uitvoeren", "teruglezen"])
def test_onverwachte_fout_na_de_schrijfaanroep_is_een_onbekende_uitkomst(
    stack: Stack, monkeypatch: pytest.MonkeyPatch, waar: str
) -> None:
    """Een andere uitzondering dan ``NasFout`` ná de schrijfaanroep (in de job-afhandeling of bij het teruglezen) is
    een onbekende uitkomst: 409 ``afwijking`` en stop, nooit een 500 zonder stop (R-VEILIG-2)."""
    hub, c, nas = stack
    if waar == "uitvoeren":
        echte_job = NasClient.job

        def job(self: NasClient, method: str, *params: Any, timeout: float, poll: float = 1.0) -> Any:
            echte_job(self, method, *params, timeout=timeout, poll=poll)
            raise RuntimeError("onverwacht")

        monkeypatch.setattr(NasClient, "job", job)
    else:

        def settle(self: Uitvoerder, *a: Any, **k: Any) -> Any:
            raise RuntimeError("onverwacht")

        monkeypatch.setattr(Uitvoerder, "_settle", settle)
    r = execute(c, hub, herstart(hub, nas))
    assert r.status_code == 409 and r.json()["code"] == "afwijking", r.text
    assert r.json()["details"]["reden"] == "uitkomst_onbekend" and r.json()["details"]["gestopt"] is True
    assert rijen(hub) == [("afwijking", "uitkomst_onbekend")]
    monkeypatch.undo()
    assert gestopt_gemeld(execute(c, hub, herstart(hub, nas)))


def test_fout_voor_de_schrijfaanroep_blijft_niets_uitgevoerd_zonder_stop(
    stack: Stack, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Faalt het bewaren van de vorige waarden (vóór ``app.update``), dan is er niets uitgevoerd: 503, geen stop, en de
    rij krijgt een einde (geen onafgemaakte uitvoering)."""
    hub, c, nas = stack
    assert execute(c, hub, approved(hub, install_prop())).status_code == 200

    def save_values(self: Journal, *a: Any, **k: Any) -> None:
        raise JournalUnavailable("vault.key")

    monkeypatch.setattr(Journal, "save_values", save_values)
    prop = app_prop(nas, "app.update", "demo-app", {"image": {"repository": REPO, "tag": f"1.2.4@{DIGEST_B}"}})
    r = execute(c, hub, approved(hub, prop))
    assert r.status_code == 503 and r.json()["code"] == "journaal_niet_beschikbaar", r.text
    assert writes(nas) == ["app.create"]
    monkeypatch.undo()
    assert rijen(hub) == [("uitgevoerd", ""), ("mislukt", "JournalUnavailable")]
    assert c.get("/api/v1/status").json()["gestopt"] is None
    assert execute(c, hub, herstart(hub, nas)).status_code == 200


def test_lopende_uitvoering_van_een_andere_instantie_is_geen_onafgemaakte_rij(tmp_path: Path, nas: FakeTrueNAS) -> None:
    """Twee instanties op dezelfde datamap in één proces: zolang de eerste nog uitvoert, is haar rij ``gestart`` geen
    onbekende uitkomst. De tweede krijgt ``executor_bezet`` (de nonce blijft bruikbaar) en er komt geen stop."""
    hub = nas_hub(tmp_path / "appdata", nas)
    set_write_key(hub, nas)
    keys = [hub.policy_key.public_key()]
    binnen, verder = threading.Event(), threading.Event()
    echte_job = NasClient.job

    def job(self: NasClient, method: str, *params: Any, timeout: float, poll: float = 1.0) -> Any:
        uit = echte_job(self, method, *params, timeout=timeout, poll=poll)
        binnen.set()
        assert verder.wait(10)
        return uit

    u1, u2 = uitvoerder(hub), uitvoerder(hub)
    eerste: list[int] = []
    mp = pytest.MonkeyPatch()
    mp.setattr(NasClient, "job", job)
    try:
        t = threading.Thread(target=lambda: eerste.append(u1.run(herstart(hub, nas), keys).status))
        t.start()
        assert binnen.wait(10)
        tweede = herstart(hub, nas)
        uit = u2.run(tweede, keys)
        assert uit.status == 409 and uit.body["code"] == "executor_bezet", uit.body
        assert journaal(hub).stopped() is None
        assert hub_client(hub).get("/api/v1/status").json()["gestopt"] is None
        verder.set()
        t.join(10)
    finally:
        verder.set()
        mp.undo()
    assert eerste == [200]
    assert u2.run(tweede, keys).status == 200  # dezelfde nonce: was nog niet verbruikt
    assert journaal(hub).stopped() is None and [s for s, _d in rijen(hub)] == ["uitgevoerd", "uitgevoerd"]


# ------------------------------------------------------------------ R-VEILIG-H1: geen valse stop door statusopvragen
def test_controle_tijdens_het_begin_van_een_uitvoering_geeft_geen_valse_stop(
    stack: Stack, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Proef N1 van de herreview, met vaste volgorde: draad A (de controle die een stop vastlegt) leest de lopende
    uitvoeringen, en pas daarna begint draad B een gewone uitvoering. De rij van B mag nooit als weggevallen tellen: B
    geeft 200 en de executor is daarna niet gestopt (R-VEILIG-H1). A wacht hooguit 1 s op het begin van B."""
    hub, _c, nas = stack
    u = uitvoerder(hub)
    j = u.journal
    a_heeft_gelezen, b_is_begonnen = threading.Event(), threading.Event()
    echt_lopend, echt_begin = Journal._lopende_nonces, Journal.begin

    def lopend(self: Journal) -> set[str]:
        uit = echt_lopend(self)
        if threading.current_thread().name == "A-controle" and not a_heeft_gelezen.is_set():
            a_heeft_gelezen.set()
            b_is_begonnen.wait(1)
        return uit

    def begin(self: Journal, **k: Any) -> None:
        echt_begin(self, **k)
        b_is_begonnen.set()

    monkeypatch.setattr(Journal, "_lopende_nonces", lopend)
    monkeypatch.setattr(Journal, "begin", begin)
    uitkomst: dict[str, Any] = {}
    # Er moet een rij zijn voordat A leest: een eerdere, afgemaakte uitvoering.
    assert u.run(herstart(hub, nas), [hub.policy_key.public_key()]).status == 200
    b_is_begonnen.clear()
    ta = threading.Thread(target=lambda: uitkomst.__setitem__("a", j.stopped()), name="A-controle")
    ta.start()
    assert a_heeft_gelezen.wait(5)
    b = u.run(herstart(hub, nas), [hub.policy_key.public_key()])
    ta.join(10)
    monkeypatch.undo()
    assert b.status == 200 and b.body["status"] == "uitgevoerd", b.body
    assert uitkomst["a"] is None
    assert journaal(hub).stopped() is None and rijen(hub) == [("uitgevoerd", ""), ("uitgevoerd", "")]
    assert u.run(herstart(hub, nas), [hub.policy_key.public_key()]).status == 200


def test_statusopvraag_leest_alleen_en_legt_geen_stop_vast(
    tmp_path: Path, nas: FakeTrueNAS, monkeypatch: pytest.MonkeyPatch
) -> None:
    """De onaangemelde statusroutes (GET /api/v1/status, GET /) en het journaal voor de Hub openen geen
    schrijftransactie: ook terwijl een ander de schrijfvergrendeling van het journaal houdt, antwoorden ze meteen en
    zonder "journaal niet beschikbaar", en een onafgemaakte rij blijft door een statusopvraag onaangeroerd. De stop
    wordt pas vóór de volgende uitvoering vastgesteld (R-VEILIG-H1)."""
    hub = nas_hub(tmp_path / "appdata", nas)
    set_write_key(hub, nas)
    keys = [hub.policy_key.public_key()]

    def weg(self: Uitvoerder, *a: Any, **k: Any) -> Any:
        raise ProcesWeg()

    monkeypatch.setattr(Uitvoerder, "_teruglezen", weg)
    req = herstart(hub, nas)
    with pytest.raises(ProcesWeg):
        uitvoerder(hub).run(req, keys)
    monkeypatch.undo()
    c = hub_client(hub)
    with contextlib.closing(sqlite3.connect(hub.settings.replay_db, timeout=0.1)) as slot:
        slot.execute("BEGIN IMMEDIATE")  # een ander houdt de schrijfvergrendeling
        try:
            for pad in ("/api/v1/status", "/"):
                r = c.get(pad)
                assert r.status_code == 200, r.text[:200]
                assert "journaal_niet_beschikbaar" not in r.text
            st = c.get("/api/v1/status").json()
            assert st["gestopt"] is None, st
            rid = req["proposal"]["idempotency_key"]
            jr = c.get(f"/api/v1/executions/{rid}", headers=auth(hub.jwt()))
            assert jr.status_code == 200 and jr.json()["uitvoeringen"][0]["status"] == "gestart", jr.text
        finally:
            slot.execute("ROLLBACK")
    assert rijen(hub) == [("gestart", "")]
    with contextlib.closing(sqlite3.connect(hub.settings.replay_db)) as db:
        assert db.execute("SELECT count(*) FROM state WHERE key = 'gestopt'").fetchone()[0] == 0
    # Vóór de volgende uitvoering wordt de onafgemaakte rij wel een stop.
    r = execute(c, hub, herstart(hub, nas))
    assert gestopt_gemeld(r) and r.json()["details"]["reden"] == "uitkomst_onbekend", r.text
    assert c.get("/api/v1/status").json()["gestopt"]["reden"] == "uitkomst_onbekend"


def test_veel_statusopvragen_tijdens_uitvoeringen_geven_nooit_een_valse_stop(stack: Stack) -> None:
    """Proef N2 van de herreview als vaste lus: acht draden vragen onaangemeld de status op en twee de pagina,
    terwijl de Hub veertig herstarts na elkaar aanbiedt. Elke herstart slaagt en de executor stopt nooit."""
    hub, c, nas = stack
    stop = threading.Event()
    opvragen = {"n": 0}
    slot = threading.Lock()

    def vloed(pad: str) -> None:
        cl = TestClient(c.app, base_url=BASE)
        while not stop.is_set():
            cl.get(pad)
            with slot:
                opvragen["n"] += 1

    draden = [threading.Thread(target=vloed, args=("/api/v1/status",), daemon=True) for _ in range(8)]
    draden += [threading.Thread(target=vloed, args=("/",), daemon=True) for _ in range(2)]
    for d in draden:
        d.start()
    uit: list[tuple[int, str]] = []
    try:
        for _ in range(40):
            r = execute(c, hub, herstart(hub, nas))
            uit.append((r.status_code, str(r.json().get("status") or r.json().get("code"))))
            if r.status_code != 200:
                break
    finally:
        stop.set()
        for d in draden:
            d.join(10)
    assert uit == [(200, "uitgevoerd")] * 40, uit[-3:]
    assert opvragen["n"] > 0
    assert journaal(hub).stopped() is None and writes(nas).count("app.redeploy") == 40
    assert {s for s, _d in rijen(hub)} == {"uitgevoerd"}


# ------------------------------------------------------------------ R-VEILIG-H2: journaalfout vóór de schrijfaanroep
def test_journaalfout_voor_de_schrijfaanroep_sluit_de_rij_als_mislukt_zonder_stop(
    stack: Stack, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Proef N7 van de herreview: bij ``app.update`` valt het journaal weg vóór de schrijfaanroep (bewaren van de
    vorige waarden en het einde van de rij falen). Er is aantoonbaar niets naar TrueNAS gestuurd: 503 "er is niets
    uitgevoerd". Zodra het journaal terug is, krijgt de rij het einde ``mislukt`` en is er geen stop."""
    hub, c, nas = stack
    assert execute(c, hub, approved(hub, install_prop())).status_code == 200
    echt_save, echt_finish = Journal.save_values, Journal.finish
    kapot = {"aan": True}

    def save(self: Journal, *a: Any, **k: Any) -> Any:
        if kapot["aan"]:
            raise JournalUnavailable("OperationalError")
        return echt_save(self, *a, **k)

    def finish(self: Journal, *a: Any, **k: Any) -> Any:
        if kapot["aan"]:
            raise JournalUnavailable("OperationalError")
        return echt_finish(self, *a, **k)

    monkeypatch.setattr(Journal, "save_values", save)
    monkeypatch.setattr(Journal, "finish", finish)
    prop = app_prop(nas, "app.update", "demo-app", {"image": {"repository": REPO, "tag": f"1.2.4@{DIGEST_B}"}})
    r = execute(c, hub, approved(hub, prop))
    assert r.status_code == 503 and r.json()["code"] == "journaal_niet_beschikbaar", r.text
    assert "niets uitgevoerd" in r.json()["message"] and writes(nas) == ["app.create"]
    kapot["aan"] = False
    r = execute(c, hub, herstart(hub, nas))
    assert r.status_code == 200 and r.json()["status"] == "uitgevoerd", r.text
    assert rijen(hub) == [("uitgevoerd", ""), ("mislukt", "JournalUnavailable"), ("uitgevoerd", "")]
    assert journaal(hub).stopped() is None and c.get("/api/v1/status").json()["gestopt"] is None


# ------------------------------------------------------------------ R-VEILIG-3: diep geneste JSON
def test_diep_geneste_json_geeft_422_en_de_executor_blijft_werken(stack: Stack) -> None:
    hub, c, nas = stack
    c = TestClient(create_app(hub.settings), base_url=BASE, raise_server_exceptions=False)
    for body in (b"[" * 200000, b'{"a":' * 100000 + b"1" + b"}" * 100000):
        r = c.post(
            "/api/v1/execute",
            content=body,
            headers={**auth(hub.jwt(), str(uuid.uuid4())), "Content-Type": "application/json"},
        )
        assert r.status_code == 422 and r.json()["code"] == "validation_error", r.text[:200]
    assert writes(nas) == [] and nas.logins == 0
    assert execute(c, hub, herstart(hub, nas)).status_code == 200


# ------------------------------------------------------------------ R-VEILIG-4: geen fouttekst van TrueNAS in journaal
def test_fouttekst_van_truenas_komt_niet_in_het_journaal(stack: Stack, caplog: pytest.LogCaptureFixture) -> None:
    """Proef J van R-VEILIG: een mislukte ``app.update``-job waarvan de fouttekst van TrueNAS de waarde van een
    omgevingsvariabele noemt. Het journaal (ook via de Hub-route) en ``/appdata`` bevatten alleen de code en de
    jobstatus, nooit die tekst."""
    hub, c, nas = stack
    geheim = "GEHEIM-" + uuid.uuid4().hex
    caplog.set_level("DEBUG")
    assert (
        execute(c, hub, approved(hub, install_prop(envs=[{"name": "PROEF_INSTELLING", "value": geheim}]))).status_code
        == 200
    )
    nas.fail["app.update"] = f"values.envs.0.value: '{geheim}' ongeldig"
    upd = approved(
        hub, app_prop(nas, "app.update", "demo-app", {"image": {"repository": REPO, "tag": f"1.2.4@{DIGEST_B}"}})
    )
    r = execute(c, hub, upd)
    assert r.status_code == 502 and r.json()["code"] == "uitvoering_mislukt" and geheim not in r.text, r.text
    jr = c.get(f"/api/v1/executions/{upd['approval']['request_id']}", headers=auth(hub.jwt()))
    assert jr.status_code == 200 and geheim not in jr.text
    assert jr.json()["uitvoeringen"][0]["detail"] == "job_mislukt [FAILED]"
    ruw = b"".join(p.read_bytes() for p in Path(hub.settings.data_dir).rglob("*") if p.is_file())
    assert geheim.encode() not in ruw
    assert geheim not in "\n".join(rec.getMessage() for rec in caplog.records)


def test_nasfout_draagt_de_vrije_tekst_niet_als_tekst_mee() -> None:
    """``str(NasFout)`` is alleen de code; de foutnaam alleen in de vorm van een foutnaam (R-VEILIG-4)."""
    exc = NasFout("truenas_fout", "app.update: [EINVAL] waarde 'GEHEIM' ongeldig", errname="EINVAL")
    assert str(exc) == "truenas_fout" and exc.errname == "EINVAL"
    assert NasFout("truenas_fout", "x", errname="geheim met spaties").errname == ""
