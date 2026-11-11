"""Resource-ETag van een doel, uit ruwe TrueNAS-readback (contract 1.3 §8 "precondities via readback (ETag/digest)";
B01-007: "preview hash + target resource ETag"; ADR-0030).

De Hub (alleen-lezen-key, bij inventaris en bij goedkeuren) en de executor (schrijfkey, vlak vóór uitvoering) rekenen
de ETag met **deze** functie uit hun eigen ``app.query`` + ``app.image.query``. Een andere image, digest,
catalogusversie of staat geeft een andere ETag: een goedkeuring vervalt dan (EX19) en de executor weigert (afwijking →
geen uitvoering).
De app-configuratie (``retrieve_config``) telt bewust niet mee: die kan geheimen bevatten en de Hub leest hem nooit.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from asm_policy.canonical import canonical_sha256
from asm_policy.params import IX_APP

ABSENT = "absent"


def app_images(app: Mapping[str, Any]) -> list[str]:
    raw = app.get("active_workloads")
    wl: Mapping[str, Any] = raw if isinstance(raw, Mapping) else {}
    refs = [str(i) for i in (wl.get("images") or []) if i]
    for c in wl.get("container_details") or []:
        if isinstance(c, Mapping) and c.get("image") and str(c["image"]) not in refs:
            refs.append(str(c["image"]))
    return sorted(set(refs))


def catalogus_app(app: Mapping[str, Any]) -> str:
    """De catalogusapp (``metadata.name``) als die zegt wát er draait; anders ``""``.

    Bij een catalogusapp liggen de images vast in de catalogus: het formulier laat hooguit kiezen uit de images van die
    app (``image_selector``), nooit een eigen repository (gelezen in ``truenas/apps``, o.a. emby, plex, jellyfin; NIET
    GEVALIDEERD op een echte NAS). De naam van de catalogusapp is ook te lezen als de app gestopt is en TrueNAS geen
    image toont. Een standaard
    Custom App (``ix-app``) en een compose-app (``custom_app``) kunnen elke image draaien: daar zegt de catalogusnaam
    niets over de inhoud."""
    raw = app.get("metadata")
    meta: Mapping[str, Any] = raw if isinstance(raw, Mapping) else {}
    naam = str(meta.get("name") or "").strip().lower()
    if not naam or naam == IX_APP or app.get("custom_app") is not False:
        return ""
    return naam


def _repo(ref: str) -> str:
    name = ref.split("@", 1)[0]
    last = name.rsplit("/", 1)[-1]
    return name.rsplit(":", 1)[0] if ":" in last else name


def image_digests(refs: Iterable[str], images: Iterable[Mapping[str, Any]]) -> list[str]:
    """``repo@sha256:…`` uit ``app.image.query`` voor de images van de app (op ``repo_tags``; een digest in de tag zelf
    telt ook)."""
    wanted = set(refs)
    out: set[str] = set()
    for ref in wanted:
        if "@sha256:" in ref:
            out.add(f"{_repo(ref)}@{ref.split('@', 1)[1]}")
    for img in images:
        if not isinstance(img, Mapping):
            continue
        tags = {str(t) for t in img.get("repo_tags") or []}
        if tags & wanted:
            out.update(str(d) for d in img.get("repo_digests") or [] if d)
    return sorted(out)


def app_state(app: Mapping[str, Any], images: Iterable[Mapping[str, Any]] = ()) -> dict[str, Any]:
    raw = app.get("metadata")
    meta: Mapping[str, Any] = raw if isinstance(raw, Mapping) else {}
    refs = app_images(app)
    return {
        "naam": str(app.get("name") or app.get("id") or ""),
        "staat": str(app.get("state") or ""),
        "catalogus_app": str(meta.get("name") or ""),
        "trein": str(meta.get("train") or ""),
        "versie": str(app.get("version") or ""),
        "custom_app": bool(app.get("custom_app")),
        "images": refs,
        "digests": image_digests(refs, list(images)),
    }


def app_etag(app: Mapping[str, Any] | None, images: Iterable[Mapping[str, Any]] = ()) -> str:
    if app is None:
        return ABSENT
    return canonical_sha256(app_state(app, images))


def dataset_etag(name: str) -> str:
    return f"dataset:{name}"


def snapshot_etag(name: str) -> str:
    return f"snapshot:{name}"
