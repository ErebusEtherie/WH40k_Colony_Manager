"""API router for development plan endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from colony_manager.adapters.api import dependencies
from colony_manager.adapters.api.middleware.auth import get_current_user_from_cookie, require_role
from colony_manager.adapters.api.schemas.common import PaginatedResponse, PaginationMeta
from colony_manager.adapters.api.schemas.development_plan import (
    DevelopmentPlanCreate,
    DevelopmentPlanResponse,
    DevelopmentPlanStatusEnum,
    DevelopmentPlanUpdate,
    InstallationResult,
)
from colony_manager.application.services.development_plan_service import DevelopmentPlanService
from colony_manager.domain.models.development_plan import DevelopmentPlanStatus
from colony_manager.domain.models.user import User
from colony_manager.domain.ports.colony_user_repository import ColonyUserRepository

router = APIRouter(prefix="/development-plans", tags=["development_plans"])

# Error message constants
ERR_PLAN_NOT_FOUND = "Development plan not found"
ERR_PLAN_INCOMPLETE = "Development plan data is incomplete"
ERR_USER_NO_ID = "Authenticated user has no ID"


@router.post(
    "/colonies/{colony_id}",
    response_model=DevelopmentPlanResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"description": "Colony not found"}},
)
def create_development_plan(
    colony_id: int,
    plan_data: DevelopmentPlanCreate,
    service: Annotated[DevelopmentPlanService, Depends(dependencies.get_development_plan_service)],
    current_user: Annotated[User, Depends(require_role("colony_manager"))],
) -> DevelopmentPlanResponse:
    """Create a new development plan for a colony.

    Development plans track long-term colony development goals.
    Requires colony_manager role or higher.
    """
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERR_USER_NO_ID,
        )

    plan = service.create_plan(
        colony_id=colony_id,
        upgrade_type=plan_data.upgrade_type,
        target_type=plan_data.target_type,
        target_name=plan_data.target_name,
        priority=plan_data.priority,
        description=plan_data.description,
        notes=plan_data.notes,
        order=plan_data.order,
        created_by=current_user.id,
    )

    if plan.id is None or plan.created_at is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERR_PLAN_INCOMPLETE,
        )

    return DevelopmentPlanResponse(
        id=plan.id,
        colony_id=plan.colony_id,
        upgrade_type=plan.upgrade_type,
        target_type=plan.target_type,
        target_name=plan.target_name,
        priority=plan.priority,
        description=plan.description,
        notes=plan.notes,
        order=plan.order,
        status=plan.status.value,
        created_by=plan.created_by,
        created_at=plan.created_at,
    )


@router.get(
    "/{plan_id}",
    response_model=DevelopmentPlanResponse,
    responses={404: {"description": "Plan not found"}},
)
def get_development_plan(
    plan_id: int,
    service: Annotated[DevelopmentPlanService, Depends(dependencies.get_development_plan_service)],
    current_user: Annotated[User, Depends(get_current_user_from_cookie)],
    colony_user_repo: Annotated[
        ColonyUserRepository, Depends(dependencies.get_colony_user_repository)
    ],
) -> DevelopmentPlanResponse:
    """Get a development plan by ID."""
    plan = service.get_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERR_PLAN_NOT_FOUND)

    # Check permission on the colony the plan belongs to
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERR_USER_NO_ID
        )
    membership = colony_user_repo.get_by_colony_and_user(plan.colony_id, current_user.id)
    if membership is None and current_user.role.value != "admin":
        raise HTTPException(
            status_code=403, detail=f"User is not a member of colony {plan.colony_id}"
        )
    if membership is None and current_user.role.value != "admin":
        raise HTTPException(
            status_code=403, detail=f"User is not a member of colony {plan.colony_id}"
        )

    if plan.id is None or plan.created_at is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERR_PLAN_INCOMPLETE,
        )

    return DevelopmentPlanResponse(
        id=plan.id,
        colony_id=plan.colony_id,
        upgrade_type=plan.upgrade_type,
        target_type=plan.target_type,
        target_name=plan.target_name,
        priority=plan.priority,
        description=plan.description,
        notes=plan.notes,
        order=plan.order,
        status=plan.status.value,
        created_by=plan.created_by,
        created_at=plan.created_at,
    )


@router.get(
    "/colonies/{colony_id}",
    response_model=PaginatedResponse[DevelopmentPlanResponse],
    responses={403: {"description": "Forbidden - User not a member of colony"}},
)
def get_development_plans_by_colony(
    colony_id: int,
    service: Annotated[DevelopmentPlanService, Depends(dependencies.get_development_plan_service)],
    current_user: Annotated[User, Depends(get_current_user_from_cookie)],
    colony_user_repo: Annotated[
        ColonyUserRepository, Depends(dependencies.get_colony_user_repository)
    ],
    status_filter: DevelopmentPlanStatusEnum | None = Query(
        default=None,
        alias="status",
        description="Filter by plan status",
        examples=["planned", "in_progress", "acquired", "delivered"],
    ),
    upgrade_type_filter: str | None = Query(
        default=None,
        alias="upgrade_type",
        description="Filter by upgrade type (infrastructure or support_upgrade)",
        examples=["infrastructure", "support_upgrade"],
    ),
    priority_filter: int | None = Query(
        default=None,
        ge=1,
        le=5,
        alias="priority",
        description="Filter by priority level (1-5)",
    ),
    name_search: str | None = Query(
        default=None,
        description="Search by target name (case-insensitive substring match)",
        examples=["spaceport", "barracks"],
    ),
    offset: int = Query(default=0, ge=0, description="Number of items to skip"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum number of items to return"),
) -> PaginatedResponse[DevelopmentPlanResponse]:
    """Get all development plans for a colony with pagination and filtering.

    Filters:
    - status: Filter by plan status (planned, in_progress, acquired, delivered)
    - upgrade_type: Filter by upgrade type (infrastructure or support_upgrade)
    - priority: Filter by priority level (1-5)
    - search: Search by target name (case-insensitive substring match)

    Note: Filters are applied in-memory after loading all items. This is acceptable
    for typical colony sizes (<100 development plans). For colonies with >1000 plans,
    consider adding filtered query methods to the repository layer to push filtering
    to the database.
    """
    # Check permission on the colony
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERR_USER_NO_ID
        )
    membership = colony_user_repo.get_by_colony_and_user(colony_id, current_user.id)
    if membership is None and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail=f"User is not a member of colony {colony_id}")

    plans = service.get_plans_by_colony(colony_id)

    filtered = plans

    if status_filter is not None:
        # Convert schema enum to domain enum for comparison
        # Note: Assumes schema enum values match domain enum values
        domain_status = DevelopmentPlanStatus(status_filter.value)
        filtered = [p for p in filtered if p.status == domain_status]

    if upgrade_type_filter is not None:
        filtered = [p for p in filtered if p.upgrade_type == upgrade_type_filter]

    if priority_filter is not None:
        filtered = [p for p in filtered if p.priority == priority_filter]

    if name_search is not None:
        search_lower = name_search.lower()
        filtered = [p for p in filtered if search_lower in p.target_name.lower()]

    # Build response with pagination
    total = len(filtered)
    items = filtered[offset : offset + limit]

    result: list[DevelopmentPlanResponse] = []
    for p in items:
        if p.id is None or p.created_at is None:
            continue  # Skip plans with incomplete data
        result.append(
            DevelopmentPlanResponse(
                id=p.id,
                colony_id=p.colony_id,
                upgrade_type=p.upgrade_type,
                target_type=p.target_type,
                target_name=p.target_name,
                priority=p.priority,
                description=p.description,
                notes=p.notes,
                order=p.order,
                status=p.status.value,
                created_by=p.created_by,
                created_at=p.created_at,
            )
        )

    return PaginatedResponse(
        items=result,
        meta=PaginationMeta(
            total=total,
            offset=offset,
            limit=limit,
            has_more=(offset + limit) < total,
        ),
    )


@router.patch(
    "/{plan_id}",
    response_model=DevelopmentPlanResponse,
    responses={404: {"description": "Plan not found"}},
)
def update_development_plan(
    plan_id: int,
    plan_data: DevelopmentPlanUpdate,
    service: Annotated[DevelopmentPlanService, Depends(dependencies.get_development_plan_service)],
    current_user: Annotated[User, Depends(require_role("colony_manager"))],
) -> DevelopmentPlanResponse:
    """Update a development plan. Requires colony_manager role or higher."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERR_USER_NO_ID,
        )

    plan = service.get_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERR_PLAN_NOT_FOUND)

    # Convert status enum if provided
    status_value = None
    if plan_data.status is not None:
        status_value = DevelopmentPlanStatus(plan_data.status)

    updated_plan = service.update_plan(
        plan_id=plan_id,
        upgrade_type=plan_data.upgrade_type,
        target_type=plan_data.target_type,
        target_name=plan_data.target_name,
        priority=plan_data.priority,
        description=plan_data.description,
        notes=plan_data.notes,
        order=plan_data.order,
        status=status_value,
        changed_by=current_user.id,
    )

    if updated_plan.id is None or updated_plan.created_at is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERR_PLAN_INCOMPLETE,
        )

    return DevelopmentPlanResponse(
        id=updated_plan.id,
        colony_id=updated_plan.colony_id,
        upgrade_type=updated_plan.upgrade_type,
        target_type=updated_plan.target_type,
        target_name=updated_plan.target_name,
        priority=updated_plan.priority,
        description=updated_plan.description,
        notes=updated_plan.notes,
        order=updated_plan.order,
        status=updated_plan.status.value,
        created_by=updated_plan.created_by,
        created_at=updated_plan.created_at,
    )


