"""OpenAPI exporteren naar ``docs/openapi/hub-api.openapi.json``; ``--check`` faalt bij drift (CI)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from fastapi.openapi.utils import get_openapi


def build_spec() -> dict[str, Any]:
    # Geen database of geheimen nodig: alleen de routes.
    from hub.app import create_app
    from hub.config import Settings

    app = create_app(Settings(database_url="postgresql+psycopg://openapi@/openapi?host=/nonexistent"))
    return get_openapi(
        title=app.title, version=app.version, description=app.description, routes=app.routes, tags=app.openapi_tags
    )


def render(spec: dict[str, Any]) -> str:
    return json.dumps(spec, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def export(out: Path, *, check: bool = False) -> int:
    text = render(build_spec())
    if check:
        current = out.read_text() if out.exists() else ""
        if current != text:
            print(
                f"OpenAPI-drift: {out} is niet actueel. Draai `make openapi` en commit het resultaat.", file=sys.stderr
            )
            return 1
        print(f"{out} is actueel")
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    print(f"geschreven: {out}")
    return 0
