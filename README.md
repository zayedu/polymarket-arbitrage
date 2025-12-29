# 🐋 Polymarket Copy Trading Bot

Automatically copy trades from the top 5 performing Polymarket traders.

**Currently tracking:** archaic, Car, nicoco89, JJo, Anjun (from Prediction Market Leaderboard)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure

Copy `env.template` to `.env` and fill in:

```bash
cp env.template .env
```

Required settings:

- `SENDGRID_API_KEY` - For email notifications
- `NOTIFICATION_EMAIL_TO` - Your email
- `DISCORD_WEBHOOK_URL` - Discord webhook for instant alerts
- `COPY_WHALE_ADDRESSES` - Already configured with top 5 traders

### 3. Run

```bash
# Run in background 24/7
./scripts/run_background.sh

# Watch live in terminal
./scripts/start_bot.sh

# Stop the bot
./scripts/stop_bot.sh

# View logs
tail -f copy_trading.log
```

## 📊 What It Does

- **Monitors** top 5 traders' wallets every 10 seconds
- **Alerts** you via Discord & email when they make new trades
- **Generates** copy trade signals with recommended size
- **Tracks** performance and PnL
- **Paper trades** by default (100% safe)

## 🔔 Notifications

You'll get **Discord + Email** alerts when:

- Any of the 5 traders opens a new position
- Includes market link, position type, prices, and recommended copy size
- Instant notifications (checks every 10 seconds)

## 🎯 Tracked Traders

All from the **Prediction Market Leaderboard** (ranked by consistency, win rate, and profit factor):

1. **archaic** - $101k positions, 1,898 predictions
2. **Car** - $397k positions, 4,662 predictions
3. **nicoco89** - $63k positions, 1,588 predictions
4. **JJo** - $181k positions, 1,220 predictions
5. **Anjun** - $575k positions, 8,919 predictions

## ⚙️ Configuration

Key settings in `.env`:

```bash
# Copy Trading
COPY_TRADING_ENABLED=true
COPY_WHALE_ADDRESSES=0x1f0a...7aa,0x7c3d...c6b,... # Top 5 traders
COPY_RATIO=0.01          # Copy 1% of their position size
MAX_COPY_SIZE=50         # Max $50 per trade

# Notifications
DISCORD_ENABLED=true
ENABLE_NOTIFICATIONS=true

# Mode
TRADING_MODE=paper       # paper or live
```

## 🛑 Safety

- **Paper trading mode** by default (no real money)
- **Position size limits** prevent over-exposure
- **Risk management** built-in
- **Discord & Email alerts** keep you informed

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
