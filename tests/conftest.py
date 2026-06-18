"""
Shared pytest fixtures for the Quant Research Platform test suite.

All fixtures use deterministic data (seeded random) so tests are
reproducible. No random failures from data variation.
"""

import pytest
import pandas as pd
import numpy as np


@pytest.fixture
def sample_ohlcv():
    """
    Deterministic OHLCV DataFrame with 252 rows (1 trading year).
    Uses a seeded random generator for reproducibility.
    """
    rng = np.random.RandomState(42)
    n = 252
    dates = pd.bdate_range(start="2022-01-03", periods=n)

    # Generate realistic-ish price data using random walk
    base_price = 100.0
    returns = rng.normal(0.0005, 0.02, n)  # Slight upward drift
    close = base_price * np.cumprod(1 + returns)
    high = close * (1 + rng.uniform(0.001, 0.03, n))
    low = close * (1 - rng.uniform(0.001, 0.03, n))
    open_price = low + rng.uniform(0, 1, n) * (high - low)
    volume = rng.randint(100000, 5000000, n).astype(float)

    df = pd.DataFrame({
        "date": dates,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "adj_close": close,
        "volume": volume,
    })
    return df


@pytest.fixture
def equity_df():
    """
    Deterministic equity DataFrame for testing analytics.
    Simulates a portfolio that grows from $10,000 to ~$11,500 over 252 days.
    """
    rng = np.random.RandomState(99)
    n = 252
    dates = pd.bdate_range(start="2022-01-03", periods=n)

    daily_returns = rng.normal(0.0002, 0.015, n)
    equity = 10000.0 * np.cumprod(1 + daily_returns)

    df = pd.DataFrame({
        "cash": equity * 0.1,  # 10% in cash
        "positions_value": equity * 0.9,
        "total_equity": equity,
    }, index=dates)
    df.index.name = "date"
    return df


@pytest.fixture
def sample_trade_history():
    """
    Deterministic trade history with known outcomes.
    3 round trips: 2 winners, 1 loser → win rate should be 66.7%
    """
    return [
        # Round trip 1: Buy at 100, sell at 110 → +$1,000 profit
        {"date": "2022-01-05", "ticker": "AAPL", "action": "BUY",
         "quantity": 100, "price": 100.0, "commission": 10.0, "slippage": 5.0},
        {"date": "2022-02-15", "ticker": "AAPL", "action": "SELL",
         "quantity": 100, "price": 110.0, "commission": 11.0, "slippage": 5.5},

        # Round trip 2: Buy at 105, sell at 95 → -$1,000 loss
        {"date": "2022-03-01", "ticker": "AAPL", "action": "BUY",
         "quantity": 100, "price": 105.0, "commission": 10.5, "slippage": 5.25},
        {"date": "2022-04-01", "ticker": "AAPL", "action": "SELL",
         "quantity": 100, "price": 95.0, "commission": 9.5, "slippage": 4.75},

        # Round trip 3: Buy at 90, sell at 100 → +$1,000 profit
        {"date": "2022-05-01", "ticker": "AAPL", "action": "BUY",
         "quantity": 100, "price": 90.0, "commission": 9.0, "slippage": 4.5},
        {"date": "2022-06-01", "ticker": "AAPL", "action": "SELL",
         "quantity": 100, "price": 100.0, "commission": 10.0, "slippage": 5.0},
    ]


@pytest.fixture
def mock_config():
    """Standard backtest configuration for testing."""
    return {
        "database": {"path": "sqlite:///data/test_market_data.db"},
        "trading": {
            "initial_capital": 10000.0,
            "commission": 0.001,
            "slippage": 0.0005,
        },
        "position_sizing": {
            "method": "fixed_capital",
            "allocation": 0.10,
        },
    }
