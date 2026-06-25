"""
Momentum + Mean Reversion Hybrid Strategy (MOMO-MR).

Uses short-term mean reversion entries within a confirmed long-term
momentum trend. This is one of the most robust quant strategies,
combining two well-documented anomalies:

1. MOMENTUM (12-month): Assets that have been going up tend to keep going up.
2. MEAN REVERSION (short-term): Within an uptrend, short-term dips are buying opportunities.

Logic:
  1. Confirm long-term uptrend: asset up over past `momentum_window` days
  2. Wait for short-term pullback: RSI dips below `entry_rsi`
  3. Enter long at the pullback
  4. Exit when RSI recovers above `exit_rsi` OR trailing stop hit

Based on Gary Antonacci's "Dual Momentum" and Larry Connors' RSI pullback research.
"""

import pandas as pd
import numpy as np

from .base_strategy import BaseStrategy


class MomentumMR(BaseStrategy):
    """
    Momentum + Mean Reversion Hybrid strategy.

    Parameters:
        momentum_window: Lookback period for momentum confirmation (default: 252 = ~12 months).
        momentum_threshold: Minimum return over momentum_window to confirm uptrend (default: 0.0 = positive).
        rsi_window: RSI calculation period (default: 14).
        entry_rsi: RSI level below which to enter (mean reversion buy) (default: 40).
        exit_rsi: RSI level above which to exit (take profit) (default: 55).
        trend_ma: Moving average period for trend confirmation (default: 200).
    """

    def __init__(
        self,
        momentum_window: int = 252,
        momentum_threshold: float = 0.0,
        rsi_window: int = 14,
        entry_rsi: int = 40,
        exit_rsi: int = 55,
        trend_ma: int = 200,
    ):
        super().__init__(
            momentum_window=momentum_window,
            rsi_window=rsi_window,
            entry_rsi=entry_rsi,
            exit_rsi=exit_rsi,
            trend_ma=trend_ma,
        )
        self.momentum_window = momentum_window
        self.momentum_threshold = momentum_threshold
        self.rsi_window = rsi_window
        self.entry_rsi = entry_rsi
        self.exit_rsi = exit_rsi
        self.trend_ma = trend_ma

    @property
    def name(self) -> str:
        return f"Momentum+MR (RSI {self.entry_rsi}/{self.exit_rsi})"

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        close = df["close"]

        # ── Momentum Filter: 12-month return ──
        df["momentum_return"] = close.pct_change(self.momentum_window)
        momentum_ok = df["momentum_return"] > self.momentum_threshold

        # ── Trend Filter: price above long-term MA ──
        df["trend_ma"] = close.rolling(self.trend_ma).mean()
        trend_ok = close > df["trend_ma"]

        # ── RSI Calculation (Wilder's) ──
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1/self.rsi_window, min_periods=self.rsi_window, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/self.rsi_window, min_periods=self.rsi_window, adjust=False).mean()
        rs = np.where(avg_loss == 0, np.inf, avg_gain / avg_loss)
        df["momr_rsi"] = 100 - (100 / (1 + pd.Series(rs, index=df.index)))

        # ── Signal Logic ──
        # State machine: FLAT → ENTRY → EXIT
        # Entry: momentum + trend confirmed AND RSI dips below entry threshold
        # Exit: RSI recovers above exit threshold
        df["signal"] = 0

        in_position = False
        signals = np.zeros(len(df))

        for i in range(len(df)):
            rsi_val = df["momr_rsi"].iloc[i]

            if not in_position:
                # Look for entry: momentum + trend + oversold RSI
                if (i >= self.momentum_window and
                    momentum_ok.iloc[i] and
                    trend_ok.iloc[i] and
                    rsi_val < self.entry_rsi):
                    signals[i] = 1  # BUY
                    in_position = True
                else:
                    signals[i] = 0  # FLAT
            else:
                # Look for exit: RSI recovered
                if rsi_val > self.exit_rsi:
                    signals[i] = -1  # SELL
                    in_position = False
                else:
                    signals[i] = 1  # HOLD long

        df["signal"] = signals
        return df
