"""Tests for the Blueair light platform."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.components.light import ATTR_BRIGHTNESS, DOMAIN as LIGHT_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.core import HomeAssistant, State
import pytest
from pytest_homeassistant.common import mock_restore_cache

from .conftest import make_humidifier, make_legacy_device, make_purifier


async def _call(hass: HomeAssistant, service: str, entity_id: str, **data: Any) -> None:
    """Call a light service and wait for it.

    Args:
        hass: Home Assistant instance.
        service: Light service name.
        entity_id: Target light.
        data: Service data.
    """
    await hass.services.async_call(
        LIGHT_DOMAIN, service, {ATTR_ENTITY_ID: entity_id, **data}, blocking=True
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("entity_id", "attribute", "full"),
    [
        ("light.bedroom_led_light", "brightness", 100),
        ("light.bedroom_mood_light", "mood_brightness", 100),
    ],
)
async def test_aws_purifier_lights_turn_off_and_back_on(
    hass: HomeAssistant,
    setup_blueair: Callable[..., Any],
    entity_id: str,
    attribute: str,
    full: int,
) -> None:
    """Turn a light off, back on at its last brightness, and to an explicit brightness."""
    device = make_purifier()
    await setup_blueair(aws=[device])
    start = getattr(device, attribute)
    assert hass.states.get(entity_id).state == "on"

    await _call(hass, SERVICE_TURN_OFF, entity_id)
    assert getattr(device, attribute) == 0
    assert hass.states.get(entity_id).state == "off"

    await _call(hass, SERVICE_TURN_ON, entity_id)
    assert getattr(device, attribute) == start

    await _call(hass, SERVICE_TURN_ON, entity_id, brightness=255)
    assert getattr(device, attribute) == full
    assert hass.states.get(entity_id).attributes[ATTR_BRIGHTNESS] == 255


@pytest.mark.asyncio
async def test_humidifier_night_light(
    hass: HomeAssistant, setup_blueair: Callable[..., Any]
) -> None:
    """Dim, switch off and restore the humidifier's night light."""
    device = make_humidifier()
    await setup_blueair(aws=[device])
    entity_id = "light.nursery_night_light"

    await _call(hass, SERVICE_TURN_ON, entity_id, brightness=128)
    assert device.night_light_brightness == 51

    await _call(hass, SERVICE_TURN_OFF, entity_id)
    assert device.night_light_brightness == 0
    assert hass.states.get(entity_id).state == "off"

    await _call(hass, SERVICE_TURN_ON, entity_id)
    assert device.night_light_brightness == 51


@pytest.mark.asyncio
async def test_legacy_led_light_uses_a_four_step_scale(
    hass: HomeAssistant, setup_blueair: Callable[..., Any]
) -> None:
    """Map Home Assistant brightness onto the legacy 0-4 brightness scale."""
    device = make_legacy_device()
    await setup_blueair(legacy=[device])

    await _call(hass, SERVICE_TURN_ON, "light.hallway_led_light", brightness=255)

    assert device.api.writes[-1] == ("brightness", 4)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("restored", "expected"), [(200, 200), (0, 255), ("bad", 255), (None, 255)]
)
async def test_lights_that_start_off_restore_their_last_brightness(
    hass: HomeAssistant,
    setup_blueair: Callable[..., Any],
    restored: Any,
    expected: int,
) -> None:
    """Turn a light that was off at startup back on at the brightness it had before."""
    if restored is not None:
        mock_restore_cache(
            hass,
            [State("light.bedroom_led_light", "off", {"last_brightness": restored})],
        )
    await setup_blueair(aws=[make_purifier(brightness=0)])

    state = hass.states.get("light.bedroom_led_light")

    assert state.state == "off"
    assert state.attributes["last_brightness"] == expected
