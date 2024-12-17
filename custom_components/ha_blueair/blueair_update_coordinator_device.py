"""Blueair device object."""
from __future__ import annotations
import logging
from .blueair_update_coordinator import BlueairUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class BlueairUpdateCoordinatorDevice(BlueairUpdateCoordinator):
    """Blueair device object."""
    @property
    def model(self) -> str:
        """Return model for device."""
        return self.blueair_api_device.compatibility

    @property
    def filter_expired(self) -> bool| None:
        """Return the current filter status."""
        return self.blueair_api_device.filter_expired

    @property
    def fan_speed(self) -> int:
        """Return the current fan speed."""
        return int(self.blueair_api_device.fan_speed)

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
    def temperature(self) -> int | None | NotImplemented:
        if self.model not in ["classic_280i", "classic_290i", "classic_480i", "classic_680i"]:
            return NotImplemented
        return int(self.blueair_api_device.temperature)

    @property
    def humidity(self) -> int | None | NotImplemented:
        if self.model not in ["classic_280i", "classic_290i", "classic_480i", "classic_680i"]:
            return NotImplemented
        return int(self.blueair_api_device.humidity)

    @property
    def voc(self) -> int | None | NotImplemented:
        if self.model not in ["classic_280i", "classic_290i", "classic_480i", "classic_680i"]:
            return NotImplemented
        return int(self.blueair_api_device.voc)

    @property
    def pm1(self) -> int | None | NotImplemented:
        if self.model not in ["classic_290i", "classic_480i", "classic_680i"]:
            return NotImplemented
        return int(self.blueair_api_device.pm1)

    @property
    def pm10(self) -> int | None | NotImplemented:
        if self.model not in ["classic_290i", "classic_480i", "classic_680i"]:
            return NotImplemented
        return int(self.blueair_api_device.pm10)

    @property
    def pm25(self) -> int | None | NotImplemented:
        if self.model not in ["classic_280i", "classic_290i", "classic_480i", "classic_680i"]:
            return NotImplemented
        return int(self.blueair_api_device.pm25)

    @property
    def co2(self) -> int | None | NotImplemented:
        if self.model not in ["classic_280i", "classic_290i", "classic_480i", "classic_680i"]:
            return NotImplemented
        return self.blueair_api_device.co2

    @property
    def fan_auto_mode(self) -> bool | None | NotImplemented:
        return NotImplemented

    @property
    def wick_dry_mode(self) -> bool | None | NotImplemented:
        return NotImplemented

    @property
    def water_shortage(self) -> bool | None | NotImplemented:
        return NotImplemented

    async def set_brightness(self, brightness) -> None:
        raise NotImplementedError

    async def set_running(self, running) -> None:
        raise NotImplementedError

    async def set_child_lock(self, locked) -> None:
        raise NotImplementedError

    async def set_night_mode(self, mode) -> None:
        raise NotImplementedError

    async def set_fan_auto_mode(self, value) -> None:
        raise NotImplementedError

    async def set_wick_dry_mode(self, value) -> None:
        raise NotImplementedError