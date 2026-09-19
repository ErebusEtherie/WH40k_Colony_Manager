"""Tests for AuthService - authentication and token management."""

from datetime import UTC, datetime, timedelta

import pytest
from freezegun import freeze_time

from colony_manager.adapters.persistence.db import init_db
from colony_manager.adapters.persistence.repositories.login_attempt_repository_impl import (
    SqlAlchemyLoginAttemptRepository,
)
from colony_manager.adapters.persistence.repositories.token_blacklist_repository_impl import (
    SqlAlchemyTokenBlacklistRepository,
)
from colony_manager.adapters.persistence.repositories.token_issuance_repository_impl import (
    SqlAlchemyTokenIssuanceRepository,
)
from colony_manager.adapters.persistence.user_repository_impl import SqlAlchemyUserRepository
from colony_manager.application.services.auth_service import (
    LOCKOUT_MAX_ATTEMPTS,
    LOCKOUT_WINDOW_MINUTES,
    AuthService,
)
from colony_manager.domain.models.login_attempt import LoginAttempt
from colony_manager.domain.models.token_blacklist import TokenBlacklist
from colony_manager.domain.models.token_issuance import TokenIssuance
from colony_manager.domain.models.user import User, UserRole
from colony_manager.domain.util.auth import hash_password
from colony_manager.domain.util.token import create_access_token, create_refresh_token


def _create_db_url(tmp_path):
    """Helper to create and initialize a test database."""
    db_path = tmp_path / "test.db"
    init_db(db_path)
    return f"sqlite:///{db_path.as_posix()}"


def _create_user(user_repo, username="testuser", email="test@example.com", is_active=True):
    """Helper to create a test user."""
    user = User(
        username=username,
        email=email,
        password_hash=hash_password("SecurePass123!"),
        role=UserRole.COLONY_MANAGER,
        is_active=is_active,
    )
    return user_repo.create(user)


class TestAuthTokenRevocation:
    """Tests for token revocation functionality."""

    def test_revoke_token_success(self, tmp_path):
        """Test successful token revocation."""
        db_url = _create_db_url(tmp_path)
        user_repo = SqlAlchemyUserRepository(db_url)
        blacklist_repo = SqlAlchemyTokenBlacklistRepository(db_url)
        auth_service = AuthService(
            token_blacklist_repository=blacklist_repo,
            user_repository=user_repo,
        )

        user = _create_user(user_repo)
        token = create_access_token(user, secret_key="test-secret-key-for-testing-minimum-32-bytes")

        result = auth_service.revoke_token(
            token, secret_key="test-secret-key-for-testing-minimum-32-bytes", reason="logout"
        )

        assert result is not None
        assert result.token_id is not None
        assert result.user_id == user.id
        assert result.reason == "logout"

    def test_revoke_invalid_token(self, tmp_path):
        """Test revoking invalid token raises error."""
        db_url = _create_db_url(tmp_path)
        user_repo = SqlAlchemyUserRepository(db_url)
        blacklist_repo = SqlAlchemyTokenBlacklistRepository(db_url)
        auth_service = AuthService(
            token_blacklist_repository=blacklist_repo,
            user_repository=user_repo,
        )

        with pytest.raises(ValueError, match="(?i)invalid"):
            auth_service.revoke_token(
                "invalid-token", secret_key="test-secret-key-for-testing-minimum-32-bytes"
            )


