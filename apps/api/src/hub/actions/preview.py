"""Preview van een actie: wat er nu staat, wat er verandert en wat er blijft (B01-007, B01-003).

De preview is een pure functie van (beleid, classificatie, doel, parameters, eigen readback) — geen klok, geen
willekeur. ``preview_hash`` = SHA-256 over de canonieke JSON. Een beheerder keurt precies deze preview goed; verandert
er iets aan (andere image of digest op de NAS, ander beleid, andere risicoklasse), dan verandert de hash en vervalt de
goedkeuring (EX19).

Geheimen: waarden van omgevingsvariabelen staan nooit in de preview (alleen de namen); verwijzingen naar de kluis
(``vault://…``) worden als verwijzing getoond, nooit ingevuld.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from asm_policy import Policy, execreq
from asm_policy.canonical import canonical_sha256
from asm_policy.engine import Classification
from asm_policy.loader import ActieDef
from asm_policy.params import IX_APP, expected_image, vault_refs

from hub.actions.doel import Doel

SCHEMA = "asm-preview/1"
DATA_BLIJFT = "Datasets en data blijven staan; de Hub en de executor verwijderen nooit data."


def _lijst(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _install(target: Mapping[str, Any], parameters: Mapping[str, Any]) -> dict[str, Any]:
    ac_raw = parameters.get("app_create")
    ac: Mapping[str, Any] = ac_raw if isinstance(ac_raw, Mapping) else {}
    values_raw = ac.get("values")
    values: Mapping[str, Any] = values_raw if isinstance(values_raw, Mapping) else {}
    manifest_raw = parameters.get("manifest")
    manifest: Mapping[str, Any] = manifest_raw if isinstance(manifest_raw, Mapping) else {}
    standaard = ac.get("catalog_app") == IX_APP
    resources = values.get("resources") if isinstance(values.get("resources"), Mapping) else {}
    return {
        "soort": "installeren",
        "app": str(target.get("app_id") or ""),
        "installatiemethode": "standaard Custom App (ix-app-waarden via app.create)"
        if standaard
        else f"catalogusapp {ac.get('catalog_app')} ({ac.get('train')})",
        "custom_compose": False,
        "catalogus": {"app": ac.get("catalog_app"), "trein": ac.get("train"), "versie": ac.get("version")},
        "image": expected_image(parameters),
        "poorten": [
            {
                "host_poort": p.get("port_number"),
                "container_poort": p.get("container_port"),
                "protocol": p.get("protocol", "tcp"),
                "bind_mode": p.get("bind_mode", "published"),
            }
            for p in _lijst(values.get("ports"))
            if isinstance(p, Mapping)
        ],
        "opslag": [
            {
                "type": s.get("type"),
                "mount_path": s.get("mount_path"),
                "host_path": (s.get("host_path_config") or {}).get("path")
                if isinstance(s.get("host_path_config"), Mapping)
                else None,
                "alleen_lezen": bool(s.get("read_only", False)),
            }
            for s in _lijst(values.get("storage"))
            if isinstance(s, Mapping)
        ],
        # Alleen de namen: een waarde kan een geheim zijn en hoort nooit in een preview, log of audit.
        "omgevingsvariabelen": sorted(
            str(e.get("name")) for e in _lijst(values.get("envs")) if isinstance(e, Mapping) and e.get("name")
        ),
        "kluisverwijzingen": vault_refs(parameters),
        "resources": resources,
        "gpu": bool((resources or {}).get("gpus")) or bool(manifest.get("gpu")),
        "restart_policy": values.get("restart_policy"),
        "host_network": bool(values.get("host_network", False)),
        "host_network_reden": manifest.get("host_network_reason"),
        "privileged": False,
        "manifest": {
            k: manifest.get(k) for k in ("app_id", "version", "image_digest", "manifest_sha256") if k in manifest
        },
        "reden_catalogusapp": manifest.get("install_reason"),
        "controles_na_installatie": _lijst(manifest.get("post_install_checks")),
    }


def _wijziging(actie: ActieDef, target: Mapping[str, Any], parameters: Mapping[str, Any], doel: Doel) -> dict[str, Any]:
    aid = actie.action_id
    if aid == "app.install":
        return _install(target, parameters)
    if aid == "app.uninstall":
        return {
            "soort": "verwijderen",
            "app": doel.naam,
            "alleen_containers": True,
            "remove_ix_volumes": False,
            "remove_images": False,
        }
    if aid == "app.update":
        if "image" in parameters:
            return {
                "soort": "bijwerken",
                "app": doel.naam,
                "van": doel.staat.get("images"),
                "naar": expected_image(parameters),
            }
        return {
            "soort": "bijwerken",
            "app": doel.naam,
            "van": doel.staat.get("versie"),
            "naar_catalogusversie": parameters.get("catalog_version"),
        }
    if aid == "app.rollback":
        if "herstel_van" in parameters:
            return {
                "soort": "terugzetten",
                "app": doel.naam,
                "methode": "app.update met de vorige waarden die de executor bij die wijziging bewaarde",
                "herstel_van": parameters.get("herstel_van"),
            }
        return {"soort": "terugzetten", "app": doel.naam, "naar_catalogusversie": parameters.get("catalog_version")}
    if aid in ("app.restart", "app.stop", "app.start"):
        return {"soort": aid.split(".", 1)[1], "app": doel.naam, "verwacht": dict(actie.verwacht)}
    if aid == "zfs.snapshot.create":
        return {
            "soort": "snapshot_maken",
            "snapshot": f"{doel.naam}@{parameters.get('naam')}",
            "recursief": bool(parameters.get("recursief", False)),
        }
    if aid == "zfs.snapshot.clone_to_sandbox":
        return {"soort": "snapshot_klonen", "snapshot": doel.naam, "naar": parameters.get("doel_dataset")}
    if aid == "notification.send":
        return {"soort": "melding", "titel": parameters.get("titel"), "prioriteit": parameters.get("prioriteit", 2)}
    return {"soort": aid}


def _terugdraaien(aid: str) -> str:
    return {
        "app.install": "Verwijderen met app.uninstall (alleen de containers); de aangemaakte data blijft staan.",
        "app.uninstall": "Opnieuw installeren met app.install en dezelfde opslag; de data is niet verwijderd.",
        "app.update": "Terugzetten met app.rollback (herstel_van = dit verzoek); data via de eigenaar of een snapshot.",
        "app.rollback": "Opnieuw bijwerken met app.update, of nogmaals terugzetten met de waarden van dit verzoek.",
        "app.stop": "Starten met app.start.",
        "app.start": "Stoppen met app.stop.",
        "app.restart": "Niet nodig: de app wordt opnieuw uitgerold met dezelfde instellingen.",
        "zfs.snapshot.create": "Een snapshot wijzigt geen data; verwijderen doet een beheerder zelf in TrueNAS.",
        "zfs.snapshot.clone_to_sandbox": "De sandbox-dataset verwijdert een beheerder zelf in TrueNAS.",
        "notification.send": "Een verstuurde melding kan niet worden teruggehaald.",
    }.get(aid, "Geen automatische weg terug bekend.")


def bouw(
    policy: Policy,
    actie: ActieDef,
    cls: Classification,
    target: Mapping[str, Any],
    parameters: Mapping[str, Any],
    doel: Doel,
) -> tuple[dict[str, Any], str]:
    """``(preview, preview_hash)``."""
    preview: dict[str, Any] = {
        "schema": SCHEMA,
        "action_id": actie.action_id,
        "omschrijving": actie.omschrijving,
        "target": dict(target),
        "parameters_sha256": execreq.parameters_sha256(parameters),
        "uitvoerder": actie.uitvoerder,
        "risk_class": cls.risk_class,
        "rule_ids": list(cls.rule_ids),
        "goedkeuring_nodig": cls.requires_approval,
        "requires_backup": cls.requires_backup,
        "opslagmutatie": cls.opslagmutatie,
        "herkend_als": cls.herkend_als,
        "kritiek": cls.kritiek,
        "policy_hash": policy.hash,
        "resource_etag": doel.etag,
        "huidig": doel.staat,
        "wijziging": _wijziging(actie, target, parameters, doel),
        "dataretentie": DATA_BLIJFT,
        "terugdraaien": _terugdraaien(actie.action_id),
    }
    return preview, canonical_sha256(preview)
