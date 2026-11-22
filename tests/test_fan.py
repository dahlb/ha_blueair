"""Tests for the Blueair fan platform."""

from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

from aiohttp import ClientConnectionError
from homeassistant.components.fan import (
    ATTR_PERCENTAGE,
    ATTR_PRESET_MODE,
    DOMAIN as FAN_DOMAIN,
    SERVICE_SET_PERCENTAGE,
    SERVICE_SET_PRESET_MODE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
import pytest

from custom_components.ha_blueair.fan import (
    _CLASSIC_PRESETS,
    _COMBO_PRESETS,
    _SIGNATURE_PRESETS,
    _percentage_speed,
    _preset_family,
    _speed_percentage,
)

from .conftest import entity_object, make_aws_device, make_combo, make_legacy_device, make_purifier

PURIFIER = "fan.bedroom_fan"


async def _call(hass: HomeAssistant, service: str, entity_id: str, **data: Any) -> None:
    """Call a fan service and wait for it.

    Args:
        hass: Home Assistant instance.
        service: Fan service name.
        entity_id: Target fan.
        data: Service data.
    """
    await hass.services.async_call(
        FAN_DOMAIN, service, {ATTR_ENTITY_ID: entity_id, **data}, blocking=True
    )


@pytest.fixture(autouse=True)
def no_night_mode_wait() -> Any:
    """Skip the 2 s wait the AWS fan makes after leaving night mode.

    Yields:
        AsyncMock: The patched sleep.
    """
    with patch("custom_components.ha_blueair.fan.sleep", AsyncMock()) as mock_sleep:
        yield mock_sleep


@pytest.mark.asyncio
async def test_aws_fan_reports_speed_and_presets(
    hass: HomeAssistant, setup_blueair: Callable[..., Any]
) -> None:
    """Show the speed as a percentage of the device's speed count, with auto/night presets."""
    await setup_blueair(aws=[make_purifier()])

    state = hass.states.get(PURIFIER)

    assert state is not None
    assert state.state == "on"
    # high_* purifiers use a 0-91 speed scale; 37 is the second gear.
    assert state.attributes[ATTR_PERCENTAGE] == 40
    assert state.attributes["preset_modes"] == ["auto", "night"]
    assert state.attributes[ATTR_PRESET_MODE] is None


@pytest.mark.asyncio
async def test_aws_fan_night_preset_can_be_turned_off_in_options(
    hass: HomeAssistant, setup_blueair: Callable[..., Any]
) -> None:
    """Leave Night out of the presets when the night_preset option is off."""
    await setup_blueair(aws=[make_purifier()], options={"night_preset": False})

    assert hass.states.get(PURIFIER).attributes["preset_modes"] == ["auto"]


@pytest.mark.asyncio
async def test_aws_fan_set_percentage_leaves_auto_and_night_first(
    hass: HomeAssistant, setup_blueair: Callable[..., Any], no_night_mode_wait: AsyncMock
) -> None:
    """Turn off auto and night mode before writing a manual speed."""
    device = make_purifier(fan_auto_mode=True, night_mode=True)
    await setup_blueair(aws=[device])

    await _call(hass, SERVICE_SET_PERCENTAGE, PURIFIER, percentage=100)

    assert device.fan_auto_mode is False
    assert device.night_mode is False
    assert device.fan_speed == 91
    no_night_mode_wait.assert_awaited_once_with(2)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("preset", "attribute"), [("auto", "fan_auto_mode"), ("night", "night_mode")]
)
async def test_aws_fan_set_preset(
    hass: HomeAssistant, setup_blueair: Callable[..., Any], preset: str, attribute: str
) -> None:
    """Switch the auto or night preset on."""
    device = make_purifier()
    await setup_blueair(aws=[device])

    await _call(hass, SERVICE_SET_PRESET_MODE, PURIFIER, preset_mode=preset)

    assert getattr(device, attribute) is True
    assert hass.states.get(PURIFIER).attributes[ATTR_PRESET_MODE] == preset


