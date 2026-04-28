"""Inventory tests for TUI screen routing."""

from polyterm.tui.controller import SCREEN_ROUTES


def test_all_tui_routes_target_callable_screens():
    """Every registered TUI route should point at an importable screen callable."""
    assert SCREEN_ROUTES

    for route, screen in SCREEN_ROUTES.items():
        assert callable(screen), f"{route} does not map to a callable screen"


def test_tui_route_inventory_has_no_missing_screen_names():
    """Unique screen functions should expose stable names for diagnostics."""
    unique_screens = set(SCREEN_ROUTES.values())

    assert len(unique_screens) >= 70
    for screen in unique_screens:
        assert getattr(screen, "__name__", ""), f"{screen!r} has no function name"
