"""Bron- en doelbinding van een planstap tegen de witte lijst (contract 1.3 §8.1; ADR-0032 deel D; S-P2-050d).

Toestandstabel: één positieve rij en per afwijkend veld één negatieve rij. Hub en executor gebruiken dezelfde
``validate_parameters``; deze tests gelden dus voor beide ankers.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
from policyhelpers import (
    DIGEST,
    DIGEST_B,
    HOST,
    catalog_binding,
    catalogus_regel,
    install_params,
    policy_met_regels,
)

from asm_policy import PolicyError, load_policy
from asm_policy.catalogbinding import readback_digest_afwijking
from asm_policy.params import validate_parameters

APP = {"host_id": HOST, "app_id": "demo-app"}


@pytest.fixture(scope="module")
def beleid(tmp_path_factory: pytest.TempPathFactory) -> Any:
    return load_policy(policy_met_regels(tmp_path_factory.mktemp("p") / "policy", [catalogus_regel()]))


def _params(**binding_change: Any) -> dict[str, Any]:
    p = install_params("demo-app")
    p["catalog_binding"] = catalog_binding(catalogus_regel(), **binding_change)
    return p


def _codes(beleid: Any, params: dict[str, Any], target: dict[str, Any] = APP) -> list[str]:
    return sorted({f.code for f in validate_parameters(beleid, beleid.actie("app.install"), target, params)})


def test_passende_binding_wordt_toegelaten(beleid: Any) -> None:
    assert _codes(beleid, _params()) == []


def test_lege_witte_lijst_weigert_elke_binding() -> None:
    echt = load_policy()
    assert echt.catalogus == ()
    assert _codes(echt, _params()) == ["catalogusversie_niet_toegelaten"]


def _rec(**change: Any) -> dict[str, Any]:
    b = catalog_binding(catalogus_regel())
    b["provenance"]["record"].update(change)
    return b


def _src(**change: Any) -> dict[str, Any]:
    b = catalog_binding(catalogus_regel())
    b["provenance"]["record"]["source"].update(change)
    return b


AFWIJKINGEN: list[tuple[str, Any, str]] = [
    ("andere manifesthash", lambda: _rec(manifest_sha256="sha256:" + "9" * 64), "catalogusversie_niet_toegelaten"),
    ("andere app_id", lambda: _rec(app_id="andere-app"), "catalogusversie_niet_toegelaten"),
    ("andere versie", lambda: _rec(version="1.2.4"), "catalogusversie_niet_toegelaten"),
    ("andere uitgever", lambda: _rec(publisher_key_sha256="sha256:" + "1" * 64), "catalogusversie_niet_toegelaten"),
    ("ander schema", lambda: _rec(schema_sha256="sha256:" + "2" * 64), "catalogusversie_niet_toegelaten"),
    ("andere validator", lambda: _rec(validator_version="0.9.1"), "catalogusversie_niet_toegelaten"),
    ("andere commit", lambda: _src(commit="d" * 40), "catalogusversie_niet_toegelaten"),
    ("ander subpad", lambda: _src(subpath=None), "catalogusversie_niet_toegelaten"),
    ("ander bestand", lambda: _src(path="demo-app/ander.yaml"), "catalogusversie_niet_toegelaten"),
    ("andere bronlocatie", lambda: _src(url="https://forge.test/x/y"), "catalogusversie_niet_toegelaten"),
    ("http-bron", lambda: _src(kind="http"), "bron_niet_toegelaten"),
    ("ingebouwde bron", lambda: _src(kind="bundled"), "bron_niet_toegelaten"),
    ("bewegende ref zonder commit", lambda: _src(commit=None), "bron_niet_gepind"),
    ("uitgever niet geverifieerd", lambda: _rec(publisher_signature="absent"), "uitgever_niet_geverifieerd"),
    ("manifest ongeldig", lambda: _rec(valid=False), "manifest_ongeldig"),
    ("onbekend recordveld", lambda: _rec(trusted=True), "onbekend_veld"),
]


@pytest.mark.parametrize(("naam", "maak", "code"), AFWIJKINGEN, ids=[a[0] for a in AFWIJKINGEN])
def test_afwijkend_record_wordt_geweigerd(beleid: Any, naam: str, maak: Any, code: str) -> None:
    p = install_params("demo-app")
    p["catalog_binding"] = maak()
    assert code in _codes(beleid, p), naam


def test_ontbrekend_recordveld_wordt_geweigerd(beleid: Any) -> None:
    b = catalog_binding(catalogus_regel())
    del b["provenance"]["record"]["publisher_key_sha256"]
    p = install_params("demo-app")
    p["catalog_binding"] = b
    assert "verplicht" in _codes(beleid, p)


BINDING_RIJEN: list[tuple[str, dict[str, Any], str]] = [
    ("release met andere digest", {"release": {"catalog": catalogus_regel()["catalog"], "image_digests": [DIGEST_B]}},
     "release_verschilt"),
    ("release met andere ix-app-versie",
     {"release": {"catalog": {"train": "stable", "app": "ix-app", "version": "1.4.9"}, "image_digests": [DIGEST]}},
     "release_verschilt"),
    ("kluisplekken", {"vault_refs": [{"path": "x", "parameter": "y", "ref": "vault://app/demo-app/y"}]},
     "kluis_nog_niet_beschikbaar"),
    ("plan-ID geen UUID", {"plan_id": "mijn-plan"}, "patroon"),
    ("onbekend veld", {"trusted_app_id": True}, "onbekend_veld"),
]  # fmt: skip


@pytest.mark.parametrize(("naam", "wijzig", "code"), BINDING_RIJEN, ids=[r[0] for r in BINDING_RIJEN])
def test_afwijkende_binding_wordt_geweigerd(beleid: Any, naam: str, wijzig: dict[str, Any], code: str) -> None:
    assert code in _codes(beleid, _params(**wijzig)), naam


@pytest.mark.parametrize("weg", ["provenance", "release", "instance", "vault_refs", "plan_etag"])
def test_ontbrekend_bindingsveld_wordt_geweigerd(beleid: Any, weg: str) -> None:
    p = _params()
    del p["catalog_binding"][weg]
    assert "verplicht" in _codes(beleid, p)


def test_instantie_hoort_bij_het_doel(beleid: Any) -> None:
    p = _params()
    p["catalog_binding"]["instance"]["app_name"] = "andere-app"
    assert "doel_verschilt" in _codes(beleid, p)
    p = _params()
    p["catalog_binding"]["instance"]["host_id"] = "andere-nas"
    assert "doel_verschilt" in _codes(beleid, p)
    p = _params()
    p["catalog_binding"]["instance"]["expected_version"] = "sha256:" + "0" * 64
    assert "doel_verschilt" in _codes(beleid, p)


def test_payload_moet_de_toegelaten_release_installeren(beleid: Any) -> None:
    p = _params()
    p["app_create"]["version"] = "1.4.9"
    assert "release_verschilt" in _codes(beleid, p)
    p = _params()
    p["app_create"]["values"]["image"]["tag"] = f"1.2.3@{DIGEST_B}"
    p["manifest"]["image_digest"] = DIGEST_B
    assert "digest_verschilt" in _codes(beleid, p)
    p = _params()
    p["manifest"]["version"] = "1.2.4"
    assert "release_verschilt" in _codes(beleid, p)


def test_dubbele_regel_is_dubbelzinnig(tmp_path: Path) -> None:
    beleid = load_policy(policy_met_regels(tmp_path / "p", [catalogus_regel(), catalogus_regel()]))
    assert _codes(beleid, _params()) == ["catalogusregel_dubbelzinnig"]


def test_ex47_blijft_gelden_met_een_geldige_binding(beleid: Any) -> None:
    p = _params()
    p["app_create"]["values"]["host_network"] = True
    assert _codes(beleid, p) != []


REGEL_FOUTEN: list[tuple[str, dict[str, Any], str]] = [
    ("kluisplekken", {"kluisplekken": ["x"]}, "kluisplekken zijn in deze versie niet toegestaan"),
    ("http-url", {"source": {"url": "http://forge.test/a/b", "subpath": None, "path": "m.yaml", "commit": "c" * 40}},
     "source.url"),
    ("subpad met ..", {"source": {"url": "https://forge.test/a/b", "subpath": "../x", "path": "m.yaml",
                                  "commit": "c" * 40}}, "geen geldig paddeel"),
    ("korte commit", {"source": {"url": "https://forge.test/a/b", "subpath": None, "path": "m.yaml",
                                 "commit": "c" * 7}}, "commit"),
    ("lege digests", {"image_digests": []}, "image_digests"),
    ("tag als digest", {"image_digests": ["latest"]}, "image_digests"),
]  # fmt: skip


@pytest.mark.parametrize(("naam", "wijzig", "melding"), REGEL_FOUTEN, ids=[r[0] for r in REGEL_FOUTEN])
def test_ongeldige_regel_geeft_geen_beleid(tmp_path: Path, naam: str, wijzig: dict[str, Any], melding: str) -> None:
    with pytest.raises(PolicyError, match=melding):
        load_policy(policy_met_regels(tmp_path / "p", [catalogus_regel(**wijzig)]))


def test_extra_regelveld_geeft_geen_beleid(tmp_path: Path) -> None:
    regel = catalogus_regel()
    regel["vrijgave"] = True
    with pytest.raises(PolicyError, match="verwacht precies de velden"):
        load_policy(policy_met_regels(tmp_path / "p", [regel]))


# ------------------------------------------------------------------ readback van de digest (executor, na uitvoering)
REF = "ghcr.io/voorbeeld/demo-app:1.2.3"
READBACK: list[tuple[str, list[str], list[dict[str, Any]], str | None]] = [
    ("digest uit app.image.query in de release", [REF],
     [{"repo_tags": [REF], "repo_digests": [f"ghcr.io/voorbeeld/demo-app@{DIGEST}"]}], None),
    ("andere digest", [REF], [{"repo_tags": [REF], "repo_digests": [f"ghcr.io/voorbeeld/demo-app@{DIGEST_B}"]}],
     "digest_verschilt"),
    ("geen imagerij", [REF], [], "digest_niet_bevestigd"),
    ("imagerij zonder digests", [REF], [{"repo_tags": [REF], "repo_digests": []}], "digest_niet_bevestigd"),
    ("geen images bij de app", [], [], "digest_niet_bevestigd"),
]  # fmt: skip


@pytest.mark.parametrize(("naam", "refs", "images", "code"), READBACK, ids=[r[0] for r in READBACK])
def test_readback_digest(naam: str, refs: list[str], images: list[dict[str, Any]], code: str | None) -> None:
    afw = readback_digest_afwijking(_params(), refs, images)
    assert (afw or {}).get("code") == code, naam


def test_readback_zonder_binding_verandert_niets() -> None:
    assert readback_digest_afwijking(install_params("demo-app"), [], []) is None
    assert copy.deepcopy(install_params("demo-app")) == install_params("demo-app")
