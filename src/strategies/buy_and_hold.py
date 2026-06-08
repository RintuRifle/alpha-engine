import pandas as pd
from .base_strategy import BaseStrategy

class BuyAndHold(BaseStrategy):
    """BENCHMARK: signal = +1 always."""
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['signal'] = 1
        return df
