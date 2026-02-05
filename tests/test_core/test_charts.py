"""Tests for ASCII chart generation"""

import pytest
from datetime import datetime, timedelta
from polyterm.core.charts import ASCIIChart, generate_price_chart, generate_comparison_chart


class TestASCIIChart:
    """Test ASCIIChart class"""

    def setup_method(self):
        self.chart = ASCIIChart(width=40, height=10)

    # --- Sparkline ---

    def test_sparkline_basic(self):
        """Sparkline should produce a string of block characters"""
        values = [0.1, 0.3, 0.5, 0.7, 0.9, 0.7, 0.5, 0.3]
        result = self.chart.generate_sparkline(values, width=8)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_sparkline_single_value(self):
        """Sparkline with single value shouldn't crash"""
        result = self.chart.generate_sparkline([0.5], width=5)
        assert isinstance(result, str)

    def test_sparkline_all_same_values(self):
        """Sparkline with all same values should still render"""
        result = self.chart.generate_sparkline([0.5, 0.5, 0.5, 0.5], width=4)
        assert isinstance(result, str)

    def test_sparkline_empty_values(self):
        """Sparkline with empty list should return empty or dash"""
        result = self.chart.generate_sparkline([], width=5)
        assert isinstance(result, str)

    def test_sparkline_respects_width(self):
        """Sparkline length should match or be close to requested width"""
        values = list(range(100))
        result = self.chart.generate_sparkline(values, width=20)
        assert len(result) <= 21  # Allow 1 char tolerance

    # --- Line Chart ---

    def test_line_chart_basic(self):
        """Line chart should render without errors"""
        now = datetime.now()
        data = [(now + timedelta(hours=i), 0.4 + i * 0.05) for i in range(10)]
        result = self.chart.generate_line_chart(data, title="Test Chart")
        assert isinstance(result, str)
        assert len(result) > 0
        assert "Test Chart" in result

    def test_line_chart_single_point(self):
        """Line chart with one data point shouldn't crash"""
        data = [(datetime.now(), 0.5)]
        result = self.chart.generate_line_chart(data)
        assert isinstance(result, str)

    def test_line_chart_two_points(self):
        """Line chart with two points should render"""
        now = datetime.now()
        data = [(now, 0.3), (now + timedelta(hours=1), 0.7)]
        result = self.chart.generate_line_chart(data)
        assert isinstance(result, str)

    def test_line_chart_empty_data(self):
        """Line chart with no data should handle gracefully"""
        result = self.chart.generate_line_chart([])
        assert isinstance(result, str)

    # --- Bar Chart ---

    def test_bar_chart_basic(self):
        """Bar chart should render categories"""
        data = [("BTC", 0.65), ("ETH", 0.45), ("SOL", 0.72)]
        result = self.chart.generate_bar_chart(data, title="Crypto Prices")
        assert isinstance(result, str)
        assert "BTC" in result
        assert "ETH" in result

    def test_bar_chart_single_item(self):
        """Bar chart with one item should work"""
        data = [("Test", 50.0)]
        result = self.chart.generate_bar_chart(data)
        assert isinstance(result, str)

    def test_bar_chart_zero_values(self):
        """Bar chart with zero values should handle gracefully"""
        data = [("A", 0), ("B", 0)]
        result = self.chart.generate_bar_chart(data)
        assert isinstance(result, str)

    # --- Y-axis labels ---

    def test_y_labels_probability_range(self):
        """Y-axis labels for 0-1 range should show percentages"""
        labels = self.chart._generate_y_labels(0.0, 1.0, 5)
        assert isinstance(labels, list)
        assert len(labels) == 5

    def test_y_labels_same_min_max(self):
        """Y-axis labels with min==max shouldn't crash"""
        labels = self.chart._generate_y_labels(0.5, 0.5, 3)
        assert isinstance(labels, list)


class TestGeneratePriceChart:
    """Test module-level convenience functions"""

    def test_generate_price_chart_basic(self):
        """generate_price_chart should produce string output"""
        now = datetime.now()
        prices = [(now + timedelta(hours=i), 0.5 + i * 0.02) for i in range(20)]
        result = generate_price_chart(prices, title="BTC Market", width=40, height=10)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_price_chart_empty(self):
        """generate_price_chart with empty data should handle gracefully"""
        result = generate_price_chart([], title="Empty")
        assert isinstance(result, str)

    def test_generate_comparison_chart(self):
        """Comparison chart should show both market names"""
        now = datetime.now()
        m1 = [(now + timedelta(hours=i), 0.5 + i * 0.01) for i in range(10)]
        m2 = [(now + timedelta(hours=i), 0.6 - i * 0.01) for i in range(10)]
        result = generate_comparison_chart(m1, m2, "Market A", "Market B")
        assert isinstance(result, str)
        assert "Market A" in result
        assert "Market B" in result
