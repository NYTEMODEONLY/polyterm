"""Tests to ensure CLI commands still work alongside TUI"""

import pytest
from click.testing import CliRunner
from unittest.mock import Mock, patch, MagicMock
from polyterm.cli.main import cli


@patch('polyterm.tui.controller.TUIController')
def test_polyterm_no_args_launches_tui(mock_tui_class):
    """Test 'polyterm' with no args launches TUI"""
    mock_tui = Mock()
    mock_tui_class.return_value = mock_tui
    
    runner = CliRunner()
    result = runner.invoke(cli, [])
    
    # Should have created and run TUI
    assert mock_tui_class.called
    assert mock_tui.run.called


def test_polyterm_monitor_still_works():
    """Test 'polyterm monitor' command exists and has help"""
    runner = CliRunner()
    result = runner.invoke(cli, ['monitor', '--help'])
    
    # Should show monitor help, not TUI
    assert result.exit_code == 0
    assert 'monitor' in result.output.lower()


def test_polyterm_whales_command_exists():
    """Test 'polyterm whales' command is registered"""
    runner = CliRunner()
    result = runner.invoke(cli, ['whales', '--help'])
    
    # Should show whales help, not TUI
    assert result.exit_code == 0
    assert 'whales' in result.output.lower() or 'whale' in result.output.lower()


def test_polyterm_watch_command_exists():
    """Test 'polyterm watch' command is registered"""
    runner = CliRunner()
    result = runner.invoke(cli, ['watch', '--help'])
    
    # Should show watch help, not TUI
    assert result.exit_code == 0
    assert 'watch' in result.output.lower()


def test_polyterm_portfolio_command_exists():
    """Test 'polyterm portfolio' command is registered"""
    runner = CliRunner()
    result = runner.invoke(cli, ['portfolio', '--help'])
    
    # Should show portfolio help, not TUI
    assert result.exit_code == 0
    assert 'portfolio' in result.output.lower()


def test_polyterm_export_command_exists():
    """Test 'polyterm export' command is registered"""
    runner = CliRunner()
    result = runner.invoke(cli, ['export', '--help'])
    
    # Should show export help, not TUI
    assert result.exit_code == 0
    assert 'export' in result.output.lower()


def test_polyterm_config_command_exists():
    """Test 'polyterm config' command is registered"""
    runner = CliRunner()
    result = runner.invoke(cli, ['config', '--help'])
    
    # Should show config help, not TUI
    assert result.exit_code == 0
    assert 'config' in result.output.lower()


def test_polyterm_version():
    """Test 'polyterm --version' works"""
    import polyterm
    runner = CliRunner()
    result = runner.invoke(cli, ['--version'])

    # Should show version, not TUI
    assert result.exit_code == 0
    assert polyterm.__version__ in result.output


def test_polyterm_help():
    """Test 'polyterm --help' works"""
    runner = CliRunner()
    result = runner.invoke(cli, ['--help'])

    # Should show CLI help, not TUI
    assert result.exit_code == 0
    assert 'PolyMarket' in result.output or 'monitor' in result.output.lower()


def test_monitor_sort_option_exists():
    """Test 'polyterm monitor --sort' option exists (used by analytics screen)"""
    runner = CliRunner()
    result = runner.invoke(cli, ['monitor', '--help'])

    # Should show sort option in help
    assert result.exit_code == 0
    assert '--sort' in result.output
    assert 'volume' in result.output.lower()


def test_monitor_sort_volume_is_valid():
    """Test 'polyterm monitor --sort volume' is a valid command"""
    runner = CliRunner()
    # Just check that the option is accepted (don't actually run monitor)
    result = runner.invoke(cli, ['monitor', '--sort', 'volume', '--help'])

    assert result.exit_code == 0


def test_monitor_sort_probability_is_valid():
    """Test 'polyterm monitor --sort probability' is a valid command"""
    runner = CliRunner()
    result = runner.invoke(cli, ['monitor', '--sort', 'probability', '--help'])

    assert result.exit_code == 0


def test_monitor_sort_recent_is_valid():
    """Test 'polyterm monitor --sort recent' is a valid command"""
    runner = CliRunner()
    result = runner.invoke(cli, ['monitor', '--sort', 'recent', '--help'])

    assert result.exit_code == 0


def test_monitor_invalid_sort_rejected():
    """Test 'polyterm monitor --sort invalid' is rejected"""
    runner = CliRunner()
    result = runner.invoke(cli, ['monitor', '--sort', 'invalid'])

    assert result.exit_code != 0
    assert 'invalid' in result.output.lower() or 'choice' in result.output.lower()

