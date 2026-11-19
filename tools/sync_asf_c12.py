"""Kopieer de C-12-regels uit de gepinde bron of controleer de bestaande kopie."""

import argparse
import ast
from pathlib import Path

BRON = Path("apps/api/src/appstore/manifest/rules.py")
REPO = Path(__file__).resolve().parents[1]
DOEL = REPO / "apps/policy/src/asm_policy/_asf_c12.py"
REGELS = {
    "Place",
    "USER_LIST_KEYS",
    "has_value",
    "is_secret_name",
    "secret_text_reasons",
}
KOP = '''"""Eigenaarsregels uit appstore-en-fork. Vernieuw deze kopie met tools/sync_asf_c12.py."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from functools import lru_cache
from typing import Any, NamedTuple
'''


def eigenaarsregels(bron: str, commit: str) -> str:
    """Neem de gebruikte declaraties en hun afhankelijkheden letterlijk over."""
    definities: dict[
        str, ast.FunctionDef | ast.ClassDef | ast.Assign | ast.AnnAssign
    ] = {}
    for node in ast.parse(bron).body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            definities[node.name] = node
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            definities[node.target.id] = node
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    definities[target.id] = node

    gekozen = set()
    openstaand = set(REGELS)
    while openstaand:
        naam = openstaand.pop()
        node = definities[naam]
        gekozen.add(naam)
        openstaand.update(
            deel.id
            for deel in ast.walk(node)
            if isinstance(deel, ast.Name) and deel.id in definities.keys() - gekozen
        )

    regels = bron.splitlines(keepends=True)
    kopie = [KOP, f"BRONCOMMIT = {commit!r}\n"]
    for node in dict.fromkeys(
        node for naam, node in definities.items() if naam in gekozen
    ):
        start = min(
            (d.lineno for d in getattr(node, "decorator_list", ())), default=node.lineno
        )
        kopie.append("".join(regels[start - 1 : node.end_lineno]))
    return "\n\n".join(kopie)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "bron", type=Path, help="werkkopie van appstore-en-fork op ASF_COMMIT"
    )
    parser.add_argument(
        "--check", action="store_true", help="controleer de kopie zonder te schrijven"
    )
    args = parser.parse_args()
    pin = next(
        regel
        for regel in (REPO / "policy/catalogus.yaml").read_text().splitlines()
        if regel.startswith("ASF_COMMIT:")
    )
    verwacht = eigenaarsregels(
        (args.bron / BRON).read_text(encoding="utf-8"), pin.split(":", 1)[1].strip()
    )
    if args.check:
        if DOEL.read_text(encoding="utf-8") != verwacht:
            raise SystemExit("C-12-regels wijken af van de gepinde bron.")
        print("C-12-regels komen overeen met de gepinde bron.")
    else:
        DOEL.write_text(verwacht, encoding="utf-8")
