"""Base entity class for Blueair entities."""
from propcache import cached_property
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from .const import DOMAIN, DATA_DEVICES, DATA_AWS_DEVICES
from .blueair_update_coordinator_device import BlueairUpdateCoordinator


def async_setup_entry_helper(hass, config_entry, async_add_entities, entity_classes):
    coordinators: list[BlueairUpdateCoordinator] = []
    coordinators.extend(hass.data[DOMAIN][DATA_DEVICES])
    coordinators.extend(hass.data[DOMAIN][DATA_AWS_DEVICES])

    entities = []
    for coordinator in coordinators:
        for kls in entity_classes:
            if kls.is_implemented(coordinator):
                entities.append(kls(coordinator))

    async_add_entities(entities)


class BlueairEntity(CoordinatorEntity[BlueairUpdateCoordinator]):
    """A base class for Blueair entities."""
    _attr_translation_key = DOMAIN

    @classmethod
    def is_implemented(kls, coordinator) -> bool:
       """Returns true if the coordinator supports this entity."""
       raise NotImplementedError

    def __init__(
        self,
        entity_type: str,
        coordinator: BlueairUpdateCoordinator,
        **kwargs,
    ) -> None:
        super().__init__(coordinator)
        self._attr_name = f"{coordinator.device_name} {entity_type}"
        self._attr_unique_id = f"{coordinator.id}_{entity_type}"

    @cached_property[DeviceInfo | None]
    def device_info(self) -> DeviceInfo:
        if self.coordinator.blueair_api_device.mac is None:
            raise ValueError("MAC address is required for device info")
        connections = {(CONNECTION_NETWORK_MAC, self.coordinator.blueair_api_device.mac)}
        return DeviceInfo(
            connections=connections,
            identifiers={(DOMAIN, self.coordinator.id)},
            manufacturer="BlueAir",
            model=self.coordinator.model,
            hw_version=self.coordinator.hw_version,
            sw_version=self.coordinator.sw_version,
            serial_number=self.coordinator.serial_number,
            name=self.coordinator.device_name,
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.online
