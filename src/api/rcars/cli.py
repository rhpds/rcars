"""RCARS CLI — RHDP Content Advisory & Recommendation System."""

from __future__ import annotations

import sys

import click
import structlog
from rich.console import Console
from rich.table import Table

from rcars.config import Settings
from rcars.db import Database
from rcars.db.overlap import generate_overlap_candidates, get_overlap_stats
from rcars.logging import setup_logging
from rcars.services.showroom_scan import scan_babylon_item

console = Console()
log = structlog.get_logger()


def _print(msg: str):
    from datetime import datetime
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{ts} {msg}", flush=True)


def get_db() -> Database:
    settings = Settings()
    if not settings.database_url:
        console.print("[red]Error:[/red] RCARS_DATABASE_URL not set")
        sys.exit(1)
    db = Database(settings.database_url)
    db.create_schema()
    return db


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
def cli(verbose: bool):
    """RCARS — RHDP Content Advisory & Recommendation System."""
    setup_logging(level="DEBUG" if verbose else "INFO", component="cli")


@cli.command("init-db")
@click.option("--drop", is_flag=True, default=False, help="Drop all tables before creating schema")
def init_db(drop: bool):
    """Initialize or reset the database schema."""
    if drop:
        settings = Settings()
        if not settings.database_url:
            console.print("[red]Error:[/red] RCARS_DATABASE_URL not set")
            sys.exit(1)
        db = Database(settings.database_url)
        console.print("[yellow]Dropping all tables...[/yellow]")
        db.drop_schema()
        db.create_schema()
        console.print("[green]Schema recreated.[/green]")
        db.close()
    else:
        db = get_db()
        console.print("[green]Schema is up to date.[/green]")
        db.close()


@cli.command()
def refresh():
    """Refresh catalog from Babylon CRDs (all namespaces)."""
    import time
    from rcars.services.catalog import CatalogReader

    settings = Settings()
    db = get_db()
    namespaces = settings.catalog_namespaces
    t0 = time.monotonic()

    _print(f"Refreshing catalog from {len(namespaces)} namespace(s): {', '.join(namespaces)}")

    try:
        reader = CatalogReader(settings.kubeconfig_path)
        items = reader.refresh_catalog(
            namespaces=namespaces,
            component_namespace=settings.agnosticv_component_namespace,
        )
    except Exception as e:
        _print(f"ERROR: Failed to connect to cluster: {e}")
        db.close()
        sys.exit(1)

    _print(f"Retrieved {len(items)} catalog items. Upserting to database...")
    current_content_ids: set[str] = set()
    count_with_showroom = 0
    for i, item in enumerate(items, 1):
        workloads = item.pop("_workloads", [])
        acl_groups = item.pop("_acl_groups", [])
        content_id = db.upsert_babylon_catalog_item(item)
        db.log_action(item["ci_name"], "refresh")
        current_content_ids.add(content_id)
        db.sync_workloads(content_id, workloads)
        db.sync_acl_groups(content_id, acl_groups)
        if item.get("showroom_url"):
            count_with_showroom += 1
        if i % 25 == 0 or i == len(items):
            _print(f"  upserted {i}/{len(items)} items...")

    retired = db.retire_missing_babylon(current_content_ids)
    if retired:
        for r in retired:
            _print(f"  retired: {r['content_id']} (stage={r.get('stage', '?')})")

    elapsed = time.monotonic() - t0
    _print(f"Done in {elapsed:.1f}s. {len(items)} items, {count_with_showroom} with Showroom, {len(retired)} retired.")
    db.close()


