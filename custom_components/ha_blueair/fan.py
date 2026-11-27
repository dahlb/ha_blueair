"""Support for Blueair fans."""

from __future__ import annotations

from abc import ABC, abstractmethod
from asyncio import sleep
from collections.abc import Awaitable, Callable, Mapping
import logging
import math
from typing import Any

from blueair_api import AP_SUB_MODE_LABELS
from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util.percentage import percentage_to_ranged_value, ranged_value_to_percentage

from . import BlueairConfigEntry
from .const import (
    CONF_NIGHT_PRESET,
    DEFAULT_FAN_SPEED_PERCENTAGE,
    DEFAULT_NIGHT_PRESET,
    MODE_AUTO,
    MODE_MANUAL_FAN,
    MODE_NIGHT,
)
from .coordinator import BlueairUpdateCoordinator, Capability
from .coordinator_device import BlueairUpdateCoordinatorDevice
from .coordinator_device_aws import BlueairUpdateCoordinatorDeviceAws
from .entity import BlueairEntity, async_setup_entry_helper

_LOGGER = logging.getLogger(__name__)

# Commands go to Blueair's cloud API; send one at a time.
PARALLEL_UPDATES = 1

# Investigation of the Blueair cloud API responses and AWS IoT
# protocol behavior shows that Signature-family devices pair every
# `apsubmode` write with a `fanspeed` reset to this value (the
# device's lowest manual speed). Mirroring the pattern keeps the
# device's stored manual fan speed at a known low value, so
# returning to manual_fan later starts at a predictable speed.
_SIGNATURE_APSUBMODE_FANSPEED_RESET = 11

# 2-in-1 combo devices (e.g. DH3i) expose a single `mode` field whose
# value selects the operating preset. The mapping follows the device
# firmware's mode enum observed in the Blueair cloud API responses:
# 1=Manual, 2=Auto, 3=Night. Unlike the Signature `apsubmode` path,
# switching to Auto/Night needs no paired fanspeed reset — the device
# manages its own fan speed in those modes and restores it on return
# to Manual.
_COMBO_MODE_TO_LABEL: dict[int, str] = {
    1: MODE_MANUAL_FAN,
    2: MODE_AUTO,
    3: MODE_NIGHT,
}


def _as_int(value: Capability[int]) -> int | None:
    """Return a reported mode value as an int, or None when it can't be read.

    Args:
        value: The value the device reported.

    Returns:
        int | None: The value, or None for None, NotImplemented, or a value
        that isn't a number.
    """
    if value is None or value is NotImplemented:
        return None
    try:
        return int(value)
    except TypeError, ValueError:
        return None


class _PresetFamily(ABC):
    """How one family of AWS fans reports and switches its preset modes.

    Blueair fans switch presets in three different ways (see
    ``_preset_family``); each family keeps its rules in one place so the fan
    entity doesn't branch on the family in every method.
    """

    # Family name for debug logs.
    name: str

    @abstractmethod
    def preset_modes(self, coordinator: BlueairUpdateCoordinatorDeviceAws) -> list[str]:
        """Return the presets the device supports.

        Args:
            coordinator: The device's coordinator.

        Returns:
            list[str]: Preset labels, before the Night option is applied.
        """

    @abstractmethod
    def preset_mode(self, coordinator: BlueairUpdateCoordinatorDeviceAws) -> str | None:
        """Return the active preset.

        Args:
            coordinator: The device's coordinator.

        Returns:
            str | None: The preset label, or None when no preset is active
            or it isn't known yet.
        """

    @abstractmethod
    def shows_speed(self, coordinator: BlueairUpdateCoordinatorDeviceAws) -> bool:
        """Return whether the fan speed is meaningful to show.

        Args:
            coordinator: The device's coordinator.

        Returns:
            bool: False while a preset picks the speed itself.
        """

    @abstractmethod
    async def leave_presets(self, coordinator: BlueairUpdateCoordinatorDeviceAws) -> None:
        """Switch to manual control so the device honors a speed write.

        Args:
            coordinator: The device's coordinator.
        """

    @abstractmethod
    async def set_preset_mode(
        self, coordinator: BlueairUpdateCoordinatorDeviceAws, preset_mode: str
    ) -> None:
        """Switch the device to a preset.

        Args:
            coordinator: The device's coordinator.
            preset_mode: The preset label.
        """


