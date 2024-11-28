# brightness
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.const import (
    UnitOfTemperature,
    PERCENTAGE,
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
)
from blueair_api import ModelEnum

from .const import DOMAIN, DATA_AWS_DEVICES
from .blueair_aws_data_update_coordinator import BlueairAwsDataUpdateCoordinator
from .entity import BlueairEntity


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Blueair sensors from config entry."""
    aws_devices: list[BlueairAwsDataUpdateCoordinator] = hass.data[DOMAIN][
        DATA_AWS_DEVICES
    ]
    entities = []

    for device in aws_devices:
        if device.model in (ModelEnum.UNKNOWN, ModelEnum.PROTECT_7470I):
            entities.extend([
                BlueairTemperatureSensor(device),
                BlueairHumiditySensor(device),
                BlueairVOCSensor(device),
                BlueairPM1Sensor(device),
                BlueairPM10Sensor(device),
                BlueairPM25Sensor(device),
            ])
        elif device.model == ModelEnum.HUMIDIFIER_I35:
            entities.extend([
                BlueairTemperatureSensor(device),
                BlueairHumiditySensor(device),
            ])

    async_add_entities(entities)


class BlueairTemperatureSensor(BlueairEntity, SensorEntity):
    """Monitors the temperature."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, device):
        """Initialize the temperature sensor."""
        super().__init__("Temperature", device)
        self._state: float = None

    @property
    def native_value(self) -> float:
        """Return the current temperature."""
        if self._device.temperature is None:
            return None
        return round(self._device.temperature, 1)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.native_value is not None


class BlueairHumiditySensor(BlueairEntity, SensorEntity):
    """Monitors the humidity."""

    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, device):
        """Initialize the humidity sensor."""
        super().__init__("Humidity", device)
        self._state: float = None

    @property
    def native_value(self) -> float:
        """Return the current humidity."""
        if self._device.humidity is None:
            return None
        return round(self._device.humidity, 0)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.native_value is not None


class BlueairVOCSensor(BlueairEntity, SensorEntity):
    """Monitors the VOC."""

    _attr_device_class = SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS
    _attr_native_unit_of_measurement = CONCENTRATION_MICROGRAMS_PER_CUBIC_METER

    def __init__(self, device):
        """Initialize the VOC sensor."""
        super().__init__("voc", device)
        self._state: float = None

    @property
    def native_value(self) -> float:
        """Return the current voc."""
        if self._device.voc is None:
            return None
        return round(self._device.voc, 0)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.native_value is not None


class BlueairPM1Sensor(BlueairEntity, SensorEntity):
    """Monitors the pm1"""

    _attr_device_class = SensorDeviceClass.PM1
    _attr_native_unit_of_measurement = "µg/m³"

    def __init__(self, device):
        """Initialize the pm1 sensor."""
        super().__init__("pm1", device)
        self._state: float = None

    @property
    def native_value(self) -> float:
        """Return the current pm1."""
        if self._device.pm1 is None:
            return None
        return round(self._device.pm1, 0)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.native_value is not None


class BlueairPM10Sensor(BlueairEntity, SensorEntity):
    """Monitors the pm10"""

    _attr_device_class = SensorDeviceClass.PM10
    _attr_native_unit_of_measurement = "µg/m³"

    def __init__(self, device):
        """Initialize the pm10 sensor."""
        super().__init__("pm10", device)
        self._state: float = None

    @property
    def native_value(self) -> float:
        """Return the current pm10."""
        if self._device.pm10 is None:
            return None
        return round(self._device.pm10, 0)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.native_value is not None


class BlueairPM25Sensor(BlueairEntity, SensorEntity):
    """Monitors the pm25"""

    _attr_device_class = SensorDeviceClass.PM25
    _attr_native_unit_of_measurement = "µg/m³"

    def __init__(self, device):
        """Initialize the pm25 sensor."""
        super().__init__("pm25", device)
        self._state: float = None

    @property
    def native_value(self) -> float:
        """Return the current pm25."""
        if self._device.pm25 is None:
            return None
        return round(self._device.pm25, 0)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.native_value is not None
