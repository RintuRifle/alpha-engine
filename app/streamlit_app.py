"""
Alpha Engine — Streamlit Dashboard

Main entry point for the interactive web application.
Wires together: data fetching, strategy execution, backtesting,
analytics, benchmark comparison, and visualization.

Modes:
  Single Strategy: Run one strategy with detailed analysis
  Compare All: Run all 7 strategies side-by-side with ranking
  Multi-Asset: Run strategy across multiple tickers simultaneously

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
from src.strategies.multi_factor import MultiFactorStrategy
from src.strategies.momentum_mr import MomentumMR
from src.strategies.custom_builder import CustomStrategy
from src.strategies.vwap_strategy import VWAPStrategy
from src.strategies.regime_detector import RegimeDetector
from src.backtester.engine import BacktestEngine
from src.analytics.benchmark import Benchmark
from src.analytics.monte_carlo import MonteCarlo
from src.analytics.report_generator import ReportGenerator
from components import sidebar, charts, metrics_display
from components.strategy_comparison import run_comparison, render_comparison
from components.walk_forward_ui import render_walk_forward
from components.optimizer_ui import render_optimizer
from components.multi_asset_ui import render_multi_asset
from components.execution_ui import render_execution_ui

# ── Page Config ──
st.set_page_config(
    page_title="Alpha Engine",
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
    "Multi-Factor": MultiFactorStrategy,
    "Momentum + MR": MomentumMR,
    "Buy & Hold": BuyAndHold,
    "Custom Builder": CustomStrategy,
    "VWAP Reversion": VWAPStrategy,
}


def main():
    # ── Header ──
    st.markdown(
        """
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/devicons/devicon@latest/devicon.min.css">
        <h1 style='text-align: center; margin-bottom: 0;'><i class="fa-solid fa-layer-group" style="color: #4ECDC4;"></i> Alpha Engine</h1>
        <p style='text-align: center; color: #888; margin-top: 0;'>
            Institutional-grade quantitative research, backtesting, and portfolio optimization platform
        </p>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # ── Sidebar Inputs ──
    inputs = sidebar.render_sidebar()
    
    # ── Main Panel Pre-Run UIs ──
    if inputs["strategy"] == "Custom Builder":
        from components.strategy_builder_ui import render_strategy_builder
        custom_params = render_strategy_builder()
        inputs["strategy_params"] = custom_params

    # ── Action Buttons ──
    st.sidebar.markdown("### <i class='fa-solid fa-bullseye' style='color: #FF6B6B;'></i> Actions", unsafe_allow_html=True)
    btn_col1, btn_col2 = st.sidebar.columns(2)
    run_single = btn_col1.button("Backtest", icon=":material/rocket_launch:", type="primary", use_container_width=True)
    run_compare = btn_col2.button("Compare", icon=":material/trophy:", use_container_width=True)

    btn_col3, btn_col4 = st.sidebar.columns(2)
    run_multi = btn_col3.button("Multi-Asset", icon=":material/public:", use_container_width=True)
    run_optimize = btn_col4.button("Optimize", icon=":material/build:", use_container_width=True)

    if run_single:
        st.session_state["app_mode"] = "single"
    elif run_compare:
        st.session_state["app_mode"] = "compare"
    elif run_multi:
        st.session_state["app_mode"] = "multi"
    elif run_optimize:
        st.session_state["app_mode"] = "optimize"
        
    app_mode = st.session_state.get("app_mode", "empty")

    if run_single:
        _run_backtest(inputs)
    elif run_compare:
        _run_comparison(inputs)
    elif app_mode == "single" and "equity_df" in st.session_state:
        _display_results(st.session_state)
    elif app_mode == "compare" and "comparison_data" in st.session_state:
        render_comparison(st.session_state["comparison_data"], inputs["capital"])
    elif app_mode == "multi":
        _run_multi_asset_mode(inputs)
    elif app_mode == "optimize":
        _run_optimizer_mode(inputs)


def _run_multi_asset_mode(inputs: dict) -> None:
    """Launch multi-asset backtest mode."""
    st.session_state.pop("equity_df", None)
    st.session_state.pop("comparison_data", None)

    strategy_class = STRATEGY_MAP[inputs["strategy"]]
    render_multi_asset(
        strategy_class=strategy_class,
        strategy_params=inputs.get("strategy_params", {}),
        backtest_engine_class=BacktestEngine,
        start_date=inputs["start_date"],
        end_date=inputs["end_date"],
        initial_capital=inputs["capital"],
        allocation=inputs.get("allocation", 0.95),
        allow_short=inputs.get("allow_short", False),
        use_stops=inputs.get("use_stops", False),
        atr_multiplier=inputs.get("atr_multiplier", 2.0),
    )


