"""Migration script for the generalized content model (RHDPCD-359).

Exports data from the old schema (catalog_items-based) and imports into
the new schema (content_entities-based).  Designed to run in two phases:

  1. Export — runs against the OLD schema before any table drops.
  2. Import — runs against the NEW schema after create_schema().

The export writes a single JSON file that the import subcommands consume.
Each import subcommand is idempotent and can be re-run safely.

Usage:
    # Phase 1 — run BEFORE dropping old tables
    python scripts/migrate_to_content_model.py export --db-url "$DATABASE_URL"

    # Phase 2 — run AFTER new schema is created and pipelines have populated it
    python scripts/migrate_to_content_model.py import-sessions  --db-url "$DATABASE_URL"
    python scripts/migrate_to_content_model.py import-workflows --db-url "$DATABASE_URL"
    python scripts/migrate_to_content_model.py import-notes     --db-url "$DATABASE_URL"

    # All-in-one interactive mode
    python scripts/migrate_to_content_model.py migrate --db-url "$DATABASE_URL"
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, date
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

EXPORT_PATH = Path("/tmp/rcars-migration-export.json")

# Stage suffixes to try when resolving a catalog_base_name to a content_id
STAGE_SUFFIXES = [".prod", ".event", ".dev", ".test"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _connect(db_url: str) -> psycopg.Connection:
    """Open a connection with dict_row factory."""
    return psycopg.connect(db_url, row_factory=dict_row)


def _json_serializer(obj):
    """Serialize datetime/date objects for JSON export."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    return str(obj)


def _table_exists(conn: psycopg.Connection, table_name: str) -> bool:
    """Check whether a table exists in the current database."""
    cur = conn.execute(
        "SELECT EXISTS ("
        "  SELECT FROM information_schema.tables "
        "  WHERE table_name = %s"
        ") AS exists",
        (table_name,),
    )
    return cur.fetchone()["exists"]


def _column_exists(conn: psycopg.Connection, table_name: str, column_name: str) -> bool:
    """Check whether a column exists on a table."""
    cur = conn.execute(
        "SELECT EXISTS ("
        "  SELECT FROM information_schema.columns "
        "  WHERE table_name = %s AND column_name = %s"
        ") AS exists",
        (table_name, column_name),
    )
    return cur.fetchone()["exists"]


def _row_count(conn: psycopg.Connection, table_name: str) -> int:
    """Return the row count for a table."""
    cur = conn.execute(f"SELECT COUNT(*) AS cnt FROM {table_name}")  # noqa: S608
    return cur.fetchone()["cnt"]


def _load_export() -> dict:
    """Load the export JSON file."""
    if not EXPORT_PATH.exists():
        print(f"ERROR: Export file not found at {EXPORT_PATH}")
        print("Run the 'export' subcommand first.")
        sys.exit(1)
    with open(EXPORT_PATH) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Export phase — runs against the OLD schema
# ---------------------------------------------------------------------------

def cmd_export(args):
    """Export preservable data from the old schema."""
    print(f"Connecting to database...")
    with _connect(args.db_url) as conn:
        # Validate old schema tables exist
        for table in ("advisor_sessions", "retirement_workflow", "showroom_analysis"):
            if not _table_exists(conn, table):
                print(f"ERROR: Table '{table}' not found. Is this the old schema?")
                sys.exit(1)

        # 1. Export ALL advisor_sessions rows
        print("Exporting advisor_sessions...")
        cur = conn.execute("SELECT * FROM advisor_sessions ORDER BY id")
        sessions = [dict(row) for row in cur.fetchall()]
        print(f"  {len(sessions)} rows exported")

        # 2. Export ALL retirement_workflow rows (small table, keep for audit trail)
        print("Exporting retirement_workflow (all rows)...")
        cur = conn.execute(
            "SELECT * FROM retirement_workflow "
            "ORDER BY catalog_base_name"
        )
        workflows = [dict(row) for row in cur.fetchall()]
        print(f"  {len(workflows)} rows exported")

        # 3. Export curator notes from showroom_analysis
        print("Exporting curator notes from showroom_analysis...")
        cur = conn.execute(
            "SELECT ci_name, notes FROM showroom_analysis "
            "WHERE notes IS NOT NULL AND notes != '' "
            "ORDER BY ci_name"
        )
        notes = [dict(row) for row in cur.fetchall()]
        print(f"  {len(notes)} rows exported")

    # Write the export file
    export_data = {
        "exported_at": datetime.utcnow().isoformat(),
        "advisor_sessions": sessions,
        "retirement_workflows": workflows,
        "curator_notes": notes,
    }

    with open(EXPORT_PATH, "w") as f:
        json.dump(export_data, f, default=_json_serializer, indent=2)

    print(f"\nExport written to {EXPORT_PATH}")
    print(f"  advisor_sessions:    {len(sessions)} rows")
    print(f"  retirement_workflows: {len(workflows)} rows")
    print(f"  curator_notes:        {len(notes)} rows")


