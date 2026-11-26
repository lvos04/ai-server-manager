"""Dienst-E2E: afzonderlijke geheime overdracht en koppelketen (contract 1.3 §8.3, M2; S-P2-050e; Sim-getest).

Echte Hub en executor, fake TrueNAS, appstore en planner (zoals ``test_catalogus_installeren``). Een witte-lijstregel
met een appgeheim en een tokenplek maakt de app een koppelbare eigen dienst. Alleen testwaarden, nooit een echte NAS.

Toestandstabel (één test per rij): positief (koppelketen), verkeerd type, verkeerd doel, tokenhergebruik, tweede
claim, ontbrekende ref, extra ref, ander token-veld, andere verzoekhash, verlopen afgifte, kijker- en beheerdersrol,
andere dienst, vreemde handtekening, onbekend veld, ontbrekende plek in de stap, markering bij bijwerken.

S-P2-070: de zoektocht na een volledige installatie-run loopt over de Hub-tabellen (ook audit en logs), de
executor-datamap, de preview (de diff), de opgevangen logregels, de uitvoeringsrespons, de versleutelde afgifte en het
antwoord van elke geregistreerde route van Hub en executor, met de vereiste rol (R-VEILIG-1); de bezochte routes moeten
gelijk zijn aan de geregistreerde. Tegenproeven: zonder afscherming en met een markering in een bevoegd antwoord wordt
de zoektocht rood (V-003). Een niet-bestaand kluispad weigert vóór ondertekening.
"""

from __future__ import annotations

import base64
import copy
import dataclasses
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
from conftest import enroll_body, idem, login_as, make_user, service_jwk
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
        *(g.encode().hex() for g in geheimen),  # bytea staat in to_jsonb als hex (S-P2-070, tegenproef V-003)
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


# Geregistreerde routes die de rondgang bewust niet aanroept: (dienst, methode, pad) → reden. Een verouderde regel
# (route bestaat niet meer) laat de rondgang ook falen.
NIET_BEZOCHT: dict[tuple[str, str, str], str] = {}


def _geregistreerd(server: Any) -> set[tuple[str, str]]:
    """Alle geregistreerde routes van een dienst, ook buiten het schema (``/``, formulieren, documentatie)."""
    from fastapi.routing import iter_route_contexts
    from starlette.routing import Route

    routes = list(iter_route_contexts(server.routes))  # ook de routes van ingesloten routers
    vreemd = [r for r in routes if not isinstance(r.original_route, Route)]
    assert not vreemd, vreemd  # een mount of websocket zou ongezien blijven
    return {(m, r.path) for r in routes for m in (r.methods or ()) if m != "HEAD"}


def _vergelijk(dienst: str, server: Any, bezocht: set[tuple[str, str]]) -> None:
    uitgezonderd = {(m, p) for d, m, p in NIET_BEZOCHT if d == dienst}
    routes = _geregistreerd(server)
    assert uitgezonderd <= routes, f"{dienst}: verouderde uitzondering {sorted(uitgezonderd - routes)}"
    assert routes - uitgezonderd == bezocht, (
        f"{dienst}: niet bezocht {sorted(routes - uitgezonderd - bezocht)}; onbekend {sorted(bezocht - routes)}"
    )


