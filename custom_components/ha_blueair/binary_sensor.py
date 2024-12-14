from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers.entity import EntityDescription
from blueair_api import FeatureEnum

from .const import DOMAIN, DATA_DEVICES, DATA_AWS_DEVICES
from .blueair_data_update_coordinator import BlueairDataUpdateCoordinator
from .blueair_aws_data_update_coordinator import BlueairAwsDataUpdateCoordinator
from .entity import BlueairEntity


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Blueair sensors from config entry."""
    feature_class_mapping = [
        [FeatureEnum.FILTER_EXPIRED, BlueairFilterExpiredSensor],
        [FeatureEnum.CHILD_LOCK, BlueairChildLockSensor],
        [FeatureEnum.WATER_SHORTAGE, BlueairWaterShortageSensor],
    ]
    coordinators: list[BlueairDataUpdateCoordinator] = hass.data[DOMAIN][DATA_DEVICES]
    entities = []
    for coordinator in coordinators:
        entities.extend(
            [
                BlueairChildLockSensor(coordinator),
                BlueairFilterExpiredSensor(coordinator),
                BlueairOnlineSensor(coordinator),
            ]
        )
    async_add_entities(entities)

    aws_coordinators: list[BlueairAwsDataUpdateCoordinator] = hass.data[DOMAIN][
        DATA_AWS_DEVICES
    ]
    entities = []
    for coordinator in aws_coordinators:
        entities.append(BlueairOnlineSensor(coordinator))
        for feature_class in feature_class_mapping:
            if coordinator.blueair_api_device.model.supports_feature(feature_class[0]):
                entities.append(feature_class[1](coordinator))
    async_add_entities(entities)


class BlueairChildLockSensor(BlueairEntity, BinarySensorEntity):
    _attr_icon = "mdi:account-child-outline"

    def __init__(self, coordinator):
        super().__init__("Child Lock", coordinator)

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self.coordinator.child_lock


class BlueairFilterExpiredSensor(BlueairEntity, BinarySensorEntity):
    _attr_icon = "mdi:air-filter"

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
