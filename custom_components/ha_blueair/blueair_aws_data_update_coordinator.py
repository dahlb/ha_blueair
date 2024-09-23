"""Blueair device object."""
import logging
from datetime import timedelta


from blueair_api import DeviceAws as BlueAirApiDeviceAws
from asyncio import sleep
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class BlueairAwsDataUpdateCoordinator(DataUpdateCoordinator):
    """Blueair device object."""

    def __init__(
        self, hass: HomeAssistant, blueair_api_device: BlueAirApiDeviceAws
    ) -> None:
        """Initialize the device."""
        self.hass: HomeAssistant = hass
        self.blueair_api_device: BlueAirApiDeviceAws = blueair_api_device
        self._manufacturer: str = "BlueAir"

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}-{self.blueair_api_device.uuid}",
            update_interval=timedelta(minutes=10),
        )

    async def _async_update_data(self):
        """Update data via library."""
        try:
            await self.blueair_api_device.refresh()
            self.name = f"{DOMAIN}-{self.blueair_api_device.name}"
            return {}
        except Exception as error:
            raise UpdateFailed(error) from error

    @property
    def id(self) -> str:
        """Return Blueair device id."""
        return self.blueair_api_device.uuid

    @property
    def device_name(self) -> str:
        """Return device name."""
        return self.blueair_api_device.name

    @property
    def manufacturer(self) -> str:
        """Return manufacturer for device."""
        return self._manufacturer

    @property
    def model(self) -> str:
        return "protect?"

    @property
    def fan_speed(self) -> int:
        """Return the current fan speed."""
        return self.blueair_api_device.fan_speed

    @property
    def is_on(self) -> False:
        """Return the current fan state."""
        return self.blueair_api_device.running

    @property
    def fan_mode_auto(self) -> bool:
        """Return the current fan mode."""
        return self.blueair_api_device.fan_auto_mode

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
    def temperature(self) -> int:
        return self.blueair_api_device.temperature

    @property
    def humidity(self) -> int:
        return self.blueair_api_device.humidity

    @property
    def voc(self) -> int:
        return self.blueair_api_device.tVOC

    @property
    def pm1(self) -> int:
        return self.blueair_api_device.pm1

    @property
    def pm10(self) -> int:
        return self.blueair_api_device.pm10

    @property
    def pm25(self) -> int:
        return self.blueair_api_device.pm2_5

    @property
    def online(self) -> bool:
        return self.blueair_api_device.wifi_working

    @property
    def fan_auto_mode(self) -> bool:
        return self.blueair_api_device.fan_auto_mode

    @property
    def filter_expired(self) -> bool:
        """Return the current filter status."""
        return self.blueair_api_device.filter_usage >= 95

    async def set_fan_speed(self, new_speed) -> None:
        self.blueair_api_device.fan_speed = new_speed
        await self.blueair_api_device.set_fan_speed(new_speed)
        await sleep(5)
        await self.async_refresh()

    async def set_running(self, running) -> None:
        self.blueair_api_device.running = running
        await self.blueair_api_device.set_running(running)
        await sleep(5)
        await self.async_refresh()

    async def set_brightness(self, brightness) -> None:
        self.blueair_api_device.brightness = brightness
        await self.blueair_api_device.set_brightness(brightness)
        await sleep(5)
        await self.async_refresh()

    async def set_child_lock(self, locked) -> None:
        self.blueair_api_device.child_lock = locked
        await self.blueair_api_device.set_child_lock(locked)
        await sleep(5)
        await self.async_refresh()

    async def set_night_mode(self, mode) -> None:
        self.blueair_api_device.night_mode = mode
        await self.blueair_api_device.set_night_mode(mode)
        await sleep(5)
        await self.async_refresh()

    async def set_fan_auto_mode(self, value) -> None:
        self.blueair_api_device.fan_auto_mode = value
        await self.blueair_api_device.set_fan_auto_mode(value)
        await sleep(5)
        await self.async_refresh()
