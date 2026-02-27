"""News command - View market-relevant news headlines"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ...core.news import NewsAggregator
from ...utils.json_output import print_json


@click.command()
@click.option("--market", "-m", default=None, help="Show news for specific market")
@click.option("--hours", default=24, help="Hours of news to show (default: 24)")
@click.option("--limit", default=20, help="Maximum articles to show")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def news(ctx, market, hours, limit, output_format):
    """View market-relevant news headlines

    Aggregates news from crypto and prediction market RSS feeds.
    Optionally filter by market relevance.

    Examples:
        polyterm news
        polyterm news --market "bitcoin"
        polyterm news --hours 6 --limit 10
        polyterm news --format json
    """
    console = Console()
    aggregator = NewsAggregator()

    try:
        if market:
            # Get news for specific market
            if output_format != 'json':
                console.print()
                console.print(f"[dim]Fetching news related to: {market}[/dim]")

            articles = aggregator.get_market_news(market, limit=limit, hours=hours)

            if output_format == 'json':
                cleaned = [{k: v for k, v in a.items() if k != 'published_dt'} for a in articles]
                print_json({
                    'success': True,
                    'market': market,
                    'hours': hours,
                    'articles': cleaned,
                    'count': len(cleaned),
                })
                return

            if not articles:
                console.print(f"[yellow]No news found matching '{market}'[/yellow]")
                return

            console.print()
            console.print(f"[bold]News for: {market}[/bold]")
            console.print()

            for i, article in enumerate(articles, 1):
                source = article.get('source', 'Unknown')
                title = article.get('title', '')
                published = article.get('published', '')[:16]

                console.print(f"  [cyan]{i}.[/cyan] [{source}] {title}")
                if published:
                    console.print(f"     [dim]{published}[/dim]")
                if article.get('summary'):
                    console.print(f"     [dim]{article['summary'][:100]}[/dim]")
                console.print()

        else:
            # Get all recent news
            if output_format != 'json':
                console.print()
                console.print(Panel(
                    "[bold cyan]Market News[/bold cyan]\n\n"
                    "Latest headlines from crypto and prediction market sources.\n"
                    "[dim]Sources: The Block, CoinDesk, Decrypt[/dim]",
                    border_style="cyan"
                ))
                console.print()
                console.print("[dim]Fetching news feeds...[/dim]")

            articles = aggregator.get_breaking_news(hours=hours, limit=limit)

            if output_format == 'json':
                cleaned = [{k: v for k, v in a.items() if k != 'published_dt'} for a in articles]
                print_json({'success': True, 'hours': hours, 'articles': cleaned, 'count': len(cleaned)})
                return

            if not articles:
                console.print("[yellow]No recent news found[/yellow]")
                return

            console.print(f"[green]Found {len(articles)} articles[/green]")
            console.print()

            table = Table(show_header=True, header_style="bold")
            table.add_column("#", width=3)
            table.add_column("Source", width=12)
            table.add_column("Title", max_width=50)
            table.add_column("Published", width=16)

            for i, article in enumerate(articles, 1):
                table.add_row(
                    str(i),
                    article.get('source', ''),
                    article.get('title', '')[:50],
                    article.get('published', '')[:16],
                )

            console.print(table)
            console.print()

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error fetching news: {e}[/red]")
    finally:
        aggregator.close()
