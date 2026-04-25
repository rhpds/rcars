"""One-time migration: export token_usage from old schema, create new schema, reimport.

Usage:
    cd src/api
    RCARS_DATABASE_URL=postgresql://rcars:dev@localhost:5432/rcars python scripts/migrate_token_usage.py

This script:
1. Exports all token_usage rows to a JSON backup
2. Drops all existing tables (clean slate)
3. Creates the new v2 schema
4. Imports token_usage rows into the new table
5. Verifies row counts match

The backup file is saved to /tmp/rcars_token_usage_backup.json as a safety net.
"""

import json
import sys
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, ".")

from rcars.db import Database
from rcars.config import Settings


def migrate():
    settings = Settings()
    db = Database(settings.database_url)

    # Check if old schema exists
    print("Checking existing schema...")
    with db.pool.connection() as conn:
        cur = conn.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'token_usage') as exists"
        )
        has_token_usage = cur.fetchone()["exists"]

    if not has_token_usage:
        print("No token_usage table found. Creating fresh schema...")
        db.create_schema()
        print("Schema created. No migration needed.")
        db.close()
        return

    # Export
    print("Exporting token_usage...")
    with db.pool.connection() as conn:
        cur = conn.execute("SELECT * FROM token_usage ORDER BY created_at")
        rows = cur.fetchall()
    print(f"  Exported {len(rows)} rows")

    dump_path = "/tmp/rcars_token_usage_backup.json"

    def serialize(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return str(obj)

    with open(dump_path, "w") as f:
        json.dump([dict(r) for r in rows], f, default=serialize, indent=2)
    print(f"  Saved to {dump_path}")

    # Drop and recreate
    print("Dropping old schema...")
    db.close()

    import psycopg
    with psycopg.connect(settings.database_url) as conn:
        conn.autocommit = True
        tables = [
            "embeddings", "enrichment_tags", "showroom_analysis",
            "analysis_log", "jobs", "token_usage", "advisor_sessions",
            "api_keys", "catalog_items", "alembic_version",
        ]
        for table in tables:
            conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")

    print("Creating new v2 schema...")
    db = Database(settings.database_url)
    db.create_schema()

    # Import
    print("Importing token_usage...")
    with open(dump_path) as f:
        saved_rows = json.load(f)

    with db.pool.connection() as conn:
        for row in saved_rows:
            conn.execute(
                """INSERT INTO token_usage (operation, model, input_tokens, output_tokens,
                   ci_name, query_text, created_at)
                   VALUES (%(operation)s, %(model)s, %(input_tokens)s, %(output_tokens)s,
                   %(ci_name)s, %(query_text)s, %(created_at)s)""",
                row,
            )
        conn.commit()

    # Verify
    with db.pool.connection() as conn:
        cur = conn.execute("SELECT COUNT(*) AS cnt FROM token_usage")
        count = cur.fetchone()["cnt"]
    print(f"  Imported {count} rows (expected {len(saved_rows)})")

    if count != len(saved_rows):
        print(f"  WARNING: Row count mismatch! Expected {len(saved_rows)}, got {count}")
        print(f"  Backup preserved at {dump_path}")
        db.close()
        sys.exit(1)

    print(f"  Row counts match. Backup at {dump_path} (safe to delete after verification).")
    print("\nMigration complete. Run 'rcars refresh' then 'rcars scan' to repopulate catalog.")
    db.close()


if __name__ == "__main__":
    migrate()
