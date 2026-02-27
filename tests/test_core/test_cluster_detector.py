"""Tests for WalletClusterDetector"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from polyterm.core.cluster_detector import WalletClusterDetector
from polyterm.db.models import Trade, Wallet


class TestTimingClusters:
    """Tests for timing correlation detection"""

    def test_detects_correlated_trades(self):
        """Should detect wallets trading within time window"""
        db = MagicMock()
        now = datetime.now()

        # Two wallets trading within 10 seconds of each other, 3 times
        trades = [
            Trade(wallet_address="0xAAA", market_id="m1", timestamp=now, size=100.0, price=0.5),
            Trade(wallet_address="0xBBB", market_id="m1", timestamp=now + timedelta(seconds=5), size=100.0, price=0.5),
            Trade(wallet_address="0xAAA", market_id="m2", timestamp=now + timedelta(minutes=1), size=100.0, price=0.5),
            Trade(wallet_address="0xBBB", market_id="m2", timestamp=now + timedelta(minutes=1, seconds=8), size=100.0, price=0.5),
            Trade(wallet_address="0xAAA", market_id="m3", timestamp=now + timedelta(minutes=2), size=100.0, price=0.5),
            Trade(wallet_address="0xBBB", market_id="m3", timestamp=now + timedelta(minutes=2, seconds=15), size=100.0, price=0.5),
        ]
        db.get_recent_trades.return_value = trades

        detector = WalletClusterDetector(db)
        results = detector.find_timing_clusters(window_seconds=30)

        assert len(results) > 0
        assert results[0][0] in ["0xAAA", "0xBBB"]
        assert results[0][1] in ["0xAAA", "0xBBB"]
        assert results[0][2] >= 3  # At least 3 correlated trades

    def test_ignores_same_wallet_trades(self):
        """Should not correlate trades from same wallet"""
        db = MagicMock()
        now = datetime.now()

        trades = [
            Trade(wallet_address="0xAAA", market_id="m1", timestamp=now, size=100.0, price=0.5),
            Trade(wallet_address="0xAAA", market_id="m2", timestamp=now + timedelta(seconds=5), size=100.0, price=0.5),
            Trade(wallet_address="0xAAA", market_id="m3", timestamp=now + timedelta(seconds=10), size=100.0, price=0.5),
        ]
        db.get_recent_trades.return_value = trades

        detector = WalletClusterDetector(db)
        results = detector.find_timing_clusters(window_seconds=30)

        assert len(results) == 0

    def test_returns_empty_when_no_trades(self):
        """Should return empty list when no trades"""
        db = MagicMock()
        db.get_recent_trades.return_value = []

        detector = WalletClusterDetector(db)
        results = detector.find_timing_clusters()

        assert results == []

    def test_filters_below_threshold(self):
        """Should filter pairs with less than 3 correlated trades"""
        db = MagicMock()
        now = datetime.now()

        # Only 2 correlated trades
        trades = [
            Trade(wallet_address="0xAAA", market_id="m1", timestamp=now, size=100.0, price=0.5),
            Trade(wallet_address="0xBBB", market_id="m1", timestamp=now + timedelta(seconds=5), size=100.0, price=0.5),
            Trade(wallet_address="0xAAA", market_id="m2", timestamp=now + timedelta(minutes=1), size=100.0, price=0.5),
            Trade(wallet_address="0xBBB", market_id="m2", timestamp=now + timedelta(minutes=1, seconds=8), size=100.0, price=0.5),
        ]
        db.get_recent_trades.return_value = trades

        detector = WalletClusterDetector(db)
        results = detector.find_timing_clusters(window_seconds=30)

        assert len(results) == 0

    def test_respects_time_window(self):
        """Should only detect trades within specified time window"""
        db = MagicMock()
        now = datetime.now()

        # Trades outside 10-second window
        trades = [
            Trade(wallet_address="0xAAA", market_id="m1", timestamp=now, size=100.0, price=0.5),
            Trade(wallet_address="0xBBB", market_id="m1", timestamp=now + timedelta(seconds=15), size=100.0, price=0.5),
            Trade(wallet_address="0xAAA", market_id="m2", timestamp=now + timedelta(minutes=1), size=100.0, price=0.5),
            Trade(wallet_address="0xBBB", market_id="m2", timestamp=now + timedelta(minutes=1, seconds=15), size=100.0, price=0.5),
            Trade(wallet_address="0xAAA", market_id="m3", timestamp=now + timedelta(minutes=2), size=100.0, price=0.5),
            Trade(wallet_address="0xBBB", market_id="m3", timestamp=now + timedelta(minutes=2, seconds=15), size=100.0, price=0.5),
        ]
        db.get_recent_trades.return_value = trades

        detector = WalletClusterDetector(db)
        results = detector.find_timing_clusters(window_seconds=10)

        assert len(results) == 0


class TestMarketOverlapClusters:
    """Tests for market overlap detection"""

    def test_detects_high_overlap(self):
        """Should detect wallets trading same markets"""
        db = MagicMock()
        now = datetime.now()

        wallets = [
            Wallet(address="0xAAA", first_seen=now),
            Wallet(address="0xBBB", first_seen=now),
        ]
        db.get_all_wallets.return_value = wallets

        # Both wallets trade same markets
        db.get_trades_by_wallet.side_effect = lambda addr, limit: [
            Trade(wallet_address=addr, market_id="m1", timestamp=now, size=100.0, price=0.5),
            Trade(wallet_address=addr, market_id="m2", timestamp=now, size=100.0, price=0.5),
            Trade(wallet_address=addr, market_id="m3", timestamp=now, size=100.0, price=0.5),
        ]

        detector = WalletClusterDetector(db)
        results = detector.find_market_overlap_clusters(min_overlap=0.7)

        assert len(results) > 0
        assert results[0][2] >= 0.7  # High overlap score

    def test_filters_low_overlap(self):
        """Should filter wallets with low market overlap"""
        db = MagicMock()
        now = datetime.now()

        wallets = [
            Wallet(address="0xAAA", first_seen=now),
            Wallet(address="0xBBB", first_seen=now),
        ]
        db.get_all_wallets.return_value = wallets

        # Different markets, low overlap
        def get_trades(addr, limit):
            if addr == "0xAAA":
                return [
                    Trade(wallet_address=addr, market_id="m1", timestamp=now, size=100.0, price=0.5),
                    Trade(wallet_address=addr, market_id="m2", timestamp=now, size=100.0, price=0.5),
                ]
            else:
                return [
                    Trade(wallet_address=addr, market_id="m3", timestamp=now, size=100.0, price=0.5),
                    Trade(wallet_address=addr, market_id="m4", timestamp=now, size=100.0, price=0.5),
                ]

        db.get_trades_by_wallet.side_effect = get_trades

        detector = WalletClusterDetector(db)
        results = detector.find_market_overlap_clusters(min_overlap=0.7)

        assert len(results) == 0

    def test_requires_at_least_two_markets(self):
        """Should skip wallets with less than 2 markets"""
        db = MagicMock()
        now = datetime.now()

        wallets = [
            Wallet(address="0xAAA", first_seen=now),
            Wallet(address="0xBBB", first_seen=now),
        ]
        db.get_all_wallets.return_value = wallets

        # One wallet has only 1 market
        def get_trades(addr, limit):
            if addr == "0xAAA":
                return [Trade(wallet_address=addr, market_id="m1", timestamp=now, size=100.0, price=0.5)]
            else:
                return [
                    Trade(wallet_address=addr, market_id="m1", timestamp=now, size=100.0, price=0.5),
                    Trade(wallet_address=addr, market_id="m2", timestamp=now, size=100.0, price=0.5),
                ]

        db.get_trades_by_wallet.side_effect = get_trades

        detector = WalletClusterDetector(db)
        results = detector.find_market_overlap_clusters()

        assert len(results) == 0

    def test_returns_empty_for_single_wallet(self):
        """Should return empty when only one wallet"""
        db = MagicMock()
        now = datetime.now()

        wallets = [Wallet(address="0xAAA", first_seen=now)]
        db.get_all_wallets.return_value = wallets

        detector = WalletClusterDetector(db)
        results = detector.find_market_overlap_clusters()

        assert results == []

    def test_boundary_overlap_70_percent(self):
        """Should detect exactly 70% overlap when min_overlap=0.7"""
        db = MagicMock()
        now = datetime.now()

        wallets = [
            Wallet(address="0xAAA", first_seen=now),
            Wallet(address="0xBBB", first_seen=now),
        ]
        db.get_all_wallets.return_value = wallets

        # 70% overlap: 7 common out of 10 total
        def get_trades(addr, limit):
            common_markets = [f"m{i}" for i in range(7)]
            if addr == "0xAAA":
                return [Trade(wallet_address=addr, market_id=m, timestamp=now, size=100.0, price=0.5)
                        for m in common_markets + ["m7", "m8"]]
            else:
                return [Trade(wallet_address=addr, market_id=m, timestamp=now, size=100.0, price=0.5)
                        for m in common_markets + ["m9"]]

        db.get_trades_by_wallet.side_effect = get_trades

        detector = WalletClusterDetector(db)
        results = detector.find_market_overlap_clusters(min_overlap=0.7)

        assert len(results) > 0


class TestSizePatternClusters:
    """Tests for size pattern detection"""

    def test_detects_matching_sizes(self):
        """Should detect wallets using same trade sizes"""
        db = MagicMock()
        now = datetime.now()

        wallets = [
            Wallet(address="0xAAA", first_seen=now),
            Wallet(address="0xBBB", first_seen=now),
        ]
        db.get_all_wallets.return_value = wallets

        # Both use same sizes
        db.get_trades_by_wallet.side_effect = lambda addr, limit: [
            Trade(wallet_address=addr, market_id="m1", timestamp=now, size=100.0, price=0.5),
            Trade(wallet_address=addr, market_id="m2", timestamp=now, size=250.0, price=0.5),
            Trade(wallet_address=addr, market_id="m3", timestamp=now, size=500.0, price=0.5),
        ]

        detector = WalletClusterDetector(db)
        results = detector.find_size_pattern_clusters()

        assert len(results) > 0
        assert results[0][2] >= 3  # At least 3 matching sizes

    def test_returns_empty_when_no_matches(self):
        """Should return empty when no matching sizes"""
        db = MagicMock()
        now = datetime.now()

        wallets = [
            Wallet(address="0xAAA", first_seen=now),
            Wallet(address="0xBBB", first_seen=now),
        ]
        db.get_all_wallets.return_value = wallets

        # Different sizes
        def get_trades(addr, limit):
            if addr == "0xAAA":
                return [
                    Trade(wallet_address=addr, market_id="m1", timestamp=now, size=100.0, price=0.5),
                    Trade(wallet_address=addr, market_id="m2", timestamp=now, size=200.0, price=0.5),
                ]
            else:
                return [
                    Trade(wallet_address=addr, market_id="m1", timestamp=now, size=300.0, price=0.5),
                    Trade(wallet_address=addr, market_id="m2", timestamp=now, size=400.0, price=0.5),
                ]

        db.get_trades_by_wallet.side_effect = get_trades

        detector = WalletClusterDetector(db)
        results = detector.find_size_pattern_clusters()

        assert len(results) == 0

    def test_returns_empty_for_few_wallets(self):
        """Should return empty when less than 2 wallets"""
        db = MagicMock()
        now = datetime.now()

        wallets = [Wallet(address="0xAAA", first_seen=now)]
        db.get_all_wallets.return_value = wallets

        detector = WalletClusterDetector(db)
        results = detector.find_size_pattern_clusters()

        assert results == []

    def test_filters_zero_size_trades(self):
        """Should filter out zero-size trades"""
        db = MagicMock()
        now = datetime.now()

        wallets = [
            Wallet(address="0xAAA", first_seen=now),
            Wallet(address="0xBBB", first_seen=now),
        ]
        db.get_all_wallets.return_value = wallets

        # Include zero-size trades
        db.get_trades_by_wallet.side_effect = lambda addr, limit: [
            Trade(wallet_address=addr, market_id="m1", timestamp=now, size=0.0, price=0.5),
            Trade(wallet_address=addr, market_id="m2", timestamp=now, size=100.0, price=0.5),
        ]

        detector = WalletClusterDetector(db)
        results = detector.find_size_pattern_clusters()

        # Only 1 non-zero size, should not meet threshold of 3
        assert len(results) == 0


class TestClusterScore:
    """Tests for cluster scoring"""

    def test_high_score_all_signals(self):
        """Should give high score when all signals present"""
        db = MagicMock()
        now = datetime.now()

        # Setup timing correlation
        timing_trades = []
        for i in range(5):
            timing_trades.extend([
                Trade(wallet_address="0xAAA", market_id=f"m{i}", timestamp=now + timedelta(minutes=i), size=100.0, price=0.5),
                Trade(wallet_address="0xBBB", market_id=f"m{i}", timestamp=now + timedelta(minutes=i, seconds=5), size=100.0, price=0.5),
            ])
        db.get_recent_trades.return_value = timing_trades

        # Setup market overlap
        db.get_trades_by_wallet.side_effect = lambda addr, limit: [
            Trade(wallet_address=addr, market_id="m1", timestamp=now, size=100.0, price=0.5),
            Trade(wallet_address=addr, market_id="m2", timestamp=now, size=100.0, price=0.5),
            Trade(wallet_address=addr, market_id="m3", timestamp=now, size=250.0, price=0.5),
        ]

        detector = WalletClusterDetector(db)
        result = detector.calculate_cluster_score("0xAAA", "0xBBB")

        assert result['score'] > 70  # High confidence
        assert result['risk'] == 'high'
        assert len(result['signals']) >= 2

    def test_low_score_no_correlation(self):
        """Should give low score when no correlation"""
        db = MagicMock()
        now = datetime.now()

        db.get_recent_trades.return_value = []

        # Different markets
        def get_trades(addr, limit):
            if addr == "0xAAA":
                return [Trade(wallet_address=addr, market_id="m1", timestamp=now, size=100.0, price=0.5)]
            else:
                return [Trade(wallet_address=addr, market_id="m2", timestamp=now, size=200.0, price=0.5)]

        db.get_trades_by_wallet.side_effect = get_trades

        detector = WalletClusterDetector(db)
        result = detector.calculate_cluster_score("0xAAA", "0xBBB")

        assert result['score'] < 40
        assert result['risk'] == 'low'

    def test_medium_score_partial_correlation(self):
        """Should give medium score for partial correlation"""
        db = MagicMock()
        now = datetime.now()

        db.get_recent_trades.return_value = []

        # Same markets but different sizes
        db.get_trades_by_wallet.side_effect = lambda addr, limit: [
            Trade(wallet_address=addr, market_id="m1", timestamp=now, size=100.0 if addr == "0xAAA" else 150.0, price=0.5),
            Trade(wallet_address=addr, market_id="m2", timestamp=now, size=200.0 if addr == "0xAAA" else 250.0, price=0.5),
        ]

        detector = WalletClusterDetector(db)
        result = detector.calculate_cluster_score("0xAAA", "0xBBB")

        assert 30 <= result['score'] <= 70
        assert result['risk'] in ['low', 'medium']

    def test_returns_low_score_for_no_trades(self):
        """Should return low score when wallets have no trades"""
        db = MagicMock()

        db.get_recent_trades.return_value = []
        db.get_trades_by_wallet.return_value = []

        detector = WalletClusterDetector(db)
        result = detector.calculate_cluster_score("0xAAA", "0xBBB")

        assert result['score'] == 0
        assert result['risk'] == 'low'
        assert len(result['signals']) == 0


class TestDetectClusters:
    """Tests for full cluster detection"""

    def test_combines_all_methods(self):
        """Should combine results from all detection methods"""
        db = MagicMock()
        now = datetime.now()

        # Setup timing
        timing_trades = []
        for i in range(5):
            timing_trades.extend([
                Trade(wallet_address="0xAAA", market_id=f"m{i}", timestamp=now + timedelta(minutes=i), size=100.0, price=0.5),
                Trade(wallet_address="0xBBB", market_id=f"m{i}", timestamp=now + timedelta(minutes=i, seconds=5), size=100.0, price=0.5),
            ])
        db.get_recent_trades.return_value = timing_trades

        # Setup market overlap
        wallets = [
            Wallet(address="0xAAA", first_seen=now),
            Wallet(address="0xBBB", first_seen=now),
        ]
        db.get_all_wallets.return_value = wallets

        db.get_trades_by_wallet.side_effect = lambda addr, limit: [
            Trade(wallet_address=addr, market_id="m1", timestamp=now, size=100.0, price=0.5),
            Trade(wallet_address=addr, market_id="m2", timestamp=now, size=100.0, price=0.5),
            Trade(wallet_address=addr, market_id="m3", timestamp=now, size=100.0, price=0.5),
        ]

        detector = WalletClusterDetector(db)
        results = detector.detect_clusters(min_score=60)

        assert len(results) > 0
        assert 'wallets' in results[0]
        assert 'score' in results[0]
        assert 'risk' in results[0]
        assert 'signals' in results[0]

    def test_reuses_precomputed_timing_during_scoring(self):
        """Should not recompute expensive timing scan per wallet pair."""
        db = MagicMock()
        now = datetime.now()

        timing_trades = []
        for i in range(3):
            timing_trades.extend([
                Trade(wallet_address="0xAAA", market_id=f"m{i}", timestamp=now + timedelta(minutes=i), size=100.0, price=0.5),
                Trade(wallet_address="0xBBB", market_id=f"m{i}", timestamp=now + timedelta(minutes=i, seconds=5), size=100.0, price=0.5),
            ])
        db.get_recent_trades.return_value = timing_trades

        db.get_all_wallets.return_value = [
            Wallet(address="0xAAA", first_seen=now),
            Wallet(address="0xBBB", first_seen=now),
        ]
        db.get_trades_by_wallet.side_effect = lambda addr, limit: [
            Trade(wallet_address=addr, market_id="m1", timestamp=now, size=100.0, price=0.5),
            Trade(wallet_address=addr, market_id="m2", timestamp=now, size=200.0, price=0.5),
            Trade(wallet_address=addr, market_id="m3", timestamp=now, size=300.0, price=0.5),
        ]

        detector = WalletClusterDetector(db)
        results = detector.detect_clusters(min_score=0)

        assert len(results) > 0
        assert db.get_recent_trades.call_count == 1

    def test_filters_by_min_score(self):
        """Should filter clusters below minimum score"""
        db = MagicMock()
        now = datetime.now()

        db.get_recent_trades.return_value = []
        db.get_all_wallets.return_value = []

        detector = WalletClusterDetector(db)
        results = detector.detect_clusters(min_score=90)

        assert len(results) == 0

    def test_returns_empty_for_empty_database(self):
        """Should return empty when no wallet data"""
        db = MagicMock()

        db.get_recent_trades.return_value = []
        db.get_all_wallets.return_value = []

        detector = WalletClusterDetector(db)
        results = detector.detect_clusters()

        assert results == []

    def test_sorts_by_score_descending(self):
        """Should sort results by score (highest first)"""
        db = MagicMock()
        now = datetime.now()

        # Create multiple wallet pairs with different correlation levels
        wallets = [
            Wallet(address="0xAAA", first_seen=now),
            Wallet(address="0xBBB", first_seen=now),
            Wallet(address="0xCCC", first_seen=now),
        ]
        db.get_all_wallets.return_value = wallets

        # AAA-BBB high overlap, AAA-CCC low overlap
        def get_trades(addr, limit):
            if addr == "0xAAA":
                return [Trade(wallet_address=addr, market_id=f"m{i}", timestamp=now, size=100.0, price=0.5) for i in range(5)]
            elif addr == "0xBBB":
                return [Trade(wallet_address=addr, market_id=f"m{i}", timestamp=now, size=100.0, price=0.5) for i in range(5)]
            else:
                return [Trade(wallet_address=addr, market_id=f"m{i}", timestamp=now, size=100.0, price=0.5) for i in range(10, 12)]

        db.get_trades_by_wallet.side_effect = get_trades
        db.get_recent_trades.return_value = []

        detector = WalletClusterDetector(db)
        results = detector.detect_clusters(min_score=0)

        if len(results) >= 2:
            assert results[0]['score'] >= results[1]['score']
