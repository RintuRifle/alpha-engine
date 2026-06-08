import pandas as pd
from .base_strategy import BaseStrategy

class MACDStrategy(BaseStrategy):
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        super().__init__(fast_period=fast_period, slow_period=slow_period, signal_period=signal_period)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        exp1 = df['close'].ewm(span=self.fast_period, adjust=False).mean()
        exp2 = df['close'].ewm(span=self.slow_period, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['signal_line'] = df['macd'].ewm(span=self.signal_period, adjust=False).mean()
        
        df['signal'] = 0
        df.loc[df['macd'] > df['signal_line'], 'signal'] = 1
        df.loc[df['macd'] < df['signal_line'], 'signal'] = -1
        
        return df
