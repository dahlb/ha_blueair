"""Tests for the Blueair device coordinators."""

from __future__ import annotations

from collections.abc import Callable
import logging
from typing import Any
from unittest.mock import patch

from aiohttp import ClientConnectionError
from blueair_api import LoginError
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    HomeAssistantError,
    ServiceValidationError,
)
from homeassistant.helpers.update_coordinator import UpdateFailed
import pytest

from custom_components.ha_blueair.const import DOMAIN

from .conftest import make_climate_device, make_humidifier, make_legacy_device, make_purifier

# AWS-only readings the legacy REST API never reports.
LEGACY_UNSUPPORTED = [
    "night_mode",
    "germ_shield",
    "wick_life",
    "water_refresher_life",
    "wick_dry_mode",
    "water_shortage",
    "water_level",
    "auto_regulated_humidity",
    "humidifier_mode",
    "combo_mode",
    "mood_brightness",
    "night_light_brightness",
    "main_mode",
    "heat_temp",
    "heat_sub_mode",
    "heat_fan_speed",
    "cool_sub_mode",
    "cool_fan_speed",
    "ap_sub_mode",
    "fan_speed_0",
    "temperature_unit",
    "rssi",
    "timer_state",
    "timer_duration",
    "hour_format",
]
# Commands the legacy REST API cannot send.
LEGACY_UNSUPPORTED_COMMANDS = [
    ("set_running", True),
    ("set_night_mode", True),
    ("set_germ_shield", True),
    ("set_mood_brightness", 10),
    ("turn_off_mood_brightness", None),
    ("set_night_light_brightness", 10),
    ("turn_off_night_light_brightness", None),
    ("set_wick_dry_mode", True),
    ("set_auto_regulated_humidity", 40),
    ("set_main_mode", 1),
    ("set_heat_temp", 20),
    ("set_heat_sub_mode", 1),
    ("set_heat_fan_speed", 11),
    ("set_cool_sub_mode", 1),
    ("set_cool_fan_speed", 11),
    ("set_ap_sub_mode", 1),
    ("set_fan_speed_0", 11),
]


@pytest.mark.asyncio
async def test_failed_polls_make_entities_unavailable_and_log_once(
    hass: HomeAssistant, setup_blueair: Callable[..., Any], caplog: pytest.LogCaptureFixture
) -> None:
    """Log an outage once and the recovery once, not a stack trace per poll."""
    device = make_purifier()
    entry = await setup_blueair(aws=[device])
    coordinator = entry.runtime_data.aws_devices[0]
    device.refresh_error = ClientConnectionError("offline")
    caplog.clear()

    for _ in range(3):
        await coordinator.async_refresh()

    assert isinstance(coordinator.last_exception, UpdateFailed)
    assert coordinator.last_exception.translation_key == "update_failed"
    assert hass.states.get("fan.bedroom_fan").state == "unavailable"
    errors = [record for record in caplog.records if record.levelno >= logging.ERROR]
    assert len(errors) == 1
    assert errors[0].exc_info is None

    device.refresh_error = None
    await coordinator.async_refresh()

    assert hass.states.get("fan.bedroom_fan").state == "on"
    assert len([r for r in caplog.records if "recovered" in r.message]) == 1


@pytest.mark.asyncio
async def test_rejected_login_while_polling_starts_reauthentication(
    hass: HomeAssistant, setup_blueair: Callable[..., Any]
) -> None:
    """Start reauthentication when a poll's login is rejected."""
    device = make_purifier()
    entry = await setup_blueair(aws=[device])
    coordinator = entry.runtime_data.aws_devices[0]
    device.refresh_error = LoginError("password changed")

    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert isinstance(coordinator.last_exception, ConfigEntryAuthFailed)
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert [flow["context"]["source"] for flow in flows] == ["reauth"]


