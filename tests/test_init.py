"""Test setting up Enua Charge and the entities it creates."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
import pytest

from custom_components.enua.const import API_BASE, DOMAIN

from .conftest import CHARGER_ID


async def _setup(hass: HomeAssistant, config_entry) -> None:
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


async def test_setup_creates_entities(
    hass: HomeAssistant, aioclient_mock, config_entry, charger
) -> None:
    """A charger becomes a device with the expected entity states."""
    aioclient_mock.get(f"{API_BASE}/chargers", json=[charger])
    await _setup(hass, config_entry)

    assert config_entry.state is ConfigEntryState.LOADED

    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device(identifiers={(DOMAIN, CHARGER_ID)})
    assert device is not None
    assert device.name == "Garasje"
    assert device.sw_version == "1.2.3"

    assert hass.states.get("sensor.garasje_vehicle_state").state == "charging"
    assert hass.states.get("sensor.garasje_session_energy").state == "4.321"
    assert hass.states.get("sensor.garasje_current_l1").state == "15.5"
    assert hass.states.get("sensor.garasje_cable_lock").state == "locked"
    assert hass.states.get("binary_sensor.garasje_online").state == "on"
    assert hass.states.get("binary_sensor.garasje_charging").state == "on"
    assert hass.states.get("binary_sensor.garasje_cable_connected").state == "on"
    assert hass.states.get("binary_sensor.garasje_problem").state == "off"
    assert hass.states.get("switch.garasje_charging").state == "on"
    assert hass.states.get("number.garasje_max_current").state == "16.0"

    # 15.5*230 + 15.4*231 + 15.6*229 = 3565 + 3557.4 + 3572.4 = 10694.8
    assert hass.states.get("sensor.garasje_power").state == "10694.8"


async def test_setup_not_ready_without_chargers(
    hass: HomeAssistant, aioclient_mock, config_entry
) -> None:
    """An account with no chargers should retry rather than load empty."""
    aioclient_mock.get(f"{API_BASE}/chargers", json=[])
    await _setup(hass, config_entry)
    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_bad_token_triggers_reauth(
    hass: HomeAssistant, aioclient_mock, config_entry
) -> None:
    """A 401 from the API starts a reauth flow instead of failing silently."""
    aioclient_mock.get(f"{API_BASE}/chargers", status=401, json={"title": "nope"})
    await _setup(hass, config_entry)

    assert config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert any(flow["context"]["source"] == "reauth" for flow in flows)


async def test_rate_limit_is_retried(
    hass: HomeAssistant, aioclient_mock, config_entry
) -> None:
    """A 429 is a transient failure, not a configuration error."""
    aioclient_mock.get(
        f"{API_BASE}/chargers",
        status=429,
        json={"title": "Too many requests", "errorCode": "RateLimit"},
    )
    await _setup(hass, config_entry)
    assert config_entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.parametrize(
    ("service", "endpoint"),
    [("turn_on", "start-charging"), ("turn_off", "stop-charging")],
)
async def test_switch_commands(
    hass: HomeAssistant, aioclient_mock, config_entry, charger, service, endpoint
) -> None:
    """The switch calls the documented command endpoints."""
    aioclient_mock.get(f"{API_BASE}/chargers", json=[charger])
    await _setup(hass, config_entry)

    aioclient_mock.post(
        f"{API_BASE}/chargers/{CHARGER_ID}/commands/{endpoint}", text=""
    )
    await hass.services.async_call(
        "switch",
        service,
        {"entity_id": "switch.garasje_charging"},
        blocking=True,
    )
    assert any(
        str(call[1]).endswith(f"commands/{endpoint}")
        for call in aioclient_mock.mock_calls
    )


async def test_set_max_current(
    hass: HomeAssistant, aioclient_mock, config_entry, charger
) -> None:
    """The number entity posts the ampere value the API expects."""
    aioclient_mock.get(f"{API_BASE}/chargers", json=[charger])
    await _setup(hass, config_entry)

    aioclient_mock.post(
        f"{API_BASE}/chargers/{CHARGER_ID}/commands/set-max-current", text=""
    )
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": "number.garasje_max_current", "value": 10},
        blocking=True,
    )
    post = next(
        call
        for call in aioclient_mock.mock_calls
        if str(call[1]).endswith("set-max-current")
    )
    assert post[2] == {"maxCurrent": 10}


async def test_unload(
    hass: HomeAssistant, aioclient_mock, config_entry, charger
) -> None:
    """The entry unloads cleanly."""
    aioclient_mock.get(f"{API_BASE}/chargers", json=[charger])
    await _setup(hass, config_entry)

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.NOT_LOADED