class TestRefreshTokenRevocation:
    """Tests for refresh-token revocation (rotation + logout)."""

    def test_revoke_refresh_token_blacklists_it(self, tmp_path):
        """Test that revoking a refresh token adds it to the blacklist."""
        db_url = _create_db_url(tmp_path)
        user_repo = SqlAlchemyUserRepository(db_url)
        blacklist_repo = SqlAlchemyTokenBlacklistRepository(db_url)
        auth_service = AuthService(
            token_blacklist_repository=blacklist_repo,
            user_repository=user_repo,
        )
        secret_key = "test-secret-key-for-testing-minimum-32-bytes"

        user = _create_user(user_repo, username="rotate_user")
        token = create_refresh_token(user, secret_key=secret_key)

        result = auth_service.revoke_refresh_token(token, secret_key, reason="rotation")

        assert result is not None
        assert result.user_id == user.id
        assert result.reason == "rotation"

        import jwt

        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        assert blacklist_repo.is_blacklisted(payload["jti"]) is True

    def test_revoke_refresh_token_marks_issuance_revoked(self, tmp_path):
        """Test that revoking a refresh token marks its issuance record revoked."""
        db_url = _create_db_url(tmp_path)
        user_repo = SqlAlchemyUserRepository(db_url)
        blacklist_repo = SqlAlchemyTokenBlacklistRepository(db_url)
        issuance_repo = SqlAlchemyTokenIssuanceRepository(db_url)
        auth_service = AuthService(
            token_blacklist_repository=blacklist_repo,
            user_repository=user_repo,
            token_issuance_repository=issuance_repo,
        )
        secret_key = "test-secret-key-for-testing-minimum-32-bytes"

        user = _create_user(user_repo, username="rotate_tracked")
        assert user.id is not None
        token = create_refresh_token(user, secret_key=secret_key)

        import jwt

        token_id = jwt.decode(token, secret_key, algorithms=["HS256"])["jti"]
        issuance_repo.create(
            TokenIssuance(
                user_id=user.id,
                token_id=token_id,
                token_type="refresh",
                issued_at=datetime.now(UTC),
                expires_at=datetime.now(UTC) + timedelta(days=7),
                revoked_at=None,
            )
        )

        auth_service.revoke_refresh_token(token, secret_key, reason="rotation")

        active = issuance_repo.get_active_tokens(user.id)
        assert all(t.token_id != token_id for t in active)

    def test_revoke_invalid_refresh_token(self, tmp_path):
        """Test that revoking an invalid refresh token raises an error."""
        db_url = _create_db_url(tmp_path)
        user_repo = SqlAlchemyUserRepository(db_url)
        blacklist_repo = SqlAlchemyTokenBlacklistRepository(db_url)
        auth_service = AuthService(
            token_blacklist_repository=blacklist_repo,
            user_repository=user_repo,
        )

        with pytest.raises(ValueError, match="(?i)invalid"):
            auth_service.revoke_refresh_token(
                "invalid-token", secret_key="test-secret-key-for-testing-minimum-32-bytes"
            )


class TestBulkTokenRevocation:
    """Tests for bulk token revocation."""

    def test_revoke_all_user_tokens(self, tmp_path):
        """Test revoking all tokens for a user."""
        db_url = _create_db_url(tmp_path)
        user_repo = SqlAlchemyUserRepository(db_url)
        blacklist_repo = SqlAlchemyTokenBlacklistRepository(db_url)
        issuance_repo = SqlAlchemyTokenIssuanceRepository(db_url)
        auth_service = AuthService(
            token_blacklist_repository=blacklist_repo,
            user_repository=user_repo,
            token_issuance_repository=issuance_repo,
        )

        user = _create_user(user_repo, username="bulkuser")

        assert user.id is not None

        # Create some token issuances
        for i in range(3):
            issuance_repo.create(
                TokenIssuance(
                    user_id=user.id,
                    token_id=f"token-{i}",
                    token_type="access",
                    issued_at=datetime.now(UTC),
                    expires_at=datetime.now(UTC) + timedelta(hours=1),
                    revoked_at=None,
                    ip_address="192.168.1.1",
                    user_agent="TestAgent/1.0",
                )
            )

        assert user.id is not None
        revoked_count = auth_service.revoke_all_user_tokens(user.id, reason="password_change")

        assert revoked_count >= 3

    def test_revoke_all_tokens_nonexistent_user(self, tmp_path):
        """Test revoking tokens for non-existent user returns 0."""
        db_url = _create_db_url(tmp_path)
        blacklist_repo = SqlAlchemyTokenBlacklistRepository(db_url)
        auth_service = AuthService(
            token_blacklist_repository=blacklist_repo,
            user_repository=SqlAlchemyUserRepository(db_url),
        )

        count = auth_service.revoke_all_user_tokens(99999, reason="test")
        assert count == 0


