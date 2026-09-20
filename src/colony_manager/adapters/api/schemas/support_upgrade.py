"""Support Upgrade API schemas."""

from pydantic import BaseModel, Field

from colony_manager.domain.enums import ModifierStat, SupportUpgradeType


class SupportUpgradeCreate(BaseModel):
    """Schema for creating new support upgrade."""

    name: str = Field(
        ..., min_length=1, max_length=255, description="User-defined name for this upgrade instance"
    )
    upgrade_type: SupportUpgradeType
    custom_stat_choice: ModifierStat | None = None
    custom_product: str | None = None
    affiliated_group: str | None = None
    notes: str = Field(default="", max_length=1000, description="Optional notes about this upgrade")


class SupportUpgradeUpdate(BaseModel):
    """Schema for updating support upgrade (partial update)."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    custom_stat_choice: ModifierStat | None = None
    custom_product: str | None = None
    affiliated_group: str | None = None
    notes: str | None = Field(default=None, max_length=1000)


class SupportUpgradeResponse(BaseModel):
    """Full support upgrade response."""

    id: int
    colony_id: int
    name: str
    upgrade_type: SupportUpgradeType
    custom_stat_choice: ModifierStat | None
    custom_product: str | None
    affiliated_group: str | None
    notes: str
    has_stat_effect: bool


class SupportUpgradeListItem(BaseModel):
    """Summary information for support upgrade list."""

    id: int | None
    name: str
    upgrade_type: SupportUpgradeType
    custom_stat_choice: ModifierStat | None
    custom_product: str | None
    affiliated_group: str | None
    has_stat_effect: bool


class SupportUpgradeValidationResponse(BaseModel):
    """Response for support upgrade validation."""

    valid: bool
    modifiers_preview: list[dict[str, object]]
    colony_type_bonus_applied: bool
    bonus_description: str | None