class _ClassicPresets(_PresetFamily):
    """Fans with separate ``automode`` and ``nightmode`` shadow fields."""

    name = "classic"

    def preset_modes(self, coordinator: BlueairUpdateCoordinatorDeviceAws) -> list[str]:
        """Return Auto and Night, for whichever fields the device has.

        Args:
            coordinator: The device's coordinator.

        Returns:
            list[str]: Preset labels.
        """
        preset_modes = []
        if coordinator.fan_auto_mode is not NotImplemented:
            preset_modes.append(MODE_AUTO)
        if coordinator.night_mode is not NotImplemented:
            preset_modes.append(MODE_NIGHT)
        return preset_modes

    def preset_mode(self, coordinator: BlueairUpdateCoordinatorDeviceAws) -> str | None:
        """Return Auto or Night when that field is on.

        Args:
            coordinator: The device's coordinator.

        Returns:
            str | None: The preset label, or None in manual control.
        """
        if coordinator.fan_auto_mode is True:
            return MODE_AUTO
        if coordinator.night_mode is True:
            return MODE_NIGHT
        return None

    def shows_speed(self, coordinator: BlueairUpdateCoordinatorDeviceAws) -> bool:
        """Return True in manual control (no preset active).

        Args:
            coordinator: The device's coordinator.

        Returns:
            bool: Whether the fan speed is meaningful to show.
        """
        return self.preset_mode(coordinator) is None

    async def leave_presets(self, coordinator: BlueairUpdateCoordinatorDeviceAws) -> None:
        """Turn auto and night mode off.

        Args:
            coordinator: The device's coordinator.
        """
        if coordinator.fan_auto_mode is True:
            await coordinator.set_fan_auto_mode(False)
        if coordinator.night_mode is True:
            await coordinator.set_night_mode(False)
            # need to wait when turning off night mode for device to receive message from
            # aws then it sets the speed to what night mode had set and updates aws with
            # that speed, without this wait the following set is overridden by the device
            await sleep(2)

    async def set_preset_mode(
        self, coordinator: BlueairUpdateCoordinatorDeviceAws, preset_mode: str
    ) -> None:
        """Turn auto or night mode on.

        Args:
            coordinator: The device's coordinator.
            preset_mode: The preset label.
        """
        if preset_mode == MODE_AUTO:
            await coordinator.set_fan_auto_mode(True)
        elif preset_mode == MODE_NIGHT:
            await coordinator.set_night_mode(True)


class _ModeFieldPresets(_PresetFamily):
    """Fans that select every preset, manual included, through one mode field."""

    def __init__(
        self,
        name: str,
        labels: Mapping[int, str],
        read: Callable[[BlueairUpdateCoordinatorDeviceAws], Capability[int]],
        write: Callable[[BlueairUpdateCoordinatorDeviceAws, int], Awaitable[None]],
        fan_speed_after_preset: int | None = None,
    ) -> None:
        """Initialize the family.

        Args:
            name: Family name for debug logs.
            labels: Mode field value to preset label; must include
                ``MODE_MANUAL_FAN``.
            read: Returns the device's mode field value.
            write: Writes a mode field value to the device.
            fan_speed_after_preset: Fan speed to write after every preset
                change, if the family needs one.
        """
        self.name = name
        self._labels = labels
        # Reverse lookup: HA preset label -> wire value. Built once at import
        # time; for AP_SUB_MODE_LABELS the library guarantees keys are ints and
        # values are unique (see test_labels_are_unique).
        self._values = {label: value for value, label in labels.items()}
        self._manual = self._values[MODE_MANUAL_FAN]
        self._read = read
        self._write = write
        self._fan_speed_after_preset = fan_speed_after_preset

    def preset_modes(self, coordinator: BlueairUpdateCoordinatorDeviceAws) -> list[str]:
        """Return every labelled mode.

        Args:
            coordinator: The device's coordinator.

        Returns:
            list[str]: Preset labels.
        """
        return list(self._labels.values())

    def preset_mode(self, coordinator: BlueairUpdateCoordinatorDeviceAws) -> str | None:
        """Return the label of the device's mode field value.

        Args:
            coordinator: The device's coordinator.

        Returns:
            str | None: The preset label, or None when the value is unknown.
        """
        value = _as_int(self._read(coordinator))
        return None if value is None else self._labels.get(value)

    def shows_speed(self, coordinator: BlueairUpdateCoordinatorDeviceAws) -> bool:
        """Return True in the manual mode, or while the mode is unknown.

        The speed slider is only meaningful in manual; in the other modes the
        device chooses the speed and a percentage would be misleading.

        Args:
            coordinator: The device's coordinator.

        Returns:
            bool: Whether the fan speed is meaningful to show.
        """
        value = _as_int(self._read(coordinator))
        return value is None or value == self._manual

    async def leave_presets(self, coordinator: BlueairUpdateCoordinatorDeviceAws) -> None:
        """Switch to the manual mode first so the device honors the speed write.

        Skipped if already there to avoid an extraneous shadow write on every
        speed change.

        Args:
            coordinator: The device's coordinator.
        """
        if _as_int(self._read(coordinator)) != self._manual:
            await self._write(coordinator, self._manual)

    async def set_preset_mode(
        self, coordinator: BlueairUpdateCoordinatorDeviceAws, preset_mode: str
    ) -> None:
        """Write the preset's mode field value.

        Args:
            coordinator: The device's coordinator.
            preset_mode: The preset label.
        """
        value = self._values.get(preset_mode)
        if value is None:
            # HA frontend validates against preset_modes before
            # calling us, so this only fires when an automation
            # or service call sends an unknown label. Surface it
            # at debug level so the user can diagnose without
            # having to enable trace-level logging on HA core.
            _LOGGER.debug(
                "BlueairAwsFan: ignoring unknown preset_mode=%r (known: %s)",
                preset_mode,
                list(self._values),
            )
            return
        await self._write(coordinator, value)
        if self._fan_speed_after_preset is not None:
            await coordinator.set_fan_speed(self._fan_speed_after_preset)


