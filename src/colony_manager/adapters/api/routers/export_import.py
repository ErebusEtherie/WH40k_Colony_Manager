"""Export/Import API router for colony data."""

import contextlib
import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from colony_manager.adapters.api.dependencies import (
    get_colony_service,
    get_colony_user_service,
    get_development_plan_service,
    get_event_service,
    get_representative_service,
    get_user_service,
)
from colony_manager.adapters.api.middleware.auth import get_current_user_from_cookie
from colony_manager.adapters.api.middleware.permissions import require_colony_permission
from colony_manager.adapters.io.colony_exporter import ColonyExporter
from colony_manager.adapters.io.colony_importer import ColonyImporter
from colony_manager.application.services.colony_service import ColonyService
from colony_manager.application.services.colony_user_service import ColonyUserService
from colony_manager.application.services.development_plan_service import DevelopmentPlanService
from colony_manager.application.services.event_service import EventService
from colony_manager.application.services.representative_service import RepresentativeService
from colony_manager.application.services.user_service import UserService
from colony_manager.domain.errors import NotFoundError
from colony_manager.domain.models.user import User

router = APIRouter(prefix="/colonies", tags=["export_import"])

ERR_COLONY_NOT_FOUND = "Colony not found"
ERR_IMPORT_FAILED = "Failed to import colony data"


@router.get(
    "/{colony_id}/export",
    response_class=Response,
    responses={404: {"description": "Colony not found"}},
)
async def export_colony(
    colony_id: int,
    current_user: Annotated[User, Depends(require_colony_permission("edit"))],
    colony_service: Annotated[ColonyService, Depends(get_colony_service)],
    representative_service: Annotated[RepresentativeService, Depends(get_representative_service)],
    event_service: Annotated[EventService, Depends(get_event_service)],
    development_plan_service: Annotated[
        DevelopmentPlanService, Depends(get_development_plan_service)
    ],
    colony_user_service: Annotated[ColonyUserService, Depends(get_colony_user_service)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> Response:
    """Export a colony and all its related data to a JSON file.

    Requires edit permission in the colony. Returns a JSON file with:
    - Colony base data and modifiers
    - Representative (if assigned)
    - All events
    - All development plans
    - All colony users

    The exported file can be imported later to restore the colony state.
    """
    # Get the colony
    try:
        colony = colony_service.get_colony(colony_id)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERR_COLONY_NOT_FOUND
        ) from e

    # Get representative if exists
    representative = None
    if colony.representative_id is not None:
        # Representative referenced but not found, skip it
        with contextlib.suppress(NotFoundError, AttributeError):
            representative = representative_service.get_representative_by_id(
                colony.representative_id
            )

    # Get all events for this colony
    events = event_service.get_events_by_colony(colony_id, active_only=False)

    # Get all development plans for this colony
    development_plans = development_plan_service.get_plans_by_colony(colony_id)

    # Get all colony users
    colony_users = colony_user_service.get_members_by_colony(colony_id)

    # Export to JSON
    exporter = ColonyExporter()
    json_content = exporter.export(
        colony=colony,
        representative=representative,
        events=events,
        development_plans=development_plans,
        colony_users=colony_users,
        user_service=user_service,  # Pass user_service to look up usernames
    )

    # Return as downloadable file
    filename = f"colony_{colony.name.replace(' ', '_')}_{colony_id}.json"
    return Response(
        content=json_content,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post(
    "/import",
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Invalid import data"},
        404: {"description": "Referenced resources not found"},
    },
)
async def import_colony(
    file_content: dict[str, Any],
    current_user: Annotated[User, Depends(get_current_user_from_cookie)],
    colony_service: Annotated[ColonyService, Depends(get_colony_service)],
    representative_service: Annotated[RepresentativeService, Depends(get_representative_service)],
    event_service: Annotated[EventService, Depends(get_event_service)],
    development_plan_service: Annotated[
        DevelopmentPlanService, Depends(get_development_plan_service)
    ],
    colony_user_service: Annotated[ColonyUserService, Depends(get_colony_user_service)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> dict[str, Any]:
    """Import a colony from a previously exported JSON file.

    The JSON content should be provided in the request body.
    Creates a new colony with all related data (representative, events, development plans, users).

    Multi-user support:
    - Current user is automatically added as owner
    - Other users from the import are looked up by username
    - If a user exists, they are added to the colony with their original role
    - If a user doesn't exist, a warning is returned (user is skipped)

    Returns:
        Dictionary with colony ID, name, and any warnings about skipped users
    """
    # Ensure current user has an ID (should always be true for authenticated users)
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Current user has no ID",
        )

    importer = ColonyImporter()

    try:
        # Parse the import data - handle both string and dict input
        if isinstance(file_content, str):
            import_data = importer.import_from_string(file_content)
        else:
            # If it's a dict, convert back to JSON string for parsing
            json_str = json.dumps(file_content)
            import_data = importer.import_from_string(json_str)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid import file format: {e}",
        ) from e

    try:
        # import_data keys: colony, representative, events, development_plans, colony_users
        colony = import_data["colony"]
        # Pass current_user.id as changed_by so the service adds them as owner
        created_colony = colony_service.create_colony(colony, changed_by=current_user.id)

        if created_colony.id is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create colony",
            )

        new_colony_id = created_colony.id

        # Create representative if present
        representative = import_data.get("representative")
        if representative:
            representative.id = None  # Clear ID for new record
            created_rep = representative_service.create_representative(representative)
            if created_rep.id:
                # Update colony with representative ID
                colony_service.update_colony(
                    new_colony_id,
                    representative_id=created_rep.id,
                )

        # Create events
        for event in import_data.get("events", []):
            event_service.create_event(
                colony_id=new_colony_id,
                name=event.name,
                description=event.description,
                created_by=current_user.id,
                modifiers=event.modifiers,
            )

        # Create development plans
        for plan in import_data.get("development_plans", []):
            development_plan_service.create_plan(
                colony_id=new_colony_id,
                upgrade_type=plan.upgrade_type,
                target_type=plan.target_type,
                target_name=plan.target_name,
                priority=plan.priority,
                description=plan.description,
                notes=plan.notes,
                order=plan.order,
                created_by=current_user.id,
            )

        # Create colony users (importer is already added as owner by create_colony)
        # Look up other users by username and add them if they exist
        warnings = []
        for colony_user in import_data.get("colony_users", []):
            # Skip if this is the current user (already added as owner by create_colony)
            if colony_user.user_id == current_user.id:
                continue

            # Look up user by username
            if colony_user.username:
                existing_user = user_service.get_user_by_username(colony_user.username)
                if existing_user and existing_user.id:
                    # User exists, add them to the colony
                    try:
                        colony_user_service.add_member(
                            colony_id=new_colony_id,
                            user_id=existing_user.id,
                            role=colony_user.role.value,
                            invited_by=current_user.id,
                        )
                    except Exception as e:  # noqa: BLE001 - Continue processing other users even if one fails
                        warnings.append(f"Failed to add user '{colony_user.username}': {e}")
                else:
                    # User doesn't exist, add warning
                    warnings.append(f"User '{colony_user.username}' not found in system, skipped")
            else:
                # No username provided, skip
                warnings.append(f"User ID {colony_user.user_id} has no username, skipped")

        result = {
            "id": new_colony_id,
            "name": created_colony.name,
            "message": "Colony imported successfully",
        }
        if warnings:
            result["warnings"] = warnings
        return result

    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {e}",
        ) from e
