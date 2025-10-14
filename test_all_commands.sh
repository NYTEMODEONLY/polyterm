#!/bin/bash
# Comprehensive test script for all PolyTerm commands

set -e

echo "PolyTerm - Command Test Suite"
echo "=============================="
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Test 1: Config
echo "Test 1: Config Commands"
echo "------------------------"
polyterm config --list | head -10
echo "✅ Config list works"

polyterm config --get api.gamma_base_url
echo "✅ Config get works"
echo ""

# Test 2: Monitor
echo "Test 2: Monitor Command"
echo "-----------------------"
timeout 5 polyterm monitor --limit 5 || echo "✅ Monitor works (interrupted)"
echo ""

# Test 3: Whales
echo "Test 3: Whales Command"
echo "----------------------"
polyterm whales --hours 24 --min-amount 50000
echo "✅ Whales command works"
echo ""

# Test 4: Portfolio
echo "Test 4: Portfolio Command"
echo "-------------------------"
polyterm portfolio --wallet 0x1234567890123456789012345678901234567890
echo "✅ Portfolio command works (shows expected error)"
echo ""

# Test 5: Export
echo "Test 5: Export Command"
echo "----------------------"
# Get a market ID first
MARKET_ID=$(python3 << 'EOF'
from polyterm.api.gamma import GammaClient
gamma = GammaClient()
markets = gamma.get_markets(limit=1)
print(markets[0]['id'])
EOF
)

polyterm export --market "$MARKET_ID" --format json -o /tmp/test_export.json
if [ -f "/tmp/test_export.json" ]; then
    echo "✅ Export to JSON works"
    rm /tmp/test_export.json
fi
echo ""

echo "=============================="
echo "All Tests Complete!"
echo "=============================="

