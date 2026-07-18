"""
Smart cache manager for market data.

Daily data: SQLite-backed range cache (fetch only the missing ranges).
Intraday data: Parquet-backed best-effort cache — Yahoo only serves short
intraday history windows, so we fetch fresh, persist to Parquet, and fall
back to the cache when the API is unavailable.
"""

import os
from datetime import datetime, timedelta

import pandas as pd

from src.data.database import Database
from src.data.fetcher import MarketDataFetcher
from src.data.validator import DataValidator
from src.utils.logger import get_logger

logger = get_logger(__name__)

INTRADAY_CACHE_DIR = "data/intraday"


class CacheManager:
    """
    Intelligent data cache that minimizes API calls by checking the database
    first and only fetching date ranges that are missing.
    """

    def __init__(self, db_path: str = "sqlite:///data/market_data.db"):
        """
        Args:
            db_path: SQLAlchemy database URL.
        """
        self.db = Database(db_path)
        self.fetcher = MarketDataFetcher()
        self.validator = DataValidator()

    def get_data(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        source: str = "auto",
    ) -> pd.DataFrame:
        """
        Get OHLCV data for a ticker at any interval, using cache when possible.

        source:
            'auto'   → yahoo, but switch to Alpaca for intraday ranges beyond
                       Yahoo's history limits (when keys are configured).
            'yahoo'  → force Yahoo Finance.
            'alpaca' → force Alpaca Market Data (US equities, needs keys).
        """
        source = (source or "auto").lower()
        if source == "auto":
            source = self._resolve_source(ticker, start_date, interval)
        if interval != "1d" or source == "alpaca":
            return self._get_intraday(ticker, start_date, end_date, interval, source)
        return self._get_daily(ticker, start_date, end_date)

    @staticmethod
    def _resolve_source(ticker: str, start_date: str, interval: str) -> str:
        """Pick yahoo vs alpaca automatically."""
        from src.data.fetcher import INTERVAL_MAX_DAYS
        from src.data.alpaca_data import alpaca_keys_present

        if interval == "1d":
            return "yahoo"
        limit = INTERVAL_MAX_DAYS.get(interval)
        days_back = (datetime.now() - datetime.strptime(start_date, "%Y-%m-%d")).days
        beyond_yahoo = limit is not None and days_back > limit
        us_ticker = "." not in ticker  # Alpaca serves US equities only
        if beyond_yahoo and us_ticker and alpaca_keys_present():
            logger.info(
                f"Auto data source: alpaca ({days_back}d back exceeds yahoo's {limit}d {interval} limit)"
            )
            return "alpaca"
        return "yahoo"

    def _get_intraday(
        self, ticker: str, start_date: str, end_date: str, interval: str,
        source: str = "yahoo",
    ) -> pd.DataFrame:
        """Fetch-fresh-first intraday flow with Parquet fallback cache."""
        os.makedirs(INTRADAY_CACHE_DIR, exist_ok=True)
        suffix = "_alpaca" if source == "alpaca" else ""
        cache_path = os.path.join(
            INTRADAY_CACHE_DIR, f"{ticker.replace('/', '_')}_{interval}{suffix}.parquet"
        )

        df = None
        try:
            if source == "alpaca":
                from src.data.alpaca_data import AlpacaDataFetcher
                df = AlpacaDataFetcher().fetch_ohlcv(ticker, start_date, end_date, interval)
            else:
                df = self.fetcher.fetch_ohlcv(ticker, start_date, end_date, interval)
        except Exception as e:
            logger.warning(f"Intraday fetch failed for {ticker}@{interval} ({source}): {e}")

        if df is not None and not df.empty:
            # Merge with existing cache (dedupe on timestamp, keep newest)
            try:
                if os.path.exists(cache_path):
                    old = pd.read_parquet(cache_path)
                    df = (
                        pd.concat([old, df])
                        .drop_duplicates(subset=["date"], keep="last")
                        .sort_values("date")
                    )
                df.to_parquet(cache_path, index=False)
            except Exception as e:
                logger.warning(f"Intraday cache write failed: {e}")
        elif os.path.exists(cache_path):
            logger.info(f"Falling back to intraday Parquet cache: {cache_path}")
            df = pd.read_parquet(cache_path)

        if df is None or df.empty:
            from src.utils.exceptions import DataFetchError
            raise DataFetchError(
                f"No intraday data for {ticker} @ {interval} "
                f"({start_date} → {end_date}). Yahoo limits intraday history "
                f"(1m≈7d, 5m/15m≈60d, 1h≈730d).",
                ticker=ticker,
            )

        # Slice to requested window (date column is exchange-local naive)
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        mask = (df["date"] >= pd.Timestamp(start_date)) & (
            df["date"] < pd.Timestamp(end_date) + pd.Timedelta(days=1)
        )
        df = df.loc[mask].drop_duplicates(subset=["date"]).sort_values("date")
        return self.validator.clean_and_validate(df, min_rows=30)

    def _get_daily(
        self, ticker: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """
        Get daily OHLCV data for a ticker, using DB cache when possible.

        Logic:
        1. Check if DB has data for the requested date range
        2. If DB covers the full range → return cached data
        3. If DB has partial data → fetch only the missing ranges
        4. If DB has no data → fetch everything from API

        Args:
            ticker: Stock symbol.
            start_date: Start date 'YYYY-MM-DD'.
            end_date: End date 'YYYY-MM-DD'.

        Returns:
            Validated OHLCV DataFrame.
        """
        logger.info(f"Requesting {ticker} from {start_date} to {end_date}")

        # Check what's in the database
        db_min, db_max = self.db.get_available_date_range(ticker)

        if db_min and db_max:
            req_start = datetime.strptime(start_date, "%Y-%m-%d").date()
            req_end = datetime.strptime(end_date, "%Y-%m-%d").date()
            cached_start = datetime.strptime(db_min, "%Y-%m-%d").date()
            cached_end = datetime.strptime(db_max, "%Y-%m-%d").date()

            # Case 1: DB fully covers the requested range
            if cached_start <= req_start and cached_end >= req_end - timedelta(days=3):
                logger.info(f"Full cache hit for {ticker} — loading from DB")
                df = self.db.load_dataframe(ticker, start_date, end_date)
                if len(df) > 10:  # Reasonable amount of data
                    return self.validator.clean_and_validate(df)

            # Case 2: Partial coverage — fetch missing ranges
            ranges_to_fetch = []

            if req_start < cached_start:
                ranges_to_fetch.append(
                    (start_date, (cached_start - timedelta(days=1)).strftime("%Y-%m-%d"))
                )
            if req_end > cached_end:
                ranges_to_fetch.append(
                    ((cached_end + timedelta(days=1)).strftime("%Y-%m-%d"), end_date)
                )

            if ranges_to_fetch:
                logger.info(
                    f"Partial cache hit for {ticker} — fetching {len(ranges_to_fetch)} missing range(s)"
                )
                for fetch_start, fetch_end in ranges_to_fetch:
                    try:
                        df_api = self.fetcher.fetch_ohlcv(ticker, fetch_start, fetch_end)
                        self.db.save_dataframe(df_api, ticker)
                    except Exception as e:
                        logger.warning(f"Failed to fetch missing range {fetch_start}→{fetch_end}: {e}")

            # Load the full range from DB (now hopefully complete)
            df = self.db.load_dataframe(ticker, start_date, end_date)
            if not df.empty:
                return self.validator.clean_and_validate(df)

        # Case 3: No cached data — full API fetch
        logger.info(f"Cache miss for {ticker} — fetching from API")
        df_api = self.fetcher.fetch_ohlcv(ticker, start_date, end_date)
        df_clean = self.validator.clean_and_validate(df_api)
        self.db.save_dataframe(df_clean, ticker)
        return df_clean
