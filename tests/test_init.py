"""Tests for Blueair config entry setup and unload."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from unittest.mock import patch

from aiohttp import ClientConnectionError
from blueair_api import LoginError, MqttError
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import REQUEST_REFRESH_DEFAULT_COOLDOWN
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed

from custom_components.ha_blueair import BlueairRuntimeData
from custom_components.ha_blueair.const import CONF_CLOUD_REGION, DOMAIN
from custom_components.ha_blueair.coordinator import BlueairUpdateCoordinator

from .conftest import (
    USERNAME,
    FakeBlueairCloud,
    FakeMqtt,
    entry_data,
    make_humidifier,
    make_legacy_device,
    make_purifier,
)


def _add_entry(hass: HomeAssistant, username: str = USERNAME) -> MockConfigEntry:
    """Add a Blueair config entry for an account.

    Args:
        hass: Home Assistant instance.
        username: Account username.

    Returns:
        MockConfigEntry: The added entry.
    """
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=username, title=username, data=entry_data(username), version=2
    )
    entry.add_to_hass(hass)
    return entry


@pytest.mark.asyncio
async def test_setup_stores_runtime_data_on_the_entry(
    hass: HomeAssistant, blueair_cloud: FakeBlueairCloud
) -> None:
    """Keep the account's coordinators and MQTT client on ConfigEntry.runtime_data."""
    entry = _add_entry(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)

    assert entry.state is ConfigEntryState.LOADED
    assert isinstance(entry.runtime_data, BlueairRuntimeData)
    assert entry.runtime_data.coordinators == []
    assert entry.runtime_data.mqtt_client is None
    assert DOMAIN not in hass.data or not isinstance(hass.data[DOMAIN], dict)


@pytest.mark.asyncio
async def test_two_accounts_load_and_unload_independently(
    hass: HomeAssistant, blueair_cloud: FakeBlueairCloud
) -> None:
    """Let a second Blueair account load, and unload, without touching the first."""
    first = _add_entry(hass, "first@example.com")
    second = _add_entry(hass, "second@example.com")
    # Loading the integration sets up every entry for the domain.
    assert await hass.config_entries.async_setup(first.entry_id)
    await hass.async_block_till_done()

    assert first.state is ConfigEntryState.LOADED
    assert second.state is ConfigEntryState.LOADED
    assert first.runtime_data is not second.runtime_data

    assert await hass.config_entries.async_unload(second.entry_id)
    await hass.async_block_till_done()

    assert second.state is ConfigEntryState.NOT_LOADED
    assert first.state is ConfigEntryState.LOADED
    assert isinstance(first.runtime_data, BlueairRuntimeData)


@pytest.mark.asyncio
async def test_setup_retries_when_blueair_is_unreachable(
    hass: HomeAssistant, blueair_cloud: FakeBlueairCloud
) -> None:
    """Retry setup later when Blueair cannot be reached."""
    blueair_cloud.aws_error = ClientConnectionError("offline")
    entry = _add_entry(hass)

    await hass.config_entries.async_setup(entry.entry_id)

    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert entry.error_reason_translation_key == "cannot_connect"
    assert entry.error_reason_translation_placeholders == {"error": "offline"}


