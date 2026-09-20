"""Explicit import/export mapping helpers for save files."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from colony_manager.adapters.io.save_file_schema import (
    ColonySaveFile,
    SaveColonyUser,
    SaveDevelopmentPlan,
    SaveEvent,
    SaveEventModifier,
    SaveModifier,
    SavePersonality,
    SaveRepresentative,
    SaveRepresentativeStats,
    SaveSkill,
    SaveTalent,
)
from colony_manager.domain.enums import ColonyType
from colony_manager.domain.models.colony import Colony
from colony_manager.domain.models.colony_user import ColonyUser
from colony_manager.domain.models.development_plan import DevelopmentPlan, DevelopmentPlanStatus
from colony_manager.domain.models.event import Event, EventModifier
from colony_manager.domain.models.modifier import Modifier
from colony_manager.domain.models.personality import Personality, PersonalityEffect
from colony_manager.domain.models.representative import (
    Representative,
    RepresentativeStats,
    Skill,
    Talent,
)


def domain_to_save_file(
    colony: Colony,
    representative: Representative | None = None,
    events: list[Event] | None = None,
    development_plans: list[DevelopmentPlan] | None = None,
    colony_users: list[ColonyUser] | list[SaveColonyUser] | None = None,
) -> ColonySaveFile:
    """Convert domain models to save file schema."""
    return ColonySaveFile(
        name=colony.name,
        founder_name=colony.founder_name,
        patron_name=colony.patron_name,
        colony_type=colony.colony_type,
        age_days=colony.age_days,
        age_last_updated=colony.age_last_updated.isoformat(),
        current_event=colony.current_event,
        base_complacency=colony.base_complacency,
        base_order=colony.base_order,
        base_productivity=colony.base_productivity,
        base_piety=colony.base_piety,
        base_size=colony.base_size,
        representative_id=colony.representative_id,
        modifiers=[
            SaveModifier(
                modifier_source_type=modifier.modifier_source_type,
                modifier_category=modifier.modifier_category,
                modifier_stat=modifier.modifier_stat,
                modifier_value=modifier.modifier_value,
                modifier_description=modifier.modifier_description,
                is_active=modifier.is_active,
            )
            for modifier in colony.modifiers
        ],
        representative=None
        if representative is None
        else domain_to_save_representative(representative),
        events=[domain_to_save_event(e) for e in (events or [])],
        development_plans=[domain_to_save_plan(p) for p in (development_plans or [])],
        colony_users=[
            u if isinstance(u, SaveColonyUser) else domain_to_save_colony_user(u)
            for u in (colony_users or [])
        ],
    )


def save_file_to_domain(save_file: ColonySaveFile) -> dict[str, Any]:
    """Convert save file to domain models.

    Returns:
        Dictionary with 'colony', 'representative', 'events', 'development_plans', 'colony_users'
    """
    colony = Colony(
        name=save_file.name,
        founder_name=save_file.founder_name,
        patron_name=save_file.patron_name,
        colony_type=ColonyType(save_file.colony_type),
        age_days=save_file.age_days,
        age_last_updated=date.fromisoformat(save_file.age_last_updated),
        current_event=save_file.current_event,
        base_complacency=save_file.base_complacency,
        base_order=save_file.base_order,
        base_productivity=save_file.base_productivity,
        base_piety=save_file.base_piety,
        base_size=save_file.base_size,
        representative_id=save_file.representative_id,
        modifiers=[
            Modifier(
                colony_id=0,
                modifier_source_type=modifier.modifier_source_type,
                modifier_category=modifier.modifier_category,
                modifier_stat=modifier.modifier_stat,
                modifier_value=modifier.modifier_value,
                modifier_description=modifier.modifier_description,
                is_active=modifier.is_active,
            )
            for modifier in save_file.modifiers
        ],
    )
    representative = (
        None
        if save_file.representative is None
        else save_file_to_domain_representative(save_file.representative)
    )
    events = [save_file_to_domain_event(e) for e in save_file.events]
    development_plans = [save_file_to_domain_plan(p) for p in save_file.development_plans]
    colony_users = [save_file_to_domain_colony_user(u) for u in save_file.colony_users]

    return {
        "colony": colony,
        "representative": representative,
        "events": events,
        "development_plans": development_plans,
        "colony_users": colony_users,
    }


def domain_to_save_event(event: Event) -> SaveEvent:
    """Convert domain Event to save file schema."""
    return SaveEvent(
        name=event.name,
        description=event.description,
        is_active=event.is_active,
        modifiers=[
            SaveEventModifier(
                stat=mod.stat,
                value=mod.value,
                description=mod.description,
            )
            for mod in event.modifiers
        ],
        created_at=event.created_at.isoformat() if event.created_at else None,
    )


def save_file_to_domain_event(save_event: SaveEvent) -> Event:
    """Convert save file Event to domain model."""
    return Event(
        id=None,  # Will be assigned on import
        colony_id=0,  # Will be set by importer
        name=save_event.name,
        description=save_event.description,
        created_by=0,  # Will be set by importer
        created_at=datetime.fromisoformat(save_event.created_at) if save_event.created_at else None,
        is_active=save_event.is_active,
        modifiers=[
            EventModifier(
                stat=mod.stat,
                value=mod.value,
                description=mod.description,
            )
            for mod in save_event.modifiers
        ],
    )


def domain_to_save_plan(plan: DevelopmentPlan) -> SaveDevelopmentPlan:
    """Convert domain DevelopmentPlan to save file schema."""
    return SaveDevelopmentPlan(
        upgrade_type=plan.upgrade_type,
        target_type=plan.target_type,
        target_name=plan.target_name,
        priority=plan.priority,
        description=plan.description,
        notes=plan.notes,
        order=plan.order,
        status=plan.status.value,
        created_by=plan.created_by,
        created_at=plan.created_at.isoformat() if plan.created_at else None,
    )


def save_file_to_domain_plan(save_plan: SaveDevelopmentPlan) -> DevelopmentPlan:
    """Convert save file DevelopmentPlan to domain model."""
    return DevelopmentPlan(
        id=None,  # Will be assigned on import
        colony_id=0,  # Will be set by importer
        upgrade_type=save_plan.upgrade_type,
        target_type=save_plan.target_type,
        target_name=save_plan.target_name,
        priority=save_plan.priority,
        description=save_plan.description,
        notes=save_plan.notes,
        order=save_plan.order,
        status=DevelopmentPlanStatus(save_plan.status),
        created_by=save_plan.created_by,
        created_at=datetime.fromisoformat(save_plan.created_at) if save_plan.created_at else None,
    )


def domain_to_save_colony_user(colony_user: ColonyUser) -> SaveColonyUser:
    """Convert domain ColonyUser to save file schema."""
    return SaveColonyUser(
        user_id=colony_user.user_id,
        role=colony_user.role,
        joined_at=colony_user.joined_at.isoformat() if colony_user.joined_at else None,
    )


def save_file_to_domain_colony_user(save_user: SaveColonyUser) -> ColonyUser:
    """Convert save file ColonyUser to domain model."""
    return ColonyUser(
        id=None,  # Will be assigned on import
        colony_id=0,  # Will be set by importer
        user_id=save_user.user_id,
        role=save_user.role,
        joined_at=datetime.fromisoformat(save_user.joined_at)
        if save_user.joined_at
        else datetime.now(timezone(timedelta(hours=1))),
        invited_by=None,  # Not stored in save file
    )


def domain_to_save_representative(representative: Representative) -> SaveRepresentative:
    stats_payload = representative.stats.model_dump(by_alias=True)
    if "int_value" in stats_payload:
        stats_payload["int"] = stats_payload.pop("int_value")
    elif "int" not in stats_payload:
        stats_payload["int"] = None

    def personality_to_save(p: Personality) -> SavePersonality:
        # Convert list[PersonalityEffect] to dict[str, int]
        stat_effects_dict = {effect.stat: effect.value for effect in p.stat_effects}
        return SavePersonality(
            name=p.name,
            description=p.description,
            stat_effects=stat_effects_dict,
            calamitous_modifier=p.calamitous_modifier,
            special_rule=p.special_rule,
        )

    return SaveRepresentative(
        name=representative.name,
        type=representative.type,
        personalities=[personality_to_save(p) for p in representative.personalities],
        stats=SaveRepresentativeStats(**stats_payload),
        skills=[
            SaveSkill(name=skill.name, level=skill.level, description=skill.description)
            for skill in representative.skills
        ],
        talents=[SaveTalent(**talent.model_dump()) for talent in representative.talents],
    )


def save_file_to_domain_representative(representative: SaveRepresentative) -> Representative:
    stats_payload = representative.stats.model_dump(by_alias=True)
    if "int" in stats_payload:
        stats_payload["int"] = stats_payload.pop("int")
    if "int_value" in stats_payload:
        stats_payload["int"] = stats_payload.pop("int_value")

    def save_to_personality(p: SavePersonality) -> Personality:
        # Convert dict[str, int] to list[PersonalityEffect]
        stat_effects_list = [
            PersonalityEffect(stat=stat, value=value) for stat, value in p.stat_effects.items()
        ]
        return Personality(
            name=p.name,
            description=p.description,
            stat_effects=stat_effects_list,
            calamitous_modifier=p.calamitous_modifier,
            special_rule=p.special_rule,
        )

    return Representative(
        name=representative.name,
        type=representative.type,
        personalities=[save_to_personality(p) for p in representative.personalities],
        stats=RepresentativeStats(**stats_payload),
        skills=[
            Skill(name=skill.name, level=skill.level, description=skill.description)
            for skill in representative.skills
        ],
        talents=[Talent(**talent.model_dump()) for talent in representative.talents],
    )
