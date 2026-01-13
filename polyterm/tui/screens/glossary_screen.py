"""Glossary Screen - Prediction market terminology"""

import subprocess
import sys
from rich.console import Console as RichConsole
from rich.panel import Panel
from rich.prompt import Prompt


def glossary_screen(console: RichConsole):
    """Show prediction market glossary

    Args:
        console: Rich Console instance
    """
    console.print(Panel("[bold]Prediction Market Glossary[/bold]", style="cyan"))
    console.print()

    console.print("[cyan]Available options:[/cyan]")
    console.print("  [bold]1.[/bold] View all terms")
    console.print("  [bold]2.[/bold] Search for a term")
    console.print("  [bold]3.[/bold] Browse by category")
    console.print("  [bold]q.[/bold] Return to menu")
    console.print()

    choice = Prompt.ask("[cyan]Select option[/cyan]", choices=["1", "2", "3", "q"], default="1")

    if choice == "q":
        return

    try:
        if choice == "1":
            # Show all terms
            subprocess.run([sys.executable, "-m", "polyterm", "glossary"])
        elif choice == "2":
            # Search for term
            search_term = Prompt.ask("[cyan]Enter search term[/cyan]")
            if search_term:
                subprocess.run([sys.executable, "-m", "polyterm", "glossary", "--search", search_term])
        elif choice == "3":
            # Show categories first
            console.print()
            console.print("[bold]Categories:[/bold]")
            console.print("  Core Concepts, Trading, Analysis, Arbitrage, Platforms, Technical, Risk")
            console.print()
            category = Prompt.ask("[cyan]Enter category name[/cyan]")
            if category:
                subprocess.run([sys.executable, "-m", "polyterm", "glossary", "--category", category])

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("[dim]Try running: polyterm glossary[/dim]")
