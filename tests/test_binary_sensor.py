from unittest.mock import MagicMock
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from custom_components.ha_blueair.binary_sensor import (
    BlueairBinarySensor,
    BlueairFilterExpiredSensor,
    BlueairOnlineSensor,
    BlueairWaterShortageSensor,
)
from custom_components.ha_blueair.blueair_update_coordinator import BlueairUpdateCoordinator

def test_is_on_returns_coordinator_value():
    coordinator = MagicMock(spec=BlueairUpdateCoordinator)
    coordinator.online = True
    coordinator.device_name = "Test Device"
    coordinator.id = "test_id"

    class MockSensor(BlueairBinarySensor):
        entity_description = MagicMock()
        entity_description.key = "online"
        entity_description.name = "Mock Name"

    sensor = MockSensor(coordinator)
    assert sensor.is_on == True

    coordinator.online = False
    assert sensor.is_on == False

def test_filter_expired_sensor():
    coordinator = MagicMock(spec=BlueairUpdateCoordinator)
    coordinator.device_name = "Test Device"
    coordinator.id = "test_id"
    sensor = BlueairFilterExpiredSensor(coordinator)

    assert sensor.entity_description.key == "filter_expired"
    assert sensor.entity_description.name == "Filter Expiration"
    assert sensor.entity_description.device_class == BinarySensorDeviceClass.PROBLEM
    assert sensor.entity_description.icon == "mdi:air-filter"

def test_online_sensor():
    coordinator = MagicMock(spec=BlueairUpdateCoordinator)
    coordinator.device_name = "Test Device"
    coordinator.id = "test_id"
    sensor = BlueairOnlineSensor(coordinator)

    assert sensor.entity_description.key == "online"
    assert sensor.entity_description.name == "Online"
    assert sensor.entity_description.device_class == BinarySensorDeviceClass.CONNECTIVITY
    assert sensor.entity_description.icon == "mdi:wifi-check"
    assert sensor.available is True

def test_online_sensor_icon():
    coordinator = MagicMock(spec=BlueairUpdateCoordinator)
    coordinator.device_name = "Test Device"
    coordinator.id = "test_id"
    sensor = BlueairOnlineSensor(coordinator)

    coordinator.online = True
    assert sensor.icon == "mdi:wifi-check"

    coordinator.online = False
    assert sensor.icon == "mdi:wifi-strength-outline"

def test_water_shortage_sensor():
    coordinator = MagicMock(spec=BlueairUpdateCoordinator)
    coordinator.device_name = "Test Device"
    coordinator.id = "test_id"
    sensor = BlueairWaterShortageSensor(coordinator)

    assert sensor.entity_description.key == "water_shortage"
    assert sensor.entity_description.name == "Water Shortage"
    assert sensor.entity_description.device_class == BinarySensorDeviceClass.PROBLEM
    assert sensor.entity_description.icon == "mdi:water-alert-outline"

def test_is_implemented():
    coordinator = MagicMock(spec=BlueairUpdateCoordinator)

    # Supported
    coordinator.online = True
    assert BlueairOnlineSensor.is_implemented(coordinator) is True

    # Not supported
    coordinator.filter_expired = NotImplemented
    assert BlueairFilterExpiredSensor.is_implemented(coordinator) is False
