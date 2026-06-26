"""
Strategy Comparison — runs all strategies on the same data and ranks them.

Composite scoring weights:
  Sharpe × 0.35 + Sortino × 0.25 + (−MaxDD) × 0.20 + CAGR × 0.15 + WinRate × 0.05

This is the "strategy bake-off" that quant funds run before deploying capital.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time

from src.strategies.ma_crossover import MACrossover
from src.strategies.rsi_reversion import RSIReversion
from src.strategies.bollinger_bands import BollingerBands
from src.strategies.macd_strategy import MACDStrategy
from src.strategies.buy_and_hold import BuyAndHold
from src.strategies.multi_factor import MultiFactorStrategy
from src.strategies.momentum_mr import MomentumMR
from src.strategies.regime_detector import RegimeDetector
from src.backtester.engine import BacktestEngine
from src.analytics.metrics import Metrics

# Default strategies with sensible parameters
DEFAULT_STRATEGIES = {
    "SMA Crossover": (MACrossover, {"short_window": 50, "long_window": 200}),
    "RSI Reversion": (RSIReversion, {"window": 14, "oversold": 30, "overbought": 70}),
    "Bollinger Bands": (BollingerBands, {"window": 20, "num_std": 2.0}),
    "MACD": (MACDStrategy, {"fast_period": 12, "slow_period": 26, "signal_period": 9}),
    "Multi-Factor": (MultiFactorStrategy, {"min_score": 3}),
    "Momentum + MR": (MomentumMR, {"rsi_window": 14, "entry_rsi": 40, "exit_rsi": 55}),
    "Buy & Hold": (BuyAndHold, {}),
}


def run_comparison(
    df: pd.DataFrame,
    ticker: str,
    initial_capital: float = 10000.0,
    allocation: float = 0.95,
    allow_short: bool = False,
    use_stops: bool = False,
    atr_multiplier: float = 2.0,
) -> dict:
    """
    Run all strategies on the same data and return comparison results.

    Returns:
        Dict with 'results' (list of per-strategy dicts), 'equity_curves', 'regime_df'.
    """
    results = []
    equity_curves = {}

    # Detect regime
    detector = RegimeDetector()
    regime_df = detector.detect(df)

    progress = st.progress(0, text="Comparing strategies...")

    for i, (name, (strategy_class, params)) in enumerate(DEFAULT_STRATEGIES.items()):
        pct = int((i / len(DEFAULT_STRATEGIES)) * 100)
        progress.progress(pct, text=f"Running {name}...")

        try:
            start_time = time.time()

            strategy = strategy_class(**params)
            df_signals = strategy.generate_signals(df)
            engine = BacktestEngine(
                data=df_signals,
                ticker=ticker,
                initial_capital=initial_capital,
                allocation=allocation,
                allow_short=allow_short,
                use_stops=use_stops,
                atr_multiplier=atr_multiplier,
            )
            portfolio = engine.run()
            equity_df = portfolio.get_equity_df()

            elapsed = time.time() - start_time

            if not equity_df.empty:
                perf = Metrics.compute_all(equity_df, portfolio.trade_history)
                equity_curves[name] = equity_df["total_equity"]

                results.append({
                    "Strategy": name,
                    "CAGR (%)": round(perf["cagr"] * 100, 2),
                    "Sharpe": round(perf["sharpe_ratio"], 3),
                    "Sortino": round(perf["sortino_ratio"], 3),
                    "Max DD (%)": round(perf["max_drawdown"] * 100, 2),
                    "Win Rate (%)": round(perf["win_rate"] * 100, 1),
                    "Trades": perf["total_trades"],
                    "Volatility (%)": round(perf["volatility"] * 100, 2),
                    "Omega": round(perf["omega_ratio"], 2) if perf["omega_ratio"] != float("inf") else 999,
                    "Time (s)": round(elapsed, 2),
                    # Raw values for composite scoring
                    "_sharpe": perf["sharpe_ratio"],
                    "_sortino": perf["sortino_ratio"],
                    "_max_dd": perf["max_drawdown"],
                    "_cagr": perf["cagr"],
                    "_win_rate": perf["win_rate"],
                })

        except Exception as e:
            results.append({
                "Strategy": name,
                "CAGR (%)": 0,
                "Sharpe": 0,
                "Error": str(e),
            })

    progress.progress(100, text="✅ Comparison complete!")

    # Compute composite score
    if results:
        _compute_composite_scores(results)

    return {
        "results": sorted(results, key=lambda x: x.get("Composite", 0), reverse=True),
        "equity_curves": equity_curves,
        "regime_df": regime_df,
    }


def _compute_composite_scores(results: list[dict]):
    """
    Compute composite ranking score for each strategy.

    Composite = Sharpe × 0.35 + Sortino × 0.25 + (−MaxDD_normalized) × 0.20
              + CAGR × 0.15 + WinRate × 0.05

    All metrics are min-max normalized to [0, 1] before weighting.
    """
    # Extract raw values
    sharpes = [r.get("_sharpe", 0) for r in results]
    sortinos = [r.get("_sortino", 0) for r in results]
    max_dds = [abs(r.get("_max_dd", 0)) for r in results]  # Absolute value
    cagrs = [r.get("_cagr", 0) for r in results]
    win_rates = [r.get("_win_rate", 0) for r in results]

    def _normalize(values):
        """Min-max normalize to [0, 1]."""
        v = np.array(values, dtype=float)
        v_min, v_max = v.min(), v.max()
        if v_max == v_min:
            return np.ones_like(v) * 0.5
        return (v - v_min) / (v_max - v_min)

    n_sharpe = _normalize(sharpes)
    n_sortino = _normalize(sortinos)
    n_dd = 1 - _normalize(max_dds)  # Lower DD = better → invert
    n_cagr = _normalize(cagrs)
    n_wr = _normalize(win_rates)

    for i, r in enumerate(results):
        composite = (
            n_sharpe[i] * 0.35 +
            n_sortino[i] * 0.25 +
            n_dd[i] * 0.20 +
            n_cagr[i] * 0.15 +
            n_wr[i] * 0.05
        )
        r["Composite"] = round(float(composite), 3)

    # Clean up internal keys
    for r in results:
        for key in ["_sharpe", "_sortino", "_max_dd", "_cagr", "_win_rate"]:
            r.pop(key, None)


def render_comparison(comparison_data: dict, initial_capital: float = 10000.0):
    """Render the full strategy comparison dashboard."""

    results = comparison_data["results"]
    equity_curves = comparison_data["equity_curves"]
    regime_df = comparison_data["regime_df"]

    # ── Comparison Table ──
    st.markdown("### 🏆 Strategy Ranking")
    df_results = pd.DataFrame(results)

    # Display columns (exclude internal/error columns)
    display_cols = [c for c in df_results.columns if not c.startswith("_") and c != "Error"]
    if "Composite" in display_cols:
        # Move Composite to front
        display_cols.remove("Composite")
        display_cols.insert(1, "Composite")

    st.dataframe(
        df_results[display_cols].style.background_gradient(
            subset=["Composite"], cmap="RdYlGn"
        ).background_gradient(
            subset=["Sharpe"], cmap="RdYlGn"
        ).background_gradient(
            subset=["CAGR (%)"], cmap="RdYlGn"
        ).format({
            "Composite": "{:.3f}",
            "CAGR (%)": "{:+.2f}%",
            "Max DD (%)": "{:.2f}%",
            "Sharpe": "{:.3f}",
            "Sortino": "{:.3f}",
            "Win Rate (%)": "{:.1f}%",
            "Volatility (%)": "{:.2f}%",
            "Time (s)": "{:.2f}s",
        }),
        width='stretch',
        height=320,
    )

    # Winner callout
    if results:
        winner = results[0]
        st.success(
            f"🥇 **{winner['Strategy']}** wins with Composite Score: **{winner.get('Composite', 0):.3f}** "
            f"| CAGR: {winner.get('CAGR (%)', 0):+.2f}% "
            f"| Sharpe: {winner.get('Sharpe', 0):.3f} "
            f"| Max DD: {winner.get('Max DD (%)', 0):.2f}%"
        )

    # ── Overlaid Equity Curves ──
    st.markdown("### 📈 Equity Curves Comparison")
    fig = go.Figure()

    colors = [
        "#00D4AA", "#FF6B6B", "#4ECDC4", "#FFD93D",
        "#45B7D1", "#FF8C00", "#9B59B6",
    ]

    for i, (name, equity) in enumerate(equity_curves.items()):
        color = colors[i % len(colors)]
        fig.add_trace(go.Scatter(
            x=equity.index,
            y=equity.values,
            mode="lines",
            name=name,
            line=dict(color=color, width=2),
        ))

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Portfolio Value ($)",
        template="plotly_dark",
        height=500,
        margin=dict(l=20, r=20, t=10, b=20),
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        hovermode="x unified",
    )
    st.plotly_chart(fig, width='stretch')

    # ── Regime Overlay ──
    st.markdown("### 🌡️ Market Regime")
    _render_regime_chart(regime_df)


def _render_regime_chart(regime_df: pd.DataFrame):
    """Show regime classification over time as a color-coded area chart."""
    if "regime" not in regime_df.columns:
        return

    fig = go.Figure()

    regime_colors = {
        "trending": "rgba(0, 212, 170, 0.3)",
        "ranging": "rgba(255, 217, 61, 0.3)",
        "crisis": "rgba(255, 68, 68, 0.3)",
    }

    # ADX line
    if "adx" in regime_df.columns:
        fig.add_trace(go.Scatter(
            x=regime_df["date"],
            y=regime_df["adx"],
            mode="lines",
            name="ADX",
            line=dict(color="#00D4AA", width=2),
        ))

    # Regime background
    fig.add_hline(y=25, line_dash="dot", line_color="rgba(255,255,255,0.3)",
                  annotation_text="Trending threshold")
    fig.add_hline(y=20, line_dash="dot", line_color="rgba(255,255,255,0.3)",
                  annotation_text="Ranging threshold")

    # Volatility on secondary axis
    if "volatility_ann" in regime_df.columns:
        fig.add_trace(go.Scatter(
            x=regime_df["date"],
            y=regime_df["volatility_ann"] * 100,
            mode="lines",
            name="Volatility (%)",
            line=dict(color="#FF6B6B", width=1.5, dash="dot"),
            yaxis="y2",
        ))

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="ADX",
        yaxis2=dict(title="Volatility (%)", overlaying="y", side="right"),
        template="plotly_dark",
        height=350,
        margin=dict(l=20, r=20, t=10, b=20),
        hovermode="x unified",
    )
    st.plotly_chart(fig, width='stretch')

    # Regime distribution
    if "regime" in regime_df.columns:
        counts = regime_df["regime"].value_counts()
        col1, col2, col3 = st.columns(3)
        col1.metric("🟢 Trending", f"{counts.get('trending', 0)} days")
        col2.metric("🟡 Ranging", f"{counts.get('ranging', 0)} days")
        col3.metric("🔴 Crisis", f"{counts.get('crisis', 0)} days")
