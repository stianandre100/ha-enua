"""Binary sensors for Enua Charge."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import EnuaConfigEntry, EnuaDataUpdateCoordinator
from .entity import EnuaEntity


@dataclass(frozen=True, kw_only=True)
class EnuaBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes an Enua binary sensor."""

    value_fn: Callable[[dict[str, Any]], bool | None]


def _bool(key: str) -> Callable[[dict[str, Any]], bool | None]:
    """Return a getter for a nullable boolean field."""

    def _get(charger: dict[str, Any]) -> bool | None:
        value = charger.get(key)
        return bool(value) if isinstance(value, bool) else None

    return _get


def _cable_connected(charger: dict[str, Any]) -> bool | None:
    """Report a plugged-in vehicle: control pilot state B or C."""
    state = charger.get("vehicleState")
    if state is None:
        return None
    return state in ("B", "C")


def _charging(charger: dict[str, Any]) -> bool | None:
    """Control pilot state C means the vehicle is drawing current."""
    state = charger.get("vehicleState")
    if state is None:
        return None
    return state == "C"


def _error(charger: dict[str, Any]) -> bool | None:
    """Control pilot state E, or either lock reporting an error."""
    values = [
        charger.get("vehicleState"),
        charger.get("cableLockStatus"),
        charger.get("wallMountLockStatus"),
    ]
    if all(value is None for value in values):
        return None
    return charger.get("vehicleState") == "E" or "Error" in values


BINARY_SENSORS: tuple[EnuaBinarySensorEntityDescription, ...] = (
    EnuaBinarySensorEntityDescription(
        key="online",
        translation_key="online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_bool("isOnline"),
    ),
    EnuaBinarySensorEntityDescription(
        key="cable_connected",
        translation_key="cable_connected",
        device_class=BinarySensorDeviceClass.PLUG,
        value_fn=_cable_connected,
    ),
    EnuaBinarySensorEntityDescription(
        key="charging",
        translation_key="charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        value_fn=_charging,
    ),
    EnuaBinarySensorEntityDescription(
        key="active_transaction",
        translation_key="active_transaction",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_bool("hasActiveTransaction"),
    ),
    EnuaBinarySensorEntityDescription(
        key="problem",
        translation_key="problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_error,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnuaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Enua binary sensors."""
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _add_new_chargers() -> None:
        new = set(coordinator.data) - known
        if not new:
            return
        known.update(new)
        async_add_entities(
            EnuaBinarySensor(coordinator, charger_id, description)
            for charger_id in new
            for description in BINARY_SENSORS
        )

    _add_new_chargers()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_chargers))


class EnuaBinarySensor(EnuaEntity, BinarySensorEntity):
    """A binary sensor derived from charger state."""

    entity_description: EnuaBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: EnuaDataUpdateCoordinator,
        charger_id: str,
        description: EnuaBinarySensorEntityDescription,
    ) -> None:
        """Initialise the binary sensor."""
        super().__init__(coordinator, charger_id)
        self.entity_description = description
        self._attr_unique_id = f"{charger_id}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        """Return the current state."""
        return self.entity_description.value_fn(self.charger)
