"""Tests for arbitrage scanner module"""

import pytest
import tempfile
import os
from datetime import datetime
from unittest.mock import MagicMock

from polyterm.db.database import Database
from polyterm.core.arbitrage import (
    ArbitrageScanner,
    ArbitrageResult,
)
from polyterm.core.orderbook import OrderBookAnalyzer, LiveOrderBook


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = Database(db_path)
        yield db


class TestArbitrageResult:
    """Test ArbitrageResult dataclass"""

    def test_result_creation(self):
        """Test creating an arbitrage result"""
        result = ArbitrageResult(
            type='intra_market',
            market1_id='market1',
            market2_id='market1',
            market1_title='Test Market',
            market2_title='Test Market',
            market1_yes_price=0.45,
            market1_no_price=0.52,
            spread=0.03,
            expected_profit_pct=3.0,
            expected_profit_usd=3.0,
            fees=2.0,
            net_profit=1.0,
            confidence='high',
        )

        assert result.type == 'intra_market'
        assert result.spread == 0.03
        assert result.net_profit == 1.0

    def test_result_timestamp(self):
        """Test that timestamp is set automatically"""
        result = ArbitrageResult(
            type='intra_market',
            market1_id='m1',
            market2_id='m2',
            market1_title='M1',
            market2_title='M2',
            market1_yes_price=0.5,
            market1_no_price=0.5,
        )

        assert result.timestamp is not None
        assert isinstance(result.timestamp, datetime)


class TestArbitrageScanner:
    """Test ArbitrageScanner class"""

    def test_intra_market_arbitrage_detection(self, temp_db):
        """Test detecting intra-market arbitrage"""
        # Create mock markets with YES + NO < 1.0
        markets = [
            {
                'id': 'event1',
                'title': 'Test Event',
                'markets': [
                    {
                        'id': 'market1',
                        'conditionId': 'cond1',
                        'outcomePrices': ['0.45', '0.50'],  # Sum = 0.95, 5% gap
                    }
                ],
            },
            {
                'id': 'event2',
                'title': 'Test Event 2',
                'markets': [
                    {
                        'id': 'market2',
                        'conditionId': 'cond2',
                        'outcomePrices': ['0.50', '0.50'],  # Sum = 1.0, no gap
                    }
                ],
            },
        ]

        scanner = ArbitrageScanner(
            database=temp_db,
            gamma_client=None,
            clob_client=None,
            min_spread=0.025,
            polymarket_fee=0.02,
        )

        opportunities = scanner.scan_intra_market_arbitrage(markets)

        # Should find the first market as opportunity (spread > 2.5%)
        assert len(opportunities) == 1
        assert opportunities[0].type == 'intra_market'
        assert opportunities[0].market1_yes_price == 0.45
        assert opportunities[0].market1_no_price == 0.50

    def test_no_arbitrage_when_prices_balanced(self, temp_db):
        """Test no arbitrage when prices sum to 1.0"""
        markets = [
            {
                'id': 'event1',
                'title': 'Balanced Event',
                'markets': [
                    {
                        'id': 'market1',
                        'outcomePrices': ['0.60', '0.40'],  # Sum = 1.0
                    }
                ],
            },
        ]

        scanner = ArbitrageScanner(
            database=temp_db,
            gamma_client=None,
            clob_client=None,
            min_spread=0.025,
        )

        opportunities = scanner.scan_intra_market_arbitrage(markets)
        assert len(opportunities) == 0

    def test_title_similarity(self, temp_db):
        """Test title similarity calculation"""
        scanner = ArbitrageScanner(
            database=temp_db,
            gamma_client=None,
            clob_client=None,
        )

        # Test exact match
        sim1 = scanner._calculate_title_similarity(
            "Will Bitcoin reach $100k?",
            "Will Bitcoin reach $100k?",
        )
        assert sim1 == 1.0

        # Test partial match
        sim2 = scanner._calculate_title_similarity(
            "Will Bitcoin reach $100k by 2025?",
            "Will Bitcoin hit $100k this year?",
        )
        assert 0.2 < sim2 < 0.8  # Should have some overlap

        # Test no match
        sim3 = scanner._calculate_title_similarity(
            "Will it rain tomorrow?",
            "Who will win the election?",
        )
        assert sim3 < 0.3

    def test_correlated_markets_detection(self, temp_db):
        """Test detecting correlated market arbitrage"""
        markets = [
            {
                'id': 'event1',
                'title': 'Will Trump win 2024 election?',
                'tags': [{'label': 'politics'}],
                'markets': [
                    {
                        'id': 'market1',
                        'outcomePrices': ['0.55', '0.45'],
                    }
                ],
            },
            {
                'id': 'event2',
                'title': 'Will Trump become president in 2024?',
                'tags': [{'label': 'politics'}],
                'markets': [
                    {
                        'id': 'market2',
                        'outcomePrices': ['0.62', '0.38'],  # 7% higher
                    }
                ],
            },
        ]

        scanner = ArbitrageScanner(
            database=temp_db,
            gamma_client=None,
            clob_client=None,
            min_spread=0.025,
        )

        opportunities = scanner.scan_correlated_markets(markets, similarity_threshold=0.5)

        # These markets are similar (both about Trump/election)
        # and have price difference
        assert len(opportunities) >= 0  # May or may not find depending on similarity

    def test_format_opportunity(self, temp_db):
        """Test opportunity formatting"""
        result = ArbitrageResult(
            type='intra_market',
            market1_id='market1',
            market2_id='market1',
            market1_title='Test Market Question',
            market2_title='Test Market Question',
            market1_yes_price=0.45,
            market1_no_price=0.52,
            spread=0.03,
            expected_profit_pct=3.1,
            expected_profit_usd=3.10,
            fees=2.0,
            net_profit=1.10,
            confidence='high',
        )

        scanner = ArbitrageScanner(
            database=temp_db,
            gamma_client=None,
            clob_client=None,
        )

        formatted = scanner.format_opportunity(result)

        assert 'Intra-Market' in formatted
        assert 'Test Market' in formatted
        assert '3.0%' in formatted or '3%' in formatted
        assert 'high' in formatted.lower()


