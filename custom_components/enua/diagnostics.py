"""Diagnostics support for Enua Charge."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .coordinator import EnuaConfigEntry

TO_REDACT = {
    "access_token",
    "refresh_token",
    "id_token",
    "serialNumber",
    "id",
    "nickname",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: EnuaConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    return {
        "entry": {
            "options": dict(entry.options),
            "data": async_redact_data(dict(entry.data), TO_REDACT),
        },
        "chargers": [
            async_redact_data(charger, TO_REDACT)
            for charger in (coordinator.data or {}).values()
        ],
    }
