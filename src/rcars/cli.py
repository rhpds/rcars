"""RCARS CLI — RHDP Content Advisory & Recommendation System."""

import logging
import sys

import click
from rich.console import Console
from rich.table import Table

from rcars.config import Settings
from rcars.db import Database

console = Console()
log = logging.getLogger("rcars")


def _print(msg: str):
    """Print with timestamp and immediately flush for subprocess capture."""
    from datetime import datetime
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{ts} {msg}", flush=True)


def get_db() -> Database:
    """Get database connection from settings. Creates schema if needed."""
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
    db = get_db()  # creates schema if missing

    if drop:
        console.print("[yellow]Dropping all tables...[/yellow]")
        db.drop_schema()
        db.create_schema()
        console.print("[green]Schema recreated.[/green]")
    else:
        console.print("[green]Schema is up to date.[/green]")

    db.close()


@cli.command()
def refresh():
    """Refresh catalog from Babylon CRDs (all namespaces: prod + dev + event)."""
    from rcars.catalog_reader import CatalogReader

    settings = Settings()
    db = get_db()

    namespaces = settings.catalog_namespaces

    console.print(f"[bold]Refreshing catalog from {len(namespaces)} namespace(s)...[/bold]")

    try:
        reader = CatalogReader(settings.kubeconfig_path)
        items = reader.refresh_catalog(
            namespaces=namespaces,
            component_namespace=settings.agnosticv_component_namespace,
        )
    except Exception as e:
        console.print(f"[red]Error connecting to cluster:[/red] {e}")
        db.close()
        sys.exit(1)

    count_with_showroom = 0
    refreshed_ci_names = set()
    for item in items:
        db.upsert_catalog_item(item)
        db.log_action(item["ci_name"], "refresh")
        refreshed_ci_names.add(item["ci_name"])
        if item.get("showroom_url"):
            count_with_showroom += 1

    removed = db.delete_removed_items(refreshed_ci_names)

    console.print(
        f"[green]Done.[/green] {len(items)} items refreshed, "
        f"{count_with_showroom} with Showroom URLs. "
        f"Removed {len(removed)} items no longer in Babylon catalog."
    )
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


@cli.command("list")
@click.option("--prod-only", is_flag=True, default=False, help="Show only prod items")
@click.option("--with-showroom", is_flag=True, default=False, help="Only items with Showroom URLs")
@click.option("--category", type=str, default=None, help="Filter by category")
def list_items(prod_only: bool, with_showroom: bool, category: str | None):
    """List catalog items."""
    db = get_db()
    items = db.list_catalog_items(prod_only=prod_only, category=category)

    if with_showroom:
        items = [i for i in items if i.get("showroom_url")]

    table = Table(title=f"Catalog Items ({len(items)})")
    table.add_column("CI Name", style="cyan", max_width=50)
    table.add_column("Display Name", max_width=40)
    table.add_column("Category")
    table.add_column("Stage")
    table.add_column("Showroom", justify="center")

    for item in items:
        showroom = "[green]Yes[/green]" if item.get("showroom_url") else "[dim]-[/dim]"
        table.add_row(
            item["ci_name"],
            item.get("display_name", ""),
            item.get("category", ""),
            item.get("stage", ""),
            showroom,
        )

    console.print(table)
    db.close()


def _catalog_url(ci_name: str, namespace: str) -> str:
    """Construct demo.redhat.com catalog URL for a CI."""
    return f"https://catalog.demo.redhat.com/catalog?item={namespace}/{ci_name}"


