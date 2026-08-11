import os
import pytest
from rcars.db.database import Database
from rcars.services.chat.evidence import build_evidence_pack, MAX_NEIGHBORS
from tests.chat_fixtures import seed_chat_fixtures

TEST_DB_URL = os.environ.get(
    "RCARS_TEST_DATABASE_URL",
    "postgresql://rcars:dev@localhost:5432/rcars_test",
)


@pytest.fixture
def db():
    import psycopg
    with psycopg.connect(TEST_DB_URL) as conn:
        conn.autocommit = True
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cur = conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        )
        for row in cur.fetchall():
            conn.execute(f"DROP TABLE IF EXISTS {row[0]} CASCADE")

    database = Database(TEST_DB_URL)
    database.create_schema()
    yield database
    database.close()


def test_pack_bounded_and_sorted(db):
    ids = seed_chat_fixtures(db)
    pack = build_evidence_pack(db, [ids["lb2144-ansible-eda"]])
    assert 1 <= len(pack) <= MAX_NEIGHBORS
    assert pack[0]["name"] == "LB2145 Ansible Automation Basics"
    assert pack[0]["shared_products"] == 91
    assert set(pack[0]) <= {"anchor", "name", "stage", "shared_products", "shared_topics",
                            "verdict", "relationship", "products", "provisions"}


def test_pack_includes_shared_workload_note(db):
    ids = seed_chat_fixtures(db)
    # ocpvirt-migration has workload rhpds.ocpvirt.setup; add it to lb2145 (not connected by similarity)
    # so the pack for ocpvirt-migration includes lb2145 via shared_workload relationship
    with db.pool.connection() as conn:
        conn.execute(
            """INSERT INTO babylon_item_workloads (content_id, workload_fqcn, workload_role, workload_collection)
               VALUES (%s, 'rhpds.ocpvirt.setup', 'setup_virt', 'rhpds.ocpvirt')
               ON CONFLICT (content_id, workload_fqcn) DO NOTHING""",
            (ids["lb2145-ansible-basics"],))
        conn.commit()
    pack = build_evidence_pack(db, [ids["ocpvirt-migration"]])
    shared = [p for p in pack if p.get("relationship") == "shared_workload"]
    assert shared and shared[0]["name"] == "LB2145 Ansible Automation Basics"


def test_empty_anchor_empty_pack(db):
    seed_chat_fixtures(db)
    assert build_evidence_pack(db, []) == []
    assert build_evidence_pack(db, ["babylon:nonexistent"]) == []
