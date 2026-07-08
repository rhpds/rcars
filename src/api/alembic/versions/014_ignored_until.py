"""Add ignored_until column to reporting_metrics.

Allows curators to mute items from the retirement dashboard
for a specified period (e.g. 30 days).

Revision ID: 014
Revises: 013
Create Date: 2026-07-08
"""
from typing import Sequence, Union

from alembic import op

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE reporting_metrics ADD COLUMN IF NOT EXISTS ignored_until DATE")


def downgrade() -> None:
    op.execute("ALTER TABLE reporting_metrics DROP COLUMN IF EXISTS ignored_until")
