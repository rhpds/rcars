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
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


@cli.command()
@click.option(
    "--include-dev",
    is_flag=True,
    default=False,
    help="Include dev and event catalog items (default: prod only)",
)
def refresh(include_dev: bool):
    """Refresh catalog from Babylon CRDs."""
    from rcars.catalog_reader import CatalogReader

    settings = Settings()
    db = get_db()

    namespaces = (
        settings.catalog_namespaces_all if include_dev
        else settings.catalog_namespaces_prod
    )

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
    for item in items:
        db.upsert_catalog_item(item)
        db.log_action(item["ci_name"], "refresh")
        if item.get("showroom_url"):
            count_with_showroom += 1

    console.print(f"[green]Done.[/green] {len(items)} items refreshed, {count_with_showroom} with Showroom URLs")
    db.close()


@cli.command()
def status():
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

    console.print(table)
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
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from rcars.analyzer import analyze_showroom

    settings = Settings()
    db = get_db()

    anthropic_client = settings.get_anthropic_client()
    if not anthropic_client:
        console.print("[red]Error:[/red] No Anthropic credentials (set ANTHROPIC_VERTEX_PROJECT_ID or ANTHROPIC_API_KEY)")
        db.close()
        sys.exit(1)

    if force:
        items = db.list_catalog_items()
        items = [i for i in items if i.get("showroom_url")]
    else:
        items = db.get_items_needing_analysis()

    # Filter to non-published items (analyze base CIs, not published VCIs)
    items = [i for i in items if not i.get("is_published")]

    if max_analyze:
        items = items[:max_analyze]

    if not items:
        console.print("[green]Nothing to analyze.[/green] All items are up to date.")
        db.close()
        return

    console.print(f"[bold]Analyzing {len(items)} Showroom(s)...[/bold]")

    completed = 0
    errors = 0

    def process_item(item):
        return analyze_showroom(
            ci_name=item["ci_name"],
            display_name=item.get("display_name", ""),
            category=item.get("category", ""),
            product=item.get("product", ""),
            showroom_url=item["showroom_url"],
            showroom_ref=item.get("showroom_ref"),
            anthropic_client=anthropic_client,
            model=settings.model,
            clone_dir=settings.clone_dir,
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

                    db.log_action(result["ci_name"], "analyze")
                    completed += 1
                    console.print(f"  [green]✓[/green] {item['ci_name']}")
                else:
                    errors += 1
                    db.log_action(item["ci_name"], "error", details="Analysis returned None")
                    console.print(f"  [red]✗[/red] {item['ci_name']}")
            except Exception as e:
                errors += 1
                db.log_action(item["ci_name"], "error", details=str(e)[:200])
                console.print(f"  [red]✗[/red] {item['ci_name']}: {e}")

    console.print(f"\n[bold]Done.[/bold] {completed} analyzed, {errors} errors")
    db.close()


@cli.command()
@click.argument("query")
@click.option("--url", "event_url", type=str, default=None, help="Event URL to analyze")
@click.option("--include-dev", is_flag=True, default=False, help="Include dev items")
@click.option("--limit", type=int, default=15, help="Max candidates to consider")
@click.option("--json-output", is_flag=True, default=False, help="Output raw JSON")
def recommend(query: str, event_url: str | None, include_dev: bool, limit: int, json_output: bool):
    """Get content recommendations for an event or use case."""
    import json as json_mod
    from rcars.recommender import recommend as run_recommend
    from rcars.event_parser import parse_event_url

    settings = Settings()
    db = get_db()

    anthropic_client = settings.get_anthropic_client()
    if not anthropic_client:
        console.print("[red]Error:[/red] No Anthropic credentials")
        db.close()
        sys.exit(1)

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

    result = run_recommend(
        query=query,
        db=db,
        anthropic_client=anthropic_client,
        model=settings.model,
        limit=limit,
        prod_only=not include_dev,
    )

    if not result:
        console.print("[yellow]No recommendations found.[/yellow]")
        db.close()
        return

    if json_output:
        console.print(json_mod.dumps(result, indent=2))
    else:
        console.print("\n[bold]Recommendations[/bold]\n")
        for rec in result.get("recommendations", []):
            score = rec.get("fit_score", 0)
            color = "green" if score >= 80 else "yellow" if score >= 60 else "red"
            console.print(f"  [{color}]{score}%[/{color}] [bold]{rec.get('display_name', rec.get('ci_name'))}[/bold]")
            ci_name = rec.get('ci_name', '')
            catalog_ns = "babylon-catalog-prod" if not include_dev else "babylon-catalog-dev"
            catalog_link = _catalog_url(ci_name, catalog_ns)
            console.print(f"       [dim]CI:[/dim] {ci_name}  [dim]→[/dim] {catalog_link}")
            console.print(f"       {rec.get('rationale', '')}")
            console.print(f"       Format: {rec.get('suggested_format', '-')} | {rec.get('duration_notes', '')}")
            if rec.get("caveats"):
                console.print(f"       [dim]Caveat: {rec['caveats']}[/dim]")
            console.print()

        if result.get("content_gaps"):
            console.print("[bold]Content Gaps[/bold]")
            for gap in result["content_gaps"]:
                console.print(f"  • {gap}")

        if result.get("overall_assessment"):
            console.print(f"\n[dim]{result['overall_assessment']}[/dim]")

    db.close()


@cli.command()
@click.option("--host", default="127.0.0.1", show_default=True, help="Host to bind")
@click.option("--port", default=8000, show_default=True, type=int, help="Port to listen on")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
def serve(host: str, port: int, reload: bool):
    """Start the RCARS web UI."""
    import uvicorn
    uvicorn.run("rcars.web.app:app", host=host, port=port, reload=reload)
