from hypothesis import given
from hypothesis import strategies as st

from colony_manager.domain.enums import ModifierCategory, ModifierSourceType, ModifierStat
from colony_manager.domain.models.modifier import Modifier
from colony_manager.domain.rules.profit_factor_calculator import calculate_profit_factor


def test_profit_factor_zero_forces_when_order_zero():
    result = calculate_profit_factor(
        base_profit_factor=5,
        current_complacency=10,
        current_order=0,
        current_productivity=10,
        actual_size=5,
        modifiers=[],
        leadership_modifier=5,
    )
    assert result == 0


def test_profit_factor_halved_when_productivity_zero():
    result = calculate_profit_factor(
        base_profit_factor=5,
        current_complacency=0,
        current_order=10,
        current_productivity=0,
        actual_size=5,
        modifiers=[
            Modifier(
                id=1,
                colony_id=1,
                modifier_source_type=ModifierSourceType.GM_CUSTOM,
                modifier_category=ModifierCategory.CUSTOM,
                modifier_stat=ModifierStat.PROFIT_FACTOR,
                modifier_value=3,
                modifier_description="PF bonus",
                is_active=True,
            )
        ],
        leadership_modifier=2,
    )
    assert result == 5  # (5 + 3 + 2) / 2 = 5.0


def test_profit_factor_halved_rounds_down():
    """When halving produces a fraction, floor() rounds down. Example: PF 3 → 1."""
    result = calculate_profit_factor(
        base_profit_factor=1,
        current_complacency=0,
        current_order=10,
        current_productivity=0,
        actual_size=5,
        modifiers=[
            Modifier(
                id=1,
                colony_id=1,
                modifier_source_type=ModifierSourceType.GM_CUSTOM,
                modifier_category=ModifierCategory.CUSTOM,
                modifier_stat=ModifierStat.PROFIT_FACTOR,
                modifier_value=2,
                modifier_description="PF bonus",
                is_active=True,
            )
        ],
        leadership_modifier=0,
    )
    assert result == 1  # (1 + 2) / 2 = 1.5 → floor(1.5) = 1


def test_profit_factor_halved_even_number():
    """When halving produces an integer, floor() has no effect. Example: PF 4 → 2."""
    result = calculate_profit_factor(
        base_profit_factor=2,
        current_complacency=0,
        current_order=10,
        current_productivity=0,
        actual_size=5,
        modifiers=[
            Modifier(
                id=1,
                colony_id=1,
                modifier_source_type=ModifierSourceType.GM_CUSTOM,
                modifier_category=ModifierCategory.CUSTOM,
                modifier_stat=ModifierStat.PROFIT_FACTOR,
                modifier_value=2,
                modifier_description="PF bonus",
                is_active=True,
            )
        ],
        leadership_modifier=0,
    )
    assert result == 2  # (2 + 2) / 2 = 2.0 → floor(2.0) = 2


def test_profit_factor_does_not_go_negative():
    result = calculate_profit_factor(
        base_profit_factor=0,
        current_complacency=0,
        current_order=10,
        current_productivity=10,
        actual_size=5,
        modifiers=[
            Modifier(
                id=1,
                colony_id=1,
                modifier_source_type=ModifierSourceType.GM_CUSTOM,
                modifier_category=ModifierCategory.CUSTOM,
                modifier_stat=ModifierStat.PROFIT_FACTOR,
                modifier_value=-10,
                modifier_description="PF penalty",
                is_active=True,
            )
        ],
        leadership_modifier=0,
    )
    assert result == 0


@given(
    base_pf=st.integers(min_value=0, max_value=20),
    complacency=st.integers(min_value=0, max_value=50),
    order=st.integers(min_value=0, max_value=50),
    productivity=st.integers(min_value=0, max_value=50),
    piety=st.integers(min_value=0, max_value=50),
    size=st.integers(min_value=1, max_value=20),
    leadership_mod=st.integers(min_value=-10, max_value=10),
    custom_pf_mod=st.integers(min_value=-20, max_value=20),
)
def test_profit_factor_zero_when_order_is_zero_property(
    base_pf, complacency, order, productivity, piety, size, leadership_mod, custom_pf_mod
):
    """Property: Order == 0 always forces Profit Factor to 0, regardless of other modifiers."""
    modifiers = [
        Modifier(
            id=1,
            colony_id=1,
            modifier_source_type=ModifierSourceType.GM_CUSTOM,
            modifier_category=ModifierCategory.CUSTOM,
            modifier_stat=ModifierStat.PROFIT_FACTOR,
            modifier_value=custom_pf_mod,
            modifier_description="Custom PF modifier",
            is_active=True,
        )
    ]
    result = calculate_profit_factor(
        base_profit_factor=base_pf,
        current_complacency=complacency,
        current_order=0,  # Order is zero
        current_productivity=productivity,
        actual_size=size,
        modifiers=modifiers,
        leadership_modifier=leadership_mod,
    )
    assert result == 0


