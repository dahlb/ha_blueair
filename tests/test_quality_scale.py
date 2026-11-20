"""Validate the integration's quality_scale.yaml self-assessment."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

QUALITY_SCALE_FILE = (
    Path(__file__).parent.parent / "custom_components" / "ha_blueair" / "quality_scale.yaml"
)

# Rule names from Home Assistant's script/hassfest/quality_scale.py, by tier. hassfest
# skips this file for custom integrations, so keep these in sync when HA adds rules.
QUALITY_SCALE_TIERS: dict[str, tuple[str, ...]] = {
    "bronze": (
        "action-setup",
        "appropriate-polling",
        "brands",
        "common-modules",
        "config-flow",
        "config-flow-test-coverage",
        "dependency-transparency",
        "docs-actions",
        "docs-conditions",
        "docs-high-level-description",
        "docs-installation-instructions",
        "docs-removal-instructions",
        "docs-triggers",
        "entity-event-setup",
        "entity-unique-id",
        "has-entity-name",
        "runtime-data",
        "test-before-configure",
        "test-before-setup",
        "unique-config-entry",
    ),
    "silver": (
        "action-exceptions",
        "config-entry-unloading",
        "docs-configuration-parameters",
        "docs-installation-parameters",
        "entity-unavailable",
        "integration-owner",
        "log-when-unavailable",
        "parallel-updates",
        "reauthentication-flow",
        "test-coverage",
    ),
    "gold": (
        "devices",
        "diagnostics",
        "discovery",
        "discovery-update-info",
        "docs-data-update",
        "docs-examples",
        "docs-known-limitations",
        "docs-supported-devices",
        "docs-supported-functions",
        "docs-troubleshooting",
        "docs-use-cases",
        "dynamic-devices",
        "entity-category",
        "entity-device-class",
        "entity-disabled-by-default",
        "entity-translations",
        "exception-translations",
        "icon-translations",
        "reconfiguration-flow",
        "repair-issues",
        "stale-devices",
    ),
    "platinum": (
        "async-dependency",
        "inject-websession",
        "strict-typing",
    ),
}
QUALITY_SCALE_RULES: frozenset[str] = frozenset(
    rule for rules in QUALITY_SCALE_TIERS.values() for rule in rules
)


def _load_rules() -> dict[str, Any]:
    """Return the ``rules`` mapping from quality_scale.yaml.

    Returns:
        dict[str, Any]: Rule name to status string or status mapping.
    """
    data = yaml.safe_load(QUALITY_SCALE_FILE.read_text(encoding="utf-8"))
    assert set(data) == {"rules"}
    return data["rules"]


def test_quality_scale_lists_every_rule_exactly() -> None:
    """List every Home Assistant quality scale rule and nothing else."""
    assert set(_load_rules()) == QUALITY_SCALE_RULES


@pytest.mark.parametrize("rule", sorted(QUALITY_SCALE_RULES))
def test_quality_scale_rule_matches_hassfest_schema(rule: str) -> None:
    """Match hassfest's schema: a status, and a comment whenever a rule is exempt."""
    value = _load_rules()[rule]

    if isinstance(value, str):
        assert value in {"todo", "done"}
        return
    assert set(value) == {"status", "comment"}
    assert value["status"] in {"todo", "done", "exempt"}
    assert isinstance(value["comment"], str)
    assert value["comment"].strip()
