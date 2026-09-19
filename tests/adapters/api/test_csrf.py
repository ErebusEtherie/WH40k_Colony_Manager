"""CSRF protection middleware tests.

These verify the narrowed CSRF exemption: only the pre-authentication auth
endpoints (login, register, refresh, csrf-token) skip CSRF validation, while
authenticated state-changers under /auth (change-password, revoke, revoke-all)
require a valid double-submit X-CSRF-Token like any other mutating request.
"""

import os

import pytest
from fastapi.testclient import TestClient

from colony_manager.adapters.api.app import create_app
from colony_manager.adapters.persistence.db import init_db


@pytest.fixture
def client(tmp_path):
    """Create an app client with an isolated DB and no preset CSRF header."""
    db_path = tmp_path / "test.db"
    os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-csrf-testing-32b"

    import colony_manager.adapters.api.dependencies as deps
    from colony_manager.adapters.api.dependencies import init_rule_config_provider

    init_rule_config_provider()
    init_db(db_path)
    app = create_app()
    app.dependency_overrides[deps.get_db_path] = lambda: db_path

    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
    if "JWT_SECRET_KEY" in os.environ:
        del os.environ["JWT_SECRET_KEY"]


def _register_and_login(client: TestClient) -> None:
    """Register a user and log in via cookie auth (does not set CSRF header)."""
    register = {
        "username": "csrftest",
        "email": "csrf@example.com",
        "password": "SecurePass123!",
    }
    assert client.post("/api/v1/auth/register", json=register).status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "csrftest", "password": "SecurePass123!"},
    )
    assert login.status_code == 200


def _get_csrf_token(client: TestClient) -> str:
    """Fetch a fresh double-submit CSRF token (also sets the CSRF cookie)."""
    csrf_response = client.get("/api/v1/auth/csrf-token")
    assert csrf_response.status_code == 200
    return csrf_response.json()["csrf_token"]


class TestCsrfExemptions:
    """Pre-authentication auth endpoints must work without a CSRF token."""

    def test_login_requires_no_csrf(self, client):
        """Login (and register) run before a session exists, so no CSRF."""
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "username": "exemptuser",
                "email": "exempt@example.com",
                "password": "SecurePass123!",
            },
        )
        assert resp.status_code == 201
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "exemptuser", "password": "SecurePass123!"},
        )
        assert resp.status_code == 200

    def test_refresh_requires_no_csrf(self, client):
        """Refresh runs off a cookie, not a header, so it is CSRF-exempt."""
        _register_and_login(client)
        resp = client.post("/api/v1/auth/refresh")
        assert resp.status_code == 200

    def test_csrf_token_endpoint_accessible_without_auth(self, client):
        """The csrf-token bootstrap endpoint is reachable pre-auth."""
        resp = client.get("/api/v1/auth/csrf-token")
        assert resp.status_code == 200
        assert "csrf_token" in resp.json()


class TestCsrfProtected:
    """Authenticated state-changers under /auth are no longer CSRF-exempt."""

    def test_mutating_endpoint_rejects_missing_csrf(self, client):
        _register_and_login(client)
        resp = client.post(
            "/api/v1/colonies",
            json={"name": "X", "founder_name": "Y", "colony_type": "mining_and_industry"},
        )
        assert resp.status_code == 403
        assert "CSRF token" in resp.json()["detail"]

    def test_change_password_rejects_missing_csrf(self, client):
        _register_and_login(client)
        resp = client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "SecurePass123!", "new_password": "NewSecure456!"},
        )
        assert resp.status_code == 403

    def test_revoke_rejects_missing_csrf(self, client):
        _register_and_login(client)
        resp = client.post("/api/v1/auth/revoke", json={"reason": "logout"})
        assert resp.status_code == 403

    def test_change_password_succeeds_with_valid_csrf(self, client):
        _register_and_login(client)
        token = _get_csrf_token(client)
        resp = client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "SecurePass123!", "new_password": "NewSecure456!"},
            headers={"X-CSRF-Token": token},
        )
        assert resp.status_code == 200
