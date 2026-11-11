"""Executor: verzoekgrootte (§5), jti-replaycache (§4.6), Idempotency-Key en rollen (§4.2) op de muterende route
``POST /connector/v1/hub-link/unlink``. Negatieve scenario's: chunked > 1 MiB vóór aanmelding, hergebruikte jti (ook
na een herstart), rol 'kind' wint, onbruikbare replaycache → 503 (fail-closed), JWT uit de toekomst."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

import pytest
from executorhelpers import AUD, UNLINK, Hub, signed
from executorhelpers import auth as _auth
from executorhelpers import b64 as _b64
from executorhelpers import client as _client
from policyhelpers import HOST, proposal

from executor.hublink import AuthFailed, HubLinkStore, verify_hub_jwt
from executor.replay import ReplayCache, ReplayUnavailable


@pytest.fixture
def hub(tmp_path: Path) -> Hub:
    return Hub(tmp_path / "appdata")


def _chunks(total: int) -> Any:
    sent = 0
    while sent < total:
        n = min(64 * 1024, total - sent)
        sent += n
        yield b"x" * n


# ------------------------------------------------------------------ verzoekgrootte (§5)
def test_413_voor_routering_en_aanmelding_ook_chunked(hub: Hub) -> None:
    c = _client(hub)
    over = 1024 * 1024 + 1
    for method, path in (("POST", UNLINK), ("POST", "/koppelen"), ("POST", "/api/v1/execute"), ("PUT", "/bestaat")):
        r = c.request(method, path, content=_chunks(over), headers={"content-type": "application/json"})
        assert r.status_code == 413, f"{method} {path}: {r.status_code} {r.text[:120]}"
        assert r.json()["code"] == "payload_too_large" and r.json()["details"] == {"max_bytes": 1048576}
        assert r.json()["trace_id"]
        r = c.request(method, path, content=b"x" * over)  # met Content-Length: direct geweigerd
        assert r.status_code == 413, f"{method} {path} (Content-Length): {r.status_code}"
    # Precies 1 MiB mag door: de route beslist (zonder Hub-JWT → 401 met reden).
    r = c.post(UNLINK, content=_chunks(1024 * 1024))
    assert r.status_code == 401 and r.json()["details"]["reason"] == "invalid_token"
    assert c.get("/healthz").status_code == 200


# ------------------------------------------------------------------ jti-replay en idempotency (§4.6, §5)
def test_unlink_vraagt_idempotency_key_en_weigert_hergebruikte_jti(hub: Hub) -> None:
    c = _client(hub)
    token, key = hub.jwt(), str(uuid.uuid4())
    r = c.post(UNLINK, headers=_auth(token))
    assert r.status_code == 400 and r.json()["code"] == "idempotency_key_required"
    # Contract 1.3 §4.6: elke POST verbruikt de jti, ook zonder Idempotency-Key (geen exacte herhaling mogelijk).
    r = c.post(UNLINK, headers=_auth(token, key))
    assert r.status_code == 401 and r.json()["details"]["reason"] == "token_replayed"
    r = c.post(UNLINK, headers=_auth(hub.jwt(), "geen-uuid"))
    assert r.status_code == 400 and r.json()["code"] == "idempotency_key_invalid"
    token, key = hub.jwt(), str(uuid.uuid4())
    first = c.post(UNLINK, headers=_auth(token, key))
    assert first.status_code == 501 and first.json()["code"] == "capability_unavailable"
    # Exacte herhaling (zelfde jti, methode, pad en key): het opgeslagen antwoord, geen tweede uitvoering.
    again = c.post(UNLINK, headers=_auth(token, key))
    assert again.status_code == 501 and again.headers["Idempotent-Replay"] == "true"
    assert again.json() == first.json()
    # Zelfde jti voor een andere mutatie (andere key) → 401 token_replayed.
    r = c.post(UNLINK, headers=_auth(token, str(uuid.uuid4())))
    assert r.status_code == 401 and r.json()["details"]["reason"] == "token_replayed"
    # Lezen met dezelfde JWT mag binnen de levensduur vaker.
    for _ in range(3):
        assert c.get("/connector/v1/hub-link", headers=_auth(token)).status_code == 200
    # Persistent: ook na een herstart (nieuwe app op dezelfde /appdata) blijft de jti gebruikt.
    restarted = _client(hub)
    r = restarted.post(UNLINK, headers=_auth(token, str(uuid.uuid4())))
    assert r.status_code == 401 and r.json()["details"]["reason"] == "token_replayed"
    # Een nieuwe JWT (nieuwe jti) is gewoon een nieuwe mutatie.
    assert restarted.post(UNLINK, headers=_auth(hub.jwt(), str(uuid.uuid4()))).status_code == 501
    assert hub.settings.replay_db.stat().st_mode & 0o077 == 0  # 0600


def test_replaycache_onbruikbaar_is_fail_closed(hub: Hub) -> None:
    hub.settings.replay_db.mkdir()  # een map waar een database hoort: SQLite kan niet openen
    c = _client(hub)
    r = c.post(UNLINK, headers=_auth(hub.jwt(), str(uuid.uuid4())))
    assert r.status_code == 503 and r.json()["code"] == "replay_check_unavailable"
    # Lezen hangt niet van de replaycache af.
    assert c.get("/connector/v1/hub-link", headers=_auth(hub.jwt())).status_code == 200


def test_rollen_kind_wint_en_admin_voor_ontkoppelen(hub: Hub) -> None:
    c = _client(hub)
    assert c.get("/connector/v1/hub-link", headers=_auth(hub.user_jwt(["viewer"]))).status_code == 200
    # 'kind' wint altijd van andere rollen in dezelfde JWT (§4.2); onbekende rollen tellen niet.
    for roles in (["kind", "admin"], ["kind"], ["onbekend"], []):
        r = c.get("/connector/v1/hub-link", headers=_auth(hub.user_jwt(roles)))
        assert r.status_code == 403, roles
    for roles in (["viewer"], ["operator"], ["admin", "kind"]):
        r = c.post(UNLINK, headers=_auth(hub.user_jwt(roles), str(uuid.uuid4())))
        assert r.status_code == 403 and r.json()["code"] == "forbidden", roles
    assert c.post(UNLINK, headers=_auth(hub.user_jwt(["admin"]), str(uuid.uuid4()))).status_code == 501


def test_niet_gekoppeld_of_andere_sleutel_ook_op_de_mutatie(hub: Hub, tmp_path: Path) -> None:
    c = _client(hub)
    # Gewisselde Hub-sleutel: onbekende kid → unknown_key; zelfde kid met een andere sleutel → invalid_token.
    other = Hub(tmp_path / "ander")
    forged = other.jwt(service_id=hub.sid)
    r = c.post(UNLINK, headers=_auth(forged, str(uuid.uuid4())))
    assert r.status_code == 401 and r.json()["details"]["reason"] == "invalid_token"
    head = _b64(json.dumps({"alg": "EdDSA", "typ": "JWT", "kid": "nieuwe-kid"}).encode())
    body = forged.split(".")[1]
    unknown = f"{head}.{body}.{_b64(other.key.sign(f'{head}.{body}'.encode()))}"
    r = c.post(UNLINK, headers=_auth(unknown, str(uuid.uuid4())))
    assert r.status_code == 401 and r.json()["details"]["reason"] == "unknown_key"
    with HubLinkStore(hub.settings.secrets_dir).update() as link:
        link.update(state="ontkoppeld", service_token=None, pins=None)
    r = c.post(UNLINK, headers=_auth(hub.jwt(), str(uuid.uuid4())))
    assert r.status_code == 401 and r.json()["details"]["reason"] == "not_linked"


def test_jwt_uit_de_toekomst_of_met_bool_tijden_is_ongeldig(hub: Hub) -> None:
    link = HubLinkStore(hub.settings.secrets_dir).read()
    t = int(time.time())
    for change in ({"iat": t + 300, "nbf": t, "exp": t + 360}, {"iat": True}, {"exp": t - 10, "iat": t}):
        with pytest.raises(AuthFailed) as exc:
            verify_hub_jwt(hub.jwt(**change), link, audience=AUD)
        assert exc.value.reason == "invalid_token", change


def test_replaycache_ruimt_op_na_exp_plus_speling(tmp_path: Path) -> None:
    cache = ReplayCache(tmp_path / "r.sqlite3")
    kw: dict[str, Any] = {
        "iss": "hub",
        "jti": "j1",
        "exp": 1000,
        "method": "POST",
        "path": "/x",
        "idempotency_key": "k",
    }
    assert cache.claim(**kw, now=900).kind == "new"
    assert cache.claim(**kw, now=901).kind == "in_progress"  # nog geen opgeslagen antwoord
    cache.store_result(iss="hub", jti="j1", status=501, body={"code": "capability_unavailable"})
    repeat = cache.claim(**kw, now=902)
    assert repeat.kind == "repeat" and repeat.status == 501 and repeat.body == {"code": "capability_unavailable"}
    assert cache.claim(**{**kw, "path": "/y"}, now=903).kind == "replayed"
    # Na exp + 30 s is de rij weg (de JWT zelf is dan verlopen: token_expired vóór deze controle).
    assert cache.claim(**{**kw, "path": "/y"}, now=1031).kind == "new"
    with pytest.raises(ReplayUnavailable):
        ReplayCache(tmp_path / "bestaat-niet" / "r.sqlite3").claim(**kw)


# ------------------------------------------------------------------ contract 1.3 §4.2, §4.6, §4.7 (C1.3-ASM-04)
def test_aud_als_lijst_en_header_zonder_kid(hub: Hub) -> None:
    c = _client(hub)
    # aud is precies één string: een lijst — ook met de eigen app_id erin — is invalid_token (§4.2).
    for aud in ([AUD], [AUD, "home-control-hub"]):
        r = c.get("/connector/v1/hub-link", headers=_auth(hub.jwt(aud=aud)))
        assert r.status_code == 401 and r.json()["details"]["reason"] == "invalid_token", aud
    # Een JWS-header zonder kid → unknown_key (§4.7).
    r = c.get("/connector/v1/hub-link", headers=_auth(hub.jwt(header={"alg": "EdDSA", "typ": "JWT"})))
    assert r.status_code == 401 and r.json()["details"]["reason"] == "unknown_key"


@pytest.mark.parametrize("header", [None, "Basic dXNlcjpwdw==", "Bearer", "Bearer   ", "Token abc"])
def test_geen_header_ander_schema_of_lege_waarde_is_invalid_token(hub: Hub, header: str | None) -> None:
    c = _client(hub)
    headers = {} if header is None else {"Authorization": header}
    r = c.get("/connector/v1/hub-link", headers=headers)
    assert r.status_code == 401 and r.json()["details"]["reason"] == "invalid_token"


def test_state_komt_voor_de_header(hub: Hub) -> None:
    """Controlevolgorde §4.7: 1 MiB → state → tokensoort. Niet gekoppeld zonder header → not_linked."""
    with HubLinkStore(hub.settings.secrets_dir).update() as link:
        link.update(state="ingetrokken", service_token=None)
    c = _client(hub)
    assert c.get("/connector/v1/hub-link").json()["details"]["reason"] == "revoked"
    with HubLinkStore(hub.settings.secrets_dir).update() as link:
        link.update(state="ontkoppeld")
    assert c.post(UNLINK).json()["details"]["reason"] == "not_linked"


def test_authenticatie_voor_rol_idempotency_en_body(hub: Hub) -> None:
    """RV9: zonder geldige authenticatie altijd 401, ook bij een ongeldige body of een ontbrekende Idempotency-Key."""
    c = _client(hub)
    for path in (UNLINK, "/api/v1/execute"):
        r = c.post(path, content=b"{geen json", headers={"content-type": "application/json"})
        assert r.status_code == 401 and r.json()["details"]["reason"] == "invalid_token", path
        r = c.post(path, json={"onbekend": 1}, headers=_auth(hub.jwt(aud="andere-app")))
        assert r.status_code == 401, path


def test_execute_eerst_aanmelden_dan_sleutel_dan_body_en_weigert_alles(tmp_path: Path) -> None:
    hub = Hub(tmp_path / "appdata", allow_writable_policy=True)
    c = _client(hub)
    # Gebruikers-JWT (ook admin) kan geen acties aanbieden: alleen de Hub met een dienst-JWT.
    admin = _auth(hub.user_jwt(["admin"]), str(uuid.uuid4()))
    r = c.post("/api/v1/execute", json={"action_id": "app.restart"}, headers=admin)
    assert r.status_code == 403 and r.json()["code"] == "forbidden"
    r = c.post("/api/v1/execute", json={"action_id": "app.restart"}, headers=_auth(hub.jwt()))
    assert r.status_code == 400 and r.json()["code"] == "idempotency_key_required"
    # Geen JSON-object → validation_error; een object dat geen ondertekend ExecutionRequest is → geweigerd.
    for inhoud in (b"{geen json", b"[1, 2]"):
        kop = {**_auth(hub.jwt(), str(uuid.uuid4())), "content-type": "application/json"}
        r = c.post("/api/v1/execute", content=inhoud, headers=kop)
        assert r.status_code == 422 and r.json()["code"] == "validation_error", inhoud
    for los in ({"zonder": "action_id"}, {"action_id": "app.restart"}, {"action_id": "shell.exec"}):
        r = c.post("/api/v1/execute", json=los, headers=_auth(hub.jwt(), str(uuid.uuid4())))
        assert r.status_code == 422 and r.json()["code"] == "execution_request_ongeldig", los
    # Ook mét geldige handtekening van de Hub blijft een verboden actie geweigerd; de herhaling geeft hetzelfde
    # antwoord (Idempotent-Replay) en voert niets opnieuw uit.
    token, key = hub.jwt(), str(uuid.uuid4())
    verzoek = signed(hub, proposal("shell.exec", {"host_id": HOST}), risk_class="R3")
    first = c.post("/api/v1/execute", json=verzoek, headers=_auth(token, key))
    assert first.status_code == 403 and first.json()["code"] == "actie_geweigerd", first.text
    again = c.post("/api/v1/execute", json=verzoek, headers=_auth(token, key))
    assert again.status_code == 403 and again.headers["Idempotent-Replay"] == "true"
    assert again.json() == first.json()
    # Geen tweede uitvoering met dezelfde jti voor een andere mutatie.
    r = c.post(UNLINK, headers=_auth(token, key))
    assert r.status_code == 401 and r.json()["details"]["reason"] == "token_replayed"


def test_execute_zonder_alleen_lezen_beleid_voert_niets_uit(hub: Hub) -> None:
    """In de ontwikkelboom is ``policy/`` beschrijfbaar: zonder de expliciete ontwikkelinstelling weigert de executor
    alles (fail-closed), ook een correct ondertekend verzoek."""
    c = _client(hub)
    verzoek = signed(hub, proposal("app.restart", {"host_id": HOST, "app_id": "my-house"}), risk_class="R1")
    r = c.post("/api/v1/execute", json=verzoek, headers=_auth(hub.jwt(), str(uuid.uuid4())))
    assert r.status_code == 503 and r.json()["code"] == "policy_niet_read_only", r.text


# ------------------------------------------------------------------ statische Idempotency-Key-test (§5, C1.3-ASM-14)
EXEMPT = {
    # Formulier-POST van een statuspagina: een browserformulier kan geen header meesturen; bescherming via het
    # formuliertoken, de herkomstcontrole, de pogingenlimiet, koppelen_bezig en de eenmaligheid van de koppelcode.
    "pair": "formulier-POST van de statuspagina (contract 1.3 §5, §3.7, §3.9; RV10)",
    # Idem voor de twee sleutelformulieren (§3.9): dezelfde regels als het koppelformulier, plus een live test van de
    # TrueNAS-schrijfsleutel tegen het vastgelegde NAS-adres en certificaat vóór er iets verandert.
    "write_key": "formulier-POST van de statuspagina (contract 1.3 §5, §3.7, §3.9)",
    "manage": "formulier-POST van de statuspagina (contract 1.3 §5, §3.7, §3.9)",
}


MUTATING = ("post", "put", "patch", "delete")


def _mutating_routes() -> dict[str, Any]:
    import ast

    from executor import app as app_module

    src = Path(app_module.__file__).read_text(encoding="utf-8")
    out: dict[str, Any] = {}
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef) and any(
            isinstance(d, ast.Call)
            and isinstance(d.func, ast.Attribute)
            and d.func.attr in ("post", "put", "patch", "delete")
            for d in n.decorator_list
        ):
            out[n.name] = n
    return out


def test_elke_mutatie_vraagt_idempotency_key_na_de_authenticatie() -> None:
    import ast

    routes = _mutating_routes()
    assert {"pair", "write_key", "manage", "hub_link_unlink", "execute"} <= set(routes)
    missing = []
    for name, fn in routes.items():
        if name in EXEMPT:
            continue
        names = sorted((n.lineno, n.col_offset, n.id) for n in ast.walk(fn) if isinstance(n, ast.Name))
        calls = [name for _, _, name in names]
        # Eerst de authenticatie (verbruikt de jti), daarna pas de sleutelcontrole (§4.7, RV9).
        if "_authenticate" not in calls or "_idempotency_key" not in calls:
            missing.append(name)
        elif calls.index("_authenticate") > calls.index("_idempotency_key"):
            missing.append(f"{name} (volgorde)")
    assert not missing, f"muterende executor-routes zonder Idempotency-Key na authenticatie: {missing}"
    assert set(EXEMPT) <= set(routes), "uitzondering zonder route"
    assert all("contract 1.3 §5" in reden for reden in EXEMPT.values())
