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
    
    console.print(menu)
    console.print()
    
    choice = console.input("[cyan]Select option (1-6):[/cyan] ").strip()
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
            console.print("[dim]Note: Config editing coming soon. Edit config.toml manually for now.[/dim]")
    
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
    
    else:
        console.print("[red]Invalid option[/red]")
    
    console.print()
    console.input("[dim]Press Enter to continue...[/dim]")


def update_polyterm(console: RichConsole):
    """Enhanced PolyTerm update function with automatic detection and user-friendly interface"""
    
    console.print(Panel("[bold green]🔄 PolyTerm Update[/bold green]", style="green"))
    console.print()
    console.print("[dim]This will automatically update PolyTerm to the latest version.[/dim]")
    console.print()
    
    import subprocess
    import sys
    import requests
    import polyterm
    
    try:
        # Step 1: Check current version
        console.print("[cyan]Step 1:[/cyan] Checking current version...")
        # Force fresh import to avoid caching issues
        import importlib
        importlib.reload(polyterm)
        current_version = polyterm.__version__
        console.print(f"[green]Current version:[/green] {current_version}")
        console.print()
        
        # Step 2: Check for updates
        console.print("[cyan]Step 2:[/cyan] Checking for updates...")
        try:
            response = requests.get("https://pypi.org/pypi/polyterm/json", timeout=10)
            if response.status_code == 200:
                data = response.json()
                latest_version = data["info"]["version"]
                
                if latest_version == current_version:
                    console.print(f"[green]✅ You're already running the latest version ({current_version})![/green]")
                    console.print()
                    console.print("[dim]No update needed.[/dim]")
                    return
                else:
                    console.print(f"[yellow]📦 Update available:[/yellow] {current_version} → {latest_version}")
                    console.print()
            else:
                console.print("[yellow]⚠️  Could not check for updates online[/yellow]")
                console.print("[dim]Proceeding with update attempt...[/dim]")
                console.print()
        except Exception as e:
            console.print(f"[yellow]⚠️  Could not check online: {e}[/yellow]")
            console.print("[dim]Proceeding with update attempt...[/dim]")
            console.print()
        
        # Step 3: Determine update method
        console.print("[cyan]Step 3:[/cyan] Determining update method...")
        
        update_methods = []
        
        # Check for pipx
        try:
            subprocess.run(["pipx", "--version"], capture_output=True, check=True)
            update_methods.append(("pipx", ["pipx", "upgrade", "polyterm"]))
            console.print("[green]✓[/green] pipx available")
        except (subprocess.CalledProcessError, FileNotFoundError):
            console.print("[dim]✗[/dim] pipx not available")
        
        # Check for pip
        try:
            subprocess.run([sys.executable, "-m", "pip", "--version"], capture_output=True, check=True)
            update_methods.append(("pip", [sys.executable, "-m", "pip", "install", "--upgrade", "polyterm"]))
            console.print("[green]✓[/green] pip available")
        except (subprocess.CalledProcessError, FileNotFoundError):
            console.print("[dim]✗[/dim] pip not available")
        
        if not update_methods:
            console.print()
            console.print("[bold red]❌ No update method available[/bold red]")
            console.print("[red]Neither pipx nor pip could be found.[/red]")
            console.print()
            console.print("[yellow]📋 Manual Update Instructions:[/yellow]")
            console.print()
            console.print("[dim]1. Open a new terminal window[/dim]")
            console.print("[dim]2. Run one of these commands:[/dim]")
            console.print("[dim]   • pipx upgrade polyterm[/dim]")
            console.print("[dim]   • pip install --upgrade polyterm[/dim]")
            console.print("[dim]3. Restart PolyTerm[/dim]")
            console.print()
            console.print("[yellow]💡 Need help? Visit: https://github.com/NYTEMODEONLY/polyterm[/yellow]")
            return
        
        # Step 4: Perform update
        console.print()
        console.print("[cyan]Step 4:[/cyan] Updating PolyTerm...")
        
        # Use pipx if available (preferred), otherwise pip
        method_name, update_cmd = update_methods[0]
        console.print(f"[green]Using {method_name} to update...[/green]")
        
        # Show progress
        console.print("[dim]Running update command...[/dim]")
        
        result = subprocess.run(update_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            console.print()
            console.print("[bold green]✅ Update successful![/bold green]")
            console.print()
            
            # Check new version
            try:
                # Import the updated version
                import importlib
                importlib.reload(polyterm)
                new_version = polyterm.__version__
                
                if new_version != current_version:
                    console.print(f"[green]🎉 Updated from {current_version} to {new_version}![/green]")
                else:
                    console.print("[green]✅ Update completed successfully![/green]")
                
                console.print()
                console.print("[bold green]🎉 Update Complete![/bold green]")
                console.print()
                console.print("[bold yellow]🔄 Next Steps:[/bold yellow]")
                console.print("[yellow]1. Close this PolyTerm window[/yellow]")
                console.print("[yellow]2. Open a new terminal[/yellow]")
                console.print("[yellow]3. Run: polyterm[/yellow]")
                console.print()
                console.print("[green]✨ New features and improvements are now available![/green]")
                console.print()
                console.print("[dim]Press Enter to continue (you can still use current session)[/dim]")
                
            except Exception as e:
                console.print("[green]✅ Update completed![/green]")
                console.print(f"[yellow]Note: Could not verify new version: {e}[/yellow]")
                console.print()
                console.print("[yellow]Please restart PolyTerm to use the updated version.[/yellow]")
        
        else:
            console.print()
            console.print("[bold red]❌ Update failed[/bold red]")
            console.print()
            
            if result.stderr:
                console.print("[red]Error details:[/red]")
                console.print(f"[red]{result.stderr}[/red]")
                console.print()
            
            # Try alternative method if available
            if len(update_methods) > 1:
                console.print("[yellow]Trying alternative update method...[/yellow]")
                alt_method_name, alt_update_cmd = update_methods[1]
                console.print(f"[dim]Using {alt_method_name}...[/dim]")
                
                alt_result = subprocess.run(alt_update_cmd, capture_output=True, text=True)
                
                if alt_result.returncode == 0:
                    console.print()
                    console.print("[bold green]✅ Update successful with alternative method![/bold green]")
                    console.print("[yellow]Please restart PolyTerm to use the new version.[/yellow]")
                else:
                    console.print()
                    console.print("[bold red]❌ Alternative method also failed[/bold red]")
                    console.print("[red]Manual update required.[/red]")
                    console.print()
                    console.print("[yellow]Try running one of these commands manually:[/yellow]")
                    for method_name, cmd in update_methods:
                        console.print(f"[dim]  {' '.join(cmd)}[/dim]")
            else:
                console.print("[yellow]Manual update required.[/yellow]")
                console.print()
                console.print("[yellow]Try running this command manually:[/yellow]")
                console.print(f"[dim]  {' '.join(update_cmd)}[/dim]")
    
    except Exception as e:
        console.print()
        console.print("[bold red]❌ Update process failed[/bold red]")
        console.print(f"[red]Unexpected error: {e}[/red]")
        console.print()
        console.print("[yellow]Please try updating manually:[/yellow]")
        console.print("[dim]  pipx upgrade polyterm[/dim]")
        console.print("[dim]  or[/dim]")
        console.print("[dim]  pip install --upgrade polyterm[/dim]")
    
    console.print()
    console.input("[dim]Press Enter to continue...[/dim]")


