import logging

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_REGION,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from blueair_api import get_devices, get_aws_devices, HttpBlueair
import asyncio

from .blueair_data_update_coordinator import BlueairDataUpdateCoordinator
from .blueair_aws_data_update_coordinator import BlueairAwsDataUpdateCoordinator
from .const import (
    DOMAIN,
    PLATFORMS,
    DATA_DEVICES,
    DATA_AWS_DEVICES,
    REGION_USA,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Required(CONF_REGION): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_migrate_entry(hass, config_entry: ConfigEntry):
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version == 1:
        new_data = {**config_entry.data, CONF_REGION: REGION_USA}

        config_entry.version = 2
        hass.config_entries.async_update_entry(config_entry, data=new_data)

    _LOGGER.info("Migration to version %s successful", config_entry.version)

    return True


async def async_setup(hass: HomeAssistant, config_entry: ConfigType) -> bool:
    hass.data.setdefault(DOMAIN, {})
    _LOGGER.debug(f"async setup")
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    _LOGGER.debug(f"async setup entry: {config_entry}")
    username = config_entry.data[CONF_USERNAME]
    password = config_entry.data[CONF_PASSWORD]
    region = config_entry.data[CONF_REGION]

    data = {}

    client_session = async_get_clientsession(hass)
    _, devices = await get_devices(
        username=username, password=password, client_session=client_session
    )
    _, aws_devices = await get_aws_devices(
        username=username,
        password=password,
        client_session=client_session,
        region=region,
    )

    def create_updaters(device):
        return BlueairDataUpdateCoordinator(
            hass=hass,
            blueair_api_device=device,
        )

    data[DATA_DEVICES] = list(map(create_updaters, devices))

    for updater in data[DATA_DEVICES]:
        await updater.async_config_entry_first_refresh()

    def create_aws_updaters(device):
        return BlueairAwsDataUpdateCoordinator(
            hass=hass,
            blueair_api_device=device,
        )

    data[DATA_AWS_DEVICES] = list(map(create_aws_updaters, aws_devices))

    for updater in data[DATA_AWS_DEVICES]:
        await updater.async_config_entry_first_refresh()

    hass.data[DOMAIN] = data

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, platform)
        )

    return True


async def async_update_options(hass: HomeAssistant, config_entry: ConfigEntry):
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    _LOGGER.debug(f"unload entry")
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(config_entry, platform)
                for platform in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN] = None

    return unload_ok
