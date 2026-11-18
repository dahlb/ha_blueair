"""Tests for the Blueair climate entity's native temperature API (issue #440)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from homeassistant.components.climate import HVACMode
from homeassistant.const import UnitOfTemperature
import pytest

from custom_components.ha_blueair.climate import BlueairThermostat
from custom_components.ha_blueair.config_flow import ConfigFlowHandler


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
