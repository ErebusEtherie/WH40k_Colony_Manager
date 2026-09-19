"""Tests for InfrastructureService - colony infrastructure management."""

from pathlib import Path

import pytest

from colony_manager.adapters.persistence.colony_repository_impl import SqlAlchemyColonyRepository
from colony_manager.adapters.persistence.db import init_db
from colony_manager.adapters.persistence.infrastructure_repository_impl import (
    SqlAlchemyInfrastructureRepository,
)
from colony_manager.adapters.persistence.repositories.audit_log_repository_impl import (
    SqlAlchemyAuditLogRepository,
)
from colony_manager.application.services.infrastructure_service import InfrastructureService
from colony_manager.domain.enums import ColonyType, InfrastructureState, InfrastructureType
from colony_manager.domain.errors import NotFoundError
from colony_manager.domain.models.colony import Colony
from colony_manager.domain.models.infrastructure import Infrastructure


def _create_db_url(tmp_path: Path) -> str:
    """Helper to create and initialize a test database."""
    db_path = tmp_path / "test.db"
    init_db(db_path)
    return f"sqlite:///{db_path.as_posix()}"


def _create_colony(colony_repo, name="Test Colony"):
    """Helper to create a test colony."""
    from datetime import date

    colony = Colony(
        name=name,
        founder_name="Test Founder",
        colony_type=ColonyType.MINING_AND_INDUSTRY,
        age_days=0,
        age_last_updated=date.today(),
        base_complacency=10,
        base_order=10,
        base_productivity=10,
        base_piety=10,
        base_size=10,
    )
    return colony_repo.create(colony)


class TestInfrastructureServiceCreation:
    """Tests for infrastructure creation."""

    def test_create_infrastructure_success(self, tmp_path):
        """Test successfully creating infrastructure."""
        db_url = _create_db_url(tmp_path)
        infra_repo = SqlAlchemyInfrastructureRepository(db_url)
        colony_repo = SqlAlchemyColonyRepository(db_url)
        service = InfrastructureService(
            repository=infra_repo,
            colony_repository=colony_repo,
        )

        colony = _create_colony(colony_repo)

        infra = Infrastructure(
            colony_id=colony.id,
            infrastructure_type=InfrastructureType.POWER_NETWORK,
            state=InfrastructureState.WORKING,
        )
        result = service.create_infrastructure(infra, changed_by=50)

        assert result.id is not None
        assert result.colony_id == colony.id
        assert result.infrastructure_type == InfrastructureType.POWER_NETWORK
        assert result.state == InfrastructureState.WORKING

    def test_create_infrastructure_for_nonexistent_colony_raises(self, tmp_path):
        """Test creating infrastructure for non-existent colony raises NotFoundError."""
        db_url = _create_db_url(tmp_path)
        infra_repo = SqlAlchemyInfrastructureRepository(db_url)
        colony_repo = SqlAlchemyColonyRepository(db_url)
        service = InfrastructureService(
            repository=infra_repo,
            colony_repository=colony_repo,
        )

        infra = Infrastructure(
            colony_id=99999,
            infrastructure_type=InfrastructureType.POWER_NETWORK,
            state=InfrastructureState.WORKING,
        )

        with pytest.raises(NotFoundError, match="Colony 99999 not found"):
            service.create_infrastructure(infra, changed_by=50)

    def test_create_infrastructure_all_types(self, tmp_path):
        """Test creating infrastructure of all types."""
        db_url = _create_db_url(tmp_path)
        infra_repo = SqlAlchemyInfrastructureRepository(db_url)
        colony_repo = SqlAlchemyColonyRepository(db_url)
        service = InfrastructureService(
            repository=infra_repo,
            colony_repository=colony_repo,
        )

        colony = _create_colony(colony_repo)

        for infra_type in InfrastructureType:
            infra = Infrastructure(
                colony_id=colony.id,
                infrastructure_type=infra_type,
                state=InfrastructureState.WORKING,
            )
            result = service.create_infrastructure(infra, changed_by=50)
            assert result.id is not None


