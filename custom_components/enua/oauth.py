"""OAuth2 (Authorization Code + PKCE) implementation for Enua Charge."""

from __future__ import annotations

from typing import Any, cast

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_entry_oauth2_flow

from .const import (
    CLIENT_ID,
    DATA_IMPLEMENTATION,
    DOMAIN,
    OAUTH2_AUTHORIZE,
    OAUTH2_TOKEN,
    SCOPES,
)


class EnuaOAuth2Implementation(
    config_entry_oauth2_flow.LocalOAuth2ImplementationWithPkce
):
    """Enua is registered as a public client in Azure AD B2C: PKCE, no secret."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialise the implementation."""
        super().__init__(
            hass,
            DOMAIN,
            CLIENT_ID,
            OAUTH2_AUTHORIZE,
            OAUTH2_TOKEN,
            client_secret="",
        )

    @property
    def name(self) -> str:
        """Name shown in the Home Assistant UI."""
        return "Enua"

    @property
    def extra_authorize_data(self) -> dict[str, Any]:
        """Add the requested scopes to the PKCE challenge parameters."""
        return {
            **super().extra_authorize_data,
            "scope": " ".join(SCOPES),
        }

    async def _token_request(self, data: dict) -> dict:
        """Ask B2C for the same scopes when refreshing.

        Azure AD B2C issues the access token for our own client id (instead of
        the Enua API resource) when the resource scope is missing from the
        request, which makes the API reject it with 401.
        """
        if data.get("grant_type") == "refresh_token":
            data.setdefault("scope", " ".join(SCOPES))
        return cast(dict, await super()._token_request(data))


@callback
def async_get_implementation(hass: HomeAssistant) -> EnuaOAuth2Implementation:
    """Return the shared implementation, registering it on first use.

    The PKCE code verifier lives on the implementation instance, so the same
    object must serve both the authorize step and the token exchange.
    """
    domain_data = hass.data.setdefault(DOMAIN, {})
    implementation = domain_data.get(DATA_IMPLEMENTATION)
    if implementation is None:
        implementation = EnuaOAuth2Implementation(hass)
        domain_data[DATA_IMPLEMENTATION] = implementation
        config_entry_oauth2_flow.async_register_implementation(
            hass, DOMAIN, implementation
        )
    return implementation
