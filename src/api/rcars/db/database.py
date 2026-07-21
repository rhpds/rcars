"""PostgreSQL + pgvector database layer for RCARS v2."""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from urllib.parse import urlsplit
from datetime import datetime, timedelta, timezone
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

import structlog

from rcars.config import STAGE_PRIORITY

logger = structlog.get_logger()

SCHEMA_SQL = """
-- ═══════════════════════════════════════════════════════════════════
-- content_entities — universal entity registry (replaces catalog_items)
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS content_entities (
    content_id      TEXT PRIMARY KEY,
    source          TEXT NOT NULL,
    content_type    TEXT NOT NULL,
    is_hands_on     BOOLEAN NOT NULL DEFAULT FALSE,

    display_name    TEXT NOT NULL,
    summary         TEXT,
    products_json   JSONB,
    topics_json     JSONB,
    audience_json   JSONB,
    difficulty      TEXT,

    retired_at      TIMESTAMPTZ,
    retirement_reason TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ce_source ON content_entities(source);
CREATE INDEX IF NOT EXISTS idx_ce_content_type ON content_entities(content_type);
CREATE INDEX IF NOT EXISTS idx_ce_retired ON content_entities(retired_at);
CREATE INDEX IF NOT EXISTS idx_ce_products ON content_entities USING gin(products_json);

-- ═══════════════════════════════════════════════════════════════════
-- babylon_items — Babylon-specific extension (1:1 with content_entities)
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS babylon_items (
    content_id      TEXT PRIMARY KEY REFERENCES content_entities(content_id) ON DELETE CASCADE,
    ci_name         TEXT NOT NULL UNIQUE,

    category        TEXT,
    stage           TEXT,
    catalog_namespace TEXT,
    is_prod         BOOLEAN DEFAULT FALSE,
    is_published    BOOLEAN DEFAULT FALSE,
    published_ci_name TEXT,
    base_ci_name    TEXT,

    showroom_url    TEXT,
    showroom_ref    TEXT,
    content_path    TEXT,
    showroom_url_override TEXT,

    is_agd_v2       BOOLEAN DEFAULT FALSE,
    agd_config      TEXT,
    cloud_provider  TEXT,
    ocp_version     TEXT,
    os_image        TEXT,
    worker_instance_count TEXT,
    control_plane_instance_count TEXT,
    instances_json  JSONB,

    keywords        TEXT[],
    description     TEXT,
    owners_json     JSONB,
    icon_url        TEXT,
    last_crd_update TIMESTAMPTZ,
    last_refreshed  TIMESTAMPTZ DEFAULT NOW(),

    scan_status     TEXT NOT NULL DEFAULT 'not_scanned',
    scan_error_class TEXT,
    scan_error      TEXT,
    scan_failed_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_bi_ci_name ON babylon_items(ci_name);
CREATE INDEX IF NOT EXISTS idx_bi_stage ON babylon_items(stage);
CREATE INDEX IF NOT EXISTS idx_bi_is_prod ON babylon_items(is_prod);
CREATE INDEX IF NOT EXISTS idx_bi_showroom_url ON babylon_items(showroom_url);
CREATE INDEX IF NOT EXISTS idx_bi_cloud_provider ON babylon_items(cloud_provider);
CREATE INDEX IF NOT EXISTS idx_bi_category ON babylon_items(category);

-- ═══════════════════════════════════════════════════════════════════
-- showroom_analysis — re-keyed from ci_name to content_id
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS showroom_analysis (
    content_id              TEXT PRIMARY KEY REFERENCES content_entities(content_id) ON DELETE CASCADE,

    summary                 TEXT,
    products_json           JSONB,
    topics_json             JSONB,
    audience_json           JSONB,
    difficulty              TEXT,
    content_hash            TEXT,
    last_analyzed           TIMESTAMPTZ,
    is_stale                BOOLEAN DEFAULT FALSE,
    stale_commit            TEXT,

    content_type            TEXT,
    modules_json            JSONB,
    learning_objectives_json JSONB,
    estimated_duration_min  INTEGER,
    curated_duration_min    INTEGER CHECK (curated_duration_min >= 0),
    format_suitability_json JSONB,
    use_cases_json          JSONB,

    last_repo_commit        TEXT,
    last_repo_updated       TIMESTAMPTZ,

    enrichment_review_needed BOOLEAN DEFAULT FALSE,
    review_reasons           JSONB,
    notes                   TEXT
);

-- ═══════════════════════════════════════════════════════════════════
-- embeddings — re-keyed, new content_type and source columns
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS embeddings (
    id              SERIAL PRIMARY KEY,
    content_id      TEXT NOT NULL REFERENCES content_entities(content_id) ON DELETE CASCADE,
    content_type    TEXT NOT NULL,
    source          TEXT NOT NULL,
    embed_type      TEXT NOT NULL,
    module_title    TEXT,
    content_text    TEXT,
    embedding       vector(384)
);

CREATE INDEX IF NOT EXISTS idx_emb_content_id ON embeddings(content_id);
CREATE INDEX IF NOT EXISTS idx_emb_content_type ON embeddings(content_type);
CREATE INDEX IF NOT EXISTS idx_emb_embed_type ON embeddings(embed_type);

-- ═══════════════════════════════════════════════════════════════════
-- performance_channels — replaces reporting_metrics
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS performance_channels (
    id                      SERIAL PRIMARY KEY,
    content_id              TEXT NOT NULL REFERENCES content_entities(content_id) ON DELETE CASCADE,
    channel                 TEXT NOT NULL,

    provisions              INTEGER DEFAULT 0,
    unique_users            INTEGER DEFAULT 0,
    requests                INTEGER DEFAULT 0,
    page_views              INTEGER DEFAULT 0,
    downloads               INTEGER DEFAULT 0,
    completions             INTEGER DEFAULT 0,

    pipeline_touched        NUMERIC,
    closed_amount           NUMERIC,
    marketing_spend         NUMERIC,
    total_cost              NUMERIC,
    avg_cost_per_provision  NUMERIC,
    success_ratio           NUMERIC,

    first_activity          DATE,
    last_activity           DATE,

    windowed_metrics        JSONB DEFAULT '{}'::jsonb,

    synced_at               TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(content_id, channel)
);

CREATE INDEX IF NOT EXISTS idx_pc_content_id ON performance_channels(content_id);
CREATE INDEX IF NOT EXISTS idx_pc_channel ON performance_channels(channel);

-- ═══════════════════════════════════════════════════════════════════
-- performance_scores — replaces retirement_score on reporting_metrics
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS performance_scores (
    content_id      TEXT PRIMARY KEY REFERENCES content_entities(content_id) ON DELETE CASCADE,
    performance_score INTEGER NOT NULL DEFAULT 0,
    score_breakdown JSONB,
    channel_scores  JSONB,
    computed_at     TIMESTAMPTZ DEFAULT NOW(),
    ignored_until   DATE
);

CREATE INDEX IF NOT EXISTS idx_ps_score ON performance_scores(performance_score DESC);

-- ═══════════════════════════════════════════════════════════════════
-- retirement_workflow — re-keyed from catalog_base_name to content_id
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS retirement_workflow (
    content_id          TEXT PRIMARY KEY REFERENCES content_entities(content_id) ON DELETE CASCADE,
    status              TEXT NOT NULL DEFAULT 'reviewed',
    step_reviewed_at    TIMESTAMPTZ,
    step_reviewed_by    TEXT,
    step_approved_at    TIMESTAMPTZ,
    step_approved_by    TEXT,
    approval_reason     TEXT,
    approval_snapshot   JSONB,
    step_notified_at    TIMESTAMPTZ,
    step_notified_by    TEXT,
    step_started_at     TIMESTAMPTZ,
    step_started_by     TEXT,
    retirement_target_date DATE,
    step_retired_at     TIMESTAMPTZ,
    replacement_ci      TEXT,
    replacement_name    TEXT,
    curator_notes       TEXT,
    jira_key            TEXT,
    jira_project        TEXT NOT NULL DEFAULT 'RHDPCD',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rw_status ON retirement_workflow(status);

-- ═══════════════════════════════════════════════════════════════════
-- content_similarity — re-keyed from ci_name_a/b to content_id_a/b
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS content_similarity (
    id SERIAL PRIMARY KEY,
    content_id_a TEXT NOT NULL REFERENCES content_entities(content_id) ON DELETE CASCADE,
    content_id_b TEXT NOT NULL REFERENCES content_entities(content_id) ON DELETE CASCADE,
    similarity_score REAL NOT NULL,
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(content_id_a, content_id_b)
);

CREATE INDEX IF NOT EXISTS idx_content_similarity_a ON content_similarity(content_id_a);
CREATE INDEX IF NOT EXISTS idx_content_similarity_b ON content_similarity(content_id_b);
CREATE INDEX IF NOT EXISTS idx_content_similarity_score ON content_similarity(similarity_score DESC);

-- ═══════════════════════════════════════════════════════════════════
-- babylon_item_workloads — re-keyed from ci_name to content_id
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS babylon_item_workloads (
    id SERIAL PRIMARY KEY,
    content_id TEXT NOT NULL REFERENCES content_entities(content_id) ON DELETE CASCADE,
    workload_fqcn TEXT NOT NULL,
    workload_role TEXT NOT NULL,
    workload_collection TEXT,
    UNIQUE(content_id, workload_fqcn)
);

CREATE INDEX IF NOT EXISTS idx_biw_content_id ON babylon_item_workloads(content_id);
CREATE INDEX IF NOT EXISTS idx_biw_workload_role ON babylon_item_workloads(workload_role);
CREATE INDEX IF NOT EXISTS idx_biw_workload_collection ON babylon_item_workloads(workload_collection);

-- ═══════════════════════════════════════════════════════════════════
-- babylon_item_acl_groups — re-keyed from ci_name to content_id
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS babylon_item_acl_groups (
    id SERIAL PRIMARY KEY,
    content_id TEXT NOT NULL REFERENCES content_entities(content_id) ON DELETE CASCADE,
    group_name TEXT NOT NULL,
    UNIQUE(content_id, group_name)
);

CREATE INDEX IF NOT EXISTS idx_biacl_content_id ON babylon_item_acl_groups(content_id);
CREATE INDEX IF NOT EXISTS idx_biacl_group_name ON babylon_item_acl_groups(group_name);

-- ═══════════════════════════════════════════════════════════════════
-- Independent reference tables (unchanged)
-- ═══════════════════════════════════════════════════════════════════
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

CREATE INDEX IF NOT EXISTS idx_wm_product_name ON workload_mapping(product_name);
CREATE INDEX IF NOT EXISTS idx_wa_product_name ON workload_aliases(product_name);

CREATE TABLE IF NOT EXISTS workload_scan_state (
    collection TEXT PRIMARY KEY,
    last_sha TEXT,
    last_scanned TIMESTAMPTZ DEFAULT NOW()
);

-- ═══════════════════════════════════════════════════════════════════
-- enrichment_tags — re-keyed from ci_name to content_id
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS enrichment_tags (
    id SERIAL PRIMARY KEY,
    content_id TEXT NOT NULL REFERENCES content_entities(content_id) ON DELETE CASCADE,
    tag_type TEXT NOT NULL,
    tag_value TEXT NOT NULL,
    added_by TEXT,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(content_id, tag_type, tag_value)
);

CREATE INDEX IF NOT EXISTS idx_et_content_id ON enrichment_tags(content_id);

-- ═══════════════════════════════════════════════════════════════════
-- Operational tables (recreated empty, unchanged structure)
-- ═══════════════════════════════════════════════════════════════════
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
    provider TEXT DEFAULT 'anthropic',
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
    key_prefix TEXT NOT NULL,
    name TEXT NOT NULL,
    created_by TEXT NOT NULL,
    scopes TEXT[],
    role TEXT NOT NULL DEFAULT 'user',
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);

-- ═══════════════════════════════════════════════════════════════════
-- advisor_sessions — preserved with new chosen_content_id column
-- ═══════════════════════════════════════════════════════════════════
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
    chosen_content_id TEXT,
    chosen_at TIMESTAMPTZ,
    opted_out BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ═══════════════════════════════════════════════════════════════════
-- Operational indexes
-- ═══════════════════════════════════════════════════════════════════
CREATE INDEX IF NOT EXISTS idx_analysis_log_ci_name ON analysis_log(ci_name);
CREATE INDEX IF NOT EXISTS idx_analysis_log_created_at ON analysis_log(created_at);
CREATE INDEX IF NOT EXISTS idx_token_usage_created_at ON token_usage(created_at);
CREATE INDEX IF NOT EXISTS idx_token_usage_operation ON token_usage(operation);
CREATE INDEX IF NOT EXISTS idx_token_usage_provider ON token_usage(provider);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_created_by ON api_keys(created_by);
CREATE INDEX IF NOT EXISTS idx_advisor_sessions_session ON advisor_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_advisor_sessions_user ON advisor_sessions(user_email);
CREATE INDEX IF NOT EXISTS idx_advisor_sessions_created ON advisor_sessions(created_at);
"""



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
        hostname = urlsplit(self._url).hostname or ""
        is_local = hostname in ("localhost", "127.0.0.1")
        allow_env = os.environ.get("RCARS_ALLOW_DROP", "").lower() == "true"
        if not is_local and not allow_env:
            raise RuntimeError(
                "drop_schema() refused: target is not localhost and "
                "RCARS_ALLOW_DROP=true is not set."
            )

        tables = [
            "retirement_workflow",
            "content_similarity",
            "performance_scores", "performance_channels",
            "embeddings", "enrichment_tags", "showroom_analysis",
            "analysis_log", "jobs", "token_usage", "advisor_sessions",
            "api_keys",
            "babylon_item_workloads", "babylon_item_acl_groups",
            "workload_aliases", "workload_mapping", "workload_scan_state",
            "babylon_items", "content_entities",
            # Legacy tables (ensure clean drop if they exist from previous schema)
            "catalog_item_workloads", "catalog_item_acl_groups",
            "reporting_metrics", "catalog_items",
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

    # ── Content entities + Babylon items ──

    def upsert_babylon_catalog_item(self, item: dict[str, Any]):
        """Upsert a Babylon catalog item across content_entities + babylon_items in one transaction."""
        ci_name = item["ci_name"]
        content_id = f"babylon:{ci_name}"

        showroom_url = item.get("showroom_url")
        category = (item.get("category") or "").lower()
        if showroom_url:
            content_type = "demo" if category in ("demo",) else "lab"
        else:
            content_type = "sandbox"

        ce_data = {
            "content_id": content_id,
            "source": "babylon",
            "content_type": content_type,
            "is_hands_on": True,
            "display_name": item.get("display_name") or ci_name,
            "retired_at": None,
            "retirement_reason": None,
            "updated_at": datetime.now(timezone.utc),
        }

        bi_fields = [
            "ci_name", "category", "stage", "catalog_namespace",
            "keywords", "description", "icon_url", "owners_json",
            "showroom_url", "showroom_ref", "content_path",
            "last_crd_update", "is_prod", "is_published",
            "published_ci_name", "base_ci_name",
            "is_agd_v2", "agd_config", "cloud_provider", "ocp_version",
            "os_image", "worker_instance_count", "control_plane_instance_count",
            "instances_json",
        ]
        bi_data = {"content_id": content_id}
        for k in bi_fields:
            if k in item:
                bi_data[k] = item[k]
        bi_data["last_refreshed"] = datetime.now(timezone.utc)

        if "owners_json" in bi_data and bi_data["owners_json"] is not None:
            bi_data["owners_json"] = Jsonb(bi_data["owners_json"])
        if "instances_json" in bi_data and bi_data["instances_json"] is not None:
            bi_data["instances_json"] = Jsonb(bi_data["instances_json"])

        ce_cols = list(ce_data.keys())
        ce_ph = [f"%({k})s" for k in ce_cols]
        ce_updates = [f"{k} = EXCLUDED.{k}" for k in ce_cols
                      if k not in ("content_id", "source", "summary", "products_json",
                                   "topics_json", "audience_json", "difficulty")]
        ce_sql = f"""
            INSERT INTO content_entities ({', '.join(ce_cols)})
            VALUES ({', '.join(ce_ph)})
            ON CONFLICT (content_id) DO UPDATE SET {', '.join(ce_updates)}
        """

        bi_cols = list(bi_data.keys())
        bi_ph = [f"%({k})s" for k in bi_cols]
        bi_updates = [f"{k} = EXCLUDED.{k}" for k in bi_cols
                      if k not in ("content_id", "showroom_url_override")]
        bi_sql = f"""
            INSERT INTO babylon_items ({', '.join(bi_cols)})
            VALUES ({', '.join(bi_ph)})
            ON CONFLICT (content_id) DO UPDATE SET {', '.join(bi_updates)}
        """

        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(ce_sql, ce_data)
                cur.execute(bi_sql, bi_data)
            conn.commit()

    def get_content_entity(self, content_id: str) -> dict[str, Any] | None:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT * FROM content_entities WHERE content_id = %(content_id)s",
                {"content_id": content_id},
            )
            return cur.fetchone()

    def get_babylon_item(self, content_id: str) -> dict[str, Any] | None:
        sql = """
            SELECT ce.*, bi.*
            FROM content_entities ce
            JOIN babylon_items bi ON bi.content_id = ce.content_id
            WHERE ce.content_id = %(content_id)s
        """
        with self._pool.connection() as conn:
            cur = conn.execute(sql, {"content_id": content_id})
            return cur.fetchone()

    def get_babylon_item_by_ci_name(self, ci_name: str) -> dict[str, Any] | None:
        sql = """
            SELECT ce.*, bi.*
            FROM content_entities ce
            JOIN babylon_items bi ON bi.content_id = ce.content_id
            WHERE bi.ci_name = %(ci_name)s
        """
        with self._pool.connection() as conn:
            cur = conn.execute(sql, {"ci_name": ci_name})
            return cur.fetchone()

    def find_catalog_item_by_display_name_prefix(
        self, pattern: str, stages: list[str] | None = None,
    ) -> dict[str, Any] | None:
        stage_list = stages or ["prod"]
        stage_placeholders = ",".join(["%s"] * len(stage_list))
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT ce.*, bi.* FROM content_entities ce "
                    f"JOIN babylon_items bi ON bi.content_id = ce.content_id "
                    f"WHERE ce.display_name ILIKE %s "
                    f"AND bi.stage IN ({stage_placeholders}) AND ce.retired_at IS NULL "
                    f"ORDER BY CASE bi.stage WHEN 'prod' THEN 0 WHEN 'event' THEN 1 ELSE 2 END "
                    f"LIMIT 1",
                    (pattern, *stage_list),
                )
                return cur.fetchone()

    def get_embedding(self, content_id: str, embed_type: str = "summary") -> list[float] | None:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT embedding::text FROM embeddings WHERE content_id = %s AND embed_type = %s LIMIT 1",
                    (content_id, embed_type),
                )
                row = cur.fetchone()
                if not row:
                    return None
                raw = row["embedding"]
                return [float(x) for x in raw.strip("[]").split(",")]

    def find_catalog_item_by_keyword_overlap(
        self, keywords: set[str], stages: list[str] | None = None, min_overlap: int = 3,
    ) -> dict[str, Any] | None:
        stage_list = stages or ["prod"]
        stage_placeholders = ",".join(["%s"] * len(stage_list))
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT ce.content_id, bi.ci_name, ce.display_name, bi.stage "
                    f"FROM content_entities ce "
                    f"JOIN babylon_items bi ON bi.content_id = ce.content_id "
                    f"WHERE bi.stage IN ({stage_placeholders}) AND ce.retired_at IS NULL",
                    (*stage_list,),
                )
                best_item = None
                best_overlap = 0
                for row in cur.fetchall():
                    name_words = {w.lower() for w in re.findall(r'[a-zA-Z]{3,}', row["display_name"] or "")}
                    overlap = len(keywords & name_words)
                    if overlap >= min_overlap and overlap > best_overlap:
                        best_overlap = overlap
                        best_item = row
                if best_item:
                    return self.get_babylon_item(best_item["content_id"])
                return None

    def list_catalog_items(
        self, prod_only: bool = False, category: str | None = None,
        stage: str | None = None, include_retired: bool = False,
    ) -> list[dict[str, Any]]:
        conditions = []
        params: dict[str, Any] = {}
        if not include_retired:
            conditions.append("ce.retired_at IS NULL")
        if prod_only:
            conditions.append("bi.is_prod = TRUE")
        if category:
            conditions.append("bi.category = %(category)s")
            params["category"] = category
        if stage:
            conditions.append("bi.stage = %(stage)s")
            params["stage"] = stage
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""SELECT ce.*, bi.*, sa.is_stale, sa.enrichment_review_needed
                  FROM content_entities ce
                  JOIN babylon_items bi ON bi.content_id = ce.content_id
                  LEFT JOIN showroom_analysis sa ON sa.content_id = ce.content_id
                  {where} ORDER BY bi.ci_name"""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()

    def list_content_entities_filtered(
        self,
        search: str | None = None,
        content_types: list[str] | None = None,
        stages: list[str] | None = None,
        cloud_provider: str | None = None,
        agd_config: str | None = None,
        workloads: list[str] | None = None,
        content_filter: str | None = None,
        category: str | None = None,
        limit: int = 50,
        offset: int = 0,
        include_retired: str | bool = False,
    ) -> dict[str, Any]:
        conditions = []
        params: dict[str, Any] = {}
        joins = []

        retired_str = str(include_retired).lower()
        if retired_str == "only":
            conditions.append("ce.retired_at IS NOT NULL")
        elif retired_str not in ("true", "1"):
            conditions.append("ce.retired_at IS NULL")

        if content_types:
            conditions.append("ce.content_type = ANY(%(content_types)s)")
            params["content_types"] = content_types

        if category:
            conditions.append("bi.category = %(category)s")
            params["category"] = category

        babylon_specific = any([stages, cloud_provider, agd_config, workloads, category])

        if stages:
            conditions.append("bi.stage = ANY(%(stages)s)")
            params["stages"] = stages
        elif babylon_specific:
            conditions.append("bi.stage = 'prod'")
        else:
            conditions.append("(bi.stage = 'prod' OR bi.content_id IS NULL)")

        if search:
            words = search.strip().split()
            if len(words) == 1:
                conditions.append(
                    "(ce.display_name ILIKE %(search)s OR bi.ci_name ILIKE %(search)s)"
                )
                params["search"] = f"%{search}%"
            else:
                word_conds = []
                for i, word in enumerate(words[:6]):
                    key = f"sw{i}"
                    word_conds.append(f"(ce.display_name ILIKE %({key})s OR bi.ci_name ILIKE %({key})s)")
                    params[key] = f"%{word}%"
                conditions.append(f"({' AND '.join(word_conds)})")

        if cloud_provider:
            conditions.append("bi.cloud_provider = %(cloud_provider)s")
            params["cloud_provider"] = cloud_provider
        if agd_config:
            conditions.append("bi.agd_config = %(agd_config)s")
            params["agd_config"] = agd_config

        if workloads:
            resolved = self._resolve_workload_aliases(workloads)
            for i, wl in enumerate(resolved):
                alias_w = f"w{i}"
                alias_m = f"m{i}"
                joins.append(
                    f"JOIN babylon_item_workloads {alias_w} "
                    f"ON {alias_w}.content_id = ce.content_id "
                    f"JOIN workload_mapping {alias_m} "
                    f"ON {alias_m}.workload_role = {alias_w}.workload_role "
                    f"AND {alias_m}.product_name = %({alias_m}_name)s"
                )
                params[f"{alias_m}_name"] = wl

        if content_filter == "unanalyzed":
            conditions.append("bi.showroom_url IS NOT NULL")
            conditions.append("bi.is_published IS NOT TRUE")
            conditions.append("bi.scan_status NOT IN ('success', 'failed')")
        elif content_filter == "scan_failures":
            conditions.append("bi.scan_status = 'failed'")
        elif content_filter == "stale":
            joins.append(
                "JOIN showroom_analysis sa_stale ON sa_stale.content_id = ce.content_id "
                "AND sa_stale.is_stale = TRUE"
            )
        elif content_filter == "needs_review":
            joins.append(
                "JOIN showroom_analysis sa_review ON sa_review.content_id = ce.content_id "
                "AND sa_review.enrichment_review_needed = TRUE"
            )

        join_sql = "\n".join(joins)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        count_sql = f"""
            SELECT COUNT(DISTINCT ce.content_id)
            FROM content_entities ce
            LEFT JOIN babylon_items bi ON bi.content_id = ce.content_id
            LEFT JOIN showroom_analysis sa ON sa.content_id = ce.content_id
            {join_sql}
            {where}
        """

        data_sql = f"""
            SELECT DISTINCT ce.*, bi.ci_name, bi.category, bi.stage, bi.catalog_namespace,
                   bi.showroom_url, bi.showroom_ref, bi.showroom_url_override, bi.content_path,
                   bi.is_prod, bi.is_published, bi.published_ci_name, bi.base_ci_name,
                   bi.is_agd_v2, bi.agd_config, bi.cloud_provider, bi.ocp_version,
                   bi.os_image, bi.worker_instance_count, bi.control_plane_instance_count,
                   bi.instances_json, bi.keywords, bi.description AS bi_description,
                   bi.icon_url, bi.owners_json, bi.scan_status, bi.scan_error_class,
                   bi.scan_error, bi.scan_failed_at, bi.last_crd_update, bi.last_refreshed,
                   sa.is_stale, sa.enrichment_review_needed
            FROM content_entities ce
            LEFT JOIN babylon_items bi ON bi.content_id = ce.content_id
            LEFT JOIN showroom_analysis sa ON sa.content_id = ce.content_id
            {join_sql}
            {where}
            ORDER BY ce.content_id
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

    def retire_removed_items(self, current_content_ids: set[str]) -> list[dict]:
        """Mark content entities not in current CRD scan as retired."""
        if not current_content_ids:
            logger.warning("retire_skipped_empty_scan",
                           component="rcars", action="retire_removed",
                           reason="Empty scan result — refusing to retire all items")
            return []
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT ce.content_id, ce.display_name, ce.retired_at, bi.ci_name, bi.stage "
                "FROM content_entities ce "
                "JOIN babylon_items bi ON bi.content_id = ce.content_id "
                "WHERE ce.source = 'babylon'"
            )
            all_items = cur.fetchall()

            newly_retired = []
            unretired = []

            for item in all_items:
                cid = item["content_id"]
                was_retired = item.get("retired_at") is not None

                if cid not in current_content_ids and not was_retired:
                    conn.execute(
                        "UPDATE content_entities SET retired_at = NOW(), "
                        "retirement_reason = 'Disappeared from Babylon CRDs' "
                        "WHERE content_id = %s",
                        (cid,),
                    )
                    newly_retired.append(item)
                elif cid in current_content_ids and was_retired:
                    conn.execute(
                        "UPDATE content_entities SET retired_at = NULL, "
                        "retirement_reason = NULL WHERE content_id = %s",
                        (cid,),
                    )
                    unretired.append(item)

            if newly_retired or unretired:
                conn.commit()

            if newly_retired:
                retired_content_ids = set()
                for item in newly_retired:
                    cid = item["content_id"]
                    base = cid.removeprefix("babylon:")
                    for suffix in (".prod", ".dev", ".event", ".test"):
                        if base.endswith(suffix):
                            base = base[:-len(suffix)]
                            break
                    all_stage_cids = {
                        f"babylon:{base}{s}" for s in (".prod", ".dev", ".event", ".test")
                    }
                    unretired_siblings = conn.execute(
                        "SELECT content_id FROM content_entities "
                        "WHERE content_id = ANY(%s) AND retired_at IS NULL",
                        (list(all_stage_cids),),
                    ).fetchall()
                    if not unretired_siblings:
                        retired_content_ids.update(all_stage_cids)
                if retired_content_ids:
                    closed = self.auto_close_retired_workflows(retired_content_ids)
                    if closed:
                        logger.info("auto_closed_retirement_workflows",
                                    component="rcars", action="auto_close",
                                    count=closed)

            if unretired:
                logger.info("unretired_items",
                            component="rcars", action="unretire",
                            count=len(unretired),
                            items=[i["content_id"] for i in unretired])
            return newly_retired

    def set_content_path(self, content_id: str, path: str | None):
        with self._pool.connection() as conn:
            conn.execute(
                "UPDATE babylon_items SET content_path = %s WHERE content_id = %s",
                (path, content_id),
            )
            conn.commit()

    # ── Showroom analysis ──

    def upsert_showroom_analysis(self, analysis: dict[str, Any]):
        fields = [
            "content_id", "content_type", "summary",
            "products_json", "audience_json", "topics_json",
            "modules_json", "learning_objectives_json",
            "difficulty", "estimated_duration_min",
            "format_suitability_json", "use_cases_json",
            "last_repo_commit", "last_repo_updated",
            "last_analyzed", "is_stale", "stale_commit", "content_hash",
            "enrichment_review_needed", "review_reasons",
        ]
        present = {k: analysis.get(k) for k in fields if k in analysis}
        if "last_analyzed" not in present:
            present["last_analyzed"] = datetime.now(timezone.utc)

        jsonb_fields = [
            "products_json", "audience_json", "topics_json",
            "modules_json", "learning_objectives_json",
            "format_suitability_json", "use_cases_json",
            "review_reasons",
        ]
        for f in jsonb_fields:
            if f in present and present[f] is not None:
                present[f] = Jsonb(present[f])

        columns = list(present.keys())
        placeholders = [f"%({k})s" for k in columns]
        updates = [f"{k} = EXCLUDED.{k}" for k in columns if k != "content_id"]

        sql = f"""
            INSERT INTO showroom_analysis ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            ON CONFLICT (content_id) DO UPDATE SET {', '.join(updates)}
        """
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, present)
            conn.commit()

    def update_content_entity_card(
        self, content_id: str,
        summary: str | None = None,
        products_json: Any = None,
        topics_json: Any = None,
        audience_json: Any = None,
        difficulty: str | None = None,
    ) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                """UPDATE content_entities
                   SET summary = %s, products_json = %s, topics_json = %s,
                       audience_json = %s, difficulty = %s, updated_at = NOW()
                   WHERE content_id = %s""",
                (summary,
                 Jsonb(products_json) if products_json is not None else None,
                 Jsonb(topics_json) if topics_json is not None else None,
                 Jsonb(audience_json) if audience_json is not None else None,
                 difficulty, content_id),
            )
            conn.commit()

    def get_showroom_analysis(self, content_id: str) -> dict[str, Any] | None:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT * FROM showroom_analysis WHERE content_id = %(content_id)s",
                {"content_id": content_id},
            )
            return cur.fetchone()

    def get_showroom_analysis_by_ci_name(self, ci_name: str) -> dict[str, Any] | None:
        content_id = f"babylon:{ci_name}"
        return self.get_showroom_analysis(content_id)

    def find_donor_by_content_hash(self, content_hash: str, exclude_content_id: str | None = None) -> dict[str, Any] | None:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                exclude_clause = "AND sa.content_id != %s" if exclude_content_id else ""
                params = [content_hash]
                if exclude_content_id:
                    params.append(exclude_content_id)
                cur.execute(f"""
                    SELECT sa.*, bi.stage, bi.ci_name
                    FROM showroom_analysis sa
                    JOIN content_entities ce ON ce.content_id = sa.content_id
                    JOIN babylon_items bi ON bi.content_id = sa.content_id
                    JOIN embeddings e ON e.content_id = sa.content_id AND e.embed_type = 'summary'
                    WHERE sa.content_hash = %s AND ce.retired_at IS NULL {exclude_clause}
                    ORDER BY CASE bi.stage WHEN 'prod' THEN 0 WHEN 'event' THEN 1 ELSE 2 END,
                             sa.last_analyzed DESC NULLS LAST, sa.content_id
                    LIMIT 1
                """, params)
                return cur.fetchone()

    def get_embeddings_for_content(self, content_id: str) -> list[dict[str, Any]]:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT embed_type, content_type, source, content_text, module_title, "
                    "embedding::text as embedding_text FROM embeddings WHERE content_id = %s",
                    (content_id,),
                )
                return cur.fetchall()

    def find_prod_ci_by_content_hash(self, content_hash: str) -> dict[str, Any] | None:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT ce.content_id, bi.ci_name, ce.display_name, bi.stage,
                              bi.catalog_namespace, bi.published_ci_name, bi.is_published
                       FROM content_entities ce
                       JOIN babylon_items bi ON bi.content_id = ce.content_id
                       JOIN showroom_analysis sa ON sa.content_id = ce.content_id
                       WHERE sa.content_hash = %s AND bi.stage = 'prod' AND ce.retired_at IS NULL
                       ORDER BY bi.ci_name
                       LIMIT 1""",
                    (content_hash,),
                )
                return cur.fetchone()

    def mark_stale(self, content_id: str, new_commit: str | None = None) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "UPDATE showroom_analysis SET is_stale = TRUE, stale_commit = %s WHERE content_id = %s",
                (new_commit, content_id),
            )
            conn.commit()

    def mark_all_stale(self) -> int:
        with self._pool.connection() as conn:
            cur = conn.execute("UPDATE showroom_analysis SET is_stale = TRUE WHERE is_stale = FALSE")
            conn.commit()
            return cur.rowcount

    def clear_stale(self, content_id: str) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "UPDATE showroom_analysis SET is_stale = FALSE, stale_commit = NULL WHERE content_id = %s",
                (content_id,),
            )
            conn.commit()

    # ── Embeddings ──

    def clear_embeddings(self, content_id: str):
        with self._pool.connection() as conn:
            conn.execute("DELETE FROM embeddings WHERE content_id = %s", (content_id,))
            conn.commit()

    def store_embedding(
        self, content_id: str, content_type: str, source: str,
        embed_type: str, content_text: str,
        embedding: list[float], module_title: str | None = None,
    ):
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                if module_title:
                    cur.execute(
                        "DELETE FROM embeddings WHERE content_id = %s AND embed_type = %s AND module_title = %s",
                        (content_id, embed_type, module_title),
                    )
                else:
                    cur.execute(
                        "DELETE FROM embeddings WHERE content_id = %s AND embed_type = %s AND module_title IS NULL",
                        (content_id, embed_type),
                    )
                cur.execute(
                    """INSERT INTO embeddings (content_id, content_type, source, embed_type, module_title, content_text, embedding)
                       VALUES (%s, %s, %s, %s, %s, %s, %s::vector)""",
                    (content_id, content_type, source, embed_type, module_title, content_text,
                     f"[{','.join(str(v) for v in embedding)}]"),
                )
            conn.commit()

    def search_embeddings(
        self, query_embedding: list[float], limit: int = 25,
        content_types: list[str] | None = None,
        stages: list[str] | None = None,
        include_zt: bool = True,
        quality_threshold: float = 0.45,
        retrieval_window: int = 200,
    ) -> list[dict[str, Any]]:
        zt_filter = ""
        if not include_zt:
            zt_filter = (
                "AND NOT EXISTS (SELECT 1 FROM babylon_items biz "
                "WHERE biz.content_id = e.content_id "
                "AND (biz.catalog_namespace LIKE 'zt-%%' OR biz.ci_name LIKE 'zt-%%'))"
            )

        stage_filter = ""
        stage_params: list = []
        if stages:
            stage_placeholders = ",".join(["%s"] * len(stages))
            stage_filter = (
                f"AND EXISTS (SELECT 1 FROM babylon_items bis "
                f"WHERE bis.content_id = e.content_id AND bis.stage IN ({stage_placeholders}))"
            )
            stage_params = list(stages)

        ct_filter = ""
        ct_params: list = []
        if content_types:
            ct_placeholders = ",".join(["%s"] * len(content_types))
            ct_filter = f"AND e.content_type IN ({ct_placeholders})"
            ct_params = list(content_types)

        vec_str = f"[{','.join(str(v) for v in query_embedding)}]"

        sql = f"""
            WITH candidates AS (
                SELECT e.content_id, e.embed_type, e.module_title, e.content_type, e.source,
                       1 - (e.embedding <=> %s::vector) AS similarity
                FROM embeddings e
                JOIN content_entities ce ON ce.content_id = e.content_id
                WHERE ce.retired_at IS NULL
                  {ct_filter}
                  {stage_filter}
                  {zt_filter}
                ORDER BY e.embedding <=> %s::vector
                LIMIT %s
            ),
            grouped AS (
                SELECT content_id, content_type, source,
                       MAX(similarity) AS best_similarity,
                       (ARRAY_AGG(embed_type ORDER BY similarity DESC))[1] AS best_match_type,
                       (ARRAY_AGG(module_title ORDER BY similarity DESC))[1] AS best_match_module
                FROM candidates
                WHERE similarity >= %s
                GROUP BY content_id, content_type, source
                ORDER BY best_similarity DESC
                LIMIT %s
            )
            SELECT g.*,
                   ce.display_name, ce.is_hands_on,
                   bi.ci_name, bi.stage, bi.category, bi.showroom_url, bi.showroom_ref,
                   bi.is_published, bi.published_ci_name, bi.base_ci_name,
                   bi.catalog_namespace, sa.content_hash
            FROM grouped g
            JOIN content_entities ce ON ce.content_id = g.content_id
            LEFT JOIN babylon_items bi ON bi.content_id = g.content_id
            LEFT JOIN showroom_analysis sa ON sa.content_id = g.content_id
            ORDER BY g.best_similarity DESC
        """
        params = [vec_str, *ct_params, *stage_params, vec_str, retrieval_window,
                  quality_threshold, limit]

        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()

    # ── Enrichment ──

    def add_enrichment_tag(self, content_id: str, tag_type: str, tag_value: str, added_by: str | None = None) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "INSERT INTO enrichment_tags (content_id, tag_type, tag_value, added_by) VALUES (%s, %s, %s, %s) ON CONFLICT (content_id, tag_type, tag_value) DO NOTHING",
                (content_id, tag_type, tag_value, added_by),
            )
            conn.commit()

    def remove_enrichment_tag(self, content_id: str, tag_type: str, tag_value: str) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "DELETE FROM enrichment_tags WHERE content_id = %s AND tag_type = %s AND tag_value = %s",
                (content_id, tag_type, tag_value),
            )
            conn.commit()

    def remove_enrichment_tag_by_id(self, tag_id: int, content_id: str | None = None) -> None:
        if content_id is not None:
            sql = "DELETE FROM enrichment_tags WHERE id = %s AND content_id = %s"
            params = (tag_id, content_id)
        else:
            sql = "DELETE FROM enrichment_tags WHERE id = %s"
            params = (tag_id,)
        with self._pool.connection() as conn:
            conn.execute(sql, params)
            conn.commit()

    def get_enrichment_tags(self, content_id: str) -> list[dict]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT id, tag_type, tag_value, added_by, added_at FROM enrichment_tags WHERE content_id = %s ORDER BY added_at",
                (content_id,),
            )
            return cur.fetchall()

    def get_enrichment_tags_for_items(self, content_ids: list[str]) -> dict[str, list[dict]]:
        if not content_ids:
            return {}
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT content_id, id, tag_type, tag_value, added_by FROM enrichment_tags WHERE content_id = ANY(%s) ORDER BY content_id, added_at",
                (content_ids,),
            )
            result: dict[str, list] = {cid: [] for cid in content_ids}
            for row in cur.fetchall():
                result[row["content_id"]].append(row)
            return result

    def set_enrichment_note(self, content_id: str, note: str) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "UPDATE showroom_analysis SET notes = %s WHERE content_id = %s", (note, content_id),
            )
            conn.commit()

    def set_enrichment_review_flag(self, content_id: str, needed: bool) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "UPDATE showroom_analysis SET enrichment_review_needed = %s WHERE content_id = %s",
                (needed, content_id),
            )
            conn.commit()

    def set_curated_duration(self, content_id: str, duration_min: int | None, updated_by: str | None = None) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "UPDATE showroom_analysis SET curated_duration_min = %s WHERE content_id = %s",
                (duration_min, content_id),
            )
            conn.commit()
        logger.info("curated_duration_set", component="rcars", action="set_curated_duration",
                    content_id=content_id, duration_min=duration_min, updated_by=updated_by)

    # ── Infrastructure metadata (workloads, ACL groups, mapping) ──

    def sync_workloads(self, content_id: str, workloads: list[dict]) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "DELETE FROM babylon_item_workloads WHERE content_id = %s", (content_id,)
            )
            for w in workloads:
                conn.execute(
                    "INSERT INTO babylon_item_workloads (content_id, workload_fqcn, workload_role, workload_collection) "
                    "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                    (content_id, w["fqcn"], w["role"], w.get("collection")),
                )
            conn.commit()

    def sync_acl_groups(self, content_id: str, groups: list[str]) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "DELETE FROM babylon_item_acl_groups WHERE content_id = %s", (content_id,)
            )
            for g in groups:
                conn.execute(
                    "INSERT INTO babylon_item_acl_groups (content_id, group_name) "
                    "VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (content_id, g),
                )
            conn.commit()

    def get_workloads(self, content_id: str) -> list[dict]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT workload_fqcn, workload_role, workload_collection "
                "FROM babylon_item_workloads WHERE content_id = %s ORDER BY workload_role",
                (content_id,),
            )
            return cur.fetchall()

    def get_acl_groups(self, content_id: str) -> list[str]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT group_name FROM babylon_item_acl_groups "
                "WHERE content_id = %s ORDER BY group_name",
                (content_id,),
            )
            return [row["group_name"] for row in cur.fetchall()]

    def get_workload_classifications(self, content_id: str) -> list[dict]:
        sql = """
            SELECT wm.product_name, wm.description, wm.category
            FROM babylon_item_workloads biw
            JOIN workload_mapping wm ON wm.workload_role = biw.workload_role
            WHERE biw.content_id = %(content_id)s
              AND wm.verified = TRUE
        """
        with self._pool.connection() as conn:
            return conn.execute(sql, {"content_id": content_id}).fetchall()

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
                SELECT biw.workload_role, biw.workload_collection,
                       COUNT(DISTINCT biw.content_id) AS ci_count
                FROM babylon_item_workloads biw
                JOIN content_entities ce ON ce.content_id = biw.content_id AND ce.retired_at IS NULL
                LEFT JOIN workload_mapping wm ON wm.workload_role = biw.workload_role
                WHERE wm.id IS NULL
                GROUP BY biw.workload_role, biw.workload_collection
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
                cur.execute(
                    "SELECT COUNT(*) AS count FROM babylon_items bi "
                    "JOIN content_entities ce ON ce.content_id = bi.content_id "
                    "WHERE bi.is_agd_v2 = TRUE AND ce.retired_at IS NULL"
                )
                v2_items = cur.fetchone()["count"]
                cur.execute(
                    "SELECT COUNT(DISTINCT biw.content_id) AS count FROM babylon_item_workloads biw "
                    "JOIN content_entities ce ON ce.content_id = biw.content_id WHERE ce.retired_at IS NULL"
                )
                with_workloads = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(*) AS count FROM workload_mapping")
                mapped_count = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(*) AS count FROM workload_mapping WHERE verified = TRUE")
                verified_count = cur.fetchone()["count"]
                cur.execute("""
                    SELECT COUNT(DISTINCT biw.workload_role) AS count
                    FROM babylon_item_workloads biw
                    JOIN content_entities ce ON ce.content_id = biw.content_id AND ce.retired_at IS NULL
                    LEFT JOIN workload_mapping wm ON wm.workload_role = biw.workload_role
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

    def get_catalog_facets(self) -> dict:
        with self._pool.connection() as conn:
            cur = conn.execute("""
                SELECT wm.product_name, wm.category, COUNT(DISTINCT biw.content_id) AS ci_count
                FROM workload_mapping wm
                JOIN babylon_item_workloads biw ON biw.workload_role = wm.workload_role
                JOIN babylon_items bi ON bi.content_id = biw.content_id AND bi.is_prod = TRUE
                JOIN content_entities ce ON ce.content_id = bi.content_id AND ce.retired_at IS NULL
                GROUP BY wm.product_name, wm.category
                ORDER BY ci_count DESC
            """)
            workloads = cur.fetchall()

            cur = conn.execute("""
                SELECT bi.agd_config, COUNT(*) AS ci_count
                FROM babylon_items bi
                JOIN content_entities ce ON ce.content_id = bi.content_id
                WHERE bi.is_agd_v2 = TRUE AND bi.is_prod = TRUE AND ce.retired_at IS NULL
                GROUP BY bi.agd_config ORDER BY ci_count DESC
            """)
            configs = cur.fetchall()

            cur = conn.execute("""
                SELECT bi.cloud_provider, COUNT(*) AS ci_count
                FROM babylon_items bi
                JOIN content_entities ce ON ce.content_id = bi.content_id
                WHERE bi.is_agd_v2 = TRUE AND bi.cloud_provider IS NOT NULL
                  AND bi.cloud_provider != 'none' AND bi.is_prod = TRUE AND ce.retired_at IS NULL
                GROUP BY bi.cloud_provider ORDER BY ci_count DESC
            """)
            cloud_providers = cur.fetchall()

            cur = conn.execute("""
                SELECT bi.os_image, COUNT(*) AS ci_count
                FROM babylon_items bi
                JOIN content_entities ce ON ce.content_id = bi.content_id
                WHERE bi.is_agd_v2 = TRUE AND bi.os_image IS NOT NULL
                  AND bi.is_prod = TRUE AND ce.retired_at IS NULL
                GROUP BY bi.os_image ORDER BY ci_count DESC
            """)
            os_images = cur.fetchall()

        return {
            "workloads": workloads,
            "configs": configs,
            "cloud_providers": cloud_providers,
            "os_images": os_images,
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
        conditions = ["bi.is_agd_v2 = TRUE", "ce.retired_at IS NULL"]
        params: dict[str, Any] = {}
        joins = []

        if prod_only:
            conditions.append("bi.is_prod = TRUE")
        if stage:
            conditions.append("bi.stage = %(stage)s")
            params["stage"] = stage
        if agd_config:
            conditions.append("bi.agd_config = %(agd_config)s")
            params["agd_config"] = agd_config
        if cloud_provider:
            conditions.append("bi.cloud_provider = %(cloud_provider)s")
            params["cloud_provider"] = cloud_provider
        if ocp_version:
            conditions.append("bi.ocp_version LIKE %(ocp_version)s")
            params["ocp_version"] = f"{ocp_version}%"
        if os_image:
            conditions.append("bi.os_image LIKE %(os_image)s")
            params["os_image"] = f"{os_image}%"

        if workloads:
            resolved = self._resolve_workload_aliases(workloads)
            for i, wl in enumerate(resolved):
                alias_w = f"w{i}"
                alias_m = f"m{i}"
                joins.append(
                    f"JOIN babylon_item_workloads {alias_w} "
                    f"ON {alias_w}.content_id = ce.content_id "
                    f"JOIN workload_mapping {alias_m} "
                    f"ON {alias_m}.workload_role = {alias_w}.workload_role "
                    f"AND {alias_m}.product_name = %({alias_m}_name)s"
                )
                params[f"{alias_m}_name"] = wl

        join_sql = "\n".join(joins)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        sql = f"""
            SELECT DISTINCT ce.*, bi.*, sa.summary AS analysis_summary, sa.content_type AS analysis_content_type,
                   sa.estimated_duration_min, sa.difficulty AS analysis_difficulty
            FROM content_entities ce
            JOIN babylon_items bi ON bi.content_id = ce.content_id
            LEFT JOIN showroom_analysis sa ON sa.content_id = ce.content_id
            {join_sql}
            {where}
            ORDER BY ce.display_name
            LIMIT %(limit)s
        """
        params["limit"] = limit

        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()

    # ── Content similarity ──

    def compute_content_similarity(self, threshold: float = 0.75, stage: str = "prod") -> dict[str, int]:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM content_similarity
                    WHERE content_id_a IN (
                        SELECT bi.content_id FROM babylon_items bi WHERE bi.stage = %(stage)s
                    )
                """, {"stage": stage})

                cur.execute("""
                    INSERT INTO content_similarity (content_id_a, content_id_b, similarity_score, computed_at)
                    SELECT a.content_id, b.content_id,
                           1.0 - (a.embedding <=> b.embedding) AS similarity,
                           NOW()
                    FROM embeddings a
                    JOIN embeddings b ON a.content_id < b.content_id
                    JOIN content_entities ce_a ON ce_a.content_id = a.content_id
                    JOIN content_entities ce_b ON ce_b.content_id = b.content_id
                    JOIN babylon_items bi_a ON bi_a.content_id = a.content_id
                    JOIN babylon_items bi_b ON bi_b.content_id = b.content_id
                    WHERE a.embed_type = 'summary'
                      AND b.embed_type = 'summary'
                      AND 1.0 - (a.embedding <=> b.embedding) >= %(threshold)s
                      AND bi_a.stage = %(stage)s
                      AND bi_b.stage = %(stage)s
                      AND (bi_a.is_published IS NULL OR bi_a.is_published = FALSE)
                      AND (bi_b.is_published IS NULL OR bi_b.is_published = FALSE)
                      AND ce_a.retired_at IS NULL
                      AND ce_b.retired_at IS NULL
                """, {"threshold": threshold, "stage": stage})
                inserted = cur.rowcount
            conn.commit()

        logger.info("content_similarity_computed", pairs_stored=inserted, threshold=threshold, stage=stage)
        return {"pairs_stored": inserted, "threshold": threshold, "stage": stage}

    def get_similar_items(self, content_id: str, min_score: float = 0.75) -> list[dict[str, Any]]:
        sql = """
            SELECT cs.content_id_a, cs.content_id_b, cs.similarity_score, cs.computed_at,
                   ce.display_name, bi.category, bi.stage, bi.ci_name, sa.summary
            FROM content_similarity cs
            JOIN content_entities ce ON ce.content_id = CASE
                WHEN cs.content_id_a = %(content_id)s THEN cs.content_id_b
                ELSE cs.content_id_a END
            LEFT JOIN babylon_items bi ON bi.content_id = ce.content_id
            LEFT JOIN showroom_analysis sa ON sa.content_id = ce.content_id
            WHERE (cs.content_id_a = %(content_id)s OR cs.content_id_b = %(content_id)s)
              AND cs.similarity_score >= %(min_score)s
            ORDER BY cs.similarity_score DESC
        """
        with self._pool.connection() as conn:
            cur = conn.execute(sql, {"content_id": content_id, "min_score": min_score})
            rows = cur.fetchall()

        results = []
        for row in rows:
            other_id = row["content_id_b"] if row["content_id_a"] == content_id else row["content_id_a"]
            results.append({
                "content_id": other_id,
                "ci_name": row.get("ci_name"),
                "display_name": row["display_name"],
                "category": row.get("category"),
                "stage": row.get("stage"),
                "summary": row.get("summary"),
                "similarity_score": round(row["similarity_score"], 4),
                "computed_at": row["computed_at"],
            })
        return results

    def get_overlap_report(self, min_score: float = 0.75, stage: str | None = None) -> list[dict[str, Any]]:
        sql = """
            SELECT cs.content_id_a, cs.content_id_b, cs.similarity_score, cs.computed_at,
                   ce_a.display_name AS display_name_a, bi_a.category AS category_a, bi_a.stage AS stage_a,
                   bi_a.ci_name AS ci_name_a, sa_a.summary AS summary_a,
                   ce_b.display_name AS display_name_b, bi_b.category AS category_b, bi_b.stage AS stage_b,
                   bi_b.ci_name AS ci_name_b, sa_b.summary AS summary_b
            FROM content_similarity cs
            JOIN content_entities ce_a ON ce_a.content_id = cs.content_id_a
            JOIN content_entities ce_b ON ce_b.content_id = cs.content_id_b
            LEFT JOIN babylon_items bi_a ON bi_a.content_id = cs.content_id_a
            LEFT JOIN babylon_items bi_b ON bi_b.content_id = cs.content_id_b
            LEFT JOIN showroom_analysis sa_a ON sa_a.content_id = cs.content_id_a
            LEFT JOIN showroom_analysis sa_b ON sa_b.content_id = cs.content_id_b
            WHERE cs.similarity_score >= %(min_score)s
        """
        params: dict[str, Any] = {"min_score": min_score}
        if stage:
            sql += " AND bi_a.stage = %(stage)s AND bi_b.stage = %(stage)s"
            params["stage"] = stage
        sql += " ORDER BY cs.similarity_score DESC"
        with self._pool.connection() as conn:
            cur = conn.execute(sql, params)
            return cur.fetchall()

    def get_similarity_stats(self, stage: str | None = None) -> dict[str, Any]:
        stage_filter = ""
        params: dict[str, Any] = {}
        if stage:
            stage_filter = """
                AND cs.content_id_a IN (SELECT bi.content_id FROM babylon_items bi WHERE bi.stage = %(stage)s)
                AND cs.content_id_b IN (SELECT bi.content_id FROM babylon_items bi WHERE bi.stage = %(stage)s)
            """
            params["stage"] = stage
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) AS count FROM content_similarity cs WHERE 1=1 {stage_filter}", params)
                total_pairs = cur.fetchone()["count"]
                cur.execute(f"SELECT MAX(cs.computed_at) AS last_computed FROM content_similarity cs WHERE 1=1 {stage_filter}", params)
                last = cur.fetchone()["last_computed"]
                cur.execute(f"SELECT COUNT(*) AS count FROM content_similarity cs WHERE cs.similarity_score >= 0.85 {stage_filter}", params)
                high_overlap = cur.fetchone()["count"]
                cur.execute(f"SELECT COUNT(*) AS count FROM content_similarity cs WHERE cs.similarity_score >= 0.75 AND cs.similarity_score < 0.85 {stage_filter}", params)
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
        provider: str = "anthropic", opted_out: bool = False,
    ) -> None:
        if opted_out:
            query_text = None
            ci_name = None
        with self._pool.connection() as conn:
            conn.execute(
                """INSERT INTO token_usage (operation, model, input_tokens, output_tokens, ci_name, query_text, provider)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (operation, model, input_tokens, output_tokens, ci_name, query_text, provider),
            )
            conn.commit()

    def get_token_stats(self, days: int | None = 30) -> list[dict[str, Any]]:
        where = "WHERE created_at >= NOW() - %(days)s * INTERVAL '1 day'" if days else ""
        params: dict[str, Any] = {"days": days} if days else {}
        sql = f"""
            SELECT operation, model, COALESCE(provider, 'anthropic') AS provider,
                   COUNT(*) AS calls,
                   SUM(input_tokens) AS input_tokens,
                   SUM(output_tokens) AS output_tokens,
                   SUM(input_tokens + output_tokens) AS total_tokens
            FROM token_usage {where}
            GROUP BY operation, model, COALESCE(provider, 'anthropic') ORDER BY total_tokens DESC
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
                SELECT ce.content_id, ce.content_type, ce.display_name,
                       bi.ci_name, bi.category, bi.stage,
                       bi.showroom_url, bi.showroom_ref, bi.showroom_url_override,
                       bi.content_path, bi.keywords, bi.scan_status,
                       bi.is_published, bi.published_ci_name, bi.base_ci_name,
                       sa.content_hash, sa.last_repo_commit
                FROM content_entities ce
                JOIN babylon_items bi ON bi.content_id = ce.content_id
                LEFT JOIN showroom_analysis sa ON sa.content_id = ce.content_id
                WHERE ce.content_type IN ('lab', 'demo')
                  AND bi.showroom_url IS NOT NULL AND bi.showroom_url != ''
                  AND (bi.is_published IS NULL OR bi.is_published = FALSE)
                  AND (sa.content_id IS NULL OR sa.is_stale = TRUE)
                  AND ce.retired_at IS NULL
                ORDER BY bi.ci_name
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

    def get_stale_check_candidates(self) -> list[dict]:
        sql = """
            SELECT ce.content_id, bi.ci_name, bi.showroom_url, bi.showroom_ref,
                   bi.showroom_url_override, sa.content_hash, sa.last_repo_commit
            FROM content_entities ce
            JOIN babylon_items bi ON bi.content_id = ce.content_id
            JOIN showroom_analysis sa ON sa.content_id = ce.content_id
            WHERE ce.content_type IN ('lab', 'demo')
              AND ce.retired_at IS NULL
        """
        with self._pool.connection() as conn:
            return conn.execute(sql).fetchall()

    def get_sandboxes_needing_summary(self) -> list[dict]:
        sql = """
            SELECT ce.content_id, ce.display_name, ce.summary,
                   bi.ci_name, bi.description, bi.cloud_provider,
                   bi.ocp_version, bi.agd_config
            FROM content_entities ce
            JOIN babylon_items bi ON bi.content_id = ce.content_id
            WHERE ce.content_type = 'sandbox'
              AND ce.retired_at IS NULL
              AND (ce.summary IS NULL
                   OR ce.updated_at < (
                       SELECT COALESCE(MAX(wss.last_scanned), '1970-01-01')
                       FROM workload_scan_state wss
                   ))
        """
        with self._pool.connection() as conn:
            return conn.execute(sql).fetchall()

    def get_scan_dedup_stats(self) -> dict[str, int]:
        with self._pool.connection() as conn:
            cur = conn.execute("""
                SELECT COALESCE(bi.showroom_url_override, bi.showroom_url) AS effective_url,
                       COALESCE(bi.showroom_ref, '') AS showroom_ref, COUNT(*) AS cnt
                FROM babylon_items bi
                JOIN content_entities ce ON ce.content_id = bi.content_id
                LEFT JOIN showroom_analysis sa ON sa.content_id = bi.content_id
                WHERE bi.showroom_url IS NOT NULL AND bi.showroom_url != ''
                  AND (bi.is_published IS NULL OR bi.is_published = FALSE)
                  AND (sa.content_id IS NULL OR sa.is_stale = TRUE)
                  AND ce.retired_at IS NULL
                GROUP BY COALESCE(bi.showroom_url_override, bi.showroom_url), COALESCE(bi.showroom_ref, '')
            """)
            groups = cur.fetchall()
        total = sum(row["cnt"] for row in groups)
        unique = len(groups)
        propagated = total - unique
        return {"total_scannable": total, "unique_pairs": unique, "will_propagate": propagated}

    def get_siblings_by_showroom(self, showroom_url: str, showroom_ref: str | None) -> list[dict[str, Any]]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT ce.*, bi.* FROM content_entities ce "
                "JOIN babylon_items bi ON bi.content_id = ce.content_id "
                "WHERE bi.showroom_url = %s AND COALESCE(bi.showroom_ref, '') = COALESCE(%s, '') "
                "AND ce.retired_at IS NULL ORDER BY bi.ci_name",
                (showroom_url, showroom_ref),
            )
            return cur.fetchall()

    def set_scan_status(self, content_id: str, status: str, error_class: str | None = None, error_message: str | None = None, conn=None):
        def _do(c):
            if status == "success":
                c.execute(
                    "UPDATE babylon_items SET scan_status = 'success', scan_error_class = NULL, scan_error = NULL, scan_failed_at = NULL WHERE content_id = %s",
                    (content_id,),
                )
            else:
                c.execute(
                    "UPDATE babylon_items SET scan_status = %s, scan_error_class = %s, scan_error = %s, scan_failed_at = %s WHERE content_id = %s",
                    (status, error_class, error_message, datetime.now(timezone.utc), content_id),
                )
        if conn:
            _do(conn)
        else:
            with self._pool.connection() as conn:
                _do(conn)
                conn.commit()

    def get_scan_failures(self) -> list[dict]:
        with self._pool.connection() as conn:
            cur = conn.execute("""
                SELECT bi.content_id, bi.ci_name, ce.display_name, bi.stage,
                       bi.scan_error_class, bi.scan_error, bi.scan_failed_at,
                       bi.showroom_url, bi.showroom_url_override
                FROM babylon_items bi
                JOIN content_entities ce ON ce.content_id = bi.content_id
                WHERE bi.scan_status = 'failed' AND ce.retired_at IS NULL
                ORDER BY bi.scan_failed_at DESC
            """)
            return cur.fetchall()

    def set_showroom_url_override(self, content_id: str, override_url: str | None):
        with self._pool.connection() as conn:
            conn.execute("UPDATE babylon_items SET showroom_url_override = %s WHERE content_id = %s", (override_url, content_id))
            conn.commit()

    # ── Status / currency ──

    def get_status_summary(self) -> dict[str, int]:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) as count FROM content_entities WHERE retired_at IS NULL")
                total = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(*) as count FROM babylon_items bi JOIN content_entities ce ON ce.content_id = bi.content_id WHERE bi.is_prod = TRUE AND ce.retired_at IS NULL")
                prod = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(*) as count FROM babylon_items bi JOIN content_entities ce ON ce.content_id = bi.content_id WHERE bi.showroom_url IS NOT NULL AND bi.showroom_url != '' AND (bi.is_published IS NULL OR bi.is_published = FALSE) AND ce.retired_at IS NULL")
                with_showroom = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(*) as count FROM showroom_analysis sa JOIN content_entities ce ON ce.content_id = sa.content_id WHERE ce.retired_at IS NULL")
                analyzed = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(*) as count FROM showroom_analysis sa JOIN content_entities ce ON ce.content_id = sa.content_id WHERE sa.is_stale = TRUE AND ce.retired_at IS NULL")
                stale = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(*) as count FROM babylon_items bi JOIN content_entities ce ON ce.content_id = bi.content_id WHERE bi.scan_status = 'failed' AND ce.retired_at IS NULL")
                scan_failures = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(*) as count FROM content_entities WHERE retired_at IS NOT NULL")
                retired = cur.fetchone()["count"]
        return {"total": total, "prod": prod, "with_showroom": with_showroom, "analyzed": analyzed, "stale": stale, "scan_failures": scan_failures, "retired": retired}

    def get_db_currency(self, stale_days: int = 3) -> dict:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT MAX(bi.last_refreshed) as max_refreshed FROM babylon_items bi JOIN content_entities ce ON ce.content_id = bi.content_id WHERE ce.retired_at IS NULL")
                row = cur.fetchone()
                last_refresh = row["max_refreshed"] if row else None
                catalog_stale = True
                catalog_date = "never"
                if last_refresh:
                    catalog_stale = (datetime.now(timezone.utc) - last_refresh) > timedelta(days=stale_days)
                    catalog_date = last_refresh.strftime("%Y.%m.%d")
                cur.execute("SELECT COUNT(*) as count FROM babylon_items bi JOIN content_entities ce ON ce.content_id = bi.content_id WHERE bi.showroom_url IS NOT NULL AND bi.showroom_url != '' AND (bi.is_published IS NULL OR bi.is_published = FALSE) AND ce.retired_at IS NULL")
                scannable = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(*) as count FROM showroom_analysis sa JOIN content_entities ce ON ce.content_id = sa.content_id WHERE ce.retired_at IS NULL")
                analyzed = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(*) as count FROM showroom_analysis sa JOIN content_entities ce ON ce.content_id = sa.content_id WHERE sa.is_stale = TRUE AND ce.retired_at IS NULL")
                stale_count = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(*) as count FROM babylon_items bi JOIN content_entities ce ON ce.content_id = bi.content_id WHERE bi.scan_status = 'failed' AND ce.retired_at IS NULL")
                failed_count = cur.fetchone()["count"]
                cur.execute(
                    "SELECT MAX(completed_at) as last_run FROM jobs "
                    "WHERE job_type = 'maintenance' AND status = 'complete'"
                )
                row = cur.fetchone()
                last_pipeline_run = row["last_run"] if row else None
        unanalyzed = max(0, scannable - analyzed - failed_count)
        incomplete = stale_count + unanalyzed + failed_count
        analysis_stale = (incomplete / scannable > 0.10) if scannable > 0 else True
        analysis_date = last_pipeline_run.strftime("%Y.%m.%d") if last_pipeline_run else "never"
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) as count FROM content_entities WHERE retired_at IS NULL")
                total = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(*) as count FROM babylon_items bi JOIN content_entities ce ON ce.content_id = bi.content_id WHERE bi.is_prod = TRUE AND ce.retired_at IS NULL")
                prod = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(*) as count FROM babylon_items bi JOIN content_entities ce ON ce.content_id = bi.content_id WHERE bi.stage = 'dev' AND ce.retired_at IS NULL")
                dev = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(*) as count FROM babylon_items bi JOIN content_entities ce ON ce.content_id = bi.content_id WHERE bi.stage = 'event' AND ce.retired_at IS NULL")
                event = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(*) as count FROM content_entities WHERE retired_at IS NOT NULL")
                retired = cur.fetchone()["count"]
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) as cnt FROM (
                        SELECT DISTINCT COALESCE(bi.showroom_url_override, bi.showroom_url), COALESCE(bi.showroom_ref, '')
                        FROM babylon_items bi
                        JOIN content_entities ce ON ce.content_id = bi.content_id
                        WHERE bi.showroom_url IS NOT NULL AND bi.showroom_url != ''
                          AND (bi.is_published IS NULL OR bi.is_published = FALSE)
                          AND ce.retired_at IS NULL
                    ) sub
                """)
                unique_showrooms = cur.fetchone()["cnt"]
        return {
            "total": total, "prod": prod, "dev": dev, "event": event, "retired": retired,
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
            event_url = None
            if user_email:
                user_email = hashlib.sha256(user_email.encode()).hexdigest()[:16]
        with self._pool.connection() as conn:
            cur = conn.execute("""
                INSERT INTO advisor_sessions (session_id, turn_index, user_email, query_text, event_url, results_json, overall_assessment, opted_out)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (session_id, turn_index, user_email, query_text, event_url,
                  Jsonb(results) if results is not None else None, overall_assessment, opted_out))
            row_id = cur.fetchone()["id"]
            conn.commit()
        return row_id

    def update_advisor_session_choice(
        self, session_id: str, turn_index: int,
        chosen_ci_name: str | None = None,
        chosen_content_id: str | None = None,
        user_email: str | None = None,
    ) -> None:
        if user_email is not None:
            sql = "UPDATE advisor_sessions SET chosen_ci_name = %s, chosen_content_id = %s, chosen_at = NOW() WHERE session_id = %s AND turn_index = %s AND user_email = %s"
            params = (chosen_ci_name, chosen_content_id, session_id, turn_index, user_email)
        else:
            sql = "UPDATE advisor_sessions SET chosen_ci_name = %s, chosen_content_id = %s, chosen_at = NOW() WHERE session_id = %s AND turn_index = %s"
            params = (chosen_ci_name, chosen_content_id, session_id, turn_index)
        with self._pool.connection() as conn:
            conn.execute(sql, params)
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

    def get_advisor_session(self, session_id: str, user_email: str | None = None) -> list[dict]:
        if user_email is not None:
            sql = "SELECT * FROM advisor_sessions WHERE session_id = %s AND user_email = %s ORDER BY turn_index"
            params = (session_id, user_email)
        else:
            sql = "SELECT * FROM advisor_sessions WHERE session_id = %s ORDER BY turn_index"
            params = (session_id,)
        with self._pool.connection() as conn:
            cur = conn.execute(sql, params)
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

    def has_active_recommend_job(self, user_email: str) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT 1 FROM jobs WHERE job_type = 'recommend' AND created_by = %s AND status IN ('queued', 'running') LIMIT 1",
                (user_email,),
            )
            return cur.fetchone() is not None

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

    def complete_job(self, job_id: str, result_json: dict | None = None, error: str | None = None, conn=None) -> None:
        status = "failed" if error else "complete"
        def _do(c):
            c.execute(
                "UPDATE jobs SET status = %s, result_json = %s, error = %s, completed_at = %s WHERE id = %s",
                (status, Jsonb(result_json) if result_json else None, error, datetime.now(timezone.utc), job_id),
            )
        if conn:
            _do(conn)
        else:
            with self._pool.connection() as conn:
                _do(conn)
                conn.commit()

    def complete_scan(self, content_id: str, job_id: str, scan_status: str,
                      result_json: dict | None = None, error: str | None = None,
                      error_class: str | None = None, error_message: str | None = None) -> None:
        with self._pool.connection() as conn:
            self.set_scan_status(content_id, scan_status, error_class=error_class, error_message=error_message, conn=conn)
            self.complete_job(job_id, result_json=result_json, error=error, conn=conn)
            conn.commit()

    def fail_job(self, job_id: str, error: str) -> None:
        self.complete_job(job_id, error=error)

    def cleanup_orphaned_jobs(self, max_age_seconds: int = 1800, maintenance_max_age_seconds: int = 7200) -> int:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "UPDATE jobs SET status = 'failed', error = 'Orphaned: exceeded max running time' "
                "WHERE status = 'running' AND ("
                "  (job_type != 'maintenance' AND COALESCE(started_at, created_at) < NOW() - make_interval(secs => %s)) OR "
                "  (job_type = 'maintenance' AND COALESCE(started_at, created_at) < NOW() - make_interval(secs => %s))"
                ") RETURNING id, job_type",
                (max_age_seconds, maintenance_max_age_seconds),
            )
            count = len(cur.fetchall())
            conn.commit()
        return count

    def prune_old_jobs(self, retain_days: int = 30) -> int:
        """Delete completed/failed jobs older than retain_days, except advisor queries and maintenance.

        The 'recommend' queue jobs are retained indefinitely — they represent real
        user searches and are intended for future recommendation quality analysis.
        Maintenance jobs are retained — their completion timestamps drive the
        analysis status display in the masthead.
        """
        with self._pool.connection() as conn:
            cur = conn.execute(
                """DELETE FROM jobs
                   WHERE queue != 'recommend'
                     AND job_type != 'maintenance'
                     AND created_at < NOW() - make_interval(days => %s)
                     AND status IN ('complete', 'completed', 'failed')
                   RETURNING id""",
                (retain_days,),
            )
            count = len(cur.fetchall())
            conn.commit()
        return count

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

    # ── Performance metrics (replaces reporting_metrics) ──

    def upsert_performance_channels(self, rows: list[dict]) -> int:
        if not rows:
            return 0
        sql = """
            INSERT INTO performance_channels (
                content_id, channel,
                provisions, unique_users, requests, completions,
                pipeline_touched, closed_amount, total_cost, avg_cost_per_provision,
                success_ratio, first_activity, last_activity,
                windowed_metrics, synced_at
            ) VALUES (
                %(content_id)s, %(channel)s,
                %(provisions)s, %(unique_users)s, %(requests)s, %(completions)s,
                %(pipeline_touched)s, %(closed_amount)s, %(total_cost)s, %(avg_cost_per_provision)s,
                %(success_ratio)s, %(first_activity)s, %(last_activity)s,
                %(windowed_metrics)s::jsonb, NOW()
            )
            ON CONFLICT (content_id, channel) DO UPDATE SET
                provisions = EXCLUDED.provisions,
                unique_users = EXCLUDED.unique_users,
                requests = EXCLUDED.requests,
                completions = EXCLUDED.completions,
                pipeline_touched = EXCLUDED.pipeline_touched,
                closed_amount = EXCLUDED.closed_amount,
                total_cost = EXCLUDED.total_cost,
                avg_cost_per_provision = EXCLUDED.avg_cost_per_provision,
                success_ratio = EXCLUDED.success_ratio,
                first_activity = EXCLUDED.first_activity,
                last_activity = EXCLUDED.last_activity,
                windowed_metrics = EXCLUDED.windowed_metrics,
                synced_at = NOW()
        """
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                for row in rows:
                    cur.execute(sql, row)
            conn.commit()
        return len(rows)

    def upsert_performance_score(self, content_id: str, score: int,
                                  breakdown: dict | None = None,
                                  channel_scores: dict | None = None) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                """INSERT INTO performance_scores (content_id, performance_score, score_breakdown, channel_scores, computed_at)
                   VALUES (%s, %s, %s, %s, NOW())
                   ON CONFLICT (content_id) DO UPDATE SET
                       performance_score = EXCLUDED.performance_score,
                       score_breakdown = EXCLUDED.score_breakdown,
                       channel_scores = EXCLUDED.channel_scores,
                       computed_at = NOW()""",
                (content_id, score,
                 Jsonb(breakdown) if breakdown else None,
                 Jsonb(channel_scores) if channel_scores else None),
            )
            conn.commit()

    def get_performance_channels(self, content_id: str) -> list[dict]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT * FROM performance_channels WHERE content_id = %s ORDER BY channel",
                (content_id,),
            )
            return cur.fetchall()

    def get_performance_score(self, content_id: str) -> dict | None:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT * FROM performance_scores WHERE content_id = %s",
                (content_id,),
            )
            return cur.fetchone()

    def set_ignored_until(self, content_id: str, until_date: str) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "UPDATE performance_scores SET ignored_until = %s WHERE content_id = %s",
                (until_date, content_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def clear_ignored(self, content_id: str) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "UPDATE performance_scores SET ignored_until = NULL WHERE content_id = %s",
                (content_id,),
            )
            conn.commit()
            return cur.rowcount > 0

    def get_catalog_base_names(self, include_retired: bool = False) -> dict[str, str]:
        retired_filter = "" if include_retired else "AND ce.retired_at IS NULL"
        sql = f"""
            SELECT DISTINCT ON (base)
                substring(bi.ci_name FROM '^(.+)\\.[^.]+$') AS base,
                ce.display_name
            FROM babylon_items bi
            JOIN content_entities ce ON ce.content_id = bi.content_id
            WHERE 1=1 {retired_filter}
            ORDER BY base, CASE bi.stage WHEN 'prod' THEN 0 WHEN 'event' THEN 1 ELSE 2 END
        """
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                return {r["base"]: r["display_name"] for r in cur.fetchall() if r["base"]}

    def get_published_base_mapping(self) -> dict[str, str]:
        sql = """
            SELECT DISTINCT ON (base_base_name)
                substring(base_bi.ci_name FROM '^(.+)\\.[^.]+$') AS base_base_name,
                substring(base_bi.published_ci_name FROM '^(.+)\\.[^.]+$') AS published_base_name
            FROM babylon_items base_bi
            JOIN content_entities base_ce ON base_ce.content_id = base_bi.content_id
            WHERE base_bi.published_ci_name IS NOT NULL
              AND base_ce.retired_at IS NULL
              AND EXISTS (
                  SELECT 1 FROM babylon_items pub_bi
                  JOIN content_entities pub_ce ON pub_ce.content_id = pub_bi.content_id
                  WHERE pub_bi.ci_name = base_bi.published_ci_name
                    AND pub_ce.retired_at IS NULL
              )
            ORDER BY base_base_name,
                     CASE base_bi.stage WHEN 'prod' THEN 0 WHEN 'event' THEN 1 ELSE 2 END
        """
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                return {
                    r["base_base_name"]: r["published_base_name"]
                    for r in cur.fetchall()
                    if r["base_base_name"] and r["published_base_name"]
                }

    def delete_orphan_performance_data(self, synced_content_ids: set[str] | None = None) -> int:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                deleted = 0
                if synced_content_ids:
                    cur.execute(
                        "DELETE FROM performance_channels WHERE content_id NOT IN (SELECT content_id FROM content_entities) AND content_id != ALL(%s)",
                        (list(synced_content_ids),),
                    )
                    deleted += cur.rowcount
                    cur.execute(
                        "DELETE FROM performance_scores WHERE content_id NOT IN (SELECT content_id FROM content_entities) AND content_id != ALL(%s)",
                        (list(synced_content_ids),),
                    )
                    deleted += cur.rowcount
                else:
                    cur.execute("DELETE FROM performance_channels WHERE content_id NOT IN (SELECT content_id FROM content_entities)")
                    deleted += cur.rowcount
                    cur.execute("DELETE FROM performance_scores WHERE content_id NOT IN (SELECT content_id FROM content_entities)")
                    deleted += cur.rowcount
            conn.commit()
        return deleted

    def resolve_base_names_to_content_ids(self, base_names: set[str]) -> dict[str, str]:
        if not base_names:
            return {}
        STAGE_SUFFIXES = [".prod", ".event", ".dev", ".test"]
        sql = """
            SELECT bi.ci_name, bi.content_id, ce.retired_at,
                   CASE bi.stage
                       WHEN 'prod' THEN 1 WHEN 'event' THEN 2
                       WHEN 'dev' THEN 3 WHEN 'test' THEN 4
                       ELSE 5
                   END AS stage_priority
            FROM babylon_items bi
            JOIN content_entities ce ON ce.content_id = bi.content_id
            ORDER BY stage_priority, ce.retired_at NULLS FIRST
        """
        result = {}
        with self._pool.connection() as conn:
            rows = conn.execute(sql).fetchall()
        for row in rows:
            ci_name = row["ci_name"]
            for suffix in STAGE_SUFFIXES:
                if ci_name.endswith(suffix):
                    base = ci_name[:-len(suffix)]
                    if base in base_names and base not in result:
                        result[base] = row["content_id"]
                    break
        return result

    def list_performance_data(
        self,
        sort_by: str = "performance_score",
        sort_dir: str = "desc",
        min_score: int | None = None,
        category: str | None = None,
        has_prod: bool | None = None,
        search: str | None = None,
        workflow_status: str | None = None,
    ) -> list[dict]:
        allowed_sorts = {
            "performance_score", "provisions", "total_cost",
            "closed_amount", "pipeline_touched", "display_name",
            "touched_roi", "closed_roi",
        }
        if sort_by not in allowed_sorts:
            sort_by = "performance_score"
        direction = "ASC" if sort_dir.lower() == "asc" else "DESC"

        conditions = ["ce.retired_at IS NULL"]
        params: dict = {}

        if min_score is not None:
            conditions.append("ps.performance_score >= %(min_score)s")
            params["min_score"] = min_score

        if search:
            words = search.strip().split()
            if len(words) == 1:
                conditions.append(
                    "(ce.display_name ILIKE %(search)s OR bi.ci_name ILIKE %(search)s)"
                )
                params["search"] = f"%{search}%"
            else:
                word_conds = []
                for i, word in enumerate(words[:6]):
                    key = f"rsw{i}"
                    word_conds.append(f"(ce.display_name ILIKE %({key})s OR bi.ci_name ILIKE %({key})s)")
                    params[key] = f"%{word}%"
                conditions.append(f"({' AND '.join(word_conds)})")

        if category:
            conditions.append("bi.category = %(category)s")
            params["category"] = category

        if has_prod is True:
            conditions.append("bi.is_prod = TRUE")
        elif has_prod is False:
            conditions.append("(bi.is_prod IS NULL OR bi.is_prod = FALSE)")

        if workflow_status == "none":
            conditions.append("rw.content_id IS NULL")
        elif workflow_status == "in_process":
            conditions.append("rw.step_approved_at IS NOT NULL AND rw.status IN ('approved', 'notified')")
        elif workflow_status:
            conditions.append("rw.status = %(workflow_status)s")
            params["workflow_status"] = workflow_status

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        roi_sorts = {
            "touched_roi": "pc.pipeline_touched / NULLIF(pc.total_cost, 0)",
            "closed_roi": "pc.closed_amount / NULLIF(pc.total_cost, 0)",
        }
        sort_col = sort_by
        if sort_by == "performance_score":
            order_expr = "ps.performance_score"
        elif sort_by in roi_sorts:
            order_expr = roi_sorts[sort_by]
        elif sort_by == "display_name":
            order_expr = "ce.display_name"
        else:
            order_expr = f"pc.{sort_by}"

        sql = f"""
            SELECT ps.content_id, ps.performance_score, ps.score_breakdown,
                   ps.channel_scores, ps.ignored_until,
                   ce.display_name, ce.content_type,
                   bi.ci_name, bi.category, bi.stage, bi.is_prod,
                   pc.provisions, pc.unique_users, pc.requests, pc.completions,
                   pc.pipeline_touched, pc.closed_amount, pc.total_cost,
                   pc.avg_cost_per_provision, pc.success_ratio,
                   pc.first_activity, pc.last_activity,
                   pc.windowed_metrics, pc.synced_at,
                   CASE WHEN rw.step_approved_at IS NOT NULL THEN rw.status END AS workflow_status,
                   rw.jira_key, rw.retirement_target_date
            FROM performance_scores ps
            JOIN content_entities ce ON ce.content_id = ps.content_id
            LEFT JOIN babylon_items bi ON bi.content_id = ps.content_id
            LEFT JOIN performance_channels pc ON pc.content_id = ps.content_id AND pc.channel = 'rhdp'
            LEFT JOIN retirement_workflow rw ON rw.content_id = ps.content_id
            {where}
            ORDER BY {order_expr} {direction} NULLS LAST
        """
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql, params)
                return cur.fetchall()

    def get_stages_for_base_names(self, base_names: list[str], include_retired: bool = False) -> dict[str, list[dict]]:
        if not base_names:
            return {}
        from rcars.services.reporting_sync import extract_base_name
        placeholders = ",".join(["%s"] * len(base_names))
        retired_filter = "" if include_retired else "AND ce.retired_at IS NULL"
        sql = f"""
            SELECT bi.ci_name, bi.catalog_namespace, bi.stage, ce.retired_at,
                   (bi.showroom_url IS NOT NULL AND bi.showroom_url != '') AS has_showroom
            FROM babylon_items bi
            JOIN content_entities ce ON ce.content_id = bi.content_id
            WHERE substring(bi.ci_name FROM '^(.+)\\.[^.]+$') IN ({placeholders})
              {retired_filter}
            ORDER BY bi.ci_name
        """
        result: dict[str, list[dict]] = {}
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql, base_names)
                for row in cur.fetchall():
                    base = extract_base_name(row["ci_name"])
                    stage_info = {
                        "stage": row["stage"],
                        "ci_name": row["ci_name"],
                        "catalog_url": f"https://catalog.demo.redhat.com/catalog?item={row['catalog_namespace']}/{row['ci_name']}",
                        "has_showroom": row["has_showroom"],
                    }
                    result.setdefault(base, []).append(stage_info)
        return result

    def get_owners_for_base_names(self, base_names: list[str]) -> dict[str, list[dict]]:
        if not base_names:
            return {}
        from rcars.services.reporting_sync import extract_base_name
        placeholders = ",".join(["%s"] * len(base_names))
        sql = f"""
            SELECT bi.ci_name, bi.owners_json
            FROM babylon_items bi
            JOIN content_entities ce ON ce.content_id = bi.content_id
            WHERE substring(bi.ci_name FROM '^(.+)\\.[^.]+$') IN ({placeholders})
              AND bi.owners_json IS NOT NULL
              AND ce.retired_at IS NULL
            ORDER BY CASE WHEN bi.stage = 'prod' THEN 0 ELSE 1 END
        """
        result: dict[str, list[dict]] = {}
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql, base_names)
                for row in cur.fetchall():
                    base = extract_base_name(row["ci_name"])
                    if base in result:
                        continue
                    oj = row["owners_json"]
                    if isinstance(oj, dict):
                        maintainers = oj.get("maintainer", [])
                        owners = []
                        for m in (maintainers if isinstance(maintainers, list) else []):
                            if isinstance(m, dict) and m.get("email"):
                                owners.append({"name": m.get("name", ""), "email": m["email"]})
                        if owners:
                            result[base] = owners
        return result

    def get_reporting_sync_status(self) -> dict:
        sql = """
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE pc.provisions > 0) AS with_provisions,
                COUNT(*) FILTER (WHERE pc.total_cost > 0) AS with_cost,
                COUNT(*) FILTER (WHERE pc.closed_amount > 0) AS with_sales,
                COUNT(*) FILTER (WHERE ps.performance_score >= 55) AS high,
                COUNT(*) FILTER (WHERE ps.performance_score >= 35 AND ps.performance_score < 55) AS review,
                COUNT(*) FILTER (WHERE ps.performance_score < 35) AS keepers,
                MAX(pc.synced_at) AS last_synced
            FROM performance_scores ps
            LEFT JOIN performance_channels pc ON pc.content_id = ps.content_id AND pc.channel = 'rhdp'
        """
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql)
                return cur.fetchone()

    def has_prod_stage(self, base_name: str) -> bool:
        sql = """
            SELECT 1 FROM babylon_items bi
            JOIN content_entities ce ON ce.content_id = bi.content_id
            WHERE bi.ci_name = %s AND ce.retired_at IS NULL LIMIT 1
        """
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (f"{base_name}.prod",))
                return cur.fetchone() is not None

    def get_all_base_names_with_prod(self) -> set[str]:
        sql = """
            SELECT DISTINCT substring(bi.ci_name FROM '^(.+)\\.prod$') AS base_name
            FROM babylon_items bi
            JOIN content_entities ce ON ce.content_id = bi.content_id
            WHERE bi.ci_name LIKE '%%.prod' AND ce.retired_at IS NULL
        """
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql)
                return {row["base_name"] for row in cur.fetchall() if row["base_name"]}

    def get_fully_retired_base_names(self) -> set[str]:
        sql = """
            SELECT base FROM (
                SELECT substring(bi.ci_name FROM '^(.+)\\.[^.]+$') AS base,
                       COUNT(*) FILTER (WHERE ce.retired_at IS NULL) AS active_count
                FROM babylon_items bi
                JOIN content_entities ce ON ce.content_id = bi.content_id
                GROUP BY substring(bi.ci_name FROM '^(.+)\\.[^.]+$')
            ) grouped
            WHERE base IS NOT NULL AND active_count = 0
        """
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql)
                return {row["base"] for row in cur.fetchall()}

    # ── Retirement Workflow ──

    def get_retirement_workflow(self, content_id: str) -> dict | None:
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT * FROM retirement_workflow WHERE content_id = %s",
                    (content_id,),
                )
                return cur.fetchone()

    def upsert_retirement_workflow(self, content_id: str, fields: dict) -> dict:
        all_fields = dict(fields)
        all_fields["content_id"] = content_id

        step_fields = {"step_approved_at", "step_notified_at", "step_started_at", "step_retired_at"}
        if "status" not in all_fields and step_fields & all_fields.keys():
            from rcars.services.retirement import derive_status
            all_fields["status"] = derive_status(all_fields)

        columns = []
        placeholders = []
        params = []
        update_parts = []

        for col, val in all_fields.items():
            columns.append(col)
            if val == "NOW()":
                placeholders.append("NOW()")
                update_parts.append(f"{col} = NOW()")
            elif col == "approval_snapshot" and isinstance(val, dict):
                placeholders.append("%s::jsonb")
                params.append(json.dumps(val))
                update_parts.append(f"{col} = %s::jsonb")
            else:
                placeholders.append("%s")
                params.append(val)
                update_parts.append(f"{col} = %s")

        if "updated_at" not in all_fields:
            columns.append("updated_at")
            placeholders.append("NOW()")
            update_parts.append("updated_at = NOW()")

        update_params = []
        for col, val in all_fields.items():
            if col == "content_id":
                continue
            if val == "NOW()":
                continue
            elif col == "approval_snapshot" and isinstance(val, dict):
                update_params.append(json.dumps(val))
            else:
                update_params.append(val)

        sql = (
            f"INSERT INTO retirement_workflow ({', '.join(columns)}) "
            f"VALUES ({', '.join(placeholders)}) "
            f"ON CONFLICT (content_id) DO UPDATE SET "
            f"{', '.join(p for p in update_parts if not p.startswith('content_id'))} "
            f"RETURNING *"
        )

        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql, params + update_params)
                row = cur.fetchone()
            conn.commit()
        return row

    def delete_retirement_workflow(self, content_id: str) -> bool:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM retirement_workflow WHERE content_id = %s",
                    (content_id,),
                )
                deleted = cur.rowcount > 0
            conn.commit()
        return deleted

    def list_retirement_workflows(self, status: str | None = None) -> list[dict]:
        if status:
            sql = "SELECT * FROM retirement_workflow WHERE status = %s ORDER BY updated_at DESC"
            params = (status,)
        else:
            sql = "SELECT * FROM retirement_workflow ORDER BY updated_at DESC"
            params = ()
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql, params)
                return cur.fetchall()

    def auto_close_retired_workflows(self, retired_content_ids: set[str]) -> int:
        if not retired_content_ids:
            return 0
        placeholders = ",".join(["%s"] * len(retired_content_ids))
        sql = (
            f"UPDATE retirement_workflow "
            f"SET step_retired_at = NOW(), status = 'retired', updated_at = NOW() "
            f"WHERE content_id IN ({placeholders}) "
            f"AND step_retired_at IS NULL"
        )
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, list(retired_content_ids))
                count = cur.rowcount
            conn.commit()
        return count

    # ── API Keys ──

    def create_api_key(
        self,
        key_hash: str,
        key_prefix: str,
        name: str,
        created_by: str,
        role: str,
        expires_at: datetime | None,
    ) -> int:
        with self.pool.connection() as conn:
            row = conn.execute(
                """INSERT INTO api_keys (key_hash, key_prefix, name, created_by, role, expires_at)
                   VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                (key_hash, key_prefix, name, created_by, role, expires_at),
            ).fetchone()
            conn.commit()
            return row["id"]

    def revoke_user_cli_keys(self, user_email: str) -> int:
        """Revoke all active CLI session keys for a user (role='user' with expiry)."""
        with self.pool.connection() as conn:
            rows = conn.execute(
                """UPDATE api_keys SET revoked_at = NOW()
                   WHERE created_by = %s AND role = 'user'
                     AND expires_at IS NOT NULL
                     AND revoked_at IS NULL
                     AND expires_at > NOW()
                   RETURNING id""",
                (user_email,),
            ).fetchall()
            conn.commit()
        return len(rows)

    def prune_expired_api_keys(self, retain_days: int = 30) -> int:
        """Hard-delete API keys that expired or were revoked more than retain_days ago."""
        with self.pool.connection() as conn:
            cur = conn.execute(
                """DELETE FROM api_keys
                   WHERE (expires_at IS NOT NULL AND expires_at < NOW() - %s * INTERVAL '1 day')
                      OR (revoked_at IS NOT NULL AND revoked_at < NOW() - %s * INTERVAL '1 day')""",
                (retain_days, retain_days),
            )
            count = cur.rowcount
            conn.commit()
        return count

    def get_api_key_by_hash(self, key_hash: str) -> dict | None:
        with self.pool.connection() as conn:
            row = conn.execute(
                """SELECT * FROM api_keys
                   WHERE key_hash = %s
                     AND revoked_at IS NULL
                     AND (expires_at IS NULL OR expires_at > NOW())""",
                (key_hash,),
            ).fetchone()
            return dict(row) if row else None

    def list_api_keys(self, active_only: bool = True) -> list[dict]:
        with self.pool.connection() as conn:
            if active_only:
                rows = conn.execute(
                    """SELECT id, key_prefix, name, created_by, role, scopes,
                              created_at, expires_at, last_used_at, revoked_at
                       FROM api_keys
                       WHERE revoked_at IS NULL
                         AND (expires_at IS NULL OR expires_at > NOW())
                       ORDER BY created_at DESC"""
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT id, key_prefix, name, created_by, role, scopes,
                              created_at, expires_at, last_used_at, revoked_at
                       FROM api_keys ORDER BY created_at DESC"""
                ).fetchall()
            return [dict(r) for r in rows]

    def revoke_api_key(self, key_id: int) -> dict | None:
        with self.pool.connection() as conn:
            row = conn.execute(
                """UPDATE api_keys SET revoked_at = NOW()
                   WHERE id = %s AND revoked_at IS NULL
                   RETURNING id, key_hash, revoked_at""",
                (key_id,),
            ).fetchone()
            return dict(row) if row else None

    def touch_api_key(self, key_id: int) -> None:
        with self.pool.connection() as conn:
            conn.execute(
                "UPDATE api_keys SET last_used_at = NOW() WHERE id = %s",
                (key_id,),
            )