class TestInfrastructureServiceQueries:
    """Tests for infrastructure queries."""

    def test_get_infrastructure_by_id(self, tmp_path):
        """Test getting infrastructure by ID."""
        db_url = _create_db_url(tmp_path)
        infra_repo = SqlAlchemyInfrastructureRepository(db_url)
        colony_repo = SqlAlchemyColonyRepository(db_url)
        service = InfrastructureService(
            repository=infra_repo,
            colony_repository=colony_repo,
        )

        colony = _create_colony(colony_repo)
        infra = Infrastructure(
            colony_id=colony.id,
            infrastructure_type=InfrastructureType.WATER_MANAGEMENT,
            state=InfrastructureState.WORKING,
        )
        created = service.create_infrastructure(infra, changed_by=50)

        retrieved = service.get_infrastructure(created.id)

        assert retrieved.id == created.id
        assert retrieved.infrastructure_type == InfrastructureType.WATER_MANAGEMENT

    def test_get_nonexistent_infrastructure_raises(self, tmp_path):
        """Test getting non-existent infrastructure raises NotFoundError."""
        db_url = _create_db_url(tmp_path)
        infra_repo = SqlAlchemyInfrastructureRepository(db_url)
        colony_repo = SqlAlchemyColonyRepository(db_url)
        service = InfrastructureService(
            repository=infra_repo,
            colony_repository=colony_repo,
        )

        with pytest.raises(NotFoundError, match="Infrastructure 99999 not found"):
            service.get_infrastructure(99999)

    def test_list_by_colony(self, tmp_path):
        """Test listing all infrastructure for a colony."""
        db_url = _create_db_url(tmp_path)
        infra_repo = SqlAlchemyInfrastructureRepository(db_url)
        colony_repo = SqlAlchemyColonyRepository(db_url)
        service = InfrastructureService(
            repository=infra_repo,
            colony_repository=colony_repo,
        )

        colony1 = _create_colony(colony_repo, "Colony 1")
        colony2 = _create_colony(colony_repo, "Colony 2")

        for _i in range(3):
            infra = Infrastructure(
                colony_id=colony1.id,
                infrastructure_type=InfrastructureType.POWER_NETWORK,
                state=InfrastructureState.WORKING,
            )
            service.create_infrastructure(infra, changed_by=50)

        for _i in range(2):
            infra = Infrastructure(
                colony_id=colony2.id,
                infrastructure_type=InfrastructureType.COMMUNICATIONS,
                state=InfrastructureState.WORKING,
            )
            service.create_infrastructure(infra, changed_by=50)

        colony1_infra = service.list_by_colony(colony1.id)
        colony2_infra = service.list_by_colony(colony2.id)

        assert len(colony1_infra) == 3
        assert len(colony2_infra) == 2
        assert all(i.colony_id == colony1.id for i in colony1_infra)
        assert all(i.colony_id == colony2.id for i in colony2_infra)

    def test_list_by_colony_empty(self, tmp_path):
        """Test listing infrastructure for colony with none."""
        db_url = _create_db_url(tmp_path)
        infra_repo = SqlAlchemyInfrastructureRepository(db_url)
        colony_repo = SqlAlchemyColonyRepository(db_url)
        service = InfrastructureService(
            repository=infra_repo,
            colony_repository=colony_repo,
        )

        colony = _create_colony(colony_repo)
        result = service.list_by_colony(colony.id)

        assert result == []

    def test_colony_exists_true(self, tmp_path):
        """Test colony_exists returns True for existing colony."""
        db_url = _create_db_url(tmp_path)
        infra_repo = SqlAlchemyInfrastructureRepository(db_url)
        colony_repo = SqlAlchemyColonyRepository(db_url)
        service = InfrastructureService(
            repository=infra_repo,
            colony_repository=colony_repo,
        )

        colony = _create_colony(colony_repo)

        assert service.colony_exists(colony.id) is True

    def test_colony_exists_false(self, tmp_path):
        """Test colony_exists returns False for non-existent colony."""
        db_url = _create_db_url(tmp_path)
        infra_repo = SqlAlchemyInfrastructureRepository(db_url)
        colony_repo = SqlAlchemyColonyRepository(db_url)
        service = InfrastructureService(
            repository=infra_repo,
            colony_repository=colony_repo,
        )

        assert service.colony_exists(99999) is False