def _executor_rondgang(keten: Keten, app: Any, ids: dict[str, str]) -> list[str]:
    """Elke route van de executor met geldige invoer en de vereiste rol: de dienst-JWT van de Hub voor de API, en voor
    de formulieren herkomst + formuliercode + de huidige schrijfsleutel. Vervangen, ontkoppelen, opnieuw koppelen en
    de sleutel opnieuw instellen geven elk een bevoegd 200-antwoord met de volledige statuspagina."""
    import httpx
    from executorhelpers import WRITE_KEY
    from fastapi.routing import APIRoute, iter_route_contexts

    basis = keten.stack.ex_url
    ex = next(s.server.config.app for s in keten.stack.servers if s.url == basis)
    hub_url = next(s.url for s in keten.stack.servers if s.server.config.app is app)
    with app.state.sessionmaker() as db:
        sql = "SELECT id FROM service WHERE app_id = 'ai-server-manager-executor'"
        dienst_id = str(db.execute(sa.text(sql)).scalar_one())

    def dienst() -> dict[str, str]:
        jwt, _ = app.state.keyring().issue_hub_service_jwt(audience="ai-server-manager-executor", service_id=dienst_id)
        return {"Authorization": f"Bearer {jwt}", **idem()}

    rid = ids["request_id"]
    bezocht: set[tuple[str, str]] = set()
    uit: list[str] = []
    c = httpx.Client(base_url=basis, headers={"Origin": basis})

    def roep(methode: str, pad: str, verwacht: int, echt: str | None = None, **kw: Any) -> httpx.Response:
        r = c.request(methode, echt or pad, **kw)
        assert r.status_code == verwacht, f"executor {methode} {pad}: {r.status_code} {r.text[:300]}"
        bezocht.add((methode, pad))
        uit.append(r.text)
        return r

    def formulier(pad: str, velden: dict[str, str], tekst: str) -> None:
        csrf = re.search(r'name="csrf" value="([^"]+)"', uit[-1])
        assert csrf, uit[-1][:300]
        assert tekst in roep("POST", pad, 200, data={"csrf": csrf.group(1), **velden}).text

    with c:
        documentatie = [r.path for r in iter_route_contexts(ex.routes) if not isinstance(r.original_route, APIRoute)]
        for pad in ("/healthz", "/readyz", "/api/v1/status", *documentatie):
            roep("GET", pad, 200)
        roep("GET", "/connector/v1/hub-link", 200, headers=dienst())
        journaal = roep("GET", "/api/v1/executions/{request_id}", 200, f"/api/v1/executions/{rid}", headers=dienst())
        assert journaal.json()["uitvoeringen"], journaal.text  # het gevulde journaal met dienstcontext
        # Bevoegd (dienst-JWT), inhoudelijk geweigerd; de geldige uitvoeringsrespons vangt _voer_uit_en_vang.
        roep("POST", "/api/v1/execute", 422, json={}, headers=dienst())
        roep("POST", "/connector/v1/hub-link/unlink", 501, headers=dienst())  # capability_unavailable volgens §3.9
        roep("GET", "/", 200)
        sleutel = {"truenas_sleutel": WRITE_KEY}
        formulier("/beheer", {**sleutel, "nieuwe_sleutel": WRITE_KEY, "actie": "vervangen"}, "is vervangen")
        formulier("/beheer", {**sleutel, "actie": "ontkoppelen"}, "Ontkoppeld van de Hub")
        # Resetten kan alleen bij een onleesbaar koppelbestand: bevoegd verzoek, vaste melding (volledige pagina).
        csrf = re.search(r'name="csrf" value="([^"]+)"', uit[-1])
        assert csrf, uit[-1][:300]
        reset = {"csrf": csrf.group(1), "bevestiging": "RESETTEN"}
        assert "koppelbestand_leesbaar" in roep("POST", "/koppelbestand-resetten", 409, data=reset).text
        r = keten.stack.admin.post("/api/v1/services/pairing-codes", json={"app_id": "ai-server-manager-executor"})
        assert r.status_code == 201, r.text
        grant = r.json()
        koppel = {
            "hub_adres": hub_url,
            "koppelcode": grant["koppelcode"],
            "hub_vingerafdruk": grant["keyset_fingerprint"],
        }
        formulier("/koppelen", koppel, "Gekoppeld met de Hub")
        formulier("/schrijfsleutel", sleutel, "De schrijfsleutel is getest en opgeslagen")
    _vergelijk("executor", ex, bezocht)
    return uit


