"""Factory for Blueair update coordinators."""

from blueair_api import Device as BlueAirApiDevice, DeviceAws as BlueAirDeviceAws
from homeassistant.core import HomeAssistant

from .blueair_update_coordinator import BlueairUpdateCoordinator
from .blueair_update_coordinator_device import BlueairUpdateCoordinatorDevice
from .blueair_update_coordinator_device_aws import BlueairUpdateCoordinatorDeviceAws
from .const import DEFAULT_SCAN_INTERVAL


async def create_blueair_coordinator(
    hass: HomeAssistant,
    blueair_api_device: BlueAirApiDevice | BlueAirDeviceAws,
    interval: int = DEFAULT_SCAN_INTERVAL,
) -> BlueairUpdateCoordinator:
    """Create the update coordinator for a Blueair API device.

    Args:
        hass: Home Assistant instance.
        blueair_api_device: Legacy or AWS Blueair API device.
        interval: Polling interval in minutes.

    Returns:
        A legacy coordinator for ``Device`` instances, otherwise an AWS coordinator.
    """
    if isinstance(blueair_api_device, BlueAirApiDevice):
        return BlueairUpdateCoordinatorDevice(
            hass=hass, blueair_api_device=blueair_api_device, interval=interval
        )
    return BlueairUpdateCoordinatorDeviceAws(
        hass=hass, blueair_api_device=blueair_api_device, interval=interval
    )
