# Charts

> ASCII chart generation for terminal-based price visualization (line, bar, sparkline).

## Overview

The charts module provides terminal-friendly chart rendering without any external charting dependencies. It supports three chart types: line charts with Bresenham's line algorithm for smooth point-to-point rendering, horizontal bar charts, and compact sparklines using Unicode block elements. These are used throughout the TUI for price history visualization and market comparison displays.

## Key Classes and Functions

### `ChartPoint`

Dataclass representing a single point on a chart.

```python
@dataclass
class ChartPoint:
    timestamp: datetime
    value: float
    label: Optional[str] = None
```

### `ASCIIChart`

Main chart generation class.

#### Constructor

```python
ASCIIChart(width: int = 60, height: int = 15)
```

#### Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `generate_line_chart` | `(data: List[Tuple[datetime, float]], title: str = "", y_label: str = "", show_grid: bool = True) -> str` | Generate a full ASCII line chart with axes and labels |
| `generate_bar_chart` | `(data: List[Tuple[str, float]], title: str = "", max_bar_width: int = 40) -> str` | Generate a horizontal bar chart |
| `generate_sparkline` | `(values: List[float], width: int = 20) -> str` | Generate a compact single-line sparkline |

#### Private Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `_draw_line` | `(canvas, x1, y1, x2, y2) -> None` | Bresenham's line algorithm for drawing between points |
| `_generate_y_labels` | `(min_val, max_val, count) -> List[str]` | Generate Y-axis percentage labels |

### `generate_price_chart(prices, title, width, height)`

Convenience function for generating price charts.

```python
def generate_price_chart(
    prices: List[Tuple[datetime, float]],  # price values 0-1
    title: str = "Price History",
    width: int = 50,
    height: int = 12,
) -> str
```

Automatically converts prices from 0-1 range to percentages (0-100%) for display.

### `generate_comparison_chart(market1_prices, market2_prices, market1_name, market2_name)`

Generate side-by-side sparkline comparison for two markets.

```python
def generate_comparison_chart(
    market1_prices: List[Tuple[datetime, float]],
    market2_prices: List[Tuple[datetime, float]],
    market1_name: str = "Market 1",
    market2_name: str = "Market 2",
) -> str
```

Shows each market's sparkline with current price and percentage change.

## Scoring / Algorithms

### Bresenham's Line Algorithm

Used in `_draw_line` to rasterize smooth lines between data points on the character canvas. Intermediate pixels use the `'` character while actual data points use `'` (filled circle).

### Sparkline Encoding

Uses 8 Unicode block elements to represent value intensity:

```
Level 0: ▁  (lowest)
Level 1: ▂
Level 2: ▃
Level 3: ▄
Level 4: ▅
Level 5: ▆
Level 6: ▇
Level 7: █  (highest)
```

Values are normalized to 0-1 range and mapped to one of 8 levels. When the input has more values than the target width, values are downsampled by stepping through the array.

### Canvas Rendering

1. Values are mapped to (x, y) coordinates on a character grid
2. X: linearly mapped across chart width
3. Y: linearly mapped and flipped (high values at top)
4. Lines drawn between consecutive points using Bresenham's algorithm
5. Y-axis labels formatted as percentages

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `width` | `60` | Chart width in characters |
| `height` | `15` | Chart height in characters |
| `max_bar_width` | `40` | Maximum bar width for bar charts |
| Sparkline `width` | `20` | Number of characters in sparkline |

### Chart Characters

| Key | Character | Usage |
|-----|-----------|-------|
| `full` | `\u2588` | Bar chart fill |
| `dot` | `\u25cf` | Data point marker |
| `line` | `\u2500` | X-axis line |
| `vline` | `\u2502` | Y-axis line |
| `corner_bl` | `\u2514` | Axis corner |
| Intermediate | `\u00b7` | Line segments between points |

## Data Sources

- Price data from `db/database.py` (market snapshots)
- CLOB price history via `api/clob.py` (`get_price_history()`)
- Direct data passed from CLI commands

## Output Format

All methods return multi-line strings suitable for direct terminal printing.

### Line chart example structure

```
  Price History

   100% |          ●·
    90% |       ·●    ●
    80% |    ●·
    70% | ●·
         └──────────────
          08:00   12:00   16:00
```

### Bar chart example structure

```
  Volume by Market

  Bitcoin │████████████████ 45000.0
  Ethereum │██████████ 28000.0
  SOL │████ 12000.0
```

### Sparkline example

```
▁▂▃▄▅▆▇█▇▆▅▄▃▂▁
```

### Comparison chart example

```
Market Comparison

Bitcoin              ▁▂▃▅▆▇▇█▇▆▅▅▄▃▃▂▂▂▃▃▄▅▅▆▆▆▇▇▇ 72% (+5.2%)
Ethereum             ▂▂▃▃▄▅▅▆▆▅▅▄▃▃▂▂▂▃▃▃▄▄▅▅▅▆▆▇▇▇ 68% (+3.1%)
```

## External Dependencies

None. This module is dependency-free and uses only Python standard library and Unicode characters.

## Related

- CLI commands: `polyterm chart -m "bitcoin"`, `polyterm compare -i`
- TUI screens: `ch` (chart), `cmp` (compare)
- Other modules: `cli/commands/chart.py` (chart command), `cli/commands/compare.py` (comparison command), `core/orderbook.py` (order book ASCII visualization)
