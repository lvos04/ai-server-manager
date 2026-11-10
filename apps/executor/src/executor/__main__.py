"""``python -m executor <init|api|export-openapi>``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from executor.config import get_settings


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="executor")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="eigen geheimen aanmaken (nooit overschrijven)")
    sub.add_parser("api", help="HTTP-API starten")
    e = sub.add_parser("export-openapi")
    e.add_argument("--out", default="docs/openapi/executor.openapi.json")
    e.add_argument("--check", action="store_true")
    args = p.parse_args(argv)
    s = get_settings()
    if args.cmd == "init":
        from executor.firststart import FirstStartError, ensure_secrets

        try:
            created = ensure_secrets(s.secrets_dir)
        except FirstStartError as exc:
            print(f"[executor] FOUT: {exc}", flush=True)
            return 78
        print(f"[executor] geheimen: {'nieuw: ' + ', '.join(created) if created else 'aanwezig'}", flush=True)
        # De echte koppelstatus (witte lijst §3.5, zonder token of hashes), niet altijd "nog niet gekoppeld".
        from executor.hublink import HubLinkStore

        try:
            state = str(HubLinkStore(s.secrets_dir).read().get("state") or "nooit_gekoppeld")
        except (OSError, ValueError):
            state = "onbekend (hub-link.json onleesbaar)"
        print(f"[executor] koppelstatus: {state}. Allowlist leeg tot fase P2: er wordt niets uitgevoerd.", flush=True)
        return 0
    if args.cmd == "api":
        import uvicorn

        uvicorn.run(
            "executor.app:create_app",
            factory=True,
            host=s.host,
            port=s.port,
            log_level=s.log_level,
            access_log=False,
            server_header=False,
        )
        return 0
    from executor.app import create_app

    app = create_app()
    text = json.dumps(app.openapi(), indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    out = Path(args.out)
    if args.check:
        if not out.exists() or out.read_text() != text:
            print(f"OpenAPI-drift: {out} is niet actueel", file=sys.stderr)
            return 1
        print(f"{out} is actueel")
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    print(f"geschreven: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
