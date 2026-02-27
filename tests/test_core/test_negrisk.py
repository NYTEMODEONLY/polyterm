"""Tests for NegRisk Multi-Outcome Arbitrage Detection"""

import json
from unittest.mock import Mock, patch
from datetime import datetime

import pytest

from polyterm.core.negrisk import NegRiskAnalyzer


# Fixtures

@pytest.fixture
def mock_gamma_client():
    """Mock GammaClient"""
    client = Mock()
    return client


@pytest.fixture
def mock_clob_client():
    """Mock CLOBClient"""
    client = Mock()
    return client


@pytest.fixture
def analyzer(mock_gamma_client, mock_clob_client):
    """NegRiskAnalyzer instance with mocked clients"""
    return NegRiskAnalyzer(
        gamma_client=mock_gamma_client,
        clob_client=mock_clob_client,
        polymarket_fee=0.02
    )


# Helper functions

def create_market(market_id, question, yes_price, no_price=None):
    """Create mock market dict with Gamma API format"""
    if no_price is None:
        no_price = 1.0 - yes_price
    return {
        'id': market_id,
        'conditionId': market_id,
        'question': question,
        'groupItemTitle': question,
        'outcomePrices': json.dumps([str(yes_price), str(no_price)]),
        'clobTokenIds': json.dumps([f'token_{market_id}']),
    }


def create_flat_market(market_id, question, yes_price, event_id, event_title, no_price=None):
    """Create flat Gamma /markets row with event metadata."""
    market = create_market(market_id, question, yes_price, no_price=no_price)
    market['events'] = [{
        'id': event_id,
        'title': event_title,
        'slug': f'{event_id}-slug',
    }]
    return market


def create_event(event_id, title, markets):
    """Create mock event dict"""
    return {
        'id': event_id,
        'title': title,
        'markets': markets,
    }


# Test Classes

class TestNegRiskFindMultiOutcomeEvents:
    """Test finding events with 3+ markets"""

    def test_finds_events_with_three_or_more_markets(self, analyzer, mock_gamma_client):
        """Should return events with 3+ markets"""
        events = [
            create_event('e1', 'Event 1', [create_market('m1', 'A', 0.3), create_market('m2', 'B', 0.3), create_market('m3', 'C', 0.3)]),
            create_event('e2', 'Event 2', [create_market('m4', 'D', 0.5)]),  # Only 1 market
            create_event('e3', 'Event 3', [create_market('m5', 'E', 0.25), create_market('m6', 'F', 0.25), create_market('m7', 'G', 0.25), create_market('m8', 'H', 0.25)]),
        ]
        mock_gamma_client.get_markets.return_value = events

        result = analyzer.find_multi_outcome_events(limit=10)

        assert len(result) == 2
        assert result[0]['id'] == 'e1'
        assert result[1]['id'] == 'e3'

    def test_excludes_two_market_events(self, analyzer, mock_gamma_client):
        """Should exclude standard binary events (2 markets)"""
        events = [
            create_event('e1', 'Binary Event', [create_market('m1', 'YES', 0.5), create_market('m2', 'NO', 0.5)]),
            create_event('e2', 'Multi Event', [create_market('m3', 'A', 0.3), create_market('m4', 'B', 0.3), create_market('m5', 'C', 0.3)]),
        ]
        mock_gamma_client.get_markets.return_value = events

        result = analyzer.find_multi_outcome_events(limit=10)

        assert len(result) == 1
        assert result[0]['id'] == 'e2'

    def test_respects_limit(self, analyzer, mock_gamma_client):
        """Should respect limit parameter"""
        events = [
            create_event(f'e{i}', f'Event {i}', [create_market(f'm{i}_{j}', f'{j}', 0.25) for j in range(4)])
            for i in range(10)
        ]
        mock_gamma_client.get_markets.return_value = events

        result = analyzer.find_multi_outcome_events(limit=3)

        assert len(result) == 3

    def test_handles_empty_markets(self, analyzer, mock_gamma_client):
        """Should handle events with empty markets list"""
        events = [
            create_event('e1', 'Empty Event', []),
            create_event('e2', 'Valid Event', [create_market('m1', 'A', 0.3), create_market('m2', 'B', 0.3), create_market('m3', 'C', 0.3)]),
        ]
        mock_gamma_client.get_markets.return_value = events

        result = analyzer.find_multi_outcome_events(limit=10)

        assert len(result) == 1
        assert result[0]['id'] == 'e2'

    def test_groups_flat_market_payload_by_event(self, analyzer, mock_gamma_client):
        """Should group flat /markets rows by event and return 3+ outcome events."""
        flat_markets = [
            create_flat_market('m1', 'A', 0.31, 'event_1', 'Event 1'),
            create_flat_market('m2', 'B', 0.29, 'event_1', 'Event 1'),
            create_flat_market('m3', 'C', 0.28, 'event_1', 'Event 1'),
            create_flat_market('m4', 'X', 0.60, 'event_2', 'Event 2'),
            create_flat_market('m5', 'Y', 0.35, 'event_2', 'Event 2'),
        ]
        mock_gamma_client.get_markets.return_value = flat_markets

        result = analyzer.find_multi_outcome_events(limit=10)

        assert len(result) == 1
        assert result[0]['id'] == 'event_1'
        assert result[0]['title'] == 'Event 1'
        assert len(result[0]['markets']) == 3


