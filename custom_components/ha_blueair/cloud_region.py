"""Pick the BlueCloud region that hosts a Blueair account's devices.

Most accounts sign in (Gigya) and keep their devices on the same region, but
some, such as accounts with a CP7i, sign in on one region while their devices
live on another. blueair_api probes every region; these helpers turn its scan
into the region the config and repair flows suggest.
"""

import logging

from blueair_api import CloudRegionScan, HttpAwsBlueair

_LOGGER = logging.getLogger(__name__)


async def async_scan_cloud_regions(api: HttpAwsBlueair) -> CloudRegionScan:
    """Probe every BlueCloud region for the account's devices.

    The probe is read-only: it does not change the client's cloud region.

    Args:
        api: Blueair AWS client for the account.

    Returns:
        CloudRegionScan: The devices and online devices found on each region.

    Raises:
        AuthError: Blueair rejected the account's credentials.
        ClientError: Blueair could not be reached.
        TimeoutError: Blueair did not answer in time.
    """
    scan = await api.discover_cloud_region()
    _LOGGER.debug(
        "BlueCloud region scan: configured=%s winner=%s multi_region=%s per_region=%s",
        scan.selected_region,
        scan.winner,
        scan.multi_region_detected,
        {
            region: {
                "devices": probe.device_count,
                "online": probe.online_count,
                "error": probe.error,
            }
            for region, probe in scan.per_region.items()
        },
    )
    return scan


def suggest_cloud_region(scan: CloudRegionScan, default: str) -> tuple[str, bool]:
    """Return the cloud region to suggest, and whether the user should confirm it.

    The region is clear when only one region has online devices, or when no
    device is online and only one region has devices at all. An account with
    no devices keeps the default.

    Args:
        scan: Result of async_scan_cloud_regions.
        default: Region to use when no region has devices, normally the
            account region.

    Returns:
        tuple[str, bool]: The suggested region, and True when the scan is
        ambiguous and the user should choose.
    """
    if scan.winner is None:
        return default, False
    online_regions = [region for region, probe in scan.per_region.items() if probe.online_count]
    ambiguous = len(online_regions) > 1 or (not online_regions and scan.multi_region_detected)
    return scan.winner, ambiguous
