"""API router for colony user membership endpoints."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from colony_manager.adapters.api.dependencies import get_colony_user_service
from colony_manager.adapters.api.middleware.permissions import require_colony_permission
from colony_manager.adapters.api.schemas.colony_user import (
    ColonyOwnershipTransfer,
    ColonyUserCreate,
    ColonyUserListItem,
    ColonyUserResponse,
    ColonyUserUpdate,
)
from colony_manager.adapters.api.schemas.common import PaginatedResponse, PaginationMeta
from colony_manager.application.services.colony_user_service import ColonyUserService
from colony_manager.domain.errors import NotFoundError
from colony_manager.domain.models.colony_user import ColonyUserRole
from colony_manager.domain.models.user import User

# Error message constants
ERR_MEMBER_NOT_FOUND = "Colony member not found"
ERR_MEMBER_ALREADY_EXISTS = "User is already a member of this colony"
ERR_USER_NO_ID = "Authenticated user has no ID"

router = APIRouter(prefix="/colonies/{colony_id}/members", tags=["colony_users"])


@router.get("", response_model=PaginatedResponse[ColonyUserListItem], responses={})
def get_colony_members(
    colony_id: int,
    service: Annotated[ColonyUserService, Depends(get_colony_user_service)],
    current_user: Annotated[User, Depends(require_colony_permission("view"))],
    offset: int = Query(default=0, ge=0, description="Number of items to skip"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum number of items to return"),
) -> PaginatedResponse[ColonyUserListItem]:
    """Get all members of a colony with pagination.

    Note: Pagination is applied in-memory after loading all items. This is acceptable
    for typical colony sizes (<100 members). For colonies with >1000 members,
    consider adding paginated query methods to the repository layer.
    """
    memberships = service.get_members_by_colony(colony_id)

    # Calculate pagination
    total = len(memberships)
    items = memberships[offset : offset + limit]

    # Build paginated response
    result: list[ColonyUserListItem] = []
    for m in items:
        if m.id is None or m.joined_at is None:
            continue  # Skip memberships with incomplete data
        result.append(
            ColonyUserListItem(
                id=m.id,
                colony_id=m.colony_id,
                user_id=m.user_id,
                role=m.role.value,
                joined_at=m.joined_at,
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


@router.post(
    "",
    response_model=ColonyUserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"description": "User already member"}, 404: {"description": "User not found"}},
)
def add_colony_member(
    colony_id: int,
    member_data: ColonyUserCreate,
    service: Annotated[ColonyUserService, Depends(get_colony_user_service)],
    current_user: Annotated[User, Depends(require_colony_permission("admin"))],
) -> ColonyUserResponse:
    """Add a user to a colony.

    Requires appropriate permissions (typically owner or editor role).
    """
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERR_USER_NO_ID,
        )

    try:
        membership = service.add_member(
            colony_id=colony_id,
            user_id=member_data.user_id,
            role=ColonyUserRole(member_data.role),
            invited_by=current_user.id,
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    if membership.id is None or membership.joined_at is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Created membership data is incomplete",
        )

    return ColonyUserResponse(
        id=membership.id,
        colony_id=membership.colony_id,
        user_id=membership.user_id,
        role=membership.role.value,
        joined_at=membership.joined_at,
        invited_by=membership.invited_by,
    )


@router.get(
    "/{user_id}",
    response_model=ColonyUserResponse,
    responses={404: {"description": "Member not found"}},
)
def get_colony_member(
    colony_id: int,
    user_id: int,
    service: Annotated[ColonyUserService, Depends(get_colony_user_service)],
    current_user: Annotated[User, Depends(require_colony_permission("view"))],
) -> ColonyUserResponse:
    """Get a specific user's membership in a colony."""
    membership = service.get_membership_by_colony_and_user(colony_id, user_id)
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_MEMBER_NOT_FOUND,
        )

    if membership.id is None or membership.joined_at is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Membership data is incomplete",
        )

    return ColonyUserResponse(
        id=membership.id,
        colony_id=membership.colony_id,
        user_id=user_id,
        role=membership.role.value,
        joined_at=membership.joined_at,
        invited_by=membership.invited_by,
    )


@router.patch(
    "/{user_id}",
    response_model=ColonyUserResponse,
    responses={404: {"description": "Member not found"}},
)
def update_colony_member_role(
    colony_id: int,
    user_id: int,
    member_data: ColonyUserUpdate,
    service: Annotated[ColonyUserService, Depends(get_colony_user_service)],
    current_user: Annotated[User, Depends(require_colony_permission("admin"))],
) -> ColonyUserResponse:
    """Update a member's role in the colony.

    Requires appropriate permissions (typically owner role).
    """
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERR_USER_NO_ID,
        )

    membership = service.get_membership_by_colony_and_user(colony_id, user_id)
    if membership is None or membership.id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_MEMBER_NOT_FOUND,
        )

    updated_membership = service.update_member_role(
        membership_id=membership.id,
        new_role=ColonyUserRole(member_data.role),
        changed_by=current_user.id,
    )

    if updated_membership.id is None or updated_membership.joined_at is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Updated membership data is incomplete",
        )

    return ColonyUserResponse(
        id=updated_membership.id,
        colony_id=updated_membership.colony_id,
        user_id=updated_membership.user_id,
        role=updated_membership.role.value,
        joined_at=updated_membership.joined_at,
        invited_by=updated_membership.invited_by,
    )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": "Member not found"}},
)
def remove_colony_member(
    colony_id: int,
    user_id: int,
    service: Annotated[ColonyUserService, Depends(get_colony_user_service)],
    current_user: Annotated[User, Depends(require_colony_permission("admin"))],
) -> None:
    """Remove a user from a colony.

    Requires appropriate permissions (typically owner role).
    """
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERR_USER_NO_ID,
        )

    membership = service.get_membership_by_colony_and_user(colony_id, user_id)
    if membership is None or membership.id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_MEMBER_NOT_FOUND,
        )

    service.remove_member(membership.id, changed_by=current_user.id)


@router.post(
    "/transfer-ownership",
    response_model=dict,
    responses={
        400: {"description": "Invalid transfer"},
        403: {"description": "Not owner"},
        404: {"description": "User not found"},
    },
)
def transfer_colony_ownership(
    colony_id: int,
    transfer_data: ColonyOwnershipTransfer,
    service: Annotated[ColonyUserService, Depends(get_colony_user_service)],
    current_user: Annotated[User, Depends(require_colony_permission("admin"))],
) -> dict[str, Any]:
    """Transfer colony ownership to another user.

    Requires owner-level permissions. The current owner is demoted to editor
    by default (can be disabled with demote_current=False).

    Returns:
        Dictionary with new_owner and previous_owner user IDs.
    """
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERR_USER_NO_ID,
        )

    # Verify current user is the owner
    current_membership = service.get_membership_by_colony_and_user(colony_id, current_user.id)
    if current_membership is None or current_membership.role != ColonyUserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the colony owner can transfer ownership",
        )

    try:
        new_owner_membership, _previous_owner_membership = service.transfer_ownership(
            colony_id=colony_id,
            current_owner_id=current_user.id,
            new_owner_id=transfer_data.new_owner_id,
            demote_current=transfer_data.demote_current,
            changed_by=current_user.id,
        )

        return {
            "message": "Ownership transferred successfully",
            "colony_id": colony_id,
            "new_owner_id": new_owner_membership.user_id,
            "previous_owner_id": current_user.id,
            "previous_owner_demoted": transfer_data.demote_current,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
