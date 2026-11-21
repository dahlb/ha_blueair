"""Tests for mapping Blueair MQTT connectivity events onto devices."""

from __future__ import annotations

import pytest

from custom_components.ha_blueair.mqtt_mapping import map_and_publish_event

from .conftest import make_purifier


@pytest.mark.parametrize(
    ("event", "start", "expected"),
    [
        ({"et": "Connected"}, False, True),
        ({"et": "NotConnected"}, True, False),
        ({"et": "Other"}, True, True),
        ({}, False, False),
    ],
)
def test_connectivity_events_update_wifi_state(
    event: dict[str, str], start: bool, expected: bool
) -> None:
    """Mark the device online or offline from MQTT connectivity events."""
    device = make_purifier(wifi_working=start)
    published: list[bool] = []
    device.register_callback(lambda: published.append(True))

    map_and_publish_event(event, device)

    assert device.wifi_working is expected
    assert published == [True]
