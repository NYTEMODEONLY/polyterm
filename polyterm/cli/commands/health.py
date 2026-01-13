"""Portfolio Health Check - Comprehensive portfolio health analysis"""

import click
from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ...db.database import Database
from ...utils.json_output import print_json


@click.command()
@click.option("--detailed", "-d", is_flag=True, help="Show detailed breakdown")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def health(ctx, detailed, output_format):
    """Check your portfolio health

    Get a comprehensive health score and recommendations.
    Analyzes diversification, risk exposure, and trading patterns.

    Examples:
        polyterm health              # Quick health check
        polyterm health --detailed   # Full analysis
    """
    console = Console()
    db = Database()

    # Get all positions
    open_positions = db.get_positions(status='open')
    closed_positions = db.get_positions(status='closed')

    # Calculate health metrics
    health_data = _calculate_health(open_positions, closed_positions)

    if output_format == 'json':
        print_json({
            'success': True,
            'overall_score': health_data['overall_score'],
            'grade': health_data['grade'],
            'metrics': health_data['metrics'],
            'issues': health_data['issues'],
            'recommendations': health_data['recommendations'],
        })
        return

    # Display
    console.print()
    console.print(Panel("[bold]Portfolio Health Check[/bold]", border_style="cyan"))
    console.print()

    # Overall score
    score = health_data['overall_score']
    grade = health_data['grade']

    if score >= 80:
        score_color = "green"
        grade_emoji = "🟢"
    elif score >= 60:
        score_color = "yellow"
        grade_emoji = "🟡"
    elif score >= 40:
        score_color = "yellow"
        grade_emoji = "🟠"
    else:
        score_color = "red"
        grade_emoji = "🔴"

    console.print(f"[bold]Overall Health:[/bold] {grade_emoji} [{score_color}]{score}/100 ({grade})[/{score_color}]")
    console.print()

    # Health bar
    filled = score // 5
    empty = 20 - filled
    bar = f"[{score_color}]{'█' * filled}{'░' * empty}[/{score_color}]"
    console.print(f"  {bar}")
    console.print()

    # Metric breakdown
    console.print("[bold]Health Metrics:[/bold]")
    console.print()

    metrics_table = Table(show_header=True, header_style="bold cyan", box=None)
    metrics_table.add_column("Metric", width=20)
    metrics_table.add_column("Score", width=10, justify="center")
    metrics_table.add_column("Status", width=12, justify="center")
    metrics_table.add_column("Details", width=25)

    for metric in health_data['metrics']:
        score_bar = _score_bar(metric['score'])

        if metric['score'] >= 70:
            status = f"[green]{metric['status']}[/green]"
        elif metric['score'] >= 40:
            status = f"[yellow]{metric['status']}[/yellow]"
        else:
            status = f"[red]{metric['status']}[/red]"

        metrics_table.add_row(
            metric['name'],
            score_bar,
            status,
            metric['details'],
        )

    console.print(metrics_table)
    console.print()

    # Issues
    if health_data['issues']:
        console.print("[bold red]Issues Found:[/bold red]")
        console.print()
        for issue in health_data['issues']:
            severity_icon = "🔴" if issue['severity'] == 'high' else "🟡" if issue['severity'] == 'medium' else "🔵"
            console.print(f"  {severity_icon} {issue['message']}")
        console.print()

    # Recommendations
    console.print("[bold]Recommendations:[/bold]")
    console.print()
    for rec in health_data['recommendations'][:5]:
        console.print(f"  [cyan]>[/cyan] {rec}")
    console.print()

    # Detailed breakdown
    if detailed:
        _display_detailed(console, health_data)


