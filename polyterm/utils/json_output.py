"""JSON output utilities for scriptable interface"""

import json
import sys
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import asdict, is_dataclass


class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for PolyTerm data types"""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if is_dataclass(obj):
            return asdict(obj)
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return super().default(obj)


def output_json(data: Any, pretty: bool = True) -> str:
    """
    Convert data to JSON string.

    Args:
        data: Data to serialize
        pretty: Whether to pretty-print

    Returns:
        JSON string
    """
    if pretty:
        return json.dumps(data, cls=JSONEncoder, indent=2, sort_keys=False)
    return json.dumps(data, cls=JSONEncoder)


def print_json(data: Any, pretty: bool = True) -> None:
    """Print data as JSON to stdout"""
    print(output_json(data, pretty))


def format_market_json(market: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format market data for JSON output.

    Args:
        market: Raw market data from API

    Returns:
        Cleaned market data for JSON output
    """
    # Parse outcome prices
    outcome_prices = market.get('outcomePrices', [])
    if isinstance(outcome_prices, str):
        try:
            outcome_prices = json.loads(outcome_prices)
        except Exception:
            outcome_prices = []

    yes_price = float(outcome_prices[0]) if outcome_prices else 0
    no_price = float(outcome_prices[1]) if len(outcome_prices) > 1 else 1 - yes_price

    return {
        'id': market.get('id', market.get('conditionId', '')),
        'slug': market.get('slug', ''),
        'title': market.get('title', market.get('question', '')),
        'description': market.get('description', ''),
        'category': market.get('category', ''),
        'yes_price': yes_price,
        'no_price': no_price,
        'probability': yes_price * 100,
        'volume_24h': float(market.get('volume24hr', market.get('volume24Hr', 0)) or 0),
        'liquidity': float(market.get('liquidity', 0) or 0),
        'end_date': market.get('endDate', ''),
        'active': market.get('active', False),
        'closed': market.get('closed', False),
        'resolution': market.get('resolution', None),
    }


def format_markets_json(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format list of markets for JSON output"""
    return [format_market_json(m) for m in markets]


def format_trade_json(trade: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format trade data for JSON output.

    Args:
        trade: Raw trade data

    Returns:
        Cleaned trade data for JSON output
    """
    return {
        'market_id': trade.get('market_id', trade.get('market', '')),
        'market_slug': trade.get('market_slug', ''),
        'wallet_address': trade.get('wallet_address', trade.get('maker_address', '')),
        'side': trade.get('side', ''),
        'outcome': trade.get('outcome', ''),
        'price': float(trade.get('price', 0)),
        'size': float(trade.get('size', trade.get('amount', 0))),
        'notional': float(trade.get('notional', 0)),
        'timestamp': trade.get('timestamp', ''),
        'tx_hash': trade.get('tx_hash', trade.get('transactionHash', '')),
    }


def format_wallet_json(wallet) -> Dict[str, Any]:
    """
    Format wallet data for JSON output.

    Args:
        wallet: Wallet object or dict

    Returns:
        Cleaned wallet data for JSON output
    """
    if hasattr(wallet, 'to_dict'):
        return wallet.to_dict()

    return {
        'address': wallet.get('address', ''),
        'first_seen': wallet.get('first_seen', ''),
        'total_trades': wallet.get('total_trades', 0),
        'total_volume': wallet.get('total_volume', 0),
        'win_rate': wallet.get('win_rate', 0),
        'avg_position_size': wallet.get('avg_position_size', 0),
        'tags': wallet.get('tags', []),
        'risk_score': wallet.get('risk_score', 0),
        'is_whale': wallet.get('total_volume', 0) >= 100000,
        'is_smart_money': wallet.get('win_rate', 0) >= 0.70 and wallet.get('total_trades', 0) >= 10,
    }


def format_alert_json(alert) -> Dict[str, Any]:
    """
    Format alert data for JSON output.

    Args:
        alert: Alert object or dict

    Returns:
        Cleaned alert data for JSON output
    """
    if hasattr(alert, 'to_dict'):
        return alert.to_dict()

    return {
        'id': alert.get('id'),
        'type': alert.get('alert_type', alert.get('type', '')),
        'market_id': alert.get('market_id', ''),
        'wallet_address': alert.get('wallet_address', ''),
        'severity': alert.get('severity', 0),
        'message': alert.get('message', ''),
        'created_at': alert.get('created_at', ''),
        'acknowledged': alert.get('acknowledged', False),
    }


def format_arbitrage_json(arb) -> Dict[str, Any]:
    """
    Format arbitrage opportunity for JSON output.

    Args:
        arb: ArbitrageResult or dict

    Returns:
        Cleaned arbitrage data for JSON output
    """
    if hasattr(arb, '__dict__'):
        return {
            'type': arb.type,
            'market1_id': arb.market1_id,
            'market2_id': arb.market2_id,
            'market1_title': arb.market1_title,
            'market2_title': arb.market2_title,
            'market1_yes_price': arb.market1_yes_price,
            'market1_no_price': arb.market1_no_price,
            'market2_yes_price': arb.market2_yes_price,
            'market2_no_price': arb.market2_no_price,
            'spread': arb.spread,
            'spread_pct': arb.spread * 100,
            'expected_profit_pct': arb.expected_profit_pct,
            'expected_profit_usd': arb.expected_profit_usd,
            'fees': arb.fees,
            'net_profit': arb.net_profit,
            'confidence': arb.confidence,
            'timestamp': arb.timestamp.isoformat() if arb.timestamp else None,
        }

    return arb


def format_orderbook_json(analysis) -> Dict[str, Any]:
    """
    Format order book analysis for JSON output.

    Args:
        analysis: OrderBookAnalysis object

    Returns:
        Cleaned analysis data for JSON output
    """
    if hasattr(analysis, '__dict__'):
        return {
            'market_id': analysis.market_id,
            'timestamp': analysis.timestamp.isoformat() if analysis.timestamp else None,
            'best_bid': analysis.best_bid,
            'best_ask': analysis.best_ask,
            'spread': analysis.spread,
            'spread_pct': analysis.spread_pct,
            'mid_price': analysis.mid_price,
            'bid_depth': analysis.bid_depth,
            'ask_depth': analysis.ask_depth,
            'imbalance': analysis.imbalance,
            'support_levels': analysis.support_levels,
            'resistance_levels': analysis.resistance_levels,
            'large_bids': [{'price': l.price, 'size': l.size} for l in analysis.large_bids],
            'large_asks': [{'price': l.price, 'size': l.size} for l in analysis.large_asks],
            'warnings': analysis.warnings,
        }

    return analysis


class JSONOutput:
    """
    Context manager for JSON output mode.

    Usage:
        with JSONOutput(enabled=True) as out:
            out.add('markets', markets)
            out.add('timestamp', datetime.now())
        # Automatically prints JSON on exit
    """

    def __init__(self, enabled: bool = False, pretty: bool = True):
        self.enabled = enabled
        self.pretty = pretty
        self.data: Dict[str, Any] = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.enabled and self.data:
            print_json(self.data, self.pretty)

    def add(self, key: str, value: Any) -> None:
        """Add data to output"""
        self.data[key] = value

    def set_error(self, error: str) -> None:
        """Set error message"""
        self.data['error'] = error
        self.data['success'] = False

    def set_success(self) -> None:
        """Mark as successful"""
        self.data['success'] = True
