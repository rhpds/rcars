"""Add quarterly_data JSONB column to reporting_metrics.

Stores per-quarter breakdowns of provisions, touched, closed, and cost
so the retirement dashboard can recompute scores for different time windows
without re-querying the MCP server.

Revision ID: 007
Revises: 006
Create Date: 2026-06-17
"""
from typing import Sequence, Union

from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE reporting_metrics
        ADD COLUMN IF NOT EXISTS quarterly_data JSONB DEFAULT '{}'::jsonb;
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE reporting_metrics DROP COLUMN IF EXISTS quarterly_data;")
