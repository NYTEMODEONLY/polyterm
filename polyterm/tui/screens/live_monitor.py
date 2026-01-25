"""Live Monitor Screen - Interactive market/category selection for live monitoring"""

from rich.panel import Panel
from rich.console import Console as RichConsole
from rich.table import Table
from rich.prompt import Prompt, Confirm
import subprocess
import sys
import os
import re
from polyterm.api.gamma import GammaClient
from polyterm.utils.config import Config


# Category options with descriptions and keywords for verification
CATEGORY_OPTIONS = [
    ("sports", "🏈 Sports", "NFL, NBA, Super Bowl, Championships...",
     ['nfl', 'nba', 'mlb', 'nhl', 'super bowl', 'championship', 'playoffs']),
    ("crypto", "💰 Crypto", "Bitcoin, Ethereum, Solana, XRP...",
     ['bitcoin', 'btc', 'ethereum', 'eth', 'solana', 'crypto']),
    ("politics", "🏛️ Politics", "Elections, Trump, Biden, Congress...",
     ['trump', 'biden', 'election', 'congress', 'senate', 'president']),
    ("economics", "📈 Economics", "Fed, Interest rates, Inflation...",
     ['fed', 'interest rate', 'inflation', 'gdp', 'recession', 'economy']),
    ("entertainment", "🎬 Entertainment", "Movies, TV, Awards, Celebrities...",
     ['oscar', 'grammy', 'emmy', 'movie', 'tv show', 'netflix', 'box office']),
]


def verify_category_markets(gamma_client: GammaClient, category: str, keywords: list) -> int:
    """Verify markets exist for category using keyword matching"""
    try:
        markets = gamma_client.get_markets(limit=100, closed=False)
        count = 0
        for m in markets:
            title = ' ' + m.get('question', '').lower() + ' '
            if any(kw in title for kw in keywords):
                count += 1
        return count
    except:
        return 0


