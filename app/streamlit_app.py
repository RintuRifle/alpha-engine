"""
Quant Research Platform — Streamlit Dashboard

Main entry point for the interactive web application.
Wires together: data fetching, strategy execution, backtesting,
analytics, benchmark comparison, and visualization.

Usage:
    streamlit run app/streamlit_app.py
"""

import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd

from src.data.cache_manager import CacheManager
from src.strategies.ma_crossover import MACrossover
from src.strategies.rsi_reversion import RSIReversion
from src.strategies.bollinger_bands import BollingerBands
from src.strategies.macd_strategy import MACDStrategy
from src.strategies.buy_and_hold import BuyAndHold
from src.backtester.engine import BacktestEngine
from src.analytics.benchmark import Benchmark
from src.analytics.monte_carlo import MonteCarlo
from components import sidebar, charts, metrics_display

# ── Page Config ──
st.set_page_config(
    page_title="Quant Research Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Strategy Registry ──
STRATEGY_MAP = {
    "SMA Crossover": MACrossover,
    "RSI Reversion": RSIReversion,
    "Bollinger Bands": BollingerBands,
    "MACD": MACDStrategy,
    "Buy & Hold": BuyAndHold,
}


def main():
    # ── Header ──
    st.markdown(
        """
        <h1 style='text-align: center; margin-bottom: 0;'>📈 Quant Research Platform</h1>
        <p style='text-align: center; color: #888; margin-top: 0;'>
            Backtest trading strategies with real market data
        </p>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # ── Sidebar Inputs ──
    inputs = sidebar.render_sidebar()

    # ── Run Button ──
    if st.sidebar.button("🚀 Run Backtest", type="primary", width="stretch"):
        _run_backtest(inputs)

    # ── Show cached results if available ──
    elif "equity_df" in st.session_state:
        _display_results(st.session_state)


def _run_backtest(inputs: dict) -> None:
    """Execute the full backtest pipeline and display results."""

    progress = st.progress(0, text="Initializing...")

    try:
        # ── Step 1: Fetch Data ──
        progress.progress(10, text=f"Fetching data for {inputs['ticker']}...")
        cache = CacheManager()
        df = cache.get_data(inputs["ticker"], inputs["start_date"], inputs["end_date"])

        # ── Step 2: Generate Strategy Signals ──
        progress.progress(30, text=f"Running {inputs['strategy']} strategy...")
        strategy_class = STRATEGY_MAP[inputs["strategy"]]
        strategy = strategy_class(**inputs.get("strategy_params", {}))
        df_with_signals = strategy.generate_signals(df)

        # ── Step 3: Run Backtest ──
        progress.progress(50, text="Running backtest simulation...")
        engine = BacktestEngine(
            data=df_with_signals,
            ticker=inputs["ticker"],
            initial_capital=inputs["capital"],
        )
        portfolio = engine.run()
        equity_df = portfolio.get_equity_df()

        # ── Post-run sanity check ──
        num_trades = len(portfolio.trade_history)
        if num_trades == 0:
            first_price = df["close"].iloc[0]
            st.warning(
                f"⚠️ **0 trades executed.** "
                f"{inputs['ticker']} opened at **${first_price:.2f}** on the first day. "
                f"Your capital is **${inputs['capital']:,}**. "
                f"Even the 1-share fallback couldn't execute — this usually means the stock "
                f"price exceeds your available capital. Try increasing your initial capital."
            )

        # ── Step 4: Fetch Benchmark ──
        progress.progress(70, text=f"Fetching benchmark ({inputs['benchmark']})...")
        benchmark_returns = Benchmark.get_benchmark_returns(
            inputs["benchmark"], inputs["start_date"], inputs["end_date"]
        )
        benchmark_equity = Benchmark.get_benchmark_equity(
            inputs["benchmark"],
            inputs["start_date"],
            inputs["end_date"],
            initial_value=inputs["capital"],
        )

        # Portfolio returns
        portfolio_returns = equity_df["total_equity"].pct_change().dropna()

        # ── Step 5: Monte Carlo ──
        progress.progress(85, text="Running Monte Carlo simulation...")
        sim_df = MonteCarlo.simulate_paths(portfolio_returns, num_sims=1000)
        percentiles = MonteCarlo.get_percentile_paths(sim_df)

        progress.progress(100, text="✅ Complete!")

        # ── Cache Results in Session State ──
        st.session_state["equity_df"] = equity_df
        st.session_state["portfolio"] = portfolio
        st.session_state["benchmark_returns"] = benchmark_returns
        st.session_state["benchmark_equity"] = benchmark_equity
        st.session_state["portfolio_returns"] = portfolio_returns
        st.session_state["sim_df"] = sim_df
        st.session_state["percentiles"] = percentiles
        st.session_state["inputs"] = inputs
        st.session_state["strategy_name"] = strategy.name

        # Display results
        _display_results(st.session_state)

    except Exception as e:
        st.error(f"❌ Error: {e}")
        st.exception(e)


def _display_results(state: dict) -> None:
    """Display all results from session state."""

    equity_df = state["equity_df"]
    portfolio = state["portfolio"]
    inputs = state["inputs"]
    strategy_name = state.get("strategy_name", inputs["strategy"])

    st.subheader(f"Results: {inputs['ticker']} — {strategy_name}")

    # ── KPI Cards ──
    metrics_display.render_metrics(
        equity_df,
        portfolio.trade_history,
        state.get("portfolio_returns"),
        state.get("benchmark_returns"),
    )

    # ── Charts in Tabs ──
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Equity Curve",
        "📉 Drawdown",
        "📊 Returns Distribution",
        "🎲 Monte Carlo",
        "📋 Trade Log",
    ])

    with tab1:
        charts.render_equity_curve(
            equity_df,
            state.get("benchmark_equity"),
            strategy_name,
        )

    with tab2:
        charts.render_drawdown_chart(equity_df)

    with tab3:
        charts.render_returns_histogram(equity_df)

    with tab4:
        sim_df = state.get("sim_df", pd.DataFrame())
        percentiles = state.get("percentiles", {})
        if not sim_df.empty:
            charts.render_monte_carlo(sim_df, percentiles)

            # Monte Carlo summary stats
            mc_stats = MonteCarlo.summary_stats(sim_df)
            if mc_stats:
                st.markdown("**Monte Carlo Summary (1-year projection)**")
                mc1, mc2, mc3 = st.columns(3)
                mc1.metric("Median Final", f"{mc_stats['median_final']:.2f}x")
                mc2.metric("Prob. of Profit", f"{mc_stats['prob_profit']*100:.1f}%")
                mc3.metric("Worst Case (5%)", f"{mc_stats['worst_case_5pct']:.2f}x")

    with tab5:
        if portfolio.trade_history:
            trade_df = pd.DataFrame(portfolio.trade_history)
            st.dataframe(
                trade_df.style.format({
                    "price": "${:.2f}",
                    "commission": "${:.2f}",
                    "slippage": "${:.2f}",
                }),
                width='stretch',
            )
        else:
            st.info("No trades were executed during this backtest.")


if __name__ == "__main__":
    main()
