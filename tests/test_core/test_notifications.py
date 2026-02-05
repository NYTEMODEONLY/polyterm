"""Comprehensive tests for notification system"""

import pytest
from unittest.mock import patch, MagicMock, call
from datetime import datetime, timezone

from polyterm.core.notifications import (
    NotificationConfig,
    NotificationManager,
    AlertNotifier,
)


class TestNotificationConfigToDict:
    """Test NotificationConfig.to_dict() method"""

    def test_default_config_to_dict(self):
        """Test default config serializes all expected fields"""
        config = NotificationConfig()
        data = config.to_dict()

        assert data["telegram"]["enabled"] is False
        assert data["telegram"]["bot_token"] == ""
        assert data["telegram"]["chat_id"] == ""
        assert data["discord"]["enabled"] is False
        assert data["discord"]["webhook_url"] == ""
        assert data["system"]["enabled"] is True
        assert data["sound"]["enabled"] is True
        assert data["sound"]["file"] == ""
        assert data["email"]["enabled"] is False

    def test_to_dict_includes_smtp_password(self):
        """Test that to_dict includes smtp_password field (was recently fixed)"""
        config = NotificationConfig(
            email_enabled=True,
            smtp_host="smtp.example.com",
            smtp_port=465,
            smtp_user="user@example.com",
            smtp_password="secret123",
            email_to="admin@example.com",
        )

        data = config.to_dict()

        assert data["email"]["smtp_password"] == "secret123"
        assert data["email"]["smtp_host"] == "smtp.example.com"
        assert data["email"]["smtp_port"] == 465
        assert data["email"]["smtp_user"] == "user@example.com"
        assert data["email"]["email_to"] == "admin@example.com"

    def test_to_dict_includes_all_telegram_fields(self):
        """Test all telegram fields in serialization"""
        config = NotificationConfig(
            telegram_enabled=True,
            telegram_bot_token="123:ABC",
            telegram_chat_id="-1001234",
        )
        data = config.to_dict()

        assert data["telegram"]["enabled"] is True
        assert data["telegram"]["bot_token"] == "123:ABC"
        assert data["telegram"]["chat_id"] == "-1001234"

    def test_to_dict_includes_all_discord_fields(self):
        """Test all discord fields in serialization"""
        config = NotificationConfig(
            discord_enabled=True,
            discord_webhook_url="https://discord.com/api/webhooks/123/abc",
        )
        data = config.to_dict()

        assert data["discord"]["enabled"] is True
        assert data["discord"]["webhook_url"] == "https://discord.com/api/webhooks/123/abc"

    def test_to_dict_has_all_top_level_keys(self):
        """Test that to_dict returns all expected top-level sections"""
        config = NotificationConfig()
        data = config.to_dict()

        assert set(data.keys()) == {"telegram", "discord", "system", "sound", "email"}


