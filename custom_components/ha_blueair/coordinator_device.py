"""Blueair device object."""

from __future__ import annotations

import logging
from types import NotImplementedType

from blueair_api import Device

from .coordinator import BlueairUpdateCoordinator, Capability

_LOGGER = logging.getLogger(__name__)


def _as_int(value: Capability[float]) -> Capability[int]:
    """Return a reported number as an int, keeping None and NotImplemented."""
    if value is None or value is NotImplemented:
        return value
    return int(value)


class BlueairUpdateCoordinatorDevice(BlueairUpdateCoordinator):
    """Blueair device object."""

    blueair_api_device: Device

    @property
    def model(self) -> str | None:
        """Return model for device."""
        return self.blueair_api_device.compatibility

    @property
    def hw_version(self) -> str | None:
        """Return the hardware version."""
        return self.blueair_api_device.mcu_firmware

    @property
    def sw_version(self) -> str | None:
        """Return the software version."""
        return self.blueair_api_device.firmware

    @property
    def serial_number(self) -> str | None:
        """Return the serial number."""
        return None

    @property
    def filter_expired(self) -> Capability[bool]:
        """Return the current filter status."""
        return self.blueair_api_device.filter_expired

    @property
    def filter_life(self) -> Capability[int]:
        """Return the filter life."""
        return NotImplemented

    @property
    def wick_life(self) -> Capability[int]:
        """Return the wick life."""
        return NotImplemented

    @property
    def fan_speed(self) -> Capability[int]:
        """Return the current fan speed."""
        return _as_int(self.blueair_api_device.fan_speed)

    @property
    def speed_count(self) -> int:
        """Return the max fan speed."""
        return 3

    @property
    def online(self) -> Capability[bool]:
        """Return whether the device is online.

        Sense+ can report wifi_working=False while refreshes and commands
        still succeed, so it counts as online whenever it reports a usable
        legacy fan state instead.
        """
        if self.model == "sense+":
            return str(self.blueair_api_device.fan_speed) in ("0", "1", "2", "3")
        return super().online

    @property
    def is_on(self) -> bool:
        """Return the current fan state."""
        if self.fan_speed == 0:
            return False
        return True

    @property
    def brightness(self) -> Capability[int]:
        """Return the brightness."""
        if (
            self.blueair_api_device.brightness is None
            or self.blueair_api_device.brightness is NotImplemented
        ):
            return self.blueair_api_device.brightness
        return round(self.blueair_api_device.brightness / 4 * 255)

    @property
    def temperature(self) -> Capability[int]:
        """Return the temperature."""
        if self.model not in ["classic_280i", "classic_290i", "classic_480i", "classic_680i"]:
            return NotImplemented
        return _as_int(self.blueair_api_device.temperature)

    @property
    def humidity(self) -> Capability[int]:
        """Return the humidity."""
        if self.model not in ["classic_280i", "classic_290i", "classic_480i", "classic_680i"]:
            return NotImplemented
        return _as_int(self.blueair_api_device.humidity)

    @property
    def voc(self) -> Capability[int]:
        """Return the VOC level."""
        if self.model not in ["classic_280i", "classic_290i", "classic_480i", "classic_680i"]:
            return NotImplemented
        return _as_int(self.blueair_api_device.voc)

    @property
    def pm1(self) -> Capability[int]:
        """Return the PM1 concentration."""
        if self.model not in ["classic_290i", "classic_480i", "classic_680i"]:
            return NotImplemented
        return _as_int(self.blueair_api_device.pm1)

    @property
    def pm10(self) -> Capability[int]:
        """Return the PM10 concentration."""
        if self.model not in ["classic_290i", "classic_480i", "classic_680i"]:
            return NotImplemented
        return _as_int(self.blueair_api_device.pm10)

    @property
    def pm25(self) -> Capability[int]:
        """Return the PM2.5 concentration."""
        if self.model not in ["classic_280i", "classic_290i", "classic_480i", "classic_680i"]:
            return NotImplemented
        return _as_int(self.blueair_api_device.pm25)

    @property
    def co2(self) -> Capability[int]:
        """Return the CO2 level."""
        if self.model not in ["classic_280i", "classic_290i", "classic_480i", "classic_680i"]:
            return NotImplemented
        return self.blueair_api_device.co2

    @property
    def germ_shield(self) -> Capability[bool]:
        """Return whether germ shield is enabled."""
        return NotImplemented

    @property
    def fan_auto_mode(self) -> Capability[bool]:
        """Return whether automatic fan mode is enabled."""
        if self.model != "classic_680i":
            return NotImplemented
        return self.blueair_api_device.fan_auto_mode

    @property
    def night_mode(self) -> NotImplementedType:
        """Return NotImplemented: the legacy API cannot set night mode.

        Reporting the device's night_mode here made the fan offer a Night preset
        whose set_night_mode raised NotImplementedError on every use.
        """
        return NotImplemented

    # ----- Stubs for AWS-only sensor attributes (issue #356) -----
    # The legacy REST device does not expose these fields, but the
    # abstract base requires every subclass to declare them so that
    # entity is_implemented() checks can safely call getattr().

    @property
    def timer_duration(self) -> Capability[int]:
        """Return the timer duration."""
        return NotImplemented

    @property
    def timer_state(self) -> Capability[int]:
        """Return the timer state."""
        return NotImplemented

    @property
    def rssi(self) -> Capability[int]:
        """Return the Wi-Fi signal strength (RSSI)."""
        return NotImplemented

    @property
    def night_light_brightness(self) -> Capability[int]:
        """Return the night light brightness."""
        return NotImplemented

    @property
    def hour_format(self) -> Capability[bool]:
        """Return the clock hour format setting."""
        return NotImplemented

    @property
    def wick_dry_mode(self) -> Capability[bool]:
        """Return whether wick dry mode is enabled."""
        return NotImplemented

    @property
    def water_shortage(self) -> Capability[bool]:
        """Return whether the water tank is low."""
        return NotImplemented

    @property
    def auto_regulated_humidity(self) -> Capability[int]:
        """Return the target humidity the device regulates to, in percent."""
        return NotImplemented

    @property
    def humidifier_mode(self) -> Capability[bool]:
        """Return the humidifier mode."""
        return NotImplemented

    @property
    def combo_mode(self) -> Capability[int]:
        """Return the combo mode."""
        return NotImplemented

    @property
    def main_mode(self) -> Capability[int]:
        """Return the main mode."""
        return NotImplemented

    @property
    def heat_temp(self) -> Capability[float]:
        """Return the heat temp."""
        return NotImplemented

    @property
    def heat_sub_mode(self) -> Capability[int]:
        """Return the heat sub mode."""
        return NotImplemented

    @property
    def heat_fan_speed(self) -> Capability[int]:
        """Return the heat fan speed."""
        return NotImplemented

    @property
    def cool_sub_mode(self) -> Capability[int]:
        """Return the cool sub mode."""
        return NotImplemented

    @property
    def cool_fan_speed(self) -> Capability[int]:
        """Return the cool fan speed."""
        return NotImplemented

    @property
    def ap_sub_mode(self) -> Capability[int]:
        """Return the air purifier sub mode."""
        return NotImplemented

    @property
    def fan_speed_0(self) -> Capability[int]:
        """Return the fan speed 0 value."""
        return NotImplemented

    @property
    def temperature_unit(self) -> Capability[int]:
        """Return the temperature unit."""
        return NotImplemented

    @property
    def water_refresher_life(self) -> Capability[int]:
        """Return the water refresher life."""
        return NotImplemented

    @property
    def water_level(self) -> Capability[int]:
        """Return the water level."""
        return NotImplemented

    @property
    def mood_brightness(self) -> Capability[int]:
        """Return the mood brightness."""
        return NotImplemented

    async def set_brightness(self, brightness: int) -> None:
        """Set the brightness."""
        # Convert Home Assistant brightness (0-255) to brightness (0-4)
        await self._async_device_command(
            self.blueair_api_device.set_brightness(round(brightness * 4 / 255.0))
        )
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

    async def set_fan_speed(self, new_speed: int) -> None:
        """Set the fan speed (0-3)."""
        # The legacy API takes the speed as a string.
        await self._async_device_command(self.blueair_api_device.set_fan_speed(str(new_speed)))
        await self.async_request_refresh()

    async def set_fan_auto_mode(self, value: bool) -> None:
        """Set the fan auto mode."""
        await self._async_device_command(self.blueair_api_device.set_fan_auto_mode(value))

    async def set_wick_dry_mode(self, value: bool) -> None:
        """Set the wick dry mode."""
        raise NotImplementedError

    async def set_auto_regulated_humidity(self, value: int) -> None:
        """Set the target humidity, in percent."""
        raise NotImplementedError

    async def set_main_mode(self, value: int) -> None:
        """Set the main mode."""
        raise NotImplementedError

    async def set_heat_temp(self, value: float) -> None:
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
