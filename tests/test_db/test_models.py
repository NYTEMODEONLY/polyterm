"""Tests for database models serialization"""

import pytest
import json
from datetime import datetime

from polyterm.db.models import Wallet, Alert


class TestWalletSerialization:
    """Test Wallet to_dict / from_dict round-trip"""

    def test_tags_not_double_encoded(self):
        """Wallet.to_dict() tags should be a list, not a JSON string"""
        wallet = Wallet(
            address="0xtest",
            first_seen=datetime.now(),
            tags=["whale", "tracked"],
        )
        d = wallet.to_dict()
        # Should be a Python list, not a JSON string
        assert isinstance(d['tags'], list)
        assert d['tags'] == ["whale", "tracked"]

    def test_favorite_markets_not_double_encoded(self):
        """Wallet.to_dict() favorite_markets should be a list"""
        wallet = Wallet(
            address="0xtest",
            first_seen=datetime.now(),
            favorite_markets=["market1", "market2"],
        )
        d = wallet.to_dict()
        assert isinstance(d['favorite_markets'], list)
        assert d['favorite_markets'] == ["market1", "market2"]

    def test_json_output_correct(self):
        """JSON serialization should produce proper arrays"""
        wallet = Wallet(
            address="0xtest",
            first_seen=datetime.now(),
            tags=["whale"],
            favorite_markets=["m1"],
        )
        d = wallet.to_dict()
        json_str = json.dumps(d, default=str)
        parsed = json.loads(json_str)

        # Tags should be a list in the final JSON
        assert isinstance(parsed['tags'], list)
        assert parsed['tags'] == ["whale"]

    def test_round_trip_preserves_tags(self):
        """Tags should survive to_dict -> from_dict round trip"""
        original = Wallet(
            address="0xtest",
            first_seen=datetime.now(),
            tags=["whale", "smart_money"],
        )
        d = original.to_dict()
        restored = Wallet.from_dict(d)
        assert restored.tags == ["whale", "smart_money"]

    def test_from_dict_handles_json_string_tags(self):
        """from_dict should handle tags as JSON string (from database)"""
        d = {
            'address': '0xtest',
            'first_seen': datetime.now().isoformat(),
            'tags': '["whale", "tracked"]',
        }
        wallet = Wallet.from_dict(d)
        assert wallet.tags == ["whale", "tracked"]


class TestAlertSerialization:
    """Test Alert to_dict / from_dict"""

    def test_data_not_double_encoded(self):
        """Alert.to_dict() data should be a dict, not a JSON string"""
        alert = Alert(
            alert_type="whale",
            market_id="m1",
            severity=80,
            message="Big trade",
            data={"notional": 50000, "wallet": "0xabc"},
        )
        d = alert.to_dict()
        assert isinstance(d['data'], dict)
        assert d['data']['notional'] == 50000

    def test_json_output_correct(self):
        """JSON output should have data as a nested object"""
        alert = Alert(
            alert_type="whale",
            market_id="m1",
            severity=80,
            message="Big trade",
            data={"size": 100},
        )
        d = alert.to_dict()
        json_str = json.dumps(d, default=str)
        parsed = json.loads(json_str)
        assert isinstance(parsed['data'], dict)
        assert parsed['data']['size'] == 100

    def test_round_trip_preserves_data(self):
        """Data should survive to_dict -> from_dict round trip"""
        original = Alert(
            alert_type="test",
            market_id="m1",
            severity=50,
            message="test",
            data={"key": "value"},
        )
        d = original.to_dict()
        restored = Alert.from_dict(d)
        assert restored.data == {"key": "value"}

    def test_from_dict_handles_json_string_data(self):
        """from_dict should handle data as JSON string (from database)"""
        d = {
            'alert_type': 'whale',
            'market_id': 'm1',
            'severity': 80,
            'message': 'test',
            'data': '{"notional": 50000}',
        }
        alert = Alert.from_dict(d)
        assert alert.data == {"notional": 50000}
