# 📁 Project Structure

```
predictions_market_arbitrage/
│
├── 📄 README.md              # Main documentation
├── 📄 requirements.txt       # Python dependencies
├── 📄 env.template           # Environment variables template
├── 📄 config.py              # Configuration management
│
├── 📂 src/                   # Source code
│   ├── app/                  # Main application
│   │   └── main.py          # Entry point
│   ├── core/                 # Core functionality
│   │   ├── models.py        # Data models
│   │   ├── scanner.py       # Market scanner
│   │   ├── storage.py       # Database
│   │   ├── notifier.py      # Email notifications
│   │   └── ...
│   ├── polymarket/           # Polymarket API clients
│   │   ├── gamma.py         # Market data API
│   │   └── clob.py          # Order book API
│   └── ml/                   # Copy trading logic
│       ├── whale_tracker.py # Track high-performers
│       └── copy_trader.py   # Generate signals
│
├── 📂 scripts/               # Helper scripts
│   ├── start_bot.sh         # Start bot (watch live)
│   ├── run_background.sh    # Run 24/7 in background
│   └── stop_bot.sh          # Stop the bot
│
├── 📂 docs/                  # Documentation
│   ├── QUICKSTART.md        # Quick start guide
│   ├── FINAL_SETUP.md       # Complete setup
│   └── ...
│
├── 📂 deploy/                # Deployment configs
│   ├── Dockerfile           # Docker image
│   ├── fly.toml             # Fly.io config
│   └── railway.toml         # Railway config
│
└── 📂 tests/                 # Unit tests
    └── test_*.py
```

## 🚀 Quick Commands

```bash
# Start bot (watch live)
./scripts/start_bot.sh

# Run in background
./scripts/run_background.sh

# Stop bot
./scripts/stop_bot.sh

# Run tests
pytest
```

## 📝 Key Files

- **`config.py`** - All configuration settings
- **`src/app/main.py`** - Main entry point
- **`src/ml/whale_tracker.py`** - Tracks @ilovecircle's positions
- **`src/core/notifier.py`** - Sends email alerts

## 🔧 Configuration

All settings in `.env` (copy from `env.template`)

## 📚 Documentation

See `docs/` folder for detailed guides.


