#!/bin/bash
# Quick start script for Polymarket Arbitrage Bot

set -e

echo "🚀 Polymarket Arbitrage Bot - Quick Start"
echo "=========================================="
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.11 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✅ Found Python $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating from template..."
    if [ -f "env.template" ]; then
        cp env.template .env
        echo "✅ Created .env file. Please edit it with your settings:"
        echo "   - Add your POLYMARKET_PRIVATE_KEY for live trading"
        echo "   - Adjust risk parameters for your capital"
    else
        echo "❌ env.template not found. Please create .env manually."
        exit 1
    fi
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Available modes:"
echo "   1. Scan mode (no trading):       python -m src.app.main --mode scan"
echo "   2. Paper trading (simulation):   python -m src.app.main --mode paper"
echo "   3. Live trading (real money):    python -m src.app.main --mode live"
echo ""
echo "⚠️  IMPORTANT: Always test in paper mode first!"
echo ""
read -p "Would you like to run a test scan now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔍 Running test scan..."
    python -m src.app.main --mode scan --iterations 1
fi

