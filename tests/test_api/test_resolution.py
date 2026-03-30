"""Tests for market resolution data functionality"""

import json
import pytest
import responses
from datetime import datetime
from polyterm.api.gamma import GammaClient
from polyterm.db.models import ResolutionOutcome


GAMMA_ENDPOINT = "https://gamma-api.polymarket.com"


class TestResolutionOutcomeModel:
    """Test ResolutionOutcome dataclass"""

    def test_to_dict(self):
        """Test serialization to dict"""
        outcome = ResolutionOutcome(
            market_id="abc123",
            market_slug="will-btc-hit-100k",
            title="Will BTC hit $100k?",
            resolved=True,
            outcome="YES",
            winning_price=1.0,
            resolved_at=datetime(2026, 3, 15, 12, 0),
            resolution_source="0xresolver",
            closed_at=datetime(2026, 3, 15, 12, 0),
        )
        d = outcome.to_dict()
        assert d['market_id'] == "abc123"
        assert d['resolved'] is True
        assert d['outcome'] == "YES"
        assert d['winning_price'] == 1.0
        assert d['resolved_at'] == "2026-03-15T12:00:00"
        assert d['resolution_source'] == "0xresolver"

    def test_from_dict(self):
        """Test deserialization from dict"""
        data = {
            'market_id': 'abc123',
            'market_slug': 'will-btc-hit-100k',
            'title': 'Will BTC hit $100k?',
            'resolved': True,
            'outcome': 'YES',
            'winning_price': 1.0,
            'resolved_at': '2026-03-15T12:00:00',
            'resolution_source': '0xresolver',
            'closed_at': '2026-03-15T12:00:00',
        }
        outcome = ResolutionOutcome.from_dict(data)
        assert outcome.market_id == "abc123"
        assert outcome.resolved is True
        assert outcome.outcome == "YES"
        assert outcome.resolved_at == datetime(2026, 3, 15, 12, 0)

    def test_from_dict_defaults(self):
        """Test from_dict with minimal data"""
        outcome = ResolutionOutcome.from_dict({'market_id': 'test'})
        assert outcome.market_id == 'test'
        assert outcome.resolved is False
        assert outcome.outcome == ''
        assert outcome.resolved_at is None
        assert outcome.closed_at is None

    def test_status_property_resolved(self):
        """Test status for resolved market"""
        outcome = ResolutionOutcome(resolved=True, outcome="YES")
        assert outcome.status == "Resolved: YES"

    def test_status_property_pending(self):
        """Test status for pending resolution"""
        outcome = ResolutionOutcome(
            resolved=False,
            closed_at=datetime(2026, 3, 15),
        )
        assert outcome.status == "Pending resolution"

    def test_status_property_active(self):
        """Test status for active market"""
        outcome = ResolutionOutcome(resolved=False)
        assert outcome.status == "Active"


