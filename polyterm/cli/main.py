"""Main CLI entry point for PolyTerm."""

import click

from .lazy_group import LAZY_COMMANDS, LazyGroup


Config = None


def _get_config_class():
    global Config
    if Config is None:
        from ..utils.config import Config as config_class

        Config = config_class
    return Config


@click.group(invoke_without_command=True, cls=LazyGroup, lazy_commands=LAZY_COMMANDS)
@click.version_option(version=__import__("polyterm").__version__)
@click.pass_context
def cli(ctx):
    """PolyTerm - Terminal-based monitoring for PolyMarket

    Track big moves, sudden shifts, and whale activity in prediction markets.
    """
    ctx.ensure_object(dict)
    ctx.obj["config"] = _get_config_class()()

    if ctx.invoked_subcommand is None:
        from ..tui.controller import TUIController

        tui = TUIController()
        tui.run()


@click.command()
def update():
    """Check for and install updates."""
    import subprocess
    import sys

    import polyterm
    import requests
    from rich.console import Console

    console = Console()

    try:
        console.print("[bold green]🔄 Checking for updates...[/bold green]")

        current_version = polyterm.__version__
        console.print(f"[green]Current version:[/green] {current_version}")

        response = requests.get("https://pypi.org/pypi/polyterm/json", timeout=10)
        if response.status_code == 200:
            data = response.json()
            latest_version = data["info"]["version"]

            if latest_version == current_version:
                console.print(
                    f"[green]✅ You're already running the latest version ({current_version})![/green]"
                )
                return

            console.print(
                f"[yellow]📦 Update available:[/yellow] {current_version} → {latest_version}"
            )

            if click.confirm("Do you want to update now?"):
                try:
                    subprocess.run(["pipx", "--version"], capture_output=True, check=True)
                    update_cmd = ["pipx", "upgrade", "polyterm"]
                    method = "pipx"
                except (subprocess.CalledProcessError, FileNotFoundError):
                    update_cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "polyterm"]
                    method = "pip"

                console.print(f"[dim]Using {method} to update...[/dim]")

                result = subprocess.run(update_cmd, capture_output=True, text=True)

                if result.returncode == 0:
                    console.print("[bold green]✅ Update successful![/bold green]")
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

cli.add_command(update)


if __name__ == "__main__":
    cli()
