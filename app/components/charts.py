"""
Chart components for the Streamlit dashboard.

Uses Plotly for interactive charts: equity curve with benchmark overlay,
drawdown chart, and returns distribution histogram.
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np


def render_equity_curve(
    equity_df: pd.DataFrame,
    benchmark_equity: pd.Series | None = None,
    strategy_name: str = "Strategy",
) -> None:
    """
    Render an interactive equity curve chart with optional benchmark overlay.

    Args:
        equity_df: Portfolio equity DataFrame with 'total_equity' column.
        benchmark_equity: Optional benchmark equity Series for comparison.
        strategy_name: Strategy name for the legend.
    """
    if equity_df.empty:
        st.warning("No equity data to display.")
        return

    st.markdown("### 📈 Equity Curve")

    fig = go.Figure()

    # Strategy equity line
    fig.add_trace(
        go.Scatter(
            x=equity_df.index,
            y=equity_df["total_equity"],
            mode="lines",
            name=strategy_name,
            line=dict(color="#00D4AA", width=2.5),
        )
    )

    # Benchmark overlay
    if benchmark_equity is not None and not benchmark_equity.empty:
        fig.add_trace(
            go.Scatter(
                x=benchmark_equity.index,
                y=benchmark_equity.values,
                mode="lines",
                name=benchmark_equity.name or "Benchmark",
                line=dict(color="#FF6B6B", width=1.5, dash="dot"),
                opacity=0.8,
            )
        )

    fig.update_layout(
        title=None,
        xaxis_title="Date",
        yaxis_title="Portfolio Value ($)",
        template="plotly_dark",
        height=450,
        margin=dict(l=20, r=20, t=10, b=20),
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        hovermode="x unified",
    )
    st.plotly_chart(fig, width='stretch')


def render_drawdown_chart(equity_df: pd.DataFrame) -> None:
    """Render a drawdown chart showing peak-to-trough declines."""
    if equity_df.empty:
        return

    st.markdown("### 📉 Drawdown")

    equity = equity_df["total_equity"]
    cummax = equity.cummax()
    drawdown = ((equity - cummax) / cummax) * 100  # As percentage

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=equity_df.index,
            y=drawdown,
            fill="tozeroy",
            name="Drawdown",
            line=dict(color="#FF4444", width=1),
            fillcolor="rgba(255, 68, 68, 0.3)",
        )
    )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Drawdown (%)",
        template="plotly_dark",
        height=300,
        margin=dict(l=20, r=20, t=10, b=20),
        hovermode="x unified",
    )
    st.plotly_chart(fig, width='stretch')


def render_returns_histogram(equity_df: pd.DataFrame) -> None:
    """Render a histogram of daily returns distribution."""
    if equity_df.empty or len(equity_df) < 2:
        return

    st.markdown("### 📊 Returns Distribution")

    returns = equity_df["total_equity"].pct_change().dropna() * 100

    fig = go.Figure()
    fig.add_trace(
        go.Histogram(
            x=returns,
            nbinsx=50,
            name="Daily Returns",
            marker_color="#4ECDC4",
            opacity=0.8,
        )
    )

    # Add vertical line at mean
    mean_ret = returns.mean()
    fig.add_vline(
        x=mean_ret,
        line_dash="dash",
        line_color="#FFD93D",
        annotation_text=f"Mean: {mean_ret:.3f}%",
    )

    fig.update_layout(
        xaxis_title="Daily Return (%)",
        yaxis_title="Frequency",
        template="plotly_dark",
        height=350,
        margin=dict(l=20, r=20, t=10, b=20),
    )
    st.plotly_chart(fig, width='stretch')


def render_monte_carlo(sim_df: pd.DataFrame, percentiles: dict) -> None:
    """Render Monte Carlo simulation paths with confidence bands."""
    if sim_df.empty:
        return

    st.markdown("### 🎲 Monte Carlo Simulation (1000 paths)")

    fig = go.Figure()

    # Plot a sample of individual paths (faded)
    sample_cols = sim_df.columns[:50]  # Show max 50 paths for performance
    for col in sample_cols:
        fig.add_trace(
            go.Scatter(
                x=sim_df.index,
                y=sim_df[col],
                mode="lines",
                line=dict(color="rgba(100, 200, 255, 0.05)", width=0.5),
                showlegend=False,
                hoverinfo="skip",
            )
        )

    # Percentile bands
    colors = {
        "p5": ("#FF4444", "5th Percentile (Worst Case)"),
        "p25": ("#FF8C00", "25th Percentile"),
        "p50": ("#00D4AA", "Median"),
        "p75": ("#4ECDC4", "75th Percentile"),
        "p95": ("#45B7D1", "95th Percentile (Best Case)"),
    }

    for key, (color, label) in colors.items():
        if key in percentiles:
            fig.add_trace(
                go.Scatter(
                    x=percentiles[key].index,
                    y=percentiles[key].values,
                    mode="lines",
                    name=label,
                    line=dict(color=color, width=2),
                )
            )

    fig.update_layout(
        xaxis_title="Trading Day",
        yaxis_title="Portfolio Value (Normalized)",
        template="plotly_dark",
        height=450,
        margin=dict(l=20, r=20, t=10, b=20),
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
    )
    st.plotly_chart(fig, width='stretch')


def render_rolling_metrics(equity_df: pd.DataFrame, window: int = 60) -> None:
    """
    Render rolling Sharpe, volatility, and return over time.

    Strategies that look great in aggregate may have terrible periods.
    This chart exposes time-varying performance quality.
    """
    if equity_df.empty or len(equity_df) < window + 10:
        st.info(f"Need at least {window + 10} data points for rolling metrics.")
        return

    st.markdown(f"### 📈 Rolling Metrics ({window}-day window)")

    returns = equity_df["total_equity"].pct_change().dropna()

    # Rolling Sharpe
    rolling_mean = returns.rolling(window).mean()
    rolling_std = returns.rolling(window).std()
    rolling_sharpe = (rolling_mean / rolling_std) * np.sqrt(252)

    # Rolling Volatility (annualized)
    rolling_vol = rolling_std * np.sqrt(252) * 100  # as percentage

    # Cumulative return
    cum_return = ((1 + returns).cumprod() - 1) * 100

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        subplot_titles=["Rolling Sharpe Ratio", "Rolling Volatility (%)", "Cumulative Return (%)"],
    )

    # Sharpe
    fig.add_trace(
        go.Scatter(
            x=rolling_sharpe.index, y=rolling_sharpe.values,
            mode="lines", name="Sharpe",
            line=dict(color="#00D4AA", width=2),
        ), row=1, col=1
    )
    fig.add_hline(y=1.0, line_dash="dot", line_color="rgba(255,255,255,0.3)",
                  annotation_text="Good (1.0)", row=1, col=1)
    fig.add_hline(y=0.0, line_dash="dot", line_color="rgba(255,68,68,0.3)",
                  row=1, col=1)

    # Volatility
    fig.add_trace(
        go.Scatter(
            x=rolling_vol.index, y=rolling_vol.values,
            mode="lines", name="Volatility",
            line=dict(color="#FF6B6B", width=2),
        ), row=2, col=1
    )

    # Cumulative Return
    fig.add_trace(
        go.Scatter(
            x=cum_return.index, y=cum_return.values,
            fill="tozeroy", name="Cum. Return",
            line=dict(color="#4ECDC4", width=2),
            fillcolor="rgba(78, 205, 196, 0.2)",
        ), row=3, col=1
    )

    fig.update_layout(
        template="plotly_dark",
        height=700,
        margin=dict(l=20, r=20, t=30, b=20),
        showlegend=False,
    )
    st.plotly_chart(fig, width='stretch')


def render_stress_test(stress_results: list[dict]) -> None:
    """Render stress test scenario results."""
    if not stress_results:
        return

    st.markdown("### ⚡ Stress Test Scenarios")

    cols = st.columns(len(stress_results))
    for i, scenario in enumerate(stress_results):
        with cols[i]:
            dd = scenario["max_drawdown_pct"]
            color = "🟢" if dd > -15 else ("🟡" if dd > -30 else "🔴")
            st.metric(
                scenario["scenario"],
                f"{scenario['total_return_pct']:+.1f}%",
                delta=f"Max DD: {dd:.1f}%",
                delta_color="inverse",
            )
            st.caption(scenario["description"])

