"""
Walk-Forward Analysis UI component.

Displays out-of-sample test results across rolling windows to detect
overfitting. If a strategy only works on training data but fails on
test data, it's likely overfit.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.analytics.walk_forward import WalkForward
from src.analytics.metrics import Metrics
from src.utils.logger import get_logger

logger = get_logger(__name__)


def render_walk_forward(
    df: pd.DataFrame,
    strategy_name: str,
    strategy_class,
    strategy_params: dict,
    backtest_engine_class,
    ticker: str,
    initial_capital: float = 10000.0,
    n_splits: int = 5,
    train_ratio: float = 0.7,
) -> None:
    """
    Run and display walk-forward analysis results.

    Shows:
    1. Per-window returns bar chart (train vs test)
    2. Summary statistics table
    3. Overfitting score (train return vs test return consistency)
    """
    st.markdown("### <i class='fa-solid fa-arrows-rotate' style='color: #2ECC71;'></i> Walk-Forward Analysis", unsafe_allow_html=True)
    st.caption(
        "Tests strategy on out-of-sample data to detect overfitting. "
        "If test returns are consistently worse than train, the strategy may be overfit."
    )

    # ── Settings ──
    col1, col2 = st.columns(2)
    with col1:
        enable_opt = st.checkbox("Enable Dynamic Optimization (Grid Search)", value=False, help="Dynamically re-optimize parameters on the training window, then apply them to the test window.")
    
    metric = "sharpe_ratio"
    param_grid = {}
    
    if enable_opt:
        from app.components.optimizer_ui import PARAM_GRIDS
        
        if strategy_name in PARAM_GRIDS:
            param_grid = PARAM_GRIDS[strategy_name]
            with col2:
                metric = st.selectbox(
                    "Optimize for",
                    ["sharpe_ratio", "cagr", "sortino_ratio", "max_drawdown"],
                    index=0,
                )
        else:
            st.warning(f"No parameter grid defined for {strategy_name}. Falling back to standard walk-forward analysis.")
            enable_opt = false

    with st.spinner("Running walk-forward analysis..."):
        if enable_opt and param_grid:
            results = WalkForward.optimize_windows(
                df=df,
                strategy_class=strategy_class,
                param_grid=param_grid,
                backtest_engine_class=backtest_engine_class,
                ticker=ticker,
                n_splits=n_splits,
                train_ratio=train_ratio,
                initial_capital=initial_capital,
                metric=metric,
            )
        else:
            windows = WalkForward.rolling_windows(df, n_splits, train_ratio)
    
            if not windows:
                st.warning("Not enough data for walk-forward analysis.")
                return
    
            results = []
            for i, (train_df, test_df) in enumerate(windows):
                try:
                    # Train: generate signals and backtest
                    strategy = strategy_class(**strategy_params)
                    train_signals = strategy.generate_signals(train_df)
                    train_engine = backtest_engine_class(
                        data=train_signals, ticker=ticker, initial_capital=initial_capital
                    )
                    train_portfolio = train_engine.run()
                    train_equity = train_portfolio.get_equity_df()
    
                    # Test: generate signals and backtest
                    strategy_test = strategy_class(**strategy_params)
                    test_signals = strategy_test.generate_signals(test_df)
                    test_engine = backtest_engine_class(
                        data=test_signals, ticker=ticker, initial_capital=initial_capital
                    )
                    test_portfolio = test_engine.run()
                    test_equity = test_portfolio.get_equity_df()
    
                    train_ret = Metrics.total_return(train_equity) if not train_equity.empty else 0
                    test_ret = Metrics.total_return(test_equity) if not test_equity.empty else 0
                    train_sharpe = Metrics.sharpe_ratio(train_equity) if not train_equity.empty else 0
                    test_sharpe = Metrics.sharpe_ratio(test_equity) if not test_equity.empty else 0
    
                    results.append({
                        "Window": i + 1,
                        "Train Size": len(train_df),
                        "Test Size": len(test_df),
                        "Train Return (%)": round(train_ret * 100, 2),
                        "Test Return (%)": round(test_ret * 100, 2),
                        "Train Sharpe": round(train_sharpe, 3),
                        "Test Sharpe": round(test_sharpe, 3),
                        "Train Trades": len(train_portfolio.trade_history),
                        "Test Trades": len(test_portfolio.trade_history),
                    })
    
                except Exception as e:
                    logger.warning(f"Walk-forward window {i+1} failed: {e}")
                    results.append({
                        "Window": i + 1,
                        "Train Size": len(train_df),
                        "Test Size": len(test_df),
                        "Train Return (%)": 0,
                        "Test Return (%)": 0,
                        "Error": str(e),
                    })


    # ── Results Table ──
    df_results = pd.DataFrame(results)
    st.dataframe(df_results, width='stretch', height=250)

    # ── Bar Chart: Train vs Test Returns ──
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[f"W{r['Window']}" for r in results],
        y=[r["Train Return (%)"] for r in results],
        name="Train Return (%)",
        marker_color="#00D4AA",
    ))
    fig.add_trace(go.Bar(
        x=[f"W{r['Window']}" for r in results],
        y=[r["Test Return (%)"] for r in results],
        name="Test Return (%)",
        marker_color="#FF6B6B",
    ))
    fig.update_layout(
        barmode="group",
        template="plotly_dark",
        height=350,
        margin=dict(l=20, r=20, t=10, b=20),
        xaxis_title="Window",
        yaxis_title="Return (%)",
    )
    st.plotly_chart(fig, width='stretch')

    # ── Overfitting Score ──
    train_returns = [r["Train Return (%)"] for r in results]
    test_returns = [r["Test Return (%)"] for r in results]

    avg_train = np.mean(train_returns)
    avg_test = np.mean(test_returns)

    if avg_train > 0:
        overfit_ratio = 1 - (avg_test / avg_train) if avg_train != 0 else 0
    else:
        overfit_ratio = 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Avg Train Return", f"{avg_train:+.2f}%")
    col2.metric("Avg Test Return", f"{avg_test:+.2f}%")

    if overfit_ratio < 0.2:
        col3.metric("Overfit Score", f"{overfit_ratio:.0%}", delta="Low Risk ✅")
    elif overfit_ratio < 0.5:
        col3.metric("Overfit Score", f"{overfit_ratio:.0%}", delta="Medium Risk ⚠️")
    else:
        col3.metric("Overfit Score", f"{overfit_ratio:.0%}", delta="High Risk 🔴", delta_color="inverse")
