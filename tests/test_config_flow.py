"""Tests for the Blueair config flow."""

from __future__ import annotations

import json
from pathlib import Path

from aiohttp import ClientConnectionError
from blueair_api import LoginError, ServerError
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_PASSWORD, CONF_REGION, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.ha_blueair.const import DOMAIN

from .conftest import USERNAME, FakeBlueairCloud, entry_data

INTEGRATION_DIR = Path(__file__).parents[1] / "custom_components" / DOMAIN


@pytest.mark.asyncio
async def test_user_flow_creates_an_entry(
    hass: HomeAssistant, blueair_cloud: FakeBlueairCloud
) -> None:
    """Create an entry keyed by the username after a successful login."""
    form = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert form["type"] is FlowResultType.FORM
    assert form["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(form["flow_id"], entry_data())

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == USERNAME
    assert result["data"] == entry_data()
    assert result["result"].unique_id == USERNAME
    assert blueair_cloud.aws_calls[-1]["region"] == entry_data()[CONF_REGION]
    # The flow's login opens its own session, so it closes it again.
    assert blueair_cloud.cleanup_calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (LoginError("bad password"), "auth"),
        (ClientConnectionError("offline"), "cannot_connect"),
        (TimeoutError(), "cannot_connect"),
        (ServerError("server error 503"), "cannot_connect"),
        (KeyError("uuid"), "unknown"),
    ],
)
async def test_user_flow_maps_login_errors(
    hass: HomeAssistant,
    blueair_cloud: FakeBlueairCloud,
    error: BaseException,
    expected: str,
) -> None:
    """Show a form error, rather than crashing, for each kind of login failure."""
    blueair_cloud.aws_error = error
    form = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(form["flow_id"], entry_data())

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected}

    blueair_cloud.aws_error = None
    retry = await hass.config_entries.flow.async_configure(form["flow_id"], entry_data())
    assert retry["type"] is FlowResultType.CREATE_ENTRY


@pytest.mark.asyncio
async def test_user_flow_aborts_for_an_account_already_configured(
    hass: HomeAssistant, blueair_cloud: FakeBlueairCloud
) -> None:
    """Refuse to add the same Blueair account twice."""
    MockConfigEntry(domain=DOMAIN, unique_id=USERNAME, data=entry_data(), version=2).add_to_hass(
        hass
    )
    form = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(form["flow_id"], entry_data())

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.asyncio
async def test_options_flow_updates_the_options(
    hass: HomeAssistant, blueair_cloud: FakeBlueairCloud
) -> None:
    """Save the polling interval and night preset options."""
    entry = MockConfigEntry(domain=DOMAIN, unique_id=USERNAME, data=entry_data(), version=2)
    entry.add_to_hass(hass)

    form = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        form["flow_id"], {"scan_interval": 10, "night_preset": False}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {"scan_interval": 10, "night_preset": False}


@pytest.mark.parametrize("file_name", ["strings.json", "translations/en.json"])
@pytest.mark.parametrize(
    ("section", "step"), [("config", "user"), ("config", "reconfigure"), ("options", "init")]
)
def test_every_flow_field_has_a_data_description(file_name: str, section: str, step: str) -> None:
    """Describe every config and options flow field, as the config-flow rule requires."""
    strings = json.loads((INTEGRATION_DIR / file_name).read_text(encoding="utf-8"))
    step_strings = strings[section]["step"][step]

    assert set(step_strings["data"]) == set(step_strings["data_description"])
    assert (
        CONF_USERNAME not in step_strings["data"] or step_strings["data_description"][CONF_USERNAME]
    )


def _reauth_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Add a Blueair entry whose stored password is out of date.

    Args:
        hass: Home Assistant instance.

    Returns:
        MockConfigEntry: The added entry.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=USERNAME,
        title=USERNAME,
        data={**entry_data(), CONF_PASSWORD: "old-password"},
        version=2,
    )
    entry.add_to_hass(hass)
    return entry


