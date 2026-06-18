"""
Risk management metrics for portfolio analysis.

Implements VaR, CVaR, Alpha, Beta, and maximum drawdown duration.
These metrics help assess the risk profile of a trading strategy
beyond just return-focused metrics.
"""

import pandas as pd
import numpy as np
from typing import Tuple

from src.utils.logger import get_logger

logger = get_logger(__name__)


class RiskManager:
    """
    Portfolio risk analytics — measures downside risk, tail risk,
    and market-relative performance.
    """

    @staticmethod
    def var_95(equity_df: pd.DataFrame) -> float:
        """
        Value at Risk (95% confidence).

        The worst expected daily loss that should NOT be exceeded
        95% of the time. Returns a negative number.

        Example: VaR = -0.02 means on 95% of days, you won't lose more than 2%.
        """
        if equity_df.empty or len(equity_df) < 2:
            return 0.0
        returns = equity_df["total_equity"].pct_change().dropna()
        return float(np.percentile(returns, 5))

    @staticmethod
    def cvar_95(equity_df: pd.DataFrame) -> float:
        """
        Conditional VaR (Expected Shortfall) at 95% confidence.

        Average loss in the worst 5% of days. Always worse than VaR.
        This is what happens in the TAIL of the distribution.
        """
        if equity_df.empty or len(equity_df) < 2:
            return 0.0
        returns = equity_df["total_equity"].pct_change().dropna()
        var = float(np.percentile(returns, 5))
        tail = returns[returns <= var]
        if tail.empty:
            return var
        return float(tail.mean())

    @staticmethod
    def calculate_alpha_beta(
        portfolio_returns: pd.Series,
        benchmark_returns: pd.Series,
    ) -> Tuple[float, float]:
        """
        Calculate Alpha and Beta relative to a benchmark.

        Alpha: Annualized excess return beyond what Beta predicts.
               Positive alpha = strategy adds value beyond market exposure.

        Beta: Sensitivity to benchmark movements.
              Beta > 1 = more volatile than market.
              Beta < 1 = less volatile than market.
              Beta = 0 = uncorrelated with market.

        Args:
            portfolio_returns: Daily returns of the portfolio.
            benchmark_returns: Daily returns of the benchmark (e.g., SPY).

        Returns:
            Tuple of (annualized_alpha, beta).
        """
        if portfolio_returns.empty or benchmark_returns.empty:
            return 0.0, 1.0

        # Align both series on common dates
        aligned = pd.concat(
            [portfolio_returns, benchmark_returns], axis=1, join="inner"
        ).dropna()

        if aligned.empty or len(aligned) < 10:
            return 0.0, 1.0

        port = aligned.iloc[:, 0].values
        bench = aligned.iloc[:, 1].values

        # Beta = Cov(portfolio, benchmark) / Var(benchmark)
        cov_matrix = np.cov(port, bench)
        cov = cov_matrix[0, 1]
        var = cov_matrix[1, 1]
        beta = cov / var if var != 0 else 1.0

        # Alpha = mean(portfolio) - beta * mean(benchmark), annualized
        alpha = (port.mean() - beta * bench.mean()) * 252

        return float(alpha), float(beta)

    @staticmethod
    def information_ratio(
        portfolio_returns: pd.Series,
        benchmark_returns: pd.Series,
    ) -> float:
        """
        Information Ratio = (portfolio_return - benchmark_return) / tracking_error

        Measures risk-adjusted excess return relative to benchmark.
        Higher is better. > 0.5 is good, > 1.0 is excellent.
        """
        if portfolio_returns.empty or benchmark_returns.empty:
            return 0.0

        aligned = pd.concat(
            [portfolio_returns, benchmark_returns], axis=1, join="inner"
        ).dropna()

        if aligned.empty:
            return 0.0

        excess = aligned.iloc[:, 0] - aligned.iloc[:, 1]
        tracking_error = excess.std()

        if tracking_error == 0:
            return 0.0

        return float((excess.mean() / tracking_error) * np.sqrt(252))

    @staticmethod
    def compute_all_risk(
        equity_df: pd.DataFrame,
        portfolio_returns: pd.Series | None = None,
        benchmark_returns: pd.Series | None = None,
    ) -> dict:
        """
        Compute all risk metrics at once.

        Returns:
            Dictionary with all risk metric names and values.
        """
        result = {
            "var_95": RiskManager.var_95(equity_df),
            "cvar_95": RiskManager.cvar_95(equity_df),
        }

        if portfolio_returns is not None and benchmark_returns is not None:
            alpha, beta = RiskManager.calculate_alpha_beta(
                portfolio_returns, benchmark_returns
            )
            result["alpha"] = alpha
            result["beta"] = beta
            result["information_ratio"] = RiskManager.information_ratio(
                portfolio_returns, benchmark_returns
            )
        else:
            result["alpha"] = 0.0
            result["beta"] = 1.0
            result["information_ratio"] = 0.0

        return result
