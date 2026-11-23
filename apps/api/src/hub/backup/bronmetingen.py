"""De worker leest de twee toegestane adapters en het archief. Scherm en gate lezen dezelfde Hub-metingen."""

from __future__ import annotations

from collections import Counter
from datetime import UTC
from typing import Any
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from hub import outbound
from hub.adapters import mediaguard_lezen
from hub.adapters.binding import binding_is_current, published_ports
from hub.backup.appdekking import EMBY, HUIS, MG, MSO, AppBronnen, Meting, herstelrapport, tijd
from hub.backup.emby_archief import lees_archief
from hub.config import Settings
from hub.incidents.downloadketen import Bron, Bronfout, mediaguard_lezer
from hub.inventory.store import kind_state
from hub.models import AdapterLink, CatalogApp, Decision, HubSetting, PeriodicTask
from hub.onboarding.catalog import D16Waarde
from hub.timeutil import utcnow
from hub.truenas.connection import current_target
from hub.truenas.normalize import recognize_app
from hub.vault import Vault

TAAK = "app_backups_meten"
SLEUTEL = "backup.appmetingen"


def rpo_doelen(db: Session) -> dict[str, dict[str, float]]:
    besluit = db.get(Decision, "D16")
    if besluit is None or besluit.status not in ("Ingevuld", "Getest"):
        return {}
    try:
        doelen = D16Waarde.model_validate(besluit.waarde, strict=True).per_app
    except ValidationError:
        return {}
    return {d.app_id: {"rpo_uren": d.rpo_uren, "rto_uren": d.rto_uren} for d in doelen}


def _herkenningen(rij: dict[str, Any]) -> set[str | None]:
    # Toets iedere identiteit apart: één herkende naam mag een tegengesteld image niet verbergen.
    namen = [rij["naam"], rij["runtime_id"], rij.get("catalogus_app")]
    bekend = {recognize_app(naam, []) for naam in namen if naam}
    if rij["herkend_als"]:
        bekend.add(recognize_app(rij["herkend_als"], []))
    images = rij.get("images")
    if not isinstance(images, list):
        return {None}
    for image in images:
        if not isinstance(image, dict) or not isinstance(image.get("repository"), str) or not image["repository"]:
            return {None}
        for waarde in (image.get("image"), image["repository"]):
            if isinstance(waarde, str):
                bekend.add(recognize_app("", [waarde]))
    return {app for app in bekend if app} or {None}


