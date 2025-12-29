"""
Copy Trader - Automatically copy trades from high-accuracy whales.
Implements proportional sizing, filters, and risk management.
"""
import logging
from typing import List, Optional, Dict
from decimal import Decimal
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from src.ml.whale_tracker import WhaleTracker, WhalePosition, WhaleProfile
from src.core.models import Market
from src.polymarket.gamma import GammaClient
from src.polymarket.clob import CLOBClient
from config import Config

logger = logging.getLogger(__name__)


class CopyTradeSignal(BaseModel):
    """Signal to copy a whale's trade."""
    whale_address: str
    whale_username: Optional[str] = None
    whale_accuracy: Decimal
    market_id: str
    market_title: str
    outcome: str  # "YES" or "NO"
    whale_shares: Decimal
    whale_price: Decimal
    current_price: Decimal
    recommended_shares: Decimal  # Our proportional size
    recommended_capital: Decimal
    confidence_score: Decimal  # 0-100
    timestamp: datetime
    reasons: List[str] = Field(default_factory=list)  # Why we should copy


class CopyTradeFilter:
    """Filters for copy trading to reduce risk."""
    
    def __init__(self, config: Config):
        """
        Initialize copy trade filters.
        
        Args:
            config: Bot configuration
        """
        self.config = config
        
        # Copy trading specific settings - VERY PERMISSIVE (copy everything!)
        self.min_whale_accuracy = Decimal("0")  # No minimum (we trust @ilovecircle)
        self.min_whale_trades = 0  # No minimum trade history required
        self.max_price = Decimal("0.999")  # Accept almost any price (up to 99.9¢)
        self.min_price = Decimal("0.001")  # Accept almost any price (down to 0.1¢)
        self.min_liquidity = Decimal("0")  # No minimum liquidity required
        self.max_copy_size = Decimal("50")  # Max $50 per copy trade
        self.copy_ratio = Decimal("0.01")  # Copy 1% of whale's position
    
    def should_copy(
        self,
        whale: WhaleProfile,
        position: WhalePosition,
        market: Optional[Market] = None,
        current_price: Optional[Decimal] = None
    ) -> tuple[bool, List[str]]:
        """
        Determine if we should copy this whale's position.
        
        Args:
            whale: Whale profile
            position: Whale's position
            market: Market data (optional)
            current_price: Current market price (optional)
            
        Returns:
            (should_copy, reasons) tuple
        """
        reasons = []
        
        # Check whale accuracy
        if whale.accuracy < self.min_whale_accuracy:
            return False, [f"Whale accuracy too low: {whale.accuracy}% < {self.min_whale_accuracy}%"]
        
        # Check whale trade history
        if whale.total_trades < self.min_whale_trades:
            return False, [f"Whale has too few trades: {whale.total_trades} < {self.min_whale_trades}"]
        
        # Check price range
        price = current_price or position.avg_price
        if price > self.max_price:
            return False, [f"Price too high: ${price:.4f} > ${self.max_price:.4f}"]
        if price < self.min_price:
            return False, [f"Price too low: ${price:.4f} < ${self.min_price:.4f}"]
        
        # Check market liquidity if available
        if market and market.volume < self.min_liquidity:
            return False, [f"Market liquidity too low: ${market.volume:.2f} < ${self.min_liquidity:.2f}"]
        
        # Check if market is still active
        if market and market.days_to_resolution <= 0:
            return False, ["Market has already resolved"]
        
        # All checks passed
        reasons.append(f"Whale accuracy: {whale.accuracy:.1f}%")
        reasons.append(f"Whale trades: {whale.total_trades}")
        reasons.append(f"Price: ${price:.4f}")
        if market:
            reasons.append(f"Market volume: ${market.volume:.0f}")
            reasons.append(f"Days to resolution: {market.days_to_resolution}")
        
        return True, reasons