# ---------------------------------------------------------------------------
# Import: advisor_sessions
# ---------------------------------------------------------------------------

def cmd_import_sessions(args):
    """Re-insert advisor_sessions and compute chosen_content_id."""
    data = _load_export()
    sessions = data.get("advisor_sessions", [])
    if not sessions:
        print("No advisor_sessions in export file. Nothing to import.")
        return

    print(f"Importing {len(sessions)} advisor_sessions rows...")

    with _connect(args.db_url) as conn:
        if not _table_exists(conn, "advisor_sessions"):
            print("ERROR: advisor_sessions table not found in new schema.")
            sys.exit(1)

        # Check if the table already has data
        existing_count = _row_count(conn, "advisor_sessions")

        # Check if chosen_content_id column exists (new schema addition)
        has_content_id_col = _column_exists(conn, "advisor_sessions", "chosen_content_id")

        if existing_count == 0:
            # Table is empty — bulk insert all rows
            print(f"  Table is empty, inserting {len(sessions)} rows...")
            inserted = 0
            for row in sessions:
                # Compute chosen_content_id from chosen_ci_name
                chosen_content_id = None
                if row.get("chosen_ci_name"):
                    chosen_content_id = f"babylon:{row['chosen_ci_name']}"

                # Build column list dynamically based on what exists
                columns = [
                    "session_id", "turn_index", "user_email", "query_text",
                    "event_url", "results_json", "overall_assessment",
                    "chosen_ci_name", "chosen_at", "opted_out", "created_at",
                ]
                values_map = {
                    "session_id": row.get("session_id"),
                    "turn_index": row.get("turn_index"),
                    "user_email": row.get("user_email"),
                    "query_text": row.get("query_text"),
                    "event_url": row.get("event_url"),
                    "results_json": json.dumps(row["results_json"]) if row.get("results_json") is not None else None,
                    "overall_assessment": row.get("overall_assessment"),
                    "chosen_ci_name": row.get("chosen_ci_name"),
                    "chosen_at": row.get("chosen_at"),
                    "opted_out": row.get("opted_out", False),
                    "created_at": row.get("created_at"),
                }

                if has_content_id_col:
                    columns.append("chosen_content_id")
                    values_map["chosen_content_id"] = chosen_content_id

                placeholders = ", ".join(f"%({c})s" for c in columns)
                col_list = ", ".join(columns)

                # Cast results_json to JSONB
                placeholders = placeholders.replace(
                    "%(results_json)s", "%(results_json)s::jsonb"
                )

                conn.execute(
                    f"INSERT INTO advisor_sessions ({col_list}) "
                    f"VALUES ({placeholders}) "
                    f"ON CONFLICT DO NOTHING",
                    values_map,
                )
                inserted += 1

            conn.commit()
            final_count = _row_count(conn, "advisor_sessions")
            print(f"  Inserted rows. Table now has {final_count} rows.")

        else:
            # Table has data — update rows missing chosen_content_id
            if not has_content_id_col:
                print(f"  Table has {existing_count} rows but no chosen_content_id column.")
                print("  Skipping — column not present. Run rcars init-db --drop to recreate schema.")
                return

            print(f"  Table has {existing_count} rows. Updating missing chosen_content_id values...")
            cur = conn.execute(
                "UPDATE advisor_sessions "
                "SET chosen_content_id = 'babylon:' || chosen_ci_name "
                "WHERE chosen_ci_name IS NOT NULL "
                "  AND (chosen_content_id IS NULL OR chosen_content_id = '') "
                "RETURNING id"
            )
            updated = len(cur.fetchall())
            conn.commit()
            print(f"  Updated {updated} rows with chosen_content_id.")


# ---------------------------------------------------------------------------
# Import: retirement_workflow
# ---------------------------------------------------------------------------

