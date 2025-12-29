"""Test scanner functionality."""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta

from src.core.models import Market, OrderBook, OrderBookLevel, OutcomeType


def test_market_days_to_resolution():
    """Test market days to resolution calculation."""
    future_date = datetime.now() + timedelta(days=7)
    market = Market(
        id="test-market",
        title="Test Market",
        condition_id="condition-1",
        yes_token_id="yes-token",
        no_token_id="no-token",
        end_date=future_date,
        volume=Decimal("10000")
    )
    
    assert market.days_to_resolution >= 6  # Should be around 7 days


def test_orderbook_properties():
    """Test orderbook property calculations."""
    orderbook = OrderBook(
        token_id="test-token",
        outcome=OutcomeType.YES,
        bids=[
            OrderBookLevel(price=Decimal("0.48"), size=Decimal("100")),
            OrderBookLevel(price=Decimal("0.47"), size=Decimal("200"))
        ],
        asks=[
            OrderBookLevel(price=Decimal("0.52"), size=Decimal("150")),
            OrderBookLevel(price=Decimal("0.53"), size=Decimal("250"))
        ]
    )
    
    assert orderbook.best_bid_price == Decimal("0.48")
    assert orderbook.best_ask_price == Decimal("0.52")
    assert orderbook.spread == Decimal("0.04")
    assert orderbook.top_of_book_liquidity == Decimal("100")  # min(100, 150)


def test_arbitrage_detection():
    """Test basic arbitrage logic."""
    yes_ask = Decimal("0.48")
    no_ask = Decimal("0.50")
    sum_asks = yes_ask + no_ask
    
    # Should be arbitrage opportunity
    assert sum_asks < Decimal("1.0")
    
    edge = Decimal("1.0") - sum_asks
    assert edge == Decimal("0.02")  # 2% edge



