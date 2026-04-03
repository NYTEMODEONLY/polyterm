# Price Alert Screen

> Set alerts to notify you when markets hit target prices.

## Overview

The Price Alert screen launches the interactive price alert manager. You can create alerts for specific price targets, list existing alerts, check which alerts have triggered, and remove alerts you no longer need. Alerts are direction-aware (above or below target).

## Access

- **Menu shortcut**: `pa` or `pricealert`
- **Menu path**: Not on paginated menu (shortcut-only access)

## What It Shows

Launches directly into the `pricealert` CLI command in interactive mode, which provides options to add, list, check, and remove price alerts.

## Navigation / Keyboard Shortcuts

No screen-level shortcuts. Navigation is handled by the interactive CLI prompts.

## CLI Command

```bash
polyterm pricealert -i
```

## Data Sources

- Local SQLite database (`~/.polyterm/data.db`) -- `price_alerts` table
- Gamma API for current market prices when checking alerts

## Related Screens

- [Alerts Screen](../screens/alerts_screen.md)
- [Alert Center Screen](../screens/alertcenter_screen.md)
