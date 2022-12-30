"""Base entity class for Blueair entities."""
import homeassistant.helpers.device_registry as dr
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from .const import DOMAIN
from .blueair_data_update_coordinator import BlueairDataUpdateCoordinator


class BlueairEntity(CoordinatorEntity):
    """A base class for Blueair entities."""

    _attr_force_update = False
    _attr_should_poll = False

    def __init__(
        self,
        entity_type: str,
        device: BlueairDataUpdateCoordinator,
        **kwargs,
    ) -> None:
        super().__init__(device)
        self._attr_name = f"{device.blueair_api_device.name} {entity_type}"
        self._attr_unique_id = f"{device.blueair_api_device.uuid}_{entity_type}"

        self._device: BlueairDataUpdateCoordinator = device

    @property
    def device_info(self) -> DeviceInfo:
        connections = {(dr.CONNECTION_NETWORK_MAC, self._device.blueair_api_device.mac)}
        return DeviceInfo(
            connections=connections,
            identifiers={(DOMAIN, self._device.id)},
            manufacturer=self._device.manufacturer,
            model=self._device.model,
            name=self._device.blueair_api_device.name,
        )

    async def async_update(self):
        """Update Blueair entity."""
        await self._device.async_request_refresh()
        self._attr_available = self._device.blueair_api_device.wifi_working

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(self._device.async_add_listener(self.async_write_ha_state))
