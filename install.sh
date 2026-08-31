#!/bin/bash

# PolyTerm Easy Install Script
# This script makes it super easy to install and run PolyTerm

set -e

echo "🚀 PolyTerm Easy Install"
echo "========================="

# Check if pipx is installed
if ! command -v pipx &> /dev/null; then
    echo "📦 Installing pipx (required for PolyTerm)..."
    
    # Check if brew is available
    if command -v brew &> /dev/null; then
        brew install pipx
    else
        echo "❌ Homebrew not found. Please install Homebrew first:"
        echo "   /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
    
    # Ensure pipx path is in PATH
    pipx ensurepath
    echo "✅ pipx installed successfully!"
else
    echo "✅ pipx already installed"
fi

# Install PolyTerm from GitHub main (PyPI is decommissioned)
echo "📥 Installing PolyTerm from GitHub main..."
pipx install git+https://github.com/NYTEMODEONLY/polyterm.git@main

echo ""
echo "🎉 Installation complete!"
echo ""
echo "You can now run PolyTerm from anywhere with:"
echo "   polyterm"
echo ""
echo "To get started:"
echo "   polyterm --help"
echo ""
echo "Happy trading! 📊"
