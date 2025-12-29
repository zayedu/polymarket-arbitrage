"""Test configuration and basic functionality."""
import pytest
from decimal import Decimal
from config import Config


def test_config_loads():
    """Test that config loads with defaults."""
    config = Config()
    assert config.min_gross_edge >= Decimal("0")
    assert config.max_trade_size > Decimal("0")


def test_config_modes():
    """Test config mode helpers."""
    config = Config(trading_mode="paper")
    assert config.is_paper_trading()
    assert not config.is_live_trading()
    assert not config.is_scan_only()



