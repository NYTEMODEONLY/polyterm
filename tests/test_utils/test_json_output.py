"""Tests for JSON output utilities"""

import json
import pytest
from datetime import datetime
from dataclasses import dataclass
from polyterm.utils.json_output import (
    JSONEncoder,
    output_json,
    print_json,
    format_market_json,
    format_trade_json,
    format_wallet_json,
    safe_float,
)


class TestSafeFloat:
    """Test safe_float helper"""

    def test_normal_float(self):
        assert safe_float(3.14) == 3.14

    def test_int(self):
        assert safe_float(42) == 42.0

    def test_numeric_string(self):
        assert safe_float("3.14") == 3.14

    def test_empty_string(self):
        assert safe_float("") == 0.0

    def test_none(self):
        assert safe_float(None) == 0.0

    def test_non_numeric_string(self):
        assert safe_float("N/A") == 0.0

    def test_zero(self):
        assert safe_float(0) == 0.0

    def test_custom_default(self):
        assert safe_float(None, default=-1.0) == -1.0

    def test_negative_number(self):
        assert safe_float("-5.5") == -5.5


class TestJSONEncoder:
    """Test custom JSON encoder"""

    def test_datetime_serialization(self):
        """Datetime should serialize to ISO format"""
        dt = datetime(2025, 1, 15, 12, 30, 0)
        result = json.dumps({"time": dt}, cls=JSONEncoder)
        data = json.loads(result)
        assert data["time"] == "2025-01-15T12:30:00"

    def test_dataclass_serialization(self):
        """Dataclasses should serialize to dict"""
        @dataclass
        class TestData:
            name: str
            value: int

        obj = TestData(name="test", value=42)
        result = json.dumps(obj, cls=JSONEncoder)
        data = json.loads(result)
        assert data["name"] == "test"
        assert data["value"] == 42

    def test_object_with_to_dict(self):
        """Objects with to_dict() should use it"""
        class Custom:
            def to_dict(self):
                return {"key": "value"}

        result = json.dumps(Custom(), cls=JSONEncoder)
        data = json.loads(result)
        assert data["key"] == "value"

    def test_simple_types(self):
        """Strings, ints, floats, bools should serialize normally"""
        data = {"s": "hello", "i": 42, "f": 3.14, "b": True, "n": None}
        result = json.dumps(data, cls=JSONEncoder)
        parsed = json.loads(result)
        assert parsed == data


class TestOutputJson:
    """Test output_json function"""

    def test_pretty_output(self):
        result = output_json({"key": "value"}, pretty=True)
        assert "\n" in result  # Pretty print has newlines

    def test_compact_output(self):
        result = output_json({"key": "value"}, pretty=False)
        assert "\n" not in result


class TestFormatMarketJson:
    """Test market formatting"""

    def test_basic_market(self):
        """Format a basic market with all fields"""
        market = {
            "id": "market-123",
            "slug": "test-market",
            "question": "Will it rain?",
            "outcomePrices": '["0.65", "0.35"]',
            "volume24hr": "100000",
            "liquidity": "50000",
            "endDate": "2025-12-31",
            "active": True,
            "closed": False,
        }
        result = format_market_json(market)
        assert result["id"] == "market-123"
        assert result["title"] == "Will it rain?"
        assert abs(result["yes_price"] - 0.65) < 0.001
        assert abs(result["no_price"] - 0.35) < 0.001
        assert result["probability"] == pytest.approx(65.0, abs=0.1)
        assert result["volume_24h"] == 100000.0
        assert result["liquidity"] == 50000.0

    def test_missing_outcome_prices(self):
        """Market with no outcome prices should default to 0"""
        market = {"id": "no-prices"}
        result = format_market_json(market)
        assert result["yes_price"] == 0
        assert result["no_price"] == 1

    def test_malformed_outcome_prices(self):
        """Malformed outcomePrices should not crash"""
        market = {"id": "bad-prices", "outcomePrices": "not_json"}
        result = format_market_json(market)
        assert result["yes_price"] == 0

    def test_single_outcome_price(self):
        """Single outcome price should infer NO price"""
        market = {"id": "single", "outcomePrices": '["0.70"]'}
        result = format_market_json(market)
        assert abs(result["yes_price"] - 0.70) < 0.001
        assert abs(result["no_price"] - 0.30) < 0.001

    def test_volume_as_string(self):
        """Volume as string should be converted to float"""
        market = {"id": "str-vol", "volume24hr": "99999.50"}
        result = format_market_json(market)
        assert result["volume_24h"] == 99999.50

    def test_non_numeric_volume(self):
        """Non-numeric volume should not crash"""
        market = {"id": "bad-vol", "volume24hr": "N/A"}
        result = format_market_json(market)
        assert result["volume_24h"] == 0.0


class TestFormatTradeJson:
    """Test trade formatting"""

    def test_basic_trade(self):
        trade = {
            "market_id": "m-1",
            "side": "BUY",
            "outcome": "YES",
            "price": "0.65",
            "size": "100",
            "notional": "65",
        }
        result = format_trade_json(trade)
        assert result["market_id"] == "m-1"
        assert result["price"] == 0.65
        assert result["size"] == 100.0
        assert result["notional"] == 65.0

    def test_missing_fields(self):
        """Missing fields should default gracefully"""
        result = format_trade_json({})
        assert result["price"] == 0.0
        assert result["size"] == 0.0


class TestFormatWalletJson:
    """Test wallet formatting"""

    def test_dict_wallet(self):
        wallet = {
            "address": "0x123",
            "total_trades": 50,
            "total_volume": 150000,
            "win_rate": 0.75,
        }
        result = format_wallet_json(wallet)
        assert result["address"] == "0x123"
        assert result["is_whale"] is True  # volume >= 100000
        assert result["is_smart_money"] is True  # win_rate >= 0.70 and trades >= 10

    def test_small_wallet(self):
        wallet = {
            "address": "0x456",
            "total_trades": 3,
            "total_volume": 500,
            "win_rate": 0.50,
        }
        result = format_wallet_json(wallet)
        assert result["is_whale"] is False
        assert result["is_smart_money"] is False
