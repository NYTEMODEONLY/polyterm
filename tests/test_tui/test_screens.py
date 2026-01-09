"""Tests for TUI screens"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from polyterm.tui.screens import (
    monitor_screen,
    whales_screen,
    watch_screen,
    analytics_screen,
    portfolio_screen,
    export_screen,
    settings_screen,
    help_screen,
)


@patch('polyterm.tui.screens.monitor.subprocess.run')
def test_monitor_screen(mock_run):
    """Test monitor screen launches with parameters"""
    mock_console = Mock()
    mock_console.input.side_effect = ["10", "", "2", "y"]
    
    monitor_screen(mock_console)
    
    # Should print panel and prompts
    assert mock_console.print.call_count >= 2
    # Should collect input
    assert mock_console.input.call_count == 4


@patch('polyterm.tui.screens.whales.subprocess.run')
def test_whales_screen(mock_run):
    """Test whales screen launches with parameters"""
    mock_console = Mock()
    mock_console.input.side_effect = ["10000", "24", "20"]
    
    whales_screen(mock_console)
    
    # Should print panel and prompts
    assert mock_console.print.call_count >= 2
    # Should collect input
    assert mock_console.input.call_count == 3


@patch('polyterm.tui.screens.watch.subprocess.run')
def test_watch_screen(mock_run):
    """Test watch screen launches with market ID"""
    mock_console = Mock()
    # Provide all 4 inputs: query (looks like market ID), threshold, refresh
    mock_console.input.side_effect = ["abc123def456789abcdef0123", "5", "10"]
    
    watch_screen(mock_console)
    
    # Should print panel and prompts
    assert mock_console.print.call_count >= 2
    # Should collect input
    assert mock_console.input.call_count >= 3


@patch('polyterm.tui.screens.analytics.APIAggregator')
@patch('polyterm.tui.screens.analytics.SubgraphClient')
@patch('polyterm.tui.screens.analytics.CLOBClient')
@patch('polyterm.tui.screens.analytics.GammaClient')
@patch('polyterm.tui.screens.analytics.Config')
def test_analytics_screen_trending(mock_config, mock_gamma, mock_clob, mock_subgraph, mock_aggregator):
    """Test analytics screen trending markets option"""
    # Setup mocks
    mock_config_instance = Mock()
    mock_config_instance.gamma_base_url = "https://gamma-api.polymarket.com"
    mock_config_instance.gamma_api_key = ""
    mock_config_instance.clob_rest_endpoint = "https://clob.polymarket.com"
    mock_config_instance.clob_endpoint = "wss://clob.polymarket.com/ws"
    mock_config_instance.subgraph_endpoint = "https://api.thegraph.com"
    mock_config.return_value = mock_config_instance

    # Mock aggregator to return sample markets
    mock_agg_instance = Mock()
    mock_agg_instance.get_top_markets_by_volume.return_value = [
        {
            "question": "Test Market 1",
            "outcomePrices": ["0.75", "0.25"],
            "volume24hr": 50000,
            "endDate": "2026-02-01T00:00:00Z",
        },
        {
            "question": "Test Market 2",
            "outcomePrices": ["0.50", "0.50"],
            "volume24hr": 30000,
            "endDate": "2026-01-20T00:00:00Z",
        },
    ]
    mock_aggregator.return_value = mock_agg_instance

    mock_console = Mock()
    mock_console.input.side_effect = ["1", "10"]

    analytics_screen(mock_console)

    # Should display submenu and table
    assert mock_console.print.call_count >= 2

    # Verify aggregator was called with correct parameters
    mock_agg_instance.get_top_markets_by_volume.assert_called_once_with(limit=10, min_volume=1000)


def test_analytics_screen_coming_soon():
    """Test analytics screen coming soon features"""
    mock_console = Mock()
    mock_console.input.return_value = "2"
    
    analytics_screen(mock_console)
    
    # Should show coming soon message
    calls = [str(call) for call in mock_console.print.call_args_list]
    assert any("coming soon" in str(call).lower() for call in calls)


@patch('polyterm.tui.screens.portfolio.subprocess.run')
def test_portfolio_screen(mock_run):
    """Test portfolio screen launches"""
    mock_console = Mock()
    mock_console.input.return_value = "0x123..."
    
    portfolio_screen(mock_console)
    
    # Should print panel and prompts
    assert mock_console.print.call_count >= 2


@patch('polyterm.tui.screens.export.subprocess.run')
def test_export_screen_json(mock_run):
    """Test export screen with JSON format"""
    mock_run.return_value = Mock(returncode=0, stderr="")
    mock_console = Mock()
    mock_console.input.side_effect = ["market123", "json", "output.json"]
    
    export_screen(mock_console)
    
    # Should collect input
    assert mock_console.input.call_count == 3


def test_export_screen_no_market():
    """Test export screen handles no market input"""
    mock_console = Mock()
    mock_console.input.return_value = ""
    
    export_screen(mock_console)
    
    # Should show error
    calls = [str(call) for call in mock_console.print.call_args_list]
    assert any("no market" in str(call).lower() for call in calls)


@patch('polyterm.tui.screens.settings.Config')
def test_settings_screen(mock_config_class):
    """Test settings screen displays config"""
    mock_config = Mock()
    mock_config.config_path = "/path/to/config.toml"
    mock_config.alert_threshold = 5
    mock_config.refresh_rate = 2
    mock_config.min_volume = 1000
    mock_config.rate_limit_calls = 10
    mock_config.rate_limit_period = 60
    mock_config_class.return_value = mock_config
    
    mock_console = Mock()
    mock_console.input.return_value = "4"
    
    settings_screen(mock_console)
    
    # Should display settings table
    assert mock_console.print.call_count >= 2


def test_help_screen():
    """Test help screen displays documentation"""
    mock_console = Mock()
    
    help_screen(mock_console)
    
    # Should print multiple sections
    assert mock_console.print.call_count >= 5
    
    # Check that key sections are printed
    calls = [str(call) for call in mock_console.print.call_args_list]
    assert any("shortcuts" in str(call).lower() for call in calls)
    assert any("features" in str(call).lower() for call in calls)


