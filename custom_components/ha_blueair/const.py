# Configuration Constants
from enum import Enum
from homeassistant.const import Platform

DOMAIN: str = "ha_blueair"

# Integration Setting Constants
CONFIG_FLOW_VERSION: int = 2
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
