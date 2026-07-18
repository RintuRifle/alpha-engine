"""
Alpaca Market Data fetcher — years of intraday history for US equities.

Yahoo caps intraday history (1m≈7d). Alpaca's data API serves minute bars
back to ~2016 on the free IEX feed, which makes real multi-year minute
backtests possible. Uses the same env keys as the live endpoints:
ALPACA_API_KEY / ALPACA_SECRET_KEY.
"""

import os
from typing import Optional

import pandas as pd

from src.utils.exceptions import DataFetchError
from src.utils.logger import get_logger

logger = get_logger(__name__)

# our interval → alpaca TimeFrame constructor args (amount, unit)
_TF_MAP = {
    "1m": (1, "Minute"),
    "2m": (2, "Minute"),
    "5m": (5, "Minute"),
    "15m": (15, "Minute"),
    "30m": (30, "Minute"),
    "1h": (1, "Hour"),
    "1d": (1, "Day"),
}


def alpaca_keys_present() -> bool:
    return bool(os.getenv("ALPACA_API_KEY")) and bool(os.getenv("ALPACA_SECRET_KEY"))


class AlpacaDataFetcher:
    """Historical OHLCV bars from Alpaca (IEX feed on free plans)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        feed: str = "iex",
    ):
        self.api_key = api_key or os.getenv("ALPACA_API_KEY")
        self.secret_key = secret_key or os.getenv("ALPACA_SECRET_KEY")
        self.feed = feed
        if not self.api_key or not self.secret_key:
            raise DataFetchError(
                "Alpaca keys not configured — set ALPACA_API_KEY / ALPACA_SECRET_KEY."
            )

    def fetch_ohlcv(
        self, ticker: str, start_date: str, end_date: str, interval: str = "1m"
    ) -> pd.DataFrame:
        """
        Fetch bars and return our standard schema:
        [date, open, high, low, close, adj_close, volume] with 'date' as
        exchange-local (America/New_York) naive datetimes.
        """
        if interval not in _TF_MAP:
            raise DataFetchError(f"Unsupported interval for Alpaca: {interval}")

        try:
            import alpaca_trade_api as tradeapi
            from alpaca_trade_api.rest import TimeFrame, TimeFrameUnit
        except ImportError as e:
            raise DataFetchError(
                f"alpaca-trade-api not installed: {e}. Run: pip install alpaca-trade-api"
            )

        amount, unit = _TF_MAP[interval]
        tf = TimeFrame(amount, getattr(TimeFrameUnit, unit))

        api = tradeapi.REST(
            key_id=self.api_key,
            secret_key=self.secret_key,
            base_url="https://paper-api.alpaca.markets",
        )

        logger.info(f"Alpaca fetch: {ticker} @ {interval} ({start_date} → {end_date}, feed={self.feed})")
        try:
            bars = api.get_bars(
                ticker.upper(),
                tf,
                start=start_date,
                end=end_date,
                adjustment="all",   # split+dividend adjusted
                feed=self.feed,
            ).df
        except Exception as e:
            raise DataFetchError(f"Alpaca API error for {ticker}: {e}", ticker=ticker)

        if bars is None or bars.empty:
            raise DataFetchError(
                f"Alpaca returned no data for {ticker} ({start_date} → {end_date}, {interval})",
                ticker=ticker,
            )

        df = bars.reset_index()
        # alpaca-trade-api names: timestamp, open, high, low, close, volume, ...
        ts_col = "timestamp" if "timestamp" in df.columns else df.columns[0]
        df = df.rename(columns={ts_col: "date"})

        # UTC tz-aware → exchange-local naive (consistent with the yahoo path)
        df["date"] = pd.to_datetime(df["date"])
        if getattr(df["date"].dt, "tz", None) is not None:
            df["date"] = (
                df["date"].dt.tz_convert("America/New_York").dt.tz_localize(None)
            )

        # Keep regular session bars only for intraday (Alpaca includes pre/post)
        if interval != "1d":
            t = df["date"].dt.time
            df = df[(t >= pd.Timestamp("09:30").time()) & (t < pd.Timestamp("16:00").time())]

        keep = [c for c in ["date", "open", "high", "low", "close", "volume"] if c in df.columns]
        df = df[keep].copy()
        df["adj_close"] = df["close"]

        logger.info(f"Alpaca: {len(df)} bars for {ticker} @ {interval}")
        return df.reset_index(drop=True)
