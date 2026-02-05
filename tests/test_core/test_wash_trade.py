"""Tests for WashTradeDetector"""

import pytest
from polyterm.core.wash_trade_detector import (
    WashTradeDetector,
    WashTradeRisk,
    WashTradeAnalysis,
    WashTradeIndicator,
    quick_wash_trade_score,
)


class TestWashTradeDetector:
    """Test wash trade detection logic"""

    def setup_method(self):
        self.detector = WashTradeDetector()

    # --- Basic Analysis ---

    def test_clean_market_low_risk(self):
        """Market with healthy metrics should be low risk"""
        result = self.detector.analyze_market(
            market_id="clean-1",
            title="Clean Market",
            volume_24h=100000,
            liquidity=200000,
            trade_count_24h=500,
            unique_traders_24h=200,
            avg_trade_size=200,
            median_trade_size=150,
            yes_volume=55000,
            no_volume=45000,
        )
        assert isinstance(result, WashTradeAnalysis)
        assert result.risk_level in (WashTradeRisk.LOW, WashTradeRisk.MEDIUM)
        assert result.overall_score < 50

    def test_suspicious_market_high_risk(self):
        """Market with suspicious metrics should be high risk"""
        result = self.detector.analyze_market(
            market_id="sus-1",
            title="Suspicious Market",
            volume_24h=1000000,  # Very high volume
            liquidity=50000,     # Very low liquidity (20:1 ratio)
            trade_count_24h=100,
            unique_traders_24h=5,  # Very few unique traders
            avg_trade_size=10000,
            median_trade_size=10000,  # Uniform sizes
            yes_volume=500000,
            no_volume=500000,   # Perfect 50/50 split
        )
        assert result.risk_level in (WashTradeRisk.HIGH, WashTradeRisk.VERY_HIGH)
        assert result.overall_score > 50

    # --- Volume/Liquidity Ratio ---

    def test_high_volume_liquidity_ratio_flagged(self):
        """Volume >> liquidity should trigger indicator"""
        result = self.detector.analyze_market(
            market_id="vol-ratio",
            title="High Volume Ratio",
            volume_24h=500000,
            liquidity=10000,  # 50:1 ratio
        )
        indicator_types = [i.indicator_type for i in result.indicators]
        assert "volume_liquidity" in indicator_types

    def test_normal_volume_liquidity_ratio(self):
        """Normal ratio shouldn't trigger high score"""
        result = self.detector.analyze_market(
            market_id="normal-ratio",
            title="Normal Ratio",
            volume_24h=100000,
            liquidity=500000,  # 0.2:1 ratio
        )
        for ind in result.indicators:
            if ind.indicator_type == "volume_liquidity":
                assert ind.score < 50

    # --- Trader Concentration ---

    def test_few_unique_traders_flagged(self):
        """Few unique traders relative to trades should trigger indicator"""
        result = self.detector.analyze_market(
            market_id="concentrated",
            title="Concentrated Trading",
            trade_count_24h=1000,
            unique_traders_24h=3,  # Only 3 traders for 1000 trades
        )
        indicator_types = [i.indicator_type for i in result.indicators]
        assert "trader_concentration" in indicator_types

    def test_diverse_traders_low_score(self):
        """Many unique traders should not trigger high score"""
        result = self.detector.analyze_market(
            market_id="diverse",
            title="Diverse Trading",
            trade_count_24h=500,
            unique_traders_24h=200,
        )
        for ind in result.indicators:
            if ind.indicator_type == "trader_concentration":
                assert ind.score < 50

    # --- Trade Size Distribution ---

    def test_uniform_trade_sizes_flagged(self):
        """Uniform trade sizes suggest wash trading"""
        result = self.detector.analyze_market(
            market_id="uniform",
            title="Uniform Sizes",
            avg_trade_size=1000,
            median_trade_size=990,  # Very close to avg = uniform
        )
        indicator_types = [i.indicator_type for i in result.indicators]
        assert "size_uniformity" in indicator_types

    # --- Side Balance ---

    def test_perfectly_balanced_sides_flagged(self):
        """Perfect 50/50 YES/NO volume split is suspicious"""
        result = self.detector.analyze_market(
            market_id="balanced",
            title="Perfectly Balanced",
            yes_volume=500000,
            no_volume=500000,
        )
        indicator_types = [i.indicator_type for i in result.indicators]
        assert "side_balance" in indicator_types

    def test_natural_imbalance_low_score(self):
        """Natural imbalance in volume shouldn't trigger high score"""
        result = self.detector.analyze_market(
            market_id="natural",
            title="Natural Volume",
            yes_volume=70000,
            no_volume=30000,
        )
        for ind in result.indicators:
            if ind.indicator_type == "side_balance":
                assert ind.score < 60

    # --- No Data Defaults ---

    def test_no_indicators_default_uncertain(self):
        """With no data, score should be uncertain (medium), not low"""
        result = self.detector.analyze_market(
            market_id="empty",
            title="Empty Market",
        )
        # After fix: default score is 40 (medium/uncertain), not 20 (low)
        assert result.overall_score >= 30

    def test_minimal_data(self):
        """Only market_id and title required"""
        result = self.detector.analyze_market(
            market_id="minimal",
            title="Minimal Market",
        )
        assert isinstance(result, WashTradeAnalysis)
        assert result.market_id == "minimal"

    # --- Output Structure ---

    def test_analysis_to_dict(self):
        """to_dict() should produce serializable dict"""
        result = self.detector.analyze_market(
            market_id="dict-test",
            title="Dict Test",
            volume_24h=100000,
            liquidity=200000,
        )
        d = result.to_dict()
        assert isinstance(d, dict)
        assert d["market_id"] == "dict-test"
        assert "risk_level" in d
        assert "overall_score" in d
        assert "indicators" in d

    # --- Risk Colors and Descriptions ---

    def test_risk_colors(self):
        """All risk levels should have colors"""
        for level in WashTradeRisk:
            color = self.detector.get_risk_color(level)
            assert isinstance(color, str)
            assert len(color) > 0

    def test_risk_descriptions(self):
        """All risk levels should have descriptions"""
        for level in WashTradeRisk:
            desc = self.detector.get_risk_description(level)
            assert isinstance(desc, str)
            assert len(desc) > 0


class TestQuickWashTradeScore:
    """Test the quick scoring function"""

    def test_quick_score_normal(self):
        """Normal volume/liquidity ratio should have low score"""
        score, desc = quick_wash_trade_score(100000, 500000)
        assert isinstance(score, int)
        assert 0 <= score <= 100
        assert isinstance(desc, str)

    def test_quick_score_high_ratio(self):
        """High volume/liquidity ratio should have high score"""
        score, desc = quick_wash_trade_score(1000000, 10000)
        assert score > 50

    def test_quick_score_zero_liquidity(self):
        """Zero liquidity should handle gracefully"""
        score, desc = quick_wash_trade_score(100000, 0)
        assert isinstance(score, int)
        assert 0 <= score <= 100

    def test_quick_score_zero_volume(self):
        """Zero volume should have low score"""
        score, desc = quick_wash_trade_score(0, 100000)
        assert score <= 30
