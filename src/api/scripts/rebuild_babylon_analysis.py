"""Dry-run-first reset of selected Babylon-derived scan artifacts, never history.

Run from src/api after the explicit maintenance-window procedure in
docs/operations/showroom-analysis-rebuild.md. This tool does not scan or deploy.
"""
import argparse
import json
import sys

from rcars.config import Settings
from rcars.db.database import Database


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    targets = parser.add_mutually_exclusive_group(required=True)
    targets.add_argument("--content-id", action="append", dest="content_ids", help="Explicit Babylon content ID; repeatable")
    targets.add_argument("--all-babylon", action="store_true", help="Include all Babylon items, including retired ones")
    parser.add_argument("--execute", action="store_true", help="Reset the dry-run-reviewed generated artifacts")
    parser.add_argument("--confirm-scans-paused", action="store_true", help="Attest all scan producers/processes are stopped and old work drained")
    args = parser.parse_args(argv)
    if args.execute and not args.confirm_scans_paused:
        parser.error("--execute requires --confirm-scans-paused after stopping/draining all scan work")
    db = Database(Settings().database_url)
    try:
        ids = args.content_ids
        if args.all_babylon:
            with db.pool.connection() as conn:
                ids = [row["content_id"] for row in conn.execute(
                    "SELECT ce.content_id FROM content_entities ce JOIN babylon_items bi USING (content_id) "
                    "WHERE ce.source = 'babylon' ORDER BY ce.content_id").fetchall()]
        counts = (db.reset_babylon_scan_artifacts(ids) if args.execute else db.preview_babylon_scan_artifacts(ids))
        print(json.dumps({"mode": "executed" if args.execute else "dry_run", "content_ids": sorted(set(ids)), "counts": counts}, indent=2))
        return 0
    except (ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
