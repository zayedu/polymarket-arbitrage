"""
Main application entry point.
Supports scan, paper trading, and live trading modes.
"""
import asyncio
import logging
import sys
from decimal import Decimal

import click
from rich.logging import RichHandler

from config import get_config, Config
from src.polymarket.gamma import GammaClient
from src.polymarket.clob import CLOBClient
from src.core.scanner import Scanner
from src.core.execution import Executor, ExecutionResult
from src.core.risk import RiskManager
from src.core.pnl import PnLTracker
from src.core.storage import Storage
from src.core.paper_trader import PaperTrader
from src.core.notifier import EmailNotifier
from src.app.ui import UI

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger(__name__)


class ArbitrageBot:
    """Main arbitrage bot orchestrator."""
    
    def __init__(self, config: Config):
        """Initialize bot with configuration."""
        self.config = config
        self.ui = UI()
        
        # Initialize clients
        self.gamma = GammaClient()
        self.clob = CLOBClient(
            private_key=config.polymarket_private_key if config.polymarket_private_key else None,
            api_key=config.polymarket_api_key if config.polymarket_api_key else None
        )
        
        # Initialize storage
        self.storage = Storage(config.database_url)
        
        # Initialize core modules
        self.scanner = Scanner(config, self.gamma, self.clob)
        self.executor = Executor(config, self.clob, self.storage)
        self.risk_manager = RiskManager(config, self.storage)
        self.pnl_tracker = PnLTracker(self.storage)
        self.paper_trader = PaperTrader(self.storage)
        
        # Initialize email notifier
        self.notifier = EmailNotifier(
            api_key=config.sendgrid_api_key if config.sendgrid_api_key else None,
            from_email=config.notification_email_from,
            to_email=config.notification_email_to if config.notification_email_to else None,
            enabled=config.enable_notifications
        )
    
    async def setup(self):
        """Setup database and resources."""
        await self.storage.initialize()
        logger.info("✅ Database initialized")
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.gamma.close()
        await self.clob.close()
        await self.storage.close()
        logger.info("✅ Cleanup complete")
    
    async def health_check_loop(self):
        """Send daily health check emails."""
        if not self.config.enable_notifications:
            return
        
        while True:
            try:
                await asyncio.sleep(86400)  # 24 hours
                
                # Gather basic stats
                stats = {
                    "Status": "Online and scanning",
                    "Mode": self.config.trading_mode.upper(),
                    "Poll Interval": f"{self.config.poll_interval_seconds}s"
                }
                
                await self.notifier.send_health_check(stats)
                logger.info("📧 Sent daily health check email")
                
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
    
    async def scan_mode(self, iterations: int = 1):
        """
        Scan-only mode: find and display opportunities without trading.
        
        Args:
            iterations: Number of scan iterations (None for continuous)
        """
        self.ui.print_banner()
        self.ui.print_info("Running in SCAN mode (no trading)")
        self.ui.print_config(self.config)
        
        iteration = 0
        max_iterations = None if iterations <= 0 else iterations
        
        try:
            while max_iterations is None or iteration < max_iterations:
                iteration += 1
                logger.info(f"\n{'='*60}")
                logger.info(f"Scan Iteration {iteration}")
                logger.info(f"{'='*60}")
                
                # Scan for opportunities
                opportunities = await self.scanner.scan_and_rank()
                
                # Display results
                self.ui.print_opportunities(opportunities, max_rows=10)
                
                if opportunities and opportunities[0]:
                    self.ui.print_opportunity_detail(opportunities[0])
                
                # Send email notification if opportunities found
                if opportunities and self.config.enable_notifications:
                    await self.notifier.send_opportunity_alert(opportunities)
                    logger.info(f"📧 Sent email alert for {len(opportunities)} opportunities")
                
                # Wait before next iteration
                if max_iterations is None or iteration < max_iterations:
                    await asyncio.sleep(self.config.poll_interval_seconds)
        
        except KeyboardInterrupt:
            logger.info("\n👋 Scan interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error in scan mode: {e}", exc_info=True)
            if self.config.enable_notifications:
                import traceback
                await self.notifier.send_error_alert(
                    str(e),
                    traceback.format_exc()
                )
            raise
    
    async def paper_trading_mode(self, iterations: int = 10):
        """
        Paper trading mode: simulate trades without real execution.
        Uses PaperTrader for realistic simulation with slippage and CSV logging.
        
        Args:
            iterations: Number of iterations (0 for continuous)
        """
        self.ui.print_banner()
        self.ui.print_info("Running in PAPER TRADING mode (simulation)")
        self.ui.print_config(self.config)
        
        iteration = 0
        max_iterations = None if iterations <= 0 else iterations
        
        logger.info(f"📝 Paper trades will be logged to: {self.paper_trader.csv_path}")
        
        try:
            while max_iterations is None or iteration < max_iterations:
                iteration += 1
                logger.info(f"\n{'='*60}")
                logger.info(f"Paper Trading Iteration {iteration}")
                logger.info(f"{'='*60}")
                
                # Scan for opportunities
                opportunities = await self.scanner.scan_and_rank()
                
                if not opportunities:
                    logger.info("No opportunities found")
                    await asyncio.sleep(self.config.poll_interval_seconds)
                    continue
                
                # Display all opportunities
                self.ui.print_opportunities(opportunities, max_rows=5)
                
                # Take the best opportunity
                best_opp = opportunities[0]
                
                # Check risk limits
                allowed, reason = await self.risk_manager.check_trade_allowed(best_opp)
                
                if not allowed:
                    logger.warning(f"Trade blocked: {reason}")
                    await asyncio.sleep(self.config.poll_interval_seconds)
                    continue
                
                # Simulate execution with PaperTrader
                logger.info(f"📝 [PAPER] Simulating trade for: {best_opp.market.title[:50]}...")
                trade_result = await self.paper_trader.simulate_trade(
                    best_opp,
                    slippage_bps=10,  # 0.1% slippage
                    gas_cost_usd=Decimal('0.01')  # Estimated gas cost
                )
                
                # Update risk manager
                await self.risk_manager.record_trade_result(
                    Decimal(str(trade_result['actual_pnl']))
                )
                
                # Wait before next iteration
                if max_iterations is None or iteration < max_iterations:
                    await asyncio.sleep(self.config.poll_interval_seconds)
        
        except KeyboardInterrupt:
            logger.info("\n👋 Paper trading interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error in paper trading mode: {e}", exc_info=True)
            if self.config.enable_notifications:
                import traceback
                await self.notifier.send_error_alert(
                    str(e),
                    traceback.format_exc()
                )
            raise
        finally:
            # Print summary
            self.paper_trader.print_summary()
    
    async def live_trading_mode(self, max_trades: int = 0):
        """
        Live trading mode: execute real trades.
        
        Args:
            max_trades: Maximum trades to execute (0 for unlimited)
        """
        self.ui.print_banner()
        self.ui.print_warning("Running in LIVE TRADING mode - REAL MONEY!")
        self.ui.print_config(self.config)
        
        # Safety confirmation
        if not self.ui.confirm("Are you sure you want to trade with real money?"):
            logger.info("Live trading cancelled by user")
            return
        
        if not self.config.polymarket_private_key:
            self.ui.print_error("No private key configured - cannot trade!")
            return
        
        trades_executed = 0
        
        try:
            while max_trades == 0 or trades_executed < max_trades:
                logger.info(f"\n{'='*60}")
                logger.info(f"Live Trading (Trades: {trades_executed})")
                logger.info(f"{'='*60}")
                
                # Check emergency stop
                should_stop, stop_reason = await self.risk_manager.check_emergency_stop()
                if should_stop:
                    self.ui.print_error(f"EMERGENCY STOP: {stop_reason}")
                    break
                
                # Scan for opportunities
                opportunities = await self.scanner.scan_and_rank()
                
                if not opportunities:
                    logger.info("No opportunities found")
                    await asyncio.sleep(self.config.poll_interval_seconds)
                    continue
                
                # Display opportunities
                self.ui.print_opportunities(opportunities, max_rows=5)
                
                # Take the best opportunity
                best_opp = opportunities[0]
                
                # Validate opportunity
                valid, validation_reason = self.risk_manager.validate_opportunity(best_opp)
                if not valid:
                    logger.warning(f"Invalid opportunity: {validation_reason}")
                    await asyncio.sleep(self.config.poll_interval_seconds)
                    continue
                
                # Check risk limits
                allowed, risk_reason = await self.risk_manager.check_trade_allowed(best_opp)
                if not allowed:
                    logger.warning(f"Trade blocked: {risk_reason}")
                    await asyncio.sleep(self.config.poll_interval_seconds)
                    continue
                
                # Execute trade
                logger.info(f"💰 LIVE: Executing {best_opp.market.title[:50]}")
                result, trade_pair = await self.executor.execute_arbitrage(
                    best_opp,
                    dry_run=False
                )
                
                if result == ExecutionResult.SUCCESS:
                    trades_executed += 1
                    self.ui.print_success(
                        f"Trade #{trades_executed} successful! "
                        f"Expected profit: ${best_opp.net_profit:.2f}"
                    )
                    
                    # Record trade
                    await self.risk_manager.record_trade_result(best_opp.net_profit)
                else:
                    self.ui.print_error(f"Trade failed with result: {result.value}")
                
                # Show risk stats
                risk_stats = await self.risk_manager.get_risk_stats()
                logger.info(
                    f"Risk Status: Exposure ${risk_stats['total_exposure']:.2f} / "
                    f"${risk_stats['max_exposure']:.2f} "
                    f"({risk_stats['exposure_utilization_pct']:.1f}%)"
                )
                
                # Wait before next iteration
                await asyncio.sleep(self.config.poll_interval_seconds)
        
        except KeyboardInterrupt:
            logger.info("\n👋 Live trading interrupted by user")
        
        finally:
            # Print final stats
            stats = await self.pnl_tracker.get_performance_stats()
            logger.info(f"\n{'='*60}")
            logger.info(f"SESSION SUMMARY")
            logger.info(f"{'='*60}")
            logger.info(f"Trades Executed: {trades_executed}")
            logger.info(f"Total Net PnL: ${stats['total']['net_pnl']:.2f}")
            logger.info(f"Win Rate: {stats['win_rate']:.1f}%")


