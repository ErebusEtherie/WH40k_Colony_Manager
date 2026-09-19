"""Integration tests for Development Plan API endpoints."""

from fastapi.testclient import TestClient


class TestDevelopmentPlansAPI:
    """Integration tests for development plan management endpoints."""

    def test_create_development_plan(self, auth_client: TestClient):
        """Test creating a new development plan for a colony."""
        colony_data = {
            "name": "Plan Test Colony",
            "founder_name": "Test Owner",
            "colony_type": "mining_and_industry",
        }
        colony_response = auth_client.post("/api/v1/colonies", json=colony_data)
        colony_id = colony_response.json()["id"]

        plan_data = {
            "upgrade_type": "infrastructure",
            "target_name": "Industrial Expansion",
            "priority": 3,
            "description": "Expand mining operations to sector 7",
            "target_type": "Acquire resources from nearby asteroids",
        }
        response = auth_client.post(
            f"/api/v1/development-plans/colonies/{colony_id}", json=plan_data
        )
        assert response.status_code == 201
        plan = response.json()
        assert plan["target_name"] == "Industrial Expansion"
        assert plan["colony_id"] == colony_id
        assert plan["upgrade_type"] == "infrastructure"
        assert "id" in plan

    def test_get_development_plan(self, auth_client: TestClient):
        """Test retrieving a specific development plan by ID."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={"name": "Test", "founder_name": "Owner", "colony_type": "mining_and_industry"},
        )
        colony_id = colony_response.json()["id"]

        plan_data = {
            "upgrade_type": "infrastructure",
            "target_name": "Test Plan",
            "priority": 2,
            "description": "Test description",
            "target_type": "Test plan",
        }
        plan_response = auth_client.post(
            f"/api/v1/development-plans/colonies/{colony_id}", json=plan_data
        )
        plan_id = plan_response.json()["id"]

        response = auth_client.get(f"/api/v1/development-plans/{plan_id}")
        assert response.status_code == 200
        plan = response.json()
        assert plan["id"] == plan_id
        assert plan["target_name"] == "Test Plan"

    def test_get_plans_by_colony(self, auth_client: TestClient):
        """Test retrieving all development plans for a colony."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Multi-Plan Colony",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]

        for i in range(3):
            plan_data = {
                "upgrade_type": "infrastructure",
                "target_name": f"Plan {i}",
                "priority": 2,
                "description": f"Description {i}",
                "target_type": f"Plan {i}",
            }
            auth_client.post(f"/api/v1/development-plans/colonies/{colony_id}", json=plan_data)

        response = auth_client.get(f"/api/v1/development-plans/colonies/{colony_id}")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 3

    def test_update_development_plan(self, auth_client: TestClient):
        """Test updating a development plan."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Update Test",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]

        plan_data = {
            "upgrade_type": "infrastructure",
            "target_name": "Original Plan",
            "priority": 2,
            "description": "Original description",
            "target_type": "Original plan",
        }
        plan_response = auth_client.post(
            f"/api/v1/development-plans/colonies/{colony_id}", json=plan_data
        )
        plan_id = plan_response.json()["id"]

        update_data = {
            "target_name": "Updated Plan",
            "description": "Updated description",
            "status": "in_progress",
        }
        response = auth_client.patch(f"/api/v1/development-plans/{plan_id}", json=update_data)
        assert response.status_code == 200
        plan = response.json()
        assert plan["target_name"] == "Updated Plan"
        assert plan["status"] == "in_progress"

    def test_delete_development_plan(self, auth_client: TestClient):
        """Test deleting a development plan."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Delete Test",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]

        plan_data = {
            "upgrade_type": "infrastructure",
            "target_name": "To Delete",
            "priority": 2,
            "description": "Will be deleted",
            "target_type": "Delete plan",
        }
        plan_response = auth_client.post(
            f"/api/v1/development-plans/colonies/{colony_id}", json=plan_data
        )
        plan_id = plan_response.json()["id"]

        response = auth_client.delete(f"/api/v1/development-plans/{plan_id}")
        assert response.status_code == 204

        response = auth_client.get(f"/api/v1/development-plans/colonies/{colony_id}")
        data = response.json()
        assert len(data["items"]) == 0

    def test_development_plan_not_found(self, auth_client: TestClient):
        """Test 404 when development plan doesn't exist."""
        response = auth_client.get("/api/v1/development-plans/99999")
        assert response.status_code == 404

    def test_create_development_plan_unauthorized(self, test_client: TestClient):
        """Test creating development plan without authentication fails.

        Note: Returns 403 (CSRF failure) rather than 401 because CSRF
        middleware runs before auth middleware for POST requests.
        """
        plan_data = {
            "upgrade_type": "infrastructure",
            "target_name": "Unauthorized Plan",
            "priority": 2,
            "description": "Should fail",
            "target_type": "Fail plan",
        }
        response = test_client.post("/api/v1/development-plans/colonies/1", json=plan_data)
        # CSRF check fails first (403) before auth check (401)
        assert response.status_code in (401, 403)

    def test_development_plan_status_enum_values(self, auth_client: TestClient):
        """Test all valid development plan status values."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Status Test",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]

        # Test status transitions: PLANNED (default) -> IN_PROGRESS -> ACQUIRED -> DELIVERED
        plan_data = {
            "upgrade_type": "infrastructure",
            "target_name": "Status Plan",
            "priority": 2,
            "description": "Testing status transitions",
            "target_type": "Status plan",
        }
        response = auth_client.post(
            f"/api/v1/development-plans/colonies/{colony_id}", json=plan_data
        )
        assert response.status_code == 201
        plan_id = response.json()["id"]

        # Default status should be PLANNED
        assert response.json()["status"] == "planned"

        # Test transition to IN_PROGRESS
        update_data = {"status": "in_progress"}
        update_response = auth_client.patch(
            f"/api/v1/development-plans/{plan_id}", json=update_data
        )
        assert update_response.status_code == 200
        assert update_response.json()["status"] == "in_progress"

        # Test transition to ACQUIRED
        update_data = {"status": "acquired"}
        update_response = auth_client.patch(
            f"/api/v1/development-plans/{plan_id}", json=update_data
        )
        assert update_response.status_code == 200
        assert update_response.json()["status"] == "acquired"

        # Test transition to DELIVERED
        update_data = {"status": "delivered"}
        update_response = auth_client.patch(
            f"/api/v1/development-plans/{plan_id}", json=update_data
        )
        assert update_response.status_code == 200
        assert update_response.json()["status"] == "delivered"
