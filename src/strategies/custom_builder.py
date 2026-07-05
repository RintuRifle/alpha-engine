"""
Custom Strategy Builder allowing dynamic rule evaluation.
"""

from typing import List, Dict, Any
import pandas as pd
import numpy as np

from src.strategies.base_strategy import BaseStrategy
from src.utils.logger import get_logger

logger = get_logger(__name__)

class CustomStrategy(BaseStrategy):
    """
    Evaluates dynamic string queries to generate signals.
    """

    def __init__(self, indicators: List[Dict[str, Any]], buy_query: str, sell_query: str, **params: Any):
        super().__init__(**params)
        self.indicators = indicators
        self.buy_query = buy_query
        self.sell_query = sell_query
        self.params["indicators"] = indicators
        self.params["buy_query"] = buy_query
        self.params["sell_query"] = sell_query

    @property
    def name(self) -> str:
        return "Custom Strategy"

    def _compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        for ind in self.indicators:
            itype = ind.get("type", "").upper()
            col = ind.get("col_name", f"{itype}_Custom")
            
            if itype == "SMA":
                window = ind.get("window", 20)
                df[col] = df["close"].rolling(window=window).mean()
            elif itype == "EMA":
                window = ind.get("window", 20)
                df[col] = df["close"].ewm(span=window, adjust=False).mean()
            elif itype == "RSI":
                window = ind.get("window", 14)
                delta = df["close"].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
                rs = gain / loss
                df[col] = 100 - (100 / (1 + rs))
            elif itype == "MACD":
                fast = ind.get("fast", 12)
                slow = ind.get("slow", 26)
                signal = ind.get("signal", 9)
                ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
                ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
                df[f"{col}_line"] = ema_fast - ema_slow
                df[f"{col}_signal"] = df[f"{col}_line"].ewm(span=signal, adjust=False).mean()
        
        return df

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self._compute_indicators(df)
        df["signal"] = 0
        
        if len(df) == 0:
            return df
            
        try:
            if self.buy_query:
                buy_mask = df.eval(self.buy_query)
                df.loc[buy_mask, "signal"] = 1
                
            if self.sell_query:
                sell_mask = df.eval(self.sell_query)
                df.loc[sell_mask, "signal"] = -1
                
        except Exception as e:
            logger.error(f"Error evaluating custom strategy query: {e}")
            
        return df
