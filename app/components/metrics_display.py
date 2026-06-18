"""
Metrics display component for the Streamlit dashboard.

Renders KPI cards with color coding: green for positive metrics,
red for negative. Shows 8 key performance indicators.
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any

from src.analytics.metrics import Metrics
from src.analytics.risk_manager import RiskManager


def render_metrics(
    equity_df: pd.DataFrame,
    trade_history: list,
    portfolio_returns: pd.Series | None = None,
    benchmark_returns: pd.Series | None = None,
) -> None:
    """
    Render KPI metric cards in a grid layout.

    Args:
        equity_df: Portfolio equity DataFrame.
        trade_history: List of trade records.
        portfolio_returns: Daily portfolio returns (for alpha/beta).
        benchmark_returns: Daily benchmark returns (for alpha/beta).
    """
    if equity_df.empty:
        return

    # Compute all metrics
    perf = Metrics.compute_all(equity_df, trade_history)
    risk = RiskManager.compute_all_risk(equity_df, portfolio_returns, benchmark_returns)

    # ── Row 1: Primary metrics ──
    st.markdown("### 📋 Performance Summary")
    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "CAGR",
        f"{perf['cagr']*100:+.2f}%",
        delta=f"{'▲' if perf['cagr'] > 0 else '▼'}",
        delta_color="normal" if perf["cagr"] >= 0 else "inverse",
    )
    col2.metric(
        "Sharpe Ratio",
        f"{perf['sharpe_ratio']:.2f}",
        delta="Good" if perf["sharpe_ratio"] > 1 else "Low",
        delta_color="normal" if perf["sharpe_ratio"] > 0.5 else "inverse",
    )
    col3.metric(
        "Max Drawdown",
        f"{perf['max_drawdown']*100:.2f}%",
        delta=f"{perf['max_dd_duration']} days",
        delta_color="inverse",
    )
    col4.metric(
        "Win Rate",
        f"{perf['win_rate']*100:.1f}%",
        delta=f"{perf['total_trades']} trades",
        delta_color="normal" if perf["win_rate"] > 0.5 else "inverse",
    )

    # ── Row 2: Advanced metrics ──
    col5, col6, col7, col8 = st.columns(4)

    col5.metric(
        "Sortino Ratio",
        f"{perf['sortino_ratio']:.2f}",
        delta_color="normal" if perf["sortino_ratio"] > 0 else "inverse",
    )
    col6.metric(
        "Alpha (Annual)",
        f"{risk['alpha']*100:+.3f}%",
        delta_color="normal" if risk["alpha"] > 0 else "inverse",
    )
    col7.metric(
        "Beta",
        f"{risk['beta']:.2f}",
    )
    col8.metric(
        "VaR (95%)",
        f"{risk['var_95']*100:.2f}%",
        delta_color="inverse",
    )

    # ── Expandable details ──
    with st.expander("📊 Detailed Metrics"):
        detail_col1, detail_col2, detail_col3 = st.columns(3)

        with detail_col1:
            st.markdown("**Returns**")
            st.write(f"Total Return: {perf['total_return']*100:+.2f}%")
            st.write(f"CAGR: {perf['cagr']*100:+.2f}%")
            st.write(f"Volatility: {perf['volatility']*100:.2f}%")

        with detail_col2:
            st.markdown("**Risk-Adjusted**")
            st.write(f"Sharpe: {perf['sharpe_ratio']:.3f}")
            st.write(f"Sortino: {perf['sortino_ratio']:.3f}")
            st.write(f"Calmar: {perf['calmar_ratio']:.3f}")

        with detail_col3:
            st.markdown("**Risk**")
            st.write(f"Max DD: {perf['max_drawdown']*100:.2f}%")
            st.write(f"VaR 95%: {risk['var_95']*100:.3f}%")
            st.write(f"CVaR 95%: {risk['cvar_95']*100:.3f}%")
            pf = perf["profit_factor"]
            pf_str = f"{pf:.2f}" if pf != float("inf") else "∞"
            st.write(f"Profit Factor: {pf_str}")
