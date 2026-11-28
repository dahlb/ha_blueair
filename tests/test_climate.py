"""Tests for the Blueair climate entity's native temperature API (issue #440)."""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from typing import Any

from homeassistant.components.climate import HVACMode
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant.common import async_fire_time_changed  # type: ignore[import-untyped]

from custom_components.ha_blueair.climate import (
    HEAT_REFUSAL_CHECK_S,
    HEAT_REFUSAL_GRACE_S,
    HEAT_REFUSAL_WINDOW_S,
    BlueairThermostat,
)
from custom_components.ha_blueair.config_flow import ConfigFlowHandler
from custom_components.ha_blueair.const import DOMAIN

from .conftest import entity_object, make_climate_device


def make_coordinator(**overrides: Any) -> SimpleNamespace:
    """Build a stub coordinator for a heater/cooler in heat mode.

    Args:
        **overrides: Coordinator attribute values to replace the defaults.

    Returns:
        A namespace exposing the attributes the climate entity reads.
    """
    values: dict[str, Any] = {
        "device_name": "Heater",
        "id": "abc123",
        "is_on": True,
        "main_mode": 1,
        "heat_sub_mode": 2,
        "ap_sub_mode": 2,
        "fan_speed_0": 11,
        "heat_fan_speed": 11,
        "cool_fan_speed": 11,
        "heat_temp": 22,
        "temperature": 20.5,
        "humidity": 40,
        "temperature_unit": 0,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.parametrize(
    "name",
    ["temperature_unit", "target_temperature", "current_temperature"],
)
def test_no_deprecated_temperature_members(name: str) -> None:
    """The entity must not override deprecated non-native temperature members.

    Args:
        name: Deprecated ClimateEntity member name.
    """
    assert name not in BlueairThermostat.__dict__


def test_config_flow_has_no_connection_class() -> None:
    """The config flow must not use the deprecated CONN_CLASS_* constants."""
    assert "CONNECTION_CLASS" not in ConfigFlowHandler.__dict__


@pytest.mark.parametrize(
    ("raw_unit", "expected"),
    [
        (0, UnitOfTemperature.CELSIUS),
        (1, UnitOfTemperature.FAHRENHEIT),
        (None, UnitOfTemperature.FAHRENHEIT),
        (NotImplemented, UnitOfTemperature.FAHRENHEIT),
        ("bad", UnitOfTemperature.FAHRENHEIT),
    ],
)
def test_native_temperature_unit(raw_unit: object, expected: str) -> None:
    """native_temperature_unit maps the device unit setting.

    Args:
        raw_unit: Raw temperature_unit value from the coordinator.
        expected: Expected Home Assistant unit.
    """
    entity = BlueairThermostat(make_coordinator(temperature_unit=raw_unit))
    assert entity.native_temperature_unit == expected


def test_native_temperatures_in_heat_mode() -> None:
    """Current and target temperatures are exposed through the native API."""
    entity = BlueairThermostat(make_coordinator())
    assert entity.hvac_mode == HVACMode.HEAT
    assert entity.native_current_temperature == 20.5
    assert entity.native_target_temperature == 22.0


def test_native_target_temperature_none_outside_heat() -> None:
    """No target temperature is reported outside heat mode."""
    entity = BlueairThermostat(make_coordinator(main_mode=2))
    assert entity.hvac_mode == HVACMode.COOL
    assert entity.native_target_temperature is None


async def test_set_temperature_updates_native_target() -> None:
    """Setting the temperature updates the native target and clamps it."""
    calls: list[float] = []

    async def set_heat_temp(value: float) -> None:
        """Record the requested heat temperature.

        Args:
            value: Requested temperature.
        """
        calls.append(value)

    entity = BlueairThermostat(make_coordinator(set_heat_temp=set_heat_temp))
    entity.async_write_ha_state = lambda: None
    await entity.async_set_temperature(temperature=99)
    assert calls == [37.0]
    assert entity.native_target_temperature == 37.0


# --- Home Assistant workflow tests against a fake T10i / T20i ------------------

CLIMATE = "climate.office_climate"


async def _climate_call(hass: Any, service: str, **data: Any) -> None:
    """Call a climate service on the fake T10i and wait for it.

    Args:
        hass: Home Assistant instance.
        service: Climate service name.
        data: Service data.
    """
    await hass.services.async_call(
        "climate", service, {"entity_id": CLIMATE, **data}, blocking=True
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("hvac_mode", "expected"),
    [
        ("heat", {"main_mode": 1, "heat_sub_mode": 2}),
        # The fake's apsubmode is manual at step 2, so fan-only resumes that speed.
        ("fan_only", {"main_mode": 0, "ap_sub_mode": 1, "fan_speed_0": 37}),
        ("cool", {"main_mode": 2, "cool_sub_mode": 1, "cool_fan_speed": 11}),
        ("off", {"standby": True}),
    ],
)
async def test_climate_set_hvac_mode_writes_the_device_mode(
    hass: Any, setup_blueair: Any, hvac_mode: str, expected: dict[str, Any]
) -> None:
    """Translate each HVAC mode into the T10i's main mode and sub mode."""
    device = make_climate_device(main_mode=0)
    await setup_blueair(aws=[device])

    await _climate_call(hass, "set_hvac_mode", hvac_mode=hvac_mode)

    for attribute, value in expected.items():
        assert getattr(device, attribute) == value
    assert hass.states.get(CLIMATE).state == hvac_mode


@pytest.mark.asyncio
async def test_climate_turns_the_device_on_before_changing_mode(
    hass: Any, setup_blueair: Any
) -> None:
    """Leave standby before switching a T10i that was off into a mode."""
    device = make_climate_device(standby=True)
    await setup_blueair(aws=[device])
    assert hass.states.get(CLIMATE).state == "off"

    await _climate_call(hass, "set_hvac_mode", hvac_mode="heat")

    assert device.standby is False
    assert device.main_mode == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("main_mode", "fan_mode", "expected"),
    [
        (1, "step3", {"heat_sub_mode": 1, "heat_fan_speed": 64}),
        (1, "auto", {"heat_sub_mode": 2}),
        (0, "step2", {"ap_sub_mode": 1, "fan_speed_0": 37}),
        (0, "auto", {"ap_sub_mode": 2}),
        (2, "step4", {"cool_sub_mode": 1, "cool_fan_speed": 91}),
    ],
)
async def test_climate_set_fan_mode_uses_the_active_modes_fields(
    hass: Any,
    setup_blueair: Any,
    main_mode: int,
    fan_mode: str,
    expected: dict[str, Any],
) -> None:
    """Write the fan mode to the heat, fan-only or cool settings of the current mode."""
    device = make_climate_device(main_mode=main_mode)
    await setup_blueair(aws=[device])

    await _climate_call(hass, "set_fan_mode", fan_mode=fan_mode)

    for attribute, value in expected.items():
        assert getattr(device, attribute) == value


