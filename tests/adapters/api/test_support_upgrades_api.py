"""Support Upgrades API integration tests."""

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


class TestSupportUpgradesAPI:
    def test_list_upgrades_empty(self, auth_client, colony):
        response = auth_client.get(f"/api/v1/colonies/{colony['id']}/upgrades")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["meta"]["total"] == 0

    def test_create_upgrade(self, auth_client, colony):
        create_data = {"name": "Arbites Precinct", "upgrade_type": "arbites_precinct"}
        response = auth_client.post(f"/api/v1/colonies/{colony['id']}/upgrades", json=create_data)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Arbites Precinct"
        assert data["upgrade_type"] == "arbites_precinct"
        assert data["has_stat_effect"] is True

    def test_create_upgrade_for_missing_colony_raises(self, auth_client):
        create_data = {"name": "Arbites Precinct", "upgrade_type": "arbites_precinct"}
        response = auth_client.post("/api/v1/colonies/9999/upgrades", json=create_data)
        assert response.status_code == 404
        assert "Colony 9999 not found" in response.json()["detail"]

    def test_create_upgrade_with_custom_stat_choice(self, auth_client, colony):
        create_data = {
            "name": "Cultural Center",
            "upgrade_type": "cultural_improvement",
            "custom_stat_choice": "order",
        }
        response = auth_client.post(f"/api/v1/colonies/{colony['id']}/upgrades", json=create_data)
        assert response.status_code == 201
        assert response.json()["custom_stat_choice"] == "order"

    def test_create_upgrade_with_custom_product(self, auth_client, colony):
        create_data = {
            "name": "Vehicle Factory",
            "upgrade_type": "industrial_facility",
            "custom_product": "Vehicles",
        }
        response = auth_client.post(f"/api/v1/colonies/{colony['id']}/upgrades", json=create_data)
        assert response.status_code == 201
        assert response.json()["custom_product"] == "Vehicles"

    def test_create_upgrade_with_affiliated_group(self, auth_client, colony):
        create_data = {
            "name": "Guild Contacts",
            "upgrade_type": "contacts",
            "affiliated_group": "Merchant Guild",
        }
        response = auth_client.post(f"/api/v1/colonies/{colony['id']}/upgrades", json=create_data)
        assert response.status_code == 201
        assert response.json()["affiliated_group"] == "Merchant Guild"

    def test_get_upgrade(self, auth_client, colony):
        create_data = {"name": "Arbites HQ", "upgrade_type": "arbites_precinct"}
        create_response = auth_client.post(
            f"/api/v1/colonies/{colony['id']}/upgrades", json=create_data
        )
        upgrade_id = create_response.json()["id"]
        response = auth_client.get(f"/api/v1/colonies/{colony['id']}/upgrades/{upgrade_id}")
        assert response.status_code == 200
        assert response.json()["id"] == upgrade_id
        assert response.json()["name"] == "Arbites HQ"

    def test_get_upgrade_missing_raises(self, auth_client, colony):
        response = auth_client.get(f"/api/v1/colonies/{colony['id']}/upgrades/9999")
        assert response.status_code == 404
        assert "SupportUpgrade 9999 not found" in response.json()["detail"]

    def test_update_upgrade(self, auth_client, colony):
        create_data = {
            "name": "Cultural Center",
            "upgrade_type": "cultural_improvement",
            "custom_stat_choice": "order",
        }
        create_response = auth_client.post(
            f"/api/v1/colonies/{colony['id']}/upgrades", json=create_data
        )
        upgrade_id = create_response.json()["id"]
        update_data = {"custom_stat_choice": "piety"}
        response = auth_client.patch(
            f"/api/v1/colonies/{colony['id']}/upgrades/{upgrade_id}", json=update_data
        )
        assert response.status_code == 200
        assert response.json()["custom_stat_choice"] == "piety"

    def test_update_upgrade_missing_raises(self, auth_client, colony):
        update_data = {"custom_stat_choice": "order"}
        response = auth_client.patch(
            f"/api/v1/colonies/{colony['id']}/upgrades/9999", json=update_data
        )
        assert response.status_code == 404

    def test_delete_upgrade(self, auth_client, colony):
        create_data = {"name": "Arbites Precinct", "upgrade_type": "arbites_precinct"}
        create_response = auth_client.post(
            f"/api/v1/colonies/{colony['id']}/upgrades", json=create_data
        )
        upgrade_id = create_response.json()["id"]
        response = auth_client.delete(f"/api/v1/colonies/{colony['id']}/upgrades/{upgrade_id}")
        assert response.status_code == 204
        get_response = auth_client.get(f"/api/v1/colonies/{colony['id']}/upgrades/{upgrade_id}")
        assert get_response.status_code == 404

    def test_delete_upgrade_missing_raises(self, auth_client, colony):
        response = auth_client.delete(f"/api/v1/colonies/{colony['id']}/upgrades/9999")
        assert response.status_code == 404

    def test_update_upgrade_name(self, auth_client, colony):
        create_data = {"name": "Old Name", "upgrade_type": "arbites_precinct"}
        create_response = auth_client.post(
            f"/api/v1/colonies/{colony['id']}/upgrades", json=create_data
        )
        upgrade_id = create_response.json()["id"]
        update_data = {"name": "New Name"}
        response = auth_client.patch(
            f"/api/v1/colonies/{colony['id']}/upgrades/{upgrade_id}", json=update_data
        )
        assert response.status_code == 200
        assert response.json()["name"] == "New Name"

    def test_update_upgrade_notes(self, auth_client, colony):
        create_data = {
            "name": "Arbites HQ",
            "upgrade_type": "arbites_precinct",
            "notes": "Initial notes",
        }
        create_response = auth_client.post(
            f"/api/v1/colonies/{colony['id']}/upgrades", json=create_data
        )
        upgrade_id = create_response.json()["id"]
        update_data = {"notes": "Updated notes"}
        response = auth_client.patch(
            f"/api/v1/colonies/{colony['id']}/upgrades/{upgrade_id}", json=update_data
        )
        assert response.status_code == 200
        assert response.json()["notes"] == "Updated notes"

    def test_validate_upgrade_transition(self, auth_client, colony):
        create_data = {
            "name": "Cultural Center",
            "upgrade_type": "cultural_improvement",
            "custom_stat_choice": "order",
        }
        create_response = auth_client.post(
            f"/api/v1/colonies/{colony['id']}/upgrades", json=create_data
        )
        upgrade_id = create_response.json()["id"]
        update_data = {"custom_stat_choice": "piety"}
        response = auth_client.patch(
            f"/api/v1/colonies/{colony['id']}/upgrades/{upgrade_id}?validate_only=true",
            json=update_data,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert "modifiers_preview" in data
