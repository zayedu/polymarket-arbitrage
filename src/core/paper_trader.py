"""
Paper trading module for simulating arbitrage trades without real capital.
Logs all trades to CSV and tracks PnL for validation.
"""
import csv
import logging
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import List, Optional
import uuid

from .models import ArbitrageOpportunity, Order, Fill, Position, OrderSide, OrderStatus, OutcomeType
from .storage import Storage

logger = logging.getLogger(__name__)


class PaperTrader:
    """Simulates arbitrage trades for validation and testing."""
    
    def __init__(self, storage: Storage, csv_path: str = "paper_trades.csv"):
        """
        Initialize paper trader.
        
        Args:
            storage: Storage instance for persistent storage
            csv_path: Path to CSV file for trade logging
        """
        self.storage = storage
        self.csv_path = Path(csv_path)
        self.trades_log: List[dict] = []
        self.cumulative_pnl = Decimal('0.0')
        self.total_trades = 0
        self.successful_trades = 0
        
        # Initialize CSV file with headers if it doesn't exist
        self._initialize_csv()
    
    def _initialize_csv(self):
        """Create CSV file with headers if it doesn't exist."""
        if not self.csv_path.exists():
            with open(self.csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp',
                    'market_id',
                    'market_title',
                    'opportunity_type',
                    'yes_ask',
                    'no_ask',
                    'gross_edge',
                    'net_profit',
                    'apy',
                    'required_capital',
                    'trade_size',
                    'simulated_yes_fill_price',
                    'simulated_no_fill_price',
                    'simulated_slippage',
                    'simulated_gas_cost',
                    'actual_pnl',
                    'cumulative_pnl',
                    'status'
                ])
            logger.info(f"Created paper trading CSV log: {self.csv_path}")
    
    async def simulate_trade(
        self,
        opportunity: ArbitrageOpportunity,
        slippage_bps: int = 10,  # 0.1% slippage
        gas_cost_usd: Decimal = Decimal('0.01')
    ) -> dict:
        """
        Simulate executing an arbitrage trade.
        
        Args:
            opportunity: Detected arbitrage opportunity
            slippage_bps: Slippage in basis points (10 = 0.1%)
            gas_cost_usd: Estimated gas cost in USD
            
        Returns:
            Trade result dictionary
        """
        self.total_trades += 1
        trade_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)
        
        # Calculate trade size (limited by available liquidity)
        trade_size = min(
            opportunity.top_of_book_depth,
            opportunity.required_capital,
            Decimal('15.0')  # Max trade size from config
        )
        
        # Simulate slippage
        slippage_factor = Decimal(slippage_bps) / Decimal('10000')
        
        if opportunity.opportunity_type == "long_arb":
            # Buying YES and NO - slippage increases our cost
            simulated_yes_fill = opportunity.yes_ask * (Decimal('1.0') + slippage_factor)
            simulated_no_fill = opportunity.no_ask * (Decimal('1.0') + slippage_factor)
        else:  # short_arb
            # Selling YES and NO - slippage decreases our proceeds
            simulated_yes_fill = opportunity.yes_ask * (Decimal('1.0') - slippage_factor)
            simulated_no_fill = opportunity.no_ask * (Decimal('1.0') - slippage_factor)
        
        # Calculate actual PnL after slippage and gas
        total_cost = (simulated_yes_fill + simulated_no_fill) * trade_size
        total_proceeds = trade_size * Decimal('1.0')  # At resolution, YES+NO = $1
        
        if opportunity.opportunity_type == "long_arb":
            actual_pnl = total_proceeds - total_cost - gas_cost_usd
        else:
            actual_pnl = total_cost - total_proceeds - gas_cost_usd
        
        # Determine if trade would be successful
        status = "success" if actual_pnl > Decimal('0.0') else "loss"
        if status == "success":
            self.successful_trades += 1
        
        self.cumulative_pnl += actual_pnl
        
        # Create trade record
        trade_record = {
            'trade_id': trade_id,
            'timestamp': timestamp.isoformat(),
            'market_id': opportunity.market.id,
            'market_title': opportunity.market.title,
            'opportunity_type': opportunity.opportunity_type,
            'yes_ask': float(opportunity.yes_ask),
            'no_ask': float(opportunity.no_ask),
            'gross_edge': float(opportunity.gross_edge),
            'net_profit': float(opportunity.net_profit),
            'apy': float(opportunity.apy),
            'required_capital': float(opportunity.required_capital),
            'trade_size': float(trade_size),
            'simulated_yes_fill_price': float(simulated_yes_fill),
            'simulated_no_fill_price': float(simulated_no_fill),
            'simulated_slippage': float(slippage_factor * Decimal('100')),  # as percentage
            'simulated_gas_cost': float(gas_cost_usd),
            'actual_pnl': float(actual_pnl),
            'cumulative_pnl': float(self.cumulative_pnl),
            'status': status
        }
        
        # Log to CSV
        self._log_to_csv(trade_record)
        
        # Store in memory
        self.trades_log.append(trade_record)
        
        # Store in database
        await self._store_in_database(opportunity, trade_record, timestamp)
        
        # Log summary
        logger.info(
            f"📝 Paper Trade #{self.total_trades}: {opportunity.market.title[:50]}... | "
            f"Type: {opportunity.opportunity_type} | Size: ${trade_size:.2f} | "
            f"PnL: ${actual_pnl:.4f} | Cumulative: ${self.cumulative_pnl:.2f} | "
            f"Status: {status.upper()}"
        )
        
        return trade_record
    
    def _log_to_csv(self, trade_record: dict):
        """Append trade record to CSV file."""
        try:
            with open(self.csv_path, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    trade_record['timestamp'],
                    trade_record['market_id'],
                    trade_record['market_title'],
                    trade_record['opportunity_type'],
                    trade_record['yes_ask'],
                    trade_record['no_ask'],
                    trade_record['gross_edge'],
                    trade_record['net_profit'],
                    trade_record['apy'],
                    trade_record['required_capital'],
                    trade_record['trade_size'],
                    trade_record['simulated_yes_fill_price'],
                    trade_record['simulated_no_fill_price'],
                    trade_record['simulated_slippage'],
                    trade_record['simulated_gas_cost'],
                    trade_record['actual_pnl'],
                    trade_record['cumulative_pnl'],
                    trade_record['status']
                ])
        except Exception as e:
            logger.error(f"Failed to write to CSV: {e}")
    
    async def _store_in_database(
        self,
        opportunity: ArbitrageOpportunity,
        trade_record: dict,
        timestamp: datetime
    ):
        """Store simulated trade in database."""
        try:
            # Create simulated orders
            yes_order = Order(
                id=f"paper_yes_{trade_record['trade_id']}",
                token_id=opportunity.market.yes_token_id,
                outcome=OutcomeType.YES,
                side=OrderSide.BUY if opportunity.opportunity_type == "long_arb" else OrderSide.SELL,
                price=Decimal(str(trade_record['simulated_yes_fill_price'])),
                size=Decimal(str(trade_record['trade_size'])),
                status=OrderStatus.FILLED,
                filled_size=Decimal(str(trade_record['trade_size'])),
                created_at=timestamp,
                updated_at=timestamp
            )
            
            no_order = Order(
                id=f"paper_no_{trade_record['trade_id']}",
                token_id=opportunity.market.no_token_id,
                outcome=OutcomeType.NO,
                side=OrderSide.BUY if opportunity.opportunity_type == "long_arb" else OrderSide.SELL,
                price=Decimal(str(trade_record['simulated_no_fill_price'])),
                size=Decimal(str(trade_record['trade_size'])),
                status=OrderStatus.FILLED,
                filled_size=Decimal(str(trade_record['trade_size'])),
                created_at=timestamp,
                updated_at=timestamp
            )
            
            # Store orders (implementation depends on storage methods)
            # await self.storage.save_order(yes_order)
            # await self.storage.save_order(no_order)
            
            # Record PnL
            await self.storage.save_pnl_entry(
                market_id=opportunity.market.id,
                realized_pnl=Decimal(str(trade_record['actual_pnl'])),
                unrealized_pnl=Decimal('0.0'),
                description=f"Paper trade: {opportunity.opportunity_type} on {opportunity.market.title}"
            )
            
        except Exception as e:
            logger.error(f"Failed to store trade in database: {e}")
    
    def get_summary(self) -> dict:
        """
        Get summary statistics of paper trading session.
        
        Returns:
            Dictionary with summary statistics
        """
        if self.total_trades == 0:
            return {
                'total_trades': 0,
                'successful_trades': 0,
                'success_rate': 0.0,
                'cumulative_pnl': 0.0,
                'average_pnl_per_trade': 0.0,
                'best_trade': None,
                'worst_trade': None
            }
        
        success_rate = (self.successful_trades / self.total_trades) * 100
        avg_pnl = self.cumulative_pnl / self.total_trades
        
        # Find best and worst trades
        best_trade = max(self.trades_log, key=lambda x: x['actual_pnl']) if self.trades_log else None
        worst_trade = min(self.trades_log, key=lambda x: x['actual_pnl']) if self.trades_log else None
        
        return {
            'total_trades': self.total_trades,
            'successful_trades': self.successful_trades,
            'failed_trades': self.total_trades - self.successful_trades,
            'success_rate': float(success_rate),
            'cumulative_pnl': float(self.cumulative_pnl),
            'average_pnl_per_trade': float(avg_pnl),
            'best_trade': {
                'market': best_trade['market_title'],
                'pnl': best_trade['actual_pnl']
            } if best_trade else None,
            'worst_trade': {
                'market': worst_trade['market_title'],
                'pnl': worst_trade['actual_pnl']
            } if worst_trade else None
        }
    
    def print_summary(self):
        """Print formatted summary to console."""
        summary = self.get_summary()
        
        logger.info("=" * 60)
        logger.info("PAPER TRADING SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total Trades:        {summary['total_trades']}")
        logger.info(f"Successful:          {summary['successful_trades']} ({summary['success_rate']:.1f}%)")
        logger.info(f"Failed:              {summary.get('failed_trades', 0)}")
        logger.info(f"Cumulative PnL:      ${summary['cumulative_pnl']:.2f}")
        logger.info(f"Avg PnL per Trade:   ${summary['average_pnl_per_trade']:.4f}")
        
        if summary['best_trade']:
            logger.info(f"Best Trade:          ${summary['best_trade']['pnl']:.4f} on {summary['best_trade']['market'][:40]}...")
        
        if summary['worst_trade']:
            logger.info(f"Worst Trade:         ${summary['worst_trade']['pnl']:.4f} on {summary['worst_trade']['market'][:40]}...")
        
        logger.info("=" * 60)
        logger.info(f"CSV Log: {self.csv_path}")
        logger.info("=" * 60)

