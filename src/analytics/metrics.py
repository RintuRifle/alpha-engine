"""
Performance metrics for backtesting results.

Implements: CAGR, Sharpe, Sortino, Calmar, Max Drawdown, Win Rate,
Profit Factor, Total Return, and Volatility.

All formulas follow standard quantitative finance conventions with
252 trading days per year for annualization.
"""

import pandas as pd
import numpy as np
from typing import List

from src.utils.logger import get_logger

logger = get_logger(__name__)

TRADING_DAYS_PER_YEAR = 252


class Metrics:
    """Collection of performance metrics for equity curves and trade history."""

    # ──────────────────────────────────────────────
    # Return Metrics
    # ──────────────────────────────────────────────

    @staticmethod
    def total_return(equity_df: pd.DataFrame) -> float:
        """Total return as a decimal (e.g., 0.15 = 15%)."""
        if equity_df.empty or len(equity_df) < 2:
            return 0.0
        start = equity_df["total_equity"].iloc[0]
        end = equity_df["total_equity"].iloc[-1]
        if start == 0:
            return 0.0
        return (end / start) - 1

    @staticmethod
    def cagr(equity_df: pd.DataFrame) -> float:
        """
        Compound Annual Growth Rate.

        CAGR = (End / Start) ^ (365 / days) - 1
        """
        if equity_df.empty or len(equity_df) < 2:
            return 0.0
        start_val = equity_df["total_equity"].iloc[0]
        end_val = equity_df["total_equity"].iloc[-1]
        if start_val <= 0:
            return 0.0

        # Ensure the index is DatetimeIndex before doing date arithmetic
        try:
            idx = pd.to_datetime(equity_df.index)
            days = (idx[-1] - idx[0]).days
        except Exception:
            # Fall back to counting rows (approx: 252 trading days/year)
            days = int(len(equity_df) * (365 / 252))

        if days <= 0:
            return 0.0
        return (end_val / start_val) ** (365.0 / days) - 1

    @staticmethod
    def volatility(equity_df: pd.DataFrame) -> float:
        """Annualized portfolio volatility (standard deviation of daily returns)."""
        if equity_df.empty or len(equity_df) < 2:
            return 0.0
        returns = equity_df["total_equity"].pct_change().dropna()
        return returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)

    # ──────────────────────────────────────────────
    # Risk-Adjusted Return Metrics
    # ──────────────────────────────────────────────

    @staticmethod
    def sharpe_ratio(equity_df: pd.DataFrame, risk_free_rate: float = 0.0) -> float:
        """
        Annualized Sharpe Ratio.

        Sharpe = (mean_return - risk_free) / std_return * sqrt(252)
        """
        if equity_df.empty or len(equity_df) < 2:
            return 0.0
        returns = equity_df["total_equity"].pct_change().dropna()
        if returns.std() == 0:
            return 0.0
        daily_rf = risk_free_rate / TRADING_DAYS_PER_YEAR
        excess_returns = returns - daily_rf
        return (excess_returns.mean() / excess_returns.std()) * np.sqrt(TRADING_DAYS_PER_YEAR)

    @staticmethod
    def sortino_ratio(equity_df: pd.DataFrame, risk_free_rate: float = 0.0) -> float:
        """
        Sortino Ratio — like Sharpe but only penalizes downside volatility.

        Sortino = (mean_return - risk_free) / downside_std * sqrt(252)

        Better than Sharpe because upside volatility is GOOD, not risky.
        """
        if equity_df.empty or len(equity_df) < 2:
            return 0.0
        returns = equity_df["total_equity"].pct_change().dropna()
        daily_rf = risk_free_rate / TRADING_DAYS_PER_YEAR
        excess_returns = returns - daily_rf

        # Downside deviation: std of only negative returns
        downside = excess_returns[excess_returns < 0]
        if downside.empty or downside.std() == 0:
            return 0.0 if excess_returns.mean() <= 0 else float("inf")

        return (excess_returns.mean() / downside.std()) * np.sqrt(TRADING_DAYS_PER_YEAR)

    @staticmethod
    def calmar_ratio(equity_df: pd.DataFrame) -> float:
        """
        Calmar Ratio = CAGR / |Max Drawdown|

        Measures return per unit of maximum drawdown risk.
        """
        cagr = Metrics.cagr(equity_df)
        mdd = abs(Metrics.max_drawdown(equity_df))
        if mdd == 0:
            return 0.0
        return cagr / mdd

    # ──────────────────────────────────────────────
    # Drawdown Metrics
    # ──────────────────────────────────────────────

    @staticmethod
    def max_drawdown(equity_df: pd.DataFrame) -> float:
        """
        Maximum Drawdown — the largest peak-to-trough decline.

        Returns a negative float (e.g., -0.25 = -25% drawdown).
        """
        if equity_df.empty or len(equity_df) < 2:
            return 0.0
        equity = equity_df["total_equity"]
        cummax = equity.cummax()
        drawdown = (equity - cummax) / cummax
        return drawdown.min()

    @staticmethod
    def max_drawdown_duration(equity_df: pd.DataFrame) -> int:
        """
        Maximum Drawdown Duration — longest consecutive run of trading days
        the portfolio stayed below its previous peak.

        Returns:
            Number of trading days in the longest drawdown period.
        """
        if equity_df.empty or len(equity_df) < 2:
            return 0
        equity = equity_df["total_equity"]
        cummax = equity.cummax()
        # Consider flat (equity == cummax) as NOT underwater
        is_underwater = equity < cummax

        max_duration = 0
        current_duration = 0
        for underwater in is_underwater:
            if underwater:
                current_duration += 1
                max_duration = max(max_duration, current_duration)
            else:
                current_duration = 0

        return max_duration

    # ──────────────────────────────────────────────
    # Trade-Level Metrics
    # ──────────────────────────────────────────────

    @staticmethod
    def win_rate(trade_history: List[dict]) -> float:
        """
        Win Rate — percentage of profitable round-trip trades.

        Matches BUY and SELL trades into round trips, calculates P&L
        for each, and returns the fraction that were profitable.

        Returns:
            Win rate as a decimal (e.g., 0.55 = 55%).
        """
        if not trade_history:
            return 0.0

        # Match BUY→SELL pairs to form round trips
        round_trips = Metrics._calculate_round_trips(trade_history)

        if not round_trips:
            return 0.0

        winning = sum(1 for pnl in round_trips if pnl > 0)
        return winning / len(round_trips)

    @staticmethod
    def profit_factor(trade_history: List[dict]) -> float:
        """
        Profit Factor = Gross Profit / Gross Loss

        > 1.0 = profitable system
        > 2.0 = very good system
        > 3.0 = excellent system
        """
        if not trade_history:
            return 0.0

        round_trips = Metrics._calculate_round_trips(trade_history)

        if not round_trips:
            return 0.0

        gross_profit = sum(pnl for pnl in round_trips if pnl > 0)
        gross_loss = abs(sum(pnl for pnl in round_trips if pnl < 0))

        if gross_loss == 0:
            return float("inf") if gross_profit > 0 else 0.0

        return gross_profit / gross_loss

    @staticmethod
    def _calculate_round_trips(trade_history: List[dict]) -> List[float]:
        """
        Match BUY and SELL trades into round trips and calculate P&L for each.

        Uses FIFO (First In, First Out) matching.

        Returns:
            List of P&L values for each completed round trip.
        """
        # Group by ticker
        buys: dict[str, list] = {}
        round_trip_pnls: list[float] = []

        for trade in trade_history:
            ticker = trade.get("ticker", "")
            action = trade.get("action", "")
            qty = trade.get("quantity", 0)
            price = trade.get("price", 0)
            commission = trade.get("commission", 0)

            if action == "BUY":
                if ticker not in buys:
                    buys[ticker] = []
                buys[ticker].append({"qty": qty, "price": price, "commission": commission})

            elif action == "SELL" and ticker in buys and buys[ticker]:
                # FIFO match with the oldest buy
                buy = buys[ticker].pop(0)
                matched_qty = min(buy["qty"], qty)

                buy_cost = matched_qty * buy["price"] + buy["commission"]
                sell_revenue = matched_qty * price - commission
                pnl = sell_revenue - buy_cost
                round_trip_pnls.append(pnl)

        return round_trip_pnls

    # ──────────────────────────────────────────────
    # All Metrics Summary
    # ──────────────────────────────────────────────

    @staticmethod
    def compute_all(equity_df: pd.DataFrame, trade_history: List[dict]) -> dict:
        """
        Compute all performance metrics at once.

        Returns:
            Dictionary with all metric names and values.
        """
        return {
            "total_return": Metrics.total_return(equity_df),
            "cagr": Metrics.cagr(equity_df),
            "sharpe_ratio": Metrics.sharpe_ratio(equity_df),
            "sortino_ratio": Metrics.sortino_ratio(equity_df),
            "calmar_ratio": Metrics.calmar_ratio(equity_df),
            "max_drawdown": Metrics.max_drawdown(equity_df),
            "max_dd_duration": Metrics.max_drawdown_duration(equity_df),
            "volatility": Metrics.volatility(equity_df),
            "win_rate": Metrics.win_rate(trade_history),
            "profit_factor": Metrics.profit_factor(trade_history),
            "total_trades": len(trade_history) // 2,
        }
