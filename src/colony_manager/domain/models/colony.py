"""Domain model for colonies."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator

from colony_manager.domain.enums import ColonyType, DynastyOutcome, ResourceType
from colony_manager.domain.models.infrastructure import Infrastructure
from colony_manager.domain.models.modifier import Modifier
from colony_manager.domain.models.support_upgrade import SupportUpgrade


class Colony(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    id: int | None = None
    name: str
    founder_name: str
    patron_name: str | None = None
    colony_type: ColonyType
    age_days: int = Field(ge=0)
    age_last_updated: date
    base_complacency: int
    base_order: int
    base_productivity: int
    base_piety: int
    base_size: int
    representative_id: int | None = None
    # Current active event (GM-defined, optional)
    current_event: str | None = None
    # Infrastructure and upgrades owned by this colony
    infrastructure: list[Infrastructure] = Field(default_factory=list)
    support_upgrades: list[SupportUpgrade] = Field(default_factory=list)
    # For Dynasty Member representatives: chosen nepotism outcome
    dynasty_outcome: DynastyOutcome | None = None
    # Lock flags - prevent stat increases until resolved (per Rogue Trader rules)
    # Complacency = 0: Order and Productivity cannot increase
    # Piety = 0: Order and Complacency cannot increase
    complacency_locked: bool = False
    order_locked: bool = False
    productivity_locked: bool = False
    # Planetary resources the colony is exploiting
    planetary_resources: list[ResourceType] = Field(default_factory=list)
    modifiers: list[Modifier] = Field(default_factory=list)

    @field_validator("age_days")
    @classmethod
    def _validate_age_days(cls, value: int) -> int:
        if value < 0:
            raise ValueError("age_days cannot be negative")
        return value

    @field_validator(
        "base_complacency", "base_order", "base_productivity", "base_piety", "base_size"
    )
    @classmethod
    def _validate_base_stats(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Base stats cannot be negative")
        return value

    def get_cycle_info(self, event_interval: int, development_interval: int) -> dict[str, int]:
        """Calculate days since/until next rolls.

        Args:
            event_interval: Global event roll interval in days (typically 60)
            development_interval: Global development roll interval in days (typically 90)

        Returns:
            Dict with keys: days_since_event_roll, days_until_event_roll,
                           days_since_development_roll, days_until_development_roll

        Note:
            When a roll is exactly due (age_days is a multiple of the interval and age > 0),
            days_since is 0 and days_until is also 0 (not the full interval).

            At colony creation (age_days = 0), days_since is 0 but days_until is the full
            interval (first rolls happen at day 60/90, not day 0).
        """
        days_since_event = self.age_days % event_interval
        # At age 0, first roll is interval days away; at other boundaries, roll is due now
        days_until_event = (
            0
            if (days_since_event == 0 and self.age_days > 0)
            else event_interval - days_since_event
        )
        days_since_dev = self.age_days % development_interval
        days_until_dev = (
            0
            if (days_since_dev == 0 and self.age_days > 0)
            else development_interval - days_since_dev
        )
        return {
            "days_since_event_roll": days_since_event,
            "days_until_event_roll": days_until_event,
            "days_since_development_roll": days_since_dev,
            "days_until_development_roll": days_until_dev,
        }
