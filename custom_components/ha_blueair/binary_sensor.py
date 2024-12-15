from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers.entity import EntityDescription

from .entity import BlueairEntity, async_setup_entry_helper


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Blueair sensors from config entry."""
    async_setup_entry_helper(hass, config_entry, async_add_entities,
        entity_classes=[
            BlueairOnlineSensor,
            BlueairFilterExpiredSensor,
            BlueairChildLockSensor,
            BlueairWaterShortageSensor,
    ])



class BlueairChildLockSensor(BlueairEntity, BinarySensorEntity):
    _attr_icon = "mdi:account-child-outline"

    @classmethod
    def is_implemented(kls, coordinator):
        return coordinator.child_lock is not NotImplemented

    def __init__(self, coordinator):
        super().__init__("Child Lock", coordinator)

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self.coordinator.child_lock


class BlueairFilterExpiredSensor(BlueairEntity, BinarySensorEntity):
    _attr_icon = "mdi:air-filter"

    @classmethod
    def is_implemented(kls, coordinator):
        return coordinator.filter_expired is not NotImplemented

    def __init__(self, coordinator):
        """Initialize the temperature sensor."""
        self.entity_description = EntityDescription(
            key=f"#{coordinator.blueair_api_device.uuid}-filter-expired",
            device_class=BinarySensorDeviceClass.PROBLEM,
        )
        super().__init__("Filter Expiration", coordinator)

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self.coordinator.filter_expired


class BlueairOnlineSensor(BlueairEntity, BinarySensorEntity):
    _attr_icon = "mdi:wifi-check"

    @classmethod
    def is_implemented(kls, coordinator):
        return coordinator.online is not NotImplemented

    def __init__(self, coordinator):
        """Initialize the temperature sensor."""
        self.entity_description = EntityDescription(
            key=f"#{coordinator.blueair_api_device.uuid}-online",
            device_class=BinarySensorDeviceClass.CONNECTIVITY,
        )
        super().__init__("Online", coordinator)

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self.coordinator.online

    @property
    def icon(self) -> str | None:
        if self.is_on:
            return self._attr_icon
        else:
            return "mdi:wifi-strength-outline"


class BlueairWaterShortageSensor(BlueairEntity, BinarySensorEntity):
    _attr_icon = "mdi:water-alert-outline"

    @classmethod
    def is_implemented(kls, coordinator):
        return coordinator.water_shortage is not NotImplemented

    def __init__(self, coordinator):
        self.entity_description = EntityDescription(
            key=f"#{coordinator.blueair_api_device.uuid}-water-shortage",
            device_class=BinarySensorDeviceClass.PROBLEM,
        )
        super().__init__("Water Shortage", coordinator)

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self.coordinator.water_shortage
