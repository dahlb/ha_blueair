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
    assert data["entry"]["data"][CONF_USERNAME] == entry.data[CONF_USERNAME]
    assert PASSWORD not in str(data)
    devices = {key: value for key, value in data.items() if key != "entry"}
    assert len(devices) == 2
    for device_data in devices.values():
        assert device_data["device"]["entities"]
