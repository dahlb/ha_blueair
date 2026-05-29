from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from blueair_api import AuthError, HttpAwsBlueair
from homeassistant import data_entry_flow
from homeassistant.const import CONF_PASSWORD, CONF_REGION, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import CONF_CLOUD_REGION, DOMAIN, REGIONS

_LOGGER = logging.getLogger(__name__)


REGION_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=REGIONS,
        mode=SelectSelectorMode.DROPDOWN,
    )
)


async def async_create_fix_flow(
    hass: HomeAssistant, issue_id: str, data: dict[str, Any] | None
) -> data_entry_flow.FlowHandler:
    return BlueairCloudRegionRepairFlow(hass, issue_id, data or {})


class BlueairCloudRegionRepairFlow(data_entry_flow.FlowHandler):
    VERSION = 1

    def __init__(
        self, hass: HomeAssistant, issue_id: str, issue_data: dict[str, Any]
    ) -> None:
        self.hass = hass
        self._issue_id = issue_id
        self._issue_data = issue_data
        self._suggested_cloud_region: str | None = None

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        entry_id = self._issue_data.get("entry_id")
        config_entry = self.hass.config_entries.async_get_entry(entry_id)
        if config_entry is None:
            return self.async_abort(reason="entry_not_found")

        current_cloud_region = config_entry.data.get(
            CONF_CLOUD_REGION, config_entry.data[CONF_REGION]
        )

        if user_input is not None:
            new_data = {
                **config_entry.data,
                CONF_CLOUD_REGION: user_input[CONF_CLOUD_REGION],
            }
            self.hass.config_entries.async_update_entry(config_entry, data=new_data)
            ir.async_delete_issue(self.hass, DOMAIN, self._issue_id)
            await self.hass.config_entries.async_reload(config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        errors: dict[str, str] = {}
        suggested_cloud_region = self._suggested_cloud_region
        if suggested_cloud_region is None:
            suggested_cloud_region = current_cloud_region
            try:
                suggested_cloud_region = await self._async_discover_cloud_region(
                    config_entry, current_cloud_region
                )
            except AuthError:
                errors["base"] = "auth"
            except Exception:
                _LOGGER.debug("BlueCloud repair discovery failed", exc_info=True)
            self._suggested_cloud_region = suggested_cloud_region

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_CLOUD_REGION,
                        default=suggested_cloud_region,
                    ): REGION_SELECTOR,
                }
            ),
            errors=errors,
            description_placeholders={
                "cloud_region": current_cloud_region,
                "suggested_cloud_region": suggested_cloud_region,
            },
        )

    async def _async_discover_cloud_region(
        self, config_entry, current_cloud_region: str
    ) -> str:
        api_cloud = HttpAwsBlueair(
            username=config_entry.data[CONF_USERNAME],
            password=config_entry.data[CONF_PASSWORD],
            gigya_region=config_entry.data[CONF_REGION],
            cloud_region=current_cloud_region,
        )
        try:
            await api_cloud.refresh_jwt()
            scan = await api_cloud.discover_cloud_region()
        finally:
            await api_cloud.cleanup_client_session()

        return scan.winner or current_cloud_region
