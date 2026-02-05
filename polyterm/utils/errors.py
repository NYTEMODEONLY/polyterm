"""Centralized error handling for user-friendly error messages"""

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from typing import Optional


class PolyTermError(Exception):
    """Base exception for PolyTerm with user-friendly messaging"""

    def __init__(self, message: str, suggestion: str = None, details: str = None):
        self.message = message
        self.suggestion = suggestion
        self.details = details
        super().__init__(message)


class APIError(PolyTermError):
    """API-related errors"""
    pass


class ConfigError(PolyTermError):
    """Configuration-related errors"""
    pass


class ValidationError(PolyTermError):
    """Input validation errors"""
    pass


class NetworkError(PolyTermError):
    """Network connectivity errors"""
    pass


def display_error(
    console: Console,
    title: str,
    message: str,
    suggestion: str = None,
    details: str = None,
):
    """Display a user-friendly error message"""
    content = f"[red]{escape(message)}[/red]"

    if details:
        content += f"\n\n[dim]Details: {escape(details)}[/dim]"

    if suggestion:
        content += f"\n\n[yellow]Suggestion:[/yellow] {escape(suggestion)}"

    console.print()
    console.print(Panel(
        content,
        title=f"[bold red]{title}[/bold red]",
        border_style="red",
    ))
    console.print()


def handle_api_error(console: Console, error: Exception, context: str = "API request"):
    """Handle API errors with helpful messages"""
    error_str = str(error).lower()

    if "timeout" in error_str or "timed out" in error_str:
        display_error(
            console,
            "Connection Timeout",
            f"The {context} took too long to respond.",
            suggestion="Check your internet connection or try again in a few moments.",
        )
    elif "connection" in error_str or "connect" in error_str:
        display_error(
            console,
            "Connection Failed",
            f"Could not connect to the API for {context}.",
            suggestion="Check your internet connection. The Polymarket API may also be temporarily down.",
            details=str(error),
        )
    elif "404" in error_str or "not found" in error_str:
        display_error(
            console,
            "Not Found",
            f"The requested resource was not found.",
            suggestion="Check that the market ID or search term is correct.",
        )
    elif "403" in error_str or "forbidden" in error_str or "unauthorized" in error_str:
        display_error(
            console,
            "Access Denied",
            "You don't have permission to access this resource.",
            suggestion="Check your API key in settings: polyterm config --api-key",
        )
    elif "429" in error_str or "rate limit" in error_str:
        display_error(
            console,
            "Rate Limited",
            "Too many requests. The API is temporarily limiting access.",
            suggestion="Wait a few seconds before trying again.",
        )
    elif "500" in error_str or "internal server" in error_str:
        display_error(
            console,
            "Server Error",
            "The Polymarket API is experiencing issues.",
            suggestion="This is usually temporary. Try again in a few minutes.",
        )
    else:
        display_error(
            console,
            "API Error",
            f"An error occurred during {context}.",
            suggestion="Try again or check 'polyterm --help' for usage.",
            details=str(error),
        )


def handle_validation_error(console: Console, field: str, value: str, expected: str):
    """Handle input validation errors"""
    display_error(
        console,
        "Invalid Input",
        f"The value '{value}' is not valid for {field}.",
        suggestion=f"Expected: {expected}",
    )


def handle_config_error(console: Console, error: Exception):
    """Handle configuration errors"""
    display_error(
        console,
        "Configuration Error",
        "There's an issue with your configuration.",
        suggestion="Try running 'polyterm config' to fix settings, or delete ~/.polyterm/config.toml to reset.",
        details=str(error),
    )


def handle_network_error(console: Console, error: Exception):
    """Handle network connectivity errors"""
    display_error(
        console,
        "Network Error",
        "Could not establish a network connection.",
        suggestion="Check your internet connection and try again.",
        details=str(error),
    )


# Common error messages with suggestions
ERROR_MESSAGES = {
    "no_markets_found": {
        "title": "No Markets Found",
        "message": "No markets matched your search criteria.",
        "suggestion": "Try broader search terms or check if the market is still active.",
    },
    "no_whales_found": {
        "title": "No Whale Activity",
        "message": "No whale trades found in the specified time period.",
        "suggestion": "Try extending the time period with --hours or lowering the threshold with --min-amount.",
    },
    "no_arbitrage": {
        "title": "No Arbitrage Opportunities",
        "message": "No arbitrage opportunities found at current spread levels.",
        "suggestion": "Try lowering the minimum spread with --min-spread, or check back later.",
    },
    "no_predictions": {
        "title": "No Predictions Available",
        "message": "Could not generate predictions for the requested markets.",
        "suggestion": "Some markets may not have enough data. Try different markets.",
    },
    "empty_portfolio": {
        "title": "Empty Portfolio",
        "message": "No positions found in your portfolio.",
        "suggestion": "Add wallet addresses with 'polyterm portfolio --add-wallet <address>'",
    },
    "invalid_market_id": {
        "title": "Invalid Market ID",
        "message": "The market ID format is not recognized.",
        "suggestion": "Market IDs are typically long hex strings starting with '0x'. Try searching by market name instead.",
    },
    "invalid_wallet": {
        "title": "Invalid Wallet Address",
        "message": "The wallet address format is not valid.",
        "suggestion": "Ethereum addresses are 42 characters starting with '0x'.",
    },
    "database_error": {
        "title": "Database Error",
        "message": "Could not access the local database.",
        "suggestion": "Try deleting ~/.polyterm/data.db and restarting PolyTerm.",
    },
}


def show_error(console: Console, error_key: str, details: str = None):
    """Show a predefined error message"""
    if error_key in ERROR_MESSAGES:
        err = ERROR_MESSAGES[error_key]
        display_error(
            console,
            err["title"],
            err["message"],
            err.get("suggestion"),
            details,
        )
    else:
        display_error(
            console,
            "Error",
            f"An unexpected error occurred: {error_key}",
            suggestion="Please try again or report this issue.",
            details=details,
        )


def format_suggestion(text: str) -> str:
    """Format a suggestion for inline display"""
    return f"[dim]Tip: {text}[/dim]"


def success_message(console: Console, title: str, message: str):
    """Display a success message"""
    console.print(Panel(
        f"[green]{message}[/green]",
        title=f"[bold green]{title}[/bold green]",
        border_style="green",
    ))
