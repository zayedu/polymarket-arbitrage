#!/bin/bash
# Quick setup script to copy @ilovecircle

echo "🐋 Setting up to copy @ilovecircle..."
echo ""
echo "Wallet Address: 0xa9878e59934ab507f9039bcb917c1bae0451141d"
echo "Stats: 1,347 trades, 74% accuracy, $2.2M profit"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env from template..."
    cp env.template .env
fi

# Add ilovecircle configuration
echo ""
echo "Adding @ilovecircle configuration to .env..."
cat >> .env << 'ENVEOF'

# ============================================
# COPY TRADING - @ilovecircle (Auto-added)
# ============================================
COPY_TRADING_ENABLED=true
COPY_WHALE_ADDRESSES=0xa9878e59934ab507f9039bcb917c1bae0451141d
COPY_RATIO=0.01
MAX_COPY_SIZE=50
MIN_WHALE_ACCURACY=70
ENVEOF

echo "✅ Configuration added!"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your SendGrid API key"
echo "2. Update SMS_ENABLED=true and SMS_PHONE_NUMBER=6475173009"
echo "3. Run: python3 -m src.app.main --mode copy"
echo ""
echo "📖 See SETUP_ILOVECIRCLE.md for full guide"
