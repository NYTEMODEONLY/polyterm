"""Tests for TUI menu and logo"""

import pytest
from io import StringIO
from unittest.mock import Mock, patch, PropertyMock
from polyterm.tui.menu import MainMenu
from polyterm.tui.logo import display_logo


def test_logo_display():
    """Test logo display function"""
    mock_console = Mock()
    # Mock console.size.width to return a specific width
    mock_size = Mock()
    mock_size.width = 80
    mock_console.size = mock_size

    display_logo(mock_console)

    # Should call print with logo and style
    assert mock_console.print.call_count == 2  # Logo + newline
    first_call = mock_console.print.call_args_list[0]
    # Check that logo contains expected text
    logo_text = first_call[0][0]
    assert "PolyMarket" in logo_text
    assert "Track. Analyze. Profit." in logo_text
    assert 'style' in first_call[1]


def test_logo_display_narrow():
    """Test logo display for narrow terminals"""
    mock_console = Mock()
    mock_size = Mock()
    mock_size.width = 50  # Narrow terminal
    mock_console.size = mock_size

    display_logo(mock_console)

    assert mock_console.print.call_count == 2
    first_call = mock_console.print.call_args_list[0]
    logo_text = first_call[0][0]
    # Narrow logo should still have key text
    assert "PolyTerm" in logo_text
    assert "Track. Analyze. Profit." in logo_text


def test_main_menu_creation():
    """Test MainMenu can be created"""
    menu = MainMenu()
    assert menu is not None
    assert hasattr(menu, 'console')
    assert hasattr(menu, 'display')
    assert hasattr(menu, 'get_choice')


@patch('polyterm.tui.menu.Console')
def test_main_menu_display(mock_console_class):
    """Test menu display creates panel"""
    mock_console = Mock()
    # Mock console.size.width for responsive menu
    mock_size = Mock()
    mock_size.width = 80
    mock_console.size = mock_size
    mock_console_class.return_value = mock_console

    menu = MainMenu()
    menu.display()
    
    # Should print panel and newline
    assert mock_console.print.call_count >= 1


@patch('polyterm.tui.menu.Console')
def test_main_menu_get_choice(mock_console_class):
    """Test menu choice input"""
    mock_console = Mock()
    mock_console.input.return_value = "1"
    mock_console_class.return_value = mock_console
    
    menu = MainMenu()
    choice = menu.get_choice()
    
    assert choice == "1"
    assert mock_console.input.called


@patch('polyterm.tui.menu.Console')
def test_main_menu_choice_lowercase(mock_console_class):
    """Test menu choice is converted to lowercase"""
    mock_console = Mock()
    mock_console.input.return_value = "  Q  "
    mock_console_class.return_value = mock_console
    
    menu = MainMenu()
    choice = menu.get_choice()
    
    assert choice == "q"


