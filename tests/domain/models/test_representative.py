"""Tests for Representative domain model validators and properties."""

import pytest
from pydantic import ValidationError

from colony_manager.domain.enums import DynastyOutcome, ModifierStat, RepresentativeType
from colony_manager.domain.models.personality import Personality
from colony_manager.domain.models.representative import (
    Representative,
    RepresentativeStats,
)


class TestRepresentativeStatsValidators:
    """Tests for RepresentativeStats field validators."""

    def test_all_stats_must_be_greater_than_zero(self):
        """All stats must be > 0 (not just >= 0)."""
        # Test each stat individually
        with pytest.raises(ValidationError) as exc_info:
            RepresentativeStats(ws=0, bs=10, s=10, t=10, ag=10, int=10, per=10, wp=10, fel=10)
        assert "ws" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            RepresentativeStats(ws=10, bs=0, s=10, t=10, ag=10, int=10, per=10, wp=10, fel=10)
        assert "bs" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            RepresentativeStats(ws=10, bs=10, s=0, t=10, ag=10, int=10, per=10, wp=10, fel=10)
        assert "s" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            RepresentativeStats(ws=10, bs=10, s=10, t=0, ag=10, int=10, per=10, wp=10, fel=10)
        assert "t" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            RepresentativeStats(ws=10, bs=10, s=10, t=10, ag=0, int=10, per=10, wp=10, fel=10)
        assert "ag" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            RepresentativeStats(ws=10, bs=10, s=10, t=10, ag=10, int=0, per=10, wp=10, fel=10)
        assert "int" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            RepresentativeStats(ws=10, bs=10, s=10, t=10, ag=10, int=10, per=0, wp=10, fel=10)
        assert "per" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            RepresentativeStats(ws=10, bs=10, s=10, t=10, ag=10, int=10, per=10, wp=0, fel=10)
        assert "wp" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            RepresentativeStats(ws=10, bs=10, s=10, t=10, ag=10, int=10, per=10, wp=10, fel=0)
        assert "fel" in str(exc_info.value)

    def test_negative_stats_rejected(self):
        """Negative stat values are rejected."""
        with pytest.raises(ValidationError):
            RepresentativeStats(
                ws=-1,
                bs=10,
                s=10,
                t=10,
                ag=10,
                int=10,
                per=10,
                wp=10,
                fel=10,
            )

    def test_positive_stats_accepted(self):
        """Positive stat values are accepted."""
        stats = RepresentativeStats(
            ws=45,
            bs=38,
            s=35,
            t=40,
            ag=30,
            int=52,
            per=41,
            wp=39,
            fel=47,
        )
        assert stats.ws == 45
        assert stats.int_ == 52
        assert stats.per == 41
        assert stats.fel == 47

    def test_int_alias_works(self):
        """The 'int' alias works for int_ field."""
        stats = RepresentativeStats(
            ws=10,
            bs=10,
            s=10,
            t=10,
            ag=10,
            int=50,
            per=10,
            wp=10,
            fel=10,
        )
        assert stats.int_ == 50


class TestRepresentativeStatsProperties:
    """Tests for RepresentativeStats bonus properties."""

    def test_int_bonus_calculation(self):
        """Intelligence bonus is stat // 10."""
        assert (
            RepresentativeStats(
                ws=10, bs=10, s=10, t=10, ag=10, int=10, per=10, wp=10, fel=10
            ).int_bonus
            == 1
        )
        assert (
            RepresentativeStats(
                ws=10, bs=10, s=10, t=10, ag=10, int=19, per=10, wp=10, fel=10
            ).int_bonus
            == 1
        )
        assert (
            RepresentativeStats(
                ws=10, bs=10, s=10, t=10, ag=10, int=20, per=10, wp=10, fel=10
            ).int_bonus
            == 2
        )
        assert (
            RepresentativeStats(
                ws=10, bs=10, s=10, t=10, ag=10, int=99, per=10, wp=10, fel=10
            ).int_bonus
            == 9
        )

    def test_per_bonus_calculation(self):
        """Perception bonus is stat // 10."""
        assert (
            RepresentativeStats(
                ws=10, bs=10, s=10, t=10, ag=10, int=10, per=10, wp=10, fel=10
            ).per_bonus
            == 1
        )
        assert (
            RepresentativeStats(
                ws=10, bs=10, s=10, t=10, ag=10, int=10, per=25, wp=10, fel=10
            ).per_bonus
            == 2
        )

    def test_fel_bonus_calculation(self):
        """Fellowship bonus is stat // 10."""
        assert (
            RepresentativeStats(
                ws=10, bs=10, s=10, t=10, ag=10, int=10, per=10, wp=10, fel=10
            ).fel_bonus
            == 1
        )
        assert (
            RepresentativeStats(
                ws=10, bs=10, s=10, t=10, ag=10, int=10, per=10, wp=10, fel=35
            ).fel_bonus
            == 3
        )

    def test_highest_leadership_bonus(self):
        """highest_leadership_bonus returns max of Int, Per, Fel bonuses."""
        stats = RepresentativeStats(ws=10, bs=10, s=10, t=10, ag=10, int=30, per=20, wp=10, fel=25)
        assert stats.highest_leadership_bonus == 3  # Int bonus

        stats = RepresentativeStats(ws=10, bs=10, s=10, t=10, ag=10, int=20, per=45, wp=10, fel=25)
        assert stats.highest_leadership_bonus == 4  # Per bonus

        stats = RepresentativeStats(ws=10, bs=10, s=10, t=10, ag=10, int=20, per=25, wp=10, fel=50)
        assert stats.highest_leadership_bonus == 5  # Fel bonus


