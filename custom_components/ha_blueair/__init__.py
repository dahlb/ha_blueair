"""The Blueair integration."""

import contextlib
from dataclasses import dataclass
from datetime import timedelta
import logging

from aiohttp import ClientError
from blueair_api import (
    Device,
    DeviceAws,
    HttpAwsBlueair,
    LoginError,
    MqttAwsBlueair,
    get_aws_devices,
    get_devices,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_REGION,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import Event, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_NIGHT_PRESET,
    DEFAULT_NIGHT_PRESET,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
    REGION_USA,
)
from .coordinator import BlueairUpdateCoordinator
from .coordinator_device import BlueairUpdateCoordinatorDevice
from .coordinator_device_aws import BlueairUpdateCoordinatorDeviceAws
from .mqtt_mapping import map_and_publish_event

_LOGGER = logging.getLogger(__name__)

# The integration is configured through config entries only; the YAML schema
# that used to live here was never read by async_setup.
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


@dataclass
class BlueairRuntimeData:
    """Per-config-entry state, stored on ConfigEntry.runtime_data.

    Each Blueair account has its own entry, so keeping this on the entry (not in
    a shared hass.data dict) lets several accounts load and unload independently.

    Attributes:
        devices: Coordinators for legacy (non-AWS) devices.
        aws_devices: Coordinators for AWS devices.
        mqtt_client: Connected MQTT client for AWS push updates, or None when
            the entry only polls.
    """

    devices: list[BlueairUpdateCoordinatorDevice]
    aws_devices: list[BlueairUpdateCoordinatorDeviceAws]
    mqtt_client: MqttAwsBlueair | None = None

    @property
    def coordinators(self) -> list[BlueairUpdateCoordinator]:
        """Return every device coordinator for the entry, legacy first."""
        return [*self.devices, *self.aws_devices]


type BlueairConfigEntry = ConfigEntry[BlueairRuntimeData]


def _schedule_update(
    hass: HomeAssistant, coordinator: BlueairUpdateCoordinator, device: DeviceAws
) -> None:
    """Hand an MQTT update to the event loop (called from the MQTT thread).

    paho's network thread can deliver a message after Home Assistant has
    closed its loop. There is nothing left to update by then, so the message
    is dropped rather than raising from the MQTT thread.
    """
    if hass.loop.is_closed():
        return
    # The loop can still close between the check and the call.
    with contextlib.suppress(RuntimeError):
        hass.loop.call_soon_threadsafe(coordinator.async_set_updated_data, str(device))


