# Help & Documentation

> In-app reference for all features, shortcuts, and CLI commands.

## Overview

The Help screen is a comprehensive reference displayed directly in the TUI (no subprocess). It lists all keyboard shortcuts, describes every feature, shows equivalent CLI commands for power users, and provides API status and external resource links. This is the go-to screen when you need to find a shortcut or understand what a feature does.

## Access

- **Menu shortcut**: `h` or `?`
- **Menu path**: Available from any menu prompt

## What It Shows

Four sections displayed inline:

1. **Keyboard Shortcuts** -- complete table of all TUI shortcuts (1-17 for menu items, plus two-letter shortcuts for every feature)
2. **Features** -- description of every feature with a brief explanation of what it does
3. **CLI Commands** -- equivalent `polyterm` commands for all features, useful for scripting and power users
4. **API Status** -- current status of Gamma API, CLOB API, and Subgraph API
5. **Resources** -- links to GitHub repository, Polymarket docs, and issue tracker

## Navigation / Keyboard Shortcuts

This screen is read-only. Scroll through the output and press Enter when done.

## CLI Command

This screen does not invoke a CLI command. All content is rendered directly using Rich tables and formatted output.

## Data Sources

- No external data sources. All content is hardcoded in the help screen.

## Related Screens

- [Glossary](../screens/glossary.md) -- prediction market terminology
