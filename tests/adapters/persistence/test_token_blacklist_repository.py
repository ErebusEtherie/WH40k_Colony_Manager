"""Tests for TokenBlacklistRepository - token revocation tracking."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from colony_manager.adapters.persistence.db import init_db
from colony_manager.adapters.persistence.repositories.token_blacklist_repository_impl import (
    SqlAlchemyTokenBlacklistRepository,
)
from colony_manager.domain.models.token_blacklist import TokenBlacklist


def _create_db_url(tmp_path: Path) -> str:
    """Helper to create and initialize a test database."""
    db_path = tmp_path / "test.db"
    init_db(db_path)
    return f"sqlite:///{db_path.as_posix()}"


class TestTokenBlacklistCreate:
    """Tests for token blacklist creation."""

    def test_create_blacklist_entry(self, tmp_path):
        """Test adding a token to the blacklist."""
        db_url = _create_db_url(tmp_path)
        repo = SqlAlchemyTokenBlacklistRepository(db_url)

        now = datetime.now(UTC)
        entry = TokenBlacklist(
            token_id="test-token-jti-123",
            user_id=1,
            expires_at=now + timedelta(hours=1),
            revoked_at=now,
            reason="logout",
        )

        created = repo.create(entry)

        assert created.id is not None
        assert created.token_id == "test-token-jti-123"
        assert created.user_id == 1
        assert created.reason == "logout"

    def test_create_entry_without_reason(self, tmp_path):
        """Test adding blacklist entry without reason."""
        db_url = _create_db_url(tmp_path)
        repo = SqlAlchemyTokenBlacklistRepository(db_url)

        now = datetime.now(UTC)
        entry = TokenBlacklist(
            token_id="test-token-456",
            user_id=2,
            expires_at=now + timedelta(hours=1),
            revoked_at=now,
        )

        created = repo.create(entry)

        assert created.id is not None
        assert created.reason is None


class TestTokenBlacklistIsBlacklisted:
    """Tests for checking if token is blacklisted."""

    def test_token_is_blacklisted(self, tmp_path):
        """Test blacklisted token returns True."""
        db_url = _create_db_url(tmp_path)
        repo = SqlAlchemyTokenBlacklistRepository(db_url)

        now = datetime.now(UTC)
        entry = TokenBlacklist(
            token_id="blacklisted-token",
            user_id=1,
            expires_at=now + timedelta(hours=1),
            revoked_at=now,
        )
        repo.create(entry)

        assert repo.is_blacklisted("blacklisted-token") is True

    def test_token_not_blacklisted(self, tmp_path):
        """Test non-blacklisted token returns False."""
        db_url = _create_db_url(tmp_path)
        repo = SqlAlchemyTokenBlacklistRepository(db_url)

        assert repo.is_blacklisted("non-existent-token") is False

    def test_expired_token_not_blacklisted(self, tmp_path):
        """Test expired blacklist entry returns False."""
        db_url = _create_db_url(tmp_path)
        repo = SqlAlchemyTokenBlacklistRepository(db_url)

        now = datetime.now(UTC)
        entry = TokenBlacklist(
            token_id="expired-token",
            user_id=1,
            expires_at=now - timedelta(days=1),  # Already expired
            revoked_at=now - timedelta(days=2),
        )
        repo.create(entry)

        # Token is expired, so not considered blacklisted
        assert repo.is_blacklisted("expired-token") is False


class TestTokenBlacklistRevokeAll:
    """Tests for bulk token revocation."""

    def test_revoke_all_user_tokens(self, tmp_path):
        """Test revoking all tokens for a user."""
        db_url = _create_db_url(tmp_path)
        repo = SqlAlchemyTokenBlacklistRepository(db_url)

        # Create token issuance table and add some tokens
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from colony_manager.adapters.persistence.orm_models import TokenIssuanceORM

        engine = create_engine(db_url)
        session_factory = sessionmaker(bind=engine)

        now = datetime.now(UTC)
        with session_factory() as session:
            # Add 3 active tokens for user 1
            for i in range(3):
                token = TokenIssuanceORM(
                    user_id=1,
                    token_id=f"token-{i}",
                    token_type="access",
                    issued_at=now,
                    expires_at=now + timedelta(hours=1),
                )
                session.add(token)

            # Add 1 expired token
            expired = TokenIssuanceORM(
                user_id=1,
                token_id="expired-token",
                token_type="access",
                issued_at=now - timedelta(days=2),
                expires_at=now - timedelta(days=1),
            )
            session.add(expired)

            # Add 1 already revoked token
            revoked = TokenIssuanceORM(
                user_id=1,
                token_id="revoked-token",
                token_type="access",
                issued_at=now - timedelta(hours=1),
                expires_at=now + timedelta(hours=1),
                revoked_at=now - timedelta(minutes=30),
            )
            session.add(revoked)

            # Add tokens for different user
            other_user = TokenIssuanceORM(
                user_id=2,
                token_id="other-user-token",
                token_type="access",
                issued_at=now,
                expires_at=now + timedelta(hours=1),
            )
            session.add(other_user)

            session.commit()

        # Revoke all tokens for user 1
        count = repo.revoke_all_user_tokens(user_id=1, reason="password_change")

        # Should only revoke the 3 active tokens
        assert count == 3

        # Verify tokens are blacklisted
        assert repo.is_blacklisted("token-0") is True
        assert repo.is_blacklisted("token-1") is True
        assert repo.is_blacklisted("token-2") is True
        assert repo.is_blacklisted("expired-token") is False  # Was already expired
        assert repo.is_blacklisted("revoked-token") is False  # Was already revoked
        assert repo.is_blacklisted("other-user-token") is False  # Different user

    def test_revoke_all_tokens_no_active_tokens(self, tmp_path):
        """Test revoking when user has no active tokens."""
        db_url = _create_db_url(tmp_path)
        repo = SqlAlchemyTokenBlacklistRepository(db_url)

        count = repo.revoke_all_user_tokens(user_id=999, reason="test")

        assert count == 0


class TestTokenBlacklistGet:
    """Tests for fetching a blacklist entry by token id."""

    def test_get_existing_token(self, tmp_path):
        """Test retrieving an existing non-expired blacklist entry."""
        db_url = _create_db_url(tmp_path)
        repo = SqlAlchemyTokenBlacklistRepository(db_url)

        now = datetime.now(UTC)
        entry = TokenBlacklist(
            token_id="get-existing",
            user_id=1,
            expires_at=now + timedelta(hours=1),
            revoked_at=now,
            reason="rotation",
        )
        repo.create(entry)

        found = repo.get("get-existing")

        assert found is not None
        assert found.token_id == "get-existing"
        assert found.user_id == 1
        assert found.reason == "rotation"

    def test_get_nonexistent_token(self, tmp_path):
        """Test retrieving a token with no blacklist entry returns None."""
        db_url = _create_db_url(tmp_path)
        repo = SqlAlchemyTokenBlacklistRepository(db_url)

        assert repo.get("no-such-token") is None

    def test_get_expired_token_returns_none(self, tmp_path):
        """Test retrieving an expired blacklist entry returns None.

        Mirrors ``is_blacklisted``: an expired entry no longer counts as a
        live revocation, so it must not be reported as one.
        """
        db_url = _create_db_url(tmp_path)
        repo = SqlAlchemyTokenBlacklistRepository(db_url)

        now = datetime.now(UTC)
        entry = TokenBlacklist(
            token_id="get-expired",
            user_id=1,
            expires_at=now - timedelta(days=1),
            revoked_at=now - timedelta(days=2),
            reason="rotation",
        )
        repo.create(entry)

        assert repo.get("get-expired") is None


class TestTokenBlacklistCleanup:
    """Tests for cleaning up expired blacklist entries."""

    def test_cleanup_expired_entries(self, tmp_path):
        """Test removing expired blacklist entries."""
        db_url = _create_db_url(tmp_path)
        repo = SqlAlchemyTokenBlacklistRepository(db_url)

        now = datetime.now(UTC)

        # Add expired entry
        expired = TokenBlacklist(
            token_id="expired-1",
            user_id=1,
            expires_at=now - timedelta(days=2),
            revoked_at=now - timedelta(days=3),
        )
        repo.create(expired)

        # Add another expired entry
        expired2 = TokenBlacklist(
            token_id="expired-2",
            user_id=1,
            expires_at=now - timedelta(days=1),
            revoked_at=now - timedelta(days=2),
        )
        repo.create(expired2)

        # Add valid (non-expired) entry
        valid = TokenBlacklist(
            token_id="valid-1",
            user_id=1,
            expires_at=now + timedelta(days=1),
            revoked_at=now,
        )
        repo.create(valid)

        # Cleanup entries expired before now
        removed = repo.cleanup_expired(before=now)

        assert removed == 2

        # Verify expired entries are removed
        assert repo.is_blacklisted("expired-1") is False
        assert repo.is_blacklisted("expired-2") is False

        # Verify valid entry still exists
        assert repo.is_blacklisted("valid-1") is True

    def test_cleanup_no_expired_entries(self, tmp_path):
        """Test cleanup when no expired entries exist."""
        db_url = _create_db_url(tmp_path)
        repo = SqlAlchemyTokenBlacklistRepository(db_url)

        now = datetime.now(UTC)

        # Add only valid entries
        valid = TokenBlacklist(
            token_id="valid-1",
            user_id=1,
            expires_at=now + timedelta(days=1),
            revoked_at=now,
        )
        repo.create(valid)

        removed = repo.cleanup_expired(before=now)

        assert removed == 0
        assert repo.is_blacklisted("valid-1") is True

    def test_cleanup_default_before_time(self, tmp_path):
        """Test cleanup uses current time by default."""
        db_url = _create_db_url(tmp_path)
        repo = SqlAlchemyTokenBlacklistRepository(db_url)

        now = datetime.now(UTC)

        # Add entry that expired 2 days ago
        expired = TokenBlacklist(
            token_id="old-expired",
            user_id=1,
            expires_at=now - timedelta(days=2),
            revoked_at=now - timedelta(days=3),
        )
        repo.create(expired)

        # Cleanup without specifying before time (should use now)
        removed = repo.cleanup_expired()

        assert removed == 1
