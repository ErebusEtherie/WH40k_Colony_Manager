"""Representative rules for the colony manager.

Per Rogue Trader Colony Rules:
- Representative types provide loss mitigation for specific stats:
  - Judge: Order losses reduced by 1 (min 1)
  - Cardinal: Piety losses reduced by 1 (min 1)
  - Colonist Representative: Complacency losses reduced by 1 (min 1)
  - Military Commander: Productivity losses reduced by 1 (min 1)
- Personalities provide stat bonuses/penalties
- Dynasty Member outcomes provide stat bonus + calamitous modifier
- Calamitous modifiers accumulate from personalities and dynasty outcomes
"""

from colony_manager.domain.enums import ModifierCategory, ModifierSourceType, ModifierStat
from colony_manager.domain.models.modifier import Modifier
from colony_manager.domain.models.representative import Representative


def get_personality_modifiers(
    representative: Representative,
    current_order: int = 0,
    current_size: int = 1,
    colony_id: int = 1,
) -> list[Modifier]:
    """
    Get all modifiers from representative's personalities.

    Args:
        representative: The representative to get personality modifiers from.
        current_order: Current Order stat for condition evaluation.
        current_size: Current Size stat for condition evaluation.

    Returns:
        List of modifiers from all personalities.

    Note:
        Conditional effects (e.g., "Administrative Expert: +2 Prod if Order > Size")
        are evaluated here based on the provided colony state.

        Variable dice effects (e.g., "Mad: -1d5 Order") are skipped - GM must
        provide the rolled value separately."""
    if representative.id is None:
        return []  # Can't create valid modifiers without an ID

    modifiers = []

    for personality in representative.personalities:
        # Skip "Quite a character" personality - doesn't provide direct modifiers
        if personality.name == "quite_a_character":
            continue

        for effect in personality.stat_effects:
            # Skip variable dice effects (e.g., "-1d5") - GM provides rolled value
            if isinstance(effect.value, str):
                continue

            # Evaluate conditional effects
            if effect.condition:
                if not _evaluate_condition(effect.condition, current_order, current_size):
                    continue

            modifiers.append(
                Modifier(
                    colony_id=colony_id,
                    modifier_source_type=ModifierSourceType.REPRESENTATIVE_LEADERSHIP,
                    modifier_category=ModifierCategory.PERMANENT,
                    modifier_stat=ModifierStat(effect.stat),
                    modifier_value=effect.value,
                    description=f"Personality: {personality.name}",
                    is_active=True,
                    source_entity_id=representative.id,
                )
            )

    return modifiers


def _evaluate_condition(condition: str, current_order: int, current_size: int) -> bool:
    """
    Evaluate a personality effect condition.

    Args:
        condition: The condition string (e.g., "order_greater_than_size").
        current_order: Current Order stat value.
        current_size: Current Size stat value.

    Returns:
        True if condition is met, False otherwise.

    Note:
        Unknown conditions log a warning and return False to prevent silent failures.
        This ensures new conditional personalities require explicit handler updates.
    """
    if condition == "order_greater_than_size":
        return current_order > current_size

    # Unknown conditions: log warning for debugging, return False to prevent silent failures
    # If you see this warning, add a handler for the new condition type above
    import warnings

    warnings.warn(
        f"Unknown personality condition: '{condition}'. Effect not applied. "
        f"Add handler in representative_rules._evaluate_condition()",
        stacklevel=2,
    )
    return False


def apply_loss_mitigation(
    stat: ModifierStat,
    loss_amount: int,
    representative: Representative | None,
) -> int:
    """
    Apply loss mitigation from representative type.

    Args:
        stat: The stat being reduced.
        loss_amount: The amount of loss before mitigation.
        representative: The representative (may provide mitigation).

    Returns:
        The mitigated loss amount (minimum 1 if loss occurred).

    Per rules:
    - Judge reduces Order losses by 1 (min 1)
    - Cardinal reduces Piety losses by 1 (min 1)
    - Colonist Representative reduces Complacency losses by 1 (min 1)
    - Military Commander reduces Productivity losses by 1 (min 1)
    """
    if loss_amount <= 0:
        return 0

    if not representative:
        return loss_amount

    mitigation_stat = representative.loss_mitigation_stat
    if not mitigation_stat or mitigation_stat != stat:
        return loss_amount

    # Apply reduction (minimum 1 loss if loss occurred)
    mitigated = loss_amount - 1
    return max(mitigated, 1)


def get_dynasty_outcome_modifiers(representative: Representative) -> list[Modifier]:
    """
    Get modifiers from Dynasty Member's chosen nepotism outcome.

    Args:
        representative: The representative (must be Dynasty Member type).

    Returns:
        List of modifiers from the chosen outcome.
    """
    if representative.type.value != "dynasty_member" or not representative.dynasty_outcome:
        return []

    # Outcomes are stored on the colony, not as modifiers
    # This function is for reference; actual effects applied elsewhere
    return []
