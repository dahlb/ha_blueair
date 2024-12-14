from __future__ import annotations

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
)
import logging

from .const import DOMAIN, DATA_AWS_DEVICES, DATA_DEVICES
from .blueair_data_update_coordinator import BlueairDataUpdateCoordinator
from .entity import BlueairEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Blueair sensors from config entry."""
    coordinators: list[BlueairDataUpdateCoordinator] = hass.data[DOMAIN][DATA_DEVICES]
    entities = []
    for coordinator in coordinators:
        entities.extend(
            [
                BlueairLightEntity(coordinator),
            ]
        )
    async_add_entities(entities)

    aws_coordinators: list[BlueairDataUpdateCoordinator] = hass.data[DOMAIN][
        DATA_AWS_DEVICES
    ]
    entities = []
    for coordinator in aws_coordinators:
        entities.extend(
            [
                BlueairLightEntity(coordinator),
            ]
        )
    async_add_entities(entities)


class BlueairLightEntity(BlueairEntity, LightEntity):
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    def __init__(self, coordinator):
        super().__init__("LED Light", coordinator)

    @property
    def brightness(self) -> int | None:
        """Return the brightness of this light between 0..255."""
        return round(self.coordinator.brightness / 100 * 255.0, 0)

    @property
    def is_on(self) -> bool:
        """Return True if the entity is on."""
        return self.coordinator.brightness != 0

    async def async_turn_on(self, **kwargs):
        if ATTR_BRIGHTNESS in kwargs:
            # Convert Home Assistant brightness (0-255) to Abode brightness (0-99)
            # If 100 is sent to Abode, response is 99 causing an error
            await self.coordinator.set_brightness(
                round(kwargs[ATTR_BRIGHTNESS] * 100 / 255.0)
            )
        else:
            await self.coordinator.set_brightness(100)

    async def async_turn_off(self, **kwargs):
        await self.coordinator.set_brightness(0)
