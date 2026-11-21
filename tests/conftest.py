"""Shared pytest fixtures for Blueair Home Assistant workflow tests."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import fields
from pathlib import Path
from types import SimpleNamespace
from typing import Any, ClassVar
from unittest.mock import patch

from blueair_api import Device, DeviceAws
from homeassistant.const import CONF_PASSWORD, CONF_REGION, CONF_USERNAME
import pytest

import custom_components

USERNAME = "user@example.com"
PASSWORD = "hunter2-not-a-real-password"
REGION = "us"

# DeviceAws fields that identify the device rather than describe a capability.
_AWS_IDENTITY_FIELDS = {"api", "raw_info", "raw_sensors", "uuid", "name_api", "mac", "type_name"}


class FakeAwsApi:
    """Stand-in for blueair_api's HttpAwsBlueair, recording every device write."""

    def __init__(self) -> None:
        """Start with no writes and no configured failure."""
        self.writes: list[tuple[str, str, Any]] = []
        self.error: BaseException | None = None

    async def set_device_info(self, uuid: str, key: str, kind: str, value: Any) -> None:
        """Record a device attribute write.

        Args:
            uuid: Device uuid.
            key: Attribute key Blueair uses.
            kind: Value kind ("v" for numbers, "vb" for booleans).
            value: Value written.

        Raises:
            BaseException: The configured ``error``.
        """
        if self.error is not None:
            raise self.error
        self.writes.append((uuid, key, value))


class RefreshlessDeviceAws(DeviceAws):
    """Real DeviceAws whose refresh keeps the attributes a test set.

    The real refresh parses a full device-info payload; tests set attributes
    directly instead, and use ``refresh_error`` to drive polling failures.
    """

    refresh_error: BaseException | None = None
    refresh_count = 0

    async def refresh(self) -> None:
        """Count the poll, or raise the configured error.

        Raises:
            BaseException: The configured ``refresh_error``.
        """
        self.refresh_count += 1
        if self.refresh_error is not None:
            raise self.refresh_error


def make_aws_device(
    *, uuid: str = "aws-1", name: str = "Bedroom", api: FakeAwsApi | None = None, **attributes: Any
) -> RefreshlessDeviceAws:
    """Build an AWS device that supports only the given attributes.

    Every capability attribute starts as NotImplemented, which is what the
    real refresh reports for features a model lacks.

    Args:
        uuid: Device uuid.
        name: Device name.
        api: Fake API that records writes; a new one by default.
        attributes: Capability attributes the device supports, with values.

    Returns:
        RefreshlessDeviceAws: The device.
    """
    device = RefreshlessDeviceAws(
        api=api or FakeAwsApi(),
        uuid=uuid,
        name_api=name,
        mac=f"00:11:22:33:44:{len(uuid):02x}",
        type_name="device",
    )
    for item in fields(DeviceAws):
        if item.name not in _AWS_IDENTITY_FIELDS and item.default is None and item.init:
            setattr(device, item.name, NotImplemented)
    device.name = name
    # Normally set by the real refresh; diagnostics include them.
    device.raw_info = {"configuration": {"di": {"name": name}}}
    device.raw_sensors = []
    for key, value in {
        "firmware": "1.0.0",
        "mcu_firmware": "2.0.0",
        "overall_firmware": "3.0.0",
        "serial_number": f"SN-{uuid}",
        "sku": "111633",
        "wifi_working": True,
        **attributes,
    }.items():
        setattr(device, key, value)
    return device


def make_purifier(**overrides: Any) -> RefreshlessDeviceAws:
    """Build an AWS purifier with fan, lights, switches and air-quality sensors.

    Args:
        overrides: Attribute overrides.

    Returns:
        RefreshlessDeviceAws: The purifier.
    """
    return make_aws_device(
        **{
            "uuid": "purifier-1",
            "name": "Bedroom",
            "hw": "high_1.5",
            "standby": False,
            "fan_speed": 37,
            "fan_auto_mode": False,
            "night_mode": False,
            "brightness": 50,
            "mood_brightness": 40,
            "child_lock": False,
            "germ_shield": True,
            "pm1": 3,
            "pm2_5": 5,
            "pm10": 7,
            "voc": 120,
            "temperature": 21,
            "humidity": 40,
            "filter_usage_percentage": 25,
            "rssi": -60,
            **overrides,
        }
    )


