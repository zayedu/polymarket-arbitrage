# 💬 Discord Notifications Setup (100% FREE!)

## 🎯 Get Free Instant Notifications on Discord

Discord notifications are **completely free** with unlimited messages! Perfect for getting instant alerts when @ilovecircle makes a trade.

---

## 📋 Setup Steps (2 minutes)

### 1. Create a Discord Server (if you don't have one)

1. Open Discord
2. Click the `+` button on the left sidebar
3. Select "Create My Own"
4. Name it "Trading Alerts" or whatever you want

### 2. Create a Webhook

1. Right-click on any text channel (e.g., #general)
2. Click "Edit Channel"
3. Go to "Integrations" tab
4. Click "Create Webhook" or "New Webhook"
5. Name it "Polymarket Bot"
6. Click "Copy Webhook URL"

**Your webhook URL will look like:**
```
https://discord.com/api/webhooks/123456789/abcdefghijklmnopqrstuvwxyz
```

### 3. Add to Your `.env` File

Open your `.env` file and add:

```bash
# Discord Notifications (100% FREE!)
DISCORD_ENABLED=true
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_URL_HERE
```

### 4. Restart the Bot

```bash
./scripts/stop_bot.sh
./scripts/run_background.sh
```

---

## ✅ What You'll Get

When @ilovecircle opens a new position, you'll get a Discord message with:

```
🚨 COPY TRADE ALERT 🚨

🐋 3 Copy Trade Signals from @ilovecircle!
Accuracy: 74.0%
New Positions: 3

#1: Will Bitcoin reach $200,000 by December 31, 2025?
❌ NO
💰 Entry: $0.9509
📊 Current: $0.9995
🎯 Confidence: 70%
💵 Size: $50.00

#2: Will Bitcoin reach $250,000 by December 31, 2025?
...
```

---

## 📱 Mobile Notifications

1. Install Discord app on your phone
2. Enable push notifications for the server
3. You'll get instant alerts on your phone!

---

## 🆓 Why Discord?

- ✅ **100% Free** - No limits, no credit card
- ✅ **Instant** - Notifications arrive in <1 second
- ✅ **Mobile** - Works on iOS and Android
- ✅ **Rich Formatting** - Beautiful embeds with colors and emojis
- ✅ **Reliable** - Discord never blocks webhooks

---

## 🔧 Troubleshooting

**Not receiving messages?**
1. Make sure `DISCORD_ENABLED=true` in your `.env`
2. Check that your webhook URL is correct
3. Make sure the bot is running: `tail -f copy_trading.log`
4. Look for "💬 Sent Discord notification" in the logs

**Want to test it?**
```bash
python3 -m src.app.main --test-notifications
```

---

## 🎉 You're All Set!

Your Discord will now get instant notifications whenever @ilovecircle makes a trade! 🐋💰

