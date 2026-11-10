"""Contract 1.3 §5: elke mutatie vraagt een ``Idempotency-Key``; alleen de uitzonderingen van §5 niet (C1.3-ASM-14).

Statische controle over alle routers: een nieuwe POST/PUT/PATCH/DELETE-route zonder de ``Idem``-afhankelijkheid laat
deze test falen, tenzij hij hieronder met reden en bron (contract of ADR) is uitgezonderd. Elke reden noemt de
paragraaf van contract 1.3 waar de uitzondering staat; een andere uitzondering vraagt een ADR en een contractmelding.
"""

from __future__ import annotations

import ast
from pathlib import Path

API = Path(__file__).resolve().parents[2]

EXEMPT: dict[str, str] = {
    # Contract §5 (ADR-0006): eenmalig van aard of geven bewust een nieuw geheim.
    "auth.py:setup_admin": "setup (contract 1.3 §5)",
    "auth.py:login": "inloggen (contract 1.3 §5)",
    "auth.py:logout": "uitloggen (contract 1.3 §5)",
    "auth.py:change_password": "wachtwoord (contract 1.3 §5)",
    "auth.py:service_jwt": "JWT-uitgifte (contract 1.3 §5)",
    "services.py:create_enrollment_token": "enrollment-token maken (contract 1.3 §5)",
    "services.py:create_pairing_code": "koppelcode maken (contract 1.3 §5)",
    "services.py:enroll": "services/enroll (contract 1.3 §3.3, §5)",
    "services.py:rotate_self": "services/self/rotate (contract 1.3 §5)",
    # Noodaccount instellen, roteren en bevestigen: geeft een geheim één keer terug of bevestigt een eenmalige TOTP.
    "breakglass.py:setup": "noodaccount instellen: TOTP-geheim één keer (contract 1.3 §5)",
    "breakglass.py:rotate": "noodaccount roteren: TOTP-geheim één keer (contract 1.3 §5)",
    "breakglass.py:confirm": "noodaccount bevestigen: eenmalige TOTP-code (contract 1.3 §5)",
    "breakglass.py:login": "inloggen (contract 1.3 §5)",
    "breakglass.py:selftest": "…/selftest: geen bijwerking behalve audit (contract 1.3 §4.1, §5)",
    # Events en diensten: dedupe op eigen sleutel in plaats van Idempotency-Key.
    "events.py:inbox": "dedupe op event_id en (source_app, source_event_id) (contract 1.3 §5, §7)",
    "monitoring.py:heartbeat": "dedupe op observed_at (contract 1.3 §5, §6.1)",
    "logs.py:logs_ingest": "dubbele levering aanvaard (contract 1.3 §5, §6.1)",
    # Connector: nog niet gebouwd → altijd 501 capability_unavailable, er wordt niets uitgevoerd.
    "events.py:propose": "zolang 501 capability_unavailable (contract 1.3 §5, §6)",
    "events.py:apply": "zolang 501 capability_unavailable (contract 1.3 §5, §6)",
    "events.py:rollback": "zolang 501 capability_unavailable (contract 1.3 §5, §6)",
    # SSO: het starten van een OIDC-(test)login is inloggen.
    "oidc.py:oidc_test_start": "start van een OIDC-testlogin (contract 1.3 §5)",
}


def _mutating_routes() -> list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef, str]]:
    out = []
    for f in sorted((API / "src" / "hub" / "routers").glob("*.py")):
        src = f.read_text(encoding="utf-8")
        for n in ast.walk(ast.parse(src)):
            if not isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            if any(
                isinstance(d, ast.Call)
                and isinstance(d.func, ast.Attribute)
                and d.func.attr in ("post", "put", "patch", "delete")
                for d in n.decorator_list
            ):
                out.append((f"{f.name}:{n.name}", n, src))
    return out


def test_elke_mutatie_vraagt_idempotency_key_behalve_de_uitzonderingen() -> None:
    routes = _mutating_routes()
    assert len(routes) > 50, "te weinig routes gevonden: klopt het pad naar de routers nog?"
    missing: list[str] = []
    for name, fn, src in routes:
        if name in EXEMPT:
            continue
        annotations = [
            ast.get_source_segment(src, a.annotation) or ""
            for a in [*fn.args.args, *fn.args.kwonlyargs]
            if a.annotation is not None
        ]
        if not any(a == "Idem" or a.endswith("Idempotency") for a in annotations):
            missing.append(name)
    assert not missing, f"muterende routes zonder Idempotency-Key (of zonder reden in EXEMPT): {missing}"


def test_elke_uitzondering_noemt_contract_1_3() -> None:
    """C1.3-ASM-14: de bron van elke uitzondering is contract 1.3 §5 (geen 'contract_issue voor 1.3' meer)."""
    assert all("contract 1.3 §" in reden for reden in EXEMPT.values()), EXEMPT
    assert not any("contract_issue" in reden or "ADR-0013" in reden for reden in EXEMPT.values())


def test_uitzonderingen_bestaan_nog() -> None:
    """Een verouderde uitzondering (route hernoemd of verdwenen) mag niet blijven staan."""
    names = {name for name, _, _ in _mutating_routes()}
    stale = sorted(set(EXEMPT) - names)
    assert not stale, f"uitzonderingen zonder route: {stale}"
