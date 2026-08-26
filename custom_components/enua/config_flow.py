"""Config flow for Enua Charge."""

from __future__ import annotations

import base64
import binascii
from collections.abc import Mapping
import json
import logging
from typing import Any

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import config_entry_oauth2_flow
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .oauth import async_get_implementation

_LOGGER = logging.getLogger(__name__)


class EnuaOAuth2FlowHandler(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN
):
    """Handle the Enua OAuth2 config flow."""

    VERSION = 1
    DOMAIN = DOMAIN

    reauth_entry: ConfigEntry | None = None

    @property
    def logger(self) -> logging.Logger:
        """Return the logger."""
        return _LOGGER

    @property
    def extra_authorize_data(self) -> dict[str, Any]:
        """Scopes are supplied by the implementation."""
        return {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Register the bundled implementation, then run the normal flow."""
        async_get_implementation(self.hass)
        return await super().async_step_user(user_input)

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication."""
        self.reauth_entry = self._get_reauth_entry()
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm re-authentication."""
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm")
        return await self.async_step_user()

    async def async_oauth_create_entry(self, data: dict[str, Any]) -> ConfigFlowResult:
        """Create or update the entry once we have a token."""
        subject = _id_token_subject(data.get("token", {}))

        if self.reauth_entry is not None:
            return self.async_update_reload_and_abort(self.reauth_entry, data=data)

        if subject:
            await self.async_set_unique_id(subject)
            self._abort_if_unique_id_configured()

        return self.async_create_entry(title="Enua Charge", data=data)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return EnuaOptionsFlow()


class EnuaOptionsFlow(OptionsFlow):
    """Let the user tune the polling interval."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, int(DEFAULT_SCAN_INTERVAL.total_seconds())
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(
                    cv.positive_int,
                    vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)


def _id_token_subject(token: Mapping[str, Any]) -> str | None:
    """Read the 'sub' claim from the id_token, without verifying it.

    The token comes straight from the B2C token endpoint over TLS and is only
    used to give the config entry a stable unique id, so signature verification
    would add a dependency without adding security here.
    """
    id_token = token.get("id_token")
    if not isinstance(id_token, str):
        return None

    parts = id_token.split(".")
    if len(parts) != 3:
        return None

    payload = parts[1]
    payload += "=" * (-len(payload) % 4)
    try:
        claims = json.loads(base64.urlsafe_b64decode(payload))
    except (binascii.Error, ValueError, UnicodeDecodeError):
        return None

    subject = claims.get("sub") if isinstance(claims, dict) else None
    return str(subject) if subject else None
