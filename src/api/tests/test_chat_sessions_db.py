import os
import pytest
from rcars.db.database import Database
from rcars.db import chat_sessions

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
        cur = conn.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        for row in cur.fetchall():
            conn.execute(f"DROP TABLE IF EXISTS {row[0]} CASCADE")
    database = Database(TEST_DB_URL)
    database.create_schema()
    yield database
    database.close()


def _log(db, session_id, turn, intent="recommend", results=None, user="u@x.com"):
    return chat_sessions.log_chat_turn(
        db.pool, session_id=session_id, turn_index=turn, user_email=user,
        query_text=f"q{turn}", results=results, overall_assessment=None,
        intent=intent, envelope={"intent": intent, "answer": "a", "blocks": []},
        scope=None)


def test_chat_columns_exist(db):
    with db.pool.connection() as conn:
        cols = {r["column_name"] for r in conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'advisor_sessions'").fetchall()}
    assert {"intent", "envelope_json", "scope_json"} <= cols


def test_turn_index_increments(db):
    assert chat_sessions.next_turn_index(db.pool, "s1") == 0
    _log(db, "s1", 0)
    assert chat_sessions.next_turn_index(db.pool, "s1") == 1


def test_ownership(db):
    _log(db, "s1", 0, user="owner@x.com")
    assert chat_sessions.session_owner_ok(db.pool, "s1", "owner@x.com")
    assert not chat_sessions.session_owner_ok(db.pool, "s1", "other@x.com")
    assert chat_sessions.session_owner_ok(db.pool, "s1", "other@x.com", is_admin=True)
    assert not chat_sessions.session_owner_ok(db.pool, "missing", "owner@x.com")


def test_context_builder_shape_and_window(db):
    for i in range(7):
        _log(db, "s1", i, results=[{"content_id": f"babylon:c{i}", "display_name": f"C{i}"}])
    ctx = chat_sessions.get_session_context(db.pool, "s1", max_turns=5)
    assert [t["n"] for t in ctx] == [2, 3, 4, 5, 6]          # window, oldest→newest
    assert ctx[-1]["results"] == [{"id": "babylon:c6", "name": "C6"}]
    assert ctx[-1]["query"] == "q6"


def test_opted_out_scrubs_envelope(db):
    chat_sessions.log_chat_turn(
        db.pool, session_id="s2", turn_index=0, user_email="u@x.com",
        query_text="secret", results=[{"content_id": "x"}], overall_assessment="a",
        intent="recommend", envelope={"answer": "secret"}, scope={"type": "prior_results"},
        opted_out=True)
    with db.pool.connection() as conn:
        row = conn.execute("SELECT * FROM advisor_sessions WHERE session_id = 's2'").fetchone()
    assert row["query_text"] is None and row["envelope_json"] is None and row["scope_json"] is None
    assert row["user_email"] != "u@x.com"