def _run_optimizer_mode(inputs: dict) -> None:
    """Launch parameter optimizer mode."""
    st.session_state.pop("equity_df", None)
    st.session_state.pop("comparison_data", None)

    try:
        cache = CacheManager()
        df = cache.get_data(inputs["ticker"], inputs["start_date"], inputs["end_date"])

        strategy_class = STRATEGY_MAP[inputs["strategy"]]
        render_optimizer(
            strategy_name=inputs["strategy"],
            strategy_class=strategy_class,
            data=df,
            backtest_engine_class=BacktestEngine,
            ticker=inputs["ticker"],
            initial_capital=inputs["capital"],
        )
    except Exception as e:
        st.error(f"❌ Error: {e}")
        st.exception(e)


def _run_comparison(inputs: dict) -> None:
    """Run all strategies and show comparison dashboard."""
    try:
        cache = CacheManager()
        df = cache.get_data(inputs["ticker"], inputs["start_date"], inputs["end_date"])

        comparison_data = run_comparison(
            df=df,
            ticker=inputs["ticker"],
            initial_capital=inputs["capital"],
            allocation=inputs.get("allocation", 0.95),
            allow_short=inputs.get("allow_short", False),
            use_stops=inputs.get("use_stops", False),
            atr_multiplier=inputs.get("atr_multiplier", 2.0),
        )

        st.session_state["comparison_data"] = comparison_data
        st.session_state.pop("equity_df", None)

        render_comparison(comparison_data, inputs["capital"])

    except Exception as e:
        st.error(f"❌ Comparison Error: {e}")
        st.exception(e)


def _run_backtest(inputs: dict) -> None:
    """Execute the full backtest pipeline and display results."""

    progress = st.progress(0, text="Initializing...")

    try:
        # ── Step 1: Fetch Data ──
        progress.progress(10, text=f"Fetching data for {inputs['ticker']}...")
        cache = CacheManager()
        df = cache.get_data(inputs["ticker"], inputs["start_date"], inputs["end_date"])

        # ── Step 2: Regime Detection ──
        progress.progress(20, text="Detecting market regime...")
        detector = RegimeDetector()
        regime_df = detector.detect(df)

        # ── Step 3: Generate Strategy Signals ──
        progress.progress(30, text=f"Running {inputs['strategy']} strategy...")
        strategy_class = STRATEGY_MAP[inputs["strategy"]]
        strategy = strategy_class(**inputs.get("strategy_params", {}))

        # Apply regime gating if enabled
        if inputs.get("regime_gate", False):
            df_with_signals = _apply_regime_gate(
                strategy, df, regime_df, inputs["strategy"]
            )
        else:
            df_with_signals = strategy.generate_signals(df)

        # ── Step 4: Run Backtest ──
        progress.progress(50, text="Running backtest simulation...")
        engine = BacktestEngine(
            data=df_with_signals,
            ticker=inputs["ticker"],
            initial_capital=inputs["capital"],
            allocation=inputs.get("allocation", 0.95),
            allow_short=inputs.get("allow_short", False),
            use_stops=inputs.get("use_stops", False),
            atr_multiplier=inputs.get("atr_multiplier", 2.0),
            use_trailing_stop=inputs.get("use_trailing_stop", True),
            use_circuit_breaker=inputs.get("use_circuit_breaker", False),
            circuit_breaker_pct=inputs.get("circuit_breaker_pct", -0.03),
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
                f"0 trades usually means one of two things: either the stock price exceeds your available capital, "
                f"OR your strategy generated 0 buy signals (e.g. your indicators require more historical data than is available)."
            )

        # ── Step 5: Fetch Benchmark ──
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

        # ── Step 6: Monte Carlo ──
        progress.progress(85, text="Running Monte Carlo simulation...")
        stress_prob = 0.10 if inputs.get("stress_test", False) else 0.0
        sim_df = MonteCarlo.simulate_paths(
            portfolio_returns, num_sims=1000, stress_probability=stress_prob
        )
        percentiles = MonteCarlo.get_percentile_paths(sim_df)

        # Stress test individual scenarios
        stress_results = []
        if inputs.get("stress_test", False):
            stress_results = MonteCarlo.stress_test_summary(portfolio_returns)

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
        st.session_state["stress_results"] = stress_results
        st.session_state["regime_df"] = regime_df
        st.session_state["df_raw"] = df
        st.session_state.pop("comparison_data", None)

        # Display results
        _display_results(st.session_state)

    except Exception as e:
        st.error(f"❌ Error: {e}")
        st.exception(e)