def cmd_import_workflows(args):
    """Import retirement_workflow rows, mapping catalog_base_name to content_id."""
    data = _load_export()
    workflows = data.get("retirement_workflows", [])
    if not workflows:
        print("No retirement_workflows in export file. Nothing to import.")
        return

    print(f"Importing {len(workflows)} retirement_workflow rows...")

    with _connect(args.db_url) as conn:
        if not _table_exists(conn, "retirement_workflow"):
            print("ERROR: retirement_workflow table not found in new schema.")
            sys.exit(1)
        if not _table_exists(conn, "content_entities"):
            print("ERROR: content_entities table not found. Run catalog refresh first.")
            sys.exit(1)

        # Warn if content_entities is empty — all workflows will fail to resolve
        ce_count = _row_count(conn, "content_entities")
        if ce_count == 0:
            print("WARNING: content_entities is empty — catalog refresh may not have run yet.")
            print("All workflows will be skipped because base names cannot resolve to content_ids.")
            print("Run catalog refresh first, then re-run this command.")
            return

        # Check if new schema uses content_id PK or catalog_base_name PK
        has_content_id_pk = _column_exists(conn, "retirement_workflow", "content_id")

        imported = 0
        skipped_no_match = 0
        skipped_exists = 0

        for row in workflows:
            base_name = row.get("catalog_base_name")
            if not base_name:
                skipped_no_match += 1
                continue

            if has_content_id_pk:
                # New schema — PK is content_id, need to resolve
                content_id = _resolve_base_name_to_content_id(conn, base_name)
                if not content_id:
                    print(f"  SKIP: No content_entity found for base_name '{base_name}'")
                    skipped_no_match += 1
                    continue

                # Check if already imported
                cur = conn.execute(
                    "SELECT 1 FROM retirement_workflow WHERE content_id = %s",
                    (content_id,),
                )
                if cur.fetchone():
                    skipped_exists += 1
                    continue

                conn.execute(
                    "INSERT INTO retirement_workflow ("
                    "  content_id, status, "
                    "  step_reviewed_at, step_reviewed_by, "
                    "  step_approved_at, step_approved_by, "
                    "  approval_reason, approval_snapshot, "
                    "  step_notified_at, step_notified_by, "
                    "  step_started_at, step_started_by, "
                    "  retirement_target_date, step_retired_at, "
                    "  replacement_ci, replacement_name, "
                    "  curator_notes, jira_key, jira_project, "
                    "  created_at, updated_at"
                    ") VALUES ("
                    "  %s, %s, %s, %s, %s, %s, %s, %s::jsonb, "
                    "  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s"
                    ") ON CONFLICT (content_id) DO NOTHING",
                    (
                        content_id,
                        row.get("status", "reviewed"),
                        row.get("step_reviewed_at"),
                        row.get("step_reviewed_by"),
                        row.get("step_approved_at"),
                        row.get("step_approved_by"),
                        row.get("approval_reason"),
                        json.dumps(row["approval_snapshot"]) if row.get("approval_snapshot") else None,
                        row.get("step_notified_at"),
                        row.get("step_notified_by"),
                        row.get("step_started_at"),
                        row.get("step_started_by"),
                        row.get("retirement_target_date"),
                        row.get("step_retired_at"),
                        row.get("replacement_ci"),
                        row.get("replacement_name"),
                        row.get("curator_notes"),
                        row.get("jira_key"),
                        row.get("jira_project", "RHDPCD"),
                        row.get("created_at"),
                        row.get("updated_at"),
                    ),
                )
                imported += 1
            else:
                # Old-style schema still using catalog_base_name PK
                # (shouldn't happen if migration ran, but handle gracefully)
                cur = conn.execute(
                    "SELECT 1 FROM retirement_workflow WHERE catalog_base_name = %s",
                    (base_name,),
                )
                if cur.fetchone():
                    skipped_exists += 1
                    continue

                # Re-insert as-is
                conn.execute(
                    "INSERT INTO retirement_workflow ("
                    "  catalog_base_name, status, "
                    "  step_reviewed_at, step_reviewed_by, "
                    "  step_approved_at, step_approved_by, "
                    "  approval_reason, approval_snapshot, "
                    "  step_notified_at, step_notified_by, "
                    "  step_started_at, step_started_by, "
                    "  retirement_target_date, step_retired_at, "
                    "  replacement_ci, replacement_name, "
                    "  curator_notes, jira_key, jira_project, "
                    "  created_at, updated_at"
                    ") VALUES ("
                    "  %s, %s, %s, %s, %s, %s, %s, %s::jsonb, "
                    "  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s"
                    ") ON CONFLICT DO NOTHING",
                    (
                        base_name,
                        row.get("status", "reviewed"),
                        row.get("step_reviewed_at"),
                        row.get("step_reviewed_by"),
                        row.get("step_approved_at"),
                        row.get("step_approved_by"),
                        row.get("approval_reason"),
                        json.dumps(row["approval_snapshot"]) if row.get("approval_snapshot") else None,
                        row.get("step_notified_at"),
                        row.get("step_notified_by"),
                        row.get("step_started_at"),
                        row.get("step_started_by"),
                        row.get("retirement_target_date"),
                        row.get("step_retired_at"),
                        row.get("replacement_ci"),
                        row.get("replacement_name"),
                        row.get("curator_notes"),
                        row.get("jira_key"),
                        row.get("jira_project", "RHDPCD"),
                        row.get("created_at"),
                        row.get("updated_at"),
                    ),
                )
                imported += 1

        conn.commit()

    print(f"  Imported: {imported}")
    print(f"  Skipped (already exists): {skipped_exists}")
    print(f"  Skipped (no content_entity match): {skipped_no_match}")