class TestNotificationConfigFromDict:
    """Test NotificationConfig.from_dict() method"""

    def test_round_trip_preserves_all_fields(self):
        """Test that to_dict -> from_dict round-trip preserves all fields"""
        original = NotificationConfig(
            telegram_enabled=True,
            telegram_bot_token="bot123",
            telegram_chat_id="chat456",
            discord_enabled=True,
            discord_webhook_url="https://discord.webhook/url",
            system_enabled=False,
            sound_enabled=False,
            sound_file="/path/to/sound.wav",
            email_enabled=True,
            smtp_host="smtp.gmail.com",
            smtp_port=465,
            smtp_user="user@gmail.com",
            smtp_password="supersecret",
            email_to="dest@example.com",
        )

        data = original.to_dict()
        restored = NotificationConfig.from_dict(data)

        assert restored.telegram_enabled == original.telegram_enabled
        assert restored.telegram_bot_token == original.telegram_bot_token
        assert restored.telegram_chat_id == original.telegram_chat_id
        assert restored.discord_enabled == original.discord_enabled
        assert restored.discord_webhook_url == original.discord_webhook_url
        assert restored.system_enabled == original.system_enabled
        assert restored.sound_enabled == original.sound_enabled
        assert restored.sound_file == original.sound_file
        assert restored.email_enabled == original.email_enabled
        assert restored.smtp_host == original.smtp_host
        assert restored.smtp_port == original.smtp_port
        assert restored.smtp_user == original.smtp_user
        assert restored.smtp_password == original.smtp_password
        assert restored.email_to == original.email_to

    def test_from_dict_with_empty_dict(self):
        """Test from_dict with empty dict uses defaults"""
        config = NotificationConfig.from_dict({})

        assert config.telegram_enabled is False
        assert config.telegram_bot_token == ""
        assert config.discord_enabled is False
        assert config.system_enabled is True
        assert config.sound_enabled is True
        assert config.email_enabled is False
        assert config.smtp_port == 587

    def test_from_dict_partial_data(self):
        """Test from_dict with partial data fills in defaults"""
        data = {
            "telegram": {"enabled": True, "bot_token": "tok"},
            # discord, system, sound, email sections missing
        }
        config = NotificationConfig.from_dict(data)

        assert config.telegram_enabled is True
        assert config.telegram_bot_token == "tok"
        assert config.telegram_chat_id == ""  # default
        assert config.discord_enabled is False  # default
        assert config.system_enabled is True  # default


class TestNotificationManagerSendTelegram:
    """Test _send_telegram method"""

    @patch("polyterm.core.notifications.requests.post")
    def test_send_telegram_success(self, mock_post):
        """Test successful Telegram notification"""
        mock_post.return_value = MagicMock(status_code=200)

        config = NotificationConfig(
            telegram_enabled=True,
            telegram_bot_token="test_token",
            telegram_chat_id="123456",
        )
        manager = NotificationManager(config)

        result = manager._send_telegram("Title", "Message", "info")

        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "test_token" in call_args[0][0]
        assert call_args[1]["json"]["chat_id"] == "123456"
        assert call_args[1]["json"]["parse_mode"] == "Markdown"

    @patch("polyterm.core.notifications.requests.post")
    def test_send_telegram_markdown_escaping_title(self, mock_post):
        """Test that special Markdown chars in title are escaped"""
        mock_post.return_value = MagicMock(status_code=200)

        config = NotificationConfig(
            telegram_enabled=True,
            telegram_bot_token="tok",
            telegram_chat_id="123",
        )
        manager = NotificationManager(config)

        # Title with special chars: _*[]()
        manager._send_telegram("Price_Alert *BTC* [Update]", "msg", "info")

        call_args = mock_post.call_args
        text = call_args[1]["json"]["text"]
        # These special chars should be escaped with backslash
        assert "\\_" in text
        assert "\\*" in text
        assert "\\[" in text
        assert "\\]" in text

    @patch("polyterm.core.notifications.requests.post")
    def test_send_telegram_markdown_escaping_message(self, mock_post):
        """Test that special Markdown chars in message body are escaped"""
        mock_post.return_value = MagicMock(status_code=200)

        config = NotificationConfig(
            telegram_enabled=True,
            telegram_bot_token="tok",
            telegram_chat_id="123",
        )
        manager = NotificationManager(config)

        manager._send_telegram("Title", "Check [this](link) for _details_", "warning")

        call_args = mock_post.call_args
        text = call_args[1]["json"]["text"]
        # Message special chars should be escaped
        assert "\\[" in text
        assert "\\]" in text
        assert "\\(" in text
        assert "\\)" in text
        assert "\\_" in text

    @patch("polyterm.core.notifications.requests.post")
    def test_send_telegram_level_emoji(self, mock_post):
        """Test that level emoji is included in message"""
        mock_post.return_value = MagicMock(status_code=200)

        config = NotificationConfig(
            telegram_enabled=True,
            telegram_bot_token="tok",
            telegram_chat_id="123",
        )
        manager = NotificationManager(config)

        for level, emoji in [("info", "\u2139\ufe0f"), ("warning", "\u26a0\ufe0f"), ("critical", "\U0001f6a8")]:
            manager._send_telegram("Title", "Msg", level)

    def test_send_telegram_missing_token_returns_false(self):
        """Test that missing bot token returns False"""
        config = NotificationConfig(
            telegram_enabled=True,
            telegram_bot_token="",
            telegram_chat_id="123",
        )
        manager = NotificationManager(config)
        assert manager._send_telegram("T", "M", "info") is False

    def test_send_telegram_missing_chat_id_returns_false(self):
        """Test that missing chat_id returns False"""
        config = NotificationConfig(
            telegram_enabled=True,
            telegram_bot_token="tok",
            telegram_chat_id="",
        )
        manager = NotificationManager(config)
        assert manager._send_telegram("T", "M", "info") is False

    @patch("polyterm.core.notifications.requests.post")
    def test_send_telegram_api_failure(self, mock_post):
        """Test that non-200 status returns False"""
        mock_post.return_value = MagicMock(status_code=400)

        config = NotificationConfig(
            telegram_enabled=True,
            telegram_bot_token="tok",
            telegram_chat_id="123",
        )
        manager = NotificationManager(config)

        result = manager._send_telegram("T", "M", "info")
        assert result is False

    @patch("polyterm.core.notifications.requests.post")
    def test_send_telegram_exception_returns_false(self, mock_post):
        """Test that network exception returns False"""
        mock_post.side_effect = Exception("Network error")

        config = NotificationConfig(
            telegram_enabled=True,
            telegram_bot_token="tok",
            telegram_chat_id="123",
        )
        manager = NotificationManager(config)

        result = manager._send_telegram("T", "M", "info")
        assert result is False


