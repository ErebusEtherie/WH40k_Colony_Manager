"""Infrastructure API schemas."""

from pydantic import BaseModel, Field

from colony_manager.domain.enums import InfrastructureState, InfrastructureType


class InfrastructureCreate(BaseModel):
    """Schema for creating new infrastructure."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="User-defined name for this infrastructure instance",
    )
    infrastructure_type: InfrastructureType
    state: InfrastructureState = InfrastructureState.PLANNED
    notes: str = Field(
        default="", max_length=1000, description="Optional notes about this infrastructure"
    )


class InfrastructureUpdate(BaseModel):
    """Schema for updating infrastructure (partial update)."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    state: InfrastructureState | None = None
    notes: str | None = Field(default=None, max_length=1000)


class InfrastructureResponse(BaseModel):
    """Full infrastructure response."""

    id: int
    colony_id: int
    name: str
    infrastructure_type: InfrastructureType
    state: InfrastructureState
    notes: str
    has_effect: bool
    is_working: bool
    is_not_working: bool


class InfrastructureListItem(BaseModel):
    """Summary information for infrastructure list."""

    id: int | None
    name: str
    infrastructure_type: InfrastructureType
    state: InfrastructureState
    has_effect: bool
    is_working: bool
    is_not_working: bool


class InfrastructureValidationResponse(BaseModel):
    """Response for infrastructure state transition validation."""

    valid: bool
    current_state: InfrastructureState
    requested_state: InfrastructureState
    modifiers_preview: list[dict[str, object]]
    would_apply_penalty: bool
    penalty_description: str | None
