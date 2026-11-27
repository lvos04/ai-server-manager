"""Kosten via de Hub-API, de B14-leesroute, een eigen testdatabase en het echte meldingspad naar nep-Gotify."""

from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import jwt
import pytest
from conftest import idem, login_as, make_user
from fakes.b14_uurreeks import ZONE, uurreeks
from fakes.fake_gotify import FakeGotify
from fakes.fake_http import FakeHTTP, Reply, Seen
from sqlalchemy import func, select

from hub import registry
from hub.keys import TOKEN_USE_USER
from hub.kosten import bronnen
from hub.kosten.overzicht import Kostencijfer, Tijdvak
from hub.models import AuditEvent, Decision, HubSetting, Notification, OutboxEvent, Service
from hub.routers import ai, kosten

pytestmark = pytest.mark.integration
NU = datetime(2026, 10, 25, 14, 30, tzinfo=UTC)
LEES = "/api/v1/kosten"
PARAMS = {"datum": "2026-10-25"}
BUDGET = f"{LEES}/budget"


class B14(FakeHTTP):
    def __init__(self, publiek: Any) -> None:
        super().__init__()
        self.publiek = publiek
        self.zonder_meter = False
        self.geschat = False

    def handle(self, seen: Seen) -> Reply:
        if seen.method != "GET" or seen.path != "/integrations/v1/energy/usage":
            return Reply(404)
        try:
            claims = jwt.decode(
                seen.headers["authorization"].removeprefix("Bearer "),
                self.publiek,
                algorithms=["EdDSA"],
                audience="home-control-hub",
            )
        except (KeyError, jwt.InvalidTokenError):
            return Reply(401)
        if claims["token_use"] != TOKEN_USE_USER or claims["roles"] != ["viewer"] or not claims["sub"]:
            return Reply(403)
        q = seen.query
        data = uurreeks(
            date.fromisoformat(q["date"][0]) if "date" in q else NU.astimezone(ZONE).date(),
            q["period"][0],
            q["role"][0],
            q["direction"][0],
        )
        if self.zonder_meter:
            for dag in data["days"]:
                for uur in dag["hours"]:
                    uur["meter_id"] = None
        if self.geschat:
            for dag in data["days"]:
                for uur in dag["hours"]:
                    uur["usage"]["quality"] = "geschat"
        return Reply(200, data)


@pytest.fixture
def b14(admin: Any, app: Any, monkeypatch: pytest.MonkeyPatch) -> Iterator[B14]:
    bron = B14(app.state.keyring().jwt_signing.public_key())
    bron.start()
    try:
        with app.state.sessionmaker() as db:
            db.add(Service(app_id="home-control-hub", enrolled_via="koppelcode"))
            d14 = db.get(Decision, "D14")
            d14.status, d14.waarde = (
                "Getest",
                {"p1_meter": True, "airco_1fase_meter": True, "energy_socket_boiler_alleen_meten": True},
            )
            db.commit()
        monkeypatch.setattr(registry, "nas_address", lambda db: "localhost")
        monkeypatch.setattr(
            registry,
            "measured_apps",
            lambda db, settings: {
                "status": "ok",
                "data": [
                    {
                        "naam": "home-control-hub",
                        "images": [{"repository": registry.expected_repository("home-control-hub")}],
                        "poorten": [{"container_poort": 30420, "host_poort": bron.port, "protocol": "tcp"}],
                    }
                ],
            },
        )
        monkeypatch.setattr(kosten, "utcnow", lambda: NU)
        yield bron
    finally:
        bron.stop()


