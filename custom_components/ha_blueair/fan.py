"""Support for Blueair fans."""
from __future__ import annotations

from homeassistant.components.fan import (
    FanEntity,
    FanEntityFeature,
)

from .const import DEFAULT_FAN_SPEED_PERCENTAGE
from .blueair_update_coordinator_device import BlueairUpdateCoordinatorDevice
from .blueair_update_coordinator_device_aws import BlueairUpdateCoordinatorDeviceAws
from .entity import BlueairEntity, async_setup_entry_helper


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Blueair sensors from config entry."""
    async_setup_entry_helper(hass, config_entry, async_add_entities,
        entity_classes=[
            BlueairFan,
            BlueairAwsFan,
    ])


class BlueairFan(BlueairEntity, FanEntity):
    """Controls Fan."""

    @classmethod
    def is_implemented(kls, coordinator):
        return isinstance(coordinator, BlueairUpdateCoordinatorDevice)

    def __init__(self, coordinator: BlueairUpdateCoordinatorDevice):
        """Initialize the temperature sensor."""
        super().__init__("Fan", coordinator)

    @property
    def supported_features(self) -> int:
        return FanEntityFeature.SET_SPEED | FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF

    @property
    def is_on(self) -> int:
        return self.coordinator.is_on

    @property
    def percentage(self) -> int:
        """Return the current speed percentage."""
        return int(round(self.coordinator.fan_speed * 33.33, 0))

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

        await self.coordinator.set_fan_speed(new_speed)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: any) -> None:
        await self.coordinator.set_fan_speed("0")

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: any,
    ) -> None:
        await self.coordinator.set_fan_speed("1")
        self.async_write_ha_state()
        if percentage is not None:
            await self.async_set_percentage(percentage=percentage)

    @property
    def speed_count(self) -> int:
        """Return the number of speeds the fan supports."""
        return self.coordinator.speed_count


class BlueairAwsFan(BlueairEntity, FanEntity):
    """Controls Fan."""

    @classmethod
    def is_implemented(kls, coordinator):
        return isinstance(coordinator, BlueairUpdateCoordinatorDeviceAws)

    def __init__(self, coordinator: BlueairUpdateCoordinatorDeviceAws):
        """Initialize the temperature sensor."""
        super().__init__("Fan", coordinator)

    @property
    def supported_features(self) -> int:
        features = FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
        if self.coordinator.fan_speed is not NotImplemented:
            features |= FanEntityFeature.SET_SPEED
        return features

    @property
    def is_on(self) -> int:
        return self.coordinator.is_on

    @property
    def percentage(self) -> int:
        """Return the current speed percentage."""
        return int((self.coordinator.fan_speed * 100) // self.coordinator.speed_count)

    async def async_set_percentage(self, percentage: int) -> None:
        await self.coordinator.set_fan_speed(int(round(percentage / 100 * self.coordinator.speed_count)))
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: any) -> None:
        await self.coordinator.set_running(False)
        self.async_write_ha_state()

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: any,
    ) -> None:
        await self.coordinator.set_running(True)
        if percentage is None:
            # FIXME: i35 (and probably others) do not remember the
            # last fan speed and always set the speed to 0. I don't know
            # where to store the last fan speed such that it persists across
            # HA reboots. Thus we set the default turn_on fan speed to 50%
            # to make sure the fan actually spins at all.
            percentage = DEFAULT_FAN_SPEED_PERCENTAGE
        if percentage is not None:
            await self.async_set_percentage(percentage=percentage)
        self.async_write_ha_state()

    @property
    def speed_count(self) -> int:
        """Return the number of speeds the fan supports."""
        return self.coordinator.speed_count
