"""
Rich terminal UI for displaying arbitrage opportunities and system status.
"""
import logging
from decimal import Decimal
from datetime import datetime
from typing import List, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich import box

from ..core.models import ArbitrageOpportunity, Position
from ..core.storage import PositionDB, PnLEntryDB

logger = logging.getLogger(__name__)


class UI:
    """Rich terminal UI for the arbitrage system."""
    
    def __init__(self):
        """Initialize UI with Rich console."""
        self.console = Console()
    
    def print_banner(self):
        """Print startup banner."""
        banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   Polymarket Arbitrage Bot - Profit-First Edition            ║
║   Strategy: YES + NO ≠ $1.00                                  ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
        """
        self.console.print(banner, style="bold cyan")
    
    def print_config(self, config) -> None:
        """Print current configuration."""
        config_table = Table(
            title="Configuration",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta"
        )
        config_table.add_column("Setting", style="cyan")
        config_table.add_column("Value", style="yellow")
        
        config_table.add_row("Trading Mode", config.trading_mode.upper())
        config_table.add_row("Min Gross Edge", f"{config.min_gross_edge:.4f}")
        config_table.add_row("Min Net Profit", f"${config.min_net_profit:.2f}")
        config_table.add_row("Min Liquidity", f"${config.min_liquidity:.2f}")
        config_table.add_row("Max Trade Size", f"${config.max_trade_size:.2f}")
        config_table.add_row("Max Daily Loss", f"${config.max_daily_loss:.2f}")
        config_table.add_row("Min APY", f"{config.min_apy}%")
        config_table.add_row("Poll Interval", f"{config.poll_interval_seconds}s")
        
        self.console.print(config_table)
        self.console.print()
    
    def create_opportunities_table(
        self,
        opportunities: List[ArbitrageOpportunity],
        max_rows: int = 10
    ) -> Table:
        """
        Create a table displaying arbitrage opportunities.
        
        Args:
            opportunities: List of opportunities to display
            max_rows: Maximum number of rows to show
            
        Returns:
            Rich Table object
        """
        table = Table(
            title=f"🎯 Arbitrage Opportunities (Top {min(len(opportunities), max_rows)})",
            box=box.DOUBLE_EDGE,
            show_header=True,
            header_style="bold white on blue"
        )
        
        table.add_column("#", style="dim", width=3)
        table.add_column("Market", style="cyan", width=35)
        table.add_column("YES Ask", justify="right", style="yellow", width=8)
        table.add_column("NO Ask", justify="right", style="yellow", width=8)
        table.add_column("Sum", justify="right", style="magenta", width=8)
        table.add_column("Edge", justify="right", style="green", width=8)
        table.add_column("Net $", justify="right", style="green bold", width=8)
        table.add_column("Size", justify="right", style="blue", width=8)
        table.add_column("APY", justify="right", style="red bold", width=9)
        table.add_column("Days", justify="right", style="dim", width=5)
        
        for idx, opp in enumerate(opportunities[:max_rows], 1):
            # Color code based on quality
            edge_color = "green bold" if opp.gross_edge >= Decimal("0.03") else "green"
            apy_color = "red bold" if opp.apy >= Decimal("100") else "yellow"
            
            # Truncate market title if too long
            title = opp.market.title[:32] + "..." if len(opp.market.title) > 35 else opp.market.title
            
            table.add_row(
                str(idx),
                title,
                f"{opp.yes_ask:.4f}",
                f"{opp.no_ask:.4f}",
                f"{opp.sum_asks:.4f}",
                f"[{edge_color}]{opp.gross_edge:.4f}[/{edge_color}]",
                f"[green bold]${opp.net_profit:.2f}[/green bold]",
                f"${opp.position_size:.0f}",
                f"[{apy_color}]{opp.apy:.1f}%[/{apy_color}]",
                str(opp.market.days_to_resolution)
            )
        
        return table
    
    def print_opportunities(
        self,
        opportunities: List[ArbitrageOpportunity],
        max_rows: int = 10
    ) -> None:
        """Print arbitrage opportunities table."""
        if not opportunities:
            self.console.print(
                Panel(
                    "[yellow]No arbitrage opportunities found.[/yellow]",
                    title="Status",
                    border_style="yellow"
                )
            )
            return
        
        table = self.create_opportunities_table(opportunities, max_rows)
        self.console.print(table)
        self.console.print()
    
    def print_opportunity_detail(self, opp: ArbitrageOpportunity) -> None:
        """Print detailed view of a single opportunity."""
        self.console.print()
        self.console.print(Panel(
            f"[bold cyan]{opp.market.title}[/bold cyan]",
            title="Market Details",
            border_style="cyan"
        ))
        
        # Market info
        info_table = Table(box=box.SIMPLE, show_header=False)
        info_table.add_column("Field", style="dim")
        info_table.add_column("Value")
        
        info_table.add_row("Market ID", opp.market.id)
        info_table.add_row("Category", opp.market.category or "N/A")
        info_table.add_row("Volume", f"${opp.market.volume:,.2f}")
        info_table.add_row("Resolution Date", opp.market.end_date.strftime("%Y-%m-%d %H:%M"))
        info_table.add_row("Days to Resolution", str(opp.market.days_to_resolution))
        
        self.console.print(info_table)
        self.console.print()
        
        # Arbitrage metrics
        metrics_table = Table(
            title="Arbitrage Metrics",
            box=box.ROUNDED,
            show_header=True
        )
        metrics_table.add_column("Metric", style="cyan")
        metrics_table.add_column("Value", style="yellow bold")
        
        metrics_table.add_row("YES Ask", f"{opp.yes_ask:.6f}")
        metrics_table.add_row("NO Ask", f"{opp.no_ask:.6f}")
        metrics_table.add_row("Sum of Asks", f"{opp.sum_asks:.6f}")
        metrics_table.add_row("Gross Edge", f"[green]{opp.gross_edge:.6f}[/green]")
        metrics_table.add_row("Position Size", f"${opp.position_size:.2f}")
        metrics_table.add_row("Estimated Gas", f"${opp.estimated_gas:.4f}")
        metrics_table.add_row("Net Profit", f"[green bold]${opp.net_profit:.2f}[/green bold]")
        metrics_table.add_row("ROI", f"[yellow]{opp.roi:.2f}%[/yellow]")
        metrics_table.add_row("APY", f"[red bold]{opp.apy:.1f}%[/red bold]")
        metrics_table.add_row("Liquidity", f"${opp.liquidity:.2f}")
        metrics_table.add_row("Confidence", f"{opp.confidence_score:.1f}/100")
        
        self.console.print(metrics_table)
        self.console.print()
    
    def print_positions(self, positions: List[PositionDB]) -> None:
        """Print current open positions."""
        if not positions:
            self.console.print("[dim]No open positions[/dim]")
            return
        
        table = Table(
            title="Open Positions",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        
        table.add_column("ID", width=5)
        table.add_column("Market", width=30)
        table.add_column("Token", width=6)
        table.add_column("Size", justify="right", width=8)
        table.add_column("Entry", justify="right", width=8)
        table.add_column("Current", justify="right", width=8)
        table.add_column("Unrealized", justify="right", width=10)
        table.add_column("Age", justify="right", width=8)
        
        for pos in positions:
            age = (datetime.now() - pos.opened_at).days
            unrealized_str = f"${pos.unrealized_pnl:.2f}" if pos.unrealized_pnl else "N/A"
            unrealized_color = "green" if (pos.unrealized_pnl or 0) >= 0 else "red"
            
            table.add_row(
                str(pos.id),
                pos.market_id[:27] + "..." if len(pos.market_id) > 30 else pos.market_id,
                pos.outcome.value,
                f"${pos.size:.2f}",
                f"{pos.average_entry_price:.4f}",
                f"{pos.current_price:.4f}" if pos.current_price else "N/A",
                f"[{unrealized_color}]{unrealized_str}[/{unrealized_color}]",
                f"{age}d"
            )
        
        self.console.print(table)
        self.console.print()
    
    def print_pnl_summary(self, entries: List[PnLEntryDB]) -> None:
        """Print PnL summary statistics."""
        if not entries:
            self.console.print("[dim]No PnL history yet[/dim]")
            return
        
        # Calculate totals
        total_realized = sum(e.realized_pnl for e in entries)
        total_fees = sum(e.fees_paid for e in entries)
        total_gas = sum(e.gas_paid for e in entries)
        total_net = total_realized - total_fees - total_gas
        
        total_entry = sum(e.entry_cost for e in entries)
        total_roi = (total_net / total_entry * 100) if total_entry > 0 else 0
        
        # Summary panel
        summary_table = Table(box=box.SIMPLE, show_header=False)
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="yellow bold", justify="right")
        
        summary_table.add_row("Total Trades", str(len(entries)))
        summary_table.add_row("Realized PnL", f"${total_realized:.2f}")
        summary_table.add_row("Total Fees", f"${total_fees:.4f}")
        summary_table.add_row("Total Gas", f"${total_gas:.4f}")
        
        net_color = "green bold" if total_net >= 0 else "red bold"
        summary_table.add_row(
            "Net Profit",
            f"[{net_color}]${total_net:.2f}[/{net_color}]"
        )
        
        roi_color = "green" if total_roi >= 0 else "red"
        summary_table.add_row(
            "Total ROI",
            f"[{roi_color}]{total_roi:.2f}%[/{roi_color}]"
        )
        
        self.console.print(Panel(
            summary_table,
            title="📊 PnL Summary",
            border_style="green" if total_net >= 0 else "red"
        ))
        self.console.print()
    
    def print_scan_status(
        self,
        markets_scanned: int,
        opportunities_found: int,
        scan_duration: float
    ) -> None:
        """Print scan status summary."""
        status_text = (
            f"[cyan]Markets Scanned:[/cyan] {markets_scanned}  "
            f"[green]Opportunities:[/green] {opportunities_found}  "
            f"[dim]Time:[/dim] {scan_duration:.2f}s"
        )
        self.console.print(Panel(status_text, border_style="blue"))
        self.console.print()
    
    def print_error(self, message: str) -> None:
        """Print error message."""
        self.console.print(f"[red bold]❌ Error:[/red bold] {message}")
    
    def print_warning(self, message: str) -> None:
        """Print warning message."""
        self.console.print(f"[yellow]⚠️  Warning:[/yellow] {message}")
    
    def print_success(self, message: str) -> None:
        """Print success message."""
        self.console.print(f"[green]✅ Success:[/green] {message}")
    
    def print_info(self, message: str) -> None:
        """Print info message."""
        self.console.print(f"[blue]ℹ️  Info:[/blue] {message}")
    
    def confirm(self, message: str) -> bool:
        """
        Ask user for confirmation.
        
        Args:
            message: Confirmation prompt
            
        Returns:
            True if user confirms, False otherwise
        """
        response = self.console.input(f"[yellow]{message} (y/n):[/yellow] ")
        return response.lower().strip() in ['y', 'yes']




