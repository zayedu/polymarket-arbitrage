"""
Polymarket Gamma API client for fetching market metadata.
API docs: https://docs.polymarket.com/#gamma-markets-api
"""
import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..core.models import Market

logger = logging.getLogger(__name__)


class GammaClient:
    """Client for Polymarket Gamma API to fetch market data."""
    
    BASE_URL = "https://gamma-api.polymarket.com"
    
    def __init__(self, timeout: int = 30):
        """
        Initialize Gamma API client.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=timeout,
            headers={"Content-Type": "application/json"}
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
        """
        Make GET request with retry logic.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            Response JSON
        """
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
    
    async def get_markets(
        self,
        limit: int = 100,
        offset: int = 0,
        active: bool = True,
        closed: bool = False
    ) -> List[dict]:
        """
        Fetch markets from Gamma API.
        
        Args:
            limit: Maximum number of markets to return
            offset: Pagination offset
            active: Include active markets
            closed: Include closed markets
            
        Returns:
            List of market dictionaries
        """
        params = {
            "limit": limit,
            "offset": offset,
            "active": str(active).lower(),
            "closed": str(closed).lower()
        }
        
        try:
            data = await self._get("/markets", params=params)
            markets = data if isinstance(data, list) else data.get("data", [])
            logger.info(f"Fetched {len(markets)} markets from Gamma API")
            return markets
        except Exception as e:
            logger.error(f"Failed to fetch markets: {e}")
            return []
    
    async def get_market_by_id(self, market_id: str) -> Optional[dict]:
        """
        Fetch detailed market information by ID.
        
        Args:
            market_id: Market identifier
            
        Returns:
            Market dictionary or None if not found
        """
        try:
            data = await self._get(f"/markets/{market_id}")
            logger.debug(f"Fetched market {market_id}")
            return data
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Market {market_id} not found")
                return None
            raise
        except Exception as e:
            logger.error(f"Failed to fetch market {market_id}: {e}")
            return None
    
    def _parse_market(self, data: dict) -> Optional[Market]:
        """
        Parse market data from API response into Market model.
        
        Args:
            data: Market data dictionary
            
        Returns:
            Market instance or None if parsing fails
        """
        try:
            # Extract required fields with fallbacks
            market_id = data.get("id") or data.get("condition_id")
            if not market_id:
                logger.warning("Market missing ID")
                return None
            
            # Parse CLOB token IDs - API returns as JSON string like "[\"id1\", \"id2\"]"
            clob_token_ids_str = data.get("clobTokenIds")
            if clob_token_ids_str:
                try:
                    import json
                    clob_token_ids = json.loads(clob_token_ids_str)
                    if isinstance(clob_token_ids, list) and len(clob_token_ids) >= 2:
                        yes_token_id = str(clob_token_ids[0])
                        no_token_id = str(clob_token_ids[1])
                    else:
                        logger.debug(f"Market {market_id} has invalid clobTokenIds format")
                        return None
                except (json.JSONDecodeError, TypeError) as e:
                    logger.debug(f"Market {market_id} failed to parse clobTokenIds: {e}")
                    return None
            else:
                # Fallback: try old API structure
                tokens = data.get("tokens", [])
                if tokens and len(tokens) >= 2:
                    yes_token = tokens[0]
                    no_token = tokens[1]
                    yes_token_id = yes_token if isinstance(yes_token, str) else yes_token.get("token_id")
                    no_token_id = no_token if isinstance(no_token, str) else no_token.get("token_id")
                else:
                    logger.debug(f"Market {market_id} missing token information")
                    return None
            
            if not yes_token_id or not no_token_id:
                logger.debug(f"Market {market_id} missing token IDs")
                return None
            
            # Basic validation - token IDs should be numeric strings or hex
            if not (yes_token_id.isdigit() or (yes_token_id.startswith("0x") and len(yes_token_id) > 10)):
                logger.debug(f"Market {market_id} has invalid YES token ID: {yes_token_id}")
                return None
            if not (no_token_id.isdigit() or (no_token_id.startswith("0x") and len(no_token_id) > 10)):
                logger.debug(f"Market {market_id} has invalid NO token ID: {no_token_id}")
                return None
            
            # Parse end date
            end_date_str = data.get("end_date") or data.get("endDate") or data.get("end_time")
            if end_date_str:
                try:
                    end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    # Try parsing as timestamp
                    try:
                        end_date = datetime.fromtimestamp(float(end_date_str))
                    except (ValueError, TypeError):
                        logger.warning(f"Market {market_id} invalid end_date: {end_date_str}")
                        end_date = datetime.now()  # Default to now
            else:
                end_date = datetime.now()
            
            # Parse volume
            volume_str = data.get("volume", "0")
            try:
                volume = Decimal(str(volume_str))
            except (ValueError, TypeError):
                volume = Decimal("0")
            
            return Market(
                id=market_id,
                title=data.get("question") or data.get("title") or "Unknown",
                condition_id=data.get("conditionId") or data.get("condition_id", market_id),
                yes_token_id=yes_token_id,
                no_token_id=no_token_id,
                end_date=end_date,
                volume=volume,
                description=data.get("description"),
                resolution_source=data.get("resolution_source"),
                category=data.get("category")
            )
        except Exception as e:
            logger.error(f"Failed to parse market: {e}", exc_info=True)
            return None
    
    async def get_active_markets(
        self,
        min_volume: Decimal = Decimal("1000"),
        max_days_to_resolution: int = 30,
        limit: int = 100
    ) -> List[Market]:
        """
        Fetch active markets filtered by volume and time to resolution.
        
        Args:
            min_volume: Minimum 24h volume in USD
            max_days_to_resolution: Maximum days until resolution
            limit: Maximum number of markets
            
        Returns:
            List of Market instances
        """
        raw_markets = await self.get_markets(limit=limit, active=True, closed=False)
        
        parsed_markets = []
        for raw_market in raw_markets:
            market = self._parse_market(raw_market)
            if market is None:
                continue
            
            # Apply filters
            if market.volume < min_volume:
                logger.debug(f"Skipping {market.id}: volume {market.volume} < {min_volume}")
                continue
            
            if market.days_to_resolution > max_days_to_resolution:
                logger.debug(f"Skipping {market.id}: {market.days_to_resolution} days > {max_days_to_resolution}")
                continue
            
            if not market.is_active:
                logger.debug(f"Skipping {market.id}: market not active")
                continue
            
            parsed_markets.append(market)
        
        logger.info(f"Filtered to {len(parsed_markets)} active markets")
        return parsed_markets
    
    async def get_market(self, market_id: str) -> Optional[Market]:
        """
        Get a single market by ID and parse it.
        
        Args:
            market_id: Market identifier
            
        Returns:
            Market instance or None
        """
        raw_market = await self.get_market_by_id(market_id)
        if raw_market is None:
            return None
        return self._parse_market(raw_market)