class TestNegRiskAnalyzeEvent:
    """Test analyzing individual events for arbitrage"""

    def test_detects_underpriced_event(self, analyzer):
        """Should detect when sum of YES prices < $1.00"""
        event = create_event('e1', 'Underpriced Event', [
            create_market('m1', 'Candidate A', 0.30),
            create_market('m2', 'Candidate B', 0.25),
            create_market('m3', 'Candidate C', 0.20),
        ])

        result = analyzer.analyze_event(event)

        assert result is not None
        assert result['type'] == 'underpriced'
        assert result['total_yes_price'] == 0.75
        assert result['spread'] == 0.25
        assert result['num_outcomes'] == 3
        assert result['fee_adjusted_profit'] > 0

    def test_detects_overpriced_event(self, analyzer):
        """Should detect when sum of YES prices > $1.00"""
        event = create_event('e1', 'Overpriced Event', [
            create_market('m1', 'Candidate A', 0.40),
            create_market('m2', 'Candidate B', 0.35),
            create_market('m3', 'Candidate C', 0.30),
        ])

        result = analyzer.analyze_event(event)

        assert result is not None
        assert result['type'] == 'overpriced'
        assert result['total_yes_price'] == 1.05
        assert result['spread'] == 0.05
        assert result['fee_adjusted_profit'] < 0

    def test_calculates_fee_adjusted_profit(self, analyzer):
        """Should calculate fee-adjusted profit correctly"""
        # Underpriced: sum = 0.90, spread = 0.10
        # Fee on cheapest outcome (0.25): 2% of (1.0 - 0.25) = 0.015
        # Net profit = 0.10 - 0.015 = 0.085
        event = create_event('e1', 'Event', [
            create_market('m1', 'A', 0.35),
            create_market('m2', 'B', 0.30),
            create_market('m3', 'C', 0.25),
        ])

        result = analyzer.analyze_event(event)

        assert result is not None
        assert result['total_yes_price'] == 0.90
        expected_profit = 0.10 - (0.02 * 0.75)
        assert abs(result['fee_adjusted_profit'] - expected_profit) < 0.001

    def test_handles_two_market_event(self, analyzer):
        """Should return None for events with < 2 markets (after checking)"""
        event = create_event('e1', 'Single Market Event', [
            create_market('m1', 'Only Option', 0.50),
        ])

        result = analyzer.analyze_event(event)

        assert result is None

    def test_handles_missing_outcome_prices(self, analyzer):
        """Should skip markets with missing outcomePrices"""
        event = create_event('e1', 'Event', [
            create_market('m1', 'A', 0.30),
            {'id': 'm2', 'question': 'B'},  # No outcomePrices
            create_market('m3', 'C', 0.30),
        ])

        result = analyzer.analyze_event(event)

        assert result is not None
        assert result['num_outcomes'] == 2
        assert result['total_yes_price'] == 0.60

    def test_parses_string_outcome_prices(self, analyzer):
        """Should parse outcomePrices when it's a JSON string"""
        event = create_event('e1', 'Event', [
            create_market('m1', 'A', 0.33),
            create_market('m2', 'B', 0.33),
            create_market('m3', 'C', 0.33),
        ])

        result = analyzer.analyze_event(event)

        assert result is not None
        assert result['num_outcomes'] == 3
        assert abs(result['total_yes_price'] - 0.99) < 0.01

    def test_handles_empty_outcomes(self, analyzer):
        """Should return None when no valid outcomes found"""
        event = create_event('e1', 'Event', [
            {'id': 'm1', 'question': 'A'},  # No outcomePrices
            {'id': 'm2', 'question': 'B'},  # No outcomePrices
        ])

        result = analyzer.analyze_event(event)

        assert result is None

    def test_includes_all_required_fields(self, analyzer):
        """Should include all required fields in result"""
        event = create_event('e1', 'Test Event', [
            create_market('m1', 'A', 0.30),
            create_market('m2', 'B', 0.30),
            create_market('m3', 'C', 0.30),
        ])

        result = analyzer.analyze_event(event)

        assert 'event_title' in result
        assert 'event_id' in result
        assert 'num_outcomes' in result
        assert 'total_yes_price' in result
        assert 'spread' in result
        assert 'type' in result
        assert 'fee_adjusted_profit' in result
        assert 'profit_per_100' in result
        assert 'outcomes' in result
        assert 'timestamp' in result

    def test_truncates_long_questions(self, analyzer):
        """Should truncate outcome questions to 60 chars"""
        long_question = "A" * 100
        event = create_event('e1', 'Event', [
            create_market('m1', long_question, 0.30),
            create_market('m2', 'B', 0.30),
            create_market('m3', 'C', 0.30),
        ])

        result = analyzer.analyze_event(event)

        assert len(result['outcomes'][0]['question']) == 60

    def test_handles_clob_token_ids_as_string(self, analyzer):
        """Should parse clobTokenIds when it's a JSON string"""
        market = create_market('m1', 'Test', 0.30)
        market['clobTokenIds'] = '["token_123"]'

        event = create_event('e1', 'Event', [
            market,
            create_market('m2', 'B', 0.30),
            create_market('m3', 'C', 0.30),
        ])

        result = analyzer.analyze_event(event)

        assert result['outcomes'][0]['token_id'] == 'token_123'

    def test_handles_clob_token_ids_as_list(self, analyzer):
        """Should handle clobTokenIds when it's already a list"""
        market = create_market('m1', 'Test', 0.30)
        market['clobTokenIds'] = ['token_456']

        event = create_event('e1', 'Event', [
            market,
            create_market('m2', 'B', 0.30),
            create_market('m3', 'C', 0.30),
        ])

        result = analyzer.analyze_event(event)

        assert result['outcomes'][0]['token_id'] == 'token_456'

    def test_handles_empty_clob_token_id_list(self, analyzer):
        """Should not crash when clobTokenIds is an empty list."""
        market = create_market('m1', 'Test', 0.30)
        market['clobTokenIds'] = []

        event = create_event('e1', 'Event', [
            market,
            create_market('m2', 'B', 0.30),
            create_market('m3', 'C', 0.30),
        ])

        result = analyzer.analyze_event(event)

        assert result is not None
        assert result['outcomes'][0]['token_id'] == ''


