"""Mapping helpers between domain models and ORM models."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta, timezone

from colony_manager.adapters.persistence.orm_models import (
    AuditLogORM,
    ColonyORM,
    ColonyUserORM,
    DevelopmentPlanORM,
    EventModifierORM,
    EventORM,
    InfrastructureORM,
    ModifierORM,
    RepresentativeORM,
    SupportUpgradeORM,
    UserORM,
)
from colony_manager.domain.enums import (
    ColonyType,
    ModifierCategory,
    ModifierSourceType,
    ModifierStat,
    RepresentativeType,
    SkillLevel,
)
from colony_manager.domain.models.audit_log import AuditLog, AuditLogAction
from colony_manager.domain.models.colony import Colony
from colony_manager.domain.models.colony_user import ColonyUser, ColonyUserRole
from colony_manager.domain.models.development_plan import DevelopmentPlan, DevelopmentPlanStatus
from colony_manager.domain.models.event import Event, EventModifier
from colony_manager.domain.models.infrastructure import Infrastructure
from colony_manager.domain.models.modifier import Modifier
from colony_manager.domain.models.personality import Personality
from colony_manager.domain.models.representative import (
    Representative,
    RepresentativeStats,
    Skill,
    Talent,
)
from colony_manager.domain.models.support_upgrade import SupportUpgrade
from colony_manager.domain.models.user import User, UserRole


def orm_to_domain_colony(orm: ColonyORM) -> Colony:
    import json

    from colony_manager.domain.enums import DynastyOutcome, ResourceType

    # Parse planetary_resources from JSON
    planetary_resources = []
    if orm.planetary_resources:
        try:
            resource_strings = json.loads(orm.planetary_resources)
            planetary_resources = [ResourceType(r) for r in resource_strings]
        except (json.JSONDecodeError, ValueError):
            planetary_resources = []

    # Parse dynasty_outcome
    dynasty_outcome = None
    if orm.dynasty_outcome:
        try:
            dynasty_outcome = DynastyOutcome(orm.dynasty_outcome)
        except ValueError:
            dynasty_outcome = None

    return Colony(
        id=orm.id,
        name=orm.name,
        founder_name=orm.founder_name,
        patron_name=orm.patron_name,
        colony_type=ColonyType(orm.colony_type),
        age_days=orm.age_days,
        age_last_updated=orm.age_last_updated,
        current_event=orm.current_event,
        base_complacency=orm.base_complacency,
        base_order=orm.base_order,
        base_productivity=orm.base_productivity,
        base_piety=orm.base_piety,
        base_size=orm.base_size,
        representative_id=orm.representative_id,
        dynasty_outcome=dynasty_outcome,
        complacency_locked=orm.complacency_locked,
        order_locked=orm.order_locked,
        productivity_locked=orm.productivity_locked,
        planetary_resources=planetary_resources,
        modifiers=[orm_to_domain_modifier(modifier) for modifier in orm.modifiers],
        infrastructure=[orm_to_domain_infrastructure(inf) for inf in orm.infrastructure],
        support_upgrades=[orm_to_domain_support_upgrade(upg) for upg in orm.support_upgrades],
    )


def domain_to_orm_colony(domain: Colony) -> ColonyORM:
    import json

    # Serialize planetary_resources to JSON
    planetary_resources_json = None
    if domain.planetary_resources:
        planetary_resources_json = json.dumps([r.value for r in domain.planetary_resources])

    return ColonyORM(
        id=domain.id,
        name=domain.name,
        founder_name=domain.founder_name,
        patron_name=domain.patron_name,
        colony_type=domain.colony_type.value,
        age_days=domain.age_days,
        age_last_updated=domain.age_last_updated,
        current_event=domain.current_event,
        base_complacency=domain.base_complacency,
        base_order=domain.base_order,
        base_productivity=domain.base_productivity,
        base_piety=domain.base_piety,
        base_size=domain.base_size,
        representative_id=domain.representative_id,
        dynasty_outcome=domain.dynasty_outcome.value if domain.dynasty_outcome else None,
        complacency_locked=domain.complacency_locked,
        order_locked=domain.order_locked,
        productivity_locked=domain.productivity_locked,
        planetary_resources=planetary_resources_json,
        modifiers=[domain_to_orm_modifier(modifier) for modifier in domain.modifiers],
        infrastructure=[domain_to_orm_infrastructure(inf) for inf in domain.infrastructure],
        support_upgrades=[domain_to_orm_support_upgrade(upg) for upg in domain.support_upgrades],
    )


def orm_to_domain_representative(orm: RepresentativeORM) -> Representative:
    """Convert a RepresentativeORM to a Representative domain model.

    Args:
        orm: The SQLAlchemy ORM model instance.

    Returns:
        The corresponding domain Representative object.
    """
    return Representative(
        id=orm.id,
        name=orm.name,
        type=RepresentativeType(orm.type),
        personalities=[Personality(**item) for item in json.loads(orm.personalities)],
        stats=RepresentativeStats(**json.loads(orm.stats)),
        skills=[
            Skill(
                name=item["name"], level=SkillLevel(item["level"]), description=item["description"]
            )
            for item in json.loads(orm.skills)
        ],
        talents=[Talent(**item) for item in json.loads(orm.talents)],
        assigned_to_colony_id=orm.assigned_to_colony_id,
    )


def domain_to_orm_representative(domain: Representative) -> RepresentativeORM:
    """Convert a Representative domain model to a RepresentativeORM.

    Args:
        domain: The domain Representative object.

    Returns:
        The corresponding SQLAlchemy ORM model instance.
    """
    return RepresentativeORM(
        id=domain.id,
        name=domain.name,
        type=domain.type.value,
        personalities=json.dumps([item.model_dump() for item in domain.personalities]),
        stats=json.dumps(domain.stats.model_dump()),
        skills=json.dumps(
            [
                {"name": item.name, "level": item.level.value, "description": item.description}
                for item in domain.skills
            ]
        ),
        talents=json.dumps([item.model_dump() for item in domain.talents]),
        assigned_to_colony_id=domain.assigned_to_colony_id,
    )


def orm_to_domain_modifier(orm: ModifierORM) -> Modifier:
    return Modifier(
        id=orm.id,
        colony_id=orm.colony_id,
        modifier_source_type=ModifierSourceType(orm.modifier_source_type),
        modifier_category=ModifierCategory(orm.modifier_category),
        modifier_stat=ModifierStat(orm.modifier_stat),
        modifier_value=orm.modifier_value,
        modifier_description=orm.modifier_description,
        is_active=orm.is_active,
        expires_at=orm.expires_at,
        source_entity_id=orm.source_entity_id,
    )


def domain_to_orm_modifier(domain: Modifier) -> ModifierORM:
    return ModifierORM(
        id=domain.id,
        colony_id=domain.colony_id,
        modifier_source_type=domain.modifier_source_type.value,
        modifier_category=domain.modifier_category.value,
        modifier_stat=domain.modifier_stat.value,
        modifier_value=domain.modifier_value,
        modifier_description=domain.modifier_description,
        is_active=domain.is_active,
        expires_at=domain.expires_at,
        source_entity_id=domain.source_entity_id,
    )


def orm_to_domain_infrastructure(orm: InfrastructureORM) -> Infrastructure:
    from colony_manager.domain.enums import InfrastructureState, InfrastructureType

    return Infrastructure(
        id=orm.id,
        colony_id=orm.colony_id,
        name=orm.name,
        infrastructure_type=InfrastructureType(orm.infrastructure_type),
        state=InfrastructureState(orm.state),
        notes=orm.notes or "",
    )


def domain_to_orm_infrastructure(domain: Infrastructure) -> InfrastructureORM:
    return InfrastructureORM(
        id=domain.id,
        colony_id=domain.colony_id,
        name=domain.name,
        infrastructure_type=domain.infrastructure_type.value,
        state=domain.state.value,
        notes=domain.notes,
    )


def orm_to_domain_support_upgrade(orm: SupportUpgradeORM) -> SupportUpgrade:
    from colony_manager.domain.enums import ModifierStat, SupportUpgradeType

    return SupportUpgrade(
        id=orm.id,
        colony_id=orm.colony_id,
        name=orm.name,
        upgrade_type=SupportUpgradeType(orm.upgrade_type),
        custom_stat_choice=ModifierStat(orm.custom_stat_choice) if orm.custom_stat_choice else None,
        custom_product=orm.custom_product,
        affiliated_group=orm.affiliated_group,
        notes=orm.notes or "",
    )


def domain_to_orm_support_upgrade(domain: SupportUpgrade) -> SupportUpgradeORM:
    return SupportUpgradeORM(
        id=domain.id,
        colony_id=domain.colony_id,
        name=domain.name,
        upgrade_type=domain.upgrade_type.value,
        custom_stat_choice=domain.custom_stat_choice.value if domain.custom_stat_choice else None,
        custom_product=domain.custom_product,
        affiliated_group=domain.affiliated_group,
        notes=domain.notes,
    )


def orm_to_domain_user(orm: UserORM) -> User:
    """Convert a UserORM to a User domain model.

    Args:
        orm: The SQLAlchemy ORM model instance.

    Returns:
        The corresponding domain User object.
    """

    return User(
        id=orm.id,
        username=orm.username,
        email=orm.email,
        password_hash=orm.password_hash,
        role=UserRole(orm.role),
        is_active=orm.is_active,
        created_at=datetime.combine(orm.created_at, datetime.min.time())
        if orm.created_at
        else None,
        updated_at=datetime.combine(orm.updated_at, datetime.min.time())
        if orm.updated_at
        else None,
    )


def domain_to_orm_user(domain: User) -> UserORM:
    """Convert a User domain model to a UserORM.

    Args:
        domain: The domain User object.

    Returns:
        The corresponding SQLAlchemy ORM model instance.
    """
    from datetime import date

    return UserORM(
        id=domain.id,
        username=domain.username,
        email=domain.email,
        password_hash=domain.password_hash,
        role=domain.role.value if hasattr(domain.role, "value") else domain.role,
        is_active=domain.is_active,
        created_at=date(domain.created_at.year, domain.created_at.month, domain.created_at.day)
        if domain.created_at
        else None,
        updated_at=date(domain.updated_at.year, domain.updated_at.month, domain.updated_at.day)
        if domain.updated_at
        else None,
    )


# Phase 4+ mappers - Event


def orm_to_domain_event(orm: EventORM) -> Event:
    """Convert an EventORM to an Event domain model."""

    return Event(
        id=orm.id,
        colony_id=orm.colony_id,
        name=orm.name,
        description=orm.description,
        created_by=orm.created_by,
        created_at=datetime.combine(orm.created_at, datetime.min.time())
        if orm.created_at
        else None,
        is_active=orm.is_active,
        modifiers=[orm_to_domain_event_modifier(mod) for mod in orm.modifiers],
    )


def domain_to_orm_event(domain: Event) -> EventORM:
    """Convert an Event domain model to an EventORM."""
    from datetime import date

    orm = EventORM(
        id=domain.id,
        colony_id=domain.colony_id,
        name=domain.name,
        description=domain.description,
        created_by=domain.created_by,
        created_at=date(domain.created_at.year, domain.created_at.month, domain.created_at.day)
        if domain.created_at
        else None,
        is_active=domain.is_active,
    )
    # Add modifiers to the ORM event
    for modifier in domain.modifiers:
        orm.modifiers.append(domain_to_orm_event_modifier(modifier))
    return orm


def orm_to_domain_event_modifier(orm: EventModifierORM) -> EventModifier:
    """Convert an EventModifierORM to an EventModifier domain model."""
    return EventModifier(
        stat=ModifierStat(orm.stat),
        value=orm.value,
        description=orm.description,
    )


def domain_to_orm_event_modifier(domain: EventModifier) -> EventModifierORM:
    """Convert an EventModifier domain model to an EventModifierORM."""
    return EventModifierORM(
        stat=domain.stat.value,
        value=domain.value,
        description=domain.description,
    )


# Phase 4+ mappers - Development Plan


def orm_to_domain_development_plan(orm: DevelopmentPlanORM) -> DevelopmentPlan:
    """Convert a DevelopmentPlanORM to a DevelopmentPlan domain model."""
    return DevelopmentPlan(
        id=orm.id,
        colony_id=orm.colony_id,
        upgrade_type=orm.upgrade_type,
        target_type=orm.target_type,
        target_name=orm.target_name,
        priority=orm.priority,
        description=orm.description,
        notes=orm.notes or "",
        order=orm.order,
        status=DevelopmentPlanStatus(orm.status),
        created_by=orm.created_by,
        created_at=orm.created_at,
    )


def domain_to_orm_development_plan(domain: DevelopmentPlan) -> DevelopmentPlanORM:
    """Convert a DevelopmentPlan domain model to a DevelopmentPlanORM."""
    return DevelopmentPlanORM(
        id=domain.id,
        colony_id=domain.colony_id,
        upgrade_type=domain.upgrade_type,
        target_type=domain.target_type,
        target_name=domain.target_name,
        priority=domain.priority,
        description=domain.description,
        notes=domain.notes,
        order=domain.order,
        status=domain.status.value if hasattr(domain.status, "value") else domain.status,
        created_by=domain.created_by,
        created_at=domain.created_at,
    )


# Phase 4+ mappers - Audit Log


def orm_to_domain_audit_log(orm: AuditLogORM) -> AuditLog:
    """Convert an AuditLogORM to an AuditLog domain model."""

    return AuditLog(
        id=orm.id,
        entity_type=orm.entity_type,
        entity_id=orm.entity_id,
        action=AuditLogAction(orm.action),
        field=orm.field,
        old_value=orm.old_value,
        new_value=orm.new_value,
        changed_by=orm.changed_by,
        changed_at=datetime.combine(orm.changed_at, datetime.min.time()).replace(tzinfo=UTC)
        if orm.changed_at
        else datetime.now(UTC),
        colony_id=orm.colony_id,
    )


def domain_to_orm_audit_log(domain: AuditLog) -> AuditLogORM:
    """Convert an AuditLog domain model to an AuditLogORM."""
    from datetime import date

    return AuditLogORM(
        id=domain.id,
        entity_type=domain.entity_type,
        entity_id=domain.entity_id,
        action=domain.action.value if hasattr(domain.action, "value") else domain.action,
        field=domain.field,
        old_value=domain.old_value,
        new_value=domain.new_value,
        changed_by=domain.changed_by,
        changed_at=date(domain.changed_at.year, domain.changed_at.month, domain.changed_at.day)
        if domain.changed_at
        else None,
        colony_id=domain.colony_id,
    )


# Phase 4+ mappers - Colony User


def orm_to_domain_colony_user(orm: ColonyUserORM) -> ColonyUser:
    """Convert a ColonyUserORM to a ColonyUser domain model."""

    return ColonyUser(
        id=orm.id,
        colony_id=orm.colony_id,
        user_id=orm.user_id,
        role=ColonyUserRole(orm.role),
        joined_at=datetime.combine(orm.joined_at, datetime.min.time()).replace(
            tzinfo=timezone(timedelta(hours=1))
        )
        if orm.joined_at
        else datetime.now(timezone(timedelta(hours=1))),
        invited_by=orm.invited_by,
    )


def domain_to_orm_colony_user(domain: ColonyUser) -> ColonyUserORM:
    """Convert a ColonyUser domain model to a ColonyUserORM."""
    from datetime import date

    return ColonyUserORM(
        id=domain.id,
        colony_id=domain.colony_id,
        user_id=domain.user_id,
        role=domain.role.value if hasattr(domain.role, "value") else domain.role,
        joined_at=date(domain.joined_at.year, domain.joined_at.month, domain.joined_at.day)
        if domain.joined_at
        else None,
        invited_by=domain.invited_by,
    )