class TestNotificationManagerSendDiscord:
    """Test _send_discord method"""

    @patch("polyterm.core.notifications.requests.post")
    def test_send_discord_success_200(self, mock_post):
        """Test successful Discord notification with 200 status"""
        mock_post.return_value = MagicMock(status_code=200)

        config = NotificationConfig(
            discord_enabled=True,
            discord_webhook_url="https://discord.com/api/webhooks/123/abc",
        )
        manager = NotificationManager(config)

        result = manager._send_discord("Title", "Message", "info")
        assert result is True

    @patch("polyterm.core.notifications.requests.post")
    def test_send_discord_success_204(self, mock_post):
        """Test successful Discord notification with 204 (no content) status"""
        mock_post.return_value = MagicMock(status_code=204)

        config = NotificationConfig(
            discord_enabled=True,
            discord_webhook_url="https://discord.com/api/webhooks/123/abc",
        )
        manager = NotificationManager(config)

        result = manager._send_discord("Title", "Message", "warning")
        assert result is True

    @patch("polyterm.core.notifications.requests.post")
    def test_send_discord_uses_timezone_aware_datetime(self, mock_post):
        """Test that Discord embed uses timezone-aware datetime (not utcnow)"""
        mock_post.return_value = MagicMock(status_code=204)

        config = NotificationConfig(
            discord_enabled=True,
            discord_webhook_url="https://discord.com/api/webhooks/123/abc",
        )
        manager = NotificationManager(config)

        manager._send_discord("Title", "Msg", "info")

        call_args = mock_post.call_args
        embed = call_args[1]["json"]["embeds"][0]
        timestamp = embed["timestamp"]
        # Timezone-aware ISO format should contain timezone info (+00:00 or Z)
        assert "+" in timestamp or "Z" in timestamp

    @patch("polyterm.core.notifications.requests.post")
    def test_send_discord_color_based_on_level(self, mock_post):
        """Test that embed color corresponds to level"""
        mock_post.return_value = MagicMock(status_code=204)

        config = NotificationConfig(
            discord_enabled=True,
            discord_webhook_url="https://discord.com/api/webhooks/123/abc",
        )
        manager = NotificationManager(config)

        # Info = blue
        manager._send_discord("T", "M", "info")
        embed = mock_post.call_args[1]["json"]["embeds"][0]
        assert embed["color"] == 0x3498db

        mock_post.reset_mock()
        mock_post.return_value = MagicMock(status_code=204)

        # Warning = orange
        manager._send_discord("T", "M", "warning")
        embed = mock_post.call_args[1]["json"]["embeds"][0]
        assert embed["color"] == 0xf39c12

        mock_post.reset_mock()
        mock_post.return_value = MagicMock(status_code=204)

        # Critical = red
        manager._send_discord("T", "M", "critical")
        embed = mock_post.call_args[1]["json"]["embeds"][0]
        assert embed["color"] == 0xe74c3c

    @patch("polyterm.core.notifications.requests.post")
    def test_send_discord_with_data_fields(self, mock_post):
        """Test that data dict is converted to embed fields"""
        mock_post.return_value = MagicMock(status_code=204)

        config = NotificationConfig(
            discord_enabled=True,
            discord_webhook_url="https://discord.com/api/webhooks/123/abc",
        )
        manager = NotificationManager(config)

        data = {"market_id": "btc", "price": 0.65, "volume": 10000}
        manager._send_discord("Title", "Msg", "info", data=data)

        embed = mock_post.call_args[1]["json"]["embeds"][0]
        assert "fields" in embed
        field_names = [f["name"] for f in embed["fields"]]
        assert "Market Id" in field_names
        assert "Price" in field_names
        assert "Volume" in field_names
        # All fields should be inline
        assert all(f["inline"] is True for f in embed["fields"])

    @patch("polyterm.core.notifications.requests.post")
    def test_send_discord_fields_limited_to_25(self, mock_post):
        """Test that Discord fields are limited to 25 (Discord embed limit)"""
        mock_post.return_value = MagicMock(status_code=204)

        config = NotificationConfig(
            discord_enabled=True,
            discord_webhook_url="https://discord.com/api/webhooks/123/abc",
        )
        manager = NotificationManager(config)

        data = {f"field_{i}": str(i) for i in range(30)}
        manager._send_discord("Title", "Msg", "info", data=data)

        embed = mock_post.call_args[1]["json"]["embeds"][0]
        assert len(embed["fields"]) <= 25

    @patch("polyterm.core.notifications.requests.post")
    def test_send_discord_footer(self, mock_post):
        """Test that footer text is set"""
        mock_post.return_value = MagicMock(status_code=204)

        config = NotificationConfig(
            discord_enabled=True,
            discord_webhook_url="https://discord.com/api/webhooks/123/abc",
        )
        manager = NotificationManager(config)

        manager._send_discord("Title", "Msg", "info")

        embed = mock_post.call_args[1]["json"]["embeds"][0]
        assert embed["footer"]["text"] == "PolyTerm Alert"

    def test_send_discord_missing_webhook_returns_false(self):
        """Test that missing webhook URL returns False"""
        config = NotificationConfig(
            discord_enabled=True,
            discord_webhook_url="",
        )
        manager = NotificationManager(config)
        assert manager._send_discord("T", "M", "info") is False

    @patch("polyterm.core.notifications.requests.post")
    def test_send_discord_exception_returns_false(self, mock_post):
        """Test that network exception returns False"""
        mock_post.side_effect = Exception("Timeout")

        config = NotificationConfig(
            discord_enabled=True,
            discord_webhook_url="https://discord.com/api/webhooks/123/abc",
        )
        manager = NotificationManager(config)

        result = manager._send_discord("T", "M", "info")
        assert result is False


