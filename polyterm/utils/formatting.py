"""Formatting utilities for terminal output"""

from datetime import datetime
from typing import Optional
from rich.console import Console
from rich.text import Text


def format_probability(probability: float, previous: Optional[float] = None) -> str:
    """Format probability as percentage with optional change indicator"""
    prob_str = f"{probability:.1f}%"
    
    if previous is not None:
        change = probability - previous
        if abs(change) >= 0.1:  # Show change if >= 0.1%
            sign = "+" if change > 0 else ""
            prob_str += f" ({sign}{change:.1f}%)"
    
    return prob_str


def format_probability_rich(probability: float, previous: Optional[float] = None) -> Text:
    """Format probability with color coding based on change"""
    text = Text()
    
    prob_str = f"{probability:.1f}%"
    
    if previous is not None:
        change = probability - previous
        if change > 5:
            color = "bright_green"
        elif change > 0:
            color = "green"
        elif change < -5:
            color = "bright_red"
        elif change < 0:
            color = "red"
        else:
            color = "white"
        
        text.append(prob_str, style=color)
        
        if abs(change) >= 0.1:
            sign = "+" if change > 0 else ""
            text.append(f" ({sign}{change:.1f}%)", style=f"dim {color}")
    else:
        text.append(prob_str, style="white")
    
    return text


def format_volume(volume: float, use_short: bool = True) -> str:
    """Format volume with K/M/B suffixes"""
    if volume >= 1_000_000_000:
        return f"{volume / 1_000_000_000:.2f}B" if use_short else f"{volume:,.0f}"
    elif volume >= 1_000_000:
        return f"{volume / 1_000_000:.2f}M" if use_short else f"{volume:,.0f}"
    elif volume >= 1_000:
        return f"{volume / 1_000:.2f}K" if use_short else f"{volume:,.0f}"
    else:
        return f"{volume:.2f}"


def format_timestamp(timestamp: int, include_time: bool = True) -> str:
    """Format Unix timestamp as human-readable string"""
    dt = datetime.fromtimestamp(timestamp)
    if include_time:
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    else:
        return dt.strftime("%Y-%m-%d")


def format_duration(seconds: int) -> str:
    """Format duration in seconds as human-readable string"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours}h"
    else:
        days = seconds // 86400
        return f"{days}d"


def format_market_title(title: str, max_length: int = 60) -> str:
    """Format market title with ellipsis if too long"""
    if len(title) <= max_length:
        return title
    return title[:max_length - 3] + "..."


def format_change_indicator(change: float) -> str:
    """Return arrow indicator for change direction"""
    if change > 0:
        return "↑"
    elif change < 0:
        return "↓"
    else:
        return "→"


def create_volatility_bar(volatility: float, width: int = 10) -> str:
    """Create ASCII bar chart for volatility"""
    filled = int(volatility / 10 * width)  # Assuming 0-100 volatility scale
    return "█" * filled + "░" * (width - filled)

