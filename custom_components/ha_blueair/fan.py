"""Support for Blueair fans."""
from __future__ import annotations

from homeassistant.components.fan import (
    FanEntity,
    SUPPORT_SET_SPEED,
)

from .const import DOMAIN, DATA_DEVICES, DATA_AWS_DEVICES
from .blueair_data_update_coordinator import BlueairDataUpdateCoordinator
from .blueair_aws_data_update_coordinator import BlueairAwsDataUpdateCoordinator
from .entity import BlueairEntity


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Blueair fans from config entry."""
    devices: list[BlueairDataUpdateCoordinator] = hass.data[DOMAIN][DATA_DEVICES]
    entities = []
    for device in devices:
        entities.extend(
            [
                BlueairFan(device),
            ]
        )
    async_add_entities(entities)

    devices: list[BlueairAwsDataUpdateCoordinator] = hass.data[DOMAIN][DATA_AWS_DEVICES]
    entities = []
    for device in devices:
        entities.extend(
            [
                BlueairAwsFan(device),
            ]
        )
    async_add_entities(entities)


class BlueairFan(BlueairEntity, FanEntity):
    """Controls Fan."""

    def __init__(self, device: BlueairDataUpdateCoordinator):
        """Initialize the temperature sensor."""
        super().__init__("Fan", device)

    @property
    def supported_features(self) -> int:
        return SUPPORT_SET_SPEED

    @property
    def is_on(self) -> int:
        return self._device.is_on

    @property
    def percentage(self) -> int:
        """Return the current speed percentage."""
        return int(round(self._device.fan_speed * 33.33, 0))

    async def async_set_percentage(self, percentage: int) -> None:
        """Sets fan speed percentage."""
        if percentage == 100:
            new_speed = "3"
        elif percentage > 50:
            new_speed = "2"
        elif percentage > 20:
            new_speed = "1"
        else:
            new_speed = "0"

        await self._device.set_fan_speed(new_speed)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: any) -> None:
        await self._device.set_fan_speed("0")

    async def async_turn_on(self, **kwargs: any) -> None:
        await self._device.set_fan_speed("2")

    @property
    def speed_count(self) -> int:
        """Return the number of speeds the fan supports."""
        return 3


class BlueairAwsFan(BlueairEntity, FanEntity):
    """Controls Fan."""

    def __init__(self, device: BlueairAwsDataUpdateCoordinator):
        """Initialize the temperature sensor."""
        super().__init__("Fan", device)

    @property
    def supported_features(self) -> int:
        return SUPPORT_SET_SPEED

    @property
    def is_on(self) -> int:
        return self._device.is_on

    @property
    def percentage(self) -> int:
        """Return the current speed percentage."""
        return self._device.fan_speed

    async def async_set_percentage(self, percentage: int) -> None:
        await self._device.set_fan_speed(percentage)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: any) -> None:
        await self._device.set_running(False)
        self.async_write_ha_state()

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: any,
    ) -> None:
        await self._device.set_running(True)
        self.async_write_ha_state()
        if percentage is not None:
            await self.async_set_percentage(percentage=percentage)

    @property
    def speed_count(self) -> int:
        """Return the number of speeds the fan supports."""
        return 100
