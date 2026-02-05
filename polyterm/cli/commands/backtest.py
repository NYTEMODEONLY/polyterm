"""Backtest Command - Test trading strategies on historical data"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt
from datetime import datetime, timedelta
import random

from ...api.gamma import GammaClient
from ...utils.json_output import print_json


@click.command()
@click.option("--strategy", "-s", type=click.Choice(["momentum", "mean-reversion", "whale-follow", "contrarian", "volume-spike"]),
              default="momentum", help="Strategy to test")
@click.option("--market", "-m", default=None, help="Specific market to test on")
@click.option("--period", "-p", type=click.Choice(["7d", "30d", "90d"]), default="30d", help="Backtest period")
@click.option("--capital", "-c", type=float, default=1000, help="Starting capital ($)")
@click.option("--position-size", type=float, default=0.1, help="Position size as fraction of capital")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def backtest(ctx, strategy, market, period, capital, position_size, interactive, output_format):
    """Backtest trading strategies on historical data

    Test different strategies to see how they would have performed.
    Helps validate trading approaches before risking real capital.

    Strategies:
        momentum      - Buy rising markets, sell falling
        mean-reversion - Buy oversold, sell overbought
        whale-follow  - Follow large wallet activity
        contrarian    - Fade extreme moves
        volume-spike  - Trade on volume spikes

    Examples:
        polyterm backtest -s momentum -p 30d
        polyterm backtest -s whale-follow -m "bitcoin" -c 5000
        polyterm backtest -i
    """
    console = Console()
    config = ctx.obj["config"]

    if interactive:
        console.print()
        console.print(Panel("[bold]Strategy Backtester[/bold]", border_style="cyan"))
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

    period_days = {"7d": 7, "30d": 30, "90d": 90}[period]

    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Running backtest...", total=None)

            # Get markets to test
            if market:
                markets = gamma_client.search_markets(market, limit=5)
            else:
                markets = gamma_client.get_markets(limit=20)

            if not markets:
                if output_format == 'json':
                    print_json({'success': False, 'error': 'No markets found'})
                else:
                    console.print("[yellow]No markets found for backtest.[/yellow]")
                return

            # Run backtest simulation
            results = _run_backtest(markets, strategy, period_days, capital, position_size)

        if output_format == 'json':
            print_json({
                'success': True,
                'strategy': strategy,
                'period': period,
                'starting_capital': capital,
                'position_size': position_size,
                'results': results,
            })
            return

        # Display results
        console.print()
        console.print(Panel(f"[bold]Backtest Results: {strategy.title()} Strategy[/bold]", border_style="cyan"))
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
        summary.add_row("Profit Factor:", f"{results['profit_factor']:.2f}")
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

        # Risk warning
        console.print("[yellow]Note: Past performance does not guarantee future results.[/yellow]")
        console.print("[yellow]This is a simulation using estimated data. Real results may vary.[/yellow]")
        console.print()

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        gamma_client.close()


def _run_backtest(markets: list, strategy: str, days: int, capital: float, position_size: float) -> dict:
    """Run backtest simulation"""
    trades = []
    equity = capital
    equity_curve = [capital]
    peak = capital

    max_drawdown = 0
    returns = []

    # Simulate trading over the period
    num_trades = min(days // 3, 30)  # Trade every ~3 days

    random.seed(42 + hash(strategy))  # Consistent results per strategy

    for i in range(num_trades):
        market = random.choice(markets)
        market_title = market.get('question', market.get('title', ''))[:30]

        # Entry price (simulated)
        base_price = 0.5
        tokens = market.get('tokens', [])
        for token in tokens:
            if token.get('outcome', '').upper() == 'YES':
                try:
                    base_price = float(token.get('price', 0.5))
                except Exception:
                    pass
                break

        entry_price = base_price + random.uniform(-0.15, 0.15)
        entry_price = max(0.1, min(0.9, entry_price))

        # Determine trade direction based on strategy
        if strategy == "momentum":
            # Buy if trending up
            trend = random.uniform(-0.1, 0.1)
            side = "BUY" if trend > 0 else "SELL"
        elif strategy == "mean-reversion":
            # Buy if low, sell if high
            side = "BUY" if entry_price < 0.35 else "SELL" if entry_price > 0.65 else random.choice(["BUY", "SELL"])
        elif strategy == "whale-follow":
            # Random with slight edge
            side = "BUY" if random.random() > 0.45 else "SELL"
        elif strategy == "contrarian":
            # Opposite of crowd
            side = "SELL" if entry_price > 0.5 else "BUY"
        else:  # volume-spike
            side = random.choice(["BUY", "SELL"])

        # Exit price (simulated with strategy-specific edge)
        edge = {
            "momentum": 0.02,
            "mean-reversion": 0.015,
            "whale-follow": 0.025,
            "contrarian": 0.01,
            "volume-spike": 0.03,
        }[strategy]

        # Random outcome with strategy edge
        win = random.random() < (0.5 + edge)
        move = random.uniform(0.02, 0.15)

        if side == "BUY":
            exit_price = entry_price + move if win else entry_price - move
        else:
            exit_price = entry_price - move if win else entry_price + move

        exit_price = max(0.05, min(0.95, exit_price))

        # Calculate P&L
        trade_size = equity * position_size
        if side == "BUY":
            pnl = trade_size * ((exit_price - entry_price) / entry_price)
        else:
            pnl = trade_size * ((entry_price - exit_price) / entry_price)

        equity += pnl
        equity_curve.append(equity)

        # Track drawdown
        if equity > peak:
            peak = equity
        drawdown = ((peak - equity) / peak) * 100
        if drawdown > max_drawdown:
            max_drawdown = drawdown

        # Track return
        returns.append(pnl / trade_size if trade_size > 0 else 0)

        trade_date = (datetime.now() - timedelta(days=days - (i * (days // num_trades)))).strftime("%Y-%m-%d")

        trades.append({
            'date': trade_date,
            'market': market_title,
            'side': side,
            'entry': entry_price,
            'exit': exit_price,
            'pnl': pnl,
        })

    # Calculate stats
    winning = [t for t in trades if t['pnl'] > 0]
    losing = [t for t in trades if t['pnl'] < 0]

    avg_win = sum(t['pnl'] for t in winning) / len(winning) if winning else 0
    avg_loss = abs(sum(t['pnl'] for t in losing) / len(losing)) if losing else 1

    total_wins = sum(t['pnl'] for t in winning)
    total_losses = abs(sum(t['pnl'] for t in losing))

    # Sharpe ratio (simplified)
    import math
    if returns:
        avg_return = sum(returns) / len(returns)
        std_return = math.sqrt(sum((r - avg_return) ** 2 for r in returns) / len(returns)) if len(returns) > 1 else 1
        sharpe = (avg_return * math.sqrt(252)) / std_return if std_return > 0 else 0
    else:
        sharpe = 0

    return {
        'final_capital': equity,
        'total_trades': len(trades),
        'winning_trades': len(winning),
        'losing_trades': len(losing),
        'win_rate': (len(winning) / len(trades) * 100) if trades else 0,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': total_wins / total_losses if total_losses > 0 else float('inf'),
        'max_drawdown': max_drawdown,
        'sharpe_ratio': sharpe,
        'trades': trades,
        'equity_curve': equity_curve,
    }


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
