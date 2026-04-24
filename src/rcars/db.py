"""PostgreSQL + pgvector database layer for RCARS."""

import logging
from datetime import datetime, timezone
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

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
    content_hash TEXT,
    enrichment_review_needed BOOLEAN DEFAULT FALSE,
    notes TEXT
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
    """PostgreSQL database with connection pooling.

    Uses psycopg_pool.ConnectionPool for thread-safe concurrent access.
    Each method acquires a connection from the pool, uses it, and returns
    it automatically via context manager.
    """

    def __init__(self, database_url: str):
        self._url = database_url
        self._pool = ConnectionPool(
            database_url,
            min_size=2,
            max_size=10,
            open=True,
            kwargs={"row_factory": dict_row, "autocommit": False},
        )

    def close(self):
        """Close the connection pool."""
        self._pool.close()

    def create_schema(self):
        """Create all tables if they don't exist, and apply migrations."""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'alembic_version'
                    ) as exists
                """)
                result = cur.fetchone()
                alembic_exists = result["exists"]

                if not alembic_exists:
                    cur.execute(SCHEMA_SQL)
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS alembic_version (
                            version_num VARCHAR(32) NOT NULL,
                            CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                        )
                    """)
                    cur.execute("INSERT INTO alembic_version (version_num) VALUES ('001')")

                # Migration 002: add content_hash column
                cur.execute("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'showroom_analysis' AND column_name = 'content_hash'
                """)
                if not cur.fetchone():
                    cur.execute("ALTER TABLE showroom_analysis ADD COLUMN content_hash TEXT")

                # Migration 003: add token_usage table
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'token_usage'
                    ) as exists
                """)
                result = cur.fetchone()
                if not result["exists"]:
                    cur.execute("""
                        CREATE TABLE token_usage (
                            id            SERIAL PRIMARY KEY,
                            operation     TEXT NOT NULL,
                            model         TEXT NOT NULL,
                            ci_name       TEXT,
                            query_text    TEXT,
                            input_tokens  INTEGER NOT NULL DEFAULT 0,
                            output_tokens INTEGER NOT NULL DEFAULT 0,
                            created_at    TIMESTAMPTZ DEFAULT NOW()
                        )
                    """)
                    cur.execute(
                        "CREATE INDEX idx_token_usage_created_at ON token_usage(created_at)"
                    )
                    cur.execute(
                        "CREATE INDEX idx_token_usage_operation ON token_usage(operation)"
                    )
            conn.commit()

    def drop_schema(self):
        """Drop all tables, terminating other connections first."""
        tables = [
            "embeddings", "enrichment_tags", "showroom_analysis",
            "analysis_log", "jobs", "token_usage", "catalog_items", "alembic_version",
        ]
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = current_database()
                      AND pid != pg_backend_pid()
                """)
                for table in tables:
                    cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            conn.commit()

    def list_tables(self) -> list[str]:
        """List all tables in the public schema."""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
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
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, present)
            conn.commit()

    def get_catalog_item(self, ci_name: str) -> dict[str, Any] | None:
        """Get a single catalog item by name."""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
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

        with self._pool.connection() as conn:
            with conn.cursor() as cur:
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
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
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
            conn.commit()

    def get_recent_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent log entries."""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM analysis_log ORDER BY created_at DESC LIMIT %(limit)s",
                    {"limit": limit},
                )
                return cur.fetchall()

    def log_token_usage(
        self,
        operation: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        ci_name: str | None = None,
        query_text: str | None = None,
    ) -> None:
        """Log a single API token usage event."""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO token_usage
                       (operation, model, input_tokens, output_tokens, ci_name, query_text)
                       VALUES (%(operation)s, %(model)s, %(input_tokens)s, %(output_tokens)s,
                               %(ci_name)s, %(query_text)s)""",
                    {
                        "operation": operation,
                        "model": model,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "ci_name": ci_name,
                        "query_text": query_text,
                    },
                )
            conn.commit()

    def get_token_stats(self, days: int | None = 30) -> list[dict[str, Any]]:
        """Return token usage aggregated by (operation, model)."""
        if days is not None:
            where = "WHERE created_at >= NOW() - %(days)s * INTERVAL '1 day'"
            params: dict[str, Any] = {"days": days}
        else:
            where = ""
            params = {}

        sql = f"""
            SELECT operation, model,
                   COUNT(*) AS calls,
                   SUM(input_tokens) AS input_tokens,
                   SUM(output_tokens) AS output_tokens,
                   SUM(input_tokens + output_tokens) AS total_tokens
            FROM token_usage
            {where}
            GROUP BY operation, model
            ORDER BY total_tokens DESC
        """
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()

    def get_recent_queries(
        self, days: int | None = 30, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Return per-query token usage for triage + rationale ops."""
        if days is not None:
            time_filter = "AND created_at >= NOW() - %(days)s * INTERVAL '1 day'"
            params: dict[str, Any] = {"days": days, "limit": limit}
        else:
            time_filter = ""
            params = {"limit": limit}

        sql = f"""
            SELECT
                query_text,
                date_trunc('minute', created_at) AS query_time,
                SUM(CASE WHEN operation = 'triage' THEN input_tokens ELSE 0 END)
                    AS triage_input,
                SUM(CASE WHEN operation = 'triage' THEN output_tokens ELSE 0 END)
                    AS triage_output,
                SUM(CASE WHEN operation = 'rationale' THEN input_tokens ELSE 0 END)
                    AS rationale_input,
                SUM(CASE WHEN operation = 'rationale' THEN output_tokens ELSE 0 END)
                    AS rationale_output,
                SUM(input_tokens + output_tokens) AS total_tokens
            FROM token_usage
            WHERE operation IN ('triage', 'rationale')
              AND query_text IS NOT NULL
              {time_filter}
            GROUP BY query_text, date_trunc('minute', created_at)
            ORDER BY query_time DESC
            LIMIT %(limit)s
        """
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()

    def get_status_summary(self) -> dict[str, int]:
        """Get summary counts for the catalog."""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) as count FROM catalog_items")
                total = cur.fetchone()["count"]

                cur.execute("SELECT COUNT(*) as count FROM catalog_items WHERE is_prod = TRUE")
                prod = cur.fetchone()["count"]

                cur.execute("""
                    SELECT COUNT(*) as count FROM catalog_items
                    WHERE showroom_url IS NOT NULL AND showroom_url != ''
                      AND (is_published IS NULL OR is_published = FALSE)
                """)
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

    def upsert_showroom_analysis(self, analysis: dict[str, Any]):
        """Insert or update a showroom analysis result."""
        fields = [
            "ci_name", "content_type", "summary",
            "products_json", "audience_json", "topics_json",
            "modules_json", "learning_objectives_json",
            "difficulty", "estimated_duration_min",
            "event_fit_json", "use_cases_json",
            "last_repo_commit", "last_repo_updated",
            "last_analyzed", "is_stale", "stale_commit", "content_hash",
            "enrichment_review_needed",
        ]
        present = {k: analysis.get(k) for k in fields if k in analysis}
        if "last_analyzed" not in present:
            present["last_analyzed"] = datetime.now(timezone.utc)

        jsonb_fields = [
            "products_json", "audience_json", "topics_json",
            "modules_json", "learning_objectives_json",
            "event_fit_json", "use_cases_json",
        ]
        for f in jsonb_fields:
            if f in present and present[f] is not None:
                present[f] = Jsonb(present[f])

        columns = list(present.keys())
        placeholders = [f"%({k})s" for k in columns]
        updates = [f"{k} = EXCLUDED.{k}" for k in columns if k != "ci_name"]

        sql = f"""
            INSERT INTO showroom_analysis ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            ON CONFLICT (ci_name) DO UPDATE SET {', '.join(updates)}
        """
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, present)
            conn.commit()

    def get_showroom_analysis(self, ci_name: str) -> dict[str, Any] | None:
        """Get analysis for a catalog item."""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM showroom_analysis WHERE ci_name = %(ci_name)s",
                    {"ci_name": ci_name},
                )
                return cur.fetchone()

    def store_embedding(
        self,
        ci_name: str,
        embed_type: str,
        content_text: str,
        embedding: list[float],
        module_title: str | None = None,
    ):
        """Store an embedding vector."""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                if module_title:
                    cur.execute(
                        """DELETE FROM embeddings
                           WHERE ci_name = %(ci_name)s AND embed_type = %(embed_type)s
                           AND module_title = %(module_title)s""",
                        {"ci_name": ci_name, "embed_type": embed_type, "module_title": module_title},
                    )
                else:
                    cur.execute(
                        """DELETE FROM embeddings
                           WHERE ci_name = %(ci_name)s AND embed_type = %(embed_type)s
                           AND module_title IS NULL""",
                        {"ci_name": ci_name, "embed_type": embed_type},
                    )
                cur.execute(
                    """INSERT INTO embeddings (ci_name, embed_type, module_title, content_text, embedding)
                       VALUES (%(ci_name)s, %(embed_type)s, %(module_title)s, %(content_text)s, %(embedding)s::vector)""",
                    {
                        "ci_name": ci_name,
                        "embed_type": embed_type,
                        "module_title": module_title,
                        "content_text": content_text,
                        "embedding": f"[{','.join(str(v) for v in embedding)}]",
                    },
                )
            conn.commit()

    def search_embeddings(
        self,
        query_embedding: list[float],
        limit: int = 15,
        prod_only: bool = True,
        embed_type: str = "ci_summary",
    ) -> list[dict[str, Any]]:
        """Search embeddings by cosine similarity."""
        prod_filter = ""
        if prod_only:
            prod_filter = "AND ci.is_prod = TRUE"

        sql = f"""
            SELECT e.ci_name, e.content_text, e.module_title,
                   e.embedding <=> %(query)s::vector AS distance,
                   ci.display_name, ci.category, ci.stage,
                   ci.is_published, ci.published_ci_name, ci.base_ci_name
            FROM embeddings e
            JOIN catalog_items ci ON e.ci_name = ci.ci_name
            WHERE e.embed_type = %(embed_type)s
            {prod_filter}
            ORDER BY distance ASC
            LIMIT %(limit)s
        """
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, {
                    "query": f"[{','.join(str(v) for v in query_embedding)}]",
                    "embed_type": embed_type,
                    "limit": limit,
                })
                return cur.fetchall()

    def get_items_needing_analysis(self) -> list[dict[str, Any]]:
        """Get catalog items that need analysis: unanalyzed or stale."""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT ci.* FROM catalog_items ci
                    LEFT JOIN showroom_analysis sa ON ci.ci_name = sa.ci_name
                    WHERE ci.showroom_url IS NOT NULL
                      AND ci.showroom_url != ''
                      AND (sa.ci_name IS NULL OR sa.is_stale = TRUE)
                    ORDER BY ci.ci_name
                """)
                return cur.fetchall()

    def get_analyzed_items(self) -> list[dict[str, Any]]:
        """Get all analyzed catalog items with their Showroom metadata."""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT ci.ci_name, ci.showroom_url, ci.showroom_ref,
                           ci.is_published, ci.base_ci_name,
                           sa.last_repo_commit, sa.content_hash
                    FROM showroom_analysis sa
                    JOIN catalog_items ci ON sa.ci_name = ci.ci_name
                    WHERE ci.showroom_url IS NOT NULL
                      AND ci.showroom_url != ''
                    ORDER BY ci.ci_name
                """)
                return cur.fetchall()

    def mark_stale(self, ci_name: str, new_commit: str | None = None) -> None:
        """Mark a showroom analysis as stale."""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE showroom_analysis
                    SET is_stale = TRUE, stale_commit = %(commit)s
                    WHERE ci_name = %(ci_name)s
                """, {"ci_name": ci_name, "commit": new_commit})
            conn.commit()

    def clear_stale(self, ci_name: str) -> None:
        """Clear the stale flag after a successful rescan."""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE showroom_analysis
                    SET is_stale = FALSE, stale_commit = NULL
                    WHERE ci_name = %(ci_name)s
                """, {"ci_name": ci_name})
            conn.commit()

    def add_enrichment_tag(self, ci_name: str, tag_type: str, tag_value: str, added_by: str | None = None) -> None:
        """Add a tag to a catalog item. Silently ignores duplicates."""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO enrichment_tags (ci_name, tag_type, tag_value, added_by)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (ci_name, tag_type, tag_value) DO NOTHING
                    """,
                    (ci_name, tag_type, tag_value, added_by),
                )
            conn.commit()

    def remove_enrichment_tag(self, ci_name: str, tag_type: str, tag_value: str) -> None:
        """Remove a specific tag from a catalog item."""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM enrichment_tags WHERE ci_name = %s AND tag_type = %s AND tag_value = %s",
                    (ci_name, tag_type, tag_value),
                )
            conn.commit()

    def get_enrichment_tags(self, ci_name: str) -> list[dict]:
        """Return all enrichment tags for a catalog item."""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT tag_type, tag_value, added_by, added_at FROM enrichment_tags WHERE ci_name = %s ORDER BY added_at",
                    (ci_name,),
                )
                return cur.fetchall()

    def get_enrichment_tags_for_items(self, ci_names: list[str]) -> dict[str, list[dict]]:
        """Return enrichment tags for multiple items, keyed by ci_name."""
        if not ci_names:
            return {}
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT ci_name, tag_type, tag_value, added_by FROM enrichment_tags WHERE ci_name = ANY(%s) ORDER BY ci_name, added_at",
                    (ci_names,),
                )
                result: dict[str, list] = {name: [] for name in ci_names}
                for row in cur.fetchall():
                    result[row["ci_name"]].append(row)
                return result

    def set_enrichment_note(self, ci_name: str, note: str, updated_by: str | None = None) -> None:
        """Set the curator note for a catalog item (requires showroom_analysis row)."""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE showroom_analysis SET notes = %s WHERE ci_name = %s",
                    (note, ci_name),
                )
                if cur.rowcount == 0:
                    cur.execute(
                        "INSERT INTO showroom_analysis (ci_name, notes) VALUES (%s, %s) ON CONFLICT (ci_name) DO UPDATE SET notes = EXCLUDED.notes",
                        (ci_name, note),
                    )
            conn.commit()

    def get_enrichment_note(self, ci_name: str) -> str | None:
        """Return the curator note for a catalog item, or None."""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT notes FROM showroom_analysis WHERE ci_name = %s", (ci_name,))
                row = cur.fetchone()
                return row["notes"] if row else None

    def set_enrichment_review_needed(self, ci_name: str, needed: bool) -> None:
        """Set or clear the enrichment review flag on showroom_analysis."""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE showroom_analysis SET enrichment_review_needed = %s WHERE ci_name = %s",
                    (needed, ci_name),
                )
                if cur.rowcount == 0:
                    cur.execute(
                        "INSERT INTO showroom_analysis (ci_name, enrichment_review_needed) VALUES (%s, %s) ON CONFLICT (ci_name) DO UPDATE SET enrichment_review_needed = EXCLUDED.enrichment_review_needed",
                        (ci_name, needed),
                    )
            conn.commit()

    def get_db_currency(self, stale_days: int = 3) -> dict:
        """Return last catalog refresh date and staleness status."""
        from datetime import timedelta
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT MAX(last_refreshed) as max_refreshed FROM catalog_items")
                row = cur.fetchone()
                last_refresh = row["max_refreshed"] if row else None
        if last_refresh is None:
            return {"last_refresh": "never", "is_stale": True}
        now = datetime.now(timezone.utc)
        is_stale = (now - last_refresh) > timedelta(days=stale_days)
        return {
            "last_refresh": last_refresh.strftime("%Y.%m.%d"),
            "is_stale": is_stale,
        }
