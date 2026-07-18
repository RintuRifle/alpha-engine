"""
Market data fetcher — Yahoo Finance primary, Alpaca fallback.

Handles rate limiting with exponential backoff, multi-ticker batch fetching,
and robust column normalization. For intraday intervals where Yahoo's lookback
limits are exceeded (e.g. 30m > 60 days), the fetcher automatically falls back
to the Alpaca Data API v2 (free IEX feed) which provides 5+ years of history.
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
    "Datetime": "date",  # yfinance uses 'Datetime' for intraday intervals
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Adj Close": "adj_close",
    "Volume": "volume",
}

# Yahoo Finance lookback limits per interval (calendar days)
INTERVAL_MAX_DAYS = {
    "1m": 7,
    "2m": 60,
    "5m": 60,
    "15m": 60,
    "30m": 60,
    "1h": 730,
    "1d": None,  # unlimited
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
    def _fetch_from_yahoo(
        self, ticker: str, start_date: str, end_date: str, interval: str = "1d"
    ) -> pd.DataFrame:
        """Fetch OHLCV from Yahoo Finance with TLS bypass and retries."""
        try:
            from curl_cffi import requests
            # Use curl_cffi to impersonate Chrome and bypass Yahoo Finance TLS fingerprinting blocks
            session = requests.Session(impersonate="chrome")

            kwargs = dict(
                start=start_date, end=end_date, interval=interval, progress=False
            )
            try:
                df = yf.download(ticker, session=session, **kwargs)
            except Exception as e:
                logger.warning(f"curl_cffi session failed for {ticker} ({e}), falling back to standard requests...")
                df = yf.download(ticker, **kwargs)

            if df.empty:
                raise DataFetchError(
                    f"No data returned for {ticker} ({start_date} to {end_date}, {interval}). "
                    f"Note: Yahoo limits intraday history "
                    f"(1m≈7d, 5m/15m≈60d, 1h≈730d). "
                    f"[ticker={ticker}, source=yfinance]",
                    ticker=ticker,
                )

            # Handle yfinance MultiIndex columns (newer versions)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [col[0] for col in df.columns]

            # Reset index so Date/Datetime becomes a column
            df.reset_index(inplace=True)

            # Normalize column names to our internal schema
            df.rename(columns=_COLUMN_MAP, inplace=True)

            # Intraday timestamps arrive tz-aware (exchange tz) — convert to
            # exchange-local naive so the whole pipeline stays consistent.
            if pd.api.types.is_datetime64_any_dtype(df["date"]):
                try:
                    if getattr(df["date"].dt, "tz", None) is not None:
                        df["date"] = df["date"].dt.tz_localize(None)
                except (TypeError, AttributeError):
                    pass

            # Ensure adj_close exists (some tickers don't have it)
            if "adj_close" not in df.columns:
                df["adj_close"] = df["close"]

            logger.info(f"Fetched {len(df)} rows for {ticker} @ {interval} (Yahoo)")
            return df

        except DataFetchError:
            raise
        except Exception as e:
            logger.error(f"Yahoo API error fetching {ticker}: {e}")
            raise DataFetchError(
                f"Failed to fetch data for {ticker}: {e}", ticker=ticker
            )

    def _fetch_from_alpaca(
        self, ticker: str, start_date: str, end_date: str, interval: str
    ) -> pd.DataFrame:
        """
        Fetch OHLCV from Alpaca Data API v2 (free IEX feed).

        Supports much longer intraday history than Yahoo Finance:
        5m/15m/30m/1h bars are available for 5+ years.
        Requires ALPACA_API_KEY and ALPACA_SECRET_KEY env vars.
        """
        import os
        from curl_cffi import requests

        api_key = os.getenv("ALPACA_API_KEY")
        secret_key = os.getenv("ALPACA_SECRET_KEY")
        if not api_key or not secret_key:
            raise DataFetchError(
                "Alpaca API keys not configured. Set ALPACA_API_KEY and "
                "ALPACA_SECRET_KEY to enable intraday fallback.",
                ticker=ticker,
            )

        # Map our interval format to Alpaca's timeframe format
        timeframe_map = {
            "1m": "1Min", "2m": "2Min", "5m": "5Min",
            "15m": "15Min", "30m": "30Min", "1h": "1Hour", "1d": "1Day",
        }
        timeframe = timeframe_map.get(interval)
        if not timeframe:
            raise DataFetchError(
                f"Unsupported interval for Alpaca: {interval}", ticker=ticker
            )

        headers = {
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": secret_key,
        }

        all_bars: list = []
        page_token: Optional[str] = None
        base_url = "https://data.alpaca.markets/v2/stocks"

        # Try multiple TLS profiles in case one is blocked by Cloudflare
        _profiles = ["chrome131", "chrome", "safari18_0", "edge101"]

        while True:
            params: dict = {
                "timeframe": timeframe,
                "start": f"{start_date}T00:00:00Z",
                "end": f"{end_date}T23:59:59Z",
                "limit": 10000,
                "adjustment": "split",
                "feed": "iex",
            }
            if page_token:
                params["page_token"] = page_token

            resp = None
            last_err = None
            for profile in _profiles:
                try:
                    session = requests.Session(impersonate=profile)
                    resp = session.get(
                        f"{base_url}/{ticker}/bars",
                        headers=headers,
                        params=params,
                    )
                    break  # success
                except Exception as e:
                    last_err = e
                    logger.debug(f"Alpaca TLS profile '{profile}' failed: {e}")
                    time.sleep(1)
                    continue

            if resp is None:
                raise DataFetchError(
                    f"All TLS profiles failed for Alpaca: {last_err}",
                    ticker=ticker,
                )

            if resp.status_code != 200:
                raise DataFetchError(
                    f"Alpaca API error {resp.status_code}: {resp.text}",
                    ticker=ticker,
                )

            data = resp.json()
            bars = data.get("bars") or []
            all_bars.extend(bars)

            page_token = data.get("next_page_token")
            if not page_token:
                break

        if not all_bars:
            raise DataFetchError(
                f"No Alpaca data for {ticker} ({start_date} to {end_date}, "
                f"{interval}).",
                ticker=ticker,
            )

        df = pd.DataFrame(all_bars)
        df.rename(
            columns={
                "t": "date", "o": "open", "h": "high", "l": "low",
                "c": "close", "v": "volume", "n": "trades", "vw": "vwap",
            },
            inplace=True,
        )
        df["date"] = pd.to_datetime(df["date"])
        if getattr(df["date"].dt, "tz", None) is not None:
            df["date"] = df["date"].dt.tz_localize(None)
        df["adj_close"] = df["close"]
        df = df[["date", "open", "high", "low", "close", "adj_close", "volume"]]
        df.sort_values("date", inplace=True)
        df.reset_index(drop=True, inplace=True)

        logger.info(f"Fetched {len(df)} rows for {ticker} @ {interval} (Alpaca)")
        return df

    def fetch_ohlcv(
        self, ticker: str, start_date: str, end_date: str, interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data for a single ticker at any supported interval.

        Tries Yahoo Finance first; for intraday intervals, automatically
        falls back to Alpaca Data API when Yahoo's lookback limits are exceeded.

        Args:
            ticker: Stock symbol (e.g., 'AAPL', 'RELIANCE.NS').
            start_date: Start date in 'YYYY-MM-DD' format.
            end_date: End date in 'YYYY-MM-DD' format.
            interval: '1m' | '2m' | '5m' | '15m' | '30m' | '1h' | '1d'.

        Returns:
            DataFrame with columns: [date, open, high, low, close, adj_close, volume].

        Raises:
            DataFetchError: If no data is returned from any source.
        """
        self._respect_rate_limit()
        logger.info(f"Fetching {ticker} @ {interval} from {start_date} to {end_date}")

        try:
            return self._fetch_from_yahoo(ticker, start_date, end_date, interval)
        except DataFetchError:
            if interval == "1d":
                raise  # Daily data has no better fallback
            logger.info(
                f"Yahoo failed for {ticker} @ {interval}, trying Alpaca fallback..."
            )
            try:
                return self._fetch_from_alpaca(
                    ticker, start_date, end_date, interval
                )
            except Exception as alpaca_err:
                logger.warning(f"Alpaca fallback also failed: {alpaca_err}")
                raise

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
