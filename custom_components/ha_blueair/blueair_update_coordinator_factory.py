"""Factory for Blueair update coordinators."""

from blueair_api import Device as BlueAirApiDevice, DeviceAws as BlueAirDeviceAws
from homeassistant.core import HomeAssistant

from .blueair_update_coordinator import BlueairUpdateCoordinator
from .blueair_update_coordinator_device import BlueairUpdateCoordinatorDevice
from .blueair_update_coordinator_device_aws import BlueairUpdateCoordinatorDeviceAws


async def create_blueair_coordinator(
    hass: HomeAssistant, blueair_api_device: BlueAirApiDevice | BlueAirDeviceAws
) -> BlueairUpdateCoordinator:
    """Create the update coordinator for a Blueair API device."""
    if blueair_api_device is BlueAirApiDevice:
        return BlueairUpdateCoordinatorDevice(hass, blueair_api_device)
    return BlueairUpdateCoordinatorDeviceAws(hass, blueair_api_device)