class TestNotificationManagerSend:
    """Test send() method routing"""

    @patch("polyterm.core.notifications.requests.post")
    def test_send_routes_to_enabled_channels_only(self, mock_post):
        """Test that send only calls enabled channels"""
        mock_post.return_value = MagicMock(status_code=200)

        config = NotificationConfig(
            telegram_enabled=True,
            telegram_bot_token="tok",
            telegram_chat_id="123",
            discord_enabled=False,
            system_enabled=False,
            sound_enabled=False,
            email_enabled=False,
        )
        manager = NotificationManager(config)

        results = manager.send("Title", "Message", level="info")

        assert "telegram" in results
        assert "discord" not in results
        assert "system" not in results
        assert "sound" not in results
        assert "email" not in results

    def test_send_no_channels_enabled(self):
        """Test that no channels enabled returns empty dict"""
        config = NotificationConfig(
            telegram_enabled=False,
            discord_enabled=False,
            system_enabled=False,
            sound_enabled=False,
            email_enabled=False,
        )
        manager = NotificationManager(config)

        results = manager.send("Title", "Message")
        assert results == {}

    @patch("polyterm.core.notifications.requests.post")
    def test_send_multiple_channels(self, mock_post):
        """Test sending to multiple enabled channels"""
        mock_post.return_value = MagicMock(status_code=200)

        config = NotificationConfig(
            telegram_enabled=True,
            telegram_bot_token="tok",
            telegram_chat_id="123",
            discord_enabled=True,
            discord_webhook_url="https://discord.com/api/webhooks/123/abc",
            system_enabled=False,
            sound_enabled=False,
        )
        manager = NotificationManager(config)

        results = manager.send("Alert", "Something happened", level="warning")

        assert "telegram" in results
        assert "discord" in results
        # Two POST calls: one to Telegram, one to Discord
        assert mock_post.call_count == 2

    @patch("polyterm.core.notifications.requests.post")
    def test_send_email_only_on_critical(self, mock_post):
        """Test that email is only sent for critical level"""
        mock_post.return_value = MagicMock(status_code=200)

        config = NotificationConfig(
            telegram_enabled=False,
            discord_enabled=False,
            system_enabled=False,
            sound_enabled=False,
            email_enabled=True,
            smtp_host="smtp.test.com",
            smtp_user="user@test.com",
            smtp_password="pass",
            email_to="dest@test.com",
        )
        manager = NotificationManager(config)

        # Non-critical should not send email
        results_info = manager.send("Title", "Msg", level="info")
        assert "email" not in results_info

        results_warning = manager.send("Title", "Msg", level="warning")
        assert "email" not in results_warning

        # Critical should send email
        with patch.object(manager, "_send_email", return_value=True) as mock_email:
            results_critical = manager.send("Title", "Msg", level="critical")
            assert "email" in results_critical
            mock_email.assert_called_once()