def _apply_regime_gate(strategy, df, regime_df, strategy_name):
    """
    Apply regime-based signal gating. Zero out signals in non-matching regimes.
    """
    compatibility = RegimeDetector.get_regime_strategy_compatibility()

    # Find which regimes this strategy is compatible with
    compatible_regimes = []
    for regime, strategies in compatibility.items():
        if strategy_name in strategies:
            compatible_regimes.append(regime)

    # If no compatibility defined, run everywhere
    if not compatible_regimes:
        return strategy.generate_signals(df)

    df_signals = strategy.generate_signals(df)

    # Zero out signals in incompatible regimes
    if "regime" in regime_df.columns and len(regime_df) == len(df_signals):
        mask = ~regime_df["regime"].isin(compatible_regimes)
        df_signals.loc[mask.values, "signal"] = 0

    return df_signals


def _display_results(state: dict) -> None:
    """Display all results from session state."""

    equity_df = state["equity_df"]
    portfolio = state["portfolio"]
    inputs = state["inputs"]
    strategy_name = state.get("strategy_name", inputs["strategy"])

    st.subheader(f"Results: {inputs['ticker']} — {strategy_name}")

    # Show risk controls status
    if inputs.get("use_stops", False):
        st.info(
            f"**Risk Controls Active** — ATR Stop ({inputs.get('atr_multiplier', 2.0)}x) "
            f"| Trailing: {'Yes' if inputs.get('use_trailing_stop', True) else 'No'} "
            f"| Circuit Breaker: {'Yes' if inputs.get('use_circuit_breaker', False) else 'No'}",
            icon=":material/security:"
        )

    if inputs.get("regime_gate", False):
        st.info("**Regime Gating Active** — signals filtered by market regime compatibility", icon=":material/psychology:")

    # ── KPI Cards ──
    metrics_display.render_metrics(
        equity_df,
        portfolio.trade_history,
        state.get("portfolio_returns"),
        state.get("benchmark_returns"),
    )

    # ── Charts in Tabs ──
    tab_names = [
        "Equity Curve",
        "Drawdown",
        "Returns Distribution",
        "Rolling Metrics",
        "Monte Carlo",
        "Walk-Forward",
        "Trade Log",
        "Live Execution"
    ]
    tabs = st.tabs(tab_names)

    with tabs[0]:
        charts.render_equity_curve(
            equity_df,
            state.get("benchmark_equity"),
            strategy_name,
        )

    with tabs[1]:
        charts.render_drawdown_chart(equity_df)

    with tabs[2]:
        charts.render_returns_histogram(equity_df)

    with tabs[3]:
        charts.render_rolling_metrics(equity_df)

    with tabs[4]:
        sim_df = state.get("sim_df", pd.DataFrame())
        percentiles = state.get("percentiles", {})
        if not sim_df.empty:
            charts.render_monte_carlo(sim_df, percentiles)

            # Monte Carlo summary stats
            mc_stats = MonteCarlo.summary_stats(sim_df)
            if mc_stats:
                st.markdown("**Monte Carlo Summary (1-year projection)**")
                mc1, mc2, mc3, mc4 = st.columns(4)
                mc1.metric("Median Final", f"{mc_stats['median_final']:.2f}x")
                mc2.metric("Prob. of Profit", f"{mc_stats['prob_profit']*100:.1f}%")
                mc3.metric("Worst Case (5%)", f"{mc_stats['worst_case_5pct']:.2f}x")
                mc4.metric("Prob. of 20%+ Loss", f"{mc_stats.get('prob_loss_20pct', 0)*100:.1f}%")

            # Stress test results
            stress_results = state.get("stress_results", [])
            if stress_results:
                charts.render_stress_test(stress_results)

    with tabs[5]:
        # Walk-Forward Analysis
        if inputs["strategy"] != "Buy & Hold":
            df_raw = state.get("df_raw")
            if df_raw is not None:
                strategy_class = STRATEGY_MAP[inputs["strategy"]]
                render_walk_forward(
                    df=df_raw,
                    strategy_name=inputs["strategy"],
                    strategy_class=strategy_class,
                    strategy_params=inputs.get("strategy_params", {}),
                    backtest_engine_class=BacktestEngine,
                    ticker=inputs["ticker"],
                    initial_capital=inputs["capital"],
                )
            else:
                st.info("Run a backtest first to see walk-forward analysis.")
        else:
            st.info("Walk-forward analysis is not applicable to Buy & Hold.")

    with tabs[6]:
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

    with tabs[7]:
        render_execution_ui(inputs)

    # ── Tear Sheet Export ──
    st.markdown("---")
    col_export1, col_export2, col_export3, _ = st.columns([1, 1, 1, 2])
    with col_export1:
        if st.button("Generate Tear Sheet", icon=":material/description:"):
            _generate_tearsheet(equity_df, inputs)
    with col_export2:
        if st.button("Download Trade Log", icon=":material/download:"):
            _download_trade_log(portfolio.trade_history, inputs)
    with col_export3:
        if st.button("Download PDF Report", icon=":material/picture_as_pdf:"):
            _generate_pdf_report(equity_df, portfolio, inputs, state)


