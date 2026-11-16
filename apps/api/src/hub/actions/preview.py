"""Preview van een actie: wat er nu staat, wat er verandert en wat er blijft (B01-007, B01-003).

De preview is een pure functie van (beleid, classificatie, doel, parameters, eigen readback) — geen klok, geen
willekeur. ``preview_hash`` = SHA-256 over de canonieke JSON. Een beheerder keurt precies deze preview goed; verandert
er iets aan (andere image of digest op de NAS, ander beleid, andere risicoklasse), dan verandert de hash en vervalt de
goedkeuring (EX19).

Geheimen: waarden van omgevingsvariabelen staan nooit in de preview (alleen de namen); verwijzingen naar de kluis
(``vault://…``) worden als verwijzing getoond, nooit ingevuld.

Installeren (S-P2-040, R-VEILIG-1; ADR-0030 besluit 32): ``wijziging.waarden`` toont elk gezet veld van
``app_create.values`` mét zijn waarde, zodat een beheerder niets ongezien goedkeurt. Uitzonderingen: van ``envs``
alleen de namen, en een geheim (waarde onder een geheim-achtige sleutel, ook direct onder ``values``, of naast een
geheim-achtige ``key`` in een paar ``key`` + ``value``) als ``***``. Van elk paar ``name`` + ``value`` (zoals de
omgevingsvariabelen van een catalogusapp) staat alleen de naam erin; de waarde is altijd ``***`` (ADR-0030 besluit 28;
S-P2-040 herstelronde 2, R-VEILIG-5 en -6). ``command`` en ``entrypoint`` komen hier niet: die weigert de Hub al bij het
voorstel (:func:`eigen_opdracht`, besluit regisseur optie C) tot een installatiescherm ze veilig kan tonen.
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
from hub.redact import LOG_SECRET_KEY_RE, REDACTED, redact_text

SCHEMA = "asm-preview/1"
DATA_BLIJFT = "Datasets en data blijven staan; de Hub en de executor verwijderen nooit data."


def _lijst(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


# Hoe elk veld van de standaard Custom App (``asm_policy.params.IX_VALUES_KEYS``) in ``wijziging.waarden`` staat
# (S-P2-040, R-VEILIG-1). Een bewakingstest eist een regel voor elk veld dat het beleid toelaat: een nieuw veld zonder
# regel maakt hem rood (``apps/api/tests/integration/test_acties.py``).
WAARDE = "waarde"  # met zijn waarde (een geheim daarin als ***)
NAMEN = "namen"  # alleen de namen; de waarden kunnen geheimen zijn (ADR-0030 besluit 28)
GEWEIGERD = "geweigerd"  # de Hub weigert een voorstel met dit veld (501 capability_unavailable, eigen_opdracht)
IX_PREVIEWREGELS: dict[str, str] = {
    "notes": WAARDE,
    "image": WAARDE,
    "hostname": WAARDE,
    "entrypoint": GEWEIGERD,
    "command": GEWEIGERD,
    "TZ": WAARDE,
    "envs": NAMEN,
    "restart_policy": WAARDE,
    "max_retry_count": WAARDE,
    "disable_builtin_healthcheck": WAARDE,
    "tty": WAARDE,
    "stdin": WAARDE,
    "devices": WAARDE,
    "privileged": WAARDE,
    "capabilities": WAARDE,
    "run_as_custom_user": WAARDE,
    "run_as": WAARDE,
    "host_network": WAARDE,
    "ports": WAARDE,
    "networks": WAARDE,
    "dns_config": WAARDE,
    "portals": WAARDE,
    "storage": WAARDE,
    "labels": WAARDE,
    "resources": WAARDE,
}
EIGEN_OPDRACHT = tuple(sorted(k for k, regel in IX_PREVIEWREGELS.items() if regel == GEWEIGERD))
GEHEIM_DIEPTE = 24  # dieper dan de dieptegrens van het beleid (MAX_PARAMETER_DIEPTE): daar komt het nooit


def eigen_opdracht(action_id: str, parameters: Mapping[str, Any]) -> list[str]:
    """De velden ``command`` en ``entrypoint`` die in de waarden van een installatie staan (elke waarde, ook leeg).

    Besluit regisseur (S-P2-040, R-VEILIG-1 optie C): de Hub weigert zo'n voorstel met ``501 capability_unavailable``
    (``details.reden`` = ``eigen_opdracht``) tot er een installatiescherm is dat de opdracht veilig kan tonen; ook een
    open voorstel van vóór dat besluit wordt bij goedkeuren of uitvoeren geweigerd."""
    if action_id != "app.install":
        return []
    ac = parameters.get("app_create") if isinstance(parameters, Mapping) else None
    values = ac.get("values") if isinstance(ac, Mapping) else None
    if not isinstance(values, Mapping):
        return []
    return [k for k in EIGEN_OPDRACHT if k in values]


def _geheime_naam(naam: Any) -> bool:
    return isinstance(naam, str) and bool(LOG_SECRET_KEY_RE.search(naam))


def _verborgen(waarde: Any) -> bool:
    """Een waarde die als ``***`` verschijnt als hij geheim is: alles behalve leeg en ja/nee."""
    return waarde not in (None, "") and not isinstance(waarde, bool)


def _toon(waarde: Any, diepte: int = 0) -> Any:
    """Een waarde zoals de beheerder hem in de preview ziet: alles, behalve een geheim (``***``). Een geheim is de
    waarde onder een geheim-achtige sleutel (``hub.redact``), de ``value`` naast een geheim-achtige ``key``, en elke
    ``value`` in een paar ``name`` + ``value``: dat is de vorm van een omgevingsvariabele (zoals ``additional_envs`` van
    een catalogusapp), en daarvan staat alleen de naam in een preview (ADR-0030 besluit 28)."""
    if diepte > GEHEIM_DIEPTE:
        return REDACTED
    if isinstance(waarde, Mapping):
        paar_geheim = ("name" in waarde) or _geheime_naam(waarde.get("key"))
        uit: dict[str, Any] = {}
        for k, w in waarde.items():
            geheim = _geheime_naam(k) or (paar_geheim and k == "value")
            uit[str(k)] = REDACTED if geheim and _verborgen(w) else _toon(w, diepte + 1)
        return uit
    if isinstance(waarde, list):
        return [_toon(w, diepte + 1) for w in waarde]
    if isinstance(waarde, str):
        return redact_text(waarde)
    return waarde


def _waarden(standaard: bool, values: Mapping[str, Any]) -> dict[str, Any]:
    """Elk gezet veld van ``app_create.values`` (R-VEILIG-1). Bij de standaard Custom App volgens
    :data:`IX_PREVIEWREGELS` (een onbekend veld laat het beleid niet toe; mocht het er toch zijn, dan met waarde); bij
    een catalogusapp de eigen waarden zoals ze zijn, met geheimen als ``***``."""
    uit: dict[str, Any] = {}
    for k, w in values.items():
        regel = IX_PREVIEWREGELS.get(k, WAARDE) if standaard else WAARDE
        if regel == NAMEN:
            uit[k] = [str(e.get("name")) for e in _lijst(w) if isinstance(e, Mapping) and e.get("name")]
        elif regel == GEWEIGERD:
            uit[k] = {"geweigerd": "eigen_opdracht"}  # komt niet voor: het voorstel wordt al geweigerd
        elif _geheime_naam(k) and _verborgen(w):
            uit[str(k)] = REDACTED  # ook een geheim-achtige sleutel direct onder values (R-VEILIG-5)
        else:
            uit[str(k)] = _toon(w)
    return uit


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
        "waarden": _waarden(standaard, values),
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


TERUG_STOP_CUSTOM_APP = (
    "Niet via het platform. Een gestopte Custom App toont in TrueNAS geen image meer; het platform kan dan niet zien "
    "wat erin draait en weigert app.start (doel_niet_herkenbaar). Weer starten kan daarna alleen in de TrueNAS-web-UI."
)


def _terugdraaien(aid: str, doel: Doel) -> str:
    if aid == "app.stop" and not doel.herkend_als.na_stop_herkenbaar:
        # ADR-0030 besluit 21: daarom is dit R2 en vraagt het altijd een goedkeuring van een beheerder.
        return TERUG_STOP_CUSTOM_APP
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
        "terugdraaien": _terugdraaien(actie.action_id, doel),
    }
    return preview, canonical_sha256(preview)
