import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_REGION,
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    DOMAIN,
    CONF_CLOUD_REGION,
    CONFIG_FLOW_VERSION,
    REGIONS,
    REGION_USA,
    DEFAULT_SCAN_INTERVAL,
)

from blueair_api import AuthError, HttpAwsBlueair

_LOGGER = logging.getLogger(__name__)


def _region_selector(options: list[str] | None = None):
    return SelectSelector(
        SelectSelectorConfig(
            options=options or REGIONS,
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


REGION_SELECTOR = _region_selector()


class OptionFlowHandler(config_entries.OptionsFlow):
    """Display preferences UI."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Display preferences UI."""
        region = config_entry.options.get(
            CONF_REGION,
            config_entry.data.get(CONF_REGION, REGION_USA),
        )
        cloud_region = config_entry.options.get(
            CONF_CLOUD_REGION,
            config_entry.data.get(CONF_CLOUD_REGION, region),
        )
        self.schema = vol.Schema(
            {
                vol.Required(
                    CONF_REGION,
                    default=region,
                ): REGION_SELECTOR,
                vol.Required(
                    CONF_CLOUD_REGION,
                    default=cloud_region,
                ): REGION_SELECTOR,
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=config_entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
            }
        )

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Display preferences UI."""
        if user_input is not None:
            _LOGGER.debug("user input in option flow : %s", user_input)
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(step_id="init", data_schema=self.schema)


@config_entries.HANDLERS.register(DOMAIN)
class ConfigFlowHandler(config_entries.ConfigFlow):

    VERSION = CONFIG_FLOW_VERSION
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_PUSH

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return preferences handler."""
        return OptionFlowHandler(config_entry)

    def __init__(self):
        self.data: dict[str, Any] = {}
        self._account_region_candidates: list[str] = []
        self._cloud_region_default = REGION_USA
        self._cloud_region_source = "defaulted to account region"

    async def _async_create_blueair_entry(self):
        username = self.data[CONF_USERNAME]
        await self.async_set_unique_id(username)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=username,
            data=self.data,
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        data_schema = {
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
        }
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            self.data = {
                CONF_USERNAME: username,
                CONF_PASSWORD: password,
            }
            account_regions = await self._async_detect_account_regions(
                username, password
            )
            if not account_regions:
                errors["base"] = "auth"
            elif len(account_regions) == 1:
                region = account_regions[0]
                self.data[CONF_REGION] = region
                return await self._async_prepare_cloud_region_step(region)
            else:
                self._account_region_candidates = account_regions
                return await self.async_step_account_region()

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(data_schema), errors=errors
        )

    async def async_step_account_region(
        self, user_input: dict[str, Any] | None = None
    ):
        if user_input is not None:
            region = user_input[CONF_REGION]
            self.data[CONF_REGION] = region
            return await self._async_prepare_cloud_region_step(region)

        options = self._account_region_candidates or REGIONS
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_REGION,
                    default=options[0],
                ): _region_selector(options),
            }
        )

        return self.async_show_form(
            step_id="account_region", data_schema=data_schema, errors={}
        )

    async def async_step_cloud_region(
        self, user_input: dict[str, Any] | None = None
    ):
        errors: dict[str, str] = {}

        if user_input is not None:
            self.data[CONF_CLOUD_REGION] = user_input[CONF_CLOUD_REGION]
            return await self._async_create_blueair_entry()

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_CLOUD_REGION,
                    default=self._cloud_region_default,
                ): REGION_SELECTOR,
            }
        )

        return self.async_show_form(
            step_id="cloud_region",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "suggested_cloud_region": self._cloud_region_default,
                "suggestion_source": self._cloud_region_source,
            },
        )

    async def _async_detect_account_regions(
        self, username: str, password: str
    ) -> list[str]:
        account_regions: list[str] = []
        for region in REGIONS:
            api_cloud = None
            try:
                api_cloud = HttpAwsBlueair(
                    username=username,
                    password=password,
                    gigya_region=region,
                    cloud_region=region,
                )
                await api_cloud.refresh_jwt()
            except AuthError:
                _LOGGER.debug("Blueair account auth failed for region %s", region)
            except Exception:
                _LOGGER.debug(
                    "Blueair account-region detection failed for %s",
                    region,
                    exc_info=True,
                )
            else:
                account_regions.append(region)
            finally:
                if api_cloud is not None:
                    await api_cloud.cleanup_client_session()
        return account_regions

    async def _async_prepare_cloud_region_step(self, region: str):
        self._cloud_region_default = region
        self._cloud_region_source = "defaulted to account region"

        api_cloud = None
        try:
            api_cloud = HttpAwsBlueair(
                username=self.data[CONF_USERNAME],
                password=self.data[CONF_PASSWORD],
                gigya_region=region,
                cloud_region=region,
            )
            await api_cloud.refresh_jwt()
            scan = await api_cloud.discover_cloud_region()
        except Exception:
            _LOGGER.debug("BlueCloud region discovery failed", exc_info=True)
        else:
            _LOGGER.debug(
                "BlueCloud region discovery: selected=%s winner=%s "
                "multi_region=%s per_region=%s",
                scan.selected_region,
                scan.winner,
                scan.multi_region_detected,
                {
                    region_key: {
                        "devices": probe.device_count,
                        "online": probe.online_count,
                        "error": probe.error,
                    }
                    for region_key, probe in scan.per_region.items()
                },
            )
            if scan.winner is not None:
                self._cloud_region_default = scan.winner
                self._cloud_region_source = "online devices found in this region"
                online_regions = [
                    region_key
                    for region_key, probe in scan.per_region.items()
                    if probe.online_count and probe.online_count > 0
                ]
                if len(online_regions) == 1:
                    _LOGGER.debug(
                        "BlueCloud region discovery: auto-selecting %s "
                        "(only online region)",
                        scan.winner,
                    )
                    self.data[CONF_CLOUD_REGION] = scan.winner
                    return await self._async_create_blueair_entry()
                _LOGGER.debug(
                    "BlueCloud region discovery: not auto-selecting "
                    "(online_regions=%s); prompting user with default %s",
                    online_regions,
                    self._cloud_region_default,
                )
            else:
                _LOGGER.debug(
                    "BlueCloud region discovery: no winner; prompting user "
                    "with default %s",
                    self._cloud_region_default,
                )
        finally:
            if api_cloud is not None:
                await api_cloud.cleanup_client_session()

        return await self.async_step_cloud_region()