_CLASSIC_PRESETS = _ClassicPresets()
# Signature devices: four presets derived from AP_SUB_MODE_LABELS
# (manual_fan / auto / night / eco). Investigation of the Blueair cloud API
# responses and AWS IoT protocol behavior shows that apsubmode writes on
# Signature-family devices are paired with a fanspeed reset (see
# _SIGNATURE_APSUBMODE_FANSPEED_RESET). The slider is hidden in non-manual
# presets, so this write is invisible while the preset is active.
_SIGNATURE_PRESETS = _ModeFieldPresets(
    "Signature",
    AP_SUB_MODE_LABELS,
    lambda coordinator: coordinator.ap_sub_mode,
    lambda coordinator, value: coordinator.set_ap_sub_mode(value),
    fan_speed_after_preset=_SIGNATURE_APSUBMODE_FANSPEED_RESET,
)
# 2-in-1 combo devices: Manual / Auto / Night via combo_mode. Combo devices
# manage their own fan speed in Auto/Night, so no paired fanspeed reset is
# needed (unlike Signature).
_COMBO_PRESETS = _ModeFieldPresets(
    "combo",
    _COMBO_MODE_TO_LABEL,
    lambda coordinator: coordinator.combo_mode,
    lambda coordinator, value: coordinator.set_combo_mode(value),
)


def _preset_family(coordinator: BlueairUpdateCoordinatorDeviceAws) -> _PresetFamily:
    """Return how the device reports and switches its presets.

    Signature-series devices switch presets via ``apsubmode`` and have no
    ``automode`` / ``nightmode`` shadow fields. Currently observed on SP4i
    (and assumed on SP1i / SP3i — same ``blue40`` / ``l_blue40`` capability
    shape). The library's ``AP_SUB_MODE_LABELS`` is intentionally
    Signature-only; T10i / pet_air_pro / 2-in-1 declare ``automode`` and so
    are excluded by this gate — see the constant's docstring in
    ``blueair_api/device_aws.py``. Issues: dahlb/ha_blueair#348 and #261.

    2-in-1 combo devices (e.g. DH3i) switch presets via ``mode``, exposed as
    ``combo_mode``. These devices declare neither ``automode`` nor
    ``nightmode`` shadow fields and have no ``apsubmode``; their
    Manual/Auto/Night presets all ride on ``combo_mode`` (see
    ``_COMBO_MODE_TO_LABEL``). Issue: dahlb/ha_blueair#241.

    Every other device uses separate ``automode`` and ``nightmode`` fields.

    Args:
        coordinator: The device's coordinator.

    Returns:
        _PresetFamily: The device's preset family.
    """
    if (
        coordinator.ap_sub_mode is not NotImplemented
        and coordinator.fan_auto_mode is NotImplemented
        and coordinator.night_mode is NotImplemented
    ):
        return _SIGNATURE_PRESETS
    if coordinator.combo_mode is not NotImplemented:
        return _COMBO_PRESETS
    return _CLASSIC_PRESETS


