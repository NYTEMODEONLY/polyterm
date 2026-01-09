"""Export Screen - Data export wizard"""

from rich.panel import Panel
from rich.console import Console as RichConsole
from rich.progress import Progress
import subprocess
import sys
import os


def export_screen(console: RichConsole):
    """Data export wizard

    Args:
        console: Rich Console instance
    """
    console.print(Panel("[bold]Data Export[/bold]", style="cyan"))
    console.print()

    console.print("[dim]Export market data to file:[/dim]")
    console.print()

    # Guided export flow
    market = console.input("Market ID or search term: ").strip()

    if not market:
        console.print("[red]No market specified[/red]")
        return

    format_choice = console.input("Format? [cyan]json/csv[/cyan] [default: json] ").strip().lower() or "json"

    if format_choice not in ['json', 'csv']:
        console.print(f"[yellow]Unknown format '{format_choice}', using json[/yellow]")
        format_choice = "json"

    default_output = f"export.{format_choice}"
    output_file = console.input(f"Output file: [cyan][default: {default_output}][/cyan] ").strip() or default_output

    # Get the absolute path for display
    full_path = os.path.abspath(output_file)

    console.print()
    console.print(f"[green]Exporting to {output_file}...[/green]")
    console.print()

    # Build command
    cmd = [
        sys.executable, "-m", "polyterm.cli.main", "export",
        "--market", market,
        "--format", format_choice,
        "--output", output_file,
    ]

    # Launch export command with progress
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            console.print(f"[green]Successfully exported![/green]")
            console.print(f"[cyan]Saved to:[/cyan] {full_path}")
        else:
            console.print(f"[red]Export failed: {result.stderr}[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


