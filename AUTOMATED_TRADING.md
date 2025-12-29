# Automated Trading System

## Overview

The automated trading system enables hands-free execution of copy trading signals based on confidence scores, position sizing strategies, and comprehensive risk management.

## Features

### 1. **Confidence-Based Filtering**
- Only executes trades that meet a minimum confidence threshold
- Confidence score (0-100) calculated from:
  - Whale accuracy (40 points max)
  - Trade history (20 points max)
  - Profitability (20 points max)
  - Market liquidity (20 points max)

### 2. **Intelligent Position Sizing**
Three position sizing modes:
- **confidence_scaled** (recommended): Scales position size by confidence
  - 100% confidence = 1.0x base size
  - 80% confidence = 0.8x base size
  - 70% confidence = 0.7x base size
- **whale_ratio**: Fixed percentage of whale's position (e.g., 1%)
- **fixed**: Fixed dollar amount per trade

### 3. **Risk Management**
Automated checks before every trade:
- Maximum position size limit
- Minimum position size limit
- Daily loss limit
- Maximum open positions
- No double-down (one position per market)

### 4. **Safety Features**
- **Paper Mode**: Simulates trades without real execution
- **Kill Switch**: Stops trading after 3 consecutive failures
- **Cooldown**: 1-hour pause after losses
- **Duplicate Prevention**: Won't execute same market within 1 hour

## Configuration

Add these settings to your `.env` file:

```bash
# Automated Trading
AUTO_TRADING_ENABLED=false          # Set to true to enable
MIN_CONFIDENCE_SCORE=70             # Only execute 70%+ confidence trades
MAX_OPEN_POSITIONS=10               # Max concurrent positions
MIN_POSITION_SIZE=5                 # Minimum $5 per trade
POSITION_SIZING_MODE=confidence_scaled  # Recommended

# Existing Copy Trading Settings
COPY_TRADING_ENABLED=true
COPY_WHALE_ADDRESSES=0x1f0a343513aa6060488fabe96960e6d1e177f7aa,0x7c3db723f1d4d8cb9c550095203b686cb11e5c6b,0x7ac83882979ccb5665cea83cb269e558b55077cd,0xc4086b708cd3a50880b7069add1a1a80000f4675,0x43372356634781eea88d61bbdd7824cdce958882
COPY_RATIO=0.01                     # Copy 1% of whale's position
MAX_COPY_SIZE=50                    # Max $50 per trade
```

## Testing

### Run Test Suite

```bash
python3 test_auto_trading.py
```

This validates:
1. ✅ Confidence threshold filtering
2. ✅ Position sizing with confidence scaling
3. ✅ Risk management limits
4. ✅ Paper trading mode

### Expected Output

```
============================================================
AUTOMATED TRADING SYSTEM - TEST SUITE
============================================================

Configuration:
  Trading mode: paper
  Auto-trading enabled: True
  Min confidence: 70%
  Position sizing: confidence_scaled
  Max position: $50
  Min position: $5

TEST 1: Confidence Threshold Filtering
✅ Confidence 90%: SIMULATED - Should execute (high confidence)
✅ Confidence 65%: SKIPPED - Should skip (below threshold)

TEST 2: Position Sizing with Confidence Scaling
Confidence 100%:
  → Position size: 9.62 shares
  → Capital required: $5.00
  → Scaling factor: 1.00x

TEST 3: Risk Management Limits
✅ Normal position ($25): SIMULATED - Should execute
✅ Too large ($100): REJECTED - Should reject
✅ Too small ($2): REJECTED - Should reject

TEST 4: Paper Trading Mode
✅ Paper mode working correctly - trade simulated, not executed

✅ ALL TESTS COMPLETED SUCCESSFULLY
```

## Usage

### Step 1: Test in Paper Mode

Keep `TRADING_MODE=paper` and `AUTO_TRADING_ENABLED=true`:

```bash
python -m src.app.main --mode copy
```

You'll see:
```
📝 [PAPER MODE] Would execute: YES on 'Market Name' @ $0.62 for $25.00 (confidence: 85%)
```

### Step 2: Monitor Paper Trading

Run for 1-2 weeks in paper mode to validate:
- Confidence scores are reasonable
- Position sizes are appropriate
- Risk limits are working
- No false positives

### Step 3: Go Live (When Ready)

Only after thorough paper trading validation:

```bash
# In .env
TRADING_MODE=live
AUTO_TRADING_ENABLED=true
MIN_CONFIDENCE_SCORE=75  # Start conservative
MAX_COPY_SIZE=10         # Start small
```

## Confidence Score Examples

### High Confidence Trade (90%)
- Whale: 85% accuracy (34 points)
- Trade history: 1500 trades (20 points)
- Profitability: $8000 profit (20 points)
- Market liquidity: $100k volume (20 points)
- **Total: 94 points → EXECUTE**

### Medium Confidence Trade (72%)
- Whale: 75% accuracy (30 points)
- Trade history: 800 trades (16 points)
- Profitability: $2000 profit (8 points)
- Market liquidity: $50k volume (18 points)
- **Total: 72 points → EXECUTE**

### Low Confidence Trade (55%)
- Whale: 70% accuracy (28 points)
- Trade history: 200 trades (4 points)
- Profitability: $500 profit (2 points)
- Market liquidity: $5k volume (1 point)
- **Total: 35 points → SKIP**

## Position Sizing Examples

With `COPY_RATIO=0.01` (1%) and `confidence_scaled` mode:

### Whale buys 10,000 shares @ $0.50 = $5,000
- Base copy size: $5,000 × 0.01 = $50
- 100% confidence: $50 × 1.0 = **$50**
- 80% confidence: $50 × 0.8 = **$40**
- 70% confidence: $50 × 0.7 = **$35**
- 60% confidence: $50 × 0.6 = **$30**