@cli.command()
@click.option("--max", "max_analyze", type=int, default=None, help="Max items to analyze")
@click.option("--force", is_flag=True, help="Bypass unchanged analysis and embedding reuse")
@click.option("--content-id", "content_ids", multiple=True, help="Restrict scanning to these Babylon content IDs")
def scan(max_analyze: int | None, force: bool, content_ids: tuple[str, ...]):
    """Scan eligible item stages independently, materializing only each target."""
    import time
    from concurrent.futures import ThreadPoolExecutor, as_completed

    settings = Settings()
    db = get_db()
    items = db.get_items_needing_analysis(settings, force=force)
    if content_ids:
        items = [item for item in items if item["content_id"] in content_ids]
    if max_analyze:
        items = items[:max_analyze]
    if not items:
        _print("Nothing to analyze.")
        db.close()
        return
    _print(f"Scanning {len(items)} item stages (max_parallel={settings.max_parallel})...")
    completed = 0
    errors = 0
    total = len(items)
    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=settings.max_parallel) as executor:
        futures = {executor.submit(scan_babylon_item, db, settings, item["content_id"], force=force): item for item in items}
        for future in as_completed(futures):
            item = futures[future]
            try:
                result = future.result()
                if result.get("success"):
                    completed += 1
                    _print(f"  {result['outcome']}: {item['ci_name']}")
                else:
                    errors += 1
                    _print(f"  FAIL: {item['ci_name']} — {result.get('message', result.get('outcome'))}")
            except Exception as e:
                errors += 1
                _print(f"  FAIL: {item['ci_name']} — {e}")
    elapsed = time.monotonic() - t0
    _print(f"Done in {elapsed:.1f}s. {completed}/{total} analyzed, {errors} errors")
    db.close()
    if errors:
        raise click.ClickException(f"{errors} item scans failed")


@cli.command()
@click.option("--failures", is_flag=True, default=False, help="Show detailed scan failures")
def status(failures: bool):
    """Show catalog status summary."""
    db = get_db()
    summary = db.get_status_summary()

    table = Table(title="RCARS Catalog Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right")

    table.add_row("Total catalog items", str(summary["total"]))
    table.add_row("Production items", str(summary["prod"]))
    table.add_row("With Showroom URL", str(summary["with_showroom"]))
    table.add_row("Analyzed", str(summary["analyzed"]))
    table.add_row("Stale", str(summary["stale"]))

    fail_count = summary.get("scan_failures", 0)
    fail_style = "red" if fail_count > 0 else "green"
    table.add_row("Scan failures", f"[{fail_style}]{fail_count}[/{fail_style}]")
    console.print(table)

    if failures:
        fail_list = db.get_scan_failures()
        if fail_list:
            ftable = Table(title="Scan Failures")
            ftable.add_column("CI Name", style="cyan")
            ftable.add_column("Error Class")
            ftable.add_column("Failed At")
            for f in fail_list:
                failed_at = f["scan_failed_at"].strftime("%Y-%m-%d %H:%M") if f.get("scan_failed_at") else ""
                ftable.add_row(f["ci_name"], f.get("scan_error_class", ""), failed_at)
            console.print(ftable)
        else:
            console.print("[green]No scan failures.[/green]")
    db.close()


@cli.command("overlap-candidates")
@click.option("--min-products", "-p", default=1, type=int, help="Minimum shared products")
@click.option("--min-topics", "-t", default=2, type=int, help="Minimum shared topics")
def overlap_candidates_cmd(min_products: int, min_topics: int):
    """Generate overlap candidates via deterministic structural matching."""
    db = get_db()
    result = generate_overlap_candidates(db.pool, min_products=min_products, min_topics=min_topics)

    click.echo(f"\nGenerated overlap candidates (min_products={min_products}, min_topics={min_topics}):")
    click.echo(f"  Pairs inserted:  {result['pairs_inserted']}")
    click.echo(f"  Pairs updated:   {result['pairs_updated']}")
    click.echo(f"  Pairs pruned:    {result['pairs_pruned_threshold']}")
    click.echo(f"  Total candidates: {result['total_candidates']}")

    stats = get_overlap_stats(db.pool)
    click.echo("\nOverlap verdict breakdown:")
    click.echo(f"  Redundant:       {stats['redundant']}")
    click.echo(f"  Complementary:   {stats['complementary']}")
    click.echo(f"  Differentiated:  {stats['differentiated']}")
    click.echo(f"  Unassessed:      {stats['unassessed']}")
    if stats['last_computed']:
        click.echo(f"  Last computed:   {stats['last_computed']}")

    db.close()


# ── Curation commands ──

@cli.command()
@click.argument("ci_name")
@click.argument("tag_type")
@click.argument("tag_value")
def tag(ci_name: str, tag_type: str, tag_value: str):
    """Add an enrichment tag to a catalog item."""
    db = get_db()
    db.add_enrichment_tag(ci_name, tag_type, tag_value)
    console.print(f"Tagged [cyan]{ci_name}[/cyan]: {tag_type}={tag_value}")
    db.close()


@cli.command()
@click.argument("ci_name")
@click.argument("tag_type")
@click.argument("tag_value")
def untag(ci_name: str, tag_type: str, tag_value: str):
    """Remove an enrichment tag from a catalog item."""
    db = get_db()
    db.remove_enrichment_tag(ci_name, tag_type, tag_value)
    console.print(f"Removed tag {tag_type}={tag_value} from [cyan]{ci_name}[/cyan]")
    db.close()


