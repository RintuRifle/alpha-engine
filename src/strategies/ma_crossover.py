"""
Moving Average Crossover Strategy.

Generates buy signals when the short-term SMA crosses above the long-term SMA,
and sell signals when it crosses below. Classic trend-following approach.
"""

import pandas as pd
import numpy as np

from .base_strategy import BaseStrategy


class MACrossover(BaseStrategy):
    """
    Simple Moving Average (SMA) Crossover strategy.

    - Buy (+1) when short_ma > long_ma (bullish crossover)
    - Sell (-1) when short_ma <= long_ma (bearish crossover)
    - NaN regions default to 0 (neutral)

    Parameters:
        short_window: Period for the short-term moving average (default: 50).
        long_window: Period for the long-term moving average (default: 200).
    """

    def __init__(self, short_window: int = 50, long_window: int = 200):
        super().__init__(short_window=short_window, long_window=long_window)
        self.short_window = short_window
        self.long_window = long_window

    @property
    def name(self) -> str:
        return f"SMA Crossover ({self.short_window}/{self.long_window})"

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["short_ma"] = df["close"].rolling(window=self.short_window).mean()
        df["long_ma"] = df["close"].rolling(window=self.long_window).mean()

        # Default to neutral, then assign signals
        df["signal"] = 0
        df.loc[df["short_ma"] > df["long_ma"], "signal"] = 1
        df.loc[df["short_ma"] <= df["long_ma"], "signal"] = -1

        # NaN period (before we have enough data for moving averages) = neutral
        df.loc[df["long_ma"].isna(), "signal"] = 0

        return df