@pytest.mark.asyncio
async def test_rejected_login_starts_reauthentication(
    hass: HomeAssistant, blueair_cloud: FakeBlueairCloud
) -> None:
    """Ask the user to log in again instead of retrying a rejected password forever."""
    blueair_cloud.aws_error = LoginError("bad password")
    entry = _add_entry(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert [flow["context"]["source"] for flow in flows] == ["reauth"]
    assert flows[0]["step_id"] == "reauth_confirm"


@pytest.mark.asyncio
async def test_setup_skips_an_unreachable_legacy_api(
    hass: HomeAssistant, blueair_cloud: FakeBlueairCloud
) -> None:
    """Load AWS devices even when the legacy Blueair API is down."""
    blueair_cloud.legacy_error = ClientConnectionError("legacy offline")
    entry = _add_entry(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)

    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.devices == []


@pytest.mark.asyncio
async def test_mqtt_starts_for_aws_devices_and_stops_on_unload(
    hass: HomeAssistant, setup_blueair: Any, fake_mqtt: type[FakeMqtt]
) -> None:
    """Subscribe every AWS device to MQTT, and disconnect when the entry unloads."""
    entry = await setup_blueair(aws=[make_purifier(), make_humidifier()])

    client = fake_mqtt.instances[0]
    assert entry.runtime_data.mqtt_client is client
    assert client.connected
    assert client.registered == ["purifier-1", "humidifier-1"]
    assert client.kwargs["user_id"] == "user-id"

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert client.disconnects == 1


@pytest.mark.asyncio
async def test_mqtt_disconnects_when_home_assistant_stops(
    hass: HomeAssistant, setup_blueair: Any, fake_mqtt: type[FakeMqtt]
) -> None:
    """Disconnect MQTT at shutdown, since entries are not unloaded then."""
    await setup_blueair(aws=[make_purifier()])

    hass.bus.async_fire(EVENT_HOMEASSISTANT_STOP)
    await hass.async_block_till_done()

    assert fake_mqtt.instances[0].disconnects == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        MqttError("TLS handshake failed"),
        OSError("network unreachable"),
        TimeoutError(),
        ValueError("No MQTT broker configured for region: xx"),
    ],
)
async def test_mqtt_connect_failure_falls_back_to_polling(
    hass: HomeAssistant, setup_blueair: Any, fake_mqtt: type[FakeMqtt], error: Exception
) -> None:
    """Keep the entry working by polling when MQTT cannot connect."""
    fake_mqtt.connect_error = error

    entry = await setup_blueair(aws=[make_purifier()])

    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.mqtt_client is None
    assert fake_mqtt.instances[0].disconnects == 1


@pytest.mark.asyncio
async def test_mqtt_connect_failure_keeps_the_polling_interval(
    hass: HomeAssistant, setup_blueair: Any, fake_mqtt: type[FakeMqtt]
) -> None:
    """Poll at the configured interval when MQTT never connects."""
    fake_mqtt.connect_error = MqttError("TLS handshake failed")

    entry = await setup_blueair(aws=[make_purifier()])

    assert entry.runtime_data.aws_devices[0].update_interval == timedelta(minutes=5)


@pytest.mark.asyncio
@pytest.mark.parametrize(("scan_interval", "mqtt_minutes"), [(5, 30), (20, 30), (30, 30)])
async def test_mqtt_lengthens_polling_while_connected(
    hass: HomeAssistant,
    setup_blueair: Any,
    fake_mqtt: type[FakeMqtt],
    scan_interval: int,
    mqtt_minutes: int,
) -> None:
    """Poll AWS devices every 30 minutes (or longer) while MQTT pushes their updates."""
    entry = await setup_blueair(
        aws=[make_purifier()],
        legacy=[make_legacy_device()],
        options={"scan_interval": scan_interval},
    )

    assert entry.runtime_data.aws_devices[0].update_interval == timedelta(minutes=mqtt_minutes)
    # Legacy devices get no MQTT updates.
    assert entry.runtime_data.devices[0].update_interval == timedelta(minutes=scan_interval)


async def _advance(hass: HomeAssistant, delta: timedelta) -> None:
    """Fire the timers due within ``delta`` and let their tasks finish."""
    async_fire_time_changed(hass, dt_util.utcnow() + delta)
    await hass.async_block_till_done()


