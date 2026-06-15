"""Add curated_duration_min to showroom_analysis.

Revision ID: 003
Revises: 002
Create Date: 2026-06-15
"""
from typing import Sequence, Union

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE showroom_analysis
            ADD COLUMN IF NOT EXISTS curated_duration_min INTEGER
                CHECK (curated_duration_min >= 0);
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE showroom_analysis
            DROP COLUMN IF EXISTS curated_duration_min;
    """)
