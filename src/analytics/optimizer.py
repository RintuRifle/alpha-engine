"""
Parameter optimizer using grid search.

Exhaustively tests all parameter combinations, backtests each,
and returns the combination that maximizes Sharpe ratio.
"""

import itertools
from typing import Any, Dict, List, Type

import pandas as pd

from src.analytics.metrics import Metrics
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Optimizer:
    """Grid search optimizer for strategy parameters."""

    @staticmethod
    def grid_search(
        strategy_class: Type,
        param_grid: Dict[str, List[Any]],
        data: pd.DataFrame,
        backtest_engine_class: Type,
        ticker: str = "AAPL",
        initial_capital: float = 10000.0,
        metric: str = "sharpe_ratio",
    ) -> Dict[str, Any]:
        """
        Exhaustive grid search over all parameter combinations.

        Args:
            strategy_class: Strategy class to optimize.
            param_grid: Dict mapping param names to value lists.
            data: OHLCV DataFrame.
            backtest_engine_class: BacktestEngine class.
            ticker: Stock ticker.
            initial_capital: Starting capital per backtest.
            metric: Metric to maximize (default: sharpe_ratio).

        Returns:
            Dict with best_params, best_metric_value, and all_results.
        """
        param_names = list(param_grid.keys())
        combinations = list(itertools.product(*param_grid.values()))
        total = len(combinations)
        logger.info(f"Grid search: {total} combos for {strategy_class.__name__}")

        all_results: List[Dict[str, Any]] = []
        best_value = float("-inf")
        best_params: Dict[str, Any] = {}

        for i, combo in enumerate(combinations):
            params = dict(zip(param_names, combo))
            try:
                strategy = strategy_class(**params)
                df_signals = strategy.generate_signals(data)
                engine = backtest_engine_class(
                    data=df_signals, ticker=ticker, initial_capital=initial_capital
                )
                portfolio = engine.run()
                equity_df = portfolio.get_equity_df()
                metrics = Metrics.compute_all(equity_df, portfolio.trade_history)
                val = metrics.get(metric, 0.0)
                if val in (float("inf"), float("-inf")):
                    val = 0.0

                result = {"params": params, metric: val,
                          "cagr": metrics.get("cagr", 0.0),
                          "max_drawdown": metrics.get("max_drawdown", 0.0)}
                all_results.append(result)

                if val > best_value:
                    best_value = val
                    best_params = params.copy()

                if (i + 1) % max(1, total // 10) == 0:
                    logger.info(f"Progress: {i+1}/{total} | Best {metric}={best_value:.4f}")
            except Exception as e:
                logger.warning(f"Combo {params} failed: {e}")

        all_results.sort(key=lambda x: x.get(metric, 0.0), reverse=True)
        logger.info(f"Best {metric}={best_value:.4f} with {best_params}")

        return {
            "best_params": best_params,
            "best_metric_value": best_value,
            "metric_name": metric,
            "total_combinations": total,
            "all_results": all_results,
        }
