"""
Paper Trading Tracker - Automatically logs all simulated trades to CSV.
Tracks performance, capital allocation, and generates summary reports.
"""
import csv
import logging
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, asdict

from ..ml.copy_trader import CopyTradeSignal

logger = logging.getLogger(__name__)


@dataclass
class PaperTrade:
    """Record of a paper trade."""
    timestamp: str
    date: str
    time: str
    whale_address: str
    whale_username: str
    whale_accuracy: float
    market_id: str
    market_title: str
    outcome: str
    entry_price: float
    shares: float
    capital: float
    confidence: float
    reasons: str
    status: str  # "SIMULATED", "SKIPPED", "REJECTED"
    
    # Performance tracking (filled in later when market resolves)
    resolution_date: str = ""
    final_price: float = 0.0
    pnl: float = 0.0
    roi_percent: float = 0.0
    result: str = ""  # "WIN", "LOSS", "PENDING"


class PaperTradingTracker:
    """
    Tracks all paper trades and maintains a CSV log.
    Provides easy performance monitoring and capital tracking.
    """
    
    def __init__(self, csv_file: str = "paper_trades.csv"):
        """
        Initialize paper trading tracker.
        
        Args:
            csv_file: Path to CSV file for logging trades
        """
        self.csv_file = Path(csv_file)
        self.trades: List[PaperTrade] = []
        self.total_capital_allocated = Decimal("0")
        self.total_trades = 0
        self.trades_by_whale = {}
        
        # Initialize CSV file with headers if it doesn't exist
        self._initialize_csv()
        
        # Load existing trades
        self._load_trades()
        
        logger.info(f"📊 Paper Trading Tracker initialized (file: {self.csv_file})")
    
    def _initialize_csv(self):
        """Create CSV file with headers if it doesn't exist."""
        if not self.csv_file.exists():
            with open(self.csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Timestamp',
                    'Date',
                    'Time',
                    'Whale Address',
                    'Whale Username',
                    'Whale Accuracy',
                    'Market ID',
                    'Market Title',
                    'Outcome',
                    'Entry Price',
                    'Shares',
                    'Capital',
                    'Confidence',
                    'Reasons',
                    'Status',
                    'Resolution Date',
                    'Final Price',
                    'PnL',
                    'ROI %',
                    'Result'
                ])
            logger.info(f"✅ Created paper trades CSV: {self.csv_file}")
    
    def _load_trades(self):
        """Load existing trades from CSV."""
        if not self.csv_file.exists():
            return
        
        try:
            with open(self.csv_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    trade = PaperTrade(
                        timestamp=row['Timestamp'],
                        date=row['Date'],
                        time=row['Time'],
                        whale_address=row['Whale Address'],
                        whale_username=row['Whale Username'],
                        whale_accuracy=float(row['Whale Accuracy']),
                        market_id=row['Market ID'],
                        market_title=row['Market Title'],
                        outcome=row['Outcome'],
                        entry_price=float(row['Entry Price']),
                        shares=float(row['Shares']),
                        capital=float(row['Capital']),
                        confidence=float(row['Confidence']),
                        reasons=row['Reasons'],
                        status=row['Status'],
                        resolution_date=row.get('Resolution Date', ''),
                        final_price=float(row.get('Final Price', 0)),
                        pnl=float(row.get('PnL', 0)),
                        roi_percent=float(row.get('ROI %', 0)),
                        result=row.get('Result', 'PENDING')
                    )
                    self.trades.append(trade)
                    
                    if trade.status == "SIMULATED":
                        self.total_capital_allocated += Decimal(str(trade.capital))
                        self.total_trades += 1
                        
                        # Track by whale
                        whale = trade.whale_username or trade.whale_address[:8]
                        if whale not in self.trades_by_whale:
                            self.trades_by_whale[whale] = []
                        self.trades_by_whale[whale].append(trade)
            
            logger.info(f"📂 Loaded {len(self.trades)} existing trades from CSV")
        except Exception as e:
            logger.warning(f"Could not load existing trades: {e}")
    
    def log_trade(
        self,
        signal: CopyTradeSignal,
        status: str,
        execution_result: Optional[str] = None
    ):
        """
        Log a paper trade to CSV.
        
        Args:
            signal: Copy trade signal
            status: "SIMULATED", "SKIPPED", or "REJECTED"
            execution_result: Optional execution result message
        """
        now = datetime.now(timezone.utc)
        
        trade = PaperTrade(
            timestamp=now.isoformat(),
            date=now.strftime('%Y-%m-%d'),
            time=now.strftime('%H:%M:%S'),
            whale_address=signal.whale_address,
            whale_username=signal.whale_username or "Unknown",
            whale_accuracy=float(signal.whale_accuracy),
            market_id=signal.market_id,
            market_title=signal.market_title,
            outcome=signal.outcome,
            entry_price=float(signal.current_price),
            shares=float(signal.recommended_shares),
            capital=float(signal.recommended_capital),
            confidence=float(signal.confidence_score),
            reasons="; ".join(signal.reasons[:3]),  # First 3 reasons
            status=status
        )
        
        # Update tracking
        if status == "SIMULATED":
            self.total_capital_allocated += signal.recommended_capital
            self.total_trades += 1
            
            whale = signal.whale_username or signal.whale_address[:8]
            if whale not in self.trades_by_whale:
                self.trades_by_whale[whale] = []
            self.trades_by_whale[whale].append(trade)
        
        self.trades.append(trade)
        
        # Append to CSV
        try:
            with open(self.csv_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    trade.timestamp,
                    trade.date,
                    trade.time,
                    trade.whale_address,
                    trade.whale_username,
                    trade.whale_accuracy,
                    trade.market_id,
                    trade.market_title,
                    trade.outcome,
                    trade.entry_price,
                    trade.shares,
                    trade.capital,
                    trade.confidence,
                    trade.reasons,
                    trade.status,
                    trade.resolution_date,
                    trade.final_price,
                    trade.pnl,
                    trade.roi_percent,
                    trade.result
                ])
            
            logger.info(f"📝 Logged {status} trade: {signal.market_title[:40]} - ${signal.recommended_capital:.2f}")
        except Exception as e:
            logger.error(f"Failed to log trade to CSV: {e}")
    
    def get_summary(self) -> dict:
        """
        Get summary statistics of paper trading performance.
        
        Returns:
            Dictionary with summary stats
        """
        simulated_trades = [t for t in self.trades if t.status == "SIMULATED"]
        skipped_trades = [t for t in self.trades if t.status == "SKIPPED"]
        rejected_trades = [t for t in self.trades if t.status == "REJECTED"]
        
        resolved_trades = [t for t in simulated_trades if t.result in ["WIN", "LOSS"]]
        wins = [t for t in resolved_trades if t.result == "WIN"]
        losses = [t for t in resolved_trades if t.result == "LOSS"]
        
        total_pnl = sum(t.pnl for t in resolved_trades)
        
        return {
            "total_signals": len(self.trades),
            "simulated_trades": len(simulated_trades),
            "skipped_trades": len(skipped_trades),
            "rejected_trades": len(rejected_trades),
            "total_capital_allocated": float(self.total_capital_allocated),
            "average_position_size": float(self.total_capital_allocated / len(simulated_trades)) if simulated_trades else 0,
            "average_confidence": sum(t.confidence for t in simulated_trades) / len(simulated_trades) if simulated_trades else 0,
            "resolved_trades": len(resolved_trades),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": (len(wins) / len(resolved_trades) * 100) if resolved_trades else 0,
            "total_pnl": total_pnl,
            "average_pnl_per_trade": total_pnl / len(resolved_trades) if resolved_trades else 0,
            "roi_percent": (total_pnl / float(self.total_capital_allocated) * 100) if self.total_capital_allocated > 0 else 0,
            "most_active_whale": max(self.trades_by_whale.items(), key=lambda x: len(x[1]))[0] if self.trades_by_whale else "None",
            "trades_by_whale": {whale: len(trades) for whale, trades in self.trades_by_whale.items()}
        }
    
    def print_summary(self):
        """Print a formatted summary of paper trading performance."""
        summary = self.get_summary()
        
        logger.info("\n" + "="*60)
        logger.info("📊 PAPER TRADING SUMMARY")
        logger.info("="*60)
        logger.info(f"\n📈 TRADING ACTIVITY:")
        logger.info(f"  Total signals: {summary['total_signals']}")
        logger.info(f"  Simulated trades: {summary['simulated_trades']}")
        logger.info(f"  Skipped (low confidence): {summary['skipped_trades']}")
        logger.info(f"  Rejected (risk limits): {summary['rejected_trades']}")
        
        logger.info(f"\n💰 CAPITAL ALLOCATION:")
        logger.info(f"  Total allocated: ${summary['total_capital_allocated']:.2f}")
        logger.info(f"  Average position: ${summary['average_position_size']:.2f}")
        logger.info(f"  Average confidence: {summary['average_confidence']:.1f}%")
        
        if summary['resolved_trades'] > 0:
            logger.info(f"\n🎯 PERFORMANCE (Resolved Markets):")
            logger.info(f"  Resolved trades: {summary['resolved_trades']}")
            logger.info(f"  Wins: {summary['wins']} | Losses: {summary['losses']}")
            logger.info(f"  Win rate: {summary['win_rate']:.1f}%")
            logger.info(f"  Total P&L: ${summary['total_pnl']:.2f}")
            logger.info(f"  Avg P&L per trade: ${summary['average_pnl_per_trade']:.2f}")
            logger.info(f"  ROI: {summary['roi_percent']:.1f}%")
        else:
            logger.info(f"\n⏳ No markets resolved yet - track performance as they resolve")
        
        logger.info(f"\n🐋 WHALE ACTIVITY:")
        logger.info(f"  Most active: {summary['most_active_whale']}")
        for whale, count in sorted(summary['trades_by_whale'].items(), key=lambda x: x[1], reverse=True):
            logger.info(f"    • {whale}: {count} trades")
        
        logger.info(f"\n📁 CSV File: {self.csv_file}")
        logger.info("="*60 + "\n")
    
    def update_trade_result(
        self,
        market_id: str,
        final_price: float,
        result: str
    ):
        """
        Update a trade with resolution results.
        
        Args:
            market_id: Market ID
            final_price: Final price at resolution (0 or 1)
            result: "WIN" or "LOSS"
        """
        # Find trade in memory
        for trade in self.trades:
            if trade.market_id == market_id and trade.status == "SIMULATED":
                # Calculate P&L
                if result == "WIN":
                    trade.pnl = trade.capital * (1 / trade.entry_price - 1)
                else:
                    trade.pnl = -trade.capital
                
                trade.roi_percent = (trade.pnl / trade.capital) * 100
                trade.final_price = final_price
                trade.result = result
                trade.resolution_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
                
                logger.info(f"✅ Updated trade result: {trade.market_title[:40]} - {result} (P&L: ${trade.pnl:.2f})")
                break
        
        # Rewrite entire CSV with updated data
        try:
            with open(self.csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Timestamp', 'Date', 'Time', 'Whale Address', 'Whale Username',
                    'Whale Accuracy', 'Market ID', 'Market Title', 'Outcome',
                    'Entry Price', 'Shares', 'Capital', 'Confidence', 'Reasons',
                    'Status', 'Resolution Date', 'Final Price', 'PnL', 'ROI %', 'Result'
                ])
                
                for trade in self.trades:
                    writer.writerow([
                        trade.timestamp, trade.date, trade.time, trade.whale_address,
                        trade.whale_username, trade.whale_accuracy, trade.market_id,
                        trade.market_title, trade.outcome, trade.entry_price,
                        trade.shares, trade.capital, trade.confidence, trade.reasons,
                        trade.status, trade.resolution_date, trade.final_price,
                        trade.pnl, trade.roi_percent, trade.result
                    ])
        except Exception as e:
            logger.error(f"Failed to update CSV: {e}")


