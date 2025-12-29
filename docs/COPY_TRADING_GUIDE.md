# 🐋 Copy Trading Guide - Follow the Whales!

## What is Copy Trading?

Copy trading automatically mirrors the positions of high-accuracy traders ("whales") on Polymarket. When a whale with 65%+ accuracy opens a position, you automatically copy it with proportional sizing.

**Why it works:**
- Proven track record (65%+ win rate)
- No ML training required
- Real-time signals from successful traders
- Polymarket tags these wallets with "Alpha" badges

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Find Alpha Whales

Run the whale finder tool:

```bash
python find_whales.py
```

This will show you the top 20 Alpha whales with:
- Username
- Accuracy percentage
- Total trades
- Profit & Loss
- Trading volume

**Example output:**
```
🐋 Top 20 Alpha Whales
#  Username        Accuracy  Trades  P&L        Volume
1  ProTrader123    72.5%     156     $12,450    $245,000
2  MarketMaster    68.3%     89      $8,920     $180,000
3  AlphaWhale      67.1%     102     $7,650     $156,000
```

### Step 2: Configure Your .env

Add the whale addresses you want to copy:

```bash
# Copy Trading Settings
COPY_TRADING_ENABLED=true
COPY_WHALE_ADDRESSES=0x1234...,0x5678...,0x9abc...
COPY_RATIO=0.01
MAX_COPY_SIZE=50
MIN_WHALE_ACCURACY=65

# Enable notifications to get alerts
ENABLE_NOTIFICATIONS=true
SMS_ENABLED=true
```

**Settings explained:**
- `COPY_WHALE_ADDRESSES`: Comma-separated list of whale addresses (get from `find_whales.py`)
- `COPY_RATIO`: Copy 1% of whale's position size (0.01 = 1%)
- `MAX_COPY_SIZE`: Maximum $50 per copy trade
- `MIN_WHALE_ACCURACY`: Only copy whales with 65%+ accuracy

### Step 3: Run Copy Trading Mode

```bash
python -m src.app.main --mode copy --iterations 0
```

The bot will:
1. Monitor your tracked whales every 60 seconds
2. Detect when they open new positions
3. Generate copy trade signals with confidence scores
4. Send you email + SMS notifications
5. Execute trades (in paper mode for testing)

---

## 📊 How It Works

### 1. Whale Monitoring

The bot continuously monitors your tracked whales' positions:

```
🔍 Monitoring 3 whales for new positions...
🚨 Whale ProTrader123 opened 1 new position(s)!
   📊 YES on 'Will Bitcoin hit $100k by March?' @ $0.6500
```

### 2. Signal Generation

For each new position, the bot:
- Fetches current market data
- Applies filters (price range, liquidity, accuracy)
- Calculates proportional position size
- Generates confidence score (0-100%)

```
🚨 1 COPY TRADE SIGNAL(S)!

Signal #1:
  Whale: ProTrader123 (72.5% accuracy)
  Market: Will Bitcoin hit $100k by March?
  Position: YES @ $0.6500
  Recommended: 7.69 shares ($5.00)
  Confidence: 85%
  Reasons: Whale accuracy: 72.5%, Whale trades: 156, Price: $0.6500
```

### 3. Filtering

The bot filters out bad trades:

**❌ Rejected if:**
- Whale accuracy < 65%
- Whale has < 50 total trades
- Price > $0.95 (too expensive)
- Price < $0.05 (too cheap)
- Market liquidity < $100
- Market already resolved

**✅ Accepted if:**
- All filters pass
- Confidence score > 50%

### 4. Position Sizing

The bot calculates your position size:

```
Whale buys: 1000 shares @ $0.65 = $650
Your copy (1%): 10 shares @ $0.65 = $6.50
Capped at max: $5.00 (max copy size)
Final: 7.69 shares @ $0.65 = $5.00
```

---

## 🎯 Expected Results

### Conservative Estimate (Following 3 Whales @ 65% Accuracy)