def make_humidifier(**overrides: Any) -> RefreshlessDeviceAws:
    """Build an AWS humidifier (H35i-style) with wick, water and night-light readings.

    Args:
        overrides: Attribute overrides.

    Returns:
        RefreshlessDeviceAws: The humidifier.
    """
    return make_aws_device(
        **{
            "uuid": "humidifier-1",
            "name": "Nursery",
            "hw": "hum1_l",
            "standby": False,
            "fan_speed": 2,
            "fan_auto_mode": False,
            "night_mode": False,
            "child_lock": False,
            "auto_regulated_humidity": 45,
            "wick_dry_mode": False,
            "wick_usage_percentage": 30,
            "water_refresher_usage_percentage": 10,
            "water_shortage": False,
            "water_level": 80,
            "night_light_brightness": 40,
            "humidity": 38,
            "temperature": 22,
            "timer_state": 0,
            "timer_duration": 3600,
            "hour_format": True,
            **overrides,
        }
    )


def make_combo(**overrides: Any) -> RefreshlessDeviceAws:
    """Build an AWS 2-in-1 purify + humidify combo (DH3i-style).

    Args:
        overrides: Attribute overrides.

    Returns:
        RefreshlessDeviceAws: The combo device.
    """
    return make_aws_device(
        **{
            "uuid": "combo-1",
            "name": "Living Room",
            "hw": "s_cmb2in1",
            "standby": False,
            "fan_speed": 37,
            "fan_auto_mode": False,
            "humidifier_mode": True,
            "combo_mode": 2,
            "auto_regulated_humidity": 50,
            "humidity": 42,
            "pm2_5": 4,
            **overrides,
        }
    )


def make_climate_device(**overrides: Any) -> RefreshlessDeviceAws:
    """Build an AWS heater / cooler purifier (T10i / T20i-style).

    Args:
        overrides: Attribute overrides.

    Returns:
        RefreshlessDeviceAws: The climate device.
    """
    return make_aws_device(
        **{
            "uuid": "climate-1",
            "name": "Office",
            "hw": "t10i",
            "standby": False,
            "fan_speed": 37,
            "main_mode": 1,
            "heat_temp": 220,
            "heat_sub_mode": 1,
            "heat_fan_speed": 37,
            "cool_sub_mode": 1,
            "cool_fan_speed": 37,
            "ap_sub_mode": 1,
            "fan_speed_0": 37,
            "temperature_unit": 0,
            "temperature": 20,
            "humidity": 35,
            "pm2_5": 2,
            **overrides,
        }
    )


class FakeLegacyApi:
    """Stand-in for blueair_api's legacy HttpBlueair, used by real Device objects."""

    def __init__(self) -> None:
        """Start with a Classic purifier's attributes and one data point."""
        self.attributes: dict[str, str] = {
            "brightness": "2",
            "child_lock": "0",
            "night_mode": "0",
            "fan_speed": "2",
            "filter_status": "OK",
            "mode": "manual",
            "wifi_status": "1",
        }
        self.data_points: dict[str, Any] = {
            "sensors": ["time", "pm", "pm1", "pm10", "tmp", "hum", "co2", "voc", "allpollu"],
            "datapoints": [[1700000000, 6, 2, 9, 21, 45, 600, 150, 10]],
        }
        self.writes: list[tuple[str, Any]] = []
        self.error: BaseException | None = None

    async def get_attributes(self, uuid: str) -> dict[str, str]:
        """Return the device attributes.

        Args:
            uuid: Device uuid.

        Returns:
            dict[str, str]: Attributes as the legacy API reports them.

        Raises:
            BaseException: The configured ``error``.
        """
        if self.error is not None:
            raise self.error
        return dict(self.attributes)

    async def get_data_points_since(self, uuid: str) -> dict[str, Any]:
        """Return the latest measurements.

        Args:
            uuid: Device uuid.

        Returns:
            dict[str, Any]: Sensor names and data points.
        """
        return self.data_points

    async def _write(self, name: str, value: Any) -> None:
        """Record a write, or raise the configured error.

        Args:
            name: Setting written.
            value: Value written.

        Raises:
            BaseException: The configured ``error``.
        """
        if self.error is not None:
            raise self.error
        self.writes.append((name, value))

    async def set_fan_speed(self, uuid: str, value: Any) -> None:
        """Record a fan speed write."""
        await self._write("fan_speed", value)

    async def set_brightness(self, uuid: str, value: Any) -> None:
        """Record a brightness write."""
        await self._write("brightness", value)

    async def set_child_lock(self, uuid: str, value: Any) -> None:
        """Record a child lock write."""
        await self._write("child_lock", value)

    async def set_fan_auto_mode(self, uuid: str, value: Any) -> None:
        """Record a fan auto mode write."""
        await self._write("fan_auto_mode", value)


