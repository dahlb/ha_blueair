<img src="https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=integration%20usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.ha_blueair.total">

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]

![Project Maintenance][maintenance-shield]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

A custom integration for Blueair Filters.  If your model isn't reported correctly please open a ticket and include your model name and the diagnostic file from the integration.

## Feature Highlights ##
- fan
  - speed
  - turn off/on
  - preset modes: night/auto (if supported)
- light
  - brightness
  - turn off/on
- sensors
  - Filter Replacement
  - Humidity
  - Connectivity
  - Temperature
  - PM 1
  - PM 2.5
  - PM 10
  - VOC
- switches
  - child lock
  - germ shield
  - wick dry
- climate (T10i/T20i only)
- humidifier (H35i/H76i only)

## Installation ##
You can install this either manually copying files or using HACS. Configuration can be done on UI, you need to enter your username and password, (I know, translations are missing).

## Beta / Pre-release Builds ##

Some changes are easier to validate with a small group of opt-in testers before
they ship to everyone. Those changes are published as **pre-release** builds that
only appear for users who have turned on beta versions in HACS. Normal users are
never offered a pre-release and stay on the latest stable build.

### Installing a beta as a tester (HACS) ###

1. In Home Assistant, open **HACS** and find **Blueair Filters** under
   Integrations.
2. Open the three-dot menu on the integration and choose **Redownload**
   (some HACS versions label this **Update information** / **Reinstall**).
3. Enable the **Show beta versions** toggle in that dialog.
4. Pick the beta version (for example `1.51.0-beta.1`) from the version list and
   download it.
5. Restart Home Assistant.

To return to a stable build, repeat the steps with **Show beta versions** turned
off, select the latest non-beta version, and restart.

> When reporting on a beta, include the exact version string and a diagnostics
> download (see [Troubleshooting](#troubleshooting-)) so issues are easy to trace.

### Publishing a beta (maintainers) ###

Stable releases are unchanged: a push to `main` runs the **Release** workflow,
which derives the next version from the conventional-commit history and publishes
a normal (non-pre-release) GitHub Release.

Pre-releases are cut manually from a feature branch so they never reach stable
users:

1. Push the change to a feature branch (do **not** merge to `main` yet).
2. Go to **Actions -> Release -> Run workflow**.
3. Select that feature branch as the workflow ref.
4. In **Pre-release version**, enter a version with a suffix, e.g.
   `1.51.0-beta.1` (the suffix may be `-alpha`, `-beta`, or `-rc`).
5. Run it. The workflow bumps `manifest.json` on that branch, tags
   `v1.51.0-beta.1`, and creates a GitHub Release that is **automatically marked
   as a pre-release** because of the suffix. HACS then offers it only to users
   with **Show beta versions** enabled.

When validation is complete, merge the branch to `main`; the normal push-to-main
flow then publishes the stable version the usual way.
## Limitations ##
If you receive an error while trying to login, try resetting your password to one with no special characters except '!' and no longer then 10 characters.

## Troubleshooting ##
If you receive an error, please go through these steps;
1. Enabled Debug Logging, at /config/integrations/integration/ha_blueair
2. Restart you home assistant to capture initialization with debug logging, then try to do what your having trouble with
3. Disable Debug Logging, at /config/integrations/integration/ha_blueair (which will download the logs)
4. Click the three dots menu for your device, at /config/integrations/integration/ha_blueair
5. Click Download Diagnostics
6. Attach both logs and diagnostics to your issue ticket.

***

[ha_blueair]: https://github.com/dahlb/ha_blueair
[commits-shield]: https://img.shields.io/github/commit-activity/y/dahlb/ha_blueair.svg?style=for-the-badge
[commits]: https://github.com/dahlb/ha_blueair/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/dahlb/ha_blueair.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Bren%20Dahl%20%40dahlb-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/dahlb/ha_blueair.svg?style=for-the-badge
[releases]: https://github.com/dahlb/ha_blueair/releases
[buymecoffee]: https://www.buymeacoffee.com/dahlb
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge


