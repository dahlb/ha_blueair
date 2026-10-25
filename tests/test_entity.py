"""Availability regression tests (python -m unittest discover -s tests).

Load the entity module with stand-ins for external Home Assistant imports so
these property tests do not require a running Home Assistant installation.
"""

import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch


class CoordinatorEntity:
    """Minimal base needed to import the entity under test."""

    def __class_getitem__(cls, item):
        return cls


class CachedProperty:
    """Stand-in for the unrelated device_info descriptor."""

    def __class_getitem__(cls, item):
        return property


def load_entity():
    """Import the actual entity module with isolated external dependencies."""
    package = "_blueair_entity_test"
    modules = {}
    attributes = {
        package: {"__path__": []},
        "propcache": {"cached_property": CachedProperty},
        "homeassistant.helpers.device_registry": {
            "CONNECTION_NETWORK_MAC": "mac", "DeviceInfo": dict
        },
        "homeassistant.helpers.update_coordinator": {
            "CoordinatorEntity": CoordinatorEntity
        },
        f"{package}.const": {
            "DOMAIN": "ha_blueair", "DATA_DEVICES": "devices",
            "DATA_AWS_DEVICES": "aws_devices"
        },
        f"{package}.blueair_update_coordinator_device": {
            "BlueairUpdateCoordinator": object
        },
    }
    for name, values in attributes.items():
        module = ModuleType(name)
        module.__dict__.update(values)
        modules[name] = module
    path = (Path(__file__).resolve().parents[1]
            / "custom_components/ha_blueair/entity.py")
    spec = importlib.util.spec_from_file_location(f"{package}.entity", path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(module)
    return module.BlueairEntity


class AvailabilityTest(unittest.TestCase):
    """Check Sense+ fallback and unchanged behavior for other models."""

    @classmethod
    def setUpClass(cls):
        cls.entity_class = load_entity()

    def available(self, model="sense+", speed=0, success=True, online=False):
        entity = object.__new__(self.entity_class)
        entity.coordinator = SimpleNamespace(
            model=model, last_update_success=success, online=online,
            blueair_api_device=SimpleNamespace(fan_speed=speed),
        )
        return entity.available

    def test_sense_plus_valid_states_without_wifi_flag(self):
        for speed in (0, 1, 2, 3, "0", "1", "2", "3"):
            with self.subTest(speed=speed):
                self.assertTrue(self.available(speed=speed))

    def test_sense_plus_invalid_states(self):
        for speed in (None, NotImplemented, -1, 4, "4", "", "bad", 2.5,
                      "2.5", True, False, [], {}):
            with self.subTest(speed=speed):
                self.assertFalse(self.available(speed=speed, online=True))

    def test_failed_refresh_stays_unavailable(self):
        for online in (False, True):
            with self.subTest(online=online):
                self.assertFalse(self.available(success=False, online=online))

    def test_other_models_keep_online_requirement(self):
        for model in ("classic_680i", "Blue Pure 211i Max", "unknown"):
            for success in (False, True):
                for online in (False, True):
                    with self.subTest(model=model, success=success, online=online):
                        self.assertEqual(
                            self.available(model=model, success=success,
                                           online=online),
                            success and online,
                        )


if __name__ == "__main__":
    unittest.main()