def _resolve_base_name_to_content_id(
    conn: psycopg.Connection, base_name: str, verbose: bool = True
) -> str | None:
    """Resolve a catalog_base_name to a content_id in content_entities.

    Tries babylon:{base_name}.prod first, then .event, .dev, .test.
    Returns the first content_id that exists in content_entities, or None.
    """
    tried = []
    for suffix in STAGE_SUFFIXES:
        candidate = f"babylon:{base_name}{suffix}"
        tried.append(candidate)
        cur = conn.execute(
            "SELECT content_id FROM content_entities WHERE content_id = %s",
            (candidate,),
        )
        if cur.fetchone():
            return candidate
    if verbose:
        print(f"    Tried: {', '.join(tried)} — none found")
    return None


# ---------------------------------------------------------------------------
# Import: curator notes
# ---------------------------------------------------------------------------

def cmd_import_notes(args):
    """Restore curator notes to showroom_analysis rows."""
    data = _load_export()
    notes = data.get("curator_notes", [])
    if not notes:
        print("No curator_notes in export file. Nothing to import.")
        return

    print(f"Importing {len(notes)} curator notes...")

    with _connect(args.db_url) as conn:
        if not _table_exists(conn, "showroom_analysis"):
            print("ERROR: showroom_analysis table not found in new schema.")
            sys.exit(1)

        # Determine key column — new schema uses content_id, old uses ci_name
        uses_content_id = _column_exists(conn, "showroom_analysis", "content_id")

        restored = 0
        skipped = 0

        for row in notes:
            ci_name = row.get("ci_name")
            note_text = row.get("notes")
            if not ci_name or not note_text:
                skipped += 1
                continue

            if uses_content_id:
                content_id = f"babylon:{ci_name}"
                cur = conn.execute(
                    "UPDATE showroom_analysis SET notes = %s "
                    "WHERE content_id = %s AND (notes IS NULL OR notes = '')",
                    (note_text, content_id),
                )
            else:
                cur = conn.execute(
                    "UPDATE showroom_analysis SET notes = %s "
                    "WHERE ci_name = %s AND (notes IS NULL OR notes = '')",
                    (note_text, ci_name),
                )

            if cur.rowcount > 0:
                restored += 1
            else:
                skipped += 1

        conn.commit()

    print(f"  Restored: {restored}")
    print(f"  Skipped (no matching row or notes already set): {skipped}")


# ---------------------------------------------------------------------------
# Interactive all-in-one migration
# ---------------------------------------------------------------------------

