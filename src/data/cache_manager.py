"""
Smart cache manager for market data.

Checks the SQLite database first, then only fetches missing date ranges
from the API. Merges cached + fresh data and returns a complete DataFrame.
"""

from datetime import datetime, timedelta

import pandas as pd

from src.data.database import Database
from src.data.fetcher import MarketDataFetcher
from src.data.validator import DataValidator
from src.utils.logger import get_logger

logger = get_logger(__name__)


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
        self, ticker: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """
        Get OHLCV data for a ticker, using DB cache when possible.

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
