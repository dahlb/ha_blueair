"""Tests for the Blueair humidifier platform."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.components.humidifier import (
    ATTR_HUMIDITY,
    ATTR_MODE,
    DOMAIN as HUMIDIFIER_DOMAIN,
    SERVICE_SET_HUMIDITY,
    SERVICE_SET_MODE,
)
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
import pytest

from .conftest import entity_object, make_combo, make_humidifier

HUMIDIFIER = "humidifier.nursery_humidifier"
COMBO = "humidifier.living_room_humidifier"


async def _call(hass: HomeAssistant, service: str, entity_id: str, **data: Any) -> None:
    """Call a humidifier service and wait for it.

    Args:
        hass: Home Assistant instance.
        service: Humidifier service name.
        entity_id: Target humidifier.
        data: Service data.
    """
    await hass.services.async_call(
        HUMIDIFIER_DOMAIN, service, {ATTR_ENTITY_ID: entity_id, **data}, blocking=True
    )


@pytest.mark.asyncio
async def test_humidifier_reports_humidity_and_mode(
    hass: HomeAssistant, setup_blueair: Callable[..., Any]
) -> None:
    """Report the target and current humidity and the active mode."""
    await setup_blueair(aws=[make_humidifier()])

    state = hass.states.get(HUMIDIFIER)

    assert state.state == "on"
    assert state.attributes[ATTR_HUMIDITY] == 45
    assert state.attributes["current_humidity"] == 38
    assert state.attributes[ATTR_MODE] == "fan_speed"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("auto", {"night_mode": False, "fan_auto_mode": True, "standby": False}),
        ("sleep", {"night_mode": True, "fan_auto_mode": False, "standby": False}),
        ("fan_speed", {"fan_auto_mode": False, "night_mode": False, "standby": False}),
    ],
)
async def test_humidifier_set_mode(
    hass: HomeAssistant,
    setup_blueair: Callable[..., Any],
    mode: str,
    expected: dict[str, Any],
) -> None:
    """Switch between auto, sleep and fan-speed modes."""
    device = make_humidifier()
    await setup_blueair(aws=[device])

    await _call(hass, SERVICE_SET_MODE, HUMIDIFIER, mode=mode)

    for attribute, value in expected.items():
        assert getattr(device, attribute) is value


@pytest.mark.asyncio
@pytest.mark.parametrize("target", ["auto", "fan_speed"])
async def test_humidifier_leaves_sleep_mode(
    hass: HomeAssistant, setup_blueair: Callable[..., Any], target: str
) -> None:
    """Keep the device running in sleep and clear night mode when leaving it."""
    device = make_humidifier()
    await setup_blueair(aws=[device])

    await _call(hass, SERVICE_SET_MODE, HUMIDIFIER, mode="sleep")
    await hass.async_block_till_done()
    state = hass.states.get(HUMIDIFIER)
    assert state.state == "on"
    assert state.attributes[ATTR_MODE] == "sleep"

    await _call(hass, SERVICE_SET_MODE, HUMIDIFIER, mode=target)
    await hass.async_block_till_done()
    state = hass.states.get(HUMIDIFIER)
    assert state.state == "on"
    assert state.attributes[ATTR_MODE] == target
    assert device.night_mode is False


@pytest.mark.asyncio
async def test_humidifier_rejects_an_unknown_mode(
    hass: HomeAssistant, setup_blueair: Callable[..., Any]
) -> None:
    """Raise a translated validation error for a mode the humidifier lacks."""
    await setup_blueair(aws=[make_humidifier()])

    with pytest.raises(ServiceValidationError) as raised:
        await entity_object(hass, HUMIDIFIER).async_set_mode("turbo")

    assert raised.value.translation_key == "invalid_mode"
    assert raised.value.translation_placeholders == {"mode": "turbo"}


@pytest.mark.asyncio
async def test_humidifier_set_humidity_turns_on_auto(
    hass: HomeAssistant, setup_blueair: Callable[..., Any]
) -> None:
    """Store the target humidity and switch to auto, the mode that uses it."""
    device = make_humidifier(standby=True)
    await setup_blueair(aws=[device])

    await _call(hass, SERVICE_SET_HUMIDITY, HUMIDIFIER, humidity=55)

    assert device.auto_regulated_humidity == 55
    assert device.fan_auto_mode is True
    assert device.standby is False


@pytest.mark.asyncio
async def test_humidifier_turn_off_and_on(
    hass: HomeAssistant, setup_blueair: Callable[..., Any]
) -> None:
    """Put the humidifier in standby and back."""
    device = make_humidifier()
    await setup_blueair(aws=[device])

    await _call(hass, SERVICE_TURN_OFF, HUMIDIFIER)
    assert device.standby is True
    await _call(hass, SERVICE_TURN_ON, HUMIDIFIER)
    assert device.standby is False


@pytest.mark.asyncio
async def test_combo_humidifier_toggles_humidification_only(
    hass: HomeAssistant, setup_blueair: Callable[..., Any]
) -> None:
    """Switch humidification on a 2-in-1 without powering the purifier down."""
    device = make_combo()
    await setup_blueair(aws=[device])

    state = hass.states.get(COMBO)
    assert state.state == "on"
    assert state.attributes[ATTR_HUMIDITY] == 50

    await _call(hass, SERVICE_TURN_OFF, COMBO)
    assert device.humidifier_mode is False
    assert device.standby is False

    await _call(hass, SERVICE_SET_HUMIDITY, COMBO, humidity=60)
    assert device.auto_regulated_humidity == 60

    await _call(hass, SERVICE_TURN_ON, COMBO)
    assert device.humidifier_mode is True
