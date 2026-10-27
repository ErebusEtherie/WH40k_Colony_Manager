#!/usr/bin/env python
"""Create the local demo/testing users in the real backend's SQLite database.

Development-only helper. The real backend seeds no users, and self-service
registration (``/auth/register``) is locked to the ``viewer`` role, so this
script creates the three demo accounts directly in SQLite, bypassing that
limitation:

    viewer        -> UserRole.VIEWER          (read-only login)
    rogue_trader  -> UserRole.COLONY_MANAGER  (charters and manages colonies)
    admin         -> UserRole.ADMIN           (full access, incl. user management)

The script is idempotent: usernames that already exist are left untouched, so
it is safe to re-run.

Usage (from the project root, with the backend stopped so SQLite is not locked):

    uv run python scripts/create_demo_users.py

The database file resolves the same way the backend does: the ``DATABASE_PATH``
environment variable wins if set, otherwise ``./colony_manager.sqlite``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from colony_manager.adapters.persistence.db import build_database_url, init_db
from colony_manager.adapters.persistence.user_repository_impl import (
    SqlAlchemyUserRepository,
)
from colony_manager.domain.models.user import User, UserRole
from colony_manager.domain.util.auth import hash_password

# Shared dev-only password for the demo accounts. Mirrors the bootstrap
# examples in README and tests/conftest.py, and satisfies the configured
# complexity requirements enforced by validate_password.
DEMO_PASSWORD = "TestP@ss123"

# (username, email, role) triples for the three demo users.
DEMO_USERS: tuple[tuple[str, str, UserRole], ...] = (
    ("viewer", "viewer@example.com", UserRole.VIEWER),
    ("rogue_trader", "rogue_trader@example.com", UserRole.COLONY_MANAGER),
    ("admin", "admin@example.com", UserRole.ADMIN),
)


def resolve_db_path() -> Path:
    """Resolve the SQLite database path the same way the backend does.

    Returns:
        ``DATABASE_PATH`` if set, otherwise ``./colony_manager.sqlite``.
    """
    configured = os.getenv("DATABASE_PATH")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path("colony_manager.sqlite").resolve()


def create_demo_users(repo: SqlAlchemyUserRepository) -> None:
    """Create the three demo users, skipping any that already exist.

    Args:
        repo: User repository bound to the target database.

    Raises:
        ValueError: If a demo user's email is taken by a different account.
    """
    for username, email, role in DEMO_USERS:
        if repo.get_by_username(username) is not None:
            print(f"[skip] '{username}' already exists")
            continue
        repo.create(
            User(
                username=username,
                email=email,
                password_hash=hash_password(DEMO_PASSWORD),
                role=role,
                is_active=True,
            )
        )
        print(f"[create] '{username}' ({role.value})")


def main() -> int:
    """Create the demo users and print a summary.

    Returns:
        Exit code 0 on success, 1 on failure.
    """
    try:
        db_path = resolve_db_path()
        init_db(db_path)
        repo = SqlAlchemyUserRepository(build_database_url(db_path))
        create_demo_users(repo)

        print()
        print(f"Demo users ensured in {db_path} (password: {DEMO_PASSWORD})")
        for username, _email, role in DEMO_USERS:
            print(f"  - {username:14s} role={role.value}")
        print("Restart the backend, then log in at http://localhost:3000.")
        return 0
    except Exception as exc:  # noqa: BLE001 - report any startup/db failure
        print(f"ERROR: Failed to create demo users: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
