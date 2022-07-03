[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

A custom integration for Blueair Filters.

Warning; this has only been tested with classic_205 and protect 7470i

## Feature Highlights ##
- adjust fan speed, turn off/on
- adjust light brightness, turn off/on
- sensors
  - filter replacement
  - humidity
  - connectivity
  - temperature
  - PM 1
  - PM 2.5
  - PM 10
  - VOC
- switches
  - child lock

## Installation ##
You can install this either manually copying files or using HACS. Configuration can be done on UI, you need to enter your username and password, (I know, translations are missing).

## Troubleshooting ##
If you receive an error while trying to login, please go through these steps;
1. You can enable logging for this integration specifically and share your logs, so I can have a deep dive investigation. To enable logging, update your `configuration.yaml` like this, we can get more information in Configuration -> Logs page
```
logger:
  default: warning
  logs:
    custom_components.ha_blueair: debug
    blueair_api: debug
```

