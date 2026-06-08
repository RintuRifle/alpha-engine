import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy

class MACrossover(BaseStrategy):
    def __init__(self, short_window: int = 50, long_window: int = 200):
        super().__init__(short_window=short_window, long_window=long_window)
        self.short_window = short_window
        self.long_window = long_window

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['short_ma'] = df['close'].rolling(window=self.short_window).mean()
        df['long_ma'] = df['close'].rolling(window=self.long_window).mean()
        
        # 1 if short > long else 0
        df['signal'] = 0
        df.loc[df['short_ma'] > df['long_ma'], 'signal'] = 1
        df.loc[df['short_ma'] <= df['long_ma'], 'signal'] = -1
        
        return df
