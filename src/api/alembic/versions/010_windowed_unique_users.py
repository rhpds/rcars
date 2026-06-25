"""Add windowed unique_users columns to reporting_metrics.

Pre-computed COUNT(DISTINCT user_id) for 1q/2q/3q windows, calculated
at sync time so windowed views show exact unique user counts.

Revision ID: 010
Revises: 009
Create Date: 2026-06-25
"""
from typing import Sequence, Union

from alembic import op

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE reporting_metrics
            ADD COLUMN IF NOT EXISTS unique_users_1q INTEGER NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS unique_users_2q INTEGER NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS unique_users_3q INTEGER NOT NULL DEFAULT 0;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE reporting_metrics
            DROP COLUMN IF EXISTS unique_users_1q,
            DROP COLUMN IF EXISTS unique_users_2q,
            DROP COLUMN IF EXISTS unique_users_3q;
    """)
