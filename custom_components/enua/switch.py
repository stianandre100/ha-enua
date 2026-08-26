"""Charging switch for Enua Charge."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import EnuaConfigEntry, EnuaDataUpdateCoordinator
from .entity import EnuaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnuaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Enua charging switches."""
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _add_new_chargers() -> None:
        new = set(coordinator.data) - known
        if not new:
            return
        known.update(new)
        async_add_entities(
            EnuaChargingSwitch(coordinator, charger_id) for charger_id in new
        )

    _add_new_chargers()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_chargers))


class EnuaChargingSwitch(EnuaEntity, SwitchEntity):
    """Start and stop the charging session."""

    _attr_translation_key = "charging"
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coordinator: EnuaDataUpdateCoordinator, charger_id: str) -> None:
        """Initialise the switch."""
        super().__init__(coordinator, charger_id)
        self._attr_unique_id = f"{charger_id}_charging"

    @property
    def is_on(self) -> bool | None:
        """Return whether a charging transaction is open."""
        value = self.charger.get("hasActiveTransaction")
        return bool(value) if isinstance(value, bool) else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start charging."""
        await self.coordinator.client.async_start_charging(self._charger_id)
        await self.coordinator.async_request_refresh_soon()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop charging."""
        await self.coordinator.client.async_stop_charging(self._charger_id)
        await self.coordinator.async_request_refresh_soon()
