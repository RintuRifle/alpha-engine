import pandas as pd
from src.utils.logger import get_logger

logger = get_logger(__name__)

class DataValidator:
    @staticmethod
    def clean_and_validate(df: pd.DataFrame) -> pd.DataFrame:
        """Handles NaNs, checks OHLCV sanity, and forward-fills."""
        if df.empty:
            return df
            
        logger.info("Validating and cleaning data")
        
        # Ensure all expected columns exist
        expected_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
        for col in expected_cols:
            if col not in df.columns:
                logger.warning(f"Missing column: {col}")
                
        # Forward fill missing values
        df.ffill(inplace=True)
        df.bfill(inplace=True) # For any NaNs at the beginning
        
        # Sanity check
        invalid_prices = df[df['high'] < df['low']]
        if not invalid_prices.empty:
            logger.warning(f"Found {len(invalid_prices)} rows where High < Low.")
            # Correction strategy: set high to max of high/low, low to min
            df['high'] = df[['high', 'low']].max(axis=1)
            df['low'] = df[['high', 'low']].min(axis=1)
            
        return df
