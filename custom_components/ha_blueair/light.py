from __future__ import annotations
from math import ceil
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    LightEntity,
)
from homeassistant.components.light.const import (
    ColorMode
)
import logging

from .entity import BlueairEntity, async_setup_entry_helper

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Blueair sensors from config entry."""
    async_setup_entry_helper(hass, config_entry, async_add_entities,
        entity_classes=[
            BlueairLightEntity,
            BlueairMoodLightEntity,
    ])


class BlueairLightEntity(BlueairEntity, LightEntity):
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    @classmethod
    def is_implemented(kls, coordinator):
        return coordinator.brightness is not NotImplemented

    def __init__(self, coordinator):
        super().__init__("LED Light", coordinator)

    @property
    def brightness(self) -> int | None:
        """Return the brightness of this light between 0..255."""
        return self.coordinator.brightness

    @property
    def is_on(self) -> bool:
        """Return True if the entity is on."""
        return self.coordinator.brightness != 0

    async def async_turn_on(self, **kwargs):
        if ATTR_BRIGHTNESS in kwargs:
            await self.coordinator.set_brightness(kwargs[ATTR_BRIGHTNESS])
        else:
            await self.coordinator.set_brightness(255)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self.coordinator.set_brightness(0)
        self.async_write_ha_state()

class BlueairMoodLightEntity(BlueairEntity, LightEntity):
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    @classmethod
    def is_implemented(kls, coordinator):
        return coordinator.mood_brightness is not NotImplemented

    def __init__(self, coordinator):
        super().__init__("Mood Light", coordinator)

    @property
    def brightness(self) -> int | None:
        """Return the brightness of this light between 0..255."""
        return self.coordinator.mood_brightness

    @property
    def is_on(self) -> bool:
        """Return True if the entity is on."""
        return self.coordinator.mood_brightness_is_on

    async def async_turn_on(self, **kwargs):
        if ATTR_BRIGHTNESS in kwargs:
            desired_brightness = kwargs[ATTR_BRIGHTNESS]
        else:
            desired_brightness = 255
        await self.coordinator.set_mood_brightness(desired_brightness)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self.coordinator.turn_off_mood_brightness()
        self.async_write_ha_state()
