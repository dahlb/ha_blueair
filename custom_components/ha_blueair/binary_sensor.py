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

# Read-only platform: the coordinators fetch data centrally, so entity updates
# never call Blueair and need no limit.
PARALLEL_UPDATES = 0


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

    # The original English name; see BlueairEntity.__init__.
    _unique_id_suffix: str

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
        super().__init__(self._unique_id_suffix, coordinator)

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        value: bool | None = getattr(self.coordinator, self.entity_description.key)
        return value


class BlueairFilterExpiredSensor(BlueairBinarySensor):
    """Blueair filter expired sensor."""

    _unique_id_suffix = "Filter Expiration"
    entity_description = BinarySensorEntityDescription(
        key="filter_expired",
        translation_key="filter_expired",
        device_class=BinarySensorDeviceClass.PROBLEM,
    )


class BlueairOnlineSensor(BlueairBinarySensor):
    """Blueair online sensor."""

    _unique_id_suffix = "Online"
    entity_description = BinarySensorEntityDescription(
        key="online",
        translation_key="online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return True


class BlueairWaterShortageSensor(BlueairBinarySensor):
    """Blueair water shortage sensor."""

    _unique_id_suffix = "Water Shortage"
    entity_description = BinarySensorEntityDescription(
        key="water_shortage",
        translation_key="water_shortage",
        device_class=BinarySensorDeviceClass.PROBLEM,
    )
