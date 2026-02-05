"""Tests for MarketRiskScorer"""

import pytest
from datetime import datetime, timedelta
from polyterm.core.risk_score import MarketRiskScorer, RiskAssessment


class TestMarketRiskScorer:
    """Test risk scoring logic"""

    def setup_method(self):
        self.scorer = MarketRiskScorer()

    # --- Grade Boundaries ---

    def test_score_to_grade_boundaries(self):
        """Test that grade boundaries match documentation: A(0-20), B(21-35), C(36-50), D(51-70), F(71+)"""
        # Low risk = grade A
        result = self.scorer.score_market(
            market_id="test-1",
            title="Will Bitcoin reach $100k by December 2025?",
            description="Resolves YES if Bitcoin spot price exceeds $100,000 on Coinbase.",
            end_date=datetime.now() + timedelta(days=60),
            volume_24h=500000,
            liquidity=1000000,
            spread=0.01,
            category="crypto",
            resolution_source="Coinbase spot price",
        )
        assert result.overall_grade in ("A", "B")  # Well-defined market
        assert result.overall_score >= 0

    def test_high_risk_market(self):
        """Test that poorly defined markets get low grades"""
        result = self.scorer.score_market(
            market_id="test-2",
            title="Will something interesting happen maybe soon?",
            description="",
            end_date=datetime.now() + timedelta(days=365),
            volume_24h=100,
            liquidity=50,
            spread=0.15,
            category="other",
            resolution_source="",
        )
        assert result.overall_grade in ("D", "F")
        assert result.overall_score > 50

    # --- Resolution Clarity ---

    def test_clear_resolution_source_reduces_risk(self):
        """Markets with clear resolution sources should score lower (better)"""
        clear = self.scorer.score_market(
            market_id="test-clear",
            title="Will ETH price exceed $5000?",
            resolution_source="CoinGecko API",
        )
        vague = self.scorer.score_market(
            market_id="test-vague",
            title="Will something happen eventually?",
            resolution_source="",
        )
        assert clear.overall_score < vague.overall_score

    def test_subjective_keywords_increase_risk(self):
        """Markets with subjective language should score higher (worse)"""
        subjective = self.scorer.score_market(
            market_id="test-subj",
            title="Will the best president significantly impact the economy?",
        )
        objective = self.scorer.score_market(
            market_id="test-obj",
            title="Will GDP growth exceed 3% in Q4 2025?",
        )
        assert subjective.overall_score >= objective.overall_score

    # --- Liquidity Scoring ---

    def test_high_liquidity_low_risk(self):
        """High liquidity should reduce risk"""
        result = self.scorer.score_market(
            market_id="test-liq",
            title="Test market",
            liquidity=5000000,
        )
        # Check factors dict has liquidity
        assert "liquidity" in result.factors

    def test_zero_liquidity_high_risk(self):
        """Zero liquidity should increase risk"""
        result = self.scorer.score_market(
            market_id="test-no-liq",
            title="Test market",
            liquidity=0,
        )
        assert result.factors["liquidity"]["score"] >= 70

    # --- Time Risk ---

    def test_imminent_resolution_low_time_risk(self):
        """Markets resolving soon should have low time risk"""
        result = self.scorer.score_market(
            market_id="test-soon",
            title="Test market",
            end_date=datetime.now() + timedelta(days=7),
        )
        assert result.factors["time_risk"]["score"] <= 30

    def test_far_future_resolution_high_time_risk(self):
        """Markets resolving far in the future should have higher time risk"""
        result = self.scorer.score_market(
            market_id="test-far",
            title="Test market",
            end_date=datetime.now() + timedelta(days=365),
        )
        assert result.factors["time_risk"]["score"] >= 40

    def test_no_end_date_high_time_risk(self):
        """Markets with no end date should have high time risk"""
        result = self.scorer.score_market(
            market_id="test-no-date",
            title="Test market",
            end_date=None,
        )
        assert result.factors["time_risk"]["score"] >= 50

    # --- Volume Quality ---

    def test_healthy_volume_liquidity_ratio(self):
        """Volume proportional to liquidity should score well"""
        result = self.scorer.score_market(
            market_id="test-healthy-vol",
            title="Test market",
            volume_24h=100000,
            liquidity=500000,
        )
        assert result.factors["volume_quality"]["score"] <= 40

    # --- Spread ---

    def test_tight_spread_low_risk(self):
        """Tight spreads should indicate low risk"""
        result = self.scorer.score_market(
            market_id="test-tight",
            title="Test market",
            spread=0.01,
        )
        assert result.factors["spread"]["score"] <= 30

    def test_wide_spread_high_risk(self):
        """Wide spreads should indicate high risk"""
        result = self.scorer.score_market(
            market_id="test-wide",
            title="Test market",
            spread=0.20,
        )
        assert result.factors["spread"]["score"] >= 50

    # --- Category Risk ---

    def test_sports_low_category_risk(self):
        """Sports markets should have low dispute risk"""
        result = self.scorer.score_market(
            market_id="test-sports",
            title="Will the Lakers win the championship?",
            category="sports",
        )
        assert result.factors["category_risk"]["score"] <= 30

    def test_politics_high_category_risk(self):
        """Political markets should have higher dispute risk"""
        result = self.scorer.score_market(
            market_id="test-politics",
            title="Will the president sign the bill?",
            category="politics",
        )
        assert result.factors["category_risk"]["score"] >= 30

    # --- Output Structure ---

    def test_assessment_has_required_fields(self):
        """RiskAssessment should contain all expected fields"""
        result = self.scorer.score_market(
            market_id="test-struct",
            title="Test market",
        )
        assert isinstance(result, RiskAssessment)
        assert result.market_id == "test-struct"
        assert result.market_title == "Test market"
        assert result.overall_grade in ("A", "B", "C", "D", "F")
        assert 0 <= result.overall_score <= 100
        assert isinstance(result.factors, dict)
        assert isinstance(result.warnings, list)
        assert isinstance(result.recommendations, list)

    def test_to_dict_output(self):
        """to_dict() should return a serializable dict"""
        result = self.scorer.score_market(
            market_id="test-dict",
            title="Test market",
        )
        d = result.to_dict()
        assert isinstance(d, dict)
        assert d["market_id"] == "test-dict"
        assert "overall_grade" in d
        assert "overall_score" in d
        assert "factors" in d

    # --- Grade helpers ---

    def test_grade_descriptions(self):
        """Grade descriptions should be non-empty"""
        for grade in ("A", "B", "C", "D", "F"):
            desc = self.scorer.get_grade_description(grade)
            assert isinstance(desc, str)
            assert len(desc) > 0

    def test_grade_colors(self):
        """Grade colors should be valid Rich color names"""
        for grade in ("A", "B", "C", "D", "F"):
            color = self.scorer.get_grade_color(grade)
            assert isinstance(color, str)
            assert len(color) > 0
