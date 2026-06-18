"""
Sidebar component for the Streamlit dashboard.

Handles all user inputs: ticker, date range, strategy selection,
strategy-specific parameter sliders, and configuration options.
"""

import streamlit as st
from datetime import date, timedelta
from typing import Dict, Any


def render_sidebar() -> Dict[str, Any]:
    """
    Render the sidebar with all configuration inputs.

    Returns:
        Dict with all user-selected parameters.
    """
    st.sidebar.markdown("## ⚙️ Configuration")

    # ── Ticker Input ──
    st.sidebar.markdown("### 📊 Asset")
    ticker = st.sidebar.text_input(
        "Ticker Symbol",
        value="AAPL",
        help="Enter any Yahoo Finance ticker (e.g., AAPL, MSFT, RELIANCE.NS)",
    )

    # ── Date Range ──
    st.sidebar.markdown("### 📅 Date Range")
    col1, col2 = st.sidebar.columns(2)
    start_date = col1.date_input(
        "Start",
        value=date.today() - timedelta(days=365 * 3),
    )
    end_date = col2.date_input("End", value=date.today())

    # ── Capital ──
    st.sidebar.markdown("### 💰 Capital")
    capital = st.sidebar.number_input(
        "Initial Capital ($)",
        min_value=1000,
        max_value=10_000_000,
        value=10000,
        step=1000,
    )

    # ── Strategy Selection ──
    st.sidebar.markdown("### 🧠 Strategy")
    strategy = st.sidebar.selectbox(
        "Select Strategy",
        ["SMA Crossover", "RSI Reversion", "Bollinger Bands", "MACD", "Buy & Hold"],
    )

    # ── Strategy-Specific Parameters ──
    strategy_params: Dict[str, Any] = {}

    if strategy == "SMA Crossover":
        st.sidebar.markdown("**SMA Parameters**")
        strategy_params["short_window"] = st.sidebar.slider(
            "Short Window", min_value=5, max_value=100, value=50, step=5
        )
        strategy_params["long_window"] = st.sidebar.slider(
            "Long Window", min_value=50, max_value=400, value=200, step=10
        )

    elif strategy == "RSI Reversion":
        st.sidebar.markdown("**RSI Parameters**")
        strategy_params["window"] = st.sidebar.slider(
            "RSI Period", min_value=5, max_value=30, value=14
        )
        strategy_params["oversold"] = st.sidebar.slider(
            "Oversold Threshold", min_value=10, max_value=40, value=30
        )
        strategy_params["overbought"] = st.sidebar.slider(
            "Overbought Threshold", min_value=60, max_value=90, value=70
        )

    elif strategy == "Bollinger Bands":
        st.sidebar.markdown("**Bollinger Parameters**")
        strategy_params["window"] = st.sidebar.slider(
            "SMA Window", min_value=5, max_value=50, value=20
        )
        strategy_params["num_std"] = st.sidebar.slider(
            "Std Deviations", min_value=1.0, max_value=3.5, value=2.0, step=0.25
        )

    elif strategy == "MACD":
        st.sidebar.markdown("**MACD Parameters**")
        strategy_params["fast_period"] = st.sidebar.slider(
            "Fast EMA", min_value=5, max_value=20, value=12
        )
        strategy_params["slow_period"] = st.sidebar.slider(
            "Slow EMA", min_value=15, max_value=50, value=26
        )
        strategy_params["signal_period"] = st.sidebar.slider(
            "Signal EMA", min_value=5, max_value=20, value=9
        )

    # ── Benchmark ──
    st.sidebar.markdown("### 📈 Benchmark")
    benchmark = st.sidebar.selectbox(
        "Benchmark Ticker",
        ["SPY", "^GSPC", "^NSEI", "QQQ"],
        help="Compare strategy against this benchmark",
    )

    # ── Divider ──
    st.sidebar.markdown("---")

    return {
        "ticker": ticker.upper().strip(),
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "capital": capital,
        "strategy": strategy,
        "strategy_params": strategy_params,
        "benchmark": benchmark,
    }
