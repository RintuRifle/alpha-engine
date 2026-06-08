import yfinance as yf
import pandas as pd
from tenacity import retry, wait_exponential, stop_after_attempt
from src.utils.logger import get_logger
from src.utils.exceptions import DataFetchError

logger = get_logger(__name__)

class MarketDataFetcher:
    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
    def fetch_ohlcv(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        logger.info(f"Fetching data for {ticker} from {start_date} to {end_date}")
        try:
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)
            if df.empty:
                raise DataFetchError(f"No data returned for {ticker}")
            
            # Formatting MultiIndex columns if present (yfinance latest changes)
            if isinstance(df.columns, pd.MultiIndex):
                # Flatten the columns if needed or just take the ticker level
                df.columns = [c[0] for c in df.columns]

            df.reset_index(inplace=True)
            df.rename(columns={"Date": "date", "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume", "Adj Close": "adj_close"}, inplace=True)
            return df
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {e}")
            raise DataFetchError(f"Error fetching data for {ticker}: {e}")
