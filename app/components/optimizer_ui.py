"""
Parameter Optimization UI component.

Provides a grid search interface with:
- Parameter range selection
- Parallel execution with progress
- Results table sorted by chosen metric
- 2D heatmap visualization for 2-parameter strategies
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from src.analytics.parallel_optimizer import ParallelOptimizer
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Default parameter grids per strategy
PARAM_GRIDS = {
    "SMA Crossover": {
        "short_window": list(range(10, 80, 5)),
        "long_window": list(range(50, 300, 10)),
    },
    "RSI Reversion": {
        "window": list(range(7, 28, 3)),
        "oversold": list(range(20, 45, 5)),
        "overbought": list(range(55, 80, 5)),
    },
    "Bollinger Bands": {
        "window": list(range(10, 50, 5)),
        "num_std": [1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0],
    },
    "MACD": {
        "fast_period": list(range(5, 20, 2)),
        "slow_period": list(range(15, 40, 3)),
        "signal_period": list(range(5, 15, 2)),
    },
    "Multi-Factor": {
        "min_score": [2, 3, 4, 5],
        "rsi_window": list(range(7, 28, 3)),
    },
    "Momentum + MR": {
        "entry_rsi": list(range(25, 50, 5)),
        "exit_rsi": list(range(45, 75, 5)),
    },
}


def render_optimizer(
    strategy_name: str,
    strategy_class,
    data: pd.DataFrame,
    backtest_engine_class,
    ticker: str,
    initial_capital: float = 10000.0,
) -> None:
    """
    Run parameter optimization and display results.
    """
    if strategy_name not in PARAM_GRIDS:
        st.info(f"No parameter grid defined for {strategy_name}.")
        return

    st.markdown("### <i class='fa-solid fa-wrench' style='color: #4ECDC4;'></i> Parameter Optimization", unsafe_allow_html=True)
    st.caption(
        f"Grid search over {strategy_name} parameters using parallel execution. "
        "Finds the combination that maximizes Sharpe ratio."
    )

    param_grid = PARAM_GRIDS[strategy_name]
    total_combos = 1
    for v in param_grid.values():
        total_combos *= len(v)

    # Show param ranges
    st.markdown(f"**Parameters:** {', '.join(param_grid.keys())} — **{total_combos} combinations**")

    metric = st.selectbox(
        "Optimize for",
        ["sharpe_ratio", "cagr", "sortino_ratio", "max_drawdown"],
        index=0,
        help="Metric to maximize (max_drawdown is minimized via absolute value)",
    )

    if st.button("Run Optimization", icon=":material/bolt:", type="primary"):
        with st.spinner(f"Running {total_combos} backtests in parallel..."):
            results = ParallelOptimizer.grid_search(
                strategy_class=strategy_class,
                param_grid=param_grid,
                data=data,
                backtest_engine_class=backtest_engine_class,
                ticker=ticker,
                initial_capital=initial_capital,
                metric=metric,
                n_jobs=-1,
            )

        if not results or not results.get("best_params"):
            st.warning("Optimization produced no valid results.")
            return

        # ── Best Params ──
        st.success(
            f"**Best {metric}:** {results['best_metric_value']:.4f} | "
            f"Params: {results['best_params']} | "
            f"Time: {results['elapsed_seconds']:.1f}s",
            icon=":material/emoji_events:"
        )

        # ── Results Table ──
        all_results = results.get("all_results", [])
        if all_results:
            rows = []
            for r in all_results[:50]:  # Top 50
                row = {**r.get("params", {})}
                row["Sharpe"] = round(r.get("sharpe_ratio", 0), 4)
                row["CAGR"] = f"{r.get('cagr', 0)*100:+.2f}%"
                row["Max DD"] = f"{r.get('max_drawdown', 0)*100:.2f}%"
                row["Sortino"] = round(r.get("sortino_ratio", 0), 4)
                row["Trades"] = r.get("total_trades", 0)
                rows.append(row)

            df_results = pd.DataFrame(rows)
            st.dataframe(df_results, width='stretch', height=350)

        # ── Heatmap (only for 2-param grids) ──
        heatmap = results.get("heatmap_data")
        if heatmap:
            _render_heatmap(heatmap, metric)


def _render_heatmap(heatmap_data: dict, metric: str) -> None:
    """Render 2D parameter heatmap."""
    st.markdown("### <i class='fa-solid fa-map' style='color: #E74C3C;'></i> Parameter Heatmap", unsafe_allow_html=True)

    z = np.array(heatmap_data["z_values"])
    x = heatmap_data["x_values"]
    y = heatmap_data["y_values"]

    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=[str(v) for v in x],
        y=[str(v) for v in y],
        colorscale="RdYlGn",
        text=np.round(z, 4),
        texttemplate="%{text}",
        hovertemplate=(
            f"{heatmap_data['x_param']}: %{{x}}<br>"
            f"{heatmap_data['y_param']}: %{{y}}<br>"
            f"{metric}: %{{z:.4f}}<extra></extra>"
        ),
    ))

    fig.update_layout(
        xaxis_title=heatmap_data["x_param"],
        yaxis_title=heatmap_data["y_param"],
        template="plotly_dark",
        height=450,
        margin=dict(l=20, r=20, t=10, b=20),
    )
    st.plotly_chart(fig, width='stretch')
