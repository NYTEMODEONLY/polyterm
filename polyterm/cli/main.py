"""Main CLI entry point for PolyTerm"""

import click
from ..utils.config import Config


@click.group(invoke_without_command=True)
@click.version_option(version="0.1.0")
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
from .commands import monitor, watch, whales, replay, portfolio, export_cmd, config_cmd

# Register commands
cli.add_command(monitor.monitor)
cli.add_command(watch.watch)
cli.add_command(whales.whales)
cli.add_command(replay.replay)
cli.add_command(portfolio.portfolio)
cli.add_command(export_cmd.export)
cli.add_command(config_cmd.config)


if __name__ == "__main__":
    cli()

