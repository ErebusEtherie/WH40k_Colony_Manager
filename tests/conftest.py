"""Pytest configuration and shared fixtures."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import colony_manager.adapters.api.dependencies as deps
from colony_manager.adapters.api.app import create_app
from colony_manager.adapters.persistence.db import init_db


def _bootstrap_user(db_path, *, username, email, password, role):
    """Create a user directly in the test DB with an explicit role.

    ``/auth/register`` is intentionally locked to the VIEWER role — a client
    can never supply its own role (see ``auth_router.register``). Tests that
    need elevated roles (``admin``, ``colony_manager``) therefore create
    users through the persistence layer directly, mirroring how a deployment
    would seed an initial admin rather than going through self-service
    registration.

    Args:
        db_path: Path to the test SQLite database.
        username: Username for the new user.
        email: Email for the new user.
        password: Plain-text password (hashed before storage).
        role: The role to assign (one of the UserRole values).

    Returns:
        The created :class:`colony_manager.domain.models.user.User`.
    """
    from colony_manager.adapters.persistence.db import build_database_url
    from colony_manager.adapters.persistence.user_repository_impl import (
        SqlAlchemyUserRepository,
    )
    from colony_manager.domain.models.user import User, UserRole
    from colony_manager.domain.util.auth import hash_password

    repo = SqlAlchemyUserRepository(build_database_url(db_path))
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        role=UserRole(role),
        is_active=True,
    )
    return repo.create(user)


@pytest.fixture
def bootstrap_user():
    """Return the direct user-bootstrap helper for tests that need elevated roles.

    Exposed as a fixture so subdirectory test modules can inject it without
    import-path gymnastics.
    """
    return _bootstrap_user


@pytest.fixture(scope="function")
def test_client(tmp_path):
    """Create test client with isolated database."""
    from colony_manager.adapters.api.dependencies import init_rule_config_provider

    db_path = tmp_path / "test.db"

    # Override dependencies to use test database
    def override_get_db_path() -> Path:
        return db_path

    init_db(db_path)

    # Initialize rule config provider singleton for tests
    init_rule_config_provider()

    app = create_app()

    # Override the dependency after app creation
    app.dependency_overrides[deps.get_db_path] = override_get_db_path

    # Don't raise exceptions for HTTP errors - we want to test error responses
    client = TestClient(app, raise_server_exceptions=False)
    yield client

    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def auth_client(test_client, request, tmp_path, bootstrap_user):
    """Create authenticated test client with a test user using cookie-based auth."""
    # Use unique username per test to avoid conflicts
    test_name = (
        request.node.name.replace("[", "_")
        .replace("]", "_")
        .replace("(", "_")
        .replace(")", "_")[:20]
    )
    username = f"testuser_{test_name}"

    # /auth/register always creates VIEWER users; bootstrap an admin directly
    # so this client retains admin privileges for admin-gated tests.
    bootstrap_user(
        tmp_path / "test.db",
        username=username,
        email=f"{username}@example.com",
        password="TestPass123!",
        role="admin",
    )

    # Login to get cookies (cookie-based auth)
    login_data = {"username": username, "password": "TestPass123!"}
    login_response = test_client.post("/api/v1/auth/login", json=login_data)
    assert login_response.status_code == 200

    # The TestClient automatically handles cookies from Set-Cookie headers
    # Cookies are persisted for subsequent requests on the same client instance

    # Fetch CSRF token for state-changing requests (double-submit pattern)
    csrf_response = test_client.get("/api/v1/auth/csrf-token")
    assert csrf_response.status_code == 200
    csrf_token = csrf_response.json()["csrf_token"]
    test_client.headers["X-CSRF-Token"] = csrf_token

    return test_client


@pytest.fixture
def test_client_with_auth(tmp_path):
    """Create test client with initialized database (for auth tests)."""
    import colony_manager.adapters.api.dependencies as deps
    from colony_manager.adapters.api.dependencies import init_rule_config_provider
    from colony_manager.adapters.persistence.db import init_db

    db_path = tmp_path / "test.db"
    init_db(db_path)

    # Initialize rule config provider singleton for tests
    init_rule_config_provider()

    app = create_app()

    def override_get_db_path() -> Path:
        return db_path

    app.dependency_overrides[deps.get_db_path] = override_get_db_path

    client = TestClient(app)
    yield client

    app.dependency_overrides.clear()
