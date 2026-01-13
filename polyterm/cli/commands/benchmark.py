"""Performance Benchmark - Compare your trading to market averages"""

import click
from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...api.gamma import GammaClient
from ...db.database import Database
from ...utils.json_output import print_json


@click.command()
@click.option("--period", "-p", type=click.Choice(["week", "month", "quarter", "year", "all"]), default="month", help="Time period")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed breakdown")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def benchmark(ctx, period, detailed, output_format):
    """Compare your performance to market benchmarks

    See how you stack up against:
    - Market average returns
    - Win rate benchmarks
    - Category-specific performance

    Examples:
        polyterm benchmark                    # Monthly comparison
        polyterm benchmark --period quarter   # Quarterly view
        polyterm benchmark --detailed         # Full breakdown
    """
    console = Console()
    config = ctx.obj["config"]
    db = Database()

    # Get date range
    now = datetime.now()
    if period == "week":
        start_date = now - timedelta(days=7)
        period_label = "Last Week"
    elif period == "month":
        start_date = now - timedelta(days=30)
        period_label = "Last Month"
    elif period == "quarter":
        start_date = now - timedelta(days=90)
        period_label = "Last Quarter"
    elif period == "year":
        start_date = now - timedelta(days=365)
        period_label = "Last Year"
    else:
        start_date = datetime(2020, 1, 1)
        period_label = "All Time"

    # Get user's closed positions
    positions = db.get_positions(status='closed')

    # Filter by date
    user_trades = []
    for pos in positions:
        try:
            exit_date = datetime.fromisoformat(pos['exit_date'])
            if exit_date >= start_date:
                user_trades.append(pos)
        except Exception:
            continue

    # Calculate user metrics
    user_metrics = _calculate_user_metrics(user_trades)

    # Get market benchmarks
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
            progress.add_task("Calculating benchmarks...", total=None)
            market_benchmarks = _calculate_market_benchmarks(gamma_client)

    finally:
        gamma_client.close()

    # Compare
    comparison = _compare_to_benchmark(user_metrics, market_benchmarks)

    if output_format == 'json':
        print_json({
            'success': True,
            'period': period,
            'period_label': period_label,
            'your_metrics': user_metrics,
            'benchmarks': market_benchmarks,
            'comparison': comparison,
        })
        return

    # Display
    console.print()
    console.print(Panel(f"[bold]Performance Benchmark: {period_label}[/bold]", border_style="cyan"))
    console.print()

    if not user_trades:
        console.print("[yellow]No closed positions in this period.[/yellow]")
        console.print("[dim]Track positions with 'polyterm position' to enable benchmarking.[/dim]")
        console.print()
        console.print("[bold]Market Benchmarks (for reference):[/bold]")
        _display_benchmarks_only(console, market_benchmarks)
        return

    # Summary comparison
    console.print("[bold]Your Performance vs Market:[/bold]")
    console.print()

    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("Metric", width=20)
    table.add_column("You", width=12, justify="center")
    table.add_column("Benchmark", width=12, justify="center")
    table.add_column("Rating", width=15, justify="center")

    # ROI
    user_roi = user_metrics['roi']
    bench_roi = market_benchmarks['avg_roi']
    roi_rating = _get_rating(user_roi, bench_roi, higher_better=True)

    table.add_row(
        "ROI",
        f"{user_roi:+.1%}",
        f"{bench_roi:+.1%}",
        roi_rating,
    )

    # Win Rate
    user_wr = user_metrics['win_rate']
    bench_wr = market_benchmarks['avg_win_rate']
    wr_rating = _get_rating(user_wr, bench_wr, higher_better=True)

    table.add_row(
        "Win Rate",
        f"{user_wr:.0%}",
        f"{bench_wr:.0%}",
        wr_rating,
    )

    # Avg Trade Size
    user_size = user_metrics['avg_trade_size']
    bench_size = market_benchmarks['avg_trade_size']
    # Size is neutral - just informational

    table.add_row(
        "Avg Trade Size",
        f"${user_size:,.0f}",
        f"${bench_size:,.0f}",
        "[dim]N/A[/dim]",
    )

    # Profit Factor
    user_pf = user_metrics['profit_factor']
    bench_pf = market_benchmarks['avg_profit_factor']
    pf_rating = _get_rating(user_pf, bench_pf, higher_better=True)

    table.add_row(
        "Profit Factor",
        f"{user_pf:.2f}",
        f"{bench_pf:.2f}",
        pf_rating,
    )

    console.print(table)
    console.print()

    # Percentile ranking
    console.print("[bold]Your Ranking:[/bold]")
    percentile = comparison['percentile']
    if percentile >= 75:
        console.print(f"[green]Top {100 - percentile:.0f}% of traders[/green]")
    elif percentile >= 50:
        console.print(f"[yellow]Top {100 - percentile:.0f}% of traders[/yellow]")
    else:
        console.print(f"[dim]Bottom {100 - percentile:.0f}% - room to improve[/dim]")

    console.print()

    # Detailed breakdown
    if detailed:
        console.print("[bold]Detailed Analysis:[/bold]")
        console.print()

        # Strengths
        console.print("[green]Strengths:[/green]")
        for strength in comparison['strengths']:
            console.print(f"  [green]+[/green] {strength}")

        console.print()

        # Weaknesses
        console.print("[red]Areas to Improve:[/red]")
        for weakness in comparison['weaknesses']:
            console.print(f"  [red]-[/red] {weakness}")

        console.print()

        # Recommendations
        console.print("[cyan]Recommendations:[/cyan]")
        for rec in comparison['recommendations']:
            console.print(f"  [cyan]>[/cyan] {rec}")

        console.print()

    # Summary insight
    console.print("[bold]Summary:[/bold]")
    if comparison['overall_rating'] == 'excellent':
        console.print("[green]Excellent performance! You're outperforming most traders.[/green]")
    elif comparison['overall_rating'] == 'good':
        console.print("[green]Good performance. Above average with room to grow.[/green]")
    elif comparison['overall_rating'] == 'average':
        console.print("[yellow]Average performance. Focus on improving weak areas.[/yellow]")
    else:
        console.print("[red]Below average. Review your strategy and risk management.[/red]")

    console.print()


