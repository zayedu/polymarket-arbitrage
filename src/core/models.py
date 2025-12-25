"""
Pydantic models for type-safe data structures.
All models use Decimal for financial precision.
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class OrderSide(str, Enum):
    """Order side enumeration."""
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    """Order status enumeration."""
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class OutcomeType(str, Enum):
    """Market outcome type."""
    YES = "YES"
    NO = "NO"


class Market(BaseModel):
    """Polymarket prediction market model."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    id: str = Field(..., description="Market ID")
    title: str = Field(..., description="Market question/title")
    condition_id: str = Field(..., description="Condition ID for resolution")
    yes_token_id: str = Field(..., description="YES outcome token ID")
    no_token_id: str = Field(..., description="NO outcome token ID")
    end_date: datetime = Field(..., description="Market resolution date")
    volume: Decimal = Field(..., description="Total trading volume in USD")
    description: Optional[str] = Field(None, description="Market description")
    resolution_source: Optional[str] = Field(None, description="Resolution criteria source")
    category: Optional[str] = Field(None, description="Market category")
    
    @property
    def days_to_resolution(self) -> int:
        """Calculate days until market resolution."""
        # Handle both naive and timezone-aware datetimes
        now = datetime.now()
        if self.end_date.tzinfo is not None:
            # end_date is timezone-aware, make now aware too
            from datetime import timezone
            now = datetime.now(timezone.utc)
            # If end_date has a different timezone, convert both to UTC
            if self.end_date.tzinfo != timezone.utc:
                end_date_utc = self.end_date.astimezone(timezone.utc)
            else:
                end_date_utc = self.end_date
            delta = end_date_utc - now
        else:
            # Both are naive
            delta = self.end_date - now
        return max(0, delta.days)
    
    @property
    def is_active(self) -> bool:
        """Check if market is still active."""
        now = datetime.now()
        if self.end_date.tzinfo is not None:
            from datetime import timezone
            now = datetime.now(timezone.utc)
            if self.end_date.tzinfo != timezone.utc:
                end_date_utc = self.end_date.astimezone(timezone.utc)
            else:
                end_date_utc = self.end_date
            return now < end_date_utc
        return now < self.end_date


class OrderBookLevel(BaseModel):
    """Single level in the order book."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    price: Decimal = Field(..., description="Price in USD (0-1 range)")
    size: Decimal = Field(..., description="Size in USD")
    
    @property
    def total_value(self) -> Decimal:
        """Calculate total value of this level."""
        return self.price * self.size


class OrderBook(BaseModel):
    """Order book for a specific outcome token."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    token_id: str = Field(..., description="Token ID")
    outcome: OutcomeType = Field(..., description="YES or NO outcome")
    bids: List[OrderBookLevel] = Field(default_factory=list, description="Bid levels")
    asks: List[OrderBookLevel] = Field(default_factory=list, description="Ask levels")
    timestamp: datetime = Field(default_factory=datetime.now, description="Snapshot time")
    
    @property
    def best_bid(self) -> Optional[OrderBookLevel]:
        """Get best bid (highest price)."""
        return self.bids[0] if self.bids else None
    
    @property
    def best_ask(self) -> Optional[OrderBookLevel]:
        """Get best ask (lowest price)."""
        return self.asks[0] if self.asks else None
    
    @property
    def best_bid_price(self) -> Decimal:
        """Get best bid price or 0."""
        return self.best_bid.price if self.best_bid else Decimal("0")
    
    @property
    def best_ask_price(self) -> Decimal:
        """Get best ask price or 1."""
        return self.best_ask.price if self.best_ask else Decimal("1")
    
    @property
    def spread(self) -> Decimal:
        """Calculate bid-ask spread."""
        if self.best_bid and self.best_ask:
            return self.best_ask.price - self.best_bid.price
        return Decimal("1")
    
    @property
    def top_of_book_liquidity(self) -> Decimal:
        """Calculate liquidity at best price."""
        bid_size = self.best_bid.size if self.best_bid else Decimal("0")
        ask_size = self.best_ask.size if self.best_ask else Decimal("0")
        return min(bid_size, ask_size)