@pytest.mark.asyncio
async def test_aws_fan_turn_off_and_on(
    hass: HomeAssistant, setup_blueair: Callable[..., Any]
) -> None:
    """Put the device in standby, and bring it back at 50% if it forgot its speed."""
    device = make_purifier()
    await setup_blueair(aws=[device])

    await _call(hass, SERVICE_TURN_OFF, PURIFIER)
    assert device.standby is True

    device.fan_speed = 0
    await _call(hass, SERVICE_TURN_ON, PURIFIER)
    assert device.standby is False
    assert device.fan_speed == round(0.5 * 91)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({ATTR_PRESET_MODE: "auto"}, {"fan_auto_mode": True}),
        ({ATTR_PERCENTAGE: 100}, {"fan_speed": 91}),
        ({}, {"fan_speed": 37}),
    ],
)
async def test_aws_fan_turn_on_resumes_or_applies_the_request(
    hass: HomeAssistant,
    setup_blueair: Callable[..., Any],
    data: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    """Apply a preset or speed with turn_on, or resume the last speed when none is given."""
    device = make_purifier(standby=True)
    await setup_blueair(aws=[device])

    await _call(hass, SERVICE_TURN_ON, PURIFIER, **data)

    assert device.standby is False
    for attribute, value in expected.items():
        assert getattr(device, attribute) == value


@pytest.mark.asyncio
async def test_signature_fan_uses_ap_sub_mode_presets(
    hass: HomeAssistant, setup_blueair: Callable[..., Any]
) -> None:
    """Switch Signature presets through apsubmode, resetting the stored manual speed."""
    device = make_aws_device(
        uuid="sig-1", name="Study", hw="l_blue40", standby=False, fan_speed=37, ap_sub_mode=1
    )
    await setup_blueair(aws=[device])
    entity_id = "fan.study_fan"

    state = hass.states.get(entity_id)
    assert state.attributes["preset_modes"] == ["manual_fan", "auto", "night", "eco"]
    assert state.attributes[ATTR_PRESET_MODE] == "manual_fan"
    assert state.attributes[ATTR_PERCENTAGE] == 40

    await _call(hass, SERVICE_SET_PRESET_MODE, entity_id, preset_mode="eco")
    assert device.ap_sub_mode == 4
    assert device.fan_speed == 11
    assert hass.states.get(entity_id).attributes[ATTR_PERCENTAGE] is None

    await _call(hass, SERVICE_SET_PERCENTAGE, entity_id, percentage=100)
    assert device.ap_sub_mode == 1
    assert device.fan_speed == 91


@pytest.mark.asyncio
async def test_combo_fan_uses_combo_mode_presets(
    hass: HomeAssistant, setup_blueair: Callable[..., Any]
) -> None:
    """Switch 2-in-1 presets through the combo mode, entering manual before a speed write."""
    device = make_combo()
    await setup_blueair(aws=[device])
    entity_id = "fan.living_room_fan"

    state = hass.states.get(entity_id)
    assert state.attributes[ATTR_PRESET_MODE] == "auto"
    assert state.attributes[ATTR_PERCENTAGE] is None

    await _call(hass, SERVICE_SET_PRESET_MODE, entity_id, preset_mode="night")
    assert device.combo_mode == 3

    await _call(hass, SERVICE_SET_PERCENTAGE, entity_id, percentage=40)
    assert device.combo_mode == 1
    # 40% rounds up to 37, the second gear, which the fan reports back as 40%.
    assert device.fan_speed == 37


@pytest.mark.asyncio
async def test_aws_fan_command_failure_raises_a_translated_error(
    hass: HomeAssistant, setup_blueair: Callable[..., Any]
) -> None:
    """Raise HomeAssistantError, not a raw aiohttp error, when a command cannot be sent."""
    device = make_purifier()
    await setup_blueair(aws=[device])
    device.api.error = ClientConnectionError("offline")

    with pytest.raises(HomeAssistantError) as raised:
        await _call(hass, SERVICE_SET_PERCENTAGE, PURIFIER, percentage=50)

    assert raised.value.translation_key == "command_failed"
    assert raised.value.translation_placeholders["device"] == "Bedroom"


@pytest.mark.asyncio
async def test_legacy_fan_maps_percentages_to_three_speeds(
    hass: HomeAssistant, setup_blueair: Callable[..., Any]
) -> None:
    """Map percentages onto the legacy 1-3 speeds; only turning off writes speed 0."""
    device = make_legacy_device()
    await setup_blueair(legacy=[device])
    entity_id = "fan.hallway_fan"

    state = hass.states.get(entity_id)
    assert state.attributes[ATTR_PERCENTAGE] == 66
    # The legacy API cannot set night mode, so Night is not offered.
    assert state.attributes["preset_modes"] == ["auto"]

    for percentage, speed in [(100, "3"), (60, "2"), (30, "1"), (10, "1")]:
        await _call(hass, SERVICE_SET_PERCENTAGE, entity_id, percentage=percentage)
        assert device.api.writes[-1] == ("fan_speed", speed)

    await _call(hass, SERVICE_TURN_OFF, entity_id)
    assert device.api.writes[-1] == ("fan_speed", "0")

    await _call(hass, SERVICE_SET_PRESET_MODE, entity_id, preset_mode="auto")
    assert device.api.writes[-1] == ("fan_auto_mode", True)


@pytest.mark.asyncio
async def test_legacy_fan_turn_on_variants(
    hass: HomeAssistant, setup_blueair: Callable[..., Any]
) -> None:
    """Turn a legacy fan on at speed 1, to a speed, to auto, or leave a running fan alone."""
    device = make_legacy_device()
    device.api.attributes["fan_speed"] = "0"
    device.api.attributes["mode"] = "auto"
    await setup_blueair(legacy=[device])
    entity_id = "fan.hallway_fan"
    assert hass.states.get(entity_id).attributes[ATTR_PRESET_MODE] == "auto"

    await _call(hass, SERVICE_TURN_ON, entity_id)
    assert device.api.writes[-1] == ("fan_speed", "1")

    # A manual speed turns auto mode off first.
    await _call(hass, SERVICE_TURN_ON, entity_id, percentage=100)
    assert device.api.writes[-2:] == [("fan_auto_mode", False), ("fan_speed", "3")]

    await _call(hass, SERVICE_TURN_ON, entity_id, preset_mode="auto")
    assert device.api.writes[-1] == ("fan_auto_mode", True)

    writes = len(device.api.writes)
    await _call(hass, SERVICE_TURN_ON, entity_id)
    assert len(device.api.writes) == writes


@pytest.mark.asyncio
async def test_legacy_fan_without_auto_mode_has_no_presets(
    hass: HomeAssistant, setup_blueair: Callable[..., Any]
) -> None:
    """Offer no presets, and no preset feature, on legacy models without auto mode."""
    await setup_blueair(legacy=[make_legacy_device(compatibility="classic_205")])

    state = hass.states.get("fan.hallway_fan")

    assert state.attributes.get("preset_modes") in (None, [])
    assert not state.attributes["supported_features"] & 8


@pytest.mark.asyncio
@pytest.mark.parametrize("ap_sub_mode", [None, "x"])
async def test_signature_fan_treats_unknown_ap_sub_mode_as_manual(
    hass: HomeAssistant, setup_blueair: Callable[..., Any], ap_sub_mode: Any
) -> None:
    """Show the speed, and switch to manual before a speed write, when apsubmode is unreadable."""
    device = make_aws_device(
        uuid="sig-1", name="Study", hw="l_blue40", standby=False, fan_speed=37, ap_sub_mode=1
    )
    await setup_blueair(aws=[device])
    entity = entity_object(hass, "fan.study_fan")
    device.ap_sub_mode = ap_sub_mode

    assert entity.preset_mode is None
    assert entity.percentage == 40
    device.fan_speed = None
    assert entity.percentage is None

    await entity.async_set_percentage(100)
    assert device.ap_sub_mode == 1

    writes = len(device.api.writes)
    await entity.async_set_preset_mode("turbo")
    assert len(device.api.writes) == writes


@pytest.mark.asyncio
@pytest.mark.parametrize("combo_mode", [None, "x"])
async def test_combo_fan_treats_unknown_combo_mode_as_manual(
    hass: HomeAssistant, setup_blueair: Callable[..., Any], combo_mode: Any
) -> None:
    """Show the speed, and switch to manual before a speed write, when the combo mode is unreadable."""
    device = make_combo()
    await setup_blueair(aws=[device])
    entity = entity_object(hass, "fan.living_room_fan")
    device.combo_mode = combo_mode

    assert entity.preset_mode is None
    assert entity.percentage == 40
    device.fan_speed = None
    assert entity.percentage is None

    await entity.async_set_percentage(100)
    assert device.combo_mode == 1

    writes = len(device.api.writes)
    await entity.async_set_preset_mode("turbo")
    assert len(device.api.writes) == writes


@pytest.mark.asyncio
async def test_aws_fan_turns_on_into_night_mode(
    hass: HomeAssistant, setup_blueair: Callable[..., Any]
) -> None:
    """Leave standby and switch straight into the night preset."""
    device = make_purifier(standby=True)
    await setup_blueair(aws=[device])

    await _call(hass, SERVICE_TURN_ON, PURIFIER, preset_mode="night")

    assert device.standby is False
    assert device.night_mode is True
    assert hass.states.get(PURIFIER).attributes[ATTR_PERCENTAGE] is None


@pytest.mark.asyncio
async def test_aws_fan_before_the_device_reports_power_and_speed(
    hass: HomeAssistant, setup_blueair: Callable[..., Any]
) -> None:
    """Report an unknown state and no percentage until the device reports them."""
    await setup_blueair(aws=[make_purifier(standby=None, fan_speed=None)])

    fan = entity_object(hass, PURIFIER)

    assert fan.is_on is None
    assert fan.percentage is None


@pytest.mark.asyncio
async def test_legacy_fan_without_a_reported_speed_has_no_percentage(
    hass: HomeAssistant, setup_blueair: Callable[..., Any]
) -> None:
    """Leave the legacy fan's percentage empty when it reports no speed."""
    device = make_legacy_device()
    await setup_blueair(legacy=[device])
    device.fan_speed = None

    assert entity_object(hass, "fan.hallway_fan").percentage is None


@pytest.mark.parametrize(
    ("speed_count", "percentage", "speed"),
    [
        (3, 0, 0),
        (3, 1, 1),
        (3, 10, 1),
        (3, 33, 1),
        (3, 34, 2),
        (3, 66, 2),
        (3, 67, 3),
        (3, 100, 3),
        (91, 1, 1),
        (91, 40, 37),
        (91, 100, 91),
    ],
)
def test_percentages_round_up_to_a_running_speed(
    speed_count: int, percentage: int, speed: int
) -> None:
    """Never turn a fan off for a non-zero percentage, and round-trip reported speeds."""
    coordinator = SimpleNamespace(speed_count=speed_count, fan_speed=speed)

    assert _percentage_speed(coordinator, percentage) == speed
    if percentage:
        # Reading a speed back and setting it again keeps the same speed.
        assert _percentage_speed(coordinator, _speed_percentage(coordinator)) == speed


def _family_coordinator(**attributes: Any) -> SimpleNamespace:
    """Return a stand-in coordinator for the preset families.

    Every preset field defaults to NotImplemented, and every setter is an
    AsyncMock so tests can check what was written.

    Args:
        attributes: Preset field values the device reports.

    Returns:
        SimpleNamespace: The coordinator.
    """
    fields = {
        "ap_sub_mode": NotImplemented,
        "combo_mode": NotImplemented,
        "fan_auto_mode": NotImplemented,
        "night_mode": NotImplemented,
        **attributes,
    }
    setters = {
        name: AsyncMock()
        for name in (
            "set_ap_sub_mode",
            "set_combo_mode",
            "set_fan_auto_mode",
            "set_night_mode",
            "set_fan_speed",
        )
    }
    return SimpleNamespace(**fields, **setters)


@pytest.mark.parametrize(
    ("attributes", "family"),
    [
        ({"ap_sub_mode": 0}, _SIGNATURE_PRESETS),
        # A device with automode as well uses the classic fields, not apsubmode.
        ({"ap_sub_mode": 0, "fan_auto_mode": False}, _CLASSIC_PRESETS),
        ({"combo_mode": 1}, _COMBO_PRESETS),
        ({"fan_auto_mode": False, "night_mode": False}, _CLASSIC_PRESETS),
        ({}, _CLASSIC_PRESETS),
    ],
)
def test_preset_family_follows_the_device_fields(
    attributes: dict[str, Any], family: object
) -> None:
    """Pick the preset family from the shadow fields the device declares."""
    assert _preset_family(_family_coordinator(**attributes)) is family


@pytest.mark.parametrize(
    ("attributes", "preset_modes"),
    [
        ({"fan_auto_mode": False, "night_mode": False}, ["auto", "night"]),
        ({"fan_auto_mode": False}, ["auto"]),
        ({"night_mode": False}, ["night"]),
        ({}, []),
    ],
)
def test_classic_presets_offer_the_fields_the_device_has(
    attributes: dict[str, Any], preset_modes: list[str]
) -> None:
    """Offer Auto and Night only for the fields the device declares."""
    assert _CLASSIC_PRESETS.preset_modes(_family_coordinator(**attributes)) == preset_modes


@pytest.mark.parametrize("family", [_SIGNATURE_PRESETS, _COMBO_PRESETS])
@pytest.mark.parametrize("value", [None, "x", NotImplemented])
def test_mode_field_presets_treat_unreadable_values_as_manual(family: Any, value: object) -> None:
    """Show the speed, and no preset, while the mode field can't be read."""
    coordinator = _family_coordinator(ap_sub_mode=value, combo_mode=value)

    assert family.preset_mode(coordinator) is None
    assert family.shows_speed(coordinator)


@pytest.mark.asyncio
@pytest.mark.parametrize("family", [_SIGNATURE_PRESETS, _COMBO_PRESETS, _CLASSIC_PRESETS])
async def test_unknown_presets_write_nothing(family: Any) -> None:
    """Ignore a preset label the family doesn't know."""
    coordinator = _family_coordinator()

    await family.set_preset_mode(coordinator, "turbo")

    for name in vars(coordinator):
        if name.startswith("set_"):
            getattr(coordinator, name).assert_not_awaited()