def cmd_migrate(args):
    """Interactive all-in-one migration with prompts between phases."""
    print("=" * 60)
    print("RCARS Content Model Migration (RHDPCD-359)")
    print("=" * 60)
    print()
    print("This will run the full migration sequence interactively.")
    print("You will be prompted before each phase.")
    print()

    # Phase 1: Export
    print("-" * 40)
    print("PHASE 1: Export from old schema")
    print("-" * 40)
    if EXPORT_PATH.exists():
        print(f"  Export file already exists at {EXPORT_PATH}")
        resp = input("  Re-export? (y/N): ").strip().lower()
        if resp == "y":
            cmd_export(args)
        else:
            print("  Using existing export file.")
            data = _load_export()
            print(f"  advisor_sessions:    {len(data.get('advisor_sessions', []))} rows")
            print(f"  retirement_workflows: {len(data.get('retirement_workflows', []))} rows")
            print(f"  curator_notes:        {len(data.get('curator_notes', []))} rows")
    else:
        cmd_export(args)

    print()

    # Phase 2: Wait for schema swap
    print("-" * 40)
    print("PHASE 2: Schema swap")
    print("-" * 40)
    print("  Before continuing, ensure that:")
    print("  1. Old tables have been dropped")
    print("  2. New schema has been created (create_schema())")
    print("  3. Catalog refresh has been run (content_entities populated)")
    print()
    resp = input("  Ready to proceed with import? (y/N): ").strip().lower()
    if resp != "y":
        print("  Aborting. Run individual import subcommands when ready.")
        return

    # Phase 3: Import sessions
    print()
    print("-" * 40)
    print("PHASE 3: Import advisor_sessions")
    print("-" * 40)
    resp = input("  Import sessions? (Y/n): ").strip().lower()
    if resp != "n":
        cmd_import_sessions(args)
    else:
        print("  Skipped.")

    # Phase 4: Import workflows
    print()
    print("-" * 40)
    print("PHASE 4: Import retirement_workflow")
    print("-" * 40)
    resp = input("  Import workflows? (Y/n): ").strip().lower()
    if resp != "n":
        cmd_import_workflows(args)
    else:
        print("  Skipped.")

    # Phase 5: Import notes
    print()
    print("-" * 40)
    print("PHASE 5: Import curator notes")
    print("-" * 40)
    print("  NOTE: Run this AFTER the scan pipeline has populated showroom_analysis.")
    resp = input("  Import notes now? (Y/n): ").strip().lower()
    if resp != "n":
        cmd_import_notes(args)
    else:
        print("  Skipped. Run 'import-notes' after scan pipeline completes.")

    print()
    print("=" * 60)
    print("Migration complete.")
    print("=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="RCARS content model migration (RHDPCD-359)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Export from old schema\n"
            "  python scripts/migrate_to_content_model.py export --db-url postgresql://rcars:dev@localhost:5432/rcars\n"
            "\n"
            "  # Import into new schema (run each after appropriate pipeline step)\n"
            "  python scripts/migrate_to_content_model.py import-sessions  --db-url $DATABASE_URL\n"
            "  python scripts/migrate_to_content_model.py import-workflows --db-url $DATABASE_URL\n"
            "  python scripts/migrate_to_content_model.py import-notes     --db-url $DATABASE_URL\n"
            "\n"
            "  # Interactive all-in-one\n"
            "  python scripts/migrate_to_content_model.py migrate --db-url $DATABASE_URL\n"
        ),
    )

    subparsers = parser.add_subparsers(dest="command", help="Migration phase to run")
    subparsers.required = True

    # export
    p_export = subparsers.add_parser("export", help="Export data from old schema")
    p_export.add_argument("--db-url", required=True, help="PostgreSQL connection URL")
    p_export.set_defaults(func=cmd_export)

    # import-sessions
    p_sessions = subparsers.add_parser("import-sessions", help="Import advisor_sessions")
    p_sessions.add_argument("--db-url", required=True, help="PostgreSQL connection URL")
    p_sessions.set_defaults(func=cmd_import_sessions)

    # import-workflows
    p_workflows = subparsers.add_parser("import-workflows", help="Import retirement_workflow")
    p_workflows.add_argument("--db-url", required=True, help="PostgreSQL connection URL")
    p_workflows.set_defaults(func=cmd_import_workflows)

    # import-notes
    p_notes = subparsers.add_parser("import-notes", help="Import curator notes")
    p_notes.add_argument("--db-url", required=True, help="PostgreSQL connection URL")
    p_notes.set_defaults(func=cmd_import_notes)

    # migrate (interactive all-in-one)
    p_migrate = subparsers.add_parser("migrate", help="Interactive all-in-one migration")
    p_migrate.add_argument("--db-url", required=True, help="PostgreSQL connection URL")
    p_migrate.set_defaults(func=cmd_migrate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
