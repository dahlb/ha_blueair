"""Diagnostics support for the Blueair integration."""

from __future__ import annotations

from logging import getLogger
from typing import Any

import attr
from homeassistant.components.diagnostics import REDACTED, async_redact_data
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_UNIQUE_ID, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from . import BlueairConfigEntry
from .const import DOMAIN

# The username is the account's email address, which is also the entry title.
TO_REDACT = {CONF_EMAIL, CONF_PASSWORD, CONF_UNIQUE_ID, CONF_USERNAME, "title"}
# Device registry fields holding the MAC address or serial number.
TO_REDACT_DEVICE = {"connections", "serial_number"}
TO_REDACT_ENTITIES: set[str] = set()


def _redact_values(data: Any, secrets: set[str]) -> Any:
    """Replace every occurrence of the given strings, wherever they appear.

    The device's own MAC address and serial number turn up inside free text
    (the device's repr) and under keys that vary by model (raw_info), so they
    are redacted by value rather than by key.

    Args:
        data: Diagnostics data to redact.
        secrets: Strings to remove.

    Returns:
        Any: A copy of data with each secret replaced by **REDACTED**.
    """
    if isinstance(data, dict):
        return {key: _redact_values(value, secrets) for key, value in data.items()}
    if isinstance(data, list | tuple | set):
        return [_redact_values(value, secrets) for value in data]
    if isinstance(data, str):
        for secret in sorted(secrets, key=len, reverse=True):
            data = data.replace(secret, REDACTED)
    return data


_LOGGER = getLogger(__name__)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: BlueairConfigEntry
) -> dict[str, dict[str, Any]]:
    """Return diagnostics for a config entry."""
    coordinators = config_entry.runtime_data.coordinators
    data: dict[str, Any] = {
        "entry": async_redact_data(config_entry.as_dict(), TO_REDACT),
    }
    # Devices are keyed by Blueair's device ID: the MAC address is redacted,
    # and some devices report none.
    for coordinator in coordinators:
        api_device = coordinator.blueair_api_device
        secrets = {
            value
            for value in (
                getattr(api_device, "serial_number", None),
                config_entry.data.get(CONF_USERNAME),
                config_entry.data.get(CONF_PASSWORD),
            )
            if isinstance(value, str) and value
        }
        if isinstance(api_device.mac, str) and api_device.mac:
            # Blueair writes MAC addresses with and without separators.
            bare_mac = api_device.mac.replace(":", "").replace("-", "")
            secrets |= {api_device.mac, bare_mac, bare_mac.lower(), bare_mac.upper()}
            secrets |= {api_device.mac.lower(), api_device.mac.upper()}
        device_data: dict[str, Any] = {
            "device_str": str(api_device),
            "raw_info": api_device.raw_info,
        }

        device_registry = dr.async_get(hass)
        entity_registry = er.async_get(hass)
        hass_device = device_registry.async_get_device_by_identifier(
            (DOMAIN, coordinator.id), config_entry.entry_id
        )
        if hass_device is not None:
            device_data["device"] = {
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

                device_data["device"]["entities"][entity_entry.entity_id] = {
                    **async_redact_data(
                        attr.asdict(
                            entity_entry,
                            filter=lambda attr, value: attr.name != "entity_id",
                        ),
                        TO_REDACT_ENTITIES,
                    ),
                    "state": state_dict,
                }

        data[coordinator.id] = _redact_values(device_data, secrets)

    return data
