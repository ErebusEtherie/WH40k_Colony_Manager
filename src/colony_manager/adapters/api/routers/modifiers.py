"""Modifier API router.

Note: Modifiers are managed through the colonies router since they are
owned by colonies. This router provides a top-level view of all modifiers.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from colony_manager.adapters.api.dependencies import get_colony_service
from colony_manager.adapters.api.middleware.auth import require_role
from colony_manager.adapters.api.schemas.common import PaginatedResponse, PaginationMeta
from colony_manager.adapters.api.schemas.modifier import ModifierListItem, ModifierResponse
from colony_manager.application.services.colony_service import ColonyService
from colony_manager.domain.models.user import User

router = APIRouter(prefix="/modifiers", tags=["modifiers"])


@router.get("", response_model=PaginatedResponse[ModifierListItem])
async def list_all_modifiers(
    current_user: Annotated[User, Depends(require_role("admin"))],
    service: ColonyService = Depends(get_colony_service),
    offset: int = Query(default=0, ge=0, description="Number of items to skip"),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum number of items to return"),
    colony_id: int | None = Query(default=None, description="Filter by colony ID"),
    is_active: bool | None = Query(default=None, description="Filter by active status"),
) -> PaginatedResponse[ModifierListItem]:
    """List all modifiers across all colonies with pagination.

    Optional filters:
    - colony_id: Filter modifiers by specific colony
    - is_active: Filter by active status (true/false)

    Note: This endpoint loads all modifiers into memory before applying pagination.
    For large datasets, consider implementing repository-level pagination in the future.
    """
    colonies = service._colony_repository.list()
    all_modifiers = []
    for colony in colonies:
        assert colony.id is not None

        # Filter by colony_id if provided
        if colony_id is not None and colony.id != colony_id:
            continue

        for mod in colony.modifiers:
            # Filter by is_active if provided
            if is_active is not None and mod.is_active != is_active:
                continue

            all_modifiers.append(
                ModifierListItem(
                    id=mod.id,
                    colony_id=colony.id,
                    modifier_source_type=mod.modifier_source_type,
                    modifier_category=mod.modifier_category,
                    modifier_stat=mod.modifier_stat,
                    modifier_value=mod.modifier_value,
                    is_active=mod.is_active,
                )
            )

    # Apply pagination
    total = len(all_modifiers)
    items = all_modifiers[offset : offset + limit]

    return PaginatedResponse(
        items=items,
        meta=PaginationMeta(
            total=total,
            offset=offset,
            limit=limit,
            has_more=(offset + limit) < total,
        ),
    )


@router.get(
    "/{modifier_id}",
    response_model=ModifierResponse,
    responses={404: {"description": "Modifier not found"}},
)
async def get_modifier(
    modifier_id: int,
    current_user: Annotated[User, Depends(require_role("admin"))],
    service: ColonyService = Depends(get_colony_service),
) -> ModifierResponse:
    """Get a specific modifier by ID (searches across all colonies)."""
    colonies = service._colony_repository.list()
    for colony in colonies:
        assert colony.id is not None
        for mod in colony.modifiers:
            if mod.id == modifier_id:
                return ModifierResponse(
                    id=mod.id,
                    colony_id=colony.id,
                    modifier_source_type=mod.modifier_source_type,
                    modifier_category=mod.modifier_category,
                    modifier_stat=mod.modifier_stat,
                    modifier_value=mod.modifier_value,
                    modifier_description=mod.modifier_description,
                    is_active=mod.is_active,
                    expires_at=mod.expires_at,
                )
    raise HTTPException(status_code=404, detail=f"Modifier {modifier_id} not found")
