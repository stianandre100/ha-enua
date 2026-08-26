"""Sensors for Enua Charge."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import LOCK_STATES, LOCK_STATUS_MAP, VEHICLE_STATE_MAP, VEHICLE_STATES
from .coordinator import EnuaConfigEntry, EnuaDataUpdateCoordinator
from .entity import EnuaEntity


@dataclass(frozen=True, kw_only=True)
class EnuaSensorEntityDescription(SensorEntityDescription):
    """Describes an Enua sensor."""

    value_fn: Callable[[dict[str, Any]], Any]


def _number(key: str) -> Callable[[dict[str, Any]], float | None]:
    """Return a getter that only passes numbers through."""

    def _get(charger: dict[str, Any]) -> float | None:
        value = charger.get(key)
        return float(value) if isinstance(value, (int, float)) else None

    return _get


def _phase_power(charger: dict[str, Any]) -> float | None:
    """Approximate the delivered power from per-phase current and voltage."""
    total = 0.0
    seen = False
    for current_key, voltage_key in (
        ("l1Current", "l1Voltage"),
        ("l2Current", "l2Voltage"),
        ("l3Current", "l3Voltage"),
    ):
        current = charger.get(current_key)
        voltage = charger.get(voltage_key)
        if isinstance(current, (int, float)) and isinstance(voltage, (int, float)):
            total += float(current) * float(voltage)
            seen = True
    return round(total, 1) if seen else None


def _session_energy(charger: dict[str, Any]) -> float | None:
    """Session energy, converted from watt-hours to kilowatt-hours."""
    value = charger.get("energy")
    if not isinstance(value, (int, float)):
        return None
    return round(float(value) / 1000, 3)


def _vehicle_state(charger: dict[str, Any]) -> str | None:
    """Map the control pilot letter to a readable state."""
    return VEHICLE_STATE_MAP.get(charger.get("vehicleState") or "")


def _lock_state(key: str) -> Callable[[dict[str, Any]], str | None]:
    """Return a getter that maps a lock status enum."""

    def _get(charger: dict[str, Any]) -> str | None:
        return LOCK_STATUS_MAP.get(charger.get(key) or "")

    return _get


SENSORS: tuple[EnuaSensorEntityDescription, ...] = (
    EnuaSensorEntityDescription(
        key="vehicle_state",
        translation_key="vehicle_state",
        device_class=SensorDeviceClass.ENUM,
        options=VEHICLE_STATES,
        value_fn=_vehicle_state,
    ),
    EnuaSensorEntityDescription(
        key="power",
        translation_key="power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        value_fn=_phase_power,
    ),
    EnuaSensorEntityDescription(
        key="session_energy",
        translation_key="session_energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        value_fn=_session_energy,
    ),
    EnuaSensorEntityDescription(
        key="l1_current",
        translation_key="l1_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=1,
        value_fn=_number("l1Current"),
    ),
    EnuaSensorEntityDescription(
        key="l2_current",
        translation_key="l2_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=1,
        value_fn=_number("l2Current"),
    ),
    EnuaSensorEntityDescription(
        key="l3_current",
        translation_key="l3_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=1,
        value_fn=_number("l3Current"),
    ),
    EnuaSensorEntityDescription(
        key="l1_voltage",
        translation_key="l1_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
        value_fn=_number("l1Voltage"),
    ),
    EnuaSensorEntityDescription(
        key="l2_voltage",
        translation_key="l2_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
        value_fn=_number("l2Voltage"),
    ),
    EnuaSensorEntityDescription(
        key="l3_voltage",
        translation_key="l3_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
        value_fn=_number("l3Voltage"),
    ),
    EnuaSensorEntityDescription(
        key="charger_max_current",
        translation_key="charger_max_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_number("chargerMaxCurrent"),
    ),
    EnuaSensorEntityDescription(
        key="vehicle_max_current",
        translation_key="vehicle_max_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_number("vehicleMaxCurrent"),
    ),
    EnuaSensorEntityDescription(
        key="cable_lock",
        translation_key="cable_lock",
        device_class=SensorDeviceClass.ENUM,
        options=LOCK_STATES,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_lock_state("cableLockStatus"),
    ),
    EnuaSensorEntityDescription(
        key="wall_mount_lock",
        translation_key="wall_mount_lock",
        device_class=SensorDeviceClass.ENUM,
        options=LOCK_STATES,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_lock_state("wallMountLockStatus"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnuaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Enua sensors."""
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _add_new_chargers() -> None:
        new = set(coordinator.data) - known
        if not new:
            return
        known.update(new)
        async_add_entities(
            EnuaSensor(coordinator, charger_id, description)
            for charger_id in new
            for description in SENSORS
        )

    _add_new_chargers()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_chargers))


class EnuaSensor(EnuaEntity, SensorEntity):
    """A sensor reading one field off a charger."""

    entity_description: EnuaSensorEntityDescription

    def __init__(
        self,
        coordinator: EnuaDataUpdateCoordinator,
        charger_id: str,
        description: EnuaSensorEntityDescription,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, charger_id)
        self.entity_description = description
        self._attr_unique_id = f"{charger_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        """Return the current value."""
        return self.entity_description.value_fn(self.charger)
