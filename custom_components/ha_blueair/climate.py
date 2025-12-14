"""Create climate platform."""

from __future__ import annotations

import time
from logging import Logger, getLogger

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.config_entries import ConfigEntry

from . import BlueairUpdateCoordinatorDeviceAws
from .blueair_update_coordinator import BlueairUpdateCoordinator
from .const import FanMode
from .entity import BlueairEntity, async_setup_entry_helper

_LOGGER: Logger = getLogger(__package__)

MIN_TEMP_C = 15.0
MAX_TEMP_C = 37.0
TEMP_STEP_C = 1.0

FAN_SPEED_BY_STEP: dict[str, int] = {
    FanMode.STEP1.value: 11,
    FanMode.STEP2.value: 37,
    FanMode.STEP3.value: 64,
    FanMode.STEP4.value: 91,
}


async def async_setup_entry(hass, config_entry: ConfigEntry, async_add_entities):
    async_setup_entry_helper(
        hass,
        config_entry,
        async_add_entities,
        entity_classes=[BlueairThermostat],
    )


def _fan_mode_from_speed(speed: int | float | None | NotImplemented) -> str | None:
    if speed in (None, NotImplemented):
        return None
    try:
        s = float(speed)
    except (TypeError, ValueError):
        return None

    if s < 12:
        return FanMode.STEP1.value
    if s < 38:
        return FanMode.STEP2.value
    if s < 65:
        return FanMode.STEP3.value
    return FanMode.STEP4.value