class TestNegRiskScanAll:
    """Test scanning all events for opportunities"""

    def test_filters_by_min_spread(self, analyzer, mock_gamma_client):
        """Should filter results by minimum spread threshold"""
        events = [
            create_event('e1', 'Small Spread', [create_market('m1', 'A', 0.33), create_market('m2', 'B', 0.33), create_market('m3', 'C', 0.33)]),  # spread ~0.01
            create_event('e2', 'Large Spread', [create_market('m4', 'A', 0.25), create_market('m5', 'B', 0.25), create_market('m6', 'C', 0.25)]),  # spread = 0.25
        ]
        mock_gamma_client.get_markets.return_value = events

        result = analyzer.scan_all(min_spread=0.02)

        assert len(result) == 1
        assert result[0]['event_id'] == 'e2'

    def test_sorts_by_profit(self, analyzer, mock_gamma_client):
        """Should sort results by fee_adjusted_profit descending"""
        events = [
            create_event('e1', 'Low Profit', [create_market('m1', 'A', 0.30), create_market('m2', 'B', 0.30), create_market('m3', 'C', 0.30)]),  # sum = 0.90
            create_event('e2', 'High Profit', [create_market('m4', 'A', 0.20), create_market('m5', 'B', 0.20), create_market('m6', 'C', 0.20)]),  # sum = 0.60
            create_event('e3', 'Med Profit', [create_market('m7', 'A', 0.25), create_market('m8', 'B', 0.25), create_market('m9', 'C', 0.25)]),  # sum = 0.75
        ]
        mock_gamma_client.get_markets.return_value = events

        result = analyzer.scan_all(min_spread=0.02)

        assert len(result) == 3
        assert result[0]['event_id'] == 'e2'  # Highest profit
        assert result[1]['event_id'] == 'e3'  # Medium profit
        assert result[2]['event_id'] == 'e1'  # Lowest profit

    def test_returns_empty_list_when_no_opportunities(self, analyzer, mock_gamma_client):
        """Should return empty list when no opportunities found"""
        events = [
            create_event('e1', 'Perfect Price', [create_market('m1', 'A', 0.33), create_market('m2', 'B', 0.33), create_market('m3', 'C', 0.34)]),
        ]
        mock_gamma_client.get_markets.return_value = events

        result = analyzer.scan_all(min_spread=0.05)

        assert result == []

    def test_respects_different_spread_thresholds(self, analyzer, mock_gamma_client):
        """Should respect various min_spread values"""
        # Create events with spreads: 0.01, 0.03, 0.05, 0.12, 0.15
        events = [
            create_event('e1', 'Event 1', [create_market('m1_1', 'A', 0.33), create_market('m1_2', 'B', 0.33), create_market('m1_3', 'C', 0.33)]),  # spread ~0.01
            create_event('e2', 'Event 2', [create_market('m2_1', 'A', 0.32), create_market('m2_2', 'B', 0.32), create_market('m2_3', 'C', 0.33)]),  # spread ~0.03
            create_event('e3', 'Event 3', [create_market('m3_1', 'A', 0.30), create_market('m3_2', 'B', 0.32), create_market('m3_3', 'C', 0.33)]),  # spread ~0.05
            create_event('e4', 'Event 4', [create_market('m4_1', 'A', 0.28), create_market('m4_2', 'B', 0.30), create_market('m4_3', 'C', 0.30)]),  # spread ~0.12
            create_event('e5', 'Event 5', [create_market('m5_1', 'A', 0.25), create_market('m5_2', 'B', 0.30), create_market('m5_3', 'C', 0.30)]),  # spread ~0.15
        ]
        mock_gamma_client.get_markets.return_value = events

        result_low = analyzer.scan_all(min_spread=0.02)
        result_high = analyzer.scan_all(min_spread=0.10)

        assert len(result_low) > len(result_high)
        assert len(result_low) >= 4  # Should include spreads 0.03, 0.05, 0.12, 0.15
        assert len(result_high) >= 2  # Should include spreads 0.12, 0.15