@pytest.mark.asyncio
async def test_mqtt_disconnect_restores_polling_and_reconnect_refreshes(
    hass: HomeAssistant, setup_blueair: Any, fake_mqtt: type[FakeMqtt]
) -> None:
    """Poll right away at the normal interval while MQTT is down, and catch up on reconnect."""
    device = make_purifier()
    entry = await setup_blueair(aws=[device])
    coordinator = entry.runtime_data.aws_devices[0]
    client = fake_mqtt.instances[0]
    polls = device.refresh_count

    client.on_disconnect_callback()
    # Every failed reconnect attempt reports a disconnect too.
    client.on_disconnect_callback()
    await _advance(hass, timedelta(seconds=REQUEST_REFRESH_DEFAULT_COOLDOWN + 1))

    assert coordinator.update_interval == timedelta(minutes=5)
    assert device.refresh_count == polls + 1

    client.on_connect_callback()
    await _advance(hass, timedelta(seconds=2 * REQUEST_REFRESH_DEFAULT_COOLDOWN + 2))

    assert coordinator.update_interval == timedelta(minutes=30)
    # The catch-up poll waits until a full polling interval has passed since the last one.
    assert device.refresh_count == polls + 1

    await _advance(hass, timedelta(minutes=5, seconds=REQUEST_REFRESH_DEFAULT_COOLDOWN + 1))

    assert device.refresh_count == polls + 2


@pytest.mark.asyncio
async def test_flapping_mqtt_polls_at_most_once_per_interval(
    hass: HomeAssistant, setup_blueair: Any, fake_mqtt: type[FakeMqtt]
) -> None:
    """A connection that keeps dropping must not poll every device on every attempt."""
    device = make_purifier()
    await setup_blueair(aws=[device])
    client = fake_mqtt.instances[0]
    polls = device.refresh_count

    start = dt_util.utcnow()
    elapsed = timedelta()

    async def tick() -> None:
        nonlocal elapsed
        elapsed += timedelta(seconds=8)
        async_fire_time_changed(hass, start + elapsed)
        await hass.async_block_till_done()

    # Twenty reconnect cycles, 16 seconds apart (5 minutes 20 seconds in all).
    for _ in range(20):
        client.on_disconnect_callback()
        await tick()
        client.on_connect_callback()
        await tick()

    # The poll on the first disconnect, the regular poll at the configured
    # 5-minute interval, and one merged catch-up when the window ended,
    # instead of two polls per reconnect cycle.
    assert device.refresh_count == polls + 3


@pytest.mark.asyncio
async def test_unloading_cancels_a_held_catch_up_poll(
    hass: HomeAssistant, setup_blueair: Any, fake_mqtt: type[FakeMqtt]
) -> None:
    """A catch-up poll held for the end of its window is dropped on unload."""
    device = make_purifier()
    entry = await setup_blueair(aws=[device])
    client = fake_mqtt.instances[0]
    client.on_disconnect_callback()
    client.on_connect_callback()
    client.on_disconnect_callback()
    await hass.async_block_till_done()
    polls = device.refresh_count

    assert await hass.config_entries.async_unload(entry.entry_id)
    await _advance(hass, timedelta(minutes=10))

    assert device.refresh_count == polls


@pytest.mark.asyncio
async def test_mqtt_messages_update_the_device(
    hass: HomeAssistant, setup_blueair: Any, fake_mqtt: type[FakeMqtt]
) -> None:
    """Apply sensor data, state changes and connectivity events to the right device."""
    device = make_purifier()
    await setup_blueair(aws=[device])
    client = fake_mqtt.instances[0]
    applied: list[tuple[str, Any]] = []
    device.apply_sensor_data = lambda sensors: applied.append(("sensors", sensors))
    device.apply_state_change = lambda state: applied.append(("state", state))

    client.on_sensor_data("purifier-1", {"pm2_5": 9})
    client.on_state_change("purifier-1", {"standby": True})
    client.on_event("purifier-1", {"et": "NotConnected"})
    # Messages for devices this entry does not own are ignored.
    client.on_sensor_data("someone-else", {"pm2_5": 1})
    client.on_state_change("someone-else", {})
    client.on_event("someone-else", {"et": "Connected"})
    await hass.async_block_till_done()

    assert applied == [("sensors", {"pm2_5": 9}), ("state", {"standby": True})]
    assert device.wifi_working is False
    assert hass.states.get("binary_sensor.bedroom_online").state == "off"


