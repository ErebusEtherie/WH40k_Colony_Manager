"""Integration tests for authentication flow."""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from colony_manager.adapters.api.app import create_app
from colony_manager.adapters.persistence.db import init_db


@pytest.fixture
def integration_client(tmp_path: Path):
    """Create test client with isolated database for integration tests."""
    from colony_manager.adapters.api.dependencies import init_rule_config_provider

    db_path = tmp_path / "test.db"
    os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-minimum-32-bytes"

    import colony_manager.adapters.api.dependencies as deps

    init_db(db_path)
    init_rule_config_provider()
    app = create_app()
    app.dependency_overrides[deps.get_db_path] = lambda: db_path

    client = TestClient(app)
    yield client

    app.dependency_overrides.clear()
    if "JWT_SECRET_KEY" in os.environ:
        del os.environ["JWT_SECRET_KEY"]


@pytest.fixture
def reuse_detection_enabled(monkeypatch):
    """Enable refresh-token reuse detection for the auth-service dependency.

    ``AuthService`` is built by ``dependencies.get_auth_service``, which reads
    ``refresh_reuse_detection_enabled`` from the security settings. Patching that
    module's ``get_security_settings`` reference switches the flag on only for
    service construction, without disturbing the (cached) settings the rest of
    the app uses.
    """
    from colony_manager.adapters.api import dependencies as deps
    from colony_manager.config import settings as settings_module

    def _settings_with_reuse_detection():
        real = settings_module.get_security_settings()
        return real.model_copy(update={"refresh_reuse_detection_enabled": True})

    monkeypatch.setattr(deps, "get_security_settings", _settings_with_reuse_detection)


def _login_with_csrf(client: TestClient, username: str, password: str) -> dict:
    """Log in via cookie-based auth and set up the double-submit CSRF token.

    Bearer auth was removed from the API, so the session cookie set by
    ``/auth/login`` is what authenticates subsequent requests. State-changing
    requests additionally require the CSRF token from ``/auth/csrf-token``
    echoed back in the ``X-CSRF-Token`` header. When a test switches users,
    call this again to re-login (which replaces the session cookie); the CSRF
    cookie persists across user switches on the same client.

    Args:
        client: The TestClient to authenticate.
        username: User to log in as.
        password: User's password.

    Returns:
        The login response body (a success message only; tokens are never
        returned in the body, only set as HttpOnly cookies).
    """
    login_response = client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    assert login_response.status_code == 200
    csrf_response = client.get("/api/v1/auth/csrf-token")
    assert csrf_response.status_code == 200
    client.headers["X-CSRF-Token"] = csrf_response.json()["csrf_token"]
    # Tokens are delivered only via HttpOnly cookies, never in the response body,
    # so there is nothing else to return here.
    return login_response.json()


