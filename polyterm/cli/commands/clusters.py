"""Wallet Cluster Detection command"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ...core.cluster_detector import WalletClusterDetector
from ...db.database import Database
from ...utils.json_output import print_json


@click.command()
@click.option("--min-score", default=60, help="Minimum cluster score (0-100)")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def clusters(ctx, min_score, output_format):
    """Detect wallet clusters (same entity controlling multiple wallets)

    Analyzes trading patterns to identify wallets that may be controlled
    by the same person or entity. Checks timing correlation, market overlap,
    and position size patterns.

    Examples:
        polyterm clusters
        polyterm clusters --min-score 70
        polyterm clusters --format json
    """
    console = Console()
    db = Database()

    try:
        if output_format != 'json':
            console.print()
            console.print(Panel(
                "[bold cyan]Wallet Cluster Detection[/bold cyan]\n\n"
                "Analyzing trading patterns to identify linked wallets.\n"
                "[dim]Checks timing, market overlap, and trade sizes.[/dim]",
                border_style="cyan"
            ))
            console.print()
            console.print("[dim]Analyzing wallet patterns...[/dim]")

        detector = WalletClusterDetector(db)
        results = detector.detect_clusters(min_score=min_score)

        if output_format == 'json':
            print_json({
                'success': True,
                'min_score': min_score,
                'clusters': results,
                'total_found': len(results),
            })
            return

        if not results:
            console.print()
            console.print("[yellow]No wallet clusters detected[/yellow]")
            console.print(f"[dim]Min score: {min_score}/100[/dim]")
            console.print("[dim]Clusters are detected from locally tracked trade data.[/dim]")
            console.print("[dim]Run 'polyterm whales' or 'polyterm live-monitor' to collect more data.[/dim]")
            return

        console.print(f"[green]Found {len(results)} potential clusters[/green]")
        console.print()

        table = Table(show_header=True, header_style="bold")
        table.add_column("#", width=3)
        table.add_column("Wallet 1", width=18)
        table.add_column("Wallet 2", width=18)
        table.add_column("Score", justify="right", width=8)
        table.add_column("Risk", width=8)
        table.add_column("Signals", max_width=30)

        for i, cluster in enumerate(results, 1):
            w1 = cluster['wallets'][0]
            w2 = cluster['wallets'][1]
            short1 = f"{w1[:8]}...{w1[-6:]}" if len(w1) > 14 else w1
            short2 = f"{w2[:8]}...{w2[-6:]}" if len(w2) > 14 else w2

            risk_color = "red" if cluster['risk'] == 'high' else "yellow" if cluster['risk'] == 'medium' else "green"

            table.add_row(
                str(i),
                short1,
                short2,
                f"{cluster['score']}/100",
                f"[{risk_color}]{cluster['risk'].upper()}[/{risk_color}]",
                ", ".join(cluster['signals']),
            )

        console.print(table)
        console.print()

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
