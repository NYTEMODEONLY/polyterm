"""Database models for persistent storage"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
import json


@dataclass
class Wallet:
    """Wallet profile for tracking traders"""
    address: str
    first_seen: datetime
    total_trades: int = 0
    total_volume: float = 0.0
    win_rate: float = 0.0
    avg_position_size: float = 0.0
    tags: List[str] = field(default_factory=list)
    updated_at: datetime = field(default_factory=datetime.now)

    # Analytics fields
    total_wins: int = 0
    total_losses: int = 0
    largest_trade: float = 0.0
    favorite_markets: List[str] = field(default_factory=list)
    risk_score: int = 0  # 0-100, higher = more suspicious

    def to_dict(self) -> Dict[str, Any]:
        return {
            'address': self.address,
            'first_seen': self.first_seen.isoformat(),
            'total_trades': self.total_trades,
            'total_volume': self.total_volume,
            'win_rate': self.win_rate,
            'avg_position_size': self.avg_position_size,
            'tags': self.tags,
            'updated_at': self.updated_at.isoformat(),
            'total_wins': self.total_wins,
            'total_losses': self.total_losses,
            'largest_trade': self.largest_trade,
            'favorite_markets': self.favorite_markets,
            'risk_score': self.risk_score,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Wallet':
        tags = data.get('tags', '[]')
        if isinstance(tags, str):
            tags = json.loads(tags)

        fav_markets = data.get('favorite_markets', '[]')
        if isinstance(fav_markets, str):
            fav_markets = json.loads(fav_markets)

        first_seen = data.get('first_seen')
        if isinstance(first_seen, str):
            first_seen = datetime.fromisoformat(first_seen)
        elif first_seen is None:
            first_seen = datetime.now()

        updated_at = data.get('updated_at')
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        elif updated_at is None:
            updated_at = datetime.now()

        return cls(
            address=data['address'],
            first_seen=first_seen,
            total_trades=data.get('total_trades', 0),
            total_volume=data.get('total_volume', 0.0),
            win_rate=data.get('win_rate', 0.0),
            avg_position_size=data.get('avg_position_size', 0.0),
            tags=tags,
            updated_at=updated_at,
            total_wins=data.get('total_wins', 0),
            total_losses=data.get('total_losses', 0),
            largest_trade=data.get('largest_trade', 0.0),
            favorite_markets=fav_markets,
            risk_score=data.get('risk_score', 0),
        )

    def is_whale(self) -> bool:
        """Check if wallet qualifies as a whale"""
        return self.total_volume >= 100000 or 'whale' in self.tags

    def is_smart_money(self) -> bool:
        """Check if wallet is considered smart money"""
        return self.win_rate >= 0.70 and self.total_trades >= 10

    def is_suspicious(self) -> bool:
        """Check if wallet has suspicious activity"""
        return self.risk_score >= 70 or 'insider_suspect' in self.tags


@dataclass
class Trade:
    """Trade record"""
    id: Optional[int] = None
    market_id: str = ""
    market_slug: str = ""
    wallet_address: str = ""
    side: str = ""  # BUY/SELL
    outcome: str = ""  # YES/NO
    price: float = 0.0
    size: float = 0.0
    notional: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    tx_hash: str = ""
    maker_address: str = ""
    taker_address: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'market_id': self.market_id,
            'market_slug': self.market_slug,
            'wallet_address': self.wallet_address,
            'side': self.side,
            'outcome': self.outcome,
            'price': self.price,
            'size': self.size,
            'notional': self.notional,
            'timestamp': self.timestamp.isoformat(),
            'tx_hash': self.tx_hash,
            'maker_address': self.maker_address,
            'taker_address': self.taker_address,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Trade':
        timestamp = data.get('timestamp')
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif isinstance(timestamp, (int, float)):
            timestamp = datetime.fromtimestamp(timestamp)
        elif timestamp is None:
            timestamp = datetime.now()

        return cls(
            id=data.get('id'),
            market_id=data.get('market_id', ''),
            market_slug=data.get('market_slug', ''),
            wallet_address=data.get('wallet_address', ''),
            side=data.get('side', ''),
            outcome=data.get('outcome', ''),
            price=float(data.get('price', 0)),
            size=float(data.get('size', 0)),
            notional=float(data.get('notional', 0)),
            timestamp=timestamp,
            tx_hash=data.get('tx_hash', ''),
            maker_address=data.get('maker_address', ''),
            taker_address=data.get('taker_address', ''),
        )


@dataclass
class Alert:
    """Alert record for persistence"""
    id: Optional[int] = None
    alert_type: str = ""  # whale, insider, arbitrage, price_shift, volume_spike
    market_id: str = ""
    wallet_address: str = ""
    severity: int = 0  # 0-100
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'alert_type': self.alert_type,
            'market_id': self.market_id,
            'wallet_address': self.wallet_address,
            'severity': self.severity,
            'message': self.message,
            'data': self.data,
            'created_at': self.created_at.isoformat(),
            'acknowledged': self.acknowledged,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Alert':
        alert_data = data.get('data', '{}')
        if isinstance(alert_data, str):
            alert_data = json.loads(alert_data)

        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()

        # Handle severity - convert string labels to numeric values
        severity = data.get('severity', 0)
        if isinstance(severity, str):
            severity_map = {'high': 80, 'medium': 50, 'low': 20, 'critical': 90}
            severity = severity_map.get(severity.lower(), 0)
        severity = int(severity) if severity else 0

        return cls(
            id=data.get('id'),
            alert_type=data.get('alert_type', ''),
            market_id=data.get('market_id', ''),
            wallet_address=data.get('wallet_address', ''),
            severity=severity,
            message=data.get('message', ''),
            data=alert_data,
            created_at=created_at,
            acknowledged=data.get('acknowledged', False),
        )


@dataclass
class MarketSnapshot:
    """Market snapshot for historical analysis"""
    id: Optional[int] = None
    market_id: str = ""
    market_slug: str = ""
    title: str = ""
    probability: float = 0.0
    volume_24h: float = 0.0
    liquidity: float = 0.0
    best_bid: float = 0.0
    best_ask: float = 0.0
    spread: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'market_id': self.market_id,
            'market_slug': self.market_slug,
            'title': self.title,
            'probability': self.probability,
            'volume_24h': self.volume_24h,
            'liquidity': self.liquidity,
            'best_bid': self.best_bid,
            'best_ask': self.best_ask,
            'spread': self.spread,
            'timestamp': self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MarketSnapshot':
        timestamp = data.get('timestamp')
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.now()

        return cls(
            id=data.get('id'),
            market_id=data.get('market_id', ''),
            market_slug=data.get('market_slug', ''),
            title=data.get('title', ''),
            probability=float(data.get('probability', 0)),
            volume_24h=float(data.get('volume_24h', 0)),
            liquidity=float(data.get('liquidity', 0)),
            best_bid=float(data.get('best_bid', 0)),
            best_ask=float(data.get('best_ask', 0)),
            spread=float(data.get('spread', 0)),
            timestamp=timestamp,
        )


@dataclass
class ArbitrageOpportunity:
    """Arbitrage opportunity record"""
    id: Optional[int] = None
    market1_id: str = ""
    market2_id: str = ""
    market1_title: str = ""
    market2_title: str = ""
    market1_price: float = 0.0
    market2_price: float = 0.0
    spread: float = 0.0
    expected_profit: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    status: str = "open"  # open, closed, expired

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'market1_id': self.market1_id,
            'market2_id': self.market2_id,
            'market1_title': self.market1_title,
            'market2_title': self.market2_title,
            'market1_price': self.market1_price,
            'market2_price': self.market2_price,
            'spread': self.spread,
            'expected_profit': self.expected_profit,
            'timestamp': self.timestamp.isoformat(),
            'status': self.status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArbitrageOpportunity':
        timestamp = data.get('timestamp')
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.now()

        return cls(
            id=data.get('id'),
            market1_id=data.get('market1_id', ''),
            market2_id=data.get('market2_id', ''),
            market1_title=data.get('market1_title', ''),
            market2_title=data.get('market2_title', ''),
            market1_price=float(data.get('market1_price', 0)),
            market2_price=float(data.get('market2_price', 0)),
            spread=float(data.get('spread', 0)),
            expected_profit=float(data.get('expected_profit', 0)),
            timestamp=timestamp,
            status=data.get('status', 'open'),
        )
