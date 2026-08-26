"""Data update coordinator for Enua Charge."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EnuaApiClient, EnuaApiError, EnuaRateLimitError
from .const import COMMAND_REFRESH_DELAY, DOMAIN

_LOGGER = logging.getLogger(__name__)

type EnuaConfigEntry = ConfigEntry[EnuaDataUpdateCoordinator]


class EnuaDataUpdateCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Poll the Enua API and hand out charger state keyed by charger id."""

    config_entry: EnuaConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: EnuaConfigEntry,
        client: EnuaApiClient,
        update_interval: timedelta,
    ) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
            config_entry=config_entry,
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch every charger the account can see."""
        try:
            chargers = await self.client.async_get_chargers()
        except ConfigEntryAuthFailed:
            raise
        except EnuaRateLimitError as err:
            raise UpdateFailed(str(err)) from err
        except EnuaApiError as err:
            raise UpdateFailed(str(err)) from err

        return {
            charger["id"]: charger
            for charger in chargers
            if isinstance(charger, dict) and charger.get("id")
        }

    async def async_request_refresh_soon(self) -> None:
        """Refresh after the charger has had time to report a new state."""
        await asyncio.sleep(COMMAND_REFRESH_DELAY)
        await self.async_request_refresh()
