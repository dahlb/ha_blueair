from __future__ import annotations

from homeassistant.components.switch import (
    SwitchEntity,
    SwitchDeviceClass,
)

from .entity import BlueairEntity, async_setup_entry_helper


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Blueair sensors from config entry."""
    async_setup_entry_helper(hass, config_entry, async_add_entities,
        entity_classes=[
            BlueairChildLockSwitchEntity,
            BlueairAutoFanModeSwitchEntity,
            BlueairNightModeSwitchEntity,
            BlueairWickDryModeSwitchEntity,
    ])


class BlueairChildLockSwitchEntity(BlueairEntity, SwitchEntity):
    _attr_device_class = SwitchDeviceClass.SWITCH

    @classmethod
    def is_implemented(kls, coordinator):
        return coordinator.child_lock is not NotImplemented

    def __init__(self, coordinator):
        super().__init__("Child Lock", coordinator)

    @property
    def is_on(self) -> int | None:
        return self.coordinator.child_lock

    async def async_turn_on(self, **kwargs):
        await self.coordinator.set_child_lock(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self.coordinator.set_child_lock(False)
        self.async_write_ha_state()


class BlueairAutoFanModeSwitchEntity(BlueairEntity, SwitchEntity):
    _attr_device_class = SwitchDeviceClass.SWITCH

    @classmethod
    def is_implemented(kls, coordinator):
        return coordinator.fan_auto_mode is not NotImplemented

    def __init__(self, coordinator):
        super().__init__("Auto Fan Mode", coordinator)

    @property
    def is_on(self) -> int | None:
        return self.coordinator.fan_auto_mode

    async def async_turn_on(self, **kwargs):
        await self.coordinator.set_fan_auto_mode(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self.coordinator.set_fan_auto_mode(False)
        self.async_write_ha_state()


class BlueairNightModeSwitchEntity(BlueairEntity, SwitchEntity):
    _attr_device_class = SwitchDeviceClass.SWITCH

    @classmethod
    def is_implemented(kls, coordinator):
        return coordinator.night_mode is not NotImplemented

    def __init__(self, coordinator):
        super().__init__("Night Mode", coordinator)

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.night_mode

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.night_mode is not None

    async def async_turn_on(self, **kwargs):
        await self.coordinator.set_night_mode(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self.coordinator.set_night_mode(False)
        self.async_write_ha_state()


class BlueairWickDryModeSwitchEntity(BlueairEntity, SwitchEntity):
    _attr_device_class = SwitchDeviceClass.SWITCH

    @classmethod
    def is_implemented(kls, coordinator):
        return coordinator.wick_dry_mode is not NotImplemented

    def __init__(self, coordinator):
        super().__init__("Wick Dry Mode", coordinator)

    @property
    def is_on(self) -> int | None:
        return self.coordinator.wick_dry_mode

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.wick_dry_mode is not None

    async def async_turn_on(self, **kwargs):
        await self.coordinator.set_wick_dry_mode(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self.coordinator.set_wick_dry_mode(False)
        self.async_write_ha_state()
