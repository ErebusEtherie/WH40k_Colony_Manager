"""Tests for the resource service."""

from datetime import date

from colony_manager.adapters.persistence.colony_repository_impl import SqlAlchemyColonyRepository
from colony_manager.adapters.persistence.resource_repository_impl import (
    SqlAlchemyResourceRepository,
)
from colony_manager.application.services.resource_service import ResourceService
from colony_manager.domain.enums import ResourceType
from colony_manager.domain.errors import NotFoundError
from colony_manager.domain.models.colony import Colony


class TestResourceService:
    def setup_method(self):
        """Set up test fixtures."""
        self.db_url = "sqlite:///:memory:"
        self.colony_repo = SqlAlchemyColonyRepository(self.db_url)
        self.resource_repo = SqlAlchemyResourceRepository(self.db_url)
        self.service = ResourceService(self.resource_repo, self.colony_repo)

    def _create_colony(self):
        """Helper to create a test colony."""
        colony = Colony(
            name="Test Colony",
            founder_name="Test Founder",
            colony_type="mining_and_industry",
            age_days=0,
            age_last_updated=date.today(),
            base_complacency=10,
            base_order=10,
            base_productivity=10,
            base_piety=10,
            base_size=5,
        )
        return self.colony_repo.create(colony)

    def test_add_resource(self):
        """Test adding a resource to a colony."""
        colony = self._create_colony()

        resource = self.service.add_resource(
            colony_id=colony.id,
            resource_type="mineral",
            name="Iron Veins",
            abundance=75,
            notes="Rich deposits",
        )

        assert resource.id is not None
        assert resource.colony_id == colony.id
        assert resource.resource_type == ResourceType.MINERAL
        assert resource.name == "Iron Veins"
        assert resource.abundance == 75

    def test_add_resource_to_missing_colony_raises(self):
        """Test that adding a resource to a missing colony raises NotFoundError."""
        try:
            self.service.add_resource(
                colony_id=9999,
                resource_type="mineral",
                name="Test",
                abundance=50,
            )
            raise AssertionError("Should have raised NotFoundError")
        except NotFoundError:
            pass

    def test_get_resource(self):
        """Test getting a resource by ID."""
        colony = self._create_colony()

        resource = self.service.add_resource(
            colony_id=colony.id,
            resource_type="mineral",
            name="Iron",
            abundance=50,
        )

        fetched = self.service.get_resource(resource.id)
        assert fetched.id == resource.id
        assert fetched.name == "Iron"

    def test_list_resources(self):
        """Test listing resources for a colony."""
        colony1 = self._create_colony()
        colony2 = self._create_colony()
        colony2.name = "Colony 2"
        colony2 = self.colony_repo.update(colony2)

        self.service.add_resource(
            colony_id=colony1.id, resource_type="mineral", name="Iron", abundance=50
        )
        self.service.add_resource(
            colony_id=colony1.id, resource_type="organic_compound", name="Fungi", abundance=30
        )
        self.service.add_resource(
            colony_id=colony2.id, resource_type="archeotech_cache", name="STC", abundance=10
        )

        colony1_resources = self.service.list_resources(colony1.id)
        colony2_resources = self.service.list_resources(colony2.id)

        assert len(colony1_resources) == 2
        assert len(colony2_resources) == 1

    def test_update_resource(self):
        """Test updating a resource's abundance and notes."""
        colony = self._create_colony()

        resource = self.service.add_resource(
            colony_id=colony.id,
            resource_type="mineral",
            name="Iron",
            abundance=50,
            notes="Initial",
        )

        updated = self.service.update_resource(
            resource_id=resource.id,
            abundance=85,
            notes="Updated notes",
        )

        assert updated.abundance == 85
        assert updated.notes == "Updated notes"

    def test_update_resource_partial(self):
        """Test updating only abundance or only notes."""
        colony = self._create_colony()

        resource = self.service.add_resource(
            colony_id=colony.id,
            resource_type="mineral",
            name="Iron",
            abundance=50,
            notes="Initial",
        )

        # Update only abundance
        updated = self.service.update_resource(resource_id=resource.id, abundance=100)
        assert updated.abundance == 100
        assert updated.notes == "Initial"

        # Update only notes
        updated = self.service.update_resource(resource_id=resource.id, notes="New notes")
        assert updated.abundance == 100
        assert updated.notes == "New notes"

    def test_remove_resource(self):
        """Test removing a resource."""
        colony = self._create_colony()

        resource = self.service.add_resource(
            colony_id=colony.id,
            resource_type="mineral",
            name="Iron",
            abundance=50,
        )

        self.service.remove_resource(resource.id)

        try:
            self.service.get_resource(resource.id)
            raise AssertionError("Should have raised ValueError")
        except ValueError:
            pass