@cli.command()
@click.argument("ci_name")
@click.option("--full", is_flag=True, default=False, help="Show full description")
def show(ci_name: str, full: bool):
    """Show details for a specific catalog item."""
    db = get_db()
    item = db.get_catalog_item(ci_name)

    if not item:
        console.print(f"[yellow]Not found:[/yellow] {ci_name}")
        db.close()
        return

    catalog_ns = item.get("catalog_namespace", "babylon-catalog-prod")
    catalog_link = _catalog_url(item["ci_name"], catalog_ns)

    # Determine item type
    if item.get("is_published"):
        item_type = "[magenta]Virtual CI (Published)[/magenta]"
    elif item.get("published_ci_name"):
        item_type = "[cyan]Base CI[/cyan]"
    else:
        item_type = "[dim]Standalone CI[/dim]"

    console.print(f"\n[bold]{item.get('display_name', ci_name)}[/bold]")
    console.print(f"  CI Name:    {item['ci_name']}")
    console.print(f"  Type:       {item_type}")
    console.print(f"  Catalog:    {catalog_link}")
    console.print(f"  Category:   {item.get('category', '-')}")
    console.print(f"  Product:    {item.get('product', '-')}")
    console.print(f"  Stage:      {item.get('stage', '-')}")
    console.print(f"  Keywords:   {', '.join(item.get('keywords') or [])}")
    console.print(f"  Showroom:   {item.get('showroom_url', '-')}")
    console.print(f"  Ref:        {item.get('showroom_ref', '-')}")

    # Show relationship
    if item.get("is_published") and item.get("base_ci_name"):
        console.print(f"  Base CI:    {item['base_ci_name']}")
    elif item.get("published_ci_name"):
        console.print(f"  Published:  {item['published_ci_name']}")

    if item.get("description"):
        if full:
            console.print(f"\n[dim]{item['description']}[/dim]")
        else:
            desc = item["description"]
            if len(desc) > 200:
                desc = desc[:200] + "..."
                console.print(f"\n  [dim]{desc}[/dim]")
                console.print("  [dim italic](use --full for complete description)[/dim italic]")
            else:
                console.print(f"\n  [dim]{desc}[/dim]")

    console.print()
    db.close()