def test_leesrecht_meterrol_en_eigenaar(
    admin: Any, app: Any, b14: B14, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    make_user(admin, "kijker", "viewer")
    with login_as(app, "kijker") as kijker:
        assert (
            kijker.put(BUDGET, json={"grens": "10", "valuta": "EUR", "periode": "dag"}, headers=idem()).status_code
            == 403
        )
        assert kijker.get(LEES, params={**PARAMS, "meterrol": "airco_binnen"}).status_code == 422
        nas = kijker.get(LEES, params={**PARAMS, "meterrol": "nas_host"}).json()
        assert nas["totaal"]["verbruik"]["waarde"] is None
        assert b14.paths() == []

        def dubbel(vak: Tijdvak) -> dict[str, Kostencijfer]:
            return {"stroomkosten": Kostencijfer(bron="home-control-hub", tijdvak=vak, waarde=Decimal("75"))}

        monkeypatch.setattr(bronnen, "mso_posten", dubbel)
        with caplog.at_level("INFO", logger="hub.kosten.overzicht"):
            airco = kijker.get(LEES, params={**PARAMS, "meterrol": "airco_outdoor"}).json()
        assert airco["meterrol"] == "airco_outdoor" and "gedeelde buitenunit" in airco["meteromschrijving"]
        assert Decimal(airco["totaal"]["stroomkosten"]["waarde"]) == 4
        assert "dubbele_kostenbron_genegeerd" in caplog.messages
        assert b14.paths() == ["/integrations/v1/energy/usage"]
        b14.zonder_meter = True
        leeg = kijker.get(LEES, params=PARAMS).json()
        assert leeg["totaal"]["verbruik"]["measurement_quality"] == "unknown"
        assert leeg["totaal"]["stroomkosten"]["waarde"] is None
        assert leeg["externe_diensten"]["waarde"] is None and leeg["cloudbudget"]["waarde"] is None
        assert "besparing" not in leeg
        b14.force_status = 403
        vergrendeld = kijker.get(LEES, params=PARAMS).json()
        assert vergrendeld["totaal"]["stroomkosten"]["reden"] == "leesrecht_geweigerd"
        assert set(b14.paths()) == {"/integrations/v1/energy/usage"}
        b14.force_status = None
        b14.zonder_meter = False
        with app.state.sessionmaker() as db:
            db.get(Decision, "D14").status = "Ingevuld"
            db.commit()
        onbevestigd = kijker.get(LEES, params=PARAMS).json()
        assert onbevestigd["totaal"]["stroomkosten"]["reden"] == "meterrol_niet_bevestigd"
        b14.geschat = True
        schatting = kijker.get(LEES, params=PARAMS).json()["totaal"]["stroomkosten"]
        assert schatting["measurement_quality"] == "estimated" and schatting["aanname"]
        assert Decimal(schatting["waarde"]) == 4


def test_cloudbudget_volgt_het_bronplafond_ook_bij_uitgeput_krediet(
    admin: Any, app: Any, settings: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings.ai_enabled = True
    monkeypatch.setattr(ai, "utcnow", lambda: NU)
    monkeypatch.setattr(kosten, "utcnow", lambda: NU)
    with app.state.sessionmaker() as db:
        d09 = db.get(Decision, "D09")
        d09.status, d09.getest_op = "Getest", NU
        d09.waarde = {
            "account_gekoppeld": True,
            "harde_stop": True,
            "overage_toegestaan": False,
            "tegoedmaand": "2026-10",
            "inbegrepen_eenheden": 4,
            "max_eenheden_per_taak": 5,
            "inbegrepen_maandbudget": "EUR 60",
        }
        db.commit()
    saldo = admin.get("/api/v1/ai/providers").json()["tegoed"]
    assert saldo["status"] == "tegoed_op" and saldo["inbegrepen"] == 4
    overzicht = admin.get(LEES, params=PARAMS).json()
    cijfer = overzicht["cloudbudget"]
    assert Decimal(cijfer["waarde"]) == saldo["inbegrepen"] and cijfer["eenheid"] == "kredieteenheden"
    assert cijfer["bron"] == "hub.D09" and cijfer["tijdvak"]["tijdzone"] == "UTC"
    assert overzicht["totaal"]["stroomkosten"]["waarde"] is None
    settings.ai_enabled = False
    assert admin.get(LEES, params=PARAMS).json()["cloudbudget"]["waarde"] is None


def test_budget_vanaf_waarneming_tot_verzending_en_bestaande_data(
    admin: Any, app: Any, b14: B14, periodic_run: Any
) -> None:
    with app.state.sessionmaker() as db:
        bestaand = OutboxEvent(
            event_type="backup.coverage.changed",
            entity_type="proef",
            entity_id="reeds-aanwezig",
            payload={"dekking": "aanwezig"},
        )
        instelling = HubSetting(sleutel="proef.bestaand", waarde={"bewaard": True}, gewijzigd_door="test")
        db.add_all([bestaand, instelling])
        db.commit()
        eerder = (bestaand.seq, bestaand.event_id, bestaand.payload, instelling.waarde, instelling.gewijzigd_op)

    gotify = FakeGotify()
    gotify.start()
    try:
        assert (
            admin.post(
                "/api/v1/notifications/channels",
                json={
                    "naam": "Proef",
                    "basis_url": gotify.url,
                    "token": next(iter(gotify.tokens)),
                },
                headers=idem(),
            ).status_code
            == 201
        )
        sleutel = idem()
        grens = {"grens": "3.99", "valuta": "EUR", "periode": "dag"}
        assert admin.put(BUDGET, json=grens).status_code == 400
        geplaatst = admin.put(BUDGET, json=grens, headers=sleutel)
        assert geplaatst.status_code == 200
        assert admin.put(BUDGET, json=grens, headers=sleutel).headers["Idempotent-Replay"] == "true"
        with app.state.sessionmaker() as db:
            assert (
                db.scalar(
                    select(func.count()).select_from(AuditEvent).where(AuditEvent.action == "kosten.budget_opgeslagen")
                )
                == 1
            )
        assert admin.get(BUDGET).headers["ETag"] == geplaatst.headers["ETag"]
        assert admin.put(BUDGET, json=grens, headers={**idem(), "If-Match": '"verouderd"'}).status_code == 412

        b14.zonder_meter = True
        assert admin.get(LEES, params=PARAMS).json()["budgetstatus"] == "onbekend"
        with app.state.sessionmaker() as db:
            assert db.scalar(select(func.count()).select_from(Notification)) == 0
        b14.zonder_meter = False
        for periode in ("week", "dag"):
            resultaat = admin.get(LEES, params={**PARAMS, "periode": periode}).json()
            assert resultaat["budgetstatus"] == "overschreden"
            assert resultaat["externe_diensten"]["reden"] == "leesroute_niet_vrijgegeven"
        buiten_reeks = admin.get(LEES, params={**PARAMS, "meterrol": "nas_host"}).json()
        assert buiten_reeks["totaal"]["verbruik"]["waarde"] is None and buiten_reeks["budgetstatus"] == "overschreden"
        with app.state.sessionmaker() as db:
            meldingen = list(db.scalars(select(Notification)))
            assert len(meldingen) == 1 and meldingen[0].status == "wachtrij"
        assert periodic_run("meldingen_versturen", now=NU)["meldingen_versturen"]["verzonden"] == 1
        assert len(gotify.messages) == 1 and gotify.messages[0]["title"] == "Stroombudget overschreden"

        for bedrag, valuta, status in [("4.00", "EUR", "binnen_grens"), ("2", "USD", "onbekend"), (None, "EUR", "uit")]:
            assert (
                admin.put(BUDGET, json={**grens, "grens": bedrag, "valuta": valuta}, headers=idem()).status_code == 200
            )
            assert admin.get(LEES, params=PARAMS).json()["budgetstatus"] == status
        with app.state.sessionmaker() as db:
            assert db.scalar(select(func.count()).select_from(Notification)) == 1
            bewaard = db.get(OutboxEvent, eerder[0])
            instelling = db.get(HubSetting, "proef.bestaand")
            assert (
                bewaard.seq,
                bewaard.event_id,
                bewaard.payload,
                instelling.waarde,
                instelling.gewijzigd_op,
            ) == eerder
    finally:
        gotify.stop()
