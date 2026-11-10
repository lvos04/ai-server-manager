"""Contract 1.2 §5: elke mutatie vraagt een ``Idempotency-Key``; alleen de vastgelegde uitzonderingen niet.

Statische controle over alle routers: een nieuwe POST/PUT/PATCH/DELETE-route zonder de ``Idem``-afhankelijkheid laat
deze test falen, tenzij hij hieronder met reden en bron (contract of ADR) is uitgezonderd.
"""

from __future__ import annotations

import ast
from pathlib import Path

API = Path(__file__).resolve().parents[2]

EXEMPT: dict[str, str] = {
    # Contract §5 (ADR-0006): eenmalig van aard of geven bewust een nieuw geheim.
    "auth.py:setup_admin": "setup (contract §5)",
    "auth.py:login": "inloggen (contract §5)",
    "auth.py:logout": "uitloggen (contract §5)",
    "auth.py:change_password": "wachtwoord (contract §5)",
    "auth.py:service_jwt": "JWT-uitgifte (contract §5)",
    "services.py:create_enrollment_token": "enrollment-token maken (contract §5)",
    "services.py:create_pairing_code": "koppelcode maken (contract §5)",
    "services.py:enroll": "services/enroll (contract §3.3, §5)",
    "services.py:rotate_self": "services/self/rotate (contract §5)",
    # Noodaccount: geeft het TOTP-geheim één keer terug of is inloggen (ADR-0013 punt 7).
    "breakglass.py:setup": "geeft het TOTP-geheim één keer terug (ADR-0013)",
    "breakglass.py:rotate": "geeft het TOTP-geheim één keer terug (ADR-0013)",
    "breakglass.py:confirm": "bevestigt een eenmalige TOTP-code (ADR-0013)",
    "breakglass.py:login": "inloggen (contract §5)",
    "breakglass.py:selftest": "geen mutatie (contract §4.1)",
    # Events en diensten: dedupe op eigen sleutel in plaats van Idempotency-Key.
    "events.py:inbox": "dedupe op event_id en (source_app, source_event_id) (contract §7)",
    "monitoring.py:heartbeat": "dedupe op observed_at (ADR-0021; contract_issue voor 1.3)",
    "logs.py:logs_ingest": "logregels zijn geen beheerhandeling (ADR-0022; contract_issue voor 1.3)",
    # Connector: nog niet gebouwd → altijd 501 capability_unavailable, er wordt niets uitgevoerd.
    "events.py:propose": "501 capability_unavailable (contract §6)",
    "events.py:apply": "501 capability_unavailable (contract §6)",
    "events.py:rollback": "501 capability_unavailable (contract §6)",
    # SSO: het starten van een testlogin is inloggen-achtig (ADR-0023).
    "oidc.py:oidc_test_start": "start een testlogin (ADR-0023)",
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


def test_uitzonderingen_bestaan_nog() -> None:
    """Een verouderde uitzondering (route hernoemd of verdwenen) mag niet blijven staan."""
    names = {name for name, _, _ in _mutating_routes()}
    stale = sorted(set(EXEMPT) - names)
    assert not stale, f"uitzonderingen zonder route: {stale}"
