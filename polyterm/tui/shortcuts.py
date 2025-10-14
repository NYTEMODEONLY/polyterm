"""Keyboard shortcuts for TUI"""

# Shortcut mappings for menu navigation
SHORTCUTS = {
    # Primary shortcuts (numbers)
    '1': 'monitor',
    '2': 'whales',
    '3': 'watch',
    '4': 'analytics',
    '5': 'portfolio',
    '6': 'export',
    '7': 'settings',
    
    # Alternative letter shortcuts
    'm': 'monitor',
    'w': 'whales',
    'a': 'analytics',
    'p': 'portfolio',
    'e': 'export',
    's': 'settings',
    
    # Help and quit
    'h': 'help',
    '?': 'help',
    'q': 'quit',
    'exit': 'quit',
    'quit': 'quit',
}


def get_action(key: str) -> str:
    """Get action for a given key
    
    Args:
        key: The key pressed (lowercase)
    
    Returns:
        Action name or the key itself if no mapping
    """
    return SHORTCUTS.get(key.lower(), key)


