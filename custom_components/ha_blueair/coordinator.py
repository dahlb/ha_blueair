"""Blueair device object."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import timedelta
import logging

from blueair_api import Device as BlueAirApiDevice, DeviceAws as BlueAirAwsDevice
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    REQUEST_REFRESH_DEFAULT_COOLDOWN,
    DataUpdateCoordinator,
    Debouncer,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class BlueairUpdateCoordinator(ABC, DataUpdateCoordinator):
    """Blueair device object."""

    def __init__(
        self,
        hass: HomeAssistant,
        blueair_api_device: BlueAirApiDevice | BlueAirAwsDevice,
        interval: int,
    ) -> None:
        """Initialize the device."""
        self.hass: HomeAssistant = hass
        self.blueair_api_device = blueair_api_device
        request_refresh_debouncer = Debouncer(
            hass,
            _LOGGER,
            cooldown=REQUEST_REFRESH_DEFAULT_COOLDOWN,
            immediate=False,
        )

        async def refresh() -> str:
            await self.blueair_api_device.refresh()
            return str(self.blueair_api_device)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}-{self.blueair_api_device.name}",
            update_interval=timedelta(minutes=interval),
            update_method=refresh,
            request_refresh_debouncer=request_refresh_debouncer,
            always_update=False,
        )

    @property
    def id(self) -> str:
        """Return Blueair device id."""
        return self.blueair_api_device.uuid

    @property
    def device_name(self) -> str:
        """Return device name."""
        return self.blueair_api_device.name

    @property
    @abstractmethod
    def model(self) -> str:
        """Return model for device, or the UUID if it's not known."""

    @property
    @abstractmethod
    def hw_version(self) -> str:
        """Return the hardware version."""

    @property
    @abstractmethod
    def sw_version(self) -> str:
        """Return the software version."""

    @property
    @abstractmethod
    def serial_number(self) -> str:
        """Return the serial number."""

    @property
    def fan_speed(self) -> int:
        """Return the current fan speed."""
        return int(self.blueair_api_device.fan_speed)

    @property
    @abstractmethod
    def speed_count(self) -> int:
        """Return the max fan speed."""

    @property
    @abstractmethod
    def is_on(self) -> bool:
        """Return whether the device is on."""

    @property
    def online(self) -> bool:
        """Return whether the device is online."""
        return self.blueair_api_device.wifi_working

    @property
    @abstractmethod
    def brightness(self) -> int:
        """Return the brightness."""

    @property
    def child_lock(self) -> bool:
        """Return whether the child lock is enabled."""
        return self.blueair_api_device.child_lock

    @property
    @abstractmethod
    def germ_shield(self) -> bool:
        """Return whether germ shield is enabled."""

    @property
    def night_mode(self) -> bool:
        """Return whether night mode is enabled."""
        return self.blueair_api_device.night_mode

    @property
    @abstractmethod
    def temperature(self) -> int:
        """Return the temperature."""

    @property
    @abstractmethod
    def humidity(self) -> int:
        """Return the humidity."""

    @property
    @abstractmethod
    def voc(self) -> int:
        """Return the VOC level."""

    @property
    @abstractmethod
    def pm1(self) -> int:
        """Return the PM1 concentration."""

    @property
    @abstractmethod
    def pm10(self) -> int:
        """Return the PM10 concentration."""

    @property
    @abstractmethod
    def pm25(self) -> int:
        """Return the PM2.5 concentration."""

    @property
    @abstractmethod
    def co2(self) -> int:
        """Return the CO2 level."""

    @property
    @abstractmethod
    def fan_auto_mode(self) -> bool | NotImplemented | None:
        """Return whether automatic fan mode is enabled."""

    @property
    @abstractmethod
    def wick_dry_mode(self) -> bool | NotImplemented | None:
        """Return whether wick dry mode is enabled."""

    @property
    @abstractmethod
    def water_shortage(self) -> bool | NotImplemented | None:
        """Return whether the water tank is low."""

    @property
    @abstractmethod
    def filter_expired(self) -> bool | NotImplemented | None:
        """Return the current filter status."""

    @property
    @abstractmethod
    def filter_life(self) -> int | NotImplemented | None:
        """Return the filter life."""

    @property
    @abstractmethod
    def wick_life(self) -> int | NotImplemented | None:
        """Return the wick life."""

    @property
    @abstractmethod
    def main_mode(self) -> int | NotImplemented | None:
        """Return the main mode."""

    @property
    @abstractmethod
    def heat_temp(self) -> int | NotImplemented | None:
        """Return the heat temp."""

    @property
    @abstractmethod
    def heat_sub_mode(self) -> int | NotImplemented | None:
        """Return the heat sub mode."""

    @property
    @abstractmethod
    def heat_fan_speed(self) -> int | NotImplemented | None:
        """Return the heat fan speed."""

    @property
    @abstractmethod
    def cool_sub_mode(self) -> int | NotImplemented | None:
        """Return the cool sub mode."""

    @property
    @abstractmethod
    def cool_fan_speed(self) -> int | NotImplemented | None:
        """Return the cool fan speed."""

    @property
    @abstractmethod
    def ap_sub_mode(self) -> int | NotImplemented | None:
        """Return the air purifier sub mode."""

    @property
    @abstractmethod
    def fan_speed_0(self) -> int | NotImplemented | None:
        """Return the fan speed 0 value."""

    @property
    @abstractmethod
    def temperature_unit(self) -> int | NotImplemented | None:
        """Return the temperature unit."""

    @property
    @abstractmethod
    def water_refresher_life(self) -> int | NotImplemented | None:
        """Return the water refresher life."""

    @property
    @abstractmethod
    def water_level(self) -> int | NotImplemented | None:
        """Return the water level."""

    @property
    @abstractmethod
    def mood_brightness(self) -> int | NotImplemented | None:
        """Return the mood brightness."""

    @property
    @abstractmethod
    def auto_regulated_humidity(self) -> bool | NotImplemented | None:
        """Return whether automatic humidity regulation is enabled."""

    @property
    def humidifier_mode(self) -> bool | NotImplemented | None:
        """Return the humidifier mode."""

    @property
    def combo_mode(self) -> int | NotImplemented | None:
        """Return the combo mode."""

    # ----- AWS-only sensor attributes (issue #356) -----
    # Declared abstract so any subclass MUST provide a value (legacy
    # subclasses return NotImplemented).  Prevents the v1.49.0 regression
    # where AWS-only properties weren't stubbed on the legacy coordinator,
    # causing AttributeError in sensor is_implemented() checks.

    @property
    @abstractmethod
    def timer_duration(self) -> int | NotImplemented | None:
        """Return the timer duration."""

    @property
    @abstractmethod
    def timer_state(self) -> int | NotImplemented | None:
        """Return the timer state."""

    @property
    @abstractmethod
    def rssi(self) -> int | NotImplemented | None:
        """Return the Wi-Fi signal strength (RSSI)."""

    @property
    @abstractmethod
    def night_light_brightness(self) -> int | NotImplemented | None:
        """Return the night light brightness."""

    @property
    @abstractmethod
    def hour_format(self) -> bool | NotImplemented | None:
        """Return the clock hour format setting."""

    async def set_fan_speed(self, new_speed: int) -> None:
        """Set the fan speed."""
        await self.blueair_api_device.set_fan_speed(new_speed)
        await self.async_request_refresh()

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
        await self.blueair_api_device.set_child_lock(locked)
        await self.async_request_refresh()

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
    async def set_auto_regulated_humidity(self, value: bool) -> None:
        """Set the auto regulated humidity."""

    @abstractmethod
    async def set_main_mode(self, value: int) -> None:
        """Set the main mode."""

    @abstractmethod
    async def set_heat_temp(self, value: int) -> None:
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
