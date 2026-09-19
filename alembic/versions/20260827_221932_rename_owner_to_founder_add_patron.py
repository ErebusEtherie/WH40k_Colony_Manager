"""Rename owner to founder_name and add patron_name column.

Revision ID: 20260827_221932
Revises: f6a9a7be18f0
Create Date: 2026-08-27

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260827_221932"
down_revision = "f6a9a7be18f0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Rename owner column to founder_name and add patron_name column."""
    # Rename owner to founder_name
    op.alter_column(
        "colonies",
        "owner",
        new_column_name="founder_name",
        existing_type=sa.String(255),
        existing_nullable=False,
    )

    # Add patron_name column (nullable, optional)
    op.add_column(
        "colonies",
        sa.Column("patron_name", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    """Revert founder_name back to owner and remove patron_name."""
    # Remove patron_name column
    op.drop_column("colonies", "patron_name")

    # Rename founder_name back to owner
    op.alter_column(
        "colonies",
        "founder_name",
        new_column_name="owner",
        existing_type=sa.String(255),
        existing_nullable=False,
    )
