"""Dienst-E2E: afzonderlijke geheime overdracht en koppelketen (contract 1.3 §8.3, M2; S-P2-050e; Sim-getest).

Echte Hub en executor, fake TrueNAS, appstore en planner (zoals ``test_catalogus_installeren``). Een witte-lijstregel
met een appgeheim en een tokenplek maakt de app een koppelbare eigen dienst. Alleen testwaarden, nooit een echte NAS.

Toestandstabel (één test per rij): positief (koppelketen), verkeerd type, verkeerd doel, tokenhergebruik, tweede
claim, ontbrekende ref, extra ref, ander token-veld, andere verzoekhash, verlopen afgifte, kijker- en beheerdersrol,
andere dienst, vreemde handtekening, onbekend veld, ontbrekende plek in de stap, markering bij bijwerken.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import logging
import re
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
import sqlalchemy as sa
from actiehelpers import app_target, keur_goed, schrijfaanroepen, stel_voor, voer_uit
from conftest import enroll_body, login_as, make_user, service_jwk
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from e2e.test_catalogus_installeren import (
    REGEL,
    Keten,
    _plan,
    _stel_voor,
    maak_keten,
    nas,  # noqa: F401 - de fixture
)
from policyhelpers import DIGEST, catalogus_regel, install_params

pytestmark = [pytest.mark.e2e, pytest.mark.integration]

REF = "vault://app/demo-app/app_secret_key"
KLUISREGEL = catalogus_regel(
    manifest_sha256=REGEL["manifest_sha256"],
    schema_sha256=REGEL["schema_sha256"],
    kluisplekken=[
        {"env": "APP_SECRET_KEY", "type": "appgeheim"},
        {"env": "HUB_ENROLLMENT_TOKEN", "type": "enrollment-token"},
    ],
)
KLUISSTAP = install_params(
    "demo-app",
    envs=[
        {"name": "APP_MODE", "value": "prod"},
        {"name": "APP_SECRET_KEY", "value": REF},
    ],
)
APPGEHEIM_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{42}$")
TOKEN_RE = re.compile(r"^enr_[A-Za-z0-9_-]{43}$")


@pytest.fixture
def kluisketen(
    admin: Any,
    app: Any,
    nas: Any,  # noqa: F811
    worker_once: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[Keten]:
    with maak_keten(admin, app, nas, worker_once, tmp_path, monkeypatch, KLUISREGEL, KLUISSTAP) as k:
        yield k


def _voorstel(keten: Keten) -> tuple[dict[str, Any], dict[str, Any]]:
    admin = keten.stack.admin
    r = _plan(admin)
    assert r.status_code == 201, r.text
    plan = r.json()
    r = _stel_voor(admin, plan)
    assert r.status_code == 201, r.text
    v = r.json()
    assert keur_goed(admin, v).status_code == 200
    return plan, v


def _envs(keten: Keten) -> dict[str, str]:
    [create] = keten.stack.nas.created
    return {e["name"]: e["value"] for e in create["values"]["envs"]}


def _met_proef(
    monkeypatch: pytest.MonkeyPatch,
    proef: Callable[[Any, dict[str, Any], dict[str, Any]], None],
) -> None:
    """Draai ``proef(kluis, link, rest)`` tijdens de echte uitvoering, vlak vóór de echte opvraag (verzoek is bezig)."""
    from executor.kluis import Kluis

    origineel = Kluis._vraag_op

    def met_proef(self: Kluis, link: Any, request: Any, binding: Any) -> Any:
        proef(self, link, self.opvraag(request, binding, X25519PrivateKey.generate()))
        return origineel(self, link, request, binding)

    monkeypatch.setattr(Kluis, "_vraag_op", met_proef)


def _scan(keten: Keten, app: Any, geheimen: list[str], hashes: list[str], teksten: list[str]) -> None:
    """Positief bewijs dat de waarden nergens staan: Hub-tabellen, executor-datamap, antwoorden en logregels."""
    zoek = [
        *geheimen,
        *(base64.b64encode(g.encode()).decode() for g in geheimen),
        *hashes,
    ]
    with app.state.sessionmaker() as db:
        tabellen = list(db.execute(sa.text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")).scalars())
        assert "app_geheim" in tabellen and "kluis_afgifte" in tabellen
        for tabel in tabellen:
            sql = f'SELECT EXISTS (SELECT 1 FROM "{tabel}" r WHERE strpos(to_jsonb(r)::text, :m) > 0)'  # noqa: S608
            for m in zoek:
                assert db.execute(sa.text(sql), {"m": m}).scalar_one() is False, tabel
    ruw = b"".join(p.read_bytes() for p in Path(keten.stack.ex_settings.data_dir).rglob("*") if p.is_file())
    for m in zoek:
        assert m.encode() not in ruw
        for tekst in teksten:
            assert m not in tekst


def test_koppelketen_vult_geheim_en_token_in_en_het_token_koppelt_eenmalig(
    kluisketen: Keten, app: Any, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    keten, admin = kluisketen, kluisketen.stack.admin
    plan, v = _voorstel(keten)
    hub_fp = app.state.keyring().keyset_fingerprint()
    assert plan["koppeling"]["soort"] == "volledig" and plan["koppeling"]["hub_key_fingerprint"] == hub_fp
    from hub.models import ActionRequest

    with app.state.sessionmaker() as db:
        gebonden = db.get(ActionRequest, uuid.UUID(v["request_id"])).parameters["catalog_binding"]
    assert [{k: r[k] for k in ("path", "parameter", "ref")} for r in gebonden["vault_refs"]] == [
        {"path": "values.envs[1].value", "parameter": "app_secret_key", "ref": REF}
    ]
    r = voer_uit(admin, v)
    assert r.status_code == 200 and r.json()["status"] == "uitgevoerd", r.text
    assert schrijfaanroepen(keten.stack.nas) == ["app.create"]
    envs = _envs(keten)
    geheim, token = envs["APP_SECRET_KEY"], envs["HUB_ENROLLMENT_TOKEN"]
    assert APPGEHEIM_RE.fullmatch(geheim) and TOKEN_RE.fullmatch(token) and len(token) == 47
    assert envs["HUB_URL"] == plan["koppeling"]["hub_url"] and envs["HUB_KEY_FINGERPRINT"] == hub_fp
    assert envs["APP_MODE"] == "prod"

    # Het token koppelt de dienst één keer (§3.4/§3.6); daarna is het waardeloos.
    r = admin.post(
        "/api/v1/services/enroll",
        json=enroll_body("demo-app", token=token, jwk=service_jwk(b"\x31" * 32)),
    )
    assert r.status_code == 200, r.text
    svc_token = r.json()["service_token"]
    assert admin.get("/api/v1/services/self", headers={"Authorization": f"Bearer {svc_token}"}).status_code == 200
    r = admin.post(
        "/api/v1/services/enroll",
        json=enroll_body("demo-app", token=token, jwk=service_jwk(b"\x32" * 32)),
    )
    assert r.status_code == 401 and r.json()["code"] == "invalid_enrollment", r.text
    with app.state.sessionmaker() as db:
        grant = db.execute(sa.text("SELECT secret_hash, used_at FROM enrollment_grant WHERE app_id = 'demo-app'")).one()
        assert grant.secret_hash == hashlib.sha256(token.encode()).hexdigest() and grant.used_at is not None
        assert db.execute(sa.text("SELECT claimed_at FROM kluis_afgifte")).scalar_one() is not None

    teksten = [
        r.text,
        json.dumps(admin.get(f"/api/v1/actions/{v['request_id']}").json()),
        json.dumps(admin.get(f"/api/v1/catalog/plans/{plan['plan_id']}").json()),
        caplog.text,
    ]
    # De SHA-256 van het token staat (alleen) in enrollment_grant; die van het appgeheim nergens.
    _scan(
        keten,
        app,
        [geheim, token],
        [hashlib.sha256(geheim.encode()).hexdigest()],
        teksten,
    )
    # Positief bewijs dat de zoektocht werkt: dezelfde zoekvraag vindt de tokenhash wel waar die hoort (V-003).
    with app.state.sessionmaker() as db:
        sql = "SELECT EXISTS (SELECT 1 FROM enrollment_grant r WHERE strpos(to_jsonb(r)::text, :m) > 0)"
        assert db.execute(sa.text(sql), {"m": hashlib.sha256(token.encode()).hexdigest()}).scalar_one() is True
    # Markering: plekken met ref en revisie in het journaal van de executor, nooit een waarde.
    from executor.journal import Journal

    s = keten.stack.ex_settings
    assert Journal(s.replay_db, s.secrets_dir).kluis_gemarkeerd("demo-app")

    # Bijwerken met image of terugzetten weigert de Hub vóór alles op deze instantie (§8.3).
    r = stel_voor(
        admin,
        "app.update",
        app_target("demo-app"),
        {"image": {"repository": "x", "tag": f"1@{DIGEST}"}},
    )
    assert r.status_code == 409 and r.json()["code"] == "kluisplekken_recept_ontbreekt", r.text
    r = stel_voor(
        admin,
        "app.rollback",
        app_target("demo-app"),
        {"herstel_van": str(uuid.uuid4())},
    )
    assert r.status_code == 409 and r.json()["code"] == "kluisplekken_recept_ontbreekt", r.text
    assert "app.config" not in keten.stack.nas.mutations


def test_verwisseld_type_weigert_de_executor_zonder_schrijfaanroep(
    kluisketen: Keten, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verkeerd type: de Hub geeft het token op de appgeheim-plek en omgekeerd; de executor toetst de eigen regel."""
    from hub.catalog import kluis

    origineel = kluis._klare_tekst

    def verwisseld(waarden: Any, token: Any) -> bytes:
        [pad] = waarden
        return origineel({pad: token}, waarden[pad])

    monkeypatch.setattr(kluis, "_klare_tekst", verwisseld)
    _p, v = _voorstel(kluisketen)
    r = voer_uit(kluisketen.stack.admin, v)
    assert r.status_code == 409 and r.json()["details"]["executor"]["code"] == "kluis_vorm_ongeldig", r.text
    assert kluisketen.stack.nas.created == [] and schrijfaanroepen(kluisketen.stack.nas) == []


