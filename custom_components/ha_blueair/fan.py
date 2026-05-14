"""Support for Blueair fans."""
from __future__ import annotations

import logging
from asyncio import sleep
from homeassistant.components.fan import (
    FanEntity,
    FanEntityFeature,
)

from blueair_api import AP_SUB_MODE_LABELS

from .blueair_update_coordinator import BlueairUpdateCoordinator
from .const import (
    DEFAULT_FAN_SPEED_PERCENTAGE,
    MODE_AUTO,
    MODE_MANUAL_FAN,
    MODE_NIGHT,
)
from .blueair_update_coordinator_device import BlueairUpdateCoordinatorDevice
from .blueair_update_coordinator_device_aws import BlueairUpdateCoordinatorDeviceAws
from .entity import BlueairEntity, async_setup_entry_helper

_LOGGER = logging.getLogger(__name__)

# Reverse lookup for AP_SUB_MODE_LABELS: HA preset label -> apsubmode
# wire value. Built once at import time; the library guarantees keys
# are ints and values are unique (see test_labels_are_unique).
_LABEL_TO_AP_SUB_MODE: dict[str, int] = {
    label: value for value, label in AP_SUB_MODE_LABELS.items()
}

# Investigation of the Blueair cloud API responses and AWS IoT
# protocol behavior shows that Signature-family devices pair every
# `apsubmode` write with a `fanspeed` reset to this value (the
# device's lowest manual speed). Mirroring the pattern keeps the
# device's stored manual fan speed at a known low value, so
# returning to manual_fan later starts at a predictable speed.
_SIGNATURE_APSUBMODE_FANSPEED_RESET = 11


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
        if len(self._attr_preset_modes) > 0:
            self._attr_supported_features |= FanEntityFeature.PRESET_MODE

        super().__init__("Fan", coordinator)

    @property
    def is_on(self) -> int:
        return self.coordinator.is_on

    @property
    def percentage(self) -> int | None:
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
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: any) -> None:
        await self.coordinator.set_fan_speed("0")
        self.async_write_ha_state()

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: any,
    ) -> None:
        if percentage is not None:
            await self.async_set_percentage(percentage=percentage)
        elif preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)
        else:
            await self.coordinator.set_fan_speed("1")
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

    @staticmethod
    def _supports_signature_presets(coordinator) -> bool:
        """True for Blueair Signature-series devices that switch presets
        via ``apsubmode`` (no ``automode`` / ``nightmode`` shadow fields).

        Currently observed on SP4i (and assumed on SP1i / SP3i — same
        ``blue40`` / ``l_blue40`` capability shape). The library's
        ``AP_SUB_MODE_LABELS`` is intentionally Signature-only;
        T10i / pet_air_pro / 2-in-1 declare ``automode`` and so are
        excluded by this gate — see the constant's docstring in
        ``blueair_api/device_aws.py``.

        Issues: dahlb/ha_blueair#348 and #261.
        """
        return (
            coordinator.ap_sub_mode is not NotImplemented
            and coordinator.fan_auto_mode is NotImplemented
            and coordinator.night_mode is NotImplemented
        )

    def __init__(self, coordinator: BlueairUpdateCoordinatorDeviceAws):
        """Initialize the fan entity."""
        self._signature_presets = self._supports_signature_presets(coordinator)

        if self._signature_presets:
            # One-shot at entity creation so a debug-log session can
            # answer "did this device enter the Signature preset path?"
            # without polling state. Fires once per entity instance
            # (typically once at HA startup / integration reload).
            _LOGGER.debug(
                "BlueairAwsFan(%s): Signature preset modes enabled "
                "(model=%s, presets=%s)",
                getattr(coordinator.blueair_api_device, "uuid", "?"),
                coordinator.model,
                list(AP_SUB_MODE_LABELS.values()),
            )

        self._attr_preset_modes = []
        if self._signature_presets:
            # Signature devices: four presets derived from
            # AP_SUB_MODE_LABELS (manual_fan / auto / night / eco).
            self._attr_preset_modes = list(AP_SUB_MODE_LABELS.values())
        else:
            if coordinator.fan_auto_mode is not NotImplemented:
                self._attr_preset_modes.append(MODE_AUTO)
            if coordinator.night_mode is not NotImplemented:
                self._attr_preset_modes.append(MODE_NIGHT)

        self._attr_supported_features = FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
        if coordinator.fan_speed is not NotImplemented:
            self._attr_supported_features |= FanEntityFeature.SET_SPEED
        if len(self._attr_preset_modes) > 0:
            self._attr_supported_features |= FanEntityFeature.PRESET_MODE

        super().__init__("Fan", coordinator)

    @property
    def is_on(self) -> int:
        return self.coordinator.is_on

    @property
    def percentage(self) -> int | None:
        """Return the current speed percentage."""
        if self._signature_presets:
            # On Signature devices the user only sees a meaningful speed
            # value while in manual_fan (apsubmode=0). In auto/night/eco
            # the device picks the speed and the percentage UI is
            # actively misleading.
            ap_sub_mode = self.coordinator.ap_sub_mode
            if ap_sub_mode in (None, NotImplemented):
                manual = True
            else:
                try:
                    manual = int(ap_sub_mode) == _LABEL_TO_AP_SUB_MODE[MODE_MANUAL_FAN]
                except (TypeError, ValueError):
                    manual = True
            if not manual:
                return None
            if self.coordinator.fan_speed in (None, NotImplemented):
                return None
            return int((self.coordinator.fan_speed * 100) // self.coordinator.speed_count)

        if self.preset_mode is None:
          return int((self.coordinator.fan_speed * 100) // self.coordinator.speed_count)
        else:
          return None

    async def async_set_percentage(self, percentage: int) -> None:
        if self._signature_presets:
            # Switch into manual_fan first so the device honors the
            # percentage write. Skipped if already there to avoid an
            # extraneous shadow write on every speed change.
            manual_value = _LABEL_TO_AP_SUB_MODE[MODE_MANUAL_FAN]
            ap_sub_mode = self.coordinator.ap_sub_mode
            try:
                already_manual = (
                    ap_sub_mode not in (None, NotImplemented)
                    and int(ap_sub_mode) == manual_value
                )
            except (TypeError, ValueError):
                already_manual = False
            if not already_manual:
                await self.coordinator.set_ap_sub_mode(manual_value)
            blueair_percentage = int(round(percentage / 100 * self.coordinator.speed_count))
            await self.coordinator.set_fan_speed(blueair_percentage)
            self.async_write_ha_state()
            return

        if self.coordinator.fan_auto_mode is True:
            await self.coordinator.set_fan_auto_mode(False)
        if self.coordinator.night_mode is True:
            await self.coordinator.set_night_mode(False)
            # need to wait when turning off night mode for device to receive message from aws then it sets the speed to what night mode had set and updates aws with that speed, without this wait the following set is overridden by the device
            await sleep(2)
        blueair_percentage = int(round(percentage / 100 * self.coordinator.speed_count))
        await self.coordinator.set_fan_speed(blueair_percentage)
        self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        if self._signature_presets:
            value = _LABEL_TO_AP_SUB_MODE.get(preset_mode)
            if value is None:
                # HA frontend validates against preset_modes before
                # calling us, so this only fires when an automation
                # or service call sends an unknown label. Surface it
                # at debug level so the user can diagnose without
                # having to enable trace-level logging on HA core.
                _LOGGER.debug(
                    "BlueairAwsFan: ignoring unknown preset_mode=%r "
                    "(known: %s)",
                    preset_mode, list(_LABEL_TO_AP_SUB_MODE),
                )
                return
            await self.coordinator.set_ap_sub_mode(value)
            # Investigation of the Blueair cloud API responses and AWS
            # IoT protocol behavior shows that apsubmode writes on
            # Signature-family devices are paired with a fanspeed
            # reset (see _SIGNATURE_APSUBMODE_FANSPEED_RESET docstring).
            # The slider is hidden in non-manual presets, so this write
            # is invisible while the preset is active.
            await self.coordinator.set_fan_speed(_SIGNATURE_APSUBMODE_FANSPEED_RESET)
            self.async_write_ha_state()
            return

        if preset_mode == MODE_AUTO:
            await self.coordinator.set_fan_auto_mode(True)
        elif preset_mode == MODE_NIGHT:
            await self.coordinator.set_night_mode(True)
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
        if self.is_on is False:
            await self.coordinator.set_running(True)
        if percentage is None:
            # FIXME: i35 (and probably others) do not remember the
            # last fan speed and always set the speed to 0. I don't know
            # where to store the last fan speed such that it persists across
            # HA reboots. Thus we set the default turn_on fan speed to 50%
            # to make sure the fan actually spins at all.
            percentage = DEFAULT_FAN_SPEED_PERCENTAGE
        if preset_mode is not None:
            await self.async_set_preset_mode(preset_mode=preset_mode)
        elif percentage is not None:
            await self.async_set_percentage(percentage=percentage)
        else:
            self.async_write_ha_state()

    @property
    def speed_count(self) -> int:
        """Return the number of speeds the fan supports."""
        return self.coordinator.speed_count

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode, e.g., auto, smart, interval, favorite."""
        if self._signature_presets:
            ap_sub_mode = self.coordinator.ap_sub_mode
            if ap_sub_mode in (None, NotImplemented):
                return None
            try:
                return AP_SUB_MODE_LABELS.get(int(ap_sub_mode))
            except (TypeError, ValueError):
                return None

        if self.coordinator.fan_auto_mode is True:
            return MODE_AUTO
        if self.coordinator.night_mode is True:
            return MODE_NIGHT
        return None
