"""
Market data fetcher using yfinance API.

Handles rate limiting with exponential backoff, multi-ticker batch fetching,
and robust column normalization for yfinance's changing API surface.
"""

import time
from typing import List, Optional

import pandas as pd
import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential

from src.utils.exceptions import DataFetchError
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Standard column mapping — yfinance column names → our internal schema
_COLUMN_MAP = {
    "Date": "date",
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Adj Close": "adj_close",
    "Volume": "volume",
}


class MarketDataFetcher:
    """Fetches OHLCV data from Yahoo Finance with retry and rate-limiting."""

    def __init__(self, rate_limit_seconds: float = 1.0):
        """
        Args:
            rate_limit_seconds: Minimum delay between consecutive API calls.
        """
        self._rate_limit = rate_limit_seconds
        self._last_call_time: float = 0.0

    def _respect_rate_limit(self) -> None:
        """Enforce minimum delay between API calls to avoid throttling."""
        elapsed = time.time() - self._last_call_time
        if elapsed < self._rate_limit:
            sleep_time = self._rate_limit - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        self._last_call_time = time.time()

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def fetch_ohlcv(
        self, ticker: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data for a single ticker.

        Args:
            ticker: Stock symbol (e.g., 'AAPL', 'RELIANCE.NS').
            start_date: Start date in 'YYYY-MM-DD' format.
            end_date: End date in 'YYYY-MM-DD' format.

        Returns:
            DataFrame with columns: [date, open, high, low, close, adj_close, volume].

        Raises:
            DataFetchError: If no data is returned or API call fails.
        """
        self._respect_rate_limit()
        logger.info(f"Fetching {ticker} from {start_date} to {end_date}")

        try:
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)

            if df.empty:
                raise DataFetchError(
                    f"No data returned for {ticker} ({start_date} to {end_date})",
                    ticker=ticker,
                )

            # Handle yfinance MultiIndex columns (newer versions)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [col[0] for col in df.columns]

            # Reset index so Date becomes a column
            df.reset_index(inplace=True)

            # Normalize column names to our internal schema
            df.rename(columns=_COLUMN_MAP, inplace=True)

            # Ensure adj_close exists (some tickers don't have it)
            if "adj_close" not in df.columns:
                df["adj_close"] = df["close"]

            logger.info(f"Fetched {len(df)} rows for {ticker}")
            return df

        except DataFetchError:
            raise
        except Exception as e:
            logger.error(f"API error fetching {ticker}: {e}")
            raise DataFetchError(
                f"Failed to fetch data for {ticker}: {e}", ticker=ticker
            )

    def fetch_multiple(
        self, tickers: List[str], start_date: str, end_date: str
    ) -> dict[str, pd.DataFrame]:
        """
        Fetch data for multiple tickers with rate limiting between calls.

        Args:
            tickers: List of stock symbols.
            start_date: Start date in 'YYYY-MM-DD' format.
            end_date: End date in 'YYYY-MM-DD' format.

        Returns:
            Dict mapping ticker → DataFrame. Failed tickers are logged and skipped.
        """
        results: dict[str, pd.DataFrame] = {}

        for i, ticker in enumerate(tickers):
            try:
                df = self.fetch_ohlcv(ticker, start_date, end_date)
                results[ticker] = df
                logger.info(f"[{i+1}/{len(tickers)}] ✓ {ticker}: {len(df)} rows")
            except DataFetchError as e:
                logger.warning(f"[{i+1}/{len(tickers)}] ✗ {ticker}: {e}")
                continue

        logger.info(
            f"Batch fetch complete: {len(results)}/{len(tickers)} tickers succeeded"
        )
        return results
