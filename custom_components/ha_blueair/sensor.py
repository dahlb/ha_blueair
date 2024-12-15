from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.const import (
    UnitOfTemperature,
    PERCENTAGE,
    CONCENTRATION_PARTS_PER_MILLION,
    CONCENTRATION_PARTS_PER_BILLION,
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
)
from blueair_api import DeviceAws

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



class BlueairTemperatureSensor(BlueairEntity, SensorEntity):
    """Monitors the temperature."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @classmethod
    def is_supported(kls, coordinator):
        return coordinator.temperature is not NotImplemented

    def __init__(self, coordinator):
        """Initialize the temperature sensor."""
        super().__init__("Temperature", coordinator)
        self._state: float | None = None

    @property
    def native_value(self) -> float | None:
        """Return the current temperature."""
        if self.coordinator.temperature is None:
            return None
        return round(self.coordinator.temperature, 1)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.native_value is not None


class BlueairHumiditySensor(BlueairEntity, SensorEntity):
    """Monitors the humidity."""

    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_native_unit_of_measurement = PERCENTAGE

    @classmethod
    def is_supported(kls, coordinator):
        return coordinator.humidity is not NotImplemented


    def __init__(self, coordinator):
        """Initialize the humidity sensor."""
        super().__init__("Humidity", coordinator)
        self._state: float | None = None

    @property
    def native_value(self) -> float | None:
        """Return the current humidity."""
        if self.coordinator.humidity is None:
            return None
        return round(self.coordinator.humidity, 0)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.native_value is not None


class BlueairVOCSensor(BlueairEntity, SensorEntity):
    """Monitors the VOC."""

    _attr_device_class = SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS
    _attr_native_unit_of_measurement = CONCENTRATION_PARTS_PER_BILLION

    @classmethod
    def is_supported(kls, coordinator):
        return coordinator.voc is not NotImplemented

    def __init__(self, coordinator):
        """Initialize the VOC sensor."""
        super().__init__("voc", coordinator)
        self._state: float | None = None

    @property
    def native_value(self) -> float | None:
        """Return the current voc."""
        if self.coordinator.voc is None:
            return None
        return round(self.coordinator.voc, 0)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.native_value is not None


class BlueairPM1Sensor(BlueairEntity, SensorEntity):
    """Monitors the pm1"""

    _attr_device_class = SensorDeviceClass.PM1
    _attr_native_unit_of_measurement = CONCENTRATION_MICROGRAMS_PER_CUBIC_METER

    @classmethod
    def is_supported(kls, coordinator):
        return coordinator.pm1 is not NotImplemented

    def __init__(self, coordinator):
        """Initialize the pm1 sensor."""
        super().__init__("pm1", coordinator)
        self._state: float | None = None

    @property
    def native_value(self) -> float | None:
        """Return the current pm1."""
        if self.coordinator.pm1 is None:
            return None
        if type(self.coordinator) is DeviceAws:
            return int((self.coordinator.pm1 * 100) // 132)
        else:
            return int(self.coordinator.pm1)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.native_value is not None


class BlueairPM10Sensor(BlueairEntity, SensorEntity):
    """Monitors the pm10"""

    _attr_device_class = SensorDeviceClass.PM10
    _attr_native_unit_of_measurement = CONCENTRATION_MICROGRAMS_PER_CUBIC_METER

    @classmethod
    def is_supported(kls, coordinator):
        return coordinator.pm10 is not NotImplemented

    def __init__(self, coordinator):
        """Initialize the pm10 sensor."""
        super().__init__("pm10", coordinator)
        self._state: float | None = None

    @property
    def native_value(self) -> float | None:
        """Return the current pm10."""
        if self.coordinator.pm10 is None:
            return None
        if type(self.coordinator) is DeviceAws:
            return int((self.coordinator.pm10 * 100) // 132)
        else:
            return int(self.coordinator.pm10)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.native_value is not None


class BlueairPM25Sensor(BlueairEntity, SensorEntity):
    """Monitors the pm2.5"""

    _attr_device_class = SensorDeviceClass.PM25
    _attr_native_unit_of_measurement = CONCENTRATION_MICROGRAMS_PER_CUBIC_METER

    @classmethod
    def is_supported(kls, coordinator):
        return coordinator.pm25 is not NotImplemented

    def __init__(self, coordinator):
        """Initialize the pm25 sensor."""
        super().__init__("pm25", coordinator)
        self._state: float | None = None

    @property
    def native_value(self) -> float | None:
        """Return the current pm25."""
        if self.coordinator.pm25 is None:
            return None
        if type(self.coordinator) is DeviceAws:
            return int((self.coordinator.pm25 * 100) // 132)
        else:
            return int(self.coordinator.pm25)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.native_value is not None


class BlueairCO2Sensor(BlueairEntity, SensorEntity):
    """Monitors the Co2"""

    _attr_device_class = SensorDeviceClass.CO2
    _attr_native_unit_of_measurement = CONCENTRATION_PARTS_PER_MILLION

    @classmethod
    def is_supported(kls, coordinator):
        return coordinator.co2 is not NotImplemented

    def __init__(self, coordinator):
        """Initialize the co2 sensor."""
        super().__init__("co2", coordinator)
        self._state: float | None = None

    @property
    def native_value(self) -> float | None:
        """Return the current co2."""
        if self.coordinator.co2 is None:
            return None
        if type(self.coordinator) is DeviceAws:
            return int((self.coordinator.co2 * 100) // 132)
        else:
            return int(self.coordinator.co2)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.native_value is not None