class CopyTrader:
    """
    Automatically copies trades from high-accuracy whales.
    """
    
    def __init__(
        self,
        config: Config,
        whale_tracker: WhaleTracker,
        gamma: GammaClient,
        clob: CLOBClient
    ):
        """
        Initialize copy trader.
        
        Args:
            config: Bot configuration
            whale_tracker: Whale tracker instance
            gamma: Gamma API client
            clob: CLOB API client
        """
        self.config = config
        self.whale_tracker = whale_tracker
        self.gamma = gamma
        self.clob = clob
        self.filter = CopyTradeFilter(config)
        
        # Track what we've copied to avoid duplicates
        self.copied_positions: Dict[str, datetime] = {}  # market_id -> timestamp
        
        logger.info("📋 Copy Trader initialized")
    
    def calculate_copy_size(
        self,
        whale_shares: Decimal,
        whale_price: Decimal,
        current_price: Decimal
    ) -> tuple[Decimal, Decimal]:
        """
        Calculate how many shares to buy based on whale's position.
        
        Args:
            whale_shares: Number of shares whale bought
            whale_price: Price whale paid
            current_price: Current market price
            
        Returns:
            (shares_to_buy, capital_required) tuple
        """
        # Calculate whale's capital deployed
        whale_capital = whale_shares * whale_price
        
        # Copy a proportional amount (default 1% of whale's size)
        our_capital = whale_capital * self.filter.copy_ratio
        
        # Cap at max copy size
        our_capital = min(our_capital, self.filter.max_copy_size)
        
        # Calculate shares at current price
        our_shares = our_capital / current_price if current_price > 0 else Decimal("0")
        
        return our_shares, our_capital
    
    def calculate_confidence(
        self,
        whale: WhaleProfile,
        position: WhalePosition,
        market: Optional[Market] = None
    ) -> Decimal:
        """
        Calculate confidence score (0-100) for copying this trade.
        
        Args:
            whale: Whale profile
            position: Whale's position
            market: Market data (optional)
            
        Returns:
            Confidence score (0-100)
        """
        score = Decimal("0")
        
        # Whale accuracy (0-40 points)
        accuracy_score = (whale.accuracy / Decimal("100")) * Decimal("40")
        score += accuracy_score
        
        # Whale trade history (0-20 points)
        trade_score = min(Decimal("20"), (Decimal(str(whale.total_trades)) / Decimal("100")) * Decimal("20"))
        score += trade_score
        
        # Whale profitability (0-20 points)
        if whale.profit_loss > 0:
            pnl_score = min(Decimal("20"), (whale.profit_loss / Decimal("1000")) * Decimal("20"))
            score += pnl_score
        
        # Market liquidity (0-20 points)
        if market:
            liquidity_score = min(Decimal("20"), (market.volume / Decimal("10000")) * Decimal("20"))
            score += liquidity_score
        
        return min(score, Decimal("100"))
    
    async def generate_copy_signals(
        self,
        new_positions: List[WhalePosition]
    ) -> List[CopyTradeSignal]:
        """
        Generate copy trade signals from whale positions.
        
        Args:
            new_positions: List of new whale positions
            
        Returns:
            List of copy trade signals
        """
        signals = []
        
        # Fetch all active markets once and build a lookup by condition_id
        logger.info(f"Fetching active markets for position matching...")
        from decimal import Decimal
        all_markets = await self.gamma.get_active_markets(
            min_volume=Decimal("10"),
            max_days_to_resolution=365,
            limit=1000
        )
        market_lookup = {m.condition_id: m for m in all_markets}
        logger.info(f"Built lookup with {len(market_lookup)} markets")
        
        for position in new_positions:
            try:
                # Skip if we've already copied this market recently
                if position.market_id in self.copied_positions:
                    last_copy = self.copied_positions[position.market_id]
                    time_since = (datetime.now(timezone.utc) - last_copy).total_seconds()
                    if time_since < 3600:  # Don't copy same market within 1 hour
                        logger.debug(f"Skipping {position.market_id} - copied {time_since/60:.0f} minutes ago")
                        continue
                
                # Get whale profile
                whale = self.whale_tracker.whales.get(position.whale_address)
                if not whale:
                    logger.warning(f"Whale {position.whale_address[:8]}... not in tracker")
                    continue
                
                # Get market data from lookup (position.market_id is condition_id)
                market = market_lookup.get(position.market_id)
                if not market:
                    logger.info(f"⚠️  Market {position.market_title[:40]} (condition_id: {position.market_id[:16]}...) not found in active markets")
                    continue
                
                logger.info(f"🔍 Evaluating position: {position.outcome} on '{market.title[:50]}' @ ${position.avg_price}")
                
                # Get current price
                from src.core.models import OutcomeType
                token_id = market.yes_token_id if position.outcome == "YES" else market.no_token_id
                outcome_type = OutcomeType.YES if position.outcome == "YES" else OutcomeType.NO
                orderbook = await self.clob.get_orderbook(token_id, outcome_type)
                current_price = orderbook.best_ask_price if orderbook else position.avg_price
                
                # Apply filters
                should_copy, reasons = self.filter.should_copy(whale, position, market, current_price)
                
                if not should_copy:
                    logger.info(f"❌ Not copying {whale.username or 'whale'}'s position: {reasons[0]}")
                    continue
                
                # Calculate copy size
                our_shares, our_capital = self.calculate_copy_size(
                    position.shares,
                    position.avg_price,
                    current_price
                )
                
                # Calculate confidence
                confidence = self.calculate_confidence(whale, position, market)
                
                # Create signal
                signal = CopyTradeSignal(
                    whale_address=position.whale_address,
                    whale_username=whale.username,
                    whale_accuracy=whale.accuracy,
                    market_id=position.market_id,
                    market_title=position.market_title,
                    outcome=position.outcome,
                    whale_shares=position.shares,
                    whale_price=position.avg_price,
                    current_price=current_price,
                    recommended_shares=our_shares,
                    recommended_capital=our_capital,
                    confidence_score=confidence,
                    timestamp=datetime.now(timezone.utc),
                    reasons=reasons
                )
                
                signals.append(signal)
                logger.info(f"✅ Copy signal: {whale.username or 'whale'} -> {position.outcome} on '{market.title[:40]}' (confidence: {confidence:.0f}%)")
                
            except Exception as e:
                logger.error(f"Error generating copy signal: {e}", exc_info=True)
                continue
        
        return signals
    
    def mark_as_copied(self, market_id: str):
        """Mark a market as copied to avoid duplicates."""
        self.copied_positions[market_id] = datetime.now(timezone.utc)
    
    def get_copy_stats(self) -> Dict:
        """Get copy trading statistics."""
        return {
            "total_copied": len(self.copied_positions),
            "whales_tracked": len(self.whale_tracker.whales),
            "copy_ratio": float(self.filter.copy_ratio),
            "max_copy_size": float(self.filter.max_copy_size),
        }


