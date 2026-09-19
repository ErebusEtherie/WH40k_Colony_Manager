"""Application service for development plan management.

This service orchestrates development plan operations, including creation,
updates, installation as infrastructure/support upgrades, and integration
with the audit logging system.
"""

from typing import Any, ClassVar

from colony_manager.domain.enums import InfrastructureState, InfrastructureType, SupportUpgradeType
from colony_manager.domain.errors import NotFoundError, ValidationError
from colony_manager.domain.models.development_plan import DevelopmentPlan, DevelopmentPlanStatus
from colony_manager.domain.models.infrastructure import Infrastructure
from colony_manager.domain.models.support_upgrade import SupportUpgrade
from colony_manager.domain.ports.audit_log_repository import AuditLogRepository
from colony_manager.domain.ports.development_plan_repository import DevelopmentPlanRepository
from colony_manager.domain.ports.infrastructure_repository import InfrastructureRepository
from colony_manager.domain.ports.support_upgrade_repository import SupportUpgradeRepository


class DevelopmentPlanService:
    """Service for managing colony development plans.

    Development plans track long-term colony development goals. This service
    handles plan CRUD operations, status transitions, and installation as
    actual Infrastructure or Support Upgrades.
    """

    # Valid status transitions
    VALID_TRANSITIONS: ClassVar[dict[DevelopmentPlanStatus, set[DevelopmentPlanStatus]]] = {
        DevelopmentPlanStatus.PLANNED: {
            DevelopmentPlanStatus.IN_PROGRESS,
            DevelopmentPlanStatus.PLANNED,
        },
        DevelopmentPlanStatus.IN_PROGRESS: {
            DevelopmentPlanStatus.PLANNED,
            DevelopmentPlanStatus.ACQUIRED,
            DevelopmentPlanStatus.IN_PROGRESS,
        },
        DevelopmentPlanStatus.ACQUIRED: {
            DevelopmentPlanStatus.PLANNED,
            DevelopmentPlanStatus.IN_PROGRESS,
            DevelopmentPlanStatus.DELIVERED,
            DevelopmentPlanStatus.ACQUIRED,
        },
        DevelopmentPlanStatus.DELIVERED: {
            DevelopmentPlanStatus.PLANNED,
            DevelopmentPlanStatus.ACQUIRED,
            DevelopmentPlanStatus.DELIVERED,
        },
    }

    def _validate_status_transition(
        self, current_status: DevelopmentPlanStatus, new_status: DevelopmentPlanStatus
    ) -> None:
        """Validate that a status transition is allowed.

        Args:
            current_status: Current status of the plan.
            new_status: Desired new status.

        Raises:
            ValidationError: If the transition is not allowed.
        """
        allowed = self.VALID_TRANSITIONS.get(current_status, set())
        if new_status not in allowed:
            raise ValidationError(
                f"Invalid status transition from {current_status.value} to {new_status.value}. "
                f"Allowed transitions: {[s.value for s in allowed]}"
            )

    def __init__(
        self,
        plan_repository: DevelopmentPlanRepository,
        audit_log_repository: AuditLogRepository | None = None,
        infrastructure_repository: InfrastructureRepository | None = None,
        support_upgrade_repository: SupportUpgradeRepository | None = None,
    ) -> None:
        self._plan_repository = plan_repository
        self._audit_log_repository = audit_log_repository
        self._infrastructure_repository = infrastructure_repository
        self._support_upgrade_repository = support_upgrade_repository

    def create_plan(
        self,
        colony_id: int,
        upgrade_type: str,
        target_type: str,
        target_name: str,
        priority: int,
        description: str,
        created_by: int,
        notes: str = "",
        order: int = 0,
    ) -> DevelopmentPlan:
        """Create a new development plan for a colony.

        Args:
            colony_id: ID of the colony.
            upgrade_type: Type of upgrade ("infrastructure" or "support_upgrade").
            target_type: The specific type enum value (e.g., "transport", "arbites_precinct").
            target_name: Custom player-defined name for the item.
            priority: Priority level (1-5).
            description: Detailed description of the plan.
            created_by: User ID creating the plan.
            notes: Optional player notes for internal tracking.
            order: Sort order for manual list arrangement.

        Returns:
            Created development plan.
        """
        plan = DevelopmentPlan(
            colony_id=colony_id,
            upgrade_type=upgrade_type,
            target_type=target_type,
            target_name=target_name,
            priority=priority,
            description=description,
            notes=notes,
            order=order,
            created_by=created_by,
        )

        created_plan = self._plan_repository.create(plan)

        # Log the creation
        if self._audit_log_repository:
            from colony_manager.domain.models.audit_log import AuditLog, AuditLogAction

            if created_plan.id is None:
                raise RuntimeError("Created plan has no ID")

            audit_log = AuditLog(
                entity_type="development_plan",
                entity_id=created_plan.id,
                action=AuditLogAction.CREATE,
                changed_by=created_by,
                colony_id=colony_id,
            )
            self._audit_log_repository.create(audit_log)

        return created_plan

    def get_plan(self, plan_id: int) -> DevelopmentPlan | None:
        """Get a development plan by ID."""
        return self._plan_repository.get_by_id(plan_id)

    def get_plans_by_colony(self, colony_id: int) -> list[DevelopmentPlan]:
        """Get all development plans for a colony."""
        return self._plan_repository.get_by_colony(colony_id)

    def update_plan(
        self,
        plan_id: int,
        upgrade_type: str | None = None,
        target_type: str | None = None,
        target_name: str | None = None,
        priority: int | None = None,
        description: str | None = None,
        notes: str | None = None,
        order: int | None = None,
        status: DevelopmentPlanStatus | None = None,
        changed_by: int | None = None,
    ) -> DevelopmentPlan:
        """Update an existing development plan."""
        plan = self._plan_repository.get_by_id(plan_id)
        if plan is None:
            raise NotFoundError(f"Development plan with ID {plan_id} not found")

        if upgrade_type is not None:
            plan.upgrade_type = upgrade_type
        if target_type is not None:
            plan.target_type = target_type
        if target_name is not None:
            plan.target_name = target_name
        if priority is not None:
            plan.priority = priority
        if description is not None:
            plan.description = description
        if notes is not None:
            plan.notes = notes
        if order is not None:
            plan.order = order
        if status is not None:
            self._validate_status_transition(plan.status, status)
            plan.status = status

        updated_plan = self._plan_repository.update(plan)

        # Log the update
        if self._audit_log_repository and changed_by:
            from colony_manager.domain.models.audit_log import AuditLog, AuditLogAction

            audit_log = AuditLog(
                entity_type="development_plan",
                entity_id=plan_id,
                action=AuditLogAction.UPDATE,
                changed_by=changed_by,
                colony_id=plan.colony_id,
            )
            self._audit_log_repository.create(audit_log)

        return updated_plan

    def delete_plan(self, plan_id: int, changed_by: int | None = None) -> None:
        """Delete a development plan."""
        plan = self._plan_repository.get_by_id(plan_id)
        if plan is None:
            raise NotFoundError(f"Development plan with ID {plan_id} not found")

        colony_id = plan.colony_id
        self._plan_repository.delete(plan_id)

        # Log the deletion
        if self._audit_log_repository and changed_by:
            from colony_manager.domain.models.audit_log import AuditLog, AuditLogAction

            audit_log = AuditLog(
                entity_type="development_plan",
                entity_id=plan_id,
                action=AuditLogAction.DELETE,
                changed_by=changed_by,
                colony_id=colony_id,
            )
            self._audit_log_repository.create(audit_log)

    def install_plan(
        self,
        plan_id: int,
        installed_by: int,
    ) -> dict[str, Any]:
        """Install a development plan as an Infrastructure or Support Upgrade.

        Only plans in DELIVERED status can be installed. This method creates
        the actual Infrastructure or SupportUpgrade entity and deletes the
        development plan.

        Args:
            plan_id: ID of the development plan to install.
            installed_by: User ID performing the installation.

        Returns:
            Dictionary with installation result including created entity details.

        Raises:
            NotFoundError: If plan not found.
            ValidationError: If plan is not in DELIVERED status.
        """
        plan = self._plan_repository.get_by_id(plan_id)
        if plan is None:
            raise NotFoundError(f"Development plan with ID {plan_id} not found")

        if self._infrastructure_repository is None or self._support_upgrade_repository is None:
            raise ValidationError(
                "Infrastructure and Support Upgrade repositories must be "
                "configured to install plans"
            )

        # Verify plan is in DELIVERED status
        plan = self._plan_repository.get_by_id(plan_id)
        if plan is None:
            raise NotFoundError(f"Development plan with ID {plan_id} not found")

        if plan.status != DevelopmentPlanStatus.DELIVERED:
            raise ValidationError(
                f"Cannot install plan with status {plan.status.value}. "
                f"Plan must be in DELIVERED status."
            )

        # Create the appropriate upgrade based on plan type
        if plan.upgrade_type == "infrastructure":
            # Create infrastructure with IN_PROGRESS state
            infra_type = InfrastructureType(plan.target_type)
            infrastructure = Infrastructure(
                colony_id=plan.colony_id,
                infrastructure_type=infra_type,
                state=InfrastructureState.IN_PROGRESS,
            )
            created_infra = self._infrastructure_repository.create(infrastructure)
            installed_type = "infrastructure"
            installed_id = created_infra.id
            installed_data = {
                "id": created_infra.id,
                "infra_type": created_infra.infrastructure_type.value,
                "custom_name": None,
            }
        elif plan.upgrade_type == "support_upgrade":
            # Create support upgrade
            upgrade_type = SupportUpgradeType(plan.target_type)
            upgrade = SupportUpgrade(
                colony_id=plan.colony_id,
                upgrade_type=upgrade_type,
            )
            created_upgrade = self._support_upgrade_repository.create(upgrade)
            installed_type = "support_upgrade"
            installed_id = created_upgrade.id
            installed_data = {
                "id": created_upgrade.id,
                "upgrade_type": created_upgrade.upgrade_type.value,
                "custom_name": None,
            }
        else:
            raise ValidationError(f"Invalid upgrade type: {plan.upgrade_type}")

        # Log the installation before deleting the plan
        if self._audit_log_repository:
            from colony_manager.domain.models.audit_log import AuditLog, AuditLogAction

            audit_log = AuditLog(
                entity_type="development_plan",
                entity_id=plan_id,
                action=AuditLogAction.UPDATE,
                field="installed_as_" + installed_type,
                old_value="development_plan",
                new_value=f"{installed_type}:{installed_id}",
                changed_by=installed_by,
                colony_id=plan.colony_id,
            )
            self._audit_log_repository.create(audit_log)

        # Delete the development plan
        self._plan_repository.delete(plan_id)

        return {
            "plan_id": plan_id,
            "plan_name": plan.target_name,
            "plan_target_type": plan.target_type,
            "installed_type": installed_type,
            "installed_id": installed_id,
            "installed_data": installed_data,
        }
