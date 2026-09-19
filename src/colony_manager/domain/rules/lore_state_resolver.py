"""Lore state resolver rules for the colony manager.

Per Rogue Trader Colony Rules:
- Complacency > Size → "Placated"
- Complacency == 0 → "riots and unrest"
- Order == 0 → "Anarchy"
- Order > Size → "Orderly"
- Productivity > Size → "Productive"
- Productivity == 0 → "Halted"
- Piety > Size → "Pious"
- Piety == 0 → "Heretical"
"""

from colony_manager.domain.enums import LoreState, ModifierStat


def _resolve_complacency_state(value: int, size: int) -> LoreState:
    """Resolve Complacency state per Rogue Trader Colony Rules.

    Args:
        value: Current Complacency value.
        size: Current colony Size for threshold comparison.

    Returns:
        PLACATED if value > size, RIOTS_AND_UNREST if value == 0, otherwise STABLE.
    """
    if value > size:
        return LoreState.PLACATED
    if value == 0:
        return LoreState.RIOTS_AND_UNREST
    return LoreState.STABLE


def _resolve_order_state(value: int, size: int) -> LoreState:
    """Resolve Order state per Rogue Trader Colony Rules.

    Args:
        value: Current Order value.
        size: Current colony Size for threshold comparison.

    Returns:
        ANARCHY if value == 0, ORDERLY if value > size, otherwise STABLE.
    """
    if value == 0:
        return LoreState.ANARCHY
    if value > size:
        return LoreState.ORDERLY
    return LoreState.STABLE


def _resolve_productivity_state(value: int, size: int) -> LoreState:
    """Resolve Productivity state per Rogue Trader Colony Rules.

    Args:
        value: Current Productivity value.
        size: Current colony Size for threshold comparison.

    Returns:
        PRODUCTIVE if value > size, HALTED if value == 0, otherwise STABLE.
    """
    if value > size:
        return LoreState.PRODUCTIVE
    if value == 0:
        return LoreState.HALTED
    return LoreState.STABLE


def _resolve_piety_state(value: int, size: int) -> LoreState:
    """Resolve Piety state per Rogue Trader Colony Rules.

    Args:
        value: Current Piety value.
        size: Current colony Size for threshold comparison.

    Returns:
        PIOUS if value > size, HERETICAL if value == 0, otherwise STABLE.
    """
    if value > size:
        return LoreState.PIOUS
    if value == 0:
        return LoreState.HERETICAL
    return LoreState.STABLE


def resolve_lore_state(stat: ModifierStat, value: int, size: int) -> LoreState:
    """
    Resolve the lore state label for a stat based on current value and size.

    Args:
        stat: The colony stat to resolve.
        value: Current value of the stat (after modifiers, clamped to >= 0).
        size: Current colony Size for threshold comparisons.

    Returns:
        The appropriate LoreState enum value.

    Raises:
        ValueError: If stat is not one of the four colony stats
            (Complacency, Order, Productivity, Piety).
    """
    resolvers = {
        ModifierStat.COMPLACENCY: _resolve_complacency_state,
        ModifierStat.ORDER: _resolve_order_state,
        ModifierStat.PRODUCTIVITY: _resolve_productivity_state,
        ModifierStat.PIETY: _resolve_piety_state,
    }

    resolver = resolvers.get(stat)
    if resolver is None:
        raise ValueError(f"Cannot resolve lore state for stat {stat}")

    return resolver(value, size)
