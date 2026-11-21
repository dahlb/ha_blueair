"""Tests for devices added to or removed from the Blueair account after setup."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import Any

from aiohttp import ClientConnectionError
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant.common import async_fire_time_changed

from custom_components.ha_blueair import async_remove_config_entry_device
from custom_components.ha_blueair.const import DEVICE_LIST_INTERVAL, DOMAIN

from .conftest import FakeBlueairCloud, make_humidifier, make_legacy_device, make_purifier


async def _check_device_list(hass: HomeAssistant) -> None:
    """Advance time past the device list interval and let any reload finish.

    Args:
        hass: Home Assistant instance.
    """
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=DEVICE_LIST_INTERVAL + 1))
    await hass.async_block_till_done(wait_background_tasks=True)


def _device(hass: HomeAssistant, uuid: str) -> dr.DeviceEntry | None:
    """Return the registry device for a Blueair device ID.

    Args:
        hass: Home Assistant instance.
        uuid: Blueair device ID.

    Returns:
        dr.DeviceEntry | None: The device, if registered.
    """
    devices = dr.async_get(hass).async_get_devices(identifiers={(DOMAIN, uuid)})
    return devices[0] if devices else None


@pytest.mark.asyncio
async def test_devices_added_to_the_account_get_entities(
    hass: HomeAssistant, setup_blueair: Callable[..., Any], blueair_cloud: FakeBlueairCloud
) -> None:
    """Reload the entry when a device appears, so its entities are created."""
    entry = await setup_blueair(aws=[make_purifier()])
    assert hass.states.get("humidifier.nursery_humidifier") is None

    blueair_cloud.aws_devices.append(make_humidifier(name="Nursery"))
    await _check_device_list(hass)

    assert entry.state is ConfigEntryState.LOADED
    assert _device(hass, "humidifier-1") is not None
    assert hass.states.get("humidifier.nursery_humidifier") is not None
    assert hass.states.get("fan.bedroom_fan") is not None


@pytest.mark.asyncio
async def test_devices_removed_from_the_account_are_removed(
    hass: HomeAssistant, setup_blueair: Callable[..., Any], blueair_cloud: FakeBlueairCloud
) -> None:
    """Reload the entry when a device goes, removing its device and entities."""
    await setup_blueair(aws=[make_purifier(), make_humidifier()], legacy=[make_legacy_device()])
    assert _device(hass, "humidifier-1") is not None

    blueair_cloud.aws_devices = [make_purifier()]
    await _check_device_list(hass)

    assert _device(hass, "humidifier-1") is None
    assert not [
        entity
        for entity in er.async_get(hass).entities.values()
        if entity.unique_id.startswith("humidifier-1_")
    ]
    assert _device(hass, "purifier-1") is not None
    assert _device(hass, "legacy-1") is not None


@pytest.mark.asyncio
async def test_an_unchanged_device_list_does_not_reload(
    hass: HomeAssistant, setup_blueair: Callable[..., Any], blueair_cloud: FakeBlueairCloud
) -> None:
    """Leave the entry alone while the account's devices stay the same."""
    await setup_blueair(aws=[make_purifier()], legacy=[make_legacy_device()])
    logins = len(blueair_cloud.aws_calls)

    await _check_device_list(hass)

    assert len(blueair_cloud.aws_calls) == logins


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [ClientConnectionError("down"), TimeoutError()])
async def test_device_list_errors_are_ignored(
    hass: HomeAssistant,
    setup_blueair: Callable[..., Any],
    blueair_cloud: FakeBlueairCloud,
    error: BaseException,
) -> None:
    """Keep every device when the device list can't be fetched."""
    entry = await setup_blueair(aws=[make_purifier()])
    logins = len(blueair_cloud.aws_calls)
    blueair_cloud.list_error = error
    blueair_cloud.aws_devices = []

    await _check_device_list(hass)

    assert len(blueair_cloud.aws_calls) == logins
    assert entry.state is ConfigEntryState.LOADED
    assert _device(hass, "purifier-1") is not None


@pytest.mark.asyncio
async def test_an_empty_device_list_keeps_every_device(
    hass: HomeAssistant, setup_blueair: Callable[..., Any], blueair_cloud: FakeBlueairCloud
) -> None:
    """Treat an account that suddenly reports no devices as a Blueair glitch."""
    await setup_blueair(aws=[make_purifier()])
    logins = len(blueair_cloud.aws_calls)
    blueair_cloud.aws_devices = []

    await _check_device_list(hass)

    assert len(blueair_cloud.aws_calls) == logins
    assert _device(hass, "purifier-1") is not None


@pytest.mark.asyncio
async def test_legacy_devices_stay_while_the_legacy_api_is_unreachable(
    hass: HomeAssistant, setup_blueair: Callable[..., Any], blueair_cloud: FakeBlueairCloud
) -> None:
    """Keep legacy devices when setup couldn't list them."""
    entry = await setup_blueair(aws=[make_purifier()], legacy=[make_legacy_device()])
    assert _device(hass, "legacy-1") is not None

    blueair_cloud.legacy_error = ClientConnectionError("legacy down")
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert _device(hass, "legacy-1") is not None


@pytest.mark.asyncio
async def test_only_devices_gone_from_the_account_can_be_deleted(
    hass: HomeAssistant, setup_blueair: Callable[..., Any]
) -> None:
    """Allow deleting a device only once Blueair no longer reports it."""
    entry = await setup_blueair(aws=[make_purifier()])
    device_registry = dr.async_get(hass)
    current = _device(hass, "purifier-1")
    gone = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, "gone-1")}
    )

    assert current is not None
    assert not await async_remove_config_entry_device(hass, entry, current)
    assert await async_remove_config_entry_device(hass, entry, gone)


@pytest.mark.asyncio
async def test_unreachable_devices_are_kept(
    hass: HomeAssistant, setup_blueair: Callable[..., Any], blueair_cloud: FakeBlueairCloud
) -> None:
    """Keep a device that was unreachable at setup: it is still on the account."""
    entry = await setup_blueair(aws=[make_purifier(), make_humidifier()])
    assert await hass.config_entries.async_unload(entry.entry_id)
    blueair_cloud.aws_devices[1].refresh_error = ClientConnectionError("device offline")

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    unreachable = _device(hass, "humidifier-1")

    assert unreachable is not None
    assert not await async_remove_config_entry_device(hass, entry, unreachable)
    # The device list check doesn't count it as a newly added device.
    await _check_device_list(hass)
    assert entry.runtime_data.unreachable[0].id == "humidifier-1"
