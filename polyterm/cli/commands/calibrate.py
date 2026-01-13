"""Probability Calibration Tracker - Track prediction accuracy"""

import click
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm

from ...db.database import Database
from ...api.gamma import GammaClient
from ...utils.json_output import print_json


@click.command()
@click.option("--add", "-a", is_flag=True, help="Add a new prediction")
@click.option("--resolve", "-r", is_flag=True, help="Resolve a prediction")
@click.option("--list", "-l", "list_preds", is_flag=True, help="List predictions")
@click.option("--stats", "-s", is_flag=True, help="Show calibration stats")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def calibrate(ctx, add, resolve, list_preds, stats, output_format):
    """Track your probability calibration

    Improve your forecasting by tracking how well-calibrated
    your probability estimates are. Good traders know their biases.

    A well-calibrated predictor has outcomes match probabilities:
    - 70% confident predictions should come true ~70% of the time
    - 90% confident predictions should come true ~90% of the time

    Examples:
        polyterm calibrate --add              # Log a new prediction
        polyterm calibrate --resolve          # Mark outcome
        polyterm calibrate --stats            # View calibration
        polyterm calibrate --list             # See all predictions
    """
    console = Console()
    db = Database()

    # Ensure predictions table exists
    _ensure_table(db)

    if add:
        _add_prediction(console, db, ctx.obj["config"])
    elif resolve:
        _resolve_prediction(console, db)
    elif list_preds:
        _list_predictions(console, db, output_format)
    elif stats:
        _show_calibration(console, db, output_format)
    else:
        # Default: show stats
        _show_calibration(console, db, output_format)


def _ensure_table(db: Database):
    """Ensure predictions table exists"""
    db.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            market_id TEXT,
            market_name TEXT NOT NULL,
            prediction TEXT NOT NULL,
            probability REAL NOT NULL,
            confidence TEXT,
            reasoning TEXT,
            outcome TEXT,
            created_at TEXT NOT NULL,
            resolved_at TEXT
        )
    """)


def _add_prediction(console: Console, db: Database, config):
    """Add a new prediction"""
    console.print()
    console.print(Panel("[bold]Log Prediction[/bold]", border_style="cyan"))
    console.print()

    # Get market
    market_search = Prompt.ask("[cyan]Market name or search[/cyan]")

    if not market_search:
        return

    # Try to find market
    gamma = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    try:
        markets = gamma.search_markets(market_search, limit=3)

        if markets:
            console.print()
            console.print("[cyan]Found markets:[/cyan]")
            for i, m in enumerate(markets, 1):
                title = m.get('question', m.get('title', ''))[:50]
                console.print(f"  {i}. {title}")

            choice = Prompt.ask("Select market (or press Enter for custom)", default="1")
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(markets):
                    market_name = markets[idx].get('question', markets[idx].get('title', ''))
                    market_id = markets[idx].get('id', '')
                else:
                    market_name = market_search
                    market_id = ''
            except ValueError:
                market_name = market_search
                market_id = ''
        else:
            market_name = market_search
            market_id = ''
    finally:
        gamma.close()

    console.print()

    # Get prediction
    prediction = Prompt.ask("[cyan]Your prediction (YES/NO)[/cyan]", choices=["YES", "NO", "yes", "no"])
    prediction = prediction.upper()

    # Get probability
    prob_str = Prompt.ask("[cyan]Your probability (e.g., 0.75 or 75%)[/cyan]")
    try:
        if '%' in prob_str:
            probability = float(prob_str.replace('%', '')) / 100
        else:
            probability = float(prob_str)
    except ValueError:
        console.print("[red]Invalid probability[/red]")
        return

    if probability < 0 or probability > 1:
        console.print("[red]Probability must be between 0 and 1[/red]")
        return

    # Get confidence bucket
    console.print()
    console.print("[cyan]Confidence level:[/cyan]")
    console.print("  1. Very Low (50-60%)")
    console.print("  2. Low (60-70%)")
    console.print("  3. Medium (70-80%)")
    console.print("  4. High (80-90%)")
    console.print("  5. Very High (90%+)")

    conf_choice = Prompt.ask("Select", default="3")
    conf_map = {"1": "very_low", "2": "low", "3": "medium", "4": "high", "5": "very_high"}
    confidence = conf_map.get(conf_choice, "medium")

    # Optional reasoning
    console.print()
    reasoning = Prompt.ask("[cyan]Brief reasoning (optional)[/cyan]", default="")

    # Save prediction
    db.execute("""
        INSERT INTO predictions (market_id, market_name, prediction, probability, confidence, reasoning, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (market_id, market_name, prediction, probability, confidence, reasoning, datetime.now().isoformat()))

    console.print()
    console.print("[green]Prediction logged![/green]")
    console.print(f"  Market: {market_name[:50]}")
    console.print(f"  Prediction: {prediction} at {probability:.0%}")
    console.print()


