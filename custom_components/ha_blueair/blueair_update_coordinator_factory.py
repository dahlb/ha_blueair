from homeassistant.core import HomeAssistant
from blueair_api import Device as BlueAirApiDevice, DeviceAws as BlueAirDeviceAws

from .blueair_update_coordinator_device_aws import BlueairUpdateCoordinatorDeviceAws
from .blueair_update_coordinator_device import BlueairUpdateCoordinatorDevice
from .blueair_update_coordinator import BlueairUpdateCoordinator

async def create_blueair_coordinator(hass: HomeAssistant,
                                     blueair_api_device: BlueAirApiDevice | BlueAirDeviceAws)\
        -> BlueairUpdateCoordinator:
    if blueair_api_device is BlueAirApiDevice:
        return BlueairUpdateCoordinatorDevice(hass, blueair_api_device)
    else:
        return BlueairUpdateCoordinatorDeviceAws(hass, blueair_api_device)
