import yfinance as yf
import pandas as pd
from src.utils.logger import get_logger

logger = get_logger(__name__)

class Benchmark:
    @staticmethod
    def get_benchmark_returns(ticker: str = "SPY", start: str = "2020-01-01", end: str = None) -> pd.Series:
        try:
            df = yf.download(ticker, start=start, end=end, progress=False)
            if df.empty: return pd.Series()
            
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]

            df['Returns'] = df['Close'].pct_change()
            return df['Returns'].dropna()
        except Exception as e:
            logger.error(f"Failed to fetch benchmark: {e}")
            return pd.Series()
