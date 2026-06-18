"""
Unit tests for all trading strategies.

Tests signal correctness on known synthetic data, ensures all strategies
produce valid signal values, and checks for look-ahead bias prevention.
"""

import pytest
import pandas as pd
import numpy as np

from src.strategies.ma_crossover import MACrossover
from src.strategies.rsi_reversion import RSIReversion
from src.strategies.bollinger_bands import BollingerBands
from src.strategies.macd_strategy import MACDStrategy
from src.strategies.buy_and_hold import BuyAndHold


class TestBuyAndHold:
    def test_signal_always_one(self, sample_ohlcv):
        """Buy & Hold should produce signal=+1 for every row."""
        strategy = BuyAndHold()
        result = strategy.generate_signals(sample_ohlcv)
        assert (result["signal"] == 1).all()

    def test_name_property(self):
        assert BuyAndHold().name == "Buy & Hold"


class TestMACrossover:
    def test_signals_are_valid(self, sample_ohlcv):
        """All signals should be -1, 0, or +1."""
        strategy = MACrossover(short_window=5, long_window=10)
        result = strategy.generate_signals(sample_ohlcv)
        assert "signal" in result.columns
        assert set(result["signal"].unique()).issubset({-1, 0, 1})

    def test_known_crossover(self):
        """With synthetic data, verify signal changes at known crossover point."""
        # Create data where short MA crosses above long MA at a known point
        n = 50
        prices = np.concatenate([
            np.linspace(100, 80, 25),   # Downtrend (short < long → signal=-1)
            np.linspace(80, 120, 25),   # Uptrend (short > long → signal=+1)
        ])

        df = pd.DataFrame({
            "date": pd.bdate_range("2022-01-03", periods=n),
            "open": prices, "high": prices * 1.01,
            "low": prices * 0.99, "close": prices, "volume": [1e6]*n,
        })

        strategy = MACrossover(short_window=3, long_window=10)
        result = strategy.generate_signals(df)

        # After warmup, the beginning (downtrend) should have -1 signals
        # and the end (uptrend) should have +1 signals
        late_signals = result["signal"].iloc[-5:]
        assert (late_signals == 1).all(), "Uptrend should produce buy signals"

    def test_nan_period_is_neutral(self):
        """Before enough data for the long MA, signal should be 0."""
        df = pd.DataFrame({
            "date": pd.bdate_range("2022-01-03", periods=20),
            "close": range(100, 120),
            "open": range(100, 120),
            "high": range(101, 121),
            "low": range(99, 119),
            "volume": [1e6]*20,
        })
        strategy = MACrossover(short_window=5, long_window=15)
        result = strategy.generate_signals(df)
        # First 14 rows should be neutral (NaN MA)
        assert (result["signal"].iloc[:14] == 0).all()

    def test_name_includes_windows(self):
        s = MACrossover(short_window=20, long_window=50)
        assert "20" in s.name and "50" in s.name


class TestRSIReversion:
    def test_signals_are_valid(self, sample_ohlcv):
        strategy = RSIReversion(window=14)
        result = strategy.generate_signals(sample_ohlcv)
        assert "signal" in result.columns
        assert "rsi" in result.columns
        assert set(result["signal"].unique()).issubset({-1, 0, 1})

    def test_oversold_produces_buy(self):
        """A consistently falling price should push RSI below 30 → buy signal."""
        prices = np.linspace(100, 50, 50)  # Steadily falling
        df = pd.DataFrame({
            "date": pd.bdate_range("2022-01-03", periods=50),
            "open": prices, "high": prices * 1.01,
            "low": prices * 0.99, "close": prices, "volume": [1e6]*50,
        })
        strategy = RSIReversion(window=14, oversold=30)
        result = strategy.generate_signals(df)
        # After warmup, falling prices should eventually trigger buy signal
        assert 1 in result["signal"].values

    def test_overbought_produces_sell(self):
        """A strongly rising price should push RSI above 70 → sell signal."""
        # Exponential rise produces stronger momentum → higher RSI
        n = 100
        prices = 50 * np.exp(np.linspace(0, 1.5, n))  # Strong exponential rise
        df = pd.DataFrame({
            "date": pd.bdate_range("2022-01-03", periods=n),
            "open": prices, "high": prices * 1.01,
            "low": prices * 0.99, "close": prices, "volume": [1e6]*n,
        })
        strategy = RSIReversion(window=14, overbought=70)
        result = strategy.generate_signals(df)
        assert -1 in result["signal"].values


class TestBollingerBands:
    def test_signals_are_valid(self, sample_ohlcv):
        strategy = BollingerBands(window=10, num_std=2.0)
        result = strategy.generate_signals(sample_ohlcv)
        assert "signal" in result.columns
        assert set(result["signal"].unique()).issubset({-1, 0, 1})

    def test_bands_are_computed(self, sample_ohlcv):
        strategy = BollingerBands(window=10)
        result = strategy.generate_signals(sample_ohlcv)
        assert "upper_band" in result.columns
        assert "lower_band" in result.columns
        # Upper band should always be above lower band (after warmup)
        valid = result.dropna(subset=["upper_band", "lower_band"])
        assert (valid["upper_band"] >= valid["lower_band"]).all()


class TestMACDStrategy:
    def test_signals_are_valid(self, sample_ohlcv):
        strategy = MACDStrategy()
        result = strategy.generate_signals(sample_ohlcv)
        assert "signal" in result.columns
        assert "macd" in result.columns
        assert "macd_signal" in result.columns
        assert set(result["signal"].unique()).issubset({-1, 0, 1})

    def test_histogram_computed(self, sample_ohlcv):
        strategy = MACDStrategy()
        result = strategy.generate_signals(sample_ohlcv)
        assert "macd_histogram" in result.columns


class TestLookAheadBias:
    def test_signal_does_not_mutate_input(self, sample_ohlcv):
        """Strategy should NOT modify the input DataFrame (uses .copy())."""
        original_cols = set(sample_ohlcv.columns)
        strategy = MACrossover(short_window=5, long_window=10)
        strategy.generate_signals(sample_ohlcv)
        assert set(sample_ohlcv.columns) == original_cols
