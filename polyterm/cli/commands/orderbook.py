"""Orderbook command - order book analysis and visualization"""

import click
from datetime import datetime
from rich.console import Console
from rich.panel import Panel

from ...api.clob import CLOBClient
from ...db.database import Database
from ...core.orderbook import OrderBookAnalyzer
from ...utils.json_output import print_json, format_orderbook_json


@click.command()
@click.argument("market_id")
@click.option("--depth", default=20, help="Order book depth")
@click.option("--chart", is_flag=True, help="Show ASCII depth chart")
@click.option("--slippage", default=None, type=float, help="Calculate slippage for order size")
@click.option("--side", type=click.Choice(["buy", "sell"]), default="buy", help="Order side for slippage")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table", help="Output format")
@click.pass_context
def orderbook(ctx, market_id, depth, chart, slippage, side, output_format):
    """Analyze order book for a market

    MARKET_ID is the market token ID to analyze.
    """

    config = ctx.obj["config"]
    console = Console()

    # Initialize
    clob_client = CLOBClient(rest_endpoint=config.clob_rest_endpoint)
    db = Database()
    analyzer = OrderBookAnalyzer(clob_client)

    try:
        if output_format != 'json':
            console.print(f"[cyan]Analyzing order book for {market_id[:30]}...[/cyan]\n")

        # Get analysis
        analysis = analyzer.analyze(market_id, depth=depth)

        if not analysis:
            if output_format == 'json':
                print_json({'success': False, 'error': 'Could not fetch order book'})
            else:
                console.print("[red]Could not fetch order book data[/red]")
            return

        # Slippage calculation
        slippage_result = None
        if slippage:
            slippage_result = analyzer.calculate_slippage(market_id, side, slippage)

        # JSON output
        if output_format == 'json':
            output = {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'analysis': format_orderbook_json(analysis),
            }
            if slippage_result:
                output['slippage'] = slippage_result
            print_json(output)
            return

        # Display analysis
        console.print(Panel(analyzer.format_analysis(analysis), title="Order Book Analysis"))

        # Show chart if requested
        if chart:
            console.print("\n")
            chart_text = analyzer.render_ascii_depth_chart(market_id, depth=depth)
            console.print(Panel(chart_text, title="Depth Chart"))

        # Show slippage if calculated
        if slippage_result:
            console.print(f"\n[bold]Slippage Analysis ({side.upper()} {slippage:,.0f} shares):[/bold]")
            if 'error' in slippage_result:
                console.print(f"  [red]{slippage_result['error']}[/red]")
            else:
                console.print(f"  Best price: ${slippage_result['best_price']:.4f}")
                console.print(f"  Avg price: ${slippage_result['avg_price']:.4f}")
                console.print(f"  Slippage: ${slippage_result['slippage']:.4f} ({slippage_result['slippage_pct']:.2f}%)")
                console.print(f"  Total cost: ${slippage_result['total_cost']:,.2f}")
                console.print(f"  Price levels used: {slippage_result['levels_used']}")

        # Check for icebergs
        icebergs = analyzer.detect_iceberg_orders(market_id)
        if icebergs:
            console.print(f"\n[yellow]Potential iceberg orders detected: {len(icebergs)}[/yellow]")
            for iceberg in icebergs[:3]:
                console.print(f"  {iceberg['side'].upper()}: {iceberg['size']:,.0f} shares @ multiple prices")

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        clob_client.close()
