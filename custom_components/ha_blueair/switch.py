from __future__ import annotations

from homeassistant.components.switch import (
    SwitchEntity,
    SwitchDeviceClass,
)

from .const import DOMAIN, DATA_AWS_DEVICES
from .blueair_data_update_coordinator import BlueairDataUpdateCoordinator
from .entity import BlueairEntity


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Blueair sensors from config entry."""
    aws_devices: list[BlueairDataUpdateCoordinator] = hass.data[DOMAIN][
        DATA_AWS_DEVICES
    ]
    entities = []
    for device in aws_devices:
        entities.extend(
            [
                BlueairChildLockSwitchEntity(device),
                BlueairAutoFanModeSwitchEntity(device),
                BlueairNightModeSwitchEntity(device),
            ]
        )
    async_add_entities(entities)


class BlueairChildLockSwitchEntity(BlueairEntity, SwitchEntity):
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, device):
        super().__init__("Child Lock", device)

    @property
    def is_on(self) -> int | None:
        return self._device.child_lock

    async def async_turn_on(self, **kwargs):
        await self._device.set_child_lock(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self._device.set_child_lock(False)
        self.async_write_ha_state()


class BlueairAutoFanModeSwitchEntity(BlueairEntity, SwitchEntity):
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, device):
        super().__init__("Auto Fan Mode", device)

    @property
    def is_on(self) -> int | None:
        return self._device.fan_auto_mode

    async def async_turn_on(self, **kwargs):
        await self._device.set_fan_auto_mode(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self._device.set_fan_auto_mode(False)
        self.async_write_ha_state()

class BlueairNightModeSwitchEntity(BlueairEntity, SwitchEntity):
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, device):
        super().__init__("Night Mode", device)

    @property
    def is_on(self) -> bool | None:
        return self._device.night_mode

    async def async_turn_on(self, **kwargs):
        await self._device.set_night_mode(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self._device.set_night_mode(False)
        self.async_write_ha_state()

