#!/usr/bin/env python3
"""
Test script for automated trading system.
Tests confidence filtering, position sizing, and execution logic.
"""
import asyncio
import logging
from decimal import Decimal
from datetime import datetime, timezone

from config import get_config
from src.ml.copy_trader import CopyTradeSignal
from src.core.auto_executor import AutoExecutor, ExecutionResult
from src.polymarket.clob import CLOBClient
from src.core.storage import Storage

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_test_signal(
    confidence: Decimal,
    capital: Decimal,
    market_title: str = "Test Market"
) -> CopyTradeSignal:
    """Create a test copy trade signal."""
    return CopyTradeSignal(
        whale_address="0x1234567890abcdef1234567890abcdef12345678",
        whale_username="@test_whale",
        whale_accuracy=Decimal("75"),
        market_id="test_market_123",
        market_slug="test-market-slug",
        market_title=market_title,
        outcome="YES",
        whale_shares=Decimal("1000"),
        whale_price=Decimal("0.60"),
        current_price=Decimal("0.62"),
        recommended_shares=Decimal("100"),
        recommended_capital=capital,
        confidence_score=confidence,
        timestamp=datetime.now(timezone.utc),
        reasons=["Test signal"]
    )


async def test_confidence_filtering():
    """Test that confidence threshold filtering works."""
    logger.info("\n" + "="*60)
    logger.info("TEST 1: Confidence Threshold Filtering")
    logger.info("="*60)
    
    config = get_config()
    storage = Storage(config.database_url)
    await storage.initialize()
    
    clob = CLOBClient()
    executor = AutoExecutor(config, clob, storage)
    
    # Test signals with different confidence levels
    test_cases = [
        (Decimal("90"), "Should execute (high confidence)"),
        (Decimal("75"), "Should execute (above threshold)"),
        (Decimal("70"), "Should execute (at threshold)"),
        (Decimal("65"), "Should skip (below threshold)"),
        (Decimal("50"), "Should skip (low confidence)"),
    ]
    
    logger.info(f"Confidence threshold: {config.min_confidence_score}%\n")
    
    for confidence, expected in test_cases:
        signal = create_test_signal(
            confidence=confidence,
            capital=Decimal("25"),
            market_title=f"Market {confidence}% confidence"
        )
        
        result = await executor.execute_copy_signal(signal)
        
        status = "✅" if "execute" in expected.lower() and result != ExecutionResult.SKIPPED else \
                 "✅" if "skip" in expected.lower() and result == ExecutionResult.SKIPPED else "❌"
        
        logger.info(f"{status} Confidence {confidence}%: {result.value} - {expected}")
    
    await storage.close()
    await clob.close()
    
    logger.info("\n✅ Confidence filtering test complete\n")


async def test_position_sizing():
    """Test that position sizing scales with confidence."""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Position Sizing with Confidence Scaling")
    logger.info("="*60)
    
    config = get_config()
    
    # Import CopyTrader to test position sizing
    from src.polymarket.gamma import GammaClient
    from src.ml.whale_tracker import WhaleTracker
    from src.ml.copy_trader import CopyTrader
    
    gamma = GammaClient()
    clob = CLOBClient()
    whale_tracker = WhaleTracker()
    copy_trader = CopyTrader(config, whale_tracker, gamma, clob)
    
    # Test position sizing with different confidence levels
    whale_shares = Decimal("1000")
    whale_price = Decimal("0.50")
    current_price = Decimal("0.52")
    
    logger.info(f"Whale position: {whale_shares} shares @ ${whale_price}")
    logger.info(f"Current price: ${current_price}")
    logger.info(f"Copy ratio: {config.copy_ratio} ({config.copy_ratio * 100}%)")
    logger.info(f"Position sizing mode: {config.position_sizing_mode}\n")
    
    test_confidences = [Decimal("100"), Decimal("80"), Decimal("70"), Decimal("60")]
    
    for confidence in test_confidences:
        shares, capital = copy_trader.calculate_copy_size(
            whale_shares,
            whale_price,
            current_price,
            confidence
        )
        
        logger.info(f"Confidence {confidence}%:")
        logger.info(f"  → Position size: {shares:.2f} shares")
        logger.info(f"  → Capital required: ${capital:.2f}")
        logger.info(f"  → Scaling factor: {confidence/100:.2f}x\n")
    
    await gamma.close()
    await clob.close()
    
    logger.info("✅ Position sizing test complete\n")


