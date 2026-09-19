"""Tests for User domain model validators and properties."""

import pytest
from pydantic import ValidationError

from colony_manager.domain.models.user import User, UserRole


class TestUserValidators:
    """Tests for User model field validators."""

    def test_username_min_length_3(self):
        """Username must be at least 3 characters."""
        for length in [0, 1, 2]:
            with pytest.raises(ValidationError) as exc_info:
                User(
                    username="a" * length,
                    email="test@example.com",
                    password_hash="hash123",
                )
            assert "username" in str(exc_info.value)

    def test_username_max_length_50(self):
        """Username must be at most 50 characters."""
        with pytest.raises(ValidationError) as exc_info:
            User(
                username="a" * 51,
                email="test@example.com",
                password_hash="hash123",
            )
        assert "username" in str(exc_info.value)

    def test_username_valid_length(self):
        """Username with valid length (3-50) is accepted."""
        user = User(username="abc", email="test@example.com", password_hash="hash123")
        assert user.username == "abc"

        user = User(username="a" * 50, email="test@example.com", password_hash="hash123")
        assert user.username == "a" * 50

    def test_email_min_length_5(self):
        """Email must be at least 5 characters."""
        for length in [0, 1, 2, 3, 4]:
            with pytest.raises(ValidationError) as exc_info:
                User(
                    username="testuser",
                    email="a" * length,
                    password_hash="hash123",
                )
            assert "email" in str(exc_info.value)

    def test_email_max_length_100(self):
        """Email must be at most 100 characters."""
        with pytest.raises(ValidationError) as exc_info:
            User(
                username="testuser",
                email="a" * 101 + "@example.com",
                password_hash="hash123",
            )
        assert "email" in str(exc_info.value)

    def test_email_valid_length(self):
        """Email with valid length (5-100) is accepted."""
        user = User(username="testuser", email="a@b.co", password_hash="hash123")
        assert user.email == "a@b.co"

    def test_password_hash_min_length_1(self):
        """Password hash must be at least 1 character."""
        with pytest.raises(ValidationError) as exc_info:
            User(
                username="testuser",
                email="test@example.com",
                password_hash="",
            )
        assert "password_hash" in str(exc_info.value)


class TestUserDefaults:
    """Tests for User model default values."""

    def test_role_defaults_to_viewer(self):
        """User role defaults to VIEWER."""
        user = User(username="testuser", email="test@example.com", password_hash="hash123")
        assert user.role == UserRole.VIEWER

    def test_is_active_defaults_to_true(self):
        """User is_active defaults to True."""
        user = User(username="testuser", email="test@example.com", password_hash="hash123")
        assert user.is_active is True

    def test_created_at_defaults_to_none(self):
        """created_at defaults to None."""
        user = User(username="testuser", email="test@example.com", password_hash="hash123")
        assert user.created_at is None

    def test_updated_at_defaults_to_none(self):
        """updated_at defaults to None."""
        user = User(username="testuser", email="test@example.com", password_hash="hash123")
        assert user.updated_at is None

    def test_can_set_explicit_role(self):
        """User role can be explicitly set."""
        user = User(
            username="admin",
            email="admin@example.com",
            password_hash="hash123",
            role=UserRole.ADMIN,
        )
        assert user.role == UserRole.ADMIN

    def test_can_set_is_active_false(self):
        """User is_active can be set to False."""
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash="hash123",
            is_active=False,
        )
        assert user.is_active is False


class TestUserRoleHierarchy:
    """Example-based boundary tests for the system-role hierarchy.

    Per 04-testing-strategy.md, the role-ordering rule is high-risk and each
    boundary must be exercised explicitly: a viewer cannot do what
    colony_manager can, and colony_manager cannot do what admin can.
    """

    def test_viewer_does_not_meet_colony_manager(self):
        """A viewer cannot satisfy a colony_manager requirement."""
        assert not UserRole.VIEWER.meets_or_exceeds(UserRole.COLONY_MANAGER)

    def test_colony_manager_does_not_meet_admin(self):
        """A colony_manager cannot satisfy an admin requirement."""
        assert not UserRole.COLONY_MANAGER.meets_or_exceeds(UserRole.ADMIN)

    def test_admin_meets_admin(self):
        """A role always satisfies a requirement at its own level."""
        assert UserRole.ADMIN.meets_or_exceeds(UserRole.ADMIN)

    def test_colony_manager_meets_colony_manager(self):
        """colony_manager satisfies its own requirement."""
        assert UserRole.COLONY_MANAGER.meets_or_exceeds(UserRole.COLONY_MANAGER)

    def test_higher_role_meets_lower_requirement(self):
        """A higher role can do everything a lower role can — never less."""
        assert UserRole.ADMIN.meets_or_exceeds(UserRole.COLONY_MANAGER)
        assert UserRole.ADMIN.meets_or_exceeds(UserRole.VIEWER)
        assert UserRole.COLONY_MANAGER.meets_or_exceeds(UserRole.VIEWER)

    def test_levels_are_string_ordered(self):
        """viewer < colony_manager < admin by level."""
        levels = [UserRole.VIEWER, UserRole.COLONY_MANAGER, UserRole.ADMIN]
        assert [r.level for r in levels] == sorted(r.level for r in levels)
        assert levels[0].level < levels[1].level < levels[2].level

    def test_viewer_meets_viewer(self):
        """A viewer satisfies a viewer requirement."""
        assert UserRole.VIEWER.meets_or_exceeds(UserRole.VIEWER)
