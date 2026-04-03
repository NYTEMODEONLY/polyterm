# Settings Screen

> View and manage PolyTerm configuration, and update the application.

## Overview

The Settings screen displays the current configuration values and provides a menu for editing alert, API, and display settings. It also includes a self-update feature that checks PyPI for new versions and upgrades via pipx or pip. Config editing currently directs users to manually edit `~/.polyterm/config.toml`.

## Access

- **Menu shortcut**: `8`, `s`
- **Menu path**: Page 1 item 8 (Settings)

## What It Shows

A table of current configuration values:

- **Config File** -- path to the TOML config file
- **Probability Threshold** -- alert trigger threshold (%)
- **Volume Threshold** -- volume change threshold (%)
- **Check Interval** -- monitoring interval (seconds)
- **Refresh Rate** -- display refresh rate (seconds)
- **Max Markets** -- maximum markets to display

Then a submenu of six operations.

## Navigation / Keyboard Shortcuts

- `1` -- Edit Alert Settings (probability threshold)
- `2` -- Edit API Settings (Gamma API key)
- `3` -- Edit Display Settings (refresh rate)
- `4` -- View Config File location
- `5` -- Reset to Defaults
- `6` -- Update PolyTerm (checks PyPI, upgrades via pipx/pip, optional restart)
- `b` -- Back to main menu

## CLI Command

This screen does not invoke a CLI subprocess. It reads configuration directly via the `Config` class and manages updates inline.

## Data Sources

- Local config file (`~/.polyterm/config.toml`)
- PyPI API (`https://pypi.org/pypi/polyterm/json`) for version checking

## Related Screens

- [export](../screens/export.md) -- export data settings
