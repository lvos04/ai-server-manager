"""TrueNAS-adapter tegen de fake WebSocketserver: TLS, foutcodes, alleen-lezen en versieverschillen."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from typing import Any

import pytest
from fakes.fake_truenas import FakeTrueNAS, KeyProfile

from hub.inventory.collector import collect
from hub.truenas.client import TLSSettings, TrueNASClient, TrueNASError, normalize_fingerprint

KEY = "readonly-test-key-0123456789"


@pytest.fixture(scope="module")
def nas() -> Iterator[FakeTrueNAS]:
    n = FakeTrueNAS(
        keys={KEY: KeyProfile(), "zonder-pools-0000000000": KeyProfile(deny={"pool.query", "core.get_methods"})}
    ).start()
    yield n
    n.stop()


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


def _err(coro: Any) -> TrueNASError:
    with pytest.raises(TrueNASError) as info:
        _run(coro)
    return info.value


async def _open(url: str, key: str, tls: TLSSettings, read_timeout: float = 3) -> TrueNASClient:
    c = TrueNASClient(url, key, tls=tls, connect_timeout=3, read_timeout=read_timeout)
    await c.open()
    return c


def test_alleen_wss(nas: FakeTrueNAS) -> None:
    with pytest.raises(TrueNASError) as e:
        TrueNASClient(nas.url.replace("wss://", "ws://"), KEY)
    assert e.value.reason_code == "not_configured"


def test_onvertrouwd_certificaat_geeft_vingerafdruk(nas: FakeTrueNAS) -> None:
    e = _err(_open(nas.url, KEY, TLSSettings()))
    assert e.reason_code == "tls_untrusted" and len(e.details["fingerprint_sha256"]) == 64


def test_extra_ca_en_pinning(nas: FakeTrueNAS) -> None:
    async def flow() -> tuple[Any, str | None]:
        c = await _open(nas.url, KEY, TLSSettings(extra_ca_file=nas.ca_file))
        try:
            return await c.call("system.version"), c.server_fingerprint
        finally:
            await c.close()

    version, fp = _run(flow())
    assert version == "TrueNAS-25.04.2" and fp
    pinned = TLSSettings(pinned_fingerprint=fp)

    async def pinned_flow() -> Any:
        c = await _open(nas.url, KEY, pinned)
        try:
            return await c.call("pool.query")
        finally:
            await c.close()

    assert _run(pinned_flow())[0]["name"] == "testpool"
    e = _err(_open(nas.url, KEY, TLSSettings(pinned_fingerprint=normalize_fingerprint("00" * 32))))
    assert e.reason_code == "tls_untrusted" and "gewijzigd" in e.detail


def test_foutcodes(nas: FakeTrueNAS) -> None:
    tls = TLSSettings(extra_ca_file=nas.ca_file)
    assert _err(_open(nas.url, "foute-key-123456789", tls)).reason_code == "auth_failed"
    assert _err(_open(nas.url.replace("/api/current", "/api/v99"), KEY, tls)).reason_code == "method_unavailable"
    assert _err(_open("wss://127.0.0.1:1/api/current", KEY, tls)).reason_code == "unreachable"

    async def calls() -> list[str]:
        c = await _open(nas.url, "zonder-pools-0000000000", tls, read_timeout=0.5)
        out = []
        try:
            for m in ("pool.query", "zfs.snapshot.query"):
                try:
                    await c.call(m)
                except TrueNASError as exc:
                    out.append(exc.reason_code)
            nas.delays["alert.list"] = 2
            try:
                await c.call("alert.list")
            except TrueNASError as exc:
                out.append(exc.reason_code)
            with pytest.raises(PermissionError):
                await c.call("app.delete", ["mediaguard"])
        finally:
            nas.delays.clear()
            await c.close()
        return out

    assert _run(calls()) == ["permission_denied", "method_unavailable", "timeout"]
    assert nas.mutations == []


def test_collector_valt_terug_op_versietabel(nas: FakeTrueNAS) -> None:
    res = _run(
        collect(
            nas.url,
            "zonder-pools-0000000000",
            tls=TLSSettings(extra_ca_file=nas.ca_file),
            connect_timeout=3,
            read_timeout=3,
        )
    )
    assert res.capabilities is not None and res.capabilities.source == "versietabel"
    assert res.capability_error == "permission_denied"
    kinds = {k.kind: k for k in res.kinds}
    assert kinds["pools"].status == "unknown" and kinds["pools"].reason_code == "permission_denied"
    assert kinds["apps"].status == "ok"
    assert res.status == "partial"
