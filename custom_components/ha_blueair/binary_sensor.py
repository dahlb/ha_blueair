from __future__ import annotations

from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_PROBLEM,
    DEVICE_CLASS_CONNECTIVITY,
    BinarySensorEntity,
)
from homeassistant.helpers.entity import EntityDescription

from .const import DOMAIN, DATA_DEVICES, DATA_AWS_DEVICES
from .blueair_data_update_coordinator import BlueairDataUpdateCoordinator
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
                BlueairOnlineSensor(device),
            ]
        )
    async_add_entities(entities)

    aws_devices: list[BlueairDataUpdateCoordinator] = hass.data[DOMAIN][
        DATA_AWS_DEVICES
    ]
    entities = []
    for device in aws_devices:
        entities.extend(
            [
                BlueairFilterExpiredSensor(device),
                BlueairOnlineSensor(device),
            ]
        )
    async_add_entities(entities)


class BlueairChildLockSensor(BlueairEntity, BinarySensorEntity):
    _attr_icon = "mdi:account-child-outline"

    def __init__(self, device):
        super().__init__("Child Lock", device)

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self._device.child_lock


class BlueairFilterExpiredSensor(BlueairEntity, BinarySensorEntity):
    _attr_icon = "mdi:air-filter"

    def __init__(self, device):
        self.entity_description = EntityDescription(
            key=f"#{device.blueair_api_device.uuid}-filter-expired",
            device_class=DEVICE_CLASS_PROBLEM,
        )
        """Initialize the temperature sensor."""
        super().__init__("Filter Expiration", device)

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self._device.filter_expired


class BlueairOnlineSensor(BlueairEntity, BinarySensorEntity):
    _attr_icon = "mdi:wifi-check"

    def __init__(self, device):
        self.entity_description = EntityDescription(
            key=f"#{device.blueair_api_device.uuid}-online",
            device_class=DEVICE_CLASS_CONNECTIVITY,
        )
        """Initialize the temperature sensor."""
        super().__init__("Online", device)

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self._device.online

    @property
    def icon(self) -> str | None:
        if self.is_on:
            return self._attr_icon
        else:
            return "mdi:wifi-strength-outline"
