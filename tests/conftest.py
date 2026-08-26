"""Fixtures for the Enua Charge tests."""

from __future__ import annotations

from collections.abc import Generator
import time
from unittest.mock import patch

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.enua.const import DOMAIN

CHARGER_ID = "11111111-2222-3333-4444-555555555555"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> Generator[None]:
    """Enable loading of the custom integration in every test."""
    yield


@pytest.fixture
def charger() -> dict:
    """Return a charger payload shaped like the Enua API returns it."""
    return {
        "id": CHARGER_ID,
        "serialNumber": "ENUA-0001",
        "nickname": "Garasje",
        "cableLockStatus": "Locked",
        "wallMountLockStatus": "Unlocked",
        "firmwareVersion": "1.2.3",
        "vehicleState": "C",
        "energy": 4321.0,
        "isOnline": True,
        "isOnlineLastChecked": "2026-08-26T10:00:00Z",
        "l1Current": 15.5,
        "l2Current": 15.4,
        "l3Current": 15.6,
        "l1Voltage": 230.0,
        "l2Voltage": 231.0,
        "l3Voltage": 229.0,
        "chargerMaxCurrent": 16.0,
        "vehicleMaxCurrent": 16,
        "hasActiveTransaction": True,
    }


@pytest.fixture
def config_entry(hass: HomeAssistant) -> ConfigEntry:
    """Return a config entry holding a valid token."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Enua Charge",
        unique_id="subject-123",
        data={
            "auth_implementation": DOMAIN,
            "token": {
                "access_token": "mock-access-token",
                "refresh_token": "mock-refresh-token",
                "expires_in": 3600,
                "expires_at": time.time() + 3600,
                "token_type": "Bearer",
            },
        },
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def mock_client_id() -> Generator[None]:
    """Pretend Enua's client id has been filled in."""
    with patch("custom_components.enua.const.CLIENT_ID", "test-client-id"):
        yield
