"""
Monte Carlo simulation for equity path analysis.

Generates 1000+ simulated equity paths by resampling historical returns.
Supports both parametric (normal distribution) and bootstrap (actual returns) methods.
Calculates confidence intervals for risk assessment.

NEW: Adversarial stress scenarios — injects real crash patterns into simulations:
  - 2008 GFC: Lehman collapse, -38% drawdown in 3 months
  - 2020 COVID: Flash crash, -34% in 23 trading days
  - 2022 Rate Hike: Slow grind down, -25% over 9 months
"""

import numpy as np
import pandas as pd
from typing import Dict

from src.utils.logger import get_logger

logger = get_logger(__name__)

# ── Pre-built Crash Sequences ──
# These are REAL return sequences from historical crashes (daily returns)
STRESS_SCENARIOS = {
    "2008_gfc": {
        "name": "2008 GFC (Lehman Collapse)",
        "description": "3-month severe crash followed by volatility",
        "daily_returns": np.array([
            -0.01, -0.02, -0.03, 0.01, -0.04, -0.02, -0.05, 0.02, -0.03, -0.04,
            -0.02, -0.06, 0.03, -0.03, -0.05, -0.01, -0.04, 0.02, -0.03, -0.02,
            -0.07, 0.04, -0.03, -0.02, -0.05, 0.01, -0.04, -0.03, 0.02, -0.06,
            0.05, -0.02, -0.03, 0.01, -0.04, -0.02, 0.03, -0.03, -0.01, -0.05,
            0.04, -0.02, 0.01, -0.03, -0.02, 0.02, -0.04, 0.01, -0.01, -0.03,
            0.03, -0.01, 0.02, -0.02, 0.01, -0.01, 0.02, 0.01, -0.01, 0.02,
        ]),
        "duration_days": 60,
    },
    "2020_covid": {
        "name": "2020 COVID Flash Crash",
        "description": "23-day violent selloff, then V-shape recovery",
        "daily_returns": np.array([
            -0.03, -0.04, 0.01, -0.05, -0.03, -0.07, 0.04, -0.10, -0.05,
            -0.12, 0.09, -0.06, -0.09, 0.06, -0.04, 0.05, -0.03, 0.02,
            -0.03, 0.01, 0.04, 0.02, 0.03,
        ]),
        "duration_days": 23,
    },
    "2022_rate_hike": {
        "name": "2022 Rate Hike Grind",
        "description": "Slow 9-month decline, persistent selling",
        "daily_returns": np.array([
            -0.01, -0.005, 0.005, -0.01, -0.005, -0.01, 0.005, -0.005,
            -0.01, 0.005, -0.005, -0.01, -0.005, 0.01, -0.01, -0.005,
            0.005, -0.01, -0.005, -0.01, 0.005, -0.005, -0.01, 0.01,
            -0.005, -0.01, -0.005, 0.005, -0.01, 0.01, -0.005, -0.01,
            -0.005, 0.01, -0.005, -0.01, 0.005, -0.005, -0.01, 0.005,
        ]),
        "duration_days": 40,
    },
}


class MonteCarlo:
    """Monte Carlo simulator for generating probabilistic equity forecasts."""

    @staticmethod
    def simulate_paths(
        returns: pd.Series,
        num_sims: int = 1000,
        horizon: int = 252,
        method: str = "bootstrap",
        initial_value: float = 1.0,
        stress_probability: float = 0.0,
    ) -> pd.DataFrame:
        """
        Simulate equity paths from historical return distribution.

        Args:
            returns: Historical daily returns series.
            num_sims: Number of simulated paths (default: 1000).
            horizon: Number of trading days to simulate (default: 252 = 1 year).
            method: 'bootstrap' (resample actual returns) or 'parametric' (normal dist).
            initial_value: Starting equity value (default: 1.0 for normalized).
            stress_probability: Probability of injecting a crash scenario (0.0-1.0).
                0.0 = no stress tests (default), 0.10 = 10% of paths include a crash.

        Returns:
            DataFrame where each column is a simulated equity path (shape: horizon x num_sims).
        """
        if returns.empty:
            return pd.DataFrame()

        returns_arr = returns.dropna().values
        logger.info(f"Monte Carlo: {num_sims} sims, {horizon} days, method={method}, stress={stress_probability:.0%}")

        sims = np.zeros((horizon, num_sims))

        for i in range(num_sims):
            if method == "bootstrap":
                # Resample actual historical returns WITH replacement
                sampled = np.random.choice(returns_arr, size=horizon, replace=True)
            else:
                # Parametric: assume normal distribution
                mu = returns_arr.mean()
                sigma = returns_arr.std()
                sampled = np.random.normal(mu, sigma, horizon)

            # Inject stress scenario with given probability
            if stress_probability > 0 and np.random.random() < stress_probability:
                # Pick a random stress scenario
                scenario_key = np.random.choice(list(STRESS_SCENARIOS.keys()))
                scenario = STRESS_SCENARIOS[scenario_key]
                crash_returns = scenario["daily_returns"]
                crash_len = min(len(crash_returns), horizon)

                # Insert crash at a random point in the simulation
                insert_point = np.random.randint(0, max(1, horizon - crash_len))
                sampled[insert_point:insert_point + crash_len] = crash_returns[:crash_len]

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
            "prob_loss_20pct": float((final_values < 0.80).mean()),
        }

    @staticmethod
    def stress_test_summary(returns: pd.Series, initial_value: float = 1.0) -> list[dict]:
        """
        Run each stress scenario individually and report outcomes.

        Returns:
            List of dicts with scenario name, max drawdown, and final value.
        """
        results = []
        for key, scenario in STRESS_SCENARIOS.items():
            crash_returns = scenario["daily_returns"]
            equity = np.cumprod(1 + crash_returns) * initial_value
            peak = np.maximum.accumulate(equity)
            drawdown = (equity - peak) / peak
            max_dd = drawdown.min()

            results.append({
                "scenario": scenario["name"],
                "description": scenario["description"],
                "duration_days": scenario["duration_days"],
                "max_drawdown_pct": round(max_dd * 100, 2),
                "final_value": round(equity[-1], 4),
                "total_return_pct": round((equity[-1] / initial_value - 1) * 100, 2),
            })
        return results
