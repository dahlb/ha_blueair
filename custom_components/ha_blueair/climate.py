"""Create climate platform."""

from logging import Logger, getLogger
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    UnitOfTemperature,
    PRECISION_HALVES,
    PRECISION_WHOLE,
)
from homeassistant.config_entries import ConfigEntry

from . import BlueairUpdateCoordinatorDeviceAws
from .blueair_update_coordinator import BlueairUpdateCoordinator
from .const import (
    FanMode,
)
from .entity import BlueairEntity, async_setup_entry_helper

_LOGGER: Logger = getLogger(__package__)

SUPPORT_FLAGS = (
    ClimateEntityFeature.TURN_ON
    | ClimateEntityFeature.TURN_OFF
    | ClimateEntityFeature.TARGET_TEMPERATURE
    | ClimateEntityFeature.FAN_MODE
)


async def async_setup_entry(hass, config_entry: ConfigEntry, async_add_entities):
    """Set up the Blueair climate from config entry."""
    async_setup_entry_helper(hass, config_entry, async_add_entities,
        entity_classes=[
            BlueairThermostat,
    ])


def fan_mode_from_int(fan_speed: int) -> str:
    """Convert fan speed from int to str.  11/37/64/91"""
    if fan_speed < 12:
        return FanMode.STEP1.value
    elif fan_speed < 38:
        return FanMode.STEP2.value
    elif fan_speed < 65:
        return FanMode.STEP3.value
    else:
        return FanMode.STEP4.value


class BlueairThermostat(BlueairEntity, ClimateEntity):
    @classmethod
    def is_implemented(kls, coordinator: BlueairUpdateCoordinator) -> bool:
        return coordinator.main_mode is not NotImplemented and coordinator.temperature is not NotImplemented

    _attr_supported_features = SUPPORT_FLAGS
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(self, coordinator: BlueairUpdateCoordinatorDeviceAws):
        """Initialize the temperature sensor."""
        super().__init__("Climate", coordinator)
        self._attr_fan_modes = [
            fan_mode.value for fan_mode in FanMode
        ]
        self._attr_hvac_modes = [
            HVACMode.OFF,
            HVACMode.FAN_ONLY,
            HVACMode.HEAT,
            HVACMode.COOL,
        ]
    @property
    def current_humidity(self) -> int | None:
        """Return current humidity."""
        return self.coordinator.humidity

    @property
    def current_temperature(self) -> float | None:
        """Return current temperature."""
        return self.coordinator.temperature

    @property
    def temperature_unit(self) -> str:
        """Return temperature unit constant."""
        if self.coordinator.temperature_unit == 1:
            return UnitOfTemperature.CELSIUS
        else:
            return UnitOfTemperature.FAHRENHEIT

    @property
    def hvac_mode(self) -> HVACMode | str | None:
        """Return hvac mode."""
        if self.coordinator.is_on is False:
            return HVACMode.OFF
        ha_mode = None
        match self.coordinator.main_mode:
            case 0:
                ha_mode = HVACMode.FAN_ONLY
            case 1:
                ha_mode = HVACMode.HEAT
            case 2:
                ha_mode = HVACMode.COOL
        return ha_mode

    @property
    def target_temperature_step(self) -> float:
        if self.temperature_unit == UnitOfTemperature.CELSIUS:
            return PRECISION_HALVES
        else:
            return PRECISION_WHOLE

    @property
    def target_temperature(self) -> float | None:
        """Return target temperature."""
        if self.hvac_mode == HVACMode.HEAT:
            return self.coordinator.heat_temp
        return None


    @property
    def fan_mode(self) -> str | None:
        """Return fan mode."""
        match self.hvac_mode:
            case HVACMode.FAN_ONLY:
                if self.coordinator.ap_sub_mode == 2:
                    return FanMode.AUTO.value
                else:
                    return fan_mode_from_int(self.coordinator.fan_speed_0)
            case HVACMode.HEAT:
                if self.coordinator.heat_sub_mode == 2:
                    return FanMode.AUTO.value
                else:
                    return fan_mode_from_int(self.coordinator.heat_fan_speed)
            case HVACMode.COOL:
                if self.coordinator.cool_sub_mode == 2:
                    return FanMode.AUTO.value
                else:
                    return fan_mode_from_int(self.coordinator.heat_fan_speed)

    def set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Update hvac mode."""
        _LOGGER.debug(f"set_hvac_mode; hvac_mode:{hvac_mode}")
        if hvac_mode in [HVACMode.DRY, HVACMode.HEAT_COOL, HVACMode.AUTO]:
            return
        if hvac_mode == HVACMode.OFF:
            if self.coordinator.is_on:
                self.coordinator.set_running(False)
            return
        mode = 0
        match hvac_mode.strip().lower():
            case HVACMode.COOL:
                mode = 2
            case HVACMode.HEAT:
                mode = 1
            case HVACMode.FAN_ONLY:
                mode = 0
            case _:
                _LOGGER.warning(f"set_hvac_mode; unknown hvac_mode:{hvac_mode}")
        if not self.coordinator.is_on:
            self.coordinator.set_running(True)
        self.coordinator.set_main_mode(mode)

    def set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode."""
        _LOGGER.debug(f"set_fan_mode; fan_mode:{fan_mode}")
        fan_speed = 0
        match fan_mode:
            case FanMode.AUTO.value:
                match self.hvac_mode:
                    case HVACMode.FAN_ONLY:
                        self.coordinator.set_ap_sub_mode(2)
                    case HVACMode.HEAT:
                        self.coordinator.set_heat_sub_mode(2)
                    case HVACMode.COOL:
                        self.coordinator.set_cool_sub_mode(2)
                return
            case FanMode.STEP1.value:
                fan_speed = 11
            case FanMode.STEP2.value:
                fan_speed = 37
            case FanMode.STEP3.value:
                fan_speed = 64
            case FanMode.STEP4.value:
                fan_speed = 91
        match self.hvac_mode:
            case HVACMode.FAN_ONLY:
                _LOGGER.debug(f"set_fan_mode; set_fan_speed_0:{fan_speed}")
                self.coordinator.set_fan_speed_0(fan_speed)
            case HVACMode.HEAT:
                _LOGGER.debug(f"set_fan_mode; set_heat_fan_speed:{fan_speed}")
                self.coordinator.set_heat_fan_speed(fan_speed)
            case HVACMode.COOL:
                _LOGGER.debug(f"set_fan_mode; set_cool_fan_speed:{fan_speed}")
                self.coordinator.set_cool_fan_speed(fan_speed)

    def set_temperature(self, **kwargs) -> None:
        """Set temperatures."""
        _LOGGER.debug(f"set_temperature; kwargs:{kwargs}")
        temperature = kwargs.get(ATTR_TEMPERATURE)
        self.coordinator.set_heat_temp(temperature)
