# Quick Start Guide

## What You Need to Do Manually

### 1. Install SendGrid (5 minutes)

```bash
pip install -r requirements.txt  # Installs sendgrid
```

Go to https://signup.sendgrid.com/ and:

- Create free account
- Verify your email
- Create API key (Settings → API Keys)
- Copy the API key

### 2. Configure Environment (2 minutes)

Edit your `.env` file:

```bash
# Paper Trading Settings
TRADING_MODE=paper
POLL_INTERVAL_SECONDS=2
MIN_GROSS_EDGE=0.005
MIN_NET_PROFIT=0.05
MIN_APY=25
MAX_DAYS_TO_RESOLUTION=7

# Email Notifications
ENABLE_NOTIFICATIONS=true
SENDGRID_API_KEY=SG.your_key_here
NOTIFICATION_EMAIL_FROM=bot@yourdomain.com
NOTIFICATION_EMAIL_TO=your@email.com
```

### 3. Run Paper Trading (24-48 hours)

```bash
# Activate venv
source venv/bin/activate

# Run in background
python -m src.app.main --mode paper --iterations 0 > paper.log 2>&1 &

# Save process ID
echo $! > bot.pid

# Watch logs
tail -f paper.log

# To stop later:
kill $(cat bot.pid)
```

**What to expect:**

- Bot scans markets every 2 seconds
- Logs opportunities to `paper_trades.csv`
- Shows simulated PnL
- Runs for 24-48 hours to validate

### 4. Deploy to Cloud (After validation)

**Option A: Railway.app ($5/month - easiest)**

```bash
# Install CLI
npm install -g @railway/cli

# Deploy
railway login
railway init
railway variables set TRADING_MODE=scan
railway variables set ENABLE_NOTIFICATIONS=true
railway variables set SENDGRID_API_KEY=your_key
railway variables set NOTIFICATION_EMAIL_TO=your@email.com
railway up
```

**Option B: Fly.io (Free)**

```bash
# Install CLI
curl -L https://fly.io/install.sh | sh

# Deploy
fly auth login
fly launch --no-deploy
fly secrets set SENDGRID_API_KEY=your_key
fly secrets set NOTIFICATION_EMAIL_TO=your@email.com
fly deploy
```

### 5. Monitor (48+ hours)

After deploying:

- Check logs: `railway logs` or `fly logs`
- Wait for email alerts when opportunities found
- Monitor for crashes
- Adjust thresholds if needed

## That's It!

**Timeline:**

- Day 1: Setup + start paper trading (30 min)
- Day 2-3: Let it run, check occasionally
- Day 4: Review results, deploy to cloud (1 hour)
- Day 5+: Monitor production

**Cost:**

- SendGrid: Free (100 emails/day)
- Railway: $5/month OR Fly.io: Free
- **Total: $0-5/month**

## Troubleshooting

**No opportunities found?**

- Lower thresholds: `MIN_GROSS_EDGE=0.001`, `MIN_APY=10`

**No emails?**

- Check spam folder
- Verify SendGrid API key
- Test: Set `MIN_GROSS_EDGE=0.001` to trigger alerts

**Bot crashes?**

- Check logs: `tail -100 paper.log`
- Verify all env vars are set
- Make sure venv is activated

