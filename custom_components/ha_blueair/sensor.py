# brightness
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import (
    DEVICE_CLASS_ILLUMINANCE,
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_PM1,
    DEVICE_CLASS_PM10,
    DEVICE_CLASS_PM25,
    DEVICE_CLASS_VOLATILE_ORGANIC_COMPOUNDS,
    TEMP_CELSIUS,
    PERCENTAGE,
)


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
                BlueairBrightness(device),
            ]
        )
    async_add_entities(entities)

    aws_devices: list[BlueairDataUpdateCoordinator] = hass.data[DOMAIN][DATA_AWS_DEVICES]
    entities = []
    for device in aws_devices:
        entities.extend(
            [
                BlueairTemperatureSensor(device),
                BlueairHumiditySensor(device),
                BlueairVOCSensor(device),
                BlueairPM1Sensor(device),
                BlueairPM10Sensor(device),
                BlueairPM25Sensor(device),
            ]
        )
    async_add_entities(entities)


class BlueairBrightness(BlueairEntity, SensorEntity):
    _attr_device_class = DEVICE_CLASS_ILLUMINANCE
    _attr_icon = "mdi:lightbulb"

    def __init__(self, device):
        super().__init__("Brightness", device)

    @property
    def native_value(self) -> float:
        return self._device.brightness


class BlueairTemperatureSensor(BlueairEntity, SensorEntity):
    """Monitors the temperature."""

    _attr_device_class = DEVICE_CLASS_TEMPERATURE
    _attr_native_unit_of_measurement = TEMP_CELSIUS

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


class BlueairHumiditySensor(BlueairEntity, SensorEntity):
    """Monitors the humidity."""

    _attr_device_class = DEVICE_CLASS_HUMIDITY
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


class BlueairVOCSensor(BlueairEntity, SensorEntity):
    """Monitors the VOC."""

    _attr_device_class = DEVICE_CLASS_VOLATILE_ORGANIC_COMPOUNDS
    _attr_native_unit_of_measurement = "ppb"

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


class BlueairPM1Sensor(BlueairEntity, SensorEntity):
    """Monitors the pm1"""

    _attr_device_class = DEVICE_CLASS_PM1
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


class BlueairPM10Sensor(BlueairEntity, SensorEntity):
    """Monitors the pm10"""

    _attr_device_class = DEVICE_CLASS_PM10
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


class BlueairPM25Sensor(BlueairEntity, SensorEntity):
    """Monitors the pm25"""

    _attr_device_class = DEVICE_CLASS_PM25
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
