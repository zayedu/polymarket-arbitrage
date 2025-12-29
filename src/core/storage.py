"""
SQLite persistence layer using SQLAlchemy.
Stores markets, orderbook snapshots, orders, fills, positions, and PnL.
"""
import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime, Text,
    ForeignKey, Boolean, Enum as SQLEnum, select
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.pool import StaticPool

from ..core.models import (
    OrderSide, OrderStatus, OutcomeType,
    Market as MarketModel,
    Position as PositionModel,
    PnLEntry as PnLEntryModel
)

logger = logging.getLogger(__name__)

Base = declarative_base()


class MarketDB(Base):
    """Database model for markets."""
    __tablename__ = "markets"
    
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    condition_id = Column(String, nullable=False)
    yes_token_id = Column(String, nullable=False)
    no_token_id = Column(String, nullable=False)
    end_date = Column(DateTime, nullable=False)
    volume = Column(Float, default=0.0)
    description = Column(Text, nullable=True)
    resolution_source = Column(Text, nullable=True)
    category = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    orders = relationship("OrderDB", back_populates="market")
    positions = relationship("PositionDB", back_populates="market")
    pnl_entries = relationship("PnLEntryDB", back_populates="market")


class OrderBookSnapshotDB(Base):
    """Database model for orderbook snapshots."""
    __tablename__ = "orderbook_snapshots"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    token_id = Column(String, nullable=False, index=True)
    outcome = Column(SQLEnum(OutcomeType), nullable=False)
    best_bid = Column(Float, nullable=True)
    best_ask = Column(Float, nullable=True)
    bid_depth = Column(Float, default=0.0)
    ask_depth = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.now, index=True)


class OrderDB(Base):
    """Database model for orders."""
    __tablename__ = "orders"
    
    id = Column(String, primary_key=True)
    market_id = Column(String, ForeignKey("markets.id"), nullable=False, index=True)
    token_id = Column(String, nullable=False)
    outcome = Column(SQLEnum(OutcomeType), nullable=False)
    side = Column(SQLEnum(OrderSide), nullable=False)
    price = Column(Float, nullable=False)
    size = Column(Float, nullable=False)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, index=True)
    filled_size = Column(Float, default=0.0)
    average_price = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.now, index=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    market = relationship("MarketDB", back_populates="orders")
    fills = relationship("FillDB", back_populates="order")


class FillDB(Base):
    """Database model for order fills."""
    __tablename__ = "fills"
    
    id = Column(String, primary_key=True)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False, index=True)
    token_id = Column(String, nullable=False)
    outcome = Column(SQLEnum(OutcomeType), nullable=False)
    side = Column(SQLEnum(OrderSide), nullable=False)
    price = Column(Float, nullable=False)
    size = Column(Float, nullable=False)
    fee = Column(Float, default=0.0)
    gas_cost = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.now, index=True)
    transaction_hash = Column(String, nullable=True)
    
    # Relationships
    order = relationship("OrderDB", back_populates="fills")


class PositionDB(Base):
    """Database model for positions."""
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    market_id = Column(String, ForeignKey("markets.id"), nullable=False, index=True)
    token_id = Column(String, nullable=False)
    outcome = Column(SQLEnum(OutcomeType), nullable=False)
    size = Column(Float, nullable=False)
    average_entry_price = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)
    current_price = Column(Float, nullable=True)
    unrealized_pnl = Column(Float, nullable=True)
    is_closed = Column(Boolean, default=False, index=True)
    opened_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    closed_at = Column(DateTime, nullable=True)
    
    # Relationships
    market = relationship("MarketDB", back_populates="positions")