### Whale buys 1,000 shares @ $0.60 = $600
- Base copy size: $600 × 0.01 = $6
- 100% confidence: $6 × 1.0 = **$6**
- 80% confidence: $6 × 0.8 = **$5** (capped at MIN_POSITION_SIZE)
- 70% confidence: $6 × 0.7 = **$5** (capped at MIN_POSITION_SIZE)

## Risk Management in Action

### Scenario 1: Normal Trade
- Confidence: 85%
- Position: $30
- Open positions: 5/10
- Daily PnL: -$2
- **Result: ✅ EXECUTE**

### Scenario 2: Position Too Large
- Confidence: 90%
- Position: $75
- Max allowed: $50
- **Result: 🚫 REJECTED**

### Scenario 3: Daily Loss Limit Hit
- Confidence: 95%
- Position: $20
- Daily PnL: -$12 (limit: -$10)
- **Result: 🚫 REJECTED**

### Scenario 4: Already Have Position
- Confidence: 88%
- Position: $25
- Existing position in same market: YES
- **Result: 🚫 REJECTED (no double-down)**

## Monitoring

### Check Executor Status

```python
from src.core.auto_executor import AutoExecutor

status = executor.get_status()
print(status)
# {
#   "enabled": True,
#   "trading_mode": "paper",
#   "consecutive_failures": 0,
#   "in_cooldown": False,
#   "executed_trades_count": 15
# }
```

### Reset Kill Switch

If the kill switch activates (3+ consecutive failures):

```python
executor.reset_kill_switch()
# 🔄 Kill switch reset - trading resumed
```

## Logs

Watch for these key messages:

### Execution
```
🚀 Executing copy trade: YES on 'Market Name' @ $0.62 for $25.00 (confidence: 85%)
✅ Order placed: order_123 - 40.32 shares @ $0.6200
```

### Filtering
```
⏭️  Skipping trade - confidence 65% < 70%
🚫 Trade rejected: Position too large: $75.00 > $50.00
```

### Safety
```
⏸️  In cooldown after loss. 45 minutes remaining
🛑 KILL SWITCH ACTIVATED: 3 consecutive failures. Manual intervention required.
```

## Best Practices

1. **Start Conservative**
   - `MIN_CONFIDENCE_SCORE=75` (higher threshold)
   - `MAX_COPY_SIZE=10` (smaller positions)
   - Paper trade for 2+ weeks

2. **Monitor Closely**
   - Check Discord notifications daily
   - Review execution logs
   - Track win rate and PnL

3. **Adjust Gradually**
   - Lower confidence threshold slowly (75 → 70 → 65)
   - Increase position sizes incrementally
   - Add more whale addresses one at a time

4. **Risk Management**
   - Never risk more than you can afford to lose
   - Keep `MAX_DAILY_LOSS` conservative
   - Limit `MAX_OPEN_POSITIONS` to 5-10

5. **Emergency Stop**
   - Set `AUTO_TRADING_ENABLED=false` to stop immediately
   - Bot will continue monitoring but won't execute

## Troubleshooting

### No Trades Executing

Check:
1. `AUTO_TRADING_ENABLED=true`?
2. Confidence scores meeting threshold?
3. Position sizes within limits?
4. Kill switch activated?

### Too Many Trades

Adjust:
1. Increase `MIN_CONFIDENCE_SCORE` (e.g., 70 → 80)
2. Decrease `MAX_OPEN_POSITIONS` (e.g., 10 → 5)
3. Reduce `MAX_COPY_SIZE` (e.g., $50 → $25)

### Trades Rejected

Common reasons:
- Confidence below threshold
- Position size too large/small
- Daily loss limit hit
- Already have position in market
- Max open positions reached

## Advanced Configuration

### Custom Confidence Weights

Edit `src/ml/copy_trader.py` → `calculate_confidence()`:

```python
# Default weights
accuracy_score = (whale.accuracy / 100) * 40  # 40% weight
trade_score = min(20, (whale.total_trades / 100) * 20)  # 20% weight
pnl_score = min(20, (whale.profit_loss / 1000) * 20)  # 20% weight
liquidity_score = min(20, (market.volume / 10000) * 20)  # 20% weight

# Custom: Prioritize accuracy more
accuracy_score = (whale.accuracy / 100) * 60  # 60% weight
trade_score = min(15, (whale.total_trades / 100) * 15)  # 15% weight
pnl_score = min(15, (whale.profit_loss / 1000) * 15)  # 15% weight
liquidity_score = min(10, (market.volume / 10000) * 10)  # 10% weight
```

### Dynamic Position Sizing

Edit `src/ml/copy_trader.py` → `calculate_copy_size()`:

```python
# Example: Scale more aggressively with confidence
if confidence_score >= 90:
    confidence_multiplier = Decimal("1.5")  # 1.5x for high confidence
elif confidence_score >= 80:
    confidence_multiplier = Decimal("1.2")  # 1.2x for good confidence
else:
    confidence_multiplier = confidence_score / Decimal("100")
```

## Support

For issues or questions:
1. Check logs in terminal output
2. Run `python3 test_auto_trading.py` to validate setup
3. Review Discord notifications for execution details
4. Check `arbitrage.db` for historical trades

## Safety Disclaimer

⚠️ **IMPORTANT**: This system executes real trades with real money when `TRADING_MODE=live`. 

- Start with paper trading
- Test thoroughly before going live
- Use small position sizes initially
- Monitor closely, especially first few days
- Never invest more than you can afford to lose
- Past performance doesn't guarantee future results

The automated trading system is a tool to assist decision-making, not a guarantee of profits.