@pytest.mark.asyncio
async def test_unexpected_mqtt_start_errors_fail_the_setup(
    hass: HomeAssistant, setup_blueair: Any, fake_mqtt: type[FakeMqtt]
) -> None:
    """Surface a bug while starting MQTT instead of silently polling."""
    fake_mqtt.connect_error = RuntimeError("bug")

    with pytest.raises(AssertionError):
        # setup_blueair asserts that setup succeeded.
        await setup_blueair(aws=[make_purifier()])

    assert hass.config_entries.async_entries(DOMAIN)[0].state is ConfigEntryState.SETUP_ERROR


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [AttributeError, KeyError, TypeError, ValueError])
async def test_mqtt_payloads_that_fail_to_apply_are_skipped(
    hass: HomeAssistant,
    setup_blueair: Any,
    fake_mqtt: type[FakeMqtt],
    caplog: pytest.LogCaptureFixture,
    error: type[Exception],
) -> None:
    """Log and skip a payload the device cannot apply, without breaking MQTT updates."""
    device = make_purifier()
    await setup_blueair(aws=[device])
    client = fake_mqtt.instances[0]

    def reject(_payload: Any) -> None:
        """Fail like a malformed payload would."""
        raise error("bad payload")

    device.apply_sensor_data = reject
    device.apply_state_change = reject

    client.on_sensor_data("purifier-1", {"pm2_5": "?"})
    client.on_state_change("purifier-1", {"standby": "?"})
    await hass.async_block_till_done()

    assert "apply_sensor_data raised" in caplog.text
    assert "apply_state_change raised" in caplog.text


@pytest.mark.asyncio
async def test_unexpected_mqtt_callback_errors_reach_the_mqtt_client(
    hass: HomeAssistant, setup_blueair: Any, fake_mqtt: type[FakeMqtt]
) -> None:
    """Let a bug propagate to blueair_api's MQTT client, which logs it and keeps going."""
    device = make_purifier()
    await setup_blueair(aws=[device])
    client = fake_mqtt.instances[0]

    def broken(_payload: Any) -> None:
        """Fail the way a bug would."""
        raise RuntimeError("bug")

    device.apply_sensor_data = broken
    device.apply_state_change = broken

    with pytest.raises(RuntimeError):
        client.on_sensor_data("purifier-1", {"pm2_5": 1})
    with pytest.raises(RuntimeError):
        client.on_state_change("purifier-1", {"standby": False})


@pytest.mark.asyncio
async def test_mqtt_credential_refresher_returns_new_credentials(
    hass: HomeAssistant,
    setup_blueair: Any,
    fake_mqtt: type[FakeMqtt],
    blueair_cloud: FakeBlueairCloud,
) -> None:
    """Refresh the AWS token and hand MQTT the new credentials on reconnect."""
    await setup_blueair(aws=[make_purifier()])

    credentials = await fake_mqtt.instances[0].credential_refresher()

    assert credentials == ("name", "signature", "token")
    assert blueair_cloud.token_refreshes == 1


@pytest.mark.asyncio
async def test_options_apply_through_the_options_flow_reload(
    hass: HomeAssistant, setup_blueair: Any
) -> None:
    """Apply the polling interval and night preset when the options flow reloads the entry."""
    entry = await setup_blueair(aws=[make_purifier()])
    coordinator = entry.runtime_data.aws_devices[0]
    assert entry.update_listeners == []

    form = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(
        form["flow_id"], {"scan_interval": 12, "night_preset": False}
    )
    await hass.async_block_till_done()

    assert entry.runtime_data.aws_devices[0] is not coordinator
    assert entry.runtime_data.aws_devices[0].update_interval == timedelta(minutes=12)
    assert hass.states.get("fan.bedroom_fan").attributes["preset_modes"] == ["auto"]


@pytest.mark.asyncio
async def test_setup_skips_an_unreachable_device(
    hass: HomeAssistant, setup_blueair: Any, caplog: pytest.LogCaptureFixture
) -> None:
    """Set up the reachable devices when one device can't be polled."""
    offline = make_humidifier()
    offline.refresh_error = ClientConnectionError("device offline")

    entry = await setup_blueair(aws=[make_purifier(), offline])

    assert entry.state is ConfigEntryState.LOADED
    assert [c.id for c in entry.runtime_data.aws_devices] == ["purifier-1"]
    assert [c.id for c in entry.runtime_data.unreachable] == ["humidifier-1"]
    assert hass.states.get("fan.bedroom_fan") is not None
    assert hass.states.get("humidifier.nursery_humidifier") is None
    assert "Blueair device Nursery is unreachable" in caplog.text