def _generate_tearsheet(equity_df: pd.DataFrame, inputs: dict) -> None:
    """Generate and offer QuantStats tear sheet for download."""
    filename = f"reports/tearsheets/{inputs['ticker']}_{inputs['strategy'].replace(' ', '_')}.html"
    title = f"{inputs['ticker']} — {inputs['strategy']} Tear Sheet"

    with st.spinner("Generating tear sheet..."):
        success = ReportGenerator.generate_tearsheet(
            equity_df,
            benchmark_ticker=inputs["benchmark"],
            output_file=filename,
            title=title,
        )

    if success:
        try:
            with open(filename, "r", encoding="utf-8") as f:
                html_content = f.read()
            st.download_button(
                "Download HTML Report",
                data=html_content,
                file_name=os.path.basename(filename),
                mime="text/html",
                icon=":material/download:"
            )
            st.success(f"Tear sheet generated! Click above to download.", icon=":material/check_circle:")
        except Exception as e:
            st.warning(f"Report generated at {filename} but couldn't load for download: {e}", icon=":material/warning:")
    else:
        st.warning("Tear sheet generation failed. Check that quantstats is installed.", icon=":material/error:")


def _download_trade_log(trade_history: list, inputs: dict) -> None:
    """Export trade log as CSV."""
    if not trade_history:
        st.info("No trades to export.")
        return

    df = pd.DataFrame(trade_history)
    csv = df.to_csv(index=False)
    st.download_button(
        "📥 Download CSV",
        data=csv,
        file_name=f"{inputs['ticker']}_{inputs['strategy'].replace(' ', '_')}_trades.csv",
        mime="text/csv",
    )


def _generate_pdf_report(equity_df: pd.DataFrame, portfolio, inputs: dict, state: dict) -> None:
    """Generate a PDF tear sheet and offer it for download."""
    from src.analytics.pdf_report import generate_pdf_report
    from src.analytics.metrics import Metrics

    with st.spinner("Generating PDF report..."):
        metrics = Metrics.compute_all(equity_df, portfolio.trade_history)
        filename = f"reports/{inputs['ticker']}_{inputs['strategy'].replace(' ', '_')}_report.pdf"

        result = generate_pdf_report(
            equity_df=equity_df,
            metrics=metrics,
            strategy_name=state.get("strategy_name", inputs["strategy"]),
            ticker=inputs["ticker"],
            start_date=str(inputs["start_date"]),
            end_date=str(inputs["end_date"]),
            initial_capital=inputs["capital"],
            trade_history=portfolio.trade_history,
            benchmark_equity=state.get("benchmark_equity"),
            output_path=filename,
        )

    if result and os.path.exists(result):
        with open(result, "rb") as f:
            pdf_data = f.read()
        st.download_button(
            "📥 Download PDF",
            data=pdf_data,
            file_name=os.path.basename(result),
            mime="application/pdf",
            icon=":material/picture_as_pdf:",
        )
        st.success("PDF report generated! Click above to download.", icon=":material/check_circle:")
    else:
        st.warning("PDF report generation failed. Make sure fpdf2 is installed: `pip install fpdf2`")


if __name__ == "__main__":
    main()