def _resolve_prediction(console: Console, db: Database):
    """Resolve a prediction with actual outcome"""
    console.print()
    console.print(Panel("[bold]Resolve Prediction[/bold]", border_style="cyan"))
    console.print()

    # Get unresolved predictions
    predictions = db.query("""
        SELECT id, market_name, prediction, probability, created_at
        FROM predictions
        WHERE outcome IS NULL
        ORDER BY created_at DESC
        LIMIT 20
    """)

    if not predictions:
        console.print("[yellow]No unresolved predictions found.[/yellow]")
        return

    console.print("[cyan]Unresolved predictions:[/cyan]")
    console.print()

    for i, pred in enumerate(predictions, 1):
        console.print(f"  {i}. {pred['market_name'][:40]}")
        console.print(f"     Predicted: {pred['prediction']} at {pred['probability']:.0%}")
        console.print()

    choice = Prompt.ask("[cyan]Select prediction to resolve[/cyan]")
    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(predictions):
            console.print("[red]Invalid selection[/red]")
            return
    except ValueError:
        console.print("[red]Invalid selection[/red]")
        return

    pred = predictions[idx]

    console.print()
    outcome = Prompt.ask("[cyan]Actual outcome (YES/NO)[/cyan]", choices=["YES", "NO", "yes", "no"])
    outcome = outcome.upper()

    # Update prediction
    db.execute("""
        UPDATE predictions
        SET outcome = ?, resolved_at = ?
        WHERE id = ?
    """, (outcome, datetime.now().isoformat(), pred['id']))

    # Check if correct
    correct = outcome == pred['prediction']

    console.print()
    if correct:
        console.print("[green]Correct prediction![/green]")
    else:
        console.print("[red]Incorrect prediction[/red]")

    console.print()


def _list_predictions(console: Console, db: Database, output_format: str):
    """List all predictions"""
    predictions = db.query("""
        SELECT id, market_name, prediction, probability, outcome, created_at, resolved_at
        FROM predictions
        ORDER BY created_at DESC
        LIMIT 50
    """)

    if output_format == 'json':
        print_json({'predictions': predictions})
        return

    console.print()
    console.print(Panel("[bold]Prediction History[/bold]", border_style="cyan"))
    console.print()

    if not predictions:
        console.print("[yellow]No predictions logged yet.[/yellow]")
        console.print("[dim]Use 'polyterm calibrate --add' to log your first prediction.[/dim]")
        return

    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("#", width=3)
    table.add_column("Market", width=35)
    table.add_column("Prediction", width=12, justify="center")
    table.add_column("Prob", width=6, justify="center")
    table.add_column("Outcome", width=10, justify="center")
    table.add_column("Result", width=10, justify="center")

    for i, pred in enumerate(predictions, 1):
        if pred['outcome']:
            correct = pred['outcome'] == pred['prediction']
            result = "[green]Correct[/green]" if correct else "[red]Wrong[/red]"
            outcome = pred['outcome']
        else:
            result = "[dim]Pending[/dim]"
            outcome = "-"

        table.add_row(
            str(i),
            pred['market_name'][:33],
            pred['prediction'],
            f"{pred['probability']:.0%}",
            outcome,
            result,
        )

    console.print(table)
    console.print()


