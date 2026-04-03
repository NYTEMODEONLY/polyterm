# Alerts

> Market shift alert system with multi-channel notification dispatch.

## Overview

The alerts module provides a rule-based alert engine that monitors market shifts and dispatches notifications through multiple channels (terminal, system notifications, callbacks). It supports three built-in alert types -- probability shifts, volume spikes, and liquidity changes -- plus custom user-defined rules. Alerts are stored in an in-memory history (capped at 1000 entries) for later retrieval.

## Key Classes and Functions

### `AlertLevel`

Enum defining alert severity levels.

| Value | String | Description |
|-------|--------|-------------|
| `INFO` | `"info"` | Informational alert |
| `WARNING` | `"warning"` | Warning-level alert |
| `CRITICAL` | `"critical"` | Critical alert (triggers terminal bell) |

### `Alert`

Data structure representing a single alert instance.

#### Constructor

```python
Alert(
    market_id: str,
    title: str,
    message: str,
    level: AlertLevel = AlertLevel.INFO,
    data: Optional[Dict[str, Any]] = None,
)
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `market_id` | `str` | Associated market identifier |
| `title` | `str` | Alert title |
| `message` | `str` | Human-readable alert message |
| `level` | `AlertLevel` | Severity level |
| `data` | `Dict[str, Any]` | Original shift data payload |
| `timestamp` | `datetime` | Time the alert was created |

### `AlertManager`

Central alert engine that processes market shifts, evaluates rules, and dispatches notifications.

#### Constructor

```python
AlertManager(enable_system_notifications: bool = False)
```

System notifications require the `plyer` package. If `plyer` is not installed, system notifications are silently disabled.

#### Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `add_callback` | `(callback: Callable[[Alert], None]) -> None` | Register a callback invoked on every dispatched alert |
| `add_rule` | `(name: str, condition: Callable[[Dict], bool], create_alert: Callable[[Dict], Alert]) -> None` | Add a custom alert rule with condition and alert factory |
| `create_probability_shift_alert` | `(shift_data: Dict, threshold: float = 10.0) -> Optional[Alert]` | Create alert for probability change exceeding threshold |
| `create_volume_spike_alert` | `(shift_data: Dict, threshold: float = 50.0) -> Optional[Alert]` | Create alert for volume change exceeding threshold |
| `create_liquidity_alert` | `(shift_data: Dict, threshold: float = 30.0) -> Optional[Alert]` | Create alert for liquidity change exceeding threshold |
| `process_shift` | `(shift_data: Dict, thresholds: Dict[str, float]) -> None` | Evaluate all built-in and custom rules against shift data |
| `dispatch_alert` | `(alert: Alert) -> None` | Store in history and send to all channels |
| `get_recent_alerts` | `(count: int = 10) -> List[Alert]` | Retrieve most recent alerts from history |
| `get_alerts_for_market` | `(market_id: str) -> List[Alert]` | Get all alerts for a specific market |
| `clear_history` | `() -> None` | Clear the alert history |

## Scoring / Algorithms

### Probability Shift Alerts

- Threshold: configurable, default `10.0`%
- Level `CRITICAL` when absolute change >= 20%
- Level `WARNING` when absolute change >= threshold but < 20%

### Volume Spike Alerts

- Threshold: configurable, default `50.0`%
- Level `WARNING` when absolute change >= 100%
- Level `INFO` when absolute change >= threshold but < 100%

### Liquidity Alerts

- Threshold: configurable, default `30.0`%
- Level `WARNING` when liquidity decreases by more than 30%
- Level `INFO` otherwise

### Custom Rules

Custom rules are evaluated via a `condition` callable that receives the raw `shift_data` dict. If the condition returns `True`, the corresponding `create_alert` callable generates the `Alert` object.

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `enable_system_notifications` | `False` | Enable OS-level desktop notifications |
| `max_history` | `1000` | Maximum alerts retained in memory |
| Default probability threshold | `10.0` | Minimum probability change (%) |
| Default volume threshold | `50.0` | Minimum volume change (%) |
| Default liquidity threshold | `30.0` | Minimum liquidity change (%) |

## Data Sources

- Shift data dictionaries passed in from `core/scanner.py` (market monitoring)
- Expected shift_data keys: `market_id`, `title`, `changes.probability_change`, `changes.volume_change`, `changes.liquidity_change`

## Output Format

Alerts are dispatched through three channels:

1. **Terminal**: ANSI-colored output with timestamp, e.g., `[14:30:05] [WARNING] Market Title: Probability increased by 15.2%`
2. **System notification**: Desktop notification via `plyer` (title truncated to 50 chars, 10-second timeout)
3. **Callbacks**: Registered callables receive the full `Alert` object

## External Dependencies

- `plyer` (optional) -- OS-level desktop notifications

## Related

- CLI commands: `polyterm pricealert` (price-based alerts use `db/database.py`; this module handles real-time shift alerts)
- TUI screens: `12/alert` shortcut
- Other modules: `core/scanner.py` (produces shift data), `core/notifications.py` (additional notification channels)