def _calculate_health(open_positions: list, closed_positions: list) -> dict:
    """Calculate portfolio health metrics"""
    metrics = []
    issues = []
    recommendations = []

    # 1. Diversification Score
    div_score, div_status, div_details, div_issues = _check_diversification(open_positions)
    metrics.append({
        'name': 'Diversification',
        'score': div_score,
        'status': div_status,
        'details': div_details,
    })
    issues.extend(div_issues)

    # 2. Position Sizing Score
    size_score, size_status, size_details, size_issues = _check_position_sizing(open_positions)
    metrics.append({
        'name': 'Position Sizing',
        'score': size_score,
        'status': size_status,
        'details': size_details,
    })
    issues.extend(size_issues)

    # 3. Win Rate Health
    wr_score, wr_status, wr_details, wr_issues = _check_win_rate(closed_positions)
    metrics.append({
        'name': 'Win Rate',
        'score': wr_score,
        'status': wr_status,
        'details': wr_details,
    })
    issues.extend(wr_issues)

    # 4. Risk Exposure
    risk_score, risk_status, risk_details, risk_issues = _check_risk_exposure(open_positions)
    metrics.append({
        'name': 'Risk Exposure',
        'score': risk_score,
        'status': risk_status,
        'details': risk_details,
    })
    issues.extend(risk_issues)

    # 5. Trading Activity
    activity_score, activity_status, activity_details, activity_issues = _check_activity(closed_positions)
    metrics.append({
        'name': 'Activity Level',
        'score': activity_score,
        'status': activity_status,
        'details': activity_details,
    })
    issues.extend(activity_issues)

    # Calculate overall score (weighted average)
    weights = [0.25, 0.20, 0.20, 0.20, 0.15]
    overall_score = sum(m['score'] * w for m, w in zip(metrics, weights))

    # Grade
    if overall_score >= 90:
        grade = 'Excellent'
    elif overall_score >= 80:
        grade = 'Good'
    elif overall_score >= 70:
        grade = 'Fair'
    elif overall_score >= 60:
        grade = 'Needs Work'
    elif overall_score >= 40:
        grade = 'Poor'
    else:
        grade = 'Critical'

    # Generate recommendations
    recommendations = _generate_recommendations(metrics, issues)

    return {
        'overall_score': int(overall_score),
        'grade': grade,
        'metrics': metrics,
        'issues': sorted(issues, key=lambda x: {'high': 0, 'medium': 1, 'low': 2}.get(x['severity'], 3)),
        'recommendations': recommendations,
        'open_positions': len(open_positions),
        'closed_positions': len(closed_positions),
    }


def _check_diversification(positions: list) -> tuple:
    """Check portfolio diversification"""
    if not positions:
        return 70, 'N/A', 'No open positions', []

    # Count unique markets
    markets = set()
    for pos in positions:
        markets.add(pos.get('market_id', ''))

    num_positions = len(positions)
    num_markets = len(markets)

    issues = []

    if num_positions == 1:
        score = 40
        status = 'Low'
        details = 'Only 1 position'
        issues.append({'severity': 'medium', 'message': 'Portfolio concentrated in single position'})
    elif num_positions <= 3:
        score = 60
        status = 'Fair'
        details = f'{num_positions} positions'
    elif num_positions <= 7:
        score = 80
        status = 'Good'
        details = f'{num_positions} positions'
    else:
        score = 90
        status = 'Excellent'
        details = f'{num_positions} positions'

    return score, status, details, issues


def _check_position_sizing(positions: list) -> tuple:
    """Check position sizing consistency"""
    if not positions:
        return 70, 'N/A', 'No open positions', []

    # Calculate position sizes
    sizes = []
    for pos in positions:
        entry = pos.get('entry_price', 0)
        shares = pos.get('shares', 0)
        size = entry * shares
        sizes.append(size)

    if not sizes:
        return 70, 'N/A', 'No size data', []

    avg_size = sum(sizes) / len(sizes)
    max_size = max(sizes)
    min_size = min(sizes)

    issues = []

    # Check for size consistency
    if max_size > avg_size * 3:
        score = 40
        status = 'Risky'
        details = f'Max position {max_size/avg_size:.1f}x avg'
        issues.append({'severity': 'high', 'message': f'One position is {max_size/avg_size:.1f}x larger than average'})
    elif max_size > avg_size * 2:
        score = 60
        status = 'Uneven'
        details = f'Some variance in sizing'
        issues.append({'severity': 'medium', 'message': 'Position sizes are inconsistent'})
    else:
        score = 85
        status = 'Good'
        details = f'Avg: ${avg_size:.0f}'

    return score, status, details, issues


def _check_win_rate(closed_positions: list) -> tuple:
    """Check historical win rate"""
    if not closed_positions:
        return 70, 'N/A', 'No trade history', []

    wins = 0
    losses = 0

    for pos in closed_positions:
        entry = pos.get('entry_price', 0)
        exit_price = pos.get('exit_price', 0)
        side = pos.get('side', 'yes')

        if side == 'yes':
            pnl = exit_price - entry
        else:
            pnl = entry - exit_price

        if pnl > 0:
            wins += 1
        elif pnl < 0:
            losses += 1

    total = wins + losses
    if total == 0:
        return 70, 'N/A', 'No completed trades', []

    win_rate = wins / total

    issues = []

    if win_rate >= 0.60:
        score = 90
        status = 'Excellent'
        details = f'{win_rate:.0%} win rate'
    elif win_rate >= 0.50:
        score = 75
        status = 'Good'
        details = f'{win_rate:.0%} win rate'
    elif win_rate >= 0.40:
        score = 55
        status = 'Fair'
        details = f'{win_rate:.0%} win rate'
        issues.append({'severity': 'medium', 'message': f'Win rate ({win_rate:.0%}) is below 50%'})
    else:
        score = 30
        status = 'Poor'
        details = f'{win_rate:.0%} win rate'
        issues.append({'severity': 'high', 'message': f'Low win rate ({win_rate:.0%}) - review strategy'})

    return score, status, details, issues


