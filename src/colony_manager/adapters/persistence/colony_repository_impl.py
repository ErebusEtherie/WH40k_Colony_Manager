"""SQLite-backed colony repository implementation."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, joinedload

from colony_manager.adapters.persistence.mappers import (
    domain_to_orm_colony,
    domain_to_orm_modifier,
    orm_to_domain_colony,
)
from colony_manager.adapters.persistence.orm_models import Base, ColonyORM
from colony_manager.domain.models.colony import Colony
from colony_manager.domain.ports.colony_repository import ColonyRepository


class SqlAlchemyColonyRepository(ColonyRepository):
    def __init__(self, database_url: str = "sqlite:///:memory:") -> None:
        self._engine = create_engine(database_url)
        Base.metadata.create_all(self._engine)

    def create(self, colony: Colony) -> Colony:
        with Session(self._engine) as session:
            orm = domain_to_orm_colony(colony)
            session.add(orm)
            session.commit()
            session.refresh(orm)
            return orm_to_domain_colony(orm)

    def get(self, colony_id: int) -> Colony | None:
        with Session(self._engine) as session:
            orm = session.get(ColonyORM, colony_id)
            if orm is None:
                return None
            # Eager load relationships
            session.refresh(orm, ["modifiers", "infrastructure", "support_upgrades"])
            if orm is None:
                return None
            return orm_to_domain_colony(orm)

    def update(self, colony: Colony) -> Colony:
        with Session(self._engine) as session:
            orm = session.get(ColonyORM, colony.id)
            if orm is None:
                raise ValueError(f"Colony {colony.id} not found")
            orm.name = colony.name
            orm.founder_name = colony.founder_name
            orm.patron_name = colony.patron_name
            orm.star_system = colony.star_system
            orm.colony_type = colony.colony_type
            orm.age_days = colony.age_days
            orm.age_last_updated = colony.age_last_updated
            orm.current_event = colony.current_event
            orm.notes = colony.notes
            orm.base_complacency = colony.base_complacency
            orm.base_order = colony.base_order
            orm.base_productivity = colony.base_productivity
            orm.base_piety = colony.base_piety
            orm.base_size = colony.base_size
            orm.representative_id = colony.representative_id
            orm.dynasty_outcome = colony.dynasty_outcome.value if colony.dynasty_outcome else None
            orm.complacency_locked = colony.complacency_locked
            orm.order_locked = colony.order_locked
            orm.productivity_locked = colony.productivity_locked
            # Serialize planetary_resources to JSON
            import json

            if colony.planetary_resources:
                orm.planetary_resources = json.dumps([r.value for r in colony.planetary_resources])
            else:
                orm.planetary_resources = None
            orm.modifiers = [domain_to_orm_modifier(modifier) for modifier in colony.modifiers]
            session.commit()
            return orm_to_domain_colony(orm)

    def delete(self, colony_id: int) -> None:
        with Session(self._engine) as session:
            orm = session.get(ColonyORM, colony_id)
            if orm is None:
                return
            # Eager load relationships
            session.refresh(orm, ["modifiers", "infrastructure", "support_upgrades"])
            if orm is not None:
                session.delete(orm)
                session.commit()

    def list(self) -> list[Colony]:
        with Session(self._engine) as session:
            return [
                orm_to_domain_colony(orm)
                for orm in session.query(ColonyORM)
                .options(
                    joinedload(ColonyORM.modifiers),
                    joinedload(ColonyORM.infrastructure),
                    joinedload(ColonyORM.support_upgrades),
                )
                .all()
            ]
