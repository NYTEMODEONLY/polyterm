"""
Notification system for alerts via multiple channels.

Supports:
- Telegram bot
- Discord webhooks
- System notifications (via plyer)
- Sound alerts
- Email (SMTP)
"""

import os
import subprocess
import sys
import json
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass
import threading

import requests

try:
    from plyer import notification as system_notification
    HAS_PLYER = True
except ImportError:
    HAS_PLYER = False


@dataclass
class NotificationConfig:
    """Configuration for notification channels"""
    # Telegram
    telegram_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Discord
    discord_enabled: bool = False
    discord_webhook_url: str = ""

    # System notifications
    system_enabled: bool = True

    # Sound alerts
    sound_enabled: bool = True
    sound_file: str = ""  # Custom sound file path

    # Email
    email_enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_to: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'telegram': {
                'enabled': self.telegram_enabled,
                'bot_token': self.telegram_bot_token,
                'chat_id': self.telegram_chat_id,
            },
            'discord': {
                'enabled': self.discord_enabled,
                'webhook_url': self.discord_webhook_url,
            },
            'system': {
                'enabled': self.system_enabled,
            },
            'sound': {
                'enabled': self.sound_enabled,
                'file': self.sound_file,
            },
            'email': {
                'enabled': self.email_enabled,
                'smtp_host': self.smtp_host,
                'smtp_port': self.smtp_port,
                'smtp_user': self.smtp_user,
                'email_to': self.email_to,
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NotificationConfig':
        telegram = data.get('telegram', {})
        discord = data.get('discord', {})
        system = data.get('system', {})
        sound = data.get('sound', {})
        email = data.get('email', {})

        return cls(
            telegram_enabled=telegram.get('enabled', False),
            telegram_bot_token=telegram.get('bot_token', ''),
            telegram_chat_id=telegram.get('chat_id', ''),
            discord_enabled=discord.get('enabled', False),
            discord_webhook_url=discord.get('webhook_url', ''),
            system_enabled=system.get('enabled', True),
            sound_enabled=sound.get('enabled', True),
            sound_file=sound.get('file', ''),
            email_enabled=email.get('enabled', False),
            smtp_host=email.get('smtp_host', ''),
            smtp_port=email.get('smtp_port', 587),
            smtp_user=email.get('smtp_user', ''),
            smtp_password=email.get('smtp_password', ''),
            email_to=email.get('email_to', ''),
        )


class NotificationManager:
    """Manages multi-channel notifications"""

    def __init__(self, config: NotificationConfig):
        self.config = config
        self._lock = threading.Lock()

    def send(
        self,
        title: str,
        message: str,
        level: str = 'info',
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, bool]:
        """
        Send notification to all enabled channels.

        Args:
            title: Notification title
            message: Notification message
            level: Severity level (info, warning, critical)
            data: Additional data

        Returns:
            Dict of channel -> success status
        """
        results = {}

        # Telegram
        if self.config.telegram_enabled:
            results['telegram'] = self._send_telegram(title, message, level)

        # Discord
        if self.config.discord_enabled:
            results['discord'] = self._send_discord(title, message, level, data)

        # System notification
        if self.config.system_enabled:
            results['system'] = self._send_system(title, message)

        # Sound alert
        if self.config.sound_enabled:
            results['sound'] = self._play_sound(level)

        # Email (only for critical)
        if self.config.email_enabled and level == 'critical':
            results['email'] = self._send_email(title, message)

        return results

    def _send_telegram(self, title: str, message: str, level: str) -> bool:
        """Send notification via Telegram bot"""
        if not self.config.telegram_bot_token or not self.config.telegram_chat_id:
            return False

        try:
            # Format message with level indicator
            level_emoji = {
                'info': 'ℹ️',
                'warning': '⚠️',
                'critical': '🚨',
            }.get(level, 'ℹ️')

            text = f"{level_emoji} *{title}*\n\n{message}"

            url = f"https://api.telegram.org/bot{self.config.telegram_bot_token}/sendMessage"
            payload = {
                'chat_id': self.config.telegram_chat_id,
                'text': text,
                'parse_mode': 'Markdown',
            }

            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200

        except Exception as e:
            print(f"Telegram notification failed: {e}")
            return False

    def _send_discord(
        self,
        title: str,
        message: str,
        level: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send notification via Discord webhook"""
        if not self.config.discord_webhook_url:
            return False

        try:
            # Color based on level
            colors = {
                'info': 0x3498db,      # Blue
                'warning': 0xf39c12,   # Orange
                'critical': 0xe74c3c,  # Red
            }

            embed = {
                'title': title,
                'description': message,
                'color': colors.get(level, 0x3498db),
                'timestamp': datetime.utcnow().isoformat(),
                'footer': {'text': 'PolyTerm Alert'},
            }

            # Add fields from data
            if data:
                fields = []
                for key, value in data.items():
                    if isinstance(value, (str, int, float)):
                        fields.append({
                            'name': key.replace('_', ' ').title(),
                            'value': str(value),
                            'inline': True,
                        })
                if fields:
                    embed['fields'] = fields[:25]  # Discord limit

            payload = {'embeds': [embed]}

            response = requests.post(
                self.config.discord_webhook_url,
                json=payload,
                timeout=10,
            )
            return response.status_code in (200, 204)

        except Exception as e:
            print(f"Discord notification failed: {e}")
            return False

    def _send_system(self, title: str, message: str) -> bool:
        """Send system notification"""
        if not HAS_PLYER:
            return False

        try:
            system_notification.notify(
                title=f"PolyTerm: {title[:50]}",
                message=message[:200],
                app_name="PolyTerm",
                timeout=10,
            )
            return True
        except Exception as e:
            print(f"System notification failed: {e}")
            return False

    def _play_sound(self, level: str) -> bool:
        """Play sound alert"""
        try:
            # Try custom sound file first
            if self.config.sound_file and os.path.exists(self.config.sound_file):
                return self._play_file(self.config.sound_file)

            # Fall back to terminal bell for critical alerts
            if level == 'critical':
                sys.stdout.write('\a')
                sys.stdout.flush()
                return True

            # Try system sounds
            if sys.platform == 'darwin':
                # macOS system sounds
                sounds = {
                    'info': 'Pop',
                    'warning': 'Ping',
                    'critical': 'Basso',
                }
                sound_name = sounds.get(level, 'Pop')
                subprocess.Popen(['afplay', f'/System/Library/Sounds/{sound_name}.aiff'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True

            elif sys.platform.startswith('linux'):
                # Try paplay (PulseAudio)
                subprocess.Popen(['paplay', '/usr/share/sounds/freedesktop/stereo/message.oga'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True

            return False

        except Exception as e:
            print(f"Sound alert failed: {e}")
            return False

    def _play_file(self, filepath: str) -> bool:
        """Play a custom sound file"""
        try:
            if sys.platform == 'darwin':
                subprocess.Popen(['afplay', filepath], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif sys.platform.startswith('linux'):
                subprocess.Popen(['aplay', filepath], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif sys.platform == 'win32':
                import winsound
                winsound.PlaySound(filepath, winsound.SND_FILENAME | winsound.SND_ASYNC)
            return True
        except Exception:
            return False

    def _send_email(self, title: str, message: str) -> bool:
        """Send email notification"""
        if not all([
            self.config.smtp_host,
            self.config.smtp_user,
            self.config.smtp_password,
            self.config.email_to,
        ]):
            return False

        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart()
            msg['From'] = self.config.smtp_user
            msg['To'] = self.config.email_to
            msg['Subject'] = f"PolyTerm Alert: {title}"

            body = f"""
PolyTerm Alert

{title}

{message}

---
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.smtp_user, self.config.smtp_password)
                server.send_message(msg)

            return True

        except Exception as e:
            print(f"Email notification failed: {e}")
            return False

    def test_telegram(self) -> bool:
        """Test Telegram connection"""
        return self._send_telegram(
            "Test Alert",
            "This is a test notification from PolyTerm.",
            "info",
        )

    def test_discord(self) -> bool:
        """Test Discord connection"""
        return self._send_discord(
            "Test Alert",
            "This is a test notification from PolyTerm.",
            "info",
            {'test': True},
        )


class AlertNotifier:
    """
    Integrates with the alert system to send notifications.

    Can be used as a callback for AlertManager.
    """

    def __init__(self, notification_manager: NotificationManager):
        self.manager = notification_manager

    def __call__(self, alert) -> None:
        """Callback for AlertManager"""
        # Map AlertLevel to notification level
        level_map = {
            'info': 'info',
            'warning': 'warning',
            'critical': 'critical',
        }
        level = level_map.get(alert.level.value if hasattr(alert.level, 'value') else alert.level, 'info')

        self.manager.send(
            title=alert.title,
            message=alert.message,
            level=level,
            data=alert.data,
        )

    async def send_whale_alert(self, trade, wallet) -> None:
        """Send whale trade notification"""
        self.manager.send(
            title="Whale Trade Detected",
            message=f"${trade.notional:,.0f} {trade.side} by {trade.wallet_address[:10]}...",
            level='warning' if trade.notional < 50000 else 'critical',
            data={
                'market': trade.market_id,
                'notional': f"${trade.notional:,.0f}",
                'wallet_volume': f"${wallet.total_volume:,.0f}",
            },
        )

    async def send_smart_money_alert(self, trade, wallet) -> None:
        """Send smart money notification"""
        self.manager.send(
            title="Smart Money Trade",
            message=f"Wallet with {wallet.win_rate:.0%} win rate traded ${trade.notional:,.0f}",
            level='info',
            data={
                'market': trade.market_id,
                'win_rate': f"{wallet.win_rate:.0%}",
                'total_trades': wallet.total_trades,
            },
        )

    async def send_insider_alert(self, alert_data: Dict[str, Any]) -> None:
        """Send insider suspect notification"""
        self.manager.send(
            title="Potential Insider Activity",
            message=alert_data.get('message', 'Suspicious trading pattern detected'),
            level='critical',
            data=alert_data.get('data', {}),
        )

    async def send_arbitrage_alert(
        self,
        market1: str,
        market2: str,
        spread: float,
        profit: float,
    ) -> None:
        """Send arbitrage opportunity notification"""
        self.manager.send(
            title="Arbitrage Opportunity",
            message=f"Spread: {spread:.1%}, Expected profit: ${profit:.2f}",
            level='warning',
            data={
                'market1': market1,
                'market2': market2,
                'spread': f"{spread:.2%}",
                'profit': f"${profit:.2f}",
            },
        )
