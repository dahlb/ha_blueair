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
        f"{package}.coordinator_device": {"BlueairUpdateCoordinator": object},
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
    """Check Sense+ fallback and unchanged behavior for other models."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load the entity class under test."""
        cls.entity_class = load_entity()

    def available(
        self,
        model: str = "sense+",
        speed: object = 0,
        success: bool = True,
        online: bool = False,
    ) -> bool:
        """Return the entity's availability for a stubbed coordinator state."""
        entity = object.__new__(self.entity_class)
        entity.coordinator = SimpleNamespace(
            model=model,
            last_update_success=success,
            online=online,
            blueair_api_device=SimpleNamespace(fan_speed=speed),
        )
        return entity.available

    def test_sense_plus_valid_states_without_wifi_flag(self) -> None:
        """Sense+ is available for every valid fan speed, even with wifi_working False."""
        for speed in (0, 1, 2, 3, "0", "1", "2", "3"):
            with self.subTest(speed=speed):
                assert self.available(speed=speed)

    def test_sense_plus_invalid_states(self) -> None:
        """Sense+ is unavailable when the fan speed is not a valid state."""
        for speed in (None, NotImplemented, -1, 4, "4", "", "bad", 2.5, "2.5", True, False, [], {}):
            with self.subTest(speed=speed):
                assert not self.available(speed=speed, online=True)

    def test_failed_refresh_stays_unavailable(self) -> None:
        """A failed refresh makes the entity unavailable regardless of online."""
        for online in (False, True):
            with self.subTest(online=online):
                assert not self.available(success=False, online=online)

    def test_other_models_keep_online_requirement(self) -> None:
        """Other models require both a successful refresh and online."""
        for model in ("classic_680i", "Blue Pure 211i Max", "unknown"):
            for success in (False, True):
                for online in (False, True):
                    with self.subTest(model=model, success=success, online=online):
                        assert self.available(model=model, success=success, online=online) == (
                            success and online
                        )


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
