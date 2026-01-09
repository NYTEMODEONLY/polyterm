"""Main CLI entry point for PolyTerm"""

import click
from ..utils.config import Config


@click.group(invoke_without_command=True)
@click.version_option(version=__import__("polyterm").__version__)
@click.pass_context
def cli(ctx):
    """PolyTerm - Terminal-based monitoring for PolyMarket
    
    Track big moves, sudden shifts, and whale activity in prediction markets.
    """
    # Initialize config and pass to subcommands
    ctx.ensure_object(dict)
    ctx.obj["config"] = Config()
    
    # If no subcommand, launch TUI
    if ctx.invoked_subcommand is None:
        from ..tui.controller import TUIController
        tui = TUIController()
        tui.run()


# Import commands
from .commands import monitor, watch, whales, replay, portfolio, export_cmd, config_cmd, live_monitor

@click.command()
def update():
    """Check for and install updates"""
    import subprocess
    import sys
    import requests
    import polyterm
    from rich.console import Console
    
    console = Console()
    
    try:
        console.print("[bold green]🔄 Checking for updates...[/bold green]")
        
        # Get current version
        current_version = polyterm.__version__
        console.print(f"[green]Current version:[/green] {current_version}")
        
        # Check for updates
        response = requests.get("https://pypi.org/pypi/polyterm/json", timeout=10)
        if response.status_code == 200:
            data = response.json()
            latest_version = data["info"]["version"]
            
            if latest_version == current_version:
                console.print(f"[green]✅ You're already running the latest version ({current_version})![/green]")
                return
            
            console.print(f"[yellow]📦 Update available:[/yellow] {current_version} → {latest_version}")
            
            # Ask user if they want to update
            if click.confirm("Do you want to update now?"):
                # Check for pipx first (preferred)
                try:
                    subprocess.run(["pipx", "--version"], capture_output=True, check=True)
                    update_cmd = ["pipx", "upgrade", "polyterm"]
                    method = "pipx"
                except (subprocess.CalledProcessError, FileNotFoundError):
                    # Fallback to pip
                    update_cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "polyterm"]
                    method = "pip"
                
                console.print(f"[dim]Using {method} to update...[/dim]")
                
                # Run update
                result = subprocess.run(update_cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    console.print(f"[bold green]✅ Update successful![/bold green]")
                    console.print(f"[green]Updated to version {latest_version}[/green]")
                    console.print()
                    console.print("[bold yellow]🔄 Restart Required[/bold yellow]")
                    console.print("[yellow]Please restart PolyTerm to use the new version.[/yellow]")
                else:
                    console.print("[bold red]❌ Update failed[/bold red]")
                    if result.stderr:
                        console.print(f"[red]Error: {result.stderr}[/red]")
            else:
                console.print("[yellow]Update cancelled.[/yellow]")
        else:
            console.print("[yellow]⚠️  Could not check for updates online[/yellow]")
            
    except Exception as e:
        console.print(f"[bold red]❌ Update check failed: {e}[/bold red]")
        console.print("[yellow]Try running: pipx upgrade polyterm[/yellow]")

# Register commands
cli.add_command(monitor.monitor)
cli.add_command(watch.watch)
cli.add_command(whales.whales)
cli.add_command(replay.replay)
cli.add_command(portfolio.portfolio)
cli.add_command(export_cmd.export)
cli.add_command(config_cmd.config)
cli.add_command(live_monitor.live_monitor)
cli.add_command(update)


if __name__ == "__main__":
    cli()

