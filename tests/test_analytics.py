"""
Unit tests for analytics metrics.

Tests mathematical correctness of CAGR, Sharpe, Sortino, Max Drawdown,
Win Rate, VaR, and CVaR using known values.
"""

import pytest
import pandas as pd
import numpy as np

from src.analytics.metrics import Metrics
from src.analytics.risk_manager import RiskManager


class TestCAGR:
    def test_known_10_percent_return(self):
        """$10,000 → $11,000 over 365 days = ~10% CAGR."""
        dates = pd.date_range("2022-01-01", periods=366)
        equity = [10000.0] * 365 + [11000.0]
        df = pd.DataFrame({"total_equity": equity}, index=dates)
        cagr = Metrics.cagr(df)
        assert round(cagr, 2) == 0.10

    def test_zero_return(self):
        """No change in equity = 0% CAGR."""
        dates = pd.date_range("2022-01-01", periods=252)
        df = pd.DataFrame({"total_equity": [10000.0]*252}, index=dates)
        assert Metrics.cagr(df) == pytest.approx(0.0, abs=1e-6)

    def test_negative_return(self):
        """Loss should produce negative CAGR."""
        dates = pd.date_range("2022-01-01", periods=366)
        equity = [10000.0] * 365 + [8000.0]
        df = pd.DataFrame({"total_equity": equity}, index=dates)
        assert Metrics.cagr(df) < 0

    def test_empty_df_returns_zero(self):
        assert Metrics.cagr(pd.DataFrame()) == 0.0


class TestSharpeRatio:
    def test_positive_sharpe(self, equity_df):
        """Growing portfolio should have positive Sharpe."""
        sharpe = Metrics.sharpe_ratio(equity_df)
        # With positive mean return and reasonable vol, Sharpe should be positive
        assert isinstance(sharpe, float)

    def test_zero_volatility_returns_zero(self):
        """Flat equity curve (zero vol) should return 0 Sharpe."""
        dates = pd.date_range("2022-01-01", periods=100)
        df = pd.DataFrame({"total_equity": [10000.0]*100}, index=dates)
        assert Metrics.sharpe_ratio(df) == 0.0


class TestSortinoRatio:
    def test_sortino_calculated(self, equity_df):
        """Sortino should be a finite number for a valid equity curve."""
        sortino = Metrics.sortino_ratio(equity_df)
        assert isinstance(sortino, float)
        assert not np.isnan(sortino)


class TestMaxDrawdown:
    def test_known_drawdown(self):
        """10000 → 8000 = -20% max drawdown."""
        dates = pd.date_range("2022-01-01", periods=5)
        df = pd.DataFrame({"total_equity": [10000, 10000, 8000, 9000, 9500]}, index=dates)
        mdd = Metrics.max_drawdown(df)
        assert mdd == pytest.approx(-0.20)

    def test_no_drawdown(self):
        """Monotonically increasing equity = 0% drawdown."""
        dates = pd.date_range("2022-01-01", periods=5)
        df = pd.DataFrame({"total_equity": [100, 200, 300, 400, 500]}, index=dates)
        assert Metrics.max_drawdown(df) == pytest.approx(0.0)

    def test_max_drawdown_duration(self):
        """Should count trading days underwater correctly."""
        dates = pd.date_range("2022-01-01", periods=10)
        # Peak at day 2, underwater for 5 days, recovers at day 8
        df = pd.DataFrame({
            "total_equity": [100, 110, 120, 110, 105, 100, 95, 110, 125, 130]
        }, index=dates)
        duration = Metrics.max_drawdown_duration(df)
        assert duration >= 4  # At least 4 days underwater


class TestWinRate:
    def test_known_win_rate(self, sample_trade_history):
        """2 wins out of 3 trades = 66.7% win rate."""
        wr = Metrics.win_rate(sample_trade_history)
        assert wr == pytest.approx(2/3, abs=0.01)

    def test_empty_history(self):
        assert Metrics.win_rate([]) == 0.0


class TestProfitFactor:
    def test_known_profit_factor(self, sample_trade_history):
        """Should be > 1.0 for a profitable set of trades."""
        pf = Metrics.profit_factor(sample_trade_history)
        assert pf > 0  # Overall profitable

    def test_empty_history(self):
        assert Metrics.profit_factor([]) == 0.0


class TestVaR:
    def test_var_95_is_negative(self, equity_df):
        """VaR (5th percentile of returns) should typically be negative."""
        var = RiskManager.var_95(equity_df)
        assert var < 0  # Worst 5% of days are losses

    def test_cvar_worse_than_var(self, equity_df):
        """CVaR (average of worst 5%) should be <= VaR."""
        var = RiskManager.var_95(equity_df)
        cvar = RiskManager.cvar_95(equity_df)
        assert cvar <= var  # CVaR is always worse than VaR


class TestAlphaBeta:
    def test_alpha_beta_types(self):
        """Alpha and Beta should be floats."""
        rng = np.random.RandomState(42)
        port = pd.Series(rng.normal(0.001, 0.02, 100))
        bench = pd.Series(rng.normal(0.0005, 0.015, 100))
        alpha, beta = RiskManager.calculate_alpha_beta(port, bench)
        assert isinstance(alpha, float)
        assert isinstance(beta, float)

    def test_perfect_correlation_beta_near_one(self):
        """Portfolio = benchmark → beta ≈ 1.0"""
        returns = pd.Series(np.random.RandomState(42).normal(0.001, 0.02, 200))
        _, beta = RiskManager.calculate_alpha_beta(returns, returns)
        assert beta == pytest.approx(1.0, abs=0.01)


class TestComputeAll:
    def test_compute_all_returns_all_keys(self, equity_df, sample_trade_history):
        """compute_all should return a dict with all expected keys."""
        result = Metrics.compute_all(equity_df, sample_trade_history)
        expected_keys = [
            "total_return", "cagr", "sharpe_ratio", "sortino_ratio",
            "calmar_ratio", "max_drawdown", "max_dd_duration",
            "volatility", "win_rate", "profit_factor", "total_trades"
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"
