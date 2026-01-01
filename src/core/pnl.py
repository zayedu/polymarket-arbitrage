"""
PnL tracking and reporting module.
Calculates realized and unrealized profit/loss.
"""
import logging
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Optional, Dict

from ..core.models import PnLEntry
from ..core.storage import Storage, PositionDB, PnLEntryDB

logger = logging.getLogger(__name__)


class PnLTracker:
    """Tracks and reports profit and loss."""
    
    def __init__(self, storage: Storage):
        """
        Initialize PnL tracker.
        
        Args:
            storage: Database storage
        """
        self.storage = storage
    
    async def calculate_total_pnl(self) -> Dict[str, Decimal]:
        """
        Calculate total PnL across all trades.
        
        Returns:
            Dictionary with PnL metrics
        """
        entries = await self.storage.get_pnl_entries()
        
        if not entries:
            return {
                "realized_pnl": Decimal("0"),
                "total_fees": Decimal("0"),
                "total_gas": Decimal("0"),
                "net_pnl": Decimal("0"),
                "total_entry_cost": Decimal("0"),
                "total_roi": Decimal("0"),
                "trade_count": 0
            }
        
        realized_pnl = sum(Decimal(str(e.realized_pnl)) for e in entries)
        total_fees = sum(Decimal(str(e.fees_paid)) for e in entries)
        total_gas = sum(Decimal(str(e.gas_paid)) for e in entries)
        total_entry_cost = sum(Decimal(str(e.entry_cost)) for e in entries)
        
        net_pnl = realized_pnl - total_fees - total_gas
        
        total_roi = Decimal("0")
        if total_entry_cost > 0:
            total_roi = (net_pnl / total_entry_cost) * Decimal("100")
        
        return {
            "realized_pnl": realized_pnl,
            "total_fees": total_fees,
            "total_gas": total_gas,
            "net_pnl": net_pnl,
            "total_entry_cost": total_entry_cost,
            "total_roi": total_roi,
            "trade_count": len(entries)
        }
    
    async def calculate_daily_pnl(self) -> Dict[str, Decimal]:
        """
        Calculate PnL for today.
        
        Returns:
            Dictionary with today's PnL metrics
        """
        today_start = datetime.combine(datetime.now().date(), datetime.min.time())
        entries = await self.storage.get_pnl_entries(start_date=today_start)
        
        if not entries:
            return {
                "realized_pnl": Decimal("0"),
                "total_fees": Decimal("0"),
                "total_gas": Decimal("0"),
                "net_pnl": Decimal("0"),
                "trade_count": 0
            }
        
        realized_pnl = sum(Decimal(str(e.realized_pnl)) for e in entries)
        total_fees = sum(Decimal(str(e.fees_paid)) for e in entries)
        total_gas = sum(Decimal(str(e.gas_paid)) for e in entries)
        
        net_pnl = realized_pnl - total_fees - total_gas
        
        return {
            "realized_pnl": realized_pnl,
            "total_fees": total_fees,
            "total_gas": total_gas,
            "net_pnl": net_pnl,
            "trade_count": len(entries)
        }
    
    async def calculate_weekly_pnl(self) -> Dict[str, Decimal]:
        """
        Calculate PnL for the past 7 days.
        
        Returns:
            Dictionary with weekly PnL metrics
        """
        week_start = datetime.now() - timedelta(days=7)
        entries = await self.storage.get_pnl_entries(start_date=week_start)
        
        if not entries:
            return {
                "realized_pnl": Decimal("0"),
                "total_fees": Decimal("0"),
                "total_gas": Decimal("0"),
                "net_pnl": Decimal("0"),
                "trade_count": 0
            }
        
        realized_pnl = sum(Decimal(str(e.realized_pnl)) for e in entries)
        total_fees = sum(Decimal(str(e.fees_paid)) for e in entries)
        total_gas = sum(Decimal(str(e.gas_paid)) for e in entries)
        
        net_pnl = realized_pnl - total_fees - total_gas
        
        return {
            "realized_pnl": realized_pnl,
            "total_fees": total_fees,
            "total_gas": total_gas,
            "net_pnl": net_pnl,
            "trade_count": len(entries)
        }
    
    async def calculate_unrealized_pnl(self) -> Decimal:
        """
        Calculate unrealized PnL from open positions.
        
        Returns:
            Total unrealized PnL
        """
        positions = await self.storage.get_open_positions()
        
        if not positions:
            return Decimal("0")
        
        total_unrealized = sum(
            Decimal(str(pos.unrealized_pnl or 0))
            for pos in positions
        )
        
        return total_unrealized
    
    async def record_closed_position(
        self,
        market_id: str,
        entry_cost: Decimal,
        exit_value: Decimal,
        fees_paid: Decimal = Decimal("0"),
        gas_paid: Decimal = Decimal("0"),
        notes: Optional[str] = None
    ) -> int:
        """
        Record a closed position as a PnL entry.
        
        Args:
            market_id: Market identifier
            entry_cost: Total cost to enter position
            exit_value: Total value when exiting
            fees_paid: Trading fees paid
            gas_paid: Gas costs paid
            notes: Optional notes
            
        Returns:
            PnL entry ID
        """
        realized_pnl = exit_value - entry_cost
        
        entry = PnLEntry(
            market_id=market_id,
            realized_pnl=realized_pnl,
            fees_paid=fees_paid,
            gas_paid=gas_paid,
            entry_cost=entry_cost,
            exit_value=exit_value,
            notes=notes
        )
        
        entry_id = await self.storage.save_pnl_entry(entry, market_id)
        
        logger.info(
            f"PnL recorded: Entry=${entry_cost:.2f}, Exit=${exit_value:.2f}, "
            f"Realized=${realized_pnl:.2f}, Net=${entry.net_pnl:.2f}"
        )
        
        return entry_id
    
    async def get_performance_stats(self) -> Dict[str, any]:
        """
        Get comprehensive performance statistics.
        
        Returns:
            Dictionary with performance metrics
        """
        # Get all PnL data
        total_pnl = await self.calculate_total_pnl()
        daily_pnl = await self.calculate_daily_pnl()
        weekly_pnl = await self.calculate_weekly_pnl()
        unrealized = await self.calculate_unrealized_pnl()
        
        # Get open positions
        open_positions = await self.storage.get_open_positions()
        
        # Calculate win rate
        all_entries = await self.storage.get_pnl_entries()
        winning_trades = sum(
            1 for e in all_entries
            if (e.realized_pnl - e.fees_paid - e.gas_paid) > 0
        )
        
        win_rate = Decimal("0")
        if all_entries:
            win_rate = (Decimal(str(winning_trades)) / Decimal(str(len(all_entries)))) * Decimal("100")
        
        # Calculate average profit per trade
        avg_profit = Decimal("0")
        if total_pnl["trade_count"] > 0:
            avg_profit = total_pnl["net_pnl"] / Decimal(str(total_pnl["trade_count"]))
        
        return {
            "total": total_pnl,
            "daily": daily_pnl,
            "weekly": weekly_pnl,
            "unrealized_pnl": unrealized,
            "open_positions": len(open_positions),
            "win_rate": win_rate,
            "avg_profit_per_trade": avg_profit
        }
    
    async def generate_daily_report(self) -> str:
        """
        Generate a daily performance report.
        
        Returns:
            Formatted report string
        """
        stats = await self.get_performance_stats()
        
        report_lines = [
            "=" * 60,
            "DAILY PERFORMANCE REPORT",
            f"Date: {datetime.now().strftime('%Y-%m-%d')}",
            "=" * 60,
            "",
            "TODAY'S PERFORMANCE:",
            f"  Trades: {stats['daily']['trade_count']}",
            f"  Realized PnL: ${stats['daily']['realized_pnl']:.2f}",
            f"  Fees Paid: ${stats['daily']['total_fees']:.4f}",
            f"  Gas Paid: ${stats['daily']['total_gas']:.4f}",
            f"  Net Profit: ${stats['daily']['net_pnl']:.2f}",
            "",
            "OVERALL PERFORMANCE:",
            f"  Total Trades: {stats['total']['trade_count']}",
            f"  Total Net Profit: ${stats['total']['net_pnl']:.2f}",
            f"  Total ROI: {stats['total']['total_roi']:.2f}%",
            f"  Win Rate: {stats['win_rate']:.1f}%",
            f"  Avg Profit/Trade: ${stats['avg_profit_per_trade']:.2f}",
            "",
            "CURRENT STATUS:",
            f"  Open Positions: {stats['open_positions']}",
            f"  Unrealized PnL: ${stats['unrealized_pnl']:.2f}",
            "=" * 60
        ]
        
        return "\n".join(report_lines)
    
    async def generate_weekly_report(self) -> str:
        """
        Generate a weekly performance report.
        
        Returns:
            Formatted report string
        """
        stats = await self.get_performance_stats()
        
        report_lines = [
            "=" * 60,
            "WEEKLY PERFORMANCE REPORT",
            f"Week Ending: {datetime.now().strftime('%Y-%m-%d')}",
            "=" * 60,
            "",
            "THIS WEEK'S PERFORMANCE:",
            f"  Trades: {stats['weekly']['trade_count']}",
            f"  Realized PnL: ${stats['weekly']['realized_pnl']:.2f}",
            f"  Fees Paid: ${stats['weekly']['total_fees']:.4f}",
            f"  Gas Paid: ${stats['weekly']['total_gas']:.4f}",
            f"  Net Profit: ${stats['weekly']['net_pnl']:.2f}",
            "",
            "OVERALL PERFORMANCE:",
            f"  Total Trades: {stats['total']['trade_count']}",
            f"  Total Net Profit: ${stats['total']['net_pnl']:.2f}",
            f"  Total ROI: {stats['total']['total_roi']:.2f}%",
            f"  Win Rate: {stats['win_rate']:.1f}%",
            f"  Avg Profit/Trade: ${stats['avg_profit_per_trade']:.2f}",
            "",
            "CURRENT STATUS:",
            f"  Open Positions: {stats['open_positions']}",
            f"  Unrealized PnL: ${stats['unrealized_pnl']:.2f}",
            "=" * 60
        ]
        
        return "\n".join(report_lines)
    
    async def log_daily_summary(self) -> None:
        """Log daily summary to console and logger."""
        report = await self.generate_daily_report()
        logger.info("\n" + report)
        print(report)
    
    async def log_weekly_summary(self) -> None:
        """Log weekly summary to console and logger."""
        report = await self.generate_weekly_report()
        logger.info("\n" + report)
        print(report)