@router.delete(
    "/{plan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": "Plan not found"}},
)
def delete_development_plan(
    plan_id: int,
    service: Annotated[DevelopmentPlanService, Depends(dependencies.get_development_plan_service)],
    current_user: Annotated[User, Depends(require_role("colony_manager"))],
) -> None:
    """Delete a development plan. Requires colony_manager role or higher."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERR_USER_NO_ID,
        )

    plan = service.get_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERR_PLAN_NOT_FOUND)

    service.delete_plan(plan_id, changed_by=current_user.id)


@router.post(
    "/{plan_id}/install",
    response_model=InstallationResult,
    responses={
        400: {"description": "Plan not in DELIVERED status"},
        404: {"description": "Plan not found"},
    },
)
def install_development_plan(
    plan_id: int,
    service: Annotated[DevelopmentPlanService, Depends(dependencies.get_development_plan_service)],
    current_user: Annotated[User, Depends(require_role("colony_manager"))],
) -> InstallationResult:
    """Install a development plan as an Infrastructure or Support Upgrade.

    Only plans in DELIVERED status can be installed. This creates the actual
    Infrastructure or SupportUpgrade entity and deletes the development plan.
    Requires colony_manager role or higher.
    """
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERR_USER_NO_ID,
        )

    result = service.install_plan(
        plan_id=plan_id,
        installed_by=current_user.id,
    )

    return InstallationResult(
        plan_id=result["plan_id"],
        plan_name=result["plan_name"],
        plan_target_type=result["plan_target_type"],
        installed_type=result["installed_type"],
        installed_id=result["installed_id"],
        installed_data=result["installed_data"],
    )
