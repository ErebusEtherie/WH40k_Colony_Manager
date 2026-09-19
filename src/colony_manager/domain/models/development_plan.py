"""Domain model for development plans.
Development plans track long-term colony development goals. They are purely
informational - no automatic stat effects. Plans follow a workflow from planning
through installation as actual Infrastructure or Support Upgrades.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class DevelopmentPlanStatus(StrEnum):
    """Status enumeration for development plans.

    Workflow: PLANNED <-> IN_PROGRESS <-> ACQUIRED -> DELIVERED
    - Any status can return to PLANNED
    - PLANNED can only go to IN_PROGRESS
    - IN_PROGRESS can go to PLANNED or ACQUIRED
    - ACQUIRED can go to IN_PROGRESS, PLANNED, or DELIVERED
    - DELIVERED can go to ACQUIRED or PLANNED
    """

    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    ACQUIRED = "acquired"
    DELIVERED = "delivered"


class DevelopmentPlan(BaseModel):
    """Domain model for colony development plans.

    Development plans track long-term colony development goals such as
    acquiring specific infrastructure or support upgrades. They are purely
    informational and do not automatically affect stats. When a plan reaches
    DELIVERED status, it can be installed to create actual Infrastructure
    or Support Upgrades.

    Attributes:
        id: Database ID (None if not yet persisted).
        colony_id: ID of the colony this plan belongs to.
        upgrade_type: Type of upgrade being pursued ("infrastructure" or "support_upgrade").
        target_type: The specific type enum value (e.g., "transport", "arbites_precinct").
        target_name: Custom player-defined name for the item (e.g., "North Spaceport").
        priority: Priority level from 1 (lowest) to 5 (highest). Default: 1.
        description: Detailed description of the plan and its goals.
        notes: Optional player notes for internal tracking.
        order: Sort order for manual list arrangement. Default: 0.
        status: Current status of the development plan.
        created_by: User ID of the user who created this plan.
        created_at: Timestamp when the plan was created.
    """

    id: int | None = None
    colony_id: int
    upgrade_type: str = Field(pattern=r"^(infrastructure|support_upgrade)$")
    target_type: str = Field(min_length=1, max_length=100)
    target_name: str = Field(min_length=1, max_length=200)
    priority: int = Field(ge=1, le=5, default=1)
    description: str = Field(min_length=1, max_length=2000)
    notes: str = Field(default="", max_length=2000)
    order: int = Field(default=0)
    status: DevelopmentPlanStatus = DevelopmentPlanStatus.PLANNED
    created_by: int
    created_at: datetime | None = None
