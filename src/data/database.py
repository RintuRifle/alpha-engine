import os
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker
from src.utils.logger import get_logger

logger = get_logger(__name__)
Base = declarative_base()

class DailyPrice(Base):
    __tablename__ = 'daily_prices'
    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), nullable=False)
    date = Column(Date, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    adj_close = Column(Float)
    volume = Column(Float)

    __table_args__ = (UniqueConstraint('ticker', 'date', name='_ticker_date_uc'),)

class Database:
    def __init__(self, db_path: str = "sqlite:///data/market_data.db"):
        self.engine = create_engine(db_path)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def save_dataframe(self, df: pd.DataFrame, ticker: str):
        if df.empty:
            return
        # Ensure date is just a date object for DB
        df_to_save = df.copy()
        df_to_save['date'] = pd.to_datetime(df_to_save['date']).dt.date
        df_to_save['ticker'] = ticker
        
        # Save to sql using pandas (upsert logic via temp table or simple append)
        try:
            with self.engine.begin() as conn:
                df_to_save.to_sql('daily_prices', conn, if_exists='append', index=False)
        except Exception as e:
            logger.warning(f"Failed to append cleanly, potentially duplicate records: {e}")
            # Real production would use proper UPSERT here

    def load_dataframe(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        query = f"""
        SELECT * FROM daily_prices 
        WHERE ticker = '{ticker}' AND date >= '{start_date}' AND date <= '{end_date}'
        ORDER BY date ASC
        """
        return pd.read_sql(query, self.engine, parse_dates=['date'])