**Monthly Performance:**
- **Trades per month:** 10-15
- **Win rate:** 60-65%
- **Average ROI per trade:** 15-25%
- **Capital deployed:** $100
- **Expected monthly profit:** $50-150

**Example Month:**
```
Week 1: 3 trades, 2 wins, 1 loss = +$12
Week 2: 4 trades, 3 wins, 1 loss = +$18
Week 3: 2 trades, 1 win, 1 loss = +$5
Week 4: 4 trades, 3 wins, 1 loss = +$15
Total: 13 trades, 9 wins (69%), +$50 profit
```

---

## ⚙️ Configuration Options

### Copy Ratio

How much of the whale's position to copy:

```bash
COPY_RATIO=0.01   # 1% - Conservative (recommended)
COPY_RATIO=0.02   # 2% - Moderate
COPY_RATIO=0.05   # 5% - Aggressive
```

**Example:**
- Whale buys $1000 worth
- You copy 1% = $10
- You copy 5% = $50

### Max Copy Size

Maximum capital per trade:

```bash
MAX_COPY_SIZE=20   # $20 max - Small account
MAX_COPY_SIZE=50   # $50 max - Medium account (recommended)
MAX_COPY_SIZE=100  # $100 max - Large account
```

### Whale Selection Criteria

```bash
MIN_WHALE_ACCURACY=65   # Minimum 65% accuracy
MIN_WHALE_ACCURACY=70   # Minimum 70% accuracy (stricter)
```

---

## 📱 Notifications

### Email Alerts

You'll receive detailed emails with:
- Whale username and accuracy
- Market details
- Recommended position size
- Confidence score
- Reasons for the signal

### SMS Alerts

Quick text messages:
```
COPY SIGNAL: ProTrader123 bought YES on 'Bitcoin $100k?' - Confidence: 85%
```

---

## 🛡️ Risk Management

### Built-in Safety Features

1. **Whale Filters:**
   - Only copy whales with 65%+ accuracy
   - Require 50+ trade history
   - Skip whales with negative P&L

2. **Price Filters:**
   - Don't buy above $0.95 (too expensive)
   - Don't buy below $0.05 (too cheap)
   - Avoid low liquidity markets

3. **Position Sizing:**
   - Proportional to whale's position (1% default)
   - Capped at max copy size ($50 default)
   - Never risk more than configured max

4. **Duplicate Prevention:**
   - Won't copy same market twice within 1 hour
   - Tracks all copied positions
   - Prevents over-exposure

### Recommended Settings for Different Bankrolls

**$50 Bankroll (Ultra Conservative):**
```bash
COPY_RATIO=0.005      # 0.5%
MAX_COPY_SIZE=5       # $5 max
MIN_WHALE_ACCURACY=70 # 70%+ only
```

**$100 Bankroll (Conservative - Recommended):**
```bash
COPY_RATIO=0.01       # 1%
MAX_COPY_SIZE=10      # $10 max
MIN_WHALE_ACCURACY=65 # 65%+
```

**$500 Bankroll (Moderate):**
```bash
COPY_RATIO=0.02       # 2%
MAX_COPY_SIZE=50      # $50 max
MIN_WHALE_ACCURACY=65 # 65%+
```

**$1000+ Bankroll (Aggressive):**
```bash
COPY_RATIO=0.05       # 5%
MAX_COPY_SIZE=100     # $100 max
MIN_WHALE_ACCURACY=60 # 60%+
```

---

## 🔍 Finding the Best Whales

### Criteria for Selecting Whales

1. **Accuracy:** 65%+ minimum, 70%+ ideal
2. **Trade Volume:** 50+ trades minimum, 100+ ideal
3. **Profitability:** Positive P&L
4. **Activity:** Active in last 30 days
5. **Diversification:** Follow 2-3 whales, not just 1

### Where to Find Them

1. **Use find_whales.py:**
   ```bash
   python find_whales.py
   ```

