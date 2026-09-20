"""Resource API schemas."""

from datetime import date

from pydantic import BaseModel, Field

from colony_manager.domain.enums import ResourceType


class ResourceCreate(BaseModel):
    """Schema for creating a new planetary resource."""

    resource_type: ResourceType
    name: str = Field(..., min_length=1, max_length=100)
    abundance: int = Field(..., ge=0)
    notes: str = ""


class ResourceUpdate(BaseModel):
    """Schema for updating a planetary resource (partial update)."""

    abundance: int | None = Field(default=None, ge=0)
    notes: str | None = None


class ResourceResponse(BaseModel):
    """Full resource response with computed fields."""

    id: int
    colony_id: int
    resource_type: ResourceType
    name: str
    abundance: int
    notes: str
    discovered_date: date
    abundance_level: str


class ResourceListItem(BaseModel):
    """Summary information for resource list."""

    id: int | None
    name: str
    resource_type: ResourceType
    abundance: int
    abundance_level: str
