"""Koppelingsgegevens voor TrueNAS: adres uit besluit D03, alleen-lezen-key uit de vault, TLS-vingerafdruk.

Het NAS-adres wordt **nooit** aangenomen: zonder ingevuld D03 is de koppeling ``not_configured``.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from hub.config import Settings
from hub.inventory.collector import ALL_KINDS, CollectResult, KindResult, collect
from hub.models import Decision, TrueNASConnection
from hub.timeutil import utcnow
from hub.truenas.client import TLSSettings, build_ws_url
from hub.truenas.messages import message
from hub.vault import Vault, make_ref

API_KEY_REF = make_ref("truenas", "readonly-api-key")


@dataclass(frozen=True)
class NasTarget:
    url: str
    host: str
    port: int | None


def current_target(db: Session) -> NasTarget | None:
    d03 = db.get(Decision, "D03")
    if d03 is None or d03.status not in ("Ingevuld", "Getest") or not isinstance(d03.waarde, dict):
        return None
    host = str(d03.waarde.get("nas_adres") or "")
    port = d03.waarde.get("https_poort")
    try:
        url = build_ws_url(host, int(port) if port else None)
    except ValueError:
        return None
    return NasTarget(url=url, host=host, port=int(port) if port else None)


def connection_row(db: Session) -> TrueNASConnection:
    row = db.get(TrueNASConnection, 1)
    if row is None:
        row = TrueNASConnection(id=1, last_test_detail={})
        db.add(row)
        db.flush()
    return row


def tls_for(row: TrueNASConnection, target: NasTarget, settings: Settings) -> TLSSettings:
    pinned = row.pinned_fingerprint if row.pinned_for_url == target.url else None
    return TLSSettings(pinned_fingerprint=pinned, extra_ca_file=settings.truenas_extra_ca_file)


def not_configured(kinds: tuple[str, ...], detail: str, url: str = "") -> CollectResult:
    res = CollectResult(status="unknown", reason_code="not_configured", target_url=url)
    res.kinds = [KindResult(k, "unknown", "not_configured", detail, None, None, utcnow()) for k in kinds]
    return res


async def run_collect(
    db: Session, vault: Vault, settings: Settings, kinds: tuple[str, ...] = ALL_KINDS
) -> CollectResult:
    target = current_target(db)
    if target is None:
        return not_configured(kinds, "Besluit D03 (NAS-adres) is nog niet ingevuld.")
    api_key = vault.get(db, API_KEY_REF)
    if not api_key:
        return not_configured(kinds, "Er is nog geen alleen-lezen-API-key ingesteld.", target.url)
    row = connection_row(db)
    return await collect(
        target.url,
        api_key,
        tls=tls_for(row, target, settings),
        connect_timeout=settings.truenas_connect_timeout,
        read_timeout=settings.truenas_read_timeout,
        kinds=kinds,
    )


def record_test(row: TrueNASConnection, result: CollectResult) -> None:
    row.last_test_at = utcnow()
    row.last_test_url = result.target_url
    row.last_test_status = result.status
    row.last_test_reason = result.reason_code
    row.last_test_detail = {
        "melding": message(result.reason_code) if result.reason_code else "",
        "nas_versie": result.nas_version,
        "key_scope": result.key_scope,
        "tls_modus": result.tls_mode,
        **{
            k: v
            for k, v in result.error_details.items()
            if k in ("detail", "fingerprint_sha256", "fingerprint_weergave", "bevestigd", "http", "method")
        },
    }
    row.updated_at = utcnow()