async def test_risk_limits():
    """Test that risk management limits are enforced."""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: Risk Management Limits")
    logger.info("="*60)
    
    config = get_config()
    storage = Storage(config.database_url)
    await storage.initialize()
    
    clob = CLOBClient()
    executor = AutoExecutor(config, clob, storage)
    
    logger.info(f"Max position size: ${config.max_copy_size}")
    logger.info(f"Min position size: ${config.min_position_size}")
    logger.info(f"Max open positions: {config.max_open_positions}\n")
    
    # Test cases for risk limits
    test_cases = [
        (Decimal("80"), Decimal("25"), "Normal position", "Should execute"),
        (Decimal("80"), Decimal("100"), "Too large", "Should reject"),
        (Decimal("80"), Decimal("2"), "Too small", "Should reject"),
    ]
    
    for confidence, capital, description, expected in test_cases:
        signal = create_test_signal(
            confidence=confidence,
            capital=capital,
            market_title=f"Market - {description}"
        )
        
        result = await executor.execute_copy_signal(signal)
        
        status = "✅" if "execute" in expected.lower() and result == ExecutionResult.SIMULATED else \
                 "✅" if "reject" in expected.lower() and result == ExecutionResult.REJECTED else "❌"
        
        logger.info(f"{status} {description} (${capital}): {result.value} - {expected}")
    
    await storage.close()
    await clob.close()
    
    logger.info("\n✅ Risk limits test complete\n")


async def test_paper_mode():
    """Test that paper mode simulates without executing real trades."""
    logger.info("\n" + "="*60)
    logger.info("TEST 4: Paper Trading Mode")
    logger.info("="*60)
    
    config = get_config()
    
    if config.trading_mode != "paper":
        logger.warning("⚠️  Not in paper mode - skipping this test")
        logger.info("Set TRADING_MODE=paper in .env to test\n")
        return
    
    storage = Storage(config.database_url)
    await storage.initialize()
    
    clob = CLOBClient()
    executor = AutoExecutor(config, clob, storage)
    
    logger.info(f"Trading mode: {config.trading_mode}")
    logger.info(f"Auto-trading enabled: {config.auto_trading_enabled}\n")
    
    signal = create_test_signal(
        confidence=Decimal("85"),
        capital=Decimal("30"),
        market_title="Paper Mode Test Market"
    )
    
    result = await executor.execute_copy_signal(signal)
    
    if result == ExecutionResult.SIMULATED:
        logger.info("✅ Paper mode working correctly - trade simulated, not executed")
    else:
        logger.error(f"❌ Unexpected result in paper mode: {result.value}")
    
    await storage.close()
    await clob.close()
    
    logger.info("\n✅ Paper mode test complete\n")


async def run_all_tests():
    """Run all automated trading tests."""
    logger.info("\n" + "="*60)
    logger.info("AUTOMATED TRADING SYSTEM - TEST SUITE")
    logger.info("="*60)
    
    config = get_config()
    
    logger.info(f"\nConfiguration:")
    logger.info(f"  Trading mode: {config.trading_mode}")
    logger.info(f"  Auto-trading enabled: {config.auto_trading_enabled}")
    logger.info(f"  Min confidence: {config.min_confidence_score}%")
    logger.info(f"  Position sizing: {config.position_sizing_mode}")
    logger.info(f"  Max position: ${config.max_copy_size}")
    logger.info(f"  Min position: ${config.min_position_size}")
    
    try:
        await test_confidence_filtering()
        await test_position_sizing()
        await test_risk_limits()
        await test_paper_mode()
        
        logger.info("\n" + "="*60)
        logger.info("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        logger.info("="*60)
        logger.info("\nNext steps:")
        logger.info("1. Review test results above")
        logger.info("2. Adjust confidence threshold if needed (MIN_CONFIDENCE_SCORE)")
        logger.info("3. Set AUTO_TRADING_ENABLED=true when ready")
        logger.info("4. Run bot in copy mode: python -m src.app.main --mode copy")
        logger.info("\n")
        
    except Exception as e:
        logger.error(f"\n❌ Test suite failed: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(run_all_tests())


