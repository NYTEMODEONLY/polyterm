"""Collect command - research archive snapshots"""

import click
from rich.console import Console

from ...api.gamma import GammaClient
from ...core.archive import ArchiveCollector
from ...db.database import Database
from ...utils.errors import handle_api_error
from ...utils.json_output import print_json


def _parse_duration(value: str) -> int:
    """Parse short duration strings such as 30s, 10m, or 1h."""
    value = str(value).strip().lower()
    if value.endswith("m"):
        return int(float(value[:-1]) * 60)
    if value.endswith("h"):
        return int(float(value[:-1]) * 3600)
    if value.endswith("s"):
        return int(float(value[:-1]))
    return int(float(value))


@click.command()
@click.option("--market", "-m", required=True, help="Market slug, ID, or search term")
@click.option("--interval", default="30s", help="Collection interval, e.g. 30s or 5m")
@click.option("--duration", default="0s", help="Foreground duration. 0s collects once.")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def collect(ctx, market, interval, duration, output_format):
    """Collect local research archive snapshots"""
    config = ctx.obj["config"]
    console = Console()
    gamma = GammaClient(base_url=config.gamma_base_url, api_key=config.gamma_api_key)

    try:
        collector = ArchiveCollector(database=Database(), gamma_client=gamma)
        interval_seconds = _parse_duration(interval)
        duration_seconds = _parse_duration(duration)

        if duration_seconds <= 0:
            result = collector.collect_once(market)
        else:
            result = collector.collect_for_duration(
                market=market,
                interval_seconds=interval_seconds,
                duration_seconds=duration_seconds,
            )

        if output_format == "json":
            print_json({"success": bool(result.get("success", True)), "archive": result})
            return

        if result.get("success", True):
            count = result.get("snapshot_count", 1)
            console.print(f"[green]Collected {count} snapshot(s).[/green]")
            console.print(f"[dim]Quality flags: {', '.join(result.get('quality_flags', []))}[/dim]")
        else:
            console.print(f"[red]Collection failed: {', '.join(result.get('quality_flags', []))}[/red]")

    except KeyboardInterrupt:
        if output_format == "json":
            print_json({"success": True, "stopped": True})
        else:
            console.print("[yellow]Collection stopped.[/yellow]")
    except Exception as exc:
        if output_format == "json":
            print_json({"success": False, "error": str(exc)})
        else:
            handle_api_error(console, exc, "archive collection")
    finally:
        gamma.close()
