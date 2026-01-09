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
        return

    elif choice == 'b':
        return

    else:
        console.print("[red]Invalid option[/red]")

    console.print()
    console.input("[dim]Press Enter to continue...[/dim]")


def _get_installed_version_pipx() -> str:
    """Get the currently installed version from pipx"""
    import subprocess
    try:
        result = subprocess.run(["pipx", "list"], capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'polyterm' in line.lower():
                    # Parse "package polyterm 0.4.2, installed using..."
                    import re
                    match = re.search(r'polyterm\s+(\d+\.\d+\.\d+)', line)
                    if match:
                        return match.group(1)
    except Exception:
        pass
    return ""


def update_polyterm(console: RichConsole) -> bool:
    """Enhanced PolyTerm update function with auto-restart capability

    Returns:
        True if app should restart, False otherwise
    """

    console.print(Panel("[bold green]🔄 PolyTerm Update[/bold green]", style="green"))
    console.print()
    console.print("[dim]This will update PolyTerm to the latest version.[/dim]")
    console.print()

    import subprocess
    import sys
    import requests
    import polyterm

    try:
        # Step 1: Check current version
        console.print("[cyan]Step 1:[/cyan] Checking current version...")
        current_version = polyterm.__version__
        console.print(f"[green]Current version:[/green] {current_version}")
        console.print()

        # Step 2: Check for updates
        console.print("[cyan]Step 2:[/cyan] Checking for updates...")
        latest_version = None
        try:
            response = requests.get("https://pypi.org/pypi/polyterm/json", timeout=10)
            if response.status_code == 200:
                data = response.json()
                latest_version = data["info"]["version"]

                if latest_version == current_version:
                    console.print(f"[green]✅ You're already running the latest version ({current_version})![/green]")
                    console.print()
                    console.print("[dim]No update needed.[/dim]")
                    console.print()
                    console.input("[dim]Press Enter to return to menu...[/dim]")
                    return False
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

        has_pipx = False
        has_pip = False

        # Check for pipx
        try:
            subprocess.run(["pipx", "--version"], capture_output=True, check=True)
            has_pipx = True
            console.print("[green]✓[/green] pipx available")
        except (subprocess.CalledProcessError, FileNotFoundError):
            console.print("[dim]✗[/dim] pipx not available")

        # Check for pip
        try:
            subprocess.run([sys.executable, "-m", "pip", "--version"], capture_output=True, check=True)
            has_pip = True
            console.print("[green]✓[/green] pip available")
        except (subprocess.CalledProcessError, FileNotFoundError):
            console.print("[dim]✗[/dim] pip not available")

        if not has_pipx and not has_pip:
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
            console.input("[dim]Press Enter to return to menu...[/dim]")
            return False

        # Step 4: Perform update
        console.print()
        console.print("[cyan]Step 4:[/cyan] Updating PolyTerm...")

        update_success = False

        if has_pipx:
            console.print("[green]Using pipx to update...[/green]")

            # First try pipx upgrade
            console.print("[dim]Trying pipx upgrade...[/dim]")
            result = subprocess.run(["pipx", "upgrade", "polyterm"], capture_output=True, text=True)

            # Verify the upgrade actually worked by checking installed version
            installed_version = _get_installed_version_pipx()
            if installed_version == latest_version:
                update_success = True
                console.print(f"[green]✓ Upgraded to {installed_version}[/green]")
            else:
                # pipx upgrade didn't work, try reinstall
                console.print("[yellow]pipx upgrade didn't update the version, trying reinstall...[/yellow]")
                subprocess.run(["pipx", "uninstall", "polyterm"], capture_output=True, text=True)
                # Use --no-cache-dir to avoid pip caching old versions
                result = subprocess.run(
                    ["pipx", "install", "polyterm", "--pip-args=--no-cache-dir"],
                    capture_output=True, text=True
                )

                if result.returncode == 0:
                    installed_version = _get_installed_version_pipx()
                    if installed_version == latest_version:
                        update_success = True
                        console.print(f"[green]✓ Reinstalled to {installed_version}[/green]")

        if not update_success and has_pip:
            console.print("[green]Using pip to update...[/green]")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "polyterm"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                update_success = True

        if update_success:
            console.print()
            console.print("[bold green]✅ Update successful![/bold green]")
            if latest_version:
                console.print(f"[green]Updated to version {latest_version}[/green]")
            console.print()

            # Ask user if they want to restart
            console.print("[bold cyan]Would you like to restart PolyTerm now?[/bold cyan]")
            console.print("[dim]Restarting is required to use the new version.[/dim]")
            console.print()
            restart = console.input("[cyan]Restart now? (Y/n):[/cyan] ").strip().lower()

            if restart != 'n':
                console.print()
                console.print("[green]🔄 Restarting PolyTerm...[/green]")
                console.print()

                # Use os.execv to replace current process with new polyterm
                import shutil
                polyterm_path = shutil.which("polyterm")

                if polyterm_path:
                    os.execv(polyterm_path, ["polyterm"])
                else:
                    # Fallback: try running as module
                    os.execv(sys.executable, [sys.executable, "-m", "polyterm"])

                # If we get here, exec failed
                return True
            else:
                console.print()
                console.print("[yellow]Update installed but not active.[/yellow]")
                console.print("[dim]Please restart PolyTerm manually to use the new version.[/dim]")
                console.print()
                console.input("[dim]Press Enter to return to menu...[/dim]")
                return False

        else:
            console.print()
            console.print("[bold red]❌ Update failed[/bold red]")
            console.print()
            console.print("[yellow]Try running manually:[/yellow]")
            console.print("[dim]  pipx uninstall polyterm && pipx install polyterm[/dim]")
            console.print("[dim]  pip install --upgrade polyterm[/dim]")
            console.print()
            console.input("[dim]Press Enter to return to menu...[/dim]")
            return False

    except Exception as e:
        console.print()
        console.print("[bold red]❌ Update process failed[/bold red]")
        console.print(f"[red]Unexpected error: {e}[/red]")
        console.print()
        console.print("[yellow]Please try updating manually:[/yellow]")
        console.print("[dim]  pipx uninstall polyterm && pipx install polyterm[/dim]")
        console.print("[dim]  pip install --upgrade polyterm[/dim]")
        console.print()
        console.input("[dim]Press Enter to return to menu...[/dim]")
        return False


