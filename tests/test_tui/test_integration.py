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
@patch('polyterm.tui.controller.Console')
def test_tui_help_command(mock_console_class, mock_display_logo):
    """Test TUI shows help on 'h' command"""
    from polyterm.tui.controller import SCREEN_ROUTES
    mock_console = Mock()
    mock_console_class.return_value = mock_console

    mock_menu = Mock()
    mock_menu.get_choice.side_effect = ['h', 'q']

    mock_help = Mock()
    original = SCREEN_ROUTES['h']
    SCREEN_ROUTES['h'] = mock_help
    SCREEN_ROUTES['?'] = mock_help
    try:
        # Mock input to return to menu
        with patch('builtins.input', return_value=''):
            controller = TUIController()
            controller.menu = mock_menu
            controller.run()

        # Should have called help screen
        assert mock_help.called
    finally:
        SCREEN_ROUTES['h'] = original
        SCREEN_ROUTES['?'] = original


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
@patch('polyterm.tui.controller.Console')
def test_tui_monitor_navigation(mock_console_class, mock_display_logo):
    """Test TUI navigates to monitor screen"""
    from polyterm.tui.controller import SCREEN_ROUTES
    mock_console = Mock()
    mock_console_class.return_value = mock_console

    mock_menu = Mock()
    mock_menu.get_choice.side_effect = ['1', 'q']

    mock_monitor = Mock()
    original = SCREEN_ROUTES['1']
    SCREEN_ROUTES['1'] = mock_monitor
    try:
        with patch('builtins.input', return_value=''):
            controller = TUIController()
            controller.menu = mock_menu
            controller.run()

        # Should have called monitor screen
        assert mock_monitor.called
    finally:
        SCREEN_ROUTES['1'] = original


@patch('polyterm.tui.controller.display_logo')
@patch('polyterm.tui.controller.Console')
def test_tui_whales_navigation(mock_console_class, mock_display_logo):
    """Test TUI navigates to whales screen"""
    from polyterm.tui.controller import SCREEN_ROUTES
    mock_console = Mock()
    mock_console_class.return_value = mock_console

    mock_menu = Mock()
    # Whales is now option 3 (option 2 is live monitor)
    mock_menu.get_choice.side_effect = ['3', 'q']

    mock_whales = Mock()
    original = SCREEN_ROUTES['3']
    SCREEN_ROUTES['3'] = mock_whales
    try:
        with patch('builtins.input', return_value=''):
            controller = TUIController()
            controller.menu = mock_menu
            controller.run()

        # Should have called whales screen
        assert mock_whales.called
    finally:
        SCREEN_ROUTES['3'] = original


@patch('polyterm.tui.controller.display_logo')
@patch('polyterm.tui.controller.Console')
def test_tui_alternative_shortcuts(mock_console_class, mock_display_logo):
    """Test TUI accepts alternative shortcuts"""
    from polyterm.tui.controller import SCREEN_ROUTES
    mock_console = Mock()
    mock_console_class.return_value = mock_console

    mock_menu = Mock()

    # Test 'mon' for monitor ('m' is now used for menu pagination)
    mock_monitor = Mock()
    original = SCREEN_ROUTES['mon']
    SCREEN_ROUTES['mon'] = mock_monitor
    try:
        mock_menu.get_choice.side_effect = ['mon', 'q']

        with patch('builtins.input', return_value=''):
            controller = TUIController()
            controller.menu = mock_menu
            controller.run()

        assert mock_monitor.called
    finally:
        SCREEN_ROUTES['mon'] = original

