"""Color themes for TUI"""

from typing import Dict

# Color theme definitions
THEMES: Dict[str, Dict[str, str]] = {
    'default': {
        'logo': 'bold cyan',
        'menu_title': 'bold yellow',
        'menu_border': 'green',
        'menu_key': 'cyan bold',
        'menu_text': 'white',
        'panel_border': 'cyan',
        'success': 'green',
        'warning': 'yellow',
        'error': 'red',
        'info': 'blue',
        'dim': 'dim',
        'status_bar': 'on blue',
    },
    
    'dark': {
        'logo': 'bold blue',
        'menu_title': 'bold white',
        'menu_border': 'blue',
        'menu_key': 'blue bold',
        'menu_text': 'bright_white',
        'panel_border': 'blue',
        'success': 'bright_green',
        'warning': 'bright_yellow',
        'error': 'bright_red',
        'info': 'bright_blue',
        'dim': 'dim',
        'status_bar': 'on black',
    },
    
    'light': {
        'logo': 'bold blue',
        'menu_title': 'bold black',
        'menu_border': 'black',
        'menu_key': 'blue bold',
        'menu_text': 'black',
        'panel_border': 'blue',
        'success': 'green',
        'warning': 'yellow',
        'error': 'red',
        'info': 'blue',
        'dim': 'dim white',
        'status_bar': 'on white',
    },
    
    'matrix': {
        'logo': 'bold green',
        'menu_title': 'bold green',
        'menu_border': 'green',
        'menu_key': 'green bold',
        'menu_text': 'bright_green',
        'panel_border': 'green',
        'success': 'bright_green',
        'warning': 'green',
        'error': 'red',
        'info': 'green',
        'dim': 'dim green',
        'status_bar': 'on black',
    },
}


def get_theme(name: str = 'default') -> Dict[str, str]:
    """Get color theme by name
    
    Args:
        name: Theme name (default, dark, light, matrix)
    
    Returns:
        Theme color dictionary
    """
    return THEMES.get(name, THEMES['default'])


def list_themes() -> list:
    """List available theme names
    
    Returns:
        List of theme names
    """
    return list(THEMES.keys())


