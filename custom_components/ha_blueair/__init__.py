"""The Blueair integration."""

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from typing import Any

from aiohttp import ClientError
from aiomqtt import MqttError
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
    CONFIG_FLOW_MINOR_VERSION,
    DEFAULT_SCAN_INTERVAL,
    DEVICE_LIST_INTERVAL,
    DOMAIN,
    MQTT_SCAN_INTERVAL,
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
        unreachable: Coordinators of devices whose first poll failed. They get
            no entities until a retry succeeds and the entry reloads.
    """

    devices: list[BlueairUpdateCoordinatorDevice]
    aws_devices: list[BlueairUpdateCoordinatorDeviceAws]
    mqtt_client: MqttAwsBlueair | None = None
    aws_api: HttpAwsBlueair | None = None
    legacy_api: HttpBlueair | None = None
    unreachable: list[BlueairUpdateCoordinator] = field(default_factory=list)

    @property
    def coordinators(self) -> list[BlueairUpdateCoordinator]:
        """Return every set-up device coordinator for the entry, legacy first."""
        return [*self.devices, *self.aws_devices]


type BlueairConfigEntry = ConfigEntry[BlueairRuntimeData]

# Errors a malformed MQTT payload can raise while blueair_api applies it to
# the device. blueair_api's MQTT client also logs anything else a callback
# raises, so an unexpected error can't stop the message loop.
_PAYLOAD_ERRORS = (AttributeError, KeyError, TypeError, ValueError)


class _MqttPolling:
    """Poll AWS devices less often while MQTT pushes their updates.

    MQTT delivers changes within seconds, so polling is only a fallback for
    missed messages while it is connected. When the connection drops, the
    devices go back to the configured interval and poll right away.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        coordinators: Sequence[BlueairUpdateCoordinatorDeviceAws],
        interval: int,
    ) -> None:
        """Initialize the polling adjuster.

        Args:
            hass: Home Assistant instance.
            config_entry: The account's config entry, which owns the refresh tasks.
            coordinators: Coordinators of the devices MQTT updates.
            interval: Configured polling interval in minutes.
        """
        self._hass = hass
        self._config_entry = config_entry
        self._coordinators = coordinators
        self._poll_interval = timedelta(minutes=interval)
        self._mqtt_interval = timedelta(minutes=max(interval, MQTT_SCAN_INTERVAL))
        self._connected = False
        self._has_connected = False

    def on_connect(self) -> None:
        """Lengthen the polling interval (called on the event loop)."""
        reconnected = self._has_connected and not self._connected
        self._connected = self._has_connected = True
        _LOGGER.debug("MQTT connected; polling AWS devices every %s", self._mqtt_interval)
        self._set_interval(self._mqtt_interval)
        if reconnected:
            # Updates pushed while disconnected were missed.
            self._request_refresh()

    def on_disconnect(self) -> None:
        """Restore the configured polling interval (called on the event loop).

        The client calls this after every failed reconnect attempt too; only
        the first call after a connection changes anything.
        """
        if not self._connected:
            return
        self._connected = False
        _LOGGER.debug("MQTT disconnected; polling AWS devices every %s", self._poll_interval)
        self._set_interval(self._poll_interval)
        # The next scheduled poll may still be a full MQTT interval away.
        self._request_refresh()

    def _set_interval(self, interval: timedelta) -> None:
        """Set every coordinator's polling interval.

        Args:
            interval: The new polling interval.
        """
        for coordinator in self._coordinators:
            coordinator.update_interval = interval

    def _request_refresh(self) -> None:
        """Ask every coordinator for a (debounced) refresh."""
        for coordinator in self._coordinators:
            self._config_entry.async_create_task(
                self._hass,
                coordinator.async_request_refresh(),
                f"Blueair refresh {coordinator.device_name}",
            )


async def _async_start_mqtt(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    region: str,
    aws_http_client: HttpAwsBlueair,
    aws_coordinators: list[BlueairUpdateCoordinatorDeviceAws],
    interval: int,
) -> MqttAwsBlueair | None:
    """Start MQTT real-time updates for AWS devices.

    Args:
        hass: Home Assistant instance.
        config_entry: The account's config entry.
        region: Blueair cloud region.
        aws_http_client: Logged-in AWS client holding the MQTT credentials.
        aws_coordinators: Coordinators of the AWS devices to subscribe to.
        interval: Configured polling interval in minutes.

    Returns:
        The connected MQTT client, or None when MQTT is unavailable and the
        integration falls back to polling only.
    """
    aws_devices: list[DeviceAws] = [c.blueair_api_device for c in aws_coordinators]
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
                except _PAYLOAD_ERRORS:
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
                except _PAYLOAD_ERRORS:
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

            # Set before connect(): the client calls on_connect_callback for the
            # first connection too.
            polling = _MqttPolling(hass, config_entry, aws_coordinators, interval)
            mqtt_client.on_connect_callback = polling.on_connect
            mqtt_client.on_disconnect_callback = polling.on_disconnect

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
        except MqttError, OSError, TimeoutError, ValueError:
            # MqttError: the broker refused or dropped the first connection;
            # OSError: network or TLS failures; ValueError: no broker for the
            # region. Anything else is a bug and fails setup visibly.
            _LOGGER.exception("Failed to start MQTT, falling back to polling only")
            if mqtt_client is not None:
                await mqtt_client.disconnect()
            mqtt_client = None
            for coordinator in aws_coordinators:
                coordinator.update_interval = timedelta(minutes=interval)
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


