"""
Utility helpers for the Quant Research Platform.

Contains configuration loading, date utilities, formatting functions,
and DataFrame helper methods used across the codebase.
"""

import os
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from dotenv import load_dotenv


def get_project_root() -> Path:
    """Return absolute path to the project root directory."""
    return Path(__file__).resolve().parent.parent.parent


def load_config(config_path: str | None = None) -> dict[str, Any]:
    """
    Load configuration from YAML file with .env overlay.

    Args:
        config_path: Optional path to config.yaml. Defaults to config/config.yaml.

    Returns:
        Merged configuration dictionary.
    """
    load_dotenv()

    if config_path is None:
        config_path = str(get_project_root() / "config" / "config.yaml")

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # Allow .env overrides for sensitive values
    if os.getenv("DB_PATH"):
        config["database"]["path"] = f"sqlite:///{os.getenv('DB_PATH')}"

    return config


def format_percentage(value: float, decimals: int = 2) -> str:
    """Format a float as a percentage string. E.g., 0.1523 → '15.23%'."""
    return f"{value * 100:.{decimals}f}%"


def format_currency(value: float, symbol: str = "$", decimals: int = 2) -> str:
    """Format a float as currency. E.g., 10543.7 → '$10,543.70'."""
    return f"{symbol}{value:,.{decimals}f}"


def annualize_returns(daily_returns: pd.Series, trading_days: int = 252) -> float:
    """
    Annualize a series of daily returns using geometric compounding.

    Args:
        daily_returns: Series of daily percentage returns.
        trading_days: Number of trading days per year.

    Returns:
        Annualized return as a float.
    """
    if daily_returns.empty:
        return 0.0
    total_return = (1 + daily_returns).prod()
    n_days = len(daily_returns)
    return total_return ** (trading_days / n_days) - 1


def trading_days_between(start: str, end: str) -> int:
    """
    Estimate the number of trading days between two date strings.
    Uses pandas business day frequency for accuracy.
    """
    return len(pd.bdate_range(start=start, end=end))


def ensure_datetime_index(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure the DataFrame has a proper DatetimeIndex.
    Handles both 'Date' and 'date' column names, or existing index.
    """
    if isinstance(df.index, pd.DatetimeIndex):
        return df

    for col in ["Date", "date"]:
        if col in df.columns:
            df = df.copy()
            df[col] = pd.to_datetime(df[col])
            df.set_index(col, inplace=True)
            return df

    # Try converting existing index
    df = df.copy()
    df.index = pd.to_datetime(df.index)
    return df


def safe_division(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safe division that returns a default value instead of raising ZeroDivisionError."""
    if denominator == 0:
        return default
    return numerator / denominator