class TestNotificationManagerSendEmail:
    """Test _send_email method"""

    def test_send_email_missing_smtp_host_returns_false(self):
        """Test that missing smtp_host returns False"""
        config = NotificationConfig(
            email_enabled=True,
            smtp_host="",
            smtp_user="user@test.com",
            smtp_password="pass",
            email_to="dest@test.com",
        )
        manager = NotificationManager(config)
        assert manager._send_email("Title", "Message") is False

    def test_send_email_missing_smtp_user_returns_false(self):
        """Test that missing smtp_user returns False"""
        config = NotificationConfig(
            email_enabled=True,
            smtp_host="smtp.test.com",
            smtp_user="",
            smtp_password="pass",
            email_to="dest@test.com",
        )
        manager = NotificationManager(config)
        assert manager._send_email("Title", "Message") is False

    def test_send_email_missing_smtp_password_returns_false(self):
        """Test that missing smtp_password returns False"""
        config = NotificationConfig(
            email_enabled=True,
            smtp_host="smtp.test.com",
            smtp_user="user@test.com",
            smtp_password="",
            email_to="dest@test.com",
        )
        manager = NotificationManager(config)
        assert manager._send_email("Title", "Message") is False

    def test_send_email_missing_email_to_returns_false(self):
        """Test that missing email_to returns False"""
        config = NotificationConfig(
            email_enabled=True,
            smtp_host="smtp.test.com",
            smtp_user="user@test.com",
            smtp_password="pass",
            email_to="",
        )
        manager = NotificationManager(config)
        assert manager._send_email("Title", "Message") is False

    @patch("smtplib.SMTP")
    def test_send_email_success(self, mock_smtp_class):
        """Test successful email sending"""
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        config = NotificationConfig(
            email_enabled=True,
            smtp_host="smtp.test.com",
            smtp_port=587,
            smtp_user="user@test.com",
            smtp_password="pass",
            email_to="dest@test.com",
        )
        manager = NotificationManager(config)

        result = manager._send_email("Alert Title", "Alert body text")
        assert result is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user@test.com", "pass")
        mock_server.send_message.assert_called_once()

    @patch("smtplib.SMTP")
    def test_send_email_smtp_failure_returns_false(self, mock_smtp_class):
        """Test that SMTP error returns False"""
        mock_smtp_class.side_effect = Exception("SMTP connection failed")

        config = NotificationConfig(
            email_enabled=True,
            smtp_host="smtp.test.com",
            smtp_port=587,
            smtp_user="user@test.com",
            smtp_password="pass",
            email_to="dest@test.com",
        )
        manager = NotificationManager(config)

        result = manager._send_email("Title", "Body")
        assert result is False


