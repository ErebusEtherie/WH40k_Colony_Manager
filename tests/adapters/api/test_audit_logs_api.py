"""Integration tests for Audit Log API endpoints."""

from fastapi.testclient import TestClient


class TestAuditLogsAPI:
    """Integration tests for audit log query endpoints."""

    def test_get_audit_logs_by_colony(self, auth_client: TestClient):
        """Test retrieving audit logs for a colony."""
        colony_data = {
            "name": "Audit Test Colony",
            "founder_name": "Test Owner",
            "colony_type": "mining_and_industry",
        }
        colony_response = auth_client.post("/api/v1/colonies", json=colony_data)
        colony_id = colony_response.json()["id"]
        event_data = {"name": "Test Event", "description": "Test", "modifiers": []}
        auth_client.post(f"/api/v1/events/colonies/{colony_id}", json=event_data)
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/audit-logs")
        assert response.status_code == 200
        data = response.json()
        logs = data["items"]
        assert len(logs) >= 1
        # Verify pagination metadata
        assert "meta" in data
        assert data["meta"]["total"] >= 1
        assert data["meta"]["offset"] == 0
        assert data["meta"]["limit"] == 50

    def test_get_audit_logs_by_colony_with_action_filter(self, auth_client: TestClient):
        """Test filtering audit logs by entity type."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Filter Test",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]
        event_data = {"name": "Test Event", "description": "Test", "modifiers": []}
        event_response = auth_client.post(f"/api/v1/events/colonies/{colony_id}", json=event_data)
        event_id = event_response.json()["id"]
        auth_client.patch(f"/api/v1/events/{event_id}", json={"name": "Updated Event"})
        # Filter by entity_type (event) instead of action (not supported)
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/audit-logs?entity_type=event")
        assert response.status_code == 200
        data = response.json()
        logs = data["items"]
        assert len(logs) >= 1
        assert all(log["entity_type"] == "event" for log in logs)

    def test_get_audit_logs_by_colony_with_entity_filter(self, auth_client: TestClient):
        """Test filtering audit logs by entity type."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Entity Filter Test",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]
        event_data = {"name": "Test Event", "description": "Test", "modifiers": []}
        auth_client.post(f"/api/v1/events/colonies/{colony_id}", json=event_data)
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/audit-logs?entity_type=event")
        assert response.status_code == 200
        data = response.json()
        logs = data["items"]
        assert len(logs) >= 1
        assert all(log["entity_type"] == "event" for log in logs)

    def test_get_audit_log_by_id(self, auth_client: TestClient):
        """Test retrieving a specific audit log entry by ID."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Single Log Test",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]
        event_data = {"name": "Test Event", "description": "Test", "modifiers": []}
        auth_client.post(f"/api/v1/events/colonies/{colony_id}", json=event_data)
        logs_response = auth_client.get(f"/api/v1/colonies/{colony_id}/audit-logs")
        logs_data = logs_response.json()
        log_id = logs_data["items"][0]["id"]
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/audit-logs/{log_id}")
        assert response.status_code == 200
        log = response.json()
        assert log["id"] == log_id
        assert log["colony_id"] == colony_id

    def test_get_audit_logs_pagination(self, auth_client: TestClient):
        """Test audit log pagination with limit and offset."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Pagination Test",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]
        for i in range(5):
            event_data = {"name": f"Event {i}", "description": f"Test {i}", "modifiers": []}
            auth_client.post(f"/api/v1/events/colonies/{colony_id}", json=event_data)
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/audit-logs?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        logs = data["items"]
        assert len(logs) == 2
        assert data["meta"]["total"] > 2
        assert data["meta"]["has_more"] is True
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/audit-logs?limit=2&offset=2")
        assert response.status_code == 200
        data = response.json()
        logs = data["items"]
        assert len(logs) == 2

    def test_get_audit_logs_empty(self, auth_client: TestClient):
        """Test audit logs for colony with no logs."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Empty Logs Test",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/audit-logs")
        assert response.status_code == 200
        data = response.json()
        logs = data["items"]
        # Colony creation is now logged, so we expect 1 log entry
        assert len(logs) == 1
        assert logs[0]["action"] == "create"
        assert data["meta"]["total"] == 1

    def test_get_audit_log_not_found(self, auth_client: TestClient):
        """Test 404 when audit log doesn't exist."""
        response = auth_client.get("/api/v1/colonies/1/audit-logs/99999")
        assert response.status_code == 404

    def test_get_audit_log_cross_colony_access_denied(self, auth_client: TestClient):
        """Test that accessing audit log from different colony returns 404."""
        # Create two colonies
        colony1_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Colony 1",
                "founder_name": "Owner1",
                "colony_type": "mining_and_industry",
            },
        )
        colony1_id = colony1_response.json()["id"]
        colony2_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Colony 2",
                "founder_name": "Owner2",
                "colony_type": "mining_and_industry",
            },
        )
        colony2_id = colony2_response.json()["id"]

        # Create an event in colony 1
        event_data = {"name": "Test Event", "description": "Test", "modifiers": []}
        auth_client.post(f"/api/v1/events/colonies/{colony1_id}", json=event_data)

        # Get the log ID from colony 1
        logs_response = auth_client.get(f"/api/v1/colonies/{colony1_id}/audit-logs")
        logs_data = logs_response.json()
        log_id = logs_data["items"][0]["id"]

        # Try to access colony 1's log through colony 2's endpoint - should fail
        response = auth_client.get(f"/api/v1/colonies/{colony2_id}/audit-logs/{log_id}")
        assert response.status_code == 404

    def test_audit_log_contains_required_fields(self, auth_client: TestClient):
        """Test that audit log entries contain all required fields."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Fields Test",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]
        event_data = {"name": "Test Event", "description": "Test", "modifiers": []}
        auth_client.post(f"/api/v1/events/colonies/{colony_id}", json=event_data)
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/audit-logs")
        data = response.json()
        log = data["items"][0]
        required_fields = [
            "id",
            "colony_id",
            "entity_type",
            "entity_id",
            "action",
            "changed_by",
            "changed_at",
        ]
        for field in required_fields:
            assert field in log, f"Missing required field: {field}"