class TestNegRiskEdgeCases:
    """Test edge cases and error handling"""

    def test_single_market_event_returns_none(self, analyzer):
        """Should return None for single-market events"""
        event = create_event('e1', 'Single Market', [
            create_market('m1', 'Only One', 0.50),
        ])

        result = analyzer.analyze_event(event)

        assert result is None

    def test_handles_zero_prices(self, analyzer):
        """Should handle markets with 0.00 prices"""
        event = create_event('e1', 'Event', [
            create_market('m1', 'A', 0.00),
            create_market('m2', 'B', 0.50),
            create_market('m3', 'C', 0.50),
        ])

        result = analyzer.analyze_event(event)

        assert result is not None
        assert result['total_yes_price'] == 1.0

    def test_handles_all_equal_prices(self, analyzer):
        """Should handle all outcomes at equal prices"""
        event = create_event('e1', 'Event', [
            create_market('m1', 'A', 0.33),
            create_market('m2', 'B', 0.33),
            create_market('m3', 'C', 0.33),
        ])

        result = analyzer.analyze_event(event)

        assert result is not None
        assert abs(result['total_yes_price'] - 0.99) < 0.01
        assert result['spread'] < 0.02

    def test_custom_polymarket_fee(self, mock_gamma_client, mock_clob_client):
        """Should use custom polymarket_fee in calculations"""
        analyzer_custom = NegRiskAnalyzer(
            gamma_client=mock_gamma_client,
            clob_client=mock_clob_client,
            polymarket_fee=0.05  # 5% fee
        )

        event = create_event('e1', 'Event', [
            create_market('m1', 'A', 0.30),
            create_market('m2', 'B', 0.30),
            create_market('m3', 'C', 0.30),
        ])

        result = analyzer_custom.analyze_event(event)

        # Fee = 5% of (1.0 - 0.30) = 0.035
        # Net profit = 0.10 - 0.035 = 0.065
        expected_profit = 0.10 - (0.05 * 0.70)
        assert abs(result['fee_adjusted_profit'] - expected_profit) < 0.001

    def test_handles_malformed_json_gracefully(self, analyzer):
        """Should skip markets with malformed JSON outcomePrices"""
        event = create_event('e1', 'Event', [
            create_market('m1', 'A', 0.30),
            {'id': 'm2', 'question': 'B', 'outcomePrices': 'not valid json'},
            create_market('m3', 'C', 0.30),
        ])

        result = analyzer.analyze_event(event)

        assert result is not None
        assert result['num_outcomes'] == 2

    def test_profit_per_100_calculation(self, analyzer):
        """Should calculate profit_per_100 correctly"""
        event = create_event('e1', 'Event', [
            create_market('m1', 'A', 0.25),
            create_market('m2', 'B', 0.25),
            create_market('m3', 'C', 0.25),
        ])

        result = analyzer.analyze_event(event)

        # fee_adjusted_profit should be multiplied by 100
        assert result['profit_per_100'] == result['fee_adjusted_profit'] * 100

    def test_timestamp_format(self, analyzer):
        """Should include ISO format timestamp"""
        event = create_event('e1', 'Event', [
            create_market('m1', 'A', 0.30),
            create_market('m2', 'B', 0.30),
            create_market('m3', 'C', 0.30),
        ])

        result = analyzer.analyze_event(event)

        # Should be parseable as ISO datetime
        dt = datetime.fromisoformat(result['timestamp'])
        assert isinstance(dt, datetime)
