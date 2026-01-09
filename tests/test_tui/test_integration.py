"""Integration tests for TUI"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from polyterm.tui.controller import TUIController


@patch('polyterm.tui.controller.Console')
def test_tui_controller_creation(mock_console_class):
    """Test TUI controller can be created"""
    controller = TUIController()
    
    assert controller is not None
    assert hasattr(controller, 'console')
    assert hasattr(controller, 'menu')
    assert hasattr(controller, 'running')
    assert controller.running is True


@patch('polyterm.tui.controller.display_logo')
@patch('polyterm.tui.controller.Console')
def test_tui_quit_command(mock_console_class, mock_display_logo):
    """Test TUI quits on 'q' command"""
    mock_console = Mock()
    mock_console_class.return_value = mock_console
    
    mock_menu = Mock()
    mock_menu.get_choice.return_value = 'q'
    
    controller = TUIController()
    controller.menu = mock_menu
    controller.run()
    
    # Should have quit
    assert controller.running is False
    assert mock_console.print.called


@patch('polyterm.tui.controller.display_logo')
@patch('polyterm.tui.controller.help_screen')
@patch('polyterm.tui.controller.Console')
def test_tui_help_command(mock_console_class, mock_help_screen, mock_display_logo):
    """Test TUI shows help on 'h' command"""
    mock_console = Mock()
    mock_console_class.return_value = mock_console
    
    mock_menu = Mock()
    mock_menu.get_choice.side_effect = ['h', 'q']
    
    # Mock input to return to menu
    with patch('builtins.input', return_value=''):
        controller = TUIController()
        controller.menu = mock_menu
        controller.run()
    
    # Should have called help screen
    assert mock_help_screen.called


@patch('polyterm.tui.controller.display_logo')
@patch('polyterm.tui.controller.Console')
def test_tui_invalid_choice(mock_console_class, mock_display_logo):
    """Test TUI handles invalid menu choice"""
    mock_console = Mock()
    mock_console_class.return_value = mock_console
    
    mock_menu = Mock()
    mock_menu.get_choice.side_effect = ['invalid', 'q']
    
    # Mock the input() call to return to menu
    with patch('builtins.input', return_value=''):
        controller = TUIController()
        controller.menu = mock_menu
        controller.run()
    
    # Should have printed error message
    error_calls = [call for call in mock_console.print.call_args_list 
                   if 'Invalid choice' in str(call)]
    assert len(error_calls) > 0


@patch('polyterm.tui.controller.display_logo')
@patch('polyterm.tui.controller.Console')
def test_tui_keyboard_interrupt(mock_console_class, mock_display_logo):
    """Test TUI handles Ctrl+C gracefully"""
    mock_console = Mock()
    mock_console_class.return_value = mock_console
    
    mock_menu = Mock()
    mock_menu.get_choice.side_effect = KeyboardInterrupt()
    
    controller = TUIController()
    controller.menu = mock_menu
    controller.run()
    
    # Should have handled interrupt
    assert controller.running is False


@patch('polyterm.tui.controller.display_logo')
@patch('polyterm.tui.controller.monitor_screen')
@patch('polyterm.tui.controller.Console')
def test_tui_monitor_navigation(mock_console_class, mock_monitor_screen, mock_display_logo):
    """Test TUI navigates to monitor screen"""
    mock_console = Mock()
    mock_console_class.return_value = mock_console
    
    mock_menu = Mock()
    mock_menu.get_choice.side_effect = ['1', 'q']
    
    with patch('builtins.input', return_value=''):
        controller = TUIController()
        controller.menu = mock_menu
        controller.run()
    
    # Should have called monitor screen
    assert mock_monitor_screen.called


@patch('polyterm.tui.controller.display_logo')
@patch('polyterm.tui.controller.whales_screen')
@patch('polyterm.tui.controller.Console')
def test_tui_whales_navigation(mock_console_class, mock_whales_screen, mock_display_logo):
    """Test TUI navigates to whales screen"""
    mock_console = Mock()
    mock_console_class.return_value = mock_console

    mock_menu = Mock()
    # Whales is now option 3 (option 2 is live monitor)
    mock_menu.get_choice.side_effect = ['3', 'q']

    with patch('builtins.input', return_value=''):
        controller = TUIController()
        controller.menu = mock_menu
        controller.run()

    # Should have called whales screen
    assert mock_whales_screen.called


@patch('polyterm.tui.controller.display_logo')
@patch('polyterm.tui.controller.Console')
def test_tui_alternative_shortcuts(mock_console_class, mock_display_logo):
    """Test TUI accepts alternative shortcuts"""
    mock_console = Mock()
    mock_console_class.return_value = mock_console
    
    mock_menu = Mock()
    
    # Test 'm' for monitor
    with patch('polyterm.tui.controller.monitor_screen') as mock_monitor:
        mock_menu.get_choice.side_effect = ['m', 'q']
        
        with patch('builtins.input', return_value=''):
            controller = TUIController()
            controller.menu = mock_menu
            controller.run()
        
        assert mock_monitor.called

