from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfTemperature,
    UnitOfTime,
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    CONCENTRATION_PARTS_PER_MILLION,
    CONCENTRATION_PARTS_PER_BILLION,
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
)

from .blueair_update_coordinator import BlueairUpdateCoordinator
from .blueair_update_coordinator_device_aws import BlueairUpdateCoordinatorDeviceAws
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
            BlueairFilterLifeSensor,
            BlueairWickLifeSensor,
            BlueairWaterRefresherLifeSensor,
            BlueairWaterLevelSensor,
            BlueairRssiSensor,
            BlueairTimerDurationSensor,
    ])


class BlueairSensor(BlueairEntity, SensorEntity):
    """Generic Blueair Sensor, configured through EntityDescription."""

    @classmethod
    def is_implemented(kls, coordinator):
        # Use NotImplemented as the default so a coordinator that doesn't even
        # declare this attribute (e.g. an AWS-only property on the legacy
        # coordinator class) is treated as "not implemented" instead of
        # raising AttributeError, which would abort the whole sensor platform.
        # See issue #356.
        return getattr(coordinator, kls(coordinator).entity_description.key, NotImplemented) is not NotImplemented

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
        device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS,
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


class BlueairFilterLifeSensor(BlueairSensor):
    """Monitors the filter remaining life"""
    entity_description = SensorEntityDescription(
        key="filter_life",
        name="Filter Life",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
        icon="mdi:air-filter",
    )


class BlueairWickLifeSensor(BlueairSensor):
    """Monitors the wick remaining life"""
    entity_description = SensorEntityDescription(
        key="wick_life",
        name="Wick Life",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
        icon="mdi:air-filter",
    )

class BlueairWaterRefresherLifeSensor(BlueairSensor):
    """Monitors the water refresher remaining life"""
    entity_description = SensorEntityDescription(
        key="water_refresher_life",
        name="Water Refresher Life",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
        icon="mdi:air-filter",
    )

class BlueairWaterLevelSensor(BlueairSensor):
    """Monitors the water level"""
    entity_description = SensorEntityDescription(
        key="water_level",
        name="Water Level",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
        icon="mdi:waves",
    )


class BlueairRssiSensor(BlueairSensor):
    """Monitors the Wi-Fi signal strength reported via MQTT (dBm).

    RSSI arrives only via the MQTT 5s topic (the REST telemetry endpoint
    does not return it), so the value is None at startup until the first
    MQTT message lands.  Override is_implemented to check the schema-
    declared sensor slugs instead of the current value, otherwise the
    entity would never be created on REST-only devices or before the
    first MQTT publish.
    """
    entity_description = SensorEntityDescription(
        key="rssi",
        name="Signal Strength",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        entity_registry_enabled_default=False,
        suggested_display_precision=0,
    )

    @classmethod
    def is_implemented(kls, coordinator):
        if not isinstance(coordinator, BlueairUpdateCoordinatorDeviceAws):
            return False
        return "rssi" in (coordinator.blueair_api_device.mqtt_sensor_slugs or [])


class BlueairTimerDurationSensor(BlueairSensor):
    """Monitors the configured sleep / off timer duration (seconds).

    AWS-only.  ``timer_duration`` is populated from REST ``states[]``
    during refresh(), so the value is available shortly after startup on
    devices that ship a sleep timer (humidifiers, Mini Restful).  The
    legacy ``Device`` API has no concept of a sleep timer, so this
    entity is restricted to AWS coordinators via :py:meth:`is_implemented`
    (mirrors :class:`BlueairRssiSensor`).
    """
    entity_description = SensorEntityDescription(
        key="timer_duration",
        name="Timer Duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        entity_registry_enabled_default=False,
        suggested_display_precision=0,
        icon="mdi:timer-outline",
    )

    @classmethod
    def is_implemented(kls, coordinator):
        # AWS-only entity: the legacy Device class does not model a sleep
        # timer at all.  Guard explicitly so this entity is never offered
        # for a legacy coordinator (issue #356).
        if not isinstance(coordinator, BlueairUpdateCoordinatorDeviceAws):
            return False
        return super().is_implemented(coordinator)