class TestGammaClientResolution:
    """Test GammaClient resolution methods"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return GammaClient(base_url=GAMMA_ENDPOINT)

    def test_parse_resolution_resolved_yes(self, client):
        """Test parsing a market that resolved YES"""
        market = {
            'id': 'market1',
            'slug': 'will-btc-hit-100k',
            'question': 'Will BTC hit $100k?',
            'closed': True,
            'active': False,
            'outcomePrices': '[1.0, 0.0]',
            'endDate': '2026-03-15T12:00:00Z',
            'resolvedBy': '0xresolver',
        }
        result = client._parse_resolution(market)
        assert result['resolved'] is True
        assert result['outcome'] == 'YES'
        assert result['winning_price'] == 1.0
        assert result['status'] == 'Resolved: YES'
        assert result['resolution_source'] == '0xresolver'

    def test_parse_resolution_resolved_no(self, client):
        """Test parsing a market that resolved NO"""
        market = {
            'id': 'market2',
            'question': 'Will ETH flip BTC?',
            'closed': True,
            'active': False,
            'outcomePrices': '[0.0, 1.0]',
            'endDate': '2026-03-10T00:00:00Z',
        }
        result = client._parse_resolution(market)
        assert result['resolved'] is True
        assert result['outcome'] == 'NO'
        assert result['winning_price'] == 1.0
        assert result['status'] == 'Resolved: NO'

    def test_parse_resolution_active_market(self, client):
        """Test parsing an active (unresolved) market"""
        market = {
            'id': 'market3',
            'question': 'Will SOL hit $500?',
            'closed': False,
            'active': True,
            'outcomePrices': '[0.35, 0.65]',
            'endDate': '2026-06-01T00:00:00Z',
        }
        result = client._parse_resolution(market)
        assert result['resolved'] is False
        assert result['outcome'] == ''
        assert result['status'] == 'Active'

    def test_parse_resolution_pending(self, client):
        """Test parsing a closed market pending resolution"""
        market = {
            'id': 'market4',
            'question': 'Some event?',
            'closed': True,
            'active': False,
            'outcomePrices': '[0.5, 0.5]',
            'endDate': '2026-03-14T00:00:00Z',
        }
        result = client._parse_resolution(market)
        assert result['resolved'] is False
        assert result['status'] == 'Pending resolution'

    def test_parse_resolution_outcome_prices_as_list(self, client):
        """Test parsing when outcomePrices is already a list"""
        market = {
            'id': 'market5',
            'closed': True,
            'active': False,
            'outcomePrices': [1.0, 0.0],
        }
        result = client._parse_resolution(market)
        assert result['resolved'] is True
        assert result['outcome'] == 'YES'

    def test_parse_resolution_empty_outcome_prices(self, client):
        """Test parsing with empty outcome prices"""
        market = {
            'id': 'market6',
            'closed': True,
            'active': False,
            'outcomePrices': '[]',
        }
        result = client._parse_resolution(market)
        assert result['resolved'] is False

    def test_parse_resolution_no_end_date(self, client):
        """Test parsing when endDate is missing"""
        market = {
            'id': 'market7',
            'closed': False,
            'active': True,
            'outcomePrices': '[0.5, 0.5]',
        }
        result = client._parse_resolution(market)
        assert result['closed_at'] is None
        assert result['resolved'] is False

    def test_parse_resolution_near_threshold(self, client):
        """Test that prices near but below 0.95 are not considered resolved"""
        market = {
            'id': 'market8',
            'closed': True,
            'active': False,
            'outcomePrices': '[0.93, 0.07]',
        }
        result = client._parse_resolution(market)
        assert result['resolved'] is False

    @responses.activate
    def test_get_resolution(self, client):
        """Test getting resolution for a specific market"""
        market_data = {
            'id': 'market1',
            'slug': 'btc-100k',
            'question': 'Will BTC hit $100k?',
            'closed': True,
            'active': False,
            'outcomePrices': '[1.0, 0.0]',
            'endDate': '2026-03-15T12:00:00Z',
            'resolvedBy': '0xresolver',
        }
        responses.add(
            responses.GET,
            f"{GAMMA_ENDPOINT}/markets/market1",
            json=market_data,
            status=200,
        )
        result = client.get_resolution('market1')
        assert result is not None
        assert result['resolved'] is True
        assert result['outcome'] == 'YES'

    @responses.activate
    def test_get_resolution_not_found(self, client):
        """Test getting resolution for non-existent market"""
        responses.add(
            responses.GET,
            f"{GAMMA_ENDPOINT}/markets/nonexistent",
            json={'error': 'not found'},
            status=404,
        )
        result = client.get_resolution('nonexistent')
        assert result is None

    @responses.activate
    def test_get_resolved_markets(self, client):
        """Test getting list of resolved markets"""
        markets_data = [
            {
                'id': 'market1',
                'question': 'Market 1',
                'closed': True,
                'active': False,
                'outcomePrices': '[1.0, 0.0]',
                'endDate': '2026-03-15T12:00:00Z',
            },
            {
                'id': 'market2',
                'question': 'Market 2',
                'closed': True,
                'active': False,
                'outcomePrices': '[0.5, 0.5]',  # Not resolved yet
                'endDate': '2026-03-14T00:00:00Z',
            },
            {
                'id': 'market3',
                'question': 'Market 3',
                'closed': True,
                'active': False,
                'outcomePrices': '[0.0, 1.0]',
                'endDate': '2026-03-13T00:00:00Z',
            },
        ]
        responses.add(
            responses.GET,
            f"{GAMMA_ENDPOINT}/markets",
            json=markets_data,
            status=200,
        )
        results = client.get_resolved_markets(limit=10)
        # Should only include markets 1 and 3 (actually resolved)
        assert len(results) == 2
        assert results[0]['id'] == 'market1'
        assert results[0]['_resolution']['outcome'] == 'YES'
        assert results[1]['id'] == 'market3'
        assert results[1]['_resolution']['outcome'] == 'NO'

    @responses.activate
    def test_get_resolved_markets_api_error(self, client):
        """Test get_resolved_markets handles API errors gracefully"""
        responses.add(
            responses.GET,
            f"{GAMMA_ENDPOINT}/markets",
            json={'error': 'server error'},
            status=500,
        )
        results = client.get_resolved_markets()
        assert results == []
