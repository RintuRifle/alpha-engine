"""
Buy and Hold strategy — the simplest possible benchmark.

Signal is always +1 (buy on day 1, hold forever). Every active strategy
should be compared against this to determine if it adds value over passive investing.
"""

import pandas as pd

from .base_strategy import BaseStrategy


class BuyAndHold(BaseStrategy):
    """
    BENCHMARK strategy: signal = +1 always.

    Use this to compare all other strategies. If your fancy strategy
    can't beat Buy & Hold, it's not worth trading.
    """

    @property
    def name(self) -> str:
        return "Buy & Hold"

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["signal"] = 1
        return df
