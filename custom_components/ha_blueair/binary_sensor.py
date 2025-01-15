from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

from .blueair_update_coordinator import BlueairUpdateCoordinator
from .entity import BlueairEntity, async_setup_entry_helper


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Blueair sensors from config entry."""
    async_setup_entry_helper(hass, config_entry, async_add_entities,
        entity_classes=[
            BlueairOnlineSensor,
            BlueairWaterShortageSensor,
    ])

class BlueairBinarySensor(BlueairEntity, BinarySensorEntity):
    @classmethod
    def is_implemented(kls, coordinator: BlueairUpdateCoordinator) -> bool:
        return getattr(coordinator, kls(coordinator).entity_description.key) is not NotImplemented

    def __init__(self, coordinator):
        """Initialize the temperature sensor."""
        super().__init__(self.entity_description.name, coordinator)

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return getattr(self.coordinator, self.entity_description.key)


class BlueairOnlineSensor(BlueairBinarySensor):
    entity_description = BinarySensorEntityDescription(
        key="online",
        name="Online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        icon="mdi:wifi-check",
    )

    @property
    def icon(self) -> str | None:
        if self.is_on:
            return self.entity_description.icon
        else:
            return "mdi:wifi-strength-outline"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return True


class BlueairWaterShortageSensor(BlueairBinarySensor):
    entity_description = BinarySensorEntityDescription(
        key="water_shortage",
        name="Water Shortage",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:water-alert-outline",
    )
