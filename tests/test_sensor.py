"""Tests for the Blueair sensor platform's battery device class repair issue."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er, issue_registry as ir
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.ha_blueair.const import DOMAIN
from custom_components.ha_blueair.sensor import (
    _LIFE_LEVEL_UNIQUE_ID_SUFFIXES,
    BATTERY_DEVICE_CLASS_ISSUE_ID,
    BlueairFilterLifeSensor,
    BlueairWaterLevelSensor,
    BlueairWaterRefresherLifeSensor,
    BlueairWickLifeSensor,
)

from .conftest import USERNAME, FakeBlueairCloud, entry_data, make_climate_device, make_purifier


async def _setup(
    hass: HomeAssistant,
    blueair_cloud: FakeBlueairCloud,
    devices: list[Any],
    registered_device_class: str | None = None,
) -> MockConfigEntry:
    """Load an entry, optionally with a Filter Life sensor already registered.

    Args:
        hass: Home Assistant instance.
        blueair_cloud: Fake cloud the entry logs in to.
        devices: AWS devices on the account.
        registered_device_class: Device class an earlier version registered the
            purifier's Filter Life sensor with; None for a new install.

    Returns:
        MockConfigEntry: The loaded entry.
    """
    blueair_cloud.aws_devices = devices
    entry = MockConfigEntry(domain=DOMAIN, unique_id=USERNAME, data=entry_data(), version=2)
    entry.add_to_hass(hass)
    if registered_device_class is not None:
        er.async_get(hass).async_get_or_create(
            "sensor",
            DOMAIN,
            "purifier-1_Filter Life",
            config_entry=entry,
            original_device_class=registered_device_class,
        )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


@pytest.mark.asyncio
@pytest.mark.parametrize("registered_device_class", [None, "humidity"])
async def test_new_installs_get_no_battery_repair_issue(
    hass: HomeAssistant, blueair_cloud: FakeBlueairCloud, registered_device_class: str | None
) -> None:
    """Skip the notice when the life sensors were never registered as batteries."""
    await _setup(hass, blueair_cloud, [make_purifier()], registered_device_class)

    assert ir.async_get(hass).async_get_issue(DOMAIN, BATTERY_DEVICE_CLASS_ISSUE_ID) is None


@pytest.mark.asyncio
async def test_installs_with_battery_life_sensors_get_a_persistent_repair_issue(
    hass: HomeAssistant, blueair_cloud: FakeBlueairCloud
) -> None:
    """Raise a persistent notice for sensors an earlier version registered as batteries."""
    await _setup(hass, blueair_cloud, [make_purifier()], registered_device_class="battery")

    issue = ir.async_get(hass).async_get_issue(DOMAIN, BATTERY_DEVICE_CLASS_ISSUE_ID)
    assert issue is not None
    # The registry no longer says battery, so the notice must survive restarts.
    assert issue.is_persistent
    registry_entry = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, "purifier-1_Filter Life")
    assert registry_entry is not None
    assert er.async_get(hass).async_get(registry_entry).original_device_class is None


@pytest.mark.asyncio
async def test_battery_repair_issue_is_removed_without_life_sensors(
    hass: HomeAssistant, blueair_cloud: FakeBlueairCloud
) -> None:
    """Remove the notice once the account has no life or level sensor."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        BATTERY_DEVICE_CLASS_ISSUE_ID,
        is_fixable=False,
        is_persistent=True,
        severity=ir.IssueSeverity.WARNING,
        translation_key=BATTERY_DEVICE_CLASS_ISSUE_ID,
    )

    await _setup(hass, blueair_cloud, [make_climate_device()])

    assert ir.async_get(hass).async_get_issue(DOMAIN, BATTERY_DEVICE_CLASS_ISSUE_ID) is None


def test_life_sensor_suffixes_match_the_sensor_unique_ids() -> None:
    """Keep the repair check's unique ID suffixes in step with the sensor classes."""
    sensor_classes = [
        BlueairFilterLifeSensor,
        BlueairWickLifeSensor,
        BlueairWaterRefresherLifeSensor,
        BlueairWaterLevelSensor,
    ]

    assert _LIFE_LEVEL_UNIQUE_ID_SUFFIXES == tuple(
        f"_{sensor_class._unique_id_suffix}" for sensor_class in sensor_classes
    )
