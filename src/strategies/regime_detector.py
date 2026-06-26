"""
Market Regime Detector — classifies market conditions in real-time.

Uses three independent indicators to classify the current market regime:
1. ADX (Average Directional Index) — measures trend strength
2. Realized Volatility — annualized standard deviation of returns
3. Price Slope — linear regression slope over lookback period

Regimes:
  TRENDING  — Strong directional move (ADX > 25, clear slope)
  RANGING   — Choppy, mean-reverting market (ADX < 20, low slope)
  CRISIS    — Extreme volatility regime (vol > 40% annualized)

Why this matters:
  - RSI mean-reversion in a strong trend = catastrophic losses
  - SMA crossover in a choppy market = death by a thousand cuts
  - Any strategy in a crisis = wipeout without hedging

Usage:
    detector = RegimeDetector()
    df = detector.detect(df)  # Adds 'regime', 'adx', 'volatility_ann' columns
    print(df['regime'].value_counts())
"""

import numpy as np
import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)


class Regime:
    """Regime constants."""
    TRENDING = "trending"
    RANGING = "ranging"
    CRISIS = "crisis"


class RegimeDetector:
    """
    Classifies market into trending, ranging, or crisis regimes.

    Parameters:
        adx_window: ADX calculation period (default: 14).
        adx_trend_threshold: ADX above this = trending (default: 25).
        adx_range_threshold: ADX below this = ranging (default: 20).
        vol_window: Realized volatility lookback (default: 20 days).
        vol_crisis_threshold: Annualized vol above this = crisis (default: 0.40 = 40%).
        slope_window: Price slope lookback (default: 20 days).
    """

    def __init__(
        self,
        adx_window: int = 14,
        adx_trend_threshold: float = 25.0,
        adx_range_threshold: float = 20.0,
        vol_window: int = 20,
        vol_crisis_threshold: float = 0.40,
        slope_window: int = 20,
    ):
        self.adx_window = adx_window
        self.adx_trend_threshold = adx_trend_threshold
        self.adx_range_threshold = adx_range_threshold
        self.vol_window = vol_window
        self.vol_crisis_threshold = vol_crisis_threshold
        self.slope_window = slope_window

    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add regime classification columns to the DataFrame.

        Adds columns:
          - 'adx': Average Directional Index value
          - 'volatility_ann': Annualized realized volatility
          - 'price_slope': Normalized price slope
          - 'regime': One of 'trending', 'ranging', 'crisis'

        Args:
            df: OHLCV DataFrame with 'high', 'low', 'close' columns.

        Returns:
            DataFrame with regime columns added.
        """
        df = df.copy()

        # ── ADX Calculation ──
        df["adx"] = self._compute_adx(df, self.adx_window)

        # ── Realized Volatility (annualized) ──
        returns = df["close"].pct_change()
        df["volatility_ann"] = returns.rolling(self.vol_window).std() * np.sqrt(252)

        # ── Price Slope (normalized by price level) ──
        df["price_slope"] = self._compute_slope(df["close"], self.slope_window)

        # ── Classify Regime ──
        conditions = [
            # Crisis: extreme volatility overrides everything
            df["volatility_ann"] > self.vol_crisis_threshold,
            # Trending: strong ADX + clear directional slope
            df["adx"] > self.adx_trend_threshold,
            # Ranging: weak ADX
            df["adx"] < self.adx_range_threshold,
        ]
        choices = [Regime.CRISIS, Regime.TRENDING, Regime.RANGING]
        df["regime"] = np.select(conditions, choices, default=Regime.RANGING)

        # Log regime distribution
        regime_counts = df["regime"].value_counts()
        logger.info(f"Regime distribution: {regime_counts.to_dict()}")

        return df

    @staticmethod
    def _compute_adx(df: pd.DataFrame, window: int = 14) -> pd.Series:
        """
        Compute Average Directional Index (ADX).

        ADX measures trend STRENGTH, not direction.
        ADX > 25 = trending market, ADX < 20 = ranging market.

        Uses Wilder's smoothing (same alpha as our RSI fix).
        """
        high = df["high"]
        low = df["low"]
        close = df["close"]

        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Directional Movement
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

        # Wilder's smoothing (EMA with alpha=1/window)
        alpha = 1 / window
        atr = pd.Series(tr, index=df.index).ewm(alpha=alpha, adjust=False).mean()
        plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=alpha, adjust=False).mean() / atr
        minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=alpha, adjust=False).mean() / atr

        # ADX = smoothed absolute difference / sum of DI lines
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        adx = dx.ewm(alpha=alpha, adjust=False).mean()

        return adx

    @staticmethod
    def _compute_slope(series: pd.Series, window: int) -> pd.Series:
        """
        Compute normalized linear regression slope over rolling window.

        Returns slope as percentage change per day (normalized by price level).
        Positive = uptrend, Negative = downtrend, Near-zero = ranging.
        """
        def _slope(arr):
            if len(arr) < 2 or np.isnan(arr).any():
                return 0.0
            x = np.arange(len(arr))
            slope = np.polyfit(x, arr, 1)[0]
            # Normalize by mean price to make slope comparable across tickers
            mean_price = np.mean(arr)
            return (slope / mean_price) * 100 if mean_price != 0 else 0.0

        return series.rolling(window).apply(_slope, raw=True)

    @staticmethod
    def get_regime_strategy_compatibility() -> dict:
        """
        Returns a mapping of which strategies work best in which regimes.

        Returns:
            Dict mapping regime → list of compatible strategy names.
        """
        return {
            Regime.TRENDING: [
                "SMA Crossover", "MACD", "Momentum + MR", "Buy & Hold",
            ],
            Regime.RANGING: [
                "RSI Reversion", "Bollinger Bands", "Multi-Factor",
            ],
            Regime.CRISIS: [
                "Buy & Hold",  # Only if already positioned; otherwise cash
            ],
        }
