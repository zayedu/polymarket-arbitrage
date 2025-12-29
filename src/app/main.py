"""
Main application entry point.
Supports scan, paper trading, and live trading modes.
"""
import asyncio
import logging
import sys
from decimal import Decimal
from typing import List

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
from src.ml.whale_tracker import WhaleTracker
from src.ml.copy_trader import CopyTrader, CopyTradeSignal
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
        
        # Initialize email notifier with SMS support
        self.notifier = EmailNotifier(
            api_key=config.sendgrid_api_key if config.sendgrid_api_key else None,
            from_email=config.notification_email_from,
            to_email=config.notification_email_to if config.notification_email_to else None,
            enabled=config.enable_notifications,
            sms_enabled=config.sms_enabled,
            sms_phone_number=config.sms_phone_number if config.sms_phone_number else None,
            sms_carrier=config.sms_carrier if config.sms_carrier else None
        )
        
        # Initialize copy trading components
        self.whale_tracker = WhaleTracker()
        self.copy_trader = CopyTrader(config, self.whale_tracker, self.gamma, self.clob)
    
    async def setup(self):
        """Setup database and resources."""
        await self.storage.initialize()
        logger.info("✅ Database initialized")
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.gamma.close()
        await self.clob.close()
        await self.storage.close()
        await self.whale_tracker.close()
        logger.info("✅ Cleanup complete")
    
    async def test_notifications(self):
        """Send test email and SMS to verify notification setup."""
        self.ui.print_banner()
        self.ui.print_info("Testing Notification System")
        
        if not self.config.enable_notifications:
            self.ui.print_error("Notifications are DISABLED in config")
            self.ui.print_info("Set ENABLE_NOTIFICATIONS=true in .env to enable")
            return
        
        logger.info("📧 Sending test email...")
        
        # Create a fake opportunity for testing
        from datetime import datetime, timezone, timedelta
        from src.core.models import Market, ArbitrageOpportunity
        
        test_market = Market(
            id="test-market-123",
            condition_id="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            title="Test Market: Will notifications work?",
            description="This is a test notification",
            end_date=datetime.now(timezone.utc) + timedelta(days=7),
            volume=Decimal("1000"),
            yes_token_id="123",
            no_token_id="456"
        )
        
        # Create dummy orderbooks for test
        from src.core.models import OrderBook, OrderBookLevel
        
        test_yes_orderbook = OrderBook(
            market_id="test-market-123",
            token_id="123",
            outcome="YES",
            bids=[OrderBookLevel(price=Decimal("0.44"), size=Decimal("100"))],
            asks=[OrderBookLevel(price=Decimal("0.45"), size=Decimal("100"))]
        )
        
        test_no_orderbook = OrderBook(
            market_id="test-market-123",
            token_id="456",
            outcome="NO",
            bids=[OrderBookLevel(price=Decimal("0.49"), size=Decimal("100"))],
            asks=[OrderBookLevel(price=Decimal("0.50"), size=Decimal("100"))]
        )
        
        test_opp = ArbitrageOpportunity(
            market=test_market,
            yes_orderbook=test_yes_orderbook,
            no_orderbook=test_no_orderbook,
            yes_ask=Decimal("0.45"),
            no_ask=Decimal("0.50"),
            gross_edge=Decimal("0.05"),
            estimated_gas=Decimal("0.01"),
            net_profit=Decimal("0.04"),
            position_size=Decimal("10.0"),
            liquidity=Decimal("100.0"),
            apy=Decimal("150.5"),
            roi=Decimal("0.04")
        )
        
        # Send test email
        email_success = await self.notifier.send_opportunity_alert([test_opp])
        
        if email_success:
            self.ui.print_success(f"✅ Test email sent to: {self.config.notification_email_to}")
        else:
            self.ui.print_error(f"❌ Failed to send test email")
            self.ui.print_info("Check your SendGrid API key and email settings")
        
        # Send test SMS if enabled
        if self.config.sms_enabled:
            logger.info("📱 Sending test SMS...")
            sms_success = await self.notifier.send_sms(
                f"TEST: Polymarket bot notifications are working! This is a test message from your arbitrage bot."
            )
            
            if sms_success:
                self.ui.print_success(f"✅ Test SMS sent to: {self.config.sms_phone_number} ({self.config.sms_carrier})")
            else:
                self.ui.print_error(f"❌ Failed to send test SMS")
                self.ui.print_info("Check your phone number and carrier settings")
        else:
            self.ui.print_info("SMS notifications are disabled (SMS_ENABLED=false)")
        
        logger.info("\n" + "="*60)
        logger.info("Test complete! Check your email and phone for messages.")
        logger.info("="*60)
    
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
                
                # Send email + SMS notifications if opportunities found
                if opportunities and self.config.enable_notifications:
                    await self.notifier.send_opportunity_alert(opportunities)
                    logger.info(f"📧 Sent email alert for {len(opportunities)} opportunities")
                    
                    if self.config.sms_enabled:
                        best = opportunities[0]
                        sms_msg = f"ARB ALERT: {len(opportunities)} opps! Best: ${best.net_profit:.2f} profit, {best.apy:.0f}% APY - {best.market.title[:50]}"
                        await self.notifier.send_sms(sms_msg)
                        logger.info(f"📱 Sent SMS alert")
                
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
    
    async def copy_trading_mode(self, iterations: int = 0):
        """
        Copy trading mode: Monitor and copy trades from high-accuracy whales.
        
        Args:
            iterations: Number of monitoring iterations (0 for continuous)
        """
        self.ui.print_banner()
        self.ui.print_info("Running in COPY TRADING mode")
        self.ui.print_config(self.config)
        
        # Check if copy trading is enabled
        if not self.config.copy_trading_enabled:
            self.ui.print_error("Copy trading is DISABLED in config")
            self.ui.print_info("Set COPY_TRADING_ENABLED=true in .env to enable")
            return
        
        # Parse whale addresses
        whale_addresses = [
            addr.strip() 
            for addr in self.config.copy_whale_addresses.split(',') 
            if addr.strip()
        ]
        
        if not whale_addresses:
            self.ui.print_error("No whale addresses configured!")
            self.ui.print_info("Add whale addresses to COPY_WHALE_ADDRESSES in .env")
            self.ui.print_info("Run 'python find_whales.py' to find Alpha whales")
            return
        
        logger.info(f"🐋 Tracking {len(whale_addresses)} whales...")
        
        # Add whales to tracker
        for address in whale_addresses:
            try:
                await self.whale_tracker.add_whale(address)
            except Exception as e:
                logger.error(f"Failed to add whale {address[:8]}...: {e}")
        
        if not self.whale_tracker.whales:
            self.ui.print_error("No valid whales added. Check addresses.")
            return
        
        # Display tracked whales
        logger.info(f"\n{'='*60}")
        logger.info("TRACKED WHALES")
        logger.info(f"{'='*60}")
        for whale in self.whale_tracker.get_tracked_whales():
            logger.info(
                f"  • {whale.username or 'Anonymous'} ({whale.address[:8]}...): "
                f"{whale.accuracy:.1f}% accuracy, {whale.total_trades} trades"
            )
        
        iteration = 0
        max_iterations = None if iterations <= 0 else iterations
        signals_generated = 0
        
        try:
            while max_iterations is None or iteration < max_iterations:
                iteration += 1
                logger.info(f"\n{'='*60}")
                logger.info(f"Copy Trading Iteration {iteration}")
                logger.info(f"{'='*60}")
                
                # Monitor whales for new positions
                new_positions = await self.whale_tracker.monitor_whales()
                
                if not new_positions:
                    logger.info("No new whale positions detected")
                    await asyncio.sleep(self.config.poll_interval_seconds)
                    continue
                
                # Generate copy trade signals
                signals = await self.copy_trader.generate_copy_signals(new_positions)
                
                if not signals:
                    logger.info("No valid copy signals generated")
                    await asyncio.sleep(self.config.poll_interval_seconds)
                    continue
                
                # Display signals
                logger.info(f"\n🚨 {len(signals)} COPY TRADE SIGNAL(S)!")
                for i, signal in enumerate(signals, 1):
                    logger.info(f"\n  Signal #{i}:")
                    logger.info(f"    Whale: {signal.whale_username or signal.whale_address[:8]}... ({signal.whale_accuracy:.1f}% accuracy)")
                    logger.info(f"    Market: {signal.market_title[:60]}")
                    logger.info(f"    Position: {signal.outcome} @ ${signal.current_price:.4f}")
                    logger.info(f"    Recommended: {signal.recommended_shares:.2f} shares (${signal.recommended_capital:.2f})")
                    logger.info(f"    Confidence: {signal.confidence_score:.0f}%")
                    logger.info(f"    Reasons: {', '.join(signal.reasons[:3])}")
                
                signals_generated += len(signals)
                
                # Send notifications
                if self.config.enable_notifications:
                    await self._send_copy_trade_notifications(signals)
                
                # In paper mode, just log. In live mode, would execute here.
                if self.config.trading_mode == 'paper':
                    logger.info("\n📋 Paper mode: Signals logged but not executed")
                    for signal in signals:
                        self.copy_trader.mark_as_copied(signal.market_id)
                else:
                    logger.info("\n⚠️  Live copy trading not yet implemented. Use paper mode for now.")
                
                # Wait before next iteration
                await asyncio.sleep(self.config.poll_interval_seconds)
        
        except KeyboardInterrupt:
            logger.info("\n👋 Copy trading interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error in copy trading mode: {e}", exc_info=True)
            if self.config.enable_notifications:
                import traceback
                await self.notifier.send_error_alert(
                    str(e),
                    traceback.format_exc()
                )
            raise
        finally:
            # Print summary
            stats = self.copy_trader.get_copy_stats()
            logger.info(f"\n{'='*60}")
            logger.info(f"COPY TRADING SUMMARY")
            logger.info(f"{'='*60}")
            logger.info(f"Iterations: {iteration}")
            logger.info(f"Signals Generated: {signals_generated}")
            logger.info(f"Whales Tracked: {stats['whales_tracked']}")
            logger.info(f"Markets Copied: {stats['total_copied']}")
    
    async def _send_copy_trade_notifications(self, signals: List[CopyTradeSignal]):
        """Send email and SMS notifications for copy trade signals."""
        try:
            logger.info(f"📧 Sending copy trade notifications for {len(signals)} signal(s)...")
            
            # Send email with all signals
            if self.config.enable_notifications and signals:
                await self.notifier.send_copy_trade_alert(signals)
                logger.info(f"✅ Sent email with {len(signals)} copy trade signal(s)")
            
            # Send SMS for the best signal
            if self.config.sms_enabled and signals:
                best = signals[0]
                sms_msg = f"COPY SIGNAL: {best.whale_username or 'Whale'} bought {best.outcome} on '{best.market_title[:40]}' - Confidence: {best.confidence_score:.0f}%"
                await self.notifier.send_sms(sms_msg)
                logger.info("📱 Sent SMS notification")
                
        except Exception as e:
            logger.error(f"Error sending copy trade notifications: {e}", exc_info=True)


@click.command()
@click.option(
    '--mode',
    type=click.Choice(['scan', 'paper', 'live', 'copy'], case_sensitive=False),
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
@click.option(
    '--test-notifications',
    is_flag=True,
    help='Send test email and SMS to verify notification setup'
)
def main(mode: str, iterations: int, max_trades: int, test_notifications: bool):
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
            
            # Handle test notifications flag
            if test_notifications:
                await bot.test_notifications()
                return
            
            if config.trading_mode == 'scan':
                await bot.scan_mode(iterations)
            elif config.trading_mode == 'paper':
                await bot.paper_trading_mode(iterations)
            elif config.trading_mode == 'live':
                await bot.live_trading_mode(max_trades)
            elif config.trading_mode == 'copy':
                await bot.copy_trading_mode(iterations)
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

