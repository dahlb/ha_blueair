# Configuration Constants
from enum import Enum
from homeassistant.const import Platform

DOMAIN: str = "ha_blueair"

# Integration Setting Constants
CONFIG_FLOW_VERSION: int = 3
CONF_CLOUD_REGION: str = "cloud_region"
REPAIR_CLOUD_REGION_MISMATCH: str = "cloud_region_mismatch"
DEFAULT_SCAN_INTERVAL: int = 5
PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.FAN,
    Platform.HUMIDIFIER,
    Platform.LIGHT,
    Platform.SENSOR,
    Platform.SWITCH,
]

class FanMode(Enum):
    AUTO = "auto"
    STEP1 = "step1"
    STEP2 = "step2"
    STEP3 = "step3"
    STEP4 = "step4"


# Home Assistant Data Storage Constants
DATA_DEVICES: str = "api_devices"
DATA_AWS_DEVICES: str = "api_aws_devices"
DATA_MQTT_CLIENT: str = "mqtt_client"

REGION_EU = "eu"
REGION_USA = "us"
REGION_AU = "au"
REGION_CN = "cn"
REGIONS = [REGION_USA, REGION_EU, REGION_AU, REGION_CN]

DEFAULT_FAN_SPEED_PERCENTAGE = 50

# Custom Mode Constants
MODE_FAN_SPEED = "fan_speed"
MODE_AUTO = "auto"
MODE_NIGHT = "night"

# Additional preset modes used by Blueair Signature-series air
# purifiers (SP1i / SP3i / SP4i, type_name='blue40', hw='l_blue40'),
# which expose all four preset modes through the `apsubmode` shadow
# field rather than `automode` / `nightmode`. See issues
# dahlb/ha_blueair#348 and #261.
#
# The integer wire values for these labels live in
# `blueair_api.AP_SUB_MODE_LABELS` so the library can stay the
# single source of truth for the apsubmode namespace (see also
# Phase 3 tracking in dahlb/ha_blueair#353).
MODE_MANUAL_FAN = "manual_fan"
MODE_ECO = "eco"
