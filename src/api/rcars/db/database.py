"""PostgreSQL + pgvector database layer for RCARS v2."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

import structlog

logger = structlog.get_logger()

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
    content_path TEXT,
    last_crd_update TIMESTAMPTZ,
    last_refreshed TIMESTAMPTZ DEFAULT NOW(),
    is_prod BOOLEAN DEFAULT FALSE,
    is_published BOOLEAN DEFAULT FALSE,
    published_ci_name TEXT,
    base_ci_name TEXT,
    scan_status TEXT NOT NULL DEFAULT 'not_scanned',
    scan_error_class TEXT,
    scan_error TEXT,
    scan_failed_at TIMESTAMPTZ,
    showroom_url_override TEXT,
    is_agd_v2 BOOLEAN DEFAULT FALSE,
    agd_config TEXT,
    cloud_provider TEXT,
    ocp_version TEXT,
    os_image TEXT,
    worker_instance_count TEXT,
    control_plane_instance_count TEXT,
    instances_json JSONB
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
    curated_duration_min INTEGER,
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

CREATE TABLE IF NOT EXISTS token_usage (
    id SERIAL PRIMARY KEY,
    operation TEXT NOT NULL,
    model TEXT NOT NULL,
    ci_name TEXT,
    query_text TEXT,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS advisor_sessions (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    turn_index INTEGER NOT NULL,
    user_email TEXT,
    query_text TEXT,
    event_url TEXT,
    results_json JSONB,
    overall_assessment TEXT,
    chosen_ci_name TEXT,
    chosen_at TIMESTAMPTZ,
    opted_out BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    job_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    queue TEXT NOT NULL DEFAULT 'default',
    created_by TEXT,
    progress_json JSONB,
    result_json JSONB,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    key_hash TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    created_by TEXT,
    scopes TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS catalog_item_workloads (
    id SERIAL PRIMARY KEY,
    ci_name TEXT NOT NULL REFERENCES catalog_items(ci_name) ON DELETE CASCADE,
    workload_fqcn TEXT NOT NULL,
    workload_role TEXT NOT NULL,
    workload_collection TEXT,
    UNIQUE(ci_name, workload_fqcn)
);

CREATE TABLE IF NOT EXISTS workload_mapping (
    id SERIAL PRIMARY KEY,
    workload_role TEXT NOT NULL UNIQUE,
    product_name TEXT NOT NULL,
    description TEXT,
    category TEXT,
    source_collection TEXT,
    verified BOOLEAN DEFAULT FALSE,
    added_by TEXT,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    verified_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS workload_aliases (
    id SERIAL PRIMARY KEY,
    product_name TEXT NOT NULL,
    alias TEXT NOT NULL UNIQUE,
    added_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS catalog_item_acl_groups (
    id SERIAL PRIMARY KEY,
    ci_name TEXT NOT NULL REFERENCES catalog_items(ci_name) ON DELETE CASCADE,
    group_name TEXT NOT NULL,
    UNIQUE(ci_name, group_name)
);

CREATE TABLE IF NOT EXISTS workload_scan_state (
    collection TEXT PRIMARY KEY,
    last_sha TEXT,
    last_scanned TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_catalog_items_stage ON catalog_items(stage);
CREATE INDEX IF NOT EXISTS idx_catalog_items_is_prod ON catalog_items(is_prod);
CREATE INDEX IF NOT EXISTS idx_catalog_items_category ON catalog_items(category);
CREATE INDEX IF NOT EXISTS idx_catalog_items_showroom_url ON catalog_items(showroom_url);
CREATE INDEX IF NOT EXISTS idx_enrichment_tags_ci_name ON enrichment_tags(ci_name);
CREATE INDEX IF NOT EXISTS idx_embeddings_ci_name ON embeddings(ci_name);
CREATE INDEX IF NOT EXISTS idx_analysis_log_ci_name ON analysis_log(ci_name);
CREATE INDEX IF NOT EXISTS idx_analysis_log_created_at ON analysis_log(created_at);
CREATE INDEX IF NOT EXISTS idx_token_usage_created_at ON token_usage(created_at);
CREATE INDEX IF NOT EXISTS idx_token_usage_operation ON token_usage(operation);
CREATE INDEX IF NOT EXISTS idx_advisor_sessions_session ON advisor_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_advisor_sessions_user ON advisor_sessions(user_email);
CREATE INDEX IF NOT EXISTS idx_advisor_sessions_created ON advisor_sessions(created_at);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_ciw_ci_name ON catalog_item_workloads(ci_name);
CREATE INDEX IF NOT EXISTS idx_ciw_workload_role ON catalog_item_workloads(workload_role);
CREATE INDEX IF NOT EXISTS idx_ciw_workload_collection ON catalog_item_workloads(workload_collection);
CREATE INDEX IF NOT EXISTS idx_wm_product_name ON workload_mapping(product_name);
CREATE INDEX IF NOT EXISTS idx_wa_product_name ON workload_aliases(product_name);
CREATE INDEX IF NOT EXISTS idx_ciag_ci_name ON catalog_item_acl_groups(ci_name);
CREATE INDEX IF NOT EXISTS idx_ciag_group_name ON catalog_item_acl_groups(group_name);

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
"""

STAGE_PRIORITY = {"prod": 0, "event": 1, "dev": 2}


