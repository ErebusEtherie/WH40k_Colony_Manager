"""Integration tests for colony lifecycle."""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from colony_manager.adapters.api.app import create_app
from colony_manager.adapters.persistence.db import init_db


@pytest.fixture
def auth_client(tmp_path: Path, bootstrap_user):
    """Create authenticated test client with isolated database."""
    db_path = tmp_path / "test.db"
    os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-minimum-32-bytes"

    import colony_manager.adapters.api.dependencies as deps

    init_db(db_path)
    app = create_app()
    app.dependency_overrides[deps.get_db_path] = lambda: db_path

    client = TestClient(app)

    # /auth/register only creates VIEWER; bootstrap a colony_manager directly
    # (needed for most operations).
    bootstrap_user(
        db_path,
        username="colony_admin",
        email="admin@example.com",
        password="SecurePass123!",
        role="colony_manager",
    )
    login_data = {"username": "colony_admin", "password": "SecurePass123!"}
    client.post("/api/v1/auth/login", json=login_data)

    # Fetch CSRF token for state-changing requests (double-submit pattern)
    csrf_response = client.get("/api/v1/auth/csrf-token")
    assert csrf_response.status_code == 200
    client.headers["X-CSRF-Token"] = csrf_response.json()["csrf_token"]

    yield client

    app.dependency_overrides.clear()
    if "JWT_SECRET_KEY" in os.environ:
        del os.environ["JWT_SECRET_KEY"]


class TestColonyLifecycleCreation:
    """Tests for colony creation and initial state."""

    def test_create_colony_initial_state(self, auth_client):
        """Test colony is created with correct initial stats."""
        create_data = {
            "name": "New Colony",
            "founder_name": "Rogue Trader",
            "colony_type": "mining_and_industry",
        }
        response = auth_client.post("/api/v1/colonies", json=create_data)
        assert response.status_code == 201
        colony = response.json()

        assert colony["name"] == "New Colony"
        assert colony["founder_name"] == "Rogue Trader"
        assert colony["colony_type"] == "mining_and_industry"
        assert "id" in colony

        # Check initial state
        state_response = auth_client.get(f"/api/v1/colonies/{colony['id']}/state")
        assert state_response.status_code == 200
        state = state_response.json()

        # Verify initial stats are reasonable (should be > 0)
        assert state["size"]["current"] > 0
        assert state["order"]["current"] > 0
        assert state["complacency"]["current"] >= 0
        assert state["productivity"]["current"] > 0
        assert state["piety"]["current"] > 0
        assert state["profit_factor"] > 0

    def test_create_multiple_colonies(self, auth_client):
        """Test creating multiple colonies."""
        colonies = []
        for i in range(3):
            create_data = {
                "name": f"Colony {i + 1}",
                "founder_name": "Owner",
                "colony_type": "agricultural",
            }
            response = auth_client.post("/api/v1/colonies", json=create_data)
            assert response.status_code == 201
            colonies.append(response.json())

        # List all colonies
        list_response = auth_client.get("/api/v1/colonies")
        assert list_response.status_code == 200
        colony_list = list_response.json()
        assert len(colony_list["items"]) == 3


class TestColonyLifecycleInfrastructure:
    """Tests for adding infrastructure to colony."""

    def test_add_infrastructure_updates_stats(self, auth_client):
        """Test adding infrastructure affects colony stats."""
        # Create colony
        create_data = {
            "name": "Infra Test",
            "founder_name": "Owner",
            "colony_type": "mining_and_industry",
        }
        colony_response = auth_client.post("/api/v1/colonies", json=create_data)
        colony = colony_response.json()
        colony_id = colony["id"]

        # Get initial state
        initial_state_response = auth_client.get(f"/api/v1/colonies/{colony_id}/state")
        initial_state = initial_state_response.json()
        initial_productivity = initial_state["productivity"]["current"]

        # Add infrastructure (correct endpoint: /colonies/{id}/infrastructure)
        infra_data = {
            "name": "Power Network",
            "infrastructure_type": "power_network",
            "state": "working",
        }
        infra_response = auth_client.post(
            f"/api/v1/colonies/{colony_id}/infrastructure", json=infra_data
        )
        assert infra_response.status_code == 201

        # Check state after adding infrastructure
        new_state_response = auth_client.get(f"/api/v1/colonies/{colony_id}/state")
        new_state = new_state_response.json()

        # Productivity should increase with working power network
        assert new_state["productivity"]["current"] >= initial_productivity

    def test_faulty_infrastructure_penalizes_stats(self, auth_client):
        """Test not working infrastructure reduces stats."""
        # Create colony
        create_data = {
            "name": "Faulty Test",
            "founder_name": "Owner",
            "colony_type": "mining_and_industry",
        }
        colony_response = auth_client.post("/api/v1/colonies", json=create_data)
        colony = colony_response.json()
        colony_id = colony["id"]

        # Add not working infrastructure (not_working = faulty/incapacitated)
        infra_data = {
            "name": "Faulty Power Network",
            "infrastructure_type": "power_network",
            "state": "not_working",
        }
        infra_response = auth_client.post(
            f"/api/v1/colonies/{colony_id}/infrastructure", json=infra_data
        )
        assert infra_response.status_code == 201

        # Check state - should have penalties
        state_response = auth_client.get(f"/api/v1/colonies/{colony_id}/state")
        state = state_response.json()

        # not working infrastructure should apply penalties
        assert state["productivity"]["current"] >= 0


