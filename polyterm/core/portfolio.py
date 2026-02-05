"""
Portfolio Analytics Module

Rebuilt to work without deprecated Subgraph API.
Uses:
- Polygon RPC for on-chain data
- Local database for cached positions
- Gamma API for market data
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from decimal import Decimal

import requests

from ..db.database import Database
from ..db.models import Trade, Wallet
from ..api.gamma import GammaClient


@dataclass
class Position:
    """User position in a market"""
    market_id: str
    market_title: str
    outcome: str  # YES or NO
    shares: float
    avg_price: float
    current_price: float
    cost_basis: float
    current_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            'market_id': self.market_id,
            'market_title': self.market_title,
            'outcome': self.outcome,
            'shares': self.shares,
            'avg_price': self.avg_price,
            'current_price': self.current_price,
            'cost_basis': self.cost_basis,
            'current_value': self.current_value,
            'unrealized_pnl': self.unrealized_pnl,
            'unrealized_pnl_pct': self.unrealized_pnl_pct,
        }


@dataclass
class PortfolioSummary:
    """Portfolio summary statistics"""
    wallet_address: str
    total_positions: int
    total_cost_basis: float
    total_current_value: float
    total_unrealized_pnl: float
    total_unrealized_pnl_pct: float
    realized_pnl: float
    total_trades: int
    win_rate: float
    positions: List[Position] = field(default_factory=list)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'wallet_address': self.wallet_address,
            'total_positions': self.total_positions,
            'total_cost_basis': self.total_cost_basis,
            'total_current_value': self.total_current_value,
            'total_unrealized_pnl': self.total_unrealized_pnl,
            'total_unrealized_pnl_pct': self.total_unrealized_pnl_pct,
            'realized_pnl': self.realized_pnl,
            'total_trades': self.total_trades,
            'win_rate': self.win_rate,
            'positions': [p.to_dict() for p in self.positions],
            'updated_at': self.updated_at.isoformat(),
        }


class PolygonRPCClient:
    """
    Client for Polygon RPC to read on-chain data.

    Uses public RPC endpoints or configured private RPC.
    """

    DEFAULT_RPC = "https://polygon-rpc.com"

    # Polymarket contract addresses
    CTFEXCHANGE = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8fed8e9"
    CONDITIONAL_TOKENS = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"

    def __init__(self, rpc_url: Optional[str] = None):
        self.rpc_url = rpc_url or self.DEFAULT_RPC
        self.session = requests.Session()

    def _call(self, method: str, params: List[Any]) -> Any:
        """Make RPC call"""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1,
        }

        try:
            response = self.session.post(
                self.rpc_url,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()

            if "error" in result:
                raise Exception(f"RPC error: {result['error']}")

            return result.get("result")

        except Exception as e:
            print(f"RPC call failed: {e}")
            return None

    def get_balance(self, address: str, token_address: str) -> int:
        """Get ERC20 token balance"""
        # ERC20 balanceOf(address) selector
        selector = "0x70a08231"
        padded_address = address.lower().replace("0x", "").zfill(64)
        data = selector + padded_address

        result = self._call("eth_call", [
            {"to": token_address, "data": data},
            "latest"
        ])

        if result:
            return int(result, 16)
        return 0

    def get_conditional_token_balance(
        self,
        address: str,
        condition_id: str,
        outcome_index: int,
    ) -> int:
        """
        Get balance of conditional token for a specific outcome.

        Polymarket uses ERC1155 conditional tokens.
        """
        # ERC1155 balanceOf(address,uint256) selector
        selector = "0x00fdd58e"

        # Calculate position ID
        # positionId = hash(collateralToken, conditionId, indexSet)
        # This is simplified - actual implementation needs proper calculation

        padded_address = address.lower().replace("0x", "").zfill(64)
        # Position ID calculation would go here

        # For now, return 0 as we need the actual position ID
        return 0

    def get_block_number(self) -> int:
        """Get current block number"""
        result = self._call("eth_blockNumber", [])
        if result:
            return int(result, 16)
        return 0


class PortfolioAnalytics:
    """
    Portfolio analytics using local database and Polygon RPC.

    Since the Subgraph API is deprecated, we:
    1. Track positions from trade history in local DB
    2. Optionally verify on-chain via Polygon RPC
    3. Get current prices from Gamma API
    """

    def __init__(
        self,
        database: Database,
        gamma_client: Optional[GammaClient] = None,
        polygon_rpc_url: Optional[str] = None,
    ):
        self.db = database
        self.gamma = gamma_client
        self.polygon = PolygonRPCClient(polygon_rpc_url) if polygon_rpc_url else None

        # Cache for market prices
        self._price_cache: Dict[str, Tuple[float, datetime]] = {}
        self._cache_ttl = 60  # 1 minute

    def get_portfolio(self, wallet_address: str) -> PortfolioSummary:
        """
        Get portfolio summary for a wallet.

        Builds positions from local trade history.

        Args:
            wallet_address: Wallet address

        Returns:
            PortfolioSummary
        """
        # Get wallet data
        wallet = self.db.get_wallet(wallet_address)
        trades = self.db.get_trades_by_wallet(wallet_address, limit=10000)

        if not trades:
            return PortfolioSummary(
                wallet_address=wallet_address,
                total_positions=0,
                total_cost_basis=0,
                total_current_value=0,
                total_unrealized_pnl=0,
                total_unrealized_pnl_pct=0,
                realized_pnl=0,
                total_trades=0,
                win_rate=0,
            )

        # Build positions from trades
        positions_map: Dict[str, Dict[str, Any]] = {}

        for trade in sorted(trades, key=lambda t: t.timestamp):
            key = f"{trade.market_id}:{trade.outcome}"

            if key not in positions_map:
                positions_map[key] = {
                    'market_id': trade.market_id,
                    'market_slug': trade.market_slug,
                    'outcome': trade.outcome or 'YES',
                    'shares': 0.0,
                    'cost_basis': 0.0,
                    'trades': [],
                }

            pos = positions_map[key]

            # Update position based on trade side
            if trade.side == 'BUY':
                pos['shares'] += trade.size
                pos['cost_basis'] += trade.notional
            else:
                pos['shares'] -= trade.size
                pos['cost_basis'] -= trade.notional

            pos['trades'].append(trade)

        # Calculate current values
        positions = []
        total_cost = 0
        total_value = 0

        for key, pos_data in positions_map.items():
            if pos_data['shares'] <= 0:
                continue  # Skip closed positions

            shares = pos_data['shares']
            cost_basis = max(0, pos_data['cost_basis'])
            avg_price = cost_basis / shares if shares > 0 else 0

            # Get current price
            current_price = self._get_current_price(pos_data['market_id'], pos_data['outcome'])
            current_value = shares * current_price

            unrealized_pnl = current_value - cost_basis
            unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0

            # Get market title
            market_title = self._get_market_title(pos_data['market_id'])

            position = Position(
                market_id=pos_data['market_id'],
                market_title=market_title,
                outcome=pos_data['outcome'],
                shares=shares,
                avg_price=avg_price,
                current_price=current_price,
                cost_basis=cost_basis,
                current_value=current_value,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_pct=unrealized_pnl_pct,
            )
            positions.append(position)

            total_cost += cost_basis
            total_value += current_value

        # Calculate realized P&L from closed positions
        realized_pnl = self._calculate_realized_pnl(trades)

        # Calculate win rate
        win_rate = wallet.win_rate if wallet else 0

        total_unrealized = total_value - total_cost
        total_unrealized_pct = (total_unrealized / total_cost * 100) if total_cost > 0 else 0

        return PortfolioSummary(
            wallet_address=wallet_address,
            total_positions=len(positions),
            total_cost_basis=total_cost,
            total_current_value=total_value,
            total_unrealized_pnl=total_unrealized,
            total_unrealized_pnl_pct=total_unrealized_pct,
            realized_pnl=realized_pnl,
            total_trades=len(trades),
            win_rate=win_rate,
            positions=positions,
        )

    def _get_current_price(self, market_id: str, outcome: str) -> float:
        """Get current market price"""
        # Check cache
        cache_key = f"{market_id}:{outcome}"
        if cache_key in self._price_cache:
            price, cached_at = self._price_cache[cache_key]
            if datetime.now() - cached_at < timedelta(seconds=self._cache_ttl):
                return price

        # Fetch from API
        if self.gamma:
            try:
                markets = self.gamma.get_markets(limit=1, market_id=market_id)
                if markets:
                    nested = markets[0].get('markets', [])
                    if nested:
                        outcome_prices = nested[0].get('outcomePrices', [])
                        if isinstance(outcome_prices, str):
                            outcome_prices = json.loads(outcome_prices)
                        if outcome_prices:
                            if outcome == 'YES':
                                price = float(outcome_prices[0])
                            else:
                                price = float(outcome_prices[1]) if len(outcome_prices) > 1 else 1 - float(outcome_prices[0])

                            self._price_cache[cache_key] = (price, datetime.now())
                            return price
            except Exception as e:
                print(f"Error fetching price: {e}")

        return 0.5  # Default to 50%

    def _get_market_title(self, market_id: str) -> str:
        """Get market title"""
        if self.gamma:
            try:
                markets = self.gamma.get_markets(limit=1, market_id=market_id)
                if markets:
                    return markets[0].get('title', markets[0].get('question', market_id))
            except Exception:
                pass
        return market_id[:30]

    def _calculate_realized_pnl(self, trades: List[Trade]) -> float:
        """Calculate realized P&L from trade history"""
        # Group by market
        market_trades: Dict[str, List[Trade]] = {}
        for trade in trades:
            key = f"{trade.market_id}:{trade.outcome}"
            if key not in market_trades:
                market_trades[key] = []
            market_trades[key].append(trade)

        realized = 0.0

        for key, market_t in market_trades.items():
            # Sort by time
            sorted_trades = sorted(market_t, key=lambda t: t.timestamp)

            # Track position and cost
            shares = 0.0
            cost_basis = 0.0

            for trade in sorted_trades:
                if trade.side == 'BUY':
                    shares += trade.size
                    cost_basis += trade.notional
                else:
                    # Selling realizes P&L
                    if shares > 0:
                        avg_cost = cost_basis / shares
                        sold_cost = avg_cost * min(trade.size, shares)
                        realized += trade.notional - sold_cost

                        # Update position
                        shares -= trade.size
                        cost_basis -= sold_cost

        return realized

    def get_performance_history(
        self,
        wallet_address: str,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Get portfolio value history.

        Args:
            wallet_address: Wallet address
            days: Number of days of history

        Returns:
            List of daily snapshots
        """
        # This would require historical snapshots
        # For now, return empty list
        return []

    def get_risk_analysis(self, wallet_address: str) -> Dict[str, Any]:
        """
        Analyze portfolio risk.

        Returns:
            Risk metrics
        """
        portfolio = self.get_portfolio(wallet_address)

        if not portfolio.positions:
            return {
                'wallet_address': wallet_address,
                'concentration_risk': 'N/A',
                'max_position_pct': 0,
                'diversification_score': 0,
            }

        # Position concentration
        total_value = portfolio.total_current_value
        position_pcts = []

        for pos in portfolio.positions:
            if total_value > 0:
                pct = (pos.current_value / total_value) * 100
                position_pcts.append({
                    'market': pos.market_title[:30],
                    'percentage': pct,
                    'value': pos.current_value,
                })

        position_pcts.sort(key=lambda x: x['percentage'], reverse=True)

        # Calculate concentration metrics
        max_position = position_pcts[0]['percentage'] if position_pcts else 0

        # Herfindahl-Hirschman Index for concentration
        hhi = sum((p['percentage'] / 100) ** 2 for p in position_pcts) * 10000

        # Concentration risk level
        if max_position > 50:
            concentration_risk = 'high'
        elif max_position > 30:
            concentration_risk = 'medium'
        else:
            concentration_risk = 'low'

        # Diversification score (inverse of HHI, normalized)
        diversification = max(0, min(100, 100 - (hhi / 100)))

        return {
            'wallet_address': wallet_address,
            'total_value': total_value,
            'position_count': len(portfolio.positions),
            'concentration_risk': concentration_risk,
            'max_position_pct': max_position,
            'hhi_index': hhi,
            'diversification_score': diversification,
            'top_positions': position_pcts[:5],
            'risk_factors': self._identify_risk_factors(portfolio),
        }

    def _identify_risk_factors(self, portfolio: PortfolioSummary) -> List[str]:
        """Identify risk factors in portfolio"""
        factors = []

        if portfolio.total_positions == 1:
            factors.append("Single position - no diversification")

        if portfolio.total_unrealized_pnl_pct < -20:
            factors.append(f"Significant unrealized loss ({portfolio.total_unrealized_pnl_pct:.1f}%)")

        # Check for highly correlated positions
        # Would need correlation data

        return factors

    def render_portfolio_ascii(self, portfolio: PortfolioSummary) -> str:
        """Render portfolio as ASCII table"""
        lines = []

        lines.append("=" * 70)
        lines.append(f"Portfolio: {portfolio.wallet_address[:20]}...")
        lines.append("=" * 70)
        lines.append("")

        # Summary
        lines.append("Summary:")
        lines.append(f"  Positions: {portfolio.total_positions}")
        lines.append(f"  Cost Basis: ${portfolio.total_cost_basis:,.2f}")
        lines.append(f"  Current Value: ${portfolio.total_current_value:,.2f}")

        pnl_sign = "+" if portfolio.total_unrealized_pnl >= 0 else ""
        lines.append(f"  Unrealized P&L: {pnl_sign}${portfolio.total_unrealized_pnl:,.2f} ({pnl_sign}{portfolio.total_unrealized_pnl_pct:.1f}%)")
        lines.append(f"  Realized P&L: ${portfolio.realized_pnl:,.2f}")
        lines.append(f"  Win Rate: {portfolio.win_rate:.0%}")
        lines.append("")

        # Positions
        if portfolio.positions:
            lines.append("Positions:")
            lines.append("-" * 70)
            lines.append(f"{'Market':<30} {'Side':<5} {'Shares':<10} {'P&L':<15}")
            lines.append("-" * 70)

            for pos in sorted(portfolio.positions, key=lambda p: p.unrealized_pnl, reverse=True):
                pnl_str = f"${pos.unrealized_pnl:+,.0f} ({pos.unrealized_pnl_pct:+.1f}%)"
                lines.append(f"{pos.market_title[:30]:<30} {pos.outcome:<5} {pos.shares:<10.0f} {pnl_str:<15}")

        lines.append("")
        lines.append(f"Last Updated: {portfolio.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")

        return "\n".join(lines)