@pytest.mark.asyncio
async def test_unreachable_device_reloads_the_entry_once_it_answers(
    hass: HomeAssistant, setup_blueair: Any
) -> None:
    """Keep retrying an unreachable device and reload to add its entities when it answers."""
    offline = make_humidifier()
    offline.refresh_error = ClientConnectionError("device offline")
    entry = await setup_blueair(aws=[make_purifier(), offline])

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=6))
    await hass.async_block_till_done(wait_background_tasks=True)
    assert entry.runtime_data.unreachable != []

    offline.refresh_error = None
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=12))
    await hass.async_block_till_done(wait_background_tasks=True)

    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.unreachable == []
    assert hass.states.get("humidifier.nursery_humidifier") is not None


@pytest.mark.asyncio
async def test_setup_retries_when_no_device_can_be_polled(
    hass: HomeAssistant, blueair_cloud: FakeBlueairCloud
) -> None:
    """Retry the whole setup only when every device is unreachable."""
    device = make_purifier()
    device.refresh_error = ClientConnectionError("offline")
    blueair_cloud.aws_devices = [device]
    entry = _add_entry(hass)

    await hass.config_entries.async_setup(entry.entry_id)

    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert entry.error_reason_translation_key == "update_failed"


@pytest.mark.asyncio
async def test_rejected_login_on_a_first_poll_fails_the_setup(
    hass: HomeAssistant, blueair_cloud: FakeBlueairCloud
) -> None:
    """Start reauthentication when any device's first poll is rejected."""
    rejected = make_humidifier()
    rejected.refresh_error = LoginError("bad password")
    blueair_cloud.aws_devices = [make_purifier(), rejected]
    entry = _add_entry(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert [flow["context"]["source"] for flow in flows] == ["reauth"]


@pytest.mark.asyncio
async def test_unexpected_first_poll_errors_fail_the_setup(
    hass: HomeAssistant, blueair_cloud: FakeBlueairCloud
) -> None:
    """Don't hide an unexpected error as an unreachable device."""
    broken = make_purifier()
    with patch.object(
        BlueairUpdateCoordinator,
        "async_config_entry_first_refresh",
        side_effect=RuntimeError("bug"),
    ):
        blueair_cloud.aws_devices = [broken]
        entry = _add_entry(hass)
        await hass.config_entries.async_setup(entry.entry_id)

    assert entry.state is ConfigEntryState.SETUP_ERROR


@pytest.mark.asyncio
async def test_version_1_entries_migrate_to_the_us_region(
    hass: HomeAssistant, blueair_cloud: FakeBlueairCloud
) -> None:
    """Give version 1 entries, which predate regions, the US region."""
    data = entry_data()
    del data["region"]
    entry = MockConfigEntry(domain=DOMAIN, unique_id=USERNAME, data=data, version=1)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)

    assert entry.version == 2
    assert entry.data["region"] == "us"
    assert entry.state is ConfigEntryState.LOADED


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("unique_id", "expected"), [("User@Example.com", "user@example.com"), (None, None)]
)
async def test_entries_migrate_to_lowercase_unique_ids(
    hass: HomeAssistant,
    blueair_cloud: FakeBlueairCloud,
    unique_id: str | None,
    expected: str | None,
) -> None:
    """Lowercase the unique ID so the same account in another case is a duplicate."""
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=unique_id, data=entry_data(), version=2, minor_version=1
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)

    assert entry.unique_id == expected
    assert (entry.version, entry.minor_version) == (2, 3)


