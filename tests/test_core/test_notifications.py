"""Tests for notification system"""

import pytest
from unittest.mock import patch, MagicMock

from polyterm.core.notifications import (
    NotificationConfig,
    NotificationManager,
    AlertNotifier,
)


class TestNotificationConfig:
    """Test NotificationConfig dataclass"""

    def test_default_config(self):
        """Test default configuration"""
        config = NotificationConfig()

        assert config.telegram_enabled is False
        assert config.discord_enabled is False
        assert config.system_enabled is True
        assert config.sound_enabled is True

    def test_config_to_dict(self):
        """Test config serialization"""
        config = NotificationConfig(
            telegram_enabled=True,
            telegram_bot_token="test_token",
            telegram_chat_id="123",
        )

        data = config.to_dict()

        assert data['telegram']['enabled'] is True
        assert data['telegram']['bot_token'] == "test_token"
        assert data['telegram']['chat_id'] == "123"

    def test_config_from_dict(self):
        """Test config deserialization"""
        data = {
            'telegram': {
                'enabled': True,
                'bot_token': 'token123',
                'chat_id': '456',
            },
            'discord': {
                'enabled': True,
                'webhook_url': 'https://discord.webhook/test',
            },
        }

        config = NotificationConfig.from_dict(data)

        assert config.telegram_enabled is True
        assert config.telegram_bot_token == 'token123'
        assert config.discord_enabled is True
        assert config.discord_webhook_url == 'https://discord.webhook/test'


class TestNotificationManager:
    """Test NotificationManager class"""

    def test_manager_initialization(self):
        """Test manager initialization"""
        config = NotificationConfig()
        manager = NotificationManager(config)

        assert manager.config == config

    def test_send_disabled_channels(self):
        """Test sending when all channels disabled"""
        config = NotificationConfig(
            telegram_enabled=False,
            discord_enabled=False,
            system_enabled=False,
            sound_enabled=False,
        )
        manager = NotificationManager(config)

        results = manager.send("Test", "Test message")

        # No channels enabled, should be empty
        assert results == {}

    @patch('polyterm.core.notifications.requests.post')
    def test_telegram_send(self, mock_post):
        """Test Telegram notification"""
        mock_post.return_value = MagicMock(status_code=200)

        config = NotificationConfig(
            telegram_enabled=True,
            telegram_bot_token='test_token',
            telegram_chat_id='123456',
        )
        manager = NotificationManager(config)

        result = manager._send_telegram("Test Title", "Test message", "info")

        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert 'test_token' in call_args[0][0]
        assert call_args[1]['json']['chat_id'] == '123456'

    @patch('polyterm.core.notifications.requests.post')
    def test_discord_send(self, mock_post):
        """Test Discord webhook notification"""
        mock_post.return_value = MagicMock(status_code=204)

        config = NotificationConfig(
            discord_enabled=True,
            discord_webhook_url='https://discord.com/api/webhooks/test',
        )
        manager = NotificationManager(config)

        result = manager._send_discord(
            "Test Title",
            "Test message",
            "warning",
            {'extra': 'data'},
        )

        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == 'https://discord.com/api/webhooks/test'
        assert 'embeds' in call_args[1]['json']

    def test_telegram_missing_config(self):
        """Test Telegram fails without config"""
        config = NotificationConfig(
            telegram_enabled=True,
            telegram_bot_token='',  # Missing
            telegram_chat_id='',
        )
        manager = NotificationManager(config)

        result = manager._send_telegram("Test", "Test", "info")
        assert result is False

    def test_discord_missing_config(self):
        """Test Discord fails without webhook"""
        config = NotificationConfig(
            discord_enabled=True,
            discord_webhook_url='',
        )
        manager = NotificationManager(config)

        result = manager._send_discord("Test", "Test", "info", None)
        assert result is False

    def test_sound_alert_critical(self):
        """Test sound plays for critical alerts"""
        config = NotificationConfig(sound_enabled=True)
        manager = NotificationManager(config)

        # This just tests the method doesn't crash
        # Actual sound playback is OS-dependent
        result = manager._play_sound('critical')
        # Result depends on platform, just verify it doesn't raise
        assert result in (True, False)

    @patch('polyterm.core.notifications.requests.post')
    def test_send_all_channels(self, mock_post):
        """Test sending to all enabled channels"""
        mock_post.return_value = MagicMock(status_code=200)

        config = NotificationConfig(
            telegram_enabled=True,
            telegram_bot_token='token',
            telegram_chat_id='123',
            discord_enabled=True,
            discord_webhook_url='https://discord/webhook',
            system_enabled=False,  # Skip system notification in test
            sound_enabled=False,   # Skip sound in test
        )
        manager = NotificationManager(config)

        results = manager.send(
            title="Test Alert",
            message="Something happened",
            level="warning",
            data={'market': 'test'},
        )

        assert 'telegram' in results
        assert 'discord' in results


class TestAlertNotifier:
    """Test AlertNotifier class"""

    def test_notifier_initialization(self):
        """Test notifier initialization"""
        config = NotificationConfig()
        manager = NotificationManager(config)
        notifier = AlertNotifier(manager)

        assert notifier.manager == manager

    @patch.object(NotificationManager, 'send')
    def test_notifier_callback(self, mock_send):
        """Test notifier as callback"""
        mock_send.return_value = {'telegram': True}

        config = NotificationConfig()
        manager = NotificationManager(config)
        notifier = AlertNotifier(manager)

        # Create mock alert
        class MockAlert:
            title = "Test Alert"
            message = "Test message"
            level = MagicMock(value='warning')
            data = {'test': 'data'}

        alert = MockAlert()
        notifier(alert)

        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args[1]['title'] == "Test Alert"
        assert call_args[1]['message'] == "Test message"

    @pytest.mark.asyncio
    @patch.object(NotificationManager, 'send')
    async def test_whale_alert(self, mock_send):
        """Test whale trade alert"""
        mock_send.return_value = {'discord': True}

        config = NotificationConfig()
        manager = NotificationManager(config)
        notifier = AlertNotifier(manager)

        class MockTrade:
            notional = 50000
            side = "BUY"
            wallet_address = "0x1234567890"
            market_id = "test_market"

        class MockWallet:
            total_volume = 200000

        await notifier.send_whale_alert(MockTrade(), MockWallet())

        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert "Whale" in call_args[1]['title']
        assert call_args[1]['level'] == 'critical'  # $50k is critical

    @pytest.mark.asyncio
    @patch.object(NotificationManager, 'send')
    async def test_arbitrage_alert(self, mock_send):
        """Test arbitrage opportunity alert"""
        mock_send.return_value = {'discord': True}

        config = NotificationConfig()
        manager = NotificationManager(config)
        notifier = AlertNotifier(manager)

        await notifier.send_arbitrage_alert(
            market1="Market A",
            market2="Market B",
            spread=0.035,
            profit=1.50,
        )

        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert "Arbitrage" in call_args[1]['title']
        assert "3.5%" in call_args[1]['message'] or "spread" in call_args[1]['message'].lower()
