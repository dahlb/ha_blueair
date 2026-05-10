def map_and_publish_sensor_data(sensors, device):
    """Handle MQTT sensor data (called from MQTT thread)."""
    if "pm1" in sensors:
        device.pm1 = int(sensors["pm1"])
    if "pm2_5" in sensors:
        device.pm2_5 = int(sensors["pm2_5"])
    if "pm10" in sensors:
        device.pm10 = int(sensors["pm10"])
    if "fsp0" in sensors:
        device.fan_speed_0 = int(sensors["fsp0"])
    if "t" in sensors:
        device.temperature = int(sensors["t"])
    if "h" in sensors:
        device.humidity = int(sensors["h"])
    if "tVOC" in sensors:
        device.total_voc = int(sensors["tVOC"])
    device.publish_updates()

def map_and_publish_event(event, device):
    event_type = event.get("et", "")
    if event_type == "Connected":
        device.wifi_working = True
    elif event_type == "NotConnected":
        device.wifi_working = False
    device.publish_updates()
