import os
import pytest
from rcars.db.database import Database

TEST_DB_URL = os.environ.get(
    "RCARS_TEST_DATABASE_URL",
    "postgresql://rcars:dev@localhost:5432/rcars_test",
)


@pytest.fixture
def db():
    # Use a separate connection to drop schema to avoid killing pool connections
    import psycopg
    from psycopg.rows import dict_row
    with psycopg.connect(TEST_DB_URL, row_factory=dict_row) as conn:
        conn.autocommit = True
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cur = conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        )
        for row in cur.fetchall():
            conn.execute(f"DROP TABLE IF EXISTS {row['tablename']} CASCADE")

    database = Database(TEST_DB_URL)
    database.create_schema()
    yield database
    database.close()


def test_schema_creation(db):
    with db.pool.connection() as conn:
        cur = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"
        )
        tables = [row["table_name"] for row in cur.fetchall()]
    assert "catalog_items" in tables
    assert "showroom_analysis" in tables
    assert "embeddings" in tables
    assert "enrichment_tags" in tables
    assert "token_usage" in tables
    assert "advisor_sessions" in tables
    assert "jobs" in tables
    assert "analysis_log" in tables
    assert "api_keys" in tables


def test_upsert_and_get_catalog_item(db):
    item = {
        "ci_name": "test.item.prod",
        "display_name": "Test Item",
        "category": "Workshops",
        "stage": "prod",
    }
    db.upsert_catalog_item(item)
    result = db.get_catalog_item("test.item.prod")
    assert result is not None
    assert result["display_name"] == "Test Item"


def test_upsert_updates_existing(db):
    db.upsert_catalog_item({"ci_name": "test.item.prod", "display_name": "V1", "stage": "prod"})
    db.upsert_catalog_item({"ci_name": "test.item.prod", "display_name": "V2", "stage": "prod"})
    result = db.get_catalog_item("test.item.prod")
    assert result["display_name"] == "V2"


def test_list_catalog_items(db):
    db.upsert_catalog_item({"ci_name": "a.prod", "stage": "prod", "is_prod": True, "category": "Demos"})
    db.upsert_catalog_item({"ci_name": "b.dev", "stage": "dev", "is_prod": False, "category": "Workshops"})
    assert len(db.list_catalog_items()) == 2
    assert len(db.list_catalog_items(prod_only=True)) == 1
    assert len(db.list_catalog_items(stage="dev")) == 1
    assert len(db.list_catalog_items(category="Demos")) == 1


def test_job_lifecycle(db):
    job_id = db.create_job(job_type="recommend", queue="recommend", created_by="test@redhat.com")
    assert job_id is not None

    job = db.get_job(job_id)
    assert job["status"] == "queued"
    assert job["created_by"] == "test@redhat.com"

    db.update_job_status(job_id, "running")
    job = db.get_job(job_id)
    assert job["status"] == "running"
    assert job["started_at"] is not None

    db.complete_job(job_id, result_json={"results": 5})
    job = db.get_job(job_id)
    assert job["status"] == "complete"
    assert job["result_json"]["results"] == 5
    assert job["completed_at"] is not None


def test_job_failure(db):
    job_id = db.create_job(job_type="scan", queue="analyze", created_by="test@redhat.com")
    db.fail_job(job_id, error="Something broke")
    job = db.get_job(job_id)
    assert job["status"] == "failed"
    assert job["error"] == "Something broke"


def test_list_jobs(db):
    db.create_job(job_type="recommend", queue="recommend")
    db.create_job(job_type="scan", queue="analyze")
    db.create_job(job_type="scan", queue="analyze")
    assert len(db.list_jobs()) == 3
    assert len(db.list_jobs(job_type="scan")) == 2


def test_enrichment_tags(db):
    db.upsert_catalog_item({"ci_name": "test.item", "stage": "prod"})
    db.add_enrichment_tag("test.item", "lifecycle", "active", added_by="curator@redhat.com")
    db.add_enrichment_tag("test.item", "event", "summit-2026")
    tags = db.get_enrichment_tags("test.item")
    assert len(tags) == 2
    assert tags[0]["tag_type"] == "lifecycle"

    db.remove_enrichment_tag("test.item", "lifecycle", "active")
    tags = db.get_enrichment_tags("test.item")
    assert len(tags) == 1


