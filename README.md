# 🐋 Polymarket Copy Trading Bot

Automatically copy trades from high-performing Polymarket traders.

Currently tracking **@ilovecircle** (74% accuracy, $2.2M profit in 2 months).

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure
Copy `env.template` to `.env` and fill in your settings:
```bash
cp env.template .env
```

Required settings:
- `SENDGRID_API_KEY` - For email notifications
- `NOTIFICATION_EMAIL_TO` - Your email address
- `COPY_WHALE_ADDRESSES` - Wallet address to copy (already set to @ilovecircle)

### 3. Run
```bash
# Watch live in terminal
./scripts/start_bot.sh

# Run in background 24/7
./scripts/run_background.sh

# Stop the bot
./scripts/stop_bot.sh
```

## 📊 What It Does

- **Monitors** @ilovecircle's wallet for new positions
- **Alerts** you via email when they make a move
- **Generates** copy trade signals with recommended size
- **Tracks** performance and PnL
- **Paper trades** by default (safe mode)

## 📧 Email Notifications

You'll receive emails when:
- @ilovecircle opens a new position
- A copy trade signal is generated
- The bot encounters an error

Check your email's "All Mail" folder if you don't see notifications in inbox.

## ⚙️ Configuration

Key settings in `.env`:

```bash
# Copy Trading
COPY_TRADING_ENABLED=true
COPY_WHALE_ADDRESSES=0xa9878e59934ab507f9039bcb917c1bae0451141d
COPY_RATIO=0.01          # Copy 1% of their position size
MAX_COPY_SIZE=50         # Max $50 per trade

# Mode
TRADING_MODE=paper       # paper or live
```

## 📚 Documentation

- **[Quick Start Guide](docs/QUICKSTART.md)** - Get started in 5 minutes
- **[Final Setup](docs/FINAL_SETUP.md)** - Complete setup instructions
- **[Copy Trading Guide](docs/COPY_TRADING_GUIDE.md)** - Detailed strategy guide

## 🎯 Current Tracking

**@ilovecircle**
- Wallet: `0xa9878e59934ab507f9039bcb917c1bae0451141d`
- Accuracy: 74%
- Profit: $2.2M in 2 months
- Portfolio: $1.2M across 16 positions
- Strategy: AI probability models (ensemble of 10 models)

## 🛑 Safety

- **Paper trading mode** by default (no real money)
- **Position size limits** prevent over-exposure
- **Risk management** built-in
- **Email alerts** keep you informed

## 🚨 Going Live

When ready to execute real trades:

1. Get capital on Polymarket
2. Add `POLYMARKET_PRIVATE_KEY` to `.env`
3. Change `TRADING_MODE=live`
4. Start with small sizes (`MAX_COPY_SIZE=10`)

## 📝 License

MIT

## ⚠️ Disclaimer

This bot is for educational purposes. Trading involves risk. Past performance doesn't guarantee future results. Start with paper trading and small positions.