class BlueairThermostat(BlueairEntity, ClimateEntity):
    @classmethod
    def is_implemented(cls, coordinator: BlueairUpdateCoordinator) -> bool:
        return (
            coordinator.main_mode is not NotImplemented
            and coordinator.temperature is not NotImplemented
        )

    _enable_turn_on_off_backwards_compatibility = False
    _attr_min_temp = MIN_TEMP_C
    _attr_max_temp = MAX_TEMP_C
    _attr_target_temperature_step = TEMP_STEP_C

    def __init__(self, coordinator: BlueairUpdateCoordinatorDeviceAws):
        super().__init__("Climate", coordinator)

        self._attr_hvac_modes = [
            HVACMode.OFF,
            HVACMode.FAN_ONLY,
            HVACMode.HEAT,
            HVACMode.COOL,
        ]

        self._optimistic_until: float = 0.0
        self._optimistic_hvac_mode: HVACMode | None = None
        self._optimistic_fan_mode: str | None = None
        self._optimistic_target_temperature: float | None = None

        self._last_fan_mode_fan_only: str | None = None
        self._last_fan_mode_cool: str | None = None
        self._last_fan_mode_heat: str | None = None

        self._apply_from_coordinator(force=True)

    @property
    def supported_features(self) -> ClimateEntityFeature:
        feats = (
            ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
            | ClimateEntityFeature.FAN_MODE
        )
        if self.hvac_mode == HVACMode.HEAT:
            feats |= ClimateEntityFeature.TARGET_TEMPERATURE
        return feats

    def _now(self) -> float:
        return time.monotonic()

    def _is_optimistic(self) -> bool:
        return self._now() < self._optimistic_until

    def _start_optimistic(self, seconds: float = 10.0) -> None:
        self._optimistic_until = self._now() + seconds

    def _coordinator_hvac_mode(self) -> HVACMode | None:
        if self.coordinator.is_on is False:
            return HVACMode.OFF

        match int(self.coordinator.main_mode or 0):
            case 0:
                return HVACMode.FAN_ONLY
            case 1:
                return HVACMode.HEAT
            case 2:
                return HVACMode.COOL
        return None

    def _coordinator_fan_mode(self, hvac: HVACMode | None) -> str | None:
        if hvac == HVACMode.FAN_ONLY:
            if int(self.coordinator.ap_sub_mode or 0) == 2:
                return FanMode.AUTO.value
            return _fan_mode_from_speed(self.coordinator.fan_speed_0)

        if hvac == HVACMode.HEAT:
            if int(self.coordinator.heat_sub_mode or 0) == 2:
                return FanMode.AUTO.value
            return _fan_mode_from_speed(self.coordinator.heat_fan_speed)

        if hvac == HVACMode.COOL:
            return _fan_mode_from_speed(self.coordinator.cool_fan_speed)

        return None

    def _coordinator_target_temperature(self, hvac: HVACMode | None) -> float | None:
        if hvac != HVACMode.HEAT:
            return None

        raw = self.coordinator.heat_temp
        if raw in (None, NotImplemented):
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    def _remember_last_fan_mode(self, hvac: HVACMode | None, fan: str | None) -> None:
        if fan in (None, NotImplemented):
            return

        if hvac == HVACMode.FAN_ONLY:
            self._last_fan_mode_fan_only = fan
        elif hvac == HVACMode.COOL:
            self._last_fan_mode_cool = (
                fan if fan != FanMode.AUTO.value else FanMode.STEP1.value
            )
        elif hvac == HVACMode.HEAT:
            self._last_fan_mode_heat = fan

    def _apply_from_coordinator(self, *, force: bool = False) -> None:
        hvac = self._coordinator_hvac_mode()
        fan = self._coordinator_fan_mode(hvac)
        tgt = self._coordinator_target_temperature(hvac)

        self._attr_current_temperature = self.coordinator.temperature
        self._attr_current_humidity = self.coordinator.humidity

        self._remember_last_fan_mode(hvac, fan)

        if force or not self._is_optimistic():
            self._attr_hvac_mode = hvac
            self._attr_fan_mode = fan
            self._attr_target_temperature = tgt
            self._optimistic_hvac_mode = None
            self._optimistic_fan_mode = None
            self._optimistic_target_temperature = None
            return

        if self._optimistic_hvac_mode is not None and hvac == self._optimistic_hvac_mode:
            self._attr_hvac_mode = hvac
            self._optimistic_hvac_mode = None

        if self._optimistic_fan_mode is not None and fan == self._optimistic_fan_mode:
            self._attr_fan_mode = fan
            self._optimistic_fan_mode = None

        if (
            self._optimistic_target_temperature is not None
            and tgt is not None
            and abs(tgt - self._optimistic_target_temperature) < 0.01
        ):
            self._attr_target_temperature = tgt
            self._optimistic_target_temperature = None

    @property
    def temperature_unit(self) -> str:
        raw = self.coordinator.temperature_unit
        try:
            unit = int(raw) if raw not in (None, NotImplemented) else None
        except (TypeError, ValueError):
            unit = None
        return UnitOfTemperature.CELSIUS if unit == 0 else UnitOfTemperature.FAHRENHEIT

    @property
    def fan_modes(self) -> list[str]:
        steps = [
            FanMode.STEP1.value,
            FanMode.STEP2.value,
            FanMode.STEP3.value,
            FanMode.STEP4.value,
        ]
        if self.hvac_mode == HVACMode.COOL:
            return steps
        return [FanMode.AUTO.value, *steps]

    @property
    def target_temperature(self) -> float | None:
        if self.hvac_mode != HVACMode.HEAT:
            return None
        return self._attr_target_temperature

    @property
    def fan_mode(self) -> str | None:
        return self._attr_fan_mode

    def _handle_coordinator_update(self) -> None:
        self._apply_from_coordinator()
        super()._handle_coordinator_update()

    async def async_turn_on(self) -> None:
        await self.coordinator.set_running(True)

    async def async_turn_off(self) -> None:
        await self.coordinator.set_running(False)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            self._start_optimistic()
            self._attr_hvac_mode = HVACMode.OFF
            self._optimistic_hvac_mode = HVACMode.OFF
            self._attr_target_temperature = None
            self._optimistic_target_temperature = None
            self.async_write_ha_state()
            await self.coordinator.set_running(False)
            return

        mode_map: dict[HVACMode, int] = {
            HVACMode.FAN_ONLY: 0,
            HVACMode.HEAT: 1,
            HVACMode.COOL: 2,
        }
        mode = mode_map.get(hvac_mode)
        if mode is None:
            return

        self._start_optimistic()
        self._attr_hvac_mode = hvac_mode
        self._optimistic_hvac_mode = hvac_mode

        if hvac_mode != HVACMode.HEAT:
            self._attr_target_temperature = None
            self._optimistic_target_temperature = None

        self.async_write_ha_state()

        if not self.coordinator.is_on:
            await self.coordinator.set_running(True)

        await self.coordinator.set_main_mode(mode)

        if hvac_mode == HVACMode.HEAT:
            self._remember_last_fan_mode(HVACMode.HEAT, FanMode.AUTO.value)
            self._optimistic_fan_mode = FanMode.AUTO.value
            self._attr_fan_mode = FanMode.AUTO.value
            self.async_write_ha_state()
            await self.coordinator.set_heat_sub_mode(2)
            return

        if hvac_mode == HVACMode.FAN_ONLY:
            desired = self._last_fan_mode_fan_only or FanMode.AUTO.value
            self._optimistic_fan_mode = desired
            self._attr_fan_mode = desired
            self.async_write_ha_state()

            if desired == FanMode.AUTO.value:
                await self.coordinator.set_ap_sub_mode(2)
                return

            speed = FAN_SPEED_BY_STEP.get(desired)
            if speed is None:
                return

            await self.coordinator.set_ap_sub_mode(1)
            await self.coordinator.set_fan_speed_0(speed)
            return

        if hvac_mode == HVACMode.COOL:
            desired = self._last_fan_mode_cool or FanMode.STEP1.value
            if desired == FanMode.AUTO.value:
                desired = FanMode.STEP1.value

            self._remember_last_fan_mode(HVACMode.COOL, desired)

            self._optimistic_fan_mode = desired
            self._attr_fan_mode = desired
            self.async_write_ha_state()

            speed = FAN_SPEED_BY_STEP.get(
                desired, FAN_SPEED_BY_STEP[FanMode.STEP1.value]
            )
            await self.coordinator.set_cool_sub_mode(1)
            await self.coordinator.set_cool_fan_speed(speed)
            return

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        self._start_optimistic()

        if fan_mode == FanMode.AUTO.value:
            if self.hvac_mode == HVACMode.COOL:
                return

            self._attr_fan_mode = FanMode.AUTO.value
            self._optimistic_fan_mode = FanMode.AUTO.value
            self.async_write_ha_state()

            match self.hvac_mode:
                case HVACMode.FAN_ONLY:
                    self._remember_last_fan_mode(HVACMode.FAN_ONLY, FanMode.AUTO.value)
                    await self.coordinator.set_ap_sub_mode(2)
                case HVACMode.HEAT:
                    self._remember_last_fan_mode(HVACMode.HEAT, FanMode.AUTO.value)
                    await self.coordinator.set_heat_sub_mode(2)
            return

        speed = FAN_SPEED_BY_STEP.get(fan_mode)
        if speed is None:
            return

        match self.hvac_mode:
            case HVACMode.FAN_ONLY:
                self._remember_last_fan_mode(HVACMode.FAN_ONLY, fan_mode)
                await self.coordinator.set_ap_sub_mode(1)
                await self.coordinator.set_fan_speed_0(speed)
            case HVACMode.HEAT:
                self._remember_last_fan_mode(HVACMode.HEAT, fan_mode)
                await self.coordinator.set_heat_sub_mode(1)
                await self.coordinator.set_heat_fan_speed(speed)
            case HVACMode.COOL:
                self._remember_last_fan_mode(HVACMode.COOL, fan_mode)
                await self.coordinator.set_cool_sub_mode(1)
                await self.coordinator.set_cool_fan_speed(speed)

        self._attr_fan_mode = fan_mode
        self._optimistic_fan_mode = fan_mode
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        if self.hvac_mode != HVACMode.HEAT:
            return

        temp_c = float(temperature)
        temp_c = max(MIN_TEMP_C, min(MAX_TEMP_C, temp_c))

        self._start_optimistic()
        self._attr_target_temperature = temp_c
        self._optimistic_target_temperature = temp_c
        self.async_write_ha_state()

        await self.coordinator.set_heat_temp(temp_c)
