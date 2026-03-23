import logging
from datetime import timedelta

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_REGION,
    CONF_SCAN_INTERVAL,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from blueair_api import get_devices, get_aws_devices, LoginError, MqttAwsBlueair

from .blueair_update_coordinator_device import BlueairUpdateCoordinatorDevice
from .blueair_update_coordinator_device_aws import BlueairUpdateCoordinatorDeviceAws
from .const import (
    DOMAIN,
    PLATFORMS,
    DATA_DEVICES,
    DATA_AWS_DEVICES,
    DATA_MQTT_CLIENT,
    REGION_USA,
    DEFAULT_SCAN_INTERVAL,
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
    _LOGGER.debug("async setup")
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    _LOGGER.debug(f"async setup entry: {config_entry}")
    username = config_entry.data[CONF_USERNAME]
    password = config_entry.data[CONF_PASSWORD]
    region = config_entry.data[CONF_REGION]
    interval = config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    _LOGGER.debug(f"setting up scan interval: {interval}")

    data = {}

    client_session = async_get_clientsession(hass)
    try:
        try:
            _, devices = await get_devices(
                username=username, password=password, client_session=client_session
            )
        except LoginError as ex:
            _LOGGER.debug(f"Legacy Login error: {ex}")
            devices = []
        aws_http_client, aws_devices = await get_aws_devices(
            username=username,
            password=password,
            client_session=client_session,
            region=region,
        )

        def create_coordinators(device):
            return BlueairUpdateCoordinatorDevice(
                hass=hass,
                blueair_api_device=device,
                interval=interval,
            )
        data[DATA_DEVICES] = list(map(create_coordinators, devices))
        def create_aws_coordinators(device):
            return BlueairUpdateCoordinatorDeviceAws(
                hass=hass,
                blueair_api_device=device,
                interval=interval,
            )
        data[DATA_AWS_DEVICES] = list(map(create_aws_coordinators, aws_devices))

        coordinators = data[DATA_DEVICES] + data[DATA_AWS_DEVICES]

        for coordinator in coordinators:
            await coordinator.async_config_entry_first_refresh()

        # Start MQTT for real-time updates on AWS devices.
        mqtt_client = None
        if (
            aws_devices
            and aws_http_client.mqtt_auth_name
            and aws_http_client.mqtt_auth_signature
            and aws_http_client.mqtt_auth_token
        ):
            try:
                mqtt_client = MqttAwsBlueair(
                    region=region,
                    mqtt_auth_name=aws_http_client.mqtt_auth_name,
                    mqtt_auth_signature=aws_http_client.mqtt_auth_signature,
                    mqtt_auth_token=aws_http_client.mqtt_auth_token,
                    user_id=aws_http_client.user_id,
                )

                # Build a lookup from device UUID to coordinator
                aws_coordinator_map = {
                    c.id: c for c in data[DATA_AWS_DEVICES]
                }

                def on_sensor_data(device_id, sensors):
                    """Handle MQTT sensor data (called from MQTT thread)."""
                    coordinator = aws_coordinator_map.get(device_id)
                    if coordinator is None:
                        return
                    device = coordinator.blueair_api_device
                    if "pm1" in sensors:
                        device.pm1 = int(sensors["pm1"])
                    if "pm2_5" in sensors:
                        device.pm2_5 = int(sensors["pm2_5"])
                    if "pm10" in sensors:
                        device.pm10 = int(sensors["pm10"])
                    if "fsp0" in sensors:
                        device.fan_speed_0 = int(sensors["fsp0"])
                    device.publish_updates()
                    # Schedule HA state update on the event loop (thread-safe)
                    hass.loop.call_soon_threadsafe(
                        coordinator.async_set_updated_data, str(device)
                    )

                def on_event(device_id, event):
                    """Handle MQTT connectivity event (called from MQTT thread)."""
                    coordinator = aws_coordinator_map.get(device_id)
                    if coordinator is None:
                        return
                    event_type = event.get("et", "")
                    if event_type == "Connected":
                        coordinator.blueair_api_device.wifi_working = True
                    elif event_type == "NotConnected":
                        coordinator.blueair_api_device.wifi_working = False
                    coordinator.blueair_api_device.publish_updates()
                    hass.loop.call_soon_threadsafe(
                        coordinator.async_set_updated_data,
                        str(coordinator.blueair_api_device),
                    )

                mqtt_client.on_sensor_data = on_sensor_data
                mqtt_client.on_event = on_event

                for device in aws_devices:
                    mqtt_client.register_device(device.uuid)

                mqtt_client.connect()
                _LOGGER.info("MQTT real-time updates started for %d device(s)", len(aws_devices))
            except Exception:
                _LOGGER.exception("Failed to start MQTT, falling back to polling only")
                if mqtt_client is not None:
                    mqtt_client.disconnect()
                mqtt_client = None
        else:
            _LOGGER.debug("MQTT credentials not available, using polling only")

        data[DATA_MQTT_CLIENT] = mqtt_client
        hass.data[DOMAIN] = data

        await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
        _LOGGER.debug("integration setup completed")

        async def update_listener(hass: HomeAssistant, updated_config_entry: ConfigEntry):
            """Handle options update."""
            new_interval = updated_config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            _LOGGER.debug(f"changing scan interval: {new_interval}")
            for coordinator_to_update in coordinators:
                coordinator_to_update.update_interval = timedelta(minutes=new_interval)
        config_entry.async_on_unload(config_entry.add_update_listener(update_listener))

        return True
    except LoginError as error:
        _LOGGER.debug("login failure, ha should retry")
        raise ConfigEntryNotReady("Login failure") from error


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    _LOGGER.debug("unload entry")
    # Disconnect MQTT before unloading platforms
    data = hass.data.get(DOMAIN)
    if data and data.get(DATA_MQTT_CLIENT):
        data[DATA_MQTT_CLIENT].disconnect()
        _LOGGER.info("MQTT disconnected")

    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )
    if unload_ok:
        hass.data[DOMAIN] = None

    return unload_ok
