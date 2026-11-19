"""MSO-antwoordvorm en de grens rond beschermde datasets."""

import json
import uuid
from ipaddress import IPv4Address
from unittest.mock import Mock

import pytest

from hub import outbound
from hub.adapters import basis, mso
from hub.models import AdapterLink


@pytest.fixture
def link() -> AdapterLink:
    return AdapterLink(
        app_id="media-source-optimizer",
        basis_url="https://mso.example",
        peer_addresses=[str(IPv4Address(bytes((192, 0, 2, 1))))],
    )


def test_beschermde_datasets_blijven_onbeschikbaar(link: AdapterLink, monkeypatch: pytest.MonkeyPatch) -> None:
    transport = Mock()
    monkeypatch.setattr(outbound, "request", transport)
    policy = outbound.OutboundPolicy()
    for path in (
        "/api/v1/system/info",
        "/api/v1/system/health",
        "/api/v1/overview",
        "/api/v1/usenet/failure-reasons",
        "/api/v1/usenet/categories/diagnosis",
        "/api/v1/mediaguard/compat",
        "/api/v1/costs/summary",
        "/api/v1/system/maintenance",
        "/api/v1/changes?status=preview",
        "/connector/v1/discover",
        "/connector/v1/health",
        "/connector/v1/items",
        "/readyz",
        "/api/v1/setup/status?refresh=true",
    ):
        with pytest.raises(outbound.OutboundError, match="capability_unavailable"):
            basis.read_request(link, path, policy=policy)
    link.app_id = "mediaguard"
    with pytest.raises(outbound.OutboundError, match="capability_unavailable"):
        basis.read_request(link, "/api/v1/setup/status", policy=policy)
    adapter: basis.ReadAdapter = mso
    assert adapter.discover()["permissions"] == []
    assert adapter.health() == basis.Measurement(status="unknown", reason_code="capability_unavailable")
    assert adapter.items("change_set", cursor=None, limit=50) == {
        "status": "unknown",
        "reason_code": "capability_unavailable",
        "observed_at": None,
        "items": [],
    }
    transport.assert_not_called()


@pytest.mark.parametrize(
    "body",
    [
        b"<html>ok</html>",
        b'{"setup_required":0,"completed":true,"version":"1.6.0"}',
        b'{"setup_required":true,"completed":true,"version":"1.6.0"}',
        b'{"setup_required":false,"completed":true,"version":"https://voorbeeld.invalid"}',
        b'{"setup_required":false,"version":"1.6.0"}',
    ],
)
def test_ongeldige_setup_levert_geen_meting(link: AdapterLink, monkeypatch: pytest.MonkeyPatch, body: bytes) -> None:
    transport = Mock(
        side_effect=[outbound.Response(200, b'{"status":"ok","version":"1.6.0"}'), outbound.Response(200, body)]
    )
    monkeypatch.setattr(outbound, "request", transport)
    result = mso.public_probes(link, outbound.OutboundPolicy())
    assert result.probes.healthz is not None
    assert result.probes.setup is None
    assert result.connection == basis.Measurement(status="unknown", reason_code="antwoord_ongeldig")


@pytest.mark.parametrize(("code", "valid_id"), [("forbidden", True), ("forbidden", False), ("onbekend", True)])
def test_foutcorrelatie_vereist_bekende_code_en_vorm(
    link: AdapterLink, monkeypatch: pytest.MonkeyPatch, code: str, valid_id: bool
) -> None:
    correlation_id = uuid.uuid4().hex[:12] if valid_id else "bron bevat vrije tekst"
    body = json.dumps({"detail": "Vrije brontekst", "code": code, "correlation_id": correlation_id}).encode()
    monkeypatch.setattr(
        outbound,
        "request",
        Mock(
            side_effect=[
                outbound.Response(403, body),
                outbound.Response(200, b'{"setup_required":true,"completed":false,"version":"1.6.0"}'),
            ]
        ),
    )
    result = mso.public_probes(link, outbound.OutboundPolicy())
    assert result.probes.healthz is None
    assert result.probes.setup and result.probes.setup.setup_required
    assert result.connection == basis.Measurement(status="unknown", reason_code="bron_credential_geweigerd")
    assert result.failures[0].correlation_id == (correlation_id if valid_id and code == "forbidden" else None)
