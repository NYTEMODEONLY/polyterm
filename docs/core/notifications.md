# Multi-Channel Notifications

> Sends alerts via Telegram, Discord, system notifications, sound, and email with severity-based routing.

## Overview

The notifications module provides a unified interface for dispatching alerts across five channels: Telegram bot messages, Discord webhook embeds, desktop system notifications (via plyer), audible sound alerts, and email (SMTP). Channels are independently configurable and severity levels control routing -- for example, email is only sent for `critical` alerts. The `AlertNotifier` class bridges this system with PolyTerm's alert and whale tracking infrastructure.

## Key Classes and Functions

### `NotificationConfig`

Dataclass holding configuration for all notification channels.

**Constructor**: `__init__(self, telegram_enabled=False, telegram_bot_token="", telegram_chat_id="", discord_enabled=False, discord_webhook_url="", system_enabled=True, sound_enabled=True, sound_file="", email_enabled=False, smtp_host="", smtp_port=587, smtp_user="", smtp_password="", email_to="")`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `telegram_enabled` | `bool` | `False` | Enable Telegram notifications |
| `telegram_bot_token` | `str` | `""` | Telegram Bot API token |
| `telegram_chat_id` | `str` | `""` | Telegram chat/channel ID |
| `discord_enabled` | `bool` | `False` | Enable Discord notifications |
| `discord_webhook_url` | `str` | `""` | Discord webhook URL |
| `system_enabled` | `bool` | `True` | Enable desktop notifications |
| `sound_enabled` | `bool` | `True` | Enable sound alerts |
| `sound_file` | `str` | `""` | Path to custom sound file |
| `email_enabled` | `bool` | `False` | Enable email (critical only) |
| `smtp_host` | `str` | `""` | SMTP server hostname |
| `smtp_port` | `int` | `587` | SMTP server port |
| `smtp_user` | `str` | `""` | SMTP username |
| `smtp_password` | `str` | `""` | SMTP password |
| `email_to` | `str` | `""` | Recipient email address |

#### Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `to_dict` | `() -> Dict[str, Any]` | Serializes config to a nested dict grouped by channel |
| `from_dict` | `(data: Dict[str, Any]) -> NotificationConfig` | Class method to deserialize from a nested dict |

### `NotificationManager`

Manages dispatching notifications to all enabled channels. Thread-safe via internal lock.

**Constructor**: `__init__(self, config: NotificationConfig)`

#### Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `send` | `(title: str, message: str, level: str = 'info', data: Optional[Dict] = None) -> Dict[str, bool]` | Sends to all enabled channels. Returns dict of channel name to success boolean. Email only fires for `critical` level. |
| `test_telegram` | `() -> bool` | Sends a test message via Telegram |
| `test_discord` | `() -> bool` | Sends a test embed via Discord |

#### Internal Channel Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `_send_telegram` | `(title: str, message: str, level: str) -> bool` | Posts Markdown-formatted message to Telegram Bot API. Escapes special characters. |
| `_send_discord` | `(title: str, message: str, level: str, data: Optional[Dict]) -> bool` | Posts a color-coded embed to Discord webhook. Adds up to 25 inline fields from `data`. |
| `_send_system` | `(title: str, message: str) -> bool` | Sends desktop notification via plyer (title truncated to 50 chars, message to 200 chars, 10s timeout). |
| `_play_sound` | `(level: str) -> bool` | Plays custom sound file, or platform-specific system sounds, or terminal bell for critical. |
| `_play_file` | `(filepath: str) -> bool` | Plays a custom sound file using platform-appropriate tool (`afplay`, `aplay`, `winsound`). |
| `_send_email` | `(title: str, message: str) -> bool` | Sends plaintext email via SMTP with STARTTLS. |

### `AlertNotifier`

Bridges the alert system with `NotificationManager`. Can be used as a callable callback for `AlertManager`.

**Constructor**: `__init__(self, notification_manager: NotificationManager)`

#### Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `__call__` | `(alert) -> None` | Callback for AlertManager. Maps alert level to notification level and sends. |
| `send_whale_alert` | `async (trade, wallet) -> None` | Sends whale trade notification. Level is `warning` for trades < $50k, `critical` for >= $50k. |
| `send_smart_money_alert` | `async (trade, wallet) -> None` | Sends notification for high win-rate wallet trades at `info` level. |
| `send_insider_alert` | `async (alert_data: Dict) -> None` | Sends insider suspect notification at `critical` level. |
| `send_arbitrage_alert` | `async (market1: str, market2: str, spread: float, profit: float) -> None` | Sends arbitrage opportunity notification at `warning` level. |

## Scoring / Algorithms

### Severity Routing

| Level | Telegram | Discord | System | Sound | Email |
|-------|----------|---------|--------|-------|-------|
| `info` | Yes | Yes | Yes | Yes | No |
| `warning` | Yes | Yes | Yes | Yes | No |
| `critical` | Yes | Yes | Yes | Yes | **Yes** |

### Discord Embed Colors

| Level | Color | Hex |
|-------|-------|-----|
| `info` | Blue | `0x3498db` |
| `warning` | Orange | `0xf39c12` |
| `critical` | Red | `0xe74c3c` |

### Sound Fallback Chain

1. Custom sound file (if configured and exists)
2. For `critical`: terminal bell (`\a`)
3. macOS: `afplay` with system sounds (`Pop`, `Ping`, `Basso`)
4. Linux: `paplay` with freedesktop sounds
5. Windows: `winsound` module

### Whale Alert Threshold

- Trade notional < $50,000: `warning` level
- Trade notional >= $50,000: `critical` level

## Configuration

Configuration is stored in `NotificationConfig` and can be serialized to/from dict format for persistence in `~/.polyterm/config.toml`.

| Setting | Default | Description |
|---------|---------|-------------|
| HTTP timeout | `10` seconds | For Telegram and Discord API calls |
| System notification timeout | `10` seconds | Desktop notification display duration |
| SMTP port | `587` | Default SMTP port with STARTTLS |
| Discord field limit | `25` | Maximum embed fields per message |

## Data Sources

- **Telegram Bot API**: `https://api.telegram.org/bot{token}/sendMessage`
- **Discord Webhook API**: User-configured webhook URL
- **plyer**: Cross-platform desktop notification library (optional dependency)
- **System sounds**: Platform-specific audio files

## Output Format

`NotificationManager.send()` returns:

```python
{
    'telegram': bool,  # True if sent successfully
    'discord': bool,
    'system': bool,
    'sound': bool,
    'email': bool,     # Only present for critical-level alerts
}
```

Only channels that are enabled appear in the result dict.

## External Dependencies

- `requests` -- HTTP client for Telegram and Discord APIs
- `plyer` -- Desktop notifications (optional; gracefully degraded if missing)
- `smtplib` -- Email via SMTP (stdlib)
- `winsound` -- Windows sound playback (stdlib, Windows only)

## Related

- TUI screen: shortcut `alert` (alerts management)
- Related modules: `polyterm/core/whale_tracker.py` (whale/insider alerts), `polyterm/core/arbitrage.py` (arb alerts)
- Config: `~/.polyterm/config.toml` (notification settings)