@cli.command()
@click.argument("ci_name")
@click.argument("text")
def note(ci_name: str, text: str):
    """Set a curator note on a catalog item."""
    db = get_db()
    db.set_enrichment_note(ci_name, text)
    console.print(f"Note set on [cyan]{ci_name}[/cyan]")
    db.close()


@cli.command()
@click.argument("ci_name")
def flag(ci_name: str):
    """Flag a catalog item for enrichment review."""
    db = get_db()
    db.set_enrichment_review_flag(ci_name, True)
    console.print(f"Flagged [cyan]{ci_name}[/cyan] for review")
    db.close()


@cli.command("override-url")
@click.argument("ci_name")
@click.argument("url")
def override_url(ci_name: str, url: str):
    """Override the Showroom URL for a catalog item."""
    db = get_db()
    db.set_showroom_url_override(ci_name, url)
    console.print(f"Showroom URL override set for [cyan]{ci_name}[/cyan]: {url}")
    db.close()


@cli.command("set-content-path")
@click.argument("ci_name")
@click.argument("path")
def set_content_path(ci_name: str, path: str):
    """Set custom content path for non-standard Showroom repos."""
    db = get_db()
    db.set_content_path(ci_name, path)
    console.print(f"Content path set for [cyan]{ci_name}[/cyan]: {path}")
    db.close()


# ── Infrastructure commands ──

@cli.group(name="infra")
def infra_group():
    """Infrastructure metadata commands."""
    pass


@infra_group.command("stats")
def infra_stats():
    """Show infrastructure metadata coverage stats."""
    db = get_db()
    stats = db.get_infra_stats()

    table = Table(title="Infrastructure Metadata Stats")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right")
    table.add_row("AgnosticD v2 items", str(stats["v2_items"]))
    table.add_row("Items with workloads", str(stats["with_workloads"]))
    table.add_row("Infrastructure workloads", str(stats["infrastructure_workloads"]))
    table.add_row("Infrastructure configs", str(stats["infrastructure_configs"]))
    console.print(table)
    db.close()


# ── Workload commands ──

@cli.group(name="workload")
def workload_group():
    """Workload mapping and scanning commands."""
    pass


@workload_group.command("alias")
@click.argument("product")
@click.argument("alias_name")
def workload_alias(product: str, alias_name: str):
    """Add a product name alias."""
    db = get_db()
    db.upsert_workload_alias(product, alias_name)
    console.print(f"Alias [cyan]{alias_name}[/cyan] → {product}")
    db.close()


@workload_group.command("scan")
@click.option("--collection", "-c", default=None, help="Scan only this collection (e.g. agnosticd.core_workloads)")
@click.option("--force", is_flag=True, default=False, help="Skip SHA check, rescan everything")
def workload_scan(collection: str | None, force: bool):
    """Scan agDv2 workload repos and base configs via LLM."""
    from rcars.services.workload_scanner import scan_all_collections, scan_configs

    settings = Settings()
    db = get_db()

    from rcars.config import fetch_litemaas_models
    if settings.use_litemaas:
        fetch_litemaas_models(settings)
    elif not settings.get_anthropic_client():
        console.print("[red]Error:[/red] No LLM provider configured (set RCARS_LITEMAAS_URL or ANTHROPIC_VERTEX_PROJECT_ID)")
        db.close()
        sys.exit(1)

    model = settings.triage_model
    _print(f"Scanning workload repos (model={model}, force={force})")
    if collection:
        _print(f"  filtering to collection: {collection}")

    results = scan_all_collections(
        clone_dir=settings.clone_dir,
        settings=settings,
        model=model,
        db=db,
        force=force,
        collection_filter=collection,
    )

    for r in results:
        status = r.get("status", "?")
        if status == "unchanged":
            _print(f"  {r['collection']}: unchanged (skipped)")
        elif status == "clone_failed":
            _print(f"  {r['collection']}: [red]clone failed[/red]")
        else:
            _print(f"  {r['collection']}: {r.get('roles_scanned', 0)} scanned, "
                   f"{r.get('roles_mapped', 0)} mapped")

    total_scanned = sum(r.get("roles_scanned", 0) for r in results)
    total_mapped = sum(r.get("roles_mapped", 0) for r in results)
    _print(f"Done. {total_scanned} roles scanned, {total_mapped} new/updated mappings.")

    console.print("\n[bold]Scanning base configs...[/bold]")
    config_result = scan_configs(settings.clone_dir, settings, model, db, force=force)
    scanned = config_result.get("configs_scanned", 0)
    status = config_result.get("status", "?")
    _print(f"Configs: {scanned} scanned ({status})")

    db.close()


