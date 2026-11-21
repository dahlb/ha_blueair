"""Tests for the Blueair switch platform."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.core import HomeAssistant
import pytest

from .conftest import make_humidifier, make_legacy_device, make_purifier


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("entity_id", "attribute"),
    [
        ("switch.bedroom_child_lock", "child_lock"),
        ("switch.bedroom_germ_shield", "germ_shield"),
        ("switch.nursery_wick_dry_mode", "wick_dry_mode"),
    ],
)
async def test_aws_switches_toggle_the_device_setting(
    hass: HomeAssistant,
    setup_blueair: Callable[..., Any],
    entity_id: str,
    attribute: str,
) -> None:
    """Turn each AWS switch on and off and report the device's state."""
    devices = [make_purifier(), make_humidifier()]
    await setup_blueair(aws=devices)
    device = devices[0] if entity_id.startswith("switch.bedroom") else devices[1]

    for service, expected in [(SERVICE_TURN_ON, True), (SERVICE_TURN_OFF, False)]:
        await hass.services.async_call(
            SWITCH_DOMAIN, service, {ATTR_ENTITY_ID: entity_id}, blocking=True
        )
        assert getattr(device, attribute) is expected
        assert hass.states.get(entity_id).state == ("on" if expected else "off")


@pytest.mark.asyncio
async def test_legacy_child_lock(hass: HomeAssistant, setup_blueair: Callable[..., Any]) -> None:
    """Send the legacy child lock write."""
    device = make_legacy_device()
    await setup_blueair(legacy=[device])

    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: "switch.hallway_child_lock"}, blocking=True
    )

    assert device.api.writes[-1] == ("child_lock", True)
