"""Blueair device object."""
from __future__ import annotations
import logging

from .blueair_update_coordinator import BlueairUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

def _cast[T](type_: type(T), value: T | None | NotImplemented) -> T:
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
        return self.blueair_api_device.mcu_firmware

    @property
    def sw_version(self) -> str:
        return self.blueair_api_device.firmware

    @property
    def serial_number(self) -> str | None:
        return None

    @property
    def filter_expired(self) -> bool | None | NotImplemented:
        """Return the current filter status."""
        return self.blueair_api_device.filter_expired

    @property
    def filter_life(self) -> int | None | NotImplemented:
        return NotImplemented

    @property
    def wick_life(self) -> int | None | NotImplemented:
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
    def brightness(self) -> int | None | NotImplemented:
        if self.blueair_api_device.brightness is None or self.blueair_api_device.brightness is NotImplemented:
            return self.blueair_api_device.brightness
        else:
            return round(self.blueair_api_device.brightness / 4 * 255.0, 0)

    @property
    def temperature(self) -> int | None | NotImplemented:
        if self.model not in ["classic_280i", "classic_290i", "classic_480i", "classic_680i"]:
            return NotImplemented
        return _cast(int, self.blueair_api_device.temperature)

    @property
    def humidity(self) -> int | None | NotImplemented:
        if self.model not in ["classic_280i", "classic_290i", "classic_480i", "classic_680i"]:
            return NotImplemented
        return _cast(int, self.blueair_api_device.humidity)

    @property
    def voc(self) -> int | None | NotImplemented:
        if self.model not in ["classic_280i", "classic_290i", "classic_480i", "classic_680i"]:
            return NotImplemented
        return _cast(int, self.blueair_api_device.voc)

    @property
    def pm1(self) -> int | None | NotImplemented:
        if self.model not in ["classic_290i", "classic_480i", "classic_680i"]:
            return NotImplemented
        return _cast(int, self.blueair_api_device.pm1)

    @property
    def pm10(self) -> int | None | NotImplemented:
        if self.model not in ["classic_290i", "classic_480i", "classic_680i"]:
            return NotImplemented
        return _cast(int, self.blueair_api_device.pm10)

    @property
    def pm25(self) -> int | None | NotImplemented:
        if self.model not in ["classic_280i", "classic_290i", "classic_480i", "classic_680i"]:
            return NotImplemented
        return _cast(int, self.blueair_api_device.pm25)

    @property
    def co2(self) -> int | None | NotImplemented:
        if self.model not in ["classic_280i", "classic_290i", "classic_480i", "classic_680i"]:
            return NotImplemented
        return self.blueair_api_device.co2

    @property
    def germ_shield(self) -> bool:
        return NotImplemented

    @property
    def fan_auto_mode(self) -> bool | None | NotImplemented:
        if self.model not in ["classic_680i"]:
            return NotImplemented
        return self.blueair_api_device.fan_auto_mode

    @property
    def wick_dry_mode(self) -> bool | None | NotImplemented:
        return NotImplemented

    @property
    def water_shortage(self) -> bool | None | NotImplemented:
        return NotImplemented

    @property
    def auto_regulated_humidity(self) -> bool | None | NotImplemented:
        return NotImplemented

    @property
    def main_mode(self) -> int | None | NotImplemented:
        return NotImplemented

    @property
    def heat_temp(self) -> int | None | NotImplemented:
        return NotImplemented

    @property
    def heat_sub_mode(self) -> int | None | NotImplemented:
        return NotImplemented

    @property
    def heat_fan_speed(self) -> int | None | NotImplemented:
        return NotImplemented

    @property
    def cool_sub_mode(self) -> int | None | NotImplemented:
        return NotImplemented

    @property
    def cool_fan_speed(self) -> int | None | NotImplemented:
        return NotImplemented

    @property
    def ap_sub_mode(self) -> int | None | NotImplemented:
        return NotImplemented

    @property
    def fan_speed_0(self) -> int | None | NotImplemented:
        return NotImplemented

    @property
    def temperature_unit(self) -> int | None | NotImplemented:
        return NotImplemented

    @property
    def water_refresher_life(self) -> int | None | NotImplemented:
        return NotImplemented

    @property
    def water_level(self) -> int | None | NotImplemented:
        return NotImplemented

    @property
    def mood_brightness(self) -> int | None | NotImplemented:
        return NotImplemented

    async def set_brightness(self, brightness) -> None:
        # Convert Home Assistant brightness (0-255) to brightness (0-4)
        await self.blueair_api_device.set_brightness(round(brightness * 4 / 255.0))
        await self.async_request_refresh()

    async def set_mood_brightness(self, mood_brightness: int) -> None:
        raise NotImplementedError

    async def turn_off_mood_brightness(self) -> None:
        raise NotImplementedError

    async def set_germ_shield(self, enabled: bool) -> None:
        raise NotImplementedError

    async def set_running(self, running) -> None:
        raise NotImplementedError

    async def set_night_mode(self, mode) -> None:
        raise NotImplementedError

    async def set_fan_auto_mode(self, value: bool) -> None:
        await self.blueair_api_device.set_fan_auto_mode(value)

    async def set_wick_dry_mode(self, value) -> None:
        raise NotImplementedError

    async def set_auto_regulated_humidity(self, value) -> None:
        raise NotImplementedError

    async def set_main_mode(self, value: int) -> None:
        raise NotImplementedError

    async def set_heat_temp(self, value: int) -> None:
        raise NotImplementedError

    async def set_heat_sub_mode(self, value: int) -> None:
        raise NotImplementedError

    async def set_heat_fan_speed(self, value: int) -> None:
        raise NotImplementedError

    async def set_cool_sub_mode(self, value: int) -> None:
        raise NotImplementedError

    async def set_cool_fan_speed(self, value: int) -> None:
        raise NotImplementedError

    async def set_ap_sub_mode(self, value: int) -> None:
        raise NotImplementedError

    async def set_fan_speed_0(self, value: int) -> None:
        raise NotImplementedError
