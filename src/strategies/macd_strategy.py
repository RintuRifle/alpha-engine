"""
MACD (Moving Average Convergence Divergence) Strategy.

Uses the MACD line and signal line crossover to generate trend-following signals.
The MACD line is the difference between a fast and slow EMA, while the signal line
is an EMA of the MACD line itself.
"""

import pandas as pd

from .base_strategy import BaseStrategy


class MACDStrategy(BaseStrategy):
    """
    MACD Signal Line Crossover strategy.

    - Buy (+1) when MACD line crosses above the signal line (bullish momentum)
    - Sell (-1) when MACD line crosses below the signal line (bearish momentum)
    - Neutral (0) during initial warmup period

    Parameters:
        fast_period: Fast EMA period (default: 12).
        slow_period: Slow EMA period (default: 26).
        signal_period: Signal line EMA period (default: 9).
    """

    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        super().__init__(
            fast_period=fast_period,
            slow_period=slow_period,
            signal_period=signal_period,
        )
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period

    @property
    def name(self) -> str:
        return f"MACD ({self.fast_period}/{self.slow_period}/{self.signal_period})"

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # Calculate MACD components
        fast_ema = df["close"].ewm(span=self.fast_period, adjust=False).mean()
        slow_ema = df["close"].ewm(span=self.slow_period, adjust=False).mean()
        df["macd"] = fast_ema - slow_ema
        df["macd_signal"] = df["macd"].ewm(span=self.signal_period, adjust=False).mean()
        df["macd_histogram"] = df["macd"] - df["macd_signal"]

        # Generate signals
        df["signal"] = 0
        df.loc[df["macd"] > df["macd_signal"], "signal"] = 1   # MACD above signal → Buy
        df.loc[df["macd"] < df["macd_signal"], "signal"] = -1  # MACD below signal → Sell

        return df
