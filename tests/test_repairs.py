"""Tests for the Blueair cloud region repair flow."""

from __future__ import annotations

from typing import Any

from aiohttp import ClientConnectionError
from blueair_api import CandidateProbe, CloudRegionScan, LoginError
from homeassistant.components.repairs import repairs_flow_manager
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.ha_blueair.const import CONF_CLOUD_REGION, DOMAIN

from .conftest import USERNAME, FakeBlueairCloud, entry_data


async def _start_fix_flow(
    hass: HomeAssistant, entry_id: str, issue_entry_id: str | None = None
) -> dict[str, Any]:
    """Raise the cloud region issue for an entry and start its fix flow.

    Args:
        hass: Home Assistant instance.
        entry_id: ID of the config entry the issue is for.
        issue_entry_id: Entry ID stored in the issue, when it differs.

    Returns:
        dict[str, Any]: The fix flow's first result.
    """
    assert await async_setup_component(hass, "repairs", {})
    # Home Assistant finds the repairs platform of loaded integrations.
    assert await hass.config_entries.async_setup(entry_id)
    await hass.async_block_till_done()
    issue_id = f"cloud_region_mismatch_{entry_id}"
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=True,
        severity=ir.IssueSeverity.WARNING,
        translation_key="cloud_region_mismatch",
        translation_placeholders={"device_name": "Purifier", "cloud_region": "us"},
        data={"entry_id": issue_entry_id or entry_id},
    )
    manager = repairs_flow_manager(hass)
    assert manager is not None
    # The repairs API starts a fix flow with only the issue ID in the context.
    return dict(await manager.async_init(DOMAIN, context={"issue_id": issue_id}))


def _add_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Add a Blueair entry using the us cloud region.

    Args:
        hass: Home Assistant instance.

    Returns:
        MockConfigEntry: The added entry.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=USERNAME,
        title=USERNAME,
        data={**entry_data(), CONF_CLOUD_REGION: "us"},
        version=2,
        minor_version=3,
    )
    entry.add_to_hass(hass)
    return entry


@pytest.mark.asyncio
async def test_fix_flow_suggests_the_region_hosting_the_devices(
    hass: HomeAssistant, blueair_cloud: FakeBlueairCloud
) -> None:
    """Suggest the scanned region, save the choice, and reload the entry."""
    entry = _add_entry(hass)
    blueair_cloud.scan = CloudRegionScan(
        selected_region="us",
        candidates_tried=["us", "eu"],
        per_region={
            "us": CandidateProbe(region="us", device_count=1, online_count=0),
            "eu": CandidateProbe(region="eu", device_count=1, online_count=1),
        },
        winner="eu",
        multi_region_detected=True,
    )

    form = await _start_fix_flow(hass, entry.entry_id)

    assert form["type"] is FlowResultType.FORM
    assert form["step_id"] == "confirm"
    assert form["errors"] == {}
    assert form["description_placeholders"] == {
        "cloud_region": "us",
        "suggested_cloud_region": "eu",
    }
    # The scan signs in on the account region, starting from the current cloud region.
    assert blueair_cloud.http_clients[-1]["gigya_region"] == "us"
    assert blueair_cloud.http_clients[-1]["cloud_region"] == "us"

    manager = repairs_flow_manager(hass)
    assert manager is not None
    result = await manager.async_configure(form["flow_id"], {CONF_CLOUD_REGION: "eu"})
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.data[CONF_CLOUD_REGION] == "eu"
    assert blueair_cloud.aws_calls[-1]["cloud_region"] == "eu"
    assert entry.state is ConfigEntryState.LOADED
    issue_id = f"cloud_region_mismatch_{entry.entry_id}"
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None
    # The scan runs once per flow.
    assert len(blueair_cloud.scan_calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (LoginError("bad password"), "auth"),
        (ClientConnectionError("offline"), "cannot_connect"),
        (TimeoutError(), "cannot_connect"),
    ],
)
async def test_fix_flow_suggests_the_current_region_when_the_scan_fails(
    hass: HomeAssistant, blueair_cloud: FakeBlueairCloud, error: BaseException, expected: str
) -> None:
    """Explain the failed scan and still let the user choose a region."""
    entry = _add_entry(hass)
    blueair_cloud.scan_error = error

    form = await _start_fix_flow(hass, entry.entry_id)

    assert form["type"] is FlowResultType.FORM
    assert form["errors"] == {"base": expected}
    assert form["description_placeholders"]["suggested_cloud_region"] == "us"


@pytest.mark.asyncio
async def test_fix_flow_keeps_the_current_region_when_no_devices_are_found(
    hass: HomeAssistant, blueair_cloud: FakeBlueairCloud
) -> None:
    """Suggest the current region when no region reports devices."""
    entry = _add_entry(hass)

    form = await _start_fix_flow(hass, entry.entry_id)

    assert form["description_placeholders"]["suggested_cloud_region"] == "us"


@pytest.mark.asyncio
async def test_fix_flow_aborts_for_a_removed_entry(
    hass: HomeAssistant, blueair_cloud: FakeBlueairCloud
) -> None:
    """Abort when the issue's config entry no longer exists."""
    entry = _add_entry(hass)

    result = await _start_fix_flow(hass, entry.entry_id, issue_entry_id="gone")

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "entry_not_found"
