"""Blueair device object."""
import logging
from datetime import timedelta


from blueair_api import Device as BlueAirApiDevice

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class BlueairDataUpdateCoordinator(DataUpdateCoordinator):
    """Blueair device object."""

    def __init__(
        self, hass: HomeAssistant, blueair_api_device: BlueAirApiDevice
    ) -> None:
        """Initialize the device."""
        self.hass: HomeAssistant = hass
        self.blueair_api_device: BlueAirApiDevice = blueair_api_device
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
        """Return model for device, or the UUID if it's not known."""
        return self.blueair_api_device.compatibility

    @property
    def fan_speed(self) -> int:
        """Return the current fan speed."""
        return int(self.blueair_api_device.fan_speed)

    @property
    def is_on(self) -> False:
        """Return the current fan state."""
        if self.fan_speed == 0:
            return False
        return True

    @property
    def fan_mode(self) -> str:
        """Return the current fan mode."""
        return self.blueair_api_device.mode

    @property
    def brightness(self) -> int:
        return self.blueair_api_device.brightness

    async def set_brightness(self, brightness) -> None:
        raise NotImplementedError()

    @property
    def child_lock(self) -> bool:
        return self.blueair_api_device.child_lock

    @property
    def online(self) -> bool:
        return self.blueair_api_device.wifi_working

    @property
    def filter_expired(self) -> bool:
        """Return the current filter status."""
        return self.blueair_api_device.filter_expired

    async def set_fan_speed(self, new_speed) -> None:
        self.blueair_api_device.fan_speed = new_speed
        await self.blueair_api_device.set_fan_speed(new_speed)
        await self.async_refresh()