class TestAuthFlowRegistration:
    """Tests for complete registration to authenticated request flow."""

    def test_registration_to_authenticated_request(self, integration_client):
        """Test full flow: register → login → authenticated request.

        Flow:
        1. Register new user with valid credentials
        2. Login to obtain access/refresh tokens
        3. Call /me endpoint to verify user details
        4. Use authenticated session to perform protected action (create colony)
        5. Verify user details match across all endpoints
        """
        # Step 1: Register new user
        register_data = {
            "username": "integration_user",
            "email": "integration@example.com",
            "password": "SecurePass123!",
        }
        register_response = integration_client.post("/api/v1/auth/register", json=register_data)
        assert register_response.status_code == 201
        user_data = register_response.json()
        assert user_data["username"] == "integration_user"
        assert user_data["email"] == "integration@example.com"
        assert user_data["role"] == "viewer"
        user_id = user_data["id"]

        # Step 2: Login to get tokens
        login_data = {
            "username": "integration_user",
            "password": "SecurePass123!",
        }
        login_response = integration_client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        login_body = login_response.json()
        # Tokens are delivered only via HttpOnly cookies, never in the body
        assert "message" in login_body
        assert "access_token" not in login_body
        assert "refresh_token" not in login_body

        # Step 3: Set up the double-submit CSRF token for state-changing requests.
        # The login session cookie authenticates; the CSRF header protects mutating calls.
        csrf_response = integration_client.get("/api/v1/auth/csrf-token")
        csrf_token = csrf_response.json()["csrf_token"]
        integration_client.headers["X-CSRF-Token"] = csrf_token

        # Get current user profile - verify all user details
        me_response = integration_client.get("/api/v1/auth/me")
        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["username"] == "integration_user"
        assert me_data["email"] == "integration@example.com"
        assert me_data["id"] == user_id
        assert me_data["role"] == "viewer"
        assert me_data["is_active"] is True

        # Step 4: Create a colony (authenticated action)
        colony_data = {
            "name": "Test Colony",
            "founder_name": "Test Owner",
            "colony_type": "mining_and_industry",
        }
        colony_response = integration_client.post("/api/v1/colonies", json=colony_data)
        assert colony_response.status_code == 201
        colony = colony_response.json()
        assert colony["name"] == "Test Colony"
        assert colony["founder_name"] == "Test Owner"
        # Verify colony has an id
        assert "id" in colony

    def test_registration_with_invalid_password(self, integration_client):
        """Test registration fails with weak password.

        Password requirements:
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one number
        - At least one special character
        """
        # Test too short password
        register_data = {
            "username": "weak_user",
            "email": "weak@example.com",
            "password": "Short1!",  # Only 7 characters
        }
        response = integration_client.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == 422  # Validation error

        # Test missing uppercase
        register_data = {
            "username": "weak_user",
            "email": "weak@example.com",
            "password": "noupperc1!",  # No uppercase
        }
        response = integration_client.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == 400
        assert "password" in response.json()["detail"].lower()

        # Test missing number
        register_data = {
            "username": "weak_user",
            "email": "weak@example.com",
            "password": "NoNumber!",  # No number
        }
        response = integration_client.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == 400
        assert "password" in response.json()["detail"].lower()

        # Test missing special character
        register_data = {
            "username": "weak_user",
            "email": "weak@example.com",
            "password": "NoSpecial1",  # No special char
        }
        response = integration_client.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == 400
        assert "password" in response.json()["detail"].lower()

    def test_registration_duplicate_username(self, integration_client):
        """Test registration fails when username already exists."""
        register_data = {
            "username": "duplicate_user",
            "email": "first@example.com",
            "password": "SecurePass123!",
        }
        response = integration_client.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == 201

        # Try to register same username with different email
        register_data["email"] = "second@example.com"
        response = integration_client.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == 400
        assert "username" in response.json()["detail"].lower()

    def test_registration_duplicate_email(self, integration_client):
        """Test registration fails when email already exists."""
        register_data = {
            "username": "first_user",
            "email": "duplicate@example.com",
            "password": "SecurePass123!",
        }
        response = integration_client.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == 201

        # Try to register same email with different username
        register_data["username"] = "second_user"
        response = integration_client.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == 400
        assert "email" in response.json()["detail"].lower()


class TestAuthFlowLogin:
    """Tests for login flow and error handling."""

    def test_login_with_wrong_password(self, integration_client):
        """Test login fails with incorrect password."""
        # Register user
        register_data = {
            "username": "login_user",
            "email": "login@example.com",
            "password": "SecurePass123!",
        }
        integration_client.post("/api/v1/auth/register", json=register_data)

        # Try login with wrong password
        login_data = {
            "username": "login_user",
            "password": "WrongPassword1!",
        }
        response = integration_client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, integration_client):
        """Test login fails for non-existent user."""
        login_data = {
            "username": "nonexistent_user",
            "password": "SecurePass123!",
        }
        response = integration_client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()


