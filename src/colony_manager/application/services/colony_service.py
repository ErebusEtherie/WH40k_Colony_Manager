"""Application service for colony use cases."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import TypedDict

from colony_manager.application.services.colony_state_calculator import ColonyStateCalculator
from colony_manager.domain.enums import ModifierStat
from colony_manager.domain.errors import NotFoundError
from colony_manager.domain.models.audit_log import AuditLog, AuditLogAction
from colony_manager.domain.models.colony import Colony
from colony_manager.domain.models.modifier import Modifier
from colony_manager.domain.ports.audit_log_repository import AuditLogRepository
from colony_manager.domain.ports.colony_repository import ColonyRepository
from colony_manager.domain.ports.colony_user_repository import ColonyUserRepository
from colony_manager.domain.ports.representative_repository import RepresentativeRepository
from colony_manager.domain.ports.rule_config_provider import RuleConfigProvider
from colony_manager.domain.rules.representative_rules import get_personality_modifiers

logger = logging.getLogger(__name__)


class RollStatusDict(TypedDict):
    """Dictionary type for roll status."""

    event_roll_due: bool
    development_roll_due: bool
    days_since_event_roll: int
    days_until_event_roll: int
    days_since_development_roll: int
    days_until_development_roll: int
    event_interval_days: int
    development_interval_days: int


class ModifierBreakdownItemDict(TypedDict):
    """Dictionary type for individual modifier in breakdown."""

    source_type: str
    source_id: int | None
    source_name: str
    value: int
    description: str


class StatBreakdownDict(TypedDict):
    """Dictionary type for stat modifier breakdown."""

    base: int
    modifiers: list[ModifierBreakdownItemDict]
    total_modifier: int
    current: int


class ModifierBreakdownDict(TypedDict):
    """Dictionary type for full modifier breakdown."""

    size: StatBreakdownDict
    complacency: StatBreakdownDict
    order: StatBreakdownDict
    productivity: StatBreakdownDict
    piety: StatBreakdownDict
    leadership_modifier: int
    profit_factor: int


def _build_stat_breakdown(
    stat: ModifierStat,
    base_value: int,
    current_value: int,
    modifiers: list[Modifier],
) -> StatBreakdownDict:
    """Build breakdown for a single stat.

    Args:
        stat: The stat type being broken down.
        base_value: Base stat value before modifiers.
        current_value: Final calculated stat value (includes conditional bonuses).
        modifiers: List of active modifiers affecting this stat.

    Returns:
        StatBreakdownDict with base, modifiers, total_modifier, and current.
    """
    breakdown_mods: list[ModifierBreakdownItemDict] = []
    total_modifier = 0

    for mod in modifiers:
        # Get source name from modifier description or source
        # Extract entity name from description
        # (e.g., "Advanced Manufactorum (manufactorum - working)" → "Advanced Manufactorum")
        if mod.modifier_description:
            # Extract entity name before first parenthesis, fallback to full description
            source_name = (
                mod.modifier_description.split(" (")[0].strip() or mod.modifier_description
            )
        else:
            source_name = f"{mod.modifier_source_type.value}"
        breakdown_mods.append(
            ModifierBreakdownItemDict(
                source_type=mod.modifier_source_type.value,
                source_id=mod.source_entity_id,
                source_name=source_name,
                value=mod.modifier_value,
                description=mod.modifier_description,
            )
        )
        total_modifier += mod.modifier_value

    return StatBreakdownDict(
        base=base_value,
        modifiers=breakdown_mods,
        total_modifier=total_modifier,
        current=current_value,
    )


class ColonyService:
    """Create, update, and query colonies via repository and rule adapters."""

    def __init__(
        self,
        colony_repository: ColonyRepository,
        representative_repository: RepresentativeRepository,
        rule_config_provider: RuleConfigProvider,
        colony_user_repository: ColonyUserRepository,
        audit_log_repository: AuditLogRepository | None = None,
    ) -> None:
        self._colony_repository = colony_repository
        self._representative_repository = representative_repository
        self._rule_config_provider = rule_config_provider
        self._state_calculator = ColonyStateCalculator(rule_config_provider)
        self._audit_log_repository = audit_log_repository
        self._colony_user_repository = colony_user_repository

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
        """Create an audit log entry if audit logging is enabled.

        Args:
            colony_id: ID of the colony being modified.
            entity_type: Type of entity (e.g., "colony", "modifier").
            entity_id: ID of the entity being modified.
            action: Action performed (e.g., "create", "update", "delete").
            field: Field that was changed (if applicable).
            old_value: Previous value (if applicable).
            new_value: New value (if applicable).
            changed_by: User ID who made the change.
        """
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
            # Don't fail the operation if audit logging fails
            # In production, you might want to log this to a monitoring system
            logger.warning("Failed to create audit log: %s", e)

    def create_colony(self, colony: Colony, changed_by: int | None = None) -> Colony:
        """Create a new colony.

        Args:
            colony: Colony domain object to create.
            changed_by: Optional user ID who created the colony (for audit logging).

        Returns:
            Created colony with ID populated.
        """
        result = self._colony_repository.create(colony)

        # Automatically add the creator as an owner member of the colony
        if changed_by is not None and result.id is not None:
            from colony_manager.domain.models.colony_user import ColonyUser, ColonyUserRole

            membership = ColonyUser(
                colony_id=result.id,
                user_id=changed_by,
                role=ColonyUserRole.OWNER,
                invited_by=changed_by,
            )
            self._colony_user_repository.create(membership)

        # Log audit entry if audit logging is enabled and user ID provided
        if (
            self._audit_log_repository is not None
            and changed_by is not None
            and result.id is not None
        ):
            self._log_audit(
                colony_id=result.id,
                entity_type="colony",
                entity_id=result.id,
                action=AuditLogAction.CREATE,
                field=None,
                old_value=None,
                new_value=f"Colony created: {result.name}",
                changed_by=changed_by,
            )

        return result

    def update_age(self, colony_id: int, age_days: int, changed_by: int | None = None) -> Colony:
        """Update colony age.

        Args:
            colony_id: The ID of the colony to update.
            age_days: New age in days.
            changed_by: Optional user ID who made the change (for audit logging).

        Returns:
            Updated colony.

        Raises:
            NotFoundError: If the colony does not exist.
        """
        colony = self._colony_repository.get(colony_id)
        if colony is None:
            raise NotFoundError(f"Colony {colony_id} not found")

        old_age = colony.age_days
        colony.age_days = age_days
        colony.age_last_updated = datetime.now(UTC).date()
        result = self._colony_repository.update(colony)

        # Log audit entry if audit logging is enabled and user ID provided
        if (
            self._audit_log_repository is not None
            and changed_by is not None
            and result.id is not None
        ):
            self._log_audit(
                colony_id=result.id,
                entity_type="colony",
                entity_id=result.id,
                action=AuditLogAction.UPDATE,
                field="age_days",
                old_value=str(old_age),
                new_value=str(age_days),
                changed_by=changed_by,
            )

        return result

    def add_modifier(
        self, colony_id: int, modifier: Modifier, changed_by: int | None = None
    ) -> Colony:
        """Add a modifier to a colony.

        Args:
            colony_id: The ID of the colony.
            modifier: Modifier to add.
            changed_by: Optional user ID who made the change (for audit logging).

        Returns:
            Updated colony with modifier added.

        Raises:
            NotFoundError: If the colony does not exist.
        """
        colony = self._colony_repository.get(colony_id)
        if colony is None:
            raise NotFoundError(f"Colony {colony_id} not found")

        colony.modifiers.append(modifier)
        result = self._colony_repository.update(colony)

        # Log audit entry if audit logging is enabled and user ID provided
        if (
            self._audit_log_repository is not None
            and changed_by is not None
            and result.id is not None
        ):
            stat_label = (
                modifier.modifier_stat.value
                if hasattr(modifier.modifier_stat, "value")
                else modifier.modifier_stat
            )
            self._log_audit(
                colony_id=result.id,
                entity_type="modifier",
                entity_id=modifier.id if modifier.id else 0,
                action=AuditLogAction.CREATE,
                field=None,
                old_value=None,
                new_value=f"Modifier added: {stat_label} = {modifier.modifier_value}",
                changed_by=changed_by,
            )

        return result

    def get_state(self, colony_id: int, as_of: date | None = None) -> dict[str, object]:
        """
        Get the calculated state for a colony.

        Args:
            colony_id: The ID of the colony.
            as_of: Optional date to calculate state for (for modifier expiry).
                   Defaults to today if not provided.

        Returns:
            Dict with calculated stats.

        Raises:
            NotFoundError: If the colony does not exist.
        """
        colony = self._colony_repository.get(colony_id)
        if colony is None:
            raise NotFoundError(f"Colony {colony_id} not found")
        return self._state_calculator.calculate(colony, as_of)

    def get_colony(self, colony_id: int) -> Colony:
        """Get a colony by ID.

        Args:
            colony_id: The ID of the colony to retrieve.

        Returns:
            The colony domain object.

        Raises:
            NotFoundError: If the colony does not exist.
        """
        colony = self._colony_repository.get(colony_id)
        if colony is None:
            raise NotFoundError(f"Colony {colony_id} not found")
        return colony

    def _prepare_audit_changes(
        self,
        colony: Colony,
        fields: dict[str, object],
    ) -> list[tuple[str, object, object]]:
        """Prepare audit log entries for field changes.

        Args:
            colony: The colony being updated.
            fields: Dictionary of field names and new values.

        Returns:
            List of tuples (field_name, old_value, new_value) for changed fields.
        """
        changes = []
        for field, value in fields.items():
            if value is not None:
                old_value = getattr(colony, field, None)
                if old_value != value:
                    changes.append((field, old_value, value))
        return changes

    def _apply_field_changes(self, colony: Colony, fields: dict[str, object]) -> None:
        """Apply field changes to a colony.

        Args:
            colony: The colony to update.
            fields: Dictionary of field names and values to apply.
        """
        for field, value in fields.items():
            if value is not None:
                setattr(colony, field, value)

    def _log_colony_update_audit(
        self,
        colony_id: int,
        changes: list[tuple[str, object, object]],
        changed_by: int,
    ) -> None:
        """Log audit entries for colony field updates.

        Args:
            colony_id: ID of the colony being updated.
            changes: List of (field, old_value, new_value) tuples.
            changed_by: User ID who made the changes.
        """
        for field, old_value, new_value in changes:
            self._log_audit(
                colony_id=colony_id,
                entity_type="colony",
                entity_id=colony_id,
                action=AuditLogAction.UPDATE,
                field=field,
                old_value=str(old_value) if old_value is not None else None,
                new_value=str(new_value),
                changed_by=changed_by,
            )

    def update_colony(
        self,
        colony_id: int,
        changed_by: int | None = None,
        **fields: object,
    ) -> Colony:
        """Update colony fields.

        Args:
            colony_id: The ID of the colony to update.
            changed_by: Optional user ID who made the change (for audit logging).
            **fields: Field names and values to update (e.g., representative_id=5).

        Returns:
            Updated colony.

        Raises:
            NotFoundError: If the colony does not exist.
        """
        colony = self._colony_repository.get(colony_id)
        if colony is None:
            raise NotFoundError(f"Colony {colony_id} not found")

        # Prepare and apply changes
        changes_to_log = []
        if self._audit_log_repository is not None and changed_by is not None:
            changes_to_log = self._prepare_audit_changes(colony, fields)

        self._apply_field_changes(colony, fields)
        result = self._colony_repository.update(colony)

        # Log audit entries for each changed field
        if (
            self._audit_log_repository is not None
            and changed_by is not None
            and result.id is not None
        ):
            self._log_colony_update_audit(result.id, changes_to_log, changed_by)

        return result

    def get_roll_status(self, colony_id: int) -> RollStatusDict:
        """
        Get the roll status for a colony (event and development rolls).

        Args:
            colony_id: The ID of the colony.

        Returns:
            Dict with keys:
                - event_roll_due: bool - whether an event roll is due now
                - development_roll_due: bool - whether a development roll is due now
                - days_since_event_roll: int - days since last event roll was due
                - days_until_event_roll: int - days until next event roll
                - days_since_development_roll: int - days since last dev roll was due
                - days_until_development_roll: int - days until next dev roll
                - event_interval_days: int - configured event roll interval
                - development_interval_days: int - configured development roll interval

        Raises:
            NotFoundError: If the colony does not exist.
        """
        colony = self._colony_repository.get(colony_id)
        if colony is None:
            raise NotFoundError(f"Colony {colony_id} not found")

        # Get intervals from config
        event_interval = self._rule_config_provider.get_event_roll_interval_days()
        development_interval = self._rule_config_provider.get_development_roll_interval_days()

        # Calculate roll timing
        cycle_info = colony.get_cycle_info(event_interval, development_interval)

        # A roll is "due" when days_since is 0 AND the colony is older than 0 days
        # (at age 0, no rolls are due yet - first rolls happen at interval milestones)
        event_roll_due = colony.age_days > 0 and cycle_info["days_since_event_roll"] == 0
        development_roll_due = (
            colony.age_days > 0 and cycle_info["days_since_development_roll"] == 0
        )

        return {
            "event_roll_due": event_roll_due,
            "development_roll_due": development_roll_due,
            "days_since_event_roll": cycle_info["days_since_event_roll"],
            "days_until_event_roll": cycle_info["days_until_event_roll"],
            "days_since_development_roll": cycle_info["days_since_development_roll"],
            "days_until_development_roll": cycle_info["days_until_development_roll"],
            "event_interval_days": event_interval,
            "development_interval_days": development_interval,
        }

    def get_modifier_breakdown(
        self, colony_id: int, as_of: date | None = None
    ) -> ModifierBreakdownDict:
        """
        Get detailed modifier breakdown grouped by stat for a colony.

        Args:
            colony_id: The ID of the colony.
            as_of: Date to check modifier expiry against. Defaults to today.

        Returns:
            Dict with modifier breakdown for each stat including:
            - base: Base stat value
            - modifiers: List of modifiers affecting this stat
            - total_modifier: Sum of all modifier values
            - current: Final calculated value (base + total_modifier)
            Also includes leadership_modifier and profit_factor.

        Raises:
            NotFoundError: If the colony does not exist.
        """
        colony = self._colony_repository.get(colony_id)
        if colony is None:
            raise NotFoundError(f"Colony {colony_id} not found")

        # Calculate full state first
        state = self._state_calculator.calculate(colony, as_of)
        # Collect ALL modifiers from all sources
        active_modifiers = self._state_calculator._get_active_modifiers(colony, as_of)
        active_modifiers.extend(self._state_calculator.get_infrastructure_modifiers(colony))
        active_modifiers.extend(self._state_calculator.get_support_upgrade_modifiers(colony))
        # Add representative personality modifiers if representative exists
        if colony.representative_id:
            rep = self._representative_repository.get(colony.representative_id)
            if rep:
                active_modifiers.extend(
                    get_personality_modifiers(
                        rep, colony.base_order, colony.base_size, colony.id or 1
                    )
                )

        # Group modifiers by stat
        from colony_manager.domain.enums import ModifierStat

        stat_modifiers: dict[ModifierStat, list[Modifier]] = {
            ModifierStat.SIZE: [],
            ModifierStat.COMPLACENCY: [],
            ModifierStat.ORDER: [],
            ModifierStat.PRODUCTIVITY: [],
            ModifierStat.PIETY: [],
        }

        for mod in active_modifiers:
            if mod.modifier_stat in stat_modifiers:
                stat_modifiers[mod.modifier_stat].append(mod)

        # Build base stat values (raw base stats from colony)
        # Note: current values may include conditional bonuses (Orderly, Pious)
        # which are not tied to specific modifiers
        base_size = colony.base_size
        base_complacency = colony.base_complacency
        base_order = colony.base_order
        base_productivity = colony.base_productivity
        base_piety = colony.base_piety

        current_size = int(state["size"])  # type: ignore[call-overload]
        current_complacency = int(state["complacency"])  # type: ignore[call-overload]
        current_order = int(state["order"])  # type: ignore[call-overload]
        current_productivity = int(state["productivity"])  # type: ignore[call-overload]
        current_piety = int(state["piety"])  # type: ignore[call-overload]

        return ModifierBreakdownDict(
            size=_build_stat_breakdown(
                ModifierStat.SIZE, base_size, current_size, stat_modifiers[ModifierStat.SIZE]
            ),
            complacency=_build_stat_breakdown(
                ModifierStat.COMPLACENCY,
                base_complacency,
                current_complacency,
                stat_modifiers[ModifierStat.COMPLACENCY],
            ),
            order=_build_stat_breakdown(
                ModifierStat.ORDER, base_order, current_order, stat_modifiers[ModifierStat.ORDER]
            ),
            productivity=_build_stat_breakdown(
                ModifierStat.PRODUCTIVITY,
                base_productivity,
                current_productivity,
                stat_modifiers[ModifierStat.PRODUCTIVITY],
            ),
            piety=_build_stat_breakdown(
                ModifierStat.PIETY, base_piety, current_piety, stat_modifiers[ModifierStat.PIETY]
            ),
            leadership_modifier=int(state["leadership_modifier"]),  # type: ignore[call-overload]
            profit_factor=int(state["profit_factor"]),  # type: ignore[call-overload]
        )
