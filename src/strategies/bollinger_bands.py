"""
Bollinger Bands Strategy.

Uses Bollinger Bands (SMA ± N standard deviations) to identify mean-reversion
opportunities. Buys when price drops below the lower band, sells when price
exceeds the upper band.
"""

import pandas as pd
import numpy as np

from .base_strategy import BaseStrategy


class BollingerBands(BaseStrategy):
    """
    Bollinger Bands mean reversion strategy.

    - Buy (+1) when close < lower_band (price is below normal range → expect bounce)
    - Sell (-1) when close > upper_band (price is above normal range → expect pullback)
    - Neutral (0) when price is within the bands

    Parameters:
        window: SMA lookback period (default: 20).
        num_std: Number of standard deviations for bands (default: 2.0).
    """

    def __init__(self, window: int = 20, num_std: float = 2.0):
        super().__init__(window=window, num_std=num_std)
        self.window = window
        self.num_std = num_std

    @property
    def name(self) -> str:
        return f"Bollinger Bands ({self.window}, {self.num_std}σ)"

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # Calculate Bollinger Bands
        df["bb_sma"] = df["close"].rolling(window=self.window).mean()
        df["bb_std"] = df["close"].rolling(window=self.window).std()
        df["upper_band"] = df["bb_sma"] + (df["bb_std"] * self.num_std)
        df["lower_band"] = df["bb_sma"] - (df["bb_std"] * self.num_std)

        # Generate signals
        df["signal"] = 0
        df.loc[df["close"] < df["lower_band"], "signal"] = 1   # Below lower → Buy
        df.loc[df["close"] > df["upper_band"], "signal"] = -1  # Above upper → Sell

        # NaN period = neutral
        df.loc[df["bb_sma"].isna(), "signal"] = 0

        return df