@cli.command()
@click.option("--max", "max_analyze", type=int, default=None, help="Max items to analyze")
@click.option("--force", is_flag=True, default=False, help="Re-analyze everything")
def scan(max_analyze: int | None, force: bool):
    """Analyze Showroom content via Sonnet API."""
    import shutil
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from pathlib import Path
    from rcars.analyzer import analyze_showroom

    settings = Settings()
    db = get_db()

    # Clean up orphaned clone directories from previous runs
    clone_base = Path(settings.clone_dir)
    if clone_base.exists():
        for entry in clone_base.iterdir():
            if entry.is_dir() and entry.name.startswith("rcars-showroom-"):
                shutil.rmtree(entry, ignore_errors=True)
                log.info("Cleaned up orphaned clone: %s", entry.name)
    else:
        clone_base.mkdir(parents=True, exist_ok=True)

    anthropic_client = settings.get_anthropic_client()
    if not anthropic_client:
        _print("ERROR: No Anthropic credentials (set ANTHROPIC_VERTEX_PROJECT_ID or ANTHROPIC_API_KEY)")
        db.close()
        sys.exit(1)

    # Gather candidates and log filtering decisions
    if force:
        all_items = db.list_catalog_items()
        with_showroom = [i for i in all_items if i.get("showroom_url")]
        _print(f"Force mode: {len(all_items)} total items, {len(with_showroom)} with Showroom URLs")
        items = with_showroom
    else:
        items = db.get_items_needing_analysis()
        _print(f"Found {len(items)} items needing analysis")

    # Filter out published CIs — base CIs own the Showroom content
    published = [i for i in items if i.get("is_published")]
    items = [i for i in items if not i.get("is_published")]
    if published:
        _print(f"Skipped {len(published)} published CIs (analysis stored on base CI):")
        for p in published:
            _print(f"  skip: {p['ci_name']} (published, base={p.get('base_ci_name', '?')})")

    if max_analyze:
        _print(f"Limiting to first {max_analyze} items (--max)")
        items = items[:max_analyze]

    if not items:
        _print("Nothing to analyze. All items are up to date.")
        db.close()
        return

    _print(f"Analyzing {len(items)} Showroom(s) (max_parallel={settings.max_parallel})...")
    for item in items:
        _print(f"  queued: {item['ci_name']}")

    completed = 0
    errors = 0
    total = len(items)

    def process_item(item):
        _print(f"  start: {item['ci_name']}")
        effective_url = item.get("showroom_url_override") or item["showroom_url"]
        return analyze_showroom(
            ci_name=item["ci_name"],
            display_name=item.get("display_name", ""),
            category=item.get("category", ""),
            product=item.get("product", ""),
            showroom_url=effective_url,
            showroom_ref=item.get("showroom_ref"),
            anthropic_client=anthropic_client,
            model=settings.model,
            clone_dir=settings.clone_dir,
            db=db,
        )

    with ThreadPoolExecutor(max_workers=settings.max_parallel) as executor:
        futures = {executor.submit(process_item, item): item for item in items}

        for future in as_completed(futures):
            item = futures[future]
            try:
                result = future.result()
                if result:
                    analysis = result["analysis"]
                    db.upsert_showroom_analysis({
                        "ci_name": result["ci_name"],
                        "content_type": analysis.get("content_type"),
                        "summary": analysis.get("summary"),
                        "products_json": analysis.get("products"),
                        "audience_json": analysis.get("audience"),
                        "topics_json": analysis.get("topics"),
                        "modules_json": analysis.get("modules"),
                        "learning_objectives_json": analysis.get("learning_objectives"),
                        "difficulty": analysis.get("difficulty"),
                        "estimated_duration_min": analysis.get("estimated_duration_min"),
                        "event_fit_json": analysis.get("event_fit"),
                        "use_cases_json": analysis.get("use_cases"),
                        "last_repo_commit": result.get("last_repo_commit"),
                        "last_repo_updated": result.get("last_repo_updated"),
                        "content_hash": result.get("content_hash"),
                        "is_stale": False,
                        "stale_commit": None,
                    })

                    # Store embeddings
                    db.store_embedding(
                        ci_name=result["ci_name"],
                        embed_type="ci_summary",
                        content_text=result["ci_embedding_text"],
                        embedding=result["ci_embedding"],
                    )
                    for mod_emb in result.get("module_embeddings", []):
                        db.store_embedding(
                            ci_name=result["ci_name"],
                            embed_type="module",
                            module_title=mod_emb["module_title"],
                            content_text=mod_emb["content_text"],
                            embedding=mod_emb["embedding"],
                        )

                    db.set_scan_status(result["ci_name"], "success")
                    db.log_action(result["ci_name"], "analyze")
                    completed += 1
                    _print(f"  done: [{completed}/{total}] {item['ci_name']}")
                else:
                    errors += 1
                    db.set_scan_status(
                        item["ci_name"], "failed",
                        error_class="unknown",
                        error_message=f"Analysis returned no result for {item.get('showroom_url')}",
                    )
                    db.log_action(item["ci_name"], "error", details="Analysis returned None")
                    _print(f"  FAIL: {item['ci_name']} — analysis returned None")
            except Exception as e:
                from rcars.analyzer import classify_scan_error
                error_class, error_msg = classify_scan_error(e, url=item.get("showroom_url"))
                errors += 1
                db.set_scan_status(item["ci_name"], "failed", error_class=error_class, error_message=error_msg)
                db.log_action(item["ci_name"], "error", details=error_msg[:500])
                _print(f"  FAIL: {item['ci_name']} — [{error_class}] {error_msg}")

    _print(f"Done. {completed}/{total} analyzed, {errors} errors")
    db.close()


@cli.command("check-stale")
@click.option("--threshold", type=float, default=0.05,
              help="Minimum change ratio to mark stale (0.0-1.0, default 0.05 = 5%%)")
@click.option("--dry-run", is_flag=True, default=False,
              help="Report changes without marking anything stale")
