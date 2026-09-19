"""Infrastructure rules for the colony manager.

Per Rogue Trader Colony Rules:
- Infrastructure has five states: planned, in_progress, working, needed, not_working
- planned: No mechanical effect (not yet installed)
- in_progress: No mechanical effect (currently being installed)
- working: Bonuses apply
- needed: Counts toward missing infrastructure penalty (-1 Complacency)
- not_working: Penalties apply

Modifiers are loaded from config/infrastructure_types.yaml to keep rule tables
as data, not code (per .clinerules/02-domain-modeling.md).
"""

from functools import lru_cache

from colony_manager.config.config_loaders import (
    ConfigurationError,
    InfrastructureConfigLoader,
    InfrastructureTypeConfig,
)
from colony_manager.domain.enums import (
    InfrastructureState,
    InfrastructureType,
    ModifierCategory,
    ModifierStat,
)
from colony_manager.domain.models.infrastructure import Infrastructure
from colony_manager.domain.models.modifier import Modifier, ModifierSourceType

# Global config loader instance
_config_loader = InfrastructureConfigLoader()


@lru_cache(maxsize=1)
def _get_config() -> dict[str, InfrastructureTypeConfig]:
    """Get cached configuration.

    Returns:
        Dictionary mapping infrastructure type name to config.

    Raises:
        ConfigurationError: If config cannot be loaded.
    """
    return _config_loader.load()


def get_infrastructure_modifiers(infrastructure: Infrastructure) -> list[Modifier]:
    """
    Get modifiers from an infrastructure based on its state.

    Args:
        infrastructure: The infrastructure to get modifiers from.

    Returns:
        List of modifiers (empty if state is planned or in_progress).

    Raises:
        ConfigurationError: If no config is found for the infrastructure type.
    """
    if infrastructure.state in (InfrastructureState.PLANNED, InfrastructureState.IN_PROGRESS):
        return []

    # Get config for this infrastructure type
    config = _get_config().get(infrastructure.infrastructure_type.value)
    if config is None:
        raise ConfigurationError(
            f"No config found for infrastructure type: {infrastructure.infrastructure_type}"
        )

    # Get state-specific config
    state_config = config.states.get(infrastructure.state.value)
    if state_config is None:
        raise ConfigurationError(
            f"No config found for infrastructure state: {infrastructure.state} "
            f"(type: {infrastructure.infrastructure_type})"
        )

    # Build modifiers from config
    modifiers = []
    for mod_config in state_config.modifiers:
        modifiers.append(
            Modifier(
                colony_id=infrastructure.colony_id,
                modifier_source_type=ModifierSourceType.INFRASTRUCTURE,
                modifier_category=ModifierCategory.PERMANENT,
                modifier_stat=ModifierStat(mod_config.stat),
                modifier_value=mod_config.value,
                description=(
                    f"{infrastructure.name} ({infrastructure.infrastructure_type.value} - "
                    f"{infrastructure.state.value})"
                ),
                is_active=True,
                source_entity_id=infrastructure.id,
            )
        )

    return modifiers


def apply_infrastructure_modifiers(
    infrastructure_list: list[Infrastructure],
) -> list[Modifier]:
    """
    Apply modifiers from all infrastructure in a colony.

    Args:
        infrastructure_list: List of all infrastructure in the colony.

    Returns:
        Combined list of all active modifiers.
    """
    all_modifiers = []
    for infra in infrastructure_list:
        all_modifiers.extend(get_infrastructure_modifiers(infra))
    return all_modifiers


def get_missing_infrastructure_penalty(
    infrastructure_list: list[Infrastructure],
    colony_id: int = 1,
) -> list[Modifier]:
    """
    Get penalty for missing required infrastructure types.

    Per business_analysis.md §3.1:
    Until each required infrastructure type is built (moved to Working),
    the colony suffers Complacency -1 per missing type.

    Required types: Transport, Power Network, Water Management, Food Production, Communications

    Args:
        infrastructure_list: List of all infrastructure in the colony.
        colony_id: The colony ID for the modifier.

    Returns:
        List containing a single penalty modifier if any types are missing,
        or empty list if all types are present and Working.
    """
    # All required infrastructure types
    required_types = {
        InfrastructureType.TRANSPORT,
        InfrastructureType.POWER_NETWORK,
        InfrastructureType.WATER_MANAGEMENT,
        InfrastructureType.FOOD_PRODUCTION,
        InfrastructureType.COMMUNICATIONS,
    }

    # Find which types have at least one Working instance
    working_types = {
        infra.infrastructure_type
        for infra in infrastructure_list
        if infra.state == InfrastructureState.WORKING
    }

    # Count missing types (not Working)
    missing_count = len(required_types - working_types)

    if missing_count == 0:
        return []

    # Apply -1 Complacency per missing type
    total_penalty = -1 * missing_count

    return [
        Modifier(
            colony_id=colony_id,
            modifier_source_type=ModifierSourceType.INFRASTRUCTURE,
            modifier_category=ModifierCategory.PERMANENT,
            modifier_stat=ModifierStat.COMPLACENCY,
            modifier_value=total_penalty,
            description=(
                f"Missing Infrastructure (-1 per type not Working, {missing_count} missing)"
            ),
            is_active=True,
        )
    ]
