<img src="https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=integration%20usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.ha_blueair.total">

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]
[![Quality Scale][quality-scale-shield]][quality-scale]

![Project Maintenance][maintenance-shield]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

A custom integration for Blueair air purifiers, humidifiers and fans.  If your model isn't reported correctly please open a ticket and include your model name and the diagnostic file from the integration.

## Feature Highlights ##
- fan
  - speed
  - turn off/on
  - preset modes: night/auto (if supported; night can be left out in the integration's options, e.g. to drop the Night switch HomeKit Bridge adds)
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

## Supported Devices ##
Wi-Fi ("i") Blueair devices on a Blueair app account are supported. Devices are listed from the account, so there is nothing to pair; what each device offers depends on what its model reports.

- **Current (AWS) models**, which update in real time:
  - **Purifiers**: Blue Pure 211i/311i/311i+/411i/511i Max (including 3250i, 3350i, 3450i, 3650i), Blue Signature SP1i/SP3i/SP4i, Classic Pro CP7i/CP9i, DustMagnet 5210i–5475i, PetAir Pro P3i, Protect 7310i–7775i and Protect+ 8440i–8880i.
  - **Humidifiers**: H35i, DreamWell H38i and H76i, and the 2-in-1 Purify + Humidify models (purifier fan plus a humidifier switch).
  - **Heater/cooler fans**: ComfortPure 3-in-1 T10i and T20i (climate entity).
  - **Other**: Dehumidifier+ Purifier D26i, Mini Restful, Pedestal Fan 1.0 and SleepAir Fan Circulator.
- **Legacy models**, which are polled: Classic 280i, 290i, 480i and 680i, and Sense+.

If a model shows the wrong entities, or Blueair releases a new one, open an issue with the model name and the diagnostics file.

## Use Cases ##
- **Clean air on a schedule** — run purifiers on Auto while you're home and turn them off when everyone leaves.
- **React to air quality** — raise the fan speed when PM 2.5 or VOC climbs, for example while cooking.
- **Quiet nights** — switch bedroom purifiers to Night (or humidifiers to Sleep) at bedtime and dim their lights.
- **Maintenance reminders** — get a notification when the Filter Expiration sensor turns on or Filter Life drops low, or when a humidifier reports Water Shortage.
- **Comfort** — hold a room's temperature with a T10i/T20i, or its humidity with a humidifier.

## Installation ##
You can install this either manually copying files or using HACS. Then add the integration from **Settings → Devices & Services → Add Integration → Blueair** and enter:

- **Region** — the Blueair region your account signs in on (`us`, `eu`, `au` or `cn`; the region you picked in the Blueair app). The region hosting your devices is found automatically; see [Account region and device cloud region](#account-region-and-device-cloud-region).
- **Username** — the email address you use to sign in to the Blueair app.
- **Password** — the password for that Blueair account.

If Blueair later rejects the saved password (for example after you change it in the app), Home Assistant shows a **Re-authenticate** prompt for the integration; enter the new password there instead of removing and re-adding it.

To change the region or password yourself, choose **Reconfigure** from the integration's three-dot menu. To use a different Blueair account, add the integration again.

### Account region and device cloud region ###
Most Blueair accounts sign in and keep their devices on the same region, but some (for example accounts with a CP7i) sign in on one region while their devices are hosted on another. After you sign in, the integration checks every Blueair cloud region for your devices:

- If one region clearly hosts your devices (the only one with online devices, or the only one with devices at all), it is saved without asking. An account without devices keeps its account region.
- If devices answer on more than one region, setup asks you to pick the **Device cloud region**, suggesting the one with the most online devices.

The device cloud region is only looked up when you add the account or fix a repair; normal startups reuse the saved value. If a device has no recent state on the saved region (a sign that it is hosted elsewhere), Home Assistant raises a **Blueair devices may be on another cloud region** repair. Its **Fix** button looks up the region again, lets you confirm it, and reloads the integration. You can also change the device cloud region from **Reconfigure**.

Devices you add to the Blueair account later appear in Home Assistant automatically, and devices you remove from the account are removed from Home Assistant, within 30 minutes. A device that is no longer on the account can also be deleted from its device page.

## Options ##
Click **Configure** on the integration to change:

- **Polling Interval in Minutes** (default 5, range 1-30) — how often every device is polled. Devices with real-time MQTT updates (most current models) poll less often while MQTT is connected; see [How Data Updates](#how-data-updates).
- **Offer the Night preset on fans** (default on) — turn off to leave Night out of fans' preset list, e.g. so HomeKit Bridge doesn't add a Night switch.
- **Filter Expiration threshold (%)** (default 0, range 0-50) — current (AWS) models turn **Filter Expiration** on when **Filter Life** is at or below this percentage; set e.g. 10 to be warned before the filter runs out. Legacy models report filter expiry themselves.

Saving the options reloads the integration.

## How Data Updates ##
- **Current (AWS) models** push changes over MQTT, so states and sensors update within seconds. While MQTT is connected they are polled only every 30 minutes (or at the polling interval, if that is longer) in case a message is missed; if MQTT disconnects they poll right away and go back to the polling interval until it reconnects.
- **Legacy models** are polled at the polling interval only.
- Commands go to Blueair's cloud; the entity shows the new state straight away and the next update confirms it.
- The account's device list is checked every 30 minutes for added or removed devices.
- If Blueair can't be reached, the entities become unavailable and the outage is logged once; they recover on the next successful update.
- If one device can't be reached when Home Assistant starts, the other devices still load. The unreachable device is retried at the polling interval, and the integration reloads to add its entities once it answers. Setup is only retried as a whole when no device can be reached.

## Automation Examples ##
Raise the fan speed when PM 2.5 is high, and go back to Auto once the air is clean:

```yaml
automation:
  - alias: "Purifier boost on high PM 2.5"
    triggers:
      - trigger: numeric_state
        entity_id: sensor.bedroom_pm_2_5
        above: 35
        for: "00:05:00"
    actions:
      - action: fan.set_percentage
        target:
          entity_id: fan.bedroom_fan
        data:
          percentage: 100
  - alias: "Purifier back to auto"
    triggers:
      - trigger: numeric_state
        entity_id: sensor.bedroom_pm_2_5
        below: 12
        for: "00:10:00"
    actions:
      - action: fan.set_preset_mode
        target:
          entity_id: fan.bedroom_fan
        data:
          preset_mode: auto
```

Switch to Night mode and turn off the light at bedtime:

```yaml
automation:
  - alias: "Purifier night mode"
    triggers:
      - trigger: time
        at: "22:30:00"
    actions:
      - action: fan.set_preset_mode
        target:
          entity_id: fan.bedroom_fan
        data:
          preset_mode: night
      - action: light.turn_off
        target:
          entity_id: light.bedroom_led_light
```

Get a reminder when the filter needs replacing. Legacy models report this directly; current (AWS) models turn **Filter Expiration** on when **Filter Life** reaches 0%, or the **Filter Expiration threshold** set in the [options](#options):

```yaml
automation:
  - alias: "Blueair filter reminder"
    triggers:
      - trigger: state
        entity_id: binary_sensor.bedroom_filter_expiration
        to: "on"
    actions:
      - action: notify.notify
        data:
          message: "The bedroom Blueair filter needs replacing."
```

Entity IDs follow your device names; check yours under **Settings → Devices & Services → Blueair**.

## Filter, Wick and Water sensors no longer report as batteries ##

The **Filter Life**, **Wick Life**, **Water Refresher Life** and **Water Level**
sensors used to be created with Home Assistant's `battery` device class. Because
they report a percentage, that classification pulled them into battery
dashboards, battery groups, low-battery notification automations/blueprints, and
HomeKit / voice-assistant battery reporting — even though none of them is a
battery.

These are filter/wick/refresher remaining-life and water-level percentages, so
the `battery` device class has been removed. There is no Home Assistant device
class that fits "filter life" or "water level", so they now have no device class.
The state values, `%` unit, `measurement` state class, icons and long-term
history are unchanged — only the battery classification is gone.

If you deliberately relied on the battery classification (for example a battery
dashboard that lists these sensors), you can re-create it with a
[template sensor](https://www.home-assistant.io/integrations/template/). Home
Assistant does not let you override a natively-set device class from the UI, so a
template sensor is the supported way to keep a battery-classified copy:

```yaml
# configuration.yaml
template:
  - sensor:
      - name: "Bedroom Blueair Filter Battery"
        unique_id: bedroom_blueair_filter_battery
        device_class: battery
        unit_of_measurement: "%"
        state_class: measurement
        # Replace with your own entity id from Developer Tools > States
        state: "{{ states('sensor.bedroom_blueair_filter_life') }}"
        availability: "{{ has_value('sensor.bedroom_blueair_filter_life') }}"
```

After a restart the new `sensor.bedroom_blueair_filter_battery` behaves like a
battery again, while the original sensor stays correctly unclassified.

## Beta / Pre-release Builds ##

Some changes are easier to validate with a small group of opt-in testers before
they ship to everyone. Those changes are published as **pre-release** builds that
only appear for users who have turned on beta versions in HACS. Normal users are
never offered a pre-release and stay on the latest stable build.

### Installing a beta as a tester (HACS) ###

1. In Home Assistant, open **HACS** and find **Blueair** under
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
## Removal ##
This integration follows the standard Home Assistant removal process; no extra steps are needed.

1. Go to **Settings → Devices & Services → Blueair**.
2. Click the three-dot menu next to your Blueair account and choose **Delete**. This removes its devices and entities and stops all requests to Blueair's cloud.
3. *(Optional)* If you installed through HACS and will not use the integration again, open **HACS**, find **Blueair**, choose **Remove**, then restart Home Assistant. For a manual install, delete `config/custom_components/ha_blueair` and restart.

Removing the integration does not change any settings on your Blueair devices or in your Blueair account.

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
[quality-scale]: custom_components/ha_blueair/quality_scale.yaml
[quality-scale-shield]: https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fdahlb%2Fha_blueair%2Fmain%2Fcustom_components%2Fha_blueair%2Fmanifest.json&query=%24.quality_scale&label=Quality%20Scale&style=for-the-badge&logo=home-assistant&color=41BDF5
[buymecoffee]: https://www.buymeacoffee.com/dahlb
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge


