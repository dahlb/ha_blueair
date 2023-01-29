import logging
from typing import Dict, Optional, Any

import voluptuous as vol
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant import config_entries
from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_REGION,
)

from .const import (
    DOMAIN,
    CONFIG_FLOW_VERSION,
    REGIONS,
    REGION_USA,
)

from blueair_api import HttpBlueair

_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register(DOMAIN)
class KiaUvoConfigFlowHandler(config_entries.ConfigFlow):

    VERSION = CONFIG_FLOW_VERSION
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_PUSH

    data: Optional[Dict[str, Any]] = {}

    def __init__(self):
        pass

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        data_schema = {
            vol.Required(
                CONF_REGION,
                default=REGION_USA,
            ): vol.In(REGIONS),
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
        }
        errors: Dict[str, str] = {}

        if user_input is not None:
            region = user_input[CONF_REGION]
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            api_cloud = None
            try:
                api_cloud = HttpBlueair(username=username, password=password)
                api_cloud.get_auth_token()
                self.data.update(user_input)
                return self.async_create_entry(
                    title=username,
                    data=self.data,
                )
            except ConfigEntryAuthFailed:
                errors["base"] = "auth"
            finally:
                if api_cloud is not None:
                    await api_cloud.cleanup_client_session()

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(data_schema), errors=errors
        )