@click.command()
@click.option(
    '--mode',
    type=click.Choice(['scan', 'paper', 'live'], case_sensitive=False),
    default='scan',
    help='Operation mode'
)
@click.option(
    '--iterations',
    type=int,
    default=0,
    help='Number of iterations (0 for continuous)'
)
@click.option(
    '--max-trades',
    type=int,
    default=0,
    help='Maximum trades in live mode (0 for unlimited)'
)
def main(mode: str, iterations: int, max_trades: int):
    """
    Polymarket Arbitrage Bot - Profit-First Edition
    
    Detects and executes arbitrage opportunities where YES + NO ≠ $1.00
    """
    # Load configuration
    config = get_config()
    
    # Override mode from CLI if provided
    if mode:
        config.trading_mode = mode.lower()
    
    # Set log level
    logging.getLogger().setLevel(config.log_level)
    
    # Create bot
    bot = ArbitrageBot(config)
    
    async def run():
        """Async main function."""
        try:
            await bot.setup()
            
            if config.trading_mode == 'scan':
                await bot.scan_mode(iterations)
            elif config.trading_mode == 'paper':
                await bot.paper_trading_mode(iterations)
            elif config.trading_mode == 'live':
                await bot.live_trading_mode(max_trades)
            else:
                logger.error(f"Unknown mode: {config.trading_mode}")
        
        finally:
            await bot.cleanup()
    
    # Run the bot
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

