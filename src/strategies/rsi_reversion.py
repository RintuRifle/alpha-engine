"""
RSI Mean Reversion Strategy.

Uses the Relative Strength Index (RSI) to identify oversold and overbought
conditions. Buys when RSI drops below the oversold threshold (expecting a
bounce), sells when RSI exceeds the overbought threshold (expecting a pullback).

RSI is calculated manually using pandas rolling windows — no external TA library needed.
"""

import pandas as pd
import numpy as np

from .base_strategy import BaseStrategy


class RSIReversion(BaseStrategy):
    """
    RSI Mean Reversion strategy.

    - Buy (+1) when RSI < oversold threshold (default: 30) — stock is "cheap"
    - Sell (-1) when RSI > overbought threshold (default: 70) — stock is "expensive"
    - Neutral (0) otherwise

    RSI Formula:
        RSI = 100 - (100 / (1 + RS))
        RS = Average Gain / Average Loss over `window` periods

    Parameters:
        window: RSI lookback period (default: 14).
        overbought: Sell when RSI exceeds this (default: 70).
        oversold: Buy when RSI drops below this (default: 30).
    """

    def __init__(self, window: int = 14, overbought: int = 70, oversold: int = 30):
        super().__init__(window=window, overbought=overbought, oversold=oversold)
        self.window = window
        self.overbought = overbought
        self.oversold = oversold

    @property
    def name(self) -> str:
        return f"RSI Reversion ({self.window}, {self.oversold}/{self.overbought})"

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # Calculate price changes
        delta = df["close"].diff()

        # Separate gains and losses
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)

        # Calculate average gain/loss using rolling mean (Wilder's method approximation)
        avg_gain = gain.rolling(window=self.window, min_periods=self.window).mean()
        avg_loss = loss.rolling(window=self.window, min_periods=self.window).mean()

        # RSI calculation with edge case handling
        # When avg_loss == 0: RSI = 100 (all gains, no losses → extremely overbought)
        # When avg_gain == 0: RSI = 0 (all losses, no gains → extremely oversold)
        rs = pd.Series(np.where(avg_loss == 0, np.inf, avg_gain / avg_loss), index=df.index)
        df["rsi"] = 100 - (100 / (1 + rs))

        # Generate signals
        df["signal"] = 0
        df.loc[df["rsi"] < self.oversold, "signal"] = 1   # Oversold → Buy
        df.loc[df["rsi"] > self.overbought, "signal"] = -1  # Overbought → Sell

        return df
