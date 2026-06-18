"""
Data ingestion script — fetches market data and stores in SQLite.

Usage:
    python run.py
    # OR
    make ingest
"""

from src.data.cache_manager import CacheManager
from src.utils.helpers import load_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    logger.info("🚀 Starting Data Ingestion...")

    config = load_config()
    tickers = config.get("data", {}).get("default_tickers", ["AAPL", "MSFT"])
    start = config.get("data", {}).get("default_start_date", "2018-01-01")
    end = config.get("data", {}).get("default_end_date", "2023-12-31")

    cache = CacheManager()

    for i, ticker in enumerate(tickers):
        logger.info(f"[{i+1}/{len(tickers)}] Fetching {ticker}...")
        try:
            df = cache.get_data(ticker, start, end)
            logger.info(f"  ✓ {ticker}: {len(df)} rows loaded")
        except Exception as e:
            logger.error(f"  ✗ {ticker}: {e}")

    logger.info("✅ Data Ingestion Complete!")


if __name__ == "__main__":
    main()