AFWIJKINGEN: list[tuple[str, Callable[[dict[str, Any]], None], int, str]] = [
    ("verkeerd doel", lambda b: b.update(instance_id=str(uuid.uuid4())), 409, "afgifte_past_niet"),
    ("ander verzoek", lambda b: b.update(request_id=str(uuid.uuid4())), 409, "afgifte_past_niet"),
    ("andere verzoekhash", lambda b: b.update(request_sha256="sha256:" + "0" * 64), 409, "afgifte_past_niet"),
    ("andere nonce", lambda b: b.update(nonce=str(uuid.uuid4())), 409, "afgifte_past_niet"),
    ("ontbrekende ref", lambda b: b.update(refs=[]), 409, "afgifte_past_niet"),
    ("extra ref", lambda b: b["refs"].append({**b["refs"][0], "revision": str(uuid.uuid4())}), 409,
     "afgifte_past_niet"),
    ("andere revisie", lambda b: b["refs"][0].update(revision=str(uuid.uuid4())), 409, "afgifte_past_niet"),
    ("token niet gevraagd", lambda b: b.update(token=False), 409, "afgifte_past_niet"),
    ("onbekend veld", lambda b: b.update(type="appgeheim"), 422, "validation_error"),
]  # fmt: skip


@pytest.mark.parametrize(("naam", "wijzig", "status", "code"), AFWIJKINGEN, ids=[a[0] for a in AFWIJKINGEN])
def test_afwijkende_opvraag_krijgt_niets_en_de_echte_slaagt_daarna(
    kluisketen: Keten,
    monkeypatch: pytest.MonkeyPatch,
    naam: str,
    wijzig: Any,
    status: int,
    code: str,
) -> None:
    gezien: list[Any] = []

    def proef(kluis: Any, link: Any, rest: dict[str, Any]) -> None:
        b = copy.deepcopy(rest)
        wijzig(b)
        res = kluis.stuur(link, b)
        gezien.append((res.status, (res.body or {}).get("code"), json.dumps(res.body)))

    _met_proef(monkeypatch, proef)
    _p, v = _voorstel(kluisketen)
    r = voer_uit(kluisketen.stack.admin, v)
    [(st, cd, body)] = gezien
    assert (st, cd) == (status, code), (naam, body)
    assert '"afgifte":' not in body
    # Een afgewezen opvraag claimt niets: de echte opvraag daarna krijgt de waarden nog.
    assert r.status_code == 200 and r.json()["status"] == "uitgevoerd", r.text