@workload_group.command("list")
def workload_list():
    """List infrastructure catalog entries."""
    db = get_db()
    rows = db.list_infrastructure()
    table = Table(title=f"Infrastructure Catalog ({len(rows)})")
    table.add_column("Role Name", style="cyan")
    table.add_column("Type")
    table.add_column("Products")
    table.add_column("Category")
    table.add_column("Collection")
    for row in rows:
        products = ", ".join(row.get("products") or [])
        table.add_row(
            row["role_name"], row["type"],
            products[:60], row.get("category") or "—",
            row.get("collection") or "—",
        )
    console.print(table)
    db.close()


# ── Reporting commands ──

@cli.group(name="reporting-db")
def reporting_db_group():
    """Reporting database metrics commands."""
    pass


@reporting_db_group.command("sync")
@click.option("--field-source", is_flag=True, default=False, help="Only sync field source content provisions")
@click.pass_context
def reporting_db_sync(ctx, field_source: bool):
    """Sync reporting metrics from RHDP MCP server."""
    from rcars.services.reporting_sync import run_reporting_sync, run_field_source_sync

    settings = Settings()
    if not settings.reporting_mcp_url or not settings.reporting_mcp_token:
        _print("ERROR: RCARS_REPORTING_MCP_URL and RCARS_REPORTING_MCP_TOKEN must be set.")
        raise SystemExit(1)

    db = Database(settings.database_url)

    if not field_source:
        _print("Syncing reporting metrics from MCP server...")
        try:
            result = run_reporting_sync(db, settings)
            _print(f"  Synced: {result['synced']} metrics")
            _print(f"  Orphans removed: {result['orphans_removed']}")
            _print(f"  Provisions: {result['provisions_rows']}, Touched: {result['touched_rows']}, "
                   f"Closed: {result['closed_rows']}, Cost: {result['cost_rows']}, Dates: {result['date_rows']}")
        except Exception as e:
            _print(f"ERROR: {e}")
            raise SystemExit(1)

    _print("Syncing field source content provisions...")
    try:
        fs_result = run_field_source_sync(db, settings)
        _print(f"  OCP: {fs_result.get('ocp', 0)}, RHEL: {fs_result.get('rhel', 0)}, "
               f"Total: {fs_result.get('total', 0)}")
    except Exception as e:
        _print(f"WARNING: Field source sync failed: {e}")


@reporting_db_group.command("status")
@click.pass_context
def reporting_db_status(ctx):
    """Show reporting sync status and score distribution."""
    settings = Settings()
    db = Database(settings.database_url)
    status = db.get_reporting_sync_status()

    if not status or status["total"] == 0:
        _print("No reporting metrics synced yet.")
        return

    _print(f"  Last synced:    {status['last_synced']}")
    _print(f"  Total items:    {status['total']}")
    _print(f"  Strong (>=55):    {status['strong']}")
    _print(f"  Moderate (35-54): {status['moderate']}")
    _print(f"  Low (<35):        {status['low']}")


@reporting_db_group.command("show")
@click.argument("identifier")
@click.pass_context
def reporting_db_show(ctx, identifier: str):
    """Show performance metrics for a content entity (accepts ci_name, content_id, or base name)."""
    from rcars.services.reporting_sync import extract_base_name

    settings = Settings()
    db = Database(settings.database_url)

    if identifier.startswith("babylon:"):
        content_id = identifier
    else:
        base_name = extract_base_name(identifier)
        resolved = db.resolve_base_names_to_content_ids({base_name})
        content_id = resolved.get(base_name)
        if not content_id:
            _print(f"No content entity found for: {base_name}")
            return

    channels = db.get_performance_channels(content_id)
    score = db.get_performance_score(content_id)
    rhdp = next((ch for ch in channels if ch["channel"] == "rhdp"), None) if channels else None

    if not rhdp and not score:
        _print(f"No performance data found for: {content_id}")
        return

    _print(f"  Content ID:        {content_id}")
    if score:
        _print(f"  Performance score: {score['performance_score']}")
    if rhdp:
        _print(f"  Provisions:        {rhdp.get('provisions', 0)}")
        _print(f"  Experiences:       {rhdp.get('experiences', 0)}")
        _print(f"  Unique users:      {rhdp.get('unique_users', 0)}")
        _print(f"  Pipeline touched:  ${float(rhdp.get('pipeline_touched') or 0):,.0f}")
        _print(f"  Closed amount:     ${float(rhdp.get('closed_amount') or 0):,.0f}")
        _print(f"  Total cost:        ${float(rhdp.get('total_cost') or 0):,.0f}")
        _print(f"  Avg cost/prov:     ${float(rhdp.get('avg_cost_per_provision') or 0):,.2f}")
        _print(f"  First activity:    {rhdp.get('first_activity') or 'N/A'}")
        _print(f"  Last activity:     {rhdp.get('last_activity') or 'N/A'}")
        _print(f"  Synced at:         {rhdp.get('synced_at')}")


