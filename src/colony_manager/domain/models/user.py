"""Domain model for user authentication."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class UserRole(StrEnum):
    """User role enumeration for authorization.

    System roles form a global hierarchy (``viewer`` < ``colony_manager`` <
    ``admin``), with higher levels subsuming lower ones for authorization
    checks. This is a distinct value space from the per-colony colony role
    (``ColonyUserRole``) — the two answer different questions and must not be
    conflated (see 02-domain-modeling.md).

    The ordering itself lives here in domain (``level`` / ``meets_or_exceeds``)
    so the hierarchy is not re-derived as a scattered dict at each adapter
    call site — a higher role can always do everything a lower role can, never
    less.
    """

    ADMIN = "admin"
    COLONY_MANAGER = "colony_manager"
    VIEWER = "viewer"

    @property
    def level(self) -> int:
        """Relative rank in the system-role hierarchy.

        Returns:
            An integer rank where ``viewer`` < ``colony_manager`` < ``admin``.
        """
        return SYSTEM_ROLE_ORDER.index(self)

    def meets_or_exceeds(self, other: "UserRole") -> bool:
        """Return True if this role is at least as privileged as ``other``.

        Args:
            other: The role to compare against.

        Returns:
            True if this role's level is >= ``other``'s level.
        """
        return self.level >= UserRole(other).level


# Ordering of the global system-role hierarchy (higher index = more privilege).
# Single source of truth for the ordering; ``UserRole.level`` and
# ``meets_or_exceeds`` reference this so the rule lives in domain.
SYSTEM_ROLE_ORDER: tuple[UserRole, ...] = (
    UserRole.VIEWER,
    UserRole.COLONY_MANAGER,
    UserRole.ADMIN,
)


class User(BaseModel):
    """User domain model for authentication and authorization.

    This model represents a user account in the system. Passwords should
    never be stored in plain text - always use hashed passwords.
    """

    id: int | None = None
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=5, max_length=100)
    password_hash: str = Field(min_length=1)  # Never store plain text passwords
    role: UserRole = UserRole.VIEWER
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # Note: Colony membership is managed via ColonyUser model, not this field.
    # The managed_colony_id field was removed in favor of proper many-to-many
    # relationships through the ColonyUser model with role-based access control.

    model_config = {"use_enum_values": False}
