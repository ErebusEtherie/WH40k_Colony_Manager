"""Colony-based representative assignment endpoint tests."""

from fastapi import status
from fastapi.testclient import TestClient


class TestColonyRepresentativeEndpoints:
    """Test colony-based representative assignment endpoints (new atomic endpoints)."""

    def test_assign_representative_via_colony_endpoint(self, auth_client: TestClient) -> None:
        """Test assigning a representative to a colony via PUT /colonies/{id}/representative."""
        # Create colony
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Test Colony",
                "founder_name": "Test Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]

        # Create representative
        rep_response = auth_client.post(
            "/api/v1/representatives",
            json={
                "name": "Test Rep",
                "type": "judge",
                "personalities": [
                    {
                        "name": "lawful",
                        "display_name": "Lawful",
                        "description": "Strict adherence to law and order.",
                    }
                ],
                "stats": {
                    "ws": 30,
                    "bs": 30,
                    "s": 30,
                    "t": 30,
                    "ag": 30,
                    "int": 50,
                    "per": 40,
                    "wp": 60,
                    "fel": 50,
                },
                "skills": [],
                "talents": [],
            },
        )
        rep_id = rep_response.json()["id"]

        # Assign to colony via new endpoint
        assign_response = auth_client.put(
            f"/api/v1/colonies/{colony_id}/representative",
            params={"representative_id": rep_id},
        )
        assert assign_response.status_code == status.HTTP_200_OK
        data = assign_response.json()
        assert data["assigned_to_colony_id"] == colony_id
        assert data["id"] == rep_id
        assert data["assignment_change"] is not None
        assert data["assignment_change"]["new_representative_id"] == rep_id

    def test_assign_representative_replaces_previous(self, auth_client: TestClient) -> None:
        """Test that assigning a new representative replaces the previous one."""
        # Create colony
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Test Colony",
                "founder_name": "Test Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]

        # Create two representatives
        rep1_response = auth_client.post(
            "/api/v1/representatives",
            json={
                "name": "Rep One",
                "type": "judge",
                "personalities": [
                    {"name": "lawful", "display_name": "Lawful", "description": "Lawful."}
                ],
                "stats": {
                    "ws": 30,
                    "bs": 30,
                    "s": 30,
                    "t": 30,
                    "ag": 30,
                    "int": 50,
                    "per": 40,
                    "wp": 60,
                    "fel": 50,
                },
                "skills": [],
                "talents": [],
            },
        )
        rep1_id = rep1_response.json()["id"]

        rep2_response = auth_client.post(
            "/api/v1/representatives",
            json={
                "name": "Rep Two",
                "type": "cardinal",
                "personalities": [
                    {"name": "devout", "display_name": "Devout", "description": "Devout."}
                ],
                "stats": {
                    "ws": 30,
                    "bs": 30,
                    "s": 30,
                    "t": 30,
                    "ag": 30,
                    "int": 40,
                    "per": 50,
                    "wp": 60,
                    "fel": 40,
                },
                "skills": [],
                "talents": [],
            },
        )
        rep2_id = rep2_response.json()["id"]

        # Assign first representative
        assign1_response = auth_client.put(
            f"/api/v1/colonies/{colony_id}/representative",
            params={"representative_id": rep1_id},
        )
        assert assign1_response.status_code == status.HTTP_200_OK

        # Assign second representative (should replace first)
        assign2_response = auth_client.put(
            f"/api/v1/colonies/{colony_id}/representative",
            params={"representative_id": rep2_id},
        )
        assert assign2_response.status_code == status.HTTP_200_OK
        data = assign2_response.json()
        assert data["assigned_to_colony_id"] == colony_id
        assert data["id"] == rep2_id
        assert data["assignment_change"]["previous_representative_id"] == rep1_id
        assert data["assignment_change"]["new_representative_id"] == rep2_id

        # Verify first representative is now unassigned
        get_rep1_response = auth_client.get(f"/api/v1/representatives/{rep1_id}")
        assert get_rep1_response.status_code == status.HTTP_200_OK

    def test_unassign_representative_via_colony_endpoint(self, auth_client: TestClient) -> None:
        """Test unassigning a representative from a colony via
        DELETE /colonies/{id}/representative.
        """
        # Create colony
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Test Colony",
                "founder_name": "Test Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]

        # Create representative
        rep_response = auth_client.post(
            "/api/v1/representatives",
            json={
                "name": "Test Rep",
                "type": "judge",
                "personalities": [
                    {"name": "lawful", "display_name": "Lawful", "description": "Lawful."}
                ],
                "stats": {
                    "ws": 30,
                    "bs": 30,
                    "s": 30,
                    "t": 30,
                    "ag": 30,
                    "int": 50,
                    "per": 40,
                    "wp": 60,
                    "fel": 50,
                },
                "skills": [],
                "talents": [],
            },
        )
        rep_id = rep_response.json()["id"]

        # Assign to colony
        assign_response = auth_client.put(
            f"/api/v1/colonies/{colony_id}/representative",
            params={"representative_id": rep_id},
        )
        assert assign_response.status_code == status.HTTP_200_OK

        # Unassign via new endpoint
        unassign_response = auth_client.delete(f"/api/v1/colonies/{colony_id}/representative")
        assert unassign_response.status_code == status.HTTP_200_OK
        data = unassign_response.json()
        assert data["assigned_to_colony_id"] is None
        assert data["assignment_change"]["new_representative_id"] is None
        assert data["assignment_change"]["previous_representative_id"] == rep_id

    def test_unassign_representative_not_found(self, auth_client: TestClient) -> None:
        """Test unassigning when no representative is assigned returns 404."""
        # Create colony without representative
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Test Colony",
                "founder_name": "Test Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]

        # Try to unassign (should fail)
        unassign_response = auth_client.delete(f"/api/v1/colonies/{colony_id}/representative")
        assert unassign_response.status_code == status.HTTP_404_NOT_FOUND

    def test_assign_nonexistent_representative(self, auth_client: TestClient) -> None:
        """Test assigning a non-existent representative returns 404."""
        # Create colony
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Test Colony",
                "founder_name": "Test Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]

        # Try to assign non-existent representative
        assign_response = auth_client.put(
            f"/api/v1/colonies/{colony_id}/representative",
            params={"representative_id": 99999},
        )
        assert assign_response.status_code == status.HTTP_404_NOT_FOUND

    def test_assign_to_nonexistent_colony(self, auth_client: TestClient) -> None:
        """Test assigning to a non-existent colony returns 404."""
        # Create representative
        rep_response = auth_client.post(
            "/api/v1/representatives",
            json={
                "name": "Test Rep",
                "type": "judge",
                "personalities": [
                    {"name": "lawful", "display_name": "Lawful", "description": "Lawful."}
                ],
                "stats": {
                    "ws": 30,
                    "bs": 30,
                    "s": 30,
                    "t": 30,
                    "ag": 30,
                    "int": 50,
                    "per": 40,
                    "wp": 60,
                    "fel": 50,
                },
                "skills": [],
                "talents": [],
            },
        )
        rep_id = rep_response.json()["id"]

        # Try to assign to non-existent colony
        assign_response = auth_client.put(
            "/api/v1/colonies/99999/representative",
            params={"representative_id": rep_id},
        )
        assert assign_response.status_code == status.HTTP_404_NOT_FOUND
