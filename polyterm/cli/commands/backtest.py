"""Backtest Command - DEMO strategy simulation (not historical replay)"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

from ...api.gamma import GammaClient
from ...core.demo_strategy_sim import DEMO_DISCLOSURE, DEMO_MODE, run_demo_simulation
from ...utils.json_output import print_json
from ...utils.errors import handle_api_error


DEMO_UNAVAILABLE = (
    "This command does not replay historical Polymarket data. "
    "It only offers a seeded random DEMO simulation. "
    "Pass --demo to run that simulation, or use `polyterm chart` / "
    "`polyterm replay` for real historical market data."
)


@click.command()
@click.option("--strategy", "-s", type=click.Choice(["momentum", "mean-reversion", "whale-follow", "contrarian", "volume-spike"]),
              default="momentum", help="Demo strategy name")
@click.option("--market", "-m", default=None, help="Market search term used only as simulation labels")
@click.option("--period", "-p", type=click.Choice(["7d", "30d", "90d"]), default="30d", help="Demo window length")
@click.option("--capital", "-c", type=float, default=1000, help="Starting capital ($)")
@click.option("--position-size", type=float, default=0.1, help="Position size as fraction of capital")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode (still requires --demo)")
@click.option("--demo", is_flag=True, help="Required. Acknowledge this is a random demo, not a historical backtest")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def backtest(ctx, strategy, market, period, capital, position_size, interactive, demo, output_format):
    """DEMO strategy simulation (not historical backtesting)

    This command does not replay historical trades or prices.
    Without --demo it refuses to run. With --demo it prints a
    disclosure and then generates seeded random trades.

    Examples:
        polyterm backtest --demo -s momentum -p 30d
        polyterm backtest --demo -i
    """
    console = Console()
    config = ctx.obj["config"]

    if not demo:
        if output_format == "json":
            print_json({
                "success": False,
                "error": DEMO_UNAVAILABLE,
                "mode": "unavailable",
                "uses_historical_data": False,
                "hint": "pass --demo to run the random simulation",
            })
        else:
            console.print()
            console.print(Panel(f"[yellow]{DEMO_UNAVAILABLE}[/yellow]", border_style="yellow"))
            console.print()
        return

    if interactive:
        console.print()
        console.print(Panel("[bold yellow]DEMO Strategy Simulator[/bold yellow]\n[dim]Not historical backtesting[/dim]", border_style="yellow"))
        console.print()
        console.print(f"[yellow]{DEMO_DISCLOSURE}[/yellow]")
        console.print()

        console.print("[cyan]Available Strategies:[/cyan]")
        console.print("  1. Momentum - Follow the trend")
        console.print("  2. Mean Reversion - Fade extremes")
        console.print("  3. Whale Follow - Copy big traders")
        console.print("  4. Contrarian - Bet against crowd")
        console.print("  5. Volume Spike - Trade on high activity")
        console.print()

        strat_choice = Prompt.ask("Select strategy", choices=["1", "2", "3", "4", "5"], default="1")
        strat_map = {
            "1": "momentum",
            "2": "mean-reversion",
            "3": "whale-follow",
            "4": "contrarian",
            "5": "volume-spike",
        }
        strategy = strat_map[strat_choice]

        console.print()
        market = Prompt.ask("[cyan]Market (leave empty for portfolio)[/cyan]", default="")
        if not market:
            market = None

        console.print()
        console.print("[cyan]Backtest Period:[/cyan]")
        console.print("  1. 7 days")
        console.print("  2. 30 days")
        console.print("  3. 90 days")
        period_choice = Prompt.ask("Select period", choices=["1", "2", "3"], default="2")
        period_map = {"1": "7d", "2": "30d", "3": "90d"}
        period = period_map[period_choice]

        console.print()
        cap_str = Prompt.ask("[cyan]Starting capital ($)[/cyan]", default="1000")
        try:
            capital = float(cap_str)
        except ValueError:
            capital = 1000

        console.print()
    elif output_format != "json":
        console.print()
        console.print(Panel(f"[yellow]{DEMO_DISCLOSURE}[/yellow]", border_style="yellow"))
        console.print()

    period_days = {"7d": 7, "30d": 30, "90d": 90}[period]

    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    try:
        if market:
            markets = gamma_client.search_markets(market, limit=5)
        else:
            markets = gamma_client.get_markets(limit=20)

        if not markets:
            if output_format == 'json':
                print_json({'success': False, 'error': 'No markets found', 'mode': DEMO_MODE})
            else:
                console.print("[yellow]No markets found for demo labels.[/yellow]")
            return

        results = run_demo_simulation(markets, strategy, period_days, capital, position_size)

        if output_format == 'json':
            print_json({
                'success': True,
                'mode': results.get('mode', DEMO_MODE),
                'uses_historical_data': False,
                'disclosure': DEMO_DISCLOSURE,
                'strategy': strategy,
                'period': period,
                'starting_capital': capital,
                'position_size': position_size,
                'results': results,
            })
            return

        # Display results
        console.print()
        console.print(Panel(
            f"[bold yellow]DEMO Results: {strategy.title()} Strategy[/bold yellow]\n"
            f"[dim]{DEMO_DISCLOSURE}[/dim]",
            border_style="yellow",
        ))
        console.print()

        # Summary metrics
        console.print("[bold]Performance Summary:[/bold]")
        console.print()

        summary = Table(show_header=False, box=None)
        summary.add_column(style="cyan", width=25)
        summary.add_column(width=20)

        final_value = results['final_capital']
        total_return = ((final_value - capital) / capital) * 100
        return_color = "green" if total_return > 0 else "red" if total_return < 0 else "white"

        summary.add_row("Starting Capital:", f"${capital:,.2f}")
        summary.add_row("Final Value:", f"${final_value:,.2f}")
        summary.add_row("Total Return:", f"[{return_color}]{total_return:+.1f}%[/{return_color}]")
        summary.add_row("", "")
        summary.add_row("Total Trades:", str(results['total_trades']))
        summary.add_row("Winning Trades:", f"[green]{results['winning_trades']}[/green]")
        summary.add_row("Losing Trades:", f"[red]{results['losing_trades']}[/red]")
        summary.add_row("Win Rate:", f"{results['win_rate']:.1f}%")
        summary.add_row("", "")
        summary.add_row("Avg Win:", f"[green]+${results['avg_win']:,.2f}[/green]")
        summary.add_row("Avg Loss:", f"[red]-${results['avg_loss']:,.2f}[/red]")
        profit_factor = results.get("profit_factor")
        summary.add_row(
            "Profit Factor:",
            f"{profit_factor:.2f}" if profit_factor is not None else "n/a (no losing trades)",
        )
        summary.add_row("", "")
        summary.add_row("Max Drawdown:", f"[red]{results['max_drawdown']:.1f}%[/red]")
        summary.add_row("Sharpe Ratio:", f"{results['sharpe_ratio']:.2f}")

        console.print(summary)
        console.print()

        # Trade log
        if results['trades']:
            console.print("[bold]Trade Log (last 10):[/bold]")
            console.print()

            trade_table = Table(show_header=True, header_style="bold cyan", box=None)
            trade_table.add_column("Date", width=12)
            trade_table.add_column("Market", width=30)
            trade_table.add_column("Side", width=6, justify="center")
            trade_table.add_column("Entry", width=8, justify="center")
            trade_table.add_column("Exit", width=8, justify="center")
            trade_table.add_column("P&L", width=12, justify="right")

            for trade in results['trades'][-10:]:
                pnl_color = "green" if trade['pnl'] > 0 else "red" if trade['pnl'] < 0 else "white"
                side_color = "green" if trade['side'] == "BUY" else "red"

                trade_table.add_row(
                    trade['date'],
                    trade['market'][:28],
                    f"[{side_color}]{trade['side']}[/{side_color}]",
                    f"{trade['entry']:.0%}",
                    f"{trade['exit']:.0%}",
                    f"[{pnl_color}]{trade['pnl']:+,.2f}[/{pnl_color}]",
                )

            console.print(trade_table)
            console.print()

        # Equity curve (ASCII)
        console.print("[bold]Equity Curve:[/bold]")
        console.print()

        equity_curve = results.get('equity_curve', [])
        if equity_curve:
            _display_equity_curve(console, equity_curve, capital)

        console.print()

        # Strategy notes
        console.print("[bold]Strategy Notes:[/bold]")
        console.print()

        strategy_notes = {
            "momentum": "Momentum strategies tend to work well in trending markets but suffer in choppy conditions.",
            "mean-reversion": "Mean reversion works best in ranging markets. Watch out for trending periods.",
            "whale-follow": "Following whales can be profitable but has lag. Best for liquid markets.",
            "contrarian": "Contrarian bets can be high reward but require patience and strong conviction.",
            "volume-spike": "Volume spikes often precede big moves. Timing is critical.",
        }
        console.print(f"[dim]{strategy_notes.get(strategy, '')}[/dim]")
        console.print()

        console.print("[yellow]DEMO: these metrics are random. They are not historical performance.[/yellow]")
        console.print()

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            handle_api_error(console, e, "backtesting")
    finally:
        gamma_client.close()


def _display_equity_curve(console: Console, curve: list, start: float):
    """Display ASCII equity curve"""
    if len(curve) < 2:
        return

    min_val = min(curve)
    max_val = max(curve)
    range_val = max_val - min_val

    if range_val == 0:
        range_val = 1

    height = 8
    width = min(50, len(curve))

    # Sample curve to fit width
    step = len(curve) / width
    sampled = [curve[int(i * step)] for i in range(width)]

    # Build chart
    for row in range(height, -1, -1):
        line = ""
        threshold = min_val + (row / height) * range_val

        for val in sampled:
            if val >= threshold:
                if val >= start:
                    line += "[green]█[/green]"
                else:
                    line += "[red]█[/red]"
            else:
                line += " "

        # Y-axis label
        y_val = min_val + (row / height) * range_val
        console.print(f"  ${y_val:>8,.0f} |{line}")

    # X-axis
    console.print(f"           +{'-' * width}")
    console.print(f"           Start{'':>{width - 10}}End")
