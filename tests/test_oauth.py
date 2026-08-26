"""Test the Azure AD B2C specifics of the OAuth2 implementation."""

from __future__ import annotations

import time

from homeassistant.core import HomeAssistant

from custom_components.enua.const import API_BASE, API_SCOPE, OAUTH2_TOKEN
from custom_components.enua.oauth import async_get_implementation


async def test_refresh_request_includes_resource_scope(
    hass: HomeAssistant, aioclient_mock
) -> None:
    """B2C must be told the resource scope again when refreshing.

    Without it the new access token is issued for our own client id and the
    Enua API answers 401.
    """
    implementation = async_get_implementation(hass)

    aioclient_mock.post(
        OAUTH2_TOKEN,
        json={
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "token_type": "Bearer",
            "expires_in": 3600,
        },
    )

    token = await implementation.async_refresh_token(
        {
            "access_token": "old",
            "refresh_token": "old-refresh",
            "expires_in": 3600,
            "expires_at": time.time() - 10,
        }
    )

    assert token["access_token"] == "new-access-token"
    request = aioclient_mock.mock_calls[0][2]
    assert request["grant_type"] == "refresh_token"
    assert API_SCOPE in request["scope"]
    assert "offline_access" in request["scope"]
    # Public client: no secret may be sent.
    assert "client_secret" not in request


async def test_implementation_is_shared(hass: HomeAssistant) -> None:
    """The PKCE verifier lives on the instance, so it must be reused."""
    first = async_get_implementation(hass)
    second = async_get_implementation(hass)
    assert first is second
    assert first.code_verifier == second.code_verifier
    assert first.client_secret == ""


async def test_api_base_is_enua_cloud() -> None:
    """Guard against a typo in the base URL."""
    assert API_BASE == "https://api.enua.io"
