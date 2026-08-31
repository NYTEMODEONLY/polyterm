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
    if "config" not in ctx.obj:
        ctx.obj["config"] = _get_config_class()()

    if ctx.invoked_subcommand is None:
        from ..tui.controller import TUIController

        tui = TUIController()
        tui.run()


@click.command()
def update():
    """Reinstall PolyTerm from GitHub main. PyPI is decommissioned."""
    import sys

    import polyterm
    from rich.console import Console

    from ..utils.install_source import manual_reinstall_commands, reinstall_from_github

    console = Console()
    pipx_cmd, pip_cmd = manual_reinstall_commands()

    try:
        console.print("[bold green]🔄 Reinstalling from GitHub main...[/bold green]")
        console.print("[dim]GitHub is the source of truth. PyPI is decommissioned.[/dim]")

        current_version = polyterm.__version__
        console.print(f"[green]Current version:[/green] {current_version}")

        if not click.confirm("Reinstall PolyTerm from GitHub main now?"):
            console.print("[yellow]Update cancelled.[/yellow]")
            return

        success, method, error_text = reinstall_from_github(sys.executable)

        if success:
            console.print("[bold green]✅ Update successful![/bold green]")
            console.print(f"[green]Reinstalled from GitHub main via {method}[/green]")
            console.print()
            console.print("[bold yellow]🔄 Restart Required[/bold yellow]")
            console.print("[yellow]Please restart PolyTerm to use the new version.[/yellow]")
            return

        console.print("[bold red]❌ Update failed[/bold red]")
        if error_text:
            console.print(f"[red]Error: {error_text}[/red]")
        console.print("[yellow]Reinstall from GitHub main:[/yellow]")
        console.print(f"[yellow]  {pipx_cmd}[/yellow]")
        console.print(f"[yellow]  {pip_cmd}[/yellow]")

    except Exception as e:
        console.print(f"[bold red]❌ Update check failed: {e}[/bold red]")
        console.print(f"[yellow]Try running: {pipx_cmd}[/yellow]")

cli.add_command(update)


if __name__ == "__main__":
    cli()