def _bronnen(db: Session, settings: Settings) -> tuple[AppBronnen, dict[str, tuple[AdapterLink, CatalogApp]]]:
    nas = current_target(db)
    inventaris = kind_state(
        db,
        "apps",
        target=nas.url if nas else None,
        ttl_seconds=settings.inventory_max_age_seconds,
        include_identity=True,
    )
    nu = utcnow()
    try:
        inventaris_tot = tijd(inventaris.get("geldig_tot"))
        actueel = tijd(inventaris.get("observed_at")) <= nu <= inventaris_tot
    except ValueError:
        inventaris_tot, actueel = nu, False
    apps = inventaris.get("data")
    geldig = (
        nas is not None
        and actueel
        and inventaris.get("status") == "ok"
        and isinstance(apps, list)
        and all(
            isinstance(a, dict)
            and isinstance(a.get("runtime_id"), str)
            and a["runtime_id"]
            and isinstance(a.get("naam"), str)
            and a["naam"]
            and "herkend_als" in a
            and (a["herkend_als"] is None or isinstance(a["herkend_als"], str))
            and (a.get("catalogus_app") is None or isinstance(a["catalogus_app"], str))
            for a in apps
        )
    )
    rijen = apps if geldig and isinstance(apps, list) else []
    if len({a["runtime_id"] for a in rijen}) != len(rijen) or len({a["naam"] for a in rijen}) != len(rijen):
        geldig, rijen = False, []
    herkenningen = {rij["runtime_id"]: _herkenningen(rij) for rij in rijen}
    aantal = Counter(app for kandidaten in herkenningen.values() for app in kandidaten)
    eenduidig = geldig and all(len(k) == 1 and None not in k for k in herkenningen.values())
    bronnen = AppBronnen(afwezig={app for app in (HUIS, MSO) if eenduidig and not aantal[app]})
    doelen = rpo_doelen(db)
    bronnen.rpo_uren = {app: doel["rpo_uren"] for app, doel in doelen.items()}
    for rij in rijen:
        app = rij["herkend_als"]
        namen = {s.lower() for s in (app, rij["naam"], rij["runtime_id"], rij.get("catalogus_app")) if s}
        grenzen = [doelen[k]["rpo_uren"] for k in namen.intersection(doelen)]
        if app and grenzen:
            bronnen.rpo_uren[app] = min(grenzen)
    koppelingen = {}
    if geldig:
        poorten = published_ports(inventaris)
        for link, target in db.execute(
            select(AdapterLink, CatalogApp).join(CatalogApp).where(AdapterLink.app_id.in_((MG, HUIS)))
        ):
            app = link.app_id
            grenzen_per_id = inventaris["identiteit_sinds"]
            if (
                target.runtime_id in grenzen_per_id
                and herkenningen.get(target.runtime_id) == {app}
                and aantal[app] == 1
                and binding_is_current(link, target, nas, poorten)
            ):
                tijden = (grenzen_per_id[target.runtime_id], target.bron.get("identiteit_sinds"))
                try:
                    sinds = max((tijd(t.replace("+00:00", "Z")) for t in tijden if t is not None), default=None)
                except (AttributeError, ValueError):
                    continue
                if sinds is not None:
                    bronnen.identiteit_sinds[app] = sinds
                koppelingen[app] = (link, target)
                bronnen.binding_tot[app] = inventaris_tot
                if app == HUIS and link.my_house_expires_at is not None:
                    bronnen.binding_tot[app] = min(inventaris_tot, link.my_house_expires_at)
    return bronnen, koppelingen


def _meting(record: object) -> Meting | None:
    if not isinstance(record, dict):
        return None
    try:
        return Meting.model_validate(record.get("meting"))
    except ValidationError:
        return None


def lees(db: Session, settings: Settings) -> AppBronnen:
    bronnen, koppelingen = _bronnen(db, settings)
    # Eén databaselezing voor de uitkomst én de bijbehorende meetrij, ook tijdens een nieuwe workerpoging.
    rij = db.execute(
        select(HubSetting.waarde, PeriodicTask.details, PeriodicTask.laatste_status, PeriodicTask.laatst_gestart)
        .select_from(PeriodicTask)
        .outerjoin(HubSetting, HubSetting.sleutel == SLEUTEL)
        .where(PeriodicTask.naam == TAAK)
    ).one_or_none()
    if rij is None:
        return bronnen
    opslag, details, status, gestart = rij
    ronde = details.get("meetronde") if isinstance(details, dict) else None
    if (
        status != "ok"
        or not isinstance(ronde, str)
        or not ronde
        or not isinstance(opslag, dict)
        or opslag.get("meetronde") != ronde
    ):
        for app in (MG, HUIS, EMBY):
            bronnen.metingen[app] = Meting(
                status="unknown", reden="meetronde", observed_at=gestart.astimezone(UTC) if gestart else utcnow()
            )
        return bronnen
    for app in (MG, HUIS, EMBY):
        record = opslag.get(app)
        meting = _meting(record)
        if meting is None or not isinstance(record, dict):
            continue
        if (
            app == EMBY
            and meting.status != "unknown"
            and (not settings.emby_inventaris_sha256 or record.get("bronreferentie") != settings.emby_inventaris_sha256)
        ):
            bronnen.metingen[app] = Meting(status="unknown", reden="leesbewijs", observed_at=meting.observed_at)
            continue
        if app != EMBY:
            if app not in koppelingen:
                continue
            link, target = koppelingen[app]
            if (
                record.get("link") != str(link.id)
                or type(record.get("versie")) is not int
                or record["versie"] != link.version
            ):
                continue
            if app == HUIS and (link.my_house_expires_at is None or link.my_house_expires_at <= utcnow()):
                continue
            bronnen.runtime_ids[app] = target.runtime_id
        bronnen.metingen[app] = meting
    return bronnen


