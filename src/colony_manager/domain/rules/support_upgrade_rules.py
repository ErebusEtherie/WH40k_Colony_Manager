"""Support Upgrade rules for the colony manager.

Per Rogue Trader Colony Rules:
- Support Upgrades provide stat bonuses and mechanical effects
- Mechanical effects are lore-only (no time tracking in engine)
- Some upgrades have conditional bonuses (e.g., Mechanicum varies by colony type)
- Cultural Improvement allows choosing any stat except Size

Modifiers are loaded from config/support_upgrades.yaml to keep rule tables
as data, not code (per .clinerules/02-domain-modeling.md).
"""

from functools import lru_cache

from colony_manager.config.config_loaders import (
    ConfigurationError,
    SupportUpgradeConfig,
    SupportUpgradeConfigLoader,
)
from colony_manager.domain.enums import (
    ColonyType,
    ModifierCategory,
    ModifierStat,
    SupportUpgradeType,
)
from colony_manager.domain.models.modifier import Modifier, ModifierSourceType
from colony_manager.domain.models.support_upgrade import SupportUpgrade

# Global config loader instance
_config_loader = SupportUpgradeConfigLoader()


@lru_cache(maxsize=1)
def _get_config() -> dict[str, SupportUpgradeConfig]:
    """Get cached configuration.

    Returns:
        Dictionary mapping support upgrade name to config.

    Raises:
        ConfigurationError: If config cannot be loaded.
    """
    return _config_loader.load()


def get_support_upgrade_modifiers(
    upgrade: SupportUpgrade,
    colony_type: ColonyType | None = None,
) -> list[Modifier]:
    """
    Get modifiers from a support upgrade.

    Args:
        upgrade: The support upgrade to get modifiers from.
        colony_type: Colony type for conditional bonuses (e.g., Mechanicum).

    Returns:
        List of modifiers from this upgrade.

    Raises:
        ConfigurationError: If no config is found for the upgrade type.
    """
    # Get config for this upgrade type
    config = _get_config().get(upgrade.upgrade_type.value)
    if config is None:
        raise ConfigurationError(
            f"No config found for support upgrade type: {upgrade.upgrade_type}"
        )

    modifiers = []

    # Handle Cultural Improvement custom choice
    if upgrade.upgrade_type == SupportUpgradeType.CULTURAL_IMPROVEMENT:
        if upgrade.custom_stat_choice and upgrade.custom_stat_choice != ModifierStat.SIZE:
            modifiers.append(
                Modifier(
                    colony_id=upgrade.colony_id,
                    modifier_source_type=ModifierSourceType.SUPPORT_UPGRADE,
                    modifier_category=ModifierCategory.PERMANENT,
                    modifier_stat=upgrade.custom_stat_choice,
                    modifier_value=1,
                    description=f"{upgrade.name} (chosen: {upgrade.custom_stat_choice.value})",
                    is_active=True,
                    source_entity_id=upgrade.id,
                )
            )
        return modifiers

    # Handle standard stat effects from config
    for stat_effect in config.stat_effects:
        # Check for conditional bonuses
        final_value = stat_effect.value

        if stat_effect.conditional_bonuses and colony_type:
            for conditional in stat_effect.conditional_bonuses:
                if colony_type.value in conditional.colony_types:
                    final_value = conditional.value
                    break

        # Skip if this is a custom_choice stat (handled separately)
        if stat_effect.stat == "custom_choice":
            continue

        modifiers.append(
            Modifier(
                colony_id=upgrade.colony_id,
                modifier_source_type=ModifierSourceType.SUPPORT_UPGRADE,
                modifier_category=ModifierCategory.PERMANENT,
                modifier_stat=ModifierStat(stat_effect.stat),
                modifier_value=final_value,
                description=(
                    f"{upgrade.name} ({_get_conditional_description(stat_effect, colony_type)})"
                ),
                is_active=True,
                source_entity_id=upgrade.id,
            )
        )

    return modifiers


def _get_conditional_description(
    stat_effect,
    colony_type: ColonyType | None,
) -> str:
    """Get description showing conditional bonus context.

    Args:
        stat_effect: The stat effect config.
        colony_type: The colony type.

    Returns:
        Description string showing final value and context.
    """
    if not stat_effect.conditional_bonuses:
        return f"+{stat_effect.value}"

    # Find if any conditional applies
    if colony_type:
        for conditional in stat_effect.conditional_bonuses:
            if colony_type.value in conditional.colony_types:
                return f"+{conditional.value} for {colony_type.value.replace('_', ' ').title()}"

    # No conditional matched, show base value
    return f"+{stat_effect.value}"


def apply_support_upgrade_modifiers(
    upgrades: list[SupportUpgrade],
    colony_type: ColonyType | None = None,
) -> list[Modifier]:
    """
    Apply modifiers from all support upgrades in a colony.

    Args:
        upgrades: List of all support upgrades in the colony.
        colony_type: Colony type for conditional bonuses.

    Returns:
        Combined list of all active modifiers.
    """
    all_modifiers = []
    for upgrade in upgrades:
        all_modifiers.extend(get_support_upgrade_modifiers(upgrade, colony_type))
    return all_modifiers
