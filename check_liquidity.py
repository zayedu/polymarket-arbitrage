"""Quick script to check which markets actually have liquidity."""
import asyncio
import sys
from decimal import Decimal

from config import get_config
from src.polymarket.gamma import GammaClient
from src.polymarket.clob import CLOBClient
from src.core.models import OutcomeType


async def main():
    config = get_config()
    
    async with GammaClient() as gamma:
        async with CLOBClient() as clob:
            print("Fetching markets...")
            markets = await gamma.get_active_markets(
                min_volume=Decimal("1000"),  # Higher volume = more liquid
                max_days_to_resolution=30,
                limit=50  # Top 50 most active markets
            )
            
            print(f"\nChecking liquidity for {len(markets)} high-volume markets...\n")
            
            liquid_count = 0
            for i, market in enumerate(markets):
                yes_ob = await clob.get_orderbook(market.yes_token_id, OutcomeType.YES)
                no_ob = await clob.get_orderbook(market.no_token_id, OutcomeType.NO)
                
                yes_liquidity = len(yes_ob.asks)
                no_liquidity = len(no_ob.asks)
                
                if yes_liquidity > 0 and no_liquidity > 0:
                    liquid_count += 1
                    yes_ask = yes_ob.best_ask_price
                    no_ask = no_ob.best_ask_price
                    sum_price = yes_ask + no_ask
                    edge = Decimal("1.0") - sum_price
                    
                    yes_depth = yes_ob.best_ask.size if yes_ob.best_ask else Decimal("0")
                    no_depth = no_ob.best_ask.size if no_ob.best_ask else Decimal("0")
                    
                    print(f"✅ {market.title[:70]}")
                    print(f"   YES: ${yes_ask:.4f} (depth: ${yes_depth:.2f})")
                    print(f"   NO:  ${no_ask:.4f} (depth: ${no_depth:.2f})")
                    print(f"   Sum: ${sum_price:.4f} (edge: {edge:.4f})")
                    print(f"   Volume: ${market.volume:,.0f} | Days: {market.days_to_resolution}")
                    print()
                else:
                    print(f"❌ {market.title[:70]} - NO LIQUIDITY")
                
                # Rate limit
                await asyncio.sleep(0.1)
            
            print(f"\n{'='*80}")
            print(f"Summary: {liquid_count}/{len(markets)} markets have orderbook liquidity")
            print(f"{'='*80}")
            
            if liquid_count == 0:
                print("\n⚠️  WARNING: NO LIQUID MARKETS FOUND")
                print("This suggests:")
                print("  1. Polymarket has low liquidity right now")
                print("  2. Arbitrage opportunities are rare/don't exist")
                print("  3. You may need to try a different trading strategy")


if __name__ == "__main__":
    asyncio.run(main())

