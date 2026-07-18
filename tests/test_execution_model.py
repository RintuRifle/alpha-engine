"""
Phase 3 tests — execution realism: spread, slippage models, liquidity caps,
partial fills, and short margin.
"""

import pandas as pd
import pytest

from src.backtester.execution_model import ExecutionModel
from src.backtester.engine import BacktestEngine

WARMUP = 20


def make_df(volume=1e6, n=30):
    rows = []
    for i in range(n):
        rows.append({
            "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0,
            "volume": volume, "signal": 0,
        })
    rows[WARMUP - 1]["signal"] = 1  # entry at bar WARMUP open
    df = pd.DataFrame(rows)
    df["date"] = pd.date_range("2024-01-01", periods=len(df), freq="B")
    return df


class TestSpreadAndSlippage:
    def test_spread_is_adverse_both_sides(self):
        m = ExecutionModel(spread_bps=20, slippage_model="fixed", slippage_bps=0)
        buy = m.effective_price(100.0, "BUY")
        sell = m.effective_price(100.0, "SELL")
        assert buy == pytest.approx(100 * (1 + 0.001))   # +10 bps (half spread)
        assert sell == pytest.approx(100 * (1 - 0.001))  # -10 bps
        assert buy > 100 > sell

    def test_volatility_slippage_scales_with_bar_range(self):
        m = ExecutionModel(slippage_model="volatility", vol_coef=0.1)
        calm = {"open": 100, "high": 100.5, "low": 99.5, "close": 100}
        wild = {"open": 100, "high": 105.0, "low": 95.0, "close": 100}
        p_calm = m.effective_price(100.0, "BUY", calm)
        p_wild = m.effective_price(100.0, "BUY", wild)
        assert p_wild > p_calm > 100.0

    def test_volume_impact_scales_with_order_size(self):
        m = ExecutionModel(slippage_model="volume", impact_bps=100)
        bar = {"open": 100, "high": 101, "low": 99, "close": 100, "volume": 10000}
        small = m.effective_price(100.0, "BUY", bar, quantity=100)    # 1% part.
        large = m.effective_price(100.0, "BUY", bar, quantity=10000)  # 100% part.
        assert large > small > 100.0
        # sqrt: 100% participation → full 100 bps
        assert large == pytest.approx(100 * (1 + 0.01), rel=1e-4)

    def test_invalid_model_rejected(self):
        with pytest.raises(ValueError):
            ExecutionModel(slippage_model="quantum")


class TestLiquidityCap:
    def test_cap_quantity(self):
        m = ExecutionModel(max_participation=0.1)
        bar = {"volume": 1000}
        qty, capped = m.cap_quantity(500, bar)
        assert (qty, capped) == (100, True)
        qty2, capped2 = m.cap_quantity(50, bar)
        assert (qty2, capped2) == (50, False)

    def test_engine_partial_fill_on_thin_volume(self):
        # tiny bar volume: full-size order must get capped
        df = make_df(volume=200)
        engine = BacktestEngine(
            data=df, ticker="TEST", initial_capital=100000,
            commission=0.0, slippage=0.0,
            execution={"max_participation": 0.1, "slippage_bps": 0},
        )
        p = engine.run()
        buys = [t for t in p.trade_history if t["action"] == "BUY"]
        assert len(buys) == 1
        assert buys[0]["quantity"] == 20, "fill must be 10% of 200-share bar volume"
        assert engine.capped_entries == 1

    def test_no_cap_when_participation_unlimited(self):
        df = make_df(volume=200)
        engine = BacktestEngine(
            data=df, ticker="TEST", initial_capital=100000,
            commission=0.0, slippage=0.0,
            execution={"max_participation": 1.0, "slippage_bps": 0},
        )
        p = engine.run()
        buys = [t for t in p.trade_history if t["action"] == "BUY"]
        assert buys[0]["quantity"] > 500
        assert engine.capped_entries == 0


class TestLegacyCompatibility:
    def test_no_execution_config_matches_legacy_flat_slippage(self):
        """Without an execution config the ExecutionModel must reproduce the
        old TransactionCosts behavior exactly (golden regression)."""
        df = make_df()
        legacy_slip = 0.0005
        engine = BacktestEngine(
            data=df, ticker="TEST", initial_capital=100000,
            commission=0.001, slippage=legacy_slip,
        )
        p = engine.run()
        buys = [t for t in p.trade_history if t["action"] == "BUY"]
        assert buys[0]["price"] == pytest.approx(100 * (1 + legacy_slip))


class TestShortMargin:
    def test_short_margin_pct_limits_position_size(self):
        df = make_df()
        df["signal"] = 0
        df.loc[WARMUP - 1, "signal"] = -1  # short entry
        common = dict(
            data=df.copy(), ticker="TEST", initial_capital=10000,
            commission=0.0, slippage=0.0, allow_short=True,
        )
        e_base = BacktestEngine(
            **{**common, "execution": {"short_margin_pct": 1.0, "slippage_bps": 0}}
        )
        p_base = e_base.run()
        e_regt = BacktestEngine(
            **{**common, "data": df.copy(),
               "execution": {"short_margin_pct": 1.5, "slippage_bps": 0}}
        )
        p_regt = e_regt.run()
        s_base = [t for t in p_base.trade_history if t["action"] == "SHORT"]
        s_regt = [t for t in p_regt.trade_history if t["action"] == "SHORT"]
        assert s_base and s_regt
        # Reg-T style 150% collateral must shrink the allowed short size
        assert s_regt[0]["quantity"] < s_base[0]["quantity"]
        # 10k cash / (100 price × 1.5 margin) = 66 shares max
        assert s_regt[0]["quantity"] <= 66


class TestAssumptionsTransparency:
    def test_assumptions_surface_all_knobs(self):
        m = ExecutionModel(spread_bps=10, slippage_model="volume",
                           impact_bps=25, max_participation=0.05)
        a = m.assumptions()
        assert a["spread_bps"] == 10
        assert a["slippage_model"] == "volume"
        assert a["impact_bps"] == 25
        assert a["max_participation"] == 0.05
        assert "cash" in a["account"]