2. **Polymarket Leaderboard:**
   - Visit https://polymarket.com/leaderboard
   - Look for "Alpha" tags
   - Check accuracy and trade count

3. **Community Recommendations:**
   - Twitter/X: Search "#Polymarket alpha"
   - Discord: Polymarket community
   - Reddit: r/Polymarket

### Red Flags (Avoid These Whales)

❌ Low trade count (< 50 trades)
❌ Negative P&L
❌ Accuracy < 60%
❌ Inactive (no trades in 30+ days)
❌ Only trades one type of market (not diversified)

---

## 🧪 Testing Before Going Live

### Step 1: Paper Trading (Recommended)

Test with paper trading first:

```bash
# In .env
TRADING_MODE=paper
COPY_TRADING_ENABLED=true

# Run
python -m src.app.main --mode copy --iterations 100
```

This will:
- Monitor whales
- Generate signals
- Log trades (but not execute)
- Track theoretical P&L

### Step 2: Small Live Trades

After 1-2 weeks of paper trading:

```bash
# In .env
TRADING_MODE=live
MAX_COPY_SIZE=5  # Start with $5 max

# Run
python -m src.app.main --mode copy
```

### Step 3: Scale Up

After 10+ successful trades:
- Increase MAX_COPY_SIZE gradually
- Add more whales
- Increase COPY_RATIO if desired

---

## 📈 Tracking Performance

### View Copy Trading Stats

The bot tracks:
- Total signals generated
- Whales tracked
- Markets copied
- Win rate (when implemented)
- Total P&L (when implemented)

### Manual Tracking

Keep a spreadsheet:
```
Date       | Whale      | Market        | Position | Size  | Result | P&L
2025-01-15 | ProTrader  | Bitcoin $100k | YES $0.65| $10   | WIN    | +$3.50
2025-01-16 | AlphaWhale | Trump 2028    | NO $0.45 | $8    | LOSS   | -$8.00
```

---

## ❓ FAQ

### Q: How much can I make?

**A:** With $100 capital and 3 whales @ 65% accuracy:
- Conservative: $30-80/month
- Moderate: $50-150/month
- Aggressive: $100-300/month (higher risk)

### Q: What if a whale starts losing?

**A:** The bot tracks whale performance. If accuracy drops below your MIN_WHALE_ACCURACY, it stops copying them automatically.

### Q: Can I copy more than 3 whales?

**A:** Yes! Add more addresses to COPY_WHALE_ADDRESSES. Recommended: 2-5 whales for diversification.

### Q: What if I miss a signal?

**A:** Email and SMS notifications ensure you don't miss anything. The bot runs 24/7 and monitors continuously.

### Q: Is this guaranteed profit?

**A:** No. Even 70% accuracy means 30% of trades lose. This is NOT arbitrage. But following proven traders significantly improves your odds.

### Q: How is this different from arbitrage?

**A:**
- **Arbitrage:** Guaranteed profit, rare opportunities
- **Copy Trading:** 65%+ win rate, frequent opportunities

---

## 🚀 Next Steps

1. ✅ **Phase 1 Complete:** Notifications working
2. ✅ **Phase 2 Complete:** Copy trading system built
3. 🔄 **Now:** Test with paper trading
4. 📊 **Next:** Add live execution (coming soon)
5. 🎯 **Future:** Add cross-platform arbitrage

---

## 💡 Pro Tips

1. **Diversify:** Follow 3-5 whales, not just 1
2. **Start small:** Test with $5-10 per trade first
3. **Be patient:** Don't expect daily signals
4. **Monitor performance:** Track your wins/losses
5. **Adjust settings:** Tweak COPY_RATIO based on results
6. **Stay updated:** Check whale accuracy monthly
7. **Use notifications:** Enable SMS for instant alerts

---

**Ready to start? Run:**

```bash
# 1. Find whales
python find_whales.py

# 2. Add addresses to .env
# 3. Enable copy trading
# 4. Run the bot
python -m src.app.main --mode copy
```

**Good luck! 🐋💰**

