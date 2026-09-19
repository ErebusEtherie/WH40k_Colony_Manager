"""Domain model for audit logs.

Audit logs track all changes to colony state for version history. They are
auto-populated via the service layer - not manually created.
"""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class AuditLogAction(StrEnum):
    """Action enumeration for audit log entries."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class AuditLog(BaseModel):
    """Domain model for audit log entries.

    Audit logs track all changes to colony state for version history and
    accountability. They are automatically created by the service layer
    whenever a colony or related entity is modified.

    Attributes:
        id: Database ID (None if not yet persisted).
        entity_type: Type of entity being changed (e.g., "colony", "infrastructure").
        entity_id: ID of the entity being changed.
        action: Action performed (create, update, delete).
        field: Specific field that was changed (None for create/delete).
        old_value: Previous value as JSON-serialized string (None for create).
        new_value: New value as JSON-serialized string (None for delete).
        changed_by: User ID of the user who made the change.
        changed_at: Timestamp when the change was made (UTC).
        colony_id: ID of the colony this change relates to.
    """

    id: int | None = None
    entity_type: str = Field(min_length=1, max_length=50)
    entity_id: int
    action: AuditLogAction
    field: str | None = Field(default=None, max_length=100)
    old_value: str | None = Field(default=None, max_length=10000)
    new_value: str | None = Field(default=None, max_length=10000)
    changed_by: int
    changed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    colony_id: int | None = None  # Optional for non-colony entities like users

    @field_validator("changed_at")
    @classmethod
    def _validate_changed_at(cls, value: datetime | None) -> datetime:
        """Ensure changed_at is never None and is timezone-aware (UTC)."""
        if value is None:
            return datetime.now(UTC)
        # Ensure UTC timezone
        if value.tzinfo is None:
            # Assume naive datetime is UTC
            return value.replace(tzinfo=UTC)
        return value
