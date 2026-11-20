"""Tests for Blueair config entry setup and unload."""

from __future__ import annotations

from aiohttp import ClientConnectionError
from blueair_api import LoginError
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.ha_blueair import BlueairRuntimeData
from custom_components.ha_blueair.const import DOMAIN

from .conftest import USERNAME, FakeBlueairCloud, entry_data


def _add_entry(hass: HomeAssistant, username: str = USERNAME) -> MockConfigEntry:
    """Add a Blueair config entry for an account.

    Args:
        hass: Home Assistant instance.
        username: Account username.

    Returns:
        MockConfigEntry: The added entry.
    """
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=username, title=username, data=entry_data(username), version=2
    )
    entry.add_to_hass(hass)
    return entry


@pytest.mark.asyncio
async def test_setup_stores_runtime_data_on_the_entry(
    hass: HomeAssistant, blueair_cloud: FakeBlueairCloud
) -> None:
    """Keep the account's coordinators and MQTT client on ConfigEntry.runtime_data."""
    entry = _add_entry(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)

    assert entry.state is ConfigEntryState.LOADED
    assert isinstance(entry.runtime_data, BlueairRuntimeData)
    assert entry.runtime_data.coordinators == []
    assert entry.runtime_data.mqtt_client is None
    assert DOMAIN not in hass.data or not isinstance(hass.data[DOMAIN], dict)


@pytest.mark.asyncio
async def test_two_accounts_load_and_unload_independently(
    hass: HomeAssistant, blueair_cloud: FakeBlueairCloud
) -> None:
    """Let a second Blueair account load, and unload, without touching the first."""
    first = _add_entry(hass, "first@example.com")
    second = _add_entry(hass, "second@example.com")
    # Loading the integration sets up every entry for the domain.
    assert await hass.config_entries.async_setup(first.entry_id)
    await hass.async_block_till_done()

    assert first.state is ConfigEntryState.LOADED
    assert second.state is ConfigEntryState.LOADED
    assert first.runtime_data is not second.runtime_data

    assert await hass.config_entries.async_unload(second.entry_id)
    await hass.async_block_till_done()

    assert second.state is ConfigEntryState.NOT_LOADED
    assert first.state is ConfigEntryState.LOADED
    assert isinstance(first.runtime_data, BlueairRuntimeData)


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [LoginError("expired"), ClientConnectionError("offline")])
async def test_setup_retries_when_blueair_fails(
    hass: HomeAssistant, blueair_cloud: FakeBlueairCloud, error: BaseException
) -> None:
    """Retry setup later when the login or the connection fails."""
    blueair_cloud.aws_error = error
    entry = _add_entry(hass)

    await hass.config_entries.async_setup(entry.entry_id)

    assert entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.asyncio
async def test_setup_skips_an_unreachable_legacy_api(
    hass: HomeAssistant, blueair_cloud: FakeBlueairCloud
) -> None:
    """Load AWS devices even when the legacy Blueair API is down."""
    blueair_cloud.legacy_error = ClientConnectionError("legacy offline")
    entry = _add_entry(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)

    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.devices == []
