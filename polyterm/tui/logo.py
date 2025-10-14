"""ASCII Logo for PolyTerm TUI"""

POLYTERM_LOGO = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   ██████╗  ██████╗ ██╗  ██╗   ██╗████████╗███████╗██████╗ ███╗   ███╗
║   ██╔══██╗██╔═══██╗██║  ╚██╗ ██╔╝╚══██╔══╝██╔════╝██╔══██╗████╗ ████║
║   ██████╔╝██║   ██║██║   ╚████╔╝    ██║   █████╗  ██████╔╝██╔████╔██║
║   ██╔═══╝ ██║   ██║██║    ╚██╔╝     ██║   ██╔══╝  ██╔══██╗██║╚██╔╝██║
║   ██║     ╚██████╔╝███████╗██║      ██║   ███████╗██║  ██║██║ ╚═╝ ██║
║   ╚═╝      ╚═════╝ ╚══════╝╚═╝      ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝
║                                                           ║
║         Terminal-Based Monitoring for PolyMarket         ║
║                   Track. Analyze. Profit.                ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
"""


def display_logo(console):
    """Display PolyTerm ASCII logo with colors
    
    Args:
        console: Rich Console instance
    """
    console.print(POLYTERM_LOGO, style="bold cyan")
    console.print()


