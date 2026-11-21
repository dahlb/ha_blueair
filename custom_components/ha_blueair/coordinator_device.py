"""Blueair device object."""

from __future__ import annotations

import logging

from .coordinator import BlueairUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


def _cast[T](type_: type(T), value: T | NotImplemented | None) -> T:
    if value in (None, NotImplemented):
        return value
    return type_(value)


class BlueairUpdateCoordinatorDevice(BlueairUpdateCoordinator):
    """Blueair device object."""

    @property
    def model(self) -> str:
        """Return model for device."""
        return self.blueair_api_device.compatibility

    @property
    def hw_version(self) -> str:
        """Return the hardware version."""
        return self.blueair_api_device.mcu_firmware

    @property
    def sw_version(self) -> str:
        """Return the software version."""
        return self.blueair_api_device.firmware

    @property
    def serial_number(self) -> str | None:
        """Return the serial number."""
        return None

    @property
    def filter_expired(self) -> bool | NotImplemented | None:
        """Return the current filter status."""
        return self.blueair_api_device.filter_expired

    @property
    def filter_life(self) -> int | NotImplemented | None:
        """Return the filter life."""
        return NotImplemented

    @property
    def wick_life(self) -> int | NotImplemented | None:
        """Return the wick life."""
        return NotImplemented

    @property
    def fan_speed(self) -> int:
        """Return the current fan speed."""
        return _cast(int, self.blueair_api_device.fan_speed)

    @property
    def speed_count(self) -> int:
        """Return the max fan speed."""
        return 3

    @property
    def is_on(self) -> bool:
        """Return the current fan state."""
        if self.fan_speed == 0:
            return False
        return True

    @property
    def brightness(self) -> int | NotImplemented | None:
        """Return the brightness."""
        if (
            self.blueair_api_device.brightness is None
            or self.blueair_api_device.brightness is NotImplemented
        ):
            return self.blueair_api_device.brightness
        return round(self.blueair_api_device.brightness / 4 * 255.0, 0)

    @property
    def temperature(self) -> int | NotImplemented | None:
        """Return the temperature."""
        if self.model not in ["classic_280i", "classic_290i", "classic_480i", "classic_680i"]:
            return NotImplemented
        return _cast(int, self.blueair_api_device.temperature)

    @property
    def humidity(self) -> int | NotImplemented | None:
        """Return the humidity."""
        if self.model not in ["classic_280i", "classic_290i", "classic_480i", "classic_680i"]:
            return NotImplemented
        return _cast(int, self.blueair_api_device.humidity)

    @property
    def voc(self) -> int | NotImplemented | None:
        """Return the VOC level."""
        if self.model not in ["classic_280i", "classic_290i", "classic_480i", "classic_680i"]:
            return NotImplemented
        return _cast(int, self.blueair_api_device.voc)

    @property
    def pm1(self) -> int | NotImplemented | None:
        """Return the PM1 concentration."""
        if self.model not in ["classic_290i", "classic_480i", "classic_680i"]:
            return NotImplemented
        return _cast(int, self.blueair_api_device.pm1)

    @property
    def pm10(self) -> int | NotImplemented | None:
        """Return the PM10 concentration."""
        if self.model not in ["classic_290i", "classic_480i", "classic_680i"]:
            return NotImplemented
        return _cast(int, self.blueair_api_device.pm10)

    @property
    def pm25(self) -> int | NotImplemented | None:
        """Return the PM2.5 concentration."""
        if self.model not in ["classic_280i", "classic_290i", "classic_480i", "classic_680i"]:
            return NotImplemented
        return _cast(int, self.blueair_api_device.pm25)

    @property
    def co2(self) -> int | NotImplemented | None:
        """Return the CO2 level."""
        if self.model not in ["classic_280i", "classic_290i", "classic_480i", "classic_680i"]:
            return NotImplemented
        return self.blueair_api_device.co2

    @property
    def germ_shield(self) -> bool:
        """Return whether germ shield is enabled."""
        return NotImplemented

    @property
    def fan_auto_mode(self) -> bool | NotImplemented | None:
        """Return whether automatic fan mode is enabled."""
        if self.model != "classic_680i":
            return NotImplemented
        return self.blueair_api_device.fan_auto_mode

    # ----- Stubs for AWS-only sensor attributes (issue #356) -----
    # The legacy REST device does not expose these fields, but the
    # abstract base requires every subclass to declare them so that
    # entity is_implemented() checks can safely call getattr().

    @property
    def timer_duration(self) -> int | NotImplemented | None:
        """Return the timer duration."""
        return NotImplemented

    @property
    def timer_state(self) -> int | NotImplemented | None:
        """Return the timer state."""
        return NotImplemented

    @property
    def rssi(self) -> int | NotImplemented | None:
        """Return the Wi-Fi signal strength (RSSI)."""
        return NotImplemented

    @property
    def night_light_brightness(self) -> int | NotImplemented | None:
        """Return the night light brightness."""
        return NotImplemented

    @property
    def hour_format(self) -> bool | NotImplemented | None:
        """Return the clock hour format setting."""
        return NotImplemented

    @property
    def wick_dry_mode(self) -> bool | NotImplemented | None:
        """Return whether wick dry mode is enabled."""
        return NotImplemented

    @property
    def water_shortage(self) -> bool | NotImplemented | None:
        """Return whether the water tank is low."""
        return NotImplemented

    @property
    def auto_regulated_humidity(self) -> bool | NotImplemented | None:
        """Return whether automatic humidity regulation is enabled."""
        return NotImplemented

    @property
    def humidifier_mode(self) -> bool | NotImplemented | None:
        """Return the humidifier mode."""
        return NotImplemented

    @property
    def combo_mode(self) -> int | NotImplemented | None:
        """Return the combo mode."""
        return NotImplemented

    @property
    def main_mode(self) -> int | NotImplemented | None:
        """Return the main mode."""
        return NotImplemented

    @property
    def heat_temp(self) -> int | NotImplemented | None:
        """Return the heat temp."""
        return NotImplemented

    @property
    def heat_sub_mode(self) -> int | NotImplemented | None:
        """Return the heat sub mode."""
        return NotImplemented

    @property
    def heat_fan_speed(self) -> int | NotImplemented | None:
        """Return the heat fan speed."""
        return NotImplemented

    @property
    def cool_sub_mode(self) -> int | NotImplemented | None:
        """Return the cool sub mode."""
        return NotImplemented

    @property
    def cool_fan_speed(self) -> int | NotImplemented | None:
        """Return the cool fan speed."""
        return NotImplemented

    @property
    def ap_sub_mode(self) -> int | NotImplemented | None:
        """Return the air purifier sub mode."""
        return NotImplemented

    @property
    def fan_speed_0(self) -> int | NotImplemented | None:
        """Return the fan speed 0 value."""
        return NotImplemented

    @property
    def temperature_unit(self) -> int | NotImplemented | None:
        """Return the temperature unit."""
        return NotImplemented

    @property
    def water_refresher_life(self) -> int | NotImplemented | None:
        """Return the water refresher life."""
        return NotImplemented

    @property
    def water_level(self) -> int | NotImplemented | None:
        """Return the water level."""
        return NotImplemented

    @property
    def mood_brightness(self) -> int | NotImplemented | None:
        """Return the mood brightness."""
        return NotImplemented

    async def set_brightness(self, brightness: int) -> None:
        """Set the brightness."""
        # Convert Home Assistant brightness (0-255) to brightness (0-4)
        await self.blueair_api_device.set_brightness(round(brightness * 4 / 255.0))
        await self.async_request_refresh()

    async def set_mood_brightness(self, mood_brightness: int) -> None:
        """Set the mood brightness."""
        raise NotImplementedError

    async def turn_off_mood_brightness(self) -> None:
        """Turn off the mood light."""
        raise NotImplementedError

    async def set_night_light_brightness(self, night_light_brightness: int) -> None:
        """Set the night light brightness."""
        raise NotImplementedError

    async def turn_off_night_light_brightness(self) -> None:
        """Turn off the night light."""
        raise NotImplementedError

    async def set_germ_shield(self, enabled: bool) -> None:
        """Set the germ shield."""
        raise NotImplementedError

    async def set_running(self, running: bool) -> None:
        """Turn the device on or off."""
        raise NotImplementedError

    async def set_night_mode(self, mode: bool) -> None:
        """Set the night mode."""
        raise NotImplementedError

    async def set_fan_auto_mode(self, value: bool) -> None:
        """Set the fan auto mode."""
        await self.blueair_api_device.set_fan_auto_mode(value)

    async def set_wick_dry_mode(self, value: bool) -> None:
        """Set the wick dry mode."""
        raise NotImplementedError

    async def set_auto_regulated_humidity(self, value: bool) -> None:
        """Set the auto regulated humidity."""
        raise NotImplementedError

    async def set_main_mode(self, value: int) -> None:
        """Set the main mode."""
        raise NotImplementedError

    async def set_heat_temp(self, value: int) -> None:
        """Set the heat temp."""
        raise NotImplementedError

    async def set_heat_sub_mode(self, value: int) -> None:
        """Set the heat sub mode."""
        raise NotImplementedError

    async def set_heat_fan_speed(self, value: int) -> None:
        """Set the heat fan speed."""
        raise NotImplementedError

    async def set_cool_sub_mode(self, value: int) -> None:
        """Set the cool sub mode."""
        raise NotImplementedError

    async def set_cool_fan_speed(self, value: int) -> None:
        """Set the cool fan speed."""
        raise NotImplementedError

    async def set_ap_sub_mode(self, value: int) -> None:
        """Set the air purifier sub mode."""
        raise NotImplementedError

    async def set_fan_speed_0(self, value: int) -> None:
        """Set the fan speed 0 value."""
        raise NotImplementedError
