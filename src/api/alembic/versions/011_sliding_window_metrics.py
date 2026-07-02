"""Replace calendar-quarter bucketing with sliding window metrics.

Adds windowed_metrics JSONB column containing pre-computed metrics
for 3m/6m/9m/12m sliding windows. Drops quarterly_data and the
per-quarter unique_users columns which are superseded.

Revision ID: 011
Revises: 010
Create Date: 2026-07-02
"""
from typing import Sequence, Union

from alembic import op

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE reporting_metrics
            ADD COLUMN IF NOT EXISTS windowed_metrics JSONB DEFAULT '{}'::jsonb,
            DROP COLUMN IF EXISTS quarterly_data,
            DROP COLUMN IF EXISTS unique_users_1q,
            DROP COLUMN IF EXISTS unique_users_2q,
            DROP COLUMN IF EXISTS unique_users_3q;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE reporting_metrics
            ADD COLUMN IF NOT EXISTS quarterly_data JSONB DEFAULT '{}'::jsonb,
            ADD COLUMN IF NOT EXISTS unique_users_1q INTEGER NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS unique_users_2q INTEGER NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS unique_users_3q INTEGER NOT NULL DEFAULT 0,
            DROP COLUMN IF EXISTS windowed_metrics;
    """)
