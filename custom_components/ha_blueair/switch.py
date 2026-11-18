"""Switch platform for Blueair devices."""

from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .blueair_update_coordinator import BlueairUpdateCoordinator
from .entity import BlueairEntity, async_setup_entry_helper

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
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

    @classmethod
    def is_implemented(cls, coordinator: BlueairUpdateCoordinator) -> bool:
        """Return whether the coordinator supports this entity."""
        return getattr(coordinator, cls(coordinator).entity_description.key) is not NotImplemented

    def __init__(self, coordinator: BlueairUpdateCoordinator) -> None:
        """Initialize the blueair switch entity."""
        super().__init__(self.entity_description.name, coordinator)

    @property
    def is_on(self) -> bool | None:
        """Return whether the device is on."""
        return getattr(self.coordinator, self.entity_description.key)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        await getattr(self.coordinator, f"set_{self.entity_description.key}")(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the entity off."""
        await getattr(self.coordinator, f"set_{self.entity_description.key}")(False)
        self.async_write_ha_state()


class BlueairChildLockSwitchEntity(BlueairSwitchEntity):
    """Blueair child lock switch entity."""

    entity_description = SwitchEntityDescription(
        key="child_lock",
        name="Child Lock",
        device_class=SwitchDeviceClass.SWITCH,
    )
    _attr_translation_key = "child_lock"


class BlueairGermShieldSwitchEntity(BlueairSwitchEntity):
    """Blueair germ shield switch entity."""

    entity_description = SwitchEntityDescription(
        key="germ_shield",
        name="Germ Shield",
        device_class=SwitchDeviceClass.SWITCH,
    )


class BlueairWickDryModeSwitchEntity(BlueairSwitchEntity):
    """Blueair wick dry mode switch entity."""

    entity_description = SwitchEntityDescription(
        key="wick_dry_mode",
        name="Wick Dry Mode",
        device_class=SwitchDeviceClass.SWITCH,
    )
