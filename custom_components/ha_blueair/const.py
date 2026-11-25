"""Constants for the Blueair integration."""

# Configuration Constants
from enum import Enum

from homeassistant.const import Platform

DOMAIN: str = "ha_blueair"
VERSION: str = "1.66.3"

# Integration Setting Constants
CONFIG_FLOW_VERSION: int = 2
# Minor version 2 lowercases the unique ID (the account username); minor
# version 3 stores the device cloud region (CONF_CLOUD_REGION).
CONFIG_FLOW_MINOR_VERSION: int = 3
# BlueCloud region that hosts the account's devices (REST API and MQTT).
# Usually the same as the account (login) region in CONF_REGION, but some
# accounts sign in on one region while their devices live on another.
CONF_CLOUD_REGION: str = "cloud_region"
# Repair issue raised when devices look like they are on another cloud region.
ISSUE_CLOUD_REGION_MISMATCH: str = "cloud_region_mismatch"
DEFAULT_SCAN_INTERVAL: int = 5
# Polling interval, in minutes, for AWS devices while MQTT pushes their
# updates; polling is then only a fallback for missed messages. A longer
# configured interval is kept.
MQTT_SCAN_INTERVAL: int = 30
# How long a device waits before polling again after BlueCloud reported a
# rate limit (HTTP 429 or 229 "too many calls"), in minutes.
RATE_LIMIT_RETRY_MINUTES: int = 15
# How often to check the account for added or removed devices, in minutes.
DEVICE_LIST_INTERVAL: int = 30
# Whether fans offer the Night preset. Off leaves Night out of their
# preset list, e.g. so HomeKit Bridge doesn't show a Night switch.
CONF_NIGHT_PRESET: str = "night_preset"
DEFAULT_NIGHT_PRESET: bool = True
# Filter Life percentage at or below which current (AWS) models report
# Filter Expiration. Legacy models report filter expiry themselves.
CONF_FILTER_EXPIRED_THRESHOLD: str = "filter_expired_threshold"
DEFAULT_FILTER_EXPIRED_THRESHOLD: int = 0
MAX_FILTER_EXPIRED_THRESHOLD: int = 50
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
    """Fan modes reported by Blueair devices."""

    AUTO = "auto"
    STEP1 = "step1"
    STEP2 = "step2"
    STEP3 = "step3"
    STEP4 = "step4"


# Home Assistant Data Storage Constants

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