def _show_calibration(console: Console, db: Database, output_format: str):
    """Show calibration statistics"""
    # Get resolved predictions
    predictions = db.query("""
        SELECT prediction, probability, outcome
        FROM predictions
        WHERE outcome IS NOT NULL
    """)

    if output_format == 'json':
        stats = _calculate_calibration(predictions)
        print_json(stats)
        return

    console.print()
    console.print(Panel("[bold]Calibration Analysis[/bold]", border_style="cyan"))
    console.print()

    if not predictions:
        console.print("[yellow]No resolved predictions to analyze.[/yellow]")
        console.print()
        console.print("[dim]Log predictions with 'polyterm calibrate --add'[/dim]")
        console.print("[dim]Then resolve them with 'polyterm calibrate --resolve'[/dim]")
        return

    stats = _calculate_calibration(predictions)

    # Overall stats
    console.print("[bold]Overall Performance:[/bold]")
    console.print()

    summary = Table(show_header=False, box=None)
    summary.add_column(style="cyan", width=25)
    summary.add_column(width=15)

    summary.add_row("Total Predictions:", str(stats['total']))
    summary.add_row("Correct:", f"[green]{stats['correct']}[/green]")
    summary.add_row("Incorrect:", f"[red]{stats['incorrect']}[/red]")
    summary.add_row("Accuracy:", f"{stats['accuracy']:.1%}")
    summary.add_row("Brier Score:", f"{stats['brier_score']:.3f}")

    console.print(summary)
    console.print()

    # Calibration by bucket
    console.print("[bold]Calibration by Confidence Level:[/bold]")
    console.print()

    cal_table = Table(show_header=True, header_style="bold cyan", box=None)
    cal_table.add_column("Confidence", width=15)
    cal_table.add_column("Predictions", width=12, justify="center")
    cal_table.add_column("Avg Prob", width=10, justify="center")
    cal_table.add_column("Actual", width=10, justify="center")
    cal_table.add_column("Calibration", width=15, justify="center")

    for bucket in stats['buckets']:
        if bucket['count'] > 0:
            diff = bucket['actual_rate'] - bucket['avg_prob']

            if abs(diff) < 0.05:
                cal_color = "green"
                cal_text = "Well Calibrated"
            elif abs(diff) < 0.10:
                cal_color = "yellow"
                cal_text = "Slightly Off"
            else:
                cal_color = "red"
                if diff > 0:
                    cal_text = "Underconfident"
                else:
                    cal_text = "Overconfident"

            cal_table.add_row(
                bucket['name'],
                str(bucket['count']),
                f"{bucket['avg_prob']:.0%}",
                f"{bucket['actual_rate']:.0%}",
                f"[{cal_color}]{cal_text}[/{cal_color}]",
            )

    console.print(cal_table)
    console.print()

    # Calibration chart (ASCII)
    console.print("[bold]Calibration Chart:[/bold]")
    console.print()
    console.print("[dim]  Perfect calibration = points on diagonal[/dim]")
    console.print()

    _draw_calibration_chart(console, stats['buckets'])

    console.print()

    # Interpretation
    console.print("[bold]Interpretation:[/bold]")
    console.print()

    brier = stats['brier_score']
    if brier < 0.1:
        console.print("  [green]Excellent calibration![/green] Your probability estimates are very accurate.")
    elif brier < 0.2:
        console.print("  [bright_green]Good calibration.[/bright_green] Room for improvement but solid overall.")
    elif brier < 0.3:
        console.print("  [yellow]Fair calibration.[/yellow] Consider adjusting your confidence levels.")
    else:
        console.print("  [red]Poor calibration.[/red] Your estimates may be overconfident or underconfident.")

    console.print()

    # Tips
    if stats['total'] < 20:
        console.print("[dim]Note: More predictions needed for reliable calibration.[/dim]")
        console.print("[dim]Aim for 50+ resolved predictions.[/dim]")

    console.print()