class PnLEntryDB(Base):
    """Database model for PnL ledger."""
    __tablename__ = "pnl_entries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    market_id = Column(String, ForeignKey("markets.id"), nullable=False, index=True)
    realized_pnl = Column(Float, nullable=False)
    fees_paid = Column(Float, default=0.0)
    gas_paid = Column(Float, default=0.0)
    entry_cost = Column(Float, nullable=False)
    exit_value = Column(Float, nullable=False)
    positions_closed = Column(Integer, default=1)
    timestamp = Column(DateTime, default=datetime.now, index=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    market = relationship("MarketDB", back_populates="pnl_entries")


class Storage:
    """Async storage layer for the arbitrage system."""
    
    def __init__(self, database_url: str):
        """
        Initialize storage with database connection.
        
        Args:
            database_url: SQLAlchemy database URL (async)
        """
        self.database_url = database_url
        
        # Create async engine
        self.engine = create_async_engine(
            database_url,
            echo=False,
            poolclass=StaticPool if "sqlite" in database_url else None
        )
        
        # Create session factory
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        logger.info(f"Initialized storage with database: {database_url}")
    
    async def initialize(self):
        """Create database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")
    
    async def close(self):
        """Close database connections."""
        await self.engine.dispose()
        logger.info("Database connections closed")
    
    # Market operations
    
    async def save_market(self, market: MarketModel) -> None:
        """Save or update a market."""
        async with self.async_session() as session:
            async with session.begin():
                db_market = MarketDB(
                    id=market.id,
                    title=market.title,
                    condition_id=market.condition_id,
                    yes_token_id=market.yes_token_id,
                    no_token_id=market.no_token_id,
                    end_date=market.end_date,
                    volume=float(market.volume),
                    description=market.description,
                    resolution_source=market.resolution_source,
                    category=market.category
                )
                await session.merge(db_market)
        logger.debug(f"Saved market {market.id}")
    
    async def get_market(self, market_id: str) -> Optional[MarketModel]:
        """Retrieve a market by ID."""
        async with self.async_session() as session:
            result = await session.execute(
                select(MarketDB).where(MarketDB.id == market_id)
            )
            db_market = result.scalar_one_or_none()
            
            if db_market:
                return MarketModel(
                    id=db_market.id,
                    title=db_market.title,
                    condition_id=db_market.condition_id,
                    yes_token_id=db_market.yes_token_id,
                    no_token_id=db_market.no_token_id,
                    end_date=db_market.end_date,
                    volume=Decimal(str(db_market.volume)),
                    description=db_market.description,
                    resolution_source=db_market.resolution_source,
                    category=db_market.category
                )
            return None
    
    # Order operations
    
    async def save_order(
        self,
        order: "Order",  # noqa
        market_id: str
    ) -> None:
        """Save or update an order."""
        async with self.async_session() as session:
            async with session.begin():
                db_order = OrderDB(
                    id=order.id,
                    market_id=market_id,
                    token_id=order.token_id,
                    outcome=order.outcome,
                    side=order.side,
                    price=float(order.price),
                    size=float(order.size),
                    status=order.status,
                    filled_size=float(order.filled_size),
                    average_price=float(order.average_price) if order.average_price else None
                )
                await session.merge(db_order)
        logger.debug(f"Saved order {order.id}")
    
    async def get_orders(
        self,
        market_id: Optional[str] = None,
        status: Optional[OrderStatus] = None
    ) -> List[OrderDB]:
        """Retrieve orders with optional filters."""
        async with self.async_session() as session:
            query = select(OrderDB)
            if market_id:
                query = query.where(OrderDB.market_id == market_id)
            if status:
                query = query.where(OrderDB.status == status)
            
            result = await session.execute(query)
            return list(result.scalars().all())
    
    # Position operations
    
    async def save_position(self, position: PositionModel, market_id: str) -> int:
        """Save a new position and return its ID."""
        async with self.async_session() as session:
            async with session.begin():
                db_position = PositionDB(
                    market_id=market_id,
                    token_id=position.token_id,
                    outcome=position.outcome,
                    size=float(position.size),
                    average_entry_price=float(position.average_entry_price),
                    total_cost=float(position.total_cost),
                    current_price=float(position.current_price) if position.current_price else None,
                    unrealized_pnl=float(position.unrealized_pnl) if position.unrealized_pnl else None
                )
                session.add(db_position)
                await session.flush()
                position_id = db_position.id
        
        logger.debug(f"Saved position {position_id} for market {market_id}")
        return position_id
    
    async def get_open_positions(self) -> List[PositionDB]:
        """Get all open positions."""
        async with self.async_session() as session:
            result = await session.execute(
                select(PositionDB).where(PositionDB.is_closed == False)  # noqa
            )
            return list(result.scalars().all())
    
    async def close_position(self, position_id: int) -> None:
        """Mark a position as closed."""
        async with self.async_session() as session:
            async with session.begin():
                result = await session.execute(
                    select(PositionDB).where(PositionDB.id == position_id)
                )
                position = result.scalar_one_or_none()
                if position:
                    position.is_closed = True
                    position.closed_at = datetime.now()
        logger.debug(f"Closed position {position_id}")
    
    # PnL operations
    
    async def save_pnl_entry(self, entry: PnLEntryModel, market_id: str) -> int:
        """Save a PnL entry and return its ID."""
        async with self.async_session() as session:
            async with session.begin():
                db_entry = PnLEntryDB(
                    market_id=market_id,
                    realized_pnl=float(entry.realized_pnl),
                    fees_paid=float(entry.fees_paid),
                    gas_paid=float(entry.gas_paid),
                    entry_cost=float(entry.entry_cost),
                    exit_value=float(entry.exit_value),
                    positions_closed=entry.positions_closed,
                    notes=entry.notes
                )
                session.add(db_entry)
                await session.flush()
                entry_id = db_entry.id
        
        logger.debug(f"Saved PnL entry {entry_id}")
        return entry_id
    
    async def get_pnl_entries(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[PnLEntryDB]:
        """Get PnL entries within date range."""
        async with self.async_session() as session:
            query = select(PnLEntryDB)
            if start_date:
                query = query.where(PnLEntryDB.timestamp >= start_date)
            if end_date:
                query = query.where(PnLEntryDB.timestamp <= end_date)
            query = query.order_by(PnLEntryDB.timestamp.desc())
            
            result = await session.execute(query)
            return list(result.scalars().all())
    
    async def get_total_pnl(self) -> Decimal:
        """Calculate total realized PnL."""
        entries = await self.get_pnl_entries()
        total = sum(
            Decimal(str(e.realized_pnl - e.fees_paid - e.gas_paid))
            for e in entries
        )
        return total



