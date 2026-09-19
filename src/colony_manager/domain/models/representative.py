"""Domain model for representatives."""

from pydantic import BaseModel, Field, model_validator

from colony_manager.domain.enums import (
    DynastyOutcome,
    ModifierStat,
    RepresentativeType,
    SkillLevel,
)
from colony_manager.domain.models.personality import Personality

# Re-export Personality for convenience
__all__ = [
    "Personality",
    "Representative",
    "RepresentativeStats",
    "Skill",
    "Talent",
]


class RepresentativeStats(BaseModel):
    ws: int = Field(gt=0)
    bs: int = Field(gt=0)
    s: int = Field(gt=0)
    t: int = Field(gt=0)
    ag: int = Field(gt=0)
    int_: int = Field(gt=0, alias="int")
    per: int = Field(gt=0)
    wp: int = Field(gt=0)
    fel: int = Field(gt=0)

    model_config = {"populate_by_name": True}

    @property
    def int_bonus(self) -> int:
        """Calculate Intelligence bonus (stat / 10, floor)."""
        return self.int_ // 10

    @property
    def per_bonus(self) -> int:
        """Calculate Perception bonus (stat / 10, floor)."""
        return self.per // 10

    @property
    def fel_bonus(self) -> int:
        """Calculate Fellowship bonus (stat / 10, floor)."""
        return self.fel // 10

    @property
    def highest_leadership_bonus(self) -> int:
        """Get highest of Int, Per, Fel bonus for Leadership modifier."""
        return max(self.int_bonus, self.per_bonus, self.fel_bonus)


class Skill(BaseModel):
    name: str
    level: SkillLevel
    description: str


class Talent(BaseModel):
    name: str
    description: str


class Representative(BaseModel):
    id: int | None = None
    name: str
    type: RepresentativeType
    personalities: list[Personality] = Field(default_factory=list)
    stats: RepresentativeStats
    skills: list[Skill] = Field(default_factory=list)
    talents: list[Talent] = Field(default_factory=list)
    # For Dynasty Member: chosen outcome from Consequences of Nepotism
    dynasty_outcome: DynastyOutcome | None = None
    # Cumulative calamitous events modifier from all sources
    calamitous_modifier: int = 0
    # Colony this representative is assigned to (if any)
    assigned_to_colony_id: int | None = None
    # Special trait description (GM reference note, no mechanical effect)
    special_trait_description: str | None = None

    @staticmethod
    def _is_quite_a_character(personality: Personality) -> bool:
        """Check if a personality is 'Quite a Character' based on name.

        Args:
            personality: The personality to check.

        Returns:
            True if the personality name is 'quite_a_character'.
        """
        return personality.name == "quite_a_character"

    @model_validator(mode="after")
    def validate_no_duplicate_personalities(self) -> "Representative":
        """Ensure no duplicate personalities are assigned.

        Per Rogue Trader Colony Rules (Core Principles #5, Table 3-6):
        "Personalities cannot be duplicated on the same Representative."
        "Select any combination. No duplicates allowed."

        Raises:
            ValueError: If duplicate personality names are found.
        """
        if self.personalities:
            seen_names = set()
            duplicates = []
            for personality in self.personalities:
                if personality.name in seen_names:
                    duplicates.append(personality.name)
                seen_names.add(personality.name)

            if duplicates:
                raise ValueError(
                    f"Duplicate personalities not allowed: {', '.join(duplicates)}. "
                    "Per Rogue Trader rules, each personality type can be selected only once."
                )
        return self

    @model_validator(mode="after")
    def validate_personality_count(self) -> "Representative":
        """Validate personality count based on 'Quite a Character' position.

        Per Rogue Trader Colony Rules (Table 3-6):
        - Base limit: 2 personalities maximum
        - If 'Quite a Character' is first (index 0): limit increases to 4
        - If 'Quite a Character' is second (index 1): limit increases to 3
        - Minimum: 1 personality required

        Raises:
            ValueError: If personality count violates the rules.
        """
        # Early exit: at least one personality required
        if not self.personalities:
            raise ValueError(
                "A representative must have at least one personality. "
                "Select at least one personality from the available options."
            )

        count = len(self.personalities)

        # Check for Quite a Character position
        quite_a_character_index = None
        for i, personality in enumerate(self.personalities):
            if self._is_quite_a_character(personality):
                quite_a_character_index = i
                break

        # Determine maximum allowed based on Quite a Character position
        if quite_a_character_index == 0:
            max_allowed = 4
        elif quite_a_character_index == 1:
            max_allowed = 3
        else:
            max_allowed = 2

        if count > max_allowed:
            if quite_a_character_index == 0:
                raise ValueError(
                    f"Cannot have {count} personalities. "
                    f"When 'Quite a Character' is first, maximum is 4 personalities."
                )
            elif quite_a_character_index == 1:
                raise ValueError(
                    f"Cannot have {count} personalities. "
                    f"When 'Quite a Character' is second, maximum is 3 personalities."
                )
            else:
                raise ValueError(
                    f"Cannot have {count} personalities. "
                    f"Maximum is 2 personalities without 'Quite a Character' "
                    f"in first or second position."
                )

        return self

    @property
    def loss_mitigation_stat(self) -> ModifierStat | None:
        """Get the stat this representative type protects from losses."""
        mitigation_map = {
            RepresentativeType.JUDGE: ModifierStat.ORDER,
            RepresentativeType.CARDINAL: ModifierStat.PIETY,
            RepresentativeType.COLONIST_REPRESENTATIVE: ModifierStat.COMPLACENCY,
            RepresentativeType.MILITARY_COMMANDER: ModifierStat.PRODUCTIVITY,
        }
        return mitigation_map.get(self.type)

    def get_total_personality_calamity_modifier(self) -> int:
        """Sum calamitous modifiers from all personalities.

        Returns:
            Total calamitous modifier from personalities (excluding 'Quite a Character').

        Note:
            Per Rogue Trader rules, 'Quite a Character' is excluded from the calamitous
            modifier calculation as it represents additional personality selections
            rather than a direct modifier.
        """
        total = 0
        for personality in self.personalities:
            # Skip 'Quite a Character' personality
            if personality.name == "quite_a_character":
                continue
            total += personality.calamitous_modifier
        return total

    def update_calamitous_modifier(self) -> None:
        """Recalculate total calamitous modifier from personalities and dynasty outcome."""
        total = self.get_total_personality_calamity_modifier()

        # Add dynasty outcome modifier if applicable
        if self.dynasty_outcome:
            dynasty_modifiers = {
                DynastyOutcome.THAT_ONE_HAS_POTENTIAL: 0,
                DynastyOutcome.ONE_TO_KEEP_AN_EYE_ON: 2,
                DynastyOutcome.THRILLING_HEROICS: 3,
                DynastyOutcome.COME_ON_ITS_JUST_A_GROX: 4,
                DynastyOutcome.YOU_BUILT_THE_PALACE_ON_A_VOLCANO: 5,
            }
            total += dynasty_modifiers.get(self.dynasty_outcome, 0)

        self.calamitous_modifier = total