class TestRefreshReuseDetection:
    """Tests for refresh-token reuse detection (family revocation on rotation replay).

    When enabled, replaying a refresh token that was already consumed by rotation
    is treated as a theft/replay and revokes the user's whole session family.
    Reasons other than rotation (logout / admin / password change) are
    intentional revocations and must never escalate into revoking other sessions.
    """

    def test_rotation_replay_revokes_whole_family(self, tmp_path):
        """A rotated-then-replayed refresh token revokes the entire family."""
        db_url = _create_db_url(tmp_path)
        user_repo = SqlAlchemyUserRepository(db_url)
        blacklist_repo = SqlAlchemyTokenBlacklistRepository(db_url)
        issuance_repo = SqlAlchemyTokenIssuanceRepository(db_url)
        auth_service = AuthService(
            token_blacklist_repository=blacklist_repo,
            user_repository=user_repo,
            token_issuance_repository=issuance_repo,
            refresh_reuse_detection_enabled=True,
        )
        secret_key = "test-secret-key-for-testing-minimum-32-bytes"

        user = _create_user(user_repo, username="reuse_user")
        assert user.id is not None

        # Three other live refresh sessions for the same user.
        for i in range(3):
            issuance_repo.create(
                TokenIssuance(
                    user_id=user.id,
                    token_id=f"live-refresh-{i}",
                    token_type="refresh",
                    issued_at=datetime.now(UTC),
                    expires_at=datetime.now(UTC) + timedelta(days=1),
                    revoked_at=None,
                    ip_address="192.168.1.1",
                    user_agent="TestAgent/1.0",
                )
            )

        # A refresh token that was already consumed by rotation (the replay).
        stolen = create_refresh_token(user, secret_key=secret_key)
        auth_service.revoke_refresh_token(stolen, secret_key, reason="rotation")
        import jwt

        stolen_jti = jwt.decode(stolen, secret_key, algorithms=["HS256"])["jti"]

        # The replay is rejected AND the whole family is revoked.
        assert auth_service.refresh_token_is_usable(stolen_jti, user.id) is False
        for i in range(3):
            assert blacklist_repo.is_blacklisted(f"live-refresh-{i}") is True
        assert blacklist_repo.is_blacklisted(stolen_jti) is True

    def test_logout_entry_rejected_without_family_revoke(self, tmp_path):
        """An owner-revoked token (logout) is rejected without escalating."""
        db_url = _create_db_url(tmp_path)
        user_repo = SqlAlchemyUserRepository(db_url)
        blacklist_repo = SqlAlchemyTokenBlacklistRepository(db_url)
        issuance_repo = SqlAlchemyTokenIssuanceRepository(db_url)
        auth_service = AuthService(
            token_blacklist_repository=blacklist_repo,
            user_repository=user_repo,
            token_issuance_repository=issuance_repo,
            refresh_reuse_detection_enabled=True,
        )
        secret_key = "test-secret-key-for-testing-minimum-32-bytes"

        user = _create_user(user_repo, username="logout_reuse_user")
        assert user.id is not None

        issuance_repo.create(
            TokenIssuance(
                user_id=user.id,
                token_id="live-refresh-0",
                token_type="refresh",
                issued_at=datetime.now(UTC),
                expires_at=datetime.now(UTC) + timedelta(days=1),
                revoked_at=None,
                ip_address="192.168.1.1",
                user_agent="TestAgent/1.0",
            )
        )

        revoked = create_refresh_token(user, secret_key=secret_key)
        auth_service.revoke_refresh_token(revoked, secret_key, reason="logout")
        import jwt

        revoked_jti = jwt.decode(revoked, secret_key, algorithms=["HS256"])["jti"]

        assert auth_service.refresh_token_is_usable(revoked_jti, user.id) is False
        # Logout is intentional: the family must survive.
        assert blacklist_repo.is_blacklisted("live-refresh-0") is False

    def test_non_blacklisted_token_is_usable(self, tmp_path):
        """A token with no blacklist entry remains usable."""
        db_url = _create_db_url(tmp_path)
        user_repo = SqlAlchemyUserRepository(db_url)
        blacklist_repo = SqlAlchemyTokenBlacklistRepository(db_url)
        auth_service = AuthService(
            token_blacklist_repository=blacklist_repo,
            user_repository=user_repo,
            refresh_reuse_detection_enabled=True,
        )
        secret_key = "test-secret-key-for-testing-minimum-32-bytes"

        user = _create_user(user_repo, username="fresh_refresh_user")
        token = create_refresh_token(user, secret_key=secret_key)
        import jwt

        token_jti = jwt.decode(token, secret_key, algorithms=["HS256"])["jti"]

        assert auth_service.refresh_token_is_usable(token_jti, user.id) is True

    def test_disabled_detection_does_not_revoke_family(self, tmp_path):
        """With the flag off, a replayed rotated token is rejected but the family survives."""
        db_url = _create_db_url(tmp_path)
        user_repo = SqlAlchemyUserRepository(db_url)
        blacklist_repo = SqlAlchemyTokenBlacklistRepository(db_url)
        issuance_repo = SqlAlchemyTokenIssuanceRepository(db_url)
        auth_service = AuthService(
            token_blacklist_repository=blacklist_repo,
            user_repository=user_repo,
            token_issuance_repository=issuance_repo,
            refresh_reuse_detection_enabled=False,
        )
        secret_key = "test-secret-key-for-testing-minimum-32-bytes"

        user = _create_user(user_repo, username="legacy_reuse_user")
        assert user.id is not None

        issuance_repo.create(
            TokenIssuance(
                user_id=user.id,
                token_id="live-refresh-0",
                token_type="refresh",
                issued_at=datetime.now(UTC),
                expires_at=datetime.now(UTC) + timedelta(days=1),
                revoked_at=None,
                ip_address="192.168.1.1",
                user_agent="TestAgent/1.0",
            )
        )

        stolen = create_refresh_token(user, secret_key=secret_key)
        auth_service.revoke_refresh_token(stolen, secret_key, reason="rotation")
        import jwt

        stolen_jti = jwt.decode(stolen, secret_key, algorithms=["HS256"])["jti"]

        # Rejected (still revoked), but no family escalation.
        assert auth_service.refresh_token_is_usable(stolen_jti, user.id) is False
        assert blacklist_repo.is_blacklisted("live-refresh-0") is False