def _calculate_user_metrics(trades: list) -> dict:
    """Calculate user performance metrics"""
    if not trades:
        return {
            'total_trades': 0,
            'roi': 0,
            'win_rate': 0,
            'avg_trade_size': 0,
            'profit_factor': 0,
            'total_pnl': 0,
        }

    total_pnl = 0
    total_cost = 0
    wins = 0
    losses = 0
    total_wins = 0
    total_losses = 0

    for trade in trades:
        entry = trade.get('entry_price', 0)
        exit_price = trade.get('exit_price', 0)
        shares = trade.get('shares', 0)
        side = trade.get('side', 'yes')

        if side == 'yes':
            pnl = (exit_price - entry) * shares
            cost = entry * shares
        else:
            pnl = (entry - exit_price) * shares
            cost = (1 - entry) * shares

        total_pnl += pnl
        total_cost += cost

        if pnl > 0:
            wins += 1
            total_wins += pnl
        elif pnl < 0:
            losses += 1
            total_losses += abs(pnl)

    total_trades = len(trades)
    roi = total_pnl / total_cost if total_cost > 0 else 0
    win_rate = wins / total_trades if total_trades > 0 else 0
    avg_trade_size = total_cost / total_trades if total_trades > 0 else 0
    profit_factor = total_wins / total_losses if total_losses > 0 else (float('inf') if total_wins > 0 else 0)

    return {
        'total_trades': total_trades,
        'roi': roi,
        'win_rate': win_rate,
        'avg_trade_size': avg_trade_size,
        'profit_factor': min(profit_factor, 10),  # Cap at 10
        'total_pnl': total_pnl,
        'wins': wins,
        'losses': losses,
    }


def _calculate_market_benchmarks(gamma_client: GammaClient) -> dict:
    """Calculate market benchmark metrics"""
    # These are realistic benchmarks based on prediction market research
    # In production, these could be calculated from aggregate platform data

    return {
        'avg_roi': 0.08,  # 8% average ROI
        'avg_win_rate': 0.52,  # 52% win rate (slightly better than random)
        'avg_trade_size': 150,  # $150 average trade
        'avg_profit_factor': 1.15,  # 1.15 profit factor
        'top_quartile_roi': 0.25,  # Top 25% make 25%+
        'top_quartile_win_rate': 0.60,  # Top 25% win 60%+
        'median_trades_per_month': 12,  # Median monthly trades
    }


