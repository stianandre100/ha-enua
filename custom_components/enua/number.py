"""Max current number entity for Enua Charge."""

from __future__ import annotations

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberMode,
)
from homeassistant.const import UnitOfElectricCurrent
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import MAX_CURRENT, MIN_CURRENT
from .coordinator import EnuaConfigEntry, EnuaDataUpdateCoordinator
from .entity import EnuaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnuaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Enua number entities."""
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _add_new_chargers() -> None:
        new = set(coordinator.data) - known
        if not new:
            return
        known.update(new)
        async_add_entities(
            EnuaMaxCurrentNumber(coordinator, charger_id) for charger_id in new
        )

    _add_new_chargers()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_chargers))


class EnuaMaxCurrentNumber(EnuaEntity, NumberEntity):
    """Set the maximum current the charger will deliver."""

    _attr_translation_key = "max_current"
    _attr_device_class = NumberDeviceClass.CURRENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_native_min_value = float(MIN_CURRENT)
    _attr_native_max_value = float(MAX_CURRENT)
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: EnuaDataUpdateCoordinator, charger_id: str) -> None:
        """Initialise the number entity."""
        super().__init__(coordinator, charger_id)
        self._attr_unique_id = f"{charger_id}_max_current"

    @property
    def native_value(self) -> float | None:
        """Return the charger's current maximum."""
        value = self.charger.get("chargerMaxCurrent")
        return float(value) if isinstance(value, (int, float)) else None

    async def async_set_native_value(self, value: float) -> None:
        """Send a new maximum current to the charger."""
        await self.coordinator.client.async_set_max_current(
            self._charger_id, int(value)
        )
        await self.coordinator.async_request_refresh_soon()