def test_token_usage(db):
    db.log_token_usage("triage", "claude-haiku-4-5", 1000, 200, query_text="test query")
    db.log_token_usage("rationale", "claude-sonnet-4-6", 2000, 500, query_text="test query")
    stats = db.get_token_stats(days=1)
    assert len(stats) == 2
    queries = db.get_recent_queries(days=1)
    assert len(queries) >= 1


def test_content_path(db):
    db.upsert_catalog_item({"ci_name": "test.nonstandard", "stage": "prod"})
    db.set_content_path("test.nonstandard", "docs/labs/")
    item = db.get_catalog_item("test.nonstandard")
    assert item["content_path"] == "docs/labs/"


def test_advisor_session(db):
    row_id = db.log_advisor_session(
        session_id="sess-1", turn_index=0, user_email="user@redhat.com",
        query_text="find openshift content", event_url=None,
        results=[{"ci_name": "test.item", "tier": "green"}],
        overall_assessment="Good match found.",
    )
    assert row_id is not None

    sessions = db.list_advisor_sessions(user_email="user@redhat.com")
    assert len(sessions) == 1

    turns = db.get_advisor_session("sess-1")
    assert len(turns) == 1
    assert turns[0]["query_text"] == "find openshift content"

    db.update_advisor_session_choice("sess-1", 0, "test.item")
    turns = db.get_advisor_session("sess-1")
    assert turns[0]["chosen_ci_name"] == "test.item"


# ── Filtered catalog query tests ──


def _seed_items(db):
    """Seed test data for filtered catalog queries."""
    items = [
        {"ci_name": "ns.ocp-ai-workshop.prod", "display_name": "OpenShift AI Workshop",
         "stage": "prod", "catalog_namespace": "babylon-catalog-prod",
         "is_prod": True, "is_agd_v2": True, "agd_config": "ocp-cnv",
         "cloud_provider": "ec2", "showroom_url": "https://github.com/example/ai"},
        {"ci_name": "ns.pipelines-lab.prod", "display_name": "Pipelines Lab",
         "stage": "prod", "catalog_namespace": "babylon-catalog-prod",
         "is_prod": True, "is_agd_v2": True, "agd_config": "ocp-workloads",
         "cloud_provider": "azure", "showroom_url": "https://github.com/example/pipe"},
        {"ci_name": "ns.getting-started.prod", "display_name": "Getting Started",
         "stage": "prod", "catalog_namespace": "babylon-catalog-prod",
         "is_prod": True, "is_agd_v2": False,
         "showroom_url": "https://github.com/example/start"},
        {"ci_name": "ns.ai-dev.dev", "display_name": "AI Dev Build",
         "stage": "dev", "catalog_namespace": "babylon-catalog-dev",
         "is_prod": False, "is_agd_v2": True, "agd_config": "ocp-cnv",
         "cloud_provider": "ec2"},
        {"ci_name": "zt-ns.zt-demo.prod", "display_name": "ZT Demo",
         "stage": "prod", "catalog_namespace": "zt-babylon-catalog-prod",
         "is_prod": True, "is_agd_v2": False,
         "showroom_url": "https://github.com/example/zt"},
        {"ci_name": "ns.stale-item.prod", "display_name": "Stale Item",
         "stage": "prod", "catalog_namespace": "babylon-catalog-prod",
         "is_prod": True, "showroom_url": "https://github.com/example/stale"},
        {"ci_name": "ns.failed-item.prod", "display_name": "Failed Item",
         "stage": "prod", "catalog_namespace": "babylon-catalog-prod",
         "is_prod": True, "showroom_url": "https://github.com/example/failed"},
    ]
    for item in items:
        db.upsert_catalog_item(item)
    db.set_scan_status("ns.stale-item.prod", "success")
    db.set_scan_status("ns.failed-item.prod", "failed", error_class="clone_failed", error_message="test error")
    db.upsert_showroom_analysis({"ci_name": "ns.stale-item.prod", "summary": "test", "is_stale": True})
    db.upsert_showroom_analysis({"ci_name": "ns.failed-item.prod", "summary": "test", "enrichment_review_needed": True})
    with db.pool.connection() as conn:
        conn.execute(
            "INSERT INTO catalog_item_workloads (ci_name, workload_fqcn, workload_role, workload_collection) "
            "VALUES (%s, %s, %s, %s)",
            ("ns.ocp-ai-workshop.prod", "agnosticd.ai_workloads.openshift_ai", "openshift_ai", "ai_workloads"),
        )
        conn.execute(
            "INSERT INTO workload_mapping (workload_role, product_name, verified) VALUES (%s, %s, %s)",
            ("openshift_ai", "OpenShift AI", True),
        )
        conn.execute(
            "INSERT INTO workload_aliases (product_name, alias) VALUES (%s, %s)",
            ("OpenShift AI", "RHOAI"),
        )
        conn.commit()


