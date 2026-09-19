"""Infrastructure API router."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from colony_manager.adapters.api import dependencies
from colony_manager.adapters.api.middleware.permissions import require_colony_permission
from colony_manager.adapters.api.schemas.common import PaginatedResponse, PaginationMeta
from colony_manager.adapters.api.schemas.infrastructure import (
    InfrastructureCreate,
    InfrastructureListItem,
    InfrastructureResponse,
    InfrastructureUpdate,
    InfrastructureValidationResponse,
)
from colony_manager.adapters.persistence.colony_repository_impl import SqlAlchemyColonyRepository
from colony_manager.adapters.persistence.infrastructure_repository_impl import (
    SqlAlchemyInfrastructureRepository,
)
from colony_manager.application.services.infrastructure_service import InfrastructureService
from colony_manager.domain.enums import InfrastructureState, InfrastructureType
from colony_manager.domain.errors import NotFoundError
from colony_manager.domain.models.user import User

router = APIRouter(prefix="/colonies/{colony_id}/infrastructure", tags=["infrastructure"])


def get_infrastructure_service(
    colony_id: int, db_path: str = Depends(dependencies.get_db_path)
) -> InfrastructureService:
    """Get infrastructure service instance with proper repositories."""
    from colony_manager.adapters.persistence.db import build_database_url

    db_url = build_database_url(db_path)
    colony_repo = SqlAlchemyColonyRepository(db_url)
    infra_repo = SqlAlchemyInfrastructureRepository(db_url)
    return InfrastructureService(infra_repo, colony_repo)


def _check_colony_exists(service: InfrastructureService, colony_id: int) -> None:
    """Check if colony exists, raise HTTPException if not."""
    if not service.colony_exists(colony_id):
        raise HTTPException(status_code=404, detail=f"Colony {colony_id} not found")


@router.get(
    "",
    response_model=PaginatedResponse[InfrastructureListItem],
    responses={404: {"description": "Colony not found"}},
)
async def list_infrastructure(
    colony_id: int,
    current_user: Annotated[User, Depends(require_colony_permission("view"))],
    service: InfrastructureService = Depends(get_infrastructure_service),
    state_filter: InfrastructureState | None = Query(
        default=None,
        alias="state",
        description="Filter by infrastructure state",
        examples=["working", "planned", "in_progress", "needed", "not_working"],
    ),
    type_filter: InfrastructureType | None = Query(
        default=None,
        alias="type",
        description="Filter by infrastructure type",
        examples=["transport", "power", "housing", "life_support", "defense", "production"],
    ),
    name_search: str | None = Query(
        default=None,
        description="Search by name (case-insensitive substring match)",
        examples=["spaceport", "reactor"],
    ),
    offset: int = Query(default=0, ge=0, description="Number of items to skip"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum number of items to return"),
) -> PaginatedResponse[InfrastructureListItem]:
    """List all infrastructure for a colony with pagination and filtering.

    Filters:
    - state: Filter by operational state (working, planned, in_progress, needed, not_working)
    - type: Filter by infrastructure type (transport, power, housing, etc.)
    - search: Search by name (case-insensitive substring match)

    Note: Filters are applied in-memory after loading all items. This is acceptable
    for typical colony sizes (<100 items). For colonies with >1000 infrastructure
    items, consider adding filtered query methods to the repository layer to push
    filtering to the database.
    """
    _check_colony_exists(service, colony_id)
    all_infrastructure = service.list_by_colony(colony_id)

    filtered = all_infrastructure

    if state_filter is not None:
        filtered = [i for i in filtered if i.state == state_filter]

    if type_filter is not None:
        filtered = [i for i in filtered if i.infrastructure_type == type_filter]

    if name_search is not None:
        search_lower = name_search.lower()
        filtered = [i for i in filtered if search_lower in i.name.lower()]

    # Calculate pagination
    total = len(filtered)
    items = filtered[offset : offset + limit]

    return PaginatedResponse(
        items=[
            InfrastructureListItem(
                id=infra.id,
                name=infra.name,
                infrastructure_type=infra.infrastructure_type,
                state=infra.state,
                has_effect=infra.has_effect,
                is_working=infra.is_working,
                is_not_working=infra.is_not_working,
            )
            for infra in items
        ],
        meta=PaginationMeta(
            total=total,
            offset=offset,
            limit=limit,
            has_more=(offset + limit) < total,
        ),
    )


@router.post(
    "",
    response_model=InfrastructureResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"description": "Colony not found"}},
)
async def create_infrastructure(
    colony_id: int,
    infra_data: InfrastructureCreate,
    current_user: Annotated[User, Depends(require_colony_permission("edit"))],
    service: InfrastructureService = Depends(get_infrastructure_service),
) -> InfrastructureResponse:
    """Add new infrastructure to a colony."""
    _check_colony_exists(service, colony_id)
    from colony_manager.domain.models.infrastructure import Infrastructure

    infrastructure = Infrastructure(
        colony_id=colony_id,
        name=infra_data.name,
        infrastructure_type=infra_data.infrastructure_type,
        state=infra_data.state,
        notes=infra_data.notes,
    )
    created = service.create_infrastructure(infrastructure)
    assert created.id is not None
    return InfrastructureResponse(
        id=created.id,
        colony_id=colony_id,
        name=created.name,
        infrastructure_type=created.infrastructure_type,
        state=created.state,
        notes=created.notes,
        has_effect=created.has_effect,
        is_working=created.is_working,
        is_not_working=created.is_not_working,
    )


@router.get(
    "/{infrastructure_id}",
    response_model=InfrastructureResponse,
    responses={404: {"description": "Colony or infrastructure not found"}},
)
async def get_infrastructure(
    colony_id: int,
    infrastructure_id: int,
    current_user: Annotated[User, Depends(require_colony_permission("view"))],
    service: InfrastructureService = Depends(get_infrastructure_service),
) -> InfrastructureResponse:
    """Get a specific infrastructure by ID."""
    _check_colony_exists(service, colony_id)
    try:
        infrastructure = service.get_infrastructure(infrastructure_id)
        if infrastructure.colony_id != colony_id:
            raise HTTPException(
                status_code=404,
                detail=f"Infrastructure {infrastructure_id} not found in colony {colony_id}",
            )
        assert infrastructure.id is not None
        return InfrastructureResponse(
            id=infrastructure.id,
            colony_id=infrastructure.colony_id,
            name=infrastructure.name,
            infrastructure_type=infrastructure.infrastructure_type,
            state=infrastructure.state,
            notes=infrastructure.notes,
            has_effect=infrastructure.has_effect,
            is_working=infrastructure.is_working,
            is_not_working=infrastructure.is_not_working,
        )
    except NotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Infrastructure {infrastructure_id} not found",
        ) from None


@router.patch(
    "/{infrastructure_id}",
    response_model=InfrastructureResponse | InfrastructureValidationResponse,
    summary="Update infrastructure",
    description=(
        "Update infrastructure name, notes, or state. Use `validate_only=true` "
        "to preview effects without applying."
    ),
    responses={404: {"description": "Colony or infrastructure not found"}},
)
async def update_infrastructure(
    colony_id: int,
    infrastructure_id: int,
    infra_data: InfrastructureUpdate,
    current_user: Annotated[User, Depends(require_colony_permission("edit"))],
    validate_only: bool = Query(False, description="If true, preview changes without applying"),
    service: InfrastructureService = Depends(get_infrastructure_service),
) -> InfrastructureResponse | InfrastructureValidationResponse:
    """Update infrastructure name, notes, or state."""
    _check_colony_exists(service, colony_id)
    try:
        infrastructure = service.get_infrastructure(infrastructure_id)

        if infrastructure.colony_id != colony_id:
            raise HTTPException(
                status_code=404,
                detail=f"Infrastructure {infrastructure_id} not found in colony {colony_id}",
            )

        # If validate_only, return preview of changes
        if validate_only:
            preview_result = service.preview_state_transition(
                infrastructure_id, infra_data.state or infrastructure.state
            )
            return InfrastructureValidationResponse(
                valid=preview_result["valid"],
                current_state=preview_result["current_state"],
                requested_state=preview_result["requested_state"],
                modifiers_preview=preview_result["modifiers_preview"],
                would_apply_penalty=preview_result["would_apply_penalty"],
                penalty_description=preview_result["penalty_description"],
            )

        # Build update data dict for batch update
        update_data = {}
        if infra_data.name is not None:
            update_data["name"] = infra_data.name
        if infra_data.notes is not None:
            update_data["notes"] = infra_data.notes
        if infra_data.state is not None:
            update_data["state"] = infra_data.state

        # Apply batch update
        infrastructure = service.update_infrastructure_batch(
            infrastructure_id, update_data, changed_by=current_user.id
        )

        assert infrastructure.id is not None
        return InfrastructureResponse(
            id=infrastructure.id,
            colony_id=infrastructure.colony_id,
            name=infrastructure.name,
            infrastructure_type=infrastructure.infrastructure_type,
            state=infrastructure.state,
            notes=infrastructure.notes,
            has_effect=infrastructure.has_effect,
            is_working=infrastructure.is_working,
            is_not_working=infrastructure.is_not_working,
        )
    except NotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Infrastructure {infrastructure_id} not found",
        ) from None


@router.delete(
    "/{infrastructure_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": "Colony or infrastructure not found"}},
)
async def delete_infrastructure(
    colony_id: int,
    infrastructure_id: int,
    current_user: Annotated[User, Depends(require_colony_permission("admin"))],
    service: InfrastructureService = Depends(get_infrastructure_service),
) -> None:
    """Remove infrastructure from a colony."""
    _check_colony_exists(service, colony_id)
    try:
        infrastructure = service.get_infrastructure(infrastructure_id)
        if infrastructure.colony_id != colony_id:
            raise HTTPException(
                status_code=404,
                detail=f"Infrastructure {infrastructure_id} not found in colony {colony_id}",
            )
        service.delete_infrastructure(infrastructure_id)
    except NotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Infrastructure {infrastructure_id} not found",
        ) from None
