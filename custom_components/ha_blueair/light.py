"""Light platform for Blueair devices."""

from __future__ import annotations

import logging
from typing import ClassVar

from homeassistant.components.light import ATTR_BRIGHTNESS, LightEntity
from homeassistant.components.light.const import ColorMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import BlueairConfigEntry
from .coordinator import BlueairUpdateCoordinator
from .entity import BlueairEntity, async_setup_entry_helper

_LOGGER = logging.getLogger(__name__)
_ATTR_LAST_BRIGHTNESS = "last_brightness"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BlueairConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Blueair sensors from config entry."""
    async_setup_entry_helper(
        hass,
        config_entry,
        async_add_entities,
        entity_classes=[
            BlueairLightEntity,
            BlueairMoodLightEntity,
            BlueairNightLightEntity,
        ],
    )


class BlueairRestoredBrightnessEntity(BlueairEntity, LightEntity, RestoreEntity):
    """Base light entity that retains brightness while the light is off."""

    @property
    def extra_state_attributes(self) -> dict[str, int]:
        """Return the brightness used when the light is next turned on."""
        return {_ATTR_LAST_BRIGHTNESS: self._last_brightness}

    async def async_added_to_hass(self) -> None:
        """Restore the previous brightness after a Home Assistant restart."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if self.is_on:
            return

        if last_state is not None:
            last_brightness = last_state.attributes.get(_ATTR_LAST_BRIGHTNESS)
            if (
                isinstance(last_brightness, int)
                and not isinstance(last_brightness, bool)
                and 0 < last_brightness <= 255
            ):
                self._last_brightness = last_brightness
                return

        self._last_brightness = 255


class BlueairLightEntity(BlueairRestoredBrightnessEntity):
    """Blueair light entity."""

    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes: ClassVar[set[ColorMode]] = {ColorMode.BRIGHTNESS}

    @classmethod
    def is_implemented(cls, coordinator: BlueairUpdateCoordinator) -> bool:
        """Return whether the coordinator supports this entity."""
        return coordinator.brightness is not NotImplemented

    def __init__(self, coordinator: BlueairUpdateCoordinator) -> None:
        """Initialize the blueair light entity."""
        super().__init__("LED Light", coordinator)
        self._last_brightness = self.coordinator.brightness or 255

    @property
    def brightness(self) -> int | None:
        """Return the brightness of this light between 0..255."""
        brightness = self.coordinator.brightness
        if brightness:
            self._last_brightness = brightness
        return brightness

    @property
    def is_on(self) -> bool:
        """Return True if the entity is on."""
        return self.coordinator.brightness != 0

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        desired_brightness = kwargs.get(ATTR_BRIGHTNESS, self._last_brightness)
        if ATTR_BRIGHTNESS in kwargs:
            self._last_brightness = desired_brightness
        await self.coordinator.set_brightness(desired_brightness)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the entity off."""
        await self.coordinator.set_brightness(0)
        self.async_write_ha_state()


class BlueairMoodLightEntity(BlueairRestoredBrightnessEntity):
    """Blueair mood light entity."""

    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes: ClassVar[set[ColorMode]] = {ColorMode.BRIGHTNESS}

    @classmethod
    def is_implemented(cls, coordinator: BlueairUpdateCoordinator) -> bool:
        """Return whether the coordinator supports this entity."""
        return coordinator.mood_brightness is not NotImplemented

    def __init__(self, coordinator: BlueairUpdateCoordinator) -> None:
        """Initialize the blueair mood light entity."""
        super().__init__("Mood Light", coordinator)
        self._last_brightness = self.coordinator.mood_brightness or 255

    @property
    def brightness(self) -> int | None:
        """Return the brightness of this light between 0..255."""
        brightness = self.coordinator.mood_brightness
        if brightness:
            self._last_brightness = brightness
        return brightness

    @property
    def is_on(self) -> bool:
        """Return True if the entity is on."""
        return self.coordinator.mood_brightness_is_on

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        desired_brightness = kwargs.get(ATTR_BRIGHTNESS, self._last_brightness)
        if ATTR_BRIGHTNESS in kwargs:
            self._last_brightness = desired_brightness
        await self.coordinator.set_mood_brightness(desired_brightness)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the entity off."""
        await self.coordinator.turn_off_mood_brightness()
        self.async_write_ha_state()


class BlueairNightLightEntity(BlueairRestoredBrightnessEntity):
    """Blueair night light entity."""

    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes: ClassVar[set[ColorMode]] = {ColorMode.BRIGHTNESS}

    @classmethod
    def is_implemented(cls, coordinator: BlueairUpdateCoordinator) -> bool:
        """Return whether the coordinator supports this entity."""
        return coordinator.night_light_brightness is not NotImplemented

    def __init__(self, coordinator: BlueairUpdateCoordinator) -> None:
        """Initialize the blueair night light entity."""
        super().__init__("Night Light", coordinator)
        self._last_brightness = self.coordinator.night_light_brightness or 255

    @property
    def brightness(self) -> int | None:
        """Return the brightness of this light between 0..255."""
        brightness = self.coordinator.night_light_brightness
        if brightness:
            self._last_brightness = brightness
        return brightness

    @property
    def is_on(self) -> bool:
        """Return True if the entity is on."""
        return self.coordinator.night_light_brightness_is_on

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        desired_brightness = kwargs.get(ATTR_BRIGHTNESS, self._last_brightness)
        if ATTR_BRIGHTNESS in kwargs:
            self._last_brightness = desired_brightness
        await self.coordinator.set_night_light_brightness(desired_brightness)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the entity off."""
        await self.coordinator.turn_off_night_light_brightness()
        self.async_write_ha_state()