async def _async_start_mqtt(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    region: str,
    aws_http_client: HttpAwsBlueair,
    aws_devices: list[DeviceAws],
    aws_coordinators: list[BlueairUpdateCoordinatorDeviceAws],
) -> MqttAwsBlueair | None:
    """Start MQTT real-time updates for AWS devices.

    Returns:
        The connected MQTT client, or None when MQTT is unavailable and the
        integration falls back to polling only.
    """
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
            aws_coordinator_map = {c.id: c for c in aws_coordinators}

            def on_sensor_data(device_id: str, sensors: dict) -> None:
                """Handle MQTT sensor data (called from MQTT thread)."""
                _LOGGER.debug("processing sensor update %s for %s", sensors, device_id)
                coordinator = aws_coordinator_map.get(device_id)
                if coordinator is None:
                    _LOGGER.debug("sensor data update provided for unknown device: %s", device_id)
                    return
                device = coordinator.blueair_api_device
                try:
                    device.apply_sensor_data(sensors)
                except Exception:
                    _LOGGER.exception(
                        "apply_sensor_data raised for device %s with payload %r",
                        device_id,
                        sensors,
                    )
                    return
                device.publish_updates()
                _schedule_update(hass, coordinator, device)

            def on_state_change(device_id: str, state: dict) -> None:
                """Handle MQTT shadow state change (called from MQTT thread)."""
                _LOGGER.debug("processing state change %s for %s", state, device_id)
                coordinator = aws_coordinator_map.get(device_id)
                if coordinator is None:
                    _LOGGER.debug("state change provided for unknown device: %s", device_id)
                    return
                device = coordinator.blueair_api_device
                try:
                    device.apply_state_change(state)
                except Exception:
                    _LOGGER.exception(
                        "apply_state_change raised for device %s with payload %r",
                        device_id,
                        state,
                    )
                    return
                device.publish_updates()
                _schedule_update(hass, coordinator, device)

            def on_event(device_id: str, event: dict) -> None:
                """Handle MQTT connectivity event (called from MQTT thread)."""
                _LOGGER.debug("processing event update %s for %s", event, device_id)
                coordinator = aws_coordinator_map.get(device_id)
                if coordinator is None:
                    _LOGGER.debug("event data update provided for unknown device: %s", device_id)
                    return
                device = coordinator.blueair_api_device
                map_and_publish_event(event, device)
                _schedule_update(hass, coordinator, device)

            mqtt_client.on_sensor_data = on_sensor_data
            mqtt_client.on_state_change = on_state_change
            mqtt_client.on_event = on_event

            # Credential refresher for automatic reconnect on token expiry.
            async def refresh_mqtt_credentials() -> tuple[str, str, str]:
                """Refresh the AWS token and return new MQTT credentials."""
                await aws_http_client.refresh_access_token()
                return (
                    aws_http_client.mqtt_auth_name,
                    aws_http_client.mqtt_auth_signature,
                    aws_http_client.mqtt_auth_token,
                )

            mqtt_client.credential_refresher = refresh_mqtt_credentials

            for device in aws_devices:
                mqtt_client.register_device(device.uuid)

            # Run connect in executor to avoid blocking the event loop
            # (TLS handshake is a blocking operation)
            await hass.async_add_executor_job(mqtt_client.connect, hass.loop)
            _LOGGER.info("MQTT real-time updates started for %d device(s)", len(aws_devices))

            # Home Assistant does not unload config entries when it stops,
            # so async_unload_entry never runs at shutdown. Without this
            # the paho thread outlives the event loop and logs an error
            # for every message it receives until the process exits.
            async def stop_mqtt(_event: Event) -> None:
                """Disconnect MQTT when Home Assistant stops."""
                await hass.async_add_executor_job(mqtt_client.disconnect)

            config_entry.async_on_unload(
                hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_mqtt)
            )
        except Exception:
            _LOGGER.exception("Failed to start MQTT, falling back to polling only")
            if mqtt_client is not None:
                mqtt_client.disconnect()
            mqtt_client = None
    else:
        _LOGGER.debug("MQTT credentials not available, using polling only")
    return mqtt_client


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate an old config entry to the current version."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version == 1:
        new_data = {**config_entry.data, CONF_REGION: REGION_USA}

        config_entry.version = 2
        hass.config_entries.async_update_entry(config_entry, data=new_data)

    _LOGGER.info("Migration to version %s successful", config_entry.version)

    return True


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Blueair integration."""
    _LOGGER.debug("async setup")
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: BlueairConfigEntry) -> bool:
    """Set up the platform from a config entry."""
    _LOGGER.debug("async setup entry: %s", config_entry)
    username = config_entry.data[CONF_USERNAME]
    password = config_entry.data[CONF_PASSWORD]
    region = config_entry.data[CONF_REGION]
    interval = config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    _LOGGER.debug("setting up scan interval: %s", interval)

    client_session = async_get_clientsession(hass)
    try:
        try:
            _, devices = await get_devices(
                username=username, password=password, client_session=client_session
            )
        except LoginError as ex:
            _LOGGER.debug("Legacy Login error: %s", ex)
            devices = []
        except (ClientError, TimeoutError) as ex:
            _LOGGER.warning("Legacy Blueair API unavailable, skipping legacy devices: %s", ex)
            devices = []
        aws_http_client, aws_devices = await get_aws_devices(
            username=username,
            password=password,
            client_session=client_session,
            region=region,
        )

        def create_coordinators(device: Device) -> BlueairUpdateCoordinatorDevice:
            return BlueairUpdateCoordinatorDevice(
                hass=hass,
                blueair_api_device=device,
                interval=interval,
            )

        device_coordinators = list(map(create_coordinators, devices))

        def create_aws_coordinators(device: DeviceAws) -> BlueairUpdateCoordinatorDeviceAws:
            return BlueairUpdateCoordinatorDeviceAws(
                hass=hass,
                blueair_api_device=device,
                interval=interval,
            )

        aws_coordinators = list(map(create_aws_coordinators, aws_devices))

        coordinators = [*device_coordinators, *aws_coordinators]

        for coordinator in coordinators:
            await coordinator.async_config_entry_first_refresh()

        mqtt_client = await _async_start_mqtt(
            hass, config_entry, region, aws_http_client, aws_devices, aws_coordinators
        )

        config_entry.runtime_data = BlueairRuntimeData(
            devices=device_coordinators,
            aws_devices=aws_coordinators,
            mqtt_client=mqtt_client,
        )

        await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
        _LOGGER.debug("integration setup completed")

        night_preset = config_entry.options.get(CONF_NIGHT_PRESET, DEFAULT_NIGHT_PRESET)

        async def update_listener(hass: HomeAssistant, updated_config_entry: ConfigEntry) -> None:
            """Handle options update."""
            if (
                updated_config_entry.options.get(CONF_NIGHT_PRESET, DEFAULT_NIGHT_PRESET)
                != night_preset
            ):
                # Fans build their preset list once, when they're created.
                hass.config_entries.async_schedule_reload(updated_config_entry.entry_id)
                return
            new_interval = updated_config_entry.options.get(
                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
            )
            _LOGGER.debug("changing scan interval: %s", new_interval)
            for coordinator_to_update in coordinators:
                coordinator_to_update.update_interval = timedelta(minutes=new_interval)

        config_entry.async_on_unload(config_entry.add_update_listener(update_listener))
    except LoginError as error:
        _LOGGER.debug("login failure, ha should retry")
        raise ConfigEntryNotReady("Login failure") from error
    except (ClientError, TimeoutError) as error:
        _LOGGER.debug("blueair cloud unreachable, ha should retry")
        raise ConfigEntryNotReady("Blueair cloud unreachable") from error
    else:
        return True


async def async_unload_entry(hass: HomeAssistant, config_entry: BlueairConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("unload entry")
    # Disconnect MQTT before unloading platforms
    mqtt_client = config_entry.runtime_data.mqtt_client
    if mqtt_client is not None:
        # disconnect() joins paho's network thread, so keep it off the loop.
        await hass.async_add_executor_job(mqtt_client.disconnect)
        _LOGGER.info("MQTT disconnected")

    return await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)
