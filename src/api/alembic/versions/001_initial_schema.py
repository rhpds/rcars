"""Initial schema — baseline from existing RCARS database.

Revision ID: 001
Revises: None
Create Date: 2026-04-10
"""
from typing import Sequence, Union

from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute("""
    CREATE TABLE IF NOT EXISTS catalog_items (
        ci_name TEXT PRIMARY KEY,
        display_name TEXT,
        category TEXT,
        product TEXT,
        product_family TEXT,
        primary_bu TEXT,
        secondary_bu TEXT,
        stage TEXT,
        catalog_namespace TEXT,
        keywords TEXT[],
        description TEXT,
        icon_url TEXT,
        owners_json JSONB,
        showroom_url TEXT,
        showroom_ref TEXT,
        last_crd_update TIMESTAMPTZ,
        last_refreshed TIMESTAMPTZ DEFAULT NOW(),
        is_prod BOOLEAN DEFAULT FALSE,
        is_published BOOLEAN DEFAULT FALSE,
        published_ci_name TEXT,
        base_ci_name TEXT
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS showroom_analysis (
        ci_name TEXT PRIMARY KEY REFERENCES catalog_items(ci_name) ON DELETE CASCADE,
        content_type TEXT,
        summary TEXT,
        products_json JSONB,
        audience_json JSONB,
        topics_json JSONB,
        modules_json JSONB,
        learning_objectives_json JSONB,
        difficulty TEXT,
        estimated_duration_min INTEGER,
        event_fit_json JSONB,
        use_cases_json JSONB,
        last_repo_commit TEXT,
        last_repo_updated TIMESTAMPTZ,
        last_analyzed TIMESTAMPTZ,
        is_stale BOOLEAN DEFAULT FALSE,
        stale_commit TEXT,
        enrichment_review_needed BOOLEAN DEFAULT FALSE,
        notes TEXT
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS enrichment_tags (
        id SERIAL PRIMARY KEY,
        ci_name TEXT NOT NULL REFERENCES catalog_items(ci_name) ON DELETE CASCADE,
        tag_type TEXT NOT NULL,
        tag_value TEXT NOT NULL,
        added_by TEXT,
        added_at TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE(ci_name, tag_type, tag_value)
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS embeddings (
        id SERIAL PRIMARY KEY,
        ci_name TEXT NOT NULL REFERENCES catalog_items(ci_name) ON DELETE CASCADE,
        embed_type TEXT NOT NULL,
        module_title TEXT,
        content_text TEXT,
        embedding vector(384)
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS analysis_log (
        id SERIAL PRIMARY KEY,
        ci_name TEXT,
        action TEXT NOT NULL,
        user_id TEXT,
        details TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        job_type TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'queued',
        triggered_by TEXT,
        progress_current INTEGER DEFAULT 0,
        progress_total INTEGER DEFAULT 0,
        result_json JSONB,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        started_at TIMESTAMPTZ,
        completed_at TIMESTAMPTZ
    )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_catalog_items_stage ON catalog_items(stage)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_catalog_items_is_prod ON catalog_items(is_prod)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_catalog_items_category ON catalog_items(category)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_catalog_items_showroom_url ON catalog_items(showroom_url)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_enrichment_tags_ci_name ON enrichment_tags(ci_name)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_embeddings_ci_name ON embeddings(ci_name)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_analysis_log_ci_name ON analysis_log(ci_name)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_analysis_log_created_at ON analysis_log(created_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS embeddings CASCADE")
    op.execute("DROP TABLE IF EXISTS enrichment_tags CASCADE")
    op.execute("DROP TABLE IF EXISTS showroom_analysis CASCADE")
    op.execute("DROP TABLE IF EXISTS analysis_log CASCADE")
    op.execute("DROP TABLE IF EXISTS jobs CASCADE")
    op.execute("DROP TABLE IF EXISTS catalog_items CASCADE")
