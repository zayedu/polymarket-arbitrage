# Paper Trading CSV Tracker

## Overview

The bot automatically logs all paper trades to `paper_trades.csv` for easy performance monitoring and capital tracking.

## CSV File Location

When running locally:

```
/path/to/project/paper_trades.csv
```

When running on Railway:

```
/app/paper_trades.csv
```

## CSV Columns

| Column          | Description                             |
| --------------- | --------------------------------------- |
| Timestamp       | ISO 8601 timestamp (UTC)                |
| Date            | YYYY-MM-DD format                       |
| Time            | HH:MM:SS format                         |
| Whale Address   | Ethereum address of the whale           |
| Whale Username  | Username (e.g., @archaic)               |
| Whale Accuracy  | Whale's historical accuracy %           |
| Market ID       | Polymarket market/condition ID          |
| Market Title    | Full market question                    |
| Outcome         | YES or NO                               |
| Entry Price     | Price at entry (0.00-1.00)              |
| Shares          | Number of shares                        |
| Capital         | Total capital allocated ($)             |
| Confidence      | Confidence score (0-100)                |
| Reasons         | Why the trade was taken                 |
| Status          | SIMULATED, SKIPPED, or REJECTED         |
| Resolution Date | When market resolved (empty if pending) |
| Final Price     | Final price at resolution (0 or 1)      |
| PnL             | Profit/Loss in $                        |
| ROI %           | Return on investment %                  |
| Result          | WIN, LOSS, or PENDING                   |

## Automatic Logging

Every time the bot processes a signal, it automatically:

1. **Logs to CSV** - Appends a new row with all trade details
2. **Updates totals** - Tracks total capital allocated
3. **Categorizes by whale** - Groups trades by which whale was copied
4. **Prints summary** - Shows performance stats every 10 iterations

## Viewing on Railway

### Option 1: Railway CLI (Recommended)

Install Railway CLI:

```bash
npm install -g @railway/cli
```

Login and link project:

```bash
railway login
railway link
```

Download the CSV:

```bash
railway run cat paper_trades.csv > paper_trades_local.csv
```

### Option 2: Railway Logs

View recent trades in logs:

```
Railway Dashboard → Deployments → Logs
```

Look for:

```
📝 Logged SIMULATED trade: Market Name - $25.00
```

### Option 3: Add Volume Mount (Advanced)

In Railway dashboard:

1. Go to Settings → Volumes
2. Add volume: `/app/data`
3. Update code to save CSV to `/app/data/paper_trades.csv`
4. Download volume contents via Railway CLI

## Summary Statistics

The bot automatically prints a summary every 10 iterations:

```
============================================================
📊 PAPER TRADING SUMMARY
============================================================

📈 TRADING ACTIVITY:
  Total signals: 45
  Simulated trades: 38
  Skipped (low confidence): 5
  Rejected (risk limits): 2

💰 CAPITAL ALLOCATION:
  Total allocated: $950.00
  Average position: $25.00
  Average confidence: 78.5%

🎯 PERFORMANCE (Resolved Markets):
  Resolved trades: 12
  Wins: 8 | Losses: 4
  Win rate: 66.7%
  Total P&L: $145.50
  Avg P&L per trade: $12.13
  ROI: 15.3%

🐋 WHALE ACTIVITY:
  Most active: @archaic
    • @archaic: 18 trades
    • @Car: 12 trades
    • @nicoco89: 8 trades

📁 CSV File: paper_trades.csv
============================================================
```

## Importing to Google Sheets

1. **Download CSV from Railway** (using Railway CLI)
2. **Open Google Sheets**
3. **File → Import → Upload**
4. **Select `paper_trades.csv`**
5. **Import location: Replace spreadsheet**

Now you have a live spreadsheet with all your trades!

## Tracking Performance

### As Markets Resolve

When a market resolves, you can manually update the CSV:

1. Download latest CSV from Railway
2. Find the trade row by Market ID
3. Update these columns:
   - Resolution Date: `2025-01-15`
   - Final Price: `1.0` (if YES won) or `0.0` (if NO won)
   - Result: `WIN` or `LOSS`
