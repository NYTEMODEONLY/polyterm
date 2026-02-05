"""Enhanced whale tracking system with individual wallet tracking"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from collections import defaultdict

from ..db.database import Database
from ..db.models import Wallet, Trade, Alert
from ..api.clob import CLOBClient


class WhaleTracker:
    """
    Enhanced whale tracker that monitors individual wallets via WebSocket.

    Uses maker_address from CLOB WebSocket to track individual traders,
    build wallet profiles, and detect whale/insider patterns.
    """

    def __init__(
        self,
        database: Database,
        clob_client: CLOBClient,
        min_whale_trade: float = 10000,  # Minimum notional for whale classification
        min_smart_money_win_rate: float = 0.70,
        min_smart_money_trades: int = 10,
    ):
        self.db = database
        self.clob = clob_client
        self.min_whale_trade = min_whale_trade
        self.min_smart_money_win_rate = min_smart_money_win_rate
        self.min_smart_money_trades = min_smart_money_trades

        # In-memory caches for fast access
        self.active_wallets: Dict[str, Wallet] = {}
        self.recent_trades: List[Trade] = []
        self.max_recent_trades = 1000

        # Callbacks for whale activity
        self.whale_callbacks: List[Callable[[Trade, Wallet], None]] = []
        self.smart_money_callbacks: List[Callable[[Trade, Wallet], None]] = []

    def add_whale_callback(self, callback: Callable[[Trade, Wallet], None]):
        """Add callback for whale trade events"""
        self.whale_callbacks.append(callback)

    def add_smart_money_callback(self, callback: Callable[[Trade, Wallet], None]):
        """Add callback for smart money trade events"""
        self.smart_money_callbacks.append(callback)

    async def process_trade(self, trade_data: Dict[str, Any]) -> Optional[Trade]:
        """
        Process a trade from WebSocket and track the wallet.

        Args:
            trade_data: Raw trade data from WebSocket

        Returns:
            Trade object if processed, None if skipped
        """
        # Extract wallet address from maker_address or taker_address
        maker_address = trade_data.get('maker_address', trade_data.get('maker', ''))
        taker_address = trade_data.get('taker_address', trade_data.get('taker', ''))

        # Use maker as primary (they provide liquidity)
        wallet_address = maker_address or taker_address
        if not wallet_address:
            return None

        # Parse trade details
        price = float(trade_data.get('price', 0))
        size = float(trade_data.get('size', trade_data.get('amount', 0)))
        notional = price * size if price and size else float(trade_data.get('notional', 0))

        # Get or create trade timestamp
        timestamp = trade_data.get('timestamp')
        if isinstance(timestamp, (int, float)):
            timestamp = datetime.fromtimestamp(timestamp)
        elif isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except Exception:
                timestamp = datetime.now()
        else:
            timestamp = datetime.now()

        # Create trade record
        trade = Trade(
            market_id=trade_data.get('market', trade_data.get('market_id', '')),
            market_slug=trade_data.get('market_slug', ''),
            wallet_address=wallet_address,
            side=trade_data.get('side', 'BUY'),
            outcome=trade_data.get('outcome', ''),
            price=price,
            size=size,
            notional=notional,
            timestamp=timestamp,
            tx_hash=trade_data.get('transactionHash', trade_data.get('tx_hash', '')),
            maker_address=maker_address,
            taker_address=taker_address,
        )

        # Store trade in database
        self.db.insert_trade(trade)

        # Update recent trades cache
        self.recent_trades.append(trade)
        if len(self.recent_trades) > self.max_recent_trades:
            self.recent_trades = self.recent_trades[-self.max_recent_trades:]

        # Update wallet profile
        wallet = await self._update_wallet(wallet_address, trade)

        # Check for whale activity
        if notional >= self.min_whale_trade:
            await self._handle_whale_trade(trade, wallet)

        # Check for smart money activity
        if wallet.is_smart_money():
            await self._handle_smart_money_trade(trade, wallet)

        return trade

    async def _update_wallet(self, address: str, trade: Trade) -> Wallet:
        """Update wallet profile with new trade data"""
        wallet = self.db.get_wallet(address)

        if not wallet:
            # New wallet
            wallet = Wallet(
                address=address,
                first_seen=trade.timestamp,
                total_trades=0,
                total_volume=0.0,
            )

        # Update statistics
        wallet.total_trades += 1
        wallet.total_volume += trade.notional
        wallet.avg_position_size = wallet.total_volume / wallet.total_trades

        if trade.notional > wallet.largest_trade:
            wallet.largest_trade = trade.notional

        # Update favorite markets
        if trade.market_id and trade.market_id not in wallet.favorite_markets:
            wallet.favorite_markets.append(trade.market_id)
            if len(wallet.favorite_markets) > 10:
                wallet.favorite_markets = wallet.favorite_markets[-10:]

        wallet.updated_at = datetime.now()

        # Auto-tag whales
        if wallet.total_volume >= 100000 and 'whale' not in wallet.tags:
            wallet.tags.append('whale')

        # Save to database
        self.db.upsert_wallet(wallet)

        # Cache for fast access
        self.active_wallets[address] = wallet

        return wallet

    async def _handle_whale_trade(self, trade: Trade, wallet: Wallet):
        """Handle whale trade detection"""
        # Create alert
        alert = Alert(
            alert_type='whale',
            market_id=trade.market_id,
            wallet_address=trade.wallet_address,
            severity=min(100, int(trade.notional / 1000)),  # $100k = 100 severity
            message=f"Whale trade: ${trade.notional:,.0f} {trade.side} on {trade.market_id[:20]}",
            data={
                'trade': trade.to_dict(),
                'wallet_volume': wallet.total_volume,
                'wallet_trades': wallet.total_trades,
            },
        )
        self.db.insert_alert(alert)

        # Trigger callbacks
        for callback in self.whale_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(trade, wallet)
                else:
                    callback(trade, wallet)
            except Exception as e:
                print(f"Error in whale callback: {e}")

    async def _handle_smart_money_trade(self, trade: Trade, wallet: Wallet):
        """Handle smart money trade detection"""
        # Create alert
        alert = Alert(
            alert_type='smart_money',
            market_id=trade.market_id,
            wallet_address=trade.wallet_address,
            severity=int(wallet.win_rate * 100),
            message=f"Smart money ({wallet.win_rate:.0%} win rate): ${trade.notional:,.0f} {trade.side}",
            data={
                'trade': trade.to_dict(),
                'wallet_win_rate': wallet.win_rate,
                'wallet_trades': wallet.total_trades,
            },
        )
        self.db.insert_alert(alert)

        # Trigger callbacks
        for callback in self.smart_money_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(trade, wallet)
                else:
                    callback(trade, wallet)
            except Exception as e:
                print(f"Error in smart money callback: {e}")

    def get_whale_leaderboard(self, limit: int = 20) -> List[Wallet]:
        """Get top whale wallets by volume"""
        return self.db.get_whale_wallets(min_volume=self.min_whale_trade)[:limit]

    def get_smart_money_leaderboard(self, limit: int = 20) -> List[Wallet]:
        """Get top smart money wallets by win rate"""
        return self.db.get_smart_money_wallets(
            min_win_rate=self.min_smart_money_win_rate,
            min_trades=self.min_smart_money_trades,
        )[:limit]

    def get_recent_whale_trades(self, hours: int = 24) -> List[Trade]:
        """Get recent large trades"""
        return self.db.get_large_trades(
            min_notional=self.min_whale_trade,
            hours=hours,
        )

    def get_wallet_profile(self, address: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive wallet profile"""
        return self.db.get_wallet_stats(address)

    def track_wallet(self, address: str, tag: str = 'tracked') -> None:
        """Add a wallet to tracked list"""
        self.db.add_wallet_tag(address, tag)

    def untrack_wallet(self, address: str, tag: str = 'tracked') -> None:
        """Remove a wallet from tracked list"""
        self.db.remove_wallet_tag(address, tag)

    def get_tracked_wallets(self) -> List[Wallet]:
        """Get all manually tracked wallets"""
        all_wallets = self.db.get_all_wallets(limit=10000)
        return [w for w in all_wallets if 'tracked' in w.tags]

    async def start_monitoring(self, market_slugs: List[str]):
        """Start monitoring markets for whale activity via WebSocket"""
        async def handle_trade(data):
            await self.process_trade(data)

        await self.clob.subscribe_to_trades(market_slugs, handle_trade)
        await self.clob.listen_for_trades()


