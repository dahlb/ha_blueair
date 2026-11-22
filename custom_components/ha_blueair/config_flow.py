"""Config flow for the Blueair integration."""

from collections.abc import Mapping
import logging
from typing import Any

from aiohttp import ClientError
from blueair_api import AuthError, get_aws_devices
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlowWithReload
from homeassistant.const import CONF_PASSWORD, CONF_REGION, CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import probatio

from .const import (
    CONF_FILTER_EXPIRED_THRESHOLD,
    CONF_NIGHT_PRESET,
    CONFIG_FLOW_MINOR_VERSION,
    CONFIG_FLOW_VERSION,
    DEFAULT_FILTER_EXPIRED_THRESHOLD,
    DEFAULT_NIGHT_PRESET,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_FILTER_EXPIRED_THRESHOLD,
    REGION_USA,
    REGIONS,
)

_LOGGER = logging.getLogger(__name__)


def _unique_id(username: str) -> str:
    """Return the config entry unique ID for a Blueair account.

    Email addresses are case-insensitive, so the same account typed with
    different capitalization gets the same unique ID.

    Args:
        username: Blueair account username (an email address).

    Returns:
        str: The lowercase username.
    """
    return username.strip().lower()


class OptionFlowHandler(OptionsFlowWithReload):
    """Display preferences UI.

    Saving the options reloads the entry, which applies the new polling
    interval and Filter Expiration threshold, and rebuilds the fans' preset
    lists.
    """

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Display preferences UI.

        Args:
            user_input: Submitted options, or None to show the form.

        Returns:
            ConfigFlowResult: The form, or the saved options.
        """
        if user_input is not None:
            _LOGGER.debug("user input in option flow : %s", user_input)
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        schema = probatio.Schema(
            {
                probatio.Required(
                    CONF_SCAN_INTERVAL,
                    default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): probatio.All(probatio.Coerce(int), probatio.Range(min=1, max=30)),
                probatio.Required(
                    CONF_NIGHT_PRESET,
                    default=options.get(CONF_NIGHT_PRESET, DEFAULT_NIGHT_PRESET),
                ): bool,
                probatio.Required(
                    CONF_FILTER_EXPIRED_THRESHOLD,
                    default=options.get(
                        CONF_FILTER_EXPIRED_THRESHOLD, DEFAULT_FILTER_EXPIRED_THRESHOLD
                    ),
                ): probatio.All(
                    probatio.Coerce(int),
                    probatio.Range(min=0, max=MAX_FILTER_EXPIRED_THRESHOLD),
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)


class ConfigFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a Blueair config flow."""

    VERSION = CONFIG_FLOW_VERSION
    MINOR_VERSION = CONFIG_FLOW_MINOR_VERSION

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionFlowHandler:
        """Return preferences handler."""
        return OptionFlowHandler()

    def __init__(self) -> None:
        """Initialize the config flow handler."""
        self.data: dict[str, Any] = {}

    async def _async_validate_login(self, username: str, password: str, region: str) -> str | None:
        """Log in to Blueair once to check the credentials.

        The login uses Home Assistant's shared aiohttp session, which
        blueair_api leaves open.

        Args:
            username: Blueair account username.
            password: Blueair account password.
            region: Blueair cloud region.

        Returns:
            str | None: The form error key, or None when the login succeeded.
        """
        try:
            await get_aws_devices(
                username=username,
                password=password,
                region=region,
                client_session=async_get_clientsession(self.hass),
            )
        except AuthError:
            return "auth"
        except ClientError, TimeoutError:
            # blueair_api's other errors (rate limits, server errors) are
            # ClientError subclasses too: Blueair could not be reached.
            _LOGGER.debug("Blueair cloud unreachable during login check", exc_info=True)
            return "cannot_connect"
        except KeyError, TypeError, ValueError:
            _LOGGER.exception("Unexpected response from Blueair during login check")
            return "unknown"
        return None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the user step of the config flow."""
        data_schema = {
            probatio.Required(
                CONF_REGION,
                default=REGION_USA,
            ): probatio.In(REGIONS),
            probatio.Required(CONF_USERNAME): str,
            probatio.Required(probatio.Secret(CONF_PASSWORD)): str,
        }
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            # Checked before logging in, so a duplicate needs no network call.
            await self.async_set_unique_id(_unique_id(username))
            self._abort_if_unique_id_configured()
            error = await self._async_validate_login(
                username, user_input[CONF_PASSWORD], user_input[CONF_REGION]
            )
            if error is None:
                self.data.update(user_input)
                return self.async_create_entry(title=username, data=self.data)
            errors["base"] = error

        return self.async_show_form(
            step_id="user", data_schema=probatio.Schema(data_schema), errors=errors
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """Start reauthentication after Blueair rejected the stored credentials.

        Args:
            entry_data: Data of the config entry that needs new credentials.

        Returns:
            ConfigFlowResult: The password form.
        """
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the account's new password and update the entry.

        Args:
            user_input: Submitted password, or None to show the form.

        Returns:
            ConfigFlowResult: The form (with any error) or the reauth abort.
        """
        reauth_entry = self._get_reauth_entry()
        username = reauth_entry.data[CONF_USERNAME]
        errors: dict[str, str] = {}
        if user_input is not None:
            password = user_input[CONF_PASSWORD]
            error = await self._async_validate_login(
                username, password, reauth_entry.data[CONF_REGION]
            )
            if error is None:
                return self.async_update_reload_and_abort(
                    reauth_entry, data_updates={CONF_PASSWORD: password}
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=probatio.Schema({probatio.Required(probatio.Secret(CONF_PASSWORD)): str}),
            description_placeholders={"username": username},
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the account's region or password.

        The username is the entry's unique ID, so another account needs its own
        entry.

        Args:
            user_input: Submitted region and password, or None to show the form.

        Returns:
            ConfigFlowResult: The form (with any error) or the reconfigure abort.
        """
        entry = self._get_reconfigure_entry()
        username = entry.data[CONF_USERNAME]
        errors: dict[str, str] = {}
        if user_input is not None:
            region = user_input[CONF_REGION]
            password = user_input[CONF_PASSWORD]
            error = await self._async_validate_login(username, password, region)
            if error is None:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_REGION: region, CONF_PASSWORD: password}
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=probatio.Schema(
                {
                    probatio.Required(CONF_REGION, default=entry.data[CONF_REGION]): probatio.In(
                        REGIONS
                    ),
                    probatio.Required(probatio.Secret(CONF_PASSWORD)): str,
                }
            ),
            description_placeholders={"username": username},
            errors=errors,
        )
