"""Tests for login attempt tracking and account lockout."""

from fastapi.testclient import TestClient


class TestLoginAttemptTracking:
    """Test login attempt tracking functionality."""

    def test_successful_login_is_logged(self, test_client_with_auth: TestClient):
        """Test that successful logins are logged."""
        # Register a user
        register_data = {
            "username": "logintestuser",
            "email": "logintest@example.com",
            "password": "TestPassword123!",
        }
        response = test_client_with_auth.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == 201

        # Login
        login_data = {
            "username": "logintestuser",
            "password": "TestPassword123!",
        }
        response = test_client_with_auth.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        # Tokens are delivered only via HttpOnly cookies, never in the body
        assert "access_token" not in response.json()
        assert "rt_access_token" in test_client_with_auth.cookies

    def test_failed_login_is_logged(self, test_client_with_auth: TestClient):
        """Test that failed login attempts are logged."""
        # Try to login with wrong password
        login_data = {
            "username": "nonexistentuser",
            "password": "wrongpassword",
        }
        response = test_client_with_auth.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 401

    def test_account_lockout_after_failed_attempts(self, test_client_with_auth: TestClient):
        """Test account lockout after 5 failed attempts."""
        # Register a user
        register_data = {
            "username": "lockouttestuser",
            "email": "lockouttest@example.com",
            "password": "TestPassword123!",
        }
        response = test_client_with_auth.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == 201

        # Make 5 failed login attempts
        for _i in range(5):
            login_data = {
                "username": "lockouttestuser",
                "password": "wrongpassword",
            }
            response = test_client_with_auth.post("/api/v1/auth/login", json=login_data)
            assert response.status_code == 401

        # 6th attempt should be locked
        login_data = {
            "username": "lockouttestuser",
            "password": "wrongpassword",
        }
        response = test_client_with_auth.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 423  # Locked
        assert "locked" in response.json()["detail"].lower()

    def test_correct_password_after_lockout_still_fails(self, test_client_with_auth: TestClient):
        """Test that even correct password fails when account is locked."""
        # Register a user
        register_data = {
            "username": "lockedcorrectuser",
            "email": "lockedcorrect@example.com",
            "password": "TestPassword123!",
        }
        response = test_client_with_auth.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == 201

        # Make 5 failed login attempts
        for _i in range(5):
            login_data = {
                "username": "lockedcorrectuser",
                "password": "wrongpassword",
            }
            response = test_client_with_auth.post("/api/v1/auth/login", json=login_data)
            assert response.status_code == 401

        # Try with correct password - should still fail due to lockout
        login_data = {
            "username": "lockedcorrectuser",
            "password": "TestPassword123!",
        }
        response = test_client_with_auth.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 423  # Locked
