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
from .blueair_update_coordinator_device_aws import BlueairUpdateCoordinatorDeviceAws
from .const import DATA_AWS_DEVICES, MODE_WICK_DRY
from .entity import BlueairEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Blueair humidifier from config entry, but only if the device type name is Humidifier. I'm not sure if we should look for the specific model, as blueair might add new types of humidifiers in the future"""

    data = hass.data[DOMAIN]
    aws_devices = data[DATA_AWS_DEVICES]

    humidifier_devices = []

    for device in aws_devices:
        api_device = device.blueair_api_device
        _LOGGER.debug(
            f"Found device: name={api_device.name}, "
            f"type_name={api_device.type_name}, "
            f"sku={api_device.sku}"
        )

        if api_device.type_name == "Humidifier":
            humidifier_devices.append(device)

    if not humidifier_devices:
        _LOGGER.debug("No humidifier devices found")
        return

    async_add_entities(
        BlueairAwsHumidifier(coordinator) for coordinator in humidifier_devices
    )


class BlueairAwsHumidifier(BlueairEntity, HumidifierEntity):
    """Controls Humidifier."""

    @classmethod
    def is_implemented(kls, coordinator):
        return isinstance(coordinator, BlueairUpdateCoordinatorDeviceAws)

    def __init__(self, coordinator: BlueairUpdateCoordinatorDeviceAws):
        """Initialize the humidifer."""
        super().__init__("Humidifier", coordinator)
        return None

    @property
    def should_poll(self) -> bool:
        """No polling needed with coordinator."""
        return False

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
        # if self.coordinator.fan_speed is not NotImplemented:
        # features |= HumidifierEntityFeature.SET_SPEED
        # return features

    @property
    def available_modes(self):
        return [MODE_AUTO, MODE_SLEEP, MODE_NORMAL, MODE_WICK_DRY]

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
        if self.coordinator.humidity is None:
            return None
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
            await self.coordinator.set_fan_auto_mode(True)
            self.async_write_ha_state()
        elif mode == MODE_WICK_DRY:
            await self.coordinator.set_wick_dry_mode(True)
            self.async_write_ha_state()
        elif mode == MODE_SLEEP:
            await self.coordinator.set_night_mode(True)
            self.async_write_ha_state()
        elif mode == MODE_NORMAL:
            await self.coordinator.set_fan_auto_mode(False)
            await self.coordinator.set_night_mode(True)
            await self.coordinator.set_running(True)

            self.async_write_ha_state()
        else:
            raise ValueError(f"Invalid mode: {mode}")

    async def async_set_humidity(self, humidity):
        """Set the humidity level. Sets Humidifier to 'On' to comply with hass requirements, and sets mode to Auto since this is the only mode in which the target humidity is used."""

        await self.coordinator.set_auto_regulated_humidity(humidity)
        await self.coordinator.set_fan_auto_mode(True)
        await self.async_turn_on()