class TestAccountLockout:
    """Tests for account lockout functionality."""

    def test_account_locks_after_max_attempts(self, tmp_path):
        """Test account locks after maximum failed attempts."""
        db_url = _create_db_url(tmp_path)
        user_repo = SqlAlchemyUserRepository(db_url)
        blacklist_repo = SqlAlchemyTokenBlacklistRepository(db_url)
        login_repo = SqlAlchemyLoginAttemptRepository(db_url)
        auth_service = AuthService(
            token_blacklist_repository=blacklist_repo,
            user_repository=user_repo,
            login_attempt_repository=login_repo,
        )

        for _i in range(LOCKOUT_MAX_ATTEMPTS):
            auth_service.track_login_attempt(
                "lockuser", success=False, ip_address="192.168.1.1", user_agent="TestAgent/1.0"
            )

        assert auth_service.is_account_locked("lockuser") is True

    def test_account_not_locked_below_max_attempts(self, tmp_path):
        """Test account not locked below max attempts."""
        db_url = _create_db_url(tmp_path)
        user_repo = SqlAlchemyUserRepository(db_url)
        blacklist_repo = SqlAlchemyTokenBlacklistRepository(db_url)
        login_repo = SqlAlchemyLoginAttemptRepository(db_url)
        auth_service = AuthService(
            token_blacklist_repository=blacklist_repo,
            user_repository=user_repo,
            login_attempt_repository=login_repo,
        )

        for _i in range(LOCKOUT_MAX_ATTEMPTS - 1):
            auth_service.track_login_attempt(
                "notlocked", success=False, ip_address="192.168.1.1", user_agent="TestAgent/1.0"
            )

        assert auth_service.is_account_locked("notlocked") is False

    def test_login_attempts_expire_after_window(self, tmp_path):
        """Test failed attempts expire after lockout window."""
        db_url = _create_db_url(tmp_path)
        user_repo = SqlAlchemyUserRepository(db_url)
        blacklist_repo = SqlAlchemyTokenBlacklistRepository(db_url)
        login_repo = SqlAlchemyLoginAttemptRepository(db_url)
        auth_service = AuthService(
            token_blacklist_repository=blacklist_repo,
            user_repository=user_repo,
            login_attempt_repository=login_repo,
        )

        with freeze_time(datetime.now(UTC) - timedelta(minutes=LOCKOUT_WINDOW_MINUTES + 5)):
            for _i in range(LOCKOUT_MAX_ATTEMPTS):
                auth_service.track_login_attempt(
                    "expireuser",
                    success=False,
                    ip_address="192.168.1.1",
                    user_agent="TestAgent/1.0",
                )

        assert auth_service.is_account_locked("expireuser") is False


