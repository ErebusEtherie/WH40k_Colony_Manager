"""Domain model for modifiers."""

from datetime import date

from pydantic import BaseModel, Field

from colony_manager.domain.enums import ModifierCategory, ModifierSourceType, ModifierStat


class Modifier(BaseModel):
    """
    A modifier applied to a colony stat.

    Modifiers can be temporary (with expiry) or permanent. When a modifier
    expires, it should be filtered out during state calculation.

    Attributes:
        id: Database ID (None if not yet persisted).
        colony_id: ID of the colony this modifier belongs to.
        modifier_source_type: Source of the modifier (e.g., infrastructure, GM custom).
        modifier_category: Category of modifier (permanent, conditional, custom).
        modifier_stat: Which stat this modifier affects.
        modifier_value: Numeric value of the modifier (positive or negative).
        modifier_description: Human-readable description of the modifier source.
        is_active: Whether the modifier is currently active (can be manually disabled).
        expires_at: Optional date when this modifier expires (None = permanent).
        source_entity_id: Optional ID of the source entity
            (infrastructure or support upgrade instance).
    """

    id: int | None = None
    colony_id: int
    modifier_source_type: ModifierSourceType
    modifier_category: ModifierCategory
    modifier_stat: ModifierStat
    modifier_value: int
    modifier_description: str = Field(validation_alias="description", default="")
    is_active: bool = True
    expires_at: date | None = None
    source_entity_id: int | None = None

    model_config = {"populate_by_name": True}

    def is_expired(self, as_of: date | None = None) -> bool:
        """
        Check if this modifier has expired.

        Args:
            as_of: Date to check against. Defaults to today if not provided.

        Returns:
            True if the modifier has an expiry date and that date is in the past.
        """
        if self.expires_at is None:
            return False
        check_date = as_of or date.today()
        return check_date > self.expires_at


__all__ = ["Modifier", "ModifierCategory", "ModifierSourceType", "ModifierStat"]
