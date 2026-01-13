"""ASCII Charts for terminal display

Provides simple ASCII-based price charts for market analysis.
"""

from typing import List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class ChartPoint:
    """Single point on a chart"""
    timestamp: datetime
    value: float
    label: Optional[str] = None


class ASCIIChart:
    """Generate ASCII charts for terminal display"""

    # Chart characters
    CHARS = {
        'full': '█',
        'top': '▀',
        'bottom': '▄',
        'line': '─',
        'vline': '│',
        'corner_tl': '┌',
        'corner_tr': '┐',
        'corner_bl': '└',
        'corner_br': '┘',
        'dot': '●',
        'empty': ' ',
    }

    def __init__(self, width: int = 60, height: int = 15):
        """Initialize chart with dimensions

        Args:
            width: Chart width in characters
            height: Chart height in characters
        """
        self.width = width
        self.height = height

    def generate_line_chart(
        self,
        data: List[Tuple[datetime, float]],
        title: str = "",
        y_label: str = "",
        show_grid: bool = True,
    ) -> str:
        """Generate an ASCII line chart

        Args:
            data: List of (timestamp, value) tuples
            title: Chart title
            y_label: Y-axis label
            show_grid: Whether to show grid lines

        Returns:
            String containing the ASCII chart
        """
        if not data or len(data) < 2:
            return "Insufficient data for chart"

        # Extract values
        values = [v for _, v in data]
        min_val = min(values)
        max_val = max(values)

        # Handle case where all values are the same
        if max_val == min_val:
            max_val = min_val + 0.1

        # Calculate value range
        val_range = max_val - min_val

        # Create canvas
        canvas = [[' ' for _ in range(self.width)] for _ in range(self.height)]

        # Calculate points
        points = []
        for i, (ts, val) in enumerate(data):
            x = int((i / (len(data) - 1)) * (self.width - 1))
            y = int(((val - min_val) / val_range) * (self.height - 1))
            y = self.height - 1 - y  # Flip y-axis
            points.append((x, y))

        # Draw line connecting points
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            self._draw_line(canvas, x1, y1, x2, y2)

        # Mark actual data points
        for x, y in points:
            if 0 <= x < self.width and 0 <= y < self.height:
                canvas[y][x] = self.CHARS['dot']

        # Build output
        lines = []

        # Title
        if title:
            lines.append(f"  {title}")
            lines.append("")

        # Y-axis labels and chart
        y_labels = self._generate_y_labels(min_val, max_val, self.height)

        for i, row in enumerate(canvas):
            label = y_labels[i] if i < len(y_labels) else ""
            line = f"{label:>8} │{''.join(row)}"
            lines.append(line)

        # X-axis
        lines.append(f"{'':>8} └{'─' * self.width}")

        # Time labels
        if data:
            start_time = data[0][0].strftime("%H:%M")
            end_time = data[-1][0].strftime("%H:%M")
            mid_time = data[len(data)//2][0].strftime("%H:%M")
            time_line = f"{'':>9}{start_time}{'':>{self.width//2 - 5}}{mid_time}{'':>{self.width//2 - 5}}{end_time}"
            lines.append(time_line)

        return '\n'.join(lines)

    def generate_bar_chart(
        self,
        data: List[Tuple[str, float]],
        title: str = "",
        max_bar_width: int = 40,
    ) -> str:
        """Generate a horizontal bar chart

        Args:
            data: List of (label, value) tuples
            title: Chart title
            max_bar_width: Maximum bar width

        Returns:
            String containing the ASCII chart
        """
        if not data:
            return "No data for chart"

        lines = []

        if title:
            lines.append(f"  {title}")
            lines.append("")

        max_val = max(v for _, v in data)
        max_label_len = max(len(l) for l, _ in data)

        for label, value in data:
            bar_len = int((value / max_val) * max_bar_width) if max_val > 0 else 0
            bar = self.CHARS['full'] * bar_len
            lines.append(f"{label:>{max_label_len}} │{bar} {value:.1f}")

        return '\n'.join(lines)

    def generate_sparkline(self, values: List[float], width: int = 20) -> str:
        """Generate a compact sparkline

        Args:
            values: List of values
            width: Sparkline width

        Returns:
            Single-line sparkline string
        """
        if not values:
            return ""

        # Sparkline characters (8 levels)
        sparks = '▁▂▃▄▅▆▇█'

        min_val = min(values)
        max_val = max(values)

        if max_val == min_val:
            return sparks[4] * width

        # Sample values if too many
        if len(values) > width:
            step = len(values) / width
            sampled = [values[int(i * step)] for i in range(width)]
        else:
            sampled = values

        result = []
        for val in sampled:
            normalized = (val - min_val) / (max_val - min_val)
            idx = min(int(normalized * 7), 7)
            result.append(sparks[idx])

        return ''.join(result)

    def _draw_line(self, canvas: List[List[str]], x1: int, y1: int, x2: int, y2: int):
        """Draw a line between two points using Bresenham's algorithm"""
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy

        x, y = x1, y1

        while True:
            if 0 <= x < self.width and 0 <= y < self.height:
                if canvas[y][x] == ' ':
                    canvas[y][x] = '·'

            if x == x2 and y == y2:
                break

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

    def _generate_y_labels(self, min_val: float, max_val: float, count: int) -> List[str]:
        """Generate Y-axis labels"""
        labels = []
        step = (max_val - min_val) / (count - 1) if count > 1 else 0

        for i in range(count):
            val = max_val - (i * step)
            if val >= 1:
                labels.append(f"{val:.0f}%")
            else:
                labels.append(f"{val*100:.0f}%")

        return labels


def generate_price_chart(
    prices: List[Tuple[datetime, float]],
    title: str = "Price History",
    width: int = 50,
    height: int = 12,
) -> str:
    """Convenience function to generate a price chart

    Args:
        prices: List of (timestamp, price) tuples where price is 0-1
        title: Chart title
        width: Chart width
        height: Chart height

    Returns:
        ASCII chart string
    """
    chart = ASCIIChart(width=width, height=height)

    # Convert prices to percentages for display
    price_pcts = [(ts, price * 100) for ts, price in prices]

    return chart.generate_line_chart(price_pcts, title=title)


def generate_comparison_chart(
    market1_prices: List[Tuple[datetime, float]],
    market2_prices: List[Tuple[datetime, float]],
    market1_name: str = "Market 1",
    market2_name: str = "Market 2",
) -> str:
    """Generate a comparison sparkline for two markets

    Args:
        market1_prices: Prices for first market
        market2_prices: Prices for second market
        market1_name: Name of first market
        market2_name: Name of second market

    Returns:
        Comparison string with sparklines
    """
    chart = ASCIIChart()

    lines = []
    lines.append("Market Comparison")
    lines.append("")

    # Market 1
    if market1_prices:
        values1 = [p for _, p in market1_prices]
        spark1 = chart.generate_sparkline(values1, width=30)
        current1 = values1[-1] * 100 if values1 else 0
        change1 = ((values1[-1] - values1[0]) / values1[0] * 100) if values1 and values1[0] > 0 else 0
        lines.append(f"{market1_name[:20]:<20} {spark1} {current1:.0f}% ({change1:+.1f}%)")

    # Market 2
    if market2_prices:
        values2 = [p for _, p in market2_prices]
        spark2 = chart.generate_sparkline(values2, width=30)
        current2 = values2[-1] * 100 if values2 else 0
        change2 = ((values2[-1] - values2[0]) / values2[0] * 100) if values2 and values2[0] > 0 else 0
        lines.append(f"{market2_name[:20]:<20} {spark2} {current2:.0f}% ({change2:+.1f}%)")

    return '\n'.join(lines)