def _drop_night_if_disabled(
    coordinator: BlueairUpdateCoordinator, preset_modes: list[str]
) -> list[str]:
    """Leave Night out of a fan's presets when the options turn it off."""
    entry = coordinator.config_entry
    if entry is None or entry.options.get(CONF_NIGHT_PRESET, DEFAULT_NIGHT_PRESET):
        return preset_modes
    return [mode for mode in preset_modes if mode != MODE_NIGHT]


def _speed_percentage(coordinator: BlueairUpdateCoordinator) -> int | None:
    """Return the fan speed as a percentage, or None before it's reported.

    Args:
        coordinator: The device's coordinator.

    Returns:
        int | None: The speed as a percentage of the device's speed count.
    """
    speed = coordinator.fan_speed
    if speed is None or speed is NotImplemented:
        return None
    return ranged_value_to_percentage((1, coordinator.speed_count), speed)


def _percentage_speed(coordinator: BlueairUpdateCoordinator, percentage: int) -> int:
    """Return the device fan speed for a percentage.

    Rounds up, so any percentage above 0 gives a speed of at least 1 instead
    of stopping the fan (e.g. 10% on a three-speed fan is speed 1, not 0).

    Args:
        coordinator: The device's coordinator.
        percentage: Requested speed percentage, 0-100.

    Returns:
        int: Fan speed between 0 and the device's speed count.
    """
    if percentage <= 0:
        return 0
    return math.ceil(percentage_to_ranged_value((1, coordinator.speed_count), percentage))


