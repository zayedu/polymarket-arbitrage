"""
Market scanner for detecting arbitrage opportunities.
Scans YES+NO orderbooks to find mispricings where sum != $1.00.
"""
import logging
import asyncio
from decimal import Decimal
from datetime import datetime
from typing import List, Optional

from config import Config
from ..polymarket.gamma import GammaClient
from ..polymarket.clob import CLOBClient
from .models import (
    Market, OrderBook, ArbitrageOpportunity, OutcomeType
)

logger = logging.getLogger(__name__)


class Scanner:
    """Scans prediction markets for arbitrage opportunities."""
    
    def __init__(
        self,
        config: Config,
        gamma_client: GammaClient,
        clob_client: CLOBClient
    ):
        """
        Initialize scanner with API clients.
        
        Args:
            config: Application configuration
            gamma_client: Gamma API client
            clob_client: CLOB API client
        """
        self.config = config
        self.gamma = gamma_client
        self.clob = clob_client
    
    async def fetch_market_orderbooks(
        self,
        market: Market
    ) -> tuple[Optional[OrderBook], Optional[OrderBook]]:
        """
        Fetch orderbooks for both YES and NO tokens.
        
        Args:
            market: Market to fetch orderbooks for
            
        Returns:
            Tuple of (yes_orderbook, no_orderbook)
        """
        try:
            # Add small delay to avoid rate limiting (50ms between markets)
            await asyncio.sleep(0.05)
            
            # Fetch both orderbooks concurrently
            yes_ob_task = self.clob.get_orderbook(
                market.yes_token_id,
                OutcomeType.YES
            )
            no_ob_task = self.clob.get_orderbook(
                market.no_token_id,
                OutcomeType.NO
            )
            
            yes_ob, no_ob = await asyncio.gather(yes_ob_task, no_ob_task)
            
            return yes_ob, no_ob
            
        except Exception as e:
            logger.error(f"Failed to fetch orderbooks for market {market.id}: {e}")
            return None, None
    
    def detect_arbitrage(
        self,
        market: Market,
        yes_orderbook: OrderBook,
        no_orderbook: OrderBook
    ) -> Optional[ArbitrageOpportunity]:
        """
        Detect arbitrage opportunity in a market.
        
        Checks if YES_ask + NO_ask < $1.00 (long arbitrage).
        
        Args:
            market: Market details
            yes_orderbook: YES outcome orderbook
            no_orderbook: NO outcome orderbook
            
        Returns:
            ArbitrageOpportunity if found, None otherwise
        """
        # Check if we have valid orderbooks
        if not yes_orderbook.best_ask or not no_orderbook.best_ask:
            logger.debug(f"Market {market.id}: Missing best ask prices")
            return None
        
        yes_ask = yes_orderbook.best_ask_price
        no_ask = no_orderbook.best_ask_price
        sum_asks = yes_ask + no_ask
        
        # LOG EVERY MARKET PRICE (temporarily for debugging)
        logger.info(
            f"📊 {market.title[:60]}: YES={yes_ask:.4f} + NO={no_ask:.4f} = {sum_asks:.4f} "
            f"(edge={Decimal('1.0')-sum_asks:.4f})"
        )
        
        # Check for long arbitrage: sum < 1.0
        if sum_asks >= Decimal("1.0"):
            return None
        
        # Calculate gross edge
        gross_edge = Decimal("1.0") - sum_asks
        
        # Check minimum edge threshold
        if gross_edge < self.config.min_gross_edge:
            logger.debug(
                f"Market {market.id}: Edge {gross_edge} < threshold {self.config.min_gross_edge}"
            )
            return None
        
        # Calculate available liquidity (minimum of YES and NO top-of-book)
        yes_liquidity = yes_orderbook.best_ask.size if yes_orderbook.best_ask else Decimal("0")
        no_liquidity = no_orderbook.best_ask.size if no_orderbook.best_ask else Decimal("0")
        available_liquidity = min(yes_liquidity, no_liquidity)
        
        # Check minimum liquidity threshold
        if available_liquidity < self.config.min_liquidity:
            logger.debug(
                f"Market {market.id}: Liquidity {available_liquidity} < threshold {self.config.min_liquidity}"
            )
            return None
        
        # Calculate position size (limited by liquidity and max trade size)
        position_size = min(
            available_liquidity,
            self.config.max_trade_size
        )
        
        # Estimate gas cost
        estimated_gas = self.config.estimated_gas_cost_usd * Decimal("2")  # 2 transactions
        
        # Calculate net profit
        net_profit = (gross_edge * position_size) - estimated_gas
        
        # Check minimum net profit threshold
        if net_profit < self.config.min_net_profit:
            logger.debug(
                f"Market {market.id}: Net profit {net_profit} < threshold {self.config.min_net_profit}"
            )
            return None
        
        # Calculate ROI and APY
        total_cost = sum_asks * position_size
        roi = (net_profit / total_cost) * Decimal("100") if total_cost > 0 else Decimal("0")
        
        # Calculate APY
        days_to_resolution = max(market.days_to_resolution, 1)
        apy = (gross_edge / Decimal(str(days_to_resolution))) * Decimal("365") * Decimal("100")
        
        # Check minimum APY threshold
        if apy < self.config.min_apy:
            logger.debug(
                f"Market {market.id}: APY {apy}% < threshold {self.config.min_apy}%"
            )
            return None
        
        # Create opportunity
        opportunity = ArbitrageOpportunity(
            market=market,
            yes_orderbook=yes_orderbook,
            no_orderbook=no_orderbook,
            yes_ask=yes_ask,
            no_ask=no_ask,
            gross_edge=gross_edge,
            estimated_gas=estimated_gas,
            net_profit=net_profit,
            position_size=position_size,
            liquidity=available_liquidity,
            apy=apy,
            roi=roi
        )
        
        logger.info(
            f"📊 Arbitrage found in {market.title[:50]}: "
            f"Edge={gross_edge:.4f}, Net={net_profit:.2f}, APY={apy:.1f}%"
        )
        
        return opportunity
    
    async def scan_market(self, market: Market) -> Optional[ArbitrageOpportunity]:
        """
        Scan a single market for arbitrage opportunities.
        
        Args:
            market: Market to scan
            
        Returns:
            ArbitrageOpportunity if found, None otherwise
        """
        try:
            # Fetch orderbooks
            yes_ob, no_ob = await self.fetch_market_orderbooks(market)
            
            if yes_ob is None or no_ob is None:
                return None
            
            # Detect arbitrage
            opportunity = self.detect_arbitrage(market, yes_ob, no_ob)
            
            return opportunity
            
        except Exception as e:
            logger.error(f"Error scanning market {market.id}: {e}", exc_info=True)
            return None
    
    async def scan_markets(
        self,
        markets: Optional[List[Market]] = None
    ) -> List[ArbitrageOpportunity]:
        """
        Scan multiple markets for arbitrage opportunities.
        
        Args:
            markets: List of markets to scan (fetches active markets if None)
            
        Returns:
            List of detected arbitrage opportunities
        """
        # Fetch active markets if not provided
        if markets is None:
            logger.info("Fetching active markets...")
            markets = await self.gamma.get_active_markets(
                min_volume=Decimal("100"),  # $100 min volume
                max_days_to_resolution=self.config.max_days_to_resolution,
                limit=100  # Start with 100 markets to avoid rate limiting
            )
            logger.info(f"Found {len(markets)} active markets to scan")
        
        if not markets:
            logger.warning("No markets to scan")
            return []
        
        # Scan all markets concurrently
        logger.info(f"Scanning {len(markets)} markets...")
        scan_tasks = [self.scan_market(market) for market in markets]
        results = await asyncio.gather(*scan_tasks, return_exceptions=True)
        
        # Filter out None and exceptions
        opportunities = []
        for result in results:
            if isinstance(result, ArbitrageOpportunity):
                opportunities.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Scan task failed: {result}")
        
        logger.info(f"Found {len(opportunities)} arbitrage opportunities")
        return opportunities
    
    def rank_opportunities(
        self,
        opportunities: List[ArbitrageOpportunity]
    ) -> List[ArbitrageOpportunity]:
        """
        Rank arbitrage opportunities by quality.
        
        Ranking criteria (in order of priority):
        1. APY (higher is better)
        2. Net profit (higher is better)
        3. Liquidity (higher is better)
        
        Args:
            opportunities: List of opportunities to rank
            
        Returns:
            Sorted list of opportunities (best first)
        """
        if not opportunities:
            return []
        
        # Sort by multiple criteria
        sorted_opps = sorted(
            opportunities,
            key=lambda opp: (
                -opp.apy,  # Higher APY first (negative for descending)
                -opp.net_profit,  # Higher profit first
                -opp.liquidity  # Higher liquidity first
            )
        )
        
        logger.info(f"Ranked {len(sorted_opps)} opportunities")
        return sorted_opps
    
    async def scan_and_rank(
        self,
        markets: Optional[List[Market]] = None
    ) -> List[ArbitrageOpportunity]:
        """
        Scan markets and return ranked opportunities.
        
        Args:
            markets: Optional list of markets to scan
            
        Returns:
            Ranked list of arbitrage opportunities
        """
        opportunities = await self.scan_markets(markets)
        ranked = self.rank_opportunities(opportunities)
        
        if ranked:
            logger.info(
                f"🎯 Top opportunity: {ranked[0].market.title[:50]} "
                f"(APY={ranked[0].apy:.1f}%, Net=${ranked[0].net_profit:.2f})"
            )
        
        return ranked
    
    async def continuous_scan(
        self,
        interval_seconds: Optional[int] = None,
        max_iterations: Optional[int] = None
    ) -> None:
        """
        Continuously scan markets at regular intervals.
        
        Args:
            interval_seconds: Seconds between scans (uses config if None)
            max_iterations: Maximum iterations (None for infinite)
        """
        interval = interval_seconds or self.config.poll_interval_seconds
        iteration = 0
        
        logger.info(f"Starting continuous scan (interval={interval}s)")
        
        try:
            while max_iterations is None or iteration < max_iterations:
                iteration += 1
                logger.info(f"=== Scan iteration {iteration} ===")
                
                try:
                    opportunities = await self.scan_and_rank()
                    
                    if opportunities:
                        logger.info(f"Found {len(opportunities)} opportunities")
                        # Top opportunity will be logged by scan_and_rank
                    else:
                        logger.info("No arbitrage opportunities found")
                    
                except Exception as e:
                    logger.error(f"Error in scan iteration: {e}", exc_info=True)
                
                # Wait before next iteration
                if max_iterations is None or iteration < max_iterations:
                    await asyncio.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("Continuous scan interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error in continuous scan: {e}", exc_info=True)
            raise

