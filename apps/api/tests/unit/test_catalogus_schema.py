"""R-VEILIG-2: de Hub valideert het oorspronkelijke manifest met de kopie van de gepinde validator en toetst de
ingevulde parameters met diens parametercontrole."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import yaml

from hub.catalog.plannen import SCHEMA_SHA256, manifest_fouten, parameters_fouten

ASF = Path(__file__).resolve().parents[2] / "src/hub/catalog/asf"
REPO = Path(__file__).resolve().parents[4]

GELDIG = {
    "manifest_version": "1",
    "app_id": "demo-app",
    "name": "Demo",
    "owner_repo": "voorbeeld/demo-app",
    "category": "other",
    "description_nl": "Fictieve app voor de schematoets.",
    "version": "1.2.3",
    "install": {"method": "catalog_app", "reason": "meerdere_containers"},
    "catalog": {"train": "stable", "app": "demo", "version": "1.0.0"},
    "values": {},
    "parameters": [
        {"name": "public_url", "type": "url", "source": "wizard", "required": False, "description_nl": "Adres."},
        {"name": "poort", "type": "port", "source": "wizard", "required": True, "description_nl": "Hostpoort."},
        {"name": "db_wachtwoord", "type": "string", "source": "generated", "secret": True, "required": True,
         "description_nl": "Gemaakt door de Hub."},
    ],
    "storage": [],
    "network": {"ports": [], "host_network": False, "host_network_reason": None},
    "privileges": {"privileged": False, "cap_add": [], "devices": [], "gpu": "none"},
    "healthcheck": {"type": "builtin"},
    "backup": {"db_export": {"method": "none"}, "snapshot_datasets": [], "rpo": "PT24H", "rto": "PT4H"},
    "dependencies": [],
    "sso": "none",
    "risk": {"install": "R2", "update": "R2", "uninstall": "R2"},
    "upgrade": {"migrations": False, "tag_only_rollback_safe": True},
    "decisions_required": [],
    "docs": ["B08_APPSTORE_LIFECYCLE"],
    "validation_status": "unvalidated",
}  # fmt: skip
REGEL = {"schema_sha256": SCHEMA_SHA256}


def test_schemakopie_past_bij_de_pin_en_weigert_een_onvolledig_manifest() -> None:
    assert manifest_fouten(REGEL, GELDIG) == 0
    zonder_naam = copy.deepcopy(GELDIG)
    del zonder_naam["name"]
    assert manifest_fouten(REGEL, zonder_naam) > 0
    assert manifest_fouten(REGEL, {"schema_version": 1, "app_id": "demo-app", "version": "1.2.3"}) > 0
    # Een regel met een ander schema dan de eigen kopie: nooit goed.
    assert manifest_fouten({"schema_sha256": "sha256:" + "5" * 64}, GELDIG) == 1


def test_alleen_gedeclareerde_niet_geheime_parameters() -> None:
    assert parameters_fouten(GELDIG, {"public_url": "https://demo.test/", "poort": 30555}) == []
    assert parameters_fouten(GELDIG, {"password": "x"}) == ["niet_gedeclareerd"]
    assert parameters_fouten(GELDIG, {"db_wachtwoord": "x"}) == ["niet_invulbaar"]
    assert parameters_fouten(GELDIG, {"poort": "30555"}) == ["type"]
    assert parameters_fouten(GELDIG, {"poort": True}) == ["type"]
    assert parameters_fouten(GELDIG, {"public_url": "x" * 501}) == ["type"]
    assert parameters_fouten(GELDIG, {"public_url": "ftp://demo.test/"}) == ["type"]


def test_validatorkopie_is_bytegelijk_aan_de_pin() -> None:
    bron = json.loads((ASF / "BRON.json").read_text(encoding="utf-8"))
    pin = yaml.safe_load((REPO / "policy/catalogus.yaml").read_text(encoding="utf-8"))["ASF_COMMIT"]
    assert bron["asf_commit"] == pin
    for naam, digest in bron["bestanden"].items():
        data = (ASF / naam).read_bytes()
        if naam == "manifest/validator.py":
            # De enige aanpassing (BRON.json): de pakketnaam van het schema.
            data = data.replace(b"resources.files(__package__)", b'resources.files("appstore.manifest")')
        assert "sha256:" + hashlib.sha256(data).hexdigest() == digest, naam
    gekopieerd = {str(p.relative_to(ASF)) for p in ASF.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    assert gekopieerd == set(bron["bestanden"]) | {"BRON.json"}


def test_regels_van_de_validator_gelden_naast_het_schema() -> None:
    host = copy.deepcopy(GELDIG)
    host["network"]["host_network"] = True  # zonder reden: regel host_network_without_reason
    assert manifest_fouten(REGEL, host) > 0


def test_parameterwaarde_volgt_de_validator() -> None:
    pad = copy.deepcopy(GELDIG)
    pad["parameters"].append(
        {"name": "data_path", "type": "path", "source": "dataset_picker", "required": True, "description_nl": "Map."}
    )
    assert parameters_fouten(pad, {"data_path": "/mnt/testpool/apps/demo"}) == []
    assert parameters_fouten(pad, {"data_path": "voorbeeldmap"}) == ["type"]  # relatief pad
    assert parameters_fouten(pad, {"data_path": "/mnt/testpool/../etc"}) == ["type"]
