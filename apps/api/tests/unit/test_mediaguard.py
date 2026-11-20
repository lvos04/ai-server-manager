"""Bescherm de lege lijst met bewezen alleen-lezen MediaGuard-routes."""

from unittest.mock import Mock

import pytest

from hub import outbound
from hub.adapters import basis
from hub.models import AdapterLink


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/health",
        "/api/v1/auth/me",
        "/api/v1/status",
        "/api/v1/mediaserver/status",
        "/api/v1/attention",
        "/api/v1/wanted",
        "/api/v1/downloads/health",
        "/api/v1/encoding/jobs",
        "/api/v1/storage/forecast",
        "/api/v1/backups",
        "/connector/v1/discover",
        "/connector/v1/health",
        "/connector/v1/items",
        "/healthz",
        "/readyz",
        "/onbekend",
    ],
)
def test_geen_bewezen_alleen_lezen_route(path: str, monkeypatch: pytest.MonkeyPatch) -> None:
    link = AdapterLink(app_id="mediaguard", basis_url="https://bron.example", peer_addresses=["peer"])
    transport = Mock(side_effect=AssertionError("MediaGuard heeft een verzoek ontvangen."))
    monkeypatch.setattr(outbound, "request", transport)

    with pytest.raises(outbound.OutboundError, match="capability_unavailable"):
        basis.read_request(link, path, policy=outbound.OutboundPolicy())

    transport.assert_not_called()
