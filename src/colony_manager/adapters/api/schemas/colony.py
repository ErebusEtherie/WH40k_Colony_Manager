"""Colony API schemas."""

from datetime import date

from pydantic import BaseModel, Field

from colony_manager.domain.enums import ColonyType, DynastyOutcome, ResourceType


class ColonyRollStatus(BaseModel):
    """Response schema for colony roll status."""

    event_roll_due: bool
    development_roll_due: bool
    days_since_event_roll: int
    days_until_event_roll: int
    days_since_development_roll: int
    days_until_development_roll: int
    event_interval_days: int
    development_interval_days: int


class ColonyStateStat(BaseModel):
    """Nested stat information with base, current, and lore state."""

    base: int
    current: int
    lore_state: str


class ColonyStateNested(BaseModel):
    """Nested colony state structure."""

    size: ColonyStateStat
    complacency: ColonyStateStat
    order: ColonyStateStat
    productivity: ColonyStateStat
    piety: ColonyStateStat
    leadership_modifier: int
    profit_factor: int
    lore_state: dict[str, str]


class ColonyCycleInfo(BaseModel):
    """Computed information about upcoming rolls."""

    days_since_event_roll: int
    days_until_event_roll: int
    days_since_development_roll: int
    days_until_development_roll: int


class ColonyCreate(BaseModel):
    """Schema for creating a new colony."""

    name: str = Field(..., min_length=1, max_length=100)
    founder_name: str = Field(..., min_length=1, max_length=100)
    patron_name: str | None = Field(default=None, min_length=1, max_length=100)
    colony_type: ColonyType
    # Optional starting settlement size. When omitted the colony is founded at the
    # colony type's base size (usually 1); supplying a larger value allows founding
    # advanced-stage colonies (pre-grown settlements). This is a deliberate override
    # of the type's base_stats.size, so defaults and auth/audit semantics are explicit.
    base_size: int | None = Field(
        None,
        ge=0,
        le=10,
        description="Initial settlement size; defaults to the colony type's base size.",
    )


class ColonyUpdate(BaseModel):
    """Schema for updating a colony (partial update)."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    founder_name: str | None = Field(default=None, min_length=1, max_length=100)
    patron_name: str | None = Field(default=None, min_length=1, max_length=100)
    age_days: int | None = Field(default=None, ge=0)
    current_event: str | None = None


class ColonyAgeAdvance(BaseModel):
    """Schema for advancing colony age.

    Supports three operations:
    - 'add': Add days to current age (positive or negative)
    - 'set': Set age to specific value
    - 'subtract': Subtract days from current age

    Use 'add' for both increasing and decreasing age.
    """

    add: int | None = Field(default=None, description="Days to add (can be negative to decrease)")
    set: int | None = Field(default=None, ge=0, description="Set age to specific value")
    subtract: int | None = Field(
        default=None, ge=0, description="Days to subtract from current age"
    )

    def get_days_delta(self, current_age: int) -> int:
        """Calculate the new age based on the operation.

        Args:
            current_age: Current colony age in days

        Returns:
            New age in days

        Raises:
            ValueError: If no valid operation is provided or result would be negative
        """
        if self.add is not None:
            new_age = current_age + self.add
        elif self.set is not None:
            new_age = self.set
        elif self.subtract is not None:
            new_age = current_age - self.subtract
        else:
            raise ValueError("One of 'add', 'set', or 'subtract' must be provided")

        if new_age < 0:
            raise ValueError(f"Age cannot be negative. Result would be {new_age} days.")

        return new_age


class ColonyListItem(BaseModel):
    """Summary information for colony list."""

    id: int | None
    name: str
    founder_name: str
    patron_name: str | None
    colony_type: ColonyType
    age_days: int
    current_size: int
    current_complacency: int
    current_order: int
    current_productivity: int
    current_piety: int
    profit_factor: int


class ColonyResponse(BaseModel):
    """Full colony response with computed state."""

    id: int | None
    name: str
    founder_name: str
    patron_name: str | None
    colony_type: ColonyType
    age_days: int
    age_last_updated: date
    current_event: str | None
    base_complacency: int
    base_order: int
    base_productivity: int
    base_piety: int
    base_size: int
    representative_id: int | None
    dynasty_outcome: DynastyOutcome | None
    complacency_locked: bool
    order_locked: bool
    productivity_locked: bool
    planetary_resources: list[ResourceType]
    state: ColonyStateNested