def _hub_rondgang(keten: Keten, app: Any, ids: dict[str, str]) -> list[str]:
    """Elke geregistreerde route van de Hub met de vereiste rol: als beheerder, en een dienstroute (de sessie krijgt
    401) opnieuw met het service-token van de executor. Leesroutes met de echte id's; schrijfroutes met een lege body
    (geweigerd ná de autorisatie). Afmelden als laatste."""
    import httpx
    from executor.hublink import HubLinkStore

    hub_url = next(s.url for s in keten.stack.servers if s.server.config.app is app)
    token = HubLinkStore(keten.stack.ex_settings.secrets_dir, allow_loopback=True).read()["service_token"]
    admin = keten.stack.admin
    r = admin.post("/api/v1/services/enrollment-tokens", json={"app_id": "home-control-hub"})
    assert r.status_code == 201, r.text
    r = admin.post("/api/v1/services/enroll", json=enroll_body("home-control-hub", token=r.json()["enrollment_token"]))
    assert r.status_code == 200, r.text
    lezer = r.json()["service_token"]  # een dienst met de leesscopes catalogus.lezen (scopes.SERVICE_SCOPES)

    def pad(p: str) -> str:
        for naam, waarde in {**ids, "app_uuid": str(uuid.uuid4())}.items():
            p = p.replace("{" + naam + "}", waarde)
        return re.sub(r"\{[a-z_]+\}", lambda _m: str(uuid.uuid4()), p)

    routes = sorted(_geregistreerd(app), key=lambda r: (r[0] != "GET", r))
    assert len(routes) > 100  # ondergrens: een lege routelijst kan de zoektocht niet groen maken (V-003)
    afmelden = ("POST", "/api/v1/auth/logout")
    uit, gelezen, bezocht = [], 0, set()
    for methode, p in [*(r for r in routes if r != afmelden), afmelden]:
        if (methode, p) == afmelden:  # als laatste: tot hier was elke aanroep aangemeld
            assert admin.get("/api/v1/auth/me").status_code == 200
        extra: dict[str, Any] = {} if methode == "GET" else {"json": {}}
        antwoord = admin.request(methode, pad(p), headers=idem(), **extra)
        if antwoord.status_code == 401 and (methode, p) != afmelden:  # dienstroute: met dienstcontext
            antwoord = httpx.request(
                methode, hub_url + pad(p), headers={"Authorization": f"Bearer {token}", **idem()}, **extra
            )
        if antwoord.status_code == 403 and antwoord.json().get("code") == "scope_ontbreekt":  # leesscope §4.4
            antwoord = httpx.request(methode, hub_url + pad(p), headers={"Authorization": f"Bearer {lezer}", **idem()})
        assert antwoord.status_code not in (401, 403), (
            f"hub {methode} {p}: {antwoord.status_code} {antwoord.text[:300]}"
        )
        gelezen += methode == "GET" and antwoord.status_code == 200
        bezocht.add((methode, p))
        uit.append(antwoord.text)
        if (methode, p) == ("GET", "/"):
            assert antwoord.status_code == 200, antwoord.text[:300]
    assert gelezen >= 40  # ondergrens: de leesroutes gaven echt inhoud terug, geen reeks 401/404 (V-003)
    _vergelijk("hub", app, bezocht)
    return uit


def _elke_route(keten: Keten, app: Any, ids: dict[str, str]) -> list[str]:
    """Het antwoord van elke geregistreerde route van executor en Hub (S-P2-070, R-VEILIG-1). De executor eerst: de
    Hub-rondgang meldt zich aan het eind af."""
    return [*_executor_rondgang(keten, app, ids), *_hub_rondgang(keten, app, ids)]