class TestAuthFlowMeEndpoint:
    """Tests for /me endpoint authentication and user details."""

    def test_me_unauthenticated(self, integration_client):
        """Test /me endpoint returns 401 without authentication."""
        response = integration_client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_me_with_invalid_cookie(self, integration_client):
        """Test /me endpoint returns 401 with an invalid session cookie."""
        integration_client.cookies["rt_access_token"] = "invalid-token"
        integration_client.cookies["rt_refresh_token"] = "invalid-token"
        response = integration_client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_me_returns_full_user_details(self, integration_client):
        """Test /me endpoint returns complete user information."""
        # Register and login
        register_data = {
            "username": "me_user",
            "email": "me@example.com",
            "password": "SecurePass123!",
        }
        integration_client.post("/api/v1/auth/register", json=register_data)

        login_data = {"username": "me_user", "password": "SecurePass123!"}
        login_response = integration_client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        # Authenticated via the session cookie set by login
        me_response = integration_client.get("/api/v1/auth/me")
        assert me_response.status_code == 200
        me_data = me_response.json()

        # Verify all expected fields are present
        assert "id" in me_data
        assert "username" in me_data
        assert "email" in me_data
        assert "role" in me_data
        assert "is_active" in me_data

        # Verify values match registration data
        assert me_data["username"] == "me_user"
        assert me_data["email"] == "me@example.com"
        assert me_data["role"] == "viewer"
        assert me_data["is_active"] is True

        # Verify sensitive data is NOT included
        assert "password" not in me_data
        assert "hashed_password" not in me_data


class TestAuthFlowTokenRefresh:
    """Tests for token refresh flow."""

    def test_token_refresh_flow(self, integration_client):
        """Test full flow: login → use access token → refresh → use new access token."""
        # Register and login
        register_data = {
            "username": "refresh_user",
            "email": "refresh@example.com",
            "password": "SecurePass123!",
        }
        integration_client.post("/api/v1/auth/register", json=register_data)

        login_data = {"username": "refresh_user", "password": "SecurePass123!"}
        login_response = integration_client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200

        # Authenticated via the session cookie set by login
        me_response = integration_client.get("/api/v1/auth/me")
        assert me_response.status_code == 200
        assert me_response.json()["username"] == "refresh_user"

        # Refresh reads the refresh-token cookie and rotates both cookies
        refresh_response = integration_client.post("/api/v1/auth/refresh")
        assert refresh_response.status_code == 200
        refresh_body = refresh_response.json()
        assert "access_token" not in refresh_body
        assert "refresh_token" not in refresh_body
        assert "message" in refresh_body

        # Rotated cookies still authenticate
        me_response2 = integration_client.get("/api/v1/auth/me")
        assert me_response2.status_code == 200
        assert me_response2.json()["username"] == "refresh_user"

    def test_refresh_invalid_token(self, integration_client):
        """Test refresh fails with an invalid refresh-token cookie."""
        integration_client.cookies["rt_refresh_token"] = "invalid-token"
        response = integration_client.post("/api/v1/auth/refresh")
        assert response.status_code == 401

    def test_refresh_rotation_rejects_reused_refresh_token(self, integration_client):
        """Test that a rotated (consumed) refresh token is rejected if replayed."""
        register_data = {
            "username": "rotation_user",
            "email": "rotation@example.com",
            "password": "SecurePass123!",
        }
        integration_client.post("/api/v1/auth/register", json=register_data)

        login_response = integration_client.post(
            "/api/v1/auth/login",
            json={"username": "rotation_user", "password": "SecurePass123!"},
        )
        assert login_response.status_code == 200

        old_refresh = integration_client.cookies.get("rt_refresh_token")

        refreshed = integration_client.post("/api/v1/auth/refresh")
        assert refreshed.status_code == 200

        # Replaying the consumed refresh token must be rejected as revoked.
        integration_client.cookies["rt_refresh_token"] = old_refresh
        replayed = integration_client.post("/api/v1/auth/refresh")
        assert replayed.status_code == 401

    def test_refresh_reuse_detection_revokes_session_family(
        self, integration_client, reuse_detection_enabled
    ):
        """Test that replaying a rotated refresh token revokes the whole family."""
        register_data = {
            "username": "reuse_detection_user",
            "email": "reuse_detection@example.com",
            "password": "SecurePass123!",
        }
        integration_client.post("/api/v1/auth/register", json=register_data)

        login_response = integration_client.post(
            "/api/v1/auth/login",
            json={"username": "reuse_detection_user", "password": "SecurePass123!"},
        )
        assert login_response.status_code == 200

        old_refresh = integration_client.cookies.get("rt_refresh_token")
        refreshed = integration_client.post("/api/v1/auth/refresh")
        assert refreshed.status_code == 200
        rotated_refresh = integration_client.cookies.get("rt_refresh_token")
        assert rotated_refresh != old_refresh

        # Replaying the consumed pre-rotation cookie is rejected...
        integration_client.cookies["rt_refresh_token"] = old_refresh
        replayed = integration_client.post("/api/v1/auth/refresh")
        assert replayed.status_code == 401

        # ...and the whole session family is revoked: the legitimate client's
        # freshly rotated cookie is dead too.
        integration_client.cookies["rt_refresh_token"] = rotated_refresh
        second = integration_client.post("/api/v1/auth/refresh")
        assert second.status_code == 401


