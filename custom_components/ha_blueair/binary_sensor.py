from __future__ import annotations

from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_PROBLEM,
    BinarySensorEntity,
)
from homeassistant.helpers.entity import EntityDescription

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
                BlueairChildLockSensor(device),
                BlueairFilterExpiredSensor(device),
            ]
        )
    async_add_entities(entities)


class BlueairChildLockSensor(BlueairEntity, BinarySensorEntity):
    _attr_icon = "mdi:account-child-outline"

    def __init__(self, device):
        """Initialize the temperature sensor."""
        super().__init__("Child Lock", device)

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self._device.blueair_api_device.child_lock


class BlueairFilterExpiredSensor(BlueairEntity, BinarySensorEntity):
    _attr_icon = "mdi:air-filter"

    def __init__(self, device):
        self.entity_description = EntityDescription(
            key=f"#{device.blueair_api_device.uuid}-filter-expired",
            device_class = DEVICE_CLASS_PROBLEM,
        )
        """Initialize the temperature sensor."""
        super().__init__("Filter Expiration", device)

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self._device.blueair_api_device.filter_expired
