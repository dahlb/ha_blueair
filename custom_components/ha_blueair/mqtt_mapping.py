"""MQTT event mapping helpers.

Sensor and shadow state updates are mapped by ``blueair_api`` itself
(``DeviceAws.apply_sensor_data`` / ``DeviceAws.apply_state_change``).
This module only handles MQTT connectivity events — the small set of
``Connected``/``NotConnected`` payloads the library doesn't translate.
"""

from typing import Any

from blueair_api import DeviceAws


def map_and_publish_event(event: dict[str, Any], device: DeviceAws) -> None:
    """Apply an MQTT connectivity event to the device and publish the update."""
    event_type = event.get("et", "")
    if event_type == "Connected":
        device.wifi_working = True
    elif event_type == "NotConnected":
        device.wifi_working = False
    device.publish_updates()
