"""Safe, module-local test fixtures for the Showroom isolation suites."""
import os
from urllib.parse import urlsplit

import psycopg
import pytest

from rcars.db.database import Database


@pytest.fixture
def db():
    url = os.environ.get("RCARS_TEST_DATABASE_URL", "postgresql://rcars:dev@localhost:5432/rcars_test")
    if "test" not in urlsplit(url).path:
        raise RuntimeError("Refusing a configured database without 'test' in its name")
    with psycopg.connect(url) as conn:
        if "test" not in conn.execute("SELECT current_database()").fetchone()[0]:
            raise RuntimeError("Refusing an effective database without 'test' in its name")
    database = Database(url)
    database.create_schema()
    with database.pool.connection() as conn:
        initial_jobs = [row["id"] for row in conn.execute("SELECT id FROM jobs").fetchall()]
    # Only these fixtures' own namespace is cleaned; never drop/truncate tables.
    with database.pool.connection() as conn:
        conn.execute("DELETE FROM embeddings WHERE content_id LIKE 'babylon:isolation-test.%'")
        conn.execute("DELETE FROM content_entities WHERE content_id LIKE 'babylon:isolation-test.%'")
        conn.execute("DELETE FROM advisor_sessions WHERE session_id = 'isolation-test-session'")
        conn.execute("DELETE FROM field_source_provisions WHERE provision_uuid = 'isolation-test-provision'")
    yield database
    with database.pool.connection() as conn:
        conn.execute("DELETE FROM jobs WHERE NOT (id = ANY(%s))", (initial_jobs,))
        conn.execute("DELETE FROM embeddings WHERE content_id LIKE 'babylon:isolation-test.%'")
        conn.execute("DELETE FROM content_entities WHERE content_id LIKE 'babylon:isolation-test.%'")
    database.close()