@pytest.mark.asyncio
async def test_climate_set_temperature_in_heat_mode(hass: Any, setup_blueair: Any) -> None:
    """Send the heating target in tenths of a degree."""
    device = make_climate_device()
    await setup_blueair(aws=[device])
    assert hass.states.get(CLIMATE).attributes["temperature"] == 22.0

    await _climate_call(hass, "set_temperature", temperature=25)

    assert device.heat_temp == 250
    assert hass.states.get(CLIMATE).attributes["temperature"] == 25.0


@pytest.mark.asyncio
async def test_climate_turn_off_and_on(hass: Any, setup_blueair: Any) -> None:
    """Put the T10i in standby and bring it back."""
    device = make_climate_device()
    await setup_blueair(aws=[device])

    await _climate_call(hass, "turn_off")
    assert device.standby is True
    await _climate_call(hass, "turn_on")
    assert device.standby is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("overrides", "hvac", "fan"),
    [
        ({"main_mode": 1, "heat_sub_mode": 1, "heat_fan_speed": 10}, "heat", "step1"),
        ({"main_mode": 1, "heat_sub_mode": 1, "heat_fan_speed": 64}, "heat", "step3"),
        ({"main_mode": 1, "heat_sub_mode": 1, "heat_fan_speed": 91}, "heat", "step4"),
        ({"main_mode": 0, "ap_sub_mode": 2}, "fan_only", "auto"),
        ({"main_mode": 2, "cool_fan_speed": None}, "cool", None),
        ({"main_mode": 2, "cool_fan_speed": "fast"}, "cool", None),
        ({"main_mode": 7}, None, None),
    ],
)
async def test_climate_reads_mode_and_fan_from_the_device(
    hass: Any,
    setup_blueair: Any,
    overrides: dict[str, Any],
    hvac: str | None,
    fan: str | None,
) -> None:
    """Bucket fan speeds into steps and tolerate values the T10i should not send."""
    await setup_blueair(aws=[make_climate_device(**overrides)])

    entity = entity_object(hass, CLIMATE)

    assert entity.hvac_mode == hvac
    assert entity.fan_mode == fan


