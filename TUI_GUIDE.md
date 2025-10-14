# PolyTerm TUI Guide 🎨

Complete guide to using PolyTerm's Terminal User Interface.

## Table of Contents

- [Getting Started](#getting-started)
- [Main Menu](#main-menu)
- [Features](#features)
  - [Monitor Markets](#1-monitor-markets-)
  - [Whale Activity](#2-whale-activity-)
  - [Watch Market](#3-watch-market-)
  - [Market Analytics](#4-market-analytics-)
  - [Portfolio](#5-portfolio-)
  - [Export Data](#6-export-data-)
  - [Settings](#7-settings-)
  - [Help](#help-)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Tips & Tricks](#tips--tricks)

## Getting Started

Launch the TUI with:

```bash
polyterm
```

You'll see the PolyTerm ASCII logo and main menu:

```
   ██████╗  ██████╗ ██╗  ██╗   ██╗████████╗███████╗██████╗ ███╗   ███╗
   ██╔══██╗██╔═══██╗██║  ╚██╗ ██╔╝╚══██╔══╝██╔════╝██╔══██╗████╗ ████║
   ██████╔╝██║   ██║██║   ╚████╔╝    ██║   █████╗  ██████╔╝██╔████╔██║
   ██╔═══╝ ██║   ██║██║    ╚██╔╝     ██║   ██╔══╝  ██╔══██╗██║╚██╔╝██║
   ██║     ╚██████╔╝███████╗██║      ██║   ███████╗██║  ██║██║ ╚═╝ ██║
   ╚═╝      ╚═════╝ ╚══════╝╚═╝      ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝

         Terminal-Based Monitoring for PolyMarket
                   Track. Analyze. Profit.


Main Menu
PolyTerm v0.1.5
```

## Main Menu

The main menu offers 7 features plus help and quit options:

```
   1 📊 Monitor Markets - Real-time market tracking
   2 🐋 Whale Activity - High-volume markets       
   3 👁  Watch Market - Track specific market       
   4 📈 Market Analytics - Trends and predictions  
   5 💼 Portfolio - View your positions            
   6 📤 Export Data - Export to JSON/CSV           
   7 ⚙️  Settings - Configuration                   
                                                   
   h ❓ Help - View documentation                  
   q 🚪 Quit - Exit PolyTerm                       
```

### Navigation

- **Select by number**: Press `1` through `7`
- **Use shortcuts**: Press letter keys (see [Keyboard Shortcuts](#keyboard-shortcuts))
- **Get help**: Press `h` or `?`
- **Quit**: Press `q`

### Version Display & Updates

PolyTerm automatically displays the current version and checks for updates:

**Current Version Display:**
```
Main Menu
PolyTerm v0.1.5
```

**Update Available:**
```
Main Menu
PolyTerm v0.1.5 🔄 Update Available: v0.1.6
```

**Updating via TUI:**
1. Go to Settings (option 7)
2. Select "🔄 Update PolyTerm" (option 6)
3. Follow the prompts to update

## Features

### 1. Monitor Markets 📊

**Real-time market tracking with live probability updates.**

When you select this option, you'll be prompted:

```
How many markets to display? [default: 10] 
Category filter (or press Enter for all): politics/crypto/sports
Refresh rate in seconds? [default: 2]
Active markets only? [Y/n]
```

**What it does:**
- Displays a live-updating table of markets
- Shows probability, 24hr volume, and data age
- Color-coded changes (green=up, red=down)
- Press `Ctrl+C` to stop monitoring

**Example output:**
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Market                                  ┃ Probability ┃ 24h Volume   ┃ Data Age ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ What price will Ethereum hit in 2025?  │      58.2% │   $203,519   │    45d   │
│ What price will Bitcoin hit in 2025?   │      42.1% │   $122,038   │    45d   │
└─────────────────────────────────────────┴────────────┴──────────────┴──────────┘
```

### 2. Whale Activity 🐋

**Track high-volume markets (proxy for whale activity).**

Prompts:
```
Minimum 24hr volume? [default: $10,000] $
Lookback period in hours? [default: 24]
Maximum results to show? [default: 20]
```

**What it does:**
- Identifies markets with significant 24hr trading volume
- Shows top markets by volume (proxy for whale activity)
- Displays market details and volume metrics

**Note:** Individual trade data is not available from current PolyMarket APIs. This feature identifies high-volume markets as a proxy.

### 3. Watch Market 👁

**Track a specific market with alerts.**

Prompts:
```
Search for market (or enter Market ID):
Enter Market ID:
Alert on probability change > [default: 5%]
Check interval in seconds? [default: 10]
```

**What it does:**
- Monitors a single market continuously
- Alerts when probability changes exceed threshold
- Shows real-time updates
- Press `Ctrl+C` to stop

**Finding Market IDs:**
- Use Monitor Markets to see IDs
- Check PolyMarket website URL
- Market IDs are long hexadecimal strings

### 4. Market Analytics 📈

**Advanced market analysis and insights.**

Submenu:
```
1. 📈 Trending Markets - Most active markets
2. 🔗 Market Correlations - Related markets
3. 🔮 Price Predictions - Trend analysis
4. 📊 Volume Analysis - Volume patterns
```

**Currently Available:**
- ✅ Trending Markets (option 1)

**Coming Soon:**
- 🔄 Market Correlations
- 🔄 Price Predictions  
- 🔄 Volume Analysis

### 5. Portfolio 💼

**View your positions and P&L.**

Prompts:
```
Wallet address (or press Enter for config):
```

**What it does:**
- Shows your market positions
- Displays P&L and performance
- Uses wallet from config if none provided

**Note:** Portfolio tracking is limited by PolyMarket API changes. The Subgraph API has been removed.

### 6. Export Data 📤

**Export market data to JSON or CSV.**

Prompts:
```
Market ID or search term:
Format? [json/csv] [default: json]
Output file: [default: export.json]
```

**What it does:**
- Exports market data to file
- Supports JSON and CSV formats
- Shows success/error message
- Creates file in current directory

**Example:**
```bash
Market ID: abc123...
Format: json
Output file: my_markets.json

✓ Successfully exported to my_markets.json
```

### 7. Settings ⚙️

**View and configure PolyTerm settings.**

Current configuration display:
```
┏━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Setting               ┃ Value                             ┃
┡━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Config File           │ ~/.polyterm/config.toml           │
│ Probability Threshold │ 15%                                │
│ Volume Threshold      │ 50.0%                              │
│ Check Interval        │ 60s                                │
│ Refresh Rate          │ 2s                                 │
│ Max Markets           │ 20                                │
└───────────────────────┴───────────────────────────────────┘
```

Options:
```
1. Edit Alert Settings
2. Edit API Settings
3. Edit Display Settings
4. View Config File
5. Reset to Defaults
6. 🔄 Update PolyTerm
```

**Note:** Config editing UI coming soon. For now, manually edit `~/.polyterm/config.toml`

### Help ❓

**Documentation and quick reference.**

Shows:
- Keyboard shortcuts
- Feature descriptions
- CLI command examples
- API status
- Resource links

## Keyboard Shortcuts

### Main Menu Shortcuts

| Key(s) | Action |
|--------|--------|
| `1` | Monitor Markets |
| `2` | Whale Activity |
| `3` | Watch Market |
| `4` | Market Analytics |
| `5` | Portfolio |
| `6` | Export Data |
| `7` | Settings |
| `h`, `?` | Help |
| `q` | Quit |

### Alternative Shortcuts

| Key | Same as | Feature |
|-----|---------|---------|
| `m` | `1` | Monitor |
| `w` | `2` | Whales |
| `a` | `4` | Analytics |
| `p` | `5` | Portfolio |
| `e` | `6` | Export |
| `s` | `7` | Settings |

### Global Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+C` | Stop current operation |
| `Enter` | Return to main menu |
| `q` | Quit from most screens |

## Tips & Tricks

### Quick Access

For fastest access, use alternative shortcuts:
- `m` for Monitor
- `w` for Whales
- Press `Enter` to quickly return to menu

### Power User Mode

If you prefer command-line:
```bash
# Direct commands still work
polyterm monitor --limit 20
polyterm whales --hours 24
polyterm watch <market-id>

# Bypass TUI completely
polyterm monitor  # Skip menu, go straight to monitoring
```

### Market Discovery

Best workflow for finding interesting markets:

1. Start with **Monitor** (`1`) to see top markets
2. Find market ID of interest
3. Use **Watch** (`3`) to track that specific market
4. Set up alerts with custom thresholds

### Exporting Data

Quick export workflow:

1. Use **Monitor** to see markets
2. Copy market IDs you're interested in
3. Go to **Export** (`6`)
4. Export to JSON for analysis
5. Process with Python/Excel/etc.

### Configuration

Edit `~/.polyterm/config.toml` for persistent settings:

```toml
[alerts]
probability_threshold = 10.0
check_interval = 60

[display]
refresh_rate = 2
max_markets = 20

[data_validation]
min_volume_threshold = 1000.0
```

Then restart PolyTerm to apply changes.

### Troubleshooting

**TUI not launching?**
```bash
# Check installation
pip show polyterm

# Try reinstalling
pip install -e .
```

**Screen issues?**
```bash
# Clear terminal first
clear
polyterm
```

**Want to go back to CLI only?**
```bash
# Just add any command
polyterm monitor  # Skips TUI
polyterm whales   # Skips TUI
```

### Advanced Usage

**Combining TUI with CLI:**

```bash
# Launch TUI
polyterm

# In another terminal, run CLI commands
polyterm monitor --limit 5 --once

# Export from CLI while TUI is running
polyterm export --market <id> --format json
```

**Scripting with TUI:**

The TUI can be scripted (though CLI is better for this):

```bash
# Not recommended, but possible
echo "1" | polyterm  # Will enter monitor screen
```

Better approach - use CLI commands in scripts:
```bash
#!/bin/bash
# monitor_script.sh
polyterm monitor --limit 10 --refresh 5 --once
```

## Getting Help

- Press `h` in the TUI for quick help
- See [README.md](README.md) for full documentation
- Check [API_SETUP.md](API_SETUP.md) for API details
- Report issues: [GitHub Issues](https://github.com/NYTEMODEONLY/polyterm/issues)

---

**Enjoy using PolyTerm! 🎨📊**

*Your terminal window to prediction markets*

