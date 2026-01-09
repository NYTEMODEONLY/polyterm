# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PolyTerm is a terminal-based monitoring tool for PolyMarket prediction markets. It provides both a CLI and an interactive TUI (Terminal User Interface) for tracking markets, whale activity, and trading opportunities.

## Common Commands

### Development Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Running Tests
```bash
# Full test suite
pytest

# Run specific test file
pytest tests/test_cli/test_cli.py -v

# Run specific test
pytest tests/test_cli/test_cli.py::TestCLI::test_cli_version -v

# Live data integration tests
pytest tests/test_live_data/ -v

# TUI tests only
pytest tests/test_tui/ -v
```

### Running the Application
```bash
# Launch TUI (default)
polyterm

# CLI commands
polyterm monitor --limit 20
polyterm whales --hours 24
polyterm live-monitor --interactive
polyterm update
```

### Building & Publishing
```bash
python -m build
python -m twine upload dist/*
```

## Architecture

### Entry Points
- **CLI**: `polyterm/cli/main.py` - Click-based CLI, launches TUI if no subcommand
- **TUI**: `polyterm/tui/controller.py` - Main TUI loop with `TUIController` class

### Layer Structure

```
polyterm/
├── api/           # Data layer - API clients
│   ├── gamma.py       # Primary: Gamma REST API (/events endpoint)
│   ├── clob.py        # CLOB REST + WebSocket (wss://ws-live-data.polymarket.com)
│   ├── subgraph.py    # GraphQL (deprecated by The Graph)
│   └── aggregator.py  # Multi-source aggregator with fallback
├── core/          # Business logic
│   ├── scanner.py     # Market monitoring & shift detection
│   ├── analytics.py   # Whale tracking (volume-based)
│   └── alerts.py      # Alert system
├── cli/           # CLI interface
│   ├── main.py        # Entry point & command registration
│   └── commands/      # Individual CLI commands
├── tui/           # Terminal UI
│   ├── controller.py  # Main loop, routes choices to screens
│   ├── menu.py        # Main menu with update checking
│   ├── logo.py        # ASCII logo (responsive to terminal width)
│   └── screens/       # Individual TUI screens
└── utils/         # Utilities
    ├── config.py      # Config management (~/.polyterm/config.toml)
    └── formatting.py  # Rich text formatting
```

### Key Patterns

**API Fallback**: `APIAggregator` tries Gamma API first, falls back to CLOB if needed.

**TUI Flow**: User selection → `TUIController` routes to screen → Screen gathers input → Launches CLI command via subprocess.

**Config**: TOML-based at `~/.polyterm/config.toml`, `Config` class uses dot notation (e.g., `config.get("alerts.probability_threshold")`).

**WebSocket**: Live monitor uses RTDS WebSocket at `wss://ws-live-data.polymarket.com` with polling fallback.

### Menu Options Mapping
```
1/m = monitor       5/a = analytics
2/l = live monitor  6/p = portfolio
3/w = whales        7/e = export
4   = watch         8/s = settings
u   = quick update  h/? = help
q   = quit
```

## Testing Notes

- Tests use `responses` library for HTTP mocking
- Live data tests (`tests/test_live_data/`) hit real APIs - may fail due to data changes
- Config tests should use `tmp_path` fixture to avoid polluting user config
- When mocking `Console`, also mock `console.size.width` for responsive menu tests