class TestRepresentativeValidators:
    """Tests for Representative model validators."""

    def test_personalities_minimum_one_required(self):
        """Representative must have at least one personality."""
        with pytest.raises(ValueError, match="at least one personality"):
            Representative(
                name="Test Rep",
                type=RepresentativeType.JUDGE,
                personalities=[],
                stats=RepresentativeStats(
                    ws=10, bs=10, s=10, t=10, ag=10, int=10, per=10, wp=10, fel=10
                ),
            )

    def test_valid_representative_with_minimal_data(self):
        """Valid Representative with minimal required data."""
        rep = Representative(
            name="Judge Dredd",
            type=RepresentativeType.JUDGE,
            personalities=[Personality(name="lawful", display_name="Lawful", description="Lawful")],
            stats=RepresentativeStats(
                ws=10, bs=10, s=10, t=10, ag=10, int=10, per=10, wp=10, fel=10
            ),
        )
        assert rep.name == "Judge Dredd"
        assert rep.type == RepresentativeType.JUDGE
        assert len(rep.personalities) == 1
        assert rep.skills == []
        assert rep.talents == []
        assert rep.dynasty_outcome is None
        assert rep.calamitous_modifier == 0
        assert rep.assigned_to_colony_id is None
        assert rep.special_trait_description is None

    def test_skills_and_talents_default_to_empty_lists(self):
        """Skills and talents default to empty lists."""
        rep = Representative(
            name="Test",
            type=RepresentativeType.JUDGE,
            personalities=[Personality(name="test", display_name="Test", description="Test")],
            stats=RepresentativeStats(
                ws=10, bs=10, s=10, t=10, ag=10, int=10, per=10, wp=10, fel=10
            ),
        )
        assert rep.skills == []
        assert rep.talents == []

    def test_duplicate_personalities_rejected(self):
        """Duplicate personalities are rejected per Rogue Trader rules.

        Per Core Principles #5 and Table 3-6:
        "Personalities cannot be duplicated on the same Representative."
        "Select any combination. No duplicates allowed."
        """
        with pytest.raises(ValueError, match="Duplicate personalities not allowed"):
            Representative(
                name="Test",
                type=RepresentativeType.JUDGE,
                personalities=[
                    Personality(name="beloved", display_name="Beloved", description="Test 1"),
                    Personality(
                        name="beloved", display_name="Beloved", description="Test duplicate"
                    ),
                ],
                stats=RepresentativeStats(
                    ws=10, bs=10, s=10, t=10, ag=10, int=10, per=10, wp=10, fel=10
                ),
            )

    def test_unique_personalities_accepted(self):
        """Multiple unique personalities are accepted (up to 2 without Quite a Character)."""
        rep = Representative(
            name="Test",
            type=RepresentativeType.JUDGE,
            personalities=[
                Personality(name="beloved", display_name="Beloved", description="Test 1"),
                Personality(
                    name="military_minded", display_name="Military-Minded", description="Test 2"
                ),
            ],
            stats=RepresentativeStats(
                ws=10, bs=10, s=10, t=10, ag=10, int=10, per=10, wp=10, fel=10
            ),
        )
        assert len(rep.personalities) == 2
        assert rep.personalities[0].name == "beloved"
        assert rep.personalities[1].name == "military_minded"
        assert rep.talents == []

    def test_maximum_two_personalities_without_quite_a_character(self):
        """Without 'Quite a Character', maximum is 2 personalities."""
        # 2 personalities is valid
        rep = Representative(
            name="Test",
            type=RepresentativeType.JUDGE,
            personalities=[
                Personality(name="beloved", display_name="Beloved", description="Test 1"),
                Personality(
                    name="military_minded", display_name="Military-Minded", description="Test 2"
                ),
            ],
            stats=RepresentativeStats(
                ws=10, bs=10, s=10, t=10, ag=10, int=10, per=10, wp=10, fel=10
            ),
        )
        assert len(rep.personalities) == 2

        # 3 personalities without Quite a Character is invalid
        with pytest.raises(ValueError, match="Maximum is 2 personalities"):
            Representative(
                name="Test",
                type=RepresentativeType.JUDGE,
                personalities=[
                    Personality(name="beloved", display_name="Beloved", description="Test 1"),
                    Personality(
                        name="military_minded", display_name="Military-Minded", description="Test 2"
                    ),
                    Personality(name="zealous", display_name="Zealous", description="Test 3"),
                ],
                stats=RepresentativeStats(
                    ws=10, bs=10, s=10, t=10, ag=10, int=10, per=10, wp=10, fel=10
                ),
            )

    def test_quite_a_character_first_allows_four_personalities(self):
        """When 'Quite a Character' is first, up to 4 personalities are allowed."""
        quite_a_character = Personality(
            name="quite_a_character",
            display_name="Quite a character",
            description="This representative is uniquely complex.",
            special_rule=(
                "Increases maximum personality limit based on position: first=4, "
                "second=3, third+=2."
            ),
        )

        # 4 personalities with Quite a Character first is valid
        rep = Representative(
            name="Test",
            type=RepresentativeType.JUDGE,
            personalities=[
                quite_a_character,
                Personality(name="beloved", display_name="Beloved", description="Test 1"),
                Personality(
                    name="military_minded", display_name="Military-Minded", description="Test 2"
                ),
                Personality(name="zealous", display_name="Zealous", description="Test 3"),
            ],
            stats=RepresentativeStats(
                ws=10, bs=10, s=10, t=10, ag=10, int=10, per=10, wp=10, fel=10
            ),
        )
        assert len(rep.personalities) == 4
        assert rep.personalities[0].name == "quite_a_character"

        # 5 personalities is still invalid even with Quite a Character first
        with pytest.raises(ValueError, match="When 'Quite a Character' is first, maximum is 4"):
            Representative(
                name="Test",
                type=RepresentativeType.JUDGE,
                personalities=[
                    quite_a_character,
                    Personality(name="beloved", display_name="Beloved", description="Test 1"),
                    Personality(
                        name="military_minded", display_name="Military-Minded", description="Test 2"
                    ),
                    Personality(name="zealous", display_name="Zealous", description="Test 3"),
                    Personality(name="corrupt", display_name="Corrupt", description="Test 4"),
                ],
                stats=RepresentativeStats(
                    ws=10, bs=10, s=10, t=10, ag=10, int=10, per=10, wp=10, fel=10
                ),
            )

    def test_quite_a_character_second_allows_three_personalities(self):
        """When 'Quite a Character' is second, up to 3 personalities are allowed."""
        quite_a_character = Personality(
            name="quite_a_character",
            display_name="Quite a character",
            description="This representative is uniquely complex.",
            special_rule=(
                "Increases maximum personality limit based on position: first=4, "
                "second=3, third+=2."
            ),
        )

        # 3 personalities with Quite a Character second is valid
        rep = Representative(
            name="Test",
            type=RepresentativeType.JUDGE,
            personalities=[
                Personality(name="beloved", display_name="Beloved", description="Test 1"),
                quite_a_character,
                Personality(
                    name="military_minded", display_name="Military-Minded", description="Test 2"
                ),
            ],
            stats=RepresentativeStats(
                ws=10, bs=10, s=10, t=10, ag=10, int=10, per=10, wp=10, fel=10
            ),
        )
        assert len(rep.personalities) == 3
        assert rep.personalities[1].name == "quite_a_character"

        # 4 personalities with Quite a Character second is invalid
        with pytest.raises(ValueError, match="When 'Quite a Character' is second, maximum is 3"):
            Representative(
                name="Test",
                type=RepresentativeType.JUDGE,
                personalities=[
                    Personality(name="beloved", display_name="Beloved", description="Test 1"),
                    quite_a_character,
                    Personality(
                        name="military_minded", display_name="Military-Minded", description="Test 2"
                    ),
                    Personality(name="zealous", display_name="Zealous", description="Test 3"),
                ],
                stats=RepresentativeStats(
                    ws=10, bs=10, s=10, t=10, ag=10, int=10, per=10, wp=10, fel=10
                ),
            )

    def test_quite_a_character_third_position_no_bonus(self):
        """When 'Quite a Character' is third or later, base limit of 2 applies."""
        quite_a_character = Personality(
            name="quite_a_character",
            display_name="Quite a character",
            description="This representative is uniquely complex.",
            special_rule=(
                "Increases maximum personality limit based on position: first=4, "
                "second=3, third+=2."
            ),
        )

        # 3 personalities with Quite a Character third is invalid (exceeds base limit)
        with pytest.raises(ValueError, match="Maximum is 2 personalities"):
            Representative(
                name="Test",
                type=RepresentativeType.JUDGE,
                personalities=[
                    Personality(name="beloved", display_name="Beloved", description="Test 1"),
                    Personality(
                        name="military_minded", display_name="Military-Minded", description="Test 2"
                    ),
                    quite_a_character,
                ],
                stats=RepresentativeStats(
                    ws=10, bs=10, s=10, t=10, ag=10, int=10, per=10, wp=10, fel=10
                ),
            )

    def test_is_quite_a_character_helper_method(self):
        """Test the _is_quite_a_character static helper method."""
        # With name "quite_a_character"
        quite_a_character = Personality(
            name="quite_a_character",
            display_name="Quite a character",
            description="Test",
            special_rule=(
                "Increases maximum personality limit based on position: first=4, "
                "second=3, third+=2."
            ),
        )
        assert Representative._is_quite_a_character(quite_a_character) is True

        # Without quite_a_character name
        normal_personality = Personality(
            name="beloved",
            display_name="Beloved",
            description="Test",
        )
        assert Representative._is_quite_a_character(normal_personality) is False

        # With different name but similar special_rule
        other_personality = Personality(
            name="test",
            display_name="Test",
            description="Test",
            special_rule=(
                "Increases maximum personality limit based on position: first=4, "
                "second=3, third+=2."
            ),
        )
        assert Representative._is_quite_a_character(other_personality) is False


