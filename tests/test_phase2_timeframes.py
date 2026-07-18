"""
Phase 2 tests — session-aware resampling and intraday engine behavior.
"""

import numpy as np
import pandas as pd
import pytest

from src.backtester.engine import BacktestEngine
from src.data.resampler import resample_ohlcv
from src.data.sessions import session_for, NSE, US_EQUITIES


def make_intraday_df(n_sessions=2, start="2026-07-13"):
    """Synthetic 1-minute NSE-style session: 09:15–15:29 (375 bars/session)."""
    frames = []
    day = pd.Timestamp(start)
    for s in range(n_sessions):
        idx = pd.date_range(
            day + pd.Timedelta(hours=9, minutes=15), periods=375, freq="1min"
        )
        base = 100 + s
        frames.append(pd.DataFrame({
            "date": idx,
            "open": base, "high": base + 0.5, "low": base - 0.5,
            "close": base + 0.1, "volume": 1000,
        }))
        day += pd.Timedelta(days=1)
    return pd.concat(frames, ignore_index=True).astype({"open": float})


class TestSessions:
    def test_suffix_detection(self):
        assert session_for("RELIANCE.NS") is NSE
        assert session_for("AAPL") is US_EQUITIES
        assert session_for("tcs.ns") is NSE

    def test_bars_per_session(self):
        assert NSE.bars_per_session(60) == 375           # 6.25h of 1m bars
        assert US_EQUITIES.bars_per_session(300) == 78   # 6.5h of 5m bars


class TestResampler:
    def test_15m_bars_anchor_to_session_open_not_midnight(self):
        df = make_intraday_df(2)
        out = resample_ohlcv(df, "15m")
        first = out["date"].iloc[0]
        assert (first.hour, first.minute) == (9, 15), \
            "first 15m bar must start at session open (09:15), not 09:00/00:00"
        # 375 minutes / 15 = 25 bars per session
        per_session = out.groupby(out["date"].dt.date).size()
        assert (per_session == 25).all()

    def test_volume_conserved(self):
        df = make_intraday_df(1)
        out = resample_ohlcv(df, "1h")
        assert out["volume"].sum() == df["volume"].sum()

    def test_no_bars_span_sessions(self):
        df = make_intraday_df(2)
        out = resample_ohlcv(df, "1h")
        # last bar of session 1 must not aggregate session 2 data
        s1 = out[out["date"].dt.date == out["date"].dt.date.iloc[0]]
        assert s1["high"].max() == pytest.approx(100.5)

    def test_to_daily(self):
        df = make_intraday_df(2)
        out = resample_ohlcv(df, "1d")
        assert len(out) == 2
        assert out["volume"].iloc[0] == 375 * 1000

    def test_unknown_interval_raises(self):
        with pytest.raises(ValueError):
            resample_ohlcv(make_intraday_df(1), "42m")


class TestIntradaySquareOff:
    def _df_with_entry(self):
        """Two sessions; BUY signal early in session 1, never an exit signal."""
        df = make_intraday_df(2)
        df["signal"] = 0
        df.loc[30, "signal"] = 1  # entry executes at bar 31 open
        return df

    def test_square_off_forces_flat_at_session_end(self):
        df = self._df_with_entry()
        engine = BacktestEngine(
            data=df, ticker="TEST.NS", initial_capital=100000,
            commission=0.0, slippage=0.0, intraday_square_off=True,
        )
        p = engine.run()
        assert p.positions.get("TEST.NS", 0) == 0, "must be flat at end"
        sells = [t for t in p.trade_history if t["action"] == "SELL"]
        assert len(sells) == 1
        sell_ts = pd.Timestamp(sells[0]["date"])
        first_session = df["date"].dt.date.iloc[0]
        assert sell_ts.date() == first_session, "square-off must happen in session 1"
        assert (sell_ts.hour, sell_ts.minute) == (15, 29), \
            "square-off on the session's LAST bar"

    def test_without_square_off_position_carries_overnight(self):
        df = self._df_with_entry()
        engine = BacktestEngine(
            data=df, ticker="TEST.NS", initial_capital=100000,
            commission=0.0, slippage=0.0, intraday_square_off=False,
        )
        p = engine.run()
        assert p.positions.get("TEST.NS", 0) > 0, "carry overnight when square-off off"

    def test_intraday_equity_curve_keeps_timestamps(self):
        df = self._df_with_entry()
        engine = BacktestEngine(
            data=df, ticker="TEST.NS", initial_capital=100000,
            commission=0.0, slippage=0.0,
        )
        eq = engine.run().get_equity_df()
        assert eq.index.nunique() == len(df), \
            "intraday equity index must keep bar timestamps (not collapse to dates)"