@pytest.mark.asyncio
async def test_reauth_flow_updates_the_password(
    hass: HomeAssistant, blueair_cloud: FakeBlueairCloud
) -> None:
    """Store the new password after Blueair accepts it, and reload the entry."""
    entry = _reauth_entry(hass)

    form = await entry.start_reauth_flow(hass)
    assert form["type"] is FlowResultType.FORM
    assert form["step_id"] == "reauth_confirm"
    assert form["description_placeholders"]["username"] == USERNAME

    result = await hass.config_entries.flow.async_configure(
        form["flow_id"], {CONF_PASSWORD: "new-password"}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_PASSWORD] == "new-password"
    assert entry.data[CONF_USERNAME] == USERNAME
    # The flow checks the new password itself before the entry reloads with it.
    assert {
        "username": USERNAME,
        "password": "new-password",
        "region": entry_data()[CONF_REGION],
    } in blueair_cloud.aws_calls
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected"),
    [(LoginError("still wrong"), "auth"), (ClientConnectionError("offline"), "cannot_connect")],
)
async def test_reauth_flow_keeps_the_form_open_on_errors(
    hass: HomeAssistant,
    blueair_cloud: FakeBlueairCloud,
    error: BaseException,
    expected: str,
) -> None:
    """Keep the old password and show an error when the new one cannot be checked."""
    entry = _reauth_entry(hass)
    blueair_cloud.aws_error = error
    form = await entry.start_reauth_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        form["flow_id"], {CONF_PASSWORD: "new-password"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected}
    assert entry.data[CONF_PASSWORD] == "old-password"


@pytest.mark.asyncio
async def test_reconfigure_flow_updates_the_region_and_password(
    hass: HomeAssistant, blueair_cloud: FakeBlueairCloud
) -> None:
    """Store the new region and password after Blueair accepts them."""
    entry = _reauth_entry(hass)

    form = await entry.start_reconfigure_flow(hass)
    assert form["type"] is FlowResultType.FORM
    assert form["step_id"] == "reconfigure"
    assert form["description_placeholders"]["username"] == USERNAME

    result = await hass.config_entries.flow.async_configure(
        form["flow_id"], {CONF_REGION: "eu", CONF_PASSWORD: "new-password"}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data == {
        CONF_USERNAME: USERNAME,
        CONF_PASSWORD: "new-password",
        CONF_REGION: "eu",
    }
    assert {"username": USERNAME, "password": "new-password", "region": "eu"} in (
        blueair_cloud.aws_calls
    )
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED


@pytest.mark.asyncio
async def test_reconfigure_flow_keeps_the_form_open_on_errors(
    hass: HomeAssistant, blueair_cloud: FakeBlueairCloud
) -> None:
    """Keep the stored settings and show an error when Blueair rejects the login."""
    entry = _reauth_entry(hass)
    blueair_cloud.aws_error = LoginError("wrong region")
    form = await entry.start_reconfigure_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        form["flow_id"], {CONF_REGION: "eu", CONF_PASSWORD: "new-password"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "auth"}
    assert entry.data[CONF_PASSWORD] == "old-password"
    assert entry.data[CONF_REGION] == entry_data()[CONF_REGION]


@pytest.mark.parametrize("file_name", ["strings.json", "translations/en.json"])
def test_reauth_and_exception_strings_exist(file_name: str) -> None:
    """Translate the reauth form and every raised exception."""
    strings = json.loads((INTEGRATION_DIR / file_name).read_text(encoding="utf-8"))
    reauth = strings["config"]["step"]["reauth_confirm"]

    assert set(reauth["data"]) == set(reauth["data_description"]) == {CONF_PASSWORD}
    assert "reauth_successful" in strings["config"]["abort"]
    assert set(strings["exceptions"]) == {
        "auth_failed",
        "update_failed",
        "command_failed",
        "cannot_connect",
        "invalid_mode",
    }
