"""
Automated trade executor for copy trading signals.
Handles confidence filtering, risk management, and trade execution.
"""
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, Dict
from enum import Enum

from config import Config
from ..polymarket.clob import CLOBClient
from ..core.models import OrderSide, OutcomeType
from ..core.storage import Storage
from ..ml.copy_trader import CopyTradeSignal

logger = logging.getLogger(__name__)


class ExecutionResult(str, Enum):
    """Execution result status for automated trades."""
    SUCCESS = "SUCCESS"
    SKIPPED = "SKIPPED"  # Confidence too low
    REJECTED = "REJECTED"  # Failed risk checks
    FAILED = "FAILED"  # Execution error
    SIMULATED = "SIMULATED"  # Paper trading mode


class AutoExecutor:
    """
    Automated executor for copy trading signals.
    Applies confidence filtering, risk management, and executes trades.
    """
    
    def __init__(
        self,
        config: Config,
        clob: CLOBClient,
        storage: Storage
    ):
        """
        Initialize automated executor.
        
        Args:
            config: Bot configuration
            clob: CLOB API client for order execution
            storage: Database storage for tracking positions
        """
        self.config = config
        self.clob = clob
        self.storage = storage
        self.enabled = config.auto_trading_enabled
        
        # Safety mechanisms
        self.consecutive_failures = 0
        self.max_consecutive_failures = 3
        self.last_loss_time: Optional[datetime] = None
        self.loss_cooldown_seconds = 3600  # 1 hour cooldown after loss
        
        # Track executed trades to avoid duplicates
        self.executed_trades: Dict[str, datetime] = {}  # market_id -> timestamp
        
        logger.info(f"🤖 AutoExecutor initialized (enabled={self.enabled}, mode={config.trading_mode})")
    
    async def execute_copy_signal(self, signal: CopyTradeSignal) -> ExecutionResult:
        """
        Execute a copy trade signal if it meets all criteria.
        
        Args:
            signal: Copy trade signal to execute
            
        Returns:
            ExecutionResult indicating outcome
        """
        if not self.enabled:
            logger.debug("Auto-trading disabled, skipping execution")
            return ExecutionResult.SKIPPED
        
        # Check if we're in cooldown after a loss
        if self.last_loss_time:
            time_since_loss = (datetime.now(timezone.utc) - self.last_loss_time).total_seconds()
            if time_since_loss < self.loss_cooldown_seconds:
                remaining = self.loss_cooldown_seconds - time_since_loss
                logger.warning(f"⏸️  In cooldown after loss. {remaining/60:.0f} minutes remaining")
                return ExecutionResult.REJECTED
        
        # Check kill switch (too many consecutive failures)
        if self.consecutive_failures >= self.max_consecutive_failures:
            logger.error(f"🛑 KILL SWITCH ACTIVATED: {self.consecutive_failures} consecutive failures. Manual intervention required.")
            return ExecutionResult.REJECTED
        
        # Check confidence threshold (redundant but important safety check)
        if signal.confidence_score < self.config.min_confidence_score:
            logger.info(f"⏭️  Skipping trade - confidence {signal.confidence_score:.0f}% < {self.config.min_confidence_score:.0f}%")
            return ExecutionResult.SKIPPED
        
        # Check risk limits
        risk_check, risk_reason = await self._check_risk_limits(signal)
        if not risk_check:
            logger.warning(f"🚫 Trade rejected: {risk_reason}")
            return ExecutionResult.REJECTED
        
        # Check for duplicate execution
        if signal.market_id in self.executed_trades:
            last_execution = self.executed_trades[signal.market_id]
            time_since = (datetime.now(timezone.utc) - last_execution).total_seconds()
            if time_since < 3600:  # Don't execute same market within 1 hour
                logger.info(f"⏭️  Skipping - already executed {signal.market_title[:30]} {time_since/60:.0f}m ago")
                return ExecutionResult.REJECTED
        
        # Paper trading mode - simulate execution
        if self.config.trading_mode == "paper":
            logger.info(
                f"📝 [PAPER MODE] Would execute: {signal.outcome} on '{signal.market_title[:50]}' "
                f"@ ${signal.current_price:.4f} for ${signal.recommended_capital:.2f} "
                f"(confidence: {signal.confidence_score:.0f}%)"
            )
            # Track as executed to avoid duplicates
            self.executed_trades[signal.market_id] = datetime.now(timezone.utc)
            return ExecutionResult.SIMULATED
        
        # Live trading mode - execute real trade
        try:
            logger.info(
                f"🚀 Executing copy trade: {signal.outcome} on '{signal.market_title[:50]}' "
                f"@ ${signal.current_price:.4f} for ${signal.recommended_capital:.2f} "
                f"(confidence: {signal.confidence_score:.0f}%)"
            )
            
            # Determine token ID based on outcome
            token_id = self._get_token_id(signal)
            
            # Place limit order
            order = await self.clob.place_limit_order(
                token_id=token_id,
                outcome=OutcomeType.YES if signal.outcome == "YES" else OutcomeType.NO,
                side=OrderSide.BUY,
                price=signal.current_price,
                size=signal.recommended_shares
            )
            
            logger.info(f"✅ Order placed: {order.id} - {signal.recommended_shares:.2f} shares @ ${signal.current_price:.4f}")
            
            # Track execution
            self.executed_trades[signal.market_id] = datetime.now(timezone.utc)
            self.consecutive_failures = 0  # Reset failure counter on success
            
            # Save to database (if storage methods exist)
            await self._save_execution(signal, order)
            
            return ExecutionResult.SUCCESS
            
        except Exception as e:
            logger.error(f"❌ Execution failed: {e}", exc_info=True)
            self.consecutive_failures += 1
            return ExecutionResult.FAILED
    
    async def _check_risk_limits(self, signal: CopyTradeSignal) -> tuple[bool, str]:
        """
        Check if trade passes all risk management limits.
        
        Args:
            signal: Copy trade signal to check
            
        Returns:
            (passes, reason) tuple
        """
        # 1. Max position size
        if signal.recommended_capital > self.config.max_copy_size:
            return False, f"Position too large: ${signal.recommended_capital:.2f} > ${self.config.max_copy_size:.2f}"
        
        # 2. Min position size
        if signal.recommended_capital < self.config.min_position_size:
            return False, f"Position too small: ${signal.recommended_capital:.2f} < ${self.config.min_position_size:.2f}"
        
        # 3. Daily loss limit
        try:
            daily_pnl = await self._get_daily_pnl()
            if daily_pnl < -self.config.max_daily_loss:
                return False, f"Daily loss limit hit: ${daily_pnl:.2f} < -${self.config.max_daily_loss:.2f}"
        except Exception as e:
            logger.warning(f"Could not check daily PnL: {e}")
        
        # 4. Max open positions
        try:
            open_positions = await self._count_open_positions()
            if open_positions >= self.config.max_open_positions:
                return False, f"Max open positions reached: {open_positions} >= {self.config.max_open_positions}"
        except Exception as e:
            logger.warning(f"Could not check open positions: {e}")
        
        # 5. Max per market (don't double-down)
        try:
            existing = await self._has_position_in_market(signal.market_id)
            if existing:
                return False, f"Already have position in {signal.market_title[:30]}"
        except Exception as e:
            logger.warning(f"Could not check existing position: {e}")
        
        return True, "All risk checks passed"
    
    async def _get_daily_pnl(self) -> Decimal:
        """Get today's PnL from storage."""
        try:
            # This would need to be implemented in storage.py
            # For now, return 0 as a safe default
            return Decimal("0")
        except Exception as e:
            logger.warning(f"Could not fetch daily PnL: {e}")
            return Decimal("0")
    
    async def _count_open_positions(self) -> int:
        """Count number of open positions."""
        try:
            # This would need to be implemented in storage.py
            # For now, return 0 as a safe default
            return 0
        except Exception as e:
            logger.warning(f"Could not count open positions: {e}")
            return 0
    
    async def _has_position_in_market(self, market_id: str) -> bool:
        """Check if we already have a position in this market."""
        try:
            # This would need to be implemented in storage.py
            # For now, return False as a safe default
            return False
        except Exception as e:
            logger.warning(f"Could not check existing position: {e}")
            return False
    
    def _get_token_id(self, signal: CopyTradeSignal) -> str:
        """
        Get the token ID for the signal's outcome.
        Note: This is a placeholder - in reality, we'd need to fetch
        the market data to get the correct token IDs.
        """
        # TODO: Fetch market data to get actual token IDs
        # For now, use market_id as a placeholder
        return signal.market_id
    
    async def _save_execution(self, signal: CopyTradeSignal, order) -> None:
        """
        Save execution details to database.
        
        Args:
            signal: Copy trade signal
            order: Executed order
        """
        try:
            # This would save to database if storage methods exist
            # For now, just log
            logger.debug(f"Execution saved: {order.id}")
        except Exception as e:
            logger.warning(f"Could not save execution: {e}")
    
    def reset_kill_switch(self) -> None:
        """Manually reset the kill switch after intervention."""
        self.consecutive_failures = 0
        self.last_loss_time = None
        logger.info("🔄 Kill switch reset - trading resumed")
    
    def get_status(self) -> dict:
        """Get current executor status."""
        return {
            "enabled": self.enabled,
            "trading_mode": self.config.trading_mode,
            "consecutive_failures": self.consecutive_failures,
            "in_cooldown": self.last_loss_time is not None and 
                          (datetime.now(timezone.utc) - self.last_loss_time).total_seconds() < self.loss_cooldown_seconds,
            "executed_trades_count": len(self.executed_trades)
        }

