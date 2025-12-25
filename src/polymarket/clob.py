"""
Polymarket CLOB (Central Limit Order Book) API client.
Handles orderbook fetching and order execution.
API docs: https://docs.polymarket.com/#clob-api
"""
import logging
import time
from decimal import Decimal
from typing import List, Optional, Dict, Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct

from ..core.models import (
    OrderBook, OrderBookLevel, Order, OrderSide, 
    OrderStatus, OutcomeType
)

logger = logging.getLogger(__name__)


class CLOBClient:
    """Client for Polymarket CLOB API."""
    
    BASE_URL = "https://clob.polymarket.com"
    CHAIN_ID = 137  # Polygon mainnet
    
    def __init__(
        self,
        private_key: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize CLOB API client.
        
        Args:
            private_key: Polygon private key for signing transactions
            api_key: Optional API key
            timeout: Request timeout in seconds
        """
        self.private_key = private_key
        self.api_key = api_key
        self.timeout = timeout
        
        # Initialize Web3 account if private key provided
        self.account = None
        if private_key:
            try:
                self.account = Account.from_key(private_key)
                logger.info(f"Initialized account: {self.account.address}")
            except Exception as e:
                logger.error(f"Failed to initialize account: {e}")
        
        # Setup HTTP client
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=timeout,
            headers=headers
        )
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True
    )
    async def _get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """Make GET request with retry logic."""
        try:
            response = await self.client.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching {endpoint}: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error fetching {endpoint}: {e}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True
    )
    async def _post(self, endpoint: str, data: dict) -> dict:
        """Make POST request with retry logic."""
        try:
            response = await self.client.post(endpoint, json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error posting to {endpoint}: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error posting to {endpoint}: {e}")
            raise
    
    async def get_orderbook(
        self,
        token_id: str,
        outcome: OutcomeType,
        depth: int = 10
    ) -> OrderBook:
        """
        Fetch orderbook for a specific token.
        
        Args:
            token_id: Token identifier
            outcome: YES or NO outcome
            depth: Number of levels to fetch
            
        Returns:
            OrderBook instance
        """
        try:
            # CLOB API endpoint structure
            params = {"token_id": token_id}
            data = await self._get("/book", params=params)
            
            # Parse bids and asks
            bids = []
            asks = []
            
            # API returns structure like: {"bids": [{"price": "0.5", "size": "100"}, ...], "asks": [...]}
            raw_bids = data.get("bids", [])[:depth]
            raw_asks = data.get("asks", [])[:depth]
            
            for bid in raw_bids:
                # Handle both dictionary format {"price": "0.5", "size": "100"} and array format ["0.5", "100"]
                if isinstance(bid, dict):
                    price = bid.get("price")
                    size = bid.get("size")
                elif isinstance(bid, (list, tuple)) and len(bid) >= 2:
                    price = bid[0]
                    size = bid[1]
                else:
                    continue
                
                if price is not None and size is not None:
                    bids.append(OrderBookLevel(
                        price=Decimal(str(price)),
                        size=Decimal(str(size))
                    ))
            
            for ask in raw_asks:
                # Handle both dictionary format and array format
                if isinstance(ask, dict):
                    price = ask.get("price")
                    size = ask.get("size")
                elif isinstance(ask, (list, tuple)) and len(ask) >= 2:
                    price = ask[0]
                    size = ask[1]
                else:
                    continue
                
                if price is not None and size is not None:
                    asks.append(OrderBookLevel(
                        price=Decimal(str(price)),
                        size=Decimal(str(size))
                    ))
            
            orderbook = OrderBook(
                token_id=token_id,
                outcome=outcome,
                bids=bids,
                asks=asks
            )
            
            logger.debug(
                f"Fetched orderbook for {token_id}: "
                f"best_bid={orderbook.best_bid_price}, "
                f"best_ask={orderbook.best_ask_price}"
            )
            
            return orderbook
            
        except Exception as e:
            logger.error(f"Failed to fetch orderbook for {token_id}: {e}", exc_info=True)
            # Return empty orderbook on error
            return OrderBook(token_id=token_id, outcome=outcome, bids=[], asks=[])
    
    def _sign_order(self, order_data: Dict[str, Any]) -> str:
        """
        Sign order data with private key.
        
        Args:
            order_data: Order parameters
            
        Returns:
            Signature string
        """
        if not self.account:
            raise ValueError("No account initialized - private key required")
        
        # Create message to sign (simplified - actual implementation may vary)
        message = encode_defunct(text=str(order_data))
        signed = self.account.sign_message(message)
        return signed.signature.hex()
    
    async def place_limit_order(
        self,
        token_id: str,
        outcome: OutcomeType,
        side: OrderSide,
        price: Decimal,
        size: Decimal
    ) -> Optional[Order]:
        """
        Place a limit order on the CLOB.
        
        Args:
            token_id: Token identifier
            outcome: YES or NO
            side: BUY or SELL
            price: Limit price (0-1 range)
            size: Order size in USD
            
        Returns:
            Order instance or None if failed
        """
        if not self.account:
            logger.error("Cannot place order: no account initialized")
            return None
        
        try:
            # Validate inputs
            if not (Decimal("0") < price < Decimal("1")):
                logger.error(f"Invalid price: {price} (must be 0-1)")
                return None
            
            if size <= Decimal("0"):
                logger.error(f"Invalid size: {size}")
                return None
            
            # Create order data
            order_data = {
                "token_id": token_id,
                "side": side.value,
                "price": str(price),
                "size": str(size),
                "timestamp": int(time.time()),
                "nonce": int(time.time() * 1000)
            }
            
            # Sign order
            signature = self._sign_order(order_data)
            order_data["signature"] = signature
            
            # Submit order
            response = await self._post("/order", order_data)
            
            # Parse response
            order_id = response.get("order_id") or response.get("id")
            
            order = Order(
                id=order_id,
                token_id=token_id,
                outcome=outcome,
                side=side,
                price=price,
                size=size,
                status=OrderStatus.PENDING
            )
            
            logger.info(
                f"Placed order {order_id}: {side.value} {size} @ {price} "
                f"for {outcome.value} token {token_id}"
            )
            
            return order
            
        except Exception as e:
            logger.error(f"Failed to place order: {e}", exc_info=True)
            return None
    
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an open order.
        
        Args:
            order_id: Order identifier
            
        Returns:
            True if cancelled successfully
        """
        try:
            response = await self._post(f"/cancel", {"order_id": order_id})
            success = response.get("success", False)
            
            if success:
                logger.info(f"Cancelled order {order_id}")
            else:
                logger.warning(f"Failed to cancel order {order_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    async def get_order_status(self, order_id: str) -> Optional[Order]:
        """
        Check order fill status.
        
        Args:
            order_id: Order identifier
            
        Returns:
            Updated Order instance or None
        """
        try:
            data = await self._get(f"/order/{order_id}")
            
            # Parse status
            status_str = data.get("status", "").upper()
            status_map = {
                "OPEN": OrderStatus.PENDING,
                "FILLED": OrderStatus.FILLED,
                "PARTIAL": OrderStatus.PARTIALLY_FILLED,
                "CANCELLED": OrderStatus.CANCELLED,
                "FAILED": OrderStatus.FAILED
            }
            status = status_map.get(status_str, OrderStatus.PENDING)
            
            # Parse filled size
            filled_size = Decimal(str(data.get("filled_size", 0)))
            avg_price = data.get("average_price")
            
            # Reconstruct order (limited info from status check)
            order = Order(
                id=order_id,
                token_id=data.get("token_id", ""),
                outcome=OutcomeType.YES,  # Would need to track this
                side=OrderSide.BUY,  # Would need to track this
                price=Decimal(str(data.get("price", 0))),
                size=Decimal(str(data.get("size", 0))),
                status=status,
                filled_size=filled_size,
                average_price=Decimal(str(avg_price)) if avg_price else None
            )
            
            logger.debug(f"Order {order_id} status: {status.value}, filled: {filled_size}")
            return order
            
        except Exception as e:
            logger.error(f"Failed to get order status for {order_id}: {e}")
            return None
    
    async def get_fills(self, order_id: str) -> List[dict]:
        """
        Get fill history for an order.
        
        Args:
            order_id: Order identifier
            
        Returns:
            List of fill dictionaries
        """
        try:
            data = await self._get(f"/fills/{order_id}")
            fills = data.get("fills", [])
            logger.debug(f"Found {len(fills)} fills for order {order_id}")
            return fills
        except Exception as e:
            logger.error(f"Failed to get fills for {order_id}: {e}")
            return []
    
    async def get_positions(self) -> List[dict]:
        """
        Get current open positions.
        
        Returns:
            List of position dictionaries
        """
        if not self.account:
            logger.error("Cannot get positions: no account initialized")
            return []
        
        try:
            params = {"address": self.account.address}
            data = await self._get("/positions", params=params)
            positions = data.get("positions", [])
            logger.info(f"Found {len(positions)} open positions")
            return positions
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []

