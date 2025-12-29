"""
Whale Tracker - Monitor high-accuracy wallets and their positions.
Tracks "Alpha" tagged wallets with 65%+ accuracy on Polymarket.
"""
import logging
from typing import List, Dict, Optional, Set
from decimal import Decimal
from datetime import datetime, timezone
import asyncio

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class WhaleProfile(BaseModel):
    """Profile of a high-accuracy trader (whale)."""
    address: str
    username: Optional[str] = None
    accuracy: Decimal = Field(default=Decimal("0"))
    total_trades: int = 0
    profit_loss: Decimal = Field(default=Decimal("0"))
    volume: Decimal = Field(default=Decimal("0"))
    markets_traded: int = 0
    last_active: Optional[datetime] = None
    is_alpha: bool = False  # Has "Alpha" tag (>65% accuracy, >50 trades)


class WhalePosition(BaseModel):
    """A position held by a whale."""
    whale_address: str
    market_id: str
    market_title: str
    outcome: str  # "YES" or "NO"
    shares: Decimal
    avg_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    timestamp: datetime


class WhaleTransaction(BaseModel):
    """A transaction (buy/sell) by a whale."""
    whale_address: str
    market_id: str
    market_title: str
    action: str  # "BUY" or "SELL"
    outcome: str  # "YES" or "NO"
    shares: Decimal
    price: Decimal
    total_cost: Decimal
    timestamp: datetime
    tx_hash: Optional[str] = None