def live_monitor_screen(console: RichConsole):
    """Interactive live monitor screen with market/category selection
    
    Args:
        console: Rich Console instance
    """
    console.print(Panel("[bold red]🔴 Live Market Monitor Setup[/bold red]", style="red"))
    console.print()
    
    # Load config
    config = Config()
    
    # Initialize gamma client for market search
    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )
    
    try:
        # Monitoring mode selection
        console.print("[cyan]Select monitoring mode:[/cyan]")
        console.print()
        console.print("1. 🔍 Monitor specific market")
        console.print("2. 📂 Monitor category (crypto, politics, sports, etc.)")
        console.print("3. 🌐 Monitor all active markets")
        console.print()
        
        choice = Prompt.ask("Enter choice", choices=["1", "2", "3"], default="1")
        
        if choice == "1":
            # Market selection
            console.print()
            console.print("[cyan]Market Selection:[/cyan]")
            market_search = Prompt.ask("Enter market ID, slug, or search term")
            
            try:
                # Try as ID/slug first
                try:
                    market_data = gamma_client.get_market(market_search)
                    market_id = market_data.get("id")
                    market_title = market_data.get("question")
                    console.print(f"\n[green]Found market:[/green] {market_title}")
                except:
                    # Search by term
                    console.print(f"\n[yellow]Searching for markets containing: {market_search}[/yellow]")
                    results = gamma_client.search_markets(market_search, limit=10)
                    
                    if not results:
                        console.print(f"[red]No markets found for: {market_search}[/red]")
                        return
                    
                    # Show search results
                    table = Table(title="Search Results", show_header=True, header_style="bold magenta")
                    table.add_column("#", style="cyan", width=3)
                    table.add_column("Market", style="white")
                    table.add_column("Category", style="dim")
                    
                    for i, m in enumerate(results):
                        table.add_row(
                            str(i+1),
                            m.get("question", "")[:60],
                            m.get("category", "unknown")
                        )
                    
                    console.print(table)
                    
                    choice_num = Prompt.ask("Select market number", default="1")
                    try:
                        choice_idx = int(choice_num) - 1
                        if 0 <= choice_idx < len(results):
                            selected = results[choice_idx]
                            market_id = selected.get("id")
                            market_title = selected.get("question")
                            console.print(f"\n[green]Selected:[/green] {market_title}")
                        else:
                            console.print("[red]Invalid selection[/red]")
                            return
                    except ValueError:
                        console.print("[red]Invalid selection[/red]")
                        return
                
                # Launch live monitor for specific market
                launch_live_monitor(console, market_id=market_id, market_title=market_title)
                
            except Exception as e:
                console.print(f"[red]Error finding market: {e}[/red]")
                return
        
        elif choice == "2":
            # Category selection with improved menu
            console.print()
            console.print("[cyan]Category Selection:[/cyan]")
            console.print()

            # Display category options in a nice table
            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_column("#", style="cyan", width=3)
            table.add_column("Category", style="bold", width=18)
            table.add_column("Examples", style="dim")

            for i, (key, name, desc, _) in enumerate(CATEGORY_OPTIONS, 1):
                table.add_row(str(i), name, desc)

            console.print(table)
            console.print()

            try:
                cat_choice = int(Prompt.ask(f"Select category (1-{len(CATEGORY_OPTIONS)})", default="1"))
                if 1 <= cat_choice <= len(CATEGORY_OPTIONS):
                    category, cat_name, _, keywords = CATEGORY_OPTIONS[cat_choice - 1]
                else:
                    console.print("[red]Invalid choice. Using 'sports' as default.[/red]")
                    category, cat_name, _, keywords = CATEGORY_OPTIONS[0]
            except ValueError:
                console.print("[red]Invalid input. Using 'sports' as default.[/red]")
                category, cat_name, _, keywords = CATEGORY_OPTIONS[0]

            # Verify category has markets using keyword matching
            console.print(f"\n[dim]Checking for {category} markets...[/dim]")
            market_count = verify_category_markets(gamma_client, category, keywords)

            if market_count == 0:
                console.print(f"[yellow]No active markets found for: {cat_name}[/yellow]")
                console.print("[dim]You can still proceed - markets may appear[/dim]")
                if not Confirm.ask("Continue anyway?"):
                    return
            else:
                console.print(f"[green]Found {market_count} {category} markets![/green]")

            console.print(f"\n[green]Selected:[/green] {cat_name}")
            launch_live_monitor(console, category=category)
        
        else:
            # All markets
            console.print()
            console.print("[green]Monitoring all active markets[/green]")
            console.print("[dim]This will show the most active markets across all categories[/dim]")
            console.print()
            
            if Confirm.ask("Launch live monitor for all markets?"):
                launch_live_monitor(console)
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Setup cancelled[/yellow]")
    finally:
        try:
            gamma_client.close()
        except:
            pass


