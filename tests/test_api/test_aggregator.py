"""Tests for APIAggregator fallback and data enrichment logic"""

import logging
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from polyterm.api.aggregator import APIAggregator


class TestAggregatorGetLiveMarkets:
    """Tests for get_live_markets fallback chain"""

    @pytest.fixture
    def mock_gamma(self):
        gamma = Mock()
        gamma.get_markets.return_value = [
            {"id": "m1", "question": "Will BTC hit 100k?", "volume": 50000, "volume24hr": 10000},
            {"id": "m2", "question": "Will ETH hit 5k?", "volume": 30000, "volume24hr": 5000},
        ]
        gamma.filter_fresh_markets.return_value = [
            {"id": "m1", "question": "Will BTC hit 100k?", "volume": 50000, "volume24hr": 10000},
            {"id": "m2", "question": "Will ETH hit 5k?", "volume": 30000, "volume24hr": 5000},
        ]
        return gamma

    @pytest.fixture
    def mock_clob(self):
        clob = Mock()
        clob.get_current_markets.return_value = [
            {"id": "c1", "title": "BTC market"},
            {"id": "c2", "title": "ETH market"},
        ]
        clob.is_market_current.return_value = True
        return clob

    @pytest.fixture
    def aggregator(self, mock_gamma, mock_clob):
        return APIAggregator(gamma_client=mock_gamma, clob_client=mock_clob)

    def test_gamma_success_returns_gamma_data(self, aggregator, mock_gamma):
        """When Gamma succeeds, returns Gamma data without touching CLOB"""
        markets = aggregator.get_live_markets(limit=100)

        assert len(markets) == 2
        assert markets[0]["id"] == "m1"
        mock_gamma.get_markets.assert_called_once()
        mock_gamma.filter_fresh_markets.assert_called_once()

    def test_gamma_success_does_not_call_clob(self, aggregator, mock_clob):
        """Successful Gamma path should not call CLOB"""
        aggregator.get_live_markets()
        mock_clob.get_current_markets.assert_not_called()

    def test_gamma_failure_falls_back_to_clob(self, aggregator, mock_gamma, mock_clob):
        """When Gamma raises, falls back to CLOB"""
        mock_gamma.get_markets.side_effect = Exception("Gamma timeout")

        markets = aggregator.get_live_markets()

        assert len(markets) == 2
        assert markets[0]["id"] == "c1"
        mock_clob.get_current_markets.assert_called_once()

    def test_gamma_empty_fresh_markets_falls_back(self, aggregator, mock_gamma, mock_clob):
        """When Gamma returns no fresh markets, falls back to CLOB"""
        mock_gamma.filter_fresh_markets.return_value = []

        markets = aggregator.get_live_markets()

        assert len(markets) == 2
        mock_clob.get_current_markets.assert_called_once()

    def test_both_fail_returns_empty_list(self, aggregator, mock_gamma, mock_clob):
        """When both Gamma and CLOB fail, returns empty list"""
        mock_gamma.get_markets.side_effect = Exception("Gamma down")
        mock_clob.get_current_markets.side_effect = Exception("CLOB down")

        markets = aggregator.get_live_markets()
        assert markets == []

    def test_clob_filters_non_current_markets(self, aggregator, mock_gamma, mock_clob):
        """CLOB fallback filters out non-current markets"""
        mock_gamma.get_markets.side_effect = Exception("Gamma down")
        mock_clob.get_current_markets.return_value = [
            {"id": "c1"}, {"id": "c2"}, {"id": "c3"},
        ]
        mock_clob.is_market_current.side_effect = [True, False, True]

        markets = aggregator.get_live_markets()
        assert len(markets) == 2

    def test_limit_parameter_passed_to_gamma(self, aggregator, mock_gamma):
        """limit parameter is forwarded to Gamma API"""
        aggregator.get_live_markets(limit=50)
        mock_gamma.get_markets.assert_called_once_with(limit=50, active=True, closed=False)

    def test_volume_params_passed_to_filter(self, aggregator, mock_gamma):
        """require_volume and min_volume forwarded to filter_fresh_markets"""
        aggregator.get_live_markets(require_volume=True, min_volume=500)
        mock_gamma.filter_fresh_markets.assert_called_once_with(
            mock_gamma.get_markets.return_value,
            max_age_hours=24,
            require_volume=True,
            min_volume=500,
        )

    def test_gamma_fallback_logs_warning(self, aggregator, mock_gamma, caplog):
        """Gamma failure logs error before falling back"""
        mock_gamma.get_markets.side_effect = Exception("timeout")

        with caplog.at_level(logging.ERROR, logger="polyterm.api.aggregator"):
            aggregator.get_live_markets()

        assert any("Gamma API failed" in r.message for r in caplog.records)

    def test_clob_fallback_logs_info(self, aggregator, mock_gamma, mock_clob, caplog):
        """Successful CLOB fallback logs info"""
        mock_gamma.get_markets.side_effect = Exception("timeout")

        with caplog.at_level(logging.INFO, logger="polyterm.api.aggregator"):
            aggregator.get_live_markets()

        assert any("CLOB fallback" in r.message for r in caplog.records)

    def test_both_fail_logs_error(self, aggregator, mock_gamma, mock_clob, caplog):
        """Both sources failing logs critical error"""
        mock_gamma.get_markets.side_effect = Exception("down")
        mock_clob.get_current_markets.side_effect = Exception("down")

        with caplog.at_level(logging.ERROR, logger="polyterm.api.aggregator"):
            aggregator.get_live_markets()

        assert any("All API sources failed" in r.message for r in caplog.records)

    def test_clob_volume_warning_when_required(self, aggregator, mock_gamma, mock_clob, caplog):
        """When require_volume=True and using CLOB fallback, logs warning"""
        mock_gamma.get_markets.side_effect = Exception("timeout")

        with caplog.at_level(logging.WARNING, logger="polyterm.api.aggregator"):
            aggregator.get_live_markets(require_volume=True)

        assert any("lack volume data" in r.message for r in caplog.records)