def test_filtered_catalog_default(db):
    """Default query returns prod items only, paginated."""
    _seed_items(db)
    result = db.list_catalog_items_filtered()
    assert result["total"] >= 5
    assert all(item["stage"] == "prod" for item in result["items"])


def test_filtered_catalog_search(db):
    """Text search matches display_name case-insensitively."""
    _seed_items(db)
    result = db.list_catalog_items_filtered(search="openshift ai")
    assert result["total"] >= 1
    assert any("AI" in item["display_name"] for item in result["items"])


def test_filtered_catalog_stage(db):
    """Stage filter includes dev items when requested."""
    _seed_items(db)
    result = db.list_catalog_items_filtered(stages=["prod", "dev"])
    ci_names = [item["ci_name"] for item in result["items"]]
    assert "ns.ai-dev.dev" in ci_names


def test_filtered_catalog_cloud_provider(db):
    """Cloud provider filter narrows results."""
    _seed_items(db)
    result = db.list_catalog_items_filtered(cloud_provider="ec2")
    assert result["total"] >= 1
    assert all(item.get("cloud_provider") == "ec2" for item in result["items"])


def test_filtered_catalog_agd_config(db):
    """AgnosticD config filter narrows results."""
    _seed_items(db)
    result = db.list_catalog_items_filtered(agd_config="ocp-cnv")
    assert result["total"] >= 1
    assert all(item.get("agd_config") == "ocp-cnv" for item in result["items"])


def test_filtered_catalog_workloads(db):
    """Workload filter with alias resolution."""
    _seed_items(db)
    result = db.list_catalog_items_filtered(workloads=["OpenShift AI"])
    assert result["total"] >= 1
    assert any("ai-workshop" in item["ci_name"] for item in result["items"])
    result2 = db.list_catalog_items_filtered(workloads=["RHOAI"])
    assert result2["total"] == result["total"]


def test_filtered_catalog_content_filter_failures(db):
    """Content filter for scan failures."""
    _seed_items(db)
    result = db.list_catalog_items_filtered(content_filter="scan_failures")
    assert result["total"] >= 1
    assert all(item["scan_status"] == "failed" for item in result["items"])


def test_filtered_catalog_content_filter_stale(db):
    """Content filter for stale items."""
    _seed_items(db)
    result = db.list_catalog_items_filtered(content_filter="stale")
    assert result["total"] >= 1
    assert all(item.get("is_stale") for item in result["items"])


def test_filtered_catalog_pagination(db):
    """Pagination returns correct slice and total."""
    _seed_items(db)
    page1 = db.list_catalog_items_filtered(limit=2, offset=0)
    page2 = db.list_catalog_items_filtered(limit=2, offset=2)
    assert len(page1["items"]) == 2
    assert len(page2["items"]) >= 1
    assert page1["total"] == page2["total"]
    assert page1["items"][0]["ci_name"] != page2["items"][0]["ci_name"]
