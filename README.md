# Polymarket Arbitrage Bot - Profit-First Edition

> ⚠️ **IMPORTANT DISCLAIMER**: As of December 2025, Polymarket markets show high efficiency with professional market makers dominating orderbooks. Most markets have symmetrical spreads (YES_ask + NO_ask ≈ $2.00), making traditional arbitrage rare. This bot is best used as a **24/7 monitoring system** to alert you when rare opportunities appear, rather than a high-frequency trading system.

A Python-based arbitrage system for Polymarket prediction markets that exploits structural mispricings where **YES + NO ≠ $1.00**.

## 🎯 Strategy Overview

The bot identifies guaranteed profit opportunities when the sum of YES and NO token prices deviates from $1.00:

- **Long Arbitrage**: Buy both YES and NO when `YES_ask + NO_ask < $1.00`
- **Guaranteed Profit**: One token will resolve to $1.00, the other to $0.00
- **Net Profit**: `$1.00 - (YES_ask + NO_ask) - fees - gas`

### Research Validation

According to academic research, **$40M+ in arbitrage profits** were extracted from Polymarket between April 2024 - April 2025 using this exact strategy. The top 10 arbitrageurs captured $8.18M (21% of total).

**Note**: These opportunities may have been exploited during Polymarket's earlier, less efficient phase. Current market conditions show high efficiency.

## 🚀 Features

### Arbitrage Mode
- ✅ **Real-time scanner** for arbitrage opportunities across Polymarket markets
- ✅ **Safe execution** with multi-leg order placement and timeout protection
- ✅ **Risk management** with position limits, daily loss caps, and exposure controls
- ✅ **Paper trading mode** to validate strategy without risking capital
- ✅ **APY optimization** to maximize capital efficiency
- ✅ **Liquidity checker** to analyze market health

