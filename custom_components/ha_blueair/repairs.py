"""Repair flows for the Blueair integration."""

import logging
from typing import Any

from aiohttp import ClientError
from blueair_api import AuthError, HttpAwsBlueair
from homeassistant.components.repairs import RepairsFlow, RepairsFlowResult
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_REGION, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import probatio

from .cloud_region import async_scan_cloud_regions
from .const import CONF_CLOUD_REGION, REGIONS

_LOGGER = logging.getLogger(__name__)


async def async_create_fix_flow(
    hass: HomeAssistant, issue_id: str, data: dict[str, Any] | None
) -> RepairsFlow:
    """Create the flow that fixes a Blueair repair issue.

    The only fixable issue is the cloud region one.

    Args:
        hass: Home Assistant instance.
        issue_id: ID of the issue to fix.
        data: The issue's data, holding the config entry ID.

    Returns:
        RepairsFlow: The cloud region repair flow.
    """
    entry_id = (data or {}).get("entry_id")
    return CloudRegionRepairFlow(entry_id if isinstance(entry_id, str) else None)


class CloudRegionRepairFlow(RepairsFlow):
    """Let the user confirm or change the entry's device cloud region."""

    def __init__(self, entry_id: str | None) -> None:
        """Initialize the flow.

        Args:
            entry_id: ID of the config entry the issue is about.
        """
        self._entry_id = entry_id
        self._suggested_cloud_region: str | None = None
        self._errors: dict[str, str] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> RepairsFlowResult:
        """Start the flow.

        The repairs manager passes the issue ID as the first step's input, so
        the form is its own step.

        Args:
            user_input: The issue ID from the repairs manager (unused).

        Returns:
            RepairsFlowResult: The confirm form, or the abort.
        """
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> RepairsFlowResult:
        """Suggest the cloud region that hosts the devices, and save the choice.

        Args:
            user_input: Submitted cloud region, or None to show the form.

        Returns:
            RepairsFlowResult: The form, the abort, or the finished flow.
        """
        entry = (
            self.hass.config_entries.async_get_entry(self._entry_id)
            if self._entry_id is not None
            else None
        )
        if entry is None:
            return self.async_abort(reason="entry_not_found")
        current = entry.data.get(CONF_CLOUD_REGION, entry.data[CONF_REGION])

        if user_input is not None:
            self.hass.config_entries.async_update_entry(
                entry, data={**entry.data, CONF_CLOUD_REGION: user_input[CONF_CLOUD_REGION]}
            )
            # The repairs manager deletes the issue; setup raises it again if
            # the devices still look stale on the chosen region.
            self.hass.config_entries.async_schedule_reload(entry.entry_id)
            return self.async_create_entry(data={})

        if self._suggested_cloud_region is None:
            self._suggested_cloud_region = await self._async_suggest(entry, current)

        return self.async_show_form(
            step_id="confirm",
            data_schema=probatio.Schema(
                {
                    probatio.Required(
                        CONF_CLOUD_REGION, default=self._suggested_cloud_region
                    ): probatio.In(REGIONS),
                }
            ),
            errors=self._errors,
            description_placeholders={
                "cloud_region": current,
                "suggested_cloud_region": self._suggested_cloud_region,
            },
        )

    async def _async_suggest(self, entry: ConfigEntry, current: str) -> str:
        """Probe Blueair for the cloud region hosting the entry's devices.

        Sets ``_errors`` when the probe fails, so the form explains why the
        suggestion is the current region.

        Args:
            entry: The account's config entry.
            current: The cloud region the entry uses now.

        Returns:
            str: The region with the account's devices, or ``current``.
        """
        api = HttpAwsBlueair(
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            client_session=async_get_clientsession(self.hass),
            gigya_region=entry.data[CONF_REGION],
            cloud_region=current,
        )
        try:
            scan = await async_scan_cloud_regions(api)
        except AuthError:
            self._errors = {"base": "auth"}
            return current
        except ClientError, TimeoutError:
            _LOGGER.debug("BlueCloud region scan failed during repair", exc_info=True)
            self._errors = {"base": "cannot_connect"}
            return current
        return scan.winner or current
