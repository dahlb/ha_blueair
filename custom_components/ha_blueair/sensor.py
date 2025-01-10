from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfTemperature,
    PERCENTAGE,
    CONCENTRATION_PARTS_PER_MILLION,
    CONCENTRATION_PARTS_PER_BILLION,
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
)

from .blueair_update_coordinator import BlueairUpdateCoordinator
from .entity import BlueairEntity, async_setup_entry_helper

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Blueair sensors from config entry."""
    async_setup_entry_helper(hass, config_entry, async_add_entities,
        entity_classes=[
            BlueairTemperatureSensor,
            BlueairHumiditySensor,
            BlueairVOCSensor,
            BlueairCO2Sensor,
            BlueairPM1Sensor,
            BlueairPM10Sensor,
            BlueairPM25Sensor,
    ])


class BlueairSensor(BlueairEntity, SensorEntity):
    """Generic Blueair Sensor, configured through EntityDescription."""

    @classmethod
    def is_implemented(kls, coordinator):
        return getattr(coordinator, kls(coordinator).entity_description.key) is not NotImplemented

    def __init__(self, coordinator: BlueairUpdateCoordinator):
        """Initialize the temperature sensor."""
        super().__init__(self.entity_description.name, coordinator)

    @property
    def native_value(self) -> float | None:
        """Return the current temperature."""
        return getattr(self.coordinator, self.entity_description.key)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return super().available and self.native_value is not None

    @property
    def state_class(self):
        """Return the state class of this entity, from STATE_CLASSES, if any."""
        return SensorStateClass.MEASUREMENT


class BlueairTemperatureSensor(BlueairSensor):
    """Generic Blueair Sensor, configured through EntityDescription."""
    entity_description = SensorEntityDescription(
        key="temperature",
        name="Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    )


class BlueairHumiditySensor(BlueairSensor):
    """Monitors the humidity."""
    entity_description = SensorEntityDescription(
        key="humidity",
        name="Humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
    )


class BlueairVOCSensor(BlueairSensor):
    """Monitors the VOC."""
    entity_description = SensorEntityDescription(
        key="voc",
        name="VOC",
        device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_BILLION,
        suggested_display_precision=0,
    )


class BlueairPM1Sensor(BlueairSensor):
    """Monitors the pm1"""
    entity_description = SensorEntityDescription(
        key="pm1",
        name="PM 1",
        device_class=SensorDeviceClass.PM1,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    )


class BlueairPM10Sensor(BlueairSensor):
    """Monitors the pm10"""
    entity_description = SensorEntityDescription(
        key="pm10",
        name="PM 10",
        device_class=SensorDeviceClass.PM10,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    )


class BlueairPM25Sensor(BlueairSensor):
    """Monitors the pm2.5"""
    entity_description = SensorEntityDescription(
        key="pm25",
        name="PM 2.5",
        device_class=SensorDeviceClass.PM25,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    )


class BlueairCO2Sensor(BlueairSensor):
    """Monitors the Co2"""
    entity_description = SensorEntityDescription(
        key="co2",
        name="CO2",
        device_class=SensorDeviceClass.CO2,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        suggested_display_precision=0,
    )
