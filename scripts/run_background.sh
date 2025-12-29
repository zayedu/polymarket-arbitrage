#!/bin/bash

# Run Polymarket Copy Trading Bot in Background
# Logs everything to copy_trading.log

# Navigate to project root (parent of scripts/)
cd "$(dirname "$0")/.."

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║  🐋 Starting Polymarket Bot in Background...                  ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check if already running
if pgrep -f "src.app.main --mode copy" > /dev/null; then
    echo "⚠️  Bot is already running!"
    echo "   Use ./scripts/stop_bot.sh to stop it first"
    exit 1
fi

# Set PYTHONPATH and start in background
# Use env to ensure PYTHONPATH is passed to nohup
PROJECT_ROOT=$(pwd)
nohup env PYTHONPATH="${PROJECT_ROOT}" python3 -m src.app.main --mode copy > copy_trading.log 2>&1 &

PID=$!
echo "✅ Bot started in background!"
echo "   PID: $PID"
echo "   Logs: $(pwd)/copy_trading.log"
echo ""
echo "📊 Commands:"
echo "   • View logs:  tail -f copy_trading.log"
echo "   • Stop bot:   ./scripts/stop_bot.sh"
echo ""

