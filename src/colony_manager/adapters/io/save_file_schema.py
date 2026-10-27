"""Portable save-file schema for colony data."""

from __future__ import annotations

from pydantic import BaseModel, Field

from colony_manager.domain.enums import (
    ModifierCategory,
    ModifierSourceType,
    ModifierStat,
    RepresentativeType,
    SkillLevel,
)
from colony_manager.domain.models.colony_user import ColonyUserRole


class SaveModifier(BaseModel):
    modifier_source_type: ModifierSourceType
    modifier_category: ModifierCategory
    modifier_stat: ModifierStat
    modifier_value: int
    modifier_description: str
    is_active: bool = True


class SaveEventModifier(BaseModel):
    """Schema for event modifiers in save files."""

    stat: ModifierStat
    value: int
    description: str


class SaveEvent(BaseModel):
    """Schema for events in save files."""

    name: str
    description: str
    is_active: bool = True
    modifiers: list[SaveEventModifier] = Field(default_factory=list)
    created_at: str | None = None


class SaveDevelopmentPlan(BaseModel):
    """Schema for development plans in save files."""

    upgrade_type: str
    target_type: str
    target_name: str
    priority: int
    description: str
    notes: str = ""
    order: int = 0
    status: str
    created_by: int
    created_at: str | None = None


class SaveColonyUser(BaseModel):
    """Schema for colony users in save files."""

    user_id: int
    username: str | None = None
    role: ColonyUserRole
    joined_at: str | None = None


class SaveRepresentativeStats(BaseModel):
    ws: int = Field(gt=0)
    bs: int = Field(gt=0)
    s: int = Field(gt=0)
    t: int = Field(gt=0)
    ag: int = Field(gt=0)
    int_value: int = Field(gt=0, alias="int")
    per: int = Field(gt=0)
    wp: int = Field(gt=0)
    fel: int = Field(gt=0)

    model_config = {"populate_by_name": True}


class SavePersonality(BaseModel):
    name: str
    description: str
    stat_effects: dict[str, int] = Field(default_factory=dict)
    calamitous_modifier: int = 0
    special_rule: str | None = None


class SaveSkill(BaseModel):
    name: str
    level: SkillLevel
    description: str


class SaveTalent(BaseModel):
    name: str
    description: str


class SaveRepresentative(BaseModel):
    name: str
    type: RepresentativeType
    personalities: list[SavePersonality]
    stats: SaveRepresentativeStats
    skills: list[SaveSkill] = Field(default_factory=list)
    talents: list[SaveTalent] = Field(default_factory=list)


class ColonySaveFile(BaseModel):
    """Complete colony save file schema including all related data."""

    name: str
    founder_name: str
    patron_name: str | None = None
    star_system: str | None = None
    colony_type: str
    age_days: int = Field(ge=0)
    age_last_updated: str
    current_event: str | None = None
    base_complacency: int
    base_order: int
    base_productivity: int
    base_piety: int
    base_size: int
    representative_id: int | None = None
    modifiers: list[SaveModifier] = Field(default_factory=list)
    representative: SaveRepresentative | None = None
    events: list[SaveEvent] = Field(default_factory=list)
    development_plans: list[SaveDevelopmentPlan] = Field(default_factory=list)
    colony_users: list[SaveColonyUser] = Field(default_factory=list)