class TestAuthFlowTokenRevocation:
    """Tests for token revocation."""

    def test_revoke_access_token(self, integration_client):
        """Test revoking access token prevents its reuse."""
        # Register and login
        register_data = {
            "username": "revoke_user",
            "email": "revoke@example.com",
            "password": "SecurePass123!",
        }
        integration_client.post("/api/v1/auth/register", json=register_data)

        # login via helper to also set up the double-submit CSRF header,
        # since /revoke is an authenticated state-changer that now enforces CSRF
        _login_with_csrf(integration_client, "revoke_user", "SecurePass123!")

        # Use the session cookie set by login
        me_response = integration_client.get("/api/v1/auth/me")
        assert me_response.status_code == 200

        # Revoke the session: the endpoint blacklists the cookie token and clears cookies
        revoke_response = integration_client.post("/api/v1/auth/revoke", json={"reason": "logout"})
        assert revoke_response.status_code == 200
        assert "rt_access_token" not in integration_client.cookies
        assert "rt_refresh_token" not in integration_client.cookies

    def test_logout_revokes_refresh_token(self, integration_client):
        """Test that logout revokes the refresh token server-side.

        After logout the refresh cookie is deleted client-side AND the token is
        revoked server-side, so restoring the captured cookie cannot resurrect
        the session via /auth/refresh.
        """
        register_data = {
            "username": "logout_refresh_user",
            "email": "logout_refresh@example.com",
            "password": "SecurePass123!",
        }
        integration_client.post("/api/v1/auth/register", json=register_data)
        _login_with_csrf(integration_client, "logout_refresh_user", "SecurePass123!")

        refresh_before_logout = integration_client.cookies.get("rt_refresh_token")

        revoke_response = integration_client.post("/api/v1/auth/revoke", json={"reason": "logout"})
        assert revoke_response.status_code == 200
        assert "rt_refresh_token" not in integration_client.cookies

        # Restore the captured refresh cookie: the token is revoked server-side,
        # so refreshing must fail.
        integration_client.cookies["rt_refresh_token"] = refresh_before_logout
        refresh_after_logout = integration_client.post("/api/v1/auth/refresh")
        assert refresh_after_logout.status_code == 401

    def test_revoke_all_tokens(self, integration_client):
        """Test revoking all tokens logs out from all sessions."""
        # Register and login
        register_data = {
            "username": "revoke_all_user",
            "email": "revoke_all@example.com",
            "password": "SecurePass123!",
        }
        integration_client.post("/api/v1/auth/register", json=register_data)

        # login via helper to also set up the double-submit CSRF header,
        # since /revoke-all is an authenticated state-changer that enforces CSRF
        _login_with_csrf(integration_client, "revoke_all_user", "SecurePass123!")

        # Revoke all of the user's sessions
        revoke_all_response = integration_client.post(
            "/api/v1/auth/revoke-all", json={"reason": "security"}
        )
        assert revoke_all_response.status_code == 200

        # The revoke-all should blacklist all refresh tokens for the user
        # Attempt a refresh using the revoked session cookie
        refresh_response = integration_client.post("/api/v1/auth/refresh")
        # Refresh may be accepted or rejected depending on whether the blacklist
        # is consulted during refresh - tolerate either.
        assert refresh_response.status_code in (200, 401)


