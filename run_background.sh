#!/bin/bash

# Run Polymarket Copy Trading Bot in Background
# Logs everything to copy_trading.log

cd "$(dirname "$0")"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║  🐋 Starting Polymarket Bot in Background...                  ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check if already running
if pgrep -f "src.app.main --mode copy" > /dev/null; then
    echo "⚠️  Bot is already running!"
    echo "   Use ./stop_bot.sh to stop it first"
    exit 1
fi

# Start in background
nohup python3 -m src.app.main --mode copy > copy_trading.log 2>&1 &

PID=$!
echo "✅ Bot started in background!"
echo "   PID: $PID"
echo "   Logs: copy_trading.log"
echo ""
echo "📊 Commands:"
echo "   • View logs:  tail -f copy_trading.log"
echo "   • Stop bot:   ./stop_bot.sh"
echo ""

