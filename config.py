"""
Configuration management for the Polymarket arbitrage system.
Loads settings from environment variables with type validation.
"""
import os
from decimal import Decimal
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Config(BaseSettings):
    """Application configuration with type-safe environment variable loading."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # API Configuration
    polymarket_private_key: str = Field(
        default="",
        description="Polygon private key for signing transactions"
    )
    polymarket_api_key: str = Field(
        default="",
        description="Optional Polymarket API key"
    )
    polygon_rpc_url: str = Field(
        default="https://polygon-rpc.com",
        description="Polygon RPC endpoint"
    )
    
    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./arbitrage.db",
        description="Database connection URL"
    )
    
    # Arbitrage Thresholds
    min_gross_edge: Decimal = Field(
        default=Decimal("0.01"),
        description="Minimum edge per dollar (0.01 = 1%)"
    )
    min_net_profit: Decimal = Field(
        default=Decimal("0.10"),
        description="Minimum net profit after costs"
    )
    min_liquidity: Decimal = Field(
        default=Decimal("10.0"),
        description="Minimum liquidity at top of book"
    )
    max_days_to_resolution: int = Field(
        default=14,
        description="Maximum days until market resolution"
    )
    min_apy: Decimal = Field(
        default=Decimal("50"),
        description="Minimum APY percentage"
    )
    
    # Risk Management
    max_trade_size: Decimal = Field(
        default=Decimal("15.0"),
        description="Maximum trade size in USD"
    )
    max_daily_loss: Decimal = Field(
        default=Decimal("10.0"),
        description="Maximum daily loss in USD"
    )
    max_open_exposure: Decimal = Field(
        default=Decimal("50.0"),
        description="Maximum total open exposure in USD"
    )
    
    # Execution Settings
    order_timeout_seconds: int = Field(
        default=5,
        description="Timeout for order execution"
    )
    partial_fill_unwind: bool = Field(
        default=True,
        description="Automatically unwind partial fills"
    )
    
    # Operation
    trading_mode: Literal["paper", "scan", "live"] = Field(
        default="paper",
        description="Trading mode"
    )
    poll_interval_seconds: int = Field(
        default=3,
        description="Market scanning interval"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    
    # Gas Settings
    max_gas_price_gwei: int = Field(
        default=50,
        description="Maximum gas price in Gwei"
    )
    estimated_gas_cost_usd: Decimal = Field(
        default=Decimal("0.01"),
        description="Estimated gas cost per transaction"
    )
    
    # Email Notifications
    enable_notifications: bool = Field(
        default=False,
        description="Enable email notifications"
    )
    sendgrid_api_key: str = Field(
        default="",
        description="SendGrid API key for email notifications"
    )
    notification_email_from: str = Field(
        default="bot@polymarket-arbitrage.com",
        description="Sender email address"
    )
    notification_email_to: str = Field(
        default="",
        description="Recipient email address for alerts"
    )
    
    # SMS Notifications (via email-to-SMS gateway)
    sms_enabled: bool = Field(
        default=False,
        description="Enable SMS notifications via carrier email gateway"
    )
    sms_phone_number: str = Field(
        default="",
        description="Phone number for SMS (digits only, e.g., 6475173009)"
    )
    sms_carrier: str = Field(
        default="",
        description="Carrier name (rogers, bell, telus, fido, koodo, freedom)"
    )
    
    # Discord Notifications (100% FREE!)
    discord_enabled: bool = Field(
        default=False,
        description="Enable Discord notifications (completely free!)"
    )
    discord_webhook_url: str = Field(
        default="",
        description="Discord webhook URL for notifications"
    )
    
    # Copy Trading Settings
    copy_trading_enabled: bool = Field(
        default=False,
        description="Enable copy trading from high-accuracy whales"
    )
    copy_whale_addresses: str = Field(
        default="",
        description="Comma-separated list of whale addresses to copy"
    )
    copy_ratio: Decimal = Field(
        default=Decimal("0.01"),
        description="Proportion of whale's position to copy (0.01 = 1%)"
    )
    max_copy_size: Decimal = Field(
        default=Decimal("50"),
        description="Maximum capital per copy trade"
    )
    min_whale_accuracy: Decimal = Field(
        default=Decimal("65"),
        description="Minimum whale accuracy to copy (%)"
    )
    
    # Automated Trading Settings
    auto_trading_enabled: bool = Field(
        default=False,
        description="Enable automated trade execution (paper mode safe)"
    )
    min_confidence_score: Decimal = Field(
        default=Decimal("70"),
        description="Minimum confidence score (0-100) to execute trade"
    )
    max_open_positions: int = Field(
        default=10,
        description="Maximum number of open positions"
    )
    min_position_size: Decimal = Field(
        default=Decimal("5"),
        description="Minimum position size in USD"
    )
    position_sizing_mode: str = Field(
        default="confidence_scaled",
        description="Position sizing strategy: confidence_scaled, fixed, or whale_ratio"
    )
    
    @field_validator("min_gross_edge", "min_net_profit", "min_liquidity", 
                     "max_trade_size", "max_daily_loss", "max_open_exposure",
                     "min_apy", "estimated_gas_cost_usd", "copy_ratio", 
                     "max_copy_size", "min_whale_accuracy", "min_confidence_score",
                     "min_position_size", mode="before")
    @classmethod
    def convert_to_decimal(cls, v):
        """Convert numeric strings to Decimal for precision."""
        if isinstance(v, str):
            return Decimal(v)
        return Decimal(str(v))
    
    def is_live_trading(self) -> bool:
        """Check if live trading is enabled."""
        return self.trading_mode == "live"
    
    def is_paper_trading(self) -> bool:
        """Check if paper trading is enabled."""
        return self.trading_mode == "paper"
    
    def is_scan_only(self) -> bool:
        """Check if scan-only mode is enabled."""
        return self.trading_mode == "scan"


# Global config instance
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reload_config() -> Config:
    """Reload configuration from environment."""
    global _config
    _config = Config()
    return _config