class TestRepresentativeProperties:
    """Tests for Representative properties."""

    def test_loss_mitigation_stat_judge(self):
        """Judge protects Order."""
        rep = Representative(
            name="Judge",
            type=RepresentativeType.JUDGE,
            personalities=[Personality(name="test", display_name="Test", description="Test")],
            stats=RepresentativeStats(
                ws=10, bs=10, s=10, t=10, ag=10, int=10, per=10, wp=10, fel=10
            ),
        )
        assert rep.loss_mitigation_stat == ModifierStat.ORDER

    def test_loss_mitigation_stat_cardinal(self):
        """Cardinal protects Piety."""
        rep = Representative(
            name="Cardinal",
            type=RepresentativeType.CARDINAL,
            personalities=[Personality(name="test", display_name="Test", description="Test")],
            stats=RepresentativeStats(
                ws=10, bs=10, s=10, t=10, ag=10, int=10, per=10, wp=10, fel=10
            ),
        )
        assert rep.loss_mitigation_stat == ModifierStat.PIETY

    def test_loss_mitigation_stat_colonist_representative(self):
        """Colonist Representative protects Complacency."""
        rep = Representative(
            name="Rep",
            type=RepresentativeType.COLONIST_REPRESENTATIVE,
            personalities=[Personality(name="test", display_name="Test", description="Test")],
            stats=RepresentativeStats(
                ws=10, bs=10, s=10, t=10, ag=10, int=10, per=10, wp=10, fel=10
            ),
        )
        assert rep.loss_mitigation_stat == ModifierStat.COMPLACENCY

    def test_loss_mitigation_stat_military_commander(self):
        """Military Commander protects Productivity."""
        rep = Representative(
            name="Commander",
            type=RepresentativeType.MILITARY_COMMANDER,
            personalities=[Personality(name="test", display_name="Test", description="Test")],
            stats=RepresentativeStats(
                ws=10, bs=10, s=10, t=10, ag=10, int=10, per=10, wp=10, fel=10
            ),
        )
        assert rep.loss_mitigation_stat == ModifierStat.PRODUCTIVITY

    def test_get_total_personality_calamity_modifier(self):
        """get_total_personality_calamity_modifier calculates total from personality objects."""
        from colony_manager.domain.models.personality import Personality

        rep = Representative(
            name="Test",
            type=RepresentativeType.JUDGE,
            personalities=[
                Personality(
                    name="calm", display_name="Calm", description="Calm", calamitous_modifier=1
                ),
                Personality(
                    name="rash", display_name="Rash", description="Rash", calamitous_modifier=2
                ),
            ],
            stats=RepresentativeStats(
                ws=10, bs=10, s=10, t=10, ag=10, int=10, per=10, wp=10, fel=10
            ),
        )

        # Calculates total directly from personality objects
        assert rep.get_total_personality_calamity_modifier() == 3

    def test_get_total_personality_calamity_modifier_excludes_quite_a_character(self):
        """'Quite a Character' personality is excluded from calamity sum."""
        from colony_manager.domain.models.personality import Personality

        rep = Representative(
            name="Test",
            type=RepresentativeType.JUDGE,
            personalities=[
                Personality(
                    name="quite_a_character",
                    display_name="Quite a character",
                    description="This representative is uniquely complex.",
                    calamitous_modifier=5,
                    special_rule=(
                        "Increases maximum personality limit based on position: first=4, "
                        "second=3, third+=2."
                    ),
                ),
                Personality(
                    name="normal",
                    display_name="Normal",
                    description="Normal",
                    calamitous_modifier=2,
                ),
            ],
            stats=RepresentativeStats(
                ws=10, bs=10, s=10, t=10, ag=10, int=10, per=10, wp=10, fel=10
            ),
        )

        # 'quite_a_character' is excluded from calamity calculation
        assert rep.get_total_personality_calamity_modifier() == 2

    def test_update_calamitous_modifier_without_dynasty(self):
        """update_calamitous_modifier calculates total without dynasty outcome."""
        from colony_manager.domain.models.personality import Personality

        rep = Representative(
            name="Test",
            type=RepresentativeType.JUDGE,
            personalities=[
                Personality(
                    name="test", display_name="Test", description="Test", calamitous_modifier=3
                ),
            ],
            stats=RepresentativeStats(
                ws=10, bs=10, s=10, t=10, ag=10, int=10, per=10, wp=10, fel=10
            ),
        )

        # Calculates total directly from personality objects
        rep.update_calamitous_modifier()
        assert rep.calamitous_modifier == 3

    def test_update_calamitous_modifier_with_dynasty_outcome(self):
        """update_calamitous_modifier includes dynasty outcome modifier."""
        from colony_manager.domain.models.personality import Personality

        rep = Representative(
            name="Dynasty Rep",
            type=RepresentativeType.DYNASTY_MEMBER,
            personalities=[
                Personality(
                    name="test", display_name="Test", description="Test", calamitous_modifier=1
                ),
            ],
            stats=RepresentativeStats(
                ws=10, bs=10, s=10, t=10, ag=10, int=10, per=10, wp=10, fel=10
            ),
            dynasty_outcome=DynastyOutcome.YOU_BUILT_THE_PALACE_ON_A_VOLCANO,
        )

        # Includes both personality and dynasty modifiers
        rep.update_calamitous_modifier()
        assert rep.calamitous_modifier == 6  # 1 from personality + 5 from dynasty outcome

    def test_update_calamitous_modifier_dynasty_modifiers(self):
        """All dynasty outcome modifiers are correctly applied."""
        from colony_manager.domain.models.personality import Personality

        dynasty_modifiers = {
            DynastyOutcome.THAT_ONE_HAS_POTENTIAL: 0,
            DynastyOutcome.ONE_TO_KEEP_AN_EYE_ON: 2,
            DynastyOutcome.THRILLING_HEROICS: 3,
            DynastyOutcome.COME_ON_ITS_JUST_A_GROX: 4,
            DynastyOutcome.YOU_BUILT_THE_PALACE_ON_A_VOLCANO: 5,
        }
        for outcome, expected_mod in dynasty_modifiers.items():
            rep = Representative(
                name="Test",
                type=RepresentativeType.DYNASTY_MEMBER,
                personalities=[
                    Personality(
                        name="test", display_name="Test", description="Test", calamitous_modifier=0
                    )
                ],
                stats=RepresentativeStats(
                    ws=10, bs=10, s=10, t=10, ag=10, int=10, per=10, wp=10, fel=10
                ),
                dynasty_outcome=outcome,
            )
            # Only dynasty modifier applies (personality has 0 calamitous modifier)
            rep.update_calamitous_modifier()
            assert rep.calamitous_modifier == expected_mod, f"Failed for {outcome}"