# ── Server command ──

@cli.command()
@click.option("--host", default="0.0.0.0", show_default=True, help="Host to bind")
@click.option("--port", default=8080, show_default=True, type=int, help="Port to listen on")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
@click.option("--workers", default=1, show_default=True, type=int, help="Number of workers")
def serve(host: str, port: int, reload: bool, workers: int):
    """Start the RCARS API server."""
    import uvicorn
    uvicorn.run(
        "rcars.api.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
        workers=workers,
    )


@cli.group(name="vocab")
def vocab_group():
    """Controlled vocabulary — review queue and re-scan staging."""


@vocab_group.command("unknowns")
@click.option("--status", default="pending", show_default=True,
              help="Filter by status: pending, aliased, promoted, rejected, or 'all'")
@click.option("--dimension", default=None, help="Filter by dimension")
@click.option("--limit", type=int, default=50, show_default=True, help="Max rows to print")
def vocab_unknowns(status: str, dimension: str | None, limit: int):
    """List terms the normalizer could not match, ranked by occurrences."""
    db = get_db()
    try:
        rows = db.get_unknown_terms(
            status=None if status == "all" else status, dimension=dimension, limit=limit
        )
    finally:
        db.close()

    if not rows:
        _print("No unknown terms.")
        return

    _print(f"{len(rows)} unknown term(s):")
    _print(f"{'DIMENSION':<12} {'COUNT':>6}  {'STATUS':<10} {'TERM':<40} EXAMPLE")
    for row in rows:
        _print(
            f"{row['dimension']:<12} {row['occurrences']:>6}  {row['status']:<10} "
            f"{row['term'][:40]:<40} {row.get('example_content_id') or ''}"
        )


@vocab_group.command("stage-rescan")
@click.option("--execute", is_flag=True, default=False,
              help="Actually stage the re-scan. Without this, only report the cost.")
def vocab_stage_rescan(execute: bool):
    """Stage the one-off Babylon re-scan that applies normalization corpus-wide.

    Marks analyzed Babylon lab/demo stages stale and clears their content hash
    so `rcars scan` validates each stage independently under the scoped policy.
    URL/ref counts are informational, never an estimate of LLM calls or fan-out.
    """
    db = get_db()
    try:
        with db.pool.connection() as conn:
            cur = conn.execute("""
                SELECT COUNT(*) AS items,
                       COUNT(DISTINCT (COALESCE(bi.showroom_url_override, bi.showroom_url),
                                       COALESCE(bi.showroom_ref, ''))) AS showrooms
                FROM showroom_analysis sa
                JOIN content_entities ce ON ce.content_id = sa.content_id
                JOIN babylon_items bi ON bi.content_id = sa.content_id
                WHERE ce.retired_at IS NULL AND ce.content_type IN ('lab', 'demo')
            """)
            counts = cur.fetchone()

        _print(f"Analyzed Babylon items:     {counts['items']}")
        _print(f"Distinct source URL/ref pairs: {counts['showrooms']} (informational only)")

        if not execute:
            _print("")
            _print("Dry run. Re-run with --execute to stage, then run: rcars scan")
            return

        with db.pool.connection() as conn:
            cur = conn.execute("""
                UPDATE showroom_analysis sa
                SET is_stale = TRUE, content_hash = NULL
                FROM content_entities ce
                JOIN babylon_items bi ON bi.content_id = ce.content_id
                WHERE ce.content_id = sa.content_id
                  AND ce.retired_at IS NULL
                  AND ce.content_type IN ('lab', 'demo')
            """)
            staged = cur.rowcount
            conn.commit()

        _print(f"Staged {staged} item(s) for re-analysis. Now run: rcars scan")
    finally:
        db.close()