@pytest.mark.asyncio
async def test_rejected_login_on_a_command_starts_reauthentication(
    hass: HomeAssistant, setup_blueair: Callable[..., Any]
) -> None:
    """Raise a translated error and start reauthentication when a command's login fails."""
    device = make_purifier()
    entry = await setup_blueair(aws=[device])
    device.api.error = LoginError("password changed")

    with pytest.raises(HomeAssistantError) as raised:
        await entry.runtime_data.aws_devices[0].set_child_lock(True)
    await hass.async_block_till_done()

    assert raised.value.translation_key == "auth_failed"
    assert len(hass.config_entries.flow.async_progress_by_handler(DOMAIN)) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("usage", "expired", "state"),
    [
        (25, False, "off"),
        (99, False, "off"),
        (100, True, "on"),
        # Some filters report usage past 100%.
        (110, True, "on"),
        (None, None, "unknown"),
    ],
)
async def test_aws_filter_expires_when_its_life_runs_out(
    hass: HomeAssistant,
    setup_blueair: Callable[..., Any],
    usage: int | None,
    expired: bool | None,
    state: str,
) -> None:
    """Turn Filter Expiration on for AWS purifiers once Filter Life reaches 0%."""
    entry = await setup_blueair(aws=[make_purifier(filter_usage_percentage=usage)])

    assert entry.runtime_data.aws_devices[0].filter_expired is expired
    assert hass.states.get("binary_sensor.bedroom_filter_expiration").state == state


@pytest.mark.asyncio
async def test_aws_devices_without_a_filter_have_no_filter_expiration(
    hass: HomeAssistant, setup_blueair: Callable[..., Any]
) -> None:
    """Leave Filter Expiration off devices that report no filter usage."""
    entry = await setup_blueair(aws=[make_purifier(filter_usage_percentage=NotImplemented)])

    assert entry.runtime_data.aws_devices[0].filter_expired is NotImplemented
    assert hass.states.get("binary_sensor.bedroom_filter_expiration") is None


@pytest.mark.asyncio
async def test_a_command_updates_every_entity_of_the_device(
    hass: HomeAssistant, setup_blueair: Callable[..., Any]
) -> None:
    """Show a command's result on the device's other entities before the next refresh."""
    device = make_humidifier()
    await setup_blueair(aws=[device])
    assert hass.states.get("fan.nursery_fan").state == "on"
    polls = device.refresh_count

    await hass.services.async_call(
        "humidifier",
        "turn_off",
        {"entity_id": "humidifier.nursery_humidifier"},
        blocking=True,
    )

    # The debounced refresh hasn't run yet; the fan shows the command's result.
    assert device.refresh_count == polls
    assert hass.states.get("fan.nursery_fan").state == "off"


@pytest.mark.asyncio
async def test_a_failed_command_does_not_update_the_entities(
    hass: HomeAssistant, setup_blueair: Callable[..., Any]
) -> None:
    """Leave the other entities alone when the command could not be sent."""
    device = make_humidifier()
    entry = await setup_blueair(aws=[device])
    coordinator = entry.runtime_data.aws_devices[0]
    device.api.error = ClientConnectionError("offline")

    with (
        patch.object(coordinator, "async_update_listeners") as update_listeners,
        pytest.raises(HomeAssistantError),
    ):
        await coordinator.set_child_lock(True)

    update_listeners.assert_not_called()


