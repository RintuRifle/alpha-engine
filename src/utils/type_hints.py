"""
Type hints and TypedDicts for the Quant Research Platform.

Provides structured types for type-safe code across all modules.
Use these instead of raw dicts for IDE autocomplete + mypy validation.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Literal, TypedDict


# ──────────────────────────────────────────────
# Order & Trade Types
# ──────────────────────────────────────────────

class OrderParameters(TypedDict, total=False):
    """Parameters for placing an order."""
    ticker: str
    action: Literal["BUY", "SELL"]
    quantity: float
    price: float
    date: date


class TradeRecord(TypedDict):
    """Immutable record of an executed trade."""
    date: date
    ticker: str
    action: Literal["BUY", "SELL"]
    quantity: float
    price: float
    commission: float
    slippage: float


# ──────────────────────────────────────────────
# Portfolio Types
# ──────────────────────────────────────────────

class PortfolioSnapshot(TypedDict):
    """Single point-in-time portfolio state."""
    date: date
    cash: float
    positions_value: float
    total_equity: float


# ──────────────────────────────────────────────
# Configuration Types
# ──────────────────────────────────────────────

class TradingConfig(TypedDict):
    """Trading parameters from config.yaml."""
    initial_capital: float
    commission: float
    slippage: float


class PositionSizingConfig(TypedDict, total=False):
    """Position sizing configuration."""
    method: Literal["fixed_capital", "fixed_shares", "kelly"]
    allocation: float
    shares: int


class BacktestConfig(TypedDict, total=False):
    """Full backtest configuration bundle."""
    ticker: str
    start_date: str
    end_date: str
    strategy_name: str
    strategy_params: Dict[str, Any]
    trading: TradingConfig
    position_sizing: PositionSizingConfig


# ──────────────────────────────────────────────
# Analytics Types
# ──────────────────────────────────────────────

class MetricsResult(TypedDict, total=False):
    """Results from a full metrics computation."""
    cagr: float
    total_return: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    volatility: float
    var_95: float
    cvar_95: float
    alpha: float
    beta: float
    total_trades: int


class StrategyParams(TypedDict, total=False):
    """Generic strategy parameters dictionary."""
    short_window: int
    long_window: int
    window: int
    overbought: int
    oversold: int
    num_std: float
    fast_period: int
    slow_period: int
    signal_period: int
