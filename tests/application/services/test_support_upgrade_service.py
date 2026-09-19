"""Tests for SupportUpgradeService - colony support upgrade management."""

from pathlib import Path

import pytest

from colony_manager.adapters.persistence.colony_repository_impl import SqlAlchemyColonyRepository
from colony_manager.adapters.persistence.db import init_db
from colony_manager.adapters.persistence.support_upgrade_repository_impl import (
    SqlAlchemySupportUpgradeRepository,
)
from colony_manager.application.services.support_upgrade_service import SupportUpgradeService
from colony_manager.domain.enums import ColonyType, SupportUpgradeType
from colony_manager.domain.errors import NotFoundError
from colony_manager.domain.models.colony import Colony
from colony_manager.domain.models.support_upgrade import SupportUpgrade


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


class TestSupportUpgradeServiceCreation:
    """Tests for support upgrade creation."""

    def test_create_upgrade_success(self, tmp_path):
        """Test successfully creating a support upgrade."""
        db_url = _create_db_url(tmp_path)
        upgrade_repo = SqlAlchemySupportUpgradeRepository(db_url)
        colony_repo = SqlAlchemyColonyRepository(db_url)
        service = SupportUpgradeService(
            repository=upgrade_repo,
            colony_repository=colony_repo,
        )

        colony = _create_colony(colony_repo)

        upgrade = SupportUpgrade(
            colony_id=colony.id,
            upgrade_type=SupportUpgradeType.INFANTRY_GARRISON,
        )
        result = service.create_upgrade(upgrade, changed_by=50)

        assert result.id is not None
        assert result.colony_id == colony.id
        assert result.upgrade_type == SupportUpgradeType.INFANTRY_GARRISON

    def test_create_upgrade_for_nonexistent_colony_raises(self, tmp_path):
        """Test creating upgrade for non-existent colony raises NotFoundError."""
        db_url = _create_db_url(tmp_path)
        upgrade_repo = SqlAlchemySupportUpgradeRepository(db_url)
        colony_repo = SqlAlchemyColonyRepository(db_url)
        service = SupportUpgradeService(
            repository=upgrade_repo,
            colony_repository=colony_repo,
        )

        upgrade = SupportUpgrade(
            colony_id=99999,
            upgrade_type=SupportUpgradeType.INFANTRY_GARRISON,
        )

        with pytest.raises(NotFoundError, match="Colony 99999 not found"):
            service.create_upgrade(upgrade, changed_by=50)

    def test_create_upgrade_all_types(self, tmp_path):
        """Test creating support upgrades of all types."""
        db_url = _create_db_url(tmp_path)
        upgrade_repo = SqlAlchemySupportUpgradeRepository(db_url)
        colony_repo = SqlAlchemyColonyRepository(db_url)
        service = SupportUpgradeService(
            repository=upgrade_repo,
            colony_repository=colony_repo,
        )

        colony = _create_colony(colony_repo)

        for upgrade_type in SupportUpgradeType:
            upgrade = SupportUpgrade(
                colony_id=colony.id,
                upgrade_type=upgrade_type,
            )
            result = service.create_upgrade(upgrade, changed_by=50)
            assert result.id is not None


