"""Extend api_keys table for external auth.

Adds key_prefix, role, expires_at columns. Makes created_by NOT NULL.

Revision ID: 013
Revises: 012
Create Date: 2026-07-03
"""
from typing import Sequence, Union

from alembic import op

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS key_prefix TEXT NOT NULL DEFAULT ''")
    op.execute("ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'user'")
    op.execute("ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ")
    op.execute("ALTER TABLE api_keys ALTER COLUMN created_by SET NOT NULL")
    op.execute("ALTER TABLE api_keys ALTER COLUMN created_by SET DEFAULT ''")
    op.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_created_by ON api_keys(created_by)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_api_keys_created_by")
    op.execute("DROP INDEX IF EXISTS idx_api_keys_hash")
    op.execute("ALTER TABLE api_keys DROP COLUMN IF EXISTS expires_at")
    op.execute("ALTER TABLE api_keys DROP COLUMN IF EXISTS role")
    op.execute("ALTER TABLE api_keys DROP COLUMN IF EXISTS key_prefix")
