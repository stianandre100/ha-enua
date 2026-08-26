"""Base entity for Enua Charge."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import EnuaDataUpdateCoordinator


class EnuaEntity(CoordinatorEntity[EnuaDataUpdateCoordinator]):
    """Common behaviour for every Enua entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: EnuaDataUpdateCoordinator, charger_id: str) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)
        self._charger_id = charger_id

    @property
    def charger(self) -> dict[str, Any]:
        """Return the latest data for this charger."""
        return self.coordinator.data.get(self._charger_id, {})

    @property
    def available(self) -> bool:
        """Entities go unavailable if the charger disappears from the account."""
        return super().available and self._charger_id in self.coordinator.data

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device this entity belongs to."""
        charger = self.charger
        name = charger.get("nickname") or charger.get("serialNumber") or "Enua Charge"
        return DeviceInfo(
            identifiers={(DOMAIN, self._charger_id)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=name,
            serial_number=charger.get("serialNumber"),
            sw_version=charger.get("firmwareVersion"),
        )
