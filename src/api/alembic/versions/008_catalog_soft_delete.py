"""Add soft-delete columns to catalog_items.

Items that disappear from Babylon CRDs get retired_at set instead of
being deleted, preserving all associated analysis and reporting data.

Revision ID: 008
Revises: 007
Create Date: 2026-06-18
"""
from typing import Sequence, Union

from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE catalog_items
        ADD COLUMN IF NOT EXISTS retired_at TIMESTAMPTZ,
        ADD COLUMN IF NOT EXISTS retirement_reason TEXT;
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_catalog_items_retired_at
        ON catalog_items (retired_at)
        WHERE retired_at IS NOT NULL;
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_catalog_items_retired_at;")
    op.execute("""
        ALTER TABLE catalog_items
        DROP COLUMN IF EXISTS retirement_reason,
        DROP COLUMN IF EXISTS retired_at;
    """)