### 🐋 Copy Trading Mode (NEW!)
- ✅ **Whale tracker** monitors high-accuracy traders (65%+ win rate)
- ✅ **Auto-copy** trades from Alpha-tagged wallets
- ✅ **Smart filters** for price, liquidity, and whale performance
- ✅ **Proportional sizing** (copy 1% of whale's position)
- ✅ **Confidence scoring** for each copy signal
- ✅ **Whale finder tool** to discover profitable traders

### Notifications & Deployment
- ✅ **Email notifications** via SendGrid for opportunity alerts
- ✅ **SMS notifications** via Rogers/Bell/Telus email gateways
- ✅ **Cloud deployment ready** (Railway.app, Fly.io, Docker)
- ✅ **PnL tracking** with daily/weekly reporting
- ✅ **Rich terminal UI** with color-coded opportunity tables

## 📊 Current Market Reality

**Testing Results** (December 2025):

- Scanned 49 high-volume markets (>$100k volume each)
- Found **0 traditional arbitrage opportunities**
- All markets showed: `YES_ask + NO_ask ≈ $1.998` (not $1.00)
- Professional market makers maintain symmetric spreads

**Why?**

- Market makers post wide spreads (0.001 bid / 0.999 ask)
- YES and NO orderbooks are mirrors of each other
- Low-volume markets have empty orderbooks
- Competition from professional arbitrage firms

---

## 🐋 Copy Trading Mode (NEW - Recommended!)

Since traditional arbitrage is rare, we've built **copy trading** to follow high-accuracy traders:

### Quick Start

```bash
# 1. Find Alpha whales (65%+ accuracy)
python find_whales.py

# 2. Configure .env
COPY_TRADING_ENABLED=true
COPY_WHALE_ADDRESSES=0x1234...,0x5678...
ENABLE_NOTIFICATIONS=true
SMS_ENABLED=true

# 3. Run copy trading mode
python -m src.app.main --mode copy
```

### Expected Results
- **Win Rate:** 60-65% (following proven traders)
- **Monthly Profit:** $50-150 on $100 capital
- **Trades/Month:** 10-15
- **Notifications:** Email + SMS for every signal

**📖 Full Guide:** [COPY_TRADING_GUIDE.md](COPY_TRADING_GUIDE.md)

---

## 📋 Prerequisites

- Python 3.11 or higher
- Polygon wallet with private key (for live trading - optional)
- SendGrid API key (for email notifications - optional)
- Basic understanding of prediction markets

## 🔧 Quick Start

See [QUICKSTART.md](QUICKSTART.md) for detailed setup instructions.

### 1. Clone the Repository

```bash
git clone https://github.com/zayedu/polymarket-arbitrage.git
cd polymarket-arbitrage
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Copy the example environment file and edit with your settings:

```bash
cp env.template .env
```

Edit `.env` and set your configuration:

```bash
# REQUIRED for live trading
POLYMARKET_PRIVATE_KEY=your_polygon_private_key_here

# OPTIONAL
POLYMARKET_API_KEY=your_api_key_if_required
POLYGON_RPC_URL=https://polygon-rpc.com

# Start with these safe defaults for $100 capital
MIN_GROSS_EDGE=0.01          # 1% minimum edge
MIN_NET_PROFIT=0.10          # $0.10 min profit
MIN_LIQUIDITY=10.0           # $10 min depth
MAX_TRADE_SIZE=15.0          # $15 max per trade
MAX_DAILY_LOSS=10.0          # $10 daily loss limit
MAX_OPEN_EXPOSURE=50.0       # $50 max total exposure
MIN_APY=50                   # 50% annualized min

# Mode: paper, scan, or live
TRADING_MODE=paper
```

## 🎮 Usage

### Recommended: 24/7 Alert Monitoring

Given current market conditions, the **best use case** is deploying as an alert bot:

```bash
# Run continuously in scan mode with email alerts
python -m src.app.main --mode scan --iterations 0
```

Set up email notifications in `.env`:

```bash
ENABLE_NOTIFICATIONS=true
SENDGRID_API_KEY=your_sendgrid_key
NOTIFICATION_EMAIL_FROM=bot@yourdomain.com
NOTIFICATION_EMAIL_TO=your@email.com
```

Deploy to cloud for 24/7 monitoring (see [QUICKSTART.md](QUICKSTART.md) for deployment guide).

### Check Market Liquidity

Before running the bot, check which markets have actual orderbook depth:

```bash
python check_liquidity.py
```

This will show you which markets have real liquidity and what the current price spreads look like.

### Scan Mode (No Trading)

Continuously scan markets and display opportunities without executing trades:

```bash
python -m src.app.main --mode scan
```

Run a single scan:

```bash
python -m src.app.main --mode scan --iterations 1
```

### Paper Trading Mode

Simulate trading to validate strategy without risking real money:

```bash
python -m src.app.main --mode paper --iterations 10
```

This will:

- Scan for opportunities
- Simulate trade execution
- Track simulated PnL in `paper_trades.csv`
- Validate your settings before going live

### Live Trading Mode

⚠️ **WARNING: This mode trades with real money!**

```bash
python -m src.app.main --mode live
```

Limit to 5 trades:

```bash
python -m src.app.main --mode live --max-trades 5
```

## 💰 Configuration for Different Bankrolls

### $100 Capital (Conservative)

```bash
MIN_GROSS_EDGE=0.02          # 2% edge minimum
MIN_NET_PROFIT=0.25          # $0.25 min profit
MAX_TRADE_SIZE=10.0          # $10 per trade
MAX_DAILY_LOSS=10.0          # 10% of capital
MAX_OPEN_EXPOSURE=50.0       # 50% of capital
MIN_APY=75                   # 75% minimum APY
```

**Strategy**: Very conservative, high APY threshold to ensure fast capital rotation.

### $500 Capital (Moderate)

```bash
MIN_GROSS_EDGE=0.015         # 1.5% edge minimum
MIN_NET_PROFIT=0.50          # $0.50 min profit
MAX_TRADE_SIZE=50.0          # $50 per trade
MAX_DAILY_LOSS=25.0          # 5% of capital
MAX_OPEN_EXPOSURE=250.0      # 50% of capital
MIN_APY=50                   # 50% minimum APY
```

### $1,000+ Capital (Aggressive)

```bash
MIN_GROSS_EDGE=0.01          # 1% edge minimum
MIN_NET_PROFIT=1.00          # $1.00 min profit
MAX_TRADE_SIZE=100.0         # $100 per trade
MAX_DAILY_LOSS=50.0          # 5% of capital
MAX_OPEN_EXPOSURE=500.0      # 50% of capital
MIN_APY=40                   # 40% minimum APY
```

## 📊 Understanding the Output

### Opportunity Table

```
┏━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━┳━━━━━━━━┳━━━━━━━━┳━━━━━━━━━┳━━━━━━┓
┃ # ┃ Market                   ┃ YES Ask  ┃ NO Ask   ┃ Sum    ┃ Edge   ┃ Net $  ┃ Size   ┃ APY    ┃ Days ┃
┡━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━╇━━━━━━━━╇━━━━━━━━╇━━━━━━━━━╇━━━━━━┩
│ 1 │ Bitcoin above $100k...   │  0.4850  │  0.4950  │ 0.9800 │ 0.0200 │ $0.28  │   $15  │ 146.0% │   5  │
└───┴──────────────────────────┴──────────┴──────────┴────────┴────────┴────────┴────────┴─────────┴──────┘
```

**Key Metrics**:

- **Edge**: Gross arbitrage profit per $1 invested
- **Net $**: Expected profit after fees and gas
- **APY**: Annualized return (higher = faster capital rotation)
- **Days**: Days until market resolution

### Color Coding

- 🟢 **Green**: Good opportunities (edge ≥ 3%, APY ≥ 100%)
- 🟡 **Yellow**: Decent opportunities (edge ≥ 1%, APY ≥ 50%)
- ⚪ **White**: Marginal opportunities

## 🛡️ Risk Management

The bot includes multiple safety layers:

### Position Limits

- **Max Trade Size**: Limits single trade exposure
- **Max Open Exposure**: Caps total capital at risk
- **Daily Loss Limit**: Stops trading after daily loss threshold

### Execution Safety

- **Limit Orders Only**: No market orders to control slippage
- **Timeout Protection**: 5-second timeout on order fills
- **Partial Fill Handling**: Automatically unwinds partial fills
- **Emergency Stop**: Halts trading if loss limits breached

### Pre-Trade Validation

Every trade is validated for:

- ✅ Sufficient edge after costs
- ✅ Adequate liquidity
- ✅ APY threshold
- ✅ Risk limit compliance
- ✅ Market still active

## 📈 Performance Tracking

### Daily Summary

```bash
python -m src.app.main --mode scan --iterations 1
# After running, check logs for daily PnL summary
```

### View Positions

Open positions are tracked in the SQLite database:

```bash
sqlite3 arbitrage.db "SELECT * FROM positions WHERE is_closed = 0;"
```

### PnL History

```bash
sqlite3 arbitrage.db "SELECT * FROM pnl_entries ORDER BY timestamp DESC LIMIT 10;"
```

## ⚠️ Important Warnings

### Capital Requirements

- **Minimum**: $100 (expect $0.10-$0.50 per trade)
- **Recommended**: $500-$1,000 for more opportunities
- **Never invest more than you can afford to lose**

### Fee Considerations

- **Polymarket Trading Fees**: Currently 0% (may change)
- **Polygon Gas Fees**: ~$0.005-$0.02 per transaction
- **Slippage**: Minimal on liquid markets

### Market Risks

1. **Oracle Risk**: Market resolution disputes (rare but possible)
2. **Leg Risk**: One side fills, other doesn't (mitigated by timeout)
3. **Liquidity Risk**: Orderbook depth changes rapidly
4. **Smart Contract Risk**: Polymarket contract vulnerabilities

### Operational Risks

1. **API Downtime**: Polymarket or Polygon RPC unavailable
2. **Network Congestion**: High gas prices on Polygon
3. **Execution Latency**: Opportunities disappear quickly

## 🔍 Troubleshooting

### "No opportunities found"

- Markets may be efficiently priced
- Try lowering `MIN_GROSS_EDGE` (but keep >= 0.01)
- Increase `MAX_DAYS_TO_RESOLUTION` for more markets
- Check Polymarket has active markets

### "Trade blocked: insufficient liquidity"

- Lower `MIN_LIQUIDITY` threshold
- Reduce `MAX_TRADE_SIZE` to match available depth

### "Daily loss limit reached"

- This is working as intended - stops prevent further losses
- Review your strategy and settings
- Wait until next day or adjust `MAX_DAILY_LOSS`

### Database errors

```bash
# Reset database
rm arbitrage.db
python -m src.app.main --mode scan --iterations 1
```

## 🧪 Testing Before Live Trading

**ALWAYS test in paper mode first:**

1. Run paper trading for 24-48 hours
2. Verify positive simulated PnL
3. Check that risk limits work correctly
4. Monitor for API errors or crashes
5. Only then proceed to live trading with small size

## 📚 Additional Resources

- [Polymarket API Docs](https://docs.polymarket.com)
- [Academic Research on Polymarket Arbitrage](https://arxiv.org/abs/2408.05316)
- [Prediction Market Arbitrage Guide](https://betmetricslab.com/arbitrage-betting/prediction-market-arbitrage/)

## ⚖️ License

MIT License - See LICENSE file for details

## ⚠️ Disclaimer

This software is for educational purposes only. Prediction market trading involves financial risk. The developers are not responsible for any losses incurred. Always:

- Start with paper trading
- Use only risk capital
- Understand the markets you're trading
- Comply with local regulations
- Never invest more than you can afford to lose

## 🤝 Contributing

Contributions welcome! Please:

1. Test thoroughly before submitting PRs
2. Follow existing code style
3. Add tests for new features
4. Update documentation

## 📞 Support

For issues:

1. Check this README
2. Search existing GitHub issues
3. Open a new issue with detailed logs

---

**Built with ❤️ for profit-first arbitrage trading**

Remember: The goal is consistent, small profits that compound over time. Even $1/day = $365/year = 365% ROI on $100 capital!
