"""Versheid en transportgrenzen van leesadapters met lokale testdubbels."""

from datetime import UTC, datetime, timedelta
from ipaddress import IPv4Address
from unittest.mock import Mock

import pytest

from hub import outbound
from hub.adapters.basis import Measurement, fresh_measurement

PEER = str(IPv4Address(bytes((192, 0, 2, 1))))
OTHER_PEER = str(IPv4Address(bytes((192, 0, 2, 2))))
URL = "https://bron.example"


def test_versheid_gebruikt_de_strengste_grens() -> None:
    now = datetime(2026, 11, 19, tzinfo=UTC)
    for seconds, max_age in [(901, 1800), (61, 60)]:
        observed = now - timedelta(seconds=seconds)
        fresh = fresh_measurement(Measurement(status="healthy", observed_at=observed), now=now, max_age_s=max_age)
        assert fresh.status == "unknown"
        assert fresh.reason_code == "meting_verouderd"
        assert fresh.observed_at == observed
    assert fresh_measurement(Measurement(status="down", observed_at=now), now=now).status == "down"
    assert fresh_measurement(Measurement(status="healthy"), now=now).status == "unknown"


def test_onbevestigde_dns_wordt_geweigerd_voor_verbinden(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(outbound, "resolve_peer_addresses", lambda *_args: frozenset({OTHER_PEER}))
    connect = Mock()
    monkeypatch.setattr(outbound.socket, "create_connection", connect)
    policy = outbound.OutboundPolicy(allowed_peer_addresses=frozenset({PEER}))
    with pytest.raises(outbound.OutboundError, match="doelbinding_gewijzigd"):
        outbound.request(URL, "GET", "/health", policy=policy)
    connect.assert_not_called()


def test_verbonden_peer_wordt_gecontroleerd_voor_tls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(outbound, "resolve_peer_addresses", lambda *_args: frozenset({PEER}))
    sock = Mock()
    sock.getpeername.return_value = (OTHER_PEER, 443)
    connect = Mock(return_value=sock)
    monkeypatch.setattr(outbound.socket, "create_connection", connect)
    tls = Mock()
    monkeypatch.setattr(outbound.ssl, "create_default_context", lambda *_args: tls)
    policy = outbound.OutboundPolicy(allowed_peer_addresses=frozenset({PEER}))
    with pytest.raises(outbound.OutboundError, match="doelbinding_gewijzigd"):
        outbound.request(URL, "GET", "/health", policy=policy)
    assert connect.call_args.args[0] == (PEER, 443)
    tls.wrap_socket.assert_not_called()
    sock.close.assert_called_once()


def test_gebonden_transport_verifieert_host_en_volgt_geen_redirect(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(outbound, "resolve_peer_addresses", lambda *_args: frozenset({PEER}))
    sock = Mock()
    sock.getpeername.return_value = (PEER, 443)
    connect = Mock(return_value=sock)
    monkeypatch.setattr(outbound.socket, "create_connection", connect)
    tls = Mock()
    monkeypatch.setattr(outbound.ssl, "create_default_context", lambda *_args: tls)
    response = Mock(status=302)
    response.read.return_value = b""
    monkeypatch.setattr(outbound.http.client.HTTPSConnection, "getresponse", lambda _self: response)
    policy = outbound.OutboundPolicy(allowed_peer_addresses=frozenset({PEER}))
    with pytest.raises(outbound.OutboundError, match="redirect_niet_gevolgd"):
        outbound.request(URL, "GET", "/health", policy=policy)
    tls.wrap_socket.assert_called_once_with(sock, server_hostname="bron.example")
    connect.assert_called_once()
