"""Support for Blueair humidifiers."""

from __future__ import annotations

import logging

from homeassistant.components.humidifier import (
    MODE_AUTO,
    MODE_NORMAL,
    MODE_SLEEP,
    HumidifierDeviceClass,
    HumidifierEntity,
    HumidifierEntityFeature,
)

from . import DOMAIN
from .blueair_update_coordinator_device_aws import BlueairUpdateCoordinator
from .const import DATA_AWS_DEVICES, MODE_WICK_DRY
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
        ],
    )


class BlueairAwsHumidifier(BlueairEntity, HumidifierEntity):
    """Controls Humidifier."""

    @classmethod
    def is_implemented(kls, coordinator):
        return coordinator.target_humidity is not NotImplemented

    def __init__(self, coordinator: BlueairUpdateCoordinator):
        """Initialize the humidifer."""
        super().__init__("Humidifier", coordinator)
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.online

    @property
    def device_class(self):
        return HumidifierDeviceClass.HUMIDIFIER

    @property
    def supported_features(self) -> int:
        return HumidifierEntityFeature.MODES

    @property
    def available_modes(self):
        return [MODE_AUTO, MODE_SLEEP, MODE_NORMAL, MODE_WICK_DRY]

    @property
    def translation_key(self):
        return "ha_blueair"

    @property
    def mode(self):
        if self.coordinator.night_mode:
            return MODE_SLEEP
        elif self.coordinator.fan_auto_mode:
            return MODE_AUTO
        elif self.coordinator.wick_dry_mode:
            return MODE_WICK_DRY
        elif self.is_on:
            return MODE_NORMAL
        else:
            return

    @property
    def is_on(self) -> int:
        return self.coordinator.is_on

    @property
    def target_humidity(self):
        _LOGGER.debug(f"Target Humidity: {self.coordinator.target_humidity}")
        return self.coordinator.target_humidity

    @property
    def current_humidity(self):
        return self.coordinator.humidity

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
        self.async_write_ha_state()

    async def async_set_mode(self, mode):
        if mode == MODE_AUTO:
            # This mode doesn't apply when off
            await self.coordinator.set_fan_auto_mode(True)
            await self.coordinator.set_running(True)
            self.async_write_ha_state()
        elif mode == MODE_WICK_DRY:
            # This mode doesn't apply when on
            await self.coordinator.set_wick_dry_mode(True)
            await self.coordinator.set_running(False)
            self.async_write_ha_state()
        elif mode == MODE_SLEEP:
            # This mode doesn't apply when off
            await self.coordinator.set_night_mode(True)
            await self.coordinator.set_fan_auto_mode(False)
            await self.coordinator.set_running(False)
            self.async_write_ha_state()
        elif mode == MODE_NORMAL:
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
