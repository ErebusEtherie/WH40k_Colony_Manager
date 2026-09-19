"""Export a colony and optional representative to a portable save file."""

from __future__ import annotations

import logging
from pathlib import Path

from colony_manager.adapters.io.mappers import domain_to_save_file
from colony_manager.application.services.user_service import UserService
from colony_manager.domain.models.colony import Colony
from colony_manager.domain.models.colony_user import ColonyUser
from colony_manager.domain.models.development_plan import DevelopmentPlan
from colony_manager.domain.models.event import Event
from colony_manager.domain.models.representative import Representative

logger = logging.getLogger(__name__)


class ColonyExporter:
    """Export colony data to a portable JSON format."""

    def export(
        self,
        colony: Colony,
        representative: Representative | None = None,
        events: list[Event] | None = None,
        development_plans: list[DevelopmentPlan] | None = None,
        colony_users: list[ColonyUser] | None = None,
        path: str | Path | None = None,
        user_service: UserService | None = None,
    ) -> str:
        """Export colony to JSON string or file.

        Args:
            colony: The colony domain model
            representative: Optional representative model
            events: Optional list of events
            development_plans: Optional list of development plans
            colony_users: Optional list of colony users
            path: Optional file path to write to
            user_service: Optional user service to look up usernames for colony users

        Returns:
            JSON string of the save file
        """
        # Enrich colony_users with usernames if user_service is provided
        enriched_colony_users = colony_users
        if colony_users and user_service:
            from colony_manager.adapters.io.mappers import domain_to_save_colony_user

            enriched_colony_users = []
            for cu in colony_users:
                save_cu = domain_to_save_colony_user(cu)
                # Look up username
                user = user_service.get_user(cu.user_id)
                if user:
                    save_cu.username = user.username
                else:
                    logger.warning(
                        "User ID %d not found during export of colony %d, username will be omitted",
                        cu.user_id,
                        colony.id,
                    )
                enriched_colony_users.append(save_cu)

        save_file = domain_to_save_file(
            colony, representative, events, development_plans, enriched_colony_users
        )
        payload = save_file.model_dump_json(indent=2)
        if path is not None:
            Path(path).write_text(payload, encoding="utf-8")
        return payload