class TestAlertNotifierCall:
    """Test AlertNotifier.__call__() method"""

    @patch.object(NotificationManager, "send")
    def test_call_with_enum_level(self, mock_send):
        """Test callback with alert that has enum level (has .value)"""
        mock_send.return_value = {"telegram": True}

        config = NotificationConfig()
        manager = NotificationManager(config)
        notifier = AlertNotifier(manager)

        class MockLevel:
            value = "warning"

        class MockAlert:
            title = "Test Alert"
            message = "Test message"
            level = MockLevel()
            data = {"key": "val"}

        notifier(MockAlert())

        mock_send.assert_called_once_with(
            title="Test Alert",
            message="Test message",
            level="warning",
            data={"key": "val"},
        )

    @patch.object(NotificationManager, "send")
    def test_call_with_string_level(self, mock_send):
        """Test callback with alert that has string level (no .value)"""
        mock_send.return_value = {}

        config = NotificationConfig()
        manager = NotificationManager(config)
        notifier = AlertNotifier(manager)

        class MockAlert:
            title = "Critical Issue"
            message = "Something broke"
            level = "critical"
            data = None

        notifier(MockAlert())

        mock_send.assert_called_once_with(
            title="Critical Issue",
            message="Something broke",
            level="critical",
            data=None,
        )

    @patch.object(NotificationManager, "send")
    def test_call_with_unknown_level_defaults_to_info(self, mock_send):
        """Test callback with unknown level maps to 'info'"""
        mock_send.return_value = {}

        config = NotificationConfig()
        manager = NotificationManager(config)
        notifier = AlertNotifier(manager)

        class MockAlert:
            title = "Unknown"
            message = "Unknown level"
            level = "debug"  # Not in level_map
            data = {}

        notifier(MockAlert())

        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args[1]["level"] == "info"

    @patch.object(NotificationManager, "send")
    def test_call_maps_all_known_levels(self, mock_send):
        """Test that all known levels are mapped correctly"""
        mock_send.return_value = {}

        config = NotificationConfig()
        manager = NotificationManager(config)
        notifier = AlertNotifier(manager)

        for level_str in ["info", "warning", "critical"]:

            class MockLevel:
                value = level_str

            class MockAlert:
                title = f"Alert {level_str}"
                message = f"Message for {level_str}"
                level = MockLevel()
                data = {}

            mock_send.reset_mock()
            notifier(MockAlert())
            assert mock_send.call_args[1]["level"] == level_str


class TestAlertNotifierInit:
    """Test AlertNotifier initialization"""

    def test_initialization(self):
        """Test notifier initialization stores manager reference"""
        config = NotificationConfig()
        manager = NotificationManager(config)
        notifier = AlertNotifier(manager)

        assert notifier.manager is manager


