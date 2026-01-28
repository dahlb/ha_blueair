"""Blueair device object."""
from __future__ import annotations

import logging

from math import ceil
from homeassistant.util.color import (
    value_to_brightness,
    brightness_to_value,
)

from blueair_api import ModelEnum, DeviceAws

from .blueair_update_coordinator import BlueairUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class BlueairUpdateCoordinatorDeviceAws(BlueairUpdateCoordinator):
    """Blueair device object."""
    blueair_api_device: DeviceAws

    @property
    def model(self) -> str:
        """Return api package enum of device model."""
        model = self.blueair_api_device.model
        if model == ModelEnum.UNKNOWN:
            model = f"Unknown ({self.blueair_api_device.sku})"
        return model

    @property
    def hw_version(self) -> str:
        return self.blueair_api_device.mcu_firmware

    @property
    def sw_version(self) -> str:
        return self.blueair_api_device.firmware

    @property
    def serial_number(self) -> str:
        return self.blueair_api_device.serial_number

    @property
    def fan_speed(self) -> int | None | NotImplemented:
        """Return the current fan speed."""
        return self.blueair_api_device.fan_speed

    @property
    def speed_count(self) -> int:
        """Return the max fan speed."""
        return self.blueair_api_device.fan_speed_count

    @property
    def is_on(self) -> bool | None | NotImplemented:
        """Return the current fan state."""
        if self.blueair_api_device.standby is None or self.blueair_api_device.standby is NotImplemented:
            return self.blueair_api_device.standby
        else:
            return not self.blueair_api_device.standby

    @property
    def brightness(self) -> int | None | NotImplemented:
        """Return the brightness of this light between 0..255."""
        if self.blueair_api_device.brightness is None or self.blueair_api_device.brightness is NotImplemented:
            return self.blueair_api_device.brightness
        else:
            return round(self.blueair_api_device.brightness / 100 * 255.0, 0)
    @property
    def germ_shield(self) -> bool | None | NotImplemented:
        return self.blueair_api_device.germ_shield

    @property
    def child_lock(self) -> bool | None | NotImplemented:
        return self.blueair_api_device.child_lock

    @property
    def night_mode(self) -> bool | None | NotImplemented:
        return self.blueair_api_device.night_mode

    @property
    def temperature(self) -> float | None | NotImplemented:
        raw = self.blueair_api_device.temperature
        if raw in (None, NotImplemented):
            return raw
        try:
            return float(raw)
        except (TypeError, ValueError):
            return raw

    @property
    def humidity(self) -> int | None | NotImplemented:
        return self.blueair_api_device.humidity

    @property
    def auto_regulated_humidity(self) -> int | None | NotImplemented:
        return self.blueair_api_device.auto_regulated_humidity

    @property
    def voc(self) -> int | None | NotImplemented:
        if self.blueair_api_device.total_voc is NotImplemented:
            return self.blueair_api_device.voc
        else:
            return self.blueair_api_device.total_voc

    @property
    def pm1(self) -> int | None | NotImplemented:
        pm1 = self.blueair_api_device.pm1
        if pm1 is None or pm1 is NotImplemented:
            return pm1
        return int((pm1 * 100) // 132)

    @property
    def pm10(self) -> int | None | NotImplemented:
        pm10 = self.blueair_api_device.pm10
        if pm10 is None or pm10 is NotImplemented:
            return pm10
        return int((pm10 * 100) // 132)

    @property
    def pm25(self) -> int | None | NotImplemented:
        # pm25 is the more common name for pm2.5.
        pm25 = self.blueair_api_device.pm2_5
        if pm25 is None or pm25 is NotImplemented:
            return pm25
        return int((pm25 * 100) // 132)

    @property
    def co2(self) -> int | None | NotImplemented:
        return NotImplemented

    @property
    def fan_auto_mode(self) -> bool | None | NotImplemented:
        return self.blueair_api_device.fan_auto_mode

    @property
    def wick_dry_mode(self) -> bool | None | NotImplemented:
        return self.blueair_api_device.wick_dry_mode

    @property
    def water_shortage(self) -> bool | None | NotImplemented:
        return self.blueair_api_device.water_shortage

    @property
    def filter_expired(self) -> bool | None | NotImplemented:
        return NotImplemented

    @property
    def filter_life(self) -> int | None | NotImplemented:
        if self.blueair_api_device.filter_usage_percentage in (NotImplemented, None):
            return self.blueair_api_device.filter_usage_percentage
        return 100 - self.blueair_api_device.filter_usage_percentage

    @property
    def wick_life(self) -> int | None | NotImplemented:
        if self.blueair_api_device.wick_usage_percentage in (NotImplemented, None):
            return self.blueair_api_device.wick_usage_percentage
        return 100 - self.blueair_api_device.wick_usage_percentage

    @property
    def water_refresher_life(self) -> int | None | NotImplemented:
        if self.blueair_api_device.water_refresher_usage_percentage in (NotImplemented, None):
            return self.blueair_api_device.water_refresher_usage_percentage
        return 100 - self.blueair_api_device.water_refresher_usage_percentage

    @property
    def water_level(self) -> int | None | NotImplemented:
        return self.blueair_api_device.water_level

    @property
    def mood_brightness_scale(self) -> tuple[int, int]:
        if self.blueair_api_device.model == ModelEnum.HUMIDIFIER_H76I:
            return (1, 3)
        return (1, 100)

    @property
    def mood_brightness(self) -> int | None | NotImplemented:
        if self.blueair_api_device.mood_brightness not in (None, NotImplemented):
            return value_to_brightness(self.mood_brightness_scale, self.blueair_api_device.mood_brightness)
        return self.blueair_api_device.mood_brightness

    @property
    def mood_brightness_is_on(self) -> int | None | NotImplemented:
        return self.blueair_api_device.mood_brightness != 0

    @property
    def main_mode(self) -> int | None | NotImplemented:
        return self.blueair_api_device.main_mode

    @property
    def heat_temp(self) -> float | None | NotImplemented:
        raw = self.blueair_api_device.heat_temp
        if raw in (None, NotImplemented):
            return raw
        try:
            return float(raw) / 10.0
        except (TypeError, ValueError):
            return raw

    @property
    def heat_sub_mode(self) -> int | None | NotImplemented:
        return self.blueair_api_device.heat_sub_mode

    @property
    def heat_fan_speed(self) -> int | None | NotImplemented:
        return self.blueair_api_device.heat_fan_speed

    @property
    def cool_sub_mode(self) -> int | None | NotImplemented:
        return self.blueair_api_device.cool_sub_mode

    @property
    def cool_fan_speed(self) -> int | None | NotImplemented:
        return self.blueair_api_device.cool_fan_speed

    @property
    def ap_sub_mode(self) -> int | None | NotImplemented:
        return self.blueair_api_device.ap_sub_mode

    @property
    def fan_speed_0(self) -> int | None | NotImplemented:
        return self.blueair_api_device.fan_speed_0

    @property
    def temperature_unit(self) -> int | None | NotImplemented:
        raw = self.blueair_api_device.temperature_unit
        if raw in (None, NotImplemented):
            return raw
        try:
            return int(raw)
        except (TypeError, ValueError):
            return raw

    async def set_running(self, running) -> None:
        await self.blueair_api_device.set_standby(not running)
        await self.async_request_refresh()

    async def set_brightness(self, brightness) -> None:
        # Convert Home Assistant brightness (0-255) to Abode brightness (0-99)
        # If 100 is sent to Abode, response is 99 causing an error
        await self.blueair_api_device.set_brightness(round(brightness * 100 / 255.0))
        await self.async_request_refresh()

    async def set_mood_brightness(self, mood_brightness) -> None:
        desired_brightness_in_range = ceil(brightness_to_value(self.mood_brightness_scale, mood_brightness))

        await self.blueair_api_device.set_mood_brightness(desired_brightness_in_range)
        await self.async_request_refresh()

    async def turn_off_mood_brightness(self) -> None:
        await self.blueair_api_device.set_mood_brightness(0)
        await self.async_request_refresh()

    async def set_germ_shield(self, enabled: bool) -> None:
        await self.blueair_api_device.set_germ_shield(enabled)
        await self.async_request_refresh()

    async def set_night_mode(self, mode) -> None:
        await self.blueair_api_device.set_night_mode(mode)
        await self.async_request_refresh()

    async def set_fan_auto_mode(self, value: bool) -> None:
        await self.blueair_api_device.set_fan_auto_mode(value)
        await self.async_request_refresh()

    async def set_wick_dry_mode(self, value) -> None:
        await self.blueair_api_device.set_wick_dry_mode(value)
        await self.async_request_refresh()

    async def set_auto_regulated_humidity(self, value) -> None:
        await self.blueair_api_device.set_auto_regulated_humidity(value)
        await self.async_request_refresh()

    async def set_main_mode(self, value: int) -> None:
        await self.blueair_api_device.set_main_mode(value)
        await self.async_request_refresh()

    async def set_heat_temp(self, value: int | float) -> None:
        if value in (None, NotImplemented):
            return
        try:
            v = float(value)
        except (TypeError, ValueError):
            return
        payload = int(round(v * 10))
        await self.blueair_api_device.set_heat_temp(payload)
        await self.async_request_refresh()

    async def set_heat_sub_mode(self, value: int) -> None:
        await self.blueair_api_device.set_heat_sub_mode(value)
        await self.async_request_refresh()

    async def set_heat_fan_speed(self, value: int) -> None:
        await self.blueair_api_device.set_heat_fan_speed(value)
        await self.async_request_refresh()

    async def set_cool_sub_mode(self, value: int) -> None:
        await self.blueair_api_device.set_cool_sub_mode(value)
        await self.async_request_refresh()

    async def set_cool_fan_speed(self, value: int) -> None:
        await self.blueair_api_device.set_cool_fan_speed(value)
        await self.async_request_refresh()

    async def set_ap_sub_mode(self, value: int) -> None:
        await self.blueair_api_device.set_ap_sub_mode(value)
        await self.async_request_refresh()

    async def set_fan_speed_0(self, value: int) -> None:
        await self.blueair_api_device.set_fan_speed_0(value)
        await self.async_request_refresh()
