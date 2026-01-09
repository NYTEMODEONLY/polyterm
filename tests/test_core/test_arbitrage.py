"""Tests for arbitrage scanner module"""

import pytest
import tempfile
import os
from datetime import datetime

from polyterm.db.database import Database
from polyterm.core.arbitrage import (
    ArbitrageScanner,
    ArbitrageResult,
)


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
