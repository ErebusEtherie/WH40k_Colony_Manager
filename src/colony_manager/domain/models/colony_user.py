"""Domain model for colony user membership.

ColonyUser represents the many-to-many relationship between users and colonies,
with role-based access control for collaborative colony management.
"""

from datetime import datetime, timedelta, timezone
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class ColonyUserRole(StrEnum):
    """Role enumeration for colony membership.

    Roles determine what actions a user can perform within a colony context.
    """

    OWNER = "owner"  # Full control, can manage members
    EDITOR = "editor"  # Can edit colony data
    VIEWER = "viewer"  # Read-only access


class ColonyUser(BaseModel):
    """Domain model for colony-user membership.

    This model represents the relationship between a user and a colony,
    including their role and permissions within that colony context.

    Attributes:
        id: Database ID (None if not yet persisted).
        colony_id: ID of the colony.
        user_id: ID of the user.
        role: User's role within this colony (owner, editor, viewer).
        joined_at: Timestamp when the user joined the colony (Warsaw timezone).
        invited_by: User ID who invited this user (None if self-joined or system-created).
    """

    id: int | None = None
    colony_id: int
    user_id: int
    role: ColonyUserRole = ColonyUserRole.VIEWER
    joined_at: datetime = Field(default_factory=lambda: datetime.now(timezone(timedelta(hours=1))))
    invited_by: int | None = None

    @field_validator("joined_at")
    @classmethod
    def _validate_joined_at(cls, value: datetime) -> datetime:
        """Ensure joined_at is timezone-aware (defaults to Warsaw/UTC+1 if naive)."""
        # Ensure timezone-aware, convert to Warsaw (UTC+1) if naive
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone(timedelta(hours=1)))
        return value
