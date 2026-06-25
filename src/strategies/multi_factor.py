"""
Multi-Factor Composite Signal Strategy.

Combines multiple independent technical indicators into a scoring system.
Trades only fire when the combined score exceeds a threshold — reducing
false signals from any single indicator.

This is how institutional desks actually generate signals:
single indicators = noise, stacked uncorrelated factors = alpha.

Factors used:
1. RSI (oversold/overbought)          → ±2 points
2. Bollinger Band position            → ±2 points
3. Volume confirmation (spike)        → +1 point
4. MACD histogram direction           → ±1 point
5. Trend filter (200-day MA)          → +1 point

Maximum possible score: +7 (strong buy) to -7 (strong sell)
Default threshold: 4 (conservative; try 3 for more trades)
"""

import pandas as pd
import numpy as np

from .base_strategy import BaseStrategy


class MultiFactorStrategy(BaseStrategy):
    """
    Multi-Factor Composite Signal strategy.

    Combines RSI, Bollinger Bands, MACD, volume, and trend direction
    into a single scoring system. Only trades when multiple factors agree.

    Parameters:
        min_score: Minimum absolute score to trigger a trade (default: 4).
        rsi_window: RSI lookback period (default: 14).
        bb_window: Bollinger Bands lookback (default: 20).
        bb_std: Bollinger Band standard deviations (default: 2.0).
        macd_fast: MACD fast EMA period (default: 12).
        macd_slow: MACD slow EMA period (default: 26).
        macd_signal: MACD signal line period (default: 9).
        trend_window: Long-term trend MA period (default: 200).
        vol_window: Volume average lookback (default: 20).
        vol_multiplier: Volume spike threshold (default: 1.5x average).
    """

    def __init__(
        self,
        min_score: int = 4,
        rsi_window: int = 14,
        bb_window: int = 20,
        bb_std: float = 2.0,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        trend_window: int = 200,
        vol_window: int = 20,
        vol_multiplier: float = 1.5,
    ):
        super().__init__(
            min_score=min_score,
            rsi_window=rsi_window,
            bb_window=bb_window,
            bb_std=bb_std,
        )
        self.min_score = min_score
        self.rsi_window = rsi_window
        self.bb_window = bb_window
        self.bb_std = bb_std
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.trend_window = trend_window
        self.vol_window = vol_window
        self.vol_multiplier = vol_multiplier

    @property
    def name(self) -> str:
        return f"Multi-Factor (score≥{self.min_score})"

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        close = df["close"]
        score = pd.Series(0, index=df.index, dtype=float)

        # ── Factor 1: RSI (±2 points) ──
        rsi = self._compute_rsi(close, self.rsi_window)
        df["mf_rsi"] = rsi
        score += (rsi < 35).astype(int) * 2    # Strong oversold → buy signal
        score -= (rsi > 65).astype(int) * 2    # Strong overbought → sell signal

        # ── Factor 2: Bollinger Band Position (±2 points) ──
        bb_sma = close.rolling(self.bb_window).mean()
        bb_std = close.rolling(self.bb_window).std()
        bb_upper = bb_sma + (bb_std * self.bb_std)
        bb_lower = bb_sma - (bb_std * self.bb_std)
        df["mf_bb_upper"] = bb_upper
        df["mf_bb_lower"] = bb_lower

        score += (close < bb_lower).astype(int) * 2    # Below lower band → buy
        score -= (close > bb_upper).astype(int) * 2    # Above upper band → sell

        # ── Factor 3: Volume Confirmation (+1 point for conviction) ──
        if "volume" in df.columns:
            avg_vol = df["volume"].rolling(self.vol_window).mean()
            score += (df["volume"] > avg_vol * self.vol_multiplier).astype(int)

        # ── Factor 4: MACD Histogram Direction (±1 point) ──
        fast_ema = close.ewm(span=self.macd_fast, adjust=False).mean()
        slow_ema = close.ewm(span=self.macd_slow, adjust=False).mean()
        macd_line = fast_ema - slow_ema
        signal_line = macd_line.ewm(span=self.macd_signal, adjust=False).mean()
        macd_hist = macd_line - signal_line
        df["mf_macd_hist"] = macd_hist

        score += (macd_hist.diff() > 0).astype(int)    # Histogram rising → bullish
        score -= (macd_hist.diff() < 0).astype(int)    # Histogram falling → bearish

        # ── Factor 5: Long-term Trend Filter (+1 point) ──
        ma_trend = close.rolling(self.trend_window).mean()
        df["mf_trend_ma"] = ma_trend
        score += (close > ma_trend).astype(int)         # Above 200-day MA → uptrend
        score -= (close < ma_trend).astype(int)         # Below 200-day MA → downtrend

        # ── Composite Signal Generation ──
        df["mf_score"] = score
        df["signal"] = 0
        df.loc[score >= self.min_score, "signal"] = 1
        df.loc[score <= -self.min_score, "signal"] = -1

        return df

    @staticmethod
    def _compute_rsi(close: pd.Series, window: int) -> pd.Series:
        """Compute RSI using Wilder's exponential smoothing."""
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)

        avg_gain = gain.ewm(alpha=1/window, min_periods=window, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/window, min_periods=window, adjust=False).mean()

        rs = np.where(avg_loss == 0, np.inf, avg_gain / avg_loss)
        rsi = 100 - (100 / (1 + pd.Series(rs, index=close.index)))
        return rsi