def test_tweede_claim_krijgt_niets(kluisketen: Keten, monkeypatch: pytest.MonkeyPatch) -> None:
    """Tokenhergebruik en herhaling: na de geslaagde claim krijgt elke volgende (geldig ondertekende) opvraag niets."""
    from executor.kluis import Kluis

    gezien: list[tuple[int, Any, str]] = []
    origineel = Kluis._vraag_op

    def daarna(self: Kluis, link: Any, request: Any, binding: Any) -> Any:
        uit = origineel(self, link, request, binding)
        res = self.stuur(link, self.opvraag(request, binding, X25519PrivateKey.generate()))
        gezien.append((res.status, (res.body or {}).get("code"), json.dumps(res.body)))
        return uit

    monkeypatch.setattr(Kluis, "_vraag_op", daarna)
    _p, v = _voorstel(kluisketen)
    r = voer_uit(kluisketen.stack.admin, v)
    assert r.status_code == 200, r.text
    [(status, code, body)] = gezien
    assert (status, code) == (
        409,
        "afgifte_al_geclaimd",
    ) and '"afgifte":' not in body, body
    with kluisketen.stack.app.state.sessionmaker() as db:
        assert db.execute(sa.text("SELECT count(*) FROM enrollment_grant WHERE app_id = 'demo-app'")).scalar_one() == 1


