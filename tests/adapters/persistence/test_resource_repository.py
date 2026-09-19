"""Tests for the resource repository implementation."""

from datetime import date

from colony_manager.adapters.persistence.resource_repository_impl import (
    SqlAlchemyResourceRepository,
)
from colony_manager.domain.enums import ResourceType
from colony_manager.domain.models.resource import ColonyResource


class TestResourceRepository:
    def test_create_and_get(self):
        repo = SqlAlchemyResourceRepository("sqlite:///:memory:")
        resource = ColonyResource(
            colony_id=1,
            resource_type=ResourceType.MINERAL,
            name="Adamantium Veins",
            abundance=75,
            notes="Rich deposits",
            discovered_date=date(2024, 1, 1),
        )
        saved = repo.create(resource)
        assert saved.id is not None
        loaded = repo.get(saved.id)
        assert loaded.name == "Adamantium Veins"

    def test_abundance_level_property(self):
        repo = SqlAlchemyResourceRepository("sqlite:///:memory:")
        test_cases = [
            (0, "Minimal"),
            (15, "Minimal"),
            (16, "Limited"),
            (40, "Limited"),
            (41, "Sustainable"),
            (65, "Sustainable"),
            (66, "Significant"),
            (85, "Significant"),
            (86, "Major"),
            (98, "Major"),
            (99, "Plentiful"),
            (150, "Plentiful"),
        ]
        for abundance, expected in test_cases:
            resource = ColonyResource(
                colony_id=1,
                resource_type=ResourceType.MINERAL,
                name=f"Test {abundance}",
                abundance=abundance,
                discovered_date=date(2024, 1, 1),
            )
            saved = repo.create(resource)
            assert saved.abundance_level == expected

    def test_update(self):
        repo = SqlAlchemyResourceRepository("sqlite:///:memory:")
        resource = ColonyResource(
            colony_id=1,
            resource_type=ResourceType.MINERAL,
            name="Iron",
            abundance=50,
            notes="Initial",
            discovered_date=date(2024, 1, 1),
        )
        saved = repo.create(resource)
        saved.abundance = 85
        saved.notes = "Updated"
        updated = repo.update(saved)
        assert updated.abundance == 85
        assert updated.notes == "Updated"

    def test_delete(self):
        repo = SqlAlchemyResourceRepository("sqlite:///:memory:")
        resource = ColonyResource(
            colony_id=1,
            resource_type=ResourceType.ORGANIC_COMPOUND,
            name="Fungi",
            abundance=30,
            discovered_date=date(2024, 1, 1),
        )
        saved = repo.create(resource)
        repo.delete(saved.id)
        try:
            repo.get(saved.id)
            raise AssertionError()
        except ValueError:
            pass  # Expected

    def test_delete_nonexistent(self):
        repo = SqlAlchemyResourceRepository("sqlite:///:memory:")
        repo.delete(9999)

    def test_get_by_colony(self):
        repo = SqlAlchemyResourceRepository("sqlite:///:memory:")
        repo.create(
            ColonyResource(
                colony_id=1,
                resource_type=ResourceType.MINERAL,
                name="Iron",
                abundance=50,
                discovered_date=date(2024, 1, 1),
            )
        )
        repo.create(
            ColonyResource(
                colony_id=1,
                resource_type=ResourceType.ORGANIC_COMPOUND,
                name="Fungi",
                abundance=30,
                discovered_date=date(2024, 1, 1),
            )
        )
        repo.create(
            ColonyResource(
                colony_id=2,
                resource_type=ResourceType.ARCHEOTECH_CACHE,
                name="STC",
                abundance=10,
                discovered_date=date(2024, 1, 1),
            )
        )
        assert len(repo.get_by_colony(1)) == 2
        assert len(repo.get_by_colony(2)) == 1

    def test_get_by_colony_empty(self):
        repo = SqlAlchemyResourceRepository("sqlite:///:memory:")
        assert repo.get_by_colony(999) == []

    def test_delete_by_colony(self):
        repo = SqlAlchemyResourceRepository("sqlite:///:memory:")
        repo.create(
            ColonyResource(
                colony_id=1,
                resource_type=ResourceType.MINERAL,
                name="Iron",
                abundance=50,
                discovered_date=date(2024, 1, 1),
            )
        )
        repo.create(
            ColonyResource(
                colony_id=1,
                resource_type=ResourceType.ORGANIC_COMPOUND,
                name="Fungi",
                abundance=30,
                discovered_date=date(2024, 1, 1),
            )
        )
        repo.create(
            ColonyResource(
                colony_id=2,
                resource_type=ResourceType.XENOS_RUINS,
                name="Temple",
                abundance=5,
                discovered_date=date(2024, 1, 1),
            )
        )
        repo.delete_by_colony(1)
        assert len(repo.get_by_colony(1)) == 0
        assert len(repo.get_by_colony(2)) == 1

    def test_get_raises_for_missing(self):
        repo = SqlAlchemyResourceRepository("sqlite:///:memory:")
        try:
            repo.get(9999)
            raise AssertionError()
        except ValueError as e:
            assert "not found" in str(e).lower()

    def test_update_raises_for_missing(self):
        repo = SqlAlchemyResourceRepository("sqlite:///:memory:")
        resource = ColonyResource(
            id=9999,
            colony_id=1,
            resource_type=ResourceType.MINERAL,
            name="Test",
            abundance=50,
            discovered_date=date(2024, 1, 1),
        )
        try:
            repo.update(resource)
            raise AssertionError()
        except ValueError as e:
            assert "not found" in str(e).lower()

    def test_all_resource_types(self):
        repo = SqlAlchemyResourceRepository("sqlite:///:memory:")
        for rt in ResourceType:
            resource = ColonyResource(
                colony_id=1,
                resource_type=rt,
                name=f"Test {rt.value}",
                abundance=50,
                discovered_date=date(2024, 1, 1),
            )
            saved = repo.create(resource)
            assert saved.resource_type == rt

    def test_zero_abundance(self):
        repo = SqlAlchemyResourceRepository("sqlite:///:memory:")
        resource = ColonyResource(
            colony_id=1,
            resource_type=ResourceType.MINERAL,
            name="Depleted",
            abundance=0,
            discovered_date=date(2024, 1, 1),
        )
        saved = repo.create(resource)
        assert saved.abundance == 0
        assert saved.abundance_level == "Minimal"
