"""API router for audit log endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from colony_manager.adapters.api.dependencies import get_audit_log_repository
from colony_manager.adapters.api.middleware.permissions import require_colony_permission
from colony_manager.adapters.api.schemas.audit_log import (
    AuditLogListItem,
    AuditLogResponse,
)
from colony_manager.adapters.api.schemas.common import PaginatedResponse, PaginationMeta
from colony_manager.domain.models.user import User
from colony_manager.domain.ports.audit_log_repository import AuditLogRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/colonies/{colony_id}/audit-logs", tags=["audit_logs"])


@router.get("", response_model=PaginatedResponse[AuditLogListItem], responses={})
def get_audit_logs_by_colony(
    colony_id: int,
    repository: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
    current_user: Annotated[User, Depends(require_colony_permission("admin"))],
    entity_type: str | None = Query(default=None, description="Filter by entity type"),
    limit: int = Query(default=50, ge=1, le=500, description="Maximum number of results"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip"),
) -> PaginatedResponse[AuditLogListItem]:
    """Get audit logs for a colony with pagination.

    Returns a chronological history of changes made to the colony.
    Requires colony owner role.
    """
    # Get total count for pagination metadata
    total = repository.count_by_colony(
        colony_id=colony_id,
        entity_type=entity_type,
    )

    # Get paginated results
    logs = repository.get_by_colony(
        colony_id=colony_id,
        limit=limit,
        offset=offset,
        entity_type=entity_type,
    )

    result: list[AuditLogListItem] = []
    for log in logs:
        if log.id is None or log.changed_at is None:
            logger.warning(
                "Skipping audit log with incomplete data: colony_id=%s, log=%s", colony_id, log
            )
            continue
        assert log.colony_id is not None
        result.append(
            AuditLogListItem(
                id=log.id,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                action=log.action.value,
                field=log.field,
                changed_by=log.changed_by,
                changed_at=log.changed_at,
                colony_id=log.colony_id,
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


@router.get(
    "/{log_id}",
    response_model=AuditLogResponse,
    responses={
        404: {"description": "Audit log entry not found"},
        500: {"description": "Internal server error - Audit log data is incomplete"},
    },
)
def get_audit_log(
    log_id: int,
    colony_id: int,
    repository: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
    current_user: Annotated[User, Depends(require_colony_permission("admin"))],
) -> AuditLogResponse:
    """Get a specific audit log entry by ID.

    Requires colony owner role.

    Raises:
        HTTPException: 404 if audit log entry not found or belongs to different colony.
    """
    log = repository.get_by_id(log_id)
    if log is None:
        raise HTTPException(status_code=404, detail="Audit log entry not found")

    # Validate the log belongs to the specified colony to prevent cross-colony access
    if log.colony_id is None or log.colony_id != colony_id:
        raise HTTPException(status_code=404, detail="Audit log entry not found")

    if log.id is None or log.changed_at is None:
        raise HTTPException(status_code=500, detail="Audit log data is incomplete")

    assert log.id is not None
    return AuditLogResponse(
        id=log.id,
        entity_type=log.entity_type,
        entity_id=log.entity_id,
        action=log.action.value,
        field=log.field,
        old_value=log.old_value,
        new_value=log.new_value,
        changed_by=log.changed_by,
        changed_at=log.changed_at,
        colony_id=log.colony_id,
    )
