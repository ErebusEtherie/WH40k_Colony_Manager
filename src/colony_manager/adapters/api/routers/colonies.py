"""Colony API router."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from colony_manager.adapters.api.dependencies import get_colony_service, get_representative_service
from colony_manager.adapters.api.middleware.auth import get_current_user_from_cookie
from colony_manager.adapters.api.middleware.permissions import require_colony_permission
from colony_manager.adapters.api.schemas.colony import (
    ColonyAgeAdvance,
    ColonyCreate,
    ColonyListItem,
    ColonyResponse,
    ColonyRollStatus,
    ColonyStateNested,
    ColonyStateStat,
    ColonyUpdate,
)
from colony_manager.adapters.api.schemas.common import PaginatedResponse, PaginationMeta
from colony_manager.adapters.api.schemas.modifier import (
    ModifierBreakdownItem,
    ModifierBreakdownResponse,
    ModifierCreate,
    ModifierResponse,
    ModifierUpdate,
    StatModifierBreakdown,
)
from colony_manager.adapters.api.schemas.representative import RepresentativeResponse
from colony_manager.application.services.colony_service import ColonyService, StatBreakdownDict
from colony_manager.application.services.representative_service import RepresentativeService
from colony_manager.domain.errors import ColonyManagerError, NotFoundError
from colony_manager.domain.models.audit_log import AuditLogAction
from colony_manager.domain.models.colony import Colony
from colony_manager.domain.models.modifier import Modifier
from colony_manager.domain.models.user import User

router = APIRouter(prefix="/colonies", tags=["colonies"])

logger = logging.getLogger(__name__)

# Error message constants
ERR_USER_NO_ID = "Authenticated user has no ID"


def _check_colony_exists(service: ColonyService, colony_id: int) -> Colony:
    """Check if colony exists, raise HTTPException if not."""
    try:
        return service.get_colony(colony_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


def _build_modifier_changes(
    modifier_data: ModifierUpdate,
    old_is_active: bool,
    old_description: str | None,
) -> list[str]:
    """Build list of change descriptions for audit logging."""
    changes = []
    if modifier_data.is_active is not None and modifier_data.is_active != old_is_active:
        changes.append(f"is_active={old_is_active}->{modifier_data.is_active}")
    if (
        modifier_data.modifier_description is not None
        and modifier_data.modifier_description != old_description
    ):
        changes.append(f"description={old_description}->{modifier_data.modifier_description}")
    return changes


def _log_modifier_audit(
    service: ColonyService,
    colony_id: int,
    modifier_id: int,
    changes: list[str],
    current_user: User,
    action: AuditLogAction,
    old_value: str | None = None,
) -> None:
    """Log audit entry for modifier changes if audit logging is enabled."""
    if service._audit_log_repository is None:
        return

    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERR_USER_NO_ID,
        )

    service._log_audit(
        colony_id=colony_id,
        entity_type="modifier",
        entity_id=modifier_id,
        action=action,
        field=None,
        old_value=old_value,
        new_value=", ".join(changes) if changes else None,
        changed_by=current_user.id,
    )


def _build_state_nested(state: dict[str, object]) -> ColonyStateNested:
    """Build nested state structure from service state dict."""
    from colony_manager.domain.enums import ModifierStat
    from colony_manager.domain.rules.lore_state_resolver import resolve_lore_state

    size = int(state.get("size", 0))  # type: ignore[call-overload]
    complacency = int(state.get("complacency", 0))  # type: ignore[call-overload]
    order = int(state.get("order", 0))  # type: ignore[call-overload]
    productivity = int(state.get("productivity", 0))  # type: ignore[call-overload]
    piety = int(state.get("piety", 0))  # type: ignore[call-overload]

    # Build lore_state dict for each stat (size doesn't have lore state)
    lore_state_dict = {
        "size": "stable",
        "complacency": resolve_lore_state(ModifierStat.COMPLACENCY, complacency, size).value,
        "order": resolve_lore_state(ModifierStat.ORDER, order, size).value,
        "productivity": resolve_lore_state(ModifierStat.PRODUCTIVITY, productivity, size).value,
        "piety": resolve_lore_state(ModifierStat.PIETY, piety, size).value,
    }

    return ColonyStateNested(
        size=ColonyStateStat(base=size, current=size, lore_state=lore_state_dict["size"]),
        complacency=ColonyStateStat(
            base=complacency, current=complacency, lore_state=lore_state_dict["complacency"]
        ),
        order=ColonyStateStat(base=order, current=order, lore_state=lore_state_dict["order"]),
        productivity=ColonyStateStat(
            base=productivity, current=productivity, lore_state=lore_state_dict["productivity"]
        ),
        piety=ColonyStateStat(base=piety, current=piety, lore_state=lore_state_dict["piety"]),
        leadership_modifier=int(state.get("leadership_modifier", 0)),  # type: ignore[call-overload]
        profit_factor=int(state.get("profit_factor", 0)),  # type: ignore[call-overload]
        lore_state=lore_state_dict,
    )


@router.get("", responses={})
async def list_colonies(
    current_user: Annotated[User, Depends(get_current_user_from_cookie)],
    service: Annotated[ColonyService, Depends(get_colony_service)],
    offset: int = Query(default=0, ge=0, description="Number of items to skip"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum number of items to return"),
) -> PaginatedResponse[ColonyListItem]:
    """List all colonies with pagination.

    Returns a paginated list of colonies. Use offset/limit for pagination.
    """
    all_colonies = service._colony_repository.list()

    # Calculate pagination
    total = len(all_colonies)
    items = all_colonies[offset : offset + limit]

    result_items = []
    for colony in items:
        assert colony.id is not None
        state = service.get_state(colony.id)
        result_items.append(
            ColonyListItem(
                id=colony.id,
                name=colony.name,
                founder_name=colony.founder_name,
                patron_name=colony.patron_name,
                colony_type=colony.colony_type,
                age_days=colony.age_days,
                current_size=int(state["size"]),  # type: ignore[call-overload]
                current_complacency=int(state["complacency"]),  # type: ignore[call-overload]
                current_order=int(state["order"]),  # type: ignore[call-overload]
                current_productivity=int(state["productivity"]),  # type: ignore[call-overload]
                current_piety=int(state["piety"]),  # type: ignore[call-overload]
                profit_factor=int(state["profit_factor"]),  # type: ignore[call-overload]
            )
        )

    return PaginatedResponse(
        items=result_items,
        meta=PaginationMeta(
            total=total,
            offset=offset,
            limit=limit,
            has_more=(offset + limit) < total,
        ),
    )


@router.post("", response_model=ColonyResponse, status_code=status.HTTP_201_CREATED, responses={})
async def create_colony(
    colony_data: ColonyCreate,
    current_user: Annotated[User, Depends(get_current_user_from_cookie)],
    service: Annotated[ColonyService, Depends(get_colony_service)],
) -> ColonyResponse:
    """Create a new colony."""
    from datetime import date

    from colony_manager.domain.models.colony import Colony

    config = service._rule_config_provider
    colony_type_config = config.get_colony_type_config(colony_data.colony_type)
    base_stats = colony_type_config.base_stats
    # Allow the GM to found an advanced-stage colony at a larger size than the
    # colony type's default (1). When base_size is omitted we fall back to the
    # type config so the common case stays behavior-identical to before.
    base_size = colony_data.base_size if colony_data.base_size is not None else base_stats.size
    colony = Colony(
        name=colony_data.name,
        founder_name=colony_data.founder_name,
        patron_name=colony_data.patron_name,
        colony_type=colony_data.colony_type,
        age_days=0,
        age_last_updated=date.today(),
        base_complacency=base_stats.complacency,
        base_order=base_stats.order,
        base_productivity=base_stats.productivity,
        base_piety=base_stats.piety,
        base_size=base_size,
    )
    created = service.create_colony(colony, changed_by=current_user.id)
    assert created.id is not None
    state = service.get_state(created.id)
    return ColonyResponse(
        id=created.id,
        name=created.name,
        founder_name=created.founder_name,
        patron_name=created.patron_name,
        colony_type=created.colony_type,
        age_days=created.age_days,
        age_last_updated=created.age_last_updated,
        current_event=created.current_event,
        base_complacency=created.base_complacency,
        base_order=created.base_order,
        base_productivity=created.base_productivity,
        base_piety=created.base_piety,
        base_size=created.base_size,
        representative_id=created.representative_id,
        dynasty_outcome=created.dynasty_outcome,
        complacency_locked=created.complacency_locked,
        order_locked=created.order_locked,
        productivity_locked=created.productivity_locked,
        planetary_resources=created.planetary_resources,
        state=_build_state_nested(state),
    )


@router.get(
    "/{colony_id}",
    response_model=ColonyResponse,
    responses={404: {"description": "Colony not found"}},
)
async def get_colony(
    colony_id: int,
    current_user: Annotated[User, Depends(require_colony_permission("view"))],
    service: Annotated[ColonyService, Depends(get_colony_service)],
) -> ColonyResponse:
    """Get a colony by ID.

    Raises:
        HTTPException: 404 if colony not found.
    """
    colony = _check_colony_exists(service, colony_id)
    state = service.get_state(colony_id)
    return ColonyResponse(
        id=colony.id,
        name=colony.name,
        founder_name=colony.founder_name,
        patron_name=colony.patron_name,
        colony_type=colony.colony_type,
        age_days=colony.age_days,
        age_last_updated=colony.age_last_updated,
        current_event=colony.current_event,
        base_complacency=colony.base_complacency,
        base_order=colony.base_order,
        base_productivity=colony.base_productivity,
        base_piety=colony.base_piety,
        base_size=colony.base_size,
        representative_id=colony.representative_id,
        dynasty_outcome=colony.dynasty_outcome,
        complacency_locked=colony.complacency_locked,
        order_locked=colony.order_locked,
        productivity_locked=colony.productivity_locked,
        planetary_resources=colony.planetary_resources,
        state=_build_state_nested(state),
    )


@router.put(
    "/{colony_id}",
    response_model=ColonyResponse,
    responses={404: {"description": "Colony not found"}},
)
async def update_colony(
    colony_id: int,
    colony_data: ColonyUpdate,
    current_user: Annotated[User, Depends(require_colony_permission("edit"))],
    service: Annotated[ColonyService, Depends(get_colony_service)],
) -> ColonyResponse:
    """Update a colony (partial update).

    Raises:
        HTTPException: 404 if colony not found.
    """
    _check_colony_exists(service, colony_id)
    update_data = colony_data.model_dump(exclude_unset=True)
    updated = service.update_colony(colony_id, changed_by=current_user.id, **update_data)
    state = service.get_state(colony_id)
    return ColonyResponse(
        id=updated.id,
        name=updated.name,
        founder_name=updated.founder_name,
        patron_name=updated.patron_name,
        colony_type=updated.colony_type,
        age_days=updated.age_days,
        age_last_updated=updated.age_last_updated,
        current_event=updated.current_event,
        base_complacency=updated.base_complacency,
        base_order=updated.base_order,
        base_productivity=updated.base_productivity,
        base_piety=updated.base_piety,
        base_size=updated.base_size,
        representative_id=updated.representative_id,
        dynasty_outcome=updated.dynasty_outcome,
        complacency_locked=updated.complacency_locked,
        order_locked=updated.order_locked,
        productivity_locked=updated.productivity_locked,
        planetary_resources=updated.planetary_resources,
        state=_build_state_nested(state),
    )


@router.delete(
    "/{colony_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": "Colony not found"}},
)
async def delete_colony(
    colony_id: int,
    current_user: Annotated[User, Depends(require_colony_permission("admin"))],
    service: Annotated[ColonyService, Depends(get_colony_service)],
) -> None:
    """Delete a colony.

    Raises:
        HTTPException: 404 if colony not found.
    """
    _check_colony_exists(service, colony_id)
    service._colony_repository.delete(colony_id)


@router.get(
    "/{colony_id}/state",
    response_model=ColonyStateNested,
    responses={404: {"description": "Colony not found"}},
)
async def get_colony_state(
    colony_id: int,
    current_user: Annotated[User, Depends(require_colony_permission("view"))],
    service: Annotated[ColonyService, Depends(get_colony_service)],
) -> ColonyStateNested:
    """Get computed state for a colony.

    Raises:
        HTTPException: 404 if colony not found.
    """
    _check_colony_exists(service, colony_id)
    state = service.get_state(colony_id)
    return _build_state_nested(state)


@router.post(
    "/{colony_id}/age",
    response_model=ColonyResponse,
    responses={
        404: {"description": "Colony not found"},
        400: {"description": "Invalid age operation"},
    },
)
async def manage_colony_age(
    colony_id: int,
    age_request: ColonyAgeAdvance,
    current_user: Annotated[User, Depends(require_colony_permission("edit"))],
    service: Annotated[ColonyService, Depends(get_colony_service)],
) -> ColonyResponse:
    """Manage colony age.

    Supports three operations:
    - add: Add days to current age (use negative values to decrease)
    - set: Set age to a specific value
    - subtract: Subtract days from current age

    Args:
        colony_id: The ID of the colony to update.
        age_request: Request body containing the age operation.

    Raises:
        HTTPException: 404 if colony not found, 400 if invalid operation.
    """
    _check_colony_exists(service, colony_id)
    try:
        # Get current colony state to calculate new age
        colony = service.get_colony(colony_id)
        new_age = age_request.get_days_delta(colony.age_days)
        updated = service.update_age(colony_id, new_age)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    state = service.get_state(colony_id)
    return ColonyResponse(
        id=updated.id,
        name=updated.name,
        founder_name=updated.founder_name,
        patron_name=updated.patron_name,
        colony_type=updated.colony_type,
        age_days=updated.age_days,
        age_last_updated=updated.age_last_updated,
        current_event=updated.current_event,
        base_complacency=updated.base_complacency,
        base_order=updated.base_order,
        base_productivity=updated.base_productivity,
        base_piety=updated.base_piety,
        base_size=updated.base_size,
        representative_id=updated.representative_id,
        dynasty_outcome=updated.dynasty_outcome,
        complacency_locked=updated.complacency_locked,
        order_locked=updated.order_locked,
        productivity_locked=updated.productivity_locked,
        planetary_resources=updated.planetary_resources,
        state=_build_state_nested(state),
    )


@router.get(
    "/{colony_id}/modifiers",
    response_model=PaginatedResponse[ModifierResponse],
    responses={404: {"description": "Colony not found"}},
)
async def list_colony_modifiers(
    colony_id: int,
    current_user: Annotated[User, Depends(require_colony_permission("view"))],
    service: Annotated[ColonyService, Depends(get_colony_service)],
    offset: int = Query(default=0, ge=0, description="Number of items to skip"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum number of items to return"),
) -> PaginatedResponse[ModifierResponse]:
    """List all modifiers for a colony with pagination.

    Raises:
        HTTPException: 404 if colony not found.
    """
    colony = _check_colony_exists(service, colony_id)

    # Apply pagination
    total = len(colony.modifiers)
    paginated_modifiers = colony.modifiers[offset : offset + limit]

    return PaginatedResponse(
        items=[
            ModifierResponse(
                id=mod.id,
                colony_id=colony_id,
                modifier_source_type=mod.modifier_source_type,
                modifier_category=mod.modifier_category,
                modifier_stat=mod.modifier_stat,
                modifier_value=mod.modifier_value,
                modifier_description=mod.modifier_description,
                is_active=mod.is_active,
                expires_at=mod.expires_at,
            )
            for mod in paginated_modifiers
        ],
        meta=PaginationMeta(
            total=total,
            offset=offset,
            limit=limit,
            has_more=(offset + limit) < total,
        ),
    )


@router.post(
    "/{colony_id}/modifiers",
    response_model=ModifierResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"description": "Colony not found"}},
)
async def add_colony_modifier(
    colony_id: int,
    modifier_data: ModifierCreate,
    current_user: Annotated[User, Depends(require_colony_permission("edit"))],
    service: Annotated[ColonyService, Depends(get_colony_service)],
) -> ModifierResponse:
    """Add a modifier to a colony.

    Raises:
        HTTPException: 404 if colony not found.
    """
    _check_colony_exists(service, colony_id)
    modifier = Modifier(
        colony_id=colony_id,
        modifier_source_type=modifier_data.modifier_source_type,
        modifier_category=modifier_data.modifier_category,
        modifier_stat=modifier_data.modifier_stat,
        modifier_value=modifier_data.modifier_value,
        modifier_description=modifier_data.modifier_description,
        is_active=modifier_data.is_active,
        expires_at=modifier_data.expires_at,
    )
    updated = service.add_modifier(colony_id, modifier, changed_by=current_user.id)
    new_modifier = updated.modifiers[-1]
    return ModifierResponse(
        id=new_modifier.id,
        colony_id=colony_id,
        modifier_source_type=new_modifier.modifier_source_type,
        modifier_category=new_modifier.modifier_category,
        modifier_stat=new_modifier.modifier_stat,
        modifier_value=new_modifier.modifier_value,
        modifier_description=new_modifier.modifier_description,
        is_active=new_modifier.is_active,
        expires_at=new_modifier.expires_at,
    )


@router.delete(
    "/{colony_id}/modifiers/{modifier_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": "Modifier not found"}},
)
async def remove_colony_modifier(
    colony_id: int,
    modifier_id: int,
    current_user: Annotated[User, Depends(require_colony_permission("edit"))],
    service: Annotated[ColonyService, Depends(get_colony_service)],
) -> None:
    """Remove a modifier from a colony.

    Raises:
        HTTPException: 404 if modifier not found.
    """
    colony = _check_colony_exists(service, colony_id)
    modifier_to_remove = next((mod for mod in colony.modifiers if mod.id == modifier_id), None)
    if modifier_to_remove is None:
        raise HTTPException(status_code=404, detail=f"Modifier {modifier_id} not found")
    colony.modifiers.remove(modifier_to_remove)
    service._colony_repository.update(colony)

    # Log audit entry
    old_value = (
        f"modifier_stat={modifier_to_remove.modifier_stat.value}, "
        f"modifier_value={modifier_to_remove.modifier_value}, "
        f"is_active={modifier_to_remove.is_active}"
    )
    _log_modifier_audit(
        service=service,
        colony_id=colony_id,
        modifier_id=modifier_id,
        changes=[],
        current_user=current_user,
        action=AuditLogAction.DELETE,
        old_value=old_value,
    )


@router.patch(
    "/{colony_id}/modifiers/{modifier_id}",
    response_model=ModifierResponse,
    responses={
        404: {"description": "Modifier not found"},
        500: {"description": "Failed to update modifier"},
    },
)
async def update_colony_modifier(
    colony_id: int,
    modifier_id: int,
    modifier_data: ModifierUpdate,
    current_user: Annotated[User, Depends(require_colony_permission("edit"))],
    service: Annotated[ColonyService, Depends(get_colony_service)],
) -> ModifierResponse:
    """Update a modifier (partial update).

    Typically used to toggle is_active status without deleting and re-adding.

    Raises:
        HTTPException: 404 if modifier not found, 500 if update fails.
    """
    colony = _check_colony_exists(service, colony_id)
    modifier_to_update = next((mod for mod in colony.modifiers if mod.id == modifier_id), None)
    if modifier_to_update is None:
        raise HTTPException(status_code=404, detail=f"Modifier {modifier_id} not found")

    # Store old values for audit log
    old_is_active = modifier_to_update.is_active
    old_description = modifier_to_update.modifier_description

    # Apply updates
    if modifier_data.is_active is not None:
        modifier_to_update.is_active = modifier_data.is_active
    if modifier_data.modifier_description is not None:
        modifier_to_update.modifier_description = modifier_data.modifier_description

    # Save colony with error handling
    try:
        service._colony_repository.update(colony)
    except Exception as e:
        logger.exception("Failed to update modifier %s for colony %s", modifier_id, colony_id)
        raise HTTPException(status_code=500, detail="Failed to update modifier") from e

    # Log audit entry if there are changes
    changes = _build_modifier_changes(modifier_data, old_is_active, old_description)
    if changes:
        _log_modifier_audit(
            service=service,
            colony_id=colony_id,
            modifier_id=modifier_id,
            changes=changes,
            current_user=current_user,
            action=AuditLogAction.UPDATE,
        )

    return ModifierResponse(
        id=modifier_to_update.id,
        colony_id=colony_id,
        modifier_source_type=modifier_to_update.modifier_source_type,
        modifier_category=modifier_to_update.modifier_category,
        modifier_stat=modifier_to_update.modifier_stat,
        modifier_value=modifier_to_update.modifier_value,
        modifier_description=modifier_to_update.modifier_description,
        is_active=modifier_to_update.is_active,
        expires_at=modifier_to_update.expires_at,
    )


@router.get(
    "/{colony_id}/roll-status",
    response_model=ColonyRollStatus,
    responses={404: {"description": "Colony not found"}},
)
async def get_colony_roll_status(
    colony_id: int,
    current_user: Annotated[User, Depends(require_colony_permission("view"))],
    service: Annotated[ColonyService, Depends(get_colony_service)],
) -> ColonyRollStatus:
    """
    Get the roll status for a colony.

    Returns information about when the next event and development rolls are due.
    Event rolls occur every 60 days, development rolls every 90 days.

    Raises:
        HTTPException: 404 if colony not found.
    """
    _check_colony_exists(service, colony_id)
    roll_status = service.get_roll_status(colony_id)
    return ColonyRollStatus(**roll_status)


@router.get(
    "/{colony_id}/modifier-breakdown",
    response_model=ModifierBreakdownResponse,
    responses={404: {"description": "Colony not found"}},
)
async def get_colony_modifier_breakdown(
    colony_id: int,
    current_user: Annotated[User, Depends(require_colony_permission("view"))],
    service: Annotated[ColonyService, Depends(get_colony_service)],
) -> ModifierBreakdownResponse:
    """
    Get detailed modifier breakdown grouped by stat for a colony.

    Returns a comprehensive breakdown showing:
    - Each stat's base value (before modifiers)
    - All active modifiers affecting that stat (source, value, description)
    - Total modifier sum per stat
    - Current calculated value per stat (includes conditional bonuses)
    - Leadership modifier and Profit Factor

    Note: Only active modifiers are included. Inactive or expired modifiers are excluded.

    This is useful for UI panels that need to display exactly how each stat
    is calculated and what modifiers are contributing to it.

    Raises:
        HTTPException: 404 if colony not found.
    """
    _check_colony_exists(service, colony_id)
    breakdown = service.get_modifier_breakdown(colony_id)

    # Convert TypedDict breakdown to Pydantic models
    def _convert_stat_breakdown(stat_breakdown: StatBreakdownDict) -> StatModifierBreakdown:
        """Convert StatBreakdownDict to StatModifierBreakdown."""
        from colony_manager.domain.enums import ModifierSourceType

        modifiers = [
            ModifierBreakdownItem(
                source_type=ModifierSourceType(item["source_type"]),
                source_id=item["source_id"],
                source_name=item["source_name"],
                value=item["value"],
                description=item["description"],
            )
            for item in stat_breakdown["modifiers"]
        ]
        return StatModifierBreakdown(
            base=stat_breakdown["base"],
            modifiers=modifiers,
            total_modifier=stat_breakdown["total_modifier"],
            current=stat_breakdown["current"],
        )

    return ModifierBreakdownResponse(
        size=_convert_stat_breakdown(breakdown["size"]),
        complacency=_convert_stat_breakdown(breakdown["complacency"]),
        order=_convert_stat_breakdown(breakdown["order"]),
        productivity=_convert_stat_breakdown(breakdown["productivity"]),
        piety=_convert_stat_breakdown(breakdown["piety"]),
        leadership_modifier=breakdown["leadership_modifier"],
        profit_factor=breakdown["profit_factor"],
    )


@router.put(
    "/{colony_id}/representative",
    response_model=RepresentativeResponse,
    responses={
        404: {"description": "Colony or representative not found"},
        400: {"description": "Assignment error"},
    },
)
async def assign_representative_to_colony(
    colony_id: int,
    representative_id: int,
    current_user: Annotated[User, Depends(require_colony_permission("edit"))],
    colony_service: Annotated[ColonyService, Depends(get_colony_service)],
    representative_service: Annotated[RepresentativeService, Depends(get_representative_service)],
) -> RepresentativeResponse:
    """Assign a representative to a colony.

    This endpoint atomically updates both the colony's representative_id and
    the representative's assigned_to_colony_id. If the colony already has a
    representative, they are automatically unassigned.

    Args:
        colony_id: ID of the colony to assign to.
        representative_id: ID of the representative to assign.
        current_user: Authenticated user with edit permission.
        colony_service: Colony service for colony operations.
        representative_service: Representative service for assignment.

    Returns:
        RepresentativeResponse with the updated representative and change tracking info.

    Raises:
        HTTPException: 404 if colony or representative not found, 400 for assignment errors.
    """
    from colony_manager.adapters.api.schemas.representative import (
        AssignmentChangeInfo,
        RepresentativeStatsCreate,
    )
    from colony_manager.domain.errors import ColonyManagerError

    try:
        result = representative_service.assign_to_colony(
            colony_id=colony_id,
            representative_id=representative_id,
            changed_by=current_user.id,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ColonyManagerError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    updated = result.representative

    return RepresentativeResponse(
        id=updated.id,
        name=updated.name,
        type=updated.type,
        personalities=updated.personalities,
        stats=RepresentativeStatsCreate(**updated.stats.model_dump(by_alias=True)),
        skills=updated.skills,
        talents=updated.talents,
        leadership_modifier=result.new_leadership,
        assigned_to_colony_id=updated.assigned_to_colony_id,
        assignment_change=AssignmentChangeInfo(
            representative_changed=True,
            previous_representative_id=result.previous_representative_id,
            new_representative_id=result.new_representative_id,
            leadership_modifier_changed=result.leadership_modifier_changed,
            previous_leadership=result.previous_leadership,
            new_leadership=result.new_leadership,
        ),
    )


@router.delete(
    "/{colony_id}/representative",
    response_model=RepresentativeResponse,
    responses={
        404: {"description": "No representative assigned"},
        400: {"description": "Unassignment error"},
        500: {"description": "Internal server error - Representative has no ID"},
    },
)
async def unassign_representative_from_colony(
    colony_id: int,
    current_user: Annotated[User, Depends(require_colony_permission("edit"))],
    representative_service: Annotated[RepresentativeService, Depends(get_representative_service)],
) -> RepresentativeResponse:
    """Unassign the current representative from a colony.

    This endpoint atomically clears both the colony's representative_id and
    the representative's assigned_to_colony_id.

    Args:
        colony_id: ID of the colony to unassign from.
        current_user: Authenticated user with edit permission.
        representative_service: Representative service for unassignment.

    Returns:
        RepresentativeResponse with the unassigned representative and change tracking info.

    Raises:
        HTTPException: 404 if no representative is assigned to the colony,
            400 for unassignment errors.
    """
    from colony_manager.adapters.api.schemas.representative import (
        AssignmentChangeInfo,
        RepresentativeStatsCreate,
    )
    from colony_manager.domain.errors import NotFoundError

    # Find the representative assigned to this colony
    all_reps = representative_service.list_representatives()
    assigned_rep = next((r for r in all_reps if r.assigned_to_colony_id == colony_id), None)

    if assigned_rep is None:
        raise HTTPException(
            status_code=404,
            detail=f"No representative assigned to colony {colony_id}",
        )

    if assigned_rep.id is None:
        raise HTTPException(
            status_code=500,
            detail="Representative has no ID - database inconsistency",
        )

    try:
        result = representative_service.unassign_from_colony(
            representative_id=assigned_rep.id,
            changed_by=current_user.id,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ColonyManagerError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    updated = result.representative

    return RepresentativeResponse(
        id=updated.id,
        name=updated.name,
        type=updated.type,
        personalities=updated.personalities,
        stats=RepresentativeStatsCreate(**updated.stats.model_dump(by_alias=True)),
        skills=updated.skills,
        talents=updated.talents,
        leadership_modifier=result.new_leadership,
        assigned_to_colony_id=updated.assigned_to_colony_id,
        assignment_change=AssignmentChangeInfo(
            representative_changed=True,
            previous_representative_id=result.previous_representative_id,
            new_representative_id=result.new_representative_id,
            leadership_modifier_changed=result.leadership_modifier_changed,
            previous_leadership=result.previous_leadership,
            new_leadership=result.new_leadership,
        ),
    )
