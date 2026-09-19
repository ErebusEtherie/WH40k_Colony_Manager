"""Infrastructure API integration tests."""

import pytest


@pytest.fixture
def colony(auth_client):
    create_data = {
        "name": "Test Colony",
        "founder_name": "Owner",
        "colony_type": "mining_and_industry",
    }
    response = auth_client.post("/api/v1/colonies", json=create_data)
    return response.json()


class TestInfrastructureAPI:
    def test_list_infrastructure_empty(self, auth_client, colony):
        response = auth_client.get(f"/api/v1/colonies/{colony['id']}/infrastructure")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["meta"]["total"] == 0

    def test_create_infrastructure(self, auth_client, colony):
        create_data = {
            "name": "Main Power Grid",
            "infrastructure_type": "power_network",
            "state": "working",
        }
        response = auth_client.post(
            f"/api/v1/colonies/{colony['id']}/infrastructure", json=create_data
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Main Power Grid"
        assert data["infrastructure_type"] == "power_network"
        assert data["state"] == "working"
        assert data["has_effect"] is True
        assert data["is_working"] is True

    def test_create_infrastructure_for_missing_colony_raises(self, auth_client):
        create_data = {
            "name": "Power Grid",
            "infrastructure_type": "power_network",
            "state": "working",
        }
        response = auth_client.post("/api/v1/colonies/9999/infrastructure", json=create_data)
        assert response.status_code == 404
        assert "Colony 9999 not found" in response.json()["detail"]

    def test_get_infrastructure(self, auth_client, colony):
        create_data = {
            "name": "Power Network",
            "infrastructure_type": "power_network",
            "state": "working",
        }
        create_response = auth_client.post(
            f"/api/v1/colonies/{colony['id']}/infrastructure", json=create_data
        )
        infra_id = create_response.json()["id"]
        response = auth_client.get(f"/api/v1/colonies/{colony['id']}/infrastructure/{infra_id}")
        assert response.status_code == 200
        assert response.json()["id"] == infra_id
        assert response.json()["name"] == "Power Network"

    def test_get_infrastructure_missing_raises(self, auth_client, colony):
        response = auth_client.get(f"/api/v1/colonies/{colony['id']}/infrastructure/9999")
        assert response.status_code == 404
        assert "Infrastructure 9999 not found" in response.json()["detail"]

    def test_update_infrastructure_state(self, auth_client, colony):
        create_data = {
            "name": "Transport Hub",
            "infrastructure_type": "power_network",
            "state": "planned",
        }
        create_response = auth_client.post(
            f"/api/v1/colonies/{colony['id']}/infrastructure", json=create_data
        )
        infra_id = create_response.json()["id"]
        update_data = {"state": "not_working"}
        response = auth_client.patch(
            f"/api/v1/colonies/{colony['id']}/infrastructure/{infra_id}", json=update_data
        )
        assert response.status_code == 200
        assert response.json()["state"] == "not_working"
        assert response.json()["is_not_working"] is True

    def test_update_infrastructure_missing_raises(self, auth_client, colony):
        update_data = {"state": "working"}
        response = auth_client.patch(
            f"/api/v1/colonies/{colony['id']}/infrastructure/9999", json=update_data
        )
        assert response.status_code == 404

    def test_delete_infrastructure(self, auth_client, colony):
        create_data = {
            "name": "Power Grid",
            "infrastructure_type": "power_network",
            "state": "working",
        }
        create_response = auth_client.post(
            f"/api/v1/colonies/{colony['id']}/infrastructure", json=create_data
        )
        infra_id = create_response.json()["id"]
        response = auth_client.delete(f"/api/v1/colonies/{colony['id']}/infrastructure/{infra_id}")
        assert response.status_code == 204
        get_response = auth_client.get(f"/api/v1/colonies/{colony['id']}/infrastructure/{infra_id}")
        assert get_response.status_code == 404

    def test_delete_infrastructure_missing_raises(self, auth_client, colony):
        response = auth_client.delete(f"/api/v1/colonies/{colony['id']}/infrastructure/9999")
        assert response.status_code == 404

    def test_infrastructure_state_defaults_to_planned(self, auth_client, colony):
        create_data = {"name": "Transport Network", "infrastructure_type": "transport"}
        response = auth_client.post(
            f"/api/v1/colonies/{colony['id']}/infrastructure", json=create_data
        )
        assert response.status_code == 201
        assert response.json()["state"] == "planned"
        assert response.json()["has_effect"] is False

    def test_update_infrastructure_name(self, auth_client, colony):
        create_data = {
            "name": "Old Name",
            "infrastructure_type": "power_network",
            "state": "planned",
        }
        create_response = auth_client.post(
            f"/api/v1/colonies/{colony['id']}/infrastructure", json=create_data
        )
        infra_id = create_response.json()["id"]
        update_data = {"name": "New Name"}
        response = auth_client.patch(
            f"/api/v1/colonies/{colony['id']}/infrastructure/{infra_id}", json=update_data
        )
        assert response.status_code == 200
        assert response.json()["name"] == "New Name"

    def test_update_infrastructure_notes(self, auth_client, colony):
        create_data = {
            "name": "Power Grid",
            "infrastructure_type": "power_network",
            "state": "planned",
            "notes": "Initial notes",
        }
        create_response = auth_client.post(
            f"/api/v1/colonies/{colony['id']}/infrastructure", json=create_data
        )
        infra_id = create_response.json()["id"]
        update_data = {"notes": "Updated notes"}
        response = auth_client.patch(
            f"/api/v1/colonies/{colony['id']}/infrastructure/{infra_id}", json=update_data
        )
        assert response.status_code == 200
        assert response.json()["notes"] == "Updated notes"

    def test_validate_infrastructure_transition(self, auth_client, colony):
        create_data = {
            "name": "Power Grid",
            "infrastructure_type": "power_network",
            "state": "planned",
        }
        create_response = auth_client.post(
            f"/api/v1/colonies/{colony['id']}/infrastructure", json=create_data
        )
        infra_id = create_response.json()["id"]
        update_data = {"state": "working"}
        response = auth_client.patch(
            f"/api/v1/colonies/{colony['id']}/infrastructure/{infra_id}?validate_only=true",
            json=update_data,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["current_state"] == "planned"
        assert data["requested_state"] == "working"
        assert "modifiers_preview" in data
