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


def get_db(ensure_schema: bool = False) -> Database:
    """Get database connection from settings."""
    settings = Settings()
    if not settings.database_url:
        console.print("[red]Error:[/red] RCARS_DATABASE_URL not set")
        sys.exit(1)
    db = Database(settings.database_url)
    if ensure_schema:
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
    db = get_db(ensure_schema=True)

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


@cli.command()
@click.argument("ci_name")
def show(ci_name: str):
    """Show details for a specific catalog item."""
    db = get_db()
    item = db.get_catalog_item(ci_name)

    if not item:
        console.print(f"[yellow]Not found:[/yellow] {ci_name}")
        db.close()
        return

    console.print(f"\n[bold]{item.get('display_name', ci_name)}[/bold]")
    console.print(f"  CI Name:    {item['ci_name']}")
    console.print(f"  Category:   {item.get('category', '-')}")
    console.print(f"  Product:    {item.get('product', '-')}")
    console.print(f"  Stage:      {item.get('stage', '-')}")
    console.print(f"  Keywords:   {', '.join(item.get('keywords') or [])}")
    console.print(f"  Showroom:   {item.get('showroom_url', '-')}")
    console.print(f"  Ref:        {item.get('showroom_ref', '-')}")

    if item.get("description"):
        desc = item["description"]
        if len(desc) > 200:
            desc = desc[:200] + "..."
        console.print(f"\n  [dim]{desc}[/dim]")

    console.print()
    db.close()
