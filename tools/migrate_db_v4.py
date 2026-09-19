"""Database migration script for Phase 4 changes.

This script migrates existing SQLite databases from Phase 3 schema to Phase 4:
- Removes: event_roll_interval_days, development_roll_interval_days columns
- Adds: current_event column

Usage:
    python tools/migrate_db_v4.py path/to/database.db

Backup your database before running this script!
"""

import sqlite3
import sys
from pathlib import Path


def migrate_database(db_path: str) -> None:
    """Migrate a single database file."""
    print(f"Migrating database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if colonies table exists
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='colonies'
    """)
    if not cursor.fetchone():
        print("  ERROR: 'colonies' table not found!")
        conn.close()
        return

    # Get current column list
    cursor.execute("PRAGMA table_info(colonies)")
    columns = {row[1]: row for row in cursor.fetchall()}

    # Check for columns to remove
    columns_to_remove = ["event_roll_interval_days", "development_roll_interval_days"]
    columns_to_add = ["current_event"]

    for col in columns_to_remove:
        if col in columns:
            print(f"  Found column to remove: {col}")
        else:
            print(f"  Column {col} not present (already migrated?)")

    for col in columns_to_add:
        if col in columns:
            print(f"  Column {col} already exists")
        else:
            print(f"  Need to add column: {col}")

    # SQLite doesn't support DROP COLUMN in older versions, so we need to:
    # 1. Create new table with correct schema
    # 2. Copy data
    # 3. Drop old table
    # 4. Rename new table

    # Build column list for new table (excluding removed columns)
    new_columns = []
    for col_name, col_info in columns.items():
        if col_name not in columns_to_remove and col_name != "sqlite_sequence":
            col_type = col_info[2]
            not_null = "NOT NULL" if col_info[3] else ""
            default = f"DEFAULT {col_info[4]}" if col_info[4] is not None else ""
            new_columns.append(f"{col_name} {col_type} {not_null} {default}".strip())

    # Add new columns
    if "current_event" not in columns:
        new_columns.append("current_event TEXT")

    # Create temporary table
    temp_columns = ", ".join([c.split()[0] for c in new_columns])
    create_sql = f"CREATE TABLE colonies_new ({', '.join(new_columns)})"

    print(f"  Creating new table with columns: {temp_columns}")

    cursor.execute(create_sql)

    # Copy data (only columns that exist in both)
    existing_cols = [c for c in columns if c not in columns_to_remove and c != "sqlite_sequence"]
    copy_cols = ", ".join(existing_cols)
    cursor.execute(f"INSERT INTO colonies_new ({copy_cols}) SELECT {copy_cols} FROM colonies")

    # Drop old table
    cursor.execute("DROP TABLE colonies")

    # Rename new table
    cursor.execute("ALTER TABLE colonies_new RENAME TO colonies")

    conn.commit()
    conn.close()

    print("  Migration complete!")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python migrate_db_v4.py <database_path>")
        print("\nExample:")
        print("  python migrate_db_v4.py data/colonies.db")
        sys.exit(1)

    db_path = sys.argv[1]

    if not Path(db_path).exists():
        print(f"ERROR: Database file not found: {db_path}")
        sys.exit(1)

    migrate_database(db_path)


if __name__ == "__main__":
    main()