def make_legacy_device(
    *, uuid: str = "legacy-1", name: str = "Hallway", compatibility: str = "classic_680i"
) -> Device:
    """Build a real legacy Device that refreshes through FakeLegacyApi.

    Args:
        uuid: Device uuid.
        name: Device name.
        compatibility: Legacy model identifier.

    Returns:
        Device: The device; its fake API is ``device.api``.
    """
    return Device(
        api=FakeLegacyApi(),
        uuid=uuid,
        name=name,
        mac="aa:bb:cc:dd:ee:ff",
        compatibility=compatibility,
        model=compatibility,
        firmware="1.2",
        mcu_firmware="3.4",
        room_location="hallway",
    )


class FakeBlueairCloud:
    """Stand-in for blueair_api's login helpers, the integration's only cloud boundary.

    Each call records its arguments. Setting ``aws_error`` or ``legacy_error``
    makes the matching helper raise, so tests can drive the failure paths.
    """

    def __init__(self) -> None:
        """Start with an account that has no devices and no MQTT credentials.

        Tests add devices to ``aws_devices`` and ``legacy_devices``.
        """
        self.aws_calls: list[dict[str, Any]] = []
        self.legacy_calls: list[dict[str, Any]] = []
        self.aws_error: BaseException | None = None
        self.legacy_error: BaseException | None = None
        self.cleanup_calls = 0
        self.aws_devices: list[Any] = []
        self.legacy_devices: list[Any] = []
        self.mqtt_credentials = False
        self.token_refreshes = 0
        self.list_error: BaseException | None = None

    async def list_aws_devices(self) -> list[dict[str, str]]:
        """List the AWS devices the way HttpAwsBlueair.devices does.

        Returns:
            list[dict[str, str]]: One entry per device in ``aws_devices``.

        Raises:
            BaseException: The configured ``list_error``.
        """
        if self.list_error is not None:
            raise self.list_error
        return [{"uuid": device.uuid, "name": device.name} for device in self.aws_devices]

    async def list_legacy_devices(self) -> list[dict[str, str]]:
        """List the legacy devices the way HttpBlueair.get_devices does.

        Returns:
            list[dict[str, str]]: One entry per device in ``legacy_devices``.
        """
        return [{"uuid": device.uuid, "name": device.name} for device in self.legacy_devices]

    async def refresh_access_token(self) -> None:
        """Record an AWS token refresh for MQTT reconnects."""
        self.token_refreshes += 1

    async def cleanup_client_session(self) -> None:
        """Record that the config flow closed the session it opened."""
        self.cleanup_calls += 1

    async def get_aws_devices(self, **kwargs: Any) -> tuple[Any, list[Any]]:
        """Return an AWS HTTP client without MQTT credentials and no devices.

        Args:
            kwargs: Arguments the integration passed.

        Returns:
            tuple[Any, list[Any]]: The client and its devices.

        Raises:
            BaseException: The configured ``aws_error``.
        """
        self.aws_calls.append(kwargs)
        if self.aws_error is not None:
            raise self.aws_error
        has_mqtt = self.mqtt_credentials
        client = SimpleNamespace(
            mqtt_auth_name="name" if has_mqtt else None,
            mqtt_auth_signature="signature" if has_mqtt else None,
            mqtt_auth_token="token" if has_mqtt else None,
            user_id="user-id" if has_mqtt else None,
            cleanup_client_session=self.cleanup_client_session,
            refresh_access_token=self.refresh_access_token,
            devices=self.list_aws_devices,
        )
        return client, list(self.aws_devices)

    async def get_devices(self, **kwargs: Any) -> tuple[Any, list[Any]]:
        """Return no legacy devices.

        Args:
            kwargs: Arguments the integration passed.

        Returns:
            tuple[Any, list[Any]]: The client and its devices.

        Raises:
            BaseException: The configured ``legacy_error``.
        """
        self.legacy_calls.append(kwargs)
        if self.legacy_error is not None:
            raise self.legacy_error
        return SimpleNamespace(get_devices=self.list_legacy_devices), list(self.legacy_devices)


def entry_data(username: str = USERNAME) -> dict[str, str]:
    """Return config entry data for a Blueair account.

    Args:
        username: Account username.

    Returns:
        dict[str, str]: Config entry data.
    """
    return {CONF_USERNAME: username, CONF_PASSWORD: PASSWORD, CONF_REGION: REGION}


