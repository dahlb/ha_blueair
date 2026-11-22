"""Switch platform for Blueair devices."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import BlueairConfigEntry
from .coordinator import BlueairUpdateCoordinator
from .entity import BlueairEntity, async_setup_entry_helper, coordinator_reports

_LOGGER = logging.getLogger(__name__)

# Commands go to Blueair's cloud API; send one at a time.
PARALLEL_UPDATES = 1


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
            BlueairChildLockSwitchEntity,
            BlueairGermShieldSwitchEntity,
            BlueairWickDryModeSwitchEntity,
        ],
    )


class BlueairSwitchEntity(BlueairEntity, SwitchEntity):
    """Blueair switch entity."""

    # The original English name; see BlueairEntity.__init__.
    _unique_id_suffix: str

    @classmethod
    def is_implemented(cls, coordinator: BlueairUpdateCoordinator) -> bool:
        """Return whether the coordinator supports this entity."""
        return coordinator_reports(coordinator, cls.entity_description.key)

    def __init__(self, coordinator: BlueairUpdateCoordinator) -> None:
        """Initialize the blueair switch entity."""
        super().__init__(self._unique_id_suffix, coordinator)

    @property
    def is_on(self) -> bool | None:
        """Return whether the device is on."""
        value: bool | None = getattr(self.coordinator, self.entity_description.key)
        return value

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        await getattr(self.coordinator, f"set_{self.entity_description.key}")(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        await getattr(self.coordinator, f"set_{self.entity_description.key}")(False)


class BlueairChildLockSwitchEntity(BlueairSwitchEntity):
    """Blueair child lock switch entity."""

    _unique_id_suffix = "Child Lock"
    entity_description = SwitchEntityDescription(
        key="child_lock",
        translation_key="child_lock",
        device_class=SwitchDeviceClass.SWITCH,
    )


class BlueairGermShieldSwitchEntity(BlueairSwitchEntity):
    """Blueair germ shield switch entity."""

    _unique_id_suffix = "Germ Shield"
    entity_description = SwitchEntityDescription(
        key="germ_shield",
        translation_key="germ_shield",
        device_class=SwitchDeviceClass.SWITCH,
    )


class BlueairWickDryModeSwitchEntity(BlueairSwitchEntity):
    """Blueair wick dry mode switch entity."""

    _unique_id_suffix = "Wick Dry Mode"
    entity_description = SwitchEntityDescription(
        key="wick_dry_mode",
        translation_key="wick_dry_mode",
        device_class=SwitchDeviceClass.SWITCH,
    )