def _lees_adapter(db: Session, settings: Settings, vault: Vault, link: AdapterLink, target: CatalogApp) -> Meting:
    from hub.routers.adapterkoppelingen import lees_huisbackup

    try:
        if link.app_id == HUIS:
            return lees_huisbackup(db, settings, vault, link, target)
        bron = Bron(db, settings, "mediaguard", link, None)
        get = mediaguard_lezer(bron, vault, uuid4())
        aanbod = mediaguard_lezen.aanbod(get("/connector/v1/discover"))
        if aanbod is None or "backups" not in aanbod[0]:
            raise Bronfout("geen herstelrapport")
        pagina = get("/connector/v1/items", query={"type": "backups", "limit": "1"})
        return herstelrapport(pagina, utcnow(), mediaguard_lezen.grens(aanbod[1], "backups"))
    except (outbound.OutboundError, Bronfout, ValueError, OSError, RecursionError):
        return Meting(status="unknown", reden="onbereikbaar", observed_at=utcnow())


def verzamel(db: Session, settings: Settings, vault: Vault, meetronde: str | None) -> dict[str, Any]:
    # Een ingehaalde worker mag de resultaten van een nieuwere poging nooit vervangen.
    poging = db.scalar(
        select(PeriodicTask)
        .where(PeriodicTask.naam == TAAK)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if poging is None or not meetronde or poging.details.get("meetronde") != meetronde:
        return {"aantal": 0}
    # Eén vaste rij en een transactieslot vóór de eerste lezing, ook wanneer twee workers tegelijk starten.
    db.execute(insert(HubSetting).values(sleutel=SLEUTEL, waarde={}, gewijzigd_door=TAAK).on_conflict_do_nothing())
    opslag = db.scalars(select(HubSetting).where(HubSetting.sleutel == SLEUTEL).with_for_update()).one()
    _, koppelingen = _bronnen(db, settings)
    storing = tijd(poging.details["storing_sinds"]) if "storing_sinds" in poging.details else None
    metingen = {}
    for app in (MG, HUIS, EMBY):
        identiteit: dict[str, Any] = {}
        if app == EMBY:
            nieuw = lees_archief(
                settings.data_dir / "overname", settings.backups_dir, utcnow(), settings.emby_inventaris_sha256
            )
            if nieuw.status != "unknown":
                identiteit = {"bronreferentie": settings.emby_inventaris_sha256}
        elif app in koppelingen:
            link, target = koppelingen[app]
            identiteit = {"link": str(link.id), "versie": link.version}
            nieuw = _lees_adapter(db, settings, vault, link, target)
            if nieuw.status == "gedekt" and nieuw.observed_at < link.ingevoerd_op:
                nieuw = Meting(status="unknown", reden="volgorde", observed_at=link.ingevoerd_op.astimezone(UTC))
        else:
            nieuw = Meting(status="unknown", reden="geen_meting", observed_at=utcnow())
        if storing is not None and nieuw.status == "gedekt" and nieuw.observed_at <= storing:
            nieuw = Meting(status="unknown", reden="volgorde", observed_at=storing)
        vorige = _meting(opslag.waarde.get(app)) if isinstance(opslag.waarde, dict) else None
        if vorige is not None and nieuw.observed_at <= vorige.observed_at and nieuw != vorige:
            # Een oudere of gelijktijdige herhaling mag nooit een storing opheffen, ook na herkoppeling.
            nieuw = Meting(status="unknown", reden="volgorde", observed_at=vorige.observed_at)
        metingen[app] = {**identiteit, "meting": nieuw.model_dump(mode="json")}
    opslag.waarde = {**metingen, "meetronde": meetronde}
    opslag.gewijzigd_op = utcnow()
    return {"aantal": len(metingen), "meetronde": meetronde}