class InsiderDetector:
    """
    Detects potential insider trading patterns.

    Detection signals:
    1. Fresh wallet + large bet
    2. Pre-event volume spike
    3. Perfect timing correlation
    4. Wallet cluster analysis
    5. Win rate anomaly
    """

    def __init__(self, database: Database):
        self.db = database

    def calculate_insider_score(self, wallet: Wallet) -> int:
        """
        Calculate insider risk score (0-100).

        Scoring:
        - Wallet age (newer = higher risk): 0-25 points
        - Position size relative to avg: 0-25 points
        - Timing before known events: 0-25 points
        - Win rate deviation: 0-25 points
        """
        score = 0

        # 1. Wallet age score (newer = riskier)
        wallet_age_days = (datetime.now() - wallet.first_seen).days
        if wallet_age_days < 1:
            score += 25  # Brand new wallet
        elif wallet_age_days < 7:
            score += 20
        elif wallet_age_days < 30:
            score += 10
        elif wallet_age_days < 90:
            score += 5

        # 2. Position size score
        if wallet.avg_position_size > 50000:
            score += 25
        elif wallet.avg_position_size > 25000:
            score += 20
        elif wallet.avg_position_size > 10000:
            score += 15
        elif wallet.avg_position_size > 5000:
            score += 10

        # 3. Win rate anomaly (unusually high)
        if wallet.total_trades >= 5:
            if wallet.win_rate > 0.95:
                score += 25  # Almost never loses
            elif wallet.win_rate > 0.85:
                score += 20
            elif wallet.win_rate > 0.75:
                score += 10

        # 4. Trading pattern (few trades, high stakes)
        if wallet.total_trades < 10 and wallet.total_volume > 50000:
            score += 15  # Few trades but big bets

        return min(100, score)

    def analyze_wallet(self, wallet: Wallet) -> Dict[str, Any]:
        """Comprehensive insider analysis for a wallet"""
        score = self.calculate_insider_score(wallet)

        risk_level = 'high' if score >= 70 else 'medium' if score >= 40 else 'low'

        risk_factors = []

        # Check each factor
        wallet_age_days = (datetime.now() - wallet.first_seen).days
        if wallet_age_days < 7:
            risk_factors.append(f"New wallet ({wallet_age_days} days old)")

        if wallet.avg_position_size > 25000:
            risk_factors.append(f"Large avg position (${wallet.avg_position_size:,.0f})")

        if wallet.win_rate > 0.80 and wallet.total_trades >= 5:
            risk_factors.append(f"Anomalous win rate ({wallet.win_rate:.0%})")

        if wallet.total_trades < 10 and wallet.total_volume > 50000:
            risk_factors.append("Few trades, high volume pattern")

        return {
            'address': wallet.address,
            'risk_score': score,
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'wallet_age_days': wallet_age_days,
            'total_trades': wallet.total_trades,
            'total_volume': wallet.total_volume,
            'win_rate': wallet.win_rate,
            'avg_position_size': wallet.avg_position_size,
        }

    def get_suspicious_wallets(self, min_score: int = 70) -> List[Dict[str, Any]]:
        """Get all wallets above suspicious threshold"""
        wallets = self.db.get_all_wallets(limit=10000)
        suspicious = []

        for wallet in wallets:
            analysis = self.analyze_wallet(wallet)
            if analysis['risk_score'] >= min_score:
                suspicious.append(analysis)

        return sorted(suspicious, key=lambda x: x['risk_score'], reverse=True)

    def flag_wallet_as_suspicious(self, address: str) -> None:
        """Flag a wallet as insider suspect"""
        wallet = self.db.get_wallet(address)
        if wallet:
            wallet.risk_score = max(wallet.risk_score, 70)
            self.db.add_wallet_tag(address, 'insider_suspect')
            self.db.upsert_wallet(wallet)

            # Create alert
            alert = Alert(
                alert_type='insider_suspect',
                wallet_address=address,
                severity=wallet.risk_score,
                message=f"Wallet flagged as insider suspect",
                data={'risk_score': wallet.risk_score},
            )
            self.db.insert_alert(alert)

    def check_trade_for_insider_signals(
        self,
        trade: Trade,
        wallet: Wallet,
    ) -> Optional[Alert]:
        """Check if a trade exhibits insider trading signals"""
        signals = []
        severity = 0

        # Signal 1: Fresh wallet with large bet
        wallet_age_days = (datetime.now() - wallet.first_seen).days
        if wallet_age_days < 3 and trade.notional >= 10000:
            signals.append("Fresh wallet with large bet")
            severity += 30

        # Signal 2: First trade is unusually large
        if wallet.total_trades == 1 and trade.notional >= 25000:
            signals.append("First trade is $25k+")
            severity += 25

        # Signal 3: High win rate wallet making another bet
        if wallet.win_rate > 0.90 and wallet.total_trades >= 5:
            signals.append(f"High win rate wallet ({wallet.win_rate:.0%})")
            severity += 20

        if signals:
            return Alert(
                alert_type='insider_signal',
                market_id=trade.market_id,
                wallet_address=wallet.address,
                severity=min(100, severity),
                message=f"Potential insider signals: {', '.join(signals)}",
                data={
                    'signals': signals,
                    'trade': trade.to_dict(),
                    'wallet_age_days': wallet_age_days,
                    'wallet_win_rate': wallet.win_rate,
                },
            )

        return None
