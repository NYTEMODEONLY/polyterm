"""Status bar for TUI"""

from datetime import datetime
from rich.console import Console


def display_status_bar(console: Console, market_count: int = 0, connected: bool = True):
    """Display bottom status bar with info
    
    Args:
        console: Rich Console instance
        market_count: Number of markets being tracked
        connected: API connection status
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    status_icon = "✅" if connected else "❌"
    
    status = f"{status_icon} Connected | Markets: {market_count} | Updated: {timestamp}"
    
    # Print status bar at bottom
    console.print(f"\n[dim]{status}[/dim]", style="on blue", justify="center")


def create_status_string(connected: bool = True, market_count: int = 0, extra: str = "") -> str:
    """Create status string without printing
    
    Args:
        connected: API connection status
        market_count: Number of markets
        extra: Extra status info
    
    Returns:
        Formatted status string
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    status_icon = "✅" if connected else "❌"
    
    parts = [
        f"{status_icon} Connected",
        f"Markets: {market_count}",
        f"Updated: {timestamp}"
    ]
    
    if extra:
        parts.append(extra)
    
    return " | ".join(parts)