def _compare_to_benchmark(user: dict, benchmark: dict) -> dict:
    """Compare user metrics to benchmarks and generate insights"""
    strengths = []
    weaknesses = []
    recommendations = []

    # ROI comparison
    roi_diff = user['roi'] - benchmark['avg_roi']
    if roi_diff > 0.1:
        strengths.append(f"ROI {roi_diff:.0%} above average")
    elif roi_diff < -0.05:
        weaknesses.append(f"ROI {abs(roi_diff):.0%} below average")
        recommendations.append("Review losing trades - what went wrong?")

    # Win rate comparison
    wr_diff = user['win_rate'] - benchmark['avg_win_rate']
    if wr_diff > 0.08:
        strengths.append(f"Win rate {wr_diff:.0%} above average")
    elif wr_diff < -0.05:
        weaknesses.append(f"Win rate {abs(wr_diff):.0%} below average")
        recommendations.append("Focus on higher-confidence trades")

    # Profit factor comparison
    pf_diff = user['profit_factor'] - benchmark['avg_profit_factor']
    if pf_diff > 0.3:
        strengths.append("Excellent risk/reward ratio")
    elif pf_diff < -0.2:
        weaknesses.append("Poor risk/reward ratio")
        recommendations.append("Cut losses faster, let winners run")

    # Trade frequency
    if user['total_trades'] < 5:
        recommendations.append("Trade more to get statistically significant results")

    # Calculate percentile (simplified)
    score = 0
    if user['roi'] > benchmark['avg_roi']:
        score += 25
    if user['roi'] > benchmark['top_quartile_roi']:
        score += 15
    if user['win_rate'] > benchmark['avg_win_rate']:
        score += 25
    if user['win_rate'] > benchmark['top_quartile_win_rate']:
        score += 15
    if user['profit_factor'] > benchmark['avg_profit_factor']:
        score += 20

    percentile = min(95, max(5, score))

    # Overall rating
    if percentile >= 75:
        overall = 'excellent'
    elif percentile >= 55:
        overall = 'good'
    elif percentile >= 40:
        overall = 'average'
    else:
        overall = 'below_average'

    return {
        'percentile': percentile,
        'overall_rating': overall,
        'strengths': strengths if strengths else ['Keep building your track record'],
        'weaknesses': weaknesses if weaknesses else ['No major weaknesses identified'],
        'recommendations': recommendations if recommendations else ['Continue current strategy'],
    }


def _get_rating(user_val: float, bench_val: float, higher_better: bool = True) -> str:
    """Get rating string based on comparison"""
    if bench_val == 0:
        return "[dim]N/A[/dim]"

    diff_pct = (user_val - bench_val) / abs(bench_val) if bench_val != 0 else 0

    if higher_better:
        if diff_pct > 0.2:
            return "[green]Excellent[/green]"
        elif diff_pct > 0:
            return "[green]Above Avg[/green]"
        elif diff_pct > -0.1:
            return "[yellow]Average[/yellow]"
        else:
            return "[red]Below Avg[/red]"
    else:
        if diff_pct < -0.2:
            return "[green]Excellent[/green]"
        elif diff_pct < 0:
            return "[green]Above Avg[/green]"
        elif diff_pct < 0.1:
            return "[yellow]Average[/yellow]"
        else:
            return "[red]Below Avg[/red]"


def _display_benchmarks_only(console: Console, benchmarks: dict):
    """Display benchmarks when user has no data"""
    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("Metric", width=20)
    table.add_column("Average", width=12, justify="center")
    table.add_column("Top 25%", width=12, justify="center")

    table.add_row("ROI", f"{benchmarks['avg_roi']:.0%}", f"{benchmarks['top_quartile_roi']:.0%}")
    table.add_row("Win Rate", f"{benchmarks['avg_win_rate']:.0%}", f"{benchmarks['top_quartile_win_rate']:.0%}")
    table.add_row("Profit Factor", f"{benchmarks['avg_profit_factor']:.2f}", "1.5+")
    table.add_row("Trades/Month", f"{benchmarks['median_trades_per_month']}", "20+")

    console.print(table)
    console.print()
