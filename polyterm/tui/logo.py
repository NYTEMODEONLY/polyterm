"""ASCII Logo for PolyTerm TUI"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text


def display_logo(console: Console):
    """Display PolyTerm ASCII logo with colors, responsive to terminal width
    
    Args:
        console: Rich Console instance
    """
    # Get terminal width, fallback to 80 if not available
    try:
        width = console.size.width
    except Exception:
        width = 80
    
    # Force narrow terminal for testing if COLUMNS env var is set
    import os
    if 'COLUMNS' in os.environ:
        width = int(os.environ['COLUMNS'])
    
    if width >= 80:
        # Full ASCII logo for wide terminals - NO BORDER
        logo_text = """
   ██████╗  ██████╗ ██╗  ██╗   ██╗████████╗███████╗██████╗ ███╗   ███╗
   ██╔══██╗██╔═══██╗██║  ╚██╗ ██╔╝╚══██╔══╝██╔════╝██╔══██╗████╗ ████║
   ██████╔╝██║   ██║██║   ╚████╔╝    ██║   █████╗  ██████╔╝██╔████╔██║
   ██╔═══╝ ██║   ██║██║    ╚██╔╝     ██║   ██╔══╝  ██╔══██╗██║╚██╔╝██║
   ██║     ╚██████╔╝███████╗██║      ██║   ███████╗██║  ██║██║ ╚═╝ ██║
   ╚═╝      ╚═════╝ ╚══════╝╚═╝      ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝

         Terminal-Based Monitoring for PolyMarket
                   Track. Analyze. Profit.
"""
        nytemode_padding = "                      "
    elif width >= 60:
        # Medium ASCII logo for medium terminals - NO BORDER
        logo_text = """
  ██████╗  ██████╗ ██╗  ██╗   ██╗████████╗███████╗██████╗ ███╗   ███╗
  ██╔══██╗██╔═══██╗██║  ╚██╗ ██╔╝╚══██╔══╝██╔════╝██╔══██╗████╗ ████║
  ██████╔╝██║   ██║██║   ╚████╔╝    ██║   █████╗  ██████╔╝██╔████╔██║
  ██╔═══╝ ██║   ██║██║    ╚██╔╝     ██║   ██╔══╝  ██╔══██╗██║╚██╔╝██║
  ██║     ╚██████╔╝███████╗██║      ██║   ███████╗██║  ██║██║ ╚═╝ ██║
  ╚═╝      ╚═════╝ ╚══════╝╚═╝      ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝

    Terminal-Based Monitoring for PolyMarket
              Track. Analyze. Profit.
"""
        nytemode_padding = "                 "
    else:
        # Compact ASCII logo for narrow terminals - NO BORDER
        logo_text = """
  ██████╗  ██████╗ ██╗  ██╗   ██╗████████╗
  ██╔══██╗██╔═══██╗██║  ╚██╗ ██╔╝╚══██╔══╝
  ██████╔╝██║   ██║██║   ╚████╔╝    ██║
  ██╔═══╝ ██║   ██║██║    ╚██╔╝     ██║
  ██║     ╚██████╔╝███████╗██║      ██║
  ╚═╝      ╚═════╝ ╚══════╝╚═╝      ╚═╝

     PolyTerm - PolyMarket Monitor
        Track. Analyze. Profit.
"""
        nytemode_padding = "           "

    console.print(logo_text, style="bold cyan")
    console.print(f"{nytemode_padding}[bright_magenta]a nytemode project[/bright_magenta]")
    console.print()


