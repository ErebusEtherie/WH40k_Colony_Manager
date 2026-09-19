"""Tests for LoginAttemptRepository - login attempt tracking."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from colony_manager.adapters.persistence.db import init_db
from colony_manager.adapters.persistence.repositories.login_attempt_repository_impl import (
    SqlAlchemyLoginAttemptRepository,
)
from colony_manager.domain.models.login_attempt import LoginAttempt


def _create_db_url(tmp_path: Path) -> str:
    """Helper to create and initialize a test database."""
    db_path = tmp_path / "test.db"
    init_db(db_path)
    return f"sqlite:///{db_path.as_posix()}"


class TestLoginAttemptCreate:
    """Tests for login attempt creation."""

    def test_create_failed_attempt(self, tmp_path):
        """Test recording a failed login attempt."""
        db_url = _create_db_url(tmp_path)
        repo = SqlAlchemyLoginAttemptRepository(db_url)

        now = datetime.now(UTC)
        attempt = LoginAttempt(
            username="testuser",
            ip_address="192.168.1.1",
            attempted_at=now,
            success=False,
            user_agent="Mozilla/5.0",
        )

        created = repo.create(attempt)

        assert created.id is not None
        assert created.username == "testuser"
        assert created.ip_address == "192.168.1.1"
        assert created.success is False

    def test_create_successful_attempt(self, tmp_path):
        """Test recording a successful login attempt."""
        db_url = _create_db_url(tmp_path)
        repo = SqlAlchemyLoginAttemptRepository(db_url)

        now = datetime.now(UTC)
        attempt = LoginAttempt(
            username="testuser",
            ip_address="192.168.1.1",
            attempted_at=now,
            success=True,
        )

        created = repo.create(attempt)

        assert created.id is not None
        assert created.success is True

    def test_create_without_optional_fields(self, tmp_path):
        """Test creating attempt without optional fields."""
        db_url = _create_db_url(tmp_path)
        repo = SqlAlchemyLoginAttemptRepository(db_url)

        now = datetime.now(UTC)
        attempt = LoginAttempt(
            username="minimaluser",
            attempted_at=now,
            success=False,
        )

        created = repo.create(attempt)

        assert created.id is not None
        assert created.ip_address is None
        assert created.user_agent is None


class TestLoginAttemptCountFailed:
    """Tests for counting failed login attempts."""

    def test_count_failed_attempts(self, tmp_path):
        """Test counting failed attempts for a username."""
        db_url = _create_db_url(tmp_path)
        repo = SqlAlchemyLoginAttemptRepository(db_url)

        now = datetime.now(UTC)
        since = now - timedelta(hours=1)

        # Create 3 failed attempts
        for i in range(3):
            repo.create(
                LoginAttempt(
                    username="lockuser",
                    ip_address="192.168.1.1",
                    attempted_at=now - timedelta(minutes=i * 5),
                    success=False,
                )
            )

        # Create 1 successful attempt
        repo.create(
            LoginAttempt(
                username="lockuser",
                ip_address="192.168.1.1",
                attempted_at=now,
                success=True,
            )
        )

        count = repo.count_failed_attempts("lockuser", since=since)

        assert count == 3

    def test_count_failed_attempts_with_ip_filter(self, tmp_path):
        """Test counting failed attempts filtered by IP."""
        db_url = _create_db_url(tmp_path)
        repo = SqlAlchemyLoginAttemptRepository(db_url)

        now = datetime.now(UTC)
        since = now - timedelta(hours=1)

        # Create 2 failed attempts from IP1
        for i in range(2):
            repo.create(
                LoginAttempt(
                    username="user1",
                    ip_address="192.168.1.1",
                    attempted_at=now - timedelta(minutes=i * 5),
                    success=False,
                )
            )

        # Create 3 failed attempts from IP2
        for i in range(3):
            repo.create(
                LoginAttempt(
                    username="user1",
                    ip_address="192.168.1.2",
                    attempted_at=now - timedelta(minutes=i * 5),
                    success=False,
                )
            )

        # Count only from IP1
        count = repo.count_failed_attempts("user1", since=since, ip_address="192.168.1.1")

        assert count == 2

    def test_count_failed_attempts_time_window(self, tmp_path):
        """Test counting only attempts within time window."""
        db_url = _create_db_url(tmp_path)
        repo = SqlAlchemyLoginAttemptRepository(db_url)

        now = datetime.now(UTC)
        since = now - timedelta(minutes=30)

        # Create 2 old failed attempts (outside window)
        for i in range(2):
            repo.create(
                LoginAttempt(
                    username="timeuser",
                    attempted_at=now - timedelta(hours=i + 1),
                    success=False,
                )
            )

        # Create 3 recent failed attempts (inside window)
        for i in range(3):
            repo.create(
                LoginAttempt(
                    username="timeuser",
                    attempted_at=now - timedelta(minutes=i * 5),
                    success=False,
                )
            )

        count = repo.count_failed_attempts("timeuser", since=since)

        assert count == 3

    def test_count_failed_attempts_zero(self, tmp_path):
        """Test counting when no failed attempts exist."""
        db_url = _create_db_url(tmp_path)
        repo = SqlAlchemyLoginAttemptRepository(db_url)

        now = datetime.now(UTC)
        since = now - timedelta(hours=1)

        count = repo.count_failed_attempts("nonexistent", since=since)

        assert count == 0

    def test_count_failed_attempts_only_success(self, tmp_path):
        """Test counting when only successful attempts exist."""
        db_url = _create_db_url(tmp_path)
        repo = SqlAlchemyLoginAttemptRepository(db_url)

        now = datetime.now(UTC)
        since = now - timedelta(hours=1)

        # Create only successful attempts
        for i in range(3):
            repo.create(
                LoginAttempt(
                    username="successuser",
                    attempted_at=now - timedelta(minutes=i * 5),
                    success=True,
                )
            )

        count = repo.count_failed_attempts("successuser", since=since)

        assert count == 0


class TestLoginAttemptCleanup:
    """Tests for cleaning up old login attempts."""

    def test_cleanup_old_attempts(self, tmp_path):
        """Test removing old login attempt records."""
        db_url = _create_db_url(tmp_path)
        repo = SqlAlchemyLoginAttemptRepository(db_url)

        now = datetime.now(UTC)

        # Create 3 old attempts (60 days ago)
        for _i in range(3):
            repo.create(
                LoginAttempt(
                    username="olduser",
                    ip_address="192.168.1.1",
                    attempted_at=now - timedelta(days=60),
                    success=False,
                )
            )

        # Create 2 recent attempts (5 days ago)
        for _i in range(2):
            repo.create(
                LoginAttempt(
                    username="newuser",
                    ip_address="192.168.1.2",
                    attempted_at=now - timedelta(days=5),
                    success=False,
                )
            )

        # Cleanup attempts older than 30 days
        cutoff = now - timedelta(days=30)
        removed = repo.cleanup_old_attempts(before=cutoff)

        assert removed == 3

        # Verify old attempts are removed (count would be 0 since all old are gone)
        count = repo.count_failed_attempts("olduser", since=now - timedelta(days=90))
        assert count == 0

        # Verify recent attempts still exist
        count = repo.count_failed_attempts("newuser", since=now - timedelta(days=10))
        assert count == 2

    def test_cleanup_no_old_attempts(self, tmp_path):
        """Test cleanup when no old attempts exist."""
        db_url = _create_db_url(tmp_path)
        repo = SqlAlchemyLoginAttemptRepository(db_url)

        now = datetime.now(UTC)

        # Create only recent attempts
        for i in range(3):
            repo.create(
                LoginAttempt(
                    username="recentuser",
                    attempted_at=now - timedelta(hours=i),
                    success=False,
                )
            )

        cutoff = now - timedelta(days=1)
        removed = repo.cleanup_old_attempts(before=cutoff)

        assert removed == 0

        # Verify all attempts still exist
        count = repo.count_failed_attempts("recentuser", since=now - timedelta(days=1))
        assert count == 3

    def test_cleanup_mixed_success_failure(self, tmp_path):
        """Test cleanup removes both successful and failed attempts."""
        db_url = _create_db_url(tmp_path)
        repo = SqlAlchemyLoginAttemptRepository(db_url)

        now = datetime.now(UTC)

        # Create old failed attempt
        repo.create(
            LoginAttempt(
                username="mixeduser",
                attempted_at=now - timedelta(days=60),
                success=False,
            )
        )

        # Create old successful attempt
        repo.create(
            LoginAttempt(
                username="mixeduser",
                attempted_at=now - timedelta(days=60),
                success=True,
            )
        )

        cutoff = now - timedelta(days=30)
        removed = repo.cleanup_old_attempts(before=cutoff)

        assert removed == 2