def launch_live_monitor(console: RichConsole, market_id: str = None, market_title: str = None, category: str = None):
    """Launch the live monitor in a new terminal window"""
    
    console.print()
    console.print("[green]🔴 Launching Live Monitor...[/green]")
    console.print()
    
    # Build command arguments
    cmd_args = [sys.executable, "-m", "polyterm.cli.main", "live-monitor"]
    
    if market_id:
        cmd_args.extend(["--market", market_id])
        monitor_type = f"Market: {market_title[:50]}"
    elif category:
        cmd_args.extend(["--category", category])
        monitor_type = f"Category: {category.title()}"
    else:
        monitor_type = "All Active Markets"
    
    # Create temporary script for the new terminal
    script_content = f'''
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from polyterm.cli.commands.live_monitor import LiveMarketMonitor
from polyterm.utils.config import Config

# Load config
config = Config()

# Create and run monitor
monitor = LiveMarketMonitor(config, market_id="{market_id or ''}", category="{category or ''}")
monitor.run_live_monitor()
'''
    
    # Write temporary script with proper synchronization
    script_path = "/tmp/polyterm_live_monitor.py"

    # Create script with forced disk sync
    with open(script_path, 'w') as f:
        f.write(script_content)
        f.flush()  # Force write to buffer
        os.fsync(f.fileno())  # Force write to disk

    # Make script executable
    os.chmod(script_path, 0o755)

    # Verify script exists and is readable
    if not os.path.exists(script_path):
        console.print("[red]❌ Failed to create script file[/red]")
        return

    # Read back to verify content
    try:
        with open(script_path, 'r') as f:
            if len(f.read()) != len(script_content):
                console.print("[red]❌ Script file incomplete[/red]")
                return
    except:
        console.print("[red]❌ Cannot read script file[/red]")
        return

    console.print(f"[green]✅ Script created at {script_path}[/green]")

    try:
        # Launch in new terminal with blocking call to ensure it starts
        if sys.platform == "darwin":  # macOS
            # Use subprocess.run instead of Popen for synchronous execution
            # Use sys.executable to ensure we use the same Python that has polyterm installed
            # Use pipx Python interpreter instead of sys.executable
            # Try to find pipx Python path dynamically
            pipx_python = None
            try:
                # Check if we're running from pipx
                if "/.local/pipx/venvs/polyterm/bin/python" in sys.executable:
                    pipx_python = sys.executable
                else:
                    # Try to find pipx Python path
                    result = subprocess.run(["which", "polyterm"], capture_output=True, text=True)
                    if result.returncode == 0:
                        polyterm_path = result.stdout.strip()
                        # Extract Python path from polyterm script
                        with open(polyterm_path, 'r') as f:
                            first_line = f.readline()
                            if first_line.startswith('#!'):
                                python_path = first_line[2:].strip()
                                # Only use if it's actually a Python interpreter
                                if 'python' in python_path.lower():
                                    pipx_python = python_path
                                # else: will fall through to sys.executable fallback below
            except Exception as e:
                print(f"Error finding pipx Python: {e}")
                pass
            
            # Fallback to sys.executable if pipx not found
            if not pipx_python:
                pipx_python = sys.executable
            
            result = subprocess.run([
                "osascript", "-e",
                f'tell app "Terminal" to do script "{pipx_python} {script_path}"'
            ], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                console.print("[green]✅ Second terminal launched successfully[/green]")
            else:
                console.print(f"[red]❌ Terminal launch failed: {result.stderr}[/red]")

        elif sys.platform.startswith("linux"):  # Linux
            subprocess.run([
                "gnome-terminal", "--", "python3", script_path
            ], timeout=5)
        elif sys.platform == "win32":  # Windows
            subprocess.run([
                "start", "cmd", "/k", f"python {script_path}"
            ], shell=True, timeout=5)
        else:
            # Fallback - run in current terminal
            console.print("[yellow]Running live monitor in current terminal...[/yellow]")
            console.print("[dim]Press Ctrl+C to stop[/dim]")
            console.print()

            # Import and run directly
            from polyterm.cli.commands.live_monitor import LiveMarketMonitor
            from polyterm.utils.config import Config
            
            config = Config()
            monitor = LiveMarketMonitor(config, market_id=market_id, category=category)
            monitor.run_live_monitor()
            return
        
        # Success message
        console.print(Panel(
            f"[bold green]🔴 Live Monitor Launched![/bold green]\n\n"
            f"[cyan]Monitoring:[/cyan] {monitor_type}\n"
            f"[dim]A new terminal window has opened with your live monitor[/dim]\n"
            f"[dim]Close the terminal window or press Ctrl+C to stop monitoring[/dim]",
            style="green"
        ))
        
    except Exception as e:
        console.print(f"[red]Error launching live monitor: {e}[/red]")
        console.print("[yellow]Falling back to current terminal...[/yellow]")
        
        # Fallback - run in current terminal
        try:
            from polyterm.cli.commands.live_monitor import LiveMarketMonitor
            from polyterm.utils.config import Config
            
            config = Config()
            monitor = LiveMarketMonitor(config, market_id=market_id, category=category)
            monitor.run_live_monitor()
        except Exception as fallback_error:
            console.print(f"[red]Error running live monitor: {fallback_error}[/red]")
    
    # Note: Script cleanup is handled by the live monitor itself when it exits
    # This prevents premature deletion before the second terminal can execute it
