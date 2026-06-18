"""
Walk-Forward Analysis for out-of-sample testing.

Implements both simple train/test split and rolling window walk-forward
analysis to detect overfitting. If a strategy only works on training
data but fails on test data, it's likely overfit.

This is CRITICAL for honest strategy evaluation.
"""

from typing import List, Tuple, Optional, Type

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)


class WalkForward:
    """
    Out-of-sample testing framework.

    Supports:
    1. Simple split: 70% train / 30% test
    2. Rolling window: Multiple train/test windows that slide forward in time
    """

    @staticmethod
    def split_data(
        df: pd.DataFrame, train_ratio: float = 0.7
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Simple train/test split.

        Args:
            df: Full dataset.
            train_ratio: Fraction for training (default: 70%).

        Returns:
            Tuple of (train_df, test_df).
        """
        if df.empty:
            return df, df

        split_idx = int(len(df) * train_ratio)
        train = df.iloc[:split_idx].copy()
        test = df.iloc[split_idx:].copy()

        logger.info(
            f"Walk-Forward Split: {len(train)} train rows ({train_ratio*100:.0f}%), "
            f"{len(test)} test rows ({(1-train_ratio)*100:.0f}%)"
        )
        return train, test

    @staticmethod
    def rolling_windows(
        df: pd.DataFrame,
        n_splits: int = 5,
        train_ratio: float = 0.7,
    ) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        Generate rolling train/test windows.

        Each window slides forward, so later windows use more recent data.
        This mimics real-world deployment where you'd retrain periodically.

        Example with n_splits=3 and 1000 rows:
          Window 1: train [0:233]    test [233:333]
          Window 2: train [333:567]  test [567:667]
          Window 3: train [667:900]  test [900:1000]

        Args:
            df: Full dataset sorted by date.
            n_splits: Number of rolling windows.
            train_ratio: Fraction of each window for training.

        Returns:
            List of (train_df, test_df) tuples.
        """
        if df.empty or n_splits <= 0:
            return []

        total_len = len(df)
        window_size = total_len // n_splits
        windows: List[Tuple[pd.DataFrame, pd.DataFrame]] = []

        for i in range(n_splits):
            start = i * window_size
            end = start + window_size if i < n_splits - 1 else total_len

            window_df = df.iloc[start:end]
            split_idx = int(len(window_df) * train_ratio)

            train = window_df.iloc[:split_idx].copy()
            test = window_df.iloc[split_idx:].copy()

            if not train.empty and not test.empty:
                windows.append((train, test))
                logger.info(
                    f"Window {i+1}/{n_splits}: "
                    f"train [{start}:{start+split_idx}] ({len(train)} rows), "
                    f"test [{start+split_idx}:{end}] ({len(test)} rows)"
                )

        return windows

    @staticmethod
    def run_walk_forward(
        df: pd.DataFrame,
        strategy_class: Type,
        strategy_params: dict,
        backtest_engine_class: Type,
        ticker: str,
        n_splits: int = 5,
        train_ratio: float = 0.7,
        initial_capital: float = 10000.0,
    ) -> List[dict]:
        """
        Run a full walk-forward analysis.

        For each rolling window:
        1. Generate signals on the test data using the strategy
        2. Run a backtest on the test data
        3. Record the metrics

        Args:
            df: Full OHLCV dataset.
            strategy_class: Strategy class (not instance).
            strategy_params: Parameters to pass to the strategy constructor.
            backtest_engine_class: BacktestEngine class.
            ticker: Stock ticker symbol.
            n_splits: Number of rolling windows.
            train_ratio: Train/test ratio per window.
            initial_capital: Starting capital per window.

        Returns:
            List of dicts with metrics for each window.
        """
        windows = WalkForward.rolling_windows(df, n_splits, train_ratio)
        results = []

        for i, (train_df, test_df) in enumerate(windows):
            try:
                # Create strategy and generate signals on test data
                strategy = strategy_class(**strategy_params)
                test_with_signals = strategy.generate_signals(test_df)

                # Run backtest on test data
                engine = backtest_engine_class(
                    data=test_with_signals,
                    ticker=ticker,
                    initial_capital=initial_capital,
                )
                portfolio = engine.run()
                equity_df = portfolio.get_equity_df()

                if not equity_df.empty:
                    start_eq = equity_df["total_equity"].iloc[0]
                    end_eq = equity_df["total_equity"].iloc[-1]
                    ret = (end_eq / start_eq - 1) if start_eq > 0 else 0.0
                else:
                    ret = 0.0

                result = {
                    "window": i + 1,
                    "train_size": len(train_df),
                    "test_size": len(test_df),
                    "test_return": ret,
                    "num_trades": len(portfolio.trade_history),
                }
                results.append(result)

                logger.info(
                    f"Window {i+1}: return={ret*100:+.2f}%, trades={len(portfolio.trade_history)}"
                )

            except Exception as e:
                logger.warning(f"Window {i+1} failed: {e}")
                results.append({
                    "window": i + 1,
                    "train_size": len(train_df),
                    "test_size": len(test_df),
                    "test_return": 0.0,
                    "num_trades": 0,
                    "error": str(e),
                })

        return results
