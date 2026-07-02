"""Add retirement_workflow table for tracking retirement lifecycle.

Tracks each catalog item through the retirement pipeline:
reviewed → approved → notified → started → retired.

Revision ID: 012
Revises: 011
Create Date: 2026-07-02
"""
from typing import Sequence, Union

from alembic import op

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS retirement_workflow (
            catalog_base_name    TEXT PRIMARY KEY,
            status               TEXT NOT NULL DEFAULT 'reviewed',
            step_reviewed_at     TIMESTAMPTZ,
            step_reviewed_by     TEXT,
            step_approved_at     TIMESTAMPTZ,
            step_approved_by     TEXT,
            approval_reason      TEXT,
            approval_snapshot    JSONB,
            step_notified_at     TIMESTAMPTZ,
            step_notified_by     TEXT,
            step_started_at      TIMESTAMPTZ,
            step_started_by      TEXT,
            retirement_target_date DATE,
            step_retired_at      TIMESTAMPTZ,
            replacement_ci       TEXT,
            replacement_name     TEXT,
            curator_notes        TEXT,
            jira_key             TEXT,
            jira_project         TEXT NOT NULL DEFAULT 'RHDPCD',
            created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS ix_retirement_workflow_status
            ON retirement_workflow (status);
    """)


def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS ix_retirement_workflow_status;
        DROP TABLE IF EXISTS retirement_workflow;
    """)
