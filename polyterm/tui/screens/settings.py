"""Settings Screen - Configuration management"""

from rich.panel import Panel
from rich.console import Console as RichConsole
from rich.table import Table
from polyterm.utils.config import Config
import os


def settings_screen(console: RichConsole):
    """Settings and configuration
    
    Args:
        console: Rich Console instance
    """
    console.print(Panel("[bold]Settings[/bold]", style="cyan"))
    console.print()
    
    # Load current config
    config = Config()
    
    # Display current config
    console.print("[bold]Current Configuration:[/bold]")
    console.print()
    
    settings_table = Table(show_header=True, header_style="bold cyan")
    settings_table.add_column("Setting", style="cyan")
    settings_table.add_column("Value", style="white")
    
    settings_table.add_row("Config File", str(config.config_path))
    settings_table.add_row("Probability Threshold", f"{config.probability_threshold}%")
    settings_table.add_row("Volume Threshold", f"{config.volume_threshold}%")
    settings_table.add_row("Check Interval", f"{config.check_interval}s")
    settings_table.add_row("Refresh Rate", f"{config.get('display.refresh_rate', 2)}s")
    settings_table.add_row("Max Markets", f"{config.get('display.max_markets', 20)}")
    
    console.print(settings_table)
    console.print()
    
    # Settings menu
    console.print("[bold]What would you like to do?[/bold]")
    console.print()
    
    menu = Table.grid(padding=(0, 1))
    menu.add_column(style="cyan bold", justify="right", width=3)
    menu.add_column(style="white")
    
    menu.add_row("1", "Edit Alert Settings")
    menu.add_row("2", "Edit API Settings")
    menu.add_row("3", "Edit Display Settings")
    menu.add_row("4", "View Config File")
    menu.add_row("5", "Reset to Defaults")
    menu.add_row("6", "🔄 Update PolyTerm")
    menu.add_row("", "")
    menu.add_row("b", "Back - Return to main menu")

    console.print(menu)
    console.print()

    choice = console.input("[cyan]Select option (1-6, b):[/cyan] ").strip().lower()
    console.print()
    
    if choice == '1':
        # Edit Alert Settings
        threshold = console.input(f"Probability threshold % [cyan][current: {config.probability_threshold}][/cyan] ").strip()
        if threshold:
            console.print(f"[yellow]Probability threshold would be set to {threshold}%[/yellow]")
            console.print("[dim]Note: Config editing coming soon. Edit config.toml manually for now.[/dim]")
    
    elif choice == '2':
        # Edit API Settings
        api_key = console.input(f"Gamma API Key [cyan][current: {'***' if config.gamma_api_key else 'Not set'}][/cyan] ").strip()
        if api_key:
            console.print(f"[yellow]API key would be set[/yellow]")
            console.print("[dim]Prefer POLYTERM_GAMMA_API_KEY. config.toml is plaintext; save() sets mode 0600.[/dim]")
    
    elif choice == '3':
        # Edit Display Settings
        refresh = console.input(f"Refresh rate (seconds) [cyan][current: {config.get('display.refresh_rate', 2)}][/cyan] ").strip()
        if refresh:
            console.print(f"[yellow]Refresh rate would be set to {refresh}s[/yellow]")
            console.print("[dim]Note: Config editing coming soon. Edit config.toml manually for now.[/dim]")
    
    elif choice == '4':
        # View Config File
        console.print(f"[green]Config file location:[/green]")
        console.print(f"  {str(config.config_path)}")
        console.print()
        
        if os.path.exists(str(config.config_path)):
            console.print("[dim]Use 'cat' or your editor to view/edit:[/dim]")
            console.print(f"[dim]  cat {str(config.config_path)}[/dim]")
        else:
            console.print("[yellow]Config file not found (using defaults)[/yellow]")
    
    elif choice == '5':
        # Reset to Defaults
        confirm = console.input("[yellow]Reset all settings to defaults? (y/N):[/yellow] ").strip().lower()
        if confirm == 'y':
            console.print("[yellow]Settings would be reset to defaults[/yellow]")
            console.print("[dim]Note: Config reset coming soon. Delete config.toml manually for now.[/dim]")
        else:
            console.print("[dim]Reset cancelled[/dim]")
    
    elif choice == '6':
        # Update PolyTerm
        update_polyterm(console)
        return

    elif choice == 'b':
        return

    else:
        console.print("[red]Invalid option[/red]")

    console.print()
    console.input("[dim]Press Enter to continue...[/dim]")


def _print_manual_reinstall(console: RichConsole) -> None:
    """Show GitHub reinstall commands. Never the PyPI package name."""
    from polyterm.utils.install_source import manual_reinstall_commands

    pipx_cmd, pip_cmd = manual_reinstall_commands()
    console.print("[yellow]Reinstall from GitHub main:[/yellow]")
    console.print(f"[dim]  {pipx_cmd}[/dim]")
    console.print(f"[dim]  {pip_cmd}[/dim]")


def update_polyterm(console: RichConsole) -> bool:
    """Reinstall PolyTerm from GitHub main, then optionally restart.

    Returns:
        True if app should restart, False otherwise
    """

    console.print(Panel("[bold green]🔄 PolyTerm Update[/bold green]", style="green"))
    console.print()
    console.print("[dim]GitHub is the source of truth. PyPI is decommissioned.[/dim]")
    console.print("[dim]This reinstalls PolyTerm from GitHub main.[/dim]")
    console.print()

    import sys
    import polyterm
    from polyterm.utils.install_source import reinstall_from_github

    try:
        console.print("[cyan]Step 1:[/cyan] Checking current version...")
        current_version = polyterm.__version__
        console.print(f"[green]Current version:[/green] {current_version}")
        console.print()

        console.print("[cyan]Step 2:[/cyan] Reinstalling from GitHub main...")
        update_success, method, error_text = reinstall_from_github(sys.executable)

        if update_success:
            console.print()
            console.print("[bold green]✅ Update successful![/bold green]")
            console.print(f"[green]Reinstalled from GitHub main via {method}[/green]")
            console.print()

            console.print("[bold cyan]Would you like to restart PolyTerm now?[/bold cyan]")
            console.print("[dim]Restarting is required to use the new version.[/dim]")
            console.print()
            restart = console.input("[cyan]Restart now? (Y/n):[/cyan] ").strip().lower()

            if restart != 'n':
                console.print()
                console.print("[green]🔄 Restarting PolyTerm...[/green]")
                console.print()

                import shutil
                polyterm_path = shutil.which("polyterm")

                if polyterm_path:
                    os.execv(polyterm_path, ["polyterm"])
                else:
                    os.execv(sys.executable, [sys.executable, "-m", "polyterm"])

                return True
            else:
                console.print()
                console.print("[yellow]Update installed but not active.[/yellow]")
                console.print("[dim]Please restart PolyTerm manually to use the new version.[/dim]")
                console.print()
                console.input("[dim]Press Enter to return to menu...[/dim]")
                return False

        console.print()
        console.print("[bold red]❌ Update failed[/bold red]")
        if error_text:
            console.print(f"[red]{error_text}[/red]")
        console.print()
        _print_manual_reinstall(console)
        console.print()
        console.input("[dim]Press Enter to return to menu...[/dim]")
        return False

    except Exception as e:
        console.print()
        console.print("[bold red]❌ Update process failed[/bold red]")
        console.print(f"[red]Unexpected error: {e}[/red]")
        console.print()
        _print_manual_reinstall(console)
        console.print()
        console.input("[dim]Press Enter to return to menu...[/dim]")
        return False