@pytest.fixture(autouse=True, scope="session")
def restrict_custom_components_path() -> Iterator[None]:
    """Limit ``custom_components`` to this repository's real directory.

    An editable install adds a setuptools path-hook placeholder to the
    ``custom_components`` namespace path, which Home Assistant iterates while
    creating the ``hass`` fixture.

    Yields:
        None: Control while the restricted path is active.
    """
    components_path = str(Path(__file__).parents[1] / "custom_components")
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(custom_components, "__path__", [components_path])
        yield


@pytest.fixture
def blueair_cloud(enable_custom_integrations: None) -> Iterator[FakeBlueairCloud]:
    """Patch blueair_api's login helpers wherever the integration imports them.

    Args:
        enable_custom_integrations: Lets Home Assistant load the integration.

    Yields:
        FakeBlueairCloud: The fake cloud.
    """
    cloud = FakeBlueairCloud()
    with (
        patch("custom_components.ha_blueair.get_aws_devices", cloud.get_aws_devices),
        patch("custom_components.ha_blueair.get_devices", cloud.get_devices),
        patch("custom_components.ha_blueair.config_flow.get_aws_devices", cloud.get_aws_devices),
    ):
        yield cloud


@pytest.fixture
async def setup_blueair(hass: Any, blueair_cloud: FakeBlueairCloud) -> Any:
    """Return a helper that loads a Blueair entry with the given devices.

    Args:
        hass: Home Assistant instance.
        blueair_cloud: Fake cloud the entry logs in to.

    Returns:
        Callable: ``await setup(aws=[...], legacy=[...], options={...})`` returning the entry.
    """
    from pytest_homeassistant.common import MockConfigEntry  # noqa: PLC0415

    from custom_components.ha_blueair.const import DOMAIN  # noqa: PLC0415

    async def _setup(
        *, aws: list[Any] | None = None, legacy: list[Any] | None = None, options: Any = None
    ) -> Any:
        blueair_cloud.aws_devices = list(aws or [])
        blueair_cloud.legacy_devices = list(legacy or [])
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id=USERNAME,
            title=USERNAME,
            data=entry_data(),
            options=options or {},
            version=2,
        )
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        return entry

    return _setup


class FakeMqtt:
    """Stand-in for blueair_api's MqttAwsBlueair; the integration sets its callbacks.

    ``instances`` collects every client the integration created, so a test can
    drive the callbacks the way the client does on the event loop.
    """

    instances: ClassVar[list[FakeMqtt]] = []
    connect_error: BaseException | None = None

    def __init__(self, **kwargs: Any) -> None:
        """Record the connection arguments.

        Args:
            kwargs: MQTT credentials and region.
        """
        self.kwargs = kwargs
        self.registered: list[str] = []
        self.connected = False
        self.disconnects = 0
        self.on_sensor_data: Any = None
        self.on_state_change: Any = None
        self.on_event: Any = None
        self.credential_refresher: Any = None
        FakeMqtt.instances.append(self)

    def register_device(self, uuid: str) -> None:
        """Record a device subscription.

        Args:
            uuid: Device uuid.
        """
        self.registered.append(uuid)

    async def connect(self) -> None:
        """Connect, or raise the configured error.

        Raises:
            BaseException: The configured ``connect_error``.
        """
        if FakeMqtt.connect_error is not None:
            raise FakeMqtt.connect_error
        self.connected = True

    async def disconnect(self) -> None:
        """Record a disconnect."""
        self.disconnects += 1


@pytest.fixture
def fake_mqtt(blueair_cloud: FakeBlueairCloud) -> Iterator[type[FakeMqtt]]:
    """Give the account MQTT credentials and patch the MQTT client.

    Args:
        blueair_cloud: Fake cloud whose AWS login returns MQTT credentials.

    Yields:
        type[FakeMqtt]: The fake client class; created clients are in ``instances``.
    """
    blueair_cloud.mqtt_credentials = True
    FakeMqtt.instances = []
    FakeMqtt.connect_error = None
    with patch("custom_components.ha_blueair.MqttAwsBlueair", FakeMqtt):
        yield FakeMqtt


def entity_object(hass: Any, entity_id: str) -> Any:
    """Return the live entity object for an entity ID.

    Lets tests call entity methods directly where Home Assistant's service
    layer would reject the input first.

    Args:
        hass: Home Assistant instance.
        entity_id: Entity ID.

    Returns:
        Any: The entity.
    """
    from homeassistant.helpers.entity_component import DATA_INSTANCES  # noqa: PLC0415

    entity = hass.data[DATA_INSTANCES][entity_id.split(".", maxsplit=1)[0]].get_entity(entity_id)
    assert entity is not None
    return entity