class ArbitrageOpportunity(BaseModel):
    """Detected arbitrage opportunity."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    market: Market = Field(..., description="Market details")
    yes_orderbook: OrderBook = Field(..., description="YES outcome orderbook")
    no_orderbook: OrderBook = Field(..., description="NO outcome orderbook")
    
    yes_ask: Decimal = Field(..., description="Best YES ask price")
    no_ask: Decimal = Field(..., description="Best NO ask price")
    
    gross_edge: Decimal = Field(..., description="Gross arbitrage edge")
    estimated_gas: Decimal = Field(..., description="Estimated gas cost")
    net_profit: Decimal = Field(..., description="Net profit after costs")
    position_size: Decimal = Field(..., description="Recommended position size")
    
    liquidity: Decimal = Field(..., description="Available liquidity")
    apy: Decimal = Field(..., description="Annualized percentage yield")
    roi: Decimal = Field(..., description="Return on investment")
    
    detected_at: datetime = Field(default_factory=datetime.now, description="Detection time")
    
    @property
    def sum_asks(self) -> Decimal:
        """Calculate YES_ask + NO_ask."""
        return self.yes_ask + self.no_ask
    
    @property
    def is_profitable(self) -> bool:
        """Check if opportunity is profitable after costs."""
        return self.net_profit > Decimal("0")
    
    @property
    def confidence_score(self) -> Decimal:
        """Calculate confidence score (0-100) based on liquidity and edge."""
        liquidity_score = min(Decimal("50"), self.liquidity)
        edge_score = min(Decimal("50"), self.gross_edge * Decimal("1000"))
        return liquidity_score + edge_score


class Order(BaseModel):
    """Trading order model."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    id: Optional[str] = Field(None, description="Order ID from exchange")
    token_id: str = Field(..., description="Token ID")
    outcome: OutcomeType = Field(..., description="YES or NO")
    side: OrderSide = Field(..., description="BUY or SELL")
    price: Decimal = Field(..., description="Order price")
    size: Decimal = Field(..., description="Order size in USD")
    status: OrderStatus = Field(default=OrderStatus.PENDING, description="Order status")
    
    filled_size: Decimal = Field(default=Decimal("0"), description="Filled size")
    average_price: Optional[Decimal] = Field(None, description="Average fill price")
    
    created_at: datetime = Field(default_factory=datetime.now, description="Order creation time")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update time")
    
    @property
    def is_filled(self) -> bool:
        """Check if order is fully filled."""
        return self.status == OrderStatus.FILLED
    
    @property
    def is_partially_filled(self) -> bool:
        """Check if order is partially filled."""
        return self.filled_size > Decimal("0") and self.filled_size < self.size
    
    @property
    def remaining_size(self) -> Decimal:
        """Calculate remaining unfilled size."""
        return self.size - self.filled_size


class Fill(BaseModel):
    """Order fill execution."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    id: str = Field(..., description="Fill ID")
    order_id: str = Field(..., description="Associated order ID")
    token_id: str = Field(..., description="Token ID")
    outcome: OutcomeType = Field(..., description="YES or NO")
    side: OrderSide = Field(..., description="BUY or SELL")
    
    price: Decimal = Field(..., description="Fill price")
    size: Decimal = Field(..., description="Fill size")
    fee: Decimal = Field(default=Decimal("0"), description="Trading fee")
    gas_cost: Decimal = Field(default=Decimal("0"), description="Gas cost")
    
    timestamp: datetime = Field(default_factory=datetime.now, description="Fill time")
    transaction_hash: Optional[str] = Field(None, description="Blockchain tx hash")
    
    @property
    def total_cost(self) -> Decimal:
        """Calculate total cost including fees."""
        return (self.price * self.size) + self.fee + self.gas_cost


class Position(BaseModel):
    """Open position in a market."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    market_id: str = Field(..., description="Market ID")
    token_id: str = Field(..., description="Token ID")
    outcome: OutcomeType = Field(..., description="YES or NO")
    
    size: Decimal = Field(..., description="Position size")
    average_entry_price: Decimal = Field(..., description="Average entry price")
    total_cost: Decimal = Field(..., description="Total cost including fees")
    
    current_price: Optional[Decimal] = Field(None, description="Current market price")
    unrealized_pnl: Optional[Decimal] = Field(None, description="Unrealized PnL")
    
    opened_at: datetime = Field(default_factory=datetime.now, description="Position open time")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update time")
    
    def update_market_price(self, price: Decimal) -> None:
        """Update current price and recalculate unrealized PnL."""
        self.current_price = price
        market_value = price * self.size
        self.unrealized_pnl = market_value - self.total_cost
        self.updated_at = datetime.now()


class PnLEntry(BaseModel):
    """PnL ledger entry."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    id: Optional[int] = Field(None, description="Entry ID")
    market_id: str = Field(..., description="Market ID")
    
    realized_pnl: Decimal = Field(..., description="Realized profit/loss")
    fees_paid: Decimal = Field(..., description="Total fees paid")
    gas_paid: Decimal = Field(..., description="Total gas paid")
    
    entry_cost: Decimal = Field(..., description="Total entry cost")
    exit_value: Decimal = Field(..., description="Total exit value")
    
    positions_closed: int = Field(default=1, description="Number of positions closed")
    timestamp: datetime = Field(default_factory=datetime.now, description="Entry time")
    
    notes: Optional[str] = Field(None, description="Additional notes")
    
    @property
    def net_pnl(self) -> Decimal:
        """Calculate net PnL after all costs."""
        return self.realized_pnl - self.fees_paid - self.gas_paid
    
    @property
    def roi(self) -> Decimal:
        """Calculate return on investment percentage."""
        if self.entry_cost > Decimal("0"):
            return (self.net_pnl / self.entry_cost) * Decimal("100")
        return Decimal("0")


class TradePair(BaseModel):
    """A pair of orders for YES+NO arbitrage."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    opportunity: ArbitrageOpportunity = Field(..., description="Associated opportunity")
    yes_order: Order = Field(..., description="YES leg order")
    no_order: Order = Field(..., description="NO leg order")
    
    created_at: datetime = Field(default_factory=datetime.now, description="Pair creation time")
    
    @property
    def is_fully_filled(self) -> bool:
        """Check if both legs are fully filled."""
        return self.yes_order.is_filled and self.no_order.is_filled
    
    @property
    def is_partially_filled(self) -> bool:
        """Check if only one leg is filled."""
        return (self.yes_order.is_filled and not self.no_order.is_filled) or \
               (self.no_order.is_filled and not self.yes_order.is_filled)
    
    @property
    def total_filled_size(self) -> Decimal:
        """Get total filled size across both legs."""
        return self.yes_order.filled_size + self.no_order.filled_size