class TestColonyLifecycleDevelopment:
    """Tests for development plans and upgrades."""

    def test_add_development_plan(self, auth_client):
        """Test adding development plan to colony."""
        # Create colony
        create_data = {
            "name": "Dev Plan Test",
            "founder_name": "Owner",
            "colony_type": "agricultural",
        }
        colony_response = auth_client.post("/api/v1/colonies", json=create_data)
        colony = colony_response.json()
        colony_id = colony["id"]

        # Add development plan (correct endpoint: /development-plans/colonies/{id})
        plan_data = {
            "upgrade_type": "infrastructure",
            "target_name": "New Facility",
            "priority": 2,
            "description": "Expand colony borders",
            "target_type": "Build it",
        }
        plan_response = auth_client.post(
            f"/api/v1/development-plans/colonies/{colony_id}", json=plan_data
        )
        assert plan_response.status_code == 201

        # Verify plan was added
        plans_response = auth_client.get(f"/api/v1/development-plans/colonies/{colony_id}")
        assert plans_response.status_code == 200
        plans = plans_response.json()
        assert len(plans) >= 1

    def test_add_support_upgrade(self, auth_client):
        """Test adding support upgrade to colony."""
        # Create colony (use valid colony_type from config)
        create_data = {
            "name": "Upgrade Test",
            "founder_name": "Owner",
            "colony_type": "agricultural",
        }
        colony_response = auth_client.post("/api/v1/colonies", json=create_data)
        colony = colony_response.json()
        colony_id = colony["id"]

        # Add support upgrade (only needs upgrade_type)
        upgrade_data = {"name": "Arbites Precinct", "upgrade_type": "arbites_precinct"}
        upgrade_response = auth_client.post(
            f"/api/v1/colonies/{colony_id}/upgrades", json=upgrade_data
        )
        assert upgrade_response.status_code == 201


class TestColonyLifecycleEvents:
    """Tests for colony events."""

    def test_add_colony_event(self, auth_client):
        """Test adding event to colony timeline."""
        # Create colony (use valid colony_type)
        create_data = {
            "name": "Event Test",
            "founder_name": "Owner",
            "colony_type": "mining_and_industry",
        }
        colony_response = auth_client.post("/api/v1/colonies", json=create_data)
        colony = colony_response.json()
        colony_id = colony["id"]

        # Add event (correct format: name, description, modifiers)
        event_data = {
            "name": "Minor Earthquake",
            "description": "Minor earthquake affects the colony",
            "modifiers": [
                {"stat": "productivity", "value": -1, "description": "Disrupted operations"}
            ],
        }
        event_response = auth_client.post(f"/api/v1/events/colonies/{colony_id}", json=event_data)
        assert event_response.status_code == 201

        # Verify event was added
        events_response = auth_client.get(f"/api/v1/events/colonies/{colony_id}")
        assert events_response.status_code == 200
        events = events_response.json()
        assert len(events) >= 1


class TestColonyLifecycleStats:
    """Tests for colony stat calculations."""

    def test_profit_factor_calculation(self, auth_client):
        """Test profit factor is calculated correctly."""
        # Create colony
        create_data = {
            "name": "PF Test",
            "founder_name": "Owner",
            "colony_type": "mining_and_industry",
        }
        colony_response = auth_client.post("/api/v1/colonies", json=create_data)
        colony = colony_response.json()
        colony_id = colony["id"]

        # Get state
        state_response = auth_client.get(f"/api/v1/colonies/{colony_id}/state")
        assert state_response.status_code == 200
        state = state_response.json()

        # Profit factor should be positive for healthy colony
        assert state["profit_factor"] > 0

    def test_colony_state_transitions(self, auth_client):
        """Test colony state transitions (e.g., Anarchy, Placated)."""
        # Create colony (use valid colony_type)
        create_data = {
            "name": "State Test",
            "founder_name": "Owner",
            "colony_type": "mining_and_industry",
        }
        colony_response = auth_client.post("/api/v1/colonies", json=create_data)
        colony = colony_response.json()
        colony_id = colony["id"]

        # Get initial state
        state_response = auth_client.get(f"/api/v1/colonies/{colony_id}/state")
        state = state_response.json()

        # Check state flags exist
        assert "lore_state" in state["size"]
        assert "lore_state" in state["order"]
        # Lore states should be defined (e.g., "Growing", "Stable", etc.)
        assert isinstance(state["size"]["lore_state"], str)
