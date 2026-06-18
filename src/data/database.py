"""
SQLite database layer using SQLAlchemy ORM.

Handles CRUD operations for historical price data with:
- Composite unique constraint on (ticker, date) to prevent duplicates
- Proper UPSERT logic (INSERT OR IGNORE + UPDATE for SQLite)
- Parameterized queries — NO SQL injection vulnerabilities
"""

import os
from datetime import date as date_type
from typing import Optional, Tuple

import pandas as pd
from sqlalchemy import (
    Column,
    Date,
    Float,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
    text,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from src.utils.logger import get_logger

logger = get_logger(__name__)
Base = declarative_base()


class DailyPrice(Base):
    """ORM model for the daily_prices table."""

    __tablename__ = "daily_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    adj_close = Column(Float)
    volume = Column(Float)

    __table_args__ = (
        UniqueConstraint("ticker", "date", name="_ticker_date_uc"),
    )

    def __repr__(self) -> str:
        return f"<DailyPrice {self.ticker} {self.date} close={self.close}>"


class Database:
    """
    SQLite database interface for storing and retrieving historical price data.

    Uses SQLAlchemy for ORM operations and parameterized queries for safety.
    """

    def __init__(self, db_path: str = "sqlite:///data/market_data.db"):
        """
        Args:
            db_path: SQLAlchemy database URL. Defaults to local SQLite file.
        """
        # Ensure the data directory exists for SQLite file path
        if db_path.startswith("sqlite:///"):
            db_file = db_path.replace("sqlite:///", "")
            os.makedirs(os.path.dirname(db_file) or ".", exist_ok=True)

        self.engine = create_engine(db_path, echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        logger.info(f"Database initialized: {db_path}")

    def save_dataframe(self, df: pd.DataFrame, ticker: str) -> int:
        """
        Save a DataFrame of OHLCV data to the database.

        Uses INSERT OR IGNORE to handle duplicate (ticker, date) pairs gracefully.

        Args:
            df: DataFrame with columns [date, open, high, low, close, volume].
            ticker: Stock ticker symbol.

        Returns:
            Number of rows successfully inserted.
        """
        if df.empty:
            return 0

        df_to_save = df.copy()
        df_to_save["date"] = pd.to_datetime(df_to_save["date"]).dt.date
        df_to_save["ticker"] = ticker

        # Select only the columns we need
        columns = ["ticker", "date", "open", "high", "low", "close", "adj_close", "volume"]
        available_cols = [c for c in columns if c in df_to_save.columns]
        df_to_save = df_to_save[available_cols]

        rows_before = self._count_rows(ticker)

        try:
            with self.engine.begin() as conn:
                # Use INSERT OR IGNORE for SQLite to skip duplicates
                for _, row in df_to_save.iterrows():
                    conn.execute(
                        text("""
                            INSERT OR IGNORE INTO daily_prices
                            (ticker, date, open, high, low, close, adj_close, volume)
                            VALUES (:ticker, :date, :open, :high, :low, :close, :adj_close, :volume)
                        """),
                        {
                            "ticker": row.get("ticker"),
                            "date": row.get("date"),
                            "open": float(row.get("open", 0)),
                            "high": float(row.get("high", 0)),
                            "low": float(row.get("low", 0)),
                            "close": float(row.get("close", 0)),
                            "adj_close": float(row.get("adj_close", row.get("close", 0))),
                            "volume": float(row.get("volume", 0)),
                        },
                    )

            rows_after = self._count_rows(ticker)
            inserted = rows_after - rows_before
            logger.info(f"Saved {inserted} new rows for {ticker} (total: {rows_after})")
            return inserted

        except Exception as e:
            logger.error(f"Database save failed for {ticker}: {e}")
            raise

    def load_dataframe(
        self, ticker: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """
        Load historical price data from the database.

        Uses parameterized queries to prevent SQL injection.

        Args:
            ticker: Stock ticker symbol.
            start_date: Start date in 'YYYY-MM-DD' format.
            end_date: End date in 'YYYY-MM-DD' format.

        Returns:
            DataFrame with OHLCV data sorted by date.
        """
        query = text("""
            SELECT ticker, date, open, high, low, close, adj_close, volume
            FROM daily_prices
            WHERE ticker = :ticker AND date >= :start_date AND date <= :end_date
            ORDER BY date ASC
        """)

        df = pd.read_sql(
            query,
            self.engine,
            params={"ticker": ticker, "start_date": start_date, "end_date": end_date},
            parse_dates=["date"],
        )
        logger.info(f"Loaded {len(df)} rows for {ticker} from DB")
        return df

    def get_available_date_range(self, ticker: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Get the earliest and latest dates available in DB for a ticker.

        Returns:
            Tuple of (min_date, max_date) as strings, or (None, None) if no data.
        """
        query = text("""
            SELECT MIN(date) as min_date, MAX(date) as max_date
            FROM daily_prices
            WHERE ticker = :ticker
        """)

        with self.engine.connect() as conn:
            result = conn.execute(query, {"ticker": ticker}).fetchone()

        if result and result[0]:
            return str(result[0]), str(result[1])
        return None, None

    def get_stored_tickers(self) -> list[str]:
        """Return a list of all tickers stored in the database."""
        query = text("SELECT DISTINCT ticker FROM daily_prices ORDER BY ticker")
        with self.engine.connect() as conn:
            result = conn.execute(query).fetchall()
        return [row[0] for row in result]

    def _count_rows(self, ticker: str) -> int:
        """Count total rows for a specific ticker."""
        query = text("SELECT COUNT(*) FROM daily_prices WHERE ticker = :ticker")
        with self.engine.connect() as conn:
            result = conn.execute(query, {"ticker": ticker}).fetchone()
        return result[0] if result else 0
