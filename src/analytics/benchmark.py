"""
Benchmark data fetcher for performance comparison.

Fetches benchmark index data (SPY for US, NIFTY50 for India) to compare
against strategy returns. Without a benchmark, you can't tell if your
strategy actually adds value or just rides the market.
"""

import pandas as pd
import yfinance as yf

from src.utils.logger import get_logger

logger = get_logger(__name__)


class Benchmark:
    """Fetches and processes benchmark index data for comparison."""

    @staticmethod
    def get_benchmark_returns(
        ticker: str = "SPY",
        start: str = "2018-01-01",
        end: str | None = None,
    ) -> pd.Series:
        """
        Fetch benchmark daily returns.

        Args:
            ticker: Benchmark ticker (SPY, ^GSPC, ^NSEI, etc.).
            start: Start date.
            end: End date (None = today).

        Returns:
            Series of daily returns with DatetimeIndex.
        """
        try:
            logger.info(f"Fetching benchmark data: {ticker}")
            df = yf.download(ticker, start=start, end=end, progress=False)

            if df.empty:
                logger.warning(f"No benchmark data for {ticker}")
                return pd.Series(dtype=float)

            # Handle MultiIndex columns
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]

            returns = df["Close"].pct_change().dropna()
            returns.name = ticker
            logger.info(f"Benchmark {ticker}: {len(returns)} daily returns")
            return returns

        except Exception as e:
            logger.error(f"Failed to fetch benchmark {ticker}: {e}")
            return pd.Series(dtype=float)

    @staticmethod
    def get_benchmark_equity(
        ticker: str = "SPY",
        start: str = "2018-01-01",
        end: str | None = None,
        initial_value: float = 10000.0,
    ) -> pd.Series:
        """
        Get benchmark equity curve (for plotting alongside strategy equity).

        Args:
            ticker: Benchmark ticker.
            start: Start date.
            end: End date.
            initial_value: Starting value to normalize to.

        Returns:
            Series of equity values.
        """
        returns = Benchmark.get_benchmark_returns(ticker, start, end)
        if returns.empty:
            return pd.Series(dtype=float)

        equity = (1 + returns).cumprod() * initial_value
        equity.name = f"{ticker} (Benchmark)"
        return equity
