from enum import Enum

# Configuration Constants
DOMAIN: str = "ha_blueair"

# Integration Setting Constants
CONFIG_FLOW_VERSION: int = 1
PLATFORMS = ["binary_sensor", "fan", "sensor"]

# Home Assistant Data Storage Constants
DATA_DEVICES: str = "api_devices"
DATA_AWS_DEVICES: str = "api_aws_devices"
