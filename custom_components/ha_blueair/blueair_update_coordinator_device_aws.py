"""Blueair device object."""
from __future__ import annotations
import logging

from blueair_api import ModelEnum

from .const import FILTER_EXPIRED_THRESHOLD
from .blueair_update_coordinator import BlueairUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class BlueairUpdateCoordinatorDeviceAws(BlueairUpdateCoordinator):
    """Blueair device object."""
    @property
    def model(self) -> str:
        """Return api package enum of device model."""
        return self.blueair_api_device.model.model_name

    @property
    def fan_speed(self) -> int | None | NotImplemented:
        """Return the current fan speed."""
        return self.blueair_api_device.fan_speed

    @property
    def speed_count(self) -> int:
        """Return the max fan speed."""
        if self.blueair_api_device.model == ModelEnum.HUMIDIFIER_H35I:
            return 64
        elif self.blueair_api_device.model in [
            ModelEnum.MAX_211I,
            ModelEnum.MAX_311I,
            ModelEnum.PROTECT_7440I,
            ModelEnum.PROTECT_7470I
        ]:
            return 91
        elif self.blueair_api_device.model == ModelEnum.T10I:
            return 4
        else:
            return 100

    @property
    def is_on(self) -> bool | None | NotImplemented:
        """Return the current fan state."""
        if self.blueair_api_device.standby is None or self.blueair_api_device.standby is NotImplemented:
            return self.blueair_api_device.standby
        else:
            return not self.blueair_api_device.standby

    @property
    def brightness(self) -> int | None | NotImplemented:
        return self.blueair_api_device.brightness

    @property
    def child_lock(self) -> bool | None | NotImplemented:
        return self.blueair_api_device.child_lock

    @property
    def night_mode(self) -> bool | None | NotImplemented:
        return self.blueair_api_device.night_mode

    @property
    def temperature(self) -> int | None | NotImplemented:
        return self.blueair_api_device.temperature

    @property
    def humidity(self) -> int | None | NotImplemented:
        return self.blueair_api_device.humidity

    @property
    def target_humidity(self) -> int | None | NotImplemented:
        return (
            self.blueair_api_device.auto_regulated_humidity
        )  # TODO: Expose in API properly / make consistent with other properties

    @property
    def voc(self) -> int | None | NotImplemented:
        return self.blueair_api_device.tVOC

    @property
    def pm1(self) -> int | None | NotImplemented:
        return self.blueair_api_device.pm1

    @property
    def pm10(self) -> int | None | NotImplemented:
        return self.blueair_api_device.pm10

    @property
    def pm25(self) -> int | None | NotImplemented:
        # pm25 is the more common name for pm2.5.
        return self.blueair_api_device.pm2_5

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
    def filter_expired(self) -> bool | None:
        """Returns the current filter status."""
        if self.blueair_api_device.filter_usage_percentage not in (NotImplemented, None):
                return (self.blueair_api_device.filter_usage_percentage >=
                        FILTER_EXPIRED_THRESHOLD)
        if self.blueair_api_device.wick_usage_percentage not in (NotImplemented, None):
                return (self.blueair_api_device.wick_usage_percentage >=
                        FILTER_EXPIRED_THRESHOLD)

    async def set_running(self, running) -> None:
        await self.blueair_api_device.set_running(running)
        await self.async_request_refresh()

    async def set_brightness(self, brightness) -> None:
        await self.blueair_api_device.set_brightness(brightness)
        await self.async_request_refresh()

    async def set_child_lock(self, locked) -> None:
        await self.blueair_api_device.set_child_lock(locked)
        await self.async_request_refresh()

    async def set_night_mode(self, mode) -> None:
        await self.blueair_api_device.set_night_mode(mode)
        await self.async_request_refresh()

    async def set_fan_auto_mode(self, value) -> None:
        await self.blueair_api_device.set_fan_auto_mode(value)
        await self.async_request_refresh()

    async def set_wick_dry_mode(self, value) -> None:
        await self.blueair_api_device.set_wick_dry_mode(value)
        await self.async_request_refresh()

    async def set_auto_regulated_humidity(self, value) -> None:
        await self.blueair_api_device.set_auto_regulated_humidity(value)
        await self.async_request_refresh()