# ── Portfolio architecture (OSSPA) commands ──

@cli.group(name="osspa")
def osspa_group():
    """Portfolio architecture ingest commands."""
    pass


@osspa_group.command("sync")
@click.option("--force", is_flag=True, default=False,
              help="Re-analyze every item, bypassing the content-hash check")
@click.option("--confirm-empty-inventory", is_flag=True, default=False,
              help="Permit retiring ALL architectures when the inventory has zero in-scope rows")
def osspa_sync_cmd(force: bool, confirm_empty_inventory: bool):
    """Sync portfolio architectures from OSSPA GitLab."""
    from rcars.services.osspa_sync import run_osspa_sync

    settings = Settings()
    db = Database(settings.database_url)
    try:
        _print("Syncing portfolio architectures from OSSPA...")
        try:
            result = run_osspa_sync(
                db, settings, force=force,
                confirm_empty_inventory=confirm_empty_inventory,
                on_progress=lambda phase, message: _print(f"  {message}"),
            )
        except Exception as e:
            _print(f"ERROR: {e}")
            raise SystemExit(1)
    finally:
        db.close()

    if result["status"] == "locked":
        _print("  Another OSSPA sync is already running — nothing to do.")
        return
    if result["status"] == "aborted_empty_inventory":
        _print("  ABORTED: no in-scope rows in PAList.csv. Nothing was upserted or retired.")
        _print("  Re-run with --confirm-empty-inventory only if the inventory is genuinely empty.")
        raise SystemExit(1)

    _print(f"  In scope:  {result['scoped_rows']}")
    _print(f"  Upserted:  {result['upserted']}")
    _print(f"  Analyzed:  {result['analyzed']}")
    _print(f"  Unchanged: {result['skipped']}")
    _print(f"  Retired:   {result['retired']}")
    _print(f"  Failed:    {result['failed']}")
    if result["retire_skipped_reason"]:
        _print(f"  WARNING: retirement skipped ({result['retire_skipped_reason']})")


@cli.group(name="retirement")
def retirement_group():
    """Retirement workflow commands."""
    pass


@retirement_group.command("sweep")
def retirement_sweep_cmd():
    """Open removal PRs for items past their retirement target date."""
    import asyncio as _asyncio
    from rcars.services.agv_access import create_retire_pr
    from rcars.services.retirement_cleanup import workflow_lock_id
    from rcars.services.retirement_jira_events import deliver_pending_events

    settings = Settings()
    if not settings.github_app_id:
        _print("ERROR: RCARS_GITHUB_APP_ID not set — GitHub App not configured.")
        raise SystemExit(1)

    db = Database(settings.database_url)
    try:
        ready = db.list_retirement_ready_for_removal()
        if not ready:
            _print("No items ready for removal PRs.")
            for error in _asyncio.run(deliver_pending_events(db, settings)):
                _print(f"  WARN {error}")
            return

        _print(f"Found {len(ready)} item(s) ready for removal PRs...")

        async def _sweep():
            opened = 0
            for wf in ready:
                content_id = wf["content_id"]
                base_name = content_id.removeprefix("babylon:")
                jira_key = wf.get("jira_key", "")
                if not jira_key:
                    _print(f"  SKIP {base_name}: no Jira key")
                    continue
                try:
                    with db.advisory_lock(workflow_lock_id(content_id)) as acquired:
                        if not acquired:
                            continue
                        current = db.get_retirement_workflow(content_id)
                        if not current or current.get("cancellation_requested_at") or current.get("agv_revert_pr_url") or current.get("agv_retire_pr_url") or current.get("step_retired_at"):
                            continue
                        result = await create_retire_pr(settings, base_name, jira_key)
                        db.record_retirement_pr(content_id, "agv_retire_pr_url", result)
                        db.log_action(base_name, "agv_retire_pr_opened", "cli", f"PR: {result['pr_url']}")
                    _print(f"  OK {base_name}: {result['pr_url']}")
                    opened += 1
                except Exception as exc:
                    _print(f"  FAIL {base_name}: {exc}")
            for error in await deliver_pending_events(db, settings):
                _print(f"  WARN {error}")
            return opened

        opened = _asyncio.run(_sweep())
        _print(f"Done. Opened {opened} removal PR(s).")
    finally:
        db.close()
