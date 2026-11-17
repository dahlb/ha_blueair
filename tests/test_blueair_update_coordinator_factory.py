"""Tests for the Blueair update coordinator factory."""

from unittest.mock import MagicMock, patch

from blueair_api import Device, DeviceAws
import pytest

from custom_components.ha_blueair import blueair_update_coordinator_factory as factory
from custom_components.ha_blueair.const import DEFAULT_SCAN_INTERVAL


@pytest.mark.parametrize(
    ("device_class", "expected", "other"),
    [
        (Device, "BlueairUpdateCoordinatorDevice", "BlueairUpdateCoordinatorDeviceAws"),
        (DeviceAws, "BlueairUpdateCoordinatorDeviceAws", "BlueairUpdateCoordinatorDevice"),
    ],
)
@pytest.mark.parametrize("interval", [None, 7])
async def test_create_blueair_coordinator_picks_coordinator_by_device_type(
    device_class: type, expected: str, other: str, interval: int | None
) -> None:
    """Legacy devices get the legacy coordinator and AWS devices the AWS one."""
    hass = MagicMock()
    device = MagicMock(spec=device_class)
    kwargs = {} if interval is None else {"interval": interval}

    with (
        patch.object(factory, expected) as expected_cls,
        patch.object(factory, other) as other_cls,
    ):
        result = await factory.create_blueair_coordinator(hass, device, **kwargs)

    expected_cls.assert_called_once_with(
        hass=hass,
        blueair_api_device=device,
        interval=DEFAULT_SCAN_INTERVAL if interval is None else interval,
    )
    other_cls.assert_not_called()
    assert result is expected_cls.return_value
