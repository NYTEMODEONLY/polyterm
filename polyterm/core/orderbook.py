"""
Order Book Intelligence Module

Features:
- ASCII visualization of bid/ask depth
- Large hidden order (iceberg) detection
- Support/resistance level identification
- Slippage calculator
- Liquidity imbalance alerts
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import math

from ..api.clob import CLOBClient


@dataclass
class OrderBookLevel:
    """Single price level in order book"""
    price: float
    size: float
    cumulative_size: float = 0.0
    order_count: int = 0


@dataclass
class OrderBookAnalysis:
    """Analysis results for an order book"""
    market_id: str
    timestamp: datetime
    best_bid: float
    best_ask: float
    spread: float
    spread_pct: float
    mid_price: float

    # Depth analysis
    bid_depth: float  # Total bid volume
    ask_depth: float  # Total ask volume
    imbalance: float  # -1 to 1, positive = more bids

    # Support/resistance
    support_levels: List[float]
    resistance_levels: List[float]

    # Large orders
    large_bids: List[OrderBookLevel]
    large_asks: List[OrderBookLevel]

    # Warnings
    warnings: List[str]


class OrderBookAnalyzer:
    """
    Analyzes order books for trading insights.
    """

    def __init__(
        self,
        clob_client: CLOBClient,
        large_order_threshold: float = 10000,  # $10k
    ):
        self.clob = clob_client
        self.large_order_threshold = large_order_threshold

    def get_order_book(self, market_id: str, depth: int = 50) -> Dict[str, Any]:
        """Fetch order book from CLOB"""
        return self.clob.get_order_book(market_id, depth=depth)

    def analyze(self, market_id: str, depth: int = 50) -> Optional[OrderBookAnalysis]:
        """
        Perform comprehensive order book analysis.

        Args:
            market_id: Market ID or token ID
            depth: Number of price levels to fetch

        Returns:
            OrderBookAnalysis with insights
        """
        try:
            book = self.get_order_book(market_id, depth)
        except Exception as e:
            print(f"Error fetching order book: {e}")
            return None

        bids = book.get('bids', [])
        asks = book.get('asks', [])

        if not bids or not asks:
            return None

        # Parse levels
        bid_levels = self._parse_levels(bids)
        ask_levels = self._parse_levels(asks)

        # Basic metrics
        best_bid = bid_levels[0].price if bid_levels else 0
        best_ask = ask_levels[0].price if ask_levels else 0
        spread = best_ask - best_bid
        mid_price = (best_bid + best_ask) / 2 if best_bid and best_ask else 0
        spread_pct = (spread / mid_price * 100) if mid_price else 0

        # Calculate depth
        bid_depth = sum(level.size * level.price for level in bid_levels)
        ask_depth = sum(level.size * level.price for level in ask_levels)
        total_depth = bid_depth + ask_depth
        imbalance = (bid_depth - ask_depth) / total_depth if total_depth else 0

        # Find support/resistance levels
        support_levels = self._find_support_levels(bid_levels)
        resistance_levels = self._find_resistance_levels(ask_levels)

        # Find large orders
        large_bids = [l for l in bid_levels if l.size * l.price >= self.large_order_threshold]
        large_asks = [l for l in ask_levels if l.size * l.price >= self.large_order_threshold]

        # Generate warnings
        warnings = []
        if abs(imbalance) > 0.5:
            side = "bids" if imbalance > 0 else "asks"
            warnings.append(f"High liquidity imbalance towards {side}")

        if spread_pct > 5:
            warnings.append(f"Wide spread: {spread_pct:.1f}%")

        if large_bids or large_asks:
            warnings.append(f"Large orders detected: {len(large_bids)} bids, {len(large_asks)} asks")

        return OrderBookAnalysis(
            market_id=market_id,
            timestamp=datetime.now(),
            best_bid=best_bid,
            best_ask=best_ask,
            spread=spread,
            spread_pct=spread_pct,
            mid_price=mid_price,
            bid_depth=bid_depth,
            ask_depth=ask_depth,
            imbalance=imbalance,
            support_levels=support_levels,
            resistance_levels=resistance_levels,
            large_bids=large_bids,
            large_asks=large_asks,
            warnings=warnings,
        )

    def _parse_levels(self, levels: List) -> List[OrderBookLevel]:
        """Parse raw order book levels"""
        parsed = []
        cumulative = 0.0

        for level in levels:
            if isinstance(level, list) and len(level) >= 2:
                price = float(level[0])
                size = float(level[1])
            elif isinstance(level, dict):
                price = float(level.get('price', 0))
                size = float(level.get('size', level.get('amount', 0)))
            else:
                continue

            cumulative += size
            parsed.append(OrderBookLevel(
                price=price,
                size=size,
                cumulative_size=cumulative,
            ))

        return parsed

    def _find_support_levels(
        self,
        bid_levels: List[OrderBookLevel],
        min_size_multiple: float = 3.0,
    ) -> List[float]:
        """Find support levels from bid clustering"""
        if not bid_levels:
            return []

        avg_size = sum(l.size for l in bid_levels) / len(bid_levels) if bid_levels else 0
        threshold = avg_size * min_size_multiple

        support = []
        for level in bid_levels:
            if level.size >= threshold:
                support.append(level.price)

        return support[:5]  # Top 5 support levels

    def _find_resistance_levels(
        self,
        ask_levels: List[OrderBookLevel],
        min_size_multiple: float = 3.0,
    ) -> List[float]:
        """Find resistance levels from ask clustering"""
        if not ask_levels:
            return []

        avg_size = sum(l.size for l in ask_levels) / len(ask_levels) if ask_levels else 0
        threshold = avg_size * min_size_multiple

        resistance = []
        for level in ask_levels:
            if level.size >= threshold:
                resistance.append(level.price)

        return resistance[:5]  # Top 5 resistance levels

    def calculate_slippage(
        self,
        market_id: str,
        side: str,
        size: float,
    ) -> Dict[str, Any]:
        """
        Calculate expected slippage for a given order size.

        Args:
            market_id: Market ID
            side: 'buy' or 'sell'
            size: Order size in shares

        Returns:
            Slippage analysis
        """
        try:
            book = self.get_order_book(market_id, depth=100)
        except Exception as e:
            return {'error': str(e)}

        if side.lower() == 'buy':
            levels = book.get('asks', [])
        else:
            levels = book.get('bids', [])

        if not levels:
            return {'error': 'No liquidity'}

        parsed = self._parse_levels(levels)
        if not parsed:
            return {'error': 'Could not parse order book'}

        # Calculate execution
        remaining = size
        total_cost = 0.0
        filled_levels = []

        for level in parsed:
            if remaining <= 0:
                break

            fill_size = min(remaining, level.size)
            total_cost += fill_size * level.price
            remaining -= fill_size
            filled_levels.append({
                'price': level.price,
                'size': fill_size,
            })

        if remaining > 0:
            return {
                'error': 'Insufficient liquidity',
                'available': size - remaining,
            }

        avg_price = total_cost / size
        best_price = parsed[0].price
        slippage = abs(avg_price - best_price)
        slippage_pct = (slippage / best_price) * 100

        return {
            'side': side,
            'size': size,
            'best_price': best_price,
            'avg_price': avg_price,
            'slippage': slippage,
            'slippage_pct': slippage_pct,
            'total_cost': total_cost,
            'levels_used': len(filled_levels),
        }

    def render_ascii_depth_chart(
        self,
        market_id: str,
        width: int = 60,
        height: int = 20,
        depth: int = 20,
    ) -> str:
        """
        Render an ASCII depth chart for the terminal.

        Args:
            market_id: Market ID
            width: Chart width in characters
            height: Chart height in lines
            depth: Number of price levels

        Returns:
            ASCII art representation of order book
        """
        try:
            book = self.get_order_book(market_id, depth=depth)
        except Exception as e:
            return f"Error fetching order book: {e}"

        bids = self._parse_levels(book.get('bids', []))
        asks = self._parse_levels(book.get('asks', []))

        if not bids or not asks:
            return "No order book data available"

        # Calculate cumulative depths
        bid_cumulative = []
        ask_cumulative = []

        cum = 0
        for level in reversed(bids):
            cum += level.size * level.price
            bid_cumulative.append((level.price, cum))
        bid_cumulative.reverse()

        cum = 0
        for level in asks:
            cum += level.size * level.price
            ask_cumulative.append((level.price, cum))

        # Find max depth for scaling
        max_depth = max(
            max((d for _, d in bid_cumulative), default=0),
            max((d for _, d in ask_cumulative), default=0),
        )

        if max_depth == 0:
            return "No depth data"

        # Build chart
        lines = []
        half_width = width // 2

        # Header
        lines.append(f"{'BIDS':^{half_width}} | {'ASKS':^{half_width}}")
        lines.append("-" * width)

        # Price range
        min_price = min(bid_cumulative[-1][0] if bid_cumulative else 0, asks[0].price if asks else 1)
        max_price = max(bids[0].price if bids else 0, ask_cumulative[-1][0] if ask_cumulative else 0)

        # Render each row
        for i in range(height):
            # Calculate price at this row
            price = max_price - (i / height) * (max_price - min_price)

            # Find cumulative depth at this price
            bid_depth_at_price = 0
            for p, d in bid_cumulative:
                if p <= price:
                    bid_depth_at_price = d
                    break

            ask_depth_at_price = 0
            for p, d in ask_cumulative:
                if p >= price:
                    ask_depth_at_price = d
                    break

            # Scale to width
            bid_bar_len = int((bid_depth_at_price / max_depth) * (half_width - 8))
            ask_bar_len = int((ask_depth_at_price / max_depth) * (half_width - 8))

            # Render bars (bids right-aligned, asks left-aligned)
            bid_bar = "#" * bid_bar_len
            ask_bar = "#" * ask_bar_len

            bid_section = f"{bid_bar:>{half_width - 1}}"
            ask_section = f"{ask_bar:<{half_width - 1}}"

            lines.append(f"{bid_section} | {ask_section}")

        # Footer with best prices
        lines.append("-" * width)
        best_bid = bids[0].price if bids else 0
        best_ask = asks[0].price if asks else 0
        spread = best_ask - best_bid
        spread_pct = (spread / ((best_bid + best_ask) / 2) * 100) if best_bid + best_ask > 0 else 0

        lines.append(f"Best Bid: ${best_bid:.3f} | Best Ask: ${best_ask:.3f}")
        lines.append(f"Spread: ${spread:.4f} ({spread_pct:.2f}%)")
        lines.append(f"Bid Depth: ${bid_cumulative[0][1]:,.0f} | Ask Depth: ${ask_cumulative[-1][1]:,.0f}")

        return "\n".join(lines)

    def detect_iceberg_orders(
        self,
        market_id: str,
        min_replenish_count: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Detect potential iceberg (hidden) orders.

        Icebergs are large orders split into smaller visible chunks
        that replenish as they're filled.

        This requires monitoring the order book over time.

        Args:
            market_id: Market ID
            min_replenish_count: Minimum replenishments to flag as iceberg

        Returns:
            List of potential iceberg orders
        """
        # Note: Real iceberg detection requires monitoring over time
        # This is a simplified version that looks for suspicious patterns
        try:
            book = self.get_order_book(market_id, depth=50)
        except Exception as e:
            return []

        potential_icebergs = []

        # Look for repeated sizes at same price (could indicate iceberg)
        bids = book.get('bids', [])
        asks = book.get('asks', [])

        for side, levels in [('bid', bids), ('ask', asks)]:
            size_counts = {}
            for level in levels:
                if isinstance(level, list) and len(level) >= 2:
                    size = float(level[1])
                    price = float(level[0])

                    # Round size to detect similar sizes
                    rounded = round(size, -2)  # Round to nearest 100
                    if rounded not in size_counts:
                        size_counts[rounded] = []
                    size_counts[rounded].append(price)

            # Flag sizes that appear multiple times
            for size, prices in size_counts.items():
                if len(prices) >= 2 and size >= 1000:
                    potential_icebergs.append({
                        'side': side,
                        'size': size,
                        'prices': prices,
                        'count': len(prices),
                        'reason': 'Repeated size pattern',
                    })

        return potential_icebergs

    def format_analysis(self, analysis: OrderBookAnalysis) -> str:
        """Format analysis for display"""
        lines = []

        lines.append(f"=== Order Book Analysis ===")
        lines.append(f"Market: {analysis.market_id[:40]}")
        lines.append(f"Time: {analysis.timestamp.strftime('%H:%M:%S')}")
        lines.append("")

        lines.append(f"Best Bid:  ${analysis.best_bid:.4f}")
        lines.append(f"Best Ask:  ${analysis.best_ask:.4f}")
        lines.append(f"Mid Price: ${analysis.mid_price:.4f}")
        lines.append(f"Spread:    ${analysis.spread:.4f} ({analysis.spread_pct:.2f}%)")
        lines.append("")

        lines.append(f"Bid Depth: ${analysis.bid_depth:,.0f}")
        lines.append(f"Ask Depth: ${analysis.ask_depth:,.0f}")

        imbalance_bar = "#" * int(abs(analysis.imbalance) * 10)
        imbalance_side = "BIDS" if analysis.imbalance > 0 else "ASKS"
        lines.append(f"Imbalance: {analysis.imbalance:+.2f} ({imbalance_bar} {imbalance_side})")
        lines.append("")

        if analysis.support_levels:
            lines.append(f"Support Levels: {', '.join(f'${p:.3f}' for p in analysis.support_levels)}")

        if analysis.resistance_levels:
            lines.append(f"Resistance Levels: {', '.join(f'${p:.3f}' for p in analysis.resistance_levels)}")

        if analysis.large_bids:
            lines.append(f"\nLarge Bids ({len(analysis.large_bids)}):")
            for level in analysis.large_bids[:3]:
                lines.append(f"  ${level.price:.4f}: {level.size:,.0f} shares (${level.size * level.price:,.0f})")

        if analysis.large_asks:
            lines.append(f"\nLarge Asks ({len(analysis.large_asks)}):")
            for level in analysis.large_asks[:3]:
                lines.append(f"  ${level.price:.4f}: {level.size:,.0f} shares (${level.size * level.price:,.0f})")

        if analysis.warnings:
            lines.append(f"\nWarnings:")
            for warning in analysis.warnings:
                lines.append(f"  - {warning}")

        return "\n".join(lines)
