import pandas as pd
from .fetcher import MarketDataFetcher
from .database import Database
from .validator import DataValidator
from src.utils.logger import get_logger

logger = get_logger(__name__)

class CacheManager:
    def __init__(self):
        self.db = Database()
        self.fetcher = MarketDataFetcher()
        self.validator = DataValidator()
        
    def get_data(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        logger.info(f"Requesting data for {ticker} from {start_date} to {end_date}")
        
        # 1. Try DB first
        df_db = self.db.load_dataframe(ticker, start_date, end_date)
        
        # Simplistic approach: if DB returned data is missing dates, just fetch from API
        # In a fully prod system, we would find exactly the missing ranges
        if len(df_db) < 10:  # arbitrary small number meaning we lack history
            logger.info("Not enough data in DB, fetching from API...")
            df_api = self.fetcher.fetch_ohlcv(ticker, start_date, end_date)
            df_clean = self.validator.clean_and_validate(df_api)
            self.db.save_dataframe(df_clean, ticker)
            return df_clean
            
        logger.info("Loaded data from DB cache.")
        return df_db
