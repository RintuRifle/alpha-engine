from abc import ABC, abstractmethod
import pandas as pd

class BaseStrategy(ABC):
    """Abstract base class that all strategies must inherit."""
    
    def __init__(self, **params):
        self.params = params

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Takes a DataFrame with OHLCV data.
        Returns the DataFrame with an additional 'signal' column.
        Signal = 1 (Buy/Long), -1 (Sell/Short), 0 (Neutral)
        """
        pass
