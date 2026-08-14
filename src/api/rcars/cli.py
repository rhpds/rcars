"""RCARS CLI — RHDP Content Advisory & Recommendation System."""

from __future__ import annotations

import logging
import sys

import click
from rich.console import Console
from rich.table import Table

from rcars.config import Settings
from rcars.db import Database
from rcars.db.overlap import generate_overlap_candidates, get_overlap_stats
from rcars.workers.scan import _sanitize_format_suitability

console = Console()
log = logging.getLogger("rcars")


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
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )


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

    retired = db.retire_removed_items(current_content_ids)
    if retired:
        for r in retired:
            _print(f"  retired: {r['content_id']} (stage={r.get('stage', '?')})")

    elapsed = time.monotonic() - t0
    _print(f"Done in {elapsed:.1f}s. {len(items)} items, {count_with_showroom} with Showroom, {len(retired)} retired.")
    db.close()


@cli.command()
@click.option("--max", "max_analyze", type=int, default=None, help="Max items to analyze")
def scan(max_analyze: int | None):
    """Analyze Showroom content via Sonnet API."""
    import shutil
    import time
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from pathlib import Path
    from rcars.services.analyzer import analyze_showroom, classify_scan_error

    settings = Settings()
    db = get_db()

    clone_base = Path(settings.clone_dir)
    clone_base.mkdir(parents=True, exist_ok=True)

    from rcars.config import fetch_litemaas_models
    if settings.use_litemaas:
        fetch_litemaas_models(settings)
    elif not settings.get_anthropic_client():
        _print("ERROR: No LLM provider configured (set RCARS_LITEMAAS_URL or ANTHROPIC_VERTEX_PROJECT_ID)")
        db.close()
        sys.exit(1)

    from rcars.workers.ops import sha_dedup_scan_items

    items = db.get_items_needing_analysis()
    _print(f"Found {len(items)} items needing analysis (ref-deduped)")

    items = [i for i in items if not i.get("is_published")]

    scan_items, sha_siblings_map = sha_dedup_scan_items(items)
    sha_merged = len(items) - len(scan_items)
    if sha_merged:
        _print(f"SHA dedup: {len(items)} ref-groups → {len(scan_items)} SHA-groups ({sha_merged} merged)")

    if max_analyze:
        _print(f"Limiting to first {max_analyze} items (--max)")
        scan_items = scan_items[:max_analyze]

    if not scan_items:
        _print("Nothing to analyze.")
        db.close()
        return

    items = scan_items
    _print(f"Analyzing {len(items)} Showroom(s) (max_parallel={settings.max_parallel})...")
    completed = 0
    errors = 0
    total = len(items)
    t0 = time.monotonic()

    def process_item(item):
        effective_url = item.get("showroom_url_override") or item["showroom_url"]
        return analyze_showroom(
            ci_name=item["ci_name"],
            display_name=item.get("display_name", ""),
            category=item.get("category", ""),
            product=item.get("product", ""),
            showroom_url=effective_url,
            showroom_ref=item.get("showroom_ref"),
            settings=settings,
            model=settings.model,
            clone_dir=settings.clone_dir,
            db=db,
            content_path=item.get("content_path"),
            keywords=item.get("keywords") or [],
        )

    with ThreadPoolExecutor(max_workers=settings.max_parallel) as executor:
        futures = {executor.submit(process_item, item): item for item in items}
        for future in as_completed(futures):
            item = futures[future]
            content_id = item["content_id"]
            content_type = item.get("content_type", "lab")
            try:
                result = future.result()
                if result and "error" in result:
                    errors += 1
                    db.set_scan_status(content_id, "failed", error_class=result["error"], error_message=result["message"])
                    _print(f"  FAIL: {item['ci_name']} — [{result['error']}] {result['message']}")
                elif result and "analysis" in result:
                    analysis = result["analysis"]
                    db.upsert_showroom_analysis({
                        "content_id": content_id,
                        "content_type": analysis.get("content_type"),
                        "summary": analysis.get("summary"),
                        "products_json": analysis.get("products"),
                        "audience_json": analysis.get("audience"),
                        "topics_json": analysis.get("topics"),
                        "modules_json": analysis.get("modules"),
                        "learning_objectives_json": analysis.get("learning_objectives"),
                        "difficulty": analysis.get("difficulty"),
                        "estimated_duration_min": analysis.get("estimated_duration_min"),
                        "format_suitability_json": _sanitize_format_suitability(analysis.get("format_suitability")),
                        "use_cases_json": analysis.get("use_cases"),
                        "last_repo_commit": result.get("last_repo_commit"),
                        "last_repo_updated": result.get("last_repo_updated"),
                        "content_hash": result.get("content_hash"),
                        "is_stale": False,
                        "stale_commit": None,
                    })
                    db.clear_embeddings(content_id)
                    db.store_embedding(
                        content_id=content_id, content_type=content_type, source="babylon",
                        embed_type="summary",
                        content_text=result["ci_embedding_text"], embedding=result["ci_embedding"],
                    )
                    for mod_emb in result.get("module_embeddings", []):
                        db.store_embedding(
                            content_id=content_id, content_type=content_type, source="babylon",
                            embed_type="module",
                            module_title=mod_emb["module_title"],
                            content_text=mod_emb["content_text"], embedding=mod_emb["embedding"],
                        )
                    db.set_scan_status(content_id, "success")

                    # Propagate to siblings with same (url, ref)
                    effective_url = item.get("showroom_url_override") or item["showroom_url"]
                    siblings = db.get_siblings_by_showroom(effective_url, item.get("showroom_ref"))
                    propagated_set = {content_id}
                    analysis_data = {
                        "content_id": None,
                        "content_type": analysis.get("content_type"),
                        "summary": analysis.get("summary"),
                        "products_json": analysis.get("products"),
                        "audience_json": analysis.get("audience"),
                        "topics_json": analysis.get("topics"),
                        "modules_json": analysis.get("modules"),
                        "learning_objectives_json": analysis.get("learning_objectives"),
                        "difficulty": analysis.get("difficulty"),
                        "estimated_duration_min": analysis.get("estimated_duration_min"),
                        "format_suitability_json": _sanitize_format_suitability(analysis.get("format_suitability")),
                        "use_cases_json": analysis.get("use_cases"),
                        "last_repo_commit": result.get("last_repo_commit"),
                        "last_repo_updated": result.get("last_repo_updated"),
                        "content_hash": result.get("content_hash"),
                        "is_stale": False,
                        "stale_commit": None,
                    }

                    def _cli_propagate(sib_content_id, sib_content_type):
                        sib_data = dict(analysis_data)
                        sib_data["content_id"] = sib_content_id
                        db.upsert_showroom_analysis(sib_data)
                        db.clear_embeddings(sib_content_id)
                        db.store_embedding(
                            content_id=sib_content_id, content_type=sib_content_type, source="babylon",
                            embed_type="summary",
                            content_text=result["ci_embedding_text"], embedding=result["ci_embedding"],
                        )
                        for mod_emb in result.get("module_embeddings", []):
                            db.store_embedding(
                                content_id=sib_content_id, content_type=sib_content_type, source="babylon",
                                embed_type="module",
                                module_title=mod_emb["module_title"],
                                content_text=mod_emb["content_text"], embedding=mod_emb["embedding"],
                            )
                        db.set_scan_status(sib_content_id, "success")

                    for sibling in siblings:
                        if sibling["content_id"] not in propagated_set:
                            _cli_propagate(sibling["content_id"], sibling.get("content_type", "lab"))
                            propagated_set.add(sibling["content_id"])

                    # Propagate to SHA siblings (different ref, same commit)
                    sha_sibs = sha_siblings_map.get(content_id, [])
                    for sha_sib in sha_sibs:
                        sib_cid = sha_sib["content_id"]
                        sib_ctype = sha_sib.get("content_type", "lab")
                        if sib_cid not in propagated_set:
                            _cli_propagate(sib_cid, sib_ctype)
                            propagated_set.add(sib_cid)
                            ref_sibs = db.get_siblings_by_showroom(sha_sib["effective_url"], sha_sib.get("showroom_ref"))
                            for ref_sib in ref_sibs:
                                if ref_sib["content_id"] not in propagated_set:
                                    _cli_propagate(ref_sib["content_id"], ref_sib.get("content_type", "lab"))
                                    propagated_set.add(ref_sib["content_id"])

                    propagated = len(propagated_set) - 1
                    completed += 1
                    prop_msg = f" (+{propagated} siblings)" if propagated else ""
                    _print(f"  done: [{completed}/{total}] {item['ci_name']}{prop_msg}")
                else:
                    errors += 1
                    db.set_scan_status(content_id, "failed", error_class="no_result", error_message="Analysis returned no results")
                    _print(f"  FAIL: {item['ci_name']} — analysis returned no results")
            except Exception as e:
                error_class, error_msg = classify_scan_error(
                    e, url=item.get("showroom_url"), ref=item.get("showroom_ref"),
                    content_path=item.get("content_path"))
                errors += 1
                db.set_scan_status(content_id, "failed", error_class=error_class, error_message=error_msg)
                _print(f"  FAIL: {item['ci_name']} — [{error_class}] {error_msg}")

    elapsed = time.monotonic() - t0
    _print(f"Done in {elapsed:.1f}s. {completed}/{total} analyzed, {errors} errors")
    db.close()


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
@click.option("--include-configs", is_flag=True, default=False, help="Also scan AgnosticD v2 base configs")
def workload_scan(collection: str | None, force: bool, include_configs: bool):
    """Scan agDv2 workload repos and optionally base configs via LLM."""
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
                   f"{r.get('roles_mapped', 0)} mapped, {r.get('roles_plumbing', 0)} plumbing")

    total_scanned = sum(r.get("roles_scanned", 0) for r in results)
    total_mapped = sum(r.get("roles_mapped", 0) for r in results)
    _print(f"Done. {total_scanned} roles scanned, {total_mapped} new/updated mappings.")

    if include_configs:
        console.print("\n[bold]Scanning base configs...[/bold]")
        config_result = scan_configs(settings.clone_dir, settings, model, db, force=force)
        console.print(f"Configs: {config_result}")

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
@click.pass_context
def reporting_db_sync(ctx):
    """Sync reporting metrics from RHDP MCP server."""
    from rcars.services.reporting_sync import run_reporting_sync

    settings = Settings()
    if not settings.reporting_mcp_url or not settings.reporting_mcp_token:
        _print("ERROR: RCARS_REPORTING_MCP_URL and RCARS_REPORTING_MCP_TOKEN must be set.")
        raise SystemExit(1)

    db = Database(settings.database_url)
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
