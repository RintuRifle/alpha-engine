"""
Abstract base class for all trading strategies.

Every strategy MUST inherit from BaseStrategy and implement generate_signals().
Provides common interface for the backtester engine and optimizer.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict

import pandas as pd


class BaseStrategy(ABC):
    """
    Abstract base class that all strategies must inherit.

    Subclasses must:
    1. Implement `generate_signals()` — adds a 'signal' column to the DataFrame.
    2. Override `name` property — human-readable strategy name.
    """

    def __init__(self, **params: Any):
        self.params: Dict[str, Any] = params

    @property
    def name(self) -> str:
        """Human-readable strategy name for display in UI and reports."""
        return self.__class__.__name__

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals from OHLCV data.

        Args:
            df: DataFrame with at minimum a 'close' column.

        Returns:
            DataFrame with an additional 'signal' column:
            - +1 = Buy / Go Long
            -  0 = Neutral / Hold
            - -1 = Sell / Go Short
        """
        pass

    def describe_params(self) -> Dict[str, Any]:
        """Return a dictionary of current strategy parameters."""
        return self.params.copy()

    def __repr__(self) -> str:
        params_str = ", ".join(f"{k}={v}" for k, v in self.params.items())
        return f"{self.name}({params_str})"
