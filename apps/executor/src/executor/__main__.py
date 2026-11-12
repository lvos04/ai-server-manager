"""``python -m executor <init|api|export-openapi>``."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

from executor.config import get_settings


def log_config() -> dict[str, Any]:
    """Logconfiguratie voor ``uvicorn.run``: die van uvicorn, plus een eigen handler voor de logger ``executor`` op INFO
    (stdout, los van root; ``propagate`` uit). Zo komt de regel per afgehandelde poging (code + trace-ID, contract 1.3
    §3.7/§3.9) in de app-log; uvicorn configureert alleen zijn eigen loggers (R-VEILIG-3, S-P2-020). Root en
    websockets blijven ongemoeid (nooit DEBUG); de TrueNAS-verbinding heeft een eigen logger vast op INFO."""
    from uvicorn.config import LOGGING_CONFIG

    cfg = copy.deepcopy(LOGGING_CONFIG)
    cfg["formatters"]["executor"] = {"format": "%(levelname)s:     %(name)s: %(message)s"}
    cfg["handlers"]["executor"] = {
        "class": "logging.StreamHandler",
        "formatter": "executor",
        "stream": "ext://sys.stdout",
        "level": "INFO",
    }
    cfg["loggers"]["executor"] = {"handlers": ["executor"], "level": "INFO", "propagate": False}
    return cfg


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
            link = HubLinkStore(s.secrets_dir).read()
            state = "onleesbaar (fail-closed)" if link.get("_onleesbaar") else str(link.get("state"))
        except (OSError, ValueError):
            state = "onbekend (hub-link.json onleesbaar)"
        print(
            f"[executor] koppelstatus: {state}. Uitvoeren kan pas na koppelen met de Hub en het instellen van de "
            "TrueNAS-schrijfsleutel op de statuspagina.",
            flush=True,
        )
        return 0
    if args.cmd == "api":
        import uvicorn

        uvicorn.run(
            "executor.app:create_app",
            factory=True,
            host=s.host,
            port=s.port,
            log_level=s.log_level,
            log_config=log_config(),
            access_log=False,
            server_header=False,
            # Nooit X-Forwarded-* vertrouwen (§3.7: bron-IP = adres van de TCP-verbinding, schema = de verbinding).
            proxy_headers=False,
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
