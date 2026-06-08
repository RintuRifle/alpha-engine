import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy

class RSIReversion(BaseStrategy):
    def __init__(self, window: int = 14, overbought: int = 70, oversold: int = 30):
        super().__init__(window=window, overbought=overbought, oversold=oversold)
        self.window = window
        self.overbought = overbought
        self.oversold = oversold

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.window).mean()
        
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        df['signal'] = 0
        df.loc[df['rsi'] < self.oversold, 'signal'] = 1
        df.loc[df['rsi'] > self.overbought, 'signal'] = -1
        
        return df
