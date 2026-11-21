"""AWS coordinator PM sensor regression tests (python -m unittest discover -s tests).

Load the AWS coordinator module with stand-ins for external Home Assistant
and blueair_api imports so these property tests do not require a running
Home Assistant installation.
"""

import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from typing import Any
import unittest
from unittest.mock import patch


def load_coordinator_device_aws() -> type[Any]:
    """Import the actual AWS coordinator module with isolated external dependencies."""
    package = "_blueair_coordinator_aws_test"
    modules = {}
    attributes = {
        package: {"__path__": []},
        "homeassistant.util.color": {
            "value_to_brightness": object,
            "brightness_to_value": object,
        },
        "blueair_api": {"DeviceAws": object},
        f"{package}.coordinator": {
            "BlueairUpdateCoordinator": object,
            "Capability": object,
        },
    }
    for name, values in attributes.items():
        module = ModuleType(name)
        module.__dict__.update(values)
        modules[name] = module
    path = (
        Path(__file__).resolve().parents[1]
        / "custom_components/ha_blueair/coordinator_device_aws.py"
    )
    spec = importlib.util.spec_from_file_location(
        f"{package}.coordinator_device_aws",
        path,
    )
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(module)
    return module.BlueairUpdateCoordinatorDeviceAws


class PmSensorScalingTest(unittest.TestCase):
    """Check that PM sensors return raw API values without scaling."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load the AWS coordinator class under test."""
        cls.coordinator_class = load_coordinator_device_aws()

    def make_coordinator(self, **device_attrs: object) -> Any:
        """Return an uninitialized coordinator with a stubbed API device."""
        coordinator = object.__new__(self.coordinator_class)
        coordinator.blueair_api_device = SimpleNamespace(**device_attrs)
        return coordinator

    def test_pm_values_returned_unscaled(self) -> None:
        """PM1, PM10, and PM2.5 return raw API values without scaling."""
        for value in (0, 9, 29, 45, 63, 132):
            with self.subTest(value=value):
                coordinator = self.make_coordinator(
                    pm1=value,
                    pm10=value,
                    pm2_5=value,
                )
                assert coordinator.pm1 == value
                assert coordinator.pm10 == value
                assert coordinator.pm25 == value

    def test_pm_none_and_not_implemented_pass_through(self) -> None:
        """None and NotImplemented pass through unchanged."""
        for value in (None, NotImplemented):
            with self.subTest(value=value):
                coordinator = self.make_coordinator(
                    pm1=value,
                    pm10=value,
                    pm2_5=value,
                )
                assert coordinator.pm1 is value
                assert coordinator.pm10 is value
                assert coordinator.pm25 is value


if __name__ == "__main__":
    unittest.main()
