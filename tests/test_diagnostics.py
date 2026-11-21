"""Tests for Blueair diagnostics."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
import pytest

from custom_components.ha_blueair.diagnostics import async_get_config_entry_diagnostics

from .conftest import PASSWORD, make_legacy_device, make_purifier


@pytest.mark.asyncio
async def test_diagnostics_cover_every_device_and_redact_credentials(
    hass: HomeAssistant, setup_blueair: Callable[..., Any]
) -> None:
    """Include every device with its entities, and never the account password."""
    entry = await setup_blueair(aws=[make_purifier()], legacy=[make_legacy_device()])

    data = await async_get_config_entry_diagnostics(hass, entry)

    assert data["entry"]["data"][CONF_PASSWORD] == "**REDACTED**"
    assert data["entry"]["data"][CONF_USERNAME] == "**REDACTED**"
    assert data["entry"]["title"] == "**REDACTED**"
    assert PASSWORD not in str(data)
    assert entry.data[CONF_USERNAME] not in str(data)
    devices = {key: value for key, value in data.items() if key != "entry"}
    assert set(devices) == {"purifier-1", "legacy-1"}
    for device_data in devices.values():
        assert device_data["device"]["entities"]


@pytest.mark.asyncio
async def test_diagnostics_redact_mac_addresses_and_serial_numbers(
    hass: HomeAssistant, setup_blueair: Callable[..., Any]
) -> None:
    """Remove the MAC address and serial number wherever they appear."""
    purifier = make_purifier(serial_number="SN-123456")
    purifier.raw_info = {
        "configuration": {"di": {"ds": "SN-123456"}},
        "mac": purifier.mac.replace(":", "").upper(),
        "states": [],
    }
    entry = await setup_blueair(aws=[purifier], legacy=[make_legacy_device()])

    data = await async_get_config_entry_diagnostics(hass, entry)

    text = str(data).lower()
    bare_mac = purifier.mac.replace(":", "").lower()
    for secret in ("sn-123456", purifier.mac.lower(), bare_mac, "aa:bb:cc:dd:ee:ff"):
        assert secret not in text
    aws = data["purifier-1"]
    assert aws["raw_info"]["configuration"]["di"]["ds"] == "**REDACTED**"
    assert aws["device"]["serial_number"] == "**REDACTED**"
    assert aws["device"]["connections"] == "**REDACTED**"
    assert "**REDACTED**" in aws["device_str"]
