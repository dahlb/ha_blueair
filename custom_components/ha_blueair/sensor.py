# brightness
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import DEVICE_CLASS_ILLUMINANCE

from .const import DOMAIN, DATA_DEVICES
from .updater import BlueairDataUpdateCoordinator
from .entity import BlueairEntity


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Blueair sensors from config entry."""
    devices: list[BlueairDataUpdateCoordinator] = hass.data[DOMAIN][DATA_DEVICES]
    entities = []
    for device in devices:
        entities.extend(
            [
                BlueairBrightness(device),
            ]
        )
    async_add_entities(entities)


class BlueairBrightness(BlueairEntity, SensorEntity):
    _attr_device_class = DEVICE_CLASS_ILLUMINANCE
    _attr_icon = "mdi:lightbulb"

    def __init__(self, device):
        super().__init__("Brightness", device)

    @property
    def native_value(self) -> float:
        return self._device.blueair_api_device.brightness
