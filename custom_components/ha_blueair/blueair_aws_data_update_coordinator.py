"""Blueair device object."""
import logging
from datetime import timedelta


from blueair_api import DeviceAws as BlueAirApiDeviceAws

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
            name=f"{DOMAIN}-{self.blueair_api_device.name}",
            update_interval=timedelta(minutes=10),
        )

    async def _async_update_data(self):
        """Update data via library."""
        try:
            await self.blueair_api_device.refresh()
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
    def is_on(self) -> bool():
        """Return the current fan state."""
        return self.blueair_api_device.running

    @property
    def fan_mode(self) -> str:
        """Return the current fan mode."""
        return self.blueair_api_device.fan_mode

    @property
    def brightness(self) -> int:
        return self.blueair_api_device.brightness

    @property
    def child_lock(self) -> bool:
        return self.blueair_api_device.child_lock

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
    def filter_expired(self) -> bool:
        """Return the current filter status."""
        return self.blueair_api_device.filter_usage >= 95

    async def set_fan_speed(self, new_speed) -> None:
        await self.blueair_api_device.set_fan_speed(new_speed)
        self.blueair_api_device.fan_speed = new_speed
        await self.async_refresh()

    async def set_running(self, running) -> None:
        await self.blueair_api_device.set_running(running)
        self.blueair_api_device.running = running
        await self.async_refresh()
