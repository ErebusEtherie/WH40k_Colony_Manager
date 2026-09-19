"""Pydantic schemas for development plan API requests and responses."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class DevelopmentPlanStatusEnum(StrEnum):
    """Enum for development plan status."""

    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    ACQUIRED = "acquired"
    DELIVERED = "delivered"


class DevelopmentPlanCreate(BaseModel):
    """Schema for creating a development plan."""

    upgrade_type: str = Field(pattern=r"^(infrastructure|support_upgrade)$")
    target_type: str = Field(min_length=1, max_length=100)
    target_name: str = Field(min_length=1, max_length=200)
    priority: int = Field(ge=1, le=5, default=1)
    description: str = Field(min_length=1, max_length=2000)
    notes: str = Field(default="", max_length=2000)
    order: int = Field(default=0)


class DevelopmentPlanUpdate(BaseModel):
    """Schema for updating a development plan."""

    upgrade_type: str | None = Field(default=None, pattern=r"^(infrastructure|support_upgrade)$")
    target_type: str | None = Field(default=None, min_length=1, max_length=100)
    target_name: str | None = Field(default=None, min_length=1, max_length=200)
    priority: int | None = Field(default=None, ge=1, le=5)
    description: str | None = Field(default=None, min_length=1, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)
    order: int | None = Field(default=None)
    status: DevelopmentPlanStatusEnum | None = None


class DevelopmentPlanResponse(BaseModel):
    """Schema for development plan response."""

    id: int
    colony_id: int
    upgrade_type: str
    target_type: str
    target_name: str
    priority: int
    description: str
    notes: str
    order: int
    status: str
    created_by: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DevelopmentPlanListItem(BaseModel):
    """Lightweight schema for development plan list items."""

    id: int
    colony_id: int
    upgrade_type: str
    target_type: str
    target_name: str
    priority: int
    order: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class InstallationResult(BaseModel):
    """Response for installing a development plan."""

    plan_id: int
    plan_name: str
    plan_target_type: str
    installed_type: str
    installed_id: int
    installed_data: dict[str, Any]
