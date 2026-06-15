"""Add content_similarity table for overlap detection.

Revision ID: 004
Revises: 003
Create Date: 2026-06-15
"""
from typing import Sequence, Union

from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS content_similarity (
            id SERIAL PRIMARY KEY,
            ci_name_a TEXT NOT NULL REFERENCES catalog_items(ci_name) ON DELETE CASCADE,
            ci_name_b TEXT NOT NULL REFERENCES catalog_items(ci_name) ON DELETE CASCADE,
            similarity_score REAL NOT NULL,
            computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(ci_name_a, ci_name_b)
        );
        CREATE INDEX IF NOT EXISTS idx_content_similarity_a ON content_similarity(ci_name_a);
        CREATE INDEX IF NOT EXISTS idx_content_similarity_b ON content_similarity(ci_name_b);
        CREATE INDEX IF NOT EXISTS idx_content_similarity_score ON content_similarity(similarity_score DESC);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS content_similarity CASCADE;")
