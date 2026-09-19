"""API router for event endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from colony_manager.adapters.api import dependencies
from colony_manager.adapters.api.middleware.auth import get_current_user_from_cookie, require_role
from colony_manager.adapters.api.schemas.common import PaginatedResponse, PaginationMeta
from colony_manager.adapters.api.schemas.event import (
    EventCreate,
    EventListItem,
    EventModifierResponse,
    EventResponse,
    EventUpdate,
)
from colony_manager.application.services.event_service import EventService
from colony_manager.domain.models.event import EventModifier
from colony_manager.domain.models.user import User
from colony_manager.domain.ports.colony_user_repository import ColonyUserRepository

router = APIRouter(prefix="/events", tags=["events"])

# Error message constants
ERR_EVENT_NOT_FOUND = "Event not found"
ERR_EVENT_INCOMPLETE = "Event data is incomplete"
ERR_USER_NO_ID = "Authenticated user has no ID"


@router.post(
    "/colonies/{colony_id}",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"description": "Colony not found"}},
)
def create_event(
    colony_id: int,
    event_data: EventCreate,
    service: Annotated[EventService, Depends(dependencies.get_event_service)],
    current_user: Annotated[User, Depends(require_role("colony_manager"))],
) -> EventResponse:
    """Create a new event for a colony.

    Events are GM-created occurrences that affect colony stats.
    Requires colony_manager role or higher.
    """
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERR_USER_NO_ID,
        )

    event = service.create_event(
        colony_id=colony_id,
        name=event_data.name,
        description=event_data.description,
        created_by=current_user.id,
        modifiers=[
            EventModifier(stat=m.stat, value=m.value, description=m.description)
            for m in event_data.modifiers
        ],
    )

    if event.id is None or event.created_at is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERR_EVENT_INCOMPLETE,
        )

    return EventResponse(
        id=event.id,
        colony_id=event.colony_id,
        name=event.name,
        description=event.description,
        created_by=event.created_by,
        created_at=event.created_at,
        is_active=event.is_active,
        modifiers=[
            EventModifierResponse(stat=m.stat, value=m.value, description=m.description)
            for m in event.modifiers
        ],
    )


@router.get(
    "/{event_id}", response_model=EventResponse, responses={404: {"description": "Event not found"}}
)
def get_event(
    event_id: int,
    service: Annotated[EventService, Depends(dependencies.get_event_service)],
    current_user: Annotated[User, Depends(get_current_user_from_cookie)],
    colony_user_repo: Annotated[
        ColonyUserRepository, Depends(dependencies.get_colony_user_repository)
    ],
) -> EventResponse:
    """Get an event by ID."""
    event = service.get_event(event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERR_EVENT_NOT_FOUND)

    # Check permission on the colony the event belongs to
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERR_USER_NO_ID
        )
    membership = colony_user_repo.get_by_colony_and_user(event.colony_id, current_user.id)
    if membership is None and current_user.role.value != "admin":
        raise HTTPException(
            status_code=403, detail=f"User is not a member of colony {event.colony_id}"
        )

    if event.id is None or event.created_at is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERR_EVENT_INCOMPLETE,
        )

    return EventResponse(
        id=event.id,
        colony_id=event.colony_id,
        name=event.name,
        description=event.description,
        created_by=event.created_by,
        created_at=event.created_at,
        is_active=event.is_active,
        modifiers=[
            EventModifierResponse(stat=m.stat, value=m.value, description=m.description)
            for m in event.modifiers
        ],
    )


@router.get(
    "/colonies/{colony_id}",
    response_model=PaginatedResponse[EventListItem],
    responses={
        403: {"description": "Forbidden - User not a member of colony"},
        404: {"description": "Colony not found"},
    },
)
def get_events_by_colony(
    colony_id: int,
    service: Annotated[EventService, Depends(dependencies.get_event_service)],
    current_user: Annotated[User, Depends(get_current_user_from_cookie)],
    colony_user_repo: Annotated[
        ColonyUserRepository, Depends(dependencies.get_colony_user_repository)
    ],
    active_only: bool = Query(
        default=False,
        description="If True, only return active events",
    ),
    name_search: str | None = Query(
        default=None,
        description="Search by name (case-insensitive substring match)",
        examples=["warp", "storm"],
    ),
    offset: int = Query(default=0, ge=0, description="Number of items to skip"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum number of items to return"),
) -> PaginatedResponse[EventListItem]:
    """List all events for a colony with pagination and filtering.

    Filters:
    - active_only: If True, only return active events
    - search: Search by name (case-insensitive substring match)

    Note: Filters are applied in-memory after loading all items. This is acceptable
    for typical colony sizes (<100 items). For colonies with >1000 events,
    consider adding filtered query methods to the repository layer.
    """
    # Check permission on the colony
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERR_USER_NO_ID
        )
    membership = colony_user_repo.get_by_colony_and_user(colony_id, current_user.id)
    if membership is None and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail=f"User is not a member of colony {colony_id}")

    events = service.get_events_by_colony(colony_id, active_only)

    # Apply filters
    filtered = events

    # Normalize empty string to None for name_search
    if name_search is not None and not name_search.strip():
        name_search = None

    if name_search is not None:
        search_lower = name_search.lower()
        filtered = [e for e in filtered if search_lower in e.name.lower()]

    # Calculate pagination
    total = len(filtered)
    items = filtered[offset : offset + limit]

    # Build paginated response
    result: list[EventListItem] = []
    for e in items:
        if e.id is None or e.created_at is None:
            continue  # Skip events with incomplete data
        result.append(
            EventListItem(
                id=e.id,
                colony_id=e.colony_id,
                name=e.name,
                description=e.description,
                is_active=e.is_active,
                modifier_count=len(e.modifiers),
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
    "/{event_id}", response_model=EventResponse, responses={404: {"description": "Event not found"}}
)
def update_event(
    event_id: int,
    event_data: EventUpdate,
    service: Annotated[EventService, Depends(dependencies.get_event_service)],
    current_user: Annotated[User, Depends(require_role("colony_manager"))],
) -> EventResponse:
    """Update an event. Requires colony_manager role or higher."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERR_USER_NO_ID,
        )

    event = service.get_event(event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERR_EVENT_NOT_FOUND)

    updated_event = service.update_event(
        event_id=event_id,
        name=event_data.name,
        description=event_data.description,
        is_active=event_data.is_active,
        changed_by=current_user.id,
    )

    if updated_event.id is None or updated_event.created_at is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERR_EVENT_INCOMPLETE,
        )

    return EventResponse(
        id=updated_event.id,
        colony_id=updated_event.colony_id,
        name=updated_event.name,
        description=updated_event.description,
        created_by=updated_event.created_by,
        created_at=updated_event.created_at,
        is_active=updated_event.is_active,
        modifiers=[
            EventModifierResponse(stat=m.stat, value=m.value, description=m.description)
            for m in updated_event.modifiers
        ],
    )


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": "Event not found"}},
)
def delete_event(
    event_id: int,
    service: Annotated[EventService, Depends(dependencies.get_event_service)],
    current_user: Annotated[User, Depends(require_role("colony_manager"))],
) -> None:
    """Delete (soft delete) an event. Requires colony_manager role or higher."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERR_USER_NO_ID,
        )

    event = service.get_event(event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERR_EVENT_NOT_FOUND)

    service.delete_event(event_id, changed_by=current_user.id)
