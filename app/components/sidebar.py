"""
Sidebar component for the Streamlit dashboard.

Handles all user inputs: ticker, date range, strategy selection,
strategy-specific parameter sliders, risk management, and engine settings.
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
    st.sidebar.markdown("## <i class='fa-solid fa-gear' style='color: #4ECDC4;'></i> Configuration", unsafe_allow_html=True)

    # ── Ticker Input ──
    st.sidebar.markdown("### <i class='fa-solid fa-chart-simple' style='color: #4ECDC4;'></i> Asset", unsafe_allow_html=True)
    
    POPULAR_TICKERS = {
        "AAPL": "Apple Inc.",
        "NVDA": "NVIDIA Corp.",
        "MSFT": "Microsoft Corp.",
        "GOOG": "Alphabet Inc.",
        "AMZN": "Amazon.com",
        "META": "Meta Platforms",
        "TSLA": "Tesla Inc.",
        "AMD": "Advanced Micro Devices",
        "BRK-B": "Berkshire Hathaway",
        "SPY": "S&P 500 ETF",
        "QQQ": "Nasdaq 100 ETF",
        "RELIANCE.NS": "Reliance Ind.",
        "TCS.NS": "Tata Consultancy",
        "INFY.NS": "Infosys Ltd.",
        "Custom...": "Type your own ticker"
    }
    
    ticker_choice = st.sidebar.selectbox(
        "Search Asset / Company",
        options=list(POPULAR_TICKERS.keys()),
        format_func=lambda x: f"{x} — {POPULAR_TICKERS[x]}",
        index=0,
        help="Type a company name or ticker to search, or select 'Custom...' to enter any Yahoo Finance ticker."
    )
    
    if ticker_choice == "Custom...":
        ticker = st.sidebar.text_input("Enter Custom Ticker", value="IBM", help="e.g., IBM, BA, TATAMOTORS.NS")
    else:
        ticker = ticker_choice

    # ── Date Range ──
    st.sidebar.markdown("### <i class='fa-regular fa-calendar-days' style='color: #4ECDC4;'></i> Date Range", unsafe_allow_html=True)
    col1, col2 = st.sidebar.columns(2)
    start_date = col1.date_input(
        "Start",
        value=date.today() - timedelta(days=365 * 3),
    )
    end_date = col2.date_input("End", value=date.today())

    # ── Capital ──
    st.sidebar.markdown("### <i class='fa-solid fa-sack-dollar' style='color: #4ECDC4;'></i> Capital", unsafe_allow_html=True)
    capital = st.sidebar.number_input(
        "Initial Capital ($)",
        min_value=1000,
        max_value=10_000_000,
        value=10000,
        step=1000,
    )

    # ── Strategy Selection ──
    st.sidebar.markdown("### <i class='fa-solid fa-brain' style='color: #4ECDC4;'></i> Strategy", unsafe_allow_html=True)
    strategy = st.sidebar.selectbox(
        "Select Strategy",
        [
            "SMA Crossover",
            "RSI Reversion",
            "Bollinger Bands",
            "MACD",
            "Multi-Factor",
            "Momentum + MR",
            "Buy & Hold",
            "Custom Builder",
            "VWAP Reversion",
        ],
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

    elif strategy == "Multi-Factor":
        st.sidebar.markdown("**Multi-Factor Parameters**")
        strategy_params["min_score"] = st.sidebar.slider(
            "Min Signal Score", min_value=2, max_value=6, value=3,
            help="Higher = fewer but stronger signals. Max possible: 7"
        )
        strategy_params["rsi_window"] = st.sidebar.slider(
            "RSI Period", min_value=5, max_value=30, value=14
        )
        strategy_params["bb_window"] = st.sidebar.slider(
            "BB Window", min_value=10, max_value=50, value=20
        )
        strategy_params["bb_std"] = st.sidebar.slider(
            "BB Std Dev", min_value=1.0, max_value=3.5, value=2.0, step=0.25
        )

    elif strategy == "Momentum + MR":
        st.sidebar.markdown("**Momentum + MR Parameters**")
        strategy_params["rsi_window"] = st.sidebar.slider(
            "RSI Period", min_value=5, max_value=30, value=14
        )
        strategy_params["entry_rsi"] = st.sidebar.slider(
            "Entry RSI (buy dip below)", min_value=20, max_value=50, value=40
        )
        strategy_params["exit_rsi"] = st.sidebar.slider(
            "Exit RSI (sell above)", min_value=40, max_value=80, value=55
        )
        strategy_params["trend_ma"] = st.sidebar.slider(
            "Trend MA Period", min_value=50, max_value=300, value=200, step=10
        )

    elif strategy == "VWAP Reversion":
        st.sidebar.markdown("**VWAP Parameters**")
        strategy_params["vwap_window"] = st.sidebar.slider(
            "VWAP Window", min_value=5, max_value=60, value=20, step=5,
            help="Rolling window for VWAP calculation"
        )
        strategy_params["threshold"] = st.sidebar.slider(
            "Deviation Threshold", min_value=0.005, max_value=0.10, value=0.02, step=0.005,
            format="%.3f",
            help="How far price must deviate from VWAP to trigger a signal (0.02 = 2%)"
        )

    # ── Engine Settings ──
    st.sidebar.markdown("### <i class='fa-solid fa-bolt' style='color: #FFD93D;'></i> Engine Settings", unsafe_allow_html=True)
    allocation = st.sidebar.slider(
        "Capital Allocation %",
        min_value=10,
        max_value=100,
        value=95,
        step=5,
        help="Percentage of capital to deploy per trade. 95% recommended (5% reserved for costs).",
    )
    allow_short = st.sidebar.checkbox(
        "Allow Short Selling",
        value=False,
        help="Enable short selling on sell signals when no position is held.",
    )

    # ── Risk Management ──
    st.sidebar.markdown("### <i class='fa-solid fa-shield-halved' style='color: #FF6B6B;'></i> Risk Management", unsafe_allow_html=True)
    use_stops = st.sidebar.checkbox(
        "ATR Stop Losses",
        value=False,
        help="Enable ATR-based dynamic stop losses. Typically reduces max drawdown 20-40%.",
    )

    atr_multiplier = 2.0
    use_trailing_stop = True
    use_circuit_breaker = False
    circuit_breaker_pct = -0.03
    stress_test = False

    if use_stops:
        atr_multiplier = st.sidebar.slider(
            "ATR Multiplier",
            min_value=1.0,
            max_value=4.0,
            value=2.0,
            step=0.5,
            help="1.5=tight stops (more trades), 2.0=standard, 3.0=wide (fewer trades)",
        )
        use_trailing_stop = st.sidebar.checkbox(
            "Trailing Stop",
            value=True,
            help="Stop follows peak price upward, never moves down.",
        )
        use_circuit_breaker = st.sidebar.checkbox(
            "Circuit Breaker",
            value=False,
            help="Halt trading if daily P&L exceeds threshold.",
        )
        if use_circuit_breaker:
            circuit_breaker_pct = st.sidebar.slider(
                "Circuit Breaker (%)",
                min_value=-10.0,
                max_value=-1.0,
                value=-3.0,
                step=0.5,
            ) / 100.0

    # ── Monte Carlo Settings ──
    st.sidebar.markdown("### <i class='fa-solid fa-dice' style='color: #9B59B6;'></i> Monte Carlo", unsafe_allow_html=True)
    stress_test = st.sidebar.checkbox(
        "Stress Test Scenarios",
        value=False,
        help="Inject 2008/COVID/rate-hike crash patterns into 10% of simulation paths.",
    )

    # ── Intelligence ──
    st.sidebar.markdown("### <i class='fa-solid fa-network-wired' style='color: #3498DB;'></i> Intelligence", unsafe_allow_html=True)
    regime_gate = st.sidebar.checkbox(
        "Regime Gating",
        value=False,
        help="Auto-disable strategy signals in incompatible market regimes. "
             "E.g., RSI signals are zeroed out during strong trends.",
    )

    # ── Benchmark ──
    st.sidebar.markdown("### <i class='fa-solid fa-arrow-trend-up' style='color: #2ECC71;'></i> Benchmark", unsafe_allow_html=True)
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
        "allocation": allocation / 100.0,
        "allow_short": allow_short,
        "use_stops": use_stops,
        "atr_multiplier": atr_multiplier,
        "use_trailing_stop": use_trailing_stop,
        "use_circuit_breaker": use_circuit_breaker,
        "circuit_breaker_pct": circuit_breaker_pct,
        "stress_test": stress_test,
        "regime_gate": regime_gate,
    }