def test_handtekening_van_een_andere_sleutel_wordt_geweigerd(
    kluisketen: Keten, monkeypatch: pytest.MonkeyPatch
) -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    gezien: list[Any] = []

    def proef(kluis: Any, link: Any, rest: dict[str, Any]) -> None:
        pem = Ed25519PrivateKey.generate().private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        echt = kluis._identiteit
        kluis._identiteit = lambda: serialization.load_pem_private_key(pem, password=None)
        try:
            res = kluis.stuur(link, rest)
        finally:
            kluis._identiteit = echt
        gezien.append((res.status, (res.body or {}).get("code")))

    _met_proef(monkeypatch, proef)
    _p, v = _voorstel(kluisketen)
    assert voer_uit(kluisketen.stack.admin, v).status_code == 200
    assert gezien == [(403, "afgifte_geweigerd")]


def test_verlopen_afgifte_geeft_niets_en_geen_installatie(kluisketen: Keten, app: Any, monkeypatch: Any) -> None:
    from datetime import timedelta

    from hub.catalog import kluis

    monkeypatch.setattr(kluis, "AFGIFTE_MAX", timedelta(seconds=-1))
    _p, v = _voorstel(kluisketen)
    r = voer_uit(kluisketen.stack.admin, v)
    assert r.status_code == 409 and r.json()["details"]["executor"]["code"] == "kluis_afgifte_mislukt", r.text
    assert kluisketen.stack.nas.created == []
    with app.state.sessionmaker() as db:
        assert db.execute(sa.text("SELECT claimed_at FROM kluis_afgifte")).scalar_one() is None


@pytest.mark.parametrize("rol", ["viewer", "admin", "andere_dienst"])
def test_geen_gebruiker_of_andere_dienst_haalt_kluiswaarden_op(kluisketen: Keten, app: Any, rol: str) -> None:
    body = {"request_id": str(uuid.uuid4()), "token": True}
    if rol == "andere_dienst":
        r = kluisketen.stack.admin.post("/api/v1/services/enrollment-tokens", json={"app_id": "home-control-hub"})
        tok = r.json()["enrollment_token"]
        r = kluisketen.stack.admin.post("/api/v1/services/enroll", json=enroll_body("home-control-hub", token=tok))
        c = kluisketen.stack.admin
        r = c.post(
            "/api/v1/executor/secret-claims",
            json=_geldige_vorm(),
            headers={"Authorization": f"Bearer {r.json()['service_token']}"},
        )
        assert r.status_code == 403 and r.json()["code"] == "afgifte_geweigerd", r.text
        return
    if rol == "viewer":
        make_user(kluisketen.stack.admin, "kijker", "viewer")
        c = login_as(app, "kijker")
    else:
        c = kluisketen.stack.admin
    r = c.post("/api/v1/executor/secret-claims", json=body)
    assert r.status_code == 401, r.text
    r = c.post("/api/v1/executor/secret-claims", json=_geldige_vorm())
    assert r.status_code == 401 and "afgifte" not in r.json(), r.text


def _geldige_vorm() -> dict[str, Any]:
    u = str(uuid.uuid4())
    return {
        "request_id": u,
        "request_sha256": "sha256:" + "0" * 64,
        "nonce": u,
        "approval_id": u,
        "instance_id": u,
        "refs": [],
        "token": True,
        "ontvanger": "A" * 43,
        "issued_at": "2026-11-21T10:00:00Z",
        "handtekening": "A" * 86,
    }