class TestInfrastructureServiceUpdate:
    """Tests for infrastructure update operations."""

    def test_update_infrastructure_state(self, tmp_path):
        """Test updating infrastructure state."""
        db_url = _create_db_url(tmp_path)
        infra_repo = SqlAlchemyInfrastructureRepository(db_url)
        colony_repo = SqlAlchemyColonyRepository(db_url)
        service = InfrastructureService(
            repository=infra_repo,
            colony_repository=colony_repo,
        )

        colony = _create_colony(colony_repo)
        infra = Infrastructure(
            colony_id=colony.id,
            infrastructure_type=InfrastructureType.POWER_NETWORK,
            state=InfrastructureState.WORKING,
        )
        created = service.create_infrastructure(infra, changed_by=50)

        updated = service.update_infrastructure_state(
            created.id,
            InfrastructureState.NOT_WORKING,
            changed_by=60,
        )

        assert updated.id == created.id
        assert updated.state == InfrastructureState.NOT_WORKING

    def test_update_nonexistent_infrastructure_raises(self, tmp_path):
        """Test updating non-existent infrastructure raises NotFoundError."""
        db_url = _create_db_url(tmp_path)
        infra_repo = SqlAlchemyInfrastructureRepository(db_url)
        colony_repo = SqlAlchemyColonyRepository(db_url)
        service = InfrastructureService(
            repository=infra_repo,
            colony_repository=colony_repo,
        )

        with pytest.raises(NotFoundError, match="Infrastructure 99999 not found"):
            service.update_infrastructure_state(
                99999, InfrastructureState.NOT_WORKING, changed_by=50
            )

    def test_update_state_all_states(self, tmp_path):
        """Test updating to all possible states."""
        db_url = _create_db_url(tmp_path)
        infra_repo = SqlAlchemyInfrastructureRepository(db_url)
        colony_repo = SqlAlchemyColonyRepository(db_url)
        service = InfrastructureService(
            repository=infra_repo,
            colony_repository=colony_repo,
        )

        colony = _create_colony(colony_repo)
        infra = Infrastructure(
            colony_id=colony.id,
            infrastructure_type=InfrastructureType.POWER_NETWORK,
            state=InfrastructureState.WORKING,
        )
        created = service.create_infrastructure(infra, changed_by=50)

        for state in InfrastructureState:
            updated = service.update_infrastructure_state(created.id, state, changed_by=50)
            assert updated.state == state


class TestInfrastructureServiceDelete:
    """Tests for infrastructure delete operations."""

    def test_delete_infrastructure_success(self, tmp_path):
        """Test successfully deleting infrastructure."""
        db_url = _create_db_url(tmp_path)
        infra_repo = SqlAlchemyInfrastructureRepository(db_url)
        colony_repo = SqlAlchemyColonyRepository(db_url)
        service = InfrastructureService(
            repository=infra_repo,
            colony_repository=colony_repo,
        )

        colony = _create_colony(colony_repo)
        infra = Infrastructure(
            colony_id=colony.id,
            infrastructure_type=InfrastructureType.POWER_NETWORK,
            state=InfrastructureState.WORKING,
        )
        created = service.create_infrastructure(infra, changed_by=50)

        service.delete_infrastructure(created.id, changed_by=50)

        with pytest.raises(NotFoundError):
            service.get_infrastructure(created.id)

    def test_delete_nonexistent_infrastructure_idempotent(self, tmp_path):
        """Test deleting non-existent infrastructure is idempotent (no error)."""
        db_url = _create_db_url(tmp_path)
        infra_repo = SqlAlchemyInfrastructureRepository(db_url)
        colony_repo = SqlAlchemyColonyRepository(db_url)
        service = InfrastructureService(
            repository=infra_repo,
            colony_repository=colony_repo,
        )

        service.delete_infrastructure(99999, changed_by=50)


