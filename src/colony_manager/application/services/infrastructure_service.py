"""Infrastructure service for managing colony infrastructure."""

import logging
from collections.abc import Mapping
from typing import Any

from colony_manager.domain.enums import InfrastructureState
from colony_manager.domain.errors import NotFoundError
from colony_manager.domain.models.audit_log import AuditLog, AuditLogAction
from colony_manager.domain.models.infrastructure import Infrastructure
from colony_manager.domain.ports.audit_log_repository import AuditLogRepository
from colony_manager.domain.ports.colony_repository import ColonyRepository
from colony_manager.domain.ports.infrastructure_repository import InfrastructureRepository
from colony_manager.domain.rules.infrastructure_rules import get_missing_infrastructure_penalty

logger = logging.getLogger(__name__)


class InfrastructureService:
    """Service layer for infrastructure management."""

    def __init__(
        self,
        repository: InfrastructureRepository,
        colony_repository: ColonyRepository,
        audit_log_repository: AuditLogRepository | None = None,
    ) -> None:
        self._repository = repository
        self._colony_repository = colony_repository
        self._audit_log_repository = audit_log_repository

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
                colony_id=colony_id,
            )
            self._audit_log_repository.create(audit_log)
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to create audit log: %s", e)

    def create_infrastructure(
        self, infrastructure: Infrastructure, changed_by: int | None = None
    ) -> Infrastructure:
        """Create new infrastructure for a colony.

        Args:
            infrastructure: The infrastructure domain object to create.
            changed_by: Optional user ID who made the change (for audit logging).

        Returns:
            The created infrastructure with ID assigned.
        """
        # Verify colony exists
        colony = self._colony_repository.get(infrastructure.colony_id)
        if colony is None:
            raise NotFoundError(f"Colony {infrastructure.colony_id} not found")
        result = self._repository.create(infrastructure)

        # Update missing infrastructure penalty
        self._update_missing_infrastructure_penalty(infrastructure.colony_id)

        # Log audit entry
        if (
            self._audit_log_repository is not None
            and changed_by is not None
            and result.id is not None
        ):
            self._log_audit(
                colony_id=infrastructure.colony_id,
                entity_type="infrastructure",
                entity_id=result.id,
                action=AuditLogAction.CREATE,
                field=None,
                old_value=None,
                new_value=result.infrastructure_type.value,
                changed_by=changed_by,
            )

        return result

    def get_infrastructure(self, infrastructure_id: int) -> Infrastructure:
        """Get infrastructure by ID."""
        infra = self._repository.get(infrastructure_id)
        if infra is None:
            raise NotFoundError(f"Infrastructure {infrastructure_id} not found")
        return infra

    def update_infrastructure_state(
        self,
        infrastructure_id: int,
        state: InfrastructureState,
        changed_by: int | None = None,
    ) -> Infrastructure:
        """Update infrastructure state.

        Args:
            infrastructure_id: ID of the infrastructure to update.
            state: New state for the infrastructure.
            changed_by: Optional user ID who made the change (for audit logging).

        Returns:
            The updated infrastructure.
        """
        infra = self.get_infrastructure(infrastructure_id)
        old_state = infra.state
        infra.state = state
        result = self._repository.update(infra)

        # Update missing infrastructure penalty
        self._update_missing_infrastructure_penalty(infra.colony_id)

        # Log audit entry
        if (
            self._audit_log_repository is not None
            and changed_by is not None
            and result.id is not None
        ):
            self._log_audit(
                colony_id=infra.colony_id,
                entity_type="infrastructure",
                entity_id=result.id,
                action=AuditLogAction.UPDATE,
                field="state",
                old_value=old_state.value,
                new_value=state.value,
                changed_by=changed_by,
            )

        return result

    def update_infrastructure_name(
        self,
        infrastructure_id: int,
        name: str,
        changed_by: int | None = None,
    ) -> Infrastructure:
        """Update infrastructure name.

        Args:
            infrastructure_id: ID of the infrastructure to update.
            name: New name for the infrastructure.
            changed_by: Optional user ID who made the change (for audit logging).

        Returns:
            The updated infrastructure.
        """
        infra = self.get_infrastructure(infrastructure_id)
        old_name = infra.name
        infra.name = name
        result = self._repository.update(infra)

        # Log audit entry
        if (
            self._audit_log_repository is not None
            and changed_by is not None
            and result.id is not None
        ):
            self._log_audit(
                colony_id=infra.colony_id,
                entity_type="infrastructure",
                entity_id=result.id,
                action=AuditLogAction.UPDATE,
                field="name",
                old_value=old_name,
                new_value=name,
                changed_by=changed_by,
            )

        return result

    def update_infrastructure_notes(
        self,
        infrastructure_id: int,
        notes: str,
        changed_by: int | None = None,
    ) -> Infrastructure:
        """Update infrastructure notes.

        Args:
            infrastructure_id: ID of the infrastructure to update.
            notes: New notes for the infrastructure.
            changed_by: Optional user ID who made the change (for audit logging).

        Returns:
            The updated infrastructure.
        """
        infra = self.get_infrastructure(infrastructure_id)
        old_notes = infra.notes
        infra.notes = notes
        result = self._repository.update(infra)

        # Log audit entry
        if (
            self._audit_log_repository is not None
            and changed_by is not None
            and result.id is not None
        ):
            self._log_audit(
                colony_id=infra.colony_id,
                entity_type="infrastructure",
                entity_id=result.id,
                action=AuditLogAction.UPDATE,
                field="notes",
                old_value=old_notes,
                new_value=notes,
                changed_by=changed_by,
            )

        return result

    def delete_infrastructure(self, infrastructure_id: int, changed_by: int | None = None) -> None:
        """Delete infrastructure.

        Args:
            infrastructure_id: ID of the infrastructure to delete.
            changed_by: Optional user ID who made the change (for audit logging).
        """
        infra = self._repository.get(infrastructure_id)
        if infra is not None:
            colony_id = infra.colony_id
            infra_type = infra.infrastructure_type.value
            self._repository.delete(infrastructure_id)

            # Update missing infrastructure penalty
            self._update_missing_infrastructure_penalty(colony_id)

            # Log audit entry
            if self._audit_log_repository is not None and changed_by is not None:
                self._log_audit(
                    colony_id=colony_id,
                    entity_type="infrastructure",
                    entity_id=infrastructure_id,
                    action=AuditLogAction.DELETE,
                    field=None,
                    old_value=infra_type,
                    new_value=None,
                    changed_by=changed_by,
                )
        else:
            # Silently ignore delete of non-existent infrastructure (idempotent)
            self._repository.delete(infrastructure_id)

    def list_by_colony(self, colony_id: int) -> list[Infrastructure]:
        """List all infrastructure for a colony."""
        return self._repository.list_by_colony(colony_id)

    def colony_exists(self, colony_id: int) -> bool:
        """Check if a colony exists."""
        return self._colony_repository.get(colony_id) is not None

    def update_infrastructure_batch(
        self,
        infrastructure_id: int,
        update_data: Mapping[str, object],
        changed_by: int | None = None,
    ) -> Infrastructure:
        """Update multiple fields on infrastructure in a single batch operation.

        Args:
            infrastructure_id: ID of the infrastructure to update.
            update_data: Dictionary of fields to update (name, notes, state).
                        Only provided fields are updated.
            changed_by: Optional user ID who made the change (for audit logging).

        Returns:
            The updated infrastructure.

        Raises:
            NotFoundError: If the infrastructure is not found.
        """
        infrastructure = self.get_infrastructure(infrastructure_id)

        # Track changes for audit logging
        changes_made = []

        # Apply updates
        if update_data.get("name") is not None:
            old_name = infrastructure.name
            infrastructure = infrastructure.model_copy(update={"name": update_data["name"]})
            changes_made.append(("name", old_name, update_data["name"]))

        if update_data.get("notes") is not None:
            old_notes = infrastructure.notes
            infrastructure = infrastructure.model_copy(update={"notes": update_data["notes"]})
            changes_made.append(("notes", old_notes, update_data["notes"]))

        if update_data.get("state") is not None:
            old_state = infrastructure.state.value
            infrastructure = infrastructure.model_copy(update={"state": update_data["state"]})
            changes_made.append(("state", old_state, infrastructure.state.value))

        # Persist the update
        result = self._repository.update(infrastructure)

        # Update missing infrastructure penalty if state changed
        if update_data.get("state") is not None:
            self._update_missing_infrastructure_penalty(infrastructure.colony_id)

        # Log audit entries for each change
        if self._audit_log_repository is not None and changed_by is not None:
            for field, old_value, new_value in changes_made:
                self._log_audit(
                    colony_id=infrastructure.colony_id,
                    entity_type="infrastructure",
                    entity_id=infrastructure_id,
                    action=AuditLogAction.UPDATE,
                    field=field,
                    old_value=str(old_value) if old_value is not None else None,
                    new_value=str(new_value) if new_value is not None else None,
                    changed_by=changed_by,
                )

        return result

    def _update_missing_infrastructure_penalty(self, colony_id: int) -> None:
        """
        Update the missing infrastructure penalty modifier for a colony.

        Removes any existing penalty modifier and adds a new one if needed
        based on current infrastructure state.

        Per business_analysis.md §3.1:
        Until each required infrastructure type is built (moved to Working),
        the colony suffers Complacency -1 per missing type.

        Args:
            colony_id: The colony ID to update.
        """
        colony = self._colony_repository.get(colony_id)
        if colony is None:
            return

        # Get all infrastructure for this colony
        infrastructure_list = self._repository.list_by_colony(colony_id)

        # Get the missing infrastructure penalty
        penalty_modifiers = get_missing_infrastructure_penalty(infrastructure_list, colony_id)

        # Remove any existing missing infrastructure penalty modifier
        colony.modifiers = [
            mod
            for mod in colony.modifiers
            if "Missing Infrastructure" not in mod.modifier_description
        ]

        # Add the new penalty if applicable
        if penalty_modifiers:
            colony.modifiers.extend(penalty_modifiers)

        # Save the updated colony
        self._colony_repository.update(colony)

    def preview_state_transition(
        self,
        infrastructure_id: int,
        new_state: InfrastructureState,
    ) -> dict[str, Any]:
        """
        Preview the effects of a state transition without applying it.

        Args:
            infrastructure_id: ID of the infrastructure to preview.
            new_state: The requested new state.

        Returns:
            Dictionary with validation results and modifiers preview. Values are
            intentionally untyped (`dict[str, Any]`): the by-key shape duplicates
            InfrastructureValidationResponse, so a parallel TypedDict is avoided
            to prevent schema drift.
        """
        from colony_manager.domain.rules.infrastructure_rules import (
            apply_infrastructure_modifiers,
        )

        infrastructure = self.get_infrastructure(infrastructure_id)
        current_state = infrastructure.state
        would_apply_penalty = False
        penalty_description: str | None = None
        modifiers_preview: list[dict[str, object]] = []

        # Create a temporary infrastructure with the new state
        temp_infra = infrastructure.model_copy(update={"state": new_state})

        # Get modifiers that would apply
        modifiers = apply_infrastructure_modifiers([temp_infra])
        modifiers_preview = [
            {
                "stat": mod.modifier_stat.value if mod.modifier_stat else None,
                "value": mod.modifier_value,
                "description": mod.modifier_description,
                "source_entity_id": mod.source_entity_id,
            }
            for mod in modifiers
        ]

        # Check if this would remove/apply a missing infrastructure penalty
        if infrastructure.is_not_working and temp_infra.is_working:
            would_apply_penalty = False  # Removing penalty
            penalty_description = "Missing infrastructure penalty would be removed"
        elif infrastructure.is_working and temp_infra.is_not_working:
            would_apply_penalty = True
            penalty_description = "Missing infrastructure penalty would be applied"

        return {
            "valid": True,
            "current_state": current_state,
            "requested_state": new_state,
            "modifiers_preview": modifiers_preview,
            "would_apply_penalty": would_apply_penalty,
            "penalty_description": penalty_description,
        }
