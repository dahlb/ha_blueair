from unittest.mock import MagicMock
import pytest
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC

from custom_components.ha_blueair.entity import BlueairEntity
from custom_components.ha_blueair.const import DOMAIN

class MockBlueairEntity(BlueairEntity):
    @classmethod
    def is_implemented(kls, coordinator):
        return True

def test_device_info():
    coordinator = MagicMock()
    coordinator.id = "test_id"
    # Note: the property is actually name on the mock, based on the codebase logic
    # _coordinator.name in issue desc, but actual file has self.coordinator.device_name
    coordinator.device_name = "test_device"
    coordinator.name = "test_device" # for compatibility with issue description if needed
    coordinator.model = "test_model"
    coordinator.hw_version = "1.0"
    coordinator.sw_version = "2.0"
    coordinator.serial_number = "12345"
    coordinator.blueair_api_device.mac = "aa:bb:cc:dd:ee:ff"

    entity = MockBlueairEntity("test_type", coordinator)

    device_info = entity.device_info

    assert device_info["connections"] == {(CONNECTION_NETWORK_MAC, "aa:bb:cc:dd:ee:ff")}
    assert device_info["identifiers"] == {(DOMAIN, "test_id")}
    assert device_info["manufacturer"] == "BlueAir"
    assert device_info["model"] == "test_model"
    assert device_info["hw_version"] == "1.0"
    assert device_info["sw_version"] == "2.0"
    assert device_info["serial_number"] == "12345"
    # Ensure we use device_name here since that's what's actually returned by the entity implementation
    assert device_info["name"] == "test_device"

def test_device_info_missing_mac():
    coordinator = MagicMock()
    coordinator.id = "test_id"
    coordinator.device_name = "test_device"
    coordinator.blueair_api_device.mac = None

    entity = MockBlueairEntity("test_type", coordinator)

    with pytest.raises(ValueError, match="MAC address is required for device info"):
        _ = entity.device_info
