# Configuration Constants
DOMAIN: str = "ha_blueair"

# Integration Setting Constants
CONFIG_FLOW_VERSION: int = 2
PLATFORMS = ["binary_sensor", "fan", "humidifier", "light", "sensor", "switch"]

# Home Assistant Data Storage Constants
DATA_DEVICES: str = "api_devices"
DATA_AWS_DEVICES: str = "api_aws_devices"

REGION_EU = "eu"
REGION_USA = "us"
REGIONS = [REGION_USA, REGION_EU]

DEFAULT_FAN_SPEED_PERCENTAGE = 50
FILTER_EXPIRED_THRESHOLD = 95

# Custom Mode Constants
MODE_FAN_SPEED = "fan_speed"