def _calculate_calibration(predictions: list) -> dict:
    """Calculate calibration statistics"""
    if not predictions:
        return {
            'total': 0,
            'correct': 0,
            'incorrect': 0,
            'accuracy': 0,
            'brier_score': 0,
            'buckets': [],
        }

    total = len(predictions)
    correct = 0
    brier_sum = 0

    # Buckets: 50-60%, 60-70%, 70-80%, 80-90%, 90-100%
    buckets = [
        {'name': '50-60%', 'min': 0.50, 'max': 0.60, 'count': 0, 'correct': 0, 'prob_sum': 0},
        {'name': '60-70%', 'min': 0.60, 'max': 0.70, 'count': 0, 'correct': 0, 'prob_sum': 0},
        {'name': '70-80%', 'min': 0.70, 'max': 0.80, 'count': 0, 'correct': 0, 'prob_sum': 0},
        {'name': '80-90%', 'min': 0.80, 'max': 0.90, 'count': 0, 'correct': 0, 'prob_sum': 0},
        {'name': '90-100%', 'min': 0.90, 'max': 1.00, 'count': 0, 'correct': 0, 'prob_sum': 0},
    ]

    for pred in predictions:
        prob = pred['probability']
        outcome = 1 if pred['outcome'] == pred['prediction'] else 0

        if outcome:
            correct += 1

        # Brier score component
        brier_sum += (prob - outcome) ** 2

        # Add to bucket
        for bucket in buckets:
            if bucket['min'] <= prob < bucket['max'] or (bucket['max'] == 1.0 and prob == 1.0):
                bucket['count'] += 1
                bucket['correct'] += outcome
                bucket['prob_sum'] += prob
                break

    # Calculate bucket statistics
    for bucket in buckets:
        if bucket['count'] > 0:
            bucket['avg_prob'] = bucket['prob_sum'] / bucket['count']
            bucket['actual_rate'] = bucket['correct'] / bucket['count']
        else:
            bucket['avg_prob'] = 0
            bucket['actual_rate'] = 0

    return {
        'total': total,
        'correct': correct,
        'incorrect': total - correct,
        'accuracy': correct / total if total > 0 else 0,
        'brier_score': brier_sum / total if total > 0 else 0,
        'buckets': buckets,
    }


def _draw_calibration_chart(console: Console, buckets: list):
    """Draw ASCII calibration chart"""
    height = 10
    width = 40

    # Create empty grid
    grid = [[' ' for _ in range(width)] for _ in range(height)]

    # Draw axes
    for y in range(height):
        grid[y][0] = '|'
    for x in range(width):
        grid[height - 1][x] = '-'
    grid[height - 1][0] = '+'

    # Draw diagonal (perfect calibration)
    for i in range(min(height, width)):
        x = int(i * width / height)
        y = height - 1 - i
        if 0 <= x < width and 0 <= y < height:
            grid[y][x] = '.'

    # Plot bucket points
    for bucket in buckets:
        if bucket['count'] > 0:
            x = int(bucket['avg_prob'] * (width - 2)) + 1
            y = height - 1 - int(bucket['actual_rate'] * (height - 1))

            if 0 <= x < width and 0 <= y < height:
                grid[y][x] = 'X'

    # Print grid
    console.print("  100% |" + "".join(grid[0]))
    for y in range(1, height - 1):
        pct = 100 - (y * 100 // (height - 1))
        console.print(f"  {pct:3}% |" + "".join(grid[y]))
    console.print("    0% +" + "-" * width)
    console.print("        0%              50%            100%")
    console.print("                Your Probability")
