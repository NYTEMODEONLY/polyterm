"""Copy trading / wallet following TUI screen"""

import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_follow_screen(console: Console):
    """Interactive wallet following screen"""
    console.clear()
    console.print(Panel(
        "[bold]Copy Trading - Wallet Following[/bold]\n\n"
        "[dim]Follow successful traders to learn from their moves.[/dim]\n\n"
        "Options:\n"
        "  [cyan]1.[/cyan] List followed wallets\n"
        "  [cyan]2.[/cyan] Follow a new wallet\n"
        "  [cyan]3.[/cyan] Unfollow a wallet\n"
        "  [cyan]4.[/cyan] Interactive mode (full features)\n\n"
        "[dim]Maximum 10 followed wallets.[/dim]",
        title="[cyan]Copy Trading[/cyan]",
        border_style="cyan",
    ))
    console.print()

    choice = Prompt.ask(
        "[cyan]Select option[/cyan]",
        choices=["1", "2", "3", "4", "q"],
        default="1"
    )

    if choice == "q":
        return

    if choice == "1":
        # List followed wallets
        cmd = ["polyterm", "follow", "--list"]
    elif choice == "2":
        # Follow a new wallet
        console.print()
        console.print("[bold]Where to find wallet addresses:[/bold]")
        console.print("  - Run 'polyterm wallets --type smart' to find smart money")
        console.print("  - Run 'polyterm wallets --type whales' to find whales")
        console.print("  - Copy addresses from Polymarket activity")
        console.print()
        address = Prompt.ask("[cyan]Enter wallet address to follow[/cyan]")
        if not address or len(address) < 10:
            console.print("[yellow]Invalid address.[/yellow]")
            Prompt.ask("[dim]Press Enter to return to menu[/dim]")
            return
        cmd = ["polyterm", "follow", "--add", address]
    elif choice == "3":
        # Unfollow a wallet
        console.print()
        address = Prompt.ask("[cyan]Enter wallet address to unfollow[/cyan]")
        if not address or len(address) < 10:
            console.print("[yellow]Invalid address.[/yellow]")
            Prompt.ask("[dim]Press Enter to return to menu[/dim]")
            return
        cmd = ["polyterm", "follow", "--remove", address]
    else:
        # Interactive mode
        cmd = ["polyterm", "follow"]

    console.print()
    console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")
    console.print()

    # Run command
    try:
        result = subprocess.run(cmd, capture_output=False)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

    console.print()
    Prompt.ask("[dim]Press Enter to return to menu[/dim]")