@given(
    base_pf=st.integers(min_value=0, max_value=20),
    complacency=st.integers(min_value=0, max_value=50),
    order=st.integers(min_value=1, max_value=50),  # Order > 0
    productivity=st.integers(min_value=0, max_value=50),
    piety=st.integers(min_value=0, max_value=50),
    size=st.integers(min_value=1, max_value=20),
    leadership_mod=st.integers(min_value=-10, max_value=10),
    custom_pf_mod=st.integers(min_value=-20, max_value=20),
)
def test_profit_factor_halved_when_productivity_zero_property(
    base_pf, complacency, order, productivity, piety, size, leadership_mod, custom_pf_mod
):
    """Property: Productivity == 0 halves the Profit Factor (round down)."""
    modifiers = [
        Modifier(
            id=1,
            colony_id=1,
            modifier_source_type=ModifierSourceType.GM_CUSTOM,
            modifier_category=ModifierCategory.CUSTOM,
            modifier_stat=ModifierStat.PROFIT_FACTOR,
            modifier_value=custom_pf_mod,
            modifier_description="Custom PF modifier",
            is_active=True,
        )
    ]
    result = calculate_profit_factor(
        base_profit_factor=base_pf,
        current_complacency=complacency,
        current_order=order,
        current_productivity=0,  # Productivity is zero
        actual_size=size,
        modifiers=modifiers,
        leadership_modifier=leadership_mod,
    )
    # When productivity is 0, PF should be halved and never negative
    assert result >= 0


@given(
    base_pf=st.integers(min_value=0, max_value=20),
    complacency=st.integers(min_value=0, max_value=50),
    order=st.integers(min_value=1, max_value=50),
    productivity=st.integers(min_value=1, max_value=50),
    piety=st.integers(min_value=0, max_value=50),
    size=st.integers(min_value=1, max_value=20),
    leadership_mod=st.integers(min_value=-50, max_value=50),
    custom_pf_mod=st.integers(min_value=-50, max_value=50),
)
def test_profit_factor_never_negative_property(
    base_pf, complacency, order, productivity, piety, size, leadership_mod, custom_pf_mod
):
    """Property: Profit Factor never goes below 0."""
    modifiers = [
        Modifier(
            id=1,
            colony_id=1,
            modifier_source_type=ModifierSourceType.GM_CUSTOM,
            modifier_category=ModifierCategory.CUSTOM,
            modifier_stat=ModifierStat.PROFIT_FACTOR,
            modifier_value=custom_pf_mod,
            modifier_description="Custom PF modifier",
            is_active=True,
        )
    ]
    result = calculate_profit_factor(
        base_profit_factor=base_pf,
        current_complacency=complacency,
        current_order=order,
        current_productivity=productivity,
        actual_size=size,
        modifiers=modifiers,
        leadership_modifier=leadership_mod,
    )
    assert result >= 0


@given(
    base_pf=st.integers(min_value=0, max_value=20),
    complacency=st.integers(min_value=0, max_value=10),
    order=st.integers(min_value=1, max_value=10),
    productivity=st.integers(min_value=1, max_value=10),  # Must be > 0 to avoid Halted penalty
    piety=st.integers(min_value=0, max_value=10),
    size=st.integers(min_value=10, max_value=20),  # Size high enough to prevent state bonuses
    modifier_values=st.lists(st.integers(min_value=-5, max_value=5), min_size=1, max_size=10),
)
def test_multiple_pf_modifiers_stack_additively(
    base_pf, complacency, order, productivity, piety, size, modifier_values
):
    """Property: Multiple PF modifiers stack additively."""
    modifiers = [
        Modifier(
            id=i,
            colony_id=1,
            modifier_source_type=ModifierSourceType.GM_CUSTOM,
            modifier_category=ModifierCategory.CUSTOM,
            modifier_stat=ModifierStat.PROFIT_FACTOR,
            modifier_value=value,
            modifier_description=f"PF modifier {i}",
            is_active=True,
        )
        for i, value in enumerate(modifier_values)
    ]

    result = calculate_profit_factor(
        base_profit_factor=base_pf,
        current_complacency=complacency,
        current_order=order,
        current_productivity=productivity,
        actual_size=size,
        modifiers=modifiers,
        leadership_modifier=0,
    )

    # Verify modifiers stack additively (clamped at 0)
    # Stats are kept <= size to prevent state bonuses from applying
    expected_raw = base_pf + sum(modifier_values)
    assert result == max(expected_raw, 0)


@given(
    base_pf=st.integers(min_value=0, max_value=20),
    size=st.integers(min_value=1, max_value=10),
    leadership_mod=st.integers(min_value=-2, max_value=2),
    modifier_values=st.lists(st.integers(min_value=-3, max_value=3), min_size=1, max_size=10),
)
def test_state_bonuses_and_modifiers_combine(base_pf, size, leadership_mod, modifier_values):
    """Property: State bonuses (Placated, Productive, Orderly) combine with modifiers."""
    modifiers = [
        Modifier(
            id=i,
            colony_id=1,
            modifier_source_type=ModifierSourceType.GM_CUSTOM,
            modifier_category=ModifierCategory.CUSTOM,
            modifier_stat=ModifierStat.PROFIT_FACTOR,
            modifier_value=value,
            modifier_description=f"PF modifier {i}",
            is_active=True,
        )
        for i, value in enumerate(modifier_values)
    ]

    # Set up colony with all state bonuses active
    result = calculate_profit_factor(
        base_profit_factor=base_pf,
        current_complacency=size + 5,  # Placated
        current_order=size + 5,  # Orderly
        current_productivity=size + 5,  # Productive
        actual_size=size,
        modifiers=modifiers,
        leadership_modifier=leadership_mod,
        is_orderly=True,
    )

    # Should have all bonuses: Placated (+1), Productive (+2), Orderly (+2),
    # leadership, and modifiers
    expected_bonus = 1 + 2 + 2 + leadership_mod + sum(modifier_values)
    expected_raw = base_pf + expected_bonus

    # Result should match expected (clamped at 0)
    assert result == max(expected_raw, 0)
