"""Upgrade limit validation for the colony manager.

Per Rogue Trader Colony Rules:
"A Colony cannot have more Support Upgrades than its Size."

Additionally, certain upgrades have per-type limits:
- Mechanicum Station: 1 per colony
- Infantry Garrison: 1 per colony
- Imperial Navy Station: 1 per colony
- Cultural Improvement: 5 per colony (one per stat)
- Personal Lodgings: 1 per colony (no benefit after first)
- Others: Unlimited (can be purchased multiple times)
"""

import json
from pathlib import Path
from typing import Any

from colony_manager.domain.enums import SupportUpgradeType
from colony_manager.domain.models.colony import Colony
from colony_manager.domain.models.support_upgrade import SupportUpgrade

# Load upgrade limits from config
_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "upgrade_limits.json"


def _load_upgrade_limits() -> dict[str, Any]:
    """Load upgrade limits from config file."""
    with open(_CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def validate_upgrade_limits(
    colony: Colony,
    new_upgrade: SupportUpgrade,
) -> list[str]:
    """
    Validate that adding a new upgrade doesn't exceed limits.

    Per Rogue Trader Colony Rules:
    "A Colony cannot have more Support Upgrades than its Size."

    Additionally checks per-type limits from config.

    Args:
        colony: The colony to validate against.
        new_upgrade: The upgrade being added.

    Returns:
        List of validation error messages (empty if valid).
    """
    errors = []
    limits = _load_upgrade_limits()

    # Check global limit: total upgrades <= Size
    current_count = len(colony.support_upgrades)
    # Note: We're checking before adding, so +1 for the new upgrade
    if current_count + 1 > colony.base_size:
        errors.append(
            f"Cannot add upgrade: Colony Size {colony.base_size} limits "
            f"total upgrades to {colony.base_size}, but colony would have "
            f"{current_count + 1} upgrades."
        )

    # Check per-type limits
    per_type_limits = limits.get("per_type_limits", {})
    upgrade_key = new_upgrade.upgrade_type.value
    max_count = per_type_limits.get(upgrade_key)

    if max_count is not None:  # None means unlimited
        current_type_count = sum(
            1 for u in colony.support_upgrades if u.upgrade_type == new_upgrade.upgrade_type
        )
        if current_type_count + 1 > max_count:
            errors.append(
                f"Cannot add {new_upgrade.upgrade_type.value}: "
                f"Limit is {max_count}, but colony would have "
                f"{current_type_count + 1}."
            )

    return errors


def check_upgrade_limits(colony: Colony) -> dict[str, Any]:
    """
    Check current upgrade limit status for a colony.

    Args:
        colony: The colony to check.

    Returns:
        Dict with limit status:
        - "global_ok": True if total upgrades <= Size
        - "per_type_ok": Dict of upgrade_type -> True/False
        - "warnings": List of warning messages
    """
    limits = _load_upgrade_limits()
    warnings = []

    # Check global limit
    global_ok = len(colony.support_upgrades) <= colony.base_size
    if not global_ok:
        warnings.append(
            f"Colony has {len(colony.support_upgrades)} upgrades but Size "
            f"is {colony.base_size} (over limit by "
            f"{len(colony.support_upgrades) - colony.base_size})."
        )

    # Check per-type limits
    per_type_limits = limits.get("per_type_limits", {})
    per_type_ok: dict[str, bool] = {}

    for upgrade_type_str, max_count in per_type_limits.items():
        if max_count is None:
            per_type_ok[upgrade_type_str] = True
            continue

        upgrade_type = SupportUpgradeType(upgrade_type_str)
        count = sum(1 for u in colony.support_upgrades if u.upgrade_type == upgrade_type)
        per_type_ok[upgrade_type_str] = count <= max_count

        if count > max_count:
            warnings.append(
                f"Colony has {count} {upgrade_type_str} but limit is "
                f"{max_count} (over limit by {count - max_count})."
            )

    return {
        "global_ok": global_ok,
        "per_type_ok": per_type_ok,
        "warnings": warnings,
    }
