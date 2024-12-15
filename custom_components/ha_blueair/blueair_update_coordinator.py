"""Blueair device object."""
from __future__ import annotations
import logging
from datetime import timedelta
from abc import ABC, abstractmethod
from asyncio import sleep

from blueair_api import Device as BlueAirApiDevice, DeviceAws as BlueAirAwsDevice

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class BlueairUpdateCoordinator(ABC, DataUpdateCoordinator):
    """Blueair device object."""

    def __init__(
        self, hass: HomeAssistant, blueair_api_device: BlueAirApiDevice | BlueAirAwsDevice
    ) -> None:
        """Initialize the device."""
        self.hass: HomeAssistant = hass
        self.blueair_api_device = blueair_api_device

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}-{self.blueair_api_device.name}",
            update_interval=timedelta(minutes=5),
            update_method=self.blueair_api_device.refresh
        )

    @property
    def id(self) -> str:
        """Return Blueair device id."""
        return self.blueair_api_device.uuid

    @property
    def device_name(self) -> str:
        """Return device name."""
        return self.blueair_api_device.name

    @property
    @abstractmethod
    def model(self) -> str:
        """Return model for device, or the UUID if it's not known."""
        pass

    @property
    def fan_speed(self) -> int:
        """Return the current fan speed."""
        return int(self.blueair_api_device.fan_speed)

    @property
    @abstractmethod
    def speed_count(self) -> int:
        """Return the max fan speed."""
        pass

    @property
    @abstractmethod
    def is_on(self) -> bool:
        pass

    @property
    def online(self) -> bool:
        return self.blueair_api_device.wifi_working

    @property
    def brightness(self) -> int:
        return self.blueair_api_device.brightness

    @property
    def child_lock(self) -> bool:
        return self.blueair_api_device.child_lock

    @property
    def night_mode(self) -> bool:
        return self.blueair_api_device.night_mode

    @property
    @abstractmethod
    def temperature(self) -> int:
        pass

    @property
    @abstractmethod
    def humidity(self) -> int:
        pass

    @property
    @abstractmethod
    def voc(self) -> int:
        pass

    @property
    @abstractmethod
    def pm1(self) -> int:
        pass

    @property
    @abstractmethod
    def pm10(self) -> int:
        pass

    @property
    @abstractmethod
    def pm25(self) -> int:
        pass

    @property
    @abstractmethod
    def co2(self) -> int:
        pass

    @property
    @abstractmethod
    def fan_auto_mode(self) -> bool | None | NotImplemented:
        pass

    @property
    @abstractmethod
    def wick_dry_mode(self) -> bool | None | NotImplemented:
        pass

    @property
    @abstractmethod
    def water_shortage(self) -> bool | None | NotImplemented:
        pass

    @property
    @abstractmethod
    def filter_expired(self) -> bool | None:
        """Return the current filter status."""
        pass

    async def set_fan_speed(self, new_speed) -> None:
        await self.blueair_api_device.set_fan_speed(new_speed)
        await sleep(5)
        await self.async_request_refresh()

    @abstractmethod
    async def set_brightness(self, brightness) -> None:
        pass

    @abstractmethod
    async def set_running(self, running) -> None:
        pass

    @abstractmethod
    async def set_child_lock(self, locked) -> None:
        pass

    @abstractmethod
    async def set_night_mode(self, mode) -> None:
        pass

    @abstractmethod
    async def set_fan_auto_mode(self, value) -> None:
        pass

    @abstractmethod
    async def set_wick_dry_mode(self, value) -> None:
        pass
