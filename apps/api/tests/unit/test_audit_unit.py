"""Auditspoor (ADR-0022): canonieke vorm v1 is deterministisch en gelijk aan de bevroren kopie in migratie 0006;
elke muterende route legt een auditrecord vast of staat met reden op de uitzonderingslijst."""

from __future__ import annotations

import ast
import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from hub import audit

API = Path(__file__).resolve().parents[2]


def _migration() -> object:
    path = API / "alembic" / "versions" / "0006_audit_hashketting.py"
    spec = importlib.util.spec_from_file_location("mig0006", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_canonieke_vorm_gelijk_aan_bevroren_kopie_in_migratie() -> None:
    row = SimpleNamespace(
        at=datetime(2026, 11, 9, 12, 0, 1, 123456, tzinfo=UTC),
        actor_type="user",
        actor_id="beheerder",
        action="user.created",
        target_type="user",
        target_id="abc",
        details={"z": 1, "a": [1.5, "ü"], "geneste": {"b": None}},
        trace_id="t",
    )
    ours = audit._row_canonical(row, 7)
    theirs = _migration()._canonical_v1(7, row)  # type: ignore[attr-defined]
    assert ours == theirs
    assert ours.startswith(b'{"actie":"user.created"')  # sleutels gesorteerd, geen spaties
    h1 = audit.chain_hash(audit.GENESIS, ours)
    assert h1 == audit.chain_hash(audit.GENESIS, ours) and len(h1) == 64
    assert audit.chain_hash("1" * 64, ours) != h1


# Muterende routes zonder eigen auditrecord, met reden. Helpers die zelf auditen tellen als audit.
EXEMPT = {
    "service_jwt": "geeft alleen een kortlevende JWT uit (exp ≤ 120 s), wijzigt niets",
    "selftest": "zelftest zonder mutatie (contract 1.2 §4.1)",
    "inbox": "events van diensten; het event zelf is het spoor (dedupe op event_id)",
    "propose": "501 capability_unavailable",
    "apply": "501 capability_unavailable",
    "rollback": "501 capability_unavailable",
    "heartbeat": "hartslag van een dienst (service-token), geen beheerhandeling",
    "logs_ingest": "logregels van een dienst (service-token), geen beheerhandeling",
    "oidc_test_start": "start alleen een testlogin; het resultaat wordt in de callback geaudit",
}
AUDITING_HELPERS = {"_set_value", "_save", "_grant", "_record", "audit_action", "_audit"}


def test_elke_muterende_route_wordt_geaudit() -> None:
    missing: list[str] = []
    for f in sorted((API / "src" / "hub" / "routers").glob("*.py")):
        src = f.read_text(encoding="utf-8")
        tree = ast.parse(src)
        helpers = {
            n.name
            for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and "audit." in (ast.get_source_segment(src, n) or "")
        }
        for n in ast.walk(tree):
            if not isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            methods = [
                d.func.attr
                for d in n.decorator_list
                if isinstance(d, ast.Call)
                and isinstance(d.func, ast.Attribute)
                and d.func.attr in ("post", "put", "patch", "delete")
            ]
            if not methods or n.name in EXEMPT:
                continue
            body = ast.get_source_segment(src, n) or ""
            calls = {c.func.id for c in ast.walk(n) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
            if "audit." in body or calls & (helpers | AUDITING_HELPERS):
                continue
            missing.append(f"{f.name}:{n.name}")
    assert not missing, f"muterende routes zonder audit (of zonder reden in EXEMPT): {missing}"
