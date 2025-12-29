#!/bin/bash

# Polymarket Copy Trading Bot Launcher
# Tracks @ilovecircle's positions and sends email alerts

# Navigate to project root (parent of scripts/)
cd "$(dirname "$0")/.."

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║  🐋 Polymarket Copy Trading Bot Starting...                   ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 Tracking: @ilovecircle (74% accuracy, $2.2M profit)"
echo "📧 Email alerts: umerzayed1@gmail.com"
echo "💰 Mode: Paper trading (safe)"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Set PYTHONPATH and run the bot
PROJECT_ROOT=$(pwd)
PYTHONPATH="${PROJECT_ROOT}" python3 -m src.app.main --mode copy