class TestSupportUpgradeServiceQueries:
    """Tests for support upgrade queries."""

    def test_get_upgrade_by_id(self, tmp_path):
        """Test getting support upgrade by ID."""
        db_url = _create_db_url(tmp_path)
        upgrade_repo = SqlAlchemySupportUpgradeRepository(db_url)
        colony_repo = SqlAlchemyColonyRepository(db_url)
        service = SupportUpgradeService(
            repository=upgrade_repo,
            colony_repository=colony_repo,
        )

        colony = _create_colony(colony_repo)
        upgrade = SupportUpgrade(
            colony_id=colony.id,
            upgrade_type=SupportUpgradeType.CONTACTS,
        )
        created = service.create_upgrade(upgrade, changed_by=50)

        retrieved = service.get_upgrade(created.id)

        assert retrieved.id == created.id
        assert retrieved.upgrade_type == SupportUpgradeType.CONTACTS

    def test_get_nonexistent_upgrade_raises(self, tmp_path):
        """Test getting non-existent upgrade raises NotFoundError."""
        db_url = _create_db_url(tmp_path)
        upgrade_repo = SqlAlchemySupportUpgradeRepository(db_url)
        colony_repo = SqlAlchemyColonyRepository(db_url)
        service = SupportUpgradeService(
            repository=upgrade_repo,
            colony_repository=colony_repo,
        )

        with pytest.raises(NotFoundError, match="SupportUpgrade 99999 not found"):
            service.get_upgrade(99999)

    def test_list_by_colony(self, tmp_path):
        """Test listing all support upgrades for a colony."""
        db_url = _create_db_url(tmp_path)
        upgrade_repo = SqlAlchemySupportUpgradeRepository(db_url)
        colony_repo = SqlAlchemyColonyRepository(db_url)
        service = SupportUpgradeService(
            repository=upgrade_repo,
            colony_repository=colony_repo,
        )

        colony1 = _create_colony(colony_repo, "Colony 1")
        colony2 = _create_colony(colony_repo, "Colony 2")

        for _i in range(3):
            upgrade = SupportUpgrade(
                colony_id=colony1.id,
                upgrade_type=SupportUpgradeType.INFANTRY_GARRISON,
            )
            service.create_upgrade(upgrade, changed_by=50)

        for _i in range(2):
            upgrade = SupportUpgrade(
                colony_id=colony2.id,
                upgrade_type=SupportUpgradeType.CONTACTS,
            )
            service.create_upgrade(upgrade, changed_by=50)

        colony1_upgrades = service.list_by_colony(colony1.id)
        colony2_upgrades = service.list_by_colony(colony2.id)

        assert len(colony1_upgrades) == 3
        assert len(colony2_upgrades) == 2
        assert all(u.colony_id == colony1.id for u in colony1_upgrades)
        assert all(u.colony_id == colony2.id for u in colony2_upgrades)

    def test_list_by_colony_empty(self, tmp_path):
        """Test listing support upgrades for colony with none."""
        db_url = _create_db_url(tmp_path)
        upgrade_repo = SqlAlchemySupportUpgradeRepository(db_url)
        colony_repo = SqlAlchemyColonyRepository(db_url)
        service = SupportUpgradeService(
            repository=upgrade_repo,
            colony_repository=colony_repo,
        )

        colony = _create_colony(colony_repo)
        result = service.list_by_colony(colony.id)

        assert result == []

    def test_colony_exists_true(self, tmp_path):
        """Test colony_exists returns True for existing colony."""
        db_url = _create_db_url(tmp_path)
        upgrade_repo = SqlAlchemySupportUpgradeRepository(db_url)
        colony_repo = SqlAlchemyColonyRepository(db_url)
        service = SupportUpgradeService(
            repository=upgrade_repo,
            colony_repository=colony_repo,
        )

        colony = _create_colony(colony_repo)

        assert service.colony_exists(colony.id) is True

    def test_colony_exists_false(self, tmp_path):
        """Test colony_exists returns False for non-existent colony."""
        db_url = _create_db_url(tmp_path)
        upgrade_repo = SqlAlchemySupportUpgradeRepository(db_url)
        colony_repo = SqlAlchemyColonyRepository(db_url)
        service = SupportUpgradeService(
            repository=upgrade_repo,
            colony_repository=colony_repo,
        )

        assert service.colony_exists(99999) is False


class TestSupportUpgradeServiceUpdate:
    """Tests for support upgrade update operations."""

    def test_update_upgrade(self, tmp_path):
        """Test updating a support upgrade."""
        db_url = _create_db_url(tmp_path)
        upgrade_repo = SqlAlchemySupportUpgradeRepository(db_url)
        colony_repo = SqlAlchemyColonyRepository(db_url)
        service = SupportUpgradeService(
            repository=upgrade_repo,
            colony_repository=colony_repo,
        )

        colony = _create_colony(colony_repo)
        upgrade = SupportUpgrade(
            colony_id=colony.id,
            upgrade_type=SupportUpgradeType.INDUSTRIAL_FACILITY,
        )
        created = service.create_upgrade(upgrade, changed_by=50)

        created.custom_product = "Updated product"
        updated = service.update_upgrade(created, changed_by=60)

        assert updated.id == created.id
        assert updated.custom_product == "Updated product"

    def test_update_nonexistent_upgrade_raises(self, tmp_path):
        """Test updating non-existent upgrade raises NotFoundError."""
        db_url = _create_db_url(tmp_path)
        upgrade_repo = SqlAlchemySupportUpgradeRepository(db_url)
        colony_repo = SqlAlchemyColonyRepository(db_url)
        service = SupportUpgradeService(
            repository=upgrade_repo,
            colony_repository=colony_repo,
        )

        upgrade = SupportUpgrade(
            colony_id=1,
            upgrade_type=SupportUpgradeType.INFANTRY_GARRISON,
            id=99999,
        )

        with pytest.raises(NotFoundError):
            service.update_upgrade(upgrade, changed_by=50)


class TestSupportUpgradeServiceDelete:
    """Tests for support upgrade delete operations."""

    def test_delete_upgrade_success(self, tmp_path):
        """Test successfully deleting a support upgrade."""
        db_url = _create_db_url(tmp_path)
        upgrade_repo = SqlAlchemySupportUpgradeRepository(db_url)
        colony_repo = SqlAlchemyColonyRepository(db_url)
        service = SupportUpgradeService(
            repository=upgrade_repo,
            colony_repository=colony_repo,
        )

        colony = _create_colony(colony_repo)
        upgrade = SupportUpgrade(
            colony_id=colony.id,
            upgrade_type=SupportUpgradeType.INFANTRY_GARRISON,
        )
        created = service.create_upgrade(upgrade, changed_by=50)

        service.delete_upgrade(created.id, changed_by=50)

        with pytest.raises(NotFoundError):
            service.get_upgrade(created.id)

    def test_delete_nonexistent_upgrade_idempotent(self, tmp_path):
        """Test deleting non-existent upgrade is idempotent (no error)."""
        db_url = _create_db_url(tmp_path)
        upgrade_repo = SqlAlchemySupportUpgradeRepository(db_url)
        colony_repo = SqlAlchemyColonyRepository(db_url)
        service = SupportUpgradeService(
            repository=upgrade_repo,
            colony_repository=colony_repo,
        )

        service.delete_upgrade(99999, changed_by=50)
