"""
VWAP Reversion Strategy.

Uses daily-approximated VWAP (Volume-Weighted Average Price) as a fair-value anchor.
When price deviates significantly below VWAP, the asset is considered undervalued (buy).
When price rises above VWAP by the threshold, the asset is considered overvalued (sell).

Parameters:
    vwap_window: Rolling window for VWAP calculation (default: 20)
    threshold: Deviation threshold from VWAP to trigger signals (default: 0.02 = 2%)
"""

import pandas as pd
import numpy as np

from src.strategies.base_strategy import BaseStrategy


class VWAPStrategy(BaseStrategy):
    """
    VWAP Reversion — Buy when price is significantly below VWAP,
    sell when price is significantly above VWAP.
    """

    def __init__(self, vwap_window: int = 20, threshold: float = 0.02, **kwargs):
        super().__init__(vwap_window=vwap_window, threshold=threshold, **kwargs)
        self.vwap_window = vwap_window
        self.threshold = threshold

    @property
    def name(self) -> str:
        return f"VWAP Reversion ({self.vwap_window}, {self.threshold:.1%})"

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate signals based on price deviation from rolling VWAP.

        VWAP = cumulative(typical_price * volume) / cumulative(volume)
        where typical_price = (high + low + close) / 3

        Signal logic:
            - Buy (+1) when close < VWAP * (1 - threshold)
            - Sell (-1) when close > VWAP * (1 + threshold)
            - Hold (0) otherwise
        """
        df = df.copy()

        # Calculate typical price (daily VWAP proxy)
        typical_price = (df["high"] + df["low"] + df["close"]) / 3

        # Rolling VWAP = rolling sum(TP * Volume) / rolling sum(Volume)
        tp_vol = typical_price * df["volume"]
        df["vwap"] = (
            tp_vol.rolling(window=self.vwap_window, min_periods=1).sum()
            / df["volume"].rolling(window=self.vwap_window, min_periods=1).sum()
        )

        # Deviation ratio: how far price is from VWAP
        df["vwap_deviation"] = (df["close"] - df["vwap"]) / df["vwap"]

        # Signal generation
        df["signal"] = 0
        df.loc[df["vwap_deviation"] < -self.threshold, "signal"] = 1   # Buy: undervalued
        df.loc[df["vwap_deviation"] > self.threshold, "signal"] = -1   # Sell: overvalued

        # Shift to prevent look-ahead bias
        df["signal"] = df["signal"].shift(1).fillna(0).astype(int)

        return df