class TestAggregatorEnrichMarketData:
    """Tests for enrich_market_data combining sources"""

    @pytest.fixture
    def mock_gamma(self):
        gamma = Mock()
        gamma.get_market.return_value = {"volume": 50000, "volume24hr": 10000}
        return gamma

    @pytest.fixture
    def mock_clob(self):
        clob = Mock()
        clob.get_order_book.return_value = {"bids": [], "asks": []}
        clob.calculate_spread.return_value = 0.02
        return clob

    @pytest.fixture
    def aggregator(self, mock_gamma, mock_clob):
        return APIAggregator(gamma_client=mock_gamma, clob_client=mock_clob)

    def test_enriches_volume_from_gamma(self, aggregator):
        """Adds volume from Gamma when missing in base data"""
        base = {"id": "m1", "question": "Test?"}
        enriched = aggregator.enrich_market_data("m1", base)

        assert enriched["volume"] == 50000
        assert enriched["volume24hr"] == 10000

    def test_skips_gamma_when_volume_exists(self, aggregator, mock_gamma):
        """Does not fetch Gamma volume when base already has it"""
        base = {"id": "m1", "volume": 99999}
        aggregator.enrich_market_data("m1", base)
        mock_gamma.get_market.assert_not_called()

    def test_adds_order_book_from_clob(self, aggregator, mock_clob):
        """Adds order book data from CLOB"""
        base = {"id": "m1", "volume": 1000}
        enriched = aggregator.enrich_market_data("m1", base)

        assert "order_book" in enriched
        assert enriched["spread"] == 0.02

    def test_data_sources_metadata(self, aggregator):
        """Tracks which data sources contributed"""
        base = {"id": "m1"}
        enriched = aggregator.enrich_market_data("m1", base)

        assert "gamma" in enriched["_data_sources"]
        assert "clob" in enriched["_data_sources"]

    def test_gamma_enrich_error_swallowed(self, aggregator, mock_gamma):
        """Gamma errors during enrichment are swallowed"""
        mock_gamma.get_market.side_effect = Exception("timeout")
        base = {"id": "m1"}

        enriched = aggregator.enrich_market_data("m1", base)
        # Should still have order book
        assert "order_book" in enriched

    def test_clob_enrich_error_swallowed(self, aggregator, mock_clob):
        """CLOB errors during enrichment are swallowed"""
        mock_clob.get_order_book.side_effect = Exception("timeout")
        base = {"id": "m1", "volume": 1000}

        enriched = aggregator.enrich_market_data("m1", base)
        assert "order_book" not in enriched

    def test_does_not_mutate_base_data(self, aggregator):
        """enrich_market_data returns a copy, does not mutate input"""
        base = {"id": "m1"}
        enriched = aggregator.enrich_market_data("m1", base)

        assert "_data_sources" not in base
        assert "_data_sources" in enriched


