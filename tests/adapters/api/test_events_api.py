"""Integration tests for Event API endpoints."""

from fastapi.testclient import TestClient


class TestEventsAPI:
    """Integration tests for event management endpoints."""

    def test_create_event(self, auth_client: TestClient):
        """Test creating a new event for a colony."""
        colony_data = {
            "name": "Event Test Colony",
            "founder_name": "Test Owner",
            "colony_type": "mining_and_industry",
        }
        colony_response = auth_client.post("/api/v1/colonies", json=colony_data)
        colony_id = colony_response.json()["id"]
        event_data = {
            "name": "Warp Storm",
            "description": "A dangerous warp storm affects the colony",
            "modifiers": [
                {"stat": "productivity", "value": -2, "description": "Storm disrupts operations"},
                {"stat": "order", "value": -1, "description": "Panic among workers"},
            ],
        }
        response = auth_client.post(f"/api/v1/events/colonies/{colony_id}", json=event_data)
        assert response.status_code == 201
        event = response.json()
        assert event["name"] == "Warp Storm"
        assert event["colony_id"] == colony_id
        assert len(event["modifiers"]) == 2
        assert "id" in event
        assert event["is_active"] is True

    def test_get_event(self, auth_client: TestClient):
        """Test retrieving a specific event by ID."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={"name": "Test", "founder_name": "Owner", "colony_type": "mining_and_industry"},
        )
        colony_id = colony_response.json()["id"]
        event_data = {"name": "Test Event", "description": "Test description", "modifiers": []}
        event_response = auth_client.post(f"/api/v1/events/colonies/{colony_id}", json=event_data)
        event_id = event_response.json()["id"]
        response = auth_client.get(f"/api/v1/events/{event_id}")
        assert response.status_code == 200
        event = response.json()
        assert event["id"] == event_id
        assert event["name"] == "Test Event"

    def test_get_events_by_colony(self, auth_client: TestClient):
        """Test retrieving all events for a colony."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Multi-Event Colony",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]
        for i in range(3):
            event_data = {"name": f"Event {i}", "description": f"Description {i}", "modifiers": []}
            auth_client.post(f"/api/v1/events/colonies/{colony_id}", json=event_data)
        response = auth_client.get(f"/api/v1/events/colonies/{colony_id}")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "meta" in data
        assert len(data["items"]) == 3
        assert data["meta"]["total"] == 3

    def test_update_event(self, auth_client: TestClient):
        """Test updating an event."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Update Test",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]
        event_data = {
            "name": "Original Event",
            "description": "Original description",
            "modifiers": [],
        }
        event_response = auth_client.post(f"/api/v1/events/colonies/{colony_id}", json=event_data)
        event_id = event_response.json()["id"]
        update_data = {
            "name": "Updated Event",
            "description": "Updated description",
            "is_active": False,
        }
        response = auth_client.patch(f"/api/v1/events/{event_id}", json=update_data)
        assert response.status_code == 200
        event = response.json()
        assert event["name"] == "Updated Event"
        assert event["description"] == "Updated description"
        assert event["is_active"] is False

    def test_delete_event(self, auth_client: TestClient):
        """Test deleting (soft delete) an event."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Delete Test",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]
        event_data = {"name": "To Delete", "description": "Will be deleted", "modifiers": []}
        event_response = auth_client.post(f"/api/v1/events/colonies/{colony_id}", json=event_data)
        event_id = event_response.json()["id"]
        response = auth_client.delete(f"/api/v1/events/{event_id}")
        assert response.status_code == 204
        response = auth_client.get(f"/api/v1/events/colonies/{colony_id}?active_only=true")
        data = response.json()
        assert len(data["items"]) == 0

    def test_event_not_found(self, auth_client: TestClient):
        """Test 404 when event doesn't exist."""
        response = auth_client.get("/api/v1/events/99999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_create_event_unauthorized(self, test_client: TestClient):
        """Test creating event without authentication fails.

        Note: Returns 403 (CSRF failure) rather than 401 because CSRF
        middleware runs before auth middleware for POST requests.
        """
        event_data = {"name": "Unauthorized Event", "description": "Should fail", "modifiers": []}
        response = test_client.post("/api/v1/events/colonies/1", json=event_data)
        # CSRF check fails first (403) before auth check (401)
        assert response.status_code in (401, 403)

    def test_get_events_by_colony_active_only(self, auth_client: TestClient):
        """Test retrieving only active events for a colony."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Active Test",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]
        for i in range(3):
            event_data = {"name": f"Event {i}", "description": f"Description {i}", "modifiers": []}
            auth_client.post(f"/api/v1/events/colonies/{colony_id}", json=event_data)
        events_response = auth_client.get(f"/api/v1/events/colonies/{colony_id}")
        event_id = events_response.json()["items"][0]["id"]
        auth_client.patch(f"/api/v1/events/{event_id}", json={"is_active": False})
        response = auth_client.get(f"/api/v1/events/colonies/{colony_id}?active_only=true")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2


class TestEventsPaginationAndFiltering:
    """Tests for events pagination and filters."""

    def test_list_events_pagination(self, auth_client: TestClient):
        """Test events pagination with offset, limit, has_more, total."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Pagination Test",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]
        for i in range(25):
            auth_client.post(
                f"/api/v1/events/colonies/{colony_id}",
                json={"name": f"Event {i}", "description": f"Description {i}", "modifiers": []},
            )
        response = auth_client.get(f"/api/v1/events/colonies/{colony_id}")
        data = response.json()
        assert len(data["items"]) == 20, f"Expected 20 items, got {len(data['items'])}"
        assert data["meta"]["total"] == 25, f"Expected total=25, got {data['meta']['total']}"
        assert data["meta"]["has_more"] is True
        assert data["meta"]["offset"] == 0
        assert data["meta"]["limit"] == 20

    def test_list_events_pagination_edge_cases(self, auth_client: TestClient):
        """Test pagination boundary conditions."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Edge Test",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]
        for i in range(10):
            auth_client.post(
                f"/api/v1/events/colonies/{colony_id}",
                json={"name": f"Event {i}", "description": f"Description {i}", "modifiers": []},
            )
        # Test exact page size
        response = auth_client.get(f"/api/v1/events/colonies/{colony_id}?limit=10")
        data = response.json()
        assert len(data["items"]) == 10
        assert data["meta"]["has_more"] is False
        # Test offset beyond total
        response = auth_client.get(f"/api/v1/events/colonies/{colony_id}?offset=100")
        data = response.json()
        assert len(data["items"]) == 0
        assert data["meta"]["has_more"] is False
        # Test limit=1
        response = auth_client.get(f"/api/v1/events/colonies/{colony_id}?limit=1")
        data = response.json()
        assert len(data["items"]) == 1
        assert data["meta"]["has_more"] is True

    def test_list_events_filter_by_active_only(self, auth_client: TestClient):
        """Test filtering events by active status."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Active Filter",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]
        for i in range(5):
            auth_client.post(
                f"/api/v1/events/colonies/{colony_id}",
                json={"name": f"Event {i}", "description": f"Description {i}", "modifiers": []},
            )
        # Deactivate first 2 events
        events_response = auth_client.get(f"/api/v1/events/colonies/{colony_id}")
        for item in events_response.json()["items"][:2]:
            auth_client.patch(f"/api/v1/events/{item['id']}", json={"is_active": False})
        response = auth_client.get(f"/api/v1/events/colonies/{colony_id}?active_only=true")
        data = response.json()
        assert len(data["items"]) == 3, f"Expected 3 active events, got {len(data['items'])}"
        for item in data["items"]:
            assert item["is_active"] is True

    def test_list_events_filter_by_search(self, auth_client: TestClient):
        """Test filtering events by name search."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Search Test",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]
        test_data = [
            {"name": "Warp Storm", "description": "Dangerous warp activity"},
            {"name": "Solar Flare", "description": "Solar activity"},
            {"name": "Tectonic Event", "description": "Ground shaking"},
            {"name": "Pirate Raid", "description": "Attack on colony"},
            {"name": "Trade Boom", "description": "Economic surge"},
        ]
        for item in test_data:
            auth_client.post(
                f"/api/v1/events/colonies/{colony_id}",
                json={"name": item["name"], "description": item["description"], "modifiers": []},
            )
        response = auth_client.get(f"/api/v1/events/colonies/{colony_id}?name_search=storm")
        data = response.json()
        storm_items = [item for item in data["items"] if "Storm" in item["name"]]
        assert len(storm_items) >= 1, "Expected at least one event with 'Storm' in name"

    def test_list_events_combined_filters(self, auth_client: TestClient):
        """Test combining active_only and search filters."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Combined Filter",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]
        test_data = [
            {"name": "Warp Storm Active", "description": "Active storm", "is_active": True},
            {"name": "Warp Storm Inactive", "description": "Inactive storm", "is_active": False},
            {"name": "Solar Flare Active", "description": "Active flare", "is_active": True},
        ]
        for item in test_data:
            event_response = auth_client.post(
                f"/api/v1/events/colonies/{colony_id}",
                json={"name": item["name"], "description": item["description"], "modifiers": []},
            )
            if not item["is_active"]:
                event_id = event_response.json()["id"]
                auth_client.patch(f"/api/v1/events/{event_id}", json={"is_active": False})
        response = auth_client.get(
            f"/api/v1/events/colonies/{colony_id}?active_only=true&name_search=storm"
        )
        data = response.json()
        assert len(data["items"]) == 1, f"Expected 1 item, got {len(data['items'])}"
        assert data["items"][0]["name"] == "Warp Storm Active"

    def test_list_events_filters_with_pagination(self, auth_client: TestClient):
        """Test combining filters with pagination."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "FilterPag",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]
        for i in range(15):
            auth_client.post(
                f"/api/v1/events/colonies/{colony_id}",
                json={
                    "name": f"Warp Event {i}",
                    "description": f"Description {i}",
                    "modifiers": [],
                },
            )
        for i in range(10):
            auth_client.post(
                f"/api/v1/events/colonies/{colony_id}",
                json={
                    "name": f"Other Event {i}",
                    "description": f"Description {i}",
                    "modifiers": [],
                },
            )
        response = auth_client.get(f"/api/v1/events/colonies/{colony_id}?name_search=warp&limit=5")
        data = response.json()
        assert len(data["items"]) == 5, f"Expected 5 items, got {len(data['items'])}"
        assert data["meta"]["total"] == 15, f"Expected total=15, got {data['meta']['total']}"
        assert data["meta"]["has_more"] is True

    def test_list_events_empty(self, auth_client: TestClient):
        """Test listing events for colony with no events."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Empty Events",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]
        response = auth_client.get(f"/api/v1/events/colonies/{colony_id}")
        data = response.json()
        assert len(data["items"]) == 0
        assert data["meta"]["total"] == 0
        assert data["meta"]["has_more"] is False
