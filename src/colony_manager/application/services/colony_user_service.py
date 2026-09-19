"""Application service for colony user membership management.

This service orchestrates colony-user membership operations, including adding
members, updating roles, and integration with the audit logging system.
"""

from colony_manager.domain.errors import NotFoundError
from colony_manager.domain.models.colony_user import ColonyUser, ColonyUserRole
from colony_manager.domain.ports.audit_log_repository import AuditLogRepository
from colony_manager.domain.ports.colony_user_repository import ColonyUserRepository
from colony_manager.domain.ports.user_repository import UserRepository


class ColonyUserService:
    """Service for managing colony-user memberships.

    This service handles membership CRUD operations and ensures proper audit logging.
    """

    def __init__(
        self,
        membership_repository: ColonyUserRepository,
        audit_log_repository: AuditLogRepository | None = None,
        user_repository: UserRepository | None = None,
    ) -> None:
        self._membership_repository = membership_repository
        self._audit_log_repository = audit_log_repository
        self._user_repository = user_repository

    def _validate_user_exists(self, user_id: int) -> None:
        """Validate that a user exists in the system.

        Args:
            user_id: ID of the user to validate.

        Raises:
            NotFoundError: If user does not exist.
        """
        if not self._user_repository.get_by_id(user_id):
            raise NotFoundError(f"User {user_id} not found")

    def add_member(
        self,
        colony_id: int,
        user_id: int,
        role: ColonyUserRole,
        invited_by: int | None = None,
    ) -> ColonyUser:
        """Add a user to a colony.

        Args:
            colony_id: ID of the colony.
            user_id: ID of the user to add.
            role: Role to assign to the user.
            invited_by: User ID who invited this user (optional).

        Returns:
            Created membership.

        Raises:
            NotFoundError: If user does not exist.
            ValueError: If user is already a member.
        """
        # Validate user exists before creating membership
        if self._user_repository:
            self._validate_user_exists(user_id)

        membership = ColonyUser(
            colony_id=colony_id,
            user_id=user_id,
            role=role,
            invited_by=invited_by,
        )

        created_membership = self._membership_repository.create(membership)

        # Log the creation
        if self._audit_log_repository:
            from colony_manager.domain.models.audit_log import AuditLog, AuditLogAction

            if created_membership.id is None:
                raise RuntimeError("Created membership has no ID")

            audit_log = AuditLog(
                entity_type="colony_membership",
                entity_id=created_membership.id,
                action=AuditLogAction.CREATE,
                field="role",
                new_value=role.value,
                changed_by=invited_by or user_id,
                colony_id=colony_id,
            )
            self._audit_log_repository.create(audit_log)

        return created_membership

    def get_membership(self, membership_id: int) -> ColonyUser | None:
        """Get a membership by ID."""
        return self._membership_repository.get_by_id(membership_id)

    def get_membership_by_colony_and_user(self, colony_id: int, user_id: int) -> ColonyUser | None:
        """Get a user's membership in a specific colony."""
        return self._membership_repository.get_by_colony_and_user(colony_id, user_id)

    def get_members_by_colony(self, colony_id: int) -> list[ColonyUser]:
        """Get all members of a colony."""
        return self._membership_repository.get_by_colony(colony_id)

    def get_colonies_by_user(self, user_id: int) -> list[ColonyUser]:
        """Get all colonies a user is a member of."""
        return self._membership_repository.get_by_user(user_id)

    def update_member_role(
        self,
        membership_id: int,
        new_role: ColonyUserRole,
        changed_by: int,
    ) -> ColonyUser:
        """Update a member's role.

        Args:
            membership_id: ID of the membership.
            new_role: New role to assign.
            changed_by: User ID making the change.

        Returns:
            Updated membership.

        Raises:
            NotFoundError: If membership not found.
        """
        membership = self._membership_repository.get_by_id(membership_id)
        if membership is None:
            raise NotFoundError(f"Membership with ID {membership_id} not found")

        old_role = membership.role
        membership.role = new_role

        updated_membership = self._membership_repository.update(membership)

        # Log the update
        if self._audit_log_repository:
            from colony_manager.domain.models.audit_log import AuditLog, AuditLogAction

            audit_log = AuditLog(
                entity_type="colony_membership",
                entity_id=membership_id,
                action=AuditLogAction.UPDATE,
                field="role",
                old_value=old_role.value,
                new_value=new_role.value,
                changed_by=changed_by,
                colony_id=membership.colony_id,
            )
            self._audit_log_repository.create(audit_log)

        return updated_membership

    def remove_member(self, membership_id: int, changed_by: int | None = None) -> None:
        """Remove a user from a colony.

        Args:
            membership_id: ID of the membership to remove.
            changed_by: User ID making the change (optional).

        Raises:
            NotFoundError: If membership not found.
        """
        membership = self._membership_repository.get_by_id(membership_id)
        if membership is None:
            raise NotFoundError(f"Membership with ID {membership_id} not found")

        colony_id = membership.colony_id
        self._membership_repository.delete(membership_id)

        # Log the deletion
        if self._audit_log_repository and changed_by:
            from colony_manager.domain.models.audit_log import AuditLog, AuditLogAction

            audit_log = AuditLog(
                entity_type="colony_membership",
                entity_id=membership_id,
                action=AuditLogAction.DELETE,
                changed_by=changed_by,
                colony_id=colony_id,
            )
            self._audit_log_repository.create(audit_log)

    def transfer_ownership(
        self,
        colony_id: int,
        current_owner_id: int,
        new_owner_id: int,
        demote_current: bool = True,
        changed_by: int | None = None,
    ) -> tuple[ColonyUser, ColonyUser | None]:
        """Transfer colony ownership from one user to another.

        Args:
            colony_id: ID of the colony.
            current_owner_id: ID of the current owner.
            new_owner_id: ID of the new owner.
            demote_current: Whether to demote current owner to editor (default True).
            changed_by: User ID making the change (optional, for audit log).

        Returns:
            Tuple of (new_owner_membership, current_owner_membership_or_none).

        Raises:
            NotFoundError: If either user does not exist or is not a member of the colony.
            ValueError: If new_owner_id is the same as current_owner_id.
        """
        if current_owner_id == new_owner_id:
            raise ValueError("Cannot transfer ownership to the same user")

        # Validate both users exist before making any changes
        if self._user_repository:
            self._validate_user_exists(current_owner_id)
            self._validate_user_exists(new_owner_id)

        # Get current owner's membership
        current_owner_membership = self._membership_repository.get_by_colony_and_user(
            colony_id, current_owner_id
        )
        if current_owner_membership is None:
            raise NotFoundError(
                f"Current owner (user {current_owner_id}) is not a member of colony {colony_id}"
            )

        # Get or create new owner's membership
        new_owner_membership = self._membership_repository.get_by_colony_and_user(
            colony_id, new_owner_id
        )

        # Update current owner's role to editor if demoting
        old_owner_role = current_owner_membership.role
        if demote_current:
            current_owner_membership.role = ColonyUserRole.EDITOR
            self._membership_repository.update(current_owner_membership)

        # Update or create new owner's membership
        old_new_owner_role = new_owner_membership.role if new_owner_membership else None
        if new_owner_membership is None:
            new_owner_membership = self._create_owner_membership(
                colony_id, new_owner_id, changed_by
            )
        else:
            new_owner_membership.role = ColonyUserRole.OWNER
            new_owner_membership = self._membership_repository.update(new_owner_membership)

        # Log the ownership transfer
        self._log_ownership_transfer(
            colony_id=colony_id,
            current_owner_membership=current_owner_membership,
            new_owner_membership=new_owner_membership,
            old_owner_role=old_owner_role,
            old_new_owner_role=old_new_owner_role,
            changed_by=changed_by,
        )

        return new_owner_membership, current_owner_membership if demote_current else None

    def _create_owner_membership(
        self,
        colony_id: int,
        user_id: int,
        invited_by: int | None,
    ) -> ColonyUser:
        """Create a new owner membership for a user."""
        membership = ColonyUser(
            colony_id=colony_id,
            user_id=user_id,
            role=ColonyUserRole.OWNER,
            invited_by=invited_by,
        )
        return self._membership_repository.create(membership)

    def _log_ownership_transfer(
        self,
        colony_id: int,
        current_owner_membership: ColonyUser,
        new_owner_membership: ColonyUser,
        old_owner_role: ColonyUserRole,
        old_new_owner_role: ColonyUserRole | None,
        changed_by: int | None,
    ) -> None:
        """Log the ownership transfer to the audit log.

        Args:
            colony_id: ID of the colony.
            current_owner_membership: Membership of the previous owner.
            new_owner_membership: Membership of the new owner.
            old_owner_role: Previous role of the current owner.
            old_new_owner_role: Previous role of the new owner (None if new member).
            changed_by: User ID making the change.
        """
        if not self._audit_log_repository or not changed_by:
            return

        from colony_manager.domain.models.audit_log import AuditLog, AuditLogAction

        # Log current owner role change
        if current_owner_membership.id is not None:
            audit_log = AuditLog(
                entity_type="colony_membership",
                entity_id=current_owner_membership.id,
                action=AuditLogAction.UPDATE,
                field="role",
                old_value=old_owner_role.value,
                new_value=current_owner_membership.role.value,
                changed_by=changed_by,
                colony_id=colony_id,
            )
            self._audit_log_repository.create(audit_log)

        # Log new owner role change
        if new_owner_membership.id is not None:
            audit_log = AuditLog(
                entity_type="colony_membership",
                entity_id=new_owner_membership.id,
                action=AuditLogAction.UPDATE,
                field="role",
                old_value=old_new_owner_role.value if old_new_owner_role else "none",
                new_value=ColonyUserRole.OWNER.value,
                changed_by=changed_by,
                colony_id=colony_id,
            )
            self._audit_log_repository.create(audit_log)
