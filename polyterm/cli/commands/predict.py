"""Predict command - AI-powered market predictions"""

import click
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ...api.gamma import GammaClient
from ...db.database import Database
from ...core.predictions import PredictionEngine, Direction
from ...utils.json_output import print_json


@click.command()
@click.option("--market", default=None, help="Specific market ID to predict")
@click.option("--limit", default=10, help="Number of markets to analyze")
@click.option("--horizon", default=24, help="Prediction horizon in hours")
@click.option("--min-confidence", default=0.5, help="Minimum confidence threshold")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table", help="Output format")
@click.pass_context
def predict(ctx, market, limit, horizon, min_confidence, output_format):
    """Generate AI-powered predictions for markets"""

    config = ctx.obj["config"]
    console = Console()

    # Initialize
    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )
    db = Database()
    engine = PredictionEngine(db)

    try:
        if output_format != 'json':
            console.print(f"[cyan]Generating predictions (horizon: {horizon}h)...[/cyan]\n")

        predictions = []

        if market:
            # Single market prediction
            markets_data = gamma_client.get_markets(limit=1, market_id=market)
            if markets_data:
                title = markets_data[0].get('title', market)
                pred = engine.generate_prediction(market, title, horizon)
                predictions.append(pred)
        else:
            # Top markets by volume
            markets_data = gamma_client.get_markets(limit=limit, active=True, closed=False)

            for m in markets_data:
                market_id = m.get('id', '')
                title = m.get('title', m.get('question', ''))

                if not market_id:
                    continue

                pred = engine.generate_prediction(market_id, title, horizon)

                if pred.confidence >= min_confidence:
                    predictions.append(pred)

        # Sort by confidence
        predictions.sort(key=lambda p: p.confidence, reverse=True)

        # JSON output
        if output_format == 'json':
            output = {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'horizon_hours': horizon,
                'count': len(predictions),
                'predictions': [p.to_dict() for p in predictions],
                'accuracy_stats': engine.get_accuracy_stats(),
            }
            print_json(output)
            return

        if not predictions:
            console.print("[yellow]No predictions generated above confidence threshold[/yellow]")
            return

        # Create table
        table = Table(title=f"Market Predictions ({horizon}h Horizon)")

        table.add_column("Market", style="cyan", max_width=35)
        table.add_column("Direction", justify="center")
        table.add_column("Expected", justify="right")
        table.add_column("Confidence", justify="right")
        table.add_column("Signals", justify="center")

        for pred in predictions[:limit]:
            # Direction with color
            if pred.direction == Direction.BULLISH:
                dir_display = "[green]+[/green]"
            elif pred.direction == Direction.BEARISH:
                dir_display = "[red]-[/red]"
            else:
                dir_display = "[dim]~[/dim]"

            # Confidence color
            conf_color = "green" if pred.confidence >= 0.7 else "yellow" if pred.confidence >= 0.5 else "dim"

            # Signal summary
            summary = pred.signal_summary
            signals_display = f"{summary['bullish']}+ {summary['bearish']}- {summary['neutral']}~"

            table.add_row(
                pred.market_title[:35],
                dir_display,
                f"{pred.probability_change:+.1f}%",
                f"[{conf_color}]{pred.confidence:.0%}[/{conf_color}]",
                signals_display,
            )

        console.print(table)

        # Show detailed view for top prediction
        if predictions:
            top = predictions[0]
            console.print(f"\n[bold]Top Prediction Details:[/bold]")
            console.print(Panel(engine.format_prediction(top), title=top.market_title[:50]))

        # Accuracy stats
        stats = engine.get_accuracy_stats()
        if stats['total_predictions'] > 0:
            console.print(f"\n[dim]Historical accuracy: {stats['accuracy']:.0%} ({stats['total_predictions']} predictions)[/dim]")

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        gamma_client.close()
