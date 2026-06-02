"""Archive command - inspect local research archive."""

import click
from rich.console import Console
from rich.table import Table

from ...core.archive import ArchiveCollector
from ...db.database import Database
from ...utils.json_output import print_json


@click.group()
def archive():
    """Search and inspect local research archive data"""


@archive.command("search")
@click.option("--query", "query", default="", help="Search query, market slug, title, or market id")
@click.option("--limit", default=20, show_default=True, type=int, help="Maximum archived briefs to return")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
def search(query, limit, output_format):
    """Search archived market research briefs"""
    collector = ArchiveCollector(database=Database())
    result = collector.search_research_briefs(query=query, limit=limit)

    if output_format == "json":
        print_json({"success": True, "archive": result})
        return

    console = Console()
    table = Table(title="Research Brief Archive")
    table.add_column("ID")
    table.add_column("Query")
    table.add_column("Market")
    table.add_column("Generated")
    table.add_column("Recommendation")

    for brief in result["briefs"]:
        table.add_row(
            str(brief.get("id", "")),
            brief.get("query", ""),
            brief.get("market_slug") or brief.get("title", ""),
            brief.get("generated_at", ""),
            brief.get("brief", {}).get("recommendation", ""),
        )
    console.print(table)
    console.print(f"[dim]Quality flags: {', '.join(result['quality_flags'])}[/dim]")
