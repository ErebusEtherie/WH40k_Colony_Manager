"""Application service for representative use cases."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from colony_manager.domain.errors import NotFoundError
from colony_manager.domain.models.audit_log import AuditLog, AuditLogAction
from colony_manager.domain.models.representative import Representative, RepresentativeStats
from colony_manager.domain.ports.audit_log_repository import AuditLogRepository
from colony_manager.domain.ports.colony_repository import ColonyRepository
from colony_manager.domain.ports.representative_repository import RepresentativeRepository

logger = logging.getLogger(__name__)


@dataclass
class AssignmentResult:
    """Result of representative assignment/unassignment with change tracking.

    Attributes:
        representative: The updated representative object.
        previous_representative_id: ID of previously assigned representative (None if none).
        new_representative_id: ID of newly assigned representative (None for unassign).
        previous_leadership: Leadership modifier before the change.
        new_leadership: Leadership modifier after the change.
        leadership_modifier_changed: Whether the leadership modifier changed.
    """

    representative: Representative
    previous_representative_id: int | None
    new_representative_id: int | None
    previous_leadership: int
    new_leadership: int
    leadership_modifier_changed: bool


class RepresentativeService:
    """Create, update, and manage representatives and their colony assignment.

    This service orchestrates representative operations including creation,
    colony assignment, and unassignment. It coordinates between the colony
    and representative repositories to maintain bidirectional consistency.
    """

    def __init__(
        self,
        colony_repository: ColonyRepository,
        representative_repository: RepresentativeRepository,
        audit_log_repository: AuditLogRepository | None = None,
    ) -> None:
        """Initialize the service with repository dependencies.

        Args:
            colony_repository: Repository for colony persistence.
            representative_repository: Repository for representative persistence.
            audit_log_repository: Optional repository for audit logging.
        """
        self._colony_repository = colony_repository
        self._representative_repository = representative_repository
        self._audit_log_repository = audit_log_repository

    @staticmethod
    def _get_leadership_modifier(stats: RepresentativeStats) -> int:
        """Calculate leadership modifier from stats.

        Leadership modifier is the highest of Int/Per/Fel bonuses.

        Args:
            stats: The representative's stats object.

        Returns:
            The leadership modifier value (highest of int//10, per//10, fel//10).
        """
        int_bonus = stats.int_ // 10
        per_bonus = stats.per // 10
        fel_bonus = stats.fel // 10
        return max(int_bonus, per_bonus, fel_bonus)

    def _log_audit(
        self,
        colony_id: int,
        entity_type: str,
        entity_id: int,
        action: str,
        field: str | None,
        old_value: str | None,
        new_value: str | None,
        changed_by: int,
    ) -> None:
        """Create an audit log entry if audit logging is enabled."""
        if self._audit_log_repository is None:
            return

        try:
            audit_log = AuditLog(
                entity_type=entity_type,
                entity_id=entity_id,
                action=AuditLogAction(action),
                field=field,
                old_value=old_value,
                new_value=new_value,
                changed_by=changed_by,
                colony_id=colony_id or 0,
            )
            self._audit_log_repository.create(audit_log)
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to create audit log: %s", e)

    def create_representative(
        self, representative: Representative, changed_by: int | None = None
    ) -> Representative:
        """Create a new representative.

        Args:
            representative: The representative domain object to create.
            changed_by: Optional user ID who made the change (for audit logging).

        Returns:
            The created representative with ID assigned.
        """
        result = self._representative_repository.create(representative)

        # Log audit entry
        if (
            self._audit_log_repository is not None
            and changed_by is not None
            and result.id is not None
        ):
            self._log_audit(
                colony_id=representative.assigned_to_colony_id or 0,
                entity_type="representative",
                entity_id=result.id,
                action=AuditLogAction.CREATE,
                field=None,
                old_value=None,
                new_value=result.name,
                changed_by=changed_by,
            )

        return result

    def get_representative_by_id(self, representative_id: int) -> Representative:
        """Get a representative by ID.

        Args:
            representative_id: ID of the representative.

        Returns:
            The representative.

        Raises:
            NotFoundError: If representative does not exist.
        """
        representative = self._representative_repository.get(representative_id)
        if representative is None:
            raise NotFoundError(f"Representative {representative_id} not found")
        return representative

    def list_representatives(self) -> list[Representative]:
        """List all representatives.

        Returns:
            List of all representatives in the system.
        """
        return self._representative_repository.list()

    def assign_to_colony(
        self, colony_id: int, representative_id: int, changed_by: int | None = None
    ) -> AssignmentResult:
        """Assign a representative to a colony.

        Updates both the colony's representative_id and the representative's
        assigned_to_colony_id to maintain bidirectional consistency.

        Args:
            colony_id: ID of the colony to assign to.
            representative_id: ID of the representative to assign.
            changed_by: Optional user ID who made the change (for audit logging).

        Returns:
            AssignmentResult with the updated representative and change tracking info.

        Raises:
            NotFoundError: If colony or representative does not exist.
        """
        colony = self._colony_repository.get(colony_id)
        if colony is None:
            raise NotFoundError(f"Colony {colony_id} not found")
        representative = self._representative_repository.get(representative_id)
        if representative is None:
            raise NotFoundError(f"Representative {representative_id} not found")

        # Get previous representative info for change tracking
        old_colony_id = representative.assigned_to_colony_id
        previous_representative_id = colony.representative_id
        previous_leadership = 0
        if previous_representative_id is not None:
            previous_rep = self._representative_repository.get(previous_representative_id)
            if previous_rep is None:
                logger.warning(
                    f"Previous representative {previous_representative_id} not found "
                    f"during assignment to colony {colony_id}"
                )
            else:
                previous_leadership = self._get_leadership_modifier(previous_rep.stats)

        # Calculate new leadership modifier
        new_leadership = self._get_leadership_modifier(representative.stats)
        leadership_modifier_changed = previous_leadership != new_leadership

        # Update colony and representative
        colony.representative_id = representative_id
        self._colony_repository.update(colony)
        representative.assigned_to_colony_id = colony_id
        result = self._representative_repository.update(representative)

        # Log audit entry
        if self._audit_log_repository is not None and changed_by is not None:
            self._log_audit(
                colony_id=colony_id,
                entity_type="representative",
                entity_id=representative_id,
                action=AuditLogAction.UPDATE,
                field="assigned_to_colony_id",
                old_value=str(old_colony_id) if old_colony_id else None,
                new_value=str(colony_id),
                changed_by=changed_by,
            )

        return AssignmentResult(
            representative=result,
            previous_representative_id=previous_representative_id,
            new_representative_id=representative_id,
            previous_leadership=previous_leadership,
            new_leadership=new_leadership,
            leadership_modifier_changed=leadership_modifier_changed,
        )

    def unassign_from_colony(
        self, representative_id: int, changed_by: int | None = None
    ) -> AssignmentResult:
        """Unassign a representative from their colony.

        Clears the representative's assigned_to_colony_id and updates the
        colony's representative_id to None.

        Args:
            representative_id: ID of the representative to unassign.
            changed_by: Optional user ID who made the change (for audit logging).

        Returns:
            AssignmentResult with the updated representative and change tracking info.

        Raises:
            NotFoundError: If representative does not exist.
        """
        representative = self._representative_repository.get(representative_id)
        if representative is None:
            raise NotFoundError(f"Representative {representative_id} not found")

        old_colony_id = representative.assigned_to_colony_id

        # Get previous leadership modifier for change tracking
        previous_leadership = self._get_leadership_modifier(representative.stats)
        previous_representative_id = representative_id
        new_leadership = 0
        leadership_modifier_changed = previous_leadership != new_leadership

        # Update colony if this rep was assigned
        if representative.assigned_to_colony_id is not None:
            colony = self._colony_repository.get(representative.assigned_to_colony_id)
            if colony is not None:
                colony.representative_id = None
                self._colony_repository.update(colony)

        representative.assigned_to_colony_id = None
        result = self._representative_repository.update(representative)

        # Log audit entry
        if (
            self._audit_log_repository is not None
            and changed_by is not None
            and old_colony_id is not None
        ):
            self._log_audit(
                colony_id=old_colony_id,
                entity_type="representative",
                entity_id=representative_id,
                action=AuditLogAction.UPDATE,
                field="assigned_to_colony_id",
                old_value=str(old_colony_id),
                new_value=None,
                changed_by=changed_by,
            )

        return AssignmentResult(
            representative=result,
            previous_representative_id=previous_representative_id,
            new_representative_id=None,
            previous_leadership=previous_leadership,
            new_leadership=new_leadership,
            leadership_modifier_changed=leadership_modifier_changed,
        )
