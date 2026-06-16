"""Add provider column to token_usage table.

Revision ID: 006
Revises: 005
Create Date: 2026-06-16
"""
from typing import Sequence, Union

from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE token_usage ADD COLUMN IF NOT EXISTS provider TEXT DEFAULT 'anthropic'")
    op.execute("CREATE INDEX IF NOT EXISTS idx_token_usage_provider ON token_usage(provider)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_token_usage_provider")
    op.execute("ALTER TABLE token_usage DROP COLUMN IF EXISTS provider")
