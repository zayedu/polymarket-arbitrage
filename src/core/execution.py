"""
Safe execution engine for arbitrage trades.
Handles multi-leg orders with timeout and unwind logic.
"""
import logging
import asyncio
from decimal import Decimal
from datetime import datetime
from typing import Optional, Tuple
from enum import Enum

from config import Config
from ..polymarket.clob import CLOBClient
from ..core.models import (
    ArbitrageOpportunity, Order, OrderSide, OrderStatus,
    OutcomeType, TradePair, Position, Fill
)
from ..core.storage import Storage

logger = logging.getLogger(__name__)


class ExecutionResult(str, Enum):
    """Execution result status."""
    SUCCESS = "SUCCESS"
    PARTIAL_FILL = "PARTIAL_FILL"
    TIMEOUT = "TIMEOUT"
    FAILED = "FAILED"
    UNWOUND = "UNWOUND"


class Executor:
    """Executes arbitrage trades with safety controls."""
    
    def __init__(
        self,
        config: Config,
        clob_client: CLOBClient,
        storage: Storage
    ):
        """
        Initialize executor.
        
        Args:
            config: Application configuration
            clob_client: CLOB API client
            storage: Database storage
        """
        self.config = config
        self.clob = clob_client
        self.storage = storage
    
    async def execute_arbitrage(
        self,
        opportunity: ArbitrageOpportunity,
        dry_run: bool = False
    ) -> Tuple[ExecutionResult, Optional[TradePair]]:
        """
        Execute arbitrage by buying both YES and NO tokens.
        
        Strategy:
        1. Place limit orders for both YES and NO at best ask
        2. Wait for fills with timeout
        3. If one leg fills but other doesn't:
           - Cancel unfilled order
           - Attempt to unwind filled leg
        
        Args:
            opportunity: Arbitrage opportunity to execute
            dry_run: If True, simulate without real execution
            
        Returns:
            Tuple of (result_status, trade_pair)
        """
        market = opportunity.market
        size = opportunity.position_size
        
        logger.info(
            f"{'[DRY RUN] ' if dry_run else ''}Executing arbitrage on {market.title[:50]}: "
            f"Size=${size}, Net Profit=${opportunity.net_profit}"
        )
        
        if dry_run:
            # Simulate successful execution
            logger.info(f"[DRY RUN] Would buy {size} of YES @ {opportunity.yes_ask}")
            logger.info(f"[DRY RUN] Would buy {size} of NO @ {opportunity.no_ask}")
            return ExecutionResult.SUCCESS, None
        
        try:
            # Step 1: Place both orders simultaneously
            logger.info("Placing both legs...")
            
            yes_order_task = self.clob.place_limit_order(
                token_id=market.yes_token_id,
                outcome=OutcomeType.YES,
                side=OrderSide.BUY,
                price=opportunity.yes_ask,
                size=size
            )
            
            no_order_task = self.clob.place_limit_order(
                token_id=market.no_token_id,
                outcome=OutcomeType.NO,
                side=OrderSide.BUY,
                price=opportunity.no_ask,
                size=size
            )
            
            # Execute both orders concurrently
            yes_order, no_order = await asyncio.gather(
                yes_order_task,
                no_order_task,
                return_exceptions=True
            )
            
            # Check for errors
            if isinstance(yes_order, Exception):
                logger.error(f"Failed to place YES order: {yes_order}")
                return ExecutionResult.FAILED, None
            
            if isinstance(no_order, Exception):
                logger.error(f"Failed to place NO order: {no_order}")
                # Cancel YES order if placed
                if yes_order and yes_order.id:
                    await self.clob.cancel_order(yes_order.id)
                return ExecutionResult.FAILED, None
            
            if not yes_order or not no_order:
                logger.error("Failed to place orders")
                return ExecutionResult.FAILED, None
            
            logger.info(f"Orders placed: YES={yes_order.id}, NO={no_order.id}")
            
            # Save orders to database
            await self.storage.save_order(yes_order, market.id)
            await self.storage.save_order(no_order, market.id)
            
            # Create trade pair
            trade_pair = TradePair(
                opportunity=opportunity,
                yes_order=yes_order,
                no_order=no_order
            )
            
            # Step 2: Wait for fills with timeout
            logger.info(f"Waiting for fills (timeout={self.config.order_timeout_seconds}s)...")
            
            result = await self._wait_for_fills(trade_pair)
            
            # Step 3: Handle partial fills if necessary
            if result == ExecutionResult.PARTIAL_FILL and self.config.partial_fill_unwind:
                logger.warning("Partial fill detected, attempting unwind...")
                unwind_result = await self._unwind_partial_fill(trade_pair)
                if unwind_result:
                    return ExecutionResult.UNWOUND, trade_pair
                else:
                    return ExecutionResult.PARTIAL_FILL, trade_pair
            
            return result, trade_pair
            
        except Exception as e:
            logger.error(f"Error executing arbitrage: {e}", exc_info=True)
            return ExecutionResult.FAILED, None
    
    async def _wait_for_fills(
        self,
        trade_pair: TradePair,
        check_interval: float = 0.5
    ) -> ExecutionResult:
        """
        Wait for both orders to fill with timeout.
        
        Args:
            trade_pair: Trade pair to monitor
            check_interval: Seconds between status checks
            
        Returns:
            ExecutionResult status
        """
        timeout = self.config.order_timeout_seconds
        elapsed = 0.0
        
        while elapsed < timeout:
            # Check order statuses
            yes_status_task = self.clob.get_order_status(trade_pair.yes_order.id)
            no_status_task = self.clob.get_order_status(trade_pair.no_order.id)
            
            yes_status, no_status = await asyncio.gather(
                yes_status_task,
                no_status_task,
                return_exceptions=True
            )
            
            # Update orders if status received
            if isinstance(yes_status, Order):
                trade_pair.yes_order = yes_status
                await self.storage.save_order(yes_status, trade_pair.opportunity.market.id)
            
            if isinstance(no_status, Order):
                trade_pair.no_order = no_status
                await self.storage.save_order(no_status, trade_pair.opportunity.market.id)
            
            # Check if both filled
            if trade_pair.is_fully_filled:
                logger.info("✅ Both legs filled successfully!")
                await self._record_successful_trade(trade_pair)
                return ExecutionResult.SUCCESS
            
            # Check if partially filled
            if trade_pair.is_partially_filled:
                logger.warning("⚠️  Partial fill detected")
                return ExecutionResult.PARTIAL_FILL
            
            # Wait before next check
            await asyncio.sleep(check_interval)
            elapsed += check_interval
        
        # Timeout reached
        logger.warning(f"⏱️  Timeout reached after {timeout}s")
        
        # Cancel any unfilled orders
        await self._cancel_unfilled_orders(trade_pair)
        
        # Check final status
        if trade_pair.is_fully_filled:
            return ExecutionResult.SUCCESS
        elif trade_pair.is_partially_filled:
            return ExecutionResult.PARTIAL_FILL
        else:
            return ExecutionResult.TIMEOUT
    
    async def _cancel_unfilled_orders(self, trade_pair: TradePair) -> None:
        """Cancel any orders that aren't filled."""
        cancel_tasks = []
        
        if not trade_pair.yes_order.is_filled:
            logger.info(f"Cancelling YES order {trade_pair.yes_order.id}")
            cancel_tasks.append(self.clob.cancel_order(trade_pair.yes_order.id))
        
        if not trade_pair.no_order.is_filled:
            logger.info(f"Cancelling NO order {trade_pair.no_order.id}")
            cancel_tasks.append(self.clob.cancel_order(trade_pair.no_order.id))
        
        if cancel_tasks:
            results = await asyncio.gather(*cancel_tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Error cancelling order: {result}")
    
    async def _unwind_partial_fill(self, trade_pair: TradePair) -> bool:
        """
        Attempt to unwind a partial fill by selling the filled leg.
        
        Args:
            trade_pair: Trade pair with partial fill
            
        Returns:
            True if unwind successful, False otherwise
        """
        # Determine which leg is filled
        if trade_pair.yes_order.is_filled and not trade_pair.no_order.is_filled:
            filled_order = trade_pair.yes_order
            token_id = trade_pair.opportunity.market.yes_token_id
            outcome = OutcomeType.YES
        elif trade_pair.no_order.is_filled and not trade_pair.yes_order.is_filled:
            filled_order = trade_pair.no_order
            token_id = trade_pair.opportunity.market.no_token_id
            outcome = OutcomeType.NO
        else:
            logger.error("Cannot unwind: unexpected fill state")
            return False
        
        logger.info(f"Attempting to unwind {outcome.value} position...")
        
        try:
            # Get current best bid to sell at
            orderbook = await self.clob.get_orderbook(token_id, outcome)
            
            if not orderbook.best_bid:
                logger.error("No bid available for unwind")
                return False
            
            # Place sell order at best bid
            unwind_order = await self.clob.place_limit_order(
                token_id=token_id,
                outcome=outcome,
                side=OrderSide.SELL,
                price=orderbook.best_bid_price,
                size=filled_order.filled_size
            )
            
            if not unwind_order:
                logger.error("Failed to place unwind order")
                return False
            
            logger.info(f"Unwind order placed: {unwind_order.id}")
            
            # Wait for unwind to fill (shorter timeout)
            await asyncio.sleep(2)
            
            unwind_status = await self.clob.get_order_status(unwind_order.id)
            
            if unwind_status and unwind_status.is_filled:
                logger.info("✅ Unwind successful")
                return True
            else:
                logger.warning("⚠️  Unwind incomplete")
                return False
                
        except Exception as e:
            logger.error(f"Error unwinding position: {e}", exc_info=True)
            return False
    
    async def _record_successful_trade(self, trade_pair: TradePair) -> None:
        """Record successful arbitrage execution in database."""
        try:
            market = trade_pair.opportunity.market
            
            # Create positions
            yes_position = Position(
                market_id=market.id,
                token_id=market.yes_token_id,
                outcome=OutcomeType.YES,
                size=trade_pair.yes_order.filled_size,
                average_entry_price=trade_pair.yes_order.average_price or trade_pair.yes_order.price,
                total_cost=trade_pair.yes_order.filled_size * trade_pair.yes_order.price
            )
            
            no_position = Position(
                market_id=market.id,
                token_id=market.no_token_id,
                outcome=OutcomeType.NO,
                size=trade_pair.no_order.filled_size,
                average_entry_price=trade_pair.no_order.average_price or trade_pair.no_order.price,
                total_cost=trade_pair.no_order.filled_size * trade_pair.no_order.price
            )
            
            # Save positions
            await self.storage.save_position(yes_position, market.id)
            await self.storage.save_position(no_position, market.id)
            
            logger.info("Positions recorded in database")
            
        except Exception as e:
            logger.error(f"Error recording trade: {e}", exc_info=True)



