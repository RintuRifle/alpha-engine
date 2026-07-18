"""
Synthetic-candle tests for intrabar stop-loss correctness.

These craft artificial OHLC sequences where the expected engine behavior
is known by hand — gap-through-stop, intrabar stop cross, no-trigger,
and trailing stop behavior.
"""

import numpy as np
import pandas as pd
import pytest

from src.backtester.engine import BacktestEngine
from src.backtester.risk_controls import RiskControls
from src.analytics.metrics import Metrics

WARMUP = 20  # bars before the entry signal (ATR needs 14+)


def make_df(post_entry_bars: list[dict]) -> pd.DataFrame:
    """
    Build a synthetic OHLCV+signal frame:
    - WARMUP flat bars around 100 (high 101 / low 99 → ATR ≈ 2)
    - buy signal on the last warmup bar (executes next bar's open)
    - then caller-provided bars
    """
    rows = []
    for i in range(WARMUP):
        rows.append(
            {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0,
             "volume": 1e6, "signal": 0}
        )
    rows[-1]["signal"] = 1  # entry executes at next bar open
    rows.extend(
        {"volume": 1e6, "signal": 0, **b} for b in post_entry_bars
    )
    df = pd.DataFrame(rows)
    df["date"] = pd.date_range("2024-01-01", periods=len(df), freq="B")
    return df


def run(df, **kwargs):
    engine = BacktestEngine(
        data=df,
        ticker="TEST",
        initial_capital=100000,
        commission=0.0,
        slippage=0.0,
        use_stops=True,
        atr_multiplier=2.0,
        **kwargs,
    )
    return engine.run()


def sells(portfolio):
    return [t for t in portfolio.trade_history if t["action"] == "SELL"]


class TestIntrabarStops:
    def test_intrabar_low_triggers_stop_even_if_close_recovers(self):
        """Entry ~100, ATR≈2 → stop ≈96. Bar dips to 94 and closes at 100:
        old engine (open-only check) missed this; now it must fill AT the stop."""
        df = make_df([
            {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0},  # entry bar
            {"open": 100.0, "high": 101.0, "low": 94.0, "close": 100.0},  # dip bar
            {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0},
        ])
        p = run(df, use_trailing_stop=False)
        s = sells(p)
        assert len(s) == 1, "intrabar dip through stop must trigger an exit"
        # conservative fill at the stop level (~96), never at the low
        assert 94.0 < s[0]["price"] <= 97.5
        assert p.positions.get("TEST", 0) == 0

    def test_gap_through_stop_fills_at_open_not_stop(self):
        """Stop ≈96 but next bar opens at 90 — you can't fill at 96;
        realistic fill is the gapped open."""
        df = make_df([
            {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0},  # entry bar
            {"open": 90.0, "high": 91.0, "low": 89.0, "close": 90.5},     # gap down
        ])
        p = run(df, use_trailing_stop=False)
        s = sells(p)
        assert len(s) == 1
        assert s[0]["price"] == pytest.approx(90.0, abs=0.5), \
            "gap-through-stop must fill at the open, not the stop price"

    def test_no_trigger_when_low_stays_above_stop(self):
        df = make_df([
            {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0},
            {"open": 100.0, "high": 101.0, "low": 97.0, "close": 100.0},  # low 97 > stop ~96
            {"open": 100.0, "high": 101.0, "low": 98.0, "close": 100.5},
        ])
        p = run(df, use_trailing_stop=False)
        assert len(sells(p)) == 0
        assert p.positions.get("TEST", 0) > 0

    def test_trailing_stop_ratchets_up_and_triggers(self):
        """Price runs to ~120, trailing stop follows (~116); later dip to 110
        must trigger even though price never revisits the original stop (~96)."""
        rally = [
            {"open": 100 + 4 * i, "high": 104 + 4 * i, "low": 99 + 4 * i,
             "close": 103 + 4 * i}
            for i in range(5)  # highs reach 120
        ]
        dip = [{"open": 118.0, "high": 119.0, "low": 110.0, "close": 118.0}]
        df = make_df(rally + dip)
        p = run(df, use_trailing_stop=True)
        s = sells(p)
        assert len(s) == 1, "trailing stop must trigger on the dip"
        assert s[0]["price"] > 105.0, "fill must be near the trailed stop, far above the entry stop"

    def test_same_bar_high_cannot_raise_stop_before_low_check(self):
        """Trailing update happens AFTER the stop check: a bar with a huge high
        AND a low through the ORIGINAL stop must exit at the original stop."""
        rc = RiskControls(atr_multiplier=2.0, use_trailing_stop=True)
        rc.on_entry(entry_price=100.0, atr_value=2.0, position_type="long")
        original_stop = rc.current_stop_price  # 96
        triggered, fill = rc.check_stop_intrabar(
            open_price=100.0, high=130.0, low=95.0
        )
        assert triggered
        assert fill == pytest.approx(original_stop), \
            "same-bar high must not trail the stop before the same bar's low is tested"


class TestTimeframeAnnualization:
    def test_daily_bars_infer_252(self):
        idx = pd.date_range("2024-01-01", periods=100, freq="B")
        eq = pd.DataFrame({"total_equity": np.linspace(100, 110, 100)}, index=idx)
        assert Metrics.infer_periods_per_year(eq) == pytest.approx(252)

    def test_minute_bars_infer_intraday_factor(self):
        idx = pd.date_range("2024-01-01 09:30", periods=390, freq="1min")
        eq = pd.DataFrame({"total_equity": np.linspace(100, 101, 390)}, index=idx)
        ann = Metrics.infer_periods_per_year(eq)
        assert ann == pytest.approx(390 * 252, rel=0.01), \
            "1-minute bars → 390 bars/session × 252 sessions"

    def test_sharpe_differs_between_timeframes_for_same_values(self):
        vals = 100 * np.cumprod(1 + np.random.default_rng(7).normal(0.0002, 0.01, 300))
        daily = pd.DataFrame(
            {"total_equity": vals},
            index=pd.date_range("2024-01-01", periods=300, freq="B"),
        )
        minute = pd.DataFrame(
            {"total_equity": vals},
            index=pd.date_range("2024-01-01 09:30", periods=300, freq="1min"),
        )
        s_daily = Metrics.sharpe_ratio(daily)
        s_minute = Metrics.sharpe_ratio(minute)
        assert abs(s_minute) > abs(s_daily) * 5, \
            "same return series must annualize very differently at 1-minute frequency"