@pytest.mark.asyncio
async def test_climate_ignores_requests_it_cannot_apply(hass: Any, setup_blueair: Any) -> None:
    """Skip unsupported HVAC modes, unknown fan modes and temperatures outside heat mode."""
    device = make_climate_device(main_mode=2)
    await setup_blueair(aws=[device])
    entity = entity_object(hass, CLIMATE)
    writes = len(device.api.writes)

    await entity.async_set_hvac_mode(HVACMode.DRY)
    await entity.async_set_fan_mode("auto")  # cool mode has no auto fan
    await entity.async_set_fan_mode("turbo")
    await entity.async_set_temperature(temperature=24)  # not in heat mode
    await entity.async_set_temperature()

    assert len(device.api.writes) == writes


@pytest.mark.asyncio
async def test_climate_hands_back_to_the_device_after_the_optimistic_window(
    hass: Any, setup_blueair: Any
) -> None:
    """Show the requested mode right away, then follow the device once it reports back."""
    device = make_climate_device(main_mode=0, ap_sub_mode=2)
    entry = await setup_blueair(aws=[device])
    entity = entity_object(hass, CLIMATE)

    await entity.async_set_hvac_mode(HVACMode.HEAT)
    assert entity.hvac_mode == HVACMode.HEAT

    # The device reports the change while the optimistic window is still open.
    entry.runtime_data.aws_devices[0].async_update_listeners()
    assert entity.hvac_mode == HVACMode.HEAT
    assert entity.fan_mode == "auto"

    # Once the window has passed, a later device change wins.
    entity._optimistic_until = 0
    device.main_mode = 2
    entry.runtime_data.aws_devices[0].async_update_listeners()
    assert entity.hvac_mode == HVACMode.COOL


@pytest.mark.asyncio
async def test_climate_resumes_remembered_fan_modes(hass: Any, setup_blueair: Any) -> None:
    """Resume the last fan mode per HVAC mode, falling back when it cannot be used."""
    device = make_climate_device(main_mode=1)
    await setup_blueair(aws=[device])
    entity = entity_object(hass, CLIMATE)

    entity._last_fan_mode_cool = "auto"
    await entity.async_set_hvac_mode(HVACMode.COOL)
    assert device.cool_fan_speed == 11

    entity._last_fan_mode_fan_only = "turbo"
    writes = len(device.api.writes)
    await entity.async_set_hvac_mode(HVACMode.FAN_ONLY)
    assert device.main_mode == 0
    assert [write[1] for write in device.api.writes[writes:]] == ["mainmode"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("overrides", "target"),
    [
        ({"heat_temp": None}, None),
        ({"heat_temp": "hot"}, None),
        ({"main_mode": None}, None),
        ({"main_mode": "x"}, None),
    ],
)
async def test_climate_target_temperature_tolerates_unreadable_values(
    hass: Any, setup_blueair: Any, overrides: dict[str, Any], target: float | None
) -> None:
    """Show no heating target when the device's value cannot be read."""
    await setup_blueair(aws=[make_climate_device(**overrides)])

    assert entity_object(hass, CLIMATE).target_temperature == target


@pytest.mark.asyncio
async def test_climate_fan_only_resumes_auto_and_follows_new_targets(
    hass: Any, setup_blueair: Any
) -> None:
    """Resume auto in fan-only mode, and pick up a heating target set on the device."""
    device = make_climate_device(main_mode=1, ap_sub_mode=2)
    entry = await setup_blueair(aws=[device])
    entity = entity_object(hass, CLIMATE)

    await entity.async_set_hvac_mode(HVACMode.FAN_ONLY)
    assert device.ap_sub_mode == 2

    await entity.async_set_hvac_mode(HVACMode.HEAT)
    entity._optimistic_until = 0
    device.heat_temp = 260
    entry.runtime_data.aws_devices[0].async_update_listeners()
    assert entity.target_temperature == 26.0


HEAT_REFUSED_ISSUE = "heat_refused_climate-1"


def _heat_refused_issue(hass: Any) -> ir.IssueEntry | None:
    """Return the fake T10i's heat refused repair issue, if raised.

    Args:
        hass: Home Assistant instance.

    Returns:
        The issue entry, or None when there is no issue.
    """
    return ir.async_get(hass).async_get_issue(DOMAIN, HEAT_REFUSED_ISSUE)


