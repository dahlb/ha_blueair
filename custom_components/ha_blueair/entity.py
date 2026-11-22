"""Base entity class for Blueair entities."""

import logging
from typing import Any, Protocol

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from propcache import cached_property

from . import BlueairConfigEntry
from .const import DOMAIN
from .coordinator import BlueairUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Module-level set of coordinator UUIDs we've already warned about for a
# missing MAC.  Keeps the log from spamming once per entity (~10 entities
# per coordinator).  See the issue linked in `device_info` below.
_MAC_MISSING_WARNED: set[str] = set()


class BlueairEntityClass(Protocol):
    """An entity class the platforms create for every device that supports it."""

    def __call__(self, coordinator: Any) -> BlueairEntity[Any]:
        """Create the entity for a coordinator is_implemented accepted."""

    def is_implemented(self, coordinator: BlueairUpdateCoordinator) -> bool:
        """Return whether the coordinator supports this entity."""


def coordinator_reports(coordinator: BlueairUpdateCoordinator, key: str) -> bool:
    """Return whether the coordinator supports the value an entity shows.

    A coordinator that doesn't declare the attribute at all (e.g. an AWS-only
    property on the legacy coordinator class) counts as not supporting it,
    instead of raising AttributeError and aborting the whole platform
    (issue #356).

    Args:
        coordinator: The device's coordinator.
        key: Name of the coordinator property, usually the entity
            description's key.

    Returns:
        bool: False when the property is missing or reports NotImplemented.
    """
    return getattr(coordinator, key, NotImplemented) is not NotImplemented


def async_setup_entry_helper(
    hass: HomeAssistant,
    config_entry: BlueairConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
    entity_classes: list[BlueairEntityClass],
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


class BlueairEntity[CoordinatorT: BlueairUpdateCoordinator = BlueairUpdateCoordinator](
    CoordinatorEntity[CoordinatorT]
):
    """A base class for Blueair entities.

    Entities that only AWS devices have use BlueairEntity with the AWS
    coordinator type; their is_implemented only accepts AWS coordinators.
    """

    _attr_has_entity_name = True

    @classmethod
    def is_implemented(cls, coordinator: BlueairUpdateCoordinator) -> bool:
        """Returns true if the coordinator supports this entity."""
        raise NotImplementedError

    def __init__(
        self,
        unique_id_suffix: str,
        coordinator: CoordinatorT,
        translation_key: str | None = None,
    ) -> None:
        """Initialize the blueair entity.

        Args:
            unique_id_suffix: The entity's original English name. Unique IDs
                were built from it before names were translated, so it stays
                to keep existing entities.
            coordinator: The device's coordinator.
            translation_key: Key for the entity's name (and state and icon
                translations) in strings.json. Entities with an
                entity_description take it from there instead.
        """
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.id}_{unique_id_suffix}"
        if translation_key is not None:
            self._attr_translation_key = translation_key

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
        # Model-specific quirks (e.g. Sense+) live in the coordinator's online.
        return self.coordinator.last_update_success and bool(self.coordinator.online)
