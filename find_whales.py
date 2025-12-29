#!/usr/bin/env python3
"""
Find Alpha Whales Tool
Discovers high-accuracy traders on Polymarket to copy.
"""
import asyncio
import logging
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.ml.whale_tracker import WhaleTracker

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

console = Console()


async def main():
    """Find and display Alpha whales."""
    console.print(Panel.fit(
        "[bold cyan]🐋 Polymarket Alpha Whale Finder[/bold cyan]\n"
        "Finding high-accuracy traders to copy...",
        border_style="cyan"
    ))
    
    tracker = WhaleTracker()
    
    try:
        # Find Alpha whales
        console.print("\n[yellow]Searching for Alpha whales (>65% accuracy, >50 trades)...[/yellow]")
        whales = await tracker.find_alpha_whales(
            min_accuracy=65,
            min_trades=50,
            limit=20
        )
        
        if not whales:
            console.print("[red]❌ No Alpha whales found. Try lowering criteria.[/red]")
            return
        
        # Display results in table
        table = Table(title=f"\n🐋 Top {len(whales)} Alpha Whales", show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=3)
        table.add_column("Username", style="cyan", width=20)
        table.add_column("Address", style="dim", width=12)
        table.add_column("Accuracy", justify="right", style="green")
        table.add_column("Trades", justify="right")
        table.add_column("P&L", justify="right", style="yellow")
        table.add_column("Volume", justify="right")
        table.add_column("Markets", justify="right")
        
        for i, whale in enumerate(whales, 1):
            table.add_row(
                str(i),
                whale.username or "Anonymous",
                f"{whale.address[:6]}...{whale.address[-4:]}",
                f"{whale.accuracy:.1f}%",
                str(whale.total_trades),
                f"${whale.profit_loss:,.0f}",
                f"${whale.volume:,.0f}",
                str(whale.markets_traded)
            )
        
        console.print(table)
        
        # Show summary
        avg_accuracy = sum(w.accuracy for w in whales) / len(whales)
        total_volume = sum(w.volume for w in whales)
        total_pnl = sum(w.profit_loss for w in whales)
        
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  • Average Accuracy: [green]{avg_accuracy:.1f}%[/green]")
        console.print(f"  • Total Volume: [yellow]${total_volume:,.0f}[/yellow]")
        console.print(f"  • Total P&L: [yellow]${total_pnl:,.0f}[/yellow]")
        
        # Show how to use
        console.print(f"\n[bold cyan]📋 To copy these whales:[/bold cyan]")
        console.print("1. Add their addresses to your .env file:")
        console.print("   [dim]COPY_WHALE_ADDRESSES=address1,address2,address3[/dim]")
        console.print("\n2. Run copy trading mode:")
        console.print("   [dim]python -m src.app.main --mode copy[/dim]")
        
        # Show top 3 recommendations
        console.print(f"\n[bold green]🎯 Top 3 Recommendations:[/bold green]")
        for i, whale in enumerate(whales[:3], 1):
            console.print(f"  {i}. {whale.username or 'Anonymous'} - {whale.accuracy:.1f}% accuracy, ${whale.profit_loss:,.0f} P&L")
            console.print(f"     [dim]Address: {whale.address}[/dim]")
        
    finally:
        await tracker.close()


if __name__ == "__main__":
    asyncio.run(main())

