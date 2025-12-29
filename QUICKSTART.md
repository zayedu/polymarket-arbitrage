# 🚀 Polymarket Copy Trading Bot - Quick Start

## ✅ Your Bot is Running!

The bot is currently tracking **@ilovecircle** (74% accuracy, $2.2M profit) and will email you at **umerzayed1@gmail.com** when they make new trades.

---

## 📋 Essential Commands

```bash
# View live activity
tail -f copy_trading.log

# Stop the bot
./scripts/stop_bot.sh

# Start the bot
./scripts/run_background.sh

# Test email notifications
python3 -m src.app.main --test-notifications
```

---

## 📧 When You'll Get Notified

You'll receive an email when @ilovecircle:
- ✅ Opens a **NEW** position (not existing ones)
- ✅ At a reasonable price (< 90¢)
- ✅ With good profit potential
- ✅ Passes all safety filters

---

## 🔍 Current Status

- **Tracking:** 1 whale (@ilovecircle)
- **Active Positions:** 16 positions
- **Mode:** Paper trading (safe, no real money)
- **Poll Interval:** Every 10 seconds

---

## 💡 Why No Signals Yet?

The bot is working correctly! It's filtering out @ilovecircle's current positions because:

- ❌ They're existing positions (opened before you started tracking)
- ❌ Prices are too high (0.95+) = low profit potential
- ✅ **This is good!** The bot protects you from bad trades

---

## 🎯 What Happens Next?

1. **Bot monitors** @ilovecircle 24/7
2. **When they open a NEW position**, you get an email
3. **Review the signal** and decide if you want to copy
4. **Manually execute** the trade on Polymarket (paper trading mode)

---

## 🛠️ Configuration

Your settings are in `.env`:

```bash
# Copy Trading
COPY_TRADING_ENABLED=true
COPY_WHALE_ADDRESSES=0xa9878e59934ab507f9039bcb917c1bae0451141d
COPY_RATIO=0.01          # Copy 1% of their position size
MAX_COPY_SIZE=50         # Max $50 per trade
MIN_WHALE_ACCURACY=70    # Only copy if >70% accuracy

# Notifications
ENABLE_NOTIFICATIONS=true
NOTIFICATION_EMAIL_TO=umerzayed1@gmail.com
```

---

## 📊 Repository Structure

```
predictions_market_arbitrage/
├── src/                 # Source code
│   ├── app/            # Main application
│   ├── core/           # Core functionality
│   ├── polymarket/     # API clients
│   └── ml/             # Copy trading logic
├── scripts/            # Helper scripts
├── deploy/             # Deployment configs
└── tests/              # Unit tests
```

---

## 🚨 Troubleshooting

**Bot not running?**
```bash
./scripts/run_background.sh
```

**Check if bot is active:**
```bash
ps aux | grep "src.app.main"
```

**View recent errors:**
```bash
tail -50 copy_trading.log | grep ERROR
```

---

## 🎉 You're All Set!

Your bot is watching @ilovecircle and will alert you when opportunities arise. Just let it run and wait for the email! 🐋💰