@pytest.mark.asyncio
async def test_lowercase_migration_keeps_a_unique_id_another_entry_uses(
    hass: HomeAssistant, blueair_cloud: FakeBlueairCloud, caplog: pytest.LogCaptureFixture
) -> None:
    """Leave the unique ID alone when another entry already has the lowercase one."""
    MockConfigEntry(
        domain=DOMAIN, unique_id="user@example.com", data=entry_data(), version=2, minor_version=2
    ).add_to_hass(hass)
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="User@Example.com",
        data=entry_data("User@Example.com"),
        version=2,
        minor_version=1,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.unique_id == "User@Example.com"
    assert entry.minor_version == 3
    assert "configured twice" in caplog.text


@pytest.mark.asyncio
async def test_setup_skips_legacy_devices_when_the_legacy_login_is_rejected(
    hass: HomeAssistant, blueair_cloud: FakeBlueairCloud
) -> None:
    """Load AWS devices when only the legacy login is rejected (AWS-only accounts)."""
    blueair_cloud.legacy_error = LoginError("no legacy account")
    entry = _add_entry(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)

    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.devices == []


def _stale(device: Any) -> Any:
    """Give a device the single offline snapshot of a region it doesn't report to.

    Args:
        device: The device to change.

    Returns:
        Any: The same device.
    """
    device.raw_info = {
        "configuration": {"di": {"name": device.name}},
        "states": [{"n": "online", "vb": False, "t": 5}, {"n": "fanspeed", "v": 0, "t": 5}],
    }
    return device


@pytest.mark.asyncio
async def test_setup_uses_the_cloud_region_for_devices_and_mqtt(
    hass: HomeAssistant, blueair_cloud: FakeBlueairCloud, fake_mqtt: type[FakeMqtt]
) -> None:
    """Sign in on the account region and reach the devices on the cloud region."""
    blueair_cloud.aws_devices = [make_purifier()]
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=USERNAME,
        data={**entry_data(), CONF_CLOUD_REGION: "eu"},
        version=2,
        minor_version=3,
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)

    assert blueair_cloud.aws_calls[-1]["gigya_region"] == "us"
    assert blueair_cloud.aws_calls[-1]["cloud_region"] == "eu"
    assert fake_mqtt.instances[0].kwargs["region"] == "eu"


@pytest.mark.asyncio
async def test_entries_migrate_to_a_cloud_region_matching_the_account_region(
    hass: HomeAssistant, blueair_cloud: FakeBlueairCloud
) -> None:
    """Give entries from before 2.3 the account region as their cloud region."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=USERNAME,
        data={**entry_data(), "region": "eu"},
        version=2,
        minor_version=2,
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)

    assert entry.minor_version == 3
    assert entry.data[CONF_CLOUD_REGION] == "eu"
    assert blueair_cloud.aws_calls[-1]["cloud_region"] == "eu"


@pytest.mark.asyncio
async def test_stale_devices_raise_a_cloud_region_issue(
    hass: HomeAssistant, setup_blueair: Any, caplog: pytest.LogCaptureFixture
) -> None:
    """Raise a fixable issue when a device has no recent state, and drop it on unload."""
    entry = await setup_blueair(aws=[make_humidifier(), _stale(make_purifier())])
    issue_id = f"cloud_region_mismatch_{entry.entry_id}"

    issue = ir.async_get(hass).async_get_issue(DOMAIN, issue_id)
    assert issue is not None
    assert issue.is_fixable
    assert issue.data == {"entry_id": entry.entry_id}
    assert issue.translation_placeholders == {"device_name": "Bedroom", "cloud_region": "us"}
    assert "may be hosted on another region" in caplog.text

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None


@pytest.mark.asyncio
async def test_current_devices_clear_the_cloud_region_issue(
    hass: HomeAssistant, blueair_cloud: FakeBlueairCloud
) -> None:
    """Delete a cloud region issue from an earlier setup once the devices report state."""
    blueair_cloud.aws_devices = [make_purifier()]
    entry = _add_entry(hass)
    issue_id = f"cloud_region_mismatch_{entry.entry_id}"
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=True,
        severity=ir.IssueSeverity.WARNING,
        translation_key="cloud_region_mismatch",
    )

    assert await hass.config_entries.async_setup(entry.entry_id)

    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None
