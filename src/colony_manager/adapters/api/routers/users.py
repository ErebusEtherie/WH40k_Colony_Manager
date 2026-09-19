"""Router for user management endpoints.

Provides REST API endpoints for admin user management operations.
All endpoints require admin authentication.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from colony_manager.adapters.api.dependencies import get_user_service
from colony_manager.adapters.api.middleware.permissions import require_admin
from colony_manager.adapters.api.schemas.common import PaginatedResponse, PaginationMeta
from colony_manager.adapters.api.schemas.user import (
    UserCreate,
    UserPasswordReset,
    UserResponse,
    UserUpdate,
)
from colony_manager.application.services.user_service import UserService
from colony_manager.domain.errors import NotFoundError, ValidationError
from colony_manager.domain.models.user import User, UserRole

router = APIRouter(prefix="/users", tags=["users"])

# Error message constant for admin-only endpoints
ADMIN_ACCESS_REQUIRED = "Admin access required"


def _user_to_response(user: User) -> UserResponse:
    """Convert domain User model to API response schema."""
    if user.id is None:
        raise ValueError("User must have an ID to be converted to response")
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role.value if isinstance(user.role, UserRole) else user.role,
        is_active=user.is_active,
    )


@router.get("", responses={403: {"description": "Forbidden - Admin only"}})
async def list_users(
    current_user: Annotated[User, Depends(require_admin)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    limit: Annotated[int, Query(ge=1, le=100, description="Number of users to return")] = 20,
    offset: Annotated[int, Query(ge=0, description="Number of users to skip")] = 0,
) -> PaginatedResponse[UserResponse]:
    """List all users with pagination.

    Requires admin privileges. Returns paginated list of users.

    Raises:
        HTTPException: 403 if user is not an admin.
    """
    # Check admin role
    user_role = (
        current_user.role.value if isinstance(current_user.role, UserRole) else current_user.role
    )
    if user_role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ADMIN_ACCESS_REQUIRED,
        )

    users, total = user_service.list_users(limit=limit, offset=offset)

    return PaginatedResponse(
        items=[_user_to_response(user) for user in users],
        meta=PaginationMeta(
            total=total,
            offset=offset,
            limit=limit,
            has_more=(offset + limit) < total,
        ),
    )


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Username/email exists"},
        403: {"description": "Forbidden - Admin only"},
    },
)
async def create_user(
    current_user: Annotated[User, Depends(require_admin)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    user_data: UserCreate,
) -> UserResponse:
    """Create a new user.

    Requires admin privileges. Creates a new user account with the provided details.
    Username and email are immutable after creation.

    Raises:
        HTTPException: 403 if user is not an admin.
        HTTPException: 400 if username or email already exists.
    """
    # Check admin role
    user_role = (
        current_user.role.value if isinstance(current_user.role, UserRole) else current_user.role
    )
    if user_role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ADMIN_ACCESS_REQUIRED,
        )

    try:
        created_user = user_service.create_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            role=user_data.role,
            is_active=user_data.is_active,
            created_by=current_user.id,
        )
        return _user_to_response(created_user)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    responses={
        403: {"description": "Forbidden - Admin only"},
        404: {"description": "User not found"},
    },
)
async def get_user(
    user_id: int,
    current_user: Annotated[User, Depends(require_admin)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    """Get a specific user by ID.

    Requires admin privileges.

    Raises:
        HTTPException: 403 if user is not an admin.
        HTTPException: 404 if user not found.
    """
    # Check admin role
    user_role = (
        current_user.role.value if isinstance(current_user.role, UserRole) else current_user.role
    )
    if user_role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ADMIN_ACCESS_REQUIRED,
        )

    user = user_service.get_user(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )

    return _user_to_response(user)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    responses={
        400: {"description": "Validation error"},
        403: {"description": "Forbidden"},
        404: {"description": "User not found"},
    },
)
async def update_user(
    user_id: int,
    current_user: Annotated[User, Depends(require_admin)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    user_data: UserUpdate,
) -> UserResponse:
    """Update a user.

    Requires admin privileges. Username and email are immutable.
    Admins cannot modify other admins, and users cannot escalate their own privileges.

    Raises:
        HTTPException: 403 if user is not an admin or lacks permission.
        HTTPException: 404 if user not found.
        HTTPException: 400 if validation fails.
    """
    # Check admin role
    user_role = (
        current_user.role.value if isinstance(current_user.role, UserRole) else current_user.role
    )
    if user_role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ADMIN_ACCESS_REQUIRED,
        )

    try:
        updated_user = user_service.update_user(
            user_id=user_id,
            role=user_data.role,
            is_active=user_data.is_active,
            changed_by=current_user.id,
        )
        return _user_to_response(updated_user)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        ) from e
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={403: {"description": "Forbidden"}, 404: {"description": "User not found"}},
)
async def delete_user(
    user_id: int,
    current_user: Annotated[User, Depends(require_admin)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> None:
    """Delete a user (soft delete).

    Requires admin privileges. Sets is_active to False instead of hard deleting.
    Admins cannot delete other admins.

    Raises:
        HTTPException: 403 if user is not an admin or lacks permission.
        HTTPException: 404 if user not found.
    """
    # Check admin role
    user_role = (
        current_user.role.value if isinstance(current_user.role, UserRole) else current_user.role
    )
    if user_role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ADMIN_ACCESS_REQUIRED,
        )

    try:
        user_service.delete_user(
            user_id=user_id,
            changed_by=current_user.id,
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        ) from e


@router.post(
    "/{user_id}/reset-password",
    response_model=UserResponse,
    responses={
        400: {"description": "Validation error"},
        403: {"description": "Forbidden"},
        404: {"description": "User not found"},
    },
)
async def reset_password(
    user_id: int,
    current_user: Annotated[User, Depends(require_admin)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    password_data: UserPasswordReset,
) -> UserResponse:
    """Reset a user's password.

    Requires admin privileges. Sets a temporary password that the user
    must change on next login.

    Raises:
        HTTPException: 403 if user is not an admin or lacks permission.
        HTTPException: 404 if user not found.
    """
    # Check admin role
    user_role = (
        current_user.role.value if isinstance(current_user.role, UserRole) else current_user.role
    )
    if user_role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ADMIN_ACCESS_REQUIRED,
        )

    try:
        updated_user = user_service.reset_password(
            user_id=user_id,
            temporary_password=password_data.temporary_password,
            changed_by=current_user.id,
        )
        return _user_to_response(updated_user)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        ) from e
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
