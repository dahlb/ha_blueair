"""Base entity class for Blueair entities."""
import homeassistant.helpers.device_registry as dr
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from .const import DOMAIN, DATA_DEVICES, DATA_AWS_DEVICES
from .blueair_data_update_coordinator import BlueairDataUpdateCoordinator
from .blueair_aws_data_update_coordinator import BlueairAwsDataUpdateCoordinator


def async_setup_entry_helper(hass, config_entry, async_add_entities, entity_classes):

    coordinators: list[BlueairDataUpdateCoordinator | BlueairAwsDataUpdateCoordinator] = []
    coordinators.extend(hass.data[DOMAIN][DATA_DEVICES])
    coordinators.extend(hass.data[DOMAIN][DATA_AWS_DEVICES])

    entities = []
    for coordinator in coordinators:
        for kls in entity_classes:
            if kls.is_supported(coordinator):
                entities.append(kls(coordinator))

    async_add_entities(entities)


class BlueairEntity(CoordinatorEntity):
    """A base class for Blueair entities."""

    _attr_force_update = False
    _attr_should_poll = False

    @classmethod
    def is_supported(kls, coordinator) -> bool:
       """Returns true if the coordinator supports this entity."""
       raise NotImplementedError

    def __init__(
        self,
        entity_type: str,
        coordinator: BlueairAwsDataUpdateCoordinator | BlueairDataUpdateCoordinator,
        **kwargs,
    ) -> None:
        super().__init__(coordinator)
        self._attr_name = f"{coordinator.blueair_api_device.name} {entity_type}"
        self._attr_unique_id = f"{coordinator.blueair_api_device.uuid}_{entity_type}"

        self.coordinator: BlueairAwsDataUpdateCoordinator = coordinator

    @property
    def device_info(self) -> DeviceInfo:
        connections = {(dr.CONNECTION_NETWORK_MAC, self.coordinator.blueair_api_device.mac)}
        return DeviceInfo(
            connections=connections,
            identifiers={(DOMAIN, self.coordinator.id)},
            manufacturer=self.coordinator.manufacturer,
            model=self.coordinator.model,
            name=self.coordinator.blueair_api_device.name,
        )

    async def async_update(self):
        """Update Blueair entity."""
        if not self.enabled:
            return

        await self.coordinator.async_request_refresh()
        self._attr_available = self.coordinator.blueair_api_device.wifi_working

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))
