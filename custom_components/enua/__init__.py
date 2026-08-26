"""The Enua Charge integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EnuaApiClient
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
from .coordinator import EnuaConfigEntry, EnuaDataUpdateCoordinator
from .oauth import async_get_implementation

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: EnuaConfigEntry) -> bool:
    """Set up Enua Charge from a config entry."""
    # Make sure our implementation is registered before the helper looks it up.
    async_get_implementation(hass)

    implementation = (
        await config_entry_oauth2_flow.async_get_config_entry_implementation(
            hass, entry
        )
    )
    oauth_session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)
    client = EnuaApiClient(async_get_clientsession(hass), oauth_session)

    seconds = entry.options.get(
        CONF_SCAN_INTERVAL, int(DEFAULT_SCAN_INTERVAL.total_seconds())
    )
    coordinator = EnuaDataUpdateCoordinator(
        hass, entry, client, timedelta(seconds=seconds)
    )

    await coordinator.async_config_entry_first_refresh()

    if not coordinator.data:
        raise ConfigEntryNotReady(
            "The Enua account signed in has no chargers. Sign in to the Enua app "
            "once with this account and make sure the chargers are owned by or "
            "shared with it."
        )

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EnuaConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: EnuaConfigEntry) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)