async def _async_first_refresh(
    coordinators: Sequence[BlueairUpdateCoordinator],
) -> list[BlueairUpdateCoordinator]:
    """Poll every device once, in parallel, before its entities are created.

    One unreachable device doesn't hold back the rest of the account: its
    coordinator is returned so setup can skip it and retry it later.

    Args:
        coordinators: Coordinators of the account's devices.

    Returns:
        list[BlueairUpdateCoordinator]: Coordinators whose first poll failed.

    Raises:
        ConfigEntryAuthFailed: Blueair rejected the stored credentials.
        ConfigEntryNotReady: No device could be polled.
    """
    results = await asyncio.gather(
        *(coordinator.async_config_entry_first_refresh() for coordinator in coordinators),
        return_exceptions=True,
    )
    unreachable: list[BlueairUpdateCoordinator] = []
    first_error: ConfigEntryNotReady | None = None
    for coordinator, result in zip(coordinators, results, strict=True):
        if isinstance(result, ConfigEntryNotReady):
            _LOGGER.warning(
                "Blueair device %s is unreachable; setting up the account without it: %s",
                coordinator.device_name,
                result.__cause__ or result,
            )
            unreachable.append(coordinator)
            first_error = first_error or result
        elif isinstance(result, BaseException):
            # ConfigEntryAuthFailed and anything unexpected fail the whole setup.
            raise result
    if first_error is not None and len(unreachable) == len(coordinators):
        raise first_error
    return unreachable


def _async_retry_unreachable_devices(
    hass: HomeAssistant,
    config_entry: BlueairConfigEntry,
    unreachable: Sequence[BlueairUpdateCoordinator],
    interval: int,
) -> None:
    """Poll devices that were unreachable at setup, and reload once one answers.

    Their capabilities, and so their entities, are only known after a
    successful poll, so the reload is what creates their entities.

    Args:
        hass: Home Assistant instance.
        config_entry: The account's config entry.
        unreachable: Coordinators whose first poll failed.
        interval: Polling interval in minutes.
    """
    if not unreachable:
        return

    async def retry(_now: datetime) -> None:
        """Poll the unreachable devices and reload when one succeeds.

        Args:
            _now: Time of the retry (unused).
        """
        for coordinator in unreachable:
            # The coordinator turns failures into last_update_success = False
            # and starts reauthentication on a rejected login.
            await coordinator.async_refresh()
            if coordinator.last_update_success:
                _LOGGER.info(
                    "Blueair device %s is reachable again; reloading", coordinator.device_name
                )
                hass.config_entries.async_schedule_reload(config_entry.entry_id)
                return

    config_entry.async_on_unload(
        async_track_time_interval(
            hass, retry, timedelta(minutes=interval), name="Blueair unreachable devices"
        )
    )


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: BlueairConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Let the user delete a device that is no longer on the Blueair account."""
    runtime_data = config_entry.runtime_data
    device_ids = {
        coordinator.id for coordinator in [*runtime_data.coordinators, *runtime_data.unreachable]
    }
    return not _is_current_device(device_entry, device_ids)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate an old config entry to the current version.

    Args:
        hass: Home Assistant instance.
        config_entry: The entry to migrate.

    Home Assistant refuses entries from a newer version (a downgrade) before
    calling this.

    Returns:
        bool: True once the entry is migrated.
    """
    _LOGGER.debug("Migrating from version %s.%s", config_entry.version, config_entry.minor_version)

    if config_entry.version == 1:
        new_data = {**config_entry.data, CONF_REGION: REGION_USA}
        # Home Assistant rejects assigning config_entry.version directly.
        hass.config_entries.async_update_entry(
            config_entry, data=new_data, version=2, minor_version=1
        )

    if config_entry.version == 2 and config_entry.minor_version < 2:
        # Unique IDs are lowercase usernames from 2.2, so the same account typed
        # with different capitalization is recognized as already configured.
        unique_id = config_entry.unique_id
        if unique_id is not None and unique_id.lower() != unique_id:
            new_unique_id = unique_id.lower()
            taken = hass.config_entries.async_entry_for_domain_unique_id(DOMAIN, new_unique_id)
            if taken is None:
                hass.config_entries.async_update_entry(config_entry, unique_id=new_unique_id)
            else:
                _LOGGER.warning(
                    "Blueair account %s is configured twice; keeping this entry's unique ID",
                    new_unique_id,
                )
        hass.config_entries.async_update_entry(
            config_entry, minor_version=CONFIG_FLOW_MINOR_VERSION
        )

    _LOGGER.info(
        "Migration to version %s.%s successful", config_entry.version, config_entry.minor_version
    )

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

        unreachable = await _async_first_refresh(coordinators)
        device_coordinators = [c for c in device_coordinators if c not in unreachable]
        aws_coordinators = [c for c in aws_coordinators if c not in unreachable]

        mqtt_client = await _async_start_mqtt(
            hass, config_entry, region, aws_http_client, aws_coordinators, interval
        )

        config_entry.runtime_data = BlueairRuntimeData(
            devices=device_coordinators,
            aws_devices=aws_coordinators,
            mqtt_client=mqtt_client,
            aws_api=aws_http_client,
            legacy_api=legacy_api,
            unreachable=unreachable,
        )

        # Unreachable devices are still on the account: keep them in the
        # registry, and don't treat them as added by the device list check.
        device_ids = {coordinator.id for coordinator in coordinators}
        if legacy_listed and device_ids:
            # Skipped for an empty account: that is more likely a Blueair glitch.
            _async_remove_stale_devices(hass, config_entry, device_ids)

        await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
        _LOGGER.debug("integration setup completed")

        # Options changes reload the entry (OptionsFlowWithReload), so the
        # polling interval and the fans' preset lists are only read here.
        _async_watch_device_list(hass, config_entry, aws_http_client, legacy_api, device_ids)
        _async_retry_unreachable_devices(hass, config_entry, unreachable, interval)
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