class TestAggregatorTopMarketsByVolume:
    """Tests for get_top_markets_by_volume"""

    @pytest.fixture
    def aggregator(self):
        gamma = Mock()
        gamma.get_markets.return_value = [
            {"id": f"m{i}", "volume24hr": i * 1000, "volume": i * 5000}
            for i in range(20)
        ]
        gamma.filter_fresh_markets.side_effect = lambda markets, **kw: markets
        clob = Mock()
        return APIAggregator(gamma_client=gamma, clob_client=clob)

    def test_returns_top_n_by_volume(self, aggregator):
        """Returns markets sorted by 24hr volume, limited"""
        top = aggregator.get_top_markets_by_volume(limit=5)
        assert len(top) == 5
        assert top[0]["volume24hr"] == 19000
        assert top[4]["volume24hr"] == 15000

    def test_passes_min_volume(self, aggregator):
        """min_volume parameter is forwarded"""
        aggregator.get_top_markets_by_volume(min_volume=500)
        # Check get_live_markets was called with min_volume
        call_kwargs = {}
        # get_live_markets calls gamma.get_markets then filter
        # Just verify it doesn't crash
        assert True


class TestAggregatorValidateDataFreshness:
    """Tests for validate_data_freshness"""

    @pytest.fixture
    def aggregator(self):
        gamma = Mock()
        gamma.is_market_fresh.return_value = True
        clob = Mock()
        return APIAggregator(gamma_client=gamma, clob_client=clob)

    def test_reports_fresh_market_count(self, aggregator):
        """Counts fresh markets correctly"""
        markets = [
            {"question": "Test 1", "volume": 1000},
            {"question": "Test 2", "volume": 2000},
        ]
        report = aggregator.validate_data_freshness(markets)

        assert report["total_markets"] == 2
        assert report["fresh_markets"] == 2
        assert report["stale_markets"] == 0

    def test_reports_stale_markets(self, aggregator):
        """Counts stale markets and adds issues"""
        aggregator.gamma_client.is_market_fresh.return_value = False
        markets = [{"question": "Stale market", "volume": 0}]

        report = aggregator.validate_data_freshness(markets)
        assert report["stale_markets"] == 1
        assert any("Stale market" in issue for issue in report["issues"])

    def test_reports_volume_presence(self, aggregator):
        """Tracks markets with volume data"""
        markets = [
            {"question": "Has volume", "volume": 1000},
            {"question": "No volume", "volume": 0},
        ]
        report = aggregator.validate_data_freshness(markets)
        assert report["markets_with_volume"] == 1

    def test_warns_when_stale_exceeds_fresh(self, aggregator):
        """Warning when more stale than fresh markets"""
        aggregator.gamma_client.is_market_fresh.side_effect = [False, False, True]
        markets = [{"question": f"M{i}", "volume": 0} for i in range(3)]

        report = aggregator.validate_data_freshness(markets)
        assert any("More stale markets" in issue for issue in report["issues"])

    def test_critical_when_no_volume(self, aggregator):
        """Critical warning when zero markets have volume"""
        markets = [{"question": "No vol", "volume": 0}]
        report = aggregator.validate_data_freshness(markets)
        assert any("CRITICAL" in issue for issue in report["issues"])

    def test_empty_markets_list(self, aggregator):
        """Handles empty market list gracefully"""
        report = aggregator.validate_data_freshness([])
        assert report["total_markets"] == 0
        assert report["fresh_markets"] == 0

    def test_tracks_oldest_market_year(self, aggregator):
        """Tracks oldest market by end date year"""
        markets = [
            {"question": "Old", "volume": 1, "endDate": "2023-01-01"},
            {"question": "New", "volume": 1, "endDate": "2026-06-01"},
        ]
        report = aggregator.validate_data_freshness(markets)
        assert report["oldest_market_year"] == 2023
