"""Real-time notification service using in-memory pub/sub."""

from __future__ import annotations

import asyncio
import contextlib
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class NotificationType(StrEnum):
    """Types of notifications that can be sent."""

    COLONY_CHANGED = "colony_changed"
    EVENT_CREATED = "event_created"
    EVENT_UPDATED = "event_updated"
    EVENT_DELETED = "event_deleted"
    DEVELOPMENT_PLAN_CREATED = "development_plan_created"
    DEVELOPMENT_PLAN_UPDATED = "development_plan_updated"
    DEVELOPMENT_PLAN_DELETED = "development_plan_deleted"
    COLONY_USER_ADDED = "colony_user_added"
    COLONY_USER_REMOVED = "colony_user_removed"
    COLONY_USER_ROLE_CHANGED = "colony_user_role_changed"


@dataclass
class Notification:
    """A notification message to be sent to clients."""

    type: NotificationType
    colony_id: int
    message: str
    user_id: int | None = None
    username: str | None = None
    entity_id: int | None = None
    entity_type: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert notification to dictionary for JSON serialization."""
        return {
            "type": self.type.value,
            "colony_id": self.colony_id,
            "message": self.message,
            "user_id": self.user_id,
            "username": self.username,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "timestamp": self.timestamp.isoformat(),
        }


class NotificationService:
    """Service for managing real-time notifications via pub/sub.

    Uses in-memory queues for simplicity. For production with multiple
    server instances, this would need to be backed by Redis or similar.
    """

    def __init__(self) -> None:
        # Map of user_id -> list of asyncio.Queue for that user
        self._subscribers: dict[int, list[asyncio.Queue[Notification]]] = defaultdict(list)
        self._lock = asyncio.Lock()

    def subscribe(self, user_id: int) -> asyncio.Queue[Notification]:
        """Subscribe to notifications for a user.

        Returns a queue that will receive notifications.
        """
        queue: asyncio.Queue[Notification] = asyncio.Queue()
        self._subscribers[user_id].append(queue)
        return queue

    def unsubscribe(self, user_id: int, queue: asyncio.Queue[Notification]) -> None:
        """Unsubscribe a specific queue for a user."""
        if user_id in self._subscribers:
            with contextlib.suppress(ValueError):  # Queue not in list
                self._subscribers[user_id].remove(queue)

    async def publish(self, notification: Notification) -> None:
        """Publish a notification to all subscribers.

        For now, publishes to all users. In a more sophisticated implementation,
        this would filter by colony membership.
        """
        async with self._lock:
            # Get all queues for users subscribed to this colony
            # For simplicity, broadcast to all users
            for queues in self._subscribers.values():
                for queue in queues:
                    with contextlib.suppress(asyncio.QueueFull):  # Skip if queue is full
                        queue.put_nowait(notification)

    async def publish_to_colony(
        self,
        colony_id: int,
        notification_type: NotificationType,
        message: str,
        user_id: int | None = None,
        username: str | None = None,
        entity_id: int | None = None,
        entity_type: str | None = None,
    ) -> None:
        """Convenience method to publish a colony-specific notification."""
        notification = Notification(
            type=notification_type,
            colony_id=colony_id,
            message=message,
            user_id=user_id,
            username=username,
            entity_id=entity_id,
            entity_type=entity_type,
        )
        await self.publish(notification)


# Global singleton instance
_notification_service: NotificationService | None = None


def get_notification_service() -> NotificationService:
    """Get the global notification service instance."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