def _check_risk_exposure(positions: list) -> tuple:
    """Check overall risk exposure"""
    if not positions:
        return 80, 'N/A', 'No open positions', []

    total_exposure = 0
    high_risk_count = 0

    for pos in positions:
        entry = pos.get('entry_price', 0)
        shares = pos.get('shares', 0)
        side = pos.get('side', 'yes')

        # Calculate exposure
        if side == 'yes':
            exposure = entry * shares
            # High risk if buying at high prices
            if entry > 0.80:
                high_risk_count += 1
        else:
            exposure = (1 - entry) * shares
            if entry < 0.20:
                high_risk_count += 1

        total_exposure += exposure

    issues = []

    risk_ratio = high_risk_count / len(positions) if positions else 0

    if risk_ratio > 0.5:
        score = 40
        status = 'High Risk'
        details = f'{high_risk_count} high-risk positions'
        issues.append({'severity': 'high', 'message': f'{high_risk_count} positions at extreme prices'})
    elif risk_ratio > 0.25:
        score = 60
        status = 'Elevated'
        details = f'Some high-risk exposure'
        issues.append({'severity': 'medium', 'message': 'Consider reducing extreme price positions'})
    else:
        score = 85
        status = 'Balanced'
        details = f'${total_exposure:,.0f} total exposure'

    return score, status, details, issues


def _check_activity(closed_positions: list) -> tuple:
    """Check trading activity level"""
    if not closed_positions:
        return 50, 'Inactive', 'No trade history', []

    # Count recent trades
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    recent_week = 0
    recent_month = 0

    for pos in closed_positions:
        try:
            exit_date = datetime.fromisoformat(pos.get('exit_date', ''))
            if exit_date >= week_ago:
                recent_week += 1
            if exit_date >= month_ago:
                recent_month += 1
        except Exception:
            continue

    issues = []

    if recent_month == 0:
        score = 40
        status = 'Inactive'
        details = 'No trades in 30 days'
        issues.append({'severity': 'low', 'message': 'No recent trading activity'})
    elif recent_month < 5:
        score = 60
        status = 'Light'
        details = f'{recent_month} trades/month'
    elif recent_month < 20:
        score = 80
        status = 'Active'
        details = f'{recent_month} trades/month'
    else:
        score = 85
        status = 'Very Active'
        details = f'{recent_month} trades/month'

    return score, status, details, issues


def _generate_recommendations(metrics: list, issues: list) -> list:
    """Generate recommendations based on health metrics"""
    recommendations = []

    for metric in metrics:
        if metric['name'] == 'Diversification' and metric['score'] < 60:
            recommendations.append("Add more positions to diversify your portfolio")

        if metric['name'] == 'Position Sizing' and metric['score'] < 60:
            recommendations.append("Use consistent position sizing (1-5% of portfolio per trade)")

        if metric['name'] == 'Win Rate' and metric['score'] < 60:
            recommendations.append("Focus on higher-confidence trades to improve win rate")

        if metric['name'] == 'Risk Exposure' and metric['score'] < 60:
            recommendations.append("Reduce positions at extreme prices (>80% or <20%)")

        if metric['name'] == 'Activity Level' and metric['score'] < 60:
            recommendations.append("Stay active - regular trading helps maintain edge")

    # Add general recommendations
    if not recommendations:
        recommendations.append("Your portfolio is healthy - keep following your strategy")
        recommendations.append("Consider using polyterm benchmark to track progress")

    return recommendations


def _display_detailed(console: Console, health_data: dict):
    """Display detailed health breakdown"""
    console.print("[bold]Detailed Analysis:[/bold]")
    console.print()

    console.print(f"  Open Positions: {health_data['open_positions']}")
    console.print(f"  Closed Positions: {health_data['closed_positions']}")
    console.print()

    # Metric explanations
    console.print("[bold]Metric Explanations:[/bold]")
    console.print()
    console.print("  [cyan]Diversification[/cyan]: Number and variety of positions")
    console.print("  [cyan]Position Sizing[/cyan]: Consistency of trade sizes")
    console.print("  [cyan]Win Rate[/cyan]: Historical success rate")
    console.print("  [cyan]Risk Exposure[/cyan]: Positions at extreme prices")
    console.print("  [cyan]Activity Level[/cyan]: Recent trading frequency")
    console.print()


def _score_bar(score: int) -> str:
    """Create visual score bar"""
    filled = score // 10
    empty = 10 - filled

    if score >= 70:
        color = "green"
    elif score >= 40:
        color = "yellow"
    else:
        color = "red"

    return f"[{color}]{'█' * filled}{'░' * empty}[/{color}]"
