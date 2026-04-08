"""PostgreSQL + pgvector database layer for RCARS."""

import logging
from datetime import datetime, timezone
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

log = logging.getLogger(__name__)

SCHEMA_SQL = """
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
);

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
    enrichment_review_needed BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS enrichment_tags (
    id SERIAL PRIMARY KEY,
    ci_name TEXT NOT NULL REFERENCES catalog_items(ci_name) ON DELETE CASCADE,
    tag_type TEXT NOT NULL,
    tag_value TEXT NOT NULL,
    added_by TEXT,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(ci_name, tag_type, tag_value)
);

CREATE TABLE IF NOT EXISTS embeddings (
    id SERIAL PRIMARY KEY,
    ci_name TEXT NOT NULL REFERENCES catalog_items(ci_name) ON DELETE CASCADE,
    embed_type TEXT NOT NULL,
    module_title TEXT,
    content_text TEXT,
    embedding vector(384)
);

CREATE TABLE IF NOT EXISTS analysis_log (
    id SERIAL PRIMARY KEY,
    ci_name TEXT,
    action TEXT NOT NULL,
    user_id TEXT,
    details TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

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
);

CREATE INDEX IF NOT EXISTS idx_catalog_items_stage ON catalog_items(stage);
CREATE INDEX IF NOT EXISTS idx_catalog_items_is_prod ON catalog_items(is_prod);
CREATE INDEX IF NOT EXISTS idx_catalog_items_category ON catalog_items(category);
CREATE INDEX IF NOT EXISTS idx_catalog_items_showroom_url ON catalog_items(showroom_url);
CREATE INDEX IF NOT EXISTS idx_enrichment_tags_ci_name ON enrichment_tags(ci_name);
CREATE INDEX IF NOT EXISTS idx_embeddings_ci_name ON embeddings(ci_name);
CREATE INDEX IF NOT EXISTS idx_analysis_log_ci_name ON analysis_log(ci_name);
CREATE INDEX IF NOT EXISTS idx_analysis_log_created_at ON analysis_log(created_at);
"""


class Database:
    """PostgreSQL database connection and operations."""

    def __init__(self, database_url: str):
        self._url = database_url
        self._conn = psycopg.connect(database_url, row_factory=dict_row)
        self._conn.autocommit = False

    def close(self):
        """Close the database connection."""
        self._conn.close()

    def create_schema(self):
        """Create all tables if they don't exist."""
        with self._conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(SCHEMA_SQL)
        self._conn.commit()

    def drop_schema(self):
        """Drop all tables. Only for testing."""
        # Table names are hardcoded literals, not user input — safe for f-string SQL
        tables = [
            "embeddings", "enrichment_tags", "showroom_analysis",
            "analysis_log", "jobs", "catalog_items",
        ]
        with self._conn.cursor() as cur:
            for table in tables:
                cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        self._conn.commit()

    def list_tables(self) -> list[str]:
        """List all tables in the public schema."""
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            )
            return [row["tablename"] for row in cur.fetchall()]

    def upsert_catalog_item(self, item: dict[str, Any]):
        """Insert or update a catalog item."""
        fields = [
            "ci_name", "display_name", "category", "product", "product_family",
            "primary_bu", "secondary_bu", "stage", "catalog_namespace",
            "keywords", "description", "icon_url", "owners_json",
            "showroom_url", "showroom_ref", "last_crd_update", "is_prod",
            "is_published", "published_ci_name", "base_ci_name",
        ]
        present = {k: item.get(k) for k in fields if k in item}
        present["last_refreshed"] = datetime.now(timezone.utc)

        # Wrap JSONB fields with Jsonb adapter
        if "owners_json" in present and present["owners_json"] is not None:
            present["owners_json"] = Jsonb(present["owners_json"])

        columns = list(present.keys())
        placeholders = [f"%({k})s" for k in columns]
        updates = [f"{k} = EXCLUDED.{k}" for k in columns if k != "ci_name"]

        sql = f"""
            INSERT INTO catalog_items ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            ON CONFLICT (ci_name) DO UPDATE SET {', '.join(updates)}
        """
        with self._conn.cursor() as cur:
            cur.execute(sql, present)
        self._conn.commit()

    def get_catalog_item(self, ci_name: str) -> dict[str, Any] | None:
        """Get a single catalog item by name."""
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM catalog_items WHERE ci_name = %(ci_name)s",
                {"ci_name": ci_name},
            )
            return cur.fetchone()

    def list_catalog_items(
        self, prod_only: bool = False, category: str | None = None
    ) -> list[dict[str, Any]]:
        """List catalog items with optional filters."""
        conditions = []
        params: dict[str, Any] = {}

        if prod_only:
            conditions.append("is_prod = TRUE")
        if category:
            conditions.append("category = %(category)s")
            params["category"] = category

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT * FROM catalog_items {where} ORDER BY ci_name"

        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def log_action(
        self,
        ci_name: str,
        action: str,
        user_id: str | None = None,
        details: str | None = None,
    ):
        """Log an action to the audit trail."""
        with self._conn.cursor() as cur:
            cur.execute(
                """INSERT INTO analysis_log (ci_name, action, user_id, details)
                   VALUES (%(ci_name)s, %(action)s, %(user_id)s, %(details)s)""",
                {
                    "ci_name": ci_name,
                    "action": action,
                    "user_id": user_id,
                    "details": details,
                },
            )
        self._conn.commit()

    def get_recent_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent log entries."""
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM analysis_log ORDER BY created_at DESC LIMIT %(limit)s",
                {"limit": limit},
            )
            return cur.fetchall()

    def get_status_summary(self) -> dict[str, int]:
        """Get summary counts for the catalog."""
        with self._conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as count FROM catalog_items")
            total = cur.fetchone()["count"]

            cur.execute("SELECT COUNT(*) as count FROM catalog_items WHERE is_prod = TRUE")
            prod = cur.fetchone()["count"]

            cur.execute(
                "SELECT COUNT(*) as count FROM catalog_items WHERE showroom_url IS NOT NULL AND showroom_url != ''"
            )
            with_showroom = cur.fetchone()["count"]

            cur.execute("SELECT COUNT(*) as count FROM showroom_analysis")
            analyzed = cur.fetchone()["count"]

            cur.execute(
                "SELECT COUNT(*) as count FROM showroom_analysis WHERE is_stale = TRUE"
            )
            stale = cur.fetchone()["count"]

        return {
            "total": total,
            "prod": prod,
            "with_showroom": with_showroom,
            "analyzed": analyzed,
            "stale": stale,
        }