def check_stale(threshold: float, dry_run: bool):
    """Check analyzed Showrooms for content changes since last scan."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from rcars.analyzer import (
        clone_showroom, read_showroom_content, filter_boilerplate_files,
        hash_showroom_content, get_repo_head,
    )

    settings = Settings()
    db = get_db()

    analyzed = db.get_analyzed_items()
    # Only check base CIs (published CIs don't have their own showrooms)
    analyzed = [a for a in analyzed if not a.get("is_published")]
    _print(f"Checking {len(analyzed)} analyzed Showrooms for content changes (threshold={threshold:.0%})...")

    stale_count = 0
    unchanged_count = 0
    error_count = 0
    total = len(analyzed)

    def check_item(item):
        ci_name = item["ci_name"]
        clone_path = clone_showroom(item["showroom_url"], item.get("showroom_ref"), settings.clone_dir)
        if not clone_path:
            return {"ci_name": ci_name, "status": "error", "reason": "clone failed"}

        try:
            head_sha, _ = get_repo_head(clone_path)
            raw_files = read_showroom_content(clone_path)
            if not raw_files:
                return {"ci_name": ci_name, "status": "error", "reason": "no .adoc files"}

            content_files = filter_boilerplate_files(raw_files)
            if not content_files:
                content_files = raw_files

            new_hash = hash_showroom_content(content_files)
            old_hash = item.get("content_hash")

            if old_hash and new_hash == old_hash:
                return {"ci_name": ci_name, "status": "unchanged", "head_sha": head_sha}

            # No old hash — backfill without marking stale
            if old_hash is None:
                return {
                    "ci_name": ci_name, "status": "backfill",
                    "head_sha": head_sha, "new_hash": new_hash,
                }

            # Hash differs and old hash existed — content changed
            new_content = "\n".join(content_files[f] for f in sorted(content_files))
            total_chars = len(new_content)
            return {
                "ci_name": ci_name, "status": "stale",
                "head_sha": head_sha, "new_hash": new_hash,
                "total_chars": total_chars,
            }
        finally:
            import shutil
            if clone_path and clone_path.exists():
                shutil.rmtree(clone_path, ignore_errors=True)

    with ThreadPoolExecutor(max_workers=settings.max_parallel) as executor:
        futures = {executor.submit(check_item, item): item for item in analyzed}

        for future in as_completed(futures):
            item = futures[future]
            ci_name = item["ci_name"]
            try:
                result = future.result()
                status = result["status"]

                if status == "unchanged":
                    unchanged_count += 1
                    _print(f"  unchanged: {ci_name}")
                elif status == "backfill":
                    if not dry_run:
                        db.upsert_showroom_analysis({
                            "ci_name": ci_name,
                            "content_hash": result["new_hash"],
                        })
                    _print(f"  backfill:  {ci_name} (hash stored, not marked stale)")
                elif status == "stale":
                    stale_count += 1
                    if not dry_run:
                        db.mark_stale(ci_name, new_commit=result.get("head_sha"))
                    prefix = "STALE" if not dry_run else "would-mark"
                    _print(f"  {prefix}:    {ci_name} (content changed, {result.get('total_chars', '?')} chars)")
                elif status == "error":
                    error_count += 1
                    _print(f"  ERROR:     {ci_name} — {result.get('reason', '?')}")
            except Exception as e:
                error_count += 1
                _print(f"  ERROR:     {ci_name} — {e}")

    _print(f"\nDone. {unchanged_count} unchanged, {stale_count} stale, {error_count} errors (of {total})")
    if stale_count > 0 and not dry_run:
        _print(f"Run 'rcars scan' to re-analyze stale items.")
    db.close()


@cli.command()
@click.argument("query")
@click.option("--url", "event_url", type=str, default=None, help="Event URL to analyze")
@click.option("--include-dev", is_flag=True, default=False, help="Include dev items")
@click.option("--limit", type=int, default=10, help="Max candidates to consider")
@click.option("--cutoff", type=float, default=None, help="Vector distance cutoff (default: from RCARS_VECTOR_CUTOFF)")
@click.option("--triage-cutoff", type=int, default=None, help="Min Haiku relevance score (default: from RCARS_TRIAGE_CUTOFF)")
@click.option("--json-output", is_flag=True, default=False, help="Output raw JSON")
def recommend(query, event_url, include_dev, limit, cutoff, triage_cutoff, json_output):
    """Get content recommendations for an event or use case."""
    import json as json_mod
    from rcars.recommender import run_query
    from rcars.event_parser import parse_event_url

    settings = Settings()
    db = get_db()

    anthropic_client = settings.get_anthropic_client()
    if not anthropic_client:
        console.print("[red]Error:[/red] No Anthropic credentials")
        db.close()
        sys.exit(1)

    # Apply CLI overrides
    if cutoff is not None:
        settings.vector_cutoff = cutoff
    if triage_cutoff is not None:
        settings.triage_cutoff = triage_cutoff

    # If event URL provided, parse it and enhance query
    if event_url:
        console.print("[bold]Parsing event URL...[/bold]")
        event_profile = parse_event_url(event_url, anthropic_client, settings.model)
        if event_profile:
            queries = event_profile.get("search_queries", [])
            themes = event_profile.get("themes", [])
            query = f"{query}. Event themes: {', '.join(themes)}. {' '.join(queries)}"
            console.print(f"  Event: {event_profile.get('event_name', 'Unknown')}")

    console.print("[bold]Searching for recommendations...[/bold]")

    final_state = None
    for state in run_query(
        query=query,
        db=db,
        anthropic_client=anthropic_client,
        settings=settings,
        prod_only=not include_dev,
    ):
        final_state = state
        if state.phase == "VECTOR_DONE":
            console.print(f"  Phase 1: {len(state.candidates)} candidates from vector search ({state.timings.get('vector_search', 0):.1f}s)")
        elif state.phase == "TRIAGE_DONE":
            console.print(f"  Phase 2: {len(state.candidates)} candidates survived triage ({state.timings.get('triage', 0):.1f}s)")
        elif state.phase == "COMPLETE":
            console.print(f"  Phase 3: Rationale generated ({state.timings.get('rationale', 0):.1f}s)")
        elif state.phase == "NO_MATCHES":
            console.print("[yellow]No relevant matches found.[/yellow]")
            db.close()
            return

    if not final_state or not final_state.candidates:
        console.print("[yellow]No recommendations found.[/yellow]")
        db.close()
        return

    if json_output:
        output = {
            "recommendations": [
                {
                    "ci_name": c.ci_name,
                    "display_name": c.display_name,
                    "relevance_score": c.relevance_score,
                    "rationale": c.rationale,
                    "suggested_format": c.suggested_format,
                    "duration_notes": c.duration_notes,
                    "caveats": c.caveats,
                }
                for c in final_state.candidates
            ],
            "overall_assessment": final_state.overall_assessment,
            "content_gaps": final_state.content_gaps,
            "timings": final_state.timings,
        }
        console.print(json_mod.dumps(output, indent=2))
    else:
        console.print("\n[bold]Recommendations[/bold]\n")
        for c in final_state.candidates:
            score = c.relevance_score or c.vector_similarity_pct
            color = "green" if score >= 80 else "yellow" if score >= 60 else "red"
            console.print(f"  [{color}]{score}%[/{color}] [bold]{c.display_name}[/bold]")
            ci_name = c.ci_name
            catalog_ns = "babylon-catalog-prod" if not include_dev else "babylon-catalog-dev"
            catalog_link = _catalog_url(ci_name, catalog_ns)
            console.print(f"       [dim]CI:[/dim] {ci_name}  [dim]→[/dim] {catalog_link}")
            if c.rationale:
                console.print(f"       {c.rationale}")
            elif c.one_line_reason:
                console.print(f"       {c.one_line_reason}")
            console.print(f"       Format: {c.suggested_format or '-'} | {c.duration_notes or ''}")
            if c.caveats:
                console.print(f"       [dim]Caveat: {c.caveats}[/dim]")
            console.print()

        if final_state.content_gaps:
            console.print("[bold]Content Gaps[/bold]")
            for gap in final_state.content_gaps:
                console.print(f"  • {gap}")

        if final_state.overall_assessment:
            console.print(f"\n[dim]{final_state.overall_assessment}[/dim]")

    db.close()


@cli.command()
@click.option("--host", default="127.0.0.1", show_default=True, help="Host to bind")
@click.option("--port", default=8000, show_default=True, type=int, help="Port to listen on")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
def serve(host: str, port: int, reload: bool):
    """Start the RCARS web UI."""
    import uvicorn
    uvicorn.run("rcars.web.app:app", host=host, port=port, reload=reload)
