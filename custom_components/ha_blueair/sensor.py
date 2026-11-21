"""Sensor platform for Blueair devices."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfDensity,
    UnitOfRatio,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
import homeassistant.helpers.issue_registry as ir

from . import BlueairConfigEntry
from .const import DOMAIN
from .coordinator import BlueairUpdateCoordinator
from .coordinator_device_aws import BlueairUpdateCoordinatorDeviceAws
from .entity import BlueairEntity, async_setup_entry_helper

# Percentage sensors that used to (incorrectly) report device_class=battery.
# See dahlb/ha_blueair#378.
_LIFE_LEVEL_SENSOR_KEYS = (
    "filter_life",
    "wick_life",
    "water_refresher_life",
    "water_level",
)
BATTERY_DEVICE_CLASS_ISSUE_ID = "life_sensors_no_longer_battery"

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
            BlueairOverallFirmwareSensor,
        ],
    )

    # The filter/wick/water-refresher life and water-level sensors previously
    # used device_class=battery, so existing installs swept them into battery
    # dashboards, low-battery automations and HomeKit battery reporting.  That
    # classification has been removed (#378).  Surface a dismissible repair to
    # let affected users know and point them at the migration guide.  Only fire
    # when the account actually exposes one of these sensors, and self-heal if
    # it no longer does.
    coordinators = config_entry.runtime_data.coordinators
    has_life_level_sensor = any(
        getattr(coordinator, key, NotImplemented) is not NotImplemented
        for coordinator in coordinators
        for key in _LIFE_LEVEL_SENSOR_KEYS
    )
    if has_life_level_sensor:
        ir.async_create_issue(
            hass,
            DOMAIN,
            BATTERY_DEVICE_CLASS_ISSUE_ID,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=BATTERY_DEVICE_CLASS_ISSUE_ID,
            learn_more_url="https://github.com/dahlb/ha_blueair#filter-wick-and-water-sensors-no-longer-report-as-batteries",
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, BATTERY_DEVICE_CLASS_ISSUE_ID)


class BlueairSensor(BlueairEntity, SensorEntity):
    """Generic Blueair Sensor, configured through EntityDescription."""

    # The original English name; see BlueairEntity.__init__.
    _unique_id_suffix: str

    @classmethod
    def is_implemented(cls, coordinator: BlueairUpdateCoordinator) -> bool:
        """Return whether the coordinator supports this entity."""
        # Use NotImplemented as the default so a coordinator that doesn't even
        # declare this attribute (e.g. an AWS-only property on the legacy
        # coordinator class) is treated as "not implemented" instead of
        # raising AttributeError, which would abort the whole sensor platform.
        # See issue #356.
        return (
            getattr(coordinator, cls(coordinator).entity_description.key, NotImplemented)
            is not NotImplemented
        )

    def __init__(self, coordinator: BlueairUpdateCoordinator) -> None:
        """Initialize the temperature sensor."""
        super().__init__(self._unique_id_suffix, coordinator)

    @property
    def native_value(self) -> float | None:
        """Return the current temperature."""
        return getattr(self.coordinator, self.entity_description.key)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return super().available and self.native_value is not None

    @property
    def state_class(self) -> SensorStateClass:
        """Return the state class of this entity, from STATE_CLASSES, if any."""
        return SensorStateClass.MEASUREMENT


class BlueairTemperatureSensor(BlueairSensor):
    """Generic Blueair Sensor, configured through EntityDescription."""

    _unique_id_suffix = "Temperature"
    entity_description = SensorEntityDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    )


class BlueairHumiditySensor(BlueairSensor):
    """Monitors the humidity."""

    _unique_id_suffix = "Humidity"
    entity_description = SensorEntityDescription(
        key="humidity",
        translation_key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
    )


class BlueairVOCSensor(BlueairSensor):
    """Monitors the VOC."""

    _unique_id_suffix = "VOC"
    entity_description = SensorEntityDescription(
        key="voc",
        translation_key="voc",
        device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS,
        native_unit_of_measurement=UnitOfRatio.PARTS_PER_BILLION,
        suggested_display_precision=0,
    )


class BlueairPM1Sensor(BlueairSensor):
    """Monitors the pm1."""

    _unique_id_suffix = "PM 1"
    entity_description = SensorEntityDescription(
        key="pm1",
        translation_key="pm1",
        device_class=SensorDeviceClass.PM1,
        native_unit_of_measurement=UnitOfDensity.MICROGRAMS_PER_CUBIC_METER,
    )


class BlueairPM10Sensor(BlueairSensor):
    """Monitors the pm10."""

    _unique_id_suffix = "PM 10"
    entity_description = SensorEntityDescription(
        key="pm10",
        translation_key="pm10",
        device_class=SensorDeviceClass.PM10,
        native_unit_of_measurement=UnitOfDensity.MICROGRAMS_PER_CUBIC_METER,
    )


class BlueairPM25Sensor(BlueairSensor):
    """Monitors the pm2.5."""

    _unique_id_suffix = "PM 2.5"
    entity_description = SensorEntityDescription(
        key="pm25",
        translation_key="pm25",
        device_class=SensorDeviceClass.PM25,
        native_unit_of_measurement=UnitOfDensity.MICROGRAMS_PER_CUBIC_METER,
    )


class BlueairCO2Sensor(BlueairSensor):
    """Monitors the Co2."""

    _unique_id_suffix = "CO2"
    entity_description = SensorEntityDescription(
        key="co2",
        translation_key="co2",
        device_class=SensorDeviceClass.CO2,
        native_unit_of_measurement=UnitOfRatio.PARTS_PER_MILLION,
        suggested_display_precision=0,
    )


class BlueairFilterLifeSensor(BlueairSensor):
    """Monitors the filter remaining life."""

    _unique_id_suffix = "Filter Life"
    entity_description = SensorEntityDescription(
        key="filter_life",
        translation_key="filter_life",
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
    )


class BlueairWickLifeSensor(BlueairSensor):
    """Monitors the wick remaining life."""

    _unique_id_suffix = "Wick Life"
    entity_description = SensorEntityDescription(
        key="wick_life",
        translation_key="wick_life",
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
    )


class BlueairWaterRefresherLifeSensor(BlueairSensor):
    """Monitors the water refresher remaining life."""

    _unique_id_suffix = "Water Refresher Life"
    entity_description = SensorEntityDescription(
        key="water_refresher_life",
        translation_key="water_refresher_life",
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
    )


class BlueairWaterLevelSensor(BlueairSensor):
    """Monitors the water level."""

    _unique_id_suffix = "Water Level"
    entity_description = SensorEntityDescription(
        key="water_level",
        translation_key="water_level",
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
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

    _unique_id_suffix = "Signal Strength"
    entity_description = SensorEntityDescription(
        key="rssi",
        translation_key="rssi",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        entity_registry_enabled_default=False,
        suggested_display_precision=0,
    )

    @classmethod
    def is_implemented(cls, coordinator: BlueairUpdateCoordinator) -> bool:
        """Return whether the coordinator supports this entity."""
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

    _unique_id_suffix = "Timer Duration"
    entity_description = SensorEntityDescription(
        key="timer_duration",
        translation_key="timer_duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        entity_registry_enabled_default=False,
        suggested_display_precision=0,
    )

    @classmethod
    def is_implemented(cls, coordinator: BlueairUpdateCoordinator) -> bool:
        """Return whether the coordinator supports this entity."""
        # AWS-only entity: the legacy Device class does not model a sleep
        # timer at all.  Guard explicitly so this entity is never offered
        # for a legacy coordinator (issue #356).
        if not isinstance(coordinator, BlueairUpdateCoordinatorDeviceAws):
            return False
        return super().is_implemented(coordinator)


class BlueairOverallFirmwareSensor(BlueairSensor):
    """Reports the device's overall firmware version (AWS shadow ``ofv``).

    The device registry only exposes two version slots, already used for
    Wi-Fi firmware (``sw_version``) and MCU firmware (``hw_version``), so
    the overall firmware version is surfaced here as a diagnostic sensor.
    AWS-only and disabled by default to avoid cluttering the device page;
    the value updates live over MQTT.  This is a text value, so it carries
    no device class, unit, or state class.
    """

    _unique_id_suffix = "Overall Firmware"
    entity_description = SensorEntityDescription(
        key="overall_firmware",
        translation_key="overall_firmware",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    )

    @classmethod
    def is_implemented(cls, coordinator: BlueairUpdateCoordinator) -> bool:
        """Return whether the coordinator supports this entity."""
        # AWS-only entity: the legacy Device class has no overall firmware
        # attribute.  Guard explicitly (mirrors the other AWS-only sensors)
        # so it is never offered for a legacy coordinator (issue #356).
        if not isinstance(coordinator, BlueairUpdateCoordinatorDeviceAws):
            return False
        return super().is_implemented(coordinator)

    @property
    def state_class(self) -> None:
        """Firmware version is a text value with no state class."""
        return None
