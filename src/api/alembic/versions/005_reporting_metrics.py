"""Add reporting_metrics table for RHDP reporting data.

Revision ID: 005
Revises: 004
Create Date: 2026-06-15
"""
from typing import Sequence, Union

from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS reporting_metrics (
            catalog_base_name  TEXT PRIMARY KEY,
            display_name       TEXT NOT NULL,
            provisions         INTEGER NOT NULL DEFAULT 0,
            provisions_quarter INTEGER NOT NULL DEFAULT 0,
            requests           INTEGER NOT NULL DEFAULT 0,
            experiences        INTEGER NOT NULL DEFAULT 0,
            unique_users       INTEGER NOT NULL DEFAULT 0,
            success_ratio      NUMERIC NOT NULL DEFAULT 0,
            failure_ratio      NUMERIC NOT NULL DEFAULT 0,
            touched_amount     NUMERIC NOT NULL DEFAULT 0,
            closed_amount      NUMERIC NOT NULL DEFAULT 0,
            total_cost         NUMERIC NOT NULL DEFAULT 0,
            avg_cost_per_provision NUMERIC NOT NULL DEFAULT 0,
            first_provision    DATE,
            last_provision     DATE,
            retirement_score   INTEGER NOT NULL DEFAULT 0,
            synced_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS ix_reporting_metrics_retirement_score
            ON reporting_metrics (retirement_score DESC);
        CREATE INDEX IF NOT EXISTS ix_reporting_metrics_display_name
            ON reporting_metrics (display_name);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS reporting_metrics CASCADE;")