class TestTokenCleanup:
    """Tests for token cleanup functionality."""

    def test_cleanup_expired_tokens(self, tmp_path):
        """Test cleanup of expired blacklist entries."""
        db_url = _create_db_url(tmp_path)
        blacklist_repo = SqlAlchemyTokenBlacklistRepository(db_url)
        auth_service = AuthService(
            token_blacklist_repository=blacklist_repo,
            user_repository=SqlAlchemyUserRepository(db_url),
        )

        expired_entry = TokenBlacklist(
            token_id="expired-token",
            user_id=1,
            expires_at=datetime.now(UTC) - timedelta(days=1),
            revoked_at=datetime.now(UTC) - timedelta(days=2),
            reason="test_expired",
        )
        blacklist_repo.create(expired_entry)

        valid_entry = TokenBlacklist(
            token_id="valid-token",
            user_id=1,
            expires_at=datetime.now(UTC) + timedelta(days=1),
            revoked_at=datetime.now(UTC),
            reason="test_valid",
        )
        blacklist_repo.create(valid_entry)

        removed = auth_service.cleanup_expired_tokens()

        assert removed == 1
        # Verify valid entry still exists by checking it's blacklisted
        assert blacklist_repo.is_blacklisted("valid-token") is True

    def test_cleanup_old_login_attempts(self, tmp_path):
        """Test cleanup of old login attempt records."""
        db_url = _create_db_url(tmp_path)
        login_repo = SqlAlchemyLoginAttemptRepository(db_url)
        auth_service = AuthService(
            token_blacklist_repository=SqlAlchemyTokenBlacklistRepository(db_url),
            user_repository=SqlAlchemyUserRepository(db_url),
            login_attempt_repository=login_repo,
        )

        old_attempt = LoginAttempt(
            username="olduser",
            ip_address="192.168.1.1",
            attempted_at=datetime.now(UTC) - timedelta(days=60),
            success=False,
            user_agent="TestAgent/1.0",
        )
        login_repo.create(old_attempt)

        recent_attempt = LoginAttempt(
            username="newuser",
            ip_address="192.168.1.2",
            attempted_at=datetime.now(UTC),
            success=True,
            user_agent="TestAgent/2.0",
        )
        login_repo.create(recent_attempt)

        removed = auth_service.cleanup_old_login_attempts(days_to_keep=30)

        assert removed == 1