def _is_on(coordinator: BlueairUpdateCoordinator) -> bool | None:
    """Return whether the device is on, or None while it's unknown."""
    is_on = coordinator.is_on
    return is_on if isinstance(is_on, bool) else None


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BlueairConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Blueair fans from config entry."""
    async_setup_entry_helper(
        hass,
        config_entry,
        async_add_entities,
        entity_classes=[
            BlueairFan,
            BlueairAwsFan,
        ],
    )


class BlueairFan(BlueairEntity[BlueairUpdateCoordinatorDevice], FanEntity):
    """Controls Fan."""

    @classmethod
    def is_implemented(cls, coordinator: BlueairUpdateCoordinator) -> bool:
        """Return whether the coordinator supports this entity."""
        return isinstance(coordinator, BlueairUpdateCoordinatorDevice)

    def __init__(self, coordinator: BlueairUpdateCoordinatorDevice) -> None:
        """Initialize the fan entity."""
        # The legacy API can set auto mode but not night mode (the legacy
        # coordinator reports night_mode as NotImplemented), so Auto is the only
        # possible preset.
        self._attr_preset_modes = []
        if coordinator.fan_auto_mode is not NotImplemented:
            self._attr_preset_modes.append(MODE_AUTO)

        self._attr_supported_features = (
            FanEntityFeature.SET_SPEED | FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
        )
        if len(self._attr_preset_modes) > 0:
            self._attr_supported_features |= FanEntityFeature.PRESET_MODE

        super().__init__("Fan", coordinator, "fan")

    @property
    def is_on(self) -> bool | None:
        """Return whether the device is on."""
        return _is_on(self.coordinator)

    @property
    def percentage(self) -> int | None:
        """Return the current speed percentage."""
        if self.preset_mode is None:
            return _speed_percentage(self.coordinator)
        return None

    async def async_set_percentage(self, percentage: int) -> None:
        """Sets fan speed percentage."""
        new_speed = _percentage_speed(self.coordinator, percentage)

        if self.coordinator.fan_auto_mode is True:
            await self.coordinator.set_fan_auto_mode(False)
        await self.coordinator.set_fan_speed(new_speed)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        if preset_mode == MODE_AUTO:
            await self.coordinator.set_fan_auto_mode(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        await self.coordinator.set_fan_speed(0)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn the entity on."""
        if percentage is not None:
            await self.async_set_percentage(percentage=percentage)
        elif preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)
        elif not self.is_on:
            # When already running and nothing is asked for, keep the
            # current speed and mode (issue #390).
            await self.coordinator.set_fan_speed(1)

    @property
    def speed_count(self) -> int:
        """Return the number of speeds the fan supports."""
        return self.coordinator.speed_count

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode, e.g., auto, smart, interval, favorite."""
        if self.coordinator.fan_auto_mode is True:
            return MODE_AUTO
        return None


class BlueairAwsFan(BlueairEntity[BlueairUpdateCoordinatorDeviceAws], FanEntity):
    """Controls Fan."""

    @classmethod
    def is_implemented(cls, coordinator: BlueairUpdateCoordinator) -> bool:
        """Return whether the coordinator supports this entity."""
        return isinstance(coordinator, BlueairUpdateCoordinatorDeviceAws)

    def __init__(self, coordinator: BlueairUpdateCoordinatorDeviceAws) -> None:
        """Initialize the fan entity."""
        self._presets = _preset_family(coordinator)
        preset_modes = self._presets.preset_modes(coordinator)

        if self._presets is not _CLASSIC_PRESETS:
            # One-shot at entity creation so a debug-log session can
            # answer "did this device enter the Signature preset path?"
            # without polling state. Fires once per entity instance
            # (typically once at HA startup / integration reload).
            _LOGGER.debug(
                "BlueairAwsFan(%s): %s preset modes enabled (model=%s, presets=%s)",
                coordinator.id,
                self._presets.name,
                coordinator.model,
                preset_modes,
            )

        self._attr_preset_modes = _drop_night_if_disabled(coordinator, preset_modes)

        self._attr_supported_features = FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
        if coordinator.fan_speed is not NotImplemented:
            self._attr_supported_features |= FanEntityFeature.SET_SPEED
        if len(self._attr_preset_modes) > 0:
            self._attr_supported_features |= FanEntityFeature.PRESET_MODE

        super().__init__("Fan", coordinator, "fan")

    @property
    def is_on(self) -> bool | None:
        """Return whether the device is on."""
        return _is_on(self.coordinator)

    @property
    def percentage(self) -> int | None:
        """Return the current speed percentage."""
        # In a preset the device picks the speed and the percentage UI is
        # actively misleading.
        if not self._presets.shows_speed(self.coordinator):
            return None
        return _speed_percentage(self.coordinator)

    async def _async_power_on_if_off(self) -> bool:
        """Leave standby when the device reports it is off.

        Setting a speed or a preset on an off purifier should turn it on, as
        Home Assistant's fan model expects (the HomeKit Bridge relies on it,
        issue #443). An unknown power state is left alone.

        Returns:
            bool: True if the device was off and a power-on was sent.
        """
        if self.is_on is not False:
            return False
        _LOGGER.debug("BlueairAwsFan(%s): powering on before the command", self.coordinator.id)
        await self.coordinator.set_running(True)
        return True

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the fan speed percentage, turning the device on if it is off.

        Args:
            percentage: Requested speed percentage, 0-100. 0 only writes a
                speed of 0 and does not turn the device on.
        """
        if percentage > 0:
            await self._async_power_on_if_off()
        await self._presets.leave_presets(self.coordinator)
        await self.coordinator.set_fan_speed(_percentage_speed(self.coordinator, percentage))

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan, turning the device on if it is off.

        Args:
            preset_mode: The preset label.
        """
        await self._async_power_on_if_off()
        await self._presets.set_preset_mode(self.coordinator, preset_mode)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        await self.coordinator.set_running(False)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn the entity on."""
        was_off = await self._async_power_on_if_off()
        if preset_mode is not None:
            await self.async_set_preset_mode(preset_mode=preset_mode)
        elif percentage is not None:
            await self.async_set_percentage(percentage=percentage)
        elif (
            was_off
            and self.preset_mode in (None, MODE_MANUAL_FAN)
            and self.coordinator.fan_speed in (None, 0)
        ):
            # NOTE: i35 (and probably others) do not remember the
            # last fan speed and always set the speed to 0. I don't know
            # where to store the last fan speed such that it persists across
            # HA reboots. Thus we set the default turn_on fan speed to 50%
            # to make sure the fan actually spins at all.
            await self.async_set_percentage(percentage=DEFAULT_FAN_SPEED_PERCENTAGE)
        # Otherwise a plain turn on resumes whatever the device was doing
        # (auto, night, its last speed) instead of forcing 50%, and
        # leaves an already-running fan alone (issue #390).

    @property
    def speed_count(self) -> int:
        """Return the number of speeds the fan supports."""
        return self.coordinator.speed_count

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode, e.g., auto, smart, interval, favorite."""
        return self._presets.preset_mode(self.coordinator)
