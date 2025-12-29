"""
Risk management module with exposure limits and safety controls.
"""
import logging
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional

from config import Config
from ..core.models import ArbitrageOpportunity
from ..core.storage import Storage

logger = logging.getLogger(__name__)


class RiskManager:
    """Manages risk limits and exposure controls."""
    
    def __init__(self, config: Config, storage: Storage):
        """
        Initialize risk manager.
        
        Args:
            config: Application configuration
            storage: Database storage
        """
        self.config = config
        self.storage = storage
        
        # Track daily statistics
        self.daily_trades = 0
        self.daily_pnl = Decimal("0")
        self.daily_reset_time = datetime.now().date()
    
    def _check_daily_reset(self) -> None:
        """Reset daily counters if new day."""
        today = datetime.now().date()
        if today > self.daily_reset_time:
            logger.info(f"Daily reset: trades={self.daily_trades}, pnl=${self.daily_pnl:.2f}")
            self.daily_trades = 0
            self.daily_pnl = Decimal("0")
            self.daily_reset_time = today
    
    async def check_trade_allowed(
        self,
        opportunity: ArbitrageOpportunity
    ) -> tuple[bool, Optional[str]]:
        """
        Check if a trade is allowed based on risk limits.
        
        Args:
            opportunity: Opportunity to check
            
        Returns:
            Tuple of (allowed, reason_if_not_allowed)
        """
        self._check_daily_reset()
        
        # Check 1: Position size limit
        if opportunity.position_size > self.config.max_trade_size:
            reason = (
                f"Position size ${opportunity.position_size:.2f} exceeds "
                f"max trade size ${self.config.max_trade_size:.2f}"
            )
            logger.warning(f"❌ Trade blocked: {reason}")
            return False, reason
        
        # Check 2: Daily loss limit
        if self.daily_pnl < -self.config.max_daily_loss:
            reason = (
                f"Daily loss ${-self.daily_pnl:.2f} exceeds "
                f"limit ${self.config.max_daily_loss:.2f}"
            )
            logger.warning(f"❌ Trade blocked: {reason}")
            return False, reason
        
        # Check 3: Total exposure limit
        open_positions = await self.storage.get_open_positions()
        total_exposure = sum(
            Decimal(str(pos.total_cost))
            for pos in open_positions
        )
        
        new_exposure = total_exposure + (opportunity.position_size * opportunity.sum_asks)
        
        if new_exposure > self.config.max_open_exposure:
            reason = (
                f"New total exposure ${new_exposure:.2f} would exceed "
                f"limit ${self.config.max_open_exposure:.2f}"
            )
            logger.warning(f"❌ Trade blocked: {reason}")
            return False, reason
        
        # Check 4: Minimum profitability
        if opportunity.net_profit < self.config.min_net_profit:
            reason = (
                f"Net profit ${opportunity.net_profit:.2f} below "
                f"minimum ${self.config.min_net_profit:.2f}"
            )
            logger.debug(f"Trade skipped: {reason}")
            return False, reason
        
        # Check 5: Minimum APY
        if opportunity.apy < self.config.min_apy:
            reason = (
                f"APY {opportunity.apy:.1f}% below "
                f"minimum {self.config.min_apy}%"
            )
            logger.debug(f"Trade skipped: {reason}")
            return False, reason
        
        # Check 6: Market resolution time
        days_to_resolution = opportunity.market.days_to_resolution
        if days_to_resolution > self.config.max_days_to_resolution:
            reason = (
                f"Days to resolution {days_to_resolution} exceeds "
                f"maximum {self.config.max_days_to_resolution}"
            )
            logger.debug(f"Trade skipped: {reason}")
            return False, reason
        
        # All checks passed
        logger.info(f"✅ Trade allowed: {opportunity.market.title[:50]}")
        return True, None
    
    async def record_trade_result(
        self,
        net_pnl: Decimal,
        success: bool = True
    ) -> None:
        """
        Record trade result for daily tracking.
        
        Args:
            net_pnl: Net profit/loss from trade
            success: Whether trade was successful
        """
        self._check_daily_reset()
        
        self.daily_trades += 1
        self.daily_pnl += net_pnl
        
        logger.info(
            f"Trade recorded: PnL=${net_pnl:.2f}, "
            f"Daily total: {self.daily_trades} trades, ${self.daily_pnl:.2f}"
        )
        
        # Check if we've hit daily loss limit
        if self.daily_pnl < -self.config.max_daily_loss:
            logger.warning(
                f"⚠️  DAILY LOSS LIMIT REACHED: ${-self.daily_pnl:.2f} / "
                f"${self.config.max_daily_loss:.2f}"
            )
    
    async def get_risk_stats(self) -> dict:
        """
        Get current risk statistics.
        
        Returns:
            Dictionary of risk metrics
        """
        self._check_daily_reset()
        
        # Get open positions
        open_positions = await self.storage.get_open_positions()
        total_exposure = sum(
            Decimal(str(pos.total_cost))
            for pos in open_positions
        )
        
        # Get PnL entries for today
        today_start = datetime.combine(datetime.now().date(), datetime.min.time())
        pnl_entries = await self.storage.get_pnl_entries(start_date=today_start)
        
        # Calculate daily stats
        daily_realized_pnl = sum(
            Decimal(str(e.realized_pnl - e.fees_paid - e.gas_paid))
            for e in pnl_entries
        )
        
        # Calculate utilization percentages
        exposure_utilization = (
            (total_exposure / self.config.max_open_exposure * Decimal("100"))
            if self.config.max_open_exposure > 0
            else Decimal("0")
        )
        
        loss_limit_utilization = (
            (abs(self.daily_pnl) / self.config.max_daily_loss * Decimal("100"))
            if self.daily_pnl < 0 and self.config.max_daily_loss > 0
            else Decimal("0")
        )
        
        return {
            "daily_trades": self.daily_trades,
            "daily_pnl": self.daily_pnl,
            "daily_realized_pnl": daily_realized_pnl,
            "open_positions": len(open_positions),
            "total_exposure": total_exposure,
            "max_exposure": self.config.max_open_exposure,
            "exposure_utilization_pct": exposure_utilization,
            "daily_loss_limit": self.config.max_daily_loss,
            "loss_limit_utilization_pct": loss_limit_utilization,
            "max_trade_size": self.config.max_trade_size,
            "can_trade": self.daily_pnl > -self.config.max_daily_loss
        }
    
    async def check_emergency_stop(self) -> tuple[bool, Optional[str]]:
        """
        Check if emergency stop conditions are met.
        
        Returns:
            Tuple of (should_stop, reason)
        """
        stats = await self.get_risk_stats()
        
        # Emergency stop if daily loss exceeded
        if not stats["can_trade"]:
            reason = (
                f"Daily loss limit reached: ${-self.daily_pnl:.2f} / "
                f"${self.config.max_daily_loss:.2f}"
            )
            return True, reason
        
        # Emergency stop if exposure dangerously high (>95%)
        if stats["exposure_utilization_pct"] > Decimal("95"):
            reason = (
                f"Exposure critically high: {stats['exposure_utilization_pct']:.1f}% "
                f"(${stats['total_exposure']:.2f} / ${stats['max_exposure']:.2f})"
            )
            return True, reason
        
        return False, None
    
    def validate_opportunity(
        self,
        opportunity: ArbitrageOpportunity
    ) -> tuple[bool, Optional[str]]:
        """
        Validate opportunity quality (non-async checks).
        
        Args:
            opportunity: Opportunity to validate
            
        Returns:
            Tuple of (valid, reason_if_not)
        """
        # Check for negative net profit
        if opportunity.net_profit <= Decimal("0"):
            return False, f"Negative net profit: ${opportunity.net_profit:.4f}"
        
        # Check for invalid prices
        if opportunity.yes_ask <= Decimal("0") or opportunity.yes_ask >= Decimal("1"):
            return False, f"Invalid YES ask: {opportunity.yes_ask}"
        
        if opportunity.no_ask <= Decimal("0") or opportunity.no_ask >= Decimal("1"):
            return False, f"Invalid NO ask: {opportunity.no_ask}"
        
        # Check for invalid sum (should be < 1.0 for arb)
        if opportunity.sum_asks >= Decimal("1.0"):
            return False, f"Sum of asks >= $1.00: {opportunity.sum_asks}"
        
        # Check for insufficient liquidity
        if opportunity.liquidity < self.config.min_liquidity:
            return False, f"Insufficient liquidity: ${opportunity.liquidity:.2f}"
        
        # Check market is still active
        if not opportunity.market.is_active:
            return False, "Market is no longer active"
        
        return True, None



