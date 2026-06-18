"""
Monte Carlo simulation for equity path analysis.

Generates 1000+ simulated equity paths by resampling historical returns.
Supports both parametric (normal distribution) and bootstrap (actual returns) methods.
Calculates confidence intervals for risk assessment.
"""

import numpy as np
import pandas as pd
from typing import Dict

from src.utils.logger import get_logger

logger = get_logger(__name__)


class MonteCarlo:
    """Monte Carlo simulator for generating probabilistic equity forecasts."""

    @staticmethod
    def simulate_paths(
        returns: pd.Series,
        num_sims: int = 1000,
        horizon: int = 252,
        method: str = "bootstrap",
        initial_value: float = 1.0,
    ) -> pd.DataFrame:
        """
        Simulate equity paths from historical return distribution.

        Args:
            returns: Historical daily returns series.
            num_sims: Number of simulated paths (default: 1000).
            horizon: Number of trading days to simulate (default: 252 = 1 year).
            method: 'bootstrap' (resample actual returns) or 'parametric' (normal dist).
            initial_value: Starting equity value (default: 1.0 for normalized).

        Returns:
            DataFrame where each column is a simulated equity path (shape: horizon x num_sims).
        """
        if returns.empty:
            return pd.DataFrame()

        returns_arr = returns.dropna().values
        logger.info(f"Monte Carlo: {num_sims} sims, {horizon} days, method={method}")

        sims = np.zeros((horizon, num_sims))

        if method == "bootstrap":
            # Resample actual historical returns WITH replacement
            for i in range(num_sims):
                sampled = np.random.choice(returns_arr, size=horizon, replace=True)
                sims[:, i] = np.cumprod(1 + sampled) * initial_value
        else:
            # Parametric: assume normal distribution
            mu = returns_arr.mean()
            sigma = returns_arr.std()
            for i in range(num_sims):
                sampled = np.random.normal(mu, sigma, horizon)
                sims[:, i] = np.cumprod(1 + sampled) * initial_value

        return pd.DataFrame(sims, columns=[f"sim_{i}" for i in range(num_sims)])

    @staticmethod
    def get_percentile_paths(sim_df: pd.DataFrame) -> Dict[str, pd.Series]:
        """
        Extract key percentile paths from simulation results.

        Returns:
            Dict with percentile labels → equity path Series.
        """
        if sim_df.empty:
            return {}

        return {
            "p5": sim_df.quantile(0.05, axis=1),
            "p25": sim_df.quantile(0.25, axis=1),
            "p50": sim_df.quantile(0.50, axis=1),
            "p75": sim_df.quantile(0.75, axis=1),
            "p95": sim_df.quantile(0.95, axis=1),
        }

    @staticmethod
    def summary_stats(sim_df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate summary statistics from simulation end values.

        Returns:
            Dict with mean, median, std, and percentile final values.
        """
        if sim_df.empty:
            return {}

        final_values = sim_df.iloc[-1]
        return {
            "mean_final": float(final_values.mean()),
            "median_final": float(final_values.median()),
            "std_final": float(final_values.std()),
            "worst_case_5pct": float(final_values.quantile(0.05)),
            "best_case_95pct": float(final_values.quantile(0.95)),
            "prob_profit": float((final_values > 1.0).mean()),
        }
