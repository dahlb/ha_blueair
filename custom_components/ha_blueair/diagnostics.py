from __future__ import annotations

from typing import Any
from logging import getLogger

import attr

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_UNIQUE_ID, CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import DOMAIN, DATA_DEVICES, DATA_AWS_DEVICES
from .blueair_update_coordinator_device import BlueairUpdateCoordinatorDevice
from .blueair_update_coordinator_device_aws import BlueairUpdateCoordinatorDeviceAws

TO_REDACT = {CONF_EMAIL, CONF_PASSWORD, CONF_UNIQUE_ID}
TO_REDACT_MAPPED = {}
TO_REDACT_DEVICE = {}
TO_REDACT_ENTITIES = {}

_LOGGER = getLogger(__name__)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, dict[str, Any]]:
    """Return diagnostics for a config entry."""
    device_coordinators: list[BlueairUpdateCoordinatorDevice] = hass.data[DOMAIN][DATA_DEVICES]
    device_aws_coordinators: list[BlueairUpdateCoordinatorDeviceAws] = hass.data[DOMAIN][DATA_AWS_DEVICES]
    coordinators = device_coordinators + device_aws_coordinators
    data = {
        "entry": async_redact_data(config_entry.as_dict(), TO_REDACT),
    }
    for coordinator in coordinators:
        data[coordinator.blueair_api_device.mac] = {
            "device_str": str(coordinator.blueair_api_device),
            "raw_info": coordinator.blueair_api_device.raw_info,
        }

        device_registry = dr.async_get(hass)
        entity_registry = er.async_get(hass)
        hass_device = device_registry.async_get_device(
            identifiers={(DOMAIN, coordinator.id)}
        )
        if hass_device is not None:
            data[coordinator.blueair_api_device.mac]["device"] = {
                **async_redact_data(attr.asdict(hass_device), TO_REDACT_DEVICE),
                "entities": {},
            }

            hass_entities = er.async_entries_for_device(
                entity_registry,
                device_id=hass_device.id,
                include_disabled_entities=True,
            )

            for entity_entry in hass_entities:
                state = hass.states.get(entity_entry.entity_id)
                state_dict = None
                if state:
                    state_dict = dict(state.as_dict())
                    # The entity_id is already provided at root level.
                    state_dict.pop("entity_id", None)
                    # The context doesn't provide useful information in this case.
                    state_dict.pop("context", None)

                data[coordinator.blueair_api_device.mac]["device"]["entities"][entity_entry.entity_id] = {
                    **async_redact_data(
                        attr.asdict(
                            entity_entry,
                            filter=lambda attr, value: attr.name != "entity_id",
                        ),
                        TO_REDACT_ENTITIES,
                    ),
                    "state": state_dict,
                }

    return data
