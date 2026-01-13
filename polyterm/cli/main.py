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
from .commands import arbitrage, predict, orderbook, wallets, alerts
from .commands import tutorial, glossary, simulate, risk, follow, parlay, bookmarks, dashboard, chart, size, compare, recent, pricealert, calendar, fees, stats, search, position, notes, presets, sentiment
from .commands import correlate, exit, depth, trade, timeline
from .commands import analytics, journal, hot, lookup, pnl
from .commands import alertcenter, groups, attribution, snapshot
from .commands import signals, similar, ladder, benchmark, pin
from .commands import spread, history, streak, digest, timing
from .commands import odds, health, scenario, summary, watchdog
from .commands import volume, screener, backtest, report, liquidity
from .commands import ev, calibrate, quick, leaderboard, notify

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
cli.add_command(arbitrage.arbitrage)
cli.add_command(predict.predict)
cli.add_command(orderbook.orderbook)
cli.add_command(wallets.wallets)
cli.add_command(alerts.alerts)
cli.add_command(tutorial.tutorial)
cli.add_command(glossary.glossary)
cli.add_command(simulate.simulate)
cli.add_command(risk.risk)
cli.add_command(follow.follow)
cli.add_command(parlay.parlay)
cli.add_command(bookmarks.bookmarks)
cli.add_command(dashboard.dashboard)
cli.add_command(chart.chart)
cli.add_command(size.size)
cli.add_command(compare.compare)
cli.add_command(recent.recent)
cli.add_command(pricealert.pricealert)
cli.add_command(calendar.calendar)
cli.add_command(fees.fees)
cli.add_command(stats.stats)
cli.add_command(search.search)
cli.add_command(position.position)
cli.add_command(notes.notes)
cli.add_command(presets.presets)
cli.add_command(sentiment.sentiment)
cli.add_command(correlate.correlate)
cli.add_command(exit.exit)
cli.add_command(depth.depth)
cli.add_command(trade.trade)
cli.add_command(timeline.timeline)
cli.add_command(analytics.analyze)
cli.add_command(journal.journal)
cli.add_command(hot.hot)
cli.add_command(lookup.lookup)
cli.add_command(pnl.pnl)
cli.add_command(alertcenter.center)
cli.add_command(groups.groups)
cli.add_command(attribution.attribution)
cli.add_command(snapshot.snapshot)
cli.add_command(signals.signals)
cli.add_command(similar.similar)
cli.add_command(ladder.ladder)
cli.add_command(benchmark.benchmark)
cli.add_command(pin.pin)
cli.add_command(spread.spread)
cli.add_command(history.history)
cli.add_command(streak.streak)
cli.add_command(digest.digest)
cli.add_command(timing.timing)
cli.add_command(odds.odds)
cli.add_command(health.health)
cli.add_command(scenario.scenario)
cli.add_command(summary.summary)
cli.add_command(watchdog.watchdog)
cli.add_command(volume.volume)
cli.add_command(screener.screener)
cli.add_command(backtest.backtest)
cli.add_command(report.report)
cli.add_command(liquidity.liquidity)
cli.add_command(ev.ev)
cli.add_command(calibrate.calibrate)
cli.add_command(quick.quick)
cli.add_command(leaderboard.leaderboard)
cli.add_command(notify.notify)


if __name__ == "__main__":
    cli()

