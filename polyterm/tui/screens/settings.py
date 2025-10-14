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
    
    menu = Table.grid(padding=(0, 1))
    menu.add_column(style="cyan bold", justify="right", width=3)
    menu.add_column(style="white")
    
    menu.add_row("1", "Edit Alert Settings")
    menu.add_row("2", "Edit API Settings")
    menu.add_row("3", "Edit Display Settings")
    menu.add_row("4", "View Config File")
    menu.add_row("5", "Reset to Defaults")
    menu.add_row("6", "🔄 Update PolyTerm")
    
    console.print(menu)
    console.print()
    
    choice = console.input("[cyan]Select option (1-6):[/cyan] ").strip()
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
    
    elif choice == '6':
        # Update PolyTerm
        console.print("[bold green]🔄 Updating PolyTerm...[/bold green]")
        console.print()
        
        import subprocess
        import sys
        
        try:
            # Check current version
            console.print("[dim]Checking current version...[/dim]")
            result = subprocess.run([sys.executable, "-m", "pip", "show", "polyterm"], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('Version:'):
                        current_version = line.split(':')[1].strip()
                        console.print(f"[dim]Current version: {current_version}[/dim]")
                        break
            
            console.print()
            console.print("[green]Updating to latest version...[/green]")
            
            # Update using pipx if available, otherwise pip
            update_cmd = None
            try:
                subprocess.run(["pipx", "--version"], capture_output=True, check=True)
                update_cmd = ["pipx", "upgrade", "polyterm"]
                console.print("[dim]Using pipx to update...[/dim]")
            except (subprocess.CalledProcessError, FileNotFoundError):
                update_cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "polyterm"]
                console.print("[dim]Using pip to update...[/dim]")
            
            if update_cmd:
                result = subprocess.run(update_cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    console.print()
                    console.print("[bold green]✅ Update successful![/bold green]")
                    console.print("[green]PolyTerm has been updated to the latest version.[/green]")
                    console.print()
                    console.print("[yellow]Please restart PolyTerm to use the new version.[/yellow]")
                else:
                    console.print()
                    console.print("[bold red]❌ Update failed[/bold red]")
                    console.print(f"[red]Error: {result.stderr}[/red]")
                    console.print()
                    console.print("[yellow]You can try updating manually:[/yellow]")
                    console.print("[dim]  pipx upgrade polyterm[/dim]")
                    console.print("[dim]  or[/dim]")
                    console.print("[dim]  pip install --upgrade polyterm[/dim]")
            else:
                console.print("[red]Could not determine update method[/red]")
                
        except Exception as e:
            console.print()
            console.print("[bold red]❌ Update failed[/bold red]")
            console.print(f"[red]Error: {e}[/red]")
            console.print()
            console.print("[yellow]You can try updating manually:[/yellow]")
            console.print("[dim]  pipx upgrade polyterm[/dim]")
            console.print("[dim]  or[/dim]")
            console.print("[dim]  pip install --upgrade polyterm[/dim]")
    
    else:
        console.print("[red]Invalid option[/red]")
    
    console.print()
    console.input("[dim]Press Enter to continue...[/dim]")