def _voer_uit_en_vang(admin: Any, v: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> tuple[Any, list[str]]:
    """Voer uit en vang de bevoegde antwoorden die de Hub en de executor onderling geven: de uitvoeringsrespons van de
    executor en de versleutelde afgifte van de Hub (beide 200)."""
    from executor.kluis import Kluis

    from hub import servicecalls

    gevangen: dict[str, tuple[int, str]] = {}
    call, stuur = servicecalls.call, Kluis.stuur

    def vang_call(base_url: str, method: str, path: str, **kw: Any) -> Any:
        res = call(base_url, method, path, **kw)
        if path == "/api/v1/execute":
            gevangen["uitvoering"] = (res.status, json.dumps(res.body))
        return res

    def vang_stuur(self: Kluis, link: Any, rest: Any) -> Any:
        res = stuur(self, link, rest)
        gevangen["afgifte"] = (res.status, json.dumps(res.body))
        return res

    with monkeypatch.context() as m:
        m.setattr(servicecalls, "call", vang_call)
        m.setattr(Kluis, "stuur", vang_stuur)
        r = voer_uit(admin, v)
    assert {k: s for k, (s, _) in gevangen.items()} == {"uitvoering": 200, "afgifte": 200}, gevangen
    return r, [t for _, t in gevangen.values()]


def test_koppelketen_vult_geheim_en_token_in_en_het_token_koppelt_eenmalig(
    kluisketen: Keten, app: Any, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
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
    r, onderling = _voer_uit_en_vang(admin, v, monkeypatch)
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

    # De preview (de diff die de beheerder goedkeurt) noemt alleen de verwijzing, met "geheim, niet getoond".
    preview = admin.get(f"/api/v1/actions/{v['request_id']}").json()["preview"]
    assert preview["wijziging"]["kluisverwijzingen"] == [{"verwijzing": REF, "waarde": "geheim, niet getoond"}]
    teksten = [
        r.text,
        *onderling,
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

    # Als laatste het antwoord van elke route (de rondgang raakt ook schrijfroutes en het afmelden).
    routes = _elke_route(keten, app, {"request_id": v["request_id"], "plan_id": plan["plan_id"]})
    _scan(keten, app, [geheim, token], [hashlib.sha256(geheim.encode()).hexdigest()], [*routes, caplog.text])


def test_rondgang_vindt_een_markering_in_elk_bevoegd_antwoord(
    kluisketen: Keten, app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tegenproef (R-VEILIG-1, V-003): een onschuldige markering die uitsluitend in één bevoegd antwoord staat (nooit in
    de database of de datamap) maakt de zoektocht rood. Per drager een eigen markering."""
    import secrets

    from executor import app as executor_app
    from executor.journal import Journal

    from hub import servicecalls
    from hub.catalog import kluis

    m = {d: secrets.token_hex(12) for d in ("journaal", "statuspagina", "uitvoering", "afgifte")}
    plan, v = _voorstel(kluisketen)
    entries, page, call, claim = Journal.entries, executor_app.executor_page, servicecalls.call, kluis.claim
    monkeypatch.setattr(
        Journal, "entries", lambda self, rid: [{**rij, "proef": m["journaal"]} for rij in entries(self, rid)]
    )
    monkeypatch.setattr(executor_app, "executor_page", lambda **kw: page(**kw) + f"<!-- {m['statuspagina']} -->")

    def call_met(base_url: str, method: str, path: str, **kw: Any) -> Any:
        # Op de draad, na de opslag voor exacte herhaling in de executor: alleen het antwoord bevat haar.
        res = call(base_url, method, path, **kw)
        return (
            dataclasses.replace(res, body={**(res.body or {}), "proef": m["uitvoering"]})
            if path == "/api/v1/execute"
            else res
        )

    monkeypatch.setattr(servicecalls, "call", call_met)
    monkeypatch.setattr(kluis, "claim", lambda *a: {**claim(*a), "proef": m["afgifte"]})
    r, onderling = _voer_uit_en_vang(kluisketen.stack.admin, v, monkeypatch)
    assert r.status_code == 200 and r.json()["status"] == "uitgevoerd", r.text
    antwoorden = [
        *onderling,
        *_elke_route(kluisketen, app, {"request_id": v["request_id"], "plan_id": plan["plan_id"]}),
    ]
    for drager, markering in m.items():
        _scan(kluisketen, app, [markering], [], [])  # niet opgeslagen: alleen het antwoord kan haar bevatten
        with pytest.raises(AssertionError):
            _scan(kluisketen, app, [markering], [], antwoorden)
        assert any(markering in a for a in antwoorden), drager


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


def test_zoektocht_wordt_rood_als_de_afscherming_uit_staat(
    kluisketen: Keten, app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tegenproef (V-003, S-P2-070): zonder versleuteling in de app-opslag staat het appgeheim leesbaar in de Hub; de
    zoektocht van de positieve rij moet dat vinden."""
    from hub.vault import Vault

    encrypt, decrypt = Vault.encrypt, Vault.decrypt

    def onversleuteld(self: Vault, aad: str, tekst: str) -> tuple[bytes, bytes]:
        return (b"\0" * 12, tekst.encode()) if aad.startswith("vault://app/") else encrypt(self, aad, tekst)

    def leesbaar(self: Vault, aad: str, nonce: bytes, ct: bytes) -> str:
        return ct.decode() if aad.startswith("vault://app/") else decrypt(self, aad, nonce, ct)

    monkeypatch.setattr(Vault, "encrypt", onversleuteld)
    monkeypatch.setattr(Vault, "decrypt", leesbaar)
    _, v = _voorstel(kluisketen)
    r = voer_uit(kluisketen.stack.admin, v)
    assert r.status_code == 200 and r.json()["status"] == "uitgevoerd", r.text
    geheim = _envs(kluisketen)["APP_SECRET_KEY"]
    with pytest.raises(AssertionError, match="app_geheim"):
        _scan(kluisketen, app, [geheim], [], [])


def test_kluisverwijzing_buiten_de_regel_weigert_vóór_ondertekening(
    admin: Any,
    app: Any,
    nas: Any,  # noqa: F811
    worker_once: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Een verwijzing naar een kluispad dat de regel niet kent: geen revisie, geen voorstel, niets ondertekend."""
    stap = copy.deepcopy(KLUISSTAP)
    stap["app_create"]["values"]["envs"][1]["value"] = "vault://app/demo-app/bestaat_niet"
    getekend = _tel_ondertekeningen(monkeypatch)
    with maak_keten(admin, app, nas, worker_once, tmp_path, monkeypatch, KLUISREGEL, stap) as k:
        r = _plan(k.stack.admin)
        if r.status_code == 201:
            r = _stel_voor(k.stack.admin, r.json())
        assert r.status_code in (409, 422), r.text
        assert not schrijfaanroepen(k.stack.nas) and getekend == []
        with app.state.sessionmaker() as db:
            assert db.execute(sa.text("SELECT count(*) FROM app_geheim")).scalar_one() == 0
            assert db.execute(sa.text("SELECT count(*) FROM kluis_afgifte")).scalar_one() == 0


def _tel_ondertekeningen(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Elke ondertekening van een ExecutionRequest door de Hub (de request_id), om "vóór ondertekening" te bewijzen."""
    from hub.actions import service

    getekend: list[str] = []
    origineel = service.execreq.sign

    def sign(envelope: Any, key: Any) -> Any:
        getekend.append(str(envelope.get("request_id")))
        return origineel(envelope, key)

    monkeypatch.setattr(service.execreq, "sign", sign)
    return getekend


@pytest.mark.parametrize("afwijking", ["revisie weg", "andere verwijzing", "andere instantie"])
def test_niet_bestaand_kluispad_bij_uitvoeren_weigert_vóór_ondertekening(
    kluisketen: Keten, app: Any, monkeypatch: pytest.MonkeyPatch, afwijking: str
) -> None:
    """Na het akkoord bestaat de gebonden revisie niet (meer) als deze verwijzing van deze instantie: de Hub weigert
    met ``kluiswaarde_ontbreekt`` vóór ondertekening; geen afgifte of schrijfaanroep, het akkoord blijft ongebruikt."""
    _, v = _voorstel(kluisketen)
    with app.state.sessionmaker() as db:
        sql = {
            "revisie weg": "DELETE FROM app_geheim",
            "andere verwijzing": "UPDATE app_geheim SET ref = 'vault://app/demo-app/iets_anders'",
            "andere instantie": "UPDATE app_geheim SET instance_id = gen_random_uuid()",
        }[afwijking]
        db.execute(sa.text(sql))
        db.commit()
    getekend = _tel_ondertekeningen(monkeypatch)
    r = voer_uit(kluisketen.stack.admin, v)
    assert r.status_code == 409 and r.json()["code"] == "kluiswaarde_ontbreekt", r.text
    assert getekend == [] and not schrijfaanroepen(kluisketen.stack.nas)
    with app.state.sessionmaker() as db:
        assert db.execute(sa.text("SELECT count(*) FROM kluis_afgifte")).scalar_one() == 0
        assert db.execute(sa.text("SELECT count(*) FROM approval WHERE used_at IS NOT NULL")).scalar_one() == 0