@pytest.mark.asyncio
async def test_climate_flags_a_device_that_refuses_to_heat(hass: Any, setup_blueair: Any) -> None:
    """Show the device's mode and raise a repair issue when it will not heat (issue #268)."""
    device = make_climate_device(main_mode=0, ap_sub_mode=2)
    entry = await setup_blueair(aws=[device])
    coordinator = entry.runtime_data.aws_devices[0]

    entity = entity_object(hass, CLIMATE)

    await _climate_call(hass, "set_hvac_mode", hvac_mode="heat")
    assert hass.states.get(CLIMATE).state == "heat"

    # The cloud echoes the old state right after the write; that is no refusal.
    device.main_mode = 0
    coordinator.async_update_listeners()
    assert hass.states.get(CLIMATE).state == "heat"
    assert _heat_refused_issue(hass) is None

    # A US T10i keeps reporting fan-only once the device has had time to act.
    entity._heat_requested_at -= HEAT_REFUSAL_GRACE_S
    coordinator.async_update_listeners()
    await hass.async_block_till_done()

    assert hass.states.get(CLIMATE).state == "fan_only"
    issue = _heat_refused_issue(hass)
    assert issue is not None
    assert issue.translation_key == "heat_refused"
    assert issue.translation_placeholders == {"device_name": "Office"}

    # Heating started on the device itself clears the issue.
    device.main_mode = 1
    coordinator.async_update_listeners()
    assert hass.states.get(CLIMATE).state == "heat"
    assert _heat_refused_issue(hass) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel", ["window_passed", "new_mode", "turn_off"])
async def test_climate_only_flags_heat_refused_while_the_request_is_pending(
    hass: Any, setup_blueair: Any, cancel: str
) -> None:
    """Treat a later mode change as the device's own, not a refused heat request.

    Args:
        hass: Home Assistant instance.
        setup_blueair: Fixture that sets up the integration with fake devices.
        cancel: How the heat request stops waiting for the device.
    """
    device = make_climate_device(main_mode=0, ap_sub_mode=2)
    entry = await setup_blueair(aws=[device])
    entity = entity_object(hass, CLIMATE)

    await entity.async_set_hvac_mode(HVACMode.HEAT)
    entity._heat_requested_at -= HEAT_REFUSAL_GRACE_S
    match cancel:
        case "window_passed":
            entity._heat_requested_at -= HEAT_REFUSAL_WINDOW_S
        case "new_mode":
            await entity.async_set_hvac_mode(HVACMode.COOL)
        case "turn_off":
            await entity.async_turn_off()
            device.standby = False

    entity._optimistic_until = 0
    device.main_mode = 0
    entry.runtime_data.aws_devices[0].async_update_listeners()

    assert entity.hvac_mode == HVACMode.FAN_ONLY
    assert _heat_refused_issue(hass) is None


@pytest.mark.asyncio
async def test_climate_removes_the_heat_refused_issue_on_unload(
    hass: Any, setup_blueair: Any
) -> None:
    """Drop the heat refused repair issue when the entity goes away."""
    device = make_climate_device(main_mode=0)
    entry = await setup_blueair(aws=[device])

    await _climate_call(hass, "set_hvac_mode", hvac_mode="heat")
    entity_object(hass, CLIMATE)._heat_requested_at -= HEAT_REFUSAL_GRACE_S
    device.main_mode = 2
    entry.runtime_data.aws_devices[0].async_update_listeners()
    assert _heat_refused_issue(hass) is not None

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert _heat_refused_issue(hass) is None


@pytest.mark.asyncio
async def test_climate_polls_to_confirm_heat(hass: Any, setup_blueair: Any) -> None:
    """Poll after the grace period, since the device may push nothing more over MQTT."""
    device = make_climate_device(main_mode=0, ap_sub_mode=2)
    await setup_blueair(aws=[device])
    entity = entity_object(hass, CLIMATE)

    await _climate_call(hass, "set_hvac_mode", hvac_mode="heat")
    assert entity._cancel_heat_check is not None

    # The device ignored the write; its state still reads fan-only on the poll.
    device.main_mode = 0
    entity._heat_requested_at -= HEAT_REFUSAL_CHECK_S
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=HEAT_REFUSAL_CHECK_S))
    await hass.async_block_till_done()

    assert entity._cancel_heat_check is None
    assert hass.states.get(CLIMATE).state == "fan_only"
    assert _heat_refused_issue(hass) is not None