class TestInfrastructureServiceAuditLogging:
    """Tests for audit logging in infrastructure operations."""

    def test_audit_log_created_on_create(self, tmp_path):
        """Test audit log entry created when creating infrastructure."""
        db_url = _create_db_url(tmp_path)
        infra_repo = SqlAlchemyInfrastructureRepository(db_url)
        colony_repo = SqlAlchemyColonyRepository(db_url)
        audit_repo = SqlAlchemyAuditLogRepository(db_url)
        service = InfrastructureService(
            repository=infra_repo,
            colony_repository=colony_repo,
            audit_log_repository=audit_repo,
        )

        colony = _create_colony(colony_repo)
        infra = Infrastructure(
            colony_id=colony.id,
            infrastructure_type=InfrastructureType.POWER_NETWORK,
            state=InfrastructureState.WORKING,
        )
        created = service.create_infrastructure(infra, changed_by=50)

        logs = audit_repo.get_by_entity("infrastructure", created.id)
        assert len(logs) == 1
        assert logs[0].action.value == "create"
        assert logs[0].changed_by == 50
        assert logs[0].new_value == InfrastructureType.POWER_NETWORK.value

    def test_audit_log_created_on_update(self, tmp_path):
        """Test audit log entry created when updating infrastructure."""
        db_url = _create_db_url(tmp_path)
        infra_repo = SqlAlchemyInfrastructureRepository(db_url)
        colony_repo = SqlAlchemyColonyRepository(db_url)
        audit_repo = SqlAlchemyAuditLogRepository(db_url)
        service = InfrastructureService(
            repository=infra_repo,
            colony_repository=colony_repo,
            audit_log_repository=audit_repo,
        )

        colony = _create_colony(colony_repo)
        infra = Infrastructure(
            colony_id=colony.id,
            infrastructure_type=InfrastructureType.POWER_NETWORK,
            state=InfrastructureState.WORKING,
        )
        created = service.create_infrastructure(infra, changed_by=50)

        service.update_infrastructure_state(
            created.id, InfrastructureState.NOT_WORKING, changed_by=60
        )

        logs = audit_repo.get_by_entity("infrastructure", created.id)
        assert len(logs) == 2
        update_log = next(log for log in logs if log.action.value == "update")
        assert update_log.changed_by == 60
        assert update_log.field == "state"
        assert update_log.old_value == InfrastructureState.WORKING.value
        assert update_log.new_value == InfrastructureState.NOT_WORKING.value

    def test_audit_log_created_on_delete(self, tmp_path):
        """Test audit log entry created when deleting infrastructure."""
        db_url = _create_db_url(tmp_path)
        infra_repo = SqlAlchemyInfrastructureRepository(db_url)
        colony_repo = SqlAlchemyColonyRepository(db_url)
        audit_repo = SqlAlchemyAuditLogRepository(db_url)
        service = InfrastructureService(
            repository=infra_repo,
            colony_repository=colony_repo,
            audit_log_repository=audit_repo,
        )

        colony = _create_colony(colony_repo)
        infra = Infrastructure(
            colony_id=colony.id,
            infrastructure_type=InfrastructureType.POWER_NETWORK,
            state=InfrastructureState.WORKING,
        )
        created = service.create_infrastructure(infra, changed_by=50)

        service.delete_infrastructure(created.id, changed_by=60)

        logs = audit_repo.get_by_entity("infrastructure", created.id)
        assert len(logs) == 2
        delete_log = next(log for log in logs if log.action.value == "delete")
        assert delete_log.changed_by == 60
        assert delete_log.old_value == InfrastructureType.POWER_NETWORK.value
        assert delete_log.new_value is None

    def test_service_without_audit_repo(self, tmp_path):
        """Test service works without audit log repository."""
        db_url = _create_db_url(tmp_path)
        infra_repo = SqlAlchemyInfrastructureRepository(db_url)
        colony_repo = SqlAlchemyColonyRepository(db_url)
        service = InfrastructureService(
            repository=infra_repo,
            colony_repository=colony_repo,
        )

        colony = _create_colony(colony_repo)
        infra = Infrastructure(
            colony_id=colony.id,
            infrastructure_type=InfrastructureType.POWER_NETWORK,
            state=InfrastructureState.WORKING,
        )

        created = service.create_infrastructure(infra, changed_by=50)
        service.update_infrastructure_state(
            created.id, InfrastructureState.NOT_WORKING, changed_by=50
        )
        service.delete_infrastructure(created.id, changed_by=50)

        assert created.id is not None

    def test_create_without_changed_by_no_audit(self, tmp_path):
        """Test creating without changed_by doesn't create audit log."""
        db_url = _create_db_url(tmp_path)
        infra_repo = SqlAlchemyInfrastructureRepository(db_url)
        colony_repo = SqlAlchemyColonyRepository(db_url)
        audit_repo = SqlAlchemyAuditLogRepository(db_url)
        service = InfrastructureService(
            repository=infra_repo,
            colony_repository=colony_repo,
            audit_log_repository=audit_repo,
        )

        colony = _create_colony(colony_repo)
        infra = Infrastructure(
            colony_id=colony.id,
            infrastructure_type=InfrastructureType.POWER_NETWORK,
            state=InfrastructureState.WORKING,
        )
        created = service.create_infrastructure(infra, changed_by=None)

        logs = audit_repo.get_by_entity("infrastructure", created.id)
        assert len(logs) == 0
