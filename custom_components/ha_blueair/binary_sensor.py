"""Binary sensor platform for Blueair devices."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import BlueairConfigEntry
from .coordinator import BlueairUpdateCoordinator
from .entity import BlueairEntity, async_setup_entry_helper


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BlueairConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Blueair sensors from config entry."""
    async_setup_entry_helper(
        hass,
        config_entry,
        async_add_entities,
        entity_classes=[
            BlueairOnlineSensor,
            BlueairFilterExpiredSensor,
            BlueairWaterShortageSensor,
        ],
    )


class BlueairBinarySensor(BlueairEntity, BinarySensorEntity):
    """Blueair binary sensor."""

    @classmethod
    def is_implemented(cls, coordinator: BlueairUpdateCoordinator) -> bool:
        """Return whether the coordinator supports this entity."""
        # See sensor.BlueairSensor.is_implemented (issue #356) for rationale
        # on the NotImplemented default.
        return (
            getattr(coordinator, cls(coordinator).entity_description.key, NotImplemented)
            is not NotImplemented
        )

    def __init__(self, coordinator: BlueairUpdateCoordinator) -> None:
        """Initialize the temperature sensor."""
        super().__init__(self.entity_description.name, coordinator)

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return getattr(self.coordinator, self.entity_description.key)


class BlueairFilterExpiredSensor(BlueairBinarySensor):
    """Blueair filter expired sensor."""

    entity_description = BinarySensorEntityDescription(
        key="filter_expired",
        name="Filter Expiration",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:air-filter",
    )


class BlueairOnlineSensor(BlueairBinarySensor):
    """Blueair online sensor."""

    entity_description = BinarySensorEntityDescription(
        key="online",
        name="Online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        icon="mdi:wifi-check",
    )

    @property
    def icon(self) -> str | None:
        """Return the icon to use in the frontend."""
        if self.is_on:
            return self.entity_description.icon
        return "mdi:wifi-strength-outline"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return True


class BlueairWaterShortageSensor(BlueairBinarySensor):
    """Blueair water shortage sensor."""

    entity_description = BinarySensorEntityDescription(
        key="water_shortage",
        name="Water Shortage",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:water-alert-outline",
    )
