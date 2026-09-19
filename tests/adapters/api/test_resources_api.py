"""Integration tests for Resource API endpoints."""

from fastapi.testclient import TestClient


class TestResourcesAPI:
    """Integration tests for planetary resource management endpoints."""

    def test_create_resource(self, auth_client: TestClient):
        """Test creating a new planetary resource for a colony."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Resource Test Colony",
                "founder_name": "Test Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]
        resource_data = {
            "resource_type": "mineral",
            "name": "Iron Ore Deposit",
            "abundance": 50,
            "notes": "Rich deposit in northern mountains",
        }
        response = auth_client.post(f"/api/v1/colonies/{colony_id}/resources", json=resource_data)
        assert response.status_code == 201
        resource = response.json()
        assert resource["name"] == "Iron Ore Deposit"
        assert resource["colony_id"] == colony_id
        assert resource["resource_type"] == "mineral"
        assert resource["abundance"] == 50
        assert "id" in resource
        assert "abundance_level" in resource

    def test_list_resources(self, auth_client: TestClient):
        """Test retrieving all resources for a colony."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Multi-Resource Colony",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]
        for i in range(3):
            resource_data = {
                "resource_type": "mineral" if i % 2 == 0 else "organic_compound",
                "name": f"Resource {i}",
                "abundance": 30 + i * 10,
            }
            auth_client.post(f"/api/v1/colonies/{colony_id}/resources", json=resource_data)
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/resources")
        assert response.status_code == 200
        data = response.json()
        resources = data["items"]
        assert len(resources) == 3
        assert "meta" in data
        assert data["meta"]["total"] == 3

    def test_get_resource(self, auth_client: TestClient):
        """Test retrieving a specific resource by ID."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={"name": "Test", "founder_name": "Owner", "colony_type": "mining_and_industry"},
        )
        colony_id = colony_response.json()["id"]
        resource_data = {"resource_type": "mineral", "name": "Test Resource", "abundance": 40}
        resource_response = auth_client.post(
            f"/api/v1/colonies/{colony_id}/resources", json=resource_data
        )
        resource_id = resource_response.json()["id"]
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/resources/{resource_id}")
        assert response.status_code == 200
        resource = response.json()
        assert resource["id"] == resource_id
        assert resource["name"] == "Test Resource"
        assert resource["abundance"] == 40

    def test_update_resource(self, auth_client: TestClient):
        """Test updating a resource\'s abundance or notes."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Update Test",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]
        resource_data = {"resource_type": "mineral", "name": "Original Resource", "abundance": 30}
        resource_response = auth_client.post(
            f"/api/v1/colonies/{colony_id}/resources", json=resource_data
        )
        resource_id = resource_response.json()["id"]
        update_data = {"abundance": 75, "notes": "Updated notes"}
        response = auth_client.patch(
            f"/api/v1/colonies/{colony_id}/resources/{resource_id}", json=update_data
        )
        assert response.status_code == 200
        resource = response.json()
        assert resource["abundance"] == 75
        assert resource["notes"] == "Updated notes"

    def test_delete_resource(self, auth_client: TestClient):
        """Test deleting a resource from a colony."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Delete Test",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]
        resource_data = {"resource_type": "mineral", "name": "To Delete", "abundance": 20}
        resource_response = auth_client.post(
            f"/api/v1/colonies/{colony_id}/resources", json=resource_data
        )
        resource_id = resource_response.json()["id"]
        response = auth_client.delete(f"/api/v1/colonies/{colony_id}/resources/{resource_id}")
        assert response.status_code == 204
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/resources")
        data = response.json()
        assert len(data["items"]) == 0

    def test_resource_not_found(self, auth_client: TestClient):
        """Test 404 when resource doesn\'t exist."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={"name": "Test", "founder_name": "Owner", "colony_type": "mining_and_industry"},
        )
        colony_id = colony_response.json()["id"]
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/resources/99999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_create_resource_unauthorized(self, test_client: TestClient):
        """Test creating resource without authentication fails.

        Note: Returns 403 (CSRF failure) rather than 401 because CSRF
        middleware runs before auth middleware for POST requests.
        """
        resource_data = {"resource_type": "mineral", "name": "Unauthorized", "abundance": 10}
        response = test_client.post("/api/v1/colonies/1/resources", json=resource_data)
        # CSRF check fails first (403) before auth check (401)
        assert response.status_code in (401, 403)
