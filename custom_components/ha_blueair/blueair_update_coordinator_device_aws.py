"""Blueair device object."""

from __future__ import annotations

import logging
from math import ceil

from blueair_api import DeviceAws
from homeassistant.util.color import brightness_to_value, value_to_brightness

from .blueair_update_coordinator import BlueairUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class BlueairUpdateCoordinatorDeviceAws(BlueairUpdateCoordinator):
    """Blueair device object."""

    blueair_api_device: DeviceAws

    @property
    def model(self) -> str:
        """Return human-readable product name for device registry."""
        return self.blueair_api_device.model_name

    @property
    def hw_version(self) -> str:
        """Return the hardware version."""
        return self.blueair_api_device.mcu_firmware

    @property
    def sw_version(self) -> str:
        """Return the software version."""
        return self.blueair_api_device.firmware

    @property
    def overall_firmware(self) -> str | NotImplemented | None:
        """Overall firmware version (AWS shadow field ``ofv``).

        Distinct from ``sw_version`` (Wi-Fi firmware) and ``hw_version``
        (MCU firmware); surfaced as a diagnostic sensor since the device
        registry only has the two version slots.
        """
        return self.blueair_api_device.overall_firmware

    @property
    def serial_number(self) -> str:
        """Return the serial number."""
        return self.blueair_api_device.serial_number

    @property
    def fan_speed(self) -> int | NotImplemented | None:
        """Return the current fan speed."""
        return self.blueair_api_device.fan_speed

    @property
    def speed_count(self) -> int:
        """Return the max fan speed."""
        return self.blueair_api_device.fan_speed_count

    @property
    def is_on(self) -> bool | NotImplemented | None:
        """Return the current fan state."""
        if (
            self.blueair_api_device.standby is None
            or self.blueair_api_device.standby is NotImplemented
        ):
            return self.blueair_api_device.standby
        return not self.blueair_api_device.standby

    @property
    def brightness(self) -> int | NotImplemented | None:
        """Return the brightness of this light between 0..255."""
        if (
            self.blueair_api_device.brightness is None
            or self.blueair_api_device.brightness is NotImplemented
        ):
            return self.blueair_api_device.brightness
        return round(self.blueair_api_device.brightness / 100 * 255.0, 0)

    @property
    def germ_shield(self) -> bool | NotImplemented | None:
        """Return whether germ shield is enabled."""
        return self.blueair_api_device.germ_shield

    @property
    def child_lock(self) -> bool | NotImplemented | None:
        """Return whether the child lock is enabled."""
        return self.blueair_api_device.child_lock

    @property
    def night_mode(self) -> bool | NotImplemented | None:
        """Return whether night mode is enabled."""
        return self.blueair_api_device.night_mode

    @property
    def temperature(self) -> float | NotImplemented | None:
        """Return the temperature."""
        raw = self.blueair_api_device.temperature
        if raw in (None, NotImplemented):
            return raw
        try:
            return float(raw)
        except TypeError, ValueError:
            return raw

    @property
    def humidity(self) -> int | NotImplemented | None:
        """Return the humidity."""
        return self.blueair_api_device.humidity

    @property
    def auto_regulated_humidity(self) -> int | NotImplemented | None:
        """Return whether automatic humidity regulation is enabled."""
        return self.blueair_api_device.auto_regulated_humidity

    @property
    def humidifier_mode(self) -> bool | NotImplemented | None:
        """Humidification on/off for 2-in-1 combo devices (e.g. DH3i).

        Independent of the purifier running state (standby), so toggling
        humidification does not power down the fan.
        """
        return self.blueair_api_device.humidifier_mode

    @property
    def combo_mode(self) -> int | NotImplemented | None:
        """Operating mode for 2-in-1 combo devices (e.g. DH3i).

        Values follow the device firmware's mode enum: 1=Manual, 2=Auto,
        3=Night. Used to surface fan presets on the combo fan entity.
        """
        return self.blueair_api_device.combo_mode

    @property
    def voc(self) -> int | NotImplemented | None:
        """Return the VOC level."""
        if self.blueair_api_device.total_voc is NotImplemented:
            return self.blueair_api_device.voc
        return self.blueair_api_device.total_voc

    @property
    def pm1(self) -> int | NotImplemented | None:
        """Return the PM1 concentration."""
        return self.blueair_api_device.pm1

    @property
    def pm10(self) -> int | NotImplemented | None:
        """Return the PM10 concentration."""
        return self.blueair_api_device.pm10

    @property
    def pm25(self) -> int | NotImplemented | None:
        """Return the PM2.5 concentration."""
        # pm25 is the more common name for pm2.5.
        return self.blueair_api_device.pm2_5

    @property
    def co2(self) -> int | NotImplemented | None:
        """Return the CO2 level."""
        return NotImplemented

    @property
    def fan_auto_mode(self) -> bool | NotImplemented | None:
        """Return whether automatic fan mode is enabled."""
        return self.blueair_api_device.fan_auto_mode

    @property
    def wick_dry_mode(self) -> bool | NotImplemented | None:
        """Return whether wick dry mode is enabled."""
        return self.blueair_api_device.wick_dry_mode

    @property
    def water_shortage(self) -> bool | NotImplemented | None:
        """Return whether the water tank is low."""
        return self.blueair_api_device.water_shortage

    @property
    def filter_expired(self) -> bool | NotImplemented | None:
        """Return whether the filter has expired."""
        return NotImplemented

    @property
    def filter_life(self) -> int | NotImplemented | None:
        """Return the filter life."""
        if self.blueair_api_device.filter_usage_percentage in (NotImplemented, None):
            return self.blueair_api_device.filter_usage_percentage
        return 100 - self.blueair_api_device.filter_usage_percentage

    @property
    def wick_life(self) -> int | NotImplemented | None:
        """Return the wick life."""
        if self.blueair_api_device.wick_usage_percentage in (NotImplemented, None):
            return self.blueair_api_device.wick_usage_percentage
        return 100 - self.blueair_api_device.wick_usage_percentage

    @property
    def water_refresher_life(self) -> int | NotImplemented | None:
        """Return the water refresher life."""
        if self.blueair_api_device.water_refresher_usage_percentage in (NotImplemented, None):
            return self.blueair_api_device.water_refresher_usage_percentage
        return 100 - self.blueair_api_device.water_refresher_usage_percentage

    @property
    def water_level(self) -> int | NotImplemented | None:
        """Return the water level."""
        return self.blueair_api_device.water_level

    @property
    def mood_brightness_scale(self) -> tuple[int, int]:
        """Return the mood light brightness scale."""
        return (1, self.blueair_api_device.mood_brightness_max)

    @property
    def mood_brightness(self) -> int | NotImplemented | None:
        """Return the mood brightness."""
        if self.blueair_api_device.mood_brightness not in (None, NotImplemented):
            return value_to_brightness(
                self.mood_brightness_scale, self.blueair_api_device.mood_brightness
            )
        return self.blueair_api_device.mood_brightness

    @property
    def mood_brightness_is_on(self) -> int | NotImplemented | None:
        """Return whether the mood light is on."""
        return self.blueair_api_device.mood_brightness != 0

    @property
    def main_mode(self) -> int | NotImplemented | None:
        """Return the main mode."""
        return self.blueair_api_device.main_mode

    @property
    def heat_temp(self) -> float | NotImplemented | None:
        """Return the heat temp."""
        raw = self.blueair_api_device.heat_temp
        if raw in (None, NotImplemented):
            return raw
        try:
            return float(raw) / 10.0
        except TypeError, ValueError:
            return raw

    @property
    def heat_sub_mode(self) -> int | NotImplemented | None:
        """Return the heat sub mode."""
        return self.blueair_api_device.heat_sub_mode

    @property
    def heat_fan_speed(self) -> int | NotImplemented | None:
        """Return the heat fan speed."""
        return self.blueair_api_device.heat_fan_speed

    @property
    def cool_sub_mode(self) -> int | NotImplemented | None:
        """Return the cool sub mode."""
        return self.blueair_api_device.cool_sub_mode

    @property
    def cool_fan_speed(self) -> int | NotImplemented | None:
        """Return the cool fan speed."""
        return self.blueair_api_device.cool_fan_speed

    @property
    def ap_sub_mode(self) -> int | NotImplemented | None:
        """Return the air purifier sub mode."""
        return self.blueair_api_device.ap_sub_mode

    @property
    def fan_speed_0(self) -> int | NotImplemented | None:
        """Return the fan speed 0 value."""
        return self.blueair_api_device.fan_speed_0

    @property
    def temperature_unit(self) -> int | NotImplemented | None:
        """Return the temperature unit."""
        raw = self.blueair_api_device.temperature_unit
        if raw in (None, NotImplemented):
            return raw
        try:
            return int(raw)
        except TypeError, ValueError:
            return raw

    @property
    def rssi(self) -> int | NotImplemented | None:
        """Return the Wi-Fi signal strength (RSSI)."""
        return self.blueair_api_device.rssi

    @property
    def night_light_brightness_scale(self) -> tuple[int, int]:
        """Return the night light brightness scale."""
        return (1, 100)

    @property
    def night_light_brightness(self) -> int | NotImplemented | None:
        """Return the night light brightness."""
        if self.blueair_api_device.night_light_brightness not in (None, NotImplemented):
            return value_to_brightness(
                self.night_light_brightness_scale,
                self.blueair_api_device.night_light_brightness,
            )
        return self.blueair_api_device.night_light_brightness

    @property
    def night_light_brightness_is_on(self) -> bool | NotImplemented | None:
        """Return whether the night light is on."""
        return self.blueair_api_device.night_light_brightness != 0

    @property
    def timer_state(self) -> int | NotImplemented | None:
        """Return the timer state."""
        return self.blueair_api_device.timer_state

    @property
    def timer_duration(self) -> int | NotImplemented | None:
        """Return the timer duration."""
        return self.blueair_api_device.timer_duration

    @property
    def hour_format(self) -> bool | NotImplemented | None:
        """Return the clock hour format setting."""
        return self.blueair_api_device.hour_format

    async def set_running(self, running: bool) -> None:
        """Turn the device on or off."""
        await self.blueair_api_device.set_standby(not running)
        await self.async_request_refresh()

    async def set_brightness(self, brightness: int) -> None:
        """Set the brightness."""
        # Convert Home Assistant brightness (0-255) to Abode brightness (0-99)
        # If 100 is sent to Abode, response is 99 causing an error
        await self.blueair_api_device.set_brightness(round(brightness * 100 / 255.0))
        await self.async_request_refresh()

    async def set_mood_brightness(self, mood_brightness: int) -> None:
        """Set the mood brightness."""
        desired_brightness_in_range = ceil(
            brightness_to_value(self.mood_brightness_scale, mood_brightness)
        )

        await self.blueair_api_device.set_mood_brightness(desired_brightness_in_range)
        await self.async_request_refresh()

    async def turn_off_mood_brightness(self) -> None:
        """Turn off the mood light."""
        await self.blueair_api_device.set_mood_brightness(0)
        await self.async_request_refresh()

    async def set_germ_shield(self, enabled: bool) -> None:
        """Set the germ shield."""
        await self.blueair_api_device.set_germ_shield(enabled)
        await self.async_request_refresh()

    async def set_night_mode(self, mode: bool) -> None:
        """Set the night mode."""
        await self.blueair_api_device.set_night_mode(mode)
        await self.async_request_refresh()

    async def set_fan_auto_mode(self, value: bool) -> None:
        """Set the fan auto mode."""
        await self.blueair_api_device.set_fan_auto_mode(value)
        await self.async_request_refresh()

    async def set_wick_dry_mode(self, value: bool) -> None:
        """Set the wick dry mode."""
        await self.blueair_api_device.set_wick_dry_mode(value)
        await self.async_request_refresh()

    async def set_auto_regulated_humidity(self, value: bool) -> None:
        """Set the auto regulated humidity."""
        await self.blueair_api_device.set_auto_regulated_humidity(value)
        await self.async_request_refresh()

    async def set_humidifier_mode(self, value: bool) -> None:
        """Set the humidifier mode."""
        await self.blueair_api_device.set_humidifier_mode(value)
        await self.async_request_refresh()

    async def set_combo_mode(self, value: int) -> None:
        """Set the combo mode."""
        await self.blueair_api_device.set_combo_mode(value)
        await self.async_request_refresh()

    async def set_main_mode(self, value: int) -> None:
        """Set the main mode."""
        await self.blueair_api_device.set_main_mode(value)
        await self.async_request_refresh()

    async def set_heat_temp(self, value: float) -> None:
        """Set the heat temp."""
        if value in (None, NotImplemented):
            return
        try:
            v = float(value)
        except TypeError, ValueError:
            return
        payload = round(v * 10)
        await self.blueair_api_device.set_heat_temp(payload)
        await self.async_request_refresh()

    async def set_heat_sub_mode(self, value: int) -> None:
        """Set the heat sub mode."""
        await self.blueair_api_device.set_heat_sub_mode(value)
        await self.async_request_refresh()

    async def set_heat_fan_speed(self, value: int) -> None:
        """Set the heat fan speed."""
        await self.blueair_api_device.set_heat_fan_speed(value)
        await self.async_request_refresh()

    async def set_cool_sub_mode(self, value: int) -> None:
        """Set the cool sub mode."""
        await self.blueair_api_device.set_cool_sub_mode(value)
        await self.async_request_refresh()

    async def set_cool_fan_speed(self, value: int) -> None:
        """Set the cool fan speed."""
        await self.blueair_api_device.set_cool_fan_speed(value)
        await self.async_request_refresh()

    async def set_ap_sub_mode(self, value: int) -> None:
        """Set the air purifier sub mode."""
        await self.blueair_api_device.set_ap_sub_mode(value)
        await self.async_request_refresh()

    async def set_fan_speed_0(self, value: int) -> None:
        """Set the fan speed 0 value."""
        await self.blueair_api_device.set_fan_speed_0(value)
        await self.async_request_refresh()

    async def set_night_light_brightness(self, night_light_brightness: int) -> None:
        """Set the night light brightness."""
        desired_brightness_in_range = ceil(
            brightness_to_value(self.night_light_brightness_scale, night_light_brightness)
        )
        await self.blueair_api_device.set_night_light_brightness(desired_brightness_in_range)
        await self.async_request_refresh()

    async def turn_off_night_light_brightness(self) -> None:
        """Turn off the night light."""
        await self.blueair_api_device.set_night_light_brightness(0)
        await self.async_request_refresh()

    async def set_timer_duration(self, value: int) -> None:
        """Set the timer duration."""
        await self.blueair_api_device.set_timer_duration(value)
        await self.async_request_refresh()

    async def set_hour_format(self, value: bool) -> None:
        """Set the hour format."""
        await self.blueair_api_device.set_hour_format(value)
        await self.async_request_refresh()
