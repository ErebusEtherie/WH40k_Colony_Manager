"""Hypothesis property-based tests for state effects."""

from datetime import date

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from colony_manager.domain.enums import ColonyType
from colony_manager.domain.models.colony import Colony
from colony_manager.domain.rules.state_effects import (
    apply_anarchy_decay,
    apply_complacency_zero,
    apply_orderly_effect,
    apply_piety_zero,
    apply_pious_effect,
)


@st.composite
def colony_states(draw):
    """Generate random but valid colony states."""
    base_size = draw(st.integers(min_value=1, max_value=10))
    base_order = draw(st.integers(min_value=0, max_value=20))
    base_complacency = draw(st.integers(min_value=0, max_value=20))
    base_productivity = draw(st.integers(min_value=0, max_value=20))
    base_piety = draw(st.integers(min_value=0, max_value=20))
    order_locked = draw(st.booleans())
    complacency_locked = draw(st.booleans())
    productivity_locked = draw(st.booleans())
    colony_type = draw(st.sampled_from(list(ColonyType)))
    return Colony(
        name=draw(st.text(min_size=1, max_size=50)),
        founder_name=draw(st.text(min_size=1, max_size=50)),
        patron_name=None,
        colony_type=colony_type,
        base_size=base_size,
        base_order=base_order,
        base_complacency=base_complacency,
        base_productivity=base_productivity,
        base_piety=base_piety,
        age_days=0,
        age_last_updated=date.today(),
        order_locked=order_locked,
        complacency_locked=complacency_locked,
        productivity_locked=productivity_locked,
    )


class TestOrderlyEffectProperties:
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(colony_states())
    def test_orderly_bonus_is_binary(self, colony: Colony):
        """Orderly bonus is always either 0 or 2."""
        bonus = apply_orderly_effect(colony.base_order, colony.base_size)
        assert bonus in (0, 2)

    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(colony_states())
    def test_orderly_condition_is_deterministic(self, colony: Colony):
        """Orderly bonus depends solely on Order > Size."""
        bonus = apply_orderly_effect(colony.base_order, colony.base_size)
        expected = 2 if colony.base_order > colony.base_size else 0
        assert expected == bonus


class TestPiousEffectProperties:
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(colony_states())
    def test_pious_bonus_is_binary_tuple(self, colony: Colony):
        """Pious bonus is always (0, 0) or (1, 1)."""
        order_bonus, complacency_bonus = apply_pious_effect(colony.base_piety, colony.base_size)
        assert (order_bonus, complacency_bonus) in ((0, 0), (1, 1))

    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(colony_states())
    def test_pious_condition_is_deterministic(self, colony: Colony):
        """Pious bonus depends solely on Piety > Size."""
        order_bonus, complacency_bonus = apply_pious_effect(colony.base_piety, colony.base_size)
        expected = (1, 1) if colony.base_piety > colony.base_size else (0, 0)
        assert expected == (order_bonus, complacency_bonus)


class TestComplacencyZeroProperties:
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(
        colony_states(),
        st.integers(min_value=1, max_value=5),
        st.integers(min_value=1, max_value=5),
    )
    def test_complacency_zero_locks_applied(self, colony: Colony, roll_order: int, roll_prod: int):
        """Complacency = 0 always applies order and productivity locks."""
        c = colony.model_copy(update={"base_complacency": 0})
        result = apply_complacency_zero(c, roll_order, roll_prod)
        assert result.order_locked is True
        assert result.productivity_locked is True

    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(
        colony_states(),
        st.integers(min_value=1, max_value=5),
        st.integers(min_value=1, max_value=5),
    )
    def test_complacency_zero_stats_never_negative(
        self, colony: Colony, roll_order: int, roll_prod: int
    ):
        """Stats after Complacency = 0 penalty are never negative."""
        c = colony.model_copy(update={"base_complacency": 0})
        result = apply_complacency_zero(c, roll_order, roll_prod)
        assert result.base_order >= 0
        assert result.base_productivity >= 0