4. Calculate PnL:
   - WIN: `Capital * (1 / Entry Price - 1)`
   - LOSS: `-Capital`
5. Calculate ROI %: `(PnL / Capital) * 100`

### Automated Tracking (Future)

In the future, the bot could automatically:

- Monitor market resolutions
- Update CSV with results
- Calculate P&L automatically
- Send performance reports

## Example CSV Data

```csv
Timestamp,Date,Time,Whale Address,Whale Username,Whale Accuracy,Market ID,Market Title,Outcome,Entry Price,Shares,Capital,Confidence,Reasons,Status,Resolution Date,Final Price,PnL,ROI %,Result
2025-12-29T12:30:45Z,2025-12-29,12:30:45,0x1f0a343513aa6060488fabe96960e6d1e177f7aa,@archaic,74.0,0x123abc...,Will Bitcoin reach $200k by Dec 31 2025?,YES,0.62,40.32,25.00,85.0,Whale accuracy: 74%; Whale trades: 1347; Price: $0.62,SIMULATED,2025-12-31,1.0,15.32,61.3,WIN
2025-12-29T13:15:22Z,2025-12-29,13:15:22,0x7c3db723f1d4d8cb9c550095203b686cb11e5c6b,@Car,72.0,0x456def...,Will Trump win 2024 election?,NO,0.45,55.56,25.00,78.0,Whale accuracy: 72%; Whale trades: 892; Price: $0.45,SIMULATED,,,,,PENDING
2025-12-29T14:00:10Z,2025-12-29,14:00:10,0x1f0a343513aa6060488fabe96960e6d1e177f7aa,@archaic,74.0,0x789ghi...,Will S&P 500 hit 6000 by year end?,YES,0.75,33.33,25.00,65.0,Whale accuracy: 74%; Whale trades: 1347; Price: $0.75,SKIPPED,,,,,
```

## Capital Tracking

The CSV makes it easy to track:

### Daily Capital Allocation

```sql
SELECT Date, SUM(Capital) as Daily_Capital
FROM paper_trades
WHERE Status = 'SIMULATED'
GROUP BY Date
```

### Capital by Whale

```sql
SELECT Whale_Username, SUM(Capital) as Total_Capital, COUNT(*) as Trades
FROM paper_trades
WHERE Status = 'SIMULATED'
GROUP BY Whale_Username
ORDER BY Total_Capital DESC
```

### Win Rate by Confidence Range

```sql
SELECT
  CASE
    WHEN Confidence >= 90 THEN '90-100%'
    WHEN Confidence >= 80 THEN '80-89%'
    WHEN Confidence >= 70 THEN '70-79%'
    ELSE '<70%'
  END as Confidence_Range,
  COUNT(*) as Trades,
  SUM(CASE WHEN Result = 'WIN' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as Win_Rate
FROM paper_trades
WHERE Status = 'SIMULATED' AND Result IN ('WIN', 'LOSS')
GROUP BY Confidence_Range
```

## Benefits

✅ **Automatic logging** - No manual tracking needed
✅ **Easy to analyze** - Import to Excel/Sheets/SQL
✅ **Capital visibility** - See exactly where money is allocated
✅ **Performance tracking** - Calculate win rate, ROI, P&L
✅ **Whale comparison** - See which whales perform best
✅ **Confidence analysis** - Validate confidence scoring
✅ **Historical record** - Complete audit trail

## Tips

1. **Download weekly** - Get fresh CSV from Railway every week
2. **Backup regularly** - Save copies of CSV as you go
3. **Track resolutions** - Update results as markets resolve
4. **Analyze patterns** - Look for trends in winning trades
5. **Adjust strategy** - Use data to optimize confidence threshold

## Next Steps

After 2-4 weeks of paper trading:

1. **Download final CSV**
2. **Calculate overall performance**:
   - Total P&L
   - Win rate
   - ROI
   - Best performing whales
3. **Decide if ready for live trading**
4. **If yes, start with small positions ($5-10)**
5. **Continue tracking in CSV**