class WhaleTracker:
    """
    Tracks high-accuracy wallets (whales) on Polymarket.
    Monitors their positions and transactions for copy trading.
    """
    
    def __init__(self, gamma_api_url: str = "https://gamma-api.polymarket.com"):
        """
        Initialize whale tracker.
        
        Args:
            gamma_api_url: Polymarket Gamma API base URL
        """
        self.gamma_api_url = gamma_api_url
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # Tracked whales
        self.whales: Dict[str, WhaleProfile] = {}
        self.whale_positions: Dict[str, List[WhalePosition]] = {}  # address -> positions
        self.recent_transactions: List[WhaleTransaction] = []
        
        # Cache for last known positions to detect changes
        self._last_positions: Dict[str, Set[str]] = {}  # address -> set of market_ids
        
        logger.info("🐋 Whale Tracker initialized")
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
    
    async def find_alpha_whales(
        self,
        min_accuracy: Decimal = Decimal("65"),
        min_trades: int = 50,
        limit: int = 20
    ) -> List[WhaleProfile]:
        """
        Find high-accuracy wallets with "Alpha" tag.
        
        Args:
            min_accuracy: Minimum accuracy percentage (default 65%)
            min_trades: Minimum number of trades (default 50)
            limit: Maximum number of whales to return
            
        Returns:
            List of whale profiles meeting criteria
        """
        try:
            logger.info(f"🔍 Searching for Alpha whales (accuracy >={min_accuracy}%, trades >={min_trades})...")
            
            # Polymarket's leaderboard endpoint
            url = f"{self.gamma_api_url}/leaderboard"
            params = {
                "limit": limit * 2,  # Get more to filter
                "order": "accuracy",  # Sort by accuracy
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            whales = []
            for user_data in data.get("users", []):
                try:
                    accuracy = Decimal(str(user_data.get("accuracy", 0))) * Decimal("100")
                    total_trades = int(user_data.get("trades", 0))
                    
                    # Filter by criteria
                    if accuracy >= min_accuracy and total_trades >= min_trades:
                        whale = WhaleProfile(
                            address=user_data.get("address", ""),
                            username=user_data.get("username"),
                            accuracy=accuracy,
                            total_trades=total_trades,
                            profit_loss=Decimal(str(user_data.get("profit_loss", 0))),
                            volume=Decimal(str(user_data.get("volume", 0))),
                            markets_traded=int(user_data.get("markets_traded", 0)),
                            is_alpha=True
                        )
                        whales.append(whale)
                        
                        if len(whales) >= limit:
                            break
                            
                except (ValueError, KeyError) as e:
                    logger.debug(f"Skipping invalid user data: {e}")
                    continue
            
            logger.info(f"✅ Found {len(whales)} Alpha whales")
            return whales
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error finding whales: {e}")
            return []
        except Exception as e:
            logger.error(f"Error finding whales: {e}", exc_info=True)
            return []
    
    async def add_whale(self, address: str, profile: Optional[WhaleProfile] = None):
        """
        Add a whale to track.
        
        Args:
            address: Wallet address to track
            profile: Optional whale profile (will fetch if not provided)
        """
        if address in self.whales:
            logger.info(f"Whale {address[:8]}... already tracked")
            return
        
        if profile:
            self.whales[address] = profile
        else:
            # Fetch profile
            profile = await self.get_whale_profile(address)
            if profile:
                self.whales[address] = profile
        
        logger.info(f"🐋 Now tracking whale: {address[:8]}... (accuracy: {profile.accuracy if profile else 'unknown'}%)")
    
    async def get_whale_profile(self, address: str) -> Optional[WhaleProfile]:
        """
        Fetch profile for a specific wallet address.
        
        Args:
            address: Wallet address
            
        Returns:
            WhaleProfile or None if not found
        """
        try:
            url = f"{self.gamma_api_url}/users/{address}"
            response = await self.client.get(url)
            
            if response.status_code == 404:
                logger.warning(f"Whale {address[:8]}... not found")
                return None
            
            response.raise_for_status()
            data = response.json()
            
            return WhaleProfile(
                address=address,
                username=data.get("username"),
                accuracy=Decimal(str(data.get("accuracy", 0))) * Decimal("100"),
                total_trades=int(data.get("trades", 0)),
                profit_loss=Decimal(str(data.get("profit_loss", 0))),
                volume=Decimal(str(data.get("volume", 0))),
                markets_traded=int(data.get("markets_traded", 0)),
                is_alpha=data.get("is_alpha", False)
            )
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching whale profile: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching whale profile: {e}")
            return None
    
    async def get_whale_positions(self, address: str) -> List[WhalePosition]:
        """
        Get current positions for a whale.
        
        Args:
            address: Wallet address
            
        Returns:
            List of current positions
        """
        try:
            url = f"{self.gamma_api_url}/users/{address}/positions"
            response = await self.client.get(url)
            
            if response.status_code == 404:
                return []
            
            response.raise_for_status()
            data = response.json()
            
            positions = []
            for pos_data in data.get("positions", []):
                try:
                    position = WhalePosition(
                        whale_address=address,
                        market_id=pos_data.get("market_id", ""),
                        market_title=pos_data.get("market_title", "Unknown"),
                        outcome=pos_data.get("outcome", "YES"),
                        shares=Decimal(str(pos_data.get("shares", 0))),
                        avg_price=Decimal(str(pos_data.get("avg_price", 0))),
                        current_price=Decimal(str(pos_data.get("current_price", 0))),
                        unrealized_pnl=Decimal(str(pos_data.get("unrealized_pnl", 0))),
                        timestamp=datetime.now(timezone.utc)
                    )
                    positions.append(position)
                except (ValueError, KeyError) as e:
                    logger.debug(f"Skipping invalid position: {e}")
                    continue
            
            return positions
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching positions: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []
    
    async def detect_new_positions(self, address: str) -> List[WhalePosition]:
        """
        Detect new positions opened by a whale since last check.
        
        Args:
            address: Wallet address
            
        Returns:
            List of newly opened positions
        """
        current_positions = await self.get_whale_positions(address)
        current_market_ids = {pos.market_id for pos in current_positions}
        
        # Get last known positions
        last_market_ids = self._last_positions.get(address, set())
        
        # Find new positions
        new_market_ids = current_market_ids - last_market_ids
        new_positions = [pos for pos in current_positions if pos.market_id in new_market_ids]
        
        # Update cache
        self._last_positions[address] = current_market_ids
        self.whale_positions[address] = current_positions
        
        return new_positions
    
    async def monitor_whales(self, poll_interval: int = 60) -> List[WhalePosition]:
        """
        Monitor all tracked whales for new positions.
        
        Args:
            poll_interval: Seconds between checks (default 60)
            
        Returns:
            List of all new positions detected
        """
        if not self.whales:
            logger.warning("No whales being tracked. Add whales first.")
            return []
        
        logger.info(f"🔍 Monitoring {len(self.whales)} whales for new positions...")
        
        all_new_positions = []
        
        for address in self.whales.keys():
            try:
                new_positions = await self.detect_new_positions(address)
                
                if new_positions:
                    whale = self.whales[address]
                    logger.info(f"🚨 Whale {whale.username or address[:8]}... opened {len(new_positions)} new position(s)!")
                    
                    for pos in new_positions:
                        logger.info(f"   📊 {pos.outcome} on '{pos.market_title[:50]}' @ ${pos.avg_price:.4f}")
                    
                    all_new_positions.extend(new_positions)
                
                # Rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error monitoring whale {address[:8]}...: {e}")
                continue
        
        if all_new_positions:
            logger.info(f"✅ Total new positions detected: {len(all_new_positions)}")
        else:
            logger.debug("No new positions detected")
        
        return all_new_positions
    
    def get_tracked_whales(self) -> List[WhaleProfile]:
        """Get list of all tracked whales."""
        return list(self.whales.values())
    
    def get_whale_summary(self) -> Dict:
        """Get summary statistics of tracked whales."""
        if not self.whales:
            return {"total_whales": 0}
        
        profiles = list(self.whales.values())
        
        return {
            "total_whales": len(profiles),
            "avg_accuracy": sum(w.accuracy for w in profiles) / len(profiles),
            "total_trades": sum(w.total_trades for w in profiles),
            "total_volume": sum(w.volume for w in profiles),
            "total_pnl": sum(w.profit_loss for w in profiles),
        }

