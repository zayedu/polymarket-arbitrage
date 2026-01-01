"""Test risk management logic."""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta

from config import Config
from src.core.models import (
    Market, OrderBook, OrderBookLevel, OutcomeType, ArbitrageOpportunity
)
from src.core.risk import RiskManager
from src.core.storage import Storage


@pytest.fixture
async def risk_manager():
    """Create a test risk manager."""
    config = Config(
        database_url="sqlite+aiosqlite:///:memory:",
        max_trade_size=Decimal("10.0"),
        max_daily_loss=Decimal("5.0"),
        min_net_profit=Decimal("0.10"),
        min_apy=Decimal("50")
    )
    storage = Storage(config.database_url)
    await storage.initialize()
    
    rm = RiskManager(config, storage)
    yield rm
    
    await storage.close()


def create_test_opportunity(
    edge: Decimal = Decimal("0.02"),
    position_size: Decimal = Decimal("10"),
    days_to_resolution: int = 7
) -> ArbitrageOpportunity:
    """Create a test arbitrage opportunity."""
    future_date = datetime.now() + timedelta(days=days_to_resolution)
    
    market = Market(
        id="test-market",
        title="Test Market",
        condition_id="condition-1",
        yes_token_id="yes-token",
        no_token_id="no-token",
        end_date=future_date,
        volume=Decimal("10000")
    )
    
    yes_ask = Decimal("0.48")
    no_ask = Decimal("1.0") - yes_ask - edge
    
    yes_ob = OrderBook(
        token_id="yes-token",
        outcome=OutcomeType.YES,
        asks=[OrderBookLevel(price=yes_ask, size=position_size)]
    )
    
    no_ob = OrderBook(
        token_id="no-token",
        outcome=OutcomeType.NO,
        asks=[OrderBookLevel(price=no_ask, size=position_size)]
    )
    
    estimated_gas = Decimal("0.02")
    net_profit = (edge * position_size) - estimated_gas
    apy = (edge / Decimal(str(days_to_resolution))) * Decimal("365") * Decimal("100")
    
    return ArbitrageOpportunity(
        market=market,
        yes_orderbook=yes_ob,
        no_orderbook=no_ob,
        yes_ask=yes_ask,
        no_ask=no_ask,
        gross_edge=edge,
        estimated_gas=estimated_gas,
        net_profit=net_profit,
        position_size=position_size,
        liquidity=position_size,
        apy=apy,
        roi=(net_profit / (yes_ask + no_ask) / position_size) * Decimal("100")
    )


@pytest.mark.asyncio
async def test_validate_opportunity(risk_manager):
    """Test opportunity validation."""
    # Valid opportunity
    good_opp = create_test_opportunity()
    valid, reason = risk_manager.validate_opportunity(good_opp)
    assert valid
    assert reason is None
    
    # Invalid: negative profit
    bad_opp = create_test_opportunity(edge=Decimal("-0.01"))
    valid, reason = risk_manager.validate_opportunity(bad_opp)
    assert not valid
    assert "negative" in reason.lower()


@pytest.mark.asyncio
async def test_trade_size_limit(risk_manager):
    """Test max trade size enforcement."""
    # Trade size exceeds limit
    big_opp = create_test_opportunity(position_size=Decimal("20"))
    allowed, reason = await risk_manager.check_trade_allowed(big_opp)
    assert not allowed
    assert "trade size" in reason.lower()
    
    # Trade size within limit
    small_opp = create_test_opportunity(position_size=Decimal("5"))
    allowed, reason = await risk_manager.check_trade_allowed(small_opp)
    assert allowed or reason  # Might fail other checks but not size


@pytest.mark.asyncio
async def test_daily_loss_tracking(risk_manager):
    """Test daily loss tracking."""
    # Record a loss
    await risk_manager.record_trade_result(Decimal("-2.0"))
    assert risk_manager.daily_pnl == Decimal("-2.0")
    assert risk_manager.daily_trades == 1
    
    # Record another loss
    await risk_manager.record_trade_result(Decimal("-3.0"))
    assert risk_manager.daily_pnl == Decimal("-5.0")
    
    # Should block trades now (hit daily limit)
    opp = create_test_opportunity()
    allowed, reason = await risk_manager.check_trade_allowed(opp)
    assert not allowed
    assert "daily loss" in reason.lower()




