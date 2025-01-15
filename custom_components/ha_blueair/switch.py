from __future__ import annotations
import logging

from homeassistant.components.switch import (
    SwitchEntity,
    SwitchDeviceClass, SwitchEntityDescription,
)

from .entity import BlueairEntity, async_setup_entry_helper

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Blueair sensors from config entry."""
    async_setup_entry_helper(hass, config_entry, async_add_entities,
        entity_classes=[
            BlueairChildLockSwitchEntity,
            BlueairGermShieldSwitchEntity,
            BlueairWickDryModeSwitchEntity,
    ])


class BlueairSwitchEntity(BlueairEntity, SwitchEntity):
    @classmethod
    def is_implemented(kls, coordinator):
        return getattr(coordinator, kls(coordinator).entity_description.key) is not NotImplemented

    def __init__(self, coordinator):
        super().__init__(self.entity_description.name, coordinator)

    @property
    def is_on(self) -> bool | None:
        return getattr(self.coordinator, self.entity_description.key)

    async def async_turn_on(self, **kwargs):
        await getattr(self.coordinator, f"set_{self.entity_description.key}")(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await getattr(self.coordinator, f"set_{self.entity_description.key}")(False)
        self.async_write_ha_state()


class BlueairChildLockSwitchEntity(BlueairSwitchEntity):
    entity_description = SwitchEntityDescription(
        key="child_lock",
        name="Child Lock",
        device_class=SwitchDeviceClass.SWITCH,
    )
    _attr_translation_key = "child_lock"


class BlueairGermShieldSwitchEntity(BlueairSwitchEntity):
    entity_description = SwitchEntityDescription(
        key="germ_shield",
        name="Germ Shield",
        device_class=SwitchDeviceClass.SWITCH,
    )


class BlueairWickDryModeSwitchEntity(BlueairSwitchEntity):
    entity_description = SwitchEntityDescription(
        key="wick_dry_mode",
        name="Wick Dry Mode",
        device_class=SwitchDeviceClass.SWITCH,
    )
