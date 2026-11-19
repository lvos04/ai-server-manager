"""Leesgrenzen van de my_house-adapter."""

import ast
import re
from pathlib import Path

from hub.adapters import my_house


def test_module_bevat_uitsluitend_toegelaten_routes() -> None:
    source = Path(my_house.__file__).read_text()
    assert not re.search(r"/(?:command|resume|ack|audit|diagnostics|backups?|users)(?:\b|/)|/lights/groups", source)
    tree = ast.parse(source)
    paths = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.startswith("/api/")
    }
    assert paths == {
        "/api/v1/health",
        "/api/v1/pairing/identity",
        "/api/v1/pairing/redeem",
        "/api/v1/clients/self/refresh",
        "/api/v1/system/status",
        "/api/v1/homes",
        "/api/v1/homes/{home_id}/zones",
        "/api/v1/homes/{home_id}/lights",
        "/api/v1/homes/{home_id}/alerts",
        "/api/v1/homes/{home_id}/devices",
        "/api/v1/system/settings",
    }


def test_link_vereist_geldig_schema_en_bevestigde_bestemming() -> None:
    base = "https://woning.example"
    assert my_house.user_link(base, "javascript:open()", None) is None
    assert my_house.user_link(base, "https://andere-woning.example", None) is None
    assert my_house.user_link(base, "https://woning.example/?", None) is None
    assert my_house.user_link(base, "javascript:open()", f"{base}/") == base