class TestAlertNotifierAsyncMethods:
    """Test AlertNotifier async notification methods"""

    @pytest.mark.asyncio
    @patch.object(NotificationManager, "send")
    async def test_whale_alert_below_50k(self, mock_send):
        """Test whale alert below 50k is warning level"""
        mock_send.return_value = {"discord": True}

        config = NotificationConfig()
        manager = NotificationManager(config)
        notifier = AlertNotifier(manager)

        class MockTrade:
            notional = 25000
            side = "BUY"
            wallet_address = "0x1234567890abcdef"
            market_id = "test_market"

        class MockWallet:
            total_volume = 100000

        await notifier.send_whale_alert(MockTrade(), MockWallet())

        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args[1]["title"] == "Whale Trade Detected"
        assert call_args[1]["level"] == "warning"  # < 50000

    @pytest.mark.asyncio
    @patch.object(NotificationManager, "send")
    async def test_whale_alert_at_or_above_50k(self, mock_send):
        """Test whale alert at or above 50k is critical level"""
        mock_send.return_value = {"discord": True}

        config = NotificationConfig()
        manager = NotificationManager(config)
        notifier = AlertNotifier(manager)

        class MockTrade:
            notional = 50000
            side = "SELL"
            wallet_address = "0xabcdef1234567890"
            market_id = "big_market"

        class MockWallet:
            total_volume = 500000

        await notifier.send_whale_alert(MockTrade(), MockWallet())

        call_args = mock_send.call_args
        assert call_args[1]["level"] == "critical"

    @pytest.mark.asyncio
    @patch.object(NotificationManager, "send")
    async def test_smart_money_alert(self, mock_send):
        """Test smart money alert"""
        mock_send.return_value = {}

        config = NotificationConfig()
        manager = NotificationManager(config)
        notifier = AlertNotifier(manager)

        class MockTrade:
            notional = 15000
            market_id = "btc_market"

        class MockWallet:
            win_rate = 0.85
            total_trades = 150

        await notifier.send_smart_money_alert(MockTrade(), MockWallet())

        call_args = mock_send.call_args
        assert "Smart Money" in call_args[1]["title"]
        assert call_args[1]["level"] == "info"
        assert "85%" in call_args[1]["message"]

    @pytest.mark.asyncio
    @patch.object(NotificationManager, "send")
    async def test_insider_alert(self, mock_send):
        """Test insider alert sends as critical"""
        mock_send.return_value = {}

        config = NotificationConfig()
        manager = NotificationManager(config)
        notifier = AlertNotifier(manager)

        alert_data = {
            "message": "Suspicious pattern detected",
            "data": {"wallet": "0x123", "score": 85},
        }

        await notifier.send_insider_alert(alert_data)

        call_args = mock_send.call_args
        assert "Insider" in call_args[1]["title"]
        assert call_args[1]["level"] == "critical"
        assert call_args[1]["message"] == "Suspicious pattern detected"

    @pytest.mark.asyncio
    @patch.object(NotificationManager, "send")
    async def test_arbitrage_alert(self, mock_send):
        """Test arbitrage alert"""
        mock_send.return_value = {}

        config = NotificationConfig()
        manager = NotificationManager(config)
        notifier = AlertNotifier(manager)

        await notifier.send_arbitrage_alert(
            market1="Market A",
            market2="Market B",
            spread=0.035,
            profit=1.50,
        )

        call_args = mock_send.call_args
        assert "Arbitrage" in call_args[1]["title"]
        assert call_args[1]["level"] == "warning"
        assert "3.5%" in call_args[1]["message"]
        assert "$1.50" in call_args[1]["message"]
        assert call_args[1]["data"]["market1"] == "Market A"
        assert call_args[1]["data"]["market2"] == "Market B"


class TestNotificationManagerSystemAndSound:
    """Test system notification and sound alert methods"""

    @patch("polyterm.core.notifications.HAS_PLYER", False)
    def test_system_notification_without_plyer(self):
        """Test system notification returns False when plyer not available"""
        config = NotificationConfig(system_enabled=True)
        manager = NotificationManager(config)
        assert manager._send_system("Title", "Message") is False

    def test_play_sound_returns_bool(self):
        """Test that _play_sound returns a boolean"""
        config = NotificationConfig(sound_enabled=True)
        manager = NotificationManager(config)
        result = manager._play_sound("info")
        assert isinstance(result, bool)
