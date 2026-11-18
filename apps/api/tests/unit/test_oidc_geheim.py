"""Zonder clientgeheim nooit uitgaand tokenverkeer, ook niet via de losse OIDC-client."""

from typing import Any

import pytest

from hub.oidc import client
from hub.outbound import OutboundPolicy


@pytest.mark.parametrize("secret", [None, ""])
def test_geen_publieke_tokenaanvraag(monkeypatch: pytest.MonkeyPatch, secret: str | None) -> None:
    calls = []

    def request(*args: Any, **kwargs: Any) -> Any:
        calls.append(True)
        raise AssertionError("Tokenaanroep zonder geheim")

    monkeypatch.setattr(client, "request", request)
    with pytest.raises(client.OidcError, match="clientgeheim"):
        client.exchange_code(
            {"token_endpoint": "https://idp.invalid/token"},
            client_id="testclient",
            client_secret=secret,
            redirect_uri="https://hub.invalid/api/v1/auth/oidc/callback",
            code="testcode",
            verifier="testverifier",
            policy=OutboundPolicy(),
        )
    assert not calls
