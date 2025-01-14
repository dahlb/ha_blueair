"""Support for Blueair fans."""
from __future__ import annotations

from homeassistant.components.fan import (
    FanEntity,
    FanEntityFeature,
)

from .blueair_update_coordinator import BlueairUpdateCoordinator
from .const import DEFAULT_FAN_SPEED_PERCENTAGE, MODE_AUTO, MODE_NIGHT
from .blueair_update_coordinator_device import BlueairUpdateCoordinatorDevice
from .blueair_update_coordinator_device_aws import BlueairUpdateCoordinatorDeviceAws
from .entity import BlueairEntity, async_setup_entry_helper


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Blueair fans from config entry."""
    async_setup_entry_helper(hass, config_entry, async_add_entities,
        entity_classes=[
            BlueairFan,
            BlueairAwsFan,
    ])


class BlueairFan(BlueairEntity, FanEntity):
    """Controls Fan."""

    @classmethod
    def is_implemented(kls, coordinator: BlueairUpdateCoordinator):
        return isinstance(coordinator, BlueairUpdateCoordinatorDevice)

    def __init__(self, coordinator: BlueairUpdateCoordinator):
        """Initialize the fan entity."""
        self._attr_preset_modes = []
        if coordinator.fan_auto_mode is not NotImplemented:
            self._attr_preset_modes.append(MODE_AUTO)
        if coordinator.night_mode is not NotImplemented:
            self._attr_preset_modes.append(MODE_NIGHT)

        self._attr_supported_features = FanEntityFeature.SET_SPEED | FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
        if self._attr_preset_modes:
            self._attr_supported_features |= FanEntityFeature.PRESET_MODE

        super().__init__("Fan", coordinator)

    @property
    def is_on(self) -> int:
        return self.coordinator.is_on

    @property
    def percentage(self) -> int:
        """Return the current speed percentage."""
        if self.preset_mode is None:
          return int(round(self.coordinator.fan_speed * 33.33, 0))
        else:
          return None

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

        if self.coordinator.fan_auto_mode is True:
            await self.coordinator.set_fan_auto_mode(False)
        if self.coordinator.night_mode is True:
            await self.coordinator.set_night_mode(False)
        await self.coordinator.set_fan_speed(new_speed)
        self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        if preset_mode == MODE_AUTO:
            await self.coordinator.set_fan_auto_mode(True)
        elif preset_mode == MODE_NIGHT:
            await self.coordinator.set_night_mode(True)

    async def async_turn_off(self, **kwargs: any) -> None:
        await self.coordinator.set_fan_speed("0")
        self.async_write_ha_state()

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: any,
    ) -> None:
        await self.coordinator.set_fan_speed("1")
        if percentage is not None:
            await self.async_set_percentage(percentage=percentage)
        elif preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)
        else:
            self.async_write_ha_state()

    @property
    def speed_count(self) -> int:
        """Return the number of speeds the fan supports."""
        return self.coordinator.speed_count

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode, e.g., auto, smart, interval, favorite."""
        if self.coordinator.fan_auto_mode is True:
            return MODE_AUTO
        if self.coordinator.night_mode is True:
            return MODE_NIGHT
        return None


class BlueairAwsFan(BlueairEntity, FanEntity):
    """Controls Fan."""

    @classmethod
    def is_implemented(kls, coordinator):
        return isinstance(coordinator, BlueairUpdateCoordinatorDeviceAws)

    def __init__(self, coordinator: BlueairUpdateCoordinatorDeviceAws):
        """Initialize the fan entity."""
        self._attr_preset_modes = []
        if coordinator.fan_auto_mode is not NotImplemented:
            self._attr_preset_modes.append(MODE_AUTO)
        if coordinator.night_mode is not NotImplemented:
            self._attr_preset_modes.append(MODE_NIGHT)

        self._attr_supported_features = FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
        if coordinator.fan_speed is not NotImplemented:
            self._attr_supported_features |= FanEntityFeature.SET_SPEED
        if self._attr_preset_modes:
            self._attr_supported_features |= FanEntityFeature.PRESET_MODE

        super().__init__("Fan", coordinator)

    @property
    def is_on(self) -> int:
        return self.coordinator.is_on

    @property
    def percentage(self) -> int:
        """Return the current speed percentage."""
        if self.preset_mode is None:
          return int((self.coordinator.fan_speed * 100) // self.coordinator.speed_count)
        else:
          return None

    async def async_set_percentage(self, percentage: int) -> None:
        if self.coordinator.fan_auto_mode is True:
            await self.coordinator.set_fan_auto_mode(False)
        if self.coordinator.night_mode is True:
            await self.coordinator.set_night_mode(False)
        await self.coordinator.set_fan_speed(int(round(percentage / 100 * self.coordinator.speed_count)))
        self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        if preset_mode == MODE_AUTO:
            await self.coordinator.set_fan_auto_mode(True)
        elif preset_mode == MODE_NIGHT:
            await self.coordinator.set_night_mode(True)

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
        elif preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)
        else:
            self.async_write_ha_state()

    @property
    def speed_count(self) -> int:
        """Return the number of speeds the fan supports."""
        return self.coordinator.speed_count

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode, e.g., auto, smart, interval, favorite."""
        if self.coordinator.fan_auto_mode is True:
            return MODE_AUTO
        if self.coordinator.night_mode is True:
            return MODE_NIGHT
        return None
