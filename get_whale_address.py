#!/usr/bin/env python3
"""
Get wallet address from Polymarket profile URL.
Usage: python3 get_whale_address.py <profile_url>
"""
import sys
import asyncio
import httpx
from rich.console import Console

console = Console()


async def get_wallet_address(profile_url: str):
    """Extract wallet address from Polymarket profile."""
    
    # Extract username from URL
    if "@" in profile_url:
        username = profile_url.split("@")[1].split("?")[0]
    else:
        console.print("[red]Invalid profile URL. Should contain @username[/red]")
        return None
    
    console.print(f"[cyan]Looking up wallet for @{username}...[/cyan]")
    
    try:
        # Try Polymarket's user API
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try username endpoint
            url = f"https://gamma-api.polymarket.com/users/{username}"
            console.print(f"[dim]Trying: {url}[/dim]")
            
            response = await client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract wallet address
                wallet = data.get("address") or data.get("wallet") or data.get("id")
                
                if wallet:
                    console.print(f"\n[green]✅ Found wallet address:[/green]")
                    console.print(f"[bold cyan]{wallet}[/bold cyan]")
                    console.print(f"\n[yellow]Add this to your .env:[/yellow]")
                    console.print(f"COPY_WHALE_ADDRESSES={wallet}")
                    return wallet
                else:
                    console.print("[yellow]⚠️  API response doesn't contain wallet address[/yellow]")
                    console.print(f"Response: {data}")
            else:
                console.print(f"[red]❌ API returned {response.status_code}[/red]")
                
                # Provide manual instructions
                console.print("\n[yellow]Manual method:[/yellow]")
                console.print(f"1. Visit: {profile_url}")
                console.print("2. Open browser DevTools (F12)")
                console.print("3. Go to Network tab")
                console.print("4. Refresh the page")
                console.print("5. Look for API calls to 'users' or 'profile'")
                console.print("6. Find the wallet address in the response")
                console.print("\nOR")
                console.print("7. Check the page source for 'address' or '0x...'")
                
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("\n[yellow]Alternative: Check Polygonscan[/yellow]")
        console.print("1. Look for their transactions on Polymarket")
        console.print("2. Find their wallet address on Polygonscan")
    
    return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        console.print("[red]Usage: python3 get_whale_address.py <profile_url>[/red]")
        console.print("[yellow]Example: python3 get_whale_address.py https://polymarket.com/@ilovecircle[/yellow]")
        sys.exit(1)
    
    profile_url = sys.argv[1]
    asyncio.run(get_wallet_address(profile_url))