@pytest.mark.asyncio
async def test_legacy_coordinator_reports_aws_only_features_as_unsupported(
    hass: HomeAssistant, setup_blueair: Callable[..., Any]
) -> None:
    """Report AWS-only readings as NotImplemented and refuse AWS-only commands."""
    entry = await setup_blueair(legacy=[make_legacy_device()])
    coordinator = entry.runtime_data.devices[0]

    for name in LEGACY_UNSUPPORTED:
        assert getattr(coordinator, name) is NotImplemented, name
    for name, value in LEGACY_UNSUPPORTED_COMMANDS:
        command = getattr(coordinator, name)
        with pytest.raises(NotImplementedError):
            await (command() if value is None else command(value))
    assert coordinator.fan_speed == 2
    assert coordinator.brightness == round(2 * 255 / 4)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("fan_speed", "wifi_status", "online"),
    [
        *[(speed, "0", True) for speed in ("0", "1", "2", "3")],
        *[(speed, "1", False) for speed in ("4", "9")],
    ],
)
async def test_sense_plus_online_follows_its_fan_state(
    hass: HomeAssistant,
    setup_blueair: Callable[..., Any],
    fan_speed: str,
    wifi_status: str,
    online: bool,
) -> None:
    """Report Sense+ online for any valid fan speed, even while wifi_working is False."""
    device = make_legacy_device(compatibility="sense+")
    entry = await setup_blueair(legacy=[device])
    coordinator = entry.runtime_data.devices[0]

    device.api.attributes.update(fan_speed=fan_speed, wifi_status=wifi_status)
    await coordinator.async_refresh()

    assert coordinator.online is online


@pytest.mark.asyncio
@pytest.mark.parametrize("wifi_status", ["0", "1"])
async def test_other_legacy_models_report_wifi_working_as_online(
    hass: HomeAssistant, setup_blueair: Callable[..., Any], wifi_status: str
) -> None:
    """Keep wifi_working as online for every legacy model but Sense+."""
    device = make_legacy_device()
    device.api.attributes["wifi_status"] = wifi_status
    entry = await setup_blueair(legacy=[device])

    assert entry.runtime_data.devices[0].online is (wifi_status == "1")


@pytest.mark.asyncio
async def test_legacy_brightness_passes_through_unknown_values(
    hass: HomeAssistant, setup_blueair: Callable[..., Any]
) -> None:
    """Hand back NotImplemented brightness unchanged instead of scaling it."""
    device = make_legacy_device()
    del device.api.attributes["brightness"]
    entry = await setup_blueair(legacy=[device])

    assert entry.runtime_data.devices[0].brightness is NotImplemented


@pytest.mark.asyncio
async def test_aws_coordinator_tolerates_malformed_values(
    hass: HomeAssistant, setup_blueair: Callable[..., Any]
) -> None:
    """Hand back raw values Carrier sends in an unexpected shape instead of crashing."""
    device = make_climate_device(
        standby=None,
        temperature="warm",
        heat_temp="hot",
        temperature_unit="?",
        total_voc=99,
        voc=1,
        rssi=-50,
        timer_state=1,
        hour_format=False,
    )
    entry = await setup_blueair(aws=[device])
    coordinator = entry.runtime_data.aws_devices[0]

    assert coordinator.is_on is None
    assert coordinator.temperature == "warm"
    assert coordinator.heat_temp == "hot"
    assert coordinator.temperature_unit == "?"
    assert coordinator.voc == 99
    assert coordinator.rssi == -50
    assert coordinator.timer_state == 1
    assert coordinator.hour_format is False
    assert coordinator.cool_sub_mode == 1


@pytest.mark.asyncio
async def test_aws_coordinator_timer_hour_format_and_heat_temp_writes(
    hass: HomeAssistant, setup_blueair: Callable[..., Any]
) -> None:
    """Write the timer and clock format, and reject heat targets that are not numbers."""
    device = make_climate_device()
    entry = await setup_blueair(aws=[device])
    coordinator = entry.runtime_data.aws_devices[0]

    await coordinator.set_timer_duration(1800)
    await coordinator.set_hour_format(False)
    assert device.timer_duration == 1800
    assert device.hour_format is False

    writes = len(device.api.writes)
    for value in (None, NotImplemented, "hot"):
        with pytest.raises(ServiceValidationError) as err:
            await coordinator.set_heat_temp(value)
        assert err.value.translation_key == "invalid_temperature"
    assert len(device.api.writes) == writes
