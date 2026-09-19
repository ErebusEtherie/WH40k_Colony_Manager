"""Integration tests for Colony Users API endpoints."""

from fastapi.testclient import TestClient


class TestColonyUsersAPI:
    """Integration tests for colony membership management endpoints."""

    def test_get_colony_members(self, auth_client: TestClient):
        """Test retrieving all members of a colony."""
        colony_data = {
            "name": "Members Test Colony",
            "founder_name": "Test Owner",
            "colony_type": "mining_and_industry",
        }
        colony_response = auth_client.post("/api/v1/colonies", json=colony_data)
        colony_id = colony_response.json()["id"]

        response = auth_client.get(f"/api/v1/colonies/{colony_id}/members")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "meta" in data
        assert isinstance(data["items"], list)

    def test_add_member_to_colony(self, auth_client: TestClient):
        """Test adding a user as a member to a colony."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Add Member Test",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]

        user_data = {
            "username": "newmember",
            "email": "member@example.com",
            "password": "TestPass123!",
        }
        user_response = auth_client.post("/api/v1/auth/register", json=user_data)
        user_id = user_response.json()["id"]

        member_data = {"user_id": user_id, "role": "viewer"}
        response = auth_client.post(f"/api/v1/colonies/{colony_id}/members", json=member_data)
        assert response.status_code == 201
        member = response.json()
        assert member["user_id"] == user_id
        assert member["colony_id"] == colony_id
        assert member["role"] == "viewer"

    def test_get_colony_member(self, auth_client: TestClient):
        """Test retrieving a specific member of a colony."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Get Member Test",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]

        user_data = {
            "username": "specificmember",
            "email": "specific@example.com",
            "password": "TestPass123!",
        }
        user_response = auth_client.post("/api/v1/auth/register", json=user_data)
        user_id = user_response.json()["id"]

        member_data = {"user_id": user_id, "role": "viewer"}
        auth_client.post(f"/api/v1/colonies/{colony_id}/members", json=member_data)

        response = auth_client.get(f"/api/v1/colonies/{colony_id}/members/{user_id}")
        assert response.status_code == 200
        member = response.json()
        assert member["user_id"] == user_id
        assert member["colony_id"] == colony_id

    def test_remove_member_from_colony(self, auth_client: TestClient):
        """Test removing a member from a colony."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Remove Member Test",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]

        user_data = {
            "username": "toremove",
            "email": "remove@example.com",
            "password": "TestPass123!",
        }
        user_response = auth_client.post("/api/v1/auth/register", json=user_data)
        user_id = user_response.json()["id"]

        member_data = {"user_id": user_id, "role": "viewer"}
        auth_client.post(f"/api/v1/colonies/{colony_id}/members", json=member_data)

        response = auth_client.delete(f"/api/v1/colonies/{colony_id}/members/{user_id}")
        assert response.status_code == 204

        # After removing the added member, only the colony creator remains
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/members")
        data = response.json()
        assert len(data["items"]) == 1  # Creator is auto-added as owner

    def test_invalid_role_rejected(self, auth_client: TestClient):
        """Test adding a member with invalid role fails."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Invalid Role Test",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]

        user_data = {
            "username": "invalidrole",
            "email": "invalid@example.com",
            "password": "TestPass123!",
        }
        user_response = auth_client.post("/api/v1/auth/register", json=user_data)
        user_id = user_response.json()["id"]

        member_data = {"user_id": user_id, "role": "invalid_role"}
        response = auth_client.post(f"/api/v1/colonies/{colony_id}/members", json=member_data)
        assert response.status_code == 422

    def test_add_nonexistent_user(self, auth_client: TestClient):
        """Test adding a non-existent user fails."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Nonexistent User Test",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]

        member_data = {"user_id": 99999, "role": "viewer"}
        response = auth_client.post(f"/api/v1/colonies/{colony_id}/members", json=member_data)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_add_member_happy_path(self, auth_client: TestClient):
        """Test successfully adding a valid user to a colony."""
        # Create colony
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Happy Path Test Colony",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]

        # Create user
        user_data = {
            "username": "happypath_user",
            "email": "happypath@example.com",
            "password": "TestPass123!",
        }
        user_response = auth_client.post("/api/v1/auth/register", json=user_data)
        user_id = user_response.json()["id"]

        # Add user to colony
        member_data = {"user_id": user_id, "role": "viewer"}
        response = auth_client.post(f"/api/v1/colonies/{colony_id}/members", json=member_data)

        # Assert success
        assert response.status_code == 201
        member = response.json()
        assert member["user_id"] == user_id
        assert member["colony_id"] == colony_id
        assert member["role"] == "viewer"
        assert "id" in member
        assert "joined_at" in member

        # Verify membership can be retrieved
        get_response = auth_client.get(f"/api/v1/colonies/{colony_id}/members/{user_id}")
        assert get_response.status_code == 200
        assert get_response.json()["user_id"] == user_id

    def test_get_member_with_nonexistent_user(self, auth_client: TestClient):
        """Test 404 when getting a member that doesn't exist."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Not Found Test",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]

        response = auth_client.get(f"/api/v1/colonies/{colony_id}/members/99999")
        assert response.status_code == 404

    def test_add_duplicate_member(self, auth_client: TestClient):
        """Test adding a user who is already a member fails."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Duplicate Test",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]

        user_data = {
            "username": "duplicate",
            "email": "duplicate@example.com",
            "password": "TestPass123!",
        }
        user_response = auth_client.post("/api/v1/auth/register", json=user_data)
        user_id = user_response.json()["id"]

        member_data = {"user_id": user_id, "role": "viewer"}
        auth_client.post(f"/api/v1/colonies/{colony_id}/members", json=member_data)

        response = auth_client.post(f"/api/v1/colonies/{colony_id}/members", json=member_data)
        assert response.status_code in [400, 409]

    def test_valid_roles(self, auth_client: TestClient):
        """Test all valid colony member roles."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Roles Test",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]

        valid_roles = ["owner", "editor", "viewer"]
        for i, role in enumerate(valid_roles):
            user_data = {
                "username": f"role{i}",
                "email": f"role{i}@example.com",
                "password": "TestPass123!",
            }
            user_response = auth_client.post("/api/v1/auth/register", json=user_data)
            user_id = user_response.json()["id"]

            member_data = {"user_id": user_id, "role": role}
            response = auth_client.post(f"/api/v1/colonies/{colony_id}/members", json=member_data)
            assert response.status_code == 201
            assert response.json()["role"] == role

    def test_update_member_role(self, auth_client: TestClient):
        """Test updating a member's role in a colony."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Update Role Test",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]

        user_data = {
            "username": "roleupdate",
            "email": "roleupdate@example.com",
            "password": "TestPass123!",
        }
        user_response = auth_client.post("/api/v1/auth/register", json=user_data)
        user_id = user_response.json()["id"]

        member_data = {"user_id": user_id, "role": "viewer"}
        auth_client.post(f"/api/v1/colonies/{colony_id}/members", json=member_data)

        update_data = {"role": "editor"}
        response = auth_client.patch(
            f"/api/v1/colonies/{colony_id}/members/{user_id}", json=update_data
        )
        assert response.status_code == 200
        member = response.json()
        assert member["role"] == "editor"

    def test_transfer_ownership_happy_path(self, auth_client: TestClient):
        """Test successfully transferring colony ownership."""
        # Create colony
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Transfer Test Colony",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]

        # Create new owner user
        new_owner_data = {
            "username": "new_owner",
            "email": "newowner@example.com",
            "password": "TestPass123!",
        }
        new_owner_response = auth_client.post("/api/v1/auth/register", json=new_owner_data)
        new_owner_id = new_owner_response.json()["id"]

        # Add new owner as member first
        auth_client.post(
            f"/api/v1/colonies/{colony_id}/members",
            json={"user_id": new_owner_id, "role": "editor"},
        )

        # Transfer ownership
        transfer_data = {"new_owner_id": new_owner_id, "demote_current": True}
        response = auth_client.post(
            f"/api/v1/colonies/{colony_id}/members/transfer-ownership",
            json=transfer_data,
        )

        # Assert success
        assert response.status_code == 200
        result = response.json()
        assert result["colony_id"] == colony_id
        assert result["new_owner_id"] == new_owner_id
        assert result["previous_owner_demoted"] is True

        # Verify new owner has OWNER role
        get_response = auth_client.get(f"/api/v1/colonies/{colony_id}/members/{new_owner_id}")
        assert get_response.status_code == 200
        assert get_response.json()["role"] == "owner"

    def test_transfer_ownership_nonexistent_new_owner(self, auth_client: TestClient):
        """Test 404 when transferring ownership to non-existent user."""
        # Create colony
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Nonexistent New Owner Test",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]

        # Try to transfer to non-existent user
        transfer_data = {"new_owner_id": 99999, "demote_current": True}
        response = auth_client.post(
            f"/api/v1/colonies/{colony_id}/members/transfer-ownership",
            json=transfer_data,
        )

        # Assert 404
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_transfer_ownership_same_user(self, auth_client: TestClient):
        """Test 400 when transferring ownership to the same user."""
        # Create colony
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Same User Test",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]

        # Get current user info from a member endpoint
        members_response = auth_client.get(f"/api/v1/colonies/{colony_id}/members")
        current_user_id = members_response.json()["items"][0]["user_id"]

        # Try to transfer to self
        transfer_data = {"new_owner_id": current_user_id, "demote_current": True}
        response = auth_client.post(
            f"/api/v1/colonies/{colony_id}/members/transfer-ownership",
            json=transfer_data,
        )

        # Assert 400
        assert response.status_code == 400
        assert "same user" in response.json()["detail"].lower()

    def test_transfer_ownership_without_demotion(self, auth_client: TestClient):
        """Test transferring ownership without demoting current owner."""
        # Create colony
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "No Demotion Test",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]

        # Create new owner user
        new_owner_data = {
            "username": "new_owner_no_demote",
            "email": "newowner2@example.com",
            "password": "TestPass123!",
        }
        new_owner_response = auth_client.post("/api/v1/auth/register", json=new_owner_data)
        new_owner_id = new_owner_response.json()["id"]

        # Add new owner as member first
        auth_client.post(
            f"/api/v1/colonies/{colony_id}/members",
            json={"user_id": new_owner_id, "role": "editor"},
        )

        # Transfer ownership without demotion
        transfer_data = {"new_owner_id": new_owner_id, "demote_current": False}
        response = auth_client.post(
            f"/api/v1/colonies/{colony_id}/members/transfer-ownership",
            json=transfer_data,
        )

        # Assert success
        assert response.status_code == 200
        assert response.json()["previous_owner_demoted"] is False

        # Verify current owner still has OWNER role (now both are owners)
        members_response = auth_client.get(f"/api/v1/colonies/{colony_id}/members")
        members = members_response.json()["items"]
        owner_count = sum(1 for m in members if m["role"] == "owner")
        assert owner_count == 2


class TestColonyUsersPagination:
    """Tests for colony users pagination."""

    def test_list_colony_users_pagination(self, auth_client: TestClient):
        """Test colony users pagination with offset, limit, has_more, total."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Pagination Test",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]
        # Create 24 users and add them to the colony (owner already exists, total=25)
        for i in range(24):
            user_data = {
                "username": f"user{i}",
                "email": f"user{i}@example.com",
                "password": "TestPass123!",
            }
            user_response = auth_client.post("/api/v1/auth/register", json=user_data)
            user_id = user_response.json()["id"]
            auth_client.post(
                f"/api/v1/colonies/{colony_id}/members", json={"user_id": user_id, "role": "viewer"}
            )
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/members")
        data = response.json()
        assert len(data["items"]) == 20, f"Expected 20 items, got {len(data['items'])}"
        assert data["meta"]["total"] == 25, f"Expected total=25, got {data['meta']['total']}"
        assert data["meta"]["has_more"] is True
        assert data["meta"]["offset"] == 0
        assert data["meta"]["limit"] == 20

    def test_list_colony_users_pagination_edge_cases(self, auth_client: TestClient):
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
        # Create 9 users (owner already exists, total=10)
        for i in range(9):
            user_data = {
                "username": f"edge{i}",
                "email": f"edge{i}@example.com",
                "password": "TestPass123!",
            }
            user_response = auth_client.post("/api/v1/auth/register", json=user_data)
            user_id = user_response.json()["id"]
            auth_client.post(
                f"/api/v1/colonies/{colony_id}/members", json={"user_id": user_id, "role": "viewer"}
            )
        # Test exact page size
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/members?limit=10")
        data = response.json()
        assert len(data["items"]) == 10
        assert data["meta"]["has_more"] is False
        # Test offset beyond total
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/members?offset=100")
        data = response.json()
        assert len(data["items"]) == 0
        assert data["meta"]["has_more"] is False
        # Test limit=1
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/members?limit=1")
        data = response.json()
        assert len(data["items"]) == 1
        assert data["meta"]["has_more"] is True

    def test_list_colony_users_empty(self, auth_client: TestClient):
        """Test listing members for colony with no members (except owner)."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Empty Members",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/members")
        data = response.json()
        # Colony has at least the owner
        assert data["meta"]["total"] >= 1
        assert data["meta"]["has_more"] is False

    def test_list_colony_users_offset(self, auth_client: TestClient):
        """Test pagination with different offset values."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Offset Test",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]
        # Create 14 users (owner already exists, total=15)
        for i in range(14):
            user_data = {
                "username": f"offset{i}",
                "email": f"offset{i}@example.com",
                "password": "TestPass123!",
            }
            user_response = auth_client.post("/api/v1/auth/register", json=user_data)
            user_id = user_response.json()["id"]
            auth_client.post(
                f"/api/v1/colonies/{colony_id}/members", json={"user_id": user_id, "role": "viewer"}
            )
        # Test offset=5
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/members?offset=5&limit=5")
        data = response.json()
        assert len(data["items"]) == 5
        assert data["meta"]["offset"] == 5
        assert data["meta"]["has_more"] is True
        # Test offset=10
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/members?offset=10&limit=5")
        data = response.json()
        assert len(data["items"]) == 5
        assert data["meta"]["offset"] == 10
        assert data["meta"]["has_more"] is False

    def test_list_colony_users_limit_variations(self, auth_client: TestClient):
        """Test pagination with different limit values."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Limit Test",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]
        # Create 29 users (owner already exists, total=30)
        for i in range(29):
            user_data = {
                "username": f"limit{i}",
                "email": f"limit{i}@example.com",
                "password": "TestPass123!",
            }
            user_response = auth_client.post("/api/v1/auth/register", json=user_data)
            user_id = user_response.json()["id"]
            auth_client.post(
                f"/api/v1/colonies/{colony_id}/members", json={"user_id": user_id, "role": "viewer"}
            )
        # Test limit=5
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/members?limit=5")
        data = response.json()
        assert len(data["items"]) == 5
        assert data["meta"]["limit"] == 5
        assert data["meta"]["has_more"] is True
        # Test limit=50 (max is 100)
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/members?limit=50")
        data = response.json()
        assert len(data["items"]) == 30
        assert data["meta"]["limit"] == 50
        assert data["meta"]["has_more"] is False

    def test_list_colony_users_total_pages(self, auth_client: TestClient):
        """Test that total_pages is calculated correctly."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Total Pages",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]
        # Create 24 users (owner already exists, total=25)
        for i in range(24):
            user_data = {
                "username": f"pages{i}",
                "email": f"pages{i}@example.com",
                "password": "TestPass123!",
            }
            user_response = auth_client.post("/api/v1/auth/register", json=user_data)
            user_id = user_response.json()["id"]
            auth_client.post(
                f"/api/v1/colonies/{colony_id}/members", json={"user_id": user_id, "role": "viewer"}
            )
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/members?limit=10")
        data = response.json()
        assert data["meta"]["total"] == 25
        assert data["meta"]["total_pages"] == 3  # ceil(25/10) = 3
        assert data["meta"]["limit"] == 10

    def test_list_colony_users_last_page(self, auth_client: TestClient):
        """Test pagination on the last page."""
        colony_response = auth_client.post(
            "/api/v1/colonies",
            json={
                "name": "Last Page",
                "founder_name": "Owner",
                "colony_type": "mining_and_industry",
            },
        )
        colony_id = colony_response.json()["id"]
        # Create 21 users (owner already exists, total=22)
        for i in range(21):
            user_data = {
                "username": f"last{i}",
                "email": f"last{i}@example.com",
                "password": "TestPass123!",
            }
            user_response = auth_client.post("/api/v1/auth/register", json=user_data)
            user_id = user_response.json()["id"]
            auth_client.post(
                f"/api/v1/colonies/{colony_id}/members", json={"user_id": user_id, "role": "viewer"}
            )
        # Get last page (offset=20, limit=10)
        response = auth_client.get(f"/api/v1/colonies/{colony_id}/members?offset=20&limit=10")
        data = response.json()
        assert len(data["items"]) == 2  # Only 2 items on last page
        assert data["meta"]["has_more"] is False
        assert data["meta"]["offset"] == 20
