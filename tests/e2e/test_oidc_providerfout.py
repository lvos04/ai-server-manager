"""Vrije providerdiagnostiek blijft buiten de antwoorden en de database."""

import uuid
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest
from conftest import idem
from e2e import test_oidc_sso
from e2e.test_oidc_sso import callback, configure
from fakes.fake_http import Reply, Seen
from fastapi.testclient import TestClient
from sqlalchemy import select

from hub import audit
from hub.app import create_app
from hub.models import AuditEvent, IdempotencyRecord, OidcConfig
from hub.oidc import service
from hub.oidc.client import b64url

idp = test_oidc_sso.idp
pytestmark = [pytest.mark.e2e, pytest.mark.integration]


@pytest.mark.parametrize("bron", ["token", "callback", "alg"])
def test_providerfout_bewaart_alleen_vaste_reden(
    admin: Any, app: Any, idp: Any, monkeypatch: pytest.MonkeyPatch, bron: str
) -> None:
    configure(admin, idp)
    canary = "ContextmarkeringUitTestprovider"
    echt = idp.handle

    def verzoek(gezien: Seen) -> Reply:
        if bron == "token" and gezien.path.endswith("/token/"):
            return Reply(400, {"error": canary})
        return echt(gezien)

    monkeypatch.setattr(idp, "handle", verzoek)
    if bron == "alg":
        kop = b64url(f'{{"alg":"{canary}"}}'.encode())
        monkeypatch.setattr(idp, "_id_token", lambda _: f"{kop}.e30.c2ln")
    start = admin.post("/api/v1/auth/oidc/test")
    assert start.status_code == 200
    if bron == "callback":
        state = parse_qs(urlsplit(start.json()["autorisatie_url"]).query)["state"][0]
        resultaat = admin.get("/api/v1/auth/oidc/callback", params={"state": state, "error": canary})
        reden = "idp_weigerde"
    else:
        resultaat = callback(admin, idp, start.json()["autorisatie_url"])
        reden = "alg_niet_toegestaan" if bron == "alg" else "token_geweigerd"
    assert resultaat.status_code == 400

    headers = idem()
    mutatie = admin.post("/api/v1/auth/oidc/discover", headers=headers)
    herhaling = admin.post("/api/v1/auth/oidc/discover", headers=headers)
    assert mutatie.status_code == herhaling.status_code == 200
    assert mutatie.json() == herhaling.json()
    beheer = admin.get("/api/v1/auth/oidc")
    with app.state.sessionmaker() as db:
        cfg = db.get(OidcConfig, 1)
        audit = db.scalars(select(AuditEvent.details).where(AuditEvent.action == "auth.oidc.tested")).all()
        idempotentie = db.scalars(select(IdempotencyRecord.response_body)).all()
        assert cfg.laatste_test["reden"] == reden
        assert all(canary[:16] not in str(deel) for deel in (cfg.laatste_test, audit, idempotentie))
    assert all(canary[:16] not in r.text for r in (resultaat, mutatie, herhaling, beheer))


def test_eerste_start_schoont_oude_alg_uitleg_zonder_auditgeschiedenis_te_wijzigen(app: Any, settings: Any) -> None:
    actie = "auth.oidc.alg_uitleg_opgeschoond"
    kanarie = "OudeAlg\n'Kanarie"
    code = "alg_niet_toegestaan"
    oud = {
        "reden": code,
        "uitleg": f"Algoritme '{kanarie}' is niet toegestaan (alleen asymmetrisch).",
    }
    schoon = {**oud, "uitleg": code}
    andere_uitleg = {"reden": code, "uitleg": "Eigen toelichting"}
    andere_reden = {
        "reden": "token_geweigerd",
        "uitleg": "Algoritme 'Behouden' is niet toegestaan (alleen asymmetrisch).",
    }
    andere_route = {
        "reden": code,
        "uitleg": "Algoritme 'AndereRoute' is niet toegestaan (alleen asymmetrisch).",
    }

    rijen = [
        (
            "PUT:/api/v1/auth/oidc",
            {"laatste_test": oud, "versie": 3},
            {"laatste_test": schoon, "versie": 3},
        ),
        (
            "POST:/api/v1/auth/oidc/discover",
            {"oidc": {"laatste_test": oud}},
            {"oidc": {"laatste_test": schoon}},
        ),
        (
            "POST:/api/v1/auth/oidc/inschakelen",
            {"laatste_test": andere_reden},
            {"laatste_test": andere_reden},
        ),
        (
            "PUT:/api/v1/auth/oidc",
            {"laatste_test": andere_uitleg},
            {"laatste_test": andere_uitleg},
        ),
        (
            "PUT:/api/v1/anders",
            {"laatste_test": andere_route},
            {"laatste_test": andere_route},
        ),
    ]
    with app.state.sessionmaker() as db:
        cfg = service.config(db)
        cfg.laatste_test = {
            "resultaat": "mislukt",
            **oud,
            "config_versie": cfg.config_versie,
        }
        cfg.issuer = "https://bewaarde-issuer.invalid"
        db.add_all(
            IdempotencyRecord(
                scope=f"user:test:{route}",
                key=uuid.uuid4(),
                request_hash="0" * 64,
                status_code=200,
                response_body=body,
            )
            for route, body, _ in rijen
        )
        audit.record(
            db,
            actor_type="user",
            actor_id="test",
            action="auth.oidc.tested",
            details=oud,
        )
        db.commit()
        historische_rij = audit.to_dict(db.scalars(select(AuditEvent)).one())
        assert audit.verify(db)["status"] == "intact"

    for _ in range(2):
        with TestClient(create_app(settings)):
            pass
        with app.state.sessionmaker() as db:
            cfg = db.get(OidcConfig, 1)
            assert cfg.laatste_test == {
                "resultaat": "mislukt",
                **schoon,
                "config_versie": 1,
            }
            assert cfg.issuer == "https://bewaarde-issuer.invalid"
            opgeslagen = db.scalars(select(IdempotencyRecord).order_by(IdempotencyRecord.id)).all()
            assert [r.response_body for r in opgeslagen] == [verwacht for _, _, verwacht in rijen]
            assert all(r.request_hash == "0" * 64 for r in opgeslagen)
            assert "OudeAlg" not in str(cfg.laatste_test)
            assert all("OudeAlg" not in str(r.response_body) for r in opgeslagen)
            auditregels = db.scalars(select(AuditEvent).order_by(AuditEvent.ketting_nr)).all()
            assert len(auditregels) == 2
            assert audit.to_dict(auditregels[0]) == historische_rij
            assert kanarie in auditregels[0].details["uitleg"]
            assert auditregels[1].action == actie
            assert auditregels[1].details == {"aantal": 3}
            assert audit.verify(db)["status"] == "intact"
