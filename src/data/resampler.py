"""
Session-aware OHLCV resampling.

Canonical flow: fetch the finest interval once, derive higher timeframes
from it. Bars are anchored to each session's first bar — never to random
midnight boundaries — so a 15m bar at NSE starts 09:15, not 09:00/00:00.
"""

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)

INTERVAL_SECONDS = {
    "1m": 60,
    "2m": 120,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "1d": 86400,
}

_AGG = {
    "open": "first",
    "high": "max",
    "low": "min",
    "close": "last",
    "volume": "sum",
}


def resample_ohlcv(df: pd.DataFrame, target_interval: str) -> pd.DataFrame:
    """
    Resample intraday OHLCV to a higher timeframe, session by session.

    Args:
        df: DataFrame with a 'date' datetime column (exchange-local, naive)
            plus open/high/low/close/volume.
        target_interval: One of INTERVAL_SECONDS keys (e.g. '15m', '1h').

    Returns:
        Resampled DataFrame with the same schema, bars labeled by open time.
    """
    if target_interval not in INTERVAL_SECONDS:
        raise ValueError(
            f"Unknown interval '{target_interval}'. Valid: {list(INTERVAL_SECONDS)}"
        )
    if df.empty:
        return df.copy()

    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    out = out.sort_values("date")
    sec = INTERVAL_SECONDS[target_interval]

    if target_interval == "1d":
        # One bar per session date
        grouped = out.groupby(out["date"].dt.date)
        rows = grouped.agg(
            open=("open", "first"), high=("high", "max"),
            low=("low", "min"), close=("close", "last"),
            volume=("volume", "sum"),
        ).reset_index(names="date")
        rows["date"] = pd.to_datetime(rows["date"])
        return rows

    cols = [c for c in ["open", "high", "low", "close", "volume"] if c in out.columns]
    chunks = []
    # Resample within each session date, anchored to that session's first bar
    for _, day in out.groupby(out["date"].dt.date, sort=True):
        day = day.set_index("date")
        res = (
            day[cols]
            .resample(f"{sec}s", origin="start", label="left", closed="left")
            .agg({k: v for k, v in _AGG.items() if k in cols})
            .dropna(subset=["open"])  # drop empty bins (lunch gaps, halts)
        )
        chunks.append(res)

    result = pd.concat(chunks).reset_index()
    logger.info(
        f"Resampled {len(out)} bars → {len(result)} bars @ {target_interval} "
        f"({out['date'].dt.date.nunique()} sessions)"
    )
    return result
