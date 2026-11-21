"""Tests for Blueair config entry setup and unload."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from aiohttp import ClientConnectionError
from blueair_api import LoginError
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.ha_blueair import BlueairRuntimeData
from custom_components.ha_blueair.const import DOMAIN

from .conftest import (
    USERNAME,
    FakeBlueairCloud,
    FakeMqtt,
    entry_data,
    make_humidifier,
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
    """Stop paho's thread at shutdown, since entries are not unloaded then."""
    await setup_blueair(aws=[make_purifier()])

    hass.bus.async_fire(EVENT_HOMEASSISTANT_STOP)
    await hass.async_block_till_done()

    assert fake_mqtt.instances[0].disconnects == 1


@pytest.mark.asyncio
async def test_mqtt_connect_failure_falls_back_to_polling(
    hass: HomeAssistant, setup_blueair: Any, fake_mqtt: type[FakeMqtt]
) -> None:
    """Keep the entry working by polling when MQTT cannot connect."""
    fake_mqtt.connect_error = OSError("TLS handshake failed")

    entry = await setup_blueair(aws=[make_purifier()])

    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.mqtt_client is None
    assert fake_mqtt.instances[0].disconnects == 1


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
async def test_mqtt_payloads_that_fail_to_apply_are_skipped(
    hass: HomeAssistant,
    setup_blueair: Any,
    fake_mqtt: type[FakeMqtt],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Log and skip a payload the device cannot apply, without killing the MQTT thread."""
    device = make_purifier()
    await setup_blueair(aws=[device])
    client = fake_mqtt.instances[0]

    def reject(_payload: Any) -> None:
        """Fail like a malformed payload would."""
        raise ValueError("bad payload")

    device.apply_sensor_data = reject
    device.apply_state_change = reject

    client.on_sensor_data("purifier-1", {"pm2_5": "?"})
    client.on_state_change("purifier-1", {"standby": "?"})
    await hass.async_block_till_done()

    assert "apply_sensor_data raised" in caplog.text
    assert "apply_state_change raised" in caplog.text


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
async def test_options_change_the_scan_interval_or_reload_for_night_preset(
    hass: HomeAssistant, setup_blueair: Any
) -> None:
    """Apply a new polling interval in place, and reload when the night preset changes."""
    entry = await setup_blueair(aws=[make_purifier()])
    coordinator = entry.runtime_data.aws_devices[0]

    hass.config_entries.async_update_entry(entry, options={"scan_interval": 12})
    await hass.async_block_till_done()
    assert coordinator.update_interval == timedelta(minutes=12)

    hass.config_entries.async_update_entry(
        entry, options={"scan_interval": 12, "night_preset": False}
    )
    await hass.async_block_till_done()
    assert entry.runtime_data.aws_devices[0] is not coordinator
    assert hass.states.get("fan.bedroom_fan").attributes["preset_modes"] == ["auto"]


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
async def test_setup_skips_legacy_devices_when_the_legacy_login_is_rejected(
    hass: HomeAssistant, blueair_cloud: FakeBlueairCloud
) -> None:
    """Load AWS devices when only the legacy login is rejected (AWS-only accounts)."""
    blueair_cloud.legacy_error = LoginError("no legacy account")
    entry = _add_entry(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)

    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.devices == []
