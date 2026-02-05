"""
Historical Data API Module

Features:
- Download historical trade data
- OHLCV data generation
- Exportable formats for ML training
- Time range queries
"""

import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path

from ..db.database import Database
from ..db.models import Trade, MarketSnapshot
from ..api.gamma import GammaClient
from ..api.clob import CLOBClient


@dataclass
class OHLCV:
    """Open-High-Low-Close-Volume candle"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    trade_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'trade_count': self.trade_count,
        }


@dataclass
class HistoricalData:
    """Historical data for a market"""
    market_id: str
    market_title: str
    start_time: datetime
    end_time: datetime
    trades: List[Trade] = field(default_factory=list)
    snapshots: List[MarketSnapshot] = field(default_factory=list)
    ohlcv: List[OHLCV] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'market_id': self.market_id,
            'market_title': self.market_title,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'trade_count': len(self.trades),
            'snapshot_count': len(self.snapshots),
            'candle_count': len(self.ohlcv),
            'trades': [t.to_dict() for t in self.trades],
            'snapshots': [s.to_dict() for s in self.snapshots],
            'ohlcv': [c.to_dict() for c in self.ohlcv],
        }


class HistoricalDataAPI:
    """
    API for historical market data.

    Provides:
    - Trade history retrieval
    - OHLCV candle generation
    - Data export for ML/backtesting
    """

    def __init__(
        self,
        database: Database,
        gamma_client: Optional[GammaClient] = None,
        clob_client: Optional[CLOBClient] = None,
    ):
        self.db = database
        self.gamma = gamma_client
        self.clob = clob_client

    def get_trades(
        self,
        market_id: Optional[str] = None,
        wallet_address: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        min_notional: float = 0,
        limit: int = 10000,
    ) -> List[Trade]:
        """
        Get historical trades with filters.

        Args:
            market_id: Filter by market
            wallet_address: Filter by wallet
            start_time: Start of time range
            end_time: End of time range
            min_notional: Minimum trade size
            limit: Maximum records

        Returns:
            List of trades
        """
        if market_id:
            trades = self.db.get_trades_by_market(market_id, limit=limit)
        elif wallet_address:
            trades = self.db.get_trades_by_wallet(wallet_address, limit=limit)
        else:
            # Get all recent trades
            hours = 24 * 30  # Default 30 days
            if start_time:
                hours = int((datetime.now() - start_time).total_seconds() / 3600)
            trades = self.db.get_recent_trades(hours=hours, limit=limit)

        # Apply filters
        if start_time:
            trades = [t for t in trades if t.timestamp >= start_time]
        if end_time:
            trades = [t for t in trades if t.timestamp <= end_time]
        if min_notional > 0:
            trades = [t for t in trades if t.notional >= min_notional]

        return sorted(trades, key=lambda t: t.timestamp)

    def get_snapshots(
        self,
        market_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 10000,
    ) -> List[MarketSnapshot]:
        """
        Get historical market snapshots.

        Args:
            market_id: Market ID
            start_time: Start of time range
            end_time: End of time range
            limit: Maximum records

        Returns:
            List of snapshots
        """
        hours = 24 * 30  # Default 30 days
        if start_time:
            hours = int((datetime.now() - start_time).total_seconds() / 3600)

        snapshots = self.db.get_market_history(market_id, hours=hours, limit=limit)

        # Apply filters
        if start_time:
            snapshots = [s for s in snapshots if s.timestamp >= start_time]
        if end_time:
            snapshots = [s for s in snapshots if s.timestamp <= end_time]

        return sorted(snapshots, key=lambda s: s.timestamp)

    def generate_ohlcv(
        self,
        market_id: str,
        interval: str = '1h',
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[OHLCV]:
        """
        Generate OHLCV candles from trade data.

        Args:
            market_id: Market ID
            interval: Candle interval (1m, 5m, 15m, 1h, 4h, 1d)
            start_time: Start time
            end_time: End time

        Returns:
            List of OHLCV candles
        """
        # Parse interval
        interval_seconds = self._parse_interval(interval)

        # Get trades
        trades = self.get_trades(
            market_id=market_id,
            start_time=start_time,
            end_time=end_time,
        )

        if not trades:
            return []

        # Generate candles
        candles = []
        current_candle_start = None
        current_trades = []

        for trade in trades:
            # Calculate candle timestamp (floor to interval)
            candle_ts = self._floor_timestamp(trade.timestamp, interval_seconds)

            if current_candle_start is None:
                current_candle_start = candle_ts
                current_trades = [trade]
            elif candle_ts == current_candle_start:
                current_trades.append(trade)
            else:
                # Finalize current candle
                if current_trades:
                    candle = self._create_candle(current_candle_start, current_trades)
                    candles.append(candle)

                # Start new candle
                current_candle_start = candle_ts
                current_trades = [trade]

        # Finalize last candle
        if current_trades:
            candle = self._create_candle(current_candle_start, current_trades)
            candles.append(candle)

        return candles

    def _parse_interval(self, interval: str) -> int:
        """Parse interval string to seconds"""
        multipliers = {
            'm': 60,
            'h': 3600,
            'd': 86400,
        }

        unit = interval[-1]
        value = int(interval[:-1])

        return value * multipliers.get(unit, 3600)

    def _floor_timestamp(self, ts: datetime, interval_seconds: int) -> datetime:
        """Floor timestamp to interval boundary"""
        epoch = ts.timestamp()
        floored = (epoch // interval_seconds) * interval_seconds
        return datetime.fromtimestamp(floored)

    def _create_candle(self, timestamp: datetime, trades: List[Trade]) -> OHLCV:
        """Create OHLCV candle from trades"""
        prices = [t.price for t in trades if t.price > 0]

        if not prices:
            return OHLCV(
                timestamp=timestamp,
                open=0, high=0, low=0, close=0,
                volume=0, trade_count=0,
            )

        return OHLCV(
            timestamp=timestamp,
            open=prices[0],
            high=max(prices),
            low=min(prices),
            close=prices[-1],
            volume=sum(t.notional for t in trades),
            trade_count=len(trades),
        )

    def get_historical_data(
        self,
        market_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        include_trades: bool = True,
        include_snapshots: bool = True,
        include_ohlcv: bool = True,
        ohlcv_interval: str = '1h',
    ) -> HistoricalData:
        """
        Get comprehensive historical data for a market.

        Args:
            market_id: Market ID
            start_time: Start time (default: 30 days ago)
            end_time: End time (default: now)
            include_trades: Include trade data
            include_snapshots: Include snapshots
            include_ohlcv: Generate OHLCV candles
            ohlcv_interval: OHLCV interval

        Returns:
            HistoricalData object with all requested data
        """
        if not start_time:
            start_time = datetime.now() - timedelta(days=30)
        if not end_time:
            end_time = datetime.now()

        # Get market title
        market_title = market_id
        if self.gamma:
            try:
                markets = self.gamma.get_markets(limit=1, market_id=market_id)
                if markets:
                    market_title = markets[0].get('title', market_id)
            except Exception:
                pass

        data = HistoricalData(
            market_id=market_id,
            market_title=market_title,
            start_time=start_time,
            end_time=end_time,
        )

        if include_trades:
            data.trades = self.get_trades(
                market_id=market_id,
                start_time=start_time,
                end_time=end_time,
            )

        if include_snapshots:
            data.snapshots = self.get_snapshots(
                market_id=market_id,
                start_time=start_time,
                end_time=end_time,
            )

        if include_ohlcv:
            data.ohlcv = self.generate_ohlcv(
                market_id=market_id,
                interval=ohlcv_interval,
                start_time=start_time,
                end_time=end_time,
            )

        return data

    def export_csv(
        self,
        data: HistoricalData,
        output_path: str,
        data_type: str = 'ohlcv',
    ) -> str:
        """
        Export historical data to CSV.

        Args:
            data: HistoricalData object
            output_path: Output file path
            data_type: Type of data to export (ohlcv, trades, snapshots)

        Returns:
            Path to exported file
        """
        import csv

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if data_type == 'ohlcv':
            with open(path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'open', 'high', 'low', 'close', 'volume', 'trade_count'])
                for candle in data.ohlcv:
                    writer.writerow([
                        candle.timestamp.isoformat(),
                        candle.open,
                        candle.high,
                        candle.low,
                        candle.close,
                        candle.volume,
                        candle.trade_count,
                    ])

        elif data_type == 'trades':
            with open(path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'market_id', 'wallet', 'side', 'price', 'size', 'notional'])
                for trade in data.trades:
                    writer.writerow([
                        trade.timestamp.isoformat(),
                        trade.market_id,
                        trade.wallet_address,
                        trade.side,
                        trade.price,
                        trade.size,
                        trade.notional,
                    ])

        elif data_type == 'snapshots':
            with open(path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'probability', 'volume_24h', 'liquidity', 'spread'])
                for snap in data.snapshots:
                    writer.writerow([
                        snap.timestamp.isoformat(),
                        snap.probability,
                        snap.volume_24h,
                        snap.liquidity,
                        snap.spread,
                    ])

        return str(path)

    def export_json(
        self,
        data: HistoricalData,
        output_path: str,
    ) -> str:
        """
        Export historical data to JSON.

        Args:
            data: HistoricalData object
            output_path: Output file path

        Returns:
            Path to exported file
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w') as f:
            json.dump(data.to_dict(), f, indent=2)

        return str(path)

    def get_statistics(
        self,
        market_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Calculate statistics for a market over time period.

        Args:
            market_id: Market ID
            start_time: Start time
            end_time: End time

        Returns:
            Statistics dictionary
        """
        trades = self.get_trades(
            market_id=market_id,
            start_time=start_time,
            end_time=end_time,
        )

        if not trades:
            return {
                'market_id': market_id,
                'trade_count': 0,
                'error': 'No trades found',
            }

        prices = [t.price for t in trades if t.price > 0]
        volumes = [t.notional for t in trades]

        # Calculate returns
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                ret = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(ret)

        return {
            'market_id': market_id,
            'start_time': start_time.isoformat() if start_time else None,
            'end_time': end_time.isoformat() if end_time else None,
            'trade_count': len(trades),
            'total_volume': sum(volumes),
            'avg_trade_size': sum(volumes) / len(volumes) if volumes else 0,
            'price': {
                'first': prices[0] if prices else 0,
                'last': prices[-1] if prices else 0,
                'high': max(prices) if prices else 0,
                'low': min(prices) if prices else 0,
                'avg': sum(prices) / len(prices) if prices else 0,
                'change': (prices[-1] - prices[0]) if prices else 0,
                'change_pct': ((prices[-1] - prices[0]) / prices[0] * 100) if prices and prices[0] > 0 else 0,
            },
            'returns': {
                'avg': sum(returns) / len(returns) if returns else 0,
                'volatility': self._calculate_volatility(returns),
                'max': max(returns) if returns else 0,
                'min': min(returns) if returns else 0,
            },
        }

    def _calculate_volatility(self, returns: List[float]) -> float:
        """Calculate standard deviation of returns"""
        if len(returns) < 2:
            return 0.0

        avg = sum(returns) / len(returns)
        variance = sum((r - avg) ** 2 for r in returns) / len(returns)
        return variance ** 0.5
