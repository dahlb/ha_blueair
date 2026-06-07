"""Support for Blueair humidifiers."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.humidifier import (
    HumidifierDeviceClass,
    HumidifierEntity,
)
from homeassistant.components.humidifier.const import (
    HumidifierEntityFeature,
    MODE_AUTO,
    MODE_SLEEP,
)

from .blueair_update_coordinator_device_aws import BlueairUpdateCoordinator
from .const import MODE_FAN_SPEED
from .entity import BlueairEntity, async_setup_entry_helper

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Blueair humidifier from config entry"""

    async_setup_entry_helper(
        hass,
        config_entry,
        async_add_entities,
        entity_classes=[
            BlueairAwsHumidifier,
            BlueairAwsComboHumidifier,
        ],
    )


class BlueairAwsHumidifier(BlueairEntity, HumidifierEntity):
    """Controls a standalone humidifier (master power toggles the device)."""

    @classmethod
    def is_implemented(kls, coordinator):
        # Standalone humidifiers only. 2-in-1 combo devices (which expose a
        # dedicated ``humidifier_mode``) are handled by BlueairAwsComboHumidifier so
        # that turning humidification off does not power down the purifier.
        return (
            coordinator.auto_regulated_humidity is not NotImplemented
            and coordinator.humidifier_mode is NotImplemented
        )

    def __init__(self, coordinator: BlueairUpdateCoordinator):
        """Initialize the humidifier."""
        self._attr_device_class = HumidifierDeviceClass.HUMIDIFIER
        self._attr_supported_features = HumidifierEntityFeature.MODES
        self._attr_available_modes = [
            MODE_AUTO,
            MODE_SLEEP,
            MODE_FAN_SPEED,
        ]
        super().__init__("Humidifier", coordinator)

    @property
    def mode(self):
        if self.coordinator.night_mode is True:
            return MODE_SLEEP
        elif self.coordinator.fan_auto_mode is True:
            return MODE_AUTO
        elif self.is_on:
            return MODE_FAN_SPEED
        else:
            return None

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.is_on

    @property
    def target_humidity(self):
        return self.coordinator.auto_regulated_humidity

    @property
    def current_humidity(self):
        return self.coordinator.humidity

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.set_running(False)
        self.async_write_ha_state()

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        await self.coordinator.set_running(True)
        self.async_write_ha_state()

    async def async_set_mode(self, mode):
        if mode == MODE_AUTO:
            # This mode doesn't apply when off
            await self.coordinator.set_fan_auto_mode(True)
            await self.coordinator.set_running(True)
            self.async_write_ha_state()
        elif mode == MODE_SLEEP:
            # This mode doesn't apply when off
            await self.coordinator.set_night_mode(True)
            await self.coordinator.set_fan_auto_mode(False)
            await self.coordinator.set_running(False)
            self.async_write_ha_state()
        elif mode == MODE_FAN_SPEED:
            # This mode doesn't apply when off
            await self.coordinator.set_fan_auto_mode(False)
            await self.coordinator.set_night_mode(False)
            await self.coordinator.set_running(True)

            self.async_write_ha_state()
        else:
            raise ValueError(f"Invalid mode: {mode}")

    async def async_set_humidity(self, humidity):
        """Set the humidity level. Sets Humidifier to 'On' to comply with hass requirements, and sets mode to Auto since this is the only mode in which the target humidity is used."""
        await self.coordinator.set_auto_regulated_humidity(humidity)
        await self.coordinator.set_fan_auto_mode(True)
        await self.async_turn_on()


class BlueairAwsComboHumidifier(BlueairEntity, HumidifierEntity):
    """Controls humidification on a 2-in-1 Purify+Humidify device (e.g. DH3i).

    On these devices humidification is a sub-function of the purifier, toggled
    via ``humidifier_mode`` independently of the device's master power (``standby``).
    Powering the purifier on/off and selecting its operating mode is handled by
    the fan entity, so this entity intentionally exposes only humidification
    on/off plus the target humidity (no modes).
    """

    @classmethod
    def is_implemented(kls, coordinator):
        return coordinator.humidifier_mode is not NotImplemented

    def __init__(self, coordinator: BlueairUpdateCoordinator):
        """Initialize the combo humidifier."""
        self._attr_device_class = HumidifierDeviceClass.HUMIDIFIER
        self._attr_supported_features = HumidifierEntityFeature(0)
        super().__init__("Humidifier", coordinator)

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.humidifier_mode

    @property
    def target_humidity(self):
        return self.coordinator.auto_regulated_humidity

    @property
    def current_humidity(self):
        return self.coordinator.humidity

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.set_humidifier_mode(False)
        self.async_write_ha_state()

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        await self.coordinator.set_humidifier_mode(True)
        self.async_write_ha_state()

    async def async_set_humidity(self, humidity):
        """Set the target humidity and ensure humidification is on."""
        await self.coordinator.set_auto_regulated_humidity(humidity)
        await self.async_turn_on()
