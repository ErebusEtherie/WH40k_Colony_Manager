"""SQLAlchemy implementation of ColonyUserRepository."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from colony_manager.adapters.persistence.mappers import (
    domain_to_orm_colony_user,
    orm_to_domain_colony_user,
)
from colony_manager.adapters.persistence.orm_models import ColonyUserORM
from colony_manager.domain.errors import NotFoundError
from colony_manager.domain.models.colony_user import ColonyUser
from colony_manager.domain.ports.colony_user_repository import ColonyUserRepository


class SqlAlchemyColonyUserRepository(ColonyUserRepository):
    """SQLAlchemy implementation of ColonyUserRepository.

    This implementation uses SQLAlchemy for database operations and follows
    the repository pattern defined in the domain layer.
    """

    def __init__(self, database_url: str = "sqlite:///:memory:") -> None:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        self._engine = create_engine(database_url)
        self._session_factory = sessionmaker(bind=self._engine, autoflush=False, autocommit=False)

    def _get_session(self) -> Any:
        """Get a database session."""

        return self._session_factory()

    def create(self, colony_user: ColonyUser) -> ColonyUser:
        """Create a new colony-user membership in the database."""
        with self._get_session() as session:
            # Check for existing membership
            existing = session.execute(
                select(ColonyUserORM).where(
                    ColonyUserORM.colony_id == colony_user.colony_id,
                    ColonyUserORM.user_id == colony_user.user_id,
                )
            ).scalar_one_or_none()

            if existing:
                raise ValueError(
                    f"User {colony_user.user_id} is already a member of "
                    f"colony {colony_user.colony_id}"
                )

            orm_membership = domain_to_orm_colony_user(colony_user)
            orm_membership.joined_at = datetime.now(UTC)

            session.add(orm_membership)
            session.commit()
            session.refresh(orm_membership)

            return orm_to_domain_colony_user(orm_membership)

    def get_by_id(self, membership_id: int) -> ColonyUser | None:
        """Get colony-user membership by ID."""
        with self._get_session() as session:
            orm_membership = session.get(ColonyUserORM, membership_id)
            if orm_membership is None:
                return None
            return orm_to_domain_colony_user(orm_membership)

    def get_by_colony_and_user(self, colony_id: int, user_id: int) -> ColonyUser | None:
        """Get colony-user membership by colony and user IDs."""
        with self._get_session() as session:
            orm_membership = session.execute(
                select(ColonyUserORM).where(
                    ColonyUserORM.colony_id == colony_id,
                    ColonyUserORM.user_id == user_id,
                )
            ).scalar_one_or_none()

            if orm_membership is None:
                return None
            return orm_to_domain_colony_user(orm_membership)

    def get_by_colony(self, colony_id: int) -> list[ColonyUser]:
        """Get all memberships for a colony."""
        with self._get_session() as session:
            result = session.execute(
                select(ColonyUserORM).where(ColonyUserORM.colony_id == colony_id)
            )
            orm_memberships = result.scalars().all()
            return [orm_to_domain_colony_user(orm) for orm in orm_memberships]

    def get_by_user(self, user_id: int) -> list[ColonyUser]:
        """Get all memberships for a user."""
        with self._get_session() as session:
            result = session.execute(select(ColonyUserORM).where(ColonyUserORM.user_id == user_id))
            orm_memberships = result.scalars().all()
            return [orm_to_domain_colony_user(orm) for orm in orm_memberships]

    def update(self, colony_user: ColonyUser) -> ColonyUser:
        """Update an existing colony-user membership."""
        if colony_user.id is None:
            raise NotFoundError("Membership ID is required for update")

        with self._get_session() as session:
            orm_membership = session.get(ColonyUserORM, colony_user.id)

            if orm_membership is None:
                raise NotFoundError(f"Membership with ID {colony_user.id} not found")

            # Update fields
            orm_membership.role = (
                colony_user.role.value if hasattr(colony_user.role, "value") else colony_user.role
            )

            session.commit()
            session.refresh(orm_membership)

            return orm_to_domain_colony_user(orm_membership)

    def delete(self, membership_id: int) -> None:
        """Delete a colony-user membership."""
        with self._get_session() as session:
            orm_membership = session.get(ColonyUserORM, membership_id)

            if orm_membership is None:
                raise NotFoundError(f"Membership with ID {membership_id} not found")

            session.delete(orm_membership)
            session.commit()