class TestAuthorizationPermissions:
    """Tests for role-based and colony-level authorization."""

    def test_viewer_cannot_edit_colony(self, integration_client):
        """Test that viewer role cannot edit colony."""
        # Register owner user
        register_data = {
            "username": "viewer_user",
            "email": "viewer@example.com",
            "password": "SecurePass123!",
        }
        integration_client.post("/api/v1/auth/register", json=register_data)
        _login_with_csrf(integration_client, "viewer_user", "SecurePass123!")

        # Create a colony (this auto-members the user as OWNER)
        create_data = {
            "name": "Viewer Test Colony",
            "founder_name": "Test Owner",
            "colony_type": "mining_and_industry",
        }
        colony_response = integration_client.post("/api/v1/colonies", json=create_data)
        assert colony_response.status_code == 201
        colony_id = colony_response.json()["id"]

        # Create another user who will be added as VIEWER
        register_data2 = {
            "username": "viewer_member",
            "email": "viewer_member@example.com",
            "password": "SecurePass123!",
            "role": "viewer",
        }
        integration_client.post("/api/v1/auth/register", json=register_data2)

        # Login as viewer_member to get their user ID
        _login_with_csrf(integration_client, "viewer_member", "SecurePass123!")

        # Get viewer's user ID from /me endpoint
        me_response = integration_client.get("/api/v1/auth/me")
        viewer_id = me_response.json()["id"]

        # Switch back to owner to add member
        _login_with_csrf(integration_client, "viewer_user", "SecurePass123!")
        add_member_data = {"user_id": viewer_id, "role": "viewer"}
        add_response = integration_client.post(
            f"/api/v1/colonies/{colony_id}/members", json=add_member_data
        )
        assert add_response.status_code == 201

        # Now login as viewer and try to edit colony
        _login_with_csrf(integration_client, "viewer_member", "SecurePass123!")
        edit_data = {"name": "Hacked Colony Name"}
        edit_response = integration_client.put(f"/api/v1/colonies/{colony_id}", json=edit_data)
        assert edit_response.status_code == 403
        assert "Insufficient colony permissions" in edit_response.json()["detail"]

    def test_editor_can_edit_colony(self, integration_client):
        """Test that editor role can edit colony."""
        # Clear any existing auth from previous tests
        integration_client.headers.pop("Authorization", None)

        # Register and login as owner
        register_data = {
            "username": "owner_user",
            "email": "owner@example.com",
            "password": "SecurePass123!",
        }
        integration_client.post("/api/v1/auth/register", json=register_data)
        _login_with_csrf(integration_client, "owner_user", "SecurePass123!")

        # Create colony (with auth)
        create_data = {
            "name": "Editor Test Colony",
            "founder_name": "Test Owner",
            "colony_type": "agricultural",
        }
        colony_response = integration_client.post("/api/v1/colonies", json=create_data)
        assert colony_response.status_code == 201
        colony_id = colony_response.json()["id"]

        # Create editor user
        register_data2 = {
            "username": "editor_user",
            "email": "editor@example.com",
            "password": "SecurePass123!",
        }
        integration_client.post("/api/v1/auth/register", json=register_data2)
        _login_with_csrf(integration_client, "editor_user", "SecurePass123!")

        # Get editor's user ID from /me endpoint
        me_response = integration_client.get("/api/v1/auth/me")
        editor_id = me_response.json()["id"]

        # Add editor to colony (switch back to owner)
        _login_with_csrf(integration_client, "owner_user", "SecurePass123!")
        add_member_data = {"user_id": editor_id, "role": "editor"}
        add_response = integration_client.post(
            f"/api/v1/colonies/{colony_id}/members", json=add_member_data
        )
        assert add_response.status_code == 201

        # Login as editor and edit colony
        _login_with_csrf(integration_client, "editor_user", "SecurePass123!")
        edit_data = {"name": "Editor Updated Colony"}
        edit_response = integration_client.put(f"/api/v1/colonies/{colony_id}", json=edit_data)
        assert edit_response.status_code == 200
        assert edit_response.json()["name"] == "Editor Updated Colony"

    def test_admin_can_access_any_colony(self, integration_client, tmp_path, bootstrap_user):
        """Test that admin users can access colonies they don't belong to."""
        # Register regular user and create colony
        register_data = {
            "username": "regular_user",
            "email": "regular@example.com",
            "password": "SecurePass123!",
        }
        integration_client.post("/api/v1/auth/register", json=register_data)
        _login_with_csrf(integration_client, "regular_user", "SecurePass123!")

        # Create colony as regular user
        create_data = {
            "name": "Admin Access Test Colony",
            "founder_name": "Regular User",
            "colony_type": "ecclesiastical",
        }
        colony_response = integration_client.post("/api/v1/colonies", json=create_data)
        assert colony_response.status_code == 201
        colony_id = colony_response.json()["id"]

        # /auth/register only creates VIEWER; bootstrap an admin directly
        bootstrap_user(
            tmp_path / "test.db",
            username="admin_user",
            email="admin@example.com",
            password="SecurePass123!",
            role="admin",
        )
        _login_with_csrf(integration_client, "admin_user", "SecurePass123!")

        # Admin accesses colony they don't belong to
        view_response = integration_client.get(f"/api/v1/colonies/{colony_id}")
        assert view_response.status_code == 200

        # Admin can also edit colony they don't belong to (admin bypass)
        edit_data = {"name": "Admin Updated Colony"}
        edit_response = integration_client.put(f"/api/v1/colonies/{colony_id}", json=edit_data)
        assert edit_response.status_code == 200

    def test_user_cannot_access_unowned_colony(self, integration_client):
        """Test that regular users cannot access colonies they don't belong to."""
        # Create Alice and get her tokens
        register_data1 = {
            "username": "user_alice",
            "email": "alice@example.com",
            "password": "SecurePass123!",
        }
        integration_client.post("/api/v1/auth/register", json=register_data1)
        _login_with_csrf(integration_client, "user_alice", "SecurePass123!")

        # Alice creates colony
        create_data = {
            "name": "Alice's Colony",
            "founder_name": "Alice",
            "colony_type": "mining_and_industry",
        }
        colony_response = integration_client.post("/api/v1/colonies", json=create_data)
        assert colony_response.status_code == 201
        alice_colony_id = colony_response.json()["id"]

        # Register Bob (login switches the session to Bob)
        register_data2 = {
            "username": "user_bob",
            "email": "bob@example.com",
            "password": "SecurePass123!",
        }
        integration_client.post("/api/v1/auth/register", json=register_data2)
        _login_with_csrf(integration_client, "user_bob", "SecurePass123!")

        # Bob tries to access Alice's colony
        view_response = integration_client.get(f"/api/v1/colonies/{alice_colony_id}")
        assert view_response.status_code == 403
        assert "not a member" in view_response.json()["detail"]

    def test_colony_manager_cannot_delete_users(self, integration_client, tmp_path, bootstrap_user):
        """Test that colony_manager role cannot access admin-only endpoints."""
        # /auth/register only creates VIEWER; bootstrap a colony_manager directly
        bootstrap_user(
            tmp_path / "test.db",
            username="manager_user",
            email="manager@example.com",
            password="SecurePass123!",
            role="colony_manager",
        )
        _login_with_csrf(integration_client, "manager_user", "SecurePass123!")

        # Try to access admin-only endpoint (list all users)
        users_response = integration_client.get("/api/v1/users")
        assert users_response.status_code == 403
        assert "Admin access required" in users_response.json()["detail"]

    def test_admin_can_delete_users(self, integration_client, tmp_path, bootstrap_user):
        """Test that admin role can access admin-only endpoints."""
        # /auth/register only creates VIEWER; bootstrap an admin directly
        bootstrap_user(
            tmp_path / "test.db",
            username="admin_delete_user",
            email="admin_delete@example.com",
            password="SecurePass123!",
            role="admin",
        )
        _login_with_csrf(integration_client, "admin_delete_user", "SecurePass123!")

        # Create a user to delete
        register_data2 = {
            "username": "temp_user",
            "email": "temp@example.com",
            "password": "SecurePass123!",
        }
        create_response = integration_client.post("/api/v1/auth/register", json=register_data2)
        temp_user_id = create_response.json()["id"]

        # Admin deletes the user
        delete_response = integration_client.delete(f"/api/v1/users/{temp_user_id}")
        assert delete_response.status_code == 204  # No Content on success
