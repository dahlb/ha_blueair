"""Base entity class for Blueair entities."""

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from propcache import cached_property

from . import BlueairConfigEntry
from .const import DOMAIN
from .coordinator_device import BlueairUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Module-level set of coordinator UUIDs we've already warned about for a
# missing MAC.  Keeps the log from spamming once per entity (~10 entities
# per coordinator).  See the issue linked in `device_info` below.
_MAC_MISSING_WARNED: set[str] = set()


def async_setup_entry_helper(
    hass: HomeAssistant,
    config_entry: BlueairConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
    entity_classes: list[type[BlueairEntity]],
) -> None:
    """Add entities of the given classes for every coordinator that supports them."""
    coordinators: list[BlueairUpdateCoordinator] = config_entry.runtime_data.coordinators

    entities = [
        kls(coordinator)
        for coordinator in coordinators
        for kls in entity_classes
        if kls.is_implemented(coordinator)
    ]

    async_add_entities(entities)


class BlueairEntity(CoordinatorEntity[BlueairUpdateCoordinator]):
    """A base class for Blueair entities."""

    _attr_has_entity_name = True
    _attr_translation_key = DOMAIN

    @classmethod
    def is_implemented(cls, coordinator: BlueairUpdateCoordinator) -> bool:
        """Returns true if the coordinator supports this entity."""
        raise NotImplementedError

    def __init__(
        self,
        entity_type: str,
        coordinator: BlueairUpdateCoordinator,
        **kwargs,
    ) -> None:
        """Initialize the blueair entity.

        Home Assistant prefixes the device name, so the friendly name stays
        "{device name} {entity type}" and new entity IDs are unchanged.
        """
        super().__init__(coordinator)
        self._attr_name = entity_type
        self._attr_unique_id = f"{coordinator.id}_{entity_type}"

    @cached_property[DeviceInfo | None]
    def device_info(self) -> DeviceInfo:
        """Return device information for the device registry."""
        # Some Blueair API responses (notably the legacy ABL device list
        # for accounts where the same device is also AWS-registered) carry
        # `mac: null`.  Falling back to identifiers-only keeps the entity
        # registerable instead of raising and aborting the platform.
        # See dahlb/ha_blueair#356 for the original symptom.
        mac = self.coordinator.blueair_api_device.mac
        if mac is None:
            uuid = self.coordinator.id
            if uuid not in _MAC_MISSING_WARNED:
                _MAC_MISSING_WARNED.add(uuid)
                _LOGGER.warning(
                    "Blueair device %s (%s) reported mac=None; registering "
                    "device by identifier only.  This usually means the "
                    "device appears in both the legacy and AWS device lists "
                    "for this account.",
                    self.coordinator.device_name,
                    uuid,
                )
            connections: set[tuple[str, str]] = set()
        else:
            connections = {(CONNECTION_NETWORK_MAC, mac)}
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
        if not self.coordinator.last_update_success:
            return False
        if self.coordinator.model == "sense+":
            # Sense+ can report wifi_working=False while refreshes and commands
            # still succeed. Require a usable legacy fan state instead.
            return str(self.coordinator.blueair_api_device.fan_speed) in ("0", "1", "2", "3")
        return self.coordinator.online
