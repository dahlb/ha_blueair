"""Shared pytest fixtures for Blueair Home Assistant workflow tests."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from homeassistant.const import CONF_PASSWORD, CONF_REGION, CONF_USERNAME
import pytest

import custom_components

USERNAME = "user@example.com"
PASSWORD = "password"
REGION = "us"


class FakeBlueairCloud:
    """Stand-in for blueair_api's login helpers, the integration's only cloud boundary.

    Each call records its arguments. Setting ``aws_error`` or ``legacy_error``
    makes the matching helper raise, so tests can drive the failure paths.
    """

    def __init__(self) -> None:
        """Start with an account that has no devices and no MQTT credentials."""
        self.aws_calls: list[dict[str, Any]] = []
        self.legacy_calls: list[dict[str, Any]] = []
        self.aws_error: BaseException | None = None
        self.legacy_error: BaseException | None = None
        self.cleanup_calls = 0

    async def cleanup_client_session(self) -> None:
        """Record that the config flow closed the session it opened."""
        self.cleanup_calls += 1

    async def get_aws_devices(self, **kwargs: Any) -> tuple[Any, list[Any]]:
        """Return an AWS HTTP client without MQTT credentials and no devices.

        Args:
            kwargs: Arguments the integration passed.

        Returns:
            tuple[Any, list[Any]]: The client and its devices.

        Raises:
            BaseException: The configured ``aws_error``.
        """
        self.aws_calls.append(kwargs)
        if self.aws_error is not None:
            raise self.aws_error
        client = SimpleNamespace(
            mqtt_auth_name=None,
            mqtt_auth_signature=None,
            mqtt_auth_token=None,
            user_id=None,
            cleanup_client_session=self.cleanup_client_session,
        )
        return client, []

    async def get_devices(self, **kwargs: Any) -> tuple[Any, list[Any]]:
        """Return no legacy devices.

        Args:
            kwargs: Arguments the integration passed.

        Returns:
            tuple[Any, list[Any]]: The client and its devices.

        Raises:
            BaseException: The configured ``legacy_error``.
        """
        self.legacy_calls.append(kwargs)
        if self.legacy_error is not None:
            raise self.legacy_error
        return None, []


def entry_data(username: str = USERNAME) -> dict[str, str]:
    """Return config entry data for a Blueair account.

    Args:
        username: Account username.

    Returns:
        dict[str, str]: Config entry data.
    """
    return {CONF_USERNAME: username, CONF_PASSWORD: PASSWORD, CONF_REGION: REGION}


@pytest.fixture(autouse=True, scope="session")
def restrict_custom_components_path() -> Iterator[None]:
    """Limit ``custom_components`` to this repository's real directory.

    An editable install adds a setuptools path-hook placeholder to the
    ``custom_components`` namespace path, which Home Assistant iterates while
    creating the ``hass`` fixture.

    Yields:
        None: Control while the restricted path is active.
    """
    components_path = str(Path(__file__).parents[1] / "custom_components")
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(custom_components, "__path__", [components_path])
        yield


@pytest.fixture
def blueair_cloud(enable_custom_integrations: None) -> Iterator[FakeBlueairCloud]:
    """Patch blueair_api's login helpers wherever the integration imports them.

    Args:
        enable_custom_integrations: Lets Home Assistant load the integration.

    Yields:
        FakeBlueairCloud: The fake cloud.
    """
    cloud = FakeBlueairCloud()
    with (
        patch("custom_components.ha_blueair.get_aws_devices", cloud.get_aws_devices),
        patch("custom_components.ha_blueair.get_devices", cloud.get_devices),
        patch("custom_components.ha_blueair.config_flow.get_aws_devices", cloud.get_aws_devices),
    ):
        yield cloud
