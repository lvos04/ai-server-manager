"""Continuïteit van instanties in twee opeenvolgende app-inventarissen."""

from datetime import datetime
from typing import Any


def by_runtime_id(data: Any) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    if isinstance(data, list):
        for app in data:
            if isinstance(app, dict) and isinstance(app.get("runtime_id"), str):
                index.setdefault(app["runtime_id"], []).append(app)
    return index


def same_destination(ports: Any, portals: Any, app: dict[str, Any]) -> bool:
    # Bij een gestopte workload kunnen gepubliceerde poorten wegvallen.
    # Een wél gemelde afwijkende poort of portal blijft een andere bestemming.
    stopped = app.get("staat") in ("STOPPED", "CRASHED")
    return all(
        measured == known or (stopped and measured == [])
        for measured, known in ((app.get("poorten"), ports), (app.get("portals"), portals))
    )


def continuity(
    previous: Any, boundaries: dict[str, str | None], data: Any, known: set[str], observed: datetime
) -> dict[str, str | None]:
    """Per unieke instantie de grens waarna een nieuwe bevestiging nodig is."""
    before = by_runtime_id(previous)
    result: dict[str, str | None] = {}
    for rid, matches in by_runtime_id(data).items():
        if len(matches) != 1:
            continue
        current = matches[0]
        earlier = before.get(rid, [])
        if (
            rid in boundaries
            and len(earlier) == 1
            and earlier[0].get("herkend_als") == current.get("herkend_als")
            and same_destination(earlier[0].get("poorten"), earlier[0].get("portals"), current)
        ):
            result[rid] = boundaries[rid]
        elif rid in known or earlier:
            result[rid] = observed.isoformat()
        else:
            result[rid] = None
    return result