class TestPietyZeroProperties:
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(
        colony_states(),
        st.integers(min_value=1, max_value=5),
        st.integers(min_value=1, max_value=5),
    )
    def test_piety_zero_locks_applied(self, colony: Colony, roll_order: int, roll_complacency: int):
        """Piety = 0 always applies order and complacency locks."""
        c = colony.model_copy(update={"base_piety": 0})
        result = apply_piety_zero(c, roll_order, roll_complacency)
        assert result.order_locked is True
        assert result.complacency_locked is True

    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(
        colony_states(),
        st.integers(min_value=1, max_value=5),
        st.integers(min_value=1, max_value=5),
    )
    def test_piety_zero_stats_never_negative(
        self, colony: Colony, roll_order: int, roll_complacency: int
    ):
        """Stats after Piety = 0 penalty are never negative."""
        c = colony.model_copy(update={"base_piety": 0})
        result = apply_piety_zero(c, roll_order, roll_complacency)
        assert result.base_order >= 0
        assert result.base_complacency >= 0


class TestAnarchyDecayProperties:
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(
        colony_states(),
        st.integers(min_value=1, max_value=5),
        st.integers(min_value=1, max_value=5),
        st.integers(min_value=1, max_value=5),
    )
    def test_anarchy_decay_stats_never_negative(
        self, colony: Colony, roll_comp: int, roll_prod: int, roll_piety: int
    ):
        """Stats after Anarchy decay are never negative."""
        c = colony.model_copy(update={"base_order": 0})
        result = apply_anarchy_decay(c, roll_comp, roll_prod, roll_piety)
        assert result.base_complacency >= 0
        assert result.base_productivity >= 0
        assert result.base_piety >= 0
        assert result.base_size >= 0

    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(
        colony_states(),
        st.integers(min_value=1, max_value=5),
        st.integers(min_value=1, max_value=5),
        st.integers(min_value=1, max_value=5),
    )
    def test_anarchy_decay_decreases_or_maintains_stats(
        self, colony: Colony, roll_comp: int, roll_prod: int, roll_piety: int
    ):
        """Anarchy decay never increases stats."""
        c = colony.model_copy(update={"base_order": 0})
        result = apply_anarchy_decay(c, roll_comp, roll_prod, roll_piety)
        assert result.base_complacency <= c.base_complacency
        assert result.base_productivity <= c.base_productivity
        assert result.base_piety <= c.base_piety
        assert result.base_size <= c.base_size


class TestStateTransitionBoundaries:
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(st.integers(min_value=1, max_value=10), st.integers(min_value=0, max_value=20))
    def test_orderly_boundary_at_size_plus_one(self, size: int, order_value: int):
        """Orderly state activates exactly when Order > Size."""
        bonus = apply_orderly_effect(order_value, size)
        if order_value > size:
            assert bonus == 2
        else:
            assert bonus == 0

    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(st.integers(min_value=1, max_value=10), st.integers(min_value=0, max_value=20))
    def test_pious_boundary_at_size_plus_one(self, size: int, piety_value: int):
        """Pious state activates exactly when Piety > Size."""
        order_bonus, complacency_bonus = apply_pious_effect(piety_value, size)
        if piety_value > size:
            assert (order_bonus, complacency_bonus) == (1, 1)
        else:
            assert (order_bonus, complacency_bonus) == (0, 0)


