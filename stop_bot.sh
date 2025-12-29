#!/bin/bash

# Stop the Polymarket Copy Trading Bot

echo "🛑 Stopping Polymarket Copy Trading Bot..."

# Find and kill the bot process
pkill -f "src.app.main --mode copy"

if [ $? -eq 0 ]; then
    echo "✅ Bot stopped successfully"
else
    echo "ℹ️  No bot process found (already stopped)"
fi

