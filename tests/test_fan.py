from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ha_blueair.blueair_update_coordinator_device import BlueairUpdateCoordinatorDevice
from custom_components.ha_blueair.blueair_update_coordinator_device_aws import BlueairUpdateCoordinatorDeviceAws
from custom_components.ha_blueair.const import MODE_AUTO
from custom_components.ha_blueair.fan import BlueairFan, BlueairAwsFan


@pytest.fixture
def mock_coordinator_device():
    coordinator = MagicMock(spec=BlueairUpdateCoordinatorDevice)
    coordinator.fan_auto_mode = False
    coordinator.speed_count = 3
    coordinator.set_fan_speed = AsyncMock()
    coordinator.set_fan_auto_mode = AsyncMock()
    coordinator.set_night_mode = AsyncMock()
    # Assume it provides unique_id from device_info or similar internally but
    # BlueairEntity tries to access some properties. Let's mock a few basic ones.
    coordinator.id = "test_device_id"
    coordinator.device_name = "test_device_name"
    coordinator.mac_address = "AA:BB:CC:DD:EE:FF"
    return coordinator

@pytest.fixture
def mock_coordinator_device_aws():
    coordinator = MagicMock(spec=BlueairUpdateCoordinatorDeviceAws)
    coordinator.fan_auto_mode = False
    coordinator.fan_speed = 50
    coordinator.is_on = False
    coordinator.speed_count = 3
    coordinator.set_fan_speed = AsyncMock()
    coordinator.set_fan_auto_mode = AsyncMock()
    coordinator.set_night_mode = AsyncMock()
    coordinator.set_running = AsyncMock()
    coordinator.id = "test_aws_device_id"
    coordinator.device_name = "test_aws_device_name"
    coordinator.mac_address = "11:22:33:44:55:66"
    return coordinator

@pytest.mark.asyncio
async def test_blueair_fan_async_turn_on_default(mock_coordinator_device):
    """Test default async_turn_on for BlueairFan."""
    fan = BlueairFan(mock_coordinator_device)
    fan.async_write_ha_state = MagicMock()

    await fan.async_turn_on()

    mock_coordinator_device.set_fan_speed.assert_awaited_once_with("1")
    fan.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_blueair_fan_async_turn_on_with_percentage(mock_coordinator_device):
    """Test async_turn_on with percentage for BlueairFan."""
    fan = BlueairFan(mock_coordinator_device)
    fan.async_set_percentage = AsyncMock()

    await fan.async_turn_on(percentage=50)

    fan.async_set_percentage.assert_awaited_once_with(percentage=50)
    mock_coordinator_device.set_fan_speed.assert_not_awaited()


@pytest.mark.asyncio
async def test_blueair_fan_async_turn_on_with_preset_mode(mock_coordinator_device):
    """Test async_turn_on with preset_mode for BlueairFan."""
    fan = BlueairFan(mock_coordinator_device)
    fan.async_set_preset_mode = AsyncMock()

    await fan.async_turn_on(preset_mode=MODE_AUTO)

    fan.async_set_preset_mode.assert_awaited_once_with(MODE_AUTO)
    mock_coordinator_device.set_fan_speed.assert_not_awaited()


@pytest.mark.asyncio
async def test_blueair_aws_fan_async_turn_on_default(mock_coordinator_device_aws):
    """Test default async_turn_on for BlueairAwsFan."""
    mock_coordinator_device_aws.is_on = False
    fan = BlueairAwsFan(mock_coordinator_device_aws)
    fan.async_set_percentage = AsyncMock()
    fan.async_write_ha_state = MagicMock()

    await fan.async_turn_on()

    mock_coordinator_device_aws.set_running.assert_awaited_once_with(True)
    # AWS fan defaults to percentage=50 when not provided
    fan.async_set_percentage.assert_awaited_once_with(percentage=50)


@pytest.mark.asyncio
async def test_blueair_aws_fan_async_turn_on_with_percentage(mock_coordinator_device_aws):
    """Test async_turn_on with percentage for BlueairAwsFan."""
    mock_coordinator_device_aws.is_on = True # already on
    fan = BlueairAwsFan(mock_coordinator_device_aws)
    fan.async_set_percentage = AsyncMock()

    await fan.async_turn_on(percentage=75)

    mock_coordinator_device_aws.set_running.assert_not_awaited()
    fan.async_set_percentage.assert_awaited_once_with(percentage=75)


@pytest.mark.asyncio
async def test_blueair_aws_fan_async_turn_on_with_preset_mode(mock_coordinator_device_aws):
    """Test async_turn_on with preset_mode for BlueairAwsFan."""
    mock_coordinator_device_aws.is_on = True # already on
    fan = BlueairAwsFan(mock_coordinator_device_aws)
    fan.async_set_preset_mode = AsyncMock()

    await fan.async_turn_on(preset_mode=MODE_AUTO)

    mock_coordinator_device_aws.set_running.assert_not_awaited()
    fan.async_set_preset_mode.assert_awaited_once_with(preset_mode=MODE_AUTO)
