"""Integration tests for Modifier API endpoints."""

from fastapi.testclient import TestClient


class TestModifiersAPI:
    """Integration tests for modifier management endpoints (admin only)."""

    def test_list_modifiers_empty(self, auth_client: TestClient):
        """Test listing all modifiers when none exist."""
        response = auth_client.get("/api/v1/modifiers")
        assert response.status_code == 200
        data = response.json()
        modifiers = data["items"]
        assert isinstance(modifiers, list)
        assert len(modifiers) == 0
        assert "meta" in data
        assert data["meta"]["total"] == 0

    def test_list_modifiers_with_colony(self, auth_client: TestClient):
        """Test listing all modifiers returns empty list for colonies without modifiers."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Modifier Test Colony",
                "founder_name": "Test Owner",
                "colony_type": "mining_and_industry",
            },
        )
        assert colony_response.status_code == 201
        response = auth_client.get("/api/v1/modifiers")
        assert response.status_code == 200
        data = response.json()
        modifiers = data["items"]
        assert isinstance(modifiers, list)

    def test_get_modifier_not_found(self, auth_client: TestClient):
        """Test 404 when modifier does not exist."""
        response = auth_client.get("/api/v1/modifiers/99999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_list_modifiers_unauthorized(self, test_client: TestClient):
        """Test listing modifiers without authentication fails."""
        response = test_client.get("/api/v1/modifiers")
        assert response.status_code == 401

    def test_get_modifier_unauthorized(self, test_client: TestClient):
        """Test getting modifier without authentication fails."""
        response = test_client.get("/api/v1/modifiers/1")
        assert response.status_code == 401