def test_stap_zonder_de_kluisplek_geeft_geen_voorstel(
    admin: Any,
    app: Any,
    nas: Any,  # noqa: F811
    worker_once: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ontbrekende ref: de plannerstap noemt de appgeheim-plek niet; de Hub maakt geen revisie en geen voorstel."""
    with maak_keten(
        admin,
        app,
        nas,
        worker_once,
        tmp_path,
        monkeypatch,
        KLUISREGEL,
        install_params("demo-app"),
    ) as k:
        r = _plan(k.stack.admin)
        assert r.status_code == 201, r.text
        r = _stel_voor(k.stack.admin, r.json())
        assert r.status_code == 409 and r.json()["code"] == "plan_stap_onverwacht", r.text
        with app.state.sessionmaker() as db:
            assert db.execute(sa.text("SELECT count(*) FROM app_geheim")).scalar_one() == 0


def test_extra_plek_met_dezelfde_verwijzing_geeft_geen_voorstel(
    admin: Any,
    app: Any,
    nas: Any,  # noqa: F811
    worker_once: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R-VEILIG-4: exact de vastgelegde plekken; een tweede plek met een bekende verwijzing krijgt geen voorstel."""
    stap = copy.deepcopy(KLUISSTAP)
    stap["app_create"]["values"]["envs"].append({"name": "API_TOKEN", "value": REF})
    with maak_keten(admin, app, nas, worker_once, tmp_path, monkeypatch, KLUISREGEL, stap) as k:
        r = _plan(k.stack.admin)
        if r.status_code == 201:
            r = _stel_voor(k.stack.admin, r.json())
        assert r.status_code in (409, 422), r.text
        assert not schrijfaanroepen(k.stack.nas)
        with app.state.sessionmaker() as db:
            assert db.execute(sa.text("SELECT count(*) FROM kluis_afgifte")).scalar_one() == 0


def test_exp_van_het_afgiftebewijs_blijft_binnen_de_afgifte_na_verwerkingstijd(
    kluisketen: Keten, app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R-VEILIG-3: exp wordt bij ondertekening begrensd op de vastgelegde eindtijd, ook na trage verwerking."""
    import time

    from hub.keys import KeyRing

    _p, v = _voorstel(kluisketen)
    kluis = app.state.vault()
    ontsleutel, onderteken = kluis.decrypt, KeyRing._sign
    gemeten: list[bool] = []

    def traag(ref: str, nonce: Any, pakket: Any) -> Any:
        if ref.startswith("vault://app/"):
            time.sleep(2)
        return ontsleutel(ref, nonce, pakket)

    def meet(self: KeyRing, claims: dict[str, Any]) -> str:
        if "kluis_afgifte" in claims:
            with app.state.sessionmaker() as db:
                einde = db.execute(sa.text("SELECT expires_at FROM kluis_afgifte")).scalar_one()
            gemeten.append(claims["exp"] <= einde.timestamp())
        return onderteken(self, claims)

    monkeypatch.setattr(kluis, "decrypt", traag)
    monkeypatch.setattr(KeyRing, "_sign", meet)
    assert voer_uit(kluisketen.stack.admin, v).status_code == 200
    assert gemeten == [True]


def test_verstreken_venster_bij_ondertekening_geeft_geen_afgiftebewijs(
    kluisketen: Keten, app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R-VEILIG-3: is het einde bij ondertekening voorbij, dan 410 en geen installatie (niet even 1 s extra)."""
    from hub.catalog import kluis as uitgever

    _p, v = _voorstel(kluisketen)
    gezien: list[tuple[int, Any]] = []
    from executor.kluis import Kluis

    sturen = Kluis.stuur

    def volg(self: Kluis, link: Any, rest: Any) -> Any:
        res = sturen(self, link, rest)
        gezien.append((res.status, res.body.get("code") if isinstance(res.body, dict) else None))
        return res

    from datetime import timedelta

    uitgeven = uitgever.KeyRing.issue_hub_service_jwt

    def verlopen(self: Any, **k: Any) -> Any:
        # Alleen het afgiftebewijs: het einde ligt net vóór het moment van ondertekenen (echte begrenzing).
        if k.get("kluis_afgifte") is not None:
            k["uiterlijk"] = uitgever.utcnow() - timedelta(seconds=1)
        return uitgeven(self, **k)

    monkeypatch.setattr(Kluis, "stuur", volg)
    monkeypatch.setattr(uitgever.KeyRing, "issue_hub_service_jwt", verlopen)
    r = voer_uit(kluisketen.stack.admin, v)
    assert r.status_code == 409 and r.json()["details"]["executor"]["code"] == "kluis_afgifte_mislukt", r.text
    assert gezien == [(410, "afgifte_verlopen")] and kluisketen.stack.nas.created == []
