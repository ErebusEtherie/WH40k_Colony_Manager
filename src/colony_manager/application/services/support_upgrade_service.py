"""Support Upgrade service for managing colony support upgrades."""

import logging
from collections.abc import Mapping
from enum import Enum
from typing import Any

from colony_manager.domain.enums import ModifierStat
from colony_manager.domain.errors import NotFoundError
from colony_manager.domain.models.audit_log import AuditLog, AuditLogAction
from colony_manager.domain.models.support_upgrade import SupportUpgrade
from colony_manager.domain.ports.audit_log_repository import AuditLogRepository
from colony_manager.domain.ports.colony_repository import ColonyRepository
from colony_manager.domain.ports.support_upgrade_repository import SupportUpgradeRepository

logger = logging.getLogger(__name__)


class SupportUpgradeService:
    """Service layer for support upgrade management."""

    def __init__(
        self,
        repository: SupportUpgradeRepository,
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

    def create_upgrade(
        self, upgrade: SupportUpgrade, changed_by: int | None = None
    ) -> SupportUpgrade:
        """Create new support upgrade for a colony.

        Args:
            upgrade: The support upgrade domain object to create.
            changed_by: Optional user ID who made the change (for audit logging).

        Returns:
            The created support upgrade with ID assigned.
        """
        # Verify colony exists
        colony = self._colony_repository.get(upgrade.colony_id)
        if colony is None:
            raise NotFoundError(f"Colony {upgrade.colony_id} not found")
        result = self._repository.create(upgrade)

        # Log audit entry
        if (
            self._audit_log_repository is not None
            and changed_by is not None
            and result.id is not None
        ):
            self._log_audit(
                colony_id=upgrade.colony_id,
                entity_type="support_upgrade",
                entity_id=result.id,
                action=AuditLogAction.CREATE,
                field=None,
                old_value=None,
                new_value=result.upgrade_type.value,
                changed_by=changed_by,
            )

        return result

    def get_upgrade(self, upgrade_id: int) -> SupportUpgrade:
        """Get support upgrade by ID."""
        upgrade = self._repository.get(upgrade_id)
        if upgrade is None:
            raise NotFoundError(f"SupportUpgrade {upgrade_id} not found")
        return upgrade

    def update_upgrade(
        self, upgrade: SupportUpgrade, changed_by: int | None = None
    ) -> SupportUpgrade:
        """Update support upgrade.

        Args:
            upgrade: The support upgrade with updated values.
            changed_by: Optional user ID who made the change (for audit logging).

        Returns:
            The updated support upgrade.
        """
        # Verify upgrade exists
        if upgrade.id is None:
            raise NotFoundError("Upgrade ID is required for update")
        self.get_upgrade(upgrade.id)

        result = self._repository.update(upgrade)

        # Log audit entry for update
        if (
            self._audit_log_repository is not None
            and changed_by is not None
            and result.id is not None
        ):
            self._log_audit(
                colony_id=upgrade.colony_id,
                entity_type="support_upgrade",
                entity_id=result.id,
                action=AuditLogAction.UPDATE,
                field=None,
                old_value=None,
                new_value=f"Updated {result.upgrade_type.value}",
                changed_by=changed_by,
            )

        return result

    def update_upgrade_name(
        self,
        upgrade_id: int,
        name: str,
        changed_by: int | None = None,
    ) -> SupportUpgrade:
        """Update support upgrade name.

        Args:
            upgrade_id: ID of the support upgrade to update.
            name: New name for the support upgrade.
            changed_by: Optional user ID who made the change (for audit logging).

        Returns:
            The updated support upgrade.
        """
        upgrade = self.get_upgrade(upgrade_id)
        old_name = upgrade.name
        upgrade.name = name
        result = self._repository.update(upgrade)

        # Log audit entry
        if (
            self._audit_log_repository is not None
            and changed_by is not None
            and result.id is not None
        ):
            self._log_audit(
                colony_id=upgrade.colony_id,
                entity_type="support_upgrade",
                entity_id=result.id,
                action=AuditLogAction.UPDATE,
                field="name",
                old_value=old_name,
                new_value=name,
                changed_by=changed_by,
            )

        return result

    def update_upgrade_notes(
        self,
        upgrade_id: int,
        notes: str,
        changed_by: int | None = None,
    ) -> SupportUpgrade:
        """Update support upgrade notes.

        Args:
            upgrade_id: ID of the support upgrade to update.
            notes: New notes for the support upgrade.
            changed_by: Optional user ID who made the change (for audit logging).

        Returns:
            The updated support upgrade.
        """
        upgrade = self.get_upgrade(upgrade_id)
        old_notes = upgrade.notes
        upgrade.notes = notes
        result = self._repository.update(upgrade)

        # Log audit entry
        if (
            self._audit_log_repository is not None
            and changed_by is not None
            and result.id is not None
        ):
            self._log_audit(
                colony_id=upgrade.colony_id,
                entity_type="support_upgrade",
                entity_id=result.id,
                action=AuditLogAction.UPDATE,
                field="notes",
                old_value=old_notes,
                new_value=notes,
                changed_by=changed_by,
            )

        return result

    def update_upgrade_custom_stat_choice(
        self,
        upgrade_id: int,
        custom_stat_choice: ModifierStat,
        changed_by: int | None = None,
    ) -> SupportUpgrade:
        """Update support upgrade custom stat choice.

        Args:
            upgrade_id: ID of the support upgrade to update.
            custom_stat_choice: New custom stat choice for the support upgrade.
            changed_by: Optional user ID who made the change (for audit logging).

        Returns:
            The updated support upgrade.
        """
        upgrade = self.get_upgrade(upgrade_id)
        old_value = upgrade.custom_stat_choice.value if upgrade.custom_stat_choice else None
        upgrade.custom_stat_choice = custom_stat_choice
        result = self._repository.update(upgrade)

        # Log audit entry
        if (
            self._audit_log_repository is not None
            and changed_by is not None
            and result.id is not None
        ):
            self._log_audit(
                colony_id=upgrade.colony_id,
                entity_type="support_upgrade",
                entity_id=result.id,
                action=AuditLogAction.UPDATE,
                field="custom_stat_choice",
                old_value=old_value,
                new_value=custom_stat_choice.value,
                changed_by=changed_by,
            )

        return result

    def update_upgrade_custom_product(
        self,
        upgrade_id: int,
        custom_product: str,
        changed_by: int | None = None,
    ) -> SupportUpgrade:
        """Update support upgrade custom product.

        Args:
            upgrade_id: ID of the support upgrade to update.
            custom_product: New custom product for the support upgrade.
            changed_by: Optional user ID who made the change (for audit logging).

        Returns:
            The updated support upgrade.
        """
        upgrade = self.get_upgrade(upgrade_id)
        old_value = upgrade.custom_product
        upgrade.custom_product = custom_product
        result = self._repository.update(upgrade)

        # Log audit entry
        if (
            self._audit_log_repository is not None
            and changed_by is not None
            and result.id is not None
        ):
            self._log_audit(
                colony_id=upgrade.colony_id,
                entity_type="support_upgrade",
                entity_id=result.id,
                action=AuditLogAction.UPDATE,
                field="custom_product",
                old_value=old_value,
                new_value=custom_product,
                changed_by=changed_by,
            )

        return result

    def update_upgrade_affiliated_group(
        self,
        upgrade_id: int,
        affiliated_group: str,
        changed_by: int | None = None,
    ) -> SupportUpgrade:
        """Update support upgrade affiliated group.

        Args:
            upgrade_id: ID of the support upgrade to update.
            affiliated_group: New affiliated group for the support upgrade.
            changed_by: Optional user ID who made the change (for audit logging).

        Returns:
            The updated support upgrade.
        """
        upgrade = self.get_upgrade(upgrade_id)
        old_value = upgrade.affiliated_group
        upgrade.affiliated_group = affiliated_group
        result = self._repository.update(upgrade)

        # Log audit entry
        if (
            self._audit_log_repository is not None
            and changed_by is not None
            and result.id is not None
        ):
            self._log_audit(
                colony_id=upgrade.colony_id,
                entity_type="support_upgrade",
                entity_id=result.id,
                action=AuditLogAction.UPDATE,
                field="affiliated_group",
                old_value=old_value,
                new_value=affiliated_group,
                changed_by=changed_by,
            )

        return result

    def delete_upgrade(self, upgrade_id: int, changed_by: int | None = None) -> None:
        """Delete support upgrade.

        Args:
            upgrade_id: ID of the support upgrade to delete.
            changed_by: Optional user ID who made the change (for audit logging).
        """
        upgrade = self._repository.get(upgrade_id)
        if upgrade is not None:
            colony_id = upgrade.colony_id
            upgrade_type = upgrade.upgrade_type.value
            self._repository.delete(upgrade_id)

            # Log audit entry
            if self._audit_log_repository is not None and changed_by is not None:
                self._log_audit(
                    colony_id=colony_id,
                    entity_type="support_upgrade",
                    entity_id=upgrade_id,
                    action=AuditLogAction.DELETE,
                    field=None,
                    old_value=upgrade_type,
                    new_value=None,
                    changed_by=changed_by,
                )
        else:
            # Silently ignore delete of non-existent upgrade (idempotent)
            self._repository.delete(upgrade_id)

    def list_by_colony(self, colony_id: int) -> list[SupportUpgrade]:
        """List all support upgrades for a colony."""
        return self._repository.list_by_colony(colony_id)

    def colony_exists(self, colony_id: int) -> bool:
        """Check if a colony exists."""
        return self._colony_repository.get(colony_id) is not None

    def _get_field_old_value(self, upgrade: SupportUpgrade, field: str) -> str | None:
        """Get the old value of a field for audit logging.

        Args:
            upgrade: The support upgrade to get the value from.
            field: The field name to get the value for.

        Returns:
            The old value as a string, or None if the field doesn't exist.
        """
        value = getattr(upgrade, field, None)
        if value is None:
            return None
        # Handle enum values (like custom_stat_choice)
        if isinstance(value, Enum):
            return str(value.value)
        return str(value)

    def _apply_field_update(
        self,
        upgrade: SupportUpgrade,
        field: str,
        update_data: Mapping[str, object],
        changes_made: list[tuple[str, str | None, str | None]],
    ) -> SupportUpgrade:
        """Apply a single field update and track the change for audit logging.

        Args:
            upgrade: The support upgrade to update.
            field: The field name to update.
            update_data: Dictionary containing the new values.
            changes_made: List to track changes for audit logging.

        Returns:
            The updated support upgrade (may be a new instance via model_copy).
        """
        new_value = update_data.get(field)
        if new_value is None:
            return upgrade

        old_value = self._get_field_old_value(upgrade, field)
        upgrade = upgrade.model_copy(update={field: new_value})
        changes_made.append((field, old_value, str(new_value)))
        return upgrade

    def update_upgrade_batch(
        self,
        upgrade_id: int,
        update_data: Mapping[str, object],
        changed_by: int | None = None,
    ) -> SupportUpgrade:
        """Update multiple fields on a support upgrade in a single batch operation.

        Args:
            upgrade_id: ID of the support upgrade to update.
            update_data: Dictionary of fields to update (name, notes, custom_stat_choice,
                        custom_product, affiliated_group). Only provided fields are updated.
            changed_by: Optional user ID who made the change (for audit logging).

        Returns:
            The updated support upgrade.

        Raises:
            NotFoundError: If the upgrade is not found.
        """
        upgrade = self.get_upgrade(upgrade_id)

        # Track changes for audit logging
        changes_made: list[tuple[str, str | None, str | None]] = []

        # Apply updates for each configurable field
        updatable_fields = [
            "name",
            "notes",
            "custom_stat_choice",
            "custom_product",
            "affiliated_group",
        ]
        for field in updatable_fields:
            upgrade = self._apply_field_update(upgrade, field, update_data, changes_made)

        # Persist the update
        result = self._repository.update(upgrade)

        # Log audit entries for each change
        if self._audit_log_repository is not None and changed_by is not None:
            for field, old_value, new_value in changes_made:
                self._log_audit(
                    colony_id=upgrade.colony_id,
                    entity_type="support_upgrade",
                    entity_id=upgrade_id,
                    action=AuditLogAction.UPDATE,
                    field=field,
                    old_value=str(old_value) if old_value is not None else None,
                    new_value=str(new_value) if new_value is not None else None,
                    changed_by=changed_by,
                )

        return result

    def preview_upgrade_changes(
        self,
        upgrade_id: int,
        update_data: Mapping[str, object],
    ) -> dict[str, Any]:
        """
        Preview the effects of upgrade changes without applying them.

        Args:
            upgrade_id: ID of the support upgrade to preview.
            update_data: Dictionary of fields to update (name, notes, custom_stat_choice, etc.).

        Returns:
            Dictionary with validation results and modifiers preview. Values are
            intentionally untyped (`dict[str, Any]`): the by-key shape duplicates
            SupportUpgradeValidationResponse, so a parallel TypedDict is avoided
            to prevent schema drift.
        """
        from colony_manager.domain.rules.support_upgrade_rules import (
            get_support_upgrade_modifiers,
        )

        upgrade = self.get_upgrade(upgrade_id)
        modifiers_preview: list[dict[str, object]] = []
        colony_type_bonus_applied = False
        bonus_description: str | None = None

        # Build temporary upgrade with proposed changes
        temp_upgrade_data: dict[str, object] = {
            "custom_stat_choice": upgrade.custom_stat_choice,
            "custom_product": upgrade.custom_product,
            "affiliated_group": upgrade.affiliated_group,
        }
        if update_data.get("custom_stat_choice") is not None:
            temp_upgrade_data["custom_stat_choice"] = update_data["custom_stat_choice"]
        if update_data.get("custom_product") is not None:
            temp_upgrade_data["custom_product"] = update_data["custom_product"]
        if update_data.get("affiliated_group") is not None:
            temp_upgrade_data["affiliated_group"] = update_data["affiliated_group"]

        temp_upgrade = upgrade.model_copy(update=temp_upgrade_data)

        # Get colony to determine colony type bonus
        colony = self._colony_repository.get(upgrade.colony_id)
        colony_type = colony.colony_type if colony else None

        # Get modifiers that would apply
        modifiers = get_support_upgrade_modifiers(temp_upgrade, colony_type)
        modifiers_preview = [
            {
                "stat": mod.modifier_stat.value if mod.modifier_stat else None,
                "value": mod.modifier_value,
                "description": mod.modifier_description,
                "source_entity_id": mod.source_entity_id,
            }
            for mod in modifiers
        ]

        # Check if colony type bonus applies
        colony_type_bonus_applied = any(
            "colony type" in mod.modifier_description.lower() for mod in modifiers
        )
        if colony_type_bonus_applied:
            bonus_description = "Colony type bonus applied"

        return {
            "valid": True,
            "modifiers_preview": modifiers_preview,
            "colony_type_bonus_applied": colony_type_bonus_applied,
            "bonus_description": bonus_description if colony_type_bonus_applied else None,
        }
