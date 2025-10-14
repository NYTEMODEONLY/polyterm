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
    
    settings_table.add_row("Config File", config.config_path)
    settings_table.add_row("Alert Threshold", f"{config.alert_threshold}%")
    settings_table.add_row("Refresh Rate", f"{config.refresh_rate}s")
    settings_table.add_row("Min Volume", f"${config.min_volume:,}")
    settings_table.add_row("API Rate Limit", f"{config.rate_limit_calls}/{config.rate_limit_period}s")
    
    console.print(settings_table)
    console.print()
    
    # Settings menu
    console.print("[bold]What would you like to do?[/bold]")
    console.print()
    
    menu = Table.grid(padding=(0, 2))
    menu.add_column(style="cyan bold", justify="right", width=3)
    menu.add_column(style="white")
    
    menu.add_row("1", "Edit Alert Settings")
    menu.add_row("2", "Edit API Settings")
    menu.add_row("3", "Edit Display Settings")
    menu.add_row("4", "View Config File")
    menu.add_row("5", "Reset to Defaults")
    
    console.print(menu)
    console.print()
    
    choice = console.input("[cyan]Select option (1-5):[/cyan] ").strip()
    console.print()
    
    if choice == '1':
        # Edit Alert Settings
        threshold = console.input(f"Alert threshold % [cyan][current: {config.alert_threshold}][/cyan] ").strip()
        if threshold:
            console.print(f"[yellow]Alert threshold would be set to {threshold}%[/yellow]")
            console.print("[dim]Note: Config editing coming soon. Edit config.toml manually for now.[/dim]")
    
    elif choice == '2':
        # Edit API Settings
        rate_limit = console.input(f"Rate limit (calls/period) [cyan][current: {config.rate_limit_calls}/{config.rate_limit_period}s][/cyan] ").strip()
        if rate_limit:
            console.print(f"[yellow]Rate limit would be set to {rate_limit}[/yellow]")
            console.print("[dim]Note: Config editing coming soon. Edit config.toml manually for now.[/dim]")
    
    elif choice == '3':
        # Edit Display Settings
        refresh = console.input(f"Refresh rate (seconds) [cyan][current: {config.refresh_rate}][/cyan] ").strip()
        if refresh:
            console.print(f"[yellow]Refresh rate would be set to {refresh}s[/yellow]")
            console.print("[dim]Note: Config editing coming soon. Edit config.toml manually for now.[/dim]")
    
    elif choice == '4':
        # View Config File
        console.print(f"[green]Config file location:[/green]")
        console.print(f"  {config.config_path}")
        console.print()
        
        if os.path.exists(config.config_path):
            console.print("[dim]Use 'cat' or your editor to view/edit:[/dim]")
            console.print(f"[dim]  cat {config.config_path}[/dim]")
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
    
    else:
        console.print("[red]Invalid option[/red]")