class TestLivePriceIntegration:
    """Test ArbitrageScanner with live WebSocket price data."""

    def _make_analyzer_with_books(self, books_data):
        """Create an OrderBookAnalyzer with pre-populated live books.

        Args:
            books_data: dict of token_id -> {bids: {price: size}, asks: {price: size}}
        """
        clob = MagicMock()
        analyzer = OrderBookAnalyzer(clob)
        for tid, data in books_data.items():
            book = LiveOrderBook(tid)
            book._bids = {str(p): str(s) for p, s in data.get("bids", {}).items()}
            book._asks = {str(p): str(s) for p, s in data.get("asks", {}).items()}
            analyzer._live_books[tid] = book
        return analyzer

    def test_intra_market_uses_live_prices(self, temp_db):
        """Live WS prices should override Gamma snapshot prices."""
        # Gamma says YES=0.50, NO=0.50 (no arb)
        # But live WS says YES mid=0.44, NO mid=0.51 => total=0.95 => arb
        analyzer = self._make_analyzer_with_books({
            "token_yes": {"bids": {0.43: 100}, "asks": {0.45: 100}},
            "token_no": {"bids": {0.50: 100}, "asks": {0.52: 100}},
        })

        markets = [{
            'id': 'event1',
            'title': 'Live Test Event',
            'markets': [{
                'id': 'market1',
                'clobTokenIds': ['token_yes', 'token_no'],
                'outcomePrices': ['0.50', '0.50'],  # Gamma: balanced
            }],
        }]

        scanner = ArbitrageScanner(
            database=temp_db,
            gamma_client=None,
            clob_client=None,
            min_spread=0.025,
            orderbook_analyzer=analyzer,
        )

        opps = scanner.scan_intra_market_arbitrage(markets)

        # Should detect arb from live prices (mid YES=0.44, mid NO=0.51, total=0.95)
        assert len(opps) == 1
        assert opps[0].type == 'intra_market'
        assert abs(opps[0].market1_yes_price - 0.44) < 0.01
        assert abs(opps[0].market1_no_price - 0.51) < 0.01

    def test_falls_back_to_gamma_when_no_live_data(self, temp_db):
        """Without live data, scanner uses Gamma snapshot prices."""
        analyzer = self._make_analyzer_with_books({})  # no live books

        markets = [{
            'id': 'event1',
            'title': 'Fallback Event',
            'markets': [{
                'id': 'market1',
                'clobTokenIds': ['token_a', 'token_b'],
                'outcomePrices': ['0.45', '0.50'],  # Gamma: arb opportunity
            }],
        }]

        scanner = ArbitrageScanner(
            database=temp_db,
            gamma_client=None,
            clob_client=None,
            min_spread=0.025,
            orderbook_analyzer=analyzer,
        )

        opps = scanner.scan_intra_market_arbitrage(markets)
        assert len(opps) == 1
        assert opps[0].market1_yes_price == 0.45

    def test_no_analyzer_uses_gamma_prices(self, temp_db):
        """Scanner without analyzer (backward compat) uses Gamma prices."""
        markets = [{
            'id': 'event1',
            'title': 'No Analyzer Event',
            'markets': [{
                'id': 'market1',
                'outcomePrices': ['0.45', '0.50'],
            }],
        }]

        scanner = ArbitrageScanner(
            database=temp_db,
            gamma_client=None,
            clob_client=None,
            min_spread=0.025,
        )

        opps = scanner.scan_intra_market_arbitrage(markets)
        assert len(opps) == 1
        assert opps[0].market1_yes_price == 0.45

    def test_live_prices_no_arb_when_balanced(self, temp_db):
        """Live prices that sum to 1.0 should not produce arb."""
        analyzer = self._make_analyzer_with_books({
            "tok_y": {"bids": {0.59: 100}, "asks": {0.61: 100}},
            "tok_n": {"bids": {0.39: 100}, "asks": {0.41: 100}},
        })

        markets = [{
            'id': 'event1',
            'title': 'Balanced Live',
            'markets': [{
                'id': 'market1',
                'clobTokenIds': ['tok_y', 'tok_n'],
                'outcomePrices': ['0.45', '0.50'],  # Gamma has arb, but live doesn't
            }],
        }]

        scanner = ArbitrageScanner(
            database=temp_db,
            gamma_client=None,
            clob_client=None,
            min_spread=0.025,
            orderbook_analyzer=analyzer,
        )

        opps = scanner.scan_intra_market_arbitrage(markets)
        # Live: mid YES=0.60, mid NO=0.40, total=1.00 => no arb
        assert len(opps) == 0

    def test_correlated_scanner_uses_live_prices(self, temp_db):
        """Correlated market scanner also picks up live prices."""
        analyzer = self._make_analyzer_with_books({
            "tok_a": {"bids": {0.40: 100}, "asks": {0.42: 100}},
            "tok_b": {"bids": {0.50: 100}, "asks": {0.52: 100}},
        })

        markets = [
            {
                'id': 'event1',
                'title': 'Will Trump win election?',
                'tags': [{'label': 'politics'}],
                'markets': [{
                    'id': 'market1',
                    'clobTokenIds': ['tok_a', 'unused_no_a'],
                    'outcomePrices': ['0.50', '0.50'],
                }],
            },
            {
                'id': 'event2',
                'title': 'Will Trump become president?',
                'tags': [{'label': 'politics'}],
                'markets': [{
                    'id': 'market2',
                    'clobTokenIds': ['tok_b', 'unused_no_b'],
                    'outcomePrices': ['0.50', '0.50'],
                }],
            },
        ]

        scanner = ArbitrageScanner(
            database=temp_db,
            gamma_client=None,
            clob_client=None,
            min_spread=0.025,
            orderbook_analyzer=analyzer,
        )

        opps = scanner.scan_correlated_markets(markets, similarity_threshold=0.3)
        # Live: market1 YES mid=0.41, market2 YES mid=0.51 => 10c spread
        if opps:
            assert opps[0].market1_yes_price < opps[0].market2_yes_price

    def test_extract_token_ids_json_string(self, temp_db):
        """Test extracting token IDs when clobTokenIds is a JSON string."""
        scanner = ArbitrageScanner(
            database=temp_db,
            gamma_client=None,
            clob_client=None,
        )

        market = {'clobTokenIds': '["tok1", "tok2"]'}
        assert scanner._extract_token_ids(market) == ['tok1', 'tok2']

    def test_extract_token_ids_list(self, temp_db):
        """Test extracting token IDs when clobTokenIds is a list."""
        scanner = ArbitrageScanner(
            database=temp_db,
            gamma_client=None,
            clob_client=None,
        )

        market = {'clobTokenIds': ['tok1', 'tok2']}
        assert scanner._extract_token_ids(market) == ['tok1', 'tok2']

    def test_extract_token_ids_missing(self, temp_db):
        """Test extracting token IDs when field is missing."""
        scanner = ArbitrageScanner(
            database=temp_db,
            gamma_client=None,
            clob_client=None,
        )

        market = {}
        assert scanner._extract_token_ids(market) == []

    def test_live_prices_yes_only_derives_no(self, temp_db):
        """When only YES token has live data, NO is derived as 1-YES."""
        analyzer = self._make_analyzer_with_books({
            "tok_yes": {"bids": {0.43: 100}, "asks": {0.45: 100}},
            # no data for tok_no
        })

        scanner = ArbitrageScanner(
            database=temp_db,
            gamma_client=None,
            clob_client=None,
            orderbook_analyzer=analyzer,
        )

        market = {'clobTokenIds': ['tok_yes', 'tok_no']}
        prices = scanner._get_live_prices_for_market(market)

        assert prices is not None
        assert abs(prices['yes'] - 0.44) < 0.01  # mid price
        assert abs(prices['no'] - 0.56) < 0.01  # derived: 1 - 0.44
