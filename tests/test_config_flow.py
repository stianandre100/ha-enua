"""Test the Enua Charge config flow."""

from __future__ import annotations

import base64
import json
from urllib.parse import parse_qs, urlparse

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.setup import async_setup_component
import pytest

from custom_components.enua.const import (
    API_SCOPE,
    DOMAIN,
    OAUTH2_AUTHORIZE,
    OAUTH2_TOKEN,
)

REDIRECT_URI = "https://example.com/auth/external/callback"


def _id_token(subject: str) -> str:
    """Build an unsigned JWT-shaped id_token."""

    def part(payload: dict) -> str:
        raw = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
        return raw.rstrip("=")

    return f"{part({'alg': 'none'})}.{part({'sub': subject})}.sig"


@pytest.fixture(autouse=True)
async def setup_http(hass: HomeAssistant) -> None:
    """The OAuth callback view needs the http integration."""
    assert await async_setup_component(hass, "http", {})


async def test_full_flow(
    hass: HomeAssistant,
    hass_client_no_auth,
    aioclient_mock,
    current_request_with_host: None,
) -> None:
    """A complete sign-in creates an entry with the token."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.EXTERNAL_STEP

    url = urlparse(result["url"])
    query = parse_qs(url.query)
    assert f"{url.scheme}://{url.netloc}{url.path}" == OAUTH2_AUTHORIZE
    assert query["redirect_uri"] == [REDIRECT_URI]
    assert query["response_type"] == ["code"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["code_challenge"]
    # The resource scope must be requested or B2C issues a token for our own
    # client id and the Enua API answers 401.
    assert API_SCOPE in query["scope"][0]
    assert "offline_access" in query["scope"][0]

    state = config_entry_oauth2_flow._encode_jwt(
        hass, {"flow_id": result["flow_id"], "redirect_uri": REDIRECT_URI}
    )
    client = await hass_client_no_auth()
    resp = await client.get(f"/auth/external/callback?code=abcd&state={state}")
    assert resp.status == 200

    aioclient_mock.post(
        OAUTH2_TOKEN,
        json={
            "refresh_token": "mock-refresh-token",
            "access_token": "mock-access-token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "id_token": _id_token("subject-123"),
        },
    )

    with (
        patch_setup_entry() as mock_setup,
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"])

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == "subject-123"
    assert result["data"]["token"]["access_token"] == "mock-access-token"
    assert len(mock_setup.mock_calls) == 1

    # The token request must carry the PKCE verifier and no client secret.
    token_request = aioclient_mock.mock_calls[0][2]
    assert token_request["grant_type"] == "authorization_code"
    assert token_request["code_verifier"]
    assert "client_secret" not in token_request


async def test_single_account_only(
    hass: HomeAssistant,
    hass_client_no_auth,
    aioclient_mock,
    current_request_with_host: None,
    config_entry,
) -> None:
    """Signing in with an already configured account aborts."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    state = config_entry_oauth2_flow._encode_jwt(
        hass, {"flow_id": result["flow_id"], "redirect_uri": REDIRECT_URI}
    )
    client = await hass_client_no_auth()
    await client.get(f"/auth/external/callback?code=abcd&state={state}")

    aioclient_mock.post(
        OAUTH2_TOKEN,
        json={
            "refresh_token": "mock-refresh-token",
            "access_token": "mock-access-token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "id_token": _id_token("subject-123"),
        },
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


def patch_setup_entry():
    """Patch async_setup_entry so the flow does not hit the API."""
    from unittest.mock import AsyncMock, patch

    return patch(
        "custom_components.enua.async_setup_entry",
        AsyncMock(return_value=True),
    )
