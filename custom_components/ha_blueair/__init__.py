"""The Blueair integration."""

from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from typing import Any

from aiohttp import ClientError
from blueair_api import (
    Device,
    DeviceAws,
    HttpAwsBlueair,
    HttpBlueair,
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
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_NIGHT_PRESET,
    DEFAULT_NIGHT_PRESET,
    DEFAULT_SCAN_INTERVAL,
    DEVICE_LIST_INTERVAL,
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
        aws_api: Logged-in AWS client, used to list the account's devices.
        legacy_api: Logged-in legacy client, or None when the account has no
            legacy login or the legacy API was unreachable at setup.
    """

    devices: list[BlueairUpdateCoordinatorDevice]
    aws_devices: list[BlueairUpdateCoordinatorDeviceAws]
    mqtt_client: MqttAwsBlueair | None = None
    aws_api: HttpAwsBlueair | None = None
    legacy_api: HttpBlueair | None = None

    @property
    def coordinators(self) -> list[BlueairUpdateCoordinator]:
        """Return every device coordinator for the entry, legacy first."""
        return [*self.devices, *self.aws_devices]


type BlueairConfigEntry = ConfigEntry[BlueairRuntimeData]


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
                user_id=aws_http_client.user_id or "",
            )

            # Build a lookup from device UUID to coordinator
            aws_coordinator_map = {c.id: c for c in aws_coordinators}

            def on_sensor_data(device_id: str, sensors: dict[str, float]) -> None:
                """Handle MQTT sensor data (called on the event loop)."""
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
                coordinator.async_set_updated_data(str(device))

            def on_state_change(device_id: str, state: dict[str, Any]) -> None:
                """Handle MQTT shadow state change (called on the event loop)."""
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
                coordinator.async_set_updated_data(str(device))

            def on_event(device_id: str, event: dict[str, Any]) -> None:
                """Handle MQTT connectivity event (called on the event loop)."""
                _LOGGER.debug("processing event update %s for %s", event, device_id)
                coordinator = aws_coordinator_map.get(device_id)
                if coordinator is None:
                    _LOGGER.debug("event data update provided for unknown device: %s", device_id)
                    return
                device = coordinator.blueair_api_device
                map_and_publish_event(event, device)
                coordinator.async_set_updated_data(str(device))

            mqtt_client.on_sensor_data = on_sensor_data
            mqtt_client.on_state_change = on_state_change
            mqtt_client.on_event = on_event

            # Credential refresher for automatic reconnect on token expiry.
            async def refresh_mqtt_credentials() -> tuple[str, str, str]:
                """Refresh the AWS token and return new MQTT credentials."""
                await aws_http_client.refresh_access_token()
                return (
                    aws_http_client.mqtt_auth_name or "",
                    aws_http_client.mqtt_auth_signature or "",
                    aws_http_client.mqtt_auth_token or "",
                )

            mqtt_client.credential_refresher = refresh_mqtt_credentials

            for device in aws_devices:
                mqtt_client.register_device(device.uuid)

            # blueair_api's MQTT client runs on the event loop (aiomqtt); it
            # keeps reconnecting on its own until disconnect().
            await mqtt_client.connect()
            _LOGGER.info("MQTT real-time updates started for %d device(s)", len(aws_devices))

            # Home Assistant does not unload config entries when it stops,
            # so async_unload_entry never runs at shutdown. Disconnect here
            # so the client leaves the broker cleanly instead of trying to
            # reconnect while Home Assistant shuts down.
            connected_client = mqtt_client

            async def stop_mqtt(_event: Event) -> None:
                """Disconnect MQTT when Home Assistant stops."""
                await connected_client.disconnect()

            config_entry.async_on_unload(
                hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_mqtt)
            )
        except Exception:
            _LOGGER.exception("Failed to start MQTT, falling back to polling only")
            if mqtt_client is not None:
                await mqtt_client.disconnect()
            mqtt_client = None
    else:
        _LOGGER.debug("MQTT credentials not available, using polling only")
    return mqtt_client


async def _async_list_device_ids(
    aws_api: HttpAwsBlueair, legacy_api: HttpBlueair | None
) -> set[str]:
    """Return the IDs of every device on the account.

    Args:
        aws_api: Logged-in AWS client.
        legacy_api: Logged-in legacy client, or None to skip legacy devices.

    Returns:
        set[str]: Device UUIDs from both APIs.
    """
    device_ids = {device["uuid"] for device in await aws_api.devices()}
    if legacy_api is not None:
        device_ids |= {device["uuid"] for device in await legacy_api.get_devices()}
    return device_ids


def _async_remove_stale_devices(
    hass: HomeAssistant, config_entry: ConfigEntry, device_ids: set[str]
) -> None:
    """Remove registry devices that are no longer on the Blueair account.

    Removing a device also removes its entities.

    Args:
        hass: Home Assistant instance.
        config_entry: The account's config entry.
        device_ids: UUIDs of the devices the account reports.
    """
    device_registry = dr.async_get(hass)
    for device_entry in dr.async_entries_for_config_entry(device_registry, config_entry.entry_id):
        if not _is_current_device(device_entry, device_ids):
            _LOGGER.info("Removing %s: it is no longer on the Blueair account", device_entry.name)
            device_registry.async_remove_device(device_entry.id)


def _is_current_device(device_entry: dr.DeviceEntry, device_ids: set[str]) -> bool:
    """Return whether a registry device is one of the account's devices."""
    return any(
        domain == DOMAIN and identifier in device_ids
        for domain, identifier in device_entry.identifiers
    )


def _async_watch_device_list(
    hass: HomeAssistant,
    config_entry: BlueairConfigEntry,
    aws_api: HttpAwsBlueair,
    legacy_api: HttpBlueair | None,
    known_ids: set[str],
) -> None:
    """Reload the entry when devices are added to or removed from the account.

    Setup creates the new devices' entities and removes the gone devices.

    Args:
        hass: Home Assistant instance.
        config_entry: The account's config entry.
        aws_api: Logged-in AWS client.
        legacy_api: Logged-in legacy client, or None to skip legacy devices.
        known_ids: UUIDs of the devices set up now.
    """

    async def check_device_list(_now: datetime) -> None:
        try:
            device_ids = await _async_list_device_ids(aws_api, legacy_api)
        except (LoginError, ClientError, TimeoutError) as error:
            # The device coordinators report outages and rejected logins.
            _LOGGER.debug("Unable to list Blueair devices: %s", error)
            return
        if not device_ids or device_ids == known_ids:
            # An empty list is more likely a Blueair glitch than an empty account.
            return
        _LOGGER.info(
            "Blueair devices changed (added: %s, removed: %s); reloading",
            sorted(device_ids - known_ids),
            sorted(known_ids - device_ids),
        )
        hass.config_entries.async_schedule_reload(config_entry.entry_id)

    config_entry.async_on_unload(
        async_track_time_interval(
            hass,
            check_device_list,
            timedelta(minutes=DEVICE_LIST_INTERVAL),
            name="Blueair device list",
        )
    )


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: BlueairConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Let the user delete a device that is no longer on the Blueair account."""
    device_ids = {coordinator.id for coordinator in config_entry.runtime_data.coordinators}
    return not _is_current_device(device_entry, device_ids)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate an old config entry to the current version."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version == 1:
        new_data = {**config_entry.data, CONF_REGION: REGION_USA}
        # Home Assistant rejects assigning config_entry.version directly.
        hass.config_entries.async_update_entry(config_entry, data=new_data, version=2)

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
        legacy_api: HttpBlueair | None = None
        # Whether the legacy device list is known, so gone devices can be removed.
        legacy_listed = True
        try:
            legacy_api, devices = await get_devices(
                username=username, password=password, client_session=client_session
            )
        except LoginError as ex:
            # Accounts without legacy devices have no legacy login.
            _LOGGER.debug("Legacy Login error: %s", ex)
            devices = []
        except (ClientError, TimeoutError) as ex:
            _LOGGER.warning("Legacy Blueair API unavailable, skipping legacy devices: %s", ex)
            devices = []
            legacy_listed = False
        aws_http_client, aws_devices = await get_aws_devices(
            username=username,
            password=password,
            client_session=client_session,
            region=region,
        )

        def create_coordinators(device: Device) -> BlueairUpdateCoordinatorDevice:
            return BlueairUpdateCoordinatorDevice(
                hass=hass,
                config_entry=config_entry,
                blueair_api_device=device,
                interval=interval,
            )

        device_coordinators = list(map(create_coordinators, devices))

        def create_aws_coordinators(device: DeviceAws) -> BlueairUpdateCoordinatorDeviceAws:
            return BlueairUpdateCoordinatorDeviceAws(
                hass=hass,
                config_entry=config_entry,
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
            aws_api=aws_http_client,
            legacy_api=legacy_api,
        )

        device_ids = {coordinator.id for coordinator in coordinators}
        if legacy_listed and device_ids:
            # Skipped for an empty account: that is more likely a Blueair glitch.
            _async_remove_stale_devices(hass, config_entry, device_ids)

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
        _async_watch_device_list(hass, config_entry, aws_http_client, legacy_api, device_ids)
    except LoginError as error:
        # Blueair rejected the stored credentials: ask the user to log in again.
        raise ConfigEntryAuthFailed(
            translation_domain=DOMAIN, translation_key="auth_failed"
        ) from error
    except (ClientError, TimeoutError) as error:
        _LOGGER.debug("blueair cloud unreachable, ha should retry")
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="cannot_connect",
            translation_placeholders={"error": str(error) or type(error).__name__},
        ) from error
    else:
        return True


async def async_unload_entry(hass: HomeAssistant, config_entry: BlueairConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("unload entry")
    # Disconnect MQTT before unloading platforms
    mqtt_client = config_entry.runtime_data.mqtt_client
    if mqtt_client is not None:
        await mqtt_client.disconnect()
        _LOGGER.info("MQTT disconnected")

    return await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)
