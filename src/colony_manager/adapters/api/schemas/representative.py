"""Representative API schemas."""

from pydantic import BaseModel, Field, model_validator

from colony_manager.domain.enums import RepresentativeType
from colony_manager.domain.models.personality import Personality, PersonalityEffect
from colony_manager.domain.models.representative import Skill, Talent


class RepresentativeStatsCreate(BaseModel):
    """Schema for creating representative stats."""

    ws: int = Field(ge=1, le=100)
    bs: int = Field(ge=1, le=100)
    s: int = Field(ge=1, le=100)
    t: int = Field(ge=1, le=100)
    ag: int = Field(ge=1, le=100)
    intelligence: int = Field(ge=1, le=100, alias="int")
    per: int = Field(ge=1, le=100)
    wp: int = Field(ge=1, le=100)
    fel: int = Field(ge=1, le=100)


class PersonalityCreate(BaseModel):
    """Schema for creating a personality with simplified effect string."""

    name: str
    display_name: str | None = None  # Domain model defaults to name if None
    description: str
    effect: str = Field(default="")
    calamitous_modifier: int = Field(default=0)
    special_rule: str | None = Field(default=None)


def parse_personality_effect(effect_str: str) -> list[PersonalityEffect]:
    """Parse a simple effect string like '+1 Fel' into PersonalityEffect list."""
    if not effect_str or effect_str.strip() == "":
        return []
    effect_str = effect_str.strip()
    sign = -1 if effect_str.startswith("-") else 1
    if effect_str[0] in "+-":
        effect_str = effect_str[1:]
    parts = effect_str.split()
    if len(parts) < 2:
        return []
    try:
        value = int(parts[0]) * sign
        stat_name = parts[1].lower()
        return [PersonalityEffect(stat=stat_name, value=value, condition=None)]
    except ValueError:
        pass
    return []


class RepresentativeCreate(BaseModel):
    """Schema for creating a new representative.

    Personality count rules (per Rogue Trader Table 3-6):
    - Base limit: 2 personalities maximum
    - If 'Quite a Character' is first (index 0): limit increases to 4
    - If 'Quite a Character' is second (index 1): limit increases to 3
    - Minimum: 1 personality required
    """

    name: str = Field(..., min_length=1, max_length=100)
    type: RepresentativeType
    personalities: list[PersonalityCreate] = Field(
        default_factory=list,
        description=(
            "List of 1-4 personalities. Count limit depends on 'Quite a Character' position."
        ),
    )
    stats: RepresentativeStatsCreate
    skills: list[Skill] = Field(default_factory=list)
    talents: list[Talent] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_personality_count(self) -> "RepresentativeCreate":
        """Validate personality count based on 'Quite a Character' position."""
        if not self.personalities:
            raise ValueError(
                "A representative must have at least one personality. "
                "Select at least one personality from the available options."
            )

        count = len(self.personalities)

        # Check for Quite a Character position by name
        # (Both PersonalityCreate and Personality use 'quite_a_character' as the name)
        quite_a_character_index = None
        for i, personality in enumerate(self.personalities):
            if personality.name == "quite_a_character":
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


class RepresentativeUpdate(BaseModel):
    """Schema for updating a representative (partial update)."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    personalities: list[PersonalityCreate] | None = None
    stats: RepresentativeStatsCreate | None = None
    skills: list[Skill] | None = None
    talents: list[Talent] | None = None


class RepresentativeListItem(BaseModel):
    """Summary information for representative list."""

    id: int | None
    name: str
    type: RepresentativeType
    leadership_modifier: int
    assigned_to_colony_id: int | None


class RepresentativeResponse(BaseModel):
    """Full representative response."""

    id: int | None
    name: str
    type: RepresentativeType
    personalities: list[Personality]
    stats: RepresentativeStatsCreate
    skills: list[Skill]
    talents: list[Talent]
    leadership_modifier: int
    assigned_to_colony_id: int | None
    assignment_change: "AssignmentChangeInfo | None" = Field(
        default=None,
        description=(
            "Change tracking information for assignment/unassign "
            "operations (None for other endpoints)"
        ),
    )


class AssignmentChangeInfo(BaseModel):
    """Information about changes made during representative assignment/unassignment.

    This provides explicit feedback about what changed when assigning or unassigning
    a representative, including the previous and new representative IDs and leadership
    modifier values.
    """

    representative_changed: bool = Field(
        default=True,
        description=(
            "Whether the representative assignment changed "
            "(always true for assign/unassign operations)"
        ),
    )
    previous_representative_id: int | None = Field(
        default=None,
        description=(
            "ID of the previously assigned representative (None if no previous representative)"
        ),
    )
    new_representative_id: int | None = Field(
        default=None,
        description="ID of the newly assigned representative (None for unassign operations)",
    )
    leadership_modifier_changed: bool = Field(
        default=False,
        description="Whether the leadership modifier changed as a result of this assignment",
    )
    previous_leadership: int = Field(
        default=0,
        description="Previous leadership modifier value (0 if no previous representative)",
    )
    new_leadership: int = Field(
        default=0,
        description="New leadership modifier value after assignment/unassignment",
    )
