"""Availability regression tests (python -m unittest discover -s tests).

Load the entity module with stand-ins for external Home Assistant imports so
these property tests do not require a running Home Assistant installation.
"""

import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from typing import Any
import unittest
from unittest.mock import patch

import pytest


class CoordinatorEntity:
    """Minimal base needed to import the entity under test."""

    def __class_getitem__(cls, item: object) -> type[CoordinatorEntity]:
        """Support subscripting like the real generic class."""
        return cls


class CachedProperty:
    """Stand-in for the unrelated device_info descriptor."""

    def __class_getitem__(cls, item: object) -> type[property]:
        """Support subscripting like the real generic descriptor."""
        return property


def load_entity() -> type[Any]:
    """Import the actual entity module with isolated external dependencies."""
    package = "_blueair_entity_test"
    modules = {}
    attributes = {
        package: {"__path__": [], "BlueairConfigEntry": object},
        "propcache": {"cached_property": CachedProperty},
        "homeassistant.helpers.device_registry": {
            "CONNECTION_NETWORK_MAC": "mac",
            "DeviceInfo": dict,
        },
        "homeassistant.helpers.update_coordinator": {"CoordinatorEntity": CoordinatorEntity},
        f"{package}.const": {
            "DOMAIN": "ha_blueair",
        },
        f"{package}.coordinator": {"BlueairUpdateCoordinator": object},
    }
    for name, values in attributes.items():
        module = ModuleType(name)
        module.__dict__.update(values)
        modules[name] = module
    path = Path(__file__).resolve().parents[1] / "custom_components/ha_blueair/entity.py"
    spec = importlib.util.spec_from_file_location(f"{package}.entity", path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(module)
    return module.BlueairEntity


class AvailabilityTest(unittest.TestCase):
    """Check that availability follows the poll result and the coordinator's online.

    Model-specific quirks (e.g. Sense+) live in the coordinator's online; see
    test_coordinator.py.
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Load the entity class under test."""
        cls.entity_class = load_entity()

    def available(self, success: bool, online: object) -> bool:
        """Return the entity's availability for a stubbed coordinator state."""
        entity = object.__new__(self.entity_class)
        entity.coordinator = SimpleNamespace(last_update_success=success, online=online)
        return entity.available

    def test_requires_a_successful_poll_and_online(self) -> None:
        """Entities are available only after a successful poll of an online device."""
        for success in (False, True):
            for online in (False, True, None):
                with self.subTest(success=success, online=online):
                    assert self.available(success, online) == (success and bool(online))


if __name__ == "__main__":
    unittest.main()


@pytest.mark.asyncio
async def test_devices_without_a_mac_register_by_identifier_and_warn_once(
    hass: Any, setup_blueair: Any, caplog: pytest.LogCaptureFixture
) -> None:
    """Register a device Blueair reports without a MAC, warning once per device."""
    from homeassistant.helpers import device_registry as dr  # noqa: PLC0415

    from .conftest import make_purifier  # noqa: PLC0415

    device = make_purifier(uuid="no-mac-1")
    device.mac = None
    entry = await setup_blueair(aws=[device])

    registered = dr.async_get(hass).async_get_device_by_identifier(
        ("ha_blueair", "no-mac-1"), entry.entry_id
    )
    assert registered is not None
    assert registered.connections == set()
    assert caplog.text.count("reported mac=None") == 1


def test_base_entity_requires_is_implemented() -> None:
    """Make every entity class say which coordinators support it."""
    from custom_components.ha_blueair.entity import BlueairEntity  # noqa: PLC0415

    with pytest.raises(NotImplementedError):
        BlueairEntity.is_implemented(object())


# Marks a coordinator that doesn't declare the attribute at all.
_MISSING = object()


@pytest.mark.parametrize(
    ("module", "class_name", "key"),
    [
        ("sensor", "BlueairTemperatureSensor", "temperature"),
        ("binary_sensor", "BlueairWaterShortageSensor", "water_shortage"),
        ("switch", "BlueairChildLockSwitchEntity", "child_lock"),
    ],
)
@pytest.mark.parametrize(
    ("value", "implemented"), [(_MISSING, False), (NotImplemented, False), (None, True)]
)
def test_is_implemented_reads_the_class_description(
    module: str, class_name: str, key: str, value: object, implemented: bool
) -> None:
    """Check support from the class's description, without creating an entity.

    A coordinator that lacks the attribute entirely is unsupported rather
    than an error (issue #356), on every platform.
    """
    entity_class = getattr(
        importlib.import_module(f"custom_components.ha_blueair.{module}"), class_name
    )
    coordinator = SimpleNamespace() if value is _MISSING else SimpleNamespace(**{key: value})

    with patch.object(entity_class, "__init__", side_effect=AssertionError("instantiated")):
        assert entity_class.is_implemented(coordinator) is implemented
