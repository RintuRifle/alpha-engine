import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy

class BollingerBands(BaseStrategy):
    def __init__(self, window: int = 20, num_std: float = 2.0):
        super().__init__(window=window, num_std=num_std)
        self.window = window
        self.num_std = num_std

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['sma'] = df['close'].rolling(window=self.window).mean()
        df['std'] = df['close'].rolling(window=self.window).std()
        df['upper_band'] = df['sma'] + (df['std'] * self.num_std)
        df['lower_band'] = df['sma'] - (df['std'] * self.num_std)
        
        df['signal'] = 0
        # Buy when price crosses above lower band (mean reversion)
        df.loc[df['close'] < df['lower_band'], 'signal'] = 1
        # Sell when price crosses below upper band
        df.loc[df['close'] > df['upper_band'], 'signal'] = -1
        
        return df
