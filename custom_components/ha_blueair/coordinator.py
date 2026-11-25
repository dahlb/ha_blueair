"""Blueair device object."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Coroutine
from datetime import timedelta
import logging
from types import NotImplementedType
from typing import Any

from aiohttp import ClientError
from blueair_api import Device as BlueAirApiDevice, DeviceAws as BlueAirAwsDevice, LoginError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import (
    REQUEST_REFRESH_DEFAULT_COOLDOWN,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# A device capability's value: NotImplemented when the model lacks the
# feature, None when the device hasn't reported it yet.
type Capability[T] = T | NotImplementedType | None


class BlueairUpdateCoordinator(ABC, DataUpdateCoordinator[str]):
    """Blueair device object.

    The coordinator's data is the device's string form, so an update that
    changes nothing doesn't write entity states (always_update=False).
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        blueair_api_device: BlueAirApiDevice | BlueAirAwsDevice,
        interval: int,
    ) -> None:
        """Initialize the device.

        Args:
            hass: Home Assistant instance.
            config_entry: Config entry of the Blueair account the device belongs to;
                passed explicitly so a rejected login can start reauthentication.
            blueair_api_device: blueair_api device this coordinator polls.
            interval: Polling interval in minutes.
        """
        self.hass: HomeAssistant = hass
        self.blueair_api_device = blueair_api_device
        # Set while MQTT pushes this device's state changes (AWS devices only).
        self.mqtt_connected = False
        request_refresh_debouncer: Debouncer[Coroutine[Any, Any, None]] = Debouncer(
            hass,
            _LOGGER,
            cooldown=REQUEST_REFRESH_DEFAULT_COOLDOWN,
            immediate=False,
        )

        async def refresh() -> str:
            """Poll the device, translating failures for DataUpdateCoordinator.

            A rejected login raises ConfigEntryAuthFailed, which starts
            reauthentication. Any other API or transport failure raises
            UpdateFailed, so the coordinator logs the outage once and its
            recovery once instead of a stack trace on every failed poll.

            Returns:
                str: The device state, compared to skip no-op updates.

            Raises:
                ConfigEntryAuthFailed: Blueair rejected the stored credentials.
                UpdateFailed: Blueair could not be reached or returned an error.
            """
            try:
                await self.blueair_api_device.refresh()
            except LoginError as error:
                raise ConfigEntryAuthFailed(
                    translation_domain=DOMAIN, translation_key="auth_failed"
                ) from error
            except (ClientError, TimeoutError) as error:
                # blueair_api's errors are ClientError subclasses too.
                raise UpdateFailed(
                    translation_domain=DOMAIN,
                    translation_key="update_failed",
                    translation_placeholders={"error": str(error)},
                ) from error
            # The device's name is only known after its first refresh.
            self.name = self._log_name()
            return str(self.blueair_api_device)

        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=self._log_name(),
            update_interval=timedelta(minutes=interval),
            update_method=refresh,
            request_refresh_debouncer=request_refresh_debouncer,
            always_update=False,
        )

    def _log_name(self) -> str:
        """Return the coordinator's name for log messages.

        Includes the device id, so devices sharing a name, or polled before
        their name is known, can still be told apart.

        Returns:
            str: ``ha_blueair-<name> (<id>)``, or ``ha_blueair-<id>`` while the
            device's name is unknown.
        """
        device = self.blueair_api_device
        if device.name:
            return f"{DOMAIN}-{device.name} ({device.uuid})"
        return f"{DOMAIN}-{device.uuid}"

    async def _async_device_command(self, command: Awaitable[Any]) -> None:
        """Await a device command, turning API failures into Home Assistant errors.

        blueair_api stores the new value on the device as it sends the command,
        so after a successful command every entity of the device is updated
        right away instead of waiting for the next refresh (e.g. turning a
        humidifier off also shows its fan as off).

        Args:
            command: The pending blueair_api device call.

        Raises:
            HomeAssistantError: Blueair rejected the login (reauthentication is
                started) or the command could not be delivered.
        """
        try:
            await command
        except LoginError as error:
            if self.config_entry is not None:
                self.config_entry.async_start_reauth(self.hass)
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="auth_failed"
            ) from error
        except (ClientError, TimeoutError) as error:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
                translation_placeholders={"device": self.device_name, "error": str(error)},
            ) from error
        self.async_update_listeners()

    async def _async_refresh_after_command(self) -> None:
        """Poll the device to confirm a command, unless MQTT will push the result.

        blueair_api already stored the command's value and every entity shows
        it (see _async_device_command). While MQTT is connected the device
        pushes its confirmed state, so the poll would only repeat it.
        """
        if self.mqtt_connected:
            return
        await self.async_request_refresh()

    @property
    def id(self) -> str:
        """Return Blueair device id."""
        # blueair_api always sets it; the legacy Device types it optional.
        return self.blueair_api_device.uuid or ""

    @property
    def device_name(self) -> str:
        """Return device name."""
        return self.blueair_api_device.name or ""

    @property
    @abstractmethod
    def model(self) -> str | None:
        """Return model for device, or the UUID if it's not known."""

    @property
    @abstractmethod
    def hw_version(self) -> str | None:
        """Return the hardware version."""

    @property
    @abstractmethod
    def sw_version(self) -> str | None:
        """Return the software version."""

    @property
    @abstractmethod
    def serial_number(self) -> str | None:
        """Return the serial number."""

    @property
    @abstractmethod
    def fan_speed(self) -> Capability[int]:
        """Return the current fan speed."""

    @property
    @abstractmethod
    def speed_count(self) -> int:
        """Return the max fan speed."""

    @property
    @abstractmethod
    def is_on(self) -> Capability[bool]:
        """Return whether the device is on."""

    @property
    def online(self) -> Capability[bool]:
        """Return whether the device is online."""
        return self.blueair_api_device.wifi_working

    @property
    @abstractmethod
    def brightness(self) -> Capability[int]:
        """Return the brightness."""

    @property
    def child_lock(self) -> Capability[bool]:
        """Return whether the child lock is enabled."""
        return self.blueair_api_device.child_lock

    @property
    @abstractmethod
    def germ_shield(self) -> Capability[bool]:
        """Return whether germ shield is enabled."""

    @property
    def night_mode(self) -> Capability[bool]:
        """Return whether night mode is enabled."""
        return self.blueair_api_device.night_mode

    @property
    @abstractmethod
    def temperature(self) -> Capability[float]:
        """Return the temperature."""

    @property
    @abstractmethod
    def humidity(self) -> Capability[int]:
        """Return the humidity."""

    @property
    @abstractmethod
    def voc(self) -> Capability[int]:
        """Return the VOC level."""

    @property
    @abstractmethod
    def pm1(self) -> Capability[int]:
        """Return the PM1 concentration."""

    @property
    @abstractmethod
    def pm10(self) -> Capability[int]:
        """Return the PM10 concentration."""

    @property
    @abstractmethod
    def pm25(self) -> Capability[int]:
        """Return the PM2.5 concentration."""

    @property
    @abstractmethod
    def co2(self) -> Capability[int]:
        """Return the CO2 level."""

    @property
    @abstractmethod
    def fan_auto_mode(self) -> Capability[bool]:
        """Return whether automatic fan mode is enabled."""

    @property
    @abstractmethod
    def wick_dry_mode(self) -> Capability[bool]:
        """Return whether wick dry mode is enabled."""

    @property
    @abstractmethod
    def water_shortage(self) -> Capability[bool]:
        """Return whether the water tank is low."""

    @property
    @abstractmethod
    def filter_expired(self) -> Capability[bool]:
        """Return the current filter status."""

    @property
    @abstractmethod
    def filter_life(self) -> Capability[int]:
        """Return the filter life."""

    @property
    @abstractmethod
    def wick_life(self) -> Capability[int]:
        """Return the wick life."""

    @property
    @abstractmethod
    def main_mode(self) -> Capability[int]:
        """Return the main mode."""

    @property
    @abstractmethod
    def heat_temp(self) -> Capability[float]:
        """Return the heat temp."""

    @property
    @abstractmethod
    def heat_sub_mode(self) -> Capability[int]:
        """Return the heat sub mode."""

    @property
    @abstractmethod
    def heat_fan_speed(self) -> Capability[int]:
        """Return the heat fan speed."""

    @property
    @abstractmethod
    def cool_sub_mode(self) -> Capability[int]:
        """Return the cool sub mode."""

    @property
    @abstractmethod
    def cool_fan_speed(self) -> Capability[int]:
        """Return the cool fan speed."""

    @property
    @abstractmethod
    def ap_sub_mode(self) -> Capability[int]:
        """Return the air purifier sub mode."""

    @property
    @abstractmethod
    def fan_speed_0(self) -> Capability[int]:
        """Return the fan speed 0 value."""

    @property
    @abstractmethod
    def temperature_unit(self) -> Capability[int]:
        """Return the temperature unit."""

    @property
    @abstractmethod
    def water_refresher_life(self) -> Capability[int]:
        """Return the water refresher life."""

    @property
    @abstractmethod
    def water_level(self) -> Capability[int]:
        """Return the water level."""

    @property
    @abstractmethod
    def mood_brightness(self) -> Capability[int]:
        """Return the mood brightness."""

    @property
    @abstractmethod
    def auto_regulated_humidity(self) -> Capability[int]:
        """Return the target humidity the device regulates to, in percent."""

    @property
    def humidifier_mode(self) -> Capability[bool]:
        """Return the humidifier mode."""

    @property
    def combo_mode(self) -> Capability[int]:
        """Return the combo mode."""

    # ----- AWS-only sensor attributes (issue #356) -----
    # Declared abstract so any subclass MUST provide a value (legacy
    # subclasses return NotImplemented).  Prevents the v1.49.0 regression
    # where AWS-only properties weren't stubbed on the legacy coordinator,
    # causing AttributeError in sensor is_implemented() checks.

    @property
    @abstractmethod
    def timer_duration(self) -> Capability[int]:
        """Return the timer duration."""

    @property
    @abstractmethod
    def timer_state(self) -> Capability[int]:
        """Return the timer state."""

    @property
    @abstractmethod
    def rssi(self) -> Capability[int]:
        """Return the Wi-Fi signal strength (RSSI)."""

    @property
    @abstractmethod
    def night_light_brightness(self) -> Capability[int]:
        """Return the night light brightness."""

    @property
    @abstractmethod
    def hour_format(self) -> Capability[bool]:
        """Return the clock hour format setting."""

    @abstractmethod
    async def set_fan_speed(self, new_speed: int) -> None:
        """Set the fan speed."""

    @abstractmethod
    async def set_brightness(self, brightness: int) -> None:
        """Set the brightness."""

    @abstractmethod
    async def set_running(self, running: bool) -> None:
        """Turn the device on or off."""

    @abstractmethod
    async def set_germ_shield(self, enabled: bool) -> None:
        """Set the germ shield."""

    async def set_child_lock(self, locked: bool) -> None:
        """Set the child lock."""
        await self._async_device_command(self.blueair_api_device.set_child_lock(locked))
        await self._async_refresh_after_command()

    @abstractmethod
    async def set_night_mode(self, mode: bool) -> None:
        """Set the night mode."""

    @abstractmethod
    async def set_fan_auto_mode(self, value: bool) -> None:
        """Set the fan auto mode."""

    @abstractmethod
    async def set_mood_brightness(self, mood_brightness: int) -> None:
        """Set the mood brightness."""

    @abstractmethod
    async def turn_off_mood_brightness(self) -> None:
        """Turn off the mood light."""

    @abstractmethod
    async def set_night_light_brightness(self, night_light_brightness: int) -> None:
        """Set the night light brightness."""

    @abstractmethod
    async def turn_off_night_light_brightness(self) -> None:
        """Turn off the night light."""

    @abstractmethod
    async def set_wick_dry_mode(self, value: bool) -> None:
        """Set the wick dry mode."""

    @abstractmethod
    async def set_auto_regulated_humidity(self, value: int) -> None:
        """Set the target humidity, in percent."""

    @abstractmethod
    async def set_main_mode(self, value: int) -> None:
        """Set the main mode."""

    @abstractmethod
    async def set_heat_temp(self, value: float) -> None:
        """Set the heat temp."""

    @abstractmethod
    async def set_heat_sub_mode(self, value: int) -> None:
        """Set the heat sub mode."""

    @abstractmethod
    async def set_heat_fan_speed(self, value: int) -> None:
        """Set the heat fan speed."""

    @abstractmethod
    async def set_cool_sub_mode(self, value: int) -> None:
        """Set the cool sub mode."""

    @abstractmethod
    async def set_cool_fan_speed(self, value: int) -> None:
        """Set the cool fan speed."""

    @abstractmethod
    async def set_ap_sub_mode(self, value: int) -> None:
        """Set the air purifier sub mode."""

    @abstractmethod
    async def set_fan_speed_0(self, value: int) -> None:
        """Set the fan speed 0 value."""