class TestCascadingEffects:
    """Tests for multiple state effects occurring simultaneously."""

    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(
        st.integers(min_value=1, max_value=5),
        st.integers(min_value=1, max_value=5),
        st.integers(min_value=1, max_value=5),
        st.integers(min_value=1, max_value=5),
    )
    def test_anarchy_and_piety_zero_stack_locks(
        self, roll_order_c: int, roll_complacency_p: int, roll_comp_a: int, roll_prod_a: int
    ):
        """When Order = 0 AND Piety = 0, both lock sets apply
        (Order locked twice, Complacency locked).
        """
        colony = Colony(
            name="Test",
            founder_name="Test Founder",
            colony_type=ColonyType.MINING_AND_INDUSTRY,
            base_size=5,
            base_order=0,
            base_complacency=10,
            base_productivity=10,
            base_piety=0,
            age_days=0,
            age_last_updated=date.today(),
        )
        # Apply Piety = 0 first (locks Order and Complacency)
        after_piety = apply_piety_zero(colony, roll_order_c, roll_complacency_p)
        # Then apply Anarchy decay (Order is still 0)
        after_anarchy = apply_anarchy_decay(after_piety, roll_comp_a, roll_prod_a, 3)

        # Order should remain locked (was locked by Piety = 0)
        assert after_anarchy.order_locked is True
        # Complacency should be locked (from Piety = 0)
        assert after_anarchy.complacency_locked is True

    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(
        st.integers(min_value=1, max_value=5),
        st.integers(min_value=1, max_value=5),
        st.integers(min_value=1, max_value=5),
        st.integers(min_value=1, max_value=5),
    )
    def test_complacency_zero_and_piety_zero_stack_locks(
        self, roll_order_c: int, roll_prod_c: int, roll_order_p: int, roll_complacency_p: int
    ):
        """When Complacency = 0 AND Piety = 0, all three stats
        (Order, Complacency, Productivity) get locked.
        """
        colony = Colony(
            name="Test",
            founder_name="Test Founder",
            colony_type=ColonyType.MINING_AND_INDUSTRY,
            base_size=5,
            base_order=10,
            base_complacency=0,
            base_productivity=10,
            base_piety=0,
            age_days=0,
            age_last_updated=date.today(),
        )
        # Apply Complacency = 0 (locks Order and Productivity)
        after_complacency = apply_complacency_zero(colony, roll_order_c, roll_prod_c)
        # Then apply Piety = 0 (locks Order and Complacency)
        after_piety = apply_piety_zero(after_complacency, roll_order_p, roll_complacency_p)

        # All three should be locked
        assert after_piety.order_locked is True
        assert after_piety.complacency_locked is True
        assert after_piety.productivity_locked is True

    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(colony_states())
    def test_orderly_and_pious_can_coexist(self, colony: Colony):
        """Orderly and Pious states can both be active simultaneously."""
        # Set up colony where both Order > Size AND Piety > Size
        high_value = max(colony.base_size, 5) + 5
        colony = colony.model_copy(
            update={
                "base_order": high_value,
                "base_piety": high_value,
            }
        )

        orderly_bonus = apply_orderly_effect(colony.base_order, colony.base_size)
        pious_order_bonus, pious_complacency_bonus = apply_pious_effect(
            colony.base_piety, colony.base_size
        )

        # Both bonuses should be active
        assert orderly_bonus == 2
        assert (pious_order_bonus, pious_complacency_bonus) == (1, 1)

    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(
        st.integers(min_value=1, max_value=5),
        st.integers(min_value=1, max_value=5),
        st.integers(min_value=1, max_value=5),
        st.integers(min_value=1, max_value=5),
        st.integers(min_value=1, max_value=5),
    )
    def test_anarchy_decay_preserves_other_locks(
        self, roll_comp: int, roll_prod: int, roll_piety: int, roll_order_c: int, roll_prod_c: int
    ):
        """Anarchy decay doesn't clear existing locks from Complacency = 0."""
        colony = Colony(
            name="Test",
            founder_name="Test Founder",
            colony_type=ColonyType.MINING_AND_INDUSTRY,
            base_size=5,
            base_order=0,
            base_complacency=0,
            base_productivity=10,
            base_piety=10,
            age_days=0,
            age_last_updated=date.today(),
        )
        # First apply Complacency = 0 (locks Order and Productivity)
        after_complacency = apply_complacency_zero(colony, roll_order_c, roll_prod_c)
        assert after_complacency.order_locked is True
        assert after_complacency.productivity_locked is True

        # Then apply Anarchy decay
        after_anarchy = apply_anarchy_decay(after_complacency, roll_comp, roll_prod, roll_piety)

        # Locks should persist (Anarchy doesn't clear them)
        assert after_anarchy.order_locked is True
        assert after_anarchy.productivity_locked is True
