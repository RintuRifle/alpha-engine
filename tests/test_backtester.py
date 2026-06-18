"""
Unit tests for the backtesting engine.

Tests: BacktestEngine simulation, Portfolio tracking, transaction costs impact,
position sizing, and trade execution.
"""

import pytest
import pandas as pd
import numpy as np

from src.backtester.engine import BacktestEngine
from src.backtester.portfolio import Portfolio
from src.backtester.transaction_costs import TransactionCosts
from src.backtester.position_sizing import PositionSizer
from src.strategies.buy_and_hold import BuyAndHold


class TestBacktestEngine:
    def test_engine_produces_equity_curve(self, sample_ohlcv):
        """Engine should produce a non-empty equity curve."""
        strategy = BuyAndHold()
        df = strategy.generate_signals(sample_ohlcv)
        engine = BacktestEngine(data=df, ticker="TEST", initial_capital=10000.0)
        portfolio = engine.run()

        equity_df = portfolio.get_equity_df()
        assert not equity_df.empty
        assert "total_equity" in equity_df.columns
        assert len(equity_df) == len(sample_ohlcv)

    def test_engine_executes_trades(self, sample_ohlcv):
        """Buy & Hold should trigger at least 1 trade."""
        strategy = BuyAndHold()
        df = strategy.generate_signals(sample_ohlcv)
        engine = BacktestEngine(data=df, ticker="TEST", initial_capital=10000.0)
        portfolio = engine.run()
        assert len(portfolio.trade_history) > 0

    def test_engine_requires_signal_column(self, sample_ohlcv):
        """Should raise ValueError if no 'signal' column."""
        with pytest.raises(ValueError, match="signal"):
            BacktestEngine(data=sample_ohlcv, ticker="TEST")

    def test_cash_never_negative(self, sample_ohlcv):
        """Portfolio cash should never go below 0."""
        strategy = BuyAndHold()
        df = strategy.generate_signals(sample_ohlcv)
        engine = BacktestEngine(data=df, ticker="TEST", initial_capital=10000.0)
        portfolio = engine.run()
        equity_df = portfolio.get_equity_df()
        assert (equity_df["cash"] >= -0.01).all()  # Allow tiny float imprecision


class TestTransactionCosts:
    def test_buy_slippage_increases_price(self):
        """Buying should cost more due to slippage."""
        tc = TransactionCosts(commission_pct=0.001, slippage_pct=0.005)
        exec_price = tc.apply_costs(100.0, "BUY")
        assert exec_price > 100.0
        assert exec_price == pytest.approx(100.5)

    def test_sell_slippage_decreases_price(self):
        """Selling should receive less due to slippage."""
        tc = TransactionCosts(commission_pct=0.001, slippage_pct=0.005)
        exec_price = tc.apply_costs(100.0, "SELL")
        assert exec_price < 100.0
        assert exec_price == pytest.approx(99.5)

    def test_commission_is_percentage(self):
        """Commission should be a percentage of notional value."""
        tc = TransactionCosts(commission_pct=0.001)
        commission = tc.calculate_commission(10000.0)
        assert commission == pytest.approx(10.0)


class TestPositionSizer:
    def test_fixed_capital_sizing(self):
        """10% of $10,000 at $100/share = 10 shares."""
        sizer = PositionSizer("fixed_capital", allocation=0.10)
        qty = sizer.get_quantity(price=100.0, available_capital=10000.0)
        assert qty == 10

    def test_fixed_shares_sizing(self):
        """Should return the fixed number of shares."""
        sizer = PositionSizer("fixed_shares", shares=50)
        qty = sizer.get_quantity(price=100.0, available_capital=100000.0)
        assert qty == 50

    def test_fixed_shares_limited_by_capital(self):
        """If can't afford all shares, buy what's affordable."""
        sizer = PositionSizer("fixed_shares", shares=100)
        qty = sizer.get_quantity(price=100.0, available_capital=500.0)
        assert qty == 5  # Can only afford 5 shares

    def test_kelly_criterion(self):
        """Kelly should return a reasonable quantity."""
        sizer = PositionSizer("kelly", win_rate=0.6, avg_win=0.03, avg_loss=0.02)
        qty = sizer.get_quantity(price=100.0, available_capital=10000.0)
        assert qty > 0
        assert qty <= 100  # Should not allocate everything

    def test_zero_price_returns_zero(self):
        """Zero or negative price should return 0 shares."""
        sizer = PositionSizer("fixed_capital", allocation=0.10)
        assert sizer.get_quantity(price=0.0, available_capital=10000.0) == 0
        assert sizer.get_quantity(price=-10.0, available_capital=10000.0) == 0


class TestPortfolio:
    def test_initial_state(self):
        portfolio = Portfolio(10000.0)
        assert portfolio.cash == 10000.0
        assert portfolio.initial_capital == 10000.0
        assert len(portfolio.positions) == 0
        assert len(portfolio.trade_history) == 0

    def test_equity_tracking(self):
        portfolio = Portfolio(10000.0)
        portfolio.update_equity("2022-01-03", {"AAPL": 150.0})
        equity_df = portfolio.get_equity_df()
        assert len(equity_df) == 1
        assert equity_df["total_equity"].iloc[0] == 10000.0  # No positions yet