class Database:
    def __init__(self, database_url: str):
        self._url = database_url
        self._pool = ConnectionPool(
            database_url,
            min_size=2,
            max_size=10,
            open=True,
            kwargs={"row_factory": dict_row, "autocommit": False},
        )

    @property
    def pool(self) -> ConnectionPool:
        return self._pool

    def close(self):
        self._pool.close()

    # ── Schema management ──

    def create_schema(self):
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                cur.execute(SCHEMA_SQL)
            conn.commit()

    def drop_schema(self):
        tables = [
            "content_similarity",
            "embeddings", "enrichment_tags", "showroom_analysis",
            "analysis_log", "jobs", "token_usage", "advisor_sessions",
            "api_keys", "catalog_item_workloads", "catalog_item_acl_groups",
            "workload_aliases", "workload_mapping", "workload_scan_state",
            "catalog_items", "alembic_version",
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

    # ── Catalog items ──

    def upsert_catalog_item(self, item: dict[str, Any]):
        fields = [
            "ci_name", "display_name", "category", "product", "product_family",
            "primary_bu", "secondary_bu", "stage", "catalog_namespace",
            "keywords", "description", "icon_url", "owners_json",
            "showroom_url", "showroom_ref", "content_path",
            "last_crd_update", "is_prod", "is_published",
            "published_ci_name", "base_ci_name",
            "is_agd_v2", "agd_config", "cloud_provider", "ocp_version",
            "os_image", "worker_instance_count", "control_plane_instance_count",
            "instances_json",
        ]
        present = {k: item.get(k) for k in fields if k in item}
        present["last_refreshed"] = datetime.now(timezone.utc)

        if "owners_json" in present and present["owners_json"] is not None:
            present["owners_json"] = Jsonb(present["owners_json"])
        if "instances_json" in present and present["instances_json"] is not None:
            present["instances_json"] = Jsonb(present["instances_json"])

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
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM catalog_items WHERE ci_name = %(ci_name)s",
                    {"ci_name": ci_name},
                )
                return cur.fetchone()

    def list_catalog_items(
        self, prod_only: bool = False, category: str | None = None,
        stage: str | None = None,
    ) -> list[dict[str, Any]]:
        conditions = []
        params: dict[str, Any] = {}
        if prod_only:
            conditions.append("ci.is_prod = TRUE")
        if category:
            conditions.append("ci.category = %(category)s")
            params["category"] = category
        if stage:
            conditions.append("ci.stage = %(stage)s")
            params["stage"] = stage
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""SELECT ci.*, sa.is_stale, sa.enrichment_review_needed
                  FROM catalog_items ci
                  LEFT JOIN showroom_analysis sa ON sa.ci_name = ci.ci_name
                  {where} ORDER BY ci.ci_name"""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()

    def list_catalog_items_filtered(
        self,
        search: str | None = None,
        stages: list[str] | None = None,
        cloud_provider: str | None = None,
        agd_config: str | None = None,
        workloads: list[str] | None = None,
        content_filter: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        conditions = []
        params: dict[str, Any] = {}
        joins = []

        if stages:
            conditions.append("ci.stage = ANY(%(stages)s)")
            params["stages"] = stages
        else:
            conditions.append("ci.stage = 'prod'")

        if search:
            conditions.append(
                "(ci.display_name ILIKE %(search)s OR ci.ci_name ILIKE %(search)s)"
            )
            params["search"] = f"%{search}%"

        if cloud_provider:
            conditions.append("ci.cloud_provider = %(cloud_provider)s")
            params["cloud_provider"] = cloud_provider
        if agd_config:
            conditions.append("ci.agd_config = %(agd_config)s")
            params["agd_config"] = agd_config

        if workloads:
            resolved = self._resolve_workload_aliases(workloads)
            for i, wl in enumerate(resolved):
                alias_w = f"w{i}"
                alias_m = f"m{i}"
                joins.append(
                    f"JOIN catalog_item_workloads {alias_w} "
                    f"ON {alias_w}.ci_name = ci.ci_name "
                    f"JOIN workload_mapping {alias_m} "
                    f"ON {alias_m}.workload_role = {alias_w}.workload_role "
                    f"AND {alias_m}.product_name = %({alias_m}_name)s"
                )
                params[f"{alias_m}_name"] = wl

        if content_filter == "unanalyzed":
            conditions.append("ci.showroom_url IS NOT NULL")
            conditions.append("ci.is_published IS NOT TRUE")
            conditions.append("ci.scan_status NOT IN ('success', 'failed')")
        elif content_filter == "scan_failures":
            conditions.append("ci.scan_status = 'failed'")
        elif content_filter == "stale":
            joins.append(
                "JOIN showroom_analysis sa_stale ON sa_stale.ci_name = ci.ci_name "
                "AND sa_stale.is_stale = TRUE"
            )
        elif content_filter == "needs_review":
            joins.append(
                "JOIN showroom_analysis sa_review ON sa_review.ci_name = ci.ci_name "
                "AND sa_review.enrichment_review_needed = TRUE"
            )

        join_sql = "\n".join(joins)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        count_sql = f"""
            SELECT COUNT(DISTINCT ci.ci_name)
            FROM catalog_items ci
            LEFT JOIN showroom_analysis sa ON sa.ci_name = ci.ci_name
            {join_sql}
            {where}
        """

        data_sql = f"""
            SELECT DISTINCT ci.*, sa.is_stale, sa.enrichment_review_needed
            FROM catalog_items ci
            LEFT JOIN showroom_analysis sa ON sa.ci_name = ci.ci_name
            {join_sql}
            {where}
            ORDER BY ci.ci_name
            LIMIT %(limit)s OFFSET %(offset)s
        """
        params["limit"] = limit
        params["offset"] = offset

        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(count_sql, params)
                total = cur.fetchone()["count"]
                cur.execute(data_sql, params)
                items = cur.fetchall()

        return {"items": items, "total": total}

    def delete_removed_items(self, current_ci_names: set[str]) -> list[dict]:
        with self._pool.connection() as conn:
            cur = conn.execute("SELECT ci_name, display_name, stage FROM catalog_items")
            all_items = cur.fetchall()
            removed = [i for i in all_items if i["ci_name"] not in current_ci_names]
            for item in removed:
                ci = item["ci_name"]
                conn.execute("DELETE FROM enrichment_tags WHERE ci_name = %s", (ci,))
                conn.execute("DELETE FROM embeddings WHERE ci_name = %s", (ci,))
                conn.execute("DELETE FROM analysis_log WHERE ci_name = %s", (ci,))
                conn.execute("DELETE FROM showroom_analysis WHERE ci_name = %s", (ci,))
                conn.execute("DELETE FROM catalog_items WHERE ci_name = %s", (ci,))
            if removed:
                conn.commit()
            return removed

    def set_content_path(self, ci_name: str, path: str | None):
        with self._pool.connection() as conn:
            conn.execute(
                "UPDATE catalog_items SET content_path = %s WHERE ci_name = %s",
                (path, ci_name),
            )
            conn.commit()

    # ── Showroom analysis ──

    def upsert_showroom_analysis(self, analysis: dict[str, Any]):
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
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM showroom_analysis WHERE ci_name = %(ci_name)s",
                    {"ci_name": ci_name},
                )
                return cur.fetchone()

    def mark_stale(self, ci_name: str, new_commit: str | None = None) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "UPDATE showroom_analysis SET is_stale = TRUE, stale_commit = %s WHERE ci_name = %s",
                (new_commit, ci_name),
            )
            conn.commit()

    def mark_all_stale(self) -> int:
        with self._pool.connection() as conn:
            cur = conn.execute("UPDATE showroom_analysis SET is_stale = TRUE WHERE is_stale = FALSE")
            conn.commit()
            return cur.rowcount

    def clear_stale(self, ci_name: str) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "UPDATE showroom_analysis SET is_stale = FALSE, stale_commit = NULL WHERE ci_name = %s",
                (ci_name,),
            )
            conn.commit()

    # ── Embeddings ──

    def clear_embeddings(self, ci_name: str):
        with self._pool.connection() as conn:
            conn.execute("DELETE FROM embeddings WHERE ci_name = %s", (ci_name,))
            conn.commit()

    def store_embedding(
        self, ci_name: str, embed_type: str, content_text: str,
        embedding: list[float], module_title: str | None = None,
    ):
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                if module_title:
                    cur.execute(
                        "DELETE FROM embeddings WHERE ci_name = %s AND embed_type = %s AND module_title = %s",
                        (ci_name, embed_type, module_title),
                    )
                else:
                    cur.execute(
                        "DELETE FROM embeddings WHERE ci_name = %s AND embed_type = %s AND module_title IS NULL",
                        (ci_name, embed_type),
                    )
                cur.execute(
                    """INSERT INTO embeddings (ci_name, embed_type, module_title, content_text, embedding)
                       VALUES (%s, %s, %s, %s, %s::vector)""",
                    (ci_name, embed_type, module_title, content_text,
                     f"[{','.join(str(v) for v in embedding)}]"),
                )
            conn.commit()

    def search_embeddings(
        self, query_embedding: list[float], limit: int = 25,
        stages: list[str] | None = None, embed_type: str = "ci_summary",
        include_zt: bool = True,
    ) -> list[dict[str, Any]]:
        stage_list = stages or ["prod"]
        stage_placeholders = ",".join(["%s"] * len(stage_list))
        stage_filter = f"AND ci.stage IN ({stage_placeholders})"
        zt_filter = "" if include_zt else "AND ci.catalog_namespace NOT LIKE 'zt-%%' AND ci.ci_name NOT LIKE 'zt-%%'"
        sql = f"""
            SELECT e.ci_name, e.content_text, e.module_title,
                   e.embedding <=> %s::vector AS distance,
                   ci.display_name, ci.category, ci.stage,
                   ci.showroom_url, ci.showroom_ref,
                   ci.is_published, ci.published_ci_name, ci.base_ci_name,
                   ci.catalog_namespace, sa.content_hash
            FROM embeddings e
            JOIN catalog_items ci ON e.ci_name = ci.ci_name
            LEFT JOIN showroom_analysis sa ON sa.ci_name = ci.ci_name
            WHERE e.embed_type = %s {stage_filter} {zt_filter}
            ORDER BY distance ASC
            LIMIT %s
        """
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (
                    f"[{','.join(str(v) for v in query_embedding)}]",
                    embed_type, *stage_list, limit,
                ))
                return cur.fetchall()

    # ── Enrichment ──

    def add_enrichment_tag(self, ci_name: str, tag_type: str, tag_value: str, added_by: str | None = None) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "INSERT INTO enrichment_tags (ci_name, tag_type, tag_value, added_by) VALUES (%s, %s, %s, %s) ON CONFLICT (ci_name, tag_type, tag_value) DO NOTHING",
                (ci_name, tag_type, tag_value, added_by),
            )
            conn.commit()

    def remove_enrichment_tag(self, ci_name: str, tag_type: str, tag_value: str) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "DELETE FROM enrichment_tags WHERE ci_name = %s AND tag_type = %s AND tag_value = %s",
                (ci_name, tag_type, tag_value),
            )
            conn.commit()

    def remove_enrichment_tag_by_id(self, tag_id: int) -> None:
        with self._pool.connection() as conn:
            conn.execute("DELETE FROM enrichment_tags WHERE id = %s", (tag_id,))
            conn.commit()

    def get_enrichment_tags(self, ci_name: str) -> list[dict]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT id, tag_type, tag_value, added_by, added_at FROM enrichment_tags WHERE ci_name = %s ORDER BY added_at",
                (ci_name,),
            )
            return cur.fetchall()

    def get_enrichment_tags_for_items(self, ci_names: list[str]) -> dict[str, list[dict]]:
        if not ci_names:
            return {}
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT ci_name, id, tag_type, tag_value, added_by FROM enrichment_tags WHERE ci_name = ANY(%s) ORDER BY ci_name, added_at",
                (ci_names,),
            )
            result: dict[str, list] = {name: [] for name in ci_names}
            for row in cur.fetchall():
                result[row["ci_name"]].append(row)
            return result

    def set_enrichment_note(self, ci_name: str, note: str, updated_by: str | None = None) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "UPDATE showroom_analysis SET notes = %s WHERE ci_name = %s", (note, ci_name),
            )
            if conn.execute("SELECT 1").fetchone():
                pass
            conn.commit()

    def set_enrichment_review_flag(self, ci_name: str, needed: bool) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "UPDATE showroom_analysis SET enrichment_review_needed = %s WHERE ci_name = %s",
                (needed, ci_name),
            )
            conn.commit()

    def set_curated_duration(self, ci_name: str, duration_min: int | None, updated_by: str | None = None) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "UPDATE showroom_analysis SET curated_duration_min = %s WHERE ci_name = %s",
                (duration_min, ci_name),
            )
            conn.commit()
        logger.info("curated_duration_set", ci_name=ci_name, duration_min=duration_min, updated_by=updated_by)

    # ── Infrastructure metadata (workloads, ACL groups, mapping) ──

    def sync_workloads(self, ci_name: str, workloads: list[dict]) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "DELETE FROM catalog_item_workloads WHERE ci_name = %s", (ci_name,)
            )
            for w in workloads:
                conn.execute(
                    "INSERT INTO catalog_item_workloads (ci_name, workload_fqcn, workload_role, workload_collection) "
                    "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                    (ci_name, w["fqcn"], w["role"], w.get("collection")),
                )
            conn.commit()

    def sync_acl_groups(self, ci_name: str, groups: list[str]) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "DELETE FROM catalog_item_acl_groups WHERE ci_name = %s", (ci_name,)
            )
            for g in groups:
                conn.execute(
                    "INSERT INTO catalog_item_acl_groups (ci_name, group_name) "
                    "VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (ci_name, g),
                )
            conn.commit()

    def get_workloads(self, ci_name: str) -> list[dict]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT workload_fqcn, workload_role, workload_collection "
                "FROM catalog_item_workloads WHERE ci_name = %s ORDER BY workload_role",
                (ci_name,),
            )
            return cur.fetchall()

    def get_acl_groups(self, ci_name: str) -> list[str]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT group_name FROM catalog_item_acl_groups "
                "WHERE ci_name = %s ORDER BY group_name",
                (ci_name,),
            )
            return [row["group_name"] for row in cur.fetchall()]

    def upsert_workload_mapping(
        self, workload_role: str, product_name: str,
        description: str | None = None, category: str | None = None,
        source_collection: str | None = None, verified: bool = False,
        added_by: str | None = None,
    ) -> None:
        with self._pool.connection() as conn:
            now = datetime.now(timezone.utc)
            conn.execute(
                "INSERT INTO workload_mapping "
                "(workload_role, product_name, description, category, source_collection, verified, added_by, added_at, verified_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (workload_role) DO UPDATE SET "
                "product_name = EXCLUDED.product_name, description = EXCLUDED.description, "
                "category = EXCLUDED.category, source_collection = EXCLUDED.source_collection, "
                "verified = EXCLUDED.verified, verified_at = EXCLUDED.verified_at",
                (workload_role, product_name, description, category, source_collection,
                 verified, added_by, now, now if verified else None),
            )
            conn.commit()

    def delete_workload_mapping(self, workload_role: str) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "DELETE FROM workload_mapping WHERE workload_role = %s",
                (workload_role,),
            )
            conn.commit()

    def list_workload_mappings(self) -> list[dict]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT * FROM workload_mapping ORDER BY product_name"
            )
            return cur.fetchall()

    def get_unmapped_workloads(self) -> list[dict]:
        with self._pool.connection() as conn:
            cur = conn.execute("""
                SELECT ciw.workload_role, ciw.workload_collection,
                       COUNT(DISTINCT ciw.ci_name) AS ci_count
                FROM catalog_item_workloads ciw
                LEFT JOIN workload_mapping wm ON wm.workload_role = ciw.workload_role
                WHERE wm.id IS NULL
                GROUP BY ciw.workload_role, ciw.workload_collection
                ORDER BY ci_count DESC
            """)
            return cur.fetchall()

    def upsert_workload_alias(self, product_name: str, alias: str) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "INSERT INTO workload_aliases (product_name, alias) "
                "VALUES (%s, %s) ON CONFLICT (alias) DO NOTHING",
                (product_name, alias),
            )
            conn.commit()

    def list_workload_aliases(self) -> list[dict]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT * FROM workload_aliases ORDER BY product_name, alias"
            )
            return cur.fetchall()

    def _resolve_workload_aliases(self, names: list[str]) -> list[str]:
        if not names:
            return names
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT alias, product_name FROM workload_aliases WHERE alias = ANY(%s)",
                (names,),
            )
            alias_map = {row["alias"]: row["product_name"] for row in cur.fetchall()}
        return [alias_map.get(n, n) for n in names]

    def get_infra_stats(self) -> dict:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS count FROM catalog_items WHERE is_agd_v2 = TRUE")
                v2_items = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(DISTINCT ci_name) AS count FROM catalog_item_workloads")
                with_workloads = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(*) AS count FROM workload_mapping")
                mapped_count = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(*) AS count FROM workload_mapping WHERE verified = TRUE")
                verified_count = cur.fetchone()["count"]
                cur.execute("""
                    SELECT COUNT(DISTINCT ciw.workload_role) AS count
                    FROM catalog_item_workloads ciw
                    LEFT JOIN workload_mapping wm ON wm.workload_role = ciw.workload_role
                    WHERE wm.id IS NULL
                """)
                unmapped_count = cur.fetchone()["count"]
        return {
            "v2_items": v2_items,
            "with_workloads": with_workloads,
            "mapped_workloads": mapped_count,
            "verified_workloads": verified_count,
            "unmapped_workloads": unmapped_count,
        }

    def search_by_infrastructure(
        self,
        workloads: list[str] | None = None,
        agd_config: str | None = None,
        cloud_provider: str | None = None,
        ocp_version: str | None = None,
        os_image: str | None = None,
        stage: str | None = None,
        prod_only: bool = True,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        conditions = ["ci.is_agd_v2 = TRUE"]
        params: dict[str, Any] = {}
        joins = []

        if prod_only:
            conditions.append("ci.is_prod = TRUE")
        if stage:
            conditions.append("ci.stage = %(stage)s")
            params["stage"] = stage
        if agd_config:
            conditions.append("ci.agd_config = %(agd_config)s")
            params["agd_config"] = agd_config
        if cloud_provider:
            conditions.append("ci.cloud_provider = %(cloud_provider)s")
            params["cloud_provider"] = cloud_provider
        if ocp_version:
            conditions.append("ci.ocp_version LIKE %(ocp_version)s")
            params["ocp_version"] = f"{ocp_version}%"
        if os_image:
            conditions.append("ci.os_image LIKE %(os_image)s")
            params["os_image"] = f"{os_image}%"

        if workloads:
            resolved = self._resolve_workload_aliases(workloads)
            for i, wl in enumerate(resolved):
                alias_w = f"w{i}"
                alias_m = f"m{i}"
                joins.append(
                    f"JOIN catalog_item_workloads {alias_w} "
                    f"ON {alias_w}.ci_name = ci.ci_name "
                    f"JOIN workload_mapping {alias_m} "
                    f"ON {alias_m}.workload_role = {alias_w}.workload_role "
                    f"AND {alias_m}.product_name = %({alias_m}_name)s"
                )
                params[f"{alias_m}_name"] = wl

        join_sql = "\n".join(joins)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        sql = f"""
            SELECT DISTINCT ci.*, sa.summary, sa.content_type,
                   sa.estimated_duration_min, sa.difficulty
            FROM catalog_items ci
            LEFT JOIN showroom_analysis sa ON sa.ci_name = ci.ci_name
            {join_sql}
            {where}
            ORDER BY ci.display_name
            LIMIT %(limit)s
        """
        params["limit"] = limit

        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()

    # ── Content similarity ──

    def compute_content_similarity(self, threshold: float = 0.75, stage: str = "prod") -> dict[str, int]:
        """Compute pairwise cosine similarity between catalog items in a given stage.

        Compares items within the same stage only — prod vs prod, event vs event,
        or dev vs dev. Published VCIs are always excluded (they have no Showroom
        content of their own).
        """
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM content_similarity")

                cur.execute("""
                    INSERT INTO content_similarity (ci_name_a, ci_name_b, similarity_score, computed_at)
                    SELECT a.ci_name, b.ci_name,
                           1.0 - (a.embedding <=> b.embedding) AS similarity,
                           NOW()
                    FROM embeddings a
                    JOIN embeddings b ON a.ci_name < b.ci_name
                    JOIN catalog_items ci_a ON ci_a.ci_name = a.ci_name
                    JOIN catalog_items ci_b ON ci_b.ci_name = b.ci_name
                    WHERE a.embed_type = 'ci_summary'
                      AND b.embed_type = 'ci_summary'
                      AND 1.0 - (a.embedding <=> b.embedding) >= %(threshold)s
                      AND ci_a.stage = %(stage)s
                      AND ci_b.stage = %(stage)s
                      AND (ci_a.is_published IS NULL OR ci_a.is_published = FALSE)
                      AND (ci_b.is_published IS NULL OR ci_b.is_published = FALSE)
                """, {"threshold": threshold, "stage": stage})
                inserted = cur.rowcount
            conn.commit()

        logger.info("content_similarity_computed", pairs_stored=inserted, threshold=threshold, stage=stage)
        return {"pairs_stored": inserted, "threshold": threshold, "stage": stage}

    def get_similar_items(self, ci_name: str, min_score: float = 0.75) -> list[dict[str, Any]]:
        sql = """
            SELECT cs.ci_name_a, cs.ci_name_b, cs.similarity_score, cs.computed_at,
                   ci.display_name, ci.category, ci.stage, sa.summary
            FROM content_similarity cs
            JOIN catalog_items ci ON ci.ci_name = CASE
                WHEN cs.ci_name_a = %(ci_name)s THEN cs.ci_name_b
                ELSE cs.ci_name_a END
            LEFT JOIN showroom_analysis sa ON sa.ci_name = ci.ci_name
            WHERE (cs.ci_name_a = %(ci_name)s OR cs.ci_name_b = %(ci_name)s)
              AND cs.similarity_score >= %(min_score)s
            ORDER BY cs.similarity_score DESC
        """
        with self._pool.connection() as conn:
            cur = conn.execute(sql, {"ci_name": ci_name, "min_score": min_score})
            rows = cur.fetchall()

        results = []
        for row in rows:
            other_ci = row["ci_name_b"] if row["ci_name_a"] == ci_name else row["ci_name_a"]
            results.append({
                "ci_name": other_ci,
                "display_name": row["display_name"],
                "category": row["category"],
                "stage": row["stage"],
                "summary": row["summary"],
                "similarity_score": round(row["similarity_score"], 4),
                "computed_at": row["computed_at"],
            })
        return results

    def get_overlap_report(self, min_score: float = 0.75) -> list[dict[str, Any]]:
        sql = """
            SELECT cs.ci_name_a, cs.ci_name_b, cs.similarity_score, cs.computed_at,
                   ci_a.display_name AS display_name_a, ci_a.category AS category_a, ci_a.stage AS stage_a,
                   sa_a.summary AS summary_a,
                   ci_b.display_name AS display_name_b, ci_b.category AS category_b, ci_b.stage AS stage_b,
                   sa_b.summary AS summary_b
            FROM content_similarity cs
            JOIN catalog_items ci_a ON ci_a.ci_name = cs.ci_name_a
            JOIN catalog_items ci_b ON ci_b.ci_name = cs.ci_name_b
            LEFT JOIN showroom_analysis sa_a ON sa_a.ci_name = cs.ci_name_a
            LEFT JOIN showroom_analysis sa_b ON sa_b.ci_name = cs.ci_name_b
            WHERE cs.similarity_score >= %(min_score)s
            ORDER BY cs.similarity_score DESC
        """
        with self._pool.connection() as conn:
            cur = conn.execute(sql, {"min_score": min_score})
            return cur.fetchall()

    def get_similarity_stats(self) -> dict[str, Any]:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS count FROM content_similarity")
                total_pairs = cur.fetchone()["count"]
                cur.execute("SELECT MAX(computed_at) AS last_computed FROM content_similarity")
                last = cur.fetchone()["last_computed"]
                cur.execute("SELECT COUNT(*) AS count FROM content_similarity WHERE similarity_score >= 0.85")
                high_overlap = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(*) AS count FROM content_similarity WHERE similarity_score >= 0.75 AND similarity_score < 0.85")
                related = cur.fetchone()["count"]
        return {
            "total_pairs": total_pairs,
            "high_overlap": high_overlap,
            "related": related,
            "last_computed": last,
        }

    # ── Workload scan state ──

    def get_scan_state(self, collection: str) -> dict | None:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT * FROM workload_scan_state WHERE collection = %s",
                (collection,),
            )
            return cur.fetchone()

    def upsert_scan_state(self, collection: str, last_sha: str) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "INSERT INTO workload_scan_state (collection, last_sha, last_scanned) "
                "VALUES (%s, %s, %s) "
                "ON CONFLICT (collection) DO UPDATE SET last_sha = EXCLUDED.last_sha, last_scanned = EXCLUDED.last_scanned",
                (collection, last_sha, datetime.now(timezone.utc)),
            )
            conn.commit()

    # ── Token usage ──

    def log_token_usage(
        self, operation: str, model: str, input_tokens: int, output_tokens: int,
        ci_name: str | None = None, query_text: str | None = None,
    ) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                """INSERT INTO token_usage (operation, model, input_tokens, output_tokens, ci_name, query_text)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (operation, model, input_tokens, output_tokens, ci_name, query_text),
            )
            conn.commit()

    def get_token_stats(self, days: int | None = 30) -> list[dict[str, Any]]:
        where = "WHERE created_at >= NOW() - %(days)s * INTERVAL '1 day'" if days else ""
        params: dict[str, Any] = {"days": days} if days else {}
        sql = f"""
            SELECT operation, model, COUNT(*) AS calls,
                   SUM(input_tokens) AS input_tokens,
                   SUM(output_tokens) AS output_tokens,
                   SUM(input_tokens + output_tokens) AS total_tokens
            FROM token_usage {where}
            GROUP BY operation, model ORDER BY total_tokens DESC
        """
        with self._pool.connection() as conn:
            cur = conn.execute(sql, params)
            return cur.fetchall()

    def get_recent_queries(self, days: int | None = 30, limit: int = 50) -> list[dict[str, Any]]:
        time_filter = "AND created_at >= NOW() - %(days)s * INTERVAL '1 day'" if days else ""
        params: dict[str, Any] = {"days": days, "limit": limit} if days else {"limit": limit}
        sql = f"""
            SELECT query_text, date_trunc('minute', created_at) AS query_time,
                   SUM(CASE WHEN operation = 'triage' THEN input_tokens ELSE 0 END) AS triage_input,
                   SUM(CASE WHEN operation = 'triage' THEN output_tokens ELSE 0 END) AS triage_output,
                   SUM(CASE WHEN operation = 'rationale' THEN input_tokens ELSE 0 END) AS rationale_input,
                   SUM(CASE WHEN operation = 'rationale' THEN output_tokens ELSE 0 END) AS rationale_output,
                   SUM(input_tokens + output_tokens) AS total_tokens
            FROM token_usage
            WHERE operation IN ('triage', 'rationale') AND query_text IS NOT NULL {time_filter}
            GROUP BY query_text, date_trunc('minute', created_at)
            ORDER BY query_time DESC LIMIT %(limit)s
        """
        with self._pool.connection() as conn:
            cur = conn.execute(sql, params)
            return cur.fetchall()

    # ── Scan management ──

    def get_items_needing_analysis(self) -> list[dict[str, Any]]:
        with self._pool.connection() as conn:
            cur = conn.execute("""
                SELECT ci.* FROM catalog_items ci
                LEFT JOIN showroom_analysis sa ON ci.ci_name = sa.ci_name
                WHERE ci.showroom_url IS NOT NULL AND ci.showroom_url != ''
                  AND (ci.is_published IS NULL OR ci.is_published = FALSE)
                  AND (sa.ci_name IS NULL OR sa.is_stale = TRUE)
                ORDER BY ci.ci_name
            """)
            all_needing = cur.fetchall()

        groups: dict[tuple, list[dict]] = {}
        for item in all_needing:
            key = (item.get("showroom_url_override") or item["showroom_url"], item.get("showroom_ref") or "")
            groups.setdefault(key, []).append(item)

        deduped = []
        for group in groups.values():
            group.sort(key=lambda i: STAGE_PRIORITY.get(i.get("stage", "dev"), 99))
            deduped.append(group[0])
        deduped.sort(key=lambda i: i.get("ci_name", ""))
        return deduped

    def get_scan_dedup_stats(self) -> dict[str, int]:
        """Return total scannable, unique (url, ref) pairs, and propagated sibling count."""
        with self._pool.connection() as conn:
            cur = conn.execute("""
                SELECT COALESCE(ci.showroom_url_override, ci.showroom_url) AS effective_url,
                       COALESCE(ci.showroom_ref, '') AS showroom_ref, COUNT(*) AS cnt
                FROM catalog_items ci
                LEFT JOIN showroom_analysis sa ON ci.ci_name = sa.ci_name
                WHERE ci.showroom_url IS NOT NULL AND ci.showroom_url != ''
                  AND (ci.is_published IS NULL OR ci.is_published = FALSE)
                  AND (sa.ci_name IS NULL OR sa.is_stale = TRUE)
                GROUP BY COALESCE(ci.showroom_url_override, ci.showroom_url), COALESCE(ci.showroom_ref, '')
            """)
            groups = cur.fetchall()
        total = sum(row["cnt"] for row in groups)
        unique = len(groups)
        propagated = total - unique
        return {"total_scannable": total, "unique_pairs": unique, "will_propagate": propagated}

    def get_siblings_by_showroom(self, showroom_url: str, showroom_ref: str | None) -> list[dict[str, Any]]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT * FROM catalog_items WHERE showroom_url = %s AND COALESCE(showroom_ref, '') = COALESCE(%s, '') AND (is_published IS NULL OR is_published = FALSE) ORDER BY ci_name",
                (showroom_url, showroom_ref),
            )
            return cur.fetchall()

    def set_scan_status(self, ci_name: str, status: str, error_class: str | None = None, error_message: str | None = None):
        with self._pool.connection() as conn:
            if status == "success":
                conn.execute(
                    "UPDATE catalog_items SET scan_status = 'success', scan_error_class = NULL, scan_error = NULL, scan_failed_at = NULL WHERE ci_name = %s",
                    (ci_name,),
                )
            else:
                conn.execute(
                    "UPDATE catalog_items SET scan_status = %s, scan_error_class = %s, scan_error = %s, scan_failed_at = %s WHERE ci_name = %s",
                    (status, error_class, error_message, datetime.now(timezone.utc), ci_name),
                )
            conn.commit()

    def get_scan_failures(self) -> list[dict]:
        with self._pool.connection() as conn:
            cur = conn.execute("""
                SELECT ci_name, display_name, stage, scan_error_class, scan_error, scan_failed_at, showroom_url, showroom_url_override
                FROM catalog_items WHERE scan_status = 'failed' ORDER BY scan_failed_at DESC
            """)
            return cur.fetchall()

    def set_showroom_url_override(self, ci_name: str, override_url: str | None):
        with self._pool.connection() as conn:
            conn.execute("UPDATE catalog_items SET showroom_url_override = %s WHERE ci_name = %s", (override_url, ci_name))
            conn.commit()

    # ── Status / currency ──

    def get_status_summary(self) -> dict[str, int]:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) as count FROM catalog_items")
                total = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(*) as count FROM catalog_items WHERE is_prod = TRUE")
                prod = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(*) as count FROM catalog_items WHERE showroom_url IS NOT NULL AND showroom_url != '' AND (is_published IS NULL OR is_published = FALSE)")
                with_showroom = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(*) as count FROM showroom_analysis")
                analyzed = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(*) as count FROM showroom_analysis WHERE is_stale = TRUE")
                stale = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(*) as count FROM catalog_items WHERE scan_status = 'failed'")
                scan_failures = cur.fetchone()["count"]
        return {"total": total, "prod": prod, "with_showroom": with_showroom, "analyzed": analyzed, "stale": stale, "scan_failures": scan_failures}

    def get_db_currency(self, stale_days: int = 3) -> dict:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT MAX(last_refreshed) as max_refreshed FROM catalog_items")
                row = cur.fetchone()
                last_refresh = row["max_refreshed"] if row else None
                catalog_stale = True
                catalog_date = "never"
                if last_refresh:
                    catalog_stale = (datetime.now(timezone.utc) - last_refresh) > timedelta(days=stale_days)
                    catalog_date = last_refresh.strftime("%Y.%m.%d")
                cur.execute("SELECT COUNT(*) as count FROM catalog_items WHERE showroom_url IS NOT NULL AND showroom_url != '' AND (is_published IS NULL OR is_published = FALSE)")
                scannable = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(*) as count FROM showroom_analysis")
                analyzed = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(*) as count FROM showroom_analysis WHERE is_stale = TRUE")
                stale_count = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(*) as count FROM catalog_items WHERE scan_status = 'failed'")
                failed_count = cur.fetchone()["count"]
                cur.execute("SELECT MAX(last_analyzed) as max_analyzed FROM showroom_analysis")
                row = cur.fetchone()
                last_analyzed = row["max_analyzed"] if row else None
        unanalyzed = max(0, scannable - analyzed - failed_count)
        incomplete = stale_count + unanalyzed + failed_count
        analysis_stale = (incomplete / scannable > 0.10) if scannable > 0 else True
        analysis_date = last_analyzed.strftime("%Y.%m.%d") if last_analyzed else "never"
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) as count FROM catalog_items")
                total = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(*) as count FROM catalog_items WHERE is_prod = TRUE")
                prod = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(*) as count FROM catalog_items WHERE stage = 'dev'")
                dev = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(*) as count FROM catalog_items WHERE stage = 'event'")
                event = cur.fetchone()["count"]
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) as cnt FROM (
                        SELECT DISTINCT COALESCE(ci.showroom_url_override, ci.showroom_url), COALESCE(ci.showroom_ref, '')
                        FROM catalog_items ci
                        WHERE ci.showroom_url IS NOT NULL AND ci.showroom_url != ''
                          AND (ci.is_published IS NULL OR ci.is_published = FALSE)
                    ) sub
                """)
                unique_showrooms = cur.fetchone()["cnt"]
        return {
            "total": total, "prod": prod, "dev": dev, "event": event,
            "scannable": scannable, "unique_showrooms": unique_showrooms, "analyzed": analyzed,
            "last_refresh": catalog_date, "is_stale": catalog_stale,
            "catalog_stale": catalog_stale, "catalog_date": catalog_date,
            "analysis_stale": analysis_stale, "analysis_date": analysis_date,
            "unanalyzed": unanalyzed, "stale_count": stale_count, "failed_count": failed_count,
        }

    # ── Advisor sessions ──

    def log_advisor_session(
        self, session_id: str, turn_index: int, user_email: str | None,
        query_text: str | None, event_url: str | None,
        results: list[dict], overall_assessment: str | None,
        opted_out: bool = False,
    ) -> int:
        if opted_out:
            query_text = None
            results = None
            overall_assessment = None
        with self._pool.connection() as conn:
            cur = conn.execute("""
                INSERT INTO advisor_sessions (session_id, turn_index, user_email, query_text, event_url, results_json, overall_assessment, opted_out)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (session_id, turn_index, user_email, query_text, event_url,
                  Jsonb(results) if results is not None else None, overall_assessment, opted_out))
            row_id = cur.fetchone()["id"]
            conn.commit()
        return row_id

    def update_advisor_session_choice(self, session_id: str, turn_index: int, chosen_ci_name: str) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "UPDATE advisor_sessions SET chosen_ci_name = %s, chosen_at = NOW() WHERE session_id = %s AND turn_index = %s",
                (chosen_ci_name, session_id, turn_index),
            )
            conn.commit()

    def list_advisor_sessions(self, user_email: str | None = None, limit: int = 50) -> list[dict]:
        if user_email:
            sql = "SELECT DISTINCT session_id, MIN(created_at) as started_at, COUNT(*) as turns FROM advisor_sessions WHERE user_email = %s GROUP BY session_id ORDER BY started_at DESC LIMIT %s"
            params = (user_email, limit)
        else:
            sql = "SELECT DISTINCT session_id, MIN(created_at) as started_at, COUNT(*) as turns FROM advisor_sessions GROUP BY session_id ORDER BY started_at DESC LIMIT %s"
            params = (limit,)
        with self._pool.connection() as conn:
            cur = conn.execute(sql, params)
            return cur.fetchall()

    def get_advisor_session(self, session_id: str) -> list[dict]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT * FROM advisor_sessions WHERE session_id = %s ORDER BY turn_index",
                (session_id,),
            )
            return cur.fetchall()

    # ── Audit log ──

    def log_action(self, ci_name: str, action: str, user_id: str | None = None, details: str | None = None):
        with self._pool.connection() as conn:
            conn.execute(
                "INSERT INTO analysis_log (ci_name, action, user_id, details) VALUES (%s, %s, %s, %s)",
                (ci_name, action, user_id, details),
            )
            conn.commit()

    # ── Jobs ──

    def create_job(self, job_type: str, queue: str, created_by: str | None = None) -> str:
        job_id = str(uuid.uuid4())
        with self._pool.connection() as conn:
            conn.execute(
                "INSERT INTO jobs (id, job_type, status, queue, created_by, created_at) VALUES (%s, %s, 'queued', %s, %s, %s)",
                (job_id, job_type, queue, created_by, datetime.now(timezone.utc)),
            )
            conn.commit()
        return job_id

    def get_job(self, job_id: str) -> dict | None:
        with self._pool.connection() as conn:
            cur = conn.execute("SELECT * FROM jobs WHERE id = %s", (job_id,))
            return cur.fetchone()

    def update_job_status(self, job_id: str, status: str, progress_json: dict | None = None) -> None:
        with self._pool.connection() as conn:
            if status == "running":
                conn.execute(
                    "UPDATE jobs SET status = %s, started_at = %s, progress_json = %s WHERE id = %s",
                    (status, datetime.now(timezone.utc), Jsonb(progress_json) if progress_json else None, job_id),
                )
            else:
                conn.execute(
                    "UPDATE jobs SET status = %s, progress_json = %s WHERE id = %s",
                    (status, Jsonb(progress_json) if progress_json else None, job_id),
                )
            conn.commit()

    def append_job_progress(self, job_id: str, progress: dict) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                """UPDATE jobs
                   SET status = 'running',
                       started_at = COALESCE(started_at, %s),
                       progress_json = jsonb_set(
                           COALESCE(progress_json, '{"messages":[]}'),
                           '{messages}',
                           COALESCE(progress_json->'messages', '[]'::jsonb) || %s::jsonb
                       )
                   WHERE id = %s""",
                (datetime.now(timezone.utc), Jsonb(progress), job_id),
            )
            conn.commit()

    def complete_job(self, job_id: str, result_json: dict | None = None, error: str | None = None) -> None:
        status = "failed" if error else "complete"
        with self._pool.connection() as conn:
            conn.execute(
                "UPDATE jobs SET status = %s, result_json = %s, error = %s, completed_at = %s WHERE id = %s",
                (status, Jsonb(result_json) if result_json else None, error, datetime.now(timezone.utc), job_id),
            )
            conn.commit()

    def fail_job(self, job_id: str, error: str) -> None:
        self.complete_job(job_id, error=error)

    def list_jobs(self, limit: int = 50, job_type: str | None = None) -> list[dict]:
        if job_type:
            sql = "SELECT * FROM jobs WHERE job_type = %s ORDER BY created_at DESC LIMIT %s"
            params = (job_type, limit)
        else:
            sql = "SELECT * FROM jobs ORDER BY created_at DESC LIMIT %s"
            params = (limit,)
        with self._pool.connection() as conn:
            cur = conn.execute(sql, params)
            return cur.fetchall()
