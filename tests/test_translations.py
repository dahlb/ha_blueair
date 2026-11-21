"""Tests that entity names, states and icons are translated."""

from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import pytest

from .conftest import (
    make_climate_device,
    make_combo,
    make_humidifier,
    make_legacy_device,
    make_purifier,
)

INTEGRATION_DIR = Path(__file__).parents[1] / "custom_components" / "ha_blueair"


def _load(file_name: str) -> dict[str, Any]:
    """Return a JSON file from the integration.

    Args:
        file_name: Path relative to the integration directory.

    Returns:
        dict[str, Any]: The parsed file.
    """
    return json.loads((INTEGRATION_DIR / file_name).read_text(encoding="utf-8"))


@pytest.mark.asyncio
@pytest.mark.parametrize("file_name", ["strings.json", "translations/en.json"])
async def test_every_entity_has_a_translated_name(
    hass: HomeAssistant, setup_blueair: Callable[..., Any], file_name: str
) -> None:
    """Give every entity a translation key with a name in strings.json."""
    entry = await setup_blueair(
        aws=[
            make_purifier(),
            make_humidifier(uuid="humidifier-1"),
            make_combo(),
            make_climate_device(),
        ],
        legacy=[make_legacy_device()],
    )
    entity_strings = _load(file_name)["entity"]

    entities = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    assert entities
    used: set[tuple[str, str]] = set()
    for entity in entities:
        assert entity.translation_key, entity.entity_id
        assert entity_strings[entity.domain][entity.translation_key]["name"], entity.entity_id
        used.add((entity.domain, entity.translation_key))

    defined = {(domain, key) for domain, keys in entity_strings.items() for key in keys}
    assert used <= defined


def test_icons_use_translation_keys_that_exist() -> None:
    """Only define icons for entities strings.json names."""
    entity_strings = _load("strings.json")["entity"]
    for domain, keys in _load("icons.json")["entity"].items():
        for key in keys:
            assert key in entity_strings[domain], f"{domain}.{key}"
